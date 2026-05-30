"""
CROSSROAD — Coalition & Faction Viewer
========================================
Maps party coalitions supporting Indonesian executive pairs,
and links every known party member to their coalition.

Data model:
  Coalition → set of parties → each party has members in govt
  e.g. Prabowo-Gibran Coalition:
    Core:    Gerindra, Golkar, PKB, Nasdem, Demokrat, PAN, PSI, PBB
    Support: Gelora, Partai Garuda, Partai Prima
    Opposition: PDIP (in 2024)

Usage:
  viewer.get_coalition("prabowo-gibran")
  → {name, parties, members, cross_party_connections, news_alignment}

  viewer.get_faction_for_person(slug)
  → {coalition, role_in_coalition, party, aligned_persons}

  viewer.get_all_coalitions()
  → list of all known coalitions with member counts
"""

import logging
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Known coalitions (seed data, updated from crawl) ─────────────────────────
# This is the ground truth for Indonesian political coalitions 2024-2029

COALITIONS: Dict[str, Dict] = {
    "prabowo-gibran-2024": {
        "name":       "Koalisi Indonesia Maju (KIM)",
        "election":   "Pilpres 2024",
        "president":  "Prabowo Subianto",
        "vp":         "Gibran Rakabuming Raka",
        "won":        True,
        "vote_pct":   58.59,
        "core_parties": [
            "Gerindra", "Golkar", "PKB", "Nasdem",
            "Demokrat", "PAN", "PSI", "PBB",
        ],
        "supporting_parties": [
            "Gelora", "Garuda", "PKN",
        ],
        "opposition_parties": [
            "PDIP",
        ],
        "cabinet": "Kabinet Merah Putih 2024-2029",
        "wiki_url": "https://id.wikipedia.org/wiki/Koalisi_Indonesia_Maju",
        "sources": [
            {"name": "Wikipedia KIM", "url": "https://id.wikipedia.org/wiki/Koalisi_Indonesia_Maju"},
            {"name": "KPU RI", "url": "https://pemilu.kpu.go.id"},
        ],
    },
    "anies-muhaimin-2024": {
        "name":       "Koalisi Perubahan",
        "election":   "Pilpres 2024",
        "president":  "Anies Baswedan",
        "vp":         "Muhaimin Iskandar",
        "won":        False,
        "vote_pct":   24.95,
        "core_parties":      ["PKS", "PKB", "Nasdem"],
        "supporting_parties":[],
        "opposition_parties":[],
        "wiki_url": "https://id.wikipedia.org/wiki/Koalisi_Perubahan_untuk_Persatuan",
        "sources": [
            {"name": "Wikipedia Koalisi Perubahan",
             "url": "https://id.wikipedia.org/wiki/Koalisi_Perubahan_untuk_Persatuan"},
        ],
    },
    "ganjar-mahfud-2024": {
        "name":       "Koalisi PDIP",
        "election":   "Pilpres 2024",
        "president":  "Ganjar Pranowo",
        "vp":         "Mahfud MD",
        "won":        False,
        "vote_pct":   16.47,
        "core_parties":      ["PDIP", "PPP", "Hanura", "Perindo"],
        "supporting_parties":[],
        "opposition_parties":[],
        "wiki_url": "https://id.wikipedia.org/wiki/Pemilihan_umum_presiden_Indonesia_2024",
        "sources": [
            {"name": "Wikipedia Pilpres 2024",
             "url": "https://id.wikipedia.org/wiki/Pemilihan_umum_presiden_Indonesia_2024"},
        ],
    },
}

# Faction alignment in DPR RI 2024-2029
DPR_FACTIONS: Dict[str, Dict] = {
    "Gerindra":  {"seats": 86,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "Golkar":    {"seats": 102, "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "PDIP":      {"seats": 110, "coalition": None,                   "position": "oposisi"},
    "PKB":       {"seats": 68,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "Nasdem":    {"seats": 69,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "PKS":       {"seats": 53,  "coalition": None,                   "position": "oposisi"},
    "Demokrat":  {"seats": 44,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "PAN":       {"seats": 48,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
    "PPP":       {"seats": 0,   "coalition": None,                   "position": "tidak lolos"},
    "Hanura":    {"seats": 0,   "coalition": None,                   "position": "tidak lolos"},
    "PSI":       {"seats": 18,  "coalition": "prabowo-gibran-2024", "position": "koalisi"},
}

# Media ownership and political alignment (for news bias scoring)
MEDIA_ALIGNMENT: Dict[str, Dict] = {
    "Metro TV":       {"owner": "Surya Paloh", "party": "Nasdem",  "bias": "nasdem"},
    "TV One":         {"owner": "Bakrie Group", "party": "Golkar",  "bias": "golkar"},
    "SCTV/Indosiar":  {"owner": "Elang Mahkota","party": None,      "bias": "neutral"},
    "Trans TV/Trans7":{"owner": "CT Corp",       "party": "Nasdem",  "bias": "nasdem"},
    "RCTI/MNC":       {"owner": "MNC Group",     "party": "Golkar",  "bias": "golkar"},
    "Kompas TV":      {"owner": "Kompas Gramedia","party": None,      "bias": "neutral"},
    "CNN Indonesia":  {"owner": "CT Corp",        "party": "Nasdem",  "bias": "slight_nasdem"},
    "Tempo":          {"owner": "Independent",    "party": None,      "bias": "investigative"},
    "Kompas":         {"owner": "Kompas Gramedia","party": None,      "bias": "neutral"},
    "Detik":          {"owner": "Chairul Tanjung","party": "Nasdem",  "bias": "slight_nasdem"},
    "Republika":      {"owner": "Harian Republika","party": None,     "bias": "islamist"},
    "Tribun":         {"owner": "Kompas Gramedia","party": None,      "bias": "neutral"},
    "JPNN":           {"owner": "Jawa Pos Group", "party": None,      "bias": "neutral"},
    "Antara":         {"owner": "State (BUMN)",   "party": None,      "bias": "government"},
}


class CoalitionViewer:
    def __init__(self, db, graph_db):
        self.db    = db
        self.graph = graph_db

    # ── Coalitions ────────────────────────────────────────────────────────────

    def get_all_coalitions(self) -> List[Dict]:
        """Return all known coalitions with metadata."""
        result = []
        for cid, c in COALITIONS.items():
            all_parties = c["core_parties"] + c.get("supporting_parties", [])
            result.append({
                "id":             cid,
                "name":           c["name"],
                "election":       c["election"],
                "president":      c["president"],
                "vp":             c["vp"],
                "won":            c["won"],
                "vote_pct":       c.get("vote_pct"),
                "total_parties":  len(all_parties),
                "core_parties":   c["core_parties"],
                "supporting":     c.get("supporting_parties", []),
                "opposition":     c.get("opposition_parties", []),
                "sources":        c.get("sources", []),
                "wiki_url":       c.get("wiki_url"),
            })
        return result

    async def get_coalition_members(self, coalition_id: str) -> Dict:
        """Get all government members belonging to a coalition's parties."""
        coalition = COALITIONS.get(coalition_id)
        if not coalition:
            return {"error": f"Coalition '{coalition_id}' not found"}

        all_parties = coalition["core_parties"] + coalition.get("supporting_parties", [])

        members_by_party: Dict[str, List[Dict]] = {}
        total = 0

        for party in all_parties:
            persons = await self.db.list_persons(party=party, limit=200)
            govt = [p for p in persons if p.get("role_type")]
            members_by_party[party] = govt
            total += len(govt)

        # DPR seats
        seats = sum(
            DPR_FACTIONS.get(p, {}).get("seats", 0)
            for p in all_parties
        )

        return {
            "coalition":          coalition,
            "members_by_party":   members_by_party,
            "total_members":      total,
            "dpr_seats_total":    seats,
            "dpr_seats_needed":   280,  # majority
            "has_majority":       seats >= 280,
        }

    def get_faction_for_party(self, party: str) -> Optional[Dict]:
        """Get which coalition a party belongs to."""
        faction = DPR_FACTIONS.get(party, {})
        coalition_id = faction.get("coalition")
        coalition = COALITIONS.get(coalition_id) if coalition_id else None
        return {
            "party":          party,
            "coalition_id":   coalition_id,
            "coalition_name": coalition["name"] if coalition else None,
            "dpr_seats":      faction.get("seats", 0),
            "position":       faction.get("position", "unknown"),
        }

    def get_faction_for_person(self, party: str) -> Dict:
        """Map a person's party to their coalition faction."""
        return self.get_faction_for_party(party) if party else {
            "party": None, "coalition_id": None, "coalition_name": None,
            "dpr_seats": 0, "position": "unknown",
        }

    # ── Media bias ────────────────────────────────────────────────────────────

    def score_news_source_bias(self, outlet: str) -> Dict:
        """Return political bias metadata for a news outlet."""
        for key, val in MEDIA_ALIGNMENT.items():
            if key.lower() in outlet.lower() or outlet.lower() in key.lower():
                return {"outlet": outlet, **val}
        return {"outlet": outlet, "owner": "Unknown", "party": None, "bias": "unknown"}

    def explain_alignment_score(self, score: float, person_party: str, outlet: str) -> str:
        """
        Human-readable explanation of why an article got its alignment score.
        score: -1.0 (critical) to +1.0 (aligned)
        """
        bias = self.score_news_source_bias(outlet)
        outlet_party = bias.get("party")

        if score > 0.5:
            if outlet_party == person_party:
                return f"Berita positif dari {outlet} (media dekat {outlet_party}, partai yang sama)"
            return f"Konten mendukung posisi {person_party}"
        elif score < -0.5:
            if outlet_party and outlet_party != person_party:
                return f"Berita kritis dari {outlet} (media dekat {outlet_party}, berbeda partai)"
            return f"Konten kritis terhadap {person_party}"
        return f"Liputan netral/faktual dari {outlet}"

    # ── Cross-coalition analysis ───────────────────────────────────────────────

    async def find_cross_coalition_links(self) -> List[Dict]:
        """
        Find persons with ALLIED_WITH edges crossing coalition lines.
        These are politically significant — e.g. opposition member allied
        with a coalition member.
        """
        q = """
        MATCH (a:Person)-[r:ALLIED_WITH]->(b:Person)
        WHERE a.party <> b.party
          AND a.party IS NOT NULL AND b.party IS NOT NULL
        RETURN a.name AS from_name, a.party AS from_party,
               b.name AS to_name, b.party AS to_party,
               r.label AS label, r.source_url AS source
        LIMIT 100
        """
        links = []
        try:
            async with self.graph.driver.session() as s:
                result = await s.run(q)
                records = await result.data()
                for rec in records:
                    from_faction = self.get_faction_for_party(rec["from_party"])
                    to_faction   = self.get_faction_for_party(rec["to_party"])
                    cross = (from_faction.get("coalition_id") !=
                             to_faction.get("coalition_id"))
                    links.append({
                        **rec,
                        "from_coalition": from_faction.get("coalition_name"),
                        "to_coalition":   to_faction.get("coalition_name"),
                        "is_cross_coalition": cross,
                    })
        except Exception as e:
            logger.warning(f"cross-coalition query: {e}")
        return links

    # ── Pilkada coalition analysis ────────────────────────────────────────────

    async def get_regional_coalitions(self) -> List[Dict]:
        """
        Find regional executive pairs (gubernur, bupati, walikota) and
        reconstruct their supporting party coalition from news + graph data.
        """
        # Get all regional executives
        governors  = await self.db.list_persons(role_type="gubernur", limit=50)
        mayors     = await self.db.list_persons(role_type="walikota", limit=100)
        regents    = await self.db.list_persons(role_type="bupati",   limit=100)

        result = []
        for person in governors + mayors + regents:
            party = person.get("party")
            if not party:
                continue
            faction = self.get_faction_for_party(party)
            result.append({
                "name":           person.get("full_name",""),
                "slug":           person.get("slug",""),
                "role":           person.get("role_type",""),
                "region":         person.get("province",""),
                "party":          party,
                "coalition":      faction.get("coalition_name"),
                "coalition_id":   faction.get("coalition_id"),
                "dpr_position":   faction.get("position"),
            })

        return result
