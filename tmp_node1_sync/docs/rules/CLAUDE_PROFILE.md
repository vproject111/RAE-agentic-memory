# CLAUDE CODE AGENT PROFILE

> **Specific instructions for Claude Code (CLI).**

## 1. NATIVE TOOLS & CAPABILITIES

### Task Tool (Specialized Agents)
- **Explore**: `Task(subagent_type="Explore", ...)` for codebase discovery.
- **Plan**: `Task(subagent_type="Plan", ...)` for complex architectural changes.
- **When to use**: Codebase exploration, multi-step planning.
- **When NOT to use**: Simple file reads (use `Read`), specific searches (use `Glob`/`Grep`).

### TodoWrite (Progress Tracking)
- **Mandatory** for tasks > 3 steps.
- **Status**: Maintain exactly ONE `in_progress` item.
- **Update**: Update frequently to keep the user informed.

### Parallel Execution
- **Allowed**: `Read("file1"), Read("file2")` (Parallel reads).
- **Avoid**: Sequential dependencies in the same block.

## 2. BEST PRACTICES

- **WebSearch**: Use for current docs/libs (e.g., "FastAPI best practices 2025").
- **Git**: Use `Bash` tool for git commands. ALWAYS use `-m` for commits.
- **Formatting**: ALWAYS run `make format && make lint` before committing.

## 3. COMMON PITFALLS

- **Interactive Commands**: Do NOT use `nano`, `vim`. Use `Edit`.
- **Feature Branch Testing**: Do NOT run `make test-unit` on feature branches. Use `pytest --no-cov`.
