from rae_core.math.quality_metrics import (
    CompletenessMetric,
    EntropyMetric,
    IMetric,
    MetricResult,
    QualityScorer,
    RelevanceMetric,
    TextCoherenceMetric,
)


class DummyMetric(IMetric):
    @property
    def name(self):
        return "dummy"

    def compute(self, content, context=None):
        return MetricResult(1.0, "dummy")


def test_abstract_metric():
    m = DummyMetric()
    assert m.name == "dummy"
    assert m.compute("test").score == 1.0


def test_entropy_metric_extra():
    metric = EntropyMetric()

    # Test list input
    res = metric.compute(["one", "two", "one"])
    assert res.score > 0

    # Test empty input
    res = metric.compute([])
    assert res.score == 0.0

    # Test single unique token
    res = metric.compute(["one", "one"])
    assert res.score == 0.0


def test_relevance_metric_extra():
    metric = RelevanceMetric()

    # Test no context
    res = metric.compute("test")
    assert res.score == 0.0
    assert res.metadata["reason"] == "no_query_context"

    # Test empty text words
    res = metric.compute("", {"query": "test"})
    assert res.score == 0.0

    # Test empty query words
    res = metric.compute("test", {"query": ""})
    assert res.score == 0.0

    # Test successful overlap
    res = metric.compute("hello world", {"query": "hello"})
    assert res.score == 1.0
    assert res.metadata["overlap_count"] == 1


def test_completeness_metric_extra():
    metric = CompletenessMetric()

    # Test with object having __dict__
    class Obj:
        def __init__(self):
            self.content = "test"
            self.created_at = "now"
            self.tags = ["tag1"]

    res = metric.compute(Obj())
    assert res.score > 0.5

    # Test with object having model_dump (mock Pydantic)
    class PydanticObj:
        def model_dump(self):
            return {"content": "test", "created_at": "now"}

    res = metric.compute(PydanticObj())
    assert res.score > 0.5

    # Test with invalid content type
    res = metric.compute(123)
    assert res.score == 0.0
    assert res.metadata["reason"] == "invalid_content_type"


def test_quality_scorer_extra():
    m1 = TextCoherenceMetric()
    m2 = EntropyMetric()

    # Test weights normalization
    scorer = QualityScorer(
        [m1, m2], weights={"text_coherence": 2.0, "shannon_entropy": 2.0}
    )
    assert scorer.weights["text_coherence"] == 0.5

    # Test evaluate
    res = scorer.evaluate("This is a coherent sentence with information.")
    assert 0.0 <= res.score <= 1.0
    assert "text_coherence" in res.metadata["components"]

    # Test with 0 weight
    scorer = QualityScorer(
        [m1, m2], weights={"text_coherence": 1.0, "shannon_entropy": 0.0}
    )
    res = scorer.evaluate("test")
    assert "shannon_entropy" not in res.metadata["components"]

    # Test with total weight 0
    scorer = QualityScorer(
        [m1, m2], weights={"text_coherence": 0.0, "shannon_entropy": 0.0}
    )
    res = scorer.evaluate("test")
    assert res.score == 0.0


def test_text_coherence_metric_extra():
    metric = TextCoherenceMetric()

    # Test non-string input (Line 53 part 1)
    res = metric.compute(None)
    assert res.score == 0.0
    assert res.metadata["reason"] == "empty_content"

    res = metric.compute(123)
    assert res.score == 0.0

    # Test whitespace string (Line 53 part 2)
    res = metric.compute("   ")
    assert res.score == 0.0
    assert res.metadata["reason"] == "empty_content"

    # Test exactly 3 words (Line 69 boundary)
    # "one two three" -> 3 words. word_count < 3 is False.
    res = metric.compute("one two three")
    # Score starts 0.5.
    # word_count > 5 is False (3 words).
    # has_punctuation False.
    # capitalized False.
    # Result 0.5.
    assert res.score == 0.5
    assert res.metadata["word_count"] == 3

    # Test short content (< 3 words)
    res = metric.compute("Too short")
    assert res.score == 0.2
    assert res.metadata["reason"] == "too_short"
