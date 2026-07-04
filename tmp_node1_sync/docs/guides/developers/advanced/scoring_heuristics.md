# Scoring & Heuristics

The RAE Memory Engine goes beyond simple semantic similarity to retrieve the most relevant and useful memories. It employs a sophisticated **Scoring & Heuristics module** that combines multiple factors to rank memories.

## Scoring Factors

When a query is made to RAE, the retrieved memories are re-scored based on the following factors:

1.  **Semantic Relevance**: The initial score provided by the vector database (e.g., Qdrant), indicating how semantically similar the memory content is to the query.
2.  **Recency Score**: Memories that have been created or accessed more recently receive a higher score. This is calculated using an exponential decay function, giving more weight to fresher information.
3.  **Usage Frequency Score**: Memories that have been accessed more frequently by agents are considered more valuable and receive a higher score. This is based on the `usage_count` field.
4.  **Importance Score**: Each memory can have an explicit `importance` score (0.0 to 1.0), which can be set manually or by an LLM during reflection. This allows critical information to be prioritized.

## Final Score Calculation

These individual scores are combined using a weighted sum to produce a final ranking score. The weights are currently configurable within the `scoring.py` service.

```python
# Example weights (configurable)
weights = {
    "semantic": 0.6,
    "recency": 0.1,
    "importance": 0.2,
    "usage": 0.1,
}

final_score = (
    semantic_score * weights["semantic"] +
    recency_score * weights["recency"] +
    importance_score * weights["importance"] +
    usage_score * weights["usage"]
)
```

## Deduplication

To maintain a clean and efficient memory, RAE includes a simple **deduplication mechanism**. When a new memory is about to be stored via the `/memory/store` endpoint, the system performs a quick similarity search. If a highly similar memory (above a configurable threshold, e.g., 0.95 semantic similarity) already exists, the new memory is not stored, and the ID of the existing memory is returned. This prevents the memory from being cluttered with redundant information.

## Benefits

*   **Higher Quality Retrieval**: Agents receive more relevant and timely information.
*   **Dynamic Context**: Memory adapts to recent events and frequently accessed knowledge.
*   **Reduced Redundancy**: Deduplication keeps the memory concise and efficient.
*   **Configurable Behavior**: Weights can be tuned to prioritize different aspects of memory.
