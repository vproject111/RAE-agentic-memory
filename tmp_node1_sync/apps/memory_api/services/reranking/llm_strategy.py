"""
LLM-based Generative Reranking Strategy.
Target: FULL_GPU Profile.
"""

import json
from typing import Any, Dict, List

import structlog

from apps.memory_api.services.reranking.base import RerankingStrategy

logger = structlog.get_logger(__name__)


class LlmRerankerStrategy(RerankingStrategy):
    """
    Reranker that uses a Listwise approach via LLM prompting.
    """

    def __init__(self, llm_service: Any):
        self.llm_service = llm_service

    async def rerank(
        self, candidates: List[Dict[str, Any]], query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Ask LLM to rank the candidates.
        """
        if not candidates:
            return []

        # Optimization: Don't rerank if list is small
        if len(candidates) <= 3:
            return candidates

        try:
            # 1. Prepare Prompt
            prompt = self._construct_prompt(candidates, query)

            # 2. Call LLM (expecting JSON)
            # We assume llm_service has a generate_json or similar method,
            # or we parse raw text.
            response = await self.llm_service.generate(
                prompt=prompt, response_format={"type": "json_object"}, temperature=0.0
            )

            # 3. Parse and Reorder
            ranked_indices = self._parse_ranking(response, len(candidates))

            # Reconstruct list
            reranked_list = []
            for idx in ranked_indices:
                if 0 <= idx < len(candidates):
                    reranked_list.append(candidates[idx])

            # Append any missing items (failures in LLM ranking) at the end
            seen_indices = set(ranked_indices)
            for i, cand in enumerate(candidates):
                if i not in seen_indices:
                    reranked_list.append(cand)

            return reranked_list[:limit]

        except Exception as e:
            logger.error("llm_rerank_failed", error=str(e))
            # Fallback to original order
            return candidates[:limit]

    def _construct_prompt(self, candidates: List[Dict[str, Any]], query: str) -> str:
        items_str = ""
        for i, cand in enumerate(candidates):
            content_snippet = cand.get("content", "")[:200].replace("\n", " ")
            items_str += f"[{i}] {content_snippet}\n"

        return f"""
You are a relevance ranking expert.
Query: "{query}"

Rank the following passages based on their relevance to the query.
Passages:
{items_str}

Return a JSON object with a single key "ranked_indices" containing a list of the indices (integers) in order of decreasing relevance.
Example: {{ "ranked_indices": [2, 0, 1] }}
Only return the JSON.
"""

    def _parse_ranking(self, response: str, max_idx: int) -> List[int]:
        try:
            # Clean up potential markdown code blocks
            clean_resp = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_resp)
            indices = data.get("ranked_indices", [])
            # Validate indices
            valid_indices = [
                i for i in indices if isinstance(i, int) and 0 <= i < max_idx
            ]
            return valid_indices
        except json.JSONDecodeError:
            logger.warning("llm_rerank_json_parse_error", response=response)
            return []
