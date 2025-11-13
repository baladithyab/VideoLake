# Videolake Testing Documentation

This directory contains comprehensive tests for the S3Vector-first architecture with optional vector store comparisons.

## Architecture Overview

S3Vector is the **primary backend** with built-in AWS integration. Other vector stores (OpenSearch, Qdrant, LanceDB) are **optional comparison backends** that require Terraform deployment.

### Deployment Modes

- **Mode 1 (S3Vector Only)**: Core functionality, no additional infrastructure needed
- **Mode 2 (Single Optional Backend)**: S3Vector + one comparison backend (deployed via Terraform)
- **Mode 3 (Full Comparison)**: S3Vector + multiple backends for performance comparison (Terraform required)

## Prerequisites

### For S3Vector Tests (Core)
- AWS credentials configured
- S3Vectors service enabled in `us-east-1`
- Bedrock access for embeddings
- No additional infrastructure required

### For Optional Backend Tests
- **Terraform deployment required** - Backends must be deployed before testing
- Run `terraform apply` with appropriate mode configuration
- Verify deployment: `terraform output` shows backend endpoints
- See [`terraform/MIGRATION_GUIDE.md`](../terraform/MIGRATION_GUIDE.md) for deployment instructions

## Test Organization

### Core S3Vector Tests (Primary)

These tests validate S3Vector functionality and require no additional infrastructure:

#### 1. `test_resource_registry_tracking.py`
**Purpose**: Verify S3Vector resource operations are properly logged in the resource registry.

**What it tests**:
- ✅ S3Vector bucket creation and logging
- ✅ S3Vector index creation with correct metadata (ARN, dimensions, distance metric)
- ✅ Resource deletion and status updates
- ✅ Registry JSON file integrity
- ✅ Timestamp and status transition tracking

**Run**:
```bash
python tests/test_resource_registry_tracking.py
```

**Expected Output**:
```
🎉 ALL REGISTRY TRACKING TESTS PASSED!
✅ S3Vector bucket: CREATE logged, DELETE logged
✅ S3Vector index: CREATE logged, DELETE logged
✅ Registry JSON properly updated
✅ Status transitions tracked correctly
✅ Timestamps recorded properly
```

#### 2. `test_e2e_vector_store_workflows.py`
**Purpose**: Core S3Vector end-to-end workflow validation with mocked dependencies.

**What it tests**:
- ✅ Complete S3Vector ingestion and search workflows
- ✅ Video processing and embedding generation
- ✅ Vector storage and retrieval
- ✅ Search query functionality
- ✅ Error handling and recovery

**Run**:
```bash
pytest tests/test_e2e_vector_store_workflows.py -v
```

#### 3. `test_all_resources_clean.py`
**Purpose**: Test S3Vector and S3 bucket lifecycle with clean exit.

**What it tests**:
- ✅ S3Vector bucket and index creation/deletion
- ✅ S3 bucket operations
- ✅ AWS CLI verification
- ✅ ARN generation and validation
- ✅ Clean termination

**Run**:
```bash
python tests/test_all_resources_clean.py
```

**Expected Output**:
```
🎉 ALL TESTS PASSED!
✅ S3Vector resources: CREATE, VERIFY, DELETE
✅ S3 bucket resources: CREATE, VERIFY, DELETE
✅ AWS CLI verification working
✅ ARN generation working
```

#### 4. `final_resource_test.py`
**Purpose**: Comprehensive lifecycle test with detailed AWS CLI verification.

**What it tests**:
- ✅ Complete resource lifecycle (create → verify → delete → verify deletion)
- ✅ Detailed AWS CLI commands for verification
- ✅ ARN output and validation
- ✅ Resource registry integration

**Run**:
```bash
python tests/final_resource_test.py
```

#### 5. `test_resource_lifecycle.py`
**Purpose**: Basic lifecycle test for S3Vector resources.

**What it tests**:
- ✅ S3Vector bucket and index creation
- ✅ AWS CLI verification
- ✅ Resource deletion

**Run**:
```bash
python tests/test_resource_lifecycle.py
```

#### 6. `test_simplified_resource_manager.py`
**Purpose**: Basic functionality test for the SimplifiedResourceManager class.

**What it tests**:
- ✅ Manager initialization
- ✅ AWS client setup
- ✅ Basic resource operations

**Run**:
```bash
python tests/test_simplified_resource_manager.py
```

#### 7. `test_all_resources.py`
**Purpose**: Original comprehensive test (may have threading issues on exit).

**Note**: Use `test_all_resources_clean.py` instead for clean exit.

### Optional Backend Tests (Require Terraform Deployment)

**Prerequisites**: Deploy backends via Terraform before running these tests.

#### 1. `test_real_aws_e2e_workflows.py`
**Purpose**: Test S3Vector with optional comparison backends using real AWS resources.

**What it tests**:
- ✅ S3Vector workflow (primary)
- ✅ OpenSearch workflow (optional, requires Terraform deployment)
- ✅ LanceDB workflow (optional, requires Terraform deployment)
- ✅ Qdrant workflow (optional, requires Terraform deployment)
- ✅ Performance comparison across backends

**Prerequisites**:
- Deploy backends: `terraform apply -var="deployment_mode=mode3"`
- Verify deployment: `terraform output`
- See [`README_REAL_AWS_TESTS.md`](README_REAL_AWS_TESTS.md) for details

**Cost**: $0.05-$5 depending on backends tested (⚠️ OpenSearch is expensive!)

**Run**:
```bash
# Core S3Vector only (no extra cost)
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws

# With optional backends (requires Terraform deployment)
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

### Integration Tests

#### 1. `test_aws_service_integrations.py`
**Purpose**: Validate AWS service integration with S3Vector and Bedrock.

**What it tests**:
- ✅ S3Vector API integration
- ✅ Bedrock embedding generation
- ✅ S3 bucket operations
- ✅ IAM permissions and policies

#### 2. `conftest.py`
**Purpose**: Shared test fixtures and configuration for pytest.

**Provides**:
- S3Vector client fixtures
- Mock AWS service fixtures
- Test data generators
- Cleanup utilities

## Resource Registry

The resource registry is located at `coordination/resource_registry.json` and tracks:

- **S3Vector Buckets**: Name, region, encryption, status, timestamps
- **S3Vector Indexes**: Name, bucket, ARN, dimensions, distance metric, status, timestamps
- **S3 Buckets**: Name, region, status, timestamps
- **OpenSearch Collections**: (future)
- **OpenSearch Domains**: (future)

### Registry Entry Example

**S3Vector Bucket**:
```json
{
  "name": "registry-test-bucket-1759185777",
  "region": "us-west-2",
  "encryption": "SSE-S3",
  "kms_key_arn": null,
  "source": "ui",
  "status": "deleted",
  "created_at": "2025-09-29T22:42:57.685479+00:00",
  "deleted_at": "2025-09-29T22:42:57.803001+00:00"
}
```

**S3Vector Index**:
```json
{
  "bucket": "registry-test-bucket-1759185778",
  "name": "registry-test-index-1759185778",
  "arn": "arn:aws:s3vectors:us-west-2:386931836011:bucket/registry-test-bucket-1759185778/index/registry-test-index-1759185778",
  "dimensions": 1536,
  "distance_metric": "cosine",
  "source": "ui",
  "status": "deleted",
  "created_at": "2025-09-29T22:42:58.334123+00:00",
  "deleted_at": "2025-09-29T22:42:58.451661+00:00"
}
```

## Running Tests

### Quick Start - Core S3Vector Tests

```bash
# Run all core S3Vector tests (no additional infrastructure needed)
pytest tests/ -v -m "not expensive"

# Run specific core test suites
pytest tests/test_e2e_vector_store_workflows.py -v
pytest tests/test_resource_registry_tracking.py -v
pytest tests/test_all_resources_clean.py -v
```

### Running Optional Backend Tests

**Prerequisites**: Deploy backends via Terraform first!

```bash
# Step 1: Deploy optional backends
cd terraform
terraform apply -var="deployment_mode=mode2"  # Or mode3 for full comparison

# Step 2: Verify deployment
terraform output

# Step 3: Run tests with deployed backends
cd ..
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

### Test Organization by Priority

**Tier 1 - Core Functionality (Run Always)**:
```bash
pytest tests/test_e2e_vector_store_workflows.py -v
pytest tests/test_resource_registry_tracking.py -v
```

**Tier 2 - Extended Validation (Run Pre-Release)**:
```bash
pytest tests/test_all_resources_clean.py -v
pytest tests/test_aws_service_integrations.py -v
```

**Tier 3 - Real AWS Integration (Run Weekly/Monthly)**:
```bash
# Requires Terraform deployment + costs money
pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

## Test Categories

### By Backend Type

**S3Vector Only (Core)**:
- All tests in Tier 1 and Tier 2
- No additional infrastructure required
- Free/minimal AWS costs

**Optional Backends (Comparison)**:
- Requires Terraform deployment
- Tests in `test_real_aws_e2e_workflows.py`
- Costs vary by backend (OpenSearch is expensive!)

### By Deployment Mode

**Mode 1 Tests (S3Vector Only)**:
```bash
pytest tests/test_e2e_vector_store_workflows.py::TestS3VectorWorkflow -v
```

**Mode 2 Tests (S3Vector + One Backend)**:
```bash
# Requires: terraform apply -var="deployment_mode=mode2"
pytest tests/test_real_aws_e2e_workflows.py::TestRealS3VectorWorkflow -v --real-aws
pytest tests/test_real_aws_e2e_workflows.py::TestRealLanceDBWorkflow -v --real-aws
```

**Mode 3 Tests (Full Comparison)**:
```bash
# Requires: terraform apply -var="deployment_mode=mode3"
pytest tests/test_real_aws_e2e_workflows.py::TestRealProviderComparison -v --real-aws
```

## Troubleshooting

### Threading Issues
If you encounter threading lock issues on exit, use the `_clean.py` versions of tests which use `os._exit()` for clean termination.

### Region Mismatch
The S3Vectors client uses `us-east-1` by default. Make sure to specify `--region us-east-1` when using AWS CLI commands for S3Vector resources.

### Registry Not Updating
If the registry isn't updating, check:
1. File permissions on `coordination/resource_registry.json`
2. The resource registry is being imported correctly
3. The log methods are being called after resource operations

## AWS CLI Verification Commands

### S3Vector Resources
```bash
# List all S3Vector buckets
aws s3vectors list-vector-buckets --region us-east-1

# Get bucket details
aws s3vectors get-vector-bucket --vector-bucket-name <bucket-name> --region us-east-1

# List indexes
aws s3vectors list-indexes --vector-bucket-name <bucket-name> --region us-east-1

# Get index details
aws s3vectors get-index --vector-bucket-name <bucket-name> --index-name <index-name> --region us-east-1
```

### S3 Buckets
```bash
# List bucket contents
aws s3 ls s3://<bucket-name>

# Get bucket location
aws s3api get-bucket-location --bucket <bucket-name>
```

## Contributing

When adding new tests:
1. Follow the existing naming convention: `test_<feature>.py`
2. Use `os._exit()` for clean termination
3. Include comprehensive error handling
4. Add AWS CLI verification where applicable
5. Update this README with test description

## Best Practices

### For Core S3Vector Development

1. **Run mocked tests frequently** - Fast, no AWS costs
2. **Use pytest markers** - Skip expensive tests: `-m "not expensive"`
3. **Check resource registry** - Verify all operations logged
4. **Clean up resources** - Use `scripts/cleanup_all_resources.py` if needed

### For Optional Backend Testing

1. **Deploy via Terraform first** - Never create resources via API
2. **Verify deployment** - Check `terraform output` before running tests
3. **Start with S3Vector** - Validate core functionality first
4. **Skip expensive backends** - OpenSearch costs $1+/hour!
5. **Clean up after testing** - Run `terraform destroy` when done

### For CI/CD

1. **Core tests on every commit** - S3Vector mocked tests only
2. **Integration tests pre-release** - Include Terraform-deployed backends
3. **Skip expensive tests in CI** - Use `-m "not expensive"` marker
4. **Weekly real AWS validation** - Full test suite on schedule only

## Terraform-First Approach

### Creating Test Infrastructure

**✅ CORRECT - Use Terraform**:
```bash
cd terraform
terraform apply -var="deployment_mode=mode2"
```

**❌ INCORRECT - Don't use API directly**:
```python
# This is deprecated!
manager.create_opensearch_collection(...)
manager.create_qdrant_cluster(...)
```

### Why Terraform-First?

1. **Infrastructure as Code** - Reproducible deployments
2. **State Management** - Track all resources properly
3. **Dependency Management** - Correct resource creation order
4. **Cost Control** - Predictable infrastructure costs
5. **Production Parity** - Test infrastructure matches production

### When to Use Each Approach

**Terraform for**:
- Optional backend deployment (OpenSearch, Qdrant, LanceDB)
- Production infrastructure
- Long-lived test environments
- Infrastructure validation

**Python API for**:
- S3Vector operations (primary backend)
- Test data generation
- Temporary test resources
- Quick validation scripts

## Notes

- All tests create temporary resources with unique timestamps
- Automatic cleanup runs even if tests fail
- Registry entries persist as 'deleted' (not removed)
- S3Vector requires no configuration - works out of the box
- Optional backends require Terraform deployment before testing
- Deprecated: Direct API-based resource creation for optional backends
- Deprecated: Streamlit-specific test references

