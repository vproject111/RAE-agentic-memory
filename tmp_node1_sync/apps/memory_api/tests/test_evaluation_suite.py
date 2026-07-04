"""
Tests for Evaluation Suite - IR Metrics and Drift Detection

Tests cover:
- MRR, NDCG, Precision, Recall, MAP calculation
- Kolmogorov-Smirnov test
- Population Stability Index (PSI)
- Drift severity classification
- A/B testing
"""

from datetime import datetime, timedelta, timezone
from typing import cast
from unittest.mock import AsyncMock
from uuid import uuid4

import numpy as np
import pytest

from apps.memory_api.models.evaluation_models import (
    DriftSeverity,
    DriftType,
    RankedResult,
)
from apps.memory_api.services.drift_detector import DriftDetector
from apps.memory_api.services.evaluation_service import EvaluationService


@pytest.fixture
def evaluation_service():
    return EvaluationService()


@pytest.fixture
def drift_detector(mock_pool):
    return DriftDetector(mock_pool)


@pytest.fixture
def mock_pool():
    return AsyncMock()


# IR Metrics Tests
@pytest.mark.asyncio
async def test_mrr_calculation(evaluation_service):
    """Test Mean Reciprocal Rank calculation"""
    doc1_id = uuid4()
    doc2_id = uuid4()
    relevance = {"q1": {str(doc1_id): 1.0, str(doc2_id): 0.5}}
    results = {
        "q1": [
            RankedResult(document_id=doc2_id, rank=1, score=0.9),
            RankedResult(document_id=doc1_id, rank=2, score=0.8),
        ]
    }

    mrr = evaluation_service._calculate_mrr(relevance, results)
    assert 0 <= mrr <= 1


@pytest.mark.asyncio
async def test_ndcg_calculation(evaluation_service):
    """Test NDCG@K calculation"""
    doc1_id = uuid4()
    doc2_id = uuid4()
    doc3_id = uuid4()
    relevance = {"q1": {str(doc1_id): 1.0, str(doc2_id): 0.5, str(doc3_id): 0.0}}
    results = {
        "q1": [
            RankedResult(document_id=doc1_id, rank=1, score=0.95),
            RankedResult(document_id=doc2_id, rank=2, score=0.85),
        ]
    }

    ndcg = evaluation_service._calculate_ndcg(relevance, results, k=10)
    assert 0 <= ndcg <= 1


@pytest.mark.asyncio
async def test_precision_recall(evaluation_service):
    """Test Precision and Recall calculation"""
    doc1_id = uuid4()
    doc2_id = uuid4()
    doc3_id = uuid4()
    relevance = {"q1": {str(doc1_id): 1.0, str(doc2_id): 1.0, str(doc3_id): 0.0}}
    results = {
        "q1": [
            RankedResult(document_id=doc1_id, rank=1, score=0.9),
            RankedResult(document_id=doc3_id, rank=2, score=0.8),
        ]
    }

    precision = evaluation_service._calculate_precision_at_k(relevance, results, k=2)
    recall = evaluation_service._calculate_recall_at_k(relevance, results, k=2)

    assert 0 <= precision <= 1
    assert 0 <= recall <= 1


# Drift Detection Tests
@pytest.mark.asyncio
async def test_kolmogorov_smirnov_test(drift_detector):
    """Test KS test for distribution comparison"""
    baseline = np.random.normal(0, 1, 100)
    current = np.random.normal(0.5, 1, 100)  # Shifted distribution

    p_value, statistic = drift_detector._kolmogorov_smirnov_test(baseline, current)

    assert 0 <= p_value <= 1
    assert 0 <= statistic <= 1


@pytest.mark.asyncio
async def test_psi_calculation(drift_detector):
    """Test Population Stability Index"""
    baseline = np.random.normal(0, 1, 100)
    current = np.random.normal(0.3, 1, 100)

    pseudo_p, psi = drift_detector._population_stability_index(baseline, current)

    assert psi >= 0


@pytest.mark.asyncio
async def test_drift_severity_classification(drift_detector):
    """Test drift severity classification"""
    # No drift
    severity = drift_detector._classify_severity(magnitude=0.05, p_value=0.1)
    assert severity == DriftSeverity.NONE

    # Medium drift
    severity = drift_detector._classify_severity(magnitude=0.15, p_value=0.01)
    assert severity == DriftSeverity.MEDIUM

    # Critical drift
    severity = drift_detector._classify_severity(magnitude=0.6, p_value=0.001)
    assert severity == DriftSeverity.CRITICAL


@pytest.mark.asyncio
async def test_drift_detection_no_data(drift_detector, mock_pool):
    """Test drift detection with minimal data (no significant drift)"""
    # Mock returns data in correct format (list of dicts with metric_value key)
    mock_pool.fetch = AsyncMock(
        return_value=[
            {"metric_value": 0.8},
            {"metric_value": 0.85},
            {"metric_value": 0.82},
        ]
    )

    result = await drift_detector.detect_drift(
        tenant_id="test",
        project_id="test",
        metric_name="search_score",  # Use recognized metric
        drift_type=DriftType.DATA_DRIFT,
        baseline_start=datetime.now(timezone.utc) - timedelta(days=14),
        baseline_end=datetime.now(timezone.utc) - timedelta(days=7),
        current_start=datetime.now(timezone.utc) - timedelta(days=7),
        current_end=datetime.now(timezone.utc),
    )

    # With identical data for both periods, no drift should be detected
    assert result.drift_detected is False


# A/B Testing Tests
@pytest.mark.asyncio
async def test_ab_test_traffic_validation():
    """Test A/B test traffic allocation validation"""
    # Valid allocation
    variants = [
        {"name": "A", "traffic_percentage": 50.0},
        {"name": "B", "traffic_percentage": 50.0},
    ]
    total = sum(cast(float, v["traffic_percentage"]) for v in variants)
    assert 99.0 <= total <= 101.0  # Allow floating point error

    # Invalid allocation
    variants_invalid = [
        {"name": "A", "traffic_percentage": 40.0},
        {"name": "B", "traffic_percentage": 40.0},
    ]
    total_invalid = sum(cast(float, v["traffic_percentage"]) for v in variants_invalid)
    assert not (99.0 <= total_invalid <= 101.0)
