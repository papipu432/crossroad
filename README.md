# CROSSROAD 🇮🇩
### Autonomous Indonesian Political Knowledge Graph

A 24-hour autonomous deep-mining platform that crawls all Indonesian officials, builds a rich knowledge graph of their relationships, and lets you query it in natural language.

---

## What It Mines

For every person (DPR, DPRD, Menteri, Gubernur, Bupati, Walikota):

| Layer | Data |
|---|---|
| **Profile** | Bio, born, birthplace, religion, ethnicity |
| **Education** | Institutions, degrees, years → classmate links |
| **Career** | Every position, years, organization |
| **Family** | Spouse, children, parents, siblings |
| **Companies** | Businesses owned or led |
| **Party/Faction** | Current + historical membership |
| **News** | 8 Indonesian outlets, scored for faction bias |
| **Relationships** | All above as Neo4j edges |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React Frontend · D3 Force Graph · Space Mono + Outfit       │
│  AgentDashboard (SSE live) · QueryPanel (RAG + Cypher)       │
└──────────────────────┬───────────────────────────────────────┘
                       │ REST + SSE
┌──────────────────────▼───────────────────────────────────────┐
│  FastAPI Backend                                              │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Master Agent (24h autonomous run)                      │ │
│  │  Phase 0: Discovery → Wikipedia lists + gov sites       │ │
│  │  Phase 1: L1 agents (×5) → profile per person           │ │
│  │  Phase 2: L2 agents (×3) → family/edu/career/companies  │ │
│  │  Phase 3: L3 agents (×2) → news + faction scoring      │ │
│  │  Phase 4: Vectorize → ChromaDB embeddings               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌─────────────┐  │
│  │  Wiki    │ │  News    │ │  Ollama    │ │  Discovery  │  │
│  │ Scraper  │ │ Crawler  │ │  Enricher  │ │  Crawler    │  │
│  │ (ID+EN)  │ │ (8 sites)│ │ (qwen2.5) │ │  (Wiki lists│  │
│  └──────────┘ └──────────┘ └────────────┘ └─────────────┘  │
└──────┬──────────────┬────────────────┬──────────────────────┘
       │              │                │
 ┌─────▼───┐  ┌───────▼──┐  ┌────────▼────┐  ┌──────────┐
 │  Neo4j  │  │PostgreSQL│  │   Redis     │  │ ChromaDB │
 │  Graph  │  │ Entities │  │ Cache + SSE │  │ Vectors  │
 └─────────┘  └──────────┘  └─────────────┘  └──────────┘
                                                  ▲
                                          ┌───────┴──────┐
                                          │    Ollama    │
                                          │  qwen2.5:7b  │
                                          │  (local LLM) │
                                          └──────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- ~10 GB RAM (Neo4j 3GB + Ollama model 5GB + rest)
- ~15 GB disk (model + databases)

### 1. Configure
```bash
cp .env.example .env
# Edit passwords if needed. Defaults work fine for local use.
```

### 2. Start services
```bash
docker compose up -d
```
First run downloads `qwen2.5:7b` (~4.7 GB). Wait ~5 minutes.

### 3. Open the app
| Service | URL |
|---|---|
| **Crossroad UI** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **Neo4j Browser** | http://localhost:7474 |
| **ChromaDB** | http://localhost:8001 |

---

## Running the 24-Hour Mine

### Option A — Manual start from UI
1. Open http://localhost:3000
2. Click **⚡ Agent** → set discovery limits → **▶ Start 24h Mining Run**
3. Watch the live progress dashboard

### Option B — Auto-start on boot
```bash
# In .env:
AUTO_START_CRAWLER=true
docker compose up -d
```

### Recommended limits for first 24h run
```
DPR:          100  (of 575 seats)
Menteri:       50  (full cabinet)
Gubernur:      40  (all provinces)
Bupati/Wali:  150  (sample of 514)
DPRD:         100  (provincial leaders)
──────────────────
Total:        ~440 persons × 3 phases
Est. time:    ~6-8 hours
```

For a full run (all 2,000+ officials), increase limits and allow 24 hours.

---

## Agent Phases

```
Phase 0 · DISCOVERY        (15-30 min)
  └─ Crawls Wikipedia list pages for DPR, Menteri, Gubernur,
     Bupati/Walikota, DPRD. Extracts names, parties, regions.
     Falls back to curated seed list if crawl fails.

Phase 1 · PROFILE  L1 (×5 parallel)   (~2-4 hours)
  └─ Per person: Wikipedia ID + EN scrape → extract bio,
     infobox, education, career, companies, family raw data.
     → Ollama fills gaps (born, religion, faction, dapil).
     → Writes to PostgreSQL + Neo4j (skeleton nodes + MEMBER_OF).

Phase 2 · DEEP-DIVE  L2 (×3 parallel)  (~3-6 hours)
  └─ Per person: Re-scrape for family details → Ollama completes
     family list → upsert family members + FAMILY_OF edges.
     → Education → STUDIED_AT edges (classmate detection).
     → Career → WORKS_AT edges.
     → Companies → OWNS edges.
     → LLM extracts additional relationship edges from context.

Phase 3 · NEWS  L3 (×2 parallel)       (~4-8 hours)
  └─ Per person: Crawls 8 outlets (Tempo, Kompas, Detik,
     CNN Indonesia, Antara, Republika, Tribun, JPNN).
     → Ollama scores each article:
       alignment_score: -1.0 (opposing faction) to +1.0 (same faction)
       sentiment: positive | negative | neutral
     → Writes to PostgreSQL + Neo4j (MENTIONED_IN edges).

Phase 4 · VECTORIZE                     (~30 min)
  └─ Embeds all person bios + news into ChromaDB
     using multilingual sentence-transformers.
     Enables semantic search and RAG queries.
```

---

## Knowledge Query Interface

Open **🧠 Query** in the UI. Three modes:

### AUTO (default)
Automatically picks the best mode for your question.

### RAG mode
Semantic search over ChromaDB, then Ollama summarizes.
Good for: broad questions, trends, summaries.

```
"Bagaimana latar belakang pendidikan politisi dari Gerindra?"
→ Searches ChromaDB for relevant bios
→ Ollama synthesizes an answer with sources
```

### Cypher mode
Translates your question into Neo4j Cypher, runs it, then explains.
Good for: specific facts, counts, relationship traversal.

```
"Siapa istri Prabowo Subianto?"
→ MATCH (p:Person {slug:'prabowo-subianto'})-[r:FAMILY_OF {subtype:'spouse'}]->(f)
  RETURN f.name

"Siapa yang bersekolah di tempat yang sama dengan Joko Widodo?"
→ MATCH (p:Person {slug:'joko-widodo'})-[:STUDIED_AT]->(u)<-[:STUDIED_AT]-(other)
  RETURN DISTINCT other.name, u.name LIMIT 20
```

---

## News Faction Bias Scoring

Every news article gets two scores from Ollama:

| Score | Meaning |
|---|---|
| **+1.0** | Strongly aligns with person's party narrative |
| **0.0** | Neutral / factual reporting |
| **-1.0** | From opposing faction, critical coverage |

Displayed in the news panel with color-coded bars:
- 🟢 Green = Aligned (pro-party source)
- 🟡 Yellow = Neutral
- 🔴 Red = Critical (opposing faction)

---

## Graph Edge Types

| Edge | Meaning |
|---|---|
| `FAMILY_OF` + subtype | spouse, child, parent, sibling… |
| `MEMBER_OF` | Party membership |
| `WORKS_AT` | Government position or employer |
| `STUDIED_AT` | University / school (enables classmate detection) |
| `OWNS` | Company ownership |
| `ALLIED_WITH` | Political alliance |
| `RIVAL_OF` | Political rivalry |
| `APPOINTED_BY` | Appointment chain |
| `MENTIONED_IN` | Person ↔ news article |

---

## Data Sources

**Profiles & Family**
- Wikipedia Indonesia `id.wikipedia.org`
- Wikipedia English `en.wikipedia.org`

**Official Lists**
- DPR RI `dpr.go.id`
- Sekretariat Kabinet `setneg.go.id`
- Kemendagri `kemendagri.go.id`
- Wikipedia list pages (governors, bupati, ministers)

**News**
- Tempo · Kompas · Detik · CNN Indonesia
- Antara · Republika · Tribun · JPNN

**LLM** — Ollama `qwen2.5:7b` (local, free, no API key ever)

---

## API Reference

```
GET  /health                           Service status
GET  /api/stats                        Database statistics

# Agent control
POST /api/agent/start                  Start autonomous mining run
POST /api/agent/stop                   Stop the agent
POST /api/agent/pause                  Pause
POST /api/agent/resume                 Resume
GET  /api/agent/status                 Current agent state
GET  /api/agent/stream                 SSE: live progress stream

# Persons
GET  /api/persons?role_type=dpr&party=PDIP   Filtered list
GET  /api/persons/search?q=Prabowo           Full-text search
GET  /api/persons/{slug}                     Full profile
GET  /api/persons/{slug}/news                News with bias scores
GET  /api/persons/{slug}/relations           All relationships

# Graph
GET  /api/graph/ego/{slug}?depth=2    Ego network (1-3 hops)
GET  /api/graph/full?limit=500        Full knowledge graph
POST /api/graph/path                  Shortest path between two people

# Query
POST /api/query                       NL question → RAG or Cypher answer
GET  /api/query/vector-search?q=      Direct semantic search

GET  /api/jobs                        Crawler job history
```

---

## Environment Variables

See `.env.example` for full reference. Key settings:

```env
AUTO_START_CRAWLER=false    # Set true to auto-mine on startup
DISCOVER_LIMIT_DPR=100      # How many DPR members to discover
CRAWL_DELAY_SECONDS=1.5     # Politeness delay between requests
AGENT_L1_CONCURRENCY=5      # Parallel profile agents
AGENT_L2_CONCURRENCY=3      # Parallel deep-dive agents
AGENT_L3_CONCURRENCY=2      # Parallel news agents
OLLAMA_MODEL=qwen2.5:7b     # Local LLM model
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + D3 v7 + Vite |
| Fonts | Space Mono + Outfit |
| State | React hooks + SSE (EventSource) |
| Backend | Python 3.12 + FastAPI |
| Scraping | httpx + BeautifulSoup4 + lxml |
| LLM | Ollama qwen2.5:7b — local, no API key |
| Knowledge Graph | Neo4j 5.23 Community + APOC |
| Relational DB | PostgreSQL 16 |
| Vector DB | ChromaDB + paraphrase-multilingual-MiniLM |
| Cache + PubSub | Redis 7 |
| Containerization | Docker Compose |
