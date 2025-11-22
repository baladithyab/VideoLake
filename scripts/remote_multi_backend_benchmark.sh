#!/bin/bash
# Remote Multi-Backend Benchmark Script (runs in us-east-1)
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="/tmp/benchmark-results-${TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

echo "=== Multi-Backend Benchmark (us-east-1 Region) ==="
echo "Timestamp: $TIMESTAMP"
echo "Results Directory: $RESULTS_DIR"

# Download scripts from S3
echo "Downloading benchmark scripts..."
aws s3 cp s3://videolake-shared-media/benchmark-scripts/benchmark_backend.py /tmp/ --region us-east-1
aws s3 cp s3://videolake-shared-media/benchmark-scripts/backend_adapters.py /tmp/ --region us-east-1
aws s3 cp s3://videolake-shared-media/benchmark-scripts/test-embeddings-text.json /tmp/ --region us-east-1

# Install dependencies if needed
pip3 install numpy boto3 requests --quiet 2>/dev/null || echo "Dependencies already installed"

# Get Qdrant endpoint
QDRANT_IP=$(aws ecs list-tasks --cluster videolake-qdrant-cluster --service-name videolake-qdrant-service --query 'taskArns[0]' --output text --region us-east-1 | xargs -I {} aws ecs describe-tasks --cluster videolake-qdrant-cluster --tasks {} --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text --region us-east-1 | xargs -I {} aws ec2 describe-network-interfaces --network-interface-ids {} --query 'NetworkInterfaces[0].Association.PublicIp' --output text --region us-east-1)

echo "Backend Endpoints:"
echo "  S3Vector: s3vectors.us-east-1.amazonaws.com"
echo "  LanceDB-EBS: http://172.31.4.104:8000 (private IP)"
echo "  Qdrant-EFS: http://$QDRANT_IP:6333"

# Benchmark S3Vector
echo ""
echo "=== Benchmarking S3Vector ==="
python3 /tmp/benchmark_backend.py \
    --backend s3vector \
    --operation search \
    --queries 50 \
    --collection videolake-multibackend-test \
    --s3vector-index videolake-benchmark-visual-text \
    --output "$RESULTS_DIR/s3vector.json"

# Benchmark LanceDB-EBS (using private IP for lower latency)
echo ""
echo "=== Benchmarking LanceDB-EBS ==="
python3 /tmp/benchmark_backend.py \
    --backend lancedb-ebs \
    --operation search \
    --queries 50 \
    --collection videolake-multibackend-test \
    --endpoint http://172.31.4.104:8000 \
    --output "$RESULTS_DIR/lancedb-ebs.json"

# Benchmark Qdrant-EFS
echo ""
echo "=== Benchmarking Qdrant-EFS ==="
python3 /tmp/benchmark_backend.py \
    --backend qdrant \
    --operation search \
    --queries 50 \
    --collection videolake-multibackend-test \
    --endpoint "http://$QDRANT_IP:6333" \
    --output "$RESULTS_DIR/qdrant-efs.json"

# Upload results to S3
echo ""
echo "=== Uploading Results to S3 ==="
aws s3 cp "$RESULTS_DIR/" "s3://videolake-shared-media/benchmark-results/remote-${TIMESTAMP}/" --recursive --region us-east-1

echo ""
echo "✓ All benchmarks complete!"
echo "Results uploaded to: s3://videolake-shared-media/benchmark-results/remote-${TIMESTAMP}/"
echo "Local results: $RESULTS_DIR"
