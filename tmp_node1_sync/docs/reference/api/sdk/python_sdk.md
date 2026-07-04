# RAE Python SDK

The RAE Memory Python SDK provides a simple and idiomatic way to interact with your RAE Memory API from your Python applications.

## Installation

```bash
pip install rae-memory-sdk
```
*(Note: The package will be published to PyPI later. For now, you can install directly from source by navigating to `sdk/python` and running `pip install .`)*

## Configuration

The SDK looks for configuration in the following order:

1.  Parameters passed directly to the `MemoryClient` constructor.
2.  Environment variables (e.g., `RAE_API_URL`, `RAE_API_KEY`, `RAE_TENANT_ID`).
3.  A `.env` file in the current working directory.

Example `.env` file:
```
RAE_API_URL="http://localhost:8000"
RAE_API_KEY="your-secret-rae-api-key"
RAE_TENANT_ID="my-application-tenant"
```

## Usage

```python
from rae_memory_sdk import MemoryClient, StoreMemoryRequest, QueryMemoryRequest, MemoryLayer

# Initialize the client (configuration loaded from .env or env vars by default)
client = MemoryClient()

# --- Store a memory ---
new_memory = StoreMemoryRequest(
    content="The user prefers concise and direct answers.",
    source="user_feedback",
    importance=0.8,
    layer=MemoryLayer.ltm,
    tags=["user_preference", "communication"]
)
try:
    response = client.store(new_memory)
    print(f"Memory stored: {response.id}")
except Exception as e:
    print(f"Error storing memory: {e}")

# --- Query memories ---
query_text = "What are the user's communication preferences?"
try:
    query_results = client.query(query_text=query_text, k=3)
    print("\nQuery Results:")
    for result in query_results.results:
        print(f"- ID: {result.id}, Score: {result.score:.2f}, Content: {result.content[:50]}...")
except Exception as e:
    print(f"Error querying memories: {e}")

# --- Delete a memory ---
# Assuming you have a memory_id to delete
# memory_to_delete_id = "..."
# try:
#     delete_response = client.delete(memory_to_delete_id)
#     print(f"\nMemory deleted: {delete_response.message}")
# except Exception as e:
#     print(f"Error deleting memory: {e}")

# --- Other endpoints (stubs) ---
# client.evaluate()
# client.reflect()
# client.get_tags()
```