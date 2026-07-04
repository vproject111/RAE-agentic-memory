"""
Trigger Repository - Database operations for event triggers and workflows

Provides CRUD operations and queries for trigger rules, workflows,
and their execution histories.
"""

import json
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import asyncpg
import structlog

logger = structlog.get_logger(__name__)


class TriggerRepository:
    """Repository for trigger rule operations."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_trigger(
        self,
        tenant_id: str,
        project_id: str,
        rule_name: str,
        event_types: List[str],
        conditions: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        created_by: str,
        description: Optional[str] = None,
        condition_operator: str = "AND",
        priority: int = 0,
        status: str = "active",
        retry_config: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new trigger rule.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            rule_name: Name of the trigger rule
            event_types: List of event types to match
            conditions: List of condition objects
            actions: List of action objects
            created_by: User who created the trigger
            description: Optional description
            condition_operator: 'AND' or 'OR' for combining conditions
            priority: Priority level (higher fires first)
            status: Initial status ('active', 'inactive', etc.)
            retry_config: Optional retry configuration
            template_id: If created from template
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created trigger record as dict
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO trigger_rules (
                    tenant_id, project_id, rule_name, description,
                    event_types, conditions, condition_operator, actions,
                    priority, status, retry_config, created_by,
                    template_id, tags, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING *
                """,
                tenant_id,
                project_id,
                rule_name,
                description,
                event_types,
                json.dumps(conditions),
                condition_operator,
                json.dumps(actions),
                priority,
                status,
                json.dumps(retry_config) if retry_config else None,
                created_by,
                template_id,
                tags or [],
                json.dumps(metadata) if metadata else "{}",
            )

        logger.info(
            "trigger_created",
            trigger_id=record["id"],
            rule_name=rule_name,
            tenant_id=tenant_id,
        )

        return dict(record)

    async def get_trigger(
        self, trigger_id: UUID, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get trigger rule by ID.

        Args:
            trigger_id: Trigger UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Trigger record dict or None if not found
        """
        async with self.pool.acquire() as conn:
            if tenant_id:
                record = await conn.fetchrow(
                    "SELECT * FROM trigger_rules WHERE id = $1 AND tenant_id = $2",
                    trigger_id,
                    tenant_id,
                )
            else:
                record = await conn.fetchrow(
                    "SELECT * FROM trigger_rules WHERE id = $1", trigger_id
                )

        return dict(record) if record else None

    async def list_triggers(
        self,
        tenant_id: str,
        project_id: str,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List trigger rules for a tenant/project.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            status_filter: Optional status filter
            limit: Maximum number of records
            offset: Pagination offset

        Returns:
            List of trigger records
        """
        async with self.pool.acquire() as conn:
            if status_filter:
                records = await conn.fetch(
                    """
                    SELECT * FROM trigger_rules
                    WHERE tenant_id = $1 AND project_id = $2 AND status = $3
                    ORDER BY priority DESC, created_at DESC
                    LIMIT $4 OFFSET $5
                    """,
                    tenant_id,
                    project_id,
                    status_filter,
                    limit,
                    offset,
                )
            else:
                records = await conn.fetch(
                    """
                    SELECT * FROM trigger_rules
                    WHERE tenant_id = $1 AND project_id = $2
                    ORDER BY priority DESC, created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    tenant_id,
                    project_id,
                    limit,
                    offset,
                )

        return [dict(r) for r in records]

    async def update_trigger(
        self,
        trigger_id: UUID,
        tenant_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update trigger rule fields.

        Args:
            trigger_id: Trigger UUID
            tenant_id: Tenant identifier (for authorization)
            updates: Dictionary of fields to update

        Returns:
            Updated trigger record or None if not found
        """
        # Build dynamic UPDATE query
        allowed_fields = {
            "rule_name",
            "description",
            "event_types",
            "conditions",
            "condition_operator",
            "actions",
            "priority",
            "status",
            "retry_config",
            "tags",
            "metadata",
        }

        # Filter to allowed fields
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return await self.get_trigger(trigger_id, tenant_id)

        # Convert complex types to JSON
        if "conditions" in filtered_updates:
            filtered_updates["conditions"] = json.dumps(filtered_updates["conditions"])
        if "actions" in filtered_updates:
            filtered_updates["actions"] = json.dumps(filtered_updates["actions"])
        if "retry_config" in filtered_updates:
            filtered_updates["retry_config"] = json.dumps(
                filtered_updates["retry_config"]
            )
        if "metadata" in filtered_updates:
            filtered_updates["metadata"] = json.dumps(filtered_updates["metadata"])

        # Build SET clause
        set_clauses = [f"{k} = ${i + 3}" for i, k in enumerate(filtered_updates.keys())]
        set_clause = ", ".join(set_clauses)

        query = f"""
            UPDATE trigger_rules
            SET {set_clause}
            WHERE id = $1 AND tenant_id = $2
            RETURNING *
        """  # nosec
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                query, trigger_id, tenant_id, *filtered_updates.values()
            )

        if record:
            logger.info(
                "trigger_updated", trigger_id=trigger_id, fields=list(updates.keys())
            )

        return dict(record) if record else None

    async def delete_trigger(self, trigger_id: UUID, tenant_id: str) -> bool:
        """
        Delete trigger rule.

        Args:
            trigger_id: Trigger UUID
            tenant_id: Tenant identifier (for authorization)

        Returns:
            True if deleted, False if not found
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM trigger_rules WHERE id = $1 AND tenant_id = $2",
                trigger_id,
                tenant_id,
            )

        deleted = bool(result.endswith("1"))  # "DELETE 1" means one row deleted

        if deleted:
            logger.info("trigger_deleted", trigger_id=trigger_id, tenant_id=tenant_id)

        return deleted

    async def get_active_triggers_for_event(
        self, event_type: str, tenant_id: str, project_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get active triggers that match a specific event type.

        Args:
            event_type: Event type to match
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            List of matching trigger records, ordered by priority
        """
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT * FROM trigger_rules
                WHERE tenant_id = $1
                  AND project_id = $2
                  AND status = 'active'
                  AND $3 = ANY(event_types)
                ORDER BY priority DESC, created_at ASC
                """,
                tenant_id,
                project_id,
                event_type,
            )

        return [dict(r) for r in records]

    async def record_execution(
        self,
        trigger_id: UUID,
        tenant_id: str,
        project_id: str,
        event_id: Optional[UUID],
        event_type: str,
        event_payload: Optional[Dict[str, Any]] = None,
        status: str = "pending",
        actions_executed: int = 0,
        actions_succeeded: int = 0,
        actions_failed: int = 0,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
        action_results: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UUID:
        """
        Record a trigger execution.

        Args:
            trigger_id: Trigger UUID
            tenant_id: Tenant identifier
            project_id: Project identifier
            event_id: Event UUID that triggered execution
            event_type: Event type
            event_payload: Event data
            status: Execution status
            actions_executed: Number of actions executed
            actions_succeeded: Number of successful actions
            actions_failed: Number of failed actions
            duration_ms: Execution duration
            error_message: Error message if failed
            error_details: Detailed error information
            action_results: Results for each action
            metadata: Additional metadata

        Returns:
            Execution UUID
        """
        async with self.pool.acquire() as conn:
            execution_id = await conn.fetchval(
                """
                INSERT INTO trigger_executions (
                    trigger_id, tenant_id, project_id,
                    event_id, event_type, event_payload,
                    status, actions_executed, actions_succeeded, actions_failed,
                    duration_ms, error_message, error_details,
                    action_results, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id
                """,
                trigger_id,
                tenant_id,
                project_id,
                event_id,
                event_type,
                json.dumps(event_payload) if event_payload else None,
                status,
                actions_executed,
                actions_succeeded,
                actions_failed,
                duration_ms,
                error_message,
                json.dumps(error_details) if error_details else None,
                json.dumps(action_results) if action_results else None,
                json.dumps(metadata) if metadata else "{}",
            )

        logger.info(
            "trigger_execution_recorded",
            execution_id=execution_id,
            trigger_id=trigger_id,
            status=status,
        )

        return cast(UUID, execution_id)

    async def update_execution(
        self, execution_id: UUID, updates: Dict[str, Any]
    ) -> bool:
        """
        Update trigger execution record.

        Args:
            execution_id: Execution UUID
            updates: Fields to update

        Returns:
            True if updated successfully
        """
        allowed_fields = {
            "status",
            "actions_executed",
            "actions_succeeded",
            "actions_failed",
            "completed_at",
            "duration_ms",
            "error_message",
            "error_details",
            "action_results",
            "retry_count",
        }

        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered_updates:
            return False

        # Convert complex types
        if "error_details" in filtered_updates:
            filtered_updates["error_details"] = json.dumps(
                filtered_updates["error_details"]
            )
        if "action_results" in filtered_updates:
            filtered_updates["action_results"] = json.dumps(
                filtered_updates["action_results"]
            )

        set_clauses = [f"{k} = ${i + 2}" for i, k in enumerate(filtered_updates.keys())]
        set_clause = ", ".join(set_clauses)

        query = f"""
            UPDATE trigger_executions
            SET {set_clause}
            WHERE id = $1
        """  # nosec
        async with self.pool.acquire() as conn:
            await conn.execute(query, execution_id, *filtered_updates.values())

        return True

    async def get_execution_history(
        self,
        trigger_id: UUID,
        tenant_id: str,
        limit: int = 100,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for a trigger.

        Args:
            trigger_id: Trigger UUID
            tenant_id: Tenant identifier
            limit: Maximum number of records
            status_filter: Optional status filter

        Returns:
            List of execution records
        """
        async with self.pool.acquire() as conn:
            if status_filter:
                records = await conn.fetch(
                    """
                    SELECT * FROM trigger_executions
                    WHERE trigger_id = $1 AND tenant_id = $2 AND status = $3
                    ORDER BY started_at DESC
                    LIMIT $4
                    """,
                    trigger_id,
                    tenant_id,
                    status_filter,
                    limit,
                )
            else:
                records = await conn.fetch(
                    """
                    SELECT * FROM trigger_executions
                    WHERE trigger_id = $1 AND tenant_id = $2
                    ORDER BY started_at DESC
                    LIMIT $3
                    """,
                    trigger_id,
                    tenant_id,
                    limit,
                )

        return [dict(r) for r in records]


class WorkflowRepository:
    """Repository for workflow operations."""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create_workflow(
        self,
        tenant_id: str,
        project_id: str,
        workflow_name: str,
        steps: List[Dict[str, Any]],
        created_by: str,
        description: Optional[str] = None,
        execution_mode: str = "sequential",
        status: str = "active",
        timeout_seconds: int = 3600,
        retry_policy: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new workflow.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            workflow_name: Workflow name
            steps: List of workflow steps
            created_by: User who created the workflow
            description: Optional description
            execution_mode: 'sequential', 'parallel', or 'dag'
            status: Initial status
            timeout_seconds: Workflow timeout
            retry_policy: Optional retry policy
            tags: Optional tags
            metadata: Optional metadata

        Returns:
            Created workflow record as dict
        """
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO workflows (
                    tenant_id, project_id, workflow_name, description,
                    steps, execution_mode, status, timeout_seconds,
                    retry_policy, created_by, tags, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                tenant_id,
                project_id,
                workflow_name,
                description,
                json.dumps(steps),
                execution_mode,
                status,
                timeout_seconds,
                json.dumps(retry_policy) if retry_policy else None,
                created_by,
                tags or [],
                json.dumps(metadata) if metadata else "{}",
            )

        logger.info(
            "workflow_created",
            workflow_id=record["id"],
            workflow_name=workflow_name,
            tenant_id=tenant_id,
        )

        return dict(record)

    async def get_workflow(
        self, workflow_id: UUID, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get workflow by ID."""
        async with self.pool.acquire() as conn:
            if tenant_id:
                record = await conn.fetchrow(
                    "SELECT * FROM workflows WHERE id = $1 AND tenant_id = $2",
                    workflow_id,
                    tenant_id,
                )
            else:
                record = await conn.fetchrow(
                    "SELECT * FROM workflows WHERE id = $1", workflow_id
                )

        return dict(record) if record else None

    async def list_workflows(
        self,
        tenant_id: str,
        project_id: str,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List workflows for a tenant/project."""
        async with self.pool.acquire() as conn:
            if status_filter:
                records = await conn.fetch(
                    """
                    SELECT * FROM workflows
                    WHERE tenant_id = $1 AND project_id = $2 AND status = $3
                    ORDER BY created_at DESC
                    LIMIT $4 OFFSET $5
                    """,
                    tenant_id,
                    project_id,
                    status_filter,
                    limit,
                    offset,
                )
            else:
                records = await conn.fetch(
                    """
                    SELECT * FROM workflows
                    WHERE tenant_id = $1 AND project_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3 OFFSET $4
                    """,
                    tenant_id,
                    project_id,
                    limit,
                    offset,
                )

        return [dict(r) for r in records]

    async def delete_workflow(self, workflow_id: UUID, tenant_id: str) -> bool:
        """Delete workflow."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM workflows WHERE id = $1 AND tenant_id = $2",
                workflow_id,
                tenant_id,
            )

        deleted = bool(result.endswith("1"))

        if deleted:
            logger.info(
                "workflow_deleted", workflow_id=workflow_id, tenant_id=tenant_id
            )

        return deleted
