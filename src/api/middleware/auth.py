"""
API Key Authentication Middleware

Simple API key authentication for S3Vector API endpoints.
Validates X-API-Key header against environment variable.
"""

import os
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validate API key for all /api/* endpoints except public routes.

    If API_KEY env var is not set, authentication is disabled (dev mode).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public endpoints
        if request.url.path in ["/", "/api/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Check if API_KEY is configured
        expected_key = os.getenv("API_KEY")

        if not expected_key:
            # Dev mode: no API key required
            return await call_next(request)

        # Validate API key
        api_key = request.headers.get("X-API-Key")

        if api_key != expected_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid or missing API key"
            )

        return await call_next(request)
