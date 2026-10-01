"""Duration instruction extractor parsing treatment length strictly from explicit text."""

import re
from typing import Optional
from .schemas import DurationInstruction, InstructionStatus
from .normalizer import InstructionTextNormalizer


SPECIAL_ARABIC_DURATIONS = [
    # English word counts
    (r"\b(?:for\s+)?one\s+weeks?\b", 1.0, "weeks"),
    (r"\b(?:for\s+)?two\s+weeks?\b", 2.0, "weeks"),
    (r"\b(?:for\s+)?one\s+months?\b", 1.0, "months"),
    (r"\b(?:for\s+)?two\s+months?\b", 2.0, "months"),
    (r"\b(?:for\s+)?one\s+days?\b", 1.0, "days"),
    (r"\b(?:for\s+)?two\s+days?\b", 2.0, "days"),

    # Arabic word counts
    (r"\b(?:لمدة\s+)?أسبوعين\b", 2.0, "weeks"),
    (r"\b(?:لمدة\s+)?اسبوعين\b", 2.0, "weeks"),
    (r"\b(?:لمدة\s+)?أسبوع\b", 1.0, "weeks"),
    (r"\b(?:لمدة\s+)?اسبوع\b", 1.0, "weeks"),
    (r"\b(?:لمدة\s+)?شهرين\b", 2.0, "months"),
    (r"\b(?:لمدة\s+)?شهر\b", 1.0, "months"),
    (r"\b(?:لمدة\s+)?يومين\b", 2.0, "days"),
    (r"\b(?:لمدة\s+)?يوم\b", 1.0, "days"),
    (r"\b(?:لمدة\s+)?عشرة\s+أيام\b", 10.0, "days"),
    (r"\b(?:لمدة\s+)?خمسة\s+أيام\b", 5.0, "days"),
    (r"\b(?:لمدة\s+)?ثلاثة\s+أيام\b", 3.0, "days"),
    (r"\b(?:لمدة\s+)?سبعة\s+أيام\b", 7.0, "days")
]

DURATION_UNIT_MAP = {
    "d": "days",
    "day": "days",
    "days": "days",
    "w": "weeks",
    "wk": "weeks",
    "wks": "weeks",
    "week": "weeks",
    "weeks": "weeks",
    "m": "months",
    "mo": "months",
    "mos": "months",
    "month": "months",
    "months": "months",
    "يوم": "days",
    "ايام": "days",
    "أيام": "days",
    "اسبوع": "weeks",
    "اسابيع": "weeks",
    "أسبوع": "weeks",
    "أسابيع": "weeks",
    "شهر": "months",
    "شهور": "months",
    "اشهر": "months"
}


class DurationExtractor:
    """Extracts explicit duration of therapy without guessing or inferring from drug identity."""

    @classmethod
    def extract(cls, raw_text: str) -> Optional[DurationInstruction]:
        if not raw_text or not raw_text.strip():
            return None

        clean_text = InstructionTextNormalizer.clean(raw_text)

        # 1. Check special Arabic word expressions first
        for pattern, val, unit in SPECIAL_ARABIC_DURATIONS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return DurationInstruction(
                    value=val,
                    unit=unit,
                    raw_text=match.group(0),
                    confidence=0.96,
                    status=InstructionStatus.PARSED
                )

        # 2. Match standard numeric patterns: "for 5 days", "5 days", "لمدة 5 أيام", "10 days", "for 2 weeks"
        units_str = r"(?:days?|d|weeks?|wks?|wk|months?|mos?|mo|يوم|ايام|أيام|اسبوع|اسابيع|أسبوع|أسابيع|شهر|شهور|اشهر)"
        duration_regex = re.compile(
            rf'(?:\b(?:for|لمدة)\s+)?(?<![a-zA-Z0-9\u0600-\u06FF])(\d+(?:\.\d+)?)\s*({units_str})\b',
            re.IGNORECASE
        )

        match = duration_regex.search(clean_text)
        if match:
            raw_match = match.group(0)
            val_str = match.group(1)
            raw_u = match.group(2).lower()
            
            try:
                val = float(val_str)
            except ValueError:
                val = 1.0

            normalized_unit = DURATION_UNIT_MAP.get(raw_u, raw_u)
            return DurationInstruction(
                value=val,
                unit=normalized_unit,
                raw_text=raw_match,
                confidence=0.95,
                status=InstructionStatus.PARSED
            )

        return None
