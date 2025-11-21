#!/usr/bin/env python3
"""
Individual Backend Benchmark Runner

Executes specific benchmark operations on a single backend.
Used by deploy_and_benchmark.py orchestrator.

Supports both SDK-based (S3Vector) and REST API-based (Qdrant, LanceDB) backends
through the unified backend adapter interface.

Usage:
    python scripts/benchmark_backend.py --backend s3vector --operation index --vectors 1000
    python scripts/benchmark_backend.py --backend lancedb --operation search --queries 100
    python scripts/benchmark_backend.py --backend qdrant --operation mixed --duration 60
"""

import argparse
import json
import time
import sys
from typing import Dict, List, Any, Optional
import numpy as np
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import backend adapters
from scripts.backend_adapters import (
    get_backend_adapter,
    validate_backend_connectivity,
    BACKEND_TYPES,
    DEFAULT_ENDPOINTS
)


class BackendBenchmark:
    """Benchmark runner for a single backend using unified adapter interface"""

    def __init__(self, backend: str, endpoint: Optional[str] = None, config: Optional[Dict] = None, collection: Optional[str] = None):
        self.backend = backend
        self.config = config or {}
        self.collection = collection

        # Add endpoint to config if provided
        if endpoint:
            self.config['endpoint'] = endpoint

        # Get appropriate backend adapter
        try:
            self.adapter = get_backend_adapter(backend, self.config)
            endpoint_info = self.adapter.get_endpoint_info()
            print(f"Initialized {backend} backend adapter:")
            print(f"  Type: {endpoint_info.get('type', 'unknown')}")
            print(f"  Endpoint: {endpoint_info.get('endpoint', 'N/A')}")
            if self.collection:
                print(f"  Collection: {self.collection}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize backend adapter for {backend}: {e}")

        self.results: Dict[str, Any] = {}

    def generate_vectors(self, count: int, dimensions: int = 1024) -> np.ndarray:
        """Generate random test vectors"""
        return np.random.rand(count, dimensions).astype(np.float32)

    def benchmark_index(self, vector_count: int, dimensions: int = 1024) -> Dict[str, Any]:
        """Benchmark vector indexing operation using backend adapter"""
        print(f"Benchmarking index operation: {vector_count} vectors ({dimensions}D)")

        vectors = self.generate_vectors(vector_count, dimensions)
        metadata = [{"id": i} for i in range(vector_count)]

        start_time = time.time()
        try:
            # Use adapter to index vectors
            result = self.adapter.index_vectors(vectors.tolist(), metadata, collection=self.collection)
            duration = time.time() - start_time

            # Merge timing with result
            result["duration_seconds"] = duration
            result["vectors_count"] = vector_count

            if result.get("success", False):
                result["vectors_per_second"] = vector_count / duration if duration > 0 else 0

            return result

        except Exception as e:
            return {
                "success": False,
                "duration_seconds": time.time() - start_time,
                "vectors_count": vector_count,
                "error": str(e),
                "backend": self.backend
            }

    def benchmark_search(self, query_count: int, top_k: int = 10, dimensions: int = 1024) -> Dict[str, Any]:
        """Benchmark vector search operation using backend adapter"""
        print(f"Benchmarking search operation: {query_count} queries, top_k={top_k} ({dimensions}D)")
        if self.collection:
            print(f"  Using collection: {self.collection}")

        query_vectors = self.generate_vectors(query_count, dimensions)
        latencies = []
        successful_queries = 0

        start_time = time.time()
        try:
            for i, query_vector in enumerate(query_vectors):
                query_start = time.time()

                # Use adapter to search
                results = self.adapter.search_vectors(query_vector.tolist(), top_k, collection=self.collection)

                query_duration = time.time() - query_start
                latencies.append(query_duration * 1000)  # Convert to ms

                if results:
                    successful_queries += 1
                else:
                    print(f"Query {i+1}/{query_count} returned no results")

            total_duration = time.time() - start_time

            if latencies:
                return {
                    "success": True,
                    "duration_seconds": total_duration,
                    "query_count": len(latencies),
                    "successful_queries": successful_queries,
                    "throughput_qps": len(latencies) / total_duration if total_duration > 0 else 0,
                    "latency_p50_ms": float(np.percentile(latencies, 50)),
                    "latency_p95_ms": float(np.percentile(latencies, 95)),
                    "latency_p99_ms": float(np.percentile(latencies, 99)),
                    "latency_min_ms": float(np.min(latencies)),
                    "latency_max_ms": float(np.max(latencies)),
                    "latency_mean_ms": float(np.mean(latencies)),
                    "latency_std_ms": float(np.std(latencies)),
                    "backend": self.backend
                }
            else:
                return {
                    "success": False,
                    "duration_seconds": total_duration,
                    "query_count": 0,
                    "error": "No successful queries",
                    "backend": self.backend
                }
        except Exception as e:
            return {
                "success": False,
                "duration_seconds": time.time() - start_time,
                "query_count": len(latencies),
                "error": str(e),
                "backend": self.backend
            }

    def benchmark_mixed_workload(self, duration_seconds: int = 60, dimensions: int = 1024) -> Dict[str, Any]:
        """Run mixed read/write workload for specified duration using backend adapter"""
        print(f"Benchmarking mixed workload: {duration_seconds}s ({dimensions}D)")
        if self.collection:
            print(f"  Using collection: {self.collection}")

        start_time = time.time()
        operations = {"index": 0, "search": 0, "errors": 0}

        try:
            while time.time() - start_time < duration_seconds:
                # 80% reads, 20% writes
                if np.random.rand() < 0.8:
                    # Search operation
                    query_vector = self.generate_vectors(1, dimensions)[0]
                    try:
                        results = self.adapter.search_vectors(query_vector.tolist(), 10, collection=self.collection)
                        if results:
                            operations["search"] += 1
                        else:
                            operations["errors"] += 1
                    except:
                        operations["errors"] += 1
                else:
                    # Index operation
                    vectors = self.generate_vectors(10, dimensions)
                    metadata = [{"id": i} for i in range(10)]
                    try:
                        result = self.adapter.index_vectors(vectors.tolist(), metadata, collection=self.collection)
                        if result.get("success", False):
                            operations["index"] += 1
                        else:
                            operations["errors"] += 1
                    except:
                        operations["errors"] += 1

            actual_duration = time.time() - start_time
            total_ops = operations["index"] + operations["search"]

            return {
                "success": True,
                "duration_seconds": actual_duration,
                "total_operations": total_ops,
                "index_operations": operations["index"],
                "search_operations": operations["search"],
                "errors": operations["errors"],
                "ops_per_second": total_ops / actual_duration if actual_duration > 0 else 0,
                "backend": self.backend
            }
        except Exception as e:
            return {
                "success": False,
                "duration_seconds": time.time() - start_time,
                "error": str(e),
                "backend": self.backend
            }

    def validate_backend(self) -> Dict[str, Any]:
        """Validate backend connectivity before benchmarking"""
        print(f"Validating {self.backend} connectivity...")
        try:
            is_healthy = self.adapter.health_check()
            endpoint_info = self.adapter.get_endpoint_info()

            return {
                "accessible": is_healthy,
                "endpoint_info": endpoint_info,
                "backend": self.backend
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e),
                "backend": self.backend
            }


def main():
    """Main benchmark entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark individual backend operations"
    )

    parser.add_argument(
        "--backend",
        required=True,
        help="Backend to benchmark (e.g., s3vector, lancedb-s3)"
    )
    parser.add_argument(
        "--operation",
        required=True,
        choices=["index", "search", "mixed"],
        help="Operation to benchmark"
    )
    parser.add_argument(
        "--vectors",
        type=int,
        default=1000,
        help="Number of vectors to index (for index operation)"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=100,
        help="Number of queries to run (for search operation)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (for mixed workload)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of results to retrieve per query"
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=1024,
        help="Vector dimension (default: 1024)"
    )
    parser.add_argument(
        "--collection",
        help="Collection name for backends that support collections (e.g., Qdrant)"
    )
    parser.add_argument(
        "--s3vector-bucket",
        help="S3Vector bucket name override (default: videolake-vectors)"
    )
    parser.add_argument(
        "--s3vector-index",
        help="S3Vector index name override (default: embeddings)"
    )

    parser.add_argument(
        "--endpoint",
        help="Backend endpoint URL (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--job_id",
        help="Job ID for tracking results"
    )

    args = parser.parse_args()

    # Validate backend first
    print(f"\n{'='*60}")
    print(f"Backend Benchmark: {args.backend}")
    print(f"{'='*60}\n")

    # Build config
    config = {}
    if args.endpoint:
        config['endpoint'] = args.endpoint
    if args.s3vector_bucket:
        config['bucket'] = args.s3vector_bucket
    if args.s3vector_index:
        config['index'] = args.s3vector_index

    # Create benchmark runner
    try:
        benchmark = BackendBenchmark(args.backend, args.endpoint, config, args.collection)
    except Exception as e:
        print(f"\n✗ Failed to initialize backend: {e}")
        return 1

    # Validate connectivity
    validation = benchmark.validate_backend()
    if not validation.get("accessible", False):
        print(f"\n✗ Backend {args.backend} is not accessible!")
        print(f"  Error: {validation.get('error', 'Unknown error')}")
        print(f"  Check that the backend is running and accessible")
        return 1

    print(f"✓ Backend {args.backend} is accessible\n")

    # Run requested operation
    if args.operation == "index":
        results = benchmark.benchmark_index(args.vectors, args.dimension)
    elif args.operation == "search":
        results = benchmark.benchmark_search(args.queries, args.top_k, args.dimension)
    elif args.operation == "mixed":
        results = benchmark.benchmark_mixed_workload(args.duration, args.dimension)
    else:
        print(f"Unknown operation: {args.operation}")
        return 1

    # Add metadata
    results["backend"] = args.backend
    results["operation"] = args.operation
    results["endpoint_info"] = benchmark.adapter.get_endpoint_info()

    # Print results
    print("\nBenchmark Results:")
    print(json.dumps(results, indent=2))

    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")
    
    # If job_id is provided, we might want to upload results to S3 or similar
    # For now, we rely on logs or the output file being in a shared location
    if args.job_id:
        print(f"Job ID: {args.job_id}")
        # TODO: Upload results to S3 if needed, using S3_BUCKET and S3_RESULTS_PREFIX env vars

    # Return exit code based on success
    return 0 if results.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())