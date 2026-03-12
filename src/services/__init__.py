"""
Services package for S3 Vector Embedding POC.

This package contains service classes for managing different aspects
of the vector embedding pipeline including multi-vector architecture,
OpenSearch integration, and multi-backend vector store coordination.
"""

# Import embedding providers to trigger auto-registration
from . import bedrock_multimodal_provider
from . import sagemaker_embedding_provider
from . import external_embedding_provider

from .bedrock_embedding import BedrockEmbeddingService, EmbeddingResult, ModelInfo
from .embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderFactory,
    ModalityType,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderCapabilities
)
from .unified_ingestion_service import (
    UnifiedIngestionService,
    IngestionRequest,
    IngestionResult
)
from .opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    HybridSearchResult,
    CostAnalysis
)
from .s3_vector_storage import S3VectorStorageManager
from .similarity_search_engine import (
    SimilaritySearchEngine,
    SimilarityQuery,
    SimilarityResult,
    SimilaritySearchResponse,
    IndexType,
    QueryInputType
)
from .twelvelabs_video_processing import (
    TwelveLabsVideoProcessingService,
    VideoEmbeddingResult,
    VideoProcessingConfig,
    AsyncJobInfo
)
from .multi_vector_coordinator import (
    MultiVectorCoordinator,
    MultiVectorConfig,
    MultiVectorResult,
    SearchRequest,
    VectorType
)

__all__ = [
    # Bedrock services
    'BedrockEmbeddingService',
    'EmbeddingResult',
    'ModelInfo',

    # Multi-modal embedding providers
    'EmbeddingProvider',
    'EmbeddingProviderFactory',
    'ModalityType',
    'EmbeddingRequest',
    'EmbeddingResponse',
    'ProviderCapabilities',

    # Unified ingestion
    'UnifiedIngestionService',
    'IngestionRequest',
    'IngestionResult',

    # OpenSearch integration
    'OpenSearchIntegrationManager',
    'IntegrationPattern',
    'HybridSearchResult',
    'CostAnalysis',

    # S3 Vector Storage
    'S3VectorStorageManager',

    # Similarity Search Engine
    'SimilaritySearchEngine',
    'SimilarityQuery',
    'SimilarityResult',
    'SimilaritySearchResponse',
    'IndexType',
    'QueryInputType',

    # TwelveLabs Video Processing
    'TwelveLabsVideoProcessingService',
    'VideoEmbeddingResult',
    'VideoProcessingConfig',
    'AsyncJobInfo',

    # Multi-Vector Coordinator
    'MultiVectorCoordinator',
    'MultiVectorConfig',
    'MultiVectorResult',
    'SearchRequest',
    'VectorType'
]