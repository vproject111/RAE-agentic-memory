# Developer Documentation Portal

**Welcome, Developer!** 👋

This is your central hub for building with RAE (Reflective Agentic-memory Engine). Whether you're integrating RAE into your AI application, contributing to the codebase, or exploring the API, you'll find everything you need here.

## 🚀 Quick Start (5 minutes)

**New to RAE?** Start here:

1. **[Installation Guide](../../../README.md#installation)**
   - Docker Compose setup (recommended)
   - Local development setup
   - Requirements: Docker, Python 3.11+

2. **[First API Call](../../../examples/quickstart.py)**
   ```python
   from rae_memory_sdk import RAEClient

   client = RAEClient(api_key="your-key")

   # Store a memory
   memory = client.memories.create(
       content="My first memory",
       metadata={"source": "quickstart"}
   )

   # Retrieve similar memories
   results = client.memories.search(query="first")
   ```

3. **[Interactive Demo](../../../examples/quickstart.py)**
   ```bash
   make demo  # Run interactive quickstart
   ```

## 📚 Core Documentation

### API Reference

| Resource | Description | Link |
|----------|-------------|------|
| **REST API** | Complete HTTP API reference | [OpenAPI Docs](http://localhost:8000/docs) |
| **Python SDK** | RAE Memory SDK documentation | [SDK Reference](../../../sdk/python/rae_memory_sdk/README.md) |
| **API Endpoints** | Auto-generated endpoint list | [Endpoints](../../.auto-generated/api/endpoints.md) |

### Architecture & Concepts

| Topic | Description | Link |
|-------|-------------|------|
| **System Architecture** | High-level design overview | [Architecture Overview](../../reference/architecture/README.md) |
| **Memory Layers** | Episodic, Working, Semantic, LTM | [Memory Layers](../../reference/architecture/memory-layers.md) |
| **Hybrid Search** | Vector + keyword search (v3) | [Hybrid Search](../../reference/architecture/hybrid-search.md) |
| **LLM Orchestrator** | Multi-model flexibility (v2.1.1) | [LLM Orchestrator](../../../docs/project-design/active/LLM_orchestrator/LLM_ORCHESTRATOR.md) |
| **Reflection Engine** | Autonomous memory consolidation | [Reflection Mode](../../../docs/REFLECTION_MODE.md) |

### Integration Guides

| Framework | Description | Link |
|-----------|-------------|------|
| **LangChain** | RAE + LangChain integration | [LangChain Guide](../../../integrations/langchain/README.md) |
| **LlamaIndex** | RAE + LlamaIndex integration | [LlamaIndex Guide](../../../integrations/llama_index/README.md) |
| **MCP (Model Context Protocol)** | Claude Desktop integration | [MCP Guide](../../../integrations/mcp/README.md) |
| **Ollama** | Local LLM wrapper | [Ollama Guide](../../../integrations/ollama-wrapper/README.md) |

## 🧪 Testing & Development

### Running Tests

```bash
# Feature branch: Test ONLY your new code
pytest --no-cov apps/memory_api/tests/services/test_my_feature.py

# Develop branch: Run FULL test suite
make test-unit

# Watch mode for TDD
make test-watch
```

**Important:** See [Testing Policy](../../AGENTS_TEST_POLICY.md) for philosophy.

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Security scan
make security
```

### Local Development

```bash
# Start API in dev mode (hot-reload)
make dev

# Access API docs
open http://localhost:8000/docs

# View logs
make logs-api
```

## 🏗️ Contributing

### Before You Start

**Required reading:**
1. [Onboarding Guide](../../../ONBOARDING_GUIDE.md) - 15 minutes
2. [Project Structure](../../../PROJECT_STRUCTURE.md) - Know where files go
3. [Conventions](../../../CONVENTIONS.md) - Architecture patterns
4. [Critical Agent Rules](../../../CRITICAL_AGENT_RULES.md) - Mandatory rules

### Development Workflow

```bash
# 1. Create feature branch from develop
git checkout develop && git pull
git checkout -b feature/my-feature

# 2. Use templates for new code
cp .ai-templates/service_template.py apps/memory_api/services/my_service.py

# 3. Implement + test (only new code)
pytest --no-cov apps/memory_api/tests/services/test_my_service.py

# 4. Format & lint
make format && make lint

# 5. Commit
git commit -m "feat: add my feature"

# 6. Push and create PR
git push origin feature/my-feature
```

**See:** [Branching Strategy](../../BRANCHING.md) for full workflow.

### Code Templates

- [Repository Template](.ai-templates/repository_template.py) - Data access layer
- [Service Template](.ai-templates/service_template.py) - Business logic
- [Route Template](.ai-templates/route_template.py) - API endpoints
- [Test Template](.ai-templates/test_template.py) - Testing patterns

## 🔍 Key Features

### 1. Multi-Layer Memory Architecture

```python
# Episodic Memory (short-term, raw events)
client.memories.create(content="User clicked button", layer="episodic")

# Working Memory (active context)
client.memories.create(content="Current task context", layer="working")

# Semantic Memory (long-term knowledge graph)
client.memories.create(content="Domain knowledge", layer="semantic")

# Long-Term Memory (consolidated memories)
client.memories.create(content="Important patterns", layer="ltm")
```

### 2. Hybrid Search (Vector + Keyword)

```python
# Combines dense vectors + BM25 + Smart Re-Ranker
results = client.memories.search(
    query="authentication bug",
    search_type="hybrid",  # or "vector", "keyword"
    limit=10
)
```

### 3. Reflection Engine

```python
# Autonomous memory consolidation
client.reflections.trigger(
    memory_ids=["mem1", "mem2", "mem3"],
    mode="pattern_detection"  # or "summarization", "abstraction"
)
```

### 4. Multi-Tenancy

```python
# Automatic tenant isolation
client = RAEClient(api_key="your-key", tenant_id="org-123")

# All queries automatically scoped to tenant
memories = client.memories.list()  # Only org-123's memories
```

### 5. LLM Orchestrator (Provider-Agnostic)

```yaml
# Single model
llm:
  mode: single
  provider: anthropic
  model: claude-3-5-sonnet-20241022

# Fallback chain
llm:
  mode: fallback
  models:
    - provider: anthropic
      model: claude-3-5-sonnet-20241022
    - provider: openai
      model: gpt-4

# Ensemble (parallel + voting)
llm:
  mode: ensemble
  models:
    - provider: anthropic
      model: claude-3-5-sonnet-20241022
    - provider: openai
      model: gpt-4
```

## 🐛 Troubleshooting

### Common Issues

#### Issue: API returns 401 Unauthorized

**Cause:** Missing or invalid API key

**Solution:**
```bash
# Check .env file
cat .env | grep API_KEY

# Verify API is running
curl http://localhost:8000/health
```

#### Issue: Docker containers not starting

**Cause:** Port conflict or missing dependencies

**Solution:**
```bash
# Check running containers
docker ps

# Stop conflicting services
docker compose down

# Rebuild and start
docker compose up --build
```

#### Issue: Tests failing with "tenant_id required"

**Cause:** Missing tenant isolation in query

**Solution:**
```python
# ❌ WRONG - Missing tenant_id
query = "SELECT * FROM memories WHERE id = $1"

# ✅ CORRECT - Includes tenant_id
query = "SELECT * FROM memories WHERE id = $1 AND tenant_id = $2"
```

**See:** [CRITICAL_AGENT_RULES.md](../../../CRITICAL_AGENT_RULES.md) RULE #4

## 📊 Monitoring & Observability

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# All services health
make health
```

### Metrics

- **Prometheus:** `http://localhost:9090` (if enabled)
- **Grafana:** `http://localhost:3000` (if enabled)
- **Logs:** `make logs` or `docker compose logs -f`

### CI/CD Status

- **GitHub Actions:** [View Workflows](https://github.com/dreamsoft-pro/RAE-agentic-memory/actions)
- **Test Coverage:** [Coverage Report](../../.auto-generated/metrics/DASHBOARD.md)

## 🎓 Learning Resources

### Tutorials

| Tutorial | Level | Time | Link |
|----------|-------|------|------|
| Getting Started | Beginner | 15 min | [Quickstart](../../../examples/quickstart.py) |
| Building a Chatbot | Intermediate | 30 min | Coming soon |
| Advanced RAG | Advanced | 45 min | Coming soon |

### Examples

- [Basic CRUD Operations](../../../examples/basic_crud.py)
- [Hybrid Search Demo](../../../examples/hybrid_search_demo.py)
- [Reflection Pipeline](../../../examples/reflection_demo.py)
- [LangChain Integration](../../../integrations/langchain/examples/)

### Video Tutorials

Coming soon!

## 💬 Community & Support

### Get Help

- **GitHub Issues:** [Report bugs or request features](https://github.com/dreamsoft-pro/RAE-agentic-memory/issues)
- **Documentation:** You're reading it!
- **Examples:** [Browse examples/](../../../examples/)

### Contributing

We welcome contributions! See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for guidelines.

**Quick contribution checklist:**
- [ ] Read [Onboarding Guide](../../../ONBOARDING_GUIDE.md)
- [ ] Follow [Conventions](../../../CONVENTIONS.md)
- [ ] Use [Code Templates](../../../.ai-templates/)
- [ ] Write tests (see [Test Policy](../../AGENTS_TEST_POLICY.md))
- [ ] Follow [Branching Strategy](../../BRANCHING.md)

## 🚑 Data Recovery & Maintenance

### Recovering "Lost" Memories (Layer Normalization)

If you have upgraded from an older version of RAE, you might find that some memories seem to be missing. This is often due to a change in memory layer naming conventions (e.g., `ltm` -> `semantic`, `em` -> `episodic`).

We provide a utility script to normalize these layer names and restore access to your data.

**How to run:**

```bash
# Run the recovery script
python scripts/recover_memory_layers.py
```

**What it does:**
1. Connects to the RAE database.
2. Updates legacy layer names to the new standard:
   - `em` -> `episodic`
   - `ltm` / `sm` -> `semantic`
   - `stm` / `wm` -> `working`
   - `rm` -> `reflective`
3. Reports the number of recovered records.

### Database Health Check

To verify which tables are actually storing data and check the overall health of your database structure, use the stats utility:

```bash
# Check database usage
python scripts/db_stats.py
```

This will output a report showing row counts for all tables, helping you verify data persistence and identify unused features.

### Graph Snapshots & Restore

For enterprise users employing the Knowledge Graph, RAE supports full point-in-time recovery via snapshots.

**Restore a snapshot:**

```bash
curl -X POST http://localhost:8000/v1/graph-management/snapshots/{snapshot_id}/restore \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "restore_mode": "replace",
    "create_backup": true
  }'
```

See [Graph Enhanced Guide](../enterprise/GRAPH_ENHANCED_GUIDE.md) for full details.

## 🗺️ Roadmap

**Current Version:** 1.0.0

**Upcoming Features:**
- GraphRAG entity resolution
- Advanced reflection modes
- Multi-modal memory support
- Distributed deployment
- Real-time streaming

See [TODO.md](../../../TODO.md) for complete roadmap.

## 📖 Reference Links

### Essential Documentation

- [README.md](../../../README.md) - Project overview
- [ONBOARDING_GUIDE.md](../../../ONBOARDING_GUIDE.md) - New developer onboarding
- [PROJECT_STRUCTURE.md](../../../PROJECT_STRUCTURE.md) - File organization
- [CONVENTIONS.md](../../../CONVENTIONS.md) - Architecture patterns

### API & SDK

- [REST API Docs](http://localhost:8000/docs) - Interactive OpenAPI docs
- [Python SDK](../../../sdk/python/rae_memory_sdk/) - Official Python client
- [API Endpoints](../../.auto-generated/api/endpoints.md) - Auto-generated list

### Architecture

- [Architecture Overview](../../reference/architecture/README.md)
- [Hybrid Search](../../reference/architecture/hybrid-search.md)
- [Memory Layers](../../reference/architecture/memory-layers.md)
- [LLM Orchestrator](../../../docs/project-design/active/LLM_orchestrator/LLM_ORCHESTRATOR.md)

### Testing & Quality

- [Testing Policy](../../AGENTS_TEST_POLICY.md) - Tests as contracts
- [Integration Checklist](../../../INTEGRATION_CHECKLIST.md) - Pre-merge verification
- [Branching Strategy](../../BRANCHING.md) - Git workflow

---

**Need help?** Start with [Quickstart](../../../examples/quickstart.py) or check [Troubleshooting](#-troubleshooting).

**Want to contribute?** Read [CONTRIBUTING.md](../../../CONTRIBUTING.md) and [Onboarding Guide](../../../ONBOARDING_GUIDE.md).

**Last Updated:** 2025-12-06
