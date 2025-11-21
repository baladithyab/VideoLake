"""
Ingestion API Routes.

This module provides API endpoints for triggering video ingestion jobs.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.ingestion.pipeline import VideoIngestionPipeline
from src.utils.logging_config import get_logger
from src.services.video_dataset_manager import VideoDatasetManager
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.config.app_config import get_config

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

class UploadUrlRequest(BaseModel):
    """Request model for getting a presigned upload URL."""
    filename: str
    content_type: str = "video/mp4"

class UploadUrlResponse(BaseModel):
    """Response model for presigned upload URL."""
    upload_url: str
    s3_uri: str
    expires_in: int

def run_ingestion_task(video_path: str, model_type: str, backend_types: Optional[List[str]]):
    """Background task to run the ingestion pipeline."""
    try:
        pipeline = VideoIngestionPipeline()
        result = pipeline.process_video(video_path, model_type, backend_types)
        logger.info(f"Ingestion job {result.job_id} completed with status: {result.status}")
    except Exception as e:
        logger.error(f"Background ingestion task failed: {e}", exc_info=True)

@router.get("/datasets", response_model=List[Dict[str, Any]])
async def list_datasets():
    """
    List available video datasets.
    """
    try:
        return VideoDatasetManager.list_available_datasets()
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(request: UploadUrlRequest):
    """
    Get a presigned S3 URL for uploading a video file.
    """
    try:
        config = get_config()
        s3_service = S3BucketUtilityService()
        
        # Use configured bucket or default
        bucket_name = config.aws.s3_bucket
        
        # Generate a unique key for the upload
        import uuid
        import os
        
        # Sanitize filename
        filename = os.path.basename(request.filename)
        file_id = str(uuid.uuid4())
        key = f"uploads/{file_id}/{filename}"
        s3_uri = f"s3://{bucket_name}/{key}"
        
        # Generate presigned URL for PUT operation
        # Note: S3BucketUtilityService.generate_presigned_url is for GET (download)
        # We need to use the underlying client for PUT (upload)
        
        try:
            url = s3_service.s3.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': key,
                    'ContentType': request.content_type
                },
                ExpiresIn=3600
            )
            
            return UploadUrlResponse(
                upload_url=url,
                s3_uri=s3_uri,
                expires_in=3600
            )
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate upload URL")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get upload URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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