"""Handwriting recognition package export."""

from .recognizer import HandwrittenTextRecognizer, CRNNModel
from .dataset import PrescriptionHandwritingDataset, handwriting_collate_fn
from .decoder import CTCDecoder, normalize_ocr_text
from .train import train_recognizer, evaluate_recognizer

__all__ = [
    "HandwrittenTextRecognizer",
    "CRNNModel",
    "PrescriptionHandwritingDataset",
    "handwriting_collate_fn",
    "CTCDecoder",
    "normalize_ocr_text",
    "train_recognizer",
    "evaluate_recognizer"
]
