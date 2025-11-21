"""
Ingestion API Routes.

This module provides API endpoints for triggering video ingestion jobs.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional

from src.ingestion.pipeline import VideoIngestionPipeline
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

class IngestionRequest(BaseModel):
    """Request model for starting an ingestion job."""
    video_path: str
    model_type: str = "marengo"
    backend_types: Optional[List[str]] = None

class IngestionResponse(BaseModel):
    """Response model for ingestion job status."""
    job_id: str
    status: str
    message: str

def run_ingestion_task(video_path: str, model_type: str, backend_types: Optional[List[str]]):
    """Background task to run the ingestion pipeline."""
    try:
        pipeline = VideoIngestionPipeline()
        result = pipeline.process_video(video_path, model_type, backend_types)
        logger.info(f"Ingestion job {result.job_id} completed with status: {result.status}")
    except Exception as e:
        logger.error(f"Background ingestion task failed: {e}", exc_info=True)

@router.post("/start", response_model=IngestionResponse)
async def start_ingestion(request: IngestionRequest, background_tasks: BackgroundTasks):
    """
    Start a video ingestion job.

    This endpoint accepts a video path (S3 URI) and configuration,
    and starts the ingestion process in the background.
    """
    try:
        # Basic validation
        if not request.video_path.startswith("s3://"):
             raise HTTPException(status_code=400, detail="video_path must be a valid S3 URI")

        # Start background task
        background_tasks.add_task(
            run_ingestion_task, 
            request.video_path, 
            request.model_type, 
            request.backend_types
        )

        return IngestionResponse(
            job_id="pending", # In a real system, we'd generate and return a job ID here
            status="accepted",
            message=f"Ingestion started for {request.video_path}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))