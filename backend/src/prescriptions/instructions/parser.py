"""Master PrescriptionInstructionParser orchestrating dose, frequency, duration, route, and timing extraction."""

import logging
from typing import Optional, List, Dict, Any
from .schemas import (
    ParsedPrescriptionInstructions,
    DoseInstruction,
    FrequencyInstruction,
    DurationInstruction,
    RouteInstruction,
    FoodTimingInstruction,
    InstructionStatus
)
from .normalizer import InstructionTextNormalizer
from .dose import DoseExtractor
from .frequency import FrequencyExtractor
from .duration import DurationExtractor
from .route import RouteExtractor
from .food_timing import FoodTimingExtractor

logger = logging.getLogger(__name__)


class PrescriptionInstructionParser:
    """Extracts explicit, non-hallucinated clinical instructions from recognized prescription text."""

    def __init__(self):
        self.normalizer = InstructionTextNormalizer()

    def parse(self, raw_instruction_text: str) -> ParsedPrescriptionInstructions:
        """Parse raw prescription text and extract all explicitly stated instruction components."""
        if not raw_instruction_text or not raw_instruction_text.strip():
            return ParsedPrescriptionInstructions(
                dose=None,
                frequency=None,
                duration=None,
                route=None,
                food_timing=None,
                prn=False,
                special_instructions=[],
                raw_instruction_text=raw_instruction_text or "",
                overall_confidence=0.0,
                uncertain_fields=[]
            )

        clean_text = self.normalizer.clean(raw_instruction_text)

        # 1. Run specialized extractors
        dose_res = DoseExtractor.extract(clean_text)
        freq_res = FrequencyExtractor.extract(clean_text)
        dur_res = DurationExtractor.extract(clean_text)
        route_res = RouteExtractor.extract(clean_text)
        timing_res = FoodTimingExtractor.extract(clean_text)

        # 2. Check PRN flag
        is_prn = False
        if freq_res and freq_res.is_prn:
            is_prn = True

        # 3. Collect uncertain fields
        uncertain_fields: List[str] = []
        confs: List[float] = []

        if dose_res:
            confs.append(dose_res.confidence)
            if dose_res.status == InstructionStatus.UNCERTAIN:
                uncertain_fields.append("dose")

        if freq_res:
            confs.append(freq_res.confidence)
            if freq_res.status == InstructionStatus.UNCERTAIN:
                uncertain_fields.append("frequency")

        if dur_res:
            confs.append(dur_res.confidence)
            if dur_res.status == InstructionStatus.UNCERTAIN:
                uncertain_fields.append("duration")

        if route_res:
            confs.append(route_res.confidence)
            if route_res.status == InstructionStatus.UNCERTAIN:
                uncertain_fields.append("route")

        if timing_res:
            confs.append(timing_res.confidence)
            if timing_res.status == InstructionStatus.UNCERTAIN:
                uncertain_fields.append("food_timing")

        # 4. Calculate overall confidence
        overall_conf = round(sum(confs) / len(confs), 4) if confs else 0.0

        return ParsedPrescriptionInstructions(
            dose=dose_res,
            frequency=freq_res,
            duration=dur_res,
            route=route_res,
            food_timing=timing_res,
            prn=is_prn,
            special_instructions=[],
            raw_instruction_text=raw_instruction_text,
            overall_confidence=overall_conf,
            uncertain_fields=uncertain_fields
        )
