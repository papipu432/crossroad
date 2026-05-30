# CROSSROAD: Indonesian Political Intelligence Platform

> **Advanced knowledge graph for tracking Indonesian political dynasties, oligarchy networks, and corruption patterns**

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/crossroad.git
cd crossroad

# Configure environment
cp .env.example .env
# Edit .env with your API keys and settings

# Deploy with Docker
docker compose up -d

# Access dashboard
open http://localhost:3000

# View API documentation
open http://localhost:8000/docs
```

## 🎯 What is CROSSROAD?

CROSSROAD is a comprehensive political intelligence platform designed specifically for Indonesian context. It autonomously discovers political figures, maps their relationships, tracks wealth and business interests, monitors legal cases, and detects oligarchic patterns.

### Key Capabilities

- **🕵️ Autonomous Discovery**: 4-phase mining (discovery → profile → news → vectorize)
- **🏛️ Dynasty Detection**: Identifies political families using surname clustering and relationship mapping
- **💰 Wealth Tracking**: LHKPN asset declarations with anomaly detection
- **🏢 Business Networks**: Company ownership, board positions, beneficial ownership
- **⚖️ Legal Monitoring**: SIPP court cases, KPK corruption cases, suspect tracking
- **🗳️ Election Data**: KPU candidate lists, vote counts, party structures
- **📊 APBD Tracking**: Regional budget flow analysis with fraud detection
- **📰 Media Monitoring**: 8 Indonesian news sources with bias scoring
- **🤖 ML Predictions**: Succession probability, coalition stability, scandal risk
- **🖼️ Image Processing**: OCR for LHKPN PDFs, face recognition

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React + D3.js)                │
│                  Interactive Graph Visualization            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Python 3.12)            │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ Crawler  │ Graph DB │ Scheduler│   ML     │  Image   │  │
│  │ Module   │ Manager  │  Engine  │ Service  │ Worker   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Neo4j 5.23 │    │  ChromaDB    │    │  InfluxDB    │
│  Graph Database│   │ Vector DB    │    │ Time-Series  │
└──────────────┘    └──────────────┘    └──────────────┘
        ▲                     ▲                     ▲
        │                     │                     │
┌─────────────────────────────────────────────────────────────┐
│                    Data Sources (Indonesia)                 │
│  Wikipedia │ KPU │ LHKPN │ KPK │ AHU │ LPSE │ JDIH │ SIPP │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI (Python 3.12) | REST API, async processing |
| **Frontend** | React 18 + D3.js | Interactive graph visualization |
| **Graph DB** | Neo4j 5.23 | Relationship mapping, Cypher queries |
| **Vector DB** | ChromaDB | Semantic search, RAG |
| **Time-Series** | InfluxDB | Budget trends, wealth history |
| **Cache** | Redis 7 | Session management, SSE streaming |
| **ML Service** | Python + scikit-learn | Prediction models, bot detection |
| **Image Worker** | Celery + Tesseract | OCR, face recognition |
| **Storage** | MinIO | Document storage (LHKPN PDFs) |

## 📁 Project Structure

```
crossroad/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── db.py                   # PostgreSQL connection
│   ├── graph.py                # Neo4j operations
│   ├── scheduler.py            # Scheduled tasks engine
│   ├── crawler/
│   │   ├── base.py             # Base scraper class
│   │   ├── wikipedia.py        # Wikipedia graph crawler
│   │   ├── news.py             # News outlet scrapers
│   │   ├── enhanced_sources.py # KPU, LHKPN, KPK, AHU
│   │   ├── business_registry.py# Company ownership detection
│   │   ├── apbd_tracker.py     # APBD budget tracking
│   │   ├── legal_scraper.py    # SIPP, JDIH, LPSE
│   │   └── social_media.py     # Meta/TikTok ad libraries
│   ├── ml_service/
│   │   ├── prediction.py       # Succession/scandal models
│   │   └── bot_detection.py    # Social media bot analysis
│   ├── image_worker/
│   │   ├── ocr.py              # LHKPN PDF parsing
│   │   └── face_recognition.py # Politician identification
│   └── tests/
│       └── test_masud_dynasty.py # Dynasty detection tests
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── hooks/              # Custom hooks
│   │   └── utils/              # Helper functions
│   └── public/
├── docs/                       # Documentation (this folder)
├── docker-compose.yml          # Container orchestration
└── .env.example                # Environment template
```

## 🎯 Key Features

### 1. Oligarchy Detection

Automatically identifies self-dealing loops and monopoly patterns:

```python
# Example: "Harum Resort" scheme detection
Governor Rudy Mas'ud 
    ↓ OWNS
PT Harum Resort 
    ↓ EXCLUSIVE_MANDATE
All government banquets MUST use this venue
    = CRITICAL CONFLICT (Score: 0.95)
```

**Oligarchy Score Components:**
- Wealth Concentration (companies owned)
- Political Power (position level)
- Business Density (companies per person)
- Conflict Severity (self-dealing schemes)
- Monopoly Control (exclusive mandates)

### 2. APBD Money Flow Tracking

Tracks regional budget from submission to execution:

```bash
GET /api/apbd/{region}/flow?year=2024
```

**Detects:**
- Ghost projects (budget allocated but no physical progress)
- Price inflation (unit costs > market rate)
- Vendor concentration (same company wins repeatedly)
- Related-party transactions (politician's company wins contracts)

### 3. Legal Case Lifecycle

Monitors entire justice process:

```
Investigation → Suspect → Defendant → Convicted → Imprisoned
```

**Sources:**
- KPK press releases
- SIPP court registry
- News media reports

### 4. Dynasty Network Mapping

Identifies political families through:

- Surname clustering algorithms
- Family relationship extraction
- Geographic power concentration
- Multi-generational position tracking

### 5. Natural Language Query

Ask complex questions in plain Indonesian:

```
"Siapa anggota DPR yang punya perusahaan tambang?"
"Tunjukkan semua kontrak APBD Kalimantan Timur dengan PT Mas'ud"
"Prediksi siapa pengganti Ganjar Pranowo sebagai Gubernur Jateng"
```

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design and data flow |
| [DATA_DICTIONARY.md](./DATA_DICTIONARY.md) | Database schema reference |
| [API_COOKBOOK.md](./API_COOKBOOK.md) | Practical API usage examples |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Development setup and contribution |
| [USER_GUIDE.md](./USER_GUIDE.md) | End-user manual |
| [OPERATIONS_RUNBOOK.md](./OPERATIONS_RUNBOOK.md) | Production deployment guide |
| [SECURITY.md](./SECURITY.md) | Security policies and practices |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | Common issues and solutions |
| [HOWTO.md](./HOWTO.md) | Step-by-step investigation tutorials |
| [WIKI.md](./WIKI.md) | Indonesian political domain knowledge |

## 🔌 API Endpoints

### Core Intelligence

```bash
POST   /api/agent/start                    # Start autonomous mining
GET    /api/person/{slug}                  # Person profile
GET    /api/person/{slug}/relationships    # Relationship network
GET    /api/person/{slug}/dossier          # Full intelligence dossier
```

### Business & Wealth

```bash
GET    /api/business/person/{slug}/portfolio  # Business portfolio
GET    /api/enhanced/lhkpn/{name}             # Asset declarations
GET    /api/oligarchy/{slug}/score            # Oligarchy risk score
POST   /api/business/scan/{slug}              # Trigger business scan
```

### Legal & Cases

```bash
GET    /api/legal/person/{slug}/cases         # All legal cases
GET    /api/legal/case/{id}                   # Case details
GET    /api/kpk/search?q=name                 # KPK corruption cases
```

### APBD & Procurement

```bash
GET    /api/apbd/{region}/flow                # Budget flow analysis
GET    /api/lpse/tenders                      # Government tenders
GET    /api/self-dealing/detect-loops         # Self-dealing detection
```

### Analytics

```bash
GET    /api/oligarchy/masud-dynasty           # Dynasty investigation
GET    /api/changes/recent?hours=24           # Change audit log
GET    /api/scheduler/status                  # Task schedule
POST   /api/oligarchy/scan-all                # Batch oligarchy scan
```

## 🗓️ Scheduled Tasks

| Frequency | Task | Description |
|-----------|------|-------------|
| **Daily** | News Updates | Scan top 100 politicians for new articles |
| **Daily** | Dynasty Recalculation | Update dynasty scores based on new relationships |
| **Weekly** | DPR Member Refresh | Update member list with change detection |
| **Weekly** | Wikipedia Deep Crawl | Recursive link-following for connected figures |
| **Weekly** | Business Portfolio Scan | Update company ownership data |
| **Monthly** | Party Structure Update | Refresh party/coalition hierarchies |
| **Monthly** | APBD Anomaly Audit | Comprehensive budget fraud detection |

## 🛡️ Security

- **Authentication**: JWT-based API authentication
- **Authorization**: Role-based access control (admin, analyst, viewer)
- **Data Privacy**: Compliance with Indonesian PDP Law (UU 27/2022)
- **Encryption**: TLS 1.3 for data in transit, AES-256 for data at rest
- **Audit Trail**: Complete logging of all data changes

See [SECURITY.md](./SECURITY.md) for detailed security policies.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) for development guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Data sources: Wikipedia, KPU, LHKPN, KPK, AHU, LPSE, JDIH, SIPP
- Inspired by Nemesis project (https://github.com/assai-id/nemesis)
- Built with ❤️ for Indonesian transparency and accountability

## 📞 Support

- **Documentation**: See `/docs` folder
- **Issues**: GitHub Issues tab
- **Email**: support@crossroad.id (placeholder)

---

**Version**: 2.0.0  
**Last Updated**: 2024  
**Status**: Production Ready ✅
