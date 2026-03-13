"""
S3Vector Benchmark Suite

Comprehensive benchmarking system for vector database comparison across 12-15 variants.

Key Components:
- BenchmarkConfig: Configuration for benchmark runs
- BenchmarkRunner: Orchestrates benchmark execution
- BenchmarkResult: Structured results with all 10 dimensions
- Comparison tools: Generate reports and visualizations

Supported Dimensions:
1. Latency (p50/p95/p99/p999)
2. Throughput (sustained QPS)
3. Recall@K (accuracy)
4. Indexing Speed (vectors/sec)
5. Memory Efficiency (bytes/vector)
6. Cost-per-query ($/1M queries)
7. Scaling (performance at scale)
8. Cold Start (serverless init)
9. Concurrent Load (multi-client)
10. Storage Efficiency (index overhead)
"""

from src.benchmarks.benchmark_config import (
    BenchmarkConfig,
    BenchmarkResult,
    DimensionResult,
    DatasetConfig,
    BackendVariant,
    QUICK_CONFIG,
    STANDARD_CONFIG,
    COMPREHENSIVE_CONFIG,
)

from src.benchmarks.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkOrchestrator,
)

__all__ = [
    # Configuration
    'BenchmarkConfig',
    'BenchmarkResult',
    'DimensionResult',
    'DatasetConfig',
    'BackendVariant',

    # Presets
    'QUICK_CONFIG',
    'STANDARD_CONFIG',
    'COMPREHENSIVE_CONFIG',

    # Execution
    'BenchmarkRunner',
    'BenchmarkOrchestrator',
]

__version__ = '1.0.0'
