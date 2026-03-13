"""
CLI Tool for Large-Scale Dataset Ingestion.

Provides command-line interface for downloading datasets and running ingestion pipelines.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from src.ingestion.batch_processor import BatchProcessor, BatchConfig, ProcessingStatus
from src.ingestion.s3_staging import S3StagingManager, StagingConfig
from src.ingestion.datasets import get_downloader, list_datasets, DATASET_REGISTRY
from src.ingestion.datasets.base import DownloadConfig
from src.services.embedding_provider import ModalityType
from src.services.vector_store_provider import VectorStoreType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description="Large-Scale Dataset Ingestion Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available datasets
  python -m src.ingestion.cli list-datasets

  # Download MS MARCO dataset
  python -m src.ingestion.cli download --dataset msmarco --max-items 100000 --output ./data/msmarco

  # Stage dataset to S3
  python -m src.ingestion.cli stage --dataset-dir ./data/msmarco --bucket my-bucket --dataset-name msmarco

  # Run full ingestion pipeline
  python -m src.ingestion.cli ingest \\
    --dataset msmarco \\
    --max-items 50000 \\
    --vector-store s3vector \\
    --vector-store-name benchmark-msmarco \\
    --batch-size 100 \\
    --rate-limit 10

  # Check ingestion progress
  python -m src.ingestion.cli status --job-id msmarco-20260313
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # List datasets command
    list_parser = subparsers.add_parser(
        'list-datasets',
        help='List available datasets'
    )

    # Download command
    download_parser = subparsers.add_parser(
        'download',
        help='Download a dataset'
    )
    download_parser.add_argument(
        '--dataset',
        required=True,
        choices=list(DATASET_REGISTRY.keys()),
        help='Dataset to download'
    )
    download_parser.add_argument(
        '--max-items',
        type=int,
        help='Maximum number of items to download'
    )
    download_parser.add_argument(
        '--output',
        type=Path,
        help='Output directory'
    )
    download_parser.add_argument(
        '--verify-checksums',
        action='store_true',
        help='Verify file checksums'
    )

    # Stage command
    stage_parser = subparsers.add_parser(
        'stage',
        help='Stage dataset to S3'
    )
    stage_parser.add_argument(
        '--dataset-dir',
        required=True,
        type=Path,
        help='Local dataset directory'
    )
    stage_parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name'
    )
    stage_parser.add_argument(
        '--dataset-name',
        required=True,
        help='Dataset name for S3 organization'
    )
    stage_parser.add_argument(
        '--modality',
        required=True,
        choices=['text', 'image', 'audio', 'video'],
        help='Data modality'
    )
    stage_parser.add_argument(
        '--max-concurrent',
        type=int,
        default=10,
        help='Maximum concurrent uploads'
    )

    # Ingest command
    ingest_parser = subparsers.add_parser(
        'ingest',
        help='Run full ingestion pipeline'
    )
    ingest_parser.add_argument(
        '--dataset',
        required=True,
        choices=list(DATASET_REGISTRY.keys()),
        help='Dataset to ingest'
    )
    ingest_parser.add_argument(
        '--max-items',
        type=int,
        help='Maximum number of items to ingest'
    )
    ingest_parser.add_argument(
        '--vector-store',
        required=True,
        choices=['s3vector', 'lancedb', 'opensearch', 'qdrant'],
        help='Vector store backend'
    )
    ingest_parser.add_argument(
        '--vector-store-name',
        required=True,
        help='Vector store collection/index name'
    )
    ingest_parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for processing'
    )
    ingest_parser.add_argument(
        '--max-concurrent',
        type=int,
        default=5,
        help='Maximum concurrent requests'
    )
    ingest_parser.add_argument(
        '--rate-limit',
        type=float,
        default=10.0,
        help='Rate limit (requests per second)'
    )
    ingest_parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=100,
        help='Checkpoint save interval'
    )
    ingest_parser.add_argument(
        '--s3-bucket',
        help='Optional S3 bucket for staging'
    )
    ingest_parser.add_argument(
        '--embedding-provider',
        help='Specific embedding provider to use'
    )
    ingest_parser.add_argument(
        '--embedding-model',
        help='Specific embedding model to use'
    )

    # Status command
    status_parser = subparsers.add_parser(
        'status',
        help='Check ingestion job status'
    )
    status_parser.add_argument(
        '--job-id',
        required=True,
        help='Job ID to check'
    )

    return parser


async def cmd_list_datasets(args):
    """List available datasets."""
    datasets = list_datasets()

    print("\n" + "="*80)
    print("Available Datasets for Benchmarking")
    print("="*80 + "\n")

    for name, info in datasets.items():
        downloader_cls = DATASET_REGISTRY[name]
        print(f"📊 {name.upper()}")
        print(f"   Modality:     {info['modality']}")
        print(f"   Description:  {info['description']}")
        print(f"   License:      {info['license']}")
        print(f"   Recommended:  {downloader_cls.RECOMMENDED_SIZE:,} items")
        print()

    print("="*80)
    print(f"Total datasets available: {len(datasets)}")
    print("="*80 + "\n")


async def cmd_download(args):
    """Download a dataset."""
    print(f"\n🔽 Downloading {args.dataset}...")

    # Create download config
    config = DownloadConfig(
        max_items=args.max_items,
        output_dir=args.output,
        verify_checksums=args.verify_checksums
    )

    # Get downloader
    downloader_cls = get_downloader(args.dataset)
    downloader = downloader_cls(config)

    # Print dataset info
    info = downloader.get_dataset_info()
    print(f"\nDataset: {info['name']}")
    print(f"Modality: {info['modality']}")
    print(f"Output: {info['output_directory']}")
    if args.max_items:
        print(f"Max items: {args.max_items:,}")
    print()

    # Download
    metadata = await downloader.download()

    # Print results
    print(f"\n✅ Download complete!")
    print(f"   Total items: {metadata.total_items:,}")
    print(f"   Downloaded: {metadata.downloaded_items:,}")
    print(f"   Failed: {metadata.failed_items:,}")
    print(f"   Size: {metadata.total_size_bytes / (1024**3):.2f} GB")
    print(f"   Time: {metadata.download_time_seconds:.2f} seconds")
    print(f"   Output: {metadata.output_directory}")
    print()


async def cmd_stage(args):
    """Stage dataset to S3."""
    print(f"\n☁️  Staging dataset to S3...")

    # Create staging config
    config = StagingConfig(
        bucket_name=args.bucket,
        max_concurrent_uploads=args.max_concurrent
    )

    staging_manager = S3StagingManager(config)

    # Find files to upload
    dataset_dir = args.dataset_dir
    if not dataset_dir.exists():
        print(f"Error: Dataset directory not found: {dataset_dir}")
        return 1

    # Collect files
    files_to_upload = []
    for file_path in dataset_dir.rglob('*'):
        if file_path.is_file():
            s3_key = staging_manager.generate_staging_key(
                args.dataset_name,
                args.modality,
                file_path.name
            )
            files_to_upload.append((file_path, s3_key))

    print(f"Found {len(files_to_upload)} files to upload")

    # Upload files
    results = await staging_manager.upload_batch(files_to_upload)

    # Print results
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    print(f"\n✅ Staging complete!")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Bucket: s3://{args.bucket}")
    print()


async def cmd_ingest(args):
    """Run full ingestion pipeline."""
    print(f"\n🚀 Starting ingestion pipeline for {args.dataset}...")

    # Generate job ID
    from datetime import datetime
    job_id = f"{args.dataset}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Map dataset to modality
    downloader_cls = get_downloader(args.dataset)
    modality_map = {
        'text': ModalityType.TEXT,
        'image': ModalityType.IMAGE,
        'audio': ModalityType.AUDIO,
        'video': ModalityType.VIDEO
    }
    modality = modality_map[downloader_cls.MODALITY]

    # Map vector store
    vector_store_map = {
        's3vector': VectorStoreType.S3VECTOR,
        'lancedb': VectorStoreType.LANCEDB,
        'opensearch': VectorStoreType.OPENSEARCH,
        'qdrant': VectorStoreType.QDRANT
    }
    vector_store = vector_store_map[args.vector_store]

    # Create batch config
    batch_config = BatchConfig(
        job_id=job_id,
        modality=modality,
        vector_store_type=vector_store,
        vector_store_name=args.vector_store_name,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent,
        rate_limit_requests_per_second=args.rate_limit,
        checkpoint_interval=args.checkpoint_interval,
        embedding_provider_id=args.embedding_provider,
        embedding_model_id=args.embedding_model
    )

    # Create batch processor
    processor = BatchProcessor(batch_config)

    # Download dataset if needed
    download_config = DownloadConfig(
        max_items=args.max_items
    )
    downloader = downloader_cls(download_config)

    print(f"\n📥 Downloading dataset...")
    await downloader.download()

    # Create data source
    async def data_source():
        async for item in downloader.stream_items():
            yield item

    # Run ingestion
    print(f"\n⚙️  Processing {args.max_items or 'all'} items...")
    print(f"   Job ID: {job_id}")
    print(f"   Vector Store: {args.vector_store}/{args.vector_store_name}")
    print(f"   Batch Size: {args.batch_size}")
    print(f"   Rate Limit: {args.rate_limit}/s")
    print()

    result = await processor.process_batch(
        data_source(),
        total_items=args.max_items,
        metadata_fn=lambda item, idx: {
            'dataset': args.dataset,
            'index': idx,
            **item
        }
    )

    # Print results
    print(f"\n✅ Ingestion complete!")
    print(f"   Job ID: {result.job_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Total: {result.total_items:,}")
    print(f"   Successful: {result.successful_items:,}")
    print(f"   Failed: {result.failed_items:,}")
    print(f"   Time: {result.total_time_seconds:.2f}s")
    print(f"   Throughput: {result.throughput_items_per_second:.2f} items/s")
    print(f"   Estimated Cost: ${result.estimated_cost_usd:.4f}")
    print()

    if result.error_summary:
        print("Errors:")
        for error_type, count in result.error_summary.items():
            print(f"   {error_type}: {count}")
        print()


async def cmd_status(args):
    """Check ingestion job status."""
    # Load checkpoint
    checkpoint_path = Path(".checkpoints") / f"{args.job_id}.json"

    if not checkpoint_path.exists():
        print(f"Error: Job not found: {args.job_id}")
        return 1

    with open(checkpoint_path, 'r') as f:
        checkpoint = json.load(f)

    # Print status
    print(f"\n📊 Job Status: {args.job_id}")
    print("="*60)
    print(f"Status:           {checkpoint['status']}")
    print(f"Total Items:      {checkpoint['total_items']:,}")
    print(f"Processed:        {checkpoint['processed_items']:,}")
    print(f"Successful:       {checkpoint['successful_items']:,}")
    print(f"Failed:           {checkpoint['failed_items']:,}")

    if checkpoint['total_items'] > 0:
        progress = (checkpoint['processed_items'] / checkpoint['total_items']) * 100
        print(f"Progress:         {progress:.1f}%")

    print(f"Estimated Cost:   ${checkpoint['estimated_cost_usd']:.4f}")
    print(f"Started:          {checkpoint['start_time']}")
    print(f"Last Updated:     {checkpoint['last_update_time']}")
    print("="*60)
    print()


async def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == 'list-datasets':
            await cmd_list_datasets(args)
        elif args.command == 'download':
            await cmd_download(args)
        elif args.command == 'stage':
            await cmd_stage(args)
        elif args.command == 'ingest':
            await cmd_ingest(args)
        elif args.command == 'status':
            await cmd_status(args)
        else:
            parser.print_help()
            return 1

        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
