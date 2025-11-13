# Resource Testing Guide

## Overview

This guide explains how to test the complete AWS resource lifecycle for the Videolake application. All tests use **REAL AWS API calls** - no mocks or simulations.

## Required Resources

The Videolake application requires these AWS resources:

1. **S3 Bucket** - For storing uploaded media files (videos, images, audio)
2. **S3Vector Bucket** - For storing vector indices
3. **S3Vector Index** - For storing embeddings (created empty, populated after media processing)
4. **OpenSearch Domain** - For hybrid search with S3Vector backend (optional but recommended)

## Test Scripts

### 1. Complete Resource Workflow Test

**File:** `tests/test_complete_resource_workflow.py`

**Purpose:** Tests the complete lifecycle of creating and deleting all required AWS resources.

**Usage:**

```bash
# Quick test (skip OpenSearch domain - saves 10-15 minutes)
python tests/test_complete_resource_workflow.py --skip-opensearch

# Full test with OpenSearch domain (takes 10-15 minutes)
python tests/test_complete_resource_workflow.py --wait-for-opensearch

# Full test without waiting for OpenSearch to become active
python tests/test_complete_resource_workflow.py

# Cleanup only (delete existing test resources)
python tests/test_complete_resource_workflow.py --cleanup-only
```

**What it tests:**

1. ✅ AWS connectivity and credentials
2. ✅ S3 bucket creation and deletion
3. ✅ S3Vector bucket creation and deletion
4. ✅ S3Vector index creation and deletion (1536 dimensions for Marengo 2.7)
5. ✅ OpenSearch domain creation and deletion (with S3Vector backend)
6. ✅ Resource verification via AWS API
7. ✅ Resource registry tracking

**Expected Output:**

```
======================================================================
🧪 COMPLETE RESOURCE WORKFLOW TEST
======================================================================

✅ S3 Bucket: Created and Deleted
✅ S3Vector Bucket: Created and Deleted
✅ S3Vector Index: Created and Deleted
✅ OpenSearch Domain: Created and Deletion Initiated

✅ All resources are working correctly with REAL AWS API calls
✅ No mocks or simulations were used
```

### 2. Simplified Resource Manager Test

**File:** `tests/test_simplified_resource_manager.py`

**Purpose:** Tests the SimplifiedResourceManager component used by the frontend.

**Usage:**

```bash
python tests/test_simplified_resource_manager.py
```

**What it tests:**

1. ✅ AWS client initialization
2. ✅ S3Vector bucket creation
3. ✅ S3Vector index creation
4. ✅ Resource verification
5. ✅ Resource deletion

### 3. Cleanup All Resources Script

**File:** `scripts/cleanup_all_resources.py`

**Purpose:** Cleans up all resources tracked in the resource registry.

**Usage:**

```bash
# Dry run (show what would be deleted)
python scripts/cleanup_all_resources.py --dry-run

# Delete all active resources
python scripts/cleanup_all_resources.py

# Delete resources and purge deleted entries from registry
python scripts/cleanup_all_resources.py --purge-deleted

# Force deletion without confirmation
python scripts/cleanup_all_resources.py --force
```

**What it does:**

1. Reads the resource registry
2. Checks which resources actually exist in AWS
3. Deletes all active resources in the correct order:
   - S3Vector indexes (must be deleted before buckets)
   - S3Vector buckets
   - S3 buckets (empties first, then deletes)
   - OpenSearch domains
4. Updates registry to mark resources as deleted
5. Optionally purges deleted entries from registry

## Resource Registry

**File:** `coordination/resource_registry.json`

The resource registry tracks all created resources with:

- Resource names and ARNs
- Creation timestamps
- Status (created/deleted)
- Deletion timestamps
- Source (ui/test/service)

**Example:**

```json
{
  "vector_buckets": [
    {
      "name": "s3vector-1759187028-vector-bucket",
      "region": "us-west-2",
      "status": "created",
      "created_at": "2025-09-29T23:03:48.548076+00:00"
    }
  ]
}
```

## Verification Commands

After creating resources, verify them with AWS CLI:

```bash
# List S3Vector buckets
aws s3vectors list-vector-buckets --region us-west-2

# Get specific S3Vector bucket
aws s3vectors get-vector-bucket --vector-bucket-name <bucket-name> --region us-west-2

# List indexes in bucket
aws s3vectors list-indexes --vector-bucket-name <bucket-name> --region us-west-2

# Get specific index
aws s3vectors get-index --vector-bucket-name <bucket-name> --index-name <index-name> --region us-west-2

# List S3 buckets
aws s3 ls

# Check S3 bucket
aws s3 ls s3://<bucket-name>

# Describe OpenSearch domain
aws opensearch describe-domain --domain-name <domain-name> --region us-west-2
```

## Important Notes

### 1. Real AWS Resources

All tests create **REAL AWS resources** that incur costs:

- **S3 Buckets**: Minimal cost (storage only)
- **S3Vector Buckets**: Minimal cost (storage only)
- **OpenSearch Domains**: ~$0.10/hour for or1.medium.search instance

**Always clean up resources after testing!**

### 2. OpenSearch Domain Creation Time

OpenSearch domains take **10-15 minutes** to become active:

- Use `--skip-opensearch` for quick tests
- Use `--wait-for-opensearch` to wait for domain to become active
- Without `--wait-for-opensearch`, domain creation is initiated but not waited for

### 3. Resource Naming

Test resources use timestamped names to avoid conflicts:

- Format: `test-workflow-{timestamp}-{resource-type}`
- Example: `test-workflow-1759659388-vectors`

### 4. Cleanup Order

Resources must be deleted in the correct order:

1. S3Vector indexes (must be deleted before buckets)
2. S3Vector buckets
3. S3 buckets (must be emptied first)
4. OpenSearch domains

### 5. Region Configuration

Default region is `us-west-2`. To use a different region:

1. Set AWS_DEFAULT_REGION environment variable
2. Or configure in `~/.aws/config`

## Troubleshooting

### Test Fails with "Access Denied"

**Solution:** Ensure your AWS credentials have the required permissions:

- `s3:*` for S3 operations
- `s3vectors:*` for S3Vector operations
- `es:*` for OpenSearch operations

### Resources Not Deleted

**Solution:** Run the cleanup script:

```bash
python scripts/cleanup_all_resources.py
```

### Registry Out of Sync

**Solution:** Purge deleted entries:

```bash
python scripts/cleanup_all_resources.py --purge-deleted
```

### Threading Warnings

Streamlit warnings about missing ScriptRunContext are **normal** when running tests outside of Streamlit. They can be safely ignored.

## Next Steps

After verifying resources work correctly:

1. **Media Processing**: Upload videos and process with Marengo 2.7 on Bedrock
2. **Index Population**: Embeddings will be stored in the S3Vector index
3. **Search Testing**: Test semantic search across modalities
4. **Visualization**: Explore embeddings with PCA, t-SNE, UMAP

## Summary

✅ All tests use **REAL AWS API calls**  
✅ No mocks or simulations  
✅ Complete resource lifecycle testing  
✅ Proper cleanup and verification  
✅ Resource registry tracking  
✅ Ready for production use

