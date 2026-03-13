"""
Ingestion API Routes.

This module provides API endpoints for triggering video ingestion jobs.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.ingestion.pipeline import VideoIngestionPipeline
from src.utils.logging_config import get_logger
from src.services.video_dataset_manager import VideoDatasetManager
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.config.unified_config_manager import get_config

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

class IngestionStatusResponse(BaseModel):
    """Response model for detailed ingestion job status."""
    status: str
    start_date: str
    stop_date: Optional[str] = None
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None

class UploadUrlRequest(BaseModel):
    """Request model for getting a presigned upload URL."""
    filename: str
    content_type: str = "video/mp4"

class UploadUrlResponse(BaseModel):
    """Response model for presigned upload URL."""
    upload_url: str
    s3_uri: str
    expires_in: int

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
            import asyncio
            url = await asyncio.to_thread(
                s3_service.s3.generate_presigned_url,
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
async def start_ingestion(request: IngestionRequest):
    """
    Start a video ingestion job.

    This endpoint accepts a video path (S3 URI) and configuration,
    and triggers the ingestion Step Function workflow.
    """
    try:
        # Basic validation
        if not request.video_path.startswith("s3://") and not request.video_path.startswith("dataset://"):
             raise HTTPException(status_code=400, detail="video_path must be a valid S3 URI or dataset:// URI")

        # Start ingestion via Step Function
        pipeline = VideoIngestionPipeline()
        result = pipeline.process_video(
            request.video_path,
            request.model_type,
            request.backend_types
        )

        return IngestionResponse(
            job_id=result.job_id,
            status=result.status,
            message=result.message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{execution_arn:path}", response_model=IngestionStatusResponse)
async def get_ingestion_status(execution_arn: str):
    """
    Get the status of an ingestion job (Step Function execution).
    """
    try:
        pipeline = VideoIngestionPipeline()
        status_info = pipeline.get_status(execution_arn)
        
        return IngestionStatusResponse(
            status=status_info['status'],
            start_date=status_info['startDate'],
            stop_date=status_info.get('stopDate'),
            input=status_info.get('input'),
            output=status_info.get('output')
        )
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))