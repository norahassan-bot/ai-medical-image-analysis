"""Food and meal timing instruction extractor parsing meal relationships from explicit text."""

import re
from typing import Optional
from .schemas import FoodTimingInstruction, InstructionStatus
from .normalizer import InstructionTextNormalizer


FOOD_TIMING_PATTERNS = [
    # Before Breakfast / Empty stomach
    (r"\b(?:before\s+breakfast|قبل\s+الإفطار|قبل\s+الافطار|قبل\s+الفطار)\b", "before_breakfast", 0.96),
    (r"\b(?:after\s+breakfast|بعد\s+الإفطار|بعد\s+الافطار|بعد\s+الفطار)\b", "after_breakfast", 0.96),
    (r"(?:on\s+(?:an\s+)?empty\s+stomach|(?:على|علي)\s+الريق|(?:على|علي)\s+معد(?:[ةه])\s+فارغ(?:[ةه]))", "empty_stomach", 0.96),
    
    # Before Food / Meals
    (r"\b(?:before\s+(?:food|meals?|eating)|a\.?c\.?|قبل\s+الأكل|قبل\s+الاكل|قبل\s+الوجبات|قبل\s+الطعام)\b", "before_food", 0.95),
    
    # After Food / Meals
    (r"\b(?:after\s+(?:food|meals?|eating)|p\.?c\.?|بعد\s+الأكل|بعد\s+الاكل|بعد\s+الوجبات|بعد\s+الطعام)\b", "after_food", 0.95),
    
    # With Food / Meals
    (r"\b(?:with\s+(?:food|meals?)|during\s+meals?|مع\s+الأكل|مع\s+الاكل|وسط\s+الأكل|وسط\s+الاكل|اثناء\s+الاكل|أثناء\s+الأكل|مع\s+الوجبات)\b", "with_food", 0.95),
    
    # Bedtime / Sleep timing
    (r"\b(?:at\s+bedtime|before\s+sleep|قبل\s+النوم|عند\s+النوم)\b", "bedtime", 0.92),
]


class FoodTimingExtractor:
    """Extracts explicit food and meal timing relationships strictly from prescription text."""

    @classmethod
    def extract(cls, raw_text: str) -> Optional[FoodTimingInstruction]:
        if not raw_text or not raw_text.strip():
            return None

        clean_text = InstructionTextNormalizer.clean(raw_text)

        for pattern, timing_val, conf in FOOD_TIMING_PATTERNS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return FoodTimingInstruction(
                    timing=timing_val,
                    raw_text=match.group(0),
                    confidence=conf,
                    status=InstructionStatus.PARSED
                )

        return None
