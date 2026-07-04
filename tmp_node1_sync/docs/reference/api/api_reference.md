# API Reference

The RAE Agentic Memory API is built using FastAPI, which provides automatic, interactive API documentation. This is the best way to explore the available endpoints, their parameters, and responses.

## Quick Links

- **Complete API Reference**: See [API Documentation](api.md) for complete endpoint listings
- **REST Examples**: See [REST API Examples](api/rest-api.md) for curl examples
- **Python SDK**: See [Python SDK](api/python-sdk.md) for Python integration

## Interactive Documentation

Once you have the Memory API running, you can access the interactive documentation in your browser:

### Swagger UI
**URL**: http://localhost:8000/docs

Swagger UI provides a rich, interactive interface where you can:
- Browse all available endpoints organized by tags
- View request/response schemas
- Make live requests to test endpoints
- Specify headers (like `X-Tenant-ID`, `X-API-Key`)
- See actual responses from the running server

**Features:**
- Try out API calls directly from the browser
- Automatic request validation
- Response examples
- Schema documentation

### ReDoc
**URL**: http://localhost:8000/redoc

ReDoc offers a clean, three-panel view of the API documentation:
- Left panel: Endpoint navigation
- Center panel: Detailed documentation
- Right panel: Request/response examples

**Best for:**
- Reading comprehensive API docs
- Understanding data models
- Printing/sharing documentation
- Clear, readable layout

## OpenAPI Specification

The underlying OpenAPI 3.0 specification is available at:

**URL**: http://localhost:8000/openapi.json

Use this JSON file to:
- Generate clients in various programming languages
- Import into API tools (Postman, Insomnia, etc.)
- Integrate with testing frameworks
- Build custom tooling

## API Overview

RAE Memory API v2.0-enterprise provides:

### Core Features (v1)
- **Memory Management** (`/v1/memory/*`) - Store, query, delete memories
- **Agent Operations** (`/v1/agent/*`) - Execute agent tasks with memory context
- **Knowledge Graphs** (`/v1/graph/*`) - Build and query GraphRAG knowledge graphs
- **Cache Management** (`/v1/cache/*`) - Context cache operations
- **Governance** (`/v1/governance/*`) - Cost tracking and budget management
- **Health & Monitoring** (`/health`, `/metrics`) - System health and Prometheus metrics

### Enterprise Features (v1)
- **Event Triggers** (`/v1/triggers/*`) - Event-driven automation and workflows
- **Reflections** (`/v1/reflections/*`) - Hierarchical reflection system with clustering
- **Hybrid Search** (`/v1/search/*`) - Multi-strategy search (vector + semantic + graph + fulltext)
- **Evaluation** (`/v1/evaluation/*`) - Search quality metrics, A/B testing, drift detection
- **Dashboard** (`/v1/dashboard/*`) - Real-time monitoring with WebSocket support
- **Graph Management** (`/v1/graph-management/*`) - Advanced graph operations, snapshots, traversal

### Core Mathematical Modules (Internal)
- **State Management** (`apps/memory_api/core/state.py`) - MDP state space (S) with memory layers and budget tracking
- **Action Space** (`apps/memory_api/core/actions.py`) - 12 action types (A) for memory operations
- **Reward Function** (`apps/memory_api/core/reward.py`) - Performance evaluation (R) with quality metrics
- **Information Bottleneck** (`apps/memory_api/core/information_bottleneck.py`) - Optimal context selection via IB principle
- **Graph Operator** (`apps/memory_api/core/graph_operator.py`) - Knowledge graph evolution G_{t+1} = T(G_t, o_t, a_t)

See [RAE Mathematical Formalization](../architecture/rae-mathematical-formalization.md) for detailed documentation.

### Total Endpoints
- **116 endpoints** across all features
- **26 core endpoints** (Memory, Agent, Cache, Graph, Governance, Health)
- **90 enterprise endpoints** (Triggers, Reflections, Search, Evaluation, Dashboard, Graph Management, Compliance)

## Authentication

All endpoints (except health checks) require authentication:

```bash
# API Key
curl -H "X-API-Key: your-api-key" http://localhost:8000/v1/memory/query

# JWT Bearer Token
curl -H "Authorization: Bearer your-token" http://localhost:8000/v1/memory/query
```

## Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-API-Key` or `Authorization` | Yes | Authentication |
| `X-Tenant-ID` | Yes | Multi-tenancy identifier |
| `X-Project-ID` | No | Project scope (optional) |
| `Content-Type` | Yes | `application/json` |

## Quick Start Examples

### Store Memory
```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{"content": "User prefers dark mode", "layer": "episodic"}'
```

### Query Memory
```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{"query_text": "user preferences", "k": 10}'
```

### Hybrid Search
```bash
curl -X POST http://localhost:8000/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-key" \
  -d '{"tenant_id": "demo-tenant", "project_id": "my-app", "query": "authentication", "k": 10}'
```

## Error Handling

All errors return a consistent format:

```json
{
  "error": {
    "code": "400",
    "message": "Validation Error",
    "details": {...}
  }
}
```

## Rate Limiting

Default: 100 requests/60 seconds per tenant

Headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1735603200
```

## Further Reading

- **[Complete API Reference](api.md)** - All endpoints with descriptions
- **[REST Examples](api/rest-api.md)** - Curl examples for all operations
- **[Python SDK](api/python-sdk.md)** - Python client library
- **[MCP Server](api/mcp-server.md)** - Model Context Protocol integration
- **[Architecture](concepts/architecture.md)** - System architecture overview
- **[Enterprise Services](services/)** - Detailed enterprise feature docs
