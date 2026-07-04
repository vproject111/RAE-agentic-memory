# RAE – Plan to improve memory and reasoning benchmarks

This document describes how to move from current results:

- **LECT:** 100% episodic consistency (1,000 cycles)  
- **MMIT:** 99.4% isolation (3 leaks / 500 ops)  
- **GRDT:** depth 10, 58.3% coherence  
- **RST:** 62.5% consistency under noise (stable to 60%)  
- **MPEB:** 95.7% adaptation  
- **ORB:** 3/6 Pareto-optimal configs  

to a more "pro" level, without compromising system stability.

---

## 1. Quantitative Goals

| Benchmark | Current state                      | "Pro" goal                       |
|-----------|------------------------------------|----------------------------------|
| LECT      | 100% (1,000 cycles)                | Maintain 100%, extend to 10k     |
| MMIT      | 99.4% (3/500 leaks)                | ≥ 99.8% (≤ 1 leak / 500 ops)     |
| GRDT      | depth = 10, 58.3% coherence        | depth ≥ 12, ≥ 70% coherence      |
| RST       | 62.5% consistency, noise up to 60% | ≥ 75% consistency, noise up to 70% |
| MPEB      | 95.7% adaptation                   | ≥ 97% + no regression in LECT/MMIT|
| ORB       | 3/6 Pareto-optimal configurations  | ≥ 5/6 Pareto-optimal configurations|

Additionally: maintain **healthy services** (Postgres, Redis, Qdrant) within target latency thresholds.

---

## 2. LECT – maintaining 100% episodic consistency

LECT already has an **ideal** score. The goal is to **maintain quality** at a larger scale.

### 2.1. Actions

- [ ] Increase the number of test cycles from **1,000 → 10,000** in nightly mode.
- [ ] Add a test variant with:
  - [ ] Different episode sizes (micro / medium / long sequences).
  - [ ] Different event types (dialog, task, system, meta).
- [ ] Introduce a **"LECT regression suite"**:
  - [ ] A set of canonical histories that must always be replayed 1:1.
  - [ ] Mark them as critical in CI (pipeline break on regression).
- [ ] Add a metric:
  - [ ] `% temporal drift` (is event order preserved).
  - [ ] `% lost events` (should remain 0).

### 2.2. Passing condition

- [ ] 10,000 LECT test cycles, 0 errors, no regression in the next 5 CI runs.

---

## 3. MMIT – improving memory isolation (99.4% → 99.8%+)

The goal is to reduce leaks between:

- different agents,
- different sessions,
- different memory layers.

### 3.1. Architectural changes

- [ ] Introduce **hard separation of namespaces**:
  - [ ] explicit `agent_id` + `session_id` in every memory operation,
  - [ ] separate keys in Redis (prefix per agent + session),
  - [ ] separate collections / payload tags in Qdrant.
- [ ] Add a **"memory isolation guard"** layer:
  - [ ] Functions that check if the search result:
    - does not contain foreign `agent_id`,
    - does not contain foreign `session_id`.
  - [ ] Logging of every operation marked as a potential leak.

### 3.2. Test changes

- [ ] Extend MMIT to, for example, **2,000 operations** per run.
- [ ] Introduce tests:
  - [ ] "agent A" and "agent B" with conflicting episodes – no cross-access.
  - [ ] parallel operations (concurrency) with high load.
- [ ] Introduce a metric:
  - [ ] `leaks_per_1000_ops` (target < 2).

### 3.3. Passing condition

- [ ] ≤ 1 leak / 500 operations in 10 consecutive runs.  
- [ ] No leaks in tests with aggressive concurrency (at least 3 different scenarios).

---

## 4. GRDT – depth and coherence of reasoning

We want to:
- increase the **maximum reasoning depth** (10 → 12+),
- increase **coherence** (58.3% → ≥ 70%).

### 4.1. "Math" layer controller

- [x] Extract the **"reasoning controller"** as a separate module:
  - [ ] with parameters:
    - maximum depth,
    - acceptable level of uncertainty,
    - "token budget / step".
  - [ ] add heuristics:
    - earlier pruning of obviously contradictory paths,
    - rewarding coherence between memory layers (episodic/semantic/reflective).

### 4.2. Reasoning task curriculum

- [ ] Prepare a set of benchmarks:
  - [ ] simple cause-and-effect chains (depth 3–5),
  - [ ] planning scenarios (depth 5–8),
  - [ ] complex multi-stage scenarios (depth 8–12).
- [ ] For each task:
  - [ ] define the **golden standard** (ideal reasoning process),
  - [ ] measure:
    - **coherence score** (comparison of process vs standard),
    - **deviation score** (number of unnecessary steps / contradictions).

### 4.3. Reasoning telemetry

- [ ] Log:
  - [ ] number of reasoning steps per task,
  - [ ] points where reasoning "strays" from the standard,
  - [ ] impact of depth on costs and time.
- [ ] Based on this:
  - [ ] fine-tune controller parameters (e.g., different profiles: "strict", "balanced", "fast").

### 4.4. Passing condition

- [ ] Average coherence ≥ 70% in 3 consecutive benchmark runs.  
- [ ] No drop in LECT/MMIT due to changes in the math layer.

---

## 5. RST – noise resistance (62.5% → 75%+)

The goal is to:

- increase the stability of responses to disturbed data,
- increase the tolerated noise level from 60% to 70%.

### 5.1. Noise pipeline

- [ ] Implement a noise addition module:
  - [ ] random removal of prompt fragments,
  - [ ] semantic paraphrases,
  - [ ] insertion of misleading information.
- [ ] Test 3 levels:
  - [ ] low (20–30%),
  - [ ] medium (40–50%),
  - [ ] high (60–70%).

### 5.2. Defense strategies

- [ ] Add "noise-aware retrieval":
  - [ ] increased weight of the last reliable episodes,
  - [ ] penalization of contradictory vectors in Qdrant.
- [ ] Add "sanity checks" before reasoning:
  - [ ] detection of obvious contradictions in the input,
  - [ ] fallback: ask for clarification (if in interactive mode) or a more cautious response.

### 5.3. Passing condition

- [ ] ≥ 75% stable responses at 60–70% noise.  
- [ ] No significant increase in errors in tests without noise.

---

## 6. MPEB – adaptation (95.7% → 97%+)

We want to strengthen adaptation without breaking stability.

### 6.1. Multi-episode adaptation runs

- [ ] Design tests where:
  - [ ] the system receives a series of tasks within the same domain, but with changing rules,
  - [ ] we measure how quickly it adapts to new rules.
- [ ] Add metrics:
  - [ ] number of episodes to full adaptation,
  - [ ] impact of adaptation on other tasks (does it not degrade previous skills).

### 6.2. "Safe adaptation guard"

- [ ] Introduce a layer that:
  - [ ] distinguishes "temporary adaptation" (sandbox) from "permanent change",
  - [ ] does not allow overwriting key rules without multiple validations.

### 6.3. Passing condition

- [ ] ≥ 97% adaptation score in 3 runs.  
- [ ] No regression in LECT / MMIT after long adaptation sequences.

---

## 7. ORB – more Pareto-optimal configurations (3/6 → 5/6)

We want to find and solidify more configurations that are:

- **cheap + fast**,
- **accurate + stable**,
- **balanced**.

### 7.1. Configuration auto-tuner

- [ ] Define parameter space:
  - [ ] context size,
  - [ ] Redis caching strategy,
  - [ ] reasoning depth,
  - [ ] Qdrant similarity thresholds,
  - [ ] memory layer weights.
- [ ] Run:
  - [ ] grid search / random search,
  - [ ] optionally simple Bayesian search.
- [ ] For each configuration:
  - [ ] measure: costs, time, quality (LECT/MMIT/GRDT/RST/MPEB benchmarks).

### 7.2. Building the Pareto front

- [ ] Define:
  - [ ] "quality" objective (combined benchmark score),
  - [ ] "cost" objective (time + tokens),
  - [ ] "stability" objective (number of regressions).
- [ ] Calculate the Pareto front and save:
  - [ ] min. 5 configurations in the `profiles/` directory as:
    - `profile_research.yaml`,
    - `profile_enterprise_safe.yaml`,
    - `profile_fast_dev.yaml`,
    - `profile_mobile_lite.yaml` (if applicable),
    - `profile_balanced_default.yaml`.

### 7.3. Passing condition

- [ ] ≥ 5/6 configurations entering the Pareto front.  
- [ ] Documented profiles + usage description in README.

---

## 8. Telemetry and CI – tying everything into one system

### 8.1. Benchmark telemetry

- [ ] Send metrics to the telemetry system:
  - [ ] LECT/MMIT/GRDT/RST/MPEB/ORB in "time series" format.
- [ ] Build a dashboard:
  - [ ] trends of results over time,
  - [ ] regression detection (alerts).

### 8.2. CI / CD as a quality guardian

- [ ] Add a "Benchmark Gate" to CI:
  - [ ] if any benchmark falls below a set threshold:
    - CI red,
    - block merge to `main`.
- [ ] Add a "nightly full benchmarks" job:
  - [ ] full test suite (longer runs, more cycles),
  - [ ] archive results for analysis.

---

## 9. Implementation Schedule

Proposed iterative approach (can be in weeks or sprints):

### Iteration 1 – Quick wins

- [ ] Extend LECT to 10,000 cycles.  
- [ ] Memory namespaces (MMIT), basic isolation guard.  
- [ ] Telemetry for all benchmarks.

### Iteration 2 – Reasoning and noise

- [x] Extract "reasoning controller" (GRDT).  
- [ ] Noise pipeline + noise-aware retrieval (RST).  
- [ ] First version of configuration auto-tuner (ORB).

### Iteration 3 – Adaptation and Pareto

- [ ] Multi-episode adaptation runs (MPEB).  
- [ ] Build `profiles/*.yaml` and Pareto front (ORB).  
- [ ] Connect everything with CI / Benchmark Gate.

---

## 10. Definition of "DONE" for the plan

The plan can be considered implemented when:

- [ ] LECT is stably 100% on 10,000 cycles.  
- [ ] MMIT ≤ 1 leak / 500 ops in 10 runs.  
- [ ] GRDT: depth ≥ 12, coherence ≥ 70%.  
- [ ] RST: ≥ 75% consistency at 60–70% noise.  
- [ ] MPEB: ≥ 97% adaptation without regression in other benchmarks.  
- [ ] ORB: ≥ 5/6 Pareto-optimal configurations + described profiles.  
- [ ] CI blocks merge on benchmark regression.  
- [ ] Telemetry and dashboard allow tracking quality trends over time.

