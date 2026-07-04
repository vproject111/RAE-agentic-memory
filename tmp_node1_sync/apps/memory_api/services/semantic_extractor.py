"""
Semantic Extractor - LLM Pipeline for Knowledge Node Extraction

This service extracts semantic knowledge from memories:
- Topics and concepts
- Canonical terms and definitions
- Semantic relationships
- Ontological categorization
- Automatic embedding generation
"""

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import structlog

from apps.memory_api.config import settings
from apps.memory_api.models.semantic_models import (
    SemanticExtractionResult,
    SemanticNodeType,
    SemanticRelationType,
)
from apps.memory_api.services.llm import get_llm_provider
from apps.memory_api.services.ml_service_client import MLServiceClient
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


# ============================================================================
# Prompts
# ============================================================================

SEMANTIC_EXTRACTION_PROMPT = """
You are a semantic knowledge extractor. Analyze the following memories and extract structured semantic knowledge.

Memories:
{memories}

Your task:
1. Extract key TOPICS and CONCEPTS
2. Identify TERMS that need canonical forms (e.g., "auth" → "authentication")
3. Extract RELATIONSHIPS between concepts
4. Identify CATEGORIES and DOMAIN

For each topic:
- Provide the exact topic string
- Assign confidence 0.0-1.0

For each term:
- Original form (as appears in text)
- Canonical form (standardized)
- Definition if clear
- Confidence 0.0-1.0

For each relationship:
- Source concept
- Relationship type (is_a, part_of, related_to, causes, requires, uses)
- Target concept
- Confidence 0.0-1.0

Return as structured JSON matching this schema:
{{
  "topics": [
    {{"topic": "authentication", "normalized_topic": "authentication", "confidence": 0.9}}
  ],
  "terms": [
    {{"original": "auth", "canonical": "authentication", "definition": "...", "confidence": 0.8}}
  ],
  "relations": [
    {{"source": "authentication", "relation": "requires", "target": "credentials", "confidence": 0.9}}
  ],
  "categories": ["security", "architecture"],
  "domain": "security"
}}
"""

CANONICALIZATION_PROMPT = """
Given the term: "{term}"

Provide the canonical (standardized, formal) form of this term.
If it's already canonical, return it unchanged.

Examples:
- "auth" → "authentication"
- "db" → "database"
- "API" → "Application Programming Interface"
- "user mgmt" → "user management"

Return ONLY the canonical form, nothing else.
"""


# ============================================================================
# Semantic Extractor
# ============================================================================


class SemanticExtractor:
    """
    Enterprise semantic knowledge extraction pipeline.

    Features:
    - LLM-based topic and term extraction
    - Automatic canonicalization
    - Relationship identification
    - Embedding generation
    - Database storage with deduplication
    """

    def __init__(self, rae_service: RAECoreService):
        self.rae_service = rae_service
        self.llm_provider = get_llm_provider()
        self.ml_client = MLServiceClient()

    async def extract_from_memories(
        self,
        tenant_id: str,
        project_id: str,
        memory_ids: Optional[List[UUID]] = None,
        max_memories: int = 100,
        min_confidence: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Extract semantic nodes from memories.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            memory_ids: Optional specific memory IDs
            max_memories: Maximum memories to process
            min_confidence: Minimum extraction confidence

        Returns:
            Dictionary with extraction statistics
        """
        logger.info(
            "semantic_extraction_started",
            tenant_id=tenant_id,
            project_id=project_id,
            max_memories=max_memories,
        )

        # Fetch memories
        memories = await self._fetch_memories(
            tenant_id, project_id, memory_ids, max_memories
        )

        if not memories:
            logger.info("no_memories_for_extraction")
            return {
                "nodes_extracted": 0,
                "relationships_created": 0,
                "memories_processed": 0,
            }

        logger.info("memories_fetched", count=len(memories))

        # Extract semantic knowledge
        extraction = await self._extract_semantic_knowledge(memories)

        # Process topics into semantic nodes
        nodes_created = 0
        relationships_created = 0

        for topic in extraction.topics:
            if topic.confidence >= min_confidence:
                try:
                    await self._create_or_update_semantic_node(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        topic=topic.topic,
                        normalized_topic=topic.normalized_topic,
                        node_type=SemanticNodeType.TOPIC,
                        confidence=topic.confidence,
                        source_memory_ids=[UUID(str(m["id"])) for m in memories],
                        domain=extraction.domain,
                        categories=extraction.categories,
                    )
                    nodes_created += 1
                except Exception as e:
                    logger.error(
                        "topic_creation_failed", topic=topic.topic, error=str(e)
                    )

        # Process terms
        for term in extraction.terms:
            if term.confidence >= min_confidence:
                try:
                    await self._create_or_update_semantic_node(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        topic=term.original,
                        normalized_topic=term.canonical,
                        node_type=SemanticNodeType.TERM,
                        confidence=term.confidence,
                        source_memory_ids=[UUID(str(m["id"])) for m in memories],
                        domain=extraction.domain,
                        categories=extraction.categories,
                        definition=term.definition,
                    )
                    nodes_created += 1
                except Exception as e:
                    logger.error(
                        "term_creation_failed", term=term.original, error=str(e)
                    )

        # Process relationships
        for relation in extraction.relations:
            if relation.confidence >= min_confidence:
                try:
                    created = await self._create_semantic_relationship(
                        tenant_id=tenant_id,
                        project_id=project_id,
                        source=relation.source,
                        relation_type=relation.relation,
                        target=relation.target,
                        confidence=relation.confidence,
                    )
                    if created:
                        relationships_created += 1
                except Exception as e:
                    logger.error("relationship_creation_failed", error=str(e))

        statistics = {
            "nodes_extracted": nodes_created,
            "relationships_created": relationships_created,
            "memories_processed": len(memories),
            "topics_found": len(extraction.topics),
            "terms_found": len(extraction.terms),
            "relations_found": len(extraction.relations),
            "domain": extraction.domain,
            "categories": extraction.categories,
        }

        logger.info("semantic_extraction_complete", statistics=statistics)

        return statistics

    async def canonicalize_term(self, term: str) -> str:
        """
        Canonicalize a term using LLM.

        Args:
            term: Original term

        Returns:
            Canonical form
        """
        try:
            prompt = CANONICALIZATION_PROMPT.format(term=term)

            result = await self.llm_provider.generate(
                system="You are a terminology standardization expert.",
                prompt=prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
            )

            canonical = result.text.strip()
            logger.info("term_canonicalized", original=term, canonical=canonical)

            return canonical

        except Exception as e:
            logger.error("canonicalization_failed", term=term, error=str(e))
            # Fallback: return lowercase trimmed version
            return term.lower().strip()

    async def _fetch_memories(
        self,
        tenant_id: str,
        project_id: str,
        memory_ids: Optional[List[UUID]],
        max_memories: int,
    ) -> List[Dict[str, Any]]:
        """Fetch memories for extraction"""
        query_filters = {}
        if memory_ids:
            query_filters["memory_ids"] = memory_ids

        return await self.rae_service.list_memories(
            tenant_id=tenant_id,
            project=project_id,
            filters=query_filters,
            limit=max_memories,
        )

    async def _extract_semantic_knowledge(
        self, memories: List[Dict[str, Any]]
    ) -> SemanticExtractionResult:
        """
        Extract semantic knowledge using LLM.

        Args:
            memories: List of memory dictionaries

        Returns:
            Structured extraction result
        """
        logger.info("extracting_semantic_knowledge", memories=len(memories))

        # Format memories for prompt
        memory_texts = [
            f"- [{m.get('created_at', 'unknown')}] {m.get('content', '')}"
            for m in memories[:20]  # Limit to 20 for context window
        ]
        memories_formatted = "\n".join(memory_texts)

        prompt = SEMANTIC_EXTRACTION_PROMPT.format(memories=memories_formatted)

        try:
            result = await self.llm_provider.generate_structured(
                system="You are a semantic knowledge extraction expert.",
                prompt=prompt,
                model=settings.RAE_LLM_MODEL_DEFAULT,
                response_model=SemanticExtractionResult,
            )

            result = cast(SemanticExtractionResult, result)

            logger.info(
                "semantic_extraction_llm_complete",
                topics=len(result.topics),
                terms=len(result.terms),
                relations=len(result.relations),
            )

            return result

        except Exception as e:
            logger.error("semantic_extraction_llm_failed", error=str(e))
            # Return empty result on failure
            return SemanticExtractionResult()

    async def _create_or_update_semantic_node(
        self,
        tenant_id: str,
        project_id: str,
        topic: str,
        normalized_topic: str,
        node_type: SemanticNodeType,
        confidence: float,
        source_memory_ids: List[UUID],
        domain: Optional[str] = None,
        categories: Optional[List[str]] = None,
        definition: Optional[str] = None,
    ) -> Optional[UUID]:
        """Create or update a semantic node"""
        categories = categories or []

        # Generate node_id from normalized topic
        node_id = normalized_topic.replace(" ", "_").lower()

        # Check if node exists
        existing = await self.rae_service.db.fetchrow(
            """
            SELECT id, reinforcement_count, source_memory_ids
            FROM semantic_nodes
            WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3
            """,
            tenant_id,
            project_id,
            node_id,
        )

        if existing:
            # Update existing node (reinforce it)
            updated_memory_ids = list(
                set(existing["source_memory_ids"] + source_memory_ids)
            )

            await self.rae_service.db.execute(
                """
                SELECT reinforce_semantic_node($1)
                """,
                existing["id"],
            )

            # Update source memory IDs
            await self.rae_service.db.execute(
                """
                UPDATE semantic_nodes
                SET source_memory_ids = $1
                WHERE id = $2
                """,
                updated_memory_ids,
                existing["id"],
            )

            logger.info("semantic_node_reinforced", node_id=node_id)
            return cast(UUID, existing["id"])

        else:
            # Create new node
            # Generate embedding
            embedding = await self._generate_embedding(normalized_topic)

            record = await self.rae_service.db.fetchrow(
                """
                INSERT INTO semantic_nodes (
                    tenant_id, project_id, node_id, label, node_type,
                    canonical_form, definition, domain, categories,
                    embedding, extraction_confidence, source_memory_ids
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
                """,
                tenant_id,
                project_id,
                node_id,
                topic,
                node_type.value,
                normalized_topic,
                definition,
                domain,
                categories,
                embedding,
                confidence,
                source_memory_ids,
            )

            logger.info("semantic_node_created", node_id=node_id)
            if not record:
                return None
            return cast(UUID, record["id"])

    async def _create_semantic_relationship(
        self,
        tenant_id: str,
        project_id: str,
        source: str,
        relation_type: str,
        target: str,
        confidence: float,
    ) -> bool:
        """Create a semantic relationship between nodes"""
        # Normalize node IDs
        source_node_id = source.replace(" ", "_").lower()
        target_node_id = target.replace(" ", "_").lower()

        # Map relation string to enum
        relation_type_enum = self._map_relation_type(relation_type)
        if not relation_type_enum:
            return False

        # Get node UUIDs
        source_uuid = await self.rae_service.db.fetchval(
            "SELECT id FROM semantic_nodes WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3",
            tenant_id,
            project_id,
            source_node_id,
        )

        target_uuid = await self.rae_service.db.fetchval(
            "SELECT id FROM semantic_nodes WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3",
            tenant_id,
            project_id,
            target_node_id,
        )

        if not source_uuid or not target_uuid:
            logger.warning(
                "relationship_nodes_not_found",
                source=source_node_id,
                target=target_node_id,
            )
            return False

        # Insert relationship (ignore if exists)
        try:
            await self.rae_service.db.execute(
                """
                INSERT INTO semantic_relationships (
                    tenant_id, project_id,
                    source_node_id, target_node_id,
                    relation_type, confidence
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT DO NOTHING
                """,
                tenant_id,
                project_id,
                source_uuid,
                target_uuid,
                relation_type_enum.value,
                confidence,
            )

            logger.info(
                "semantic_relationship_created",
                source=source,
                relation=relation_type,
                target=target,
            )
            return True

        except Exception as e:
            logger.error("relationship_creation_failed", error=str(e))
            return False

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for semantic node"""
        try:
            result = await self.ml_client.generate_embeddings([text])
            embeddings = result.get("embeddings", [])
            if embeddings:
                return cast(List[float], embeddings[0])
            return [0.0] * 1536
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return [0.0] * 1536

    def _map_relation_type(self, relation_str: str) -> Optional[SemanticRelationType]:
        """Map string relation to enum"""
        mapping = {
            "is_a": SemanticRelationType.IS_A,
            "part_of": SemanticRelationType.PART_OF,
            "related_to": SemanticRelationType.RELATED_TO,
            "synonym_of": SemanticRelationType.SYNONYM_OF,
            "causes": SemanticRelationType.CAUSES,
            "requires": SemanticRelationType.REQUIRES,
            "uses": SemanticRelationType.USES,
            "similar_to": SemanticRelationType.SIMILAR_TO,
            "implements": SemanticRelationType.IMPLEMENTS,
            "derives_from": SemanticRelationType.DERIVES_FROM,
        }

        return mapping.get(relation_str.lower())
