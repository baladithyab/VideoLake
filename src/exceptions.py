"""
Custom exception classes for S3 Vector Embedding POC.

This module defines the exception hierarchy for handling various error
scenarios in the vector embedding pipeline.
"""

from typing import Optional, Dict, Any


class VectorEmbeddingError(Exception):
    """Base exception for vector embedding operations."""
    
    def __init__(self, message: str, error_code: Optional[str] = None, 
                 error_details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_code = error_code
        self.error_details = error_details or {}


class ModelAccessError(VectorEmbeddingError):
    """Raised when model access is denied or model is unavailable."""
    pass


class VectorStorageError(VectorEmbeddingError):
    """Raised when vector storage operations fail."""
    pass


class AsyncProcessingError(VectorEmbeddingError):
    """Raised when async processing fails."""
    pass


class ConfigurationError(VectorEmbeddingError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(VectorEmbeddingError):
    """Raised when input validation fails."""
    pass


class OpenSearchIntegrationError(VectorEmbeddingError):
    """Raised when OpenSearch integration operations fail."""
    pass


class CostOptimizationError(VectorEmbeddingError):
    """Raised when cost optimization strategies fail."""
    pass


class CostMonitoringError(VectorEmbeddingError):
    """Raised when cost monitoring operations fail."""
    pass


# Aliases for compatibility
S3VectorError = VectorEmbeddingError
VideoProcessingError = AsyncProcessingError
EmbeddingError = ModelAccessError