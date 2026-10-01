"""Pydantic schemas for structured medication normalization, matching, and candidate ranking."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    """Clinical safety status categories for candidate identification."""
    CONFIRMED_CANDIDATE = "confirmed_candidate"
    POSSIBLE_CANDIDATE = "possible_candidate"
    UNCERTAIN = "uncertain"
    UNMATCHED = "unmatched"


class MatchType(str, Enum):
    """Matching strategy mechanism used to establish identity."""
    EXACT = "exact"
    ALIAS = "alias"
    TRANSLITERATION = "transliteration"
    FUZZY = "fuzzy"
    NONE = "none"


class StrengthInfo(BaseModel):
    """Extracted medication strength with numeric value and metric unit."""
    value: Optional[float] = Field(None, description="Numeric magnitude of the dose/strength")
    unit: Optional[str] = Field(None, description="Standardized measurement unit (e.g., mg, g, ml, %)")
    raw_text: str = Field(..., description="Preserved verbatim raw strength snippet from OCR")


class DosageFormInfo(BaseModel):
    """Extracted explicit dosage form representation."""
    form: str = Field(..., description="Standardized dosage form (e.g., tablet, capsule, syrup)")
    raw_text: str = Field(..., description="Preserved verbatim raw dosage form token (e.g., tab, cap, susp)")


class MedicationConcept(BaseModel):
    """Standardized medication concept representing canonical identity from RxNorm or local catalog."""
    identifier: str = Field(..., description="Unique concept ID (e.g. RxCUI or EDA registration code)")
    name: str = Field(..., description="Canonical product or generic display name")
    generic_name: Optional[str] = Field(None, description="Active generic substance name")
    brand_name: Optional[str] = Field(None, description="Proprietary trade / brand name")
    active_ingredients: List[str] = Field(default_factory=list, description="Constituent active pharmaceutical ingredients")
    dosage_form: Optional[str] = Field(None, description="Cataloged default dosage form")
    strength: Optional[str] = Field(None, description="Cataloged standard strength specification")
    manufacturer: Optional[str] = Field(None, description="Marketing authorization holder / pharmaceutical company")
    source: str = Field(default="RxNorm", description="Reference authority (RxNorm, EgyptianDrugAuthority, LocalCatalog)")
    source_version: Optional[str] = Field(None, description="Release version/date of the dictionary source")
    match_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized similarity/matching score")
    match_type: MatchType = Field(default=MatchType.NONE, description="Method of match identification")
    aliases: List[str] = Field(default_factory=list, description="Associated synonyms, brand aliases, or transliterations")


class CandidateItem(BaseModel):
    """Ranked alternative candidate option for uncertain handwriting recognition."""
    name: str = Field(..., description="Candidate medication name")
    score: float = Field(..., ge=0.0, le=1.0, description="Composite ranking score")
    match_type: MatchType = Field(..., description="Matching method used")
    identifier: Optional[str] = Field(None, description="Concept identifier if cataloged")
    generic_name: Optional[str] = Field(None, description="Generic ingredient title")
    brand_name: Optional[str] = Field(None, description="Brand title")
    source: Optional[str] = Field(None, description="Data source provider")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary provider metadata")


class ScoreBreakdown(BaseModel):
    """Transparent, explainable breakdown of candidate matching confidence."""
    ocr_confidence: Optional[float] = Field(None, description="Upstream handwriting recognition confidence")
    string_similarity: float = Field(0.0, ge=0.0, le=1.0, description="Edit distance / token similarity score")
    match_type_bonus: float = Field(0.0, ge=0.0, le=1.0, description="Bonus applied for exact/alias/transliteration match")
    exact_alias_match: bool = Field(False, description="Whether exact alias lookup was triggered")
    transliteration_match: bool = Field(False, description="Whether Arabic phonetic mapping was used")
    dictionary_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in catalog entry presence")


class MedicationMatchResult(BaseModel):
    """Full structured output of medication understanding, normalization, and matching."""
    raw_text: str = Field(..., description="Verbatim handwriting OCR text preserving original recognition output")
    normalized_text: str = Field(..., description="Normalized clean string representation")
    cleaned_medication_query: str = Field(..., description="Medication name extracted after peeling strength & form tokens")
    status: MatchStatus = Field(..., description="Clinical candidate status: confirmed, possible, uncertain, unmatched")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall calibrated confidence score")
    matched_medication: Optional[MedicationConcept] = Field(None, description="Top matched structured medication concept")
    strength: Optional[StrengthInfo] = Field(None, description="Explicitly extracted dosage strength (if visible)")
    dosage_form: Optional[DosageFormInfo] = Field(None, description="Explicitly extracted dosage form (if visible)")
    alternatives: List[CandidateItem] = Field(default_factory=list, description="Top-k alternative ranked medication candidates")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata, provider status, and score breakdown")
