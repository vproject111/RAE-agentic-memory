# PROMPTS

## 7.1 Prompt dla Gemini CLI (ARCHITEKTURA → KOD)
Rola: Senior Platform Engineer.
Cel: Wygeneruj kompletne moduły zgodne z kontraktami z `docs/OPENAPI.md`, `docs/MCP.md`, DDL w `infra/postgres/ddl/*.sql` i kolekcją Qdrant `infra/qdrant/collections.yaml`.

Wymagania:
1. Najpierw wczytaj kontrakty. Nie zmieniaj nazw pól.
2. Wygeneruj: modele Pydantic → routy FastAPI → middleware tenant (SET LOCAL app.current_tenant_id) → Cost-Guard → klient Qdrant (hybryda dense+sparse z RRF) → integracja z rerankerem (HTTP do apps/reranker-service).
3. Każda ścieżka: testy (pytest) i docstring.
4. OTel: spany retrieve, rerank, llm.call, cost.
5. Zwracaj JSON dokładnie wg OpenAPI.
6. Nie zmieniaj nazw i ścieżek.

FORMAT WYJŚCIA (wymagany):
```json
{
  "changeset": [
    {"path": "apps/memory-api/models.py", "content": "..."},
    {"path": "apps/memory-api/main.py", "content": "..."},
    {"path": "apps/memory-api/middleware/tenant.py", "content": "..."},
    {"path": "apps/memory-api/middleware/cost_guard.py", "content": "..."},
    {"path": "apps/memory-api/services/qdrant_client.py", "content": "..."},
    {"path": "apps/memory-api/routers/memory.py", "content": "..."},
    {"path": "apps/memory-api/routers/agent.py", "content": "..."},
    {"path": "apps/reranker-service/main.py", "content": "..."},
    {"path": "cli/gemini-cli/main.py", "content": "..."},
    {"path": "eval/run_eval.py", "content": "..."}
  ],
  "post_steps": ["make up", "make migrate", "pytest -q", "python eval/run_eval.py"]
}
```

## 7.2 Prompt dla Jules (KOD → CI/TESTY/UTRZYMANIE)
Rola: Senior DevOps & Test Engineer.
Zadanie: Dockerfile + docker compose, migracje (alembic), CI (GitHub Actions), Prometheus/Grafana, Makefile.

FORMAT WYJŚCIA:
```json
{
  "changeset": [
    {"path": "infra/docker compose.yml", "content": "..."},
    {"path": "apps/memory-api/Dockerfile", "content": "..."},
    {"path": "apps/reranker-service/Dockerfile", "content": "..."},
    {"path": ".github/workflows/ci.yml", "content": "..."},
    {"path": "Makefile", "content": "..."},
    {"path": "infra/grafana/dashboards/memory.json", "content": "..."}
  ],
  "post_steps": ["make up", "make migrate", "make seed", "pytest -q", "make eval"]
}
```
