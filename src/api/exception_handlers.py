"""
Centralized Exception Handlers for FastAPI Application.

Provides consistent error responses across all API endpoints.
"""

import uuid
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.exceptions import (
    VectorEmbeddingError,
    ModelAccessError,
    VectorStorageError,
    AsyncProcessingError,
    ConfigurationError,
    ValidationError as CustomValidationError,
    ProcessingError,
    OpenSearchIntegrationError,
    CostOptimizationError,
    CostMonitoringError
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_error_response(
    request: Request,
    error_type: str,
    message: str,
    status_code: int = 500,
    error_code: str = None,
    details: Dict[str, Any] = None
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        request: FastAPI request object
        error_type: Type of error (exception class name)
        message: Human-readable error message
        status_code: HTTP status code
        error_code: Optional application error code
        details: Optional additional error details

    Returns:
        JSONResponse with standardized error format
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    response_data = {
        "success": False,
        "error": {
            "type": error_type,
            "message": message,
            "request_id": request_id
        }
    }

    if error_code:
        response_data["error"]["code"] = error_code

    if details:
        response_data["error"]["details"] = details

    # Log error
    logger.error(
        f"Error response: {error_type}",
        extra={
            "request_id": request_id,
            "error_type": error_type,
            "message": message,
            "status_code": status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=status_code,
        content=response_data
    )


async def vector_embedding_error_handler(request: Request, exc: VectorEmbeddingError) -> JSONResponse:
    """Handle VectorEmbeddingError and its subclasses."""
    # Map exception types to HTTP status codes
    status_code_map = {
        ModelAccessError: status.HTTP_503_SERVICE_UNAVAILABLE,
        VectorStorageError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        AsyncProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        ConfigurationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        CustomValidationError: status.HTTP_400_BAD_REQUEST,
        ProcessingError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        OpenSearchIntegrationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        CostOptimizationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
        CostMonitoringError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    }

    status_code = status_code_map.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)

    return create_error_response(
        request=request,
        error_type=exc.__class__.__name__,
        message=str(exc),
        status_code=status_code,
        error_code=exc.error_code,
        details=exc.error_details
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })

    return create_error_response(
        request=request,
        error_type="ValidationError",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"validation_errors": errors}
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    return create_error_response(
        request=request,
        error_type="HTTPException",
        message=exc.detail,
        status_code=exc.status_code
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    # Log full traceback for debugging
    logger.exception(
        f"Unexpected error: {exc}",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "path": request.url.path,
            "method": request.method
        }
    )

    return create_error_response(
        request=request,
        error_type=exc.__class__.__name__,
        message="An unexpected error occurred",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"original_error": str(exc)}
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # Custom exception handlers
    app.add_exception_handler(VectorEmbeddingError, vector_embedding_error_handler)
    app.add_exception_handler(ModelAccessError, vector_embedding_error_handler)
    app.add_exception_handler(VectorStorageError, vector_embedding_error_handler)
    app.add_exception_handler(AsyncProcessingError, vector_embedding_error_handler)
    app.add_exception_handler(ConfigurationError, vector_embedding_error_handler)
    app.add_exception_handler(CustomValidationError, vector_embedding_error_handler)
    app.add_exception_handler(ProcessingError, vector_embedding_error_handler)
    app.add_exception_handler(OpenSearchIntegrationError, vector_embedding_error_handler)
    app.add_exception_handler(CostOptimizationError, vector_embedding_error_handler)
    app.add_exception_handler(CostMonitoringError, vector_embedding_error_handler)

    # Standard exception handlers
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Exception handlers registered successfully")
