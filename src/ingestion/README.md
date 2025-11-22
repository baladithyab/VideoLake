# Video Ingestion Pipeline

## Quick Start

```python
from src.ingestion.pipeline import VideoIngestionPipeline

# Initialize pipeline
pipeline = VideoIngestionPipeline()

# Process a video
result = pipeline.process_video(
    video_path="s3://my-bucket/videos/sample.mp4",
    model_type="marengo",
    backend_types=["s3vector", "lancedb"]
)

print(f"Job ID: {result.job_id}")
print(f"Status: {result.status}")

# Check status
status = pipeline.get_status(result.job_id)
print(f"Execution Status: {status['status']}")
```

## Files

- [`pipeline.py`](pipeline.py) - Python API for triggering the pipeline
- [`step_function_definition.json`](step_function_definition.json) - AWS Step Functions workflow definition
- [`../lambda/validate_input.py`](../lambda/validate_input.py) - Input validation Lambda
- [`../lambda/generate_embeddings.py`](../lambda/generate_embeddings.py) - Bedrock Marengo embeddings generation
- [`../lambda/backend_upsert.py`](../lambda/backend_upsert.py) - Vector backend upsert logic

## Architecture

```
pipeline.py → Step Function → Lambda Functions → S3/Bedrock/Backends → SNS
```

See [`../../docs/VIDEO_INGESTION_PIPELINE.md`](../../docs/VIDEO_INGESTION_PIPELINE.md) for complete documentation.

## Deployment

Deploy using Terraform module:
```hcl
module "ingestion_pipeline" {
  source = "./terraform/modules/ingestion_pipeline"
  
  project_name            = "videolake"
  environment             = "prod"
  embeddings_bucket_name  = "my-embeddings-bucket"
  notification_email      = "alerts@example.com"
  # ... other variables
}
```

## Environment Variables

```bash
export INGESTION_STATE_MACHINE_ARN=<step-function-arn>
```

## Testing

Mock mode (no AWS resources):
```python
import os
os.environ.pop('INGESTION_STATE_MACHINE_ARN', None)

pipeline = VideoIngestionPipeline()
result = pipeline.process_video("s3://test/video.mp4")
# Returns mock success