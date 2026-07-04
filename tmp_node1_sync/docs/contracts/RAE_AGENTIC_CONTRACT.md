# RAE Agentic Pattern + Security Contract (ISO 42001 + ISO 27000)
schema: rae-contract/v1
applies_to:
  - Gemini CLI working on RAE (code + operations)
  - Any agent/tooling that writes to RAE memory
status: active
owner: RAE maintainers
last_updated: 2026-01-17

---

## 0) Purpose (What this file is)
This file is a **normative execution contract**.  
It is NOT documentation “for humans only” and NOT a prompt suggestion.

Agents (including Gemini CLI) MUST:
- follow the **agentic pattern → RAE event** mappings,
- obey **ISO 27000 information security policies** (classification, flow, retention),
- produce **ISO 42001 audit traces** (why/what/how, accountable decisions),
- emit explicit **policy events** on violations.

RAE is the *arbiter*:
- ISO 42001: accountability / traceability / governance of AI behavior.
- ISO 27000: information classification / access / retention / audit.

---

## 1) Non-negotiable Principles
1. **Pattern ≠ Feature**
   - “Agentic patterns” are OBSERVABLE behaviors to be recorded, not framework features to implement.
2. **RAE is not an agent runtime**
   - RAE does not “plan/rout/chain tools” as a framework; it records and reflects.
3. **Security is enforced by policy, not model intuition**
   - LLM is not the security authority; policies are.
4. **Memory-layer separation is mandatory**
   - Working/Episodic/Semantic/Reflective have distinct allowed data classes and retention.

---

## 2) Glossary (RAE-centric)
- **Agentic Pattern**: an observable behavior of an agent (e.g., prompt chaining, routing, tool-use).
- **RAE Event**: structured record of an agentic pattern occurrence (typed + fields).
- **Information Class**: security label (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED).
- **Memory Layer**:
  - Working (short-lived operational context)
  - Episodic (time-stamped experiences)
  - Semantic (generalized knowledge)
  - Reflective (meta-insights, failure modes, policy conclusions)

---

## 3) ISO 27000 Information Security Contract

### 3.1 Information Classification (mandatory)
The agent MUST classify any info before persistence.

information_classes:
  PUBLIC:
    description: shareable, non-sensitive knowledge
    allowed_layers: [Semantic, Reflective]
    retention: long_term
    audit_required: false

  INTERNAL:
    description: internal engineering/system knowledge, non-personal
    allowed_layers: [Working, Episodic, Reflective]
    retention: medium_term
    audit_required: true

  CONFIDENTIAL:
    description: business-sensitive operational data (customers, costs, production KPIs, internal docs)
    allowed_layers: [Working, Episodic, Reflective]
    forbidden_layers: [Semantic]
    retention: short_term
    audit_required: true
    encryption_required: true

  RESTRICTED:
    description: highly sensitive (PII, credentials, legal case details, secrets, tokens, private keys)
    allowed_layers: [Working]
    forbidden_layers: [Episodic, Semantic, Reflective]
    retention: transient
    audit_required: true
    encryption_required: true
    hitl_required: true

### 3.2 Data Types (detection hints)
restricted_indicators:
  - credentials: [api_key, token, secret, private_key, password, session_cookie]
  - pii: [email, phone, address, pesel, id_number]
  - legal_sensitive: [court_case_details, prosecutor_documents, evidence_raw]
confidential_indicators:
  - commercial: [pricing, margin, contracts, supplier_terms]
  - operations: [MES exports, logistics manifests, production line telemetry]
internal_indicators:
  - engineering: [logs_without_pii, stacktraces_sanitized, architecture_notes]

### 3.3 Memory Write Rules (hard limits)
rules:
  - IF class == RESTRICTED:
      - DO NOT persist outside Working
      - MUST be encrypted in Working layer
      - MUST halt and require HITL approval to proceed
      - MUST emit security_event: restricted_detected
  - IF class == CONFIDENTIAL:
      - MUST NOT promote to Semantic
      - MUST enforce short retention + encryption-at-rest
  - IF class == INTERNAL:
      - OK for Episodic/Reflective; Semantic only after explicit sanitization + approval tag
  - PUBLIC:
      - OK for Semantic/Reflective

### 3.4 Retention & Purging (policy-driven)
retention_policy:
  transient: "minutes/hours (in-memory or TTL)"
  short_term: "days/weeks"
  medium_term: "weeks/months"
  long_term: "months/years"

The agent MUST attach retention label per event.
RAE MUST be able to purge by:
- class
- layer
- project/tenant
- time range
- tag (policy-violation, hitl-required)

---

## 4) ISO 42001 Governance & Accountability Contract

### 4.1 Every decision must be traceable
For any non-trivial action (routing, tool invocation, plan revision), the agent MUST record:
- decision rationale (brief)
- alternatives considered
- confidence estimate
- risk classification
- expected impact
- observed outcome

### 4.2 Human-in-the-loop (HITL) conditions
HITL is mandatory when:
- RESTRICTED data detected
- autonomous action modifies persistent memory schema/policies
- repeated failure indicates “unsafe drift”
- confidence < threshold for high-impact operations

### 4.3 Policy violation handling
On any violation, agent MUST:
1) stop/contain,
2) emit policy event,
3) produce a short reflective note: “what happened + why + how prevented next time”.

---

## 5) Canonical RAE Event Schema (minimum fields)
Each persisted event MUST include:

event:
  event_id: uuid
  timestamp: iso8601
  actor:
    agent_id: string
    agent_version: string
    runtime: [gemini_cli, other]
  context:
    project: string
    tenant: string | null
    session_id: string
    task_id: string | null
  classification:
    info_class: [PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED]
    retention: [transient, short_term, medium_term, long_term]
    contains_pii: boolean
    contains_secrets: boolean
  governance:
    decision_rationale: string
    alternatives: list[string] | null
    confidence: float (0..1)
    risk_level: [low, medium, high]
    hitl_required: boolean
  payload:
    pattern_type: string
    fields: object
  outcome:
    success: boolean
    error_type: string | null
    cost:
      tokens: int | null
      latency_ms: int | null
  audit:
    provenance:
      source_type: [codebase, user_input, tool_output, retrieved_memory, external_doc]
      source_ref: string | null
    integrity:
      content_hash: string | null
      signature: string | null

---

## 6) Agentic Pattern Catalogue → RAE Mappings (execution rules)

### 6.1 Prompt Chaining
pattern_type: prompt_chaining
default_layer: Episodic
default_class_max: CONFIDENTIAL

fields:
  - chain_length: int
  - step_summaries: list[string]  # sanitized
  - context_growth_tokens: int | null
  - validation_breaks: int
quality_rules:
  - IF chain_length > 5 AND validation_breaks == 0:
      - emit quality_event: high_risk_sequence
      - require reflective_analysis
security_rules:
  - IF info_class == RESTRICTED:
      - abort_chain + HITL

---

### 6.2 Routing Decision
pattern_type: routing_decision
default_layer: Episodic
default_class_max: CONFIDENTIAL

fields:
  - options: list[string]
  - selected: string
  - decision_basis: [rules, llm, embedding, hybrid]
  - basis_confidence: float
quality_rules:
  - IF basis_confidence < 0.5 AND risk_level != low:
      - HITL required
  - IF selected fails repeatedly:
      - emit quality_event: routing_failure
      - recommend policy update

---

### 6.3 Tool Invocation
pattern_type: tool_invocation
default_layer: Working
default_class_max: CONFIDENTIAL

fields:
  - tool_id: string
  - tool_inputs_summary: string  # sanitized
  - tool_outputs_summary: string # sanitized
  - tool_errors: list[string] | null
  - cost: {tokens:int|null, latency_ms:int|null}
quality_rules:
  - IF cost.tokens > threshold OR latency_ms > threshold:
      - emit quality_event: heavy_tool_use
      - suggest optimization / caching
security_rules:
  - NEVER send RESTRICTED to external tools (unless explicitly allowed + HITL)

---

### 6.4 Planning / Plan Revision
pattern_type: planning
default_layer: Episodic
default_class_max: INTERNAL

fields:
  - plan_version: int
  - steps: list[string]
  - changed_steps: list[string] | null
  - reason_for_change: string
quality_rules:
  - IF plan revisions > 3 without progress:
      - emit quality_event: thrashing
      - trigger reflective diagnosis

---

### 6.5 Reflection Trigger
pattern_type: reflection
default_layer: Reflective
default_class_max: INTERNAL

fields:
  - hypothesis: string
  - evidence_refs: list[string]
  - confidence_before: float
  - confidence_after: float
  - lesson: string
quality_rules:
  - IF confidence_after < confidence_before:
      - emit quality_event: negative_delta
      - suggest alternate strategy / HITL
security_rules:
  - Reflection MUST NOT store CONFIDENTIAL/RESTRICTED details verbatim;
    store only sanitized lessons + references.

---

### 6.6 Multi-agent Interaction
pattern_type: inter_agent_interaction
default_layer: Episodic
default_class_max: INTERNAL

fields:
  - participants: list[string]
  - roles: object
  - conflict_points: list[string] | null
  - resolution: string | null
quality_rules:
  - IF repeated conflicts:
      - emit quality_event: coordination_failure
      - recommend routing/role change

---

## 7) Enforcement: Policy Events (must exist)
policy_event_types:
  - restricted_detected
  - pii_detected
  - secret_detected
  - forbidden_layer_write_attempt
  - external_tool_blocked
  - hitl_required_stop
  - sanitization_required

On any policy event:
- agent MUST stop the unsafe action,
- write a minimal safe audit record (no secrets),
- request HITL if required.

---

## 8) Gemini CLI Integration Notes (operational)
This contract is intended to be loaded as a **single source of truth** for:
- event typing,
- memory-layer routing,
- classification & retention,
- audit trace requirements.

Recommended operational workflow:
1) On start: load this contract file.
2) For each action:
   - classify information
   - select pattern_type
   - build RAE event (min schema)
   - validate against policy rules
3) If violation:
   - emit policy event
   - halt + request HITL

---

## 9) Minimal Test Checklist (must be automated)
tests:
  - classification_required:
      - any persistence without info_class fails
  - restricted_never_persisted:
      - RESTRICTED cannot be written to Episodic/Semantic/Reflective
  - confidential_never_semantic:
      - CONFIDENTIAL cannot be promoted to Semantic
  - audit_fields_present:
      - decision_rationale, confidence, provenance required for routing/tool/planning
  - policy_event_emission:
      - forbidden write triggers policy event

---

## 10) Migration/Adoption Plan (incremental)
Phase 1 (logging only):
- Implement event schema + logging pipeline
- Emit policy events (do not block yet, except RESTRICTED)

Phase 2 (enforcement):
- Block forbidden layer writes
- Enforce retention + encryption flags
- HITL gates for restricted/high-risk operations

Phase 3 (self-improvement):
- Reflective analytics over quality_events
- Policy tuning suggestions (Feniks / RAE reflection loop)

---

## 11) Appendix: “Safe Summaries” rules (sanitization)
When summarizing inputs/outputs for persistence:
- remove direct identifiers, secrets, full raw dumps
- keep only:
  - what the action was
  - what decision was made
  - what changed
  - where to find original securely (reference id)

Allowed:
- hashes, ids, pointers to secured storage
Forbidden:
- raw tokens, passwords, private keys, personal addresses, full invoices, full legal evidence

---
END