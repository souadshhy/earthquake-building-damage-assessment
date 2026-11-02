"""Frozen pre-event branch of the pinned Microsoft checkpoint; no damage output."""
from pathlib import Path
import hashlib

import numpy as np
import torch
from torch import nn

from .vendor.microsoft_siam_unet import SiamUnet

PINNED_SHA256 = "d80e9a49d3001d1f152b82bf38e14bb5dc0b1b1b3f62a4b88c25a2a13e9643b3"


def load_pre_event_detector(path):
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != PINNED_SHA256:
        raise ValueError("Expected the verified pinned Microsoft checkpoint")
    allowed = [(np._core.multiarray.scalar, "numpy.core.multiarray.scalar"), np.dtype,
               type(np.dtype("float64")), type(np.dtype("float32")), type(np.dtype("int64"))]
    with torch.serialization.safe_globals(allowed):
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    state = checkpoint["state_dict"]
    model = SiamUnet(init_features=state["encoder1.enc1conv1.weight"].shape[0],
                     out_channels_s=state["conv_s.weight"].shape[0],
                     out_channels_c=state["conv_c.weight"].shape[0])
    model.load_state_dict(state, strict=True)
    model.requires_grad_(False)
    model.eval()
    return PreEventBranch(model).eval()


class PreEventBranch(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, image):
        m = self.model
        e1 = m.encoder1(image)
        e2 = m.encoder2(m.pool1(e1))
        e3 = m.encoder3(m.pool2(e2))
        e4 = m.encoder4(m.pool3(e3))
        bottleneck = m.bottleneck(m.pool4(e4))
        d4 = m.decoder4(torch.cat((m.upconv4(bottleneck), e4), dim=1))
        d3 = m.decoder3(torch.cat((m.upconv3(d4), e3), dim=1))
        d2 = m.decoder2(torch.cat((m.upconv2(d3), e2), dim=1))
        d1 = m.decoder1(torch.cat((m.upconv1(d2), e1), dim=1))
        return m.conv_s(d1)


def predict_building_probability(model, image, chip_size=256):
    if chip_size < 16 or chip_size % 16:
        raise ValueError("Chip size must be a positive multiple of 16")
    array = np.asarray(image, dtype=np.float32) / 255.
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("Expected RGB image")
    height, width = array.shape[:2]
    mean = array.mean(axis=(0, 1))
    std = array.std(axis=(0, 1)).clip(1e-6)
    normalized = (array-mean)/std
    padded = np.pad(normalized, ((0, (-height) % chip_size), (0, (-width) % chip_size), (0, 0)), mode="edge")
    result = np.zeros(padded.shape[:2], dtype=np.float32)
    model.eval()
    with torch.inference_mode():
        for y in range(0, padded.shape[0], chip_size):
            for x in range(0, padded.shape[1], chip_size):
                chip = torch.from_numpy(padded[y:y+chip_size, x:x+chip_size].copy()).permute(2, 0, 1)[None]
                logits = model(chip)
                if logits.shape[1] != 2:
                    raise ValueError("Expected background/building segmentation logits")
                result[y:y+chip_size, x:x+chip_size] = logits.softmax(1)[0, 1].numpy()
    return result[:height, :width]
