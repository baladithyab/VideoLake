"""
Comprehensive Benchmark Runner for Vector Stores.

Implements all 10 benchmark dimensions:
1. Latency (p50/p95/p99)
2. Throughput (QPS)
3. Recall@k
4. Indexing Speed
5. Memory Efficiency
6. Cost per Query
7. Scaling
8. Cold Start
9. Concurrent Load
10. Storage Efficiency
"""

import asyncio
import time
import psutil
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from src.services.benchmark_models import (
    ComprehensiveBenchmarkResult,
    LatencyMetrics,
    ThroughputMetrics,
    RecallMetrics,
    IndexingMetrics,
    MemoryMetrics,
    CostMetrics,
    ScalingMetrics,
    ColdStartMetrics,
    ConcurrentLoadMetrics,
    StorageEfficiencyMetrics,
    BenchmarkStatus,
    BenchmarkConfiguration
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ComprehensiveBenchmarkRunner:
    """
    Runs comprehensive benchmarks across all 10 dimensions for a vector store backend.
    """

    def __init__(
        self,
        backend: str,
        variant: str,
        adapter: Any,  # Backend adapter instance
        config: BenchmarkConfiguration
    ):
        self.backend = backend
        self.variant = variant
        self.adapter = adapter
        self.config = config
        self.job_id = f"{backend}_{variant}_{int(time.time())}"

    def generate_vectors(self, count: int, dimensions: int) -> np.ndarray:
        """Generate random normalized test vectors"""
        vectors = np.random.rand(count, dimensions).astype(np.float32)
        # Normalize vectors for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / norms

    async def run_all_benchmarks(self) -> ComprehensiveBenchmarkResult:
        """
        Execute all enabled benchmark dimensions and return comprehensive results.
        """
        result = ComprehensiveBenchmarkResult(
            backend=self.backend,
            variant=self.variant,
            job_id=self.job_id,
            vector_dimension=self.config.vector_dimension,
            status=BenchmarkStatus.RUNNING
        )

        try:
            logger.info(f"Starting comprehensive benchmark for {self.backend}/{self.variant}")

            # Dimension 1 & 2: Latency and Throughput (combined)
            logger.info("Running latency and throughput tests...")
            latency, throughput = await self.measure_latency_and_throughput()
            result.latency = latency
            result.throughput = throughput

            # Dimension 3: Recall@k
            if self.config.enable_recall_testing:
                logger.info("Running recall@k tests...")
                result.recall = await self.measure_recall()

            # Dimension 4: Indexing Speed
            logger.info("Running indexing speed tests...")
            result.indexing = await self.measure_indexing_speed()

            # Dimension 5: Memory Efficiency
            if self.config.enable_memory_profiling:
                logger.info("Running memory efficiency tests...")
                result.memory = await self.measure_memory_efficiency()

            # Dimension 6: Cost per Query
            logger.info("Calculating cost metrics...")
            result.cost = self.calculate_cost_metrics(result)

            # Dimension 7: Scaling
            if self.config.enable_scaling_testing and len(self.config.vector_counts) > 1:
                logger.info("Running scaling tests...")
                result.scaling = await self.measure_scaling()

            # Dimension 8: Cold Start (serverless only)
            if self.config.enable_cold_start_testing and self._is_serverless():
                logger.info("Running cold start tests...")
                result.cold_start = await self.measure_cold_start()

            # Dimension 9: Concurrent Load
            if self.config.enable_concurrent_load_testing:
                logger.info("Running concurrent load tests...")
                result.concurrent_load = await self.measure_concurrent_load()

            # Dimension 10: Storage Efficiency
            logger.info("Measuring storage efficiency...")
            result.storage_efficiency = await self.measure_storage_efficiency()

            result.status = BenchmarkStatus.COMPLETED
            logger.info(f"Benchmark completed successfully for {self.backend}/{self.variant}")

        except Exception as e:
            logger.error(f"Benchmark failed for {self.backend}/{self.variant}: {e}")
            result.status = BenchmarkStatus.FAILED
            result.error_message = str(e)

        return result

    async def measure_latency_and_throughput(
        self
    ) -> Tuple[LatencyMetrics, ThroughputMetrics]:
        """
        Measure query latency (p50/p95/p99) and throughput (QPS).
        Combines both measurements in a single test run for efficiency.
        """
        query_count = self.config.query_count
        dimension = self.config.vector_dimension
        top_k = self.config.top_k

        # Generate query vectors
        query_vectors = self.generate_vectors(query_count, dimension)

        latencies = []
        successful_queries = 0
        failed_queries = 0

        start_time = time.time()

        for query_vector in query_vectors:
            query_start = time.time()

            try:
                # Execute search via adapter
                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    top_k
                )

                query_duration = (time.time() - query_start) * 1000  # Convert to ms
                latencies.append(query_duration)

                if results:
                    successful_queries += 1
                else:
                    failed_queries += 1

            except Exception as e:
                failed_queries += 1
                logger.warning(f"Query failed: {e}")

        total_duration = time.time() - start_time

        # Calculate latency metrics
        if latencies:
            latency = LatencyMetrics(
                p50_ms=float(np.percentile(latencies, 50)),
                p95_ms=float(np.percentile(latencies, 95)),
                p99_ms=float(np.percentile(latencies, 99)),
                p999_ms=float(np.percentile(latencies, 99.9)) if len(latencies) >= 1000 else None,
                min_ms=float(np.min(latencies)),
                max_ms=float(np.max(latencies)),
                mean_ms=float(np.mean(latencies)),
                std_ms=float(np.std(latencies))
            )
        else:
            latency = LatencyMetrics(p50_ms=0, p95_ms=0, p99_ms=0)

        # Calculate throughput metrics
        qps = len(latencies) / total_duration if total_duration > 0 else 0
        error_rate = failed_queries / query_count if query_count > 0 else 0

        throughput = ThroughputMetrics(
            qps=qps,
            sustained_qps=qps,  # For single-threaded test, same as QPS
            peak_qps=qps,
            total_queries=len(latencies),
            duration_seconds=total_duration,
            error_rate=error_rate
        )

        return latency, throughput

    async def measure_recall(self) -> RecallMetrics:
        """
        Measure recall@k by comparing against ground truth (brute force search).
        """
        test_query_count = min(100, self.config.query_count)  # Limit for ground truth computation
        dimension = self.config.vector_dimension

        # Generate test dataset and queries
        dataset_size = self.config.vector_counts[0]  # Use smallest size for recall testing
        dataset_vectors = self.generate_vectors(dataset_size, dimension)
        query_vectors = self.generate_vectors(test_query_count, dimension)

        # Index the dataset
        metadata = [{"id": i} for i in range(dataset_size)]
        await asyncio.to_thread(
            self.adapter.index_vectors,
            dataset_vectors.tolist(),
            metadata
        )

        # Compute ground truth (brute force)
        ground_truth_results = []
        for query_vector in query_vectors:
            # Cosine similarity
            similarities = np.dot(dataset_vectors, query_vector)
            top_indices = np.argsort(similarities)[-self.config.top_k:][::-1]
            ground_truth_results.append(set(top_indices.tolist()))

        # Query via adapter and compare
        recall_scores = []
        for i, query_vector in enumerate(query_vectors):
            try:
                results = await asyncio.to_thread(
                    self.adapter.search_vectors,
                    query_vector.tolist(),
                    self.config.top_k
                )

                # Extract IDs from results
                result_ids = set()
                if results:
                    for r in results:
                        if isinstance(r, dict) and 'id' in r:
                            result_ids.add(r['id'])
                        elif isinstance(r, dict) and 'metadata' in r:
                            result_ids.add(r['metadata'].get('id'))

                # Calculate recall
                ground_truth = ground_truth_results[i]
                if ground_truth:
                    recall = len(result_ids & ground_truth) / len(ground_truth)
                    recall_scores.append(recall)

            except Exception as e:
                logger.warning(f"Recall test query {i} failed: {e}")

        avg_recall = np.mean(recall_scores) if recall_scores else 0.0

        return RecallMetrics(
            recall_at_10=float(avg_recall),
            ground_truth_count=len(ground_truth_results),
            test_queries=test_query_count
        )

    async def measure_indexing_speed(self) -> IndexingMetrics:
        """
        Measure indexing performance (vectors/second).
        """
        vector_count = self.config.vector_counts[0]
        dimension = self.config.vector_dimension
        batch_size = min(1000, vector_count)

        vectors = self.generate_vectors(vector_count, dimension)
        metadata = [{"id": i} for i in range(vector_count)]

        # Monitor memory before indexing
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()

        try:
            result = await asyncio.to_thread(
                self.adapter.index_vectors,
                vectors.tolist(),
                metadata
            )

            duration = time.time() - start_time
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_peak = memory_after  # Simplified - actual peak would need continuous monitoring

            if result and result.get("success", False):
                return IndexingMetrics(
                    vectors_per_second=vector_count / duration if duration > 0 else 0,
                    total_vectors=vector_count,
                    duration_seconds=duration,
                    batch_size=batch_size,
                    memory_peak_mb=memory_peak
                )
            else:
                raise Exception(f"Indexing failed: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Indexing measurement failed: {e}")
            return IndexingMetrics(
                vectors_per_second=0,
                total_vectors=0,
                duration_seconds=0,
                batch_size=batch_size
            )

    async def measure_memory_efficiency(self) -> MemoryMetrics:
        """
        Measure memory usage per vector and index overhead.
        """
        vector_count = self.config.vector_counts[0]
        dimension = self.config.vector_dimension

        # Calculate raw vector size
        raw_size_bytes = vector_count * dimension * 4  # float32 = 4 bytes
        raw_size_mb = raw_size_bytes / 1024 / 1024

        # Monitor process memory
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Index vectors
        vectors = self.generate_vectors(vector_count, dimension)
        metadata = [{"id": i} for i in range(vector_count)]

        await asyncio.to_thread(
            self.adapter.index_vectors,
            vectors.tolist(),
            metadata
        )

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = memory_after - memory_before

        # Calculate metrics
        bytes_per_vector = (memory_used * 1024 * 1024) / vector_count
        index_overhead = (memory_used - raw_size_mb) / raw_size_mb if raw_size_mb > 0 else 0

        return MemoryMetrics(
            bytes_per_vector=bytes_per_vector,
            total_memory_mb=memory_used,
            index_overhead_ratio=index_overhead,
            peak_memory_mb=memory_after,
            vector_count=vector_count
        )

    def calculate_cost_metrics(self, result: ComprehensiveBenchmarkResult) -> CostMetrics:
        """
        Calculate estimated cost per query and monthly cost.
        Uses backend-specific pricing models from research document.
        """
        # Cost models per backend (from VECTORDB_RESEARCH.md)
        cost_models = {
            "s3vector": {
                "storage_per_gb_month": 0.023,
                "request_per_1k": 0.0004,
                "query_per_1k": 0.0005
            },
            "qdrant-ecs": {
                "compute_per_hour": 3.01,  # 2vCPU/8GB Fargate
                "storage_per_gb_month": 0.08  # EFS
            },
            "lancedb-ecs": {
                "compute_per_hour": 3.01,
                "storage_per_gb_month": 0.08
            },
            "lancedb-s3": {
                "compute_per_hour": 0.20,  # Minimal compute
                "storage_per_gb_month": 0.023
            },
            "opensearch-provisioned": {
                "instance_per_hour": 0.167,  # r6g.large
                "storage_per_gb_month": 0.08
            },
            "opensearch-serverless": {
                "ocu_per_hour": 0.24,
                "min_ocu": 4,
                "storage_per_gb_month": 0.024
            },
            "pgvector-aurora": {
                "acu_per_hour": 0.12,
                "min_acu": 0.5,
                "storage_per_gb_month": 0.10,
                "io_per_million": 0.20
            }
        }

        # Get cost model for backend
        backend_key = f"{self.backend}-{self.variant}" if self.variant else self.backend
        cost_model = cost_models.get(backend_key) or cost_models.get(self.backend, {})

        if not cost_model:
            # Default model
            cost_model = {"compute_per_hour": 0.10, "storage_per_gb_month": 0.05}

        # Calculate storage cost
        vector_count = result.vector_count or self.config.vector_counts[0]
        vector_size_gb = (vector_count * self.config.vector_dimension * 4) / 1024 / 1024 / 1024
        storage_cost_month = vector_size_gb * cost_model.get("storage_per_gb_month", 0.05)

        # Calculate compute cost
        if "compute_per_hour" in cost_model:
            compute_cost_month = cost_model["compute_per_hour"] * 24 * 30
        elif "instance_per_hour" in cost_model:
            compute_cost_month = cost_model["instance_per_hour"] * 24 * 30 * 3  # 3 nodes
        elif "ocu_per_hour" in cost_model:
            compute_cost_month = cost_model["ocu_per_hour"] * cost_model.get("min_ocu", 1) * 24 * 30
        elif "acu_per_hour" in cost_model:
            compute_cost_month = cost_model["acu_per_hour"] * cost_model.get("min_acu", 1) * 24 * 30
        else:
            compute_cost_month = 100  # Default estimate

        # Calculate per-query cost
        queries_per_month = self.config.queries_per_day * self.config.days_per_month
        monthly_cost = compute_cost_month + storage_cost_month

        # Add request costs for serverless
        if "request_per_1k" in cost_model:
            request_cost_month = (queries_per_month / 1000) * cost_model["request_per_1k"]
            monthly_cost += request_cost_month

        cost_per_query = monthly_cost / queries_per_month if queries_per_month > 0 else 0

        return CostMetrics(
            cost_per_query_usd=cost_per_query,
            cost_per_1k_queries_usd=cost_per_query * 1000,
            monthly_cost_estimate_usd=monthly_cost,
            storage_cost_per_month_usd=storage_cost_month,
            compute_cost_per_hour_usd=cost_model.get("compute_per_hour") or cost_model.get("instance_per_hour")
        )

    async def measure_scaling(self) -> ScalingMetrics:
        """
        Measure performance across different dataset sizes.
        """
        latency_by_size = {}
        qps_by_size = {}
        indexing_time_by_size = {}

        for vector_count in self.config.vector_counts:
            logger.info(f"Testing scaling at {vector_count} vectors...")

            # Index data
            vectors = self.generate_vectors(vector_count, self.config.vector_dimension)
            metadata = [{"id": i} for i in range(vector_count)]

            index_start = time.time()
            await asyncio.to_thread(
                self.adapter.index_vectors,
                vectors.tolist(),
                metadata
            )
            indexing_time = time.time() - index_start
            indexing_time_by_size[vector_count] = indexing_time

            # Measure query performance
            query_count = min(100, self.config.query_count)  # Reduced for scaling test
            query_vectors = self.generate_vectors(query_count, self.config.vector_dimension)

            latencies = []
            start_time = time.time()

            for query_vector in query_vectors:
                query_start = time.time()
                try:
                    await asyncio.to_thread(
                        self.adapter.search_vectors,
                        query_vector.tolist(),
                        self.config.top_k
                    )
                    latencies.append((time.time() - query_start) * 1000)
                except Exception:
                    pass

            duration = time.time() - start_time

            if latencies:
                latency_by_size[vector_count] = float(np.percentile(latencies, 99))
                qps_by_size[vector_count] = len(latencies) / duration

        return ScalingMetrics(
            dataset_sizes=self.config.vector_counts,
            latency_p99_by_size=latency_by_size,
            qps_by_size=qps_by_size,
            indexing_time_by_size=indexing_time_by_size
        )

    async def measure_cold_start(self) -> ColdStartMetrics:
        """
        Measure cold start time for serverless backends.
        """
        # This is a simplified implementation
        # Real implementation would restart the service and measure

        query_vector = self.generate_vectors(1, self.config.vector_dimension)[0]

        # First query (cold)
        cold_start = time.time()
        await asyncio.to_thread(
            self.adapter.search_vectors,
            query_vector.tolist(),
            self.config.top_k
        )
        cold_time = (time.time() - cold_start) * 1000

        # Second query (warm)
        warm_start = time.time()
        await asyncio.to_thread(
            self.adapter.search_vectors,
            query_vector.tolist(),
            self.config.top_k
        )
        warm_time = (time.time() - warm_start) * 1000

        return ColdStartMetrics(
            cold_start_time_ms=cold_time,
            warm_start_time_ms=warm_time,
            initialization_overhead_ms=cold_time - warm_time,
            first_query_latency_ms=cold_time
        )

    async def measure_concurrent_load(self) -> ConcurrentLoadMetrics:
        """
        Measure performance under concurrent load.
        """
        concurrent_clients = self.config.concurrent_clients
        queries_per_client = self.config.query_count // concurrent_clients

        query_vectors = self.generate_vectors(
            queries_per_client * concurrent_clients,
            self.config.vector_dimension
        )

        async def run_client_queries(client_id: int) -> Dict[str, Any]:
            """Run queries for a single client"""
            start_idx = client_id * queries_per_client
            end_idx = start_idx + queries_per_client
            client_vectors = query_vectors[start_idx:end_idx]

            latencies = []
            successes = 0
            failures = 0

            for query_vector in client_vectors:
                query_start = time.time()
                try:
                    results = await asyncio.to_thread(
                        self.adapter.search_vectors,
                        query_vector.tolist(),
                        self.config.top_k
                    )
                    latencies.append((time.time() - query_start) * 1000)
                    if results:
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1

            return {
                "latencies": latencies,
                "successes": successes,
                "failures": failures
            }

        # Run concurrent clients
        start_time = time.time()
        tasks = [run_client_queries(i) for i in range(concurrent_clients)]
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Aggregate results
        all_latencies = []
        total_successes = 0
        total_failures = 0

        for result in results:
            all_latencies.extend(result["latencies"])
            total_successes += result["successes"]
            total_failures += result["failures"]

        total_requests = total_successes + total_failures
        p99_latency = float(np.percentile(all_latencies, 99)) if all_latencies else 0
        throughput = len(all_latencies) / duration if duration > 0 else 0
        error_rate = total_failures / total_requests if total_requests > 0 else 0

        return ConcurrentLoadMetrics(
            concurrent_clients=concurrent_clients,
            total_requests=total_requests,
            successful_requests=total_successes,
            failed_requests=total_failures,
            latency_p99_ms=p99_latency,
            throughput_qps=throughput,
            error_rate=error_rate
        )

    async def measure_storage_efficiency(self) -> StorageEfficiencyMetrics:
        """
        Measure storage utilization and overhead.
        """
        vector_count = self.config.vector_counts[0]
        dimension = self.config.vector_dimension

        # Calculate raw vector size
        raw_size = vector_count * dimension * 4  # float32 = 4 bytes

        # For now, estimate stored size
        # Real implementation would query the backend's storage API
        # Most vector DBs have 1.2-2x overhead for indexing

        # Estimate based on backend type
        if "s3vector" in self.backend:
            overhead = 1.05  # S3Vector is very efficient
        elif "faiss" in self.backend:
            overhead = 1.1  # FAISS is efficient
        elif "lancedb" in self.backend:
            overhead = 1.3  # Columnar overhead
        elif "hnsw" in self.variant or "opensearch" in self.backend or "qdrant" in self.backend:
            overhead = 1.8  # HNSW graph overhead
        else:
            overhead = 1.5  # Default

        stored_size = int(raw_size * overhead)
        index_size = stored_size - raw_size
        overhead_pct = ((stored_size - raw_size) / raw_size * 100) if raw_size > 0 else 0

        return StorageEfficiencyMetrics(
            raw_vector_size_bytes=raw_size,
            stored_size_bytes=stored_size,
            index_size_bytes=index_size,
            overhead_percentage=overhead_pct
        )

    def _is_serverless(self) -> bool:
        """Check if the backend is serverless"""
        serverless_keywords = ["serverless", "lambda", "s3vector"]
        return any(keyword in self.backend.lower() or keyword in self.variant.lower()
                   for keyword in serverless_keywords)
