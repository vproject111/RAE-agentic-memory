from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from rae_core.types.branded import (
    make_knowledge_id,
    make_checksum_sha256,
    make_tenant_id,
    make_request_id,
    make_actor_id,
)
from rae_core.models.knowledge import (
    KnowledgeRecord,
    KnowledgeClass,
    AuthorityLevel,
    KnowledgeSourceType,
)


def test_branded_types_valid():
    k_id = make_knowledge_id("  test-knowledge-id  ")
    assert k_id == "test-knowledge-id"

    checksum = make_checksum_sha256("A" * 64)
    assert checksum == "a" * 64

    t_id = make_tenant_id("t1")
    assert t_id == "t1"


def test_branded_types_invalid():
    with pytest.raises(ValueError, match="nie może być pusta"):
        make_knowledge_id("   ")

    with pytest.raises(TypeError, match="musi być tekstem"):
        make_knowledge_id(123)

    with pytest.raises(ValueError, match="64-znakowym hashem SHA-256"):
        make_checksum_sha256("short-hash")


def test_knowledge_record_valid():
    record = KnowledgeRecord(
        tenant_id=make_tenant_id("t1"),
        knowledge_id=make_knowledge_id("k1"),
        knowledge_class=KnowledgeClass.NORMATIVE,
        authority_level=AuthorityLevel.CANONICAL,
        source_type=KnowledgeSourceType.OPENAPI,
        source_ref="file:///path/to/spec.yaml",
        owner="sec-team",
        version="1.0.0",
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2026, 12, 31, tzinfo=timezone.utc),
        checksum=make_checksum_sha256("b" * 64),
        content_summary="Valid specification of API contracts",
        content_size_bytes=1024,
    )
    assert record.knowledge_id == "k1"
    assert record.tenant_id == "t1"
    assert len(record.checksum) == 64


def test_knowledge_record_invalid_dates():
    with pytest.raises(ValidationError, match="valid_until musi być późniejsze niż valid_from"):
        KnowledgeRecord(
            tenant_id=make_tenant_id("t1"),
            knowledge_id=make_knowledge_id("k1"),
            knowledge_class=KnowledgeClass.NORMATIVE,
            authority_level=AuthorityLevel.CANONICAL,
            source_type=KnowledgeSourceType.OPENAPI,
            source_ref="file:///path/to/spec.yaml",
            owner="sec-team",
            valid_from=datetime(2026, 12, 31, tzinfo=timezone.utc),
            valid_until=datetime(2026, 1, 1, tzinfo=timezone.utc),  # End before start
            checksum=make_checksum_sha256("b" * 64),
            content_summary="Invalid dates",
            content_size_bytes=100,
        )


def test_knowledge_record_duplicate_scope():
    with pytest.raises(ValidationError, match="scope nie może zawierać duplikatów"):
        KnowledgeRecord(
            tenant_id=make_tenant_id("t1"),
            knowledge_id=make_knowledge_id("k1"),
            knowledge_class=KnowledgeClass.NORMATIVE,
            authority_level=AuthorityLevel.CANONICAL,
            source_type=KnowledgeSourceType.OPENAPI,
            source_ref="file:///path/to/spec.yaml",
            owner="sec-team",
            scope=["admin", "read", "admin"],  # Duplicated
            checksum=make_checksum_sha256("c" * 64),
            content_summary="Duplicate scope elements",
            content_size_bytes=200,
        )
