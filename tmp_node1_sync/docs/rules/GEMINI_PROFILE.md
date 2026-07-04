# GEMINI AGENT PROFILE

> **Specific instructions for Gemini CLI Agent.**

## 1. BOOTSTRAPPING (Memory First)

On every new session:
1. **Check Memory**: `search_memory(query="project_rules_summary_v1", tags=["system", "rules", "bootstrap"])`
2. **Action**:
   - If found: Confirm "✅ Rules loaded from RAE Memory."
   - If not found: Read `docs/rules/AGENT_CORE_PROTOCOL.md`, summarize, and `save_memory`.

## 2. MEMORY USAGE (RAE)

- **Tool**: `save_memory`, `search_memory`, `get_related_context`.
- **When to Save**:
  - Completed workflow steps.
  - Bug fixes (what & why).
  - Key architectural decisions.
- **Tags**: Use meaningful tags (e.g., `["bug-fix", "critical", "auth"]`).

## 3. GEMINI SPECIFIC TIPS

- **Context Window**: You have a large context, but use `read_file` judiciously to avoid "lost in the middle" phenomena.
- **Thinking**: Explicitly state your plan using `write_todos` for complex tasks.
- **Silence**: Do not be verbose. 1-2 sentences max per turn unless explaining a complex issue.
- **Docker & Migrations**: Always delete `alembic/versions/__pycache__` after modifying migration files to prevent Docker using stale bytecode.

## 4. RATE LIMITS & RESOURCE EFFICIENCY

- **Respect Limits**: Strictly adhere to tool usage limits. Do not loop excessively.
- **Batching**: Prefer batch operations over single-item loops where possible.
- **Memory**: "Input/Output MUST flow through RAE to minimize token usage."

