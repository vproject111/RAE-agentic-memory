#!/bin/bash
set -e

echo "🗄️  Initializing RAE Database Schema..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if postgres container is running
if ! docker ps | grep -q rae-postgres; then
    echo -e "${RED}Error: PostgreSQL container (rae-postgres) is not running.${NC}"
    echo "Please start the containers first:"
    echo "  docker compose up -d"
    exit 1
fi

# Database connection settings
DB_USER=${POSTGRES_USER:-rae_user}
DB_NAME=${POSTGRES_DB:-rae_memory}

echo "Using DB User: $DB_USER"
echo "Using DB Name: $DB_NAME"

# Wait for postgres to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec rae-postgres pg_isready -U $DB_USER -d $DB_NAME > /dev/null 2>&1; then
        echo -e "${GREEN}PostgreSQL is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Error: PostgreSQL did not become ready in time.${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""

# Execute DDL files
echo -e "${YELLOW}Executing DDL scripts...${NC}"
for file in infra/postgres/ddl/*.sql; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo -n "  - $filename... "
        if docker exec -i rae-postgres psql -U $DB_USER -d $DB_NAME < "$file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ (may already exist)${NC}"
        fi
    fi
done

# Execute migration files
echo -e "${YELLOW}Executing migrations...${NC}"
for file in infra/postgres/migrations/*.sql; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        echo -n "  - $filename... "
        if docker exec -i rae-postgres psql -U $DB_USER -d $DB_NAME < "$file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
        else
            echo -e "${YELLOW}⚠ (may already exist)${NC}"
        fi
    fi
done

# Verify critical tables exist
echo -e "${YELLOW}Verifying database schema...${NC}"
TABLES=("memories" "shared_memories")
for table in "${TABLES[@]}"; do
    echo -n "  - Checking table '$table'... "
    if docker exec rae-postgres psql -U $DB_USER -d $DB_NAME -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table');" | grep -q 't'; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Missing!${NC}"
        echo -e "${RED}Error: Table '$table' was not created. Check the DDL scripts.${NC}"
        exit 1
    fi
done

# Add missing columns if needed
echo -e "${YELLOW}Checking for required columns...${NC}"
echo -n "  - Adding 'project' column to memories... "
docker exec rae-postgres psql -U $DB_USER -d $DB_NAME -c "ALTER TABLE memories ADD COLUMN IF NOT EXISTS project VARCHAR(255);" > /dev/null 2>&1
echo -e "${GREEN}✓${NC}"

echo -n "  - Adding 'created_at' column to memories... "
docker exec rae-postgres psql -U $DB_USER -d $DB_NAME -c "ALTER TABLE memories ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now();" > /dev/null 2>&1
docker exec rae-postgres psql -U $DB_USER -d $DB_NAME -c "UPDATE memories SET created_at = timestamp WHERE created_at IS NULL;" > /dev/null 2>&1
echo -e "${GREEN}✓${NC}"

echo ""
echo -e "${GREEN}✅ Database initialization complete!${NC}"
echo ""
echo "You can now restart the API service:"
echo "  docker compose restart rae-api"
echo ""
echo "Or restart all services:"
echo "  docker compose restart"
