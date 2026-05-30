"""
CROSSROAD v2 — FastAPI Application
Autonomous 24-hour deep mining system for Indonesian political knowledge graph.
"""
import asyncio
import json
import logging
import os
from typing import List, Optional, Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import db
from graph import GraphDB
from enricher.llm import LLMEnricher
from agents.master import (
    start_run, stop_run, pause_run, resume_run, is_running,
    bus as progress_bus,
)
import redis.asyncio as aioredis
import json as _json

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Crossroad v2 — Indonesian Political Knowledge Graph", version="2.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], allow_credentials=True,
)

_graph_db = GraphDB()
_llm      = LLMEnricher()
_redis: Optional[aioredis.Redis] = None

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL = 60 * 20


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def cache_get(key: str):
    try:
        r = await get_redis()
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, val, ttl: int = CACHE_TTL):
    try:
        r = await get_redis()
        await r.set(key, json.dumps(val, ensure_ascii=False, default=str), ex=ttl)
    except Exception:
        pass


# ── Request models ─────────────────────────────────────────────────────────────

class AgentStartRequest(BaseModel):
    limit_dpr:      int = 100
    limit_menteri:  int = 50
    limit_gubernur: int = 40
    limit_regional: int = 150
    limit_dprd:     int = 100
    # restart_mode:
    #   "fresh"       — wipe everything and start from zero
    #   "skip"        — keep existing data, skip already-crawled pages
    #   "new"         — start normally (default for first run)
    restart_mode: str = "new"

class QueryRequest(BaseModel):
    question: str
    mode: str = "auto"  # auto | rag | cypher

class PathRequest(BaseModel):
    slug_a: str
    slug_b: str


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — always returns 200, reports each service status."""
    status = {}

    try:
        status["neo4j"] = "connected" if await asyncio.wait_for(_graph_db.ping(), timeout=2) else "disconnected"
    except Exception:
        status["neo4j"] = "disconnected"

    try:
        # Ollama can be slow — short timeout, failure is non-critical
        status["ollama"] = "connected" if await asyncio.wait_for(_llm.ping(), timeout=1.5) else "disconnected"
    except Exception:
        status["ollama"] = "disconnected"

    try:
        r = await get_redis()
        status["redis"] = "connected" if await asyncio.wait_for(r.ping(), timeout=1) else "disconnected"
    except Exception:
        status["redis"] = "disconnected"

    try:
        import httpx
        chroma_host = os.getenv('CHROMA_HOST', 'chromadb')
        chroma_port = os.getenv('CHROMA_PORT', '8000')
        # Try v2 first (newer Chroma), fall back to v1
        for path in ("/api/v2/heartbeat", "/api/v1/heartbeat"):
            try:
                async with httpx.AsyncClient(timeout=2) as c:
                    resp = await c.get(f"http://{chroma_host}:{chroma_port}{path}")
                    if resp.status_code in (200, 401):  # 401 = auth required = chroma is up
                        status["chroma"] = "connected"
                        break
            except Exception:
                pass
        else:
            status["chroma"] = "disconnected"
    except Exception:
        status["chroma"] = "disconnected"

    return {
        "status": "ok",   # always 200 — frontend depends on this
        **status,
        "model":        _llm.model,
        "agent_running": is_running(),
        "intelligence": _INTEL_OK if "_INTEL_OK" in globals() else False,
    }


# ── Agent control ──────────────────────────────────────────────────────────────

@app.post("/api/agent/start")
async def agent_start(req: AgentStartRequest, bg: BackgroundTasks):
    if is_running():
        raise HTTPException(409, "Agent is already running. Stop it first.")

    limits = {
        "dpr":          req.limit_dpr,
        "menteri":      req.limit_menteri,
        "gubernur":     req.limit_gubernur,
        "regional":     req.limit_regional,
        "dprd":         req.limit_dprd,
        "restart_mode": req.restart_mode,
    }

    # Handle restart modes
    if req.restart_mode == "fresh":
        # Wipe all crawl data — persons, relations, news, graph
        try:
            await db.truncate_crawl_data()
            await _graph_db.clear_all()
            logger.info("🔄 Fresh restart: all crawl data cleared")
        except Exception as e:
            logger.error(f"Fresh restart clear error: {e}")

    elif req.restart_mode == "skip":
        # Keep data but mark already-crawled pages as visited
        # The graph agent will call load_visited_from_db() on startup
        limits["preload_visited"] = True
        logger.info("⏭ Skip restart: will skip already-crawled pages")

    job_id = await db.create_job("master_agent",
        f"full_run ({req.restart_mode})", total=0)
    run_id = await start_run(limits, job_id)
    return {"run_id": run_id, "job_id": job_id, "status": "started",
            "restart_mode": req.restart_mode}


@app.post("/api/agent/stop")
async def agent_stop():
    await stop_run()
    return {"status": "stop_sent"}


@app.post("/api/agent/pause")
async def agent_pause():
    await pause_run()
    return {"status": "pause_sent"}


@app.post("/api/agent/resume")
async def agent_resume():
    await resume_run()
    return {"status": "resume_sent"}


@app.get("/api/agent/status")
async def agent_status():
    state = await progress_bus.get_state()
    return {
        "running": is_running(),
        "state": state,
    }


# ── SSE progress stream ────────────────────────────────────────────────────────

@app.get("/api/agent/stream")
async def agent_stream():
    """
    Server-Sent Events stream for real-time agent progress.
    Frontend subscribes to this to update the progress dashboard.
    """
    async def event_generator():
        r = await get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe("crossroad:agent:progress")
        try:
            # Send current state immediately
            state = await progress_bus.get_state()
            if state:
                yield f"data: {json.dumps(state)}\n\n"
            # Stream updates
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data']}\n\n"
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe("crossroad:agent:progress")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── Persons ────────────────────────────────────────────────────────────────────

@app.get("/api/persons")
async def list_persons(
    role_type: Optional[str] = Query(None),
    party:     Optional[str] = Query(None),
    province:  Optional[str] = Query(None),
    limit:     int           = Query(300),
):
    ck = f"persons:{role_type}:{party}:{province}:{limit}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "persons": cached}
    persons = await db.list_persons(role_type=role_type, party=party, province=province, limit=limit)
    await cache_set(ck, persons, 60 * 5)
    return {"source": "live", "persons": persons}


@app.get("/api/persons/search")
async def search_persons(q: str = Query(..., min_length=2)):
    pg = await db.search_persons(q, limit=15)
    neo = await _graph_db.search_graph(q)
    seen = {p.get("slug","") for p in pg}
    for n in neo:
        if n.get("slug","") not in seen:
            pg.append({"full_name": n.get("name",""), "slug": n.get("slug",""),
                        "party": n.get("party"), "role_type": n.get("role_type")})
    return {"results": pg[:20]}


@app.get("/api/persons/{slug}")
async def get_person(slug: str):
    ck = f"person:{slug}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "person": cached}
    person = await db.get_person(slug)
    if not person:
        raise HTTPException(404, f"Person '{slug}' not found")
    await cache_set(ck, person, 60 * 15)
    return {"source": "live", "person": person}


@app.get("/api/persons/{slug}/news")
async def get_person_news(slug: str):
    ck = f"news:{slug}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "articles": cached}
    person = await db.get_person(slug)
    if not person:
        raise HTTPException(404, "Person not found")
    articles = await db.get_person_news(person["id"], limit=40)
    await cache_set(ck, articles, 60 * 15)
    return {"source": "live", "articles": articles}


@app.get("/api/persons/{slug}/relations")
async def get_relations(slug: str):
    person = await db.get_person(slug)
    if not person:
        raise HTTPException(404, "Person not found")
    rels = await db.get_relationships(person["id"])
    return {"relationships": rels}


# ── Graph ──────────────────────────────────────────────────────────────────────

@app.get("/api/graph/ego/{slug}")
async def ego_graph(slug: str, depth: int = Query(2, ge=1, le=3)):
    ck = f"ego:{slug}:{depth}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", **cached}
    data = await _graph_db.get_ego_graph(slug, depth=depth)
    if not data["nodes"]:
        person = await db.get_person(slug)
        if person:
            data = {
                "nodes": [{"id": slug, "name": person["full_name"], "_label": "Person",
                           "party": person.get("party"), "role_type": person.get("role_type")}],
                "edges": [], "center": slug,
            }
    await cache_set(ck, data, 60 * 15)
    return {"source": "live", **data}


@app.get("/api/graph/full")
async def full_graph(limit: int = Query(500, le=1000)):
    ck = f"full_graph:{limit}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", **cached}
    data = await _graph_db.get_full_graph(limit=limit)
    await cache_set(ck, data, 60 * 3)
    return {"source": "live", **data}


@app.post("/api/graph/path")
async def path_between(req: PathRequest):
    return await _graph_db.get_path_between(req.slug_a, req.slug_b)


# ── NL Query / RAG ────────────────────────────────────────────────────────────

@app.post("/api/query")
async def nl_query(req: QueryRequest):
    """
    Natural language query interface.
    Combines ChromaDB RAG + Ollama LLM + optional Cypher translation.
    """
    from vector.chroma import VectorStore, KnowledgeInterface
    vs = VectorStore()
    ki = KnowledgeInterface(_graph_db, vs)
    result = await ki.query(req.question, mode=req.mode)
    return result


@app.get("/api/query/vector-search")
async def vector_search(q: str = Query(..., min_length=3), n: int = Query(5, le=20)):
    """Direct semantic similarity search against ChromaDB."""
    from vector.chroma import VectorStore
    vs = VectorStore()
    results = await vs.search_all(q, n_each=n)
    return results


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
async def stats():
    ck = "stats"
    cached = await cache_get(ck)
    if cached:
        return cached
    s = await db.get_stats()
    # Add vector store counts
    try:
        from vector.chroma import VectorStore
        vs = VectorStore()
        s["chroma_persons"] = vs.count("persons_bio")
        s["chroma_news"]    = vs.count("news_articles")
    except Exception:
        pass
    await cache_set(ck, s, 60 * 3)
    return s


@app.get("/api/jobs")
async def list_jobs():
    jobs = await db.get_jobs(limit=30)
    return {"jobs": jobs}


# ── Lifecycle ──────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    await _graph_db.init_schema()
    logger.info("🇮🇩 Crossroad v2 started — Autonomous Knowledge Graph ready")
    # Auto-start if configured
    if os.getenv("AUTO_START_CRAWLER","false").lower() == "true":
        logger.info("AUTO_START_CRAWLER=true — starting master agent…")
        limits = {
            "dpr": int(os.getenv("DISCOVER_LIMIT_DPR","100")),
            "menteri": int(os.getenv("DISCOVER_LIMIT_MENTERI","50")),
            "gubernur": 40,
            "regional": int(os.getenv("DISCOVER_LIMIT_REGIONAL","150")),
            "dprd": int(os.getenv("DISCOVER_LIMIT_DPRD","100")),
        }
        job_id = await db.create_job("master_agent", "auto_start", total=0)
        await start_run(limits, job_id)


@app.on_event("shutdown")
async def shutdown():
    await stop_run()
    await _graph_db.close()
    await db.close()
    if _redis:
        await _redis.aclose()


# ══════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE ENDPOINTS — Dynasty, Coalition, Faction
# ══════════════════════════════════════════════════════════════════════════════

try:
    from intelligence.dynasties  import DynastyDetector
    from intelligence.coalitions import CoalitionViewer, COALITIONS
    _INTEL_OK = True
except ImportError as e:
    logger.warning(f"Intelligence modules not loaded: {e}")
    DynastyDetector = None
    CoalitionViewer = None
    COALITIONS = {}
    _INTEL_OK = False

_dynasty_detector: Optional[DynastyDetector] = None
_coalition_viewer: Optional[CoalitionViewer]  = None


def _get_dynasty():
    global _dynasty_detector
    if not _INTEL_OK:
        return None
    if _dynasty_detector is None:
        _dynasty_detector = DynastyDetector(graph_db=_graph_db, db=db)
    return _dynasty_detector


def _get_coalition():
    global _coalition_viewer
    if not _INTEL_OK:
        return None
    if _coalition_viewer is None:
        _coalition_viewer = CoalitionViewer(db=db, graph_db=_graph_db)
    return _coalition_viewer


# ── Dynasty ────────────────────────────────────────────────────────────────────

@app.get("/api/dynasties")
async def list_dynasties(min_members: int = Query(2, ge=2, le=10)):
    """Detect all political dynasties in the knowledge base."""
    detector = _get_dynasty()
    if not detector:
        return {"source": "unavailable", "dynasties": [], "count": 0}
    ck = f"dynasties:{min_members}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "dynasties": cached}
    dynasties = await detector.detect_all(min_members=min_members)
    await cache_set(ck, dynasties, 60 * 10)
    return {"source": "live", "dynasties": dynasties, "count": len(dynasties)}


@app.get("/api/dynasties/{slug}")
async def get_dynasty_for_person(slug: str):
    """Get the dynasty that a specific person belongs to."""
    detector = _get_dynasty()
    dynasty  = await detector.detect_for_person(slug)
    if not dynasty:
        return {"dynasty": None, "message": "No dynasty detected for this person"}
    return {"dynasty": dynasty}


@app.get("/api/dynasties/{slug}/graph")
async def dynasty_graph(slug: str):
    """Get the family graph for dynasty visualization."""
    ck = f"dynasty_graph:{slug}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", **cached}
    data = await _graph_db.get_family_cluster(slug, depth=3)
    await cache_set(ck, data, 60 * 15)
    return {"source": "live", **data}


# ── Coalitions ─────────────────────────────────────────────────────────────────

@app.get("/api/coalitions")
async def list_coalitions():
    """List all known political coalitions."""
    viewer = _get_coalition()
    if not viewer:
        return {"coalitions": []}
    return {"coalitions": viewer.get_all_coalitions()}


@app.get("/api/coalitions/{coalition_id}")
async def get_coalition(coalition_id: str):
    """Get full details of a coalition including all member persons."""
    ck = f"coalition:{coalition_id}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", **cached}
    viewer = _get_coalition()
    data   = await viewer.get_coalition_members(coalition_id)
    await cache_set(ck, data, 60 * 15)
    return {"source": "live", **data}


@app.get("/api/coalitions/{coalition_id}/graph")
async def coalition_graph(coalition_id: str):
    """Get the Neo4j subgraph for a coalition's member parties."""
    coalition = COALITIONS.get(coalition_id)
    if not coalition:
        raise HTTPException(404, f"Coalition '{coalition_id}' not found")
    parties = coalition["core_parties"] + coalition.get("supporting_parties", [])
    ck = f"coalition_graph:{coalition_id}"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", **cached}
    data = await _graph_db.get_coalition_subgraph(parties)
    await cache_set(ck, data, 60 * 10)
    return {"source": "live", **data}


@app.get("/api/factions/{party}")
async def get_faction(party: str):
    """Get coalition/faction info for a party."""
    viewer = _get_coalition()
    return viewer.get_faction_for_party(party)


@app.get("/api/factions/person/{slug}")
async def get_faction_for_person(slug: str):
    """Get the coalition/faction of a person based on their party."""
    person = await db.get_person(slug)
    if not person:
        raise HTTPException(404, "Person not found")
    viewer  = _get_coalition()
    faction = viewer.get_faction_for_person(person.get("party",""))
    return {"person": person.get("full_name"), "party": person.get("party"), **faction}


@app.get("/api/coalitions/regional/all")
async def regional_coalitions():
    """Map all governors/mayors/regents to their national coalition."""
    ck = "regional_coalitions"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "regions": cached}
    viewer = _get_coalition()
    data   = await viewer.get_regional_coalitions()
    await cache_set(ck, data, 60 * 10)
    return {"source": "live", "regions": data}


@app.get("/api/media-bias/{outlet}")
async def media_bias(outlet: str):
    """Get political bias metadata for a news outlet."""
    viewer = _get_coalition()
    return viewer.score_news_source_bias(outlet)


# ── Cross-coalition links ──────────────────────────────────────────────────────

@app.get("/api/coalitions/cross-links")
async def cross_coalition_links():
    """Find political alliances that cross coalition lines."""
    ck = "cross_coalition_links"
    cached = await cache_get(ck)
    if cached:
        return {"source": "cache", "links": cached}
    viewer = _get_coalition()
    links  = await viewer.find_cross_coalition_links()
    await cache_set(ck, links, 60 * 15)
    return {"source": "live", "links": links}
