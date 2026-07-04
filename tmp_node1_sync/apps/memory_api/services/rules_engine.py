"""
Rules Engine - Event-Driven Automation System

This service implements:
- Condition evaluation with complex logic
- Event matching and filtering
- Action execution with retry logic
- Workflow orchestration
- Rate limiting and cooldowns
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

import asyncpg
import structlog

from apps.memory_api.models.event_models import (
    ActionConfig,
    ActionExecution,
    ActionType,
    Condition,
    ConditionGroup,
    ConditionOperator,
    Event,
    EventType,
    ExecutionStatus,
    TriggerRule,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Rules Engine
# ============================================================================


class RulesEngine:
    """
    Event-driven automation rules engine.

    Features:
    - Event matching with complex conditions
    - AND/OR condition groups
    - Rate limiting and cooldowns
    - Action execution with retries
    - Workflow orchestration
    - Execution history tracking
    """

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize rules engine.

        Args:
            pool: Database connection pool
        """
        self.pool = pool

    async def process_event(self, event: Event) -> Dict[str, Any]:
        """
        Process an event and execute matching triggers.

        Args:
            event: Event to process

        Returns:
            Dictionary with execution results
        """
        logger.info(
            "processing_event",
            event_id=event.event_id,
            event_type=event.event_type.value,
            tenant_id=event.tenant_id,
        )

        # Fetch active trigger rules for this tenant/project
        triggers = await self._fetch_active_triggers(
            event.tenant_id, event.project_id, event.event_type
        )

        if not triggers:
            logger.info("no_matching_triggers", event_type=event.event_type.value)
            return {
                "event_id": event.event_id,
                "triggers_matched": 0,
                "actions_executed": 0,
            }

        # Evaluate each trigger
        matched_triggers = []
        for trigger in triggers:
            if await self._evaluate_trigger(trigger, event):
                matched_triggers.append(trigger)

        logger.info("triggers_matched", count=len(matched_triggers))

        # Execute actions for matched triggers
        execution_results = []
        for trigger in matched_triggers:
            results = await self._execute_trigger_actions(trigger, event)
            execution_results.extend(results)

        return {
            "event_id": event.event_id,
            "triggers_matched": len(matched_triggers),
            "actions_executed": len(execution_results),
            "executions": execution_results,
        }

    # ========================================================================
    # Condition Evaluation
    # ========================================================================

    async def _evaluate_trigger(self, trigger: TriggerRule, event: Event) -> bool:
        """
        Evaluate if a trigger should fire for an event.

        Checks:
        1. Event type matches
        2. Conditions are met
        3. Rate limits not exceeded
        4. Cooldown period passed

        Args:
            trigger: Trigger rule
            event: Event to evaluate

        Returns:
            True if trigger should fire
        """
        # Check rate limiting
        if not await self._check_rate_limit(trigger):
            logger.info("trigger_rate_limited", trigger_id=trigger.trigger_id)
            return False

        # Check cooldown
        if not self._check_cooldown(trigger):
            logger.info("trigger_in_cooldown", trigger_id=trigger.trigger_id)
            return False

        # Evaluate conditions
        if trigger.condition.condition_group:
            result = self._evaluate_condition_group(
                trigger.condition.condition_group, event.payload
            )

            logger.info(
                "condition_evaluated", trigger_id=trigger.trigger_id, result=result
            )

            return result

        # No conditions - always fire on matching event type
        return True

    def _evaluate_condition_group(
        self, group: ConditionGroup, data: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a condition group with AND/OR logic.

        Args:
            group: Condition group to evaluate
            data: Event payload data

        Returns:
            True if condition group passes
        """
        results = []

        # Evaluate individual conditions
        for condition in group.conditions:
            if isinstance(condition, Condition):
                result = self._evaluate_condition(condition, data)
                results.append(result)
            elif isinstance(condition, ConditionGroup):
                result = self._evaluate_condition_group(condition, data)
                results.append(result)

        # Evaluate nested groups
        for nested_group in group.groups:
            result = self._evaluate_condition_group(nested_group, data)
            results.append(result)

        # Apply operator
        if group.operator.upper() == "AND":
            return all(results) if results else True
        elif group.operator.upper() == "OR":
            return any(results) if results else False
        else:
            logger.warning("unknown_operator", operator=group.operator)
            return False

    def _evaluate_condition(self, condition: Condition, data: Dict[str, Any]) -> bool:
        """
        Evaluate a single condition.

        Supports:
        - Dot notation for nested fields (e.g., "payload.importance")
        - All comparison operators
        - Null checks
        - Regex matching

        Args:
            condition: Condition to evaluate
            data: Event data

        Returns:
            True if condition passes
        """
        # Get field value (supports dot notation)
        field_value = self._get_nested_value(data, condition.field)

        # Evaluate based on operator
        result = False

        if condition.operator == ConditionOperator.EQUALS:
            result = field_value == condition.value

        elif condition.operator == ConditionOperator.NOT_EQUALS:
            result = field_value != condition.value

        elif condition.operator == ConditionOperator.GREATER_THAN:
            result = field_value > condition.value

        elif condition.operator == ConditionOperator.LESS_THAN:
            result = field_value < condition.value

        elif condition.operator == ConditionOperator.GREATER_EQUAL:
            result = field_value >= condition.value

        elif condition.operator == ConditionOperator.LESS_EQUAL:
            result = field_value <= condition.value

        elif condition.operator == ConditionOperator.CONTAINS:
            if isinstance(field_value, str):
                if condition.case_sensitive:
                    result = condition.value in field_value
                else:
                    result = condition.value.lower() in field_value.lower()
            elif isinstance(field_value, (list, tuple)):
                result = condition.value in field_value
            else:
                result = False

        elif condition.operator == ConditionOperator.NOT_CONTAINS:
            if isinstance(field_value, str):
                if condition.case_sensitive:
                    result = condition.value not in field_value
                else:
                    result = condition.value.lower() not in field_value.lower()
            elif isinstance(field_value, (list, tuple)):
                result = condition.value not in field_value
            else:
                result = True

        elif condition.operator == ConditionOperator.IN:
            result = field_value in condition.value

        elif condition.operator == ConditionOperator.NOT_IN:
            result = field_value not in condition.value

        elif condition.operator == ConditionOperator.MATCHES_REGEX:
            if isinstance(field_value, str):
                result = bool(re.match(condition.value, field_value))
            else:
                result = False

        elif condition.operator == ConditionOperator.IS_NULL:
            result = field_value is None

        elif condition.operator == ConditionOperator.IS_NOT_NULL:
            result = field_value is not None

        # Apply negation if specified
        if condition.negate:
            result = not result

        return result

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

        Args:
            data: Data dictionary
            field_path: Path like "payload.importance"

        Returns:
            Field value or None
        """
        keys = field_path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    # ========================================================================
    # Rate Limiting and Cooldown
    # ========================================================================

    async def _check_rate_limit(self, trigger: TriggerRule) -> bool:
        """
        Check if trigger is within rate limit.

        Args:
            trigger: Trigger rule

        Returns:
            True if within rate limit
        """
        if not trigger.condition.max_executions_per_hour:
            return True

        # Check if we're in a new hour window
        now = datetime.now(timezone.utc)
        if (
            trigger.hour_window_start is None
            or (now - trigger.hour_window_start).total_seconds() >= 3600
        ):
            # Reset counter for new hour
            await self.pool.execute(
                """
                UPDATE trigger_rules
                SET executions_this_hour = 0, hour_window_start = $1
                WHERE trigger_id = $2
                """,
                now,
                trigger.trigger_id,
            )
            return True

        # Check current count
        return trigger.executions_this_hour < trigger.condition.max_executions_per_hour

    def _check_cooldown(self, trigger: TriggerRule) -> bool:
        """
        Check if cooldown period has passed.

        Args:
            trigger: Trigger rule

        Returns:
            True if cooldown passed
        """
        if not trigger.condition.cooldown_seconds:
            return True

        if not trigger.last_executed_at:
            return True

        elapsed = (
            datetime.now(timezone.utc) - trigger.last_executed_at
        ).total_seconds()
        return elapsed >= trigger.condition.cooldown_seconds

    # ========================================================================
    # Action Execution
    # ========================================================================

    async def _execute_trigger_actions(
        self, trigger: TriggerRule, event: Event
    ) -> List[ActionExecution]:
        """
        Execute all actions for a triggered rule.

        Args:
            trigger: Trigger rule
            event: Event that triggered it

        Returns:
            List of action execution records
        """
        logger.info(
            "executing_trigger_actions",
            trigger_id=trigger.trigger_id,
            actions=len(trigger.actions),
        )

        executions = []

        # Execute each action
        for action_config in trigger.actions:
            execution = await self._execute_action(
                trigger=trigger, event=event, action_config=action_config
            )
            executions.append(execution)

        # Update trigger execution count
        await self.pool.execute(
            """
            UPDATE trigger_rules
            SET execution_count = execution_count + 1,
                last_executed_at = $1,
                executions_this_hour = executions_this_hour + 1
            WHERE trigger_id = $2
            """,
            datetime.now(timezone.utc),
            trigger.trigger_id,
        )

        return executions

    async def _execute_action(
        self,
        trigger: TriggerRule,
        event: Event,
        action_config: ActionConfig,
        attempt: int = 1,
    ) -> ActionExecution:
        """
        Execute a single action.

        Handles:
        - Action-specific logic
        - Error handling
        - Retry logic
        - Execution tracking

        Args:
            trigger: Trigger rule
            event: Event that triggered
            action_config: Action configuration
            attempt: Retry attempt number

        Returns:
            ActionExecution record
        """
        execution_id = uuid4()
        started_at = datetime.now(timezone.utc)

        logger.info(
            "executing_action",
            execution_id=execution_id,
            action_type=action_config.action_type.value,
            attempt=attempt,
        )

        try:
            # Execute action based on type
            result = await self._execute_action_by_type(
                action_config.action_type, action_config.config, event, trigger
            )

            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Create successful execution record
            execution = ActionExecution(
                execution_id=execution_id,
                trigger_id=trigger.trigger_id,
                event_id=event.event_id,
                event_type=event.event_type,
                action_type=action_config.action_type,
                action_config=action_config.config,
                status=ExecutionStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                success=True,
                result=result,
                attempt_number=attempt,
                max_attempts=action_config.max_retries + 1,
                tenant_id=trigger.tenant_id,
                project_id=trigger.project_id,
            )

            logger.info(
                "action_executed_successfully",
                execution_id=execution_id,
                duration_ms=duration_ms,
            )

            return execution

        except Exception as e:
            logger.error(
                "action_execution_failed",
                execution_id=execution_id,
                error=str(e),
                attempt=attempt,
            )

            # Retry if configured
            if action_config.retry_on_failure and attempt <= action_config.max_retries:
                logger.info("retrying_action", attempt=attempt + 1)
                await asyncio.sleep(action_config.retry_delay_seconds)
                return await self._execute_action(
                    trigger, event, action_config, attempt + 1
                )

            # Create failed execution record
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            execution = ActionExecution(
                execution_id=execution_id,
                trigger_id=trigger.trigger_id,
                event_id=event.event_id,
                event_type=event.event_type,
                action_type=action_config.action_type,
                action_config=action_config.config,
                status=ExecutionStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e),
                attempt_number=attempt,
                max_attempts=action_config.max_retries + 1,
                tenant_id=trigger.tenant_id,
                project_id=trigger.project_id,
            )

            return execution

    async def _execute_action_by_type(
        self,
        action_type: ActionType,
        config: Dict[str, Any],
        event: Event,
        trigger: TriggerRule,
    ) -> Dict[str, Any]:
        """
        Execute action based on type.

        Args:
            action_type: Type of action
            config: Action configuration
            event: Triggering event
            trigger: Trigger rule

        Returns:
            Action result dictionary
        """
        if action_type == ActionType.SEND_NOTIFICATION:
            return await self._action_send_notification(config, event)

        elif action_type == ActionType.SEND_WEBHOOK:
            return await self._action_send_webhook(config, event)

        elif action_type == ActionType.GENERATE_REFLECTION:
            return await self._action_generate_reflection(config, event)

        elif action_type == ActionType.EXTRACT_SEMANTICS:
            return await self._action_extract_semantics(config, event)

        elif action_type == ActionType.APPLY_DECAY:
            return await self._action_apply_decay(config, event)

        elif action_type == ActionType.CREATE_SNAPSHOT:
            return await self._action_create_snapshot(config, event)

        elif action_type == ActionType.RUN_EVALUATION:
            return await self._action_run_evaluation(config, event)

        else:
            logger.warning("unsupported_action_type", action_type=action_type.value)
            return {"status": "skipped", "reason": "Unsupported action type"}

    # ========================================================================
    # Action Implementations
    # ========================================================================

    async def _action_send_notification(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Send notification action"""
        logger.info("sending_notification", channel=config.get("channel"))

        # Placeholder - would integrate with notification service
        return {
            "status": "sent",
            "channel": config.get("channel", "default"),
            "message": config.get("message", "Notification sent"),
        }

    async def _action_send_webhook(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Send webhook action"""
        import aiohttp

        url = config.get("url")
        if not url:
            raise ValueError("Webhook URL required")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=event.model_dump()) as response:
                return {"status": "sent", "status_code": response.status, "url": url}

    async def _action_generate_reflection(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Generate reflection action"""
        logger.info("generating_reflection")

        # Would call reflection pipeline
        return {"status": "queued", "action": "reflection_generation"}

    async def _action_extract_semantics(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Extract semantics action"""
        logger.info("extracting_semantics")

        # Would call semantic extractor
        return {"status": "queued", "action": "semantic_extraction"}

    async def _action_apply_decay(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Apply decay action"""
        logger.info("applying_decay")

        threshold_days = config.get("threshold_days", 60)

        # Would call decay function
        return {
            "status": "completed",
            "action": "decay_applied",
            "threshold_days": threshold_days,
        }

    async def _action_create_snapshot(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Create snapshot action"""
        logger.info("creating_snapshot")

        # Would call snapshot creation
        return {"status": "created", "action": "snapshot"}

    async def _action_run_evaluation(
        self, config: Dict[str, Any], event: Event
    ) -> Dict[str, Any]:
        """Run evaluation action"""
        logger.info("running_evaluation")

        # Would call evaluation service
        return {"status": "queued", "action": "evaluation"}

    # ========================================================================
    # Data Access
    # ========================================================================

    async def _fetch_active_triggers(
        self, tenant_id: str, project_id: str, event_type: EventType
    ) -> List[TriggerRule]:
        """
        Fetch active triggers matching event type.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            event_type: Event type

        Returns:
            List of matching trigger rules
        """
        # Placeholder - would query database
        # For now return empty list
        return []
