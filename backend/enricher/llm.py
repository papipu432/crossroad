"""
Crossroad LLM Enricher — uses local Ollama (qwen2.5:7b).
Extracts relationships from scraped data, scores news alignment,
and fills profile gaps that scrapers can't reach.
NO frontier LLM. No API keys. Runs entirely local.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


class LLMEnricher:
    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host  = host.rstrip("/")
        self.model = model
        self.url   = f"{self.host}/api/chat"

    async def ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def _chat(self, system: str, user: str, timeout: float = 120.0) -> str:
        payload = {
            "model": self.model, "stream": False,
            "options": {"temperature": 0.05, "num_predict": 2048, "top_p": 0.9},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        async with httpx.AsyncClient(timeout=timeout) as c:
            r = await c.post(self.url, json=payload)
            r.raise_for_status()
            return r.json().get("message", {}).get("content", "")

    @staticmethod
    def _json(text: str) -> Optional[Any]:
        text = text.strip()
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        for s, e in [('{', '}'), ('[', ']')]:
            si, ei = text.find(s), text.rfind(e)
            if si != -1 and ei > si:
                try:
                    return json.loads(text[si:ei+1])
                except Exception:
                    pass
        return None

    # ── Profile enrichment ─────────────────────────────────────────────────────

    async def enrich_profile(self, name: str, scraped: Dict, known: Dict) -> Dict:
        """
        Fill gaps in scraped data using LLM knowledge.
        scraped = result from WikiDeepScraper
        known   = what we already know (seed data: party, role_type, etc.)
        """
        system = (
            "You are an expert on Indonesian politics and public figures. "
            "Given partial information, complete the JSON profile. "
            "Return ONLY a JSON object — no prose, no markdown.\n"
            "Schema: {full_name, born, birthplace, religion, ethnicity, "
            "role_type, current_position, party, faction, province, dapil, bio, "
            "education:[{year,institution,degree}], "
            "career:[{year_start,year_end,org,title}], "
            "companies:[{name,role,industry}], "
            "wiki_url_id, sources:[{name,url}]}\n"
            "role_type: dpr|dprd|menteri|gubernur|bupati|walikota|presiden|wapres\n"
            "party: PDIP|Gerindra|Golkar|PKB|Demokrat|PKS|Nasdem|PAN|PPP|PSI|Hanura|Perindo|Independen\n"
            "Return ONLY the JSON object. Empty fields = null."
        )
        user = (
            f"Indonesian public figure: {name}\n"
            f"Known: party={known.get('party')}, role={known.get('role_type')}, "
            f"province={known.get('province')}, position={known.get('position')}\n"
            f"Scraped bio: {(scraped.get('bio') or '')[:400]}\n"
            f"Scraped education: {scraped.get('education', [])[:4]}\n"
            f"Scraped career: {scraped.get('career', [])[:4]}\n"
            "Complete the full profile JSON. Include any public business interests, "
            "education institutions, career milestones, and family connections you know of.\n"
            "Return ONLY the JSON."
        )
        try:
            raw = await self._chat(system, user)
            result = self._json(raw)
            if isinstance(result, dict):
                result["full_name"] = result.get("full_name") or name
                # Merge: scraped data takes precedence for factual fields
                if scraped.get("born") and not result.get("born"):
                    result["born"] = scraped["born"]
                if scraped.get("education") and not result.get("education"):
                    result["education"] = scraped["education"]
                if scraped.get("career") and not result.get("career"):
                    result["career"] = scraped["career"]
                return result
        except Exception as e:
            logger.error(f"enrich_profile failed [{name}]: {e}")
        # Merge scraped + known as fallback
        return {**known, **scraped, "full_name": name}

    # ── Relationship extraction ────────────────────────────────────────────────

    async def extract_relationships(self, name: str, profile: Dict,
                                     family: List[Dict], news_titles: List[str]) -> List[Dict]:
        """
        Extract relationship edges from profile + family + news context.
        Returns list of {from, to, rel_type, subtype, label, year_start, year_end, source}.
        """
        system = (
            "You are an Indonesian political network analyst. "
            "Extract relationship edges from the given data. "
            "Return ONLY a JSON array. No prose.\n"
            "Each edge: {from_name, to_name, to_type, rel_type, subtype, label, year_start, year_end, source_hint}\n"
            "rel_type values: FAMILY_OF | MEMBER_OF | WORKS_AT | STUDIED_AT | OWNS | ALLIED_WITH | RIVAL_OF | MET_AT | APPOINTED_BY\n"
            "to_type: person | org | party | university | company | govt\n"
            "subtype examples: spouse, child, parent, director, shareholder, classmate, coalition\n"
            "source_hint: a short description of how this is known (e.g. 'Wikipedia infobox', 'news coverage')\n"
            "Return ONLY known, publicly verifiable facts. Return ONLY the JSON array."
        )
        edu_str = json.dumps(profile.get("education", [])[:5], ensure_ascii=False)
        career_str = json.dumps(profile.get("career", [])[:5], ensure_ascii=False)
        companies_str = json.dumps(profile.get("companies", [])[:4], ensure_ascii=False)
        family_str = json.dumps([{"name": f["name"], "relation": f.get("relation")} for f in family[:8]], ensure_ascii=False)
        news_str = "\n".join(f"- {t}" for t in news_titles[:10])

        user = (
            f"Person: {name}\n"
            f"Party: {profile.get('party')}, Role: {profile.get('role_type')}, Province: {profile.get('province')}\n"
            f"Education: {edu_str}\n"
            f"Career: {career_str}\n"
            f"Companies: {companies_str}\n"
            f"Known family: {family_str}\n"
            f"Recent news headlines:\n{news_str}\n\n"
            "Extract all relationship edges. Include:\n"
            "1. Family (FAMILY_OF with subtype spouse/child/etc)\n"
            "2. Party membership (MEMBER_OF)\n"
            "3. Education institutions (STUDIED_AT with subtype like classmate if relevant)\n"
            "4. Past/current employers or government positions (WORKS_AT or APPOINTED_BY)\n"
            "5. Companies owned or led (OWNS)\n"
            "6. Political alliances or rivalries (ALLIED_WITH / RIVAL_OF)\n"
            "7. Notable meetings or collaborations (MET_AT)\n"
            "Return ONLY the JSON array."
        )
        try:
            raw = await self._chat(system, user, timeout=90.0)
            result = self._json(raw)
            if isinstance(result, list):
                return result
        except Exception as e:
            logger.error(f"extract_relationships failed [{name}]: {e}")
        return []

    # ── News scoring ───────────────────────────────────────────────────────────

    async def score_news(self, party: str, articles: List[Dict]) -> List[Dict]:
        """Score each article for party alignment and sentiment."""
        if not party or not articles:
            return articles
        system = (
            "You are a political analyst specializing in Indonesian politics. "
            "Score each news article's relation to the politician's party stance.\n"
            "alignment_score: float -1.0 to +1.0\n"
            "  +1.0 = strongly supports / aligns with party\n"
            "   0.0 = neutral / factual\n"
            "  -1.0 = criticises / contradicts party\n"
            "sentiment: positive | negative | neutral\n"
            "Return ONLY a JSON array [{id, alignment_score, sentiment}]. Same order as input."
        )
        snippets = [{"id": i, "title": a.get("title",""), "summary": (a.get("summary","") or "")[:150]}
                    for i, a in enumerate(articles[:20])]
        user = (
            f"Politician's party: {party}\n"
            f"Articles:\n{json.dumps(snippets, ensure_ascii=False)}\n"
            "Score each article. Return ONLY the JSON array."
        )
        try:
            raw = await self._chat(system, user, timeout=60.0)
            scores = self._json(raw)
            if isinstance(scores, list):
                score_map = {s.get("id"): s for s in scores if isinstance(s, dict)}
                for i, a in enumerate(articles):
                    if i in score_map:
                        a["alignment_score"] = score_map[i].get("alignment_score", 0.0)
                        a["sentiment"]       = score_map[i].get("sentiment", "neutral")
        except Exception as e:
            logger.warning(f"score_news failed: {e}")
        return articles

    # ── Family completeness ────────────────────────────────────────────────────

    async def complete_family(self, name: str, known: List[Dict]) -> List[Dict]:
        """Ask LLM for publicly known family not found by Wikipedia scraper."""
        system = (
            "You are a biographer specializing in Indonesian public figures. "
            "Return ONLY a JSON array of family members. No prose.\n"
            "Each: {name, relation, position, party, source_hint}\n"
            "relation: spouse|child|parent|sibling|in-law|relative\n"
            "source_hint: brief note on how this is publicly known\n"
            "ONLY publicly known, verifiable facts. Return ONLY the JSON array."
        )
        known_str = json.dumps([{"name": f["name"], "relation": f.get("relation")} for f in known[:8]], ensure_ascii=False)
        user = (
            f"Indonesian politician: {name}\n"
            f"Already documented: {known_str}\n"
            "List all other publicly known family members (spouse, children, parents, siblings). "
            "Include any political positions they hold and party affiliations.\n"
            "Return ONLY the JSON array."
        )
        try:
            raw = await self._chat(system, user, timeout=60.0)
            result = self._json(raw)
            if isinstance(result, list):
                return result
        except Exception as e:
            logger.warning(f"complete_family failed [{name}]: {e}")
        return known
