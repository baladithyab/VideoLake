"""
Comprehensive Automated Benchmark Runner

Orchestrates benchmarks across all vector DB variants with:
- Automated backend detection and initialization
- Parallel execution across multiple backends
- Results storage and comparison
- Report generation
- Support for 12-15 vector DB variants across 3 tiers
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from src.services.benchmark_dimensions import (
    BenchmarkDimensionsRunner,
    ComprehensiveBenchmarkResults
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BackendConfig:
    """Configuration for a vector database backend"""
    name: str
    variant: str
    tier: int  # 1=MUST, 2=SHOULD, 3=OPTIONAL
    enabled: bool = True
    endpoint: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dimensions: int = 1024
    vector_count: int = 10000
    collection: Optional[str] = None


class BenchmarkRegistry:
    """
    Registry of supported vector database backends

    Based on research document recommendations:
    - Tier 1 (MUST): 7 variants
    - Tier 2 (SHOULD): 5 variants
    - Tier 3 (OPTIONAL): 3 variants
    """

    # Tier 1: Must include (core comparison)
    TIER_1_BACKENDS = [
        BackendConfig(name='s3vector', variant='serverless', tier=1),
        BackendConfig(name='qdrant', variant='ecs-efs', tier=1),
        BackendConfig(name='lancedb', variant='ebs', tier=1),
        BackendConfig(name='lancedb', variant='s3-remote-api', tier=1),
        BackendConfig(name='opensearch', variant='provisioned-hnsw', tier=1),
        BackendConfig(name='pgvector', variant='aurora-serverless', tier=1),
        BackendConfig(name='pgvector', variant='rds-postgresql', tier=1),
    ]

    # Tier 2: Should include (important alternatives)
    TIER_2_BACKENDS = [
        BackendConfig(name='pgvector', variant='aurora-ivfflat', tier=2),
        BackendConfig(name='opensearch', variant='serverless', tier=2),
        BackendConfig(name='qdrant', variant='cloud-managed', tier=2),
        BackendConfig(name='faiss', variant='embedded', tier=2),
        BackendConfig(name='zilliz', variant='cloud', tier=2),
    ]

    # Tier 3: Optional (specialized)
    TIER_3_BACKENDS = [
        BackendConfig(name='faiss', variant='lambda', tier=3),
        BackendConfig(name='faiss', variant='ec2-gpu', tier=3),
        BackendConfig(name='opensearch', variant='algorithm-comparison', tier=3),
    ]

    @classmethod
    def get_all_backends(cls, tier_filter: Optional[int] = None) -> List[BackendConfig]:
        """Get all registered backends, optionally filtered by tier"""
        all_backends = cls.TIER_1_BACKENDS + cls.TIER_2_BACKENDS + cls.TIER_3_BACKENDS

        if tier_filter is not None:
            return [b for b in all_backends if b.tier <= tier_filter]

        return all_backends

    @classmethod
    def get_backend(cls, name: str, variant: str) -> Optional[BackendConfig]:
        """Get specific backend configuration"""
        for backend in cls.get_all_backends():
            if backend.name == name and backend.variant == variant:
                return backend
        return None

    @classmethod
    def list_backend_names(cls) -> List[str]:
        """List all backend name+variant combinations"""
        return [f"{b.name}-{b.variant}" for b in cls.get_all_backends()]


class ComprehensiveBenchmarkRunner:
    """
    Automated benchmark runner for all vector DB variants
    """

    def __init__(self, output_dir: Path = None):
        """
        Args:
            output_dir: Directory to store results (default: ./benchmark_results)
        """
        self.output_dir = output_dir or Path('./benchmark_results')
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.results: Dict[str, ComprehensiveBenchmarkResults] = {}
        self.registry = BenchmarkRegistry()

    def get_backend_adapter(self, backend_config: BackendConfig):
        """
        Get backend adapter for the specified configuration

        Returns adapter compatible with BenchmarkDimensionsRunner
        """
        # Import backend adapters dynamically
        try:
            from scripts.backend_adapters import get_backend_adapter

            # Build adapter key
            adapter_key = f"{backend_config.name}-{backend_config.variant}"

            # Get adapter with config
            adapter = get_backend_adapter(
                backend=adapter_key,
                config=backend_config.config
            )

            # Add backend name for identification
            adapter.backend_name = adapter_key

            return adapter

        except ImportError as e:
            logger.error(f"Failed to import backend adapters: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create adapter for {backend_config.name}-{backend_config.variant}: {e}")
            raise

    async def run_backend_benchmark(self, backend_config: BackendConfig,
                                    benchmark_config: Dict[str, Any]) -> Optional[ComprehensiveBenchmarkResults]:
        """
        Run comprehensive benchmark for a single backend

        Args:
            backend_config: Backend configuration
            benchmark_config: Benchmark parameters (dimensions, vector_count, etc.)

        Returns:
            ComprehensiveBenchmarkResults or None if failed
        """
        backend_key = f"{backend_config.name}-{backend_config.variant}"
        logger.info(f"Starting benchmark for {backend_key}...")

        try:
            # Get backend adapter
            adapter = self.get_backend_adapter(backend_config)

            # Validate connectivity
            logger.info(f"Validating {backend_key} connectivity...")
            is_healthy = adapter.health_check()
            if not is_healthy:
                logger.error(f"{backend_key} is not accessible, skipping...")
                return None

            # Create benchmark runner
            runner = BenchmarkDimensionsRunner(adapter)

            # Run comprehensive benchmark
            config = {
                'dimensions': benchmark_config.get('dimensions', 1024),
                'collection': backend_config.collection,
                'vector_count': benchmark_config.get('vector_count', 10000),
                'query_count': benchmark_config.get('query_count', 100),
                'enabled_dimensions': benchmark_config.get('enabled_dimensions', [
                    'latency', 'throughput', 'recall', 'indexing', 'memory',
                    'cost', 'scaling', 'cold_start', 'concurrent_load', 'storage'
                ])
            }

            results = await runner.run_comprehensive_benchmark(config)

            # Store results
            self.results[backend_key] = results

            # Save to file
            self._save_backend_results(backend_key, results)

            logger.info(f"✓ Completed benchmark for {backend_key}")
            return results

        except Exception as e:
            logger.error(f"Benchmark failed for {backend_key}: {e}", exc_info=True)
            return None

    def _save_backend_results(self, backend_key: str, results: ComprehensiveBenchmarkResults):
        """Save individual backend results to JSON file"""
        timestamp = results.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{backend_key}_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w') as f:
            json.dump(results.to_dict(), f, indent=2)

        logger.info(f"Saved results to {filepath}")

    async def run_all_benchmarks(self, tier_filter: Optional[int] = None,
                                 backend_filter: Optional[List[str]] = None,
                                 benchmark_config: Optional[Dict[str, Any]] = None) -> Dict[str, ComprehensiveBenchmarkResults]:
        """
        Run benchmarks for all (or filtered) backends

        Args:
            tier_filter: Only run backends up to this tier (1, 2, or 3)
            backend_filter: List of backend keys to run (e.g., ['s3vector-serverless'])
            benchmark_config: Benchmark parameters

        Returns:
            Dictionary of backend_key -> results
        """
        benchmark_config = benchmark_config or {}

        # Get backends to test
        backends = self.registry.get_all_backends(tier_filter)

        # Apply backend filter
        if backend_filter:
            backends = [b for b in backends if f"{b.name}-{b.variant}" in backend_filter]

        logger.info(f"Running benchmarks for {len(backends)} backends...")

        # Run benchmarks in parallel (with concurrency limit)
        max_concurrent = benchmark_config.get('max_concurrent_backends', 3)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(backend: BackendConfig):
            async with semaphore:
                return await self.run_backend_benchmark(backend, benchmark_config)

        tasks = [run_with_semaphore(backend) for backend in backends]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out failures
        successful_results = {}
        for backend, result in zip(backends, results):
            backend_key = f"{backend.name}-{backend.variant}"
            if isinstance(result, Exception):
                logger.error(f"Backend {backend_key} failed: {result}")
            elif result is not None:
                successful_results[backend_key] = result

        logger.info(f"Completed {len(successful_results)}/{len(backends)} benchmarks successfully")

        # Save aggregate results
        self._save_aggregate_results(successful_results)

        return successful_results

    def _save_aggregate_results(self, results: Dict[str, ComprehensiveBenchmarkResults]):
        """Save all results in a single comparison file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"benchmark_comparison_{timestamp}.json"
        filepath = self.output_dir / filename

        aggregate = {
            'timestamp': timestamp,
            'backends_tested': len(results),
            'results': {key: result.to_dict() for key, result in results.items()}
        }

        with open(filepath, 'w') as f:
            json.dump(aggregate, f, indent=2)

        logger.info(f"Saved aggregate results to {filepath}")

    def generate_comparison_report(self, results: Optional[Dict[str, ComprehensiveBenchmarkResults]] = None) -> str:
        """
        Generate comparison report across all backends

        Returns:
            Markdown-formatted report
        """
        results = results or self.results

        if not results:
            return "No benchmark results available"

        # Build comparison tables
        report = []
        report.append("# Vector Database Benchmark Comparison Report")
        report.append(f"\nGenerated: {datetime.utcnow().isoformat()}")
        report.append(f"\nBackends tested: {len(results)}")
        report.append("\n---\n")

        # Performance comparison table
        report.append("## Performance Comparison")
        report.append("\n| Backend | P50 Latency | P99 Latency | QPS | Recall@10 | Indexing (vec/s) |")
        report.append("|---------|-------------|-------------|-----|-----------|------------------|")

        for backend_key, result in sorted(results.items()):
            latency = result.latency
            throughput = result.throughput
            recall = result.recall
            indexing = result.indexing

            p50 = f"{latency.p50_ms:.2f}ms" if latency else "N/A"
            p99 = f"{latency.p99_ms:.2f}ms" if latency else "N/A"
            qps = f"{throughput.qps:.1f}" if throughput else "N/A"
            recall_val = f"{recall.recall_at_k:.1%}" if recall else "N/A"
            idx_speed = f"{indexing.vectors_per_second:.0f}" if indexing else "N/A"

            report.append(f"| {backend_key} | {p50} | {p99} | {qps} | {recall_val} | {idx_speed} |")

        # Cost comparison
        report.append("\n## Cost Comparison")
        report.append("\n| Backend | Monthly Cost | Cost/1M Queries | Storage Cost/GB |")
        report.append("|---------|--------------|-----------------|-----------------|")

        for backend_key, result in sorted(results.items()):
            cost = result.cost
            if cost:
                monthly = f"${cost.monthly_cost_estimate:.2f}"
                per_million = f"${cost.cost_per_million_queries:.2f}"
                storage = f"${cost.storage_cost_per_gb:.3f}"
            else:
                monthly = per_million = storage = "N/A"

            report.append(f"| {backend_key} | {monthly} | {per_million} | {storage} |")

        # Memory efficiency
        report.append("\n## Memory & Storage Efficiency")
        report.append("\n| Backend | Bytes/Vector | Overhead % | Compression Ratio |")
        report.append("|---------|--------------|------------|-------------------|")

        for backend_key, result in sorted(results.items()):
            memory = result.memory
            storage = result.storage

            bytes_per_vec = f"{memory.bytes_per_vector:.1f}" if memory else "N/A"
            overhead = f"{memory.overhead_percentage:.1f}%" if memory else "N/A"
            compression = f"{storage.compression_ratio:.2f}x" if storage else "N/A"

            report.append(f"| {backend_key} | {bytes_per_vec} | {overhead} | {compression} |")

        # Scaling characteristics
        report.append("\n## Scaling Characteristics")
        report.append("\n| Backend | Scaling Efficiency | Cold Start | Concurrent QPS |")
        report.append("|---------|-------------------|------------|----------------|")

        for backend_key, result in sorted(results.items()):
            scaling = result.scaling
            cold_start = result.cold_start
            concurrent = result.concurrent_load

            efficiency = f"{scaling.scaling_efficiency:.1%}" if scaling else "N/A"
            cold = f"{cold_start.cold_start_ms:.1f}ms" if cold_start else "N/A"
            conc_qps = f"{concurrent.total_qps:.1f}" if concurrent else "N/A"

            report.append(f"| {backend_key} | {efficiency} | {cold} | {conc_qps} |")

        # Summary recommendations
        report.append("\n## Key Findings")
        report.append("\n### Best Performance")
        if results:
            # Find best latency
            best_latency = min(
                (r for r in results.values() if r.latency),
                key=lambda r: r.latency.p50_ms,
                default=None
            )
            if best_latency:
                backend = [k for k, v in results.items() if v == best_latency][0]
                report.append(f"- **Lowest Latency**: {backend} ({best_latency.latency.p50_ms:.2f}ms p50)")

            # Find best throughput
            best_qps = max(
                (r for r in results.values() if r.throughput),
                key=lambda r: r.throughput.qps,
                default=None
            )
            if best_qps:
                backend = [k for k, v in results.items() if v == best_qps][0]
                report.append(f"- **Highest Throughput**: {backend} ({best_qps.throughput.qps:.1f} QPS)")

            # Find lowest cost
            best_cost = min(
                (r for r in results.values() if r.cost),
                key=lambda r: r.cost.monthly_cost_estimate,
                default=None
            )
            if best_cost:
                backend = [k for k, v in results.items() if v == best_cost][0]
                report.append(f"- **Lowest Cost**: {backend} (${best_cost.cost.monthly_cost_estimate:.2f}/month)")

        return "\n".join(report)

    def save_comparison_report(self, report: str, filename: str = "benchmark_report.md"):
        """Save comparison report to markdown file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            f.write(report)
        logger.info(f"Saved comparison report to {filepath}")


async def main():
    """Example usage of comprehensive benchmark runner"""
    runner = ComprehensiveBenchmarkRunner(output_dir=Path('./benchmark_results'))

    # Run Tier 1 benchmarks only (7 core backends)
    benchmark_config = {
        'dimensions': 1024,
        'vector_count': 10000,
        'query_count': 100,
        'enabled_dimensions': [
            'latency', 'throughput', 'recall', 'indexing',
            'memory', 'cost', 'storage'
        ],
        'max_concurrent_backends': 2
    }

    results = await runner.run_all_benchmarks(
        tier_filter=1,  # Only Tier 1
        benchmark_config=benchmark_config
    )

    # Generate and save report
    report = runner.generate_comparison_report(results)
    runner.save_comparison_report(report)

    print(f"\n{report}")


if __name__ == '__main__':
    asyncio.run(main())
