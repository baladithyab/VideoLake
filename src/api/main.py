"""
FastAPI REST API for Videolake Application.

This module provides REST API endpoints for the React frontend to interact
with all backend services including multiple vector store backends.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager
import logging

from src.utils.logging_config import get_logger
from src.api.exception_handlers import register_exception_handlers
from src.api.middleware.observability import ObservabilityMiddleware, PerformanceLoggingMiddleware
from src.core.dependencies import initialize_services, cleanup_services

logger = get_logger(__name__)


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup and shutdown.

    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown").
    """
    # Startup
    try:
        await initialize_services()
        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        await cleanup_services()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# Create FastAPI app with lifespan
app = FastAPI(
    title="S3Vector API",
    description="REST API for S3Vector Multi-Vector Search Platform",
    version="1.0.0",
    lifespan=lifespan
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
    from src.core.dependencies import (
        get_storage_manager,
        get_search_engine,
        get_twelvelabs_service,
        get_bedrock_service
    )

    checks = {}
    overall_healthy = True

    # Check service initialization
    try:
        storage_manager = get_storage_manager()
        search_engine = get_search_engine()
        twelvelabs_service = get_twelvelabs_service()
        bedrock_service = get_bedrock_service()

        checks["services"] = {
            "storage_manager": True,
            "search_engine": True,
            "twelvelabs_service": True,
            "bedrock_service": True
        }
    except Exception as e:
        checks["services"] = {"error": str(e)}
        overall_healthy = False

    # Check AWS S3 connectivity
    try:
        storage_manager.s3_client.list_buckets()
        checks["aws_s3"] = {"status": "healthy"}
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
        # Quick check - list foundation models
        response = bedrock_service.bedrock_client.list_foundation_models()
        checks["aws_bedrock"] = {
            "status": "healthy",
            "models_available": len(response.get("modelSummaries", []))
        }
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
    analytics,
    infrastructure
)

# Include routers
app.include_router(resources.router, prefix="/api/resources", tags=["resources"])
app.include_router(processing.router, prefix="/api/processing", tags=["processing"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(embeddings.router, prefix="/api/embeddings", tags=["embeddings"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(infrastructure.router, prefix="/api", tags=["infrastructure"])

