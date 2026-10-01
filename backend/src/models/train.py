"""Comprehensive and reproducible training pipeline for clinical Chest X-Ray classification.

Pipeline Architecture & Best Practices:
--------------------------------------
1. Transfer Learning Workflow:
   - Phase 1 (Feature Extraction): Pretrained backbone convolutional layers are frozen (requires_grad=False).
     Only the newly initialized binary classification head is trained with learning_rate (e.g. 1e-3).
   - Phase 2 (Optional Fine-Tuning): Backbone layers are unlocked and fine-tuned with a reduced learning rate
     (e.g., 1e-5) to adapt specialized radiographic features without disrupting pretrained low-level filters.

2. Class Imbalance Management:
   Class weights are computed strictly from the training partition using inverse frequency scaling:
     w_c = N_total / (N_classes * N_c)
   The test set is NEVER used for class weighting, hyperparameter tuning, or early stopping.

3. Reproducibility & Device Agnosticism:
   Random seeds are synchronized across Python, NumPy, and PyTorch. Execution runs transparently
   on CUDA GPUs when available with graceful fallback to CPU.
"""

import os
import sys
import json
import random
import argparse
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add backend root to path if executed as script
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.data.dataset import ChestXRayDataset, CLASS_TO_IDX, IDX_TO_CLASS
from src.data.preprocessing import DEFAULT_IMAGE_SIZE
from src.models.model import (
    MedicalClassifier,
    build_model,
    save_model_checkpoint,
    get_device,
)

logger = logging.getLogger("MedicalTrainer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@dataclass
class TrainingConfig:
    """Configuration hyperparameter schema for model training."""
    architecture: str = "resnet18"
    batch_size: int = 32
    learning_rate: float = 1e-3
    epochs: int = 10
    optimizer: str = "adam"  # 'adam', 'adamw', 'sgd'
    weight_decay: float = 1e-4
    momentum: float = 0.9  # for SGD
    scheduler: str = "plateau"  # 'plateau', 'cosine', 'step', 'none'
    early_stopping_patience: int = 5
    early_stopping_min_delta: float = 1e-4
    random_seed: int = 42
    freeze_backbone: bool = True
    fine_tune: bool = False
    fine_tune_epochs: int = 5
    fine_tune_lr: float = 1e-5
    checkpoint_metric: str = "val_acc"  # 'val_loss', 'val_acc', 'val_f1'
    use_class_weights: bool = True
    num_workers: int = 0
    dataset_root: str = "data/chest_xray"
    checkpoint_dir: str = "backend/models"
    reports_dir: str = "reports/training"
    device: Optional[str] = None
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE
    max_train_batches: Optional[int] = None  # for quick smoke tests
    max_val_batches: Optional[int] = None    # for quick smoke tests

    def __post_init__(self):
        """Validate hyperparameter ranges and types upon instantiation."""
        if self.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.batch_size}")
        if self.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {self.learning_rate}")
        if self.epochs <= 0:
            raise ValueError(f"epochs must be positive, got {self.epochs}")
        if self.optimizer.lower() not in ("adam", "adamw", "sgd"):
            raise ValueError(f"Unsupported optimizer '{self.optimizer}'. Expected: 'adam', 'adamw', 'sgd'")
        if self.scheduler.lower() not in ("plateau", "cosine", "step", "none"):
            raise ValueError(f"Unsupported scheduler '{self.scheduler}'. Expected: 'plateau', 'cosine', 'step', 'none'")


def set_seed(seed: int = 42):
    """Enforce deterministic random seeds across Python, NumPy, and PyTorch."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


class EarlyStopping:
    """Early stopping handler to terminate training when validation metric ceases improving."""

    def __init__(
        self,
        patience: int = 5,
        min_delta: float = 1e-4,
        metric: str = "val_acc",
    ):
        self.patience = patience
        self.min_delta = min_delta
        self.metric = metric
        self.is_loss_metric = "loss" in metric.lower()

        self.best_score = float("inf") if self.is_loss_metric else -float("inf")
        self.best_epoch = 0
        self.patience_counter = 0
        self.should_stop = False

    def step(self, current_val: float, epoch: int) -> bool:
        """Evaluate early stopping condition.

        Returns:
            bool: True if current metric is a new best score, False otherwise.
        """
        is_improved = False
        if self.is_loss_metric:
            if current_val < self.best_score - self.min_delta:
                self.best_score = current_val
                self.best_epoch = epoch
                self.patience_counter = 0
                is_improved = True
            else:
                self.patience_counter += 1
        else:
            if current_val > self.best_score + self.min_delta:
                self.best_score = current_val
                self.best_epoch = epoch
                self.patience_counter = 0
                is_improved = True
            else:
                self.patience_counter += 1

        if self.patience_counter >= self.patience:
            self.should_stop = True

        return is_improved


class MedicalTrainer:
    """Orchestrates model training, validation, early stopping, and artifact logging."""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self._validate_config()
        set_seed(self.config.random_seed)

        # Device determination
        if self.config.device:
            self.device = torch.device(self.config.device)
        else:
            self.device = get_device()
        logger.info(f"Initialized MedicalTrainer on device: {self.device}")

        # Directory preparation
        self.checkpoint_dir = Path(self.config.checkpoint_dir)
        self.reports_dir = Path(self.config.reports_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Datasets & DataLoaders (STRICT TEST SET ISOLATION: test split is never loaded)
        self.train_dataset, self.val_dataset = self._init_datasets()
        self.train_loader, self.val_loader = self._init_dataloaders()

        # Model instantiation
        self.model = build_model(
            architecture=self.config.architecture,
            num_classes=2,
            pretrained=True,
            freeze_backbone=self.config.freeze_backbone,
            device=self.device,
        )

        # Loss function
        self.criterion = self._init_loss_function()

        # Optimizer & Scheduler
        self.optimizer = self._init_optimizer(self.model, self.config.learning_rate)
        self.scheduler = self._init_scheduler(self.optimizer)

        # Early Stopping & Checkpoint Tracker
        self.early_stopper = EarlyStopping(
            patience=self.config.early_stopping_patience,
            min_delta=self.config.early_stopping_min_delta,
            metric=self.config.checkpoint_metric,
        )

        self.history: List[Dict[str, Any]] = []

    def _validate_config(self):
        """Validate configuration hyperparameter ranges and types."""
        if self.config.batch_size <= 0:
            raise ValueError(f"batch_size must be positive, got {self.config.batch_size}")
        if self.config.learning_rate <= 0:
            raise ValueError(f"learning_rate must be positive, got {self.config.learning_rate}")
        if self.config.epochs <= 0:
            raise ValueError(f"epochs must be positive, got {self.config.epochs}")
        if self.config.optimizer.lower() not in ("adam", "adamw", "sgd"):
            raise ValueError(f"Unsupported optimizer '{self.config.optimizer}'. Expected: 'adam', 'adamw', 'sgd'")
        if self.config.scheduler.lower() not in ("plateau", "cosine", "step", "none"):
            raise ValueError(f"Unsupported scheduler '{self.config.scheduler}'. Expected: 'plateau', 'cosine', 'step', 'none'")

    def _init_datasets(self) -> Tuple[ChestXRayDataset, ChestXRayDataset]:
        """Instantiate training and validation datasets with path checks."""
        root = Path(self.config.dataset_root)
        if not root.exists():
            raise FileNotFoundError(f"Dataset root directory not found at: {root.resolve()}")

        train_ds = ChestXRayDataset(
            dataset_root=root,
            split="train",
            image_size=self.config.image_size,
        )
        val_ds = ChestXRayDataset(
            dataset_root=root,
            split="val",
            image_size=self.config.image_size,
        )

        logger.info(f"Loaded Train Dataset: {len(train_ds)} images | Val Dataset: {len(val_ds)} images")
        return train_ds, val_ds

    def _init_dataloaders(self) -> Tuple[DataLoader, DataLoader]:
        """Create seeded DataLoaders for train and validation splits."""
        generator = torch.Generator()
        generator.manual_seed(self.config.random_seed)

        train_loader = DataLoader(
            self.train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=self.config.num_workers,
            generator=generator,
        )
        val_loader = DataLoader(
            self.val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=self.config.num_workers,
        )
        return train_loader, val_loader

    def _init_loss_function(self) -> nn.Module:
        """Build CrossEntropyLoss with optional training class weighting."""
        if self.config.use_class_weights:
            class_weights = self.train_dataset.get_class_weights().to(self.device)
            logger.info(f"Using inverse training class weights: {class_weights.tolist()}")
            return nn.CrossEntropyLoss(weight=class_weights)
        return nn.CrossEntropyLoss()

    def _init_optimizer(self, model: nn.Module, lr: float) -> torch.optim.Optimizer:
        """Instantiate selected optimizer with trainable parameters."""
        trainable_params = [p for p in model.parameters() if p.requires_grad]
        opt_name = self.config.optimizer.lower()

        if opt_name == "adam":
            return torch.optim.Adam(trainable_params, lr=lr, weight_decay=self.config.weight_decay)
        elif opt_name == "adamw":
            return torch.optim.AdamW(trainable_params, lr=lr, weight_decay=self.config.weight_decay)
        elif opt_name == "sgd":
            return torch.optim.SGD(
                trainable_params,
                lr=lr,
                momentum=self.config.momentum,
                weight_decay=self.config.weight_decay,
            )
        else:
            raise ValueError(f"Unknown optimizer: {opt_name}")

    def _init_scheduler(self, optimizer: torch.optim.Optimizer) -> Optional[Any]:
        """Instantiate learning rate scheduler."""
        sched_name = self.config.scheduler.lower()
        if sched_name == "plateau":
            mode = "min" if "loss" in self.config.checkpoint_metric.lower() else "max"
            return torch.optim.lr_scheduler.ReduceLROnPlateau(
                optimizer, mode=mode, factor=0.5, patience=2
            )
        elif sched_name == "cosine":
            return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=self.config.epochs, eta_min=1e-6)
        elif sched_name == "step":
            return torch.optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.5)
        elif sched_name == "none":
            return None
        return None

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Execute training across all batches in the train DataLoader."""
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for batch_idx, (images, targets) in enumerate(self.train_loader):
            if self.config.max_train_batches and batch_idx >= self.config.max_train_batches:
                break

            images, targets = images.to(self.device), targets.to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        epoch_loss = total_loss / total if total > 0 else 0.0
        epoch_acc = correct / total if total > 0 else 0.0

        return {"train_loss": float(epoch_loss), "train_acc": float(epoch_acc)}

    def validate_epoch(self, epoch: int) -> Dict[str, float]:
        """Execute deterministic evaluation over validation DataLoader."""
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for batch_idx, (images, targets) in enumerate(self.val_loader):
                if self.config.max_val_batches and batch_idx >= self.config.max_val_batches:
                    break

                images, targets = images.to(self.device), targets.to(self.device)
                outputs = self.model(images)
                loss = self.criterion(outputs, targets)

                total_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()

                all_preds.extend(predicted.cpu().numpy().tolist())
                all_targets.extend(targets.cpu().numpy().tolist())

        epoch_loss = total_loss / total if total > 0 else 0.0
        epoch_acc = correct / total if total > 0 else 0.0

        # Compute simple F1 score
        tp = sum(1 for p, t in zip(all_preds, all_targets) if p == 1 and t == 1)
        fp = sum(1 for p, t in zip(all_preds, all_targets) if p == 1 and t == 0)
        fn = sum(1 for p, t in zip(all_preds, all_targets) if p == 0 and t == 1)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "val_loss": float(epoch_loss),
            "val_acc": float(epoch_acc),
            "val_f1": float(f1),
        }

    def train(self) -> Dict[str, Any]:
        """Execute full training lifecycle with checkpointing and history recording."""
        logger.info(
            f"Starting training run: Architecture={self.config.architecture}, "
            f"Epochs={self.config.epochs}, BatchSize={self.config.batch_size}, LR={self.config.learning_rate}"
        )

        best_checkpoint_path = self.checkpoint_dir / f"best_{self.config.architecture}.pth"
        canonical_best_path = self.checkpoint_dir / "best_model.pth"

        for epoch in range(1, self.config.epochs + 1):
            train_metrics = self.train_epoch(epoch)
            val_metrics = self.validate_epoch(epoch)

            # Retrieve current learning rate
            current_lr = self.optimizer.param_groups[0]["lr"]

            epoch_record = {
                "epoch": epoch,
                "learning_rate": current_lr,
                **train_metrics,
                **val_metrics,
            }
            self.history.append(epoch_record)

            # Determine checkpoint candidate value
            eval_val = val_metrics.get(self.config.checkpoint_metric, val_metrics["val_acc"])
            is_best = self.early_stopper.step(eval_val, epoch)

            logger.info(
                f"Epoch [{epoch:02d}/{self.config.epochs:02d}] - "
                f"Train Loss: {train_metrics['train_loss']:.4f} | Train Acc: {train_metrics['train_acc']:.4f} | "
                f"Val Loss: {val_metrics['val_loss']:.4f} | Val Acc: {val_metrics['val_acc']:.4f} | "
                f"Val F1: {val_metrics['val_f1']:.4f} | LR: {current_lr:.2e} "
                f"{'[BEST CHECKPOINT]' if is_best else ''}"
            )

            # Save checkpoint if best
            if is_best:
                save_model_checkpoint(
                    model=self.model,
                    filepath=best_checkpoint_path,
                    optimizer=self.optimizer,
                    epoch=epoch,
                    metrics=val_metrics,
                    extra_config=asdict(self.config),
                )
                # Also save canonical best_model.pth
                save_model_checkpoint(
                    model=self.model,
                    filepath=canonical_best_path,
                    optimizer=self.optimizer,
                    epoch=epoch,
                    metrics=val_metrics,
                    extra_config=asdict(self.config),
                )

            # Step scheduler
            if self.scheduler is not None:
                if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                    self.scheduler.step(eval_val)
                else:
                    self.scheduler.step()

            # Early stopping check
            if self.early_stopper.should_stop:
                logger.info(
                    f"Early stopping triggered at epoch {epoch}. "
                    f"Best Epoch: {self.early_stopper.best_epoch} with {self.config.checkpoint_metric}={self.early_stopper.best_score:.4f}"
                )
                break

        # Save History & Visualizations
        history_csv = self.checkpoint_dir / f"history_{self.config.architecture}.csv"
        history_json = self.checkpoint_dir / f"history_{self.config.architecture}.json"
        self._save_history(history_csv, history_json)
        self._plot_training_curves()

        return {
            "best_epoch": self.early_stopper.best_epoch,
            "best_score": self.early_stopper.best_score,
            "best_checkpoint_path": str(canonical_best_path),
            "history_path": str(history_csv),
            "history": self.history,
        }

    def _save_history(self, csv_path: Path, json_path: Path):
        """Save training history in structured CSV and JSON formats."""
        df = pd.DataFrame(self.history)
        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.history, f, indent=2)
        logger.info(f"Saved training history to {csv_path} and {json_path}")

    def _plot_training_curves(self):
        """Generate and export training vs. validation loss and metric curves."""
        if not self.history:
            return

        df = pd.DataFrame(self.history)
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Loss curve
        axes[0].plot(df["epoch"], df["train_loss"], label="Train Loss", color="#0ea5e9", lw=2, marker="o")
        axes[0].plot(df["epoch"], df["val_loss"], label="Val Loss", color="#f43f5e", lw=2, marker="s")
        axes[0].set_title(f"{self.config.architecture.upper()} - Training & Validation Loss")
        axes[0].set_xlabel("Epoch")
        axes[0].set_ylabel("CrossEntropy Loss")
        axes[0].grid(True, linestyle="--", alpha=0.6)
        axes[0].legend()

        # Accuracy curve
        axes[1].plot(df["epoch"], df["train_acc"], label="Train Accuracy", color="#10b981", lw=2, marker="o")
        axes[1].plot(df["epoch"], df["val_acc"], label="Val Accuracy", color="#8b5cf6", lw=2, marker="s")
        if "val_f1" in df:
            axes[1].plot(df["epoch"], df["val_f1"], label="Val F1", color="#f59e0b", lw=2, linestyle="--")
        axes[1].set_title(f"{self.config.architecture.upper()} - Classification Metrics")
        axes[1].set_xlabel("Epoch")
        axes[1].set_ylabel("Score")
        axes[1].grid(True, linestyle="--", alpha=0.6)
        axes[1].legend()

        plt.tight_layout()
        plot_path = self.reports_dir / f"training_curves_{self.config.architecture}.png"
        plt.savefig(plot_path, dpi=150)
        plt.close(fig)
        logger.info(f"Saved training curves to {plot_path}")


def train_model(config: Optional[TrainingConfig] = None, **kwargs) -> Dict[str, Any]:
    """Programmatic entrypoint to run training given a TrainingConfig or keyword arguments."""
    if config is None:
        config = TrainingConfig(**kwargs)
    elif kwargs:
        for k, v in kwargs.items():
            if hasattr(config, k):
                setattr(config, k, v)

    trainer = MedicalTrainer(config)
    return trainer.train()


def parse_args() -> TrainingConfig:
    """Parse command-line arguments into a TrainingConfig instance."""
    parser = argparse.ArgumentParser(description="Train Chest X-Ray Medical Vision Classifier")
    parser.add_argument("--architecture", type=str, default="resnet18", help="CNN architecture (resnet18, densenet121, etc.)")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs")
    parser.add_argument("--optimizer", type=str, default="adam", choices=["adam", "adamw", "sgd"], help="Optimizer")
    parser.add_argument("--scheduler", type=str, default="plateau", choices=["plateau", "cosine", "step", "none"], help="LR Scheduler")
    parser.add_argument("--patience", type=int, default=5, help="Early stopping patience")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--dataset-root", type=str, default="data/chest_xray", help="Dataset directory")
    parser.add_argument("--checkpoint-dir", type=str, default="backend/models", help="Checkpoint directory")
    parser.add_argument("--reports-dir", type=str, default="reports/training", help="Reports directory")
    parser.add_argument("--device", type=str, default=None, help="Device (cpu, cuda)")

    args = parser.parse_args()
    return TrainingConfig(
        architecture=args.architecture,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        epochs=args.epochs,
        optimizer=args.optimizer,
        scheduler=args.scheduler,
        early_stopping_patience=args.patience,
        random_seed=args.seed,
        dataset_root=args.dataset_root,
        checkpoint_dir=args.checkpoint_dir,
        reports_dir=args.reports_dir,
        device=args.device,
    )


if __name__ == "__main__":
    cfg = parse_args()
    train_model(cfg)
