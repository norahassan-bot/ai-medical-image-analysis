"""Frequency instruction extractor parsing explicit daily counts, intervals, PRN, and timings."""

import re
from typing import Optional
from .schemas import FrequencyInstruction, FrequencyType, InstructionStatus
from .normalizer import InstructionTextNormalizer


# Explicit frequency patterns: (regex_pattern, frequency_type, times_per_day, interval_hours, specific_timing, is_prn, confidence)
FREQUENCY_PATTERNS = [
    # --- As Needed / PRN ---
    (r"\b(?:as\s+needed|prn|p\.r\.n\.)\b", FrequencyType.AS_NEEDED, None, None, None, True, 0.98),
    (r"(?:عند\s+اللزوم|عند\s+الحاج(?:[ةه])|وقت\s+الحاج(?:[ةه]))", FrequencyType.AS_NEEDED, None, None, None, True, 0.98),

    # --- Hourly Intervals (English & Arabic) ---
    (r"\b(?:every|q)\s*4\s*(?:hours?|h|hrs?)\b", FrequencyType.INTERVAL, 6, 4, None, False, 0.96),
    (r"\bكل\s+4\s+ساع(?:ات|[ةه])\b", FrequencyType.INTERVAL, 6, 4, None, False, 0.96),
    (r"\b(?:every|q)\s*6\s*(?:hours?|h|hrs?)\b", FrequencyType.INTERVAL, 4, 6, None, False, 0.96),
    (r"\bكل\s+6\s+ساع(?:ات|[ةه])\b", FrequencyType.INTERVAL, 4, 6, None, False, 0.96),
    (r"\b(?:every|q)\s*8\s*(?:hours?|h|hrs?)\b", FrequencyType.INTERVAL, 3, 8, None, False, 0.96),
    (r"\bكل\s+8\s+ساع(?:ات|[ةه])\b", FrequencyType.INTERVAL, 3, 8, None, False, 0.96),
    (r"\b(?:every|q)\s*12\s*(?:hours?|h|hrs?)\b", FrequencyType.INTERVAL, 2, 12, None, False, 0.96),
    (r"\bكل\s+12\s+ساع(?:[ةه]|ات)\b", FrequencyType.INTERVAL, 2, 12, None, False, 0.96),
    (r"\b(?:every|q)\s*24\s*(?:hours?|h|hrs?)\b", FrequencyType.INTERVAL, 1, 24, None, False, 0.96),
    (r"\bكل\s+24\s+ساع(?:[ةه]|ات)\b", FrequencyType.INTERVAL, 1, 24, None, False, 0.96),

    # --- Daily Counts (English) ---
    (r"\b(?:four\s+times\s+(?:daily|a\s+day)|4\s+times\s+(?:daily|a\s+day)|qid)\b", FrequencyType.DAILY_COUNT, 4, 6, None, False, 0.95),
    (r"\b(?:three\s+times\s+(?:daily|a\s+day)|3\s+times\s+(?:daily|a\s+day)|tid)\b", FrequencyType.DAILY_COUNT, 3, 8, None, False, 0.95),
    (r"\b(?:twice\s+(?:daily|a\s+day)|two\s+times\s+(?:daily|a\s+day)|2\s+times\s+(?:daily|a\s+day)|bid|bd)\b", FrequencyType.DAILY_COUNT, 2, 12, None, False, 0.95),
    (r"\b(?:once\s+(?:daily|a\s+day)|one\s+time\s+(?:daily|a\s+day)|1\s+time\s+(?:daily|a\s+day)|qd|od)\b", FrequencyType.DAILY_COUNT, 1, 24, None, False, 0.95),

    # --- Daily Counts (Arabic) ---
    (r"\b(?:اربع|4)\s+مرات\s+(?:يوميا|باليوم|في\s+اليوم)\b", FrequencyType.DAILY_COUNT, 4, 6, None, False, 0.96),
    (r"\b(?:ثلاث|3)\s+مرات\s+(?:يوميا|باليوم|في\s+اليوم)\b", FrequencyType.DAILY_COUNT, 3, 8, None, False, 0.96),
    (r"\b(?:مرتين|2\s+مرة)\s*(?:يوميا|باليوم|في\s+اليوم)?\b", FrequencyType.DAILY_COUNT, 2, 12, None, False, 0.95),
    (r"\b(?:صباحا\s+ومساء(?:ء)?)\b", FrequencyType.DAILY_COUNT, 2, 12, "صباحاً ومساءً", False, 0.94),
    (r"\b(?:مرة|1\s+مرة)\s+(?:يوميا|باليوم|في\s+اليوم)\b", FrequencyType.DAILY_COUNT, 1, 24, None, False, 0.95),
    (r"\bيوميا\b", FrequencyType.DAILY_COUNT, 1, 24, None, False, 0.85),

    # --- Specific Times ---
    (r"\b(?:at\s+bedtime|before\s+sleep|hs)\b", FrequencyType.SPECIFIC_TIME, 1, None, "bedtime", False, 0.92),
    (r"\b(?:قبل\s+النوم|عند\s+النوم)\b", FrequencyType.SPECIFIC_TIME, 1, None, "قبل النوم", False, 0.92),
    (r"\b(?:in\s+the\s+morning|morning)\b", FrequencyType.SPECIFIC_TIME, 1, None, "morning", False, 0.90),
    (r"\b(?:صباحا|في\s+الصباح)\b", FrequencyType.SPECIFIC_TIME, 1, None, "صباحاً", False, 0.90),
    (r"\b(?:in\s+the\s+evening|evening)\b", FrequencyType.SPECIFIC_TIME, 1, None, "evening", False, 0.90),
    (r"\b(?:مساء(?:ء)?|في\s+المساء)\b", FrequencyType.SPECIFIC_TIME, 1, None, "مساءً", False, 0.90),
]

# Patterns representing corrupted or ambiguous frequency OCR
UNCERTAIN_FREQUENCY_PATTERNS = [
    r"\?+\s*h\b",
    r"\d+\?\s*h\b",
    r"\?+\s*مرات",
    r"كل\s+\?+\s*ساع",
    r"(?:every|q)\s*\?+"
]


class FrequencyExtractor:
    """Extracts explicit frequency, administration intervals, and PRN flags from prescription text."""

    @classmethod
    def extract(cls, raw_text: str) -> Optional[FrequencyInstruction]:
        if not raw_text or not raw_text.strip():
            return None

        clean_text = InstructionTextNormalizer.clean(raw_text)

        # 1. Check for noisy or corrupted frequency snippets requiring explicit uncertainty flag
        for uncert_pattern in UNCERTAIN_FREQUENCY_PATTERNS:
            match = re.search(uncert_pattern, clean_text, re.IGNORECASE)
            if match:
                return FrequencyInstruction(
                    frequency_type=FrequencyType.UNCERTAIN,
                    times_per_day=None,
                    interval_hours=None,
                    raw_text=match.group(0),
                    confidence=0.30,
                    status=InstructionStatus.UNCERTAIN
                )

        # 2. Check explicit known patterns
        for pattern, freq_type, times, interval, timing, is_prn, conf in FREQUENCY_PATTERNS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return FrequencyInstruction(
                    frequency_type=freq_type,
                    times_per_day=times,
                    interval_hours=interval,
                    specific_timing=timing,
                    is_prn=is_prn,
                    raw_text=match.group(0),
                    confidence=conf,
                    status=InstructionStatus.PARSED
                )

        return None
