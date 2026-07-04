# API Endpoints Reference

**Auto-Generated** from OpenAPI specification

**Last Updated:** 2025-12-06
**API Version:** 2.1.1

## Core Memory Endpoints

### POST /v1/memories/create
Create a new memory entry.

**Request Body:**
```json
{
  "content": "string",
  "layer": "episodic|semantic|ltm|rm",
  "tags": ["string"],
  "metadata": {}
}
```

### POST /v1/memory/query
Query memories with hybrid search.

### POST /v1/memory/reflection
Generate reflection from memories.

## GraphRAG Endpoints

### POST /v1/graph/entities
Extract entities from text.

### GET /v1/graph/traverse
Traverse knowledge graph.

## Enterprise Endpoints

### POST /v1/triggers/create
Create event trigger rule.

### GET /v1/cost/usage
Get cost tracking data.

---

**Note:** Full API documentation will be auto-generated from FastAPI app in future iteration.
See interactive docs at: http://localhost:8000/docs
