# Knowledge Graph (GraphRAG)

**GraphRAG** (Graph-based Retrieval Augmented Generation) is RAE's knowledge graph system that captures relationships between memories, entities, and concepts for more intelligent retrieval and reasoning.

## What is GraphRAG?

Traditional RAG (Retrieval Augmented Generation) uses vector similarity to find relevant information. GraphRAG adds a **relationship layer** that understands how different pieces of information connect.

### Vector Search vs GraphRAG

**Vector Search Only:**
```
Query: "authentication issues"
Results: [memory1, memory2, memory3]  ← Similar embeddings
```

**GraphRAG (Hybrid):**
```
Query: "authentication issues"

Vector Results: [memory1, memory2, memory3]
     ↓
Graph Traversal: Discovers related concepts
     ↓
- auth.py (file entity)
- JWT tokens (concept)
- session management (related issue)
- security best practices (solution)
     ↓
Synthesized Context: Complete understanding with relationships
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  MEMORY STORE (Vector Database)                    │
│  ┌────────┐ ┌────────┐ ┌────────┐                 │
│  │ Mem 1  │ │ Mem 2  │ │ Mem 3  │  ...            │
│  └────┬───┘ └───┬────┘ └───┬────┘                 │
└───────┼─────────┼──────────┼───────────────────────┘
        │         │          │
        │    Extraction      │
        │         │          │
        ▼         ▼          ▼
┌─────────────────────────────────────────────────────┐
│  KNOWLEDGE GRAPH (PostgreSQL)                      │
│                                                     │
│    [Entity] ──relation──> [Entity]                │
│       │                       │                     │
│       │                       │                     │
│    [Entity] <──relation── [Entity]                │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Core Concepts

### Entities

**Entities** are the "nouns" in your knowledge graph - people, places, concepts, code files, etc.

```python
class Entity:
    id: str
    name: str
    type: str  # person, file, concept, organization, etc.
    properties: dict
    importance: float
```

**Examples:**
- `Entity(name="auth.py", type="file")`
- `Entity(name="JWT", type="concept")`
- `Entity(name="John Doe", type="person")`
- `Entity(name="Authentication", type="concept")`

### Relationships

**Relationships** are the "verbs" - how entities connect.

```python
class Relationship:
    id: str
    source_id: str  # From entity
    target_id: str  # To entity
    relation_type: str
    properties: dict
    confidence: float
```

**Common Relationship Types:**
- `MENTIONS` - Memory mentions an entity
- `RELATED_TO` - General relationship
- `PART_OF` - Hierarchical relationship
- `CAUSED_BY` - Causal relationship
- `USED_IN` - Usage relationship
- `IMPLEMENTED_IN` - Code relationships

**Example Graph:**
```
[auth.py] ─HAS_BUG→ [Session Timeout]
    │
    └─FIXED_BY→ [User]
    │
    └─RELATED_TO→ [JWT]
```

### Triples

Knowledge is stored as **triples** (subject-predicate-object):

```
(auth.py, HAS_BUG, "session timeout")
(User, FIXED, auth.py)
(auth.py, USES, JWT)
```

## Graph Construction

### Automatic Extraction

RAE automatically extracts entities and relationships from memories:

```python
memory = "User fixed a bug in auth.py related to JWT token expiration"

# LLM extraction
extraction = await extract_graph(memory)

# Result
{
    "entities": [
        {"name": "User", "type": "person"},
        {"name": "auth.py", "type": "file"},
        {"name": "JWT", "type": "concept"},
        {"name": "bug", "type": "issue"}
    ],
    "relationships": [
        {"source": "User", "relation": "FIXED", "target": "bug"},
        {"source": "bug", "relation": "IN_FILE", "target": "auth.py"},
        {"source": "bug", "relation": "RELATED_TO", "target": "JWT"}
    ]
}
```

### Extraction Prompt

```python
EXTRACTION_PROMPT = """
Extract entities and relationships from this text:

{text}

Identify:
1. **Entities**: People, files, concepts, organizations
2. **Relationships**: How entities connect

Format as JSON:
{
  "entities": [
    {"name": "...", "type": "person|file|concept|..."}
  ],
  "relationships": [
    {"source": "...", "relation": "...", "target": "..."}
  ]
}

Guidelines:
- Extract only significant entities
- Use clear, consistent relationship types
- Include confidence (0-1) for each extraction
"""
```

### Manual Graph Construction

You can also manually build the graph:

```python
# Add entity
await client.add_entity(
    name="auth.py",
    type="file",
    properties={
        "path": "src/auth.py",
        "language": "python",
        "lines": 250
    }
)

# Add relationship
await client.add_relationship(
    source="auth.py",
    relation="IMPORTS",
    target="jwt_library",
    properties={"version": "2.0"}
)
```

## Hybrid Search

GraphRAG combines vector search with graph traversal:

### 1. Vector Search (Semantic Similarity)

Find memories similar to query:

```python
query = "authentication problems"

# Vector search
vector_results = await vector_search(
    query=query,
    top_k=10
)
# Returns: memories with similar embeddings
```

### 2. Graph Expansion

Expand results by traversing the graph:

```python
# For each vector result, find connected entities
expanded_results = []

for memory in vector_results:
    # Get entities mentioned in memory
    entities = await get_memory_entities(memory.id)

    # Traverse graph (BFS/DFS)
    related = await graph_traverse(
        start_nodes=entities,
        max_depth=2,
        relation_types=["RELATED_TO", "CAUSED_BY"]
    )

    expanded_results.extend(related)
```

### 3. Context Synthesis

Combine vector and graph results:

```python
# Synthesize comprehensive context
context = await synthesize_context(
    vector_results=vector_results,
    graph_results=expanded_results,
    max_tokens=2000
)

# Use in LLM prompt
response = await llm.generate(
    prompt=f"Context: {context}\n\nQuestion: {query}",
    model="gpt-4"
)
```

## API Usage

### Basic Graph Query

```python
from rae_memory_sdk import MemoryClient

client = MemoryClient(api_url="http://localhost:8000")

# Hybrid search with graph
results = await client.hybrid_search(
    query="What caused the authentication bug?",
    use_graph=True,
    graph_depth=2,
    top_k=10
)

# Results include:
# - vector_matches: Similar memories
# - graph_nodes: Related entities
# - graph_edges: Relationships
# - synthesized_context: Combined understanding
```

### Graph Traversal

```python
# Find all entities related to a concept
entities = await client.graph_traverse(
    start_entity="authentication",
    relation_types=["RELATED_TO", "PART_OF"],
    max_depth=3
)

for entity in entities:
    print(f"{entity['name']} ({entity['type']})")
```

### Find Paths

```python
# Find connection between two entities
path = await client.find_path(
    start="auth.py",
    end="security_policy",
    max_depth=5
)

# Result: auth.py → uses → JWT → follows → security_policy
```

## Graph Algorithms

### PageRank - Find Important Entities

```python
# Find most important entities in graph
important_entities = await client.pagerank(
    top_k=10
)

for entity, score in important_entities:
    print(f"{entity}: {score:.3f}")

# Output:
# authentication: 0.892
# user_management: 0.756
# database: 0.643
```

### Community Detection

```python
# Discover clusters of related concepts
communities = await client.detect_communities()

for community in communities:
    print(f"Community {community['id']}:")
    for entity in community['members']:
        print(f"  - {entity}")

# Output:
# Community 1:
#   - authentication
#   - JWT
#   - OAuth
#   - session_management
# Community 2:
#   - database
#   - PostgreSQL
#   - migrations
```

### Shortest Path

```python
# Find shortest path between concepts
path = await client.shortest_path(
    start="bug",
    end="solution",
    max_hops=10
)

print(" → ".join(path))
# Output: bug → reported_in → auth.py → fixed_by → refactor → solution
```

## Advanced Features

### Temporal Graph

Track how relationships change over time:

```python
# Add timestamped relationship
await client.add_relationship(
    source="auth.py",
    relation="HAS_BUG",
    target="session_timeout",
    timestamp=datetime(2025, 1, 15),
    properties={"severity": "high"}
)

# Query graph at specific time
graph_state = await client.graph_at_time(
    timestamp=datetime(2025, 1, 15)
)

# Query temporal evolution
evolution = await client.graph_evolution(
    entity="auth.py",
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 1, 31)
)
```

### Multi-Hop Reasoning

Answer complex queries requiring multi-step reasoning:

```python
query = "What architectural decisions led to the current authentication implementation?"

# Multi-hop traversal
answer = await client.multi_hop_query(
    query=query,
    max_hops=5,
    reasoning_strategy="backward_chaining"
)

# Traces reasoning path
# Decision 1 → influenced → Design 2 → led to → Implementation 3
```

### Graph Embeddings

Generate embeddings for entities based on graph structure:

```python
# Node2Vec-style embeddings
embeddings = await client.compute_graph_embeddings(
    dimensions=128,
    walk_length=10,
    walks_per_node=80
)

# Use for similarity
similar_entities = await client.similar_by_graph_structure(
    entity="authentication",
    top_k=10
)
```

## Storage Schema

### PostgreSQL Tables

```sql
-- Entities table
CREATE TABLE kg_entities (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    properties JSONB,
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_entities_tenant_type ON kg_entities(tenant_id, type);
CREATE INDEX idx_entities_name ON kg_entities USING gin(to_tsvector('english', name));

-- Relationships table
CREATE TABLE kg_relationships (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    source_id UUID REFERENCES kg_entities(id),
    target_id UUID REFERENCES kg_entities(id),
    relation_type TEXT NOT NULL,
    properties JSONB,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_relationships_source ON kg_relationships(source_id);
CREATE INDEX idx_relationships_target ON kg_relationships(target_id);
CREATE INDEX idx_relationships_type ON kg_relationships(relation_type);

-- Memory-Entity associations
CREATE TABLE memory_entities (
    memory_id UUID REFERENCES memories(id),
    entity_id UUID REFERENCES kg_entities(id),
    PRIMARY KEY (memory_id, entity_id)
);
```

## Performance Optimization

### Indexing

```sql
-- Add indexes for common queries
CREATE INDEX idx_entities_importance ON kg_entities(importance DESC);
CREATE INDEX idx_relationships_confidence ON kg_relationships(confidence DESC);

-- Composite indexes
CREATE INDEX idx_rel_source_type ON kg_relationships(source_id, relation_type);
CREATE INDEX idx_rel_target_type ON kg_relationships(target_id, relation_type);
```

### Caching

```python
# Cache frequently accessed subgraphs
@cache(ttl=3600)
async def get_entity_neighborhood(entity_id: str, depth: int = 1):
    """Cache entity neighborhood for 1 hour."""
    return await graph.get_neighbors(entity_id, depth)
```

### Pruning

```python
# Remove low-importance entities periodically
@celery.task
def prune_graph():
    """Remove entities with low importance and no connections."""

    await db.execute("""
        DELETE FROM kg_entities
        WHERE importance < 0.1
        AND id NOT IN (
            SELECT DISTINCT source_id FROM kg_relationships
            UNION
            SELECT DISTINCT target_id FROM kg_relationships
        )
    """)
```

## Use Cases

### 1. Code Understanding

```python
# Query: "What files are affected by authentication changes?"

# GraphRAG finds:
# - Direct: auth.py
# - Related: jwt_utils.py (imports auth)
# - Indirect: user_controller.py (uses auth)
# - Tests: test_auth.py (tests auth)
```

### 2. Causal Analysis

```python
# Query: "Why did performance degrade?"

# Graph reveals causal chain:
# Performance degradation
#   ← caused by ← Slow queries
#   ← caused by ← Missing index
#   ← caused by ← Recent schema change
#   ← made by ← Developer A
```

### 3. Knowledge Discovery

```python
# Find hidden connections
path = await client.find_surprising_connections(
    entity="feature_X",
    min_path_length=3,
    max_path_length=6
)

# Discovers: feature_X → uses → library_Y → has_bug → affects → feature_Z
# Insight: Feature X might be affected by bug in library Y
```

## Configuration

```env
# .env
# Enable graph extraction
ENABLE_GRAPH_EXTRACTION=true

# Extraction model (needs good reasoning)
GRAPH_EXTRACTION_MODEL=gpt-4

# Auto-extract on memory store
AUTO_EXTRACT_GRAPH=true

# Graph traversal limits
MAX_GRAPH_DEPTH=5
MAX_GRAPH_NODES=1000

# Importance calculation
ENTITY_IMPORTANCE_ALGORITHM=pagerank  # pagerank, degree, betweenness
```

## Best Practices

### 1. Consistent Entity Naming

```python
# BAD
entities = ["Auth.py", "auth.py", "authentication.py"]  # Same entity!

# GOOD
entity = "auth.py"  # Canonical name
aliases = ["Auth.py", "authentication.py"]  # Track aliases
```

### 2. Meaningful Relationships

```python
# BAD
relation = "RELATED_TO"  # Too vague

# GOOD
relations = ["IMPORTS", "USES", "EXTENDS", "IMPLEMENTS"]  # Specific
```

### 3. Bidirectional Relationships

```python
# Add both directions for easier traversal
await add_relationship("A", "IMPORTS", "B")
await add_relationship("B", "IMPORTED_BY", "A")
```

### 4. Graph Validation

```python
# Validate graph periodically
@celery.task
def validate_graph():
    """Check graph integrity."""

    # Find orphaned entities
    orphans = await find_orphaned_entities()

    # Find circular dependencies
    cycles = await detect_cycles()

    # Report anomalies
    if orphans or cycles:
        await alert_admin(orphans=orphans, cycles=cycles)
```

## Troubleshooting

### Graph Too Large

```python
# Limit graph size
await prune_low_importance_entities(threshold=0.2)
await remove_old_relationships(days=90)
await consolidate_similar_entities()
```

### Slow Graph Queries

```sql
-- Add missing indexes
CREATE INDEX idx_rel_composite ON kg_relationships(source_id, relation_type, target_id);

-- Analyze query plans
EXPLAIN ANALYZE
SELECT * FROM kg_relationships WHERE source_id = '...';
```

### Extraction Quality

```python
# Improve extraction prompt
# - Be more specific about entity types
# - Provide examples
# - Use better model (GPT-4 > GPT-3.5)

# Validate extractions
confidence_threshold = 0.8
if extraction.confidence < confidence_threshold:
    await manual_review(extraction)
```

## Further Reading

- [Memory Layers](memory-layers.md) - Foundation for graph
- [Reflection Engine](reflection-engine.md) - Generates insights from graph
- [Hybrid Search](../guides/hybrid-search.md) - Combining vector + graph

---

**Next**: [Architecture Overview →](architecture.md)
