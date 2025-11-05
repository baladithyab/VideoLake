"""
Media Processing API Router.

Handles video upload and processing with TwelveLabs Marengo.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks, Depends
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
import tempfile
import os
import boto3
from datetime import datetime
import requests
import uuid

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.core.dependencies import get_storage_manager, get_twelvelabs_service
from src.api.validators import (
    validate_s3_uri,
    validate_index_arn,
    validate_embedding_options,
    VideoParametersValidator
)
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry
from src.utils.timing_tracker import TimingTracker

logger = get_logger(__name__)

router = APIRouter()


class ProcessVideoRequest(BaseModel):
    """Request model for video processing with enhanced validation."""
    video_s3_uri: Optional[str] = Field(
        None,
        description="S3 URI or HTTP URL of the video to process"
    )
    embedding_options: List[str] = Field(
        default=["visual-text", "visual-image", "audio"],
        description="Embedding options for video processing"
    )
    start_sec: float = Field(
        default=0,
        ge=0,
        description="Start time in seconds"
    )
    length_sec: Optional[float] = Field(
        None,
        ge=0,
        description="Length of video segment to process in seconds"
    )
    use_fixed_length_sec: Optional[float] = Field(
        None,
        ge=0,
        description="Fixed length for video clips in seconds"
    )

    @field_validator('video_s3_uri')
    @classmethod
    def validate_uri(cls, v):
        """Validate S3 URI if provided and it's an S3 URI."""
        if v and v.startswith('s3://'):
            return validate_s3_uri(v)
        return v

    @field_validator('embedding_options')
    @classmethod
    def validate_options(cls, v):
        return validate_embedding_options(v)


class ProcessingJobStatus(BaseModel):
    """Processing job status model."""
    job_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class StoreEmbeddingsRequest(BaseModel):
    """Request model for storing embeddings with enhanced validation."""
    job_id: str = Field(..., description="Processing job ID", min_length=1)
    index_arn: str = Field(..., description="S3 Vector index ARN")

    @field_validator('index_arn')
    @classmethod
    def validate_arn(cls, v):
        return validate_index_arn(v)


# In-memory job tracking (in production, use Redis or database)
processing_jobs: Dict[str, ProcessingJobStatus] = {}


def download_video_to_s3(http_url: str, video_id: str) -> str:
    """
    Download video from HTTP URL and upload to S3 media bucket.

    Args:
        http_url: HTTP URL of the video
        video_id: Unique identifier for the video

    Returns:
        S3 URI of the uploaded video
    """
    try:
        # Get media bucket from registry
        s3_buckets = resource_registry.list_s3_buckets()

        # Filter for media buckets (buckets with 'media' in the name or type)
        media_buckets = [
            b for b in s3_buckets
            if 'media' in b.get('name', '').lower() or b.get('bucket_type') == 'media'
        ]

        if not media_buckets:
            # Fallback: use any S3 bucket
            if not s3_buckets:
                raise ValueError("No S3 bucket found. Please create an S3 bucket first.")
            media_bucket = s3_buckets[0]["name"]
            logger.warning(f"No media bucket found, using first available bucket: {media_bucket}")
        else:
            media_bucket = media_buckets[0]["name"]

        # Download video from HTTP URL
        logger.info(f"Downloading video from {http_url}")
        response = requests.get(http_url, stream=True, timeout=300)
        response.raise_for_status()

        # Get file extension from URL
        file_ext = os.path.splitext(http_url.split('?')[0])[-1] or '.mp4'

        # Create S3 key
        s3_key = f"sample-videos/{video_id}{file_ext}"

        # Upload to S3
        s3_client = boto3.client('s3')
        logger.info(f"Uploading video to s3://{media_bucket}/{s3_key}")

        # Upload in chunks
        s3_client.upload_fileobj(
            response.raw,
            media_bucket,
            s3_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )

        s3_uri = f"s3://{media_bucket}/{s3_key}"
        logger.info(f"Video uploaded successfully to {s3_uri}")

        return s3_uri

    except Exception as e:
        logger.error(f"Failed to download video to S3: {e}")
        raise


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file to S3."""
    tracker = TimingTracker("video_upload")

    try:
        # Create temporary file
        with tracker.time_operation("create_temp_file"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name

        # Upload to S3
        with tracker.time_operation("s3_upload"):
            s3_client = boto3.client('s3')
            bucket_name = os.getenv('S3_VECTORS_BUCKET')
            s3_key = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"

            s3_client.upload_file(tmp_path, bucket_name, s3_key)
            s3_uri = f"s3://{bucket_name}/{s3_key}"

        # Cleanup temp file
        os.unlink(tmp_path)

        report = tracker.finish()

        return {
            "success": True,
            "s3_uri": s3_uri,
            "filename": file.filename,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_video(
    request: ProcessVideoRequest,
    background_tasks: BackgroundTasks,
    twelvelabs_service: TwelveLabsVideoProcessingService = Depends(get_twelvelabs_service)
):
    """Start video processing job."""
    tracker = TimingTracker("video_processing")

    try:
        if not request.video_s3_uri:
            raise HTTPException(status_code=400, detail="video_s3_uri is required")

        video_uri = request.video_s3_uri

        # If the URI is an HTTP URL, download to S3 first
        if video_uri.startswith('http://') or video_uri.startswith('https://'):
            with tracker.time_operation("download_video_to_s3"):
                logger.info(f"Detected HTTP URL, downloading to S3: {video_uri}")
                video_id = str(uuid.uuid4())
                video_uri = download_video_to_s3(video_uri, video_id)
                logger.info(f"Downloaded to S3: {video_uri}")

        # Start async processing
        with tracker.time_operation("start_twelvelabs_processing"):
            job_info = twelvelabs_service.start_video_processing(
                video_s3_uri=video_uri,
                embedding_options=request.embedding_options,
                start_sec=request.start_sec,
                length_sec=request.length_sec,
                use_fixed_length_sec=request.use_fixed_length_sec
            )

        # Track job
        job_status = ProcessingJobStatus(
            job_id=job_info.job_id,
            status="processing",
            progress=0.0
        )
        processing_jobs[job_info.job_id] = job_status

        # Add background task to monitor job
        background_tasks.add_task(monitor_processing_job, job_info.job_id, twelvelabs_service)

        report = tracker.finish()

        return {
            "success": True,
            "job_id": job_info.job_id,
            "status": "processing",
            "s3_uri": video_uri,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Video processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get processing job status."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "success": True,
        "job": processing_jobs[job_id].dict()
    }


@router.get("/jobs")
async def list_jobs():
    """List all processing jobs."""
    return {
        "success": True,
        "jobs": [job.dict() for job in processing_jobs.values()]
    }


@router.post("/store-embeddings")
async def store_embeddings(
    request: StoreEmbeddingsRequest,
    storage_manager: S3VectorStorageManager = Depends(get_storage_manager)
):
    """Store processed embeddings in S3 Vector index."""
    tracker = TimingTracker("store_embeddings")

    try:
        with tracker.time_operation("validate_job"):
            if request.job_id not in processing_jobs:
                raise HTTPException(status_code=404, detail="Job not found")

            job = processing_jobs[request.job_id]
            if job.status != "completed":
                raise HTTPException(status_code=400, detail="Job not completed")

            if not job.result:
                raise HTTPException(status_code=400, detail="No results available")

        # Store embeddings
        with tracker.time_operation("prepare_vectors"):

            # Extract vectors from result
            vectors_data = []
            for segment in job.result.get('segments', []):
                vectors_data.append({
                    'id': segment.get('segment_id'),
                    'vector': segment.get('embedding'),
                    'metadata': {
                        'video_id': job.result.get('video_id'),
                        'start_sec': segment.get('start_offset_sec'),
                        'end_sec': segment.get('end_offset_sec'),
                        'embedding_option': segment.get('embedding_option')
                    }
                })

        with tracker.time_operation("s3vector_put_vectors"):
            result = storage_manager.put_vectors(request.index_arn, vectors_data)

        report = tracker.finish()

        return {
            "success": True,
            "stored_count": len(vectors_data),
            "result": result,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def monitor_processing_job(job_id: str, service: TwelveLabsVideoProcessingService):
    """Background task to monitor processing job."""
    try:
        # Poll for job completion (use correct method name)
        result = service.wait_for_completion(job_id, timeout_sec=3600)

        # Update job status
        if job_id in processing_jobs:
            processing_jobs[job_id].status = "completed"
            processing_jobs[job_id].progress = 100.0
            processing_jobs[job_id].result = {
                "video_id": result.video_id,
                "segments": [
                    {
                        "segment_id": seg.segment_id,
                        "start_offset_sec": seg.start_offset_sec,
                        "end_offset_sec": seg.end_offset_sec,
                        "embedding_option": seg.embedding_option,
                        "embedding": seg.embedding
                    }
                    for seg in result.segments
                ]
            }
            logger.info(f"Job {job_id} completed successfully with {len(result.segments)} segments")
    except Exception as e:
        logger.error(f"Job monitoring failed for {job_id}: {e}")
        if job_id in processing_jobs:
            processing_jobs[job_id].status = "failed"
            processing_jobs[job_id].error = str(e)


@router.get("/sample-videos")
async def get_sample_videos():
    """Get list of Creative Commons sample videos from Google/Blender collections."""
    return {
        "success": True,
        "categories": [
            {
                "name": "Movies",
                "videos": [
                    {
                        "id": "big-buck-bunny",
                        "title": "Big Buck Bunny",
                        "description": "Big Buck Bunny tells the story of a giant rabbit with a heart bigger than himself. When one sunny day three rodents rudely harass him, something snaps... and the rabbit ain't no bunny anymore! In the typical cartoon tradition he prepares the nasty rodents a comical revenge.\n\nLicensed under the Creative Commons Attribution license\nhttp://www.bigbuckbunny.org",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"],
                        "subtitle": "By Blender Foundation",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/BigBuckBunny.jpg"
                    },
                    {
                        "id": "elephants-dream",
                        "title": "Elephant Dream",
                        "description": "The first Blender Open Movie from 2006",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"],
                        "subtitle": "By Blender Foundation",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ElephantsDream.jpg"
                    },
                    {
                        "id": "for-bigger-blazes",
                        "title": "For Bigger Blazes",
                        "description": "HBO GO now works with Chromecast -- the easiest way to enjoy online video on your TV. For when you want to settle into your Iron Throne to watch the latest episodes. For $35.\nLearn how to use Chromecast with HBO GO and more at google.com/chromecast.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"],
                        "subtitle": "By Google",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerBlazes.jpg"
                    },
                    {
                        "id": "for-bigger-escape",
                        "title": "For Bigger Escape",
                        "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for when Batman's escapes aren't quite big enough. For $35. Learn how to use Chromecast with Google Play Movies and more at google.com/chromecast.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"],
                        "subtitle": "By Google",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerEscapes.jpg"
                    },
                    {
                        "id": "for-bigger-fun",
                        "title": "For Bigger Fun",
                        "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV. For $35. Find out more at google.com/chromecast.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4"],
                        "subtitle": "By Google",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerFun.jpg"
                    },
                    {
                        "id": "for-bigger-joyrides",
                        "title": "For Bigger Joyrides",
                        "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for the times that call for bigger joyrides. For $35. Learn how to use Chromecast with YouTube and more at google.com/chromecast.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"],
                        "subtitle": "By Google",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerJoyrides.jpg"
                    },
                    {
                        "id": "for-bigger-meltdowns",
                        "title": "For Bigger Meltdowns",
                        "description": "Introducing Chromecast. The easiest way to enjoy online video and music on your TV—for when you want to make Buster's big meltdowns even bigger. For $35. Learn how to use Chromecast with Netflix and more at google.com/chromecast.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"],
                        "subtitle": "By Google",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerMeltdowns.jpg"
                    },
                    {
                        "id": "sintel",
                        "title": "Sintel",
                        "description": "Sintel is an independently produced short film, initiated by the Blender Foundation as a means to further improve and validate the free/open source 3D creation suite Blender. With initial funding provided by 1000s of donations via the internet community, it has again proven to be a viable development model for both open 3D technology as for independent animation film.\nThis 15 minute film has been realized in the studio of the Amsterdam Blender Institute, by an international team of artists and developers. In addition to that, several crucial technical and creative targets have been realized online, by developers and artists and teams all over the world.\nwww.sintel.org",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4"],
                        "subtitle": "By Blender Foundation",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/Sintel.jpg"
                    },
                    {
                        "id": "subaru-outback",
                        "title": "Subaru Outback On Street And Dirt",
                        "description": "Smoking Tire takes the all-new Subaru Outback to the highest point we can find in hopes our customer-appreciation Balloon Launch will get some free T-shirts into the hands of our viewers.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4"],
                        "subtitle": "By Garage419",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/SubaruOutbackOnStreetAndDirt.jpg"
                    },
                    {
                        "id": "tears-of-steel",
                        "title": "Tears of Steel",
                        "description": "Tears of Steel was realized with crowd-funding by users of the open source 3D creation tool Blender. Target was to improve and test a complete open and free pipeline for visual effects in film - and to make a compelling sci-fi film in Amsterdam, the Netherlands. The film itself, and all raw material used for making it, have been released under the Creatieve Commons 3.0 Attribution license. Visit the tearsofsteel.org website to find out more about this, or to purchase the 4-DVD box with a lot of extras. (CC) Blender Foundation - http://www.tearsofsteel.org",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"],
                        "subtitle": "By Blender Foundation",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/TearsOfSteel.jpg"
                    },
                    {
                        "id": "volkswagen-gti",
                        "title": "Volkswagen GTI Review",
                        "description": "The Smoking Tire heads out to Adams Motorsports Park in Riverside, CA to test the most requested car of 2010, the Volkswagen GTI. Will it beat the Mazdaspeed3's standard-setting lap time? Watch and see...",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/VolkswagenGTIReview.mp4"],
                        "subtitle": "By Garage419",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/VolkswagenGTIReview.jpg"
                    },
                    {
                        "id": "bullrun",
                        "title": "We Are Going On Bullrun",
                        "description": "The Smoking Tire is going on the 2010 Bullrun Live Rally in a 2011 Shelby GT500, and posting a video from the road every single day! The only place to watch them is by subscribing to The Smoking Tire or watching at BlackMagicShine.com",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4"],
                        "subtitle": "By Garage419",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/WeAreGoingOnBullrun.jpg"
                    },
                    {
                        "id": "cars-for-grand",
                        "title": "What care can you get for a grand?",
                        "description": "The Smoking Tire meets up with Chris and Jorge from CarsForAGrand.com to see just how far $1,000 can go when looking for a car.The Smoking Tire meets up with Chris and Jorge from CarsForAGrand.com to see just how far $1,000 can go when looking for a car.",
                        "sources": ["http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WhatCarCanYouGetForAGrand.mp4"],
                        "subtitle": "By Garage419",
                        "thumb": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/images/WhatCarCanYouGetForAGrand.jpg"
                    }
                ]
            }
        ]
    }


@router.post("/process-sample")
async def process_sample_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    twelvelabs_service: TwelveLabsVideoProcessingService = Depends(get_twelvelabs_service),
    embedding_options: List[str] = ["visual-text", "visual-image", "audio"]
):
    """
    Process a sample video by downloading it to S3 first, then processing.

    This endpoint:
    1. Finds the sample video by ID
    2. Downloads it from HTTP URL to S3 media bucket
    3. Starts TwelveLabs processing with the S3 URI
    """
    try:
        # Get sample videos data
        sample_videos_response = await get_sample_videos()
        all_videos = sample_videos_response["categories"][0]["videos"]

        # Find the requested video
        video = next((v for v in all_videos if v["id"] == video_id), None)
        if not video:
            raise HTTPException(status_code=404, detail=f"Sample video '{video_id}' not found")

        # Download video to S3
        logger.info(f"Downloading sample video '{video['title']}' to S3")
        http_url = video["sources"][0]
        s3_uri = download_video_to_s3(http_url, video_id)

        # Start async processing with S3 URI
        job_info = twelvelabs_service.start_video_processing(
            video_s3_uri=s3_uri,
            embedding_options=embedding_options,
            start_sec=0,
            use_fixed_length_sec=5.0
        )

        # Track job
        job_status = ProcessingJobStatus(
            job_id=job_info.job_id,
            status="processing",
            progress=0.0
        )
        processing_jobs[job_info.job_id] = job_status

        # Add background task to monitor job
        background_tasks.add_task(monitor_processing_job, job_info.job_id, twelvelabs_service)

        return {
            "success": True,
            "job_id": job_info.job_id,
            "status": "processing",
            "video_title": video["title"],
            "s3_uri": s3_uri
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process sample video: {e}")
        raise HTTPException(status_code=500, detail=str(e))

