#!/usr/bin/env python3
"""Embedding-client-level benchmarks for embedded LanceDB backends.

This script uses the minimal `LanceDBEmbeddedClient` to run end-to-end
index+search benchmarks against embedded LanceDB on different storage
backends (S3, EFS, EBS/local).

It reuses the cc-open-samples Marengo embeddings files to mimic a real
embedding client workload.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lancedb_embedded_client import LanceDBEmbeddedClient
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BACKENDS = [
    "lancedb-s3-embedded",
    "lancedb-efs-embedded",
    "lancedb-ebs-embedded",
]
DEFAULT_MODALITIES = ["text", "image", "audio"]


def load_embeddings(path: Path) -> List[Dict[str, Any]]:
    """Load embeddings from cc-open-samples JSON file."""
    with path.open() as f:
        data = json.load(f)

    if isinstance(data, dict) and "embeddings" in data:
        embeddings = data["embeddings"]
    elif isinstance(data, list):
        embeddings = data
    else:
        raise ValueError("Unexpected embeddings format (dict or list expected)")

    if not embeddings:
        raise ValueError("No embeddings found in file")
    first = embeddings[0]
    if "values" not in first or "id" not in first:
        raise ValueError("Invalid embedding format: missing 'values' or 'id'")

    return embeddings


def make_client(backend: str, args: argparse.Namespace) -> LanceDBEmbeddedClient:
    """Construct a LanceDBEmbeddedClient for the given backend."""
    if backend == "lancedb-s3-embedded":
        bucket = args.s3_bucket or os.getenv("LANCEDB_S3_BUCKET")
        prefix = args.s3_prefix or os.getenv("LANCEDB_S3_PREFIX", "")
        if not bucket:
            raise RuntimeError(
                "S3 backend selected but no bucket provided. "
                "Set --s3-bucket or LANCEDB_S3_BUCKET."
            )
        return LanceDBEmbeddedClient.for_s3(bucket=bucket, prefix=prefix, backend_name=backend)

    if backend == "lancedb-efs-embedded":
        path = args.efs_path or os.getenv("LANCEDB_EFS_URI", "/mnt/lancedb_efs")
        return LanceDBEmbeddedClient.for_efs(mount_path=path, backend_name=backend)

    if backend == "lancedb-ebs-embedded":
        path = args.ebs_path or os.getenv("LANCEDB_EBS_URI", "/mnt/lancedb")
        return LanceDBEmbeddedClient.for_ebs(mount_path=path, backend_name=backend)

    raise ValueError(f"Unsupported backend: {backend}")


def run_benchmark_for(
    backend: str,
    modality: str,
    args: argparse.Namespace,
    results_dir: Path,
) -> None:
    """Run index+search benchmark for a single backend/modality pair."""
    embeddings_path = Path(args.embeddings_root) / f"cc-open-samples-{modality}.json"
    logger.info(f"[{backend}/{modality}] Loading embeddings from {embeddings_path}")

    embeddings = load_embeddings(embeddings_path)
    vectors = [e["values"] for e in embeddings]
    table_name = f"videolake-client-{backend}-{modality}"

    metadata: List[Dict[str, Any]] = []
    for e in embeddings:
        meta = {
            "id": e["id"],
            "video_id": e.get("video_id"),
            "modality": e.get("modality", modality),
            "collection": table_name,
        }
        if "metadata" in e:
            meta.update(e["metadata"])
        metadata.append(meta)

    client = make_client(backend, args)
    if not client.health_check():
        raise RuntimeError(f"LanceDB backend {backend} at {client.uri} is not healthy")

    logger.info(f"[{backend}/{modality}] Indexing {len(vectors)} vectors into {table_name}")
    idx_start = time.time()
    index_result = client.index_vectors(table_name, vectors, metadata)
    idx_duration = time.time() - idx_start

    query_count = min(args.queries, len(vectors))
    if query_count == 0:
        raise RuntimeError("No vectors available for queries")

    latencies_ms: List[float] = []
    successful_queries = 0

    search_start = time.time()
    for i in range(query_count):
        query_vector = vectors[i]
        t0 = time.time()
        hits = client.search(table_name, query_vector, top_k=args.top_k)
        dt_ms = (time.time() - t0) * 1000.0
        latencies_ms.append(dt_ms)
        if hits:
            successful_queries += 1
    total_search_duration = time.time() - search_start

    arr = np.array(latencies_ms, dtype=np.float64)
    result = {
        "success": True,
        "backend": backend,
        "modality": modality,
        "table_name": table_name,
        "storage_uri": client.uri,
        "vectors_indexed": len(vectors),
        "index_duration_seconds": idx_duration,
        "query_count": query_count,
        "successful_queries": successful_queries,
        "duration_seconds": total_search_duration,
        "throughput_qps": query_count / total_search_duration if total_search_duration > 0 else 0.0,
        "latency_p50_ms": float(np.percentile(arr, 50)),
        "latency_p95_ms": float(np.percentile(arr, 95)),
        "latency_p99_ms": float(np.percentile(arr, 99)),
        "latency_min_ms": float(np.min(arr)),
        "latency_max_ms": float(np.max(arr)),
        "latency_mean_ms": float(np.mean(arr)),
        "latency_std_ms": float(np.std(arr)),
        "index_result": index_result,
    }

    out_path = results_dir / f"{backend}_{modality}_embedded_client.json"
    out_path.write_text(json.dumps(result, indent=2))
    logger.info(f"[{backend}/{modality}] Results written to {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embedding-client-level benchmarks using embedded LanceDB."
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        default=DEFAULT_BACKENDS,
        choices=DEFAULT_BACKENDS,
        help="Embedded LanceDB backends to benchmark.",
    )
    parser.add_argument(
        "--modalities",
        nargs="+",
        default=DEFAULT_MODALITIES,
        choices=DEFAULT_MODALITIES,
        help="Embedding modalities to benchmark.",
    )
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--dimension", type=int, default=1024)
    parser.add_argument(
        "--embeddings-root",
        default="embeddings/cc-open-samples-marengo",
        help="Root dir containing cc-open-samples-<modality>.json files.",
    )
    parser.add_argument("--s3-bucket", help="LanceDB S3 bucket (or env LANCEDB_S3_BUCKET)")
    parser.add_argument("--s3-prefix", help="Optional prefix inside the S3 bucket")
    parser.add_argument("--efs-path", help="EFS mount path (or env LANCEDB_EFS_URI)")
    parser.add_argument("--ebs-path", help="EBS mount path (or env LANCEDB_EBS_URI)")
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory for benchmark results; default "
            "benchmark-results/lancedb_embedded_client_<timestamp>"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    ts = time.strftime("%Y%m%d_%H%M%S")
    results_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path("benchmark-results") / f"lancedb_embedded_client_{ts}"
    )
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"Results directory: {results_dir}")

    for backend in args.backends:
        for modality in args.modalities:
            try:
                print(f"\n=== Benchmarking {backend} / {modality} ===")
                run_benchmark_for(backend, modality, args, results_dir)
            except Exception as e:  # pragma: no cover - defensive
                logger.error(f"Benchmark failed for {backend}/{modality}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

