# Evaluation Service - Search Quality Metrics

## Overview

The Evaluation Service provides industry-standard Information Retrieval (IR) metrics to measure and monitor search quality in RAE. It implements standard metrics used in academic research and production search systems.

## Supported Metrics

### 1. MRR (Mean Reciprocal Rank)

**Formula**: `MRR = (1/|Q|) * Σ(1/rank_i)`

**Purpose**: Measures how quickly users find a relevant result.

**Best For**:
- Question-answering systems
- Single-result queries
- "Find the one correct answer" scenarios

**Example**:
```
Query 1: First relevant result at rank 3 → RR = 1/3 = 0.333
Query 2: First relevant result at rank 1 → RR = 1/1 = 1.000
Query 3: No relevant result → RR = 0.000

MRR = (0.333 + 1.000 + 0.000) / 3 = 0.444
```

### 2. NDCG (Normalized Discounted Cumulative Gain)

**Formula**:
- `DCG@K = Σ(rel_i / log2(i+1))` for i=1 to K
- `NDCG@K = DCG@K / IDCG@K`

**Purpose**: Measures ranking quality with graded relevance.

**Best For**:
- Ranked result lists
- Graded relevance (0-1 scale or 0-5 stars)
- Position-aware evaluation

**Example**:
```
Results: [rel=1.0, rel=0.5, rel=0.0, rel=0.8]
DCG@4 = 1.0/log2(2) + 0.5/log2(3) + 0.0/log2(4) + 0.8/log2(5)
      = 1.0 + 0.315 + 0.0 + 0.344 = 1.659

Ideal: [1.0, 0.8, 0.5, 0.0]
IDCG@4 = 1.0 + 0.504 + 0.315 + 0.0 = 1.819

NDCG@4 = 1.659 / 1.819 = 0.912
```

### 3. Precision@K

**Formula**: `Precision@K = (# relevant docs in top K) / K`

**Purpose**: Measures accuracy of top-K results.

**Best For**:
- Top-N recommendations
- First-page results
- User satisfaction (users rarely look beyond top-K)

**Example**:
```
Top 5 results: [relevant, not-relevant, relevant, relevant, not-relevant]
Precision@5 = 3/5 = 0.600
```

### 4. Recall@K

**Formula**: `Recall@K = (# relevant docs in top K) / (total # relevant docs)`

**Purpose**: Measures coverage of relevant results.

**Best For**:
- Comprehensive search
- Discovery scenarios
- "Did we find all relevant items?"

**Example**:
```
Top 5 results contain 3 relevant documents
Total relevant documents in corpus: 8
Recall@5 = 3/8 = 0.375
```

### 5. MAP (Mean Average Precision)

**Formula**: `MAP = (1/|Q|) * Σ(AP_i)` where `AP = (1/R) * Σ(Precision@k * rel(k))`

**Purpose**: Measures precision across all relevant results.

**Best For**:
- Overall search quality
- Multiple relevant documents per query
- Position-sensitive evaluation

## API Usage

### Evaluate Search Results

```python
from apps.memory_api.services.evaluation_service import EvaluationService
from apps.memory_api.models.evaluation_models import (
    RelevanceJudgment,
    RankedResult,
    MetricType
)

eval_service = EvaluationService()

# Ground truth relevance judgments
relevance_judgments = [
    RelevanceJudgment(
        query_id="q1",
        document_id=UUID("mem_123"),
        relevance_score=1.0  # 0.0 = not relevant, 1.0 = highly relevant
    ),
    RelevanceJudgment(
        query_id="q1",
        document_id=UUID("mem_456"),
        relevance_score=0.7
    )
]

# System-generated search results
search_results = {
    "q1": [
        RankedResult(
            document_id=UUID("mem_123"),
            rank=1,
            score=0.95
        ),
        RankedResult(
            document_id=UUID("mem_789"),
            rank=2,
            score=0.87
        ),
        RankedResult(
            document_id=UUID("mem_456"),
            rank=3,
            score=0.82
        )
    ]
}

# Evaluate
result = await eval_service.evaluate_search_results(
    tenant_id="my-tenant",
    project_id="my-project",
    relevance_judgments=relevance_judgments,
    search_results=search_results,
    metrics_to_compute=[
        MetricType.MRR,
        MetricType.NDCG,
        MetricType.PRECISION,
        MetricType.RECALL,
        MetricType.MAP
    ],
    k_values=[1, 3, 5, 10]
)

# Result:
# EvaluationResult(
#     evaluation_id=UUID(...),
#     metrics=[
#         MetricScore(metric_type=MetricType.MRR, score=1.0),
#         MetricScore(metric_type=MetricType.NDCG, score=0.95, k=5),
#         MetricScore(metric_type=MetricType.PRECISION, score=0.67, k=3),
#         ...
#     ],
#     num_queries_evaluated=1,
#     overall_quality_score=0.85,
#     best_metric=MetricType.MRR,
#     worst_metric=MetricType.RECALL
# )
```

### A/B Testing

```python
# Compare two search variants
comparison = await eval_service.compare_ab_variants(
    variant_a_metrics=variant_a_results.metrics,
    variant_b_metrics=variant_b_results.metrics,
    confidence_level=0.95
)

# Returns:
# {
#     "comparisons": {
#         "mrr": {
#             "variant_a": 0.75,
#             "variant_b": 0.82,
#             "improvement_percent": 9.3,
#             "winner": "B"
#         },
#         "ndcg": {...}
#     },
#     "overall_winner": "B",
#     "is_significant": True
# }
```

## Creating Test Sets

### 1. Manual Annotation

```python
# Create relevance judgments manually
judgments = [
    RelevanceJudgment(
        query_id="auth_query_1",
        document_id=UUID("mem_auth_best_practices"),
        relevance_score=1.0,  # Highly relevant
        annotator="human@example.com"
    ),
    RelevanceJudgment(
        query_id="auth_query_1",
        document_id=UUID("mem_oauth_implementation"),
        relevance_score=0.8,  # Relevant
        annotator="human@example.com"
    ),
    RelevanceJudgment(
        query_id="auth_query_1",
        document_id=UUID("mem_ui_components"),
        relevance_score=0.0,  # Not relevant
        annotator="human@example.com"
    )
]
```

### 2. LLM-Assisted Annotation

```python
# Use LLM to generate relevance scores
from apps.memory_api.services.llm import get_llm_provider

llm = get_llm_provider()

async def annotate_with_llm(query: str, document: str) -> float:
    prompt = f"""
    Rate the relevance of this document to the query on a scale of 0.0 to 1.0:

    Query: {query}
    Document: {document}

    Return only a number between 0.0 (not relevant) and 1.0 (highly relevant).
    """

    response = await llm.generate(prompt=prompt)
    return float(response.text.strip())

# Annotate results
relevance_score = await annotate_with_llm(
    query="authentication best practices",
    document=memory.content
)
```

## Continuous Evaluation

### Scheduled Evaluation

```python
# Run evaluation on schedule (via Rules Engine or Celery)
from celery import Celery

@app.task
async def run_daily_evaluation():
    eval_service = EvaluationService()

    # Load test set
    test_queries = load_test_queries()
    relevance_judgments = load_relevance_judgments()

    # Run searches
    search_results = {}
    for query in test_queries:
        results = await search_service.search(query=query.text, k=10)
        search_results[query.id] = results

    # Evaluate
    result = await eval_service.evaluate_search_results(
        tenant_id="system",
        project_id="evaluation",
        relevance_judgments=relevance_judgments,
        search_results=search_results,
        metrics_to_compute=[MetricType.NDCG, MetricType.MRR]
    )

    # Store results
    await store_evaluation_result(result)

    # Alert if quality drops
    if result.overall_quality_score < 0.7:
        await send_alert("Search quality degraded!")
```

## Interpreting Results

### MRR Interpretation
- `MRR > 0.8`: Excellent (first result usually relevant)
- `MRR > 0.6`: Good (relevant result in top 3)
- `MRR > 0.4`: Fair (relevant result in top 5)
- `MRR < 0.4`: Poor (improvement needed)

### NDCG@10 Interpretation
- `NDCG > 0.9`: Excellent ranking
- `NDCG > 0.7`: Good ranking
- `NDCG > 0.5`: Fair ranking
- `NDCG < 0.5`: Poor ranking

### Precision@5 Interpretation
- `P@5 > 0.8`: Excellent (4+ relevant in top 5)
- `P@5 > 0.6`: Good (3+ relevant in top 5)
- `P@5 > 0.4`: Fair (2+ relevant in top 5)
- `P@5 < 0.4`: Poor (< 2 relevant in top 5)

## Best Practices

1. **Use Multiple Metrics**: Don't rely on a single metric
2. **Test Regularly**: Run evaluations on schedule
3. **Version Test Sets**: Track changes to evaluation data
4. **Stratify Queries**: Test different query types separately
5. **Monitor Trends**: Track metrics over time, not just absolute values
6. **A/B Test Changes**: Compare before/after for improvements
7. **Validate Judgments**: Review relevance annotations periodically

## Integration with Drift Detection

```python
# Trigger evaluation when drift detected
from apps.memory_api.models.event_models import EventType

TriggerRule(
    name="Drift Response - Evaluate",
    event_type=EventType.DRIFT_DETECTED,
    actions=[
        ActionConfig(
            action_type=ActionType.RUN_EVALUATION,
            config={
                "test_set": "standard_queries",
                "metrics": ["mrr", "ndcg", "precision"]
            }
        )
    ]
)
```

## Future Enhancements

- [ ] Automatic test set generation
- [ ] Inter-annotator agreement metrics
- [ ] Query difficulty estimation
- [ ] Failure analysis (which queries perform poorly)
- [ ] Real-time evaluation dashboard
- [ ] Statistical significance testing
- [ ] Click-through rate (CTR) tracking
- [ ] User satisfaction surveys integration
