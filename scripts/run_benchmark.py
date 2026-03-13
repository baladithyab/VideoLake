#!/usr/bin/env python3
"""
CLI Tool for Running Comprehensive Benchmarks.

Provides a command-line interface for executing and viewing comprehensive benchmarks
across all vector database variants.

Usage:
    # Run comprehensive benchmark for specific backends
    python scripts/run_benchmark.py run s3vector qdrant-ecs lancedb-s3

    # Run with custom configuration
    python scripts/run_benchmark.py run s3vector --config config.json

    # Check status of a running job
    python scripts/run_benchmark.py status <job-id>

    # Get results
    python scripts/run_benchmark.py results <job-id>

    # Generate report
    python scripts/run_benchmark.py report <job-id> --format markdown

    # List all jobs
    python scripts/run_benchmark.py list
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.benchmark_models import BenchmarkConfiguration
from src.services.comprehensive_benchmark_runner import ComprehensiveBenchmarkRunner
from src.services.benchmark_report_generator import BenchmarkReportGenerator
from src.utils.logging_config import get_logger

# Import backend adapters
try:
    from scripts.backend_adapters import get_backend_adapter, BACKEND_TYPES
except ImportError:
    print("ERROR: backend_adapters.py not found. Ensure scripts/backend_adapters.py exists.")
    sys.exit(1)

logger = get_logger(__name__)


class BenchmarkCLI:
    """CLI controller for comprehensive benchmarks"""

    def __init__(self):
        self.results_dir = Path("benchmark_results")
        self.results_dir.mkdir(exist_ok=True)

    async def run_benchmark(
        self,
        backends: List[str],
        config: Optional[BenchmarkConfiguration] = None
    ) -> str:
        """
        Run comprehensive benchmark for specified backends.
        """
        if not config:
            config = BenchmarkConfiguration(backends=backends)

        print(f"\n{'='*60}")
        print("S3Vector Comprehensive Benchmark Suite")
        print(f"{'='*60}\n")
        print(f"Backends: {', '.join(backends)}")
        print(f"Vector Dimension: {config.vector_dimension}")
        print(f"Dataset Sizes: {config.vector_counts}")
        print(f"Test Duration: {config.test_duration_seconds}s")
        print(f"\nStarting benchmark...\n")

        results = []
        job_id = f"cli_{int(time.time())}"

        for i, backend in enumerate(backends, 1):
            print(f"\n[{i}/{len(backends)}] Benchmarking {backend}...")
            print("-" * 60)

            try:
                # Parse backend name
                parts = backend.split("-", 1)
                backend_name = parts[0]
                variant = parts[1] if len(parts) > 1 else "default"

                # Get adapter
                adapter = get_backend_adapter(backend_name, config.to_dict())

                # Create runner
                runner = ComprehensiveBenchmarkRunner(
                    backend=backend_name,
                    variant=variant,
                    adapter=adapter,
                    config=config
                )

                # Run benchmarks
                result = await runner.run_all_benchmarks()
                results.append(result)

                # Print summary
                print(f"\n✓ {backend} completed:")
                if result.latency:
                    print(f"  - Latency P99: {result.latency.p99_ms:.2f}ms")
                if result.throughput:
                    print(f"  - Throughput: {result.throughput.qps:.0f} QPS")
                if result.cost:
                    print(f"  - Monthly Cost: ${result.cost.monthly_cost_estimate_usd:.2f}")

            except Exception as e:
                print(f"\n✗ {backend} failed: {e}")
                logger.error(f"Benchmark failed for {backend}: {e}")

        # Save results
        self._save_results(job_id, results)

        print(f"\n{'='*60}")
        print(f"Benchmark Complete!")
        print(f"Job ID: {job_id}")
        print(f"Results saved to: {self.results_dir}/{job_id}/")
        print(f"{'='*60}\n")

        return job_id

    def _save_results(self, job_id: str, results: List):
        """Save benchmark results to local directory"""
        job_dir = self.results_dir / job_id
        job_dir.mkdir(exist_ok=True)

        # Save individual results
        for result in results:
            result_file = job_dir / f"{result.backend}_{result.variant}.json"
            with open(result_file, 'w') as f:
                f.write(result.to_json())

        # Save summary
        summary = {
            "job_id": job_id,
            "backends": [f"{r.backend}/{r.variant}" for r in results],
            "timestamp": results[0].timestamp.isoformat() if results else None,
            "results_count": len(results)
        }

        summary_file = job_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"Saved {len(results)} results to {job_dir}")

    def generate_report(
        self,
        job_id: str,
        format: str = "markdown"
    ):
        """Generate a report from saved results"""
        job_dir = self.results_dir / job_id

        if not job_dir.exists():
            print(f"ERROR: Job {job_id} not found in {self.results_dir}")
            return

        # Load results
        result_files = list(job_dir.glob("*.json"))
        result_files = [f for f in result_files if f.name != "summary.json"]

        if not result_files:
            print(f"ERROR: No results found for job {job_id}")
            return

        print(f"Loading {len(result_files)} results...")

        # Load results (simplified - in production would deserialize properly)
        results = []
        for result_file in result_files:
            with open(result_file, 'r') as f:
                result_dict = json.load(f)
                results.append(result_dict)

        # Generate report
        generator = BenchmarkReportGenerator()

        # Create comparison (simplified)
        from src.services.benchmark_models import BenchmarkComparison
        comparison = BenchmarkComparison(job_id=job_id)

        if format == "markdown":
            report = generator.generate_markdown_report(comparison)
            report_file = job_dir / "report.md"
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"\nMarkdown report saved to: {report_file}")
            print("\n" + "="*60)
            print(report[:1000])  # Print first 1000 chars
            print("...\n")

        elif format == "csv":
            # Simplified CSV generation
            report = generator.generate_csv_export([])
            report_file = job_dir / "report.csv"
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"\nCSV report saved to: {report_file}")

        elif format == "json":
            report_file = job_dir / "report.json"
            with open(report_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nJSON report saved to: {report_file}")

    def list_jobs(self):
        """List all benchmark jobs"""
        if not self.results_dir.exists():
            print("No benchmark results found.")
            return

        jobs = [d for d in self.results_dir.iterdir() if d.is_dir()]

        if not jobs:
            print("No benchmark jobs found.")
            return

        print(f"\nBenchmark Jobs ({len(jobs)}):")
        print(f"{'='*60}")
        print(f"{'Job ID':<20} {'Backends':<20} {'Files':<10}")
        print(f"{'-'*60}")

        for job_dir in sorted(jobs, reverse=True):
            job_id = job_dir.name
            result_files = len(list(job_dir.glob("*.json"))) - 1  # Exclude summary.json
            backends = "N/A"

            # Try to read summary
            summary_file = job_dir / "summary.json"
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                    backends = ", ".join(summary.get("backends", []))[:15] + "..."

            print(f"{job_id:<20} {backends:<20} {result_files:<10}")

        print(f"{'='*60}\n")

    def show_status(self, job_id: str):
        """Show status of a benchmark job"""
        job_dir = self.results_dir / job_id

        if not job_dir.exists():
            print(f"ERROR: Job {job_id} not found")
            return

        summary_file = job_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)

            print(f"\nJob: {job_id}")
            print(f"Status: Completed")
            print(f"Backends: {', '.join(summary.get('backends', []))}")
            print(f"Results: {summary.get('results_count', 0)}")
            print(f"Timestamp: {summary.get('timestamp', 'N/A')}")
        else:
            print(f"\nJob: {job_id}")
            print(f"Status: Unknown (no summary.json)")


def main():
    parser = argparse.ArgumentParser(
        description="S3Vector Comprehensive Benchmark CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run benchmark for multiple backends
  python scripts/run_benchmark.py run s3vector qdrant-ecs lancedb-s3

  # List all jobs
  python scripts/run_benchmark.py list

  # Generate report
  python scripts/run_benchmark.py report <job-id> --format markdown

  # Show job status
  python scripts/run_benchmark.py status <job-id>
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a comprehensive benchmark")
    run_parser.add_argument(
        "backends",
        nargs="+",
        help="Backend names (e.g., s3vector, qdrant-ecs, lancedb-s3)"
    )
    run_parser.add_argument(
        "--config",
        type=str,
        help="Path to JSON configuration file"
    )
    run_parser.add_argument(
        "--dimension",
        type=int,
        default=1536,
        help="Vector dimension (default: 1536)"
    )
    run_parser.add_argument(
        "--vectors",
        type=int,
        nargs="+",
        default=[1000, 10000],
        help="Dataset sizes to test (default: 1000 10000)"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Check job status")
    status_parser.add_argument("job_id", help="Job ID to check")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("job_id", help="Job ID to report on")
    report_parser.add_argument(
        "--format",
        choices=["markdown", "json", "csv"],
        default="markdown",
        help="Report format (default: markdown)"
    )

    # List command
    subparsers.add_parser("list", help="List all benchmark jobs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cli = BenchmarkCLI()

    try:
        if args.command == "run":
            # Build config
            config = BenchmarkConfiguration(
                backends=args.backends,
                vector_dimension=args.dimension,
                vector_counts=args.vectors
            )

            # Override with config file if provided
            if args.config:
                with open(args.config, 'r') as f:
                    config_dict = json.load(f)
                    config = BenchmarkConfiguration(**config_dict)

            # Run benchmark
            job_id = asyncio.run(cli.run_benchmark(args.backends, config))

        elif args.command == "status":
            cli.show_status(args.job_id)

        elif args.command == "report":
            cli.generate_report(args.job_id, args.format)

        elif args.command == "list":
            cli.list_jobs()

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        logger.exception("CLI error")
        sys.exit(1)


if __name__ == "__main__":
    main()
