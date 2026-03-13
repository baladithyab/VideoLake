"""
Ingestion API Routes.

This module provides API endpoints for triggering video ingestion jobs.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config.unified_config_manager import get_config
from src.ingestion.dataset_downloader import DatasetType
from src.ingestion.pipeline import (
    BatchIngestionConfig,
    BatchIngestionPipeline,
    VideoIngestionPipeline,
)
from src.services.embedding_provider import ModalityType
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.services.video_dataset_manager import VideoDatasetManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

class IngestionRequest(BaseModel):
    """Request model for starting an ingestion job."""
    video_path: str
    model_type: str = "marengo"
    backend_types: list[str] | None = None

class IngestionResponse(BaseModel):
    """Response model for ingestion job status."""
    job_id: str
    status: str
    message: str

class IngestionStatusResponse(BaseModel):
    """Response model for detailed ingestion job status."""
    status: str
    start_date: str
    stop_date: str | None = None
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None

class UploadUrlRequest(BaseModel):
    """Request model for getting a presigned upload URL."""
    filename: str
    content_type: str = "video/mp4"

class UploadUrlResponse(BaseModel):
    """Response model for presigned upload URL."""
    upload_url: str
    s3_uri: str
    expires_in: int

@router.get("/datasets", response_model=list[dict[str, Any]])
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
        import os
        import uuid

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

            # Wrap blocking boto3 call
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


# ============================================================================
# Batch Ingestion API (New - for 10K+ items)
# ============================================================================

class BatchIngestionRequest(BaseModel):
    """Request model for batch ingestion of large datasets."""
    items: list[str]  # List of content items, file paths, or S3 URIs
    modality: str  # text, image, audio, video
    provider_name: str = "bedrock"
    model_id: str | None = None
    backend_types: list[str] | None = None
    batch_size: int = 100
    max_concurrent_batches: int = 5
    enable_checkpointing: bool = True
    job_name: str | None = None


class BatchIngestionResponse(BaseModel):
    """Response model for batch ingestion."""
    job_id: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    total_batches: int
    completed_batches: int
    processing_time_seconds: float
    cost_estimate: float
    message: str
    embeddings_generated: int


class DatasetIngestionRequest(BaseModel):
    """Request model for ingesting recommended datasets."""
    dataset_type: str  # ms_marco, coco, librispeech, msr_vtt
    provider_name: str = "bedrock"
    model_id: str | None = None
    backend_types: list[str] | None = None
    download_if_missing: bool = True
    stage_to_s3: bool = False


class CheckpointStatusResponse(BaseModel):
    """Response model for checkpoint status."""
    job_id: str
    job_name: str
    status: str
    progress_percentage: float
    processed_items: int
    failed_items: int
    total_items: int
    current_batch: int
    total_batches: int
    elapsed_seconds: float
    items_per_second: float
    eta_seconds: float
    cost_estimate: float | None
    error_message: str | None


@router.post("/batch/start", response_model=BatchIngestionResponse)
async def start_batch_ingestion(request: BatchIngestionRequest):
    """
    Start a batch ingestion job for large-scale datasets (10K-100K items).

    This endpoint processes large volumes of items with:
    - Configurable batch processing and chunking
    - Rate limiting and retry logic for AWS services
    - Checkpoint/resume for long-running jobs
    - Progress tracking and cost estimation
    - Support for all modalities (text, image, audio, video)

    Example:
        ```json
        {
            "items": ["s3://bucket/item1.txt", "s3://bucket/item2.txt", ...],
            "modality": "text",
            "provider_name": "bedrock",
            "batch_size": 100,
            "max_concurrent_batches": 5
        }
        ```
    """
    try:
        # Validate modality
        try:
            modality = ModalityType(request.modality.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid modality: {request.modality}. "
                       f"Must be one of: text, image, audio, video"
            )

        # Validate minimum items
        if len(request.items) < 10:
            raise HTTPException(
                status_code=400,
                detail="Batch ingestion requires at least 10 items. "
                       "Use /start endpoint for single items."
            )

        # Create pipeline config
        config = BatchIngestionConfig(
            batch_size=request.batch_size,
            max_concurrent_batches=request.max_concurrent_batches,
            enable_checkpointing=request.enable_checkpointing
        )

        # Initialize pipeline
        pipeline = BatchIngestionPipeline(config=config)

        # Start ingestion
        result = await pipeline.ingest_items(
            items=request.items,
            modality=modality,
            provider_name=request.provider_name,
            model_id=request.model_id,
            backend_types=request.backend_types,
            job_name=request.job_name
        )

        return BatchIngestionResponse(
            job_id=result.job_id,
            status=result.status,
            total_items=result.total_items,
            processed_items=result.processed_items,
            failed_items=result.failed_items,
            total_batches=result.total_batches,
            completed_batches=result.completed_batches,
            processing_time_seconds=result.processing_time_seconds,
            cost_estimate=result.cost_estimate,
            message=result.message,
            embeddings_generated=result.embeddings_generated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start batch ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dataset/ingest", response_model=BatchIngestionResponse)
async def ingest_dataset(request: DatasetIngestionRequest):
    """
    Ingest a recommended large-scale dataset.

    Supported datasets:
    - `ms_marco`: 8.8M text passages from Bing search results
    - `coco`: 118K images with object detection annotations
    - `librispeech`: 104K audio clips (360 hours of speech)
    - `msr_vtt`: 10K videos with natural language descriptions

    The dataset will be downloaded (if not cached), optionally staged to S3,
    and ingested with batch processing.

    Example:
        ```json
        {
            "dataset_type": "ms_marco",
            "provider_name": "bedrock",
            "download_if_missing": true,
            "stage_to_s3": false
        }
        ```
    """
    try:
        # Validate dataset type
        try:
            dataset_type = DatasetType(request.dataset_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dataset type: {request.dataset_type}. "
                       f"Must be one of: ms_marco, coco, librispeech, msr_vtt"
            )

        # Initialize pipeline
        pipeline = BatchIngestionPipeline()

        # Start dataset ingestion
        result = await pipeline.ingest_dataset(
            dataset_type=dataset_type,
            provider_name=request.provider_name,
            model_id=request.model_id,
            backend_types=request.backend_types,
            download_if_missing=request.download_if_missing,
            stage_to_s3=request.stage_to_s3
        )

        return BatchIngestionResponse(
            job_id=result.job_id,
            status=result.status,
            total_items=result.total_items,
            processed_items=result.processed_items,
            failed_items=result.failed_items,
            total_batches=result.total_batches,
            completed_batches=result.completed_batches,
            processing_time_seconds=result.processing_time_seconds,
            cost_estimate=result.cost_estimate,
            message=result.message,
            embeddings_generated=result.embeddings_generated
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest dataset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/available", response_model=list[dict[str, Any]])
async def list_available_datasets():
    """
    List all available recommended datasets for ingestion.

    Returns dataset metadata including:
    - Name and description
    - Modality (text, image, audio, video)
    - Size (GB) and item count
    - License information
    - Download URLs

    These datasets are vetted for large-scale benchmarking and testing.
    """
    try:
        return BatchIngestionPipeline.list_available_datasets()
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/checkpoint/{job_id}", response_model=CheckpointStatusResponse)
async def get_checkpoint_status(job_id: str):
    """
    Get checkpoint status for a batch ingestion job.

    Returns detailed progress information including:
    - Processing status and progress percentage
    - Items processed and failed
    - Processing speed and ETA
    - Cost estimation
    - Error messages (if any)

    Useful for monitoring long-running ingestion jobs.
    """
    try:
        pipeline = BatchIngestionPipeline()
        stats = pipeline.get_checkpoint_status(job_id)

        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"Checkpoint not found for job: {job_id}"
            )

        return CheckpointStatusResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get checkpoint status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/checkpoints", response_model=list[dict[str, Any]])
async def list_checkpoints():
    """
    List all checkpointed batch ingestion jobs.

    Returns a list of all jobs with checkpoint data, including
    completed, failed, and in-progress jobs.
    """
    try:
        pipeline = BatchIngestionPipeline()
        return pipeline.list_checkpoints()
    except Exception as e:
        logger.error(f"Failed to list checkpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/resume/{job_id}", response_model=dict[str, Any])
async def resume_batch_job(job_id: str):
    """
    Resume a failed or interrupted batch ingestion job.

    The job will continue from the last saved checkpoint, processing
    only the remaining batches.

    Returns:
        Information about whether the job can be resumed.
    """
    try:
        pipeline = BatchIngestionPipeline()

        if not pipeline.resume_job(job_id):
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} cannot be resumed. "
                       "It may be completed or not checkpointed."
            )

        return {
            "job_id": job_id,
            "status": "resumable",
            "message": "Job can be resumed. Use /batch/start with the same job_id."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check resume status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
