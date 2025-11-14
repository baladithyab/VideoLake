#!/usr/bin/env python3
"""
Benchmark Results Analyzer

Analyzes and compares benchmark results across multiple backends.
Generates comparison reports, charts, and recommendations.

Usage:
    python scripts/results_analyzer.py --results results1.json results2.json
    python scripts/results_analyzer.py --directory ./benchmark-results --compare
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict
import statistics


class ResultsAnalyzer:
    """Analyzes benchmark results and generates comparisons"""
    
    def __init__(self, result_files: List[Path]):
        self.result_files = result_files
        self.results: List[Dict[str, Any]] = []
        self.load_results()
    
    def load_results(self):
        """Load all result files"""
        for file_path in self.result_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.results.extend(data)
                    else:
                        self.results.append(data)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
    
    def group_by_backend(self) -> Dict[str, List[Dict]]:
        """Group results by backend"""
        grouped = defaultdict(list)
        for result in self.results:
            backend = result.get("backend", "unknown")
            grouped[backend].append(result)
        return dict(grouped)
    
    def calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical metrics"""
        if not values:
            return {}
        
        return {
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "count": len(values)
        }
    
    def analyze_index_performance(self) -> Dict[str, Dict]:
        """Analyze indexing performance across backends"""
        grouped = self.group_by_backend()
        analysis = {}
        
        for backend, results in grouped.items():
            index_results = [
                r for r in results 
                if r.get("operation") == "index" and r.get("error") is None
            ]
            
            if not index_results:
                continue
            
            durations = [r["duration_seconds"] for r in index_results]
            vector_counts = [r["vectors_count"] for r in index_results]
            
            analysis[backend] = {
                "duration_stats": self.calculate_statistics(durations),
                "vector_counts": sorted(set(vector_counts)),
                "throughput_avg": sum(
                    r["vectors_count"] / r["duration_seconds"] 
                    for r in index_results if r["duration_seconds"] > 0
                ) / len(index_results) if index_results else 0,
                "sample_count": len(index_results)
            }
        
        return analysis
    
    def analyze_search_performance(self) -> Dict[str, Dict]:
        """Analyze search performance across backends"""
        grouped = self.group_by_backend()
        analysis = {}
        
        for backend, results in grouped.items():
            search_results = [
                r for r in results 
                if r.get("operation") == "search" and r.get("error") is None
            ]
            
            if not search_results:
                continue
            
            latencies_p50 = [r["latency_p50_ms"] for r in search_results if "latency_p50_ms" in r]
            latencies_p95 = [r["latency_p95_ms"] for r in search_results if "latency_p95_ms" in r]
            latencies_p99 = [r["latency_p99_ms"] for r in search_results if "latency_p99_ms" in r]
            throughputs = [r["throughput_qps"] for r in search_results if "throughput_qps" in r]
            
            analysis[backend] = {
                "latency_p50_stats": self.calculate_statistics(latencies_p50),
                "latency_p95_stats": self.calculate_statistics(latencies_p95),
                "latency_p99_stats": self.calculate_statistics(latencies_p99),
                "throughput_stats": self.calculate_statistics(throughputs),
                "sample_count": len(search_results)
            }
        
        return analysis
    
    def compare_backends(self) -> Dict[str, Any]:
        """Generate backend comparison"""
        index_analysis = self.analyze_index_performance()
        search_analysis = self.analyze_search_performance()
        
        comparison = {
            "index_performance": {},
            "search_performance": {},
            "rankings": {
                "fastest_index": None,
                "fastest_search": None,
                "most_consistent": None
            }
        }
        
        # Compare index performance
        for backend, stats in index_analysis.items():
            comparison["index_performance"][backend] = {
                "avg_throughput_vectors_per_sec": stats["throughput_avg"],
                "avg_duration_seconds": stats["duration_stats"].get("mean", 0)
            }
        
        # Compare search performance
        for backend, stats in search_analysis.items():
            comparison["search_performance"][backend] = {
                "p50_latency_ms": stats["latency_p50_stats"].get("median", 0),
                "p95_latency_ms": stats["latency_p95_stats"].get("median", 0),
                "p99_latency_ms": stats["latency_p99_stats"].get("median", 0),
                "avg_throughput_qps": stats["throughput_stats"].get("mean", 0)
            }
        
        # Determine rankings
        if comparison["index_performance"]:
            fastest_index = max(
                comparison["index_performance"].items(),
                key=lambda x: x[1]["avg_throughput_vectors_per_sec"]
            )
            comparison["rankings"]["fastest_index"] = fastest_index[0]
        
        if comparison["search_performance"]:
            fastest_search = max(
                comparison["search_performance"].items(),
                key=lambda x: x[1]["avg_throughput_qps"]
            )
            comparison["rankings"]["fastest_search"] = fastest_search[0]
        
        return comparison
    
    def generate_recommendations(self, comparison: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Index performance recommendations
        if comparison["index_performance"]:
            fastest = comparison["rankings"]["fastest_index"]
            if fastest:
                recommendations.append(
                    f"For bulk indexing workloads, {fastest} shows the best throughput"
                )
        
        # Search performance recommendations
        if comparison["search_performance"]:
            fastest = comparison["rankings"]["fastest_search"]
            if fastest:
                recommendations.append(
                    f"For search-heavy workloads, {fastest} provides the best query performance"
                )
        
        # Latency recommendations
        for backend, stats in comparison["search_performance"].items():
            if stats["p99_latency_ms"] > 1000:  # > 1 second
                recommendations.append(
                    f"Warning: {backend} shows high p99 latency ({stats['p99_latency_ms']:.2f}ms), "
                    "may not be suitable for real-time applications"
                )
        
        return recommendations
    
    def generate_markdown_report(self, output_file: Path):
        """Generate comprehensive markdown report"""
        comparison = self.compare_backends()
        recommendations = self.generate_recommendations(comparison)
        
        with open(output_file, 'w') as f:
            f.write("# Benchmark Results Analysis\n\n")
            
            # Index Performance
            f.write("## Index Performance Comparison\n\n")
            f.write("| Backend | Avg Throughput (vectors/s) | Avg Duration (s) |\n")
            f.write("|---------|---------------------------|------------------|\n")
            for backend, stats in sorted(
                comparison["index_performance"].items(),
                key=lambda x: x[1]["avg_throughput_vectors_per_sec"],
                reverse=True
            ):
                f.write(f"| {backend} | {stats['avg_throughput_vectors_per_sec']:.2f} | "
                       f"{stats['avg_duration_seconds']:.2f} |\n")
            f.write("\n")
            
            # Search Performance
            f.write("## Search Performance Comparison\n\n")
            f.write("| Backend | P50 Latency (ms) | P95 Latency (ms) | P99 Latency (ms) | Avg Throughput (QPS) |\n")
            f.write("|---------|------------------|------------------|------------------|---------------------|\n")
            for backend, stats in sorted(
                comparison["search_performance"].items(),
                key=lambda x: x[1]["avg_throughput_qps"],
                reverse=True
            ):
                f.write(f"| {backend} | {stats['p50_latency_ms']:.2f} | "
                       f"{stats['p95_latency_ms']:.2f} | {stats['p99_latency_ms']:.2f} | "
                       f"{stats['avg_throughput_qps']:.2f} |\n")
            f.write("\n")
            
            # Rankings
            f.write("## Rankings\n\n")
            if comparison["rankings"]["fastest_index"]:
                f.write(f"**Fastest Index:** {comparison['rankings']['fastest_index']}\n\n")
            if comparison["rankings"]["fastest_search"]:
                f.write(f"**Fastest Search:** {comparison['rankings']['fastest_search']}\n\n")
            
            # Recommendations
            if recommendations:
                f.write("## Recommendations\n\n")
                for i, rec in enumerate(recommendations, 1):
                    f.write(f"{i}. {rec}\n")
                f.write("\n")
        
        print(f"Report generated: {output_file}")
    
    def generate_csv_export(self, output_file: Path):
        """Export results as CSV for external analysis"""
        import csv
        
        with open(output_file, 'w', newline='') as f:
            if not self.results:
                return
            
            # Get all possible fields
            fieldnames = set()
            for result in self.results:
                fieldnames.update(result.keys())
            
            fieldnames = sorted(list(fieldnames))
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"CSV exported: {output_file}")


def main():
    """Main analyzer entry point"""
    parser = argparse.ArgumentParser(
        description="Analyze and compare benchmark results"
    )
    
    parser.add_argument(
        "--results",
        nargs="+",
        type=Path,
        help="Result files to analyze (JSON format)"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help="Directory containing result files"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Generate comparison report"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("analysis_report.md"),
        help="Output file for report (default: analysis_report.md)"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Export results as CSV"
    )
    
    args = parser.parse_args()
    
    # Collect result files
    result_files = []
    if args.results:
        result_files.extend(args.results)
    if args.directory:
        if not args.directory.exists():
            print(f"Directory not found: {args.directory}")
            return 1
        result_files.extend(args.directory.glob("*.json"))
    
    if not result_files:
        print("No result files specified")
        return 1
    
    # Create analyzer
    analyzer = ResultsAnalyzer(result_files)
    
    if not analyzer.results:
        print("No results loaded")
        return 1
    
    print(f"Loaded {len(analyzer.results)} results from {len(result_files)} files")
    
    # Generate reports
    if args.compare:
        analyzer.generate_markdown_report(args.output)
    
    if args.csv:
        analyzer.generate_csv_export(args.csv)
    
    # Print summary
    comparison = analyzer.compare_backends()
    print("\n=== Quick Summary ===")
    print(f"Backends analyzed: {len(comparison['index_performance'])}")
    if comparison["rankings"]["fastest_index"]:
        print(f"Fastest index: {comparison['rankings']['fastest_index']}")
    if comparison["rankings"]["fastest_search"]:
        print(f"Fastest search: {comparison['rankings']['fastest_search']}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())