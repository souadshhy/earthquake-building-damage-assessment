import math
import random
from functools import lru_cache

import numpy as np
import torch
from PIL import Image, ImageOps
from torch.utils.data import Dataset

MEAN = torch.tensor([0.485, 0.456, 0.406])[:, None, None]
STD = torch.tensor([0.229, 0.224, 0.225])[:, None, None]


def crop_pair(before, after, bbox, augment=False):
    x1, y1, x2, y2 = bbox
    if not all(math.isfinite(v) for v in bbox) or x2 <= x1 or y2 <= y1:
        raise ValueError("Invalid crop bounding box")
    dx, dy = (x2 - x1) * 0.2, (y2 - y1) * 0.2
    box = (math.floor(x1-dx), math.floor(y1-dy), math.ceil(x2+dx), math.ceil(y2+dy))
    images = [im.crop(box).resize((224, 224), Image.Resampling.BILINEAR) for im in (before, after)]
    if augment:
        horizontal, vertical, angle = random.random() < .5, random.random() < .5, random.choice([0, 90, 180, 270])
        images = [im.rotate(angle) for im in images]
        if horizontal:
            images = [ImageOps.mirror(im) for im in images]
        if vertical:
            images = [ImageOps.flip(im) for im in images]
    return tuple((torch.from_numpy(np.asarray(im, dtype=np.float32).copy()).permute(2, 0, 1) / 255 - MEAN) / STD for im in images)


class BuildingDataset(Dataset):
    def __init__(self, rows, augment=False):
        self.rows, self.augment = rows, augment

    @staticmethod
    @lru_cache(maxsize=12)
    def image(path):
        with Image.open(path) as image:
            return image.convert("RGB")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        before, after = crop_pair(self.image(row["before"]), self.image(row["after"]), row["bbox"], self.augment)
        return before, after, row["class_index"]
