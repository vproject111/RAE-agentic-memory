# Memory API - Complete REST API Reference

> **Core Memory Operations** - Store, retrieve, update, and manage memories across 4 layers.

---

## Base URL

```
http://localhost:8000/v1
```

**Authentication**: All endpoints require either API key or JWT token.

```bash
# API Key authentication
curl -H "X-API-Key: your-api-key" ...

# JWT authentication
curl -H "Authorization: Bearer your-jwt-token" ...

# Tenant isolation (required)
curl -H "X-Tenant-ID: your-tenant-id" ...
```

---

## Endpoints Overview

| Category | Endpoint | Method | Description |
|----------|----------|--------|-------------|
| **Memory CRUD** | `/memories/create` | POST | Create new memory |
| | `/memories/{id}` | GET | Get memory by ID |
| | `/memories/{id}` | PUT | Update memory |
| | `/memories/{id}` | DELETE | Delete memory |
| **Search** | `/memory/query` | POST | Hybrid search |
| | `/memory/search/advanced` | POST | Advanced search with filters |
| **Reflection** | `/reflection/generate` | POST | Generate reflection |
| | `/reflections` | GET | List reflections |
| **Graph** | `/graph/nodes` | GET | Get graph nodes |
| | `/graph/traverse` | POST | Traverse knowledge graph |

---

## 1. Create Memory

**POST** `/v1/memories/create`

### Request Body

```json
{
  "layer": "ltm",
  "memory_type": "semantic",
  "content": "JWT tokens must be validated using signature verification",
  "importance": 0.9,
  "tags": ["security", "auth", "best_practice"],
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "source": "security_audit_2025",
    "confidence": 0.95
  }
}
```

### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "layer": "ltm",
  "memory_type": "semantic",
  "content": "JWT tokens must be validated using signature verification",
  "importance": 0.9,
  "tags": ["security", "auth", "best_practice"],
  "created_at": "2025-12-08T17:30:00Z",
  "embedding_status": "pending"
}
```

### Field Descriptions

- **layer** (required): `stm`, `ltm`, `em`, `rm` - See [Memory Layers](../architecture/MEMORY_LAYERS.md)
- **memory_type** (required): `sensory`, `episodic`, `semantic`, `profile`, `reflection`, `strategy`
- **content** (required): Memory text (max 50,000 characters)
- **importance** (optional): 0.0-1.0 score (default: 0.5)
- **tags** (optional): Array of strings for categorization
- **session_id** (optional): Links to execution session
- **metadata** (optional): Custom JSON object

### Status Codes

- `201 Created`: Memory created successfully
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication failed
- `402 Payment Required`: Budget exceeded
- `500 Internal Server Error`: Server error

---

## 2. Query Memory (Hybrid Search)

**POST** `/v1/memory/query`

### Request Body

```json
{
  "query": "authentication best practices",
  "top_k": 10,
  "enable_vector": true,
  "enable_semantic": true,
  "enable_graph": true,
  "enable_fulltext": true,
  "enable_reranking": true,
  "temporal_filter": "2025-12-01T00:00:00Z",
  "tag_filter": ["security", "auth"],
  "min_importance": 0.5
}
```

### Response

```json
{
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "JWT tokens must be validated...",
      "layer": "ltm",
      "memory_type": "semantic",
      "importance": 0.9,
      "hybrid_score": 0.87,
      "vector_score": 0.85,
      "graph_score": 0.90,
      "tags": ["security", "auth"],
      "created_at": "2025-12-08T17:30:00Z"
    }
  ],
  "query_analysis": {
    "intent": "factual",
    "confidence": 0.95,
    "key_entities": ["authentication"],
    "key_concepts": ["security", "best practices"]
  },
  "applied_weights": {
    "vector": 0.3,
    "semantic": 0.2,
    "graph": 0.4,
    "fulltext": 0.1
  },
  "total_time_ms": 145.67,
  "cache_hit": false
}
```

### Field Descriptions

- **query** (required): Search query text
- **top_k** (optional): Number of results (default: 10, max: 100)
- **enable_***: Toggle search strategies (all default: true)
- **temporal_filter**: Only return memories after this timestamp
- **tag_filter**: Only return memories with these tags
- **min_importance**: Filter by minimum importance score

---

## 3. Generate Reflection

**POST** `/v1/reflection/generate`

### Request Body

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "outcome": "failure",
  "importance": 0.85,
  "mode": "full"
}
```

### Response

```json
{
  "reflection_id": "789e4567-e89b-12d3-a456-426614174999",
  "reflection_type": "failure_analysis",
  "content": "Authentication failures often stem from missing JWT validation...",
  "importance": 0.95,
  "related_memories": [
    "123e4567-e89b-12d3-a456-426614174000"
  ],
  "generated_at": "2025-12-08T17:35:00Z",
  "cost": 0.0234
}
```

### Field Descriptions

- **session_id** (required): Session to reflect on
- **outcome** (optional): `success` or `failure` (auto-detected if omitted)
- **importance** (optional): 0.0-1.0 (default: 0.7)
- **mode** (optional): `full` (LLM-powered) or `lite` (heuristic) (default: auto)

---

## 4. List Memories

**GET** `/v1/memories?layer=ltm&limit=50&offset=0`

### Query Parameters

- **layer** (optional): Filter by layer (`stm`, `ltm`, `em`, `rm`)
- **memory_type** (optional): Filter by type
- **tags** (optional): Comma-separated tags
- **limit** (optional): Results per page (default: 50, max: 1000)
- **offset** (optional): Pagination offset (default: 0)

### Response

```json
{
  "memories": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "content": "...",
      "layer": "ltm",
      "importance": 0.9,
      "created_at": "2025-12-08T17:30:00Z"
    }
  ],
  "total": 1523,
  "limit": 50,
  "offset": 0
}
```

---

## 5. Update Memory

**PUT** `/v1/memories/{id}`

### Request Body

```json
{
  "importance": 0.95,
  "tags": ["security", "auth", "jwt", "critical"],
  "metadata": {
    "reviewed": true,
    "review_date": "2025-12-08"
  }
}
```

### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "updated_fields": ["importance", "tags", "metadata"],
  "updated_at": "2025-12-08T18:00:00Z"
}
```

**Note**: Cannot update `layer`, `memory_type`, or `content`. Create new memory instead.

---

## 6. Delete Memory

**DELETE** `/v1/memories/{id}`

### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "deleted": true,
  "cascade_deleted": {
    "graph_nodes": 3,
    "embeddings": 1,
    "reflections": 0
  }
}
```

**Note**: Deletion is permanent and cascades to related data.

---

## Complete Examples

### Example 1: Store and Query

```python
import requests

BASE_URL = "http://localhost:8000/v1"
HEADERS = {
    "X-API-Key": "your-api-key",
    "X-Tenant-ID": "my-tenant",
    "Content-Type": "application/json"
}

# 1. Create memory
response = requests.post(
    f"{BASE_URL}/memories/create",
    headers=HEADERS,
    json={
        "layer": "ltm",
        "memory_type": "semantic",
        "content": "JWT tokens must be validated using signature verification",
        "importance": 0.9,
        "tags": ["security", "auth"]
    }
)
memory_id = response.json()["id"]
print(f"Created memory: {memory_id}")

# 2. Query similar memories
response = requests.post(
    f"{BASE_URL}/memory/query",
    headers=HEADERS,
    json={
        "query": "How to secure authentication?",
        "top_k": 5,
        "enable_graph": True
    }
)
results = response.json()["results"]
print(f"Found {len(results)} similar memories")
```

### Example 2: Reflection Workflow

```python
# 1. Execute action (e.g., API call fails)
session_id = "550e8400-e29b-41d4-a716-446655440000"

# 2. Store outcome as memory
requests.post(
    f"{BASE_URL}/memories/create",
    headers=HEADERS,
    json={
        "layer": "em",
        "memory_type": "episodic",
        "content": "Authentication failed: JWT signature verification error",
        "session_id": session_id,
        "importance": 0.8,
        "tags": ["failure", "auth"]
    }
)

# 3. Generate reflection
response = requests.post(
    f"{BASE_URL}/reflection/generate",
    headers=HEADERS,
    json={
        "session_id": session_id,
        "outcome": "failure",
        "importance": 0.85,
        "mode": "full"
    }
)
reflection = response.json()
print(f"Reflection: {reflection['content']}")
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "BUDGET_EXCEEDED",
    "message": "Monthly budget limit of $100.00 exceeded",
    "details": {
      "current_spend": 105.43,
      "limit": 100.00,
      "reset_date": "2026-01-01T00:00:00Z"
    }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_INPUT` | 400 | Invalid request body |
| `UNAUTHORIZED` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `BUDGET_EXCEEDED` | 402 | Cost limit reached |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Rate Limiting

Default rate limits (configurable):

```
- Authenticated users: 1000 requests/hour
- Create memory: 100 requests/hour
- Query memory: 500 requests/hour
- Generate reflection: 50 requests/hour
```

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 957
X-RateLimit-Reset: 1701964800
```

---

## Related Documentation

- **[Hybrid Search API](./SEARCH_API.md)** - Advanced search operations
- **[Reflection Engine API](./REFLECTION_ENGINE_API.md)** - Reflection management
- **[Memory Layers](../architecture/MEMORY_LAYERS.md)** - Memory model reference
- **[Python SDK](../../sdk/python/README.md)** - Official Python client

---

**Version**: 2.1.0
**Last Updated**: 2025-12-08
**Interactive Docs**: http://localhost:8000/docs (Swagger UI)
