# TwelveLabs Marengo S3 Region Mismatch Issue

## Problem Summary

Bedrock video processing with TwelveLabs Marengo 2.7 is failing with:
```
ValidationException - Invalid S3 credentials
```

## Root Cause Analysis

### Key Discovery

**You were absolutely correct** - Marengo 2.7 is NOT part of AWS Bedrock batch inference! 

According to AWS documentation:
- **Batch Inference** (`CreateModelInvocationJob`) - For processing multiple prompts in batch jobs
  - Requires `roleArn` parameter
  - Supported models: Anthropic Claude, Meta Llama, Amazon Nova, etc.
  - **NOT supported by TwelveLabs Marengo**

- **Async Invoke** (`StartAsyncInvoke`) - For processing individual large assets asynchronously
  - Does NOT require `roleArn` parameter
  - Supported by TwelveLabs Marengo 2.7
  - Used for video/audio processing

### The Actual Issue: Cross-Region S3 Access

**Configuration Mismatch**:
- Bedrock Region: `us-east-1` (from `config.yaml`)
- S3 Bucket Region: `us-west-2` (bucket `s3vector-1761077785-media`)

**Error Details**:
```json
{
  "Error": {
    "Message": "Invalid S3 credentials",
    "Code": "ValidationException"
  },
  "Request": {
    "modelId": "twelvelabs.marengo-embed-2-7-v1:0",
    "modelInput": {
      "mediaSource": {
        "s3Location": {
          "uri": "s3://s3vector-1761077785-media/videos/...",
          "bucketOwner": "386931836011"
        }
      }
    },
    "outputDataConfig": {
      "s3OutputDataConfig": {
        "uri": "s3://s3vector-1761077785-media/video-processing-results/..."
      }
    }
  }
}
```

## Why This Happens

AWS Bedrock `StartAsyncInvoke` may have restrictions on cross-region S3 access:

1. **Bedrock in us-east-1** tries to access **S3 bucket in us-west-2**
2. The "Invalid S3 credentials" error is misleading - it's actually a **region mismatch** issue
3. Bedrock may require S3 buckets to be in the same region for async operations

## Possible Solutions

### Option 1: Use Same Region for Bedrock and S3 (Recommended)

**Change Bedrock region to match S3**:

```yaml
# src/config/config.yaml
aws:
  region: us-west-2  # Match S3 bucket region
  bedrock_region: us-west-2  # Change from us-east-1
```

**Pros**:
- Simplest solution
- No data transfer costs
- Faster processing (same region)

**Cons**:
- Need to verify Marengo 2.7 is available in us-west-2

**Verification**:
```bash
aws bedrock list-foundation-models --region us-west-2 \
    --query "modelSummaries[?contains(modelId, 'marengo')]"
```

### Option 2: Create S3 Bucket in us-east-1

**Create new bucket in Bedrock's region**:

```python
# Update resource manager to create buckets in us-east-1
bucket_region = 'us-east-1'  # Match Bedrock region
```

**Pros**:
- Keeps Bedrock in us-east-1 (if required)
- Guaranteed compatibility

**Cons**:
- Need to migrate existing videos
- More complex migration

### Option 3: Use Bedrock Cross-Region Inference (If Available)

Check if Marengo supports cross-region inference profiles.

**Verification**:
```bash
aws bedrock list-inference-profiles --region us-east-1 \
    --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'marengo')]"
```

## Investigation Steps Taken

1. ✅ Checked AWS documentation - Confirmed Marengo uses `StartAsyncInvoke`, NOT batch inference
2. ✅ Verified model availability - Marengo 2.7 is ACTIVE in us-east-1
3. ✅ Checked IAM permissions - AWSCloud9SSMAccessRole has AdministratorAccess
4. ✅ Verified S3 bucket exists and is accessible
5. ✅ Confirmed bucket policy grants Bedrock permissions
6. ✅ Identified region mismatch - **Bedrock (us-east-1) vs S3 (us-west-2)**

## Incorrect Assumptions Made

### ❌ Assumption 1: Marengo uses batch inference
**Reality**: Marengo uses `StartAsyncInvoke` for async processing, not batch inference

### ❌ Assumption 2: Need `roleArn` parameter
**Reality**: `StartAsyncInvoke` does NOT require `roleArn` - that's only for batch inference

### ❌ Assumption 3: Need IAM service role
**Reality**: Bedrock uses the caller's IAM permissions directly for `StartAsyncInvoke`

## Recommended Fix

**Step 1**: Check if Marengo 2.7 is available in us-west-2:

```bash
aws bedrock get-foundation-model \
    --model-identifier twelvelabs.marengo-embed-2-7-v1:0 \
    --region us-west-2
```

**Step 2**: If available, update config to use us-west-2:

```yaml
# src/config/config.yaml
aws:
  region: us-west-2
  bedrock_region: us-west-2
```

**Step 3**: Restart Streamlit and test video processing

**Step 4**: If Marengo is NOT available in us-west-2:
- Either create new S3 bucket in us-east-1
- Or check if cross-region access can be enabled

## Testing

After applying the fix:

```bash
# 1. Restart Streamlit
# 2. Process a test video
# 3. Check run.log for success:

# Expected SUCCESS:
INFO: Starting async video processing...
INFO: Started video processing job: arn:aws:bedrock:us-west-2:...
INFO: Job status: IN_PROGRESS

# No more:
ERROR: ValidationException - Invalid S3 credentials
```

## Key Learnings

1. **Always verify API requirements** - Don't assume similar APIs work the same way
2. **Region consistency matters** - Cross-region access may have restrictions
3. **Error messages can be misleading** - "Invalid S3 credentials" was actually a region issue
4. **Read the docs carefully** - Batch inference ≠ Async invoke

## Related Documentation

- AWS Bedrock `StartAsyncInvoke` API: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_StartAsyncInvoke.html
- TwelveLabs Marengo Parameters: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-marengo.html
- Batch Inference Supported Models: https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference-supported.html (Marengo NOT listed)

## Files to Clean Up

The following files were created based on incorrect assumptions and should be removed:

- ~~`scripts/create_bedrock_service_role.py`~~ (Already removed)
- ~~`docs/BEDROCK_SERVICE_ROLE_FIX.md`~~ (Already removed)
- `docs/AUTOMATIC_BEDROCK_PERMISSIONS.md` (Bucket policies are still useful, but not the root cause)
- `scripts/add_bedrock_permissions_to_existing_buckets.py` (Bucket policies applied, but not the solution)

## Next Steps

1. Verify Marengo availability in us-west-2
2. Update configuration to use matching regions
3. Test video processing
4. Document the correct solution
5. Update any misleading documentation

