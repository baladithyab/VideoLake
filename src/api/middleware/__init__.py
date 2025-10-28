"""
Middleware package for FastAPI application.
"""

from .observability import ObservabilityMiddleware

__all__ = ['ObservabilityMiddleware']
