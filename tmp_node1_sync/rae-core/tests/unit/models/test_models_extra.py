from rae_core.models.context import ContextMetadata, ContextWindow, WorkingContext
from rae_core.models.scoring import QualityMetrics
from rae_core.models.search import ScoringWeights


def test_quality_metrics_compute_overall():
    m = QualityMetrics(coherence=0.8, completeness=0.7, accuracy=0.9, relevance=0.6)
    res = m.compute_overall()
    assert 0.0 <= res <= 1.0
    assert m.overall_quality == res


def test_context_models():
    w = ContextWindow()
    assert w.max_tokens == 4096

    ctx = WorkingContext(tenant_id="t1")
    assert ctx.tenant_id == "t1"

    m = ContextMetadata()
    assert m.total_items == 0


def test_scoring_weights_validate_sum():
    w = ScoringWeights(similarity=0.4, importance=0.3, recency=0.3)
    assert w.validate_sum() is True

    w2 = ScoringWeights(similarity=0.1, importance=0.1, recency=0.1)
    assert w2.validate_sum() is False
