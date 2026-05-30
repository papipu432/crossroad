# CROSSROAD Data Dictionary

## Node Types

### Person

Represents a political figure or public person.

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `slug` | String | Unique identifier (URL-safe name) | `prabowo-subianto` |
| `name` | String | Full name | `Prabowo Subianto` |
| `birth_date` | Date | Date of birth | `1951-10-17` |
| `birth_place` | String | Place of birth | `Jakarta` |
| `nationality` | String | Nationality | `Indonesian` |
| `religion` | String | Religion | `Islam` |
| `education` | List[String] | Education history | `["SMA Negeri 4 Jakarta", "SESA Fort Benning"]` |
| `positions` | List[Object] | Current and past positions | See Position node |
| `image_url` | String | Profile image URL | `https://...` |
| `wikipedia_url` | String | Wikipedia page URL | `https://id.wikipedia.org/...` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-01T00:00:00Z` |
| `updated_at` | DateTime | Last update timestamp | `2024-01-15T00:00:00Z` |
| `oligarchy_score` | Float | Oligarchy risk score (0.0-1.0) | `0.85` |
| `dynasty_score` | Float | Dynasty influence score (0.0-1.0) | `0.92` |

**Labels**: `:Person`

**Indexes**:
- `CREATE INDEX FOR (p:Person) ON (p.slug)`
- `CREATE INDEX FOR (p:Person) ON (p.name)`

---

### Company

Represents a business entity (PT, CV, Tbk, etc.).

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `npwb` | String | Nomor Pokok Wajib Pajak / Business ID | `01.203.456.7-89.000` |
| `name` | String | Company name | `PT Harum Resort Indonesia` |
| `legal_form` | String | Legal form (PT, CV, Tbk) | `PT` |
| `capital_authorized` | Integer | Authorized capital (IDR) | `1000000000000` |
| `capital_paid` | Integer | Paid-up capital (IDR) | `500000000000` |
| `business_activities` | List[String] | KBLI codes and descriptions | `["55110 - Hotel dan Resort"]` |
| `province` | String | Province location | `Kalimantan Timur` |
| `city` | String | City location | `Balikpapan` |
| `establishment_date` | Date | Establishment date | `2015-03-15` |
| `status` | String | Active/Inactive status | `Active` |
| `website` | String | Company website | `https://...` |
| `created_at` | DateTime | Record creation timestamp | `2024-01-01T00:00:00Z` |

**Labels**: `:Company`

**Indexes**:
- `CREATE INDEX FOR (c:Company) ON (c.npwb)`
- `CREATE INDEX FOR (c:Company) ON (c.name)`

---

### Position

Represents a political or organizational position.

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `title` | String | Position title | `Gubernur Kalimantan Timur` |
| `institution` | String | Institution name | `Pemerintah Provinsi Kalimantan Timur` |
| `level` | String | Government level | `Provincial`, `National`, `Regional` |
| `start_date` | Date | Start date | `2018-10-01` |
| `end_date` | Date | End date (null if current) | `2023-10-01` |
| `is_current` | Boolean | Currently held | `true` |
| `appointment_type` | String | How appointed | `Elected`, `Appointed` |
| `salary_range` | String | Salary range (if known) | `Rp 50-100 juta` |

**Labels**: `:Position`

---

### Party

Represents a political party.

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `name` | String | Party name | `Partai Gerindra` |
| `abbreviation` | String | Short name | `Gerindra` |
| `coalition` | String | Current coalition | `Koalisi Indonesia Maju` |
| `ideology_score` | Float | Ideology spectrum (-1.0 to +1.0) | `0.3` |
| `founded_date` | Date | Founding date | `2008-02-06` |
| `chairman` | String | Current chairman | `Prabowo Subianto` |
| `headquarters` | String | Headquarters location | `Jakarta` |
| `seats_dpr` | Integer | DPR seats | `87` |
| `vote_percentage` | Float | Last election vote % | `24.5` |

**Labels**: `:Party`

---

### Case

Represents a legal case (corruption, criminal, civil).

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | String | Case ID (SIPP number) | `123/Pid.Sus/2024/PN.Jkt` |
| `type` | String | Case type | `Corruption`, `Criminal`, `Civil` |
| `category` | String | Specific category | `Suap`, `Gratifikasi`, `Penggelapan` |
| `status` | String | Current status | `Investigation`, `Trial`, `Verdict`, `Appeal` |
| `verdict` | String | Court verdict (if concluded) | `Guilty`, `Not Guilty` |
| `sentence` | String | Sentence details | `5 years prison, Rp 500M fine` |
| `court` | String | Court name | `Pengadilan Negeri Jakarta Pusat` |
| `judge_panel` | List[String] | Judges | `["John Doe", "Jane Smith"]` |
| `prosecutor` | String | Prosecutor office | `Kejaksaan Tinggi DKI Jakarta` |
| `loss_amount` | Integer | State financial loss (IDR) | `100000000000` |
| `start_date` | Date | Case start date | `2023-01-15` |
| `end_date` | Date | Case end date | `2024-06-20` |
| `source_url` | String | Source URL | `https://kpk.go.id/...` |

**Labels**: `:Case`

**Indexes**:
- `CREATE INDEX FOR (c:Case) ON (c.id)`

---

### Budget

Represents a government budget line (APBN/APBD).

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | String | Budget line ID | `APBD-KALTIM-2024-001` |
| `region` | String | Region name | `Kalimantan Timur` |
| `year` | Integer | Budget year | `2024` |
| `category` | String | Budget category | `Infrastructure`, `Education` |
| `sub_category` | String | Sub-category | `Road Construction` |
| `amount_allocated` | Integer | Allocated amount (IDR) | `50000000000` |
| `amount_realized` | Integer | Realized amount (IDR) | `45000000000` |
| `realization_rate` | Float | Realization percentage | `0.90` |
| `description` | String | Project description | `Construction of Balikpapan-Samarinda toll road` |
| `contractor` | String | Contractor name | `PT Pembangunan Jaya` |
| `start_date` | Date | Project start date | `2024-01-01` |
| `end_date` | Date | Project end date | `2024-12-31` |
| `status` | String | Project status | `Planning`, `Ongoing`, `Completed`, `Delayed` |
| `anomaly_flags` | List[String] | Detected anomalies | `["Price inflation", "Single bidder"]` |
| `risk_score` | Float | Fraud risk score (0.0-1.0) | `0.75` |

**Labels**: `:Budget`

---

### Document

Represents a text document for semantic search.

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | String | Document ID (UUID) | `550e8400-e29b-41d4-a716-446655440000` |
| `url` | String | Source URL | `https://news.com/article/123` |
| `title` | String | Document title | `Governor Rudy Mas'ud Opens New Resort` |
| `content` | String | Full text content | `...` |
| `embedding` | List[Float] | Vector embedding (768 dims) | `[0.1, -0.2, ...]` |
| `source_type` | String | Source type | `News`, `Wikipedia`, `LHKPN`, `Court` |
| `published_date` | Date | Publication date | `2024-01-15` |
| `language` | String | Language code | `id` (Indonesian) |
| `entities` | List[String] | Mentioned entities | `["Rudy Mas'ud", "PT Harum Resort"]` |

**Labels**: `:Document`

---

### Tender

Represents a government procurement tender (LPSE).

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | String | Tender ID | `LPSE-2024-001234` |
| `title` | String | Tender title | `Construction of Government Office Building` |
| `budget_owner` | String | Budget owner agency | `Dinas PUPR Kalimantan Timur` |
| `estimated_value` | Integer | Estimated value (IDR) | `100000000000` |
| `winner` | String | Winning company | `PT Mas'ud Construction` |
| `winner_value` | Integer | Winning bid value (IDR) | `95000000000` |
| `bidder_count` | Integer | Number of bidders | `3` |
| `method` | String | Procurement method | `Open Tender`, `Direct Selection` |
| `announcement_date` | Date | Announcement date | `2024-01-10` |
| `award_date` | Date | Award date | `2024-02-15` |
| `completion_date` | Date | Expected completion | `2024-12-31` |
| `anomaly_flags` | List[String] | Detected anomalies | `["Related party", "Single bidder"]` |

**Labels**: `:Tender`

---

## Relationship Types

### Family Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `FAMILY_OF` | `type` (Spouse, Child, Parent, Sibling), `evidence` (URL) | Family connection |
| `MARRIED_TO` | `marriage_date`, `evidence` | Marriage relationship |
| `PARENT_OF` | `evidence` | Parent-child relationship |
| `CHILD_OF` | `evidence` | Child-parent relationship |
| `SIBLING_OF` | `evidence` | Sibling relationship |

**Example**:
```cypher
(:Person {name: "Rudy Mas'ud"})-[FAMILY_OF {type: "Spouse"}]->(:Person {name: "Resnawan"})
```

---

### Political Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `MEMBER_OF` | `start_date`, `end_date`, `position` | Party membership |
| `HOLDS_POSITION` | `start_date`, `end_date`, `appointed_by` | Position holding |
| `MENTORED_BY` | `since`, `evidence` | Political mentorship |
| `POLITICAL_ALLY` | `strength` (0.0-1.0), `evidence` | Political alliance |
| `COALITION_MEMBER` | `since`, `role` | Coalition membership |

**Example**:
```cypher
(:Person {name: "Prabowo Subianto"})-[MEMBER_OF {start_date: "2008-02-06"}]->(:Party {name: "Partai Gerindra"})
```

---

### Business Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `OWNS_SHARES` | `percentage`, `value` (IDR), `date` | Share ownership |
| `COMMISSIONER_OF` | `start_date`, `end_date`, `type` (Independent, Main) | Commissioner role |
| `DIRECTOR_OF` | `start_date`, `end_date`, `role` | Director role |
| `BENEFICIAL_OWNER_OF` | `percentage`, `evidence` | Beneficial ownership |
| `FOUNDED` | `date`, `initial_capital` | Company founder |

**Example**:
```cypher
(:Person {name: "Rudy Mas'ud"})-[OWNS_SHARES {percentage: 75.0}]->(:Company {name: "PT Harum Resort"})
```

---

### Legal Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `INDICTED_IN` | `role` (Suspect, Defendant, Witness), `date` | Case involvement |
| `CONVICTED_IN` | `sentence`, `verdict_date` | Conviction |
| `IMPRISONED_IN` | `facility`, `release_date` | Imprisonment |
| `ACQUITTED_IN` | `verdict_date`, `reason` | Acquittal |

**Example**:
```cypher
(:Person {name: "Anwar Ibrahim"})-[INDICTED_IN {role: "Suspect", date: "2023-05-10"}]->(:Case {id: "123/Pid.Sus/2023"})
```

---

### Financial Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `WON_TENDER` | `amount`, `date`, `project_name` | Won government tender |
| `FUNDED_BY` | `amount`, `date`, `source` | Budget funding |
| `PAID_TO` | `amount`, `date`, `purpose` | Payment made |
| `ASSET_DECLARED` | `year`, `total_value`, `document_url` | LHKPN declaration |

**Example**:
```cypher
(:Company {name: "PT Mas'ud Construction"})-[WON_TENDER {amount: 95000000000, date: "2024-02-15"}]->(:Budget {id: "APBD-KALTIM-2024-001"})
```

---

### Document Relationships

| Relationship | Properties | Description |
|--------------|------------|-------------|
| `MENTIONED_IN` | `count`, `sentiment` (-1.0 to +1.0) | Entity mentioned in document |
| `SOURCE_FOR` | `relevance_score`, `extracted_date` | Document as evidence source |

**Example**:
```cypher
(:Document {url: "https://news.com/..."})-[SOURCE_FOR {relevance_score: 0.95}]->(:Person {name: "Rudy Mas'ud"})
```

---

## Time-Series Data (InfluxDB)

### Measurement: `wealth_history`

| Field | Type | Description |
|-------|------|-------------|
| `total_assets` | Integer | Total declared assets (IDR) |
| `cash` | Integer | Cash and equivalents |
| `real_estate` | Integer | Property values |
| `vehicles` | Integer | Vehicle values |
| `investments` | Integer | Stock and bond holdings |
| `other` | Integer | Other assets |

**Tags**: `person_slug`, `year`, `source` (LHKPN)

---

### Measurement: `budget_execution`

| Field | Type | Description |
|-------|------|-------------|
| `allocated` | Integer | Budget allocated |
| `realized` | Integer | Budget realized |
| `rate` | Float | Realization rate |

**Tags**: `region`, `year`, `category`

---

### Measurement: `sentiment_scores`

| Field | Type | Description |
|-------|------|-------------|
| `positive` | Float | Positive sentiment ratio |
| `negative` | Float | Negative sentiment ratio |
| `neutral` | Float | Neutral sentiment ratio |
| `overall` | Float | Overall sentiment (-1.0 to +1.0) |

**Tags**: `person_slug`, `source_type` (News, Social Media)

---

### Measurement: `relationship_strength`

| Field | Type | Description |
|-------|------|-------------|
| `strength` | Float | Relationship strength (0.0-1.0) |
| `interaction_count` | Integer | Number of interactions |

**Tags**: `person1_slug`, `person2_slug`, `relationship_type`

---

## Enumerations

### Legal Status
- `INVESTIGATION`: Under investigation
- `SUSPECT`: Named as suspect
- `DEFENDANT`: Charged in court
- `CONVICTED`: Found guilty
- `ACQUITTED`: Found not guilty
- `APPEAL`: Under appeal
- `FINAL`: Final verdict

### Risk Levels
- `LOW`: 0.0 - 0.3
- `MEDIUM`: 0.3 - 0.6
- `HIGH`: 0.6 - 0.8
- `CRITICAL`: 0.8 - 1.0

### Government Levels
- `NATIONAL`: National level (President, Minister, DPR)
- `PROVINCIAL`: Provincial level (Governor, DPRD Provinsi)
- `REGIONAL`: Regency/City level (Bupati/Walikota, DPRD Kota)
- `DISTRICT`: District level (Camat)
- `VILLAGE`: Village level (Kepala Desa)

### Company Status
- `ACTIVE`: Currently operating
- `INACTIVE`: Not operating
- `DISSOLVED`: Legally dissolved
- `MERGED`: Merged with another company

---

**Version**: 2.0.0  
**Last Updated**: 2024
