# S3Vector Testing Guide

## Overview

This testing guide covers the comprehensive testing strategy for the S3Vector-first architecture with optional vector store comparison capabilities. The testing approach ensures reliability, performance, and proper integration across all components.

## Test Architecture

### S3Vector-First Philosophy

**S3Vector is the primary backend** - All core functionality tests target S3Vector as the default vector store with built-in AWS integration.

**Optional backends** (OpenSearch, Qdrant, LanceDB) are **comparison backends only**, used for performance benchmarking and architectural validation. These require Terraform deployment before testing.

### Testing Pyramid

```
         /\
        /E2E\      <- End-to-End Integration Tests
       /------\     (S3Vector + Optional Backend Workflows)
      /  Unit  \   <- Unit Tests & Component Tests
     /----------\   (S3Vector Operations, Service Integration)
    / Core Tests \ <- S3Vector Core Functionality
   /--------------\ (Primary backend, no infrastructure required)
```

## Test Suite Components

### 1. Core S3Vector Tests (Primary)

**Location**: [`tests/test_e2e_vector_store_workflows.py`](../tests/test_e2e_vector_store_workflows.py)

**Purpose**: Validate S3Vector core functionality with mocked dependencies

**Infrastructure Required**: None (S3Vector is built-in)

**Key Test Classes**:
- `TestS3VectorWorkflow`: Complete ingestion and search workflows
- `TestS3VectorIndexManagement`: Index creation and management
- `TestS3VectorEmbedding`: Embedding storage and retrieval
- `TestS3VectorSearch`: Search query functionality

**Coverage Requirements**:
- S3Vector operations: >90%
- Core workflows: 100%
- Error handling: >85%

**Run**:
```bash
pytest tests/test_e2e_vector_store_workflows.py -v
```

### 2. Optional Backend Tests (Comparison Only)

**Location**: [`tests/test_real_aws_e2e_workflows.py`](../tests/test_real_aws_e2e_workflows.py)

**Purpose**: Test S3Vector against optional backends for comparison

**Infrastructure Required**: Terraform deployment

**Prerequisites**:
```bash
cd terraform
terraform apply -var="deployment_mode=mode2"  # or mode3
terraform output  # Verify deployment
```

**Key Test Classes**:
- `TestRealS3VectorWorkflow`: S3Vector with real AWS (primary)
- `TestRealLanceDBWorkflow`: LanceDB comparison (optional)
- `TestRealQdrantWorkflow`: Qdrant comparison (optional)
- `TestRealOpenSearchWorkflow`: OpenSearch comparison (optional, expensive!)
- `TestRealProviderComparison`: Cross-backend performance analysis

**Cost Estimates**:
- S3Vector tests: $0.01-0.02 (no infrastructure)
- LanceDB tests: $0.01 (if deployed)
- Qdrant tests: $0.02-0.05 (if deployed)
- OpenSearch tests: $1.00+/hour ⚠️ (if deployed)

**Run**:
```bash
# Core S3Vector only (no infrastructure needed)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# With optional backends (requires Terraform deployment)
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

### 3. Integration Tests

**Location**: [`tests/test_aws_service_integrations.py`](../tests/test_aws_service_integrations.py)

**Purpose**: Validate AWS service integration

**What it tests**:
- S3Vector API integration
- Bedrock embedding generation
- S3 bucket operations
- IAM permissions and policies

**Run**:
```bash
pytest tests/test_aws_service_integrations.py -v
```

### 4. Resource Management Tests

**Location**: [`tests/test_resource_registry_tracking.py`](../tests/test_resource_registry_tracking.py)

**Purpose**: Verify resource tracking and registry updates

**What it tests**:
- S3Vector resource creation logging
- Resource deletion tracking
- Registry JSON integrity
- Status transitions

**Run**:
```bash
python tests/test_resource_registry_tracking.py
```

## Test Infrastructure

### Test Fixtures (`conftest.py`)

**Location**: [`tests/conftest.py`](../tests/conftest.py)

**Provides**:
- S3Vector client fixtures
- Mock AWS service fixtures
- Test data generators
- Cleanup utilities
- Pytest configuration

### Mock Strategy

**Always Mock**:
- External API calls (TwelveLabs, Bedrock)
- File system operations
- Network requests
- Time-dependent operations

**Never Mock** (for real AWS tests):
- S3Vector operations (primary backend)
- S3 bucket operations
- AWS service interactions

## Running Tests

### Development Testing (Daily)

Run core S3Vector tests with mocks:

```bash
# All core tests
pytest tests/test_e2e_vector_store_workflows.py -v

# Specific workflow
pytest tests/test_e2e_vector_store_workflows.py::TestS3VectorWorkflow -v

# With coverage
pytest tests/test_e2e_vector_store_workflows.py --cov=src --cov-report=html
```

### Pre-Release Validation (Weekly)

Run real AWS tests for S3Vector:

```bash
# Core S3Vector validation
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# Error handling
pytest tests/test_real_aws_e2e_workflows.py::TestRealErrorHandling -v --real-aws
```

**Cost**: ~$0.02-0.05, **Duration**: 5 minutes

### Backend Comparison Testing (Monthly/As Needed)

**Prerequisites**: Deploy optional backends via Terraform first!

```bash
# Step 1: Deploy backends
cd terraform
terraform apply -var="deployment_mode=mode2"  # or mode3

# Step 2: Verify deployment
terraform output

# Step 3: Run comparison tests
cd ..
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"

# Step 4: Performance comparison
pytest tests/test_real_aws_e2e_workflows.py::TestRealProviderComparison -v --real-aws

# Step 5: Clean up
cd terraform
terraform destroy
```

**Cost**: $0.05-0.10 (without OpenSearch), **Duration**: 10-15 minutes

### CI/CD Integration

**On Every Commit**:
```bash
# Fast, mocked core tests only
pytest tests/test_e2e_vector_store_workflows.py -v -m "not expensive"
```

**Weekly Scheduled**:
```bash
# Real AWS validation (S3Vector core only)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
```

**Pre-Release**:
```bash
# Full test suite with optional backends (requires Terraform)
# Run after: terraform apply -var="deployment_mode=mode2"
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

## Test Organization by Deployment Mode

### Mode 1: S3Vector Only

**Tests**:
- Core S3Vector workflows (mocked)
- Real AWS S3Vector validation
- Resource management
- Integration tests

**Commands**:
```bash
pytest tests/test_e2e_vector_store_workflows.py::TestS3VectorWorkflow -v
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
```

**Infrastructure**: None required

### Mode 2: S3Vector + One Optional Backend

**Prerequisites**:
```bash
terraform apply -var="deployment_mode=mode2" -var="primary_backend=lancedb"
```

**Tests**:
- All Mode 1 tests
- Optional backend workflow (LanceDB or Qdrant)
- Limited comparison tests

**Commands**:
```bash
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
pytest tests/test_real_aws_e2e_workflows.py::TestRealLanceDBWorkflow -v --real-aws
```

### Mode 3: Full Comparison

**Prerequisites**:
```bash
terraform apply -var="deployment_mode=mode3"
```

**Tests**:
- All Mode 1 and Mode 2 tests
- All optional backends (including expensive OpenSearch)
- Full performance comparison

**Commands**:
```bash
# Without OpenSearch (recommended)
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"

# With OpenSearch (expensive!)
SKIP_EXPENSIVE_TESTS=0 pytest tests/test_real_aws_e2e_workflows.py -v --real-aws
```

## Success Criteria

### Core S3Vector Tests (Required)
- ✅ Success rate: >95%
- ✅ All S3Vector workflows tested
- ✅ Performance: <5s for core operations
- ✅ Memory usage: <100MB for mocked tests

### Optional Backend Tests (When Needed)
- ✅ Terraform deployment successful
- ✅ Backend connectivity validated
- ✅ Comparison metrics collected
- ✅ Clean teardown via `terraform destroy`

### Integration Tests
- ✅ AWS service integration working
- ✅ Resource tracking accurate
- ✅ Error handling comprehensive

## Best Practices

### 1. S3Vector-First Development

- Always test S3Vector functionality first
- Use mocked tests for rapid development
- Only test optional backends for comparison needs
- S3Vector requires no infrastructure setup

### 2. Terraform-First Infrastructure

**✅ CORRECT**:
```bash
cd terraform
terraform apply -var="deployment_mode=mode2"
terraform output
# Then run tests
```

**❌ INCORRECT**:
```python
# Don't create infrastructure via API
manager.create_opensearch_collection(...)
manager.create_qdrant_cluster(...)
```

### 3. Cost-Conscious Testing

- Run S3Vector mocked tests frequently (free)
- Run real S3Vector tests weekly ($0.02-0.05)
- Run optional backend tests monthly ($0.05-0.10)
- Skip OpenSearch tests unless absolutely necessary ($1+/hour)

### 4. Test Isolation

- Each test creates uniquely named resources
- Automatic cleanup via fixtures
- No shared state between tests
- Independent test execution

### 5. CI/CD Strategy

**Every Commit**:
- Core S3Vector mocked tests
- Fast (<1 minute)
- No AWS costs

**Weekly Schedule**:
- Real AWS S3Vector validation
- ~$0.05 cost
- 5-10 minutes

**Pre-Release**:
- Full test suite with Terraform-deployed backends
- ~$0.10 cost (skip OpenSearch)
- 15-20 minutes

## Troubleshooting

### Test Failures

**S3Vector Tests Failing**:
1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify region: `echo $AWS_REGION`
3. Check S3Vectors service: `aws s3vectors list-vector-buckets --region us-east-1`

**Optional Backend Tests Failing**:
1. Verify Terraform deployment: `terraform output`
2. Check backend connectivity
3. Ensure backends are healthy
4. Review deployment logs

### Cost Issues

**Unexpected Costs**:
1. Check if OpenSearch tests ran
2. Verify resources were cleaned up
3. Check `terraform state` for orphaned resources
4. Review AWS Cost Explorer

**Cleanup**:
```bash
# S3Vector resources
python scripts/cleanup_all_resources.py --prefix test-real-e2e

# Terraform-deployed backends
cd terraform && terraform destroy
```

### Performance Issues

**Slow Tests**:
1. Use mocked tests for development
2. Run real AWS tests selectively
3. Check network connectivity
4. Verify AWS service health

## Documentation References

- **Main Test README**: [`tests/README.md`](../tests/README.md)
- **Real AWS Tests Guide**: [`tests/README_REAL_AWS_TESTS.md`](../tests/README_REAL_AWS_TESTS.md)
- **Quick Start**: [`tests/REAL_AWS_TESTS_QUICKSTART.md`](../tests/REAL_AWS_TESTS_QUICKSTART.md)
- **Terraform Guide**: [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md)

## Maintenance

### Regular Updates

1. **Monthly**: Review test data and fixtures
2. **Quarterly**: Update cost estimates
3. **Semi-annually**: Performance baseline updates
4. **Annually**: Complete test strategy review

### Test Data Refresh

Keep test data current with production patterns:
- Update sample videos
- Refresh embedding dimensions
- Update mock responses
- Review test coverage

## Conclusion

This testing strategy ensures the S3Vector-first architecture is:
- **Reliable**: Through comprehensive S3Vector core testing
- **Performant**: Via optional backend comparison when needed
- **Cost-Effective**: By focusing on S3Vector with minimal infrastructure
- **Maintainable**: With clear test organization and Terraform-first approach

The testing approach prioritizes S3Vector as the primary backend while allowing optional backend testing for comparison and validation purposes.