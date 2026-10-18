"""Unit tests for DeterministicReflectionEngine (Tier 1 Reflection)."""

import pytest

from rae_core.reflection.deterministic import DeterministicReflectionEngine


def test_deterministic_reflection_tokenization():
    engine = DeterministicReflectionEngine()
    tokens = engine._tokenize("The quick brown fox jumps over the lazy dog and ignores the stop words.")
    assert "quick" in tokens
    assert "brown" in tokens
    assert "the" not in tokens
    assert "and" not in tokens


def test_deterministic_reflection_jaccard():
    engine = DeterministicReflectionEngine()
    set_a = {"database", "postgres", "timeout"}
    set_b = {"database", "postgres", "error"}
    sim = engine.compute_jaccard_similarity(set_a, set_b)
    # intersection: {database, postgres} (2), union: {database, postgres, timeout, error} (4) -> 0.5
    assert sim == 0.5


def test_deterministic_reflection_cosine():
    engine = DeterministicReflectionEngine()
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]
    assert pytest.approx(engine.compute_cosine_similarity(vec_a, vec_b)) == 1.0
    assert pytest.approx(engine.compute_cosine_similarity(vec_a, vec_c)) == 0.0


def test_deterministic_concept_graph():
    engine = DeterministicReflectionEngine()
    memories = [
        {"content": "Database timeout occurred on PostgreSQL node."},
        {"content": "PostgreSQL database connection pool exhausted."},
        {"content": "Vector index sync failed with timeout."},
    ]
    graph = engine.extract_concept_graph(memories)
    assert "database" in graph["top_concepts"] or "postgresql" in graph["top_concepts"]
    assert graph["vocabulary_size"] > 0


def test_deterministic_clustering_and_consolidation():
    engine = DeterministicReflectionEngine(similarity_threshold=0.3)
    memories = [
        {
            "id": "mem-1",
            "content": "Postgres connection pool max size reached.",
            "importance": 0.6,
            "tags": ["postgres", "db"],
            "metadata": {"witness_count": 2},
        },
        {
            "id": "mem-2",
            "content": "Postgres connection pool overflow error.",
            "importance": 0.7,
            "tags": ["postgres", "error"],
            "metadata": {"witness_count": 3},
        },
        {
            "id": "mem-3",
            "content": "Frontend UI theme changed to dark mode.",
            "importance": 0.4,
            "tags": ["ui", "theme"],
            "metadata": {"witness_count": 1},
        },
    ]

    clusters = engine.cluster_memories(memories)
    # Should have at least 2 distinct clusters (postgres cluster + frontend cluster)
    assert len(clusters) >= 2

    # Consolidate first cluster
    consolidated = engine.consolidate_cluster(clusters[0])
    assert "canonical_memory_id" in consolidated
    assert consolidated["importance"] >= 0.6
    assert consolidated["witness_count"] >= 1
    assert "Consolidated Insight" in consolidated["content"]


def test_generate_reflection_from_trace():
    engine = DeterministicReflectionEngine()
    events = [
        {"event_type": "tool_call", "tags": ["db_query"]},
        {"event_type": "error_event", "tags": ["timeout"]},
    ]
    error = {"error_message": "Connection reset by peer", "error_category": "network_error"}

    result = engine.generate_reflection_from_trace(
        task_goal="Fetch customer record",
        task_description="Query PostgreSQL",
        events=events,
        outcome="failure",
        error=error,
    )

    assert "Execution failed" in result["reflection"]
    assert "network_error" in result["tags"]
    assert result["importance"] >= 0.8
    assert result["confidence"] >= 0.85
    assert result["method"] == "deterministic_math_tier1"
