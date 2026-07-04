#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Full Benchmark Suite INSIDE Docker on Lumina..."
echo "-----------------------------------------------------"

# Helper function to run inside docker
run_in_docker() {
    docker exec rae-api-dev "$@"
}

# 1. Standard Benchmarks
echo ">> Running Standard Benchmarks..."
run_in_docker python3 benchmarking/scripts/run_benchmark.py --set academic_lite.yaml
run_in_docker python3 benchmarking/scripts/run_benchmark.py --set academic_extended.yaml
run_in_docker python3 benchmarking/scripts/run_benchmark.py --set industrial_small.yaml
run_in_docker python3 benchmarking/scripts/run_benchmark.py --set industrial_large.yaml

# 2. Specialized '9/5' Benchmarks
echo ">> Running Specialized '9/5' Benchmarks..."
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark lect
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark mmit
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark grdt
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark rst
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark orb
run_in_docker python3 -m benchmarking.nine_five_benchmarks.runner --benchmark mpeb

# 3. Performance Benchmarks
echo ">> Running Performance/Infrastructure Tests..."
# performance tests might need pytest inside
run_in_docker pytest benchmarking/performance/

echo "-----------------------------------------------------"
echo "✅ All Benchmarks Completed Successfully!"