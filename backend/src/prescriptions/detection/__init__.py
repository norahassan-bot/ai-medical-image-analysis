"""Detection package export."""

from .detector import MedicineRegionDetector, MedicineRegionCropper
from .dataset import PrescriptionDetectionDataset
from .train import train_detector, evaluate_detector

__all__ = [
    "MedicineRegionDetector",
    "MedicineRegionCropper",
    "PrescriptionDetectionDataset",
    "train_detector",
    "evaluate_detector"
]
