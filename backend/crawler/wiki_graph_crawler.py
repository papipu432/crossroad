"""
CROSSROAD — Wikipedia Graph Crawler v2
========================================
The engine that finds Prabowo→Tommy (depth 2 via Titiek) and
Rudy Mas'ud's 6 siblings in government (each on separate pages).

Key improvements over v1:
  - Follows EVERY internal /wiki/ link, not just infobox
  - Scores by: infobox field (highest) > family section > career > text mention
  - Extracts sibling lists from text ("Kakak-adiknya adalah A, B, C, D")
  - Extracts family from prose patterns ("adik kandung Rudy Mas'ud")
  - Handles redirects and disambiguation pages
  - Extracts company/business mentions with OWNS relationship hint
  - Extracts education classmates ("teman seangkatan", "almamater")
  - Annotates EVERY edge with source_url + exact evidence text

Architecture:
  crawl(url) → CrawlResult{
    title, entity_type, infobox, bio, sections,
    all_links[sorted by relevance],
    queue[high-relevance subset],
    relationships[typed, sourced],
    raw_text
  }
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

logger = logging.getLogger(__name__)

WIKI_ID = "https://id.wikipedia.org"
WIKI_EN = "https://en.wikipedia.org"

HEADERS = {
    "User-Agent": "Crossroad-OSINT/2.0 (academic research; contact: research@crossroad.id)",
    "Accept-Language": "id,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

# ── Relationship patterns ─────────────────────────────────────────────────────
# Indonesian prose patterns that indicate family/political relationships

SIBLING_PATTERNS = [
    r"kakak(?:\s+kandung)?\s+(?:dari\s+)?(.+?)(?:\.|,|\s+adalah|\s+yang)",
    r"adik(?:\s+kandung)?\s+(?:dari\s+)?(.+?)(?:\.|,|\s+adalah|\s+yang)",
    r"saudara(?:\s+kandung)?\s+(?:dari\s+)?(.+?)(?:\.|,|\s+adalah|\s+yang)",
    r"(?:ia|dia)\s+merupakan\s+(?:kakak|adik|saudara)\s+(?:kandung\s+)?(?:dari\s+)?(.+?)(?:\.|,)",
    r"Kakak-adiknya\s+adalah\s+(.+?)(?:\.|$)",  # "Kakak-adiknya adalah A, B, C, D"
    r"saudara[-\s]saudaran?ya\s+(?:adalah\s+)?(.+?)(?:\.|$)",
    r"siblings?\s+(?:are|include)\s+(.+?)(?:\.|$)",
]

SPOUSE_PATTERNS = [
    r"menikah\s+dengan\s+(.+?)(?:\s+pada|\s+di|\s+tahun|\.|,)",
    r"istrinya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"suaminya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"pasangannya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"married\s+(?:to\s+)?(.+?)(?:\s+in|\s+on|\.|,)",
]

PARENT_PATTERNS = [
    r"putra\s+(?:dari\s+)?(.+?)(?:\s+dan|\.|,)",
    r"putri\s+(?:dari\s+)?(.+?)(?:\s+dan|\.|,)",
    r"anak\s+(?:dari\s+)?(.+?)(?:\s+dan|\.|,)",
    r"lahir\s+dari\s+(?:pasangan\s+)?(.+?)(?:\s+dan|\.|,)",
    r"son\s+of\s+(.+?)(?:\s+and|\.|,)",
    r"daughter\s+of\s+(.+?)(?:\s+and|\.|,)",
    r"ayahnya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"ibunya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"orang\s+tuanya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
]

CHILD_PATTERNS = [
    r"anaknya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"putra(?:nya)?\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"putrinya\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"dikaruniai\s+(?:\d+\s+(?:orang\s+)?anak\s+)?(?:yaitu\s+|bernama\s+)?(.+?)(?:\.|$)",
]

COUSIN_PATTERNS = [
    r"sepupu(?:nya)?\s+(?:adalah\s+)?(.+?)(?:\.|,)",
    r"cousin\s+of\s+(.+?)(?:\.|,)",
]

# Section titles → relationship type hint
SECTION_HINTS = {
    "keluarga":           "FAMILY",
    "family":             "FAMILY",
    "kehidupan pribadi":  "FAMILY",
    "personal life":      "FAMILY",
    "pernikahan":         "FAMILY",
    "marriage":           "FAMILY",
    "orang tua":          "PARENT",
    "parents":            "PARENT",
    "anak-anak":          "CHILD",
    "children":           "CHILD",
    "pendidikan":         "EDUCATION",
    "education":          "EDUCATION",
    "riwayat pendidikan": "EDUCATION",
    "karier":             "CAREER",
    "career":             "CAREER",
    "jabatan":            "CAREER",
    "riwayat jabatan":    "CAREER",
    "bisnis":             "BUSINESS",
    "usaha":              "BUSINESS",
    "perusahaan":         "BUSINESS",
    "business":           "BUSINESS",
    "partai":             "PARTY",
    "politik":            "POLITICAL",
    "political career":   "POLITICAL",
    "kontroversi":        "CONTROVERSY",
    "corruption":         "CORRUPTION",
    "korupsi":            "CORRUPTION",
}

# Relevance scoring — how much do we want to crawl this link?
RELEVANCE_BOOST = {
    # Infobox fields → +points
    "pasangan":          9,  "spouse":       9,
    "suami":             9,  "istri":        9,
    "anak":              8,  "children":     8,
    "orang tua":         8,  "parents":      8,
    "saudara":           8,  "siblings":     8,
    "partai":            7,  "party":        7,
    "pendidikan":        6,  "education":    6,
    "almamater":         6,  "alma mater":   6,
    "jabatan":           5,  "office":       5,
    # Section names → +points
    "FAMILY":            7,
    "PARENT":            8,
    "CHILD":             7,
    "EDUCATION":         5,
    "CAREER":            4,
    "BUSINESS":          5,
    "PARTY":             6,
}

# Keywords in link context → add to relevance
CONTEXT_KEYWORDS = {
    # Government positions
    "presiden": 4, "wakil presiden": 4, "menteri": 4, "gubernur": 4,
    "bupati": 3, "walikota": 3, "anggota dpr": 3, "anggota dprd": 3,
    "senator": 3, "ketua": 2, "wakil ketua": 2,
    # Business
    "direktur": 2, "komisaris": 2, "ceo": 2, "owner": 2, "pemilik": 2,
    "pengusaha": 2, "founder": 2, "pendiri": 2,
    # Military
    "jenderal": 3, "laksamana": 3, "marsekal": 3, "kolonel": 2,
    "purnawirawan": 2, "tni": 2, "polri": 2,
    # Family
    "adik kandung": 5, "kakak kandung": 5, "saudara kandung": 5,
    "putra": 4, "putri": 4, "istri": 4, "suami": 4, "anak": 3,
    "menantu": 3, "mertua": 3, "ipar": 3, "sepupu": 3,
    # Education
    "universitas": 2, "akademi militer": 3, "akabri": 3,
    "almamater": 2, "teman seangkatan": 3,
    # Politics
    "partai": 3, "fraksi": 3, "koalisi": 3, "ketua umum": 4,
    # Indonesia-specific names
    "soeharto": 4, "soekarno": 4, "cendana": 4, "mas'ud": 3, "yudhoyono": 3,
}


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class WikiLink:
    url: str
    anchor_text: str
    context: str          # surrounding sentence
    section: str          # section this link appeared in
    section_hint: str     # FAMILY|EDUCATION|CAREER|etc.
    infobox_field: str    # if from infobox
    entity_type: str      # PERSON|PARTY|UNIVERSITY|COMPANY|ORGANIZATION|OTHER|SKIP
    relevance_score: int  # 0–10


@dataclass
class InboxData:
    raw:        Dict[str, str] = field(default_factory=dict)
    born:       Optional[str]  = None
    birthplace: Optional[str]  = None
    religion:   Optional[str]  = None
    party:      Optional[str]  = None
    spouse:     List[str]      = field(default_factory=list)
    children:   List[str]      = field(default_factory=list)
    parents:    List[str]      = field(default_factory=list)
    siblings:   List[str]      = field(default_factory=list)
    education:  List[str]      = field(default_factory=list)
    office:     List[str]      = field(default_factory=list)


@dataclass
class CrawlResult:
    url:          str
    title:        str
    entity_type:  str
    lang:         str
    infobox:      InboxData         = field(default_factory=InboxData)
    bio:          str               = ""
    sections:     List[Dict]        = field(default_factory=list)
    categories:   List[str]         = field(default_factory=list)
    all_links:    List[WikiLink]    = field(default_factory=list)
    queue:        List[WikiLink]    = field(default_factory=list)
    relationships:List[Dict]        = field(default_factory=list)
    raw_text:     str               = ""
    crawled_at:   str               = ""


# ── Main crawler ───────────────────────────────────────────────────────────────

class WikiGraphCrawler:
    def __init__(self, delay: float = 1.5, min_relevance: int = 2):
        self.delay         = delay
        self.min_relevance = min_relevance

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def _fetch(self, url: str) -> Optional[Tuple[str, BeautifulSoup]]:
        await asyncio.sleep(self.delay)
        try:
            async with httpx.AsyncClient(
                headers=HEADERS, follow_redirects=True,
                timeout=25.0, verify=False
            ) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return str(r.url), BeautifulSoup(r.text, "lxml")
                logger.debug(f"HTTP {r.status_code}: {url}")
        except Exception as e:
            logger.debug(f"Fetch error {url}: {e}")
        return None

    # ── Entity type classification ────────────────────────────────────────────

    SKIP_NS = {
        "kategori:", "category:", "wikipedia:", "template:", "berkas:", "file:",
        "bantuan:", "help:", "portal:", "pembicaraan:", "talk:", "khusus:", "special:",
        "wp:", "wt:",
    }

    def _classify(self, title: str, href: str, context: str = "") -> str:
        t = title.lower()
        h = href.lower()

        for ns in self.SKIP_NS:
            if h.startswith(f"/wiki/{ns}") or t.startswith(ns):
                return "SKIP"

        combined = t + " " + context.lower()

        if any(x in t for x in ["partai ", "party ", "koalisi", "fraksi"]):
            return "PARTY"

        if any(x in t for x in [
            "universitas", "university", "sekolah tinggi", "akademi militer",
            "akabri", "institut ", "college ", "school "
        ]):
            return "UNIVERSITY"

        if any(x in t for x in [
            "pt ", "tbk", "group", " corp", "company", "perusahaan",
            "konglomer", "holding",
        ]):
            return "COMPANY"

        if any(x in t for x in [
            "kementerian", "kpk", "bpk", "bin", "kopassus", "kostrad",
            "tentara", "militer", "kepolisian",
        ]):
            return "ORGANIZATION"

        # Check if title looks like a person name (2+ capitalized words)
        words = [w for w in title.split() if w]
        if len(words) >= 2:
            caps = sum(1 for w in words[:4] if w and w[0].isupper())
            if caps >= 2:
                return "PERSON"

        # Context-based: if mentioned in family/political context
        if any(k in combined for k in [
            "politikus", "politician", "presiden", "menteri", "gubernur",
            "bupati", "walikota", "anggota dpr", "senator",
            "pengusaha", "businessman",
        ]):
            return "PERSON"

        return "OTHER"

    def _score(self, link_text: str, context: str, section: str,
                section_hint: str, infobox_field: str) -> int:
        score = 0
        combined = (link_text + " " + context + " " + infobox_field).lower()

        # Infobox link base
        if infobox_field:
            score += RELEVANCE_BOOST.get(infobox_field.lower(), 3)
            score += 4  # infobox bonus

        # Section hint bonus
        if section_hint in RELEVANCE_BOOST:
            score += RELEVANCE_BOOST[section_hint]

        # Context keywords
        for kw, pts in CONTEXT_KEYWORDS.items():
            if kw in combined:
                score += pts

        return min(score, 10)

    # ── Infobox parser ────────────────────────────────────────────────────────

    def _parse_infobox(self, soup: BeautifulSoup) -> InboxData:
        data = InboxData()
        table = soup.find("table", {"class": re.compile(r"infobox")})
        if not table:
            return data

        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not (th and td):
                continue
            field_key = th.get_text(" ", strip=True).lower().strip(":")
            field_val = td.get_text(" ", strip=True)
            data.raw[field_key] = field_val

            f = field_key
            if any(x in f for x in ("lahir","born","tanggal lahir","date of birth")):
                yr = re.search(r"\d{4}", field_val)
                if yr:
                    data.born = yr.group()
                place = re.sub(r"\d{1,2}\s+\w+\s+\d{4}|\d{4}", "", field_val).strip(" ,\n")
                if len(place) > 2:
                    data.birthplace = place[:80]

            elif any(x in f for x in ("agama","religion")):
                data.religion = field_val[:50]

            elif any(x in f for x in ("partai","party","afiliasi politik")):
                data.party = field_val[:80]

            elif any(x in f for x in ("pasangan","spouse","suami","istri","married")):
                data.spouse.extend(self._split_names(field_val))

            elif any(x in f for x in ("anak","children","putra","putri","child")):
                data.children.extend(self._split_names(field_val))

            elif any(x in f for x in ("orang tua","parents","ayah","ibu","father","mother","parent")):
                data.parents.extend(self._split_names(field_val))

            elif any(x in f for x in ("saudara","siblings","kakak","adik","brother","sister")):
                data.siblings.extend(self._split_names(field_val))

            elif any(x in f for x in ("pendidikan","education","almamater","alma mater")):
                for item in re.split(r"[•\n;,]", field_val):
                    item = item.strip()
                    if len(item) > 4:
                        data.education.append(item)

            elif any(x in f for x in ("jabatan","office","posisi","menjabat","position")):
                data.office.append(field_val[:120])

        return data

    def _split_names(self, text: str) -> List[str]:
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\(\s*\d{4}[^\)]*\)", "", text)
        text = re.sub(r"\(\s*lahir[^\)]*\)", "", text, flags=re.IGNORECASE)
        parts = re.split(r"[,;\n•·]", text)
        result = []
        for n in parts:
            n = re.sub(r"^\s*[\d\-\.]+\s*", "", n).strip()
            # Must look like a proper name
            if len(n) >= 4 and re.search(r"[A-Za-z]", n):
                # Remove leading titles
                n = re.sub(r"^(H\.|Hj\.|Dr\.|Drs\.|Prof\.|Ir\.)\s+", "", n, flags=re.IGNORECASE)
                if n and len(n) >= 4:
                    result.append(n.strip())
        return result

    # ── Link extraction ───────────────────────────────────────────────────────

    def _extract_infobox_links(self, soup: BeautifulSoup, base: str) -> List[WikiLink]:
        links = []
        table = soup.find("table", {"class": re.compile(r"infobox")})
        if not table:
            return links

        for row in table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not (th and td):
                continue
            field_key = th.get_text(" ", strip=True).lower().strip(":")
            ctx = td.get_text(" ", strip=True)

            for a in td.find_all("a", href=True):
                href = a.get("href", "")
                if not href.startswith("/wiki/"):
                    continue
                title = a.get("title") or a.get_text(strip=True)
                if not title or len(title) < 2:
                    continue
                etype = self._classify(title, href, ctx)
                if etype == "SKIP":
                    continue

                section_hint = ""
                for k, v in SECTION_HINTS.items():
                    if k in field_key:
                        section_hint = v
                        break

                score = self._score(title, ctx[:200], "infobox", section_hint, field_key)

                links.append(WikiLink(
                    url=urljoin(base, href),
                    anchor_text=title,
                    context=ctx[:200],
                    section="infobox",
                    section_hint=section_hint,
                    infobox_field=field_key,
                    entity_type=etype,
                    relevance_score=score,
                ))

        return links

    def _extract_section_links(self, soup: BeautifulSoup, base: str
                               ) -> Tuple[List[Dict], List[WikiLink]]:
        """Return (sections, all_links_from_sections)."""
        sections = []
        all_links = []
        content = soup.find("div", {"class": "mw-parser-output"})
        if not content:
            return sections, all_links

        cur_title  = "intro"
        cur_hint   = ""
        cur_text   = []
        cur_links  = []

        def flush():
            if cur_text or cur_links:
                sections.append({
                    "title": cur_title,
                    "hint":  cur_hint,
                    "text":  " ".join(cur_text)[:1000],
                    "links": cur_links[:],
                })
                all_links.extend(cur_links)

        for elem in content.children:
            if not hasattr(elem, "name") or elem.name is None:
                continue

            if elem.name in ("h2", "h3", "h4"):
                flush()
                cur_title  = elem.get_text(strip=True)
                cur_hint   = ""
                cur_text   = []
                cur_links  = []
                tl = cur_title.lower()
                for k, v in SECTION_HINTS.items():
                    if k in tl:
                        cur_hint = v
                        break

            elif elem.name in ("p", "ul", "ol", "dl"):
                text = elem.get_text(" ", strip=True)
                cur_text.append(text[:600])

                for a in elem.find_all("a", href=True):
                    href = a.get("href", "")
                    if not href.startswith("/wiki/"):
                        continue
                    title = a.get("title") or a.get_text(strip=True)
                    if not title:
                        continue

                    # Get enclosing sentence for context
                    parent = a.parent
                    ctx = parent.get_text(" ", strip=True)[:250] if parent else ""

                    etype = self._classify(title, href, ctx)
                    if etype == "SKIP":
                        continue

                    score = self._score(title, ctx, cur_title, cur_hint, "")

                    link = WikiLink(
                        url=urljoin(base, href),
                        anchor_text=title,
                        context=ctx,
                        section=cur_title,
                        section_hint=cur_hint,
                        infobox_field="",
                        entity_type=etype,
                        relevance_score=score,
                    )
                    cur_links.append(link)

        flush()
        return sections, all_links

    # ── Relationship inference ────────────────────────────────────────────────

    def _infer_from_infobox(self, title: str, url: str, ib: InboxData) -> List[Dict]:
        rels = []
        src = url

        for name in ib.spouse:
            rels.append({"from_entity": title, "to_entity": name, "rel_type": "FAMILY_OF",
                         "subtype": "spouse", "label": "pasangan", "source_url": src,
                         "evidence": f"Infobox 'pasangan': {name}", "confidence": 0.97})
        for name in ib.children:
            rels.append({"from_entity": title, "to_entity": name, "rel_type": "FAMILY_OF",
                         "subtype": "child", "label": "anak", "source_url": src,
                         "evidence": f"Infobox 'anak': {name}", "confidence": 0.97})
        for name in ib.parents:
            rels.append({"from_entity": title, "to_entity": name, "rel_type": "FAMILY_OF",
                         "subtype": "parent", "label": "orang tua", "source_url": src,
                         "evidence": f"Infobox 'orang tua': {name}", "confidence": 0.97})
        for name in ib.siblings:
            rels.append({"from_entity": title, "to_entity": name, "rel_type": "FAMILY_OF",
                         "subtype": "sibling", "label": "saudara kandung", "source_url": src,
                         "evidence": f"Infobox 'saudara': {name}", "confidence": 0.95})
        for edu in ib.education:
            rels.append({"from_entity": title, "to_entity": edu, "to_type": "UNIVERSITY",
                         "rel_type": "STUDIED_AT", "subtype": "alumni", "label": edu,
                         "source_url": src, "evidence": f"Infobox 'pendidikan': {edu}",
                         "confidence": 0.95})
        if ib.party:
            rels.append({"from_entity": title, "to_entity": ib.party, "to_type": "PARTY",
                         "rel_type": "MEMBER_OF", "subtype": "party_member",
                         "label": f"anggota {ib.party}", "source_url": src,
                         "evidence": f"Infobox 'partai': {ib.party}", "confidence": 0.98})
        for pos in ib.office:
            rels.append({"from_entity": title, "to_entity": pos[:60], "to_type": "ORGANIZATION",
                         "rel_type": "WORKS_AT", "subtype": "official", "label": pos[:60],
                         "source_url": src, "evidence": f"Infobox 'jabatan': {pos[:80]}",
                         "confidence": 0.90})

        return rels

    def _infer_from_text(self, title: str, url: str, sections: List[Dict]) -> List[Dict]:
        """
        Extract relationships from prose text using regex patterns.
        This catches sibling lists like "Kakak-adiknya adalah A, B, C, D"
        and phrases like "adik kandung Rudy Mas'ud".
        """
        rels = []

        all_text = " ".join(s.get("text","") for s in sections)

        def extract_names_from_match(m: re.Match) -> List[str]:
            raw = m.group(1)
            # Split on comma/dan/serta
            parts = re.split(r",|dan|serta|;", raw, flags=re.IGNORECASE)
            names = []
            for p in parts:
                p = p.strip()
                p = re.sub(r"\(.*?\)", "", p).strip()
                if len(p) >= 4 and re.search(r"[A-Z]", p):
                    names.append(p)
            return names

        PROSE_PATTERNS = [
            (SIBLING_PATTERNS, "sibling", "FAMILY_OF", "saudara kandung"),
            (SPOUSE_PATTERNS,  "spouse",  "FAMILY_OF", "pasangan"),
            (PARENT_PATTERNS,  "parent",  "FAMILY_OF", "orang tua"),
            (CHILD_PATTERNS,   "child",   "FAMILY_OF", "anak"),
            (COUSIN_PATTERNS,  "cousin",  "FAMILY_OF", "sepupu"),
        ]

        for patterns, subtype, rel_type, label in PROSE_PATTERNS:
            for pattern in patterns:
                for m in re.finditer(pattern, all_text, re.IGNORECASE):
                    names = extract_names_from_match(m)
                    for name in names[:8]:  # limit per match
                        # Avoid extracting generic words
                        if len(name.split()) < 2 and len(name) < 8:
                            continue
                        rels.append({
                            "from_entity": title, "to_entity": name,
                            "rel_type": rel_type, "subtype": subtype, "label": label,
                            "source_url": url,
                            "evidence": m.group(0)[:200],
                            "confidence": 0.75,
                        })

        # Section-based relationship hints
        for sec in sections:
            hint  = sec.get("hint","")
            stext = sec.get("text","")
            for link in sec.get("links",[]):
                etype = link.entity_type
                lname = link.anchor_text

                if hint == "FAMILY":
                    rels.append({
                        "from_entity": title, "to_entity": lname,
                        "rel_type": "FAMILY_OF", "subtype": "relative",
                        "label": sec["title"], "source_url": url,
                        "evidence": link.context[:200], "confidence": 0.70,
                    })
                elif hint == "EDUCATION" and etype == "UNIVERSITY":
                    rels.append({
                        "from_entity": title, "to_entity": lname, "to_type": "UNIVERSITY",
                        "rel_type": "STUDIED_AT", "subtype": "alumni",
                        "label": lname, "source_url": url,
                        "evidence": link.context[:200], "confidence": 0.85,
                    })
                elif hint == "CAREER" and etype in ("ORGANIZATION","COMPANY","UNIVERSITY"):
                    rels.append({
                        "from_entity": title, "to_entity": lname, "to_type": etype,
                        "rel_type": "WORKS_AT", "subtype": "career",
                        "label": link.context[:60], "source_url": url,
                        "evidence": link.context[:200], "confidence": 0.75,
                    })
                elif hint == "BUSINESS" and etype == "COMPANY":
                    rels.append({
                        "from_entity": title, "to_entity": lname, "to_type": "COMPANY",
                        "rel_type": "OWNS", "subtype": "owner",
                        "label": f"pemilik/komisaris {lname}", "source_url": url,
                        "evidence": link.context[:200], "confidence": 0.75,
                    })
                elif hint == "POLITICAL" and etype == "PERSON":
                    rels.append({
                        "from_entity": title, "to_entity": lname,
                        "rel_type": "ALLIED_WITH", "subtype": "political_ally",
                        "label": "sekutu politik", "source_url": url,
                        "evidence": link.context[:200], "confidence": 0.65,
                    })

        return rels

    # ── Page type detection ───────────────────────────────────────────────────

    def _detect_page_type(self, soup: BeautifulSoup) -> str:
        # Check categories first
        cats = [a.get_text(strip=True).lower()
                for a in soup.select("#mw-normal-catlinks li a")]
        cat_text = " ".join(cats)

        person_signals = [
            "politikus indonesia", "politician", "presiden", "wakil presiden",
            "menteri", "gubernur", "bupati", "walikota", "anggota dpr",
            "lahir", "meninggal", "is an indonesian", "is a politician",
            "purnawirawan", "jenderal", "laksamana",
        ]
        for sig in person_signals:
            if sig in cat_text:
                return "PERSON"

        if any(x in cat_text for x in ["partai politik", "political party"]):
            return "PARTY"
        if any(x in cat_text for x in ["universitas", "university", "akademi"]):
            return "UNIVERSITY"
        if any(x in cat_text for x in ["perusahaan", "corporation", "company"]):
            return "COMPANY"

        # Fallback: check first paragraph
        first_p = ""
        content = soup.find("div", {"class": "mw-parser-output"})
        if content:
            for p in content.find_all("p", recursive=False):
                t = p.get_text(strip=True)
                if len(t) > 50:
                    first_p = t.lower()
                    break

        for sig in person_signals:
            if sig in first_p:
                return "PERSON"

        # Title looks like a name?
        h1 = soup.find("h1", {"id": "firstHeading"})
        if h1:
            words = h1.get_text(strip=True).split()
            if len(words) >= 2 and all(w[0].isupper() for w in words[:3] if w):
                return "PERSON"

        return "OTHER"

    # ── Main crawl ─────────────────────────────────────────────────────────────

    async def crawl(self, url: str, max_queue: int = 60) -> Optional[CrawlResult]:
        fetched = await self._fetch(url)
        if not fetched:
            return None

        final_url, soup = fetched
        lang = "en" if "en.wikipedia.org" in final_url else "id"
        base = WIKI_EN if lang == "en" else WIKI_ID

        # Skip disambiguation pages
        if soup.find("table", {"class": re.compile(r"disambig")}) or \
           "disambiguation" in final_url.lower() or \
           "disambig" in (soup.find("div", {"id": "disambig"}) or " "):
            logger.debug(f"Skipping disambiguation: {final_url}")
            return None

        # Title
        h1    = soup.find("h1", {"id": "firstHeading"})
        title = h1.get_text(strip=True) if h1 else final_url.split("/")[-1].replace("_"," ")

        # Entity type
        etype = self._detect_page_type(soup)

        # Infobox
        infobox = self._parse_infobox(soup)

        # Bio (first 2 substantive paragraphs)
        bio_parts = []
        content = soup.find("div", {"class": "mw-parser-output"})
        if content:
            for p in content.find_all("p", recursive=False):
                t = p.get_text(strip=True)
                if len(t) > 60 and not t.startswith("^"):
                    bio_parts.append(t)
                if len(bio_parts) >= 2:
                    break

        # Sections + links
        sections, section_links = self._extract_section_links(soup, base)

        # Infobox links (highest priority)
        infobox_links = self._extract_infobox_links(soup, base)

        # Deduplicate all links
        all_links: List[WikiLink] = []
        seen: Set[str] = set()
        for link in infobox_links + section_links:
            clean = link.url.split("#")[0]
            if clean not in seen:
                seen.add(clean)
                all_links.append(link)

        # Sort by relevance
        all_links.sort(key=lambda x: x.relevance_score, reverse=True)

        # Queue = top relevant links
        queue = [
            l for l in all_links
            if l.relevance_score >= self.min_relevance
            and l.entity_type not in ("OTHER", "SKIP")
        ][:max_queue]

        # Relationships
        rels = self._infer_from_infobox(title, final_url, infobox)
        rels += self._infer_from_text(title, final_url, sections)

        # Deduplicate relationships
        seen_rels = set()
        unique_rels = []
        for r in rels:
            key = (r["from_entity"], r.get("to_entity",""), r["rel_type"], r.get("subtype",""))
            if key not in seen_rels:
                seen_rels.add(key)
                unique_rels.append(r)

        # Categories
        cats = [a.get_text(strip=True)
                for a in soup.select("#mw-normal-catlinks li a, .mw-normal-catlinks li a")]

        from datetime import datetime, timezone
        result = CrawlResult(
            url=final_url,
            title=title,
            entity_type=etype,
            lang=lang,
            infobox=infobox,
            bio=" ".join(bio_parts)[:800],
            sections=sections,
            categories=cats[:25],
            all_links=all_links,
            queue=queue,
            relationships=unique_rels,
            raw_text=soup.get_text()[:6000],
            crawled_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Crawled [{lang}] '{title}' ({etype}) | "
            f"links={len(all_links)} queued={len(queue)} "
            f"rels={len(unique_rels)} ib_fields={len(infobox.raw)}"
        )
        return result

    async def crawl_by_name(self, name: str, lang: str = "id") -> Optional[CrawlResult]:
        base = WIKI_ID if lang == "id" else WIKI_EN
        slug = name.strip().replace(" ", "_")
        return await self.crawl(f"{base}/wiki/{quote(slug)}")
