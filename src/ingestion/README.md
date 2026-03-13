# Production Ingestion Pipeline

Large-scale multi-modal ingestion system for benchmarking vector databases with 10K-100K+ items.

## Features

- **Batch Processing**: Configurable batch sizes (10-1000 items) with parallel execution
- **Checkpoint/Resume**: S3-based checkpointing for fault tolerance and long-running jobs
- **Rate Limiting**: Token bucket algorithm prevents AWS throttling
- **Progress Tracking**: Real-time progress callbacks and detailed metrics
- **Cost Management**: Cost estimation and limits to prevent runaway bills
- **Multi-Modal Support**: Text, image, audio, and video ingestion
- **Dataset Downloaders**: Built-in downloaders for MS MARCO, COCO, LibriSpeech, MSR-VTT, etc.

## Quick Start

### Large-Scale Batch Ingestion (NEW)

Process 10K-100K+ items with automatic checkpointing and rate limiting:

```python
from src.ingestion import (
    BatchProcessor,
    BatchConfig,
    BatchItem,
    DatasetDownloader,
    get_dataset_config,
    ModalityType,
    VectorStoreType
)

# Configure batch processor
config = BatchConfig(
    batch_size=100,
    max_concurrent_batches=10,
    enable_checkpointing=True,
    checkpoint_interval=500,
    max_cost_usd=50.0
)

processor = BatchProcessor(
    job_id="ms-marco-100k",
    config=config
)

# Download and stage dataset
dataset_config = get_dataset_config("ms_marco_100k")
downloader = DatasetDownloader(dataset_config)
await downloader.download_and_stage()

# Create item generator
async def items():
    async for item in downloader.stream_items():
        yield BatchItem(
            item_id=item.item_id,
            content=item.content,
            modality=ModalityType.TEXT,
            metadata=item.metadata
        )

# Run ingestion
result = await processor.process_dataset(
    items=items(),
    dataset_name="ms-marco-100k",
    embedding_provider_id="bedrock-titan",
    vector_store_type=VectorStoreType.S3VECTOR,
    vector_store_name="msmarco-index",
    resume=True  # Resume from checkpoint if exists
)

print(f"Processed {result.items_processed} items in {result.total_time_seconds/3600:.2f}h")
print(f"Cost: ${result.total_cost_usd:.2f} | Throughput: {result.avg_items_per_second:.1f} items/sec")
```

See [`example_usage.py`](example_usage.py) for complete examples.

### Single Video Ingestion (Step Functions)

Process individual videos via AWS Step Functions:

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

## Core Components

### Batch Processing
- [`batch_processor.py`](batch_processor.py) - Orchestrates large-scale ingestion with parallelization
- [`checkpoint.py`](checkpoint.py) - S3-based checkpoint/resume for fault tolerance
- [`rate_limiter.py`](rate_limiter.py) - Token bucket rate limiting for AWS APIs
- [`dataset_downloader.py`](dataset_downloader.py) - Downloads and stages benchmark datasets

### Video Pipeline (Step Functions)
- [`pipeline.py`](pipeline.py) - Python API for triggering the pipeline
- [`step_function_definition.json`](step_function_definition.json) - AWS Step Functions workflow definition
- [`../lambda/validate_input.py`](../lambda/validate_input.py) - Input validation Lambda
- [`../lambda/generate_embeddings.py`](../lambda/generate_embeddings.py) - Bedrock Marengo embeddings generation
- [`../lambda/backend_upsert.py`](../lambda/backend_upsert.py) - Vector backend upsert logic

### Bedrock Adapters
- [`models/bedrock.py`](models/bedrock.py) - Bedrock multimodal adapter for video embeddings

## Architecture

### Large-Scale Batch Processing
```
DatasetDownloader → S3 Staging → BatchProcessor → RateLimiter → Bedrock/SageMaker
                                       ↓
                                CheckpointManager → S3 Checkpoints
                                       ↓
                                VectorStoreProvider → S3Vector/LanceDB/Qdrant/OpenSearch
```

### Single Video Processing
```
pipeline.py → Step Function → Lambda Functions → S3/Bedrock/Backends → SNS
```

## Supported Datasets

### Text (10K-100K+ documents)
- **MS MARCO**: 3.2M documents, web search ranking
- **Wikipedia**: 6.5M articles, encyclopedia content
- **Common Crawl News**: 20M+ news articles
- **Natural Questions**: 307K Q&A pairs from Google Search

### Image (5K-100K+ images)
- **COCO**: 330K images with captions and object detection
- **LAION**: 400M image-text pairs (use subsets)
- **OpenImages**: 9M images with annotations
- **ImageNet**: 14M images with hierarchical labels

### Audio (2K-50K+ clips)
- **LibriSpeech**: 1000 hours of English speech
- **Common Voice**: Multilingual speech dataset
- **VoxCeleb**: Speaker recognition dataset
- **AudioSet**: 2M audio clips with event labels

### Video (1K-10K+ videos)
- **MSR-VTT**: 10K videos with descriptions
- **ActivityNet**: 20K videos with temporal annotations
- **Kinetics**: 650K video clips for action recognition
- **YouTube-8M**: 8M videos with labels

See [`../../docs/benchmarking/DATASET_RECOMMENDATIONS.md`](../../docs/benchmarking/DATASET_RECOMMENDATIONS.md) for detailed specifications.

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