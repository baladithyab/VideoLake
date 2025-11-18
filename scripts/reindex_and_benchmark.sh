#!/bin/bash

# Script to re-index all backends and run benchmarks
# After fresh infrastructure deployment

set -e

LOG_FILE="/tmp/reindex_and_benchmark.log"

echo "Starting re-indexing and benchmarking at $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Step 1: Re-index all backends
echo "" | tee -a "$LOG_FILE"
echo "Step 1: Re-indexing all backends..." | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

cd /home/ubuntu/S3Vector

# Run the indexing script
python3 scripts/index_all_backends.py 2>&1 | tee -a "$LOG_FILE"

# Step 2: Wait for indexing to complete
echo "" | tee -a "$LOG_FILE"
echo "Step 2: Waiting 30 seconds for indexing to stabilize..." | tee -a "$LOG_FILE"
sleep 30

# Step 3: Run local benchmarks
echo "" | tee -a "$LOG_FILE"
echo "Step 3: Running local benchmarks (us-west-1 to us-east-1)..." | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

bash /tmp/run_quick_benchmark.sh 2>&1 | tee -a "$LOG_FILE"

# Step 4: Display results
echo "" | tee -a "$LOG_FILE"
echo "Step 4: Benchmark Results" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

if [ -f /tmp/quick_benchmark_results.json ]; then
  cat /tmp/quick_benchmark_results.json | tee -a "$LOG_FILE"
else
  echo "No benchmark results found" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "Completed at $(date)" | tee -a "$LOG_FILE"
echo "Full log: $LOG_FILE"

