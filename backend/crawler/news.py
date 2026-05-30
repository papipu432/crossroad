"""
Crossroad News Crawler — scrapes 8 Indonesian news outlets for
individual-focused articles, extracts content, deduplicates.
"""
import asyncio
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

from constants import NEWS_SOURCES, NEWS_CATEGORIES

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "id,en;q=0.9",
}


def categorize(text: str) -> str:
    text_lower = text.lower()
    for cat, keywords in NEWS_CATEGORIES.items():
        if any(k in text_lower for k in keywords):
            return cat
    return "other"


class NewsCrawler:
    def __init__(self, delay: float = 1.2, max_per_source: int = 6):
        self.delay = delay
        self.max_per_source = max_per_source

    async def _get(self, url: str) -> Optional[BeautifulSoup]:
        await asyncio.sleep(self.delay)
        try:
            async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True,
                                         timeout=15.0, verify=False) as c:
                r = await c.get(url)
                if r.status_code == 200:
                    return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            logger.debug(f"News fetch failed {url}: {e}")
        return None

    async def _search_source(self, source: Dict, name: str) -> List[Dict]:
        query = quote(name)
        url = source["search"].format(q=query)
        soup = await self._get(url)
        if not soup:
            return []

        articles = []
        # Generic article detection
        candidates = (
            soup.select("article, .article-item, .news-item, .list-content__item, "
                        ".article__list, .latest--item, .card-detail, li.clearfix")
        )
        if not candidates:
            candidates = soup.find_all(["article", "li"], limit=20)

        last_name = name.split()[-1].lower() if name else ""

        for el in candidates[:15]:
            # Find title
            title_el = el.find(["h2", "h3", "h4"])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 15:
                continue
            # Must mention the person (by last name at minimum)
            summary_text = el.get_text(" ", strip=True)[:400]
            if last_name and last_name not in title.lower() and last_name not in summary_text.lower():
                continue

            # Find link
            link_el = el.find("a", href=True) or title_el.find_parent("a")
            if not link_el:
                continue
            href = link_el["href"]
            link = href if href.startswith("http") else urljoin(source["base"], href)
            if not link.startswith("http"):
                continue

            # Find date
            date_el = el.find(["time", "span"], class_=re.compile(r"date|time|ago", re.I))
            date = date_el.get_text(strip=True) if date_el else None

            category = categorize(title + " " + summary_text)
            articles.append({
                "url":         link,
                "title":       title[:220],
                "summary":     summary_text[:400],
                "outlet":      source["name"],
                "published_at":date[:60] if date else None,
                "category":    category,
                "sentiment":   "neutral",
                "credibility": 0.75,
            })

            if len(articles) >= self.max_per_source:
                break

        logger.info(f"[{source['name']}] {len(articles)} articles for '{name}'")
        return articles

    async def crawl_person(self, name: str) -> List[Dict]:
        """Crawl all news sources for a person, deduplicate by URL and title."""
        tasks = [self._search_source(src, name) for src in NEWS_SOURCES]
        batches = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls, seen_titles = set(), set()
        all_articles = []
        for batch in batches:
            if isinstance(batch, (Exception, BaseException)):
                continue
            for a in batch:
                u = a["url"]
                t = a["title"][:50].lower()
                if u in seen_urls or t in seen_titles:
                    continue
                seen_urls.add(u)
                seen_titles.add(t)
                all_articles.append(a)

        # Sort by date descending (best-effort)
        all_articles.sort(key=lambda x: x.get("published_at") or "", reverse=True)
        return all_articles[:40]

    async def fetch_article_body(self, url: str) -> Optional[str]:
        """Fetch article full text for deeper analysis."""
        soup = await self._get(url)
        if not soup:
            return None
        for tag in soup(["nav","footer","aside","script","style","iframe","header"]):
            tag.decompose()
        for sel in [".article-content",".detail__body",".read__content","article .content",
                    ".content-body",".entry-content",".post-content","[itemprop=articleBody]"]:
            elems = soup.select(sel)
            if elems:
                text = " ".join(p.get_text(strip=True) for p in elems)
                if len(text) > 200:
                    return text[:3000]
        return None
