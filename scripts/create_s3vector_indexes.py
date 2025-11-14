#!/usr/bin/env python3
"""Create S3Vector indexes programmatically based on embedding specs.

This script is Marengo-aware: it inspects an embeddings JSON file to
infer the vector dimension and (optionally) modality, then ensures that
appropriate S3Vector indexes exist in the configured vector bucket.

It is intended to be run *before* scripts/index_embeddings.py so that
S3Vector has matching-dimension indexes for the benchmark collections.

Usage examples:

  python scripts/create_s3vector_indexes.py \
      --embeddings embeddings/test-embeddings-text.json \
      --bucket videolake-vectors \
      --index-prefix videolake-benchmark

This will create an index named:
  <index-prefix>-<modality>
for example: "videolake-benchmark-text" when modality=="text".

If the embeddings JSON does not declare a modality, the base
--index-name will be used as-is.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Ensure project root on path so we can reuse existing managers
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.s3vector.index_manager import S3VectorIndexManager
from src.services.s3_vector_storage import S3VectorStorageManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def _detect_dimension_and_modality(embeddings_path: Path) -> tuple[int, Optional[str]]:
    """Return (dimension, modality) from an embeddings JSON file.

    Supports both formats:
    - {"dataset": ..., "modality": ..., "embedding_dimension": 1024, "embeddings": [...]} 
    - [ {"values": [...], ...}, ... ]
    """
    with embeddings_path.open() as f:
        data = json.load(f)

    modality: Optional[str] = None
    dimension: Optional[int] = None

    if isinstance(data, dict):
        modality = data.get("modality")
        if isinstance(data.get("embedding_dimension"), int):
            dimension = data["embedding_dimension"]
        embeddings = data.get("embeddings") or []
    else:
        embeddings = data

    if dimension is None:
        if isinstance(embeddings, list) and embeddings:
            first = embeddings[0]
            if isinstance(first, dict) and isinstance(first.get("values"), list):
                dimension = len(first["values"])

    if dimension is None:
        raise ValueError("Could not infer embedding dimension from file; expected 'embedding_dimension' field or non-empty 'values' array")

    return dimension, modality


def ensure_s3vector_index(bucket: str, index_name: str, dimension: int) -> None:
    """Ensure an S3Vector index exists for the given bucket/index/dimension.

    Uses S3VectorIndexManager.create_vector_index, which is idempotent and
    returns status "already_exists" if the index is present.
    """
    logger.info(
        "Ensuring S3Vector index exists", extra={
            "bucket": bucket,
            "index_name": index_name,
            "dimension": dimension,
        },
    )

    index_mgr = S3VectorIndexManager()

    result = index_mgr.create_vector_index(
        bucket_name=bucket,
        index_name=index_name,
        dimensions=dimension,
        distance_metric="cosine",
        data_type="float32",
    )

    status = result.get("status", "unknown")
    logger.info(
        "S3Vector index ensure result",
        extra={"bucket": bucket, "index_name": index_name, "dimension": dimension, "status": status},
    )

    print(f"S3Vector index '{index_name}' in bucket '{bucket}': {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Marengo-aware S3Vector indexes based on embedding specs")
    parser.add_argument("--embeddings", required=True, help="Path to embeddings JSON file")
    parser.add_argument("--bucket", default="videolake-vectors", help="S3Vector bucket name")
    parser.add_argument(
        "--index-prefix",
        default="videolake-benchmark",
        help="Prefix for index name; final name may be '<prefix>-<modality>'",
    )
    parser.add_argument(
        "--index-name",
        default=None,
        help="Explicit index name override (if provided, modality suffix is not added)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    embeddings_path = Path(args.embeddings)

    if not embeddings_path.is_file():
        print(f"Embeddings file not found: {embeddings_path}")
        return 1

    try:
        dimension, modality = _detect_dimension_and_modality(embeddings_path)
    except Exception as e:
        logger.exception("Failed to inspect embeddings file")
        print(f"Failed to inspect embeddings file: {e}")
        return 1

    print(f"Detected embedding dimension: {dimension}")
    if modality:
        print(f"Detected modality: {modality}")

    if args.index_name:
        index_name = args.index_name
    else:
        # If modality present (e.g., 'text', 'visual-text', 'audio') suffix it
        suffix = modality.replace("_", "-") if modality else None
        index_name = f"{args.index_prefix}-{suffix}" if suffix else args.index_prefix

    print(f"Ensuring S3Vector index '{index_name}' in bucket '{args.bucket}'")

    try:
        ensure_s3vector_index(args.bucket, index_name, dimension)
    except Exception as e:
        logger.exception("Failed to ensure S3Vector index")
        print(f"Failed to ensure S3Vector index: {e}")
        return 1

    # Optional: demonstrate that S3VectorStorageManager can now use this index
    try:
        storage_mgr = S3VectorStorageManager()
        # This will resolve the identifier and fail fast if the index truly doesn't exist
        test_identifier = f"bucket/{args.bucket}/index/{index_name}"
        storage_mgr.describe_vector_index(test_identifier)
        print("Verified index via S3VectorStorageManager.describe_vector_index")
    except Exception as e:
        # Don't hard fail the script for describe-only issues; index creation is the primary goal
        logger.warning("Index creation succeeded but describe_vector_index failed: %s", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())

