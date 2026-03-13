"""
Benchmark Configuration Models

Defines configuration structures for benchmark runs including:
- Backend variants and tiers
- Dataset configurations
- Benchmark dimensions to measure
- Result storage models
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class BackendVariant(str, Enum):
    """Supported vector database backend variants"""
    # Tier 1: Must include (7 variants)
    S3VECTOR_SERVERLESS = "s3vector-serverless"
    QDRANT_ECS_EFS = "qdrant-ecs-efs"
    LANCEDB_EBS = "lancedb-ebs"
    LANCEDB_S3_REMOTE = "lancedb-s3-remote-api"
    OPENSEARCH_PROVISIONED = "opensearch-provisioned-hnsw"
    PGVECTOR_AURORA_SERVERLESS = "pgvector-aurora-serverless"
    PGVECTOR_RDS = "pgvector-rds-postgresql"

    # Tier 2: Should include (5 variants)
    PGVECTOR_AURORA_IVFFLAT = "pgvector-aurora-ivfflat"
    OPENSEARCH_SERVERLESS = "opensearch-serverless"
    QDRANT_CLOUD = "qdrant-cloud-managed"
    FAISS_EMBEDDED = "faiss-embedded"
    ZILLIZ_CLOUD = "zilliz-cloud"

    # Tier 3: Optional (3 variants)
    FAISS_LAMBDA = "faiss-lambda"
    FAISS_EC2_GPU = "faiss-ec2-gpu"
    OPENSEARCH_ALGORITHM_COMPARISON = "opensearch-algorithm-comparison"


class BenchmarkDimension(str, Enum):
    """10 benchmark dimensions"""
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    RECALL = "recall"
    INDEXING_SPEED = "indexing_speed"
    MEMORY_EFFICIENCY = "memory_efficiency"
    COST_PER_QUERY = "cost_per_query"
    SCALING = "scaling"
    COLD_START = "cold_start"
    CONCURRENT_LOAD = "concurrent_load"
    STORAGE_EFFICIENCY = "storage_efficiency"


@dataclass
class DatasetConfig:
    """Dataset configuration for benchmarking"""
    name: str
    vector_count: int
    dimensions: int
    similarity_metric: str = "cosine"  # cosine, euclidean, dot_product

    # For real datasets (optional)
    source: Optional[str] = None  # e.g., "huggingface:msmarco"
    description: Optional[str] = None


@dataclass
class DimensionResult:
    """Results for a single benchmark dimension"""
    dimension: BenchmarkDimension
    value: Any  # Primary metric value
    unit: str  # Unit of measurement
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Complete benchmark results for a single backend"""
    backend: BackendVariant
    timestamp: datetime
    dataset: DatasetConfig

    # 10 Dimension results
    latency: Optional[DimensionResult] = None
    throughput: Optional[DimensionResult] = None
    recall: Optional[DimensionResult] = None
    indexing_speed: Optional[DimensionResult] = None
    memory_efficiency: Optional[DimensionResult] = None
    cost_per_query: Optional[DimensionResult] = None
    scaling: Optional[DimensionResult] = None
    cold_start: Optional[DimensionResult] = None
    concurrent_load: Optional[DimensionResult] = None
    storage_efficiency: Optional[DimensionResult] = None

    # Overall metadata
    duration_seconds: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_dimension_result(self, dimension: BenchmarkDimension) -> Optional[DimensionResult]:
        """Get result for a specific dimension"""
        return getattr(self, dimension.value, None)

    def set_dimension_result(self, result: DimensionResult):
        """Set result for a dimension"""
        setattr(self, result.dimension.value, result)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'backend': self.backend.value,
            'timestamp': self.timestamp.isoformat(),
            'dataset': {
                'name': self.dataset.name,
                'vector_count': self.dataset.vector_count,
                'dimensions': self.dataset.dimensions,
                'similarity_metric': self.dataset.similarity_metric,
            },
            'dimensions': {
                dim.value: {
                    'value': getattr(self, dim.value).value if getattr(self, dim.value) else None,
                    'unit': getattr(self, dim.value).unit if getattr(self, dim.value) else None,
                    'metadata': getattr(self, dim.value).metadata if getattr(self, dim.value) else {},
                    'success': getattr(self, dim.value).success if getattr(self, dim.value) else False,
                }
                for dim in BenchmarkDimension
            },
            'duration_seconds': self.duration_seconds,
            'success': self.success,
            'error_message': self.error_message,
            'metadata': self.metadata,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of key metrics"""
        summary = {
            'backend': self.backend.value,
            'timestamp': self.timestamp.isoformat(),
        }

        # Add key metrics
        if self.latency:
            summary['latency_p50_ms'] = self.latency.metadata.get('p50_ms')
            summary['latency_p99_ms'] = self.latency.metadata.get('p99_ms')
        if self.throughput:
            summary['qps'] = self.throughput.value
        if self.recall:
            summary['recall_at_k'] = self.recall.value
        if self.cost_per_query:
            summary['monthly_cost'] = self.cost_per_query.metadata.get('monthly_cost_estimate')

        return summary


@dataclass
class BenchmarkConfig:
    """
    Configuration for a benchmark run

    Defines what to benchmark, how to benchmark it, and where to store results.
    """
    # Backends to benchmark
    backends: List[BackendVariant] = field(default_factory=list)

    # Dataset configuration
    dataset: DatasetConfig = field(default_factory=lambda: DatasetConfig(
        name="synthetic",
        vector_count=10000,
        dimensions=1024,
        similarity_metric="cosine"
    ))

    # Which dimensions to measure
    enabled_dimensions: List[BenchmarkDimension] = field(default_factory=lambda: [
        BenchmarkDimension.LATENCY,
        BenchmarkDimension.THROUGHPUT,
        BenchmarkDimension.RECALL,
        BenchmarkDimension.INDEXING_SPEED,
        BenchmarkDimension.MEMORY_EFFICIENCY,
        BenchmarkDimension.COST_PER_QUERY,
        BenchmarkDimension.SCALING,
        BenchmarkDimension.COLD_START,
        BenchmarkDimension.CONCURRENT_LOAD,
        BenchmarkDimension.STORAGE_EFFICIENCY,
    ])

    # Benchmark parameters
    query_count: int = 100  # For latency measurement
    throughput_duration_seconds: int = 60  # For sustained QPS
    recall_sample_count: int = 100  # For recall@k evaluation
    top_k: int = 10  # Results to retrieve per query
    concurrent_clients: int = 10  # For concurrent load testing

    # Scaling test parameters
    scaling_vector_counts: List[int] = field(default_factory=lambda: [1000, 5000, 10000, 50000])

    # Execution parameters
    max_concurrent_backends: int = 3  # Max backends to test in parallel
    timeout_seconds: int = 3600  # Per-backend timeout

    # Output configuration
    output_dir: str = "./benchmark_results"
    save_raw_results: bool = True
    generate_report: bool = True

    # Additional metadata
    run_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate run_id if not provided"""
        if not self.run_id:
            self.run_id = f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def get_tier_1_backends(self) -> List[BackendVariant]:
        """Get Tier 1 backends from config"""
        tier_1 = [
            BackendVariant.S3VECTOR_SERVERLESS,
            BackendVariant.QDRANT_ECS_EFS,
            BackendVariant.LANCEDB_EBS,
            BackendVariant.LANCEDB_S3_REMOTE,
            BackendVariant.OPENSEARCH_PROVISIONED,
            BackendVariant.PGVECTOR_AURORA_SERVERLESS,
            BackendVariant.PGVECTOR_RDS,
        ]
        return [b for b in self.backends if b in tier_1]

    def get_tier_2_backends(self) -> List[BackendVariant]:
        """Get Tier 2 backends from config"""
        tier_2 = [
            BackendVariant.PGVECTOR_AURORA_IVFFLAT,
            BackendVariant.OPENSEARCH_SERVERLESS,
            BackendVariant.QDRANT_CLOUD,
            BackendVariant.FAISS_EMBEDDED,
            BackendVariant.ZILLIZ_CLOUD,
        ]
        return [b for b in self.backends if b in tier_2]

    def get_tier_3_backends(self) -> List[BackendVariant]:
        """Get Tier 3 backends from config"""
        tier_3 = [
            BackendVariant.FAISS_LAMBDA,
            BackendVariant.FAISS_EC2_GPU,
            BackendVariant.OPENSEARCH_ALGORITHM_COMPARISON,
        ]
        return [b for b in self.backends if b in tier_3]


# Preset configurations

QUICK_CONFIG = BenchmarkConfig(
    backends=[
        BackendVariant.S3VECTOR_SERVERLESS,
        BackendVariant.QDRANT_ECS_EFS,
        BackendVariant.LANCEDB_EBS,
    ],
    dataset=DatasetConfig(
        name="quick_test",
        vector_count=1000,
        dimensions=512,
    ),
    query_count=50,
    throughput_duration_seconds=30,
    recall_sample_count=50,
    enabled_dimensions=[
        BenchmarkDimension.LATENCY,
        BenchmarkDimension.THROUGHPUT,
        BenchmarkDimension.RECALL,
    ],
    description="Quick validation benchmark (3 backends, 1K vectors, 3 dimensions)"
)

STANDARD_CONFIG = BenchmarkConfig(
    backends=[
        BackendVariant.S3VECTOR_SERVERLESS,
        BackendVariant.QDRANT_ECS_EFS,
        BackendVariant.LANCEDB_EBS,
        BackendVariant.LANCEDB_S3_REMOTE,
        BackendVariant.OPENSEARCH_PROVISIONED,
        BackendVariant.PGVECTOR_AURORA_SERVERLESS,
        BackendVariant.PGVECTOR_RDS,
    ],
    dataset=DatasetConfig(
        name="standard_benchmark",
        vector_count=10000,
        dimensions=1024,
    ),
    query_count=100,
    throughput_duration_seconds=60,
    recall_sample_count=100,
    enabled_dimensions=[
        BenchmarkDimension.LATENCY,
        BenchmarkDimension.THROUGHPUT,
        BenchmarkDimension.RECALL,
        BenchmarkDimension.INDEXING_SPEED,
        BenchmarkDimension.MEMORY_EFFICIENCY,
        BenchmarkDimension.COST_PER_QUERY,
        BenchmarkDimension.STORAGE_EFFICIENCY,
    ],
    description="Standard benchmark (Tier 1: 7 backends, 10K vectors, 7 dimensions)"
)

COMPREHENSIVE_CONFIG = BenchmarkConfig(
    backends=[
        # Tier 1
        BackendVariant.S3VECTOR_SERVERLESS,
        BackendVariant.QDRANT_ECS_EFS,
        BackendVariant.LANCEDB_EBS,
        BackendVariant.LANCEDB_S3_REMOTE,
        BackendVariant.OPENSEARCH_PROVISIONED,
        BackendVariant.PGVECTOR_AURORA_SERVERLESS,
        BackendVariant.PGVECTOR_RDS,
        # Tier 2
        BackendVariant.PGVECTOR_AURORA_IVFFLAT,
        BackendVariant.OPENSEARCH_SERVERLESS,
        BackendVariant.QDRANT_CLOUD,
        BackendVariant.FAISS_EMBEDDED,
        BackendVariant.ZILLIZ_CLOUD,
    ],
    dataset=DatasetConfig(
        name="comprehensive_benchmark",
        vector_count=50000,
        dimensions=1536,
    ),
    query_count=200,
    throughput_duration_seconds=120,
    recall_sample_count=200,
    concurrent_clients=20,
    scaling_vector_counts=[1000, 5000, 10000, 50000, 100000],
    enabled_dimensions=list(BenchmarkDimension),  # All 10 dimensions
    description="Comprehensive benchmark (Tiers 1+2: 12 backends, 50K vectors, all 10 dimensions)"
)
