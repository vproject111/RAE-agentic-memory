"""
Tests for ContextProvenanceService - ISO/IEC 42001 Section 8 (Transparency & Explainability)
"""

from uuid import uuid4

import pytest

from apps.memory_api.services.context_provenance_service import (
    ContextProvenanceService,
    ContextSource,
    ContextSourceType,
    DecisionType,
)

pytestmark = pytest.mark.iso42001


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """Mock logger to avoid structured logging issues"""
    mocker.patch("apps.memory_api.services.context_provenance_service.logger")


@pytest.fixture
def provenance_service():
    """Create ContextProvenanceService instance"""
    return ContextProvenanceService()


class TestCreateDecisionContext:
    """Tests for create_decision_context method"""

    @pytest.mark.asyncio
    async def test_create_context_basic(self, provenance_service, mocker):
        """Test basic context creation"""
        mocker.patch.object(provenance_service, "_store_context", return_value=None)

        sources = [
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="User prefers dark mode",
                relevance_score=0.95,
                trust_level="high",
                source_owner="user@example.com",
            ),
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="User language is English",
                relevance_score=0.85,
                trust_level="high",
                source_owner="user@example.com",
            ),
        ]

        result = await provenance_service.create_decision_context(
            tenant_id="test-tenant",
            project_id="test-project",
            query="What are user preferences?",
            sources=sources,
        )

        assert result.tenant_id == "test-tenant"
        assert result.project_id == "test-project"
        assert result.query == "What are user preferences?"
        assert result.total_sources == 2
        assert len(result.sources) == 2

    @pytest.mark.asyncio
    async def test_quality_metrics_calculation(self, provenance_service, mocker):
        """Test quality metrics calculation"""
        mocker.patch.object(provenance_service, "_store_context", return_value=None)

        sources = [
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="Content 1",
                relevance_score=0.9,
                trust_level="high",  # 1.0
            ),
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="Content 2",
                relevance_score=0.8,
                trust_level="medium",  # 0.7
            ),
        ]

        result = await provenance_service.create_decision_context(
            tenant_id="test-tenant",
            project_id="test-project",
            query="Test query",
            sources=sources,
        )

        # Average relevance: (0.9 + 0.8) / 2 = 0.85
        assert abs(result.avg_relevance - 0.85) < 0.01

        # Average trust: (1.0 + 0.7) / 2 = 0.85
        assert abs(result.avg_trust - 0.85) < 0.01

        # Coverage score: min(2/5, 1.0) = 0.4
        assert result.coverage_score == 0.4

    @pytest.mark.asyncio
    async def test_empty_sources(self, provenance_service, mocker):
        """Test context creation with no sources"""
        mocker.patch.object(provenance_service, "_store_context", return_value=None)

        result = await provenance_service.create_decision_context(
            tenant_id="test-tenant",
            project_id="test-project",
            query="Test query",
            sources=[],
        )

        assert result.total_sources == 0
        assert result.avg_relevance == 0.0
        assert result.avg_trust == 0.0
        assert result.coverage_score == 0.0

    @pytest.mark.asyncio
    async def test_trust_level_mapping(self, provenance_service, mocker):
        """Test trust level to numeric mapping"""
        mocker.patch.object(provenance_service, "_store_context", return_value=None)

        sources = [
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="High trust",
                relevance_score=0.9,
                trust_level="high",  # 1.0
            ),
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="Medium trust",
                relevance_score=0.9,
                trust_level="medium",  # 0.7
            ),
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="Low trust",
                relevance_score=0.9,
                trust_level="low",  # 0.4
            ),
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content="Unverified",
                relevance_score=0.9,
                trust_level="unverified",  # 0.0
            ),
        ]

        result = await provenance_service.create_decision_context(
            tenant_id="test-tenant",
            project_id="test-project",
            query="Test query",
            sources=sources,
        )

        # Average: (1.0 + 0.7 + 0.4 + 0.0) / 4 = 0.525
        assert abs(result.avg_trust - 0.525) < 0.01

    @pytest.mark.asyncio
    async def test_coverage_score_max_cap(self, provenance_service, mocker):
        """Test coverage score caps at 1.0"""
        mocker.patch.object(provenance_service, "_store_context", return_value=None)

        # Create 10 sources (more than max of 5)
        sources = [
            ContextSource(
                source_id=uuid4(),
                source_type=ContextSourceType.MEMORY,
                content=f"Content {i}",
                relevance_score=0.9,
                trust_level="high",
            )
            for i in range(10)
        ]

        result = await provenance_service.create_decision_context(
            tenant_id="test-tenant",
            project_id="test-project",
            query="Test query",
            sources=sources,
        )

        # Coverage should cap at 1.0 even with 10 sources
        assert result.coverage_score == 1.0


class TestRecordDecision:
    """Tests for record_decision method"""

    @pytest.mark.asyncio
    async def test_record_decision_basic(self, provenance_service, mocker):
        """Test basic decision recording"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.sources = [mocker.MagicMock(), mocker.MagicMock()]
        mock_context.avg_relevance = 0.85

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )
        mocker.patch.object(provenance_service, "_store_decision", return_value=None)

        result = await provenance_service.record_decision(
            tenant_id="test-tenant",
            project_id="test-project",
            decision_type=DecisionType.RESPONSE_GENERATION,
            decision_description="Generated response to user query",
            context_id=context_id,
            output="Here is your answer...",
            confidence=0.9,
            model_name="gpt-4",
        )

        assert result.tenant_id == "test-tenant"
        assert result.project_id == "test-project"
        assert result.decision_type == DecisionType.RESPONSE_GENERATION
        assert result.context_id == context_id
        assert result.output == "Here is your answer..."
        assert result.confidence == 0.9
        assert result.model_name == "gpt-4"
        assert result.human_approved is False

    @pytest.mark.asyncio
    async def test_record_decision_with_human_approval(
        self, provenance_service, mocker
    ):
        """Test decision recording with human approval"""
        context_id = uuid4()
        approval_request_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.sources = []
        mock_context.avg_relevance = 0.85

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )
        mocker.patch.object(provenance_service, "_store_decision", return_value=None)

        result = await provenance_service.record_decision(
            tenant_id="test-tenant",
            project_id="test-project",
            decision_type=DecisionType.ACTION_EXECUTION,
            decision_description="Delete critical data",
            context_id=context_id,
            output="Data deleted",
            confidence=0.95,
            human_approved=True,
            approval_request_id=approval_request_id,
        )

        assert result.human_approved is True
        assert result.approval_request_id == approval_request_id

    @pytest.mark.asyncio
    async def test_context_summary_generation(self, provenance_service, mocker):
        """Test context summary generation"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.sources = [
            mocker.MagicMock(),
            mocker.MagicMock(),
            mocker.MagicMock(),
        ]
        mock_context.avg_relevance = 0.75

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )
        mocker.patch.object(provenance_service, "_store_decision", return_value=None)

        result = await provenance_service.record_decision(
            tenant_id="test-tenant",
            project_id="test-project",
            decision_type=DecisionType.RESPONSE_GENERATION,
            decision_description="Test decision",
            context_id=context_id,
            output="Test output",
            confidence=0.9,
        )

        assert "3 sources" in result.context_summary
        assert "0.75" in result.context_summary


class TestGetDecisionLineage:
    """Tests for get_decision_lineage method"""

    @pytest.mark.asyncio
    async def test_get_full_lineage(self, provenance_service, mocker):
        """Test retrieving full decision lineage"""
        decision_id = uuid4()
        context_id = uuid4()

        # Mock decision
        mock_decision = mocker.MagicMock()
        mock_decision.decision_id = decision_id
        mock_decision.context_id = context_id
        mock_decision.confidence = 0.9
        mock_decision.human_approved = True
        mock_decision.dict.return_value = {
            "decision_id": str(decision_id),
            "confidence": 0.9,
        }

        # Mock context
        mock_source = mocker.MagicMock()
        mock_source.source_id = uuid4()
        mock_source.source_type = ContextSourceType.MEMORY
        mock_source.trust_level = "high"
        mock_source.relevance_score = 0.95
        mock_source.source_owner = "user@example.com"

        mock_context = mocker.MagicMock()
        mock_context.query = "What are user preferences?"
        mock_context.sources = [mock_source]
        mock_context.dict.return_value = {"query": "What are user preferences?"}

        mocker.patch.object(
            provenance_service, "_get_decision", return_value=mock_decision
        )
        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.get_decision_lineage(decision_id)

        assert "decision" in result
        assert "context" in result
        assert "provenance_chain" in result
        assert result["provenance_chain"]["query"] == "What are user preferences?"
        assert result["provenance_chain"]["decision_confidence"] == 0.9
        assert result["provenance_chain"]["human_approved"] is True
        assert len(result["provenance_chain"]["sources"]) == 1

    @pytest.mark.asyncio
    async def test_get_lineage_decision_not_found(self, provenance_service, mocker):
        """Test lineage retrieval for non-existent decision"""
        decision_id = uuid4()
        mocker.patch.object(provenance_service, "_get_decision", return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await provenance_service.get_decision_lineage(decision_id)


class TestAuditContextQuality:
    """Tests for audit_context_quality method"""

    @pytest.mark.asyncio
    async def test_audit_high_quality_context(self, provenance_service, mocker):
        """Test auditing high quality context"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.avg_trust = 0.9
        mock_context.avg_relevance = 0.85
        mock_context.coverage_score = 0.8
        mock_context.total_sources = 4

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.audit_context_quality(context_id)

        assert result["quality_score"] > 0.8
        assert len(result["issues"]) == 0
        assert len(result["recommendations"]) == 0

    @pytest.mark.asyncio
    async def test_audit_low_trust(self, provenance_service, mocker):
        """Test auditing context with low trust"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.avg_trust = 0.5  # Low trust
        mock_context.avg_relevance = 0.85
        mock_context.coverage_score = 0.8
        mock_context.total_sources = 4

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.audit_context_quality(context_id)

        assert any("Low average trust" in issue for issue in result["issues"])
        assert any("trust" in rec.lower() for rec in result["recommendations"])

    @pytest.mark.asyncio
    async def test_audit_low_relevance(self, provenance_service, mocker):
        """Test auditing context with low relevance"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.avg_trust = 0.9
        mock_context.avg_relevance = 0.5  # Low relevance
        mock_context.coverage_score = 0.8
        mock_context.total_sources = 4

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.audit_context_quality(context_id)

        assert any("Low average relevance" in issue for issue in result["issues"])
        assert any("query" in rec.lower() for rec in result["recommendations"])

    @pytest.mark.asyncio
    async def test_audit_insufficient_sources(self, provenance_service, mocker):
        """Test auditing context with insufficient sources"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.avg_trust = 0.9
        mock_context.avg_relevance = 0.85
        mock_context.coverage_score = 0.8
        mock_context.total_sources = 1  # Insufficient

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.audit_context_quality(context_id)

        assert any("Insufficient" in issue for issue in result["issues"])
        assert any(
            "expand" in rec.lower() or "context retrieval" in rec.lower()
            for rec in result["recommendations"]
        )

    @pytest.mark.asyncio
    async def test_audit_quality_score_calculation(self, provenance_service, mocker):
        """Test quality score calculation formula"""
        context_id = uuid4()
        mock_context = mocker.MagicMock()
        mock_context.avg_trust = 0.8
        mock_context.avg_relevance = 0.9
        mock_context.coverage_score = 0.6
        mock_context.total_sources = 3

        mocker.patch.object(
            provenance_service, "_get_context", return_value=mock_context
        )

        result = await provenance_service.audit_context_quality(context_id)

        # Quality = trust*0.4 + relevance*0.4 + coverage*0.2
        # = 0.8*0.4 + 0.9*0.4 + 0.6*0.2 = 0.32 + 0.36 + 0.12 = 0.80
        expected_quality = 0.80
        assert abs(result["quality_score"] - expected_quality) < 0.01

    @pytest.mark.asyncio
    async def test_audit_context_not_found(self, provenance_service, mocker):
        """Test auditing non-existent context"""
        context_id = uuid4()
        mocker.patch.object(provenance_service, "_get_context", return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await provenance_service.audit_context_quality(context_id)
