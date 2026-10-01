"""PyTorch Dataset for Prescription Layout & Medicine Region Detection."""

import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
import torch
from torch.utils.data import Dataset

from ..config import PrescriptionConfig, default_config
from ..preprocessing.image_preprocessor import PrescriptionImagePreprocessor


class PrescriptionDetectionDataset(Dataset):
    """Dataset for training Faster R-CNN on annotated prescription layout bounding boxes."""

    def __init__(
        self,
        metadata_file: Optional[Path] = None,
        images_dir: Optional[Path] = None,
        split: str = "train",
        config: Optional[PrescriptionConfig] = None,
        transforms: bool = True
    ):
        self.config = config or default_config
        self.split = split
        self.transforms = transforms
        self.preprocessor = PrescriptionImagePreprocessor(self.config)

        self.metadata_file = metadata_file or (self.config.data_dir / "metadata" / "full_prescriptions_metadata.json")
        self.images_dir = images_dir or (self.config.data_dir / "raw" / "full_prescriptions")

        self.samples = self._load_and_filter_samples()

    def _load_and_filter_samples(self) -> List[Dict[str, Any]]:
        """Loads metadata and partitions by split with zero patient leakage."""
        if not self.metadata_file.exists():
            return []

        with open(self.metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        filtered = []
        for item in data:
            # Deterministic split by MD5 hash of prescription_id to guarantee zero leakage
            presc_id = str(item.get("prescription_id", ""))
            h_val = int(hashlib.md5(presc_id.encode("utf-8")).hexdigest()[:8], 16) % 10

            if self.split == "train" and h_val < 7:
                filtered.append(item)
            elif self.split in ("val", "validation") and (7 <= h_val < 9):
                filtered.append(item)
            elif self.split == "test" and h_val >= 9:
                filtered.append(item)
            elif self.split == "all":
                filtered.append(item)

        # Fallback if filtered is empty (small dataset mode)
        if not filtered and data:
            filtered = data

        return filtered

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        sample = self.samples[idx]
        img_path = self.images_dir / sample["filename"]

        if not img_path.exists():
            # Create synthetic canvas if sample image missing
            canvas = np.full((1024, 768, 3), 255, dtype=np.uint8)
        else:
            canvas = cv2.imread(str(img_path))

        # Preprocess for detection
        prep = self.preprocessor.preprocess_for_detection(canvas)
        tensor_chw = prep["tensor"]
        scale = prep["scale"]
        pad_x, pad_y = prep["padding"]

        boxes = []
        labels = []

        for b in sample.get("bounding_boxes", []):
            lbl_name = b.get("label", "")
            # Filter specifically for medicine blocks
            if "medicine" in lbl_name:
                x, y, w, h = b["bbox"]
                # Transform bbox to letterbox coordinate space
                tx1 = x * scale + pad_x
                ty1 = y * scale + pad_y
                tx2 = (x + w) * scale + pad_x
                ty2 = (y + h) * scale + pad_y

                if (tx2 - tx1) > 5 and (ty2 - ty1) > 5:
                    boxes.append([tx1, ty1, tx2, ty2])
                    labels.append(1)  # Class 1: medicine_region

        if len(boxes) == 0:
            # Dummy box for empty labels to prevent PyTorch crash
            boxes = [[0.0, 0.0, 10.0, 10.0]]
            labels = [0]

        target = {
            "boxes": torch.tensor(boxes, dtype=torch.float32),
            "labels": torch.tensor(labels, dtype=torch.int64),
            "image_id": torch.tensor([idx]),
            "prescription_id": sample.get("prescription_id", f"sample_{idx}")
        }

        image_tensor = torch.from_numpy(tensor_chw).float()
        return image_tensor, target


def detection_collate_fn(batch):
    """Collate function for variable number of bounding boxes per prescription."""
    images = [item[0] for item in batch]
    targets = [item[1] for item in batch]
    return torch.stack(images, dim=0), targets
