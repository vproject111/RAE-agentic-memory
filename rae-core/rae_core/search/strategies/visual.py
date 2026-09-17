"""Visual search strategy for multimodal artifacts (screenshots, diagrams, PDF pages)."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from rae_core.models.multimodal import MultimodalArtifact
from rae_core.search.strategies import SearchStrategy


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm1 * norm2)))


class VisualSearchStrategy(SearchStrategy):
    """
    Search strategy specialized for multimodal artifacts.
    Supports OCR keyword matching, visual embedding similarity (CLIP/SigLIP),
    and hybrid text-to-visual ranking.
    """

    def __init__(
        self,
        default_weight: float = 0.4,
        artifacts: dict[UUID, MultimodalArtifact] | None = None,
    ):
        self.default_weight = default_weight
        self._artifacts: dict[UUID, MultimodalArtifact] = (
            dict(artifacts) if artifacts else {}
        )

    def register_artifact(self, memory_id: UUID, artifact: MultimodalArtifact) -> None:
        """Register a multimodal artifact indexed by its corresponding memory UUID."""
        self._artifacts[memory_id] = artifact

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        project: str | None = None,
        **kwargs: Any,
    ) -> list[tuple[UUID, float, float]]:
        """
        Search multimodal artifacts using text query and optional visual embeddings.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        query_visual_emb: list[float] | None = kwargs.get("visual_embedding")
        query_text_emb: list[float] | None = kwargs.get("text_embedding")

        results: list[tuple[UUID, float, float]] = []

        for mem_id, artifact in self._artifacts.items():
            # Check project filter
            if project and artifact.envelope and artifact.envelope.project != project:
                continue

            score = 0.0

            # 1. OCR Keyword Match
            ocr_text = (artifact.ocr_extracted_text or "").lower()
            if ocr_text and query_words:
                matching_words = sum(1 for w in query_words if w in ocr_text)
                ocr_score = matching_words / len(query_words)
                score = max(score, ocr_score * 0.85)

            # 2. Text Embedding Similarity
            if query_text_emb and artifact.text_embedding:
                emb_score = _cosine_similarity(query_text_emb, artifact.text_embedding)
                score = max(score, emb_score)

            # 3. Visual Embedding Similarity
            if query_visual_emb and artifact.visual_embedding:
                vis_score = _cosine_similarity(
                    query_visual_emb, artifact.visual_embedding
                )
                score = max(score, vis_score)

            if score > 0.05:
                results.append((mem_id, min(1.0, score), 0.0))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_strategy_name(self) -> str:
        return "visual"

    def get_strategy_weight(self) -> float:
        return self.default_weight
