from fastapi import FastAPI, HTTPException, Body, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from src.backend.vector_store_manager import VectorStoreManager, VectorStoreType
from src.backend.ingestion_service import IngestionService
from src.backend.benchmark_service import BenchmarkService

app = FastAPI(
    title="VideoLake API",
    description="Unified multi-modal video search and analytics platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize VectorStoreManager
manager = VectorStoreManager()
ingestion_service = IngestionService()
benchmark_service = BenchmarkService()

# Pydantic models
class BackendConfig(BaseModel):
    backend_type: VectorStoreType

class SearchRequest(BaseModel):
    query_vector: List[float]
    top_k: int = 10
    collection: Optional[str] = None

class BenchmarkRequest(BaseModel):
    backends: List[str]
    config: Dict[str, Any] = {}

class ProcessVideoRequest(BaseModel):
    s3_key: str
    model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    bucket_name: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "VideoLake API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "backend_health": manager.health_check()}

@app.get("/config")
async def get_config():
    """Return available backends and active backend."""
    return {
        "available_backends": manager.get_available_backends(),
        "active_backend": manager.active_backend
    }

@app.post("/config/backend")
async def switch_backend(config: BackendConfig):
    """Switch active backend."""
    try:
        manager.set_active_backend(config.backend_type)
        return {"message": f"Switched to {config.backend_type}", "active_backend": config.backend_type}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/search")
async def search(request: SearchRequest):
    """Perform vector search."""
    try:
        results = manager.search_vectors(request.query_vector, request.top_k, request.collection)
        return {"results": results}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/upload")
async def upload_video(file: UploadFile = File(...), bucket_name: Optional[str] = None):
    """Upload a video file to S3."""
    return await ingestion_service.upload_video(file, bucket_name)

@app.post("/ingest/process")
async def process_video(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    """Process a video using TwelveLabs Marengo model."""
    # We can run this in background if needed, but for now we'll await it to return results immediately
    # or we can use background_tasks.add_task(ingestion_service.process_video, ...)
    # Given the requirement to "Parse results" and "Upsert", it might be better to wait or return a job ID.
    # The prompt implies a synchronous flow or at least initiating it.
    # Since process_video in IngestionService is async and handles the heavy lifting (including waiting for Bedrock),
    # we should probably run it in the background for a real API, but for this task, let's await it to show completion.
    # However, Bedrock async invoke can take time.
    # Let's await it for simplicity as per the "Implement process_video" instruction which implies a direct call.
    
    return await ingestion_service.process_video(request.s3_key, request.model_id, request.bucket_name)

@app.post("/benchmark/start")
async def start_benchmark(request: BenchmarkRequest):
    """Start a benchmark job."""
    job_id = await benchmark_service.start_benchmark(request.backends, request.config)
    return {"job_id": job_id, "status": "pending"}

@app.get("/benchmark/status/{job_id}")
async def get_benchmark_status(job_id: str):
    """Get the status of a benchmark job."""
    status = benchmark_service.get_status(job_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Job not found")
    return status