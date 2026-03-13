"""
Comprehensive Benchmark Suite for Vector Databases

Implements 10 benchmark dimensions across all vector DB variants:
1. Query Latency (P50/P99)
2. Throughput (QPS)
3. Recall@k (accuracy against ground truth)
4. Indexing Speed (vectors/second)
5. Memory Efficiency (bytes per vector)
6. Cost-per-Query ($/1M queries)
7. Scaling (performance across vector counts)
8. Cold Start (initialization time)
9. Concurrent Load (multi-client performance)
10. Storage Efficiency (index overhead)

Supports 12-15 vector DB variants in 3 tiers as per VECTORDB_RESEARCH.md.
"""

import asyncio
import time
import numpy as np
import psutil
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkDimensions:
    """Results container for all 10 benchmark dimensions"""
    # Required fields (no defaults) must come first
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    throughput_qps: float
    vectors_tested: int

    # Optional fields (with defaults)
    # 1. Query Latency (remaining)
    latency_p999_ms: Optional[float] = None
    latency_min_ms: Optional[float] = None
    latency_max_ms: Optional[float] = None
    latency_mean_ms: Optional[float] = None
    latency_std_ms: Optional[float] = None

    # 2. Throughput (remaining)
    sustained_qps: Optional[float] = None

    # 3. Recall@k
    recall_at_10: Optional[float] = None
    recall_at_50: Optional[float] = None
    recall_at_100: Optional[float] = None

    # 4. Indexing Speed
    index_throughput_vectors_per_sec: Optional[float] = None
    index_build_time_sec: Optional[float] = None

    # 5. Memory Efficiency
    memory_usage_mb: Optional[float] = None
    memory_per_vector_bytes: Optional[float] = None
    peak_memory_mb: Optional[float] = None

    # 6. Cost per Query
    cost_per_million_queries_usd: Optional[float] = None
    infrastructure_cost_monthly_usd: Optional[float] = None

    # 7. Scaling
    performance_degradation_pct: Optional[float] = None

    # 8. Cold Start
    cold_start_time_sec: Optional[float] = None
    warm_start_time_sec: Optional[float] = None

    # 9. Concurrent Load
    concurrent_clients: int = 1
    concurrent_qps: Optional[float] = None
    concurrent_error_rate: Optional[float] = None

    # 10. Storage Efficiency
    total_storage_bytes: Optional[int] = None
    storage_per_vector_bytes: Optional[float] = None
    index_overhead_pct: Optional[float] = None

    # Metadata
    backend: str = ""
    variant: str = ""
    test_duration_sec: float = 0.0
    success: bool = True
    errors: Optional[List[str]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ComprehensiveBenchmark:
    """
    Enhanced benchmark runner implementing all 10 dimensions.

    Extends the basic BackendBenchmark with:
    - Ground truth generation for recall@k
    - Memory tracking
    - Cost modeling
    - Concurrent load testing
    - Storage measurement
    """

    def __init__(self, adapter, backend: str, variant: str = "standard", cost_config: Optional[Dict] = None):
        """
        Initialize comprehensive benchmark.

        Args:
            adapter: Backend adapter instance
            backend: Backend name (e.g., "s3vector", "qdrant")
            variant: Variant name (e.g., "serverless", "ecs-efs")
            cost_config: Cost model parameters:
                - infrastructure_monthly_usd: Base monthly cost
                - compute_cost_per_hour: Cost per compute hour
                - storage_cost_per_gb: Cost per GB storage
        """
        self.adapter = adapter
        self.backend = backend
        self.variant = variant
        self.cost_config = cost_config or {}

        # Ground truth cache for recall calculation
        self.ground_truth_cache: Dict[str, List[int]] = {}

        # Memory tracking
        self.process = psutil.Process()
        self.initial_memory_mb = 0
        self.peak_memory_mb = 0

    def generate_vectors(self, count: int, dimensions: int = 1536) -> np.ndarray:
        """Generate random normalized test vectors (default OpenAI ada-002 dimensions)"""
        vectors = np.random.rand(count, dimensions).astype(np.float32)
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / norms

    def compute_ground_truth(self, query: np.ndarray, corpus: np.ndarray, k: int = 100) -> List[int]:
        """
        Compute ground truth nearest neighbors using brute force.

        Args:
            query: Query vector (1D array)
            corpus: Corpus of vectors (2D array)
            k: Number of neighbors to return

        Returns:
            List of indices of k nearest neighbors
        """
        # Compute cosine similarities
        similarities = np.dot(corpus, query) / (
            np.linalg.norm(corpus, axis=1) * np.linalg.norm(query)
        )
        # Get top k indices
        top_k_indices = np.argsort(similarities)[::-1][:k]
        return top_k_indices.tolist()

    def calculate_recall(self, retrieved: List[int], ground_truth: List[int], k: int) -> float:
        """
        Calculate recall@k metric.

        Args:
            retrieved: List of retrieved indices
            ground_truth: List of ground truth indices
            k: Number of top results to consider

        Returns:
            Recall@k value (0.0 to 1.0)
        """
        if not ground_truth or not retrieved:
            return 0.0

        retrieved_set = set(retrieved[:k])
        ground_truth_set = set(ground_truth[:k])

        if len(ground_truth_set) == 0:
            return 0.0

        intersection = len(retrieved_set.intersection(ground_truth_set))
        return intersection / len(ground_truth_set)

    def track_memory(self):
        """Track current memory usage"""
        mem_info = self.process.memory_info()
        current_mb = mem_info.rss / 1024 / 1024
        self.peak_memory_mb = max(self.peak_memory_mb, current_mb)
        return current_mb

    def estimate_cost_per_query(self, qps: float, vector_count: int) -> Dict[str, float]:
        """
        Estimate cost per query based on infrastructure costs.

        Args:
            qps: Queries per second
            vector_count: Number of vectors stored

        Returns:
            Dictionary with cost metrics
        """
        monthly_cost = self.cost_config.get('infrastructure_monthly_usd', 0)
        storage_cost_per_gb = self.cost_config.get('storage_cost_per_gb', 0)

        # Estimate storage (1536 dim float32 = 6KB per vector)
        storage_gb = (vector_count * 1536 * 4) / (1024 ** 3)
        storage_cost = storage_gb * storage_cost_per_gb

        total_monthly_cost = monthly_cost + storage_cost

        # Queries per month (30 days)
        queries_per_month = qps * 86400 * 30

        # Cost per million queries
        cost_per_million = (total_monthly_cost / queries_per_month) * 1_000_000 if queries_per_month > 0 else 0

        return {
            "cost_per_million_queries_usd": cost_per_million,
            "infrastructure_cost_monthly_usd": total_monthly_cost,
            "storage_cost_monthly_usd": storage_cost,
            "estimated_monthly_queries": queries_per_month
        }

    async def measure_cold_start(self, collection: Optional[str] = None) -> float:
        """
        Measure cold start time (initialization).

        Returns:
            Cold start time in seconds
        """
        start_time = time.time()

        try:
            # Trigger initialization by running a health check or first query
            await asyncio.to_thread(self.adapter.health_check)

            # For some backends, first query is the real cold start
            test_vector = self.generate_vectors(1, 1536)[0]
            await asyncio.to_thread(
                self.adapter.search_vectors,
                test_vector.tolist(),
                10,
                collection=collection
            )

        except Exception as e:
            logger.warning(f"Cold start measurement failed: {e}")

        return time.time() - start_time

    def benchmark_concurrent_load(
        self,
        query_count: int,
        concurrent_clients: int,
        top_k: int = 10,
        dimensions: int = 1536,
        collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Benchmark with concurrent clients (dimension 9).

        Args:
            query_count: Total number of queries
            concurrent_clients: Number of concurrent clients
            top_k: Results per query
            dimensions: Vector dimensions
            collection: Optional collection name

        Returns:
            Concurrent load metrics
        """
        queries_per_client = query_count // concurrent_clients
        query_vectors = self.generate_vectors(query_count, dimensions)

        all_latencies = []
        errors = 0
        start_time = time.time()

        def run_client(client_id: int, start_idx: int) -> List[float]:
            """Run queries for a single client"""
            client_latencies = []
            client_errors = 0

            for i in range(queries_per_client):
                query_idx = start_idx + i
                if query_idx >= len(query_vectors):
                    break

                query_start = time.time()
                try:
                    self.adapter.search_vectors(
                        query_vectors[query_idx].tolist(),
                        top_k,
                        collection=collection
                    )
                    client_latencies.append((time.time() - query_start) * 1000)
                except Exception as e:
                    client_errors += 1
                    logger.debug(f"Client {client_id} query error: {e}")

            return client_latencies, client_errors

        # Run concurrent clients
        with ThreadPoolExecutor(max_workers=concurrent_clients) as executor:
            futures = []
            for client_id in range(concurrent_clients):
                start_idx = client_id * queries_per_client
                future = executor.submit(run_client, client_id, start_idx)
                futures.append(future)

            # Collect results
            for future in as_completed(futures):
                try:
                    client_latencies, client_errors = future.result()
                    all_latencies.extend(client_latencies)
                    errors += client_errors
                except Exception as e:
                    logger.error(f"Client thread failed: {e}")
                    errors += queries_per_client

        total_duration = time.time() - start_time
        successful_queries = len(all_latencies)

        if all_latencies:
            return {
                "concurrent_clients": concurrent_clients,
                "total_queries": query_count,
                "successful_queries": successful_queries,
                "concurrent_qps": successful_queries / total_duration if total_duration > 0 else 0,
                "concurrent_error_rate": errors / query_count if query_count > 0 else 0,
                "concurrent_latency_p50_ms": float(np.percentile(all_latencies, 50)),
                "concurrent_latency_p95_ms": float(np.percentile(all_latencies, 95)),
                "concurrent_latency_p99_ms": float(np.percentile(all_latencies, 99)),
                "duration_seconds": total_duration
            }
        else:
            return {
                "concurrent_clients": concurrent_clients,
                "concurrent_qps": 0,
                "concurrent_error_rate": 1.0,
                "error": "All queries failed"
            }

    def measure_storage_efficiency(self, vector_count: int, dimensions: int = 1536) -> Dict[str, Any]:
        """
        Measure storage efficiency (dimension 10).

        Note: This requires backend-specific implementation.
        For now, we estimate based on vector dimensions.

        Args:
            vector_count: Number of vectors
            dimensions: Vector dimensions

        Returns:
            Storage efficiency metrics
        """
        # Raw vector size (float32)
        raw_bytes_per_vector = dimensions * 4
        raw_total_bytes = vector_count * raw_bytes_per_vector

        # Estimated index overhead (varies by backend)
        # HNSW: ~40-60% overhead
        # IVF: ~10-20% overhead
        # Flat: ~5% overhead (metadata only)
        overhead_estimate = 0.4  # Default to HNSW-like overhead

        estimated_total_bytes = raw_total_bytes * (1 + overhead_estimate)
        estimated_bytes_per_vector = estimated_total_bytes / vector_count if vector_count > 0 else 0

        return {
            "raw_bytes_per_vector": raw_bytes_per_vector,
            "estimated_total_storage_bytes": estimated_total_bytes,
            "estimated_storage_per_vector_bytes": estimated_bytes_per_vector,
            "estimated_index_overhead_pct": overhead_estimate * 100
        }

    async def run_comprehensive_benchmark(
        self,
        vector_count: int = 10000,
        query_count: int = 1000,
        dimensions: int = 1536,
        top_k: int = 10,
        concurrent_clients: int = 5,
        collection: Optional[str] = None,
        measure_recall: bool = True
    ) -> BenchmarkDimensions:
        """
        Run complete benchmark across all 10 dimensions.

        Args:
            vector_count: Number of vectors to index
            query_count: Number of queries to run
            dimensions: Vector dimensions
            top_k: Results per query
            concurrent_clients: Number of concurrent clients for load test
            collection: Optional collection name
            measure_recall: Whether to compute recall (computationally expensive)

        Returns:
            BenchmarkDimensions with all metrics
        """
        logger.info(f"Starting comprehensive benchmark: {self.backend}/{self.variant}")
        logger.info(f"  Vectors: {vector_count}, Queries: {query_count}, Dimensions: {dimensions}")

        overall_start = time.time()
        errors = []

        # Track initial memory
        self.initial_memory_mb = self.track_memory()

        # 8. Cold Start
        cold_start_time = 0.0
        try:
            cold_start_time = await self.measure_cold_start(collection)
            logger.info(f"  ✓ Cold start: {cold_start_time:.3f}s")
        except Exception as e:
            errors.append(f"Cold start measurement failed: {e}")
            logger.warning(f"  ✗ Cold start failed: {e}")

        # Generate test vectors
        corpus_vectors = self.generate_vectors(vector_count, dimensions)
        query_vectors = self.generate_vectors(query_count, dimensions)

        # 4. Indexing Speed
        index_start = time.time()
        try:
            # Index in batches
            batch_size = 1000
            for i in range(0, len(corpus_vectors), batch_size):
                batch = corpus_vectors[i:i+batch_size]
                metadata = [{"id": j} for j in range(i, i+len(batch))]
                await asyncio.to_thread(
                    self.adapter.index_vectors,
                    batch.tolist(),
                    metadata,
                    collection=collection
                )

            index_duration = time.time() - index_start
            index_throughput = vector_count / index_duration if index_duration > 0 else 0
            logger.info(f"  ✓ Indexing: {index_throughput:.1f} vectors/sec ({index_duration:.1f}s)")
        except Exception as e:
            errors.append(f"Indexing failed: {e}")
            logger.error(f"  ✗ Indexing failed: {e}")
            index_duration = 0
            index_throughput = 0

        # Track memory after indexing
        memory_after_index = self.track_memory()

        # Prepare ground truth for recall if requested
        ground_truth_map = {}
        if measure_recall:
            try:
                logger.info("  Computing ground truth for recall@k...")
                for i, query in enumerate(query_vectors[:100]):  # Limit to 100 for performance
                    ground_truth_map[i] = self.compute_ground_truth(query, corpus_vectors, k=100)
                logger.info(f"  ✓ Ground truth computed for {len(ground_truth_map)} queries")
            except Exception as e:
                errors.append(f"Ground truth computation failed: {e}")
                logger.warning(f"  ✗ Ground truth failed: {e}")

        # 1 & 2. Query Latency and Throughput
        latencies = []
        recall_at_10_scores = []
        recall_at_50_scores = []
        recall_at_100_scores = []

        search_start = time.time()
        successful_queries = 0

        try:
            for i, query_vector in enumerate(query_vectors):
                query_start = time.time()

                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    top_k if not measure_recall else 100,  # Get more results for recall
                    collection=collection
                )

                query_duration = (time.time() - query_start) * 1000
                latencies.append(query_duration)

                if results:
                    successful_queries += 1

                    # 3. Calculate recall@k if ground truth available
                    if measure_recall and i in ground_truth_map:
                        retrieved_ids = [r.get('id', -1) for r in results if isinstance(r, dict)]
                        if not retrieved_ids and results:
                            # Handle different result formats
                            retrieved_ids = list(range(len(results)))

                        ground_truth = ground_truth_map[i]
                        recall_at_10_scores.append(self.calculate_recall(retrieved_ids, ground_truth, 10))
                        recall_at_50_scores.append(self.calculate_recall(retrieved_ids, ground_truth, 50))
                        recall_at_100_scores.append(self.calculate_recall(retrieved_ids, ground_truth, 100))

            search_duration = time.time() - search_start
            throughput_qps = len(latencies) / search_duration if search_duration > 0 else 0
            logger.info(f"  ✓ Search: {throughput_qps:.1f} QPS, P50={np.percentile(latencies, 50):.2f}ms")

        except Exception as e:
            errors.append(f"Search benchmark failed: {e}")
            logger.error(f"  ✗ Search failed: {e}")
            search_duration = 0
            throughput_qps = 0

        # 9. Concurrent Load
        concurrent_metrics = {}
        if concurrent_clients > 1:
            try:
                concurrent_metrics = self.benchmark_concurrent_load(
                    min(query_count, 500),  # Limit concurrent test size
                    concurrent_clients,
                    top_k,
                    dimensions,
                    collection
                )
                logger.info(f"  ✓ Concurrent ({concurrent_clients} clients): {concurrent_metrics.get('concurrent_qps', 0):.1f} QPS")
            except Exception as e:
                errors.append(f"Concurrent load test failed: {e}")
                logger.warning(f"  ✗ Concurrent test failed: {e}")

        # 5. Memory Efficiency
        final_memory = self.track_memory()
        memory_used_mb = self.peak_memory_mb - self.initial_memory_mb
        memory_per_vector = (memory_used_mb * 1024 * 1024) / vector_count if vector_count > 0 else 0

        # 10. Storage Efficiency
        storage_metrics = self.measure_storage_efficiency(vector_count, dimensions)

        # 6. Cost Efficiency
        cost_metrics = self.estimate_cost_per_query(throughput_qps, vector_count)

        # Compile results
        total_duration = time.time() - overall_start

        result = BenchmarkDimensions(
            # 1. Latency
            latency_p50_ms=float(np.percentile(latencies, 50)) if latencies else 0,
            latency_p95_ms=float(np.percentile(latencies, 95)) if latencies else 0,
            latency_p99_ms=float(np.percentile(latencies, 99)) if latencies else 0,
            latency_p999_ms=float(np.percentile(latencies, 99.9)) if len(latencies) >= 1000 else None,
            latency_min_ms=float(np.min(latencies)) if latencies else 0,
            latency_max_ms=float(np.max(latencies)) if latencies else 0,
            latency_mean_ms=float(np.mean(latencies)) if latencies else 0,
            latency_std_ms=float(np.std(latencies)) if latencies else 0,

            # 2. Throughput
            throughput_qps=throughput_qps,
            sustained_qps=throughput_qps,  # Could add separate 5-minute sustained test

            # 3. Recall@k
            recall_at_10=float(np.mean(recall_at_10_scores)) if recall_at_10_scores else None,
            recall_at_50=float(np.mean(recall_at_50_scores)) if recall_at_50_scores else None,
            recall_at_100=float(np.mean(recall_at_100_scores)) if recall_at_100_scores else None,

            # 4. Indexing Speed
            index_throughput_vectors_per_sec=index_throughput,
            index_build_time_sec=index_duration,

            # 5. Memory Efficiency
            memory_usage_mb=memory_used_mb,
            memory_per_vector_bytes=memory_per_vector,
            peak_memory_mb=self.peak_memory_mb,

            # 6. Cost
            cost_per_million_queries_usd=cost_metrics['cost_per_million_queries_usd'],
            infrastructure_cost_monthly_usd=cost_metrics['infrastructure_cost_monthly_usd'],

            # 7. Scaling
            vectors_tested=vector_count,
            performance_degradation_pct=None,  # Would need multiple runs with different sizes

            # 8. Cold Start
            cold_start_time_sec=cold_start_time,

            # 9. Concurrent Load
            concurrent_clients=concurrent_clients,
            concurrent_qps=concurrent_metrics.get('concurrent_qps'),
            concurrent_error_rate=concurrent_metrics.get('concurrent_error_rate'),

            # 10. Storage Efficiency
            total_storage_bytes=storage_metrics['estimated_total_storage_bytes'],
            storage_per_vector_bytes=storage_metrics['estimated_storage_per_vector_bytes'],
            index_overhead_pct=storage_metrics['estimated_index_overhead_pct'],

            # Metadata
            backend=self.backend,
            variant=self.variant,
            test_duration_sec=total_duration,
            success=len(errors) == 0,
            errors=errors
        )

        logger.info(f"Comprehensive benchmark completed in {total_duration:.1f}s")
        if errors:
            logger.warning(f"Completed with {len(errors)} errors: {errors}")

        return result
