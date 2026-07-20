from unittest.mock import MagicMock

from rae_core.reflection.layers.l1_operational import (
    ContractEnforcer,
    EvidenceVerifier,
    L1OperationalReflection,
    UncertaintyEstimator,
)


def test_evidence_verifier():
    verifier = EvidenceVerifier()
    # Case 1: with sources
    res = verifier.verify({"retrieved_sources": ["s1"], "answer_draft": "test"})
    assert res["coverage_ratio"] == 1.0

    # Case 2: no sources, short draft
    res = verifier.verify({"retrieved_sources": [], "answer_draft": "test"})
    assert res["coverage_ratio"] == 0.0

    # Case 3: no sources, long draft
    res = verifier.verify(
        {"retrieved_sources": [], "answer_draft": "this is a very long draft"}
    )
    assert res["coverage_ratio"] == 0.0

    # Case 4: default
    res = verifier.verify({})
    assert res["coverage_ratio"] == 0.0


def test_contract_enforcer():
    enforcer = ContractEnforcer()
    res = enforcer.enforce({})
    assert res["contract_status"] == "ok"


def test_uncertainty_estimator():
    estimator = UncertaintyEstimator()
    # Case 1: no uncertainty
    res = estimator.estimate({"answer_draft": "certain", "retrieved_sources": ["s1"]})
    assert res["uncertainty_level"] == 0.0

    # Case 2: "probably"
    res = estimator.estimate({"answer_draft": "Probably", "retrieved_sources": ["s1"]})
    assert res["uncertainty_level"] == 0.3

    # Case 3: "maybe"
    res = estimator.estimate({"answer_draft": "maybe", "retrieved_sources": ["s1"]})
    assert res["uncertainty_level"] == 0.3

    # Case 4: no sources
    res = estimator.estimate({"answer_draft": "certain", "retrieved_sources": []})
    assert res["uncertainty_level"] == 0.5

    # Case 5: "maybe" and no sources
    res = estimator.estimate({"answer_draft": "maybe", "retrieved_sources": []})
    assert res["uncertainty_level"] == 0.8

    # Case 6: clamp to 1.0
    # To get 1.0, we need uncertainty > 1.0.
    # Current max is 0.3 + 0.5 = 0.8.
    # Wait, the code says uncertainty = 0.0. if "probably" or "maybe" -> 0.3. if not sources -> +0.5.
    # So max is 0.8.
    # Let's check if there's any other way to get 1.0. No.
    # But I can mock it if I want to test min(1.0, uncertainty).


def test_l1_operational_reflection():
    l1 = L1OperationalReflection(coverage_threshold=0.5, max_uncertainty=0.7)

    # Case 1: No block
    payload = {"retrieved_sources": ["s1"], "answer_draft": "certain"}
    res = l1.reflect(payload)
    assert res["block"] is False
    assert res["coverage_ratio"] == 1.0
    assert res["uncertainty_level"] == 0.0

    # Case 2: Block by coverage
    payload = {"retrieved_sources": [], "answer_draft": "certain"}
    res = l1.reflect(payload)
    assert res["block"] is True
    assert res["coverage_ratio"] == 0.0

    # Case 3: Block by uncertainty
    l1.max_uncertainty = 0.2
    payload = {"retrieved_sources": ["s1"], "answer_draft": "maybe"}
    res = l1.reflect(payload)
    assert res["block"] is True
    assert res["uncertainty_level"] == 0.3

    # Case 4: Block by contract_status
    # We need to mock contract_enforcer.enforce
    l1.contract_enforcer.enforce = MagicMock(return_value={"contract_status": "error"})
    res = l1.reflect(payload)
    assert res["block"] is True
    assert res["contract_status"] == "error"
