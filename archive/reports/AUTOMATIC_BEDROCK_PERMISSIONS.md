# Automatic Bedrock Permissions for S3 Buckets

## Overview

The resource manager now automatically configures S3 bucket permissions for Bedrock when creating new buckets. This eliminates the "Invalid S3 credentials" error that was occurring during video processing.

## What Changed

### 1. Automatic Policy Application (New Buckets)

**File**: `frontend/components/simplified_resource_manager.py`

When creating a new S3 bucket via `_create_s3_bucket_real()`, the system now:
1. Creates the bucket
2. Applies encryption (if specified)
3. **Automatically adds Bedrock permissions** (new!)
4. Registers the bucket in the resource registry

**Code Changes**:
```python
def _create_s3_bucket_real(self, bucket_name: str, 
                           encryption_configuration: Optional[Dict[str, Any]] = None,
                           enable_bedrock_access: bool = True) -> Tuple[bool, str]:
    """Create a real S3 bucket using AWS API.
    
    Args:
        enable_bedrock_access: If True, automatically add bucket policy for Bedrock (default: True)
    """
    # ... create bucket ...
    # ... add encryption ...
    
    # Add Bedrock permissions for video processing
    if enable_bedrock_access:
        self._add_bedrock_bucket_policy(bucket_name)
    
    # ... rest of setup ...
```

**New Helper Method**:
```python
def _add_bedrock_bucket_policy(self, bucket_name: str) -> bool:
    """Add bucket policy to allow Bedrock service access."""
    # Gets AWS account ID
    # Creates bucket policy with Bedrock service principal
    # Applies policy to bucket
    # Returns True on success, False on failure (non-blocking)
```

### 2. Utility Script for Existing Buckets

**File**: `scripts/add_bedrock_permissions_to_existing_buckets.py`

A new script to apply Bedrock permissions to buckets that were created before this feature was added.

**Usage**:
```bash
# Update all buckets in resource registry
python scripts/add_bedrock_permissions_to_existing_buckets.py

# Update specific bucket
python scripts/add_bedrock_permissions_to_existing_buckets.py --bucket-name s3vector-1761077785-media

# Specify region
python scripts/add_bedrock_permissions_to_existing_buckets.py --region us-east-1
```

**What It Does**:
1. Reads all S3 and S3Vector buckets from resource registry
2. Gets current AWS account ID
3. Creates Bedrock access policy for each bucket
4. Applies the policy
5. Reports success/failure for each bucket

## Bucket Policy Details

The policy grants Bedrock service the following permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockS3Access",
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock.amazonaws.com"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:ListBucket",
                "s3:GetBucketLocation"
            ],
            "Resource": [
                "arn:aws:s3:::BUCKET_NAME",
                "arn:aws:s3:::BUCKET_NAME/*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "YOUR_ACCOUNT_ID"
                }
            }
        }
    ]
}
```

**Permissions Explained**:
- `s3:GetObject` - Read video files for processing
- `s3:PutObject` - Write embedding results
- `s3:ListBucket` - List bucket contents
- `s3:GetBucketLocation` - Get bucket region

**Security**:
- Scoped to Bedrock service only (`bedrock.amazonaws.com`)
- Restricted to your AWS account via `aws:SourceAccount` condition
- No public access granted

## Migration for Existing Deployments

### Step 1: Update Existing Buckets

Run the utility script to add permissions to all existing buckets:

```bash
cd /home/ubuntu/S3Vector
python scripts/add_bedrock_permissions_to_existing_buckets.py
```

**Expected Output**:
```
======================================================================
🔐 Adding Bedrock Permissions to S3 Buckets
======================================================================

Found 5 bucket(s) in resource registry:
  - s3vector-1759674268-media (S3, us-west-2)
  - s3vector-1760551160-media (S3, us-west-2)
  - s3vector-1761077785-media (S3, us-west-2)
  ...

Updating s3vector-1761077785-media...
✅ Successfully added Bedrock access policy to bucket: s3vector-1761077785-media
   Account ID: 386931836011
   Region: us-west-2

======================================================================
📊 Summary
======================================================================
✅ Successfully updated: 3
❌ Failed: 0
📦 Total buckets: 3
```

### Step 2: Verify Video Processing Works

1. Restart Streamlit app (if running)
2. Navigate to Media Processing page
3. Select sample videos
4. Click "Process Videos"
5. Check `run.log` for successful job submissions

**Before Fix** (run.log):
```
ERROR:src.services.twelvelabs_video_processing:AWS error starting video processing: ValidationException - Invalid S3 credentials
```

**After Fix** (run.log):
```
INFO:src.services.twelvelabs_video_processing:Starting async video processing...
INFO:src.services.twelvelabs_video_processing:Started video processing job: job-abc123
INFO:src.services.twelvelabs_video_processing:Job status: IN_PROGRESS
```

## Future Bucket Creation

All new S3 buckets created through the resource manager will automatically have Bedrock permissions applied. No manual intervention needed!

**Where This Applies**:
- Individual S3 bucket creation (Simplified Resource Manager)
- Complete setup workflows
- Programmatic bucket creation via `_create_s3_bucket_real()`

**To Disable** (if needed):
```python
# Pass enable_bedrock_access=False to skip Bedrock policy
success, arn = manager._create_s3_bucket_real(
    bucket_name="my-bucket",
    enable_bedrock_access=False  # Skip Bedrock permissions
)
```

## Troubleshooting

### Policy Application Failed

If the automatic policy application fails during bucket creation:
1. The bucket is still created successfully
2. A warning is logged (non-blocking)
3. You can manually apply the policy later using the utility script

### Bucket Already Has Policy

If a bucket already has a policy, the new Bedrock policy will **replace** it. If you need to preserve existing policies, you'll need to merge them manually.

### Cross-Region Buckets

The script uses the region from the resource registry. If a bucket is in a different region, specify it:

```bash
python scripts/add_bedrock_permissions_to_existing_buckets.py \
    --bucket-name my-bucket \
    --region us-east-1
```

## Testing

### Test New Bucket Creation

```python
from frontend.components.simplified_resource_manager import SimplifiedResourceManager

manager = SimplifiedResourceManager(region='us-west-2')
success, arn = manager._create_s3_bucket_real("test-bedrock-permissions")

# Verify policy was applied
import boto3
s3 = boto3.client('s3', region_name='us-west-2')
policy = s3.get_bucket_policy(Bucket="test-bedrock-permissions")
print(policy['Policy'])  # Should contain Bedrock permissions
```

### Test Video Processing

1. Upload a sample video to the bucket
2. Use Media Processing page to process it
3. Check that Bedrock can access the video and write results

## Related Documentation

- `docs/BEDROCK_S3_PERMISSIONS_FIX.md` - Original manual fix documentation
- `docs/PROCESSING_MODE_SIMPLIFICATION.md` - Processing mode changes
- `examples/real_video_processing_demo.py` - Example with bucket policies

## Summary

✅ **New buckets**: Automatically get Bedrock permissions
✅ **Existing buckets**: Use utility script to add permissions
✅ **Video processing**: Should now work without "Invalid S3 credentials" errors
✅ **Security**: Scoped to Bedrock service and your AWS account only

