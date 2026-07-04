# MCP Server Migration Guide: v1.0 → v1.1

This guide helps you migrate from the legacy MCP server (v1.0.0 in `integrations/mcp-server/`) to the new refactored version (v1.1.0 in `integrations/mcp/`).

---

## Why Migrate?

### New Features in v1.1.0

✅ **Security Enhancements**
- Comprehensive PII scrubbing with 50+ test cases
- Enhanced detection patterns for API keys, emails, credit cards, SSNs, etc.
- Improved logging security with structured sanitization

✅ **Rate Limiting**
- Built-in rate limiter (100 requests/minute per tenant by default)
- Configurable limits via environment variables
- Protection against DoS attacks and abuse

✅ **Testing & Quality**
- 20+ new unit tests for PII scrubbing
- Integration tests with real RAE API (docker compose.lite.yml)
- 59 total test functions ensuring reliability

✅ **Performance & Observability**
- Documented performance benchmarks
- Enhanced Prometheus metrics
- Improved structured logging

✅ **Documentation**
- Performance benchmarks published
- Security best practices documented
- Comprehensive troubleshooting guide

---

## Breaking Changes

### Package Naming

**v1.0.0** (old):
```python
from rae_mcp_server.server import RAEMemoryClient
```

**v1.1.0** (new):
```python
from rae_mcp.server import RAEMemoryClient
```

### Entry Point

**v1.0.0** (old):
```bash
python -m rae_mcp_server
```

**v1.1.0** (new):
```bash
rae-mcp-server  # Installed as script entry point
```

### Configuration

No changes - environment variables remain the same:
- `RAE_API_URL`
- `RAE_API_KEY`
- `RAE_PROJECT_ID`
- `RAE_TENANT_ID`

**New optional variables**:
- `MCP_RATE_LIMIT_ENABLED` (default: `true`)
- `MCP_RATE_LIMIT_REQUESTS` (default: `100`)
- `MCP_RATE_LIMIT_WINDOW` (default: `60` seconds)

---

## Step-by-Step Migration

### 1. Uninstall Old Version

```bash
# If installed via pip
pip uninstall rae-mcp-server

# Or remove from pyproject.toml if using local development
```

### 2. Install New Version

```bash
cd integrations/mcp
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

### 3. Verify Installation

```bash
rae-mcp-server --help
```

Expected output:
```
Usage: rae-mcp-server [OPTIONS]

Enterprise-grade MCP server for RAE Memory Engine
...
```

### 4. Update IDE Configurations

#### Claude Desktop

**No changes required** - the command name remains `rae-mcp-server`.

File: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server",  // ✅ No change needed
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Optional**: Add new rate limit configuration:

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server",
      "env": {
        "RAE_API_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key",
        "MCP_RATE_LIMIT_ENABLED": "true",
        "MCP_RATE_LIMIT_REQUESTS": "100",
        "MCP_RATE_LIMIT_WINDOW": "60"
      }
    }
  }
}
```

#### Cursor

**No changes required**.

File: `.cursor/config.json`

```json
{
  "mcp": {
    "servers": {
      "rae-memory": {
        "command": "rae-mcp-server",  // ✅ No change needed
        "args": []
      }
    }
  }
}
```

#### Cline (VS Code)

**No changes required**.

File: VS Code MCP settings

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "rae-mcp-server"  // ✅ No change needed
    }
  }
}
```

### 5. Test the Migration

#### Manual Test

Start your IDE (Claude Desktop, Cursor, or Cline) and try:

```
Save this to memory: Migration to MCP v1.1.0 successful
Tags: migration, test
Layer: episodic
```

You should see:
```
✓ Memory stored successfully
ID: <memory-id>
Layer: episodic
Tags: migration, test
```

#### Automated Test

Run the new integration tests:

```bash
cd integrations/mcp

# PII scrubbing tests
pytest tests/test_pii_scrubber.py -v

# Integration tests (requires docker compose.lite.yml running)
pytest tests/test_mcp_integration.py -v -m integration

# All tests
pytest tests/ -v
```

---

## New Configuration Options

### Rate Limiting

Control request limits per tenant:

```bash
# .env or environment variables
MCP_RATE_LIMIT_ENABLED=true          # Enable/disable rate limiting
MCP_RATE_LIMIT_REQUESTS=100          # Max requests per window
MCP_RATE_LIMIT_WINDOW=60             # Time window in seconds
```

**Behavior**:
- When rate limit is exceeded, tool calls return user-friendly error message
- Metrics are recorded via Prometheus (`mcp_tool_errors_total{error_type="rate_limit"}`)
- Sliding window algorithm ensures fair distribution

**Disable Rate Limiting** (not recommended for production):

```bash
MCP_RATE_LIMIT_ENABLED=false
```

---

## Compatibility Matrix

| Feature | v1.0.0 | v1.1.0 | Compatible? |
|---------|--------|--------|-------------|
| **MCP Tools** | 3 tools | 3 tools | ✅ Yes |
| **MCP Resources** | 2 resources | 2 resources | ✅ Yes |
| **MCP Prompts** | 2 prompts | 2 prompts | ✅ Yes |
| **API Endpoints** | Same | Same | ✅ Yes |
| **Environment Vars** | 4 vars | 4 + 3 optional | ✅ Backward compatible |
| **Entry Point** | `python -m` | `rae-mcp-server` | ✅ Both work |
| **Package Name** | `rae_mcp_server` | `rae_mcp` | ⚠️ Import path changed |

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'rae_mcp'`

**Cause**: Old version still installed or incorrect installation.

**Solution**:
```bash
pip uninstall rae-mcp-server
cd integrations/mcp
pip install -e .
```

### Issue: `command not found: rae-mcp-server`

**Cause**: Package not installed or not in PATH.

**Solution**:
```bash
# Check installation
pip list | grep rae-mcp

# Reinstall
cd integrations/mcp
pip install -e .

# Verify
which rae-mcp-server
```

### Issue: Rate limit errors appearing frequently

**Cause**: Rate limit too low for your usage.

**Solution**:
```bash
# Increase limit in .env
MCP_RATE_LIMIT_REQUESTS=500
MCP_RATE_LIMIT_WINDOW=60

# Or disable (not recommended)
MCP_RATE_LIMIT_ENABLED=false
```

### Issue: Tests failing with "RAE API failed to start"

**Cause**: Docker services not running or ports in use.

**Solution**:
```bash
# Check if ports are available
lsof -i :8000
lsof -i :5432
lsof -i :6333
lsof -i :6379

# Start RAE Lite manually
docker compose -f docker compose.lite.yml up -d

# Check health
curl http://localhost:8000/health
```

---

## Rollback Plan

If you encounter issues and need to rollback to v1.0.0:

```bash
# Uninstall v1.1.0
pip uninstall rae-mcp

# Reinstall v1.0.0
cd integrations/mcp-server
pip install -e .

# Verify
python -m rae_mcp_server --help
```

**Note**: v1.0.0 will be removed in RAE v2.0.0 (Q2 2025). Please report migration issues so we can improve v1.1.0.

---

## What's Next?

### Performance Benchmarks

v1.1.0 includes documented performance characteristics:

- **save_memory**: p50 = 45ms, p95 = 120ms, p99 = 250ms
- **search_memory**: p50 = 80ms, p95 = 200ms, p99 = 400ms
- **Throughput**: 100+ tool calls/second (single instance)
- **Memory**: 150 MB baseline, 300 MB under load

See `docs/MCP_ENTERPRISE_REVIEW.md` for full benchmarks.

### Future Enhancements (v1.2+)

- OpenTelemetry distributed tracing
- Redis-based distributed rate limiting
- Circuit breaker pattern for RAE API calls
- Health check HTTP endpoint

---

## Support

### Documentation

- **MCP Server Guide**: `docs/integrations/mcp_protocol_server.md`
- **Enterprise Review**: `docs/MCP_ENTERPRISE_REVIEW.md`
- **Context Watcher**: `docs/integrations/context_watcher_daemon.md`

### Getting Help

1. **GitHub Issues**: [RAE Issues](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
2. **Email**: lesniowskig@gmail.com
3. **Documentation**: Check `integrations/mcp/README.md`

### Reporting Migration Issues

If you encounter problems during migration, please open an issue with:

- Old version used (v1.0.0)
- New version installed (v1.1.0)
- IDE used (Claude Desktop, Cursor, Cline)
- Error messages or logs
- Steps to reproduce

---

## Summary

✅ **Migration is straightforward** - mostly install new package
✅ **Zero downtime** - entry point name unchanged (`rae-mcp-server`)
✅ **Backward compatible** - all old configurations work
✅ **New features** - PII scrubbing, rate limiting, integration tests
✅ **Better quality** - 59 test functions, comprehensive coverage

**Estimated migration time**: 10-15 minutes

---

**Migration completed?** Give us feedback! Open an issue or send an email to let us know how it went.
