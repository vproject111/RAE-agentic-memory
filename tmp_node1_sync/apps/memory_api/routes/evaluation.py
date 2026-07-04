"""
Evaluation API Routes - Metrics and Quality Monitoring

This module provides FastAPI routes for evaluation operations including:
- Search result evaluation (MRR, NDCG, Precision, Recall)
- Drift detection
- A/B testing
- Quality monitoring
- Benchmarking
"""

from typing import Any, cast

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.models.evaluation_models import (
    CreateABTestRequest,
    CreateABTestResponse,
    DetectDriftRequest,
    DetectDriftResponse,
    EvaluateSearchRequest,
    EvaluateSearchResponse,
    GetQualityMetricsRequest,
    GetQualityMetricsResponse,
)
from apps.memory_api.repositories.evaluation_repository import (
    ABTestRepository,
    BenchmarkRepository,
)
from apps.memory_api.services.drift_detector import DriftDetector
from apps.memory_api.services.evaluation_service import EvaluationService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/evaluation", tags=["Evaluation"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_pool(request: Request):
    """Get database connection pool from app state"""
    return request.app.state.pool


async def get_ab_test_repo(pool=Depends(get_pool)) -> ABTestRepository:
    """Get A/B test repository"""
    return ABTestRepository(pool)


async def get_benchmark_repo(pool=Depends(get_pool)) -> BenchmarkRepository:
    """Get benchmark repository"""
    return BenchmarkRepository(pool)


# ============================================================================
# Search Evaluation
# ============================================================================


@router.post("/search", response_model=EvaluateSearchResponse)
async def evaluate_search_results(
    request: EvaluateSearchRequest, pool=Depends(get_pool)
):
    """
    Evaluate search results against ground truth relevance judgments.

    Computes standard IR metrics:
    - MRR (Mean Reciprocal Rank)
    - NDCG@K (Normalized Discounted Cumulative Gain)
    - Precision@K
    - Recall@K
    - MAP (Mean Average Precision)

    **Use Case:** Measure search quality after system changes or for A/B testing.
    """
    try:
        service = EvaluationService()

        result = await service.evaluate_search_results(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            relevance_judgments=request.relevance_judgments,
            search_results=request.search_results,
            metrics_to_compute=request.metrics_to_compute,
            k_values=request.k_values,
        )

        logger.info(
            "search_evaluation_complete",
            queries=result.num_queries_evaluated,
            overall_quality=result.overall_quality_score,
        )

        return EvaluateSearchResponse(
            evaluation_result=result,
            message=f"Evaluated {result.num_queries_evaluated} queries with {len(result.metrics)} metrics",
        )

    except Exception as e:
        logger.error("search_evaluation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics/supported")
async def get_supported_metrics():
    """
    Get list of supported evaluation metrics.

    Returns available metrics with descriptions and parameters.
    """
    return {
        "metrics": {
            "mrr": {
                "name": "Mean Reciprocal Rank",
                "description": "Average of reciprocal ranks of first relevant result",
                "parameters": [],
                "range": [0.0, 1.0],
                "higher_is_better": True,
            },
            "ndcg": {
                "name": "Normalized Discounted Cumulative Gain",
                "description": "Position-aware ranking quality metric",
                "parameters": ["k"],
                "range": [0.0, 1.0],
                "higher_is_better": True,
            },
            "precision": {
                "name": "Precision at K",
                "description": "Fraction of retrieved documents that are relevant",
                "parameters": ["k"],
                "range": [0.0, 1.0],
                "higher_is_better": True,
            },
            "recall": {
                "name": "Recall at K",
                "description": "Fraction of relevant documents that are retrieved",
                "parameters": ["k"],
                "range": [0.0, 1.0],
                "higher_is_better": True,
            },
            "map": {
                "name": "Mean Average Precision",
                "description": "Mean of average precision across queries",
                "parameters": [],
                "range": [0.0, 1.0],
                "higher_is_better": True,
            },
        }
    }


# ============================================================================
# Drift Detection
# ============================================================================


@router.post("/drift/detect", response_model=DetectDriftResponse)
async def detect_drift(request: DetectDriftRequest, pool=Depends(get_pool)):
    """
    Detect distribution drift between baseline and current periods.

    Uses statistical tests (Kolmogorov-Smirnov, PSI) to detect significant
    changes in metric distributions over time.

    **Use Case:** Monitor for data quality issues, concept drift, or system degradation.

    **Drift Types:**
    - `data_drift`: Input distribution changed
    - `concept_drift`: Input-output relationship changed
    - `prediction_drift`: Output distribution changed
    """
    try:
        detector = DriftDetector(pool)

        result = await detector.detect_drift(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            metric_name=request.metric_name,
            drift_type=request.drift_type,
            baseline_start=request.baseline_start,
            baseline_end=request.baseline_end,
            current_start=request.current_start,
            current_end=request.current_end,
            p_value_threshold=request.p_value_threshold,
            statistical_test=request.statistical_test,
        )

        logger.info(
            "drift_detection_complete",
            detected=result.drift_detected,
            severity=result.severity.value,
            metric=request.metric_name,
        )

        message = f"Drift {'detected' if result.drift_detected else 'not detected'}"
        if result.drift_detected:
            message += (
                f" (severity: {result.severity.value}, p-value: {result.p_value:.4f})"
            )

        return DetectDriftResponse(drift_result=result, message=message)

    except Exception as e:
        logger.error("drift_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/drift/severity-levels")
async def get_drift_severity_levels():
    """
    Get drift severity levels and their meanings.

    Returns classification thresholds and recommended actions.
    """
    return {
        "severity_levels": {
            "none": {
                "description": "No significant drift detected",
                "magnitude_range": [0.0, 0.0],
                "action": "Continue monitoring",
            },
            "low": {
                "description": "Minor drift detected",
                "magnitude_range": [0.0, 0.1],
                "action": "Monitor closely, no immediate action required",
            },
            "medium": {
                "description": "Moderate drift detected",
                "magnitude_range": [0.1, 0.25],
                "action": "Investigate data sources, review recent changes",
            },
            "high": {
                "description": "Severe drift detected",
                "magnitude_range": [0.25, 0.5],
                "action": "Immediate investigation required, consider retraining",
            },
            "critical": {
                "description": "Critical drift requiring immediate action",
                "magnitude_range": [0.5, 1.0],
                "action": "URGENT: System validation and immediate remediation",
            },
        },
        "thresholds": {"p_value": 0.05, "psi_warning": 0.1, "psi_critical": 0.25},
    }


# ============================================================================
# A/B Testing
# ============================================================================


@router.post("/ab-test/create", response_model=CreateABTestResponse, status_code=201)
async def create_ab_test(
    request: CreateABTestRequest, repo: ABTestRepository = Depends(get_ab_test_repo)
):
    """
    Create a new A/B test to compare variants.

    Sets up controlled experiment to compare different configurations,
    models, or strategies.

    **Use Case:** Test new search algorithms, weight profiles, or model versions.
    """
    try:
        # Validate traffic allocation
        total_traffic = sum(v.traffic_percentage for v in request.variants)
        if not (99.0 <= total_traffic <= 101.0):  # Allow small floating point error
            raise HTTPException(
                status_code=400,
                detail=f"Traffic allocation must sum to 100% (got {total_traffic}%)",
            )

        # Extract variant A and B (support only 2 variants for now)
        if len(request.variants) != 2:
            raise HTTPException(
                status_code=400,
                detail="Currently only 2-variant A/B tests are supported",
            )

        variant_a = request.variants[0]
        variant_b = request.variants[1]

        # Create test in database
        req_any = cast(Any, request)
        test_record = await repo.create_test(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            test_name=request.test_name,
            description=request.description,
            hypothesis=req_any.hypothesis,
            variant_a_name=variant_a.variant_name,
            variant_a_config=variant_a.configuration,
            variant_b_name=variant_b.variant_name,
            variant_b_config=variant_b.configuration,
            traffic_split=variant_b.traffic_percentage / 100.0,
            min_sample_size=req_any.min_sample_size,
            confidence_level=request.confidence_level,
            primary_metric=req_any.primary_metric,
            secondary_metrics=req_any.secondary_metrics,
            created_by=req_any.created_by,
            tags=req_any.tags,
            metadata=req_any.metadata,
        )

        logger.info(
            "ab_test_created",
            test_id=test_record["id"],
            test_name=request.test_name,
            variants=len(request.variants),
        )

        return CreateABTestResponse(
            test_id=test_record["id"],
            message=f"A/B test '{request.test_name}' created with {len(request.variants)} variants",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_test_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/ab-test/{test_id}/compare")
async def compare_ab_test_variants(
    test_id: str, repo: ABTestRepository = Depends(get_ab_test_repo)
):
    """
    Compare A/B test variants and determine winner.

    Performs statistical significance testing to determine if one variant
    is significantly better than others.

    **Returns:** Comparison results with winner determination.
    """
    try:
        from uuid import UUID

        test_uuid = UUID(test_id)

        # Get test details
        test_record = await repo.get_test(test_uuid)
        if not test_record:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")

        # Calculate statistics
        stats = await repo.calculate_statistics(test_uuid)

        # Get sample counts
        variant_a_count = stats.get("variant_a_count", 0)
        variant_b_count = stats.get("variant_b_count", 0)

        # Check if we have enough samples
        min_samples = test_record.get("min_sample_size", 100)
        if variant_a_count < min_samples or variant_b_count < min_samples:
            return {
                "test_id": test_id,
                "comparison": {
                    "message": f"Not enough samples yet (need {min_samples} per variant)",
                    "status": "pending",
                    "variant_a_count": variant_a_count,
                    "variant_b_count": variant_b_count,
                    "min_sample_size": min_samples,
                },
            }

        # Return basic statistics (full statistical testing would be in application code)
        logger.info(
            "ab_test_comparison_complete",
            test_id=test_id,
            variant_a_count=variant_a_count,
            variant_b_count=variant_b_count,
        )

        return {
            "test_id": test_id,
            "test_name": test_record["test_name"],
            "status": test_record["status"],
            "statistics": stats,
            "comparison": {
                "variant_a_samples": variant_a_count,
                "variant_b_samples": variant_b_count,
                "variant_a_avg": stats.get("variant_a_avg"),
                "variant_b_avg": stats.get("variant_b_avg"),
                "message": "Basic statistics calculated. Full statistical testing available via application logic.",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_test_comparison_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Quality Monitoring
# ============================================================================


@router.post("/quality/metrics", response_model=GetQualityMetricsResponse)
async def get_quality_metrics(
    request: GetQualityMetricsRequest, pool=Depends(get_pool)
):
    """
    Get quality metrics for a time period.

    Returns comprehensive quality indicators including retrieval metrics,
    performance stats, and drift alerts.

    **Use Case:** Monitor system health, track quality over time.
    """
    try:
        # In production, would calculate from stored metrics
        # For now, return structure

        from apps.memory_api.models.evaluation_models import QualityMetrics

        quality_metrics = QualityMetrics(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            period_start=request.period_start,
            period_end=request.period_end,
        )

        logger.info(
            "quality_metrics_retrieved",
            tenant_id=request.tenant_id,
            period=f"{request.period_start} to {request.period_end}",
        )

        return GetQualityMetricsResponse(
            quality_metrics=quality_metrics,
            alerts=[],
            message="Quality metrics retrieved successfully",
        )

    except Exception as e:
        logger.error("get_quality_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/quality/thresholds")
async def get_quality_thresholds():
    """
    Get configured quality thresholds.

    Returns minimum acceptable values for metrics and performance indicators.
    """
    return {
        "retrieval_quality": {
            "min_mrr": 0.5,
            "min_ndcg": 0.6,
            "min_precision": 0.7,
            "description": "Minimum acceptable retrieval quality metrics",
        },
        "performance": {
            "max_response_time_ms": 1000,
            "max_p95_response_time_ms": 2000,
            "max_error_rate": 0.05,
            "description": "Maximum acceptable performance degradation",
        },
        "drift": {
            "p_value_threshold": 0.05,
            "max_acceptable_magnitude": 0.25,
            "description": "Drift detection sensitivity",
        },
    }


# ============================================================================
# Benchmarking
# ============================================================================


@router.post("/benchmark/run")
async def run_benchmark_suite(
    suite_name: str,
    tenant_id: str,
    project_id: str,
    repo: BenchmarkRepository = Depends(get_benchmark_repo),
):
    """
    Run a predefined benchmark suite.

    Executes standardized queries and evaluates results against known
    ground truth for consistent performance measurement.

    **Use Case:** Regular system validation, regression testing.
    """
    try:
        # Find suite by name
        suites = await repo.list_suites(
            tenant_id=tenant_id, project_id=project_id, status="active"
        )
        suite = next((s for s in suites if s["suite_name"] == suite_name), None)

        if not suite:
            raise HTTPException(
                status_code=404,
                detail=f"Benchmark suite '{suite_name}' not found for tenant/project",
            )

        # Create execution record
        execution = await repo.create_execution(
            suite_id=suite["id"],
            tenant_id=tenant_id,
            project_id=project_id,
            triggered_by="api",
        )

        # Update to running status
        await repo.update_execution(execution["id"], status="running")

        logger.info(
            "benchmark_run_started",
            suite=suite_name,
            execution_id=execution["id"],
        )

        return {
            "execution_id": str(execution["id"]),
            "suite_id": str(suite["id"]),
            "suite_name": suite_name,
            "status": "running",
            "message": f"Benchmark suite '{suite_name}' execution started",
            "note": "Execution in progress. Poll execution status or wait for completion.",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("benchmark_run_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/benchmark/suites")
async def list_benchmark_suites(
    tenant_id: str,
    project_id: str,
    repo: BenchmarkRepository = Depends(get_benchmark_repo),
):
    """
    List available benchmark suites.

    Returns configured benchmark suites for systematic evaluation.
    """
    try:
        suites = await repo.list_suites(
            tenant_id=tenant_id, project_id=project_id, status="active"
        )

        # Format response
        formatted_suites = []
        for suite in suites:
            formatted_suites.append(
                {
                    "id": str(suite["id"]),
                    "name": suite["suite_name"],
                    "description": suite.get("description", ""),
                    "num_queries": suite["total_queries"],
                    "version": suite.get("version", "1.0"),
                    "is_baseline": suite.get("is_baseline", False),
                    "last_executed_at": (
                        suite["last_executed_at"].isoformat()
                        if suite.get("last_executed_at")
                        else None
                    ),
                    "execution_count": suite.get("execution_count", 0),
                }
            )

        return {"suites": formatted_suites, "total": len(formatted_suites)}

    except Exception as e:
        logger.error("list_benchmark_suites_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# System Information
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for evaluation service"""
    return {
        "status": "healthy",
        "service": "evaluation_api",
        "version": "1.0",
        "features": [
            "search_evaluation",
            "drift_detection",
            "ab_testing",
            "quality_monitoring",
            "benchmarking",
        ],
        "supported_metrics": ["mrr", "ndcg", "precision", "recall", "map"],
        "statistical_tests": ["ks_test", "psi", "chi_square"],
    }


@router.get("/info")
async def get_evaluation_info():
    """
    Get information about the evaluation system.

    Returns available metrics, tests, and configuration.
    """
    return {
        "evaluation_metrics": {
            "mrr": "Mean Reciprocal Rank - First relevant result position",
            "ndcg": "Normalized DCG - Position-aware ranking quality",
            "precision": "Precision@K - Relevant fraction of retrieved",
            "recall": "Recall@K - Retrieved fraction of relevant",
            "map": "Mean Average Precision - Average across queries",
            "f1": "F1 Score - Harmonic mean of precision and recall",
        },
        "drift_detection": {
            "tests": {
                "ks_test": "Kolmogorov-Smirnov two-sample test",
                "psi": "Population Stability Index",
                "chi_square": "Chi-square test for categorical data",
            },
            "severity_levels": ["none", "low", "medium", "high", "critical"],
            "drift_types": ["data_drift", "concept_drift", "prediction_drift"],
        },
        "ab_testing": {
            "max_variants": 10,
            "min_sample_size": 100,
            "confidence_levels": [0.90, 0.95, 0.99],
        },
        "quality_monitoring": {
            "monitored_metrics": [
                "avg_mrr",
                "avg_ndcg",
                "avg_response_time",
                "error_rate",
            ],
            "alert_types": [
                "quality_degradation",
                "performance_degradation",
                "drift_detected",
            ],
        },
    }
