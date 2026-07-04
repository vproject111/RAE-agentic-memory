#!/bin/bash
# scripts/install_mcp_service.sh
# Skrypt do instalacji usługi systemd dla rae-mcp-server

set -e

SERVICE_FILE="rae-mcp.service"
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_FILE"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
VENV_ACTIVATE="$PROJECT_ROOT/.venv/bin/activate"
MCP_SERVER_PATH="$PROJECT_ROOT/.venv/bin/rae-mcp-server"

echo "⚙️  Generating systemd service file for rae-mcp-server..."

mkdir -p "$(dirname "$SERVICE_PATH")"

cat << EOF > "$SERVICE_PATH"
[Unit]
Description=RAE MCP Server
After=network-online.target

[Service]
Type=simple
ExecStart=/bin/bash -c "source $VENV_ACTIVATE && $MCP_SERVER_PATH"
WorkingDirectory=$PROJECT_ROOT
Restart=on-failure
RestartSec=5s
Environment=RAE_API_URL=http://localhost:8000
Environment=RAE_API_KEY=dev-key
Environment=RAE_TENANT_ID=shared-agents
Environment=RAE_PROJECT_ID=$(basename "$PROJECT_ROOT")

[Install]
WantedBy=default.target
EOF

echo "✅ Service file created: $SERVICE_PATH"
echo "🚀 Enabling and starting rae-mcp.service..."

systemctl --user enable "$SERVICE_FILE"
systemctl --user start "$SERVICE_FILE"

echo "✅ rae-mcp-server systemd service enabled and started."
echo "ℹ️  To check status: systemctl --user status rae-mcp.service"
echo "ℹ️  To stop: systemctl --user stop rae-mcp.service"
echo "ℹ️  To disable: systemctl --user disable rae-mcp.service"
echo ""
echo "Note: If this is the first time you're using user-level systemd services,"
echo "you might need to run 'loginctl enable-linger $USER' once."
echo "This ensures user services continue to run after you log out."
