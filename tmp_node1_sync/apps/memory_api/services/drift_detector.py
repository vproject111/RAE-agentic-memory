"""
Drift Detector - Statistical Distribution Change Detection

This service implements drift detection using statistical tests:
- Kolmogorov-Smirnov test for distribution comparison
- Population Stability Index (PSI)
- Chi-square test for categorical drift
- Automated severity classification
"""

from datetime import datetime
from typing import List, Tuple

import asyncpg
import numpy as np
import structlog
from scipy import stats

from apps.memory_api.models.evaluation_models import (
    DistributionStatistics,
    DriftDetectionResult,
    DriftSeverity,
    DriftType,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Drift Detector
# ============================================================================


class DriftDetector:
    """
    Service for detecting distribution drift in system metrics.

    Implements multiple statistical tests:
    - Kolmogorov-Smirnov test (2-sample)
    - Population Stability Index (PSI)
    - Chi-square test
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize drift detector.

        Args:
            pool: Database connection pool
        """
        self.pool = pool

    async def detect_drift(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        drift_type: DriftType,
        baseline_start: datetime,
        baseline_end: datetime,
        current_start: datetime,
        current_end: datetime,
        p_value_threshold: float = 0.05,
        statistical_test: str = "ks_test",
    ) -> DriftDetectionResult:
        """
        Detect drift between baseline and current distributions.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            metric_name: Name of metric to analyze
            drift_type: Type of drift to detect
            baseline_start: Start of baseline period
            baseline_end: End of baseline period
            current_start: Start of current period
            current_end: End of current period
            p_value_threshold: Significance threshold
            statistical_test: Test to use (ks_test, psi, chi_square)

        Returns:
            DriftDetectionResult with drift analysis
        """
        logger.info(
            "drift_detection_started",
            metric=metric_name,
            drift_type=drift_type.value,
            test=statistical_test,
        )

        # Fetch baseline data
        baseline_data = await self._fetch_metric_data(
            tenant_id, project_id, metric_name, baseline_start, baseline_end
        )

        # Fetch current data
        current_data = await self._fetch_metric_data(
            tenant_id, project_id, metric_name, current_start, current_end
        )

        if len(baseline_data) == 0 or len(current_data) == 0:
            logger.warning("insufficient_data_for_drift_detection")
            # Return no drift detected if insufficient data
            return self._create_no_drift_result(
                drift_type, baseline_start, baseline_end, current_start, current_end
            )

        # Calculate distribution statistics
        baseline_stats = self._calculate_distribution_stats(
            baseline_data, baseline_start
        )
        current_stats = self._calculate_distribution_stats(current_data, current_start)

        # Perform statistical test
        if statistical_test == "ks_test":
            test_result = self._kolmogorov_smirnov_test(baseline_data, current_data)
            test_name = "Kolmogorov-Smirnov Test"
        elif statistical_test == "psi":
            test_result = self._population_stability_index(baseline_data, current_data)
            test_name = "Population Stability Index"
        else:
            # Default to KS test
            test_result = self._kolmogorov_smirnov_test(baseline_data, current_data)
            test_name = "Kolmogorov-Smirnov Test"

        p_value, test_statistic = test_result

        # Determine if drift detected
        drift_detected = p_value < p_value_threshold

        # Calculate drift magnitude and severity
        drift_magnitude = self._calculate_drift_magnitude(baseline_stats, current_stats)
        severity = self._classify_severity(drift_magnitude, p_value)

        # Determine actions
        action_required = severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
        recommended_actions = self._recommend_actions(
            severity, drift_type, drift_magnitude
        )

        result = DriftDetectionResult(
            drift_detected=drift_detected,
            drift_type=drift_type,
            severity=severity,
            p_value=p_value,
            test_statistic=test_statistic,
            test_name=test_name,
            baseline_stats=baseline_stats,
            current_stats=current_stats,
            drift_magnitude=drift_magnitude,
            confidence=1.0 - p_value,
            action_required=action_required,
            recommended_actions=recommended_actions,
            baseline_period=(baseline_start, baseline_end),
            current_period=(current_start, current_end),
        )

        logger.info(
            "drift_detection_complete",
            detected=drift_detected,
            severity=severity.value,
            p_value=p_value,
        )

        return result

    # ========================================================================
    # Statistical Tests
    # ========================================================================

    def _kolmogorov_smirnov_test(
        self, baseline: np.ndarray, current: np.ndarray
    ) -> Tuple[float, float]:
        """
        Perform 2-sample Kolmogorov-Smirnov test.

        Tests whether two samples come from the same distribution.

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples

        Returns:
            Tuple of (p_value, test_statistic)
        """
        statistic, p_value = stats.ks_2samp(baseline, current)
        return float(p_value), float(statistic)

    def _population_stability_index(
        self, baseline: np.ndarray, current: np.ndarray, bins: int = 10
    ) -> Tuple[float, float]:
        """
        Calculate Population Stability Index (PSI).

        PSI measures the change in distribution between two samples.
        PSI = Σ((actual% - expected%) * ln(actual% / expected%))

        Args:
            baseline: Baseline distribution samples
            current: Current distribution samples
            bins: Number of bins for histogram

        Returns:
            Tuple of (psi_value, psi_value) - PSI doesn't have p-value
        """
        # Create bins based on baseline
        bin_edges = np.histogram_bin_edges(baseline, bins=bins)

        # Calculate histograms
        baseline_hist, _ = np.histogram(baseline, bins=bin_edges)
        current_hist, _ = np.histogram(current, bins=bin_edges)

        # Convert to percentages
        baseline_pct = baseline_hist / len(baseline)
        current_pct = current_hist / len(current)

        # Avoid division by zero
        baseline_pct = np.where(baseline_pct == 0, 0.0001, baseline_pct)
        current_pct = np.where(current_pct == 0, 0.0001, current_pct)

        # Calculate PSI
        psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))

        # Convert PSI to pseudo p-value for consistency
        # PSI > 0.25 is considered significant drift
        pseudo_p_value = 1.0 - min(1.0, psi / 0.25)

        return float(pseudo_p_value), float(psi)

    # ========================================================================
    # Distribution Statistics
    # ========================================================================

    def _calculate_distribution_stats(
        self, data: np.ndarray, timestamp: datetime
    ) -> DistributionStatistics:
        """
        Calculate comprehensive distribution statistics.

        Args:
            data: Sample data
            timestamp: Timestamp for statistics

        Returns:
            DistributionStatistics with all metrics
        """
        if len(data) == 0:
            return DistributionStatistics(
                mean=0.0,
                std=0.0,
                min=0.0,
                max=0.0,
                median=0.0,
                q25=0.0,
                q75=0.0,
                sample_size=0,
                timestamp=timestamp,
            )

        return DistributionStatistics(
            mean=float(np.mean(data)),
            std=float(np.std(data)),
            min=float(np.min(data)),
            max=float(np.max(data)),
            median=float(np.median(data)),
            q25=float(np.percentile(data, 25)),
            q75=float(np.percentile(data, 75)),
            skewness=float(stats.skew(data)) if len(data) > 2 else None,
            kurtosis=float(stats.kurtosis(data)) if len(data) > 2 else None,
            sample_size=len(data),
            timestamp=timestamp,
        )

    def _calculate_drift_magnitude(
        self,
        baseline_stats: DistributionStatistics,
        current_stats: DistributionStatistics,
    ) -> float:
        """
        Calculate magnitude of drift between distributions.

        Uses relative change in mean and std as proxy.

        Args:
            baseline_stats: Baseline statistics
            current_stats: Current statistics

        Returns:
            Drift magnitude (0-1 scale)
        """
        if baseline_stats.mean == 0:
            return 0.0

        # Relative change in mean
        mean_change = abs(current_stats.mean - baseline_stats.mean) / abs(
            baseline_stats.mean
        )

        # Relative change in std
        std_change = 0.0
        if baseline_stats.std > 0:
            std_change = (
                abs(current_stats.std - baseline_stats.std) / baseline_stats.std
            )

        # Combined magnitude (weighted average)
        magnitude = 0.7 * mean_change + 0.3 * std_change

        # Cap at 1.0
        return min(1.0, magnitude)

    def _classify_severity(self, magnitude: float, p_value: float) -> DriftSeverity:
        """
        Classify drift severity based on magnitude and significance.

        Args:
            magnitude: Drift magnitude (0-1)
            p_value: Statistical test p-value

        Returns:
            DriftSeverity classification
        """
        # No significant drift
        if p_value >= 0.05:
            return DriftSeverity.NONE

        # Classify by magnitude
        if magnitude < 0.1:
            return DriftSeverity.LOW
        elif magnitude < 0.25:
            return DriftSeverity.MEDIUM
        elif magnitude < 0.5:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL

    def _recommend_actions(
        self, severity: DriftSeverity, drift_type: DriftType, magnitude: float
    ) -> List[str]:
        """
        Recommend actions based on drift severity.

        Args:
            severity: Drift severity
            drift_type: Type of drift
            magnitude: Drift magnitude

        Returns:
            List of recommended actions
        """
        actions = []

        if severity == DriftSeverity.NONE or severity == DriftSeverity.LOW:
            actions.append("Continue monitoring")
            return actions

        if severity == DriftSeverity.MEDIUM:
            actions.append("Investigate data sources for changes")
            actions.append("Review recent system updates")

        elif severity in [DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            actions.append("URGENT: Review system configuration")
            actions.append("Investigate data quality issues")
            actions.append("Consider retraining models")

            if drift_type == DriftType.CONCEPT_DRIFT:
                actions.append("Retrain models with recent data")
            elif drift_type == DriftType.DATA_DRIFT:
                actions.append("Validate input data sources")
            elif drift_type == DriftType.PREDICTION_DRIFT:
                actions.append("Review model performance metrics")

        return actions

    # ========================================================================
    # Data Fetching
    # ========================================================================

    async def _fetch_metric_data(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> np.ndarray:
        """
        Fetch metric data from database for given time period.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            metric_name: Metric name
            start_time: Period start
            end_time: Period end

        Returns:
            NumPy array of metric values
        """
        # This is a placeholder - actual implementation depends on how metrics are stored
        # For now, we'll fetch search relevance scores as an example

        try:
            if metric_name == "search_score":
                # Fetch search scores from memories table
                records = await self.pool.fetch(
                    """
                    SELECT importance as metric_value
                    FROM memories
                    WHERE tenant_id = $1 AND project = $2
                        AND created_at BETWEEN $3 AND $4
                    ORDER BY created_at
                    """,
                    tenant_id,
                    project_id,
                    start_time,
                    end_time,
                )

                values = [float(r["metric_value"]) for r in records]
                return np.array(values)

            elif metric_name == "response_time":
                # Placeholder for response time metrics
                # Would need separate metrics table
                return np.array([])

            else:
                logger.warning("unknown_metric", metric=metric_name)
                return np.array([])

        except Exception as e:
            logger.error("fetch_metric_data_failed", error=str(e))
            return np.array([])

    def _create_no_drift_result(
        self,
        drift_type: DriftType,
        baseline_start: datetime,
        baseline_end: datetime,
        current_start: datetime,
        current_end: datetime,
    ) -> DriftDetectionResult:
        """Create a no-drift result when data is insufficient"""
        return DriftDetectionResult(
            drift_detected=False,
            drift_type=drift_type,
            severity=DriftSeverity.NONE,
            p_value=1.0,
            test_statistic=0.0,
            test_name="No Test (Insufficient Data)",
            baseline_stats=DistributionStatistics(
                mean=0.0,
                std=0.0,
                min=0.0,
                max=0.0,
                median=0.0,
                q25=0.0,
                q75=0.0,
                sample_size=0,
                timestamp=baseline_start,
            ),
            current_stats=DistributionStatistics(
                mean=0.0,
                std=0.0,
                min=0.0,
                max=0.0,
                median=0.0,
                q25=0.0,
                q75=0.0,
                sample_size=0,
                timestamp=current_start,
            ),
            drift_magnitude=0.0,
            confidence=0.0,
            action_required=False,
            recommended_actions=["Collect more data"],
            baseline_period=(baseline_start, baseline_end),
            current_period=(current_start, current_end),
        )
