# CROSSROAD — Enhanced Indonesian Political Intelligence Platform

## 🚀 What's New in This Version

This enhanced version of CROSSROAD goes beyond the original Nemesis project with **Indonesia-specific intelligence features**:

### ✨ Major Additions

#### 1. **Daily Scheduled Scraping** (`scheduler.py`)
- **Automatic daily news updates** for all tracked politicians
- **Weekly DPR member list refresh** with change detection
- **Weekly deep Wikipedia crawls** for top connected figures
- **Daily dynasty recalculation** as new relationships discovered
- **Monthly party structure updates** tracking coalition shifts
- **Change audit trail** - tracks every position change, party switch, new relationship

#### 2. **Enhanced Data Sources** (`crawler/enhanced_sources.py`)
- **KPU Integration**: Election candidate lists, vote counts, party structures
- **LHKPN Asset Tracking**: Wealth declarations, detects suspicious growth (>100% = alert)
- **KPK Corruption Cases**: Tracks investigations, trials, verdicts with loss amounts
- **AHU Business Registry**: Links politicians to companies they own/control
- **Risk Scoring**: Automatic 0-1.0 risk score based on corruption cases + wealth anomalies

#### 3. **Dynamic Party/Coalition Updates**
- Automatically detects when MPs switch parties
- Tracks coalition realignments (KIM → KMP, etc.)
- Updates faction mappings in real-time
- Maintains historical party affiliation timeline

#### 4. **Better Relationship Detection**
- **Tim Sukses Detector**: Identifies campaign team members during elections
- **Dynasty Clustering v2**: Uses surname + geography + marriage patterns
- **Business Network Mapping**: Connects politicians through shared company ownership
- **Temporal Edges**: Relationships timestamped to track alliance evolution

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SCHEDULER (Daily Tasks)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Daily News   │  │ Weekly DPR   │  │ Dynasty      │      │
│  │ Update       │  │ Refresh      │  │ Recalc       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              ENHANCED DATA SOURCES                          │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                    │
│  │ KPU  │  │LHKPN │  │ KPK  │  │ AHU  │                    │
│  │Election│ │Assets│ │Cases │ │Biz   │                    │
│  └──────┘  └──────┘  └──────┘  └──────┘                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              KNOWLEDGE GRAPH (Neo4j)                        │
│  Persons ←→ Relationships ←→ Events ←→ Evidence            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              INTELLIGENCE LAYER                             │
│  Dynasty Detection | Coalition Mapping | Risk Scoring      │
└─────────────────────────────────────────────────────────────┘
```

## 🛠️ Setup & Configuration

### Enable Scheduler (Optional)
Add to your `.env` file:
```bash
ENABLE_SCHEDULER=true
AUTO_START_CRAWLER=false  # Set true for immediate full crawl
```

### Environment Variables
```bash
# Scheduler
ENABLE_SCHEDULER=true

# Crawler tuning
CRAWL_DELAY_SECONDS=1.5
AGENT_L1_CONCURRENCY=4
AGENT_L3_CONCURRENCY=2

# Source limits
DISCOVER_LIMIT_DPR=100
DISCOVER_LIMIT_MENTERI=50
DISCOVER_LIMIT_REGIONAL=150
```

## 📡 New API Endpoints

### Intelligence Dossier
```bash
GET /api/enhanced/person/{slug}/dossier
```
Returns comprehensive profile with assets, corruption cases, business interests, risk score.

### KPU Election Data
```bash
GET /api/enhanced/kpu/candidates?level=nasional
```
Get official candidate lists from 2024 elections.

### LHKPN Asset Search
```bash
GET /api/enhanced/lhkpn/{name}
```
Search politician asset declarations, detect wealth anomalies.

### KPK Case Search
```bash
GET /api/enhanced/kpk/search?q=nama_politisi
```
Find corruption cases involving specific politicians.

### Scheduler Status
```bash
GET /api/scheduler/status
```
View upcoming scheduled tasks and last run times.

### Change Audit Log
```bash
GET /api/changes/recent?hours=24
```
See all detected changes in last N hours (position switches, new relationships).

## 🔍 Key Features Explained

### 1. Dynamic Party Updates
The system now **automatically detects** when politicians change parties by:
- Weekly re-scraping of DPR official list
- Comparing current DB state vs fresh data
- Creating `party_switched` change records with timestamps
- Updating Neo4j graph edges automatically

Example detected change:
```json
{
  "entity_type": "person",
  "entity_id": "ahmad-syaikhu",
  "change_type": "party_switched",
  "old_value": {"party": "PKS"},
  "new_value": {"party": "Gerindra"},
  "source": "DPR Update",
  "timestamp": "2025-01-15T08:30:00Z"
}
```

### 2. Wealth Anomaly Detection
LHKPN crawler compares multiple years of asset declarations:
- **Normal**: <50% growth over term
- **Suspicious**: >100% growth without promotion
- **Critical**: >300% growth → triggers investigation flag

### 3. Dynasty Detection Improvements
New algorithm considers:
- Surname clustering (Mas'ud, Soeharto, Yudhoyono)
- Geographic concentration (same province/dapil)
- Marriage links (istri/suami relationships)
- Cross-party dynasties (family in multiple parties)

Output example:
```json
{
  "family_name": "Mas'ud",
  "dynasty_score": 9.1,
  "dynasty_type": "regional_dominant",
  "active_positions": 7,
  "govt_levels": ["provinsi", "lokal"],
  "dominant_party": "Golkar",
  "regions": ["Kalimantan Timur"]
}
```

### 4. Tim Sukses (Campaign Team) Detection
During election periods, system identifies:
- Campaign managers linked to candidates
- Volunteer coordinators
- Family members in campaign roles
- Post-election appointments (quid pro quo tracking)

## 🗓️ Default Schedule

| Task | Frequency | Description |
|------|-----------|-------------|
| Daily News Update | Every 24h | Fresh articles for top 100 politicians |
| Weekly DPR Refresh | Every 168h | Position/party change detection |
| Weekly Wiki Deep Crawl | Every 168h | Re-mine top 50 connected persons |
| Daily Dynasty Recalc | Every 24h | Update dynasty clusters |
| Monthly Party Structure | Every 720h | Coalition/faction updates |

## ⚠️ Important Notes

### Rate Limiting
- KPU: 2 second delay between requests
- LHKPN: 3 second delay (authenticated sessions)
- KPK: 2 second delay
- AHU: 3 second delay

### Legal Compliance
All data sourced from:
- ✅ Public government websites (kpu.go.id, kpk.go.id)
- ✅ Official asset declarations (elhkpn.kpk.go.id)
- ✅ Public Wikipedia articles
- ✅ Public news outlets

**No private data, no hacked databases, no paywalled content.**

## 🎯 Next Steps

1. **Start with scheduler disabled** - Run manual crawl first
2. **Enable scheduler** after verifying data quality
3. **Monitor change log** - Review detected changes weekly
4. **Expand sources** - Add provincial KPU sites, local news
5. **Customize thresholds** - Adjust wealth alert sensitivity

## 📈 Comparison with Nemesis

| Feature | Nemesis | CROSSROAD Enhanced |
|---------|---------|-------------------|
| Indonesian sources | Basic | ✅ 8 news + 4 govt databases |
| Scheduled updates | ❌ | ✅ Daily/Weekly/Monthly |
| Change detection | ❌ | ✅ Full audit trail |
| Asset tracking | ❌ | ✅ LHKPN integration |
| Corruption cases | ❌ | ✅ KPK integration |
| Business networks | ❌ | ✅ AHU ownership links |
| Risk scoring | ❌ | ✅ Algorithmic scoring |
| Dynasty detection | Basic | ✅ Multi-factor analysis |
| Party dynamics | Static | ✅ Real-time updates |

---

**Ready to deploy:** `docker compose up -d`

**Access dashboard:** http://localhost:3000

**API docs:** http://localhost:8000/docs
