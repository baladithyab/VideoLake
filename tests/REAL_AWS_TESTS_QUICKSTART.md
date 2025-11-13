# Real AWS Tests - Quick Start Guide

⚠️ **These tests use REAL AWS resources and will incur costs!**

## TL;DR - S3Vector-First Testing

### Phase 1: Core S3Vector Tests (No Infrastructure Setup)

```bash
# 1. Set up environment
export AWS_REGION=us-east-1

# 2. Check prerequisites (no cost)
pytest tests/test_real_aws_e2e_workflows.py --collect-only

# 3. Run S3Vector tests (primary backend, no extra infrastructure)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
```

**Cost**: ~$0.02, **Duration**: 3-5 minutes, **Infrastructure**: None required

### Phase 2: Optional Backend Tests (Requires Terraform)

Only if you need backend comparison testing:

```bash
# 1. Deploy optional backends via Terraform
cd terraform
terraform apply -var="deployment_mode=mode2"  # Or mode3 for full comparison

# 2. Verify deployment
terraform output

# 3. Run tests with optional backends
cd ..
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"

# 4. Clean up when done
cd terraform && terraform destroy
```

## Estimated Costs

| Test Suite | Cost | Time | Infrastructure Required |
|------------|------|------|------------------------|
| **S3Vector Only (Core)** | $0.02-0.05 | 5 min | None (built-in) |
| **With Optional Backends** | $0.05-0.10 | 10 min | Terraform deployment |
| **With OpenSearch** | $2-5 | 20-30 min | Mode 3 Terraform deployment |
| **Single S3Vector Test** | $0.01-0.02 | 2-5 min | None |

## Prerequisites

### For S3Vector Tests (Core - Always Required)

1. **AWS Credentials**: Configured and working
   ```bash
   aws sts get-caller-identity  # Should succeed
   ```

2. **Supported Region**: us-east-1 or us-west-2
   ```bash
   export AWS_REGION=us-east-1
   ```

3. **Python Packages**: pytest, boto3, requests
   ```bash
   pip install pytest boto3 requests
   ```

**Note**: S3Vector tests work immediately - no additional infrastructure setup required!

### For Optional Backend Tests (Only if Needed)

1. **Terraform Installed**: Version 1.0+
   ```bash
   terraform --version
   ```

2. **Deploy Backends**:
   ```bash
   cd terraform
   terraform apply -var="deployment_mode=mode2"  # Or mode3
   ```

3. **Verify Deployment**:
   ```bash
   terraform output  # Should show backend endpoints
   ```

See [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md) for detailed instructions.

## Quick Commands

### Core S3Vector Tests (Start Here)

```bash
# S3Vector workflow (primary backend, no infrastructure setup)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Error handling (cheapest test)
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

**Cost**: ~$0.02-0.05, **Infrastructure**: None required

### Optional Backend Tests (Requires Terraform First!)

```bash
# Step 1: Deploy backends
cd terraform && terraform apply -var="deployment_mode=mode2"

# Step 2: Verify deployment
terraform output

# Step 3: Run optional backend tests
cd .. && pytest tests/test_real_aws_e2e_workflows.py::TestRealLanceDBWorkflow -v --real-aws

# Step 4: Clean up
cd terraform && terraform destroy
```

### Performance Comparison (Requires Deployed Backends)

```bash
# Requires Mode 2 or Mode 3 deployment
pytest tests/test_real_aws_e2e_workflows.py::TestRealProviderComparison -v --real-aws
```

### Keep Resources for Debugging

For S3Vector resources:
```bash
KEEP_TEST_RESOURCES=1 pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Clean up manually
python scripts/cleanup_all_resources.py --prefix test-real-e2e
```

For Terraform-deployed backends:
```bash
# Don't run terraform destroy until debugging is complete
```

## What Gets Created

### Core S3Vector Tests
- ✅ S3 buckets (for videos and vectors)
- ✅ S3 Vector indexes (native AWS service)
- ✅ Test video uploads
- ✅ Bedrock API calls (video processing)

**Infrastructure Required**: None - S3Vector is built-in!
**Cleanup**: Automatic via test fixtures

### Optional Backend Tests (If Deployed via Terraform)
- ⚠️ OpenSearch Serverless collections (Mode 3 only, very expensive!)
- ✅ Qdrant clusters (Mode 2/3)
- ✅ LanceDB S3 buckets (Mode 2/3)

**Infrastructure Required**: Terraform deployment
**Cleanup**: Run `terraform destroy`

## Safety Features

✅ Requires `--real-aws` flag (won't run accidentally)  
✅ Interactive cost warnings  
✅ Automatic resource cleanup (even if tests fail)  
✅ Unique resource names (no conflicts)  
✅ Skip expensive tests by default  
✅ Detailed cost logging

## Troubleshooting

### "Prerequisites not met"
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check region
echo $AWS_REGION

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### "Tests skipped"
You need the `--real-aws` flag:
```bash
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws
```

### Resources not cleaned up
```bash
# List orphaned resources
aws s3 ls | grep test-real-e2e

# Clean up manually
python scripts/cleanup_all_resources.py --prefix test-real-e2e
```

## Cost Control

### Minimize Costs

**For S3Vector Tests (Always Cheap)**:
```bash
# Run core S3Vector tests only (~$0.02)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

**For Optional Backend Tests**:
```bash
# Skip expensive tests (no OpenSearch)
export SKIP_EXPENSIVE_TESTS=1
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"

# Use Terraform destroy immediately after testing
cd terraform && terraform destroy
```

### Monitor Costs
```bash
# View AWS costs
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity DAILY \
  --metrics UnblendedCost
```

## When to Run These Tests

### S3Vector Tests (Core)

✅ **Run for:**
- Validating S3Vector core functionality
- Pre-release validation
- After AWS S3Vectors service updates
- Investigating S3Vector-specific issues

✅ **Safe to run:**
- Weekly/monthly scheduled validation
- Before major releases
- When troubleshooting S3Vector bugs

### Optional Backend Tests (Comparison)

✅ **Run for:**
- Performance comparison analysis
- Backend selection decisions
- Architecture validation
- Comprehensive benchmarking

❌ **Don't run for:**
- Regular development (use mocked tests)
- Every commit (infrastructure overhead + costs)
- CI/CD on every PR (too expensive)
- S3Vector-only features (no comparison needed)

## More Information

- **Full documentation**: [`tests/README_REAL_AWS_TESTS.md`](README_REAL_AWS_TESTS.md)
- **Terraform deployment**: [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md)
- **Mocked E2E tests**: [`tests/test_e2e_vector_store_workflows.py`](test_e2e_vector_store_workflows.py)
- **Cleanup script**: [`scripts/cleanup_all_resources.py`](../scripts/cleanup_all_resources.py)
- **Architecture overview**: [`tests/README.md`](README.md)

## Support

Questions or issues? Check:
1. Full README: `tests/README_REAL_AWS_TESTS.md`
2. AWS CloudWatch logs
3. Test output logs (very detailed)