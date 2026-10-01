"""Clinical model evaluation, performance metric calculation, and error analysis.

Evaluation Philosophy & Clinical Standards:
------------------------------------------
1. Clinical Positive vs. Negative Definition:
   - Negative Class (Index 0): NORMAL
   - Positive Class (Index 1): PNEUMONIA
   All binary metrics (Precision, Recall/Sensitivity, F1-Score, ROC-AUC) are calibrated with
   respect to the Positive Class (PNEUMONIA) to reflect clinical diagnostic detection performance.

2. Test-Set Strict Isolation:
   The test dataset (624 holdout pediatric radiographs) is evaluated strictly once as a final benchmark.
   No threshold tuning, model selection, or weight retraining is conducted based on test-set metrics.

3. Metric Explanations:
   - Sensitivity / Recall: Proportion of actual pneumonia cases correctly identified (TP / (TP + FN)).
   - Specificity: Proportion of true normal cases correctly identified (TN / (TN + FP)).
   - Precision / PPV: Proportion of positive predictions that were true pneumonia (TP / (TP + FP)).
   - F1-Score: Harmonic mean of precision and recall.
   - ROC-AUC: Discriminative ability across all possible classification probability thresholds.

4. Research Disclaimer:
   Metrics reported here represent empirical computer vision performance on a pediatric cohort
   (children aged 1–5). This system is a clinical decision-support research tool and does NOT
   constitute an autonomous medical diagnostic device.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    confusion_matrix,
    classification_report,
)

# Add backend root to path if executed directly
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.data.dataset import ChestXRayDataset, CLASS_TO_IDX, IDX_TO_CLASS
from src.data.preprocessing import DEFAULT_IMAGE_SIZE
from src.models.model import MedicalClassifier, load_model_checkpoint, get_device

logger = logging.getLogger("MedicalEvaluation")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def compute_clinical_metrics(
    y_true: Union[List[int], np.ndarray],
    y_pred: Union[List[int], np.ndarray],
    y_probs: Optional[Union[List[float], np.ndarray]] = None,
) -> Dict[str, Any]:
    """Calculate comprehensive clinical diagnostic metrics for binary classification.

    Args:
        y_true: Ground truth binary labels (0=NORMAL, 1=PNEUMONIA).
        y_pred: Predicted binary labels (0=NORMAL, 1=PNEUMONIA).
        y_probs: Continuous positive-class (PNEUMONIA) prediction probabilities in [0.0, 1.0].

    Returns:
        Structured dictionary of diagnostic performance metrics.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_pred_arr = np.asarray(y_pred, dtype=int)

    # Confusion matrix: [[TN, FP], [FN, TP]]
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    prec = float(precision_score(y_true_arr, y_pred_arr, pos_label=1, zero_division=0))
    recall = float(recall_score(y_true_arr, y_pred_arr, pos_label=1, zero_division=0))
    specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    f1 = float(f1_score(y_true_arr, y_pred_arr, pos_label=1, zero_division=0))

    metrics: Dict[str, Any] = {
        "accuracy": acc,
        "precision": prec,
        "recall_sensitivity": recall,
        "specificity": specificity,
        "f1_score": f1,
        "confusion_matrix": {
            "matrix": cm.tolist(),
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp),
        },
        "positive_class": "PNEUMONIA (Index 1)",
        "negative_class": "NORMAL (Index 0)",
        "total_samples": len(y_true_arr),
    }

    # ROC-AUC calculation
    if y_probs is not None:
        y_probs_arr = np.asarray(y_probs, dtype=float)
        unique_classes = np.unique(y_true_arr)
        if len(unique_classes) > 1:
            try:
                auc_val = float(roc_auc_score(y_true_arr, y_probs_arr))
                metrics["roc_auc"] = auc_val
            except Exception as e:
                metrics["roc_auc"] = None
                metrics["roc_auc_note"] = f"Calculation error: {e}"
        else:
            metrics["roc_auc"] = None
            metrics["roc_auc_note"] = f"NOT AVAILABLE — Split contains only single class: {unique_classes.tolist()}"
    else:
        metrics["roc_auc"] = None
        metrics["roc_auc_note"] = "NOT AVAILABLE — Probability outputs not provided"

    return metrics


def run_model_inference(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device,
    split_name: str = "eval",
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """Execute forward-pass inference over a deterministic DataLoader.

    Args:
        model: Trained MedicalClassifier model.
        dataloader: PyTorch DataLoader for evaluation split.
        device: Device (CPU/CUDA) to run inference on.
        split_name: Name of the split ('validation' or 'test').

    Returns:
        Tuple of (metrics_dict, detailed_predictions_dataframe).
    """
    model.eval()
    dataset = dataloader.dataset

    all_true: List[int] = []
    all_pred: List[int] = []
    all_prob_pneumonia: List[float] = []
    all_prob_normal: List[float] = []
    all_paths: List[str] = []

    # Get sample paths from dataset if available
    sample_paths = [str(p) for p, _ in getattr(dataset, "samples", [])]

    sample_offset = 0
    with torch.no_grad():
        for images, targets in dataloader:
            images = images.to(device)
            batch_size = images.size(0)

            logits = model(images)
            probabilities = F.softmax(logits, dim=1)
            _, predicted = logits.max(1)

            prob_np = probabilities.cpu().numpy()
            pred_np = predicted.cpu().numpy()
            target_np = targets.numpy()

            all_true.extend(target_np.tolist())
            all_pred.extend(pred_np.tolist())
            all_prob_normal.extend(prob_np[:, 0].tolist())
            all_prob_pneumonia.extend(prob_np[:, 1].tolist())

            if sample_paths:
                batch_paths = sample_paths[sample_offset : sample_offset + batch_size]
                all_paths.extend(batch_paths)
                sample_offset += batch_size

    # Compute metrics
    metrics = compute_clinical_metrics(
        y_true=all_true,
        y_pred=all_pred,
        y_probs=all_prob_pneumonia,
    )

    # Class labels
    true_class_names = [IDX_TO_CLASS[t] for t in all_true]
    pred_class_names = [IDX_TO_CLASS[p] for p in all_pred]
    is_correct = [t == p for t, p in zip(all_true, all_pred)]

    # Categorize error types: TP, TN, FP, FN
    error_types = []
    for t, p in zip(all_true, all_pred):
        if t == 1 and p == 1:
            error_types.append("TP")
        elif t == 0 and p == 0:
            error_types.append("TN")
        elif t == 0 and p == 1:
            error_types.append("FP (False Pneumonia)")
        else:
            error_types.append("FN (Missed Pneumonia)")

    df_preds = pd.DataFrame({
        "image_path": all_paths if len(all_paths) == len(all_true) else [f"sample_{i}" for i in range(len(all_true))],
        "true_index": all_true,
        "true_label": true_class_names,
        "predicted_index": all_pred,
        "predicted_label": pred_class_names,
        "probability_normal": all_prob_normal,
        "probability_pneumonia": all_prob_pneumonia,
        "is_correct": is_correct,
        "error_type": error_types,
        "split": split_name,
    })

    return metrics, df_preds


def plot_confusion_matrix(
    cm: Union[List[List[int]], np.ndarray],
    class_names: List[str],
    output_path: Union[str, Path],
    title: str = "Confusion Matrix",
):
    """Render and save annotated confusion matrix with counts and percentages."""
    cm_arr = np.asarray(cm)
    fig, ax = plt.subplots(figsize=(6, 5))

    cax = ax.matshow(cm_arr, cmap="Blues", alpha=0.85)
    fig.colorbar(cax)

    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, fontsize=11, fontweight="bold")
    ax.set_yticklabels(class_names, fontsize=11, fontweight="bold")

    total = np.sum(cm_arr)
    for i in range(cm_arr.shape[0]):
        for j in range(cm_arr.shape[1]):
            count = cm_arr[i, j]
            pct = (count / total * 100) if total > 0 else 0
            text_color = "white" if count > (cm_arr.max() / 2) else "black"
            ax.text(
                j, i, f"{count}\n({pct:.1f}%)",
                ha="center", va="center", color=text_color, fontsize=12, fontweight="bold"
            )

    ax.set_xlabel("Predicted Diagnosis", fontsize=12, fontweight="bold", labelpad=10)
    ax.set_ylabel("True Ground Truth", fontsize=12, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved confusion matrix plot to {output_path}")


def plot_roc_curve(
    y_true: List[int],
    y_probs: List[float],
    output_path: Union[str, Path],
    title: str = "Receiver Operating Characteristic (ROC) Curve",
) -> Optional[float]:
    """Plot and save ROC curve."""
    if len(np.unique(y_true)) < 2:
        logger.warning("Cannot generate ROC plot: single class present.")
        return None

    fpr, tpr, _ = roc_curve(y_true, y_probs)
    auc_val = float(roc_auc_score(y_true, y_probs))

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color="#0ea5e9", lw=2.5, label=f"ROC Curve (AUC = {auc_val:.4f})")
    ax.plot([0, 1], [0, 1], color="#94a3b8", lw=1.5, linestyle="--", label="Chance Level (AUC = 0.5000)")

    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("False Positive Rate (1 - Specificity)", fontsize=11, fontweight="bold")
    ax.set_ylabel("True Positive Rate (Sensitivity)", fontsize=11, fontweight="bold")
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(loc="lower right", fontsize=11)
    ax.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info(f"Saved ROC curve plot to {output_path}")
    return auc_val


def evaluate_checkpoint(
    checkpoint_path: Union[str, Path] = "backend/models/best_model.pth",
    dataset_root: Union[str, Path] = "data/chest_xray",
    reports_dir: Union[str, Path] = "reports/evaluation",
    device: Optional[Union[str, torch.device]] = None,
    batch_size: int = 32,
    image_size: Tuple[int, int] = DEFAULT_IMAGE_SIZE,
) -> Dict[str, Any]:
    """Comprehensive evaluation entrypoint for Validation and Test datasets.

    Args:
        checkpoint_path: Path to trained PyTorch checkpoint (.pth).
        dataset_root: Path to chest_xray directory.
        reports_dir: Directory where evaluation artifacts will be exported.
        device: Device to use for evaluation.
        batch_size: DataLoader batch size.
        image_size: Target image dimensions.

    Returns:
        Structured evaluation metrics report dictionary.
    """
    ckpt_file = Path(checkpoint_path)
    if not ckpt_file.exists():
        raise FileNotFoundError(f"Trained checkpoint not found at: {ckpt_file.resolve()}")

    data_dir = Path(dataset_root)
    if not data_dir.exists():
        raise FileNotFoundError(f"Dataset root directory not found at: {data_dir.resolve()}")

    out_dir = Path(reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target_device = torch.device(device) if device else get_device()
    logger.info(f"Starting model evaluation on device: {target_device}")

    # 1. Load Model from Checkpoint
    model, checkpoint_info = load_model_checkpoint(ckpt_file, device=target_device)
    model_metadata = model.get_model_metadata()

    # 2. Instantiate Validation & Test Datasets (with deterministic preprocessing)
    val_dataset = ChestXRayDataset(dataset_root=data_dir, split="val", image_size=image_size)
    test_dataset = ChestXRayDataset(dataset_root=data_dir, split="test", image_size=image_size)

    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # 3. Evaluate Validation Set
    logger.info(f"Running inference on Validation set ({len(val_dataset)} images)...")
    val_metrics, val_df = run_model_inference(model, val_loader, target_device, split_name="validation")

    # 4. Evaluate Test Set (Strict Holdout Evaluation)
    logger.info(f"Running inference on Test set ({len(test_dataset)} images)...")
    test_metrics, test_df = run_model_inference(model, test_loader, target_device, split_name="test")

    # 5. Export Prediction DataFrames
    val_pred_path = out_dir / "predictions_validation.csv"
    test_pred_path = out_dir / "predictions_test.csv"
    val_df.to_csv(val_pred_path, index=False)
    test_df.to_csv(test_pred_path, index=False)
    logger.info(f"Saved prediction CSVs to {val_pred_path} and {test_pred_path}")

    # 6. Generate and Save Confusion Matrices
    class_labels = ["NORMAL", "PNEUMONIA"]
    cm_val_path = out_dir / "confusion_matrix_val.png"
    cm_test_path = out_dir / "confusion_matrix_test.png"
    plot_confusion_matrix(val_metrics["confusion_matrix"]["matrix"], class_labels, cm_val_path, title="Validation Set Confusion Matrix")
    plot_confusion_matrix(test_metrics["confusion_matrix"]["matrix"], class_labels, cm_test_path, title="Test Set (Holdout) Confusion Matrix")

    # 7. Generate ROC Plot for Test Set
    roc_test_path = out_dir / "roc_curve_test.png"
    plot_roc_curve(test_df["true_index"].tolist(), test_df["probability_pneumonia"].tolist(), roc_test_path, title="Test Set ROC Curve")

    # 8. Generate Textual Classification Reports
    val_report = classification_report(val_df["true_index"], val_df["predicted_index"], target_names=class_labels, zero_division=0)
    test_report = classification_report(test_df["true_index"], test_df["predicted_index"], target_names=class_labels, zero_division=0)

    val_report_path = out_dir / "classification_report_val.txt"
    test_report_path = out_dir / "classification_report_test.txt"
    with open(val_report_path, "w", encoding="utf-8") as f:
        f.write("=== VALIDATION CLASSIFICATION REPORT ===\n")
        f.write(val_report)
    with open(test_report_path, "w", encoding="utf-8") as f:
        f.write("=== TEST (HOLDOUT) CLASSIFICATION REPORT ===\n")
        f.write(test_report)

    # 9. Perform Error Analysis Summary
    error_analysis = {
        "validation_errors": {
            "total_samples": len(val_df),
            "correct": int(val_df["is_correct"].sum()),
            "incorrect": int((~val_df["is_correct"]).sum()),
            "false_positives": int((val_df["error_type"] == "FP (False Pneumonia)").sum()),
            "false_negatives": int((val_df["error_type"] == "FN (Missed Pneumonia)").sum()),
        },
        "test_errors": {
            "total_samples": len(test_df),
            "correct": int(test_df["is_correct"].sum()),
            "incorrect": int((~test_df["is_correct"]).sum()),
            "false_positives": int((test_df["error_type"] == "FP (False Pneumonia)").sum()),
            "false_negatives": int((test_df["error_type"] == "FN (Missed Pneumonia)").sum()),
        },
    }
    error_path = out_dir / "error_analysis.json"
    with open(error_path, "w", encoding="utf-8") as f:
        json.dump(error_analysis, f, indent=2)

    # 10. Assemble and Save metrics.json
    final_report: Dict[str, Any] = {
        "metadata": {
            "checkpoint": str(ckpt_file),
            "architecture": model_metadata["architecture"],
            "num_classes": model_metadata["num_classes"],
            "class_mapping": CLASS_TO_IDX,
            "total_parameters": model_metadata["total_parameters"],
            "device": str(target_device),
        },
        "validation": val_metrics,
        "test": test_metrics,
        "error_analysis": error_analysis,
        "disclaimer": "Metrics reflect evaluation on retrospective pediatric chest radiographs (ages 1-5). For research/decision-support only; not an autonomous diagnostic device.",
    }

    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
    logger.info(f"Saved comprehensive evaluation report to {metrics_path}")

    return final_report


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate Trained Chest X-Ray Model Checkpoint")
    parser.add_argument("--checkpoint", type=str, default="backend/models/best_model.pth", help="Checkpoint file path")
    parser.add_argument("--dataset-root", type=str, default="data/chest_xray", help="Dataset root directory")
    parser.add_argument("--reports-dir", type=str, default="reports/evaluation", help="Output directory for reports")
    parser.add_argument("--batch-size", type=int, default=32, help="Evaluation batch size")
    parser.add_argument("--device", type=str, default=None, help="Device (cpu, cuda)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    evaluate_checkpoint(
        checkpoint_path=args.checkpoint,
        dataset_root=args.dataset_root,
        reports_dir=args.reports_dir,
        device=args.device,
        batch_size=args.batch_size,
    )
