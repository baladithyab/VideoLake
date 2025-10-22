"""
Services package for S3 Vector Embedding POC.

This package contains service classes for managing different aspects
of the vector embedding pipeline including multi-vector architecture,
OpenSearch integration, and enhanced Streamlit coordination.
"""

from .bedrock_embedding import BedrockEmbeddingService, EmbeddingResult, ModelInfo
from .opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    ExportStatus,
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
from .streamlit_integration_utils import (
    StreamlitServiceManager,
    StreamlitIntegrationConfig,
    get_service_manager,
    reset_service_manager
)

__all__ = [
    # Bedrock services
    'BedrockEmbeddingService',
    'EmbeddingResult', 
    'ModelInfo',
    
    # OpenSearch integration
    'OpenSearchIntegrationManager',
    'IntegrationPattern',
    'ExportStatus',
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
    'VectorType',
    
    # Streamlit Integration
    'StreamlitServiceManager',
    'StreamlitIntegrationConfig',
    'get_service_manager',
    'reset_service_manager'
]