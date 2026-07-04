# IDE Integration Guide (Legacy)

**⚠️ This document is deprecated. Please use the new comprehensive guide:**

**→ [IDE_INTEGRATION.md](./IDE_INTEGRATION.md)** ←

---

## Quick Migration

The MCP server has moved:

- **Old location**: `integrations/mcp-server`
- **New location**: `integrations/mcp`
- **Old command**: `python -m rae_mcp_server`
- **New command**: `rae-mcp-server` (installed script)

### Quick Setup

1. Install new MCP server:
   ```bash
   cd integrations/mcp
   pip install -e .
   ```

2. Update your IDE configuration to use `rae-mcp-server` instead of `python -m rae_mcp_server`

3. Follow the full guide: [IDE_INTEGRATION.md](./IDE_INTEGRATION.md)

### Migration Guide

See [integrations/MIGRATION.md](../../integrations/MIGRATION.md) for detailed migration instructions.

---

## Resources

- **[New IDE Integration Guide](./IDE_INTEGRATION.md)** - Complete documentation
- **[MCP Protocol Server](../integrations/mcp_protocol_server.md)** - Technical details
- **[Migration Guide](../../integrations/MIGRATION.md)** - Upgrade instructions
- **[Configuration Examples](../../examples/ide-config/)** - Ready-to-use configs
