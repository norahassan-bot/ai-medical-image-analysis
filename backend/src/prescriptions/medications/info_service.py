"""Medication Information Retrieval Service fetching verified educational and clinical reference facts."""

import time
import logging
from typing import Optional, Dict, Any, List
from .schemas import MedicationConcept
from .providers.base import MedicationInfoProvider
from .providers.egypt import EgyptianMedicationProvider
from .providers.rxnorm import RxNormProvider
from .indication_parser import MedicationIndicationResolver

logger = logging.getLogger(__name__)


class MedicationInfoService:
    """Retrieves verified non-prescriptive medication information from authorized medical references."""

    def __init__(
        self,
        providers: Optional[List[MedicationInfoProvider]] = None,
        enable_rxnorm: bool = True,
        rxnorm_timeout: float = 3.0
    ):
        if providers is not None:
            self.providers = providers
        else:
            self.providers = [
                EgyptianMedicationProvider(),
                RxNormProvider(timeout_seconds=rxnorm_timeout, offline_mode=not enable_rxnorm)
            ]

    def get_medication_info(
        self,
        medication_name: str,
        generic_name: Optional[str] = None,
        identifier: Optional[str] = None,
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve verified medication information, pharmacological class, educational explanation, and general uses."""
        if not medication_name or not medication_name.strip():
            return {
                "status": "unverified",
                "message": "Medication name not provided.",
                "medication_name": None,
                "generic_name": None,
                "brand_name": None,
                "active_ingredients": [],
                "drug_class": None,
                "what_is_it": None,
                "general_uses": [],
                "route": None,
                "source": None,
                "disclaimer": self._disclaimer()
            }

        clean_name = medication_name.strip()
        
        # 1. Resolve knowledge repository facts first
        knowledge = MedicationIndicationResolver.resolve_knowledge(clean_name, generic_name)
        
        # 2. Query Providers for structured concept metadata
        matched_concept: Optional[MedicationConcept] = None
        if identifier:
            for prov in self.providers:
                try:
                    c = prov.get_by_identifier(identifier)
                    if c:
                        matched_concept = c
                        break
                except Exception as exc:
                    logger.warning("Provider lookup failed for %s: %s", identifier, exc)

        if not matched_concept:
            for prov in self.providers:
                try:
                    results = prov.search(clean_name, limit=1)
                    if results:
                        matched_concept = results[0]
                        break
                except Exception as exc:
                    logger.warning("Provider search failed for %s: %s", clean_name, exc)

        # 3. Assemble verified information payload
        if knowledge or matched_concept:
            gen_name = (knowledge.get("generic_name") if knowledge else None) or (matched_concept.generic_name if matched_concept else None)
            brand_name = (knowledge.get("canonical_name") if knowledge else None) or (matched_concept.brand_name if matched_concept else clean_name)
            act_ing = (knowledge.get("active_ingredients") if knowledge else None) or (matched_concept.active_ingredients if matched_concept else [])
            drug_class = knowledge.get("drug_class") if knowledge else "Pharmaceutical Medication"
            what_is_it = knowledge.get("what_is_it") if knowledge else f"{clean_name} is a standardized pharmaceutical product."
            what_is_it_ar = knowledge.get("what_is_it_ar") if knowledge else f"{clean_name} هو دواء طبي معتمد."
            general_uses = knowledge.get("general_uses") if knowledge else []
            general_uses_ar = knowledge.get("general_uses_ar") if knowledge else []
            route = (knowledge.get("standard_route") if knowledge else None) or (matched_concept.dosage_form if matched_concept else None)

            source_meta = {
                "name": matched_concept.source if matched_concept else "VerifiedPharmaceuticalKnowledgeBase",
                "id": matched_concept.identifier if matched_concept else f"KNOW-{clean_name.upper()}",
                "version": matched_concept.source_version if matched_concept else "v1.0-ClinicalRef",
                "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

            return {
                "status": "verified",
                "medication_name": clean_name,
                "generic_name": gen_name,
                "brand_name": brand_name,
                "active_ingredients": act_ing,
                "drug_class": drug_class,
                "what_is_it": what_is_it,
                "what_is_it_ar": what_is_it_ar,
                "general_uses": general_uses,
                "general_uses_ar": general_uses_ar,
                "route": route,
                "source": source_meta,
                "disclaimer": self._disclaimer()
            }

        # 4. If neither knowledge repository nor providers verified it
        return {
            "status": "unverified",
            "message": "Medication information could not be verified in reference databases.",
            "medication_name": clean_name,
            "generic_name": generic_name,
            "brand_name": clean_name,
            "active_ingredients": [],
            "drug_class": None,
            "what_is_it": f"{clean_name} is an unverified medication token.",
            "what_is_it_ar": f"{clean_name} لم يتم التحقق من معلوماته في قواعد البيانات المعتمدة.",
            "general_uses": [],
            "general_uses_ar": [],
            "route": None,
            "source": None,
            "disclaimer": self._disclaimer()
        }

    @staticmethod
    def _disclaimer() -> str:
        return (
            "Medication information describes general uses from verified medical references and is for educational purposes only. "
            "It does not constitute a prescription, diagnosis, clinical recommendation, or patient-specific treatment advice."
        )
