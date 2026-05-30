"""
CROSSROAD v2 — Master Agent (rewritten)
=========================================
Orchestrates the full autonomous mining run using the new
recursive graph-crawling architecture.

Flow:
  Phase 0: SEED
    Load known officials (from constants.py seed list OR Wikipedia discovery)
    Insert skeleton nodes into PG + Neo4j

  Phase 1: GRAPH MINE
    For each seed person, launch GraphMiningAgent at their Wikipedia page
    Agent follows ALL links recursively (depth 1-3):
      - Infobox: pasangan, anak, orang tua, partai, pendidikan → immediate edges
      - Family section links → FAMILY_OF edges
      - Career section links → WORKS_AT edges
      - Education section links → STUDIED_AT edges
    Every edge has source_url + evidence text annotated

  Phase 2: NEWS
    For each discovered person, crawl 8 Indonesian news outlets
    Ollama scores every article for faction bias (-1 to +1)

  Phase 3: VECTORIZE
    Embed all persons + news into ChromaDB for RAG queries

Progress is streamed live via Redis pub/sub → SSE → frontend.
"""

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis.asyncio as aioredis
from slugify import slugify

import db
from graph import GraphDB
from crawler.news import NewsCrawler
from enricher.llm import LLMEnricher
from agents.graph_agent import GraphMiningAgent, build_seed_urls, QueueItem
from agents.discovery import DiscoveryCrawler
from constants import SEED_OFFICIALS

logger = logging.getLogger(__name__)

REDIS_URL        = os.getenv("REDIS_URL", "redis://redis:6379/0")
PROGRESS_CHANNEL = "crossroad:agent:progress"
AGENT_STATE_KEY  = "crossroad:agent:state"

CRAWL_DELAY  = float(os.getenv("CRAWL_DELAY_SECONDS", "1.5"))
L1_CONC      = int(os.getenv("AGENT_L1_CONCURRENCY", "4"))
L3_CONC      = int(os.getenv("AGENT_L3_CONCURRENCY", "2"))


# ── Progress ──────────────────────────────────────────────────────────────────

@dataclass
class MasterProgress:
    run_id: str
    status: str = "idle"
    phase: str = "init"
    phase_label: str = "Initializing…"

    # Discovery
    discovered: int = 0

    # Graph mine phase
    graph_pages_crawled: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    graph_queue_size: int = 0

    # News phase
    news_persons_done: int = 0
    news_persons_total: int = 0
    news_articles: int = 0

    # Active work
    current_crawling: List[str] = field(default_factory=list)

    # Graph mining extras
    graph_depth: int = 0
    graph_max_nodes: int = 0
    # Errors
    errors: List[str] = field(default_factory=list)

    started_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProgressBus:
    def __init__(self):
        self._r: Optional[aioredis.Redis] = None

    async def _redis(self) -> aioredis.Redis:
        if not self._r:
            self._r = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._r

    async def publish(self, progress: MasterProgress):
        r = await self._redis()
        data = json.dumps(asdict(progress), ensure_ascii=False, default=str)
        await r.set(AGENT_STATE_KEY, data, ex=86400)
        await r.publish(PROGRESS_CHANNEL, data)

    async def get_state(self) -> Optional[Dict]:
        r = await self._redis()
        raw = await r.get(AGENT_STATE_KEY)
        return json.loads(raw) if raw else None

    async def set_command(self, cmd: str):
        r = await self._redis()
        await r.set("crossroad:agent:command", cmd, ex=3600)

    async def get_command(self) -> Optional[str]:
        r = await self._redis()
        cmd = await r.get("crossroad:agent:command")
        if cmd:
            await r.delete("crossroad:agent:command")
        return cmd

    async def close(self):
        if self._r:
            await self._r.aclose()


bus = ProgressBus()


# ── Master agent ──────────────────────────────────────────────────────────────

class MasterAgent:
    def __init__(self):
        self.graph_db  = GraphDB()
        self.llm       = LLMEnricher()
        self.news_cr   = NewsCrawler(delay=CRAWL_DELAY, max_per_source=8)
        self.disc_cr   = DiscoveryCrawler(delay=CRAWL_DELAY)
        self._stop     = False
        self._paused   = False
        self.progress: Optional[MasterProgress] = None

    async def _emit(self, **kwargs):
        if self.progress:
            for k, v in kwargs.items():
                if hasattr(self.progress, k):
                    setattr(self.progress, k, v)
            self.progress.updated_at = datetime.now(timezone.utc).isoformat()
            await bus.publish(self.progress)

    async def _check_stop(self):
        cmd = await bus.get_command()
        if cmd == "stop":
            self._stop = True
        elif cmd == "pause":
            self._paused = True
            await self._emit(status="paused", phase_label="⏸ Paused — waiting for resume…")
        elif cmd == "resume":
            self._paused = False
            await self._emit(status="graph_mining", phase_label="▶ Resumed")

    async def _wait_if_paused(self):
        """Yield until resume command or stop."""
        while self._paused and not self._stop:
            await asyncio.sleep(1)
            cmd = await bus.get_command()
            if cmd == "resume":
                self._paused = False
                await self._emit(status="graph_mining", phase_label="▶ Resumed — continuing crawl")
            elif cmd == "stop":
                self._stop = True
                break

    # ── Phase 0: Seed ─────────────────────────────────────────────────────────

    async def phase0_seed(self, limits: Dict) -> List[Dict]:
        """Load seed officials and insert skeleton nodes."""
        await self._emit(phase="seed", phase_label="Phase 0: Seeding known officials…",
                         status="seeding")

        # Start with hardcoded seed list
        all_persons = list(SEED_OFFICIALS)
        seed_slugs = {slugify(s["name"], separator="-") for s in all_persons}

        # Live discovery from Wikipedia
        try:
            discovered = await self.disc_cr.discover_all(
                limit_dpr=limits.get("dpr", 100),
                limit_menteri=limits.get("menteri", 50),
                limit_gubernur=limits.get("gubernur", 40),
                limit_regional=limits.get("regional", 150),
                limit_dprd=limits.get("dprd", 100),
            )
            for cat, persons in discovered.items():
                for p in persons:
                    sl = slugify(p["name"], separator="-")
                    if sl not in seed_slugs:
                        seed_slugs.add(sl)
                        all_persons.append(p)
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            self.progress.errors.append(f"Discovery: {str(e)[:100]}")

        # Insert skeleton nodes
        for person in all_persons:
            name = person.get("name") or person.get("full_name","")
            if not name:
                continue
            try:
                await db.upsert_person({
                    "full_name":  name,
                    "role_type":  person.get("role_type"),
                    "current_position": person.get("position"),
                    "party":      person.get("party"),
                    "faction":    person.get("faction"),
                    "province":   person.get("province"),
                    "dapil":      person.get("dapil"),
                    "wiki_url_id":person.get("wiki_url_id"),
                    "crawl_depth": 0,
                    "sources": [{"name": "Seed", "url": person.get("source_url","internal")}],
                })
                await self.graph_db.upsert_person({
                    "slug":     slugify(name, separator="-"),
                    "full_name":name,
                    "party":    person.get("party"),
                    "role_type":person.get("role_type"),
                    "province": person.get("province"),
                })
            except Exception as e:
                logger.debug(f"Seed insert error [{name}]: {e}")

        await self._emit(discovered=len(all_persons),
                         phase_label=f"Phase 0 complete: {len(all_persons)} officials seeded")
        logger.info(f"Phase 0: {len(all_persons)} officials seeded")
        return all_persons

    # ── Phase 1: Graph mine ───────────────────────────────────────────────────

    async def phase1_graph_mine(self, officials: List[Dict], limits: Dict):
        """
        Launch GraphMiningAgent for each seed person.
        Each agent follows links recursively, building the knowledge graph.
        """
        await self._emit(
            phase="graph_mine",
            phase_label="Phase 1: Mining Wikipedia graph (recursive link-following)…",
            status="graph_mining",
        )

        # Build seed URLs from officials with known wiki URLs first,
        # then fall back to name-based URL construction
        seed_urls = build_seed_urls(officials)

        # Deduplicate
        seed_urls = list(dict.fromkeys(seed_urls))

        max_depth  = limits.get("graph_depth", 2)
        max_nodes  = limits.get("graph_max_nodes", 300)
        self.progress.graph_max_nodes = max_nodes  # per seed (rough)
        self.progress.graph_depth = max_depth
        self.progress.max_l1_workers = L1_CONC
        await bus.publish(self.progress)
        batch_size = L1_CONC  # process N seed URLs concurrently

        agent = GraphMiningAgent(
            graph_db=self.graph_db,
            llm=self.llm,
            max_depth=max_depth,
            max_nodes=max_nodes,
            concurrency=L1_CONC,
            min_relevance=2,
        )

        # Subscribe to graph agent events for forwarding to master progress
        async def forward_graph_events():
            r = aioredis.from_url(REDIS_URL, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe("crossroad:graph_agent:progress")
            try:
                async for msg in pubsub.listen():
                    if msg["type"] != "message":
                        continue
                    try:
                        evt = json.loads(msg["data"])
                        if evt.get("event") == "crawling":
                            url = evt.get("url","")
                            self.progress.current_crawling = [url]
                            self.progress.graph_depth = evt.get("depth", 0)
                            # Forward all active workers
                            workers = evt.get("workers", [])
                            self.progress.active_workers = workers[:20]  # cap for Redis size
                            await bus.publish(self.progress)
                        elif evt.get("event") == "page_crawled":
                            stats = evt.get("stats", {})
                            workers = evt.get("workers", [])
                            self.progress.active_workers = workers[:20]
                            await self._emit(
                                graph_pages_crawled=stats.get("pages_crawled", 0),
                                graph_nodes=stats.get("nodes_created", 0),
                                graph_edges=stats.get("edges_created", 0),
                            )
                            continue  # skip the duplicate page_crawled handling below
                    except Exception:
                        pass
            except asyncio.CancelledError:
                pass
            finally:
                await pubsub.unsubscribe()
                await r.aclose()

        fwd_task = asyncio.create_task(forward_graph_events())

        # If restart_mode=skip, pre-load already-crawled URLs into visited set
        if limits.get("preload_visited"):
            await self._emit(phase_label="⏭ Loading already-crawled URLs to skip…")
            n = await agent.load_visited_from_db()
            await self._emit(phase_label=f"⏭ Skipping {n} already-crawled pages")

        try:
            job_id = await db.create_job("graph_mine", f"{len(seed_urls)} seeds")
            stats  = await agent.run(seed_urls, job_id=job_id)
        finally:
            fwd_task.cancel()
            try:
                await fwd_task
            except asyncio.CancelledError:
                pass

        await self._emit(
            phase_label=f"Phase 1 complete: {stats['pages_crawled']} pages, "
                        f"{stats['nodes_created']} nodes, {stats['edges_created']} edges",
            graph_pages_crawled=stats.get("pages_crawled", 0),
            graph_nodes=stats.get("nodes_created", 0),
            graph_edges=stats.get("edges_created", 0),
        )
        logger.info(f"Phase 1 complete: {stats}")

    # ── Phase 2: News ─────────────────────────────────────────────────────────

    async def phase2_news(self):
        """Crawl news for all discovered persons + score faction bias."""
        await self._emit(phase="news",
                         phase_label="Phase 2: Crawling news + scoring faction bias…",
                         status="news_crawling")

        persons = await db.list_persons(limit=2000)
        await self._emit(news_persons_total=len(persons))
        logger.info(f"Phase 2: News crawl for {len(persons)} persons")

        sem = asyncio.Semaphore(L3_CONC)
        self.progress.max_news_workers = L3_CONC
        await bus.publish(self.progress)

        async def crawl_one(person: Dict):
            if self._stop:
                return
            await self._check_stop()

            name = person.get("full_name","")
            pid  = person.get("id")
            if not name or not pid:
                return

            async with sem:
                await self._wait_if_paused()
                if self._stop:
                    return
                try:
                    articles = await self.news_cr.crawl_person(name)
                    party = person.get("party")
                    if party and articles:
                        articles = await self.llm.score_news(party, articles)

                    for a in articles[:30]:
                        try:
                            nid = await db.upsert_news(a)
                            await db.link_person_news(pid, nid, a.get("alignment_score",0.0))
                            await self.graph_db.upsert_news(a)
                            slug = slugify(name, separator="-")
                            await self.graph_db.link_person_news(slug, a["url"], a.get("alignment_score",0.0))
                        except Exception:
                            pass

                    self.progress.news_persons_done += 1
                    self.progress.news_articles += len(articles)
                    await bus.publish(self.progress)

                except Exception as e:
                    logger.warning(f"News error [{name}]: {e}")

        await asyncio.gather(*[crawl_one(p) for p in persons], return_exceptions=True)

        await self._emit(
            phase_label=f"Phase 2 complete: {self.progress.news_articles} articles for {self.progress.news_persons_done} persons"
        )
        logger.info(f"Phase 2 complete: {self.progress.news_articles} articles")

    # ── Phase 3: Vectorize ────────────────────────────────────────────────────

    async def phase3_vectorize(self):
        """Embed all persons + news into ChromaDB."""
        await self._emit(phase="vectorize",
                         phase_label="Phase 3: Embedding into ChromaDB for RAG…",
                         status="vectorizing")
        try:
            from vector.chroma import VectorStore
            vs = VectorStore()
            persons = await db.list_persons(limit=5000)
            await vs.embed_persons(persons)
            logger.info(f"Phase 3: Embedded {len(persons)} persons into ChromaDB")
            await self._emit(phase_label=f"Phase 3 complete: {len(persons)} persons embedded")
        except Exception as e:
            logger.error(f"Phase 3 vectorize error: {e}")
            self.progress.errors.append(f"Vectorize: {str(e)[:100]}")

    # ── Main run ──────────────────────────────────────────────────────────────

    async def run(self, run_id: str, limits: Dict, job_id: Optional[int] = None):
        self._stop = False
        self.progress = MasterProgress(
            run_id=run_id,
            status="starting",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        await bus.publish(self.progress)

        if job_id:
            await db.update_job(job_id, "running")

        try:
            # Phase 0: Seed
            officials = await self.phase0_seed(limits)
            if self._stop:
                return

            # Phase 1: Recursive graph mine
            await self.phase1_graph_mine(officials, limits)
            if self._stop:
                return

            # Phase 2: News
            await self.phase2_news()
            if self._stop:
                return

            # Phase 3: Vectorize
            await self.phase3_vectorize()

            # Done
            stats = await db.get_stats()
            await self._emit(
                status="done",
                phase="done",
                phase_label=(
                    f"✓ Complete — {stats.get('total_persons',0)} persons, "
                    f"{stats.get('total_rels',0)} relations, "
                    f"{self.progress.news_articles} articles"
                ),
            )

            if job_id:
                await db.update_job(job_id, "done", summary={
                    "persons":      stats.get("total_persons"),
                    "relations":    stats.get("total_rels"),
                    "news":         self.progress.news_articles,
                    "graph_nodes":  self.progress.graph_nodes,
                    "graph_edges":  self.progress.graph_edges,
                })

        except MemoryError as e:
            logger.error(f"OUT OF MEMORY — reduce concurrency or limits")
            await self._emit(status="error", phase="error",
                             phase_label="⚠ Out of memory — reduce limits and restart")
            if job_id:
                await db.update_job(job_id, "failed", error="MemoryError")
        except Exception as e:
            logger.error(f"Master agent error: {e}", exc_info=True)
            # Don't re-raise — let the backend stay alive even if agent crashes
            await self._emit(status="error", phase="error",
                             phase_label=f"✗ Error: {str(e)[:120]} — backend still running")
            if job_id:
                await db.update_job(job_id, "failed", error=str(e))
            # Note: NOT re-raising so the FastAPI process stays alive


# ── Singleton management ──────────────────────────────────────────────────────

_master: Optional[MasterAgent]   = None
_run_task: Optional[asyncio.Task] = None


def get_master() -> MasterAgent:
    global _master
    if _master is None:
        _master = MasterAgent()
    return _master


async def start_run(limits: Dict, job_id: Optional[int] = None) -> str:
    global _run_task
    run_id = str(uuid.uuid4())[:8]
    if _run_task and not _run_task.done():
        raise RuntimeError("Run already in progress")
    master = get_master()
    _run_task = asyncio.create_task(master.run(run_id, limits, job_id))
    return run_id


async def stop_run():
    await bus.set_command("stop")
    master = get_master()
    master._stop = True


async def pause_run():
    await bus.set_command("pause")


async def resume_run():
    await bus.set_command("resume")


def is_running() -> bool:
    return _run_task is not None and not _run_task.done()
