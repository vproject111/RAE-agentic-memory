# RAE Project Instructions for GitHub Copilot

When generating code or providing git commands for the RAE project, follow these specific guidelines:

## Git Workflow & Branching

We follow a strict Git Flow variant (see `docs/BRANCHING.md`):

1.  **Features**: Always start from `develop`.
    - Pattern: `feature/description`
    - Command: `git checkout develop && git pull && git checkout -b feature/my-feature`

2.  **Hotfixes**: Fixes for production issues start from `main`.
    - Pattern: `hotfix/description`
    - Command: `git checkout main && git pull && git checkout -b hotfix/fix-id`

3.  **Releases**: Start from `develop`.
    - Pattern: `release/x.y`

4.  **Main Integrity**:
    - BEFORE merging any branch to `main`, you must confirm that GitHub Actions CI has passed.
    - Use `gh run watch` to wait for tests.
    - Do not merge if CI fails.

## Code Standards

- **Stack**: Python 3.11+, FastAPI, PostgreSQL (asyncpg), Qdrant, Redis.
- **Style**: We use `black` (100 chars), `isort`, and `ruff`.
- **Testing**: Always include unit tests (`pytest`). Use mocking for external services (LLM, DB).
- **Async**: Use `async/await` for all I/O operations (DB, API calls).

## Architecture Boundaries

- **API Layer**: `apps/memory_api/routes` or `api/v1` - Input validation, auth checks.
- **Service Layer**: `apps/memory_api/services` - Business logic, orchestration.
- **Data Access**: `apps/memory_api/repositories` - Direct DB/Qdrant interactions.
- **Models**: `apps/memory_api/models` - Pydantic models and DB schemas.

Do not mix business logic into the API layer. Use Dependency Injection.
