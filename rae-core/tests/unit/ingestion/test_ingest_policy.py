from rae_core.ingestion.policy import ContentSignature, IngestPolicySelector


def test_select_policy_fallback():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "OPERATIONAL_FALLBACK"}, dist={}, stab={"conflict": False}
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_FALLBACK"


def test_select_policy_conflict():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "PROSE_LIKE"}, dist={}, stab={"conflict": True}
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_MIXED_SAFE"


def test_select_policy_log_stream():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "LINEAR_LOG_LIKE"},
        dist={"repeatability_score": 0.5},
        stab={"conflict": False},
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_LOG_STREAM"


def test_select_policy_technical_formal():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "TECHNICAL_SPEC_LIKE"}, dist={}, stab={"conflict": False}
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_TECHNICAL_FORMAL"


def test_select_policy_procedure_doc():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "LIST_PROCEDURE_LIKE"}, dist={}, stab={"conflict": False}
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_PROCEDURE_DOC"


def test_select_policy_data_table():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "TABLE_RECORD_LIKE"}, dist={}, stab={"conflict": False}
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_DATA_TABLE"


def test_select_policy_default_prose():
    selector = IngestPolicySelector()
    sig = ContentSignature(
        struct={"mode": "UNKNOWN"},
        dist={"repeatability_score": 0.1},
        stab={"conflict": False},
    )
    policy, audit = selector.select_policy(sig)
    assert policy == "POLICY_PROSE_TEXT"
