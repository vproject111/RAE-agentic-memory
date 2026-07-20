from rae_core.reflection.layers.l3_meta import (
    FieldDensityMonitor,
    L3MetaFieldReflection,
    RenormalizationEngine,
    SymmetryAndAnomalyDetector,
)


def test_field_density_monitor():
    monitor = FieldDensityMonitor()
    # Case 1: normal
    res = monitor.monitor({"answer_draft": "test"})
    assert res["density_delta"] == 0.05
    assert len(res["emerging_clusters"]) == 0

    # Case 2: cluster detected
    res = monitor.monitor({"answer_draft": "local first strategy"})
    assert "local_first + grant_strategy" in res["emerging_clusters"]


def test_renormalization_engine():
    engine = RenormalizationEngine()
    # Case 1: ok
    res = engine.renormalize({"answer_draft": "test"})
    assert len(res["scale_inconsistencies"]) == 0

    # Case 2: inconsistency
    res = engine.renormalize({"answer_draft": "always correct except when wrong"})
    assert "generalization_contradiction" in res["scale_inconsistencies"]
    assert res["scale_inconsistency_penalty"] == 0.1


def test_symmetry_and_anomaly_detector():
    detector = SymmetryAndAnomalyDetector()
    # Case 1: policy violation
    res = detector.detect({"answer_draft": "x" * 60, "retrieved_sources": []})
    assert any(a["type"] == "policy_violation" for a in res["anomalies"])

    # Case 2: domain leakage
    res = detector.detect(
        {"answer_draft": "confidential data in public", "retrieved_sources": ["s1"]}
    )
    assert any(a["type"] == "domain_leakage" for a in res["anomalies"])


def test_l3_meta_field_reflection():
    l3 = L3MetaFieldReflection()

    # Case 1: High FSI
    payload = {"answer_draft": "test", "retrieved_sources": ["s1"]}
    res = l3.reflect(payload)
    assert res["field_stability_index"] == 1.0
    assert res["block"] is False

    # Case 2: Penalty for scale inconsistency
    payload = {"answer_draft": "always except", "retrieved_sources": ["s1"]}
    res = l3.reflect(payload)
    assert res["field_stability_index"] == 0.9  # 1.0 - 0.1

    # Case 3: Bonus for emerging clusters
    payload = {"answer_draft": "local strategy", "retrieved_sources": ["s1"]}
    res = l3.reflect(payload)
    assert res["field_stability_index"] == 1.0  # 1.0 + 0.1 -> clamped to 1.0

    # Case 4: Block by critical anomaly
    l3.critical_threshold = 0.5
    payload = {
        "answer_draft": "x" * 60,
        "retrieved_sources": [],
    }  # policy violation severity 0.8
    res = l3.reflect(payload)
    assert res["block"] is True

    # Case 5: Block by scale penalty
    l3.scale_tolerance = 0.05
    payload = {
        "answer_draft": "always except",
        "retrieved_sources": ["s1"],
    }  # penalty 0.1
    res = l3.reflect(payload)
    assert res["block"] is True

    # Case 6: Clamp FSI to 0
    # To get 0, we need penalty/anomaly > 1.1?
    # Anomaly policy_violation(0.8) + domain_leakage(0.6) = 1.4.
    payload = {
        "answer_draft": "confidential public " + "x" * 60,
        "retrieved_sources": [],
    }
    res = l3.reflect(payload)
    # severity = 0.8 + 0.6 = 1.4. penalty = 0. FSI = 1 - 1.4 = -0.4 -> 0.0.
    assert res["field_stability_index"] == 0.0
