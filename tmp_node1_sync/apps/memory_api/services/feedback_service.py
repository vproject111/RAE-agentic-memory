"""
Feedback Service (Iteration 3)

Implements the "Feedback Loop" (learning-to-remember) mechanism.
"""

from typing import TYPE_CHECKING, Optional

import structlog

from apps.memory_api.config import settings

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class FeedbackService:
    """
    Service for processing user/system feedback on memory retrieval quality.
    """

    def __init__(self, rae_service: "RAECoreService"):
        self.rae_service = rae_service

    async def process_feedback(
        self,
        tenant_id: str,
        memory_id: str,
        feedback_type: str,
        comment: Optional[str] = None,
        score: Optional[float] = None,
        query_text: Optional[str] = None,
        weights_snapshot: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Process feedback for a specific memory and persist to database.
        """
        # 1. Determine numeric score
        if score is None:
            if feedback_type == "positive":
                score = 1.0
            elif feedback_type == "negative":
                score = -1.0
            else:
                score = 0.0

        # 2. Adjust importance (Legacy mechanism)
        delta = 0.0
        if feedback_type == "positive":
            delta = settings.FEEDBACK_POSITIVE_DELTA
        elif feedback_type == "negative":
            delta = -settings.FEEDBACK_NEGATIVE_DELTA
        
        # Always try to adjust importance if feedback loop is enabled or for Phase 4
        await self.rae_service.adjust_importance(
            memory_id=memory_id, tenant_id=tenant_id, delta=delta
        )

        # 3. Persist to memory_feedback table (Phase 4) - MANDATORY
        try:
            import json
            from uuid import UUID, uuid4
            
            sql = """
                INSERT INTO memory_feedback (
                    id, tenant_id, query_text, memory_id, score, 
                    weights_snapshot, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """
            await self.rae_service.db.execute(
                sql,
                uuid4(),
                tenant_id,
                query_text or "unknown",
                UUID(memory_id),
                score,
                json.dumps(weights_snapshot or {}),
                json.dumps(metadata or {})
            )

            
            logger.info(
                "feedback_persisted",
                memory_id=memory_id,
                tenant_id=tenant_id,
                score=score
            )
            return True
        except Exception as e:
            logger.error("feedback_persistence_failed", error=str(e))
            return False


