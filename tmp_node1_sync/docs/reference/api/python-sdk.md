# Python SDK

Official Python client for RAE Memory API.

## Installation

```bash
pip install rae-memory-sdk

# Or from source
cd sdk/python/rae_memory_sdk
pip install -e .
```

## Quick Start

```python
import asyncio
from rae_memory_sdk import MemoryClient

async def main():
    # Initialize client
    client = MemoryClient(
        api_url="http://localhost:8000",
        tenant_id="my-tenant",
        project_id="my-project",
        api_key="your-api-key"  # Optional if auth disabled
    )

    # Store a memory
    result = await client.store_memory(
        content="User prefers TypeScript over JavaScript",
        layer="episodic",
        tags=["preference", "coding"]
    )
    print(f"Stored: {result['id']}")

    # Query memories
    results = await client.query_memory(
        query="What languages does the user prefer?",
        top_k=5
    )
    for r in results:
        print(f"[{r['score']:.2f}] {r['content']}")

    # Hybrid search with graph
    results = await client.hybrid_search(
        query="authentication issues",
        use_graph=True,
        graph_depth=2
    )

    # Generate reflection
    reflection = await client.generate_reflection(
        memory_limit=50,
        min_confidence=0.8
    )
    print(f"Insight: {reflection['content']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

### MemoryClient

```python
class MemoryClient:
    def __init__(
        self,
        api_url: str,
        tenant_id: str,
        project_id: str = None,
        api_key: str = None
    )
```

### Store Memory

```python
async def store_memory(
    self,
    content: str,
    layer: str = "episodic",
    tags: List[str] = None,
    metadata: dict = None,
    importance: float = None
) -> dict
```

**Parameters:**
- `content` (str): Memory content
- `layer` (str): episodic, working, semantic, or ltm
- `tags` (List[str]): Tags for categorization
- `metadata` (dict): Additional metadata
- `importance` (float): Importance score (0-1)

**Returns:** Dict with memory ID and status

### Query Memory

```python
async def query_memory(
    self,
    query: str,
    top_k: int = 10,
    layers: List[str] = None,
    filters: dict = None
) -> List[dict]
```

**Parameters:**
- `query` (str): Search query
- `top_k` (int): Number of results
- `layers` (List[str]): Layers to search
- `filters` (dict): Additional filters

**Returns:** List of matching memories

### Hybrid Search

```python
async def hybrid_search(
    self,
    query: str,
    use_graph: bool = True,
    graph_depth: int = 2,
    top_k: int = 10
) -> dict
```

Combines vector search with graph traversal.

### Generate Reflection

```python
async def generate_reflection(
    self,
    memory_limit: int = 50,
    min_confidence: float = 0.7,
    focus: str = None
) -> dict
```

Generate insights from recent memories.

### Batch Operations

```python
async def store_batch(
    self,
    memories: List[dict]
) -> List[dict]
```

Store multiple memories efficiently.

### Memory Management

```python
async def get_memory(self, memory_id: str) -> dict
async def update_memory(self, memory_id: str, updates: dict) -> dict
async def delete_memory(self, memory_id: str) -> dict
async def list_memories(self, limit: int = 50, offset: int = 0) -> List[dict]
```

## Advanced Usage

### Custom Headers

```python
client = MemoryClient(
    api_url="http://localhost:8000",
    tenant_id="my-tenant",
    headers={"X-Custom-Header": "value"}
)
```

### Error Handling

```python
from rae_memory_sdk.exceptions import (
    RAEException,
    AuthenticationError,
    RateLimitError
)

try:
    await client.store_memory(...)
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after}s")
except RAEException as e:
    print(f"Error: {e}")
```

### Context Manager

```python
async with MemoryClient(...) as client:
    await client.store_memory(...)
# Automatically closes connection
```

### Streaming Results

```python
async for memory in client.stream_memories(query="..."):
    print(memory['content'])
```

## Examples

See `/examples` directory for complete examples:
- `quickstart.py` - Basic usage
- `agent-pipeline/` - Agent integration
- `e2e_basic_usage/` - End-to-end example

## Synchronous Client

For non-async code:

```python
from rae_memory_sdk import SyncMemoryClient

client = SyncMemoryClient(...)
result = client.store_memory(...)  # Synchronous
```

## See Also

- [REST API Reference](rest-api.md)
- [Examples](../examples/overview.md)
- [Architecture](../concepts/architecture.md)
