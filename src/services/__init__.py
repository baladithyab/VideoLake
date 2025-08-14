"""
Services package for S3 Vector Embedding POC.

This package contains service classes for managing different aspects
of the vector embedding pipeline including OpenSearch integration.
"""

from .bedrock_embedding import BedrockEmbeddingService, EmbeddingResult, ModelInfo
from .opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    ExportStatus,
    HybridSearchResult,
    CostAnalysis
)

__all__ = [
    'BedrockEmbeddingService',
    'EmbeddingResult', 
    'ModelInfo',
    'OpenSearchIntegrationManager',
    'IntegrationPattern',
    'ExportStatus',
    'HybridSearchResult',
    'CostAnalysis'
]