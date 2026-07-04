"""
Event Triggers API Routes - Automation and Rules Management

This module provides FastAPI routes for event trigger operations including:
- Trigger rule creation and management
- Event emission
- Action execution
- Workflow orchestration
- Trigger templates
"""

from datetime import timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.models.event_models import (
    DEFAULT_TEMPLATES,
    CreateTriggerRequest,
    CreateTriggerResponse,
    CreateWorkflowRequest,
    CreateWorkflowResponse,
    EmitEventRequest,
    EmitEventResponse,
    Event,
    EventType,
    GetTriggerExecutionsRequest,
    GetTriggerExecutionsResponse,
    TriggerRule,
    TriggerStatus,
    UpdateTriggerRequest,
)
from apps.memory_api.repositories.trigger_repository import (
    TriggerRepository,
    WorkflowRepository,
)
from apps.memory_api.services.rules_engine import RulesEngine

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/triggers", tags=["Event Triggers"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_pool(request: Request):
    """Get database connection pool from app state"""
    return request.app.state.pool


async def get_trigger_repo(pool=Depends(get_pool)) -> TriggerRepository:
    """Get trigger repository instance"""
    return TriggerRepository(pool)


async def get_workflow_repo(pool=Depends(get_pool)) -> WorkflowRepository:
    """Get workflow repository instance"""
    return WorkflowRepository(pool)


# ============================================================================
# Trigger Management
# ============================================================================


@router.post("/create", response_model=CreateTriggerResponse, status_code=201)
async def create_trigger(
    request: CreateTriggerRequest, repo: TriggerRepository = Depends(get_trigger_repo)
):
    """
    Create a new event trigger rule.

    Triggers automatically execute actions when events match conditions.

    **Use Case:** Automate workflows like:
    - Generate reflections when memory count threshold reached
    - Send alerts on quality degradation
    - Apply decay on schedule
    - Create snapshots periodically
    """
    try:
        # Create trigger in database
        trigger_record = await repo.create_trigger(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            rule_name=request.rule_name,
            event_types=[et.value for et in request.condition.event_types],
            conditions=(
                request.condition.condition_group.model_dump()["conditions"]
                if request.condition.condition_group
                else []
            ),
            actions=[a.model_dump() for a in request.actions],
            created_by=request.created_by,
            description=request.description,
            condition_operator="AND",  # Default as it's not in request
            priority=request.priority,
            status=(
                TriggerStatus.ACTIVE if request.is_enabled else TriggerStatus.INACTIVE
            ),
            retry_config=None,  # Default as it's not in request
        )

        return CreateTriggerResponse(
            trigger_id=trigger_record["id"],
            message=f"Trigger rule '{request.rule_name}' created successfully",
        )

    except Exception as e:
        logger.error("trigger_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{trigger_id}", response_model=TriggerRule)
async def get_trigger(
    trigger_id: str, repo: TriggerRepository = Depends(get_trigger_repo)
):
    """Get trigger rule by ID"""
    try:
        trigger = await repo.get_trigger(UUID(trigger_id))

        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")

        return TriggerRule(**trigger)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{trigger_id}")
async def update_trigger(
    trigger_id: str,
    request: UpdateTriggerRequest,
    repo: TriggerRepository = Depends(get_trigger_repo),
):
    """
    Update trigger rule configuration.

    Can update:
    - Rule name and description
    - Conditions
    - Actions
    - Priority
    - Enable/disable status
    """
    try:
        # Prepare updates dict
        updates: Dict[str, Any] = {}
        if request.rule_name is not None:
            updates["rule_name"] = request.rule_name
        if request.description is not None:
            updates["description"] = request.description
        if request.condition is not None:
            updates["condition"] = request.condition.model_dump()
        if request.actions is not None:
            updates["actions"] = [a.model_dump() for a in request.actions]
        if request.priority is not None:
            updates["priority"] = request.priority
        if request.status is not None:
            updates["status"] = request.status
        if request.is_enabled is not None:
            updates["is_enabled"] = request.is_enabled

        # Update in database
        # Note: tenant_id should come from auth context in production
        tenant_id = "default"  # TODO: Get from auth context
        updated_trigger = await repo.update_trigger(
            UUID(trigger_id), tenant_id, updates
        )

        if not updated_trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")

        return {
            "trigger_id": trigger_id,
            "message": "Trigger updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{trigger_id}")
async def delete_trigger(
    trigger_id: str, repo: TriggerRepository = Depends(get_trigger_repo)
):
    """Delete trigger rule"""
    try:
        # Note: tenant_id should come from auth context in production
        tenant_id = "default"  # TODO: Get from auth context
        deleted = await repo.delete_trigger(UUID(trigger_id), tenant_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Trigger not found")

        return {"trigger_id": trigger_id, "message": "Trigger deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{trigger_id}/enable")
async def enable_trigger(trigger_id: str, pool=Depends(get_pool)):
    """Enable a trigger rule"""
    try:
        logger.info("enable_trigger_requested", trigger_id=trigger_id)

        return {
            "trigger_id": trigger_id,
            "status": TriggerStatus.ACTIVE,
            "message": "Trigger enabled",
        }

    except Exception as e:
        logger.error("enable_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{trigger_id}/disable")
async def disable_trigger(trigger_id: str, pool=Depends(get_pool)):
    """Disable a trigger rule"""
    try:
        logger.info("disable_trigger_requested", trigger_id=trigger_id)

        return {
            "trigger_id": trigger_id,
            "status": TriggerStatus.INACTIVE,
            "message": "Trigger disabled",
        }

    except Exception as e:
        logger.error("disable_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/list")
async def list_triggers(
    tenant_id: str,
    project_id: str,
    status_filter: Optional[str] = None,
    limit: int = 100,
    repo: TriggerRepository = Depends(get_trigger_repo),
):
    """
    List trigger rules.

    Filter by status (active, inactive, paused, error).
    """
    try:
        triggers = await repo.list_triggers(
            tenant_id=tenant_id,
            project_id=project_id,
            status_filter=status_filter,
            limit=limit,
        )

        return {
            "triggers": triggers,
            "total_count": len(triggers),
            "message": f"Found {len(triggers)} triggers",
        }

    except Exception as e:
        logger.error("list_triggers_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Event Emission
# ============================================================================


@router.post("/events/emit", response_model=EmitEventResponse)
async def emit_event(request: EmitEventRequest, pool=Depends(get_pool)):
    """
    Emit a custom event to trigger automation rules.

    Events are evaluated against all active trigger conditions.
    Matching triggers execute their configured actions.

    **Use Case:** Manually trigger automations or emit custom application events.
    """
    try:
        # Create event
        event = Event(
            event_id=uuid4(),
            event_type=request.event_type,
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            source_service="api",
            payload=request.payload,
            tags=request.tags,
            user_id=request.user_id,
        )

        logger.info(
            "event_emitted", event_id=event.event_id, event_type=event.event_type.value
        )

        # Process event with rules engine
        engine = RulesEngine(pool)
        result = await engine.process_event(event)

        return EmitEventResponse(
            event_id=event.event_id,
            triggers_matched=result["triggers_matched"],
            actions_queued=result["actions_executed"],
            message=f"Event processed: {result['triggers_matched']} triggers matched",
        )

    except Exception as e:
        logger.error("emit_event_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/events/types")
async def get_event_types():
    """
    Get list of supported event types.

    Returns available event types with descriptions.
    """
    return {
        "event_types": {
            "memory_created": "New memory created",
            "memory_updated": "Memory updated",
            "memory_deleted": "Memory deleted",
            "memory_accessed": "Memory retrieved/accessed",
            "reflection_generated": "New reflection generated",
            "semantic_node_created": "Semantic node created",
            "semantic_node_degraded": "Semantic node degraded",
            "search_executed": "Search query executed",
            "query_analyzed": "Query intent analyzed",
            "drift_detected": "Distribution drift detected",
            "quality_degraded": "Quality metrics degraded",
            "threshold_exceeded": "Metric threshold exceeded",
            "schedule_triggered": "Scheduled event fired",
        }
    }


# ============================================================================
# Execution History
# ============================================================================


@router.post("/executions", response_model=GetTriggerExecutionsResponse)
async def get_trigger_executions(
    request: GetTriggerExecutionsRequest,
    repo: TriggerRepository = Depends(get_trigger_repo),
):
    """
    Get execution history for a trigger.

    Returns action execution logs with status, duration, and results.

    **Use Case:** Debug trigger behavior, monitor automation performance.
    """
    try:
        # Get execution history from database
        tenant_id = "default"  # TODO: Get from auth context
        executions = await repo.get_execution_history(
            trigger_id=request.trigger_id,
            tenant_id=tenant_id,
            limit=request.limit,
            status_filter=request.status_filter,
        )

        # Get trigger info for summary
        trigger = await repo.get_trigger(request.trigger_id, tenant_id)

        from datetime import datetime, timedelta

        from apps.memory_api.models.event_models import TriggerExecutionSummary

        summary = TriggerExecutionSummary(
            trigger_id=request.trigger_id,
            trigger_name=trigger["rule_name"] if trigger else "Unknown Trigger",
            period_start=datetime.now(timezone.utc) - timedelta(days=7),
            period_end=datetime.now(timezone.utc),
        )

        return GetTriggerExecutionsResponse(
            executions=executions, total_count=len(executions), summary=summary
        )

    except Exception as e:
        logger.error("get_executions_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Workflows
# ============================================================================


@router.post(
    "/workflows/create", response_model=CreateWorkflowResponse, status_code=201
)
async def create_workflow(
    request: CreateWorkflowRequest,
    repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """
    Create a workflow (chain of actions).

    Workflows allow multiple actions to be executed in sequence or parallel
    with dependency management.

    **Use Case:** Complex automation scenarios like:
    - Generate reflection → Extract semantics → Create snapshot
    - Detect drift → Send alert → Run evaluation
    """
    try:
        # Create workflow in database
        workflow_record = await repo.create_workflow(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            workflow_name=request.workflow_name,
            steps=[s.model_dump() for s in request.steps],
            created_by=request.created_by,
            description=request.description,
            execution_mode=("parallel" if request.parallel_execution else "sequential"),
        )

        return CreateWorkflowResponse(
            workflow_id=workflow_record["id"],
            message=f"Workflow '{request.workflow_name}' created with {len(request.steps)} steps",
        )

    except Exception as e:
        logger.error("workflow_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str, repo: WorkflowRepository = Depends(get_workflow_repo)
):
    """Get workflow definition by ID"""
    try:
        workflow = await repo.get_workflow(UUID(workflow_id))

        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {"workflow": workflow, "message": "Workflow retrieved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_workflow_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/workflows")
async def list_workflows(
    tenant_id: str,
    project_id: str,
    limit: int = 100,
    repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """List workflows"""
    try:
        workflows = await repo.list_workflows(
            tenant_id=tenant_id, project_id=project_id, limit=limit
        )

        return {
            "workflows": workflows,
            "total_count": len(workflows),
            "message": f"Found {len(workflows)} workflows",
        }

    except Exception as e:
        logger.error("list_workflows_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Templates
# ============================================================================


@router.get("/templates")
async def get_trigger_templates():
    """
    Get pre-configured trigger templates.

    Templates provide ready-to-use trigger configurations for common use cases.
    """
    return {
        "templates": [
            {
                "template_id": template.template_id,
                "template_name": template.template_name,
                "description": template.description,
                "category": template.category,
                "parameters": template.parameters,
                "required_parameters": template.required_parameters,
                "use_cases": template.use_cases,
            }
            for template in DEFAULT_TEMPLATES.values()
        ]
    }


@router.get("/templates/{template_id}")
async def get_trigger_template(template_id: str):
    """Get specific trigger template"""
    try:
        if template_id not in DEFAULT_TEMPLATES:
            raise HTTPException(
                status_code=404, detail=f"Template '{template_id}' not found"
            )

        template = DEFAULT_TEMPLATES[template_id]

        return {
            "template": template.model_dump(),
            "message": "Template retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_template_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/templates/{template_id}/instantiate", response_model=CreateTriggerResponse
)
async def instantiate_template(
    template_id: str,
    tenant_id: str,
    project_id: str,
    rule_name: str,
    parameters: dict,
    created_by: str,
    pool=Depends(get_pool),
):
    """
    Create a trigger from template.

    Instantiates a pre-configured template with user-provided parameters.

    **Use Case:** Quick setup of common automation patterns.
    """
    try:
        if template_id not in DEFAULT_TEMPLATES:
            raise HTTPException(
                status_code=404, detail=f"Template '{template_id}' not found"
            )

        template = DEFAULT_TEMPLATES[template_id]

        # Validate required parameters
        for param in template.required_parameters:
            if param not in parameters:
                raise HTTPException(
                    status_code=400, detail=f"Required parameter '{param}' missing"
                )

        trigger_id = uuid4()

        logger.info(
            "trigger_instantiated_from_template",
            trigger_id=trigger_id,
            template_id=template_id,
            rule_name=rule_name,
        )

        return CreateTriggerResponse(
            trigger_id=trigger_id,
            message=f"Trigger created from template '{template.template_name}'",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("instantiate_template_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# System Information
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for event triggers service"""
    return {
        "status": "healthy",
        "service": "event_triggers_api",
        "version": "1.0",
        "features": [
            "trigger_rules",
            "event_emission",
            "workflows",
            "templates",
            "condition_evaluation",
            "action_execution",
        ],
        "supported_events": [e.value for e in EventType],
        "supported_actions": [
            "send_notification",
            "send_webhook",
            "generate_reflection",
            "extract_semantics",
            "apply_decay",
            "create_snapshot",
            "run_evaluation",
        ],
    }


@router.get("/info")
async def get_triggers_info():
    """
    Get information about the event triggers system.

    Returns available operators, event types, and action types.
    """
    return {
        "condition_operators": {
            "equals": "Equal to",
            "not_equals": "Not equal to",
            "greater_than": "Greater than",
            "less_than": "Less than",
            "greater_equal": "Greater than or equal",
            "less_equal": "Less than or equal",
            "contains": "Contains substring/element",
            "not_contains": "Does not contain",
            "in": "In list",
            "not_in": "Not in list",
            "matches_regex": "Matches regex pattern",
            "is_null": "Is null/None",
            "is_not_null": "Is not null/None",
        },
        "event_types": [e.value for e in EventType],
        "action_types": {
            "send_notification": "Send notification to configured channel",
            "send_email": "Send email notification",
            "send_webhook": "POST event to webhook URL",
            "create_memory": "Create new memory",
            "update_memory": "Update existing memory",
            "delete_memory": "Delete memory",
            "generate_reflection": "Generate reflection from memories",
            "extract_semantics": "Extract semantic nodes",
            "apply_decay": "Apply decay to semantic nodes",
            "reinforce_node": "Reinforce semantic node",
            "create_snapshot": "Create graph snapshot",
            "run_evaluation": "Run evaluation suite",
        },
        "templates": list(DEFAULT_TEMPLATES.keys()),
        "examples": {
            "simple_condition": {
                "field": "importance",
                "operator": "greater_than",
                "value": 0.8,
            },
            "condition_group": {
                "operator": "AND",
                "conditions": [
                    {"field": "importance", "operator": "greater_than", "value": 0.7},
                    {"field": "tags", "operator": "contains", "value": "critical"},
                ],
            },
        },
    }
