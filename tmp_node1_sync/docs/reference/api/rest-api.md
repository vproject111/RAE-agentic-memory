# REST API Examples

Complete examples for using RAE Memory API via REST.

## Base URL

```
http://localhost:8000
```

## Authentication

Include API key in headers:
```bash
curl -H "X-API-Key: your-api-key"
```

Or use Bearer token:
```bash
curl -H "Authorization: Bearer your-token"
```

## Core Operations

### Store Memory

**POST** `/v1/memory/store`

```bash
curl -X POST http://localhost:8000/v1/memory/store \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "User prefers dark mode for better readability",
    "layer": "episodic",
    "tags": ["preference", "ui"],
    "importance": 0.8,
    "project": "my-app"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Memory stored successfully."
}
```

### Query Memory

**POST** `/v1/memory/query`

```bash
curl -X POST http://localhost:8000/v1/memory/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query_text": "What are user UI preferences?",
    "k": 10,
    "filters": {
      "tags": ["preference"]
    }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User prefers dark mode for better readability",
      "score": 0.92,
      "layer": "episodic",
      "tags": ["preference", "ui"],
      "importance": 0.8,
      "timestamp": "2025-01-20T10:30:00Z"
    }
  ]
}
```

### Delete Memory

**DELETE** `/v1/memory/delete?memory_id={id}`

```bash
curl -X DELETE "http://localhost:8000/v1/memory/delete?memory_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key"
```

## Knowledge Graph Operations

### Extract Knowledge Graph

**POST** `/v1/graph/extract`

```bash
curl -X POST http://localhost:8000/v1/graph/extract \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project": "my-app",
    "memory_ids": ["550e8400-e29b-41d4-a716-446655440000"],
    "min_confidence": 0.7
  }'
```

### Query Knowledge Graph

**POST** `/v1/graph/query`

```bash
curl -X POST http://localhost:8000/v1/graph/query \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project": "my-app",
    "query": "authentication security",
    "k": 10,
    "enable_graph_traversal": true,
    "max_depth": 2
  }'
```

### Get Graph Statistics

**GET** `/v1/graph/stats?tenant_id=demo-tenant&project=my-app`

```bash
curl http://localhost:8000/v1/graph/stats?tenant_id=demo-tenant&project=my-app \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key"
```

## Agent Operations

### Execute Agent Task

**POST** `/v1/agent/execute`

```bash
curl -X POST http://localhost:8000/v1/agent/execute \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project": "my-app",
    "prompt": "What security issues have we encountered?",
    "budget_tokens": 20000
  }'
```

**Response:**
```json
{
  "answer": "Based on memory records, several security issues have been identified...",
  "used_memories": {
    "episodic": 5,
    "semantic": 3
  },
  "cost": {
    "input_tokens": 1500,
    "output_tokens": 800,
    "total_estimate": 0.045
  }
}
```

## Enterprise Features

### Hybrid Search

**POST** `/v1/search/hybrid`

```bash
curl -X POST http://localhost:8000/v1/search/hybrid \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project_id": "my-app",
    "query": "authentication best practices",
    "k": 10,
    "enable_vector_search": true,
    "enable_semantic_search": true,
    "enable_graph_search": true,
    "enable_fulltext_search": true,
    "enable_reranking": true
  }'
```

**Response:**
```json
{
  "search_result": {
    "results": [...],
    "total_results": 10,
    "total_time_ms": 245,
    "query_analysis": {
      "intent": "conceptual",
      "confidence": 0.92
    },
    "applied_weights": {
      "vector": 0.3,
      "semantic": 0.3,
      "graph": 0.3,
      "fulltext": 0.1
    }
  },
  "message": "Hybrid search completed: 10 results in 245ms"
}
```

### Create Event Trigger

**POST** `/v1/triggers/create`

```bash
curl -X POST http://localhost:8000/v1/triggers/create \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "rule_name": "Alert on High Importance",
    "event_type": "memory_created",
    "condition": {
      "field": "importance",
      "operator": "GREATER_THAN",
      "value": 0.8
    },
    "actions": [
      {
        "action_type": "send_webhook",
        "config": {
          "url": "https://example.com/webhook",
          "method": "POST"
        }
      }
    ]
  }'
```

### Generate Reflections

**POST** `/v1/reflections/generate`

```bash
curl -X POST http://localhost:8000/v1/reflections/generate \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project": "my-app",
    "max_memories": 100,
    "min_cluster_size": 5,
    "enable_clustering": true
  }'
```

### Evaluate Search Results

**POST** `/v1/evaluation/search`

```bash
curl -X POST http://localhost:8000/v1/evaluation/search \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project_id": "my-app",
    "relevance_judgments": {
      "query1": {
        "mem1": 2,
        "mem2": 1
      }
    },
    "search_results": {
      "query1": ["mem1", "mem2", "mem3"]
    },
    "metrics_to_compute": ["mrr", "ndcg", "precision"]
  }'
```

### Create Graph Snapshot

**POST** `/v1/graph-management/snapshots`

```bash
curl -X POST http://localhost:8000/v1/graph-management/snapshots \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "tenant_id": "demo-tenant",
    "project_id": "my-app",
    "description": "Daily backup",
    "metadata": {
      "reason": "scheduled_backup"
    }
  }'
```

## Health Checks

### Comprehensive Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.3
    },
    "vector_store": {
      "status": "healthy",
      "response_time_ms": 8.7
    }
  },
  "version": "2.0.0-enterprise",
  "uptime_seconds": 3600
}
```

### Readiness Probe

**GET** `/health/ready`

```bash
curl http://localhost:8000/health/ready
```

### Liveness Probe

**GET** `/health/live`

```bash
curl http://localhost:8000/health/live
```

## WebSocket Connection

### Dashboard Real-time Updates

**WS** `/v1/dashboard/ws`

```javascript
const ws = new WebSocket('ws://localhost:8000/v1/dashboard/ws?tenant_id=demo-tenant&project_id=my-app');

ws.onopen = () => {
  console.log('Connected to dashboard');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received update:', data);
};
```

## Governance & Cost Tracking

### Get Tenant Governance Stats

**GET** `/v1/governance/tenant/{tenant_id}`

```bash
curl http://localhost:8000/v1/governance/tenant/demo-tenant \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key"
```

### Get Budget Status

**GET** `/v1/governance/tenant/{tenant_id}/budget`

```bash
curl http://localhost:8000/v1/governance/tenant/demo-tenant/budget \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-API-Key: your-api-key"
```

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "code": "400",
    "message": "Invalid request",
    "details": {
      "field": "content",
      "issue": "Content exceeds maximum length"
    }
  }
}
```

**Status Codes:**
- 200: Success
- 201: Created
- 202: Accepted (async operation)
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 422: Validation Error
- 429: Rate Limit Exceeded
- 500: Internal Server Error

## Rate Limiting

Default: 100 requests per 60 seconds

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1735603200
```

## Interactive Documentation

For more details and to try the API interactively:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## SDKs

For easier API usage, see:

- [Python SDK](python-sdk.md)
- [MCP Server Integration](mcp-server.md)
