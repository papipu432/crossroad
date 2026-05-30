# CROSSROAD API Cookbook

Practical recipes for common investigation tasks.

## Table of Contents

1. [Track a Political Dynasty](#track-a-political-dynasty)
2. [Detect Self-Dealing Schemes](#detect-self-dealing-schemes)
3. [Find Ghost Projects in APBD](#find-ghost-projects-in-apbd)
4. [Monitor Legal Cases](#monitor-legal-cases)
5. [Analyze Wealth Anomalies](#analyze-wealth-anomalies)
6. [Map Business Networks](#map-business-networks)
7. [Query with Natural Language](#query-with-natural-language)
8. [Generate Investigation Reports](#generate-investigation-reports)

---

## Track a Political Dynasty

### Find All Family Members

```bash
curl "http://localhost:8000/api/oligarchy/masud-dynasty" | jq
```

**Response**:
```json
{
  "dynasty_name": "Mas'ud",
  "members": [
    {
      "name": "Rudy Mas'ud",
      "position": "Gubernur Kalimantan Timur",
      "oligarchy_score": 0.92
    },
    {
      "name": "Resnawan",
      "position": "Anggota DPR",
      "oligarchy_score": 0.78
    }
  ],
  "companies_owned": 15,
  "total_wealth": 5000000000000
}
```

### Calculate Dynasty Score

```bash
curl "http://localhost:8000/api/oligarchy/rudy-masud/score" | jq
```

---

## Detect Self-Dealing Schemes

### Find Self-Dealing Loops

```bash
curl "http://localhost:8000/api/self-dealing/detect-loops" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

**Example Output**:
```
Governor Rudy Mas'ud 
  → OWNS (75%) → PT Harum Resort 
  → WON_TENDER → APBD Contract (Banquet Services)
  = CRITICAL CONFLICT
```

### Scan Specific Person

```bash
curl -X POST "http://localhost:8000/api/business/scan/rudy-masud" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Find Ghost Projects in APBD

### Get Budget Flow Analysis

```bash
curl "http://localhost:8000/api/apbd/kalimantan-timur/flow?year=2024" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

### Detect Anomalies

```bash
curl "http://localhost:8000/api/apbd/anomalies?region=kalimantan-timur&risk_threshold=0.7" | jq
```

**Filters Available**:
- `risk_threshold`: Minimum risk score (0.0-1.0)
- `category`: Budget category (Infrastructure, Education, etc.)
- `status`: Project status (Delayed, Completed, etc.)

---

## Monitor Legal Cases

### Get Person's Legal History

```bash
curl "http://localhost:8000/api/legal/person/rudy-masud/cases" | jq
```

### Search KPK Cases

```bash
curl "http://localhost:8000/api/kpk/search?q=korupsi+kaltim" | jq
```

### Track Case Status

```bash
curl "http://localhost:8000/api/legal/case/123-Pid.Sus-2024-PN.Jkt" | jq
```

---

## Analyze Wealth Anomalies

### Get LHKPN Data

```bash
curl "http://localhost:8000/api/enhanced/lhkpn/Rudy%20Mas'ud" | jq
```

### Compare Year-over-Year

```bash
curl "http://localhost:8000/api/wealth/rudy-masud/history?start_year=2019&end_year=2024" | jq
```

**Detects**:
- Wealth growth > 100% (flagged as suspicious)
- Asset type changes
- Unexplained income sources

---

## Map Business Networks

### Get Full Business Portfolio

```bash
curl "http://localhost:8000/api/business/person/rudy-masud/portfolio" | jq
```

**Returns**:
- Companies owned (with percentages)
- Board positions (Commissioner, Director)
- Beneficial ownership
- Related tenders won

### Find Companies by Sector

```bash
curl "http://localhost:8000/api/business/sectors/mining" | jq
```

### Check Conflict of Interest

```bash
curl "http://localhost:8000/api/business/conflicts/detect" | jq
```

---

## Query with Natural Language

### Indonesian Queries

```bash
curl -X POST "http://localhost:8000/api/query/natural" \
  -H "Content-Type: application/json" \
  -d '{"query": "Siapa anggota DPR yang punya perusahaan tambang?"}' | jq
```

### English Queries

```bash
curl -X POST "http://localhost:8000/api/query/natural" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show all companies owned by Governor of East Kalimantan"}' | jq
```

### Complex Queries

```bash
curl -X POST "http://localhost:8000/api/query/natural" \
  -H "Content-Type: application/json" \
  -d '{"query": "Tunjukkan semua kontrak APBD Kalimantan Timur dengan PT Mas'ud tahun 2024"}' | jq
```

---

## Generate Investigation Reports

### Full Intelligence Dossier

```bash
curl "http://localhost:8000/api/person/rudy-masud/dossier" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

**Includes**:
- Biography
- Family network
- Business interests
- Legal cases
- Wealth history
- Oligarchy score breakdown

### Export to PDF

```bash
curl "http://localhost:8000/api/report/generate/rudy-masud?format=pdf" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output dossier.pdf
```

### Batch Scan All Politicians

```bash
curl -X POST "http://localhost:8000/api/oligarchy/scan-all" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Advanced Cypher Queries

### Direct Neo4j Access

```bash
curl -X POST "http://localhost:7474/db/data/transaction/commit" \
  -H "Content-Type: application/json" \
  -u neo4j:your_password \
  -d '{
    "statements": [{
      "statement": "MATCH (p:Person)-[:OWNS_SHARES]->(c:Company) WHERE p.name CONTAINS \"Mas\\'ud\" RETURN p.name, c.name, c.capital"
    }]
  }' | jq
```

### Find Shortest Path

```cypher
MATCH path = shortestPath(
  (p1:Person {name: "Rudy Mas'ud"})-[*..5]-(p2:Person {name: "Prabowo Subianto"})
)
RETURN path
```

### Cluster Detection

```cypher
MATCH (p:Person)-[:FAMILY_OF]-(family:Person)
WHERE p.name = "Rudy Mas'ud"
RETURN collect(family.name) as family_members
```

---

## Real-Time Monitoring

### Subscribe to Progress (SSE)

```bash
curl -N "http://localhost:8000/api/agent/progress" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Get Recent Changes

```bash
curl "http://localhost:8000/api/changes/recent?hours=24" | jq
```

### Scheduler Status

```bash
curl "http://localhost:8000/api/scheduler/status" | jq
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| Standard API | 100 req/min |
| Natural Query | 10 req/min |
| Report Generation | 5 req/min |
| Bulk Operations | 2 req/min |

---

**Version**: 2.0.0  
**Last Updated**: 2024
