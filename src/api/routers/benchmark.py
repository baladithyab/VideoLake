"""
Benchmark API Router.

Handles benchmark jobs for vector store backends.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from src.services.benchmark_service import BenchmarkService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Initialize benchmark service
benchmark_service = BenchmarkService()

class BenchmarkRequest(BaseModel):
    backends: List[str]
    config: Dict[str, Any] = {}

@router.post("/start")
async def start_benchmark(request: BenchmarkRequest):
    """
    Start a benchmark job.
    
    Config options:
    - operation: "index", "search", or "mixed"
    - vectors: int
    - queries: int
    - top_k: int
    - dimension: int
    - duration: int
    - collection: str
    - use_ecs: bool (default: False) - Run on ECS
    """
    try:
        job_id = await benchmark_service.start_benchmark(request.backends, request.config)
        return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        logger.error(f"Failed to start benchmark: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}")
async def get_benchmark_status(job_id: str):
    """Get the status of a benchmark job."""
    status = benchmark_service.get_status(job_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return status

@router.get("/results/{job_id}")
async def get_benchmark_results(job_id: str):
    """Get the results of a benchmark job."""
    results = benchmark_service.get_results(job_id)
    if results.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return results

@router.get("/list")
async def list_benchmarks():
    """List all benchmark jobs."""
    return benchmark_service.list_benchmarks()