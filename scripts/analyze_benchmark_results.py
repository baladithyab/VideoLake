#!/usr/bin/env python3
"""
Benchmark Results Analysis Script

Analyzes benchmark results from multiple backends and modalities, generating
comprehensive comparison reports, summary statistics, and identifying outliers.

Usage:
    python3 scripts/analyze_benchmark_results.py <results_directory>
    python3 scripts/analyze_benchmark_results.py benchmark-results/session_20231117_123456
    python3 scripts/analyze_benchmark_results.py benchmark-results/session_20231117_123456 --output report.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import statistics

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BenchmarkMetrics:
    """Container for benchmark metrics"""
    backend: str
    modality: str
    query_count: int
    successful_queries: int
    duration_seconds: float
    throughput_qps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_min_ms: float
    latency_max_ms: float
    latency_mean_ms: float
    latency_std_ms: float
    success: bool = True
    error: Optional[str] = None


@dataclass
class BackendSummary:
    """Summary statistics for a backend across all modalities"""
    backend: str
    total_queries: int = 0
    successful_queries: int = 0
    avg_throughput_qps: float = 0.0
    avg_latency_p50_ms: float = 0.0
    avg_latency_p95_ms: float = 0.0
    avg_latency_p99_ms: float = 0.0
    modality_results: Dict[str, BenchmarkMetrics] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_queries == 0:
            return 0.0
        return (self.successful_queries / self.total_queries) * 100


class BenchmarkAnalyzer:
    """Analyzer for benchmark results"""
    
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.metrics: List[BenchmarkMetrics] = []
        self.backend_summaries: Dict[str, BackendSummary] = {}
        
    def load_results(self) -> bool:
        """Load all JSON result files from the directory"""
        logger.info(f"Loading results from: {self.results_dir}")
        
        if not self.results_dir.exists():
            logger.error(f"Results directory does not exist: {self.results_dir}")
            return False
        
        if not self.results_dir.is_dir():
            logger.error(f"Path is not a directory: {self.results_dir}")
            return False
        
        # Find all JSON files (excluding metadata.json)
        json_files = [f for f in self.results_dir.glob("*.json") if f.name != "metadata.json"]
        
        if not json_files:
            logger.error(f"No JSON result files found in: {self.results_dir}")
            return False
        
        logger.info(f"Found {len(json_files)} result files")
        
        # Load each file
        loaded_count = 0
        for json_file in json_files:
            try:
                metrics = self._load_single_result(json_file)
                if metrics:
                    self.metrics.append(metrics)
                    loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load {json_file.name}: {e}")
        
        logger.info(f"Successfully loaded {loaded_count}/{len(json_files)} result files")
        return loaded_count > 0
    
    def _load_single_result(self, json_file: Path) -> Optional[BenchmarkMetrics]:
        """Load and parse a single result file"""
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Extract backend and modality from filename
        # Expected format: ccopen_<backend>_<modality>_search.json
        parts = json_file.stem.split('_')
        if len(parts) < 4:
            logger.warning(f"Unexpected filename format: {json_file.name}")
            return None
        
        # Handle backend names with hyphens (e.g., qdrant-ebs)
        backend = '_'.join(parts[1:-2])  # Everything between ccopen and modality
        modality = parts[-2]  # Second to last part
        
        # Check if benchmark was successful
        if not data.get("success", False):
            logger.warning(f"Benchmark failed for {backend}/{modality}: {data.get('error', 'Unknown error')}")
            return BenchmarkMetrics(
                backend=backend,
                modality=modality,
                query_count=data.get("query_count", 0),
                successful_queries=0,
                duration_seconds=data.get("duration_seconds", 0),
                throughput_qps=0,
                latency_p50_ms=0,
                latency_p95_ms=0,
                latency_p99_ms=0,
                latency_min_ms=0,
                latency_max_ms=0,
                latency_mean_ms=0,
                latency_std_ms=0,
                success=False,
                error=data.get("error")
            )
        
        # Extract metrics
        return BenchmarkMetrics(
            backend=backend,
            modality=modality,
            query_count=data.get("query_count", 0),
            successful_queries=data.get("successful_queries", 0),
            duration_seconds=data.get("duration_seconds", 0),
            throughput_qps=data.get("throughput_qps", 0),
            latency_p50_ms=data.get("latency_p50_ms", 0),
            latency_p95_ms=data.get("latency_p95_ms", 0),
            latency_p99_ms=data.get("latency_p99_ms", 0),
            latency_min_ms=data.get("latency_min_ms", 0),
            latency_max_ms=data.get("latency_max_ms", 0),
            latency_mean_ms=data.get("latency_mean_ms", 0),
            latency_std_ms=data.get("latency_std_ms", 0)
        )
    
    def calculate_summaries(self) -> None:
        """Calculate summary statistics per backend"""
        logger.info("Calculating backend summaries...")
        
        # Group metrics by backend
        backend_metrics: Dict[str, List[BenchmarkMetrics]] = {}
        for metric in self.metrics:
            if metric.backend not in backend_metrics:
                backend_metrics[metric.backend] = []
            backend_metrics[metric.backend].append(metric)
        
        # Calculate summaries
        for backend, metrics_list in backend_metrics.items():
            summary = BackendSummary(backend=backend)
            
            # Aggregate metrics
            throughputs = []
            p50_latencies = []
            p95_latencies = []
            p99_latencies = []
            
            for metric in metrics_list:
                summary.total_queries += metric.query_count
                summary.successful_queries += metric.successful_queries
                summary.modality_results[metric.modality] = metric
                
                if metric.success and metric.throughput_qps > 0:
                    throughputs.append(metric.throughput_qps)
                    p50_latencies.append(metric.latency_p50_ms)
                    p95_latencies.append(metric.latency_p95_ms)
                    p99_latencies.append(metric.latency_p99_ms)
            
            # Calculate averages
            if throughputs:
                summary.avg_throughput_qps = statistics.mean(throughputs)
                summary.avg_latency_p50_ms = statistics.mean(p50_latencies)
                summary.avg_latency_p95_ms = statistics.mean(p95_latencies)
                summary.avg_latency_p99_ms = statistics.mean(p99_latencies)
            
            self.backend_summaries[backend] = summary
        
        logger.info(f"Calculated summaries for {len(self.backend_summaries)} backends")
    
    def identify_outliers(self) -> Dict[str, List[str]]:
        """Identify performance outliers"""
        logger.info("Identifying performance outliers...")
        
        # Collect all throughput and latency values
        all_throughputs = [m.throughput_qps for m in self.metrics if m.success]
        all_p95_latencies = [m.latency_p95_ms for m in self.metrics if m.success]
        
        if not all_throughputs or not all_p95_latencies:
            return {}
        
        # Calculate statistics
        mean_throughput = statistics.mean(all_throughputs)
        stdev_throughput = statistics.stdev(all_throughputs) if len(all_throughputs) > 1 else 0
        
        mean_latency = statistics.mean(all_p95_latencies)
        stdev_latency = statistics.stdev(all_p95_latencies) if len(all_p95_latencies) > 1 else 0
        
        outliers = {
            "high_performers": [],
            "low_performers": [],
            "high_latency": [],
            "low_latency": []
        }
        
        # Identify outliers (2 standard deviations)
        for metric in self.metrics:
            if not metric.success:
                continue
            
            backend_modality = f"{metric.backend}/{metric.modality}"
            
            # Throughput outliers
            if stdev_throughput > 0:
                if metric.throughput_qps > mean_throughput + 2 * stdev_throughput:
                    outliers["high_performers"].append(backend_modality)
                elif metric.throughput_qps < mean_throughput - 2 * stdev_throughput:
                    outliers["low_performers"].append(backend_modality)
            
            # Latency outliers
            if stdev_latency > 0:
                if metric.latency_p95_ms > mean_latency + 2 * stdev_latency:
                    outliers["high_latency"].append(backend_modality)
                elif metric.latency_p95_ms < mean_latency - 2 * stdev_latency:
                    outliers["low_latency"].append(backend_modality)
        
        return outliers
    
    def generate_markdown_report(self, output_file: Path) -> None:
        """Generate comprehensive markdown report"""
        logger.info(f"Generating markdown report: {output_file}")
        
        with open(output_file, 'w') as f:
            # Header
            f.write("# Benchmark Results Analysis Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Results Directory:** `{self.results_dir}`\n\n")
            f.write(f"**Total Benchmarks:** {len(self.metrics)}\n\n")
            f.write("---\n\n")
            
            # Executive Summary
            f.write("## Executive Summary\n\n")
            self._write_executive_summary(f)
            
            # Backend Comparison Table
            f.write("## Backend Comparison\n\n")
            self._write_backend_comparison_table(f)
            
            # Detailed Results by Backend
            f.write("## Detailed Results by Backend\n\n")
            self._write_detailed_results(f)
            
            # Performance Outliers
            f.write("## Performance Outliers\n\n")
            self._write_outliers_section(f)
            
            # Recommendations
            f.write("## Recommendations\n\n")
            self._write_recommendations(f)
        
        logger.info(f"Markdown report saved to: {output_file}")
    
    def _write_executive_summary(self, f) -> None:
        """Write executive summary section"""
        # Find best performers
        if not self.backend_summaries:
            f.write("*No successful benchmarks to summarize.*\n\n")
            return
        
        # Best throughput
        best_throughput = max(
            self.backend_summaries.values(),
            key=lambda s: s.avg_throughput_qps
        )
        
        # Best latency
        best_latency = min(
            self.backend_summaries.values(),
            key=lambda s: s.avg_latency_p95_ms if s.avg_latency_p95_ms > 0 else float('inf')
        )
        
        f.write(f"- **Best Throughput:** {best_throughput.backend} ")
        f.write(f"({best_throughput.avg_throughput_qps:.2f} queries/sec)\n")
        
        f.write(f"- **Best Latency (P95):** {best_latency.backend} ")
        f.write(f"({best_latency.avg_latency_p95_ms:.2f} ms)\n")
        
        # Overall success rate
        total_queries = sum(s.total_queries for s in self.backend_summaries.values())
        successful_queries = sum(s.successful_queries for s in self.backend_summaries.values())
        success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
        
        f.write(f"- **Overall Success Rate:** {success_rate:.1f}% ")
        f.write(f"({successful_queries}/{total_queries} queries)\n\n")
    
    def _write_backend_comparison_table(self, f) -> None:
        """Write backend comparison table"""
        f.write("### Average Performance Metrics\n\n")
        
        # Table header
        f.write("| Backend | Throughput (QPS) | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Success Rate |\n")
        f.write("|---------|------------------|------------------|------------------|------------------|-------------|\n")
        
        # Sort by throughput (descending)
        sorted_backends = sorted(
            self.backend_summaries.values(),
            key=lambda s: s.avg_throughput_qps,
            reverse=True
        )
        
        for summary in sorted_backends:
            f.write(f"| {summary.backend} ")
            f.write(f"| {summary.avg_throughput_qps:.2f} ")
            f.write(f"| {summary.avg_latency_p50_ms:.2f} ")
            f.write(f"| {summary.avg_latency_p95_ms:.2f} ")
            f.write(f"| {summary.avg_latency_p99_ms:.2f} ")
            f.write(f"| {summary.success_rate:.1f}% |\n")
        
        f.write("\n")
    
    def _write_detailed_results(self, f) -> None:
        """Write detailed results for each backend"""
        for backend_name in sorted(self.backend_summaries.keys()):
            summary = self.backend_summaries[backend_name]
            
            f.write(f"### {backend_name}\n\n")
            
            # Modality-specific results
            f.write("| Modality | Queries | Throughput (QPS) | P50 (ms) | P95 (ms) | P99 (ms) | Mean (ms) | Status |\n")
            f.write("|----------|---------|------------------|----------|----------|----------|-----------|--------|\n")
            
            for modality in sorted(summary.modality_results.keys()):
                metric = summary.modality_results[modality]
                status = "✓" if metric.success else "✗"
                
                f.write(f"| {modality} ")
                f.write(f"| {metric.query_count} ")
                f.write(f"| {metric.throughput_qps:.2f} ")
                f.write(f"| {metric.latency_p50_ms:.2f} ")
                f.write(f"| {metric.latency_p95_ms:.2f} ")
                f.write(f"| {metric.latency_p99_ms:.2f} ")
                f.write(f"| {metric.latency_mean_ms:.2f} ")
                f.write(f"| {status} |\n")
                
                if not metric.success and metric.error:
                    f.write(f"\n*Error: {metric.error}*\n")
            
            f.write("\n")
    
    def _write_outliers_section(self, f) -> None:
        """Write performance outliers section"""
        outliers = self.identify_outliers()
        
        if not any(outliers.values()):
            f.write("*No significant outliers detected.*\n\n")
            return
        
        if outliers["high_performers"]:
            f.write("### High Performers (Throughput)\n\n")
            for item in outliers["high_performers"]:
                f.write(f"- {item}\n")
            f.write("\n")
        
        if outliers["low_latency"]:
            f.write("### Low Latency Champions\n\n")
            for item in outliers["low_latency"]:
                f.write(f"- {item}\n")
            f.write("\n")
        
        if outliers["low_performers"]:
            f.write("### Low Performers (Throughput)\n\n")
            for item in outliers["low_performers"]:
                f.write(f"- {item}\n")
            f.write("\n")
        
        if outliers["high_latency"]:
            f.write("### High Latency Cases\n\n")
            for item in outliers["high_latency"]:
                f.write(f"- {item}\n")
            f.write("\n")
    
    def _write_recommendations(self, f) -> None:
        """Write recommendations based on analysis"""
        if not self.backend_summaries:
            return
        
        # Find best overall backend
        best_overall = max(
            self.backend_summaries.values(),
            key=lambda s: (s.success_rate, s.avg_throughput_qps, -s.avg_latency_p95_ms)
        )
        
        f.write(f"1. **Recommended Backend:** {best_overall.backend}\n")
        f.write(f"   - Throughput: {best_overall.avg_throughput_qps:.2f} QPS\n")
        f.write(f"   - P95 Latency: {best_overall.avg_latency_p95_ms:.2f} ms\n")
        f.write(f"   - Success Rate: {best_overall.success_rate:.1f}%\n\n")
        
        f.write("2. **For Production Use:**\n")
        f.write("   - Consider both throughput and latency requirements\n")
        f.write("   - Factor in operational complexity and cost\n")
        f.write("   - Validate with production-like workloads\n\n")
        
        f.write("3. **Next Steps:**\n")
        f.write("   - Run extended duration tests for stability\n")
        f.write("   - Test with larger datasets\n")
        f.write("   - Evaluate cost per query for each backend\n\n")
    
    def export_csv(self, output_file: Path) -> None:
        """Export results to CSV format"""
        logger.info(f"Exporting CSV: {output_file}")
        
        import csv
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Backend', 'Modality', 'Query Count', 'Successful Queries',
                'Duration (s)', 'Throughput (QPS)', 'P50 (ms)', 'P95 (ms)',
                'P99 (ms)', 'Min (ms)', 'Max (ms)', 'Mean (ms)', 'StdDev (ms)',
                'Success', 'Error'
            ])
            
            # Data rows
            for metric in self.metrics:
                writer.writerow([
                    metric.backend,
                    metric.modality,
                    metric.query_count,
                    metric.successful_queries,
                    f"{metric.duration_seconds:.2f}",
                    f"{metric.throughput_qps:.2f}",
                    f"{metric.latency_p50_ms:.2f}",
                    f"{metric.latency_p95_ms:.2f}",
                    f"{metric.latency_p99_ms:.2f}",
                    f"{metric.latency_min_ms:.2f}",
                    f"{metric.latency_max_ms:.2f}",
                    f"{metric.latency_mean_ms:.2f}",
                    f"{metric.latency_std_ms:.2f}",
                    metric.success,
                    metric.error or ''
                ])
        
        logger.info(f"CSV exported to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze benchmark results and generate reports"
    )
    
    parser.add_argument(
        "results_dir",
        type=Path,
        help="Directory containing benchmark result JSON files"
    )
    
    parser.add_argument(
        "--output",
        type=Path,
        help="Output markdown file (default: <results_dir>/analysis_report.md)"
    )
    
    parser.add_argument(
        "--csv",
        type=Path,
        help="Export CSV file (default: <results_dir>/results.csv)"
    )
    
    args = parser.parse_args()
    
    # Set default output paths
    if not args.output:
        args.output = args.results_dir / "analysis_report.md"
    
    if not args.csv:
        args.csv = args.results_dir / "results.csv"
    
    print(f"\n{'='*60}")
    print("Benchmark Results Analysis")
    print(f"{'='*60}\n")
    
    # Create analyzer
    analyzer = BenchmarkAnalyzer(args.results_dir)
    
    # Load results
    print(f"Loading results from: {args.results_dir}")
    if not analyzer.load_results():
        print("\n✗ Failed to load results")
        return 1
    
    print(f"✓ Loaded {len(analyzer.metrics)} benchmark results\n")
    
    # Calculate summaries
    print("Calculating statistics...")
    analyzer.calculate_summaries()
    print(f"✓ Processed {len(analyzer.backend_summaries)} backends\n")
    
    # Generate reports
    print(f"Generating markdown report: {args.output}")
    analyzer.generate_markdown_report(args.output)
    print(f"✓ Markdown report saved\n")
    
    print(f"Exporting CSV: {args.csv}")
    analyzer.export_csv(args.csv)
    print(f"✓ CSV exported\n")
    
    # Print summary to console
    print(f"{'='*60}")
    print("Summary")
    print(f"{'='*60}\n")
    
    for backend_name in sorted(analyzer.backend_summaries.keys()):
        summary = analyzer.backend_summaries[backend_name]
        print(f"{backend_name}:")
        print(f"  Throughput: {summary.avg_throughput_qps:.2f} QPS")
        print(f"  P95 Latency: {summary.avg_latency_p95_ms:.2f} ms")
        print(f"  Success Rate: {summary.success_rate:.1f}%")
        print()
    
    print(f"{'='*60}")
    print("Analysis Complete!")
    print(f"{'='*60}\n")
    print(f"Reports saved to:")
    print(f"  - Markdown: {args.output}")
    print(f"  - CSV: {args.csv}\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())