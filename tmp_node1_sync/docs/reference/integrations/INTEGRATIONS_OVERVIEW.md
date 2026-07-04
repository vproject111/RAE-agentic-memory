# Integrations Overview

## Overview

RAE provides integrations with popular platforms and services for seamless memory management across different environments.

**Location**: `integrations/`

## Available Integrations

### 1. Model Context Protocol (MCP)

**Location**: `integrations/mcp/`

Standard protocol for AI assistants to access RAE.

```bash
# Install MCP server
cd integrations/mcp
pip install -e .

# Configure in Claude Desktop / Cline / etc.
{
  "mcpServers": {
    "rae-memory": {
      "command": "python",
      "args": ["-m", "rae_mcp.server"],
      "env": {
        "RAE_BASE_URL": "http://localhost:8000",
        "RAE_API_KEY": "your-api-key"
      }
    }
  }
}
```

**Exposed Tools**:
- `store_memory` - Store new memory
- `query_memories` - Search memories
- `query_graph` - GraphRAG queries
- `generate_reflection` - Create reflection

**Documentation**: See [MCP_IDE_INTEGRATION.md](./MCP_IDE_INTEGRATION.md)

### 2. Context Watcher

**Location**: `integrations/context-watcher/`

Monitors code changes and automatically stores relevant context.

```bash
# Install
cd integrations/context-watcher
pip install -e .

# Start watching
context-watcher \
  --repo /path/to/repo \
  --rae-url http://localhost:8000 \
  --watch-patterns "*.py,*.ts,*.md"
```

**Features**:
- Automatic commit tracking
- File change detection
- Important code pattern recognition
- Continuous context building

### 3. Slack Integration

**Location**: `integrations/slack/` (planned)

Store and query memories from Slack.

```bash
# Commands in Slack
/rae store "Team decided to use PostgreSQL"
/rae query "What database are we using?"
/rae reflect "Deploy failed due to missing env vars"
```

**Use Cases**:
- Team knowledge management
- Decision tracking
- Incident memory

### 4. GitHub Integration

**Location**: `integrations/github/` (planned)

Integrate with GitHub for PR and issue memory.

**Features**:
- Automatic PR memory storage
- Code review insights
- Issue context tracking
- Commit message analysis

**Setup**:
```yaml
# .github/workflows/rae-memory.yml
name: RAE Memory
on: [pull_request, issues]

jobs:
  store:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/rae-github-action@v1
        with:
          rae-url: ${{ secrets.RAE_URL }}
          api-key: ${{ secrets.RAE_API_KEY }}
```

### 5. VS Code Extension

**Location**: `integrations/vscode/` (planned)

RAE memory directly in VS Code.

**Features**:
- Quick memory storage (Cmd+Shift+M)
- Inline memory queries
- Code context awareness
- Automatic code memory

### 6. Email Integration

**Location**: `integrations/email/` (planned)

Store important emails as memories.

**Setup**:
```yaml
# Forward to: memories@rae.yourcompany.com
# Automatically stored with:
# - Subject as content
# - Sender as source
# - Auto-detected importance
# - Tags from subject/body
```

### 7. Ollama Wrapper

**Location**: `integrations/ollama-wrapper/`

Local LLM support via Ollama.

```bash
# Start wrapper
python integrations/ollama-wrapper/server.py

# Configure RAE
RAE_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
RAE_LLM_MODEL_DEFAULT=llama3
```

## Integration Patterns

### Webhook Integration

Generic webhook receiver:

```python
# POST to RAE webhook endpoint
POST /api/v1/webhooks/memory
Content-Type: application/json
X-Webhook-Secret: your-secret

{
  "content": "Event occurred",
  "source": "external_system",
  "importance": 0.7,
  "tags": ["webhook", "external"]
}
```

### API Integration

Direct API calls from any system:

```python
import requests

response = requests.post(
    "http://rae:8000/api/v1/memories",
    headers={
        "Authorization": f"Bearer {api_key}",
        "X-Tenant-ID": tenant_id
    },
    json={
        "content": "Important event",
        "source": "my_app",
        "importance": 0.8
    }
)
```

### SDK Integration

Use Python SDK in your application:

```python
from rae_memory_sdk import MemoryClient

client = MemoryClient(
    base_url="http://rae:8000",
    api_key=api_key,
    tenant_id=tenant_id
)

# Store from your app
client.store_memory(
    content=f"User {user_id} completed action X",
    source="myapp",
    importance=0.6,
    tags=["user_action"]
)

# Query for context
results = client.query_memories(
    query=f"What has user {user_id} done?",
    k=10
)
```

## Configuration

### Integration Registry

Register integrations in `integrations.yaml`:

```yaml
integrations:
  - id: slack
    name: Slack Integration
    enabled: true
    config:
      bot_token: ${SLACK_BOT_TOKEN}
      signing_secret: ${SLACK_SIGNING_SECRET}
      channel_whitelist: ["general", "engineering"]

  - id: github
    name: GitHub Integration
    enabled: true
    config:
      app_id: ${GITHUB_APP_ID}
      private_key_path: /secrets/github.pem
      repositories: ["owner/repo1", "owner/repo2"]
```

### Per-Tenant Integration Settings

```python
{
  "tenant_id": "tenant-123",
  "integrations": {
    "slack": {
      "enabled": true,
      "workspace_id": "T12345",
      "auto_store_channels": ["engineering"]
    },
    "github": {
      "enabled": true,
      "organizations": ["my-org"]
    }
  }
}
```

## Security

### API Key Management

- **Per-Integration Keys**: Each integration gets dedicated API key
- **Scoped Permissions**: Keys limited to specific operations
- **Rotation**: Automatic key rotation support
- **Audit**: All integration activity logged

### Webhook Verification

```python
# Verify webhook signatures
def verify_webhook(request, secret):
    signature = request.headers.get("X-Webhook-Signature")
    expected = hmac.new(secret, request.body, "sha256").hexdigest()
    return hmac.compare_digest(signature, expected)
```

## Monitoring

### Integration Metrics

```
# Prometheus metrics
rae_integration_requests_total{integration="slack", status="success"}
rae_integration_latency_seconds{integration="github"}
rae_integration_errors_total{integration="slack", error_type="auth"}
```

### Health Checks

```bash
# Check integration health
curl http://rae:8000/api/v1/integrations/health

# Response:
{
  "slack": {"status": "healthy", "last_activity": "2025-12-01T10:30:00Z"},
  "github": {"status": "degraded", "error": "Rate limit"}
}
```

## Developing Custom Integrations

### Integration Template

```python
from rae_memory_sdk import MemoryClient

class MyIntegration:
    def __init__(self, rae_url, api_key, tenant_id):
        self.client = MemoryClient(rae_url, api_key, tenant_id)

    async def handle_event(self, event):
        """Process event from external system"""
        content = self.extract_content(event)
        importance = self.calculate_importance(event)

        memory_id = self.client.store_memory(
            content=content,
            source="my_integration",
            importance=importance,
            tags=self.extract_tags(event)
        )

        return memory_id

    def extract_content(self, event):
        # Extract meaningful content
        pass

    def calculate_importance(self, event):
        # Calculate importance score
        pass

    def extract_tags(self, event):
        # Extract relevant tags
        pass
```

## Related Documentation

- [MCP IDE Integration](./MCP_IDE_INTEGRATION.md) - Detailed MCP setup
- [Python SDK](./SDK_PYTHON_REFERENCE.md) - SDK for integrations
- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant isolation in integrations
