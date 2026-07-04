from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.models.event_models import (
    ActionConfig,
    ActionType,
    Condition,
    ConditionGroup,
    ConditionOperator,
    Event,
    EventType,
    ExecutionStatus,
    TriggerCondition,
    TriggerRule,
)
from apps.memory_api.services.rules_engine import RulesEngine

# Test Data
TENANT_ID = "t1"
PROJECT_ID = "p1"


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def rules_engine(mock_pool):
    return RulesEngine(mock_pool)


@pytest.fixture
def sample_event():
    return Event(
        event_id=str(uuid4()),
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        source_service="test_service",
        event_type=EventType.MEMORY_CREATED,
        timestamp=datetime.now(timezone.utc),
        payload={
            "content": "Important memory about AI safety",
            "importance": 0.9,
            "tags": ["ai", "safety", "critical"],
            "metadata": {"source": "user_chat", "confidence": 0.95},
        },
    )


@pytest.mark.asyncio
async def test_evaluate_condition_operators(rules_engine, sample_event):
    """Test all condition operators."""
    payload = sample_event.payload

    # EQUALS
    c = Condition(
        field="metadata.source", operator=ConditionOperator.EQUALS, value="user_chat"
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    c = Condition(
        field="metadata.source", operator=ConditionOperator.EQUALS, value="api"
    )
    assert rules_engine._evaluate_condition(c, payload) is False

    # NOT_EQUALS
    c = Condition(field="importance", operator=ConditionOperator.NOT_EQUALS, value=0.5)
    assert rules_engine._evaluate_condition(c, payload) is True

    # GREATER_THAN / LESS_THAN
    c = Condition(
        field="importance", operator=ConditionOperator.GREATER_THAN, value=0.8
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    c = Condition(field="importance", operator=ConditionOperator.LESS_THAN, value=0.1)
    assert rules_engine._evaluate_condition(c, payload) is False

    # CONTAINS (String)
    c = Condition(
        field="content", operator=ConditionOperator.CONTAINS, value="AI safety"
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    # CONTAINS (List)
    c = Condition(field="tags", operator=ConditionOperator.CONTAINS, value="critical")
    assert rules_engine._evaluate_condition(c, payload) is True

    # NOT_CONTAINS
    c = Condition(field="tags", operator=ConditionOperator.NOT_CONTAINS, value="funny")
    assert rules_engine._evaluate_condition(c, payload) is True

    # IN
    c = Condition(
        field="metadata.source",
        operator=ConditionOperator.IN,
        value=["user_chat", "system"],
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    # NOT_IN
    c = Condition(
        field="metadata.source",
        operator=ConditionOperator.NOT_IN,
        value=["email", "slack"],
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    # MATCHES_REGEX
    c = Condition(
        field="content",
        operator=ConditionOperator.MATCHES_REGEX,
        value=r".*AI\s+safety.*",
    )
    assert rules_engine._evaluate_condition(c, payload) is True

    # IS_NULL / IS_NOT_NULL
    c = Condition(field="non_existent", operator=ConditionOperator.IS_NULL, value=True)
    assert rules_engine._evaluate_condition(c, payload) is True

    c = Condition(
        field="importance", operator=ConditionOperator.IS_NOT_NULL, value=True
    )
    assert rules_engine._evaluate_condition(c, payload) is True


@pytest.mark.asyncio
async def test_evaluate_condition_group(rules_engine, sample_event):
    """Test nested condition groups."""
    payload = sample_event.payload

    # (importance > 0.8 AND source == 'user_chat')
    group_and = ConditionGroup(
        operator="AND",
        conditions=[
            Condition(
                field="importance", operator=ConditionOperator.GREATER_THAN, value=0.8
            ),
            Condition(
                field="metadata.source",
                operator=ConditionOperator.EQUALS,
                value="user_chat",
            ),
        ],
    )
    assert rules_engine._evaluate_condition_group(group_and, payload) is True

    # (tags contains 'funny' OR tags contains 'critical')
    group_or = ConditionGroup(
        operator="OR",
        conditions=[
            Condition(field="tags", operator=ConditionOperator.CONTAINS, value="funny"),
            Condition(
                field="tags", operator=ConditionOperator.CONTAINS, value="critical"
            ),
        ],
    )
    assert rules_engine._evaluate_condition_group(group_or, payload) is True


@pytest.mark.asyncio
async def test_process_event_flow(rules_engine, sample_event):
    """Test full event processing flow."""
    # Mock triggers
    trigger = TriggerRule(
        trigger_id=uuid4(),
        rule_name="High Importance Trigger",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        created_by="test_user",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED],
            condition_group=ConditionGroup(
                operator="AND",
                conditions=[
                    Condition(
                        field="importance",
                        operator=ConditionOperator.GREATER_THAN,
                        value=0.8,
                    )
                ],
            ),
        ),
        actions=[ActionConfig(action_type=ActionType.GENERATE_REFLECTION, config={})],
        is_enabled=True,
    )

    # Mock internal methods to focus on flow
    with (
        patch.object(
            rules_engine, "_fetch_active_triggers", new_callable=AsyncMock
        ) as mock_fetch,
        patch.object(
            rules_engine, "_execute_trigger_actions", new_callable=AsyncMock
        ) as mock_exec,
    ):
        mock_fetch.return_value = [trigger]
        mock_exec.return_value = [
            MagicMock(status=ExecutionStatus.COMPLETED, success=True)
        ]

        result = await rules_engine.process_event(sample_event)

        assert result["triggers_matched"] == 1
        assert result["actions_executed"] == 1
        mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_action_retry_logic(rules_engine, sample_event):
    """Test that actions are retried on failure."""
    trigger = TriggerRule(
        trigger_id=uuid4(),
        rule_name="Retry Test",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        created_by="test_user",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED],
            condition_group=ConditionGroup(operator="AND", conditions=[]),
        ),
        actions=[],
    )

    action_config = ActionConfig(
        action_type=ActionType.SEND_WEBHOOK,
        config={"url": "http://bad-url"},
        retry_on_failure=True,
        max_retries=2,
        retry_delay_seconds=1,
    )

    # Mock execution to fail twice then succeed
    # Also mock asyncio.sleep to skip waiting
    with (
        patch.object(
            rules_engine, "_execute_action_by_type", new_callable=AsyncMock
        ) as mock_exec_type,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_exec_type.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            {"status": "sent"},
        ]

        execution = await rules_engine._execute_action(
            trigger, sample_event, action_config
        )

        assert execution.success is True
        assert execution.attempt_number == 3
        assert mock_exec_type.call_count == 3
        assert mock_sleep.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_check(rules_engine):
    """Test rate limiting logic."""
    trigger = TriggerRule(
        trigger_id=uuid4(),
        rule_name="Rate Limit Test",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        created_by="test_user",
        condition=TriggerCondition(
            event_types=[EventType.MEMORY_CREATED],
            condition_group=ConditionGroup(operator="AND", conditions=[]),
            max_executions_per_hour=10,
        ),
        actions=[],
        executions_this_hour=5,
        hour_window_start=datetime.now(timezone.utc),
    )

    # Under limit
    assert await rules_engine._check_rate_limit(trigger) is True

    # Over limit
    trigger.executions_this_hour = 10
    assert await rules_engine._check_rate_limit(trigger) is False

    # New window (reset)
    trigger.executions_this_hour = 10
    trigger.hour_window_start = datetime.now(timezone.utc) - timedelta(hours=2)

    # Should reset and return True
    # DB execute mock needed
    rules_engine.pool.execute = AsyncMock()

    assert await rules_engine._check_rate_limit(trigger) is True
    rules_engine.pool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_webhook_action(rules_engine, sample_event):
    """Test webhook action execution using aiohttp mock."""
    config = {"url": "http://test.com/webhook"}
    # trigger is not used

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_post.return_value = mock_response

        result = await rules_engine._action_send_webhook(config, sample_event)

        assert result["status"] == "sent"
        assert result["status_code"] == 200
