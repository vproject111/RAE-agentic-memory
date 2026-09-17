"""Adaptive Search Engine with bounded 2-pass retrieval loop."""

from __future__ import annotations

import os
from typing import Any
from uuid import UUID

import structlog

from rae_core.models.evidence_package import EvidenceItem, EvidencePackage
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.rewriter import QueryRewriter, RewritePlan
from rae_core.search.sufficiency_gate import (
    EvidenceSufficiencyGate,
    GateDecision,
)

logger = structlog.get_logger(__name__)


class AdaptiveSearchEngine(HybridSearchEngine):
    """
    Adaptive Search Engine executing a bounded 2-pass retrieval loop.
    Pass 1: Initial Hybrid Search + Evidence Sufficiency evaluation.
    Pass 2: If Pass 1 is INSUFFICIENT and 2-pass is enabled, rewrite query,
            adjust strategy weights, retrieve complementary evidence,
            fuse results, and re-assess sufficiency.
    Hard limit: max_passes = 2 (strictly enforced, no infinite loops).
    """

    def __init__(
        self,
        *args: Any,
        rewriter: QueryRewriter | None = None,
        sufficiency_gate: EvidenceSufficiencyGate | None = None,
        max_passes: int = 2,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.rewriter = rewriter or QueryRewriter()
        self.sufficiency_gate = sufficiency_gate or EvidenceSufficiencyGate()
        self.max_passes = min(max_passes, 2)  # Enforce hard upper bound of 2

    @staticmethod
    def is_2pass_enabled() -> bool:
        env_val = os.getenv("RAE_ADAPTIVE_2PASS_ENABLED", "false").lower()
        return env_val in ("1", "true", "yes", "on")

    async def search_adaptive_evidence(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        enable_reranking: bool = False,
        math_controller: Any = None,
        force_2pass: bool = False,
        **kwargs: Any,
    ) -> EvidencePackage:
        """
        Execute adaptive evidence search with bounded 2-pass loop.
        """
        # Pass 1: Standard Evidence Search
        package = await self.search_evidence(
            query=query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            filters=filters,
            limit=limit,
            strategies=strategies,
            strategy_weights=strategy_weights,
            enable_reranking=enable_reranking,
            math_controller=math_controller,
            **kwargs,
        )

        assessment = self.sufficiency_gate.evaluate(package)
        package.metadata["sufficiency_assessment"] = assessment.model_dump()
        package.confidence_score = assessment.composite_score
        package.missing_aspects = assessment.missing_aspects
        package.metadata["pass_count"] = 1

        should_run_pass_2 = (self.is_2pass_enabled() or force_2pass) and (
            assessment.decision != GateDecision.SUFFICIENT
        )

        if not should_run_pass_2 or self.max_passes < 2:
            return package

        # Pass 2: Targeted Query Rewrite & Retrieval
        logger.info(
            "adaptive_retrieval_pass_2_initiated",
            query=query,
            decision=assessment.decision,
            score=assessment.composite_score,
            missing=assessment.missing_aspects,
        )

        rewrite_plan: RewritePlan = self.rewriter.create_rewrite_plan(
            query=query,
            assessment=assessment,
        )
        package.metadata["rewrite_plan"] = rewrite_plan.model_dump()

        # Compute adjusted strategy weights
        pass2_weights: dict[str, float] = dict(strategy_weights or {})
        for strat_name, multiplier in rewrite_plan.strategy_weight_adjustments.items():
            base_w = pass2_weights.get(strat_name, 1.0)
            pass2_weights[strat_name] = base_w * multiplier

        # Choose refined query
        pass2_query = (
            rewrite_plan.refined_queries[0] if rewrite_plan.refined_queries else query
        )

        pass2_filters = filters
        if rewrite_plan.focus_filters:
            pass2_filters = dict(filters or {})
            pass2_filters.update(rewrite_plan.focus_filters)

        pass2_package = await self.search_evidence(
            query=pass2_query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            filters=pass2_filters,
            limit=limit,
            strategies=strategies,
            strategy_weights=pass2_weights,
            enable_reranking=enable_reranking,
            math_controller=math_controller,
            **kwargs,
        )

        # FUSE Pass 1 and Pass 2 items
        fused_items: list[EvidenceItem] = []
        seen_memory_ids: dict[UUID, EvidenceItem] = {}

        # Items from pass 1
        for item in package.items:
            seen_memory_ids[item.memory_id] = item
            fused_items.append(item)

        # Merge items from pass 2
        for item in pass2_package.items:
            if item.memory_id in seen_memory_ids:
                existing = seen_memory_ids[item.memory_id]
                # Boost relevance if retrieved in both passes
                existing.relevance_score = min(
                    1.0, max(existing.relevance_score, item.relevance_score) * 1.1
                )
            else:
                seen_memory_ids[item.memory_id] = item
                fused_items.append(item)

        # Sort by relevance
        fused_items.sort(key=lambda x: x.relevance_score, reverse=True)
        top_fused_items = fused_items[:limit]

        # Formulate final EvidencePackage
        active_strategies = list(
            set(package.strategies_used + pass2_package.strategies_used)
        )
        final_package = EvidencePackage(
            package_id=package.package_id,
            query=query,
            tenant_id=tenant_id,
            items=top_fused_items,
            strategies_used=active_strategies,
            confidence_score=package.confidence_score,
            conflicts=package.conflicts + pass2_package.conflicts,
            missing_aspects=package.missing_aspects,
            metadata={
                **package.metadata,
                "pass_count": 2,
                "pass2_query": pass2_query,
                "pass2_item_count": len(pass2_package.items),
            },
        )

        # Re-evaluate final sufficiency
        final_assessment = self.sufficiency_gate.evaluate(final_package)
        final_package.metadata["final_sufficiency_assessment"] = (
            final_assessment.model_dump()
        )
        final_package.confidence_score = final_assessment.composite_score
        final_package.missing_aspects = final_assessment.missing_aspects

        return final_package
