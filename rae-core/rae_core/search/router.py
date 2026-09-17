"""Strategy router mapping classified queries to optimal retrieval profiles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from rae_core.evaluation.golden_queries import QueryCategory
from rae_core.search.classifier import ClassificationResult, QueryClassifier

ROUTING_PROFILES: dict[QueryCategory, dict[str, float]] = {
    QueryCategory.EXACT_IDENTIFIER: {
        "fulltext": 0.80,
        "anchor": 0.80,
        "vector": 0.15,
        "graph": 0.0,
    },
    QueryCategory.CODE_SYMBOL: {
        "fulltext": 0.60,
        "anchor": 0.50,
        "vector": 0.30,
        "graph": 0.15,
    },
    QueryCategory.SEMANTIC_CODE: {
        "vector": 0.55,
        "fulltext": 0.25,
        "graph": 0.20,
        "anchor": 0.10,
    },
    QueryCategory.HISTORICAL_DECISION: {
        "vector": 0.45,
        "fulltext": 0.30,
        "graph": 0.25,
        "anchor": 0.10,
    },
    QueryCategory.GRAPH_RELATION: {
        "graph": 0.60,
        "vector": 0.20,
        "fulltext": 0.20,
        "anchor": 0.10,
    },
    QueryCategory.CROSS_FILE: {
        "graph": 0.45,
        "vector": 0.40,
        "fulltext": 0.20,
    },
    QueryCategory.CROSS_REPOSITORY: {
        "vector": 0.50,
        "fulltext": 0.30,
        "graph": 0.20,
    },
    QueryCategory.TEMPORAL: {
        "fulltext": 0.40,
        "vector": 0.40,
        "graph": 0.20,
    },
    QueryCategory.MULTI_SOURCE: {
        "vector": 0.40,
        "fulltext": 0.30,
        "graph": 0.30,
    },
}


class RoutingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    category: QueryCategory
    confidence: float
    matched_rule: str
    strategy_weights: dict[str, float] = Field(
        description="Weights for strategies matching the routing profile"
    )
    active_strategies: list[str] = Field(
        description="List of active strategies with non-zero allocation"
    )
    pruned_strategies: list[str] = Field(
        default_factory=list,
        description="Strategies omitted to avoid redundant latency",
    )


class StrategyRouter:
    """
    Intelligent Strategy Router for HybridSearchEngine.
    Selects active strategies and relative weights based on deterministic query classification.
    """

    def __init__(
        self,
        classifier: QueryClassifier | None = None,
        prune_threshold: float = 0.05,
    ):
        self.classifier = classifier or QueryClassifier()
        self.prune_threshold = prune_threshold

    def route(
        self,
        query: str,
        available_strategies: list[str] | None = None,
    ) -> RoutingPlan:
        """
        Determine optimal active strategies and weights for a search query.
        """
        classification: ClassificationResult = self.classifier.classify(query)
        base_profile = ROUTING_PROFILES.get(
            classification.category,
            ROUTING_PROFILES[QueryCategory.SEMANTIC_CODE],
        )

        all_strats = (
            available_strategies
            if available_strategies is not None
            else list(base_profile.keys())
        )

        active: list[str] = []
        pruned: list[str] = []
        weights: dict[str, float] = {}

        for strat in all_strats:
            weight = base_profile.get(strat, 0.2)
            if weight > self.prune_threshold:
                active.append(strat)
                weights[strat] = weight
            else:
                pruned.append(strat)

        # Fallback safeguard: ensure at least one strategy is active
        if not active and all_strats:
            active.append(all_strats[0])
            weights[all_strats[0]] = 1.0

        return RoutingPlan(
            query=query,
            category=classification.category,
            confidence=classification.confidence,
            matched_rule=classification.matched_rule,
            strategy_weights=weights,
            active_strategies=active,
            pruned_strategies=pruned,
        )
