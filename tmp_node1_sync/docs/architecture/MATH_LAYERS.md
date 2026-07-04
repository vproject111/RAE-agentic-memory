# 🔢 RAE Mathematical Layers - Three-Tier Intelligence Model

> **Decision Intelligence Above Memory** - Mathematical framework that monitors, analyzes, and optimizes the 4-layer memory system.

---

## Overview

RAE's mathematical layer is not just metrics—it's a **complete decision-making framework** that sits above the 4-layer memory architecture. It provides the intelligence needed to make RAE stable, adaptive, predictable, and cost-efficient.

```
┌────────────────────────────────────────────────────────────┐
│         MATH-3: POLICY OPTIMIZATION                        │
│         (Decision Layer - What to do?)                     │
│  • Cost-Quality Frontier                                   │
│  • Optimal Retrieval Ratio                                 │
│  • Reflection Policy Efficiency                            │
└──────────────────────┬─────────────────────────────────────┘
                       │ Guides system behavior
┌──────────────────────┴─────────────────────────────────────┐
│         MATH-2: DYNAMICS TRACKING                          │
│         (Evolution Layer - How does it change?)            │
│  • Memory Drift Index                                      │
│  • Structural Drift                                        │
│  • Retention Curves                                        │
│  • Reflection Gain Score                                   │
└──────────────────────┬─────────────────────────────────────┘
                       │ Monitors quality
┌──────────────────────┴─────────────────────────────────────┐
│         MATH-1: STRUCTURE ANALYSIS                         │
│         (Topology Layer - How does it look?)               │
│  • Graph Connectivity Score                                │
│  • Semantic Coherence Score                                │
│  • Graph Entropy                                           │
│  • Cluster Consistency                                     │
└────────────────────────────────────────────────────────────┘
                       │ Analyzes structure
┌────────────────────────────────────────────────────────────┐
│   4-LAYER MEMORY SYSTEM (Cognitive Architecture)          │
│   Sensory → Working → Long-Term → Reflective              │
└────────────────────────────────────────────────────────────┘
```

**Key Insight**: Mathematical layers work **above** memory layers, continuously monitoring and optimizing all memory operations.

---

## 🔷 Math-1: Memory Structure Mathematics

> **The Geometry of Information** - How memory looks and organizes itself.

### Purpose

Analyzes the **structural topology** of the memory system:
- Knowledge graph connectivity
- Semantic coherence of stored information
- Information entropy and distribution
- Local and global structural patterns

### Key Metrics

#### 1.1. Graph Connectivity Score (GCS)

**Definition**: Measures how well-connected the knowledge graph is.

```
GCS = (# connected nodes) / (total # nodes)
```

**Interpretation**:
- **GCS < 0.5**: Fragmented knowledge (many isolated islands)
- **GCS = 0.5-0.8**: Moderate connectivity
- **GCS > 0.8**: Highly interconnected (good for GraphRAG)

**Why it matters**: High connectivity enables graph traversal to discover related concepts.

#### 1.2. Semantic Coherence Score (SCS)

**Definition**: Measures semantic consistency within memory clusters.

```
SCS = avg(cosine_similarity(memories_in_cluster))
```

**Interpretation**:
- **SCS < 0.6**: Low coherence (unrelated memories grouped together)
- **SCS = 0.6-0.8**: Moderate coherence
- **SCS > 0.8**: High coherence (well-organized semantic clusters)

**Why it matters**: High coherence means retrieval returns contextually related memories.

#### 1.3. Graph Entropy (H)

**Definition**: Measures information distribution and predictability.

```
H = -Σ p(i) * log2(p(i))

where p(i) = degree(node_i) / Σ degrees
```

**Interpretation**:
- **Low H**: Centralized (hub-and-spoke structure)
- **High H**: Distributed (many equally connected nodes)

**Why it matters**: Optimal entropy balances centralization (fast retrieval) with distribution (resilience).

#### 1.4. Cluster Consistency Ratio (CCR)

**Definition**: Measures stability of semantic clusters over time.

```
CCR = (# stable cluster assignments) / (total # nodes)
```

**Interpretation**:
- **CCR > 0.8**: Stable knowledge structure
- **CCR < 0.5**: Volatile, constantly changing

**Why it matters**: High CCR means the knowledge graph is converging to a stable structure.

### Implementation

**Code Reference**: [`apps/memory_api/core/math_structure.py`](../../apps/memory_api/core/math_structure.py)

```python
from apps.memory_api.core.math_structure import MathStructure

math1 = MathStructure(memory_repository, graph_repository)

# Analyze graph structure
metrics = await math1.analyze_structure(tenant_id, project_id)

print(f"Graph Connectivity: {metrics.graph_connectivity_score:.2f}")
print(f"Semantic Coherence: {metrics.semantic_coherence_score:.2f}")
print(f"Graph Entropy: {metrics.graph_entropy:.2f}")
```

---

## 🔶 Math-2: Memory Dynamics Mathematics

> **The Physics of Memory Evolution** - How memory changes over time.

### Purpose

Tracks **temporal evolution** of the memory system:
- Semantic drift (meaning changes)
- Structural drift (graph topology changes)
- Memory quality degradation
- Reflection effectiveness (Reflection Gain)
- Long-term retention curves

### Key Metrics

#### 2.1. Memory Drift Index (MDI)

**Definition**: Measures semantic drift of memories over time.

```
MDI(t) = 1 - cosine_similarity(embedding_t, embedding_t0)
```

**Interpretation**:
- **MDI < 0.1**: Stable (low drift)
- **MDI = 0.1-0.3**: Moderate drift
- **MDI > 0.3**: High drift (meaning changed significantly)

**Why it matters**: High drift indicates memories need re-embedding or pruning.

#### 2.2. Structural Drift (SD)

**Definition**: Measures changes in graph topology over time.

```
SD(t) = |E(t) - E(t-Δt)| / |E(t-Δt)|

where E = set of edges in knowledge graph
```

**Interpretation**:
- **SD < 0.05**: Stable structure
- **SD > 0.2**: Rapid structural evolution

**Why it matters**: Tracks how quickly the knowledge graph evolves.

#### 2.3. Retention Curve (RC)

**Definition**: Tracks how many memories survive over time.

```
RC(t) = (# memories at time t) / (# memories at t=0)
```

**Interpretation**:
- **Exponential decay**: RC(t) = e^(-λt) (typical for Sensory/Working)
- **Power law**: RC(t) = t^(-α) (typical for Long-Term/Reflective)

**Why it matters**: Validates that decay policies are working as intended.

#### 2.4. Reflection Gain Score (RG)

**Definition**: Measures effectiveness of reflection generation.

```
RG = (quality_after_reflection - quality_before) / quality_before
```

**Interpretation**:
- **RG > 0**: Reflection improved memory quality
- **RG < 0**: Reflection degraded quality (bad reflections!)
- **RG > 0.2**: Highly effective reflection

**Why it matters**: Validates that Reflection Engine V2 is adding value.

#### 2.5. Compression Fidelity Ratio (CFR)

**Definition**: Measures information loss during memory consolidation.

```
CFR = mutual_information(consolidated, original) / entropy(original)
```

**Interpretation**:
- **CFR > 0.8**: Low information loss (good compression)
- **CFR < 0.5**: High information loss (lossy compression)

**Why it matters**: Ensures summarization doesn't lose critical information.

### Implementation

**Code Reference**: [`apps/memory_api/core/math_dynamics.py`](../../apps/memory_api/core/math_dynamics.py)

```python
from apps.memory_api.core.math_dynamics import MathDynamics

math2 = MathDynamics(memory_repository)

# Track drift over time
drift_metrics = await math2.calculate_drift(
    tenant_id,
    project_id,
    time_window_days=7
)

print(f"Memory Drift Index: {drift_metrics.memory_drift_index:.3f}")
print(f"Structural Drift: {drift_metrics.structural_drift:.3f}")
print(f"Reflection Gain: {drift_metrics.reflection_gain:.2%}")
```

---

## 🔷 Math-3: Memory Policy Mathematics

> **Economics & Control Theory** - What decisions to make and when.

### Purpose

**Optimal decision-making** under constraints:
- Which memories to strengthen/prune
- When to trigger reflection (full vs lite)
- How to balance cost vs quality
- Optimal retrieval strategies
- Budget-aware operation

### Key Metrics

#### 3.1. Cost-Quality Frontier (CQF)

**Definition**: Pareto-optimal tradeoff between cost and quality.

```
CQF: min cost(operation)
     subject to: quality(operation) ≥ threshold
```

**Example**: Use cheap embedding model (OpenAI ada-002) for low-importance memories, expensive model (Claude) for high-importance.

**Why it matters**: Enables budget-aware operation without sacrificing critical quality.

#### 3.2. Optimal Retrieval Ratio (ORR)

**Definition**: Best balance between retrieval strategies.

```
ORR = argmax_weights {
    quality(results)
    subject to:
        w_vector + w_graph + w_sparse + w_fts = 1.0,
        latency ≤ max_latency,
        cost ≤ budget
}
```

**Example**: For factual queries, use more graph search. For semantic queries, use more vector search.

**Why it matters**: Dynamically adapts search strategy to query type and constraints.

#### 3.3. Reflection Policy Efficiency (RPE)

**Definition**: Measures cost-effectiveness of reflection generation.

```
RPE = reflection_gain / (LLM_cost + latency_cost)
```

**Interpretation**:
- **RPE > 1.0**: Reflection is cost-effective
- **RPE < 0.5**: Too expensive relative to value

**Why it matters**: Determines when to trigger full reflection vs lite reflection vs skip.

### Decision Rules

#### When to Reflect?

```python
def should_reflect(outcome, importance, budget_remaining):
    if outcome == "success" and importance < 0.5:
        return "skip"  # Don't reflect on low-importance successes

    if outcome == "failure":
        if budget_remaining > threshold:
            return "full"  # Full LLM-powered reflection
        else:
            return "lite"  # Heuristic-based reflection

    if importance > 0.8 and reflection_gain_history > 0.2:
        return "full"  # High-value memories deserve reflection

    return "skip"
```

#### When to Prune?

```python
def should_prune(memory):
    if memory.importance < 0.1 and memory.usage_count == 0:
        return True  # Never accessed, low importance

    if memory.drift_index > 0.3:
        return True  # Semantic drift too high

    if memory.age_days > retention_policy[memory.layer]:
        return True  # Exceeded TTL

    return False
```

### Implementation

**Code Reference**: [`apps/memory_api/core/math_policy.py`](../../apps/memory_api/core/math_policy.py)

```python
from apps.memory_api.core.math_policy import MathPolicy

math3 = MathPolicy(cost_controller, reflection_engine)

# Decide on reflection strategy
decision = await math3.decide_reflection_strategy(
    outcome="failure",
    importance=0.85,
    budget_remaining=50.00
)

print(f"Reflection Decision: {decision.strategy}")  # "full"
print(f"Estimated Cost: ${decision.estimated_cost:.2f}")
print(f"Expected Gain: {decision.expected_gain:.2%}")
```

---

## 🔄 Integration with RAE Architecture

### How Mathematical Layers Work With Memory Layers

```
User Query: "authentication bug from last week"
    ↓
MATH-3 Policy: Analyze query intent, budget, constraints
    ↓ Decision: Use hybrid search (vector=0.3, graph=0.4, sparse=0.2, fts=0.1)
    ↓
MATH-1 Structure: Check graph connectivity around "authentication" node
    ↓ Result: GCS = 0.87 (highly connected) → graph search recommended
    ↓
Hybrid Search: Execute multi-strategy search
    ↓
MATH-2 Dynamics: Filter results by drift (MDI < 0.3)
    ↓ Result: Remove 3 memories with high semantic drift
    ↓
Context Builder: Assemble Working Memory
    ↓
MATH-3 Policy: Inject reflections? (check budget + importance)
    ↓ Decision: Yes, inject 2 relevant reflections
    ↓
Return: Top-k results with context + reflections
```

### Real-World Example

**Scenario**: System runs out of budget mid-month.

```python
# Math-3 Policy adapts automatically:

if budget_remaining < 10% of monthly_limit:
    # Switch to degraded mode
    - Use cached embeddings only (no new API calls)
    - Skip LLM-based reflection (use heuristics)
    - Reduce graph traversal depth (2 → 1)
    - Increase cache TTL (5min → 30min)

# Quality degrades gracefully:
- Vector search: 100% → 90% (cached embeddings)
- Reflection quality: 95% → 70% (heuristic-based)
- Graph search: 85% → 75% (reduced depth)

# Cost: $150/month → $80/month (46% reduction)
```

---

## 📊 Mathematical Foundation

### Markov Decision Process (MDP) Formalism

RAE's mathematical layer is built on rigorous MDP theory:

```
MDP = (S, A, T, R, γ)

where:
- S: State space (memory system state)
- A: Action space (retrieve, prune, reflect, update graph, etc.)
- T: Transition function (deterministic state changes)
- R: Reward function (quality metrics)
- γ: Discount factor (future reward consideration)
```

**Reward Function**:
```
R(s_t, a_t, s_{t+1}) = w_q · Quality(a_t) - w_c · Cost(a_t)

where:
- Quality(a_t): Precision@k, MRR, semantic coherence
- Cost(a_t): LLM API cost + latency cost
- w_q, w_c: Configurable weights
```

**See**: [RAE Mathematical Formalization](../reference/architecture/rae-mathematical-formalization.md) for complete specification.

---

## 🧪 Benchmarking Mathematical Layers

Every benchmark should measure all three mathematical layers:

### Math-1 Metrics (Structure)
```bash
# Before/After comparison
python benchmarking/scripts/run_benchmark_math.py \
    --set academic_extended.yaml \
    --metrics structure

# Outputs:
# - Graph Connectivity Score: 0.85
# - Semantic Coherence Score: 0.78
# - Graph Entropy: 3.42
# - Cluster Consistency: 0.91
```

### Math-2 Metrics (Dynamics)
```bash
# Drift tracking over 30 days
python benchmarking/scripts/run_benchmark_math.py \
    --set stress_memory_drift.yaml \
    --metrics dynamics

# Outputs:
# - Memory Drift Index: 0.15 (low drift)
# - Structural Drift: 0.08 (stable)
# - Reflection Gain: +18.5% (effective)
# - Retention Curve: Exponential decay (λ=0.005)
```

### Math-3 Metrics (Policy)
```bash
# Cost-quality analysis
python benchmarking/scripts/run_benchmark_math.py \
    --set industrial_large.yaml \
    --metrics policy

# Outputs:
# - Cost-Quality Frontier: Optimal at $45/month for 0.85 quality
# - Reflection Policy Efficiency: 1.45 (cost-effective)
# - Budget adherence: 98.5% (stayed within limits)
```

**See**: [Benchmark Math Extension Guide](../project-design/active/BENCHMARK_MATH_EXTENSION.md)

---

## 🎯 Best Practices

### 1. Monitor All Three Layers

```python
# Regular health check (daily)
math_metrics = await rae.get_math_health()

if math_metrics.graph_connectivity < 0.5:
    logger.warning("Low graph connectivity - review entity linking")

if math_metrics.memory_drift_index > 0.3:
    logger.warning("High semantic drift - consider re-embedding")

if math_metrics.reflection_gain < 0:
    logger.error("Negative reflection gain - reflections are harmful!")
```

### 2. Use Math-3 for Decision-Making

```python
# Don't hardcode decisions - use Math-3 policy
decision = await math3.decide_action(
    action_type="reflection",
    context=current_state,
    constraints={"budget_remaining": 50.00, "latency_max_ms": 500}
)

if decision.recommended_action == "full_reflection":
    await reflection_engine.generate_full_reflection(...)
elif decision.recommended_action == "lite_reflection":
    await reflection_engine.generate_lite_reflection(...)
else:
    logger.info("Skipping reflection (not cost-effective)")
```

### 3. Track Trends, Not Just Snapshots

```python
# Don't just check current value - track trends
drift_trend = await math2.get_drift_trend(days=30)

if drift_trend.slope > 0.01:  # Drift accelerating
    logger.warning("Memory quality degrading - investigate!")
```

---

## 📚 Related Documentation

- **[Memory Layers](./MEMORY_LAYERS.md)** - 4-layer cognitive architecture
- **[Hybrid Search](./HYBRID_SEARCH.md)** - Multi-strategy retrieval
- **[Mathematical Formalization](../reference/architecture/rae-mathematical-formalization.md)** - Complete MDP specification
- **[Cost Controller](../reference/concepts/cost-controller.md)** - Budget management
- **[Benchmarking Guide](../../benchmarking/README.md)** - Testing mathematical layers

---

## 🔬 Implementation Status

| Component | Status | Tests | Coverage |
|-----------|--------|-------|----------|
| **Math-1: Structure** | ✅ Implemented | 42 tests | 85% |
| **Math-2: Dynamics** | ✅ Implemented | 38 tests | 78% |
| **Math-3: Policy** | 🟡 Partial | 25 tests | 65% |
| **MDP Formalism** | ✅ Complete | N/A | N/A |
| **Benchmarking** | ✅ Complete | 11 benchmarks | 100% |

**Code Location**: [`apps/memory_api/core/`](../../apps/memory_api/core/)

---

**Version**: 2.1.0
**Last Updated**: 2025-12-08
**Status**: Production Ready (Math-1/2), Beta (Math-3) ✅

**See also**: [Main README](../../README.md) | [Architecture Overview](../reference/concepts/architecture.md)
