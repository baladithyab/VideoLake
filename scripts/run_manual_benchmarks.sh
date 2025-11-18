#!/bin/bash

# Manual benchmark runner - runs each benchmark sequentially
# This bypasses the comprehensive benchmark script issues

set -e

cd /home/ubuntu/S3Vector

# Create session directory
SESSION_DIR="benchmark-results/manual_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SESSION_DIR"

echo "============================================"
echo "Manual Benchmark Execution"
echo "Session: $SESSION_DIR"
echo "============================================"
echo ""

# Define backends and modalities
BACKENDS=("s3vector" "qdrant-ebs" "lancedb-ebs" "lancedb-efs" "lancedb-s3" "qdrant-efs")
MODALITIES=("text" "image" "audio")

# S3Vector indexes for each modality
declare -A S3VECTOR_INDEXES
S3VECTOR_INDEXES[text]="videolake-benchmark-visual-text"
S3VECTOR_INDEXES[image]="videolake-benchmark-visual-image"
S3VECTOR_INDEXES[audio]="videolake-benchmark-visual-audio"

# Endpoints
QDRANT_EBS_ENDPOINT="http://44.201.32.17:6333"
LANCEDB_EBS_ENDPOINT="http://98.82.24.196:8000"
LANCEDB_EFS_ENDPOINT="http://54.166.202.132:8000"
LANCEDB_S3_ENDPOINT="http://100.25.34.180:8000"
QDRANT_EFS_ENDPOINT="http://13.220.215.190:6333"
S3VECTOR_BUCKET="videolake-vectors"

TOTAL_BENCHMARKS=$((${#BACKENDS[@]} * ${#MODALITIES[@]}))
CURRENT=0

for backend in "${BACKENDS[@]}"; do
  for modality in "${MODALITIES[@]}"; do
    CURRENT=$((CURRENT + 1))
    echo ""
    echo "============================================"
    echo "[$CURRENT/$TOTAL_BENCHMARKS] $backend / $modality"
    echo "============================================"
    
    OUTPUT_FILE="$SESSION_DIR/${backend}_${modality}.json"
    
    # Build command based on backend
    case $backend in
      s3vector)
        python3 scripts/benchmark_backend.py \
          --backend s3vector \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --s3vector-bucket "$S3VECTOR_BUCKET" \
          --s3vector-index "${S3VECTOR_INDEXES[$modality]}" \
          --output "$OUTPUT_FILE"
        ;;
      qdrant-ebs)
        python3 scripts/benchmark_backend.py \
          --backend qdrant \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --endpoint "$QDRANT_EBS_ENDPOINT" \
          --collection "videolake-benchmark-$modality" \
          --output "$OUTPUT_FILE"
        ;;
      lancedb-ebs)
        python3 scripts/benchmark_backend.py \
          --backend lancedb \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --endpoint "$LANCEDB_EBS_ENDPOINT" \
          --collection "videolake-benchmark-$modality" \
          --output "$OUTPUT_FILE"
        ;;
      lancedb-efs)
        python3 scripts/benchmark_backend.py \
          --backend lancedb \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --endpoint "$LANCEDB_EFS_ENDPOINT" \
          --collection "videolake-benchmark-$modality" \
          --output "$OUTPUT_FILE"
        ;;
      lancedb-s3)
        python3 scripts/benchmark_backend.py \
          --backend lancedb \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --endpoint "$LANCEDB_S3_ENDPOINT" \
          --collection "videolake-benchmark-$modality" \
          --output "$OUTPUT_FILE"
        ;;
      qdrant-efs)
        python3 scripts/benchmark_backend.py \
          --backend qdrant \
          --operation search \
          --queries 100 \
          --top-k 10 \
          --dimension 1024 \
          --endpoint "$QDRANT_EFS_ENDPOINT" \
          --collection "videolake-benchmark-$modality" \
          --output "$OUTPUT_FILE"
        ;;
    esac
    
    if [ $? -eq 0 ]; then
      echo "✓ Benchmark completed successfully"
    else
      echo "✗ Benchmark failed"
    fi
  done
done

echo ""
echo "============================================"
echo "All Benchmarks Complete!"
echo "============================================"
echo "Session directory: $SESSION_DIR"
echo "Total benchmarks: $TOTAL_BENCHMARKS"
echo ""
echo "Next steps:"
echo "  python3 scripts/analyze_benchmark_results.py $SESSION_DIR"

