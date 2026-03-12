"""
Service Locator for Frontend-Backend Integration

This module provides a simple service locator pattern that allows 
frontend components to access backend services without complex
dependency injection or circular imports.
"""

from typing import Optional, Dict, Any
import streamlit as st
import logging

logger = logging.getLogger(__name__)


class ServiceLocator:
    """
    Simple service locator for frontend-backend integration.
    
    This enables frontend components to access backend services
    through a centralized registry, avoiding circular dependencies
    and complex initialization patterns.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
        
    def register_service(self, service_name: str, service_instance: Any) -> None:
        """Register a service in the locator."""
        self._services[service_name] = service_instance
        logger.debug(f"Registered service: {service_name}")
    
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service from the locator."""
        return self._services.get(service_name)
    
    def is_available(self, service_name: str) -> bool:
        """Check if a service is available."""
        return service_name in self._services
    
    def get_available_services(self) -> list:
        """Get list of available service names."""
        return list(self._services.keys())
    
    def initialize_backend_services(self) -> bool:
        """Initialize backend services if not already done."""
        if self._initialized:
            return True
            
        try:
            # Try to initialize core backend services
            self._init_similarity_search_engine()
            self._init_multi_vector_coordinator()
            self._init_storage_services()
            self._init_embedding_services()
            
            self._initialized = True
            logger.info("Backend services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize backend services: {str(e)}")
            return False
    
    def _init_similarity_search_engine(self) -> None:
        """Initialize similarity search engine."""
        try:
            from src.services.similarity_search_engine import SimilaritySearchEngine
            search_engine = SimilaritySearchEngine()
            self.register_service('similarity_search_engine', search_engine)
        except Exception as e:
            logger.warning(f"Could not initialize similarity search engine: {str(e)}")
    
    def _init_multi_vector_coordinator(self) -> None:
        """Initialize multi-vector coordinator."""
        try:
            from src.services.multi_vector_coordinator import MultiVectorCoordinator
            coordinator = MultiVectorCoordinator()
            self.register_service('multi_vector_coordinator', coordinator)
        except Exception as e:
            logger.warning(f"Could not initialize multi-vector coordinator: {str(e)}")
    
    def _init_storage_services(self) -> None:
        """Initialize storage services."""
        try:
            from src.services.s3_vector_storage import S3VectorStorageManager
            storage_manager = S3VectorStorageManager()
            self.register_service('s3_vector_storage', storage_manager)
        except Exception as e:
            logger.warning(f"Could not initialize S3 vector storage: {str(e)}")
            
        try:
            from src.services.comprehensive_video_processing_service import ComprehensiveVideoProcessingService
            video_storage = ComprehensiveVideoProcessingService()
            self.register_service('video_storage', video_storage)
        except Exception as e:
            logger.warning(f"Could not initialize video storage: {str(e)}")
    
    def _init_embedding_services(self) -> None:
        """Initialize embedding services."""
        try:
            from src.services.bedrock_embedding import BedrockEmbeddingService
            bedrock_service = BedrockEmbeddingService()
            self.register_service('bedrock_service', bedrock_service)
        except Exception as e:
            logger.warning(f"Could not initialize Bedrock service: {str(e)}")
            
        try:
            from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
            twelvelabs_service = TwelveLabsVideoProcessingService()
            self.register_service('twelvelabs_service', twelvelabs_service)
        except Exception as e:
            logger.warning(f"Could not initialize TwelveLabs service: {str(e)}")
    
    def execute_search(self, query: str, vector_types: list, top_k: int = 10, 
                      similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """
        Execute a search using available backend services.
        
        Args:
            query: Search query text
            vector_types: List of vector types to search
            top_k: Number of results to return
            similarity_threshold: Minimum similarity threshold
            
        Returns:
            Dictionary with search results
        """
        try:
            # Try to use similarity search engine first
            search_engine = self.get_service('similarity_search_engine')
            if search_engine:
                return self._execute_search_engine_search(
                    search_engine, query, vector_types, top_k, similarity_threshold
                )
            
            # Fallback to coordinator
            coordinator = self.get_service('multi_vector_coordinator')
            if coordinator:
                return self._execute_coordinator_search(
                    coordinator, query, vector_types, top_k, similarity_threshold
                )
            
            # If no services available, return empty results
            logger.warning("No backend search services available")
            return {
                'query': query,
                'vector_types': vector_types,
                'results': [],
                'message': 'No backend services available'
            }
            
        except Exception as e:
            logger.error(f"Search execution failed: {str(e)}")
            return {
                'query': query,
                'vector_types': vector_types,
                'results': [],
                'error': str(e)
            }
    
    def _execute_search_engine_search(self, search_engine, query: str, 
                                    vector_types: list, top_k: int, 
                                    similarity_threshold: float) -> Dict[str, Any]:
        """Execute search using similarity search engine."""
        try:
            # For now, use a simple text search approach
            # This would be expanded to use the proper interface when ready
            from src.services.similarity_search_engine import IndexType
            
            # Mock index ARN for demo
            index_arn = "arn:aws:s3vectors:us-east-1:123456789012:index/demo-index"
            
            response = search_engine.search_by_text_query(
                query_text=query,
                index_arn=index_arn,
                index_type=IndexType.MARENGO_MULTIMODAL,
                top_k=top_k,
                metadata_filters={'similarity_threshold': similarity_threshold}
            )
            
            # Convert response to frontend format
            results = []
            for result in response.results:
                results.append({
                    'segment_id': result.key,
                    'similarity': result.similarity_score,
                    'vector_type': result.embedding_option or 'visual-text',
                    'start_time': result.start_sec or 0.0,
                    'end_time': result.end_sec or 10.0,
                    'metadata': result.metadata
                })
            
            return {
                'query': query,
                'vector_types': vector_types,
                'results': results,
                'processing_time_ms': response.processing_time_ms,
                'total_results': response.total_results
            }
            
        except Exception as e:
            logger.error(f"Search engine execution failed: {str(e)}")
            raise
    
    def _execute_coordinator_search(self, coordinator, query: str, 
                                  vector_types: list, top_k: int, 
                                  similarity_threshold: float) -> Dict[str, Any]:
        """Execute search using multi-vector coordinator."""
        try:
            # Use coordinator's search capabilities
            from src.services.multi_vector_coordinator import SearchRequest
            
            search_request = SearchRequest(
                query_text=query,
                vector_types=vector_types,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            response = coordinator.search_multi_vector(search_request)
            
            return {
                'query': query,
                'vector_types': vector_types,
                'results': response.get('results', []),
                'processing_time_ms': response.get('processing_time_ms', 0),
                'search_id': response.get('search_id', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Coordinator search execution failed: {str(e)}")
            raise


# Global service locator instance
_service_locator = None


def get_service_locator() -> ServiceLocator:
    """Get the global service locator instance."""
    global _service_locator
    
    if _service_locator is None:
        _service_locator = ServiceLocator()
        
        # Initialize on first access
        if not _service_locator._initialized:
            _service_locator.initialize_backend_services()
    
    return _service_locator


def get_backend_service(service_name: str) -> Optional[Any]:
    """Get a backend service by name."""
    locator = get_service_locator()
    return locator.get_service(service_name)


def execute_backend_search(query: str, vector_types: list, top_k: int = 10, 
                          similarity_threshold: float = 0.0) -> Dict[str, Any]:
    """Execute a search using available backend services."""
    locator = get_service_locator()
    return locator.execute_search(query, vector_types, top_k, similarity_threshold)


# Streamlit session state integration
def init_services_in_session():
    """Initialize services in Streamlit session state."""
    if 'service_locator' not in st.session_state:
        st.session_state.service_locator = get_service_locator()
        
        # Store service status in session state
        locator = st.session_state.service_locator
        st.session_state.backend_services_available = locator._initialized
        st.session_state.available_services = locator.get_available_services()


def get_session_service_locator() -> ServiceLocator:
    """Get service locator from Streamlit session state."""
    if 'service_locator' not in st.session_state:
        init_services_in_session()
    
    return st.session_state.service_locator