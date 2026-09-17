"""Unit tests for QueryClassifier (Iteration 5)."""

from __future__ import annotations

import time
from uuid import uuid4

from rae_core.evaluation.golden_queries import QueryCategory
from rae_core.search.classifier import QueryClassifier


def test_classifier_exact_identifiers():
    classifier = QueryClassifier()

    # UUID
    uid = str(uuid4())
    res = classifier.classify(uid)
    assert res.category == QueryCategory.EXACT_IDENTIFIER
    assert res.confidence >= 0.95

    # CVE
    res = classifier.classify("What is the fix for CVE-2026-12345?")
    assert res.category == QueryCategory.EXACT_IDENTIFIER
    assert res.matched_rule == "cve_pattern"

    # Ticket
    res = classifier.classify("Status of RAE-4091 issue")
    assert res.category == QueryCategory.EXACT_IDENTIFIER
    assert res.matched_rule == "ticket_pattern"

    # Git hash
    res = classifier.classify("595fedf2")
    assert res.category == QueryCategory.EXACT_IDENTIFIER


def test_classifier_code_symbols():
    classifier = QueryClassifier()

    # Class name (CamelCase)
    res = classifier.classify("Where is HybridSearchEngine declared?")
    assert res.category == QueryCategory.CODE_SYMBOL

    # Method call
    res = classifier.classify("Implementation of search_evidence()")
    assert res.category == QueryCategory.CODE_SYMBOL

    # File path / extension
    res = classifier.classify("Inspect config/math_controller.yaml")
    assert res.category == QueryCategory.CODE_SYMBOL


def test_classifier_graph_relations():
    classifier = QueryClassifier()

    res = classifier.classify("kto wywołuje tę funkcję?")
    assert res.category == QueryCategory.GRAPH_RELATION

    res = classifier.classify("What depends on LogicGateway?")
    assert res.category == QueryCategory.GRAPH_RELATION

    res = classifier.classify("who calls the reranker in search engine")
    assert res.category == QueryCategory.GRAPH_RELATION


def test_classifier_historical_decisions():
    classifier = QueryClassifier()

    res = classifier.classify("dlaczego zmieniono profil na cheap?")
    assert res.category == QueryCategory.HISTORICAL_DECISION

    res = classifier.classify("history of changes in emerald reranker ADR")
    assert res.category == QueryCategory.HISTORICAL_DECISION


def test_classifier_latency_budget():
    """DoD: Classifier must execute in under 0.5ms (budget < 1.5ms)."""
    classifier = QueryClassifier()
    queries = [
        "CVE-2026-9999",
        "Where is AdaptiveSearchEngine defined?",
        "who calls search_evidence()",
        "how does context enricher work",
        "why did we change the math controller",
    ] * 200

    start = time.perf_counter()
    for q in queries:
        classifier.classify(q)
    total_time = time.perf_counter() - start

    avg_ms = (total_time / len(queries)) * 1000
    assert avg_ms < 0.5, f"Classifier too slow: {avg_ms:.4f} ms/query"
