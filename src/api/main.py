"""
FastAPI REST API for S3Vector Application.

This module provides REST API endpoints for the React frontend to interact
with all backend services.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging
import time

from src.services import (
    get_service_manager,
    StreamlitIntegrationConfig,
    MultiVectorCoordinator
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="S3Vector API",
    description="REST API for S3Vector Multi-Vector Search Platform",
    version="1.0.0"
)

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


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    start_time = time.time()

    # Log request details
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"Origin: {request.headers.get('origin', 'No origin header')}")

    # Process request
    response = await call_next(request)

    # Log response details
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} (took {process_time:.2f}s)")

    return response


# Global service manager instance
service_manager = None
coordinator = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global service_manager, coordinator
    try:
        integration_config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            default_vector_types=["visual-text", "visual-image", "audio"],
            max_concurrent_jobs=8,
            enable_performance_monitoring=True
        )
        service_manager = get_service_manager(integration_config)
        coordinator = service_manager.multi_vector_coordinator if service_manager else None
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
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "service_manager": service_manager is not None,
            "coordinator": coordinator is not None
        }
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

