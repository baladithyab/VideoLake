"""
Parallel Vector Store Comparison Service

Queries multiple vector stores simultaneously and collects performance metrics
for real-time comparison. Enables demo to showcase differences between:
- S3Vector (direct)
- OpenSearch (with S3Vector backend)
- Qdrant
- LanceDB (EFS/EBS/S3 backends)

This replaces the need for dedicated benchmark infrastructure by integrating
metrics collection directly into query execution.
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.services.vector_store_s3vector_provider import S3VectorProvider
from src.services.vector_store_opensearch_provider import OpenSearchProvider
from src.services.vector_store_qdrant_provider import QdrantProvider
from src.services.vector_store_lancedb_provider import LanceDBProvider
from src.exceptions import VectorStorageError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class VectorStoreType(Enum):
    """Supported vector store types."""
    S3VECTOR = "s3vector"
    OPENSEARCH = "opensearch"
    QDRANT = "qdrant"
    LANCEDB = "lancedb"


@dataclass
class QueryMetrics:
    """Performance metrics for a single query operation."""
    vector_store: str
    query_latency_ms: float
    result_count: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None

    # Detailed metrics
    connection_time_ms: Optional[float] = None
    search_time_ms: Optional[float] = None
    post_processing_time_ms: Optional[float] = None

    # Cost estimation (if available)
    estimated_cost_usd: Optional[float] = None

    @property
    def latency_category(self) -> str:
        """Categorize latency for easy comparison."""
        if self.query_latency_ms < 50:
            return "fast"
        elif self.query_latency_ms < 200:
            return "medium"
        else:
            return "slow"


@dataclass
class ComparisonResult:
    """Results from parallel vector store comparison."""
    query_vector: List[float]
    top_k: int
    filters: Optional[Dict[str, Any]]

    # Results by vector store
    metrics: Dict[str, QueryMetrics] = field(default_factory=dict)
    results: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # Aggregate statistics
    total_stores_queried: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    fastest_store: Optional[str] = None
    slowest_store: Optional[str] = None
    avg_latency_ms: Optional[float] = None

    def compute_statistics(self) -> None:
        """Compute aggregate statistics from metrics."""
        self.total_stores_queried = len(self.metrics)
        self.successful_queries = sum(1 for m in self.metrics.values() if m.success)
        self.failed_queries = self.total_stores_queried - self.successful_queries

        # Find fastest and slowest
        successful_metrics = [(store, m) for store, m in self.metrics.items() if m.success]

        if successful_metrics:
            fastest = min(successful_metrics, key=lambda x: x[1].query_latency_ms)
            slowest = max(successful_metrics, key=lambda x: x[1].query_latency_ms)

            self.fastest_store = fastest[0]
            self.slowest_store = slowest[0]

            # Compute average latency
            latencies = [m.query_latency_ms for _, m in successful_metrics]
            self.avg_latency_ms = sum(latencies) / len(latencies) if latencies else None

    def get_ranking(self) -> List[Tuple[str, float]]:
        """Get vector stores ranked by query latency."""
        successful = [(store, m.query_latency_ms) for store, m in self.metrics.items() if m.success]
        return sorted(successful, key=lambda x: x[1])

    def get_summary_table(self) -> Dict[str, Any]:
        """Get summary table for display."""
        return {
            'query_summary': {
                'total_stores': self.total_stores_queried,
                'successful': self.successful_queries,
                'failed': self.failed_queries,
                'avg_latency_ms': round(self.avg_latency_ms, 2) if self.avg_latency_ms else None
            },
            'performance_ranking': self.get_ranking(),
            'fastest_store': {
                'name': self.fastest_store,
                'latency_ms': round(self.metrics[self.fastest_store].query_latency_ms, 2) if self.fastest_store else None
            } if self.fastest_store else None,
            'slowest_store': {
                'name': self.slowest_store,
                'latency_ms': round(self.metrics[self.slowest_store].query_latency_ms, 2) if self.slowest_store else None
            } if self.slowest_store else None
        }


class ParallelVectorStoreComparison:
    """
    Parallel query execution across multiple vector stores with metrics collection.

    Enables real-time comparison in the demo by querying all configured
    vector stores simultaneously and collecting performance metrics.

    Example:
        comparison = ParallelVectorStoreComparison(
            enabled_stores=['s3vector', 'opensearch', 'qdrant', 'lancedb']
        )

        result = comparison.query_all_stores(
            query_vector=[0.1, 0.2, ...],  # From Marengo or Nova
            index_name="demo-videos",
            top_k=10
        )

        # Shows real-time metrics:
        # - S3Vector: 45ms, 10 results
        # - OpenSearch: 120ms, 10 results
        # - Qdrant: 35ms, 10 results
        # - LanceDB: 67ms, 10 results
    """

    def __init__(
        self,
        enabled_stores: Optional[List[str]] = None,
        max_workers: int = 4
    ):
        """
        Initialize parallel comparison service.

        Args:
            enabled_stores: Which stores to query (default: all)
            max_workers: Max parallel queries
        """
        self.enabled_stores = enabled_stores or ['s3vector', 'opensearch', 'qdrant', 'lancedb']
        self.max_workers = max_workers

        # Initialize providers for enabled stores
        self.providers = self._initialize_providers()

        logger.info(
            f"Initialized parallel comparison for stores: {list(self.providers.keys())}"
        )

    def _initialize_providers(self) -> Dict[str, Any]:
        """Initialize vector store providers."""
        providers = {}

        if 's3vector' in self.enabled_stores:
            try:
                providers['s3vector'] = S3VectorProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize S3Vector provider: {e}")

        if 'opensearch' in self.enabled_stores:
            try:
                providers['opensearch'] = OpenSearchProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenSearch provider: {e}")

        if 'qdrant' in self.enabled_stores:
            try:
                providers['qdrant'] = QdrantProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Qdrant provider: {e}")

        if 'lancedb' in self.enabled_stores:
            try:
                providers['lancedb'] = LanceDBProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize LanceDB provider: {e}")

        return providers

    def query_all_stores(
        self,
        query_vector: List[float],
        index_name: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        timeout_sec: int = 30
    ) -> ComparisonResult:
        """
        Query all enabled vector stores in parallel and collect metrics.

        Args:
            query_vector: Query embedding vector
            index_name: Index/collection name to query
            top_k: Number of results to return
            filters: Optional metadata filters
            timeout_sec: Query timeout per store

        Returns:
            ComparisonResult with metrics and results from all stores
        """
        comparison_result = ComparisonResult(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters
        )

        # Execute queries in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            for store_name, provider in self.providers.items():
                future = executor.submit(
                    self._query_single_store,
                    store_name=store_name,
                    provider=provider,
                    query_vector=query_vector,
                    index_name=index_name,
                    top_k=top_k,
                    filters=filters,
                    timeout_sec=timeout_sec
                )
                futures[future] = store_name

            # Collect results as they complete
            for future in as_completed(futures, timeout=timeout_sec + 5):
                store_name = futures[future]
                try:
                    metrics, results = future.result()
                    comparison_result.metrics[store_name] = metrics
                    comparison_result.results[store_name] = results

                except Exception as e:
                    logger.error(f"Query failed for {store_name}: {str(e)}")
                    comparison_result.metrics[store_name] = QueryMetrics(
                        vector_store=store_name,
                        query_latency_ms=0,
                        result_count=0,
                        timestamp=datetime.utcnow(),
                        success=False,
                        error_message=str(e)
                    )

        # Compute aggregate statistics
        comparison_result.compute_statistics()

        logger.info(
            f"Parallel query complete: {comparison_result.successful_queries}/"
            f"{comparison_result.total_stores_queried} successful, "
            f"fastest={comparison_result.fastest_store}, "
            f"avg_latency={comparison_result.avg_latency_ms}ms"
        )

        return comparison_result

    def _query_single_store(
        self,
        store_name: str,
        provider: Any,
        query_vector: List[float],
        index_name: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
        timeout_sec: int
    ) -> Tuple[QueryMetrics, List[Dict[str, Any]]]:
        """Query a single vector store and collect metrics."""
        start_time = time.time()

        try:
            # Execute query based on provider type
            if store_name == 's3vector':
                results = provider.query(
                    index_arn=index_name,  # May need to convert index_name to ARN
                    query_vector=query_vector,
                    top_k=top_k,
                    metadata_filters=filters
                )

            elif store_name == 'opensearch':
                results = provider.query(
                    index_name=index_name,
                    query_vector=query_vector,
                    top_k=top_k,
                    filters=filters
                )

            elif store_name == 'qdrant':
                results = provider.query(
                    collection_name=index_name,
                    query_vector=query_vector,
                    top_k=top_k,
                    filters=filters
                )

            elif store_name == 'lancedb':
                results = provider.query(
                    table_name=index_name,
                    query_vector=query_vector,
                    top_k=top_k,
                    filters=filters
                )

            else:
                raise ValueError(f"Unknown vector store: {store_name}")

            query_latency_ms = (time.time() - start_time) * 1000

            metrics = QueryMetrics(
                vector_store=store_name,
                query_latency_ms=query_latency_ms,
                result_count=len(results) if results else 0,
                timestamp=datetime.utcnow(),
                success=True,
                search_time_ms=query_latency_ms  # Simplified
            )

            return metrics, results

        except Exception as e:
            query_latency_ms = (time.time() - start_time) * 1000

            metrics = QueryMetrics(
                vector_store=store_name,
                query_latency_ms=query_latency_ms,
                result_count=0,
                timestamp=datetime.utcnow(),
                success=False,
                error_message=str(e)
            )

            return metrics, []

    def generate_comparison_report(
        self,
        comparison_result: ComparisonResult
    ) -> str:
        """
        Generate markdown comparison report.

        Args:
            comparison_result: Results from parallel query

        Returns:
            Markdown formatted comparison report
        """
        report = []
        report.append("# Vector Store Performance Comparison\n")
        report.append(f"**Query Time**: {datetime.utcnow().isoformat()}\n")
        report.append(f"**Query Dimension**: {len(comparison_result.query_vector)}D\n")
        report.append(f"**Top K**: {comparison_result.top_k}\n\n")

        # Summary table
        report.append("## Summary\n")
        report.append("| Metric | Value |\n")
        report.append("|--------|-------|\n")
        report.append(f"| Stores Queried | {comparison_result.total_stores_queried} |\n")
        report.append(f"| Successful | {comparison_result.successful_queries} |\n")
        report.append(f"| Failed | {comparison_result.failed_queries} |\n")
        report.append(f"| Avg Latency | {round(comparison_result.avg_latency_ms, 2) if comparison_result.avg_latency_ms else 'N/A'} ms |\n")
        report.append(f"| Fastest Store | {comparison_result.fastest_store or 'N/A'} |\n\n")

        # Performance ranking
        report.append("## Performance Ranking\n")
        report.append("| Rank | Vector Store | Latency (ms) | Results | Status |\n")
        report.append("|------|-------------|--------------|---------|--------|\n")

        ranking = comparison_result.get_ranking()
        for rank, (store, latency) in enumerate(ranking, 1):
            metrics = comparison_result.metrics[store]
            report.append(
                f"| {rank} | **{store.upper()}** | {round(latency, 2)} | "
                f"{metrics.result_count} | ✅ |\n"
            )

        # Failed queries
        failed = [(store, m) for store, m in comparison_result.metrics.items() if not m.success]
        if failed:
            report.append("\n### Failed Queries\n")
            for store, metrics in failed:
                report.append(f"- **{store.upper()}**: {metrics.error_message}\n")

        # Detailed metrics
        report.append("\n## Detailed Metrics\n")
        for store, metrics in comparison_result.metrics.items():
            if metrics.success:
                report.append(f"\n### {store.upper()}\n")
                report.append(f"- **Latency**: {round(metrics.query_latency_ms, 2)}ms\n")
                report.append(f"- **Category**: {metrics.latency_category}\n")
                report.append(f"- **Results**: {metrics.result_count}\n")
                if metrics.estimated_cost_usd:
                    report.append(f"- **Est. Cost**: ${metrics.estimated_cost_usd:.6f}\n")

        return ''.join(report)
