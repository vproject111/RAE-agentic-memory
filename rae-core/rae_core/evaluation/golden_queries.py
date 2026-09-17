"""Golden queries data structures and metrics calculation for retrieval evaluation."""

from __future__ import annotations

import json
import math
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryCategory(StrEnum):
    EXACT_IDENTIFIER = "exact_identifier"
    CODE_SYMBOL = "code_symbol"
    SEMANTIC_CODE = "semantic_code"
    HISTORICAL_DECISION = "historical_decision"
    CROSS_FILE = "cross_file"
    CROSS_REPOSITORY = "cross_repository"
    TEMPORAL = "temporal"
    MULTI_SOURCE = "multi_source"
    GRAPH_RELATION = "graph_relation"


class GoldenQueryCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    query_id: str = Field(description="Unique case identifier")
    query: str = Field(description="Search query string")
    category: QueryCategory = Field(description="Taxonomy category")
    tenant_id: str = Field(description="Tenant ID for tenancy isolation test")
    expected_sources: list[str] = Field(
        default_factory=list,
        description="Expected file paths, class names, or content substrings",
    )
    expected_memory_ids: list[UUID] = Field(
        default_factory=list, description="Expected UUIDs if known"
    )
    forbidden_sources: list[str] = Field(
        default_factory=list,
        description="Sources that must NOT appear (e.g. wrong tenant)",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class MetricResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    category: QueryCategory
    recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_10: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_10: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    empty: bool
    wrong_tenant_found: bool


class BenchmarkSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_queries: int
    recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_10: float = Field(ge=0.0, le=1.0)
    mrr: float = Field(ge=0.0, le=1.0)
    ndcg_at_10: float = Field(ge=0.0, le=1.0)
    latency_p50_ms: float
    latency_p95_ms: float
    reranker_gain: float = Field(default=0.0)
    empty_result_rate: float = Field(ge=0.0, le=1.0)
    wrong_tenant_count: int = Field(default=0)
    category_breakdown: dict[str, dict[str, float]] = Field(default_factory=dict)
    timestamp: str
    engine_profile: str = Field(default="standard")


def compute_relevance_vector(
    returned_items: list[tuple[Any, ...]],
    expected_sources: list[str],
    expected_memory_ids: list[UUID] | None = None,
    item_source_lookup: dict[UUID, str] | None = None,
) -> list[int]:
    """Compute binary relevance vector (1=relevant, 0=non-relevant) for returned results."""
    relevance: list[int] = []
    expected_id_set = {str(uid) for uid in (expected_memory_ids or [])}
    normalized_sources = [s.strip().lower() for s in expected_sources if s.strip()]

    for item in returned_items:
        m_id = item[0] if len(item) > 0 else None
        m_id_str = str(m_id) if m_id is not None else ""

        is_match = False
        if expected_id_set and m_id_str in expected_id_set:
            is_match = True
        elif item_source_lookup and m_id in item_source_lookup:
            source_content = item_source_lookup[m_id].lower()
            if any(src in source_content for src in normalized_sources):
                is_match = True

        relevance.append(1 if is_match else 0)

    return relevance


def calculate_recall_at_k(relevance: list[int], k: int, total_expected: int) -> float:
    """Calculate Recall@K with strict bounds [0.0, 1.0]."""
    if total_expected <= 0:
        return 1.0
    hits = sum(relevance[:k])
    return min(1.0, float(hits) / float(total_expected))


def calculate_mrr(relevance: list[int]) -> float:
    """Calculate Mean Reciprocal Rank (MRR) for first relevant hit."""
    for rank, rel in enumerate(relevance, start=1):
        if rel > 0:
            return 1.0 / float(rank)
    return 0.0


def calculate_ndcg_at_k(relevance: list[int], k: int, total_expected: int) -> float:
    """Calculate Normalized Discounted Cumulative Gain at K (NDCG@K)."""
    sub_rel = relevance[:k]
    if not any(sub_rel):
        return 0.0

    dcg = 0.0
    for idx, rel in enumerate(sub_rel):
        if rel > 0:
            dcg += float(rel) / math.log2(idx + 2)

    ideal_hits = min(total_expected, k)
    if ideal_hits <= 0:
        return 0.0

    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    if idcg <= 0.0:
        return 0.0

    return min(1.0, dcg / idcg)


def load_golden_queries_from_file(path: str | Path) -> list[GoldenQueryCase]:
    """Load golden query cases from a JSON file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Golden queries file not found: {p}")
    with open(p, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "queries" in data:
        items = data["queries"]
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("Invalid format in golden queries JSON")

    return [GoldenQueryCase.model_validate(item) for item in items]
