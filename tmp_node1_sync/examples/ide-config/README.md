# IDE Configuration Examples

This directory contains ready-to-use configuration files for integrating RAE Memory Engine with various IDEs via the Model Context Protocol (MCP).

## Prerequisites

1. **Install RAE MCP Server**:
   ```bash
   cd integrations/mcp
   pip install -e .
   ```

2. **Verify Installation**:
   ```bash
   rae-mcp-server --help
   ```

3. **Start RAE API** (if not already running):
   ```bash
   docker compose -f docker compose.lite.yml up -d
   ```

## Configuration Steps

### 1. Choose Your IDE

Select the appropriate configuration file for your IDE:

- **Claude Desktop**: `claude/claude_desktop_config.json`
- **Cursor**: `cursor/mcp.json`
- **Cline (VSCode)**: `cline/settings.json`
- **Windsurf**: `windsurf/mcp.json`
- **Continue (VSCode)**: `continue/settings.json`

### 2. Customize Environment Variables

Replace the following placeholders in the configuration file:

| Variable | Description | Example |
|----------|-------------|---------|
| `RAE_API_URL` | RAE Memory API endpoint | `http://localhost:8000` |
| `RAE_API_KEY` | Your API key | `my-secure-api-key-123` |
| `RAE_PROJECT_ID` | Project identifier | `my-awesome-project` |
| `RAE_TENANT_ID` | Tenant identifier | `my-company` |

**Example**:
```json
{
  "env": {
    "RAE_API_URL": "http://localhost:8000",
    "RAE_API_KEY": "dev-api-key-2024",
    "RAE_PROJECT_ID": "chatbot-v2",
    "RAE_TENANT_ID": "acme-corp"
  }
}
```

### 3. Find Absolute Path (for Cursor)

Cursor requires the absolute path to `rae-mcp-server`:

```bash
which rae-mcp-server
# Example output: /home/user/.local/bin/rae-mcp-server
```

Update `cursor/mcp.json` with this path.

### 4. Copy Configuration to IDE

#### Claude Desktop (macOS)
```bash
cp claude/claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

#### Claude Desktop (Windows)
```powershell
Copy-Item claude\claude_desktop_config.json $env:APPDATA\Claude\claude_desktop_config.json
```

#### Cursor
```bash
cp cursor/mcp.json .cursor/mcp.json
# Or edit directly: ~/.cursor/config.json
```

#### Cline (VSCode)
1. Open VSCode Settings (Cmd+, or Ctrl+,)
2. Search for "Cline: MCP Settings"
3. Click "Edit in settings.json"
4. Merge content from `cline/settings.json`

#### Windsurf
```bash
cp windsurf/mcp.json .windsurf/mcp.json
```

#### Continue (VSCode)
1. Open VSCode Settings (Cmd+, or Ctrl+,)
2. Search for "Continue"
3. Edit settings and merge content from `continue/settings.json`

### 5. Restart IDE

Restart your IDE to load the MCP configuration.

## Verification

After restarting your IDE, verify the integration works:

### Test Commands

1. **Save Memory**:
   ```
   Please save this to memory: "We decided to use PostgreSQL for the database"
   Tags: database, architecture, decision
   ```

2. **Search Memory**:
   ```
   Search my memory for database decisions
   ```

3. **Get Context**:
   ```
   Show me the history of src/auth/middleware.py
   ```

### Expected Behavior

- IDE should invoke MCP tools (`save_memory`, `search_memory`)
- You should see confirmation messages in the chat
- Check RAE API logs: `docker compose logs -f memory-api`

## Troubleshooting

### Command Not Found: `rae-mcp-server`

**Solution**: Ensure `rae-mcp-server` is in your PATH:
```bash
# Check if installed
pip show rae-mcp

# Add to PATH (if needed)
export PATH="$PATH:$HOME/.local/bin"
```

### RAE API Connection Error

**Solution**: Verify RAE API is running:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### MCP Server Not Starting in IDE

**Solutions**:
1. Check IDE logs (location varies by IDE)
2. Verify environment variables are set correctly
3. Test MCP server manually:
   ```bash
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | rae-mcp-server
   ```

### Rate Limiting Errors

If you see "Rate limit exceeded" messages:
```bash
# Increase rate limit (optional)
export MCP_RATE_LIMIT_REQUESTS=500
export MCP_RATE_LIMIT_WINDOW=60
```

## IDE-Specific Notes

### Claude Desktop
- Native MCP support (no plugins required)
- Auto-loads on startup
- Logs: `~/Library/Logs/Claude/` (macOS)

### Cursor
- Requires **absolute paths** for commands
- Configuration: `.cursor/mcp.json` or `~/.cursor/config.json`
- Restart required after config changes

### Cline (VSCode)
- Install Cline extension first
- Configuration via VSCode settings
- Provider ID must match server name

### Windsurf
- Emerging IDE with MCP support
- Configuration format similar to Cursor
- Check official docs for latest updates

### Continue (VSCode)
- Install Continue extension first
- MCP support may vary by version
- Check extension settings for MCP options

## Advanced Configuration

### Custom Memory Layers

Specify memory layer when saving:
```json
{
  "layer": "semantic"  // Options: episodic, working, semantic, ltm
}
```

### Multiple Projects

Create separate MCP servers for different projects:
```json
{
  "mcpServers": {
    "rae-project-a": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_PROJECT_ID": "project-a"
      }
    },
    "rae-project-b": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_PROJECT_ID": "project-b"
      }
    }
  }
}
```

### OpenTelemetry Tracing

Enable tracing for debugging:
```json
{
  "env": {
    "OTEL_ENABLED": "true",
    "OTEL_EXPORTER": "console"
  }
}
```

## Resources

- **Full Documentation**: [docs/guides/ide-integration.md](../../docs/guides/ide-integration.md)
- **MCP Protocol**: [docs/integrations/mcp_protocol_server.md](../../docs/integrations/mcp_protocol_server.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md)
- **MCP Specification**: https://modelcontextprotocol.io/

## Support

- **Issues**: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- **Discussions**: https://github.com/dreamsoft-pro/RAE-agentic-memory/discussions
- **Documentation**: https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/docs

## License

Apache License 2.0 - see [LICENSE](../../LICENSE)
