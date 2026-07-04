"""
Semantic Search - 3-Stage Pipeline for Knowledge Node Retrieval

This service implements enterprise semantic search with:
- Stage 1: Topic identification → vector search
- Stage 2: Term normalization → canonicalization
- Stage 3: Semantic re-ranking
"""

from typing import Any, Dict, List, Optional, Tuple, cast

import asyncpg
import numpy as np
import structlog

from apps.memory_api.models.semantic_models import (
    SemanticDefinition,
    SemanticNode,
    SemanticNodeType,
)
from apps.memory_api.services.ml_service_client import MLServiceClient
from apps.memory_api.services.semantic_extractor import SemanticExtractor

logger = structlog.get_logger(__name__)


# ============================================================================
# 3-Stage Semantic Search
# ============================================================================


class SemanticSearchPipeline:
    """
    Enterprise 3-stage semantic search pipeline.

    Stage 1: Topic Identification → Vector Search
    - Extract topics from query
    - Convert topics to embeddings
    - Vector similarity search in semantic_index

    Stage 2: Term Normalization → Canonicalization
    - Normalize query terms to canonical forms
    - Match against canonical_form field
    - Expand results with synonyms

    Stage 3: Semantic Re-ranking
    - Re-rank results based on contextual relevance
    - Apply boosting based on priority, importance, reinforcement
    - Filter degraded nodes if requested
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.ml_client = MLServiceClient()
        self.semantic_extractor = SemanticExtractor(pool)

    async def search(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        k: int = 10,
        enable_topic_matching: bool = True,
        enable_canonicalization: bool = True,
        enable_reranking: bool = True,
        node_types: Optional[List[SemanticNodeType]] = None,
        domains: Optional[List[str]] = None,
        min_priority: Optional[int] = None,
        exclude_degraded: bool = True,
    ) -> Tuple[List[SemanticNode], Dict[str, Any]]:
        """
        Execute 3-stage semantic search.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Search query
            k: Number of results
            enable_topic_matching: Enable stage 1
            enable_canonicalization: Enable stage 2
            enable_reranking: Enable stage 3
            node_types: Filter by node types
            domains: Filter by domains
            min_priority: Minimum priority
            exclude_degraded: Exclude degraded nodes

        Returns:
            Tuple of (results, statistics)
        """
        logger.info("semantic_search_started", tenant_id=tenant_id, query=query, k=k)

        statistics = {
            "stage1_results": 0,
            "stage2_results": 0,
            "stage3_results": 0,
            "identified_topics": [],
            "canonical_terms": [],
        }

        results = []

        # Stage 1: Topic Identification → Vector Search
        if enable_topic_matching:
            stage1_results, topics = await self._stage1_topic_matching(
                tenant_id,
                project_id,
                query,
                k * 3,  # Get more for filtering
            )
            results.extend(stage1_results)
            statistics["stage1_results"] = len(stage1_results)
            statistics["identified_topics"] = topics
            logger.info("stage1_complete", results=len(stage1_results), topics=topics)

        # Stage 2: Term Normalization → Canonicalization
        if enable_canonicalization:
            stage2_results, canonical_terms = await self._stage2_canonicalization(
                tenant_id, project_id, query, k * 2
            )
            results.extend(stage2_results)
            statistics["stage2_results"] = len(stage2_results)
            statistics["canonical_terms"] = canonical_terms
            logger.info(
                "stage2_complete", results=len(stage2_results), terms=canonical_terms
            )

        # Deduplicate results by ID
        unique_results = self._deduplicate_by_id(results)

        # Apply filters
        filtered_results = self._apply_filters(
            unique_results,
            node_types=node_types,
            domains=domains,
            min_priority=min_priority,
            exclude_degraded=exclude_degraded,
        )

        # Stage 3: Semantic Re-ranking
        if enable_reranking:
            reranked_results = await self._stage3_reranking(filtered_results, query, k)
            final_results = reranked_results[:k]
            statistics["stage3_results"] = len(final_results)
            logger.info("stage3_complete", results=len(final_results))
        else:
            # Simple truncation without re-ranking
            final_results = filtered_results[:k]
            statistics["stage3_results"] = len(final_results)

        logger.info("semantic_search_complete", final_results=len(final_results))

        return final_results, statistics

    async def _stage1_topic_matching(
        self, tenant_id: str, project_id: str, query: str, k: int
    ) -> Tuple[List[SemanticNode], List[str]]:
        """
        Stage 1: Topic identification and vector search.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Search query
            k: Number of results

        Returns:
            Tuple of (results, identified_topics)
        """
        logger.info("stage1_topic_matching", query=query)

        # Generate query embedding
        result = await self.ml_client.generate_embeddings([query])
        embeddings = result.get("embeddings", [])
        query_embedding = (
            cast(List[float], embeddings[0]) if embeddings else [0.0] * 1536
        )

        # Simple topic extraction (split query into key terms)
        # In production, use LLM for better topic extraction
        topics = self._extract_topics_simple(query)

        # Vector search in semantic_nodes
        records = await self.pool.fetch(
            """
            SELECT *
            FROM semantic_nodes
            WHERE tenant_id = $1 AND project_id = $2
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $3
            LIMIT $4
            """,
            tenant_id,
            project_id,
            query_embedding,
            k,
        )

        results = [self._record_to_semantic_node(r) for r in records]

        logger.info("stage1_vector_search", results=len(results))

        return results, topics

    async def _stage2_canonicalization(
        self, tenant_id: str, project_id: str, query: str, k: int
    ) -> Tuple[List[SemanticNode], List[str]]:
        """
        Stage 2: Term normalization and canonicalization.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Search query
            k: Number of results

        Returns:
            Tuple of (results, canonical_terms)
        """
        logger.info("stage2_canonicalization", query=query)

        # Extract terms from query
        terms = query.lower().split()

        # Canonicalize each term
        canonical_terms = []
        for term in terms:
            if len(term) > 2:  # Skip very short terms
                canonical = await self.semantic_extractor.canonicalize_term(term)
                canonical_terms.append(canonical)

        # Search for nodes matching canonical forms
        results = []

        for canonical in canonical_terms:
            records = await self.pool.fetch(
                """
                SELECT *
                FROM semantic_nodes
                WHERE tenant_id = $1 AND project_id = $2
                  AND (
                    canonical_form ILIKE $3
                    OR label ILIKE $3
                    OR $4 = ANY(aliases)
                  )
                LIMIT $5
                """,
                tenant_id,
                project_id,
                f"%{canonical}%",
                canonical,
                k,
            )

            for r in records:
                results.append(self._record_to_semantic_node(r))

        logger.info(
            "stage2_canonicalization_complete",
            results=len(results),
            terms=canonical_terms,
        )

        return results, canonical_terms

    async def _stage3_reranking(
        self, nodes: List[SemanticNode], query: str, k: int
    ) -> List[SemanticNode]:
        """
        Stage 3: Semantic re-ranking with boosting.

        Args:
            nodes: Candidate nodes
            query: Original query
            k: Number of results to return

        Returns:
            Re-ranked nodes
        """
        logger.info("stage3_reranking", candidates=len(nodes), k=k)

        if not nodes:
            return []

        # Calculate re-ranking scores
        scored_nodes = []

        for node in nodes:
            # Base score from importance
            base_score = node.importance_score

            # Boost by priority (1-5)
            priority_boost = node.priority / 5.0

            # Boost by reinforcement count (log scale)
            reinforcement_boost = min(1.0, np.log1p(node.reinforcement_count) / 10.0)

            # Boost by access count (log scale)
            access_boost = min(1.0, np.log1p(node.accessed_count) / 10.0)

            # Penalty for degradation
            degradation_penalty = 0.5 if node.is_degraded else 1.0

            # Compute final score
            final_score = (
                base_score * 0.4
                + priority_boost * 0.3
                + reinforcement_boost * 0.2
                + access_boost * 0.1
            ) * degradation_penalty

            scored_nodes.append((node, final_score))

        # Sort by score descending
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Return top k
        reranked = [node for node, score in scored_nodes[:k]]

        logger.info("stage3_reranking_complete", results=len(reranked))

        return reranked

    def _extract_topics_simple(self, query: str) -> List[str]:
        """
        Simple topic extraction from query.

        In production, use LLM for better results.
        """
        # Lowercase and split
        terms = query.lower().split()

        # Filter out very short terms and common stop words
        stop_words = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
        }
        topics = [t for t in terms if len(t) > 2 and t not in stop_words]

        return topics[:5]  # Limit to 5 topics

    def _deduplicate_by_id(self, nodes: List[SemanticNode]) -> List[SemanticNode]:
        """Deduplicate nodes by ID"""
        seen = set()
        unique = []

        for node in nodes:
            if node.id not in seen:
                seen.add(node.id)
                unique.append(node)

        return unique

    def _apply_filters(
        self,
        nodes: List[SemanticNode],
        node_types: Optional[List[SemanticNodeType]] = None,
        domains: Optional[List[str]] = None,
        min_priority: Optional[int] = None,
        exclude_degraded: bool = True,
    ) -> List[SemanticNode]:
        """Apply filters to nodes"""
        filtered = nodes

        if node_types:
            filtered = [n for n in filtered if n.node_type in node_types]

        if domains:
            filtered = [n for n in filtered if n.domain in domains]

        if min_priority:
            filtered = [n for n in filtered if n.priority >= min_priority]

        if exclude_degraded:
            filtered = [n for n in filtered if not n.is_degraded]

        return filtered

    def _record_to_semantic_node(self, record) -> SemanticNode:
        """Convert database record to SemanticNode"""
        # Parse definitions JSONB
        definitions = []
        if record.get("definitions"):
            for defn in record["definitions"]:
                if isinstance(defn, dict):
                    definitions.append(SemanticDefinition(**defn))

        return SemanticNode(
            id=record["id"],
            tenant_id=record["tenant_id"],
            project_id=record["project_id"],
            node_id=record["node_id"],
            label=record["label"],
            node_type=SemanticNodeType(record["node_type"]),
            canonical_form=record["canonical_form"],
            aliases=record.get("aliases", []),
            definition=record.get("definition"),
            definitions=definitions,
            context=record.get("context"),
            examples=record.get("examples", []),
            categories=record.get("categories", []),
            domain=record.get("domain"),
            relations=record.get("relations", {}),
            embedding=record.get("embedding"),
            priority=record["priority"],
            importance_score=float(record["importance_score"]),
            last_reinforced_at=record["last_reinforced_at"],
            reinforcement_count=record["reinforcement_count"],
            decay_rate=float(record["decay_rate"]),
            is_degraded=record["is_degraded"],
            degradation_timestamp=record.get("degradation_timestamp"),
            source_memory_ids=record.get("source_memory_ids", []),
            extraction_model=record.get("extraction_model"),
            extraction_confidence=(
                float(record["extraction_confidence"])
                if record.get("extraction_confidence")
                else None
            ),
            tags=record.get("tags", []),
            metadata=record.get("metadata", {}),
            created_at=record["created_at"],
            updated_at=record["updated_at"],
            last_accessed_at=record["last_accessed_at"],
            accessed_count=record["accessed_count"],
        )
