#!/usr/bin/env python3
"""
Validate Test Embeddings

Verifies that generated embeddings are properly formatted and ready for
backend indexing and benchmarking.
"""

import json
import sys
from pathlib import Path
import numpy as np


def validate_embedding_file(filepath: Path) -> dict:
    """Validate a single embedding file."""
    print(f"\n📋 Validating: {filepath.name}")
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Basic structure checks
    checks = {
        "has_embeddings": "embeddings" in data and len(data["embeddings"]) > 0,
        "has_dimension": "embedding_dimension" in data,
        "has_dataset": "dataset" in data,
    }
    
    # Validate embedding structure
    if checks["has_embeddings"]:
        first_emb = data["embeddings"][0]
        checks["has_values"] = "values" in first_emb
        checks["has_metadata"] = "metadata" in first_emb
        
        if checks["has_values"]:
            values = first_emb["values"]
            checks["correct_dimension"] = len(values) == data["embedding_dimension"]
            checks["values_are_floats"] = all(isinstance(v, (int, float)) for v in values[:10])
            
            # Check normalization (should be unit vectors)
            vector = np.array(values)
            norm = np.linalg.norm(vector)
            checks["normalized"] = bool(abs(norm - 1.0) < 0.01)
    
    # Print results
    for check, result in checks.items():
        status = "✓" if result else "✗"
        print(f"  {status} {check.replace('_', ' ').title()}: {result}")
    
    # Summary stats
    if checks["has_embeddings"]:
        print(f"\n📊 Statistics:")
        print(f"  Embedding count: {len(data['embeddings'])}")
        print(f"  Dimension: {data['embedding_dimension']}")
        if "modality" in data:
            print(f"  Modality: {data['modality']}")
    
    return {
        "file": filepath.name,
        "valid": all(checks.values()),
        "checks": checks,
        "count": len(data["embeddings"]) if checks["has_embeddings"] else 0
    }


def main():
    embeddings_dir = Path("embeddings")
    
    if not embeddings_dir.exists():
        print("❌ Embeddings directory not found!")
        sys.exit(1)
    
    print("=" * 60)
    print("🔍 EMBEDDING VALIDATION")
    print("=" * 60)
    
    # Find all embedding files
    embedding_files = list(embeddings_dir.glob("test-embeddings*.json"))
    
    if not embedding_files:
        print("❌ No embedding files found!")
        sys.exit(1)
    
    print(f"\nFound {len(embedding_files)} embedding file(s)")
    
    # Validate each file
    results = []
    for filepath in sorted(embedding_files):
        result = validate_embedding_file(filepath)
        results.append(result)
    
    # Overall summary
    print("\n" + "=" * 60)
    print("📈 VALIDATION SUMMARY")
    print("=" * 60)
    
    all_valid = all(r["valid"] for r in results)
    total_embeddings = sum(r["count"] for r in results)
    
    print(f"\nTotal embedding files: {len(results)}")
    print(f"Total embeddings: {total_embeddings}")
    print(f"All validated: {'✓ YES' if all_valid else '✗ NO'}")
    
    # Check manifest
    manifest_path = embeddings_dir / "manifest.json"
    if manifest_path.exists():
        print(f"\n✓ Manifest file exists: {manifest_path.name}")
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        print(f"  Dataset: {manifest.get('dataset', 'N/A')}")
        print(f"  Ready for indexing: {manifest.get('usage', {}).get('ready_for_indexing', False)}")
    
    if all_valid:
        print("\n✅ All embeddings are valid and ready for benchmarking!")
        print("\nCompatible backends:")
        print("  • S3Vector")
        print("  • Qdrant")
        print("  • LanceDB")
        sys.exit(0)
    else:
        print("\n❌ Some embeddings failed validation!")
        sys.exit(1)


if __name__ == "__main__":
    main()