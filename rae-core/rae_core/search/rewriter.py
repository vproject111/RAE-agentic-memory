"""Architectural Query Rewriter for targeted 2-pass retrieval in RAE."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rae_core.search.sufficiency_gate import SufficiencyAssessment


class RewritePlan(BaseModel):
    """Execution plan for the second pass of adaptive retrieval."""

    model_config = ConfigDict(extra="forbid")

    original_query: str = Field(description="Original search query string")
    missing_aspects: list[str] = Field(
        default_factory=list, description="Specific terms/aspects absent in Pass 1"
    )
    refined_queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="Targeted query variations for Pass 2",
    )
    strategy_weight_adjustments: dict[str, float] = Field(
        default_factory=dict,
        description="Multipliers for strategy weights in Pass 2 (e.g. {'fulltext': 1.5, 'vector': 0.8})",
    )
    focus_filters: dict[str, Any] | None = Field(
        default=None, description="Optional metadata filters for targeted search"
    )


class QueryRewriter:
    """
    Deterministic Query Rewriter that formulates targeted second-pass queries
    and strategy weight adjustments without relying on slow or non-deterministic LLM calls.
    """

    def __init__(self, default_boost: float = 1.4):
        self.default_boost = default_boost

    def create_rewrite_plan(
        self,
        query: str,
        assessment: SufficiencyAssessment | None = None,
    ) -> RewritePlan:
        """
        Construct a targeted RewritePlan based on sufficiency assessment gaps.
        """
        missing_aspects = assessment.missing_aspects if assessment else []
        refined_queries: list[str] = []
        weight_adjustments: dict[str, float] = {}

        # 1. Analyze missing aspects to determine strategy bias
        has_code_symbol = any(
            any(char in term for char in ("_", ".", "(", ")")) or term[0].isupper()
            for term in missing_aspects
            if term
        )

        if has_code_symbol or any("identifier" in m.lower() for m in missing_aspects):
            # Missing exact symbol -> boost FullText and Anchor search
            weight_adjustments = {
                "fulltext": self.default_boost,
                "anchor": self.default_boost,
                "vector": 0.7,
            }
        else:
            # Missing semantic context -> boost Vector and Graph
            weight_adjustments = {
                "vector": self.default_boost,
                "graph": self.default_boost,
                "fulltext": 0.8,
            }

        # 2. Formulate refined queries
        if missing_aspects:
            # Focused query on the primary missing term
            primary_missing = " ".join(missing_aspects[:2])
            refined_queries.append(f"{query} {primary_missing}")
            refined_queries.append(primary_missing)
        else:
            # General precision query: clean punctuation
            refined_queries.append(query.strip())

        return RewritePlan(
            original_query=query,
            missing_aspects=missing_aspects,
            refined_queries=refined_queries[:3],
            strategy_weight_adjustments=weight_adjustments,
        )
