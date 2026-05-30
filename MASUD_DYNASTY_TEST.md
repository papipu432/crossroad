# 🚀 Testing the Mas'ud Dynasty Detector

## Quick Start

### 1. Start the Stack
```bash
docker compose up -d
```

Wait for all services to be ready (Neo4j, PostgreSQL, Redis, Backend, Frontend).

### 2. Run Initial Data Mining
```bash
# Start the autonomous mining agent
curl -X POST http://localhost:8000/api/agent/start \
  -H "Content-Type: application/json" \
  -d '{
    "limit_dpr": 50,
    "limit_menteri": 20,
    "limit_gubernur": 10,
    "limit_regional": 50,
    "restart_mode": "fresh"
  }'
```

### 3. Test Mas'ud Dynasty Detection

#### Option A: Via API
```bash
# Full Mas'ud Dynasty investigation
curl http://localhost:8000/api/oligarchy/masud-dynasty | jq

# Oligarchy score for specific person
curl http://localhost:8000/api/oligarchy/rudy-masud/score | jq

# Detect self-dealing loops
curl http://localhost:8000/api/self-dealing/detect-loops | jq
```

#### Option B: Direct Python Script
```bash
cd backend
python tests/test_masud_dynasty.py
```

### 4. Monitor Progress
```bash
# Check scheduler status
curl http://localhost:8000/api/scheduler/status | jq

# View recent changes
curl "http://localhost:8000/api/changes/recent?hours=24" | jq
```

## Expected Output

### Mas'ud Dynasty Report
```json
{
  "investigation_status": "complete",
  "family_name": "Mas'ud",
  "risk_level": "CRITICAL",
  "total_score": 0.85,
  "component_scores": {
    "wealth_concentration": 0.75,
    "political_power": 0.90,
    "business_density": 0.60,
    "conflict_severity": 0.80,
    "monopoly_control": 0.95
  },
  "statistics": {
    "total_companies": 15,
    "government_positions": 7,
    "self_dealing_schemes": 3
  },
  "warning_flags": [
    "Governor owns multiple companies",
    "DETECTED EXCLUSIVE MANDATES (1)",
    "Governor directly profiting from business interests"
  ],
  "detected_schemes": [
    {
      "politician_name": "Rudy Mas'ud",
      "politician_position": "Gubernur Kalimantan Timur",
      "company_name": "PT Harum Resort",
      "relationship_type": "OWNER",
      "government_contract_type": "EXCLUSIVE_MANDATE",
      "is_exclusive": true,
      "confidence_score": 0.95
    }
  ]
}
```

## API Endpoints Reference

### Oligarchy Detection
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/oligarchy/masud-dynasty` | GET | Full Mas'ud Dynasty investigation |
| `/api/oligarchy/{slug}/score` | GET | Oligarchy score for specific person |
| `/api/oligarchy/scan-all` | POST | Background scan of all politicians |
| `/api/oligarchy/scan-status/{task_id}` | GET | Check scan task status |

### Self-Dealing Detection
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/self-dealing/detect-loops` | GET | Detect politician→company→contract loops |

### Business Tracking
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/business/person/{slug}/portfolio` | GET | Full business portfolio |
| `/api/business/company/{npwb}` | GET | Company details + politicians |
| `/api/business/scan/{slug}` | POST | Trigger background scan |
| `/api/business/conflicts/detect` | GET | All detected conflicts |
| `/api/business/sectors/{sector}` | GET | Companies by sector |

## Understanding the Scores

### Oligarchy Score Components (0.0 - 1.0)
- **Wealth Concentration**: Number of companies owned
- **Political Power**: Government position level
- **Business Density**: Companies per family member
- **Conflict Severity**: Self-dealing schemes detected
- **Monopoly Control**: Exclusive mandates found

### Risk Levels
- **LOW** (< 0.3): No significant concerns
- **MEDIUM** (0.3 - 0.5): Some business interests
- **HIGH** (0.5 - 0.7): Multiple conflicts
- **CRITICAL** (≥ 0.7): Severe oligarchy patterns

## Troubleshooting

### No Data Found
If the detector returns empty results:
1. Ensure mining has completed: `curl http://localhost:8000/api/mining/status`
2. Manually add seed data for East Kalimantan politicians
3. Run Wikipedia crawler: `curl -X POST http://localhost:8000/api/crawl/wiki -d '{"seed": "Rudy_Masud"}'`

### Neo4j Connection Error
```bash
docker compose logs neo4j
docker compose restart neo4j
```

### Check Logs
```bash
# Backend logs
docker compose logs -f backend

# Specific service
docker compose logs -f neo4j
```

## Next Steps

1. **Add More Data Sources**: Integrate LPSE for government contracts
2. **Enable Scheduled Scans**: Set `ENABLE_SCHEDULER=true` in `.env`
3. **Visualize Networks**: Use frontend D3.js graph explorer
4. **Set Up Alerts**: Configure webhook notifications for CRITICAL scores

## Advanced Usage

### Custom Dynasty Detection
```python
from backend.tests.test_masud_dynasty import MasudDynastyDetector
from backend.graph import GraphDB
from backend.db import Database

async def custom_scan():
    graph = GraphDB()
    db = Database()
    await db.init()
    
    detector = MasudDynastyDetector(graph, db)
    
    # Scan for different dynasty
    detector.target_surnames = ["Soeharto", "Yudhoyono", "Jokowi"]
    score = await detector.scan_masud_dynasty()
    
    print(f"Risk Level: {score.risk_level}")
    print(f"Schemes Detected: {len(score.detected_schemes)}")
```

### Batch Processing
```bash
# Scan all governors
for slug in governor-slugs.txt; do
  curl http://localhost:8000/api/oligarchy/$slug/score | jq '.risk_level'
done
```
