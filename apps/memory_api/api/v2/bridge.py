import json
from typing import Any, Dict
from uuid import uuid4

import structlog
from fastapi import APIRouter, HTTPException, Request

from apps.memory_api.models.event_models import (
    BridgeInteractionRequest,
    EmitEventResponse,
    Event,
    EventType,
)
from apps.memory_api.services.rae_core_service import RAECoreService

router = APIRouter(prefix="/v2/bridge", tags=["Bridge"])
logger = structlog.get_logger(__name__)


@router.post("/interact", response_model=EmitEventResponse)
async def agent_interaction(
    request_data: BridgeInteractionRequest,
    request: Request,
):
    """
    Handles Agent-to-Agent (A2A) interactions through the RAE Bridge.
    All interactions are recorded as events and captured in memory.

    Features:
    - **Implicit Capture**: Automatic storage in Episodic Layer.
    - **Intelligent Context**: Auto-detection of projects (Dreamsoft, ScreenWatcher).
    - **Human Labeling**: Clean, readable operation names generated on the fly.
    """
    service: RAECoreService = request.app.state.rae_core_service
    payload = request_data.payload

    # SYSTEM 95.1: Intelligent Context Resolution
    tenant_id = (
        request.headers.get("X-Tenant-Id") or "00000000-0000-0000-0000-000000000000"
    )
    project = request.headers.get("X-Project-Id")

    # Auto-detect project from payload keywords if not explicitly provided
    if not project:
        payload_str = str(payload).lower()
        if any(
            kw in payload_str for kw in ["speed", "area", "machine", "job id", "ink"]
        ):
            project = "screenwatcher"
        elif any(
            kw in payload_str
            for kw in ["dreamsoft", "modernization", "nextjs", "angular"]
        ):
            project = "dreamsoft_modernization"
        else:
            project = "default"

    # SYSTEM 95.2: Human-Centric Labeling
    # Check payload for intelligence FIRST
    payload_data = payload.get(
        "payload", payload
    )  # Support both nested and flat payload
    action_name = payload_data.get("action", "interaction").replace("_", " ").title()

    # Check agents
    s_agent = request_data.source_agent
    t_agent = request_data.target_agent

    human_label = request_data.human_label or f"{action_name} ({s_agent} -> {t_agent})"

    event_id = uuid4()
    correlation_id = request_data.correlation_id or event_id

    # 1. Create the Event
    Event(
        event_id=event_id,
        event_type=EventType.AGENT_INTERACTION,
        tenant_id=tenant_id,
        project=project,
        source_service=s_agent,
        payload={
            "target_agent": t_agent,
            "interaction_data": payload,
            "strategy": request_data.strategy,
        },
        session_id=request_data.session_id,
        correlation_id=correlation_id,
        metadata={"a2a": True, "protocol": "mcp-bridge-v1"},
    )

    # 2. Implicit Capture: Store in Memory (Episodic)
    try:
        content_summary = f"A2A: {s_agent} -> {t_agent}: {str(payload)[:500]}"

        await service.engine.store_memory(
            tenant_id=tenant_id,
            agent_id=s_agent,
            content=content_summary,
            layer="episodic",
            project=project,
            session_id=request_data.session_id,
            human_label=human_label,
            metadata={
                "event_id": str(event_id),
                "correlation_id": str(correlation_id),
                "target_agent": t_agent,
                "full_payload": payload,
                "human_label": human_label,
                "strategy": request_data.strategy,
                "autonomy_state": request_data.autonomy_state,
                "autonomy_journal": request_data.autonomy_journal,
            },
        )
    except Exception as e:
        logger.error("bridge_memory_capture_failed", error=str(e))
        # We continue even if memory capture fails, but log it

    # 3. Active A2A Bridge Routing
    target_response = None
    routing_msg = (
        f"A2A Interaction captured in memory (no active routing mapped for '{t_agent}')"
    )

    AGENT_ROUTING_MAP = {
        "rae-quality": "http://rae-quality:8010",
        "rae-hive": "http://rae-hive:8013",
        "rae-lab": "http://rae-lab:8011",
        "rae-phoenix": "http://rae-phoenix:8012",
        "rae-suite": "http://rae-suite:8009",
    }

    if t_agent in AGENT_ROUTING_MAP:
        base_url = AGENT_ROUTING_MAP[t_agent]
        route_url = f"{base_url}/v2/bridge/interact"
        forward_payload = payload

        intent = payload.get("intent")
        if t_agent == "rae-phoenix":
            if intent in ["REFACTOR_CODE", "CODE_REFACTORING_REQUEST"]:
                route_url = f"{base_url}/v2/phoenix/repair"
                forward_payload = {
                    "project": payload.get("project") or project,
                    "code": payload.get("faulty_code") or payload.get("code") or "",
                    "reason": payload.get("tribunal_reasoning")
                    or payload.get("reason")
                    or "Quality standards not met",
                    "file_path": payload.get("file_path", "unknown.py"),
                }
            elif intent in ["CREATE_CODE", "CREATE_TASK"]:
                route_url = f"{base_url}/v2/phoenix/create"
                forward_payload = {
                    "project": payload.get("project") or project,
                    "objective": payload.get("objective") or "",
                    "target_path": payload.get("target_path") or "",
                    "architecture_style": payload.get(
                        "architecture_style", "Clean Architecture"
                    ),
                }
        elif t_agent == "rae-quality":
            if intent in ["AUDIT_CODE", "RUN_AUDIT"]:
                route_url = f"{base_url}/v2/quality/audit"
                forward_payload = {
                    "code": payload.get("code") or payload.get("faulty_code") or "",
                    "project": payload.get("project") or project,
                    "importance": payload.get("importance", "medium"),
                }

        logger.info("routing_a2a_interaction", target_agent=t_agent, url=route_url)
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                headers = {"X-Tenant-Id": tenant_id}
                if project:
                    headers["X-Project-Id"] = project
                if request_data.autonomy_state:
                    # Sanitize to prevent HTTP header injection
                    sanitized_state = request_data.autonomy_state.replace(
                        "\r", ""
                    ).replace("\n", "")[:50]
                    headers["X-Autonomy-State"] = sanitized_state
                if request_data.autonomy_journal:
                    # Sanitize list elements to prevent injection and DoS
                    sanitized_journal = []
                    for item in request_data.autonomy_journal[:100]:
                        if isinstance(item, str):
                            sanitized_journal.append(
                                item.replace("\r", "").replace("\n", "")[:50]
                            )
                    try:
                        headers["X-Autonomy-Journal"] = json.dumps(sanitized_journal)
                    except (TypeError, ValueError) as json_err:
                        logger.error(
                            "bridge_journal_serialization_failed", error=str(json_err)
                        )

                resp = await client.post(
                    route_url, json=forward_payload, headers=headers, timeout=60.0
                )
                if resp.status_code in [200, 201]:
                    target_response = resp.json()
                    routing_msg = f"A2A Interaction routed to {t_agent} successfully"
                else:
                    routing_msg = f"A2A Routing to {t_agent} failed with status {resp.status_code}"
                    logger.error(
                        "routing_a2a_failed_status",
                        target=t_agent,
                        status=resp.status_code,
                        body=resp.text,
                    )
        except Exception as e:
            routing_msg = f"A2A Routing to {t_agent} raised exception: {str(e)}"
            logger.error("routing_a2a_exception", target=t_agent, error=str(e))

    return EmitEventResponse(
        event_id=event_id,
        triggers_matched=0,
        actions_queued=0,
        message=routing_msg,
        target_response=target_response,
        autonomy_state=request_data.autonomy_state,
        autonomy_journal=request_data.autonomy_journal,
    )


@router.post("/audit")
async def semantic_audit(
    payload: Dict[str, Any], request: Request, source_agent: str = "open-claw"
):
    """
    Phase 3 Hard Frames: Semantic Firewall.
    Analyzes the intent of the agent before allowing execution.
    """
    service: RAECoreService = request.app.state.rae_core_service
    prompt = payload.get("prompt", "")
    payload.get("context", "no_context")

    # 1. Intent Analysis via Reflective Layer
    is_safe = True
    reason = "Intent matches project scope"

    forbidden_keywords = ["private_key", "password", "hasło", "klucz", ".env", "secret"]
    if any(kw in prompt.lower() for kw in forbidden_keywords):
        is_safe = False
        reason = "RESTRICTED data leak or credential access attempt detected"

    # 2. Log the Audit Attempt
    await service.engine.store_memory(
        tenant_id="00000000-0000-0000-0000-000000000000",
        agent_id=source_agent,
        content=f"PHASE 3 AUDIT: {source_agent} prompt audit -> {is_safe}. Reason: {reason}",
        layer="reflective",
        tags=["phase3_audit", "firewall"],
        metadata={"prompt_snippet": prompt[:100], "safe": is_safe, "reason": reason},
    )

    if not is_safe:
        raise HTTPException(
            status_code=403, detail=f"Semantic Firewall Block: {reason}"
        )

    return {"status": "approved", "audit_id": str(uuid4()), "reason": reason}
