"""
Production Ingestion Pipeline for Large-Scale Multi-Modal Datasets.

Provides batch processing, rate limiting, checkpointing, and progress tracking
for ingesting 10K-100K+ items into vector stores.

Core Components:
- BatchProcessor: Orchestrates large-scale ingestion with parallelization
- CheckpointManager: Checkpoint/resume for fault tolerance
- RateLimiter: Token bucket rate limiting for AWS APIs
- DatasetDownloader: Downloads and stages benchmark datasets

Example Usage:
    ```python
    from src.ingestion import (
        BatchProcessor,
        BatchConfig,
        BatchItem,
        DatasetDownloader,
        DatasetConfig,
        DatasetType,
        ModalityType
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
        job_id="ingest-msmarco-100k",
        config=config
    )

    # Download dataset
    dataset_config = DatasetConfig(
        dataset_type=DatasetType.MS_MARCO,
        max_items=100000,
        s3_bucket="my-datasets"
    )

    downloader = DatasetDownloader(dataset_config)
    await downloader.download_and_stage()

    # Process dataset
    async def item_generator():
        async for item in downloader.stream_items():
            yield BatchItem(
                item_id=item.item_id,
                content=item.content,
                modality=ModalityType.TEXT,
                metadata=item.metadata
            )

    result = await processor.process_dataset(
        items=item_generator(),
        dataset_name="ms-marco-100k",
        embedding_provider_id="bedrock-titan",
        vector_store_type=VectorStoreType.S3VECTOR,
        vector_store_name="msmarco-index"
    )

    print(f"Success! Processed {result.items_processed} items")
    print(f"Cost: ${result.total_cost_usd:.2f}")
    print(f"Throughput: {result.avg_items_per_second:.1f} items/sec")
    ```
"""

from src.ingestion.batch_processor import (
    BatchProcessor,
    BatchConfig,
    BatchItem,
    BatchResult,
    IngestionJobResult
)

from src.ingestion.checkpoint import (
    CheckpointManager,
    CheckpointState
)

from src.ingestion.rate_limiter import (
    RateLimiter,
    ServiceType,
    RateLimit
)

from src.ingestion.dataset_downloader import (
    DatasetDownloader,
    DatasetConfig,
    DatasetType,
    DatasetItem,
    RECOMMENDED_DATASETS,
    get_dataset_config
)

# Re-export from services for convenience
from src.services.embedding_provider import ModalityType
from src.services.vector_store_provider import VectorStoreType


__all__ = [
    # Batch processing
    "BatchProcessor",
    "BatchConfig",
    "BatchItem",
    "BatchResult",
    "IngestionJobResult",

    # Checkpointing
    "CheckpointManager",
    "CheckpointState",

    # Rate limiting
    "RateLimiter",
    "ServiceType",
    "RateLimit",

    # Dataset management
    "DatasetDownloader",
    "DatasetConfig",
    "DatasetType",
    "DatasetItem",
    "RECOMMENDED_DATASETS",
    "get_dataset_config",

    # Enums from other modules
    "ModalityType",
    "VectorStoreType",
]


# Version info
__version__ = "1.0.0"
__author__ = "S3Vector Team"
__description__ = "Production ingestion pipeline for large-scale multi-modal datasets"
