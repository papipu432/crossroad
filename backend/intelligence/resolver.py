"""
CROSSROAD — Entity Resolver
==============================
Handles the problem where the same person appears under multiple names:
  "Rudy Mas'ud" = "H. Rudy Mas'ud" = "Gubernur Kaltim" = "Rudy Masud"
  "Prabowo"     = "Prabowo Subianto" = "Presiden Prabowo"

Resolution strategy:
  1. Normalized name matching (strip titles, normalize apostrophes)
  2. Slug similarity (edit distance)
  3. Cross-reference: same party + same region + overlapping role
  4. LLM disambiguation for ambiguous cases

Output: canonical slug + alias list stored in PostgreSQL
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from slugify import slugify

logger = logging.getLogger(__name__)

# Titles to strip when normalizing
TITLE_PREFIXES = [
    r"^h\.\s+", r"^hj\.\s+", r"^dr\.\s+", r"^drs\.\s+", r"^prof\.\s+",
    r"^ir\.\s+", r"^kh\.\s+", r"^ust\.\s+", r"^brigjen\s+", r"^mayjen\s+",
    r"^letjen\s+", r"^jenderal\s+", r"^irjen\s+", r"^komjen\s+",
    r"^purn\.\s+", r"^marsekal\s+",
]
TITLE_SUFFIXES = [
    r",?\s+s\.e\.?$", r",?\s+s\.h\.?$", r",?\s+m\.si\.?$", r",?\s+ph\.d\.?$",
    r",?\s+m\.m\.?$", r",?\s+s\.sos\.?$", r",?\s+m\.b\.a\.?$",
]

NICKNAME_MAP = {
    "Prabowo":  "Prabowo Subianto",
    "Jokowi":   "Joko Widodo",
    "Megawati": "Megawati Soekarnoputri",
    "SBY":      "Susilo Bambang Yudhoyono",
    "AHY":      "Agus Harimurti Yudhoyono",
    "Cak Imin": "Muhaimin Iskandar",
    "Gibran":   "Gibran Rakabuming Raka",
    "Anies":    "Anies Baswedan",
    "Ganjar":   "Ganjar Pranowo",
}


def normalize_name(name: str) -> str:
    """Normalize a name for comparison."""
    name = name.strip().lower()
    # Normalize apostrophes
    name = name.replace("'", "").replace("'", "").replace("`", "")
    # Strip titles
    for pattern in TITLE_PREFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    for pattern in TITLE_SUFFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def names_likely_same(name_a: str, name_b: str) -> Tuple[bool, float]:
    """
    Returns (is_same, confidence) for two names.
    Uses token overlap + normalized comparison.
    """
    norm_a = normalize_name(name_a)
    norm_b = normalize_name(name_b)

    if norm_a == norm_b:
        return True, 1.0

    # Check nickname map
    for nick, full in NICKNAME_MAP.items():
        if norm_a == nick.lower() and norm_b == normalize_name(full):
            return True, 0.95
        if norm_b == nick.lower() and norm_a == normalize_name(full):
            return True, 0.95

    # Token overlap
    tokens_a = set(norm_a.split())
    tokens_b = set(norm_b.split())
    if not tokens_a or not tokens_b:
        return False, 0.0

    intersection = tokens_a & tokens_b
    union        = tokens_a | tokens_b
    jaccard      = len(intersection) / len(union)

    # If one is a strict subset (nickname)
    if tokens_a.issubset(tokens_b) or tokens_b.issubset(tokens_a):
        if len(intersection) >= 2:
            return True, 0.85

    # High overlap
    if jaccard >= 0.7:
        return True, jaccard

    # Last-name + first-name match (Indonesian naming: surname last)
    if tokens_a and tokens_b:
        last_a = list(tokens_a)[-1]
        last_b = list(tokens_b)[-1]
        if last_a == last_b and len(last_a) >= 4:
            first_overlap = tokens_a & tokens_b - {last_a}
            if first_overlap:
                return True, 0.80

    return False, jaccard


def canonical_slug(name: str) -> str:
    """Generate canonical slug from name."""
    norm = normalize_name(name)
    return slugify(norm, separator="-")


class EntityResolver:
    """Resolves entity duplicates and builds an alias table."""

    def __init__(self, db):
        self.db = db
        self._cache: Dict[str, str] = {}  # alias → canonical slug

    async def build_alias_table(self) -> Dict[str, str]:
        """
        Scan all persons and find duplicates.
        Returns alias_map: {variant_name → canonical_slug}
        """
        persons = await self.db.list_persons(limit=5000)
        alias_map: Dict[str, str] = {}

        # Group by normalized name
        groups: Dict[str, List[Dict]] = {}
        for p in persons:
            name = p.get("full_name","") or p.get("name","")
            norm = normalize_name(name)
            if norm not in groups:
                groups[norm] = []
            groups[norm].append(p)

        # For each group with multiple entries, pick canonical (highest role weight)
        from intelligence.dynasties import ROLE_WEIGHTS
        for norm, group in groups.items():
            if len(group) == 1:
                continue
            # Pick canonical = highest-ranked person
            canonical = max(
                group,
                key=lambda p: ROLE_WEIGHTS.get(p.get("role_type",""), 0)
            )
            canon_slug = canonical.get("slug","")
            if not canon_slug:
                continue
            for p in group:
                if p is not canonical:
                    alias = p.get("slug","")
                    if alias:
                        alias_map[alias] = canon_slug

        # Also add nickname aliases
        for nick, full in NICKNAME_MAP.items():
            nick_slug = canonical_slug(nick)
            full_slug = canonical_slug(full)
            alias_map[nick_slug] = full_slug

        self._cache = alias_map
        return alias_map

    def resolve(self, slug: str) -> str:
        """Resolve a slug to its canonical form."""
        return self._cache.get(slug, slug)

    def are_same_entity(self, name_a: str, name_b: str) -> bool:
        same, conf = names_likely_same(name_a, name_b)
        return same and conf >= 0.75
