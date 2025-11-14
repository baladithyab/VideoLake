#!/usr/bin/env python3
"""
Generate Test Embeddings for Backend Benchmarking

Creates synthetic embeddings that mimic AWS Bedrock Marengo multimodal outputs.
These embeddings follow the correct format and dimensions for benchmarking S3Vector,
Qdrant, and LanceDB backends without requiring actual video processing.

Usage:
    python scripts/generate_test_embeddings.py --count 100 --dimension 1024
    python scripts/generate_test_embeddings.py --count 10 --dimension 1536 --output embeddings/quick-test.json
"""

import json
import numpy as np
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import hashlib


def generate_normalized_embedding(dimension: int, seed: int) -> List[float]:
    """
    Generate a normalized random embedding vector.
    
    Args:
        dimension: Embedding dimension (1024 or 1536)
        seed: Random seed for reproducibility
        
    Returns:
        List of floats representing normalized embedding
    """
    np.random.seed(seed)
    # Generate random vector
    vector = np.random.randn(dimension).astype(np.float32)
    # Normalize to unit length (cosine similarity ready)
    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


def generate_test_embeddings(
    count: int,
    dimension: int = 1024,
    modalities: List[str] | None = None,
    dataset_name: str = "synthetic-test"
) -> Dict[str, Any]:
    """
    Generate a batch of test embeddings with metadata.
    
    Args:
        count: Number of embeddings to generate
        dimension: Embedding dimension (1024 or 1536)
        modalities: List of modalities (text, image, audio)
        dataset_name: Name of the test dataset
        
    Returns:
        Dictionary with embeddings and metadata
    """
    if modalities is None:
        modalities = ["text", "image", "audio"]
    
    embeddings = []
    
    for i in range(count):
        video_id = f"test_video_{i:04d}"
        
        # Generate embedding for each modality
        embedding_data = {
            "video_id": video_id,
            "dataset": dataset_name,
            "embeddings": {},
            "metadata": {
                "title": f"Test Video {i+1}",
                "description": f"Synthetic test content for benchmarking ({dimension}D)",
                "duration_sec": np.random.uniform(10, 120),
                "resolution": f"{np.random.choice([720, 1080, 1440])}p",
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        # Generate embeddings for each modality
        for modality in modalities:
            seed = int(hashlib.md5(f"{video_id}_{modality}".encode()).hexdigest()[:8], 16)
            embedding_vector = generate_normalized_embedding(dimension, seed)
            
            embedding_data["embeddings"][modality] = {
                "values": embedding_vector,
                "dimension": dimension,
                "modality": modality,
                "model": "synthetic-bedrock-marengo-2.7",
                "normalized": True
            }
        
        embeddings.append(embedding_data)
    
    return {
        "dataset": dataset_name,
        "embedding_count": count,
        "embedding_dimension": dimension,
        "modalities": modalities,
        "format_version": "1.0",
        "generated_at": datetime.utcnow().isoformat(),
        "embeddings": embeddings
    }


def create_flat_format_for_backend(embeddings_data: Dict[str, Any], modality: str) -> List[Dict[str, Any]]:
    """
    Convert embeddings to flat format for backend ingestion.
    
    Args:
        embeddings_data: Full embeddings data structure
        modality: Specific modality to extract (text, image, or audio)
        
    Returns:
        List of flat embedding records ready for backend insertion
    """
    flat_embeddings = []
    
    for item in embeddings_data["embeddings"]:
        video_id = item["video_id"]
        
        if modality in item["embeddings"]:
            embedding_info = item["embeddings"][modality]
            
            flat_record = {
                "id": f"{video_id}_{modality}",
                "video_id": video_id,
                "modality": modality,
                "values": embedding_info["values"],
                "dimension": embedding_info["dimension"],
                "metadata": {
                    **item["metadata"],
                    "embedding_modality": modality,
                    "model": embedding_info["model"]
                }
            }
            
            flat_embeddings.append(flat_record)
    
    return flat_embeddings


def save_embeddings(embeddings_data: Dict[str, Any], output_path: Path) -> None:
    """Save embeddings to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(embeddings_data, f, indent=2)
    
    print(f"✓ Saved embeddings: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def create_manifest(embeddings_data: Dict[str, Any], output_dir: Path) -> None:
    """Create manifest file with embedding statistics."""
    manifest = {
        "dataset": embeddings_data["dataset"],
        "generated_at": embeddings_data["generated_at"],
        "format_version": embeddings_data["format_version"],
        "statistics": {
            "total_videos": embeddings_data["embedding_count"],
            "embedding_dimension": embeddings_data["embedding_dimension"],
            "modalities": embeddings_data["modalities"],
            "total_embeddings": embeddings_data["embedding_count"] * len(embeddings_data["modalities"])
        },
        "files": {
            "full": "test-embeddings.json",
            "by_modality": {
                modality: f"test-embeddings-{modality}.json"
                for modality in embeddings_data["modalities"]
            }
        },
        "usage": {
            "description": "Synthetic embeddings for backend benchmarking",
            "ready_for_indexing": True,
            "backends_compatible": ["s3vector", "qdrant", "lancedb"]
        }
    }
    
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"✓ Created manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic embeddings for backend benchmarking",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of embeddings to generate (default: 100)"
    )
    
    parser.add_argument(
        "--dimension",
        type=int,
        choices=[1024, 1536],
        default=1024,
        help="Embedding dimension (default: 1024)"
    )
    
    parser.add_argument(
        "--modalities",
        nargs="+",
        choices=["text", "image", "audio"],
        default=["text", "image", "audio"],
        help="Modalities to generate (default: all)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="embeddings/test-embeddings.json",
        help="Output file path (default: embeddings/test-embeddings.json)"
    )
    
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="synthetic-test",
        help="Dataset name (default: synthetic-test)"
    )
    
    parser.add_argument(
        "--split-by-modality",
        action="store_true",
        help="Also save separate files per modality"
    )
    
    args = parser.parse_args()
    
    print(f"Generating {args.count} synthetic embeddings...")
    print(f"  Dimension: {args.dimension}")
    print(f"  Modalities: {', '.join(args.modalities)}")
    print(f"  Dataset: {args.dataset_name}")
    
    # Generate embeddings
    embeddings_data = generate_test_embeddings(
        count=args.count,
        dimension=args.dimension,
        modalities=args.modalities,
        dataset_name=args.dataset_name
    )
    
    # Save full embeddings
    output_path = Path(args.output)
    save_embeddings(embeddings_data, output_path)
    
    # Optionally save per-modality files
    if args.split_by_modality:
        output_dir = output_path.parent
        for modality in args.modalities:
            flat_embeddings = create_flat_format_for_backend(embeddings_data, modality)
            
            modality_data = {
                "dataset": embeddings_data["dataset"],
                "modality": modality,
                "embedding_count": len(flat_embeddings),
                "embedding_dimension": args.dimension,
                "generated_at": embeddings_data["generated_at"],
                "embeddings": flat_embeddings
            }
            
            modality_path = output_dir / f"test-embeddings-{modality}.json"
            save_embeddings(modality_data, modality_path)
    
    # Create manifest
    create_manifest(embeddings_data, output_path.parent)
    
    print(f"\n✓ Generation complete!")
    print(f"\nStatistics:")
    print(f"  Total videos: {args.count}")
    print(f"  Modalities per video: {len(args.modalities)}")
    print(f"  Total embeddings: {args.count * len(args.modalities)}")
    print(f"  Dimension: {args.dimension}")
    print(f"  Total vectors: {args.count * len(args.modalities) * args.dimension:,}")
    
    print(f"\nReady for backend indexing:")
    print(f"  ✓ S3Vector")
    print(f"  ✓ Qdrant")
    print(f"  ✓ LanceDB")
    
    print(f"\nNext steps:")
    print(f"  1. Use these embeddings with benchmark scripts")
    print(f"  2. Index into all backends")
    print(f"  3. Run comparative benchmarks")


if __name__ == "__main__":
    main()