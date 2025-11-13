"""
Videolake Vector Store Provider Abstraction

Provides a unified interface for multiple vector store backends in the Videolake
platform using the Strategy/Provider pattern. This architecture enables seamless
integration of diverse vector store backends (AWS S3Vector, OpenSearch, LanceDB,
Qdrant, etc.) without changing client code, supporting Videolake's multi-backend
vector search capabilities.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class VectorStoreType(str, Enum):
    """Supported vector store types."""
    # Currently implemented
    S3_VECTOR = "s3_vector"
    OPENSEARCH = "opensearch"
    LANCEDB = "lancedb"
    QDRANT = "qdrant"

    # Extensible for future implementations
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    MILVUS = "milvus"
    CHROMA = "chroma"


class VectorStoreState(str, Enum):
    """Vector store states."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    AVAILABLE = "AVAILABLE"
    UPDATING = "UPDATING"
    DELETING = "DELETING"
    DELETED = "DELETED"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class VectorStoreConfig:
    """Configuration for a vector store."""
    store_type: VectorStoreType
    name: str
    dimension: int
    similarity_metric: str = "cosine"  # cosine, euclidean, dot_product
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Provider-specific configurations
    s3vector_config: Optional[Dict[str, Any]] = None
    opensearch_config: Optional[Dict[str, Any]] = None
    lancedb_config: Optional[Dict[str, Any]] = None
    qdrant_config: Optional[Dict[str, Any]] = None
    pinecone_config: Optional[Dict[str, Any]] = None
    weaviate_config: Optional[Dict[str, Any]] = None


@dataclass
class VectorStoreStatus:
    """Status information for a vector store."""
    store_type: VectorStoreType
    name: str
    state: VectorStoreState
    arn: Optional[str] = None
    endpoint: Optional[str] = None
    region: Optional[str] = None
    created_at: Optional[datetime] = None
    vector_count: int = 0
    dimension: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    progress_percentage: int = 0
    estimated_time_remaining: Optional[int] = None


class VectorStoreProvider(ABC):
    """
    Abstract base class for Videolake vector store providers.
    
    All vector store backend implementations in the Videolake platform must
    inherit from this class and implement the required methods. This ensures
    a consistent interface across different vector store backends (AWS S3Vector,
    OpenSearch, LanceDB, Qdrant, etc.).
    """
    
    @property
    @abstractmethod
    def store_type(self) -> VectorStoreType:
        """Return the type of this vector store."""
        pass
    
    @abstractmethod
    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new vector store.
        
        Args:
            config: Configuration for the vector store
            
        Returns:
            VectorStoreStatus with creation result
        """
        pass
    
    @abstractmethod
    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete a vector store.
        
        Args:
            name: Name of the vector store
            force: Whether to force deletion (e.g., delete non-empty stores)
            
        Returns:
            VectorStoreStatus with deletion result
        """
        pass
    
    @abstractmethod
    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get current status of a vector store.
        
        Args:
            name: Name of the vector store
            
        Returns:
            VectorStoreStatus with current state
        """
        pass
    
    @abstractmethod
    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all vector stores of this type.
        
        Returns:
            List of VectorStoreStatus objects
        """
        pass
    
    @abstractmethod
    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in the store.
        
        Args:
            name: Name of the vector store
            vectors: List of vector objects with id, values, and metadata
            
        Returns:
            Result dictionary with upsert statistics
        """
        pass
    
    @abstractmethod
    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar vectors.
        
        Args:
            name: Name of the vector store
            query_vector: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of similar vectors with scores
        """
        pass
    
    @abstractmethod
    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to the vector store backend.
        
        Tests actual connectivity to the backend service and returns
        detailed health information including response time.
        
        Returns:
            Dictionary with:
                - accessible (bool): Whether backend is accessible
                - endpoint (str): Backend endpoint/URL
                - response_time_ms (float): Response time in milliseconds
                - health_status (str): Health status (healthy, degraded, unhealthy)
                - error_message (Optional[str]): Error message if not accessible
        """
        pass
    
    def validate_config(self, config: VectorStoreConfig) -> bool:
        """
        Validate configuration for this provider.
        
        Args:
            config: Configuration to validate
            
        Returns:
            True if valid, raises exception otherwise
        """
        if config.store_type != self.store_type:
            raise ValueError(f"Invalid store type: {config.store_type}, expected {self.store_type}")
        
        if not config.name:
            raise ValueError("Store name is required")
        
        if config.dimension <= 0:
            raise ValueError("Dimension must be positive")
        
        if config.similarity_metric not in ["cosine", "euclidean", "dot_product"]:
            raise ValueError(f"Invalid similarity metric: {config.similarity_metric}")
        
        return True
    
    def poll_until_ready(self, name: str, timeout: int = 300, poll_interval: int = 5) -> VectorStoreStatus:
        """
        Poll store status until it reaches a ready state or timeout.
        
        Args:
            name: Name of the vector store
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds
            
        Returns:
            Final VectorStoreStatus
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_status(name)
            
            # Check if terminal state reached
            if status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE,
                              VectorStoreState.DELETED, VectorStoreState.FAILED,
                              VectorStoreState.NOT_FOUND]:
                return status
            
            # Update estimated time
            elapsed = time.time() - start_time
            status.estimated_time_remaining = max(0, int(timeout - elapsed))
            
            time.sleep(poll_interval)
        
        # Timeout reached
        status = self.get_status(name)
        if status.state not in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]:
            status.error_message = f"Operation timed out after {timeout} seconds"
        
        return status


class VectorStoreProviderFactory:
    """
    Factory for creating Videolake vector store providers.
    
    This factory maintains a registry of available backend providers in the
    Videolake platform and creates instances based on the requested store type,
    enabling dynamic backend selection for multi-backend vector operations.
    """
    
    _providers: Dict[VectorStoreType, type] = {}
    
    @classmethod
    def register_provider(cls, store_type: VectorStoreType, provider_class: type):
        """Register a provider class for a store type."""
        if not issubclass(provider_class, VectorStoreProvider):
            raise TypeError(f"{provider_class} must inherit from VectorStoreProvider")
        cls._providers[store_type] = provider_class
        logger.info(f"Registered vector store provider: {store_type.value}")
    
    @classmethod
    def create_provider(cls, store_type: VectorStoreType) -> VectorStoreProvider:
        """Create a provider instance for the given store type."""
        if store_type not in cls._providers:
            raise ValueError(f"No provider registered for store type: {store_type.value}")
        
        provider_class = cls._providers[store_type]
        return provider_class()
    
    @classmethod
    def get_available_providers(cls) -> List[VectorStoreType]:
        """Get list of available provider types."""
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_available(cls, store_type: VectorStoreType) -> bool:
        """Check if a provider is available."""
        return store_type in cls._providers

