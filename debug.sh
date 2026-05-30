#!/bin/bash
# CROSSROAD — Debug & Auto-Fix Script
# Run: bash debug.sh
# It reads your actual logs and tells you exactly what to fix.

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
info() { echo -e "  ${BLUE}→${NC} $1"; }

echo ""
echo -e "${BLUE}══════════════════════════════════════${NC}"
echo -e "${BLUE}  CROSSROAD Debug & Auto-Fix${NC}"
echo -e "${BLUE}══════════════════════════════════════${NC}"
echo ""

# ── 1. Check Docker ──────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Docker${NC}"
if ! command -v docker &>/dev/null; then
    fail "Docker not found. Install Docker Desktop first."
    exit 1
fi
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"

# ── 2. Container status ──────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[2/6] Container Status${NC}"
declare -A CONTAINER_STATUS
for name in crossroad_backend crossroad_neo4j crossroad_postgres crossroad_redis crossroad_chroma crossroad_ollama crossroad_frontend; do
    status=$(docker inspect --format='{{.State.Status}}' "$name" 2>/dev/null || echo "missing")
    health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$name" 2>/dev/null || echo "missing")
    CONTAINER_STATUS[$name]="$status/$health"

    short="${name#crossroad_}"
    if [ "$status" = "running" ] && [ "$health" != "unhealthy" ]; then
        ok "$short: $status ($health)"
    elif [ "$status" = "missing" ]; then
        warn "$short: not created"
    else
        fail "$short: $status ($health)"
    fi
done

# ── 3. Backend specific diagnosis ────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[3/6] Backend Diagnosis${NC}"

BACKEND_STATUS="${CONTAINER_STATUS[crossroad_backend]}"

if [[ "$BACKEND_STATUS" == "missing"* ]]; then
    fail "Backend container not created. Run: docker compose up -d backend"

elif [[ "$BACKEND_STATUS" == *"exited"* ]] || [[ "$BACKEND_STATUS" == *"Exit"* ]]; then
    fail "Backend CRASHED. Reading error..."
    echo ""
    echo -e "${RED}══ Backend error log ══${NC}"
    docker compose logs backend --tail=30 2>/dev/null | grep -E "(ERROR|error|Traceback|ModuleNotFound|ImportError|Exception|Cannot|Failed)" | tail -10
    echo ""

    # Detect specific errors
    LOGS=$(docker compose logs backend --tail=50 2>/dev/null)

    if echo "$LOGS" | grep -q "ModuleNotFoundError\|ImportError\|No module named"; then
        warn "Python import error detected!"
        BAD_MODULE=$(echo "$LOGS" | grep -oP "No module named '\K[^']+")
        if [ -n "$BAD_MODULE" ]; then
            info "Missing module: $BAD_MODULE"
        fi
        echo ""
        info "FIX: Rebuild the backend image:"
        echo "       docker compose build backend --no-cache"
        echo "       docker compose up -d backend"

    elif echo "$LOGS" | grep -q "Neo4j\|ServiceUnavailable\|bolt://"; then
        warn "Neo4j connection failed. Neo4j may not be ready."
        info "FIX: Wait 2 minutes for Neo4j, then restart backend:"
        echo "       docker compose restart backend"

    elif echo "$LOGS" | grep -q "asyncpg\|PostgreSQL\|postgres"; then
        warn "PostgreSQL connection failed."
        info "FIX:"
        echo "       docker compose restart postgres"
        echo "       docker compose restart backend"

    elif echo "$LOGS" | grep -q "redis\|Redis"; then
        warn "Redis connection failed."
        info "FIX:"
        echo "       docker compose restart redis"
        echo "       docker compose restart backend"

    else
        info "Full backend logs:"
        docker compose logs backend --tail=40
    fi

elif [[ "$BACKEND_STATUS" == *"restarting"* ]]; then
    warn "Backend is stuck in restart loop. Reading why..."
    docker compose logs backend --tail=20 2>/dev/null

else
    # Backend is running — test HTTP
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        ok "Backend HTTP responding on port 8000"
        HEALTH=$(curl -s http://localhost:8000/health)
        echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
    else
        fail "Backend running but NOT responding on port 8000"
        info "Check if another process is using port 8000:"
        echo "       lsof -i :8000"
    fi
fi

# ── 4. Test backend from inside Docker network ───────────────────────────────
echo ""
echo -e "${YELLOW}[4/6] Network Connectivity Test${NC}"

# Test if frontend can reach backend by hostname
if docker ps | grep -q crossroad_frontend; then
    RESULT=$(docker exec crossroad_frontend curl -sf --connect-timeout 3 http://backend:8000/health 2>&1)
    if echo "$RESULT" | grep -q '"status"'; then
        ok "Frontend → backend:8000 connection works"
    else
        fail "Frontend CANNOT reach backend:8000"
        info "They may be on different Docker networks"
        info "FIX: docker compose down && docker compose up -d"
    fi
fi

# ── 5. Port mapping ───────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[5/6] Port Mapping${NC}"
for port in 3000 8000 7474 6379 8001 11434; do
    container=$(docker ps --format "{{.Names}}: {{.Ports}}" 2>/dev/null | grep ":${port}->" | head -1)
    if [ -n "$container" ]; then
        ok "Port $port → $container"
    else
        warn "Port $port not mapped to any running container"
    fi
done

# ── 6. Auto-fix summary ───────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}[6/6] Recommended Actions${NC}"

ALL_RUNNING=true
for name in crossroad_backend crossroad_neo4j crossroad_postgres crossroad_redis crossroad_chroma; do
    status="${CONTAINER_STATUS[$name]}"
    if [[ ! "$status" == "running"* ]]; then
        ALL_RUNNING=false
        break
    fi
done

if [ "$ALL_RUNNING" = true ]; then
    HEALTH_RESULT=$(curl -s http://localhost:8000/health 2>/dev/null)
    if echo "$HEALTH_RESULT" | grep -q '"status": "ok"'; then
        ok "Everything looks healthy!"
        echo ""
        info "Open the app: http://localhost:$(grep FRONTEND_PORT .env 2>/dev/null | cut -d= -f2 || echo 3000)"
    else
        warn "Containers running but backend not responding."
        echo ""
        echo -e "${YELLOW}Try:${NC}"
        echo "  docker compose restart backend"
        echo "  docker compose logs backend -f"
    fi
else
    echo ""
    echo -e "${YELLOW}Start with correct order:${NC}"
    echo ""
    echo "  # Step 1: Start databases"
    echo "  docker compose up -d neo4j postgres redis chromadb"
    echo ""
    echo "  # Step 2: Wait 30 seconds for databases to be ready"
    echo "  sleep 30"
    echo ""
    echo "  # Step 3: Start backend"
    echo "  docker compose up -d backend"
    echo ""
    echo "  # Step 4: Watch backend start"
    echo "  docker compose logs backend -f"
    echo ""
    echo "  # Step 5: Once backend is up, start frontend"
    echo "  docker compose up -d frontend"
    echo ""
    echo "  # Step 6: Start Ollama (optional, for LLM features)"
    echo "  docker compose up -d ollama ollama-init"
fi

echo ""
echo -e "${BLUE}══════════════════════════════════════${NC}"
