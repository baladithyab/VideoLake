# Benchmark Execution Guide

**Master execution plan for the complete 8-phase S3Vector benchmark project**

> **Status**: Ready for Execution  
> **Last Updated**: 2025-11-17  
> **Estimated Duration**: 6-8 hours total (excluding Phase 5-7)

---

## Table of Contents

- [Methodology](#methodology)
- [Quick Start](#quick-start)
- [Prerequisites Checklist](#prerequisites-checklist)
- [Phase 1: Infrastructure Deployment](#phase-1-infrastructure-deployment)
- [Phase 2: Data Population](#phase-2-data-population)
- [Phase 3: Benchmark Execution](#phase-3-benchmark-execution)
- [Phase 4: Results Analysis](#phase-4-results-analysis)
- [Phase 5-7: Dockerized Proximity Benchmarking](#phase-5-7-dockerized-proximity-benchmarking-future)
- [Phase 8: Final Recommendations](#phase-8-final-recommendations)
- [Quick Reference Commands](#quick-reference-commands)
- [Troubleshooting](#troubleshooting)

---

## Methodology

We employ two distinct benchmarking methodologies to ensure accuracy and relevance:

### 1. Remote/In-Region Benchmarking (Preferred)
This method executes benchmark scripts on a dedicated EC2 instance (`lancedb-benchmark-runner`) located in the **same AWS region (us-east-1)** as the vector databases.

-   **Why**: Eliminates variable internet latency, providing a true measure of database performance.
-   **How**: Uses AWS Systems Manager (SSM) to trigger scripts on the remote instance.
-   **Use Case**: Performance tuning, backend comparison, latency analysis.

### 2. Local/Cross-Region Benchmarking
This method executes benchmark scripts from your local machine, connecting to the vector databases over the public internet.

-   **Why**: Simulates the experience of a remote client or end-user.
-   **How**: Runs Python scripts directly from your local terminal.
-   **Use Case**: End-to-end connectivity testing, user experience validation.

**Recommendation**: Always use **In-Region Benchmarking** for comparative performance analysis to isolate database latency from network noise.

---

## Quick Start

**For experienced users who want to execute all phases immediately:**

```bash
# 1. Deploy infrastructure
cd terraform && terraform destroy -auto-approve && terraform apply -auto-approve && cd ..

# 2. Export endpoints
export S3VECTOR_BUCKET=$(cd terraform && terraform output -raw s3vector_bucket_name)
export QDRANT_EBS_ENDPOINT=$(cd terraform && terraform output -raw qdrant_ebs_endpoint 2>/dev/null || echo "")
export LANCEDB_EBS_ENDPOINT=$(cd terraform && terraform output -raw lancedb_ebs_endpoint 2>/dev/null || echo "")
export OPENSEARCH_ENDPOINT=$(cd terraform && terraform output -raw opensearch_endpoint 2>/dev/null || echo "")

# 3. Index data (~10 minutes)
./scripts/index_all_backends.sh

# 4. Run benchmarks (~15 minutes)
./scripts/run_comprehensive_benchmarks.sh

# 5. Analyze results
python3 scripts/analyze_benchmark_results.py benchmark-results/session_YYYYMMDD_HHMMSS/
```

> ⚠️ **First-time users**: Skip Quick Start and follow detailed phases below.

---

## Prerequisites Checklist

### Required Tools

- [ ] **Terraform** ≥ 1.0 installed
- [ ] **AWS CLI** ≥ 2.0 configured
- [ ] **Python** ≥ 3.8 with dependencies installed
- [ ] **Git** latest version
- [ ] **jq** for JSON processing (optional but recommended)

**Verify installation:**

```bash
terraform --version   # Should show v1.0+
aws --version        # Should show aws-cli/2.0+
python3 --version    # Should show Python 3.8+
```

### AWS Configuration

- [ ] AWS credentials configured (`aws configure` or environment variables)
- [ ] Sufficient IAM permissions (see [BENCHMARK_SETUP_GUIDE.md](BENCHMARK_SETUP_GUIDE.md#aws-account-requirements))
- [ ] Region set to `us-east-1` (recommended) or supported region
- [ ] Bedrock model access enabled (Titan, Marengo)

**Verify AWS access:**

```bash
aws sts get-caller-identity
# Should return your account ID and user ARN
```

### Repository Setup

- [ ] Repository cloned
- [ ] Virtual environment created and activated
- [ ] Python dependencies installed

**Setup commands:**

```bash
git clone <repository-url>
cd S3Vector
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Pre-flight Check

Run this validation before starting:

```bash
# Check all prerequisites
echo "=== Pre-flight Validation ==="
echo -n "Terraform: "; terraform --version | head -n1
echo -n "AWS CLI: "; aws --version
echo -n "Python: "; python3 --version
echo -n "AWS Account: "; aws sts get-caller-identity --query Account --output text
echo -n "AWS Region: "; aws configure get region
echo "=== Validation Complete ==="
```

**Expected Output:** All commands should succeed with version/account information.

---

## Phase 1: Infrastructure Deployment

**Objective**: Deploy vector database infrastructure for benchmarking  
**Duration**: 15-20 minutes  
**Action**: Deploy all backends with correct configuration

### Step 1.1: Clean Existing Resources

> ⚠️ **WARNING**: This destroys all existing resources. Backup any important data first.

```bash
cd terraform

# Review what will be destroyed
terraform plan -destroy

# Confirm and destroy
terraform destroy -auto-approve
```

**Success Criteria:**
- ✅ All resources destroyed successfully
- ✅ No orphaned resources remain

**Verification:**

```bash
# Should return empty or minimal resources
aws ec2 describe-instances --filters "Name=tag:Project,Values=videolake" --query 'Reservations[].Instances[].InstanceId'
```

### Step 1.2: Deploy with Correct Configuration

Deploy all backends including the fixed LanceDB EBS module:

```bash
# Create configuration file
cat > terraform.tfvars << 'EOF'
# Enable all backends for comprehensive testing
deploy_s3vector = true
deploy_qdrant_ebs = true
deploy_lancedb_ebs = true
deploy_lancedb_s3 = true
deploy_opensearch = true

# Configuration
aws_region = "us-east-1"
project_name = "videolake"

# LanceDB EBS settings (new EC2 module)
lancedb_instance_type = "t3.xlarge"
lancedb_storage_gb = 100
EOF

# Initialize and deploy
terraform init
terraform plan -out=benchmark.tfplan
terraform apply benchmark.tfplan
```

**Duration**: ~15 minutes  
**Success Criteria:**
- ✅ S3 buckets created
- ✅ EC2 instances launched (Qdrant, LanceDB)
- ✅ ECS services running (LanceDB S3)
- ✅ OpenSearch domain active
- ✅ All endpoints accessible

### Step 1.3: Extract and Export Endpoints

```bash
# Return to project root
cd ..

# Extract all endpoints
export S3VECTOR_BUCKET=$(cd terraform && terraform output -raw s3vector_bucket_name)
export QDRANT_EBS_ENDPOINT=$(cd terraform && terraform output -raw qdrant_ebs_endpoint)
export LANCEDB_EBS_ENDPOINT=$(cd terraform && terraform output -raw lancedb_ebs_endpoint)
export LANCEDB_S3_ENDPOINT=$(cd terraform && terraform output -raw lancedb_s3_endpoint)
export OPENSEARCH_ENDPOINT=$(cd terraform && terraform output -raw opensearch_endpoint)

# Display endpoints
echo "=== Deployed Endpoints ==="
echo "S3Vector Bucket: $S3VECTOR_BUCKET"
echo "Qdrant EBS: $QDRANT_EBS_ENDPOINT"
echo "LanceDB EBS: $LANCEDB_EBS_ENDPOINT"
echo "LanceDB S3: $LANCEDB_S3_ENDPOINT"
echo "OpenSearch: $OPENSEARCH_ENDPOINT"
echo "========================="
```

**Save these to a file for later use:**

```bash
# Save for future sessions
cat > .benchmark_env << EOF
export S3VECTOR_BUCKET="$S3VECTOR_BUCKET"
export QDRANT_EBS_ENDPOINT="$QDRANT_EBS_ENDPOINT"
export LANCEDB_EBS_ENDPOINT="$LANCEDB_EBS_ENDPOINT"
export LANCEDB_S3_ENDPOINT="$LANCEDB_S3_ENDPOINT"
export OPENSEARCH_ENDPOINT="$OPENSEARCH_ENDPOINT"
EOF

# In future sessions, simply run:
# source .benchmark_env
```

### Step 1.4: Verify Deployment

Health check all backends:

```bash
# S3Vector bucket
aws s3 ls s3://$S3VECTOR_BUCKET/ --region us-east-1

# Qdrant EBS (EC2)
curl -s "$QDRANT_EBS_ENDPOINT/collections" | jq

# LanceDB EBS (EC2)
curl -s "$LANCEDB_EBS_ENDPOINT/health" | jq

# LanceDB S3 (ECS - may need to discover IP)
curl -s "$LANCEDB_S3_ENDPOINT/health" | jq

# OpenSearch
curl -s "$OPENSEARCH_ENDPOINT/_cluster/health" | jq
```

**Expected Output**: Each command should return valid JSON responses without errors.

**Phase 1 Complete**: ✅ All infrastructure deployed and verified

---

## Phase 2: Data Population

**Objective**: Index embeddings into all backends  
**Duration**: 5-10 minutes  
**Action**: Use automated indexing script

### Step 2.1: Verify Embedding Files

```bash
# Check embedding files exist
ls -lh embeddings/cc-open-samples-marengo/*.json

# Expected output: 3 files (text, image, audio), ~2-3MB each
```

**Files required:**
- [`embeddings/cc-open-samples-marengo/cc-open-samples-text.json`](embeddings/cc-open-samples-marengo/cc-open-samples-text.json) (716 embeddings)
- [`embeddings/cc-open-samples-marengo/cc-open-samples-image.json`](embeddings/cc-open-samples-marengo/cc-open-samples-image.json) (716 embeddings)
- [`embeddings/cc-open-samples-marengo/cc-open-samples-audio.json`](embeddings/cc-open-samples-marengo/cc-open-samples-audio.json) (716 embeddings)

### Step 2.2: Run Indexing Script

The [`scripts/index_all_backends.sh`](scripts/index_all_backends.sh) script handles all backends automatically:

```bash
# Make script executable (if not already)
chmod +x scripts/index_all_backends.sh

# Run indexing for all backends and modalities
./scripts/index_all_backends.sh
```

**What this does:**
1. Validates environment and endpoints
2. Indexes 716 text embeddings to all backends
3. Indexes 716 image embeddings to all backends
4. Indexes 716 audio embeddings to all backends
5. Logs all operations to `logs/indexing_TIMESTAMP.log`

**Duration**: ~5-10 minutes (parallelized by backend)

### Step 2.3: Monitor Progress

In **another terminal**, monitor the log file:

```bash
tail -f logs/indexing_*.log | grep -E "(INFO|SUCCESS|ERROR)"
```

**Expected Progress:**
```
[INFO] Indexing text to s3vector...
[SUCCESS] ✓ Indexed 716 text embeddings to s3vector (45s)
[INFO] Indexing text to qdrant-ebs...
[SUCCESS] ✓ Indexed 716 text embeddings to qdrant-ebs (38s)
...
```

### Step 2.4: Verify Indexing

```bash
# S3Vector - check indexes created
aws s3vectors list-vector-indexes \
  --bucket-name $S3VECTOR_BUCKET \
  --region us-east-1

# Qdrant - check collections
curl -s "$QDRANT_EBS_ENDPOINT/collections" | jq '.result.collections[].name'

# LanceDB - check tables
curl -s "$LANCEDB_EBS_ENDPOINT/tables" | jq

# Expected: Collections/tables for text, image, audio modalities
```

**Success Criteria:**
- ✅ All 15 operations successful (5 backends × 3 modalities)
- ✅ 716 vectors indexed per modality per backend
- ✅ All collections/indexes created
- ✅ No errors in log file

### Troubleshooting Phase 2

**Issue**: Backend not accessible

```bash
# Re-export endpoints and retry
source .benchmark_env
./scripts/index_all_backends.sh --backends <failed-backend>
```

**Issue**: Dimension mismatch

```bash
# Verify embedding dimensions
python3 -c "
import json
with open('embeddings/cc-open-samples-marengo/cc-open-samples-text.json') as f:
    data = json.load(f)
    dims = set(len(e['values']) for e in data['embeddings'])
    print(f'Dimensions found: {dims}')
"
# Should output: Dimensions found: {1024}
```

**Phase 2 Complete**: ✅ All data indexed across all backends

---

## Phase 3: Benchmark Execution

**Objective**: Execute 100-query search benchmarks for all backend/modality combinations  
**Duration**: 10-15 minutes  
**Action**: Use comprehensive benchmark script

### Step 3.1: Run Comprehensive Benchmarks

```bash
# Make script executable (if not already)
chmod +x scripts/run_comprehensive_benchmarks.sh

# Run benchmarks with default settings (100 queries per test)
./scripts/run_comprehensive_benchmarks.sh
```

**Configuration:**
- **Queries per benchmark**: 100
- **Top-K results**: 10
- **Vector dimension**: 1024
- **Total benchmarks**: 15 (5 backends × 3 modalities)

**Duration**: ~10-15 minutes (sequential execution)

### Step 3.2: Monitor Execution

In **another terminal**:

```bash
# Watch progress in log file
tail -f logs/benchmark_*.log | grep -E "(PROGRESS|SUCCESS|ERROR)"
```

**Expected Progress:**
```
[PROGRESS] [1/15] (7%) - s3vector/text
[SUCCESS] ✓ Benchmark completed (120s)
[PROGRESS] [2/15] (13%) - s3vector/image
[SUCCESS] ✓ Benchmark completed (118s)
...
```

### Step 3.3: Locate Results

Results are saved to a session directory:

```bash
# Find the latest session directory
LATEST_SESSION=$(ls -td benchmark-results/session_* | head -n1)
echo "Results directory: $LATEST_SESSION"

# List result files
ls -lh $LATEST_SESSION/*.json
```

**Expected Files:**
```
ccopen_s3vector_text_search.json
ccopen_s3vector_image_search.json
ccopen_s3vector_audio_search.json
ccopen_qdrant-ebs_text_search.json
ccopen_qdrant-ebs_image_search.json
ccopen_qdrant-ebs_audio_search.json
ccopen_lancedb-ebs_text_search.json
ccopen_lancedb-ebs_image_search.json
ccopen_lancedb-ebs_audio_search.json
ccopen_lancedb-s3_text_search.json
ccopen_lancedb-s3_image_search.json
ccopen_lancedb-s3_audio_search.json
ccopen_opensearch_text_search.json
ccopen_opensearch_image_search.json
ccopen_opensearch_audio_search.json
metadata.json
summary.txt
```

### Step 3.4: Quick Results Preview

```bash
# View quick summary
cat $LATEST_SESSION/summary.txt

# Check sample result
cat $LATEST_SESSION/ccopen_s3vector_text_search.json | jq '{
  backend,
  throughput_qps,
  latency_p50_ms,
  latency_p95_ms,
  latency_p99_ms
}'
```

**Expected Metrics:**
- **Throughput**: 2-6 queries/second (varies by backend)
- **P50 Latency**: 150-400ms
- **P95 Latency**: 200-500ms
- **P99 Latency**: 250-600ms

### Step 3.5: Verify Completeness

```bash
# Count successful benchmarks
grep -c '"success": true' $LATEST_SESSION/*.json

# Expected: 15 (all benchmarks successful)
```

**Success Criteria:**
- ✅ 15 JSON result files created
- ✅ All benchmarks report `"success": true`
- ✅ All queries completed (100/100)
- ✅ No errors in log file

**Phase 3 Complete**: ✅ All benchmarks executed successfully

---

## Phase 4: Results Analysis

**Objective**: Generate comprehensive analysis report comparing all backends  
**Duration**: < 1 minute  
**Action**: Run analysis script

### Step 4.1: Run Analysis Script

```bash
# Get latest session directory
LATEST_SESSION=$(ls -td benchmark-results/session_* | head -n1)

# Run analysis
python3 scripts/analyze_benchmark_results.py $LATEST_SESSION
```

**What this generates:**
1. **Markdown report**: `$LATEST_SESSION/analysis_report.md`
2. **CSV export**: `$LATEST_SESSION/results.csv`
3. **Console summary**: Performance rankings and outliers

**Duration**: < 1 minute

### Step 4.2: Review Analysis Report

```bash
# View full report
cat $LATEST_SESSION/analysis_report.md

# Or open in markdown viewer
code $LATEST_SESSION/analysis_report.md  # VS Code
# or
open -a "Typora" $LATEST_SESSION/analysis_report.md  # Mac with Typora
```

**Report Sections:**
1. **Executive Summary**: Best performers identified
2. **Backend Comparison Table**: Side-by-side metrics
3. **Detailed Results**: Per-backend, per-modality breakdown
4. **Performance Outliers**: Statistical anomalies
5. **Recommendations**: Production deployment guidance

### Step 4.3: Interpret Key Metrics

**Understanding the results:**

| Metric | Good Value | Excellent Value | Interpretation |
|--------|------------|-----------------|----------------|
| **Throughput (QPS)** | > 3 | > 5 | Higher = better concurrency |
| **P50 Latency** | < 300ms | < 200ms | Typical user experience |
| **P95 Latency** | < 500ms | < 300ms | 95% of requests |
| **P99 Latency** | < 750ms | < 400ms | Tail latency (SLA critical) |

**Published Benchmark Comparison:**

Based on [`benchmark-results/ccopen_benchmark_summary.md`](benchmark-results/ccopen_benchmark_summary.md):

| Backend | Expected QPS | Expected P95 | Notes |
|---------|-------------|--------------|-------|
| **S3Vector** | 5.35 | 238ms | Highest throughput |
| **Qdrant EBS** | 3.94 | 263ms | Consistent latency |
| **LanceDB EBS** | ~3.5 | ~350ms | True EBS (after fix) |
| **LanceDB S3** | 2.32 | 452ms | Cost-optimized |
| **OpenSearch** | 1.04 | 963ms | Hybrid search features |

### Step 4.4: Identify Performance Issues

**Compare your results to published benchmarks:**

```bash
# Extract key metrics from your results
python3 << 'EOF'
import json
from pathlib import Path
import glob

session = sorted(Path('benchmark-results').glob('session_*'))[-1]
results = {}

for file in session.glob('*_search.json'):
    with open(file) as f:
        data = json.load(f)
    backend = file.stem.split('_')[1]
    if backend not in results:
        results[backend] = []
    results[backend].append(data.get('throughput_qps', 0))

print("Average QPS by Backend:")
for backend, qps_list in sorted(results.items()):
    avg_qps = sum(qps_list) / len(qps_list)
    print(f"  {backend:15} {avg_qps:6.2f}")
EOF
```

**Red Flags:**
- ❌ QPS significantly lower than expected (>30% difference)
- ❌ P99 latency > 1000ms consistently
- ❌ High variance in latency (large std deviation)
- ❌ Any failed queries (`successful_queries < query_count`)

**When to investigate further:**
- Results deviate significantly from published benchmarks
- One backend performs much worse than others
- High latency variance suggests infrastructure issues
- Any benchmark failures

### Step 4.5: Export for Reporting

```bash
# Copy reports to project root for easy access
cp $LATEST_SESSION/analysis_report.md ./LATEST_BENCHMARK_REPORT.md
cp $LATEST_SESSION/results.csv ./LATEST_BENCHMARK_RESULTS.csv
cp $LATEST_SESSION/summary.txt ./LATEST_BENCHMARK_SUMMARY.txt

echo "Reports copied to project root"
```

**Success Criteria:**
- ✅ Analysis report generated
- ✅ All backends analyzed
- ✅ Performance rankings identified
- ✅ Results align with expected values (±20%)

**Phase 4 Complete**: ✅ Comprehensive analysis generated

---

## Phase 5-7: Dockerized Proximity Benchmarking (Future)

**Status**: 🚧 Not Yet Implemented  
**Objective**: Measure performance impact of proximity deployment (co-location with compute)  
**Estimated Duration**: TBD

### Overview

**Goal**: Validate performance improvements when vector stores are deployed in the same VPC/AZ as application compute.

**Approach:**
1. **Phase 5**: Create Docker images with embedded application + vector client
2. **Phase 6**: Deploy on ECS Fargate in same VPC as vector backends
3. **Phase 7**: Run proximity benchmarks measuring reduced network latency

### Why Proximity Matters

**Current Setup** (Phases 1-4):
```
[Your Computer] ---(internet)---> [Vector Database on AWS]
                 ↑
           Network latency: 50-100ms base
```

**Proximity Setup** (Phases 5-7):
```
[ECS Task] ---(VPC internal)---> [Vector Database]
     ↑
  Network latency: 1-5ms base
```

**Expected Improvements:**
- 🚀 **Latency reduction**: 40-60ms improvement in P50/P95
- 🚀 **Throughput increase**: 15-25% QPS improvement
- 🚀 **Consistency**: Lower latency variance

### Prerequisites for Future Work

When implementing Phases 5-7, you'll need:

**Docker Images:**
- [ ] Application server with vector client libraries
- [ ] Benchmark harness containerized
- [ ] Multi-stage build for optimization

**ECS Configuration:**
- [ ] Task definitions with proper networking
- [ ] VPC endpoints for S3/Bedrock access
- [ ] Security groups allowing backend access

**Benchmark Modifications:**
- [ ] Support for internal endpoints
- [ ] VPC-specific health checks
- [ ] CloudWatch metrics integration

### Placeholder Implementation

```bash
# Phase 5: Docker Image Creation (future)
# ./scripts/build_benchmark_docker.sh

# Phase 6: ECS Deployment (future)  
# terraform apply -var="deploy_proximity_benchmarks=true"

# Phase 7: Proximity Benchmarks (future)
# ./scripts/run_proximity_benchmarks.sh
```

### Next Steps for Implementation

1. **Design application container**: Choose framework (FastAPI, Flask, etc.)
2. **Create benchmark Docker image**: Package [`scripts/benchmark_backend.py`](scripts/benchmark_backend.py)
3. **Update Terraform**: Add ECS task definitions for benchmark runners
4. **Implement orchestration**: Script to deploy, run, collect results
5. **Analysis tools**: Compare local vs. proximity performance

**Reference Documentation**: To be created when implementing
- `docs/PROXIMITY_BENCHMARKING.md`
- `terraform/modules/proximity_ecs/`
- `scripts/run_proximity_benchmarks.sh`

---

## Phase 8: Final Recommendations

**Objective**: Synthesize results into production deployment guidance  
**Duration**: Manual review (30-60 minutes)  
**Action**: Document findings and recommendations

### Step 8.1: Performance Summary

Create a comprehensive summary document:

```bash
cat > PERFORMANCE_SUMMARY.md << 'EOF'
# Performance Summary - [Your Project Name]

**Date**: $(date +"%Y-%m-%d")  
**Environment**: AWS us-east-1  
**Dataset**: CC/Open Samples (716 vectors × 3 modalities)

## Top Performers

### Highest Throughput
- **Backend**: [Fill from Phase 4 analysis]
- **Average QPS**: [XX.XX]
- **Cost per million queries**: [$XX.XX]

### Lowest Latency
- **Backend**: [Fill from Phase 4 analysis]
- **P95 Latency**: [XXX ms]
- **P99 Latency**: [XXX ms]

### Best Cost-Performance
- **Backend**: [Compare monthly cost vs. QPS]
- **Monthly cost**: [$XXX]
- **Effective cost**: [$X.XX per million queries]

## Deployment Recommendations

### Production Workload Profile

**High-throughput, cost-sensitive:**
- Recommended: S3Vector
- Rationale: Best QPS/$ ratio, serverless scaling
- Monthly cost: ~$0.50

**Low-latency, performance-critical:**
- Recommended: Qdrant EBS or LanceDB EBS
- Rationale: Consistent P95/P99, direct EBS I/O
- Monthly cost: ~$45-138

**Hybrid search, advanced features:**
- Recommended: OpenSearch with S3Vector
- Rationale: Full-text search, aggregations, analytics
- Monthly cost: ~$120+

### Implementation Plan

1. **Pilot Phase**: [Chosen backend], 1 month evaluation
2. **Metrics to track**: QPS, P95/P99 latency, error rate, cost
3. **Success criteria**: [Define thresholds]
4. **Rollback plan**: [Define conditions]

### Scale Considerations

**Current (716 vectors):**
- Sufficient for: Development, testing, POC
- Limitations: Not representative of production scale

**Recommended next steps:**
- Test with 10K+ vectors for realistic sizing
- Run extended duration tests (24+ hours)
- Simulate concurrent users (10-100 simultaneous queries)
- Measure under load (sustained high QPS)

## Cost Optimization

### Monthly Cost Breakdown (Current Deployment)

| Component | Monthly Cost | Notes |
|-----------|-------------|-------|
| S3Vector | $0.50 | Request-based pricing |
| Qdrant EBS (t3.xlarge + 100GB EBS) | $138 | 24/7 operation |
| LanceDB EBS (t3.xlarge + 100GB EBS) | $138 | 24/7 operation |
| LanceDB S3 (ECS + S3) | $30 | Fargate + storage |
| OpenSearch (2× OR1.medium) | $120 | Managed service |
| **Total** | ~$426 | All backends running |

### Cost Reduction Strategies

1. **Stop unused backends**:
   ```bash
   terraform destroy -target=module.opensearch
   terraform destroy -target=module.lancedb_s3
   # Saves ~$150/month
   ```

2. **Use Spot instances** for development:
   - Potential savings: 50-70%
   - Trade-off: Potential interruptions

3. **Schedule ECS services**:
   ```bash
   # Stop at night, start during work hours
   aws ecs update-service --desired-count 0  # evening
   aws ecs update-service --desired-count 1  # morning
   ```

## Security & Compliance

- [ ] Enable encryption at rest (all backends)
- [ ] Configure VPC endpoints for private connectivity
- [ ] Implement least-privilege IAM policies
- [ ] Enable CloudWatch logging for audit trail
- [ ] Set up AWS Config for compliance monitoring

## Monitoring & Alerting

**Key metrics to monitor:**
- Query latency (P50, P95, P99)
- Throughput (queries/second)
- Error rate
- Backend resource utilization (CPU, memory, IOPS)

**Recommended tools:**
- CloudWatch dashboards for metrics
- Lambda for custom health checks
- SNS for alerting
- X-Ray for distributed tracing

EOF

echo "Performance summary template created: PERFORMANCE_SUMMARY.md"
echo "Fill in values from Phase 4 analysis report"
```

### Step 8.2: Production Deployment Checklist

```markdown
## Production Deployment Checklist

### Pre-Deployment
- [ ] Benchmark results reviewed and approved
- [ ] Backend selected based on requirements
- [ ] Cost estimates validated with finance
- [ ] Security review completed
- [ ] Compliance requirements verified

### Infrastructure
- [ ] Production Terraform workspace created
- [ ] Terraform state backend configured (S3 + DynamoDB)
- [ ] VPC and networking properly configured
- [ ] Security groups follow least-privilege
- [ ] Backup and disaster recovery planned

### Application Integration
- [ ] Client libraries integrated in application
- [ ] Connection pooling configured
- [ ] Retry logic implemented
- [ ] Circuit breakers configured
- [ ] Timeout values optimized

### Monitoring
- [ ] CloudWatch dashboards created
- [ ] Alarms configured for key metrics
- [ ] Log aggregation setup (CloudWatch Logs)
- [ ] Tracing enabled (X-Ray)
- [ ] Runbooks created for common issues

### Operations
- [ ] Deployment automation tested
- [ ] Rollback procedure documented
- [ ] On-call rotation established
- [ ] Incident response plan created
- [ ] Maintenance windows scheduled

### Post-Deployment
- [ ] Monitor metrics for 7 days
- [ ] Compare production metrics to benchmark
- [ ] Gather user feedback
- [ ] Document lessons learned
- [ ] Schedule performance review
```

### Step 8.3: Document Lessons Learned

```bash
# Create lessons learned document
cat > LESSONS_LEARNED.md << 'EOF'
# Lessons Learned - Benchmark Project

## What Went Well

1. **Infrastructure as Code**: Terraform enabled reproducible deployments
2. **Automation**: Scripts reduced manual steps and errors
3. **Documentation**: Comprehensive guides enabled self-service
4. **[Add your observations]**

## Challenges Encountered

1. **LanceDB EBS Issue**: Initially deployed wrong backend (EFS vs EBS)
   - Resolution: Created new EC2-based module
   - Lesson: Always verify deployment matches documentation

2. **[Add your challenges]**

## Improvements for Next Time

1. **Earlier validation**: Test infrastructure before full deployment
2. **Better monitoring**: Real-time dashboards during benchmarks
3. **Parallel execution**: Run benchmarks concurrently where safe
4. **[Add your improvements]**

## Knowledge Gaps Identified

1. Need deeper understanding of: [e.g., ECS networking]
2. Consider training on: [e.g., Terraform advanced features]
3. Research needed: [e.g., vector database internals]

## Action Items

- [ ] Update documentation with corrections
- [ ] Fix identified bugs
- [ ] Implement suggested improvements
- [ ] Share findings with team
EOF

echo "Lessons learned template created: LESSONS_LEARNED.md"
```

**Phase 8 Complete**: ✅ Recommendations documented

---

## Quick Reference Commands

### Environment Export (After Phase 1)

```bash
# Save endpoints to file
cat > .benchmark_env << EOF
export S3VECTOR_BUCKET="$(cd terraform && terraform output -raw s3vector_bucket_name)"
export QDRANT_EBS_ENDPOINT="$(cd terraform && terraform output -raw qdrant_ebs_endpoint)"
export LANCEDB_EBS_ENDPOINT="$(cd terraform && terraform output -raw lancedb_ebs_endpoint)"
export LANCEDB_S3_ENDPOINT="$(cd terraform && terraform output -raw lancedb_s3_endpoint)"
export OPENSEARCH_ENDPOINT="$(cd terraform && terraform output -raw opensearch_endpoint)"
EOF

# Source in current session
source .benchmark_env
```

### Complete Workflow (All Phases)

```bash
# Phase 1: Infrastructure
cd terraform && terraform apply -auto-approve && cd ..
source .benchmark_env

# Phase 2: Data Population  
./scripts/index_all_backends.sh

# Phase 3: Benchmarks
./scripts/run_comprehensive_benchmarks.sh

# Phase 4: Analysis
LATEST=$(ls -td benchmark-results/session_* | head -n1)
python3 scripts/analyze_benchmark_results.py $LATEST
```

### Individual Backend Operations

```bash
# Index single backend
./scripts/index_all_backends.sh --backends s3vector

# Benchmark single backend
./scripts/run_comprehensive_benchmarks.sh --backends qdrant-ebs

# Benchmark single modality
./scripts/run_comprehensive_benchmarks.sh --modalities text
```

### Cleanup Operations

```bash
# Destroy all infrastructure
cd terraform && terraform destroy -auto-approve

# Clean old log files
find logs/ -type f -mtime +7 -delete

# Archive old results
tar -czf benchmark-results-archive-$(date +%Y%m%d).tar.gz benchmark-results/session_*
```

### Health Checks

```bash
# Check all backends
echo "S3Vector:"; aws s3 ls s3://$S3VECTOR_BUCKET/ --region us-east-1
echo "Qdrant:"; curl -s "$QDRANT_EBS_ENDPOINT/collections" | jq -r '.status'
echo "LanceDB EBS:"; curl -s "$LANCEDB_EBS_ENDPOINT/health" | jq -r '.status'
echo "LanceDB S3:"; curl -s "$LANCEDB_S3_ENDPOINT/health" | jq -r '.status'
echo "OpenSearch:"; curl -s "$OPENSEARCH_ENDPOINT/_cluster/health" | jq -r '.status'
```

### Results Export

```bash
# Get latest session
LATEST=$(ls -td benchmark-results/session_* | head -n1)

# Copy to project root
cp $LATEST/analysis_report.md ./LATEST_REPORT.md
cp $LATEST/results.csv ./LATEST_RESULTS.csv

# Create archive
tar -czf benchmark-$(date +%Y%m%d).tar.gz $LATEST/
```

---

## Troubleshooting

### Common Issues

#### Issue: Terraform Apply Fails

**Symptoms:**
```
Error: Error creating ECS Service: InvalidParameterException
```

**Solution:**
```bash
# Check AWS quotas
aws service-quotas list-service-quotas \
  --service-code ecs \
  --query 'Quotas[?QuotaName==`Services per cluster`]'

# Or destroy and retry
terraform destroy -auto-approve
terraform apply -auto-approve
```

#### Issue: Backend Not Accessible

**Symptoms:**
```
curl: (7) Failed to connect to XX.XX.XX.XX port 6333: Connection refused
```

**Solution:**
```bash
# Check security group
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=*qdrant*" \
  --query 'SecurityGroups[].IpPermissions[]'

# Wait for instance to initialize (EC2 backends)
aws ec2 describe-instance-status \
  --instance-ids i-xxxxx \
  --query 'InstanceStatuses[0].InstanceStatus.Status'
```

#### Issue: Indexing Fails

**Symptoms:**
```
[ERROR] ✗ Failed to index text to qdrant-ebs
```

**Solution:**
```bash
# Check endpoint is correct
echo $QDRANT_EBS_ENDPOINT
curl -v $QDRANT_EBS_ENDPOINT/collections

# Try manual index
python3 scripts/index_embeddings.py \
  --embeddings embeddings/cc-open-samples-marengo/cc-open-samples-text.json \
  --backends qdrant-ebs \
  --endpoint $QDRANT_EBS_ENDPOINT \
  --collection videolake-benchmark-text
```

#### Issue: Benchmark Timeout

**Symptoms:**
```
[ERROR] ✗ Benchmark failed (300s)
Timeout waiting for response
```

**Solution:**
```bash
# Reduce query count
./scripts/run_comprehensive_benchmarks.sh --queries 50

# Or increase timeout in benchmark_backend.py
# Edit: REQUEST_TIMEOUT = 60  # Increase as needed
```

#### Issue: Out of Memory

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Reduce batch size or use smaller dataset
# For testing, use test embeddings instead:
./scripts/index_all_backends.sh --embeddings embeddings/test-embeddings-text.json
```

### Getting Help

**Before requesting support, collect:**

```bash
# System information
./scripts/collect_diagnostics.sh > diagnostics.txt

# Or manually:
echo "=== System Info ==="
terraform version
aws --version
python3 --version
echo "=== AWS Identity ==="
aws sts get-caller-identity
echo "=== Deployed Resources ==="
cd terraform && terraform show && cd ..
echo "=== Recent Logs ==="
tail -100 logs/*.log
```

**Support Resources:**
- [`BENCHMARK_SETUP_GUIDE.md`](BENCHMARK_SETUP_GUIDE.md) - Detailed setup instructions
- [`INFRASTRUCTURE_CHANGES.md`](INFRASTRUCTURE_CHANGES.md) - Recent infrastructure updates  
- [`backend-troubleshooting-report.md`](backend-troubleshooting-report.md) - Known issues
- Project issue tracker - Report bugs and request features

---

## Success Criteria Summary

**Phase 1 Complete When:**
- ✅ All Terraform resources deployed (`terraform apply` succeeds)
- ✅ All endpoints exported to environment variables
- ✅ All health checks pass

**Phase 2 Complete When:**
- ✅ 15 indexing operations successful (5 backends × 3 modalities)
- ✅ 716 vectors loaded per modality per backend
- ✅ All collections/indexes visible in backends

**Phase 3 Complete When:**
- ✅ 15 benchmark files generated
- ✅ All benchmarks report `"success": true`
- ✅ 100/100 queries completed for each benchmark

**Phase 4 Complete When:**
- ✅ Analysis report generated
- ✅ Performance rankings identified
- ✅ Results align with published benchmarks (±20%)
- ✅ Recommendations documented

**Phase 8 Complete When:**
- ✅ Performance summary created
- ✅ Production recommendations documented
- ✅ Cost analysis completed
- ✅ Deployment checklist reviewed

---

## Appendix: Published Benchmark Results

**Reference**: [`benchmark-results/ccopen_benchmark_summary.md`](benchmark-results/ccopen_benchmark_summary.md)

**Note**: These are the expected results your benchmarks should approximate.

| Backend | Avg QPS | P50 (ms) | P95 (ms) | P99 (ms) | Cost/Month |
|---------|---------|----------|----------|----------|------------|
| **S3Vector** | 5.35 | 188 | 238 | 313 | $0.50 |
| **Qdrant EBS** | 3.94 | 255 | 263 | 264 | $138 |
| **LanceDB EBS** | ~3.5 | ~300 | ~350 | ~400 | $138 |
| **LanceDB S3** | 2.32 | 438 | 452 | 455 | $30 |
| **OpenSearch** | 1.04 | 963 | 975 | 982 | $120 |

**Key Findings:**
- S3Vector provides best throughput and cost-efficiency
- Qdrant EBS offers most consistent latency
- LanceDB EBS (after fix) provides true block storage performance
- OpenSearch suited for hybrid search use cases

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-17  
**Maintained By**: S3Vector Benchmark Team

**Ready to start?** Begin with [Prerequisites Checklist](#prerequisites-checklist) ✅