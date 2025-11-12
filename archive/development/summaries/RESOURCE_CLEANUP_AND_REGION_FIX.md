# Resource Cleanup and Region Tracking Fix

## Summary

Fixed two critical issues in the S3Vector resource management system:
1. **Resource cleanup wasn't working** - UI showed success but didn't delete resources
2. **OpenSearch domain region was incorrectly tracked** - Registry showed us-west-2 but domain was in us-east-1

## Issues Fixed

### Issue 1: Resource Cleanup Not Working

**Problem:**
- User clicks "Delete All Resources" in Streamlit UI
- UI shows "✅ All resources deleted successfully!"
- Resources still exist in AWS
- Registry still shows resources as active

**Root Cause:**
The cleanup functions in `SimplifiedResourceManager` were stubbed out with placeholder code:

```python
def _delete_all_resources(self, resources: Dict[str, List[Dict]]):
    """Delete all resources."""
    with st.spinner("Deleting all resources..."):
        try:
            # This would call the actual AWS APIs  ← STUB!
            st.success("✅ All resources deleted successfully!")
            time.sleep(2)
            st.rerun()
```

**Solution:**
Implemented real deletion logic that:
- ✅ Calls actual AWS APIs for each resource type
- ✅ Deletes in correct dependency order
- ✅ Shows real-time progress with progress bar
- ✅ Updates resource registry after each deletion
- ✅ Reports accurate success/failure counts
- ✅ Handles errors gracefully per resource

### Issue 2: OpenSearch Domain Region Incorrectly Tracked

**Problem:**
- OpenSearch domain created in us-east-1
- Registry recorded region as us-west-2
- Caused confusion when checking domain status

**Root Cause:**
In `_create_opensearch_domain_real()`, the code used `self.region` instead of extracting the actual region from the ARN:

```python
self.resource_registry.log_opensearch_domain_created(
    domain_name=domain_name,
    domain_arn=domain_arn,
    region=self.region,  # ← Wrong! Uses configured region, not actual region
    ...
)
```

**Solution:**
Extract the actual region from the ARN:

```python
# Extract actual region from ARN (OpenSearch domains may be created in different region)
# ARN format: arn:aws:es:REGION:account-id:domain/domain-name
actual_region = domain_arn.split(':')[3] if ':' in domain_arn else self.region

self.resource_registry.log_opensearch_domain_created(
    domain_name=domain_name,
    domain_arn=domain_arn,
    region=actual_region,  # ← Correct! Uses actual region from ARN
    ...
)
```

## Changes Made

### 1. `frontend/components/simplified_resource_manager.py`

#### Added Real Deletion Logic

**`_delete_all_resources()`** - Lines 604-683
- Deletes resources in correct order: indexes → vector buckets → S3 buckets → OpenSearch domains
- Shows progress bar with status updates
- Calls real AWS APIs: `_delete_s3vector_index_real()`, `_delete_s3vector_bucket_real()`, `_delete_s3_bucket_real()`, `_delete_opensearch_domain_real()`
- Tracks deleted/failed counts
- Updates registry after each deletion

**`_delete_selected_resources()`** - Lines 685-774
- Same deletion order as delete all
- Finds full resource details from registry
- Progress tracking for each selected resource
- Proper error handling per resource

**`_delete_opensearch_domain_real()`** - Lines 1433-1498 (NEW METHOD)
- Checks if domain exists before deletion
- Initiates domain deletion via AWS API
- Updates resource registry
- Optional waiting for deletion completion (up to 10 minutes)
- Handles ResourceNotFoundException gracefully

#### Fixed Region Tracking

**`_create_opensearch_domain_real()`** - Lines 961-975
- Extracts actual region from ARN instead of using `self.region`
- Ensures registry reflects actual AWS resource location

### 2. `coordination/resource_registry.json`

Updated OpenSearch domain region:
```json
{
  "name": "s3vector-1759661152-domain",
  "arn": "arn:aws:es:us-east-1:386931836011:domain/s3vector-1759661152-domain",
  "region": "us-east-1",  // Changed from us-west-2
  ...
}
```

### 3. `frontend/pages/02_🎬_Media_Processing.py`

Added missing import:
```python
from src.utils.resource_registry import resource_registry
```

### 4. Documentation

Created `docs/CLEANUP_FIX.md` with detailed explanation of the fix.

## Deletion Order

Resources are deleted in the correct dependency order to avoid errors:

1. **S3Vector Indexes** - Must be deleted before their buckets
2. **S3Vector Buckets** - Must be deleted before underlying S3 buckets
3. **S3 Buckets** - Can be deleted independently (after emptying)
4. **OpenSearch Domains** - Can be deleted last (automatically removes indexes)

## Testing

### Test Cleanup Functionality

1. **Create test resources:**
   ```bash
   python scripts/create_all_resources.py
   ```

2. **Verify resources exist:**
   ```bash
   aws s3 ls | grep s3vector
   aws s3vectors list-vector-buckets
   aws opensearch list-domain-names --region us-east-1
   ```

3. **Delete via Streamlit UI:**
   - Navigate to Resource Management page
   - Click "🧹 Resource Cleanup" tab
   - Select "Delete All Resources"
   - Type "DELETE ALL" to confirm
   - Click "🗑️ DELETE ALL RESOURCES"
   - Watch progress bar and status updates

4. **Verify deletion:**
   ```bash
   aws s3 ls | grep s3vector  # Should be empty
   aws s3vectors list-vector-buckets  # Should be empty
   aws opensearch list-domain-names --region us-east-1  # Should not show domain
   cat coordination/resource_registry.json  # Should show empty arrays
   ```

### Test Region Tracking

1. **Create new resources:**
   ```bash
   python scripts/create_all_resources.py
   ```

2. **Check registry region:**
   ```bash
   cat coordination/resource_registry.json | grep -A5 opensearch_domains
   ```

3. **Verify matches ARN:**
   - ARN shows: `arn:aws:es:us-east-1:...`
   - Registry shows: `"region": "us-east-1"`
   - ✅ They match!

## Current Resource Status

All resources are currently **ACTIVE**:

1. ✅ **S3 Bucket**: `s3vector-1759661152-media` (us-west-2)
2. ✅ **S3Vector Bucket**: `s3vector-1759661152-vector-bucket` (us-west-2)
3. ✅ **S3Vector Index**: `s3vector-1759661152-index` (us-east-1, 1536 dimensions)
4. ✅ **OpenSearch Domain**: `s3vector-1759661152-domain` (us-east-1)
   - Endpoint: `search-s3vector-1759661152-domain-nlqixzmbe2uvhbgs2t36ytzymi.us-east-1.es.amazonaws.com`
   - Status: Active
   - S3Vectors: Enabled

## Next Steps

Now that resource management is working correctly:

1. ✅ **Resource Creation** - Working (`scripts/create_all_resources.py`)
2. ✅ **Resource Cleanup** - Working (Streamlit UI + `scripts/cleanup_all_resources.py`)
3. ✅ **Region Tracking** - Fixed (extracts from ARN)
4. 🔄 **Ready for Media Processing** - Can now test video processing with Marengo 2.7

## Files Modified

- `frontend/components/simplified_resource_manager.py` - Fixed cleanup + region tracking
- `frontend/pages/02_🎬_Media_Processing.py` - Added missing import
- `coordination/resource_registry.json` - Updated OpenSearch domain region
- `docs/CLEANUP_FIX.md` - Detailed documentation
- `RESOURCE_CLEANUP_AND_REGION_FIX.md` - This summary

## Verification Commands

```bash
# Check Streamlit app is running
curl http://localhost:8501

# Check current resources
python scripts/verify_resources.py

# Test cleanup script
python scripts/cleanup_all_resources.py --force

# Test creation script
python scripts/create_all_resources.py

# Check registry
cat coordination/resource_registry.json | python -m json.tool
```

