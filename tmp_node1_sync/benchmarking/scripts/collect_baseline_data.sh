#!/bin/bash
# Collect baseline data for Math Layer Controller development
# Runs benchmarks 20 times with --enable-math to gather training data

set -e

# Export database credentials
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=rae
export POSTGRES_PASSWORD=rae_password
export POSTGRES_DB=rae
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# Activate virtual environment
source .venv/bin/activate

# Create output directory
mkdir -p eval/math_policy_logs/baseline

echo "🚀 Starting baseline data collection"
echo "   Target: 20 benchmark runs with mathematical metrics"
echo "   Estimated time: ~40-60 minutes (2-3 min per run)"
echo ""

# Run 20 benchmarks
for i in {1..20}; do
    echo "================================================"
    echo "📊 Run $i/20 - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "================================================"

    # Run benchmark
    python benchmarking/scripts/run_benchmark_math.py \
        --set academic_lite.yaml \
        --enable-math

    # Copy results to baseline directory
    LATEST=$(ls -t benchmarking/results/academic_lite_*.json | head -1 | xargs basename | sed 's/.json//')
    cp benchmarking/results/${LATEST}*.json eval/math_policy_logs/baseline/

    echo "✅ Run $i completed - files copied to baseline/"
    echo ""

    # Sleep between runs to avoid overload (except last run)
    if [ $i -lt 20 ]; then
        echo "⏳ Waiting 10 seconds before next run..."
        sleep 10
    fi
done

echo ""
echo "🎉 Baseline data collection complete!"
echo "   📁 Location: eval/math_policy_logs/baseline/"
echo "   📊 Total files: $(ls eval/math_policy_logs/baseline/*.json | wc -l)"
echo ""
echo "Next step: Analyze data and design Math Layer Controller"
