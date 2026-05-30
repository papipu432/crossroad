# CROSSROAD Developer Guide

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development

```bash
# Clone repository
git clone https://github.com/your-org/crossroad.git
cd crossroad

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements-dev.txt

# Install frontend dependencies
cd frontend
npm install

# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Start development services
docker compose up -d neo4j chromadb postgres redis

# Run backend in development mode
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run frontend in development mode
cd frontend
npm run dev
```

### Environment Variables

```bash
# Database
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

POSTGRES_URL=postgresql://postgres:password@localhost:5432/crossroad

REDIS_URL=redis://localhost:6379/0

CHROMADB_URL=http://localhost:8001

# LLM (Ollama)
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b

# Security
JWT_SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Scheduler
ENABLE_SCHEDULER=true
SCHEDULER_TIMEZONE=Asia/Jakarta

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
```

## Running Tests

```bash
# Run all tests
pytest backend/tests/ -v

# Run specific test
pytest backend/tests/test_masud_dynasty.py -v

# Run with coverage
pytest --cov=backend backend/tests/

# Run frontend tests
cd frontend
npm test
```

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Docstrings for all public functions
- Maximum line length: 100 characters

```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/
pylint backend/

# Type checking
mypy backend/
```

### TypeScript/JavaScript

- ESLint configuration provided
- Prettier for formatting
- Strict TypeScript mode

```bash
cd frontend
npm run lint
npm run format
```

## Making Contributions

### Branch Naming

```
feature/add-new-scraper
bugfix/fix-wikipedia-parsing
docs/update-api-docs
test/add-oligarchy-tests
```

### Commit Messages

```
feat: add LPSE scraper for procurement tracking
fix: correct wealth anomaly detection threshold
docs: update API cookbook with new examples
test: add Mas'ud dynasty detection tests
refactor: optimize Neo4j queries for performance
```

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Ensure all tests pass
5. Update documentation
6. Submit PR with description
7. Address review comments
8. Merge after approval

## Debugging

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Use Python debugger
import pdb; pdb.set_trace()

# Neo4j query logging
export NEO4J_LOG_QUERIES=true
```

### Frontend Debugging

```bash
# React DevTools
# Install browser extension

# Network debugging
# Open browser DevTools → Network tab

# State debugging
# Use Redux DevTools if applicable
```

### Database Debugging

```bash
# Neo4j Browser
open http://localhost:7474

# Query example
MATCH (p:Person)-[:OWNS_SHARES]->(c:Company)
WHERE p.name CONTAINS "Mas'ud"
RETURN p, c

# PostgreSQL
psql -h localhost -U postgres -d crossroad

# Redis CLI
redis-cli
```

## Adding New Data Sources

### Step 1: Create Scraper Class

```python
# backend/crawler/new_source.py
from .base import BaseScraper

class NewSourceScraper(BaseScraper):
    async def scrape(self, entity: Person) -> dict:
        # Implement scraping logic
        pass
    
    async def extract_relationships(self, content: str) -> list:
        # Extract relationships from content
        pass
```

### Step 2: Register Scraper

```python
# backend/crawler/__init__.py
from .new_source import NewSourceScraper

SCRAPERS = {
    "new_source": NewSourceScraper,
    # ... other scrapers
}
```

### Step 3: Add to Scheduler

```python
# backend/scheduler.py
async def scrape_new_source():
    scraper = NewSourceScraper()
    await scraper.run_batch()
```

### Step 4: Write Tests

```python
# backend/tests/test_new_source.py
def test_new_source_scraper():
    scraper = NewSourceScraper()
    result = scraper.scrape(test_person)
    assert result is not None
```

## Performance Optimization

### Neo4j Queries

```cypher
// Bad: Full scan
MATCH (p:Person) WHERE p.name CONTAINS "Prabowo" RETURN p

// Good: Index usage
MATCH (p:Person) WHERE p.name = "Prabowo Subianto" RETURN p

// Better: With labels
MATCH (p:Person:Politician) WHERE p.name = "Prabowo Subianto" RETURN p
```

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_person_profile(slug: str) -> dict:
    # Expensive operation
    return profile
```

### Async Operations

```python
# Bad: Sequential
results = []
for url in urls:
    result = await fetch(url)
    results.append(result)

# Good: Parallel
tasks = [fetch(url) for url in urls]
results = await asyncio.gather(*tasks)
```

## Deployment

### Docker Build

```bash
# Build images
docker compose build

# Run production
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes (Future)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crossroad-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: backend
        image: crossroad/backend:latest
```

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues.

---

**Version**: 2.0.0  
**Last Updated**: 2024
