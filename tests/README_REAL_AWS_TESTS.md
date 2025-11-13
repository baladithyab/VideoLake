# Real AWS End-to-End Integration Tests

⚠️ **WARNING: These tests use REAL AWS resources and WILL INCUR COSTS!**

## Overview

The [`test_real_aws_e2e_workflows.py`](test_real_aws_e2e_workflows.py) file contains comprehensive end-to-end integration tests that use actual AWS services instead of mocks. These tests validate the complete video retrieval workflow using real resources.

### S3Vector-First Architecture

**S3Vector is the primary backend** - Core tests validate S3Vector functionality with no additional infrastructure required.

**Optional backends** (OpenSearch, Qdrant, LanceDB) are **comparison backends only** and require Terraform deployment before testing.

## Estimated Costs

| Test Type | Estimated Cost | Duration | Infrastructure Required | Notes |
|-----------|---------------|----------|------------------------|-------|
| **S3Vector Workflow (Core)** | $0.01-0.02 | 2-5 min | None (built-in) | Primary backend test |
| **LanceDB Workflow (Optional)** | $0.01 | 1-2 min | Terraform deployment | S3 storage only |
| **Qdrant Workflow (Optional)** | $0.02-0.05 | 2-5 min | Terraform deployment | Memory-based storage |
| **OpenSearch Workflow (Optional)** | $1.00+/hour | 10-20 min | Terraform deployment | ⚠️ VERY EXPENSIVE! |
| **Provider Comparison** | $0.05 | 5 min | Depends on mode | Compares deployed backends |
| **Core Tests Only** | $0.02-0.05 | 5 min | None | S3Vector only |
| **Full Suite (no OpenSearch)** | $0.05-0.10 | 10 min | Mode 2/3 deployment | Includes optional backends |
| **Full Suite (with OpenSearch)** | $2-5 | 20-30 min | Mode 3 deployment | ⚠️ Includes expensive tests |

## Prerequisites

### Core Prerequisites (For S3Vector Tests)

These are required for all tests:

You need AWS credentials with the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:PutBucketPolicy",
        "s3vectors:CreateIndex",
        "s3vectors:DeleteIndex",
        "s3vectors:DescribeIndex",
        "s3vectors:PutVectors",
        "s3vectors:QueryVectors",
        "bedrock:InvokeModel",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: S3Vector tests work immediately with these permissions - no additional infrastructure setup required.

### Optional Backend Prerequisites (For Comparison Tests)

**Required before running optional backend tests:**

1. **Terraform Deployment**
   ```bash
   cd terraform
   
   # Mode 2: S3Vector + one optional backend
   terraform apply -var="deployment_mode=mode2" -var="primary_backend=lancedb"
   
   # Mode 3: S3Vector + multiple backends for comparison
   terraform apply -var="deployment_mode=mode3"
   ```

2. **Verify Deployment**
   ```bash
   terraform output
   # Should show: opensearch_endpoint, qdrant_endpoint, lancedb_bucket, etc.
   ```

3. **Additional AWS Permissions** (if using optional backends)
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "aoss:CreateCollection",
       "aoss:DeleteCollection",
       "aoss:BatchGetCollection",
       "ec2:CreateVpc",
       "ec2:CreateSubnet",
       "ecs:CreateCluster",
       "ecs:CreateService"
     ],
     "Resource": "*"
   }
   ```

See [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md) for detailed deployment instructions.

### 2. AWS Region

Tests must run in a region that supports TwelveLabs models:
- `us-east-1` (recommended)
- `us-west-2`

Set your region:
```bash
export AWS_REGION=us-east-1
```

### 3. Environment Variables

Required:
```bash
export AWS_REGION=us-east-1
```

Optional:
```bash
# Custom test prefix (default: auto-generated with timestamp)
export REAL_AWS_TEST_PREFIX=my-test-prefix

# Keep resources after tests for debugging
export KEEP_TEST_RESOURCES=1

# Skip expensive tests (OpenSearch)
export SKIP_EXPENSIVE_TESTS=1

# Mark as automated (skips interactive confirmations)
export CI=1
export AUTOMATED_TEST=1
```

### 4. Python Dependencies

```bash
pip install pytest boto3 requests python-dotenv
```

## Running Tests Safely

### Phase 1: Core S3Vector Tests (No Infrastructure Required)

**Start here - these tests work immediately:**

1. **Check Prerequisites** (dry run):
```bash
pytest tests/test_real_aws_e2e_workflows.py --collect-only
```

2. **Run Core S3Vector Tests**:
```bash
# S3Vector workflow only (primary backend, no extra infrastructure)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Error handling tests (cheapest, ~$0.01)
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

**Cost**: ~$0.02-0.05, **Duration**: 5 minutes, **Infrastructure**: None required

### Phase 2: Optional Backend Tests (Requires Terraform)

**Only proceed if you need backend comparison testing:**

1. **Deploy Optional Backends**:
```bash
cd terraform

# Mode 2: S3Vector + one optional backend
terraform apply -var="deployment_mode=mode2" -var="primary_backend=lancedb"

# Mode 3: Full comparison (includes expensive OpenSearch)
terraform apply -var="deployment_mode=mode3"
```

2. **Verify Deployment**:
```bash
terraform output
# Confirm endpoints are available before running tests
```

3. **Run Optional Backend Tests**:
```bash
cd ..

# LanceDB workflow (if deployed via Terraform)
pytest tests/test_real_aws_e2e_workflows.py::TestRealLanceDBWorkflow -v --real-aws

# Qdrant workflow (if deployed via Terraform)
pytest tests/test_real_aws_e2e_workflows.py::TestRealQdrantWorkflow -v --real-aws

# Performance comparison across backends
pytest tests/test_real_aws_e2e_workflows.py::TestRealProviderComparison -v --real-aws
```

**⚠️ OpenSearch Tests (Very Expensive!):**
```bash
# Only run if you deployed Mode 3 and accept $1+/hour costs!
pytest tests/test_real_aws_e2e_workflows.py::TestRealOpenSearchWorkflow -v --real-aws
```

4. **Clean Up After Testing**:
```bash
cd terraform
terraform destroy
```

### Running All Tests at Once

**⚠️ Core Only (Recommended):**
```bash
# Run all S3Vector tests, no optional backends (~$0.05, 5 minutes)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

**⚠️ With Optional Backends (Requires Terraform deployment):**
```bash
# Requires terraform apply first!
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

**⚠️ Full Suite Including OpenSearch (Expensive!):**
```bash
# Requires Mode 3 deployment, $2-5 in costs!
SKIP_EXPENSIVE_TESTS=0 pytest tests/test_real_aws_e2e_workflows.py -v --real-aws
```

### Keeping Resources for Debugging

```bash
# Resources will NOT be deleted after tests
KEEP_TEST_RESOURCES=1 pytest tests/test_real_aws_e2e_workflows.py -v --real-aws
```

**Manual cleanup after debugging:**

For S3Vector resources:
```bash
python scripts/cleanup_all_resources.py --prefix test-real-e2e
```

For Terraform-deployed backends:
```bash
cd terraform
terraform destroy
```

## Safety Features

### 1. Explicit Opt-In Required

Tests will NOT run without the `--real-aws` flag:

```bash
# This will SKIP all real AWS tests
pytest tests/test_real_aws_e2e_workflows.py -v

# This will RUN real AWS tests (incurs costs)
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws
```

### 2. Automatic Resource Cleanup

All resources are cleaned up automatically using pytest fixtures with try/finally blocks:
- S3 buckets (with all objects)
- S3 Vector indexes
- Uploaded test files

Cleanup runs even if tests fail!

### 3. Unique Resource Names

Resources are named with timestamps and UUIDs to avoid conflicts:
```
test-real-e2e-1699632120-abc123-videos
test-real-e2e-1699632120-abc123-idx
```

### 4. Cost Tracking and Logging

All tests log:
- Estimated costs before operations
- Actual resource creation
- Performance metrics
- Total time and cost summary

### 5. Interactive Confirmations

Expensive tests (OpenSearch) require:
- Environment variable confirmation
- Auto-skip in CI/automated environments
- Clear cost warnings before execution

## Test Structure

### TestRealS3VectorWorkflow

**What it tests:**
1. Real video processing with TwelveLabs
2. Real S3 Vector index creation
3. Actual vector upsert operations
4. Real similarity queries
5. Performance measurements

**Cost:** ~$0.01-0.02  
**Duration:** 2-5 minutes

### TestRealOpenSearchWorkflow

**What it tests:**
1. OpenSearch Serverless collection creation
2. Video processing
3. OpenSearch vector storage
4. KNN and hybrid search

**Cost:** ~$1.00+ per hour  
**Duration:** 10-20 minutes  
**⚠️ EXPENSIVE!** Requires explicit opt-in

### TestRealLanceDBWorkflow

**What it tests:**
1. LanceDB with S3 backend
2. Video processing integration
3. Columnar storage benefits

**Cost:** ~$0.01  
**Duration:** 1-2 minutes

### TestRealProviderComparison

**What it tests:**
1. Performance comparison across providers
2. Throughput measurements
3. Latency benchmarks
4. Cost analysis

**Cost:** ~$0.05  
**Duration:** 5 minutes

### TestRealErrorHandling

**What it tests:**
1. Invalid video file handling
2. Error recovery
3. Graceful failure modes

**Cost:** < $0.01  
**Duration:** < 1 minute

## Troubleshooting

### Test Skipped: "Prerequisites not met"

**Check:**
1. AWS credentials configured: `aws sts get-caller-identity`
2. Region supports TwelveLabs: `echo $AWS_REGION`
3. Bedrock access: `aws bedrock list-foundation-models --region us-east-1`

### Test Failed: "Invalid S3 credentials"

**Solution:**
This error occurs when Bedrock cannot access S3. The test automatically:
1. Creates S3 buckets
2. Adds Bedrock service access policies
3. Configures proper IAM permissions

If still failing, check your IAM role has:
- `iam:PassRole` permission
- Trust relationship with `bedrock.amazonaws.com`

### Resources Not Cleaned Up

**Manual cleanup:**
```bash
# List resources with test prefix
aws s3 ls | grep test-real-e2e

# Clean up specific resources
python scripts/cleanup_all_resources.py --prefix test-real-e2e-1699632120
```

### Cost Higher Than Expected

**Check:**
1. OpenSearch tests ran (very expensive!)
2. Tests failed and retried multiple times
3. Resources not cleaned up (kept for debugging)

**View actual costs:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=SERVICE
```

## Cost Optimization

### 1. Skip Expensive Tests

```bash
# Always skip OpenSearch tests
export SKIP_EXPENSIVE_TESTS=1
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

### 2. Use Shorter Videos

Tests use a 15-second video by default. For even lower costs:
- Modify `test_video_url` in TestConfig
- Use 5-second clips

### 3. Run Selectively

Don't run full suite every time:
```bash
# Run only what changed
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
```

### 4. Batch Test Runs

Multiple consecutive test runs reuse some resources:
- Test video is downloaded once
- Embeddings can be cached

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Real AWS E2E Tests

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly, Sunday 2 AM
  workflow_dispatch:  # Manual trigger only

jobs:
  real-aws-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'  # Only on main branch
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run Real AWS Tests (no OpenSearch)
        env:
          SKIP_EXPENSIVE_TESTS: 1
          AUTOMATED_TEST: 1
        run: |
          pytest tests/test_real_aws_e2e_workflows.py \
            -v --real-aws -m "not expensive" \
            --junitxml=test-results.xml
      
      - name: Upload Test Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results.xml
```

### Important CI/CD Notes

1. **Never auto-run on every commit** - costs add up quickly!
2. **Use scheduled runs** - weekly or monthly
3. **Skip OpenSearch** - too expensive for CI
4. **Set AUTOMATED_TEST=1** - skips interactive prompts
5. **Monitor costs** - set up AWS budget alerts

## Comparison with Mocked Tests

| Aspect | Mocked Tests | Real AWS Tests |
|--------|-------------|----------------|
| **Cost** | $0.00 | $0.05-5.00 |
| **Duration** | < 1 min | 2-30 min |
| **Reliability** | Mock behavior | Real API behavior |
| **Coverage** | Logic flow | Full integration |
| **When to Run** | Every commit | Weekly/monthly |
| **Purpose** | Unit testing | E2E validation |

## Best Practices

1. **S3Vector-First Testing**
   - Always test S3Vector core functionality first
   - Only test optional backends when doing comparison analysis
   - S3Vector tests require no additional infrastructure

2. **Use Terraform for Optional Backends**
   - Never create optional backend infrastructure via API
   - Always deploy via Terraform: `terraform apply`
   - Verify deployment before running tests: `terraform output`
   - Clean up with: `terraform destroy`

3. **Default to Mocked Tests**
   - Use [`test_e2e_vector_store_workflows.py`](test_e2e_vector_store_workflows.py) for regular development
   - Use real AWS tests for validation only
   - Mocked tests are free and fast

4. **Run Real Tests Sparingly**
   - Before major releases
   - After AWS service updates
   - When mocked tests show discrepancies
   - Weekly/monthly scheduled validation

5. **Monitor Costs**
   - Set up AWS Cost Anomaly Detection
   - Review AWS Cost Explorer regularly
   - Set budget alerts
   - Skip expensive tests in CI: `-m "not expensive"`

6. **Clean Up Properly**
   - S3Vector resources: Use cleanup scripts
   - Optional backends: Use `terraform destroy`
   - Check for orphaned resources weekly
   - Use tagging for easy identification

7. **Document Failures**
   - Real AWS failures may indicate actual bugs
   - Compare with mock test results
   - Update mocks based on real behavior
   - File issues for infrastructure problems

## Support

If you encounter issues:

1. Check logs: Tests log detailed information including errors
2. Review AWS CloudWatch: Real API errors are logged
3. Manual verification: Use AWS Console to inspect resources
4. Cost concerns: Contact AWS Support for billing questions

## License

Same as parent project.