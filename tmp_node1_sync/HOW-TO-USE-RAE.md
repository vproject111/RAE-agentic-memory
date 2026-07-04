# How to Use RAE Memory

It needs to be USED ACTIVELY:
  1. Bootstrap at the beginning of the session
  2. Save decisions/insights during
  3. Handoff at the end
  4. Monitor health
  5. Fallback when it doesn't work

## Quick Start

### 1. Launch Environment

Standard Dev Environment:
```bash
make dev
# or
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**With Local LLM (Ollama):**
See [Local LLM Setup Guide](docs/guides/LOCAL_LLM_SETUP.md) for details.
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile local-llm up -d
```

### 2. Access Interfaces

- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Dashboard**: [http://localhost:8501](http://localhost:8501)
- **Database UI**: [http://localhost:8080](http://localhost:8080) (System: postgres, User: rae, Pass: rae_password, DB: rae)

### 3. Research Mode (Telemetry)

For deep analysis, debugging, and tracing distributed calls (RAE-Sync), you can run RAE in **Research Mode**. This enables OpenTelemetry, Jaeger, and detailed logging.

**Start Research Mode:**
```bash
make run-research
```

**Access Telemetry Tools:**
*   **Jaeger UI (Tracing):** [http://localhost:16686](http://localhost:16686) - Visualize request flows and latency.
*   **Prometheus Metrics:** [http://localhost:8888/metrics](http://localhost:8888/metrics) - Low-level OTel metrics.
*   **RAE Sync Dashboard:** [http://localhost:8000/docs#/Sync](http://localhost:8000/docs#/Sync) - Inspect mesh topology.

### 4. Agent Workflow

See [AGENT_CORE_PROTOCOL](docs/rules/AGENT_CORE_PROTOCOL.md) for the mandatory workflow rules.