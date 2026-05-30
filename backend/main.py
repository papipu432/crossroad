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
    
    # Start scheduler if enabled
    if os.getenv("ENABLE_SCHEDULER", "false").lower() == "true":
        from scheduler import start_scheduler
        asyncio.create_task(start_scheduler())
        logger.info("🕐 Scheduler enabled — daily updates active")
    
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


# ── Enhanced Data Sources API ───────────────────────────────────────────────

@app.get("/api/enhanced/person/{slug}/dossier")
async def get_person_dossier(slug: str):
    """
    Get comprehensive intelligence dossier for a person.
    Includes: assets, KPK cases, business interests, risk score.
    """
    from crawler.enhanced_sources import IntegratedDataSource
    
    person = await db.get_person(slug)
    if not person:
        raise HTTPException(404, "Person not found")
    
    source = IntegratedDataSource()
    try:
        dossier = await source.enrich_person(
            slug,
            person.get("full_name", ""),
            person.get("current_position", "")
        )
        return {"source": "live", **dossier}
    finally:
        await source.close_all()


@app.get("/api/enhanced/kpu/candidates")
async def get_kpu_candidates(level: str = Query("nasional")):
    """Get election candidates from KPU."""
    from crawler.enhanced_sources import crawl_kpu_candidates
    
    candidates = await crawl_kpu_candidates(level)
    return {"candidates": candidates, "count": len(candidates)}


@app.get("/api/enhanced/lhkpn/{name}")
async def search_lhkpn(name: str):
    """Search asset declarations by name."""
    from crawler.enhanced_sources import crawl_lhkpn_assets
    
    declarations = await crawl_lhkpn_assets(name)
    return {
        "declarations": [
            {
                "name": d.name,
                "position": d.position,
                "report_date": d.report_date,
                "total_assets": d.total_assets,
                "net_worth": d.total_assets - d.liabilities,
                "source_url": d.source_url
            }
            for d in declarations
        ],
        "count": len(declarations)
    }


@app.get("/api/enhanced/kpk/search")
async def search_kpk(q: str = Query(..., min_length=2)):
    """Search KPK corruption cases."""
    from crawler.enhanced_sources import crawl_kpk_cases
    
    cases = await crawl_kpk_cases(q)
    return {
        "cases": [
            {
                "title": c.title,
                "status": c.status,
                "category": c.category,
                "loss_amount": c.loss_amount,
                "source_url": c.source_url
            }
            for c in cases
        ],
        "count": len(cases)
    }


@app.get("/api/scheduler/status")
async def scheduler_status():
    """Get scheduler status and upcoming tasks."""
    from scheduler import get_scheduler
    
    scheduler = get_scheduler()
    if not scheduler:
        return {"enabled": False, "message": "Scheduler not running"}
    
    return {
        "enabled": True,
        "running": scheduler.running,
        "tasks": [
            {
                "name": t.name,
                "type": t.schedule_type.value,
                "interval_hours": t.interval_hours,
                "last_run": t.last_run.isoformat() if t.last_run else None,
                "next_run": t.next_run.isoformat() if t.next_run else None,
                "enabled": t.enabled,
                "errors": t.errors
            }
            for t in scheduler.tasks.values()
        ]
    }


@app.get("/api/changes/recent")
async def get_recent_changes(hours: int = Query(24, ge=1, le=168)):
    """Get recent changes from audit log."""
    from scheduler import DynamicUpdater, GraphDB, LLMEnricher
    
    graph_db = GraphDB()
    llm = LLMEnricher()
    updater = DynamicUpdater(graph_db, llm)
    
    try:
        changes = await updater.get_recent_changes(hours)
        return {"changes": changes, "count": len(changes)}
    finally:
        await graph_db.close()


# ── Business Registry Endpoints ───────────────────────────────────────────────

@app.get("/api/business/person/{slug}/portfolio")
async def get_person_business_portfolio(slug: str):
    """
    Get complete business portfolio for a politician.
    Returns companies where they are shareholder, commissioner, or director.
    """
    from crawler.business_registry import BusinessRegistryIntegration
    from db import get_person_by_slug
    
    # Get person details
    person = await get_person_by_slug(slug)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    integration = BusinessRegistryIntegration()
    try:
        portfolio = await integration.get_person_business_portfolio(person['full_name'])
        
        # Also get from graph DB
        companies = await _graph_db.get_person_companies(slug)
        
        # Detect conflicts
        conflicts = await _graph_db.detect_business_conflicts(slug)
        
        return {
            "person": person,
            "portfolio": portfolio,
            "graph_companies": companies,
            "conflicts_detected": conflicts,
            "total_companies": portfolio['total_companies'] + len(companies)
        }
    finally:
        await integration.close_all()


@app.get("/api/business/company/{npwb}")
async def get_company_details(npwb: str):
    """
    Get company details and all associated politicians.
    """
    people = await _graph_db.get_company_people(npwb)
    
    if not people:
        # Try to fetch from registry
        from crawler.business_registry import AHUEnhancedCrawler
        
        crawler = AHUEnhancedCrawler()
        try:
            # Search by NPWB
            companies = await crawler.search_company_by_name(npwb, exact=True)
            if companies:
                company = companies[0]
                
                # Store in graph
                await _graph_db.upsert_company({
                    "npwb": company.npwb,
                    "name": company.name,
                    "establishment_date": company.establishment_date,
                    "capital_authorized": company.capital_authorized,
                    "capital_paid": company.capital_paid,
                    "status": company.status,
                    "province": company.province,
                    "city": company.city,
                    "business_activities": company.business_activities,
                    "source_url": company.source_url
                })
                
                return {
                    "company": {
                        "name": company.name,
                        "npwb": company.npwb,
                        "establishment_date": company.establishment_date,
                        "capital": company.capital_authorized,
                        "status": company.status,
                        "province": company.province,
                        "shareholders": [
                            {"name": s.name, "percent": s.shares_percent}
                            for s in company.shareholders
                        ],
                        "commissioners": [
                            {"name": c.name, "appointment_date": c.appointment_date}
                            for c in company.commissioners
                        ],
                        "directors": [
                            {"name": d.name, "appointment_date": d.appointment_date}
                            for d in company.directors
                        ]
                    },
                    "people": []
                }
        finally:
            await crawler.close()
        
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"company_npwb": npwb, "associated_people": people}


@app.post("/api/business/scan/{slug}")
async def scan_person_business_connections(slug: str, background_tasks: BackgroundTasks):
    """
    Trigger a background scan of business connections for a person.
    Stores results in graph database.
    """
    from crawler.business_registry import BusinessRegistryIntegration
    from db import get_person_by_slug
    
    person = await get_person_by_slug(slug)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    async def scan_task():
        integration = BusinessRegistryIntegration()
        try:
            portfolio = await integration.get_person_business_portfolio(person['full_name'])
            
            # Store companies in graph
            for company_data in portfolio.get('private_companies', []):
                await _graph_db.upsert_company(company_data)
                
                # Link person to company
                if portfolio.get('as_shareholder'):
                    for share in portfolio['as_shareholder']:
                        if share['company'] == company_data['name']:
                            await _graph_db.link_person_company(
                                slug, 
                                company_data.get('npwb', ''),
                                'shareholder',
                                {
                                    'shares_percent': share.get('shares_percent'),
                                    'shares_value': share.get('shares_value')
                                }
                            )
                
                if portfolio.get('as_commissioner'):
                    for comm in portfolio['as_commissioner']:
                        if comm['company'] == company_data['name']:
                            await _graph_db.link_person_company(
                                slug,
                                company_data.get('npwb', ''),
                                'commissioner',
                                {'appointment_date': comm.get('appointment_date')}
                            )
                
                if portfolio.get('as_director'):
                    for director in portfolio['as_director']:
                        if director['company'] == company_data['name']:
                            await _graph_db.link_person_company(
                                slug,
                                company_data.get('npwb', ''),
                                'director',
                                {'appointment_date': director.get('appointment_date')}
                            )
            
            logger.info(f"Business scan completed for {slug}: {portfolio['total_companies']} companies found")
            
        except Exception as e:
            logger.error(f"Business scan error for {slug}: {e}")
        finally:
            await integration.close_all()
    
    background_tasks.add_task(scan_task)
    
    return {
        "status": "scanning",
        "message": f"Background scan started for {person['full_name']}",
        "person_slug": slug
    }


@app.get("/api/business/conflicts/detect")
async def detect_all_conflicts():
    """
    Detect conflicts of interest for all politicians in the database.
    Returns list of flagged individuals.
    """
    from db import execute_query
    
    query = """
    SELECT p.slug, p.full_name, p.position, p.party
    FROM persons p
    WHERE p.position IS NOT NULL
    AND (p.position LIKE '%Menteri%' OR p.position LIKE '%Gubernur%' 
         OR p.position LIKE '%Anggota Komisi%' OR p.position LIKE '%DPR%')
    """
    
    results = await execute_query(query)
    
    all_conflicts = []
    
    for person in results:
        conflicts = await _graph_db.detect_business_conflicts(person['slug'])
        if conflicts:
            all_conflicts.append({
                "person": person,
                "conflicts": conflicts,
                "severity": max([c.get('severity', 'low') for c in conflicts], key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x, 0))
            })
    
    # Sort by severity
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    all_conflicts.sort(key=lambda x: severity_order.get(x['severity'], 3))
    
    return {
        "total_flagged": len(all_conflicts),
        "conflicts": all_conflicts
    }


@app.get("/api/business/sectors/{sector}")
async def get_companies_by_sector(sector: str):
    """
    Get all companies in a specific sector and their political connections.
    """
    from neo4j.exceptions import CypherSyntaxError
    
    try:
        q = """
        MATCH (c:Company)
        WHERE ANY(activity IN c.business_activities WHERE toLower(activity) CONTAINS toLower($sector))
        OPTIONAL MATCH (p:Person)-[r]->(c)
        RETURN c, collect(DISTINCT p) AS politicians, collect(DISTINCT r) AS relationships
        """
        
        results = []
        async with _graph_db.driver.session() as s:
            cursor = await s.run(q, {"sector": sector})
            async for record in cursor:
                company = dict(record["c"])
                politicians = [dict(p) for p in record["politicians"] if p]
                relationships = [dict(r) for r in record["relationships"] if r]
                
                results.append({
                    "company": company,
                    "politicians": politicians,
                    "relationships": relationships
                })
        
        return {"sector": sector, "companies": results, "count": len(results)}
        
    except Exception as e:
        logger.error(f"Sector query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 🔍 MAS'UD DYNASTY & OLIGARCHY DETECTION API
# ============================================================================

@app.get("/api/oligarchy/masud-dynasty")
async def scan_masud_dynasty():
    """
    Comprehensive investigation of the Mas'ud Dynasty in East Kalimantan.
    
    Detects:
    - Family members in government positions
    - Business ownership networks
    - Self-dealing schemes (politician → company → government contract)
    - Monopoly patterns (like "Harum Resort" exclusive mandates)
    - Oligarchy score with risk assessment
    
    Returns detailed report with warning flags and evidence.
    """
    from tests.test_masud_dynasty import MasudDynastyDetector
    
    detector = MasudDynastyDetector(_graph_db, db)
    
    try:
        score = await detector.scan_masud_dynasty()
        
        # Convert dataclasses to dicts for JSON response
        schemes_list = []
        for scheme in score.detected_schemes:
            schemes_list.append({
                "politician_name": scheme.politician_name,
                "politician_position": scheme.politician_position,
                "company_name": scheme.company_name,
                "company_npwb": scheme.company_npwb,
                "relationship_type": scheme.relationship_type,
                "government_contract_type": scheme.government_contract_type,
                "contract_value": scheme.contract_value,
                "is_exclusive": scheme.is_exclusive,
                "confidence_score": scheme.confidence_score,
                "evidence_urls": scheme.evidence_urls,
                "detection_date": scheme.detection_date,
            })
        
        return {
            "investigation_status": "complete",
            "family_name": score.family_name,
            "risk_level": score.risk_level,
            "total_score": score.total_score,
            "component_scores": {
                "wealth_concentration": score.wealth_concentration,
                "political_power": score.political_power,
                "business_density": score.business_density,
                "conflict_severity": score.conflict_severity,
                "monopoly_control": score.monopoly_control,
            },
            "statistics": {
                "total_companies": score.total_companies,
                "government_positions": score.total_government_positions,
                "self_dealing_schemes": len(score.detected_schemes),
            },
            "warning_flags": score.warning_flags,
            "detected_schemes": schemes_list,
        }
        
    except Exception as e:
        logger.error(f"Mas'ud dynasty scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/oligarchy/{person_slug}/score")
async def get_oligarchy_score(person_slug: str):
    """
    Get oligarchy score for a specific person.
    
    Analyzes:
    - Number of companies owned
    - Government position held
    - Conflict of interest severity
    - Family political network
    """
    from intelligence.dynasties import DynastyDetector
    from tests.test_masud_dynasty import MasudDynastyDetector
    
    detector = MasudDynastyDetector(_graph_db, db)
    
    # Get person info
    person = await db.get_person(person_slug)
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    
    # Check if person is part of any dynasty
    dynasty_detector = DynastyDetector(_graph_db, db)
    dynasty_info = await dynasty_detector.detect_for_person(person_slug)
    
    # Get business holdings
    try:
        companies = await _graph_db.get_person_companies(person_slug)
    except Exception:
        companies = []
    
    # Get conflicts
    try:
        conflicts = await _graph_db.detect_business_conflicts(person_slug)
    except Exception:
        conflicts = []
    
    # Calculate simple oligarchy indicators
    indicators = {
        "has_government_position": bool(person.get("position")),
        "owns_companies": len(companies) > 0,
        "company_count": len(companies),
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "is_dynasty_member": dynasty_info is not None,
        "dynasty_score": dynasty_info.get("dynasty_score") if dynasty_info else None,
    }
    
    # Simple risk calculation
    risk_score = 0.0
    if indicators["has_government_position"]:
        risk_score += 0.3
    if indicators["owns_companies"]:
        risk_score += min(indicators["company_count"] * 0.1, 0.3)
    if indicators["has_conflicts"]:
        risk_score += min(indicators["conflict_count"] * 0.15, 0.3)
    if indicators["is_dynasty_member"]:
        risk_score += 0.1
    
    risk_level = "LOW"
    if risk_score >= 0.7:
        risk_level = "CRITICAL"
    elif risk_score >= 0.5:
        risk_level = "HIGH"
    elif risk_score >= 0.3:
        risk_level = "MEDIUM"
    
    return {
        "person": {
            "slug": person_slug,
            "name": person.get("full_name") or person.get("name"),
            "position": person.get("position"),
            "party": person.get("party"),
            "province": person.get("province"),
        },
        "oligarchy_indicators": indicators,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "dynasty_info": dynasty_info,
        "companies": companies,
        "conflicts": conflicts,
    }


@app.post("/api/oligarchy/scan-all")
async def scan_all_oligarchs(background_tasks: BackgroundTasks):
    """
    Trigger background scan of all politicians for oligarchy patterns.
    Returns task ID to check status later.
    """
    import uuid
    from scheduler import OligarchyScanner
    
    task_id = str(uuid.uuid4())
    
    async def run_scan():
        scanner = OligarchyScanner(_graph_db, db)
        results = await scanner.scan_all_politicians()
        # Cache results
        await cache_set(f"oligarchy:scan:{task_id}", results, ttl=3600)
    
    background_tasks.add_task(run_scan)
    
    return {
        "task_id": task_id,
        "status": "started",
        "message": "Oligarchy scan initiated. Check status via /api/oligarchy/scan-status/{task_id}"
    }


@app.get("/api/oligarchy/scan-status/{task_id}")
async def get_scan_status(task_id: str):
    """Get status of oligarchy scan task."""
    result = await cache_get(f"oligarchy:scan:{task_id}")
    
    if result is None:
        return {"task_id": task_id, "status": "pending", "message": "Scan still running or not found"}
    
    return {
        "task_id": task_id,
        "status": "complete",
        "results": result
    }


@app.get("/api/self-dealing/detect-loops")
async def detect_self_dealing_loops():
    """
    Detect self-dealing loops in the graph:
    Politician → Owns Company → Wins Government Contract → Profits
    
    Returns all detected loops with confidence scores.
    """
    query = """
    MATCH (p:Person)-[r1:OWNS_SHARES|COMMISSIONER_OF|DIRECTOR_OF|BENEFICIAL_OWNER_OF]->(c:Company)
    WHERE r1.is_current = true
    MATCH (c)-[r2:WON_CONTRACT]->(g:GovernmentContract)
    OPTIONAL MATCH (p)-[:MEMBER_OF|WORKS_AT]->(agency:Org)
    WHERE agency.name IN g.agency_name
    RETURN p, c, g, r1, r2, agency
    ORDER BY g.contract_value DESC
    LIMIT 100
    """
    
    loops = []
    try:
        async with _graph_db.driver.session() as session:
            result = await session.run(query)
            async for record in result:
                person = dict(record["p"]) if record["p"] else {}
                company = dict(record["c"]) if record["c"] else {}
                contract = dict(record["g"]) if record["g"] else {}
                ownership = dict(record["r1"]) if record["r1"] else {}
                contract_rel = dict(record["r2"]) if record["r2"] else {}
                agency = dict(record["agency"]) if record["agency"] else {}
                
                # Calculate conflict score
                conflict_score = 0.7
                if agency:
                    conflict_score = 0.95  # Direct agency connection
                
                loops.append({
                    "politician": {
                        "name": person.get("name"),
                        "position": person.get("position"),
                        "party": person.get("party"),
                    },
                    "company": {
                        "name": company.get("name"),
                        "npwb": company.get("npwb"),
                        "activities": company.get("business_activities"),
                    },
                    "contract": {
                        "id": contract.get("contract_id"),
                        "title": contract.get("title"),
                        "value": contract.get("contract_value"),
                        "agency": contract.get("agency_name") or agency.get("name"),
                        "date": contract.get("award_date"),
                    },
                    "ownership_role": ownership.get("role_type"),
                    "shares_percent": ownership.get("shares_percent"),
                    "conflict_score": conflict_score,
                    "is_self_dealing": conflict_score > 0.8,
                })
        
        return {
            "total_loops": len(loops),
            "high_confidence": sum(1 for l in loops if l["conflict_score"] > 0.8),
            "loops": loops
        }
        
    except Exception as e:
        logger.error(f"Self-dealing loop detection error: {e}")
        # Return empty if no contracts in DB yet
        return {
            "total_loops": 0,
            "high_confidence": 0,
            "loops": [],
            "note": "No government contract data available yet. Run LPSE crawler first."
        }
