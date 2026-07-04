# RAE – Cold Engineering Review Plan

This document defines a STRICT, ITERATIVE ENGINEERING REVIEW
of the RAE codebase and architecture.

The goal is NOT to refactor immediately.
The goal is to:
- step back
- evaluate correctness and robustness
- identify structural risks
- produce actionable reports

Gemini acts as:
- systems auditor
- code reviewer
- architecture consistency checker

Gemini MUST NOT:
- refactor code
- introduce new features
- redesign architecture
- optimize prematurely

This is an ANALYSIS-FIRST phase.

---

## 0. Review Mode Declaration (MANDATORY)

Before starting, Gemini MUST explicitly state:

"I am running in COLD ENGINEERING REVIEW MODE.
I will analyze, not refactor.
I will produce findings and reports only.
No code will be changed."

---

## 1. Review Philosophy (READ CAREFULLY)

This review is based on the following principles:

1. Architecture before code
2. Contracts before implementations
3. Determinism before cleverness
4. Observability before optimization
5. Explicit failure over implicit success

The system under review:
- is novel
- has no direct reference architecture
- therefore REQUIRES custom evaluation criteria

Standard patterns may be used,
but blind adherence to frameworks is forbidden.

---

## 2. Review Scope (WHAT MUST BE EVALUATED)

Gemini MUST evaluate the following dimensions independently:

1. Architectural agnosticism
2. Asynchronicity and execution model
3. Cold-start capability (clean instance)
4. Database creation and migration mechanisms
5. Data consistency across storage layers
6. Test philosophy and coverage intent
7. Failure modes and recovery paths
8. Internal conceptual coherence (RAE-specific)

Each dimension produces a SEPARATE REPORT.

---

## 3. Iteration Structure (CRITICAL)

The review MUST be performed in ITERATIONS.

Each iteration:
- focuses on ONE dimension only
- ends with a written report
- does NOT influence other iterations

No cross-fixing during iteration.

---

## 4. ITERATION 1 – Architectural Agnosticism

### Goal
Verify that RAE core is truly agnostic with respect to:
- databases
- storage backends
- cache implementations
- execution environment

### Questions to Answer
- Are abstractions real or leaky?
- Is any concrete technology assumed implicitly?
- Are providers interchangeable without semantic drift?
- Are defaults masking coupling?

### Required Output
`REPORT_01_ARCH_AGNOSTICISM.md`

Report MUST include:
- confirmed agnostic components
- suspected hidden coupling
- explicit violations
- risk level (LOW / MEDIUM / HIGH)

---

## 5. ITERATION 2 – Asynchronicity & Execution Model

### Goal
Evaluate whether async behavior is:
- intentional
- consistent
- observable
- safe under load

### Questions to Answer
- Where is async REQUIRED vs incidental?
- Are async boundaries explicit?
- Are blocking calls hidden inside async flows?
- Is task lifecycle clearly defined?

### Required Output
`REPORT_02_ASYNC_EXECUTION.md`

Include:
- async flow map (conceptual, textual)
- potential deadlocks
- starvation risks
- observability gaps

---

## 6. ITERATION 3 – Cold Start & Clean Instance

### Goal
Verify that a completely clean environment can:
- start RAE
- create required structures
- reach a valid initial state

WITHOUT:
- manual steps
- pre-existing databases
- hidden state

### Questions to Answer
- Is bootstrapping deterministic?
- Are assumptions about prior state present?
- Are failures explicit and actionable?

### Required Output
`REPORT_03_COLD_START.md`

Include:
- cold start path description
- mandatory prerequisites
- failure points
- missing automation

---

## 7. ITERATION 4 – Migrations & Schema Management

### Goal
Evaluate database creation, migrations, and evolution.

### Questions to Answer
- Are migrations idempotent?
- Can partial migrations be detected?
- Is schema versioning explicit?
- Is rollback strategy defined?

### Required Output
`REPORT_04_MIGRATIONS.md`

Include:
- migration lifecycle analysis
- schema drift risks
- multi-node execution risks
- recommendations (without implementation)

---

## 8. ITERATION 5 – Data Consistency & Integrity

### Goal
Evaluate consistency across:
- relational storage
- vector storage
- cache layers
- derived state

### Questions to Answer
- What is the source of truth?
- Where eventual consistency is allowed?
- How inconsistencies are detected?
- How corruption would be noticed?

### Required Output
`REPORT_05_DATA_CONSISTENCY.md`

Include:
- consistency model description
- weak points
- missing invariants
- detection mechanisms

---

## 9. ITERATION 6 – Test Philosophy & Coverage INTENT

### Goal
Evaluate tests NOT by quantity, but by INTENT.

This iteration is inspired by:
- DeepMind-style invariant testing
- property-based thinking
- architectural safety checks

### Questions to Answer
- What properties are being protected?
- Which invariants are explicitly tested?
- Which invariants are only assumed?
- Are tests guarding architecture or just behavior?

### Required Output
`REPORT_06_TEST_PHILOSOPHY.md`

Include:
- mapped invariants
- test gaps by concept
- false sense of security risks
- alignment with RAE architecture

---

## 10. ITERATION 7 – Failure Modes & Recovery

### Goal
Evaluate how the system behaves when things go wrong.

### Questions to Answer
- What happens on partial failure?
- Are failures loud or silent?
- Can the system recover without restart?
- Is corruption survivable?

### Required Output
`REPORT_07_FAILURE_RECOVERY.md`

Include:
- failure scenarios
- detection paths
- recovery mechanisms
- catastrophic risks

---

## 11. ITERATION 8 – RAE-Specific Conceptual Coherence

### Goal
Evaluate whether the implementation truly reflects:
- 4-layer memory model
- 3-layer math model
- reflective architecture intent

### Questions to Answer
- Are layers cleanly separated?
- Are responsibilities blurred?
- Does code match declared concepts?
- Is reflection operational or decorative?

### Required Output
`REPORT_08_CONCEPTUAL_COHERENCE.md`

---

## 12. FINAL SYNTHESIS (MANDATORY)

After ALL iterations:

Gemini MUST produce:

`FINAL_RAE_ENGINEERING_ASSESSMENT.md`

This report MUST include:
- summary of systemic risks
- ordering of fixes by impact
- what MUST be fixed before further features
- what is acceptable technical debt
- what is surprisingly solid

NO CODE CHANGES.
NO OPTIMIZATIONS.
NO REFACTOR PROPOSALS YET.

---

## 13. STOP CONDITION

After final synthesis:
- STOP analysis
- WAIT for human decision
- DO NOT propose fixes unless asked

END OF DOCUMENT
