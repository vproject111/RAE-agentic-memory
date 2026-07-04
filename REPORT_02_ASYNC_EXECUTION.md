# REPORT_02_ASYNC_EXECUTION.md

## Goal
Evaluate whether async behavior is intentional, consistent, observable, and safe under load.

## Findings

### Async Flow Map (Conceptual)
1. **API Ingress**: FastAPI (Async) receives request.
2. **Middleware**: Tenant and Budget enforcement (Async).
3. **Core Services**: `RAECoreService` and `ReflectionPipeline` (Async).
4. **IO Operations**: `asyncpg` (Postgres), `AsyncQdrantClient` (Vector), `redis` (Cache) - all non-blocking.
5. **Lifespan**: Connections managed via async context manager.

### Potential Deadlocks & Starvation Risks
- **CPU-Bound Blocking (HIGH RISK)**: `ReflectionPipeline._cluster_memories` performs `HDBSCAN` and `KMeans` clustering directly in the async event loop. Since these are heavy CPU operations from `scikit-learn`, they will block the entire event loop during execution, potentially causing timeouts for other concurrent requests.
- **Synchronous Migrations**: Handled correctly via `asyncio.to_thread` for Alembic.

### Observability Gaps
- **Tracing**: OpenTelemetry is integrated (`setup_opentelemetry`), but it's unclear if spans cover the internal clustering logic's performance characteristics.
- **Metrics**: Prometheus metrics are present, but might not capture event loop lag caused by CPU-bound clustering.

## Recommendations
- Offload `scikit-learn` clustering operations to a thread pool or process pool to prevent event loop starvation.
