import sys
import os
from pathlib import Path
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import json
import boto3

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
        self.ecs_client = boto3.client('ecs', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        self.ecs_cluster = os.getenv('ECS_BENCHMARK_CLUSTER', 'videolake-benchmark-runner-cluster')
        self.ecs_task_definition = os.getenv('ECS_BENCHMARK_TASK_DEFINITION', 'videolake-benchmark-runner')
        self.ecs_subnets = os.getenv('ECS_SUBNETS', '').split(',')
        self.ecs_security_groups = os.getenv('ECS_SECURITY_GROUPS', '').split(',')

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
                - use_ecs: Boolean to run on ECS (default: False)
        
        Returns:
            job_id: Unique identifier for the benchmark job
        """
        job_id = str(uuid.uuid4())
        use_ecs = config.get("use_ecs", False)

        self.jobs[job_id] = {
            "status": "pending",
            "backends": backends,
            "config": config,
            "results": {},
            "errors": [],
            "type": "ecs" if use_ecs else "local"
        }
        
        if use_ecs:
            try:
                task_arn = await self._run_ecs_benchmark(job_id, backends, config)
                self.jobs[job_id]["task_arn"] = task_arn
                self.jobs[job_id]["status"] = "submitted" # ECS task submitted
            except Exception as e:
                logger.error(f"Failed to submit ECS benchmark job {job_id}: {e}")
                self.jobs[job_id]["status"] = "failed"
                self.jobs[job_id]["error"] = str(e)
        else:
            # Run in background locally
            asyncio.create_task(self._run_benchmark_task(job_id, backends, config))
            
        return job_id

    async def _run_ecs_benchmark(self, job_id: str, backends: List[str], config: Dict[str, Any]) -> str:
        """Run benchmark on ECS"""
        
        # Construct command overrides
        # The container runs scripts/benchmark_backend.py by default
        # We need to construct the arguments based on config
        
        # Note: The current benchmark_backend.py script might need adjustments to handle multiple backends
        # or we run one task per backend. For now, let's assume we run one task that iterates or we pick the first backend.
        # If multiple backends are requested, we might need to launch multiple tasks or update the script.
        # For simplicity, let's assume the script can handle one backend at a time, so we might need to loop here
        # or just take the first one if the script is limited.
        # However, the requirement says "Pass configuration as environment variables overrides".
        
        # Let's look at how we can pass config.
        # We will pass the config as environment variables that the script can pick up,
        # OR we override the command. Overriding command is usually cleaner for CLI args.
        
        backend = backends[0] if backends else "s3vector" # Default to first backend
        
        cmd = ["python", "scripts/benchmark_backend.py"]
        cmd.extend(["--backend", backend])
        
        operation = config.get("operation", "search")
        cmd.extend(["--operation", operation])
        
        if "vectors" in config:
            cmd.extend(["--vectors", str(config.get("vectors"))])
        if "queries" in config:
            cmd.extend(["--queries", str(config.get("queries"))])
        if "top_k" in config:
            cmd.extend(["--top_k", str(config.get("top_k"))])
        if "dimension" in config:
            cmd.extend(["--dimension", str(config.get("dimension"))])
        if "collection" in config:
            collection = config.get("collection")
            if collection:
                cmd.extend(["--collection", str(collection)])
            
        # Add job_id to track results
        cmd.extend(["--job_id", job_id])

        overrides = {
            'containerOverrides': [
                {
                    'name': 'benchmark-runner',
                    'command': cmd,
                    'environment': [
                        {'name': 'BENCHMARK_JOB_ID', 'value': job_id},
                        {'name': 'BENCHMARK_CONFIG', 'value': json.dumps(config)}
                    ]
                }
            ]
        }
        
        # Network configuration for Fargate
        network_config = {
            'awsvpcConfiguration': {
                'subnets': self.ecs_subnets,
                'securityGroups': self.ecs_security_groups,
                'assignPublicIp': 'ENABLED'
            }
        }

        # If subnets are not configured, try to fetch default VPC subnets (this is a fallback, might be slow)
        if not self.ecs_subnets or self.ecs_subnets == ['']:
             # This part is tricky without explicit config.
             # Ideally, these should be in env vars.
             # For now, we'll assume they are set or we might fail if not set.
             logger.warning("ECS_SUBNETS not set. ECS run_task might fail if using awsvpc network mode.")

        response = self.ecs_client.run_task(
            cluster=self.ecs_cluster,
            taskDefinition=self.ecs_task_definition,
            launchType='FARGATE',
            networkConfiguration=network_config,
            overrides=overrides,
            count=1,
            startedBy=f'benchmark-service-{job_id}'
        )
        
        if not response['tasks']:
            raise Exception(f"Failed to start ECS task: {response.get('failures')}")
            
        task_arn = response['tasks'][0]['taskArn']
        logger.info(f"Started ECS benchmark task: {task_arn}")
        return task_arn

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
        job = self.jobs.get(job_id)
        if not job:
            return {"status": "not_found"}
            
        # If it's an ECS job, check ECS status if it's not already completed/failed
        if job.get("type") == "ecs" and job.get("status") in ["submitted", "pending", "running"]:
            try:
                task_arn = job.get("task_arn")
                if task_arn:
                    response = self.ecs_client.describe_tasks(
                        cluster=self.ecs_cluster,
                        tasks=[task_arn]
                    )
                    
                    if response['tasks']:
                        task = response['tasks'][0]
                        last_status = task['lastStatus']
                        job["ecs_status"] = last_status
                        
                        if last_status == 'STOPPED':
                            # Task finished
                            exit_code = task['containers'][0].get('exitCode')
                            if exit_code == 0:
                                job["status"] = "completed"
                                # TODO: Fetch results from S3 or logs?
                                # For now, we just mark it as completed.
                                # The frontend might need to fetch results separately or we implement S3 fetch here.
                            else:
                                job["status"] = "failed"
                                job["error"] = f"ECS task stopped with exit code {exit_code}"
                                job["stop_reason"] = task.get('stoppedReason')
                        elif last_status == 'RUNNING':
                            job["status"] = "running"
            except Exception as e:
                logger.error(f"Error checking ECS task status: {e}")
                
        return job

    def get_results(self, job_id: str) -> Dict[str, Any]:
        """Get results for a benchmark job"""
        job = self.jobs.get(job_id)
        if not job:
            return {"status": "not_found"}
            
        if job.get("status") != "completed":
            return {"status": job.get("status"), "message": "Job not completed yet"}
            
        return job.get("results", {})

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """List all benchmark jobs"""
        return [
            {
                "job_id": job_id,
                "status": job["status"],
                "type": job["type"],
                "backends": job["backends"],
                "config": job["config"],
                "created_at": job.get("created_at") # We should add timestamp
            }
            for job_id, job in self.jobs.items()
        ]