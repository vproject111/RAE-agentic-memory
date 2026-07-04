# RAE Cold-Start & Bootstrap Instability — Investigation Task

## Context

RAE (Reflective Agentic-Memory Engine) works correctly in a local developer environment:
- tests pass
- iterative fixes applied via LLM (Gemini / Claude)
- runtime is stable when services already exist

However, when the same code is pushed to GitHub and cloned by a third party:
- the project cannot be started manually from scratch
- runtime fails or enters an undefined state
- failure is not clearly explained by error messages

Critical notes:
- hard-coded filesystem paths have already been removed
- storage, cache and database layers are implemented via agnostic providers
- this is **not** a request to redesign architecture
- this is a **bootstrap / cold-start reliability problem**

---

## Problem Statement

The system behaves differently under:
1. **Warm runtime conditions** (local dev machine)
2. **Cold-start conditions** (fresh clone, empty environment, no prior state)

The goal of this investigation is to identify **why RAE is not cold-start safe**, despite passing tests and working locally.

---

## Investigation Goals

Identify **all implicit assumptions** that allow RAE to work locally but break in a clean environment.

Specifically determine whether the issue is caused by:
- provider initialization order
- import-time side effects
- hidden environment dependencies
- missing or incomplete default configuration
- premature resource access (DB, cache, vector store)
- test coverage gaps (lack of bootstrap / smoke tests)

---

## Scope (What to Analyze)

### 1. Startup Lifecycle
Determine whether RAE has a **clearly defined startup lifecycle**, or whether:
- providers are instantiated during import
- connections happen before configuration is validated
- runtime state is assumed to exist

### 2. Provider Contracts
For each provider (DB, cache, vector store, memory layer):
- Can it be instantiated with zero configuration?
- Does it access environment variables at import time?
- Does it connect eagerly instead of lazily?
- Does it fail loudly and explicitly when misconfigured?

### 3. Import-Time Side Effects
Identify any module-level code that:
- initializes providers
- connects to external services
- creates resources
- reads environment variables

These must be flagged as potential bootstrap breakers.

### 4. Configuration Validation
Check whether:
- configuration completeness is validated before runtime starts
- missing configuration produces clear, early errors
- defaults are sufficient for minimal startup

### 5. Cold-Start Test Gap
Determine whether there exists a test that verifies:
- RAE can start from a completely empty environment
- no prior DB, cache, or vector data exists
- no environment variables are defined

If not, explain why existing tests fail to detect bootstrap issues.

---

## Constraints

- Do NOT redesign core architecture
- Do NOT change provider abstraction model
- Do NOT optimize logic or performance
- Focus strictly on **bootstrap correctness and determinism**

---

## Expected Output

Produce a structured report containing:

1. **Root Causes**
   - Concrete, code-level reasons why cold-start fails

2. **Failure Classifications**
   - Import-time side effects
   - Initialization order violations
   - Hidden state assumptions
   - Missing validation

3. **Minimal Fix Strategy**
   - What must be enforced to guarantee cold-start safety
   - Without architectural refactors

4. **Bootstrap Safety Rules**
   - A short list of non-negotiable rules
   - Example: “Import must never cause external connections”

---

## Success Criteria

After applying the findings:
- A fresh clone of the repository
- With no environment variables
- With no existing services or data
- Following documented steps

Must result in:
- deterministic startup
- or a **clear, explicit error explaining exactly what is missing**

---

## Important Note

This investigation is about **system correctness**, not developer convenience.

A system that only works after it has already been run once is considered **bootstrap-broken**.

