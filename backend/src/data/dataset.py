"""PyTorch Dataset implementations and DataLoader builders for Chest X-Ray studies.

Features:
---------
1. Strict class indexing: NORMAL -> 0, PNEUMONIA -> 1.
2. Dataset partition validation (verifies directory existence, non-empty files, supported extensions).
3. Graceful error handling for corrupted/unreadable images with explicit warnings.
4. Reproducible DataLoader construction with configurable batch size, num_workers, and seeds.
5. Strict test-set isolation: test split remains purely deterministic and isolated.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Callable, Tuple, Dict, List, Any
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image

from .preprocessing import get_transforms, DEFAULT_IMAGE_SIZE

logger = logging.getLogger(__name__)

# Strict canonical class-to-index mapping
CLASS_TO_IDX: Dict[str, int] = {
    "NORMAL": 0,
    "PNEUMONIA": 1,
}

IDX_TO_CLASS: Dict[int, str] = {
    0: "NORMAL",
    1: "PNEUMONIA",
}

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


class ChestXRayDataset(Dataset):
    """PyTorch Dataset representing a partitioned collection of Chest X-Ray images."""

    def __init__(
        self,
        dataset_root: str | Path = "data/chest_xray",
        split: str = "train",
        transform: Optional[Callable] = None,
        image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    ):
        """Initialize ChestXRayDataset.

        Args:
            dataset_root: Path to the chest_xray directory.
            split: One of 'train', 'val' (or 'validation'), 'test'.
            transform: Custom torchvision transform. If None, default transforms for split are used.
            image_size: Target image size (H, W) if building default transform.
        """
        self.dataset_root = Path(dataset_root)
        self.raw_split = split
        self.split = "val" if split.lower() in ("val", "validation") else split.lower()
        self.image_size = image_size

        # Default transform pipeline if none supplied
        self.transform = transform if transform is not None else get_transforms(
            split=self.split,
            image_size=self.image_size
        )

        self.samples: List[Tuple[Path, int]] = []
        self.corrupted_files: List[Tuple[Path, str]] = []

        self._validate_and_index()

    def _validate_and_index(self):
        """Verify directories and index all valid image files."""
        if not self.dataset_root.exists():
            raise FileNotFoundError(
                f"Dataset root directory does not exist: {self.dataset_root.resolve()}"
            )

        split_dir = self.dataset_root / self.split
        if not split_dir.exists():
            # Check for alternative naming
            alt_name = "validation" if self.split == "val" else ("val" if self.split == "validation" else None)
            if alt_name and (self.dataset_root / alt_name).exists():
                split_dir = self.dataset_root / alt_name
            else:
                raise FileNotFoundError(
                    f"Dataset split directory not found: {split_dir.resolve()}"
                )

        # Check classes exist
        for class_name, class_idx in CLASS_TO_IDX.items():
            class_dir = split_dir / class_name
            if not class_dir.exists():
                raise FileNotFoundError(
                    f"Expected class directory missing: {class_dir.resolve()}"
                )

            # Index files
            for file_path in sorted(class_dir.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                    self.samples.append((file_path, class_idx))

        if len(self.samples) == 0:
            raise ValueError(
                f"Dataset split '{self.split}' in {split_dir.resolve()} contains 0 valid images."
            )

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """Fetch and preprocess a single sample.

        Returns:
            Tuple of (image_tensor: torch.Tensor, label: int)
        """
        image_path, label = self.samples[idx]

        try:
            # Open with PIL and convert to RGB (standardizes 1-channel grayscale and 3-channel RGB)
            with Image.open(image_path) as raw_img:
                image = raw_img.convert("RGB")
        except Exception as e:
            logger.error(f"Error reading image {image_path}: {e}")
            self.corrupted_files.append((image_path, str(e)))
            # Return a blank tensor fallback in extreme rare runtime corruption
            image = Image.new("RGB", self.image_size, (0, 0, 0))

        if self.transform is not None:
            image = self.transform(image)

        return image, label

    def get_class_distribution(self) -> Dict[str, int]:
        """Compute distribution of classes in this dataset split."""
        distribution: Dict[str, int] = {c: 0 for c in CLASS_TO_IDX.keys()}
        for _, label_idx in self.samples:
            class_name = IDX_TO_CLASS[label_idx]
            distribution[class_name] += 1
        return distribution

    def get_class_weights(self) -> torch.Tensor:
        """Calculate inverse frequency weights for class-imbalanced loss functions."""
        dist = self.get_class_distribution()
        total = len(self.samples)
        num_classes = len(CLASS_TO_IDX)
        weights = [total / (num_classes * dist[IDX_TO_CLASS[i]]) for i in range(num_classes)]
        return torch.tensor(weights, dtype=torch.float32)


# Backwards-compatible alias
MedicalImageDataset = ChestXRayDataset


def create_dataloaders(
    dataset_root: str | Path = "data/chest_xray",
    batch_size: int = 32,
    num_workers: int = 0,
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
    seed: int = 42,
    pin_memory: bool = False,
) -> Dict[str, DataLoader]:
    """Create reproducible PyTorch DataLoaders for train, validation, and test splits.

    Args:
        dataset_root: Path to chest_xray directory.
        batch_size: Batch size for DataLoader.
        num_workers: Number of background DataLoader subprocesses.
        image_size: Target spatial dimensions (H, W).
        seed: Random seed for shuffling reproducibility.
        pin_memory: Whether to copy Tensors into CUDA pinned memory.

    Returns:
        Dictionary mapping {'train': DataLoader, 'val': DataLoader, 'test': DataLoader}.
    """
    # Set seed for generator
    generator = torch.Generator()
    generator.manual_seed(seed)

    train_dataset = ChestXRayDataset(
        dataset_root=dataset_root,
        split="train",
        image_size=image_size
    )

    val_dataset = ChestXRayDataset(
        dataset_root=dataset_root,
        split="val",
        image_size=image_size
    )

    test_dataset = ChestXRayDataset(
        dataset_root=dataset_root,
        split="test",
        image_size=image_size
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=pin_memory,
        generator=generator,
        drop_last=False,
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )

    return {
        "train": train_loader,
        "val": val_loader,
        "test": test_loader,
    }
