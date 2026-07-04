"""
Query Analyzer - LLM-Based Query Intent Classification and Strategy Selection

This service analyzes user queries to:
- Classify query intent (factual, conceptual, exploratory, etc.)
- Extract key entities and concepts
- Recommend optimal search strategies
- Calculate dynamic weights for hybrid search
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import structlog
from pydantic import BaseModel

from apps.memory_api.config import settings
from apps.memory_api.models.hybrid_search_models import (
    DEFAULT_WEIGHT_PROFILES,
    QueryAnalysis,
    QueryIntent,
    SearchStrategy,
)
from apps.memory_api.services.llm import get_llm_provider

logger = structlog.get_logger(__name__)


# ============================================================================
# Prompts
# ============================================================================

QUERY_ANALYSIS_PROMPT = """You are a query analysis expert. Analyze the following search query and provide structured classification.

Query: "{query}"

Your task:
1. Classify the INTENT of the query
2. Extract KEY ENTITIES (named entities, specific things)
3. Extract KEY CONCEPTS (abstract ideas, topics)
4. Identify TEMPORAL MARKERS (time-related terms like "recent", "last week", dates)
5. Identify RELATION TYPES (words indicating relationships like "between", "related to", "causes")
6. Recommend SEARCH STRATEGIES (vector, semantic, graph, fulltext)
7. Suggest WEIGHTS for each strategy (must sum to 1.0)

Intent types:
- factual: Looking for specific facts or information
- conceptual: Understanding concepts and their relationships
- exploratory: Open-ended exploration, browsing
- temporal: Time-based queries (recent, historical, timeline)
- relational: Finding relationships and connections
- aggregative: Summary, statistics, aggregation

Search strategies:
- vector: Semantic similarity using embeddings
- semantic: Knowledge graph nodes and definitions
- graph: Graph traversal and relationships
- fulltext: Keyword-based text search

Examples:

Query: "What authentication methods did we implement last quarter?"
{{
  "intent": "temporal",
  "confidence": 0.9,
  "key_entities": ["authentication methods"],
  "key_concepts": ["authentication", "implementation"],
  "temporal_markers": ["last quarter"],
  "relation_types": [],
  "recommended_strategies": ["vector", "fulltext", "temporal"],
  "strategy_weights": {{"vector": 0.4, "semantic": 0.2, "graph": 0.1, "fulltext": 0.3}},
  "requires_temporal_filtering": true,
  "requires_graph_traversal": false
}}

Query: "How does the payment system relate to our authentication layer?"
{{
  "intent": "relational",
  "confidence": 0.95,
  "key_entities": ["payment system", "authentication layer"],
  "key_concepts": ["payment", "authentication", "system architecture"],
  "temporal_markers": [],
  "relation_types": ["relate to"],
  "recommended_strategies": ["graph", "semantic", "vector"],
  "strategy_weights": {{"vector": 0.2, "semantic": 0.3, "graph": 0.4, "fulltext": 0.1}},
  "requires_temporal_filtering": false,
  "requires_graph_traversal": true,
  "suggested_depth": 3
}}

Query: "Show me everything about microservices architecture"
{{
  "intent": "exploratory",
  "confidence": 0.85,
  "key_entities": [],
  "key_concepts": ["microservices", "architecture"],
  "temporal_markers": [],
  "relation_types": [],
  "recommended_strategies": ["semantic", "vector", "graph"],
  "strategy_weights": {{"vector": 0.3, "semantic": 0.4, "graph": 0.2, "fulltext": 0.1}},
  "requires_temporal_filtering": false,
  "requires_graph_traversal": false
}}

Now analyze this query and return ONLY valid JSON matching the schema:
"""


# ============================================================================
# Query Analyzer
# ============================================================================


class QueryAnalyzer:
    """
    LLM-based query analyzer for intent classification and strategy selection.

    Features:
    - Intent classification (6 types)
    - Entity and concept extraction
    - Dynamic weight calculation
    - Strategy recommendation
    - Temporal and graph detection
    """

    def __init__(self):
        """Initialize query analyzer"""
        self.llm_provider = get_llm_provider()
        self.weight_profiles = DEFAULT_WEIGHT_PROFILES

    async def analyze_intent(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        context: Optional[List[str]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> QueryAnalysis:
        """
        Analyze query using LLM to determine intent and optimal strategies.

        Args:
            query: User search query
            context: Optional conversation history for context
            user_preferences: Optional user preferences

        Returns:
            QueryAnalysis with intent, entities, and recommended strategies
        """
        logger.info("query_analysis_started", query=query)

        try:
            # Add context if provided
            full_prompt = QUERY_ANALYSIS_PROMPT.format(query=query)

            if context:
                context_str = "\n".join([f"- {c}" for c in context[-3:]])  # Last 3
                full_prompt += f"\n\nConversation context:\n{context_str}"

            # Call LLM for structured analysis
            result = await self.llm_provider.generate_structured(
                system="You are a query analysis expert specializing in search optimization.",
                prompt=full_prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
                response_model=QueryAnalysisResult,
            )
            result = cast(QueryAnalysisResult, result)

            # Convert to QueryAnalysis
            analysis = QueryAnalysis(
                intent=QueryIntent(result.intent),
                confidence=result.confidence,
                key_entities=result.key_entities,
                key_concepts=result.key_concepts,
                temporal_markers=result.temporal_markers,
                relation_types=result.relation_types,
                recommended_strategies=[
                    SearchStrategy(s) for s in result.recommended_strategies
                ],
                strategy_weights=result.strategy_weights,
                requires_temporal_filtering=result.requires_temporal_filtering,
                requires_graph_traversal=result.requires_graph_traversal,
                suggested_depth=result.suggested_depth,
                original_query=query,
                analyzed_at=datetime.now(timezone.utc),
            )

            logger.info(
                "query_analysis_complete",
                intent=analysis.intent.value,
                confidence=analysis.confidence,
                strategies=len(analysis.recommended_strategies),
            )

            return analysis

        except Exception as e:
            logger.error("query_analysis_failed", error=str(e))
            # Fallback to balanced strategy
            return self._create_fallback_analysis(query)

    async def calculate_dynamic_weights(
        self, query_analysis: QueryAnalysis
    ) -> Dict[SearchStrategy, float]:
        """
        Calculate dynamic weights based on query analysis.

        Weights are calculated from:
        1. LLM-suggested weights (if available)
        2. Intent-based weight profile
        3. Default balanced profile (fallback)

        Args:
            query_analysis: Analyzed query

        Returns:
            Dictionary of strategy weights (sum to 1.0)
        """
        logger.info("calculating_dynamic_weights", intent=query_analysis.intent.value)

        # Use LLM-suggested weights if available and valid
        if query_analysis.strategy_weights:
            weights = {
                SearchStrategy(k): v for k, v in query_analysis.strategy_weights.items()
            }

            # Validate weights sum to ~1.0
            total = sum(weights.values())
            if 0.95 <= total <= 1.05:
                # Normalize to exactly 1.0
                normalized = {k: v / total for k, v in weights.items()}
                logger.info("using_llm_suggested_weights", weights=normalized)
                return normalized

        # Fallback to intent-based profile
        intent_weights = self._get_weights_for_intent(query_analysis.intent)

        logger.info(
            "using_intent_based_weights",
            intent=query_analysis.intent.value,
            weights=intent_weights,
        )

        return intent_weights

    def _get_weights_for_intent(
        self, intent: QueryIntent
    ) -> Dict[SearchStrategy, float]:
        """
        Get optimal weights for a specific query intent.

        Maps intents to pre-defined weight profiles.

        Args:
            intent: Query intent

        Returns:
            Dictionary of strategy weights
        """
        intent_to_profile = {
            QueryIntent.FACTUAL: "factual",
            QueryIntent.CONCEPTUAL: "conceptual",
            QueryIntent.EXPLORATORY: "balanced",
            QueryIntent.TEMPORAL: "factual",  # Temporal queries benefit from vector + fulltext
            QueryIntent.RELATIONAL: "relational",
            QueryIntent.AGGREGATIVE: "balanced",
        }

        profile_name = intent_to_profile.get(intent, "balanced")
        profile = self.weight_profiles[profile_name]

        return profile.weights

    def _create_fallback_analysis(self, query: str) -> QueryAnalysis:
        """
        Create fallback analysis when LLM analysis fails.

        Uses heuristics to provide reasonable defaults.

        Args:
            query: Original query

        Returns:
            QueryAnalysis with balanced defaults
        """
        logger.info("creating_fallback_analysis", query=query)

        # Simple heuristics
        query_lower = query.lower()

        # Detect intent from keywords
        intent = QueryIntent.EXPLORATORY  # Default

        if any(
            word in query_lower for word in ["how", "relate", "connection", "between"]
        ):
            intent = QueryIntent.RELATIONAL
        elif any(word in query_lower for word in ["what", "when", "who", "specific"]):
            intent = QueryIntent.FACTUAL
        elif any(word in query_lower for word in ["concept", "understand", "explain"]):
            intent = QueryIntent.CONCEPTUAL
        elif any(
            word in query_lower for word in ["recent", "last", "yesterday", "ago"]
        ):
            intent = QueryIntent.TEMPORAL

        # Extract simple entities (words in quotes or capitalized sequences)
        entities = []
        if '"' in query:
            entities = [word.strip('"') for word in query.split('"') if word.strip()]

        # Use balanced weights
        balanced_profile = self.weight_profiles["balanced"]

        return QueryAnalysis(
            intent=intent,
            confidence=0.5,  # Lower confidence for fallback
            key_entities=entities,
            key_concepts=[],
            temporal_markers=[],
            relation_types=[],
            recommended_strategies=[
                SearchStrategy.VECTOR,
                SearchStrategy.SEMANTIC,
                SearchStrategy.GRAPH,
                SearchStrategy.FULLTEXT,
            ],
            strategy_weights={
                "vector": balanced_profile.weights[SearchStrategy.VECTOR],
                "semantic": balanced_profile.weights[SearchStrategy.SEMANTIC],
                "graph": balanced_profile.weights[SearchStrategy.GRAPH],
                "fulltext": balanced_profile.weights[SearchStrategy.FULLTEXT],
            },
            requires_temporal_filtering=intent == QueryIntent.TEMPORAL,
            requires_graph_traversal=intent == QueryIntent.RELATIONAL,
            suggested_depth=3 if intent == QueryIntent.RELATIONAL else None,
            original_query=query,
        )

    def get_available_profiles(self) -> Dict[str, Dict]:
        """
        Get all available weight profiles.

        Returns:
            Dictionary of profile name to profile details
        """
        return {
            name: {
                "description": profile.description,
                "weights": {k.value: v for k, v in profile.weights.items()},
                "use_cases": profile.use_cases,
            }
            for name, profile in self.weight_profiles.items()
        }

    async def explain_analysis(self, analysis: QueryAnalysis) -> str:
        """
        Generate human-readable explanation of query analysis.

        Args:
            analysis: Query analysis

        Returns:
            Explanation string
        """
        explanation = f"Query Intent: {analysis.intent.value} (confidence: {analysis.confidence:.2f})\n"

        if analysis.key_entities:
            explanation += f"Key Entities: {', '.join(analysis.key_entities)}\n"

        if analysis.key_concepts:
            explanation += f"Key Concepts: {', '.join(analysis.key_concepts)}\n"

        explanation += "\nRecommended Strategies:\n"
        for strategy in analysis.recommended_strategies:
            weight = analysis.strategy_weights.get(strategy.value, 0.0)
            explanation += f"  - {strategy.value}: {weight:.2%}\n"

        if analysis.requires_temporal_filtering:
            explanation += "\nTemporal filtering recommended\n"

        if analysis.requires_graph_traversal:
            depth = analysis.suggested_depth or 3
            explanation += f"\nGraph traversal recommended (depth: {depth})\n"

        return explanation


# ============================================================================
# Pydantic Model for LLM Response
# ============================================================================


class QueryAnalysisResult(BaseModel):
    """Structured output from LLM query analysis"""

    intent: str
    confidence: float
    key_entities: List[str]
    key_concepts: List[str]
    temporal_markers: List[str]
    relation_types: List[str]
    recommended_strategies: List[str]
    strategy_weights: Dict[str, float]
    requires_temporal_filtering: bool
    requires_graph_traversal: bool
    suggested_depth: Optional[int] = None
