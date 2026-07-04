# Legacy MCP Endpoints - DEPRECATED

⚠️ **WARNING:** This document describes deprecated API endpoints that are no longer supported in RAE v2.0.0-enterprise.

**Last Supported Version:** 1.0.0-beta
**Deprecation Date:** 2025-11-22
**Removal Date:** v3.0.0 (planned)

---

## Migration Required

If you're using any of the following endpoints, please migrate to the new v1 API immediately:

| Old Endpoint (Deprecated) | New Endpoint (v2.0.0-enterprise) | Status |
|---------------------------|----------------------------------|--------|
| `POST /memory/add` | `POST /v1/memories/create` | ❌ Deprecated |
| `POST /memory/store` | `POST /v1/memories/create` | ❌ Deprecated |
| `GET /memory/query` | `POST /v1/search/hybrid` | ❌ Deprecated |
| `POST /memory/reflect` | `POST /v1/reflections/generate` | ❌ Deprecated |

---

## Why These Endpoints Were Deprecated

1. **Inconsistent Naming:** Old endpoints didn't follow RESTful conventions
2. **No Versioning:** Difficult to maintain backwards compatibility
3. **Limited Functionality:** New endpoints support GraphRAG, hierarchical search, and advanced features
4. **Security Improvements:** New API has better auth, rate limiting, and multi-tenancy

---

## Old Endpoint Documentation (For Reference Only)

### POST /memory/add

**Deprecated in:** v2.0.0-enterprise
**Replaced by:** `POST /v1/memories/create`

**Old Request:**
```json
{
  "content": "User prefers dark mode",
  "layer": "working",
  "source": "user_settings",
  "tags": ["preference", "ui"]
}
```

**Old Response:**
```json
{
  "id": "mem_123",
  "status": "success"
}
```

**Migration:**
```json
// New API (v2.0.0-enterprise)
POST /v1/memories/create

Request:
{
  "content": "User prefers dark mode",
  "layer": "wm",
  "source": "user_settings",
  "tags": ["preference", "ui"],
  "tenant_id": "your-tenant-id",
  "project": "your-project"
}

Response:
{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "message": "Memory created successfully"
}
```

---

### POST /memory/store

**Deprecated in:** v2.0.0-enterprise
**Replaced by:** `POST /v1/memories/create`

This was an alias for `/memory/add` with identical behavior.

**Migration:** Use `POST /v1/memories/create` (same as above)

---

### GET /memory/query

**Deprecated in:** v2.0.0-enterprise
**Replaced by:** `POST /v1/search/hybrid`

**Old Request:**
```bash
GET /memory/query?q=authentication&layer=semantic
```

**Old Response:**
```json
{
  "results": [
    {
      "id": "mem_456",
      "content": "User authentication uses JWT tokens",
      "score": 0.92
    }
  ]
}
```

**Migration:**
```json
// New API (v2.0.0-enterprise)
POST /v1/search/hybrid

Request:
{
  "query": "authentication",
  "tenant_id": "your-tenant-id",
  "project": "your-project",
  "layer_filter": "sm",
  "enable_graph": true,
  "max_results": 10
}

Response:
{
  "vector_matches": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "User authentication uses JWT tokens",
      "score": 0.92,
      "layer": "sm"
    }
  ],
  "graph_nodes": [...],
  "graph_edges": [...],
  "synthesized_context": "...",
  "statistics": {
    "vector_results": 5,
    "graph_nodes_found": 3
  }
}
```

---

### POST /memory/reflect

**Deprecated in:** v2.0.0-enterprise
**Replaced by:** `POST /v1/reflections/generate`

**Old Request:**
```json
{
  "memory_ids": ["mem_1", "mem_2", "mem_3"]
}
```

**Old Response:**
```json
{
  "reflection_id": "ref_789",
  "content": "Pattern detected: User prefers Python over JavaScript",
  "score": 0.88
}
```

**Migration:**
```json
// New API (v2.0.0-enterprise)
POST /v1/reflections/generate

Request:
{
  "tenant_id": "your-tenant-id",
  "project": "your-project",
  "reflection_type": "INSIGHT",
  "enable_clustering": true,
  "max_memories": 50
}

Response:
{
  "reflection": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "content": "Pattern detected: User prefers Python over JavaScript for data processing tasks",
    "reflection_type": "INSIGHT",
    "scoring": {
      "novelty_score": 0.85,
      "importance_score": 0.90,
      "utility_score": 0.88
    }
  },
  "statistics": {
    "memories_processed": 42,
    "clusters_found": 3
  }
}
```

---

## Breaking Changes in v2.0.0-enterprise

### 1. Layer Names

**Old (1.0.0-beta):**
- `episodic`
- `working`
- `semantic`
- `long_term`

**New (2.0.0-enterprise):**
- `em` (episodic memories)
- `wm` (working memories)
- `sm` (semantic memories)
- `ltm` (long-term memories)

### 2. Authentication

**Old:** Optional tenant_id in query params
**New:** Required tenant_id in request body + Bearer token authentication

### 3. Response Format

**Old:** Simple JSON with minimal metadata
**New:** Structured responses with:
- Detailed error messages
- Request tracking IDs
- Performance metrics
- Pagination info

---

## Migration Tools

### Automated Migration Script (Coming Soon)

We're working on an automated migration script to help you update your codebase:

```bash
# Not yet available
python scripts/migrate_to_v2.py --check
python scripts/migrate_to_v2.py --dry-run
python scripts/migrate_to_v2.py --execute
```

### Manual Migration Checklist

- [ ] Update all `/memory/add` calls to `/v1/memories/create`
- [ ] Update all `/memory/store` calls to `/v1/memories/create`
- [ ] Update all `/memory/query` calls to `/v1/search/hybrid`
- [ ] Update all `/memory/reflect` calls to `/v1/reflections/generate`
- [ ] Update layer names (episodic → em, working → wm, etc.)
- [ ] Add tenant_id and project to all requests
- [ ] Update error handling for new response format
- [ ] Test with new API before deploying

---

## Support Timeline

| Version | Old Endpoints | New Endpoints | Support |
|---------|---------------|---------------|---------|
| 1.0.0-beta | ✅ Supported | ❌ Not available | End of Life |
| 2.0.0-enterprise (current) | ⚠️ Warning logs | ✅ Recommended | Full support |
| 2.1.0 (planned) | ❌ Disabled by default | ✅ Only option | Full support |
| 3.0.0 (planned) | ❌ Completely removed | ✅ Only option | Full support |

---

## Getting Help

If you need assistance migrating from old endpoints:

1. **Documentation:** Read the [new API documentation](../api/rest-api.md)
2. **Examples:** Check [migration examples](../examples/)
3. **Issues:** Open a GitHub issue with tag `migration-help`
4. **Discord:** Join our community at https://discord.gg/rae-memory

---

## References

- **New API Documentation:** `/docs/api/rest-api.md`
- **Version Matrix:** `/docs/VERSION_MATRIX.md`
- **Migration Guide:** `/docs/guides/migration-v1-to-v2.md` (to be created)
- **OpenAPI Spec:** `http://localhost:8000/docs`

---

**Last Updated:** 2025-11-22
**Document Version:** 1.0
**Status:** Deprecated - For reference only
