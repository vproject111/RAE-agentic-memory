#!/usr/bin/env python3
"""
Analyze baseline benchmark data for Iteration 2
"""

import glob
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List


def load_all_benchmarks(
    results_dir: str = "benchmarking/results",
) -> List[Dict[str, Any]]:
    """Load all academic_lite benchmark results"""
    files = glob.glob(f"{results_dir}/academic_lite_*[0-9].json")
    files = [
        f
        for f in files
        if not any(
            x in f
            for x in ["_structure", "_dynamics", "_policy", "_snapshots", "_decisions"]
        )
    ]

    data = []
    for file in sorted(files):
        with open(file) as f:
            benchmark_data = json.load(f)
            # Only include benchmarks with math metrics
            if "math" in benchmark_data.get("metrics", {}):
                data.append(benchmark_data)

    return data


def analyze_benchmarks(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze benchmark data"""

    if not data:
        return {"error": "No benchmark data with math metrics found"}

    # Extract metrics
    mrrs = [d["metrics"]["mrr"] for d in data]
    hit_rates_5 = [d["metrics"]["hit_rate"]["@5"] for d in data]
    quality_scores = [d["metrics"]["overall_quality_score"] for d in data]

    query_times = [d["metrics"]["performance"]["avg_query_time_ms"] for d in data]
    insert_times = [d["metrics"]["performance"]["avg_insert_time_ms"] for d in data]

    # Math metrics
    gcs_values = [
        d["metrics"]["math"]["structure"]["graph_connectivity_score"]["value"]
        for d in data
    ]
    orr_values = [
        d["metrics"]["math"]["policy"]["optimal_retrieval_ratio"]["value"] for d in data
    ]
    mdi_values = [
        d["metrics"]["math"]["dynamics"]["memory_drift_index"]["value"] for d in data
    ]

    analysis = {
        "num_runs": len(data),
        "quality_metrics": {
            "mrr": {
                "mean": statistics.mean(mrrs),
                "median": statistics.median(mrrs),
                "stdev": statistics.stdev(mrrs) if len(mrrs) > 1 else 0,
                "min": min(mrrs),
                "max": max(mrrs),
            },
            "hit_rate_5": {
                "mean": statistics.mean(hit_rates_5),
                "median": statistics.median(hit_rates_5),
                "stdev": statistics.stdev(hit_rates_5) if len(hit_rates_5) > 1 else 0,
            },
            "overall_quality": {
                "mean": statistics.mean(quality_scores),
                "median": statistics.median(quality_scores),
                "stdev": (
                    statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0
                ),
            },
        },
        "performance_metrics": {
            "query_time_ms": {
                "mean": statistics.mean(query_times),
                "median": statistics.median(query_times),
                "p95": (
                    sorted(query_times)[int(len(query_times) * 0.95)]
                    if query_times
                    else 0
                ),
            },
            "insert_time_ms": {
                "mean": statistics.mean(insert_times),
                "median": statistics.median(insert_times),
            },
        },
        "math_metrics": {
            "graph_connectivity": {
                "mean": statistics.mean(gcs_values),
                "stdev": statistics.stdev(gcs_values) if len(gcs_values) > 1 else 0,
            },
            "optimal_retrieval_ratio": {
                "mean": statistics.mean(orr_values),
                "stdev": statistics.stdev(orr_values) if len(orr_values) > 1 else 0,
            },
            "memory_drift_index": {
                "mean": statistics.mean(mdi_values),
                "stdev": statistics.stdev(mdi_values) if len(mdi_values) > 1 else 0,
            },
        },
        "raw_data": {
            "mrrs": mrrs,
            "query_times": query_times,
            "gcs": gcs_values,
            "orr": orr_values,
        },
    }

    return analysis


if __name__ == "__main__":
    data = load_all_benchmarks()
    analysis = analyze_benchmarks(data)

    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        exit(1)

    # Save analysis
    output_file = "eval/math_policy_logs/baseline_analysis.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(analysis, f, indent=2)

    print(f"✅ Analyzed {analysis['num_runs']} benchmark runs")
    print(f"📊 Results saved to {output_file}")
    print("\nKey findings:")
    print(
        f"  MRR: {analysis['quality_metrics']['mrr']['mean']:.3f} ± {analysis['quality_metrics']['mrr']['stdev']:.3f}"
    )
    print(f"  Quality: {analysis['quality_metrics']['overall_quality']['mean']:.3f}")
    print(
        f"  Query time: {analysis['performance_metrics']['query_time_ms']['mean']:.1f}ms"
    )
    print(f"  ORR: {analysis['math_metrics']['optimal_retrieval_ratio']['mean']:.3f}")
