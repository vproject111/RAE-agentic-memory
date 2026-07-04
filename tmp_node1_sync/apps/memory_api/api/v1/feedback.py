from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.models.feedback import FeedbackRequest
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.feedback_service import FeedbackService
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=dict)
async def submit_feedback(
    feedback: FeedbackRequest,
    request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Submit feedback for a retrieved memory.

    Used for the 'Feedback Loop' mechanism to adjust memory importance.
    """
    # Initialize service
    service = FeedbackService(rae_service=rae_service)

    success = await service.process_feedback(
        tenant_id=str(tenant_id),
        memory_id=feedback.memory_id,
        feedback_type=feedback.feedback_type,
        comment=feedback.comment,
        score=feedback.score,
        query_text=feedback.query_text,
        weights_snapshot=feedback.weights_snapshot,
        metadata=feedback.metadata,
    )

    if not success:
        # Could be disabled feature or memory not found
        # For API UX, we return 200 OK but with status
        return {"status": "ignored_or_failed", "message": "Feedback not applied"}

    return {"status": "success", "message": "Feedback recorded"}
