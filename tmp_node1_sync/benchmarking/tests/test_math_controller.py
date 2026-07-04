"""
Unit tests for MathLayerController

Tests cover:
- MathDecision creation and serialization
- Features extraction and constraints
- MathLayerController decision logic
- Configuration system
"""

import pytest

from benchmarking.math_metrics.controller import (
    Features,
    MathControllerConfig,
    MathDecision,
    MathLayerController,
    MathLevel,
    TaskContext,
    TaskType,
)


class TestMathDecision:
    """Test MathDecision dataclass"""

    def test_decision_creation(self):
        """Test basic decision creation"""
        decision = MathDecision(
            selected_level=MathLevel.L1,
            strategy_id="relevance_scoring",
            params={"weight": 0.5},
            explanation="Test decision",
        )

        assert decision.selected_level == MathLevel.L1
        assert decision.strategy_id == "relevance_scoring"
        assert decision.confidence == 1.0
        assert len(decision.decision_id) == 8

    def test_decision_serialization(self):
        """Test decision to_dict and from_dict"""
        decision = MathDecision(
            selected_level=MathLevel.L2,
            strategy_id="entropy_minimization",
        )

        data = decision.to_dict()
        assert data["selected_level"] == "information_theoretic"

        # Round-trip
        restored = MathDecision.from_dict(data)
        assert restored.selected_level == MathLevel.L2


class TestFeatures:
    """Test Features dataclass"""

    def test_budget_constrained(self):
        """Test budget constraint detection"""
        features = Features(
            task_type=TaskType.MEMORY_RETRIEVE,
            cost_budget=0.005,
        )
        assert features.is_budget_constrained()

        features2 = Features(
            task_type=TaskType.MEMORY_RETRIEVE,
            cost_budget=0.02,
        )
        assert not features2.is_budget_constrained()

    def test_latency_constrained(self):
        """Test latency constraint detection"""
        features = Features(
            task_type=TaskType.MEMORY_RETRIEVE,
            latency_budget_ms=50,
        )
        assert features.is_latency_constrained()


class TestMathLayerController:
    """Test MathLayerController"""

    @pytest.fixture
    def controller(self):
        """Create controller with default config"""
        return MathLayerController()

    @pytest.fixture
    def simple_context(self):
        """Create simple task context"""
        return TaskContext(task_type=TaskType.MEMORY_RETRIEVE)

    def test_controller_initialization(self, controller):
        """Test controller initializes correctly"""
        assert controller.config is not None
        assert controller.decision_engine is not None

    def test_decide_returns_decision(self, controller, simple_context):
        """Test decide returns MathDecision"""
        decision = controller.decide(simple_context)

        assert isinstance(decision, MathDecision)
        assert decision.selected_level in MathLevel
        assert len(decision.decision_id) == 8

    def test_budget_forces_l1(self, controller):
        """Test budget constraint forces L1"""
        context = TaskContext(
            task_type=TaskType.REFLECTION_DEEP,  # Would normally use L2
            budget_constraints={"max_cost_usd": 0.001},
        )

        decision = controller.decide(context)
        assert decision.selected_level == MathLevel.L1

    def test_latency_forces_l1(self, controller):
        """Test latency constraint forces L1"""
        context = TaskContext(
            task_type=TaskType.REFLECTION_DEEP,
            budget_constraints={"max_latency_ms": 50},
        )

        decision = controller.decide(context)
        assert decision.selected_level == MathLevel.L1

    def test_task_type_influences_level(self, controller):
        """Test different task types select appropriate levels"""
        # Retrieval prefers L1
        retrieval_context = TaskContext(task_type=TaskType.MEMORY_RETRIEVE)
        retrieval_decision = controller.decide(retrieval_context)
        assert retrieval_decision.selected_level == MathLevel.L1

    def test_decision_logging(self, controller, simple_context):
        """Test decisions are logged to history"""
        initial_count = len(controller.decision_history)

        controller.decide(simple_context)

        assert len(controller.decision_history) == initial_count + 1

    def test_outcome_recording(self, controller, simple_context):
        """Test outcome recording"""
        decision = controller.decide(simple_context)

        outcome = controller.record_outcome(
            decision_id=decision.decision_id,
            success=True,
            metrics={"mrr": 0.85},
        )

        assert outcome is not None
        assert outcome.success is True

    def test_explanation_generation(self, controller, simple_context):
        """Test explanation is generated"""
        decision = controller.decide(simple_context)

        assert len(decision.explanation) > 0
        assert decision.selected_level.value in decision.explanation


class TestMathControllerConfig:
    """Test configuration system"""

    def test_default_config(self):
        """Test default configuration"""
        config = MathControllerConfig()

        assert config.profile == "research"
        assert config.default_level == MathLevel.L1
        assert len(config.allowed_levels) == 3

    def test_production_profile_restricts_l3(self):
        """Test production profile handling"""
        config = MathControllerConfig(
            profile="production",
            allowed_levels=[MathLevel.L1, MathLevel.L2],
        )

        controller = MathLayerController(config=config)

        # L3 should not be selected in production
        context = TaskContext(
            task_type=TaskType.REFLECTION_DEEP,
            session_metadata={"turn_number": 100},
        )

        decision = controller.decide(context)
        assert decision.selected_level != MathLevel.L3


class TestMathLevel:
    """Test MathLevel enum"""

    def test_cost_multipliers(self):
        """Test cost multipliers are ordered"""
        assert MathLevel.L1.cost_multiplier < MathLevel.L2.cost_multiplier
        assert MathLevel.L2.cost_multiplier < MathLevel.L3.cost_multiplier

    def test_descriptions_exist(self):
        """Test all levels have descriptions"""
        for level in MathLevel:
            assert len(level.description) > 0


class TestTaskType:
    """Test TaskType enum"""

    def test_preferred_levels(self):
        """Test preferred levels are assigned"""
        for task_type in TaskType:
            assert task_type.preferred_level in MathLevel
