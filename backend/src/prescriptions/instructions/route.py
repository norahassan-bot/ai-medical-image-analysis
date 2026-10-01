"""Route of administration extractor parsing explicit delivery routes from prescription text."""

import re
from typing import Optional
from .schemas import RouteInstruction, InstructionStatus
from .normalizer import InstructionTextNormalizer


ROUTE_PATTERNS = [
    # Oral
    (r"\b(?:by\s+mouth|oral(?:ly)?|p\.?o\.?|عن\s+طريق\s+الفم|فمويا|فموي|بلع)\b", "oral", 0.96),
    
    # Topical
    (r"\b(?:topical(?:ly)?|apply\s+topically|موضعيا|موضعي|دهان\s+موضعي|دهان)\b", "topical", 0.95),
    
    # Ophthalmic
    (r"\b(?:ophthalmic|eye\s+drops?|in\s+eye|قطرة\s+للعين|نقط\s+للعين|للعين)\b", "ophthalmic", 0.95),
    
    # Otic
    (r"\b(?:otic|ear\s+drops?|in\s+ear|قطرة\s+للأذن|قطرة\s+للاذن|للأذن|للاذن)\b", "otic", 0.95),
    
    # Nasal
    (r"\b(?:nasal(?:\s+spray)?|in\s+nose|بخاخ\s+للأنف|بخاخ\s+للانف|للأنف|للانف)\b", "nasal", 0.94),
    
    # Inhalation
    (r"\b(?:inhal(?:ed|ation)?|nebulizer|استنشاق|جلسات\s+استنشاق)\b", "inhalation", 0.94),
    
    # Intramuscular
    (r"\b(?:i\.?m\.?|intramuscular(?:ly)?|حقن\s+عضلي|عضل|بالعضل)\b", "intramuscular", 0.96),
    
    # Intravenous
    (r"\b(?:i\.?v\.?|intravenous(?:ly)?|حقن\s+وريدي|وريد|بالوريد)\b", "intravenous", 0.96),
    
    # Subcutaneous
    (r"\b(?:s\.?c\.?|subq|subcutaneous(?:ly)?|تحت\s+الجلد)\b", "subcutaneous", 0.95),
    
    # Sublingual
    (r"\b(?:sublingual(?:ly)?|s\.?l\.?|تحت\s+اللسان)\b", "sublingual", 0.96),
    
    # Rectal
    (r"\b(?:rectal(?:ly)?|suppository|لبوس\s+شرجي|شرجي|تحاميل)\b", "rectal", 0.95),
]


class RouteExtractor:
    """Extracts explicit route of administration without inferring from dosage form."""

    @classmethod
    def extract(cls, raw_text: str) -> Optional[RouteInstruction]:
        if not raw_text or not raw_text.strip():
            return None

        clean_text = InstructionTextNormalizer.clean(raw_text)

        for pattern, route_val, conf in ROUTE_PATTERNS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                return RouteInstruction(
                    route=route_val,
                    raw_text=match.group(0),
                    confidence=conf,
                    status=InstructionStatus.PARSED
                )

        return None
