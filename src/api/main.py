"""
FastAPI REST API for S3Vector Application.

This module provides REST API endpoints for the React frontend to interact
with all backend services.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.similarity_search_engine import SimilaritySearchEngine
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger
from src.api.exception_handlers import register_exception_handlers
from src.api.middleware.observability import ObservabilityMiddleware, PerformanceLoggingMiddleware

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="S3Vector API",
    description="REST API for S3Vector Multi-Vector Search Platform",
    version="1.0.0"
)

# Register exception handlers
register_exception_handlers(app)

# Add observability middleware
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(PerformanceLoggingMiddleware, slow_request_threshold_ms=2000.0)

# Configure CORS - Allow requests from React frontend
# Allow all localhost ports for development (Vite can use any available port)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Global service instances
storage_manager = None
search_engine = None
twelvelabs_service = None
bedrock_service = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global storage_manager, search_engine, twelvelabs_service, bedrock_service
    try:
        # Initialize core services
        storage_manager = S3VectorStorageManager()
        search_engine = SimilaritySearchEngine()
        twelvelabs_service = TwelveLabsVideoProcessingService()
        bedrock_service = BedrockEmbeddingService()

        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "S3Vector API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """
    Deep health check endpoint.

    Checks:
    - Service initialization
    - AWS connectivity
    - External API availability
    """
    from datetime import datetime
    import os
    import requests

    checks = {}
    overall_healthy = True

    # Check service initialization
    checks["services"] = {
        "storage_manager": storage_manager is not None,
        "search_engine": search_engine is not None,
        "twelvelabs_service": twelvelabs_service is not None,
        "bedrock_service": bedrock_service is not None
    }

    if not all(checks["services"].values()):
        overall_healthy = False

    # Check AWS S3 connectivity
    try:
        if storage_manager:
            storage_manager.s3_client.list_buckets()
            checks["aws_s3"] = {"status": "healthy"}
        else:
            checks["aws_s3"] = {"status": "not_initialized"}
            overall_healthy = False
    except Exception as e:
        checks["aws_s3"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # Check TwelveLabs API
    try:
        api_key = os.getenv("TWELVE_LABS_API_KEY")
        if api_key:
            response = requests.get(
                "https://api.twelvelabs.io/v1.2/engines",
                headers={"x-api-key": api_key},
                timeout=5
            )
            checks["twelvelabs_api"] = {
                "status": "healthy" if response.status_code == 200 else "degraded",
                "status_code": response.status_code
            }
        else:
            checks["twelvelabs_api"] = {"status": "not_configured"}
    except Exception as e:
        checks["twelvelabs_api"] = {"status": "degraded", "error": str(e)}

    # Check AWS Bedrock
    try:
        if bedrock_service:
            # Quick check - list foundation models
            response = bedrock_service.bedrock_client.list_foundation_models()
            checks["aws_bedrock"] = {
                "status": "healthy",
                "models_available": len(response.get("modelSummaries", []))
            }
        else:
            checks["aws_bedrock"] = {"status": "not_initialized"}
            overall_healthy = False
    except Exception as e:
        checks["aws_bedrock"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


# Import routers
from .routers import (
    resources,
    processing,
    search,
    embeddings,
    analytics
)

# Include routers
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(processing.router, prefix="/api/processing", tags=["processing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])

