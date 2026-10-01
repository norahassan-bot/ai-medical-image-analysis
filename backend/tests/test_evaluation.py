import pytest
from pathlib import Path
import json
import numpy as np

from src.evaluation.evaluate import (
    compute_clinical_metrics,
    plot_confusion_matrix,
    plot_roc_curve,
    evaluate_checkpoint,
)
from src.data.dataset import CLASS_TO_IDX, IDX_TO_CLASS


def test_deterministic_metric_calculations():
    """Verify exact diagnostic metric calculations on controlled toy data."""
    # 4 True Pneumonia (1), 4 True Normal (0)
    # Predicted: 3 TP, 1 FN, 3 TN, 1 FP
    y_true = [1, 1, 1, 1, 0, 0, 0, 0]
    y_pred = [1, 1, 1, 0, 0, 0, 0, 1]
    y_prob = [0.9, 0.85, 0.7, 0.4, 0.1, 0.2, 0.3, 0.6]

    metrics = compute_clinical_metrics(y_true, y_pred, y_prob)

    assert metrics["accuracy"] == 6 / 8  # 0.75
    assert metrics["precision"] == 3 / 4  # 3 TP / (3 TP + 1 FP) = 0.75
    assert metrics["recall_sensitivity"] == 3 / 4  # 3 TP / (3 TP + 1 FN) = 0.75
    assert metrics["specificity"] == 3 / 4  # 3 TN / (3 TN + 1 FP) = 0.75
    assert metrics["f1_score"] == 0.75
    assert metrics["confusion_matrix"]["matrix"] == [[3, 1], [1, 3]]
    assert metrics["confusion_matrix"]["true_positives"] == 3
    assert metrics["confusion_matrix"]["false_negatives"] == 1
    assert metrics["confusion_matrix"]["true_negatives"] == 3
    assert metrics["confusion_matrix"]["false_positives"] == 1
    assert isinstance(metrics["roc_auc"], float)
    assert 0.0 <= metrics["roc_auc"] <= 1.0


def test_roc_auc_single_class_edge_case():
    """Verify graceful handling of ROC-AUC when a split has only one class."""
    y_true = [1, 1, 1, 1]
    y_pred = [1, 1, 1, 1]
    y_prob = [0.9, 0.8, 0.7, 0.6]

    metrics = compute_clinical_metrics(y_true, y_pred, y_prob)
    assert metrics["roc_auc"] is None
    assert "NOT AVAILABLE" in metrics["roc_auc_note"]


def test_class_mapping_standardization():
    """Verify that evaluation preserves the canonical class mapping."""
    assert CLASS_TO_IDX["NORMAL"] == 0
    assert CLASS_TO_IDX["PNEUMONIA"] == 1
    assert IDX_TO_CLASS[0] == "NORMAL"
    assert IDX_TO_CLASS[1] == "PNEUMONIA"


def test_missing_checkpoint_error(tmp_path):
    """Verify that a nonexistent checkpoint raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Trained checkpoint not found"):
        evaluate_checkpoint(checkpoint_path=tmp_path / "nonexistent.pth")


def test_confusion_matrix_plot_creation(tmp_path):
    """Verify confusion matrix plot file generation."""
    cm = [[10, 2], [3, 25]]
    out_file = tmp_path / "cm_test.png"
    plot_confusion_matrix(cm, ["NORMAL", "PNEUMONIA"], out_file)
    assert out_file.exists()
    assert out_file.stat().st_size > 0


def test_roc_curve_plot_creation(tmp_path):
    """Verify ROC curve plot generation."""
    y_true = [0, 0, 1, 1, 0, 1]
    y_prob = [0.1, 0.3, 0.8, 0.9, 0.4, 0.7]
    out_file = tmp_path / "roc_test.png"
    auc = plot_roc_curve(y_true, y_prob, out_file)
    assert out_file.exists()
    assert auc is not None
    assert auc > 0.5
