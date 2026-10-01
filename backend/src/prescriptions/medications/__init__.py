"""Medication Name Understanding, Normalization, and Matching module."""

from .schemas import (
    MatchStatus,
    MatchType,
    StrengthInfo,
    DosageFormInfo,
    MedicationConcept,
    CandidateItem,
    ScoreBreakdown,
    MedicationMatchResult
)
from .normalizer import MedicationTextNormalizer
from .candidate_generator import CandidateGenerator
from .confidence import ConfidencePolicy
from .matcher import MedicationMatcher
from .providers.base import MedicationInfoProvider
from .providers.rxnorm import RxNormProvider
from .providers.egypt import EgyptianMedicationProvider

__all__ = [
    "MatchStatus",
    "MatchType",
    "StrengthInfo",
    "DosageFormInfo",
    "MedicationConcept",
    "CandidateItem",
    "ScoreBreakdown",
    "MedicationMatchResult",
    "MedicationTextNormalizer",
    "CandidateGenerator",
    "ConfidencePolicy",
    "MedicationMatcher",
    "MedicationInfoProvider",
    "RxNormProvider",
    "EgyptianMedicationProvider"
]
