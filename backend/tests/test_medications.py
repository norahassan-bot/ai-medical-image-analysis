"""Comprehensive automated test suite for Medication Understanding, Normalization, Providers, Matching, and Safety."""

import pytest
from unittest.mock import MagicMock, patch
import requests

from src.prescriptions.medications.schemas import (
    MatchStatus,
    MatchType,
    MedicationConcept,
    CandidateItem,
    StrengthInfo,
    DosageFormInfo,
    MedicationMatchResult
)
from src.prescriptions.medications.normalizer import MedicationTextNormalizer
from src.prescriptions.medications.candidate_generator import (
    CandidateGenerator,
    levenshtein_dist,
    normalized_levenshtein_similarity,
    jaro_winkler_similarity,
    ngram_dice_similarity,
    composite_string_similarity
)
from src.prescriptions.medications.confidence import ConfidencePolicy
from src.prescriptions.medications.providers.base import MedicationInfoProvider
from src.prescriptions.medications.providers.egypt import EgyptianMedicationProvider, SEED_EGYPTIAN_CATALOG
from src.prescriptions.medications.providers.rxnorm import RxNormProvider
from src.prescriptions.medications.matcher import MedicationMatcher
from src.prescriptions.pipeline.prescription_pipeline import PrescriptionRecognitionPipeline
import numpy as np


# ==============================================================================
# 1. TEXT NORMALIZATION TESTS
# ==============================================================================

def test_normalization_whitespace_and_casing():
    normalizer = MedicationTextNormalizer()
    res1 = normalizer.normalize("  augmentin   ")
    assert res1["cleaned_query"] == "Augmentin"
    assert res1["raw_text"] == "  augmentin   "

    res2 = normalizer.normalize("AUGMENTIN")
    assert res2["cleaned_query"] == "Augmentin"


def test_normalization_ocr_space_splitting():
    normalizer = MedicationTextNormalizer()
    res = normalizer.normalize("Augm entin")
    assert "Augmentin" in res["normalized_text"]
    assert res["cleaned_query"] == "Augmentin"

    res_amox = normalizer.normalize("Amox icillin")
    assert "Amoxicillin" in res_amox["normalized_text"]


def test_normalization_ocr_character_substitutions():
    normalizer = MedicationTextNormalizer()
    # Augmentln (l instead of i)
    res1 = normalizer.normalize("Augmentln")
    assert res1["cleaned_query"] == "Augmentin"

    # Augment1n (1 instead of i)
    res2 = normalizer.normalize("Augment1n")
    assert res2["cleaned_query"] == "Augmentin"


def test_normalization_arabic_and_transliteration():
    normalizer = MedicationTextNormalizer()
    
    # Arabic Augmentin without diacritics
    res_ar1 = normalizer.normalize("اوجمنتين")
    assert "Augmentin" in res_ar1["transliteration_candidates"]

    # Arabic Augmentin with alef hamza
    res_ar2 = normalizer.normalize("أوجمنتين")
    assert "Augmentin" in res_ar2["transliteration_candidates"]

    # Arabic Cataflam
    res_cata = normalizer.normalize("كاتافلام")
    assert "Cataflam" in res_cata["transliteration_candidates"]

    # Arabic Panadol
    res_pan = normalizer.normalize("بانادول")
    assert "Panadol" in res_pan["transliteration_candidates"]


# ==============================================================================
# 2. STRENGTH & DOSAGE FORM EXTRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected_val,expected_unit", [
    ("Augmentin 500mg", 500.0, "mg"),
    ("Augmentin 500 mg", 500.0, "mg"),
    ("Panadol 1g", 1.0, "g"),
    ("Panadol 1 g", 1.0, "g"),
    ("Omeprazole 20mg", 20.0, "mg"),
    ("Syrup 5 ml", 5.0, "ml"),
    ("Eye Drops 0.5%", 0.5, "%"),
    ("Thyroxine 50mcg", 50.0, "mcg")
])
def test_strength_extraction(input_text, expected_val, expected_unit):
    normalizer = MedicationTextNormalizer()
    res = normalizer.normalize(input_text)
    assert res["strength"] is not None
    assert res["strength"].value == expected_val
    assert res["strength"].unit == expected_unit
    assert res["raw_text"] == input_text


@pytest.mark.parametrize("input_text,expected_form", [
    ("Augmentin 1g tab", "tablet"),
    ("Augmentin 1g tablet", "tablet"),
    ("Antinal 200mg cap", "capsule"),
    ("Antinal 200mg capsule", "capsule"),
    ("Cataflam syrup", "syrup"),
    ("Cefotax 1g vial", "vial"),
    ("Voltaren 75mg amp", "ampoule")
])
def test_dosage_form_extraction(input_text, expected_form):
    normalizer = MedicationTextNormalizer()
    res = normalizer.normalize(input_text)
    assert res["dosage_form"] is not None
    assert res["dosage_form"].form == expected_form


def test_dosage_form_absent_is_none():
    normalizer = MedicationTextNormalizer()
    res = normalizer.normalize("Augmentin 1g")
    assert res["dosage_form"] is None  # Never infer if not written!


# ==============================================================================
# 3. STRING SIMILARITY & CANDIDATE GENERATION TESTS
# ==============================================================================

def test_similarity_metrics():
    # Exact match
    assert normalized_levenshtein_similarity("Augmentin", "Augmentin") == 1.0
    assert jaro_winkler_similarity("Augmentin", "Augmentin") == 1.0
    assert ngram_dice_similarity("Augmentin", "Augmentin") == 1.0
    assert composite_string_similarity("Augmentin", "Augmentin") == 1.0

    # 1 OCR typo
    sim_typo = composite_string_similarity("Augmentin", "Augmentln")
    assert sim_typo > 0.85

    # Prefix truncation
    sim_prefix = composite_string_similarity("Augm...", "Augmentin")
    assert sim_prefix >= 0.70

    # Totally different words
    sim_diff = composite_string_similarity("Augmentin", "Paracetamol")
    assert sim_diff < 0.30


# ==============================================================================
# 4. PROVIDER TESTS (EGYPTIAN & RXNORM)
# ==============================================================================

def test_egyptian_provider_exact_and_arabic_search():
    provider = EgyptianMedicationProvider()
    
    # English brand search
    res_eng = provider.search("Augmentin")
    assert len(res_eng) >= 1
    assert res_eng[0].name == "Augmentin"
    assert res_eng[0].identifier == "EDA-EGY-001"
    assert res_eng[0].source == "EgyptianDrugAuthority_Seed"

    # Arabic search
    res_ar = provider.search("كاتافلام")
    assert len(res_ar) >= 1
    assert res_ar[0].name == "Cataflam"
    assert res_ar[0].match_type in [MatchType.TRANSLITERATION, MatchType.ALIAS, MatchType.EXACT]


def test_egyptian_provider_future_ingestion():
    provider = EgyptianMedicationProvider()
    custom_record = {
        "identifier": "EDA-NEW-999",
        "name": "NewMedEGY",
        "brand_name": "NewMedEGY",
        "generic_name": "Generic Substance",
        "dosage_form": "tablet",
        "strength": "100mg",
        "aliases": ["NewMedEGY", "NewMed"]
    }
    provider.register_record(custom_record)
    found = provider.get_by_identifier("EDA-NEW-999")
    assert found is not None
    assert found.name == "NewMedEGY"


def test_rxnorm_provider_mocked_success():
    provider = RxNormProvider(timeout_seconds=2.0)
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "drugGroup": {
            "name": "Amoxicillin",
            "conceptGroup": [
                {
                    "tty": "IN",
                    "conceptProperties": [
                        {
                            "rxcui": "723",
                            "name": "Amoxicillin",
                            "synonym": "",
                            "tty": "IN"
                        }
                    ]
                }
            ]
        }
    }

    with patch.object(provider.session, "get", return_value=mock_response):
        concepts = provider.search("Amoxicillin")
        assert len(concepts) == 1
        assert concepts[0].identifier == "723"
        assert concepts[0].name == "Amoxicillin"
        assert concepts[0].source == "RxNorm"


def test_rxnorm_provider_timeout_graceful_handling():
    provider = RxNormProvider(timeout_seconds=0.1)
    
    with patch.object(provider.session, "get", side_effect=requests.Timeout("Connection timed out")):
        concepts = provider.search("Amoxicillin")
        assert concepts == []  # Must return empty list, NOT crash!
        
        candidates = provider.find_candidates("Amoxicillin")
        assert candidates == []


def test_rxnorm_provider_http_500_graceful_handling():
    provider = RxNormProvider(timeout_seconds=1.0)
    mock_500 = MagicMock()
    mock_500.status_code = 500
    
    with patch.object(provider.session, "get", return_value=mock_500):
        concepts = provider.search("Amoxicillin")
        assert concepts == []


# ==============================================================================
# 5. MASTER MEDICATION MATCHER TESTS
# ==============================================================================

def test_matcher_exact_match():
    matcher = MedicationMatcher(rxnorm_offline=True)
    res = matcher.match("Augmentin 1g")
    
    assert res.status == MatchStatus.CONFIRMED_CANDIDATE
    assert res.matched_medication is not None
    assert res.matched_medication.name == "Augmentin"
    assert res.strength is not None
    assert res.strength.value == 1.0
    assert res.strength.unit == "g"
    assert res.confidence >= 0.85


def test_matcher_fuzzy_match():
    matcher = MedicationMatcher(rxnorm_offline=True)
    # Misspelled "Omeprazol" -> "Omeprazole"
    res = matcher.match("Omeprazol 20mg")
    assert res.matched_medication is not None
    assert res.matched_medication.name == "Omeprazole"
    assert res.status in [MatchStatus.CONFIRMED_CANDIDATE, MatchStatus.POSSIBLE_CANDIDATE]
    assert res.strength.value == 20.0


def test_matcher_arabic_transliteration():
    matcher = MedicationMatcher(rxnorm_offline=True)
    res = matcher.match("أوجمنتين 1 جم")
    assert res.matched_medication is not None
    assert res.matched_medication.name == "Augmentin"
    assert res.status in [MatchStatus.CONFIRMED_CANDIDATE, MatchStatus.POSSIBLE_CANDIDATE]


def test_matcher_unmatched_unknown_drug():
    matcher = MedicationMatcher(rxnorm_offline=True)
    # Random nonsense word
    res = matcher.match("Xyzzqweplk 999mg")
    assert res.status == MatchStatus.UNMATCHED
    assert res.matched_medication is None
    assert res.confidence < 0.40


def test_matcher_ambiguous_low_confidence():
    matcher = MedicationMatcher(rxnorm_offline=True)
    # Truncated partial token "Co..."
    res = matcher.match("Co")
    # Should not be high confidence confirmed!
    assert res.status in [MatchStatus.UNCERTAIN, MatchStatus.UNMATCHED, MatchStatus.POSSIBLE_CANDIDATE]
    assert res.status != MatchStatus.CONFIRMED_CANDIDATE


def test_matcher_batch_multi_medications():
    matcher = MedicationMatcher(rxnorm_offline=True)
    items = [
        {"raw_text": "Augmentin 1g tab", "confidence": 0.95},
        {"raw_text": "Cataflam 50mg", "confidence": 0.92},
        {"raw_text": "Panadol 500mg", "confidence": 0.90}
    ]
    results = matcher.match_batch(items)
    assert len(results) == 3
    assert results[0].matched_medication.name == "Augmentin"
    assert results[1].matched_medication.name == "Cataflam"
    assert results[2].matched_medication.name == "Panadol"


# ==============================================================================
# 6. SAFETY BOUNDARY TESTS (CRITICAL)
# ==============================================================================

def test_safety_no_clinical_recommendation_in_match_results():
    """Verify system NEVER outputs dosage schedules, duration, or disease indications."""
    matcher = MedicationMatcher(rxnorm_offline=True)
    res = matcher.match("Augmentin 1g")
    
    # Check match result dict
    dump = res.model_dump()
    forbidden_terms = [
        "twice daily",
        "take 1 tablet every 8 hours",
        "recommended dosage",
        "treatment for pneumonia",
        "indicated for infection",
        "patient diagnosed with",
        "for 7 days"
    ]
    dump_str = str(dump).lower()
    for term in forbidden_terms:
        assert term not in dump_str


def test_safety_uncertain_input_remains_uncertain():
    matcher = MedicationMatcher(rxnorm_offline=True)
    # Severely degraded token
    res = matcher.match("A..g..m")
    assert res.status != MatchStatus.CONFIRMED_CANDIDATE
    assert res.confidence < 0.85


# ==============================================================================
# 7. PIPELINE INTEGRATION TESTS
# ==============================================================================

def test_pipeline_integration_with_medication_matching():
    pipeline = PrescriptionRecognitionPipeline(device="cpu")
    canvas = np.full((600, 500, 3), 255, dtype=np.uint8)
    
    result = pipeline.analyze(canvas)
    assert result.analysis_type == "prescription"
    assert result.status == "completed"
    assert len(result.regions) >= 1
    
    first_region = result.regions[0]
    assert hasattr(first_region, "medication_status")
    assert hasattr(first_region, "medication_match")
    assert "matcher" in result.model_versions
