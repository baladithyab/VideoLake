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
BACKEND_CONFIGS = {
    's3vector': {
        'type': 'sdk',
        'bucket': 'videolake-vectors',
        'index': 'embeddings'
    },
    'qdrant': {
        'type': 'rest',
        'endpoint': 'http://52.90.39.152:6333'
    },
    'lancedb': {
        'type': 'rest',
        'endpoint': 'http://3.91.12.124:8000'
    }
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
        
        # Index vectors
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
        choices=['s3vector', 'qdrant', 'lancedb'],
        help='Backends to index to (space-separated)'
    )
    parser.add_argument(
        '--collection',
        default='videolake-benchmark',
        help='Collection/index name to use'
    )
    
    args = parser.parse_args()
    
    # Load embeddings
    print(f"\n{'='*60}")
    print(f"Loading embeddings from: {args.embeddings}")
    print(f"{'='*60}")
    
    try:
        with open(args.embeddings) as f:
            data = json.load(f)
        
        # Handle both formats: with 'embeddings' key or direct array
        if isinstance(data, dict) and 'embeddings' in data:
            embeddings = data['embeddings']
            print(f"Dataset: {data.get('dataset', 'unknown')}")
            print(f"Modality: {data.get('modality', 'unknown')}")
            print(f"Dimension: {data.get('embedding_dimension', 'unknown')}")
        elif isinstance(data, list):
            embeddings = data
        else:
            print(f"❌ Invalid data format - expected list or dict with 'embeddings' key")
            return 1
        
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
    
    # Index to each backend
    results = {}
    for backend in args.backends:
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