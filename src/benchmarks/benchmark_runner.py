"""
Benchmark Runner

Orchestrates benchmark execution across multiple backends with:
- Sequential or parallel execution
- Progress tracking
- Error handling and retry logic
- Results aggregation
- Report generation
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime

from src.benchmarks.benchmark_config import (
    BenchmarkConfig,
    BenchmarkResult,
    BackendVariant,
    BenchmarkDimension,
    DimensionResult,
    DatasetConfig,
)
from src.services.benchmark_dimensions import (
    BenchmarkDimensionsRunner,
    ComprehensiveBenchmarkResults,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BenchmarkRunner:
    """
    Executes benchmarks for a single backend according to configuration
    """

    def __init__(self, config: BenchmarkConfig):
        """
        Args:
            config: Benchmark configuration
        """
        self.config = config
        self.results: Optional[BenchmarkResult] = None

    def get_backend_adapter(self, backend: BackendVariant):
        """
        Get backend adapter for the specified variant

        Returns adapter compatible with BenchmarkDimensionsRunner
        """
        try:
            from scripts.backend_adapters import get_backend_adapter

            # Get adapter with default config
            adapter = get_backend_adapter(
                backend=backend.value,
                config={}
            )

            # Add backend name for identification
            adapter.backend_name = backend.value

            return adapter

        except ImportError as e:
            logger.error(f"Failed to import backend adapters: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create adapter for {backend.value}: {e}")
            raise

    def convert_dimension_results(self, comprehensive_results: ComprehensiveBenchmarkResults,
                                  enabled_dimensions: List[BenchmarkDimension]) -> Dict[BenchmarkDimension, DimensionResult]:
        """
        Convert ComprehensiveBenchmarkResults to DimensionResult format

        Args:
            comprehensive_results: Raw results from BenchmarkDimensionsRunner
            enabled_dimensions: Dimensions that were measured

        Returns:
            Dictionary of dimension -> DimensionResult
        """
        results = {}

        # Latency
        if BenchmarkDimension.LATENCY in enabled_dimensions and comprehensive_results.latency:
            lat = comprehensive_results.latency
            results[BenchmarkDimension.LATENCY] = DimensionResult(
                dimension=BenchmarkDimension.LATENCY,
                value=lat.p50_ms,
                unit="ms",
                metadata={
                    'p50_ms': lat.p50_ms,
                    'p95_ms': lat.p95_ms,
                    'p99_ms': lat.p99_ms,
                    'p999_ms': lat.p999_ms,
                    'min_ms': lat.min_ms,
                    'max_ms': lat.max_ms,
                    'mean_ms': lat.mean_ms,
                    'std_ms': lat.std_ms,
                    'samples': lat.samples,
                },
                success=True
            )

        # Throughput
        if BenchmarkDimension.THROUGHPUT in enabled_dimensions and comprehensive_results.throughput:
            thr = comprehensive_results.throughput
            results[BenchmarkDimension.THROUGHPUT] = DimensionResult(
                dimension=BenchmarkDimension.THROUGHPUT,
                value=thr.qps,
                unit="QPS",
                metadata={
                    'duration_seconds': thr.duration_seconds,
                    'total_queries': thr.total_queries,
                    'successful_queries': thr.successful_queries,
                    'failed_queries': thr.failed_queries,
                    'error_rate': thr.error_rate,
                },
                success=True
            )

        # Recall
        if BenchmarkDimension.RECALL in enabled_dimensions and comprehensive_results.recall:
            rec = comprehensive_results.recall
            results[BenchmarkDimension.RECALL] = DimensionResult(
                dimension=BenchmarkDimension.RECALL,
                value=rec.recall_at_k,
                unit="ratio",
                metadata={
                    'k': rec.k,
                    'ground_truth_method': rec.ground_truth_method,
                    'distance_correlation': rec.distance_correlation,
                    'samples_evaluated': rec.samples_evaluated,
                },
                success=True
            )

        # Indexing Speed
        if BenchmarkDimension.INDEXING_SPEED in enabled_dimensions and comprehensive_results.indexing:
            idx = comprehensive_results.indexing
            results[BenchmarkDimension.INDEXING_SPEED] = DimensionResult(
                dimension=BenchmarkDimension.INDEXING_SPEED,
                value=idx.vectors_per_second,
                unit="vectors/sec",
                metadata={
                    'total_vectors': idx.total_vectors,
                    'duration_seconds': idx.duration_seconds,
                    'batch_size': idx.batch_size,
                    'peak_memory_mb': idx.peak_memory_mb,
                    'build_time_seconds': idx.build_time_seconds,
                },
                success=True
            )

        # Memory Efficiency
        if BenchmarkDimension.MEMORY_EFFICIENCY in enabled_dimensions and comprehensive_results.memory:
            mem = comprehensive_results.memory
            results[BenchmarkDimension.MEMORY_EFFICIENCY] = DimensionResult(
                dimension=BenchmarkDimension.MEMORY_EFFICIENCY,
                value=mem.bytes_per_vector,
                unit="bytes/vector",
                metadata={
                    'total_memory_mb': mem.total_memory_mb,
                    'index_memory_mb': mem.index_memory_mb,
                    'overhead_percentage': mem.overhead_percentage,
                    'peak_memory_mb': mem.peak_memory_mb,
                },
                success=True
            )

        # Cost per Query
        if BenchmarkDimension.COST_PER_QUERY in enabled_dimensions and comprehensive_results.cost:
            cost = comprehensive_results.cost
            results[BenchmarkDimension.COST_PER_QUERY] = DimensionResult(
                dimension=BenchmarkDimension.COST_PER_QUERY,
                value=cost.cost_per_million_queries,
                unit="$/1M queries",
                metadata={
                    'monthly_cost_estimate': cost.monthly_cost_estimate,
                    'storage_cost_per_gb': cost.storage_cost_per_gb,
                    'compute_cost_per_hour': cost.compute_cost_per_hour,
                    'cost_breakdown': cost.total_cost_breakdown,
                },
                success=True
            )

        # Scaling
        if BenchmarkDimension.SCALING in enabled_dimensions and comprehensive_results.scaling:
            scl = comprehensive_results.scaling
            results[BenchmarkDimension.SCALING] = DimensionResult(
                dimension=BenchmarkDimension.SCALING,
                value=scl.scaling_efficiency,
                unit="efficiency ratio",
                metadata={
                    'vector_counts': scl.vector_counts,
                    'latency_at_scale': scl.latency_at_scale,
                    'qps_at_scale': scl.qps_at_scale,
                },
                success=True
            )

        # Cold Start
        if BenchmarkDimension.COLD_START in enabled_dimensions and comprehensive_results.cold_start:
            cold = comprehensive_results.cold_start
            results[BenchmarkDimension.COLD_START] = DimensionResult(
                dimension=BenchmarkDimension.COLD_START,
                value=cold.cold_start_ms,
                unit="ms",
                metadata={
                    'warm_start_ms': cold.warm_start_ms,
                    'initialization_overhead_ms': cold.initialization_overhead_ms,
                    'applicable': cold.applicable,
                },
                success=True
            )

        # Concurrent Load
        if BenchmarkDimension.CONCURRENT_LOAD in enabled_dimensions and comprehensive_results.concurrent_load:
            conc = comprehensive_results.concurrent_load
            results[BenchmarkDimension.CONCURRENT_LOAD] = DimensionResult(
                dimension=BenchmarkDimension.CONCURRENT_LOAD,
                value=conc.total_qps,
                unit="QPS",
                metadata={
                    'concurrent_clients': conc.concurrent_clients,
                    'qps_per_client': conc.qps_per_client,
                    'latency_degradation_pct': conc.latency_degradation_pct,
                    'errors_under_load': conc.errors_under_load,
                },
                success=True
            )

        # Storage Efficiency
        if BenchmarkDimension.STORAGE_EFFICIENCY in enabled_dimensions and comprehensive_results.storage:
            stor = comprehensive_results.storage
            results[BenchmarkDimension.STORAGE_EFFICIENCY] = DimensionResult(
                dimension=BenchmarkDimension.STORAGE_EFFICIENCY,
                value=stor.overhead_percentage,
                unit="%",
                metadata={
                    'raw_vector_size_mb': stor.raw_vector_size_mb,
                    'stored_size_mb': stor.stored_size_mb,
                    'index_overhead_mb': stor.index_overhead_mb,
                    'compression_ratio': stor.compression_ratio,
                },
                success=True
            )

        return results

    async def run(self, backend: BackendVariant,
                  progress_callback: Optional[Callable[[str, float], None]] = None) -> BenchmarkResult:
        """
        Run benchmark for a single backend

        Args:
            backend: Backend variant to test
            progress_callback: Optional callback(message, progress_pct)

        Returns:
            BenchmarkResult with all measured dimensions
        """
        logger.info(f"Starting benchmark for {backend.value}")
        start_time = time.time()

        result = BenchmarkResult(
            backend=backend,
            timestamp=datetime.utcnow(),
            dataset=self.config.dataset,
        )

        try:
            # Get backend adapter
            if progress_callback:
                progress_callback(f"Initializing {backend.value}", 0)

            adapter = self.get_backend_adapter(backend)

            # Validate connectivity
            logger.info(f"Validating {backend.value} connectivity...")
            is_healthy = adapter.health_check()
            if not is_healthy:
                raise RuntimeError(f"{backend.value} is not accessible")

            if progress_callback:
                progress_callback(f"Running benchmarks for {backend.value}", 10)

            # Create benchmark runner
            dimensions_runner = BenchmarkDimensionsRunner(adapter)

            # Build dimensions runner config
            runner_config = {
                'dimensions': self.config.dataset.dimensions,
                'collection': None,  # Can be parameterized
                'vector_count': self.config.dataset.vector_count,
                'query_count': self.config.query_count,
                'enabled_dimensions': [dim.value for dim in self.config.enabled_dimensions]
            }

            # Run comprehensive benchmark
            comprehensive_results = await dimensions_runner.run_comprehensive_benchmark(runner_config)

            # Convert results to DimensionResult format
            dimension_results = self.convert_dimension_results(
                comprehensive_results,
                self.config.enabled_dimensions
            )

            # Assign dimension results to BenchmarkResult
            for dim, dim_result in dimension_results.items():
                result.set_dimension_result(dim_result)

            result.success = True
            logger.info(f"✓ Successfully completed benchmark for {backend.value}")

            if progress_callback:
                progress_callback(f"Completed {backend.value}", 100)

        except Exception as e:
            logger.error(f"Benchmark failed for {backend.value}: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)

            if progress_callback:
                progress_callback(f"Failed: {backend.value}", 100)

        result.duration_seconds = time.time() - start_time
        self.results = result
        return result


class BenchmarkOrchestrator:
    """
    Orchestrates benchmarks across multiple backends with:
    - Sequential or parallel execution
    - Progress tracking
    - Results aggregation
    - Report generation
    """

    def __init__(self, config: BenchmarkConfig):
        """
        Args:
            config: Benchmark configuration
        """
        self.config = config
        self.results: Dict[BackendVariant, BenchmarkResult] = {}
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def run_all(self, progress_callback: Optional[Callable[[str, Dict], None]] = None) -> Dict[BackendVariant, BenchmarkResult]:
        """
        Run benchmarks for all configured backends

        Args:
            progress_callback: Optional callback(status_message, progress_dict)

        Returns:
            Dictionary of backend -> BenchmarkResult
        """
        logger.info(f"Starting benchmark run: {self.config.run_id}")
        logger.info(f"Backends to test: {len(self.config.backends)}")

        # Run benchmarks with concurrency limit
        semaphore = asyncio.Semaphore(self.config.max_concurrent_backends)

        async def run_with_semaphore(backend: BackendVariant, index: int):
            async with semaphore:
                runner = BenchmarkRunner(self.config)

                def backend_progress(msg: str, pct: float):
                    if progress_callback:
                        progress = {
                            'current_backend': backend.value,
                            'backend_index': index,
                            'total_backends': len(self.config.backends),
                            'backend_progress': pct,
                            'overall_progress': ((index * 100 + pct) / len(self.config.backends))
                        }
                        progress_callback(msg, progress)

                try:
                    result = await asyncio.wait_for(
                        runner.run(backend, backend_progress),
                        timeout=self.config.timeout_seconds
                    )
                    return backend, result
                except asyncio.TimeoutError:
                    logger.error(f"Benchmark timed out for {backend.value}")
                    result = BenchmarkResult(
                        backend=backend,
                        timestamp=datetime.utcnow(),
                        dataset=self.config.dataset,
                        success=False,
                        error_message=f"Timeout after {self.config.timeout_seconds}s"
                    )
                    return backend, result

        # Create tasks for all backends
        tasks = [run_with_semaphore(backend, i) for i, backend in enumerate(self.config.backends)]

        # Execute and gather results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Backend failed with exception: {result}")
            else:
                backend, benchmark_result = result
                self.results[backend] = benchmark_result

                # Save individual result
                if self.config.save_raw_results:
                    self._save_backend_result(backend, benchmark_result)

        logger.info(f"Completed {len(self.results)}/{len(self.config.backends)} benchmarks")

        # Generate report if requested
        if self.config.generate_report:
            report = self.generate_comparison_report()
            self._save_report(report)

        # Save aggregate results
        self._save_aggregate_results()

        return self.results

    def _save_backend_result(self, backend: BackendVariant, result: BenchmarkResult):
        """Save individual backend result to JSON"""
        filename = f"{backend.value}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.info(f"Saved result to {filepath}")

    def _save_aggregate_results(self):
        """Save all results in one file"""
        filename = f"{self.config.run_id}_results.json"
        filepath = self.output_dir / filename

        aggregate = {
            'run_id': self.config.run_id,
            'timestamp': datetime.utcnow().isoformat(),
            'config': {
                'dataset': {
                    'name': self.config.dataset.name,
                    'vector_count': self.config.dataset.vector_count,
                    'dimensions': self.config.dataset.dimensions,
                },
                'backends_tested': len(self.results),
                'enabled_dimensions': [dim.value for dim in self.config.enabled_dimensions],
            },
            'results': {
                backend.value: result.to_dict()
                for backend, result in self.results.items()
            }
        }

        with open(filepath, 'w') as f:
            json.dump(aggregate, f, indent=2)

        logger.info(f"Saved aggregate results to {filepath}")

    def generate_comparison_report(self) -> str:
        """
        Generate markdown comparison report

        Returns:
            Markdown-formatted report
        """
        if not self.results:
            return "No benchmark results available"

        lines = []
        lines.append(f"# Benchmark Comparison Report")
        lines.append(f"\n**Run ID:** {self.config.run_id}")
        lines.append(f"**Timestamp:** {datetime.utcnow().isoformat()}")
        lines.append(f"**Dataset:** {self.config.dataset.name} ({self.config.dataset.vector_count:,} vectors @ {self.config.dataset.dimensions}D)")
        lines.append(f"**Backends Tested:** {len(self.results)}")
        lines.append("\n---\n")

        # Performance table
        lines.append("## Performance Comparison\n")
        lines.append("| Backend | P50 Latency | P99 Latency | QPS | Recall@10 | Indexing Speed |")
        lines.append("|---------|-------------|-------------|-----|-----------|----------------|")

        for backend, result in sorted(self.results.items(), key=lambda x: x[0].value):
            p50 = f"{result.latency.metadata['p50_ms']:.2f}ms" if result.latency else "N/A"
            p99 = f"{result.latency.metadata['p99_ms']:.2f}ms" if result.latency else "N/A"
            qps = f"{result.throughput.value:.1f}" if result.throughput else "N/A"
            recall = f"{result.recall.value:.1%}" if result.recall else "N/A"
            idx_speed = f"{result.indexing_speed.value:.0f} vec/s" if result.indexing_speed else "N/A"

            lines.append(f"| {backend.value} | {p50} | {p99} | {qps} | {recall} | {idx_speed} |")

        # Cost table
        lines.append("\n## Cost Analysis\n")
        lines.append("| Backend | Monthly Cost | Cost per 1M Queries | Storage Cost/GB |")
        lines.append("|---------|--------------|---------------------|-----------------|")

        for backend, result in sorted(self.results.items(), key=lambda x: x[0].value):
            if result.cost_per_query:
                monthly = f"${result.cost_per_query.metadata['monthly_cost_estimate']:.2f}"
                per_million = f"${result.cost_per_query.value:.2f}"
                storage = f"${result.cost_per_query.metadata['storage_cost_per_gb']:.3f}"
            else:
                monthly = per_million = storage = "N/A"

            lines.append(f"| {backend.value} | {monthly} | {per_million} | {storage} |")

        # Efficiency table
        lines.append("\n## Efficiency Metrics\n")
        lines.append("| Backend | Bytes/Vector | Memory Overhead | Scaling Efficiency |")
        lines.append("|---------|--------------|-----------------|-------------------|")

        for backend, result in sorted(self.results.items(), key=lambda x: x[0].value):
            bytes_vec = f"{result.memory_efficiency.value:.1f}" if result.memory_efficiency else "N/A"
            overhead = f"{result.memory_efficiency.metadata.get('overhead_percentage', 0):.1f}%" if result.memory_efficiency else "N/A"
            scaling = f"{result.scaling.value:.1%}" if result.scaling else "N/A"

            lines.append(f"| {backend.value} | {bytes_vec} | {overhead} | {scaling} |")

        # Key findings
        lines.append("\n## Key Findings\n")

        # Best latency
        latency_results = [(b, r) for b, r in self.results.items() if r.latency and r.success]
        if latency_results:
            best_lat = min(latency_results, key=lambda x: x[1].latency.metadata['p50_ms'])
            lines.append(f"- **Lowest Latency:** {best_lat[0].value} ({best_lat[1].latency.metadata['p50_ms']:.2f}ms p50)")

        # Best throughput
        qps_results = [(b, r) for b, r in self.results.items() if r.throughput and r.success]
        if qps_results:
            best_qps = max(qps_results, key=lambda x: x[1].throughput.value)
            lines.append(f"- **Highest Throughput:** {best_qps[0].value} ({best_qps[1].throughput.value:.1f} QPS)")

        # Best cost
        cost_results = [(b, r) for b, r in self.results.items() if r.cost_per_query and r.success]
        if cost_results:
            best_cost = min(cost_results, key=lambda x: x[1].cost_per_query.metadata['monthly_cost_estimate'])
            lines.append(f"- **Lowest Cost:** {best_cost[0].value} (${best_cost[1].cost_per_query.metadata['monthly_cost_estimate']:.2f}/month)")

        return "\n".join(lines)

    def _save_report(self, report: str):
        """Save report to markdown file"""
        filename = f"{self.config.run_id}_report.md"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            f.write(report)

        logger.info(f"Saved report to {filepath}")
