"""Egyptian Medication Provider abstraction for domestic brand names, Arabic nomenclature, and future EDA ingestion."""

import logging
from typing import List, Optional, Dict, Any
from .base import MedicationInfoProvider
from ..schemas import MedicationConcept, MatchType
from ..normalizer import MedicationTextNormalizer

logger = logging.getLogger(__name__)


# Verified starter reference catalog of standard Egyptian domestic brand medications
# Note: Designed for extensible future ingestion from the official Egyptian Drug Authority (EDA).
SEED_EGYPTIAN_CATALOG: List[Dict[str, Any]] = [
    {
        "identifier": "EDA-EGY-001",
        "name": "Augmentin",
        "brand_name": "Augmentin",
        "arabic_name": "أوجمنتين",
        "generic_name": "Amoxicillin / Clavulanic Acid",
        "active_ingredients": ["Amoxicillin Trihydrate", "Clavulanate Potassium"],
        "dosage_form": "tablet",
        "strength": "1g",
        "manufacturer": "GlaxoSmithKline (GSK Egypt)",
        "aliases": ["Augmentin", "أوجمنتين", "اوجمنتين", "اوجمينتين", "Augmentin 1g", "Augmentin 625mg"]
    },
    {
        "identifier": "EDA-EGY-002",
        "name": "Cataflam",
        "brand_name": "Cataflam",
        "arabic_name": "كاتافلام",
        "generic_name": "Diclofenac Potassium",
        "active_ingredients": ["Diclofenac Potassium"],
        "dosage_form": "tablet",
        "strength": "50mg",
        "manufacturer": "Novartis Egypt",
        "aliases": ["Cataflam", "كاتافلام", "كتافلام", "كتافاست", "Catafast", "Cataflam 50mg"]
    },
    {
        "identifier": "EDA-EGY-003",
        "name": "Panadol",
        "brand_name": "Panadol",
        "arabic_name": "بانادول",
        "generic_name": "Paracetamol",
        "active_ingredients": ["Paracetamol"],
        "dosage_form": "tablet",
        "strength": "500mg",
        "manufacturer": "GlaxoSmithKline Consumer Healthcare",
        "aliases": ["Panadol", "بانادول", "بنادول", "Panadol Advance", "Panadol Extra", "Panadol 500mg"]
    },
    {
        "identifier": "EDA-EGY-004",
        "name": "Congestal",
        "brand_name": "Congestal",
        "arabic_name": "كونجستال",
        "generic_name": "Paracetamol / Pseudoephedrine / Chlorpheniramine",
        "active_ingredients": ["Paracetamol", "Pseudoephedrine HCl", "Chlorpheniramine Maleate"],
        "dosage_form": "tablet",
        "strength": "Combination",
        "manufacturer": "SIGMA Pharmaceuticals Egypt",
        "aliases": ["Congestal", "كونجستال", "كونجستل", "Congestal tab"]
    },
    {
        "identifier": "EDA-EGY-005",
        "name": "Antinal",
        "brand_name": "Antinal",
        "arabic_name": "أنتينال",
        "generic_name": "Nifuroxazide",
        "active_ingredients": ["Nifuroxazide"],
        "dosage_form": "capsule",
        "strength": "200mg",
        "manufacturer": "Amoun Pharmaceutical Co.",
        "aliases": ["Antinal", "أنتينال", "انتينال", "Antinal 200mg", "Antinal cap"]
    },
    {
        "identifier": "EDA-EGY-006",
        "name": "Flagyl",
        "brand_name": "Flagyl",
        "arabic_name": "فلاجيل",
        "generic_name": "Metronidazole",
        "active_ingredients": ["Metronidazole"],
        "dosage_form": "tablet",
        "strength": "500mg",
        "manufacturer": "Sanofi Egypt",
        "aliases": ["Flagyl", "فلاجيل", "فلاجيلين", "Flagyl 500mg"]
    },
    {
        "identifier": "EDA-EGY-007",
        "name": "Brufen",
        "brand_name": "Brufen",
        "arabic_name": "بروفين",
        "generic_name": "Ibuprofen",
        "active_ingredients": ["Ibuprofen"],
        "dosage_form": "tablet",
        "strength": "400mg",
        "manufacturer": "Abbott Egypt / Kahira Pharma",
        "aliases": ["Brufen", "بروفين", "بروفن", "Brufen 400mg", "Brufen 600mg"]
    },
    {
        "identifier": "EDA-EGY-008",
        "name": "Voltaren",
        "brand_name": "Voltaren",
        "arabic_name": "فولتارين",
        "generic_name": "Diclofenac Sodium",
        "active_ingredients": ["Diclofenac Sodium"],
        "dosage_form": "tablet",
        "strength": "100mg",
        "manufacturer": "Novartis Egypt",
        "aliases": ["Voltaren", "فولتارين", "فلترين", "Voltaren 100mg", "Voltaren 75mg amp"]
    },
    {
        "identifier": "EDA-EGY-009",
        "name": "Omeprazole",
        "brand_name": "Omeprazole",
        "arabic_name": "أوميبرازول",
        "generic_name": "Omeprazole",
        "active_ingredients": ["Omeprazole"],
        "dosage_form": "capsule",
        "strength": "20mg",
        "manufacturer": "SEDICO / EIPICO Egypt",
        "aliases": ["Omeprazole", "أوميبرازول", "اوميبرازول", "امبرازول", "Omeprazol", "Omeprazole 20mg"]
    },
    {
        "identifier": "EDA-EGY-010",
        "name": "Septazole",
        "brand_name": "Septazole",
        "arabic_name": "سيبتازول",
        "generic_name": "Sulfamethoxazole / Trimethoprim",
        "active_ingredients": ["Sulfamethoxazole", "Trimethoprim"],
        "dosage_form": "tablet",
        "strength": "800mg/160mg",
        "manufacturer": "Alexandria Pharmaceuticals",
        "aliases": ["Septazole", "سيبتازول", "سبتازول", "Septazole Forte"]
    },
    {
        "identifier": "EDA-EGY-011",
        "name": "Amoxil",
        "brand_name": "Amoxil",
        "arabic_name": "أموكسيل",
        "generic_name": "Amoxicillin",
        "active_ingredients": ["Amoxicillin"],
        "dosage_form": "capsule",
        "strength": "500mg",
        "manufacturer": "GlaxoSmithKline Egypt",
        "aliases": ["Amoxil", "أموكسيل", "اموكسيل", "Amoxil 500mg"]
    },
    {
        "identifier": "EDA-EGY-012",
        "name": "Klavimox",
        "brand_name": "Klavimox",
        "arabic_name": "كلافيموكس",
        "generic_name": "Amoxicillin / Clavulanic Acid",
        "active_ingredients": ["Amoxicillin", "Clavulanic Acid"],
        "dosage_form": "tablet",
        "strength": "1g",
        "manufacturer": "Eva Pharma",
        "aliases": ["Klavimox", "كلافيموكس", "كلافيموکس", "Klavimox 1g", "Klavimox 625mg"]
    },
    {
        "identifier": "EDA-EGY-013",
        "name": "Hibiotic",
        "brand_name": "Hibiotic",
        "arabic_name": "هاي بيوتك",
        "generic_name": "Amoxicillin / Clavulanic Acid",
        "active_ingredients": ["Amoxicillin", "Clavulanic Acid"],
        "dosage_form": "tablet",
        "strength": "1g",
        "manufacturer": "Amoun Pharmaceutical Co.",
        "aliases": ["Hibiotic", "هاي بيوتك", "هايبيوتك", "Hibiotic 1g", "Hibiotic 625mg"]
    },
    {
        "identifier": "EDA-EGY-014",
        "name": "Alphintern",
        "brand_name": "Alphintern",
        "arabic_name": "ألفينترن",
        "generic_name": "Chymotrypsin / Trypsin",
        "active_ingredients": ["Chymotrypsin", "Trypsin"],
        "dosage_form": "tablet",
        "strength": "300 units",
        "manufacturer": "Amoun Pharmaceutical Co.",
        "aliases": ["Alphintern", "ألفينترن", "الفينترن", "Alphintern tab"]
    },
    {
        "identifier": "EDA-EGY-015",
        "name": "Ciprocin",
        "brand_name": "Ciprocin",
        "arabic_name": "سيبروسين",
        "generic_name": "Ciprofloxacin",
        "active_ingredients": ["Ciprofloxacin HCl"],
        "dosage_form": "tablet",
        "strength": "500mg",
        "manufacturer": "EIPICO Egypt",
        "aliases": ["Ciprocin", "سيبروسين", "Ciprocin 500mg", "Ciprocin 750mg", "Ciprofloxacin"]
    },
    {
        "identifier": "EDA-EGY-016",
        "name": "Zithromax",
        "brand_name": "Zithromax",
        "arabic_name": "زيثروماكس",
        "generic_name": "Azithromycin",
        "active_ingredients": ["Azithromycin Dihydrate"],
        "dosage_form": "capsule",
        "strength": "500mg",
        "manufacturer": "Pfizer Egypt",
        "aliases": ["Zithromax", "زيثروماكس", "ازيثرومايسين", "أزيثرومايسين", "Zithromax 500mg"]
    },
    {
        "identifier": "EDA-EGY-017",
        "name": "Cidophage",
        "brand_name": "Cidophage",
        "arabic_name": "سيدوفاج",
        "generic_name": "Metformin HCl",
        "active_ingredients": ["Metformin Hydrochloride"],
        "dosage_form": "tablet",
        "strength": "500mg",
        "manufacturer": "Chemical Industries Development (CID)",
        "aliases": ["Cidophage", "سيدوفاج", "ميتفورمين", "Cidophage 500mg", "Cidophage 850mg", "Cidophage 1000mg"]
    },
    {
        "identifier": "EDA-EGY-018",
        "name": "Controloc",
        "brand_name": "Controloc",
        "arabic_name": "كونترولوك",
        "generic_name": "Pantoprazole",
        "active_ingredients": ["Pantoprazole Sodium"],
        "dosage_form": "tablet",
        "strength": "40mg",
        "manufacturer": "Takeda / Eva Pharma",
        "aliases": ["Controloc", "كونترولوك", "بانتوبرازول", "Controloc 40mg", "Controloc 20mg"]
    }
]


class EgyptianMedicationProvider(MedicationInfoProvider):
    """Local provider and schema abstraction for Egyptian domestic medications.
    
    Acts as a verified reference catalog and local search layer. Structured for
    future bulk ingestion of official Egyptian Drug Authority (EDA) registration datasets.
    """

    def __init__(self, catalog: Optional[List[Dict[str, Any]]] = None):
        self._catalog: List[Dict[str, Any]] = catalog or list(SEED_EGYPTIAN_CATALOG)
        self._id_index: Dict[str, Dict[str, Any]] = {item["identifier"]: item for item in self._catalog}

    @property
    def provider_name(self) -> str:
        return "EgyptianDrugAuthority_Seed"

    @property
    def provider_version(self) -> str:
        return "EDA-Reference-Catalog-v1.0"

    def register_record(self, record: Dict[str, Any]) -> None:
        """Register a single validated Egyptian medication record."""
        if not record.get("identifier"):
            raise ValueError("Record missing required 'identifier' field")
        self._catalog.append(record)
        self._id_index[record["identifier"]] = record

    def ingest_dataset(self, dataset: List[Dict[str, Any]]) -> int:
        """Bulk ingest verified Egyptian medication records."""
        count = 0
        for item in dataset:
            if "identifier" in item:
                self._catalog.append(item)
                self._id_index[item["identifier"]] = item
                count += 1
        return count

    def get_by_identifier(self, identifier: str) -> Optional[MedicationConcept]:
        """Fetch concept by unique Egyptian Drug identifier."""
        raw = self._id_index.get(identifier)
        if not raw:
            return None
        return self._to_concept(raw, match_score=1.0, match_type=MatchType.EXACT)

    def search(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Search canonical concepts by English name, Arabic name, generic name, or aliases."""
        if not query or not query.strip():
            return []

        clean_query = query.strip().lower()
        norm_ar_query = MedicationTextNormalizer.normalize_arabic(clean_query)
        results: List[MedicationConcept] = []

        for record in self._catalog:
            # 1. Exact Name / Brand match
            name = record.get("name", "").lower()
            brand = record.get("brand_name", "").lower()
            generic = record.get("generic_name", "").lower()
            ar_name = MedicationTextNormalizer.normalize_arabic(record.get("arabic_name", ""))
            aliases = [a.lower() for a in record.get("aliases", [])]
            norm_ar_aliases = [MedicationTextNormalizer.normalize_arabic(a) for a in record.get("aliases", [])]

            if clean_query in [name, brand]:
                results.append(self._to_concept(record, match_score=1.0, match_type=MatchType.EXACT))
            elif norm_ar_query and (norm_ar_query == ar_name or norm_ar_query in norm_ar_aliases):
                results.append(self._to_concept(record, match_score=1.0, match_type=MatchType.TRANSLITERATION))
            elif clean_query in aliases or clean_query in generic:
                results.append(self._to_concept(record, match_score=0.95, match_type=MatchType.ALIAS))
            elif name.startswith(clean_query) or (norm_ar_query and ar_name.startswith(norm_ar_query)):
                results.append(self._to_concept(record, match_score=0.90, match_type=MatchType.ALIAS))

            if len(results) >= limit:
                break

        return results

    def find_candidates(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Find candidate concepts with exact or partial matching."""
        return self.search(query, limit=limit)

    def _to_concept(self, record: Dict[str, Any], match_score: float, match_type: MatchType) -> MedicationConcept:
        """Convert internal dictionary to standard MedicationConcept."""
        return MedicationConcept(
            identifier=record["identifier"],
            name=record["name"],
            brand_name=record.get("brand_name"),
            generic_name=record.get("generic_name"),
            active_ingredients=record.get("active_ingredients", []),
            dosage_form=record.get("dosage_form"),
            strength=record.get("strength"),
            manufacturer=record.get("manufacturer"),
            source=self.provider_name,
            source_version=self.provider_version,
            match_score=match_score,
            match_type=match_type,
            aliases=record.get("aliases", [])
        )
