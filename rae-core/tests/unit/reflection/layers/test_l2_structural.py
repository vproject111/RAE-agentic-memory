from rae_core.reflection.layers.l2_structural import (
    CostOptimizer,
    L2StructuralReflection,
    PatternDetector,
    RetrievalAnalyzer,
)


def test_retrieval_analyzer():
    analyzer = RetrievalAnalyzer()
    # Case 1: with sources, no log issue
    res = analyzer.analyze({"retrieved_sources": ["s1"], "answer_draft": "test"})
    assert res["retrieval_quality"] == 1.0
    assert len(res["missed_sources"]) == 0

    # Case 2: no sources
    res = analyzer.analyze({"retrieved_sources": [], "answer_draft": "test"})
    assert res["retrieval_quality"] == 0.0

    # Case 3: log in draft, but not in sources
    res = analyzer.analyze(
        {"retrieved_sources": ["s1"], "answer_draft": "Check the log file"}
    )
    assert res["retrieval_quality"] == 0.8
    assert "log_source" in res["missed_sources"]

    # Case 4: log in draft, and in sources
    res = analyzer.analyze(
        {"retrieved_sources": ["log_abc.txt"], "answer_draft": "Check the log file"}
    )
    assert res["retrieval_quality"] == 1.0
    assert len(res["missed_sources"]) == 0


def test_pattern_detector():
    detector = PatternDetector()
    # Case 1: No pattern
    res = detector.detect({"answer_draft": "normal flow"})
    assert len(res["insight_candidates"]) == 0

    # Case 2: Speed drop
    res = detector.detect({"answer_draft": "There is a drop in speed"})
    assert len(res["insight_candidates"]) == 1
    assert res["insight_candidates"][0]["pattern"] == "speed_drop_detected"


def test_cost_optimizer():
    optimizer = CostOptimizer()
    # Case 1: optimal
    res = optimizer.optimize(
        {"answer_draft": "x" * 100, "retrieved_sources": ["s1"] * 5}
    )
    assert res["optimization_suggestion"] == "optimal"

    # Case 2: too many sources
    res = optimizer.optimize(
        {"answer_draft": "x" * 100, "retrieved_sources": ["s1"] * 21}
    )
    assert res["optimization_suggestion"] == "decrease_top_k"

    # Case 3: too little content/sources
    res = optimizer.optimize({"answer_draft": "x" * 10, "retrieved_sources": ["s1"]})
    assert res["optimization_suggestion"] == "increase_top_k"


def test_l2_structural_reflection():
    l2 = L2StructuralReflection()
    payload = {"retrieved_sources": ["s1"], "answer_draft": "test"}
    res = l2.reflect(payload)
    assert "retrieval_quality" in res
    assert "missed_sources" in res
    assert "insight_candidates" in res
    assert "optimization_suggestion" in res
