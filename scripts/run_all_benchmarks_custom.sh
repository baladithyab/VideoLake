#!/bin/bash
set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Logging and results configuration
RESULTS_DIR="${PROJECT_ROOT}/benchmark-results/multi-backend-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESULTS_DIR"

echo "Results directory: $RESULTS_DIR"

# Endpoints
LANCEDB_S3_ENDPOINT="http://184.72.74.37:8000"
LANCEDB_EFS_ENDPOINT="http://3.85.224.23:8000"
QDRANT_EFS_ENDPOINT="http://18.212.133.68:6333"
QDRANT_EBS_ENDPOINT="http://3.220.167.102:6333"
LANCEDB_EBS_ENDPOINT="http://3.238.148.68:8000"
OPENSEARCH_ENDPOINT="https://search-videolake-jp74yuza4pylhzhut4vimyh43a.us-east-1.es.amazonaws.com"
S3VECTOR_BUCKET="videolake-vectors"

# Common parameters
QUERIES=50
TOP_K=10
DIMENSION=1024
COLLECTION_PREFIX="videolake-benchmark"

# Function to run benchmark
run_benchmark() {
    local backend=$1
    local endpoint=$2
    local collection=$3
    local output_file="$RESULTS_DIR/${backend}.json"
    
    echo "----------------------------------------------------------------"
    echo "Benchmarking $backend..."
    echo "Endpoint: $endpoint"
    echo "Collection: $collection"
    echo "Output: $output_file"
    
    local cmd=(python3 "${SCRIPT_DIR}/benchmark_backend.py" \
        --backend "$backend" \
        --operation search \
        --queries "$QUERIES" \
        --top-k "$TOP_K" \
        --dimension "$DIMENSION" \
        --output "$output_file")

    if [[ -n "$endpoint" ]]; then
        cmd+=("--endpoint" "$endpoint")
    fi

    if [[ "$backend" == "s3vector" ]]; then
        cmd+=("--s3vector-bucket" "$S3VECTOR_BUCKET")
        cmd+=("--s3vector-index" "$collection")
    else
        cmd+=("--collection" "$collection")
    fi

    echo "Running: ${cmd[*]}"
    "${cmd[@]}" || echo "Error benchmarking $backend"
    echo "----------------------------------------------------------------"
}

# 1. S3Vector
# S3Vector uses a specific index name for text
run_benchmark "s3vector" "" "videolake-benchmark-visual-text"

# 2. LanceDB ECS+S3
run_benchmark "lancedb-s3" "$LANCEDB_S3_ENDPOINT" "${COLLECTION_PREFIX}-text"

# 3. LanceDB ECS+EFS
run_benchmark "lancedb-efs" "$LANCEDB_EFS_ENDPOINT" "${COLLECTION_PREFIX}-text"

# 4. LanceDB EC2+EBS
run_benchmark "lancedb-ebs" "$LANCEDB_EBS_ENDPOINT" "${COLLECTION_PREFIX}-text"

# 5. Qdrant ECS+EFS
run_benchmark "qdrant-efs" "$QDRANT_EFS_ENDPOINT" "${COLLECTION_PREFIX}-text"

# 6. Qdrant EC2+EBS
run_benchmark "qdrant-ebs" "$QDRANT_EBS_ENDPOINT" "${COLLECTION_PREFIX}-text"

# 7. OpenSearch
# OpenSearch uses a different collection name format in some cases, but let's try the standard one first.
# If it fails, we might need to check if the index exists or if it uses a different name.
run_benchmark "opensearch" "$OPENSEARCH_ENDPOINT" "${COLLECTION_PREFIX}-text"

echo "Benchmarks completed. Results in $RESULTS_DIR"
ls -l "$RESULTS_DIR"

# Create a summary report
SUMMARY_FILE="$RESULTS_DIR/COMPREHENSIVE_REPORT.md"
echo "# Comprehensive Benchmark Report" > "$SUMMARY_FILE"
echo "Date: $(date)" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "| Backend | Success | QPS | P95 Latency (ms) |" >> "$SUMMARY_FILE"
echo "|---|---|---|---|" >> "$SUMMARY_FILE"

for file in "$RESULTS_DIR"/*.json; do
    if [[ -f "$file" ]]; then
        backend=$(jq -r '.backend // "unknown"' "$file")
        success=$(jq -r '.success // false' "$file")
        qps=$(jq -r '.throughput_qps // 0' "$file")
        p95=$(jq -r '.latency_p95_ms // 0' "$file")
        
        # Format numbers
        qps_fmt=$(printf "%.2f" "$qps")
        p95_fmt=$(printf "%.2f" "$p95")
        
        echo "| $backend | $success | $qps_fmt | $p95_fmt |" >> "$SUMMARY_FILE"
    fi
done

echo "" >> "$SUMMARY_FILE"
echo "See JSON files in $RESULTS_DIR for full details."
cat "$SUMMARY_FILE"