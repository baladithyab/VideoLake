"""
Streamlit Integration Utilities for Enhanced Multi-Vector Architecture

This module provides utilities for integrating the enhanced multi-vector services
with the Streamlit application, including initialization, configuration management,
and unified API endpoints for the enhanced architecture.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.services.multi_vector_coordinator import MultiVectorCoordinator, MultiVectorConfig, SearchRequest
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.similarity_search_engine import SimilaritySearchEngine
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StreamlitIntegrationConfig:
    """Configuration for Streamlit integration."""
    enable_multi_vector: bool = True
    enable_concurrent_processing: bool = True
    default_vector_types: Optional[List[str]] = None
    max_concurrent_jobs: int = 8
    enable_performance_monitoring: bool = True
    
    def __post_init__(self):
        if self.default_vector_types is None:
            self.default_vector_types = ["visual-text", "visual-image", "audio"]


class StreamlitServiceManager:
    """
    Manages enhanced services for Streamlit integration with multi-vector capabilities.
    
    This manager provides:
    1. Unified service initialization and configuration
    2. Simplified API for Streamlit components
    3. Service coordination and health monitoring
    4. Performance tracking and optimization
    """
    
    def __init__(self, config: Optional[StreamlitIntegrationConfig] = None):
        """
        Initialize the Streamlit Service Manager.
        
        Args:
            config: Integration configuration
        """
        self.config = config or StreamlitIntegrationConfig()
        
        # Initialize core services
        self._initialize_services()
        
        # Setup multi-vector coordinator
        if self.config.enable_multi_vector:
            try:
                self._initialize_multi_vector_coordinator()
            except Exception as e:
                logger.error(f"Multi-vector coordinator initialization failed: {e}")
                # Don't fail the entire service manager, but log the issue
                self.multi_vector_coordinator = None
        
        logger.info("StreamlitServiceManager initialized successfully")

    def _initialize_services(self) -> None:
        """Initialize all core services."""
        try:
            # Initialize real AWS services only
            self.storage_manager = S3VectorStorageManager()
            self.search_engine = SimilaritySearchEngine()
            self.twelvelabs_service = TwelveLabsVideoProcessingService()
            self.bedrock_service = BedrockEmbeddingService()
            
            logger.info("Core services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize core services: {e}")
            raise RuntimeError(f"Service initialization failed. Ensure AWS credentials and resources are properly configured: {e}")

    def _initialize_multi_vector_coordinator(self) -> None:
        """Initialize the multi-vector coordinator."""
        try:
            vector_types = self.config.default_vector_types or ["visual-text", "visual-image", "audio"]
            multi_vector_config = MultiVectorConfig(
                vector_types=vector_types,
                max_concurrent_jobs=self.config.max_concurrent_jobs,
                enable_cross_vector_search=True,
                fusion_method="weighted_average"
            )
            
            # Validate that required services are available
            if not self.twelvelabs_service:
                raise RuntimeError("TwelveLabs service not initialized")
            if not self.search_engine:
                raise RuntimeError("Search engine not initialized")
            if not self.storage_manager:
                raise RuntimeError("Storage manager not initialized")
            if not self.bedrock_service:
                raise RuntimeError("Bedrock service not initialized")
            
            self.multi_vector_coordinator = MultiVectorCoordinator(
                config=multi_vector_config,
                twelvelabs_service=self.twelvelabs_service,
                search_engine=self.search_engine,
                storage_manager=self.storage_manager,
                bedrock_service=self.bedrock_service
            )
            
            # Validate coordinator was created successfully
            if self.multi_vector_coordinator is None:
                raise RuntimeError("MultiVectorCoordinator creation returned None")
            
            logger.info("Multi-vector coordinator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize multi-vector coordinator: {e}")
            self.multi_vector_coordinator = None
            # Re-raise the exception so calling code knows initialization failed
            raise RuntimeError(f"MultiVectorCoordinator initialization failed: {e}")

    def create_multi_index_architecture(self,
                                      bucket_name: str,
                                      vector_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a multi-index architecture for Streamlit application.
        
        Args:
            bucket_name: S3 Vector bucket name
            vector_types: Vector types to create indexes for
            
        Returns:
            Dictionary with creation results
        """
        vector_types = vector_types or self.config.default_vector_types or ["visual-text", "visual-image", "audio"]
        
        logger.info(f"Creating multi-index architecture: bucket={bucket_name}, types={vector_types}")
        
        try:
            result = self.storage_manager.create_multi_index_architecture(
                bucket_name=bucket_name,
                vector_types=vector_types,
                base_dimensions=1024,
                distance_metric="cosine"
            )
            
            # Register indexes with search engine
            for vector_type, index_result in result['index_results'].items():
                if index_result.get('status') == 'created':
                    index_arn = index_result.get('response', {}).get('indexArn')
                    if index_arn:
                        self.search_engine.register_index(
                            index_arn=index_arn,
                            index_type=self._get_index_type_for_vector(vector_type),
                            vector_types=[vector_type]
                        )
            
            logger.info(f"Multi-index architecture created successfully: {result['successful_indexes']} indexes")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create multi-index architecture: {e}")
            raise

    def process_video_multi_vector(self,
                                 video_inputs: List[Dict[str, Any]],
                                 vector_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Process videos with multi-vector capabilities for Streamlit.
        
        Args:
            video_inputs: List of video input configurations
            vector_types: Vector types to generate
            
        Returns:
            Dictionary with processing results
        """
        if not self.multi_vector_coordinator:
            raise RuntimeError("Multi-vector coordinator not initialized")
        
        vector_types = vector_types or self.config.default_vector_types or ["visual-text", "visual-image", "audio"]
        
        logger.info(f"Processing {len(video_inputs)} videos with {len(vector_types)} vector types")
        
        try:
            result = self.multi_vector_coordinator.process_multi_vector_content(
                content_inputs=video_inputs,
                vector_types=vector_types
            )
            
            # Format result for Streamlit display
            return {
                'success': True,
                'results_by_type': result.results_by_type,
                'processing_stats': result.processing_stats,
                'processing_time_ms': result.total_processing_time_ms,
                'successful_types': result.successful_types,
                'failed_types': result.failed_types,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Multi-vector video processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': 0
            }

    def search_multi_vector(self,
                          query_text: Optional[str] = None,
                          query_media_uri: Optional[str] = None,
                          vector_types: Optional[List[str]] = None,
                          top_k: int = 10,
                          fusion_method: str = "weighted_average") -> Dict[str, Any]:
        """
        Perform multi-vector search for Streamlit interface.
        
        Args:
            query_text: Text query
            query_media_uri: Media file URI for query
            vector_types: Vector types to search
            top_k: Number of results to return
            fusion_method: Method for combining results
            
        Returns:
            Dictionary with search results
        """
        if not self.multi_vector_coordinator:
            raise RuntimeError("Multi-vector coordinator not initialized")
        
        vector_types = vector_types or self.config.default_vector_types or ["visual-text", "visual-image", "audio"]
        
        logger.info(f"Performing multi-vector search across {len(vector_types)} types")
        
        try:
            search_request = SearchRequest(
                query_text=query_text,
                query_media_uri=query_media_uri,
                vector_types=vector_types,
                top_k=top_k,
                fusion_method=fusion_method,
                enable_cross_type_fusion=True
            )
            
            result = self.multi_vector_coordinator.search_multi_vector(search_request)
            
            # Format result for Streamlit display
            return {
                'success': True,
                'search_id': result['search_id'],
                'results': result['results'],
                'processing_time_ms': result['processing_time_ms'],
                'metadata': result['metadata']
            }
            
        except Exception as e:
            logger.error(f"Multi-vector search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time_ms': 0
            }

    def store_vectors_multi_index(self,
                                vectors_by_type: Dict[str, List[Dict[str, Any]]],
                                bucket_name: str) -> Dict[str, Any]:
        """
        Store vectors across multiple indexes for Streamlit.
        
        Args:
            vectors_by_type: Vectors organized by type
            bucket_name: Target bucket name
            
        Returns:
            Dictionary with storage results
        """
        logger.info(f"Storing vectors across {len(vectors_by_type)} vector types")
        
        try:
            result = self.storage_manager.put_vectors_multi_index(
                vectors_by_type=vectors_by_type,
                bucket_name=bucket_name
            )
            
            # Format result for Streamlit display
            return {
                'success': True,
                'results_by_type': result['results_by_type'],
                'total_vectors_stored': result['total_vectors_stored'],
                'successful_types': result['successful_types'],
                'failed_types': result['failed_types_count']
            }
            
        except Exception as e:
            logger.error(f"Multi-index vector storage failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_vectors_stored': 0
            }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status for Streamlit dashboard.
        
        Returns:
            Dictionary with system status and statistics
        """
        status = {
            'services': {
                'storage_manager': self._check_service_health(self.storage_manager),
                'search_engine': self._check_service_health(self.search_engine),
                'twelvelabs_service': self._check_service_health(self.twelvelabs_service),
                'bedrock_service': self._check_service_health(self.bedrock_service),
                'multi_vector_coordinator': self._check_service_health(self.multi_vector_coordinator)
            },
            'configuration': {
                'multi_vector_enabled': self.config.enable_multi_vector,
                'concurrent_processing': self.config.enable_concurrent_processing,
                'default_vector_types': self.config.default_vector_types,
                'max_concurrent_jobs': self.config.max_concurrent_jobs
            }
        }
        
        # Add performance stats if available
        if self.multi_vector_coordinator:
            try:
                coordination_stats = self.multi_vector_coordinator.get_coordination_stats()
                status['performance'] = coordination_stats['performance']
                status['active_workflows'] = coordination_stats['active_workflows']
                status['storage_stats'] = coordination_stats['storage_stats']
            except Exception as e:
                logger.warning(f"Could not retrieve coordination stats: {e}")
        
        return status

    def _check_service_health(self, service: Any) -> Dict[str, Any]:
        """Check health status of a service."""
        if service is None:
            return {'status': 'not_initialized', 'healthy': False}
        
        try:
            # Basic health check - service exists and has expected attributes
            service_type = type(service).__name__
            return {
                'status': 'healthy',
                'healthy': True,
                'type': service_type,
                'initialized_at': getattr(service, '_initialized_at', 'unknown')
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'healthy': False,
                'error': str(e)
            }

    def _get_index_type_for_vector(self, vector_type: str):
        """Get appropriate index type for vector type."""
        from src.services.similarity_search_engine import IndexType
        
        if vector_type in ['visual-text', 'visual-image', 'audio']:
            return IndexType.MARENGO_MULTIMODAL
        elif vector_type == 'text-titan':
            return IndexType.TITAN_TEXT
        else:
            return IndexType.MARENGO_MULTIMODAL  # Default

    def get_vector_type_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """
        Get capabilities and configuration for each vector type.
        
        Returns:
            Dictionary mapping vector types to their capabilities
        """
        capabilities = {}
        
        vector_types = self.config.default_vector_types or ["visual-text", "visual-image", "audio"]
        for vector_type in vector_types:
            if hasattr(self.storage_manager, 'vector_type_configs') and vector_type in self.storage_manager.vector_type_configs:
                config = self.storage_manager.vector_type_configs[vector_type]
                capabilities[vector_type] = {
                    'dimensions': config['dimensions'],
                    'default_metric': config['default_metric'],
                    'supported_operations': ['embedding', 'storage', 'search'],
                    'service_provider': self._get_service_provider_for_type(vector_type),
                    'processing_mode': 'batch' if vector_type in ['visual-text', 'visual-image', 'audio'] else 'single'
                }
            else:
                # Fail gracefully if vector type configuration is not available
                logger.error(f"Vector type configuration not found for: {vector_type}")
                raise RuntimeError(f"Vector type {vector_type} is not properly configured. Check storage manager initialization.")
        
        return capabilities

    def _get_service_provider_for_type(self, vector_type: str) -> str:
        """Get the service provider for a vector type."""
        if vector_type in ['visual-text', 'visual-image', 'audio']:
            return 'TwelveLabs'
        elif vector_type == 'text-titan':
            return 'Bedrock'
        else:
            return 'Unknown'

    def cleanup(self) -> None:
        """Cleanup resources and shutdown services."""
        logger.info("Cleaning up StreamlitServiceManager")
        
        try:
            if hasattr(self, 'multi_vector_coordinator') and self.multi_vector_coordinator:
                self.multi_vector_coordinator.shutdown()
            
            # Additional cleanup for other services if needed
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info("StreamlitServiceManager cleanup completed")



# Global service manager instance for Streamlit
_service_manager = None


def get_service_manager(config: Optional[StreamlitIntegrationConfig] = None) -> StreamlitServiceManager:
    """
    Get or create the global service manager instance for Streamlit.
    
    Args:
        config: Optional configuration (only used on first call)
        
    Returns:
        StreamlitServiceManager instance
    """
    global _service_manager
    
    if _service_manager is None:
        _service_manager = StreamlitServiceManager(config)
    
    return _service_manager


def reset_service_manager() -> None:
    """Reset the global service manager (useful for testing)."""
    global _service_manager
    
    if _service_manager:
        _service_manager.cleanup()
    
    _service_manager = None