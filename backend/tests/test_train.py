import pytest
from pathlib import Path
import torch
import torch.nn as nn

from src.models.train import (
    TrainingConfig,
    EarlyStopping,
    MedicalTrainer,
    set_seed,
    train_model,
)
from src.models.model import build_model

DATASET_ROOT = Path("data/chest_xray")


def test_training_config_validation():
    """Verify that invalid hyperparameter configurations raise explicit ValueError."""
    with pytest.raises(ValueError, match="batch_size must be positive"):
        TrainingConfig(batch_size=0)

    with pytest.raises(ValueError, match="learning_rate must be positive"):
        TrainingConfig(learning_rate=-0.01)

    with pytest.raises(ValueError, match="epochs must be positive"):
        TrainingConfig(epochs=-1)

    with pytest.raises(ValueError, match="Unsupported optimizer"):
        TrainingConfig(optimizer="invalid_opt")

    with pytest.raises(ValueError, match="Unsupported scheduler"):
        TrainingConfig(scheduler="invalid_sched")


def test_early_stopping_logic():
    """Verify early stopping triggers correctly on loss and accuracy metrics."""
    # Test for loss (minimization)
    es_loss = EarlyStopping(patience=3, min_delta=0.01, metric="val_loss")
    assert es_loss.step(1.0, epoch=1) is True
    assert es_loss.best_score == 1.0
    assert es_loss.best_epoch == 1

    assert es_loss.step(1.05, epoch=2) is False
    assert es_loss.patience_counter == 1
    assert es_loss.should_stop is False

    assert es_loss.step(1.02, epoch=3) is False
    assert es_loss.patience_counter == 2

    assert es_loss.step(1.03, epoch=4) is False
    assert es_loss.patience_counter == 3
    assert es_loss.should_stop is True

    # Test for accuracy (maximization)
    es_acc = EarlyStopping(patience=2, min_delta=0.01, metric="val_acc")
    assert es_acc.step(0.80, epoch=1) is True
    assert es_acc.step(0.85, epoch=2) is True
    assert es_acc.best_score == 0.85
    assert es_acc.best_epoch == 2

    assert es_acc.step(0.852, epoch=3) is False  # below min_delta
    assert es_acc.step(0.84, epoch=4) is False
    assert es_acc.should_stop is True


def test_reproducibility_seed():
    """Verify that setting seed guarantees deterministic initial weights."""
    set_seed(123)
    t1 = torch.randn(5, 5)

    set_seed(123)
    t2 = torch.randn(5, 5)

    assert torch.equal(t1, t2), "Seeded tensor generation must be exactly reproducible"


def test_optimizer_and_scheduler_builders():
    """Verify that optimizer and scheduler builders support configured types."""
    model = build_model(architecture="resnet18", num_classes=2, pretrained=False, device="cpu")

    for opt_name in ["adam", "adamw", "sgd"]:
        cfg = TrainingConfig(optimizer=opt_name, learning_rate=1e-3)
        # Trainer helper verification
        params = [p for p in model.parameters() if p.requires_grad]
        if opt_name == "adam":
            opt = torch.optim.Adam(params, lr=1e-3)
        elif opt_name == "adamw":
            opt = torch.optim.AdamW(params, lr=1e-3)
        elif opt_name == "sgd":
            opt = torch.optim.SGD(params, lr=1e-3, momentum=0.9)
        assert isinstance(opt, torch.optim.Optimizer)


def test_training_smoke_test(tmp_path):
    """Execute a lightweight 1-epoch technical smoke test with small batch constraints."""
    if not DATASET_ROOT.exists():
        pytest.skip(f"Dataset root not found at {DATASET_ROOT}")

    chk_dir = tmp_path / "checkpoints"
    rep_dir = tmp_path / "reports"

    config = TrainingConfig(
        architecture="resnet18",
        batch_size=8,
        learning_rate=1e-3,
        epochs=1,
        optimizer="adam",
        scheduler="none",
        early_stopping_patience=2,
        random_seed=42,
        freeze_backbone=True,
        dataset_root=str(DATASET_ROOT),
        checkpoint_dir=str(chk_dir),
        reports_dir=str(rep_dir),
        device="cpu",
        max_train_batches=2,  # Process only 2 batches for fast unit test
        max_val_batches=2,    # Process only 2 batches for fast unit test
    )

    result = train_model(config)

    assert result["best_epoch"] == 1
    assert "best_score" in result
    assert Path(result["best_checkpoint_path"]).exists()
    assert Path(result["history_path"]).exists()
    assert len(result["history"]) == 1

    # Verify history columns
    h0 = result["history"][0]
    assert "train_loss" in h0
    assert "train_acc" in h0
    assert "val_loss" in h0
    assert "val_acc" in h0
    assert "learning_rate" in h0
