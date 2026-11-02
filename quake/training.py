import collections
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from .crops import BuildingDataset
from .data import validate_manifest
from .io import jsonl, write_json, sha256
from .metrics import classification_metrics
from .models import DamageClassifier, load_damage


def seed_everything(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def class_weights(rows):
    counts = np.bincount([r["class_index"] for r in rows], minlength=4)
    if (counts == 0).any():
        raise ValueError("Training requires at least one building of every category")
    weights = 1 / np.sqrt(counts.astype(float))
    return torch.tensor(weights / weights.mean(), dtype=torch.float32)


def predict_rows(model, rows, batch_size, device):
    labels, predictions, probabilities = [], [], []
    model.eval()
    with torch.inference_mode():
        for before, after, target in DataLoader(BuildingDataset(rows), batch_size=batch_size):
            p = model(before.to(device), after.to(device)).softmax(1).cpu()
            labels.extend(target.tolist())
            predictions.extend(p.argmax(1).tolist())
            probabilities.extend(p.tolist())
    return labels, predictions, probabilities


def train(data, output, mode="paired", epochs=23, batch_size=16, tiny=False, steps=150):
    seed_everything()
    torch.set_num_threads(2)
    manifest = validate_manifest(data)
    rows = list(jsonl(Path(data) / "buildings.jsonl"))
    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "validation"]
    if tiny:
        selected = []
        for c in range(4):
            selected.extend([r for r in train_rows if r["class_index"] == c][:2])
        train_rows = val_rows = selected
    output = Path(output)
    if (output / "best.pt").exists():
        raise ValueError("Use a fresh experiment directory; checkpoint already exists")
    output.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DamageClassifier(mode, pretrained=True).to(device)
    weights = class_weights(train_rows).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True).strip()
    except subprocess.CalledProcessError:
        revision = "uncommitted"
    config = {"mode": mode, "seed": 42, "batch_size": batch_size, "epochs": epochs,
              "tiny": tiny, "tiny_steps": steps, "manifest": manifest,
              "class_weights": weights.cpu().tolist(), "code_revision": revision,
              "device": device, "encoder_initialization": "torchvision_ResNet18_IMAGENET1K_V1",
              "context_each_side": .2, "input_size": 224,
              "selection_partition": "train_tiny" if tiny else "validation"}
    write_json(output / "config.json", config)
    start = time.perf_counter()
    best, stale, history = -1., 0, []
    if tiny:
        for parameter in model.encoder.parameters():
            parameter.requires_grad = False
        model.encoder.eval()
        # Cache frozen features to make the CPU feasibility trial inexpensive.
        dataset = BuildingDataset(train_rows)
        before, after = [], []
        for i in range(len(dataset)):
            a, b, _ = dataset[i]
            before.append(a)
            after.append(b)
        with torch.no_grad():
            post = model.encoder(torch.stack(after).to(device))
            pre = model.encoder(torch.stack(before).to(device))
            features = torch.cat((pre, post, abs(pre-post)), 1) if mode == "paired" else post
        target = torch.tensor([r["class_index"] for r in train_rows], device=device)
        optimizer = torch.optim.AdamW(model.head.parameters(), lr=1e-3, weight_decay=1e-4)
        losses = []
        for step in range(steps):
            optimizer.zero_grad()
            loss = loss_fn(model.head(features), target)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        predictions = model.head(features).argmax(1).detach().cpu().tolist()
        result = classification_metrics(target.cpu().tolist(), predictions)
        result.update({"initial_loss": losses[0], "final_loss": losses[-1],
                       "passed": result["macro_f1"] >= .95 and losses[-1] < losses[0] * .25,
                       "purpose": "tiny_training_only_overfit_not_generalization"})
        checkpoint = {"state_dict": model.cpu().state_dict(), "mode": mode, "purpose": "feasibility_only",
                      "config": config, "class_names": list(manifest["classes"]), "metrics": result}
        torch.save(checkpoint, output / "best.pt")
        write_json(output / "tiny_result.json", result)
        write_json(output / "tiny_buildings.json", train_rows)
        print(result, flush=True)
    else:
        optimizer = torch.optim.AdamW([
            {"params": model.encoder.parameters(), "lr": 1e-4},
            {"params": model.head.parameters(), "lr": 1e-3}], weight_decay=1e-4)
        for epoch in range(epochs):
            frozen = epoch < 3
            for parameter in model.encoder.parameters():
                parameter.requires_grad = not frozen
            model.train()
            if frozen:
                model.encoder.eval()
            loader = DataLoader(BuildingDataset(train_rows, augment=True), batch_size=batch_size, shuffle=True)
            running, batches = 0., 0
            try:
                for before, after, target in loader:
                    optimizer.zero_grad(set_to_none=True)
                    loss = loss_fn(model(before.to(device), after.to(device)), target.to(device))
                    loss.backward()
                    optimizer.step()
                    running += float(loss.detach())
                    batches += 1
            except torch.cuda.OutOfMemoryError:
                if batch_size <= 1:
                    raise
                # Roll back the incomplete epoch including optimizer and RNG states.
                raise RuntimeError("GPU memory exhausted. Restart this experiment in a new directory with half the batch size; do not silently retain a partial epoch.")
            truth, predicted, _ = predict_rows(model, val_rows, batch_size, device)
            metrics = classification_metrics(truth, predicted)
            history.append({"epoch": epoch+1, "loss": running/max(batches, 1), "validation": metrics})
            score = metrics["macro_f1"]
            print(f"epoch={epoch+1} loss={running/max(batches,1):.4f} val_macro_f1={score:.4f}", flush=True)
            if score > best:
                best, stale = score, 0
                torch.save({"state_dict": model.state_dict(), "mode": mode, "purpose": "trained_experiment",
                            "config": config, "epoch": epoch+1, "metrics": metrics,
                            "class_names": list(manifest["classes"])}, output / "best.pt")
            else:
                stale += 1
            write_json(output / "history.json", history)
            if stale >= 5:
                break
    runtime = {"elapsed_seconds": time.perf_counter()-start, "device": device,
               "peak_cuda_memory_bytes": torch.cuda.max_memory_allocated() if device == "cuda" else 0,
               "checkpoint_sha256": sha256(output / "best.pt")}
    write_json(output / "runtime.json", runtime)
    return runtime


def evaluate(data, checkpoint, split, output, allow_feasibility=False):
    manifest = validate_manifest(data)
    model, saved = load_damage(checkpoint, allow_feasibility=allow_feasibility)
    if saved["config"]["manifest"]["buildings_sha256"] != manifest["buildings_sha256"]:
        raise ValueError("Checkpoint and evaluation manifest do not match")
    rows = list(jsonl(Path(data) / "buildings.jsonl"))
    subset = [r for r in rows if r["split"] == split]
    if not subset:
        raise ValueError("Empty evaluation partition")
    truth, predicted, probabilities = predict_rows(model, subset, 16, "cpu")
    training_labels = [r["class_index"] for r in rows if r["split"] == "train"]
    majority = collections.Counter(training_labels).most_common(1)[0][0]
    result = {"split": split, "level": "ground_truth_building_crops", "classifier": classification_metrics(truth, predicted),
              "majority_baseline": classification_metrics(truth, [majority]*len(truth)),
              "checkpoint_sha256": sha256(checkpoint), "purpose": saved["purpose"],
              "predictions": [{"building_id": r["building_id"], "truth": y, "prediction": k, "probabilities": p}
                              for r, y, k, p in zip(subset, truth, predicted, probabilities)]}
    write_json(output, result)
    return result["classifier"]
