# Real AWS Tests - Quick Start Guide

⚠️ **These tests use REAL AWS resources and will incur costs!**

## TL;DR - Run Tests Safely

```bash
# 1. Set up environment
export AWS_REGION=us-east-1

# 2. Check prerequisites (no cost)
pytest tests/test_real_aws_e2e_workflows.py --collect-only

# 3. Run tests with safety script (recommended)
python scripts/run_real_aws_tests.py --skip-expensive

# 4. OR run pytest directly with confirmation
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

## Estimated Costs

| Test Suite | Cost | Time |
|------------|------|------|
| **Without OpenSearch** | $0.05-0.10 | 10 min |
| **With OpenSearch** | $2-5 | 20-30 min |
| **Single Test** | $0.01-0.02 | 2-5 min |

## Prerequisites

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

## Quick Commands

### Safe Execution (Recommended)

```bash
# Use the safety script - handles everything
python scripts/run_real_aws_tests.py --skip-expensive
```

### Run Specific Tests

```bash
# S3Vector workflow only (~$0.02, 3 min)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Performance comparison (~$0.05, 5 min)
pytest tests/test_real_aws_e2e_workflows.py::TestRealProviderComparison -v --real-aws

# Error handling (cheapest, ~$0.01, 1 min)
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

### Keep Resources for Debugging

```bash
KEEP_TEST_RESOURCES=1 pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Clean up manually after debugging
python scripts/cleanup_all_resources.py --prefix test-real-e2e
```

## What Gets Created

During tests, these AWS resources are created:
- ✅ S3 buckets (for videos and vectors)
- ✅ S3 Vector indexes
- ✅ Test video uploads
- ✅ Bedrock API calls (TwelveLabs video processing)
- ⚠️ OpenSearch collections (if expensive tests enabled)

**All resources are automatically cleaned up!**

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
```bash
# Always skip expensive tests
export SKIP_EXPENSIVE_TESTS=1

# Run only what you need
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws

# Use safety script (built-in cost warnings)
python scripts/run_real_aws_tests.py --skip-expensive
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

✅ **Run for:**
- Pre-release validation
- After AWS service updates
- Investigating real API behavior
- Performance benchmarking

❌ **Don't run for:**
- Regular development (use mocked tests)
- Every commit (too expensive)
- CI/CD on every PR (cost adds up)

## More Information

- Full documentation: [`tests/README_REAL_AWS_TESTS.md`](tests/README_REAL_AWS_TESTS.md)
- Mocked E2E tests: [`tests/test_e2e_vector_store_workflows.py`](tests/test_e2e_vector_store_workflows.py)
- Cleanup script: [`scripts/cleanup_all_resources.py`](scripts/cleanup_all_resources.py)

## Support

Questions or issues? Check:
1. Full README: `tests/README_REAL_AWS_TESTS.md`
2. AWS CloudWatch logs
3. Test output logs (very detailed)