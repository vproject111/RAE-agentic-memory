"""
Evaluation Suite Models - Metrics and Quality Assessment

This module defines models for the evaluation system including:
- Retrieval metrics (MRR, NDCG, Precision, Recall)
- Distribution drift detection
- A/B testing support
- Quality monitoring
- Performance benchmarking
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class MetricType(str, Enum):
    """Types of evaluation metrics"""

    MRR = "mrr"  # Mean Reciprocal Rank
    NDCG = "ndcg"  # Normalized Discounted Cumulative Gain
    PRECISION = "precision"  # Precision at K
    RECALL = "recall"  # Recall at K
    F1 = "f1"  # F1 Score
    MAP = "map"  # Mean Average Precision
    ACCURACY = "accuracy"  # Classification accuracy
    AUC = "auc"  # Area Under Curve


class DriftType(str, Enum):
    """Types of distribution drift"""

    CONCEPT_DRIFT = "concept_drift"  # Target distribution changed
    DATA_DRIFT = "data_drift"  # Input distribution changed
    PREDICTION_DRIFT = "prediction_drift"  # Output distribution changed


class DriftSeverity(str, Enum):
    """Severity levels for drift"""

    NONE = "none"  # No significant drift
    LOW = "low"  # Minor drift detected
    MEDIUM = "medium"  # Moderate drift
    HIGH = "high"  # Severe drift
    CRITICAL = "critical"  # Critical drift requiring action


class EvaluationStatus(str, Enum):
    """Status of evaluation run"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Core Metric Models
# ============================================================================


class RelevanceJudgment(BaseModel):
    """
    Relevance judgment for a query-document pair.

    Used as ground truth for evaluation.
    """

    query_id: str = Field(..., description="Query identifier")
    document_id: UUID = Field(..., description="Memory/document UUID")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Ground truth relevance"
    )

    # Optional metadata
    judged_by: Optional[str] = None
    judgment_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    judgment_confidence: float = Field(1.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class RankedResult(BaseModel):
    """
    A ranked search result for evaluation.

    Represents system output to be evaluated against ground truth.
    """

    document_id: UUID
    rank: int = Field(..., ge=1)
    score: float = Field(..., ge=0.0, le=1.0)

    # Optional result metadata
    strategy_used: Optional[str] = None
    retrieval_time_ms: Optional[int] = None


class MetricScore(BaseModel):
    """
    Score for a specific metric.

    Single metric evaluation result.
    """

    metric_type: MetricType
    score: float = Field(..., ge=0.0, le=1.0)

    # Metric-specific parameters
    k: Optional[int] = Field(
        None, description="Top-K for Precision@K, Recall@K, NDCG@K"
    )

    # Metadata
    num_queries: int = Field(0, ge=0, description="Number of queries evaluated")
    num_documents: int = Field(0, ge=0, description="Number of documents")
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationResult(BaseModel):
    """
    Complete evaluation result for a query set.

    Aggregates multiple metrics for comprehensive evaluation.
    """

    evaluation_id: UUID
    tenant_id: str
    project_id: str

    # Metrics
    metrics: List[MetricScore] = Field(default_factory=list)

    # Query-level results
    num_queries_evaluated: int = Field(0, ge=0)
    num_documents_retrieved: int = Field(0, ge=0)
    avg_retrieval_time_ms: float = Field(0.0, ge=0.0)

    # Summary statistics
    best_metric: Optional[MetricType] = None
    worst_metric: Optional[MetricType] = None
    overall_quality_score: float = Field(0.0, ge=0.0, le=1.0)

    # Configuration
    evaluation_config: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    started_at: datetime
    completed_at: datetime
    evaluation_duration_ms: int = Field(0, ge=0)

    # Status
    status: EvaluationStatus


# ============================================================================
# Drift Detection Models
# ============================================================================


class DistributionStatistics(BaseModel):
    """
    Statistical summary of a distribution.

    Used for comparing distributions over time.
    """

    mean: float
    std: float
    min: float
    max: float
    median: float
    q25: float  # 25th percentile
    q75: float  # 75th percentile

    # Distribution shape
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None

    # Sample info
    sample_size: int = Field(..., ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DriftDetectionResult(BaseModel):
    """
    Result from drift detection analysis.

    Indicates whether distribution has shifted significantly.
    """

    drift_detected: bool
    drift_type: DriftType
    severity: DriftSeverity

    # Statistical test results
    p_value: float = Field(..., ge=0.0, le=1.0, description="Statistical test p-value")
    test_statistic: float
    test_name: str = Field(..., description="Name of statistical test used")

    # Distribution comparison
    baseline_stats: DistributionStatistics
    current_stats: DistributionStatistics

    # Drift magnitude
    drift_magnitude: float = Field(0.0, ge=0.0, description="Magnitude of drift")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in detection"
    )

    # Recommendations
    action_required: bool = Field(False)
    recommended_actions: List[str] = Field(default_factory=list)

    # Metadata
    detection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    baseline_period: Tuple[datetime, datetime]
    current_period: Tuple[datetime, datetime]


class DriftMonitor(BaseModel):
    """
    Continuous drift monitoring configuration.

    Defines thresholds and monitoring windows.
    """

    monitor_id: UUID
    tenant_id: str
    project_id: str

    # What to monitor
    metric_name: str = Field(..., description="Metric to monitor for drift")
    drift_types_enabled: List[DriftType] = Field(
        default_factory=lambda: [DriftType.DATA_DRIFT, DriftType.PREDICTION_DRIFT]
    )

    # Thresholds
    p_value_threshold: float = Field(0.05, gt=0.0, lt=1.0)
    severity_threshold: DriftSeverity = Field(DriftSeverity.MEDIUM)

    # Monitoring windows
    baseline_window_days: int = Field(30, gt=0, le=365)
    detection_window_days: int = Field(7, gt=0, le=90)
    check_frequency_hours: int = Field(24, gt=0, le=168)

    # Alerting
    alert_enabled: bool = Field(True)
    alert_recipients: List[str] = Field(default_factory=list)

    # Status
    is_active: bool = Field(True)
    last_check_at: Optional[datetime] = None
    last_drift_detected_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# A/B Testing Models
# ============================================================================


class ABTestVariant(BaseModel):
    """
    A variant in an A/B test.

    Represents a specific configuration or model version.
    """

    variant_id: str = Field(..., max_length=100)
    variant_name: str
    description: Optional[str] = None

    # Configuration
    configuration: Dict[str, Any] = Field(default_factory=dict)

    # Traffic allocation
    traffic_percentage: float = Field(..., ge=0.0, le=100.0)

    # Status
    is_active: bool = Field(True)


class ABTestResult(BaseModel):
    """
    Result from an A/B test comparison.

    Compares performance between variants.
    """

    test_id: UUID
    tenant_id: str
    project_id: str

    # Test configuration
    test_name: str
    variants: List[ABTestVariant]

    # Results by variant
    variant_metrics: Dict[str, List[MetricScore]] = Field(default_factory=dict)

    # Statistical significance
    is_significant: bool = Field(False)
    p_value: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(0.95, ge=0.0, le=1.0)

    # Winner determination
    winning_variant: Optional[str] = None
    improvement_percentage: Optional[float] = None

    # Sample sizes
    sample_sizes: Dict[str, int] = Field(default_factory=dict)

    # Duration
    test_duration_days: int = Field(0, ge=0)
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# Quality Monitoring Models
# ============================================================================


class QualityMetrics(BaseModel):
    """
    Quality metrics for system monitoring.

    Tracks overall system health and performance.
    """

    tenant_id: str
    project_id: str

    # Retrieval quality
    avg_mrr: float = Field(0.0, ge=0.0, le=1.0)
    avg_ndcg: float = Field(0.0, ge=0.0, le=1.0)
    avg_precision: float = Field(0.0, ge=0.0, le=1.0)

    # Performance
    avg_response_time_ms: float = Field(0.0, ge=0.0)
    p95_response_time_ms: float = Field(0.0, ge=0.0)
    p99_response_time_ms: float = Field(0.0, ge=0.0)

    # Volume
    total_queries: int = Field(0, ge=0)
    total_documents_retrieved: int = Field(0, ge=0)
    avg_results_per_query: float = Field(0.0, ge=0.0)

    # Error rates
    error_rate: float = Field(0.0, ge=0.0, le=1.0)
    timeout_rate: float = Field(0.0, ge=0.0, le=1.0)

    # Drift indicators
    drift_detected: bool = Field(False)
    drift_severity: Optional[DriftSeverity] = None

    # Time period
    period_start: datetime
    period_end: datetime

    # Computed at
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QualityAlert(BaseModel):
    """
    Alert for quality degradation.

    Triggered when metrics fall below thresholds.
    """

    alert_id: UUID
    tenant_id: str
    project_id: str

    # Alert details
    alert_type: str = Field(..., description="Type of quality issue")
    severity: str = Field(..., description="Alert severity")
    message: str

    # Metrics that triggered alert
    triggering_metrics: Dict[str, float] = Field(default_factory=dict)
    thresholds: Dict[str, float] = Field(default_factory=dict)

    # Context
    affected_queries: int = Field(0, ge=0)
    time_window: str

    # Status
    is_acknowledged: bool = Field(False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    # Timestamps
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None


# ============================================================================
# Request/Response Models
# ============================================================================


class EvaluateSearchRequest(BaseModel):
    """Request to evaluate search results"""

    tenant_id: str
    project_id: str

    # Ground truth
    relevance_judgments: List[RelevanceJudgment] = Field(..., min_length=1)

    # System results to evaluate
    search_results: Dict[str, List[RankedResult]] = Field(
        ..., description="Query ID -> ranked results mapping"
    )

    # Metrics to compute
    metrics_to_compute: List[MetricType] = Field(
        default_factory=lambda: [MetricType.MRR, MetricType.NDCG, MetricType.PRECISION]
    )
    k_values: List[int] = Field(default_factory=lambda: [1, 3, 5, 10])


class EvaluateSearchResponse(BaseModel):
    """Response from search evaluation"""

    evaluation_result: EvaluationResult
    message: str = "Evaluation completed successfully"


class DetectDriftRequest(BaseModel):
    """Request to detect distribution drift"""

    tenant_id: str
    project_id: str

    # What to analyze
    metric_name: str
    drift_type: DriftType

    # Time windows
    baseline_start: datetime
    baseline_end: datetime
    current_start: datetime
    current_end: datetime

    # Detection parameters
    p_value_threshold: float = Field(0.05, gt=0.0, lt=1.0)
    statistical_test: str = Field("ks_test", description="Statistical test to use")


class DetectDriftResponse(BaseModel):
    """Response from drift detection"""

    drift_result: DriftDetectionResult
    message: str = "Drift detection completed"


class CreateABTestRequest(BaseModel):
    """Request to create A/B test"""

    tenant_id: str
    project_id: str
    test_name: str
    description: Optional[str] = None

    variants: List[ABTestVariant] = Field(..., min_length=2, max_length=10)

    # Test parameters
    duration_days: int = Field(7, gt=0, le=90)
    metrics_to_track: List[MetricType] = Field(
        default_factory=lambda: [MetricType.MRR, MetricType.NDCG]
    )
    confidence_level: float = Field(0.95, gt=0.0, lt=1.0)


class CreateABTestResponse(BaseModel):
    """Response from A/B test creation"""

    test_id: UUID
    message: str = "A/B test created successfully"


class GetQualityMetricsRequest(BaseModel):
    """Request to get quality metrics"""

    tenant_id: str
    project_id: str
    period_start: datetime
    period_end: datetime


class GetQualityMetricsResponse(BaseModel):
    """Response with quality metrics"""

    quality_metrics: QualityMetrics
    alerts: List[QualityAlert] = Field(default_factory=list)
    message: str = "Quality metrics retrieved"


# ============================================================================
# Benchmark Models
# ============================================================================


class BenchmarkSuite(BaseModel):
    """
    A suite of benchmark queries and expected results.

    Used for consistent system evaluation.
    """

    suite_id: UUID
    suite_name: str
    description: Optional[str] = None

    # Benchmark queries
    queries: List[str] = Field(..., min_length=1)
    relevance_judgments: List[RelevanceJudgment] = Field(..., min_length=1)

    # Expected performance
    target_mrr: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_ndcg: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Metadata
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = Field("1.0")


class BenchmarkResult(BaseModel):
    """
    Result from running a benchmark suite.

    Compares current performance to targets.
    """

    benchmark_id: UUID
    suite_id: UUID
    tenant_id: str
    project_id: str

    # Results
    metrics: List[MetricScore]

    # Performance vs targets
    meets_targets: bool
    target_comparison: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Metric -> {target, actual, difference}"
    )

    # Execution
    execution_time_ms: int
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_by: Optional[str] = None


# ============================================================================
# Configuration
# ============================================================================


class EvaluationConfig(BaseModel):
    """
    Global configuration for evaluation system.

    Defines default thresholds and monitoring settings.
    """

    # Metric thresholds
    min_acceptable_mrr: float = Field(0.5, ge=0.0, le=1.0)
    min_acceptable_ndcg: float = Field(0.6, ge=0.0, le=1.0)
    min_acceptable_precision: float = Field(0.7, ge=0.0, le=1.0)

    # Performance thresholds
    max_acceptable_response_time_ms: int = Field(1000, gt=0)
    max_acceptable_error_rate: float = Field(0.05, ge=0.0, le=1.0)

    # Drift detection
    drift_detection_enabled: bool = Field(True)
    drift_check_frequency_hours: int = Field(24, gt=0)
    drift_p_value_threshold: float = Field(0.05, gt=0.0, lt=1.0)

    # A/B testing
    ab_testing_enabled: bool = Field(True)
    min_sample_size_per_variant: int = Field(100, gt=0)

    # Alerting
    alert_on_quality_degradation: bool = Field(True)
    alert_recipients: List[str] = Field(default_factory=list)


class UpdateEvaluationConfigRequest(BaseModel):
    """Request to update evaluation configuration"""

    config: EvaluationConfig


class GetEvaluationConfigResponse(BaseModel):
    """Response with evaluation configuration"""

    config: EvaluationConfig
    message: str = "Configuration retrieved"
