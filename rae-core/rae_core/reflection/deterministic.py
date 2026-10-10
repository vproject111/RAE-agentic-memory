"""Deterministic / Mathematical Reflection Engine (Tier 1 Reflection).

Executes instant (<5ms, $0.00 cost) statistical, graph-based, and semantic
clustering reflection without calling external LLMs.
"""

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class DeterministicReflectionEngine:
    """Tier 1 Math-First Reflection Engine.

    Performs:
    1. Fast lexical and n-gram concept co-occurrence analysis.
    2. Cosine similarity clustering for convergent memories.
    3. Graph centrality scoring to extract anchor themes.
    4. Deterministic consolidation and witness tracking without LLM calls.
    """

    def __init__(self, similarity_threshold: float = 0.88):
        self.similarity_threshold = similarity_threshold

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract normalized words filtering stop words and punctuation."""
        if not text:
            return []
        tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", text.lower())
        stop_words = {
            "the", "and", "for", "with", "this", "that", "from", "are", "was",
            "were", "will", "have", "has", "had", "not", "but", "what", "which",
            "when", "where", "how", "all", "any", "both", "each", "few", "more",
            "most", "other", "some", "such", "than", "too", "very", "can", "may",
            "into", "then", "them", "these", "they", "been", "being", "here",
        }
        return [t for t in tokens if t not in stop_words]

    def compute_jaccard_similarity(self, tokens_a: set[str], tokens_b: set[str]) -> float:
        """Compute Jaccard similarity between two token sets."""
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union) if union else 0.0

    @staticmethod
    def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def extract_concept_graph(
        self, memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build co-occurrence graph across memory texts and extract dominant hubs."""
        word_freq = Counter()
        co_occurrences = Counter()

        for mem in memories:
            content = mem.get("content", "")
            tokens = set(self._tokenize(content))
            for t in tokens:
                word_freq[t] += 1
            token_list = sorted(list(tokens))
            for i in range(len(token_list)):
                for j in range(i + 1, len(token_list)):
                    pair = (token_list[i], token_list[j])
                    co_occurrences[pair] += 1

        top_concepts = [w for w, _ in word_freq.most_common(10)]
        strong_relations = [
            {"source": pair[0], "target": pair[1], "weight": count}
            for pair, count in co_occurrences.most_common(15)
            if count >= 2
        ]

        return {
            "top_concepts": top_concepts,
            "relations": strong_relations,
            "vocabulary_size": len(word_freq),
        }

    def cluster_memories(
        self, memories: list[dict[str, Any]]
    ) -> list[list[dict[str, Any]]]:
        """Group memories into semantic/lexical clusters based on similarity."""
        if not memories:
            return []

        clusters: list[list[dict[str, Any]]] = []
        tokenized = [set(self._tokenize(m.get("content", ""))) for m in memories]

        assigned = [False] * len(memories)

        for i in range(len(memories)):
            if assigned[i]:
                continue
            current_cluster = [memories[i]]
            assigned[i] = True

            for j in range(i + 1, len(memories)):
                if assigned[j]:
                    continue
                # Check vector similarity if present
                sim = 0.0
                vec_i = memories[i].get("embedding")
                vec_j = memories[j].get("embedding")
                if vec_i and vec_j:
                    sim = self.compute_cosine_similarity(vec_i, vec_j)
                else:
                    sim = self.compute_jaccard_similarity(tokenized[i], tokenized[j])

                if sim >= self.similarity_threshold:
                    current_cluster.append(memories[j])
                    assigned[j] = True

            clusters.append(current_cluster)

        return clusters

    def consolidate_cluster(
        self, cluster: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Synthesize a cluster into a deterministic consolidated insight."""
        if not cluster:
            return {}

        best_memory = max(cluster, key=lambda m: float(m.get("importance", 0.5)))
        all_tags: set[str] = set()
        total_witnesses = 0

        for m in cluster:
            all_tags.update(m.get("tags") or [])
            meta = m.get("metadata") or {}
            w_count = meta.get("witness_count", 1)
            total_witnesses += int(w_count)

        base_importance = float(best_memory.get("importance", 0.5))
        # Logarithmic reinforcement based on cluster size and witness count
        boost = 0.1 * math.log(1.0 + len(cluster))
        consolidated_importance = min(1.0, round(base_importance + boost, 3))

        summary = (
            f"[Consolidated Insight: {len(cluster)} evidence nodes, {total_witnesses} witnesses] "
            f"{best_memory.get('content', '')}"
        )

        return {
            "canonical_memory_id": str(best_memory.get("id")),
            "source_ids": [str(m.get("id")) for m in cluster if m.get("id")],
            "content": summary,
            "importance": consolidated_importance,
            "witness_count": total_witnesses,
            "tags": sorted(list(all_tags)),
            "cluster_size": len(cluster),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_reflection_from_trace(
        self,
        task_goal: str,
        task_description: str,
        events: list[dict[str, Any]],
        outcome: str,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate structured reflection for execution traces without LLM."""
        is_failure = outcome.lower() in ["failure", "error", "timeout"]

        event_types = [e.get("event_type", "step") for e in events]
        event_summary = ", ".join(event_types[:6]) if event_types else "no events"

        tags = ["deterministic_reflection", outcome.lower()]
        for e in events:
            tags.extend(e.get("tags", []))

        if is_failure:
            err_msg = (error or {}).get("error_message", "Unknown execution failure")
            err_cat = (error or {}).get("error_category", "execution_error")
            reflection_text = (
                f"Execution failed during [{event_summary}] with error: {err_msg}. "
                f"Root cause relates to {err_cat}. Mitigation required before next cycle."
            )
            strategy_text = (
                f"Implement fail-safe check for {err_cat} and verify precondition state "
                "prior to action execution."
            )
            importance = 0.85
            confidence = 0.90
            tags.append(str(err_cat))
        else:
            reflection_text = (
                f"Task achieved SUCCESS through structured execution sequence: [{event_summary}]. "
                "Actions conformed to expected constraints with zero detected faults."
            )
            strategy_text = (
                "Preserve current action template and parameters as baseline for similar tasks."
            )
            importance = 0.70
            confidence = 0.95
            tags.append("best_practice")

        return {
            "reflection": reflection_text,
            "strategy": strategy_text,
            "importance": importance,
            "confidence": confidence,
            "tags": sorted(list(set(tags))),
            "method": "deterministic_math_tier1",
        }
