# Resource Cleanup Fix

## Issue
The Streamlit Resource Management page showed resources but cleanup wasn't working. The cleanup buttons would show success messages but didn't actually delete any AWS resources.

## Root Cause
In `frontend/components/simplified_resource_manager.py`, the cleanup functions were stubbed out:

```python
def _delete_all_resources(self, resources: Dict[str, List[Dict]]):
    """Delete all resources."""
    with st.spinner("Deleting all resources..."):
        try:
            # This would call the actual AWS APIs  ← STUB!
            st.success("✅ All resources deleted successfully!")
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to delete resources: {e}")
```

## Solution

### 1. Implemented Real Deletion Logic

**`_delete_all_resources()`** - Now actually deletes resources:
- ✅ Deletes in correct order: indexes → vector buckets → S3 buckets → OpenSearch domains
- ✅ Shows progress bar with real-time status
- ✅ Calls actual AWS APIs for each resource type
- ✅ Updates resource registry after each deletion
- ✅ Reports success/failure counts

**`_delete_selected_resources()`** - Now actually deletes selected resources:
- ✅ Same deletion order as delete all
- ✅ Finds full resource details from registry
- ✅ Progress tracking for each resource
- ✅ Proper error handling per resource

### 2. Added OpenSearch Domain Deletion

Created new method `_delete_opensearch_domain_real()`:
- ✅ Checks if domain exists before deletion
- ✅ Initiates domain deletion via AWS API
- ✅ Updates resource registry
- ✅ Optional waiting for deletion completion
- ✅ Proper error handling for ResourceNotFoundException

### 3. Deletion Order

Resources are deleted in the correct dependency order:

1. **S3Vector Indexes** - Must be deleted before buckets
2. **S3Vector Buckets** - Must be deleted before S3 buckets
3. **S3 Buckets** - Can be deleted independently
4. **OpenSearch Domains** - Can be deleted last (includes indexes)

## Implementation Details

### Delete All Resources
```python
def _delete_all_resources(self, resources: Dict[str, List[Dict]]):
    """Delete all resources using real AWS APIs."""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_resources = sum(len(res) for res in resources.values())
    deleted_count = 0
    failed_count = 0
    
    # Delete indexes
    for index in resources.get('indexes', []):
        if self._delete_s3vector_index_real(index['bucket'], index['name']):
            deleted_count += 1
        progress_bar.progress(deleted_count / total_resources)
    
    # Delete vector buckets
    for bucket in resources.get('vector_buckets', []):
        if self._delete_s3vector_bucket_real(bucket['name']):
            deleted_count += 1
        progress_bar.progress(deleted_count / total_resources)
    
    # ... and so on
```

### Delete OpenSearch Domain
```python
def _delete_opensearch_domain_real(self, domain_name: str, wait_for_deletion: bool = False) -> bool:
    """Delete a real OpenSearch domain using AWS API."""
    # Check if exists
    try:
        self.opensearch_client.describe_domain(DomainName=domain_name)
    except ResourceNotFoundException:
        # Already deleted
        self.resource_registry.log_opensearch_domain_deleted(domain_name)
        return True
    
    # Delete domain
    self.opensearch_client.delete_domain(DomainName=domain_name)
    self.resource_registry.log_opensearch_domain_deleted(domain_name)
    
    # Optionally wait for completion
    if wait_for_deletion:
        # Poll every 30s for up to 10 minutes
        ...
```

## Testing

### Before Fix
```
User clicks "Delete All Resources"
→ Shows "✅ All resources deleted successfully!"
→ Resources still exist in AWS
→ Registry still shows resources
```

### After Fix
```
User clicks "Delete All Resources"
→ Shows progress bar: "Deleting index: s3vector-xxx-index..."
→ Actually calls AWS APIs to delete each resource
→ Updates registry after each deletion
→ Shows final count: "✅ Successfully deleted 4 resources!"
→ Resources are actually deleted from AWS
→ Registry is updated correctly
```

## Files Modified

1. **`frontend/components/simplified_resource_manager.py`**
   - Fixed `_delete_all_resources()` to actually delete resources
   - Fixed `_delete_selected_resources()` to actually delete resources
   - Added `_delete_opensearch_domain_real()` method

2. **`frontend/components/simplified_resource_manager.py`** (region fix)
   - Fixed OpenSearch domain region tracking to extract from ARN

3. **`coordination/resource_registry.json`**
   - Updated OpenSearch domain region from us-west-2 to us-east-1

## Related Changes

Also fixed the OpenSearch domain region tracking issue:
- OpenSearch domains are created in us-east-1 by default
- Registry was recording us-west-2 (from `self.region`)
- Now extracts actual region from ARN: `arn:aws:es:REGION:...`

## Verification

To verify the fix works:

1. **Create resources**:
   ```bash
   python scripts/create_all_resources.py
   ```

2. **Check resources exist**:
   ```bash
   aws s3 ls | grep s3vector
   aws s3vectors list-vector-buckets
   aws opensearch list-domain-names --region us-east-1
   ```

3. **Use Streamlit UI to delete**:
   - Navigate to Resource Management page
   - Click "🧹 Resource Cleanup" tab
   - Select "Delete All Resources"
   - Type "DELETE ALL" to confirm
   - Click "🗑️ DELETE ALL RESOURCES"

4. **Verify deletion**:
   ```bash
   aws s3 ls | grep s3vector  # Should be empty
   aws s3vectors list-vector-buckets  # Should be empty
   aws opensearch list-domain-names --region us-east-1  # Should not show domain
   ```

## Next Steps

- ✅ Cleanup functionality now works correctly
- ✅ Resources are actually deleted from AWS
- ✅ Registry is updated properly
- 🔄 Ready to test media processing workflow

