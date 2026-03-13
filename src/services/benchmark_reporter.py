"""
Benchmark Report Generator

Generates comprehensive markdown reports with comparison matrices,
performance analysis, and cost-performance rankings.

Implements reporting requirements from VECTORDB_RESEARCH.md section 10.5.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from src.services.benchmark_storage import BenchmarkStorage

logger = logging.getLogger(__name__)


class BenchmarkReporter:
    """
    Generates comprehensive benchmark reports in markdown format.

    Reports include:
    - Executive summary with winner/leader per dimension
    - Performance comparison matrix (all 10 dimensions)
    - Cost-performance analysis
    - Use case recommendations
    - Detailed per-variant breakdown
    """

    def __init__(self, storage: BenchmarkStorage):
        self.storage = storage

    def format_latency(self, ms: float) -> str:
        """Format latency value"""
        if ms < 1:
            return f"{ms*1000:.0f}μs"
        elif ms < 1000:
            return f"{ms:.2f}ms"
        else:
            return f"{ms/1000:.2f}s"

    def format_cost(self, usd: float) -> str:
        """Format cost value"""
        if usd < 1:
            return f"${usd:.2f}"
        elif usd < 100:
            return f"${usd:.0f}"
        else:
            return f"${usd:,.0f}"

    def format_bytes(self, bytes_val: float) -> str:
        """Format bytes value"""
        if bytes_val < 1024:
            return f"{bytes_val:.0f}B"
        elif bytes_val < 1024**2:
            return f"{bytes_val/1024:.1f}KB"
        elif bytes_val < 1024**3:
            return f"{bytes_val/(1024**2):.1f}MB"
        else:
            return f"{bytes_val/(1024**3):.2f}GB"

    def generate_executive_summary(self, results: Dict[str, List[Dict]]) -> str:
        """Generate executive summary section"""
        lines = [
            "## Executive Summary\n",
            "This report presents comprehensive benchmark results across all tested vector database variants. ",
            "Each variant was evaluated on 10 key performance dimensions.\n",
        ]

        # Count variants per tier
        tier_counts = {"Tier 1": 0, "Tier 2": 0, "Tier 3": 0}
        for variant_name in results.keys():
            # Simple tier detection based on name
            if any(x in variant_name for x in ["s3vector", "qdrant-ecs", "lancedb", "pgvector-rds"]):
                tier_counts["Tier 1"] += 1
            elif any(x in variant_name for x in ["opensearch-serverless", "qdrant-cloud", "faiss-embedded"]):
                tier_counts["Tier 2"] += 1
            else:
                tier_counts["Tier 3"] += 1

        lines.append(f"\n**Variants Tested:** {len(results)} total across {sum(1 for c in tier_counts.values() if c > 0)} tiers\n")
        for tier, count in tier_counts.items():
            if count > 0:
                lines.append(f"- {tier}: {count} variants\n")

        # Find leaders in each dimension
        leaders = self._find_dimension_leaders(results)

        lines.append("\n### Performance Leaders\n")
        lines.append("| Dimension | Winner | Value |\n")
        lines.append("|-----------|--------|-------|\n")

        dimension_labels = {
            "latency_p50_ms": ("Lowest Latency (P50)", self.format_latency),
            "throughput_qps": ("Highest Throughput", lambda x: f"{x:.1f} QPS"),
            "recall_at_10": ("Best Accuracy (Recall@10)", lambda x: f"{x*100:.1f}%"),
            "index_throughput_vectors_per_sec": ("Fastest Indexing", lambda x: f"{x:.0f} v/s"),
            "memory_per_vector_bytes": ("Most Memory Efficient", self.format_bytes),
            "cost_per_million_queries_usd": ("Lowest Cost", lambda x: f"${x:.2f}/1M"),
            "cold_start_time_sec": ("Fastest Cold Start", lambda x: f"{x:.2f}s"),
            "concurrent_qps": ("Best Concurrent Load", lambda x: f"{x:.1f} QPS"),
            "storage_per_vector_bytes": ("Most Storage Efficient", self.format_bytes)
        }

        for metric, (label, formatter) in dimension_labels.items():
            if metric in leaders and leaders[metric]:
                variant, value = leaders[metric]
                formatted_value = formatter(value) if value is not None else "N/A"
                lines.append(f"| {label} | **{variant}** | {formatted_value} |\n")

        return "".join(lines)

    def _find_dimension_leaders(self, results: Dict[str, List[Dict]]) -> Dict[str, tuple]:
        """
        Find the best variant for each dimension.

        Returns:
            Dictionary mapping metric names to (variant, value) tuples
        """
        leaders = {}

        # Define metrics and whether higher is better
        metrics_config = {
            "latency_p50_ms": False,  # Lower is better
            "throughput_qps": True,
            "recall_at_10": True,
            "index_throughput_vectors_per_sec": True,
            "memory_per_vector_bytes": False,
            "cost_per_million_queries_usd": False,
            "cold_start_time_sec": False,
            "concurrent_qps": True,
            "storage_per_vector_bytes": False
        }

        for metric, higher_is_better in metrics_config.items():
            best_variant = None
            best_value = float('-inf') if higher_is_better else float('inf')

            for variant_name, variant_results in results.items():
                # Get mean value across all runs
                values = [r.get(metric) for r in variant_results if r.get(metric) is not None]
                if not values:
                    continue

                mean_value = sum(values) / len(values)

                if higher_is_better:
                    if mean_value > best_value:
                        best_value = mean_value
                        best_variant = variant_name
                else:
                    if mean_value < best_value:
                        best_value = mean_value
                        best_variant = variant_name

            if best_variant:
                leaders[metric] = (best_variant, best_value)

        return leaders

    def generate_comparison_matrix(self, results: Dict[str, List[Dict]]) -> str:
        """Generate performance comparison matrix"""
        lines = [
            "\n## Performance Comparison Matrix\n",
            "\nAll metrics shown are averages across tested vector counts.\n",
            "\n### Latency & Throughput\n",
            "\n| Variant | P50 Latency | P95 Latency | P99 Latency | Throughput (QPS) | Concurrent QPS |\n",
            "|---------|-------------|-------------|-------------|------------------|----------------|\n"
        ]

        for variant_name, variant_results in sorted(results.items()):
            # Calculate averages
            p50 = self._avg_metric(variant_results, "latency_p50_ms")
            p95 = self._avg_metric(variant_results, "latency_p95_ms")
            p99 = self._avg_metric(variant_results, "latency_p99_ms")
            qps = self._avg_metric(variant_results, "throughput_qps")
            concurrent = self._avg_metric(variant_results, "concurrent_qps")

            lines.append(
                f"| {variant_name} | {self.format_latency(p50) if p50 else 'N/A'} | "
                f"{self.format_latency(p95) if p95 else 'N/A'} | "
                f"{self.format_latency(p99) if p99 else 'N/A'} | "
                f"{qps:.1f} | {concurrent:.1f if concurrent else 'N/A'} |\n"
            )

        # Accuracy section
        lines.append("\n### Accuracy (Recall@k)\n")
        lines.append("\n| Variant | Recall@10 | Recall@50 | Recall@100 |\n")
        lines.append("|---------|-----------|-----------|------------|\n")

        for variant_name, variant_results in sorted(results.items()):
            r10 = self._avg_metric(variant_results, "recall_at_10")
            r50 = self._avg_metric(variant_results, "recall_at_50")
            r100 = self._avg_metric(variant_results, "recall_at_100")

            lines.append(
                f"| {variant_name} | "
                f"{r10*100:.1f}% " if r10 else "N/A | "
                f"{r50*100:.1f}% " if r50 else "N/A | "
                f"{r100*100:.1f}% " if r100 else "N/A |\n"
            )

        # Indexing & Resource Efficiency
        lines.append("\n### Indexing & Resource Efficiency\n")
        lines.append("\n| Variant | Index Speed (v/s) | Memory/Vector | Storage/Vector | Cold Start |\n")
        lines.append("|---------|-------------------|---------------|----------------|------------|\n")

        for variant_name, variant_results in sorted(results.items()):
            index_speed = self._avg_metric(variant_results, "index_throughput_vectors_per_sec")
            mem_per_vec = self._avg_metric(variant_results, "memory_per_vector_bytes")
            storage_per_vec = self._avg_metric(variant_results, "storage_per_vector_bytes")
            cold_start = self._avg_metric(variant_results, "cold_start_time_sec")

            lines.append(
                f"| {variant_name} | "
                f"{index_speed:.0f} | " if index_speed else "N/A | "
                f"{self.format_bytes(mem_per_vec)} | " if mem_per_vec else "N/A | "
                f"{self.format_bytes(storage_per_vec)} | " if storage_per_vec else "N/A | "
                f"{cold_start:.2f}s" if cold_start else "N/A |\n"
            )

        return "".join(lines)

    def _avg_metric(self, results: List[Dict], metric: str) -> Optional[float]:
        """Calculate average value for a metric"""
        values = [r.get(metric) for r in results if r.get(metric) is not None]
        return sum(values) / len(values) if values else None

    def generate_cost_analysis(self, results: Dict[str, List[Dict]]) -> str:
        """Generate cost-performance analysis"""
        lines = [
            "\n## Cost-Performance Analysis\n",
            "\n| Variant | Monthly Cost | Cost/1M Queries | QPS/$ | Cost Rank |\n",
            "|---------|--------------|-----------------|-------|----------|\n"
        ]

        # Collect cost data
        cost_data = []
        for variant_name, variant_results in results.items():
            monthly_cost = self._avg_metric(variant_results, "infrastructure_cost_monthly_usd")
            cost_per_million = self._avg_metric(variant_results, "cost_per_million_queries_usd")
            qps = self._avg_metric(variant_results, "throughput_qps")

            if monthly_cost is not None and qps is not None and monthly_cost > 0:
                qps_per_dollar = qps / monthly_cost
                cost_data.append({
                    "variant": variant_name,
                    "monthly_cost": monthly_cost,
                    "cost_per_million": cost_per_million,
                    "qps_per_dollar": qps_per_dollar
                })

        # Sort by QPS per dollar (best value)
        cost_data.sort(key=lambda x: x["qps_per_dollar"], reverse=True)

        for rank, data in enumerate(cost_data, 1):
            lines.append(
                f"| {data['variant']} | "
                f"{self.format_cost(data['monthly_cost'])} | "
                f"{self.format_cost(data['cost_per_million']) if data['cost_per_million'] else 'N/A'} | "
                f"{data['qps_per_dollar']:.2f} | "
                f"#{rank} |\n"
            )

        # Cost tiers
        lines.append("\n### Cost Tiers\n")
        lines.append("\n| Tier | Cost Range | Variants |\n")
        lines.append("|------|------------|----------|\n")

        tiers = [
            ("Ultra-Low", (0, 10), []),
            ("Low", (10, 100), []),
            ("Medium", (100, 300), []),
            ("High", (300, 700), []),
            ("Premium", (700, float('inf')), [])
        ]

        for variant_name, variant_results in results.items():
            monthly_cost = self._avg_metric(variant_results, "infrastructure_cost_monthly_usd")
            if monthly_cost is not None:
                for tier_name, (min_cost, max_cost), variants in tiers:
                    if min_cost <= monthly_cost < max_cost:
                        variants.append(variant_name)
                        break

        for tier_name, (min_cost, max_cost), variants in tiers:
            if variants:
                cost_range = f"${min_cost}-${max_cost}" if max_cost != float('inf') else f"${min_cost}+"
                variant_list = ", ".join(variants)
                lines.append(f"| **{tier_name}** | {cost_range} | {variant_list} |\n")

        return "".join(lines)

    def generate_use_case_recommendations(self, results: Dict[str, List[Dict]]) -> str:
        """Generate use case recommendations"""
        lines = [
            "\n## Use Case Recommendations\n",
            "\nBased on benchmark results, here are the recommended variants for common use cases:\n"
        ]

        leaders = self._find_dimension_leaders(results)

        # Define use cases
        use_cases = [
            {
                "name": "Real-time Search (Low Latency)",
                "metric": "latency_p50_ms",
                "description": "Applications requiring sub-10ms query response times"
            },
            {
                "name": "High Throughput",
                "metric": "throughput_qps",
                "description": "Systems handling thousands of queries per second"
            },
            {
                "name": "Cost-Optimized",
                "metric": "cost_per_million_queries_usd",
                "description": "Budget-constrained deployments prioritizing cost efficiency"
            },
            {
                "name": "High Accuracy",
                "metric": "recall_at_10",
                "description": "Applications where search quality is paramount"
            },
            {
                "name": "Fast Indexing",
                "metric": "index_throughput_vectors_per_sec",
                "description": "Scenarios with frequent data updates and bulk ingestion"
            },
            {
                "name": "Serverless/Auto-scaling",
                "metric": "cold_start_time_sec",
                "description": "Variable workloads requiring quick cold starts"
            }
        ]

        lines.append("\n| Use Case | Recommended Variant | Key Metric | Notes |\n")
        lines.append("|----------|---------------------|------------|-------|\n")

        for use_case in use_cases:
            metric = use_case["metric"]
            if metric in leaders:
                variant, value = leaders[metric]

                # Format value
                if "latency" in metric:
                    formatted = self.format_latency(value)
                elif "throughput" in metric or "qps" in metric:
                    formatted = f"{value:.1f} QPS"
                elif "cost" in metric:
                    formatted = self.format_cost(value)
                elif "recall" in metric:
                    formatted = f"{value*100:.1f}%"
                elif "time" in metric:
                    formatted = f"{value:.2f}s"
                else:
                    formatted = f"{value:.1f}"

                lines.append(
                    f"| **{use_case['name']}** | {variant} | {formatted} | {use_case['description']} |\n"
                )

        return "".join(lines)

    def generate_detailed_breakdown(self, results: Dict[str, List[Dict]]) -> str:
        """Generate detailed per-variant breakdown"""
        lines = ["\n## Detailed Variant Breakdown\n"]

        for variant_name, variant_results in sorted(results.items()):
            lines.append(f"\n### {variant_name}\n")

            # Show results at each scale
            lines.append("\n| Vector Count | P50 Latency | QPS | Recall@10 | Index Time |\n")
            lines.append("|--------------|-------------|-----|-----------|------------|\n")

            for result in variant_results:
                vector_count = result.get("vectors_tested", 0)
                p50 = result.get("latency_p50_ms")
                qps = result.get("throughput_qps")
                recall = result.get("recall_at_10")
                index_time = result.get("index_build_time_sec")

                lines.append(
                    f"| {vector_count:,} | "
                    f"{self.format_latency(p50) if p50 else 'N/A'} | "
                    f"{qps:.1f} | " if qps else "N/A | "
                    f"{recall*100:.1f}% | " if recall else "N/A | "
                    f"{index_time:.1f}s" if index_time else "N/A |\n"
                )

        return "".join(lines)

    def generate_comprehensive_report(
        self,
        session_id: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate complete comprehensive benchmark report.

        Args:
            session_id: Session to report on (default: latest)
            output_path: Path to save markdown file

        Returns:
            Markdown report content
        """
        if not session_id:
            session_id = self.storage.get_latest_session()

        if not session_id:
            logger.error("No benchmark sessions found")
            return ""

        logger.info(f"Generating comprehensive report for session {session_id}")

        # Load results
        results = self.storage.load_session_results(session_id)

        if not results:
            logger.error(f"No results found for session {session_id}")
            return ""

        # Generate report sections
        report_lines = [
            f"# Comprehensive Vector Database Benchmark Report\n",
            f"\n**Session:** {session_id}\n",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
            f"**Variants Tested:** {len(results)}\n",
            "\n---\n"
        ]

        report_lines.append(self.generate_executive_summary(results))
        report_lines.append(self.generate_comparison_matrix(results))
        report_lines.append(self.generate_cost_analysis(results))
        report_lines.append(self.generate_use_case_recommendations(results))
        report_lines.append(self.generate_detailed_breakdown(results))

        # Footer
        report_lines.append("\n---\n")
        report_lines.append("\n## Methodology\n")
        report_lines.append("\nBenchmarks conducted using the comprehensive suite implementing 10 dimensions:\n")
        report_lines.append("1. Query Latency (P50/P95/P99/P999)\n")
        report_lines.append("2. Throughput (QPS sustained)\n")
        report_lines.append("3. Recall@k (accuracy against ground truth)\n")
        report_lines.append("4. Indexing Speed (vectors/second)\n")
        report_lines.append("5. Memory Efficiency (bytes per vector)\n")
        report_lines.append("6. Cost per Query ($/million)\n")
        report_lines.append("7. Scaling (performance degradation)\n")
        report_lines.append("8. Cold Start (initialization time)\n")
        report_lines.append("9. Concurrent Load (multi-client QPS)\n")
        report_lines.append("10. Storage Efficiency (index overhead)\n")
        report_lines.append("\n" + "="*80 + "\n")
        report_lines.append("*Generated by S3Vector Comprehensive Benchmark Suite*\n")

        report_content = "".join(report_lines)

        # Save to file if requested
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report_content)
            logger.info(f"Report saved to {output_path}")

        return report_content
