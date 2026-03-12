#!/bin/bash
set -e

# Benchmark Runner Entrypoint Script
# Runs benchmarks from us-east-1 and uploads results to S3

echo "============================================"
echo "S3Vector Benchmark Runner (us-east-1)"
echo "============================================"
echo ""

# Configuration from environment variables
BACKENDS="${BACKENDS:-s3vector,qdrant-ebs,qdrant-efs,lancedb-ebs,lancedb-efs,lancedb-s3}"
MODALITIES="${MODALITIES:-text,image,audio}"
QUERIES="${QUERIES:-100}"
TOP_K="${TOP_K:-10}"
DIMENSION="${DIMENSION:-1024}"
S3VECTOR_BUCKET="${S3VECTOR_BUCKET:-videolake-vectors}"
S3_BUCKET="${S3_BUCKET:-videolake-shared-media}"
S3_RESULTS_PREFIX="${S3_RESULTS_PREFIX:-benchmark-results}"
SESSION_NAME="${SESSION_NAME:-containerized_$(date +%Y%m%d_%H%M%S)}"

# Backend endpoints (from environment or defaults)
QDRANT_EBS_ENDPOINT="${QDRANT_EBS_ENDPOINT:-http://44.201.32.17:6333}"
QDRANT_EFS_ENDPOINT="${QDRANT_EFS_ENDPOINT:-http://13.220.215.190:6333}"
LANCEDB_EBS_ENDPOINT="${LANCEDB_EBS_ENDPOINT:-http://98.82.24.196:8000}"
LANCEDB_EFS_ENDPOINT="${LANCEDB_EFS_ENDPOINT:-http://54.166.202.132:8000}"
LANCEDB_S3_ENDPOINT="${LANCEDB_S3_ENDPOINT:-http://100.25.34.180:8000}"

# Create session directory
SESSION_DIR="/app/results/${SESSION_NAME}"
mkdir -p "$SESSION_DIR"

echo "Configuration:"
echo "  Backends: $BACKENDS"
echo "  Modalities: $MODALITIES"
echo "  Queries per benchmark: $QUERIES"
echo "  Session: $SESSION_NAME"
echo "  Results directory: $SESSION_DIR"
echo ""

# Convert comma-separated lists to arrays
IFS=',' read -ra BACKEND_ARRAY <<< "$BACKENDS"
IFS=',' read -ra MODALITY_ARRAY <<< "$MODALITIES"

# Calculate total benchmarks
TOTAL_BENCHMARKS=$((${#BACKEND_ARRAY[@]} * ${#MODALITY_ARRAY[@]}))
CURRENT_BENCHMARK=0

echo "Starting $TOTAL_BENCHMARKS benchmarks..."
echo ""

# Run benchmarks
for backend in "${BACKEND_ARRAY[@]}"; do
    for modality in "${MODALITY_ARRAY[@]}"; do
        CURRENT_BENCHMARK=$((CURRENT_BENCHMARK + 1))
        
        echo "============================================"
        echo "[$CURRENT_BENCHMARK/$TOTAL_BENCHMARKS] $backend / $modality"
        echo "============================================"
        echo ""

        # Set backend-specific parameters
        case "$backend" in
            s3vector)
                index_name="videolake-benchmark-visual-${modality}"
                if [ "$modality" = "audio" ]; then
                    index_name="videolake-benchmark-audio"
                fi
                BACKEND_ARGS="--backend s3vector --s3vector-bucket $S3VECTOR_BUCKET --s3vector-index ${index_name}"
                ;;
            qdrant-ebs)
                BACKEND_ARGS="--backend qdrant --endpoint $QDRANT_EBS_ENDPOINT --collection videolake-benchmark-${modality}"
                ;;
            qdrant-efs)
                BACKEND_ARGS="--backend qdrant --endpoint $QDRANT_EFS_ENDPOINT --collection videolake-benchmark-${modality}"
                ;;
            lancedb-ebs)
                BACKEND_ARGS="--backend lancedb --endpoint $LANCEDB_EBS_ENDPOINT --collection videolake-benchmark-${modality}"
                ;;
            lancedb-efs)
                BACKEND_ARGS="--backend lancedb --endpoint $LANCEDB_EFS_ENDPOINT --collection videolake-benchmark-${modality}"
                ;;
            lancedb-s3)
                BACKEND_ARGS="--backend lancedb --endpoint $LANCEDB_S3_ENDPOINT --collection videolake-benchmark-${modality}"
                ;;
            *)
                echo "❌ Unknown backend: $backend"
                continue
                ;;
        esac
        
        # Output file
        OUTPUT_FILE="$SESSION_DIR/${backend}_${modality}.json"
        
        # Run benchmark
        python3 /app/scripts/benchmark_backend.py \
            $BACKEND_ARGS \
            --operation search \
            --queries $QUERIES \
            --top-k $TOP_K \
            --dimension $DIMENSION \
            --output "$OUTPUT_FILE" || {
                echo "⚠️ Benchmark failed for $backend / $modality"
                echo '{"success": false, "error": "Benchmark execution failed"}' > "$OUTPUT_FILE"
            }
        
        echo ""
    done
done

echo "============================================"
echo "All Benchmarks Complete!"
echo "============================================"
echo ""

# Generate summary
echo "Generating summary..."
cat > "$SESSION_DIR/SUMMARY.txt" << EOF
S3Vector Benchmark Results (us-east-1)
Session: $SESSION_NAME
Date: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
Region: us-east-1 (containerized)

Benchmarks Executed: $TOTAL_BENCHMARKS
Queries per Benchmark: $QUERIES
Top-K: $TOP_K
Dimension: $DIMENSION

Results:
EOF

# Add results to summary
for f in "$SESSION_DIR"/*.json; do
    if [ -f "$f" ]; then
        filename=$(basename "$f")
        success=$(jq -r '.success // false' "$f")
        if [ "$success" = "true" ]; then
            qps=$(jq -r '.throughput_qps // 0' "$f")
            p50=$(jq -r '.latency_p50_ms // 0' "$f")
            echo "  ✓ $filename: ${qps} QPS | ${p50}ms p50" >> "$SESSION_DIR/SUMMARY.txt"
        else
            echo "  ✗ $filename: FAILED" >> "$SESSION_DIR/SUMMARY.txt"
        fi
    fi
done

cat "$SESSION_DIR/SUMMARY.txt"
echo ""

# Upload results to S3 if configured
if [ -n "$S3_BUCKET" ] && [ -n "$S3_RESULTS_PREFIX" ]; then
    echo "Uploading results to S3..."
    aws s3 sync "$SESSION_DIR" "s3://$S3_BUCKET/$S3_RESULTS_PREFIX/$SESSION_NAME/" --region us-east-1 && \
        echo "✓ Results uploaded to s3://$S3_BUCKET/$S3_RESULTS_PREFIX/$SESSION_NAME/" || \
        echo "⚠️ Failed to upload results to S3"
fi

echo ""
echo "Benchmark runner complete!"

