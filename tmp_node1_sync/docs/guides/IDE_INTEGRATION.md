# IDE Integration Guide

Comprehensive guide for integrating RAE Memory Engine with your IDE using the Model Context Protocol (MCP).

## Table of Contents

1. [Overview](#overview)
2. [Quick Start (3 Steps)](#quick-start-3-steps)
3. [Supported IDEs](#supported-ides)
4. [IDE Recipes](#ide-recipes)
5. [Non-MCP IDEs](#non-mcp-ides)
6. [Troubleshooting & FAQ](#troubleshooting--faq)
7. [Advanced Configuration](#advanced-configuration)

---

## Overview

RAE provides seamless integration with modern IDEs through two complementary mechanisms:

### 🔌 MCP Server (`rae-mcp-server`)

The **Model Context Protocol (MCP) Server** is the primary integration mechanism for IDEs with native MCP support.

**What it does**:
- Exposes RAE memory operations as **MCP tools** (save, search, context retrieval)
- Provides **resources** for project reflection and guidelines
- Injects **prompts** with recent context automatically
- Communicates via **JSON-RPC 2.0 over STDIO** (no HTTP overhead)

**Supported IDEs**:
- Claude Desktop
- Cursor
- VSCode (Cline extension)
- Windsurf
- VSCode (Continue extension)

**Learn More**: [MCP Protocol Server Documentation](../integrations/mcp_protocol_server.md)

### 📁 Context Watcher

The **Context Watcher** is an HTTP daemon that monitors file changes and streams them to RAE in real-time.

**What it does**:
- Watches project directories for file changes
- Automatically saves file modifications to RAE memory
- Provides ambient awareness of project evolution
- Works with any IDE (complementary to MCP)

**Learn More**: [Context Watcher Documentation](../integrations/context_watcher_daemon.md)

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│  IDE (Claude Desktop, Cursor, Cline, etc.)               │
│  - User writes code                                      │
│  - AI assistant invokes MCP tools                        │
└───────────────────┬──────────────────────────────────────┘
                    │
                    │ STDIO (JSON-RPC 2.0)
                    │
┌───────────────────▼──────────────────────────────────────┐
│  RAE MCP Server (rae-mcp-server)                         │
│  - save_memory, search_memory, get_related_context       │
│  - PII scrubbing, rate limiting, validation              │
└───────────────────┬──────────────────────────────────────┘
                    │
                    │ HTTP REST API
                    │
┌───────────────────▼──────────────────────────────────────┐
│  RAE Memory API (port 8000)                              │
│  - 4-layer memory (episodic/working/semantic/ltm)        │
│  - GraphRAG, reflection engine, embeddings               │
└───────────────────┬──────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────┐
│  PostgreSQL + pgvector                                   │
└──────────────────────────────────────────────────────────┘
```

---

## Quick Start (3 Steps)

### Step 1: Start RAE Memory API

Choose your deployment profile and start RAE:

```bash
# Option A: RAE Lite (recommended for first-time users)
docker compose -f docker compose.lite.yml up -d

# Option B: RAE Standard (with ML service and dashboard)
docker compose up -d

# Option C: RAE Enterprise (Kubernetes)
# See: docs/deployment/kubernetes.md
```

**Verify API is running**:
```bash
curl http://localhost:8000/health
```

Expected response: `{"status": "healthy"}`

### Step 2: Install MCP Server

```bash
cd integrations/mcp
pip install -e .
```

**Verify installation**:
```bash
rae-mcp-server --help
```

Expected output:
```
Usage: rae-mcp-server [OPTIONS]

Enterprise-grade MCP server for RAE Memory Engine
```

### Step 3: Configure Your IDE

1. **Choose your IDE** from the [IDE Recipes](#ide-recipes) section below
2. **Copy the configuration template** from `examples/ide-config/<YOUR-IDE>/`
3. **Customize environment variables** (API URL, API key, project ID, tenant ID)
4. **Restart your IDE**
5. **Test the integration** by asking your AI assistant to save or search memory

**Example Test**:
```
Please save this to memory: "We decided to use PostgreSQL for the database because of its excellent ACID compliance and pgvector support."

Tags: database, architecture, decision
Layer: semantic
```

---

## Supported IDEs

| IDE | Integration Type | Status | Config Example | Notes |
|-----|------------------|--------|----------------|-------|
| **Claude Desktop** | MCP (STDIO) | ✅ Stable | [claude/](../../examples/ide-config/claude/) | Native MCP support |
| **Cursor** | MCP | ✅ Stable | [cursor/](../../examples/ide-config/cursor/) | Requires absolute paths |
| **VSCode + Cline** | MCP | ✅ Stable | [cline/](../../examples/ide-config/cline/) | Cline extension required |
| **VSCode + Continue** | MCP / HTTP | 🟡 Beta | [continue/](../../examples/ide-config/continue/) | Verify MCP support |
| **Windsurf** | MCP | 🟡 Beta | [windsurf/](../../examples/ide-config/windsurf/) | Emerging IDE |
| **JetBrains** | HTTP/CLI | 🟡 Beta | [See Non-MCP section](#jetbrains-pycharm--intellij--webstorm) | External tool integration |
| **Vim/Neovim** | HTTP/CLI | 🟡 Beta | [See Non-MCP section](#vimneovim) | Command hooks |
| **Sublime Text** | HTTP/CLI | 🟡 Beta | [See Non-MCP section](#sublime-text) | Build system integration |

**Legend**:
- ✅ **Stable**: Production-ready, fully tested
- 🟡 **Beta**: Functional, needs more testing
- 🔴 **Experimental**: Work in progress

---

## IDE Recipes

Detailed configuration instructions for each IDE.

### Claude Desktop

**Platform**: macOS, Windows
**Status**: ✅ Stable

#### Configuration (macOS)

1. Locate config file:
   ```bash
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. Copy template:
   ```bash
   cp examples/ide-config/claude/claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. Edit configuration:
   ```json
   {
     "mcpServers": {
       "rae-memory": {
         "command": "rae-mcp-server",
         "env": {
           "RAE_API_URL": "http://localhost:8000",
           "RAE_API_KEY": "your-api-key-here",
           "RAE_PROJECT_ID": "my-project",
           "RAE_TENANT_ID": "my-tenant"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop

#### Configuration (Windows)

1. Locate config file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Copy and edit as above

#### Verification

1. Open Claude Desktop
2. Start a new conversation
3. Test command:
   ```
   Can you search my memory for database decisions?
   ```
4. Claude should invoke the `search_memory` tool

#### Troubleshooting

- **Check logs**: `~/Library/Logs/Claude/` (macOS)
- **Verify PATH**: `which rae-mcp-server`
- **Test API**: `curl http://localhost:8000/health`

---

### Cursor

**Platform**: macOS, Windows, Linux
**Status**: ✅ Stable

#### Configuration

1. Find absolute path to `rae-mcp-server`:
   ```bash
   which rae-mcp-server
   # Example: /home/user/.local/bin/rae-mcp-server
   ```

2. Create `.cursor/mcp.json` in project root:
   ```json
   {
     "mcpServers": {
       "rae-memory": {
         "command": "/absolute/path/to/rae-mcp-server",
         "env": {
           "RAE_API_URL": "http://localhost:8000",
           "RAE_API_KEY": "your-api-key-here",
           "RAE_PROJECT_ID": "my-project",
           "RAE_TENANT_ID": "my-tenant"
         }
       }
     }
   }
   ```

   **Important**: Cursor requires **absolute paths** for the command.

3. Alternatively, edit global config:
   ```bash
   ~/.cursor/config.json
   ```

4. Restart Cursor

#### Verification

1. Open Cursor in your project
2. Use Cmd+K (Mac) or Ctrl+K (Windows) to open AI chat
3. Test command:
   ```
   Save this to memory: test message
   ```
4. Cursor should invoke the MCP tool

#### Troubleshooting

- **Absolute path required**: Use `which rae-mcp-server` to find the path
- **Virtual environment**: If using venv, path might be `.venv/bin/rae-mcp-server`
- **Check Cursor logs**: Settings → Advanced → Open Logs

---

### VSCode + Cline

**Platform**: macOS, Windows, Linux
**Status**: ✅ Stable

#### Prerequisites

Install the Cline extension:
1. Open VSCode
2. Go to Extensions (Cmd+Shift+X or Ctrl+Shift+X)
3. Search for "Cline"
4. Install the extension

#### Configuration

1. Open VSCode Settings (Cmd+, or Ctrl+,)
2. Search for "Cline: MCP Settings"
3. Click "Edit in settings.json"
4. Add MCP server configuration:

   ```json
   {
     "cline.mcpServers": {
       "rae-memory": {
         "command": "rae-mcp-server",
         "env": {
           "RAE_API_URL": "http://localhost:8000",
           "RAE_API_KEY": "your-api-key-here",
           "RAE_PROJECT_ID": "my-project",
           "RAE_TENANT_ID": "my-tenant"
         }
       }
     }
   }
   ```

5. Reload VSCode window (Cmd+Shift+P → "Reload Window")

#### Verification

1. Open Cline panel in VSCode
2. Start a conversation
3. Test command:
   ```
   Can you search my memory for recent decisions?
   ```
4. Cline should show MCP tool invocation

#### Troubleshooting

- **Provider ID**: The server name (`rae-memory`) must match the `providerId` in Cline's config
- **Check extension logs**: Output → Cline
- **Verify PATH**: Open terminal in VSCode and run `which rae-mcp-server`

---

### VSCode + Continue

**Platform**: macOS, Windows, Linux
**Status**: 🟡 Beta (verify MCP support in your Continue version)

#### Prerequisites

Install the Continue extension:
1. Open VSCode
2. Go to Extensions (Cmd+Shift+X or Ctrl+Shift+X)
3. Search for "Continue"
4. Install the extension

#### Configuration

1. Open Continue settings
2. Add MCP server configuration:

   ```json
   {
     "mcpServers": {
       "rae-memory": {
         "command": "rae-mcp-server",
         "env": {
           "RAE_API_URL": "http://localhost:8000",
           "RAE_API_KEY": "your-api-key-here",
           "RAE_PROJECT_ID": "my-project",
           "RAE_TENANT_ID": "my-tenant"
         }
       }
     }
   }
   ```

3. Reload VSCode

#### Verification

1. Open Continue panel
2. Test MCP integration with AI commands

#### Notes

- Continue's MCP support may vary by version
- Check official Continue documentation for latest MCP integration status
- Alternative: Use HTTP API directly (see [Non-MCP IDEs](#non-mcp-ides))

---

### Windsurf

**Platform**: macOS, Windows, Linux
**Status**: 🟡 Beta

Windsurf is an emerging IDE with MCP support.

#### Configuration

Create `.windsurf/mcp.json` in your project:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key-here",
        "RAE_PROJECT_ID": "my-project",
        "RAE_TENANT_ID": "my-tenant"
      }
    }
  }
}
```

#### Notes

- Configuration format similar to Cursor
- Check Windsurf documentation for latest MCP integration details
- Restart IDE after configuration changes

---

## Non-MCP IDEs

For IDEs without native MCP support, you can integrate RAE through HTTP API calls or CLI commands.

### JetBrains (PyCharm / IntelliJ / WebStorm)

#### Option 1: External Tool (Recommended)

1. **Create RAE CLI wrapper script** (`rae-cli.py`):

   ```python
   #!/usr/bin/env python3
   import sys
   import requests
   import json

   RAE_API_URL = "http://localhost:8000"
   RAE_API_KEY = "your-api-key-here"
   PROJECT_ID = "my-project"
   TENANT_ID = "my-tenant"

   def save_memory(content, source, tags=None, layer="episodic"):
       """Save content to RAE memory."""
       response = requests.post(
           f"{RAE_API_URL}/v1/memory/store",
           headers={
               "Content-Type": "application/json",
               "X-API-Key": RAE_API_KEY,
               "X-Project-Id": PROJECT_ID,
               "X-Tenant-Id": TENANT_ID,
           },
           json={
               "content": content,
               "source": source,
               "tags": tags or [],
               "layer": layer,
           },
       )
       return response.json()

   def search_memory(query, top_k=5):
       """Search RAE memory."""
       response = requests.post(
           f"{RAE_API_URL}/v1/memory/query",
           headers={
               "Content-Type": "application/json",
               "X-API-Key": RAE_API_KEY,
               "X-Project-Id": PROJECT_ID,
               "X-Tenant-Id": TENANT_ID,
           },
           json={"query_text": query, "k": top_k},
       )
       return response.json()

   if __name__ == "__main__":
       command = sys.argv[1] if len(sys.argv) > 1 else "help"

       if command == "save":
           content = sys.argv[2] if len(sys.argv) > 2 else ""
           source = sys.argv[3] if len(sys.argv) > 3 else "cli"
           result = save_memory(content, source)
           print(json.dumps(result, indent=2))

       elif command == "search":
           query = sys.argv[2] if len(sys.argv) > 2 else ""
           result = search_memory(query)
           print(json.dumps(result, indent=2))

       else:
           print("Usage:")
           print("  rae-cli.py save <content> <source>")
           print("  rae-cli.py search <query>")
   ```

2. **Make executable**:
   ```bash
   chmod +x rae-cli.py
   ```

3. **Configure as External Tool in JetBrains**:
   - Go to: **Settings → Tools → External Tools**
   - Click **+** to add new tool
   - **Name**: RAE Save Memory
   - **Program**: `/path/to/rae-cli.py`
   - **Arguments**: `save "$SelectedText$" "$FilePath$"`
   - **Working directory**: `$ProjectFileDir$`

4. **Usage**:
   - Select text in editor
   - Right-click → External Tools → RAE Save Memory

#### Option 2: Context Watcher + MCP in External Client

1. Start Context Watcher to monitor file changes
2. Use Claude Desktop / Cursor as external MCP client
3. Files changes automatically saved to RAE
4. Query RAE memory from external client

---

### Vim/Neovim

#### Option 1: Command Mapping

Add to `~/.vimrc` or `~/.config/nvim/init.vim`:

```vim
" Save selected text to RAE memory
vnoremap <leader>rs :!curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "X-Project-Id: my-project" \
  -H "X-Tenant-Id: my-tenant" \
  -d '{"content": "<C-R>\"", "source": "vim", "layer": "episodic"}'<CR>

" Search RAE memory (prompt for query)
nnoremap <leader>rq :!curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -H "X-Project-Id: my-project" \
  -H "X-Tenant-Id: my-tenant" \
  -d '{"query_text": "<query>", "k": 5}'<CR>
```

**Usage**:
- Select text in visual mode → `<leader>rs` to save
- Press `<leader>rq` to search (edit query inline)

#### Option 2: Lua Plugin (Neovim)

Create `~/.config/nvim/lua/rae.lua`:

```lua
local M = {}

M.save_memory = function()
  local content = vim.fn.getreg('"')
  local source = vim.fn.expand('%:p')

  local cmd = string.format(
    'curl -s -X POST http://localhost:8000/v1/memory/store ' ..
    '-H "Content-Type: application/json" ' ..
    '-H "X-API-Key: your-api-key" ' ..
    '-H "X-Project-Id: my-project" ' ..
    '-H "X-Tenant-Id: my-tenant" ' ..
    '-d \'{"content": "%s", "source": "%s", "layer": "episodic"}\'',
    content:gsub('"', '\\"'),
    source
  )

  local result = vim.fn.system(cmd)
  print("Saved to RAE: " .. result)
end

M.search_memory = function()
  local query = vim.fn.input("Search RAE: ")

  local cmd = string.format(
    'curl -s -X POST http://localhost:8000/v1/memory/query ' ..
    '-H "Content-Type: application/json" ' ..
    '-H "X-API-Key: your-api-key" ' ..
    '-H "X-Project-Id: my-project" ' ..
    '-H "X-Tenant-Id: my-tenant" ' ..
    '-d \'{"query_text": "%s", "k": 5}\'',
    query:gsub('"', '\\"')
  )

  local result = vim.fn.system(cmd)
  print(result)
end

return M
```

Load in `init.lua`:
```lua
local rae = require('rae')
vim.keymap.set('v', '<leader>rs', rae.save_memory)
vim.keymap.set('n', '<leader>rq', rae.search_memory)
```

---

### Sublime Text

#### Build System Integration

Create `RAE.sublime-build`:

```json
{
  "shell_cmd": "curl -X POST http://localhost:8000/v1/memory/store -H 'Content-Type: application/json' -H 'X-API-Key: your-api-key' -H 'X-Project-Id: my-project' -H 'X-Tenant-Id: my-tenant' -d '{\"content\": \"$selection\", \"source\": \"$file\", \"layer\": \"episodic\"}'",
  "selector": "source"
}
```

**Usage**:
- Tools → Build System → RAE
- Select text → Ctrl+B (Cmd+B on Mac)

---

## Troubleshooting & FAQ

### Issue: `command not found: rae-mcp-server`

**Symptoms**:
- IDE shows "MCP server failed to start"
- Command not found errors

**Solutions**:

1. **Verify installation**:
   ```bash
   pip show rae-mcp
   ```

2. **Check PATH**:
   ```bash
   which rae-mcp-server
   ```

3. **Add to PATH** (if needed):
   ```bash
   export PATH="$PATH:$HOME/.local/bin"
   ```

4. **Use absolute path** in IDE config:
   ```json
   {
     "command": "/home/user/.local/bin/rae-mcp-server"
   }
   ```

---

### Issue: RAE API Connection Error

**Symptoms**:
- "Connection refused" errors
- Tool calls timeout
- "Failed to connect to RAE API"

**Solutions**:

1. **Verify API is running**:
   ```bash
   curl http://localhost:8000/health
   ```

   Expected: `{"status": "healthy"}`

2. **Check Docker containers**:
   ```bash
   docker compose ps
   ```

   All services should be "Up"

3. **Review API logs**:
   ```bash
   docker compose logs -f memory-api
   ```

4. **Verify network connectivity**:
   ```bash
   ping localhost
   telnet localhost 8000
   ```

---

### Issue: MCP Server Not Starting in IDE

**Symptoms**:
- IDE shows "MCP server crashed"
- No tools available in AI assistant
- IDE logs show startup errors

**Solutions**:

1. **Test server manually**:
   ```bash
   rae-mcp-server
   ```

   Server should start and wait for input

2. **Check environment variables**:
   ```bash
   env | grep RAE_
   ```

   Ensure `RAE_API_URL`, `RAE_API_KEY`, etc. are set

3. **Review IDE logs**:
   - **Claude Desktop**: `~/Library/Logs/Claude/` (macOS)
   - **Cursor**: Settings → Advanced → Open Logs
   - **Cline**: Output → Cline

4. **Test with minimal config**:
   ```json
   {
     "mcpServers": {
       "rae": {
         "command": "rae-mcp-server"
       }
     }
   }
   ```

---

### Issue: Rate Limiting Errors

**Symptoms**:
- "Rate limit exceeded" messages
- Tool calls rejected after many requests

**Solutions**:

1. **Increase rate limit** (for development):
   ```bash
   export MCP_RATE_LIMIT_REQUESTS=500
   export MCP_RATE_LIMIT_WINDOW=60
   ```

2. **Disable rate limiting** (not recommended for production):
   ```bash
   export MCP_RATE_LIMIT_ENABLED=false
   ```

3. **Check rate limit status**:
   - Rate limit info included in error messages
   - Default: 100 requests per 60 seconds per tenant

---

### Issue: High Latency / Slow Tool Calls

**Symptoms**:
- Tool calls take > 5 seconds
- IDE feels sluggish when using RAE tools

**Solutions**:

1. **Check RAE API performance**:
   ```bash
   time curl -X POST http://localhost:8000/v1/memory/query \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-key" \
     -d '{"query_text":"test","k":5}'
   ```

2. **Reduce search `top_k`**:
   - Lower values = faster searches
   - Optimal range: 5-10 results

3. **Optimize RAE deployment**:
   - Use RAE Standard (not Lite) for better performance
   - Increase PostgreSQL resources
   - Use local deployment (avoid remote API)

4. **Monitor system resources**:
   ```bash
   docker stats
   ```

---

### FAQ

#### Q: Can I use multiple MCP servers in one IDE?

**A**: Yes! Most IDEs support multiple MCP servers:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server",
      "env": {"RAE_PROJECT_ID": "project-a"}
    },
    "rae-docs": {
      "command": "rae-mcp-server",
      "env": {"RAE_PROJECT_ID": "docs"}
    }
  }
}
```

#### Q: How do I switch between projects?

**A**: Use different `RAE_PROJECT_ID` values or configure multiple MCP servers (one per project).

#### Q: Does RAE work offline?

**A**: RAE requires the Memory API to be running. For offline use, run RAE locally (docker compose) instead of cloud deployment.

#### Q: What's the difference between MCP and Context Watcher?

**A**:
- **MCP**: On-demand, explicit tool calls from AI assistant
- **Context Watcher**: Automatic, passive file change monitoring
- **Recommended**: Use both together for best experience

#### Q: Can I use RAE with Claude API (not Claude Desktop)?

**A**: Yes, but you'll need to handle tool calling logic in your application. See [RAE SDK documentation](../../sdk/python/README.md).

#### Q: How do I debug MCP communication?

**A**: Enable OpenTelemetry tracing:

```json
{
  "env": {
    "OTEL_ENABLED": "true",
    "OTEL_EXPORTER": "console"
  }
}
```

Output will show detailed spans for each tool call.

---

## Advanced Configuration

### Custom Memory Layers

Specify which memory layer to use when saving:

```json
{
  "layer": "semantic"
}
```

**Available layers**:
- `episodic`: Recent events and activities (default)
- `working`: Current task context (short-term)
- `semantic`: Concepts, guidelines, principles
- `ltm`: Long-term facts and knowledge

**Example** (in AI chat):
```
Save this to semantic memory: "Always use FastAPI for REST APIs in this project"
```

---

### Multiple Projects / Tenants

Configure separate MCP servers for different projects:

```json
{
  "mcpServers": {
    "rae-backend": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_PROJECT_ID": "backend-service",
        "RAE_TENANT_ID": "company-a"
      }
    },
    "rae-frontend": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_PROJECT_ID": "frontend-app",
        "RAE_TENANT_ID": "company-a"
      }
    }
  }
}
```

---

### OpenTelemetry Tracing

Enable distributed tracing for debugging and performance monitoring:

```json
{
  "env": {
    "OTEL_ENABLED": "true",
    "OTEL_SERVICE_NAME": "rae-mcp-server",
    "OTEL_EXPORTER": "console"
  }
}
```

**Supported exporters**:
- `console`: Print spans to stdout (development)
- `jaeger`: Send to Jaeger backend (future)
- `otlp`: OpenTelemetry Protocol (future)

**Learn More**: [MCP Protocol Server - OpenTelemetry](../integrations/mcp_protocol_server.md#opentelemetry-distributed-tracing-new-in-v120)

---

### Rate Limiting Configuration

Adjust rate limits per tenant:

```json
{
  "env": {
    "MCP_RATE_LIMIT_ENABLED": "true",
    "MCP_RATE_LIMIT_REQUESTS": "200",
    "MCP_RATE_LIMIT_WINDOW": "60"
  }
}
```

**Configuration**:
- `MCP_RATE_LIMIT_REQUESTS`: Max requests per window
- `MCP_RATE_LIMIT_WINDOW`: Window duration (seconds)
- `MCP_RATE_LIMIT_ENABLED`: Enable/disable rate limiting

---

### Context Watcher Integration

Use Context Watcher alongside MCP for automatic file tracking:

1. **Start Context Watcher**:
   ```bash
   cd integrations/context-watcher
   python context_watcher.py --watch-dir /path/to/project
   ```

2. **Configure in IDE** (optional):
   - Context Watcher runs independently
   - No IDE configuration needed
   - File changes automatically synced to RAE

3. **Verify**:
   ```bash
   curl http://localhost:5001/health
   ```

**Learn More**: [Context Watcher Documentation](../integrations/context_watcher_daemon.md)

---

## Related Documentation

- **[MCP Protocol Server](../integrations/mcp_protocol_server.md)**: Full MCP implementation details
- **[Context Watcher](../integrations/context_watcher_daemon.md)**: File monitoring daemon
- **[RAE Memory API](../../apps/memory_api/README.md)**: Core API reference
- **[Python SDK](../../sdk/python/README.md)**: Direct API integration
- **[MCP Specification](https://modelcontextprotocol.io/)**: Official MCP protocol docs

---

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

---

## Support

- **GitHub Issues**: https://github.com/dreamsoft-pro/RAE-agentic-memory/issues
- **Discussions**: https://github.com/dreamsoft-pro/RAE-agentic-memory/discussions
- **Documentation**: https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/docs

---

## License

Apache License 2.0 - see [LICENSE](../../LICENSE)
