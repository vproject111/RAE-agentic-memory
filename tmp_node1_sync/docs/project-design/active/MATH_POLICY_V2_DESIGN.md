# Math Layer Controller Policy v2 - Data-Driven Design

**Document Type**: Architectural Design
**Target**: Iteration 2 of MathLayerController
**Status**: Draft
**Date**: 2025-12-07

---

## 1. Executive Summary

This document defines **Policy v2** for the Math Layer Controller - a data-driven, feature-weighted approach to selecting between three mathematical levels (L1, L2, L3) for RAE memory operations.

### Key Design Goals

1. **Maximize quality-adjusted return** while respecting cost/latency constraints
2. **Reduce variance** - current MRR median=0.0 vs max=1.0 indicates inconsistency
3. **Explainability** - every decision must have human-readable justification
4. **Extensibility** - prepare groundwork for ML-based policy (Iteration 3)
5. **Safety-first** - prefer L1 when uncertain, never exceed budgets

### Summary of Changes from v1

| Aspect | Policy v1 (Current) | Policy v2 (Proposed) |
|--------|---------------------|----------------------|
| Level Selection | Simple if-else rules | Weighted feature scoring |
| Reward Function | Basic (success + quality - cost) | Multi-objective with penalties |
| Feature Usage | 5-6 features | 15+ features with importance weights |
| Confidence | Static calculation | Dynamic, history-aware |
| Monitoring | Log-only | Active anomaly detection |

---

## 2. Reward Function Design

### 2.1 Mathematical Formulation

The reward function is a weighted combination of quality, cost, and stability components:

```
R(decision, outcome) = w_q * Q(outcome)
                     - w_c * C(decision)
                     - w_s * S(outcome)
                     - P(outcome)
```

Where:
- `Q(outcome)`: Quality component
- `C(decision)`: Cost component
- `S(outcome)`: Stability penalty component
- `P(outcome)`: Catastrophic failure penalty

### 2.2 Quality Component Q(outcome)

Quality measures how well the memory operation performed:

```
Q(outcome) = w_mrr * MRR
           + w_hit * HitRate@5
           + w_prec * Precision@5
           + w_orr * OptimalRetrievalRatio
```

**Default Weights** (configurable):
```yaml
quality_weights:
  mrr: 0.35           # Mean Reciprocal Rank (primary)
  hit_rate: 0.30      # Hit Rate @5 (secondary)
  precision: 0.15     # Precision @5
  orr: 0.20           # Optimal Retrieval Ratio
```

**Rationale**:
- MRR is primary because rank position matters for user experience
- Hit rate ensures we find *something* relevant
- Precision prevents noise in results
- ORR validates we're getting the *best* memories

### 2.3 Cost Component C(decision)

Cost captures computational and monetary expense:

```
C(decision) = (cost_multiplier(level) * base_cost) / budget_remaining
            + latency_penalty(actual_latency, budget_latency)
```

Where:
```python
def cost_multiplier(level: MathLevel) -> float:
    return {
        MathLevel.L1: 1.0,    # Baseline
        MathLevel.L2: 2.5,    # Information-theoretic overhead
        MathLevel.L3: 4.0,    # Meta-learning + ensemble
    }[level]

def latency_penalty(actual_ms: float, budget_ms: float) -> float:
    if budget_ms is None:
        return 0.0
    ratio = actual_ms / budget_ms
    if ratio <= 0.8:
        return 0.0               # Within budget
    elif ratio <= 1.0:
        return 0.2 * (ratio - 0.8) / 0.2  # Linear ramp
    else:
        return 1.0 + (ratio - 1.0) * 2.0  # Penalty accelerates
```

### 2.4 Stability Penalty S(outcome)

Stability measures consistency and drift:

```
S(outcome) = w_drift * MemoryDriftIndex
           + w_structural * StructuralDrift
           + w_churn * LevelChurn
```

Where `LevelChurn` penalizes frequent switching between levels:

```python
def level_churn_penalty(history: List[MathLevel], window: int = 10) -> float:
    """Penalize excessive level switching"""
    if len(history) < 2:
        return 0.0
    recent = history[-window:]
    transitions = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
    return transitions / (len(recent) - 1)  # 0.0 = stable, 1.0 = switches every time
```

**Default Weights**:
```yaml
stability_weights:
  memory_drift: 0.3     # Semantic drift in memories
  structural_drift: 0.3 # Graph topology changes
  level_churn: 0.4      # Penalize oscillation between levels
```

### 2.5 Catastrophic Failure Penalty P(outcome)

Binary penalties for severe failures:

```python
def catastrophic_penalty(outcome: Outcome) -> float:
    penalty = 0.0

    # Complete retrieval failure (MRR = 0 when expecting results)
    if outcome.expected_results and outcome.mrr == 0.0:
        penalty += PENALTY_ZERO_MRR  # 2.0

    # System error or timeout
    if outcome.error_occurred:
        penalty += PENALTY_ERROR  # 3.0

    # Budget violation (exceeded hard limits)
    if outcome.budget_exceeded:
        penalty += PENALTY_BUDGET_VIOLATION  # 5.0

    # Quality collapse (MRR dropped > 50% from baseline)
    if outcome.mrr < outcome.baseline_mrr * 0.5:
        penalty += PENALTY_QUALITY_COLLAPSE  # 1.5

    return penalty
```

**Default Penalty Values**:
```yaml
penalties:
  zero_mrr: 2.0           # Complete retrieval failure
  error: 3.0              # System error
  budget_violation: 5.0   # Hard limit exceeded
  quality_collapse: 1.5   # Significant quality drop
  timeout: 2.5            # Operation timed out
```

### 2.6 Complete Reward Formula

Putting it all together:

```python
def calculate_reward(
    decision: MathDecision,
    outcome: Outcome,
    config: RewardConfig,
) -> float:
    """
    Calculate reward for a decision-outcome pair.

    Range: Approximately -10.0 to +1.0
    - Positive: Good decision
    - Negative: Bad decision (penalties applied)
    - Near 0: Neutral (cost offset quality)
    """
    # Quality (0.0 to 1.0)
    quality = (
        config.quality_weights.mrr * outcome.mrr +
        config.quality_weights.hit_rate * outcome.hit_rate_5 +
        config.quality_weights.precision * outcome.precision_5 +
        config.quality_weights.orr * outcome.orr
    )

    # Cost (0.0 to ~2.0 typically)
    base_cost = decision.selected_level.cost_multiplier * 0.1
    latency_cost = latency_penalty(outcome.latency_ms, decision.features_used.latency_budget_ms)
    cost = base_cost + latency_cost

    # Stability (0.0 to 1.0)
    stability = (
        config.stability_weights.memory_drift * outcome.memory_drift +
        config.stability_weights.structural_drift * outcome.structural_drift +
        config.stability_weights.level_churn * level_churn_penalty(decision_history)
    )

    # Catastrophic penalties (0.0 to ~10.0)
    penalty = catastrophic_penalty(outcome)

    # Weighted combination
    reward = (
        config.w_quality * quality -
        config.w_cost * cost -
        config.w_stability * stability -
        penalty
    )

    return reward
```

**Default Component Weights**:
```yaml
reward_weights:
  quality: 1.0      # Full weight on quality
  cost: 0.3         # Moderate cost penalty
  stability: 0.2    # Light stability preference
```

---

## 3. Feature Importance Analysis

### 3.1 Feature Categories

Based on analysis of the existing system, features are grouped into four categories:

#### Category A: Task Context (Highest Importance)
| Feature | Type | Range | Importance | Rationale |
|---------|------|-------|------------|-----------|
| task_type | Categorical | 7 values | 0.25 | Different tasks need different levels |
| session_length | Integer | 0-1000+ | 0.15 | Long sessions benefit from L2/L3 |
| is_first_turn | Boolean | 0/1 | 0.10 | First turn needs fast response |

#### Category B: Memory State (High Importance)
| Feature | Type | Range | Importance | Rationale |
|---------|------|-------|------------|-----------|
| memory_count | Integer | 0-10000+ | 0.20 | Scale determines optimal level |
| memory_entropy | Float | 0.0-4.0 | 0.18 | High entropy needs L2 |
| graph_density | Float | 0.0-1.0 | 0.12 | Sparse graphs need restructuring |
| graph_connectivity | Float | 0.0-5.0 | 0.10 | GCS indicates integration quality |

#### Category C: Recent Performance (Medium Importance)
| Feature | Type | Range | Importance | Rationale |
|---------|------|-------|------------|-----------|
| recent_mrr | Float | 0.0-1.0 | 0.15 | Poor MRR suggests upgrade needed |
| recent_scs | Float | 0.0-1.0 | 0.08 | Semantic coherence quality |
| previous_level_success | Boolean | 0/1 | 0.12 | Repeat successful patterns |

#### Category D: Constraints (Override Priority)
| Feature | Type | Range | Importance | Rationale |
|---------|------|-------|------------|-----------|
| cost_budget | Float | 0.0-inf | OVERRIDE | Hard constraint |
| latency_budget_ms | Integer | 0-inf | OVERRIDE | Hard constraint |

### 3.2 Feature Computation

```python
@dataclass
class FeaturesV2(Features):
    """Extended features for Policy v2"""

    # New features beyond v1
    quality_trend: float = 0.0        # MRR trend over last N queries
    error_rate_recent: float = 0.0    # Error rate in last N operations
    level_history: List[MathLevel] = field(default_factory=list)
    consecutive_same_level: int = 0   # Stability indicator
    query_complexity: float = 0.0     # Estimated query difficulty
    time_since_reflection: int = 0    # Operations since last reflection

    def compute_derived_features(self) -> Dict[str, float]:
        """Compute derived features for decision making"""
        return {
            # Scale features
            "memory_scale": min(self.memory_count / 1000, 1.0),  # Normalized
            "session_scale": min(self.session_length / 50, 1.0),

            # Entropy normalization
            "entropy_normalized": self.memory_entropy / 4.0,  # Assume max ~4.0

            # Quality indicators
            "quality_declining": 1.0 if self.quality_trend < -0.1 else 0.0,
            "quality_improving": 1.0 if self.quality_trend > 0.1 else 0.0,

            # Stability indicators
            "level_stable": 1.0 if self.consecutive_same_level >= 5 else 0.0,
            "needs_reflection": 1.0 if self.time_since_reflection > 100 else 0.0,
        }
```

### 3.3 Feature Importance Weights

Weights determine how much each feature influences level selection:

```yaml
feature_weights:
  # Category A: Task Context
  task_type_score: 0.25
  session_length_score: 0.15

  # Category B: Memory State
  memory_count_score: 0.20
  entropy_score: 0.18
  graph_density_score: 0.12

  # Category C: Performance
  recent_mrr_score: 0.15
  previous_success_score: 0.12

  # Bias towards stability
  stability_bonus: 0.10
```

---

## 4. Level Selection Strategy

### 4.1 Decision Flow Chart

```
                    START
                      │
                      ▼
              ┌───────────────┐
              │ Check Hard    │
              │ Constraints   │
              └───────┬───────┘
                      │
           ┌──────────┴──────────┐
           │                     │
           ▼                     ▼
    Budget/Latency         No Constraints
    Constrained
           │                     │
           ▼                     ▼
        USE L1            ┌──────────────┐
        (forced)          │ Compute      │
                          │ Level Scores │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │ Apply Task   │
                          │ Type Priors  │
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │ Check Quality│
                          │ Thresholds   │
                          └──────┬───────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
            Score(L1) >   Score(L2) >   Score(L3) >
            others        others        others
                    │            │            │
                    ▼            ▼            ▼
                 USE L1       USE L2       USE L3
                                 │
                                 ▼
                          ┌──────────────┐
                          │ Apply Safety │
                          │ Overrides    │
                          └──────┬───────┘
                                 │
                                 ▼
                          FINAL DECISION
```

### 4.2 Level Scoring Algorithm

Each level gets a score based on features:

```python
def compute_level_scores(features: FeaturesV2, config: PolicyConfig) -> Dict[MathLevel, float]:
    """
    Compute a score for each level based on current features.
    Higher score = more appropriate level.
    """
    scores = {
        MathLevel.L1: 0.0,
        MathLevel.L2: 0.0,
        MathLevel.L3: 0.0,
    }

    # === L1 Score: Fast, simple, cheap ===
    scores[MathLevel.L1] = (
        0.3 +  # Base score (default preference)
        0.2 * (1.0 - features.memory_scale) +  # Better for small memory
        0.2 * (1.0 - features.entropy_normalized) +  # Better for organized memory
        0.3 * features.task_type_l1_affinity() +  # Task preference
        0.1 * float(features.previous_level == MathLevel.L1 and features.previous_level_success)
    )

    # === L2 Score: Information-theoretic, balanced ===
    scores[MathLevel.L2] = (
        0.0 +  # No base (must earn it)
        0.25 * features.entropy_normalized +  # High entropy needs L2
        0.20 * features.memory_scale +  # Larger memories benefit from L2
        0.25 * features.task_type_l2_affinity() +  # Task preference
        0.15 * (1.0 - features.recent_mrr) +  # Poor quality suggests upgrade
        0.10 * float(features.previous_level == MathLevel.L2 and features.previous_level_success) +
        0.05 * features.session_scale  # Longer sessions benefit
    )

    # === L3 Score: Adaptive, meta-learning ===
    scores[MathLevel.L3] = (
        -0.2 +  # Negative base (must strongly earn it)
        0.20 * features.memory_scale +  # Large memory benefits
        0.15 * features.entropy_normalized +  # Complex state
        0.25 * features.task_type_l3_affinity() +  # Task preference
        0.20 * float(features.recent_mrr < 0.3) +  # Quality crisis
        0.15 * float(features.session_length > 20) +  # Long session
        0.10 * float(features.previous_level == MathLevel.L3 and features.previous_level_success)
    )

    # === Apply level-specific thresholds ===
    if features.memory_count < config.l2_memory_threshold:
        scores[MathLevel.L2] *= 0.5  # Penalize L2 for small memory
        scores[MathLevel.L3] *= 0.3  # Strongly penalize L3

    if features.memory_count < config.l3_memory_threshold:
        scores[MathLevel.L3] *= 0.5  # Penalize L3 for medium memory

    return scores
```

### 4.3 Task Type Affinity Functions

```python
def task_type_l1_affinity(task_type: TaskType) -> float:
    """How well L1 suits this task type (0.0 to 1.0)"""
    return {
        TaskType.MEMORY_STORE: 0.9,       # Simple insertion
        TaskType.MEMORY_RETRIEVE: 0.7,    # Basic retrieval OK
        TaskType.REFLECTION_LIGHT: 0.8,   # Light reflection is L1 territory
        TaskType.MEMORY_CONSOLIDATE: 0.3, # Consolidation needs more
        TaskType.REFLECTION_DEEP: 0.2,    # Deep reflection needs more
        TaskType.GRAPH_UPDATE: 0.4,       # Structure changes need care
        TaskType.CONTEXT_SELECT: 0.5,     # Context selection is balanced
    }[task_type]

def task_type_l2_affinity(task_type: TaskType) -> float:
    """How well L2 suits this task type (0.0 to 1.0)"""
    return {
        TaskType.MEMORY_STORE: 0.3,       # L1 usually sufficient
        TaskType.MEMORY_RETRIEVE: 0.5,    # Can help with complex queries
        TaskType.REFLECTION_LIGHT: 0.4,   # Sometimes useful
        TaskType.MEMORY_CONSOLIDATE: 0.8, # Consolidation benefits from IT
        TaskType.REFLECTION_DEEP: 0.7,    # Deep reflection benefits
        TaskType.GRAPH_UPDATE: 0.8,       # Graph optimization is L2 strength
        TaskType.CONTEXT_SELECT: 0.9,     # Context selection is L2 core use case
    }[task_type]

def task_type_l3_affinity(task_type: TaskType) -> float:
    """How well L3 suits this task type (0.0 to 1.0)"""
    return {
        TaskType.MEMORY_STORE: 0.1,       # Overkill for storage
        TaskType.MEMORY_RETRIEVE: 0.3,    # Rarely needed
        TaskType.REFLECTION_LIGHT: 0.2,   # Light reflection doesn't need L3
        TaskType.MEMORY_CONSOLIDATE: 0.7, # Can benefit from meta-learning
        TaskType.REFLECTION_DEEP: 0.9,    # Deep reflection is L3 primary use
        TaskType.GRAPH_UPDATE: 0.5,       # L2 usually sufficient
        TaskType.CONTEXT_SELECT: 0.6,     # Can help in complex cases
    }[task_type]
```

### 4.4 Decision Thresholds

```yaml
# Level selection thresholds
thresholds:
  # Minimum memory count for each level
  l1_memory_min: 0        # L1 works at any scale
  l2_memory_min: 30       # L2 needs enough data for entropy analysis
  l3_memory_min: 200      # L3 needs substantial history for meta-learning

  # Minimum session length
  l2_session_min: 3       # Need some context
  l3_session_min: 10      # Need substantial session history

  # Quality triggers (upgrade level if quality below threshold)
  mrr_upgrade_threshold: 0.4    # Consider upgrade if MRR < 0.4
  mrr_downgrade_threshold: 0.8  # Can downgrade if MRR > 0.8 consistently

  # Entropy thresholds
  entropy_l2_trigger: 0.7       # High entropy suggests L2
  entropy_l3_trigger: 1.5       # Very high entropy might need L3

  # Confidence thresholds
  min_confidence_for_l2: 0.6    # Need confidence to use L2
  min_confidence_for_l3: 0.75   # Need high confidence to use L3

  # Score difference threshold
  min_score_advantage: 0.15     # Level must beat alternative by this margin
```

---

## 5. Policy Rules v2 - Weighted Decision System

### 5.1 Decision Algorithm Pseudocode

```python
class PolicyV2:
    """Data-driven policy for math level selection"""

    def __init__(self, config: PolicyConfig):
        self.config = config
        self.decision_history: List[DecisionWithOutcome] = []
        self.feature_weights = config.feature_weights

    def select_level(self, context: TaskContext) -> MathDecision:
        """Main decision entry point"""

        # Step 1: Extract and compute features
        features = self.extract_features(context)
        derived = features.compute_derived_features()

        # Step 2: Check hard constraints (OVERRIDE)
        if self._is_budget_constrained(features):
            return self._create_decision(
                level=MathLevel.L1,
                features=features,
                reason="Budget constraint forces L1",
                confidence=0.95,
            )

        if self._is_latency_constrained(features):
            return self._create_decision(
                level=MathLevel.L1,
                features=features,
                reason="Latency constraint forces L1",
                confidence=0.95,
            )

        # Step 3: Compute level scores
        scores = self.compute_level_scores(features)

        # Step 4: Apply safety overrides
        scores = self._apply_safety_overrides(scores, features)

        # Step 5: Select highest scoring allowed level
        allowed_levels = self._get_allowed_levels(features)
        best_level = max(
            allowed_levels,
            key=lambda lvl: scores[lvl]
        )

        # Step 6: Check confidence threshold
        confidence = self._compute_confidence(scores, features)
        if confidence < self.config.min_confidence_for_l2 and best_level != MathLevel.L1:
            # Fall back to L1 if uncertain
            best_level = MathLevel.L1
            confidence = 0.7  # Adjusted for fallback

        # Step 7: Build decision
        return self._create_decision(
            level=best_level,
            features=features,
            reason=self._build_explanation(best_level, scores, features),
            confidence=confidence,
        )

    def _apply_safety_overrides(
        self,
        scores: Dict[MathLevel, float],
        features: FeaturesV2,
    ) -> Dict[MathLevel, float]:
        """Apply safety checks that can override scoring"""

        # Safety 1: Block L3 in production profiles
        if self.config.profile in ["production", "cheap"]:
            scores[MathLevel.L3] = -999.0

        # Safety 2: Block L2/L3 after consecutive errors
        if features.error_rate_recent > self.config.error_threshold:
            scores[MathLevel.L2] *= 0.3
            scores[MathLevel.L3] = -999.0

        # Safety 3: Force downgrade after budget violation
        if self._recent_budget_violation():
            scores[MathLevel.L2] *= 0.5
            scores[MathLevel.L3] = -999.0

        # Safety 4: Stability bonus for consistent level
        if features.consecutive_same_level >= 5:
            current_level = features.level_history[-1] if features.level_history else MathLevel.L1
            scores[current_level] += self.config.stability_bonus

        return scores

    def _compute_confidence(
        self,
        scores: Dict[MathLevel, float],
        features: FeaturesV2,
    ) -> float:
        """Compute confidence in the decision"""

        # Base confidence from score margin
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) >= 2:
            margin = sorted_scores[0] - sorted_scores[1]
            margin_confidence = min(margin / 0.5, 1.0)  # 0.5 margin = full confidence
        else:
            margin_confidence = 1.0

        # Data confidence (more data = more confident)
        data_confidence = min(features.memory_count / 100, 1.0)

        # History confidence (successful history = more confident)
        if features.previous_level_success is True:
            history_confidence = 0.9
        elif features.previous_level_success is False:
            history_confidence = 0.6
        else:
            history_confidence = 0.7

        # Weighted combination
        confidence = (
            0.5 * margin_confidence +
            0.3 * data_confidence +
            0.2 * history_confidence
        )

        return min(max(confidence, 0.3), 0.99)  # Clamp to [0.3, 0.99]
```

### 5.2 Feature-to-Level Mapping Rules

Beyond weighted scoring, specific rules handle edge cases:

```python
class PolicyRulesV2:
    """Explicit rules that override or modify scoring"""

    @staticmethod
    def rule_first_turn_fast() -> PolicyRule:
        """First turn should be fast - prefer L1"""
        return PolicyRule(
            name="first_turn_fast",
            condition=lambda f: f.is_first_turn,
            action=lambda scores: {**scores, MathLevel.L1: scores[MathLevel.L1] + 0.3},
            priority=10,
        )

    @staticmethod
    def rule_quality_crisis_upgrade() -> PolicyRule:
        """Quality crisis should trigger upgrade"""
        return PolicyRule(
            name="quality_crisis_upgrade",
            condition=lambda f: f.recent_mrr < 0.2 and f.memory_count > 50,
            action=lambda scores: {
                MathLevel.L1: scores[MathLevel.L1] - 0.3,
                MathLevel.L2: scores[MathLevel.L2] + 0.2,
                MathLevel.L3: scores[MathLevel.L3] + 0.1,
            },
            priority=8,
        )

    @staticmethod
    def rule_high_entropy_needs_l2() -> PolicyRule:
        """High entropy memory benefits from L2's information-theoretic approach"""
        return PolicyRule(
            name="high_entropy_needs_l2",
            condition=lambda f: f.memory_entropy > 1.0 and f.memory_count > 30,
            action=lambda scores: {**scores, MathLevel.L2: scores[MathLevel.L2] + 0.25},
            priority=7,
        )

    @staticmethod
    def rule_deep_reflection_needs_sophistication() -> PolicyRule:
        """Deep reflection tasks need L2 or L3"""
        return PolicyRule(
            name="deep_reflection_needs_sophistication",
            condition=lambda f: f.task_type == TaskType.REFLECTION_DEEP,
            action=lambda scores: {
                MathLevel.L1: scores[MathLevel.L1] - 0.2,
                MathLevel.L2: scores[MathLevel.L2] + 0.15,
                MathLevel.L3: scores[MathLevel.L3] + 0.2,
            },
            priority=6,
        )

    @staticmethod
    def rule_stable_success_stay() -> PolicyRule:
        """If current level is working well, don't change"""
        return PolicyRule(
            name="stable_success_stay",
            condition=lambda f: (
                f.previous_level_success is True and
                f.recent_mrr > 0.7 and
                f.consecutive_same_level >= 3
            ),
            action=lambda scores: {
                **scores,
                f.previous_level: scores[f.previous_level] + 0.2
            },
            priority=5,
        )

    @staticmethod
    def rule_consolidation_prefer_l2() -> PolicyRule:
        """Memory consolidation benefits from information-theoretic optimization"""
        return PolicyRule(
            name="consolidation_prefer_l2",
            condition=lambda f: f.task_type == TaskType.MEMORY_CONSOLIDATE,
            action=lambda scores: {**scores, MathLevel.L2: scores[MathLevel.L2] + 0.2},
            priority=5,
        )

    @staticmethod
    def get_all_rules() -> List[PolicyRule]:
        """Get all policy rules sorted by priority"""
        rules = [
            PolicyRulesV2.rule_first_turn_fast(),
            PolicyRulesV2.rule_quality_crisis_upgrade(),
            PolicyRulesV2.rule_high_entropy_needs_l2(),
            PolicyRulesV2.rule_deep_reflection_needs_sophistication(),
            PolicyRulesV2.rule_stable_success_stay(),
            PolicyRulesV2.rule_consolidation_prefer_l2(),
        ]
        return sorted(rules, key=lambda r: r.priority, reverse=True)
```

---

## 6. Configuration Schema

### 6.1 Complete YAML Schema

```yaml
# Math Layer Controller Configuration - Policy v2
# ================================================

version: "2.0"
profile: "research"  # research | production | cheap

# === Reward Function Configuration ===
reward:
  # Component weights
  weights:
    quality: 1.0
    cost: 0.3
    stability: 0.2

  # Quality sub-weights (must sum to 1.0)
  quality_weights:
    mrr: 0.35
    hit_rate: 0.30
    precision: 0.15
    orr: 0.20

  # Stability sub-weights (must sum to 1.0)
  stability_weights:
    memory_drift: 0.3
    structural_drift: 0.3
    level_churn: 0.4

  # Catastrophic penalties
  penalties:
    zero_mrr: 2.0
    error: 3.0
    budget_violation: 5.0
    quality_collapse: 1.5
    timeout: 2.5

# === Feature Configuration ===
features:
  # Feature importance weights
  weights:
    task_type: 0.25
    memory_count: 0.20
    entropy: 0.18
    session_length: 0.15
    recent_mrr: 0.15
    previous_success: 0.12

  # History window sizes
  history:
    mrr_window: 10          # Number of recent queries for MRR trend
    level_window: 20        # Number of recent decisions for stability
    error_window: 50        # Number of recent operations for error rate

# === Level Selection Configuration ===
level_selection:
  # Allowed levels per profile
  allowed_levels:
    research: [L1, L2, L3]
    production: [L1, L2]
    cheap: [L1]

  # Minimum memory count thresholds
  memory_thresholds:
    l2_min: 30
    l3_min: 200

  # Minimum session length thresholds
  session_thresholds:
    l2_min: 3
    l3_min: 10

  # Entropy thresholds
  entropy_thresholds:
    l2_trigger: 0.7
    l3_trigger: 1.5

  # Quality thresholds
  quality_thresholds:
    mrr_upgrade: 0.4      # Consider upgrade if below
    mrr_downgrade: 0.8    # Can downgrade if above (consistently)

  # Confidence requirements
  confidence_thresholds:
    l2_min: 0.6
    l3_min: 0.75

  # Score margin required
  min_score_advantage: 0.15

# === Safety Configuration ===
safety:
  # Profile-based restrictions
  l3_blacklist_profiles: [production, cheap]
  l2_blacklist_profiles: [cheap]

  # Error handling
  error_threshold: 0.1             # Error rate to trigger downgrade
  consecutive_error_limit: 3       # Force L1 after N consecutive errors

  # Budget protection
  budget_violation_cooldown: 10    # Operations to stay at L1 after violation

  # Stability incentives
  stability_bonus: 0.1             # Bonus for staying at same level
  churn_penalty: 0.05              # Penalty per level switch (recent)

  # Rollback configuration
  rollback:
    enabled: true
    quality_drop_threshold: 0.3    # MRR drop to trigger rollback
    min_observations: 5            # Observations before rollback decision

# === Strategy Configuration ===
strategies:
  L1:
    available: [default, relevance_scoring, importance_scoring]
    default: relevance_scoring
    params:
      relevance_scoring:
        recency_decay_days: 7
        semantic_weight: 0.6
        recency_weight: 0.3
        importance_weight: 0.1

  L2:
    available: [default, entropy_minimization, information_bottleneck, mutual_information]
    default: entropy_minimization
    params:
      entropy_minimization:
        target_entropy: 0.5
        max_iterations: 100
        convergence_threshold: 0.001
      information_bottleneck:
        beta: 1.0
        max_iterations: 50
        context_budget: 4096

  L3:
    available: [hybrid_default, weighted_combination]
    default: hybrid_default
    params:
      hybrid_default:
        l1_weight: 0.5
        l2_weight: 0.5
        exploration_rate: 0.1

# === Monitoring Configuration ===
monitoring:
  # Metrics to track
  metrics:
    - name: level_distribution
      type: histogram
      description: Distribution of level selections

    - name: quality_by_level
      type: gauge
      description: Average quality score per level

    - name: decision_confidence
      type: histogram
      description: Distribution of decision confidence scores

    - name: reward_distribution
      type: histogram
      description: Distribution of calculated rewards

  # Alerting thresholds
  alerts:
    low_quality_threshold: 0.3      # Alert if avg quality drops below
    high_error_rate_threshold: 0.15 # Alert if error rate exceeds
    low_confidence_threshold: 0.5   # Alert if avg confidence drops below

  # Dashboard update frequency
  dashboard_refresh_seconds: 60

# === Logging Configuration ===
logging:
  enabled: true
  level: INFO

  # Log file paths
  decision_log: "eval/math_policy_logs/decisions_v2.jsonl"
  outcome_log: "eval/math_policy_logs/outcomes_v2.jsonl"
  metrics_log: "eval/math_policy_logs/metrics_v2.jsonl"

  # What to include
  include_features: true
  include_scores: true
  include_explanation: true

  # Retention
  retention_days: 90
  max_file_size_mb: 100

# === Telemetry Configuration ===
telemetry:
  span_name: "math_layer_decision_v2"
  attributes:
    service: "rae-memory"
    component: "math_layer_controller"
    policy_version: "2.0"
  detailed_metrics: true
```

---

## 7. Example Scenarios

### Scenario 1: Small Memory, Simple Query

**Context**:
- task_type: MEMORY_RETRIEVE
- memory_count: 25
- session_length: 2
- recent_mrr: 0.7
- memory_entropy: 0.3

**Level Scores**:
- L1: 0.3 + 0.2*(1-0.025) + 0.2*(1-0.075) + 0.3*0.7 = 0.83
- L2: 0.0 + 0.25*0.075 + 0.20*0.025 + 0.25*0.5 + 0.15*0.3 = 0.21 (penalized for small memory)
- L3: -0.2 + ... = -0.15 (strongly penalized)

**Decision**: L1 (relevance_scoring)
**Confidence**: 0.85
**Explanation**: "Selected L1 (Rule-based scoring) | Small memory (25) works well with fast heuristics | Good recent quality (MRR=0.7) confirms L1 is sufficient"

### Scenario 2: Large Memory, High Entropy, Poor Quality

**Context**:
- task_type: CONTEXT_SELECT
- memory_count: 500
- session_length: 15
- recent_mrr: 0.25
- memory_entropy: 1.2

**Level Scores**:
- L1: 0.3 + 0.2*(1-0.5) + 0.2*(1-0.3) + 0.3*0.5 = 0.59
- L2: 0.0 + 0.25*0.3 + 0.20*0.5 + 0.25*0.9 + 0.15*0.75 + 0.05*0.3 = 0.56
- L2 (with rules): 0.56 + 0.25 (high entropy) + 0.2 (quality crisis) = 1.01
- L3: -0.2 + 0.20*0.5 + 0.15*0.3 + 0.25*0.6 + 0.20 + 0.15 = 0.55

**Decision**: L2 (entropy_minimization)
**Confidence**: 0.72
**Explanation**: "Selected L2 (Information-theoretic) | High entropy (1.2) suggests disorganized memory | Poor recent quality (MRR=0.25) triggered quality_crisis_upgrade rule | Context selection task benefits from information-theoretic optimization"

### Scenario 3: Deep Reflection, Long Session, Complex State

**Context**:
- task_type: REFLECTION_DEEP
- memory_count: 800
- session_length: 35
- recent_mrr: 0.45
- memory_entropy: 0.9
- previous_level: L2
- previous_level_success: True

**Level Scores**:
- L1: 0.3 + 0.2*0.2 + 0.2*0.775 + 0.3*0.2 = 0.46
- L2: 0.0 + 0.25*0.225 + 0.20*0.8 + 0.25*0.7 + 0.15*0.55 + 0.10 = 0.60
- L3: -0.2 + 0.20*0.8 + 0.15*0.225 + 0.25*0.9 + 0.15 = 0.51
- L3 (with rules): 0.51 + 0.2 (deep reflection rule) = 0.71

**Decision**: L3 (hybrid_default)
**Confidence**: 0.68
**Explanation**: "Selected L3 (Adaptive hybrid) | Deep reflection task benefits from meta-learning (rule: deep_reflection_needs_sophistication) | Large memory (800) and long session (35) justify sophisticated approach | Previous L2 success provides baseline for adaptive optimization"

### Scenario 4: Production Mode, Budget Constraint

**Context**:
- task_type: MEMORY_CONSOLIDATE
- memory_count: 300
- session_length: 20
- recent_mrr: 0.5
- cost_budget: 0.005 (constrained)
- profile: production

**Decision**: L1 (importance_scoring)
**Confidence**: 0.95
**Explanation**: "Selected L1 (Rule-based scoring) | OVERRIDE: Budget constraint ($0.005 remaining) forces lowest-cost approach | Production profile restricts L3"

### Scenario 5: Error Recovery Mode

**Context**:
- task_type: MEMORY_RETRIEVE
- memory_count: 150
- session_length: 8
- recent_mrr: 0.15
- error_rate_recent: 0.15
- consecutive_errors: 2

**Level Scores**: (After safety overrides)
- L1: 0.65
- L2: 0.40 * 0.3 = 0.12 (penalized by safety)
- L3: -999.0 (blocked by safety)

**Decision**: L1 (relevance_scoring)
**Confidence**: 0.80
**Explanation**: "Selected L1 (Rule-based scoring) | Safety override: High recent error rate (15%) penalizes L2 | L3 blocked due to error recovery mode | Reverting to stable baseline for reliability"

---

## 8. Monitoring and Adaptation

### 8.1 Metrics to Track

```python
class PolicyMonitor:
    """Monitors policy performance for evaluation and adaptation"""

    def __init__(self, config: MonitoringConfig):
        self.metrics = {
            # Level selection metrics
            "level_distribution": Counter(),           # How often each level is selected
            "level_by_task_type": defaultdict(Counter), # Level distribution per task

            # Quality metrics
            "quality_by_level": defaultdict(list),     # Quality scores per level
            "mrr_by_level": defaultdict(list),         # MRR per level

            # Confidence metrics
            "confidence_distribution": [],              # Decision confidence scores
            "confidence_vs_outcome": [],               # Confidence correlation with success

            # Reward metrics
            "reward_by_level": defaultdict(list),      # Rewards per level
            "cumulative_reward": 0.0,                  # Total reward

            # Error metrics
            "error_rate_by_level": defaultdict(list),  # Errors per level
            "budget_violations": 0,                     # Number of budget violations

            # Stability metrics
            "level_transitions": [],                    # Level change patterns
            "churn_rate": 0.0,                         # Frequency of level changes
        }

    def compute_summary(self) -> Dict[str, Any]:
        """Compute summary statistics"""
        return {
            "avg_quality_l1": np.mean(self.metrics["quality_by_level"][MathLevel.L1]),
            "avg_quality_l2": np.mean(self.metrics["quality_by_level"][MathLevel.L2]),
            "avg_quality_l3": np.mean(self.metrics["quality_by_level"][MathLevel.L3]),
            "avg_reward": np.mean(self.metrics["reward_by_level"][MathLevel.L1] +
                                  self.metrics["reward_by_level"][MathLevel.L2] +
                                  self.metrics["reward_by_level"][MathLevel.L3]),
            "l1_selection_rate": self.metrics["level_distribution"][MathLevel.L1] /
                                 sum(self.metrics["level_distribution"].values()),
            "avg_confidence": np.mean(self.metrics["confidence_distribution"]),
            "churn_rate": self.metrics["churn_rate"],
        }
```

### 8.2 Anomaly Detection

```python
class PolicyAnomalyDetector:
    """Detects when policy is failing and needs intervention"""

    def __init__(self, config: AnomalyConfig):
        self.config = config
        self.quality_history = deque(maxlen=100)
        self.error_history = deque(maxlen=100)
        self.confidence_history = deque(maxlen=100)

    def check_anomalies(self) -> List[Anomaly]:
        """Check for policy anomalies"""
        anomalies = []

        # Anomaly 1: Quality degradation
        if len(self.quality_history) >= 20:
            recent_quality = list(self.quality_history)[-20:]
            if np.mean(recent_quality) < self.config.low_quality_threshold:
                anomalies.append(Anomaly(
                    type="quality_degradation",
                    severity="high",
                    message=f"Average quality dropped to {np.mean(recent_quality):.2f}",
                    recommended_action="Consider forcing L2 for recovery",
                ))

        # Anomaly 2: High error rate
        if len(self.error_history) >= 50:
            error_rate = sum(self.error_history) / len(self.error_history)
            if error_rate > self.config.high_error_rate_threshold:
                anomalies.append(Anomaly(
                    type="high_error_rate",
                    severity="critical",
                    message=f"Error rate at {error_rate:.1%}",
                    recommended_action="Force L1 and investigate",
                ))

        # Anomaly 3: Confidence collapse
        if len(self.confidence_history) >= 20:
            recent_confidence = list(self.confidence_history)[-20:]
            if np.mean(recent_confidence) < self.config.low_confidence_threshold:
                anomalies.append(Anomaly(
                    type="confidence_collapse",
                    severity="medium",
                    message=f"Decision confidence dropped to {np.mean(recent_confidence):.2f}",
                    recommended_action="Review feature extraction and thresholds",
                ))

        # Anomaly 4: Level oscillation
        if self._detect_oscillation():
            anomalies.append(Anomaly(
                type="level_oscillation",
                severity="medium",
                message="Frequent switching between levels detected",
                recommended_action="Increase stability_bonus or min_score_advantage",
            ))

        return anomalies

    def _detect_oscillation(self) -> bool:
        """Detect if policy is oscillating between levels"""
        # Check last 10 decisions for oscillation pattern
        recent_levels = list(self.level_history)[-10:]
        if len(recent_levels) < 10:
            return False

        transitions = sum(1 for i in range(1, len(recent_levels))
                         if recent_levels[i] != recent_levels[i-1])
        return transitions >= 6  # 6+ transitions in 10 decisions = oscillation
```

### 8.3 Rollback Strategy

```python
class PolicyRollback:
    """Handles rollback to safe defaults when policy fails"""

    def __init__(self, config: RollbackConfig):
        self.config = config
        self.baseline_policy = BaselinePolicyV1()  # Iteration 1 policy
        self.rollback_active = False
        self.rollback_reason = None
        self.observations_since_rollback = 0

    def check_rollback_needed(self, monitor: PolicyMonitor) -> bool:
        """Check if rollback to baseline is needed"""

        if not self.config.enabled:
            return False

        summary = monitor.compute_summary()

        # Condition 1: Severe quality drop
        if summary["avg_quality_l2"] < summary["avg_quality_l1"] * 0.7:
            self.rollback_reason = "L2 quality significantly worse than L1"
            return True

        # Condition 2: L3 causing problems
        if (summary["avg_quality_l3"] < self.config.quality_drop_threshold and
            monitor.metrics["level_distribution"][MathLevel.L3] > 0):
            self.rollback_reason = "L3 causing quality degradation"
            return True

        # Condition 3: Overall policy worse than baseline
        if summary["avg_reward"] < -0.5:  # Consistently negative reward
            self.rollback_reason = "Policy consistently underperforming"
            return True

        return False

    def execute_rollback(self):
        """Execute rollback to baseline policy"""
        self.rollback_active = True
        self.observations_since_rollback = 0

        logger.warning(
            "policy_rollback_executed",
            reason=self.rollback_reason,
            action="Reverting to Policy V1 (baseline)",
        )

    def should_exit_rollback(self, recent_quality: float) -> bool:
        """Check if safe to exit rollback mode"""
        self.observations_since_rollback += 1

        if self.observations_since_rollback < self.config.min_observations:
            return False

        if recent_quality > 0.6:  # Quality recovered
            logger.info(
                "policy_rollback_exit",
                observations=self.observations_since_rollback,
                quality=recent_quality,
            )
            self.rollback_active = False
            return True

        return False
```

---

## 9. Evaluation Metrics for Policy Performance

### 9.1 Primary Metrics

| Metric | Description | Target | How to Compute |
|--------|-------------|--------|----------------|
| Policy Quality Score | Weighted quality across all decisions | > 0.6 | `mean(quality_scores)` |
| Cost Efficiency | Quality per unit cost | > 0.3 | `quality / (cost_multiplier * base_cost)` |
| Decision Stability | Low churn rate | < 0.2 | `transitions / (n_decisions - 1)` |
| Confidence Accuracy | Confidence correlates with outcome | r > 0.5 | `correlation(confidence, success)` |

### 9.2 Level-Specific Metrics

| Metric | L1 Target | L2 Target | L3 Target |
|--------|-----------|-----------|-----------|
| Selection Rate | 60-80% | 15-35% | 0-10% |
| Avg Quality | > 0.5 | > 0.65 | > 0.75 |
| Avg Latency | < 20ms | < 50ms | < 150ms |
| Error Rate | < 5% | < 8% | < 12% |

### 9.3 Comparative Evaluation

```python
def evaluate_policy_v2(
    decisions_v1: List[DecisionWithOutcome],
    decisions_v2: List[DecisionWithOutcome],
) -> PolicyComparison:
    """Compare Policy V2 against V1 baseline"""

    return PolicyComparison(
        # Quality improvement
        quality_lift=np.mean([d.outcome.quality for d in decisions_v2]) -
                     np.mean([d.outcome.quality for d in decisions_v1]),

        # Cost change
        cost_delta=np.mean([d.decision.cost for d in decisions_v2]) -
                   np.mean([d.decision.cost for d in decisions_v1]),

        # Stability comparison
        churn_reduction=compute_churn(decisions_v1) - compute_churn(decisions_v2),

        # Statistical significance
        quality_p_value=ttest_ind(
            [d.outcome.quality for d in decisions_v1],
            [d.outcome.quality for d in decisions_v2],
        ).pvalue,

        # Per-level breakdown
        level_analysis={
            MathLevel.L1: analyze_level_performance(decisions_v2, MathLevel.L1),
            MathLevel.L2: analyze_level_performance(decisions_v2, MathLevel.L2),
            MathLevel.L3: analyze_level_performance(decisions_v2, MathLevel.L3),
        },
    )
```

---

## 10. Migration Path

### 10.1 Implementation Phases

**Phase 1: Feature Extension** (Week 1)
- Extend `Features` dataclass with new fields
- Implement derived feature computation
- Add feature logging

**Phase 2: Scoring System** (Week 2)
- Implement `compute_level_scores()`
- Add task affinity functions
- Implement policy rules

**Phase 3: Reward Function** (Week 3)
- Implement complete reward calculation
- Add catastrophic penalty detection
- Connect to outcome recording

**Phase 4: Monitoring** (Week 4)
- Implement `PolicyMonitor`
- Add anomaly detection
- Implement rollback logic

**Phase 5: Testing & Tuning** (Week 5)
- Run ablation studies
- Tune weights via benchmarks
- Document results

### 10.2 Backward Compatibility

Policy V2 maintains backward compatibility with V1:

```python
class MathLayerController:
    def __init__(self, config_path: str = None, policy_version: str = "v2"):
        if policy_version == "v1":
            self.policy = PolicyV1(config)  # Original behavior
        elif policy_version == "v2":
            self.policy = PolicyV2(config)  # New behavior
        else:
            raise ValueError(f"Unknown policy version: {policy_version}")
```

### 10.3 Configuration Migration

```yaml
# To migrate from v1 to v2, add these to your config:
version: "2.0"  # Required for v2

# All v1 settings continue to work
# These new sections are optional with sensible defaults:
reward: ...
features: ...
level_selection: ...
monitoring: ...
```

---

## 11. Open Questions for Iteration 3

1. **Should we use learned feature weights?**
   - Current: Hand-tuned weights
   - Future: Learn weights from outcome data via gradient descent

2. **Multi-armed bandit for strategy selection?**
   - Current: Rule-based strategy selection within level
   - Future: UCB or Thompson Sampling for strategy exploration

3. **Online reward adaptation?**
   - Current: Fixed reward function
   - Future: Adjust component weights based on observed correlations

4. **Hierarchical policy?**
   - Current: Single-level decision
   - Future: Separate policies for level selection vs strategy selection

---

## 12. Appendix: Mathematical Notation

| Symbol | Meaning |
|--------|---------|
| L | Math Level (L1, L2, L3) |
| R | Reward |
| Q | Quality component |
| C | Cost component |
| S | Stability penalty |
| P | Catastrophic penalty |
| w_x | Weight for component x |
| f | Feature vector |
| theta | Policy parameters |
| pi(L|f) | Policy: probability of level L given features f |

---

*Document prepared for Iteration 2 of Math Layer Controller development.*
*For implementation, refer to: `/benchmarking/math_metrics/controller/`*
