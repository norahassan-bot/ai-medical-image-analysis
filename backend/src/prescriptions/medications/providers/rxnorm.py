"""NLM RxNorm/RxNav API Provider for standardized medication concept resolution."""

import time
import logging
from typing import List, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base import MedicationInfoProvider
from ..schemas import MedicationConcept, MatchType

logger = logging.getLogger(__name__)


class RxNormProvider(MedicationInfoProvider):
    """Integrates with the US National Library of Medicine (NLM) RxNav REST API.
    
    Provides standardized medication concept resolution, RxCUI identifier mapping,
    exact name lookup, and approximate phonetic matching.
    """

    DEFAULT_BASE_URL = "https://rxnav.nlm.nih.gov/REST"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout_seconds: float = 3.0,
        max_retries: int = 2,
        cache_size: int = 500,
        offline_mode: bool = False
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds
        self.offline_mode = offline_mode
        self._cache: Dict[str, Any] = {}
        self.cache_size = cache_size

        # Configure resilient session
        self.session = requests.Session()
        retries = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "AIMedicalPrescriptionAnalysis/1.0"
        })

    @property
    def provider_name(self) -> str:
        return "RxNorm"

    @property
    def provider_version(self) -> str:
        return "NLM RxNav REST API (Current)"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def _save_to_cache(self, key: str, value: Any) -> None:
        if len(self._cache) >= self.cache_size:
            # Pop oldest item
            first_key = next(iter(self._cache))
            self._cache.pop(first_key, None)
        self._cache[key] = value

    def search(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Query RxNorm drugs.json endpoint for exact and standardized concept matches."""
        if self.offline_mode or not query or not query.strip():
            return []

        clean_query = query.strip()
        cache_key = f"drugs:{clean_query.lower()}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/drugs.json"
        params = {"name": clean_query}

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                logger.warning("RxNav drugs.json returned status %d for query %s", resp.status_code, clean_query)
                return []

            data = resp.json()
            concepts = self._parse_drugs_json(data, clean_query, limit)
            self._save_to_cache(cache_key, concepts)
            return concepts
        except (requests.RequestException, ValueError) as exc:
            logger.warning("RxNav search failed for '%s': %s", clean_query, str(exc))
            return []

    def get_by_identifier(self, identifier: str) -> Optional[MedicationConcept]:
        """Fetch RxCUI properties from RxNav."""
        if self.offline_mode or not identifier or not identifier.strip():
            return None

        clean_id = identifier.strip()
        cache_key = f"rxcui:{clean_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/rxcui/{clean_id}/properties.json"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code != 200:
                return None

            data = resp.json()
            props = data.get("properties", {})
            if not props:
                return None

            concept = MedicationConcept(
                identifier=str(props.get("rxcui", clean_id)),
                name=props.get("name", f"RxCUI {clean_id}"),
                brand_name=props.get("synonym"),
                source=self.provider_name,
                source_version=self.provider_version,
                match_score=1.0,
                match_type=MatchType.EXACT
            )
            self._save_to_cache(cache_key, concept)
            return concept
        except (requests.RequestException, ValueError) as exc:
            logger.warning("RxNav get_by_identifier failed for '%s': %s", clean_id, str(exc))
            return None

    def find_candidates(self, query: str, limit: int = 5) -> List[MedicationConcept]:
        """Search RxNav approximateTerm.json for approximate string & phonetic candidates."""
        if self.offline_mode or not query or not query.strip():
            return []

        clean_query = query.strip()
        cache_key = f"approx:{clean_query.lower()}:{limit}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Try exact search first
        exact_results = self.search(clean_query, limit=limit)
        if exact_results:
            self._save_to_cache(cache_key, exact_results)
            return exact_results

        # Fallback to approximateTerm
        url = f"{self.base_url}/approximateTerm.json"
        params = {
            "term": clean_query,
            "maxEntries": limit
        }

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code != 200:
                return []

            data = resp.json()
            candidates = self._parse_approximate_json(data, limit)
            self._save_to_cache(cache_key, candidates)
            return candidates
        except (requests.RequestException, ValueError) as exc:
            logger.warning("RxNav find_candidates failed for '%s': %s", clean_query, str(exc))
            return []

    def _parse_drugs_json(self, data: Dict[str, Any], query: str, limit: int) -> List[MedicationConcept]:
        """Parse structured concept groups returned by RxNav drugs.json."""
        results: List[MedicationConcept] = []
        drug_group = data.get("drugGroup", {})
        concept_group = drug_group.get("conceptGroup", [])

        for group in concept_group:
            concept_props = group.get("conceptProperties", [])
            for prop in concept_props:
                rxcui = str(prop.get("rxcui", ""))
                name = prop.get("name", "")
                synonym = prop.get("synonym", "")
                tty = prop.get("tty", "")

                if not name:
                    continue

                concept = MedicationConcept(
                    identifier=rxcui,
                    name=name,
                    brand_name=synonym if synonym else (name if tty in ["BN", "SBD", "BPCK"] else None),
                    generic_name=name if tty in ["IN", "PIN", "MIN", "SCD"] else None,
                    source=self.provider_name,
                    source_version=self.provider_version,
                    match_score=0.98 if query.lower() == name.lower() else 0.90,
                    match_type=MatchType.EXACT if query.lower() == name.lower() else MatchType.ALIAS,
                    aliases=[synonym] if synonym else []
                )
                results.append(concept)
                if len(results) >= limit:
                    return results

        return results

    def _parse_approximate_json(self, data: Dict[str, Any], limit: int) -> List[MedicationConcept]:
        """Parse candidates returned by RxNav approximateTerm.json."""
        results: List[MedicationConcept] = []
        approx_group = data.get("approximateGroup", {})
        candidates = approx_group.get("candidate", [])

        for cand in candidates:
            rxcui = str(cand.get("rxcui", ""))
            score_str = cand.get("score", "0")
            rank = cand.get("rank", "")

            try:
                score_val = float(score_str) / 100.0  # RxNav approximateTerm score is 0-100
            except ValueError:
                score_val = 0.5

            # If RXCUI is present, retrieve concept properties or create concept
            concept = self.get_by_identifier(rxcui)
            if concept:
                concept.match_score = round(score_val, 4)
                concept.match_type = MatchType.FUZZY
                results.append(concept)
            else:
                results.append(MedicationConcept(
                    identifier=rxcui or f"rxnav_approx_{rank}",
                    name=f"RxNorm Concept ({rxcui})" if rxcui else "Approximate Candidate",
                    source=self.provider_name,
                    source_version=self.provider_version,
                    match_score=round(score_val, 4),
                    match_type=MatchType.FUZZY
                ))

            if len(results) >= limit:
                break

        return results
