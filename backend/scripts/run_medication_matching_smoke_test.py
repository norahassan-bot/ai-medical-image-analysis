"""Real Smoke Test for Medication Understanding, Normalization, and Concept Matching."""

import json
import time
from pathlib import Path
import sys

# Ensure backend directory is in path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.prescriptions.medications.matcher import MedicationMatcher
from src.prescriptions.medications.schemas import MatchStatus, MatchType


def run_smoke_test():
    print("=== Starting Real Medication Matching Smoke Test ===")
    
    # Initialize master matcher
    matcher = MedicationMatcher(enable_rxnorm=True, rxnorm_offline=False, rxnorm_timeout=3.0)

    test_scenarios = [
        {
            "scenario_id": "high_confidence_medicine",
            "description": "High-confidence clean recognized medicine with dosage form and strength",
            "raw_text": "Augmentin 1g tab",
            "ocr_confidence": 0.96
        },
        {
            "scenario_id": "ocr_space_split_error",
            "description": "OCR space splitting error on compound antibiotic",
            "raw_text": "Augm entin 1g",
            "ocr_confidence": 0.88
        },
        {
            "scenario_id": "ocr_character_substitution",
            "description": "OCR character substitution error (l instead of i)",
            "raw_text": "Augmentln 625mg",
            "ocr_confidence": 0.82
        },
        {
            "scenario_id": "difficult_handwritten_medicine",
            "description": "Difficult handwriting truncation and phonetic variant",
            "raw_text": "Omeprazol 20mg",
            "ocr_confidence": 0.78
        },
        {
            "scenario_id": "medicine_with_spaced_strength",
            "description": "Medication with explicit separated strength token",
            "raw_text": "Panadol 500 mg",
            "ocr_confidence": 0.94
        },
        {
            "scenario_id": "arabic_egyptian_brand",
            "description": "Arabic handwritten script for Egyptian market brand",
            "raw_text": "أوجمنتين 1 جم",
            "ocr_confidence": 0.91
        },
        {
            "scenario_id": "arabic_nsaid_brand",
            "description": "Arabic script for domestic NSAID Cataflam",
            "raw_text": "كاتافلام 50 مجم",
            "ocr_confidence": 0.89
        },
        {
            "scenario_id": "unmatched_nonsense_token",
            "description": "Completely ungrounded/nonsense OCR transcription",
            "raw_text": "Xyzzqweplk 999mg",
            "ocr_confidence": 0.35
        },
        {
            "scenario_id": "ambiguous_truncated_token",
            "description": "Ambiguous truncated token requiring uncertainty classification",
            "raw_text": "Co...",
            "ocr_confidence": 0.50
        }
    ]

    results = []
    latencies = []

    for item in test_scenarios:
        t0 = time.time()
        match_res = matcher.match(
            raw_text=item["raw_text"],
            ocr_confidence=item["ocr_confidence"]
        )
        elapsed_ms = round((time.time() - t0) * 1000, 2)
        latencies.append(elapsed_ms)

        res_dict = {
            "scenario_id": item["scenario_id"],
            "description": item["description"],
            "raw_text": match_res.raw_text,
            "normalized_text": match_res.normalized_text,
            "cleaned_medication_query": match_res.cleaned_medication_query,
            "result_status": match_res.status.value,
            "confidence": match_res.confidence,
            "matching_method": match_res.metadata.get("matching_method"),
            "matched_medication": match_res.matched_medication.model_dump() if match_res.matched_medication else None,
            "strength": match_res.strength.model_dump() if match_res.strength else None,
            "dosage_form": match_res.dosage_form.model_dump() if match_res.dosage_form else None,
            "candidates": [c.model_dump() for c in match_res.alternatives],
            "provider": match_res.matched_medication.source if match_res.matched_medication else "None",
            "latency_ms": elapsed_ms
        }
        results.append(res_dict)
        print(f"[{item['scenario_id']}] Raw: '{item['raw_text']}' -> Status: {match_res.status.value}, Match: '{match_res.matched_medication.name if match_res.matched_medication else 'None'}', Conf: {match_res.confidence} ({elapsed_ms}ms)")

    output_dir = Path(__file__).resolve().parent.parent.parent / "reports" / "prescription"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "medication_matching_smoke_test.json"

    smoke_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_scenarios_tested": len(results),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
        "scenarios": results,
        "summary": {
            "confirmed_candidates": sum(1 for r in results if r["result_status"] == MatchStatus.CONFIRMED_CANDIDATE.value),
            "possible_candidates": sum(1 for r in results if r["result_status"] == MatchStatus.POSSIBLE_CANDIDATE.value),
            "uncertain_candidates": sum(1 for r in results if r["result_status"] == MatchStatus.UNCERTAIN.value),
            "unmatched_candidates": sum(1 for r in results if r["result_status"] == MatchStatus.UNMATCHED.value)
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(smoke_report, f, indent=2, ensure_ascii=False)

    print(f"\nSmoke test completed successfully. Saved to: {output_path}")


if __name__ == "__main__":
    run_smoke_test()
