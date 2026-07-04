import argparse
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List

# Ensure core module can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

ROOT_DIR = PROJECT_ROOT

import requests  # noqa: E402
import yaml  # noqa: E402

API = os.environ.get("MEMORY_API_URL", "http://localhost:8000")
TENANT_ID = "eval-tenant"


def calculate_ndcg(
    retrieved_items: List[Dict], expected_results: List[Dict], k: int
) -> float:
    """
    Calculates Normalized Discounted Cumulative Gain (NDCG) at k.
    retrieved_items: List of dictionaries, each with at least 'source_id'.
    expected_results: List of dictionaries, each with 'source_id' and 'relevance'.
    k: The number of top results to consider.
    """
    if not expected_results:
        return 0.0

    # Create a map of source_id to relevance for quick lookup
    expected_relevance_map = {
        item["source_id"]: item["relevance"] for item in expected_results
    }

    dcg = 0.0
    for i, item in enumerate(retrieved_items[:k]):
        rank = i + 1
        relevance = expected_relevance_map.get(item.get("source_id"), 0)
        dcg += relevance / math.log2(rank + 1)

    # Calculate Ideal DCG (IDCG)
    ideal_relevances = sorted(
        [item["relevance"] for item in expected_results], reverse=True
    )[:k]
    idcg = 0.0
    for i, relevance in enumerate(ideal_relevances):
        rank = i + 1
        idcg += relevance / math.log2(rank + 1)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def add_memories(memories):
    """Adds memories to the memory-api."""
    print("Adding memories...")
    for mem in memories:
        headers = {"X-Tenant-Id": TENANT_ID}
        payload = mem.copy()

        # The API generates the memory_id, so we don't send it.
        if "memory_id" in payload:
            del payload["memory_id"]

        try:
            r = requests.post(f"{API}/memory/add", json=payload, headers=headers)
            r.raise_for_status()
            print(f"  - Added memory with source_id: {mem.get('source_id')}")
        except requests.exceptions.RequestException as e:
            print(
                f"  - Failed to add memory with source_id: {mem.get('source_id')}. Error: {e}"
            )


def run_evaluation(queries):
    """Runs the evaluation queries and returns the metrics."""
    print("\nRunning evaluation queries...")
    latencies = []
    hit_rate_at_5 = []
    mrr_scores = []
    ndcg_scores = []

    for q in queries:
        t0 = time.time()
        headers = {"X-Tenant-Id": TENANT_ID}
        payload = {
            "tenant_id": TENANT_ID,
            "query_text": q["query"],
            "k": 10,  # We retrieve 10 documents for evaluation
        }

        try:
            r = requests.post(f"{API}/memory/query", json=payload, headers=headers)
            r.raise_for_status()
            dt = (time.time() - t0) * 1000
            latencies.append(dt)

            data = r.json()
            retrieved_items = data.get("results", [])
            expected_results = q.get("expected_results", [])

            # Hit Rate @ 5
            expected_source_ids = {
                item["source_id"] for item in expected_results if item["relevance"] > 0
            }
            got_source_ids_top_5 = {
                item.get("source_id")
                for item in retrieved_items[:5]
                if item.get("source_id")
            }
            hit = 1 if expected_source_ids & got_source_ids_top_5 else 0
            hit_rate_at_5.append(hit)
            print(f"  - Query '{q['query']}': Hit@5: {hit}")

            # MRR
            rank = 0
            for i, item in enumerate(retrieved_items):
                if item.get("source_id") in expected_source_ids:
                    rank = i + 1
                    break

            if rank > 0:
                mrr_scores.append(1 / rank)
            else:
                mrr_scores.append(0)

            # NDCG @ 5
            ndcg = calculate_ndcg(retrieved_items, expected_results, k=5)
            ndcg_scores.append(ndcg)

        except requests.exceptions.RequestException as e:
            print(f"  - Query '{q['query']}' failed. Error: {e}")
            hit_rate_at_5.append(0)
            mrr_scores.append(0)
            ndcg_scores.append(0)

    metrics = {
        "hit_rate@5": statistics.mean(hit_rate_at_5) if hit_rate_at_5 else 0,
        "mrr": statistics.mean(mrr_scores) if mrr_scores else 0,
        "ndcg@5": statistics.mean(ndcg_scores) if ndcg_scores else 0,
        "p95_latency_ms": (
            sorted(latencies)[int(0.95 * len(latencies)) - 1] if latencies else 0
        ),
        "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
    }
    return metrics


def main():
    """Main function to run the evaluation."""
    parser = argparse.ArgumentParser(
        description="Run evaluation for the Agentic Memory API."
    )
    parser.add_argument(
        "--no-add",
        action="store_true",
        help="Skip adding memories and run only the evaluation.",
    )
    args = parser.parse_args()

    goldenset_path = ROOT_DIR / "eval" / "goldenset.yaml"
    with open(goldenset_path, "r", encoding="utf-8") as f:
        goldenset = yaml.safe_load(f)

    if not args.no_add:
        add_memories(goldenset.get("memories", []))

    metrics = run_evaluation(goldenset.get("queries", []))

    print("\n--- Evaluation Metrics ---")
    print(f"Hit Rate @ 5: {metrics['hit_rate@5']:.2f}")
    print(f"MRR: {metrics['mrr']:.2f}")
    print(f"NDCG @ 5: {metrics['ndcg@5']:.2f}")
    print(f"P95 Latency (ms): {metrics['p95_latency_ms']:.2f}")
    print(f"Average Latency (ms): {metrics['avg_latency_ms']:.2f}")
    print("--------------------------")


if __name__ == "__main__":
    main()
