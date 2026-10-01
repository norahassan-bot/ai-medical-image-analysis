# Task 25 — Medication Information Retrieval & Prescription Instruction Parsing

## 1. Overview & Core Safety Principles

The **Prescription Understanding** subsystem extends the AI Medical Image Analysis platform by providing two strictly decoupled capabilities:
1. **Medication Information Retrieval:** Verified, educational drug facts (generic name, active ingredients, drug class, standard routes, general/common therapeutic indications) retrieved from trusted sources (e.g., RxNorm/RxNav and Egyptian Pharmaceutical Reference).
2. **Prescription Instruction Parsing:** Deterministic extraction and normalization of explicitly written dosing instructions (amount, units, frequency, intervals, duration, route, food/meal timing, PRN conditionality) directly from recognized prescription text.

```
                  Prescription Image / Handwriting Regions
                                      │
                                      ▼
                      Task 23 OCR / HTR Recognition
                                      │
                                      ▼
                      Task 24 Medication Normalization & Matching
                                      │
                ┌─────────────────────┴─────────────────────┐
                │                                           │
                ▼                                           ▼
   Medication Information Retrieval           Prescription Instruction Parsing
    (Verified Knowledge Sources)               (Explicit Written Text Only)
                │                                           │
                ▼                                           ▼
      Educational Drug Facts                   Structured Dosing Directives
      - Generic / Brand Names                  - Dose Value & Unit
      - Drug Classification                    - Frequency & Interval
      - General / Common Uses                  - Duration & Route
      - Source Attribution                     - Food / Meal Timing
                │                                           │
                └─────────────────────┬─────────────────────┘
                                      │
                                      ▼
                       PrescriptionUnderstandingResult
                   (Unified Structured Explanation & Audit)
```

### Strict Safety & Non-Prescribing Commitments
- **Zero Prescribing / Recommendation:** The system never prescribes, recommends medications, changes doses, or advises initiating or halting any treatment.
- **Zero Diagnosis Inference:** The system never infers or claims a patient-specific diagnosis or underlying disease from the prescribed medication (e.g., Omeprazole is described as "commonly used for acid-related conditions", never "prescribed because the patient has gastritis").
- **Zero Dosage / Frequency Hallucination:** The system never infers or defaults a patient's dose, frequency, or duration from general drug databases or clinical habits when absent in the prescription text. If a dose is unwritten, it is explicitly marked `None` / `"غير واضح من الروشتة"`.
- **Preserved Uncertainty:** Unclear, corrupted, or low-confidence handwriting tokens (e.g. `"1 tab ?? h"`) are flagged as `status: "uncertain"` rather than silently guessed.

> **Crucial Disclaimer:**  
> *"Medication information describes general uses and must not be interpreted as a diagnosis or as a recommendation for the individual patient."*  
> *"Prescription dose, frequency, and duration are extracted only from explicit readable prescription text. Values not clearly present are marked as unknown or uncertain."*

---

## 2. Architecture & Modules

The implementation is located under `backend/src/prescriptions/` and divided into specialized packages:

```
backend/src/prescriptions/
├── medications/
│   ├── info_service.py              # MedicationInfoService (Retrieval orchestrator)
│   ├── indication_parser.py         # MedicationIndicationResolver (Reference database)
│   ├── matcher.py                   # MedicationMatcher (from Task 24)
│   ├── normalizer.py                # MedicationNormalizer
│   └── schemas.py                   # Medication data contracts & source metadata
├── instructions/
│   ├── __init__.py                  # Instructions package exports
│   ├── parser.py                    # PrescriptionInstructionParser (Master parser)
│   ├── normalizer.py                # InstructionTextNormalizer (Numerals & script)
│   ├── dose.py                      # DoseExtractor (Values & units)
│   ├── frequency.py                 # FrequencyExtractor (Daily counts, intervals, PRN)
│   ├── duration.py                  # DurationExtractor (Days, weeks, months)
│   ├── route.py                     # RouteExtractor (Oral, topical, ophthalmic, etc.)
│   ├── food_timing.py               # FoodTimingExtractor (Before/after meals, bedtime)
│   └── schemas.py                   # Instruction data contracts & field confidence
└── prescription_understanding.py    # Master PrescriptionUnderstandingService
```

---

## 3. Medication Information Retrieval

### Provider-Based Resolution & Fallbacks
1. **RxNorm Provider:** Queries RxNav REST API endpoints (`/rxcui.json`, `/allrelated.json`, `/property.json`) for generic active ingredients, brand names, and RxCUI identifiers.
2. **MedicationIndicationResolver:** Provides curated pharmaceutical reference knowledge for essential medications across Egyptian and international formularies (e.g., Amoxicillin/Clavulanate, Omeprazole, Paracetamol, Metformin, Ciprofloxacin, Azithromycin, Diclofenac, etc.).
3. **Graceful Degradation:** If network connectivity fails or an external provider times out, the service returns `status: "provider_unavailable"` or `status: "unverified"`, preserving system stability and alerting the client transparently without crashing.

### Retrievable Fields
- `matched_name` / `brand_names`: Brand and commercial names.
- `generic_name`: Approved international nonproprietary name (INN).
- `active_ingredients`: List of active pharmaceutical ingredients (APIs).
- `drug_class`: Pharmacological / therapeutic classification (e.g., `Beta-lactam Antibiotic / Penicillin`).
- `general_uses` (EN & AR): Educational list of conditions the drug is commonly indicated for.
- `what_is_it` (EN & AR): Concise patient-friendly explanation in formal medical terminology.
- `source`: Provenance tracking including source name (`RxNorm`, `Egyptian Pharmaceutical Reference`), source ID, and retrieval timestamp.

---

## 4. Prescription Instruction Parsing Engine

### 4.1 Dose Extraction (`DoseExtractor`)
- **Supported Units:** Tablets, capsules, pills, drops, ml/cc, spoons/syrups, puffs, sachets, patches, injections/ampoules (`قرص`, `كبسولة`, `نقط`, `مل`, `ملعقة`, `بخاخ`, `كيس`, `حقنة`).
- **Numeric & Fraction Parsing:** Supports integers, decimals, fractions (`½`, `¼`, `3/4`), word forms (`one`, `two`, `half`, `قرص واحد`, `قرصين`, `نصف قرص`, `ملعقة واحدة`).
- **Safety Guarantee:** If no dosage unit or count is explicitly found in the instruction text, `dose` returns `None`.

### 4.2 Frequency Extraction (`FrequencyExtractor`)
- **Daily Counts:** Once daily (`مرة يومياً`, `1x/d`), twice daily (`مرتين يومياً`, `BID`), 3 times daily (`٣ مرات يومياً`, `TID`), 4 times daily (`QID`).
- **Hourly Intervals:** Every 4/6/8/12/24 hours (`كل ٨ ساعات`, `q8h`, `q12h`, `every 12 hours`), calculating equivalent `interval_hours` and `times_per_day`.
- **Conditionality (PRN):** `"as needed"`, `"PRN"`, `"عند اللزوم"`, `"عند الحاجة"` mapped to `frequency_type: "as_needed"`, leaving numeric frequency unforced.
- **Specific Timing:** Morning (`صباحاً`), evening (`مساءً`), bedtime (`HS`, `قبل النوم`).

### 4.3 Duration Extraction (`DurationExtractor`)
- **Supported Units:** Days (`أيام`), weeks (`أسابيع`), months (`شهور`).
- **Phrasing Patterns:** `"for 5 days"`, `"لمدة ٥ أيام"`, `"one week"`, `"أسبوعين"`, `"لمدة شهر"`.

### 4.4 Route Extraction (`RouteExtractor`)
- **Recognized Routes:** Oral (`PO`, `oral`, `عن طريق الفم`), Topical (`topical`, `دهان موضعي`), Ophthalmic (`eye drops`, `قطرة للعين`), Otic (`ear drops`, `قطرة للأذن`), Nasal (`nasal spray`, `بخاخ للأنف`), Inhaled (`inhalation`, `استنشاق`), Intramuscular (`IM`, `حقن عضلي`), Intravenous (`IV`, `حقن وريدي`), Rectal (`suppository`, `لبوس`).

### 4.5 Food & Meal Timing (`FoodTimingExtractor`)
- **Recognized Instructions:** Before food (`قبل الأكل`, `AC`), after food (`بعد الأكل`, `PC`), with food (`مع الأكل`), empty stomach (`على الريق`), before breakfast (`قبل الإفطار`), before sleep / bedtime (`قبل النوم`).

---

## 5. Arabic Script & Numerals Support

The engine features native bilingual support tailored for Middle Eastern prescription patterns:
- **Numeral Normalization:** Safely converts Eastern Arabic numerals (`٠, ١, ٢, ٣, ٤, ٥, ٦, ٧, ٨, ٩`) to standard floats/ints while retaining original raw tokens.
- **Orthographic Normalization:** Robust against common OCR spelling variations (e.g. `[ةه]`, `[يى]`, `[أإآا]`).
- **Bilingual Explanations:** Every output schema provides complete Arabic (RTL) and English (LTR) descriptions for UI rendering.

---

## 6. Confidence Scoring & Uncertainty Handling

Each parsed component maintains its own discrete confidence score:
$$\text{Confidence}_{\text{field}} = \text{OCR\_Confidence} \times \text{Parser\_Weight}$$

| Extraction Case | Field Confidence | Status | UI Treatment |
|---|---|---|---|
| Explicit match with clean OCR | $0.85 - 0.98$ | `confirmed` | Standard display |
| Ambiguous abbreviation or low OCR | $0.40 - 0.70$ | `uncertain` | Highlighted as uncertain |
| Corrupted token (e.g. `"?? h"`) | $< 0.40$ | `uncertain` | `"عدد مرات الاستخدام: غير واضح من الروشتة"` |
| Completely absent field | `None` | `not_found` | `"غير مذكور في الروشتة"` |

---

## 7. Example Output

```json
{
  "analysis_type": "prescription_understanding",
  "status": "completed",
  "prescription_id": "RX_EGY_001_DUAL_MED",
  "parser_version": "2.0.0",
  "disclaimer_ar": "تنبيه طبي: المعلومات الدوائية الواردة هي لأغراض تعليمية وإرشادية عامة ولا تعتبر تشخيصاً لحالة المريض أو توصية بالعلاج...",
  "disclaimer_en": "Medical Disclaimer: The medication information provided is for general educational reference only and must NOT be construed as a clinical diagnosis...",
  "medications": [
    {
      "raw_text": "Augmentin 1g tab",
      "ocr_confidence": 0.95,
      "medication": {
        "matched_name": "Augmentin",
        "generic_name": "Amoxicillin and Clavulanate Potassium",
        "active_ingredients": ["Amoxicillin", "Clavulanate potassium"],
        "source": "RxNorm"
      },
      "strength": {
        "value": 1.0,
        "unit": "g"
      },
      "dosage_form": {
        "form": "tablet"
      },
      "instructions": {
        "dose": {
          "value": 1.0,
          "unit": "tablet",
          "raw_text": "1 tab",
          "confidence": 0.90
        },
        "frequency": {
          "frequency_type": "interval",
          "times_per_day": 2,
          "interval_hours": 12,
          "raw_text": "every 12 hours",
          "confidence": 0.90
        },
        "duration": {
          "value": 7.0,
          "unit": "days",
          "raw_text": "for 7 days",
          "confidence": 0.90
        },
        "food_timing": {
          "timing": "after_food",
          "raw_text": "after food",
          "confidence": 0.85
        },
        "uncertain_fields": []
      },
      "medication_information": {
        "status": "verified",
        "generic_name": "Amoxicillin and Clavulanate Potassium",
        "drug_class": "Beta-lactam Antibiotic / Penicillin Combination",
        "general_uses": [
          "Treatment of bacterial infections including respiratory tract, otitis media, sinusitis, and skin infections."
        ],
        "general_uses_ar": [
          "علاج الالتهابات البكتيرية مثل عدوى الجهاز التنفسي والتهاب الأذن والجيوب الأنفية والمسالك البولية."
        ],
        "what_is_it": "Augmentin is an antibacterial combination medicine comprising amoxicillin and clavulanate potassium.",
        "what_is_it_ar": "أوجمنتين هو مضاد حيوي مركب يحتوي على أموكسيسيلين وحمض الكلافولانيك لمكافحة البكتيريا المقاومة.",
        "source": {
          "source_name": "RxNorm / Egyptian Reference",
          "source_id": "1114195"
        }
      }
    }
  ]
}
```

---

## 8. Known Limitations & Future Work

1. **Overlapping Multi-Drug Layouts:** In prescriptions where handwriting lines intersect without horizontal delimiters, line-to-medication bounding association relies on vertical proximity heuristic.
2. **Tapering / Titration Regimens:** Variable dosing regimens (e.g. "take 3 tabs day 1, 2 tabs day 2, 1 tab day 3") are parsed into their base step; full chronological titration graphs will be enhanced in subsequent safety verification tasks.
3. **Regional Non-Standard Abbreviations:** Highly localized physician shorthand not present in standard medical dictionaries defaults safely to `status: "uncertain"`.
