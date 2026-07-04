# MCP IDE Integration

## Overview

The Model Context Protocol (MCP) allows AI assistants like Claude, Cline, and other IDEs to access RAE memory directly. This provides seamless context sharing between development tools.

**Location**: `integrations/mcp/`

## What is MCP?

MCP is a standard protocol developed by Anthropic for connecting AI assistants to external context sources. It provides:
- **Standardized Tools**: Common interface for memory operations
- **Type Safety**: JSON Schema validation
- **Security**: Token-based authentication
- **Extensibility**: Custom tools per integration

## Installation

### Install MCP Server

```bash
cd integrations/mcp
pip install -e .

# Verify installation
python -m rae_mcp.server --version
```

## IDE Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "rae-memory": {
      "command": "python",
      "args": ["-m", "rae_mcp.server"],
      "env": {
        "RAE_BASE_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key-here",
        "RAE_TENANT_ID": "your-tenant-id",
        "RAE_PROJECT_ID": "default"
      }
    }
  }
}
```

### Cline (VS Code Extension)

Add to Cline MCP settings:

```json
{
  "rae-memory": {
    "command": "python",
    "args": ["-m", "rae_mcp.server"],
    "env": {
      "RAE_BASE_URL": "http://localhost:8000",
      "RAE_API_KEY": "your-api-key-here",
      "RAE_TENANT_ID": "your-tenant-id"
    }
  }
}
```

### Zed Editor

Add to MCP configuration:

```json
{
  "context_servers": {
    "rae-memory": {
      "command": ["python", "-m", "rae_mcp.server"],
      "env": {
        "RAE_BASE_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key-here",
        "RAE_TENANT_ID": "your-tenant-id"
      }
    }
  }
}
```

## Available MCP Tools

### 1. store_memory

Store a new memory in RAE.

```json
{
  "name": "store_memory",
  "description": "Store a new memory",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {"type": "string"},
      "source": {"type": "string"},
      "importance": {"type": "number", "minimum": 0, "maximum": 1},
      "tags": {"type": "array", "items": {"type": "string"}},
      "layer": {"type": "string", "enum": ["sm", "em", "ltm", "rm"]}
    },
    "required": ["content", "source"]
  }
}
```

**Example Usage**:
```
User: "Remember that we decided to use PostgreSQL for the database"
Claude: [Uses store_memory tool]
  → Stored memory with ID: mem-123
```

### 2. query_memories

Search for relevant memories.

```json
{
  "name": "query_memories",
  "description": "Search memories semantically",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "k": {"type": "integer", "default": 10},
      "min_importance": {"type": "number", "default": 0.0},
      "layers": {"type": "array", "items": {"type": "string"}},
      "tags": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["query"]
  }
}
```

**Example Usage**:
```
User: "What database are we using?"
Claude: [Uses query_memories tool with query="database selection"]
  → Found 3 relevant memories
  → Response: "Based on team memory, you decided to use PostgreSQL..."
```

### 3. query_graph

GraphRAG query for complex reasoning.

```json
{
  "name": "query_graph",
  "description": "Query knowledge graph with multi-hop reasoning",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "k": {"type": "integer", "default": 10},
      "max_depth": {"type": "integer", "default": 2}
    },
    "required": ["query"]
  }
}
```

**Example Usage**:
```
User: "What are the dependencies of the auth module?"
Claude: [Uses query_graph tool]
  → Traversed graph: auth → jwt-lib → crypto
  → Response: "The auth module depends on jwt-lib and crypto..."
```

### 4. generate_reflection

Create a reflection from execution events.

```json
{
  "name": "generate_reflection",
  "description": "Generate reflection from task execution",
  "inputSchema": {
    "type": "object",
    "properties": {
      "events": {"type": "array"},
      "outcome": {"type": "string", "enum": ["success", "failure", "partial"]},
      "task_description": {"type": "string"}
    },
    "required": ["events", "outcome"]
  }
}
```

**Example Usage**:
```
User: "The API call timed out after 30 seconds"
Claude: [Uses generate_reflection tool]
  → Generated reflection about timeout handling
  → Stored as reflective memory
```

### 5. get_memory_stats

Get memory statistics.

```json
{
  "name": "get_memory_stats",
  "description": "Get memory statistics for tenant",
  "inputSchema": {
    "type": "object",
    "properties": {}
  }
}
```

## Usage Patterns

### Pattern 1: Project Context Awareness

```
User: "Start working on the authentication feature"

Claude:
1. [Calls query_memories("authentication feature requirements")]
2. Retrieves past decisions, code patterns, requirements
3. Responds with context-aware suggestions
```

### Pattern 2: Continuous Learning

```
User: "I fixed the bug by adding a null check"

Claude:
1. [Calls store_memory("Fixed null pointer bug with null check", ...)]
2. Memory stored for future reference
3. Can recall this fix in similar situations
```

### Pattern 3: Team Knowledge

```
User: "What's our code review process?"

Claude:
1. [Calls query_memories("code review process")]
2. Retrieves team decisions and guidelines
3. Provides accurate, team-specific answer
```

### Pattern 4: Cross-Session Memory

```
Session 1:
User: "We should use Redis for caching"
Claude: [Stores decision]

Session 2 (next day):
User: "What caching solution should we use?"
Claude: [Queries memories, finds previous decision]
  → "Based on previous discussion, you decided to use Redis..."
```

## Configuration

### Environment Variables

```bash
# Required
RAE_BASE_URL=http://localhost:8000
RAE_API_KEY=your-api-key-here
RAE_TENANT_ID=your-tenant-id

# Optional
RAE_PROJECT_ID=default
RAE_TIMEOUT_SECONDS=30
RAE_MAX_RETRIES=3
```

### Per-Project Configuration

For project-specific settings, create `.rae-mcp.json`:

```json
{
  "base_url": "http://localhost:8000",
  "tenant_id": "project-specific-tenant",
  "project_id": "my-project",
  "default_tags": ["my-project", "team-a"],
  "auto_store_important": true,
  "importance_threshold": 0.7
}
```

## Advanced Features

### Auto-Store on Important Events

Enable automatic memory storage for important events:

```json
{
  "auto_store": {
    "enabled": true,
    "triggers": [
      "code_error_fixed",
      "design_decision_made",
      "important_question_answered"
    ]
  }
}
```

### Smart Context Injection

RAE MCP can automatically inject relevant context:

```
User: "Fix the authentication bug"

Claude (internal):
1. Detects "authentication" + "bug"
2. Queries RAE for authentication-related memories
3. Injects top 3 most relevant memories into context
4. Responds with context-aware solution
```

### Cost Optimization

Reduce LLM calls with intelligent caching:

```json
{
  "mcp_config": {
    "cache_queries": true,
    "cache_ttl_seconds": 300,
    "query_importance_threshold": 0.5
  }
}
```

## Troubleshooting

### MCP Server Not Starting

Check logs:
```bash
# Test MCP server manually
python -m rae_mcp.server --debug

# Check connection to RAE
curl http://localhost:8000/health
```

### Authentication Errors

Verify API key:
```bash
# Test API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:8000/api/v1/memories
```

### No Memories Retrieved

Check tenant/project:
```bash
# Verify tenant has memories
rae memory list --tenant-id YOUR_TENANT_ID
```

## Security

### API Key Storage

Store API keys securely:
```bash
# Use environment variables
export RAE_API_KEY=$(cat ~/.rae/api_key)

# Or use secrets manager
export RAE_API_KEY=$(aws secretsmanager get-secret-value --secret-id rae-api-key --query SecretString --output text)
```

### Network Security

For remote RAE instances, use HTTPS:
```json
{
  "RAE_BASE_URL": "https://rae.yourcompany.com",
  "RAE_VERIFY_SSL": "true"
}
```

## Performance

### Query Optimization

Optimize MCP queries:
```python
# In MCP configuration
{
  "query_defaults": {
    "k": 5,  # Fewer results = faster
    "min_importance": 0.6,  # Filter low-importance
    "use_cache": true
  }
}
```

### Async Operations

MCP server uses async operations for performance:
```python
# Non-blocking queries
await rae_client.query_memories_async(query="...")
```

## Examples

### Example 1: Code Review Assistant

```
User: "Review this pull request"
Claude:
1. [Queries RAE for code review guidelines]
2. [Queries for similar PRs and their feedback]
3. Provides context-aware review based on team standards
```

### Example 2: Onboarding New Team Member

```
User: "What's our development workflow?"
Claude:
1. [Queries RAE for workflow documentation]
2. [Retrieves team decisions and practices]
3. Provides comprehensive onboarding information
```

### Example 3: Debugging Helper

```
User: "Getting error: Connection timeout"
Claude:
1. [Queries RAE for "connection timeout" solutions]
2. Finds previous fixes and patterns
3. Suggests solution based on team's past experience
```

## Related Documentation

- [Integrations Overview](./INTEGRATIONS_OVERVIEW.md) - All integrations
- [Python SDK](./SDK_PYTHON_REFERENCE.md) - SDK used by MCP
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant isolation
