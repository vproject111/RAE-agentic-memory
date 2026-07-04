"""
Reflection Pipeline - Enterprise Clustering & Generation System

This module implements the complete reflection generation pipeline with:
- Memory clustering using HDBSCAN and k-means
- Hierarchical reflection generation (insight → meta-insight)
- Automatic scoring and prioritization
- Embedding generation for reflections
- Cache-aware generation
- Full telemetry and cost tracking
"""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

import numpy as np
import structlog

# Optional scikit-learn imports for clustering
try:  # pragma: no cover
    from sklearn.cluster import HDBSCAN, KMeans
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover
    HDBSCAN = None  # type: ignore[assignment,misc]
    KMeans = None  # type: ignore[assignment,misc]
    StandardScaler = None  # type: ignore[assignment,misc]
    SKLEARN_AVAILABLE = False

if TYPE_CHECKING:
    from sklearn.cluster import HDBSCAN, KMeans  # noqa: F401
    from sklearn.preprocessing import StandardScaler  # noqa: F401

from apps.memory_api.config import settings
from apps.memory_api.models.reflection_models import (
    GenerateReflectionRequest,
    ReflectionScoring,
    ReflectionTelemetry,
    ReflectionType,
    ReflectionUnit,
)
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.repositories import reflection_repository
from apps.memory_api.services.llm import get_llm_provider
from apps.memory_api.services.ml_service_client import MLServiceClient
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


# ============================================================================
# Prompts
# ============================================================================

CLUSTER_INSIGHT_PROMPT = """
You are analyzing a cluster of related memories to extract key insights.

Memories in this cluster:
{memories}

Your task:
1. Identify the main theme or pattern connecting these memories
2. Extract the most important insight that can be learned
3. Be concise but comprehensive

Provide your insight as a clear, actionable statement.
"""

META_INSIGHT_PROMPT = """
You are analyzing a collection of insights to extract higher-level patterns.

Related insights:
{insights}

Your task:
1. Identify patterns across these insights
2. Extract meta-level understanding
3. Synthesize a broader principle or pattern

Provide your meta-insight as a clear, strategic observation.
"""

REFLECTION_SCORING_PROMPT = """
Evaluate this reflection on multiple dimensions:

Reflection: {reflection}

Score each dimension from 0.0 to 1.0:

1. Novelty: How unique or surprising is this insight?
2. Importance: How significant is this for decision-making?
3. Utility: How actionable or useful is this?
4. Confidence: How confident are you in this assessment?

Return scores as JSON:
{{
  "novelty": 0.0-1.0,
  "importance": 0.0-1.0,
  "utility": 0.0-1.0,
  "confidence": 0.0-1.0
}}
"""


# ============================================================================
# Reflection Pipeline
# ============================================================================


class ReflectionPipeline:
    """
    Enterprise reflection generation pipeline with clustering and hierarchical insights.

    Features:
    - Automatic memory clustering (HDBSCAN or k-means)
    - Per-cluster insight generation
    - Hierarchical meta-insight generation
    - Automatic scoring (novelty, importance, utility, confidence)
    - Embedding generation for similarity search
    - Cache checking to avoid duplicate reflections
    - Full telemetry and cost tracking
    """

    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service
        self.llm_provider = get_llm_provider()
        self.ml_client = MLServiceClient()

    def _ensure_sklearn_available(self) -> None:
        """Ensure scikit-learn is available for clustering operations."""
        if not SKLEARN_AVAILABLE:
            raise RuntimeError(
                "Reflection clustering requires scikit-learn. "
                "Install ML extras: `pip install -r apps/memory_api/requirements-ml.txt` "
                "or run: `pip install scikit-learn`."
            )

    async def generate_reflections(
        self, request: GenerateReflectionRequest
    ) -> Tuple[List[ReflectionUnit], Dict[str, Any]]:
        """
        Generate reflections from memories using clustering pipeline.

        Args:
            request: Generation request with parameters

        Returns:
            Tuple of (generated_reflections, statistics)
        """
        with tracer.start_as_current_span("rae.reflection_pipeline.generate") as span:
            span.set_attribute("rae.tenant_id", request.tenant_id)
            span.set_attribute("rae.project_id", request.project)
            span.set_attribute("rae.reflection.max_memories", request.max_memories)
            span.set_attribute(
                "rae.reflection.min_cluster_size", request.min_cluster_size
            )

            logger.info(
                "reflection_pipeline_started",
                tenant_id=request.tenant_id,
                project=request.project,
                max_memories=request.max_memories,
            )

            start_time = datetime.now()
            statistics = {
                "memories_processed": 0,
                "clusters_found": 0,
                "insights_generated": 0,
                "meta_insights_generated": 0,
                "total_cost_usd": 0.0,
                "total_duration_ms": 0,
            }

            # Step 1: Fetch memories
            memories = await self._fetch_memories(
                request.tenant_id,
                request.project,
                request.max_memories,
                request.memory_filters,
                request.since,
            )

            logger.info(
                "memories_fetch_result",
                tenant_id=request.tenant_id,
                project=request.project,
                count=len(memories) if memories else 0,
                filters=request.memory_filters,
            )

            if not memories:
                span.set_attribute("rae.reflection.memories_count", 0)
                span.set_attribute("rae.outcome.label", "no_memories")
                logger.info("no_memories_for_reflection", project=request.project)
                return [], statistics

            statistics["memories_processed"] = len(memories)
            span.set_attribute("rae.reflection.memories_count", len(memories))
            logger.info("memories_fetched", count=len(memories))

            # Step 2: Cluster memories
            if request.enable_clustering:
                clusters = await self._cluster_memories(
                    memories, request.min_cluster_size
                )
            else:
                # Treat all memories as a single cluster
                clusters = {"global": memories}
                logger.info("clustering_disabled_using_single_global_cluster")

            statistics["clusters_found"] = len(clusters)
            span.set_attribute("rae.reflection.clusters_count", len(clusters))
            logger.info("clustering_complete", clusters=len(clusters))

            if not clusters:
                span.set_attribute("rae.outcome.label", "no_clusters")
                logger.info("no_clusters_found", min_size=request.min_cluster_size)
                return [], statistics

            # Step 3: Generate insights for each cluster
            insights = []
            for cluster_id, cluster_memories in clusters.items():
                try:
                    insight = await self._generate_cluster_insight(
                        tenant_id=request.tenant_id,
                        project_id=request.project,
                        cluster_id=cluster_id,
                        memories=cluster_memories,
                        parent_reflection_id=request.parent_reflection_id,
                    )
                    insights.append(insight)
                    statistics["insights_generated"] += 1
                    if insight.telemetry:
                        statistics["total_cost_usd"] += (
                            insight.telemetry.generation_cost_usd or 0.0
                        )
                except Exception as e:
                    logger.error(
                        "cluster_insight_failed", cluster_id=cluster_id, error=str(e)
                    )

            span.set_attribute("rae.reflection.insights_generated", len(insights))
            logger.info("insights_generated", count=len(insights))

            # Step 4: Generate meta-insights if we have multiple insights
            all_reflections = insights.copy()

            if len(insights) >= 3 and not request.parent_reflection_id:
                try:
                    meta_insight = await self._generate_meta_insight(
                        tenant_id=request.tenant_id,
                        project_id=request.project,
                        insights=insights,
                    )
                    all_reflections.append(meta_insight)
                    statistics["meta_insights_generated"] += 1
                    if meta_insight.telemetry:
                        statistics["total_cost_usd"] += (
                            meta_insight.telemetry.generation_cost_usd or 0.0
                        )
                    span.set_attribute("rae.reflection.meta_insights_generated", 1)
                    logger.info("meta_insight_generated")
                except Exception as e:
                    logger.error("meta_insight_failed", error=str(e))

            # Calculate total duration
            end_time = datetime.now()
            statistics["total_duration_ms"] = int(
                (end_time - start_time).total_seconds() * 1000
            )

            span.set_attribute("rae.reflection.total_reflections", len(all_reflections))
            span.set_attribute(
                "rae.reflection.total_cost_usd", statistics["total_cost_usd"]
            )
            span.set_attribute(
                "rae.reflection.duration_ms", statistics["total_duration_ms"]
            )
            span.set_attribute("rae.outcome.label", "success")

            logger.info(
                "reflection_pipeline_complete",
                reflections=len(all_reflections),
                statistics=statistics,
            )

            return all_reflections, statistics

    async def _fetch_memories(
        self,
        tenant_id: str,
        project_id: str,
        limit: int,
        filters: Optional[Dict[str, Any]],
        since: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """Fetch memories for reflection generation"""
        # Build query filters for RAECoreService
        query_filters = {}
        if since:
            query_filters["since"] = since

        layer = filters.get("layer") if filters else None
        tags = filters.get("tags") if filters else None

        # Use RAECoreService instead of direct pool access
        return await self.rae_service.list_memories(
            tenant_id=tenant_id,
            project=project_id,
            layer=layer,
            tags=tags,
            filters=query_filters,
            limit=limit,
        )

    async def _cluster_memories(
        self, memories: List[Dict[str, Any]], min_cluster_size: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Cluster memories using HDBSCAN/k-means or a simple time-based fallback.
        """
        with tracer.start_as_current_span("rae.reflection_pipeline.cluster") as span:
            span.set_attribute("rae.reflection.cluster.memory_count", len(memories))

            # --- Fallback Clustering (No scikit-learn) ---
            if not SKLEARN_AVAILABLE:
                logger.info("clustering_fallback_active", reason="sklearn_missing")
                # Simple strategy: Group by 4-hour time windows
                clusters: Dict[str, List[Dict[str, Any]]] = {}
                for memory in memories:
                    created_at = memory.get("created_at")
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(
                                created_at.replace("Z", "+00:00")
                            )
                        except Exception:
                            created_at = datetime.now()
                    if created_at:
                        # Bucket by 4 hours
                        bucket = created_at.strftime("%Y-%m-%d-%H")
                        bucket_id = f"time_bucket_{int(created_at.hour // 4)}"
                        key = f"{bucket}-{bucket_id}"
                        if key not in clusters:
                            clusters[key] = []
                        clusters[key].append(memory)

                # Filter small clusters
                valid_clusters = {
                    k: v for k, v in clusters.items() if len(v) >= min_cluster_size
                }
                # If no time clusters, put everything in one global cluster
                if not valid_clusters and len(memories) >= min_cluster_size:
                    valid_clusters = {"global_fallback": memories}

                return valid_clusters

            # --- Standard ML Clustering ---
            self._ensure_sklearn_available()

            span.set_attribute("rae.reflection.cluster.memory_count", len(memories))
            span.set_attribute("rae.reflection.cluster.min_size", min_cluster_size)

            logger.info(
                "clustering_memories", count=len(memories), min_size=min_cluster_size
            )

            # Extract embeddings
            embeddings = []
            valid_memories = []

            # Determine target dimension dynamically from the first valid memory
            target_dim = None

            for memory in memories:
                emb = memory.get("embedding")
                if emb and isinstance(emb, (list, np.ndarray)) and len(emb) > 0:
                    if target_dim is None:
                        target_dim = len(emb)

                    # Strictly filter for consistent dimension in the current batch
                    if len(emb) == target_dim:
                        embeddings.append(emb)
                        valid_memories.append(memory)
                    else:
                        logger.warning(
                            "skipping_incompatible_embedding",
                            expected=target_dim,
                            got=len(emb),
                            memory_id=memory.get("id"),
                        )

            if len(embeddings) < min_cluster_size:
                span.set_attribute(
                    "rae.reflection.cluster.valid_memories", len(embeddings)
                )
                span.set_attribute("rae.outcome.label", "insufficient_memories")
                logger.warning(
                    "insufficient_memories_for_clustering", count=len(embeddings)
                )
                return {}

            span.set_attribute("rae.reflection.cluster.valid_memories", len(embeddings))
            embeddings_array = np.array(embeddings)

            # Standardize embeddings
            scaler = StandardScaler()
            embeddings_scaled = scaler.fit_transform(embeddings_array)

            # Try HDBSCAN first (density-based, automatic cluster detection)
            algorithm_used = "hdbscan"
            try:
                clusterer = HDBSCAN(
                    min_cluster_size=min_cluster_size,
                    min_samples=max(2, min_cluster_size // 2),
                    metric="euclidean",
                )
                # Offload CPU-bound clustering to thread pool
                cluster_labels = await asyncio.to_thread(
                    clusterer.fit_predict, embeddings_scaled
                )

                # Check if we got meaningful clusters (not all noise)
                unique_labels = set(cluster_labels)
                unique_labels.discard(-1)  # Remove noise label

                if len(unique_labels) == 0:
                    # Fall back to k-means
                    logger.info("hdbscan_found_no_clusters_falling_back_to_kmeans")
                    raise ValueError("No clusters found")

            except Exception as e:
                algorithm_used = "kmeans"
                logger.info("using_kmeans_clustering", reason=str(e))
                # Fall back to k-means with heuristic for number of clusters
                n_clusters = max(2, min(len(embeddings) // min_cluster_size, 10))
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                # Offload CPU-bound clustering to thread pool
                cluster_labels = await asyncio.to_thread(
                    clusterer.fit_predict, embeddings_scaled
                )

            span.set_attribute("rae.reflection.cluster.algorithm", algorithm_used)

            # Group memories by cluster
            ml_clusters: Dict[str, List[Dict[str, Any]]] = {}
            for memory, label in zip(valid_memories, cluster_labels):
                if label == -1:  # Skip noise in HDBSCAN
                    continue

                cluster_id = f"cluster_{label}"
                if cluster_id not in ml_clusters:
                    ml_clusters[cluster_id] = []
                ml_clusters[cluster_id].append(memory)

            # Filter out clusters below minimum size
            clusters = {
                cid: mems
                for cid, mems in ml_clusters.items()
                if len(mems) >= min_cluster_size
            }

            span.set_attribute("rae.reflection.cluster.clusters_found", len(clusters))
            if clusters:
                span.set_attribute(
                    "rae.reflection.cluster.avg_cluster_size",
                    sum(len(mems) for mems in clusters.values()) / len(clusters),
                )
            span.set_attribute("rae.outcome.label", "success")

            logger.info(
                "clustering_complete",
                clusters_found=len(clusters),
                sizes=[len(mems) for mems in clusters.values()],
            )

            return clusters

    async def _generate_cluster_insight(
        self,
        tenant_id: str,
        project_id: str,
        cluster_id: str,
        memories: List[Dict[str, Any]],
        parent_reflection_id: Optional[UUID] = None,
    ) -> ReflectionUnit:
        """Generate insight for a single cluster of memories"""
        logger.info(
            "generating_cluster_insight", cluster_id=cluster_id, memories=len(memories)
        )

        generation_start = datetime.now()

        # Format memories for prompt
        memory_texts = [
            f"- [{m.get('created_at', 'unknown')}] {m.get('content', '')}"
            for m in memories[:20]  # Limit to 20 for context window
        ]
        memories_formatted = "\n".join(memory_texts)

        # Generate insight using LLM
        prompt = CLUSTER_INSIGHT_PROMPT.format(memories=memories_formatted)

        try:
            result = await self.llm_provider.generate(
                system="You are an expert at pattern recognition and insight extraction.",
                prompt=prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
            )

            insight_text = result.text

            # Calculate generation metrics
            generation_duration = int(
                (datetime.now() - generation_start).total_seconds() * 1000
            )

            # Score the insight
            scoring = await self._score_reflection(insight_text)

            # Generate embedding for the insight
            embedding = await self._generate_embedding(insight_text)

            # Extract source memory IDs
            source_memory_ids = [UUID(m["id"]) for m in memories if m.get("id")]

            # Create telemetry
            telemetry = ReflectionTelemetry(
                generation_model=settings.RAE_LLM_MODEL_DEFAULT,
                generation_duration_ms=generation_duration,
                generation_tokens_used=(
                    result.usage.total_tokens if result.usage else None
                ),
                generation_cost_usd=getattr(cast(Any, result), "cost_usd", None),
            )

            # Determine priority based on cluster size and importance
            priority = self._calculate_priority(len(memories), scoring)

            # Create reflection in database
            # Create reflection in database
            reflection = await reflection_repository.create_reflection(
                pool=self.rae_service.postgres_pool,
                tenant_id=tenant_id,
                project_id=project_id,
                content=insight_text,
                reflection_type=ReflectionType.INSIGHT,
                priority=priority,
                scoring=scoring,
                parent_reflection_id=parent_reflection_id,
                source_memory_ids=source_memory_ids,
                embedding=embedding,
                cluster_id=cluster_id,
                tags=["cluster_insight", cluster_id],
                telemetry=telemetry,
            )

            logger.info(
                "cluster_insight_generated",
                reflection_id=str(reflection.id),
                score=reflection.score,
                priority=priority,
            )

            return reflection

        except Exception as e:
            logger.error("cluster_insight_generation_failed", error=str(e))
            raise

    async def _generate_meta_insight(
        self, tenant_id: str, project_id: str, insights: List[ReflectionUnit]
    ) -> ReflectionUnit:
        """Generate meta-insight from multiple insights"""
        logger.info("generating_meta_insight", insights=len(insights))

        generation_start = datetime.now()

        # Format insights for prompt
        insight_texts = [
            f"- {insight.content}"
            for insight in insights[:10]  # Limit to 10 for context window
        ]
        insights_formatted = "\n".join(insight_texts)

        # Generate meta-insight using LLM
        prompt = META_INSIGHT_PROMPT.format(insights=insights_formatted)

        try:
            result = await self.llm_provider.generate(
                system="You are an expert at synthesizing higher-level patterns from insights.",
                prompt=prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
            )

            meta_insight_text = result.text

            # Calculate generation metrics
            generation_duration = int(
                (datetime.now() - generation_start).total_seconds() * 1000
            )

            # Score the meta-insight (typically higher scores for synthesis)
            scoring = await self._score_reflection(meta_insight_text)
            # Boost scores slightly for meta-insights
            scoring.importance_score = min(1.0, scoring.importance_score * 1.1)
            scoring.utility_score = min(1.0, scoring.utility_score * 1.1)

            # Generate embedding
            embedding = await self._generate_embedding(meta_insight_text)

            # Extract source reflection IDs
            source_reflection_ids = [insight.id for insight in insights]

            # Create telemetry
            telemetry = ReflectionTelemetry(
                generation_model=settings.RAE_LLM_MODEL_DEFAULT,
                generation_duration_ms=generation_duration,
                generation_tokens_used=(
                    result.usage.total_tokens if result.usage else None
                ),
                generation_cost_usd=getattr(cast(Any, result), "cost_usd", None),
            )

            # Meta-insights get high priority
            priority = 5

            # Create meta-reflection in database
            # Create reflection in database
            reflection = await reflection_repository.create_reflection(
                pool=self.rae_service.postgres_pool,
                tenant_id=tenant_id,
                project_id=project_id,
                content=meta_insight_text,
                reflection_type=ReflectionType.META,
                priority=priority,
                scoring=scoring,
                source_reflection_ids=source_reflection_ids,
                embedding=embedding,
                tags=["meta_insight", "synthesis"],
                telemetry=telemetry,
            )

            logger.info(
                "meta_insight_generated",
                reflection_id=str(reflection.id),
                score=reflection.score,
            )

            return reflection

        except Exception as e:
            logger.error("meta_insight_generation_failed", error=str(e))
            raise

    async def _score_reflection(self, reflection_text: str) -> ReflectionScoring:
        """
        Score a reflection on multiple dimensions using LLM.

        Args:
            reflection_text: The reflection content to score

        Returns:
            ReflectionScoring with component scores
        """
        try:
            prompt = REFLECTION_SCORING_PROMPT.format(reflection=reflection_text)

            # Use structured output for reliable parsing
            from pydantic import BaseModel, Field

            class ScoreResponse(BaseModel):
                novelty: float = Field(..., ge=0.0, le=1.0)
                importance: float = Field(..., ge=0.0, le=1.0)
                utility: float = Field(..., ge=0.0, le=1.0)
                confidence: float = Field(..., ge=0.0, le=1.0)

            result = await self.llm_provider.generate_structured(
                system="You are an expert evaluator of insights and reflections.",
                prompt=prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
                response_model=ScoreResponse,
            )
            result = cast(ScoreResponse, result)

            return ReflectionScoring(
                novelty_score=result.novelty,
                importance_score=result.importance,
                utility_score=result.utility,
                confidence_score=result.confidence,
            )

        except Exception as e:
            logger.warning("scoring_failed_using_defaults", error=str(e))
            # Return default middle scores
            return ReflectionScoring(
                novelty_score=0.5,
                importance_score=0.5,
                utility_score=0.5,
                confidence_score=0.5,
            )

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for reflection text"""
        try:
            result = await self.ml_client.generate_embeddings([text])
            if result and "embeddings" in result and len(result["embeddings"]) > 0:
                return cast(List[float], result["embeddings"][0])
            return [0.0] * 1536
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Return zero vector as fallback
            return [0.0] * 1536

    def _calculate_priority(self, cluster_size: int, scoring: ReflectionScoring) -> int:
        """
        Calculate priority (1-5) based on cluster size and scores.

        Larger clusters and higher scores get higher priority.
        """
        # Base priority from composite score
        score_priority = scoring.composite_score * 5

        # Bonus for larger clusters (more evidence)
        size_bonus = min(1.0, cluster_size / 10)  # Max bonus at 10+ memories

        # Calculate final priority
        priority = int(round(score_priority + size_bonus))

        # Clamp to 1-5 range
        return max(1, min(5, priority))
