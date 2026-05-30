# Business & Wealth Tracking Guide

## Overview

This guide explains how to use the enhanced business registry tracking system for Indonesian political figures. The system automatically tracks:

- **Company ownership** (shareholders)
- **Board positions** (commissioners, directors)
- **Beneficial ownership** (ultimate beneficial owners)
- **Conflicts of interest** (position vs business holdings)
- **Wealth declarations** (LHKPN reports)

## Data Sources

### 1. AHU Online (Direktorat Jenderal AHU)
- **URL**: https://ahu.go.id
- **Data**: Company registrations, shareholders, commissioners, directors
- **Coverage**: All registered PT (Perseroan Terbatas) in Indonesia
- **Update Frequency**: Weekly automatic scans

### 2. OSS (Online Single Submission)
- **URL**: https://oss.go.id
- **Data**: Business licenses (NIB), KBLI codes, investment data
- **Coverage**: All licensed businesses since 2018
- **Use Case**: Verify business activities and sectors

### 3. IDX (Indonesia Stock Exchange)
- **URL**: https://idx.co.id
- **Data**: Public company profiles, major shareholders, board members
- **Coverage**: 800+ listed companies
- **Special Feature**: Real-time ownership disclosures

### 4. LHKPN (KPK Asset Declarations)
- **URL**: https://elhkpn.kpk.go.id
- **Data**: Annual asset declarations by public officials
- **Coverage**: All elected/appointed officials
- **Alert System**: Detects suspicious wealth growth (>100% YoY)

## API Endpoints

### Get Person's Business Portfolio

```bash
GET /api/business/person/{slug}/portfolio
```

**Response:**
```json
{
  "person": {
    "slug": "prabowo-subianto",
    "full_name": "Prabowo Subianto",
    "position": "Presiden Republik Indonesia"
  },
  "portfolio": {
    "total_companies": 15,
    "as_shareholder": [
      {
        "company": "PT Nusantara Energy",
        "npwb": "01.203.456.7-89.000",
        "shares_percent": 45.5,
        "shares_value": 125000000000,
        "province": "DKI Jakarta"
      }
    ],
    "as_commissioner": [
      {
        "company": "PT Agrindo Sejahtera",
        "npwb": "02.304.567.8-90.000",
        "appointment_date": "2018-03-15",
        "province": "Jawa Tengah"
      }
    ],
    "as_director": [],
    "estimated_total_value": 450000000000,
    "sectors": ["Pertambangan", "Energi", "Perkebunan"],
    "public_companies": [
      {
        "name": "PT Bank Mandiri Tbk",
        "ticker": "BMRI",
        "sector": "Keuangan"
      }
    ],
    "private_companies": [...]
  },
  "conflicts_detected": [
    {
      "type": "energy_minister_mining",
      "severity": "critical",
      "position": "Menteri ESDM",
      "conflicting_sectors": ["Pertambangan", "Energi"],
      "recommendation": "Review for potential divestment required"
    }
  ]
}
```

### Scan Person's Business Connections (Background Task)

```bash
POST /api/business/scan/{slug}
```

**Use Case**: Trigger on-demand scan for a specific politician. Results are stored in Neo4j graph.

**Response:**
```json
{
  "status": "scanning",
  "message": "Background scan started for Prabowo Subianto",
  "person_slug": "prabowo-subianto"
}
```

### Get Company Details

```bash
GET /api/business/company/{npwb}
```

**Response:**
```json
{
  "company": {
    "name": "PT Kaltim Prima Coal",
    "npwb": "01.203.456.7-89.000",
    "establishment_date": "1990-05-20",
    "capital": 5000000000000,
    "status": "active",
    "province": "Kalimantan Timur",
    "shareholders": [
      {"name": "Bumi Resources Tbk", "percent": 85.0}
    ],
    "commissioners": [
      {"name": "Garibaldi Thohir", "appointment_date": "2020-01-15"}
    ],
    "directors": [...]
  },
  "associated_people": [
    {
      "person": {
        "slug": "garibaldi-thohir",
        "full_name": "Garibaldi Thohir",
        "position": "Wakil Menteri BUMN"
      },
      "relationship": {
        "role_type": "commissioner",
        "appointment_date": "2020-01-15",
        "is_current": true
      }
    }
  ]
}
```

### Detect All Conflicts of Interest

```bash
GET /api/business/conflicts/detect
```

**Response:**
```json
{
  "total_flagged": 12,
  "conflicts": [
    {
      "person": {
        "slug": "arif-budiman",
        "full_name": "Arif Budiman",
        "position": "Menteri ESDM",
        "party": "PDIP"
      },
      "conflicts": [
        {
          "position": "Menteri ESDM",
          "company": "PT Tambang Batubara Jaya",
          "sector": "Pertambangan",
          "activity": "Pertambangan Batubara",
          "role": "OWNS_SHARES",
          "severity": "high"
        }
      ],
      "severity": "high"
    }
  ]
}
```

### Get Companies by Sector

```bash
GET /api/business/sectors/{sector}
```

**Example**: `/api/business/sectors/pertambangan`

**Response:**
```json
{
  "sector": "pertambangan",
  "companies": [
    {
      "company": {
        "name": "PT Freeport Indonesia",
        "npwb": "...",
        "business_activities": ["Pertambangan Tembaga", "Pertambangan Emas"]
      },
      "politicians": [
        {
          "slug": "ridwan-hamilu",
          "full_name": "Ridwan Hamilu",
          "position": "Komisaris"
        }
      ],
      "relationships": [...]
    }
  ],
  "count": 45
}
```

## Graph Database Schema

### Company Node
```cypher
(:Company {
  npwb: "01.203.456.7-89.000",
  name: "PT Example Tbk",
  establishment_date: "2010-05-20",
  capital_authorized: 1000000000000,
  capital_paid: 750000000000,
  status: "active",
  province: "DKI Jakarta",
  city: "Jakarta Selatan",
  business_activities: ["Pertambangan", "Energi"],
  source_url: "https://ahu.go.id/...",
  data_source: "AHU",
  updated_at: timestamp()
})
```

### Relationships

#### OWNS_SHARES
```cypher
(:Person)-[r:OWNS_SHARES {
  role_type: "shareholder",
  shares_percent: 25.5,
  shares_value: 50000000000,
  appointment_date: "2018-03-15",
  is_current: true,
  updated_at: timestamp()
}]->(:Company)
```

#### COMMISSIONER_OF
```cypher
(:Person)-[r:COMMISSIONER_OF {
  role_type: "commissioner",
  appointment_date: "2020-01-10",
  is_current: true,
  updated_at: timestamp()
}]->(:Company)
```

#### DIRECTOR_OF
```cypher
(:Person)-[r:DIRECTOR_OF {
  role_type: "director",
  appointment_date: "2019-06-20",
  is_current: true,
  updated_at: timestamp()
}]->(:Company)
```

#### BENEFICIAL_OWNER_OF
```cypher
(:Person)-[r:BENEFICIAL_OWNER_OF {
  role_type: "beneficial_owner",
  ownership_percent: 15.0,
  is_current: true,
  updated_at: timestamp()
}]->(:Company)
```

## Conflict Detection Rules

The system automatically flags conflicts based on position-sector combinations:

| Position Pattern | Conflicting Sectors | Severity |
|-----------------|---------------------|----------|
| Menteri ESDM | Pertambangan, Energi, Minyak dan Gas | Critical |
| Menteri Perhubungan | Transportasi, Logistik, Konstruksi Jalan | High |
| Menteri Pertanian | Perkebunan, Pertanian, Agroindustri | High |
| Anggota Komisi VI DPR | Manufaktur, Industri, Perdagangan | Medium |
| Gubernur | Konstruksi, Pengembangan Properti (local) | High |
| Wakil Gubernur | Konstruksi, Pengembangan Properti (local) | High |

## Scheduled Updates

### Daily Tasks
- **News monitoring**: Scan 8 news outlets for business-related mentions
- **LHKPN alerts**: Check for new asset declarations with >100% growth

### Weekly Tasks
- **AHU company scans**: Update top 100 politicians' business portfolios
- **IDX disclosures**: Refresh public company board compositions
- **Party structure**: Verify no new business conflicts from position changes

### Monthly Tasks
- **Full portfolio refresh**: Re-scan all politicians' business connections
- **Sector analysis**: Generate sector-politician network maps
- **Conflict audit**: Comprehensive conflict of interest report

## Manual Triggers

### Scan Specific Person
```bash
curl -X POST http://localhost:8000/api/business/scan/prabowo-subianto
```

### Check Scheduler Status
```bash
curl http://localhost:8000/api/scheduler/status
```

### View Recent Changes
```bash
curl "http://localhost:8000/api/changes/recent?hours=168"
```

## Integration with Nemesis Project

**Should you merge with Nemesis?** 

**Recommendation: NO** - Your CROSSROAD implementation is superior for Indonesian context because:

1. **Local Sources**: Nemesis uses generic sources; CROSSROAD has KPU, LHKPN, KPK, AHU
2. **Scheduled Updates**: Nemesis lacks automated daily/weekly scraping
3. **Conflict Detection**: CROSSROAD has Indonesia-specific conflict rules
4. **Business Registry**: Nemesis doesn't track corporate ownership
5. **Language**: CROSSROAD handles Indonesian names, titles, and contexts

**Instead, use CROSSROAD as your foundation and:**
- Add more Indonesian news sources
- Expand seed politician list
- Integrate social media monitoring (Twitter/X API)
- Add temporal tracking for alliance shifts

## Best Practices

### 1. Entity Resolution
Indonesian names have variations. The system uses fuzzy matching:
- "Prabowo Subianto" = "Prabowo" = "H. Prabowo Subianto"
- "Garibaldi Thohir" = "Boy Thohir"

### 2. Evidence Tracking
All relationships include:
- `source_url`: Original data source
- `evidence`: Exact text snippet
- `confidence`: 0.0-1.0 score
- `updated_at`: Timestamp

### 3. Privacy Compliance
- Only use publicly available data
- Mask ID numbers (KTP/NPWP)
- Respect robots.txt
- Rate limit requests (2-3 second delays)

### 4. Data Validation
Before storing in graph:
```python
# Validate NPWB format
assert re.match(r'\d{2}\.\d{3}\.\d{3}\.\d-\d{5}', npwb)

# Validate shares percentage
assert 0 <= shares_percent <= 100

# Verify person exists before linking
person = await get_person_by_slug(slug)
assert person is not None
```

## Troubleshooting

### Issue: Company not found
**Solution**: Try alternative search strategies:
```python
# Search by NPWB
companies = await crawler.search_company_by_name(npwb, exact=True)

# Search by partial name
companies = await crawler.search_company_by_name("Kaltim Prima")

# Search IDX for public companies
profile = await idx.get_company_profile("ADRO")
```

### Issue: False positive conflicts
**Solution**: Refine conflict patterns in `graph.py`:
```python
conflict_sectors = {
    'Menteri ESDM': ['Pertambangan', 'Energi'],  # Narrow down
    # Add exceptions
}
```

### Issue: Slow scans
**Solution**: Use background tasks:
```python
@app.post("/api/business/scan/{slug}")
async def scan_person_business_connections(slug: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(scan_task)
    return {"status": "scanning"}
```

## Next Steps

1. **Deploy**: `docker compose up -d`
2. **Initial Scan**: Run scans for top 50 politicians
3. **Monitor**: Check `/api/scheduler/status` daily
4. **Expand**: Add more seed politicians in `constants.py`
5. **Visualize**: Use D3.js frontend to explore business networks

## Contact & Support

For questions about Indonesian political data:
- KPU: https://kpu.go.id/kontak
- KPK: https://kpk.go.id/kontak
- AHU: https://ahu.go.id/kontak
