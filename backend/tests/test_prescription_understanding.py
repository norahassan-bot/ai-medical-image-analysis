"""Comprehensive automated test suite for Medication Information Retrieval, Instruction Parsing, and Safety."""

import pytest
from unittest.mock import MagicMock, patch

from src.prescriptions.instructions.schemas import (
    InstructionStatus,
    FrequencyType,
    DoseInstruction,
    FrequencyInstruction,
    DurationInstruction,
    RouteInstruction,
    FoodTimingInstruction,
    ParsedPrescriptionInstructions
)
from src.prescriptions.instructions.normalizer import InstructionTextNormalizer
from src.prescriptions.instructions.dose import DoseExtractor
from src.prescriptions.instructions.frequency import FrequencyExtractor
from src.prescriptions.instructions.duration import DurationExtractor
from src.prescriptions.instructions.route import RouteExtractor
from src.prescriptions.instructions.food_timing import FoodTimingExtractor
from src.prescriptions.instructions.parser import PrescriptionInstructionParser

from src.prescriptions.medications.info_service import MedicationInfoService
from src.prescriptions.medications.indication_parser import MedicationIndicationResolver
from src.prescriptions.prescription_understanding import (
    PrescriptionUnderstandingService,
    PrescriptionUnderstandingResult
)


# ==============================================================================
# 1. MEDICATION INFORMATION RETRIEVAL TESTS (PART A)
# ==============================================================================

def test_medication_info_verified_augmentin():
    info_service = MedicationInfoService()
    info = info_service.get_medication_info("Augmentin")
    
    assert info["status"] == "verified"
    assert info["medication_name"] == "Augmentin"
    assert "Amoxicillin" in info["generic_name"]
    assert "Antibacterial" in info["drug_class"]
    assert len(info["general_uses"]) >= 2
    assert "respiratory" in str(info["general_uses"]).lower()
    assert info["source"] is not None
    assert "educational" in info["disclaimer"].lower()


def test_medication_info_verified_arabic_knowledge():
    info_service = MedicationInfoService()
    info = info_service.get_medication_info("Cataflam")
    
    assert info["status"] == "verified"
    assert info["brand_name"] == "Cataflam"
    assert "what_is_it_ar" in info
    assert len(info["general_uses_ar"]) >= 1


def test_medication_info_unknown_drug_unverified():
    info_service = MedicationInfoService()
    info = info_service.get_medication_info("Xyzzqweplk99")
    
    assert info["status"] == "unverified"
    assert info["generic_name"] is None
    assert info["general_uses"] == []
    assert "could not be verified" in info["message"].lower()


def test_medication_info_empty_input():
    info_service = MedicationInfoService()
    info = info_service.get_medication_info("")
    assert info["status"] == "unverified"


# ==============================================================================
# 2. DOSE EXTRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected_val,expected_unit", [
    ("1 tablet", 1.0, "tablet"),
    ("1 tab", 1.0, "tablet"),
    ("2 tablets", 2.0, "tablet"),
    ("5 ml", 5.0, "ml"),
    ("half tablet", 0.5, "tablet"),
    ("1/2 tab", 0.5, "tablet"),
    ("½ tab", 0.5, "tablet"),
    ("قرص واحد", 1.0, "tablet"),
    ("قرصين", 2.0, "tablet"),
    ("نصف قرص", 0.5, "tablet"),
    ("ملعقة واحدة", 1.0, "spoon"),
    ("٥ مل", 5.0, "ml")
])
def test_dose_extraction(input_text, expected_val, expected_unit):
    res = DoseExtractor.extract(input_text)
    assert res is not None
    assert res.value == expected_val
    assert res.unit == expected_unit
    assert res.status == InstructionStatus.PARSED


def test_dose_extraction_absent_is_none():
    # Only drug name and strength -> NO prescription dose written!
    res = DoseExtractor.extract("Augmentin 1g")
    assert res is None  # Never hallucinate a dose!


# ==============================================================================
# 3. FREQUENCY EXTRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected_type,expected_times,expected_interval", [
    ("once daily", FrequencyType.DAILY_COUNT, 1, 24),
    ("twice daily", FrequencyType.DAILY_COUNT, 2, 12),
    ("three times daily", FrequencyType.DAILY_COUNT, 3, 8),
    ("every 6 hours", FrequencyType.INTERVAL, 4, 6),
    ("every 8 hours", FrequencyType.INTERVAL, 3, 8),
    ("every 12 hours", FrequencyType.INTERVAL, 2, 12),
    ("مرة يومياً", FrequencyType.DAILY_COUNT, 1, 24),
    ("مرتين يومياً", FrequencyType.DAILY_COUNT, 2, 12),
    ("٣ مرات يومياً", FrequencyType.DAILY_COUNT, 3, 8),
    ("كل ٨ ساعات", FrequencyType.INTERVAL, 3, 8),
    ("كل ١٢ ساعة", FrequencyType.INTERVAL, 2, 12),
])
def test_frequency_extraction(input_text, expected_type, expected_times, expected_interval):
    res = FrequencyExtractor.extract(input_text)
    assert res is not None
    assert res.frequency_type == expected_type
    assert res.times_per_day == expected_times
    assert res.interval_hours == expected_interval
    assert res.status == InstructionStatus.PARSED


@pytest.mark.parametrize("input_text", [
    "PRN",
    "as needed",
    "عند اللزوم",
    "عند الحاجة"
])
def test_prn_frequency_extraction(input_text):
    res = FrequencyExtractor.extract(input_text)
    assert res is not None
    assert res.frequency_type == FrequencyType.AS_NEEDED
    assert res.is_prn is True
    assert res.times_per_day is None


def test_frequency_uncertainty_corrupted_ocr():
    res = FrequencyExtractor.extract("1 tab ?? h")
    assert res is not None
    assert res.frequency_type == FrequencyType.UNCERTAIN
    assert res.status == InstructionStatus.UNCERTAIN
    assert res.confidence <= 0.40


# ==============================================================================
# 4. DURATION EXTRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected_val,expected_unit", [
    ("for 5 days", 5.0, "days"),
    ("5 days", 5.0, "days"),
    ("one week", 1.0, "weeks"),
    ("1 week", 1.0, "weeks"),
    ("for 2 weeks", 2.0, "weeks"),
    ("٥ أيام", 5.0, "days"),
    ("لمدة ٥ أيام", 5.0, "days"),
    ("لمدة أسبوع", 1.0, "weeks"),
    ("أسبوعين", 2.0, "weeks"),
    ("لمدة شهر", 1.0, "months")
])
def test_duration_extraction(input_text, expected_val, expected_unit):
    res = DurationExtractor.extract(input_text)
    assert res is not None
    assert res.value == expected_val
    assert res.unit == expected_unit
    assert res.status == InstructionStatus.PARSED


def test_duration_absent_is_none():
    res = DurationExtractor.extract("Augmentin 1g 1 tab twice daily")
    assert res is None  # Duration not written -> must be None!


# ==============================================================================
# 5. FOOD TIMING & ROUTE EXTRACTION TESTS
# ==============================================================================

@pytest.mark.parametrize("input_text,expected_timing", [
    ("before food", "before_food"),
    ("after food", "after_food"),
    ("with food", "with_food"),
    ("before breakfast", "before_breakfast"),
    ("after meals", "after_food"),
    ("قبل الأكل", "before_food"),
    ("بعد الأكل", "after_food"),
    ("مع الأكل", "with_food"),
    ("على الريق", "empty_stomach"),
    ("قبل النوم", "bedtime")
])
def test_food_timing_extraction(input_text, expected_timing):
    res = FoodTimingExtractor.extract(input_text)
    assert res is not None
    assert res.timing == expected_timing
    assert res.status == InstructionStatus.PARSED


@pytest.mark.parametrize("input_text,expected_route", [
    ("by mouth", "oral"),
    ("oral", "oral"),
    ("apply topically", "topical"),
    ("eye drops", "ophthalmic"),
    ("ear drops", "otic"),
    ("IM", "intramuscular"),
    ("IV", "intravenous"),
    ("عن طريق الفم", "oral"),
    ("دهان موضعي", "topical"),
    ("قطرة للعين", "ophthalmic"),
    ("حقن عضلي", "intramuscular")
])
def test_route_extraction(input_text, expected_route):
    res = RouteExtractor.extract(input_text)
    assert res is not None
    assert res.route == expected_route
    assert res.status == InstructionStatus.PARSED


# ==============================================================================
# 6. MASTER INSTRUCTION PARSER TESTS
# ==============================================================================

def test_instruction_parser_full_complex_sentence():
    parser = PrescriptionInstructionParser()
    text = "Augmentin 1g 1 tab every 12 hours for 5 days after food"
    res = parser.parse(text)
    
    assert res.dose is not None
    assert res.dose.value == 1.0
    assert res.dose.unit == "tablet"
    
    assert res.frequency is not None
    assert res.frequency.interval_hours == 12
    assert res.frequency.times_per_day == 2
    
    assert res.duration is not None
    assert res.duration.value == 5.0
    assert res.duration.unit == "days"
    
    assert res.food_timing is not None
    assert res.food_timing.timing == "after_food"
    assert res.overall_confidence > 0.85


def test_instruction_parser_arabic_complex_sentence():
    parser = PrescriptionInstructionParser()
    text = "قرص مرتين يوميا بعد الاكل لمدة ٥ ايام"
    res = parser.parse(text)
    
    assert res.dose is not None
    assert res.dose.value == 1.0
    assert res.dose.unit == "tablet"
    
    assert res.frequency is not None
    assert res.frequency.times_per_day == 2
    
    assert res.duration is not None
    assert res.duration.value == 5.0
    assert res.duration.unit == "days"
    
    assert res.food_timing is not None
    assert res.food_timing.timing == "after_food"


# ==============================================================================
# 7. HIGH-LEVEL PRESCRIPTION UNDERSTANDING SERVICE TESTS
# ==============================================================================

def test_prescription_understanding_service_multi_medication():
    service = PrescriptionUnderstandingService()
    lines = [
        {"raw_text": "Augmentin 1g 1 tab twice daily for 7 days after food", "confidence": 0.95},
        {"raw_text": "Cataflam 50mg 1 tab PRN", "confidence": 0.92},
        {"raw_text": "Omeprazole 20mg 1 cap before breakfast", "confidence": 0.90}
    ]
    
    result = service.understand_from_text(lines)
    assert result.analysis_type == "prescription_understanding"
    assert result.status == "completed"
    assert result.total_medications == 3
    assert len(result.medications) == 3
    
    # Medicine 1: Augmentin
    med1 = result.medications[0]
    assert med1.medication.matched_name == "Augmentin"
    assert med1.strength.value == 1.0
    assert med1.instructions.dose.value == 1.0
    assert med1.instructions.frequency.times_per_day == 2
    assert med1.instructions.duration.value == 7.0
    assert med1.instructions.food_timing.timing == "after_food"
    assert med1.medication_information["status"] == "verified"
    
    # Medicine 2: Cataflam
    med2 = result.medications[1]
    assert "Cataflam" in med2.medication.matched_name
    assert med2.instructions.prn is True
    assert med2.instructions.duration is None
    
    # Medicine 3: Omeprazole
    med3 = result.medications[2]
    assert med3.medication.matched_name.lower() == "omeprazole"
    assert med3.instructions.food_timing.timing == "before_breakfast"


# ==============================================================================
# 8. CRITICAL SAFETY & NEGATIVE TESTS (SECTION 31)
# ==============================================================================

def test_safety_never_infer_dose_from_medication_identity():
    """Verify system NEVER fabricates a dose when only medication name is recognized."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Augmentin 1g"])
    
    med = result.medications[0]
    # The prescription line contains NO dose instructions (e.g. '1 tab')
    assert med.instructions.dose is None


def test_safety_never_infer_frequency_from_medication_identity():
    """Verify system NEVER invents a frequency from drug identity or standard practices."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Augmentin 1g"])
    
    med = result.medications[0]
    assert med.instructions.frequency is None


def test_safety_never_infer_duration_from_medication_identity():
    """Verify system NEVER invents treatment duration (e.g. 5 days) without written text."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Amoxil 500mg 1 cap"])
    
    med = result.medications[0]
    assert med.instructions.duration is None


def test_safety_never_infer_diagnosis_or_clinical_intent():
    """Verify system NEVER states why doctor prescribed the drug or diagnoses patient."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Omeprazole 20mg"])
    
    dump_str = str(result.model_dump()).lower()
    forbidden_terms = [
        "patient has gastritis",
        "patient diagnosed with",
        "doctor prescribed this because",
        "you should take",
        "recommended treatment for you",
        "patient condition"
    ]
    for forb in forbidden_terms:
        assert forb not in dump_str


def test_safety_never_turn_general_knowledge_into_patient_instructions():
    """Verify educational general uses are NOT injected into prescription instructions."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Cidophage 500mg"])
    
    med = result.medications[0]
    # General knowledge has uses, but instructions must be empty!
    assert len(med.medication_information["general_uses"]) > 0
    assert med.instructions.dose is None
    assert med.instructions.frequency is None


def test_safety_uncertain_ocr_remains_uncertain():
    """Verify ambiguous or corrupted OCR instructions are explicitly marked uncertain."""
    service = PrescriptionUnderstandingService()
    result = service.understand_from_text(["Augmentin 1g ?? h"])
    
    med = result.medications[0]
    assert med.instructions.frequency is not None
    assert med.instructions.frequency.status == InstructionStatus.UNCERTAIN
    assert "frequency" in med.instructions.uncertain_fields
