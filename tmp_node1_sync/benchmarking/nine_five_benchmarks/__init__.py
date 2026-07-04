"""
RAE 9/5 Research Benchmarks

Advanced benchmarks for comprehensive evaluation of RAE (Reflective Agentic Memory Engine).
These benchmarks go beyond standard metrics to test long-term behavior, stability, and policy evolution.

Benchmark Suite:
1. LECT - Long-term Episodic Consistency Test
2. MMIT - Multi-Layer Memory Interference Test
3. GRDT - Graph Reasoning Depth Test
4. RST - Reflective Stability Test
5. MPEB - Math-3 Policy Evolution Benchmark
6. ORB - OpenTelemetry Research Benchmark

Usage:
    from benchmarking.nine_five_benchmarks import (
        LECTBenchmark,
        MMITBenchmark,
        GRDTBenchmark,
        RSTBenchmark,
        MPEBBenchmark,
        ORBBenchmark,
    )

    # Run LECT benchmark
    lect = LECTBenchmark()
    results = lect.run(num_cycles=10000)

    # Run all benchmarks
    from benchmarking.nine_five_benchmarks import run_all_benchmarks
    all_results = run_all_benchmarks()
"""

from .grdt_benchmark import GRDTBenchmark
from .lect_benchmark import LECTBenchmark
from .mmit_benchmark import MMITBenchmark
from .mpeb_benchmark import MPEBBenchmark
from .orb_benchmark import ORBBenchmark
from .rst_benchmark import RSTBenchmark
from .runner import NineFiveBenchmarkRunner, run_all_benchmarks

__all__ = [
    "LECTBenchmark",
    "MMITBenchmark",
    "GRDTBenchmark",
    "RSTBenchmark",
    "MPEBBenchmark",
    "ORBBenchmark",
    "run_all_benchmarks",
    "NineFiveBenchmarkRunner",
]

__version__ = "1.0.0"
