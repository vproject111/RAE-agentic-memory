#!/bin/bash
set -e

# RAE Agentic Memory - Developer Autostart Setup Script
# Configures a systemd user service to automatically start RAE in development mode (hot-reload) on boot.

PROJECT_DIR=$(pwd)
SERVICE_NAME="rae-dev"
SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME.service"
DOCKER_CMD=$(which docker)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Configuring RAE Developer Autostart...${NC}"

# Check for Docker
if [ -z "$DOCKER_CMD" ]; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

# Ensure systemd user directory exists
mkdir -p "$HOME/.config/systemd/user"

# Create systemd service file
echo -e "${BLUE}📝 Creating systemd service file at $SERVICE_FILE...${NC}"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=RAE Agentic Memory (Dev Mode)
After=docker.service network-online.target
Wants=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$PROJECT_DIR
ExecStart=$DOCKER_CMD compose -f docker-compose.yml -f docker-compose.dev.yml up -d
ExecStop=$DOCKER_CMD compose -f docker-compose.yml -f docker-compose.dev.yml stop

[Install]
WantedBy=default.target
EOF

# Reload systemd daemon
echo -e "${BLUE}🔄 Reloading systemd...${NC}"
systemctl --user daemon-reload

# Enable and start service
echo -e "${BLUE}🔌 Enabling and starting $SERVICE_NAME service...${NC}"
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

# Enable lingering for user (so service starts on boot without login)
if command -v loginctl &> /dev/null; then
    echo -e "${BLUE}👤 Enabling lingering for user $(whoami)...${NC}"
    loginctl enable-linger $(whoami)
fi

echo -e "${GREEN}✅ RAE Developer Autostart configured successfully!${NC}"
echo -e "   - Service: $SERVICE_NAME"
echo -e "   - Status: $(systemctl --user is-active $SERVICE_NAME)"
echo -e "   - Logs: journalctl --user -u $SERVICE_NAME -f"
echo -e "   - RAE API is now running at http://localhost:8000 with hot-reload enabled."
