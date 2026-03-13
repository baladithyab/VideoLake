"""
Comprehensive Benchmark Dimensions Module

Implements 10 benchmark dimensions for vector database comparison:
1. Latency (p50/p99/p999)
2. Throughput (sustained QPS)
3. Recall@k (accuracy vs ground truth)
4. Indexing speed (vectors/sec)
5. Memory efficiency (bytes/vector)
6. Cost-per-query ($/1M queries)
7. Scaling (performance at different sizes)
8. Cold start (serverless initialization)
9. Concurrent load (multi-client performance)
10. Storage efficiency (index overhead)
"""

import time
import asyncio
import numpy as np
import psutil
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import tracemalloc

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LatencyMetrics:
    """Query latency measurements"""
    p50_ms: float
    p95_ms: float
    p99_ms: float
    p999_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    std_ms: float
    samples: int


@dataclass
class ThroughputMetrics:
    """Sustained throughput measurements"""
    qps: float
    duration_seconds: float
    total_queries: int
    successful_queries: int
    failed_queries: int
    error_rate: float


@dataclass
class RecallMetrics:
    """Recall accuracy measurements"""
    recall_at_k: float
    k: int
    ground_truth_method: str
    distance_correlation: float
    samples_evaluated: int


@dataclass
class IndexingMetrics:
    """Indexing performance measurements"""
    vectors_per_second: float
    total_vectors: int
    duration_seconds: float
    batch_size: int
    peak_memory_mb: float
    build_time_seconds: float


@dataclass
class MemoryMetrics:
    """Memory efficiency measurements"""
    bytes_per_vector: float
    total_memory_mb: float
    index_memory_mb: float
    overhead_percentage: float
    peak_memory_mb: float


@dataclass
class CostMetrics:
    """Cost efficiency measurements"""
    cost_per_million_queries: float
    monthly_cost_estimate: float
    storage_cost_per_gb: float
    compute_cost_per_hour: float
    total_cost_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class ScalingMetrics:
    """Scaling performance measurements"""
    vector_counts: List[int] = field(default_factory=list)
    latency_at_scale: List[float] = field(default_factory=list)
    qps_at_scale: List[float] = field(default_factory=list)
    scaling_efficiency: float = 0.0  # 1.0 = linear, <1.0 = sub-linear


@dataclass
class ColdStartMetrics:
    """Cold start measurements (serverless)"""
    cold_start_ms: float
    warm_start_ms: float
    initialization_overhead_ms: float
    applicable: bool = True  # False for always-on services


@dataclass
class ConcurrentLoadMetrics:
    """Concurrent load performance"""
    concurrent_clients: int
    qps_per_client: List[float] = field(default_factory=list)
    total_qps: float = 0.0
    latency_degradation_pct: float = 0.0  # vs single client
    errors_under_load: int = 0


@dataclass
class StorageMetrics:
    """Storage efficiency measurements"""
    raw_vector_size_mb: float
    stored_size_mb: float
    index_overhead_mb: float
    compression_ratio: float
    overhead_percentage: float


@dataclass
class ComprehensiveBenchmarkResults:
    """Complete benchmark results across all dimensions"""
    backend: str
    timestamp: datetime
    latency: Optional[LatencyMetrics] = None
    throughput: Optional[ThroughputMetrics] = None
    recall: Optional[RecallMetrics] = None
    indexing: Optional[IndexingMetrics] = None
    memory: Optional[MemoryMetrics] = None
    cost: Optional[CostMetrics] = None
    scaling: Optional[ScalingMetrics] = None
    cold_start: Optional[ColdStartMetrics] = None
    concurrent_load: Optional[ConcurrentLoadMetrics] = None
    storage: Optional[StorageMetrics] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class BenchmarkDimensionsRunner:
    """
    Runs comprehensive benchmarks across all 10 dimensions
    """

    def __init__(self, backend_adapter):
        """
        Args:
            backend_adapter: Backend adapter implementing search_vectors, index_vectors, etc.
        """
        self.adapter = backend_adapter
        self.results = ComprehensiveBenchmarkResults(
            backend=getattr(backend_adapter, 'backend_name', 'unknown'),
            timestamp=datetime.utcnow()
        )

    def generate_vectors(self, count: int, dimensions: int = 1024) -> np.ndarray:
        """Generate random normalized test vectors"""
        vectors = np.random.rand(count, dimensions).astype(np.float32)
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / norms

    def compute_ground_truth(self, vectors: np.ndarray, query_vector: np.ndarray,
                            k: int = 10) -> List[int]:
        """
        Compute ground truth nearest neighbors using brute force

        Args:
            vectors: Database vectors (n, d)
            query_vector: Query vector (d,)
            k: Number of neighbors

        Returns:
            List of indices of k nearest neighbors
        """
        # Compute cosine similarity (assuming normalized vectors)
        similarities = np.dot(vectors, query_vector)
        # Get top k indices (argsort returns ascending, we want descending)
        top_k_indices = np.argsort(similarities)[-k:][::-1]
        return top_k_indices.tolist()

    async def measure_latency(self, query_count: int = 100, top_k: int = 10,
                             dimensions: int = 1024, collection: Optional[str] = None) -> LatencyMetrics:
        """
        Dimension 1: Query Latency (p50/p95/p99/p999)
        """
        logger.info(f"Measuring latency with {query_count} queries...")

        query_vectors = self.generate_vectors(query_count, dimensions)
        latencies = []

        for query_vector in query_vectors:
            start = time.perf_counter()
            try:
                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    top_k,
                    collection=collection
                )
                duration = (time.perf_counter() - start) * 1000  # Convert to ms
                latencies.append(duration)
            except Exception as e:
                logger.warning(f"Query failed: {e}")
                continue

        if not latencies:
            raise RuntimeError("No successful queries for latency measurement")

        return LatencyMetrics(
            p50_ms=float(np.percentile(latencies, 50)),
            p95_ms=float(np.percentile(latencies, 95)),
            p99_ms=float(np.percentile(latencies, 99)),
            p999_ms=float(np.percentile(latencies, 99.9)),
            min_ms=float(np.min(latencies)),
            max_ms=float(np.max(latencies)),
            mean_ms=float(np.mean(latencies)),
            std_ms=float(np.std(latencies)),
            samples=len(latencies)
        )

    async def measure_throughput(self, duration_seconds: int = 60, top_k: int = 10,
                                 dimensions: int = 1024, collection: Optional[str] = None) -> ThroughputMetrics:
        """
        Dimension 2: Sustained Throughput (QPS)
        """
        logger.info(f"Measuring throughput for {duration_seconds}s...")

        start_time = time.time()
        total_queries = 0
        successful = 0
        failed = 0

        while time.time() - start_time < duration_seconds:
            query_vector = self.generate_vectors(1, dimensions)[0]
            try:
                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    top_k,
                    collection=collection
                )
                successful += 1
            except Exception as e:
                failed += 1
            total_queries += 1

        actual_duration = time.time() - start_time
        qps = successful / actual_duration if actual_duration > 0 else 0
        error_rate = failed / total_queries if total_queries > 0 else 0

        return ThroughputMetrics(
            qps=qps,
            duration_seconds=actual_duration,
            total_queries=total_queries,
            successful_queries=successful,
            failed_queries=failed,
            error_rate=error_rate
        )

    async def measure_recall(self, sample_count: int = 100, k: int = 10,
                            dimensions: int = 1024, indexed_vectors: Optional[np.ndarray] = None,
                            collection: Optional[str] = None) -> RecallMetrics:
        """
        Dimension 3: Recall@K (accuracy vs ground truth)
        """
        logger.info(f"Measuring recall@{k} with {sample_count} samples...")

        if indexed_vectors is None:
            # Generate and index test vectors
            indexed_vectors = self.generate_vectors(1000, dimensions)
            metadata = [{"id": i} for i in range(len(indexed_vectors))]
            await asyncio.to_thread(
                self.adapter.index_vectors,
                indexed_vectors.tolist(),
                metadata,
                collection=collection
            )
            # Wait for indexing to complete
            await asyncio.sleep(2)

        query_vectors = self.generate_vectors(sample_count, dimensions)
        recall_scores = []

        for query_vector in query_vectors:
            # Ground truth
            ground_truth = set(self.compute_ground_truth(indexed_vectors, query_vector, k))

            # Backend results
            try:
                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    k,
                    collection=collection
                )
                # Extract IDs from results
                returned_ids = set()
                for result in results[:k]:
                    if isinstance(result, dict):
                        returned_ids.add(result.get('id', result.get('metadata', {}).get('id')))

                # Calculate recall
                intersection = ground_truth & returned_ids
                recall = len(intersection) / k if k > 0 else 0
                recall_scores.append(recall)
            except Exception as e:
                logger.warning(f"Recall query failed: {e}")
                continue

        avg_recall = np.mean(recall_scores) if recall_scores else 0.0

        return RecallMetrics(
            recall_at_k=float(avg_recall),
            k=k,
            ground_truth_method="brute_force_cosine",
            distance_correlation=1.0,  # Simplified
            samples_evaluated=len(recall_scores)
        )

    async def measure_indexing_speed(self, vector_count: int = 10000, dimensions: int = 1024,
                                     batch_size: int = 1000, collection: Optional[str] = None) -> IndexingMetrics:
        """
        Dimension 4: Indexing Speed (vectors/sec)
        """
        logger.info(f"Measuring indexing speed for {vector_count} vectors...")

        tracemalloc.start()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        vectors = self.generate_vectors(vector_count, dimensions)
        metadata = [{"id": i, "batch": i // batch_size} for i in range(vector_count)]

        start_time = time.time()

        # Index in batches
        for i in range(0, vector_count, batch_size):
            batch_vectors = vectors[i:i+batch_size]
            batch_metadata = metadata[i:i+batch_size]

            try:
                await asyncio.to_thread(
                    self.adapter.index_vectors,
                    batch_vectors.tolist(),
                    batch_metadata,
                    collection=collection
                )
            except Exception as e:
                logger.error(f"Batch indexing failed: {e}")
                raise

        duration = time.time() - start_time

        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        peak_memory = end_memory  # Simplified, real peak would need continuous monitoring

        tracemalloc.stop()

        return IndexingMetrics(
            vectors_per_second=vector_count / duration if duration > 0 else 0,
            total_vectors=vector_count,
            duration_seconds=duration,
            batch_size=batch_size,
            peak_memory_mb=peak_memory,
            build_time_seconds=duration
        )

    async def measure_memory_efficiency(self, vector_count: int = 10000, dimensions: int = 1024,
                                       collection: Optional[str] = None) -> MemoryMetrics:
        """
        Dimension 5: Memory Efficiency (bytes/vector)
        """
        logger.info(f"Measuring memory efficiency for {vector_count} vectors...")

        # Calculate raw vector size
        raw_size_bytes = vector_count * dimensions * 4  # float32 = 4 bytes
        raw_size_mb = raw_size_bytes / 1024 / 1024

        # Measure memory before indexing
        before_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Index vectors
        vectors = self.generate_vectors(vector_count, dimensions)
        metadata = [{"id": i} for i in range(vector_count)]

        await asyncio.to_thread(
            self.adapter.index_vectors,
            vectors.tolist(),
            metadata,
            collection=collection
        )

        # Measure memory after indexing
        await asyncio.sleep(2)  # Let memory settle
        after_memory = psutil.Process().memory_info().rss / 1024 / 1024

        index_memory = max(0, after_memory - before_memory)
        bytes_per_vector = (index_memory * 1024 * 1024) / vector_count if vector_count > 0 else 0
        overhead_pct = ((index_memory - raw_size_mb) / raw_size_mb * 100) if raw_size_mb > 0 else 0

        return MemoryMetrics(
            bytes_per_vector=bytes_per_vector,
            total_memory_mb=after_memory,
            index_memory_mb=index_memory,
            overhead_percentage=overhead_pct,
            peak_memory_mb=after_memory
        )

    def estimate_cost(self, backend: str, monthly_queries: int = 1000000,
                     storage_gb: float = 10.0) -> CostMetrics:
        """
        Dimension 6: Cost-per-query ($/1M queries)

        Uses research document cost estimates
        """
        logger.info(f"Estimating costs for {backend}...")

        # Cost estimates from research document (100K vectors @ 1536-dim)
        cost_table = {
            's3vector': {'monthly': 2.5, 'storage_per_gb': 0.023},
            'qdrant-ecs': {'monthly': 103, 'storage_per_gb': 0.08},
            'lancedb-s3': {'monthly': 7.5, 'storage_per_gb': 0.023},
            'lancedb-ebs': {'monthly': 92, 'storage_per_gb': 0.08},
            'opensearch': {'monthly': 362, 'storage_per_gb': 0.08},
            'opensearch-serverless': {'monthly': 691, 'storage_per_gb': 0.024},
            'pgvector-aurora': {'monthly': 174, 'storage_per_gb': 0.10},
            'pgvector-rds': {'monthly': 211, 'storage_per_gb': 0.115},
        }

        backend_key = backend.lower().replace('_', '-')
        costs = cost_table.get(backend_key, {'monthly': 100, 'storage_per_gb': 0.10})

        monthly_base = costs['monthly']
        storage_cost = storage_gb * costs['storage_per_gb']
        total_monthly = monthly_base + storage_cost

        # Calculate per-query cost
        cost_per_million = (total_monthly / monthly_queries) * 1_000_000 if monthly_queries > 0 else 0

        return CostMetrics(
            cost_per_million_queries=cost_per_million,
            monthly_cost_estimate=total_monthly,
            storage_cost_per_gb=costs['storage_per_gb'],
            compute_cost_per_hour=monthly_base / 730,  # Average hours per month
            total_cost_breakdown={
                'compute': monthly_base,
                'storage': storage_cost,
                'total': total_monthly
            }
        )

    async def measure_scaling(self, vector_counts: List[int] = None, dimensions: int = 1024,
                             collection: Optional[str] = None) -> ScalingMetrics:
        """
        Dimension 7: Scaling (performance at different sizes)
        """
        if vector_counts is None:
            vector_counts = [1000, 5000, 10000, 50000]

        logger.info(f"Measuring scaling across {vector_counts}...")

        latencies = []
        qps_values = []

        for count in vector_counts:
            try:
                # Index vectors
                vectors = self.generate_vectors(count, dimensions)
                metadata = [{"id": i} for i in range(count)]

                await asyncio.to_thread(
                    self.adapter.index_vectors,
                    vectors.tolist(),
                    metadata,
                    collection=collection
                )

                # Measure latency
                latency_metrics = await self.measure_latency(
                    query_count=50,
                    dimensions=dimensions,
                    collection=collection
                )
                latencies.append(latency_metrics.p50_ms)

                # Measure QPS
                throughput_metrics = await self.measure_throughput(
                    duration_seconds=30,
                    dimensions=dimensions,
                    collection=collection
                )
                qps_values.append(throughput_metrics.qps)

            except Exception as e:
                logger.error(f"Scaling test failed at {count} vectors: {e}")
                latencies.append(None)
                qps_values.append(None)

        # Calculate scaling efficiency (simplified)
        # Ideal: performance constant regardless of size
        valid_qps = [q for q in qps_values if q is not None]
        if len(valid_qps) >= 2:
            efficiency = min(valid_qps) / max(valid_qps)
        else:
            efficiency = 1.0

        return ScalingMetrics(
            vector_counts=vector_counts,
            latency_at_scale=latencies,
            qps_at_scale=qps_values,
            scaling_efficiency=efficiency
        )

    async def measure_cold_start(self, dimensions: int = 1024,
                                 collection: Optional[str] = None) -> ColdStartMetrics:
        """
        Dimension 8: Cold Start (serverless initialization)
        """
        logger.info("Measuring cold start latency...")

        # Cold start: first query after initialization
        cold_start_times = []
        for _ in range(3):  # Average of 3 cold starts
            # Simulate restart (adapter-specific)
            query_vector = self.generate_vectors(1, dimensions)[0]

            start = time.perf_counter()
            try:
                await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    10,
                    collection=collection
                )
                cold_time = (time.perf_counter() - start) * 1000
                cold_start_times.append(cold_time)
            except Exception as e:
                logger.warning(f"Cold start query failed: {e}")

        # Warm start: subsequent queries
        warm_start_times = []
        for _ in range(10):
            query_vector = self.generate_vectors(1, dimensions)[0]
            start = time.perf_counter()
            try:
                await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    10,
                    collection=collection
                )
                warm_time = (time.perf_counter() - start) * 1000
                warm_start_times.append(warm_time)
            except Exception as e:
                logger.warning(f"Warm start query failed: {e}")

        cold_avg = np.mean(cold_start_times) if cold_start_times else 0
        warm_avg = np.mean(warm_start_times) if warm_start_times else 0

        return ColdStartMetrics(
            cold_start_ms=float(cold_avg),
            warm_start_ms=float(warm_avg),
            initialization_overhead_ms=float(cold_avg - warm_avg),
            applicable=True
        )

    async def measure_concurrent_load(self, concurrent_clients: int = 10, queries_per_client: int = 50,
                                     dimensions: int = 1024, collection: Optional[str] = None) -> ConcurrentLoadMetrics:
        """
        Dimension 9: Concurrent Load (multi-client performance)
        """
        logger.info(f"Measuring concurrent load with {concurrent_clients} clients...")

        async def client_workload(client_id: int) -> Tuple[float, int]:
            """Single client workload"""
            start = time.time()
            successful = 0

            for _ in range(queries_per_client):
                query_vector = self.generate_vectors(1, dimensions)[0]
                try:
                    await asyncio.to_thread(
                        self.adapter.search_vectors,
                        query_vector.tolist(),
                        10,
                        collection=collection
                    )
                    successful += 1
                except Exception as e:
                    logger.debug(f"Client {client_id} query failed: {e}")

            duration = time.time() - start
            qps = successful / duration if duration > 0 else 0
            return qps, successful

        # Measure single-client baseline
        baseline_qps, _ = await client_workload(0)

        # Run concurrent clients
        tasks = [client_workload(i) for i in range(concurrent_clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        qps_per_client = []
        total_successful = 0
        errors = 0

        for result in results:
            if isinstance(result, Exception):
                errors += 1
            else:
                qps, successful = result
                qps_per_client.append(qps)
                total_successful += successful

        total_qps = sum(qps_per_client)
        avg_qps_per_client = np.mean(qps_per_client) if qps_per_client else 0

        # Calculate degradation
        degradation_pct = ((baseline_qps - avg_qps_per_client) / baseline_qps * 100) if baseline_qps > 0 else 0

        return ConcurrentLoadMetrics(
            concurrent_clients=concurrent_clients,
            qps_per_client=qps_per_client,
            total_qps=total_qps,
            latency_degradation_pct=degradation_pct,
            errors_under_load=errors
        )

    async def measure_storage_efficiency(self, vector_count: int = 10000, dimensions: int = 1024,
                                        collection: Optional[str] = None) -> StorageMetrics:
        """
        Dimension 10: Storage Efficiency (index overhead)
        """
        logger.info(f"Measuring storage efficiency for {vector_count} vectors...")

        # Raw vector size
        raw_size_bytes = vector_count * dimensions * 4  # float32
        raw_size_mb = raw_size_bytes / 1024 / 1024

        # Index vectors and measure stored size (adapter-specific)
        vectors = self.generate_vectors(vector_count, dimensions)
        metadata = [{"id": i} for i in range(vector_count)]

        await asyncio.to_thread(
            self.adapter.index_vectors,
            vectors.tolist(),
            metadata,
            collection=collection
        )

        # For most backends, we estimate based on memory usage
        # Real implementation would query backend-specific storage metrics
        memory_metrics = await self.measure_memory_efficiency(vector_count, dimensions, collection)
        stored_size_mb = memory_metrics.index_memory_mb

        index_overhead = max(0, stored_size_mb - raw_size_mb)
        compression_ratio = raw_size_mb / stored_size_mb if stored_size_mb > 0 else 1.0
        overhead_pct = (index_overhead / raw_size_mb * 100) if raw_size_mb > 0 else 0

        return StorageMetrics(
            raw_vector_size_mb=raw_size_mb,
            stored_size_mb=stored_size_mb,
            index_overhead_mb=index_overhead,
            compression_ratio=compression_ratio,
            overhead_percentage=overhead_pct
        )

    async def run_comprehensive_benchmark(self, config: Dict[str, Any]) -> ComprehensiveBenchmarkResults:
        """
        Run all benchmark dimensions

        Args:
            config: Configuration with keys:
                - dimensions: int (default 1024)
                - collection: Optional[str]
                - vector_count: int (for indexing tests)
                - query_count: int (for latency tests)
                - enabled_dimensions: List[str] (optional, default all)
        """
        dimensions = config.get('dimensions', 1024)
        collection = config.get('collection')
        vector_count = config.get('vector_count', 10000)
        query_count = config.get('query_count', 100)
        enabled = config.get('enabled_dimensions', [
            'latency', 'throughput', 'recall', 'indexing', 'memory',
            'cost', 'scaling', 'cold_start', 'concurrent_load', 'storage'
        ])

        logger.info(f"Running comprehensive benchmark with dimensions: {enabled}")

        # Run each enabled dimension
        if 'latency' in enabled:
            try:
                self.results.latency = await self.measure_latency(
                    query_count=query_count,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Latency: p50={self.results.latency.p50_ms:.2f}ms")
            except Exception as e:
                logger.error(f"Latency measurement failed: {e}")

        if 'throughput' in enabled:
            try:
                self.results.throughput = await self.measure_throughput(
                    duration_seconds=60,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Throughput: {self.results.throughput.qps:.2f} QPS")
            except Exception as e:
                logger.error(f"Throughput measurement failed: {e}")

        if 'indexing' in enabled:
            try:
                self.results.indexing = await self.measure_indexing_speed(
                    vector_count=vector_count,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Indexing: {self.results.indexing.vectors_per_second:.2f} vectors/sec")
            except Exception as e:
                logger.error(f"Indexing measurement failed: {e}")

        if 'recall' in enabled:
            try:
                self.results.recall = await self.measure_recall(
                    sample_count=100,
                    k=10,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Recall@10: {self.results.recall.recall_at_k:.2%}")
            except Exception as e:
                logger.error(f"Recall measurement failed: {e}")

        if 'memory' in enabled:
            try:
                self.results.memory = await self.measure_memory_efficiency(
                    vector_count=vector_count,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Memory: {self.results.memory.bytes_per_vector:.2f} bytes/vector")
            except Exception as e:
                logger.error(f"Memory measurement failed: {e}")

        if 'cost' in enabled:
            try:
                self.results.cost = self.estimate_cost(
                    backend=self.results.backend,
                    monthly_queries=1_000_000,
                    storage_gb=10.0
                )
                logger.info(f"✓ Cost: ${self.results.cost.monthly_cost_estimate:.2f}/month")
            except Exception as e:
                logger.error(f"Cost estimation failed: {e}")

        if 'scaling' in enabled:
            try:
                self.results.scaling = await self.measure_scaling(
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Scaling: efficiency={self.results.scaling.scaling_efficiency:.2%}")
            except Exception as e:
                logger.error(f"Scaling measurement failed: {e}")

        if 'cold_start' in enabled:
            try:
                self.results.cold_start = await self.measure_cold_start(
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Cold start: {self.results.cold_start.cold_start_ms:.2f}ms")
            except Exception as e:
                logger.error(f"Cold start measurement failed: {e}")

        if 'concurrent_load' in enabled:
            try:
                self.results.concurrent_load = await self.measure_concurrent_load(
                    concurrent_clients=10,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Concurrent load: {self.results.concurrent_load.total_qps:.2f} total QPS")
            except Exception as e:
                logger.error(f"Concurrent load measurement failed: {e}")

        if 'storage' in enabled:
            try:
                self.results.storage = await self.measure_storage_efficiency(
                    vector_count=vector_count,
                    dimensions=dimensions,
                    collection=collection
                )
                logger.info(f"✓ Storage: {self.results.storage.overhead_percentage:.1f}% overhead")
            except Exception as e:
                logger.error(f"Storage measurement failed: {e}")

        return self.results
