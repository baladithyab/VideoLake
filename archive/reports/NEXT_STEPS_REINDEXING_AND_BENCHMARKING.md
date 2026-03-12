# Next Steps: Re-indexing and Benchmarking

## Current Status

✅ **Infrastructure Deployed**: All backends are running with optimized LanceDB API  
❌ **Data Not Indexed**: Fresh infrastructure has no data  
❌ **Benchmarks Failed**: All backends returned errors (no collections/tables exist)

## Backend Endpoints

```bash
# LanceDB Backends
export LANCEDB_EBS_ENDPOINT="http://44.204.254.20:8000"
export LANCEDB_EFS_ENDPOINT="http://3.94.117.145:8000"
export LANCEDB_S3_ENDPOINT="http://98.81.178.222:8000"

# Qdrant Backends
export QDRANT_EBS_ENDPOINT="http://44.192.62.209:6333"
export QDRANT_EFS_ENDPOINT="http://54.90.142.5:6333"

# S3Vector
export S3VECTOR_BUCKET="videolake-vectors"

# OpenSearch
export OPENSEARCH_ENDPOINT="https://search-videolake-jp74yuza4pylhzhut4vimyh43a.us-east-1.es.amazonaws.com"
```

## Step 1: Re-index All Backends

### Option A: Use Python Indexing Script (Recommended)

```bash
cd /home/ubuntu/S3Vector

# Index text embeddings
python3 scripts/index_embeddings.py \
  --backend lancedb-ebs \
  --embeddings embeddings/marengo/marengo-benchmark-v1-text.json \
  --collection text_embeddings

python3 scripts/index_embeddings.py \
  --backend lancedb-efs \
  --embeddings embeddings/marengo/marengo-benchmark-v1-text.json \
  --collection text_embeddings

python3 scripts/index_embeddings.py \
  --backend lancedb-s3 \
  --embeddings embeddings/marengo/marengo-benchmark-v1-text.json \
  --collection text_embeddings

python3 scripts/index_embeddings.py \
  --backend qdrant-ebs \
  --embeddings embeddings/marengo/marengo-benchmark-v1-text.json \
  --collection text_embeddings

python3 scripts/index_embeddings.py \
  --backend qdrant-efs \
  --embeddings embeddings/marengo/marengo-benchmark-v1-text.json \
  --collection text_embeddings

# Repeat for image and audio embeddings if needed
```

### Option B: Use Bash Indexing Script

```bash
cd /home/ubuntu/S3Vector

# Set all required environment variables
export S3VECTOR_BUCKET="videolake-vectors"
export QDRANT_EBS_ENDPOINT="http://44.192.62.209:6333"
export LANCEDB_EBS_ENDPOINT="http://44.204.254.20:8000"
export LANCEDB_EFS_ENDPOINT="http://3.94.117.145:8000"
export LANCEDB_S3_ENDPOINT="http://98.81.178.222:8000"
export QDRANT_EFS_ENDPOINT="http://54.90.142.5:6333"
export OPENSEARCH_ENDPOINT="https://search-videolake-jp74yuza4pylhzhut4vimyh43a.us-east-1.es.amazonaws.com"
export LANCEDB_EFS_ENDPOINT_CMD="echo http://3.94.117.145:8000"

# Run indexing script
./scripts/index_all_backends.sh
```

## Step 2: Run Local Benchmarks

After indexing completes, run the benchmark script:

```bash
cd /home/ubuntu/S3Vector
bash /tmp/run_quick_benchmark.sh
```

Results will be saved to:
- Log: `/tmp/benchmark_execution.log`
- JSON: `/tmp/quick_benchmark_results.json`

## Step 3: Rebuild Containerized Benchmark Runner

```bash
cd /home/ubuntu/S3Vector

# Build and push benchmark runner image
./scripts/build_and_push_benchmark_image.sh

# Update ECS service to run 1 task
aws ecs update-service \
  --cluster videolake-benchmark-runner-cluster \
  --service videolake-benchmark-runner-service \
  --desired-count 1 \
  --region us-east-1

# Monitor benchmark execution
aws logs tail /ecs/benchmark/videolake-benchmark-runner \
  --region us-east-1 \
  --follow
```

## Step 4: Document Results

Create a final benchmark report comparing:
- **Before Optimization**: Previous LanceDB performance (28-46 QPS)
- **After Optimization**: New LanceDB performance (expected 150-250 QPS)
- **Qdrant Performance**: Baseline comparison (~190-250 QPS)
- **S3Vector Performance**: Native AWS service (~7-8 QPS)

## Expected Results

| Backend | Previous QPS | Expected QPS | Improvement |
|---------|-------------|--------------|-------------|
| LanceDB EBS | 28.5 | 150-200 | 5-7x |
| LanceDB EFS | 43 | 200-250 | 5-6x |
| LanceDB S3 | 46 | 180-220 | 4-5x |
| Qdrant EBS | ~190 | ~190 | No change |
| Qdrant EFS | ~250 | ~250 | No change |
| S3Vector | ~7-8 | ~7-8 | No change |

## Troubleshooting

### LanceDB EBS Connection Errors
If LanceDB EBS shows connection errors, check if the service is running:
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=videolake-lancedb-ebs-lancedb" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --region us-east-1
```

### HTTP 500 Errors
Indicates tables don't exist - run indexing first.

### HTTP 404 Errors
Indicates collections don't exist - run indexing first.

## Files Created

- `/tmp/benchmark_execution.log` - Benchmark execution log
- `/tmp/quick_benchmark_results.json` - Benchmark results
- `benchmark-results/2025-11-17-fresh-infrastructure-status.md` - Infrastructure status
- `NEXT_STEPS_REINDEXING_AND_BENCHMARKING.md` - This file

