

"""
API Key Authentication Middleware

Simple API key authentication for S3Vector API endpoints.
Validates X-API-Key header against environment variable.
"""

import logging
import os

from fastapi import HTTPException, Request
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validate API key for all /api/* endpoints except public routes.

    If API_KEY env var is not set, authentication is disabled (dev mode).
    """

    _auth_warning_logged = False

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in ["/", "/api/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Check if API_KEY is configured
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            # Check if running in production
            environment = os.getenv('ENVIRONMENT', '').lower()
            if environment == 'production':
                # BLOCK all requests in production when API_KEY is not set
                raise HTTPException(
                    status_code=500,
                    detail='API_KEY must be configured in production'
                )

            # Dev mode: log warning once and allow requests
            if not APIKeyMiddleware._auth_warning_logged:
                logger.warning(
                    "API_KEY not configured - authentication disabled. "
                    "This is only safe for local development."
                )
                APIKeyMiddleware._auth_warning_logged = True
            return await call_next(request)

        # Validate API key
        api_key = request.headers.get("X-API-Key")

        if api_key != expected_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing API key"
            )

        return await call_next(request)
