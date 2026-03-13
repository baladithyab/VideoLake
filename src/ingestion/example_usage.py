"""
Example: Large-Scale Multi-Modal Dataset Ingestion.

Demonstrates end-to-end pipeline for ingesting 100K items from MS MARCO
into S3Vector with checkpointing, rate limiting, and progress tracking.

Usage:
    python -m src.ingestion.example_usage
"""

import asyncio
import sys
from datetime import datetime

from src.ingestion import (
    BatchProcessor,
    BatchConfig,
    BatchItem,
    DatasetDownloader,
    DatasetConfig,
    DatasetType,
    ModalityType,
    VectorStoreType,
    get_dataset_config
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


async def progress_callback(progress_data: dict):
    """Callback for progress updates."""
    print(
        f"\r[{datetime.now().strftime('%H:%M:%S')}] "
        f"Progress: {progress_data['processed_items']}/{progress_data['total_items']} "
        f"({progress_data['progress_percentage']:.1f}%) | "
        f"Cost: ${progress_data['total_cost_usd']:.2f} | "
        f"Elapsed: {progress_data['elapsed_time_seconds']/60:.1f}min",
        end='',
        flush=True
    )


async def example_text_ingestion():
    """
    Example: Ingest 100K MS MARCO documents.

    Demonstrates:
    - Dataset download and staging
    - Batch processing with checkpointing
    - Rate limiting
    - Cost tracking
    - Resume from checkpoint
    """
    print("=" * 80)
    print("Example: MS MARCO 100K Text Ingestion")
    print("=" * 80)
    print()

    # Step 1: Configure dataset download
    print("Step 1: Configuring dataset download...")
    dataset_config = get_dataset_config("ms_marco_100k")  # 100K documents
    dataset_config.s3_bucket = "s3vector-benchmarks"
    dataset_config.s3_prefix = "datasets/ms-marco-100k"

    print(f"  Dataset: MS MARCO")
    print(f"  Max items: {dataset_config.max_items:,}")
    print(f"  S3 location: s3://{dataset_config.s3_bucket}/{dataset_config.s3_prefix}")
    print()

    # Step 2: Download and stage dataset
    print("Step 2: Downloading and staging to S3...")
    downloader = DatasetDownloader(dataset_config)

    try:
        items_staged = await downloader.download_and_stage()
        print(f"  ✓ Staged {items_staged:,} documents to S3")
    except Exception as e:
        logger.warning(f"Dataset already staged or download failed: {e}")
        print(f"  → Skipping download (dataset may already exist)")

    print()

    # Step 3: Configure batch processor
    print("Step 3: Configuring batch processor...")
    batch_config = BatchConfig(
        batch_size=100,  # Process 100 items per batch
        max_concurrent_batches=10,  # 10 parallel batches
        enable_checkpointing=True,
        checkpoint_interval=500,  # Checkpoint every 500 items
        checkpoint_s3_bucket="s3vector-checkpoints",
        enable_rate_limiting=True,
        max_cost_usd=50.0,  # Stop if cost exceeds $50
        progress_callback=progress_callback,
        log_interval=20  # Log every 20 batches
    )

    processor = BatchProcessor(
        job_id=f"ms-marco-100k-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        config=batch_config
    )

    print(f"  Batch size: {batch_config.batch_size}")
    print(f"  Concurrent batches: {batch_config.max_concurrent_batches}")
    print(f"  Checkpointing: {batch_config.checkpoint_interval} items")
    print(f"  Cost limit: ${batch_config.max_cost_usd}")
    print()

    # Step 4: Process dataset
    print("Step 4: Processing dataset...")
    print()

    # Create item generator from staged S3 data
    async def item_generator():
        async for item in downloader.stream_items():
            yield BatchItem(
                item_id=item.item_id,
                content=item.content,  # S3 URI or text content
                modality=ModalityType.TEXT,
                metadata=item.metadata
            )

    # Run ingestion
    try:
        result = await processor.process_dataset(
            items=item_generator(),
            dataset_name="ms-marco-100k",
            embedding_provider_id="bedrock-titan",  # Amazon Titan Text Embeddings
            vector_store_type=VectorStoreType.S3VECTOR,
            vector_store_name="ms-marco-index",
            resume=True  # Resume from checkpoint if exists
        )

        # Step 5: Display results
        print("\n")
        print("=" * 80)
        print("Ingestion Complete!")
        print("=" * 80)
        print()
        print("Summary:")
        print(f"  Total items: {result.total_items:,}")
        print(f"  Processed: {result.items_processed:,}")
        print(f"  Failed: {result.items_failed:,}")
        print(f"  Skipped: {result.items_skipped:,}")
        print(f"  Success rate: {result.items_processed / result.total_items * 100:.1f}%")
        print()
        print("Embedding Stats:")
        print(f"  Embeddings generated: {result.embeddings_generated:,}")
        print(f"  Vectors stored: {result.vectors_stored:,}")
        print()
        print("Performance:")
        print(f"  Total time: {result.total_time_seconds/3600:.2f} hours")
        print(f"  Throughput: {result.avg_items_per_second:.1f} items/sec")
        print()
        print("Cost:")
        print(f"  Total cost: ${result.total_cost_usd:.2f}")
        print(f"  Cost per item: ${result.avg_cost_per_item:.4f}")
        print()

        if result.error_count > 0:
            print(f"Errors: {result.error_count}")
            print("First 5 errors:")
            for error in result.errors[:5]:
                print(f"  - {error}")
            print()

        print("=" * 80)

        return result

    except KeyboardInterrupt:
        print("\n\nIngestion interrupted by user.")
        print("Progress saved to checkpoint. Resume with resume=True.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        print(f"\n\nError: {e}")
        print("Check logs for details.")
        sys.exit(1)


async def example_multi_modal_ingestion():
    """
    Example: Ingest multiple modalities in parallel.

    Demonstrates parallel ingestion across text, image, audio, and video.
    """
    print("=" * 80)
    print("Example: Multi-Modal Parallel Ingestion")
    print("=" * 80)
    print()

    # Configure datasets for each modality
    datasets = {
        "text": get_dataset_config("ms_marco_10k"),
        "image": get_dataset_config("coco_5k"),
        "audio": get_dataset_config("librispeech_2k"),
    }

    # Create ingestion tasks
    tasks = []

    for modality, dataset_config in datasets.items():
        dataset_config.s3_bucket = "s3vector-benchmarks"

        # Configure batch processor for this modality
        batch_config = BatchConfig(
            batch_size=50,
            max_concurrent_batches=5,
            enable_checkpointing=True,
            checkpoint_interval=200,
            checkpoint_s3_bucket="s3vector-checkpoints"
        )

        processor = BatchProcessor(
            job_id=f"{modality}-{datetime.now().strftime('%Y%m%d-%H%M')}",
            config=batch_config
        )

        # Create task
        async def ingest_modality(mod, ds_cfg, proc):
            downloader = DatasetDownloader(ds_cfg)

            async def item_gen():
                async for item in downloader.stream_items():
                    yield BatchItem(
                        item_id=item.item_id,
                        content=item.content,
                        modality=ModalityType[mod.upper()],
                        metadata=item.metadata
                    )

            return await proc.process_dataset(
                items=item_gen(),
                dataset_name=f"{mod}-benchmark",
                embedding_provider_id="bedrock-titan",
                vector_store_type=VectorStoreType.S3VECTOR,
                vector_store_name=f"{mod}-index"
            )

        tasks.append(ingest_modality(modality, dataset_config, processor))

    # Run all ingestion tasks in parallel
    print("Starting parallel ingestion for all modalities...")
    print()

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Display results
    print("\n")
    print("=" * 80)
    print("Multi-Modal Ingestion Complete!")
    print("=" * 80)
    print()

    for modality, result in zip(datasets.keys(), results):
        if isinstance(result, Exception):
            print(f"{modality.upper()}: FAILED - {result}")
        else:
            print(f"{modality.upper()}:")
            print(f"  Processed: {result.items_processed:,} items")
            print(f"  Cost: ${result.total_cost_usd:.2f}")
            print(f"  Throughput: {result.avg_items_per_second:.1f} items/sec")
            print()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Large-scale ingestion examples")
    parser.add_argument(
        "example",
        choices=["text", "multi-modal"],
        help="Example to run"
    )

    args = parser.parse_args()

    if args.example == "text":
        await example_text_ingestion()
    elif args.example == "multi-modal":
        await example_multi_modal_ingestion()


if __name__ == "__main__":
    asyncio.run(main())
