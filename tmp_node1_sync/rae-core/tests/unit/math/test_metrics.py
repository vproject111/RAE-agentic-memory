from rae_core.math.quality_metrics import (
    EntropyMetric,
    QualityScorer,
    TextCoherenceMetric,
)


def test_text_coherence_metric():
    metric = TextCoherenceMetric()

    # Test empty
    res = metric.compute("")
    assert res.score == 0.0

    # Test short/garbage
    res = metric.compute("a b")
    assert res.score == 0.2

    # Test good sentence
    res = metric.compute("This is a complete, well-formed sentence.")
    assert res.score > 0.5
    assert res.metadata["has_punctuation"] is True
    assert res.metadata["is_capitalized"] is True


def test_entropy_metric():
    metric = EntropyMetric()

    # Low entropy (repetitive)
    res_low = metric.compute("test test test test")
    assert res_low.score == 0.0  # Normalized 0 because only 1 unique token

    # High entropy (unique words)
    res_high = metric.compute("alpha beta gamma delta")
    assert res_high.score == 1.0  # Max entropy for unique tokens

    # Mixed
    res_mid = metric.compute("a b a c")
    assert 0.0 < res_mid.score < 1.0


def test_quality_scorer_aggregation():
    m1 = TextCoherenceMetric()
    m2 = EntropyMetric()

    # Equal weights
    scorer = QualityScorer([m1, m2])

    # "test test test" -> Coherence: Low, Entropy: Low
    res = scorer.evaluate("test test test")
    assert res.score < 0.5

    # "This is a diverse sentence." -> Coherence: High, Entropy: High
    res = scorer.evaluate("This is a diverse sentence.")
    assert res.score > 0.6
    assert "text_coherence" in res.metadata["components"]
    assert "shannon_entropy" in res.metadata["components"]


def test_scorer_custom_weights():
    m1 = TextCoherenceMetric()
    m2 = EntropyMetric()

    # Only care about entropy
    scorer = QualityScorer(
        [m1, m2], weights={"shannon_entropy": 1.0, "text_coherence": 0.0}
    )

    res = scorer.evaluate("a b c d")
    # Entropy is 1.0, Coherence is ~0.2 (too short)
    # Result should be 1.0 because Coherence weight is 0
    assert res.score == 1.0
