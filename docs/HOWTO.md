# CROSSROAD HOWTO Guide

Step-by-step tutorials for common investigation workflows.

## Table of Contents

1. [How to Trace APBD Money Flow](#how-to-trace-apbd-money-flow)
2. [How to Investigate a Political Dynasty](#how-to-investigate-a-political-dynasty)
3. [How to Detect Self-Dealing Schemes](#how-to-detect-self-dealing-schemes)
4. [How to Track Legal Cases](#how-to-track-legal-cases)
5. [How to Map Business Networks](#how-to-map-business-networks)
6. [How to Generate Intelligence Reports](#how-to-generate-intelligence-reports)

---

## How to Trace APBD Money Flow

### Scenario
You suspect corruption in East Kalimantan's infrastructure budget.

### Step 1: Access Budget Module

```bash
# Open dashboard
open http://localhost:3000

# Navigate to: Analytics → Budget Flow
```

### Step 2: Select Region and Year

- Region: `Kalimantan Timur`
- Year: `2024`
- Category: `Infrastructure` (optional filter)

### Step 3: Analyze Flow Diagram

**What to look for**:
- Large allocations to single contractors
- Projects with low realization rates (<50%)
- Unusual budget amendments

### Step 4: Identify Anomalies

```bash
# API call for anomaly detection
curl "http://localhost:8000/api/apbd/anomalies?region=kalimantan-timur&risk_threshold=0.7" | jq
```

**Red flags**:
- ⚠️ Single bidder tenders
- ⚠️ Price inflation (>30% above market)
- ⚠️ Related-party transactions
- ⚠️ Ghost projects (0% physical progress)

### Step 5: Trace Contractor Connections

```bash
# Get contractor details
curl "http://localhost:8000/api/business/company/PT-Masud-Construction" | jq

# Check political connections
curl "http://localhost:8000/api/business/person/rudy-masud/portfolio" | jq
```

### Step 6: Export Evidence

```bash
# Generate report
curl "http://localhost:8000/api/report/apbd/kalimantan-timur/2024?format=pdf" \
  --output apbd_report.pdf
```

---

## How to Investigate a Political Dynasty

### Scenario
Research the Mas'ud family political network.

### Step 1: Start Dynasty Search

```bash
# API endpoint
curl "http://localhost:8000/api/oligarchy/masud-dynasty" | jq
```

### Step 2: Map Family Members

**Dashboard**: Dynasty Tracker → Search "Mas'ud"

**Identify**:
- Current office holders
- Previous positions
- Family relationships (spouse, children, siblings)

### Step 3: Analyze Power Concentration

```cypher
// Neo4j query
MATCH (p:Person)-[:FAMILY_OF]-(family:Person)
WHERE p.name CONTAINS "Mas'ud"
RETURN p.name, p.position, family.name, family.position
```

### Step 4: Track Wealth Accumulation

```bash
# Get LHKPN data for all family members
curl "http://localhost:8000/api/enhanced/lhkpn/Rudy%20Mas'ud" | jq
curl "http://localhost:8000/api/enhanced/lhkpn/Resnawan" | jq

# Compare year-over-year growth
curl "http://localhost:8000/api/wealth/masud-family/history" | jq
```

**Look for**:
- Sudden wealth increases coinciding with elections
- Asset transfers between family members
- Undeclared assets

### Step 5: Document Business Interests

```bash
# Scan all companies
curl -X POST "http://localhost:8000/api/oligarchy/scan-all" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Review results
curl "http://localhost:8000/api/business/person/rudy-masud/portfolio" | jq
```

### Step 6: Calculate Dynasty Score

**Components**:
- Number of family members in office (weight: 30%)
- Total controlled wealth (weight: 25%)
- Business empire size (weight: 25%)
- Multi-generational presence (weight: 20%)

**Output**: Score 0.0-1.0 (≥0.7 = significant dynasty)

---

## How to Detect Self-Dealing Schemes

### Scenario
Investigate potential conflict of interest in government contracts.

### Step 1: Run Self-Dealing Detection

```bash
curl "http://localhost:8000/api/self-dealing/detect-loops" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq
```

### Step 2: Review Detected Loops

**Example output**:
```
Governor Rudy Mas'ud 
  ↓ OWNS (75%)
PT Harum Resort Indonesia
  ↓ WON_TENDER (Rp 50B)
APBD Contract: Government Banquet Services
  ↓ BENEFITS
Governor's Office Events
```

### Step 3: Verify Ownership

```bash
# Check company registration
curl "http://localhost:8000/api/business/company/PT-Harum-Resort" | jq

# Verify shareholder list
# Look for: Politician name, family members, proxies
```

### Step 4: Examine Tender Process

```bash
# Get tender details
curl "http://localhost:8000/api/lpse/tender/LPSE-2024-001234" | jq

# Check for red flags:
# - Single bidder?
# - Direct selection method?
# - Awarded price close to estimate?
```

### Step 5: Calculate Conflict Severity

**Scoring**:
- **CRITICAL** (0.9-1.0): Direct ownership + exclusive mandate
- **HIGH** (0.7-0.9): Family member ownership + preferential treatment
- **MEDIUM** (0.5-0.7): Indirect connection + suspicious patterns
- **LOW** (0.0-0.5): Weak or no connection

### Step 6: Build Case File

```bash
# Collect evidence
# - Company documents
# - Tender records
# - LHKPN declarations
# - News articles

# Generate dossier
curl "http://localhost:8000/api/report/self-dealing/rudy-masud?format=pdf" \
  --output case_file.pdf
```

---

## How to Track Legal Cases

### Scenario
Monitor corruption case against politician.

### Step 1: Search for Cases

```bash
# By person
curl "http://localhost:8000/api/legal/person/rudy-masud/cases" | jq

# By keyword
curl "http://localhost:8000/api/kpk/search?q=korupsi+kaltim" | jq

# By case number
curl "http://localhost:8000/api/legal/case/123-Pid.Sus-2024-PN.Jkt" | jq
```

### Step 2: Track Case Timeline

**Dashboard**: Legal Tracker → Case Details

**Timeline stages**:
1. Investigation started
2. Named as suspect
3. Charged in court
4. Trial proceedings
5. Verdict
6. Appeal (if any)
7. Final verdict

### Step 3: Set Up Alerts

```bash
# Subscribe to case updates
curl -X POST "http://localhost:8000/api/legal/alerts/subscribe" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "123-Pid.Sus-2024-PN.Jkt", "email": "you@example.com"}'
```

### Step 4: Monitor Co-Defendants

```cypher
// Find related cases
MATCH (c:Case)<-[:INDICTED_IN]-(p:Person)
WHERE c.id = "123-Pid.Sus-2024-PN.Jkt"
RETURN p.name, p.role
```

### Step 5: Analyze Asset Recovery

```bash
# Check returned state losses
curl "http://localhost:8000/api/legal/case/123-Pid.Sus-2024-PN.Jkt/assets" | jq

# Compare: Loss amount vs. Recovered amount
```

---

## How to Map Business Networks

### Scenario
Understand business empire of political figure.

### Step 1: Get Person's Portfolio

```bash
curl "http://localhost:8000/api/business/person/rudy-masud/portfolio" | jq
```

### Step 2: Visualize Network

**Dashboard**: Graph Explorer → Search person → Filter: Business relationships only

**Node types**:
- Person (politician, family, associates)
- Company (PT, CV, Tbk)
- Position (commissioner, director, shareholder)

### Step 3: Identify Key Companies

**Look for**:
- Companies with government contracts
- Monopolies in strategic sectors
- Recently established companies (after election)

### Step 4: Trace Beneficial Ownership

```bash
# Check hidden ownership
curl "http://localhost:8000/api/business/company/PT-X/beneficial-owners" | jq

# Look for: Proxy shareholders, nominee arrangements
```

### Step 5: Cross-Reference with Tenders

```bash
# Find all tenders won by network companies
curl "http://localhost:8000/api/business/network/rudy-masud/tenders" | jq
```

### Step 6: Calculate Network Value

**Total estimated value**:
- Share ownership × Company capital
- Contract values from government
- Asset declarations

---

## How to Generate Intelligence Reports

### Scenario
Create comprehensive report for investigation.

### Step 1: Define Scope

- Subject: Person, company, or region
- Time period: Specific years or all-time
- Focus areas: Business, legal, family, etc.

### Step 2: Gather Data

```bash
# Person dossier
curl "http://localhost:8000/api/person/rudy-masud/dossier" \
  -H "Authorization: Bearer YOUR_TOKEN" > dossier.json

# Business portfolio
curl "http://localhost:8000/api/business/person/rudy-masud/portfolio" > business.json

# Legal cases
curl "http://localhost:8000/api/legal/person/rudy-masud/cases" > legal.json

# Wealth history
curl "http://localhost:8000/api/wealth/rudy-masud/history" > wealth.json
```

### Step 3: Generate Report

```bash
# PDF format
curl "http://localhost:8000/api/report/generate/rudy-masud?format=pdf&sections=all" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output full_report.pdf

# Excel format (for data analysis)
curl "http://localhost:8000/api/report/generate/rudy-masud?format=xlsx" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output data_export.xlsx
```

### Step 4: Customize Report

**Sections available**:
- Executive Summary
- Biography
- Family Network
- Business Interests
- Legal Cases
- Wealth Analysis
- Oligarchy Score
- Recommendations

### Step 5: Share Securely

```bash
# Encrypt report
gpg --encrypt --recipient recipient@example.com full_report.pdf

# Or use secure link (expires in 7 days)
curl "http://localhost:8000/api/report/share/full_report.pdf?expiry=7d" | jq
```

---

## Tips for Effective Investigations

### Best Practices

1. **Start broad, then narrow**: Begin with general search, focus on anomalies
2. **Cross-reference sources**: Verify information across multiple databases
3. **Document everything**: Save screenshots, export data, note timestamps
4. **Follow the money**: Budget flows and company ownership often reveal truth
5. **Track changes over time**: Sudden wealth or position changes are red flags

### Common Pitfalls

❌ Assuming guilt from allegations  
✅ Verify with official sources (court records, LHKPN)

❌ Ignoring proxy ownership  
✅ Look for family members and close associates

❌ Focusing only on current positions  
✅ Historical data shows patterns

❌ Overlooking small contracts  
✅ Multiple small contracts can equal large corruption

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Quick search |
| `Ctrl+G` | Open graph explorer |
| `Ctrl+R` | Generate report |
| `Ctrl+L` | View legal cases |
| `Esc` | Close modal |

---

**Version**: 2.0.0  
**Last Updated**: 2024
