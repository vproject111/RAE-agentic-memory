#!/bin/bash
# 🤖 RAE Multi-Agent Setup Script (Example)
#
# This is an EXAMPLE script. For actual use:
# 1. Copy to .local/setup-rae-mcp.sh
# 2. Customize configuration variables
# 3. Run: .local/setup-rae-mcp.sh
#
# Why .local/? It's gitignored - safe for your custom settings!

set -e

# Configuration - CUSTOMIZE THESE
RAE_API_URL="${RAE_API_URL:-http://localhost:8000}"
RAE_API_KEY="${RAE_API_KEY:-dev-key}"
RAE_TENANT_ID="${RAE_TENANT_ID:-shared-agents}"
RAE_PROJECT_ID="${RAE_PROJECT_ID:-$(basename $(pwd))}"

echo "🤖 RAE Multi-Agent Setup"
echo ""
echo "This is an example script. To use:"
echo "1. cp .claude/scripts/setup-rae-mcp-example.sh .local/setup-rae-mcp.sh"
echo "2. Edit .local/setup-rae-mcp.sh with your settings"
echo "3. Run: .local/setup-rae-mcp.sh"
echo ""
echo "See README-MULTI-AGENT.md for full documentation."
echo ""
