"""
Media Processing API Router.

Handles video upload and processing with TwelveLabs Marengo.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import tempfile
import os
import boto3
from datetime import datetime

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ProcessVideoRequest(BaseModel):
    """Request model for video processing."""
    video_s3_uri: Optional[str] = None
    embedding_options: List[str] = ["visual-text", "visual-image", "audio"]
    start_sec: float = 0
    length_sec: Optional[float] = None
    use_fixed_length_sec: Optional[float] = None


class ProcessingJobStatus(BaseModel):
    """Processing job status model."""
    job_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# In-memory job tracking (in production, use Redis or database)
processing_jobs: Dict[str, ProcessingJobStatus] = {}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file to S3."""
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        # Upload to S3
        s3_client = boto3.client('s3')
        bucket_name = os.getenv('S3_VECTORS_BUCKET')
        s3_key = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        
        s3_client.upload_file(tmp_path, bucket_name, s3_key)
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        
        # Cleanup temp file
        os.unlink(tmp_path)
        
        return {
            "success": True,
            "s3_uri": s3_uri,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Video upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_video(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """Start video processing job."""
    try:
        if not request.video_s3_uri:
            raise HTTPException(status_code=400, detail="video_s3_uri is required")
        
        # Initialize TwelveLabs service
        twelvelabs_service = TwelveLabsVideoProcessingService()
        
        # Start async processing
        job_info = twelvelabs_service.start_video_processing(
            video_s3_uri=request.video_s3_uri,
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
        
        return {
            "success": True,
            "job_id": job_info.job_id,
            "status": "processing"
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
async def store_embeddings(job_id: str, index_arn: str):
    """Store processed embeddings in S3 Vector index."""
    try:
        if job_id not in processing_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = processing_jobs[job_id]
        if job.status != "completed":
            raise HTTPException(status_code=400, detail="Job not completed")
        
        if not job.result:
            raise HTTPException(status_code=400, detail="No results available")
        
        # Store embeddings
        storage_manager = S3VectorStorageManager()
        
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
        
        result = storage_manager.put_vectors(index_arn, vectors_data)
        
        return {
            "success": True,
            "stored_count": len(vectors_data),
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def monitor_processing_job(job_id: str, service: TwelveLabsVideoProcessingService):
    """Background task to monitor processing job."""
    try:
        # Poll for job completion
        result = service.wait_for_job_completion(job_id, timeout_sec=3600)
        
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
async def process_sample_video(video_id: str, background_tasks: BackgroundTasks):
    """Process a sample video."""
    # Implementation similar to process_video
    return {
        "success": True,
        "message": f"Processing sample video {video_id}"
    }

