"""
Importance Scoring Service - Automatic memory prioritization
"""

import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class ImportanceLevel(str, Enum):
    """Memory importance levels"""

    CRITICAL = "critical"  # Score > 0.8
    HIGH = "high"  # Score > 0.6
    MEDIUM = "medium"  # Score > 0.4
    LOW = "low"  # Score > 0.2
    MINIMAL = "minimal"  # Score <= 0.2


class ScoringFactors:
    """Weights for different scoring factors"""

    def __init__(
        self,
        recency: float = 0.15,
        access_frequency: float = 0.20,
        graph_centrality: float = 0.15,
        semantic_relevance: float = 0.15,
        user_rating: float = 0.10,
        consolidation: float = 0.10,
        manual_boost: float = 0.15,
    ):
        """
        Initialize scoring factor weights

        All weights should sum to 1.0 for normalized scoring.

        Args:
            recency: Weight for how recent the memory is
            access_frequency: Weight for how often memory is accessed
            graph_centrality: Weight for centrality in knowledge graph
            semantic_relevance: Weight for semantic similarity to recent queries
            user_rating: Weight for explicit user ratings
            consolidation: Weight for consolidated/reflected memories
            manual_boost: Weight for manually boosted memories
        """
        self.recency = recency
        self.access_frequency = access_frequency
        self.graph_centrality = graph_centrality
        self.semantic_relevance = semantic_relevance
        self.user_rating = user_rating
        self.consolidation = consolidation
        self.manual_boost = manual_boost

        # Validate weights sum to 1.0
        total = sum(
            [
                recency,
                access_frequency,
                graph_centrality,
                semantic_relevance,
                user_rating,
                consolidation,
                manual_boost,
            ]
        )
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            logger.warning(
                "scoring_weights_not_normalized",
                total=total,
                message="Scoring factor weights should sum to 1.0",
            )


class Memory:
    """Memory representation for scoring"""

    def __init__(
        self,
        id: str,
        content: str,
        layer: str,
        tenant_id: UUID,
        created_at: datetime,
        accessed_at: Optional[datetime] = None,
        access_count: int = 0,
        graph_centrality: float = 0.0,
        user_rating: Optional[float] = None,
        is_consolidated: bool = False,
        manual_importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.content = content
        self.layer = layer
        self.tenant_id = tenant_id
        self.created_at = created_at
        self.accessed_at = accessed_at or created_at
        self.access_count = access_count
        self.graph_centrality = graph_centrality
        self.user_rating = user_rating
        self.is_consolidated = is_consolidated
        self.manual_importance = manual_importance
        self.metadata = metadata or {}

        # Calculated importance
        self.importance_score: Optional[float] = None
        self.importance_level: Optional[ImportanceLevel] = None


class ImportanceScoringService:
    """Service for calculating memory importance scores"""

    def __init__(
        self,
        rae_service: RAECoreService,
        scoring_factors: Optional[ScoringFactors] = None,
    ):
        """
        Initialize importance scoring service

        Args:
            rae_service: RAECoreService instance
            scoring_factors: Custom scoring factor weights
        """
        self.rae_service = rae_service
        self.scoring_factors = scoring_factors or ScoringFactors()

    async def calculate_importance(
        self, memory: Memory, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        Calculate importance score for a memory

        Args:
            memory: Memory to score
            context: Optional context for scoring (e.g., recent queries)

        Returns:
            Importance score between 0.0 and 1.0
        """
        context = context or {}

        # Calculate individual factor scores
        recency_score = await self._calculate_recency_score(memory)
        access_score = await self._calculate_access_score(memory)
        centrality_score = memory.graph_centrality  # Already normalized 0-1
        relevance_score = await self._calculate_relevance_score(memory, context)
        rating_score = self._calculate_rating_score(memory)
        consolidation_score = 1.0 if memory.is_consolidated else 0.0
        manual_score = memory.manual_importance or 0.5  # Default to neutral

        # Weighted combination
        importance = (
            self.scoring_factors.recency * recency_score
            + self.scoring_factors.access_frequency * access_score
            + self.scoring_factors.graph_centrality * centrality_score
            + self.scoring_factors.semantic_relevance * relevance_score
            + self.scoring_factors.user_rating * rating_score
            + self.scoring_factors.consolidation * consolidation_score
            + self.scoring_factors.manual_boost * manual_score
        )

        # Ensure score is in [0, 1]
        importance = max(0.0, min(1.0, importance))

        # Update memory
        memory.importance_score = importance
        memory.importance_level = self._score_to_level(importance)

        logger.debug(
            "importance_calculated",
            memory_id=memory.id,
            score=importance,
            level=memory.importance_level.value,
            factors={
                "recency": recency_score,
                "access": access_score,
                "centrality": centrality_score,
                "relevance": relevance_score,
                "rating": rating_score,
                "consolidated": consolidation_score,
                "manual": manual_score,
            },
        )

        return importance

    async def _calculate_recency_score(self, memory: Memory) -> float:
        """
        Calculate recency score using exponential decay

        Recent memories score higher, with exponential decay over time.
        """
        now = datetime.now(timezone.utc)
        age_seconds = (now - memory.created_at).total_seconds()

        # Decay parameters
        # Half-life of 7 days (604800 seconds)
        half_life = 604800

        # Exponential decay: score = 2^(-age/half_life)
        score = math.pow(2, -age_seconds / half_life)

        return score

    async def _calculate_access_score(self, memory: Memory) -> float:
        """
        Calculate access frequency score

        More frequently accessed memories score higher.
        Also considers recency of last access.
        """
        if memory.access_count == 0:
            return 0.0

        # Access frequency component (logarithmic to prevent dominance)
        # Score reaches 0.8 at 100 accesses
        frequency_component = min(
            math.log10(memory.access_count + 1) / math.log10(100), 0.8
        )

        # Recency of last access component
        now = datetime.now(timezone.utc)
        days_since_access = (now - memory.accessed_at).days

        # Decay over 30 days
        recency_component = max(0, 1 - days_since_access / 30)

        # Combine (70% frequency, 30% recency)
        score = 0.7 * frequency_component + 0.3 * recency_component

        return min(score, 1.0)

    async def _calculate_relevance_score(
        self, memory: Memory, context: Dict[str, Any]
    ) -> float:
        """
        Calculate semantic relevance to recent queries/context

        Uses vector similarity if available.
        """
        recent_queries = context.get("recent_queries", [])

        if not recent_queries:
            return 0.5  # Neutral score if no context

        if not self.rae_service or not self.rae_service.qdrant_client:
            return 0.5  # Neutral if vector store unavailable

        # In production, calculate semantic similarity
        # between memory and recent queries
        # For now, return neutral score
        return 0.5

    def _calculate_rating_score(self, memory: Memory) -> float:
        """
        Convert user rating to normalized score

        User ratings are typically 1-5 stars.
        """
        if memory.user_rating is None:
            return 0.5  # Neutral if no rating

        # Normalize rating (assuming 1-5 scale) to 0-1
        normalized = (memory.user_rating - 1) / 4

        return max(0.0, min(1.0, normalized))

    def _score_to_level(self, score: float) -> ImportanceLevel:
        """Convert numeric score to importance level"""
        if score > 0.8:
            return ImportanceLevel.CRITICAL
        elif score > 0.6:
            return ImportanceLevel.HIGH
        elif score > 0.4:
            return ImportanceLevel.MEDIUM
        elif score > 0.2:
            return ImportanceLevel.LOW
        else:
            return ImportanceLevel.MINIMAL

    async def recalculate_all_scores(
        self, tenant_id: UUID, batch_size: int = 100
    ) -> Dict[str, Any]:
        """
        Recalculate importance scores for all memories

        Args:
            tenant_id: Tenant UUID
            batch_size: Number of memories to process per batch

        Returns:
            Statistics about recalculation
        """
        logger.info(
            "recalculating_all_scores", tenant_id=str(tenant_id), batch_size=batch_size
        )

        stats = {
            "total_processed": 0,
            "by_level": {level.value: 0 for level in ImportanceLevel},
        }

        # In production, fetch memories in batches from database
        # For now, return empty stats

        logger.info("recalculation_complete", tenant_id=str(tenant_id), stats=stats)

        return stats

    async def get_top_important_memories(
        self,
        tenant_id: UUID,
        limit: int = 20,
        layer: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Memory]:
        """
        Get most important memories for tenant

        Args:
            tenant_id: Tenant UUID
            limit: Maximum number of memories to return
            layer: Optional layer filter
            min_score: Minimum importance score

        Returns:
            List of Memory objects sorted by importance
        """
        # In production, query database sorted by importance_score
        # For now, return empty list

        return []

    async def boost_importance(
        self, memory_id: str, boost_amount: float = 0.2, reason: Optional[str] = None
    ):
        """
        Manually boost a memory's importance

        Args:
            memory_id: Memory ID
            boost_amount: Amount to boost (0.0 to 1.0)
            reason: Optional reason for boost
        """
        logger.info(
            "importance_boosted",
            memory_id=memory_id,
            boost_amount=boost_amount,
            reason=reason,
        )

        # In production, update memory.manual_importance
        # and recalculate score

    async def decay_importance(
        self,
        tenant_id: UUID,
        decay_rate: float = 0.01,
        consider_access_stats: bool = True,
    ) -> int:
        """
        Apply time-based decay to all memories with temporal considerations.
        """
        logger.info(
            "applying_importance_decay",
            tenant_id=str(tenant_id),
            decay_rate=decay_rate,
            consider_access_stats=consider_access_stats,
        )

        if not self.rae_service:
            logger.warning(
                "decay_importance_skipped",
                tenant_id=str(tenant_id),
                reason="no_rae_service",
            )
            return 0

        try:
            updated_count = await self.rae_service.decay_importance(
                tenant_id=str(tenant_id),
                decay_rate=decay_rate,
                consider_access_stats=consider_access_stats,
            )

            logger.info(
                "importance_decay_complete",
                tenant_id=str(tenant_id),
                updated_count=updated_count,
                decay_rate=decay_rate,
                consider_access_stats=consider_access_stats,
            )

            return updated_count

        except Exception as e:
            logger.error(
                "importance_decay_failed",
                tenant_id=str(tenant_id),
                error=str(e),
                decay_rate=decay_rate,
            )
            raise

    async def get_importance_distribution(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get distribution of importance scores for analysis

        Args:
            tenant_id: Tenant UUID

        Returns:
            Statistics about importance distribution
        """
        # In production, calculate actual distribution
        return {
            "total_memories": 0,
            "by_level": {level.value: 0 for level in ImportanceLevel},
            "avg_score": 0.0,
            "median_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "score_histogram": [],
        }

    async def identify_undervalued_memories(
        self, tenant_id: UUID, threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Identify memories that might be more important than their score suggests

        Looks for:
        - Memories with high centrality but low score
        - Memories frequently accessed recently but low score
        - Memories connected to important entities

        Args:
            tenant_id: Tenant UUID
            threshold: Score threshold for undervalued

        Returns:
            List of potentially undervalued memories with reasons
        """
        undervalued: List[Dict[str, Any]] = []

        # In production, query for memories with:
        # - High graph_centrality but low importance_score
        # - Recent high access_count but low importance_score
        # - Connected to high-importance entities

        return undervalued

    async def suggest_importance_adjustments(
        self, tenant_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Suggest manual importance adjustments

        Uses ML/heuristics to identify memories that should be
        manually reviewed for importance.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of suggestions with reasoning
        """
        suggestions = []

        # Identify undervalued memories
        undervalued = await self.identify_undervalued_memories(tenant_id)

        for memory_info in undervalued:
            suggestions.append(
                {
                    "memory_id": memory_info["memory_id"],
                    "action": "boost",
                    "current_score": memory_info["current_score"],
                    "suggested_score": memory_info["suggested_score"],
                    "reason": memory_info["reason"],
                    "confidence": memory_info["confidence"],
                }
            )

        return suggestions

    async def auto_archive_low_importance(
        self, tenant_id: UUID, threshold: float = 0.1, min_age_days: int = 90
    ) -> List[str]:
        """
        Automatically archive very low importance memories

        Args:
            tenant_id: Tenant UUID
            threshold: Importance threshold for archival
            min_age_days: Minimum age before archival

        Returns:
            List of archived memory IDs
        """
        logger.info(
            "auto_archiving_low_importance",
            tenant_id=str(tenant_id),
            threshold=threshold,
            min_age_days=min_age_days,
        )

        archived: List[str] = []

        # In production:
        # 1. Find memories with importance < threshold
        # 2. Filter to memories older than min_age_days
        # 3. Move to archive (don't delete, just mark as archived)

        logger.info(
            "auto_archive_complete",
            tenant_id=str(tenant_id),
            archived_count=len(archived),
        )

        return archived

    async def get_importance_trends(
        self, tenant_id: UUID, period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze importance score trends over time

        Args:
            tenant_id: Tenant UUID
            period_days: Period to analyze

        Returns:
            Trend analysis data
        """
        # In production, track score changes over time
        return {
            "period_days": period_days,
            "avg_score_change": 0.0,
            "trending_up": [],  # Memories gaining importance
            "trending_down": [],  # Memories losing importance
            "stable": [],  # Memories with stable importance
            "volatility": 0.0,  # Score volatility measure
        }

    def get_scoring_explanation(self, memory: Memory) -> Dict[str, Any]:
        """
        Get detailed explanation of importance score

        Useful for debugging and transparency.

        Args:
            memory: Memory to explain

        Returns:
            Detailed scoring breakdown
        """
        if memory.importance_score is None:
            return {"error": "Memory has not been scored"}

        return {
            "memory_id": memory.id,
            "overall_score": memory.importance_score,
            "level": memory.importance_level.value if memory.importance_level else None,
            "factors": {
                "recency": {
                    "weight": self.scoring_factors.recency,
                    "days_old": (datetime.now(timezone.utc) - memory.created_at).days,
                },
                "access_frequency": {
                    "weight": self.scoring_factors.access_frequency,
                    "access_count": memory.access_count,
                    "days_since_access": (
                        datetime.now(timezone.utc) - memory.accessed_at
                    ).days,
                },
                "graph_centrality": {
                    "weight": self.scoring_factors.graph_centrality,
                    "score": memory.graph_centrality,
                },
                "user_rating": {
                    "weight": self.scoring_factors.user_rating,
                    "rating": memory.user_rating,
                },
                "consolidated": {
                    "weight": self.scoring_factors.consolidation,
                    "is_consolidated": memory.is_consolidated,
                },
                "manual": {
                    "weight": self.scoring_factors.manual_boost,
                    "manual_score": memory.manual_importance,
                },
            },
            "recommendations": self._generate_recommendations(memory),
        }

    def _generate_recommendations(self, memory: Memory) -> List[str]:
        """Generate recommendations for improving importance"""
        recommendations = []

        if memory.access_count < 5:
            recommendations.append(
                "Memory has low access count. Consider if it's still relevant."
            )

        if (datetime.now(timezone.utc) - memory.accessed_at).days > 30:
            recommendations.append(
                "Memory hasn't been accessed recently. Consider archival."
            )

        if memory.graph_centrality < 0.1:
            recommendations.append(
                "Memory has low connectivity. Consider adding more relationships."
            )

        if not memory.is_consolidated:
            recommendations.append(
                "Memory is not consolidated. Consider running reflection."
            )

        return recommendations
