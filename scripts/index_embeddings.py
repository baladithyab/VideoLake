#!/usr/bin/env python3
"""Index embeddings into all backends."""
import json
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backend_adapters import get_backend_adapter
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Backend configurations
# For REST backends we rely on DEFAULT_ENDPOINTS in scripts.backend_adapters
# and only specify minimal type hints here.
BACKEND_CONFIGS = {
    's3vector': {
        'type': 'sdk',
        'bucket': 'videolake-vectors',
        'index': 'embeddings',
    },
    # Qdrant variants
    'qdrant': {'type': 'rest'},        # ECS Fargate + EFS (canonical)
    'qdrant-efs': {'type': 'rest'},    # alias for qdrant
    'qdrant-ebs': {'type': 'rest'},    # EC2 + EBS
    # LanceDB variants (REST API wrappers)
    'lancedb': {'type': 'rest'},       # ECS Fargate + EFS (canonical)
    'lancedb-efs': {'type': 'rest'},
    'lancedb-s3': {'type': 'rest'},    # ECS Fargate + S3 backend
    'lancedb-ebs': {'type': 'rest'},   # ECS Fargate + provisioned EFS (EBS-like)
    # LanceDB embedded variants (direct Python SDK on EC2)
    'lancedb-embedded': {'type': 'embedded'},
    'lancedb-s3-embedded': {'type': 'embedded'},
    'lancedb-efs-embedded': {'type': 'embedded'},
    'lancedb-ebs-embedded': {'type': 'embedded'},
    # New naming convention aliases
    'lancedb-embedded-s3': {'type': 'embedded'},
    'lancedb-embedded-efs': {'type': 'embedded'},
    'lancedb-embedded-ebs': {'type': 'embedded'},
    # OpenSearch with S3 Vectors engine (or regular knn on fallback)
    'opensearch': {'type': 'opensearch'},
}

# Default S3Vector index names per embedding modality
MODALITY_S3VECTOR_INDEX = {
    "text": "videolake-benchmark-visual-text",
    "image": "videolake-benchmark-visual-image",
    "audio": "videolake-benchmark-audio",
}



def index_to_backend(backend_name: str, embeddings: list, collection_name: str) -> bool:
    """
    Index embeddings to a specific backend.

    Args:
        backend_name: Name of backend (s3vector, qdrant, lancedb)
        embeddings: List of embedding objects from JSON
        collection_name: Collection/index name to use

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Indexing to {backend_name.upper()}")
    print(f"{'='*60}")

    config = BACKEND_CONFIGS.get(backend_name)
    if not config:
        logger.error(f"Unknown backend: {backend_name}")
        return False

    try:
        # Get backend adapter
        adapter = get_backend_adapter(backend_name, config)

        # Health check first
        print(f"Performing health check...")
        if not adapter.health_check():
            print(f"❌ {backend_name} not accessible")
            return False

        print(f"✅ {backend_name} is accessible")

        # Prepare vectors and metadata
        vectors = [emb['values'] for emb in embeddings]
        metadata = []

        for emb in embeddings:
            meta = {
                'id': emb['id'],
                'video_id': emb['video_id'],
                'modality': emb['modality'],
                'collection': collection_name
            }
            # Add any additional metadata fields
            if 'metadata' in emb:
                meta.update(emb['metadata'])
            metadata.append(meta)

        print(f"Indexing {len(vectors)} vectors to collection '{collection_name}'...")

        # Index vectors (S3Vector adapter will lazily create the index if needed)
        result = adapter.index_vectors(vectors, metadata, collection=collection_name)

        if result.get('success'):
            duration = result.get('duration_seconds', 0)
            print(f"✅ Successfully indexed {len(vectors)} vectors")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Rate: {len(vectors)/duration:.1f} vectors/sec" if duration > 0 else "")
            return True
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Indexing failed: {error}")
            return False

    except Exception as e:
        logger.exception(f"Exception while indexing to {backend_name}")
        print(f"❌ Error: {e}")
        return False


def main():
    """Main indexing workflow"""
    parser = argparse.ArgumentParser(
        description='Index embeddings into vector store backends'
    )
    parser.add_argument(
        '--embeddings',
        required=True,
        help='Path to embeddings JSON file'
    )
    parser.add_argument(
        '--backends',
        nargs='+',
        default=['s3vector', 'qdrant', 'lancedb'],
        help=(
            'Backends to index to (space-separated or comma-separated). '
            'Variants include qdrant-efs, qdrant-ebs, lancedb-efs, lancedb-s3, lancedb-ebs.'
        ),
    )
    parser.add_argument(
        '--collection',
        default='videolake-benchmark',
        help='Collection/index name to use'
    )
    parser.add_argument(
        '--s3vector-index',
        help='Override S3Vector index name (defaults to BACKEND_CONFIGS["s3vector"]["index"])'
    )
    parser.add_argument(
        '--qdrant-endpoint',
        help='Override Qdrant REST endpoint, e.g. http://host:6333'
    )
    parser.add_argument(
        '--lancedb-endpoint',
        help='Override LanceDB REST endpoint, e.g. http://host:8000'
    )


    args = parser.parse_args()
    # Apply REST endpoint overrides before using BACKEND_CONFIGS
    if args.qdrant_endpoint:
        BACKEND_CONFIGS['qdrant']['endpoint'] = args.qdrant_endpoint
    if args.lancedb_endpoint:
        # Apply LanceDB endpoint override to all REST LanceDB variants
        for name in ('lancedb', 'lancedb-efs', 'lancedb-s3', 'lancedb-ebs'):
            if name in BACKEND_CONFIGS:
                BACKEND_CONFIGS[name]['endpoint'] = args.lancedb_endpoint



    # Load embeddings
    print(f"\n{'='*60}")
    print(f"Loading embeddings from: {args.embeddings}")
    print(f"{'='*60}")

    modality = None
    dataset = "unknown"

    try:
        with open(args.embeddings) as f:
            data = json.load(f)

        # Handle both formats: with 'embeddings' key or direct array
        if isinstance(data, dict) and 'embeddings' in data:
            embeddings = data['embeddings']
            dataset = data.get('dataset', 'unknown')
            modality = data.get('modality')
            print(f"Dataset: {dataset}")
            print(f"Modality: {modality or 'unknown'}")
            print(f"Dimension: {data.get('embedding_dimension', 'unknown')}")
        elif isinstance(data, list):
            embeddings = data
        else:
            print(f"❌ Invalid data format - expected list or dict with 'embeddings' key")
            return 1

        # Derive S3Vector index name from modality if not explicitly provided
        s3vector_index = args.s3vector_index
        if s3vector_index is None and modality:
            s3vector_index = MODALITY_S3VECTOR_INDEX.get(modality)
        if s3vector_index:
            BACKEND_CONFIGS['s3vector']['index'] = s3vector_index

        print(f"Using S3Vector index: {BACKEND_CONFIGS['s3vector'].get('index', 'embeddings')}\n")

        print(f"Loaded {len(embeddings)} embeddings")

        if len(embeddings) == 0:
            print("❌ No embeddings found in file")
            return 1

        # Validate first embedding
        first = embeddings[0]
        if 'values' not in first or 'id' not in first:
            print("❌ Invalid embedding format - missing 'values' or 'id' field")
            return 1

        print(f"Embedding dimension: {len(first['values'])}")
        print(f"Collection: {args.collection}")

    except FileNotFoundError:
        print(f"❌ Embeddings file not found: {args.embeddings}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON file: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error loading embeddings: {e}")
        return 1

    # Process backends list (handle comma-separation)
    backends = []
    for b in args.backends:
        backends.extend(b.split(','))
    backends = [b.strip() for b in backends if b.strip()]

    # Index to each backend
    results = {}
    for backend in backends:
        if backend not in BACKEND_CONFIGS:
            print(f"❌ Unknown backend: {backend}")
            results[backend] = 'failed (unknown backend)'
            continue

        try:
            success = index_to_backend(backend, embeddings, args.collection)
            results[backend] = 'success' if success else 'failed'
        except Exception as e:
            logger.exception(f"Unexpected error with {backend}")
            print(f"❌ Unexpected error: {e}")
            results[backend] = f'error: {str(e)}'

    # Print summary
    print("\n" + "="*60)
    print("INDEXING SUMMARY")
    print("="*60)
    for backend, status in results.items():
        status_icon = "✅" if status == 'success' else "❌"
        print(f"{status_icon} {backend}: {status}")

    # Return exit code
    all_success = all(r == 'success' for r in results.values())
    return 0 if all_success else 1


if __name__ == '__main__':
    sys.exit(main())