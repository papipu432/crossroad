# CROSSROAD Architecture

## System Overview

CROSSROAD is a microservices-based political intelligence platform built for Indonesian context. The system autonomously discovers political figures, maps relationships, tracks wealth/business interests, monitors legal cases, and detects oligarchic patterns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   Web Dashboard  │  │   Mobile App     │  │   API Clients    │  │
│  │  (React + D3.js) │  │   (Future)       │  │  (curl, Python)  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTPS (TLS 1.3)
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Nginx Reverse Proxy                        │  │
│  │         • SSL Termination                                     │  │
│  │         • Rate Limiting                                       │  │
│  │         • Load Balancing                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Backend (Python 3.12)                    │  │
│  │                                                               │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │  │
│  │  │   REST API  │  │ GraphQL API │  │ WebSocket   │          │  │
│  │  │  Endpoints  │  │  (Future)   │  │  (SSE)      │          │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │  │
│  │                                                               │  │
│  │  Core Services:                                               │  │
│  │  • Agent Orchestrator  • Graph Manager  • Scheduler Engine   │  │
│  │  • Entity Resolver     • RAG Engine     • Auth Service       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  WORKER LAYER    │    │  ML SERVICE      │    │  IMAGE WORKER    │
│  ┌────────────┐  │    │  ┌────────────┐  │    │  ┌────────────┐  │
│  │  Celery    │  │    │  │ Prediction │  │    │  │   Celery   │  │
│  │  Workers   │  │    │  │   Models   │  │    │  │   Workers  │  │
│  │            │  │    │  │            │  │    │  │            │  │
│  │ • Scraping │  │    │  │ • Succession│  │    │  │ • OCR      │  │
│  │ • ETL      │  │    │  │ • Scandal   │  │    │  │ • Face Rec │  │
│  │ • Vectorize│  │    │  │ • Bot Det   │  │    │  │ • PDF Parse│  │
│  └────────────┘  │    │  └────────────┘  │    │  └────────────┘  │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Neo4j 5.23 │  │  ChromaDB    │  │  InfluxDB    │             │
│  │  Graph DB    │  │  Vector DB   │  │  Time-Series │             │
│  │              │  │              │  │              │             │
│  │ • Persons    │  │ • Documents  │  │ • Budget     │             │
│  │ • Companies  │  │ • Embeddings │  │   Trends     │             │
│  │ • Relations  │  │ • Semantic   │  │ • Wealth     │             │
│  │ • Cases      │  │   Search     │  │   History    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  PostgreSQL  │  │    Redis 7   │  │    MinIO     │             │
│  │  Relational  │  │    Cache     │  │  Object Store│             │
│  │              │  │              │  │              │             │
│  │ • Users      │  │ • Sessions   │  │ • LHKPN PDFs │             │
│  │ • Audit Log  │  │ • Task Queue │  │ • Images     │             │
│  │ • Config     │  │ • Rate Limit │  │ • Documents  │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   EXTERNAL DATA SOURCES                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │Wikipedia│ │  KPU   │ │ LHKPN  │ │  KPK   │ │  AHU   │          │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘          │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │  LPSE  │ │  JDIH  │ │  SIPP  │ │PDDIKTI │ │Social  │          │
│  │        │ │        │ │        │ │        │ │ Media  │          │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘          │
│  ┌────────┐ ┌────────┐ ┌────────┐                                │
│  │ News   │ │ Meta   │ │ TikTok │                                │
│  │ Outlets│ │ Ads    │ │ Ads    │                                │
│  └────────┘ └────────┘ └────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Frontend (React 18 + D3.js)

**Location**: `/frontend`

**Technologies**:
- React 18 with TypeScript
- D3.js v7 for force-directed graphs
- Tailwind CSS for styling
- React Query for data fetching
- Socket.io client for real-time updates

**Key Components**:
- `GraphExplorer`: Interactive network visualization
- `PersonProfile`: Detailed politician dossier
- `DynastyMap`: Family tree visualization
- `BudgetFlow`: APBD money flow Sankey diagram
- `NaturalQuery`: NLQ interface with RAG

### 2. Backend (FastAPI)

**Location**: `/backend`

**Technologies**:
- Python 3.12 with async/await
- FastAPI for REST API
- Pydantic v2 for data validation
- SQLAlchemy 2.0 for ORM
- Neo4j Driver for graph operations

**Core Modules**:

#### Agent Orchestrator
```python
# 4-phase autonomous mining
Phase 1: Discovery (seed → Wikipedia → new entities)
Phase 2: Profiling (scrape bio, positions, family)
Phase 3: News Mining (extract relationships from articles)
Phase 4: Vectorization (embed documents for RAG)
```

#### Graph Manager
- Cypher query builder
- Relationship inference engine
- Temporal edge tracking
- Evidence provenance

#### Scheduler Engine
- APScheduler for cron jobs
- Task prioritization queue
- Progress tracking with Redis
- Pause/resume capabilities

### 3. Crawler Module

**Location**: `/backend/crawler`

**Sources**:

| Source | Type | Data Extracted |
|--------|------|----------------|
| Wikipedia | Graph | Bio, positions, family, links |
| KPU | Government | Candidates, votes, parties |
| LHKPN | Government | Asset declarations, wealth |
| KPK | Government | Corruption cases, suspects |
| AHU | Government | Company ownership, directors |
| LPSE | Government | Tenders, contracts, vendors |
| JDIH | Government | Regulations, decrees |
| SIPP | Judiciary | Court cases, verdicts |
| PDDIKTI | Education | Academic positions, grants |
| News Outlets | Media | Relationships, events |
| Meta Ads | Social | Political ad spenders |
| TikTok Ads | Social | Campaign financing |

**Scraper Features**:
- Rotating user agents
- Request rate limiting
- Retry with exponential backoff
- JavaScript rendering (Playwright)
- CAPTCHA detection

### 4. ML Service

**Location**: `/backend/ml_service`

**Models**:

#### Succession Prediction
- Input: Position history, age, party loyalty, network centrality
- Output: Probability of becoming successor (0.0-1.0)
- Algorithm: Gradient Boosting Classifier

#### Scandal Risk Forecasting
- Input: Business conflicts, legal history, sentiment trends
- Output: Risk score (LOW/MEDIUM/HIGH/CRITICAL)
- Algorithm: Random Forest + SHAP explainability

#### Bot Detection
- Input: Tweet patterns, follower graphs, engagement ratios
- Output: Bot probability (0.0-1.0)
- Algorithm: Isolation Forest + Network Analysis

#### Coalition Stability
- Input: Historical alliances, ideology scores, election results
- Output: Stability index (0.0-1.0)
- Algorithm: Time-series forecasting (Prophet)

### 5. Image Worker

**Location**: `/backend/image_worker`

**Capabilities**:

#### OCR Pipeline
- Tesseract for text extraction
- Layout analysis for LHKPN forms
- Table structure recognition
- Confidence scoring

#### Face Recognition
- InsightFace for embedding generation
- Politician database matching
- Group photo analysis
- Co-occurrence network building

#### Document Processing
- PDF parsing (LHKPN reports)
- Image enhancement
- Watermark removal
- Metadata extraction

### 6. Database Layer

#### Neo4j (Graph Database)

**Schema**:
```cypher
// Nodes
(:Person {slug, name, birth_date, positions[]})
(:Company {npwb, name, capital, sector})
(:Position {title, institution, start_date, end_date})
(:Party {name, coalition, ideology_score})
(:Case {id, type, status, verdict})
(:Budget {region, year, amount, category})
(:Document {url, content, embedding, source})

// Relationships
(:Person)-[FAMILY_OF {type, evidence}]->(:Person)
(:Person)-[MEMBER_OF {start_date, end_date}]->(:Party)
(:Person)-[HOLDS_POSITION {dates}]->(:Position)
(:Person)-[OWNS_SHARES {percentage}]->(:Company)
(:Person)-[COMMISSIONER_OF]->(:Company)
(:Person)-[INDICTED_IN {role}]->(:Case)
(:Company)-[WON_TENDER {amount, date}]->(:Budget)
(:Person)-[MENTORED_BY]->(:Person)
(:Person)-[POLITICAL_ALLY]->(:Person)
```

**Indexes**:
- Person: `CREATE INDEX FOR (p:Person) ON (p.slug)`
- Company: `CREATE INDEX FOR (c:Company) ON (c.npwb)`
- Full-text: `CREATE FULLTEXT INDEX entityNames FOR (p:Person|c:Company) ON EACH [p.name, c.name]`

#### ChromaDB (Vector Database)

**Collections**:
- `documents`: News articles, biographies
- `lhkpn_reports`: Asset declaration texts
- `legal_cases`: Court documents
- `regulations`: JDIH legal texts

**Embedding Model**: `paraphrase-multilingual-MiniLM-L12-v2` (supports Indonesian)

#### InfluxDB (Time-Series)

**Measurements**:
- `wealth_history`: Asset values over time
- `budget_execution`: Monthly spending rates
- `sentiment_scores`: Daily media sentiment
- `relationship_strength`: Edge weight evolution

#### PostgreSQL (Relational)

**Tables**:
- `users`: Authentication and authorization
- `audit_log`: All data changes with timestamps
- `scheduler_tasks`: Task definitions and states
- `api_keys`: API token management

#### Redis (Cache & Queue)

**Use Cases**:
- Session storage (JWT blacklist)
- Rate limiting counters
- Celery task queue
- Real-time progress updates (SSE)

#### MinIO (Object Storage)

**Buckets**:
- `lhkpn-pdfs`: Original asset declaration PDFs
- `company-documents`: AHU registration files
- `legal-documents`: Court verdicts
- `profile-images`: Politician photos

## Data Flow

### 1. Autonomous Mining Flow

```
User triggers mining → Agent Orchestrator
    ↓
Phase 1: Discovery
    - Load seed entities
    - Query Wikipedia API
    - Extract linked entities
    - Create Person nodes
    ↓
Phase 2: Profiling
    - Scrape Wikipedia infoboxes
    - Extract positions, family
    - Query KPU for election data
    - Update Person properties
    ↓
Phase 3: News Mining
    - Fetch recent articles
    - NLP extraction (NER, RE)
    - Create relationships
    - Attach evidence URLs
    ↓
Phase 4: Vectorization
    - Generate embeddings
    - Store in ChromaDB
    - Link to entities
    ↓
Complete → Update dashboard
```

### 2. Natural Language Query Flow

```
User asks: "Siapa anggota DPR yang punya perusahaan tambang?"
    ↓
FastAPI receives query
    ↓
RAG Engine
    - Encode query to embedding
    - Search ChromaDB for relevant docs
    - Retrieve context
    ↓
LLM (Ollama qwen2.5:7b)
    - Translate NL to Cypher
    - Validate query safety
    ↓
Neo4j executes Cypher
    ↓
Results formatted as JSON
    ↓
Return to user with sources
```

### 3. Oligarchy Detection Flow

```
Scheduler triggers scan
    ↓
Load all politicians with positions
    ↓
For each person:
    - Query business ownership (AHU)
    - Calculate wealth concentration
    - Detect self-dealing loops
    - Score monopoly control
    ↓
Compute oligarchy score (0.0-1.0)
    ↓
If score > 0.7:
    - Flag as CRITICAL
    - Generate alert
    - Create investigation dossier
    ↓
Store results in Neo4j
    ↓
Update dashboard alerts
```

### 4. APBD Fraud Detection Flow

```
Weekly scheduler task
    ↓
Fetch APBD data from SIPD/OpenSP2D
    ↓
ETL Pipeline:
    - Parse budget lines
    - Normalize categories
    - Link to regions
    ↓
Fraud Detection Algorithms:
    - Ghost project detection
    - Price inflation analysis
    - Vendor concentration
    - Related-party transactions
    ↓
Create (:Budget) nodes
Create (:Company)-[WON_TENDER]->(:Budget) edges
    ↓
Flag anomalies with risk scores
    ↓
Generate audit report
```

## Security Architecture

### Authentication Flow
```
User login → Validate credentials → Generate JWT
    ↓
Store JWT in HTTP-only cookie
    ↓
Subsequent requests: Validate JWT signature
    ↓
Extract user roles from JWT claims
    ↓
Authorize based on RBAC policies
```

### Data Privacy
- PII encryption at rest (AES-256)
- TLS 1.3 for data in transit
- Access logging for compliance
- Data retention policies (auto-delete after 5 years)
- Compliance with UU 27/2022 (Indonesian PDP Law)

### Rate Limiting
- API: 100 requests/minute per user
- Scrapers: 1 request/second per domain
- LLM: 10 queries/minute per user

## Deployment Architecture

### Production Setup
```
┌─────────────────────────────────────────┐
│           Load Balancer (Nginx)         │
└─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│  Backend Node 1  │   │  Backend Node 2  │
│  (FastAPI + Gunicorn) │  (FastAPI + Gunicorn) │
└──────────────────┘   └──────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
        ┌───────────┴───────────┬───────────┐
        ▼                       ▼           ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Neo4j Cluster  │   │  PostgreSQL HA   │   │   Redis Cluster  │
│  (3 nodes, Causal│   │  (Primary +      │   │  (Sentinel mode) │
│   Clustering)    │   │   Replica)       │   │                  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
```

### Docker Compose Services
- `backend`: FastAPI application
- `frontend`: React SPA (Nginx)
- `neo4j`: Graph database
- `chromadb`: Vector database
- `influxdb`: Time-series database
- `postgres`: Relational database
- `redis`: Cache and queue
- `minio`: Object storage
- `ml-service`: Prediction models
- `image-worker`: OCR and face recognition
- `celery-worker`: Background tasks

## Performance Considerations

### Caching Strategy
- L1: Redis cache for frequent queries (TTL: 5 minutes)
- L2: Application-level cache for expensive computations (TTL: 1 hour)
- L3: Database query result cache (TTL: 24 hours)

### Indexing Strategy
- Neo4j: Node property indexes for all lookup fields
- ChromaDB: HNSW index for approximate nearest neighbor search
- PostgreSQL: B-tree indexes on foreign keys and frequently queried columns

### Scalability
- Horizontal scaling: Add more backend nodes behind load balancer
- Database sharding: Partition Neo4j by region for large datasets
- CDN: Serve static assets via CloudFront/Akamai

## Monitoring & Observability

### Metrics Collection
- Prometheus: Application metrics (request latency, error rates)
- Grafana: Dashboards for visualization
- Neo4j Metrics: Query performance, memory usage

### Logging
- Structured logging with JSON format
- Log aggregation via ELK stack (Elasticsearch, Logstash, Kibana)
- Correlation IDs for request tracing

### Alerting
- PagerDuty integration for critical alerts
- Slack notifications for warnings
- Email digests for daily summaries

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Maintainer**: CROSSROAD Team
