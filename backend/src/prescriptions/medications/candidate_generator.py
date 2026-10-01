"""Multi-tier medication candidate generation using deterministic, alias, transliteration, and fuzzy matching."""

import math
from typing import List, Dict, Any, Tuple, Optional, Set
from .schemas import CandidateItem, MatchType, MedicationConcept
from .providers.base import MedicationInfoProvider
from .normalizer import MedicationTextNormalizer


def levenshtein_dist(s1: str, s2: str) -> int:
    """Compute standard Levenshtein edit distance between two strings."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,      # Deletion
                dp[i][j - 1] + 1,      # Insertion
                dp[i - 1][j - 1] + cost # Substitution
            )
    return dp[m][n]


def normalized_levenshtein_similarity(s1: str, s2: str) -> float:
    """Normalized edit distance similarity between 0.0 and 1.0."""
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    s1_l, s2_l = s1.lower(), s2.lower()
    max_len = max(len(s1_l), len(s2_l))
    dist = levenshtein_dist(s1_l, s2_l)
    return max(0.0, 1.0 - (dist / max_len))


def jaro_similarity(s1: str, s2: str) -> float:
    """Compute Jaro similarity metric."""
    s1_l, s2_l = s1.lower(), s2.lower()
    l1, l2 = len(s1_l), len(s2_l)
    if l1 == 0 and l2 == 0:
        return 1.0
    if l1 == 0 or l2 == 0:
        return 0.0

    match_distance = (max(l1, l2) // 2) - 1
    s1_matches = [False] * l1
    s2_matches = [False] * l2

    matches = 0
    for i in range(l1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, l2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1_l[i] == s2_l[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    # Calculate transpositions
    k = 0
    transpositions = 0
    for i in range(l1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1_l[i] != s2_l[k]:
            transpositions += 1
        k += 1

    transpositions = transpositions / 2.0
    return ((matches / l1) + (matches / l2) + ((matches - transpositions) / matches)) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, prefix_scaling: float = 0.1) -> float:
    """Compute Jaro-Winkler similarity giving weight to common initial prefixes."""
    jaro = jaro_similarity(s1, s2)
    s1_l, s2_l = s1.lower(), s2.lower()
    prefix_len = 0
    max_prefix = min(4, min(len(s1_l), len(s2_l)))
    for i in range(max_prefix):
        if s1_l[i] == s2_l[i]:
            prefix_len += 1
        else:
            break
    return jaro + (prefix_len * prefix_scaling * (1.0 - jaro))


def ngram_dice_similarity(s1: str, s2: str, n: int = 2) -> float:
    """Compute character n-gram Dice similarity coefficient."""
    s1_l, s2_l = s1.lower(), s2.lower()
    if len(s1_l) < n or len(s2_l) < n:
        return 1.0 if s1_l == s2_l else 0.0

    s1_grams = {s1_l[i:i + n] for i in range(len(s1_l) - n + 1)}
    s2_grams = {s2_l[i:i + n] for i in range(len(s2_l) - n + 1)}

    intersection = len(s1_grams.intersection(s2_grams))
    total = len(s1_grams) + len(s2_grams)
    if total == 0:
        return 0.0
    return (2.0 * intersection) / total


def composite_string_similarity(query: str, target: str) -> float:
    """Weighted composite string similarity blending edit distance, Jaro-Winkler, and n-grams."""
    if not query or not target:
        return 0.0
    q_clean = query.strip().lower()
    t_clean = target.strip().lower()

    if q_clean == t_clean:
        return 1.0

    # Prefix match bonus for truncated handwriting tokens (e.g. "Augm..." -> "Augmentin")
    prefix_query = q_clean.rstrip(".")
    if len(prefix_query) >= 3 and t_clean.startswith(prefix_query):
        # High score proportional to prefix length relative to target
        prefix_ratio = len(prefix_query) / len(t_clean)
        return min(0.92, 0.70 + (0.22 * prefix_ratio))

    lev = normalized_levenshtein_similarity(q_clean, t_clean)
    jw = jaro_winkler_similarity(q_clean, t_clean)
    dice = ngram_dice_similarity(q_clean, t_clean, n=2)

    score = (0.45 * lev) + (0.35 * jw) + (0.20 * dice)
    return round(score, 4)


class CandidateGenerator:
    """Generates and ranks candidate medications through exact, transliteration, alias, and fuzzy pipelines."""

    def __init__(
        self,
        providers: List[MedicationInfoProvider],
        fuzzy_min_threshold: float = 0.45,
        max_candidates: int = 5
    ):
        self.providers = providers
        self.fuzzy_min_threshold = fuzzy_min_threshold
        self.max_candidates = max_candidates

    def generate_candidates(
        self,
        cleaned_query: str,
        transliteration_candidates: Optional[List[str]] = None
    ) -> List[CandidateItem]:
        """Generate ranked candidate medications for the query."""
        if not cleaned_query and not transliteration_candidates:
            return []

        candidates_map: Dict[str, CandidateItem] = {}

        # 1. Exact & Alias Search across providers with cleaned query
        if cleaned_query:
            for prov in self.providers:
                exact_concepts = prov.search(cleaned_query, limit=self.max_candidates)
                for concept in exact_concepts:
                    self._add_or_update_candidate(
                        candidates_map,
                        name=concept.name,
                        score=concept.match_score,
                        match_type=concept.match_type,
                        identifier=concept.identifier,
                        generic_name=concept.generic_name,
                        brand_name=concept.brand_name,
                        source=concept.source,
                        details={"catalog_entry": concept.model_dump()}
                    )

        # 2. Transliteration Search across providers with transliterated candidates
        for trans in (transliteration_candidates or []):
            for prov in self.providers:
                trans_concepts = prov.search(trans, limit=self.max_candidates)
                for concept in trans_concepts:
                    self._add_or_update_candidate(
                        candidates_map,
                        name=concept.name,
                        score=0.92,
                        match_type=MatchType.TRANSLITERATION,
                        identifier=concept.identifier,
                        generic_name=concept.generic_name,
                        brand_name=concept.brand_name,
                        source=concept.source,
                        details={"transliterated_from": trans, "catalog_entry": concept.model_dump()}
                    )

        # 3. If no high score candidates yet, run Provider find_candidates (RxNav approximate / local partials)
        has_high_score = any(c.score >= 0.85 for c in candidates_map.values())
        if not has_high_score and cleaned_query:
            for prov in self.providers:
                approx_concepts = prov.find_candidates(cleaned_query, limit=self.max_candidates)
                for concept in approx_concepts:
                    # Evaluate string similarity against concept name and brand name
                    sim_name = composite_string_similarity(cleaned_query, concept.name)
                    sim_brand = composite_string_similarity(cleaned_query, concept.brand_name or "")
                    best_sim = max(sim_name, sim_brand, concept.match_score)

                    if best_sim >= self.fuzzy_min_threshold:
                        self._add_or_update_candidate(
                            candidates_map,
                            name=concept.name,
                            score=best_sim,
                            match_type=MatchType.FUZZY,
                            identifier=concept.identifier,
                            generic_name=concept.generic_name,
                            brand_name=concept.brand_name,
                            source=concept.source,
                            details={"approximate_match": True}
                        )

        # 4. Fallback Fuzzy Matching against local provider known catalog entries
        if cleaned_query and len(candidates_map) < self.max_candidates:
            # Query providers with empty search or catalog records if accessible
            for prov in self.providers:
                if hasattr(prov, "_catalog"):
                    for rec in getattr(prov, "_catalog", []):
                        name = rec.get("name", "")
                        brand = rec.get("brand_name", "")
                        aliases = rec.get("aliases", [])
                        
                        sim_name = composite_string_similarity(cleaned_query, name)
                        sim_brand = composite_string_similarity(cleaned_query, brand) if brand else 0.0
                        sim_alias = max([composite_string_similarity(cleaned_query, a) for a in aliases]) if aliases else 0.0

                        best_sim = max(sim_name, sim_brand, sim_alias)
                        if best_sim >= self.fuzzy_min_threshold:
                            self._add_or_update_candidate(
                                candidates_map,
                                name=name,
                                score=round(best_sim, 4),
                                match_type=MatchType.FUZZY,
                                identifier=rec.get("identifier"),
                                generic_name=rec.get("generic_name"),
                                brand_name=rec.get("brand_name"),
                                source=prov.provider_name,
                                details={"fuzzy_score": best_sim}
                            )

        # Sort candidates descending by score
        ranked_candidates = sorted(candidates_map.values(), key=lambda c: c.score, reverse=True)
        return ranked_candidates[:self.max_candidates]

    def _add_or_update_candidate(
        self,
        candidates_map: Dict[str, CandidateItem],
        name: str,
        score: float,
        match_type: MatchType,
        identifier: Optional[str] = None,
        generic_name: Optional[str] = None,
        brand_name: Optional[str] = None,
        source: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add candidate or update score if a higher confidence path exists."""
        key = name.lower()
        if key in candidates_map:
            if score > candidates_map[key].score:
                candidates_map[key].score = score
                candidates_map[key].match_type = match_type
                if identifier:
                    candidates_map[key].identifier = identifier
                if source:
                    candidates_map[key].source = source
        else:
            candidates_map[key] = CandidateItem(
                name=name,
                score=round(score, 4),
                match_type=match_type,
                identifier=identifier,
                generic_name=generic_name,
                brand_name=brand_name,
                source=source,
                details=details or {}
            )
