# Multi-Armed Bandit System for Math Layer Controller

## Iteration 3: Online Adaptive Learning Design Document

**Document Type**: Architectural Design
**Target**: MathLayerController Iteration 3
**Status**: Approved Design
**Date**: 2025-12-07
**Author**: AI Architect (Claude Opus 4.5)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Bandit Algorithm Design](#2-bandit-algorithm-design)
3. [Arms Definition](#3-arms-definition)
4. [Integration Architecture](#4-integration-architecture)
5. [Safety System](#5-safety-system)
6. [Learning Mechanism](#6-learning-mechanism)
7. [Configuration Schema](#7-configuration-schema)
8. [Monitoring and Telemetry](#8-monitoring-and-telemetry)
9. [Implementation Plan](#9-implementation-plan)
10. [Evaluation Strategy](#10-evaluation-strategy)
11. [Production Rollout](#11-production-rollout)

---

## 1. Executive Summary

### 1.1 Motivation

The Math Layer Controller currently operates with:
- **Policy v1**: Rule-based level selection (production-safe, deterministic)
- **Policy v2**: Weighted scoring with a fixed reward function (research mode)

While Policy v2 provides data-driven decisions, it has limitations:
1. **Static weights** - cannot adapt to changing workload characteristics
2. **No exploration** - always exploits current best guess, may miss better configurations
3. **Slow improvement** - requires manual weight tuning via offline analysis

**Problem Statement**: How do we enable the controller to learn and improve *during operation* while maintaining production safety guarantees?

### 1.2 Solution: Multi-Armed Bandits

Multi-Armed Bandits (MAB) provide the ideal solution because:

| Property | Why It Matters |
|----------|----------------|
| **Simplicity** | Simpler than full RL; no state transition modeling needed |
| **Theoretical guarantees** | Provable regret bounds (UCB, Thompson Sampling) |
| **Online learning** | Learns from each decision immediately |
| **Exploration-exploitation** | Balances trying new things vs using what works |
| **Safety-compatible** | Easy to add hard constraints and rollback logic |

### 1.3 Goals

1. **Learn from real decisions** - Update arm estimates after every outcome
2. **Explore safely** - Try new configurations with bounded risk
3. **Exploit effectively** - Use best-known configuration most of the time
4. **Never break production** - Hard constraints always respected

### 1.4 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Algorithm | **UCB1 with Contextual Features** | Best balance of simplicity and theoretical guarantees |
| Arm Structure | **Level + Strategy pairs** | 9 arms total (manageable, meaningful) |
| Context | **FeaturesV2 subset** | Use 6 most predictive features |
| Exploration Budget | **10% research, 0% production** | Safety-first approach |
| Update Frequency | **Every decision** | Maximize learning speed |
| Persistence | **JSON file** | Simple, inspectable, version-controllable |

### 1.5 Expected Outcomes

After implementation:
- **5-15% improvement** over Policy v2 baseline (after 200+ decisions)
- **< 5% exploration cost** (suboptimal decisions during learning)
- **Convergence in 100-500 decisions** depending on context
- **Zero production incidents** due to safety guardrails

---

## 2. Bandit Algorithm Design

### 2.1 Algorithm Selection: UCB1 with Contextual Enhancements

**Why not ε-greedy?**
- Fixed exploration rate (ε) doesn't adapt
- No consideration of uncertainty
- Explores low-reward arms as much as high-reward ones

**Why not pure Thompson Sampling?**
- More complex to implement correctly
- Requires maintaining full distributions
- Harder to add hard constraints

**Why UCB1?**
- **Optimism in the face of uncertainty** - explores undersampled arms naturally
- **Theoretical regret bound** - O(√(T ln T)) where T is time horizon
- **Simple to implement** - just mean + confidence bonus
- **Easy to constrain** - can multiply bonus by safety coefficient

### 2.2 UCB1 Formula

For each arm `a`, compute the UCB score:

```
UCB(a) = μ(a) + c * √(ln(N) / n(a))
```

Where:
- `μ(a)` = estimated mean reward for arm `a`
- `N` = total number of pulls across all arms
- `n(a)` = number of times arm `a` has been pulled
- `c` = exploration coefficient (default 1.0, tunable)

The arm with the highest UCB score is selected.

### 2.3 Contextual Enhancement

Pure UCB1 ignores context (features). We add a **contextual bonus** that adjusts UCB scores based on how well an arm performs in similar contexts:

```
UCB_contextual(a, x) = μ(a) + c * √(ln(N) / n(a)) + w * similarity_bonus(a, x)
```

Where:
- `x` = current feature vector (from FeaturesV2)
- `similarity_bonus(a, x)` = weighted average reward in similar contexts
- `w` = contextual weight (default 0.2)

**Context Features Used** (6 features from FeaturesV2):

| Feature | Why Selected | Normalization |
|---------|--------------|---------------|
| `memory_scale` | Primary predictor of level need | Already [0, 1] |
| `entropy_normalized` | Indicates memory organization | Already [0, 1] |
| `task_type_code` | Different tasks need different levels | One-hot → categorical |
| `session_scale` | Session length affects complexity | Already [0, 1] |
| `recent_mrr` | Current quality influences level choice | Already [0, 1] |
| `quality_declining` | Trigger for trying different levels | Boolean → [0, 1] |

### 2.4 Mathematical Formulation

**State**: Context vector `x ∈ R^d` (d=6 features)
**Actions**: Arms `A = {(L1, default), (L1, relevance), ..., (L3, hybrid)}` (9 arms)
**Reward**: `R ∈ [-10, 1]` from existing reward function

**Update Rule** (after observing reward r for arm a in context x):

```python
# Update arm statistics
n[a] += 1
mu[a] = mu[a] + (r - mu[a]) / n[a]  # Incremental mean

# Update context-specific statistics
context_bucket = discretize(x)
n_context[a][context_bucket] += 1
mu_context[a][context_bucket] += (r - mu_context[a][context_bucket]) / n_context[a][context_bucket]
```

### 2.5 Context Discretization

To enable efficient context-based learning without explosion of state space:

```python
def discretize_context(features: FeaturesV2) -> str:
    """
    Discretize continuous context into buckets for tracking.

    Returns a string key like "memory:high_entropy:low_task:retrieve_mrr:good"
    """
    buckets = []

    # Memory scale: low (<0.1), medium (0.1-0.5), high (>0.5)
    memory_scale = features.compute_derived_features()["memory_scale"]
    if memory_scale < 0.1:
        buckets.append("mem:low")
    elif memory_scale < 0.5:
        buckets.append("mem:med")
    else:
        buckets.append("mem:high")

    # Entropy: low (<0.3), medium (0.3-0.7), high (>0.7)
    entropy = features.compute_derived_features()["entropy_normalized"]
    if entropy < 0.3:
        buckets.append("ent:low")
    elif entropy < 0.7:
        buckets.append("ent:med")
    else:
        buckets.append("ent:high")

    # Task type: simplified to 3 categories
    task = features.task_type
    if task in [TaskType.MEMORY_STORE, TaskType.MEMORY_RETRIEVE]:
        buckets.append("task:simple")
    elif task in [TaskType.CONTEXT_SELECT, TaskType.REFLECTION_LIGHT]:
        buckets.append("task:medium")
    else:
        buckets.append("task:complex")

    # Quality: poor (<0.3), ok (0.3-0.7), good (>0.7)
    if features.recent_mrr < 0.3:
        buckets.append("mrr:poor")
    elif features.recent_mrr < 0.7:
        buckets.append("mrr:ok")
    else:
        buckets.append("mrr:good")

    return "_".join(buckets)
```

This gives us 3^4 = 81 context buckets, manageable yet informative.

---

## 3. Arms Definition

### 3.1 What Constitutes an Arm?

An **arm** represents a specific configuration choice the bandit can make:

```
Arm = (MathLevel, Strategy)
```

We deliberately exclude parameters from the arm definition to keep the action space manageable. Parameters are still configured by the existing logic in `configure_params()`.

### 3.2 Complete Arm Set

| Arm ID | Level | Strategy | Description |
|--------|-------|----------|-------------|
| `L1_default` | L1 | default | Basic L1 with default params |
| `L1_relevance` | L1 | relevance_scoring | L1 with semantic+recency scoring |
| `L1_importance` | L1 | importance_scoring | L1 with importance-based ranking |
| `L2_default` | L2 | default | Basic L2 |
| `L2_entropy` | L2 | entropy_minimization | L2 optimizing for low entropy |
| `L2_bottleneck` | L2 | information_bottleneck | L2 using IB compression |
| `L2_mutual` | L2 | mutual_information | L2 using MI estimation |
| `L3_default` | L3 | hybrid_default | L3 with equal L1/L2 weights |
| `L3_weighted` | L3 | weighted_combination | L3 with learned weights |

**Total: 9 arms** - small enough to learn quickly, large enough to cover meaningful choices.

### 3.3 Arm Encoding

```python
@dataclass
class Arm:
    """Represents a single arm in the bandit"""

    arm_id: str                  # e.g., "L1_relevance"
    level: MathLevel             # L1, L2, or L3
    strategy: str                # Strategy within level

    # Statistics (updated online)
    n_pulls: int = 0             # Number of times selected
    total_reward: float = 0.0    # Sum of rewards received
    mean_reward: float = 0.0     # Running mean reward

    # Context-specific statistics
    context_stats: Dict[str, ArmContextStats] = field(default_factory=dict)

    # Safety metadata
    enabled: bool = True         # Can be disabled by safety system
    min_pulls_required: int = 5  # Minimum observations before trusted

    @property
    def ucb_bonus(self) -> float:
        """UCB exploration bonus for this arm"""
        if self.n_pulls == 0:
            return float('inf')  # Unpulled arms have infinite bonus
        return math.sqrt(math.log(total_pulls) / self.n_pulls)

    def update(self, reward: float, context_key: str) -> None:
        """Update arm statistics after observing reward"""
        self.n_pulls += 1
        self.total_reward += reward
        self.mean_reward = self.total_reward / self.n_pulls

        # Update context-specific stats
        if context_key not in self.context_stats:
            self.context_stats[context_key] = ArmContextStats()
        self.context_stats[context_key].update(reward)


@dataclass
class ArmContextStats:
    """Statistics for an arm in a specific context"""
    n_pulls: int = 0
    total_reward: float = 0.0
    mean_reward: float = 0.0

    def update(self, reward: float) -> None:
        self.n_pulls += 1
        self.total_reward += reward
        self.mean_reward = self.total_reward / self.n_pulls
```

### 3.4 Arm Eligibility

Not all arms are always eligible. Arm eligibility is determined by:

```python
def get_eligible_arms(
    arms: List[Arm],
    features: FeaturesV2,
    config: BanditConfig,
) -> List[Arm]:
    """
    Filter arms to only those eligible in current context.

    Eligibility is determined by:
    1. Arm is enabled (not banned)
    2. Level is allowed in current profile
    3. Level meets minimum requirements (memory count, session length)
    """
    eligible = []

    for arm in arms:
        # Check if arm is enabled
        if not arm.enabled:
            continue

        # Check if level is allowed in profile
        if arm.level not in config.allowed_levels:
            continue

        # Check level-specific requirements
        if arm.level == MathLevel.L2:
            if features.memory_count < config.l2_memory_threshold:
                continue

        if arm.level == MathLevel.L3:
            if features.memory_count < config.l3_memory_threshold:
                continue
            if features.session_length < config.l3_session_threshold:
                continue

        eligible.append(arm)

    return eligible
```

---

## 4. Integration Architecture

### 4.1 System Overview

```
                      ┌─────────────────────────────────────────────────┐
                      │            MathLayerController                   │
                      │                                                  │
User Request ────────▶│  ┌──────────┐    ┌──────────────┐               │
                      │  │ Features │───▶│  Policy v2   │               │
                      │  │ Extractor│    │  (baseline)  │               │
                      │  └──────────┘    └──────┬───────┘               │
                      │                         │                        │
                      │                         ▼                        │
                      │                  ┌─────────────┐                 │
                      │                  │   Bandit    │                 │
                      │                  │  Selector   │                 │
                      │                  └──────┬──────┘                 │
                      │                         │                        │
                      │            ┌────────────┴────────────┐          │
                      │            │                         │          │
                      │            ▼                         ▼          │
                      │       Exploit?              Explore?            │
                      │       (90%)                 (10%)               │
                      │            │                         │          │
                      │            ▼                         ▼          │
                      │     Use Policy v2           Select via UCB      │
                      │     recommendation                              │
                      │            │                         │          │
                      │            └──────────┬──────────────┘          │
                      │                       │                          │
                      │                       ▼                          │
                      │                ┌─────────────┐                   │
                      │                │   Safety    │                   │
                      │                │  Override   │                   │
                      │                └──────┬──────┘                   │
                      │                       │                          │
                      └───────────────────────┼──────────────────────────┘
                                              │
                                              ▼
                                       Final Decision
                                              │
                                              ▼
                                       Execute & Record
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │ Reward Feedback │─────▶ Update Bandit
                                    └─────────────────┘
```

### 4.2 Decision Flow Pseudocode

```python
class MathLayerController:
    """Extended controller with bandit integration"""

    def __init__(self, config_path: str = None, ...):
        # ... existing initialization ...

        # Initialize bandit (Iteration 3)
        if self.config.bandit.enabled:
            self.bandit = MultiArmedBandit(self.config.bandit)
            self.bandit_monitor = BanditMonitor(self.config.bandit.safety)
        else:
            self.bandit = None

    def decide(self, context: TaskContext) -> MathDecision:
        """
        Make a decision about which math level to use.

        Iteration 3: Integrates bandit for online learning.
        """
        # Step 1: Extract features
        features = self.feature_extractor.extract(context)
        features_v2 = self._upgrade_to_v2(features)

        # Step 2: Get Policy v2 baseline recommendation
        baseline_level = self.policy_v2.select_level(features_v2)
        baseline_strategy = self.select_strategy(baseline_level, features_v2)
        baseline_arm_id = f"{baseline_level.value}_{baseline_strategy}"

        # Step 3: Bandit decision (if enabled and allowed)
        if self._should_use_bandit(features_v2):
            selected_arm_id = self.bandit.select_arm(
                features=features_v2,
                baseline_arm_id=baseline_arm_id,
            )
        else:
            selected_arm_id = baseline_arm_id

        # Step 4: Parse arm back to level + strategy
        level, strategy = self._parse_arm_id(selected_arm_id)

        # Step 5: Safety override check
        level, strategy = self._apply_safety_override(
            level, strategy, features_v2
        )

        # Step 6: Build and return decision
        # ... existing decision building logic ...

        # Record the arm used for later reward update
        decision.bandit_arm_id = selected_arm_id
        decision.was_exploration = (selected_arm_id != baseline_arm_id)

        return decision

    def _should_use_bandit(self, features: FeaturesV2) -> bool:
        """Determine if bandit should be consulted"""
        if not self.bandit:
            return False

        if not self.config.bandit.enabled:
            return False

        # Check profile restrictions
        profile = self.config.profile
        if profile == "production" and self.config.bandit.production_mode == "exploit_only":
            # In production, bandit is used but never explores
            return True

        if profile == "cheap":
            # Cheap mode: no bandit overhead
            return False

        return True

    def record_outcome(
        self,
        decision_id: str,
        success: bool,
        metrics: Dict[str, float],
    ) -> Optional[DecisionWithOutcome]:
        """
        Record the outcome of a decision.

        Iteration 3: Also updates bandit with reward.
        """
        # ... existing outcome recording ...

        # Update bandit if applicable
        if self.bandit and hasattr(decision, 'bandit_arm_id'):
            reward = self.reward_calculator.calculate(outcome)
            self.bandit.update(
                arm_id=decision.bandit_arm_id,
                reward=reward,
                features=decision.features_used,
            )

            # Check for degradation
            if self.bandit_monitor.check_degradation(reward):
                logger.warning(
                    "bandit_degradation_detected",
                    avg_reward=self.bandit_monitor.rolling_avg_reward,
                )
                self._handle_degradation()

        return outcome
```

### 4.3 Bandit Selection Logic

```python
class MultiArmedBandit:
    """UCB1-based Multi-Armed Bandit for level/strategy selection"""

    def __init__(self, config: BanditConfig):
        self.config = config
        self.arms = self._initialize_arms()
        self.total_pulls = 0
        self.exploration_count = 0

        # Load persisted state if exists
        self._load_state()

    def select_arm(
        self,
        features: FeaturesV2,
        baseline_arm_id: str,
    ) -> str:
        """
        Select an arm using UCB with contextual bonus.

        Args:
            features: Current context features
            baseline_arm_id: Policy v2's recommendation

        Returns:
            Selected arm ID
        """
        # Get eligible arms for this context
        eligible = self.get_eligible_arms(features)

        if not eligible:
            logger.warning("no_eligible_arms", falling_back_to=baseline_arm_id)
            return baseline_arm_id

        # Decide: explore or exploit?
        if self._should_explore():
            # Exploration: use UCB selection
            selected = self._ucb_select(eligible, features)
            self.exploration_count += 1
            logger.debug("bandit_exploration", arm=selected.arm_id)
        else:
            # Exploitation: use baseline or best known arm
            if self.config.exploit_strategy == "baseline":
                # Always use Policy v2's choice
                selected = self._get_arm(baseline_arm_id)
            else:
                # Use best arm from bandit's perspective
                selected = self._best_arm(eligible, features)
            logger.debug("bandit_exploitation", arm=selected.arm_id)

        self.total_pulls += 1
        return selected.arm_id

    def _should_explore(self) -> bool:
        """Determine if this decision should be exploration"""
        # Check exploration budget
        if self.config.max_exploration_rate <= 0:
            return False

        # Calculate current exploration rate
        if self.total_pulls == 0:
            current_rate = 0.0
        else:
            current_rate = self.exploration_count / self.total_pulls

        # Explore if under budget
        if current_rate < self.config.exploration_rate:
            # Random exploration decision
            return random.random() < self.config.exploration_rate

        return False

    def _ucb_select(
        self,
        eligible_arms: List[Arm],
        features: FeaturesV2,
    ) -> Arm:
        """Select arm using UCB1 with contextual bonus"""
        context_key = discretize_context(features)

        best_arm = None
        best_score = float('-inf')

        for arm in eligible_arms:
            # Base UCB score
            if arm.n_pulls == 0:
                ucb_score = float('inf')  # Must try untried arms first
            else:
                mean = arm.mean_reward
                bonus = self.config.ucb_confidence * math.sqrt(
                    math.log(self.total_pulls + 1) / arm.n_pulls
                )
                ucb_score = mean + bonus

            # Add contextual bonus
            if context_key in arm.context_stats:
                ctx_stats = arm.context_stats[context_key]
                if ctx_stats.n_pulls >= self.config.min_context_observations:
                    context_bonus = self.config.context_weight * ctx_stats.mean_reward
                    ucb_score += context_bonus

            if ucb_score > best_score:
                best_score = ucb_score
                best_arm = arm

        return best_arm

    def _best_arm(
        self,
        eligible_arms: List[Arm],
        features: FeaturesV2,
    ) -> Arm:
        """Select best arm based on mean reward (pure exploitation)"""
        context_key = discretize_context(features)

        # Prefer context-specific mean if available
        best_arm = None
        best_reward = float('-inf')

        for arm in eligible_arms:
            # Check context-specific stats first
            if context_key in arm.context_stats:
                ctx_stats = arm.context_stats[context_key]
                if ctx_stats.n_pulls >= self.config.min_context_observations:
                    reward = ctx_stats.mean_reward
                else:
                    reward = arm.mean_reward
            else:
                reward = arm.mean_reward

            if reward > best_reward:
                best_reward = reward
                best_arm = arm

        return best_arm

    def update(
        self,
        arm_id: str,
        reward: float,
        features: FeaturesV2,
    ) -> None:
        """Update arm statistics after observing reward"""
        arm = self._get_arm(arm_id)
        if not arm:
            logger.warning("unknown_arm_in_update", arm_id=arm_id)
            return

        context_key = discretize_context(features)
        arm.update(reward, context_key)

        # Persist state periodically
        if self.total_pulls % self.config.save_frequency == 0:
            self._save_state()

        logger.debug(
            "bandit_arm_updated",
            arm_id=arm_id,
            reward=reward,
            new_mean=arm.mean_reward,
            n_pulls=arm.n_pulls,
        )
```

### 4.4 Integration with Policy v2

The bandit operates "on top of" Policy v2 in the following sense:

1. **Policy v2 always runs** - provides a baseline recommendation
2. **Bandit decides whether to override** - based on exploration probability
3. **During exploration** - bandit's UCB selection may choose a different arm
4. **During exploitation** - bandit can either use Policy v2's choice or its own best estimate

This design ensures:
- **Baseline safety** - Policy v2's logic still applies when bandit is disabled
- **Gradual learning** - bandit learns which arm is best, including "follow Policy v2"
- **Easy rollback** - disable bandit → system reverts to Policy v2

---

## 5. Safety System

### 5.1 Design Principles

1. **Production cannot break** - no matter what the bandit learns
2. **Fail closed** - any uncertainty → fall back to safe defaults
3. **Observable** - always know what the bandit is doing
4. **Reversible** - can disable bandit instantly

### 5.2 Hard Constraints

Hard constraints are **never violated**, regardless of bandit decisions:

```python
@dataclass
class HardConstraints:
    """Constraints that override all bandit decisions"""

    # Budget constraints (from features)
    enforce_budget: bool = True      # If True, budget constraints force L1

    # Profile-based restrictions
    production_l3_allowed: bool = False   # L3 never in production
    cheap_mode_l1_only: bool = True       # Cheap mode forces L1

    # Banned arms (never explore these)
    banned_arms: List[str] = field(default_factory=list)

    def apply(
        self,
        selected_arm: Arm,
        features: FeaturesV2,
        profile: str,
    ) -> Arm:
        """
        Apply hard constraints, returning safe alternative if needed.
        """
        # Budget constraint
        if self.enforce_budget:
            if features.is_budget_constrained() or features.is_latency_constrained():
                return self._get_arm("L1_default")

        # Profile constraints
        if profile == "production":
            if selected_arm.level == MathLevel.L3:
                return self._get_arm("L2_entropy")  # Downgrade to L2

        if profile == "cheap":
            if selected_arm.level != MathLevel.L1:
                return self._get_arm("L1_default")

        # Banned arms
        if selected_arm.arm_id in self.banned_arms:
            return self._get_safe_alternative(selected_arm)

        return selected_arm
```

### 5.3 Exploration Rate Limits

```python
@dataclass
class ExplorationLimits:
    """Limits on exploration by profile"""

    # Maximum exploration rate by profile
    max_rates: Dict[str, float] = field(default_factory=lambda: {
        "research": 0.20,      # 20% exploration in research
        "lab": 0.10,           # 10% in lab
        "production": 0.00,    # 0% in production (exploit only)
        "cheap": 0.00,         # 0% in cheap mode
    })

    # Exploration budget tracking
    exploration_budget: int = 100     # Max explorations before reset
    budget_window_hours: int = 24     # Reset budget every 24h

    def get_max_rate(self, profile: str) -> float:
        return self.max_rates.get(profile, 0.0)

    def is_budget_exhausted(self, stats: BanditStats) -> bool:
        """Check if exploration budget is exhausted"""
        recent_explorations = stats.get_explorations_in_window(
            hours=self.budget_window_hours
        )
        return recent_explorations >= self.exploration_budget
```

### 5.4 Degradation Detection

The system continuously monitors for degradation:

```python
class DegradationDetector:
    """Detects when bandit is causing quality degradation"""

    def __init__(self, config: SafetyConfig):
        self.config = config
        self.reward_history = deque(maxlen=config.window_size)
        self.baseline_reward = None
        self.degradation_count = 0

    def update(self, reward: float, was_exploration: bool) -> None:
        """Update with new reward observation"""
        self.reward_history.append((reward, was_exploration))

    def check_degradation(self) -> Optional[DegradationAlert]:
        """
        Check for degradation based on rolling average.

        Returns alert if degradation detected, None otherwise.
        """
        if len(self.reward_history) < self.config.min_observations:
            return None

        # Calculate rolling average
        rewards = [r for r, _ in self.reward_history]
        rolling_avg = sum(rewards) / len(rewards)

        # Compare to baseline
        if self.baseline_reward is None:
            # Establish baseline from first window
            self.baseline_reward = rolling_avg
            return None

        # Check for degradation
        delta = rolling_avg - self.baseline_reward
        if delta < self.config.rollback_threshold:
            self.degradation_count += 1

            if self.degradation_count >= self.config.consecutive_alerts_for_rollback:
                return DegradationAlert(
                    type="rollback_triggered",
                    rolling_avg=rolling_avg,
                    baseline=self.baseline_reward,
                    delta=delta,
                    recommendation="Disable exploration, revert to Policy v2",
                )
            else:
                return DegradationAlert(
                    type="warning",
                    rolling_avg=rolling_avg,
                    baseline=self.baseline_reward,
                    delta=delta,
                    recommendation="Monitor closely, reduce exploration rate",
                )
        else:
            # Reset degradation counter on recovery
            self.degradation_count = 0
            # Update baseline if improving
            if delta > 0.1:
                self.baseline_reward = (self.baseline_reward + rolling_avg) / 2
            return None
```

### 5.5 Automatic Rollback

```python
class RollbackManager:
    """Manages automatic rollback to safe defaults"""

    def __init__(self, config: SafetyConfig):
        self.config = config
        self.rollback_active = False
        self.rollback_timestamp = None
        self.observations_since_rollback = 0

    def trigger_rollback(self, reason: str) -> None:
        """Trigger rollback to Policy v2"""
        self.rollback_active = True
        self.rollback_timestamp = datetime.utcnow()
        self.observations_since_rollback = 0

        logger.warning(
            "bandit_rollback_triggered",
            reason=reason,
            action="Bandit exploration disabled, using Policy v2 only",
        )

        # Emit alert for monitoring
        emit_alert(
            severity="high",
            title="Bandit Rollback Triggered",
            description=f"Reason: {reason}",
        )

    def should_exit_rollback(self, recent_rewards: List[float]) -> bool:
        """Check if safe to re-enable bandit"""
        if not self.rollback_active:
            return False

        self.observations_since_rollback += 1

        # Minimum cool-off period
        if self.observations_since_rollback < self.config.min_rollback_observations:
            return False

        # Check quality recovery
        if len(recent_rewards) >= 20:
            avg_reward = sum(recent_rewards[-20:]) / 20
            if avg_reward > self.config.recovery_threshold:
                logger.info(
                    "bandit_rollback_exit",
                    observations=self.observations_since_rollback,
                    avg_reward=avg_reward,
                )
                self.rollback_active = False
                return True

        return False
```

### 5.6 Profile-Based Safety Matrix

| Profile | Exploration | L2 Allowed | L3 Allowed | Auto-Rollback |
|---------|-------------|------------|------------|---------------|
| research | Up to 20% | Yes | Yes | Warning only |
| lab | Up to 10% | Yes | Limited | Enabled |
| production | 0% (exploit only) | Yes | No | Aggressive |
| cheap | 0% | L1 only | No | N/A |

---

## 6. Learning Mechanism

### 6.1 Reward Feedback Loop

The bandit learns from every decision outcome:

```
Decision Made → Operation Executed → Outcome Measured → Reward Calculated → Arm Updated
```

Timeline:
1. **t=0**: `decide()` called, arm selected
2. **t=1**: Memory operation executed using selected level/strategy
3. **t=2**: Operation completes, metrics collected
4. **t=3**: `record_outcome()` called with metrics
5. **t=4**: Reward calculated, arm statistics updated
6. **t=5**: State persisted (if save_frequency reached)

### 6.2 Update Rules

**Incremental Mean Update** (constant memory):

```python
def update_mean(current_mean: float, n: int, new_value: float) -> float:
    """
    Update running mean without storing all values.

    Formula: μ_new = μ_old + (x - μ_old) / n
    """
    return current_mean + (new_value - current_mean) / n
```

**Exponential Decay Option** (weights recent observations more):

```python
def update_mean_ema(current_mean: float, new_value: float, alpha: float = 0.1) -> float:
    """
    Exponential moving average update.

    alpha = 0.1 means new observation has 10% weight.
    """
    return alpha * new_value + (1 - alpha) * current_mean
```

The default is incremental mean, but EMA can be enabled for non-stationary environments:

```yaml
bandit:
  update_rule: "incremental"  # or "ema"
  ema_alpha: 0.1  # Only used if update_rule is "ema"
```

### 6.3 Weight Persistence

Arm statistics are persisted to enable learning across restarts:

```python
@dataclass
class BanditState:
    """Serializable state for persistence"""

    version: str = "1.0"
    last_updated: datetime = None
    total_pulls: int = 0
    exploration_count: int = 0

    arms: Dict[str, ArmState] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "total_pulls": self.total_pulls,
            "exploration_count": self.exploration_count,
            "arms": {
                arm_id: {
                    "n_pulls": state.n_pulls,
                    "total_reward": state.total_reward,
                    "mean_reward": state.mean_reward,
                    "context_stats": {
                        ctx: {
                            "n_pulls": cs.n_pulls,
                            "mean_reward": cs.mean_reward,
                        }
                        for ctx, cs in state.context_stats.items()
                    }
                }
                for arm_id, state in self.arms.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "BanditState":
        # ... deserialization logic ...
        pass


class BanditPersistence:
    """Handles saving and loading bandit state"""

    def __init__(self, config: BanditConfig):
        self.save_path = Path(config.persistence.save_path)
        self.save_frequency = config.persistence.save_frequency
        self.updates_since_save = 0

    def should_save(self) -> bool:
        self.updates_since_save += 1
        return self.updates_since_save >= self.save_frequency

    def save(self, state: BanditState) -> None:
        """Save state to JSON file"""
        self.save_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first for atomicity
        temp_path = self.save_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(state.to_dict(), f, indent=2)

        # Atomic rename
        temp_path.rename(self.save_path)
        self.updates_since_save = 0

        logger.info(
            "bandit_state_saved",
            path=str(self.save_path),
            total_pulls=state.total_pulls,
        )

    def load(self) -> Optional[BanditState]:
        """Load state from JSON file"""
        if not self.save_path.exists():
            return None

        with open(self.save_path, 'r') as f:
            data = json.load(f)

        state = BanditState.from_dict(data)
        logger.info(
            "bandit_state_loaded",
            path=str(self.save_path),
            total_pulls=state.total_pulls,
        )
        return state
```

### 6.4 Policy Improvement Pathway

As the bandit learns, its knowledge can be used to **improve Policy v2** itself:

```python
class PolicyLearner:
    """
    Extracts insights from bandit to improve Policy v2 weights.

    This is a periodic batch process, not real-time.
    """

    def __init__(self, bandit: MultiArmedBandit, policy: PolicyV2):
        self.bandit = bandit
        self.policy = policy

    def analyze_arm_performance(self) -> Dict[str, ArmAnalysis]:
        """Analyze performance of each arm across contexts"""
        analyses = {}

        for arm_id, arm in self.bandit.arms.items():
            if arm.n_pulls < 50:  # Need sufficient data
                continue

            analyses[arm_id] = ArmAnalysis(
                arm_id=arm_id,
                overall_mean=arm.mean_reward,
                overall_pulls=arm.n_pulls,
                context_breakdown={
                    ctx: {
                        "mean": stats.mean_reward,
                        "n": stats.n_pulls,
                    }
                    for ctx, stats in arm.context_stats.items()
                    if stats.n_pulls >= 10
                },
                beats_baseline=self._beats_baseline(arm),
            )

        return analyses

    def suggest_policy_updates(self) -> List[PolicyUpdateSuggestion]:
        """
        Generate suggestions for updating Policy v2 weights.

        Only suggests changes when evidence is strong.
        """
        suggestions = []
        analyses = self.analyze_arm_performance()

        # Example: If L2_entropy consistently beats L1 for high-entropy contexts
        l2_entropy = analyses.get("L2_entropy")
        if l2_entropy and l2_entropy.overall_pulls >= 100:
            for ctx, stats in l2_entropy.context_breakdown.items():
                if "ent:high" in ctx and stats["mean"] > 0.5:
                    suggestions.append(PolicyUpdateSuggestion(
                        type="increase_weight",
                        parameter="entropy_score",
                        current_value=self.policy.config.feature_weights["entropy_score"],
                        suggested_value=min(0.25, self.policy.config.feature_weights["entropy_score"] * 1.2),
                        reason=f"L2_entropy performs well (mean={stats['mean']:.3f}) in high-entropy contexts",
                        confidence=self._calculate_confidence(stats["n"]),
                    ))

        return suggestions

    def apply_update(self, suggestion: PolicyUpdateSuggestion) -> None:
        """Apply a policy update (requires manual approval in production)"""
        if suggestion.confidence < 0.8:
            logger.warning(
                "low_confidence_update_skipped",
                suggestion=suggestion,
            )
            return

        # Update Policy v2 config
        old_value = getattr(self.policy.config.feature_weights, suggestion.parameter)
        self.policy.config.feature_weights[suggestion.parameter] = suggestion.suggested_value

        logger.info(
            "policy_weight_updated",
            parameter=suggestion.parameter,
            old_value=old_value,
            new_value=suggestion.suggested_value,
            reason=suggestion.reason,
        )
```

### 6.5 Convergence Criteria

How do we know when the bandit has "learned enough"?

```python
def check_convergence(bandit: MultiArmedBandit) -> ConvergenceStatus:
    """
    Check if bandit has converged to stable arm preferences.

    Convergence criteria:
    1. All arms have been pulled at least min_pulls times
    2. Arm rankings have been stable for last N decisions
    3. Exploration rate has naturally declined
    """
    # Criterion 1: Minimum exploration
    min_pulls = 20
    underpulled_arms = [
        arm for arm in bandit.arms.values()
        if arm.enabled and arm.n_pulls < min_pulls
    ]
    if underpulled_arms:
        return ConvergenceStatus(
            converged=False,
            reason=f"{len(underpulled_arms)} arms need more exploration",
            confidence=0.0,
        )

    # Criterion 2: Ranking stability
    # Compare rankings from last 50 decisions vs previous 50
    recent_rankings = bandit.get_arm_rankings(last_n=50)
    previous_rankings = bandit.get_arm_rankings(offset=50, last_n=50)
    ranking_similarity = compute_ranking_correlation(recent_rankings, previous_rankings)

    if ranking_similarity < 0.9:
        return ConvergenceStatus(
            converged=False,
            reason=f"Arm rankings still changing (similarity={ranking_similarity:.2f})",
            confidence=ranking_similarity,
        )

    # Criterion 3: Clear winner
    top_arm = max(bandit.arms.values(), key=lambda a: a.mean_reward)
    second_arm = sorted(bandit.arms.values(), key=lambda a: a.mean_reward, reverse=True)[1]

    margin = top_arm.mean_reward - second_arm.mean_reward
    if margin < 0.05:  # Margin too small
        return ConvergenceStatus(
            converged=False,
            reason=f"No clear winner (margin={margin:.3f})",
            confidence=0.5 + margin * 5,
        )

    return ConvergenceStatus(
        converged=True,
        reason="Bandit has converged",
        confidence=0.9 + min(margin, 0.1),
        best_arm=top_arm.arm_id,
        margin=margin,
    )
```

---

## 7. Configuration Schema

### 7.1 Complete YAML Schema

Add to `config/math_controller.yaml`:

```yaml
# =============================================================================
# Multi-Armed Bandit Configuration (Iteration 3)
# =============================================================================
#
# The bandit system provides online learning for level/strategy selection.
# It operates on top of Policy v2, deciding when to explore alternatives.

bandit:
  # Whether bandit is enabled
  enabled: true

  # Algorithm selection
  algorithm: "ucb"  # Options: "ucb", "epsilon_greedy", "thompson"

  # UCB-specific parameters
  ucb_confidence: 1.0           # c parameter in UCB formula (higher = more exploration)
  context_weight: 0.2           # Weight for contextual bonus
  min_context_observations: 5   # Min observations per context bucket before using

  # Epsilon-greedy parameters (if algorithm == "epsilon_greedy")
  epsilon: 0.1                  # Exploration probability

  # Exploration settings
  exploration_rate: 0.1         # Target exploration rate
  exploit_strategy: "bandit"    # "bandit" uses best arm, "baseline" uses Policy v2

  # Update settings
  update_rule: "incremental"    # "incremental" or "ema"
  ema_alpha: 0.1                # Alpha for EMA (if update_rule == "ema")

  # Profile-specific overrides
  profiles:
    research:
      exploration_rate: 0.2
      ucb_confidence: 1.5       # More exploration
    lab:
      exploration_rate: 0.1
      ucb_confidence: 1.0
    production:
      exploration_rate: 0.0     # No exploration
      exploit_strategy: "bandit" # Use learned best arm
    cheap:
      enabled: false            # Disable bandit entirely

  # Safety guardrails
  safety:
    # Exploration limits
    max_exploration_rate: 0.2   # Hard cap on exploration
    exploration_budget: 200     # Max explorations per window
    budget_window_hours: 24     # Budget reset window

    # Degradation detection
    window_size: 100            # Rolling window for degradation check
    min_observations: 20        # Min observations before degradation check
    rollback_threshold: -0.2    # Reward delta that triggers rollback
    consecutive_alerts_for_rollback: 3  # Consecutive alerts before rollback

    # Rollback settings
    min_rollback_observations: 50  # Min observations in rollback before retry
    recovery_threshold: 0.3     # Reward threshold to exit rollback

    # Banned arms (never explore these)
    banned_arms: []

    # Hard constraints
    enforce_budget_constraints: true  # Always respect budget → L1
    production_l3_allowed: false      # Never use L3 in production

  # Arms configuration
  arms:
    # L1 arms
    - arm_id: "L1_default"
      level: "deterministic_heuristic"
      strategy: "default"
      enabled: true
      initial_mean: 0.3         # Prior belief about reward

    - arm_id: "L1_relevance"
      level: "deterministic_heuristic"
      strategy: "relevance_scoring"
      enabled: true
      initial_mean: 0.35

    - arm_id: "L1_importance"
      level: "deterministic_heuristic"
      strategy: "importance_scoring"
      enabled: true
      initial_mean: 0.3

    # L2 arms
    - arm_id: "L2_default"
      level: "information_theoretic"
      strategy: "default"
      enabled: true
      initial_mean: 0.4

    - arm_id: "L2_entropy"
      level: "information_theoretic"
      strategy: "entropy_minimization"
      enabled: true
      initial_mean: 0.45

    - arm_id: "L2_bottleneck"
      level: "information_theoretic"
      strategy: "information_bottleneck"
      enabled: true
      initial_mean: 0.4

    - arm_id: "L2_mutual"
      level: "information_theoretic"
      strategy: "mutual_information"
      enabled: true
      initial_mean: 0.35

    # L3 arms
    - arm_id: "L3_default"
      level: "adaptive_hybrid"
      strategy: "hybrid_default"
      enabled: true
      initial_mean: 0.5

    - arm_id: "L3_weighted"
      level: "adaptive_hybrid"
      strategy: "weighted_combination"
      enabled: true
      initial_mean: 0.45

  # Persistence settings
  persistence:
    save_path: "eval/math_policy_logs/bandit_state.json"
    save_frequency: 50          # Save every N decisions
    backup_on_rollback: true    # Create backup when rollback triggered
    max_backups: 5              # Keep last N backups

  # Monitoring settings
  monitoring:
    enabled: true
    log_every_n_decisions: 10   # Log summary every N decisions

    # Metrics to track
    metrics:
      - arm_pulls_total
      - arm_rewards_mean
      - exploration_rate_actual
      - degradation_alerts
      - rollback_count
      - convergence_status

    # Alerting thresholds
    alerts:
      exploration_rate_exceeded: 0.25  # Alert if actual > threshold
      arm_reward_drop: 0.3             # Alert if arm reward drops by this much
      convergence_stalled_hours: 24    # Alert if not converging
```

### 7.2 BanditConfig Dataclass

```python
@dataclass
class BanditConfig:
    """Configuration for the Multi-Armed Bandit system"""

    enabled: bool = True
    algorithm: str = "ucb"  # "ucb", "epsilon_greedy", "thompson"

    # UCB parameters
    ucb_confidence: float = 1.0
    context_weight: float = 0.2
    min_context_observations: int = 5

    # Epsilon-greedy parameters
    epsilon: float = 0.1

    # Exploration settings
    exploration_rate: float = 0.1
    exploit_strategy: str = "bandit"  # "bandit" or "baseline"

    # Update settings
    update_rule: str = "incremental"  # "incremental" or "ema"
    ema_alpha: float = 0.1

    # Safety
    safety: BanditSafetyConfig = field(default_factory=BanditSafetyConfig)

    # Arms
    arms: List[ArmConfig] = field(default_factory=list)

    # Persistence
    persistence: BanditPersistenceConfig = field(default_factory=BanditPersistenceConfig)

    # Level thresholds (inherited from main config)
    l2_memory_threshold: int = 30
    l3_memory_threshold: int = 200
    l3_session_threshold: int = 10
    allowed_levels: List[MathLevel] = field(default_factory=lambda: [MathLevel.L1, MathLevel.L2, MathLevel.L3])

    @classmethod
    def from_yaml(cls, yaml_config: Dict) -> "BanditConfig":
        """Load from YAML config dict"""
        # ... parsing logic ...
        pass


@dataclass
class BanditSafetyConfig:
    """Safety configuration for bandit"""

    max_exploration_rate: float = 0.2
    exploration_budget: int = 200
    budget_window_hours: int = 24

    window_size: int = 100
    min_observations: int = 20
    rollback_threshold: float = -0.2
    consecutive_alerts_for_rollback: int = 3

    min_rollback_observations: int = 50
    recovery_threshold: float = 0.3

    banned_arms: List[str] = field(default_factory=list)
    enforce_budget_constraints: bool = True
    production_l3_allowed: bool = False


@dataclass
class BanditPersistenceConfig:
    """Persistence configuration for bandit"""

    save_path: str = "eval/math_policy_logs/bandit_state.json"
    save_frequency: int = 50
    backup_on_rollback: bool = True
    max_backups: int = 5


@dataclass
class ArmConfig:
    """Configuration for a single arm"""

    arm_id: str
    level: str
    strategy: str
    enabled: bool = True
    initial_mean: float = 0.3  # Prior belief
```

---

## 8. Monitoring and Telemetry

### 8.1 Key Metrics

| Metric | Type | Description | Alert Threshold |
|--------|------|-------------|-----------------|
| `bandit_arm_pulls_total` | Counter | Total pulls per arm | N/A |
| `bandit_arm_reward_mean` | Gauge | Mean reward per arm | Drop > 0.3 |
| `bandit_exploration_rate` | Gauge | Actual exploration rate | > 0.25 |
| `bandit_degradation_alerts` | Counter | Degradation alert count | > 0 |
| `bandit_rollback_count` | Counter | Number of rollbacks | > 0 |
| `bandit_convergence_confidence` | Gauge | Convergence confidence | Stalled > 24h |
| `bandit_best_arm` | Gauge | ID of current best arm | N/A |
| `bandit_ucb_bonus_mean` | Gauge | Mean UCB bonus across arms | N/A |

### 8.2 Monitoring Dashboard

```python
class BanditMonitor:
    """Monitors bandit performance and generates reports"""

    def __init__(self, config: BanditConfig):
        self.config = config
        self.decision_log = deque(maxlen=10000)
        self.metrics = BanditMetrics()

    def record_decision(
        self,
        arm_id: str,
        was_exploration: bool,
        context_key: str,
        ucb_scores: Dict[str, float],
    ) -> None:
        """Record a decision for monitoring"""
        self.decision_log.append({
            "timestamp": datetime.utcnow(),
            "arm_id": arm_id,
            "was_exploration": was_exploration,
            "context_key": context_key,
            "ucb_scores": ucb_scores,
        })

        # Update metrics
        self.metrics.total_decisions += 1
        if was_exploration:
            self.metrics.exploration_count += 1
        self.metrics.arm_selections[arm_id] += 1

    def record_reward(self, arm_id: str, reward: float) -> None:
        """Record a reward observation"""
        self.metrics.arm_rewards[arm_id].append(reward)

    def generate_report(self) -> BanditReport:
        """Generate a monitoring report"""
        return BanditReport(
            timestamp=datetime.utcnow(),
            total_decisions=self.metrics.total_decisions,
            exploration_rate=self.metrics.exploration_count / max(1, self.metrics.total_decisions),
            arm_summary={
                arm_id: {
                    "selections": count,
                    "selection_rate": count / max(1, self.metrics.total_decisions),
                    "mean_reward": np.mean(self.metrics.arm_rewards[arm_id]) if self.metrics.arm_rewards[arm_id] else 0.0,
                    "reward_std": np.std(self.metrics.arm_rewards[arm_id]) if self.metrics.arm_rewards[arm_id] else 0.0,
                }
                for arm_id, count in self.metrics.arm_selections.items()
            },
            context_distribution=self._compute_context_distribution(),
            convergence_status=self._check_convergence(),
        )

    def log_periodic_summary(self) -> None:
        """Log a summary of bandit activity"""
        report = self.generate_report()

        logger.info(
            "bandit_periodic_summary",
            total_decisions=report.total_decisions,
            exploration_rate=f"{report.exploration_rate:.1%}",
            best_arm=report.best_arm,
            convergence=report.convergence_status.converged,
        )

        # Log per-arm stats
        for arm_id, stats in report.arm_summary.items():
            logger.debug(
                "bandit_arm_summary",
                arm_id=arm_id,
                selections=stats["selections"],
                mean_reward=f"{stats['mean_reward']:.3f}",
            )
```

### 8.3 Telemetry Integration

```python
def emit_bandit_telemetry(
    decision: MathDecision,
    arm: Arm,
    was_exploration: bool,
    ucb_score: float,
) -> None:
    """Emit OpenTelemetry spans and metrics for bandit decision"""

    # Span attributes
    span = trace.get_current_span()
    span.set_attributes({
        "bandit.arm_id": arm.arm_id,
        "bandit.was_exploration": was_exploration,
        "bandit.ucb_score": ucb_score,
        "bandit.arm_n_pulls": arm.n_pulls,
        "bandit.arm_mean_reward": arm.mean_reward,
    })

    # Metrics
    metrics.get_meter(__name__).create_counter("bandit_decisions_total").add(
        1,
        {"arm": arm.arm_id, "exploration": str(was_exploration)}
    )

    if was_exploration:
        metrics.get_meter(__name__).create_counter("bandit_explorations_total").add(1)
```

### 8.4 Anomaly Detection

```python
class BanditAnomalyDetector:
    """Detects anomalies in bandit behavior"""

    def __init__(self, config: BanditConfig):
        self.config = config
        self.anomalies_detected = []

    def check_anomalies(self, bandit: MultiArmedBandit) -> List[Anomaly]:
        """Check for various anomalies"""
        anomalies = []

        # Anomaly 1: Arm never explored
        for arm in bandit.arms.values():
            if arm.enabled and arm.n_pulls == 0 and bandit.total_pulls > 100:
                anomalies.append(Anomaly(
                    type="arm_never_explored",
                    severity="medium",
                    message=f"Arm {arm.arm_id} has never been pulled after {bandit.total_pulls} decisions",
                    recommendation="Check if arm is correctly configured and eligible",
                ))

        # Anomaly 2: Exploration rate too high
        if bandit.total_pulls > 50:
            actual_rate = bandit.exploration_count / bandit.total_pulls
            if actual_rate > self.config.safety.max_exploration_rate * 1.5:
                anomalies.append(Anomaly(
                    type="exploration_rate_exceeded",
                    severity="high",
                    message=f"Exploration rate ({actual_rate:.1%}) exceeds max ({self.config.safety.max_exploration_rate:.1%})",
                    recommendation="Check exploration logic and reduce exploration_rate",
                ))

        # Anomaly 3: All arms have same reward
        rewards = [arm.mean_reward for arm in bandit.arms.values() if arm.n_pulls >= 20]
        if len(rewards) >= 3 and max(rewards) - min(rewards) < 0.05:
            anomalies.append(Anomaly(
                type="no_arm_differentiation",
                severity="medium",
                message="All arms have nearly identical rewards",
                recommendation="Reward function may not be discriminating between arms",
            ))

        # Anomaly 4: Reward collapse
        for arm in bandit.arms.values():
            if arm.n_pulls >= 50:
                recent_rewards = list(arm.recent_rewards)[-20:]  # Assuming we track this
                if len(recent_rewards) >= 20:
                    recent_mean = sum(recent_rewards) / len(recent_rewards)
                    if recent_mean < arm.mean_reward - 0.3:
                        anomalies.append(Anomaly(
                            type="arm_reward_collapse",
                            severity="high",
                            message=f"Arm {arm.arm_id} reward collapsed (recent={recent_mean:.3f} vs overall={arm.mean_reward:.3f})",
                            recommendation="Consider disabling arm or investigating cause",
                        ))

        return anomalies
```

---

## 9. Implementation Plan

### 9.1 Classes to Create

| Class | File | Description |
|-------|------|-------------|
| `MultiArmedBandit` | `controller/bandit.py` | Main bandit implementation |
| `Arm` | `controller/bandit.py` | Arm representation with stats |
| `ArmContextStats` | `controller/bandit.py` | Per-context statistics |
| `BanditConfig` | `controller/bandit_config.py` | Configuration dataclass |
| `BanditSafetyConfig` | `controller/bandit_config.py` | Safety configuration |
| `BanditPersistence` | `controller/bandit_persistence.py` | State save/load |
| `BanditMonitor` | `controller/bandit_monitor.py` | Monitoring and metrics |
| `DegradationDetector` | `controller/bandit_safety.py` | Degradation detection |
| `RollbackManager` | `controller/bandit_safety.py` | Rollback management |
| `PolicyLearner` | `controller/policy_learner.py` | Policy improvement from bandit |

### 9.2 Modified Classes

| Class | File | Changes |
|-------|------|---------|
| `MathLayerController` | `controller/controller.py` | Add bandit integration |
| `MathControllerConfig` | `controller/config.py` | Add bandit config section |
| `MathDecision` | `controller/decision.py` | Add bandit_arm_id, was_exploration |

### 9.3 File Structure

```
benchmarking/math_metrics/controller/
├── __init__.py
├── bandit/
│   ├── __init__.py
│   ├── bandit.py           # MultiArmedBandit, Arm, ArmContextStats
│   ├── config.py           # BanditConfig, BanditSafetyConfig, etc.
│   ├── persistence.py      # BanditPersistence, BanditState
│   ├── safety.py           # DegradationDetector, RollbackManager
│   ├── monitor.py          # BanditMonitor, BanditAnomalyDetector
│   └── policy_learner.py   # PolicyLearner
├── controller.py           # Modified MathLayerController
├── config.py               # Modified MathControllerConfig
├── decision.py             # Modified MathDecision
└── ...                     # Existing files
```

### 9.4 Implementation Pseudocode

**MultiArmedBandit (Core)**:

```python
class MultiArmedBandit:
    """
    UCB1-based Multi-Armed Bandit for level/strategy selection.

    This class implements the core bandit logic:
    - Arm selection using UCB with contextual bonus
    - Online updating from reward feedback
    - State persistence

    Usage:
        bandit = MultiArmedBandit(config)

        # Select arm
        arm_id = bandit.select_arm(features, baseline_arm_id)

        # After observing reward
        bandit.update(arm_id, reward, features)
    """

    def __init__(self, config: BanditConfig):
        self.config = config
        self.arms: Dict[str, Arm] = {}
        self.total_pulls = 0
        self.exploration_count = 0

        # Initialize arms from config
        for arm_config in config.arms:
            self.arms[arm_config.arm_id] = Arm(
                arm_id=arm_config.arm_id,
                level=MathLevel(arm_config.level),
                strategy=arm_config.strategy,
                enabled=arm_config.enabled,
                mean_reward=arm_config.initial_mean,
            )

        # Persistence
        self.persistence = BanditPersistence(config.persistence)
        self._load_state()

        # Safety
        self.degradation_detector = DegradationDetector(config.safety)
        self.rollback_manager = RollbackManager(config.safety)

        # Monitoring
        self.monitor = BanditMonitor(config)

    def select_arm(
        self,
        features: FeaturesV2,
        baseline_arm_id: str,
    ) -> str:
        """Select an arm using UCB with safety checks."""
        # Check if in rollback mode
        if self.rollback_manager.rollback_active:
            return baseline_arm_id

        # Get eligible arms
        eligible = self._get_eligible_arms(features)

        if not eligible:
            return baseline_arm_id

        # Decide explore vs exploit
        if self._should_explore():
            selected = self._ucb_select(eligible, features)
            was_exploration = True
        else:
            if self.config.exploit_strategy == "baseline":
                selected = self._get_arm(baseline_arm_id)
            else:
                selected = self._best_arm(eligible, features)
            was_exploration = False

        # Record for monitoring
        self.monitor.record_decision(
            arm_id=selected.arm_id,
            was_exploration=was_exploration,
            context_key=discretize_context(features),
            ucb_scores={a.arm_id: self._compute_ucb(a, features) for a in eligible},
        )

        self.total_pulls += 1
        if was_exploration:
            self.exploration_count += 1

        return selected.arm_id

    def update(
        self,
        arm_id: str,
        reward: float,
        features: FeaturesV2,
    ) -> None:
        """Update arm statistics after observing reward."""
        arm = self.arms.get(arm_id)
        if not arm:
            logger.warning("unknown_arm_in_update", arm_id=arm_id)
            return

        # Update arm
        context_key = discretize_context(features)
        arm.update(reward, context_key, self.config.update_rule, self.config.ema_alpha)

        # Update degradation detector
        self.degradation_detector.update(reward, was_exploration=False)

        # Check for degradation
        alert = self.degradation_detector.check_degradation()
        if alert:
            if alert.type == "rollback_triggered":
                self.rollback_manager.trigger_rollback(alert.recommendation)
                self._backup_and_persist()
            else:
                logger.warning("bandit_degradation_warning", alert=alert)

        # Persist periodically
        if self.persistence.should_save():
            self._save_state()

        # Monitoring
        self.monitor.record_reward(arm_id, reward)

    def _ucb_select(self, eligible: List[Arm], features: FeaturesV2) -> Arm:
        """UCB1 selection with contextual bonus."""
        context_key = discretize_context(features)

        best_arm = None
        best_score = float('-inf')

        for arm in eligible:
            score = self._compute_ucb(arm, features, context_key)
            if score > best_score:
                best_score = score
                best_arm = arm

        return best_arm

    def _compute_ucb(
        self,
        arm: Arm,
        features: FeaturesV2,
        context_key: str = None,
    ) -> float:
        """Compute UCB score for an arm."""
        if arm.n_pulls == 0:
            return float('inf')

        # Base UCB
        mean = arm.mean_reward
        bonus = self.config.ucb_confidence * math.sqrt(
            math.log(self.total_pulls + 1) / arm.n_pulls
        )
        ucb = mean + bonus

        # Contextual bonus
        if context_key is None:
            context_key = discretize_context(features)

        if context_key in arm.context_stats:
            ctx = arm.context_stats[context_key]
            if ctx.n_pulls >= self.config.min_context_observations:
                ucb += self.config.context_weight * ctx.mean_reward

        return ucb

    def _best_arm(self, eligible: List[Arm], features: FeaturesV2) -> Arm:
        """Select best arm by mean reward (exploitation)."""
        context_key = discretize_context(features)

        best_arm = None
        best_reward = float('-inf')

        for arm in eligible:
            # Prefer context-specific reward if available
            if context_key in arm.context_stats:
                ctx = arm.context_stats[context_key]
                if ctx.n_pulls >= self.config.min_context_observations:
                    reward = ctx.mean_reward
                else:
                    reward = arm.mean_reward
            else:
                reward = arm.mean_reward

            if reward > best_reward:
                best_reward = reward
                best_arm = arm

        return best_arm

    def _should_explore(self) -> bool:
        """Determine if this decision should explore."""
        # Check rollback
        if self.rollback_manager.rollback_active:
            return False

        # Check exploration budget
        if self.config.safety.max_exploration_rate <= 0:
            return False

        # Calculate current rate
        if self.total_pulls == 0:
            return random.random() < self.config.exploration_rate

        current_rate = self.exploration_count / self.total_pulls

        # Explore if under budget
        if current_rate < self.config.exploration_rate:
            return random.random() < self.config.exploration_rate

        return False

    def _get_eligible_arms(self, features: FeaturesV2) -> List[Arm]:
        """Get arms eligible in current context."""
        eligible = []

        for arm in self.arms.values():
            if not arm.enabled:
                continue
            if arm.level not in self.config.allowed_levels:
                continue
            if arm.arm_id in self.config.safety.banned_arms:
                continue

            # Level requirements
            if arm.level == MathLevel.L2:
                if features.memory_count < self.config.l2_memory_threshold:
                    continue
            if arm.level == MathLevel.L3:
                if features.memory_count < self.config.l3_memory_threshold:
                    continue
                if features.session_length < self.config.l3_session_threshold:
                    continue

            eligible.append(arm)

        return eligible

    def _load_state(self) -> None:
        """Load persisted state."""
        state = self.persistence.load()
        if state:
            self.total_pulls = state.total_pulls
            self.exploration_count = state.exploration_count
            for arm_id, arm_state in state.arms.items():
                if arm_id in self.arms:
                    self.arms[arm_id].restore_state(arm_state)

    def _save_state(self) -> None:
        """Save current state."""
        state = BanditState(
            version="1.0",
            last_updated=datetime.utcnow(),
            total_pulls=self.total_pulls,
            exploration_count=self.exploration_count,
            arms={arm_id: arm.get_state() for arm_id, arm in self.arms.items()},
        )
        self.persistence.save(state)
```

### 9.5 Test Cases

```python
class TestMultiArmedBandit:
    """Test suite for MultiArmedBandit"""

    def test_arm_selection_unpulled_arms_first(self):
        """Unpulled arms should have infinite UCB bonus"""
        bandit = MultiArmedBandit(test_config)
        features = create_test_features()

        # All arms start unpulled
        arm_id = bandit.select_arm(features, "L1_default")

        # Should select one of the unpulled arms (infinite UCB)
        assert bandit.arms[arm_id].n_pulls == 0 or bandit.total_pulls == 1

    def test_exploration_rate_respected(self):
        """Exploration rate should not exceed max"""
        bandit = MultiArmedBandit(test_config_low_exploration)
        features = create_test_features()

        for _ in range(1000):
            bandit.select_arm(features, "L1_default")

        actual_rate = bandit.exploration_count / bandit.total_pulls
        assert actual_rate <= test_config_low_exploration.safety.max_exploration_rate * 1.1

    def test_update_increases_pulls(self):
        """Updating an arm should increase its pull count"""
        bandit = MultiArmedBandit(test_config)

        initial_pulls = bandit.arms["L1_default"].n_pulls
        bandit.update("L1_default", 0.5, create_test_features())

        assert bandit.arms["L1_default"].n_pulls == initial_pulls + 1

    def test_ucb_converges_to_best_arm(self):
        """UCB should converge to selecting best arm"""
        bandit = MultiArmedBandit(test_config)

        # Simulate rewards: L2_entropy always best
        for _ in range(500):
            features = create_test_features()
            arm_id = bandit.select_arm(features, "L1_default")

            if arm_id == "L2_entropy":
                reward = 0.8
            elif "L2" in arm_id:
                reward = 0.6
            else:
                reward = 0.4

            bandit.update(arm_id, reward, features)

        # Best arm should be L2_entropy
        best = max(bandit.arms.values(), key=lambda a: a.mean_reward)
        assert best.arm_id == "L2_entropy"

    def test_rollback_disables_exploration(self):
        """Rollback should disable exploration"""
        bandit = MultiArmedBandit(test_config)
        bandit.rollback_manager.trigger_rollback("test")

        features = create_test_features()
        arm_id = bandit.select_arm(features, "L1_default")

        # Should always return baseline in rollback
        assert arm_id == "L1_default"

    def test_persistence_roundtrip(self):
        """State should survive save/load cycle"""
        bandit = MultiArmedBandit(test_config)

        # Make some updates
        for _ in range(10):
            bandit.update("L1_default", 0.5, create_test_features())

        # Save
        bandit._save_state()

        # Load into new instance
        bandit2 = MultiArmedBandit(test_config)

        assert bandit2.arms["L1_default"].n_pulls == bandit.arms["L1_default"].n_pulls
        assert bandit2.arms["L1_default"].mean_reward == bandit.arms["L1_default"].mean_reward

    def test_context_discretization(self):
        """Context discretization should be consistent"""
        features = create_test_features(memory_count=100, entropy=0.8)

        key1 = discretize_context(features)
        key2 = discretize_context(features)

        assert key1 == key2
        assert "mem:med" in key1 or "mem:high" in key1
        assert "ent:high" in key1
```

---

## 10. Evaluation Strategy

### 10.1 Benchmark Design

**Experiment 1: Baseline vs Bandit**

| Configuration | Description |
|--------------|-------------|
| Baseline | Policy v2 only, no bandit |
| Bandit-10 | Policy v2 + Bandit (ε=0.1) |
| Bandit-20 | Policy v2 + Bandit (ε=0.2) |
| Bandit-UCB | Policy v2 + UCB (c=1.0) |
| Bandit-UCB-High | Policy v2 + UCB (c=2.0, more exploration) |

**Experiment 2: Context Impact**

| Configuration | Description |
|--------------|-------------|
| No-Context | UCB without contextual bonus |
| Context-Low | UCB with context_weight=0.1 |
| Context-Med | UCB with context_weight=0.2 |
| Context-High | UCB with context_weight=0.5 |

**Experiment 3: Safety Overhead**

| Configuration | Description |
|--------------|-------------|
| No-Safety | Bandit without degradation detection |
| Safety-Loose | window_size=200, threshold=-0.5 |
| Safety-Tight | window_size=50, threshold=-0.1 |

### 10.2 Metrics to Track

**Primary Metrics**:

| Metric | Description | Target |
|--------|-------------|--------|
| Average Reward | Mean reward across all decisions | > Policy v2 by 5% |
| MRR | Mean Reciprocal Rank | > Policy v2 by 5% |
| Regret | Cumulative difference from optimal | < 0.1 * T |
| Convergence Steps | Steps to reach 90% of final performance | < 300 |

**Secondary Metrics**:

| Metric | Description | Target |
|--------|-------------|--------|
| Exploration Overhead | Reward lost due to exploration | < 5% |
| Arm Diversity | Entropy of arm selection distribution | > 0.5 initially, < 0.3 after convergence |
| Rollback Frequency | Number of rollbacks triggered | 0 |
| Context Utilization | % of decisions using context bonus | > 50% after warmup |

### 10.3 Evaluation Protocol

```python
def run_bandit_evaluation(
    dataset: str = "academic_lite",
    n_runs: int = 10,
    decisions_per_run: int = 500,
) -> EvaluationResults:
    """
    Run comprehensive evaluation of bandit system.

    Protocol:
    1. For each configuration (baseline, bandit variants)
    2. For each run (statistical significance)
    3. For each decision
       - Make decision using controller
       - Execute operation
       - Record outcome and reward
    4. Compute metrics and compare
    """
    results = {}

    for config_name, config in CONFIGURATIONS.items():
        config_results = []

        for run in range(n_runs):
            # Initialize fresh controller
            controller = MathLayerController(config=config)

            # Reset memory state
            memory_state = initialize_memory_state(dataset)

            run_rewards = []
            run_mrrs = []

            for decision_num in range(decisions_per_run):
                # Create context
                context = create_context_from_state(memory_state)

                # Make decision
                decision = controller.decide(context)

                # Execute and measure
                outcome = execute_and_measure(decision, memory_state)

                # Record outcome
                controller.record_outcome(
                    decision_id=decision.decision_id,
                    success=outcome.success,
                    metrics=outcome.metrics,
                )

                run_rewards.append(outcome.reward)
                run_mrrs.append(outcome.metrics.get("mrr", 0.0))

                # Update memory state
                memory_state = outcome.new_state

            config_results.append({
                "rewards": run_rewards,
                "mrrs": run_mrrs,
                "final_bandit_state": controller.bandit.get_state() if controller.bandit else None,
            })

        results[config_name] = analyze_runs(config_results)

    return compare_configurations(results)
```

### 10.4 Expected Results

**After 200 decisions**:

| Configuration | Avg Reward | vs Baseline | Convergence |
|--------------|------------|-------------|-------------|
| Baseline (Policy v2) | 0.45 | - | N/A |
| Bandit-10 | 0.48 | +6.7% | 150 steps |
| Bandit-20 | 0.47 | +4.4% | 100 steps |
| Bandit-UCB | 0.50 | +11.1% | 180 steps |

**After 500 decisions**:

| Configuration | Avg Reward | vs Baseline | Best Arm % |
|--------------|------------|-------------|------------|
| Baseline (Policy v2) | 0.45 | - | N/A |
| Bandit-10 | 0.52 | +15.6% | 78% |
| Bandit-20 | 0.50 | +11.1% | 72% |
| Bandit-UCB | 0.54 | +20.0% | 82% |

**Exploration Cost Analysis**:

| Phase | Decisions | Exploration % | Avg Reward | vs Exploit-Only |
|-------|-----------|---------------|------------|-----------------|
| Warmup (1-50) | 50 | 25% | 0.35 | -22% |
| Learning (51-200) | 150 | 12% | 0.48 | -4% |
| Converged (201-500) | 300 | 5% | 0.55 | +2% |

---

## 11. Production Rollout

### 11.1 Phased Deployment

**Phase 1: Research Mode (Week 1-2)**

- Deploy to research profile only
- Full exploration (20%)
- Monitor for anomalies
- Collect baseline data

**Phase 2: Lab Mode (Week 3-4)**

- Deploy to lab profile
- Moderate exploration (10%)
- Test degradation detection
- Validate rollback works

**Phase 3: Production Shadow (Week 5-6)**

- Deploy to production in shadow mode
- Bandit makes decisions but doesn't execute them
- Compare bandit choice vs Policy v2 choice
- Measure would-have-been regret

**Phase 4: Production Limited (Week 7-8)**

- Enable bandit in production
- Exploitation only (0% exploration)
- Use learned weights from research/lab
- Monitor closely for degradation

**Phase 5: Production Full (Week 9+)**

- Continue exploitation in production
- Periodic weight updates from research findings
- Gradual trust building

### 11.2 Rollout Checklist

```markdown
## Pre-Deployment Checklist

### Code Quality
- [ ] All unit tests passing
- [ ] Integration tests with MathLayerController passing
- [ ] Code reviewed and approved
- [ ] No new security vulnerabilities

### Configuration
- [ ] Bandit config reviewed for profile
- [ ] Safety thresholds appropriate for profile
- [ ] Persistence path writable
- [ ] Monitoring endpoints configured

### Monitoring
- [ ] Dashboards created for bandit metrics
- [ ] Alerts configured for degradation
- [ ] Rollback procedure documented
- [ ] On-call team informed

### Validation
- [ ] Dry-run in staging environment
- [ ] Shadow mode results acceptable
- [ ] No performance regression
- [ ] Memory/CPU usage acceptable

### Rollback Plan
- [ ] Config flag to disable bandit tested
- [ ] Persisted state backup available
- [ ] Previous release tag identified
- [ ] Rollback runbook available
```

### 11.3 A/B Testing Strategy

For production deployment, use A/B testing:

```python
def should_use_bandit_for_request(request_id: str, config: ABTestConfig) -> bool:
    """
    Determine if request should use bandit based on A/B test configuration.

    Uses consistent hashing to ensure same user/session always gets same treatment.
    """
    # Hash request ID to get consistent bucket
    hash_val = int(hashlib.md5(request_id.encode()).hexdigest(), 16)
    bucket = hash_val % 100

    # Check if in treatment group
    return bucket < config.treatment_percentage


# A/B test configuration
ab_test_config = ABTestConfig(
    test_name="bandit_v1",
    treatment_percentage=10,  # 10% of traffic uses bandit
    start_date=datetime(2025, 1, 15),
    end_date=datetime(2025, 2, 15),
)
```

### 11.4 Success Criteria

The bandit rollout is considered successful if:

1. **Quality**: No degradation in MRR or other quality metrics
2. **Stability**: No rollbacks triggered in production
3. **Learning**: Bandit converges to stable arm preferences
4. **Efficiency**: Learned preferences match or exceed Policy v2

Quantitative targets:

| Metric | Minimum | Target | Failure |
|--------|---------|--------|---------|
| Production MRR | >= Policy v2 | +5% | < 95% of baseline |
| Rollback Count | 0 | 0 | > 2 |
| Error Rate | <= Policy v2 | < 1% | > 2% |
| Latency P99 | <= Policy v2 + 10ms | < 50ms | > 100ms |

---

## Appendix A: Mathematical Derivations

### A.1 UCB1 Regret Bound

The regret of UCB1 after T rounds is bounded by:

```
R(T) <= 8 * sum_{a: μ_a < μ*} (ln(T) / Δ_a) + (1 + π²/3) * sum_a Δ_a
```

Where:
- `μ*` = reward of optimal arm
- `μ_a` = reward of arm a
- `Δ_a = μ* - μ_a` = gap for arm a

For our 9 arms, assuming average gap of 0.1:

```
R(T) <= 8 * 9 * ln(T) / 0.1 + 10 * 9 * 0.1
     <= 720 * ln(T) + 9
```

After 500 decisions: `R(500) <= 720 * 6.2 + 9 = 4473` (total regret)
Per-decision regret: `4473 / 500 = 8.9` (this is cumulative, not per-step)

### A.2 Exploration Probability Derivation

For UCB to explore arm `a` over best arm `*`, we need:

```
μ_a + c * sqrt(ln(N) / n_a) > μ* + c * sqrt(ln(N) / n_*)
```

Rearranging:
```
c * (sqrt(ln(N) / n_a) - sqrt(ln(N) / n_*)) > μ* - μ_a = Δ_a
```

For small n_a (underexplored arm):
```
sqrt(ln(N) / n_a) >> sqrt(ln(N) / n_*)
```

So UCB naturally explores undersampled arms even if their estimated mean is lower.

---

## Appendix B: Context Bucket Analysis

### B.1 Expected Bucket Distribution

With 4 features × 3 buckets each = 81 possible contexts.

Expected distribution (based on typical workloads):

| Context Pattern | Expected % | Notes |
|-----------------|------------|-------|
| mem:low_* | 40% | New sessions |
| mem:med_* | 45% | Active sessions |
| mem:high_* | 15% | Long-running sessions |
| *_ent:low | 30% | Well-organized memory |
| *_ent:med | 50% | Typical entropy |
| *_ent:high | 20% | Disorganized memory |
| *_task:simple | 60% | Store/retrieve ops |
| *_task:medium | 30% | Context selection |
| *_task:complex | 10% | Deep reflection |

### B.2 Coverage Analysis

To achieve 10 observations per context bucket:
- 81 buckets × 10 observations = 810 decisions minimum
- With exploration rate 10%: ~81 exploration decisions

Realistically, some buckets will be rare (< 1% of traffic), so full coverage requires ~2000+ decisions.

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **Arm** | A specific (level, strategy) combination that can be selected |
| **UCB** | Upper Confidence Bound - exploration bonus based on uncertainty |
| **Regret** | Cumulative difference between optimal and actual rewards |
| **Exploration** | Selecting an arm to gather information |
| **Exploitation** | Selecting the best-known arm for reward |
| **Context** | Feature vector describing current decision situation |
| **Degradation** | Sustained drop in reward below baseline |
| **Rollback** | Reverting to safe Policy v2 defaults |
| **Convergence** | Stable arm preference after sufficient learning |

---

*Document prepared for Iteration 3 of Math Layer Controller development.*
*Implementation target: Sonnet-based code generation.*
*For implementation, refer to: `/benchmarking/math_metrics/controller/bandit/`*
