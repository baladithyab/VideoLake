"""
Videolake Unified Vector Store Manager

Provides a unified interface for managing multiple vector store backends in the
Videolake platform using the provider pattern. This is the main entry point for
all vector store operations, supporting AWS S3Vector, OpenSearch, LanceDB, and
Qdrant backends seamlessly.
"""

from typing import Dict, Any, Optional, List

from src.services.vector_store_provider import (
    VectorStoreType,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreState,
    VectorStoreProviderFactory
)
from src.utils.logging_config import get_logger

# Import providers to register them
from src.services.vector_store_s3vector_provider import S3VectorProvider
from src.services.vector_store_opensearch_provider import OpenSearchProvider
from src.services.vector_store_lancedb_provider import LanceDBProvider
from src.services.vector_store_qdrant_provider import QdrantProvider
from src.services.vector_store_milvus_provider import MilvusProvider
from src.services.vector_store_faiss_provider import FAISSProvider

# Register all providers
VectorStoreProviderFactory.register_provider(VectorStoreType.S3_VECTOR, S3VectorProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.OPENSEARCH, OpenSearchProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.LANCEDB, LanceDBProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.QDRANT, QdrantProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.MILVUS, MilvusProvider)
VectorStoreProviderFactory.register_provider(VectorStoreType.FAISS, FAISSProvider)

logger = get_logger(__name__)


class VectorStoreManager:
    """
    Unified manager for all Videolake vector store operations.
    
    This class provides a single interface for working with multiple
    vector store backends in the Videolake platform. It uses the provider
    pattern to delegate operations to the appropriate backend implementation
    (AWS S3Vector, OpenSearch, LanceDB, or Qdrant).
    
    Example usage:
        manager = VectorStoreManager()
        
        # Create an AWS S3 Vector store
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name="my-vector-bucket",
            dimension=1536
        )
        status = manager.create_store(config)
        
        # Create an OpenSearch store
        config = VectorStoreConfig(
            store_type=VectorStoreType.OPENSEARCH,
            name="my-opensearch-domain",
            dimension=1536,
            opensearch_config={
                "instance_type": "t3.small.search",
                "instance_count": 1
            }
        )
        status = manager.create_store(config)
        
        # List all stores of a type
        stores = manager.list_stores(VectorStoreType.S3_VECTOR)
        
        # Get status of a specific store
        status = manager.get_store_status(VectorStoreType.S3_VECTOR, "my-vector-bucket")
        
        # Delete a store
        status = manager.delete_store(VectorStoreType.S3_VECTOR, "my-vector-bucket")
    """
    
    def __init__(self):
        """Initialize the vector store manager."""
        self.factory = VectorStoreProviderFactory
        logger.info(f"Vector store manager initialized with providers: {self.get_available_store_types()}")
    
    def get_available_store_types(self) -> List[str]:
        """
        Get list of available vector store types.
        
        Returns:
            List of store type names
        """
        return [st.value for st in self.factory.get_available_providers()]
    
    def is_store_type_available(self, store_type: VectorStoreType) -> bool:
        """
        Check if a store type is available.
        
        Args:
            store_type: Type to check
            
        Returns:
            True if available
        """
        return self.factory.is_provider_available(store_type)
    
    def create_store(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new vector store.
        
        Args:
            config: Configuration for the store
            
        Returns:
            VectorStoreStatus with creation result
        """
        logger.info(f"Creating {config.store_type.value} store: {config.name}")
        
        try:
            provider = self.factory.create_provider(config.store_type)
            status = provider.create(config)
            
            logger.info(f"Store creation result: {status.state.value}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to create store: {e}")
            return VectorStoreStatus(
                store_type=config.store_type,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def delete_store(self, store_type: VectorStoreType, name: str, 
                    force: bool = False) -> VectorStoreStatus:
        """
        Delete a vector store.
        
        Args:
            store_type: Type of store
            name: Name of the store
            force: Whether to force deletion
            
        Returns:
            VectorStoreStatus with deletion result
        """
        logger.info(f"Deleting {store_type.value} store: {name}")
        
        try:
            provider = self.factory.create_provider(store_type)
            status = provider.delete(name, force=force)
            
            logger.info(f"Store deletion result: {status.state.value}")
            return status
            
        except Exception as e:
            logger.error(f"Failed to delete store: {e}")
            return VectorStoreStatus(
                store_type=store_type,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def get_store_status(self, store_type: VectorStoreType, name: str) -> VectorStoreStatus:
        """
        Get current status of a vector store.
        
        Args:
            store_type: Type of store
            name: Name of the store
            
        Returns:
            VectorStoreStatus with current state
        """
        try:
            provider = self.factory.create_provider(store_type)
            return provider.get_status(name)
            
        except Exception as e:
            logger.error(f"Failed to get store status: {e}")
            return VectorStoreStatus(
                store_type=store_type,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def list_stores(self, store_type: VectorStoreType) -> List[VectorStoreStatus]:
        """
        List all stores of a given type.
        
        Args:
            store_type: Type of stores to list
            
        Returns:
            List of VectorStoreStatus objects
        """
        try:
            provider = self.factory.create_provider(store_type)
            return provider.list_stores()
            
        except Exception as e:
            logger.error(f"Failed to list stores: {e}")
            return []
    
    def list_all_stores(self) -> Dict[str, List[VectorStoreStatus]]:
        """
        List all stores across all available types.
        
        Returns:
            Dictionary mapping store type to list of stores
        """
        all_stores = {}
        
        for store_type in self.factory.get_available_providers():
            try:
                stores = self.list_stores(store_type)
                all_stores[store_type.value] = stores
            except Exception as e:
                logger.error(f"Failed to list {store_type.value} stores: {e}")
                all_stores[store_type.value] = []
        
        return all_stores
    
    def poll_until_ready(self, store_type: VectorStoreType, name: str,
                        timeout: int = 300, poll_interval: int = 5) -> VectorStoreStatus:
        """
        Poll store status until it reaches a ready state or timeout.
        
        Args:
            store_type: Type of store
            name: Name of the store
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds
            
        Returns:
            Final VectorStoreStatus
        """
        try:
            provider = self.factory.create_provider(store_type)
            return provider.poll_until_ready(name, timeout, poll_interval)
            
        except Exception as e:
            logger.error(f"Failed to poll store status: {e}")
            return VectorStoreStatus(
                store_type=store_type,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def upsert_vectors(self, store_type: VectorStoreType, name: str,
                      vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in a store.
        
        Args:
            store_type: Type of store
            name: Name of the store
            vectors: List of vector objects
            
        Returns:
            Result dictionary with upsert statistics
        """
        try:
            provider = self.factory.create_provider(store_type)
            return provider.upsert_vectors(name, vectors)
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query(self, store_type: VectorStoreType, name: str,
             query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query a store for similar vectors.
        
        Args:
            store_type: Type of store
            name: Name of the store
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional filters
            
        Returns:
            List of similar vectors with scores
        """
        try:
            provider = self.factory.create_provider(store_type)
            return provider.query(name, query_vector, top_k, filter_metadata)
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

