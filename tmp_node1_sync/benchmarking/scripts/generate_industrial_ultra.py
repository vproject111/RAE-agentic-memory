#!/usr/bin/env python3
"""
Generator for industrial_ultra.yaml benchmark dataset (10x larger)

Usage:
    python generate_industrial_ultra.py --size 10000 --output benchmarking/sets/industrial_ultra.yaml
"""

import sys
from pathlib import Path

# Reuse the existing generator logic
sys.path.insert(0, str(Path(__file__).parent))
import argparse

import yaml
from generate_industrial_large import IndustrialDataGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate industrial_ultra.yaml benchmark"
    )
    parser.add_argument(
        "--size", type=int, default=10000, help="Number of memories to generate"
    )
    parser.add_argument(
        "--queries", type=int, default=500, help="Number of queries to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarking/sets/industrial_ultra.yaml",
        help="Output file path",
    )

    args = parser.parse_args()

    print(f"🏭 Generating Industrial ULTRA Benchmark ({args.size} memories)...")
    generator = IndustrialDataGenerator(seed=1337)  # Different seed for ultra

    memories = generator.generate_memories(args.size)
    queries = generator.generate_queries(args.queries, memories)

    benchmark = {
        "name": "industrial_ultra",
        "description": f"Ultra-scale industrial benchmark with {args.size} memories",
        "version": "1.0",
        "memories": memories,
        "queries": queries,
        "config": {
            "top_k": 10,
            "min_relevance_score": 0.2,
            "enable_reranking": True,
            "enable_reflection": True,
            "enable_graph": True,
            "test_scale": True,
            "test_performance": True,
        },
    }

    print(f"💾 Writing to {args.output}...")
    with open(args.output, "w") as f:
        yaml.dump(
            benchmark, f, default_flow_style=False, allow_unicode=True, sort_keys=False
        )

    print(f"✅ Generated {len(memories)} memories and {len(queries)} queries.")


if __name__ == "__main__":
    main()
