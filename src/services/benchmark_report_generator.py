"""
Benchmark Report Generator.

Generates markdown reports and comparison tables from benchmark results.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from src.services.benchmark_models import (
    ComprehensiveBenchmarkResult,
    BenchmarkComparison
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BenchmarkReportGenerator:
    """
    Generates comprehensive benchmark reports in various formats.
    """

    def generate_markdown_report(
        self,
        comparison: BenchmarkComparison
    ) -> str:
        """
        Generate a comprehensive markdown report from benchmark comparison.
        """
        report = []

        # Header
        report.append("# Vector Database Benchmark Results")
        report.append(f"\n**Generated:** {comparison.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**Job ID:** {comparison.job_id}")
        report.append(f"**Backends Tested:** {', '.join(comparison.backends)}\n")
        report.append("---\n")

        # Executive Summary
        report.append("## Executive Summary\n")

        best_latency = comparison.get_best_by_latency()
        best_throughput = comparison.get_best_by_throughput()
        best_cost = comparison.get_best_by_cost()

        if best_latency:
            report.append(f"**Lowest Latency (P99):** {best_latency.backend}/{best_latency.variant} - {best_latency.latency.p99_ms:.2f}ms")
        if best_throughput:
            report.append(f"**Highest Throughput:** {best_throughput.backend}/{best_throughput.variant} - {best_throughput.throughput.qps:.0f} QPS")
        if best_cost:
            report.append(f"**Best Cost Efficiency:** {best_cost.backend}/{best_cost.variant} - ${best_cost.cost.monthly_cost_estimate_usd:.2f}/month")

        report.append("\n---\n")

        # Performance Comparison Table
        report.append("## Performance Comparison\n")
        report.append(self._generate_performance_table(comparison.results))
        report.append("\n")

        # Cost Comparison Table
        report.append("## Cost Analysis\n")
        report.append(self._generate_cost_table(comparison.results))
        report.append("\n")

        # Scaling Performance
        report.append("## Scaling Performance\n")
        report.append(self._generate_scaling_section(comparison.results))
        report.append("\n")

        # Detailed Results
        report.append("## Detailed Results\n")
        for result in comparison.results:
            report.append(self._generate_detailed_result_section(result))
            report.append("\n")

        # Recommendations
        report.append("## Recommendations\n")
        report.append(self._generate_recommendations(comparison))
        report.append("\n")

        return "\n".join(report)

    def _generate_performance_table(
        self,
        results: List[ComprehensiveBenchmarkResult]
    ) -> str:
        """Generate markdown table for performance metrics"""
        lines = []
        lines.append("| Backend | Variant | P50 (ms) | P99 (ms) | QPS | Recall@10 | Index Speed (v/s) |")
        lines.append("|---------|---------|----------|----------|-----|-----------|-------------------|")

        for result in results:
            backend = result.backend
            variant = result.variant
            p50 = f"{result.latency.p50_ms:.2f}" if result.latency else "N/A"
            p99 = f"{result.latency.p99_ms:.2f}" if result.latency else "N/A"
            qps = f"{result.throughput.qps:.0f}" if result.throughput else "N/A"
            recall = f"{result.recall.recall_at_10:.2%}" if result.recall else "N/A"
            index_speed = f"{result.indexing.vectors_per_second:.0f}" if result.indexing else "N/A"

            lines.append(f"| {backend} | {variant} | {p50} | {p99} | {qps} | {recall} | {index_speed} |")

        return "\n".join(lines)

    def _generate_cost_table(
        self,
        results: List[ComprehensiveBenchmarkResult]
    ) -> str:
        """Generate markdown table for cost metrics"""
        lines = []
        lines.append("| Backend | Variant | Monthly Cost | Cost/Query | Cost/1K Queries | QPS/$ |")
        lines.append("|---------|---------|--------------|------------|-----------------|-------|")

        for result in results:
            if not result.cost or not result.throughput:
                continue

            backend = result.backend
            variant = result.variant
            monthly = f"${result.cost.monthly_cost_estimate_usd:.2f}"
            per_query = f"${result.cost.cost_per_query_usd:.6f}"
            per_1k = f"${result.cost.cost_per_1k_queries_usd:.4f}"

            # Calculate QPS per dollar
            qps_per_dollar = result.throughput.qps / result.cost.monthly_cost_estimate_usd if result.cost.monthly_cost_estimate_usd > 0 else 0
            qps_dollar = f"{qps_per_dollar:.1f}"

            lines.append(f"| {backend} | {variant} | {monthly} | {per_query} | {per_1k} | {qps_dollar} |")

        return "\n".join(lines)

    def _generate_scaling_section(
        self,
        results: List[ComprehensiveBenchmarkResult]
    ) -> str:
        """Generate scaling performance section"""
        lines = []

        for result in results:
            if not result.scaling:
                continue

            lines.append(f"### {result.backend}/{result.variant}\n")
            lines.append("| Dataset Size | P99 Latency (ms) | QPS | Indexing Time (s) |")
            lines.append("|--------------|------------------|-----|-------------------|")

            for size in result.scaling.dataset_sizes:
                p99 = result.scaling.latency_p99_by_size.get(size, 0)
                qps = result.scaling.qps_by_size.get(size, 0)
                index_time = result.scaling.indexing_time_by_size.get(size, 0)

                lines.append(f"| {size:,} | {p99:.2f} | {qps:.0f} | {index_time:.1f} |")

            lines.append("\n")

        return "\n".join(lines)

    def _generate_detailed_result_section(
        self,
        result: ComprehensiveBenchmarkResult
    ) -> str:
        """Generate detailed section for a single result"""
        lines = []
        lines.append(f"### {result.backend}/{result.variant}\n")

        # Configuration
        lines.append(f"**Configuration:**")
        lines.append(f"- Vector Count: {result.vector_count:,}")
        lines.append(f"- Dimension: {result.vector_dimension}")
        lines.append(f"- Test Duration: {result.test_duration_seconds:.1f}s")
        lines.append(f"- Status: {result.status.value}\n")

        # Latency
        if result.latency:
            lines.append("**Latency:**")
            lines.append(f"- P50: {result.latency.p50_ms:.2f}ms")
            lines.append(f"- P95: {result.latency.p95_ms:.2f}ms")
            lines.append(f"- P99: {result.latency.p99_ms:.2f}ms")
            lines.append(f"- Mean: {result.latency.mean_ms:.2f}ms ± {result.latency.std_ms:.2f}ms")
            lines.append(f"- Range: {result.latency.min_ms:.2f}ms - {result.latency.max_ms:.2f}ms\n")

        # Throughput
        if result.throughput:
            lines.append("**Throughput:**")
            lines.append(f"- QPS: {result.throughput.qps:.0f}")
            lines.append(f"- Sustained QPS: {result.throughput.sustained_qps:.0f}")
            lines.append(f"- Peak QPS: {result.throughput.peak_qps:.0f}")
            lines.append(f"- Total Queries: {result.throughput.total_queries:,}")
            lines.append(f"- Error Rate: {result.throughput.error_rate:.2%}\n")

        # Recall
        if result.recall:
            lines.append("**Recall:**")
            lines.append(f"- Recall@10: {result.recall.recall_at_10:.2%}")
            lines.append(f"- Test Queries: {result.recall.test_queries}")
            lines.append(f"- Ground Truth: {result.recall.ground_truth_count}\n")

        # Indexing
        if result.indexing:
            lines.append("**Indexing:**")
            lines.append(f"- Speed: {result.indexing.vectors_per_second:.0f} vectors/second")
            lines.append(f"- Total Vectors: {result.indexing.total_vectors:,}")
            lines.append(f"- Duration: {result.indexing.duration_seconds:.1f}s")
            if result.indexing.memory_peak_mb:
                lines.append(f"- Peak Memory: {result.indexing.memory_peak_mb:.0f}MB\n")

        # Memory
        if result.memory:
            lines.append("**Memory Efficiency:**")
            lines.append(f"- Bytes per Vector: {result.memory.bytes_per_vector:.0f}")
            lines.append(f"- Total Memory: {result.memory.total_memory_mb:.0f}MB")
            lines.append(f"- Index Overhead: {result.memory.index_overhead_ratio:.1%}")
            lines.append(f"- Peak Memory: {result.memory.peak_memory_mb:.0f}MB\n")

        # Cost
        if result.cost:
            lines.append("**Cost:**")
            lines.append(f"- Monthly Estimate: ${result.cost.monthly_cost_estimate_usd:.2f}")
            lines.append(f"- Cost per Query: ${result.cost.cost_per_query_usd:.6f}")
            lines.append(f"- Cost per 1K Queries: ${result.cost.cost_per_1k_queries_usd:.4f}")
            lines.append(f"- Storage Cost: ${result.cost.storage_cost_per_month_usd:.2f}/month")
            if result.cost.compute_cost_per_hour_usd:
                lines.append(f"- Compute Cost: ${result.cost.compute_cost_per_hour_usd:.4f}/hour\n")

        # Concurrent Load
        if result.concurrent_load:
            lines.append("**Concurrent Load:**")
            lines.append(f"- Clients: {result.concurrent_load.concurrent_clients}")
            lines.append(f"- Total Requests: {result.concurrent_load.total_requests:,}")
            lines.append(f"- Successful: {result.concurrent_load.successful_requests:,}")
            lines.append(f"- Failed: {result.concurrent_load.failed_requests}")
            lines.append(f"- P99 Latency: {result.concurrent_load.latency_p99_ms:.2f}ms")
            lines.append(f"- Throughput: {result.concurrent_load.throughput_qps:.0f} QPS")
            lines.append(f"- Error Rate: {result.concurrent_load.error_rate:.2%}\n")

        # Storage Efficiency
        if result.storage_efficiency:
            lines.append("**Storage Efficiency:**")
            lines.append(f"- Raw Size: {result.storage_efficiency.raw_vector_size_bytes / 1024 / 1024:.0f}MB")
            lines.append(f"- Stored Size: {result.storage_efficiency.stored_size_bytes / 1024 / 1024:.0f}MB")
            lines.append(f"- Index Size: {result.storage_efficiency.index_size_bytes / 1024 / 1024:.0f}MB")
            lines.append(f"- Overhead: {result.storage_efficiency.overhead_percentage:.1f}%\n")

        return "\n".join(lines)

    def _generate_recommendations(
        self,
        comparison: BenchmarkComparison
    ) -> str:
        """Generate recommendations based on benchmark results"""
        lines = []

        best_latency = comparison.get_best_by_latency()
        best_throughput = comparison.get_best_by_throughput()
        best_cost = comparison.get_best_by_cost()

        # Best for latency-sensitive applications
        if best_latency:
            lines.append("### For Latency-Sensitive Applications")
            lines.append(f"**Recommended:** {best_latency.backend}/{best_latency.variant}")
            lines.append(f"- P99 Latency: {best_latency.latency.p99_ms:.2f}ms")
            if best_latency.cost:
                lines.append(f"- Monthly Cost: ${best_latency.cost.monthly_cost_estimate_usd:.2f}")
            lines.append("")

        # Best for high-throughput applications
        if best_throughput:
            lines.append("### For High-Throughput Applications")
            lines.append(f"**Recommended:** {best_throughput.backend}/{best_throughput.variant}")
            lines.append(f"- Throughput: {best_throughput.throughput.qps:.0f} QPS")
            if best_throughput.cost:
                lines.append(f"- Monthly Cost: ${best_throughput.cost.monthly_cost_estimate_usd:.2f}")
            lines.append("")

        # Best for cost-sensitive deployments
        if best_cost:
            lines.append("### For Cost-Sensitive Deployments")
            lines.append(f"**Recommended:** {best_cost.backend}/{best_cost.variant}")
            lines.append(f"- Monthly Cost: ${best_cost.cost.monthly_cost_estimate_usd:.2f}")
            if best_cost.throughput:
                lines.append(f"- Throughput: {best_cost.throughput.qps:.0f} QPS")
            lines.append("")

        # Best overall (balanced)
        lines.append("### Best Overall (Balanced Performance/Cost)")

        # Calculate cost-performance ratio for all results
        ratios = []
        for result in comparison.results:
            ratio = comparison.get_cost_performance_ratio(result)
            if ratio:
                ratios.append((result, ratio))

        if ratios:
            best_overall = max(ratios, key=lambda x: x[1])
            result, ratio = best_overall
            lines.append(f"**Recommended:** {result.backend}/{result.variant}")
            lines.append(f"- QPS per $: {ratio:.1f}")
            if result.latency:
                lines.append(f"- P99 Latency: {result.latency.p99_ms:.2f}ms")
            if result.cost:
                lines.append(f"- Monthly Cost: ${result.cost.monthly_cost_estimate_usd:.2f}")

        return "\n".join(lines)

    def generate_json_report(
        self,
        comparison: BenchmarkComparison
    ) -> Dict[str, Any]:
        """
        Generate a JSON report from benchmark comparison.
        """
        return comparison.to_dict()

    def generate_csv_export(
        self,
        results: List[ComprehensiveBenchmarkResult]
    ) -> str:
        """
        Generate CSV export of benchmark results.
        """
        lines = []

        # Header
        header = [
            "Backend",
            "Variant",
            "Vector Count",
            "Dimension",
            "P50 Latency (ms)",
            "P99 Latency (ms)",
            "QPS",
            "Recall@10",
            "Index Speed (v/s)",
            "Monthly Cost ($)",
            "Cost/Query ($)",
            "Memory/Vector (bytes)",
            "Storage Overhead (%)"
        ]
        lines.append(",".join(header))

        # Data rows
        for result in results:
            row = [
                result.backend,
                result.variant,
                str(result.vector_count),
                str(result.vector_dimension),
                f"{result.latency.p50_ms:.2f}" if result.latency else "",
                f"{result.latency.p99_ms:.2f}" if result.latency else "",
                f"{result.throughput.qps:.0f}" if result.throughput else "",
                f"{result.recall.recall_at_10:.4f}" if result.recall else "",
                f"{result.indexing.vectors_per_second:.0f}" if result.indexing else "",
                f"{result.cost.monthly_cost_estimate_usd:.2f}" if result.cost else "",
                f"{result.cost.cost_per_query_usd:.8f}" if result.cost else "",
                f"{result.memory.bytes_per_vector:.0f}" if result.memory else "",
                f"{result.storage_efficiency.overhead_percentage:.1f}" if result.storage_efficiency else ""
            ]
            lines.append(",".join(row))

        return "\n".join(lines)
