# AGENT CORE PROTOCOL (v2.1)

> **SINGLE SOURCE OF TRUTH** for all AI Agents (Gemini, Claude, etc.) working on RAE.
> **MANDATORY**: Read this before every session.

## 1. CORE MANDATES

- **Async-First**: **ALWAYS** use asynchronous connections and operations wherever possible to ensure high performance and non-blocking I/O.
- **Autonomy**: Work autonomously. Do NOT ask for permission to create files, add tests, or commit standard work.
- **Security**: **ALWAYS** include `tenant_id` in SQL queries. This is a multi-tenant system.
- **Non-Interactive**: **NEVER** use interactive commands (`nano`, `vim`, `git add -i`, `less`). Use `cat`, `sed`, or tool-specific edits.
- **Templates**: **ALWAYS** start with templates from `.ai-templates/` (Repo, Service, Route, Test). Do NOT write from scratch.
- **Repository Hygiene**: **NEVER** mix code from other projects. Check `git remote -v` and `git status` constantly.

## 2. WORKFLOW & GIT STRATEGY (4-PHASE)

Strictly follow the flow: `feature/*` → `develop` → `release/*` → `main`.

| Phase | Branch | Action | Protection |
| :--- | :--- | :--- | :--- |
| **1. Dev** | `feature/name` | Create from `develop`. Work here. | Low. Fast iteration. |
| **2. Integ** | `develop` | Merge feature here. **RUN FULL TESTS**. | Medium. Must be stable. |
| **3. QA** | `release/vX` | Create from `develop`. Final QA. | High. 1 Approval. |
| **4. Prod** | `main` | Merge `release` via PR. **HOLY**. | **MAX**. 2 Approvals. |

### STRICT MERGE PROTOCOL (Anti-Data-Loss)
To prevent "lost work" or partial merges, execute this EXACT sequence when finishing a feature:

1. **Update**: `git checkout develop && git pull origin develop`
2. **Merge**: `git merge --no-ff feature/name` (Forces a merge commit for visibility)
3. **Verify (The "Zero-Diff" Check)**:
   - Run: `git log feature/name ^develop` -> **MUST BE EMPTY**
   - Run: `git diff develop...feature/name` -> **MUST BE EMPTY**
   - *If output exists, the merge failed. DO NOT PROCEED.*
4. **Test**: `make lint && make test-unit`
5. **Delete**: Only after passing step 3 & 4: `git branch -d feature/name`

**Crucial**:
- **NEVER** push directly to `main` or `release` (except PRs).
- **NEVER** leave `main` or `develop` with red CI.

## 3. TESTING PROTOCOL

Different branches = Different testing levels.

### Phase 1: Feature Branch (`feature/*`)
- **Goal**: Speed & Focus.
- **Command**: `pytest --no-cov path/to/new_test.py`
- **Fast Loop**: Use `make test-fast` to stop on first error, then `make test-fix` to verify only the fixed tests.
- **Rule**: Test **ONLY** your new code. Do NOT run full suite.

### Phase 2: Develop Branch (`develop`)
- **Goal**: Integrity & Regression.
- **Command**: `make lint` and `make test-lite` (or `test-core`)
- **CRITICAL RULE**: **MANDATORY** before **EVERY** push to `develop`. You **MUST** run both commands locally. 
- **ENFORCEMENT**: Never push to `develop` if there are any linting errors or test failures. Fix ALL issues locally first.

### Phase 3: Main/Release
- **Goal**: Production Guarantee.
- **Command**: CI (GitHub Actions).
- **Rule**: If CI fails, fix immediately on `develop` and propagate up.

## 4. Git & Version Control
- **Atomic Commits:** One logical change per commit.
- **Messages:** "Why" over "What". Format: `type(scope): description`.
- **Pre-push:** Run `make lint` and `make test-lite` locally.
- **Branches:** `feature/name`, `fix/name`. Never push to `main` directly.

## 5. Infrastructure & Cluster Strategy ("Cluster First")
- **Mandate:** Always offload heavy tasks (Benchmarks, Training, Bulk Inference) to the Cluster.
- **Node1 (Lumina):** Primary Compute (i7/4080). Use for Logic/Math benchmarks.
- **Node2 (Julia):** Secondary Compute (i9/4080). Use for Training/Validation.
- **Node3 (Piotrek):** Inference Engine (128GB RAM). Use for LLM/Embeddings via Ollama Proxy.
- **Startup:** At session start, run `python scripts/connect_cluster.py` to verify connectivity.
- **Security:** NEVER commit passwords or private keys. Use `config/cluster.yaml` and SSH keys.

## 6. DOCUMENTATION STRATEGY

### 6.1 Synchronization Rule (Zero Drift Strategy)
**Problem**: CI automatically updates `CHANGELOG.md` and metrics files, creating new commits on remote branches. This causes local branches to fall behind (`git pull` conflicts).
**Solution**: **ALWAYS run `make docs` locally before pushing.**
- **Why**: The CI workflow checks `if git diff --quiet`. If you generate and commit the docs locally, the CI sees no changes and **skips creating a new commit**.
- **Result**: Local and Remote branches stay perfectly synchronized (same commit hash). No more "your branch is behind" errors.

- **Auto-Generated (DO NOT EDIT MANUALLY)**: `CHANGELOG.md`, `STATUS.md`, `TODO.md`, `docs/.auto-generated/`.
- **Manual (EDIT THESE)**: `CONVENTIONS.md`, `PROJECT_STRUCTURE.md`, `docs/guides/`, `.ai-templates/`.

## 7. SESSION STARTUP ROUTINE

1. **Read Protocol**: Read this file (`docs/rules/AGENT_CORE_PROTOCOL.md`).
2. **Verify Cluster**: **MANDATORY**. Run `.venv/bin/python3 scripts/connect_cluster.py` to check status of Node1, Node2, and Node3.
3. **Check Context**: Use `search_memory` (if available) for recent agent activity.
4. **Plan**: Create a plan/todo list before editing code.

## 8. HIGH STANDARDS & QUALITY GATES

- **Zero Warning Policy**: Treat warnings as errors. Fix them immediately. Do not ignore them.
  - *Exception*: If a warning originates from a 3rd party library and is beyond the agent's control, document it and suppress it if possible, ensuring it doesn't clutter the CI output.
- **No Drift**: Ensure architectural decisions are persistent. Do not re-introduce fixed bugs or deprecated patterns.
- **Best Practices**:
  - **Clean Code**: Follow SOLID, DRY, and KISS principles.
  - **Type Safety**: strict `mypy` compliance.
  - **Documentation**: Keep docs in sync with code (especially `CONVENTIONS.md`).
- **Definition of Done**:
  - Tests passed (Green).
  - Linter passed (No warnings).
  - Documentation updated.
  - PR ready for review.

## 9. RESOURCE & COMMUNICATION EFFICIENCY

- **RAE-First Communication**: **MANDATORY**. All communication and context exchange between agents MUST pass through RAE. Agents must consult RAE for context before acting and store results in RAE. Direct side-channels are prohibited to ensure full auditability and shared state. Input/Output MUST flow through RAE to minimize token usage.
- **RAE-First Infrastructure**: **MANDATORY**. ALWAYS use the existing Docker infrastructure (`rae-api`, `postgres`, `qdrant`, etc.) for running tests, benchmarks, and scripts. DO NOT install dependencies or run heavy processes on the host machine if they can be executed inside a container. Use `docker compose exec` to run commands in the correct environment.
- **Model Economy**: **MANDATORY**. Save tokens by using cheaper/lighter models (e.g., L1 heuristics, "cheap" profile in `math_controller.yaml`) for simple tasks, boilerplate, and routine checks. Reserve SOTA models (Gemini 1.5 Pro, Claude 3.5 Sonnet) only for complex reasoning, architectural decisions, and final reviews.
- **Compute Offloading**: For heavy tasks (embeddings, large benchmarks), utilize the Compute Cluster:
  - **Node KUBUS**: RTX 4080 (GPU acceleration, Local LLMs). Primary for high-quality code generation and audits.
  - **Node PIOTREK**: 128GB RAM (Large-scale memory testing).
  - **Other Nodes**: Emerging compute resources should be integrated via RAECoreService.

## 10. DISTRIBUTED COMPUTE WORKFLOW (Writer/Reviewer)

When delegating tasks to external nodes (e.g., node1/KUBUS), follow the **Agentic Quality Loop**:
- **Zero-Token Policy (Core)**: Tasks with high token volume (large implementation files) MUST be delegated to Node1 (KUBUS) where code is generated by **DeepSeek** and reviewed by **Ollama** locally, saving external API costs and avoiding rate limits.
- **Workflow Flow**: Gemini CLI (Task Prep) -> Node1 (Code Gen & Review) -> Gemini CLI (Verification & Deployment).
- **Phase 1: Writer**: Typically **DeepSeek** (e.g., `deepseek-coder:33b`) writes the code or performs analysis.
- **Phase 2: Reviewer**: Typically **Ollama** running a secondary model (e.g., `senior-architect` persona) checks the code.
- **Atomic Tasking**: Tasks for Node1 MUST be atomic (max 1-2 files, <50 LOC). Large tasks must be split into iterations.
- **Mandatory Quality Gates for Delegated Code**:
    - **Telemetry**: New code MUST include OpenTelemetry instrumentation (e.g., `LLMTracer`, `RAETracing`).
    - **Tests**: Every code change MUST be accompanied by unit tests (target 80% coverage).
    - **No Regression**: Node1 results MUST be verified against local linting and project contracts.
    - **Agnosticism**: No absolute paths or provider lock-in allowed.
- **RAE-First Context**: Every delegated task MUST include a `context_id` referencing latest memories in RAE to prevent hallucinating APIs.
- **Opportunistic Availability**: External nodes are **NOT** permanent resources. Check status via `ControlPlaneService`.
- **Graceful Fallback**: If a node is unavailable, fallback to local or cloud providers.

## 11. DEPLOYMENT & CI PROTOCOL (DevOps V2 - Zero Drift)

**Mandatory Workflow for Code Changes**:

1. **Pre-Push Sequence (The "Golden Command")**:
   - Run: `make pre-push`
   - **What this does**:
     1. Formats code (Black/Isort/Ruff).
     2. **Generates Documentation & Metrics** (Crucial! Prevents CI from creating "fix" commits that drift history).
     3. Lints strictly.
     4. Runs Unit Tests.
   - **If Failed**: Fix issues and repeat.

2. **Commit Generated Artifacts**:
   - `make pre-push` will likely modify files like `CHANGELOG.md` or `docs/metrics/`.
   - **MANDATORY**: Add these changes to your commit (or create a new one: `chore: update docs`).
   - *Example*: `git add . && git commit --amend --no-edit` (if amending) or `git commit -m "chore: auto-update docs"`.

3. **Push**:
   - `git push origin develop` (or feature branch).
   - Because you already generated the docs, the CI "Auto-Update" job will see 0 changes and skip its commit. **History stays clean.**

4. **Post-Commit Verification**:
   - Run: `gh run list --branch develop --limit 1`
   - **Requirement**: Monitor status until `success`.

5. **Sandbox Strategy**:
   - **Dev**: Port 8000 (`docker-compose.yml` + `dev.yml`). Hot Reload.
   - **Lite Sandbox**: Port 8010 (`docker-compose.test-sandbox.yml`). Integration Tests.
   - **Full Sandbox**: Port 8020 (`docker-compose.sandbox-full.yml`). Full Stack verification.
   - **Rule**: Sandboxes must be startable from scratch (`down -v` -> `up -d`) without manual intervention.

## 12. DEFINITION OF DONE (PRO)
- All tests pass (Green).
- Linter passed (No warnings).
- Benchmarks verified against baseline.
- PR ready for review.
- CI Workflow Green.

## 13. SECURITY & COMPLIANCE PROTOCOL (ISO 42001/27001)

- **Mandatory Compliance Checks**:
  - Every new feature MUST pass `make test-compliance`.
  - Every security-related change MUST pass `make security-check`.
  - Do NOT merge code with High/Medium security vulnerabilities (unless explicitly approved and documented with `# nosec`).

- **Feature Requirements**:
  - **Human Approval**: Any high-risk operation MUST implement `HumanApprovalService`.
  - **Audit Logs**: Critical state changes MUST be logged via `AuditService`.
  - **Data Isolation**: New tables MUST include `tenant_id` and have RLS policies.

- Zero Errors / Zero Drift:
  - Maintain 0 failures in test-compliance.
  - Do not introduce regressions in ISO 42001 coverage (currently 100% for key services).

## 14. ANTI-LOOPING & STABILITY PROTOCOL

### 14.1 Agent (CLI) Self-Correction Rule
- **The "Rule of Three"**: If a specific command or operation fails **3 times** in a row with the same error, the Agent **MUST** stop the loop.
- **Action on Failure**:
    1. Stop the current retry chain.
    2. Read the underlying source code or configuration files related to the error.
    3. Perform a root-cause analysis (RCA).
    4. Propose a code-based fix instead of a configuration-based retry.
- **No Infinite Retries**: Blindly repeating `docker restart` or `curl` commands without changing the state is forbidden.

### 14.2 System (RAE Self-Improvement) Stability Rule
- **Weight Guardrails**: Any automated tuning of mathematical weights (e.g., alpha, beta, gamma) MUST adhere to:
    - **Sum Constraint**: Weights must always sum to **1.0**.
    - **Boundary Limits**: Each weight must be within range `[0.05, 0.85]` to prevent complete loss of a signal (e.g., ignoring recency entirely).
- **Update Frequency**: Automated updates to tenant configuration MUST be throttled (max once per 10 feedback events or a fixed time interval).
- **Oscillation Detection**: If a weight change is reversed by the next tuning cycle (A -> B -> A), the system MUST halt automated tuning for that tenant and request HITL (Human-in-the-loop) review.
- **Baseline Fallback**: Always maintain a "Golden Baseline" configuration. If performance (MRR/HitRate) drops by >15% after tuning, revert to baseline immediately.

