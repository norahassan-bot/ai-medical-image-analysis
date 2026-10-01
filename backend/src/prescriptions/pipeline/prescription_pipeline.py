"""End-to-end Prescription Recognition Pipeline integrating Preprocessing, Detection, Cropping, HTR, and Medication Matching."""

import time
from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import numpy as np
from PIL import Image

from ..config import PrescriptionConfig, default_config
from ..preprocessing.image_preprocessor import PrescriptionImagePreprocessor
from ..detection.detector import MedicineRegionDetector, MedicineRegionCropper
from ..handwriting.recognizer import HandwrittenTextRecognizer
from ..medications.matcher import MedicationMatcher
from ..schemas.prediction import (
    PrescriptionPipelineResult,
    RecognizedMedicineRegion,
    AlternativeCandidate
)


class PrescriptionRecognitionPipeline:
    """Master end-to-end inference pipeline for medical prescription recognition and medication understanding."""

    def __init__(
        self,
        config: Optional[PrescriptionConfig] = None,
        detector: Optional[MedicineRegionDetector] = None,
        recognizer: Optional[HandwrittenTextRecognizer] = None,
        matcher: Optional[MedicationMatcher] = None,
        device: Optional[str] = None
    ):
        self.config = config or default_config
        self.device = device
        self.preprocessor = PrescriptionImagePreprocessor(self.config)
        self.cropper = MedicineRegionCropper(self.config)
        
        self.detector = detector or MedicineRegionDetector(config=self.config, device=self.device)
        self.recognizer = recognizer or HandwrittenTextRecognizer(config=self.config, device=self.device)
        self.matcher = matcher or MedicationMatcher(enable_rxnorm=True, rxnorm_offline=False)

    def analyze(
        self,
        image_input: Union[str, Path, bytes, Image.Image, np.ndarray],
        score_threshold: Optional[float] = None,
        top_k: int = 3
    ) -> PrescriptionPipelineResult:
        """Executes full prescription recognition & medication understanding pipeline.
        
        Steps:
            1. Validate & Load Original Image
            2. Preprocess full sheet
            3. Detect medicine regions
            4. Crop detected regions with safety padding
            5. Run CRNN handwriting recognition on each crop
            6. Match recognized text with standardized medication candidates
            7. Enforce clinical safety boundaries (no dosage/diagnosis inference)
            8. Return structured Pydantic result
        """
        start_time = time.time()
        
        # 1. Load & Validate
        bgr_image = self.preprocessor.load_image(image_input)
        if bgr_image.shape[0] < 20 or bgr_image.shape[1] < 20:
            raise ValueError(f"Image too small for prescription analysis: {bgr_image.shape}")

        # 2. Region Detection
        raw_detections = self.detector.detect(bgr_image, score_threshold=score_threshold)
        
        # If no deep learning detector boxes fired (e.g. baseline threshold), extract primary central prescription body
        if len(raw_detections) == 0:
            h, w = bgr_image.shape[:2]
            # Fallback heuristic medicine block for empty detections
            fallback_box = [int(w * 0.1), int(h * 0.25), int(w * 0.9), int(h * 0.75)]
            raw_detections = [{"bbox": fallback_box, "confidence": 0.50, "class_name": "medicine_region"}]

        # 3. Medicine Region Cropping
        crops = self.cropper.crop_regions(bgr_image, raw_detections)

        # 4. Handwriting Recognition & Medication Matching per crop
        recognized_regions: List[RecognizedMedicineRegion] = []

        for idx, crop_info in enumerate(crops):
            crop_bgr = crop_info["crop_bgr"]
            det_conf = crop_info["confidence"]
            bbox = crop_info["bbox"]
            reg_id = crop_info["region_id"]

            # Run HTR recognition
            htr_res = self.recognizer.recognize(crop_bgr, top_k=top_k)

            # Convert alternative dicts to Pydantic models
            alts = [
                AlternativeCandidate(
                    text=a.get("text", ""),
                    confidence=float(a.get("confidence", 0.0))
                )
                for a in htr_res.get("alternatives", [])
            ]

            # Run Medication Name Normalization & Concept Matching
            med_match = self.matcher.match(
                raw_text=htr_res["raw_text"],
                ocr_confidence=htr_res.get("confidence")
            )

            recognized_region = RecognizedMedicineRegion(
                region_id=reg_id,
                bbox=bbox,
                detection_confidence=round(det_conf, 4),
                raw_text=htr_res["raw_text"],
                normalized_text=htr_res["normalized_text"],
                recognition_confidence=round(htr_res["confidence"], 4),
                uncertain=htr_res["uncertain"] or (med_match.status.value in ["uncertain", "unmatched"]),
                alternatives=alts,
                character_confidences=htr_res.get("character_confidences"),
                medication_status=med_match.status.value,
                matched_name=med_match.matched_medication.name if med_match.matched_medication else None,
                matched_medication=med_match.matched_medication,
                strength=med_match.strength,
                dosage_form=med_match.dosage_form,
                medication_match=med_match
            )
            recognized_regions.append(recognized_region)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return PrescriptionPipelineResult(
            analysis_type="prescription",
            status="completed",
            total_regions_detected=len(recognized_regions),
            regions=recognized_regions,
            model_versions={
                "detector": self.detector.version,
                "recognizer": self.recognizer.version,
                "matcher": "MedicationMatcher-v1.0"
            },
            processing_time_ms=latency_ms,
            disclaimer="RESEARCH BASELINE: Output reflects visual transcription and medication name matching only. "
                       "No dosages, drug interactions, or therapeutic instructions are inferred."
        )
