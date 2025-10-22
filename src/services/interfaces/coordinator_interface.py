"""
Coordinator Service Interface

Abstract interface for multi-vector coordination services,
enabling dependency inversion and breaking circular dependencies.

Note: Processing is always parallel since Bedrock operations are async.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ProcessingResult:
    """Result from multi-vector processing operation.

    All processing is done in parallel with async job polling.
    """
    results_by_type: Dict[str, Any]
    processing_stats: Dict[str, Any]
    total_processing_time_ms: int
    successful_types: List[str]
    failed_types: List[str]
    metadata: Dict[str, Any]


@dataclass
class CoordinatorSearchRequest:
    """Unified search request for coordinator services."""
    query_text: Optional[str] = None
    query_media_uri: Optional[str] = None
    query_embedding: Optional[Dict[str, List[float]]] = None
    
    # Search configuration
    vector_types: Optional[List[str]] = None
    target_indexes: Optional[List[str]] = None
    top_k: int = 10
    similarity_threshold: float = 0.0
    
    # Filtering and processing
    metadata_filters: Optional[Dict[str, Any]] = None
    temporal_filters: Optional[Dict[str, Any]] = None
    fusion_method: str = "weighted_average"
    enable_cross_type_fusion: bool = True


class ICoordinatorService(ABC):
    """
    Abstract interface for multi-vector coordination services.
    
    This interface defines the contract for coordination operations,
    allowing different coordinator implementations to be used
    without creating circular dependencies.
    """
    
    @abstractmethod
    def process_multi_vector_content(self,
                                   content_inputs: List[Dict[str, Any]],
                                   vector_types: Optional[List[str]] = None) -> ProcessingResult:
        """
        Process content to generate embeddings across multiple vector types.

        All jobs are submitted in parallel and polled for completion since
        Bedrock operations are async.

        Args:
            content_inputs: List of content input configurations
            vector_types: Vector types to generate (defaults to config)

        Returns:
            ProcessingResult with embeddings by vector type
        """
        pass
    
    @abstractmethod
    def search_multi_vector(self, search_request: CoordinatorSearchRequest) -> Dict[str, Any]:
        """
        Perform unified search across multiple vector types and indexes.
        
        Args:
            search_request: Unified search request configuration
            
        Returns:
            Dictionary with search results and metadata
        """
        pass
    
    @abstractmethod
    def get_coordination_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about multi-vector coordination.
        
        Returns:
            Dictionary with performance stats, active workflows, and configuration
        """
        pass
    
    @abstractmethod
    def get_compatible_vector_types(self, query_type: str) -> List[str]:
        """
        Get vector types compatible with a specific query type.
        
        Args:
            query_type: Type of query (text, video, audio, etc.)
            
        Returns:
            List of compatible vector type names
        """
        pass
    
    @abstractmethod
    def register_service_dependency(self, 
                                  service_name: str, 
                                  service_instance: Any) -> None:
        """
        Register a service dependency for coordination.
        
        Args:
            service_name: Name of the service
            service_instance: Service instance to register
        """
        pass


class ICoordinatorFactory(ABC):
    """
    Abstract factory for creating coordinator service instances.
    
    This enables dynamic creation of different coordinator implementations
    based on configuration or runtime requirements.
    """
    
    @abstractmethod
    def create_multi_vector_coordinator(self, 
                                      config: Optional[Dict[str, Any]] = None) -> ICoordinatorService:
        """Create a multi-vector coordinator service."""
        pass
    
    @abstractmethod
    def create_lightweight_coordinator(self, 
                                     config: Optional[Dict[str, Any]] = None) -> ICoordinatorService:
        """Create a lightweight coordinator for simple operations."""
        pass


class IServiceRegistry(ABC):
    """
    Abstract interface for service registry and dependency injection.
    
    This enables services to find and interact with each other
    without creating direct circular dependencies.
    """
    
    @abstractmethod
    def register_service(self, service_name: str, service_instance: Any) -> None:
        """Register a service instance in the registry."""
        pass
    
    @abstractmethod
    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service instance from the registry."""
        pass
    
    @abstractmethod
    def list_services(self) -> List[str]:
        """List all registered service names."""
        pass
    
    @abstractmethod
    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available in the registry."""
        pass