#!/usr/bin/env python3
"""
Complete S3Vector Demo Script

This script demonstrates the complete capabilities of the S3Vector project:
1. Video processing with both Marengo (multi-vector) and Nova (single-vector)
2. Storage across all 4 vector stores (S3Vector, OpenSearch, Qdrant, LanceDB)
3. Parallel querying with real-time performance comparison
4. Cost and latency analysis

Usage:
    python scripts/run_complete_demo.py --video big-buck-bunny --models all --stores all
    python scripts/run_complete_demo.py --video sintel --models marengo --stores s3vector,qdrant
    python scripts/run_complete_demo.py --help
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.embedding_model_selector import EmbeddingModelSelector, EmbeddingModel, UnifiedEmbeddingResult
from src.services.parallel_vector_store_comparison import ParallelVectorStoreComparison, ComparisonResult
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Demo video catalog (Creative Commons licensed)
DEMO_VIDEOS = {
    "big-buck-bunny": {
        "title": "Big Buck Bunny",
        "url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "duration_sec": 596,
        "description": "A giant rabbit's comical revenge",
        "license": "Creative Commons Attribution 3.0",
        "source": "Blender Foundation"
    },
    "sintel": {
        "title": "Sintel",
        "url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
        "duration_sec": 888,
        "description": "A young woman's quest to save her dragon friend",
        "license": "Creative Commons Attribution 3.0",
        "source": "Blender Foundation"
    },
    "elephants-dream": {
        "title": "Elephants Dream",
        "url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "duration_sec": 654,
        "description": "The first Blender Open Movie from 2006",
        "license": "Creative Commons Attribution 3.0",
        "source": "Blender Foundation"
    },
    "tears-of-steel": {
        "title": "Tears of Steel",
        "url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
        "duration_sec": 734,
        "description": "Sci-fi film with visual effects",
        "license": "Creative Commons Attribution 3.0",
        "source": "Blender Foundation"
    }
}


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")


def print_section(text: str) -> None:
    """Print formatted section."""
    print(f"\n{'-'*80}")
    print(f"  {text}")
    print(f"{'-'*80}\n")


def run_embedding_comparison_demo(
    video_id: str,
    models: List[str],
    s3_video_uri: str
) -> Dict[str, UnifiedEmbeddingResult]:
    """
    Demonstrate embedding model comparison: Marengo vs Nova.

    Args:
        video_id: Video identifier
        models: Which models to test ('marengo', 'nova', or 'all')
        s3_video_uri: S3 URI of uploaded video

    Returns:
        Dict with embedding results from each model
    """
    print_section("PHASE 1: Embedding Model Comparison (Marengo vs Nova)")

    results = {}

    if 'marengo' in models or 'all' in models:
        print("\n🎬 Processing with MARENGO (Multi-Vector Approach)...")
        print("   - Generates 3 separate embedding spaces:")
        print("     • visual-text (1024D)")
        print("     • visual-image (1024D)")
        print("     • audio (1024D)")
        print("   - User chooses which vectors to generate\n")

        try:
            marengo_selector = EmbeddingModelSelector(model=EmbeddingModel.MARENGO)
            marengo_result = marengo_selector.process_video(
                video_uri=s3_video_uri,
                vector_types=["visual-text", "visual-image", "audio"]
            )

            results['marengo'] = marengo_result

            print(f"✅ Marengo processing complete!")
            print(f"   - Embeddings generated: {marengo_result.total_embedding_count}")
            print(f"   - Total dimensions: {marengo_result.total_dimensions}D")
            print(f"   - Processing time: {marengo_result.processing_time_ms}ms")
            print(f"   - Vector types: {', '.join(marengo_result.embeddings.keys())}\n")

        except Exception as e:
            print(f"❌ Marengo processing failed: {str(e)}\n")
            results['marengo'] = {'error': str(e)}

    if 'nova' in models or 'all' in models:
        print("\n🌟 Processing with NOVA (Single-Vector Approach)...")
        print("   - Generates 1 unified embedding space:")
        print("     • unified (1024D across all modalities)")
        print("   - User chooses dimension (3072/1024/384/256)")
        print("   - User chooses mode (AUDIO_VIDEO_COMBINED, etc.)\n")

        try:
            nova_selector = EmbeddingModelSelector(
                model=EmbeddingModel.NOVA,
                embedding_dimension=1024
            )
            nova_result = nova_selector.process_video(
                video_uri=s3_video_uri,
                embedding_mode="AUDIO_VIDEO_COMBINED"
            )

            results['nova'] = nova_result

            print(f"✅ Nova processing complete!")
            print(f"   - Embeddings generated: {nova_result.total_embedding_count}")
            print(f"   - Unified dimension: {nova_result.total_dimensions}D")
            print(f"   - Processing time: {nova_result.processing_time_ms}ms")
            print(f"   - Embedding keys: {', '.join(nova_result.embeddings.keys())}\n")

        except Exception as e:
            print(f"❌ Nova processing failed: {str(e)}\n")
            results['nova'] = {'error': str(e)}

    # Comparison summary
    if 'marengo' in results and 'nova' in results:
        if not isinstance(results['marengo'], dict) or 'error' not in results['marengo']:
            if not isinstance(results['nova'], dict) or 'error' not in results['nova']:
                print("\n📊 COMPARISON SUMMARY:")
                print(f"   Marengo: {results['marengo'].total_embedding_count} embeddings, "
                      f"{results['marengo'].total_dimensions}D total")
                print(f"   Nova: {results['nova'].total_embedding_count} embedding, "
                      f"{results['nova'].total_dimensions}D total")
                print(f"\n   Storage Efficiency:")
                print(f"   - Marengo stores {results['marengo'].total_embedding_count} vectors per video")
                print(f"   - Nova stores {results['nova'].total_embedding_count} vector per video")
                print(f"   - Nova reduces storage by {((results['marengo'].total_embedding_count - 1) / results['marengo'].total_embedding_count * 100):.1f}%\n")

    return results


def run_vector_store_comparison_demo(
    index_name: str,
    query_vector: List[float],
    enabled_stores: List[str],
    top_k: int = 10
) -> ComparisonResult:
    """
    Demonstrate parallel vector store querying with metrics.

    Args:
        index_name: Index/collection name
        query_vector: Query embedding
        enabled_stores: Which stores to query
        top_k: Number of results

    Returns:
        ComparisonResult with metrics from all stores
    """
    print_section("PHASE 2: Vector Store Performance Comparison")

    print(f"\n🔍 Querying {len(enabled_stores)} vector stores in parallel...")
    print(f"   Stores: {', '.join(s.upper() for s in enabled_stores)}")
    print(f"   Index: {index_name}")
    print(f"   Vector dimension: {len(query_vector)}D")
    print(f"   Top K: {top_k}\n")

    # Create comparison service
    comparison = ParallelVectorStoreComparison(
        enabled_stores=enabled_stores,
        max_workers=len(enabled_stores)
    )

    # Execute parallel queries
    start_time = time.time()
    result = comparison.query_all_stores(
        query_vector=query_vector,
        index_name=index_name,
        top_k=top_k
    )
    total_time_ms = (time.time() - start_time) * 1000

    print(f"✅ Parallel query complete in {round(total_time_ms, 2)}ms\n")

    # Display results
    print("\n📊 PERFORMANCE RESULTS:\n")

    ranking = result.get_ranking()
    for rank, (store, latency) in enumerate(ranking, 1):
        metrics = result.metrics[store]
        print(f"   {rank}. {store.upper():15s} - {round(latency, 2):6.2f}ms - "
              f"{metrics.result_count} results - {metrics.latency_category}")

    if result.failed_queries > 0:
        print(f"\n⚠️  {result.failed_queries} store(s) failed to query")

    print(f"\n   Average latency: {round(result.avg_latency_ms, 2)}ms")
    print(f"   Fastest: {result.fastest_store.upper() if result.fastest_store else 'N/A'}")
    print(f"   Slowest: {result.slowest_store.upper() if result.slowest_store else 'N/A'}\n")

    return result


def main():
    """Main demo execution."""
    parser = argparse.ArgumentParser(
        description="Complete S3Vector Demo - Embedding Models + Vector Store Comparison"
    )
    parser.add_argument(
        '--video',
        choices=list(DEMO_VIDEOS.keys()),
        default='big-buck-bunny',
        help='Demo video to process'
    )
    parser.add_argument(
        '--models',
        default='all',
        help='Embedding models to test (marengo, nova, or all)'
    )
    parser.add_argument(
        '--stores',
        default='all',
        help='Vector stores to query (s3vector,opensearch,qdrant,lancedb or all)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Number of results to retrieve per store'
    )
    parser.add_argument(
        '--skip-processing',
        action='store_true',
        help='Skip video processing, only run queries'
    )
    parser.add_argument(
        '--output',
        default='demo_results.json',
        help='Output file for results'
    )

    args = parser.parse_args()

    # Parse models and stores
    models = ['marengo', 'nova'] if args.models == 'all' else [args.models]
    stores = ['s3vector', 'opensearch', 'qdrant', 'lancedb'] if args.stores == 'all' else args.stores.split(',')

    # Get video info
    video_info = DEMO_VIDEOS[args.video]

    print_header(f"S3Vector Complete Demo - {video_info['title']}")

    print(f"\n📹 Video: {video_info['title']}")
    print(f"   Source: {video_info['source']}")
    print(f"   Duration: {video_info['duration_sec']}s")
    print(f"   License: {video_info['license']}\n")

    print(f"🎯 Demo Configuration:")
    print(f"   Embedding Models: {', '.join(m.upper() for m in models)}")
    print(f"   Vector Stores: {', '.join(s.upper() for s in stores)}")
    print(f"   Top K Results: {args.top_k}\n")

    # Phase 1: Embedding comparison (if not skipped)
    embedding_results = {}
    if not args.skip_processing:
        # For demo purposes, assume video is already in S3
        # In production, you'd download and upload first
        s3_video_uri = f"s3://demo-bucket/{args.video}.mp4"

        embedding_results = run_embedding_comparison_demo(
            video_id=args.video,
            models=models,
            s3_video_uri=s3_video_uri
        )
    else:
        print_section("PHASE 1: SKIPPED (using existing embeddings)")

    # Phase 2: Vector store comparison
    # For demo, use a sample query vector
    # In production, you'd use actual embeddings from Phase 1
    if embedding_results and 'marengo' in embedding_results:
        marengo_result = embedding_results['marengo']
        if hasattr(marengo_result, 'embeddings') and 'visual-text' in marengo_result.embeddings:
            query_vector = marengo_result.embeddings['visual-text'][0] if marengo_result.embeddings['visual-text'] else None
        else:
            query_vector = None
    else:
        query_vector = None

    if query_vector:
        comparison_result = run_vector_store_comparison_demo(
            index_name="demo-videos",
            query_vector=query_vector,
            enabled_stores=stores,
            top_k=args.top_k
        )

        # Generate comparison report
        print_section("PHASE 3: Generating Comparison Report")

        comparison_service = ParallelVectorStoreComparison(enabled_stores=stores)
        report = comparison_service.generate_comparison_report(comparison_result)

        # Save report
        report_file = args.output.replace('.json', '_report.md')
        with open(report_file, 'w') as f:
            f.write(report)

        print(f"\n📄 Comparison report saved to: {report_file}\n")

        # Save detailed results
        results_data = {
            'video': video_info,
            'embedding_models': models,
            'vector_stores': stores,
            'embedding_results': {
                model: {
                    'model_type': res.model_type if hasattr(res, 'model_type') else None,
                    'approach': res.embedding_approach if hasattr(res, 'embedding_approach') else None,
                    'embeddings_count': res.total_embedding_count if hasattr(res, 'total_embedding_count') else 0,
                    'total_dimensions': res.total_dimensions if hasattr(res, 'total_dimensions') else 0,
                    'processing_time_ms': res.processing_time_ms if hasattr(res, 'processing_time_ms') else 0
                }
                for model, res in embedding_results.items()
                if hasattr(res, 'model_type')
            },
            'comparison_summary': comparison_result.get_summary_table()
        }

        with open(args.output, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

        print(f"💾 Detailed results saved to: {args.output}\n")

    else:
        print("\n⚠️  No query vector available - skipping vector store comparison\n")

    print_header("Demo Complete!")

    # Print key takeaways
    print("\n🎓 KEY TAKEAWAYS:\n")
    print("   1. EMBEDDING MODELS:")
    print("      • Marengo: 3 separate spaces → choose which vectors to generate")
    print("      • Nova: 1 unified space → simpler, cross-modal search\n")

    print("   2. VECTOR STORES:")
    print("      • S3Vector: Native AWS, cost-effective")
    print("      • OpenSearch: S3Vector backend, hybrid search")
    print("      • Qdrant: High performance, cloud/local")
    print("      • LanceDB: Flexible backends (S3/EFS/EBS)\n")

    print("   3. PERFORMANCE:")
    if 'comparison_result' in locals() and comparison_result.fastest_store:
        print(f"      • Fastest: {comparison_result.fastest_store.upper()}")
        print(f"      • Average: {round(comparison_result.avg_latency_ms, 2)}ms\n")
    else:
        print("      • Run with --stores all to see performance comparison\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {str(e)}\n")
        logger.error(f"Demo error: {str(e)}", exc_info=True)
        sys.exit(1)
