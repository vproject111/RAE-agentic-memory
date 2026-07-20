from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError
from rae_core.types.branded import (
    make_knowledge_id,
    make_checksum_sha256,
    make_tenant_id,
)
from rae_core.models.knowledge import (
    KnowledgeClass,
    AuthorityLevel,
    KnowledgeSourceType,
)
from rae_core.models.registry import (
    KnowledgeRegistryRecord,
    KnowledgeRevisionDraft,
    KnowledgeRevisionRecord,
)


def test_registry_record_valid():
    record = KnowledgeRegistryRecord(
        tenant_id=make_tenant_id("t1"),
        knowledge_id=make_knowledge_id("openapi-spec"),
        knowledge_class=KnowledgeClass.NORMATIVE,
        owner="security-team",
        scope=["read", "admin"],
        generation=1,
    )
    assert record.knowledge_id == "openapi-spec"
    assert "admin" in record.scope


def test_registry_record_invalid_scope():
    with pytest.raises(ValidationError, match="scope nie może zawierać duplikatów"):
        KnowledgeRegistryRecord(
            tenant_id=make_tenant_id("t1"),
            knowledge_id=make_knowledge_id("openapi-spec"),
            knowledge_class=KnowledgeClass.NORMATIVE,
            owner="security-team",
            scope=["read", "read"],  # Duplicated
        )


def test_revision_draft_valid():
    reg_id = uuid4()
    draft = KnowledgeRevisionDraft(
        registry_id=reg_id,
        authority_level=AuthorityLevel.CANONICAL,
        source_type=KnowledgeSourceType.OPENAPI,
        source_ref="git://dreamsoft/factory",
        version="2.0.0",
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2026, 6, 30, tzinfo=timezone.utc),
        checksum=make_checksum_sha256("d" * 64),
        content_summary="V2 specification",
        content_size_bytes=5000,
        created_by="operator",
        payload=b"openapi: 3.0.0\n",
    )
    assert draft.registry_id == reg_id
    assert draft.payload == b"openapi: 3.0.0\n"


def test_revision_draft_invalid_dates():
    with pytest.raises(ValidationError, match="valid_until musi być późniejsze niż valid_from"):
        KnowledgeRevisionDraft(
            registry_id=uuid4(),
            authority_level=AuthorityLevel.CANONICAL,
            source_type=KnowledgeSourceType.OPENAPI,
            source_ref="git://dreamsoft/factory",
            valid_from=datetime(2026, 6, 30, tzinfo=timezone.utc),
            valid_until=datetime(2026, 1, 1, tzinfo=timezone.utc),  # End before start
            checksum=make_checksum_sha256("e" * 64),
            content_summary="Invalid dates",
            content_size_bytes=100,
            created_by="operator",
        )
