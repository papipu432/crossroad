"""
CROSSROAD — Dynasty Detector
================================
Detects political dynasties by finding family clusters with multiple
government positions. Works on both the Neo4j graph and PostgreSQL.

Detection logic:
  1. Find surname groups (Mas'ud, Soeharto, Yudhoyono, etc.)
  2. For each group, find members with government roles
  3. Score by: breadth of positions, govt levels, party control, region
  4. Classify: regional_dominant | national | cross_party | local

Example output:
  Keluarga Mas'ud (Kalimantan Timur)
    - Rudy Mas'ud      → Gubernur Kaltim        (Golkar)
    - Hasanuddin       → Ketua DPRD Kaltim       (Golkar)
    - Rahmad Mas'ud    → Wali Kota Balikpapan    (Golkar)
    - Syarifah Suraidah→ DPR RI Komisi VI        (Golkar) [istri]
    - Syahariah        → DPRD Kaltim             (Golkar)
    - Abdul Gafur      → Bupati PPU (mantan OTT) (Demokrat)
    - Alwi Al Qadri    → Ketua DPRD Balikpapan   (Golkar) [sepupu]
    Score: 9.1 | Type: regional_dominant
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

GOVT_ROLES = {
    "presiden", "wapres", "menteri", "gubernur",
    "bupati", "walikota", "dpr", "dprd",
}

ROLE_WEIGHTS = {
    "presiden": 10, "wapres": 9, "menteri": 7,
    "gubernur": 6,  "bupati": 5, "walikota": 5,
    "dpr": 4,       "dprd": 3,
}

LEVEL_MAP = {
    "presiden": "nasional", "wapres": "nasional",
    "menteri":  "nasional", "dpr":    "nasional",
    "gubernur": "provinsi", "dprd":   "provinsi",
    "bupati":   "lokal",    "walikota":"lokal",
}


class DynastyDetector:
    def __init__(self, graph_db, db):
        self.graph = graph_db
        self.db    = db

    # ── Public API ────────────────────────────────────────────────────────────

    async def detect_all(self, min_members: int = 2) -> List[Dict]:
        """Detect all dynasties across the full dataset."""
        persons = await self.db.list_persons(limit=3000)
        clusters = self._cluster_by_surname(persons)
        dynasties = []
        for cluster in clusters:
            d = self._analyze_cluster(cluster)
            if d and d["active_positions"] >= min_members:
                dynasties.append(d)
        dynasties.sort(key=lambda x: x["dynasty_score"], reverse=True)
        return dynasties

    async def detect_for_person(self, slug: str) -> Optional[Dict]:
        """Detect the dynasty that includes this person."""
        person = await self.db.get_person(slug)
        if not person:
            return None
        # Get their family from Neo4j
        cluster = await self._get_family_cluster_neo4j(slug)
        if not cluster:
            # Fallback: surname match from PG
            name = person.get("full_name","")
            surname = name.split()[-1].lower() if name else ""
            persons = await self.db.list_persons(limit=3000)
            cluster = [
                p for p in persons
                if surname and surname in (p.get("full_name","") or "").lower()
            ]
        if not cluster:
            cluster = [person]
        return self._analyze_cluster(cluster)

    # ── Clustering ────────────────────────────────────────────────────────────

    def _cluster_by_surname(self, persons: List[Dict]) -> List[List[Dict]]:
        """Group persons by shared surname tokens."""
        surname_map: Dict[str, List[Dict]] = defaultdict(list)
        for p in persons:
            name = p.get("full_name","") or p.get("name","")
            for token in self._surname_tokens(name):
                surname_map[token].append(p)

        seen_ids: Set[int] = set()
        clusters = []
        for token, group in surname_map.items():
            # Deduplicate
            cluster = []
            for p in group:
                pid = p.get("id") or id(p)
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    cluster.append(p)
            # Only keep if 2+ are in government
            govt = [p for p in cluster if p.get("role_type") in GOVT_ROLES]
            if len(govt) >= 2:
                clusters.append(cluster)

        return clusters

    def _surname_tokens(self, name: str) -> List[str]:
        """Extract candidate surname tokens from a full name."""
        if not name:
            return []
        words = [w.strip(".,") for w in name.split() if len(w) >= 4]
        tokens = []
        # Last name and second-to-last if multi-word
        if words:
            tokens.append(words[-1].lower())
        if len(words) >= 2:
            tokens.append(words[-2].lower())
        # Also handle hyphenated names (Rudy Mas'ud → masud)
        combined = name.lower().replace("'","").replace("-","")
        for word in combined.split():
            if len(word) >= 5 and word not in tokens:
                tokens.append(word)
        return list(set(tokens))

    async def _get_family_cluster_neo4j(self, slug: str) -> List[Dict]:
        """Get family members via Neo4j FAMILY_OF traversal."""
        q = """
        MATCH (center:Person {slug: $slug})
        OPTIONAL MATCH path = (center)-[:FAMILY_OF*1..3]-(relative:Person)
        RETURN center,
               collect(DISTINCT {
                 slug:     relative.slug,
                 name:     relative.name,
                 role_type:relative.role_type,
                 party:    relative.party,
                 province: relative.province,
                 position: relative.position
               }) AS relatives
        """
        try:
            async with self.graph.driver.session() as s:
                result = await s.run(q, {"slug": slug})
                rec = await result.single()
                if not rec:
                    return []
                center = dict(rec["center"])
                rels = [r for r in rec["relatives"] if r and r.get("slug")]
                return [center] + rels
        except Exception as e:
            logger.warning(f"Neo4j family cluster error: {e}")
            return []

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _analyze_cluster(self, cluster: List[Dict]) -> Optional[Dict]:
        if not cluster:
            return None

        govt_members = [
            p for p in cluster
            if p.get("role_type") in GOVT_ROLES
        ]
        if len(govt_members) < 2:
            return None

        names       = [p.get("full_name") or p.get("name","") for p in cluster]
        family_name = self._best_family_name(names)

        party_counts: Dict[str, int] = defaultdict(int)
        for p in govt_members:
            if p.get("party"):
                party_counts[p["party"]] += 1

        levels:  Set[str] = set()
        regions: Set[str] = set()
        for p in govt_members:
            lvl = LEVEL_MAP.get(p.get("role_type",""), "")
            if lvl:
                levels.add(lvl)
            prov = p.get("province","")
            if prov:
                regions.add(prov)

        head = max(govt_members,
                   key=lambda p: ROLE_WEIGHTS.get(p.get("role_type",""), 0),
                   default=govt_members[0])

        score = self._score(govt_members, levels, party_counts, regions)
        dtype = self._classify(levels, regions, party_counts)

        return {
            "family_name":      family_name,
            "head_person":      head.get("full_name") or head.get("name",""),
            "head_slug":        head.get("slug",""),
            "members":          self._fmt_members(govt_members, head),
            "total_family":     len(cluster),
            "active_positions": len(govt_members),
            "govt_levels":      sorted(levels),
            "parties":          dict(sorted(party_counts.items(), key=lambda x: -x[1])),
            "dominant_party":   max(party_counts, key=party_counts.get) if party_counts else None,
            "regions":          sorted(regions),
            "dynasty_score":    round(score, 1),
            "dynasty_type":     dtype,
        }

    def _best_family_name(self, names: List[str]) -> str:
        token_count: Dict[str, int] = defaultdict(int)
        for name in names:
            for tok in self._surname_tokens(name):
                token_count[tok] += 1
        if not token_count:
            return names[0].split()[-1] if names else "Unknown"
        best = max(token_count, key=token_count.get)
        return best.title()

    def _score(self, govt, levels, parties, regions) -> float:
        s = min(len(govt) * 0.9, 5.0)                        # breadth
        s += {3: 2.5, 2: 1.5}.get(len(levels), 0.5)          # level coverage
        total_w = sum(ROLE_WEIGHTS.get(p.get("role_type",""), 0) for p in govt)
        s += min(total_w / 14, 2.0)                           # role importance
        if len(parties) == 1:
            s += 0.5                                          # party lock
        if len(regions) == 1:
            s += 0.3                                          # regional concentration
        return min(s, 10.0)

    def _classify(self, levels, regions, parties) -> str:
        if "nasional" in levels and len(levels) >= 2:
            return "national_regional"
        if "nasional" in levels:
            return "national"
        if len(regions) == 1:
            return "regional_dominant"
        if len(parties) > 2:
            return "cross_party"
        return "regional"

    def _fmt_members(self, members, head) -> List[Dict]:
        out = []
        for m in members:
            out.append({
                "name":     m.get("full_name") or m.get("name",""),
                "slug":     m.get("slug",""),
                "role":     m.get("role_type",""),
                "position": m.get("current_position") or m.get("position",""),
                "party":    m.get("party",""),
                "region":   m.get("province",""),
                "is_head":  m is head,
            })
        return sorted(out, key=lambda x: ROLE_WEIGHTS.get(x["role"], 0), reverse=True)
