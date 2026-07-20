from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.interfaces.adapter import (
    IKnowledgeAdapter,
    RetrievalContext,
    RetrievedKnowledge,
)
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType

logger = logging.getLogger(__name__)


class RAEMemoryQueryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layer_filter: str | None = None


class RAEAgenticMemoryAdapter(IKnowledgeAdapter[RAEMemoryQueryParams]):
    adapter_id = "rae-agentic-memory"
    source_type = KnowledgeSourceType.DATABASE

    def __init__(self, rae_service: RAECoreService) -> None:
        self.rae_service = rae_service

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[RAEMemoryQueryParams],
    ) -> list[RetrievedKnowledge]:
        layer_filter = context.params.layer_filter if context.params else None

        # Call the real RAECoreService.search_memories
        memories = await self.rae_service.search_memories(
            query=query,
            tenant_id=str(context.tenant_id),
            limit=limit,
            layer=layer_filter,
        )

        results: list[RetrievedKnowledge] = []
        for memory in memories:
            m_id = memory.get("id")
            content = memory.get("content")
            content_hash = memory.get("content_hash")
            if not content or not content_hash or not m_id:
                continue

            # Ensure we respect max_response_bytes constraint
            if len(content.encode("utf-8")) > context.max_response_bytes:
                continue

            info_class_val = memory.get("info_class", "internal")
            # If info_class is string (e.g. from JSON serialization), normalize it
            if hasattr(info_class_val, "value"):
                info_class_str = info_class_val.value.upper()
            else:
                info_class_str = str(info_class_val).upper()

            authority_map = {
                "RESTRICTED": AuthorityLevel.UNTRUSTED,
                "CONFIDENTIAL": AuthorityLevel.APPROVED,
                "INTERNAL": AuthorityLevel.OBSERVED,
                "PUBLIC": AuthorityLevel.CANONICAL,
            }
            authority = authority_map.get(info_class_str, AuthorityLevel.UNTRUSTED)

            # Extract score, falling back to math_score or search_score or a default
            score_val = memory.get("math_score") or memory.get("search_score") or memory.get("score") or 0.5

            observed_at_val = memory.get("created_at")
            if isinstance(observed_at_val, str):
                try:
                    observed_at = datetime.fromisoformat(observed_at_val)
                except Exception:
                    observed_at = datetime.now(timezone.utc)
            elif isinstance(observed_at_val, datetime):
                observed_at = observed_at_val
            else:
                observed_at = datetime.now(timezone.utc)

            results.append(
                RetrievedKnowledge(
                    evidence_id=f"rae-memory:{m_id}",
                    content=content,
                    source_ref=f"rae-db://memories/{m_id}",
                    source_type=KnowledgeSourceType.DATABASE,
                    authority_level=authority,
                    score=max(0.0, min(1.0, float(score_val))),
                    observed_at=observed_at,
                    checksum=content_hash,
                    knowledge_id=memory.get("knowledge_id"),
                    metadata=memory.get("metadata") or {},
                )
            )

        return results
