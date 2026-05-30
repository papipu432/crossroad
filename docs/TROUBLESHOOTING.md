# CROSSROAD Troubleshooting Guide

## Common Issues & Solutions

### Installation Issues

#### Docker Compose Fails to Start

**Error**: `Cannot start service backend: driver failed programming external connectivity`

**Solution**:
```bash
# Check if ports are in use
lsof -i :8000
lsof -i :3000
lsof -i :7687

# Kill conflicting processes
kill -9 <PID>

# Or change ports in docker-compose.yml
# Restart
docker compose up -d
```

#### Neo4j Won't Start

**Error**: `Neo4j failed to start: insufficient memory`

**Solution**:
```bash
# Reduce heap size in .env
NEO4J_dbms_memory_heap_max__size=2G

# Clear old data (WARNING: deletes all data!)
docker compose down
rm -rf neo4j_data/
docker compose up -d neo4j
```

#### Python Dependencies Fail

**Error**: `ERROR: Could not find a version that satisfies the requirement`

**Solution**:
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Clear cache
pip cache purge

# Install from requirements
pip install -r requirements.txt --no-cache-dir

# If specific package fails, install separately
pip install <package_name>==<version>
```

### Scraper Issues

#### Wikipedia Scraper Blocked

**Error**: `HTTP 429 Too Many Requests`

**Solution**:
```bash
# Add delay in crawler/base.py
import asyncio
await asyncio.sleep(2)  # Add between requests

# Use rotating proxies
# Update PROXY_LIST in .env
PROXY_LIST=["proxy1:port", "proxy2:port"]

# Reduce concurrent requests
MAX_CONCURRENT_REQUESTS=5
```

#### LHKPN PDF Download Fails

**Error**: `SSL Certificate Error` or `Connection Timeout`

**Solution**:
```bash
# Disable SSL verification (development only!)
# In crawler/enhanced_sources.py:
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Add retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def download_lhkpn():
    ...
```

#### News Scraper Returns Empty Results

**Error**: No articles extracted

**Solution**:
```bash
# Check website structure changed
# Inspect HTML manually
curl https://news-site.com/article | grep "<title>"

# Update selectors in crawler/news.py
# Example: OLD: soup.select(".article-title")
#          NEW: soup.select("h1.headline")

# Test scraper
python -m backend.crawler.news --test
```

### Database Issues

#### Neo4j Query Timeout

**Error**: `Query execution timed out`

**Solution**:
```cypher
// Optimize query with indexes
CREATE INDEX FOR (p:Person) ON (p.slug);

// Use EXPLAIN to analyze
EXPLAIN MATCH (p:Person)-[*..5]-(c:Company) 
RETURN p, c;

// Limit results
MATCH (p:Person) RETURN p LIMIT 100;

// Increase timeout in Neo4j config
dbms.transaction.timeout=300
```

#### ChromaDB Connection Refused

**Error**: `Connection refused to localhost:8001`

**Solution**:
```bash
# Check if ChromaDB is running
docker compose ps chromadb

# Restart service
docker compose restart chromadb

# Check logs
docker compose logs chromadb

# Verify port mapping
netstat -tlnp | grep 8001
```

#### PostgreSQL Locks

**Error**: `could not obtain lock on row`

**Solution**:
```sql
-- Find blocking queries
SELECT pid, usename, query, state, wait_event_type
FROM pg_stat_activity
WHERE state != 'idle';

-- Terminate blocking query
SELECT pg_terminate_backend(<pid>);

-- Vacuum database
VACUUM ANALYZE;
```

### API Issues

#### 401 Unauthorized

**Error**: `{"detail": "Not authenticated"}`

**Solution**:
```bash
# Check JWT token validity
# Token might be expired

# Refresh token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <old_token>"

# Login again
curl -X POST http://localhost:8000/api/auth/login \
  -d '{"username": "admin", "password": "..."}'
```

#### Rate Limit Exceeded

**Error**: `{"detail": "Rate limit exceeded"}`

**Solution**:
```bash
# Wait for reset (usually 1 minute)
# Check rate limit headers
curl -I http://localhost:8000/api/person/prabowo-subianto

# Headers show:
# X-RateLimit-Limit: 100
# X-RateLimit-Remaining: 0
# X-RateLimit-Reset: 1640000060

# For higher limits, use authenticated endpoint
# Or request API key upgrade
```

#### Natural Language Query Returns Wrong Results

**Error**: Query misunderstood or returns irrelevant data

**Solution**:
```bash
# Rephrase query more specifically
# Bad: "Show me politicians"
# Good: "List all governors in Java island"

# Check RAG context
# Add more relevant documents to ChromaDB

# Fine-tune LLM prompt in main.py
# Adjust temperature parameter (lower = more deterministic)
```

### Performance Issues

#### Slow Dashboard Loading

**Symptoms**: Graph takes >10 seconds to render

**Solution**:
```javascript
// Frontend: Limit nodes displayed
const MAX_NODES = 100;
const filteredData = data.slice(0, MAX_NODES);

// Enable pagination
// Implement virtual scrolling for large lists

// Backend: Add caching
@cache.cached(timeout=300)
def get_graph_data():
    ...
```

#### High Memory Usage

**Symptoms**: Container using >90% memory

**Solution**:
```bash
# Identify memory leaks
docker stats

# Restart memory-heavy services
docker compose restart backend

# Increase memory limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 4G
```

#### Disk Space Full

**Symptoms**: `No space left on device`

**Solution**:
```bash
# Check disk usage
df -h
du -sh /var/lib/docker/*

# Clean Docker
docker system prune -a

# Remove old logs
find /var/log -name "*.log" -mtime +30 -delete

# Expand disk or add storage
```

### Scheduler Issues

#### Tasks Not Running

**Symptoms**: Scheduled jobs not executing

**Solution**:
```bash
# Check scheduler status
curl http://localhost:8000/api/scheduler/status

# Restart scheduler
docker compose restart scheduler

# Check Redis connection
redis-cli ping

# View scheduled jobs
curl http://localhost:8000/api/scheduler/jobs

# Manually trigger job
curl -X POST http://localhost:8000/api/scheduler/trigger/daily_news
```

#### Progress Stuck at 0%

**Symptoms**: Mining progress doesn't advance

**Solution**:
```bash
# Check for errors in logs
docker compose logs backend | grep ERROR

# Clear stuck tasks in Redis
redis-cli DEL task_queue

# Restart mining agent
curl -X POST http://localhost:8000/api/agent/restart

# Check entity resolver for infinite loops
# Add timeout to recursive functions
```

### Frontend Issues

#### Blank Page After Login

**Symptoms**: White screen, console errors

**Solution**:
```javascript
// Check browser console for errors
// Common: API endpoint mismatch

// Update frontend/.env
REACT_APP_API_URL=http://localhost:8000

// Clear browser cache
// Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

// Rebuild frontend
cd frontend
npm run build
```

#### Graph Not Rendering

**Symptoms**: Empty graph area

**Solution**:
```javascript
// Check D3.js data format
// Should be: {nodes: [], links: []}

// Verify Neo4j query returns data
MATCH (n) RETURN n LIMIT 10;

// Check browser console for JavaScript errors
// Increase container size
// Disable browser extensions temporarily
```

### ML Service Issues

#### Prediction Model Returns NaN

**Error**: `Prediction result is NaN`

**Solution**:
```python
# Check input data for nulls
if pd.isnull(input_data).any():
    input_data = input_data.fillna(0)

# Verify model file exists
import os
if not os.path.exists('model.pkl'):
    raise Exception("Model file not found")

# Retrain model
python -m backend.ml_service.train
```

#### OCR Quality Poor

**Symptoms**: Text extraction inaccurate

**Solution**:
```python
# Preprocess image
from PIL import Image, ImageEnhance

image = Image.open(pdf_path)
image = ImageEnhance.Contrast(image).enhance(2.0)
image = image.convert('1')  # Binarize

# Use better OCR engine
# Install Tesseract with training data
# Configure language: ind (Indonesian)

# Post-process with spell checker
from spellchecker import SpellChecker
spell = SpellChecker(language='id')
```

## Debugging Tools

### Backend Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Python debugger
import pdb; pdb.set_trace()

# Profile performance
python -m cProfile -o output.prof backend/main.py

# Memory profiling
python -m memory_profiler backend/main.py
```

### Frontend Debugging

```javascript
// React DevTools
// Install Chrome extension

// Network tab
// Check API responses

// Console logging
console.log('State:', state);

// Performance tab
// Record timeline for slow renders
```

### Database Debugging

```bash
# Neo4j Browser
open http://localhost:7474

# Query logging
MATCH (n) RETURN n LIMIT 10;

# Explain query plan
EXPLAIN MATCH (p:Person) RETURN p;

# Monitor connections
SHOW TRANSACTIONS;
```

## Getting Help

If issues persist:

1. **Check Logs**: `docker compose logs -f`
2. **Search Issues**: GitHub Issues tab
3. **Documentation**: See other docs in `/docs` folder
4. **Contact**: support@crossroad.id

---

**Version**: 2.0.0  
**Last Updated**: 2024
