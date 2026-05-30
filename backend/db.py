"""Async PostgreSQL client for Crossroad."""
import json
import logging
import os
from typing import Any, Dict, List, Optional

import asyncpg
from slugify import slugify

logger = logging.getLogger(__name__)
PG_DSN = os.getenv("PG_DSN", "postgresql://crossroad:crossroad2025@postgres:5432/crossroad")
_pool: Optional[asyncpg.Pool] = None


async def pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(PG_DSN, min_size=2, max_size=15)
    return _pool


async def close():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def _slug(name: str) -> str:
    return slugify(name, separator="-", lowercase=True)


def _j(v) -> str:
    return json.dumps(v or [], ensure_ascii=False)


def _pj(v) -> Any:
    if v is None:
        return []
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return []
    return v


# ── Persons ────────────────────────────────────────────────────────────────────

async def upsert_person(p: Dict) -> int:
    db = await pool()
    slug = _slug(p.get("name", p.get("full_name", "")))
    sql = """
        INSERT INTO persons
            (slug, full_name, aliases, photo_url, born, birthplace, religion, ethnicity, gender,
             role_type, current_position, party, faction, dapil, province,
             bio, education, career, companies, awards, wiki_url_id, wiki_url_en,
             sources, crawl_depth, crawled_at, enriched_at)
        VALUES
            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26)
        ON CONFLICT (slug) DO UPDATE SET
            full_name        = EXCLUDED.full_name,
            aliases          = COALESCE(EXCLUDED.aliases, persons.aliases),
            photo_url        = COALESCE(EXCLUDED.photo_url, persons.photo_url),
            born             = COALESCE(EXCLUDED.born, persons.born),
            birthplace       = COALESCE(EXCLUDED.birthplace, persons.birthplace),
            religion         = COALESCE(EXCLUDED.religion, persons.religion),
            role_type        = COALESCE(EXCLUDED.role_type, persons.role_type),
            current_position = COALESCE(EXCLUDED.current_position, persons.current_position),
            party            = COALESCE(EXCLUDED.party, persons.party),
            faction          = COALESCE(EXCLUDED.faction, persons.faction),
            dapil            = COALESCE(EXCLUDED.dapil, persons.dapil),
            province         = COALESCE(EXCLUDED.province, persons.province),
            bio              = COALESCE(EXCLUDED.bio, persons.bio),
            education        = CASE WHEN EXCLUDED.education::text != '[]' THEN EXCLUDED.education ELSE persons.education END,
            career           = CASE WHEN EXCLUDED.career::text != '[]' THEN EXCLUDED.career ELSE persons.career END,
            companies        = CASE WHEN EXCLUDED.companies::text != '[]' THEN EXCLUDED.companies ELSE persons.companies END,
            wiki_url_id      = COALESCE(EXCLUDED.wiki_url_id, persons.wiki_url_id),
            wiki_url_en      = COALESCE(EXCLUDED.wiki_url_en, persons.wiki_url_en),
            sources          = EXCLUDED.sources,
            crawl_depth      = LEAST(EXCLUDED.crawl_depth, persons.crawl_depth),
            crawled_at       = EXCLUDED.crawled_at,
            enriched_at      = COALESCE(EXCLUDED.enriched_at, persons.enriched_at),
            updated_at       = NOW()
        RETURNING id
    """
    row = await db.fetchrow(sql,
        slug,
        p.get("name") or p.get("full_name", ""),
        p.get("aliases"),
        p.get("photo_url"),
        p.get("born"),
        p.get("birthplace"),
        p.get("religion"),
        p.get("ethnicity"),
        p.get("gender", "male"),
        p.get("role_type"),
        p.get("position") or p.get("current_position"),
        p.get("party"),
        p.get("faction"),
        p.get("dapil"),
        p.get("province"),
        p.get("bio"),
        _j(p.get("education")),
        _j(p.get("career")),
        _j(p.get("companies")),
        _j(p.get("awards")),
        p.get("wiki_url_id") or p.get("wiki_url"),
        p.get("wiki_url_en"),
        _j(p.get("sources")),
        p.get("crawl_depth", 0),
        p.get("crawled_at"),
        p.get("enriched_at"),
    )
    return row["id"]


async def get_person(identifier: str) -> Optional[Dict]:
    """Find by slug or name substring."""
    db = await pool()
    slug = _slug(identifier)
    row = await db.fetchrow("SELECT * FROM persons WHERE slug=$1", slug)
    if not row:
        row = await db.fetchrow(
            "SELECT * FROM persons WHERE full_name ILIKE $1 ORDER BY id LIMIT 1",
            f"%{identifier}%"
        )
    if not row:
        # full-text search
        row = await db.fetchrow(
            "SELECT * FROM persons WHERE to_tsvector('simple', full_name) @@ plainto_tsquery('simple', $1) LIMIT 1",
            identifier
        )
    return _person_dict(row) if row else None


async def list_persons(role_type: Optional[str] = None, party: Optional[str] = None,
                       province: Optional[str] = None, limit: int = 300) -> List[Dict]:
    db = await pool()
    wheres, params = [], []
    if role_type and role_type != "all":
        params.append(role_type)
        wheres.append(f"role_type = ${len(params)}")
    if party:
        params.append(party)
        wheres.append(f"party = ${len(params)}")
    if province:
        params.append(f"%{province}%")
        wheres.append(f"province ILIKE ${len(params)}")
    params.append(limit)
    where_clause = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    rows = await db.fetch(f"SELECT * FROM persons {where_clause} ORDER BY full_name LIMIT ${len(params)}", *params)
    return [_person_dict(r) for r in rows]


async def search_persons(q: str, limit: int = 20) -> List[Dict]:
    db = await pool()
    rows = await db.fetch(
        """SELECT * FROM persons
           WHERE full_name ILIKE $1
              OR to_tsvector('simple', full_name) @@ plainto_tsquery('simple', $2)
           ORDER BY
             CASE WHEN full_name ILIKE $1 THEN 0 ELSE 1 END, full_name
           LIMIT $3""",
        f"%{q}%", q, limit
    )
    return [_person_dict(r) for r in rows]


def _person_dict(row) -> Dict:
    d = dict(row)
    for key in ("education", "career", "companies", "awards", "sources"):
        d[key] = _pj(d.get(key))
    return d


# ── Organisations ──────────────────────────────────────────────────────────────

async def upsert_org(o: Dict) -> int:
    db = await pool()
    slug = _slug(o.get("name", ""))
    sql = """
        INSERT INTO organisations (slug, name, short_name, org_type, description, founded, website)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (slug) DO UPDATE SET
            name        = EXCLUDED.name,
            short_name  = COALESCE(EXCLUDED.short_name, organisations.short_name),
            description = COALESCE(EXCLUDED.description, organisations.description),
            founded     = COALESCE(EXCLUDED.founded, organisations.founded),
            website     = COALESCE(EXCLUDED.website, organisations.website)
        RETURNING id
    """
    row = await db.fetchrow(sql, slug, o["name"], o.get("short_name"),
                            o.get("org_type"), o.get("description"), o.get("founded"), o.get("website"))
    return row["id"]


async def get_org(name: str) -> Optional[Dict]:
    db = await pool()
    row = await db.fetchrow("SELECT * FROM organisations WHERE name ILIKE $1 OR short_name ILIKE $1 LIMIT 1", name)
    return dict(row) if row else None


# ── Relationships ──────────────────────────────────────────────────────────────

async def upsert_relationship(rel: Dict) -> int:
    db = await pool()
    sql = """
        INSERT INTO relationships
            (from_id, from_type, to_id, to_type, rel_type, subtype, label,
             year_start, year_end, is_current, weight, sources, notes)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        ON CONFLICT DO NOTHING
        RETURNING id
    """
    row = await db.fetchrow(sql,
        rel["from_id"], rel.get("from_type", "person"),
        rel["to_id"],   rel.get("to_type", "person"),
        rel["rel_type"], rel.get("subtype"),
        rel.get("label"),
        rel.get("year_start"), rel.get("year_end"),
        rel.get("is_current", True),
        rel.get("weight", 1.0),
        _j(rel.get("sources")),
        rel.get("notes"),
    )
    return row["id"] if row else -1


async def get_relationships(person_id: int) -> List[Dict]:
    db = await pool()
    rows = await db.fetch(
        "SELECT * FROM relationships WHERE from_id=$1 OR to_id=$1 ORDER BY rel_type",
        person_id
    )
    return [dict(r) for r in rows]


# ── News ───────────────────────────────────────────────────────────────────────

async def upsert_news(a: Dict) -> int:
    db = await pool()
    sql = """
        INSERT INTO news_articles
            (url, title, summary, full_text, outlet, published_at, category, sentiment, credibility)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ON CONFLICT (url) DO UPDATE SET
            title       = EXCLUDED.title,
            summary     = COALESCE(EXCLUDED.summary, news_articles.summary),
            category    = COALESCE(EXCLUDED.category, news_articles.category),
            sentiment   = COALESCE(EXCLUDED.sentiment, news_articles.sentiment)
        RETURNING id
    """
    row = await db.fetchrow(sql,
        a["url"], a["title"], a.get("summary"), a.get("full_text"),
        a.get("outlet"), a.get("published_at"), a.get("category", "other"),
        a.get("sentiment", "neutral"), a.get("credibility", 0.7)
    )
    return row["id"]


async def link_person_news(person_id: int, news_id: int, alignment: float = 0.0, mention_type: str = "mentioned"):
    db = await pool()
    await db.execute(
        """INSERT INTO person_news (person_id, news_id, alignment_score, mention_type)
           VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING""",
        person_id, news_id, alignment, mention_type
    )


async def get_person_news(person_id: int, limit: int = 30) -> List[Dict]:
    db = await pool()
    rows = await db.fetch("""
        SELECT na.*, pn.alignment_score, pn.mention_type
        FROM news_articles na
        JOIN person_news pn ON pn.news_id = na.id
        WHERE pn.person_id = $1
        ORDER BY na.published_at DESC NULLS LAST, na.id DESC
        LIMIT $2
    """, person_id, limit)
    return [dict(r) for r in rows]


# ── Jobs ───────────────────────────────────────────────────────────────────────

async def create_job(job_type: str, target: str, total: int = 0) -> int:
    db = await pool()
    row = await db.fetchrow(
        "INSERT INTO crawl_jobs (job_type, target, total) VALUES ($1,$2,$3) RETURNING id",
        job_type, target, total
    )
    return row["id"]


async def update_job(job_id: int, status: str, progress: int = None,
                     summary: Dict = None, error: str = None):
    db = await pool()
    sets, vals = [], [job_id]
    def add(col, val):
        vals.append(val)
        sets.append(f"{col}=${len(vals)}")
    add("status", status)
    if progress is not None: add("progress", progress)
    if summary:              add("result_summary", json.dumps(summary, ensure_ascii=False))
    if error:                add("error_msg", error)
    if status == "running":  add("started_at", "NOW()")
    if status in ("done","failed","partial"): add("finished_at", "NOW()")
    await db.execute(
        f"UPDATE crawl_jobs SET {', '.join(sets)} WHERE id=$1",
        *vals
    )


async def get_jobs(limit: int = 20) -> List[Dict]:
    db = await pool()
    rows = await db.fetch(
        "SELECT * FROM crawl_jobs ORDER BY created_at DESC LIMIT $1", limit
    )
    return [dict(r) for r in rows]


async def log_source(entity_type: str, entity_id: int, name: str, url: str, status: int = 200):
    db = await pool()
    try:
        await db.execute(
            "INSERT INTO source_audit (entity_type, entity_id, source_name, source_url, http_status) VALUES ($1,$2,$3,$4,$5)",
            entity_type, entity_id, name, url, status
        )
    except Exception:
        pass


# ── Stats ──────────────────────────────────────────────────────────────────────

async def get_stats() -> Dict:
    db = await pool()
    total    = await db.fetchval("SELECT COUNT(*) FROM persons")
    by_role  = await db.fetch("SELECT role_type, COUNT(*) c FROM persons WHERE role_type IS NOT NULL GROUP BY role_type ORDER BY c DESC")
    by_party = await db.fetch("SELECT party, COUNT(*) c FROM persons WHERE party IS NOT NULL GROUP BY party ORDER BY c DESC")
    total_rels = await db.fetchval("SELECT COUNT(*) FROM relationships")
    total_news = await db.fetchval("SELECT COUNT(*) FROM news_articles")
    return {
        "total_persons":  total,
        "total_rels":     total_rels,
        "total_news":     total_news,
        "by_role":        {r["role_type"]: r["c"] for r in by_role},
        "by_party":       {r["party"]: r["c"] for r in by_party},
    }


async def truncate_crawl_data():
    """
    Wipe all crawled data for a fresh restart.
    Keeps schema intact, just deletes rows.
    """
    pool = await _pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM person_news")
            await conn.execute("DELETE FROM news_articles")
            await conn.execute("DELETE FROM relationships")
            await conn.execute("DELETE FROM persons")
            await conn.execute("DELETE FROM organisations")
            await conn.execute("UPDATE crawl_jobs SET status='archived' WHERE status IN ('running','done','failed')")
    logger.info("Crawl data wiped for fresh restart")


# ── Updates for Scheduler ──────────────────────────────────────────────────────

async def update_person_position(slug: str, new_position: str, source: str):
    """Update a person's position (for scheduler change detection)."""
    db = await pool()
    await db.execute(
        "UPDATE persons SET current_position = $1, updated_at = NOW() WHERE slug = $2",
        new_position, slug
    )
    logger.info(f"Updated position for {slug}: {new_position}")


async def update_person_party(slug: str, new_party: str, source: str):
    """Update a person's party affiliation (for scheduler change detection)."""
    db = await pool()
    await db.execute(
        "UPDATE persons SET party = $1, updated_at = NOW() WHERE slug = $2",
        new_party, slug
    )
    logger.info(f"Updated party for {slug}: {new_party}")
