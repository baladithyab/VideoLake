import sys
import os
from pathlib import Path
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import json

# Add project root to path to allow importing scripts
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from scripts.benchmark_backend import BackendBenchmark
except ImportError:
    logging.warning("Could not import BackendBenchmark from scripts. Ensure the script is in the python path.")
    BackendBenchmark = None

logger = logging.getLogger(__name__)

class BenchmarkService:
    def __init__(self):
        self.jobs = {}
        # Use a thread pool to run blocking benchmark operations
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def start_benchmark(self, backends: List[str], config: Dict[str, Any]) -> str:
        """
        Start a benchmark job for the specified backends.
        
        Args:
            backends: List of backend names to benchmark (e.g., ["s3vector", "lancedb-s3"])
            config: Configuration dictionary containing:
                - operation: "index", "search", or "mixed" (default: "search")
                - vectors: Number of vectors for index (default: 1000)
                - queries: Number of queries for search (default: 100)
                - top_k: Top K results (default: 10)
                - dimension: Vector dimension (default: 1024)
                - duration: Duration for mixed workload (default: 60)
                - collection: Optional collection name
        
        Returns:
            job_id: Unique identifier for the benchmark job
        """
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "status": "pending",
            "backends": backends,
            "config": config,
            "results": {},
            "errors": []
        }
        
        # Run in background
        asyncio.create_task(self._run_benchmark_task(job_id, backends, config))
        return job_id

    async def _run_benchmark_task(self, job_id: str, backends: List[str], config: Dict[str, Any]):
        self.jobs[job_id]["status"] = "running"
        
        try:
            # Run benchmarks for each backend sequentially in the thread pool
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                self.executor, 
                self._execute_benchmarks, 
                backends, 
                config
            )
            
            self.jobs[job_id]["results"] = results
            self.jobs[job_id]["status"] = "completed"
        except Exception as e:
            logger.error(f"Benchmark job {job_id} failed: {e}")
            self.jobs[job_id]["status"] = "failed"
            self.jobs[job_id]["error"] = str(e)

    def _execute_benchmarks(self, backends: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Blocking function to execute benchmarks"""
        if not BackendBenchmark:
            raise RuntimeError("BackendBenchmark class not available")

        results = {}
        operation = config.get("operation", "search")
        
        for backend in backends:
            try:
                logger.info(f"Starting benchmark for {backend}...")
                
                # Initialize benchmark runner
                # We pass a copy of config to avoid modifying the original
                runner_config = config.copy()
                
                # Extract specific params
                collection = runner_config.get("collection")
                
                runner = BackendBenchmark(
                    backend=backend,
                    config=runner_config,
                    collection=collection
                )
                
                # Validate connectivity
                validation = runner.validate_backend()
                if not validation.get("accessible", False):
                    results[backend] = {
                        "success": False,
                        "error": f"Backend not accessible: {validation.get('error')}"
                    }
                    continue

                # Run operation
                if operation == "index":
                    vectors = int(runner_config.get("vectors", 1000))
                    dimension = int(runner_config.get("dimension", 1024))
                    res = runner.benchmark_index(vectors, dimension)
                elif operation == "search":
                    queries = int(runner_config.get("queries", 100))
                    top_k = int(runner_config.get("top_k", 10))
                    dimension = int(runner_config.get("dimension", 1024))
                    res = runner.benchmark_search(queries, top_k, dimension)
                elif operation == "mixed":
                    duration = int(runner_config.get("duration", 60))
                    dimension = int(runner_config.get("dimension", 1024))
                    res = runner.benchmark_mixed_workload(duration, dimension)
                else:
                    res = {"success": False, "error": f"Unknown operation: {operation}"}
                
                results[backend] = res
                
            except Exception as e:
                logger.error(f"Error benchmarking {backend}: {e}")
                results[backend] = {
                    "success": False,
                    "error": str(e)
                }
                
        return results

    def get_status(self, job_id: str) -> Dict[str, Any]:
        return self.jobs.get(job_id, {"status": "not_found"})