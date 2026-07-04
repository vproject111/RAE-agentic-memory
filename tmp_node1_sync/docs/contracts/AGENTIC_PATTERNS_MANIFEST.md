# Agentic Patterns Manifest for RAE

## Version
schema: 1.0
project: RAE-agentic-memory
purpose: Map agentic design patterns into RAE memory and reasoning structures for Gemini CLI

---

## Definitions
# Agentic patterns are *observed behaviors* from LLM agents.
# These definitions map them to RAE memory events and layers.

### Prompt Chaining
description: A sequence of dependent prompts where output of one influences the next.
rae_event: chain_execution
rae_memory_layer: Episodic
fields:
  - chain_length
  - intermediate_outputs
  - context_growth
  - error_propagation
quality_contract:
  - if chain_length > 5 and no validation_breaks then tag: high_risk_sequence
  - if intermediate_outputs contain contradictions then trigger: reflective_analysis

---

### Routing Decision
description: Choosing one among multiple reasoning paths/tools.
rae_event: decision_point
rae_memory_layer: Episodic
fields:
  - alternatives
  - selected_path
  - decision_basis
  - outcome
quality_contract:
  - if decision_basis_confidence < 0.5 then trigger: HITL_review
  - if selected_path failed then record: routing_failure

---

### Tool Use
description: Agent invokes external tool/model.
rae_event: tool_invocation
rae_memory_layer: Working
fields:
  - tool_id
  - inputs
  - outputs
  - cost_metrics
quality_contract:
  - if cost_metrics.token_count > threshold then mark: heavy_tool_use
  - if output_errors then log: error_category

---

### Reflection Trigger
description: Agent self-evaluates output for correctness.
rae_event: reflection_trigger
rae_memory_layer: Reflective
fields:
  - rationale
  - confidence_before
  - confidence_after
  - timestamp
quality_contract:
  - if confidence_delta < 0 then escalate: deeper_reflection
  - if reflection fails then record: cognitive_failure

---

## Pattern to RAE Memory Mappings
mapping:
  - PromptChaining → chain_execution @ Episodic
  - Routing Decision → decision_point @ Episodic
  - Tool Use → tool_invocation @ Working
  - Reflection Trigger → reflection_trigger @ Reflective

---

## Quality System Overrides
# These rules define systemic reactions in RAE

rule: heavy_tool_use → create_summary_task @ Reflective
rule: routing_failure → increase_retrieval_context
rule: high_risk_sequence → breakpoint_reflection_epoch
rule: cognitive_failure → HITL_alert

---

## Diagnostics & Auditing
# Define expected trace output

trace_plan:
  - event_type
  - memory_layer
  - timestamp
  - decision_rationale
  - impact_assessment

---

## Usage Notes
# This document is read by Gemini CLI and informs:
# - event detection
# - memory layer assignment
# - quality overrides
