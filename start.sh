#!/bin/bash
# NovaSaaS Customer Success AI System - Startup Script
# Usage: ./start.sh [dev|prod]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   NovaSaaS Customer Success AI System                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys before starting.${NC}"
    echo ""
fi

# Default mode
MODE=${1:-dev}

if [ "$MODE" = "dev" ]; then
    echo -e "${GREEN}🚀 Starting development stack...${NC}"
    echo ""
    
    # Start all services
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}✅ Services started!${NC}"
    echo ""
    echo "Service URLs:"
    echo -e "  ${GREEN}Frontend:${NC}  http://localhost:3000"
    echo -e "  ${GREEN}Backend:${NC}   http://localhost:8000"
    echo -e "  ${GREEN}Backend API:${NC} http://localhost:8000/docs"
    echo -e "  ${GREEN}Agent:${NC}     http://localhost:8001"
    echo ""
    echo "Database:"
    echo -e "  ${GREEN}PostgreSQL:${NC} localhost:5432 (novasaas/novasaas)"
    echo -e "  ${GREEN}Kafka:${NC}      localhost:9092"
    echo -e "  ${GREEN}Redis:${NC}      localhost:6379"
    echo ""
    echo "To view logs:"
    echo "  docker-compose logs -f [service]"
    echo ""
    echo "To stop:"
    echo "  docker-compose down"
    
elif [ "$MODE" = "prod" ]; then
    echo -e "${GREEN}🚀 Starting production stack...${NC}"
    echo ""
    
    # Build all services
    docker-compose -f docker-compose.yml build
    
    # Start all services
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}✅ Production services started!${NC}"
    
else
    echo -e "${RED}❌ Unknown mode: $MODE${NC}"
    echo "Usage: ./start.sh [dev|prod]"
    exit 1
fi
