# Bedrock S3 Permissions Fix

## Problem

Bedrock Marengo 2.7 video processing is failing with:
```
ValidationException - Invalid S3 credentials
```

## Root Cause

AWS Bedrock needs explicit permissions to:
1. **Read** video files from your S3 bucket (input)
2. **Write** embedding results to your S3 bucket (output)

The current S3 bucket (`s3vector-1761077785-media`) doesn't have a bucket policy granting Bedrock these permissions.

## Solution

Add an S3 bucket policy that grants Bedrock service permissions.

### Option 1: AWS Console (Recommended for Quick Fix)

1. Go to AWS S3 Console
2. Select bucket: `s3vector-1761077785-media`
3. Go to **Permissions** tab
4. Scroll to **Bucket policy**
5. Click **Edit**
6. Add this policy (replace `YOUR-ACCOUNT-ID` with `386931836011`):

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
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::s3vector-1761077785-media",
                "arn:aws:s3:::s3vector-1761077785-media/*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "386931836011"
                }
            }
        }
    ]
}
```

7. Click **Save changes**

### Option 2: AWS CLI

```bash
# Create policy file
cat > /tmp/bedrock-s3-policy.json << 'EOF'
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
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::s3vector-1761077785-media",
                "arn:aws:s3:::s3vector-1761077785-media/*"
            ],
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "386931836011"
                }
            }
        }
    ]
}
EOF

# Apply policy
aws s3api put-bucket-policy \
    --bucket s3vector-1761077785-media \
    --policy file:///tmp/bedrock-s3-policy.json \
    --region us-west-2
```

### Option 3: Programmatic Fix (Add to Resource Manager)

Update `frontend/components/simplified_resource_manager.py` to automatically add this policy when creating S3 buckets for video processing.

## Verification

After applying the policy:

1. Restart Streamlit app (if needed)
2. Go to Media Processing page
3. Select sample videos
4. Click "Process Videos"
5. Check `run.log` - should see successful job submissions instead of "Invalid S3 credentials"

## Expected Log Output After Fix

```
INFO:src.services.twelvelabs_video_processing:Starting async video processing for s3://s3vector-1761077785-media/videos/...
INFO:src.services.twelvelabs_video_processing:Started video processing job: job-abc123
INFO:src.services.twelvelabs_video_processing:Polling job status...
INFO:src.services.twelvelabs_video_processing:Job completed successfully
```

## Additional Notes

- This policy is scoped to your AWS account (`386931836011`) for security
- The policy allows Bedrock to read/write only to this specific bucket
- You'll need to apply this policy to any new S3 buckets created for video processing
- Consider adding this policy automatically in the resource creation workflow

