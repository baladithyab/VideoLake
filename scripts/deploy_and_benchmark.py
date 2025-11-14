#!/usr/bin/env python3
"""
Videolake Deployment & Benchmarking Orchestration

Automates the complete workflow:
1. Infrastructure deployment via Terraform
2. Docker image build & ECR push
3. Multi-backend deployment (7 configurations)
4. Comprehensive benchmark testing
5. Results collection & reporting

Usage:
    python scripts/deploy_and_benchmark.py --backends s3vector lancedb-s3
    python scripts/deploy_and_benchmark.py --all-backends --benchmark-only
    python scripts/deploy_and_benchmark.py --backends qdrant-efs --destroy-after
"""

import subprocess
import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import backend adapters for connectivity validation
from scripts.backend_adapters import (
    validate_backend_connectivity,
    BACKEND_TYPES,
    DEFAULT_ENDPOINTS
)

# Backend configurations with correct endpoints
BACKEND_CONFIGS = {
    "s3vector": {
        "name": "S3Vector Direct",
        "terraform_dir": "terraform/backends/s3vector",
        "requires_docker": False,
        "service_name": "s3vector-api",
        "backend_type": "sdk",  # AWS SDK-based
        "endpoint": None  # No HTTP endpoint, uses AWS SDK
    },
    "opensearch": {
        "name": "OpenSearch + S3Vector",
        "terraform_dir": "terraform/backends/opensearch",
        "requires_docker": False,
        "service_name": "opensearch-s3vector-api",
        "backend_type": "hybrid",  # Both OpenSearch REST and S3Vector SDK
        "endpoint": None
    },
    "lancedb-s3": {
        "name": "LanceDB + S3",
        "terraform_dir": "terraform/backends/lancedb_s3",
        "requires_docker": True,
        "service_name": "lancedb-s3-api",
        "backend_type": "rest",
        "endpoint": "http://18.234.151.118:8000"  # Updated LanceDB endpoint
    },
    "lancedb-efs": {
        "name": "LanceDB + EFS",
        "terraform_dir": "terraform/backends/lancedb_efs",
        "requires_docker": True,
        "service_name": "lancedb-efs-api",
        "backend_type": "rest",
        "endpoint": "http://18.234.151.118:8000"  # Updated LanceDB endpoint
    },
    "lancedb-ebs": {
        "name": "LanceDB + EBS",
        "terraform_dir": "terraform/backends/lancedb_ebs",
        "requires_docker": True,
        "service_name": "lancedb-ebs-api",
        "backend_type": "rest",
        "endpoint": "http://18.234.151.118:8000"  # Updated LanceDB endpoint
    },
    "qdrant-efs": {
        "name": "Qdrant + EFS",
        "terraform_dir": "terraform/backends/qdrant_efs",
        "requires_docker": False,
        "service_name": "qdrant-efs-api",
        "backend_type": "rest",
        "endpoint": "http://98.93.105.87:6333"
    },
    "qdrant-ebs": {
        "name": "Qdrant + EBS",
        "terraform_dir": "terraform/backends/qdrant_ebs",
        "requires_docker": False,
        "service_name": "qdrant-ebs-api",
        "backend_type": "rest",
        "endpoint": "http://98.93.105.87:6333"
    }
}


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run"""
    backend: str
    operation: str
    duration_seconds: float
    vectors_count: int
    latency_p50_ms: Optional[float] = None
    latency_p95_ms: Optional[float] = None
    latency_p99_ms: Optional[float] = None
    throughput_qps: Optional[float] = None
    memory_mb: Optional[float] = None
    cpu_percent: Optional[float] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class VideolakeOrchestrator:
    """Orchestrates Videolake deployment and benchmarking"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.results: List[BenchmarkResult] = []
        self.project_root = Path(__file__).parent.parent
        self.output_dir = Path(config["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.terraform_outputs: Dict[str, Any] = {}
        self.setup_logging()

    def setup_logging(self):
        """Configure logging with file and console handlers"""
        log_file = self.output_dir / f"orchestration_{datetime.now():%Y%m%d_%H%M%S}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Orchestration started - Logs: {log_file}")
        self.logger.info(f"Configuration: {json.dumps(self.config, indent=2)}")

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, 
                   check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run shell command with logging"""
        cwd = cwd or self.project_root
        self.logger.info(f"Running: {' '.join(cmd)} in {cwd}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=capture_output,
                text=True
            )
            
            if result.stdout:
                self.logger.debug(f"STDOUT: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"STDERR: {result.stderr}")
            
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command failed: {' '.join(cmd)}")
            self.logger.error(f"Exit code: {e.returncode}")
            if e.stdout:
                self.logger.error(f"STDOUT: {e.stdout}")
            if e.stderr:
                self.logger.error(f"STDERR: {e.stderr}")
            raise

    def deploy_infrastructure(self, backends: List[str]):
        """Deploy Terraform infrastructure for specified backends"""
        self.logger.info(f"Deploying infrastructure for backends: {backends}")
        
        for backend in backends:
            if backend not in BACKEND_CONFIGS:
                raise ValueError(f"Unknown backend: {backend}")
            
            config = BACKEND_CONFIGS[backend]
            self.logger.info(f"Deploying {config['name']}...")
            
            terraform_dir = self.project_root / config["terraform_dir"]
            if not terraform_dir.exists():
                raise FileNotFoundError(f"Terraform directory not found: {terraform_dir}")
            
            # Terraform init
            self.logger.info(f"Running terraform init for {backend}...")
            self.run_command(["terraform", "init"], cwd=terraform_dir)
            
            # Terraform plan
            self.logger.info(f"Running terraform plan for {backend}...")
            plan_file = terraform_dir / "tfplan"
            self.run_command(
                ["terraform", "plan", "-out", str(plan_file)],
                cwd=terraform_dir
            )
            
            # Terraform apply
            self.logger.info(f"Running terraform apply for {backend}...")
            self.run_command(
                ["terraform", "apply", "-auto-approve", str(plan_file)],
                cwd=terraform_dir
            )
            
            # Capture outputs
            self.logger.info(f"Capturing terraform outputs for {backend}...")
            result = self.run_command(
                ["terraform", "output", "-json"],
                cwd=terraform_dir
            )
            self.terraform_outputs[backend] = json.loads(result.stdout)
            
            self.logger.info(f"✓ {config['name']} deployed successfully")

    def build_and_push_docker(self):
        """Build LanceDB Docker image and push to ECR"""
        self.logger.info("Building and pushing LanceDB Docker image...")
        
        # Check if ECR module outputs exist
        ecr_dir = self.project_root / "terraform/modules/ecr_lancedb"
        if not ecr_dir.exists():
            raise FileNotFoundError("ECR module not found")
        
        # Get ECR outputs (assuming ECR is deployed as part of infrastructure)
        # For now, we'll build locally and push using AWS CLI
        docker_dir = self.project_root / "docker/lancedb-api"
        
        if not docker_dir.exists():
            raise FileNotFoundError(f"Docker directory not found: {docker_dir}")
        
        # Build Docker image
        image_tag = "lancedb-api:latest"
        self.logger.info(f"Building Docker image: {image_tag}")
        self.run_command(
            ["docker", "build", "-t", image_tag, "."],
            cwd=docker_dir
        )
        
        # Get ECR login and push (this would use terraform outputs in production)
        self.logger.info("Docker image built successfully")
        self.logger.info("Note: ECR push requires terraform outputs for ECR repository URL")

    def wait_for_backends(self, backends: List[str], timeout: int = 600):
        """Wait for backend services to be healthy using unified connectivity validation"""
        self.logger.info(f"Waiting for backends to be healthy (timeout: {timeout}s)...")
        
        start_time = time.time()
        healthy_backends = set()
        
        while time.time() - start_time < timeout:
            for backend in backends:
                if backend in healthy_backends:
                    continue
                
                config = BACKEND_CONFIGS[backend]
                backend_type = config.get("backend_type", "rest")
                
                # Use unified connectivity validation
                try:
                    validation_config = {}
                    if config.get("endpoint"):
                        validation_config["endpoint"] = config["endpoint"]
                    
                    validation = validate_backend_connectivity(backend, validation_config)
                    
                    if validation.get("accessible", False):
                        self.logger.info(f"✓ {config['name']} is healthy "
                                       f"({validation.get('response_time_ms', 0):.0f}ms)")
                        healthy_backends.add(backend)
                    else:
                        self.logger.debug(f"Backend {backend} not ready: {validation.get('error', 'not accessible')}")
                        
                except Exception as e:
                    self.logger.debug(f"Backend {backend} connectivity check failed: {e}")
            
            if len(healthy_backends) == len(backends):
                self.logger.info("All backends are healthy!")
                return
            
            time.sleep(10)
        
        unhealthy = set(backends) - healthy_backends
        raise TimeoutError(f"Backends did not become healthy: {unhealthy}")

    def run_benchmarks(self, backends: List[str]):
        """Run comprehensive benchmarks on all backends"""
        self.logger.info(f"Running benchmarks on {len(backends)} backends...")
        
        test_vectors = [10, 100, 1000]
        test_queries = [10, 50, 100]
        
        for backend in backends:
            config = BACKEND_CONFIGS[backend]
            self.logger.info(f"Benchmarking {config['name']}...")
            
            for vector_count in test_vectors:
                # Index benchmark
                start = time.time()
                try:
                    # Build command with endpoint if available
                    cmd = [
                        "python", "scripts/benchmark_backend.py",
                        "--backend", backend,
                        "--operation", "index",
                        "--vectors", str(vector_count)
                    ]
                    
                    # Add endpoint for REST backends
                    backend_config = BACKEND_CONFIGS.get(backend, {})
                    if backend_config.get("endpoint"):
                        cmd.extend(["--endpoint", backend_config["endpoint"]])
                    
                    # Call benchmark script
                    result = self.run_command(cmd, check=False)
                    
                    duration = time.time() - start
                    
                    if result.returncode == 0:
                        self.results.append(BenchmarkResult(
                            backend=backend,
                            operation="index",
                            duration_seconds=duration,
                            vectors_count=vector_count
                        ))
                        self.logger.info(f"✓ Indexed {vector_count} vectors in {duration:.2f}s")
                    else:
                        self.logger.error(f"✗ Index failed for {vector_count} vectors")
                        self.results.append(BenchmarkResult(
                            backend=backend,
                            operation="index",
                            duration_seconds=duration,
                            vectors_count=vector_count,
                            error=result.stderr
                        ))
                except Exception as e:
                    self.logger.error(f"Benchmark error: {e}")
                    self.results.append(BenchmarkResult(
                        backend=backend,
                        operation="index",
                        duration_seconds=time.time() - start,
                        vectors_count=vector_count,
                        error=str(e)
                    ))
                
                # Search benchmarks
                for query_count in test_queries:
                    start = time.time()
                    try:
                        # Build command with endpoint if available
                        cmd = [
                            "python", "scripts/benchmark_backend.py",
                            "--backend", backend,
                            "--operation", "search",
                            "--queries", str(query_count)
                        ]
                        
                        # Add endpoint for REST backends (reuse backend_config from above)
                        backend_config = BACKEND_CONFIGS.get(backend, {})
                        if backend_config.get("endpoint"):
                            cmd.extend(["--endpoint", backend_config["endpoint"]])
                        
                        result = self.run_command(cmd, check=False)
                        
                        duration = time.time() - start
                        
                        if result.returncode == 0:
                            # Parse latency metrics from output
                            self.results.append(BenchmarkResult(
                                backend=backend,
                                operation="search",
                                duration_seconds=duration,
                                vectors_count=query_count,
                                throughput_qps=query_count / duration if duration > 0 else 0
                            ))
                            self.logger.info(f"✓ Searched {query_count} queries in {duration:.2f}s "
                                           f"({query_count/duration:.2f} QPS)")
                        else:
                            self.results.append(BenchmarkResult(
                                backend=backend,
                                operation="search",
                                duration_seconds=duration,
                                vectors_count=query_count,
                                error=result.stderr
                            ))
                    except Exception as e:
                        self.logger.error(f"Search benchmark error: {e}")

    def collect_results(self):
        """Collect and format benchmark results"""
        self.logger.info("Collecting benchmark results...")
        
        # Save as JSON
        json_file = self.output_dir / f"results_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(json_file, 'w') as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)
        
        self.logger.info(f"Results saved to {json_file}")
        
        # Generate summary statistics
        summary = defaultdict(lambda: {"index": [], "search": []})
        for result in self.results:
            if result.error is None:
                summary[result.backend][result.operation].append(result.duration_seconds)
        
        # Save summary
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(dict(summary), f, indent=2)
        
        self.logger.info(f"Summary saved to {summary_file}")

    def generate_report(self):
        """Generate markdown report with results"""
        self.logger.info("Generating markdown report...")
        
        report_file = self.output_dir / f"report_{datetime.now():%Y%m%d_%H%M%S}.md"
        
        with open(report_file, 'w') as f:
            f.write("# Videolake Benchmark Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            f.write("## Configuration\n\n")
            f.write(f"```json\n{json.dumps(self.config, indent=2)}\n```\n\n")
            
            f.write("## Results Summary\n\n")
            
            # Group by backend
            backends = {}
            for result in self.results:
                if result.backend not in backends:
                    backends[result.backend] = []
                backends[result.backend].append(result)
            
            for backend, results in backends.items():
                config = BACKEND_CONFIGS.get(backend, {})
                f.write(f"### {config.get('name', backend)}\n\n")
                
                # Index results
                index_results = [r for r in results if r.operation == "index" and r.error is None]
                if index_results:
                    f.write("**Index Performance:**\n\n")
                    f.write("| Vectors | Duration (s) |\n")
                    f.write("|---------|-------------|\n")
                    for r in sorted(index_results, key=lambda x: x.vectors_count):
                        f.write(f"| {r.vectors_count} | {r.duration_seconds:.2f} |\n")
                    f.write("\n")
                
                # Search results
                search_results = [r for r in results if r.operation == "search" and r.error is None]
                if search_results:
                    f.write("**Search Performance:**\n\n")
                    f.write("| Queries | Duration (s) | Throughput (QPS) |\n")
                    f.write("|---------|--------------|------------------|\n")
                    for r in sorted(search_results, key=lambda x: x.vectors_count):
                        qps = r.throughput_qps or 0
                        f.write(f"| {r.vectors_count} | {r.duration_seconds:.2f} | {qps:.2f} |\n")
                    f.write("\n")
                
                # Errors
                error_results = [r for r in results if r.error is not None]
                if error_results:
                    f.write("**Errors:**\n\n")
                    for r in error_results:
                        f.write(f"- {r.operation} ({r.vectors_count} vectors): {r.error}\n")
                    f.write("\n")
        
        self.logger.info(f"Report generated: {report_file}")

    def cleanup(self, destroy: bool = False):
        """Cleanup resources if requested"""
        if not destroy:
            self.logger.info("Skipping cleanup (--destroy-after not specified)")
            return
        
        self.logger.info("Cleaning up infrastructure...")
        
        backends = self.config.get("backends", [])
        for backend in backends:
            config = BACKEND_CONFIGS.get(backend)
            if not config:
                continue
            
            terraform_dir = self.project_root / config["terraform_dir"]
            if terraform_dir.exists():
                self.logger.info(f"Destroying {config['name']}...")
                try:
                    self.run_command(
                        ["terraform", "destroy", "-auto-approve"],
                        cwd=terraform_dir,
                        check=False
                    )
                    self.logger.info(f"✓ {config['name']} destroyed")
                except Exception as e:
                    self.logger.error(f"Failed to destroy {backend}: {e}")


def main():
    """Main orchestration entry point"""
    parser = argparse.ArgumentParser(
        description="Videolake Deployment & Benchmarking Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy and benchmark S3Vector only
  python scripts/deploy_and_benchmark.py --backends s3vector
  
  # Deploy and benchmark multiple backends
  python scripts/deploy_and_benchmark.py --backends s3vector lancedb-s3 opensearch
  
  # Benchmark only (skip deployment)
  python scripts/deploy_and_benchmark.py --backends s3vector --benchmark-only
  
  # Deploy, benchmark, and destroy
  python scripts/deploy_and_benchmark.py --backends s3vector --destroy-after
  
  # All backends with full workflow
  python scripts/deploy_and_benchmark.py --all-backends
        """
    )
    
    parser.add_argument(
        "--backends",
        nargs="+",
        choices=list(BACKEND_CONFIGS.keys()),
        help="Backends to deploy and benchmark"
    )
    parser.add_argument(
        "--all-backends",
        action="store_true",
        help="Deploy and benchmark all backends"
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Skip infrastructure deployment"
    )
    parser.add_argument(
        "--skip-docker",
        action="store_true",
        help="Skip Docker build/push"
    )
    parser.add_argument(
        "--benchmark-only",
        action="store_true",
        help="Only run benchmarks (skip deployment)"
    )
    parser.add_argument(
        "--destroy-after",
        action="store_true",
        help="Destroy infrastructure after benchmarking"
    )
    parser.add_argument(
        "--output-dir",
        default="./benchmark-results",
        help="Output directory for results (default: ./benchmark-results)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout in seconds for waiting for backends (default: 600)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.backends and not args.all_backends:
        parser.error("Must specify --backends or --all-backends")
    
    if args.all_backends:
        args.backends = list(BACKEND_CONFIGS.keys())
    
    # Create orchestrator
    orchestrator = VideolakeOrchestrator(vars(args))
    
    try:
        if not args.benchmark_only:
            # Infrastructure deployment
            if not args.skip_deploy:
                orchestrator.deploy_infrastructure(args.backends)
            
            # Docker image management
            if not args.skip_docker:
                needs_docker = any(
                    BACKEND_CONFIGS[b].get("requires_docker", False)
                    for b in args.backends
                )
                if needs_docker:
                    orchestrator.build_and_push_docker()
            
            # Wait for backends to be ready
            orchestrator.wait_for_backends(args.backends, timeout=args.timeout)
        
        # Run benchmarks
        orchestrator.run_benchmarks(args.backends)
        
        # Collect and report results
        orchestrator.collect_results()
        orchestrator.generate_report()
        
        orchestrator.logger.info("✓ Orchestration completed successfully!")
        
        # Cleanup if requested
        if args.destroy_after:
            orchestrator.cleanup(destroy=True)
        
        return 0
    
    except Exception as e:
        orchestrator.logger.error(f"✗ Orchestration failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())