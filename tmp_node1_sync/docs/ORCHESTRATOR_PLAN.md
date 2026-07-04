# 🎼 Multi-Agent Orchestrator - Implementation Plan

**Date**: 2025-12-10
**Status**: 📋 PLANNING PHASE
**Goal**: Build intelligent orchestrator managing Claude + Gemini CLI for high-quality autonomous development

---

## 🎯 Vision

**Problem**: Ręczne klikanie "Enter" w CLI, brak cross-review, ryzyko obniżenia jakości

**Solution**: Mądry orkiestrator który:
- ✅ Przydziela zadania wg trudności (tani model do prostych, Opus/Pro do trudnych)
- ✅ Wymusza cross-review (jeden pisze plan → drugi sprawdza, jeden koduje → drugi recenzuje)
- ✅ Gwarantuje jakość (ZERO-WARNINGS, testy, brak regresji)
- ✅ Działa **100% autonomicznie** dla obu modeli (Claude + Gemini CLI)

**Your Role**: Architect - wymyślasz cele, orkiestrator + agenci robią resztę

---

## 📐 Architecture Overview

```
                    ┌─────────────────────────────────┐
                    │    YOU (Human Architect)        │
                    │  - Defines goals & priorities   │
                    │  - Reviews final results        │
                    │  - Resolves conflicts (rare)    │
                    └──────────────┬──────────────────┘
                                   │ tasks.yaml
                                   ▼
              ┌─────────────────────────────────────────┐
              │      ORCHESTRATOR (Python)              │
              │  - Loads tasks                          │
              │  - Routes to models (by risk/area)      │
              │  - Enforces quality gates               │
              │  - Manages state machine                │
              │  - Logs everything                      │
              └─────┬────────────────────────┬──────────┘
                    │                        │
         ┌──────────▼─────────┐   ┌─────────▼──────────┐
         │  Gemini CLI        │   │  Claude CLI/API    │
         │  (non-interactive) │   │  (API key)         │
         │  ~/.gemini auth    │   │  ANTHROPIC_API_KEY │
         └─────┬──────────────┘   └──────────┬─────────┘
               │                             │
               │  4 ROLES (each can be either model):
               │
               ├─► Planner-Agent (high-risk → Sonnet/Pro)
               ├─► Plan-Reviewer-Agent (different model!)
               ├─► Implementer-Agent (by difficulty)
               └─► Code-Reviewer-Agent (different than implementer!)
                           │
                           ▼
              ┌─────────────────────────────┐
              │    QUALITY GATE             │
              │  - pytest (all tests)       │
              │  - mypy/ruff (ZERO-WARNINGS)│
              │  - coverage (no regression) │
              │  - git hooks validation     │
              └─────────────────────────────┘
```

---

## 🧩 Components Breakdown

### 1. Task Definition (`tasks.yaml`)

**You write** high-level goals:

```yaml
tasks:
  - id: RAE-001
    goal: "Complete Phase 2 of RAE-core: implement search strategies and hybrid engine"
    risk: high              # high/medium/low
    area: core              # core/math/api/docs/tests
    repo: RAE-agentic-memory
    context_files:
      - rae-core/rae_core/search/
      - docs/RAE_PHASE2_PLAN.md
    constraints:
      - ZERO-WARNINGS
      - 80%+ test coverage
      - No breaking changes to public API

  - id: RAE-002
    goal: "Update README with Phase 1 completion status"
    risk: low
    area: docs
    repo: RAE-agentic-memory
    context_files:
      - README.md
      - docs/RAE_PHASE1_COMPLETION_PLAN.md
```

**Orchestrator processes** these into actionable steps.

---

### 2. Agent Roles & Model Routing

#### 2.1 Planner-Agent

**Responsibility**: Create step-by-step plan from task goal

**Input**:
- Task from `tasks.yaml`
- Current repo state (git status, structure)
- Relevant policies (AUTONOMOUS_OPERATIONS.md, TESTING_OPTIMIZATION.md, etc.)

**Output**:
```json
{
  "task_id": "RAE-001",
  "plan_version": 1,
  "steps": [
    {
      "id": "S1",
      "type": "analysis",
      "description": "Read existing search/ structure, identify gaps vs Phase 2 plan",
      "risk": "medium",
      "estimated_complexity": "medium",
      "files_to_read": ["rae-core/rae_core/search/*", "docs/RAE_PHASE2_PLAN.md"]
    },
    {
      "id": "S2",
      "type": "implementation",
      "description": "Implement HybridSearchEngine class with semantic + working memory fusion",
      "risk": "high",
      "estimated_complexity": "large",
      "files_to_create": ["rae-core/rae_core/search/hybrid.py"],
      "tests_required": true
    },
    {
      "id": "S3",
      "type": "testing",
      "description": "Write comprehensive tests for HybridSearchEngine",
      "risk": "medium",
      "estimated_complexity": "medium",
      "files_to_create": ["rae-core/tests/unit/search/test_hybrid.py"],
      "coverage_target": "90%"
    },
    {
      "id": "S4",
      "type": "validation",
      "description": "Run full test suite, verify ZERO-WARNINGS, check coverage",
      "risk": "low",
      "commands": ["pytest rae-core/tests/", "mypy rae-core/", "ruff check rae-core/"]
    }
  ],
  "estimated_duration": "4-6 hours",
  "dependencies": [],
  "rollback_strategy": "All changes in feature/rae-phase2-search branch"
}
```

**Model Selection**:
- `risk: high` OR `area: core|math` → **Claude Sonnet / Gemini Pro**
- `risk: medium` → **Gemini Pro / Claude Sonnet**
- `risk: low` → **Gemini Flash**

---

#### 2.2 Plan-Reviewer-Agent

**Responsibility**: Cross-check plan quality

**CRITICAL**: Must be **different model** than Planner to avoid blind spots!

**Input**:
- Plan JSON from Planner-Agent
- Original task
- Project constraints

**Output**:
```json
{
  "plan_id": "RAE-001-v1",
  "status": "approved" | "rejected" | "needs_revision",
  "review": {
    "completeness": 9,
    "feasibility": 8,
    "risk_assessment": 9,
    "missing_steps": [
      "Add step for updating __init__.py exports after creating hybrid.py"
    ],
    "concerns": [
      "Step S2 might be too large - consider splitting implementation into sub-steps"
    ],
    "suggestions": [
      "Add explicit validation step for backward compatibility with existing search API"
    ]
  },
  "revised_plan": { ... } // if needs_revision
}
```

**Model Selection**:
```python
# RULE: Different than Planner
if planner_used == "claude_sonnet":
    return "gemini_pro"
elif planner_used == "gemini_pro":
    return "claude_sonnet"
```

---

#### 2.3 Implementer-Agent

**Responsibility**: Write code for approved plan steps

**Input**:
- Single step from approved plan
- Context files
- Project style guide & conventions

**Output**:
- Code changes (diff/patch/full file)
- Explanation of changes
- Self-assessment of confidence

**Model Selection**:
```python
def choose_implementer(step):
    if step["risk"] == "high" or step["estimated_complexity"] == "large":
        return "claude_sonnet"  # Best reasoning for complex code

    if step["type"] in ["docs", "comments", "simple_refactor"]:
        return "gemini_flash"  # Fast & cheap for simple tasks

    if step["area"] == "tests" and step["risk"] == "low":
        return "gemini_flash"  # Good at writing tests

    return "gemini_pro"  # Default for medium complexity
```

---

#### 2.4 Code-Reviewer-Agent

**Responsibility**: Review generated code before committing

**CRITICAL**: Must be **different model** than Implementer!

**Input**:
- Diff/patch from Implementer
- Original step description
- Coding standards

**Output**:
```json
{
  "step_id": "S2",
  "status": "approved" | "rejected" | "needs_changes",
  "review": {
    "correctness": 8,
    "code_quality": 9,
    "test_coverage": "needs_improvement",
    "performance_concerns": [],
    "security_issues": [],
    "required_changes": [
      "Add docstring to HybridSearchEngine class",
      "Add type hints to _fuse_results method"
    ],
    "optional_improvements": [
      "Consider adding @lru_cache for repeated similarity calculations"
    ]
  }
}
```

**Model Selection**:
```python
# RULE: Different than Implementer
if implementer_used == "claude_sonnet":
    return "gemini_pro"  # Strong reviewer
elif implementer_used == "gemini_flash":
    return "claude_sonnet"  # High-quality review for cheap code
else:
    return "gemini_flash"  # Fast review for Pro-written code
```

---

### 3. Quality Gate (Automated Validation)

**Non-negotiable checks** after code review approval:

```python
class QualityGate:
    """Enforces quality standards - NO EXCEPTIONS"""

    def validate(self, changes: CodeChanges) -> ValidationResult:
        checks = [
            self.run_all_tests(),           # pytest, phpunit, ng test, etc.
            self.check_zero_warnings(),     # mypy, ruff, eslint, phpstan
            self.check_coverage(),          # Must not decrease
            self.check_git_hooks(),         # Pre-commit hooks pass
            self.check_breaking_changes(),  # API contract preserved
        ]

        return ValidationResult(
            passed=all(c.success for c in checks),
            checks=checks,
            can_merge=all(c.success for c in checks)
        )
```

**Rules**:
- ❌ **ANY test fails** → BLOCK merge, send logs back to Implementer
- ❌ **ANY new warnings** → BLOCK merge (ZERO-WARNINGS policy)
- ❌ **Coverage decreases** → BLOCK merge
- ❌ **Git hooks fail** → BLOCK merge (pre-commit, commitlint, etc.)
- ✅ **All green** → Can merge to feature branch

**Auto-fix attempts**:
- Max 3 retry attempts with feedback
- If still failing → mark task as `AWAITING_HUMAN_REVIEW`

---

### 4. State Machine

```
NEW
  ├─► (Planner-Agent) ──► PLANNING
  │                          │
  │                          ▼
  │                    (Plan-Reviewer-Agent)
  │                          │
  │                ┌─────────┴─────────┐
  │                │                   │
  │           APPROVED            REJECTED
  │                │                   │
  │                ▼                   ▼
  │            PLANNED      AWAITING_HUMAN_REVIEW
  │                │
  │                ▼
  │         (For each step):
  │                │
  │                ├─► (Implementer-Agent) ──► IMPLEMENTING
  │                │                               │
  │                │                               ▼
  │                │                   (Code-Reviewer-Agent)
  │                │                               │
  │                │                    ┌──────────┴──────────┐
  │                │                    │                     │
  │                │               APPROVED              REJECTED
  │                │                    │                     │
  │                │                    ▼                     │
  │                │            (Quality Gate)                │
  │                │                    │                     │
  │                │         ┌──────────┴──────────┐         │
  │                │         │                     │         │
  │                │      PASSED                FAILED       │
  │                │         │                     │         │
  │                │         ▼                     ▼         │
  │                │   STEP_COMPLETE      (retry or await human)
  │                │         │
  │                └─────────┤
  │                          │
  │                (All steps complete?)
  │                          │
  │                ┌─────────┴─────────┐
  │                │                   │
  │               YES                  NO
  │                │                   │
  │                ▼                   │
  │              DONE                  │
  │                                    │
  └────────────────────────────────────┘
```

**State Persistence**: `orchestrator/state/{task_id}.json`

---

## 🔧 Implementation Structure

### Files to Create

```
orchestrator/
├── __init__.py
├── main.py                    # Entry point, CLI
├── config.py                  # Load policies & settings
├── task_loader.py             # Parse tasks.yaml
├── state_machine.py           # Task state management
├── model_router.py            # Choose model for each role
├── quality_gate.py            # Run tests, lint, coverage
├── agents/
│   ├── __init__.py
│   ├── base.py               # Base agent class
│   ├── gemini_adapter.py     # Call gemini CLI
│   ├── claude_adapter.py     # Call claude API
│   ├── planner.py            # Planner-Agent logic
│   ├── plan_reviewer.py      # Plan-Reviewer-Agent logic
│   ├── implementer.py        # Implementer-Agent logic
│   └── code_reviewer.py      # Code-Reviewer-Agent logic
├── prompts/
│   ├── planner_prompt.j2     # Jinja2 template for planning
│   ├── plan_review_prompt.j2
│   ├── implementer_prompt.j2
│   └── code_review_prompt.j2
└── state/                    # Task state files (gitignored)

docs/
├── ORCHESTRATOR_SPEC.md       # This plan (full spec)
├── AGENT_ROLES.md             # Detailed role descriptions
├── MODEL_ROUTING.md           # Routing rules & rationale
├── QUALITY_POLICY.md          # Quality gate rules
└── ORCHESTRATOR_RUNBOOK.md    # How to use

.orchestrator/                 # Project-specific config
├── tasks.yaml                # Your task queue
├── model_config.yaml         # Model preferences
└── quality_rules.yaml        # Project-specific quality rules
```

---

## 🔐 Autonomy & Permissions

### Gemini CLI Setup

**One-time**:
```bash
# Login via browser (you do this once)
gemini auth login

# Verify
gemini -p "test" --output-format json
```

**Orchestrator calls**:
```python
import subprocess
import json

def call_gemini(prompt: str, model: str = "gemini-2.5-flash") -> dict:
    """Call Gemini CLI non-interactively"""
    proc = subprocess.run(
        ["gemini", "-p", prompt, "-m", model, "--output-format", "json"],
        capture_output=True,
        text=True,
        check=True,
        timeout=300
    )
    return json.loads(proc.stdout)
```

**Autonomy**: Same as Claude - no prompts!
- Add to `.orchestrator/gemini_permissions.yaml` (if gemini supports it)
- OR gemini CLI runs with `--non-interactive` flag (no confirmations)

---

### Claude API/CLI

**Setup**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# OR use claude CLI with stored credentials
```

**Orchestrator calls**:
```python
from anthropic import Anthropic

def call_claude(prompt: str, model: str = "claude-3-5-sonnet-20241022") -> str:
    """Call Claude API"""
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

**Autonomy**: Already configured in `.claude/settings.local.json`

---

### File Operations Autonomy

**Already configured** (from Fix #2):
- `Write(//home/grzegorz/cloud/Dockerized/RAE-agentic-memory/**)`
- `Edit(//home/grzegorz/cloud/Dockerized/RAE-agentic-memory/**)`
- `Read(//home/grzegorz/cloud/Dockerized/**)`

Orchestrator inherits these permissions → **100% autonomous file ops**

---

## 📋 Model Routing Matrix

| Role | Risk Level | Area | Model Choice | Rationale |
|------|-----------|------|--------------|-----------|
| **Planner** | High | core, math | Claude Sonnet | Best reasoning |
| **Planner** | High | api, services | Gemini Pro | Good architecture |
| **Planner** | Medium | tests, docs | Gemini Pro | Fast planning |
| **Planner** | Low | docs, comments | Gemini Flash | Cheap & good enough |
| **Plan-Reviewer** | Any | Any | **Different than Planner** | Cross-check |
| **Implementer** | High | core, math | Claude Sonnet | Complex logic |
| **Implementer** | Medium | api, services | Gemini Pro | Solid coding |
| **Implementer** | Low | tests, docs | Gemini Flash | Fast & cheap |
| **Code-Reviewer** | Any | Any | **Different than Implementer** | Cross-check |

**Cost Optimization**:
- Gemini Flash: $0.00001875/1K tokens (cheapest)
- Gemini Pro: $0.00025/1K tokens
- Claude Sonnet: $0.003/1K tokens (most expensive but best quality)

**Strategy**: Use Sonnet for critical code, Flash for simple tasks, Pro as middle ground.

---

## 🎯 Quality Policy Integration

### Existing Policies (Already Enforced)

From `AUTONOMOUS_OPERATIONS.md`, `TESTING_OPTIMIZATION.md`, etc:

```yaml
quality_rules:
  # From TESTING_OPTIMIZATION.md
  test_classification:
    TRIVIAL: "skip tests, only lint (~10s)"
    SMALL: "quick tests (~1-2 min)"
    MEDIUM: "full tests 1 Python (~5 min)"
    LARGE: "everything (~15 min)"

  # From current policies
  zero_warnings: true
  all_tests_pass: true
  no_coverage_regression: true

  # Pre-commit hooks (already configured)
  hooks:
    - lint
    - format_check
    - security_scan
    - test_unit (on develop)

  # Branch strategy (from BRANCH_STRATEGY.md)
  workflow:
    - feature/* → develop (local merge after tests)
    - develop → release/* (1 approval)
    - release/* → main (2 approvals + full validation)
```

**Orchestrator respects these** automatically via Quality Gate.

---

### New Quality Rules (Orchestrator-Specific)

```yaml
orchestrator_quality:
  # Cross-review requirements
  min_reviews:
    plan: 1  # Plan-Reviewer must approve
    code: 1  # Code-Reviewer must approve

  # Model diversity
  enforce_different_models:
    plan_review: true   # Reviewer != Planner
    code_review: true   # Reviewer != Implementer

  # Auto-fix limits
  max_retry_attempts: 3
  escalate_to_human_after: 3  # failures

  # Merge criteria
  merge_requires:
    - all_tests_pass
    - zero_warnings
    - code_review_approved
    - coverage_maintained
    - git_hooks_pass
```

---

## 🚀 Implementation Phases

### Phase 1: Minimal Viable Orchestrator (MVP)
**Timeline**: 1-2 days
**Goal**: Prove concept works

**Deliverables**:
- ✅ `orchestrator/main.py` - reads `tasks.yaml`, runs single task
- ✅ `orchestrator/agents/gemini_adapter.py` - call Gemini CLI
- ✅ `orchestrator/agents/claude_adapter.py` - call Claude API
- ✅ `orchestrator/model_router.py` - simple routing logic
- ✅ `orchestrator/quality_gate.py` - run pytest + mypy + ruff
- ✅ `docs/ORCHESTRATOR_SPEC.md` - this document
- ✅ `.orchestrator/tasks.yaml` - example tasks

**Test**:
```yaml
# Simple test task
- id: TEST-001
  goal: "Add docstring to rae_core/context/builder.py"
  risk: low
  area: docs
```

Run: `python orchestrator/main.py --task TEST-001`

**Expected**:
1. Planner (Gemini Flash) creates plan
2. Plan-Reviewer (Claude Sonnet) approves
3. Implementer (Gemini Flash) adds docstring
4. Code-Reviewer (Claude Sonnet) approves
5. Quality Gate runs (tests pass, no warnings)
6. Changes committed to feature branch

**Success Criteria**:
- ✅ Task completes end-to-end autonomously
- ✅ Both models used (Gemini + Claude)
- ✅ Quality gate enforced
- ✅ No manual intervention needed

---

### Phase 2: Multi-Task + Better Logging
**Timeline**: 2-3 days
**Goal**: Production-ready for RAE project

**Deliverables**:
- ✅ State persistence (`orchestrator/state/{task_id}.json`)
- ✅ Multi-task queue processing
- ✅ Better error handling & retry logic
- ✅ Structured logging (`ORCHESTRATOR_RUN_LOG.md`)
- ✅ Human review UI (simple CLI for `AWAITING_HUMAN_REVIEW` tasks)

**Test**:
```yaml
# Real RAE tasks
- id: RAE-PHASE2-001
  goal: "Implement search strategies module"
  risk: high
  area: core

- id: RAE-PHASE2-002
  goal: "Add tests for search strategies"
  risk: medium
  area: tests

- id: RAE-DOCS-001
  goal: "Update README with Phase 1 completion"
  risk: low
  area: docs
```

Run: `python orchestrator/main.py --batch`

**Success Criteria**:
- ✅ All 3 tasks complete autonomously
- ✅ Models routed correctly (Sonnet for high-risk, Flash for docs)
- ✅ Cross-reviews work (different models)
- ✅ Quality maintained (all tests pass, ZERO-WARNINGS)
- ✅ Logs show clear audit trail

---

### Phase 3: RAE Integration + Intelligence
**Timeline**: 3-5 days
**Goal**: Learn from history, optimize routing

**Deliverables**:
- ✅ Store task history in RAE memory
- ✅ Track model performance (success rate, time, cost)
- ✅ Dynamic routing based on historical data
- ✅ Automatic task generation from analysis
- ✅ Integration with GitHub Actions (run on PR)

**Features**:
```python
# Intelligent routing based on history
def choose_model_intelligent(step, history):
    # Which model succeeded most for this type of task?
    best_model = history.get_best_performer(
        area=step["area"],
        risk=step["risk"],
        type=step["type"]
    )

    # Fallback to rules if no history
    if best_model and best_model.success_rate > 0.8:
        return best_model.name
    else:
        return choose_model_by_rules(step)
```

**Test**:
- Run 20+ tasks through orchestrator
- Check if routing improves over time
- Verify cost optimization (use cheaper models when proven effective)

---

### Phase 4: Multi-Project + Advanced Features
**Timeline**: Future
**Goal**: Scale beyond RAE

**Deliverables**:
- ✅ Support multiple repos (RAE, Feniks, others)
- ✅ Task prioritization & scheduling
- ✅ Parallel task execution (multiple tasks at once)
- ✅ Advanced conflict resolution
- ✅ Integration with Linear/Jira/GitHub Issues

---

## 💰 Cost Estimation

**Assumptions**:
- Average task: 5 steps
- Each step: ~2000 tokens input, ~1000 tokens output

**Per Task Cost**:

| Step | Model | Input | Output | Cost |
|------|-------|-------|--------|------|
| Planning | Gemini Pro | 2K | 1K | $0.00075 |
| Plan Review | Claude Sonnet | 2K | 0.5K | $0.0105 |
| Implement (x3) | Gemini Flash | 2K x 3 | 1K x 3 | $0.000169 |
| Code Review (x3) | Claude Sonnet | 2K x 3 | 0.5K x 3 | $0.0315 |
| **TOTAL** | | | | **~$0.043/task** |

**Monthly (100 tasks)**: ~$4.30

**Compare to**:
- Claude-only (all Sonnet): ~$0.15/task → $15/month
- **Savings**: ~70% cheaper!

---

## 📊 Success Metrics

### Phase 1 (MVP)

- ✅ End-to-end task completion (1 task)
- ✅ 100% autonomous (no prompts)
- ✅ Quality gate enforced
- ✅ Both models used correctly

### Phase 2 (Production)

- ✅ 10+ tasks completed autonomously
- ✅ 0 quality regressions
- ✅ <5% tasks need human review
- ✅ 50%+ cost savings vs Claude-only

### Phase 3 (Intelligent)

- ✅ Model performance tracking working
- ✅ Routing improves based on history
- ✅ Task completion time decreases 20%+
- ✅ RAE memory integration complete

---

## 🎓 Example Task Flow

### Task: "Implement Phase 2 Search Strategies"

**1. You Define Task** (`tasks.yaml`):
```yaml
- id: RAE-PHASE2-SEARCH
  goal: "Implement search strategies: semantic, working memory, hybrid"
  risk: high
  area: core
  context_files:
    - docs/RAE_PHASE2_PLAN.md
    - rae-core/rae_core/search/
  constraints:
    - ZERO-WARNINGS
    - 85%+ test coverage
    - No breaking changes
```

**2. Orchestrator Starts**:
```bash
$ python orchestrator/main.py --task RAE-PHASE2-SEARCH
```

**3. Planning** (Claude Sonnet - high risk):
```
[PLANNER] Reading context...
[PLANNER] Analyzing Phase 2 requirements...
[PLANNER] Creating 12-step plan:
  S1: Analyze existing search/ structure
  S2: Design SearchStrategy interface
  S3: Implement SemanticSearchStrategy
  S4: Implement WorkingMemorySearchStrategy
  S5: Implement HybridSearchEngine
  S6: Write unit tests for SemanticSearchStrategy
  S7: Write unit tests for WorkingMemorySearchStrategy
  S8: Write unit tests for HybridSearchEngine
  S9: Integration tests
  S10: Update __init__.py exports
  S11: Update documentation
  S12: Full validation (tests + lint + coverage)
```

**4. Plan Review** (Gemini Pro - different model):
```
[PLAN-REVIEWER] Reviewing 12-step plan...
[PLAN-REVIEWER] ✅ Completeness: 9/10
[PLAN-REVIEWER] ✅ Feasibility: 8/10
[PLAN-REVIEWER] ⚠️  Suggestions:
  - Add step for backward compatibility check
  - Split S5 into 2 sub-steps (too large)
[PLAN-REVIEWER] STATUS: APPROVED with minor revisions
```

**5. Implementation** (Steps 1-12):

```
[STEP S1] Implementer: Claude Sonnet (high risk)
[STEP S1] ✅ Analysis complete
[STEP S1] Code-Reviewer: Gemini Pro
[STEP S1] ✅ Review passed

[STEP S2] Implementer: Claude Sonnet (high risk)
[STEP S2] ✅ Created SearchStrategy interface
[STEP S2] Code-Reviewer: Gemini Pro
[STEP S2] ✅ Review passed

[STEP S3] Implementer: Claude Sonnet (high risk)
[STEP S3] ✅ Created SemanticSearchStrategy
[STEP S3] Code-Reviewer: Gemini Pro
[STEP S3] ⚠️  Review: Add docstrings
[STEP S3] Implementer: Claude Sonnet (retry)
[STEP S3] ✅ Docstrings added
[STEP S3] Code-Reviewer: Gemini Pro
[STEP S3] ✅ Review passed

... (steps 4-11 similar) ...

[STEP S12] Running Quality Gate...
[STEP S12] ✅ pytest: 164 tests passed
[STEP S12] ✅ mypy: No errors
[STEP S12] ✅ ruff: No warnings
[STEP S12] ✅ coverage: 87% (target: 85%+)
[STEP S12] ✅ QUALITY GATE PASSED
```

**6. Completion**:
```
[ORCHESTRATOR] Task RAE-PHASE2-SEARCH completed
[ORCHESTRATOR] Branch: feature/rae-phase2-search
[ORCHESTRATOR] Commits: 12
[ORCHESTRATOR] Tests: 164 passed, 0 failed
[ORCHESTRATOR] Coverage: 87% (↑2%)
[ORCHESTRATOR] Warnings: 0 (ZERO-WARNINGS maintained)
[ORCHESTRATOR] Cost: $0.38 (5 Sonnet calls, 7 Pro/Flash calls)
[ORCHESTRATOR] Time: 1h 23min

Ready to merge to develop!
```

**7. You Review Final Result**:
```bash
$ git diff develop feature/rae-phase2-search
$ git log feature/rae-phase2-search --oneline
$ pytest rae-core/tests/  # Verify yourself

# If satisfied:
$ git checkout develop
$ git merge feature/rae-phase2-search --no-ff
$ git push origin develop
```

---

## 🔒 Safety & Rollback

### Safety Mechanisms

1. **All work in feature branches** (never directly on develop/main)
2. **Git hooks still run** (pre-commit, commitlint)
3. **Quality gate is hard stop** (no merge without green tests)
4. **Human review option** (tasks can escalate to `AWAITING_HUMAN_REVIEW`)
5. **Rollback easy**: `git branch -D feature/task-name`

### Escalation Triggers

Task goes to `AWAITING_HUMAN_REVIEW` when:
- ❌ Quality gate fails 3+ times
- ❌ Plan-Reviewer rejects plan
- ❌ Code-Reviewer rejects code 3+ times
- ❌ Breaking API changes detected
- ❌ Timeout (task runs >6 hours)

**You review**: `python orchestrator/main.py --review`

Shows tasks needing human decision:
```
AWAITING HUMAN REVIEW:
- RAE-PHASE2-SEARCH (S5): Code review rejected 3x
  Issue: HybridSearchEngine.fuse() logic unclear
  Options:
    1. Approve current implementation
    2. Provide feedback and retry
    3. Skip this step
    4. Abort task
```

---

## 🎯 Next Steps (After This Plan)

### Immediate (This Session End)

1. ✅ Review this plan
2. ✅ Ask questions / request changes
3. ✅ **STOP** - no implementation yet!

### Next Session (Implementation Start)

**Phase 1 - MVP** (1-2 days):

1. Create directory structure
2. Implement adapters (Gemini CLI + Claude API)
3. Implement simple Planner-Agent
4. Implement simple Quality Gate
5. Test with 1 simple task (add docstring)

**Phase 2 - Production** (2-3 days):

6. Add all 4 agent roles
7. Implement state machine
8. Add cross-review logic
9. Test with real RAE Phase 2 tasks
10. Integrate with existing CI/CD

**Phase 3 - Intelligence** (future):

11. RAE memory integration
12. Historical performance tracking
13. Dynamic routing optimization

---

## 📖 Documentation Structure

```
docs/
├── ORCHESTRATOR_PLAN.md          ← This file (master plan)
├── ORCHESTRATOR_SPEC.md          ← Detailed technical spec
├── AGENT_ROLES.md                ← Role descriptions & prompts
├── MODEL_ROUTING.md              ← Routing logic & rationale
├── QUALITY_POLICY.md             ← Quality gate rules
├── ORCHESTRATOR_RUNBOOK.md       ← How to use (user guide)
└── ORCHESTRATOR_DEVELOPMENT.md   ← Developer guide
```

---

## ✅ Decision Points (Answer Before Implementing)

### 1. Model Access

- ✅ **Gemini**: CLI via `~/.gemini/settings.json` (already works)
- ✅ **Claude**: API via `ANTHROPIC_API_KEY` (already configured)

### 2. State Storage

**Options**:
- A) JSON files in `orchestrator/state/` (MVP - simple)
- B) SQLite database (Phase 2 - structured queries)
- C) RAE memory (Phase 3 - full integration)

**Decision**: Start with A, migrate to C

### 3. Task Source

**Options**:
- A) YAML file (`.orchestrator/tasks.yaml`) - manual
- B) Auto-generate from issues/PRs - automated
- C) RAE analysis generates tasks - AI-driven

**Decision**: Start with A, add B in Phase 2, C in Phase 3

### 4. Cost Limits

**Should orchestrator**:
- Track spending per task?
- Have daily/monthly budget limits?
- Alert when expensive operations planned?

**Recommendation**: Yes to all - add in Phase 2

---

## 📊 Telemetry - Observability First

**CRITICAL**: Orkiestrator jako kluczowy element musi mieć pełną telemetrię od początku!

### 3-Layer Telemetry Strategy

**1. Traces (Przepływ wykonania)**

Każde uruchomienie orkiestratora tworzy strukturę spanów:

```
orchestrator.run (główna sesja)
  ├─ task.run (RAE-001)
  │   ├─ task.plan
  │   │   └─ llm.call (claude_sonnet, role=planner)
  │   ├─ task.review_plan
  │   │   └─ llm.call (gemini_pro, role=plan_reviewer)
  │   ├─ step.run (S1)
  │   │   ├─ llm.call (gemini_flash, role=implementer)
  │   │   ├─ llm.call (claude_sonnet, role=code_reviewer)
  │   │   └─ quality_gate.run
  │   ├─ step.run (S2)
  │   └─ ...
  └─ task.run (RAE-002)
```

**Atrybuty spanów**:
```python
# Task-level
task.id = "RAE-001"
task.area = "core"
task.risk = "high"
task.complexity = "large"

# Step-level
step.id = "S2"
step.type = "implementation"
step.risk = "high"

# LLM-level
llm.provider = "gemini_cli" | "claude_api" | "local_ollama"
llm.model_name = "gemini-2.0-flash"
llm.role = "planner" | "plan_reviewer" | "implementer" | "code_reviewer"
llm.prompt_tokens = 2048
llm.completion_tokens = 512

# Result
result.status = "success" | "fail" | "retry" | "human_required"
result.attempt = 1
```

**2. Metrics (Metryki ilościowe)**

```python
# Task metrics
orchestrator_tasks_total{status="success|fail|human_required"}
orchestrator_task_duration_seconds (histogram)

# Step metrics
orchestrator_steps_total{type="plan|implement|review|quality_gate", status="..."}

# LLM usage
orchestrator_llm_calls_total{provider="...", model="...", role="..."}
orchestrator_llm_tokens_total{provider="...", model="..."}
orchestrator_llm_cost_usd{provider="...", model="..."}

# Quality Gate
orchestrator_quality_gate_runs_total{status="passed|failed"}
orchestrator_quality_regressions_total{type="tests_failed|warnings_new|coverage_drop"}

# Model routing decisions
orchestrator_model_routing{task_risk="...", task_area="...", model_chosen="..."}
```

**3. Logs (Szczegóły tekstowe)**

Structured logging z kontekstem:

```python
# Routing decisions
LOG: "Task RAE-MATH-001 / step S2 → implementer=gemini_flash (reason: low-risk tests), reviewer=claude_sonnet (cross-check)"

# Quality gate failures
LOG: "Quality gate FAILED: pytest failed (3 tests: test_hybrid_search, test_vector_similarity, test_cache_expiry)"
LOG: "Quality gate FAILED: ruff detected 2 new warnings in rae_core/search/hybrid.py"

# Cross-review conflicts
LOG: "Code-Reviewer (claude_sonnet) REJECTED patch from Implementer (gemini_flash): Missing docstrings, unclear variable names"

# Retry attempts
LOG: "Step S2 retry attempt 2/3: Re-implementing with feedback from reviewer"
```

### Implementation Requirements

**Phase 1 (MVP)**:
- ✅ Initialize OpenTelemetry (OTel) TracerProvider, MeterProvider
- ✅ Export to OTLP (compatible with existing Jaeger/Grafana/Tempo)
- ✅ Basic spans for: orchestrator.run, task.run, llm.call
- ✅ Basic counters: llm_calls_total, quality_gate_runs_total
- ✅ Structured logging with context

**Phase 2 (Production)**:
- ✅ Full span hierarchy with all attributes
- ✅ All metrics defined above
- ✅ Cost tracking per task/step
- ✅ Performance histograms (duration distributions)
- ✅ Integration with existing RAE telemetry

**Phase 3 (Intelligence)**:
- ✅ Historical analysis: "Which model performs best for task_area=math?"
- ✅ Cost optimization: "Can we use cheaper model based on success rate?"
- ✅ Quality trends: "Are we improving coverage over time?"
- ✅ Anomaly detection: "Task took 10x longer than usual"

### Technical Stack

```python
# Requirements
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp
opentelemetry-instrumentation  # auto-instrumentation for libs

# Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=orchestrator
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production
```

### Dashboard Views

**1. Orchestrator Overview**
- Tasks completed today (success/fail/pending)
- Average task duration
- Model usage breakdown (% Claude vs Gemini vs Local)
- Total cost today/week/month

**2. Quality Dashboard**
- Quality gate pass rate (%)
- Top failing tests
- Warning trends (should be zero!)
- Coverage trends

**3. Model Performance**
- Success rate by model and role
- Average retry count by model
- Cost per task by model choice
- Response time distribution

**4. Task Flow Visualization**
- Gantt chart of task execution
- Bottleneck identification
- Parallel execution opportunities

### Success Metrics (with Telemetry)

After 1 month, you should be able to answer:

❓ "Który model najczęściej wymaga poprawek?"
→ Query: `orchestrator_steps_total{status="retry"}` grouped by `llm.model_name`

❓ "Ile kosztuje typowy task high-risk vs low-risk?"
→ Query: `sum(orchestrator_llm_cost_usd) by (task.risk)`

❓ "Czy jakość się poprawia czy tylko mielimy w pętli?"
→ Query: `rate(orchestrator_quality_regressions_total)` over time

❓ "Gdzie są bottlenecki w pipeline?"
→ Trace analysis: which spans take longest?

---

## 🎬 Conclusion

**This Plan Gives You**:
- ✅ Mądry orkiestrator (routing wg trudności)
- ✅ Cross-review (plan + kod sprawdzany przez drugi model)
- ✅ Gwarancja jakości (ZERO-WARNINGS, testy, brak regresji)
- ✅ 100% autonomia (Gemini + Claude bez promptów)
- ✅ 70% oszczędność kosztów (Flash do prostych, Sonnet do trudnych)
- ✅ Twoja rola = architekt (wymyślasz cele, orkiestrator wykonuje)

**Gra jest warta świeczki?**

✅ **TAK** - jeśli:
- Planujesz ciągłą modernizację (RAE + inne projekty)
- Chcesz przestać klikać "Enter"
- Jakość musi być zachowana/podniesiona
- Masz 4-7 dni na MVP + production version

❌ **NIE** - jeśli:
- Jednorazowy projekt
- Ręczne review preferowane
- Nie używasz AI nałogowo

---

**Status**: 🚀 IMPLEMENTATION IN PROGRESS - Telemetry integrated into plan

**Questions?**
- Czy routing modeli jest OK?
- Czy quality gate rules są wystarczające?
- Czy chcesz dodać/zmienić coś w planie?

**Next**: Poczekaj na Twoje "Go" i zacznę implementację Phase 1 (MVP)!
