# VideoLake Video Ingestion Pipeline

## Overview

The VideoLake video ingestion pipeline is an automated, serverless workflow that processes videos using AWS Step Functions, Lambda, and Bedrock Marengo to generate multimodal embeddings.

## Architecture

```
User Upload (S3)
    │
    ├─> API Trigger (pipeline.py)
    │
    └─> Step Function Orchestration (Async Pattern)
         │
         ├─> 1. Validate Input (Lambda)
         │    └─> Check S3 path, file format, model type
         │
         ├─> 2. Start Embedding Job (Lambda)
         │    └─> Initiate async Bedrock Marengo job
         │
         ├─> 3. Wait & Poll Loop
         │    ├─> Wait 30 seconds
         │    ├─> Check Job Status (Lambda)
         │    └─> Repeat until COMPLETED or FAILED
         │
         ├─> 4. Retrieve Embeddings (Lambda)
         │    ├─> Download output from S3
         │    └─> Format as JSONL
         │
         ├─> 5. Save to S3 (AWS SDK)
         │    └─> Write embeddings.jsonl to final location
         │
         ├─> 6. Optional: Upsert to Backends (Lambda)
         │    ├─> S3Vector
         │    ├─> LanceDB
         │    ├─> Qdrant
         │    └─> OpenSearch
         │
         └─> 7. Notify Completion (SNS)
              ├─> Success notifications
              └─> Error notifications
```

## Components

### 1. Step Function Definition
**File:** [`src/ingestion/step_function_definition.json`](../src/ingestion/step_function_definition.json)

State machine that orchestrates the entire pipeline with:
- Input validation
- Error handling and retries
- Conditional backend upserts
- SNS notifications for completion/errors

### 2. Lambda Functions

#### Validate Input
**File:** [`src/lambda/validate_input.py`](../src/lambda/validate_input.py)

Validates:
- S3 URI format and video file existence
- Video file extension (mp4, mov, avi, etc.)
- Model type (marengo, bedrock, titan-multimodal)
- Backend types (s3vector, lancedb, qdrant, opensearch)
- Generates unique video_id for tracking

#### Start Embedding Job
**File:** [`src/lambda/start_embedding_job.py`](../src/lambda/start_embedding_job.py)

Function:
- Validates video exists in S3 and checks size (max 100MB)
- Initiates async Bedrock Marengo job
- Returns job ID for polling
- Fast execution (~1-2 seconds)

#### Check Embedding Status
**File:** [`src/lambda/check_embedding_status.py`](../src/lambda/check_embedding_status.py)

Function:
- Polls Bedrock for async job status
- Returns: IN_PROGRESS, COMPLETED, or FAILED
- Called repeatedly by Step Function until completion
- Lightweight polling function

#### Retrieve Embeddings
**File:** [`src/lambda/retrieve_embeddings.py`](../src/lambda/retrieve_embeddings.py)

Processing:
- Downloads completed embeddings from S3 output location
- Parses Bedrock Marengo output format
- Supports video and audio embeddings
- Formats output as JSONL (one embedding per line)

**Output Format:**
```json
{
  "id": "video_name_abc123_frame_0",
  "video_id": "video_name_abc123",
  "embedding": [0.1, 0.2, ..., 1024 dimensions],
  "metadata": {
    "video_path": "s3://bucket/path/video.mp4",
    "frame_index": 0,
    "timestamp": 0.0,
    "modality": "video",
    "model_type": "marengo",
    "created_at": "2025-11-22T00:00:00.000Z"
  }
}
```

#### Backend Upsert
**File:** [`src/lambda/backend_upsert.py`](../src/lambda/backend_upsert.py)

Capabilities:
- Reads embeddings from S3 JSONL file
- Upserts to multiple vector backends in parallel
- Returns detailed results for each backend
- Handles partial failures gracefully

### 3. Terraform Infrastructure
**File:** [`terraform/modules/ingestion_pipeline/main.tf`](../terraform/modules/ingestion_pipeline/main.tf)

Resources created:
- **3 Lambda Functions** (validate, generate, upsert)
- **IAM Roles & Policies** for Lambda and Step Functions
- **Step Function State Machine** with the workflow
- **2 SNS Topics** for completion and error notifications
- **Lambda Packages** (automatic ZIP creation)

### 4. Python API
**File:** [`src/ingestion/pipeline.py`](../src/ingestion/pipeline.py)

Public interface:
```python
from src.ingestion.pipeline import VideoIngestionPipeline

pipeline = VideoIngestionPipeline()

# Process a video
result = pipeline.process_video(
    video_path="s3://my-bucket/videos/sample.mp4",
    model_type="marengo",
    backend_types=["s3vector", "lancedb"]
)

# Check status
status = pipeline.get_status(result.job_id)
```

## Deployment

### Prerequisites
1. AWS Account with Bedrock access
2. Terraform installed
3. S3 bucket for embeddings storage
4. (Optional) Email for notifications

### Terraform Variables

```hcl
module "ingestion_pipeline" {
  source = "./modules/ingestion_pipeline"

  project_name                  = "videolake"
  environment                   = "prod"
  ecs_cluster_arn              = module.ecs.cluster_arn
  ingestion_task_definition_arn = module.ecs.task_definition_arn
  subnet_ids                    = module.vpc.private_subnet_ids
  security_group_id             = module.vpc.default_security_group_id
  embeddings_bucket_name        = "my-embeddings-bucket"
  notification_email            = "alerts@example.com"  # Optional
}
```

### Deploy

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Environment Setup

After deployment, set the Step Function ARN:
```bash
export INGESTION_STATE_MACHINE_ARN=$(terraform output -raw ingestion_pipeline_arn)
```

## Usage

### 1. Upload Video to S3
```bash
aws s3 cp my-video.mp4 s3://my-bucket/videos/my-video.mp4
```

### 2. Trigger Pipeline

**Via Python API:**
```python
from src.ingestion.pipeline import VideoIngestionPipeline

pipeline = VideoIngestionPipeline()
result = pipeline.process_video(
    video_path="s3://my-bucket/videos/my-video.mp4",
    model_type="marengo",
    backend_types=["s3vector"]
)
print(f"Job ID: {result.job_id}")
print(f"Status: {result.status}")
```

**Via AWS CLI:**
```bash
aws stepfunctions start-execution \
  --state-machine-arn $INGESTION_STATE_MACHINE_ARN \
  --input '{
    "video_path": "s3://my-bucket/videos/my-video.mp4",
    "model_type": "marengo",
    "backend_types_str": "s3vector,lancedb"
  }'
```

### 3. Monitor Execution

**Via AWS Console:**
- Navigate to Step Functions → State Machines
- Find your execution
- View visual workflow and logs

**Via Python API:**
```python
status = pipeline.get_status(execution_arn)
print(f"Status: {status['status']}")
print(f"Output: {status['output']}")
```

**Via AWS CLI:**
```bash
aws stepfunctions describe-execution \
  --execution-arn <execution-arn>
```

## Output

### Embeddings Storage
Embeddings are saved to S3 as JSONL:
```
s3://{embeddings_bucket}/embeddings/{video_id}/embeddings.jsonl
```

### Notifications

**Success Email:**
- Subject: "VideoLake Ingestion Completed Successfully"
- Contains: video_id, output_key, embeddings_count, backend results

**Error Email:**
- Subject: "VideoLake Ingestion Failed"
- Contains: error details, video_path, execution_id

## Error Handling

The pipeline includes comprehensive error handling:

1. **Validation Errors**: Invalid S3 paths, unsupported formats → immediate failure
2. **Bedrock Errors**: Rate limits, service errors → automatic retry (3 attempts)
3. **S3 Errors**: Upload failures → automatic retry (3 attempts)
4. **Backend Errors**: Upsert failures → partial success (embeddings saved, notification sent)

## Configuration

### Supported Video Formats
- `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`, `.flv`, `.wmv`

### Supported Models
- `marengo` - AWS Bedrock Marengo (default)
- `bedrock` - Generic Bedrock models
- `titan-multimodal` - Amazon Titan Multimodal

### Supported Backends
- `s3vector` - S3-based vector storage
- `lancedb` - LanceDB vector database
- `qdrant` - Qdrant vector search engine
- `opensearch` - OpenSearch with KNN

### Limits
- Maximum video size: 100 MB (configurable in Lambda)
- Maximum processing time: 15 minutes (Lambda timeout)
- Maximum embedding dimension: 1024 (Bedrock Marengo default)

## Cost Estimation

Per video processing:
- **Step Function**: $0.000025 per state transition (~10 transitions = $0.00025)
- **Lambda Validate**: ~100ms @ 256MB = $0.000001
- **Lambda Generate**: ~5min @ 3GB = $0.005
- **Lambda Upsert**: ~30s @ 1GB = $0.0005
- **S3 Storage**: ~$0.023 per GB/month
- **Bedrock Marengo**: Pay per token (varies by video length)
- **SNS**: $0.50 per 1M notifications

**Estimated cost per video:** ~$0.01-0.10 (excluding Bedrock)

## Troubleshooting

### Lambda Timeout
**Problem:** Video processing exceeds 15 minutes
**Solution:** 
- Reduce video size
- Increase Lambda timeout (max 15min)
- Split large videos into chunks

### Bedrock Access Denied
**Problem:** Lambda cannot invoke Bedrock
**Solution:**
- Verify Bedrock model access in AWS Console
- Check Lambda IAM role has `bedrock:InvokeModel` permission
- Ensure correct AWS region

### S3 Access Denied
**Problem:** Cannot read/write S3 objects
**Solution:**
- Verify Lambda role has S3 permissions
- Check bucket policies
- Verify video exists in S3

### Missing Notifications
**Problem:** No email notifications
**Solution:**
- Check SNS subscription confirmation (check spam folder)
- Verify email in Terraform variables
- Check SNS topic permissions

## Development

### Testing Locally
```python
# Mock mode (no AWS resources needed)
import os
os.environ.pop('INGESTION_STATE_MACHINE_ARN', None)

from src.ingestion.pipeline import VideoIngestionPipeline
pipeline = VideoIngestionPipeline()
result = pipeline.process_video("s3://test/video.mp4")
# Returns mock success
```

### Adding New Backends
1. Update [`backend_upsert.py`](../src/lambda/backend_upsert.py)
2. Add new backend function (e.g., `upsert_to_milvus`)
3. Update `upsert_to_backend()` routing
4. Update `supported_backends` in [`validate_input.py`](../src/lambda/validate_input.py)

### Extending Embeddings
To add custom metadata or processing:
1. Modify [`generate_embeddings.py`](../src/lambda/generate_embeddings.py)
2. Update JSONL format in `lambda_handler()`
3. Adjust backend upsert functions accordingly

## Future Enhancements

- [ ] Support for live video streams
- [ ] Batch processing multiple videos
- [ ] Custom embedding models
- [ ] Advanced video preprocessing (compression, transcoding)
- [ ] Distributed processing for large videos
- [ ] Real-time progress tracking
- [ ] Automatic video quality detection
- [ ] Multi-region deployment

## References

- [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/)
- [AWS Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html)

## Support

For issues or questions:
- Create an issue in the repository
- Check CloudWatch Logs for Lambda functions
- Review Step Function execution history
- Check SNS email notifications for error details