# CROSSROAD — Troubleshooting Guide

## 504 Gateway Timeout on /health

The frontend gets 504 when the backend container isn't running yet.

### Quick diagnosis
```bash
# See what's actually running
docker compose ps

# Read backend logs
docker compose logs backend --tail=50

# Test backend directly (bypasses nginx)
curl http://localhost:8000/health
```

### Most common causes

---

#### 1. Backend crashed on startup (most likely)

**Symptom:** `docker compose ps` shows `crossroad_backend` as `Exit 1`

**Read the actual error:**
```bash
docker compose logs backend --tail=30
```

**Common errors and fixes:**

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'intelligence'` | `docker compose build backend && docker compose up -d backend` |
| `ModuleNotFoundError: No module named 'slugify'` | Same as above — rebuild image |
| `Can't connect to Neo4j` | Wait 2 min, then `docker compose restart backend` |
| `Port 8000 already in use` | Change `BACKEND_PORT=8001` in `.env` |

---

#### 2. Neo4j hasn't finished starting (very common on first boot)

Neo4j takes **60-90 seconds** to be ready. Backend starts, can't connect, crashes.

**Fix:**
```bash
# Wait until neo4j is healthy
docker compose ps   # check neo4j shows "healthy"

# Then restart backend
docker compose restart backend

# Watch it start
docker compose logs backend -f
```

---

#### 3. ChromaDB image not pulled yet

```bash
docker compose logs chromadb --tail=20
```

If it shows pull errors:
```bash
docker pull chromadb/chroma:latest
docker compose up -d chromadb
docker compose restart backend
```

---

#### 4. Ollama model still downloading

The `qwen2.5:7b` model is ~4.7 GB. First boot can take **5-15 minutes**.

The backend now starts WITHOUT waiting for Ollama — so this shouldn't cause 504 anymore.

Check progress:
```bash
docker compose logs ollama-init -f
```

---

#### 5. Port 13001 vs 3000

The error shows `localhost:13001` — that means the `.env` has `FRONTEND_PORT=13001`.
Make sure you're accessing the correct port.

Check:
```bash
cat .env | grep FRONTEND_PORT
docker compose ps   # shows the port mapping
```

---

### Full clean restart

```bash
# Stop everything
docker compose down

# Start in correct order
./startup.sh up

# Or manually:
docker compose up -d neo4j postgres redis chromadb
sleep 30
docker compose up -d backend
sleep 10
docker compose up -d frontend ollama ollama-init
```

---

### Check all services are healthy

```bash
./startup.sh status
```

Or manually:
```bash
# Neo4j
curl http://localhost:7474

# Backend
curl http://localhost:8000/health | python3 -m json.tool

# Redis
docker compose exec redis redis-cli ping

# ChromaDB
curl http://localhost:8001/api/v1/heartbeat

# Ollama
curl http://localhost:11434/api/tags
```

---

### Memory issues (if you have < 8GB RAM)

The stack needs approximately:
- Neo4j: 2GB
- Ollama + qwen2.5:7b: 5GB
- Backend: 500MB
- Everything else: ~1GB

**If you have 8GB RAM total**, reduce Neo4j memory in `docker-compose.yml`:
```yaml
NEO4J_dbms_memory_heap_max__size: "1G"    # was 2G
NEO4J_dbms_memory_pagecache_size: "256m"  # was 512m
```

Or use a smaller model:
```bash
# In .env:
OLLAMA_MODEL=qwen2.5:3b   # half the size
```

---

### After any code change to backend

```bash
docker compose build backend
docker compose up -d backend
```

The `--reload` flag in uvicorn means Python code changes in `./backend/` 
auto-reload without rebuild. But Dockerfile changes need a full rebuild.

---

### Logs for each service

```bash
docker compose logs backend   --tail=50 -f
docker compose logs neo4j     --tail=30
docker compose logs postgres  --tail=20
docker compose logs redis     --tail=10
docker compose logs chromadb  --tail=20
docker compose logs ollama    --tail=20
docker compose logs frontend  --tail=20
```
