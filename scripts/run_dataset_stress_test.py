#!/usr/bin/env python3
"""
Video Dataset Stress Test Runner

Processes large video datasets to stress test vector stores with realistic workloads.

WORKFLOW (Bedrock Async Pattern):
1. Download videos from dataset source (HuggingFace/Pexels/etc.)
2. Upload videos to S3
3. Submit Bedrock async job: S3 (video) → Bedrock → S3 (embeddings)
4. Wait for async job completion
5. Retrieve embeddings from S3 output
6. Optionally: Load embeddings into vector stores for querying

DEFAULT MODE: --embedding-only (no vector store setup needed)
   - Just generates embeddings and saves to S3
   - Perfect for building an embedding dataset first
   - Later, you can bulk-load into vector stores

FULL MODE: --store-in-vector-dbs (requires vector stores to be set up)
   - Generates embeddings AND stores in vector databases
   - Requires pre-configured vector stores (S3Vector indexes, Qdrant collections, etc.)

Supports:
- HuggingFace datasets with streaming (MSR-VTT, WebVid, YouCook2, ActivityNet)
- Creative Commons sources (Pexels, Pixabay)
- Progressive download and upload
- Parallel processing with configurable concurrency
- Cost limits and time limits
- Checkpointing for resumability

Usage:
    # Generate embeddings only (no vector store setup needed)
    python scripts/run_dataset_stress_test.py --dataset msr-vtt-100 --model marengo

    # Generate and store (requires vector stores configured)
    python scripts/run_dataset_stress_test.py --dataset msr-vtt-100 --model nova --store-in-vector-dbs --stores s3vector,qdrant

    # Quick test with 4 Blender videos
    python scripts/run_dataset_stress_test.py --dataset blender --model marengo

    # Stress test with 1000 videos (embedding only)
    python scripts/run_dataset_stress_test.py --dataset msr-vtt-1000 --model nova --max-cost 7000

    # Large scale with cost limit
    python scripts/run_dataset_stress_test.py --dataset webvid-10k --model nova --max-cost 100000
"""

import argparse
import sys
import time
import yaml
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.video_dataset_manager import VideoDatasetManager, VideoDatasetConfig
from src.services.bulk_video_processor import BulkVideoProcessor, BulkProcessingConfig, BulkProcessingMetrics
from src.services.embedding_model_selector import EmbeddingModel
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Load datasets catalog
def load_datasets_catalog() -> Dict:
    """Load datasets from configuration."""
    config_path = Path(__file__).parent.parent / "src" / "config" / "datasets.yaml"

    with open(config_path) as f:
        return yaml.safe_load(f)


DATASETS_CATALOG = load_datasets_catalog()


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{'='*100}")
    print(f"  {text}")
    print(f"{'='*100}\n")


def print_section(text: str) -> None:
    """Print formatted section."""
    print(f"\n{'-'*100}")
    print(f"  {text}")
    print(f"{'-'*100}\n")


def select_dataset(dataset_name: str) -> VideoDatasetConfig:
    """
    Select dataset from catalog.

    Args:
        dataset_name: Dataset identifier

    Returns:
        VideoDatasetConfig
    """
    # Check in all categories
    for category in ['quick_demo', 'small_test', 'stress_test', 'large_scale']:
        datasets = DATASETS_CATALOG.get(category, {})
        for ds_id, ds_config in datasets.items():
            if ds_id == dataset_name or ds_config.get('name', '').lower().replace(' ', '-') == dataset_name:
                return _build_dataset_config(ds_id, ds_config)

    # Shortcut mappings
    shortcuts = {
        'blender': 'blender_cc',
        'msr-vtt-100': 'msr_vtt_100',
        'msr-vtt-1000': 'msr_vtt_1000',
        'msr-vtt-full': 'msr_vtt_full',
        'webvid-10k': 'webvid_10k',
        'pexels-100': 'pexels_cc0_100',
        'youcook2': 'youcook2_full',
        'activitynet-1000': 'activitynet_1000'
    }

    if dataset_name in shortcuts:
        return select_dataset(shortcuts[dataset_name])

    raise ValueError(
        f"Dataset '{dataset_name}' not found. Available: {list(shortcuts.keys())}"
    )


def _build_dataset_config(ds_id: str, ds_config: Dict) -> VideoDatasetConfig:
    """Build VideoDatasetConfig from YAML config."""
    source = ds_config.get('source', 'direct_url')

    config = VideoDatasetConfig(
        name=ds_config.get('name', ds_id),
        source=source,
        max_videos=ds_config.get('max_videos') or ds_config.get('video_count')
    )

    if source == "huggingface":
        config.hf_dataset_id = ds_config.get('hf_dataset_id')
        config.hf_split = ds_config.get('hf_split', 'train')
        config.hf_streaming = ds_config.get('streaming', True)

    elif source == "direct_url":
        config.video_urls = [v['url'] for v in ds_config.get('videos', [])]

    elif source == "pexels":
        # Will use Pexels API
        pass

    return config


def progress_callback(metrics: BulkProcessingMetrics) -> None:
    """Callback for progress updates."""
    print(f"\r  Progress: {metrics.processed_videos}/{metrics.total_videos} videos "
          f"({metrics.success_rate:.1f}% success, ${metrics.estimated_total_cost_usd:.2f} cost)   ",
          end='', flush=True)


def main():
    """Main stress test execution."""
    parser = argparse.ArgumentParser(
        description="Stress test vector stores with large video datasets"
    )
    parser.add_argument(
        '--dataset',
        required=True,
        help='Dataset to use (blender, msr-vtt-100, msr-vtt-1000, webvid-10k, etc.)'
    )
    parser.add_argument(
        '--model',
        choices=['marengo', 'nova'],
        default='marengo',
        help='Embedding model (marengo or nova)'
    )
    parser.add_argument(
        '--vector-types',
        default='visual-text',
        help='Marengo vector types (comma-separated: visual-text,audio,visual-image)'
    )
    parser.add_argument(
        '--nova-dimension',
        type=int,
        choices=[3072, 1024, 384, 256],
        default=1024,
        help='Nova embedding dimension'
    )
    parser.add_argument(
        '--stores',
        default='s3vector',
        help='Vector stores (comma-separated: s3vector,opensearch,qdrant,lancedb or "all")'
    )
    parser.add_argument(
        '--lancedb-backend',
        choices=['s3', 'efs', 'ebs'],
        default='s3',
        help='LanceDB backend type'
    )
    parser.add_argument(
        '--max-videos',
        type=int,
        help='Limit number of videos (overrides dataset default)'
    )
    parser.add_argument(
        '--max-cost',
        type=float,
        help='Maximum cost in USD (stops when exceeded)'
    )
    parser.add_argument(
        '--max-hours',
        type=int,
        default=24,
        help='Maximum processing time in hours'
    )
    parser.add_argument(
        '--concurrent',
        type=int,
        default=5,
        help='Number of concurrent video processings'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Batch size for parallel processing'
    )
    parser.add_argument(
        '--s3-bucket',
        default='s3vector-datasets',
        help='S3 bucket for dataset storage'
    )
    parser.add_argument(
        '--output',
        default='stress_test_results.json',
        help='Output file for results'
    )
    parser.add_argument(
        '--embedding-only',
        action='store_true',
        default=True,
        help='Only generate embeddings, do not set up vector stores (default: True)'
    )
    parser.add_argument(
        '--store-in-vector-dbs',
        action='store_true',
        help='Also store embeddings in vector databases (requires vector store setup)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show configuration without processing'
    )

    args = parser.parse_args()

    # Parse vector stores
    if args.stores == 'all':
        stores = ['s3vector', 'opensearch', 'qdrant', 'lancedb']
    else:
        stores = args.stores.split(',')

    # Parse vector types
    vector_types = args.vector_types.split(',')

    # Select dataset
    try:
        dataset_config = select_dataset(args.dataset)
    except ValueError as e:
        print(f"\n❌ Error: {str(e)}\n")
        print("Available datasets:")
        print("  Quick: blender")
        print("  Small: msr-vtt-100, pexels-100")
        print("  Stress: msr-vtt-1000, activitynet-1000, youcook2")
        print("  Large: msr-vtt-full, webvid-10k")
        sys.exit(1)

    # Override max_videos if specified
    if args.max_videos:
        dataset_config.max_videos = args.max_videos

    # Set S3 bucket
    dataset_config.s3_bucket = args.s3_bucket

    print_header(f"S3Vector Stress Test - {dataset_config.name}")

    print(f"📊 Configuration:\n")
    print(f"   Dataset: {dataset_config.name}")
    print(f"   Source: {dataset_config.source}")
    if dataset_config.hf_dataset_id:
        print(f"   HuggingFace ID: {dataset_config.hf_dataset_id}")
    print(f"   Max Videos: {dataset_config.max_videos or 'unlimited'}")
    print(f"\n   Embedding Model: {args.model.upper()}")
    if args.model == 'marengo':
        print(f"   Vector Types: {', '.join(vector_types)}")
    else:
        print(f"   Nova Dimension: {args.nova_dimension}D")
    print(f"\n   Vector Stores: {', '.join(s.upper() for s in stores)}")
    if 'lancedb' in stores:
        print(f"   LanceDB Backend: {args.lancedb_backend.upper()}")
    print(f"\n   Concurrency: {args.concurrent} videos")
    print(f"   Batch Size: {args.batch_size}")
    print(f"   S3 Bucket: {args.s3_bucket}")

    if args.max_cost:
        print(f"\n   💰 Cost Limit: ${args.max_cost:,.2f}")
    if args.max_hours:
        print(f"   ⏱️  Time Limit: {args.max_hours} hours")

    if args.dry_run:
        print("\n✅ Dry run complete - no processing performed\n")
        sys.exit(0)

    # Confirm for large datasets
    if dataset_config.max_videos and dataset_config.max_videos > 500:
        print(f"\n⚠️  WARNING: This will process {dataset_config.max_videos} videos")
        estimated_cost = dataset_config.max_videos * 6.3  # Rough estimate
        print(f"   Estimated cost: ${estimated_cost:,.2f}")
        print(f"   Estimated time: {dataset_config.max_videos / 50:.1f} hours")

        confirm = input("\nProceed? (yes/no): ")
        if confirm.lower() != 'yes':
            print("\n❌ Cancelled\n")
            sys.exit(0)

    print_section("Starting Bulk Processing Pipeline")

    # Determine processing mode
    embedding_only = args.embedding_only and not args.store_in_vector_dbs

    # Create bulk processing config
    bulk_config = BulkProcessingConfig(
        dataset_config=dataset_config,
        embedding_model=EmbeddingModel.MARENGO if args.model == 'marengo' else EmbeddingModel.NOVA,
        marengo_vector_types=vector_types,
        nova_dimension=args.nova_dimension,
        embedding_only=embedding_only,  # Only generate embeddings, no vector store setup
        save_embeddings_to_s3=True,  # Save to S3 for later use
        enabled_vector_stores=stores if not embedding_only else [],
        lancedb_backend=args.lancedb_backend,
        max_concurrent_videos=args.concurrent,
        batch_size=args.batch_size,
        max_cost_usd=args.max_cost,
        max_processing_time_hours=args.max_hours
    )

    print(f"\n   Processing Mode: {'EMBEDDING ONLY (no vector stores)' if embedding_only else 'FULL PIPELINE (embeddings + storage)'}")
    if embedding_only:
        print(f"   Embeddings saved to: s3://{args.s3_bucket}/datasets/embeddings/{dataset_config.name}/")

    # Create bulk processor
    processor = BulkVideoProcessor(bulk_config)

    # Run processing
    print("\n🚀 Processing started...\n")

    try:
        results = processor.process_dataset(progress_callback=progress_callback)

        print("\n")  # New line after progress
        print_section("Processing Complete!")

        print(f"\n📊 RESULTS:\n")
        print(f"   Total Videos: {results.total_videos}")
        print(f"   Successfully Processed: {results.processed_videos}")
        print(f"   Failed: {results.failed_videos}")
        print(f"   Success Rate: {results.success_rate:.1f}%")
        print(f"\n   Embeddings Generated: {results.embeddings_generated}")
        print(f"   Total Processing Time: {results.total_processing_time_sec/3600:.2f} hours")
        print(f"   Avg Time per Video: {results.avg_processing_time_sec:.2f}s")
        print(f"\n   💰 Total Cost: ${results.estimated_total_cost_usd:.2f}")
        print(f"   Cost per Video: ${results.cost_per_video_usd:.4f}")

        # Vector store breakdown
        print(f"\n   📦 Vector Store Results:")
        for store in stores:
            stored = results.vectors_stored.get(store, 0)
            errors = results.storage_errors.get(store, 0)
            success_rate = (stored / (stored + errors) * 100) if (stored + errors) > 0 else 0
            print(f"      {store.upper():12s}: {stored} vectors stored, {errors} errors ({success_rate:.1f}% success)")

        # Generate and save report
        print_section("Generating Report")

        report = processor.generate_report()
        report_file = args.output.replace('.json', '_report.md')

        with open(report_file, 'w') as f:
            f.write(report)

        print(f"   📄 Report saved to: {report_file}")

        # Save detailed results
        results_data = {
            'dataset': dataset_config.name,
            'configuration': {
                'embedding_model': args.model,
                'vector_types': vector_types if args.model == 'marengo' else None,
                'nova_dimension': args.nova_dimension if args.model == 'nova' else None,
                'vector_stores': stores,
                'max_concurrent': args.concurrent,
                'batch_size': args.batch_size
            },
            'metrics': {
                'total_videos': results.total_videos,
                'processed': results.processed_videos,
                'failed': results.failed_videos,
                'success_rate': results.success_rate,
                'embeddings_generated': results.embeddings_generated,
                'processing_time_hours': results.total_processing_time_sec / 3600,
                'avg_time_per_video_sec': results.avg_processing_time_sec,
                'total_cost_usd': results.estimated_total_cost_usd,
                'cost_per_video': results.cost_per_video_usd
            },
            'vector_stores': {
                store: {
                    'vectors_stored': results.vectors_stored.get(store, 0),
                    'errors': results.storage_errors.get(store, 0)
                }
                for store in stores
            },
            'completed_at': results.completed_at
        }

        with open(args.output, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"   💾 Results saved to: {args.output}\n")

        print_header("Stress Test Complete!")

        # Print key insights
        print("\n🎓 KEY INSIGHTS:\n")

        if results.processed_videos > 100:
            print("   ✅ Successfully processed 100+ videos - system handles scale")
        if results.success_rate > 95:
            print("   ✅ High success rate indicates stable pipeline")
        if results.fastest_video_sec and results.slowest_video_sec:
            variance = results.slowest_video_sec / results.fastest_video_sec
            if variance < 3:
                print("   ✅ Low variance in processing time - predictable performance")

        # Vector store comparison
        if len(stores) > 1:
            print("\n   📊 Vector Store Comparison:")
            for store in sorted(stores, key=lambda s: results.vectors_stored.get(s, 0), reverse=True):
                stored = results.vectors_stored.get(store, 0)
                total = results.processed_videos
                percentage = (stored / total * 100) if total > 0 else 0
                print(f"      {store.upper():12s}: {percentage:.1f}% storage success")

    except KeyboardInterrupt:
        print("\n\n⚠️  Processing interrupted by user")
        print(f"\n   Processed so far: {processor.metrics.processed_videos} videos")
        print(f"   Checkpoint saved - can resume with same command\n")
        sys.exit(1)

    except Exception as e:
        print(f"\n\n❌ Stress test failed: {str(e)}\n")
        logger.error(f"Stress test error: {str(e)}", exc_info=True)
        sys.exit(1)


def list_datasets():
    """List all available datasets."""
    print_header("Available Video Datasets")

    for category, datasets in DATASETS_CATALOG.items():
        if category == 'recommendations' or category == 'cost_notes' or category == 'huggingface' or category == 'upload':
            continue

        print(f"\n{category.upper().replace('_', ' ')}:")

        for ds_id, ds_config in datasets.items():
            if isinstance(ds_config, dict):
                name = ds_config.get('name', ds_id)
                video_count = ds_config.get('video_count') or ds_config.get('max_videos', 'variable')
                cost = ds_config.get('estimated_cost_usd', 'N/A')
                print(f"\n  {ds_id}:")
                print(f"    Name: {name}")
                print(f"    Videos: {video_count}")
                print(f"    Cost: ${cost}")
                if ds_config.get('description'):
                    print(f"    Description: {ds_config['description']}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--list-datasets':
        list_datasets()
        sys.exit(0)

    main()
