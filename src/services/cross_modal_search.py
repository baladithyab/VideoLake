"""
Cross-Modal Search Engine Service

This service enables cross-modal search capabilities between text and video embeddings,
bridging different embedding spaces for unified search experiences. It handles:
- Text-to-video search: Finding video segments using natural language queries
- Video-to-video search: Finding similar video content across libraries
- Cross-modal similarity: Bridging text and video embeddings through semantic mapping

The service addresses the challenge of different embedding spaces:
- Text embeddings (Bedrock Titan Text V2): 1024 dimensions  
- Video embeddings (TwelveLabs Marengo): 1024 dimensions
"""

import json
import time
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorEmbeddingError, ValidationError, VectorStorageError
from src.utils.logging_config import get_logger
from src.config import config_manager

logger = get_logger(__name__)


@dataclass
class CrossModalSearchResult:
    """Result from cross-modal search operations."""
    query_type: str  # "text_to_video", "video_to_video", "hybrid"
    results: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]
    processing_time_ms: int
    similarity_scores: List[float]
    total_results: int


@dataclass
class SearchQuery:
    """Unified search query structure for cross-modal operations."""
    query_text: Optional[str] = None
    query_video_key: Optional[str] = None
    query_embedding: Optional[List[float]] = None
    embedding_type: Optional[str] = None  # "text", "video"
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 10
    include_cross_modal: bool = True


class CrossModalSearchEngine:
    """
    Cross-modal search engine that enables searching across text and video embeddings.
    
    This service provides:
    1. Text-to-video search: Natural language queries to find relevant video segments
    2. Video-to-video search: Find similar video content using video embeddings
    3. Unified search: Combine both modalities for comprehensive results
    4. Semantic bridging: Handle different embedding dimensions through projection
    """
    
    def __init__(self, 
                 text_storage_service: Optional[EmbeddingStorageIntegration] = None,
                 video_storage_service: Optional[VideoEmbeddingStorageService] = None,
                 bedrock_service: Optional[BedrockEmbeddingService] = None,
                 s3_vector_manager: Optional[S3VectorStorageManager] = None):
        """
        Initialize the cross-modal search engine.
        
        Args:
            text_storage_service: Service for text embedding operations
            video_storage_service: Service for video embedding operations  
            bedrock_service: Bedrock service for text embedding generation
            s3_vector_manager: S3 Vector storage manager
        """
        self.text_storage = text_storage_service or EmbeddingStorageIntegration()
        self.video_storage = video_storage_service or VideoEmbeddingStorageService()
        self.bedrock_service = bedrock_service or BedrockEmbeddingService()
        self.s3_vector_manager = s3_vector_manager or S3VectorStorageManager()
        
        # Dimensionality mapping for cross-modal search
        self.text_embedding_dim = 1024  # Bedrock Titan Text V2
        self.video_embedding_dim = 1024  # TwelveLabs Marengo
        
        # Note: Semantic bridge functionality removed - using simple dimension adjustment instead
        
        logger.info("CrossModalSearchEngine initialized")

    def search_text_to_video(self,
                           query_text: str,
                           video_index_arn: str,
                           top_k: int = 10,
                           time_range_filter: Optional[Dict[str, float]] = None,
                           content_filters: Optional[Dict[str, Any]] = None,
                           ) -> CrossModalSearchResult:
        """
        Search for video segments using natural language text queries.
        
        This method generates a text embedding and searches for semantically similar
        video segments using simple dimension adjustment to handle different embedding spaces.
        
        Args:
            query_text: Natural language query
            video_index_arn: ARN of the video index to search
            top_k: Number of results to return
            time_range_filter: Optional temporal filtering
            content_filters: Optional metadata filters
            
        Returns:
            CrossModalSearchResult with video segments matching the text query
            
        Raises:
            ValidationError: If inputs are invalid
            VectorEmbeddingError: If text embedding generation fails
            VectorStorageError: If video search fails
        """
        start_time = time.time()
        logger.info(f"Starting text-to-video search: '{query_text[:100]}...'")
        
        # Validate inputs
        if not query_text or not query_text.strip():
            raise ValidationError("Query text cannot be empty")
        if not video_index_arn:
            raise ValidationError("Video index ARN is required")
        if top_k <= 0:
            raise ValidationError("top_k must be positive")
            
        try:
            # Generate text embedding for cross-modal search
            # Note: For true cross-modal compatibility, both text and video should use the same embedding model
            # Currently using Titan for text and Marengo for video - this creates a semantic gap
            logger.debug("Generating text embedding for cross-modal search")
            
            # Generate text embedding using Bedrock Titan
            # TODO: For better cross-modal results, consider:
            # 1. Using a unified multimodal model (e.g., CLIP-style)
            # 2. Training a projection layer between Titan and Marengo spaces
            # 3. Using TwelveLabs text embedding if available
            embedding_result = self.bedrock_service.generate_text_embedding(query_text.strip())
            text_embedding = embedding_result.embedding
            
            # Truncate/pad to match video embedding dimensions (1024 for Marengo)
            if len(text_embedding) > self.video_embedding_dim:
                query_vector = text_embedding[:self.video_embedding_dim]
            else:
                query_vector = text_embedding + [0.0] * (self.video_embedding_dim - len(text_embedding))
            
            # Search in video index
            logger.debug(f"Searching video index with projected embedding (dim: {len(query_vector)})")
            search_results = self.video_storage.search_video_segments(
                index_arn=video_index_arn,
                query_vector=query_vector,
                top_k=top_k,
                time_range_filter=time_range_filter,
                content_filters=content_filters
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Extract results and scores
            results = search_results.get('results', [])
            scores = [result.get('similarity_score', 0.0) for result in results]
            
            search_metadata = {
                'query_text': query_text,
                'query_embedding_dim': len(text_embedding),
                'projected_embedding_dim': len(query_vector),
                'video_index_arn': video_index_arn,
                'dimension_adjustment': 'truncate_pad',  # Simple approach without semantic bridge
                'time_range_filter': time_range_filter,
                'content_filters': content_filters,
                'model_used': embedding_result.model_id,
                'cross_modal_note': 'Using Titan embedding with dimension adjustment - should use Marengo for production'
            }
            
            logger.info(f"Text-to-video search completed: {len(results)} results in {processing_time_ms}ms")
            
            return CrossModalSearchResult(
                query_type="text_to_video",
                results=results,
                search_metadata=search_metadata,
                processing_time_ms=processing_time_ms,
                similarity_scores=scores,
                total_results=len(results)
            )
            
        except Exception as e:
            logger.error(f"Text-to-video search failed: {str(e)}")
            if isinstance(e, (ValidationError, VectorEmbeddingError, VectorStorageError)):
                raise
            raise VectorEmbeddingError(f"Text-to-video search failed: {str(e)}")

    def search_video_to_video(self,
                            query_video_key: str,
                            video_index_arn: str,
                            top_k: int = 10,
                            time_range_filter: Optional[Dict[str, float]] = None,
                            content_filters: Optional[Dict[str, Any]] = None,
                            exclude_self: bool = True) -> CrossModalSearchResult:
        """
        Search for similar video segments using a reference video segment.
        
        Args:
            query_video_key: Key of the reference video segment
            video_index_arn: ARN of the video index to search
            top_k: Number of results to return
            time_range_filter: Optional temporal filtering
            content_filters: Optional metadata filters
            exclude_self: Whether to exclude the query video from results
            
        Returns:
            CrossModalSearchResult with similar video segments
            
        Raises:
            ValidationError: If inputs are invalid
            VectorStorageError: If vector operations fail
        """
        start_time = time.time()
        logger.info(f"Starting video-to-video search for key: {query_video_key}")
        
        # Validate inputs
        if not query_video_key:
            raise ValidationError("Query video key cannot be empty")
        if not video_index_arn:
            raise ValidationError("Video index ARN is required")
        if top_k <= 0:
            raise ValidationError("top_k must be positive")
            
        try:
            # Get the reference video embedding
            logger.debug("Retrieving reference video embedding")
            reference_vectors = self.s3_vector_manager.list_vectors(
                index_arn=video_index_arn,
                max_results=100,
                return_data=True
            )
            
            if not reference_vectors or 'vectors' not in reference_vectors or len(reference_vectors['vectors']) == 0:
                raise VectorStorageError(f"Reference video not found: {query_video_key}")
            
            # Find the specific vector by key
            reference_vector_data = None
            for vector in reference_vectors['vectors']:
                if vector.get('key') == query_video_key:
                    reference_vector_data = vector
                    break
            
            if not reference_vector_data:
                raise VectorStorageError(f"Reference video not found: {query_video_key}")
                
            query_vector = reference_vector_data['data']['float32']
            
            # Adjust top_k if excluding self
            search_top_k = top_k + 1 if exclude_self else top_k
            
            # Search for similar videos
            logger.debug(f"Searching for similar videos (top_k: {search_top_k})")
            search_results = self.video_storage.search_video_segments(
                index_arn=video_index_arn,
                query_vector=query_vector,
                top_k=search_top_k,
                time_range_filter=time_range_filter,
                content_filters=content_filters
            )
            
            # Filter out self if requested
            results = search_results.get('results', [])
            if exclude_self:
                results = [r for r in results if r.get('key') != query_video_key][:top_k]
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            scores = [result.get('similarity_score', 0.0) for result in results]
            
            search_metadata = {
                'query_video_key': query_video_key,
                'video_index_arn': video_index_arn,
                'exclude_self': exclude_self,
                'time_range_filter': time_range_filter,
                'content_filters': content_filters,
                'reference_metadata': reference_vector_data.get('metadata', {})
            }
            
            logger.info(f"Video-to-video search completed: {len(results)} results in {processing_time_ms}ms")
            
            return CrossModalSearchResult(
                query_type="video_to_video",
                results=results,
                search_metadata=search_metadata,
                processing_time_ms=processing_time_ms,
                similarity_scores=scores,
                total_results=len(results)
            )
            
        except Exception as e:
            logger.error(f"Video-to-video search failed: {str(e)}")
            if isinstance(e, (ValidationError, VectorStorageError)):
                raise
            raise VectorStorageError(f"Video-to-video search failed: {str(e)}")

    def unified_search(self,
                      search_query: SearchQuery,
                      text_index_arn: Optional[str] = None,
                      video_index_arn: Optional[str] = None) -> Dict[str, CrossModalSearchResult]:
        """
        Perform unified search across both text and video modalities.
        
        Args:
            search_query: Unified search query object
            text_index_arn: ARN of text index (required for text results)
            video_index_arn: ARN of video index (required for video results)
            
        Returns:
            Dictionary with separate results for each modality
            
        Raises:
            ValidationError: If inputs are invalid
        """
        start_time = time.time()
        logger.info("Starting unified cross-modal search")
        
        results = {}
        
        # Text search (if text query provided and text index available)
        if search_query.query_text and text_index_arn:
            logger.debug("Performing text-to-text search")
            try:
                text_results = self.text_storage.search_similar_text(
                    query_text=search_query.query_text,
                    index_arn=text_index_arn,
                    top_k=search_query.top_k,
                    metadata_filters=search_query.filters
                )
                
                # Convert to CrossModalSearchResult format
                results['text'] = CrossModalSearchResult(
                    query_type="text_to_text",
                    results=text_results.get('results', []),
                    search_metadata=text_results.get('metadata', {}),
                    processing_time_ms=text_results.get('processing_time_ms', 0),
                    similarity_scores=[r.get('similarity_score', 0.0) for r in text_results.get('results', [])],
                    total_results=len(text_results.get('results', []))
                )
            except Exception as e:
                logger.warning(f"Text search failed: {str(e)}")
        
        # Cross-modal text-to-video search
        if search_query.query_text and video_index_arn and search_query.include_cross_modal:
            logger.debug("Performing text-to-video search")
            try:
                results['text_to_video'] = self.search_text_to_video(
                    query_text=search_query.query_text,
                    video_index_arn=video_index_arn,
                    top_k=search_query.top_k,
                    content_filters=search_query.filters
                )
            except Exception as e:
                logger.warning(f"Text-to-video search failed: {str(e)}")
        
        # Video-to-video search
        if search_query.query_video_key and video_index_arn:
            logger.debug("Performing video-to-video search")
            try:
                results['video_to_video'] = self.search_video_to_video(
                    query_video_key=search_query.query_video_key,
                    video_index_arn=video_index_arn,
                    top_k=search_query.top_k,
                    content_filters=search_query.filters
                )
            except Exception as e:
                logger.warning(f"Video-to-video search failed: {str(e)}")
        
        total_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Unified search completed with {len(results)} result sets in {total_time_ms}ms")
        
        return results

    # Semantic bridge functionality removed - using simple dimension adjustment instead

    def _project_text_to_video(self, text_embedding: List[float]) -> List[float]:
        """Simple projection by truncating/padding dimensions."""
        # Simple approach: truncate or pad to match video embedding dimensions
        if len(text_embedding) > self.video_embedding_dim:
            return text_embedding[:self.video_embedding_dim]
        else:
            return text_embedding + [0.0] * (self.video_embedding_dim - len(text_embedding))

    def _project_video_to_text(self, video_embedding: List[float]) -> List[float]:
        """Simple projection by truncating/padding dimensions."""
        # Simple approach: truncate or pad to match text embedding dimensions
        if len(video_embedding) > self.text_embedding_dim:
            return video_embedding[:self.text_embedding_dim]
        else:
            return video_embedding + [0.0] * (self.text_embedding_dim - len(video_embedding))

    def _sample_embeddings(self, index_arn: str, sample_size: int, embedding_type: str) -> List[Dict[str, Any]]:
        """Sample embeddings from an index for training purposes."""
        bucket_name = self._extract_bucket_from_arn(index_arn)
        index_name = self._extract_index_from_arn(index_arn)
        
        # Note: list_vectors doesn't support metadata filtering directly
        # We would need to filter results after retrieving them
        response = self.s3_vector_manager.list_vectors(
            index_arn=index_arn,
            max_results=sample_size,
            return_metadata=True
        )
        
        embeddings = []
        for vector in response.get('vectors', []):
            embeddings.append({
                'key': vector['key'],
                'embedding': vector['data']['float32'],
                'metadata': vector.get('metadata', {})
            })
        
        return embeddings

    def _extract_bucket_from_arn(self, arn: str) -> str:
        """Extract bucket name from S3 Vector index ARN."""
        # ARN format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
        parts = arn.split('/')
        if len(parts) >= 2:
            return parts[1]
        raise ValidationError(f"Invalid ARN format: {arn}")

    def _extract_index_from_arn(self, arn: str) -> str:
        """Extract index name from S3 Vector index ARN."""
        # ARN format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
        parts = arn.split('/')
        if len(parts) >= 4:
            return parts[3]
        raise ValidationError(f"Invalid ARN format: {arn}")

    def get_search_capabilities(self) -> Dict[str, Any]:
        """
        Get information about current search capabilities and configuration.
        
        Returns:
            Dictionary with capability information
        """
        return {
            'modalities_supported': ['text', 'video'],
            'search_types': [
                'text_to_text',
                'text_to_video', 
                'video_to_video',
                'unified_search'
            ],
            'embedding_dimensions': {
                'text': self.text_embedding_dim,
                'video': self.video_embedding_dim
            },
            'dimension_adjustment': {
                'text_to_video': 'truncate_pad',
                'video_to_text': 'truncate_pad'
            },
            'features': [
                'Cross-modal projection',
                'Temporal filtering for video',
                'Metadata filtering',
                'Batch operations',
                'Cost optimization'
            ]
        }