"""
Comprehensive Benchmarks API Router (NEW).

Handles comprehensive benchmark suite with 10 dimensions across all vector DB variants.
This is separate from the legacy benchmark.py router.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import asyncio
from datetime import datetime

from src.services.benchmark_models import (
    BenchmarkConfiguration,
    BenchmarkStatus,
    ComprehensiveBenchmarkResult,
    BenchmarkComparison
)
from src.services.comprehensive_benchmark_runner import ComprehensiveBenchmarkRunner
from src.services.benchmark_report_generator import BenchmarkReportGenerator
from src.utils.logging_config import get_logger

# Import backend adapters
try:
    from scripts.backend_adapters import get_backend_adapter
except ImportError:
    get_backend_adapter = None

logger = get_logger(__name__)

router = APIRouter(tags=["Comprehensive Benchmarks"])

# In-memory job storage (will be replaced by persistent storage from bench-storage-builder)
active_jobs: Dict[str, Dict[str, Any]] = {}
completed_results: Dict[str, ComprehensiveBenchmarkResult] = {}


class ComprehensiveBenchmarkRequest(BaseModel):
    """Request to start a comprehensive benchmark"""
    backends: List[str] = Field(..., description="List of backend names (e.g., ['s3vector', 'qdrant-ecs', 'lancedb-s3'])")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Benchmark configuration")


class BenchmarkJobResponse(BaseModel):
    """Response when starting a benchmark job"""
    job_id: str
    status: str
    backends: List[str]
    estimated_duration_minutes: Optional[int] = None


class BenchmarkStatusResponse(BaseModel):
    """Status of a running benchmark job"""
    job_id: str
    status: str
    backends: List[str]
    completed_backends: List[str]
    failed_backends: List[str]
    progress_percentage: float
    current_backend: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/comprehensive/start", response_model=BenchmarkJobResponse)
async def start_comprehensive_benchmark(
    request: ComprehensiveBenchmarkRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a comprehensive benchmark across multiple backends.

    Runs all 10 benchmark dimensions:
    1. Latency (p50/p95/p99)
    2. Throughput (QPS)
    3. Recall@k
    4. Indexing Speed
    5. Memory Efficiency
    6. Cost per Query
    7. Scaling
    8. Cold Start (serverless)
    9. Concurrent Load
    10. Storage Efficiency
    """
    if not get_backend_adapter:
        raise HTTPException(
            status_code=500,
            detail="Backend adapters not available. Ensure scripts/backend_adapters.py is present."
        )

    job_id = str(uuid.uuid4())

    # Parse configuration
    config = BenchmarkConfiguration(**request.config) if request.config else BenchmarkConfiguration()
    config.backends = request.backends

    # Store job metadata
    active_jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "backends": request.backends,
        "completed_backends": [],
        "failed_backends": [],
        "config": config.to_dict(),
        "created_at": datetime.utcnow().isoformat(),
        "results": {}
    }

    # Start benchmark in background
    background_tasks.add_task(run_comprehensive_benchmark, job_id, request.backends, config)

    # Estimate duration (rough estimate: 5-10 minutes per backend)
    estimated_minutes = len(request.backends) * 7

    return BenchmarkJobResponse(
        job_id=job_id,
        status="pending",
        backends=request.backends,
        estimated_duration_minutes=estimated_minutes
    )


async def run_comprehensive_benchmark(
    job_id: str,
    backends: List[str],
    config: BenchmarkConfiguration
):
    """
    Run comprehensive benchmark for all backends sequentially.
    This runs in the background.
    """
    job = active_jobs[job_id]
    job["status"] = "running"

    try:
        for backend in backends:
            logger.info(f"Starting benchmark for {backend} (job {job_id})")
            job["current_backend"] = backend

            try:
                # Parse backend name (format: "backend-variant" or just "backend")
                parts = backend.split("-", 1)
                backend_name = parts[0]
                variant = parts[1] if len(parts) > 1 else "default"

                # Get backend adapter
                adapter = get_backend_adapter(backend_name, config.to_dict())

                # Create runner
                runner = ComprehensiveBenchmarkRunner(
                    backend=backend_name,
                    variant=variant,
                    adapter=adapter,
                    config=config
                )

                # Run all benchmarks
                result = await runner.run_all_benchmarks()

                # Store result
                completed_results[f"{job_id}_{backend}"] = result
                job["results"][backend] = result.to_dict()
                job["completed_backends"].append(backend)

                logger.info(f"Completed benchmark for {backend} (job {job_id})")

            except Exception as e:
                logger.error(f"Benchmark failed for {backend}: {e}")
                job["failed_backends"].append(backend)
                job["results"][backend] = {
                    "backend": backend,
                    "status": "failed",
                    "error": str(e)
                }

            # Update progress
            total = len(backends)
            completed = len(job["completed_backends"]) + len(job["failed_backends"])
            job["progress_percentage"] = (completed / total) * 100

        # Mark job as completed
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"Benchmark job {job_id} completed")

    except Exception as e:
        logger.error(f"Benchmark job {job_id} failed: {e}")
        job["status"] = "failed"
        job["error_message"] = str(e)


@router.get("/comprehensive/status/{job_id}", response_model=BenchmarkStatusResponse)
async def get_benchmark_status(job_id: str):
    """
    Get the status of a comprehensive benchmark job.
    """
    job = active_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return BenchmarkStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        backends=job["backends"],
        completed_backends=job["completed_backends"],
        failed_backends=job["failed_backends"],
        progress_percentage=job.get("progress_percentage", 0),
        current_backend=job.get("current_backend"),
        error_message=job.get("error_message")
    )


@router.get("/comprehensive/results/{job_id}")
async def get_benchmark_results(job_id: str):
    """
    Get the complete results of a comprehensive benchmark job.
    Returns all 10 dimensions for each backend.
    """
    job = active_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] not in ["completed", "running"]:
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": "Job not completed yet"
        }

    return {
        "job_id": job_id,
        "status": job["status"],
        "backends": job["backends"],
        "completed_backends": job["completed_backends"],
        "failed_backends": job["failed_backends"],
        "results": job["results"],
        "created_at": job.get("created_at"),
        "completed_at": job.get("completed_at")
    }


@router.get("/comprehensive/comparison/{job_id}")
async def get_benchmark_comparison(job_id: str):
    """
    Get a comparison of all backends in a benchmark job.
    Includes winner by dimension and cost-performance rankings.
    """
    job = active_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # Build comparison
    comparison = BenchmarkComparison(job_id=job_id)

    for backend, result_dict in job["results"].items():
        if result_dict.get("status") == "failed":
            continue

        # Reconstruct result (simplified - in production would deserialize properly)
        # For now, just use the dict
        comparison.backends.append(backend)

    # Determine winners by dimension
    comparison.winner_by_dimension = _determine_winners(job["results"])

    # Calculate cost-performance rankings
    comparison.cost_performance_ranking = _calculate_cost_performance(job["results"])

    return comparison.to_dict()


@router.get("/comprehensive/report/{job_id}")
async def get_benchmark_report(
    job_id: str,
    format: str = Query("markdown", pattern="^(markdown|json|csv)$")
):
    """
    Generate a comprehensive benchmark report.

    Formats:
    - markdown: Full markdown report with tables and recommendations
    - json: Structured JSON data
    - csv: CSV export for spreadsheet analysis
    """
    job = active_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")

    # Build comparison
    comparison = BenchmarkComparison(job_id=job_id)
    results = []

    for backend, result_dict in job["results"].items():
        if result_dict.get("status") == "failed":
            continue
        # In production, properly deserialize ComprehensiveBenchmarkResult
        # For now, use dict representation
        comparison.backends.append(backend)

    # Generate report
    generator = BenchmarkReportGenerator()

    if format == "markdown":
        report = generator.generate_markdown_report(comparison)
        return {"format": "markdown", "report": report}

    elif format == "json":
        report = generator.generate_json_report(comparison)
        return {"format": "json", "report": report}

    elif format == "csv":
        report = generator.generate_csv_export(results)
        return {"format": "csv", "report": report}

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")


@router.get("/comprehensive/list")
async def list_benchmark_jobs(
    status: Optional[str] = Query(None, pattern="^(pending|running|completed|failed)$"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    List all benchmark jobs with optional status filtering.
    """
    jobs = list(active_jobs.values())

    # Filter by status if specified
    if status:
        jobs = [j for j in jobs if j["status"] == status]

    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    # Limit results
    jobs = jobs[:limit]

    # Return summary info
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "backends": j["backends"],
                "completed_backends": j["completed_backends"],
                "failed_backends": j["failed_backends"],
                "created_at": j.get("created_at"),
                "progress_percentage": j.get("progress_percentage", 0)
            }
            for j in jobs
        ]
    }


@router.delete("/comprehensive/{job_id}")
async def cancel_benchmark_job(job_id: str):
    """
    Cancel a running benchmark job.
    """
    job = active_jobs.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job["status"] not in ["pending", "running"]:
        raise HTTPException(status_code=400, detail=f"Job is {job['status']}, cannot cancel")

    job["status"] = "cancelled"
    job["cancelled_at"] = datetime.utcnow().isoformat()

    return {"message": f"Job {job_id} cancelled", "status": "cancelled"}


def _determine_winners(results: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Determine the winner for each benchmark dimension"""
    winners = {}

    # Find best latency
    best_latency = None
    best_latency_backend = None
    for backend, result in results.items():
        if result.get("latency"):
            p99 = result["latency"].get("p99_ms", float('inf'))
            if best_latency is None or p99 < best_latency:
                best_latency = p99
                best_latency_backend = backend

    if best_latency_backend:
        winners["latency"] = best_latency_backend

    # Find best throughput
    best_qps = None
    best_qps_backend = None
    for backend, result in results.items():
        if result.get("throughput"):
            qps = result["throughput"].get("qps", 0)
            if best_qps is None or qps > best_qps:
                best_qps = qps
                best_qps_backend = backend

    if best_qps_backend:
        winners["throughput"] = best_qps_backend

    # Find best cost
    best_cost = None
    best_cost_backend = None
    for backend, result in results.items():
        if result.get("cost"):
            monthly = result["cost"].get("monthly_cost_estimate_usd", float('inf'))
            if best_cost is None or monthly < best_cost:
                best_cost = monthly
                best_cost_backend = backend

    if best_cost_backend:
        winners["cost"] = best_cost_backend

    return winners


def _calculate_cost_performance(results: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate cost-performance ratio for ranking"""
    rankings = []

    for backend, result in results.items():
        if result.get("throughput") and result.get("cost"):
            qps = result["throughput"].get("qps", 0)
            monthly_cost = result["cost"].get("monthly_cost_estimate_usd", 1)

            if monthly_cost > 0:
                qps_per_dollar = qps / monthly_cost

                rankings.append({
                    "backend": backend,
                    "qps": qps,
                    "monthly_cost": monthly_cost,
                    "qps_per_dollar": qps_per_dollar
                })

    # Sort by QPS per dollar (descending)
    rankings.sort(key=lambda x: x["qps_per_dollar"], reverse=True)

    return rankings
