#!/bin/bash
# Smoke test for RAE Lite Profile
# Tests basic functionality of docker-compose.lite.yml

set -e

echo "🧪 RAE Lite Profile Smoke Test"
echo "================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}❌ docker compose not found${NC}"
    exit 1
fi

echo "✅ docker compose found"

# Validate YAML syntax
echo -n "Validating docker-compose.lite.yml syntax... "
if docker compose -f docker-compose.lite.yml config > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Valid${NC}"
else
    echo -e "${RED}❌ Invalid${NC}"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env and add your LLM API key${NC}"
    exit 1
fi

echo "✅ .env file exists"

# Start services
echo ""
echo "🚀 Starting RAE Lite services..."
docker compose -f docker-compose.lite.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check if services are running
echo ""
echo "Checking service status:"
SERVICES=$(docker compose -f docker-compose.lite.yml ps --services)
for service in $SERVICES; do
    STATUS=$(docker compose -f docker-compose.lite.yml ps -q $service | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not found")
    if [ "$STATUS" = "running" ]; then
        echo -e "  ${GREEN}✅${NC} $service: running"
    else
        echo -e "  ${RED}❌${NC} $service: $STATUS"
    fi
done

# Port configuration
API_PORT="${RAE_LITE_PORT:-8002}"
API_URL="http://localhost:${API_PORT}"
TENANT_ID="00000000-0000-0000-0000-000000000000"

# Wait for API to be ready
echo ""
echo "⏳ Waiting for API to be ready on ${API_URL}..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s ${API_URL}/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -n "."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}❌ API failed to start within timeout${NC}"
    docker compose -f docker-compose.lite.yml logs rae-api-lite
    exit 1
fi

# Test health endpoint
echo ""
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s ${API_URL}/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi

# Test API endpoints
echo ""
echo "Testing API endpoints..."

# Test store memory
echo -n "  Testing POST /v1/memory/store... "
STORE_RESPONSE=$(curl -s -X POST ${API_URL}/v1/memory/store \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: ${TENANT_ID}" \
    -H "X-API-Key: secret" \
    -d '{
        "content": "Smoke test memory",
        "source": "smoke-test",
        "layer": "em",
        "importance": 0.5
    }' 2>&1)

if echo "$STORE_RESPONSE" | grep -q '"id"'; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    echo "Response: $STORE_RESPONSE"
fi

# Test query memory
echo -n "  Testing POST /v1/memory/query... "
QUERY_RESPONSE=$(curl -s -X POST ${API_URL}/v1/memory/query \
    -H "Content-Type: application/json" \
    -H "X-Tenant-Id: ${TENANT_ID}" \
    -H "X-API-Key: secret" \
    -d '{
        "query_text": "smoke test",
        "k": 5
    }' 2>&1)

if echo "$QUERY_RESPONSE" | grep -q '"results"'; then
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${RED}❌${NC}"
    echo "Response: $QUERY_RESPONSE"
fi

# Summary
echo ""
echo "================================"
echo -e "${GREEN}✅ RAE Lite Profile smoke test PASSED${NC}"
echo ""
echo "Services running:"
echo "  - API: ${API_URL}"
echo "  - API Docs: ${API_URL}/docs"
echo "  - PostgreSQL: localhost:5434"
echo "  - Qdrant: localhost:6335"
echo "  - Redis: localhost:6380"
