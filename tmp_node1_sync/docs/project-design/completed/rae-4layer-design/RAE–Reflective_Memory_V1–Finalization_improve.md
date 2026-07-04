# RAE–Reflective_Memory_v1  
## Closure Plan & Definition of Done

**Baseline state:**  
- Code: `project_dump.txt` (post latest Claude iteration)  
- Docs: `REFLECTIVE_MEMORY_V1.md`, `STATUS.md`, `RAE-improve_01.md`, `RAE-improve-02.md`  
- Marker: **RAE-ReflectiveMemory-state-2025-11-28-pre-closure**

**Goal of this document:**  
Provide a *single, final* checklist that, once completed, allows you uczciwie powiedzieć:

> **„Reflective Memory v1 is DONE (for real), RAE Lite is ready for serious PoC in big companies.”**

---

## 0. Work mode & reality check

Before touching anything in code for any item below:

1. **Always check the current code first**, not just documentation.
2. For each subsection:
   - mark current status (`implemented / partial / missing`),
   - do the minimal necessary changes,
   - add/update tests & docs.

At the end, all sections 1–5 should have status `DONE`.

---

## 1. Reflective Memory Engine – correctness & completeness

**Objective:** Reflective Memory v1 is internally coherent and behaves as described in `REFLECTIVE_MEMORY_V1.md`.

### 1.1. Data model & types

- [ ] Single source of truth for mapping:

  | Conceptual Layer | `layer` (enum) | `memory_type` (typical)           |
  |------------------|----------------|------------------------------------|
  | Sensory/STM      | `stm`          | `sensory`                          |
  | Working/Episodic | `em` / `stm`   | `episodic`                         |
  | LTM              | `ltm` / `em`   | `episodic`, `semantic`, `profile` |
  | Reflective       | `rm`           | `reflection`, `strategy`          |

- [ ] This exact table exists in one doc (e.g. `docs/MEMORY_MODEL.md`) and is linked from:
  - `REFLECTIVE_MEMORY_V1.md`
  - any other doc mentioning “4 layers”.

- [ ] DB schema matches the above:
  - `memory_type`, `layer`, `importance`, `usage_count`, `last_accessed_at`, `session_id` are present and used.
  - Migrations are clean and replayable on a fresh DB.

### 1.2. Scoring & retrieval

- [ ] `compute_memory_score` implements the formula:

  \[
  final\_score = α · relevance + β · importance + γ · recency
  \]

  with config-driven weights and decay parameters.

- [ ] All memory retrieval paths (at least):
  - `/v1/memory/search`
  - `/v1/search/hybrid`
  - internal retrieval in `ContextBuilder`

  use **one canonical scoring implementation** (no custom “shortcut” scoring hidden in services).

- [ ] There is at least one test that:
  - sets up memories with different relevance, importance, recency,
  - asserts relative ordering after scoring.

---

## 2. Background maintenance – decay, summarization, dreaming

**Objective:** Memory actually *ages*, *compresses* and *consolidates* itself over time – and this is observable.

### 2.1. Decay

- [ ] There is a clear entrypoint for decay:
  - Celery task / CLI command like `rae_maintenance decay`.
- [ ] Decay:
  - never produces `importance < 0` (configurable floor),
  - decays old, rarely used memories stronger than fresh, frequently used ones.
- [ ] Logging:
  - number of updated rows,
  - min/avg/max delta importance.
- [ ] Metrics (if Prometheus is enabled):
  - `rae_reflective_decay_updated_total`.
- [ ] Test:
  - creates memories with different ages and usage,
  - runs decay once,
  - asserts expected direction/order of changes.

### 2.2. Summarization

- [ ] Summarization worker exists and is callable:
  - Celery task / CLI: `rae_maintenance summarize`.
- [ ] Summaries:
  - are only generated for sessions crossing a configurable threshold (length/time/importances),
  - are stored as `memory_type="episodic_summary"` linked to `session_id`.
- [ ] Logging:
  - number of sessions considered,
  - number of summaries created.
- [ ] Test:
  - creates at least one long session,
  - runs summarization,
  - asserts presence of `episodic_summary` and correct `session_id`.

### 2.3. Dreaming (reflections & strategies in the background)

- [ ] Dreaming worker exists and is callable:
  - Celery task / CLI: `rae_maintenance dream`.
- [ ] Selection rules:
  - picks only memories with `importance >= DREAMING_IMPORTANCE_THRESHOLD`,
  - does NOT re-process recently dreamed episodes too often (simple cooldown / timestamp).
- [ ] New `reflection`/`strategy` entries:
  - are linked back to source memories (via graph or parent ids),
  - are deduplicated at least heuristically (no flood of near-identical reflections).
- [ ] Logging:
  - number of candidate episodes,
  - number of reflections/strategies created.
- [ ] Test:
  - creates high-importance episodes,
  - runs dreaming,
  - asserts new `memory_type in ("reflection", "strategy")` with links to those episodes.

---

## 3. Agent integration – ContextBuilder & Actor–Evaluator–Reflector

**Objective:** Agents consistently use reflective memory via a **single, canonical path**.

### 3.1. ContextBuilder as single entrypoint

- [ ] All agent-like entrypoints:
  - `/v1/agent/execute`
  - MCP/IDE integrations
  - any CLI agent loop
- [ ] …use pattern:

  ```python
  context = context_builder.build_context(...)
  prompt = context.to_prompt()
(or documented equivalent).

 No remaining “manual prompt assembly” bypassing ContextBuilder.

3.2. Reflections in context
 build_context(...):

queries memory_type in ("reflection", "strategy") for given tenant/project/session,

respects reflection token limit & importance threshold,

adds section clearly labeled e.g. ## Lessons Learned (Reflective Memory).

 If reflective memory is disabled:

section is either absent or clearly marked as disabled (helps debugging).

3.3. Actor–Evaluator–Reflector flow
 There is a small, clear module defining:

python
Skopiuj kod
class EvaluationResult(BaseModel):
    outcome: OutcomeType  # success / failure / partial
    error_info: Optional[ErrorInfo]
    notes: Optional[str]
    importance_hint: Optional[float]
and a protocol like:

python
Skopiuj kod
class Evaluator(Protocol):
    def evaluate(self, execution_context: ExecutionContext) -> EvaluationResult:
        ...
 Reflector consumes EvaluationResult and:

optionally boosts/lowers importance of involved memories,

optionally creates reflections/strategies.

 End-to-end test exists:

Scenario:

Task execution fails (simulated or real).

Evaluator produces EvaluationResult with failure and error info.

Reflector creates reflection/strategy.

Next agent call to similar task:

builds context via ContextBuilder,

includes the new reflection in Lessons Learned,

test asserts presence of reflection text in final prompt.

4. Feature flags & modes – Lite vs Full
Objective: Configuration flags really change behavior, not only docs.

4.1. Flags inventory & usage
 All flags related to reflective memory & workers are listed and explained in one place (e.g. docs/CONFIG_REFLECTIVE_MEMORY.md):

REFLECTIVE_MEMORY_ENABLED

REFLECTIVE_MEMORY_MODE (lite/full)

DREAMING_ENABLED

SUMMARIZATION_ENABLED

REFLECTIONS_MAX_TOKENS

thresholds for importance/decay/etc.

 For each flag, there is at least one reference in code where it is actually used.

4.2. Behavior matrix
 The following table (or equivalent) is accurate against real code:

Setting	Expected behavior
REFLECTIVE_MEMORY_ENABLED=0	No new reflections created, no Lessons Learned in context
REFLECTIVE_MEMORY_MODE=lite	Summarization allowed, dreaming disabled by default
REFLECTIVE_MEMORY_MODE=full	Summarization + dreaming active
DREAMING_ENABLED=0	Dreaming disabled, regardless of mode
SUMMARIZATION_ENABLED=0	No episodic summaries created

 There is at least one test for lite and full modes:

lite: dreaming worker exits early (no new reflections), summarization works,

full: both summarization and dreaming can produce new memories.

5. Security, tenancy & “almost enterprise” honesty
Objective: Reflective memory is reasonably safe for multi-tenant PoC and honestly described as “almost enterprise”.

5.1. Tenant isolation
 All memory-related endpoints:

store / search / reflect / governance

 …perform explicit tenant checks:

tenant ID is always required,

queries are scoped by tenant,

no cross-tenant reads/writes are possible.

5.2. Auth & governance
 There is a minimal auth layer for production:

JWT / API keys / gateway – documented in one place.

 Governance endpoints (costs, budgets, audit) are:

protected by at least “admin” role,

not reachable without auth even if someone turns on DEBUG.

5.3. Documentation honesty
 README.md and Project maturity – why "almost enterprise" sections:

list clearly what is done (RLS, tenant scoping, basic auth),

list clearly what is NOT done yet (e.g. no formal pen-tests, no TLS termination inside RAE, no external secrets manager),

avoid marketing language suggesting full enterprise certification.

6. SDK & DX (minimum bar for external teams)
Objective: It’s realistically possible for an external team to adopt RAE Lite + reflective memory.

 Python SDK has at least:

version ≥ 0.3.0,

documented methods for:

storing memories (with layer & type),

querying with reflective context,

working with sessions,

examples for:

personal assistant,

team knowledge base,

incident/post-mortem memory.

 There is a minimal, end-to-end Quickstart for RAE Lite + reflective memory:

spin up docker compose for Lite,

run single Python script that:

stores a few events,

runs a failure → reflection → next attempt story,

prints out prompt with Lessons Learned.

7. Final “DONE” checklist
Reflective Memory v1 and RAE Lite are considered closed when:

 Section 1 (engine & scoring) is DONE.

 Section 2 (decay / summarization / dreaming) is DONE.

 Section 3 (ContextBuilder & Actor–Evaluator–Reflector) is DONE.

 Section 4 (flags & modes) is DONE.

 Section 5 (security & tenancy) is DONE.

 Section 6 (SDK & DX) is DONE.

 STATUS.md and REFLECTIVE_MEMORY_V1.md have been updated to match reality.

 A short internal note was written (e.g. RAE-ReflectiveMemory_v1-closure-report.md) summarizing:

what changed,

what is still explicitly out of scope for v1,

what is planned for v1.1+.

When all of the above are ticked, możesz spokojnie mówić:

„Reflective Memory v1 is not a plan, it’s a finished module.
RAE Lite z pamięcią rozumną jest gotowe do sensownych PoC w dużych firmach –
z uczciwym dopiskiem almost enterprise tam, gdzie trzeba.”