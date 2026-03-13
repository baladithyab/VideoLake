#!/usr/bin/env python3
"""
Benchmark CLI - Simple interface for running and viewing benchmarks

Usage:
    # Run quick benchmark for a single variant
    python scripts/benchmark_cli.py run --variant s3vector --quick

    # Run full benchmark suite for Tier 1
    python scripts/benchmark_cli.py run --tier 1

    # List all sessions
    python scripts/benchmark_cli.py list

    # View results from a session
    python scripts/benchmark_cli.py show --session <session_id>

    # Compare variants
    python scripts/benchmark_cli.py compare --variants s3vector qdrant-ecs lancedb-ebs

    # Generate report
    python scripts/benchmark_cli.py report --session <session_id>
"""

import argparse
import asyncio
import sys
from pathlib import Path
from tabulate import tabulate
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.benchmark_storage import BenchmarkStorage
from src.services.benchmark_reporter import BenchmarkReporter
from scripts.orchestrate_benchmarks import BenchmarkOrchestrator, VARIANT_CONFIGS


def cmd_list(args):
    """List all benchmark sessions"""
    storage = BenchmarkStorage(Path(args.results_dir))
    sessions = storage.list_sessions()

    if not sessions:
        print("No benchmark sessions found.")
        return

    print("\nBenchmark Sessions:\n")
    table_data = [
        [
            s["session_id"],
            s["timestamp"],
            s["variant_count"],
            ", ".join(s["variants"][:3]) + ("..." if len(s["variants"]) > 3 else "")
        ]
        for s in sessions
    ]

    print(tabulate(
        table_data,
        headers=["Session ID", "Timestamp", "Variants", "Tested"],
        tablefmt="grid"
    ))


def cmd_show(args):
    """Show results from a session"""
    storage = BenchmarkStorage(Path(args.results_dir))

    session_id = args.session
    if not session_id:
        sessions = storage.list_sessions()
        if sessions:
            session_id = sessions[0]["session_id"]
            print(f"Using latest session: {session_id}\n")
        else:
            print("No sessions found.")
            return

    results = storage.load_session_results(session_id)

    if not results:
        print(f"No results found for session {session_id}")
        return

    print(f"\n{'='*80}")
    print(f"Session: {session_id}")
    print(f"{'='*80}\n")

    for variant_name, variant_results in sorted(results.items()):
        print(f"\n{variant_name}:")
        print(f"  Results: {len(variant_results)} scale(s)")

        if variant_results:
            # Show summary of first result
            result = variant_results[0]
            print(f"  Vectors: {result.get('vectors_tested', 'N/A'):,}")
            print(f"  Latency P50: {result.get('latency_p50_ms', 'N/A'):.2f}ms")
            print(f"  Throughput: {result.get('throughput_qps', 'N/A'):.1f} QPS")
            if result.get('recall_at_10'):
                print(f"  Recall@10: {result.get('recall_at_10', 0)*100:.1f}%")


def cmd_compare(args):
    """Compare multiple variants"""
    storage = BenchmarkStorage(Path(args.results_dir))

    session_id = args.session
    if not session_id:
        session_id = storage.get_latest_session()
        if session_id:
            print(f"Using latest session: {session_id}\n")

    if not session_id:
        print("No sessions found.")
        return

    variants = args.variants
    metric = args.metric or "throughput_qps"

    comparison = storage.compare_variants(variants, session_id, metric)

    if "error" in comparison:
        print(f"Error: {comparison['error']}")
        return

    print(f"\n{'='*80}")
    print(f"Comparing {len(variants)} variants on '{metric}'")
    print(f"Session: {session_id}")
    print(f"{'='*80}\n")

    if "ranked" in comparison:
        table_data = [
            [rank, item["variant"], f"{item['mean']:.2f}"]
            for rank, item in enumerate(comparison["ranked"], 1)
        ]

        print(tabulate(
            table_data,
            headers=["Rank", "Variant", f"Mean {metric}"],
            tablefmt="grid"
        ))


def cmd_report(args):
    """Generate comprehensive report"""
    storage = BenchmarkStorage(Path(args.results_dir))
    reporter = BenchmarkReporter(storage)

    session_id = args.session
    if not session_id:
        session_id = storage.get_latest_session()
        if session_id:
            print(f"Using latest session: {session_id}\n")

    if not session_id:
        print("No sessions found.")
        return

    output_path = args.output
    if not output_path:
        output_path = Path(args.results_dir) / session_id / "REPORT.md"

    print(f"Generating report for session {session_id}...")
    report = reporter.generate_comprehensive_report(session_id, output_path)

    if report:
        print(f"\n✓ Report generated: {output_path}")
        print(f"  Size: {len(report)} characters")
    else:
        print("Failed to generate report")


async def cmd_run(args):
    """Run benchmarks"""
    orchestrator = BenchmarkOrchestrator(results_dir=Path(args.results_dir))

    # Parse vector counts
    if args.quick:
        vector_counts = [1000]  # Quick test with 1K vectors
        query_count = 100
        concurrent_clients = 1
    else:
        vector_counts = [int(x.strip()) for x in args.vectors.split(',')]
        query_count = args.queries
        concurrent_clients = args.concurrent_clients

    print(f"\n{'='*80}")
    print(f"Running Benchmarks")
    print(f"Vector counts: {vector_counts}")
    print(f"Queries: {query_count}")
    print(f"Concurrent clients: {concurrent_clients}")
    print(f"{'='*80}\n")

    # Run benchmarks
    if args.tier:
        await orchestrator.run_tier(
            args.tier,
            vector_counts=vector_counts,
            query_count=query_count,
            concurrent_clients=concurrent_clients
        )
    elif args.variant:
        await orchestrator.run_variants(
            [args.variant],
            vector_counts=vector_counts,
            query_count=query_count,
            concurrent_clients=concurrent_clients
        )
    else:
        print("Error: Must specify --tier or --variant")
        return

    # Generate report
    print("\nGenerating report...")
    orchestrator.generate_session_report()

    print(f"\n✓ Benchmarks complete!")
    print(f"  Session: {orchestrator.session_id}")
    print(f"  Results: {orchestrator.session_dir}")


def cmd_variants(args):
    """List available variants"""
    print("\nAvailable Variants:\n")

    for tier in [1, 2, 3]:
        tier_variants = [
            (name, config) for name, config in VARIANT_CONFIGS.items()
            if config["tier"] == tier
        ]

        if tier_variants:
            print(f"{'='*80}")
            print(f"TIER {tier}")
            print(f"{'='*80}\n")

            for name, config in tier_variants:
                monthly_cost = config['cost'].get('infrastructure_monthly_usd', 0)
                print(f"  {name:25s} - {config['description']}")
                print(f"  {'':25s}   Monthly Cost: ${monthly_cost:,.0f}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark CLI - Run and view vector DB benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("docs/benchmarking/results/comprehensive"),
        help="Results directory"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # List command
    subparsers.add_parser("list", help="List all benchmark sessions")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show session results")
    show_parser.add_argument("--session", help="Session ID (default: latest)")

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare variants")
    compare_parser.add_argument("--variants", nargs="+", required=True, help="Variants to compare")
    compare_parser.add_argument("--session", help="Session ID (default: latest)")
    compare_parser.add_argument("--metric", default="throughput_qps", help="Metric to compare")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("--session", help="Session ID (default: latest)")
    report_parser.add_argument("--output", type=Path, help="Output path")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run benchmarks")
    run_group = run_parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument("--tier", type=int, choices=[1, 2, 3], help="Run tier")
    run_group.add_argument("--variant", help="Run specific variant")
    run_parser.add_argument("--quick", action="store_true", help="Quick test (1K vectors, 100 queries)")
    run_parser.add_argument("--vectors", default="1000,10000,100000", help="Vector counts (comma-separated)")
    run_parser.add_argument("--queries", type=int, default=1000, help="Number of queries")
    run_parser.add_argument("--concurrent-clients", type=int, default=5, help="Concurrent clients")

    # Variants command
    subparsers.add_parser("variants", help="List available variants")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    if args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "run":
        return asyncio.run(cmd_run(args))
    elif args.command == "variants":
        cmd_variants(args)
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
