#!/bin/bash
# CROSSROAD — Startup & Diagnostics Script
# Run: ./startup.sh [up|down|logs|status|reset]

set -e
COMPOSE="docker compose"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   🇮🇩  CROSSROAD Knowledge Graph         ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""
}

check_status() {
    echo -e "${YELLOW}═══ Service Status ═══${NC}"
    $COMPOSE ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || $COMPOSE ps
    echo ""
}

wait_for_backend() {
    echo -e "${YELLOW}Waiting for backend to start...${NC}"
    local max=60
    local i=0
    while [ $i -lt $max ]; do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Backend is up!${NC}"
            curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8000/health
            return 0
        fi
        echo -n "."
        sleep 2
        i=$((i+1))
    done
    echo ""
    echo -e "${RED}✗ Backend did not start after ${max}s. Check logs:${NC}"
    echo "  docker compose logs backend --tail=50"
    return 1
}

diagnose() {
    echo -e "${YELLOW}═══ Diagnosing issues ═══${NC}"

    echo ""
    echo -e "${BLUE}Backend logs (last 30 lines):${NC}"
    $COMPOSE logs backend --tail=30 2>/dev/null || echo "Backend container not found"

    echo ""
    echo -e "${BLUE}Container health:${NC}"
    for svc in crossroad_backend crossroad_neo4j crossroad_postgres crossroad_redis crossroad_chroma crossroad_ollama; do
        status=$(docker inspect --format='{{.State.Health.Status}}' $svc 2>/dev/null || echo "not found")
        case $status in
            healthy)   echo -e "  ${GREEN}✓${NC} $svc: $status" ;;
            unhealthy) echo -e "  ${RED}✗${NC} $svc: $status" ;;
            starting)  echo -e "  ${YELLOW}⟳${NC} $svc: $status" ;;
            *)         echo -e "  ${RED}?${NC} $svc: $status" ;;
        esac
    done

    echo ""
    echo -e "${BLUE}Direct backend test:${NC}"
    if curl -sf http://localhost:8000/health; then
        echo -e "${GREEN}Backend responding${NC}"
    else
        echo -e "${RED}Backend NOT responding on port 8000${NC}"
        echo ""
        echo -e "${YELLOW}Common fixes:${NC}"
        echo "  1. Python import error  → docker compose logs backend --tail=50"
        echo "  2. Neo4j not ready      → wait 2 min then: docker compose restart backend"
        echo "  3. Port conflict        → change BACKEND_PORT in .env"
        echo "  4. First boot (Ollama)  → model download takes 5-10min, backend starts anyway"
    fi
}

cmd=${1:-"up"}

case $cmd in
    up)
        print_header
        # Ensure .env exists
        if [ ! -f .env ]; then
            echo -e "${YELLOW}Creating .env from .env.example${NC}"
            cp .env.example .env
        fi

        echo -e "${YELLOW}Starting services (this may take 2-5 min on first boot)...${NC}"
        echo ""

        # Start core infra first (without ollama dependency)
        $COMPOSE up -d neo4j postgres redis chromadb
        echo -e "${YELLOW}Waiting for databases (30s)...${NC}"
        sleep 30

        # Start backend (doesn't need ollama)
        $COMPOSE up -d backend
        echo ""

        # Start ollama in background (model download may take a while)
        echo -e "${YELLOW}Starting Ollama (model download happens in background)...${NC}"
        $COMPOSE up -d ollama ollama-init

        # Wait for backend
        wait_for_backend

        echo ""
        echo -e "${YELLOW}Starting frontend...${NC}"
        $COMPOSE up -d frontend

        echo ""
        echo -e "${GREEN}═══ CROSSROAD is running! ═══${NC}"
        echo ""
        echo -e "  Frontend:     ${BLUE}http://localhost:${FRONTEND_PORT:-3000}${NC}"
        echo -e "  API Docs:     ${BLUE}http://localhost:${BACKEND_PORT:-8000}/docs${NC}"
        echo -e "  Neo4j:        ${BLUE}http://localhost:${NEO4J_BROWSER_PORT:-7474}${NC}"
        echo -e "  ChromaDB:     ${BLUE}http://localhost:${CHROMA_PORT:-8001}${NC}"
        echo ""
        echo -e "${YELLOW}Note: Ollama model download continues in background.${NC}"
        echo -e "Check status: ${BLUE}docker compose logs ollama-init -f${NC}"
        ;;

    down)
        echo -e "${YELLOW}Stopping CROSSROAD...${NC}"
        $COMPOSE down
        echo -e "${GREEN}Done.${NC}"
        ;;

    restart-backend)
        echo -e "${YELLOW}Restarting backend...${NC}"
        $COMPOSE restart backend
        wait_for_backend
        ;;

    logs)
        $COMPOSE logs ${2:-backend} -f --tail=50
        ;;

    status)
        print_header
        check_status
        diagnose
        ;;

    reset)
        echo -e "${RED}WARNING: This will delete all data (Neo4j, Postgres, Redis, Chroma)${NC}"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            $COMPOSE down -v
            echo -e "${GREEN}All volumes deleted. Run ./startup.sh up to start fresh.${NC}"
        else
            echo "Cancelled."
        fi
        ;;

    *)
        echo "Usage: ./startup.sh [up|down|restart-backend|logs [service]|status|reset]"
        ;;
esac
