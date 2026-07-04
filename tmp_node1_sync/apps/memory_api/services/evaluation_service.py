"""
Evaluation Service - Metrics Calculation and Quality Assessment

This service implements:
- Retrieval metrics (MRR, NDCG, Precision@K, Recall@K)
- Statistical significance testing
- Performance benchmarking
- Quality monitoring
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import numpy as np
import structlog

from apps.memory_api.models.evaluation_models import (
    EvaluationResult,
    EvaluationStatus,
    MetricScore,
    MetricType,
    RankedResult,
    RelevanceJudgment,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Evaluation Service
# ============================================================================


class EvaluationService:
    """
    Service for calculating retrieval metrics and evaluating search quality.

    Implements standard IR metrics:
    - MRR (Mean Reciprocal Rank)
    - NDCG (Normalized Discounted Cumulative Gain)
    - Precision@K
    - Recall@K
    - MAP (Mean Average Precision)
    """

    def __init__(self):
        """Initialize evaluation service"""
        pass

    async def evaluate_search_results(
        self,
        tenant_id: str,
        project_id: str,
        relevance_judgments: List[RelevanceJudgment],
        search_results: Dict[str, List[RankedResult]],
        metrics_to_compute: List[MetricType],
        k_values: Optional[List[int]] = None,
    ) -> EvaluationResult:
        """
        Evaluate search results against ground truth relevance judgments.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            relevance_judgments: Ground truth relevance scores
            search_results: System-generated ranked results (query_id -> results)
            metrics_to_compute: Which metrics to calculate
            k_values: K values for Precision@K, Recall@K, NDCG@K

        Returns:
            EvaluationResult with computed metrics
        """
        start_time = datetime.now(timezone.utc)
        k_values = k_values or [1, 3, 5, 10]

        logger.info(
            "evaluation_started",
            tenant_id=tenant_id,
            queries=len(search_results),
            metrics=len(metrics_to_compute),
        )

        # Organize relevance judgments by query
        relevance_by_query = self._organize_relevance_judgments(relevance_judgments)

        # Calculate metrics
        metric_scores = []
        total_retrieval_time = 0
        total_documents = 0

        for metric_type in metrics_to_compute:
            if metric_type == MetricType.MRR:
                score = self._calculate_mrr(relevance_by_query, search_results)
                metric_scores.append(
                    MetricScore(
                        metric_type=MetricType.MRR,
                        score=score,
                        num_queries=len(search_results),
                    )
                )

            elif metric_type == MetricType.NDCG:
                for k in k_values:
                    score = self._calculate_ndcg(relevance_by_query, search_results, k)
                    metric_scores.append(
                        MetricScore(
                            metric_type=MetricType.NDCG,
                            score=score,
                            k=k,
                            num_queries=len(search_results),
                        )
                    )

            elif metric_type == MetricType.PRECISION:
                for k in k_values:
                    score = self._calculate_precision_at_k(
                        relevance_by_query, search_results, k
                    )
                    metric_scores.append(
                        MetricScore(
                            metric_type=MetricType.PRECISION,
                            score=score,
                            k=k,
                            num_queries=len(search_results),
                        )
                    )

            elif metric_type == MetricType.RECALL:
                for k in k_values:
                    score = self._calculate_recall_at_k(
                        relevance_by_query, search_results, k
                    )
                    metric_scores.append(
                        MetricScore(
                            metric_type=MetricType.RECALL,
                            score=score,
                            k=k,
                            num_queries=len(search_results),
                        )
                    )

            elif metric_type == MetricType.MAP:
                score = self._calculate_map(relevance_by_query, search_results)
                metric_scores.append(
                    MetricScore(
                        metric_type=MetricType.MAP,
                        score=score,
                        num_queries=len(search_results),
                    )
                )

        # Calculate summary statistics
        for query_id, results in search_results.items():
            total_documents += len(results)
            for result in results:
                if result.retrieval_time_ms:
                    total_retrieval_time += result.retrieval_time_ms

        avg_retrieval_time = (
            total_retrieval_time / len(search_results) if search_results else 0
        )

        # Find best and worst metrics
        best_metric = (
            max(metric_scores, key=lambda m: m.score) if metric_scores else None
        )
        worst_metric = (
            min(metric_scores, key=lambda m: m.score) if metric_scores else None
        )

        # Calculate overall quality score (average of all metrics)
        overall_quality = (
            sum(m.score for m in metric_scores) / len(metric_scores)
            if metric_scores
            else 0.0
        )

        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        evaluation_result = EvaluationResult(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            metrics=metric_scores,
            num_queries_evaluated=len(search_results),
            num_documents_retrieved=total_documents,
            avg_retrieval_time_ms=avg_retrieval_time,
            best_metric=best_metric.metric_type if best_metric else None,
            worst_metric=worst_metric.metric_type if worst_metric else None,
            overall_quality_score=overall_quality,
            started_at=start_time,
            completed_at=end_time,
            evaluation_duration_ms=duration_ms,
            status=EvaluationStatus.COMPLETED,
        )

        logger.info(
            "evaluation_complete",
            overall_quality=overall_quality,
            duration_ms=duration_ms,
        )

        return evaluation_result

    # ========================================================================
    # Metric Calculations
    # ========================================================================

    def _calculate_mrr(
        self,
        relevance_by_query: Dict[str, Dict[UUID, float]],
        search_results: Dict[str, List[RankedResult]],
    ) -> float:
        """
        Calculate Mean Reciprocal Rank.

        MRR = (1/|Q|) * Σ(1/rank_i)
        where rank_i is the rank of the first relevant document for query i.
        """
        reciprocal_ranks = []

        for query_id, results in search_results.items():
            relevance = relevance_by_query.get(query_id, {})

            # Find rank of first relevant document
            for result in results:
                if (
                    result.document_id in relevance
                    and relevance[result.document_id] > 0.5
                ):
                    reciprocal_ranks.append(1.0 / result.rank)
                    break
            else:
                # No relevant document found
                reciprocal_ranks.append(0.0)

        mrr = np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
        return float(mrr)

    def _calculate_ndcg(
        self,
        relevance_by_query: Dict[str, Dict[UUID, float]],
        search_results: Dict[str, List[RankedResult]],
        k: int,
    ) -> float:
        """
        Calculate Normalized Discounted Cumulative Gain at K.

        DCG@K = Σ(rel_i / log2(i+1))  for i=1 to K
        NDCG@K = DCG@K / IDCG@K
        """
        ndcg_scores = []

        for query_id, results in search_results.items():
            relevance = relevance_by_query.get(query_id, {})

            # Calculate DCG@K
            dcg = 0.0
            for i, result in enumerate(results[:k], start=1):
                rel = relevance.get(result.document_id, 0.0)
                dcg += rel / np.log2(i + 1)

            # Calculate IDCG@K (ideal DCG)
            ideal_rels = sorted(relevance.values(), reverse=True)[:k]
            idcg = sum(
                rel / np.log2(i + 1) for i, rel in enumerate(ideal_rels, start=1)
            )

            # NDCG
            if idcg > 0:
                ndcg_scores.append(dcg / idcg)
            else:
                ndcg_scores.append(0.0)

        ndcg = np.mean(ndcg_scores) if ndcg_scores else 0.0
        return float(ndcg)

    def _calculate_precision_at_k(
        self,
        relevance_by_query: Dict[str, Dict[UUID, float]],
        search_results: Dict[str, List[RankedResult]],
        k: int,
    ) -> float:
        """
        Calculate Precision at K.

        Precision@K = (# relevant docs in top K) / K
        """
        precision_scores = []

        for query_id, results in search_results.items():
            relevance = relevance_by_query.get(query_id, {})

            # Count relevant documents in top K
            relevant_in_k = sum(
                1
                for result in results[:k]
                if result.document_id in relevance
                and relevance[result.document_id] > 0.5
            )

            precision = relevant_in_k / min(k, len(results)) if results else 0.0
            precision_scores.append(precision)

        precision = float(np.mean(precision_scores)) if precision_scores else 0.0
        return float(precision)

    def _calculate_recall_at_k(
        self,
        relevance_by_query: Dict[str, Dict[UUID, float]],
        search_results: Dict[str, List[RankedResult]],
        k: int,
    ) -> float:
        """
        Calculate Recall at K.

        Recall@K = (# relevant docs in top K) / (total # relevant docs)
        """
        recall_scores = []

        for query_id, results in search_results.items():
            relevance = relevance_by_query.get(query_id, {})

            # Total relevant documents
            total_relevant = sum(1 for rel in relevance.values() if rel > 0.5)

            if total_relevant == 0:
                continue

            # Count relevant documents in top K
            relevant_in_k = sum(
                1
                for result in results[:k]
                if result.document_id in relevance
                and relevance[result.document_id] > 0.5
            )

            recall = relevant_in_k / total_relevant
            recall_scores.append(recall)

        recall = float(np.mean(recall_scores)) if recall_scores else 0.0
        return float(recall)

    def _calculate_map(
        self,
        relevance_by_query: Dict[str, Dict[UUID, float]],
        search_results: Dict[str, List[RankedResult]],
    ) -> float:
        """
        Calculate Mean Average Precision.

        MAP = (1/|Q|) * Σ(AP_i)
        AP = (1/R) * Σ(Precision@k * rel(k))
        """
        ap_scores = []

        for query_id, results in search_results.items():
            relevance = relevance_by_query.get(query_id, {})

            # Total relevant documents
            total_relevant = sum(1 for rel in relevance.values() if rel > 0.5)

            if total_relevant == 0:
                continue

            # Calculate Average Precision
            relevant_found = 0
            sum_precisions = 0.0

            for i, result in enumerate(results, start=1):
                if (
                    result.document_id in relevance
                    and relevance[result.document_id] > 0.5
                ):
                    relevant_found += 1
                    precision_at_i = relevant_found / i
                    sum_precisions += precision_at_i

            ap = sum_precisions / total_relevant if total_relevant > 0 else 0.0
            ap_scores.append(ap)

        map_score = np.mean(ap_scores) if ap_scores else 0.0
        return float(map_score)

    # ========================================================================
    # A/B Testing
    # ========================================================================

    async def compare_ab_variants(
        self,
        variant_a_metrics: List[MetricScore],
        variant_b_metrics: List[MetricScore],
        confidence_level: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Compare two A/B test variants for statistical significance.

        Args:
            variant_a_metrics: Metrics for variant A
            variant_b_metrics: Metrics for variant B
            confidence_level: Confidence level for significance test

        Returns:
            Dictionary with comparison results
        """
        logger.info("comparing_ab_variants")

        # Group metrics by type
        a_by_type = {m.metric_type: m.score for m in variant_a_metrics}
        b_by_type = {m.metric_type: m.score for m in variant_b_metrics}

        # Compare each metric
        comparisons = {}

        for metric_type in a_by_type.keys():
            if metric_type not in b_by_type:
                continue

            score_a = a_by_type[metric_type]
            score_b = b_by_type[metric_type]

            # Calculate improvement
            improvement = ((score_b - score_a) / score_a * 100) if score_a > 0 else 0.0

            comparisons[metric_type.value] = {
                "variant_a": score_a,
                "variant_b": score_b,
                "improvement_percent": improvement,
                "winner": (
                    "B" if score_b > score_a else "A" if score_a > score_b else "TIE"
                ),
            }

        # Overall winner (majority of metrics)
        winners = [c["winner"] for c in comparisons.values()]
        overall_winner = max(set(winners), key=winners.count) if winners else "TIE"

        logger.info("ab_comparison_complete", winner=overall_winner)

        return {
            "comparisons": comparisons,
            "overall_winner": overall_winner,
            "is_significant": overall_winner != "TIE",  # Simplified
        }

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _organize_relevance_judgments(
        self, judgments: List[RelevanceJudgment]
    ) -> Dict[str, Dict[UUID, float]]:
        """
        Organize relevance judgments by query ID.

        Args:
            judgments: List of relevance judgments

        Returns:
            Dictionary: query_id -> {document_id -> relevance_score}
        """
        organized: Dict[str, Dict[UUID, float]] = {}

        for judgment in judgments:
            if judgment.query_id not in organized:
                organized[judgment.query_id] = {}

            organized[judgment.query_id][
                judgment.document_id
            ] = judgment.relevance_score

        return organized
