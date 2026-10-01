"""Prescription medication text normalization, strength extraction, dosage form extraction, and Arabic transliteration."""

import re
import unicodedata
from typing import Tuple, Optional, List, Dict, Any
from .schemas import StrengthInfo, DosageFormInfo


# Comprehensive Arabic medicine name alias map (Egyptian market common catalog)
ARABIC_MEDICATION_MAP: Dict[str, str] = {
    "اوجمنتين": "Augmentin",
    "أوجمنتين": "Augmentin",
    "اوجمينتين": "Augmentin",
    "أوجمينتين": "Augmentin",
    "كاتافلام": "Cataflam",
    "كتافلام": "Cataflam",
    "كتافاست": "Catafast",
    "بانادول": "Panadol",
    "بنادول": "Panadol",
    "كونجستال": "Congestal",
    "كونجستل": "Congestal",
    "انتينال": "Antinal",
    "أنتينال": "Antinal",
    "فلاجيل": "Flagyl",
    "فلاجيلين": "Flagyl",
    "بروفين": "Brufen",
    "بروفن": "Brufen",
    "فولتارين": "Voltaren",
    "فلترين": "Voltaren",
    "اوميبرازول": "Omeprazole",
    "أوميبرازول": "Omeprazole",
    "امبرازول": "Omeprazole",
    "سيبتازول": "Septazole" ,
    "سبتازول": "Septazole",
    "اموكسيل": "Amoxil",
    "أموكسيل": "Amoxil",
    "كلافيموكس": "Klavimox",
    "هاي بيوتك": "Hibiotic",
    "هايبيوتك": "Hibiotic",
    "الفينترن": "Alphintern",
    "ألفينترن": "Alphintern",
    "ميجاموكس": "Megamox",
    "سيفوتاكس": "Cefotax",
    "كابوتن": "Capoten",
    "كونكور": "Concor",
    "زيرتك": "Zyrtec",
    "ديسفلاديل": "Disflatyl",
    "سبازموبيرالجين": "Spasmopyralgin",
    "ستربسلز": "Strepsils",
    "تلفاست": "Telfast",
    "اموكسيسيلين": "Amoxicillin",
    "أموكسيسيلين": "Amoxicillin",
    "باراسيتامول": "Paracetamol",
    "ايبوبروفين": "Ibuprofen",
    "إيبوبروفين": "Ibuprofen",
    "سيبروفلوكساسين": "Ciprofloxacin",
    "سيبروسين": "Ciprocin",
    "ازيثرومايسين": "Azithromycin",
    "أزيثرومايسين": "Azithromycin",
    "زيثروماكس": "Zithromax",
    "سيفيكسيم": "Cefixime",
    "جابتين": "Gaptin",
    "لانتوس": "Lantus",
    "ميتفورمين": "Metformin",
    "سيدوفاج": "Cidophage",
    "كابوزايد": "Capozide",
    "نابروكسين": "Naproxen",
    "رواتنكس": "Rowatinex",
    "يوريكول": "Uricol",
    "كولشيسين": "Colchicine",
    "بانتوبرازول": "Pantoprazole",
    "كونترولوك": "Controloc",
    "نيكسيوم": "Nexium",
    "اسبرين": "Aspirin",
    "أسبيرين": "Aspirin",
    "جوسبرين": "Jusprin"
}

# Common OCR space split merges for known pharmacological roots & drugs
COMMON_OCR_SPLIT_MERGES = [
    (r"\bAugm\s+entin\b", "Augmentin"),
    (r"\bAmox\s+icillin\b", "Amoxicillin"),
    (r"\bParace\s+tamol\b", "Paracetamol"),
    (r"\bCipro\s+floxacin\b", "Ciprofloxacin"),
    (r"\bCipro\s+cin\b", "Ciprocin"),
    (r"\bIbu\s+profen\b", "Ibuprofen"),
    (r"\bOmep\s+razole\b", "Omeprazole"),
    (r"\bKlavim\s+ox\b", "Klavimox"),
    (r"\bPana\s+dol\b", "Panadol"),
    (r"\bCata\s+flam\b", "Cataflam"),
    (r"\bAnti\s+nal\b", "Antinal"),
    (r"\bFla\s+gyl\b", "Flagyl"),
    (r"\bBru\s+fen\b", "Brufen"),
    (r"\bVol\s+taren\b", "Voltaren"),
    (r"\bSepta\s+zole\b", "Septazole"),
    (r"\bConges\s+tal\b", "Congestal"),
    (r"\bMetro\s+nidazole\b", "Metronidazole"),
    (r"\bAzithro\s+mycin\b", "Azithromycin"),
    (r"\bClavul\s+anate\b", "Clavulanate"),
    (r"\bCeph\s+alexin\b", "Cephalexin"),
    (r"\bAlphin\s+tern\b", "Alphintern")
]

# Standard dosage form normalization dictionary
DOSAGE_FORM_MAP: Dict[str, str] = {
    "tab": "tablet",
    "tabs": "tablet",
    "tablet": "tablet",
    "tablets": "tablet",
    "cap": "capsule",
    "caps": "capsule",
    "capsule": "capsule",
    "capsules": "capsule",
    "syr": "syrup",
    "syrup": "syrup",
    "susp": "suspension",
    "suspension": "suspension",
    "crm": "cream",
    "cream": "cream",
    "oint": "ointment",
    "ointment": "ointment",
    "gtt": "drops",
    "gtts": "drops",
    "drop": "drops",
    "drops": "drops",
    "inj": "injection",
    "injection": "injection",
    "amp": "ampoule",
    "amps": "ampoule",
    "ampoule": "ampoule",
    "ampoules": "ampoule",
    "ampule": "ampoule",
    "supp": "suppository",
    "suppositories": "suppository",
    "suppository": "suppository",
    "vial": "vial",
    "vials": "vial",
    "spray": "spray",
    "lotion": "lotion",
    "gel": "gel",
    "eff": "effervescent",
    "sachet": "sachet",
    "sachets": "sachet",
    "قرص": "tablet",
    "اقراص": "tablet",
    "أقراص": "tablet",
    "كبسول": "capsule",
    "كبسولة": "capsule",
    "كبسولات": "capsule",
    "شراب": "syrup",
    "معلق": "suspension",
    "مرهم": "ointment",
    "كريم": "cream",
    "قطرة": "drops",
    "نقط": "drops",
    "حقن": "injection",
    "حقنة": "injection",
    "امبول": "ampoule",
    "أمبول": "ampoule",
    "فوار": "effervescent",
    "اكياس": "sachet",
    "أكياس": "sachet",
    "كيس": "sachet",
    "لبوس": "suppository"
}

# Regex to detect strength expressions: "500mg", "500 mg", "1g", "1.5 g", "20mcg", "5 ml", "0.5%", "1 جم", "50 مجم", etc.
STRENGTH_REGEX = re.compile(
    r'(?<![a-zA-Z0-9\u0600-\u06FF])(\d+(?:\.\d+)?)\s*(mg|g|mcg|µg|ug|ml|mL|l|L|iu|IU|%|meq|mEq|مجم|ملجم|جم|ميكروجرام|مايكروجرام|مل|ملل)(?![a-zA-Z0-9\u0600-\u06FF])',
    re.IGNORECASE
)

# Regex to detect dosage form tokens
DOSAGE_FORM_REGEX = re.compile(
    r'\b(tablets?|tabs?|capsules?|caps?|syrups?|syr|suspensions?|susp|creams?|crm|ointments?|oint|drops?|gtts?|injections?|inj|ampoules?|ampules?|amps?|suppositor(?:y|ies)|supp|vials?|spray|lotion|gel|eff|sachets?)\b|(?<![a-zA-Z0-9\u0600-\u06FF])(اقراص|أقراص|قرص|كبسولات|كبسولة|كبسول|شراب|معلق|كريم|مرهم|قطرة|نقط|حقنة|حقن|أمبول|امبول|فوار|أكياس|اكياس|كيس|لبوس)(?![a-zA-Z0-9\u0600-\u06FF])',
    re.IGNORECASE
)

# Arabic diacritics / tashkeel regex
ARABIC_DIACRITICS_REGEX = re.compile(r'[\u0617-\u061A\u064B-\u0652]')


class MedicationTextNormalizer:
    """Robust text normalizer specifically tailored for prescription recognition outputs."""

    def __init__(self):
        pass

    @staticmethod
    def normalize_arabic(text: str) -> str:
        """Standardize Arabic characters, remove diacritics/tashkeel, unify alefs and yaas."""
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
        return text.strip()

    @staticmethod
    def contains_arabic(text: str) -> bool:
        """Checks if text contains Arabic Unicode characters."""
        return any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' for char in text)

    @staticmethod
    def transliterate_arabic_phonetic(arabic_text: str) -> List[str]:
        """Generate phonetic Latin transliteration candidates for Arabic medicine text."""
        norm_ar = MedicationTextNormalizer.normalize_arabic(arabic_text)
        if not norm_ar:
            return []

        # Check explicit market dictionary first
        if norm_ar in ARABIC_MEDICATION_MAP:
            return [ARABIC_MEDICATION_MAP[norm_ar]]

        # Check if individual words or segments match known map
        words = norm_ar.split()
        for w in words:
            if w in ARABIC_MEDICATION_MAP:
                return [ARABIC_MEDICATION_MAP[w]]

        # Phonetic mapping table
        charmap = {
            'ا': ['a', 'e', 'o'],
            'ب': ['b', 'p'],
            'ت': ['t'],
            'ث': ['th', 's'],
            'ج': ['g', 'j'],
            'ح': ['h', 'ha'],
            'خ': ['kh'],
            'د': ['d'],
            'ذ': ['z', 'th'],
            'ر': ['r'],
            'ز': ['z'],
            'س': ['s'],
            'ش': ['sh', 'ch'],
            'ص': ['s'],
            'ض': ['d'],
            'ط': ['t'],
            'ظ': ['z'],
            'ع': ['a', 'o', 'e'],
            'غ': ['gh', 'g'],
            'ف': ['f', 'v', 'ph'],
            'ق': ['k', 'q', 'c'],
            'ك': ['k', 'c'],
            'ل': ['l'],
            'م': ['m'],
            'ن': ['n'],
            'ه': ['h'],
            'و': ['o', 'u', 'w'],
            'ي': ['i', 'y', 'e'],
            'ء': ['']
        }

        # Simple primary phonetic transliteration
        primary = []
        for ch in norm_ar:
            if ch in charmap:
                primary.append(charmap[ch][0])
            elif ch.isalnum():
                primary.append(ch)

        candidate = "".join(primary).capitalize()
        return [candidate] if candidate else []

    def extract_strength(self, text: str) -> Tuple[Optional[StrengthInfo], str]:
        """Extract explicit strength token (e.g. '500mg', '1g', '1 جم') and return remaining string."""
        if not text:
            return None, text

        match = STRENGTH_REGEX.search(text)
        if not match:
            return None, text

        raw_match = match.group(0)
        val_str = match.group(1)
        unit_str = match.group(2).lower()
        
        # Normalize unit representations
        if unit_str in ['µg', 'ug', 'ميكروجرام', 'مايكروجرام']:
            unit_str = 'mcg'
        elif unit_str in ['مجم', 'ملجم']:
            unit_str = 'mg'
        elif unit_str in ['جم']:
            unit_str = 'g'
        elif unit_str in ['مل', 'ملل']:
            unit_str = 'ml'
        elif unit_str == 'l':
            unit_str = 'l'

        try:
            val = float(val_str)
        except ValueError:
            val = None

        strength_info = StrengthInfo(
            value=val,
            unit=unit_str,
            raw_text=raw_match.strip()
        )

        # Remove strength from text
        cleaned_text = STRENGTH_REGEX.sub(' ', text, count=1)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return strength_info, cleaned_text

    def extract_dosage_form(self, text: str) -> Tuple[Optional[DosageFormInfo], str]:
        """Extract explicit dosage form (e.g. 'tab', 'capsule', 'قرص') and return remaining string."""
        if not text:
            return None, text

        match = DOSAGE_FORM_REGEX.search(text)
        if not match:
            return None, text

        raw_token = match.group(0)
        normalized_form = DOSAGE_FORM_MAP.get(raw_token.lower(), raw_token.lower())

        dosage_form_info = DosageFormInfo(
            form=normalized_form,
            raw_text=raw_token
        )

        # Remove dosage form from text
        cleaned_text = DOSAGE_FORM_REGEX.sub(' ', text, count=1)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        return dosage_form_info, cleaned_text

    def normalize(self, raw_text: str) -> Dict[str, Any]:
        """Normalize raw prescription OCR text and extract components safely.
        
        Returns:
            Dict containing:
                - raw_text: unmodified string
                - normalized_text: cleaned string with unified casing/spacing
                - cleaned_query: stripped medication name for dictionary lookup
                - strength: StrengthInfo or None
                - dosage_form: DosageFormInfo or None
                - transliteration_candidates: List of Arabic->Latin candidates if applicable
        """
        if not raw_text or not raw_text.strip():
            return {
                "raw_text": raw_text or "",
                "normalized_text": "",
                "cleaned_query": "",
                "strength": None,
                "dosage_form": None,
                "transliteration_candidates": []
            }

        # 1. Base cleanup: remove line breaks, strip edges, normalize spaces
        clean = raw_text.strip()
        clean = re.sub(r'[\r\n\t]+', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean)

        # 2. Check for Arabic text
        transliteration_candidates: List[str] = []
        if self.contains_arabic(clean):
            norm_ar = self.normalize_arabic(clean)
            transliteration_candidates = self.transliterate_arabic_phonetic(clean)
            if norm_ar in ARABIC_MEDICATION_MAP:
                mapped_latin = ARABIC_MEDICATION_MAP[norm_ar]
                if mapped_latin not in transliteration_candidates:
                    transliteration_candidates.insert(0, mapped_latin)

        # 3. Correct OCR word splits (e.g. "Augm entin" -> "Augmentin")
        for pattern, replacement in COMMON_OCR_SPLIT_MERGES:
            clean = re.sub(pattern, replacement, clean, flags=re.IGNORECASE)

        # 4. Standardize spacing around numbers and units (e.g. "1 g" -> "1g", "500 mg" -> "500mg")
        clean = re.sub(r'(\d+)\s+(mg|g|mcg|µg|ug|ml|iu|%)\b', r'\1\2', clean, flags=re.IGNORECASE)

        # 5. Fix common internal OCR character substitutions when embedded in alpha tokens
        # e.g., "Augment1n" -> "Augmentin", "Augmentln" -> "Augmentin"
        clean = re.sub(r'\b([A-Za-z]+)1([A-Za-z]+)\b', r'\g<1>i\g<2>', clean)
        clean = re.sub(r'\b([A-Za-z]+)0([A-Za-z]+)\b', r'\g<1>o\g<2>', clean)
        clean = re.sub(r'\bAugmentln\b', 'Augmentin', clean, flags=re.IGNORECASE)

        # 6. Extract strength and dosage form from the cleaned line
        strength_info, without_strength = self.extract_strength(clean)
        dosage_form_info, without_form = self.extract_dosage_form(without_strength)

        # 7. Clean up leftover punctuation from the query string (e.g. trailing dots, commas, quotes)
        cleaned_query = re.sub(r'^[^\w\u0600-\u06FF]+|[^\w\u0600-\u06FF]+$', '', without_form).strip()
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query)

        # Retain capitalized casing for display if English
        if cleaned_query and not self.contains_arabic(cleaned_query):
            # Title case words
            cleaned_query = " ".join([w.capitalize() for w in cleaned_query.split()])

        return {
            "raw_text": raw_text,
            "normalized_text": clean,
            "cleaned_query": cleaned_query,
            "strength": strength_info,
            "dosage_form": dosage_form_info,
            "transliteration_candidates": transliteration_candidates
        }
