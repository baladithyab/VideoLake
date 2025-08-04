"""
Services package for S3 Vector Embedding POC.

This package contains service classes for managing different aspects
of the vector embedding pipeline.
"""

from .bedrock_embedding import BedrockEmbeddingService, EmbeddingResult, ModelInfo

__all__ = [
    'BedrockEmbeddingService',
    'EmbeddingResult', 
    'ModelInfo'
]