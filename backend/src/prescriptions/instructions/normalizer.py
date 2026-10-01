"""Instruction text normalizer converting Arabic numbers, fractions, and standardizing medical abbreviations."""

import re
import unicodedata
from typing import Dict, Any


# Mapping of Eastern Arabic numerals to Western Arabic numerals
EASTERN_ARABIC_DIGITS_MAP = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
}

# Mapping of fraction symbols
FRACTIONS_MAP = {
    '½': ' 0.5 ',
    '¼': ' 0.25 ',
    '¾': ' 0.75 ',
    '1/2': ' 0.5 ',
    '1/4': ' 0.25 ',
    '3/4': ' 0.75 '
}

# Arabic diacritics / tashkeel regex
ARABIC_DIACRITICS_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652]')


class InstructionTextNormalizer:
    """Normalizes raw prescription text before specialized token extraction."""

    @staticmethod
    def normalize_numbers(text: str) -> str:
        """Convert Eastern Arabic numerals (١, ٢, ٣, ...) to Western digits (1, 2, 3, ...)."""
        if not text:
            return ""
        for ar_digit, en_digit in EASTERN_ARABIC_DIGITS_MAP.items():
            text = text.replace(ar_digit, en_digit)
        return text

    @staticmethod
    def normalize_fractions(text: str) -> str:
        """Standardize Unicode and ASCII fraction representations into decimal strings."""
        if not text:
            return ""
        for frac, dec in FRACTIONS_MAP.items():
            text = text.replace(frac, dec)
        return text

    @staticmethod
    def normalize_arabic_script(text: str) -> str:
        """Standardize Arabic characters, remove diacritics/tashkeel, and unify letter variants."""
        if not text:
            return ""
        # Remove tashkeel/diacritics
        text = ARABIC_DIACRITICS_REGEX.sub('', text)
        # Remove tatweel (kashida)
        text = text.replace('ـ', '')
        # Unify Alefs
        text = re.sub(r'[أإآٱ]', 'ا', text)
        # Unify Yaa / Alef Maqsura
        text = text.replace('ى', 'ي')
        # Unify Taa Marbuta to Haa
        text = text.replace('ة', 'ه')
        # Unify Hamzas
        text = re.sub(r'[ؤئ]', 'ء', text)
        return text

    @classmethod
    def clean(cls, raw_text: str) -> str:
        """Execute full normalization pipeline on raw instruction string."""
        if not raw_text:
            return ""
        text = raw_text.strip()
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = cls.normalize_numbers(text)
        text = cls.normalize_fractions(text)
        text = cls.normalize_arabic_script(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
