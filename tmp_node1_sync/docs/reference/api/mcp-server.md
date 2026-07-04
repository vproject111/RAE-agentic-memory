# MCP Server API (Legacy)

**⚠️ This document is deprecated. Please use the new documentation:**

**→ [MCP Protocol Server Documentation](../integrations/mcp_protocol_server.md)** ←

**→ [IDE Integration Guide](../guides/IDE_INTEGRATION.md)** ←

---

## Quick Migration

The MCP server has been upgraded and moved:

- **Old location**: `integrations/mcp-server`
- **New location**: `integrations/mcp`
- **Old command**: `python -m rae_mcp_server`
- **New command**: `rae-mcp-server` (installed script)

## Installation

```bash
cd integrations/mcp
pip install -e .
```

## Configuration

### Cursor / Claude Desktop

Add to config file:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_TENANT_ID": "your-tenant-id",
        "RAE_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Config Locations:**
- **Cursor**: `~/.cursor/config.json`
- **Claude Desktop (macOS)**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop (Windows)**: `%APPDATA%\Claude\claude_desktop_config.json`

## Available Tools

### save_memory
Save to RAE memory from IDE.

```
/rae-save This is important information
```

### search_memory
Search memories.

```
/rae-search authentication issues
```

### list_memories
List recent memories.

```
/rae-list 10
```

### generate_reflection
Generate AI insights.

```
/rae-reflect
```

## Auto-Context Injection

RAE automatically injects relevant context into prompts based on:
- Current workspace/project
- File being edited
- Conversation context

**Example:**
```
You: How do I fix the auth bug?

[RAE Auto-Injects]
Context from memory:
- auth.py had similar bug last week
- Fixed by updating JWT validation
- Related to session timeout

Your AI: Based on previous fixes...
```

## MCP Protocol Details

### Resources

RAE exposes memories as MCP resources:

```
rae://memory/{memory_id}
rae://project/{project_id}/memories
rae://search?q={query}
```

### Prompts

Pre-configured prompts:

```
/rae-summarize - Summarize recent activity
/rae-patterns - Find patterns in memories
/rae-related - Find related information
```

## Development

### Custom MCP Server

Extend the base server:

```python
from rae_mcp_server import RAEMCPServer

class CustomMCPServer(RAEMCPServer):
    async def custom_tool(self, params):
        # Your custom logic
        return result

server = CustomMCPServer(
    api_url="http://localhost:8000",
    tenant_id="your-tenant"
)
server.run()
```

### Testing

```bash
# Test MCP server
python -m rae_mcp_server --test

# Debug mode
RAE_DEBUG=true python -m rae_mcp_server
```

## Troubleshooting

### Server Not Loading

1. Check config file syntax (valid JSON)
2. Verify Python and rae_mcp_server installed
3. Check logs: `tail -f ~/.cursor/logs/mcp.log`

### Connection Errors

1. Ensure RAE API is running: `curl http://localhost:8000/health`
2. Check API_URL in config
3. Verify network connectivity

### Authentication Issues

1. Check API key is correct
2. Verify tenant_id exists
3. Check API auth is enabled: `ENABLE_API_KEY_AUTH=true`

## Best Practices

1. **Use project-specific tenants** for better organization
2. **Tag memories consistently** for better retrieval
3. **Review auto-injected context** periodically
4. **Set appropriate memory limits** to avoid context overflow

## See Also

- [IDE Integration Guide](../guides/ide-integration.md)
- [Python SDK](python-sdk.md)
- [REST API](rest-api.md)

---

For MCP protocol specification, see: https://modelcontextprotocol.io
