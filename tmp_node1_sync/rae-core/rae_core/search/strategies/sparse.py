"""Sparse vector search strategy (BM25, TF-IDF)."""

import math
from collections import Counter
from typing import Any
from uuid import UUID

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.search.strategies import SearchStrategy


class SparseVectorStrategy(SearchStrategy):
    """Sparse vector search using BM25 algorithm.

    Implements BM25 ranking for keyword-based relevance scoring.
    BM25 is superior to TF-IDF for information retrieval.
    """

    def __init__(
        self,
        memory_storage: IMemoryStorage,
        default_weight: float = 0.2,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """Initialize sparse vector strategy.

        Args:
            memory_storage: Memory storage for content retrieval
            default_weight: Default weight in hybrid search (0.0-1.0)
            k1: BM25 term frequency saturation parameter (typically 1.2-2.0)
            b: BM25 length normalization parameter (typically 0.75)
        """
        self.memory_storage = memory_storage
        self.default_weight = default_weight
        self.k1 = k1
        self.b = b

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization (split on whitespace and lowercase)."""
        return text.lower().split()

    def _compute_bm25_score(
        self,
        query_terms: list[str],
        doc_terms: list[str],
        avg_doc_length: float,
        doc_count: int,
        term_doc_freq: dict[str, int],
    ) -> float:
        """Compute BM25 score for a document.

        Args:
            query_terms: Query tokens
            doc_terms: Document tokens
            avg_doc_length: Average document length in corpus
            doc_count: Total number of documents
            term_doc_freq: Number of documents containing each term

        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = len(doc_terms)
        doc_term_freq = Counter(doc_terms)

        for term in query_terms:
            if term not in doc_term_freq:
                continue

            # Term frequency in document
            tf = doc_term_freq[term]

            # Inverse document frequency
            df = term_doc_freq.get(term, 1)
            idf = math.log((doc_count - df + 0.5) / (df + 0.5) + 1.0)

            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (
                1 - self.b + self.b * (doc_length / avg_doc_length)
            )

            score += idf * (numerator / denominator)

        return score

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[tuple[UUID, float]]:
        """Execute BM25 search.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            filters: Optional filters (layer, agent_id, etc.)
            limit: Maximum number of results

        Returns:
            List of (memory_id, bm25_score) tuples
        """
        # Extract filters
        layer = filters.get("layer") if filters else None
        agent_id = filters.get("agent_id") if filters else None

        # Retrieve memories for scoring
        memories = await self.memory_storage.list_memories(
            tenant_id=tenant_id,
            agent_id=agent_id,
            layer=layer,
            limit=1000,  # Fetch more for BM25 corpus
        )

        if not memories:
            return []

        # Tokenize query
        query_terms = self._tokenize(query)

        # Build corpus statistics and prepare memories for scoring
        doc_count = len(memories)
        total_doc_length = 0
        term_doc_freq: dict[str, int] = {}
        processed_memories: list[tuple[UUID, list[str]]] = []

        for memory in memories:
            memory_id = memory["id"]
            if isinstance(memory_id, str):
                memory_id = UUID(memory_id)

            content = memory.get("content", "")
            doc_terms = self._tokenize(content)
            processed_memories.append((memory_id, doc_terms))
            total_doc_length += len(doc_terms)

            # Count document frequency for each term
            unique_terms = set(doc_terms)
            for term in unique_terms:
                term_doc_freq[term] = term_doc_freq.get(term, 0) + 1

        avg_doc_length = total_doc_length / doc_count

        # Score each document
        results: list[tuple[UUID, float]] = []
        for memory_id, doc_terms in processed_memories:
            score = self._compute_bm25_score(
                query_terms,
                doc_terms,
                avg_doc_length,
                doc_count,
                term_doc_freq,
            )

            if score > 0:
                results.append((memory_id, score))

        # Sort by score descending and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "sparse"

    def get_strategy_weight(self) -> float:
        """Return default weight for hybrid fusion."""
        return self.default_weight
