"""Prescription Analysis & Handwritten Medical Text Recognition Package."""

from .config import PrescriptionConfig, default_config
from .preprocessing import PrescriptionImagePreprocessor
from .detection import MedicineRegionDetector, MedicineRegionCropper
from .handwriting import HandwrittenTextRecognizer, CRNNModel, CTCDecoder, normalize_ocr_text
from .pipeline import PrescriptionRecognitionPipeline
from .schemas import PrescriptionPipelineResult, RecognizedMedicineRegion, MedicineCropInfo

__all__ = [
    "PrescriptionConfig",
    "default_config",
    "PrescriptionImagePreprocessor",
    "MedicineRegionDetector",
    "MedicineRegionCropper",
    "HandwrittenTextRecognizer",
    "CRNNModel",
    "CTCDecoder",
    "normalize_ocr_text",
    "PrescriptionRecognitionPipeline",
    "PrescriptionPipelineResult",
    "RecognizedMedicineRegion",
    "MedicineCropInfo"
]
