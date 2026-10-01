"""Pydantic schemas for structured prescription detection, recognition, and pipeline outputs."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from ..medications.schemas import MedicationMatchResult, StrengthInfo, DosageFormInfo, MedicationConcept, CandidateItem


class AlternativeCandidate(BaseModel):
    """Alternative candidate for uncertain handwriting recognition."""
    text: str = Field(..., description="Candidate recognized medication/token text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Normalized model confidence score")


class NormalizedTextResult(BaseModel):
    """Raw vs normalized OCR text output with confidence."""
    raw_text: str = Field(..., description="Raw string from handwriting decoder")
    normalized_text: str = Field(..., description="Standardized medication/dosage string")
    normalization_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in normalized token")


class MedicineCropInfo(BaseModel):
    """Metadata for an extracted medicine region crop."""
    region_id: str = Field(..., description="Unique identifier for the detected medicine region")
    crop_path: Optional[str] = Field(None, description="Filesystem path if saved to disk")
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2]")
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="Detector confidence score")


class RecognizedMedicineRegion(BaseModel):
    """Fully recognized and evaluated single medicine region with grounded medication identity."""
    region_id: str = Field(..., description="Unique region ID (e.g. medicine_1)")
    bbox: List[int] = Field(..., min_length=4, max_length=4, description="Bounding box [x1, y1, x2, y2]")
    detection_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence of medicine region detection")
    raw_text: str = Field(..., description="Raw recognized text before normalization")
    normalized_text: str = Field(..., description="Cleaned/normalized medication token")
    recognition_confidence: float = Field(..., ge=0.0, le=1.0, description="Explicit character/token sequence probability")
    uncertain: bool = Field(False, description="Flag indicating low confidence (< threshold)")
    alternatives: List[AlternativeCandidate] = Field(default_factory=list, description="Top-k alternative candidates from HTR")
    character_confidences: Optional[List[float]] = Field(default=None, description="Per-character probabilities")
    
    # Grounded Medication Understanding additions (Task 24)
    medication_status: Optional[str] = Field(None, description="Candidate status: confirmed_candidate, possible_candidate, uncertain, unmatched")
    matched_name: Optional[str] = Field(None, description="Standardized canonical medication name")
    matched_medication: Optional[MedicationConcept] = Field(None, description="Structured concept identity")
    strength: Optional[StrengthInfo] = Field(None, description="Explicitly visible strength with value and unit")
    dosage_form: Optional[DosageFormInfo] = Field(None, description="Explicitly visible dosage form")
    medication_match: Optional[MedicationMatchResult] = Field(None, description="Full structured medication understanding output")


class PrescriptionPipelineResult(BaseModel):
    """Master structured result returned by PrescriptionRecognitionPipeline."""
    analysis_type: str = Field(default="prescription", description="Type of medical document analysis")
    status: str = Field(default="completed", description="Status of pipeline execution (completed/failed)")
    total_regions_detected: int = Field(..., ge=0, description="Number of candidate medicine regions found")
    regions: List[RecognizedMedicineRegion] = Field(default_factory=list, description="Extracted & recognized medicine regions")
    model_versions: Dict[str, str] = Field(..., description="Model version identifiers for detector, recognizer, and matcher")
    processing_time_ms: float = Field(..., description="End-to-end inference latency in milliseconds")
    disclaimer: str = Field(
        default="RESEARCH BASELINE: This output reflects visual handwriting recognition and medication name matching only. "
                "No clinical recommendations, dosages, drug interactions, or therapeutic instructions are inferred.",
        description="Medical safety and research disclaimer"
    )
