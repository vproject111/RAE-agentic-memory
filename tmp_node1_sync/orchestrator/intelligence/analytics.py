"""Performance analytics for orchestrator intelligence.

Analyzes execution records to identify patterns, model performance,
and optimization opportunities.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .performance_tracker import ExecutionRecord, PerformanceTracker, TaskOutcome

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformance:
    """Performance metrics for a specific model."""

    model_id: str
    provider: str
    role: str  # 'planner' or 'implementer'

    # Execution metrics
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float

    # Cost metrics
    total_cost: float
    avg_cost_per_task: float

    # Time metrics
    total_duration: float
    avg_duration: float

    # Quality metrics
    quality_gate_pass_rate: float
    code_review_pass_rate: float
    avg_retries: float

    # Task breakdown
    by_area: Dict[str, int]
    by_risk: Dict[str, int]


@dataclass
class TaskPatternAnalysis:
    """Analysis of task execution patterns."""

    task_area: str
    task_risk: str

    # Success metrics
    total_attempts: int
    successful: int
    failed: int
    success_rate: float

    # Best performing models
    best_planner: Optional[Tuple[str, float]]  # (model_id, success_rate)
    best_implementer: Optional[Tuple[str, float]]

    # Cost analysis
    avg_cost: float
    min_cost: float
    max_cost: float

    # Duration analysis
    avg_duration: float
    min_duration: float
    max_duration: float

    # Common failure patterns
    common_errors: List[Tuple[str, int]]  # (error_type, count)


class PerformanceAnalytics:
    """Analyzes performance data to extract insights.

    Provides methods for analyzing model performance, identifying patterns,
    and generating recommendations for routing optimization.
    """

    def __init__(self, tracker: PerformanceTracker):
        """Initialize analytics with performance tracker.

        Args:
            tracker: Performance tracker with execution records
        """
        self.tracker = tracker

    def analyze_model_performance(
        self, model_id: str, role: str = "any", min_samples: int = 5
    ) -> Optional[ModelPerformance]:
        """Analyze performance of a specific model.

        Args:
            model_id: Model identifier
            role: Role to analyze ('planner', 'implementer', 'any')
            min_samples: Minimum samples required for analysis

        Returns:
            Model performance metrics or None if insufficient data
        """
        # Get relevant records
        if role == "any":
            records = self.tracker.get_records_by_model(model_id, role="any")
            # Use role where model appeared most
            planner_count = len([r for r in records if r.planner_model == model_id])
            implementer_count = len(
                [r for r in records if r.implementer_model == model_id]
            )
            primary_role = (
                "planner" if planner_count >= implementer_count else "implementer"
            )
        else:
            records = self.tracker.get_records_by_model(model_id, role=role)
            primary_role = role

        if len(records) < min_samples:
            logger.warning(
                f"Insufficient data for model {model_id} (role={role}): "
                f"{len(records)} samples < {min_samples} required"
            )
            return None

        # Calculate metrics
        successful = [r for r in records if r.outcome == TaskOutcome.SUCCESS]
        failed = [r for r in records if r.outcome == TaskOutcome.FAILED]

        total_cost = sum(r.total_cost_usd for r in records)
        total_duration = sum(r.duration_seconds for r in records)

        quality_passed = sum(1 for r in records if r.quality_gate_passed)
        code_review_passed = sum(1 for r in records if r.code_review_passed)
        total_retries = sum(r.num_retries for r in records)

        # Task breakdown
        by_area: Dict[str, int] = defaultdict(int)
        by_risk: Dict[str, int] = defaultdict(int)

        for record in records:
            by_area[record.task_area] += 1
            by_risk[record.task_risk] += 1

        # Extract provider
        provider = (
            records[0].planner_provider
            if primary_role == "planner"
            else records[0].implementer_provider
        )

        return ModelPerformance(
            model_id=model_id,
            provider=provider,
            role=primary_role,
            total_tasks=len(records),
            successful_tasks=len(successful),
            failed_tasks=len(failed),
            success_rate=len(successful) / len(records),
            total_cost=total_cost,
            avg_cost_per_task=total_cost / len(records),
            total_duration=total_duration,
            avg_duration=total_duration / len(records),
            quality_gate_pass_rate=quality_passed / len(records),
            code_review_pass_rate=code_review_passed / len(records),
            avg_retries=total_retries / len(records),
            by_area=dict(by_area),
            by_risk=dict(by_risk),
        )

    def analyze_task_pattern(
        self, task_area: str, task_risk: str, min_samples: int = 3
    ) -> Optional[TaskPatternAnalysis]:
        """Analyze execution patterns for a task type.

        Args:
            task_area: Task area (core, api, docs, etc.)
            task_risk: Risk level (low, medium, high)
            min_samples: Minimum samples required

        Returns:
            Task pattern analysis or None if insufficient data
        """
        # Get matching records
        records = [
            r
            for r in self.tracker.get_all_records()
            if r.task_area == task_area and r.task_risk == task_risk
        ]

        if len(records) < min_samples:
            return None

        # Success metrics
        successful = [r for r in records if r.outcome == TaskOutcome.SUCCESS]
        failed = [r for r in records if r.outcome == TaskOutcome.FAILED]

        # Find best performing models
        planner_performance: Dict[str, Tuple[int, int]] = defaultdict(
            lambda: (0, 0)
        )  # (success, total)
        implementer_performance: Dict[str, Tuple[int, int]] = defaultdict(
            lambda: (0, 0)
        )

        for record in records:
            success = 1 if record.outcome == TaskOutcome.SUCCESS else 0

            # Track planner
            p_success, p_total = planner_performance[record.planner_model]
            planner_performance[record.planner_model] = (
                p_success + success,
                p_total + 1,
            )

            # Track implementer
            i_success, i_total = implementer_performance[record.implementer_model]
            implementer_performance[record.implementer_model] = (
                i_success + success,
                i_total + 1,
            )

        # Find best performers (min 2 samples)
        def get_best(
            perf_dict: Dict[str, Tuple[int, int]],
        ) -> Optional[Tuple[str, float]]:
            valid = [
                (model, succ / total)
                for model, (succ, total) in perf_dict.items()
                if total >= 2
            ]
            if not valid:
                return None
            return max(valid, key=lambda x: x[1])

        best_planner = get_best(planner_performance)
        best_implementer = get_best(implementer_performance)

        # Cost analysis
        costs = [r.total_cost_usd for r in records]
        durations = [r.duration_seconds for r in records]

        # Common errors
        error_counts: Dict[str, int] = defaultdict(int)
        for record in failed:
            if record.error_type:
                error_counts[record.error_type] += 1

        common_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]

        return TaskPatternAnalysis(
            task_area=task_area,
            task_risk=task_risk,
            total_attempts=len(records),
            successful=len(successful),
            failed=len(failed),
            success_rate=len(successful) / len(records),
            best_planner=best_planner,
            best_implementer=best_implementer,
            avg_cost=sum(costs) / len(costs),
            min_cost=min(costs),
            max_cost=max(costs),
            avg_duration=sum(durations) / len(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            common_errors=common_errors,
        )

    def rank_models_for_task(
        self,
        task_area: str,
        task_risk: str,
        role: str,
        metric: str = "success_rate",
        min_samples: int = 3,
    ) -> List[Tuple[str, float]]:
        """Rank models by performance for a specific task type.

        Args:
            task_area: Task area
            task_risk: Risk level
            role: Role ('planner' or 'implementer')
            metric: Metric to rank by ('success_rate', 'cost', 'duration')
            min_samples: Minimum samples required per model

        Returns:
            List of (model_id, metric_value) tuples, sorted by performance
        """
        # Get matching records
        records = [
            r
            for r in self.tracker.get_all_records()
            if r.task_area == task_area and r.task_risk == task_risk
        ]

        # Group by model
        model_records: Dict[str, List[ExecutionRecord]] = defaultdict(list)

        for record in records:
            if role == "planner":
                model_records[record.planner_model].append(record)
            else:
                model_records[record.implementer_model].append(record)

        # Calculate metrics
        results: List[Tuple[str, float]] = []

        for model_id, model_recs in model_records.items():
            if len(model_recs) < min_samples:
                continue

            if metric == "success_rate":
                successful = len(
                    [r for r in model_recs if r.outcome == TaskOutcome.SUCCESS]
                )
                value = successful / len(model_recs)
                # Higher is better
                results.append((model_id, value))

            elif metric == "cost":
                avg_cost = sum(r.total_cost_usd for r in model_recs) / len(model_recs)
                # Lower is better, invert for ranking
                results.append((model_id, -avg_cost))

            elif metric == "duration":
                avg_duration = sum(r.duration_seconds for r in model_recs) / len(
                    model_recs
                )
                # Lower is better, invert for ranking
                results.append((model_id, -avg_duration))

        # Sort by metric value (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_provider_comparison(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across providers.

        Returns:
            Dictionary mapping provider names to performance metrics
        """
        providers = set()
        for record in self.tracker.get_all_records():
            providers.add(record.planner_provider)
            providers.add(record.implementer_provider)

        comparison: Dict[str, Dict[str, float]] = {}

        for provider in providers:
            records = self.tracker.get_records_by_provider(provider, role="any")

            if not records:
                continue

            successful = len([r for r in records if r.outcome == TaskOutcome.SUCCESS])
            total_cost = sum(r.total_cost_usd for r in records)
            total_duration = sum(r.duration_seconds for r in records)

            comparison[provider] = {
                "total_tasks": len(records),
                "success_rate": successful / len(records),
                "avg_cost": total_cost / len(records),
                "avg_duration": total_duration / len(records),
            }

        return comparison

    def identify_optimization_opportunities(
        self, min_cost_savings: float = 0.01
    ) -> List[Dict[str, any]]:
        """Identify opportunities to optimize routing for cost or performance.

        Args:
            min_cost_savings: Minimum cost savings to report (USD per task)

        Returns:
            List of optimization recommendations
        """
        opportunities = []

        # Analyze each task pattern
        task_patterns = set()
        for record in self.tracker.get_all_records():
            task_patterns.add((record.task_area, record.task_risk))

        for task_area, task_risk in task_patterns:
            pattern = self.analyze_task_pattern(task_area, task_risk)

            if not pattern or pattern.total_attempts < 5:
                continue

            # Check if there's a cheaper model with similar success rate
            if pattern.best_implementer:
                best_model, best_success = pattern.best_implementer

                # Get current average cost
                current_cost = pattern.avg_cost

                # Find cheaper alternatives
                implementer_rankings = self.rank_models_for_task(
                    task_area, task_risk, "implementer", metric="cost", min_samples=2
                )

                for model_id, neg_cost in implementer_rankings:
                    alt_cost = -neg_cost
                    if alt_cost < current_cost - min_cost_savings:
                        # Check success rate
                        alt_records = [
                            r
                            for r in self.tracker.get_all_records()
                            if r.task_area == task_area
                            and r.task_risk == task_risk
                            and r.implementer_model == model_id
                        ]
                        alt_success = len(
                            [r for r in alt_records if r.outcome == TaskOutcome.SUCCESS]
                        )
                        alt_success_rate = alt_success / len(alt_records)

                        # If success rate is comparable (within 10%)
                        if alt_success_rate >= pattern.success_rate - 0.1:
                            savings = current_cost - alt_cost

                            opportunities.append(
                                {
                                    "type": "cost_optimization",
                                    "task_area": task_area,
                                    "task_risk": task_risk,
                                    "role": "implementer",
                                    "current_model": best_model,
                                    "recommended_model": model_id,
                                    "current_cost": current_cost,
                                    "new_cost": alt_cost,
                                    "savings_per_task": savings,
                                    "current_success_rate": best_success,
                                    "new_success_rate": alt_success_rate,
                                }
                            )
                            break

        return opportunities
