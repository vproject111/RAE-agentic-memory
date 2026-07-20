from datetime import datetime, timezone
import pytest
from uuid import uuid4

from rae_core.governance.context import Clock, ResolutionContext
from rae_core.models.evidence import ConflictType, ResolutionStatus
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType
from rae_core.interfaces.adapter import RetrievedKnowledge
from rae_core.governance.adapter_broker import AdapterBroker
from rae_core.governance.engine import DefaultKnowledgeResolutionEngine
from rae_core.governance.hashing import calculate_content_hash, calculate_audit_hash


# 1. Custom Clock Mock

class FrozenClock(Clock):
    def __init__(self, frozen_time: datetime):
        self.frozen_time = frozen_time

    def now(self) -> datetime:
        return self.frozen_time


class MockBroker:
    def __init__(self, mock_results):
        self.mock_results = mock_results

    async def retrieve(self, query, context):
        self.last_query = query
        self.last_context = context
        return self.mock_results


# 2. Hashing Determinism Tests

def test_content_hash_determinism():
    clock_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Create two identical bundles but with different evidence sorting in constructor
    evidence_1 = [
        RetrievedKnowledge(
            evidence_id="ev-1",
            content="Evidence 1 Content",
            source_ref="test://ref1",
            source_type=KnowledgeSourceType.TEST,
            authority_level=AuthorityLevel.CANONICAL,
            score=0.95,
            observed_at=clock_time,
            checksum="a" * 64,
        ),
        RetrievedKnowledge(
            evidence_id="ev-2",
            content="Evidence 2 Content",
            source_ref="test://ref2",
            source_type=KnowledgeSourceType.TEST,
            authority_level=AuthorityLevel.OBSERVED,
            score=0.75,
            observed_at=clock_time,
            checksum="b" * 64,
        )
    ]
    
    context = ResolutionContext(
        tenant_id="t1",
        request_id="r1",
        policy_version="1.0.0",
    )
    
    # Bundle 1
    broker_1 = MockBroker(evidence_1)
    engine_1 = DefaultKnowledgeResolutionEngine(broker_1, FrozenClock(clock_time))
    
    # Bundle 2 (with reversed evidence list in adapter response)
    broker_2 = MockBroker(list(reversed(evidence_1)))
    engine_2 = DefaultKnowledgeResolutionEngine(broker_2, FrozenClock(clock_time))
    
    import asyncio
    bundle_1 = asyncio.run(engine_1.resolve("query", context=context))
    bundle_2 = asyncio.run(engine_2.resolve("query", context=context))
    
    # The content_hash must be identical regardless of retrieval ordering!
    assert bundle_1.content_hash == bundle_2.content_hash


# 3. Conflict Resolution Tests

def test_resolution_engine_conflict_handling():
    clock_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Setup conflicting evidence (same source_ref, different checksums)
    evidence = [
        RetrievedKnowledge(
            evidence_id="ev-1",
            content="V1 Spec",
            source_ref="openapi://dreamsoft/factory",
            source_type=KnowledgeSourceType.OPENAPI,
            authority_level=AuthorityLevel.OBSERVED,  # Lower authority
            score=0.8,
            observed_at=clock_time,
            checksum="a" * 64,
        ),
        RetrievedKnowledge(
            evidence_id="ev-2",
            content="V2 Spec",
            source_ref="openapi://dreamsoft/factory",
            source_type=KnowledgeSourceType.OPENAPI,
            authority_level=AuthorityLevel.CANONICAL,  # Higher authority (should win)
            score=0.95,
            observed_at=clock_time,
            checksum="b" * 64,
        )
    ]
    
    broker = MockBroker(evidence)
    engine = DefaultKnowledgeResolutionEngine(broker, FrozenClock(clock_time))
    context = ResolutionContext(
        tenant_id="t1",
        request_id="r1",
        policy_version="1.0.0",
    )
    
    import asyncio
    bundle = asyncio.run(engine.resolve("users", context=context))
    
    # Conflicting items must be resolved with a warning
    assert bundle.resolution_status == ResolutionStatus.RESOLVED_WITH_WARNING
    assert len(bundle.conflicts) == 1
    assert bundle.conflicts[0].conflict_type == ConflictType.VERSION
    assert bundle.conflicts[0].preferred_source == "openapi://dreamsoft/factory"
    
    # The winning evidence item in the bundle must be the Canonical one
    assert len(bundle.evidence) == 1
    assert bundle.evidence[0].authority_level == AuthorityLevel.CANONICAL
    assert bundle.evidence[0].checksum == "b" * 64
