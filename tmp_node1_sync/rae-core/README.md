# RAE-core

**Pure Python memory system for AI agents**

RAE-core is the foundational library for the RAE (Reflective Agentic Engine) ecosystem. It provides a complete, storage-agnostic implementation of:

- **4-layer memory architecture** (Sensory, Working, Long-term, Reflective)
- **3-layer mathematical framework** (Structure Analysis, Dynamics Tracking, Policy Optimization)
- **Hybrid search engine** (Vector + Graph + Sparse + Full-text)
- **Reflection system** (Actor-Evaluator-Reflector pattern)
- **Context management** with intelligent scoring and decay

## Key Features

- **Storage Agnostic**: Works with any storage backend through abstract interfaces
- **LLM Optional**: Can run with rule-based fallbacks (no API calls required)
- **Offline First**: Designed to work completely offline
- **Type Safe**: Full type hints with mypy strict mode
- **Zero Infrastructure**: No FastAPI, PostgreSQL, or Docker required
- **Extensible**: Clean interfaces for custom implementations

## Installation

### Basic Installation (Reference Adapters)

```bash
pip install rae-core
```

This includes:
- **InMemoryStorage** - Dictionary-based storage for testing/development
- **InMemoryCache** - Dictionary-based cache with TTL support
- **InMemoryVectorStore** - Numpy-based vector similarity search
- **SQLiteStorage** - File-based storage with FTS5 full-text search (via `aiosqlite`)
- **SQLiteVectorStore** - File-based vector storage

### Production Adapters (Optional)

For production deployments, install the appropriate extras:

```bash
# PostgreSQL storage
pip install rae-core[postgres]

# Redis cache
pip install rae-core[redis]

# Qdrant vector store
pip install rae-core[qdrant]

# All production adapters
pip install rae-core[all]

# Development tools
pip install rae-core[dev]
```

## Quick Start

```python
from rae_core import RAEEngine
from apps.memory_api.adapters.memory import InMemoryStorage, InMemoryVectorStore

# Initialize with in-memory storage (no dependencies)
engine = RAEEngine(
    storage=InMemoryStorage(),
    vector_store=InMemoryVectorStore(),
    enable_llm=False  # Use rule-based fallback
)

# Store a memory
memory_id = await engine.store_memory(
    content="User prefers Python over JavaScript",
    layer="episodic",
    tags=["preference", "programming"]
)

# Search memories
results = await engine.search(
    query="What does the user like?",
    strategy="hybrid",
    limit=5
)

for result in results:
    print(f"{result.score}: {result.content}")
```

## Production Usage

### PostgreSQL Storage

```python
from rae_core import RAEEngine
from apps.memory_api.adapters.postgres import PostgreSQLStorage

engine = RAEEngine(
    storage=PostgreSQLStorage(
        dsn="postgresql://user:pass@localhost/rae"
    )
)
```

### Redis Cache

```python
from apps.memory_api.adapters.redis import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    prefix="rae:"
)
```

### Qdrant Vector Store

```python
from apps.memory_api.adapters.qdrant import QdrantVectorStore

vector_store = QdrantVectorStore(
    url="http://localhost:6333",
    collection_name="rae_vectors"
)
```

## Configuration & Telemetry

RAE-core uses `pydantic-settings` for configuration. All settings can be overridden via environment variables with the `RAE_` prefix.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `RAE_SENSORY_MAX_SIZE` | Max items in sensory layer | 100 |
| `RAE_WORKING_MAX_SIZE` | Max items in working memory | 50 |
| `RAE_EPISODIC_MAX_SIZE` | Max items in episodic memory | 500 |
| `RAE_DECAY_RATE` | Memory decay rate (0.0-1.0) | 0.95 |
| `RAE_OTEL_ENABLED` | Enable OpenTelemetry tracing | `True` |

### Telemetry (Privacy-First)

RAE-core is designed with a **Privacy-First** approach. While OpenTelemetry support is built-in via the `RAE_OTEL_ENABLED` flag (default: `True`), RAE-core **does not** initialize any telemetry exporters automatically.

It is up to the hosting application (e.g., RAE-Server, RAE-Lite) to configure the OpenTelemetry SDK and exporters. This ensures no data leaves the system without explicit configuration by the implementer.

To disable telemetry support completely:
```bash
export RAE_OTEL_ENABLED=False
```

## Architecture

```
rae_core/
├── interfaces/     # Abstract interfaces (IStorage, IVectorStore, ILLMProvider)
├── models/         # Pydantic data models
├── layers/         # 4-layer memory architecture
├── math/           # Mathematical scoring and optimization
├── search/         # Hybrid search engine
├── reflection/     # Reflection system
├── context/        # Context building
├── scoring/        # Memory scoring algorithms
├── llm/            # LLM orchestration (optional)
├── sync/           # Sync protocol (for RAE-Sync)
└── engine.py       # Main RAEEngine entry point
```

## Documentation

See the [full documentation](https://github.com/dreamsoft-pro/RAE-agentic-memory/tree/main/rae-core/docs) for:

- Architecture overview
- API reference
- Implementation guides
- Custom adapters

## Ecosystem

RAE-core powers multiple products:

- **RAE-Server**: Enterprise multi-tenant server (FastAPI + PostgreSQL + Qdrant)
- **RAE-Lite**: Local desktop app (SQLite + no Docker)
- **RAE-Mobile**: iOS/Android app (future)
- **RAE-Sync**: Cross-device sync protocol

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Author

Grzegorz Leśniowski - [DreamSoft](https://dreamsoft.pro)
