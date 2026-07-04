#!/usr/bin/env bash
set -e

# RAE Quickstart Script
# This script helps you get RAE up and running in under 5 minutes
# Usage: ./scripts/quickstart.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Banner
echo -e "${BLUE}"
cat << "EOF"
    ____  ___    ______
   / __ \/   |  / ____/
  / /_/ / /| | / __/
 / _, _/ ___ |/ /___
/_/ |_/_/  |_/_____/

Reflective Agentic Memory Engine
v1.0.0-beta
EOF
echo -e "${NC}"

log_info "Starting RAE Quickstart..."

# Step 1: Check Docker
log_info "Checking for Docker..."
if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    echo "Please start Docker and try again"
    exit 1
fi

log_success "Docker is installed and running"

# Step 2: Check docker compose
log_info "Checking for docker compose..."
if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
    log_error "docker compose is not installed"
    echo "Please install docker compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

# Determine which compose command to use
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker compose"
fi

log_success "docker compose is available"

# Step 3: Set up .env file
log_info "Setting up environment configuration..."

if [ -f ".env" ]; then
    log_warn ".env file already exists - keeping existing configuration"
else
    if [ ! -f ".env.example" ]; then
        log_error ".env.example not found!"
        exit 1
    fi

    cp .env.example .env
    log_success "Created .env from .env.example"

    # Prompt for API keys
    echo ""
    echo -e "${YELLOW}OPTIONAL: Configure LLM API Keys${NC}"
    echo "RAE can work with OpenAI, Anthropic, or Google Gemini."
    echo "You can add these keys later in the .env file."
    echo ""

    read -p "Do you want to configure an API key now? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Which LLM provider do you want to use?"
        echo "1) OpenAI (GPT-4, GPT-3.5)"
        echo "2) Anthropic (Claude)"
        echo "3) Google (Gemini)"
        echo "4) Skip for now"
        echo ""
        read -p "Enter choice (1-4): " -n 1 -r choice
        echo ""

        case $choice in
            1)
                echo -n "Enter your OpenAI API key (input hidden): "
                read -s api_key
                echo ""  # New line after enter
                if [ -n "$api_key" ]; then
                    sed -i "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
                    log_success "OpenAI API key configured"
                fi
                ;;
            2)
                echo -n "Enter your Anthropic API key (input hidden): "
                read -s api_key
                echo ""  # New line after enter
                if [ -n "$api_key" ]; then
                    sed -i "s/ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$api_key/" .env
                    log_success "Anthropic API key configured"
                fi
                ;;
            3)
                echo -n "Enter your Google Gemini API key (input hidden): "
                read -s api_key
                echo ""  # New line after enter
                if [ -n "$api_key" ]; then
                    sed -i "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$api_key/" .env
                    log_success "Google Gemini API key configured"
                fi
                ;;
            *)
                log_info "Skipping API key configuration"
                ;;
        esac
    fi

    # Set secure permissions on .env file (owner read/write only)
    if [ -f ".env" ]; then
        chmod 600 .env
        log_success "Secure permissions set on .env file (600)"
    fi
fi

# Step 4: Pull and build images
log_info "Pulling Docker images (this may take a few minutes on first run)..."
$COMPOSE_CMD pull -q || log_warn "Some images may need to be built locally"

log_info "Building RAE services..."
$COMPOSE_CMD build --quiet || {
    log_error "Build failed"
    exit 1
}

log_success "Images ready"

# Step 5: Start services
log_info "Starting RAE services..."
$COMPOSE_CMD up -d

# Step 6: Wait for health checks
log_info "Waiting for services to be healthy..."

MAX_WAIT=120
ELAPSED=0
INTERVAL=2

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check RAE API health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log_success "RAE API is healthy!"
        break
    fi

    echo -n "."
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    log_warn "Services are taking longer than expected to start"
    log_info "You can check the status with: $COMPOSE_CMD logs -f"
else
    # Step 7: Display access information
    echo ""
    echo -e "${GREEN}=================================${NC}"
    echo -e "${GREEN}  RAE is ready! 🚀${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo ""
    echo -e "📊 ${BLUE}Swagger API Documentation:${NC}"
    echo -e "   http://localhost:8000/docs"
    echo ""
    echo -e "📈 ${BLUE}Dashboard (Streamlit):${NC}"
    echo -e "   http://localhost:8501"
    echo ""
    echo -e "🔍 ${BLUE}Health Check:${NC}"
    echo -e "   http://localhost:8000/health"
    echo ""
    echo -e "📝 ${BLUE}Example cURL command:${NC}"
    echo -e '   curl -X POST http://localhost:8000/v1/memories \\'
    echo -e '     -H "Content-Type: application/json" \\'
    echo -e '     -d '"'"'{"content": "Hello RAE!", "tenant_id": "demo", "project": "quickstart"}'"'"
    echo ""
    echo -e "${YELLOW}💡 Tip:${NC} Run './scripts/seed_demo_data.py' to add sample memories"
    echo -e "${YELLOW}💡 Tip:${NC} View logs with: $COMPOSE_CMD logs -f"
    echo -e "${YELLOW}💡 Tip:${NC} Stop services with: $COMPOSE_CMD down"
    echo ""
fi

# Step 8: Show service status
log_info "Service status:"
$COMPOSE_CMD ps

exit 0
