"""Confidence calibration policy and explainable scoring for medication matching."""

from typing import List, Optional, Tuple, Dict, Any
from .schemas import (
    MatchStatus,
    MatchType,
    CandidateItem,
    ScoreBreakdown
)


class ConfidencePolicy:
    """Configurable confidence classification thresholds for clinical safety."""

    def __init__(
        self,
        high_threshold: float = 0.85,
        medium_threshold: float = 0.60,
        low_threshold: float = 0.40,
        ambiguity_margin: float = 0.05
    ):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.low_threshold = low_threshold
        self.ambiguity_margin = ambiguity_margin

    def evaluate_candidates(
        self,
        candidates: List[CandidateItem],
        ocr_confidence: Optional[float] = None
    ) -> Tuple[MatchStatus, float, Optional[ScoreBreakdown]]:
        """Evaluate ranked candidates and determine clinical candidate status and calibrated confidence score."""
        if not candidates:
            return MatchStatus.UNMATCHED, 0.0, None

        top_cand = candidates[0]
        match_score = top_cand.score
        match_type = top_cand.match_type

        # Calculate composite score factoring in OCR confidence if provided
        if ocr_confidence is not None and 0.0 <= ocr_confidence <= 1.0:
            if match_type == MatchType.EXACT:
                # Exact dictionary match has strong prior
                composite_conf = (0.75 * match_score) + (0.25 * ocr_confidence)
            elif match_type == MatchType.TRANSLITERATION:
                composite_conf = (0.70 * match_score) + (0.30 * ocr_confidence)
            else:
                composite_conf = (0.60 * match_score) + (0.40 * ocr_confidence)
        else:
            composite_conf = match_score

        # Ambiguity Penalty Check:
        # If multiple candidates have very close scores (< ambiguity_margin), penalize to avoid overconfident misidentification
        if len(candidates) > 1 and match_type != MatchType.EXACT:
            second_score = candidates[1].score
            score_diff = abs(match_score - second_score)
            if score_diff < self.ambiguity_margin:
                # Apply 10% ambiguity penalty
                composite_conf = composite_conf * 0.90

        composite_conf = round(max(0.0, min(1.0, composite_conf)), 4)

        # Classify status based on calibrated thresholds
        if composite_conf >= self.high_threshold and match_type in [MatchType.EXACT, MatchType.ALIAS, MatchType.TRANSLITERATION, MatchType.FUZZY]:
            status = MatchStatus.CONFIRMED_CANDIDATE
        elif composite_conf >= self.medium_threshold:
            status = MatchStatus.POSSIBLE_CANDIDATE
        elif composite_conf >= self.low_threshold:
            status = MatchStatus.UNCERTAIN
        else:
            status = MatchStatus.UNMATCHED

        breakdown = ScoreBreakdown(
            ocr_confidence=ocr_confidence,
            string_similarity=round(match_score, 4),
            match_type_bonus=0.15 if match_type in [MatchType.EXACT, MatchType.TRANSLITERATION] else 0.05,
            exact_alias_match=(match_type in [MatchType.EXACT, MatchType.ALIAS]),
            transliteration_match=(match_type == MatchType.TRANSLITERATION),
            dictionary_confidence=1.0 if top_cand.identifier else 0.8
        )

        return status, composite_conf, breakdown
