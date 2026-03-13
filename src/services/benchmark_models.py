"""
Benchmark data models for comprehensive vector store testing.

Defines all benchmark dimensions, result structures, and comparison models
for the S3Vector benchmark suite.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import json


class BenchmarkStatus(str, Enum):
    """Status of a benchmark job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BenchmarkDimension(str, Enum):
    """10 comprehensive benchmark dimensions"""
    LATENCY = "latency"  # p50/p95/p99 query latency
    THROUGHPUT = "throughput"  # queries per second
    RECALL = "recall"  # recall@k accuracy vs ground truth
    INDEXING_SPEED = "indexing_speed"  # vectors/second during indexing
    MEMORY_EFFICIENCY = "memory_efficiency"  # memory usage per vector
    COST_PER_QUERY = "cost_per_query"  # estimated cost per query operation
    SCALING = "scaling"  # performance at different dataset sizes
    COLD_START = "cold_start"  # time to first query (serverless)
    CONCURRENT_LOAD = "concurrent_load"  # performance under concurrent requests
    STORAGE_EFFICIENCY = "storage_efficiency"  # bytes per vector (index overhead)


@dataclass
class LatencyMetrics:
    """Latency measurements in milliseconds"""
    p50_ms: float
    p95_ms: float
    p99_ms: float
    p999_ms: Optional[float] = None
    min_ms: float = 0.0
    max_ms: float = 0.0
    mean_ms: float = 0.0
    std_ms: float = 0.0


@dataclass
class ThroughputMetrics:
    """Throughput measurements"""
    qps: float  # queries per second
    sustained_qps: float  # sustained over test duration
    peak_qps: float  # maximum observed
    total_queries: int
    duration_seconds: float
    error_rate: float = 0.0  # percentage of failed queries


@dataclass
class RecallMetrics:
    """Recall accuracy measurements"""
    recall_at_10: float  # recall@10
    recall_at_50: Optional[float] = None  # recall@50
    recall_at_100: Optional[float] = None  # recall@100
    ground_truth_count: int = 0
    test_queries: int = 0


@dataclass
class IndexingMetrics:
    """Indexing performance measurements"""
    vectors_per_second: float
    total_vectors: int
    duration_seconds: float
    batch_size: int
    memory_peak_mb: Optional[float] = None
    cpu_utilization: Optional[float] = None


@dataclass
class MemoryMetrics:
    """Memory efficiency measurements"""
    bytes_per_vector: float
    total_memory_mb: float
    index_overhead_ratio: float  # (total_memory - raw_vectors) / raw_vectors
    peak_memory_mb: float
    vector_count: int


@dataclass
class CostMetrics:
    """Cost analysis per operation"""
    cost_per_query_usd: float
    cost_per_1k_queries_usd: float
    monthly_cost_estimate_usd: float  # at 10K queries/day
    storage_cost_per_month_usd: float
    compute_cost_per_hour_usd: Optional[float] = None


@dataclass
class ScalingMetrics:
    """Performance across different dataset sizes"""
    dataset_sizes: List[int]  # [1K, 10K, 100K, 1M]
    latency_p99_by_size: Dict[int, float]  # {size: p99_ms}
    qps_by_size: Dict[int, float]  # {size: qps}
    indexing_time_by_size: Dict[int, float]  # {size: seconds}


@dataclass
class ColdStartMetrics:
    """Cold start measurements (serverless only)"""
    cold_start_time_ms: float
    warm_start_time_ms: float
    initialization_overhead_ms: float
    first_query_latency_ms: float


@dataclass
class ConcurrentLoadMetrics:
    """Performance under concurrent load"""
    concurrent_clients: int
    total_requests: int
    successful_requests: int
    failed_requests: int
    latency_p99_ms: float
    throughput_qps: float
    error_rate: float


@dataclass
class StorageEfficiencyMetrics:
    """Storage utilization measurements"""
    raw_vector_size_bytes: int
    stored_size_bytes: int
    index_size_bytes: int
    overhead_percentage: float
    compression_ratio: Optional[float] = None


@dataclass
class ComprehensiveBenchmarkResult:
    """
    Complete benchmark results for a single vector store variant.
    Contains all 10 benchmark dimensions.
    """
    # Metadata
    backend: str
    variant: str  # e.g., "ecs-efs", "serverless", "s3"
    job_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Configuration
    vector_count: int = 0
    vector_dimension: int = 1536
    test_duration_seconds: float = 0.0

    # 10 Benchmark Dimensions
    latency: Optional[LatencyMetrics] = None
    throughput: Optional[ThroughputMetrics] = None
    recall: Optional[RecallMetrics] = None
    indexing: Optional[IndexingMetrics] = None
    memory: Optional[MemoryMetrics] = None
    cost: Optional[CostMetrics] = None
    scaling: Optional[ScalingMetrics] = None
    cold_start: Optional[ColdStartMetrics] = None
    concurrent_load: Optional[ConcurrentLoadMetrics] = None
    storage_efficiency: Optional[StorageEfficiencyMetrics] = None

    # Overall status
    status: BenchmarkStatus = BenchmarkStatus.PENDING
    error_message: Optional[str] = None

    # Raw data
    raw_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime to ISO string
        result['timestamp'] = self.timestamp.isoformat()
        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class BenchmarkComparison:
    """
    Comparison of multiple benchmark results across backends.
    Used for generating comparison tables and visualizations.
    """
    job_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    backends: List[str] = field(default_factory=list)
    results: List[ComprehensiveBenchmarkResult] = field(default_factory=list)

    # Comparison summaries
    winner_by_dimension: Dict[str, str] = field(default_factory=dict)  # {dimension: backend}
    cost_performance_ranking: List[Dict[str, Any]] = field(default_factory=list)

    def add_result(self, result: ComprehensiveBenchmarkResult):
        """Add a benchmark result to the comparison"""
        self.results.append(result)
        if result.backend not in self.backends:
            self.backends.append(result.backend)

    def get_best_by_latency(self) -> Optional[ComprehensiveBenchmarkResult]:
        """Get the result with lowest p99 latency"""
        valid_results = [r for r in self.results if r.latency is not None]
        if not valid_results:
            return None
        return min(valid_results, key=lambda r: r.latency.p99_ms)

    def get_best_by_throughput(self) -> Optional[ComprehensiveBenchmarkResult]:
        """Get the result with highest QPS"""
        valid_results = [r for r in self.results if r.throughput is not None]
        if not valid_results:
            return None
        return max(valid_results, key=lambda r: r.throughput.qps)

    def get_best_by_cost(self) -> Optional[ComprehensiveBenchmarkResult]:
        """Get the result with lowest cost per query"""
        valid_results = [r for r in self.results if r.cost is not None]
        if not valid_results:
            return None
        return min(valid_results, key=lambda r: r.cost.cost_per_query_usd)

    def get_cost_performance_ratio(self, result: ComprehensiveBenchmarkResult) -> Optional[float]:
        """Calculate QPS per dollar per month"""
        if not result.throughput or not result.cost:
            return None
        if result.cost.monthly_cost_estimate_usd == 0:
            return float('inf')
        return result.throughput.qps / result.cost.monthly_cost_estimate_usd

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'timestamp': self.timestamp.isoformat(),
            'backends': self.backends,
            'results': [r.to_dict() for r in self.results],
            'winner_by_dimension': self.winner_by_dimension,
            'cost_performance_ranking': self.cost_performance_ranking
        }


@dataclass
class BenchmarkConfiguration:
    """Configuration for running comprehensive benchmarks"""
    # Test parameters
    vector_counts: List[int] = field(default_factory=lambda: [1000, 10000, 100000])
    vector_dimension: int = 1536
    query_count: int = 1000
    top_k: int = 10
    concurrent_clients: int = 10
    test_duration_seconds: int = 300  # 5 minutes

    # Test modes
    enable_recall_testing: bool = True
    enable_cold_start_testing: bool = True
    enable_concurrent_load_testing: bool = True
    enable_scaling_testing: bool = True
    enable_memory_profiling: bool = True

    # Cost assumptions (for estimation)
    queries_per_day: int = 10000
    days_per_month: int = 30

    # Backends to test
    backends: List[str] = field(default_factory=list)

    # Storage configuration
    results_bucket: Optional[str] = None
    results_table: Optional[str] = None  # DynamoDB table for results

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
