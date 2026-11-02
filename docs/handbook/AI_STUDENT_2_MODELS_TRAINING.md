# AI handoff — Student 2: models and training

## Whole-project context

We are a four-student team building a local earthquake building-damage inspection-support prototype. The system accepts supported before/after optical imagery, localizes buildings/groups in the pre-event image, creates paired crops, estimates damage with our trained classifier, converts pixel regions to geographic features, and shows an interactive map with suggested inspection tiers and CSV/GeoJSON downloads.

Regions/building groups are accepted targets. Do not assume one connected segmentation object is one verified physical building. Suggested high/medium/lower tiers support visual inspection planning, not structural-safety certification. Within-tier targets remain tied; model confidence is not a physical damage percentage or a justified within-tier urgency score.

Models are already selected:
- Frozen Microsoft pretrained UNet pre-event building branch: segmentation/localization only. Do not reuse its pretrained damage head as our trained damage classifier. A pinned checkpoint previously loaded and ran on one Mexico training image without weight updates. This is not held-out performance.
- Shared-encoder paired ResNet-18 initialized from ImageNet. It encodes both 224×224 crops with the same weights, concatenates before/after features and their absolute feature difference, and uses a new four-output head. ImageNet initialization originally recognized everyday objects, not damage. The new damage classifier requires supervised training.

Four native classes, in order: no-damage, minor-damage, major-damage, destroyed. Quantitative scoring retains all four; minor/major confusion remains wrong. The map alone groups probabilities as P(no damage), P(minor)+P(major), P(destroyed), then selects its display category. Preserve native probabilities/class in records.

## Frozen data decisions

| Role | Source | Prepared membership |
|---|---|---|
| Train | xBD Harvey + Michael + Mexico earthquake | 783 pairs, 77,338 eligible building annotations |
| Validation | xBD Florence | 319 pairs, 6,120 annotations |
| Primary test | xBD Matthew | 238 pairs, 13,155 annotations |
| External test | HaitiBRD 2010 earthquake | 139 reference regions: 83/32/16/8 |
| External test | EBD Türkiye 2023 earthquake | 1,461 reference regions: 1,433/19/3/6 |

External count order is no/minor/major/destroyed. Optional pooled result: 1,600 regions, support 1,516/51/19/14. Retain all four classes from both sources; no destroyed-only additions or oversampling. Separate source results are mandatory; pooling is supplementary. Neither external source enters training, validation, tuning or checkpoint selection.

Source annotations have different provenance: manual satellite interpretation for Haiti, model-assisted/manual-corrected for EBD. Both document xBD-style criteria; do not claim identical annotation reliability or field-engineering truth. Haiti is one small original scene with twenty derived crops; those are not twenty independent scenes. Raw advertised building totals do not equal available classifier instances.

Data indexes: data/xbd_team_v1 and data/team_external_tests_v1. Data/weights/runs/runtime are local, ignored by Git. A fresh clone does not include pixels or checkpoints. Prepared Haiti input images are in data/haitibrd_prepared_v1, including twelve same-grid RGB GeoTIFF pairs. EBD has no established coordinates; never invent them. Reference GeoJSON contains labels and must not become a production inference input.

## Current implementation state

Data/source audits, split/config decisions, preparation scripts, classifier/evaluator code and detector sanity checking exist. The damage classifier has not been trained in this handoff and no damage accuracy has been measured. backend/app.py has health only; frontend/ is a buildable starter, not the interactive map. contracts/examples/result.fixture.json is explicitly synthetic developer data, not real predictions. Local source checks previously passed; inspect and rerun relevant checks after your changes instead of claiming old results verify new code.

The team goal is one real image pair → detected regions → genuine trained damage predictions → suggested tiers → interactive map → downloadable report. Classifier evaluation on reference crops is separate from complete detector/pipeline evaluation. Disclose possible detector pretraining overlap with xBD events.

## How to use this handoff

All paths below are relative to the repository root. Read the actual files before editing; do not rely only on this document. Read README.md, docs/handbook/STUDENT_PROJECT_GUIDE.md, docs/OWNERSHIP.md, docs/SETUP.md, docs/EXTERNAL_TESTS.md, docs/LABEL_CONTRACT.md, configs/dataset_roles.json and contracts/API.md as relevant.

This file provides project context and role boundaries. Follow the student's current request and the agreed repository configuration. When this file is first provided, inspect the repository and establish the student's immediate task. Do not launch training, large downloads or unrelated implementation merely because they appear in the plan. Preparation so far ran no damage training. If the student explicitly requests the next authorized training stage, work within that stage and the hardware/data constraints.

Work on a branch, preserve teammates' changes and coordinate shared contracts/configuration/dependency edits. Own your module and matching report section; do not independently redesign the whole project. Keep interfaces backward compatible where feasible and update an example with any agreed change. Never fabricate model results, civil approval, geographic coordinates, tests or implemented endpoints.

Provide concise plain-language progress: what exists, what you changed, how checked, and the next handoff/blocker. If required data/weights are absent, identify the exact missing source/path and continue independent source work; do not pretend preparation or inference succeeded.

## Your role

Act as the technical assistant for Student 2. You own localization, damage-model training, checkpoint provenance and the model inference function. Student 1 owns data/evaluation integrity; Student 3 owns jobs/geography/exports; Student 4 owns the map. Do not take over their modules or change their interfaces silently.

### Owned files

- quake/models.py, quake/training.py, quake/detector.py, quake/cli.py and quake/vendor/.
- scripts/download_weights.py and scripts/verify_detector.py.
- Matching model tests, including tests/test_detector.py.
- reports/models/.

Coordinate with Student 1 on preprocessing, class order, splits, loss weights and evaluation changes. Coordinate the inference interface with Student 3 in contracts/. Retain the Microsoft source license.

## Work in this order

1. Inspect current code and checkpoint purpose checks. Confirm the actual GPU model, VRAM, RAM and OS. Do not assume CUDA is available or that batch size 16 fits.
2. Reproduce the frozen detector loading/inference check using verified local data and the pinned checkpoint. No optimizer/backward pass is needed for this check. Record runtime and inspect the output. One successful image is not a detector benchmark.
3. Confirm Student 1's manifests and crop loader. Keep before/after crops in the same window and use identical training augmentations.
4. When the student requests training, first run a tiny learning check using training examples only. This asks whether the implementation can learn a few examples, not how well it generalizes.
5. Once the tiny check passes and hardware is understood, train the paired model. Use validation only to select checkpoints/settings. Keep test answers out of development.
6. Train the after-only ResNet-18 comparison on identical xBD splits. Record configuration differences clearly.
7. Hand frozen, reloadable checkpoints to Student 1 for evaluation, and a documented real inference function to Student 3. Support integration of one genuine prediction before polishing full-scale experiments.

## Model details to preserve

The localization adapter uses only the frozen pre-event segmentation branch. Do not use the upstream pretrained damage output as the required trained damage model. Keep its pinned checksum/source revision and license. Possible xBD pretraining overlap must be disclosed for detector/full-pipeline results.

DamageClassifier uses one ResNet-18 encoder shared between before/after views. Its original ImageNet output is removed. Each view yields 512 features; paired concatenation contains before, after and absolute difference, totaling 1,536 inputs to a new four-output linear head. After-only mode uses 512 post-event features. The absolute difference is between feature vectors, not raw pixels.

Crop each reference bbox with 20% context on each side; pad edges; resize 224×224; apply ImageNet normalization. Current starting schedule: three head-only epochs, then up to twenty fine-tuning epochs. AdamW head LR 1e-3, encoder LR 1e-4, weight decay 1e-4, seed 42; validation macro-F1 selects checkpoints with patience five. Weights use inverse square-root training class frequency normalized to mean one. Reduce batch size if required, recording actual settings.

Inspect actual training code before describing behavior. If changing the encoder's frozen/evaluation mode, optimizer groups, memory handling or restart logic, verify the change rather than assuming the plan already implements every detail.

### Commands for the appropriate stage

Detector-only, once data/weights exist:

    python scripts/download_weights.py
    python scripts/verify_detector.py

Training, only for an explicitly requested training stage:

    python -m quake.cli train --data data/xbd_team_v1 --output runs/tiny_paired --tiny
    python -m quake.cli train --data data/xbd_team_v1 --output runs/paired_v1
    python -m quake.cli train --data data/xbd_team_v1 --output runs/after_only_v1 --mode after_only

Use fresh run directories. If memory failure requires restarting, do not silently preserve a partially completed epoch while claiming a clean run. Save actual configuration, source revision, manifest/checkpoint hashes, learning logs, runtime and measured peak memory.

## Evidence and inference handoff

A tiny trial checkpoint must remain identified as feasibility-only. Its training-subset score is not validation/test accuracy and it cannot replace the final trained experiment checkpoint. Do not bypass load_damage purpose checks to make integration appear complete.

Agree an inference function with Student 3. Inputs should be supported imagery and model configuration, not reference damage labels. Outputs include pixel regions, four probabilities in the fixed class order, image IDs and model version. The backend handles jobs, coordinates and exports. The map's grouped categories are presentation, not a new three-class training objective.

Do not sort physical inspection urgency by model confidence, invent extra damage categories, or add a target accuracy unsupported by results. For touching/merged detections, report the group object and its limits. Never call fixture probabilities genuine inference.

## Acceptance and report

The first training gate needs actual optimization, evidence of learning on the tiny training-only subset, reloadable weights and measured runtime/memory. The main handoff needs a genuine trained checkpoint, consistent inference after reload, settings/manifests/logs and the after-only comparison.

Write reports/models/ with architecture, transfer learning, preprocessing, training settings, hardware, checkpoint selection, baselines, provenance and measured results. Student 1 evaluates held-out tests after freezing; cooperate on error analysis without tuning to those answers.
