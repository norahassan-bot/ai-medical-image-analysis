import pytest
from pathlib import Path
import torch
from PIL import Image

from src.data.dataset import (
    ChestXRayDataset,
    create_dataloaders,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
)
from src.data.preprocessing import (
    get_transforms,
    get_train_transforms,
    get_eval_transforms,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_IMAGENET_MEAN,
    DEFAULT_IMAGENET_STD,
)

DATASET_ROOT = Path("data/chest_xray")


def test_class_mapping():
    """Verify standard canonical class index mapping."""
    assert CLASS_TO_IDX["NORMAL"] == 0
    assert CLASS_TO_IDX["PNEUMONIA"] == 1
    assert IDX_TO_CLASS[0] == "NORMAL"
    assert IDX_TO_CLASS[1] == "PNEUMONIA"


def test_dataset_splits_loading():
    """Verify that all splits can be instantiated with correct counts."""
    if not DATASET_ROOT.exists():
        pytest.skip(f"Dataset root not found at {DATASET_ROOT}")

    train_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="train")
    val_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="val")
    test_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="test")

    assert len(train_ds) == 5216
    assert len(val_ds) == 16
    assert len(test_ds) == 624

    # Class distributions
    train_dist = train_ds.get_class_distribution()
    assert train_dist["NORMAL"] == 1341
    assert train_dist["PNEUMONIA"] == 3875

    val_dist = val_ds.get_class_distribution()
    assert val_dist["NORMAL"] == 8
    assert val_dist["PNEUMONIA"] == 8

    test_dist = test_ds.get_class_distribution()
    assert test_dist["NORMAL"] == 234
    assert test_dist["PNEUMONIA"] == 390


def test_dataset_item_shape_and_dtype():
    """Verify single sample tensor shape (3, H, W) and float32 dtype."""
    if not DATASET_ROOT.exists():
        pytest.skip(f"Dataset root not found at {DATASET_ROOT}")

    val_ds = ChestXRayDataset(
        dataset_root=DATASET_ROOT,
        split="val",
        image_size=(224, 224)
    )

    img_tensor, label = val_ds[0]

    assert isinstance(img_tensor, torch.Tensor)
    assert img_tensor.shape == (3, 224, 224)
    assert img_tensor.dtype == torch.float32
    assert label in (0, 1)


def test_eval_transforms_are_deterministic():
    """Verify that validation/test transforms produce identical outputs for identical inputs."""
    eval_transform = get_eval_transforms(image_size=(224, 224))

    # Create dummy PIL test image
    test_img = Image.new("RGB", (300, 400), color=(128, 128, 128))

    t1 = eval_transform(test_img)
    t2 = eval_transform(test_img)

    assert torch.allclose(t1, t2), "Evaluation transforms must be strictly deterministic"


def test_dataloaders_creation_and_batch_iteration():
    """Verify batch iteration from train, validation, and test DataLoaders."""
    if not DATASET_ROOT.exists():
        pytest.skip(f"Dataset root not found at {DATASET_ROOT}")

    batch_size = 16
    loaders = create_dataloaders(
        dataset_root=DATASET_ROOT,
        batch_size=batch_size,
        num_workers=0,
        image_size=(224, 224),
        seed=42,
    )

    assert "train" in loaders
    assert "val" in loaders
    assert "test" in loaders

    # Test train batch
    train_images, train_labels = next(iter(loaders["train"]))
    assert train_images.shape == (batch_size, 3, 224, 224)
    assert train_images.dtype == torch.float32
    assert train_labels.shape == (batch_size,)

    # Test val batch
    val_images, val_labels = next(iter(loaders["val"]))
    assert val_images.shape == (batch_size, 3, 224, 224)
    assert val_labels.shape == (batch_size,)

    # Test test batch
    test_images, test_labels = next(iter(loaders["test"]))
    assert test_images.shape == (batch_size, 3, 224, 224)
    assert test_labels.shape == (batch_size,)


def test_missing_and_empty_dataset_handling(tmp_path):
    """Verify that nonexistent directories or empty splits raise explicit FileNotFoundError/ValueError."""
    with pytest.raises(FileNotFoundError):
        ChestXRayDataset(dataset_root=tmp_path / "nonexistent", split="train")

    empty_root = tmp_path / "empty_dataset"
    empty_root.mkdir()
    (empty_root / "train" / "NORMAL").mkdir(parents=True)
    (empty_root / "train" / "PNEUMONIA").mkdir(parents=True)

    with pytest.raises(ValueError, match="contains 0 valid images"):
        ChestXRayDataset(dataset_root=empty_root, split="train")


def test_test_set_isolation():
    """Verify that test dataset path paths do not overlap with train or val."""
    if not DATASET_ROOT.exists():
        pytest.skip(f"Dataset root not found at {DATASET_ROOT}")

    train_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="train")
    val_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="val")
    test_ds = ChestXRayDataset(dataset_root=DATASET_ROOT, split="test")

    train_paths = set(p for p, _ in train_ds.samples)
    val_paths = set(p for p, _ in val_ds.samples)
    test_paths = set(p for p, _ in test_ds.samples)

    assert len(train_paths.intersection(val_paths)) == 0, "Train and Val splits must not overlap"
    assert len(train_paths.intersection(test_paths)) == 0, "Train and Test splits must not overlap"
    assert len(val_paths.intersection(test_paths)) == 0, "Val and Test splits must not overlap"
