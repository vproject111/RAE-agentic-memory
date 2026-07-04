"""
Policy Metrics - Decision Optimization

These metrics analyze the quality of memory policy decisions:
- Optimal Retrieval Ratio (ORR): How often optimal memories are retrieved
- Cost-Quality Frontier (CQF): Trade-off between cost and quality
- Reflection Policy Efficiency: Whether reflection was triggered appropriately
- Cross-Layer Mathematical Consistency (CMC): Consistency between Math-1, Math-2, Math-3 layers
"""

from typing import Any, Dict, List, Optional, Set

import numpy as np

from .base import MathMetricBase


class OptimalRetrievalRatio(MathMetricBase):
    """
    Optimal Retrieval Ratio (ORR)

    Measures how often the system retrieves optimal memory fragments.

    Formula: ORR = optimal_hits / total_retrievals

    We define "optimal" as memories that:
    1. Are in the ground truth for the query
    2. Are ranked in top-k results

    High ORR = system consistently retrieves best memories
    Low ORR = system retrieves suboptimal memories

    Range: 0.0 (never optimal) to 1.0 (always optimal)
    Typical good value: > 0.7
    """

    def __init__(self):
        super().__init__(
            name="optimal_retrieval_ratio",
            description="Frequency of optimal memory retrieval",
        )

    def calculate(
        self,
        query_results: List[Dict[str, Any]],
        k: int = 5,
    ) -> float:
        """
        Calculate ORR from query results.

        Args:
            query_results: List of query result dicts with 'expected' and 'retrieved' keys
            k: Top-k threshold

        Returns:
            ORR value (0.0 to 1.0)
        """
        if len(query_results) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_queries": 0,
                "reason": "No queries provided",
            }
            return 0.0

        optimal_hits = 0
        total_queries = len(query_results)

        # Track detailed stats
        rank_positions = []  # Position of first relevant result
        num_optimal_per_query = []

        for result in query_results:
            expected = set(result.get("expected", []))
            retrieved = result.get("retrieved", [])[:k]

            # Count how many optimal results in top-k
            optimal_count = sum(1 for mem_id in retrieved if mem_id in expected)
            num_optimal_per_query.append(optimal_count)

            # Mark as hit if at least one optimal result in top-k
            if optimal_count > 0:
                optimal_hits += 1

                # Find rank of first optimal result
                for i, mem_id in enumerate(retrieved, 1):
                    if mem_id in expected:
                        rank_positions.append(i)
                        break

        orr = optimal_hits / total_queries

        self._last_value = orr
        self._last_metadata = {
            "num_queries": total_queries,
            "optimal_hits": optimal_hits,
            "k": k,
            "avg_rank_of_first_hit": (
                float(np.mean(rank_positions)) if rank_positions else 0.0
            ),
            "avg_optimal_per_query": float(np.mean(num_optimal_per_query)),
        }

        return orr


class CostQualityFrontier(MathMetricBase):
    """
    Cost-Quality Frontier (CQF)

    Measures the trade-off between reflection cost and quality improvement.

    Formula: CQF = reflection_gain / tokens_used * 1000

    This gives us "quality improvement per 1000 tokens".

    High CQF = efficient reflection (good quality for low cost)
    Low CQF = inefficient reflection (small improvement for high cost)

    Range: Unbounded (can be negative if reflection degrades quality)
    Typical good value: > 0.01 (1% quality improvement per 1000 tokens)
    """

    def __init__(self):
        super().__init__(
            name="cost_quality_frontier",
            description="Quality improvement per unit cost",
        )

    def calculate(
        self,
        reflection_gain: float,
        tokens_used: int,
    ) -> float:
        """
        Calculate CQF from reflection results.

        Args:
            reflection_gain: Quality improvement (RG score)
            tokens_used: Total tokens consumed

        Returns:
            CQF value (quality per 1000 tokens)
        """
        if tokens_used == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "reflection_gain": reflection_gain,
                "tokens_used": 0,
                "reason": "No tokens used",
            }
            return 0.0

        # Calculate efficiency: gain per 1000 tokens
        cqf = (reflection_gain / tokens_used) * 1000

        self._last_value = cqf
        self._last_metadata = {
            "reflection_gain": reflection_gain,
            "tokens_used": tokens_used,
            "cost_efficiency": (
                "high" if cqf > 0.01 else "medium" if cqf > 0.005 else "low"
            ),
        }

        return cqf


class ReflectionPolicyEfficiency(MathMetricBase):
    """
    Reflection Policy Efficiency

    Measures whether reflection was triggered at the right times.

    We analyze:
    1. True Positives: Reflection triggered when needed (gain > threshold)
    2. False Positives: Reflection triggered but no benefit
    3. True Negatives: No reflection when not needed
    4. False Negatives: Missed opportunities (should have reflected but didn't)

    Efficiency = (TP + TN) / (TP + TN + FP + FN)

    Range: 0.0 (poor policy) to 1.0 (perfect policy)
    Typical good value: > 0.8
    """

    def __init__(self):
        super().__init__(
            name="reflection_policy_efficiency",
            description="Accuracy of reflection trigger decisions",
        )

    def calculate(
        self,
        reflection_events: List[Dict[str, Any]],
        gain_threshold: float = 0.05,
    ) -> float:
        """
        Calculate policy efficiency.

        Args:
            reflection_events: List of events with:
                - 'triggered': bool (was reflection triggered)
                - 'gain': float (actual reflection gain)
                - 'needed': bool (was reflection needed based on gain threshold)
            gain_threshold: Minimum gain to consider reflection "needed"

        Returns:
            Efficiency score (0.0 to 1.0)
        """
        if len(reflection_events) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_events": 0,
                "reason": "No reflection events provided",
            }
            return 0.0

        # Count policy outcomes
        true_positives = 0  # Triggered and beneficial
        false_positives = 0  # Triggered but not beneficial
        true_negatives = 0  # Not triggered and not needed
        false_negatives = 0  # Not triggered but was needed

        for event in reflection_events:
            triggered = event.get("triggered", False)
            gain = event.get("gain", 0.0)
            needed = gain >= gain_threshold

            if triggered and needed:
                true_positives += 1
            elif triggered and not needed:
                false_positives += 1
            elif not triggered and not needed:
                true_negatives += 1
            elif not triggered and needed:
                false_negatives += 1

        total = len(reflection_events)
        efficiency = (true_positives + true_negatives) / total if total > 0 else 0.0

        # Calculate precision and recall for reflection policy
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        self._last_value = efficiency
        self._last_metadata = {
            "num_events": total,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "true_negatives": true_negatives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "gain_threshold": gain_threshold,
        }

        return efficiency


class CrossLayerMathematicalConsistency(MathMetricBase):
    """
    Cross-Layer Mathematical Consistency (CMC)

    Measures the consistency of mathematical decisions across RAE's three math layers:

    **Math-1 (Heuristics Layer)**:
    - Gating decisions (should memory be processed?)
    - Priority scoring
    - Fast heuristic evaluations

    **Math-2 (Metrics Layer)**:
    - Similarity metrics (cosine, Jaccard, etc.)
    - Ranking algorithms
    - Distance calculations

    **Math-3 (Policy Layer)**:
    - Graph operator decisions
    - MDP-based policy optimization
    - Long-term value estimation

    A consistent system should have:
    - Math-1 gating decisions aligned with Math-2 rankings
      (items passed by gating should rank well)
    - Math-2 rankings aligned with Math-3 policy decisions
      (top-ranked items should be selected by policy)
    - No conflicts where lower layers contradict higher layer decisions

    Formula:
        CMC = weighted_mean(
            consistency_1_2,  # Math-1 <-> Math-2 alignment
            consistency_2_3,  # Math-2 <-> Math-3 alignment
            consistency_1_3   # Math-1 <-> Math-3 alignment (transitive check)
        )

    Where each consistency score is:
        consistency = agreement_count / total_decisions

    Range: 0.0 (complete inconsistency) to 1.0 (perfect consistency)
    Typical good value: > 0.8

    Example:
        >>> cmc = CrossLayerMathematicalConsistency()
        >>> result = cmc.calculate(
        ...     math1_decisions=[
        ...         {"item_id": "m1", "passed_gating": True, "priority": 0.8},
        ...         {"item_id": "m2", "passed_gating": True, "priority": 0.6},
        ...         {"item_id": "m3", "passed_gating": False, "priority": 0.2},
        ...     ],
        ...     math2_rankings=[
        ...         {"item_id": "m1", "rank": 1, "score": 0.95},
        ...         {"item_id": "m2", "rank": 2, "score": 0.75},
        ...         {"item_id": "m3", "rank": 5, "score": 0.20},
        ...     ],
        ...     math3_policies=[
        ...         {"item_id": "m1", "action": "retrieve", "value": 0.9},
        ...         {"item_id": "m2", "action": "retrieve", "value": 0.7},
        ...         {"item_id": "m3", "action": "skip", "value": 0.1},
        ...     ],
        ... )
        >>> print(f"CMC: {result:.2f}")
        CMC: 1.00
    """

    def __init__(self):
        super().__init__(
            name="cross_layer_mathematical_consistency",
            description="Consistency of decisions across Math-1, Math-2, Math-3 layers",
        )

    def calculate(
        self,
        math1_decisions: List[Dict[str, Any]],
        math2_rankings: List[Dict[str, Any]],
        math3_policies: List[Dict[str, Any]],
        gating_threshold: float = 0.5,
        rank_threshold: int = 10,
        policy_positive_actions: Optional[List[str]] = None,
        weight_1_2: float = 0.4,
        weight_2_3: float = 0.4,
        weight_1_3: float = 0.2,
    ) -> float:
        """
        Calculate Cross-Layer Mathematical Consistency score.

        Args:
            math1_decisions: List of Math-1 layer decisions, each with:
                - "item_id": str - unique identifier
                - "passed_gating": bool - whether item passed gating
                - "priority": float - priority score (0.0 to 1.0)
                - "score": float (optional) - raw gating score

            math2_rankings: List of Math-2 layer rankings, each with:
                - "item_id": str - unique identifier
                - "rank": int - ranking position (1 = best)
                - "score": float - similarity/ranking score

            math3_policies: List of Math-3 layer policy decisions, each with:
                - "item_id": str - unique identifier
                - "action": str - action taken ("retrieve", "skip", "archive", etc.)
                - "value": float - estimated value/utility

            gating_threshold: Priority threshold for considering item "gated in"
            rank_threshold: Rank threshold for considering item "highly ranked"
            policy_positive_actions: Actions considered "positive" decisions.
                                   Defaults to ["retrieve", "use", "include"]
            weight_1_2: Weight for Math-1 <-> Math-2 consistency
            weight_2_3: Weight for Math-2 <-> Math-3 consistency
            weight_1_3: Weight for Math-1 <-> Math-3 consistency

        Returns:
            CMC score (0.0 to 1.0)
        """
        # Set default positive actions
        if policy_positive_actions is None:
            policy_positive_actions = ["retrieve", "use", "include", "select"]

        # Handle empty inputs
        if not math1_decisions and not math2_rankings and not math3_policies:
            self._last_value = 1.0  # Vacuously consistent
            self._last_metadata = {
                "num_items": 0,
                "reason": "No decisions provided",
            }
            return 1.0

        # Build lookup dictionaries by item_id
        math1_by_id = {d["item_id"]: d for d in math1_decisions}
        math2_by_id = {r["item_id"]: r for r in math2_rankings}
        math3_by_id = {p["item_id"]: p for p in math3_policies}

        # Get all unique item IDs
        all_ids = (
            set(math1_by_id.keys()) | set(math2_by_id.keys()) | set(math3_by_id.keys())
        )

        if not all_ids:
            self._last_value = 1.0
            self._last_metadata = {
                "num_items": 0,
                "reason": "No item IDs found",
            }
            return 1.0

        # Calculate consistency scores
        consistency_1_2 = self._calculate_math1_math2_consistency(
            math1_by_id, math2_by_id, all_ids, gating_threshold, rank_threshold
        )

        consistency_2_3 = self._calculate_math2_math3_consistency(
            math2_by_id, math3_by_id, all_ids, rank_threshold, policy_positive_actions
        )

        consistency_1_3 = self._calculate_math1_math3_consistency(
            math1_by_id, math3_by_id, all_ids, gating_threshold, policy_positive_actions
        )

        # Calculate weighted average
        total_weight = weight_1_2 + weight_2_3 + weight_1_3
        if total_weight == 0:
            total_weight = 1.0

        cmc = (
            weight_1_2 * consistency_1_2
            + weight_2_3 * consistency_2_3
            + weight_1_3 * consistency_1_3
        ) / total_weight

        self._last_value = cmc
        self._last_metadata = {
            "num_items": len(all_ids),
            "num_math1_decisions": len(math1_decisions),
            "num_math2_rankings": len(math2_rankings),
            "num_math3_policies": len(math3_policies),
            "consistency_math1_math2": consistency_1_2,
            "consistency_math2_math3": consistency_2_3,
            "consistency_math1_math3": consistency_1_3,
            "weight_1_2": weight_1_2,
            "weight_2_3": weight_2_3,
            "weight_1_3": weight_1_3,
            "gating_threshold": gating_threshold,
            "rank_threshold": rank_threshold,
            "policy_positive_actions": policy_positive_actions,
        }

        return cmc

    def _calculate_math1_math2_consistency(
        self,
        math1_by_id: Dict[str, Dict[str, Any]],
        math2_by_id: Dict[str, Dict[str, Any]],
        all_ids: Set[str],
        gating_threshold: float,
        rank_threshold: int,
    ) -> float:
        """
        Calculate consistency between Math-1 gating and Math-2 rankings.

        Consistency rules:
        - Items that passed gating (high priority) should be highly ranked
        - Items that failed gating should have low ranks
        """
        agreements = 0
        comparisons = 0

        for item_id in all_ids:
            m1 = math1_by_id.get(item_id)
            m2 = math2_by_id.get(item_id)

            if m1 is None or m2 is None:
                continue  # Skip items missing from either layer

            comparisons += 1

            # Get Math-1 gating decision
            passed_gating = m1.get("passed_gating", False)
            priority = m1.get("priority", 0.0)
            m1_positive = passed_gating or priority >= gating_threshold

            # Get Math-2 ranking decision
            rank = m2.get("rank", float("inf"))
            m2_positive = rank <= rank_threshold

            # Check consistency
            if m1_positive == m2_positive:
                agreements += 1

        if comparisons == 0:
            return 1.0  # No comparisons possible = vacuously consistent

        return agreements / comparisons

    def _calculate_math2_math3_consistency(
        self,
        math2_by_id: Dict[str, Dict[str, Any]],
        math3_by_id: Dict[str, Dict[str, Any]],
        all_ids: Set[str],
        rank_threshold: int,
        policy_positive_actions: List[str],
    ) -> float:
        """
        Calculate consistency between Math-2 rankings and Math-3 policy decisions.

        Consistency rules:
        - Highly ranked items should be selected by policy
        - Low-ranked items should be skipped/ignored by policy
        """
        agreements = 0
        comparisons = 0

        for item_id in all_ids:
            m2 = math2_by_id.get(item_id)
            m3 = math3_by_id.get(item_id)

            if m2 is None or m3 is None:
                continue

            comparisons += 1

            # Get Math-2 ranking decision
            rank = m2.get("rank", float("inf"))
            m2_positive = rank <= rank_threshold

            # Get Math-3 policy decision
            action = m3.get("action", "")
            m3_positive = action.lower() in [a.lower() for a in policy_positive_actions]

            # Check consistency
            if m2_positive == m3_positive:
                agreements += 1

        if comparisons == 0:
            return 1.0

        return agreements / comparisons

    def _calculate_math1_math3_consistency(
        self,
        math1_by_id: Dict[str, Dict[str, Any]],
        math3_by_id: Dict[str, Dict[str, Any]],
        all_ids: Set[str],
        gating_threshold: float,
        policy_positive_actions: List[str],
    ) -> float:
        """
        Calculate transitive consistency between Math-1 gating and Math-3 policy.

        This checks for direct conflicts where:
        - Math-1 gates out an item but Math-3 selects it
        - Math-1 prioritizes an item but Math-3 ignores it
        """
        agreements = 0
        comparisons = 0

        for item_id in all_ids:
            m1 = math1_by_id.get(item_id)
            m3 = math3_by_id.get(item_id)

            if m1 is None or m3 is None:
                continue

            comparisons += 1

            # Get Math-1 gating decision
            passed_gating = m1.get("passed_gating", False)
            priority = m1.get("priority", 0.0)
            m1_positive = passed_gating or priority >= gating_threshold

            # Get Math-3 policy decision
            action = m3.get("action", "")
            m3_positive = action.lower() in [a.lower() for a in policy_positive_actions]

            # Check consistency
            if m1_positive == m3_positive:
                agreements += 1

        if comparisons == 0:
            return 1.0

        return agreements / comparisons

    def calculate_detailed(
        self,
        math1_decisions: List[Dict[str, Any]],
        math2_rankings: List[Dict[str, Any]],
        math3_policies: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate CMC with detailed per-item analysis.

        Returns detailed breakdown of consistency for each item,
        useful for debugging and understanding layer interactions.

        Args:
            math1_decisions: Math-1 layer decisions
            math2_rankings: Math-2 layer rankings
            math3_policies: Math-3 layer policy decisions
            **kwargs: Additional arguments passed to calculate()

        Returns:
            Dict with:
                - "cmc_score": Overall CMC score
                - "per_item_analysis": List of per-item consistency details
                - "inconsistent_items": List of item IDs with conflicts
                - "conflict_types": Breakdown of conflict types
        """
        # Calculate overall score
        cmc_score = self.calculate(
            math1_decisions, math2_rankings, math3_policies, **kwargs
        )

        # Build lookups
        math1_by_id = {d["item_id"]: d for d in math1_decisions}
        math2_by_id = {r["item_id"]: r for r in math2_rankings}
        math3_by_id = {p["item_id"]: p for p in math3_policies}

        all_ids = (
            set(math1_by_id.keys()) | set(math2_by_id.keys()) | set(math3_by_id.keys())
        )

        # Get thresholds from kwargs or defaults
        gating_threshold = kwargs.get("gating_threshold", 0.5)
        rank_threshold = kwargs.get("rank_threshold", 10)
        policy_positive_actions = kwargs.get(
            "policy_positive_actions", ["retrieve", "use", "include", "select"]
        )

        # Analyze each item
        per_item_analysis = []
        inconsistent_items = []
        conflict_types = {
            "math1_math2": 0,
            "math2_math3": 0,
            "math1_math3": 0,
        }

        for item_id in all_ids:
            m1 = math1_by_id.get(item_id)
            m2 = math2_by_id.get(item_id)
            m3 = math3_by_id.get(item_id)

            item_analysis = {
                "item_id": item_id,
                "math1": m1,
                "math2": m2,
                "math3": m3,
                "conflicts": [],
            }

            # Determine layer decisions
            m1_positive = None
            m2_positive = None
            m3_positive = None

            if m1:
                passed_gating = m1.get("passed_gating", False)
                priority = m1.get("priority", 0.0)
                m1_positive = passed_gating or priority >= gating_threshold

            if m2:
                rank = m2.get("rank", float("inf"))
                m2_positive = rank <= rank_threshold

            if m3:
                action = m3.get("action", "")
                m3_positive = action.lower() in [
                    a.lower() for a in policy_positive_actions
                ]

            # Check for conflicts
            if m1_positive is not None and m2_positive is not None:
                if m1_positive != m2_positive:
                    item_analysis["conflicts"].append("math1_math2")
                    conflict_types["math1_math2"] += 1

            if m2_positive is not None and m3_positive is not None:
                if m2_positive != m3_positive:
                    item_analysis["conflicts"].append("math2_math3")
                    conflict_types["math2_math3"] += 1

            if m1_positive is not None and m3_positive is not None:
                if m1_positive != m3_positive:
                    item_analysis["conflicts"].append("math1_math3")
                    conflict_types["math1_math3"] += 1

            item_analysis["is_consistent"] = len(item_analysis["conflicts"]) == 0

            per_item_analysis.append(item_analysis)

            if not item_analysis["is_consistent"]:
                inconsistent_items.append(item_id)

        return {
            "cmc_score": cmc_score,
            "metadata": self._last_metadata,
            "per_item_analysis": per_item_analysis,
            "inconsistent_items": inconsistent_items,
            "conflict_types": conflict_types,
            "num_consistent": len(all_ids) - len(inconsistent_items),
            "num_inconsistent": len(inconsistent_items),
        }
