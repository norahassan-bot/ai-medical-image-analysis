"""Master MedicationMatcher orchestrating normalization, candidate generation, provider lookup, and confidence scoring."""

import time
import logging
from typing import List, Optional, Dict, Any

from .schemas import (
    MedicationMatchResult,
    MedicationConcept,
    CandidateItem,
    MatchStatus,
    MatchType,
    StrengthInfo,
    DosageFormInfo
)
from .normalizer import MedicationTextNormalizer
from .candidate_generator import CandidateGenerator
from .confidence import ConfidencePolicy
from .providers.base import MedicationInfoProvider
from .providers.egypt import EgyptianMedicationProvider
from .providers.rxnorm import RxNormProvider

logger = logging.getLogger(__name__)


class MedicationMatcher:
    """Master service for converting raw handwriting recognition strings into grounded, structured medication candidates."""

    def __init__(
        self,
        providers: Optional[List[MedicationInfoProvider]] = None,
        confidence_policy: Optional[ConfidencePolicy] = None,
        enable_rxnorm: bool = True,
        rxnorm_offline: bool = False,
        rxnorm_timeout: float = 3.0
    ):
        self.normalizer = MedicationTextNormalizer()
        self.confidence_policy = confidence_policy or ConfidencePolicy()

        if providers is not None:
            self.providers = providers
        else:
            self.providers = [
                EgyptianMedicationProvider(),
                RxNormProvider(
                    timeout_seconds=rxnorm_timeout,
                    offline_mode=not enable_rxnorm or rxnorm_offline
                )
            ]

        self.candidate_generator = CandidateGenerator(
            providers=self.providers,
            fuzzy_min_threshold=self.confidence_policy.low_threshold,
            max_candidates=5
        )

    def match(
        self,
        raw_text: str,
        ocr_confidence: Optional[float] = None
    ) -> MedicationMatchResult:
        """Perform end-to-end normalization, candidate generation, and concept matching for a single OCR line."""
        start_time = time.time()

        # Handle empty/whitespace input
        if not raw_text or not raw_text.strip():
            return MedicationMatchResult(
                raw_text=raw_text or "",
                normalized_text="",
                cleaned_medication_query="",
                status=MatchStatus.UNMATCHED,
                confidence=0.0,
                matched_medication=None,
                strength=None,
                dosage_form=None,
                alternatives=[],
                metadata={
                    "ocr_confidence": ocr_confidence,
                    "matching_method": MatchType.NONE.value,
                    "elapsed_ms": round((time.time() - start_time) * 1000, 2),
                    "disclaimer": "Visual transcription only. No clinical indications inferred."
                }
            )

        # 1. Normalize & Extract Strength / Dosage Form / Transliterations
        norm_result = self.normalizer.normalize(raw_text)
        normalized_text = norm_result["normalized_text"]
        cleaned_query = norm_result["cleaned_query"]
        strength_info = norm_result["strength"]
        dosage_form_info = norm_result["dosage_form"]
        transliterations = norm_result["transliteration_candidates"]

        # 2. Generate and Rank Candidates
        candidates = self.candidate_generator.generate_candidates(
            cleaned_query=cleaned_query,
            transliteration_candidates=transliterations
        )

        # 3. Calibrate Confidence and Status
        status, conf, breakdown = self.confidence_policy.evaluate_candidates(
            candidates=candidates,
            ocr_confidence=ocr_confidence
        )

        # 4. Resolve Concept for Top Candidate
        top_concept: Optional[MedicationConcept] = None
        top_match_type = MatchType.NONE

        if candidates and status != MatchStatus.UNMATCHED:
            top_cand = candidates[0]
            top_match_type = top_cand.match_type

            # Resolve concept by identifier or lookup
            if top_cand.identifier:
                for prov in self.providers:
                    resolved = prov.get_by_identifier(top_cand.identifier)
                    if resolved:
                        top_concept = resolved
                        top_concept.match_score = top_cand.score
                        top_concept.match_type = top_cand.match_type
                        break

            if not top_concept:
                top_concept = MedicationConcept(
                    identifier=top_cand.identifier or f"matched_{top_cand.name.lower().replace(' ', '_')}",
                    name=top_cand.name,
                    brand_name=top_cand.brand_name,
                    generic_name=top_cand.generic_name,
                    source=top_cand.source or "MedicationMatcher",
                    match_score=top_cand.score,
                    match_type=top_cand.match_type
                )

        # Build Alternatives List (excluding top candidate if matched)
        alternatives = candidates[1:] if len(candidates) > 1 else []

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return MedicationMatchResult(
            raw_text=raw_text,
            normalized_text=normalized_text,
            cleaned_medication_query=cleaned_query,
            status=status,
            confidence=conf,
            matched_medication=top_concept,
            strength=strength_info,
            dosage_form=dosage_form_info,
            alternatives=alternatives,
            metadata={
                "ocr_confidence": ocr_confidence,
                "matching_method": top_match_type.value,
                "elapsed_ms": elapsed_ms,
                "score_breakdown": breakdown.model_dump() if breakdown else None,
                "providers": [p.get_provider_info() for p in self.providers],
                "disclaimer": "Visual transcription only. No clinical indications inferred."
            }
        )

    def match_batch(
        self,
        items: List[Dict[str, Any]]
    ) -> List[MedicationMatchResult]:
        """Process multiple medication lines in a multi-item prescription."""
        results: List[MedicationMatchResult] = []
        for item in items:
            raw = item.get("raw_text", "")
            ocr_conf = item.get("confidence") or item.get("ocr_confidence")
            res = self.match(raw_text=raw, ocr_confidence=ocr_conf)
            results.append(res)
        return results
