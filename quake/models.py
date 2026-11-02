import torch
from torch import nn
from torchvision.models import resnet18, ResNet18_Weights


class DamageClassifier(nn.Module):
    def __init__(self, mode="paired", pretrained=True):
        super().__init__()
        if mode not in ("paired", "after_only"):
            raise ValueError("Unknown classifier mode")
        self.mode = mode
        self.encoder = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1 if pretrained else None)
        self.encoder.fc = nn.Identity()
        self.head = nn.Linear(1536 if mode == "paired" else 512, 4)

    def forward(self, before, after):
        post = self.encoder(after)
        if self.mode == "after_only":
            return self.head(post)
        pre = self.encoder(before)
        return self.head(torch.cat((pre, post, torch.abs(pre - post)), dim=1))


def load_damage(path, device="cpu", allow_feasibility=False):
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if checkpoint.get("purpose") != "trained_experiment" and not allow_feasibility:
        raise ValueError("Checkpoint is feasibility-only; explicitly enable feasibility mode to use it")
    model = DamageClassifier(checkpoint["mode"], pretrained=False)
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.eval().to(device)
    return model, checkpoint
