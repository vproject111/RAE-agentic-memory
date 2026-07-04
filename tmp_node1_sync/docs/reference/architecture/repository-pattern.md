# Repository Pattern Implementation

## Overview

RAE Memory Engine implements the Repository/DAO (Data Access Object) pattern to separate business logic from data access concerns. This architectural decision provides better testability, maintainability, and adheres to SOLID principles.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                     │
│                  routes/*, api/v1/*                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│              services/* (Business Logic)                    │
│  - EntityResolutionService                                  │
│  - ReflectionEngine                                         │
│  - CommunityDetectionService                                │
│  - HybridSearchService                                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repository Layer (DAO)                     │
│             repositories/* (Data Access)                    │
│  - GraphRepository                                          │
│  - MemoryRepository                                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
│        PostgreSQL (with pgvector extension)                 │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. Separation of Concerns
- **Services** focus on business logic and orchestration
- **Repositories** handle all SQL queries and database operations
- Clear responsibility boundaries

### 2. Testability
- Services can be unit tested with mocked repositories
- Repositories can be tested independently
- No need to mock database connections in service tests

### 3. Maintainability
- Database schema changes affect only repository layer
- Business logic changes don't touch SQL
- Easier to locate and fix data access issues

### 4. Consistency
- All database operations follow same pattern
- Standardized error handling
- Unified logging and monitoring

## GraphRepository

The `GraphRepository` provides all database operations for the knowledge graph.

### Core Methods

#### Node Operations
```python
async def get_all_nodes(tenant_id: str, project_id: str) -> List[Dict[str, Any]]
async def update_node_label(node_internal_id: int, new_label: str) -> bool
async def delete_node(node_internal_id: int) -> bool
async def upsert_node(tenant_id, project_id, node_id, label, properties) -> int
async def create_node(tenant_id, project_id, node_id, label, properties) -> bool
async def get_node_by_id(node_id, tenant_id, project_id) -> Optional[GraphNode]
async def get_nodes_by_ids(node_ids, tenant_id, project_id) -> List[GraphNode]
async def get_node_internal_id(tenant_id, project_id, node_id) -> Optional[int]
```

#### Edge Operations
```python
async def get_all_edges(tenant_id: str, project_id: str) -> List[Dict[str, Any]]
async def merge_node_edges(source_node_id: int, target_node_id: int) -> Dict[str, int]
async def delete_node_edges(node_internal_id: int) -> int
async def create_edge(tenant_id, project_id, source_id, target_id, relation, properties) -> bool
async def get_edges_between_nodes(node_ids, tenant_id, project_id) -> List[GraphEdge]
```

#### Batch Operations
```python
async def store_graph_triples(triples, tenant_id, project_id) -> Dict[str, int]
```

#### Graph Traversal
```python
async def traverse_graph_bfs(start_node_ids, tenant_id, project_id, max_depth) -> Tuple[List[GraphNode], List[GraphEdge]]
async def traverse_graph_dfs(start_node_ids, tenant_id, project_id, max_depth) -> Tuple[List[GraphNode], List[GraphEdge]]
```

#### Search Operations
```python
async def find_relevant_communities(query, tenant_id, project_id, limit=3) -> List[Dict[str, Any]]
async def find_nodes_by_content_match(content, tenant_id, project_id, limit=5) -> List[str]
```

## Refactored Services

### EntityResolutionService

**Purpose**: Orchestrates entity deduplication and merging in the knowledge graph.

**Refactoring Changes**:
- Removed direct SQL queries
- Uses `GraphRepository` for all database operations
- Improved testability with repository injection

**Example Usage**:
```python
# Before (Direct SQL)
async with self.pool.acquire() as conn:
    await conn.execute(
        "UPDATE knowledge_graph_nodes SET label = $1 WHERE id = $2",
        canonical_name, node_id
    )

# After (Repository Pattern)
await self.graph_repo.update_node_label(
    node_internal_id=node_id,
    new_label=canonical_name
)
```

### ReflectionEngine

**Purpose**: Generates reflective memories and extracts knowledge graph triples.

**Refactoring Changes**:
- Batch triple storage uses `GraphRepository.store_graph_triples()`
- Eliminated manual node and edge insertion logic
- Simplified transaction management

**Example Usage**:
```python
# Before (Direct SQL - multiple statements)
await conn.execute("INSERT INTO knowledge_graph_nodes ...")
source_node = await conn.fetchrow("SELECT id FROM ...")
await conn.execute("INSERT INTO knowledge_graph_edges ...")

# After (Repository Pattern - single call)
stats = await self.graph_repo.store_graph_triples(
    triples=triple_dicts,
    tenant_id=tenant_id,
    project_id=project_id
)
```

### CommunityDetectionService

**Purpose**: Detects communities in knowledge graph and creates super-nodes.

**Refactoring Changes**:
- Graph loading uses repository methods
- Super-node creation uses `upsert_node()`
- NetworkX graph construction simplified

**Example Usage**:
```python
# Before (Direct SQL)
nodes = await conn.fetch("SELECT id, label FROM knowledge_graph_nodes ...")
edges = await conn.fetch("SELECT source_node_id, target_node_id ...")

# After (Repository Pattern)
nodes = await self.graph_repo.get_all_nodes(tenant_id, project_id)
edges = await self.graph_repo.get_all_edges(tenant_id, project_id)
```

## Testing Strategy

### Repository Tests

Located in `tests/repositories/test_graph_repository.py`

**Strategy**: Mock database connections, verify SQL calls
```python
@pytest.mark.asyncio
async def test_get_all_nodes(mock_pool):
    pool, conn = mock_pool
    conn.fetch.return_value = [{"id": 1, "node_id": "node1", "label": "Label1"}]

    repo = GraphRepository(pool)
    nodes = await repo.get_all_nodes(tenant_id="tenant1", project_id="project1")

    assert len(nodes) == 1
    conn.fetch.assert_called_once()
```

### Service Tests

Located in `tests/services/`

**Strategy**: Mock repositories, verify business logic
```python
@pytest.mark.asyncio
async def test_merge_nodes_uses_repository(mock_dependencies):
    mock_pool, mock_graph_repo, mock_ml_client = mock_dependencies

    mock_graph_repo.merge_node_edges.return_value = {
        "outgoing_updated": 2,
        "incoming_updated": 1
    }

    service = EntityResolutionService(
        pool=mock_pool,
        graph_repository=mock_graph_repo
    )

    await service._merge_nodes(nodes, "project1", "tenant1")

    mock_graph_repo.merge_node_edges.assert_called_once()
```

## Migration Guide

### For New Services

1. **Inject GraphRepository in constructor**:
```python
def __init__(self, pool: asyncpg.Pool, graph_repository: GraphRepository = None):
    self.pool = pool
    self.graph_repo = graph_repository or GraphRepository(pool)
```

2. **Use repository methods instead of direct SQL**:
```python
# ❌ Don't do this
async with self.pool.acquire() as conn:
    await conn.execute("DELETE FROM knowledge_graph_nodes WHERE id = $1", node_id)

# ✅ Do this instead
await self.graph_repo.delete_node(node_internal_id=node_id)
```

3. **Write testable code**:
```python
# Constructor accepts optional repository for testing
service = MyService(
    pool=pool,
    graph_repository=mock_repository  # Inject mock in tests
)
```

### For Existing Services

1. **Identify direct SQL queries** in service methods
2. **Find or create equivalent repository method**
3. **Replace SQL with repository call**
4. **Add repository injection to constructor**
5. **Update or create tests** with mocked repository

## Performance Considerations

### Connection Pooling

Repositories use the same connection pool as direct SQL:
```python
async with self.pool.acquire() as conn:
    # No performance difference
```

### Batch Operations

Use batch methods for multiple operations:
```python
# ✅ Good: Single transaction
await repo.store_graph_triples(triples, tenant_id, project_id)

# ❌ Bad: Multiple round trips
for triple in triples:
    await repo.create_node(...)
    await repo.create_edge(...)
```

### Query Optimization

Repository methods use optimized SQL:
- Recursive CTEs for graph traversal
- Batch inserts with ON CONFLICT
- Proper indexing assumptions

## Error Handling

### Repository Layer

Repositories log errors and let exceptions propagate:
```python
async def delete_node(self, node_internal_id: int) -> bool:
    async with self.pool.acquire() as conn:
        result = await conn.execute(...)

        if success:
            logger.info("node_deleted", node_id=node_internal_id)
        else:
            logger.warning("node_deletion_failed", node_id=node_internal_id)

        return success
```

### Service Layer

Services handle business logic errors:
```python
try:
    await self.graph_repo.delete_node(node_id)
except Exception as e:
    logger.error("failed_to_delete_node", node_id=node_id, error=str(e))
    raise BusinessLogicError("Cannot delete node") from e
```

## Future Enhancements

### Planned Improvements

1. **MemoryRepository expansion** - Complete migration of all memory operations
2. **Caching layer** - Add Redis caching in repository methods
3. **Query builder** - Type-safe query construction
4. **Connection retry logic** - Automatic reconnection on failures
5. **Metrics collection** - Repository-level performance monitoring

### Additional Repositories

Candidates for extraction:
- `SemanticRepository` - Semantic memory operations
- `ReflectionRepository` - Reflection-specific queries
- `CacheRepository` - Cache operations abstraction

## References

- [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [DAO Pattern](https://www.oracle.com/java/technologies/dataaccessobject.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)

## Related Documentation

- [Architecture Overview](../concepts/architecture.md)
- [Testing Guide](../guides/testing.md)
- [Contributing Guidelines](../../CONTRIBUTING.md)
