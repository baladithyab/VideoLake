"""
Observability Middleware for Request Tracking and Performance Monitoring.

Provides:
- Request ID generation and propagation
- Request/response logging
- Performance timing
- Error tracking
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for observability and request tracking.

    Adds:
    - Unique request ID to each request
    - Request/response logging with timing
    - Performance metrics
    - Error tracking
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add observability.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with added headers
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Get client info
        client_host = request.client.host if request.client else "unknown"

        # Track timing
        start_time = time.time()

        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": client_host,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_host": client_host
                }
            )

            # Add observability headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error_type": e.__class__.__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2),
                    "client_host": client_host
                },
                exc_info=True
            )

            # Re-raise to be handled by exception handlers
            raise


class PerformanceLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for detailed performance logging.

    Tracks slow requests and logs warnings.
    """

    def __init__(self, app: ASGIApp, slow_request_threshold_ms: float = 1000.0):
        """
        Initialize performance logging middleware.

        Args:
            app: ASGI application
            slow_request_threshold_ms: Threshold for slow request warning (default: 1000ms)
        """
        super().__init__(app)
        self.slow_request_threshold_ms = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log performance warnings."""
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log slow requests
        if duration_ms > self.slow_request_threshold_ms:
            request_id = getattr(request.state, "request_id", "unknown")
            logger.warning(
                f"Slow request detected: {duration_ms:.2f}ms",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "threshold_ms": self.slow_request_threshold_ms
                }
            )

        return response
