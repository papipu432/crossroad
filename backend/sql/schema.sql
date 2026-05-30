-- ═══════════════════════════════════════════════════════════════════════════
-- CROSSROAD — Indonesian Political Knowledge Graph
-- PostgreSQL Schema
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Entity types ──────────────────────────────────────────────────────────────
-- person  : politician, family member, associate
-- org     : party, company, NGO, university, government body
-- event   : election, meeting, trial, appointment

-- ── Persons (politicians + associates + family) ───────────────────────────────
CREATE TABLE IF NOT EXISTS persons (
    id              SERIAL PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,          -- url-safe identifier
    full_name       TEXT NOT NULL,
    aliases         TEXT[],                         -- nicknames, alternative spellings
    photo_url       TEXT,
    born            TEXT,
    birthplace      TEXT,
    religion        TEXT,
    ethnicity       TEXT,
    gender          TEXT DEFAULT 'male',
    -- Political role
    role_type       TEXT,  -- dpr | dprd | menteri | gubernur | bupati | walikota | presiden | wapres
    current_position TEXT,
    party           TEXT,
    faction         TEXT,
    dapil           TEXT,  -- electoral district
    province        TEXT,
    -- Biography
    bio             TEXT,
    education       JSONB DEFAULT '[]',   -- [{year, institution, degree, city}]
    career          JSONB DEFAULT '[]',   -- [{year_start, year_end, org, title}]
    companies       JSONB DEFAULT '[]',   -- [{name, role, industry, founded}]
    awards          JSONB DEFAULT '[]',
    -- Crawl metadata
    wiki_url_id     TEXT,   -- id.wikipedia.org URL
    wiki_url_en     TEXT,   -- en.wikipedia.org URL
    sources         JSONB DEFAULT '[]',   -- [{name, url, scraped_at}]
    crawl_depth     INT DEFAULT 0,        -- 0=seed, 1=family, 2=associate
    crawled_at      TIMESTAMPTZ,
    enriched_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Organisations (parties, companies, universities, govt bodies) ──────────────
CREATE TABLE IF NOT EXISTS organisations (
    id              SERIAL PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    short_name      TEXT,
    org_type        TEXT,  -- party | company | university | ngo | govt | military
    description     TEXT,
    founded         TEXT,
    dissolved       TEXT,
    website         TEXT,
    logo_url        TEXT,
    sources         JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Relationships (the heart of Crossroad) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS relationships (
    id              SERIAL PRIMARY KEY,
    from_id         INT NOT NULL,          -- person.id
    from_type       TEXT DEFAULT 'person', -- person | org
    to_id           INT NOT NULL,
    to_type         TEXT DEFAULT 'person', -- person | org
    rel_type        TEXT NOT NULL,
    -- rel_type values:
    --   FAMILY_OF (+ subtype: spouse, child, parent, sibling, relative, in-law)
    --   MEMBER_OF  (party membership)
    --   WORKS_AT   (current/past position)
    --   STUDIED_AT
    --   OWNS       (company ownership)
    --   ALLIED_WITH
    --   RIVAL_OF
    --   MET_AT     (documented meeting)
    --   APPOINTED_BY
    --   INVESTIGATED_BY
    subtype         TEXT,                  -- e.g. 'spouse', 'child', 'director'
    label           TEXT,                  -- human-readable edge label
    year_start      TEXT,
    year_end        TEXT,
    is_current      BOOLEAN DEFAULT TRUE,
    weight          FLOAT DEFAULT 1.0,     -- relationship strength
    sources         JSONB DEFAULT '[]',    -- [{name, url}]
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── News articles ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS news_articles (
    id              SERIAL PRIMARY KEY,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    summary         TEXT,
    full_text       TEXT,
    outlet          TEXT,               -- Tempo, Kompas, Detik, etc.
    published_at    TEXT,
    category        TEXT,               -- corruption | policy | election | family | business | statement | legal | other
    sentiment       TEXT DEFAULT 'neutral',
    credibility     FLOAT DEFAULT 0.7,  -- source credibility score
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Person ↔ News mentions ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS person_news (
    person_id       INT REFERENCES persons(id) ON DELETE CASCADE,
    news_id         INT REFERENCES news_articles(id) ON DELETE CASCADE,
    alignment_score FLOAT DEFAULT 0.0,  -- -1 to +1: against↔party-aligned
    mention_type    TEXT DEFAULT 'mentioned', -- subject | mentioned | quoted
    PRIMARY KEY (person_id, news_id)
);

-- ── Crawler jobs ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id              SERIAL PRIMARY KEY,
    job_type        TEXT NOT NULL,  -- bulk_seed | enrich_person | crawl_news | crawl_family | crawl_companies
    target          TEXT,           -- person slug or category name
    status          TEXT DEFAULT 'pending',  -- pending | running | done | failed | partial
    progress        INT DEFAULT 0,
    total           INT DEFAULT 0,
    result_summary  JSONB,
    error_msg       TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Source audit trail ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_audit (
    id              SERIAL PRIMARY KEY,
    entity_type     TEXT,   -- person | org | news | relationship
    entity_id       INT,
    source_name     TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TIMESTAMPTZ DEFAULT NOW(),
    http_status     INT,
    notes           TEXT
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_persons_role_type  ON persons(role_type);
CREATE INDEX IF NOT EXISTS idx_persons_party      ON persons(party);
CREATE INDEX IF NOT EXISTS idx_persons_province   ON persons(province);
CREATE INDEX IF NOT EXISTS idx_persons_slug       ON persons(slug);
CREATE INDEX IF NOT EXISTS idx_persons_name       ON persons USING gin(to_tsvector('simple', full_name));
CREATE INDEX IF NOT EXISTS idx_rels_from          ON relationships(from_id, from_type);
CREATE INDEX IF NOT EXISTS idx_rels_to            ON relationships(to_id, to_type);
CREATE INDEX IF NOT EXISTS idx_rels_type          ON relationships(rel_type);
CREATE INDEX IF NOT EXISTS idx_news_outlet        ON news_articles(outlet);
CREATE INDEX IF NOT EXISTS idx_news_category      ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_jobs_status        ON crawl_jobs(status);
CREATE INDEX IF NOT EXISTS idx_orgs_type          ON organisations(org_type);

-- ── updated_at trigger ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER persons_updated_at
    BEFORE UPDATE ON persons FOR EACH ROW EXECUTE FUNCTION set_updated_at();
