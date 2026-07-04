# Mathematical Decision Engine for RAE

## Overview

The Mathematical Decision Engine is the "brain" that uses the three-tier mathematical metrics to make intelligent decisions about memory management.

**Key Principle:** The three layers don't just measure - they **guide actions**.

```
┌─────────────────────────────────────────────────────────────┐
│                   DECISION LOOP                              │
│                                                              │
│  Measure → Analyze → Decide → Act → Measure (repeat)       │
└─────────────────────────────────────────────────────────────┘
```

## Three Decision Layers

### 1. Structure-Based Decisions (Geometry → Actions)

**Measures graph topology and semantic coherence to decide on memory organization.**

#### Decision Rules:

```python
# Rule 1: Graph Connectivity
if GCS < 1.0:
    → LOW_CONNECTIVITY
    → ACTION: Add semantic connections
    → PRIORITY: High

if GCS > 3.0:
    → OVER_CONNECTED
    → ACTION: Prune weak edges
    → PRIORITY: Medium

# Rule 2: Semantic Coherence
if SCS < 0.6:
    → WEAK_CONNECTIONS
    → ACTION: Strengthen semantic links
    → PRIORITY: High

if SCS > 0.9:
    → STRONG_COHERENCE
    → ACTION: Maintain current structure
    → PRIORITY: Low

# Rule 3: Graph Entropy
if Entropy > log2(num_nodes) * 0.7:
    → HIGH_DISORGANIZATION
    → ACTION: Cluster and organize
    → PRIORITY: High

if Entropy < log2(num_nodes) * 0.3:
    → OVER_ORGANIZED
    → ACTION: Allow more diversity
    → PRIORITY: Low

# Rule 4: Structural Drift
if Structural_Drift > 0.5:
    → UNSTABLE_STRUCTURE
    → ACTION: Consolidate and stabilize
    → PRIORITY: Critical

if Structural_Drift < 0.1:
    → STABLE_STRUCTURE
    → ACTION: Continue normal operation
    → PRIORITY: None
```

#### Action Map:

| Metric | Threshold | Decision | Action |
|--------|-----------|----------|--------|
| GCS < 1.0 | Low connectivity | Add connections | `graph_service.enhance_connectivity()` |
| SCS < 0.6 | Weak semantics | Strengthen links | `graph_service.strengthen_semantic_edges()` |
| Entropy > 0.7*max | Disorganized | Cluster memories | `memory_service.cluster_and_organize()` |
| S-Drift > 0.5 | Unstable | Consolidate | `memory_service.consolidate_structure()` |

### 2. Dynamics-Based Decisions (Evolution → Actions)

**Tracks memory changes over time to decide on maintenance and reflection.**

#### Decision Rules:

```python
# Rule 1: Memory Drift Index
if MDI > 0.5:
    → HIGH_SEMANTIC_DRIFT
    → ACTION: Trigger memory consolidation
    → PRIORITY: Critical

if MDI > 0.3 and MDI <= 0.5:
    → MODERATE_DRIFT
    → ACTION: Schedule reflection
    → PRIORITY: High

if MDI <= 0.3:
    → STABLE_CONTENT
    → ACTION: No action needed
    → PRIORITY: None

# Rule 2: Retention Curve (AUC)
if Retention_AUC < 0.6:
    → POOR_RETENTION
    → ACTION: Increase importance scores
    → ACTION: Add memory reinforcement
    → PRIORITY: High

if Retention_AUC > 0.8:
    → GOOD_RETENTION
    → ACTION: Continue current policy
    → PRIORITY: None

# Rule 3: Reflection Gain Score
if RG < 0.05:
    → LOW_REFLECTION_VALUE
    → ACTION: Skip expensive reflection
    → ACTION: Use lightweight reflection
    → PRIORITY: Medium

if RG > 0.15:
    → HIGH_REFLECTION_VALUE
    → ACTION: Increase reflection frequency
    → PRIORITY: High

# Rule 4: Compression Fidelity
if CFR < 0.7:
    → LOSSY_COMPRESSION
    → ACTION: Reduce compression ratio
    → ACTION: Keep more detail
    → PRIORITY: High

if CFR > 0.9:
    → SAFE_COMPRESSION
    → ACTION: Allow more compression
    → PRIORITY: Low
```

#### Action Map:

| Metric | Threshold | Decision | Action |
|--------|-----------|----------|--------|
| MDI > 0.5 | High drift | Consolidate | `memory_service.consolidate_memories()` |
| MDI 0.3-0.5 | Moderate drift | Reflect | `reflection_engine.trigger_reflection()` |
| Retention < 0.6 | Poor retention | Reinforce | `memory_service.increase_importance()` |
| RG < 0.05 | Low value | Skip reflection | `reflection_engine.use_lightweight()` |
| CFR < 0.7 | Lossy compression | Reduce compression | `memory_service.reduce_compression_ratio()` |

### 3. Policy-Based Decisions (Optimization → Actions)

**Optimizes cost-quality trade-offs and retrieval efficiency.**

#### Decision Rules:

```python
# Rule 1: Optimal Retrieval Ratio
if ORR < 0.5:
    → POOR_RETRIEVAL
    → ACTION: Improve search algorithm
    → ACTION: Re-index memories
    → PRIORITY: Critical

if ORR >= 0.7 and ORR < 0.85:
    → GOOD_RETRIEVAL
    → ACTION: Fine-tune parameters
    → PRIORITY: Low

if ORR >= 0.85:
    → EXCELLENT_RETRIEVAL
    → ACTION: Maintain current policy
    → PRIORITY: None

# Rule 2: Cost-Quality Frontier
if CQF < 0.005:
    → INEFFICIENT_REFLECTION
    → ACTION: Reduce reflection scope
    → ACTION: Use cheaper models
    → PRIORITY: High

if CQF >= 0.01:
    → EFFICIENT_REFLECTION
    → ACTION: Continue current approach
    → PRIORITY: None

if CQF >= 0.02:
    → HIGHLY_EFFICIENT
    → ACTION: Consider expanding scope
    → PRIORITY: Low

# Rule 3: Reflection Policy Efficiency
if RPE < 0.6:
    → BAD_POLICY
    → ACTION: Retrain policy model
    → ACTION: Adjust thresholds
    → PRIORITY: Critical

if RPE >= 0.8:
    → GOOD_POLICY
    → ACTION: Continue monitoring
    → PRIORITY: None
```

#### Action Map:

| Metric | Threshold | Decision | Action |
|--------|-----------|----------|--------|
| ORR < 0.5 | Poor retrieval | Improve search | `search_service.retrain_ranker()` |
| ORR < 0.7 | Suboptimal | Fine-tune | `search_service.optimize_parameters()` |
| CQF < 0.005 | Inefficient | Reduce cost | `reflection_engine.use_cheaper_model()` |
| RPE < 0.6 | Bad policy | Retrain | `policy_engine.retrain_decision_model()` |

## Integrated Decision Algorithm

### Main Decision Loop

```python
class MathematicalDecisionEngine:
    """
    Integrated decision engine using all three metric layers.

    This is the "brain" that turns measurements into actions.
    """

    def __init__(self):
        self.structure_metrics = StructureMetricsAnalyzer()
        self.dynamics_metrics = DynamicsMetricsAnalyzer()
        self.policy_metrics = PolicyMetricsAnalyzer()

        self.action_queue = PriorityQueue()
        self.thresholds = self._load_thresholds()

    async def analyze_and_decide(
        self,
        snapshot_current: MemorySnapshot,
        snapshot_previous: Optional[MemorySnapshot] = None,
        query_results: Optional[List[Dict]] = None,
    ) -> List[Action]:
        """
        Main decision loop: analyze metrics and generate actions.

        Returns:
            Prioritized list of actions to execute
        """
        actions = []

        # Layer 1: Structure Analysis
        structure_actions = self._analyze_structure(snapshot_current)
        actions.extend(structure_actions)

        # Layer 2: Dynamics Analysis (requires previous snapshot)
        if snapshot_previous:
            dynamics_actions = self._analyze_dynamics(
                snapshot_current,
                snapshot_previous
            )
            actions.extend(dynamics_actions)

        # Layer 3: Policy Analysis (requires query results)
        if query_results:
            policy_actions = self._analyze_policy(query_results)
            actions.extend(policy_actions)

        # Sort by priority
        actions.sort(key=lambda a: a.priority, reverse=True)

        return actions

    def _analyze_structure(self, snapshot: MemorySnapshot) -> List[Action]:
        """Analyze structure metrics and generate actions"""
        actions = []

        # Calculate metrics
        gcs = self.structure_metrics.calculate_gcs(snapshot)
        scs = self.structure_metrics.calculate_scs(snapshot)
        entropy = self.structure_metrics.calculate_entropy(snapshot)

        # Apply decision rules
        if gcs < self.thresholds['gcs_low']:
            actions.append(Action(
                type=ActionType.ADD_CONNECTIONS,
                priority=Priority.HIGH,
                reason=f"Low GCS: {gcs:.3f} < {self.thresholds['gcs_low']}",
                params={'target_gcs': self.thresholds['gcs_target']}
            ))

        if scs < self.thresholds['scs_low']:
            actions.append(Action(
                type=ActionType.STRENGTHEN_SEMANTICS,
                priority=Priority.HIGH,
                reason=f"Low SCS: {scs:.3f} < {self.thresholds['scs_low']}",
                params={'target_scs': self.thresholds['scs_target']}
            ))

        if entropy > self.thresholds['entropy_high']:
            actions.append(Action(
                type=ActionType.CLUSTER_MEMORIES,
                priority=Priority.HIGH,
                reason=f"High entropy: {entropy:.3f} > {self.thresholds['entropy_high']}",
                params={'method': 'hierarchical'}
            ))

        return actions

    def _analyze_dynamics(
        self,
        current: MemorySnapshot,
        previous: MemorySnapshot
    ) -> List[Action]:
        """Analyze dynamics metrics and generate actions"""
        actions = []

        # Calculate metrics
        mdi = self.dynamics_metrics.calculate_mdi(previous, current)
        structural_drift = self.dynamics_metrics.calculate_drift(previous, current)

        # Apply decision rules
        if mdi > self.thresholds['mdi_critical']:
            actions.append(Action(
                type=ActionType.CONSOLIDATE_MEMORY,
                priority=Priority.CRITICAL,
                reason=f"Critical drift: MDI={mdi:.3f}",
                params={'aggressive': True}
            ))
        elif mdi > self.thresholds['mdi_moderate']:
            actions.append(Action(
                type=ActionType.TRIGGER_REFLECTION,
                priority=Priority.HIGH,
                reason=f"Moderate drift: MDI={mdi:.3f}",
                params={'depth': 'normal'}
            ))

        if structural_drift > self.thresholds['structural_drift_high']:
            actions.append(Action(
                type=ActionType.STABILIZE_STRUCTURE,
                priority=Priority.CRITICAL,
                reason=f"Unstable structure: drift={structural_drift:.3f}",
                params={}
            ))

        return actions

    def _analyze_policy(self, query_results: List[Dict]) -> List[Action]:
        """Analyze policy metrics and generate actions"""
        actions = []

        # Calculate metrics
        orr = self.policy_metrics.calculate_orr(query_results)

        # Apply decision rules
        if orr < self.thresholds['orr_poor']:
            actions.append(Action(
                type=ActionType.IMPROVE_SEARCH,
                priority=Priority.CRITICAL,
                reason=f"Poor retrieval: ORR={orr:.3f}",
                params={'reindex': True}
            ))
        elif orr < self.thresholds['orr_good']:
            actions.append(Action(
                type=ActionType.TUNE_SEARCH,
                priority=Priority.LOW,
                reason=f"Suboptimal retrieval: ORR={orr:.3f}",
                params={'method': 'grid_search'}
            ))

        return actions
```

## Default Thresholds

```python
DEFAULT_THRESHOLDS = {
    # Structure thresholds
    'gcs_low': 1.0,
    'gcs_target': 1.5,
    'scs_low': 0.6,
    'scs_target': 0.75,
    'entropy_high': 0.7,  # as fraction of max entropy

    # Dynamics thresholds
    'mdi_moderate': 0.3,
    'mdi_critical': 0.5,
    'structural_drift_high': 0.5,
    'retention_poor': 0.6,
    'rg_low': 0.05,
    'rg_high': 0.15,
    'cfr_low': 0.7,

    # Policy thresholds
    'orr_poor': 0.5,
    'orr_good': 0.7,
    'orr_excellent': 0.85,
    'cqf_inefficient': 0.005,
    'cqf_efficient': 0.01,
    'rpe_bad': 0.6,
    'rpe_good': 0.8,
}
```

## Action Types

```python
class ActionType(Enum):
    # Structure actions
    ADD_CONNECTIONS = "add_connections"
    STRENGTHEN_SEMANTICS = "strengthen_semantics"
    CLUSTER_MEMORIES = "cluster_memories"
    PRUNE_WEAK_EDGES = "prune_weak_edges"

    # Dynamics actions
    CONSOLIDATE_MEMORY = "consolidate_memory"
    TRIGGER_REFLECTION = "trigger_reflection"
    STABILIZE_STRUCTURE = "stabilize_structure"
    INCREASE_IMPORTANCE = "increase_importance"
    REDUCE_COMPRESSION = "reduce_compression"

    # Policy actions
    IMPROVE_SEARCH = "improve_search"
    TUNE_SEARCH = "tune_search"
    REDUCE_REFLECTION_COST = "reduce_reflection_cost"
    RETRAIN_POLICY = "retrain_policy"

class Priority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    NONE = 0
```

## Integration with RAE

```python
# In memory service
class MemoryService:
    def __init__(self):
        self.decision_engine = MathematicalDecisionEngine()
        self.snapshots = []

    async def periodic_analysis(self):
        """Run periodically (e.g., every 100 operations)"""

        # Capture snapshot
        snapshot = await self.capture_snapshot()
        self.snapshots.append(snapshot)

        # Analyze and get actions
        previous = self.snapshots[-2] if len(self.snapshots) > 1 else None
        actions = await self.decision_engine.analyze_and_decide(
            snapshot_current=snapshot,
            snapshot_previous=previous,
            query_results=self.recent_query_results,
        )

        # Execute actions
        for action in actions:
            await self.execute_action(action)

    async def execute_action(self, action: Action):
        """Execute decided action"""
        if action.type == ActionType.ADD_CONNECTIONS:
            await self.graph_service.enhance_connectivity(
                target_gcs=action.params['target_gcs']
            )
        elif action.type == ActionType.TRIGGER_REFLECTION:
            await self.reflection_engine.trigger_reflection(
                depth=action.params['depth']
            )
        # ... more actions
```

## Usage Example

```python
# Initialize decision engine
engine = MathematicalDecisionEngine()

# Capture snapshots
snapshot_t0 = await capture_snapshot()
# ... operations ...
snapshot_t1 = await capture_snapshot()

# Get decisions
actions = await engine.analyze_and_decide(
    snapshot_current=snapshot_t1,
    snapshot_previous=snapshot_t0,
    query_results=recent_queries,
)

# Review actions
for action in actions:
    print(f"[{action.priority.name}] {action.type.value}: {action.reason}")

# Execute
for action in actions:
    await execute_action(action)
```

## Adaptive Thresholds

The decision engine can learn and adapt thresholds over time:

```python
class AdaptiveDecisionEngine(MathematicalDecisionEngine):
    """Decision engine with adaptive thresholds"""

    def update_thresholds_from_feedback(self, feedback: Dict):
        """
        Adjust thresholds based on performance feedback.

        Example: If actions keep triggering but metrics don't improve,
        adjust thresholds to be less sensitive.
        """
        if feedback['action_effectiveness'] < 0.5:
            # Actions not helping - adjust thresholds
            self.thresholds['mdi_moderate'] *= 1.1
            self.thresholds['gcs_low'] *= 0.9
```

## Summary

The Mathematical Decision Engine transforms the RAE math layer from **passive measurement** into **active intelligence**:

1. **Measures** using 11 mathematical metrics across 3 layers
2. **Analyzes** against configurable thresholds
3. **Decides** which actions to take
4. **Acts** through the memory management system
5. **Learns** by adapting thresholds based on outcomes

This closes the loop and makes the math layer a true "brain" for memory management.
