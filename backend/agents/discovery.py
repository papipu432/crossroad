"""
CROSSROAD — Discovery Crawler
Automatically discovers all Indonesian officials from:
  - Wikipedia list pages (DPR 575 members, DPRD, etc.)
  - Official government sites
  - Known seed lists as fallback

Returns: List[{name, role_type, party, province, wiki_url, source_url}]
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, quote

import httpx
from bs4 import BeautifulSoup
from slugify import slugify

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CrossroadBot/1.0; research)",
    "Accept-Language": "id,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ── Wikipedia discovery URLs ──────────────────────────────────────────────────
DISCOVERY_SOURCES = {
    "dpr": [
        "https://id.wikipedia.org/wiki/Daftar_anggota_Dewan_Perwakilan_Rakyat_2024%E2%80%932029",
        "https://id.wikipedia.org/wiki/Dewan_Perwakilan_Rakyat_Republik_Indonesia",
    ],
    "menteri": [
        "https://id.wikipedia.org/wiki/Kabinet_Merah_Putih",
        "https://id.wikipedia.org/wiki/Daftar_menteri_Indonesia",
    ],
    "gubernur": [
        "https://id.wikipedia.org/wiki/Daftar_gubernur_di_Indonesia",
        "https://id.wikipedia.org/wiki/Gubernur",
    ],
    "bupati": [
        "https://id.wikipedia.org/wiki/Daftar_bupati_dan_wali_kota_di_Indonesia",
    ],
    "dprd": [
        "https://id.wikipedia.org/wiki/Dewan_Perwakilan_Rakyat_Daerah_Provinsi",
        "https://id.wikipedia.org/wiki/Dewan_Perwakilan_Rakyat_Daerah",
    ],
}

PARTY_ALIASES = {
    "PDIP": ["PDIP","PDI-P","PDI PERJUANGAN","PERJUANGAN"],
    "Gerindra": ["GERINDRA","GERAKAN INDONESIA RAYA"],
    "Golkar": ["GOLKAR","PARTAI GOLKAR"],
    "PKB": ["PKB","KEBANGKITAN BANGSA"],
    "Demokrat": ["DEMOKRAT","PARTAI DEMOKRAT"],
    "PKS": ["PKS","KEADILAN SEJAHTERA"],
    "Nasdem": ["NASDEM","PARTAI NASDEM","NASIONAL DEMOKRAT"],
    "PAN": ["PAN","AMANAT NASIONAL"],
    "PPP": ["PPP","PERSATUAN PEMBANGUNAN"],
    "PSI": ["PSI","SOLIDARITAS INDONESIA"],
    "Hanura": ["HANURA","HATI NURANI"],
    "Perindo": ["PERINDO","PERSATUAN INDONESIA"],
    "PKN": ["PKN","KEBANGKITAN NUSANTARA"],
}


def normalize_party(text: str) -> Optional[str]:
    if not text:
        return None
    up = text.upper().strip()
    for party, aliases in PARTY_ALIASES.items():
        if any(a in up for a in aliases):
            return party
    # Short match
    for party in PARTY_ALIASES:
        if party.upper() in up:
            return party
    return None


class DiscoveryCrawler:
    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self._seen_slugs: set = set()

    async def _get(self, url: str, timeout: float = 25.0) -> Optional[BeautifulSoup]:
        await asyncio.sleep(self.delay)
        try:
            async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True,
                timeout=timeout, verify=False
            ) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return BeautifulSoup(r.text, "lxml")
                logger.debug(f"Discovery {r.status_code}: {url}")
        except Exception as e:
            logger.debug(f"Discovery error {url}: {e}")
        return None

    def _extract_name_party(self, cell_text: str) -> tuple[str, Optional[str]]:
        """Extract person name from table cell, strip party refs."""
        text = re.sub(r'\[.*?\]', '', cell_text).strip()
        # Remove parenthetical party refs
        party_match = re.search(r'\(([A-Z\-]+)\)', text)
        party = None
        if party_match:
            party = normalize_party(party_match.group(1))
            text = text[:party_match.start()].strip()
        # Clean up
        text = re.sub(r'\s+', ' ', text).strip()
        return text, party

    def _dedupe(self, name: str) -> bool:
        """Return True if new (not seen before)."""
        s = slugify(name, separator="-")
        if s in self._seen_slugs:
            return False
        self._seen_slugs.add(s)
        return True

    # ── DPR ──────────────────────────────────────────────────────────────────
    async def discover_dpr(self, limit: int = 575) -> List[Dict]:
        found = []
        for url in DISCOVERY_SOURCES["dpr"]:
            if len(found) >= limit:
                break
            soup = await self._get(url)
            if not soup:
                continue

            # Look for wikitables
            for table in soup.find_all("table", {"class": re.compile("wikitable")}):
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 2:
                        continue
                    # Name usually in col 1 or 2; try both
                    for col_idx in (1, 0, 2):
                        if col_idx < len(cells):
                            cell = cells[col_idx]
                            # Try linked name first
                            link = cell.find("a")
                            raw = (link.get_text(strip=True) if link
                                   else cell.get_text(strip=True))
                            name, party = self._extract_name_party(raw)
                            if len(name) >= 5 and re.search(r'[A-Za-z]', name):
                                if self._dedupe(name):
                                    # Party from dedicated column
                                    if not party and len(cells) > 3:
                                        party = normalize_party(cells[3].get_text(strip=True))
                                    # Dapil / region
                                    region = cells[2].get_text(strip=True) if len(cells) > 2 else None
                                    wiki_href = link["href"] if link and link.get("href","").startswith("/wiki/") else None
                                    found.append({
                                        "name": name,
                                        "role_type": "dpr",
                                        "position": "Anggota DPR RI 2024-2029",
                                        "party": party,
                                        "dapil": region,
                                        "wiki_url_id": f"https://id.wikipedia.org{wiki_href}" if wiki_href else None,
                                        "source_url": url,
                                    })
                                break
                    if len(found) >= limit:
                        break
                if len(found) >= limit:
                    break

            logger.info(f"[Discovery/DPR] Found {len(found)} from {url}")

        logger.info(f"[Discovery/DPR] Total: {len(found)}")
        return found[:limit]

    # ── Menteri ───────────────────────────────────────────────────────────────
    async def discover_menteri(self, limit: int = 60) -> List[Dict]:
        found = []
        for url in DISCOVERY_SOURCES["menteri"]:
            soup = await self._get(url)
            if not soup:
                continue
            for table in soup.find_all("table", {"class": re.compile("wikitable")}):
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = row.find_all(["td","th"])
                    if len(cells) < 2:
                        continue
                    # Ministry name is col 0 or 1, person is col 1 or 2
                    for col_idx in (1, 2):
                        if col_idx >= len(cells):
                            continue
                        cell = cells[col_idx]
                        link = cell.find("a")
                        raw = link.get_text(strip=True) if link else cell.get_text(strip=True)
                        name, party = self._extract_name_party(raw)
                        if len(name) >= 5 and re.search(r'[A-Z]', name):
                            if self._dedupe(name):
                                position = cells[0].get_text(strip=True)[:80] if cells else "Menteri"
                                wiki_href = link["href"] if link and link.get("href","").startswith("/wiki/") else None
                                found.append({
                                    "name": name,
                                    "role_type": "menteri",
                                    "position": position,
                                    "party": party,
                                    "province": "Jakarta",
                                    "wiki_url_id": f"https://id.wikipedia.org{wiki_href}" if wiki_href else None,
                                    "source_url": url,
                                })
                            break
                if len(found) >= limit:
                    break

        logger.info(f"[Discovery/Menteri] Total: {len(found)}")
        return found[:limit]

    # ── Gubernur ──────────────────────────────────────────────────────────────
    async def discover_gubernur(self, limit: int = 50) -> List[Dict]:
        found = []
        for url in DISCOVERY_SOURCES["gubernur"]:
            soup = await self._get(url)
            if not soup:
                continue
            for table in soup.find_all("table", {"class": re.compile("wikitable")}):
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = row.find_all(["td","th"])
                    if len(cells) < 2:
                        continue
                    province = cells[0].get_text(strip=True) if cells else None
                    for col_idx in (1, 2):
                        if col_idx >= len(cells):
                            continue
                        cell = cells[col_idx]
                        link = cell.find("a")
                        raw = link.get_text(strip=True) if link else cell.get_text(strip=True)
                        name, party = self._extract_name_party(raw)
                        if len(name) >= 5 and re.search(r'[A-Z]', name) and not re.match(r'^[0-9]', name):
                            if self._dedupe(name):
                                wiki_href = link["href"] if link and link.get("href","").startswith("/wiki/") else None
                                found.append({
                                    "name": name,
                                    "role_type": "gubernur",
                                    "position": f"Gubernur {province or ''}".strip(),
                                    "party": party,
                                    "province": province,
                                    "wiki_url_id": f"https://id.wikipedia.org{wiki_href}" if wiki_href else None,
                                    "source_url": url,
                                })
                            break
                if len(found) >= limit:
                    break

        logger.info(f"[Discovery/Gubernur] Total: {len(found)}")
        return found[:limit]

    # ── Bupati/Walikota ───────────────────────────────────────────────────────
    async def discover_regional(self, limit: int = 300) -> List[Dict]:
        """Discover bupati and walikota."""
        found = []
        for url in DISCOVERY_SOURCES["bupati"]:
            soup = await self._get(url)
            if not soup:
                continue
            for table in soup.find_all("table", {"class": re.compile("wikitable")}):
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = row.find_all(["td","th"])
                    if len(cells) < 2:
                        continue
                    region = cells[0].get_text(strip=True)
                    # Determine walikota vs bupati
                    role = "walikota" if "kota" in region.lower() else "bupati"
                    for col_idx in (1, 2):
                        if col_idx >= len(cells):
                            continue
                        cell = cells[col_idx]
                        link = cell.find("a")
                        raw = link.get_text(strip=True) if link else cell.get_text(strip=True)
                        name, party = self._extract_name_party(raw)
                        if len(name) >= 5 and re.search(r'[A-Z]', name):
                            if self._dedupe(name):
                                wiki_href = link["href"] if link and link.get("href","").startswith("/wiki/") else None
                                found.append({
                                    "name": name,
                                    "role_type": role,
                                    "position": f"{'Wali Kota' if role=='walikota' else 'Bupati'} {region}".strip(),
                                    "party": party,
                                    "province": region,
                                    "wiki_url_id": f"https://id.wikipedia.org{wiki_href}" if wiki_href else None,
                                    "source_url": url,
                                })
                            break
                if len(found) >= limit:
                    break

        logger.info(f"[Discovery/Regional] Total: {len(found)}")
        return found[:limit]

    # ── DPRD ──────────────────────────────────────────────────────────────────
    async def discover_dprd(self, limit: int = 200) -> List[Dict]:
        """Discover DPRD provincial leaders (chairpersons of each province)."""
        found = []
        provinces = [
            "Aceh","Sumatera Utara","Sumatera Barat","Riau","Kepulauan Riau",
            "Jambi","Bengkulu","Sumatera Selatan","Kepulauan Bangka Belitung",
            "Lampung","DKI Jakarta","Jawa Barat","Jawa Tengah","DI Yogyakarta",
            "Jawa Timur","Banten","Bali","Nusa Tenggara Barat","Nusa Tenggara Timur",
            "Kalimantan Barat","Kalimantan Tengah","Kalimantan Selatan",
            "Kalimantan Timur","Kalimantan Utara","Sulawesi Utara","Gorontalo",
            "Sulawesi Tengah","Sulawesi Barat","Sulawesi Selatan","Sulawesi Tenggara",
            "Maluku","Maluku Utara","Papua","Papua Barat","Papua Selatan",
            "Papua Tengah","Papua Pegunungan","Papua Barat Daya",
        ]

        # Try generic DPRD page
        url = DISCOVERY_SOURCES["dprd"][0]
        soup = await self._get(url)
        if soup:
            for table in soup.find_all("table", {"class": re.compile("wikitable")}):
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cells = row.find_all(["td","th"])
                    for col_idx in (1, 2, 0):
                        if col_idx >= len(cells):
                            continue
                        cell = cells[col_idx]
                        link = cell.find("a")
                        raw = link.get_text(strip=True) if link else cell.get_text(strip=True)
                        name, party = self._extract_name_party(raw)
                        if len(name) >= 5 and re.search(r'[A-Z]', name):
                            if self._dedupe(name):
                                province = cells[0].get_text(strip=True) if cells else None
                                wiki_href = link["href"] if link and link.get("href","").startswith("/wiki/") else None
                                found.append({
                                    "name": name,
                                    "role_type": "dprd",
                                    "position": f"Anggota DPRD {province or 'Provinsi'}",
                                    "party": party,
                                    "province": province,
                                    "wiki_url_id": f"https://id.wikipedia.org{wiki_href}" if wiki_href else None,
                                    "source_url": url,
                                })
                            break

        logger.info(f"[Discovery/DPRD] Total: {len(found)}")
        return found[:limit]

    # ── Full discovery ────────────────────────────────────────────────────────
    async def discover_all(
        self,
        limit_dpr: int = 100,
        limit_menteri: int = 50,
        limit_gubernur: int = 40,
        limit_regional: int = 150,
        limit_dprd: int = 100,
    ) -> Dict[str, List[Dict]]:
        """Run all discovery crawlers and return dict by category."""
        logger.info("Starting full discovery crawl…")
        results = {}

        dpr  = await self.discover_dpr(limit_dpr)
        results["dpr"] = dpr

        ment = await self.discover_menteri(limit_menteri)
        results["menteri"] = ment

        gub  = await self.discover_gubernur(limit_gubernur)
        results["gubernur"] = gub

        reg  = await self.discover_regional(limit_regional)
        results["bupati"] = [r for r in reg if r["role_type"] == "bupati"]
        results["walikota"] = [r for r in reg if r["role_type"] == "walikota"]

        dprd = await self.discover_dprd(limit_dprd)
        results["dprd"] = dprd

        total = sum(len(v) for v in results.values())
        logger.info(f"Discovery complete. Total: {total} officials")
        for cat, items in results.items():
            logger.info(f"  {cat}: {len(items)}")

        return results
