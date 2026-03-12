# AWS S3Vector Bucket and Index Creation Workflow Research

## Executive Summary

The issue with S3Vector index creation failing with "NotFoundException: The specified vector bucket could not be found" is due to a fundamental misunderstanding between **regular S3 buckets** and **S3Vector buckets**. These are completely different AWS services with different APIs, endpoints, and purposes.

## Key Findings

### 1. S3Vector vs Regular S3 Buckets

**Critical Distinction:**
- **Regular S3 buckets** (what's currently working): Created via `aws s3 mb` or `aws s3api create-bucket`
- **S3Vector buckets** (what's needed): Created via `aws s3vectors create-vector-bucket`

**The Problem:**
- Current success: "s3vector-setup-1757111669-s3" is a **regular S3 bucket**
- Current failure: Trying to create vector indexes in a regular S3 bucket using S3Vector APIs

### 2. Correct S3Vector Workflow

#### Step 1: Create Vector Bucket (Not Regular S3 Bucket)
```bash
# CORRECT - Creates S3Vector bucket
aws s3vectors create-vector-bucket \
  --vector-bucket-name "amzn-s3-demo-vector-bucket"

# With KMS encryption (optional)
aws s3vectors create-vector-bucket \
  --vector-bucket-name "amzn-s3-demo-vector-bucket" \
  --encryption-configuration '{
    "sseType": "aws:kms", 
    "kmsKeyArn": "arn:aws:kms:us-east-1:111122223333:key/1234abcd-12ab-34cd-56ef-1234567890ab"
  }'
```

#### Step 2: Create Vector Index Within Vector Bucket
```bash
# CORRECT - Creates vector index in S3Vector bucket
aws s3vectors create-index \
  --vector-bucket-name "amzn-s3-demo-vector-bucket" \
  --index-name "my-vector-index" \
  --data-type "float32" \
  --dimension 1024 \
  --distance-metric "cosine"

# With non-filterable metadata
aws s3vectors create-index \
  --vector-bucket-name "amzn-s3-demo-vector-bucket" \
  --index-name "my-vector-index" \
  --data-type "float32" \
  --dimension 1024 \
  --distance-metric "cosine" \
  --metadata-configuration '{
    "nonFilterableMetadataKeys": ["nonFilterableKey1", "nonFilterableKey2"]
  }'
```

### 3. S3Vector Bucket Requirements

#### Naming Rules:
- Must be 3-63 characters long
- Only lowercase letters, numbers, and hyphens
- Must be unique within AWS account for the Region
- Cannot be changed after creation

#### Encryption:
- **Default**: SSE-S3 (AES256) - automatically applied
- **Optional**: SSE-KMS with customer managed keys
- **Important**: Encryption settings cannot be changed after creation

#### Permissions:
- `s3vectors:CreateVectorBucket` for bucket creation
- `s3vectors:CreateIndex` for index creation

### 4. Vector Index Requirements

#### Immutable Configuration:
Once created, the following **CANNOT** be changed:
- Index name
- Dimension
- Distance metric  
- Non-filterable metadata keys

#### Parameters:
- **Index name**: 3-63 characters, lowercase letters, numbers, hyphens, dots
- **Dimension**: 1-4096 (must match embedding model output)
- **Distance metric**: 
  - `cosine` - for normalized vectors, direction matters more
  - `euclidean` - when both direction and magnitude matter
- **Data type**: `float32` (standard for vector embeddings)

#### Metadata:
- **Filterable metadata**: Added per vector, can be used in queries
- **Non-filterable metadata**: Specified at index creation, stored but not queryable
- **Limit**: Maximum 10 non-filterable metadata keys

### 5. API Differences

#### Regular S3 API:
```python
# WRONG - This creates regular S3 bucket
import boto3
s3_client = boto3.client('s3')
s3_client.create_bucket(Bucket='my-bucket')
```

#### S3Vector API:
```python
# CORRECT - This creates S3Vector bucket
import boto3
s3vectors_client = boto3.client('s3vectors')
s3vectors_client.create_vector_bucket(vectorBucketName='my-vector-bucket')
```

## Root Cause Analysis

The current implementation likely:
1. ✅ Creates a regular S3 bucket successfully
2. ❌ Attempts to create vector indexes using S3Vector APIs on the regular S3 bucket
3. ❌ Fails with "NotFoundException" because S3Vector APIs cannot find an S3Vector bucket

## Recommended Solution

### Immediate Fix:
1. **Replace regular S3 bucket creation** with S3Vector bucket creation
2. **Update API calls** to use `s3vectors` service instead of `s3` service
3. **Verify permissions** include S3Vector-specific permissions

### Implementation Steps:

#### 1. Update Bucket Creation:
```python
# Replace this (regular S3)
s3_client.create_bucket(Bucket=bucket_name)

# With this (S3Vector)
s3vectors_client.create_vector_bucket(vectorBucketName=bucket_name)
```

#### 2. Update Index Creation:
```python
# Use S3Vector API for index creation
s3vectors_client.create_index(
    vectorBucketName=bucket_name,
    indexName=index_name,
    dataType='float32',
    dimension=1536,  # Match your embedding model
    distanceMetric='cosine'
)
```

#### 3. Update IAM Permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3vectors:CreateVectorBucket",
        "s3vectors:CreateIndex",
        "s3vectors:DeleteVectorBucket",
        "s3vectors:DeleteIndex",
        "s3vectors:GetVectorBucket",
        "s3vectors:ListVectorBuckets",
        "s3vectors:PutVectors",
        "s3vectors:GetVectors",
        "s3vectors:QueryVectors"
      ],
      "Resource": "*"
    }
  ]
}
```

## Important Notes

### Preview Status:
- **Amazon S3 Vectors is in preview** and subject to change
- APIs and functionality may evolve

### Region Availability:
- Not available in all AWS regions
- Check current region support before implementation

### Cost Considerations:
- S3Vector pricing differs from regular S3
- Vector storage and query operations have separate pricing

### Migration Strategy:
- **Cannot migrate** regular S3 bucket to S3Vector bucket
- Must create new S3Vector bucket and migrate data
- Plan for application downtime during migration

## Next Steps

1. **Audit current implementation** to identify all S3 vs S3Vector API usage
2. **Update boto3 clients** to use 's3vectors' service
3. **Test vector bucket creation** in development environment
4. **Update error handling** for S3Vector-specific exceptions
5. **Verify IAM permissions** include S3Vector actions
6. **Plan production migration** from regular S3 to S3Vector buckets

## References

- [Creating a vector bucket - AWS Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-buckets-create.html)
- [Creating a vector index - AWS Documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-create-index.html)
- [CreateVectorBucket API - AWS Documentation](https://docs.aws.amazon.com/AmazonS3/latest/API/API_S3VectorBuckets_CreateVectorBucket.html)
- [S3Vector OpenSearch Integration - AWS Documentation](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/s3-vector-opensearch-integration-engine.html)