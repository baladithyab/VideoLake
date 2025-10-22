# US-EAST-1 Migration - Complete Project Standardization

## Summary

Migrated entire S3Vector project to use `us-east-1` exclusively to resolve Bedrock Marengo 2.7 cross-region S3 access issues.

## Problem

- **Bedrock Region**: `us-east-1` (configured in `config.yaml`)
- **S3 Buckets**: Created in `us-west-2` (from AWS CLI default region)
- **Error**: `ValidationException - Invalid S3 credentials` when Bedrock tried to access S3

## Root Cause

1. AWS CLI was configured with `us-west-2` as default region
2. `simplified_resource_manager.py` was using `boto3.Session().region_name` which picked up CLI config
3. All S3 buckets were created in `us-west-2`
4. Bedrock Marengo 2.7 in `us-east-1` cannot access S3 buckets in `us-west-2` for `StartAsyncInvoke`

## Changes Made

### 1. Updated AWS CLI Configuration

```bash
aws configure set region us-east-1
```

**Before**: `us-west-2`
**After**: `us-east-1`

### 2. Updated Resource Manager

**File**: `frontend/components/simplified_resource_manager.py`

**Before**:
```python
# Get region from boto3 session
session = boto3.Session()
self.region = session.region_name or 'us-east-1'
```

**After**:
```python
# Get region from unified config (always use us-east-1 for this project)
from src.config.unified_config_manager import get_unified_config_manager
config_manager = get_unified_config_manager()
self.region = config_manager.config.aws.region
```

### 3. Verified Configuration Files

**File**: `src/config/config.yaml`

```yaml
aws:
  region: us-east-1  # ✅ Already correct
  
marengo:
  bedrock_region: us-east-1  # ✅ Already correct
```

### 4. Verified AWS Client Pool

**File**: `src/shared/aws_client_pool.py`

```python
# Already using unified config
session_kwargs = {'region_name': aws_config.region}  # ✅ Correct
```

## Current State

### Existing Resources (Wrong Region)

**S3 Buckets in us-west-2** (need migration or recreation):
- `s3vector-1759674268-media`
- `s3vector-1760551160-media`
- `s3vector-1761077785-media` (active)

**Vector Bucket in us-west-2**:
- `s3vector-1761077785-vector-bucket`

**Resources Already in us-east-1** (correct):
- `s3vector-prod-media-processing` (vector bucket)
- `s3vector-1761077785-domain` (OpenSearch domain)
- `s3vector-1761077785-index` (S3 Vectors index)

### New Resources (Correct Region)

All new resources created after this fix will be in `us-east-1`.

## Migration Options

### Option 1: Create New Buckets (Recommended)

**Pros**:
- Clean start
- No data migration needed if no critical data
- Immediate fix

**Steps**:
1. Create new S3 bucket via Streamlit UI
2. Verify it's created in `us-east-1`
3. Set as active bucket
4. Test video processing
5. Delete old `us-west-2` buckets (optional)

### Option 2: Migrate Existing Data

**Pros**:
- Preserves existing videos/data

**Cons**:
- More complex
- Requires data transfer

**Steps**:
1. Create new bucket in `us-east-1`
2. Copy data: `aws s3 sync s3://old-bucket s3://new-bucket --source-region us-west-2 --region us-east-1`
3. Update resource registry
4. Delete old bucket

### Option 3: Keep Old Buckets for Reference

**Pros**:
- No data loss
- Can reference old data

**Cons**:
- Ongoing storage costs
- Confusion about which bucket to use

## Verification Steps

### 1. Check AWS CLI Region

```bash
aws configure get region
# Expected: us-east-1
```

### 2. Create Test S3 Bucket

```bash
# Via Streamlit UI or:
aws s3api create-bucket --bucket test-s3vector-$(date +%s) --region us-east-1
aws s3api get-bucket-location --bucket test-s3vector-XXXXX
# Expected: null (which means us-east-1)
```

### 3. Test Video Processing

1. Restart Streamlit app
2. Create new S3 bucket via UI
3. Verify bucket region in resource registry
4. Process test video
5. Check `run.log` for success

**Expected Success**:
```
INFO: Starting async video processing...
INFO: Started video processing job: arn:aws:bedrock:us-east-1:...
INFO: Job status: IN_PROGRESS
```

**No More**:
```
ERROR: ValidationException - Invalid S3 credentials
```

## Resource Registry Updates

After creating new buckets, the registry should show:

```json
{
  "s3_buckets": [
    {
      "name": "s3vector-XXXXXXXXXX-media",
      "region": "us-east-1",  // ✅ Correct
      "source": "ui",
      "status": "created"
    }
  ]
}
```

## Marengo 2.7 Regional Availability

According to AWS documentation, Marengo 2.7 is available in:
- ✅ `us-east-1` (US East N. Virginia)
- ✅ `eu-west-1` (Europe Ireland)
- ✅ `ap-northeast-2` (Asia Pacific Seoul)

**Not available in**:
- ❌ `us-west-2`
- ❌ `us-west-1`
- ❌ Other regions

## Configuration Hierarchy

The project now enforces region consistency:

1. **Primary Source**: `src/config/config.yaml` → `aws.region: us-east-1`
2. **AWS Client Pool**: Uses unified config manager → `us-east-1`
3. **Resource Manager**: Uses unified config manager → `us-east-1`
4. **AWS CLI**: Configured to `us-east-1` (for manual operations)

## Testing Checklist

- [x] AWS CLI region set to `us-east-1`
- [x] Resource manager uses unified config
- [x] AWS client pool uses unified config
- [x] Config files specify `us-east-1`
- [ ] Create new S3 bucket via UI
- [ ] Verify new bucket is in `us-east-1`
- [ ] Test video processing with new bucket
- [ ] Verify no "Invalid S3 credentials" errors
- [ ] Update active bucket in resource registry
- [ ] (Optional) Delete old `us-west-2` buckets

## Cleanup Tasks

### Old Buckets to Delete (After Migration)

```bash
# Only delete after verifying new buckets work!
aws s3 rb s3://s3vector-1759674268-media --force
aws s3 rb s3://s3vector-1760551160-media --force
aws s3 rb s3://s3vector-1761077785-media --force
```

### Old Vector Bucket

```bash
# Check if still needed
aws s3 rb s3://s3vector-1761077785-vector-bucket --force
```

## Related Documentation

- `docs/MARENGO_S3_REGION_ISSUE.md` - Original issue analysis
- `docs/AUTOMATIC_BEDROCK_PERMISSIONS.md` - Bucket policy setup (still relevant)
- `docs/PROCESSING_MODE_SIMPLIFICATION.md` - Processing mode changes

## Summary

The project is now configured to use `us-east-1` exclusively:

1. ✅ AWS CLI default region: `us-east-1`
2. ✅ Config files: `us-east-1`
3. ✅ Resource manager: Uses config (not boto3 session)
4. ✅ AWS client pool: Uses config
5. ⏳ Existing buckets: Still in `us-west-2` (need migration/recreation)
6. ✅ New buckets: Will be created in `us-east-1`

**Next Step**: Create new S3 bucket via Streamlit UI and test video processing.

