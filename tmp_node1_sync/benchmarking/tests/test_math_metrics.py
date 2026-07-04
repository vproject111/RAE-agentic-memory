"""
Unit tests for mathematical metrics module

Tests all three layers of mathematical metrics:
- Structure Metrics
- Dynamics Metrics
- Policy Metrics
"""

from datetime import datetime, timedelta

import numpy as np
import pytest

from benchmarking.math_metrics.base import (
    MemorySnapshot,
)
from benchmarking.math_metrics.dynamics_metrics import (
    CompressionFidelityRatio,
    MemoryDriftIndex,
    ReflectionGainScore,
    RetentionCurve,
)
from benchmarking.math_metrics.policy_metrics import (
    CostQualityFrontier,
    OptimalRetrievalRatio,
    ReflectionPolicyEfficiency,
)
from benchmarking.math_metrics.structure_metrics import (
    GraphConnectivityScore,
    GraphEntropyMetric,
    SemanticCoherenceScore,
    StructuralDriftMetric,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def simple_snapshot():
    """Create a simple memory snapshot for testing"""
    embeddings = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.9, 0.1],
        ],
        dtype=np.float32,
    )

    edges = [
        ("mem_1", "mem_2", 0.9),
        ("mem_3", "mem_4", 0.9),
        ("mem_1", "mem_3", 0.3),
    ]

    return MemorySnapshot(
        timestamp=datetime.now(),
        memory_ids=["mem_1", "mem_2", "mem_3", "mem_4"],
        embeddings=embeddings,
        graph_edges=edges,
    )


@pytest.fixture
def modified_snapshot(simple_snapshot):
    """Create a modified version of simple_snapshot for drift testing"""
    # Slightly different embeddings
    embeddings = np.array(
        [
            [0.95, 0.05, 0.0],
            [0.85, 0.15, 0.0],
            [0.05, 0.95, 0.0],
            [0.0, 0.85, 0.15],
        ],
        dtype=np.float32,
    )

    # Modified edges (one removed, one added)
    edges = [
        ("mem_1", "mem_2", 0.85),
        ("mem_3", "mem_4", 0.85),
        ("mem_2", "mem_3", 0.4),  # New edge
    ]

    return MemorySnapshot(
        timestamp=simple_snapshot.timestamp + timedelta(hours=1),
        memory_ids=["mem_1", "mem_2", "mem_3", "mem_4"],
        embeddings=embeddings,
        graph_edges=edges,
    )


# ============================================================================
# Base Tests
# ============================================================================


class TestMemorySnapshot:
    """Test MemorySnapshot class"""

    def test_snapshot_creation(self, simple_snapshot):
        """Test basic snapshot creation"""
        assert simple_snapshot.num_memories == 4
        assert simple_snapshot.embedding_dim == 3
        assert len(simple_snapshot.graph_edges) == 3

    def test_get_embedding(self, simple_snapshot):
        """Test embedding retrieval"""
        emb = simple_snapshot.get_embedding("mem_1")
        assert emb is not None
        np.testing.assert_array_almost_equal(emb, [1.0, 0.0, 0.0])

        # Non-existent memory
        assert simple_snapshot.get_embedding("mem_999") is None

    def test_snapshot_validation(self):
        """Test snapshot validation"""
        with pytest.raises(ValueError):
            MemorySnapshot(
                timestamp=datetime.now(),
                memory_ids=["mem_1", "mem_2"],
                embeddings=np.array([[1.0, 0.0]]),  # Mismatch!
            )


# ============================================================================
# Structure Metrics Tests
# ============================================================================


class TestGraphConnectivityScore:
    """Test Graph Connectivity Score metric"""

    def test_empty_graph(self):
        """Test with empty graph"""
        metric = GraphConnectivityScore()
        score = metric.calculate(num_nodes=0, edges=[])
        assert score == 0.0

    def test_disconnected_graph(self):
        """Test with disconnected graph"""
        metric = GraphConnectivityScore()
        score = metric.calculate(num_nodes=10, edges=[])
        assert score == 0.0

    def test_connected_graph(self):
        """Test with well-connected graph"""
        edges = [
            ("a", "b", 1.0),
            ("b", "c", 1.0),
            ("c", "d", 1.0),
            ("d", "a", 1.0),
        ]
        metric = GraphConnectivityScore()
        score = metric.calculate(num_nodes=4, edges=edges)

        # Average degree = 2*4/4 = 2
        # GCS = 2 / log(4) ≈ 1.44
        assert score > 1.0
        assert score < 2.0


class TestSemanticCoherenceScore:
    """Test Semantic Coherence Score metric"""

    def test_empty_edges(self, simple_snapshot):
        """Test with no edges"""
        snapshot = MemorySnapshot(
            timestamp=datetime.now(),
            memory_ids=simple_snapshot.memory_ids,
            embeddings=simple_snapshot.embeddings,
            graph_edges=[],  # No edges
        )
        metric = SemanticCoherenceScore()
        score = metric.calculate(snapshot)
        assert score == 0.0

    def test_coherent_edges(self, simple_snapshot):
        """Test with semantically coherent edges"""
        metric = SemanticCoherenceScore()
        score = metric.calculate(simple_snapshot)

        # Edges connect similar memories
        assert score > 0.5
        assert score <= 1.0


class TestGraphEntropyMetric:
    """Test Graph Entropy metric"""

    def test_empty_graph(self):
        """Test with empty graph"""
        metric = GraphEntropyMetric()
        entropy = metric.calculate(num_nodes=0, edges=[])
        assert entropy == 0.0

    def test_uniform_graph(self):
        """Test with uniform degree distribution (high entropy)"""
        # Complete graph where all nodes have same degree
        edges = [
            ("a", "b", 1.0),
            ("b", "c", 1.0),
            ("c", "a", 1.0),
        ]
        metric = GraphEntropyMetric()
        entropy = metric.calculate(num_nodes=3, edges=edges)
        assert entropy >= 0.0


class TestStructuralDriftMetric:
    """Test Structural Drift metric"""

    def test_identical_snapshots(self, simple_snapshot):
        """Test with identical snapshots (no drift)"""
        metric = StructuralDriftMetric()
        drift = metric.calculate(simple_snapshot, simple_snapshot)
        assert drift == 0.0

    def test_modified_snapshot(self, simple_snapshot, modified_snapshot):
        """Test with modified snapshot (some drift)"""
        metric = StructuralDriftMetric()
        drift = metric.calculate(simple_snapshot, modified_snapshot)

        # Should have some drift (edges changed)
        assert drift > 0.0
        assert drift < 1.0

        metadata = metric.get_metadata()
        assert "edges_added" in metadata
        assert "edges_removed" in metadata


# ============================================================================
# Dynamics Metrics Tests
# ============================================================================


class TestMemoryDriftIndex:
    """Test Memory Drift Index metric"""

    def test_identical_snapshots(self, simple_snapshot):
        """Test with identical snapshots (no drift)"""
        metric = MemoryDriftIndex()
        drift = metric.calculate(simple_snapshot, simple_snapshot)
        assert drift == pytest.approx(0.0, abs=1e-6)

    def test_drifted_snapshot(self, simple_snapshot, modified_snapshot):
        """Test with drifted snapshot"""
        metric = MemoryDriftIndex()
        drift = metric.calculate(simple_snapshot, modified_snapshot)

        # Should have small drift (embeddings slightly changed)
        assert drift > 0.0
        assert drift < 0.5


class TestRetentionCurve:
    """Test Retention Curve metric"""

    def test_insufficient_data(self):
        """Test with insufficient time points"""
        metric = RetentionCurve()
        auc = metric.calculate(time_points=[0.0], mrr_values=[1.0])
        assert auc == 0.0

    def test_perfect_retention(self):
        """Test with perfect retention"""
        metric = RetentionCurve()
        auc = metric.calculate(
            time_points=[0.0, 1.0, 2.0, 3.0],
            mrr_values=[1.0, 1.0, 1.0, 1.0],
        )
        assert auc == 1.0

    def test_linear_decay(self):
        """Test with linear decay"""
        metric = RetentionCurve()
        auc = metric.calculate(
            time_points=[0.0, 1.0, 2.0, 3.0],
            mrr_values=[1.0, 0.75, 0.5, 0.25],
        )

        # Linear decay should give AUC around 0.625
        assert 0.5 < auc < 0.8


class TestReflectionGainScore:
    """Test Reflection Gain Score metric"""

    def test_positive_gain(self):
        """Test with positive reflection gain"""
        metric = ReflectionGainScore()
        gain = metric.calculate(mrr_before=0.7, mrr_after=0.85, tokens_used=1000)

        assert gain == pytest.approx(0.15, abs=1e-6)
        metadata = metric.get_metadata()
        # gain_per_1k_tokens = (rg / tokens_used) * 1000 = (0.15 / 1000) * 1000 = 0.15
        assert metadata["gain_per_1k_tokens"] == pytest.approx(0.15, abs=1e-6)

    def test_negative_gain(self):
        """Test with negative gain (quality degradation)"""
        metric = ReflectionGainScore()
        gain = metric.calculate(mrr_before=0.8, mrr_after=0.7, tokens_used=500)

        assert gain == pytest.approx(-0.1, abs=1e-6)

    def test_zero_gain(self):
        """Test with no improvement"""
        metric = ReflectionGainScore()
        gain = metric.calculate(mrr_before=0.75, mrr_after=0.75, tokens_used=200)

        assert gain == 0.0


class TestCompressionFidelityRatio:
    """Test Compression Fidelity Ratio metric"""

    def test_perfect_compression(self):
        """Test with identical original and compressed"""
        original = [np.array([1.0, 0.0, 0.0], dtype=np.float32)]
        compressed = [np.array([1.0, 0.0, 0.0], dtype=np.float32)]

        metric = CompressionFidelityRatio()
        cfr = metric.calculate(original, compressed)

        assert cfr == pytest.approx(1.0, abs=0.01)

    def test_lossy_compression(self):
        """Test with lossy compression"""
        original = [
            np.array([1.0, 0.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0, 0.0], dtype=np.float32),
        ]
        compressed = [
            np.array([0.9, 0.1, 0.0], dtype=np.float32),
            np.array([0.1, 0.9, 0.0], dtype=np.float32),
        ]

        metric = CompressionFidelityRatio()
        cfr = metric.calculate(original, compressed)

        # Should be high but not perfect
        assert 0.8 < cfr < 1.0


# ============================================================================
# Policy Metrics Tests
# ============================================================================


class TestOptimalRetrievalRatio:
    """Test Optimal Retrieval Ratio metric"""

    def test_perfect_retrieval(self):
        """Test with perfect retrieval"""
        query_results = [
            {"expected": ["mem_1"], "retrieved": ["mem_1", "mem_2", "mem_3"]},
            {"expected": ["mem_2"], "retrieved": ["mem_2", "mem_1", "mem_3"]},
            {"expected": ["mem_3"], "retrieved": ["mem_3", "mem_4", "mem_5"]},
        ]

        metric = OptimalRetrievalRatio()
        orr = metric.calculate(query_results, k=5)

        assert orr == 1.0

    def test_partial_retrieval(self):
        """Test with partial retrieval"""
        query_results = [
            {"expected": ["mem_1"], "retrieved": ["mem_1", "mem_2"]},  # Hit
            {"expected": ["mem_2"], "retrieved": ["mem_3", "mem_4"]},  # Miss
            {"expected": ["mem_3"], "retrieved": ["mem_3", "mem_1"]},  # Hit
        ]

        metric = OptimalRetrievalRatio()
        orr = metric.calculate(query_results, k=5)

        assert orr == pytest.approx(2.0 / 3.0, abs=0.01)


class TestCostQualityFrontier:
    """Test Cost-Quality Frontier metric"""

    def test_efficient_reflection(self):
        """Test with efficient reflection"""
        metric = CostQualityFrontier()
        cqf = metric.calculate(reflection_gain=0.15, tokens_used=1000)

        # 0.15 / 1000 * 1000 = 0.15 (15% improvement per 1000 tokens)
        assert cqf == 0.15

    def test_inefficient_reflection(self):
        """Test with inefficient reflection"""
        metric = CostQualityFrontier()
        cqf = metric.calculate(reflection_gain=0.01, tokens_used=5000)

        # Small gain for high cost
        assert cqf == 0.002


class TestReflectionPolicyEfficiency:
    """Test Reflection Policy Efficiency metric"""

    def test_perfect_policy(self):
        """Test with perfect policy decisions"""
        events = [
            {"triggered": True, "gain": 0.1},  # TP
            {"triggered": False, "gain": 0.01},  # TN
            {"triggered": True, "gain": 0.08},  # TP
            {"triggered": False, "gain": 0.02},  # TN
        ]

        metric = ReflectionPolicyEfficiency()
        efficiency = metric.calculate(events, gain_threshold=0.05)

        assert efficiency == 1.0

    def test_mixed_policy(self):
        """Test with mixed policy decisions"""
        events = [
            {"triggered": True, "gain": 0.1},  # TP
            {"triggered": True, "gain": 0.01},  # FP
            {"triggered": False, "gain": 0.08},  # FN
            {"triggered": False, "gain": 0.02},  # TN
        ]

        metric = ReflectionPolicyEfficiency()
        efficiency = metric.calculate(events, gain_threshold=0.05)

        # 2 correct (TP + TN) out of 4
        assert efficiency == 0.5


# ============================================================================
# Integration Tests
# ============================================================================


class TestMetricsIntegration:
    """Test metrics working together"""

    def test_full_pipeline(self, simple_snapshot, modified_snapshot):
        """Test calculating all metrics on same data"""
        # Structure metrics
        gcs = GraphConnectivityScore()
        scs = SemanticCoherenceScore()
        entropy = GraphEntropyMetric()
        drift = StructuralDriftMetric()

        gcs_value = gcs.calculate(
            num_nodes=simple_snapshot.num_memories,
            edges=simple_snapshot.graph_edges,
        )
        scs_value = scs.calculate(simple_snapshot)
        entropy_value = entropy.calculate(
            num_nodes=simple_snapshot.num_memories,
            edges=simple_snapshot.graph_edges,
        )
        drift_value = drift.calculate(simple_snapshot, modified_snapshot)

        # All metrics should return valid values
        assert isinstance(gcs_value, float)
        assert isinstance(scs_value, float)
        assert isinstance(entropy_value, float)
        assert isinstance(drift_value, float)

        # Dynamics metrics
        mdi = MemoryDriftIndex()
        mdi_value = mdi.calculate(simple_snapshot, modified_snapshot)
        assert isinstance(mdi_value, float)

        # All metrics should have metadata
        assert len(gcs.get_metadata()) > 0
        assert len(scs.get_metadata()) > 0
        assert len(drift.get_metadata()) > 0
