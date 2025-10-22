# S3Vector Resource Management Tests

This directory contains comprehensive tests for the Simplified Resource Manager and resource registry tracking.

## Test Files

### 1. `test_resource_registry_tracking.py`
**Purpose**: Verify that all resource operations are properly logged in the resource registry JSON file.

**What it tests**:
- ✅ S3Vector bucket creation is logged with correct metadata
- ✅ S3Vector bucket deletion updates status to 'deleted'
- ✅ S3Vector index creation is logged with ARN, dimensions, and distance metric
- ✅ S3Vector index deletion updates status to 'deleted'
- ✅ Registry JSON file is properly updated
- ✅ Timestamps are recorded correctly
- ✅ Status transitions are tracked

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

### 2. `test_all_resources_clean.py`
**Purpose**: Test all resource types (S3Vector buckets, indexes, S3 buckets) with clean exit (no threading issues).

**What it tests**:
- ✅ S3Vector bucket creation and deletion
- ✅ S3Vector index creation and deletion
- ✅ S3 bucket creation and deletion
- ✅ AWS CLI verification for all resources
- ✅ ARN generation and validation
- ✅ Clean exit without threading issues

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

### 3. `final_resource_test.py`
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

### 4. `test_resource_lifecycle.py`
**Purpose**: Basic lifecycle test for S3Vector resources.

**What it tests**:
- ✅ S3Vector bucket and index creation
- ✅ AWS CLI verification
- ✅ Resource deletion

**Run**:
```bash
python tests/test_resource_lifecycle.py
```

### 5. `test_simplified_resource_manager.py`
**Purpose**: Basic functionality test for the SimplifiedResourceManager class.

**What it tests**:
- ✅ Manager initialization
- ✅ AWS client setup
- ✅ Basic resource operations

**Run**:
```bash
python tests/test_simplified_resource_manager.py
```

### 6. `test_all_resources.py`
**Purpose**: Original comprehensive test (may have threading issues on exit).

**Note**: Use `test_all_resources_clean.py` instead for clean exit.

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

## Running All Tests

To run all tests sequentially:

```bash
# Test registry tracking
python tests/test_resource_registry_tracking.py

# Test all resource types
python tests/test_all_resources_clean.py

# Test complete lifecycle
python tests/final_resource_test.py
```

## Test Results Summary

All tests are passing:

| Test | Status | Description |
|------|--------|-------------|
| Registry Tracking | ✅ PASS | All operations logged correctly |
| S3Vector Resources | ✅ PASS | Create, verify, delete working |
| S3 Buckets | ✅ PASS | Create, verify, delete working |
| AWS CLI Verification | ✅ PASS | All resources verifiable |
| ARN Generation | ✅ PASS | Proper ARN format |
| Clean Exit | ✅ PASS | No threading issues |

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

## Notes

- All tests create temporary resources with timestamps in the name
- Tests automatically clean up resources after completion
- Emergency cleanup is included in exception handlers
- Registry entries are never deleted, only marked as 'deleted'
- All tests suppress Streamlit warnings with `STREAMLIT_SERVER_HEADLESS='true'`

