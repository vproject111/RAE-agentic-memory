<!-- RAE_DOC_FRAGMENT:hybrid_search_core -->
# Hybrid Search System

RAE combines **4 complementary search strategies**:

1. **Vector Search** - Dense embeddings for semantic similarity
2. **Graph Traversal** - GraphRAG for discovering connected concepts
3. **Sparse Vectors** - BM25-style keyword matching
4. **Full-Text Search** - PostgreSQL FTS for exact phrases

All strategies execute in parallel, with results intelligently fused using query-specific weights determined by LLM-powered query analysis.

**See**: [Complete Hybrid Search Documentation](../../architecture/HYBRID_SEARCH.md)
<!-- END_RAE_DOC_FRAGMENT:hybrid_search_core -->
