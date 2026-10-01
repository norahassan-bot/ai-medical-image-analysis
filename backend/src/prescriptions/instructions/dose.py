"""Dose instruction extractor parsing explicit dosage amounts and units from prescription text."""

import re
from typing import Optional, Tuple
from .schemas import DoseInstruction, InstructionStatus
from .normalizer import InstructionTextNormalizer


DOSE_UNIT_MAP = {
    # English
    "tab": "tablet",
    "tabs": "tablet",
    "tablet": "tablet",
    "tablets": "tablet",
    "cap": "capsule",
    "caps": "capsule",
    "capsule": "capsule",
    "capsules": "capsule",
    "ml": "ml",
    "cc": "ml",
    "spoon": "spoon",
    "spoons": "spoon",
    "tsp": "teaspoon",
    "tbsp": "tablespoon",
    "drop": "drops",
    "drops": "drops",
    "gtt": "drops",
    "gtts": "drops",
    "puff": "puff",
    "puffs": "puff",
    "sachet": "sachet",
    "sachets": "sachet",
    "amp": "ampoule",
    "ampoule": "ampoule",
    "vial": "vial",
    # Arabic
    "قرص": "tablet",
    "اقراص": "tablet",
    "كبسول": "capsule",
    "كبسولة": "capsule",
    "كبسولات": "capsule",
    "ملعقة": "spoon",
    "ملاعق": "spoon",
    "مل": "ml",
    "نقطة": "drops",
    "نقط": "drops",
    "قطرة": "drops",
    "قطرات": "drops",
    "بخة": "puff",
    "بخات": "puff",
    "كيس": "sachet",
    "اكياس": "sachet",
    "امبول": "ampoule",
    "حقنة": "ampoule"
}

# Arabic and English special word counts
SPECIAL_WORD_AMOUNTS = [
    # English word counts
    (r"\bhalf\s+(?:a\s+)?tablets?\b", 0.5, "tablet"),
    (r"\bhalf\s+(?:a\s+)?tabs?\b", 0.5, "tablet"),
    (r"\bhalf\s+(?:a\s+)?capsules?\b", 0.5, "capsule"),
    (r"\bhalf\s+(?:a\s+)?caps?\b", 0.5, "capsule"),
    (r"\bhalf\s+(?:a\s+)?spoons?\b", 0.5, "spoon"),
    (r"\bone\s+tablets?\b", 1.0, "tablet"),
    (r"\bone\s+tabs?\b", 1.0, "tablet"),
    (r"\btwo\s+tablets?\b", 2.0, "tablet"),
    (r"\btwo\s+tabs?\b", 2.0, "tablet"),
    
    # Arabic word counts (accounting for [ةه] and [يى])
    (r"\bنصف\s+قرص\b", 0.5, "tablet"),
    (r"\bقرص\s+ونصف\b", 1.5, "tablet"),
    (r"\bقرص\s+واحد\b", 1.0, "tablet"),
    (r"\bقرصين\b", 2.0, "tablet"),
    (r"\bنصف\s+كبسول(?:[ةه])?\b", 0.5, "capsule"),
    (r"\bكبسول(?:[ةه])?\s+واحد(?:[ةه])?\b", 1.0, "capsule"),
    (r"\bكبسولتين\b", 2.0, "capsule"),
    (r"\bنصف\s+ملعق(?:[ةه])?\b", 0.5, "spoon"),
    (r"\bملعق(?:[ةه])?\s+واحد(?:[ةه])?\b", 1.0, "spoon"),
    (r"\bملعقتين\b", 2.0, "spoon"),
    (r"\bملعق(?:[ةه])\s+صغير(?:[ةه])\b", 1.0, "teaspoon"),
    (r"\bملعق(?:[ةه])\s+كبير(?:[ةه])\b", 1.0, "tablespoon"),
    (r"\bكيس\s+واحد\b", 1.0, "sachet"),
    (r"\bكيسين\b", 2.0, "sachet"),
    (r"\bنصف\b", 0.5, "unit"),
]


class DoseExtractor:
    """Extracts explicit dose quantity and unit from prescription text without guessing."""

    @classmethod
    def extract(cls, raw_text: str) -> Optional[DoseInstruction]:
        if not raw_text or not raw_text.strip():
            return None

        clean_text = InstructionTextNormalizer.clean(raw_text)

        # 1. Check special word amounts first (English and Arabic)
        for pattern, val, unit in SPECIAL_WORD_AMOUNTS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return DoseInstruction(
                    value=val,
                    unit=unit,
                    raw_text=match.group(0),
                    confidence=0.96,
                    status=InstructionStatus.PARSED
                )

        # 2. Match numeric patterns with units: e.g. "1 tab", "2 tablets", "5 ml", "0.5 tab", "2 قرص"
        # Avoid matching strength patterns like "500mg" or "1g" as a dose unless followed by form
        unit_pattern_str = r"(?:tabs?|tablets?|caps?|capsules?|ml|cc|spoons?|tsp|tbsp|drops?|gtts?|puffs?|sachets?|amps?|vials?|قرص|اقراص|كبسول(?:ة|ات)?|ملعق(?:ة|ات)?|مل|نقط(?:ة)?|قطر(?:ة|ات)?|بخ(?:ة|ات)?|كيس|اكياس)"
        
        # Regex: optional decimal/int number followed by unit
        regex_standard = re.compile(
            rf'(?<![a-zA-Z0-9\u0600-\u06FF])(\d+(?:\.\d+)?)\s*({unit_pattern_str})\b',
            re.IGNORECASE
        )
        
        match = regex_standard.search(clean_text)
        if match:
            raw_match = match.group(0)
            val_str = match.group(1)
            raw_unit = match.group(2).lower()
            
            try:
                val = float(val_str)
            except ValueError:
                val = 1.0

            normalized_unit = DOSE_UNIT_MAP.get(raw_unit, raw_unit)
            return DoseInstruction(
                value=val,
                unit=normalized_unit,
                raw_text=raw_match,
                confidence=0.94,
                status=InstructionStatus.PARSED
            )

        # 3. Match standalone unit without explicit number (e.g. "take tab", "قرص بعد الأكل" -> 1 tablet)
        standalone_unit_regex = re.compile(
            rf'(?<!\d\s)(?<!\d)(?:take\s+)?({unit_pattern_str})(?!\s*\d)',
            re.IGNORECASE
        )
        match_standalone = standalone_unit_regex.search(clean_text)
        if match_standalone:
            raw_u = match_standalone.group(1).lower()
            normalized_u = DOSE_UNIT_MAP.get(raw_u, raw_u)
            # Only accept if not part of a strength string
            if normalized_u != "ml":
                return DoseInstruction(
                    value=1.0,
                    unit=normalized_u,
                    raw_text=match_standalone.group(0),
                    confidence=0.88,
                    status=InstructionStatus.PARSED
                )

        return None
