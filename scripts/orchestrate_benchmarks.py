#!/usr/bin/env python3
"""
Benchmark Orchestrator

Automates comprehensive benchmarking across all vector DB variants in 3 tiers.
Implements the benchmark methodology from docs/reviews/VECTORDB_RESEARCH.md.

Tier 1 (Must Include - 7 variants):
  - S3Vector Serverless
  - Qdrant ECS/EFS
  - LanceDB ECS/EBS
  - LanceDB S3 Remote API
  - OpenSearch Provisioned
  - pgvector Aurora Serverless v2
  - pgvector RDS PostgreSQL

Tier 2 (Should Include - 5 variants):
  - pgvector Aurora IVFFlat
  - OpenSearch Serverless
  - Qdrant Cloud
  - FAISS Embedded
  - Zilliz Cloud

Tier 3 (Optional - 3 variants):
  - FAISS Lambda
  - FAISS EC2 GPU
  - OpenSearch Algorithm Comparison

Usage:
    # Run all Tier 1 benchmarks
    python scripts/orchestrate_benchmarks.py --tier 1

    # Run specific variants
    python scripts/orchestrate_benchmarks.py --variants s3vector qdrant-ecs lancedb-ebs

    # Run with custom scale
    python scripts/orchestrate_benchmarks.py --tier 1 --vectors 1000,10000,100000

    # Generate comparison report
    python scripts/orchestrate_benchmarks.py --report-only
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.comprehensive_benchmark import ComprehensiveBenchmark, BenchmarkDimensions
from scripts.backend_adapters import get_backend_adapter
from src.services.benchmark_storage import BenchmarkStorage
from src.services.benchmark_reporter import BenchmarkReporter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Variant configurations with cost models
VARIANT_CONFIGS = {
    # ===== TIER 1: MUST INCLUDE =====
    "s3vector": {
        "tier": 1,
        "backend": "s3vector",
        "variant": "serverless",
        "description": "S3Vector Serverless - AWS Native",
        "cost": {
            "infrastructure_monthly_usd": 0,  # Pay per request
            "storage_cost_per_gb": 0.023,  # S3 Standard
            "request_cost_per_million": 0.40  # S3 GET requests
        },
        "config": {}
    },
    "qdrant-ecs": {
        "tier": 1,
        "backend": "qdrant",
        "variant": "ecs-efs",
        "description": "Qdrant on ECS with EFS",
        "cost": {
            "infrastructure_monthly_usd": 103,  # 2 vCPU / 8GB Fargate
            "storage_cost_per_gb": 0.30  # EFS
        },
        "config": {}
    },
    "lancedb-ebs": {
        "tier": 1,
        "backend": "lancedb",
        "variant": "ecs-ebs",
        "description": "LanceDB on ECS with EBS",
        "cost": {
            "infrastructure_monthly_usd": 92,  # 2 vCPU / 8GB Fargate
            "storage_cost_per_gb": 0.08  # EBS gp3
        },
        "config": {}
    },
    "lancedb-s3": {
        "tier": 1,
        "backend": "lancedb",
        "variant": "s3",
        "description": "LanceDB S3 Remote API",
        "cost": {
            "infrastructure_monthly_usd": 5,  # Minimal compute
            "storage_cost_per_gb": 0.023  # S3 Standard
        },
        "config": {}
    },
    "opensearch": {
        "tier": 1,
        "backend": "opensearch",
        "variant": "provisioned-hnsw",
        "description": "OpenSearch Provisioned (HNSW)",
        "cost": {
            "infrastructure_monthly_usd": 362,  # 3x r6g.large
            "storage_cost_per_gb": 0.08  # EBS gp3
        },
        "config": {
            "index_type": "hnsw"
        }
    },
    "pgvector-aurora": {
        "tier": 1,
        "backend": "pgvector",
        "variant": "aurora-serverless-v2",
        "description": "pgvector Aurora Serverless v2",
        "cost": {
            "infrastructure_monthly_usd": 174,  # 2 ACUs average
            "storage_cost_per_gb": 0.10  # Aurora storage
        },
        "config": {
            "index_type": "hnsw"
        }
    },
    "pgvector-rds": {
        "tier": 1,
        "backend": "pgvector",
        "variant": "rds",
        "description": "pgvector RDS PostgreSQL",
        "cost": {
            "infrastructure_monthly_usd": 211,  # db.r6g.large
            "storage_cost_per_gb": 0.115  # gp3
        },
        "config": {
            "index_type": "hnsw"
        }
    },

    # ===== TIER 2: SHOULD INCLUDE =====
    "pgvector-aurora-ivf": {
        "tier": 2,
        "backend": "pgvector",
        "variant": "aurora-ivfflat",
        "description": "pgvector Aurora (IVFFlat)",
        "cost": {
            "infrastructure_monthly_usd": 174,
            "storage_cost_per_gb": 0.10
        },
        "config": {
            "index_type": "ivfflat"
        }
    },
    "opensearch-serverless": {
        "tier": 2,
        "backend": "opensearch",
        "variant": "serverless",
        "description": "OpenSearch Serverless",
        "cost": {
            "infrastructure_monthly_usd": 691,  # 4 OCUs minimum
            "storage_cost_per_gb": 0.024
        },
        "config": {}
    },
    "qdrant-cloud": {
        "tier": 2,
        "backend": "qdrant",
        "variant": "cloud",
        "description": "Qdrant Cloud (Managed)",
        "cost": {
            "infrastructure_monthly_usd": 200,  # 4GB cluster
            "storage_cost_per_gb": 0  # Included
        },
        "config": {}
    },
    "faiss-embedded": {
        "tier": 2,
        "backend": "faiss",
        "variant": "embedded",
        "description": "FAISS Embedded",
        "cost": {
            "infrastructure_monthly_usd": 100,  # Application cost
            "storage_cost_per_gb": 0  # In-memory
        },
        "config": {}
    },
    "zilliz": {
        "tier": 2,
        "backend": "milvus",
        "variant": "zilliz-cloud",
        "description": "Zilliz Cloud (Managed Milvus)",
        "cost": {
            "infrastructure_monthly_usd": 250,
            "storage_cost_per_gb": 0
        },
        "config": {}
    },

    # ===== TIER 3: OPTIONAL =====
    "faiss-lambda": {
        "tier": 3,
        "backend": "faiss",
        "variant": "lambda",
        "description": "FAISS on Lambda",
        "cost": {
            "infrastructure_monthly_usd": 2,  # Pay per invocation
            "storage_cost_per_gb": 0.023  # S3 for index
        },
        "config": {}
    },
    "faiss-gpu": {
        "tier": 3,
        "backend": "faiss",
        "variant": "ec2-gpu",
        "description": "FAISS on EC2 GPU",
        "cost": {
            "infrastructure_monthly_usd": 735,  # g5.xlarge
            "storage_cost_per_gb": 0.08  # EBS
        },
        "config": {}
    },
    "opensearch-faiss": {
        "tier": 3,
        "backend": "opensearch",
        "variant": "provisioned-faiss-ivf",
        "description": "OpenSearch with FAISS IVF",
        "cost": {
            "infrastructure_monthly_usd": 362,
            "storage_cost_per_gb": 0.08
        },
        "config": {
            "index_type": "faiss_ivf"
        }
    }
}


class BenchmarkOrchestrator:
    """Orchestrates comprehensive benchmarking across all variants"""

    def __init__(self, results_dir: Path = None):
        self.results_dir = results_dir or Path("docs/benchmarking/results/comprehensive")
        self.results_dir.mkdir(parents=True, exist_ok=True)

        self.storage = BenchmarkStorage(self.results_dir)
        self.reporter = BenchmarkReporter(self.storage)

        # Track session
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.results_dir / f"session_{self.session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_variants_by_tier(self, tier: int) -> List[str]:
        """Get all variant names for a given tier"""
        return [
            name for name, config in VARIANT_CONFIGS.items()
            if config["tier"] == tier
        ]

    def get_all_variants(self) -> List[str]:
        """Get all variant names"""
        return list(VARIANT_CONFIGS.keys())

    async def benchmark_variant(
        self,
        variant_name: str,
        vector_counts: List[int] = [1000, 10000, 100000],
        query_count: int = 1000,
        dimensions: int = 1536,
        concurrent_clients: int = 5
    ) -> List[BenchmarkDimensions]:
        """
        Run comprehensive benchmark for a single variant across multiple scales.

        Args:
            variant_name: Variant identifier
            vector_counts: List of vector counts to test (for scaling dimension)
            query_count: Number of queries per test
            dimensions: Vector dimensions
            concurrent_clients: Number of concurrent clients

        Returns:
            List of BenchmarkDimensions, one per vector count
        """
        config = VARIANT_CONFIGS.get(variant_name)
        if not config:
            raise ValueError(f"Unknown variant: {variant_name}")

        logger.info(f"\n{'='*80}")
        logger.info(f"Benchmarking: {config['description']}")
        logger.info(f"Tier {config['tier']} | {config['backend']}/{config['variant']}")
        logger.info(f"{'='*80}\n")

        # Initialize adapter
        try:
            adapter = get_backend_adapter(config['backend'], config['config'])

            # Validate connectivity
            if not adapter.health_check():
                logger.error(f"Backend {variant_name} is not accessible")
                return []

            logger.info(f"✓ Backend {variant_name} is accessible")
        except Exception as e:
            logger.error(f"Failed to initialize {variant_name}: {e}")
            return []

        results = []

        # Run benchmark at each scale
        for vector_count in vector_counts:
            logger.info(f"\n--- Testing with {vector_count:,} vectors ---")

            try:
                benchmark = ComprehensiveBenchmark(
                    adapter=adapter,
                    backend=config['backend'],
                    variant=config['variant'],
                    cost_config=config['cost']
                )

                result = await benchmark.run_comprehensive_benchmark(
                    vector_count=vector_count,
                    query_count=query_count,
                    dimensions=dimensions,
                    concurrent_clients=concurrent_clients,
                    measure_recall=vector_count <= 10000  # Recall is expensive, limit to smaller scales
                )

                # Save individual result
                result_file = self.session_dir / f"{variant_name}_{vector_count}.json"
                with open(result_file, 'w') as f:
                    json.dump(result.__dict__, f, indent=2, default=str)

                results.append(result)

                logger.info(f"✓ Completed {vector_count:,} vectors: {result.throughput_qps:.1f} QPS, {result.latency_p50_ms:.2f}ms P50")

            except Exception as e:
                logger.error(f"Benchmark failed for {variant_name} @ {vector_count} vectors: {e}")
                continue

        # Store aggregated results
        self.storage.store_variant_results(variant_name, results, self.session_id)

        return results

    async def run_tier(self, tier: int, **kwargs) -> Dict[str, List[BenchmarkDimensions]]:
        """
        Run all benchmarks for a given tier.

        Args:
            tier: Tier number (1, 2, or 3)
            **kwargs: Additional arguments passed to benchmark_variant

        Returns:
            Dictionary mapping variant names to results
        """
        variants = self.get_variants_by_tier(tier)
        logger.info(f"\n{'#'*80}")
        logger.info(f"# TIER {tier} BENCHMARKS")
        logger.info(f"# Variants: {', '.join(variants)}")
        logger.info(f"{'#'*80}\n")

        results = {}
        for variant in variants:
            try:
                variant_results = await self.benchmark_variant(variant, **kwargs)
                results[variant] = variant_results
            except Exception as e:
                logger.error(f"Failed to benchmark {variant}: {e}")
                results[variant] = []

        return results

    async def run_variants(self, variants: List[str], **kwargs) -> Dict[str, List[BenchmarkDimensions]]:
        """
        Run benchmarks for specific variants.

        Args:
            variants: List of variant names
            **kwargs: Additional arguments passed to benchmark_variant

        Returns:
            Dictionary mapping variant names to results
        """
        results = {}
        for variant in variants:
            try:
                variant_results = await self.benchmark_variant(variant, **kwargs)
                results[variant] = variant_results
            except Exception as e:
                logger.error(f"Failed to benchmark {variant}: {e}")
                results[variant] = []

        return results

    def generate_session_report(self):
        """Generate comprehensive comparison report for this session"""
        logger.info("\n" + "="*80)
        logger.info("Generating session report...")
        logger.info("="*80 + "\n")

        # Generate markdown report
        report_path = self.session_dir / "COMPREHENSIVE_REPORT.md"
        self.reporter.generate_comprehensive_report(
            session_id=self.session_id,
            output_path=report_path
        )

        logger.info(f"✓ Report generated: {report_path}")

        # Generate comparison charts
        charts_dir = self.session_dir / "charts"
        charts_dir.mkdir(exist_ok=True)

        logger.info(f"✓ Charts directory: {charts_dir}")

        return report_path


async def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate comprehensive vector DB benchmarks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Variant selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3],
        help="Run all benchmarks for a specific tier"
    )
    group.add_argument(
        "--variants",
        nargs="+",
        help="Run specific variants (space-separated)"
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all variants (tiers 1, 2, and 3)"
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List all available variants and exit"
    )
    group.add_argument(
        "--report-only",
        action="store_true",
        help="Generate report from existing results without running benchmarks"
    )

    # Benchmark parameters
    parser.add_argument(
        "--vectors",
        type=str,
        default="1000,10000,100000",
        help="Comma-separated vector counts for scaling tests (default: 1000,10000,100000)"
    )
    parser.add_argument(
        "--queries",
        type=int,
        default=1000,
        help="Number of queries per test (default: 1000)"
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=1536,
        help="Vector dimensions (default: 1536, OpenAI ada-002)"
    )
    parser.add_argument(
        "--concurrent-clients",
        type=int,
        default=5,
        help="Number of concurrent clients for load testing (default: 5)"
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("docs/benchmarking/results/comprehensive"),
        help="Directory for results storage"
    )

    args = parser.parse_args()

    # List variants
    if args.list:
        print("\nAvailable variants:\n")
        for tier in [1, 2, 3]:
            tier_variants = [
                (name, config) for name, config in VARIANT_CONFIGS.items()
                if config["tier"] == tier
            ]
            print(f"TIER {tier}:")
            for name, config in tier_variants:
                print(f"  {name:25s} - {config['description']}")
            print()
        return 0

    # Initialize orchestrator
    orchestrator = BenchmarkOrchestrator(results_dir=args.results_dir)

    # Report only
    if args.report_only:
        orchestrator.generate_session_report()
        return 0

    # Parse vector counts
    vector_counts = [int(x.strip()) for x in args.vectors.split(',')]

    # Run benchmarks
    if args.tier:
        await orchestrator.run_tier(
            args.tier,
            vector_counts=vector_counts,
            query_count=args.queries,
            dimensions=args.dimensions,
            concurrent_clients=args.concurrent_clients
        )
    elif args.variants:
        await orchestrator.run_variants(
            args.variants,
            vector_counts=vector_counts,
            query_count=args.queries,
            dimensions=args.dimensions,
            concurrent_clients=args.concurrent_clients
        )
    elif args.all:
        for tier in [1, 2, 3]:
            await orchestrator.run_tier(
                tier,
                vector_counts=vector_counts,
                query_count=args.queries,
                dimensions=args.dimensions,
                concurrent_clients=args.concurrent_clients
            )
    else:
        parser.error("Must specify --tier, --variants, --all, --list, or --report-only")

    # Generate report
    orchestrator.generate_session_report()

    logger.info("\n" + "="*80)
    logger.info("Benchmark orchestration complete!")
    logger.info(f"Results saved to: {orchestrator.session_dir}")
    logger.info("="*80 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
