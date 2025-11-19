from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreType(str, Enum):
    S3_VECTOR = "s3vector"
    LANCEDB = "lancedb"
    QDRANT = "qdrant"
    OPENSEARCH = "opensearch"

class VectorStoreProvider(ABC):
    """Abstract base class for vector store providers."""

    @abstractmethod
    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        """Index vectors into the backend."""
        pass

    @abstractmethod
    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        """Search for similar vectors."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Check if backend is accessible."""
        pass

    @abstractmethod
    def get_endpoint_info(self) -> Dict[str, str]:
        """Get endpoint information."""
        pass

class VectorStoreManager:
    """
    Manages dynamic switching between vector store backends.
    """

    def __init__(self):
        self.active_backend: Optional[VectorStoreType] = None
        self.providers: Dict[VectorStoreType, VectorStoreProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize available providers based on configuration."""
        # We will lazily load these or load them based on env vars
        # For now, we'll just set up the structure.
        # In a real scenario, we might read from a config file or env vars
        # to decide which providers to instantiate.
        pass

    def register_provider(self, backend_type: VectorStoreType, provider: VectorStoreProvider):
        """Register a provider instance."""
        self.providers[backend_type] = provider
        logger.info(f"Registered provider: {backend_type}")

    def set_active_backend(self, backend_type: VectorStoreType):
        """Switch the active backend."""
        if backend_type not in self.providers:
            raise ValueError(f"Backend {backend_type} not registered.")
        self.active_backend = backend_type
        logger.info(f"Switched active backend to: {backend_type}")

    def get_active_provider(self) -> VectorStoreProvider:
        """Get the currently active provider."""
        if not self.active_backend:
            raise RuntimeError("No active backend selected.")
        return self.providers[self.active_backend]

    def get_available_backends(self) -> List[str]:
        """Return list of registered backends."""
        return [b.value for b in self.providers.keys()]

    # Proxy methods to the active provider
    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        return self.get_active_provider().index_vectors(vectors, metadata, collection)

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        return self.get_active_provider().search_vectors(query_vector, top_k, collection)

    def health_check(self) -> bool:
        return self.get_active_provider().health_check()

# Concrete Implementations (Adapters)
# These adapt the existing scripts/backend_adapters.py logic into the new structure if needed,
# or we can import them directly if they are compatible.
# Given the task, we should implement concrete classes here or import them.
# Since scripts/backend_adapters.py already has robust implementations, we can reuse them
# by wrapping them or importing them if the path allows.
# However, the task says "Implement concrete classes...".
# Let's import the adapters from scripts.backend_adapters to avoid code duplication
# and wrap them in the VectorStoreProvider interface if necessary.
# The interfaces in backend_adapters.py (BackendAdapter) are almost identical to VectorStoreProvider.

import sys
from pathlib import Path

# Add project root to path to allow importing from scripts
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from scripts.backend_adapters import (
        S3VectorAdapter,
        QdrantAdapter,
        RestAPIAdapter,
        LanceDBEmbeddedAdapter,
        OpenSearchAdapter,
        get_backend_adapter
    )
except ImportError:
    logger.warning("Could not import backend adapters from scripts.backend_adapters. Ensure the path is correct.")

class S3VectorProvider(VectorStoreProvider):
    def __init__(self, bucket_name: str = "videolake-vectors", index_name: str = "embeddings"):
        self.adapter = S3VectorAdapter(bucket_name, index_name)

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        return self.adapter.index_vectors(vectors, metadata, collection)

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        return self.adapter.search_vectors(query_vector, top_k, collection)

    def health_check(self) -> bool:
        return self.adapter.health_check()

    def get_endpoint_info(self) -> Dict[str, str]:
        return self.adapter.get_endpoint_info()

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Map upsert_vectors to index_vectors for S3Vector
        # Extract vectors and metadata from the list of dicts
        vecs = [v['vector'] for v in vectors]
        metas = [v['metadata'] for v in vectors]
        return self.index_vectors(vecs, metas, collection=name)

    def query(self, name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.search_vectors(query_vector, top_k, collection=name)


class QdrantProvider(VectorStoreProvider):
    def __init__(self, endpoint: str):
        self.adapter = QdrantAdapter(endpoint)

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        return self.adapter.index_vectors(vectors, metadata, collection)

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        return self.adapter.search_vectors(query_vector, top_k, collection)

    def health_check(self) -> bool:
        return self.adapter.health_check()

    def get_endpoint_info(self) -> Dict[str, str]:
        return self.adapter.get_endpoint_info()

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        vecs = [v['vector'] for v in vectors]
        metas = [v['metadata'] for v in vectors]
        return self.index_vectors(vecs, metas, collection=name)

    def query(self, name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.search_vectors(query_vector, top_k, collection=name)


class LanceDBProvider(VectorStoreProvider):
    def __init__(self, uri: str, mode: str = "embedded"):
        if mode == "embedded":
            self.adapter = LanceDBEmbeddedAdapter(uri)
        else:
            # Assuming REST mode for LanceDB
            self.adapter = RestAPIAdapter(uri, "lancedb")

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        return self.adapter.index_vectors(vectors, metadata, collection)

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        return self.adapter.search_vectors(query_vector, top_k, collection)

    def health_check(self) -> bool:
        return self.adapter.health_check()

    def get_endpoint_info(self) -> Dict[str, str]:
        return self.adapter.get_endpoint_info()

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        vecs = [v['vector'] for v in vectors]
        metas = [v['metadata'] for v in vectors]
        return self.index_vectors(vecs, metas, collection=name)

    def query(self, name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.search_vectors(query_vector, top_k, collection=name)


class OpenSearchProvider(VectorStoreProvider):
    def __init__(self, endpoint: str, username: Optional[str] = None, password: Optional[str] = None):
        self.adapter = OpenSearchAdapter(endpoint, username=username, password=password)

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        return self.adapter.index_vectors(vectors, metadata, collection)

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        return self.adapter.search_vectors(query_vector, top_k, collection)

    def health_check(self) -> bool:
        return self.adapter.health_check()

    def get_endpoint_info(self) -> Dict[str, str]:
        return self.adapter.get_endpoint_info()

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        vecs = [v['vector'] for v in vectors]
        metas = [v['metadata'] for v in vectors]
        return self.index_vectors(vecs, metas, collection=name)

    def query(self, name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return self.search_vectors(query_vector, top_k, collection=name)