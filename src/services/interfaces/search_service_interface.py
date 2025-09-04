"""
Search Service Interface

Abstract interface for search services, enabling dependency inversion
and breaking circular dependencies between services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class QueryInputType(Enum):
    """Supported query input types for similarity search."""
    TEXT = "text"
    VIDEO_KEY = "video_key"
    VIDEO_FILE = "video_file"
    AUDIO_FILE = "audio_file"
    IMAGE_FILE = "image_file"
    EMBEDDING = "embedding"


class IndexType(Enum):
    """Types of vector indexes supported."""
    MARENGO_MULTIMODAL = "marengo_multimodal"
    TITAN_TEXT = "titan_text"


@dataclass
class SearchResult:
    """Generic search result interface."""
    key: str
    similarity_score: float
    content_type: str
    metadata: Dict[str, Any]
    confidence_score: float = 0.0
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    duration_sec: Optional[float] = None
    embedding_option: Optional[str] = None
    model_id: Optional[str] = None
    retrieval_time_ms: int = 0
    explanation: Optional[str] = None


@dataclass
class SearchResponse:
    """Generic search response interface."""
    results: List[SearchResult]
    total_results: int
    query_id: str
    input_type: QueryInputType
    index_type: IndexType
    processing_time_ms: int
    result_distribution: Dict[str, int]
    similarity_range: Tuple[float, float]
    cost_estimate: float
    search_suggestions: List[str]


@dataclass
class SearchQuery:
    """Generic search query interface."""
    # Query input (exactly one must be provided)
    query_text: Optional[str] = None
    query_video_key: Optional[str] = None
    query_video_s3_uri: Optional[str] = None
    query_audio_s3_uri: Optional[str] = None
    query_image_s3_uri: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    
    # Query configuration
    top_k: int = 10
    similarity_threshold: float = 0.0
    target_indexes: Optional[List[str]] = None
    vector_types: Optional[List[str]] = None
    
    # Filtering
    metadata_filters: Optional[Dict[str, Any]] = None
    temporal_filter: Optional[Dict[str, Any]] = None
    content_type_filter: Optional[List[str]] = None
    
    # Processing options
    extract_entities: bool = True
    expand_synonyms: bool = True
    include_explanations: bool = False
    deduplicate_results: bool = True
    cross_index_fusion: bool = True


class ISearchService(ABC):
    """
    Abstract interface for search services.
    
    This interface defines the contract for search operations,
    allowing different implementations (direct S3Vector, OpenSearch hybrid, etc.)
    to be used interchangeably.
    """
    
    @abstractmethod
    def find_similar_content(self, 
                           query: SearchQuery,
                           index_arn: str,
                           index_type: IndexType) -> SearchResponse:
        """
        Find similar content using the specified query and index.
        
        Args:
            query: Search query with input and configuration
            index_arn: ARN of the vector index to search
            index_type: Type of index (determines supported query types)
            
        Returns:
            SearchResponse with comprehensive results and analytics
        """
        pass
    
    @abstractmethod
    def search_by_text_query(self,
                           query_text: str,
                           index_arn: str,
                           index_type: IndexType,
                           top_k: int = 10,
                           temporal_filter: Optional[Dict[str, Any]] = None,
                           metadata_filters: Optional[Dict[str, Any]] = None) -> SearchResponse:
        """
        Search using natural language text queries.
        
        Args:
            query_text: Natural language query text
            index_arn: ARN of the vector index
            index_type: Type of index
            top_k: Number of results to return
            temporal_filter: Optional temporal filtering
            metadata_filters: Optional metadata filters
            
        Returns:
            SearchResponse with text query results
        """
        pass
    
    @abstractmethod
    def search_multi_index(self,
                         query: SearchQuery,
                         index_configurations: List[Dict[str, Any]],
                         fusion_method: str = "weighted_average") -> SearchResponse:
        """
        Search across multiple indexes and fuse results.
        
        Args:
            query: Search query with multi-index configuration
            index_configurations: List of index configs with ARN and type
            fusion_method: Method for combining results
            
        Returns:
            SearchResponse with fused multi-index results
        """
        pass
    
    @abstractmethod
    def get_compatible_indexes(self, query: SearchQuery) -> List[str]:
        """
        Get list of indexes compatible with the query.
        
        Args:
            query: Search query to check compatibility for
            
        Returns:
            List of compatible index ARNs
        """
        pass
    
    @abstractmethod
    def register_index(self, 
                      index_arn: str, 
                      index_type: IndexType,
                      vector_types: List[str], 
                      metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Register an index for multi-index search coordination.
        
        Args:
            index_arn: ARN of the index to register
            index_type: Type of the index
            vector_types: Supported vector types
            metadata: Additional index metadata
        """
        pass
    
    @abstractmethod
    def get_engine_capabilities(self) -> Dict[str, Any]:
        """
        Get comprehensive information about search engine capabilities.
        
        Returns:
            Dictionary with supported features, models, and statistics
        """
        pass


class ISearchServiceFactory(ABC):
    """
    Abstract factory for creating search service instances.
    
    This enables dynamic creation of different search service implementations
    based on configuration or runtime requirements.
    """
    
    @abstractmethod
    def create_s3vector_search_service(self, 
                                     config: Optional[Dict[str, Any]] = None) -> ISearchService:
        """Create a direct S3Vector search service."""
        pass
    
    @abstractmethod
    def create_opensearch_search_service(self, 
                                       config: Optional[Dict[str, Any]] = None) -> ISearchService:
        """Create an OpenSearch hybrid search service."""
        pass
    
    @abstractmethod
    def create_unified_search_service(self, 
                                    config: Optional[Dict[str, Any]] = None) -> ISearchService:
        """Create a unified search service supporting both patterns."""
        pass