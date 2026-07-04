# Developer Cheat Sheet & Quick Reference

> **For AI Agents:** Read this file at the start of every session to locate test commands, profiles, and MCP configurations.

## 🐍 Environment & Python
- **Virtual Env Python:** `./.venv/bin/python`
- **Pytest:** `./.venv/bin/pytest`
- **Activate:** `source .venv/bin/activate`

## 🧪 Testing Commands (Preferred)
Use `make` targets when possible, or direct paths for specific files.

| Task | Command | Description |
|------|---------|-------------|
| **Core Tests** | `make test-core` | Runs `rae-core` tests with coverage. |
| **Unit Tests** | `make test-lite` | Runs standard unit tests (CPU only). |
| **Integration** | `make test-int` | Runs DB/API contract tests (requires Docker). |
| **Compliance (ISO)** | `make test-compliance` | Runs ISO 42001 governance & approval tests. |
| **Specific File** | `./.venv/bin/pytest --no-cov path/to/test.py` | **BEST for dev loop.** Skips coverage checks. |
| **Focus Mode** | `make test-focus FILE=path/to/test.py` | Same as above, via Makefile. |
| **All Tests** | `make test-full-stack` | Runs everything (Unit + Int + LLM). Slow. |

> **Full Test Inventory:** See `TEST_INVENTORY.txt` for a complete list of all auto-discovered tests.

## 📊 Benchmark Map
All benchmarks are located in `benchmarking/`.

### 1. Standard Benchmarks (YAML-defined)
Run via: `python benchmarking/scripts/run_benchmark.py --set <name>.yaml`
Location: `benchmarking/sets/`

- **Academic Lite**: `academic_lite.yaml` (<10s, quick check)
- **Academic Extended**: `academic_extended.yaml` (~30s, standard check)
- **Industrial Small**: `industrial_small.yaml` (~2min, simulation)
- **Industrial Large**: `industrial_large.yaml` (~15min, stress test)
- **Stress Drift**: `stress_memory_drift.yaml` (Long-term stability)

### 2. Specialized "9/5" Benchmarks (Research)
Run via: `python -m benchmarking.nine_five_benchmarks.runner --benchmark <name>`
Location: `benchmarking/nine_five_benchmarks/`

- **LECT**: Long-term Event Consistency Test
- **MMIT**: Multi-Model Interference Test
- **GRDT**: Graph Retrieval Depth Test
- **RST**: Reflection Stability Test
- **ORB**: Orchestrator Routing Benchmark
- **MPEB**: Massive Text Embedding Benchmark (RAE-specific)

### 3. Performance & Infrastructure
Run via: `pytest benchmarking/performance/`

- **API Latency**: `test_api_latency_benchmarks.py`
- **DB Query**: `test_database_query_benchmarks.py`
- **Embedding Speed**: `test_embedding_speed_benchmarks.py`
- **Memory Usage**: `test_memory_usage_benchmarks.py`

## 🔌 MCP & Hotreload Configuration
For **RAE-First** communication in `hotreload` mode:

- **Config File:** `.claude/mcp.json`
- **Server Name:** `rae-dev`
- **API URL:** `http://localhost:8001`
- **Port Mapping:** `8001` (Dev/Hotreload), `8008` (Lite)
- **Startup:**
    1. Ensure Dev API is running: `make dev` or `docker compose up rae-api-dev`
    2. Connection check: `curl http://localhost:8001/health`

## 🐳 Docker Profiles
| Profile | Command | Ports | Description |
|---------|---------|-------|-------------|
| **Standard** | `docker compose up -d` | `:8000` | Production-like, all services. |
| **Dev** | `make dev-full` | `:8001` | Hotreload API, debug tools enabled. |
| **Lite** | `docker compose --profile lite up` | `:8008` | Minimal resource usage, no heavy ML. |

## 📂 Key Paths
- **Logs:** `logs/` (or `docker compose logs -f`)
- **Config:** `config/` (Default settings), `.env` (Secrets)
- **Core Logic:** `rae-core/`
- **API Logic:** `apps/memory_api/`
