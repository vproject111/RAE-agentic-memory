"""
Tests for Event Triggers - Rules Engine and Automation

Tests cover:
- Event emission and processing
- Condition evaluation (AND/OR logic)
- Action execution
- Rate limiting and cooldowns
- Workflow orchestration
- Circuit breaker for actions
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.memory_api.models.event_models import (
    ActionType,
    Condition,
    ConditionGroup,
    ConditionOperator,
    Event,
    EventType,
    TriggerRule,
)
from apps.memory_api.services.rules_engine import RulesEngine


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def rules_engine(mock_pool):
    return RulesEngine(mock_pool)


@pytest.fixture
def sample_event():
    return Event(
        event_id=uuid4(),
        event_type=EventType.MEMORY_CREATED,
        tenant_id="test",
        project_id="test",
        source_service="api",
        payload={"importance": 0.9, "memory_count": 55},
    )


# Event Processing Tests
@pytest.mark.asyncio
async def test_process_event(rules_engine, sample_event, mock_pool):
    """Test event processing and trigger matching"""
    mock_pool.fetch = AsyncMock(return_value=[])

    result = await rules_engine.process_event(sample_event)

    assert "triggers_matched" in result
    assert "actions_executed" in result


# Condition Evaluation Tests
@pytest.mark.asyncio
async def test_evaluate_simple_condition(rules_engine):
    """Test simple condition evaluation"""
    condition = Condition(
        field="payload.importance", operator=ConditionOperator.GREATER_THAN, value=0.8
    )

    data = {"payload": {"importance": 0.9}}
    result = rules_engine._evaluate_condition(condition, data)

    assert result is True


@pytest.mark.asyncio
async def test_evaluate_condition_group_and(rules_engine):
    """Test AND condition group"""
    group = ConditionGroup(
        operator="AND",
        conditions=[
            Condition(
                field="payload.importance",
                operator=ConditionOperator.GREATER_THAN,
                value=0.8,
            ),
            Condition(
                field="payload.memory_count",
                operator=ConditionOperator.GREATER_EQUAL,
                value=50,
            ),
        ],
    )

    data = {"payload": {"importance": 0.9, "memory_count": 55}}
    result = rules_engine._evaluate_condition_group(group, data)

    assert result is True


@pytest.mark.asyncio
async def test_evaluate_condition_group_or(rules_engine):
    """Test OR condition group"""
    group = ConditionGroup(
        operator="OR",
        conditions=[
            Condition(
                field="payload.importance",
                operator=ConditionOperator.GREATER_THAN,
                value=0.95,
            ),
            Condition(
                field="payload.memory_count",
                operator=ConditionOperator.GREATER_EQUAL,
                value=50,
            ),
        ],
    )

    data = {"payload": {"importance": 0.7, "memory_count": 55}}
    result = rules_engine._evaluate_condition_group(group, data)

    assert result is True  # Second condition is true


@pytest.mark.asyncio
async def test_nested_condition_groups(rules_engine):
    """Test nested condition groups"""
    group = ConditionGroup(
        operator="AND",
        conditions=[
            Condition(
                field="payload.importance",
                operator=ConditionOperator.GREATER_THAN,
                value=0.5,
            )
        ],
        groups=[
            ConditionGroup(
                operator="OR",
                conditions=[
                    Condition(
                        field="payload.type",
                        operator=ConditionOperator.EQUALS,
                        value="critical",
                    ),
                    Condition(
                        field="payload.priority",
                        operator=ConditionOperator.GREATER_THAN,
                        value=7,
                    ),
                ],
            )
        ],
    )

    data = {"payload": {"importance": 0.8, "type": "critical", "priority": 5}}
    result = rules_engine._evaluate_condition_group(group, data)

    assert result is True


# Condition Operators Tests
@pytest.mark.asyncio
async def test_condition_operators(rules_engine):
    """Test all condition operators"""
    data = {"value": 10, "text": "hello world", "items": [1, 2, 3], "null_value": None}

    # EQUALS
    assert rules_engine._evaluate_condition(
        Condition(field="value", operator=ConditionOperator.EQUALS, value=10), data
    )

    # CONTAINS
    assert rules_engine._evaluate_condition(
        Condition(field="text", operator=ConditionOperator.CONTAINS, value="world"),
        data,
    )

    # IN
    assert rules_engine._evaluate_condition(
        Condition(field="value", operator=ConditionOperator.IN, value=[10, 20, 30]),
        data,
    )

    # IS_NULL
    assert rules_engine._evaluate_condition(
        Condition(field="null_value", operator=ConditionOperator.IS_NULL, value=None),
        data,
    )


# Rate Limiting Tests
@pytest.mark.asyncio
async def test_rate_limiting(rules_engine, mock_pool):
    """Test rate limiting for triggers"""
    from apps.memory_api.models.event_models import TriggerCondition

    trigger = TriggerRule(
        trigger_id=uuid4(),
        tenant_id="test",
        project_id="test",
        rule_name="test",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED], max_executions_per_hour=5
        ),
        actions=[],
        executions_this_hour=5,  # Already at limit
        hour_window_start=datetime.now(timezone.utc),
        created_by="test",
    )

    # Should be rate limited (returns False when at limit)
    # Since hour_window_start is current time, it won't reset
    # executions_this_hour (5) < max_executions_per_hour (5) = False
    can_execute = await rules_engine._check_rate_limit(trigger)
    assert can_execute is False


@pytest.mark.asyncio
async def test_cooldown_period(rules_engine):
    """Test cooldown period between executions"""
    from datetime import timedelta

    from apps.memory_api.models.event_models import TriggerCondition

    trigger = TriggerRule(
        trigger_id=uuid4(),
        tenant_id="test",
        project_id="test",
        rule_name="test",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED], cooldown_seconds=60
        ),
        actions=[],
        last_executed_at=datetime.now(timezone.utc)
        - timedelta(seconds=30),  # Executed 30s ago
        created_by="test",
    )

    # Should be in cooldown (don't await - _check_cooldown is not async)
    can_execute = rules_engine._check_cooldown(trigger)
    assert can_execute is False


# Action Execution Tests
@pytest.mark.asyncio
async def test_execute_action(rules_engine, sample_event, mock_pool):
    """Test action execution"""
    from apps.memory_api.models.event_models import ActionConfig, TriggerCondition

    trigger = TriggerRule(
        trigger_id=uuid4(),
        tenant_id="test",
        project_id="test",
        rule_name="test",
        condition=TriggerCondition(event_types=[EventType.MEMORY_CREATED]),
        actions=[],
        created_by="test",
    )

    action_config = ActionConfig(
        action_type=ActionType.SEND_NOTIFICATION,
        config={"channel": "email", "message": "Test"},
    )

    mock_pool.execute = AsyncMock()

    result = await rules_engine._execute_action(trigger, sample_event, action_config)

    # _execute_action returns ActionExecution object
    assert result is not None


# Workflow Tests
@pytest.mark.asyncio
async def test_workflow_execution(rules_engine, mock_pool):
    """Test workflow model and step dependencies"""
    from apps.memory_api.models.event_models import (
        ActionConfig,
        ActionType,
        CreateWorkflowRequest,
        WorkflowStep,
    )

    # Create workflow with multiple steps
    step1 = WorkflowStep(
        step_id="step_1",
        step_name="Generate Reflection",
        action=ActionConfig(
            action_type=ActionType.GENERATE_REFLECTION, config={"model": "gpt-4"}
        ),
        depends_on=[],
        order=1,
    )

    step2 = WorkflowStep(
        step_id="step_2",
        step_name="Extract Semantics",
        action=ActionConfig(
            action_type=ActionType.EXTRACT_SEMANTICS, config={"threshold": 0.8}
        ),
        depends_on=["step_1"],  # Depends on step 1
        order=2,
    )

    step3 = WorkflowStep(
        step_id="step_3",
        step_name="Send Notification",
        action=ActionConfig(
            action_type=ActionType.SEND_NOTIFICATION,
            config={"channel": "slack", "message": "Processing complete"},
        ),
        depends_on=["step_1", "step_2"],  # Depends on both steps
        order=3,
    )

    # Create workflow request
    workflow = CreateWorkflowRequest(
        tenant_id="test",
        project_id="test",
        workflow_name="Test Workflow",
        description="Multi-step workflow with dependencies",
        steps=[step1, step2, step3],
        stop_on_failure=True,
        parallel_execution=False,
        created_by="test_user",
    )

    # Verify workflow structure
    assert len(workflow.steps) == 3
    assert workflow.steps[0].step_id == "step_1"
    assert workflow.steps[1].depends_on == ["step_1"]
    assert workflow.steps[2].depends_on == ["step_1", "step_2"]

    # Verify step ordering
    assert workflow.steps[0].order == 1
    assert workflow.steps[1].order == 2
    assert workflow.steps[2].order == 3

    # Verify action types
    assert workflow.steps[0].action.action_type == ActionType.GENERATE_REFLECTION
    assert workflow.steps[1].action.action_type == ActionType.EXTRACT_SEMANTICS
    assert workflow.steps[2].action.action_type == ActionType.SEND_NOTIFICATION

    # Verify workflow configuration
    assert workflow.stop_on_failure is True
    assert workflow.parallel_execution is False
