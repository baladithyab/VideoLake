"""
Similarity Search Engine Service

This service provides unified similarity search capabilities across S3 Vector indexes,
supporting multimodal search within the same embedding space. It handles:

1. Multimodal search within Marengo indexes (text, video, audio, image queries)
2. Text search within Titan text indexes  
3. Natural language query processing and enhancement
4. Temporal video search with time-based filtering
5. Advanced metadata filtering and result processing
6. Performance optimization and cost tracking

Key insight: TwelveLabs Marengo generates embeddings in the same 1024-dimensional 
space for all input modalities (text, video, audio, image), enabling true multimodal
search within a single index. Titan text embeddings are separate and only support
text-to-text search.

Based on AWS Documentation:
- TwelveLabs Marengo Embed 2.7: Input modalities: Video, Text, Audio, Image
- Model ID: twelvelabs.marengo-embed-2-7-v1:0  
- Output: 1024-dimensional embeddings in unified space
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

from src.services.interfaces.search_service_interface import (
    ISearchService, SearchQuery, SearchResponse, SearchResult,
    QueryInputType, IndexType
)
from src.services.interfaces.service_registry import get_global_service, ServiceNames
from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.unified_video_processing_service import UnifiedVideoProcessingService
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.exceptions import ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Remove duplicate enum definitions - using the ones from interface


@dataclass
class TemporalFilter:
    """Temporal filtering criteria for video/audio search."""
    start_time: Optional[float] = None    # Start time in seconds
    end_time: Optional[float] = None      # End time in seconds
    duration_min: Optional[float] = None  # Minimum segment duration
    duration_max: Optional[float] = None  # Maximum segment duration
    
    def to_s3_metadata_filter(self) -> Dict[str, Any]:
        """Convert temporal filter to S3 Vector metadata filter format."""
        filter_conditions = {}
        
        if self.start_time is not None:
            filter_conditions["start_sec"] = {"$gte": self.start_time}
        if self.end_time is not None:
            filter_conditions["end_sec"] = {"$lte": self.end_time}
        
        # Duration is calculated as end_sec - start_sec, but S3 Vectors
        # doesn't support computed fields in filters, so we approximate
        if self.duration_min is not None or self.duration_max is not None:
            logger.warning("Duration filtering requires post-processing - not supported directly by S3 Vector filters")
            
        return filter_conditions


@dataclass
class SimilarityQuery:
    """Unified similarity query supporting all input modalities."""
    # Query input (exactly one must be provided)
    query_text: Optional[str] = None
    query_video_key: Optional[str] = None       # Key of existing video in index
    query_video_s3_uri: Optional[str] = None    # S3 URI of video file
    query_audio_s3_uri: Optional[str] = None    # S3 URI of audio file  
    query_image_s3_uri: Optional[str] = None    # S3 URI of image file
    query_embedding: Optional[List[float]] = None
    
    # Multi-index query configuration
    target_indexes: Optional[List[str]] = None   # Specific indexes to search
    vector_types: Optional[List[str]] = None     # Vector types to include
    cross_index_fusion: bool = True              # Enable cross-index result fusion
    
    # Query configuration
    top_k: int = 10
    similarity_threshold: float = 0.0           # Minimum similarity score
    
    # Filtering
    metadata_filters: Optional[Dict[str, Any]] = None
    temporal_filter: Optional[TemporalFilter] = None
    content_type_filter: Optional[List[str]] = None  # Filter by content_type metadata
    
    # Query enhancement (for text queries)
    extract_entities: bool = True
    expand_synonyms: bool = True
    
    # Result processing
    include_explanations: bool = False
    deduplicate_results: bool = True
    diversity_factor: float = 0.0               # 0.0 = no diversification, 1.0 = maximum
    
    def get_input_type(self) -> QueryInputType:
        """Determine the input type based on provided query parameters."""
        if self.query_text:
            return QueryInputType.TEXT
        elif self.query_video_key:
            return QueryInputType.VIDEO_KEY
        elif self.query_video_s3_uri:
            return QueryInputType.VIDEO_FILE
        elif self.query_audio_s3_uri:
            return QueryInputType.AUDIO_FILE
        elif self.query_image_s3_uri:
            return QueryInputType.IMAGE_FILE
        elif self.query_embedding:
            return QueryInputType.EMBEDDING
        else:
            raise ValidationError("No query input provided")


@dataclass
class SimilarityResult:
    """Enhanced similarity search result with multimodal context."""
    # Core result data
    key: str
    similarity_score: float
    content_type: str                           # text, video, audio, image
    metadata: Dict[str, Any]
    
    # Enhanced information
    explanation: Optional[str] = None           # Why this result matched
    confidence_score: float = 0.0              # Adjusted confidence after post-processing
    
    # Temporal information (for video/audio results)
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    duration_sec: Optional[float] = None
    
    # Embedding information
    embedding_option: Optional[str] = None      # For Marengo: visual-text, visual-image, audio
    model_id: Optional[str] = None
    
    # Performance tracking
    retrieval_time_ms: int = 0


@dataclass 
class SimilaritySearchResponse:
    """Comprehensive similarity search response with analytics."""
    # Results
    results: List[SimilarityResult]
    total_results: int
    query_id: str
    
    # Query information
    input_type: QueryInputType
    index_type: IndexType
    processing_time_ms: int
    
    # Analytics
    result_distribution: Dict[str, int]         # Count by content_type
    similarity_range: Tuple[float, float]       # Min/max similarity scores
    cost_estimate: float
    
    # Suggestions
    search_suggestions: List[str]


class SimilaritySearchEngine(ISearchService):
    """
    Unified similarity search engine supporting multimodal search within S3 Vector indexes.
    
    This engine understands the embedding model used to create each index and routes
    queries appropriately:
    
    - Marengo indexes: Support text, video, audio, image queries (same embedding space)
    - Titan text indexes: Support only text queries
    
    Key capabilities:
    1. Query input processing for all supported modalities
    2. Embedding generation using the appropriate model
    3. S3 Vector search with native metadata filtering
    4. Result post-processing and enhancement
    5. Performance analytics and cost tracking
    """
    
    def __init__(self,
                 bedrock_service: Optional[BedrockEmbeddingService] = None,
                 twelvelabs_service: Optional[TwelveLabsVideoProcessingService] = None,
                 s3_vector_manager: Optional[S3VectorStorageManager] = None,
                 text_storage: Optional[EmbeddingStorageIntegration] = None,
                 video_storage: Optional[UnifiedVideoProcessingService] = None):
        """
        Initialize the similarity search engine.
        
        Args:
            bedrock_service: Bedrock embedding service (for Titan text embeddings)
            twelvelabs_service: TwelveLabs service (for Marengo embeddings)
            s3_vector_manager: S3 Vector storage manager
            text_storage: Text embedding storage service  
            video_storage: Video embedding storage service
        """
        self.bedrock_service = bedrock_service or BedrockEmbeddingService()
        self.twelvelabs_service = twelvelabs_service or TwelveLabsVideoProcessingService()
        self.s3_vector_manager = s3_vector_manager or S3VectorStorageManager()
        self.text_storage = text_storage or EmbeddingStorageIntegration()
        self.video_storage = video_storage or UnifiedVideoProcessingService()
        
        # Performance tracking with thread safety
        self._stats_lock = Lock()
        self.search_stats = {
            'total_searches': 0,
            'total_cost': 0.0,
            'average_latency_ms': 0.0,
            'searches_by_input_type': {},
            'multi_index_searches': 0,
            'cross_vector_searches': 0
        }
        
        # Multi-index configuration
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.index_registry: Dict[str, Dict[str, Any]] = {}
        
        logger.info("SimilaritySearchEngine initialized with multi-vector and multi-index capabilities")

    def find_similar_content(self,
                           query: SearchQuery,
                           index_arn: str,
                           index_type: IndexType) -> SearchResponse:
        """
        Find similar content using multimodal search within the specified index.
        
        This is the main entry point for all similarity search operations.
        
        Args:
            query: Similarity query with input and configuration
            index_arn: ARN of the S3 Vector index to search
            index_type: Type of index (determines supported query types)
            
        Returns:
            SimilaritySearchResponse with comprehensive results and analytics
            
        Raises:
            ValidationError: If query/index combination is invalid
        """
        start_time = time.time()
        query_id = f"sim_search_{int(start_time)}_{id(query)}"
        input_type = query.get_input_type()
        
        logger.info(f"Starting similarity search: {query_id}, input: {input_type.value}, index: {index_type.value}")
        
        # Validate query against index type
        self._validate_query_index_compatibility(query, index_type, input_type)
        
        # Process query to generate embedding
        query_embedding, cost = self._generate_query_embedding(query, index_type, index_arn)
        
        # Prepare metadata filters
        combined_filters = self._prepare_metadata_filters(query)
        
        # Execute S3 Vector search
        search_results = self.s3_vector_manager.query_vectors(
            index_arn=index_arn,
            query_vector=query_embedding,
            top_k=query.top_k,
            metadata_filter=combined_filters,
            return_distance=True,
            return_metadata=True
        )
        
        # Convert to similarity results
        similarity_results = self._convert_to_similarity_results(
            search_results, query, input_type, index_type
        )
        
        # Post-process results
        processed_results = self._post_process_results(similarity_results, query)
        
        # Generate response
        processing_time_ms = int((time.time() - start_time) * 1000)
        response = self._generate_search_response(
            processed_results, query_id, input_type, index_type, 
            processing_time_ms, cost, query
        )
        
        # Update statistics
        self._update_search_stats(input_type, processing_time_ms, cost)
        
        logger.info(f"Similarity search completed: {query_id}, {len(processed_results)} results, {processing_time_ms}ms")
        return response

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
            index_arn: ARN of the S3 Vector index
            index_type: Type of index (determines embedding model)
            top_k: Number of results to return
            temporal_filter: Optional temporal filtering for video/audio content
            metadata_filters: Optional metadata filters
            
        Returns:
            SimilaritySearchResponse with text query results
        """
        query = SearchQuery(
            query_text=query_text,
            top_k=top_k,
            metadata_filters=metadata_filters,
            extract_entities=True,
            expand_synonyms=True,
            include_explanations=True
        )
        
        return self.find_similar_content(query, index_arn, index_type)

    def search_video_scenes(self,
                          video_query: Union[str, str, str],  # text query, video key, or video S3 URI
                          index_arn: str,
                          time_range: Optional[Tuple[float, float]] = None,
                          top_k: int = 10) -> SimilaritySearchResponse:
        """
        Search for specific video scenes using temporal and content criteria.
        
        Args:
            video_query: Either text description, existing video key, or video S3 URI
            index_arn: ARN of the Marengo multimodal index
            time_range: Optional time range filter (start_sec, end_sec)
            top_k: Number of results to return
            
        Returns:
            SimilaritySearchResponse with video scene results
        """
        # Create temporal filter
        temporal_filter = None
        if time_range:
            temporal_filter = TemporalFilter(
                start_time=time_range[0],
                end_time=time_range[1]
            )
        
        # Determine query type
        if video_query.startswith("s3://"):
            # S3 URI provided
            query = SimilarityQuery(
                query_video_s3_uri=video_query,
                top_k=top_k,
                temporal_filter=temporal_filter,
                content_type_filter=["video"],
                include_explanations=True
            )
        elif " " in video_query or len(video_query) > 50:
            # Looks like text description
            query = SimilarityQuery(
                query_text=video_query,
                top_k=top_k,
                temporal_filter=temporal_filter,
                content_type_filter=["video"],
                extract_entities=True,
                include_explanations=True
            )
        else:
            # Assume it's a video key
            query = SimilarityQuery(
                query_video_key=video_query,
                top_k=top_k,
                temporal_filter=temporal_filter,
                content_type_filter=["video"],
                include_explanations=True
            )
        
        return self.find_similar_content(query, index_arn, IndexType.MARENGO_MULTIMODAL)

    def search_multi_index(self,
                          query: SearchQuery,
                          index_configurations: List[Dict[str, Any]],
                          fusion_method: str = "weighted_average") -> SearchResponse:
        """
        Search across multiple indexes and fuse results.
        
        Args:
            query: Similarity query with multi-index configuration
            index_configurations: List of index configs with ARN and type
            fusion_method: Method for combining results ("weighted_average", "rank_fusion", "max_score")
            
        Returns:
            SimilaritySearchResponse with fused multi-index results
        """
        start_time = time.time()
        query_id = f"multi_index_{int(start_time)}_{id(query)}"
        input_type = query.get_input_type()
        
        logger.info(f"Starting multi-index search: {query_id}, {len(index_configurations)} indexes")
        
        # Execute searches across all indexes concurrently
        search_tasks = []
        with ThreadPoolExecutor(max_workers=len(index_configurations)) as executor:
            for i, config in enumerate(index_configurations):
                index_arn = config['index_arn']
                index_type = IndexType(config['index_type'])
                weight = config.get('weight', 1.0)
                
                # Create a copy of query for this index
                index_query = SimilarityQuery(
                    query_text=query.query_text,
                    query_video_key=query.query_video_key,
                    query_video_s3_uri=query.query_video_s3_uri,
                    query_audio_s3_uri=query.query_audio_s3_uri,
                    query_image_s3_uri=query.query_image_s3_uri,
                    query_embedding=query.query_embedding,
                    top_k=query.top_k * 2,  # Get more results for fusion
                    similarity_threshold=query.similarity_threshold * 0.8,  # Lower threshold for fusion
                    metadata_filters=query.metadata_filters,
                    temporal_filter=query.temporal_filter,
                    content_type_filter=query.content_type_filter,
                    extract_entities=query.extract_entities,
                    expand_synonyms=query.expand_synonyms,
                    include_explanations=query.include_explanations,
                    deduplicate_results=query.deduplicate_results,
                    diversity_factor=query.diversity_factor
                )
                
                future = executor.submit(self._search_single_index_with_metadata, 
                                       index_query, index_arn, index_type, weight, i)
                search_tasks.append(future)
            
            # Collect all results
            index_results = []
            total_cost = 0.0
            
            for future in as_completed(search_tasks):
                try:
                    result = future.result()
                    index_results.append(result)
                    total_cost += result.get('cost', 0.0)
                except Exception as e:
                    logger.error(f"Index search failed: {e}")
                    # Continue with other results
        
        # Fuse results from all indexes
        fused_results = self._fuse_multi_index_results(
            index_results, query, fusion_method
        )
        
        # Generate final response
        processing_time_ms = int((time.time() - start_time) * 1000)
        response = self._generate_search_response(
            fused_results, query_id, input_type, IndexType.MARENGO_MULTIMODAL,
            processing_time_ms, total_cost, query
        )
        
        # Update statistics
        self._update_search_stats(
            input_type, processing_time_ms, total_cost,
            is_multi_index=True, is_cross_vector=len(index_configurations) > 1
        )
        
        logger.info(f"Multi-index search completed: {query_id}, {len(fused_results)} final results")
        return response

    def _search_single_index_with_metadata(self, query: SimilarityQuery, index_arn: str, 
                                         index_type: IndexType, weight: float, 
                                         index_id: int) -> Dict[str, Any]:
        """Search a single index and return results with metadata."""
        try:
            response = self.find_similar_content(query, index_arn, index_type)
            return {
                'index_arn': index_arn,
                'index_type': index_type,
                'weight': weight,
                'index_id': index_id,
                'results': response.results,
                'cost': response.cost_estimate,
                'processing_time_ms': response.processing_time_ms,
                'success': True
            }
        except Exception as e:
            logger.error(f"Failed to search index {index_arn}: {e}")
            return {
                'index_arn': index_arn,
                'index_type': index_type,
                'weight': weight,
                'index_id': index_id,
                'results': [],
                'cost': 0.0,
                'processing_time_ms': 0,
                'success': False,
                'error': str(e)
            }

    def _fuse_multi_index_results(self,
                                index_results: List[Dict[str, Any]],
                                query: SimilarityQuery,
                                fusion_method: str) -> List[SimilarityResult]:
        """Fuse results from multiple indexes using the specified method."""
        if fusion_method == "weighted_average":
            return self._fuse_weighted_average(index_results, query)
        elif fusion_method == "rank_fusion":
            return self._fuse_rank_based(index_results, query)
        elif fusion_method == "max_score":
            return self._fuse_max_score(index_results, query)
        else:
            logger.warning(f"Unknown fusion method: {fusion_method}, using weighted_average")
            return self._fuse_weighted_average(index_results, query)

    def _fuse_weighted_average(self, index_results: List[Dict[str, Any]], 
                             query: SimilarityQuery) -> List[SimilarityResult]:
        """Fuse results using weighted average of similarity scores."""
        result_map = {}
        
        for index_result in index_results:
            if not index_result['success']:
                continue
                
            weight = index_result['weight']
            for result in index_result['results']:
                key = result.key
                if key not in result_map:
                    result_map[key] = {
                        'result': result,
                        'weighted_score': 0.0,
                        'weight_sum': 0.0,
                        'index_count': 0
                    }
                
                result_map[key]['weighted_score'] += result.similarity_score * weight
                result_map[key]['weight_sum'] += weight
                result_map[key]['index_count'] += 1
        
        # Calculate final scores and create results
        fused_results = []
        for key, data in result_map.items():
            if data['weight_sum'] > 0:
                final_score = data['weighted_score'] / data['weight_sum']
                result = data['result']
                result.similarity_score = final_score
                result.confidence_score = final_score * (data['index_count'] / len(index_results))
                fused_results.append(result)
        
        # Sort by final score and limit results
        fused_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return fused_results[:query.top_k]

    def _fuse_rank_based(self, index_results: List[Dict[str, Any]], 
                       query: SimilarityQuery) -> List[SimilarityResult]:
        """Fuse results using reciprocal rank fusion."""
        result_map = {}
        
        for index_result in index_results:
            if not index_result['success']:
                continue
                
            weight = index_result['weight']
            for rank, result in enumerate(index_result['results']):
                key = result.key
                if key not in result_map:
                    result_map[key] = {
                        'result': result,
                        'rrf_score': 0.0,
                        'index_count': 0
                    }
                
                # Reciprocal Rank Fusion: 1 / (k + rank) where k=60 is common
                rrf_score = weight * (1.0 / (60 + rank + 1))
                result_map[key]['rrf_score'] += rrf_score
                result_map[key]['index_count'] += 1
        
        # Create final results
        fused_results = []
        for key, data in result_map.items():
            result = data['result']
            result.similarity_score = data['rrf_score']
            result.confidence_score = data['rrf_score'] * (data['index_count'] / len(index_results))
            fused_results.append(result)
        
        # Sort by RRF score and limit results
        fused_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return fused_results[:query.top_k]

    def _fuse_max_score(self, index_results: List[Dict[str, Any]], 
                      query: SimilarityQuery) -> List[SimilarityResult]:
        """Fuse results by taking maximum score across indexes."""
        result_map = {}
        
        for index_result in index_results:
            if not index_result['success']:
                continue
                
            for result in index_result['results']:
                key = result.key
                if key not in result_map or result.similarity_score > result_map[key].similarity_score:
                    result_map[key] = result
        
        # Sort by score and limit results
        fused_results = list(result_map.values())
        fused_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return fused_results[:query.top_k]

    def register_index(self, index_arn: str, index_type: IndexType, 
                      vector_types: List[str], metadata: Dict[str, Any] = None) -> None:
        """Register an index for multi-index search coordination."""
        self.index_registry[index_arn] = {
            'index_type': index_type,
            'vector_types': set(vector_types),
            'metadata': metadata or {},
            'registered_at': time.time()
        }
        logger.info(f"Registered index {index_arn} with vector types: {vector_types}")

    def get_compatible_indexes(self, query: SearchQuery) -> List[str]:
        """Get list of indexes compatible with the query."""
        input_type = query.get_input_type()
        compatible_indexes = []
        
        for index_arn, config in self.index_registry.items():
            index_type = config['index_type']
            vector_types = config['vector_types']
            
            # Check compatibility based on input type and index type
            if self._is_query_compatible(input_type, index_type, vector_types):
                # Apply vector type filter if specified
                if query.vector_types:
                    if any(vt in vector_types for vt in query.vector_types):
                        compatible_indexes.append(index_arn)
                else:
                    compatible_indexes.append(index_arn)
        
        return compatible_indexes

    def _is_query_compatible(self, input_type: QueryInputType, index_type: IndexType, 
                           vector_types: Set[str]) -> bool:
        """Check if query input type is compatible with index."""
        if index_type == IndexType.TITAN_TEXT:
            return input_type in [QueryInputType.TEXT, QueryInputType.EMBEDDING]
        elif index_type == IndexType.MARENGO_MULTIMODAL:
            return True  # Marengo supports all input types
        return False

    def filter_by_metadata(self,
                         results: List[SimilarityResult],
                         metadata_filters: Dict[str, Any],
                         similarity_threshold: float = 0.0) -> List[SimilarityResult]:
        """
        Apply additional metadata filtering to search results.
        
        This performs post-search filtering for complex conditions not supported
        by S3 Vector's native filtering capabilities.
        
        Args:
            results: Base search results to filter
            metadata_filters: Additional metadata filtering criteria
            similarity_threshold: Minimum similarity score
            
        Returns:
            Filtered list of similarity results
        """
        filtered_results = []
        
        for result in results:
            # Apply similarity threshold
            if result.similarity_score < similarity_threshold:
                continue
                
            # Apply metadata filters
            if self._matches_metadata_filters(result.metadata, metadata_filters):
                # Apply duration filter if needed (post-processing)
                if result.start_sec is not None and result.end_sec is not None:
                    duration = result.end_sec - result.start_sec
                    result.duration_sec = duration
                    
                filtered_results.append(result)
        
        return filtered_results

    def _validate_query_index_compatibility(self,
                                          query: SimilarityQuery,
                                          index_type: IndexType,
                                          input_type: QueryInputType) -> None:
        """Validate that the query input type is compatible with the index type."""
        if index_type == IndexType.TITAN_TEXT:
            if input_type != QueryInputType.TEXT and input_type != QueryInputType.EMBEDDING:
                raise ValidationError(
                    f"Titan text indexes only support text queries. "
                    f"Got input type: {input_type.value}"
                )
        elif index_type == IndexType.MARENGO_MULTIMODAL:
            # Marengo supports all input types
            pass
        else:
            raise ValidationError(f"Unsupported index type: {index_type}")
        
        # Validate query parameters
        if query.top_k <= 0 or query.top_k > 1000:
            raise ValidationError("top_k must be between 1 and 1000")
        
        if query.similarity_threshold < 0.0 or query.similarity_threshold > 1.0:
            raise ValidationError("similarity_threshold must be between 0.0 and 1.0")

    def _generate_query_embedding(self,
                                query: SimilarityQuery,
                                index_type: IndexType,
                                index_arn: str) -> Tuple[List[float], float]:
        """
        Generate query embedding using the appropriate model for the index type.
        
        Returns:
            Tuple of (embedding_vector, cost_estimate)
        """
        input_type = query.get_input_type()
        cost = 0.0
        
        if input_type == QueryInputType.EMBEDDING:
            # Direct embedding provided
            return query.query_embedding, 0.0
        
        elif input_type == QueryInputType.TEXT:
            # Process text query
            text = query.query_text
            if query.extract_entities or query.expand_synonyms:
                text = self._enhance_text_query(text, query)
            
            if index_type == IndexType.TITAN_TEXT:
                # Use Bedrock Titan for text embedding
                result = self.bedrock_service.generate_text_embedding(text)
                cost = 0.0001  # Approximate cost
                return result.embedding, cost
            else:
                # Use TwelveLabs Marengo for text embedding
                embedding_result = self.twelvelabs_service.generate_text_embedding(text)
                cost = 0.0001  # Approximate cost
                return embedding_result['embedding'], cost
                
        elif input_type == QueryInputType.VIDEO_KEY:
            # Get embedding from existing video in index
            return self._get_embedding_from_video_key(query.query_video_key, index_arn), 0.0
        
        elif input_type in [QueryInputType.VIDEO_FILE, QueryInputType.AUDIO_FILE, QueryInputType.IMAGE_FILE]:
            # Process media file using Marengo
            if index_type != IndexType.MARENGO_MULTIMODAL:
                raise ValidationError(f"Media queries only supported with Marengo indexes")
            
            s3_uri = (query.query_video_s3_uri or 
                     query.query_audio_s3_uri or 
                     query.query_image_s3_uri)
            
            media_type = {
                QueryInputType.VIDEO_FILE: "video",
                QueryInputType.AUDIO_FILE: "audio", 
                QueryInputType.IMAGE_FILE: "image"
            }[input_type]
            
            embedding_result = self.twelvelabs_service.generate_media_embedding(
                s3_uri=s3_uri,
                input_type=media_type
            )
            
            cost = 0.05 if media_type == "video" else 0.001  # Rough estimates
            return embedding_result['embedding'], cost
        
        else:
            raise ValidationError(f"Unsupported input type: {input_type}")

    def _enhance_text_query(self, text: str, query: SimilarityQuery) -> str:
        """Enhance text query with entity extraction and synonym expansion."""
        enhanced_text = text
        
        if query.extract_entities:
            entities = self._extract_entities(text)
            if entities:
                logger.debug(f"Extracted entities: {entities}")
        
        if query.expand_synonyms:
            enhanced_text = self._expand_with_synonyms(text)
            
        return enhanced_text

    def _extract_entities(self, text: str) -> List[str]:
        """Simple entity extraction (in production, use proper NLP library)."""
        # Simplified implementation
        words = text.lower().split()
        entities = []
        
        # Time entities
        time_words = ['morning', 'afternoon', 'evening', 'night', 'today', 'yesterday']
        entities.extend([w for w in words if w in time_words])
        
        # Action entities  
        action_words = ['running', 'walking', 'talking', 'singing', 'dancing', 'cooking']
        entities.extend([w for w in words if w in action_words])
        
        return list(set(entities))

    def _expand_with_synonyms(self, text: str) -> str:
        """Simple synonym expansion (in production, use proper thesaurus)."""
        # Simplified implementation
        synonyms = {
            'happy': 'joyful cheerful delighted',
            'sad': 'melancholy sorrowful',
            'fast': 'quick rapid swift',
            'slow': 'gradual leisurely'
        }
        
        words = text.split()
        expanded = words.copy()
        
        for word in words:
            if word.lower() in synonyms:
                expanded.extend(synonyms[word.lower()].split())
                
        return ' '.join(expanded)

    def _get_embedding_from_video_key(self, video_key: str, index_arn: str) -> List[float]:
        """Retrieve embedding for existing video by key."""
        try:
            # List vectors in the index to find the specific video key
            response = self.s3_vector_manager.list_vectors(
                index_arn=index_arn,
                max_results=100,  # Start with a reasonable limit
                return_data=True
            )
            
            # Find the specific vector by key
            target_vector = None
            for vector in response.get('vectors', []):
                if vector.get('key') == video_key:
                    target_vector = vector
                    break
            
            if not target_vector:
                # If not found in first 100, we might need to paginate
                # For now, raise a more informative error
                raise ValidationError(
                    f"Video key '{video_key}' not found in index. "
                    f"Available keys might need pagination to access."
                )
            
            # Extract the embedding data
            embedding_data = target_vector.get('data', {})
            if 'float32' in embedding_data:
                return embedding_data['float32']
            else:
                raise ValidationError(f"No embedding data found for video key: {video_key}")
                
        except Exception as e:
            logger.error(f"Failed to retrieve embedding for video key {video_key}: {str(e)}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to retrieve video embedding: {str(e)}")

    def _prepare_metadata_filters(self, query: SimilarityQuery) -> Optional[Dict[str, Any]]:
        """Prepare combined metadata filters for S3 Vector search."""
        combined_filters = {}
        
        # Add user-provided metadata filters
        if query.metadata_filters:
            combined_filters.update(query.metadata_filters)
        
        # Add temporal filters
        if query.temporal_filter:
            temporal_filters = query.temporal_filter.to_s3_metadata_filter()
            combined_filters.update(temporal_filters)
        
        # Add content type filter
        if query.content_type_filter:
            combined_filters["content_type"] = {"$in": query.content_type_filter}
        
        return combined_filters if combined_filters else None

    def _convert_to_similarity_results(self,
                                     search_results: Dict[str, Any],
                                     query: SimilarityQuery,
                                     input_type: QueryInputType,
                                     index_type: IndexType) -> List[SimilarityResult]:
        """Convert S3 Vector search results to SimilarityResult objects."""
        results = []
        
        for vector in search_results.get('vectors', []):
            metadata = vector.get('metadata', {})
            distance = vector.get('distance', 0.0)
            similarity_score = max(0.0, 1.0 - distance)  # Convert distance to similarity
            
            result = SimilarityResult(
                key=vector.get('key', ''),
                similarity_score=similarity_score,
                content_type=metadata.get('content_type', 'unknown'),
                metadata=metadata,
                confidence_score=similarity_score,
                start_sec=metadata.get('start_sec'),
                end_sec=metadata.get('end_sec'),
                embedding_option=metadata.get('embedding_option'),
                model_id=metadata.get('model_id')
            )
            
            # Calculate duration for video/audio content
            if result.start_sec is not None and result.end_sec is not None:
                result.duration_sec = result.end_sec - result.start_sec
            
            # Generate explanation if requested
            if query.include_explanations:
                result.explanation = self._generate_result_explanation(
                    result, input_type, index_type
                )
            
            results.append(result)
        
        return results

    def _generate_result_explanation(self,
                                   result: SimilarityResult,
                                   input_type: QueryInputType,
                                   index_type: IndexType) -> str:
        """Generate human-readable explanation for why this result matched."""
        explanations = []
        
        # Input type explanation
        if input_type == QueryInputType.TEXT:
            explanations.append(f"Matched text query to {result.content_type} content")
        elif input_type in [QueryInputType.VIDEO_FILE, QueryInputType.AUDIO_FILE, QueryInputType.IMAGE_FILE]:
            explanations.append(f"Similar {input_type.value.replace('_file', '')} content")
        
        # Similarity score explanation
        if result.similarity_score > 0.9:
            explanations.append("very high similarity")
        elif result.similarity_score > 0.7:
            explanations.append("high similarity")
        elif result.similarity_score > 0.5:
            explanations.append("moderate similarity")
        else:
            explanations.append("low similarity")
        
        # Model explanation
        if index_type == IndexType.MARENGO_MULTIMODAL:
            explanations.append("using TwelveLabs Marengo multimodal embeddings")
        else:
            explanations.append("using Bedrock Titan text embeddings")
        
        return "; ".join(explanations)

    def _post_process_results(self,
                            results: List[SimilarityResult],
                            query: SimilarityQuery) -> List[SimilarityResult]:
        """Apply post-processing to search results."""
        processed = results
        
        # Apply similarity threshold
        if query.similarity_threshold > 0.0:
            processed = [r for r in processed if r.similarity_score >= query.similarity_threshold]
        
        # Deduplication
        if query.deduplicate_results:
            processed = self._deduplicate_results(processed)
        
        # Diversification
        if query.diversity_factor > 0.0:
            processed = self._apply_diversification(processed, query.diversity_factor)
        
        return processed

    def _deduplicate_results(self, results: List[SimilarityResult]) -> List[SimilarityResult]:
        """Remove duplicate results based on key and high metadata similarity."""
        if not results:
            return results
        
        deduplicated = [results[0]]
        
        for result in results[1:]:
            is_duplicate = False
            
            for existing in deduplicated:
                # Check exact key match
                if result.key == existing.key:
                    is_duplicate = True
                    break
                
                # Check high metadata similarity for same content type
                if (result.content_type == existing.content_type and
                    self._calculate_metadata_similarity(result.metadata, existing.metadata) > 0.95):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
        
        return deduplicated

    def _apply_diversification(self, 
                             results: List[SimilarityResult], 
                             diversity_factor: float) -> List[SimilarityResult]:
        """Apply diversification to reduce overly similar results."""
        if not results or diversity_factor <= 0.0:
            return results
        
        diversified = [results[0]]  # Keep top result
        
        for result in results[1:]:
            diversity_penalty = 1.0
            
            # Calculate penalty based on similarity to already selected results
            for selected in diversified:
                content_similarity = self._calculate_content_similarity(result, selected)
                diversity_penalty *= (1.0 - content_similarity * diversity_factor)
            
            # Adjust confidence score
            result.confidence_score = result.similarity_score * diversity_penalty
            diversified.append(result)
        
        # Re-sort by adjusted confidence
        diversified.sort(key=lambda x: x.confidence_score, reverse=True)
        return diversified

    def _calculate_metadata_similarity(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> float:
        """Calculate similarity between metadata dictionaries."""
        if not metadata1 or not metadata2:
            return 0.0
        
        common_keys = set(metadata1.keys()) & set(metadata2.keys())
        if not common_keys:
            return 0.0
        
        matches = sum(1 for key in common_keys if metadata1[key] == metadata2[key])
        return matches / len(common_keys)

    def _calculate_content_similarity(self, result1: SimilarityResult, result2: SimilarityResult) -> float:
        """Calculate content similarity between two results."""
        # Different content types are less similar
        if result1.content_type != result2.content_type:
            return 0.2
        
        # Base similarity on metadata
        metadata_sim = self._calculate_metadata_similarity(result1.metadata, result2.metadata)
        
        # For temporal content, consider overlap
        if (result1.content_type in ['video', 'audio'] and 
            result1.start_sec is not None and result2.start_sec is not None):
            temporal_sim = self._calculate_temporal_overlap(result1, result2)
            return (metadata_sim + temporal_sim) / 2.0
        
        return metadata_sim

    def _calculate_temporal_overlap(self, result1: SimilarityResult, result2: SimilarityResult) -> float:
        """Calculate temporal overlap between two temporal results."""
        start1, end1 = result1.start_sec or 0, result1.end_sec or 0
        start2, end2 = result2.start_sec or 0, result2.end_sec or 0
        
        if start1 >= end1 or start2 >= end2:
            return 0.0
        
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        
        if overlap_start >= overlap_end:
            return 0.0
        
        overlap_duration = overlap_end - overlap_start
        total_duration = max(end1, end2) - min(start1, start2)
        
        return overlap_duration / total_duration if total_duration > 0 else 0.0

    def _matches_metadata_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches the specified filters."""
        for key, filter_value in filters.items():
            if key not in metadata:
                return False
            
            metadata_value = metadata[key]
            
            if isinstance(filter_value, dict):
                # Handle comparison operators
                for op, value in filter_value.items():
                    if op == "$eq" and metadata_value != value:
                        return False
                    elif op == "$ne" and metadata_value == value:
                        return False
                    elif op == "$gt" and metadata_value <= value:
                        return False
                    elif op == "$gte" and metadata_value < value:
                        return False
                    elif op == "$lt" and metadata_value >= value:
                        return False
                    elif op == "$lte" and metadata_value > value:
                        return False
                    elif op == "$in" and metadata_value not in value:
                        return False
                    elif op == "$nin" and metadata_value in value:
                        return False
            elif isinstance(filter_value, list):
                if metadata_value not in filter_value:
                    return False
            else:
                if metadata_value != filter_value:
                    return False
        
        return True

    def _generate_search_response(self,
                                results: List[SimilarityResult],
                                query_id: str,
                                input_type: QueryInputType,
                                index_type: IndexType,
                                processing_time_ms: int,
                                cost: float,
                                query: SimilarityQuery) -> SimilaritySearchResponse:
        """Generate comprehensive search response with analytics."""
        # Result distribution by content type
        distribution = {}
        similarities = []
        
        for result in results:
            distribution[result.content_type] = distribution.get(result.content_type, 0) + 1
            similarities.append(result.similarity_score)
        
        # Similarity range
        if similarities:
            similarity_range = (min(similarities), max(similarities))
        else:
            similarity_range = (0.0, 0.0)
        
        # Generate suggestions
        suggestions = []
        if len(results) < query.top_k // 2:
            suggestions.append("Try reducing similarity threshold or expanding query terms")
        if similarities and max(similarities) < 0.5:
            suggestions.append("Consider using different query terms for better matches")
        if input_type == QueryInputType.TEXT and index_type == IndexType.MARENGO_MULTIMODAL:
            suggestions.append("This multimodal index supports video, audio, and image queries too")
        
        return SimilaritySearchResponse(
            results=results,
            total_results=len(results),
            query_id=query_id,
            input_type=input_type,
            index_type=index_type,
            processing_time_ms=processing_time_ms,
            result_distribution=distribution,
            similarity_range=similarity_range,
            cost_estimate=cost,
            search_suggestions=suggestions
        )

    def _update_search_stats(self, input_type: QueryInputType, processing_time_ms: int, cost: float, 
                           is_multi_index: bool = False, is_cross_vector: bool = False) -> None:
        """Update global search performance statistics."""
        with self._stats_lock:
            self.search_stats['total_searches'] += 1
            self.search_stats['total_cost'] += cost
            
            if is_multi_index:
                self.search_stats['multi_index_searches'] += 1
            if is_cross_vector:
                self.search_stats['cross_vector_searches'] += 1
            
            # Update input type stats
            input_key = input_type.value
            if input_key not in self.search_stats['searches_by_input_type']:
                self.search_stats['searches_by_input_type'][input_key] = 0
            self.search_stats['searches_by_input_type'][input_key] += 1
            
            # Update rolling average latency
            current_avg = self.search_stats['average_latency_ms']
            total_searches = self.search_stats['total_searches']
            self.search_stats['average_latency_ms'] = (
                (current_avg * (total_searches - 1) + processing_time_ms) / total_searches
            )

    def get_engine_capabilities(self) -> Dict[str, Any]:
        """Get comprehensive information about search engine capabilities."""
        return {
            'supported_index_types': [t.value for t in IndexType],
            'supported_input_types': [t.value for t in QueryInputType],
            'index_compatibility': {
                'marengo_multimodal': ['text', 'video_file', 'video_key', 'audio_file', 'image_file', 'embedding'],
                'titan_text': ['text', 'embedding']
            },
            'features': [
                'Multimodal search within same embedding space',
                'Natural language query processing', 
                'Temporal video/audio search',
                'Advanced metadata filtering',
                'Result deduplication and diversification',
                'Entity extraction and synonym expansion',
                'Performance analytics and cost tracking',
                'S3 Vector native filtering'
            ],
            'models_supported': {
                'marengo': 'twelvelabs.marengo-embed-2-7-v1:0',
                'titan_text': 'amazon.titan-embed-text-v2:0'
            },
            'performance_stats': dict(self.search_stats)
        }