from typing import TYPE_CHECKING, Any, Dict, List, Optional

import asyncpg
import structlog
from pydantic import BaseModel, Field

from apps.memory_api import metrics
from apps.memory_api.config import settings
from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.graph_extraction import (
    GraphExtractionResult,
    GraphExtractionService,
)
from apps.memory_api.services.llm import get_llm_provider

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


# Legacy models for backward compatibility
class Triple(BaseModel):
    """
    Legacy triple model - use GraphTriple instead for new code.
    Represents a (Subject, Relation, Object) triple.
    """

    source: str = Field(..., description="The source entity")
    relation: str = Field(..., description="The relationship between the entities")
    target: str = Field(..., description="The target entity")


class Triples(BaseModel):
    """
    Legacy triples collection - use GraphExtractionResult instead.
    Represents a list of triples.
    """

    triples: List[Triple]


REFLECTION_PROMPT = """
You are a reasoning engine that synthesizes key insights from a list of recent events.
Your task is to extract significant relationships between entities as (Subject) -> [RELATION] -> (Object) triples.
Focus on extracting the most important information from the provided context, paying attention to the SOURCE of information.

Recent Events (Format: [Source] Content):
{episodes}
"""

# New hierarchical summarization prompt
HIERARCHICAL_SUMMARY_PROMPT = """
You are analyzing a collection of events and summaries. Your task is to synthesize
a comprehensive but concise overview that captures the key patterns, decisions, and insights.

Focus on:
1. Major themes and patterns
2. Critical decisions and their rationale
3. Important events and their impact
4. Relationships between concepts
5. Source reliability and consensus (if multiple sources are present)

Content to analyze:
{content}

Provide a clear, structured summary that will be useful for future reference.
"""


class ReflectionEngine:
    """
    Enterprise-grade service for generating reflective memories and knowledge graphs.

    Features:
    - Legacy triple extraction (backward compatible)
    - Advanced knowledge graph extraction with confidence scoring
    - Hierarchical (map-reduce) summarization for large episode collections
    - Integration with GraphExtractionService
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        rae_service: "RAECoreService",
        graph_repository: Optional[GraphRepository] = None,
    ):
        self.pool = pool
        self.graph_repo = graph_repository or GraphRepository(pool)
        self.rae_service = rae_service
        self.llm_provider = get_llm_provider()
        self.graph_extractor = GraphExtractionService(self.rae_service, self.graph_repo)

    async def generate_reflection(self, project: str, tenant_id: str) -> str:
        """
        Generates a new reflective memory for a given project and tenant.
        """
        # 1. Fetch recent, unprocessed episodic memories
        episodes = await self._get_recent_episodes(project, tenant_id)
        if not episodes:
            logger.info(
                "no_new_episodes_for_reflection", project=project, tenant_id=tenant_id
            )
            return "No new episodes, skipping."

        episode_lines = []
        for e in episodes:
            # Safely access provenance since it might be missing in old memories
            provenance = e.get("provenance") or {}
            source_dev = (
                provenance.get("origin_device")
                or provenance.get("rae.sync.origin")
                or e.get("source")
                or "unknown"
            )
            episode_lines.append(f"- [{source_dev}] {e['content']}")

        episode_content = "\n".join(episode_lines)

        # 2. Use LLM to synthesize a lesson
        system_prompt = "You are a helpful assistant that synthesizes insights."
        final_prompt = REFLECTION_PROMPT.format(episodes=episode_content)

        from typing import cast

        extracted_triples = cast(
            Triples,
            await self.llm_provider.generate_structured(
                system=system_prompt,
                prompt=final_prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
                response_model=Triples,
            ),
        )
        logger.info("extracted_triples", triples=extracted_triples.model_dump_json())

        # 3. Store the new reflective memory (triples)
        await self._store_triples(extracted_triples.triples, project, tenant_id)

        metrics.reflection_event_counter.labels(
            tenant_id=tenant_id, project=project
        ).inc()

        # 4. Mark the processed episodes
        # (This part is omitted for simplicity, but in a real system, you'd
        # have a 'processed_for_reflection' flag in the DB)

        logger.info(
            "reflection_generated",
            project=project,
            triples=extracted_triples.model_dump_json(),
        )
        return f"Generated reflection for project {project}: {extracted_triples.model_dump_json()}"

    async def _store_triples(self, triples: List[Triple], project: str, tenant_id: str):
        """
        Store triples in knowledge graph using repository pattern.

        Args:
            triples: List of Triple objects with source, target, relation
            project: Project identifier
            tenant_id: Tenant identifier
        """
        # Convert legacy Triple objects to repository format
        triple_dicts = [
            {
                "source": triple.source,
                "target": triple.target,
                "relation": triple.relation,
                "confidence": 1.0,  # Legacy triples have full confidence
                "metadata": {},
            }
            for triple in triples
        ]

        # Use repository's batch storage method
        stats = await self.graph_repo.store_graph_triples(
            triples=triple_dicts, tenant_id=tenant_id, project_id=project
        )

        logger.info(
            "triples_stored",
            project=project,
            tenant_id=tenant_id,
            nodes_created=stats["nodes_created"],
            edges_created=stats["edges_created"],
        )

    async def _get_recent_episodes(self, project: str, tenant_id: str) -> List[Dict]:
        """
        Fetches episodic memories for a project that haven't been used for reflection yet.
        """
        # Using RAECoreService list_memories
        return await self.rae_service.list_memories(
            tenant_id=tenant_id, layer="episodic", project=project, limit=10
        )

    async def extract_knowledge_graph_enhanced(
        self,
        project: str,
        tenant_id: str,
        limit: int = 50,
        min_confidence: float = 0.5,
        auto_store: bool = True,
    ) -> GraphExtractionResult:
        """
        Enhanced knowledge graph extraction using the GraphExtractionService.

        This method provides enterprise-grade extraction with:
        - Confidence scoring
        - Rich metadata
        - Automatic storage to database
        - Comprehensive statistics

        Args:
            project: Project identifier
            tenant_id: Tenant identifier
            limit: Maximum number of memories to process
            min_confidence: Minimum confidence threshold for triples
            auto_store: Automatically store triples in database (default: True)

        Returns:
            GraphExtractionResult with triples, entities, and statistics
        """
        logger.info(
            "enhanced_graph_extraction_started",
            project=project,
            tenant_id=tenant_id,
            limit=limit,
        )

        # Use the dedicated graph extraction service
        extraction_result = await self.graph_extractor.extract_knowledge_graph(
            project_id=project,
            tenant_id=tenant_id,
            limit=limit,
            min_confidence=min_confidence,
        )

        # Optionally store triples in database
        if auto_store and extraction_result.triples:
            storage_stats = await self.graph_extractor.store_graph_triples(
                triples=extraction_result.triples,
                project_id=project,
                tenant_id=tenant_id,
            )

            # Update statistics with storage results
            extraction_result.statistics.update(storage_stats)

            logger.info(
                "enhanced_graph_extraction_completed",
                project=project,
                statistics=extraction_result.statistics,
            )

        return extraction_result

    async def generate_hierarchical_reflection(
        self,
        project: str,
        tenant_id: str,
        bucket_size: int = 10,
        max_episodes: Optional[int] = None,
    ) -> str:
        """
        Generate hierarchical (Map-Reduce) summarization of episodes.

        This method handles large numbers of episodes by recursively summarizing them:
        1. Split episodes into buckets
        2. Summarize each bucket (Map phase)
        3. Recursively summarize the summaries (Reduce phase)

        This approach scales to handle thousands of episodes without hitting
        context window limits.

        Args:
            project: Project identifier
            tenant_id: Tenant identifier
            bucket_size: Number of episodes per bucket (default: 10)
            max_episodes: Maximum episodes to process (default: None = all)

        Returns:
            Final synthesized reflection summary
        """
        logger.info(
            "hierarchical_reflection_started",
            project=project,
            tenant_id=tenant_id,
            bucket_size=bucket_size,
        )

        # 1. Fetch all episodes
        episodes = await self._fetch_all_episodes(
            project=project, tenant_id=tenant_id, limit=max_episodes
        )

        if not episodes:
            logger.info("no_episodes_for_hierarchical_reflection", project=project)
            return "No episodes available for reflection."

        logger.info(
            "fetched_episodes_for_hierarchical", count=len(episodes), project=project
        )

        # 2. If small enough, summarize directly
        if len(episodes) <= bucket_size:
            return await self._summarize_episodes(episodes)

        # 3. Split into buckets and process hierarchically
        buckets = [
            episodes[i : i + bucket_size] for i in range(0, len(episodes), bucket_size)
        ]

        logger.info(
            "processing_hierarchical_buckets",
            bucket_count=len(buckets),
            bucket_size=bucket_size,
        )

        # 4. Map phase: Summarize each bucket
        summaries = []
        for i, bucket in enumerate(buckets):
            logger.info(f"summarizing_bucket_{i + 1}/{len(buckets)}")
            summary = await self._summarize_episodes(bucket)
            summaries.append(summary)

        # 5. Reduce phase: Recursively summarize summaries
        final_summary = await self._recursive_reduce(summaries, bucket_size)

        logger.info(
            "hierarchical_reflection_completed",
            project=project,
            final_length=len(final_summary),
        )

        return final_summary

    async def _fetch_all_episodes(
        self, project: str, tenant_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all episodic memories for hierarchical processing.

        Args:
            project: Project identifier
            tenant_id: Tenant identifier
            limit: Optional limit on episodes to fetch

        Returns:
            List of episode dictionaries
        """
        return await self.rae_service.list_memories(
            tenant_id=tenant_id,
            layer="episodic",
            project=project,
            limit=limit
            or 1000,  # Set a high default limit if not specified, as list_memories requires limit
        )

    async def _summarize_episodes(self, episodes: List[Dict[str, Any]]) -> str:
        """
        Summarize a small batch of episodes.

        Args:
            episodes: List of episode dictionaries

        Returns:
            Summarized text
        """
        episode_lines = []
        for ep in episodes:
            provenance = ep.get("provenance") or {}
            source_dev = (
                provenance.get("origin_device")
                or provenance.get("rae.sync.origin")
                or ep.get("source")
                or "unknown"
            )
            episode_lines.append(
                f"- [{ep.get('created_at', 'unknown')}] [{source_dev}] {ep.get('content', '')}"
            )

        formatted_episodes = "\n".join(episode_lines)

        prompt = HIERARCHICAL_SUMMARY_PROMPT.format(content=formatted_episodes)

        result = await self.llm_provider.generate(
            system="You are a helpful assistant that synthesizes insights.",
            prompt=prompt,
            model=settings.RAE_LLM_MODEL_DEFAULT,
        )

        return result.text

    async def _summarize_summaries(self, summaries: List[str]) -> str:
        """
        Summarize a collection of summaries (meta-summarization).

        Args:
            summaries: List of summary texts

        Returns:
            Meta-summary text
        """
        formatted_summaries = "\n\n---\n\n".join(
            [f"Summary {i + 1}:\n{summary}" for i, summary in enumerate(summaries)]
        )

        prompt = HIERARCHICAL_SUMMARY_PROMPT.format(content=formatted_summaries)

        result = await self.llm_provider.generate(
            system="You are a helpful assistant that synthesizes insights.",
            prompt=prompt,
            model=settings.RAE_LLM_MODEL_DEFAULT,
        )

        return result.text

    async def _recursive_reduce(self, summaries: List[str], bucket_size: int) -> str:
        """
        Recursively reduce summaries until we have a single final summary.

        Args:
            summaries: List of summaries to reduce
            bucket_size: Size of each reduction bucket

        Returns:
            Final reduced summary
        """
        if len(summaries) <= bucket_size:
            # Base case: small enough to summarize directly
            return await self._summarize_summaries(summaries)

        # Recursive case: split and reduce further
        buckets = [
            summaries[i : i + bucket_size]
            for i in range(0, len(summaries), bucket_size)
        ]

        meta_summaries = []
        for bucket in buckets:
            meta_summary = await self._summarize_summaries(bucket)
            meta_summaries.append(meta_summary)

        # Recurse
        return await self._recursive_reduce(meta_summaries, bucket_size)
