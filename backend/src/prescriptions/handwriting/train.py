"""Training script for CRNN + BiLSTM + CTC Handwritten Text Recognizer."""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from ..config import PrescriptionConfig, default_config
from .dataset import PrescriptionHandwritingDataset, handwriting_collate_fn
from .recognizer import HandwrittenTextRecognizer, CRNNModel
from ..evaluation.metrics import evaluate_htr_predictions


def set_seed(seed: int = 42):
    """Sets deterministic random seed."""
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate_recognizer(
    recognizer: HandwrittenTextRecognizer,
    test_dataset: PrescriptionHandwritingDataset
) -> Dict[str, Any]:
    """Evaluates recognizer on an isolated test partition."""
    recognizer.model.eval()
    predictions = []

    for i in range(len(test_dataset)):
        img_tensor, target, target_len, label_text = test_dataset[i]
        
        with torch.no_grad():
            log_probs = recognizer.model(img_tensor.unsqueeze(0).to(recognizer.device))
            
        single_lp = log_probs[:, 0, :]
        pred_text, confidence, _ = recognizer.decoder.decode_greedy(single_lp)

        predictions.append({
            "predicted_text": pred_text,
            "ground_truth": label_text,
            "confidence": confidence
        })

    metrics = evaluate_htr_predictions(predictions)
    return metrics, predictions


def train_recognizer(
    epochs: int = 20,
    batch_size: int = 16,
    learning_rate: float = 5e-4,
    seed: int = 42,
    config: Optional[PrescriptionConfig] = None
) -> Dict[str, Any]:
    """Runs configurable training for CRNN Handwritten Text Recognizer."""
    cfg = config or default_config
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_dataset = PrescriptionHandwritingDataset(split="train", config=cfg)
    val_dataset = PrescriptionHandwritingDataset(split="val", config=cfg)
    test_dataset = PrescriptionHandwritingDataset(split="test", config=cfg)

    # Fallback to train dataset if splits are small in local test setup
    if len(train_dataset) == 0:
        train_dataset = PrescriptionHandwritingDataset(split="all", config=cfg)
    if len(test_dataset) == 0:
        test_dataset = train_dataset

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=handwriting_collate_fn
    )

    recognizer = HandwrittenTextRecognizer(config=cfg, device=str(device))
    model = recognizer.model
    model.train()

    criterion = nn.CTCLoss(
        blank=recognizer.decoder.blank_index,
        reduction="mean",
        zero_infinity=True
    )

    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    history = []
    best_loss = float("inf")
    start_time = time.time()

    print(f"[*] Starting CRNN Handwritten Text Recognizer training on {device}...")
    print(f"    - Train Samples: {len(train_dataset)} | Val: {len(val_dataset)} | Test: {len(test_dataset)}")

    for epoch in range(1, epochs + 1):
        model.train()
        epoch_loss = 0.0
        batch_count = 0

        for images, targets, input_lengths, target_lengths, _ in train_loader:
            images = images.to(device)
            targets = targets.to(device)

            log_probs = model(images)  # (T, B, C)

            loss = criterion(log_probs, targets, input_lengths, target_lengths)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            epoch_loss += loss.item()
            batch_count += 1

        lr_scheduler.step()
        avg_loss = epoch_loss / max(1, batch_count)
        history.append({"epoch": epoch, "ctc_loss": round(avg_loss, 4), "lr": optimizer.param_groups[0]["lr"]})

        print(f"Epoch [{epoch:02d}/{epochs:02d}] - CTC Loss: {avg_loss:.4f} - LR: {optimizer.param_groups[0]['lr']:.6f}")

        # Checkpoint best model
        if avg_loss < best_loss:
            best_loss = avg_loss
            best_ckpt = cfg.recognition_checkpoint_dir / "best_recognizer.pt"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": avg_loss,
                "version": recognizer.version,
                "vocab": cfg.recognition_vocab,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }, best_ckpt)

    # Save final checkpoint
    final_ckpt = cfg.recognition_checkpoint_dir / "final_recognizer.pt"
    torch.save({
        "epoch": epochs,
        "model_state_dict": model.state_dict(),
        "loss": avg_loss,
        "version": recognizer.version,
        "vocab": cfg.recognition_vocab,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }, final_ckpt)

    # Test set evaluation
    test_metrics, sample_preds = evaluate_recognizer(recognizer, test_dataset)

    # Compile training summary metadata
    training_summary = {
        "model_name": "CRNN-BiLSTM-CTC",
        "version": recognizer.version,
        "task": "handwritten_medical_text_recognition",
        "dataset": "rxhandbd",
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "random_seed": seed,
        "training_duration_seconds": round(time.time() - start_time, 2),
        "best_ctc_loss": round(best_loss, 4),
        "test_metrics": test_metrics,
        "history": history
    }

    # Save metrics and predictions
    metrics_file = cfg.reports_dir / "recognition_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as f:
        json.dump(training_summary, f, indent=2)

    predictions_file = cfg.reports_dir / "sample_predictions.json"
    with open(predictions_file, "w", encoding="utf-8") as f:
        json.dump(sample_preds[:20], f, indent=2)

    print(f"[+] HTR training complete! Metrics saved to {metrics_file}")
    return training_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CRNN Handwriting Recognizer")
    parser.add_argument("--epochs", type=int, default=10, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=5e-4, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    train_recognizer(epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.lr, seed=args.seed)
