"""Evaluation metrics for handwriting recognition and prescription layout detection."""

from typing import List, Dict, Any, Tuple
import numpy as np


def levenshtein_distance(seq1: List[Any], seq2: List[Any]) -> int:
    """Computes Levenshtein edit distance between two sequences."""
    n, m = len(seq1), len(seq2)
    dp = np.zeros((n + 1, m + 1), dtype=int)

    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if seq1[i - 1] == seq2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

    return int(dp[n][m])


def compute_cer(predictions: List[str], ground_truths: List[str]) -> float:
    """Computes Character Error Rate (CER) = sum(edit_distance) / sum(len(gt))."""
    total_dist = 0
    total_chars = 0

    for pred, gt in zip(predictions, ground_truths):
        p_chars = list(pred)
        g_chars = list(gt)
        dist = levenshtein_distance(p_chars, g_chars)
        total_dist += dist
        total_chars += len(g_chars)

    if total_chars == 0:
        return 0.0
    return round(float(total_dist / total_chars), 4)


def compute_wer(predictions: List[str], ground_truths: List[str]) -> float:
    """Computes Word Error Rate (WER) = sum(word_edit_distance) / sum(len(gt_words))."""
    total_dist = 0
    total_words = 0

    for pred, gt in zip(predictions, ground_truths):
        p_words = pred.strip().split()
        g_words = gt.strip().split()
        dist = levenshtein_distance(p_words, g_words)
        total_dist += dist
        total_words += max(1, len(g_words))

    if total_words == 0:
        return 0.0
    return round(float(total_dist / total_words), 4)


def compute_exact_match(predictions: List[str], ground_truths: List[str]) -> float:
    """Computes exact match sequence accuracy."""
    if not predictions:
        return 0.0
    matches = sum(1 for p, g in zip(predictions, ground_truths) if p.strip().lower() == g.strip().lower())
    return round(float(matches / len(predictions)), 4)


def evaluate_htr_predictions(
    predictions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes exhaustive metrics across recognized clinical tokens.
    
    Each item in predictions must have:
        - 'predicted_text': str
        - 'ground_truth': str
        - 'confidence': float
        - 'category': Optional[str]
    """
    preds = [p.get("predicted_text", "") for p in predictions]
    gts = [p.get("ground_truth", "") for p in predictions]
    confs = [p.get("confidence", 0.0) for p in predictions]

    overall_cer = compute_cer(preds, gts)
    overall_wer = compute_wer(preds, gts)
    overall_acc = compute_exact_match(preds, gts)

    # Breakdown by length (short <= 5 chars, long > 5 chars)
    short_preds, short_gts = [], []
    long_preds, long_gts = [], []

    for p, g in zip(preds, gts):
        if len(g) <= 5:
            short_preds.append(p)
            short_gts.append(g)
        else:
            long_preds.append(p)
            long_gts.append(g)

    short_cer = compute_cer(short_preds, short_gts) if short_gts else 0.0
    long_cer = compute_cer(long_preds, long_gts) if long_gts else 0.0

    return {
        "character_error_rate_cer": overall_cer,
        "word_error_rate_wer": overall_wer,
        "exact_match_accuracy": overall_acc,
        "mean_confidence": round(float(np.mean(confs)), 4) if confs else 0.0,
        "short_words_cer": short_cer,
        "long_words_cer": long_cer,
        "total_evaluated_samples": len(predictions)
    }
