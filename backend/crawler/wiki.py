"""
Crossroad Wikipedia Scraper
Extracts: bio, education, family, career, companies from Wikipedia
Indonesian + English editions. Returns structured data for Neo4j.
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Crossroad-OSINT/1.0 (research, non-commercial) Python/httpx",
    "Accept-Language": "id,en;q=0.9",
}

WIKI_ID = "https://id.wikipedia.org"
WIKI_EN = "https://en.wikipedia.org"


class WikiDeepScraper:
    def __init__(self, delay: float = 1.5):
        self.delay = delay

    async def _get(self, url: str) -> Optional[BeautifulSoup]:
        await asyncio.sleep(self.delay)
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20.0, verify=False) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return BeautifulSoup(r.text, "lxml")
                logger.debug(f"Wiki {r.status_code}: {url}")
        except Exception as e:
            logger.debug(f"Wiki error {url}: {e}")
        return None

    async def _find_page(self, name: str, lang: str = "id") -> Optional[tuple[str, BeautifulSoup]]:
        base = WIKI_ID if lang == "id" else WIKI_EN
        # 1. Direct URL
        slug = name.strip().replace(" ", "_")
        url = f"{base}/wiki/{quote(slug)}"
        soup = await self._get(url)
        if soup and self._is_person_page(soup):
            return url, soup
        # 2. Search
        search = f"{base}/w/index.php?search={quote(name)}&ns0=1"
        soup = await self._get(search)
        if soup:
            link = soup.select_one(".mw-search-result-heading a")
            if link:
                url = urljoin(base, link["href"])
                soup = await self._get(url)
                if soup and self._is_person_page(soup):
                    return url, soup
        return None

    def _is_person_page(self, soup: BeautifulSoup) -> bool:
        text = soup.get_text().lower()
        keywords = ["politikus", "anggota dpr", "menteri", "gubernur", "bupati", "walikota",
                    "politician", "minister", "member of parliament", "senator", "lahir",
                    "born", "dewan perwakilan", "presiden"]
        return any(k in text for k in keywords)

    def _infobox(self, soup: BeautifulSoup) -> Dict[str, str]:
        ib = {}
        table = soup.find("table", {"class": re.compile(r"infobox")})
        if not table:
            return ib
        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = th.get_text(" ", strip=True).lower().strip(":")
                val = td.get_text(" ", strip=True)
                ib[key] = val
        return ib

    def _extract_born(self, ib: Dict) -> Optional[str]:
        for key in ("lahir", "born", "tanggal lahir", "date of birth"):
            if key in ib:
                m = re.search(r"\d{4}", ib[key])
                if m:
                    return m.group()
        return None

    def _extract_birthplace(self, ib: Dict) -> Optional[str]:
        for key in ("lahir", "born", "tempat lahir", "place of birth"):
            if key in ib:
                # Remove year
                text = re.sub(r"\d{1,2}\s+\w+\s+\d{4}", "", ib[key])
                text = re.sub(r"\d{4}", "", text).strip(" ,\n")
                if len(text) > 2:
                    return text[:80]
        return None

    def _extract_education(self, soup: BeautifulSoup, ib: Dict) -> List[Dict]:
        edu = []
        # From infobox
        for key in ("pendidikan", "education", "alma mater", "almamater"):
            if key in ib:
                for line in re.split(r"[•\n]", ib[key]):
                    line = line.strip()
                    if len(line) > 5:
                        year = re.search(r"\d{4}", line)
                        edu.append({
                            "institution": re.sub(r"\(\d{4}\)", "", line).strip(),
                            "year": year.group() if year else None,
                        })
        # From section
        for heading in soup.find_all(["h2", "h3"]):
            if any(k in heading.get_text().lower() for k in ("pendidikan", "education", "riwayat pendidikan")):
                ul = heading.find_next("ul")
                if ul:
                    for li in ul.find_all("li"):
                        text = li.get_text(strip=True)
                        if len(text) > 5 and not any(e["institution"] == text for e in edu):
                            year = re.search(r"\d{4}", text)
                            edu.append({"institution": text, "year": year.group() if year else None})
        return edu[:8]

    def _extract_career(self, soup: BeautifulSoup, ib: Dict) -> List[Dict]:
        career = []
        for heading in soup.find_all(["h2", "h3"]):
            text_lower = heading.get_text().lower()
            if any(k in text_lower for k in ("karier", "career", "jabatan", "riwayat jabatan", "pekerjaan")):
                ul = heading.find_next("ul")
                if ul:
                    for li in ul.find_all("li"):
                        item = li.get_text(strip=True)
                        if len(item) > 5:
                            years = re.findall(r"\d{4}", item)
                            career.append({
                                "title": item,
                                "year_start": years[0] if years else None,
                                "year_end":   years[1] if len(years) > 1 else None,
                            })
        return career[:12]

    def _extract_companies(self, soup: BeautifulSoup, ib: Dict) -> List[Dict]:
        companies = []
        for heading in soup.find_all(["h2", "h3"]):
            text_lower = heading.get_text().lower()
            if any(k in text_lower for k in ("bisnis", "usaha", "perusahaan", "business", "aset")):
                ul = heading.find_next("ul")
                if ul:
                    for li in ul.find_all("li"):
                        item = li.get_text(strip=True)
                        if len(item) > 5:
                            companies.append({"name": item, "role": "terkait"})
        return companies[:8]

    def _extract_family(self, soup: BeautifulSoup, ib: Dict, wiki_url: str) -> List[Dict]:
        members = []
        # From infobox
        relation_map = {
            "pasangan": "spouse", "spouse": "spouse", "suami": "spouse", "istri": "spouse",
            "anak": "child", "children": "child", "putra": "child", "putri": "child",
            "orang tua": "parent", "parents": "parent", "ayah": "parent", "ibu": "parent",
            "saudara": "sibling", "siblings": "sibling",
        }
        for ib_key, relation in relation_map.items():
            val = ib.get(ib_key, "")
            if val:
                for name in re.split(r"[,;•\n\d\(\)]", val):
                    name = re.sub(r"\(.*?\)", "", name).strip()
                    if len(name) > 3 and re.search(r"[A-Za-z]", name):
                        members.append({
                            "name": name,
                            "relation": relation,
                            "source_url": wiki_url,
                            "source_name": "Wikipedia",
                        })

        # From "kehidupan pribadi" / "keluarga" section
        for heading in soup.find_all(["h2", "h3"]):
            text_lower = heading.get_text().lower()
            if any(k in text_lower for k in ("keluarga", "kehidupan pribadi", "family", "personal life", "life")):
                # Look for linked names
                section_elem = heading.find_next(["p", "ul"])
                if section_elem:
                    for a in section_elem.find_all("a", href=True):
                        name = a.get_text(strip=True)
                        if len(name) > 3 and "/wiki/" in a["href"]:
                            members.append({
                                "name": name,
                                "relation": "relative",
                                "source_url": wiki_url,
                                "source_name": "Wikipedia",
                                "wiki_href": a["href"],
                            })

        # Deduplicate
        seen = set()
        unique = []
        for m in members:
            k = m["name"].lower()
            if k not in seen and len(k) > 3:
                seen.add(k)
                unique.append(m)
        return unique[:10]

    def _extract_bio(self, soup: BeautifulSoup) -> Optional[str]:
        content = soup.find("div", {"class": "mw-parser-output"})
        if not content:
            return None
        paras = []
        for p in content.find_all("p", recursive=False):
            text = p.get_text(strip=True)
            if len(text) > 60 and not text.startswith("^"):
                paras.append(text)
            if len(paras) >= 2:
                break
        return " ".join(paras)[:800] if paras else None

    # ── Main entry point ──────────────────────────────────────────────────────

    async def scrape_person(self, name: str) -> Dict[str, Any]:
        """
        Full deep scrape for a person: bio, infobox, education,
        career, companies, family.
        Returns dict ready for DB upsert + relationship extraction.
        """
        result: Dict[str, Any] = {
            "full_name": name,
            "wiki_url_id": None, "wiki_url_en": None,
            "bio": None, "born": None, "birthplace": None,
            "religion": None, "education": [], "career": [],
            "companies": [], "family": [], "sources": [],
        }

        for lang in ("id", "en"):
            found = await self._find_page(name, lang)
            if not found:
                continue
            url, soup = found
            if lang == "id":
                result["wiki_url_id"] = url
            else:
                result["wiki_url_en"] = url
            result["sources"].append({"name": f"Wikipedia ({lang.upper()})", "url": url})

            ib = self._infobox(soup)
            if not result["bio"]:
                result["bio"] = self._extract_bio(soup)
            if not result["born"]:
                result["born"] = self._extract_born(ib)
            if not result["birthplace"]:
                result["birthplace"] = self._extract_birthplace(ib)
            if not result["religion"]:
                result["religion"] = ib.get("agama") or ib.get("religion")

            if not result["education"]:
                result["education"] = self._extract_education(soup, ib)
            if not result["career"]:
                result["career"] = self._extract_career(soup, ib)
            if not result["companies"]:
                result["companies"] = self._extract_companies(soup, ib)
            if not result["family"]:
                result["family"] = self._extract_family(soup, ib, url)

            logger.info(f"[Wiki/{lang}] Scraped: {name} — edu:{len(result['education'])} family:{len(result['family'])}")

        return result
