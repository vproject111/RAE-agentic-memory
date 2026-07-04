# Python SDK Reference

## Overview

The RAE Python SDK (`rae-memory-sdk`) provides a simple, type-safe interface for interacting with RAE from Python applications.

**Location**: `sdk/python/rae_memory_sdk/`

## Installation

```bash
pip install rae-memory-sdk

# Or from source:
cd sdk/python
pip install -e .
```

## Quick Start

```python
from rae_memory_sdk import MemoryClient

# Initialize client
client = MemoryClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id"
)

# Store a memory
memory_id = client.store_memory(
    content="User prefers dark mode and TypeScript",
    source="user_preferences",
    importance=0.8,
    layer="em",  # episodic
    tags=["preferences", "ui"],
    project="my-project"
)

# Query memories
results = client.query_memories(
    query="What are the user's UI preferences?",
    k=5,
    min_importance=0.5
)

for result in results:
    print(f"{result.content} (score: {result.score})")
```

## Core Methods

### store_memory()

Store a new memory in RAE.

```python
def store_memory(
    self,
    content: str,
    source: str,
    importance: float = 0.5,
    layer: str = "em",
    tags: Optional[List[str]] = None,
    project: str = "default",
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Store a memory.

    Args:
        content: Memory content (required)
        source: Source identifier (e.g., "agent", "user_input")
        importance: Importance score 0.0-1.0
        layer: Memory layer ("sm"=sensory, "em"=episodic, "ltm"=long-term, "rm"=reflective)
        tags: Optional list of tags
        project: Project identifier
        metadata: Optional metadata dict

    Returns:
        Memory ID (UUID string)
    """
```

**Example:**

```python
memory_id = client.store_memory(
    content="Bug fixed: database connection timeout handled",
    source="development",
    importance=0.7,
    layer="em",
    tags=["bug-fix", "database"],
    metadata={"pr_number": 123, "author": "dev@example.com"}
)
```

### query_memories()

Semantic search for relevant memories.

```python
def query_memories(
    self,
    query: str,
    k: int = 10,
    min_importance: float = 0.0,
    layers: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    project: str = "default",
    hybrid_search: bool = True
) -> List[MemoryResult]:
    """
    Query memories using semantic search.

    Args:
        query: Search query text
        k: Number of results to return
        min_importance: Minimum importance threshold
        layers: Filter by memory layers (e.g., ["em", "ltm"])
        tags: Filter by tags
        project: Project identifier
        hybrid_search: Use hybrid search (semantic + keyword)

    Returns:
        List of MemoryResult objects
    """
```

**Example:**

```python
# Find relevant technical decisions
results = client.query_memories(
    query="How did we handle authentication?",
    k=5,
    min_importance=0.6,
    layers=["em", "ltm"],
    tags=["authentication", "security"]
)

for result in results:
    print(f"[{result.importance:.2f}] {result.content}")
    print(f"  Tags: {', '.join(result.tags)}")
    print(f"  Score: {result.score:.3f}\n")
```

### query_graph()

GraphRAG query for complex reasoning.

```python
def query_graph(
    self,
    query: str,
    k: int = 10,
    max_depth: int = 2,
    project: str = "default"
) -> GraphQueryResult:
    """
    Query knowledge graph with multi-hop reasoning.

    Args:
        query: Natural language query
        k: Number of starting nodes
        max_depth: Maximum traversal depth
        project: Project identifier

    Returns:
        GraphQueryResult with entities, relationships, answer
    """
```

**Example:**

```python
result = client.query_graph(
    query="What dependencies does the authentication module have?",
    k=5,
    max_depth=2
)

print(f"Answer: {result.answer}")
print(f"\nEntities: {result.entities}")
print(f"Relationships: {result.relationships}")
```

### delete_memory()

Delete a specific memory.

```python
def delete_memory(self, memory_id: str) -> bool:
    """Delete memory by ID. Returns True if successful."""
```

### batch_store()

Store multiple memories efficiently.

```python
def batch_store(
    self,
    memories: List[Dict[str, Any]],
    project: str = "default"
) -> List[str]:
    """
    Store multiple memories in a single request.

    Args:
        memories: List of memory dicts with content, source, importance, etc.
        project: Project identifier

    Returns:
        List of memory IDs
    """
```

**Example:**

```python
memories = [
    {"content": "Memory 1", "source": "batch", "importance": 0.5},
    {"content": "Memory 2", "source": "batch", "importance": 0.6},
    {"content": "Memory 3", "source": "batch", "importance": 0.7}
]

ids = client.batch_store(memories, project="my-project")
```

## Advanced Features

### Reflections

Generate and query reflections:

```python
# Generate reflection from events
reflection = client.generate_reflection(
    events=[
        {"event_type": "tool_call", "content": "Called API"},
        {"event_type": "error_event", "content": "Timeout"}
    ],
    outcome="failure",
    task_description="API integration"
)

# Query reflections
reflections = client.query_reflections(
    query="API timeout issues",
    k=5,
    min_importance=0.7
)
```

### Cost Tracking

```python
# Get current cost usage
usage = client.get_cost_usage(month="2025-12")

print(f"Total cost: ${usage['total_cost_usd']:.2f}")
print(f"Budget: ${usage['budget_usd']:.2f}")
print(f"Remaining: ${usage['budget_remaining_usd']:.2f}")
```

### Decay and Maintenance

```python
# Trigger decay cycle
client.run_decay(tenant_id="tenant-123")

# Trigger summarization
client.summarize_session(session_id="session-uuid")
```

## Data Models

### MemoryResult

```python
@dataclass
class MemoryResult:
    id: str
    content: str
    source: str
    importance: float
    layer: str
    tags: List[str]
    created_at: datetime
    score: float  # Relevance score from query
    metadata: Dict[str, Any]
```

### GraphQueryResult

```python
@dataclass
class GraphQueryResult:
    answer: str
    entities: List[Entity]
    relationships: List[Relationship]
    confidence: float
    sources: List[str]
```

## Configuration

### Environment Variables

```bash
# SDK configuration
RAE_BASE_URL=http://localhost:8000
RAE_API_KEY=your-api-key
RAE_TENANT_ID=your-tenant-id

# Optional
RAE_TIMEOUT_SECONDS=30
RAE_MAX_RETRIES=3
```

### Client Options

```python
client = MemoryClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    tenant_id="your-tenant-id",
    timeout=30,
    max_retries=3,
    verify_ssl=True
)
```

## Examples

### Example 1: Team Assistant Memory

```python
# Store team preferences and decisions
client.store_memory(
    content="Team decided to use PostgreSQL for primary database",
    source="team_meeting",
    importance=0.9,
    tags=["decision", "database", "architecture"]
)

# Later, query for decisions
decisions = client.query_memories(
    query="What database should we use?",
    tags=["decision", "database"]
)
```

### Example 2: Project Code Memory

```python
# Store information about code changes
client.store_memory(
    content="Refactored authentication to use JWT tokens",
    source="git_commit",
    importance=0.8,
    tags=["refactoring", "authentication"],
    metadata={"commit_sha": "abc123", "pr_number": 456}
)

# Query for relevant code history
history = client.query_memories(
    query="How does authentication work?",
    tags=["authentication"]
)
```

### Example 3: Learning Agent

```python
# Store learning experiences
client.store_memory(
    content="API rate limit exceeded - implement exponential backoff",
    source="agent_experience",
    importance=0.85,
    layer="ltm",  # Long-term memory
    tags=["api", "rate-limit", "lesson"]
)

# Generate reflection on failure
reflection = client.generate_reflection(
    events=[...],
    outcome="failure",
    task_description="API calls"
)
```

## Error Handling

```python
from rae_memory_sdk.exceptions import (
    RAEException,
    AuthenticationError,
    BudgetExceededError,
    NotFoundError
)

try:
    client.store_memory(content="...", ...)
except BudgetExceededError as e:
    print(f"Budget exceeded: {e.budget_info}")
except AuthenticationError:
    print("Invalid API key")
except RAEException as e:
    print(f"RAE error: {e}")
```

## Related Documentation

- [Multi-Tenancy](./MULTI_TENANCY.md) - Tenant configuration
- [LLM Profiles](./LLM_PROFILES_AND_COST_GUARD.md) - Cost tracking
- [Reflection Engine](./REFLECTION_ENGINE_V2_IMPLEMENTATION.md) - Reflections API
