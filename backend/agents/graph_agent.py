"""
CROSSROAD — Recursive Graph Mining Agent
=========================================
This is the REAL OSINT engine.

How it works (using Prabowo as example):
─────────────────────────────────────────
Depth 0:  crawl(prabowo_url)
          → finds: Titiek Soeharto [infobox:pasangan, score=9]
          → finds: Soemitro Djojohadikusumo [infobox:orang tua, score=8]
          → finds: Gerindra [infobox:partai, score=7]
          → finds: AKABRI [infobox:pendidikan, score=6]
          → finds: Kopassus [career section, score=6]
          → finds: Soeharto [context: "mertua Soeharto", score=8]
          → queues all for depth-1 crawl

Depth 1a: crawl(titiek_soeharto_url)
          → finds: Hutomo Mandala Putra (Tommy) [siblings section, score=7]
          → finds: Soeharto [infobox:orang tua]
          → finds: Didit Hediprasetyo [infobox:anak]
          → infers: FAMILY_OF(Titiek, Tommy, sibling)
          → queues Tommy for depth-2

Depth 1b: crawl(soemitro_url)
          → finds: Margono Djojohadikusumo [grandfather]
          → finds: Hashim Djojohadikusumo [sibling]
          → infers: FAMILY_OF(Prabowo, Hashim, sibling via father)

Depth 2:  crawl(tommy_soeharto_url)
          → LLM sees: Prabowo married Titiek (sister of Tommy)
          → infers: FAMILY_OF(Prabowo, Tommy, "mantan ipar/ex-brother-in-law")

Each result is:
  1. Written immediately to PostgreSQL (raw data + sources)
  2. Written to Neo4j (nodes + typed edges with source_url + evidence)
  3. Embedded into ChromaDB (for RAG)
  4. Published to Redis pub/sub (for live UI updates)

The graph self-expands: every person found becomes a new node,
and every link on their page spawns more sub-agents.
"""

import asyncio
import json
import logging
import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from slugify import slugify

import redis.asyncio as aioredis

import db
from graph import GraphDB
from crawler.wiki_graph_crawler import WikiGraphCrawler, CrawlResult, WikiLink
from enricher.llm import LLMEnricher

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY_SECONDS", "1.5"))

# Agent progress channel
GRAPH_CHANNEL = "crossroad:graph_agent:progress"

# ── Crawl queue item ──────────────────────────────────────────────────────────

@dataclass
class QueueItem:
    url: str
    depth: int
    parent_title: str        # who spawned this crawl
    parent_slug: str
    infobox_field: str = ""  # if this was found in infobox
    entity_type: str = ""    # pre-classified type
    relevance: int = 0
    relationship_hint: str = "" # 'spouse','child','sibling','parent','party',etc.


# ── Graph mining agent ────────────────────────────────────────────────────────

class GraphMiningAgent:
    """
    Recursive Wikipedia graph miner.
    Starts at seed_url, follows all relevant links to max_depth.
    Builds the knowledge graph edge by edge, with every edge annotated
    with source_url and evidence text.
    """

    def __init__(
        self,
        graph_db: GraphDB,
        llm: LLMEnricher,
        max_depth: int = 3,
        max_nodes: int = 500,
        concurrency: int = 4,
        min_relevance: int = 2,
    ):
        self.graph_db      = graph_db
        self.llm           = llm
        self.crawler       = WikiGraphCrawler(delay=CRAWL_DELAY, min_relevance=min_relevance)
        self.max_depth     = max_depth
        self.max_nodes     = max_nodes
        self.concurrency   = concurrency
        self.min_relevance = min_relevance

        # State
        self._visited: Set[str]  = set()   # crawled URLs
        self._queued:  Set[str]  = set()   # URLs in queue (avoid duplicates)
        self._queue: deque       = deque()
        self._sem: Optional[asyncio.Semaphore] = None
        self._redis: Optional[aioredis.Redis]  = None

        # Stats
        self.stats = {
            "nodes_created": 0,
            "edges_created": 0,
            "pages_crawled": 0,
            "pages_failed":  0,
            "persons_found": 0,
            "orgs_found":    0,
        }
        # Per-worker state: worker_id -> {url, name, depth, entity_type, started}
        self._workers: Dict[int, Dict] = {}
        self._worker_counter: int = 0
        self._stop   = False
        self._paused = False

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    async def _publish(self, event: Dict):
        """Push progress event to Redis pub/sub for live UI."""
        try:
            r = await self._get_redis()
            event["ts"] = datetime.now(timezone.utc).isoformat()
            await r.publish(GRAPH_CHANNEL, json.dumps(event, ensure_ascii=False, default=str))
        except Exception:
            pass

    async def _is_visited(self, url: str) -> bool:
        # Normalize: strip trailing slash, anchors
        clean = url.split("#")[0].rstrip("/")
        return clean in self._visited

    async def _mark_visited(self, url: str):
        clean = url.split("#")[0].rstrip("/")
        self._visited.add(clean)

    # ── Process one crawl result ──────────────────────────────────────────────

    async def _persist_result(self, result: CrawlResult, parent_slug: str = ""):
        """Write crawl result to PostgreSQL + Neo4j + ChromaDB."""

        # 1. Upsert the entity itself
        if result.entity_type == "PERSON":
            person_data = {
                "full_name":       result.title,
                "bio":             result.bio,
                "born":            result.infobox.born,
                "birthplace":      result.infobox.birthplace,
                "religion":        result.infobox.religion,
                "party":           result.infobox.party,
                "education":       [{"institution": e} for e in result.infobox.education],
                "career":          [{"title": o} for o in result.infobox.office],
                "wiki_url_id":     result.url if result.lang == "id" else None,
                "wiki_url_en":     result.url if result.lang == "en" else None,
                "sources":         [{"name": f"Wikipedia ({result.lang.upper()})", "url": result.url}],
                "crawl_depth":     0,
                "crawled_at":      result.crawled_at,
            }
            pid = await db.upsert_person(person_data)
            self.stats["persons_found"] += 1
            self.stats["nodes_created"] += 1

            # Neo4j node
            p_slug = slugify(result.title, separator="-")
            await self.graph_db.upsert_person({
                **person_data,
                "slug": p_slug,
                "id": pid,
                "name": result.title,
            })

            # Log source
            await db.log_source("person", pid, f"Wikipedia ({result.lang.upper()})", result.url)

        elif result.entity_type in ("PARTY", "ORGANIZATION", "COMPANY", "UNIVERSITY"):
            org_type_map = {
                "PARTY": "party", "COMPANY": "company",
                "UNIVERSITY": "university", "ORGANIZATION": "org",
            }
            org_slug = slugify(result.title, separator="-")
            org_data = {
                "name":     result.title,
                "slug":     org_slug,
                "org_type": org_type_map.get(result.entity_type, "org"),
            }
            await db.upsert_org(org_data)
            await self.graph_db.upsert_org(org_data)
            self.stats["orgs_found"]    += 1
            self.stats["nodes_created"] += 1

        # 2. Write all inferred relationships to Neo4j with source annotation
        for rel in result.relationships:
            await self._write_relationship(rel, result)

        # 3. Embed into ChromaDB
        try:
            from vector.chroma import VectorStore
            vs = VectorStore()
            if result.entity_type == "PERSON":
                person_row = await db.get_person(result.title)
                if person_row:
                    await vs.embed_persons([person_row])
        except Exception as e:
            logger.debug(f"ChromaDB embed skipped: {e}")

        self.stats["pages_crawled"] += 1

        # 4. Publish live update
        await self._publish({
            "event": "page_crawled",
            "title": result.title,
            "type": result.entity_type,
            "links_found": len(result.all_links),
            "rels_found": len(result.relationships),
            "stats": self.stats,
            "workers": [w for w in self._workers.values()],
        })

    async def _write_relationship(self, rel: Dict, result: CrawlResult):
        """Write one relationship edge to PostgreSQL + Neo4j with full source annotation."""
        from_name  = rel.get("from_entity","")
        to_name    = rel.get("to_entity","")
        if not from_name or not to_name:
            return

        from_slug  = slugify(from_name, separator="-")
        to_slug    = slugify(to_name, separator="-")
        rel_type   = rel.get("rel_type", "RELATED_TO")
        to_type    = rel.get("to_type", "PERSON")
        subtype    = rel.get("subtype","")
        label      = rel.get("label","")
        source_url = rel.get("source_url", result.url)
        evidence   = rel.get("evidence","")
        confidence = rel.get("confidence", 0.7)

        # Ensure target node exists in Neo4j
        if to_type == "PERSON":
            await self.graph_db.upsert_person({"slug": to_slug, "full_name": to_name})
            # Ensure in PG too
            await db.upsert_person({
                "full_name": to_name, "crawl_depth": 2,
                "sources": [{"name": "Inferred from " + from_name, "url": source_url}],
            })
        else:
            org_type = {
                "PARTY":"party","COMPANY":"company",
                "UNIVERSITY":"university","ORGANIZATION":"org",
            }.get(to_type,"org")
            await self.graph_db.upsert_org({"slug": to_slug, "name": to_name, "org_type": org_type})
            await db.upsert_org({"name": to_name, "slug": to_slug, "org_type": org_type})

        # Write edge with source annotation
        neo4j_to_label = "Person" if to_type == "PERSON" else "Org"
        await self.graph_db.upsert_relationship(
            from_slug, "Person",
            to_slug, neo4j_to_label,
            rel_type,
            props={
                "subtype":    subtype,
                "label":      label or subtype,
                "source_url": source_url,
                "evidence":   evidence[:200],
                "confidence": confidence,
                "is_current": True,
            }
        )

        # PG relationship
        from_person = await db.get_person(from_name)
        to_person   = await db.get_person(to_name) if to_type == "PERSON" else None

        if from_person and (to_person or to_type != "PERSON"):
            to_id = to_person["id"] if to_person else 0
            try:
                await db.upsert_relationship({
                    "from_id":    from_person["id"],
                    "from_type":  "person",
                    "to_id":      to_id,
                    "to_type":    "person" if to_type == "PERSON" else "org",
                    "rel_type":   rel_type,
                    "subtype":    subtype,
                    "label":      label,
                    "is_current": True,
                    "sources":    [{"name": f"Wikipedia ({result.lang.upper()})",
                                    "url": source_url, "evidence": evidence[:100]}],
                    "notes":      evidence[:200],
                })
            except Exception:
                pass

        self.stats["edges_created"] += 1

    # ── Crawl one item from queue ─────────────────────────────────────────────

    async def _crawl_item(self, item: QueueItem):
        """Fetch and process one URL, then enqueue its links."""
        if self._stop:
            return
        while self._paused and not self._stop:
            await asyncio.sleep(0.5)
        if self._stop:
            return
        if await self._is_visited(item.url):
            return
        if len(self._visited) >= self.max_nodes:
            return

        await self._mark_visited(item.url)

        import time
        worker_id = id(asyncio.current_task())
        page_name = item.url.split("/")[-1].replace("_"," ")
        try:
            from urllib.parse import unquote
            page_name = unquote(page_name)
        except Exception:
            pass

        # Register this worker
        self._workers[worker_id] = {
            "id":         worker_id,
            "url":        item.url,
            "name":       page_name,
            "depth":      item.depth,
            "parent":     item.parent_title,
            "entity_type":item.entity_type or "?",
            "started":    time.time(),
            "status":     "crawling",
        }

        logger.info(
            f"  [{item.depth}/{self.max_depth}] Crawling: {page_name}"
            f" (parent: {item.parent_title}, relevance: {item.relevance})"
        )

        await self._publish({
            "event": "crawling",
            "url": item.url,
            "name": page_name,
            "depth": item.depth,
            "parent": item.parent_title,
            "visited_count": len(self._visited),
            "queue_size": len(self._queue),
            "workers": [w for w in self._workers.values()],  # all active workers
        })

        # Crawl the page
        result = await self.crawler.crawl(item.url)
        if not result:
            self.stats["pages_failed"] += 1
            return

        # If this was an infobox link with a relationship hint,
        # add a direct relationship from parent
        if item.relationship_hint and item.parent_slug:
            rel_type_map = {
                "spouse": "FAMILY_OF", "child": "FAMILY_OF",
                "parent": "FAMILY_OF", "sibling": "FAMILY_OF",
                "party":  "MEMBER_OF", "education": "STUDIED_AT",
                "career": "WORKS_AT",  "company": "OWNS",
            }
            rel_type = rel_type_map.get(item.relationship_hint, "RELATED_TO")
            # Add to result relationships
            result.relationships.append({
                "from_entity": item.parent_title,
                "to_entity":   result.title,
                "rel_type":    rel_type,
                "subtype":     item.relationship_hint,
                "label":       item.infobox_field or item.relationship_hint,
                "source_url":  item.url,
                "evidence":    f"Infobox/link from {item.parent_title} page: {item.infobox_field}",
                "confidence":  0.95,
            })

        # Update worker status to processing
        if worker_id in self._workers:
            self._workers[worker_id]["status"] = "processing"
            self._workers[worker_id]["entity_type"] = result.entity_type
            self._workers[worker_id]["rels_found"] = len(result.relationships)

        # Persist this result
        await self._persist_result(result, parent_slug=item.parent_slug)

        # Enqueue sub-links if not at max depth
        if item.depth < self.max_depth:
            new_items = 0
            for link in result.queue:
                if link.url in self._queued or link.url in self._visited:
                    continue
                if len(self._visited) + len(self._queued) >= self.max_nodes:
                    break

                # Determine relationship hint from infobox field
                hint = self._infobox_field_to_hint(link.infobox_field)

                self._queued.add(link.url)
                self._queue.append(QueueItem(
                    url=link.url,
                    depth=item.depth + 1,
                    parent_title=result.title,
                    parent_slug=slugify(result.title, separator="-"),
                    infobox_field=link.infobox_field,
                    entity_type=link.entity_type,
                    relevance=link.relevance_score,
                    relationship_hint=hint,
                ))
                new_items += 1

            logger.info(f"    → Queued {new_items} new links from {result.title}")

        # Worker finished - remove from active registry
        self._workers.pop(worker_id, None)

    def _infobox_field_to_hint(self, field: str) -> str:
        """Map infobox field name to relationship hint."""
        f = field.lower()
        if any(x in f for x in ("pasangan","spouse","suami","istri")):
            return "spouse"
        if any(x in f for x in ("anak","children","putra","putri")):
            return "child"
        if any(x in f for x in ("orang tua","parents","ayah","ibu")):
            return "parent"
        if any(x in f for x in ("saudara","siblings","kakak","adik")):
            return "sibling"
        if any(x in f for x in ("partai","party")):
            return "party"
        if any(x in f for x in ("pendidikan","education","alma","almamater")):
            return "education"
        if any(x in f for x in ("jabatan","office","posisi")):
            return "career"
        return ""

    # ── Main run loop ─────────────────────────────────────────────────────────

    async def run(
        self,
        seed_urls: List[str],
        job_id: Optional[int] = None,
        run_label: str = "graph_mine",
    ):
        """
        Start recursive graph mining from seed_urls.

        seed_urls: list of Wikipedia URLs to start from
                   e.g. ["https://id.wikipedia.org/wiki/Prabowo_Subianto"]
        """
        self._stop    = False
        self._visited = set()
        self._queued  = set(seed_urls)
        self._queue   = deque()
        self._sem     = asyncio.Semaphore(self.concurrency)
        self.stats    = {k: 0 for k in self.stats}
        self._workers = {}
        self._worker_counter = 0

        # Seed the queue
        for url in seed_urls:
            self._queue.append(QueueItem(
                url=url, depth=0,
                parent_title="seed", parent_slug="seed",
                relevance=10,
            ))

        start_time = datetime.now(timezone.utc)
        logger.info(
            f"Graph mining started: {len(seed_urls)} seeds, "
            f"max_depth={self.max_depth}, max_nodes={self.max_nodes}"
        )

        await self._publish({
            "event": "started",
            "seeds": seed_urls,
            "max_depth": self.max_depth,
            "max_nodes": self.max_nodes,
        })

        if job_id:
            await db.update_job(job_id, "running")

        # BFS loop with concurrency
        while self._queue and not self._stop:
            if len(self._visited) >= self.max_nodes:
                logger.info(f"Max nodes reached: {self.max_nodes}")
                break

            # Handle pause
            while self._paused and not self._stop:
                await asyncio.sleep(1)

            # Gather a batch
            batch = []
            while self._queue and len(batch) < self.concurrency:
                item = self._queue.popleft()
                if not await self._is_visited(item.url):
                    batch.append(item)

            if not batch:
                break

            # Run batch concurrently
            async def bounded_crawl(item: QueueItem):
                async with self._sem:
                    await self._crawl_item(item)

            await asyncio.gather(
                *[bounded_crawl(item) for item in batch],
                return_exceptions=True
            )

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Graph mining complete: "
            f"pages={self.stats['pages_crawled']}, "
            f"nodes={self.stats['nodes_created']}, "
            f"edges={self.stats['edges_created']}, "
            f"elapsed={elapsed:.0f}s"
        )

        await self._publish({
            "event": "complete",
            "stats": self.stats,
            "elapsed_seconds": elapsed,
        })

        if job_id:
            await db.update_job(job_id, "done", summary=self.stats)

        return self.stats

    def stop(self):
        self._stop = True


# ── Seed URL builder ──────────────────────────────────────────────────────────

def build_seed_urls(persons: List[Dict]) -> List[str]:
    """Build Wikipedia seed URLs for a list of persons."""
    urls = []
    for p in persons:
        wiki_id = p.get("wiki_url_id")
        wiki_en = p.get("wiki_url_en")
        name    = p.get("full_name") or p.get("name","")

        if wiki_id:
            urls.append(wiki_id)
        elif wiki_en:
            urls.append(wiki_en)
        elif name:
            slug = name.strip().replace(" ", "_")
            urls.append(f"https://id.wikipedia.org/wiki/{quote(slug)}")

    return list(dict.fromkeys(urls))  # deduplicate, preserve order


from urllib.parse import quote

