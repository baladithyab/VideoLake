
# Large-Scale Dataset Ingestion Pipeline

Production-grade ingestion system for benchmarking vector databases with 10K-100K+ items across all modalities.

## Features

- ✅ **Batch Processing**: Configurable chunk sizes (10-100K items)
- ✅ **Checkpoint/Resume**: Long-running job recovery
- ✅ **Rate Limiting**: AWS API throttling protection
- ✅ **Progress Tracking**: Real-time status and cost estimation
- ✅ **Multi-Modal**: Text, image, audio, video support
- ✅ **S3 Staging**: Efficient large dataset handling
- ✅ **Dataset Downloaders**: MS MARCO, COCO, LibriSpeech, MSR-VTT

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dataset       │────▶│  Batch Processor │────▶│  Vector Store   │
│   Downloaders   │     │  + Checkpointing │     │  (S3Vector etc) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                         │
         │                       ▼                         │
         │              ┌──────────────────┐              │
         └─────────────▶│   S3 Staging     │──────────────┘
                        │   Manager        │
                        └──────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  AWS Bedrock/    │
                        │  SageMaker       │
                        └──────────────────┘
```

## Quick Start

### 1. List Available Datasets

```bash
python -m src.ingestion.cli list-datasets
```

Output:
```
==================================================================================
Available Datasets for Benchmarking
==================================================================================

📊 MSMARCO
   Modality:     text
   Description:  MS MARCO Document Ranking - Large-scale information retrieval dataset
   License:      Microsoft Research License
   Recommended:  100,000 items

📊 COCO
   Modality:     image
   Description:  COCO - Common Objects in Context image dataset
   License:      CC-BY 4.0
   Recommended:  100,000 items

📊 LIBRISPEECH
   Modality:     audio
   Description:  LibriSpeech - Large corpus of read English speech
   License:      CC-BY 4.0
   Recommended:  100,000 items

📊 MSRVTT
   Modality:     video
   Description:  MSR-VTT - Microsoft Research Video to Text dataset
   License:      Research use
   Recommended:  10,000 items
```

### 2. Download a Dataset

```bash
# Download MS MARCO (text)
python -m src.ingestion.cli download \
  --dataset msmarco \
  --max-items 100000 \
  --output ./data/msmarco

# Download COCO (image)
python -m src.ingestion.cli download \
  --dataset coco \
  --max-items 50000 \
  --output ./data/coco
```

### 3. Run Full Ingestion Pipeline

```bash
python -m src.ingestion.cli ingest \
  --dataset msmarco \
  --max-items 50000 \
  --vector-store s3vector \
  --vector-store-name benchmark-msmarco \
  --batch-size 100 \
  --rate-limit 10 \
  --max-concurrent 5 \
  --checkpoint-interval 100
```

### 4. Monitor Progress

```bash
# Check job status
python -m src.ingestion.cli status --job-id msmarco-20260313-142530

# Output:
# 📊 Job Status: msmarco-20260313-142530
# ============================================================
# Status:           in_progress
# Total Items:      50,000
# Processed:        15,234
# Successful:       15,180
# Failed:           54
# Progress:         30.5%
# Estimated Cost:   $2.1234
# Started:          2026-03-13T14:25:30.123456
# Last Updated:     2026-03-13T14:35:42.789012
# ============================================================
```

## Components

### 1. Batch Processor

Core processing engine with checkpointing and rate limiting.

```python
from src.ingestion.batch_processor import BatchProcessor, BatchConfig
from src.services.embedding_provider import ModalityType
from src.services.vector_store_provider import VectorStoreType

config = BatchConfig(
    job_id="my-ingestion-job",
    modality=ModalityType.TEXT,
    vector_store_type=VectorStoreType.S3VECTOR,
    vector_store_name="my-collection",
    batch_size=100,
    max_concurrent=5,
    rate_limit_requests_per_second=10.0,
    checkpoint_interval=100
)

processor = BatchProcessor(config)

# Process data with automatic checkpointing
async def data_source():
    for item in my_data:
        yield item

result = await processor.process_batch(
    data_source(),
    total_items=10000
)

print(f"Processed: {result.successful_items}/{result.total_items}")
print(f"Cost: ${result.estimated_cost_usd:.4f}")
```

### 2. S3 Staging Manager

Efficient S3 uploads with multipart and parallel processing.

```python
from src.ingestion.s3_staging import S3StagingManager, StagingConfig

config = StagingConfig(
    bucket_name="my-benchmark-bucket",
    prefix="staging",
    enable_versioning=True,
    storage_class="INTELLIGENT_TIERING",
    max_concurrent_uploads=10
)

staging = S3StagingManager(config)

# Upload single file
result = await staging.upload_file(
    local_path=Path("data/document.txt"),
    s3_key="staging/msmarco/text/20260313/doc001.txt"
)

# Upload batch
files = [(Path(f), f"staging/dataset/{f.name}") for f in data_dir.glob("*")]
results = await staging.upload_batch(files)
```

### 3. Dataset Downloaders

Standardized downloaders for benchmark datasets.

```python
from src.ingestion.datasets import get_downloader
from src.ingestion.datasets.base import DownloadConfig

# Configure download
config = DownloadConfig(
    max_items=100000,
    output_dir=Path("./data/msmarco"),
    verify_checksums=True
)

# Get downloader
downloader_cls = get_downloader('msmarco')
downloader = downloader_cls(config)

# Download dataset
metadata = await downloader.download()

# Stream items for processing
async for item in downloader.stream_items():
    print(item['text'])
```

## Dataset Details

### MS MARCO (Text)

- **Size**: 3.2M documents, 367K queries
- **Recommended**: 100K documents
- **Format**: TSV (compressed)
- **Storage**: ~500 MB uncompressed (100K docs)
- **Embedding Cost**: ~$10-20 (with chunking)

```bash
python -m src.ingestion.cli ingest \
  --dataset msmarco \
  --max-items 100000 \
  --vector-store s3vector \
  --vector-store-name msmarco-benchmark \
  --batch-size 100 \
  --rate-limit 10
```

### COCO (Image)

- **Size**: 330K images (train+val)
- **Recommended**: 100K images
- **Format**: JPEG + JSON annotations
- **Storage**: ~35 GB (100K images)
- **Embedding Cost**: ~$80 (Amazon Titan)

```bash
python -m src.ingestion.cli ingest \
  --dataset coco \
  --max-items 100000 \
  --vector-store s3vector \
  --vector-store-name coco-benchmark \
  --batch-size 50 \
  --rate-limit 5
```

### LibriSpeech (Audio)

- **Size**: 1000 hours, ~300K utterances
- **Recommended**: 100K clips
- **Format**: FLAC + TXT transcripts
- **Storage**: ~50 GB (100K clips)
- **Embedding Cost**: ~$50-100 (SageMaker)

```bash
python -m src.ingestion.cli ingest \
  --dataset librispeech \
  --max-items 100000 \
  --vector-store s3vector \
  --vector-store-name librispeech-benchmark \
  --batch-size 50 \
  --rate-limit 10
```

### MSR-VTT (Video)

- **Size**: 10K videos
- **Recommended**: 10K videos
- **Format**: MP4 + JSON annotations
- **Storage**: ~30 GB
- **Embedding Cost**: ~$80 (frame extraction + Titan)

**Note**: Videos must be downloaded separately using youtube-dl or the generated script.

```bash
# Download metadata
python -m src.ingestion.cli download \
  --dataset msrvtt \
  --output ./data/msrvtt

# Use generated script to download videos
bash ./data/msrvtt/download_videos.sh

# Run ingestion
python -m src.ingestion.cli ingest \
  --dataset msrvtt \
  --max-items 10000 \
  --vector-store s3vector \
  --vector-store-name msrvtt-benchmark \
  --batch-size 20 \
  --rate-limit 5
```

## Cost Optimization

### Recommended Settings by Scale

| Items | Batch Size | Max Concurrent | Rate Limit | Est. Time | Est. Cost |
|-------|------------|----------------|------------|-----------|-----------|
| 10K   | 100        | 5              | 10/s       | 30-60 min | $1-5      |
| 50K   | 100        | 10             | 15/s       | 2-4 hours | $5-20     |
| 100K  | 200        | 10             | 20/s       | 4-8 hours | $10-40    |
| 500K  | 500        | 15             | 25/s       | 1-2 days  | $50-200   |

### Cost Breakdown

1. **Embedding Generation** (70-80% of cost)
   - Text: $0.0001 per 1K tokens
   - Image: $0.0008 per image
   - Audio/Video: Variable (SageMaker)

2. **S3 Storage** (10-15% of cost)
   - Standard: $0.023/GB/month
   - Intelligent Tiering: Auto-optimized

3. **API Requests** (5-10% of cost)
   - PUT: $0.000005 per request
   - GET: $0.0000004 per request

## Troubleshooting

### Checkpoint Recovery

If a job fails, it can be resumed from the last checkpoint:

```python
# Checkpoints are automatically saved to .checkpoints/
# Resume by re-running the same job_id
processor = BatchProcessor(config)  # Automatically loads checkpoint
result = await processor.process_batch(data_source(), total_items=10000)
```

### Rate Limiting

Adjust rate limits to avoid throttling:

```bash
# Conservative (recommended for free tier)
--rate-limit 5 --max-concurrent 3

# Moderate (standard usage)
--rate-limit 10 --max-concurrent 5

# Aggressive (high throughput)
--rate-limit 25 --max-concurrent 15
```

### Memory Management

For large datasets, use streaming to avoid memory issues:

```python
# Good: Streaming (low memory)
async for item in downloader.stream_items():
    process(item)

# Bad: Loading all into memory
items = list(downloader.stream_items())  # Don't do this!
```

## Advanced Usage

### Custom Metadata

Add custom metadata to each item:

```python
def add_metadata(item, index):
    return {
        **item,
        'batch_id': 'batch-001',
        'processing_date': '2026-03-13',
        'custom_field': 'value'
    }

result = await processor.process_batch(
    data_source(),
    total_items=10000,
    metadata_fn=add_metadata
)
```

### Parallel Processing

Process multiple datasets in parallel:

```python
import asyncio

async def ingest_dataset(dataset_name, max_items):
    config = BatchConfig(...)
    processor = BatchProcessor(config)
    # ... process dataset

# Run multiple ingestions in parallel
await asyncio.gather(
    ingest_dataset('msmarco', 50000),
    ingest_dataset('coco', 50000),
    ingest_dataset('librispeech', 50000)
)
```

### Cost Tracking

Monitor costs in real-time:

```python
progress = processor.get_progress()
print(f"Estimated cost so far: ${progress['estimated_cost_usd']:.4f}")
print(f"Average time per item: {progress['avg_embedding_time_ms']}ms")
```

## References

- [Dataset Recommendations](../benchmarking/DATASET_RECOMMENDATIONS.md)
- [AWS Cost Optimization](../aws/COST_OPTIMIZATION.md)
- [Vector Store Providers](../../src/services/vector_store_provider.py)
- [Embedding Providers](../../src/services/embedding_provider.py)
