from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.config import settings
from apps.memory_api.models import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    CostInfo,
    QueryMemoryResponse,
)
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import get_and_verify_tenant_id

# All agent endpoints require authentication
router = APIRouter(
    prefix="/agent",
    tags=["agent", "external"],
    dependencies=[Depends(auth.verify_token)],
)

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute(
    req: AgentExecuteRequest,
    request: Request,
    verified_tenant_id: UUID = Depends(get_and_verify_tenant_id),
):
    """
    RAE-First Agent Pipeline:
    1) Input registration (Sensory Memory)
    2) Automated context building (Hybrid Search + Rerank)
    3) Agent execution (LLM) within RAE boundaries
    4) Outcome evaluation & automatic storage (Episodic/Semantic)

    **Security:** Requires authentication and tenant access.
    """
    tenant_id: UUID = verified_tenant_id
    rae_service = request.app.state.rae_core_service

    with tracer.start_as_current_span("rae.api.agent.execute") as span:
        span.set_attribute("rae.tenant_id", str(tenant_id))
        span.set_attribute("rae.project_id", req.project)
        span.set_attribute("rae.agent.prompt_length", len(req.prompt))

        try:
            # EXECUTE VIA RAE-FIRST RUNTIME
            # This one call handles everything: context, execution, and memory hooks.
            action = await rae_service.execute_action(
                tenant_id=tenant_id,
                agent_id=req.project,
                prompt=req.prompt,
                session_id=req.session_id,
                metadata={
                    "requested_model": settings.RAE_LLM_MODEL_DEFAULT,
                    "source": "api_v1_agent_execute",
                },
            )

            # Metadata for response
            cost = CostInfo(
                input_tokens=0,  # Runtime doesn't return usage yet, but will track internally
                output_tokens=0,
                total_estimate=0.0,
            )

            # Return response matches the old contract but data was handled by RAERuntime
            return AgentExecuteResponse(
                answer=str(action.content),
                used_memories=QueryMemoryResponse(
                    results=[]
                ),  # Context usage is now internal to RAE
                cost=cost,
            )

        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            span.set_attribute("rae.error.message", str(e))
            logger.error("agent_execute_failed", error=str(e))
            raise HTTPException(
                status_code=500, detail=f"RAE-First execution failed: {e}"
            )
