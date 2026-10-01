"""Master Prescription Understanding Service integrating Medication Matching, Verified Drug Information, and Instruction Parsing."""

import time
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from .medications.schemas import (
    MedicationMatchResult,
    MedicationConcept,
    StrengthInfo,
    DosageFormInfo,
    MatchStatus
)
from .medications.matcher import MedicationMatcher
from .medications.info_service import MedicationInfoService
from .instructions.schemas import (
    ParsedPrescriptionInstructions,
    DoseInstruction,
    FrequencyInstruction,
    DurationInstruction,
    RouteInstruction,
    FoodTimingInstruction
)
from .instructions.parser import PrescriptionInstructionParser
from .pipeline.prescription_pipeline import PrescriptionRecognitionPipeline

logger = logging.getLogger(__name__)


class MedicationSummary(BaseModel):
    """Clean representation of matched medication identity."""
    matched_name: Optional[str] = Field(None, description="Matched canonical medication name")
    generic_name: Optional[str] = Field(None, description="Generic active substance name")
    brand_name: Optional[str] = Field(None, description="Trade brand name")
    source: Optional[str] = Field(None, description="Authority source (RxNorm, EDA)")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Matching confidence score")
    status: str = Field("unmatched", description="Match status")


class StructuredPrescriptionMedicationItem(BaseModel):
    """Complete understanding of a single prescription item with separate instructions and educational facts."""
    region_id: str = Field(default="med_1", description="Unique identifier of prescription item/region")
    raw_text: str = Field(..., description="Verbatim OCR text from prescription crop")
    normalized_text: str = Field(..., description="Cleaned/normalized text representation")
    medication: MedicationSummary = Field(..., description="Matched medication identity")
    strength: Optional[StrengthInfo] = Field(None, description="Explicitly visible strength specification")
    dosage_form: Optional[DosageFormInfo] = Field(None, description="Explicitly visible dosage form")
    instructions: ParsedPrescriptionInstructions = Field(..., description="Explicitly written prescription instructions")
    medication_information: Dict[str, Any] = Field(..., description="Verified educational facts and general indications")
    association_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence that instructions belong to this medication")
    association_uncertain: bool = Field(False, description="Whether layout/instruction association is ambiguous")


class PrescriptionUnderstandingResult(BaseModel):
    """Master structured output schema for Task 25 Prescription Understanding."""
    analysis_type: str = Field(default="prescription_understanding", description="Analysis category")
    status: str = Field(default="completed", description="Service execution status")
    parser_version: str = Field(default="2.0.0", description="Prescription understanding engine version")
    total_medications: int = Field(..., ge=0, description="Total recognized prescription medication entries")
    medications: List[StructuredPrescriptionMedicationItem] = Field(default_factory=list, description="Structured medication entries")
    processing_time_ms: float = Field(..., description="Total pipeline execution latency in milliseconds")
    disclaimer_en: str = Field(
        default="CRITICAL SAFETY DISCLAIMER: This system extracts and transcribes visual prescription instructions "
                "and retrieves general educational medication facts. It does not prescribe medication, recommend dosage adjustments, "
                "or infer patient-specific diagnoses.",
        description="Medical safety boundary disclaimer in English"
    )
    disclaimer_ar: str = Field(
        default="تنبيه طبي: المعلومات الدوائية الواردة هي لأغراض تعليمية وإرشادية عامة ولا تعتبر تشخيصاً لحالة المريض أو توصية بالعلاج. "
                "تُستخرج الجرعات وتعليمات الاستخدام من النص المكتوب في الروشتة فقط، ولا يُعتمد على التخمين أو الاستنتاج.",
        description="Medical safety boundary disclaimer in Arabic"
    )


class PrescriptionUnderstandingService:
    """Master orchestrator executing Medication Understanding, Verified Info Retrieval, and Instruction Parsing."""

    def __init__(
        self,
        matcher: Optional[MedicationMatcher] = None,
        info_service: Optional[MedicationInfoService] = None,
        instruction_parser: Optional[PrescriptionInstructionParser] = None,
        pipeline: Optional[PrescriptionRecognitionPipeline] = None
    ):
        self.matcher = matcher or MedicationMatcher()
        self.info_service = info_service or MedicationInfoService()
        self.instruction_parser = instruction_parser or PrescriptionInstructionParser()
        self.pipeline = pipeline
        self.parser_version = "2.0.0"

    def understand_from_text(
        self,
        text_lines: List[Union[str, Dict[str, Any]]],
        prescription_id: Optional[str] = None
    ) -> PrescriptionUnderstandingResult:
        """Process structured or raw text lines into comprehensive prescription understanding results."""
        start_time = time.time()
        medication_items: List[StructuredPrescriptionMedicationItem] = []

        for idx, line in enumerate(text_lines):
            reg_id = f"med_{idx + 1}"
            if isinstance(line, str):
                raw_text = line
                instruction_text = line
                ocr_conf = None
            else:
                raw_text = line.get("raw_text", "")
                instruction_text = line.get("instruction_text", raw_text)
                combined_text = f"{raw_text} {instruction_text}".strip()
                ocr_conf = line.get("confidence") or line.get("ocr_confidence")

            if not raw_text.strip() and not instruction_text.strip():
                continue

            # 1. Match Medication Identity (Task 24)
            match_res = self.matcher.match(raw_text=raw_text, ocr_confidence=ocr_conf)

            # 2. Retrieve Verified Medication Information (Part A)
            med_name = match_res.matched_medication.name if match_res.matched_medication else match_res.cleaned_medication_query
            gen_name = match_res.matched_medication.generic_name if match_res.matched_medication else None
            concept_id = match_res.matched_medication.identifier if match_res.matched_medication else None
            src_name = match_res.matched_medication.source if match_res.matched_medication else None

            med_info = self.info_service.get_medication_info(
                medication_name=med_name,
                generic_name=gen_name,
                identifier=concept_id,
                source=src_name
            )

            # 3. Parse Explicit Prescription Instructions (Part B)
            # Parse from the explicit instruction text (or combined line)
            text_to_parse_instructions = instruction_text if instruction_text else raw_text
            parsed_instructions = self.instruction_parser.parse(text_to_parse_instructions)

            # 4. Medication Summary
            med_summary = MedicationSummary(
                matched_name=match_res.matched_medication.name if match_res.matched_medication else None,
                generic_name=gen_name,
                brand_name=match_res.matched_medication.brand_name if match_res.matched_medication else None,
                source=src_name,
                confidence=match_res.confidence,
                status=match_res.status.value
            )

            # 5. Assemble Item
            item = StructuredPrescriptionMedicationItem(
                region_id=reg_id,
                raw_text=match_res.raw_text,
                normalized_text=match_res.normalized_text,
                medication=med_summary,
                strength=match_res.strength,
                dosage_form=match_res.dosage_form,
                instructions=parsed_instructions,
                medication_information=med_info,
                association_confidence=0.95,
                association_uncertain=False
            )
            medication_items.append(item)

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return PrescriptionUnderstandingResult(
            analysis_type="prescription_understanding",
            status="completed",
            total_medications=len(medication_items),
            medications=medication_items,
            processing_time_ms=latency_ms
        )

    def understand_prescription(
        self,
        image_input: Union[str, Path, bytes, Image.Image, np.ndarray],
        score_threshold: Optional[float] = None
    ) -> PrescriptionUnderstandingResult:
        """Run full end-to-end vision, HTR, matching, information retrieval, and instruction parsing on prescription image."""
        if self.pipeline is None:
            self.pipeline = PrescriptionRecognitionPipeline(device="cpu")

        # 1. Execute Task 23 Vision Pipeline
        pipeline_result = self.pipeline.analyze(image_input, score_threshold=score_threshold)

        # 2. Extract lines from recognized regions
        lines = [
            {"raw_text": reg.raw_text, "confidence": reg.recognition_confidence}
            for reg in pipeline_result.regions
        ]

        # 3. Execute Understanding
        return self.understand_from_text(lines)
