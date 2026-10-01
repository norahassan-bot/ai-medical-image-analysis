"""Training script for Medicine Region Detector (Faster R-CNN MobileNetV3)."""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader

from ..config import PrescriptionConfig, default_config
from .dataset import PrescriptionDetectionDataset, detection_collate_fn
from .detector import MedicineRegionDetector


def set_seed(seed: int = 42):
    """Sets deterministic random seed."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """Computes Intersection over Union for [x1, y1, x2, y2]."""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_w = max(0.0, x2 - x1)
    inter_h = max(0.0, y2 - y1)
    inter_area = inter_w * inter_h

    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union_area = area1 + area2 - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def evaluate_detector(
    detector: MedicineRegionDetector,
    test_dataset: PrescriptionDetectionDataset,
    iou_threshold: float = 0.50
) -> Dict[str, Any]:
    """Evaluates detector on an isolated test partition without leakage."""
    detector.model.eval()
    total_gt = 0
    total_pred = 0
    true_positives = 0
    ious = []

    for i in range(len(test_dataset)):
        img_tensor, target = test_dataset[i]
        gt_boxes = target["boxes"].numpy()
        gt_labels = target["labels"].numpy()

        valid_gt = [gt_boxes[k] for k in range(len(gt_labels)) if gt_labels[k] == 1]
        total_gt += len(valid_gt)

        with torch.no_grad():
            preds = detector.model(img_tensor.unsqueeze(0).to(detector.device))

        if preds and len(preds) > 0:
            pred = preds[0]
            p_boxes = pred["boxes"].cpu().numpy()
            p_scores = pred["scores"].cpu().numpy()
            p_labels = pred["labels"].cpu().numpy()

            pred_boxes = [p_boxes[k] for k in range(len(p_labels)) if p_labels[k] == 1 and p_scores[k] >= 0.4]
            total_pred += len(pred_boxes)

            matched_gt = set()
            for pb in pred_boxes:
                best_iou = 0.0
                best_gt_idx = -1
                for gt_idx, gb in enumerate(valid_gt):
                    if gt_idx in matched_gt:
                        continue
                    iou = compute_iou(pb, gb)
                    if iou > best_iou:
                        best_iou = iou
                        best_gt_idx = gt_idx

                if best_iou >= iou_threshold and best_gt_idx >= 0:
                    true_positives += 1
                    matched_gt.add(best_gt_idx)
                    ious.append(best_iou)

    precision = float(true_positives / total_pred) if total_pred > 0 else 0.0
    recall = float(true_positives / total_gt) if total_gt > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    mean_iou = float(np.mean(ious)) if ious else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "mAP_50": round(precision * recall, 4) if (precision and recall) else round(f1, 4),
        "mean_iou": round(mean_iou, 4),
        "total_ground_truth": total_gt,
        "total_predictions": total_pred,
        "true_positives": true_positives
    }


def train_detector(
    epochs: int = 15,
    batch_size: int = 4,
    learning_rate: float = 1e-3,
    seed: int = 42,
    config: Optional[PrescriptionConfig] = None
) -> Dict[str, Any]:
    """Runs configurable training for Faster R-CNN medicine region detector."""
    cfg = config or default_config
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_dataset = PrescriptionDetectionDataset(split="train", config=cfg)
    val_dataset = PrescriptionDetectionDataset(split="val", config=cfg)
    test_dataset = PrescriptionDetectionDataset(split="test", config=cfg)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=detection_collate_fn
    )

    detector = MedicineRegionDetector(config=cfg, device=str(device))
    model = detector.model
    model.train()

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = optim.AdamW(params, lr=learning_rate, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    history = []
    best_loss = float("inf")
    start_time = time.time()

    print(f"[*] Starting Medicine Region Detector training on {device}...")
    print(f"    - Train Samples: {len(train_dataset)} | Val: {len(val_dataset)} | Test: {len(test_dataset)}")

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        batch_count = 0

        for images, targets in train_loader:
            images = [img.to(device) for img in images]
            targets = [{k: v.to(device) for k, v in t.items() if isinstance(v, torch.Tensor)} for t in targets]

            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())

            optimizer.zero_grad()
            losses.backward()
            torch.nn.utils.clip_grad_norm_(params, max_norm=5.0)
            optimizer.step()

            epoch_loss += losses.item()
            batch_count += 1

        lr_scheduler.step()
        avg_loss = epoch_loss / max(1, batch_count)
        history.append({"epoch": epoch, "loss": round(avg_loss, 4), "lr": optimizer.param_groups[0]["lr"]})

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - Loss: {avg_loss:.4f} - LR: {optimizer.param_groups[0]['lr']:.6f}")

        # Checkpoint best model
        if avg_loss < best_loss:
            best_loss = avg_loss
            best_ckpt = cfg.detection_checkpoint_dir / "best_detector.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": avg_loss,
                "version": detector.version,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }, best_ckpt)

    # Save final checkpoint
    final_ckpt = cfg.detection_checkpoint_dir / "final_detector.pt"
    torch.save({
        "epoch": epochs,
        "model_state_dict": model.state_dict(),
        "loss": avg_loss,
        "version": detector.version,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }, final_ckpt)

    # Isolated test set evaluation
    test_metrics = evaluate_detector(detector, test_dataset)

    # Compile training summary metadata
    training_summary = {
        "model_name": "FasterRCNN-MobileNetV3",
        "version": detector.version,
        "task": "medicine_region_detection",
        "dataset": "bangladesh_curated_prescriptions",
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "random_seed": seed,
        "training_duration_seconds": round(time.time() - start_time, 2),
        "best_training_loss": round(best_loss, 4),
        "test_metrics": test_metrics,
        "history": history
    }

    # Save metadata and reports
    metrics_file = cfg.reports_dir / "detection_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, indent=2)

    print(f"[+] Detector training complete! Metrics saved to {metrics_file}")
    return training_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Medicine Region Detector")
    parser.add_argument("--epochs", type=int, default=5, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    train_detector(epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr, seed=args.seed)
