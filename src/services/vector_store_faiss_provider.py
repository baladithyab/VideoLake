"""
Videolake FAISS Backend Provider (Embedded)

Implementation of the Videolake VectorStoreProvider interface for FAISS.
FAISS is an embedded vector search library integrated into the Videolake platform,
offering ultra-fast in-process similarity search with multiple index types optimized
for different scales and accuracy requirements.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreState,
    VectorStoreCapabilities
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FAISSProvider(VectorStoreProvider):
    """
    FAISS embedded backend implementation for Videolake platform.

    Features integrated into Videolake:
    - Ultra-fast in-process vector search (<1ms latency)
    - Multiple index types (Flat, IVF, HNSW, PQ)
    - Memory-efficient implementations
    - GPU acceleration support
    - No network overhead
    - Zero database cost (embedded library)
    - Optimal for read-heavy workloads

    Note: FAISS is an embedded library, so collections are managed in-memory
    or loaded from disk. Persistence is handled via serialization.
    """

    def __init__(self):
        """Initialize FAISS provider."""
        try:
            import faiss
            import numpy as np

            self.faiss = faiss
            self.np = np

            # In-memory collection storage
            self._collections: Dict[str, Dict[str, Any]] = {}

            # Storage directory for persisted indexes
            self.storage_dir = os.getenv("FAISS_STORAGE_DIR", "./data/faiss_indexes")
            Path(self.storage_dir).mkdir(parents=True, exist_ok=True)

            # Check for GPU support
            self.gpu_available = self.faiss.get_num_gpus() > 0

            logger.info(f"FAISS provider initialized (GPU available: {self.gpu_available})")

        except ImportError as e:
            logger.error(f"Failed to import faiss: {e}")
            raise ImportError(
                "faiss-cpu or faiss-gpu is required for FAISSProvider. "
                "Install with: pip install faiss-cpu (or faiss-gpu for GPU support)"
            )
        except Exception as e:
            logger.error(f"Failed to initialize FAISS provider: {e}")
            raise

    @property
    def store_type(self) -> VectorStoreType:
        """Get the store type."""
        return VectorStoreType.FAISS

    def _get_metric_type(self, similarity_metric: str) -> int:
        """Convert similarity metric to FAISS metric type."""
        metric_map = {
            "cosine": self.faiss.METRIC_INNER_PRODUCT,  # Requires normalized vectors
            "euclidean": self.faiss.METRIC_L2,
            "dot_product": self.faiss.METRIC_INNER_PRODUCT
        }
        return metric_map.get(similarity_metric.lower(), self.faiss.METRIC_L2)

    def _create_index(self, dimension: int, similarity_metric: str, index_type: str = "Flat") -> Any:
        """
        Create a FAISS index.

        Args:
            dimension: Vector dimension
            similarity_metric: Similarity metric (cosine, euclidean, dot_product)
            index_type: Index type (Flat, IVF, HNSW)

        Returns:
            FAISS index object
        """
        metric = self._get_metric_type(similarity_metric)

        if index_type == "Flat":
            # Exact search (brute-force)
            if metric == self.faiss.METRIC_INNER_PRODUCT:
                index = self.faiss.IndexFlatIP(dimension)
            else:
                index = self.faiss.IndexFlatL2(dimension)

        elif index_type == "IVF":
            # Inverted file index (faster but approximate)
            nlist = 100  # Number of clusters
            quantizer = self.faiss.IndexFlatL2(dimension)
            if metric == self.faiss.METRIC_INNER_PRODUCT:
                index = self.faiss.IndexIVFFlat(quantizer, dimension, nlist, self.faiss.METRIC_INNER_PRODUCT)
            else:
                index = self.faiss.IndexIVFFlat(quantizer, dimension, nlist)

        elif index_type == "HNSW":
            # Hierarchical Navigable Small World (fast approximate search)
            M = 32  # Number of connections per layer
            if metric == self.faiss.METRIC_INNER_PRODUCT:
                index = self.faiss.IndexHNSWFlat(dimension, M, self.faiss.METRIC_INNER_PRODUCT)
            else:
                index = self.faiss.IndexHNSWFlat(dimension, M)

        else:
            # Default to Flat
            logger.warning(f"Unknown index type {index_type}, using Flat")
            index = self.faiss.IndexFlatL2(dimension)

        return index

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new FAISS index for Videolake.

        Args:
            config: Vector store configuration

        Returns:
            VectorStoreStatus with creation result
        """
        try:
            logger.info(f"Creating FAISS index: {config.name}")

            if config.name in self._collections:
                logger.warning(f"Index {config.name} already exists")
                return self.get_status(config.name)

            # Get index type from config (default to Flat)
            faiss_config = config.metadata.get("faiss_config", {})
            index_type = faiss_config.get("index_type", "Flat")

            # Create FAISS index
            index = self._create_index(
                dimension=config.dimension,
                similarity_metric=config.similarity_metric,
                index_type=index_type
            )

            # Store collection metadata
            self._collections[config.name] = {
                "index": index,
                "dimension": config.dimension,
                "similarity_metric": config.similarity_metric,
                "index_type": index_type,
                "metadata_store": {},  # Map vector IDs to metadata
                "id_map": {},  # Map internal index IDs to external IDs
                "created_at": datetime.now(timezone.utc),
                "vector_count": 0
            }

            logger.info(f"FAISS index created: {config.name} (type: {index_type})")

            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=config.name,
                state=VectorStoreState.ACTIVE,
                dimension=config.dimension,
                created_at=datetime.now(timezone.utc),
                metadata={
                    "index_type": index_type,
                    "gpu_enabled": False,  # CPU by default
                    "storage": "in-memory"
                }
            )

        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete a FAISS index.

        Args:
            name: Index name
            force: Force deletion even if index has data

        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            logger.info(f"Deleting FAISS index: {name}")

            if name not in self._collections:
                return VectorStoreStatus(
                    store_type=VectorStoreType.FAISS,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Index {name} not found"
                )

            # Remove from memory
            del self._collections[name]

            # Remove persisted file if it exists
            index_path = os.path.join(self.storage_dir, f"{name}.index")
            metadata_path = os.path.join(self.storage_dir, f"{name}.metadata.json")

            if os.path.exists(index_path):
                os.remove(index_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            logger.info(f"FAISS index deleted: {name}")

            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=name,
                state=VectorStoreState.DELETED
            )

        except Exception as e:
            logger.error(f"Failed to delete FAISS index: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get status of a FAISS index.

        Args:
            name: Index name

        Returns:
            VectorStoreStatus with current state
        """
        try:
            if name not in self._collections:
                return VectorStoreStatus(
                    store_type=VectorStoreType.FAISS,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Index {name} not found"
                )

            collection = self._collections[name]

            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=name,
                state=VectorStoreState.ACTIVE,
                vector_count=collection["vector_count"],
                dimension=collection["dimension"],
                created_at=collection["created_at"],
                metadata={
                    "index_type": collection["index_type"],
                    "storage": "in-memory"
                }
            )

        except Exception as e:
            logger.error(f"Failed to get FAISS index status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.FAISS,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all FAISS indexes.

        Returns:
            List of VectorStoreStatus objects
        """
        try:
            return [
                VectorStoreStatus(
                    store_type=VectorStoreType.FAISS,
                    name=name,
                    state=VectorStoreState.ACTIVE,
                    vector_count=collection["vector_count"]
                )
                for name, collection in self._collections.items()
            ]

        except Exception as e:
            logger.error(f"Failed to list FAISS indexes: {e}")
            return []

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert vectors into FAISS index.

        Note: FAISS doesn't support true updates. This method adds new vectors.
        For updates, delete and recreate the index.

        Args:
            name: Index name
            vectors: List of vector objects with 'id', 'values', and 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            logger.info(f"Adding {len(vectors)} vectors to FAISS index: {name}")

            if name not in self._collections:
                return {
                    "success": False,
                    "error": f"Index {name} not found"
                }

            collection = self._collections[name]
            index = collection["index"]

            # Prepare vectors for FAISS
            vector_data = []
            for vector in vectors:
                vector_data.append(vector.get("values", []))

            # Convert to numpy array
            vector_array = self.np.array(vector_data, dtype='float32')

            # Normalize vectors if using cosine similarity
            if collection["similarity_metric"] == "cosine":
                self.faiss.normalize_L2(vector_array)

            # Train index if needed (IVF indexes require training)
            if hasattr(index, 'is_trained') and not index.is_trained:
                logger.info(f"Training index {name}")
                index.train(vector_array)

            # Add vectors to index
            start_idx = index.ntotal
            index.add(vector_array)

            # Store metadata and ID mappings
            for i, vector in enumerate(vectors):
                internal_id = start_idx + i
                external_id = str(vector.get("id", internal_id))
                collection["id_map"][internal_id] = external_id
                collection["metadata_store"][external_id] = vector.get("metadata", {})

            collection["vector_count"] = index.ntotal

            logger.info(f"Successfully added {len(vectors)} vectors to {name}")

            return {
                "success": True,
                "upserted_count": len(vectors),
                "index_name": name,
                "total_vectors": index.ntotal
            }

        except Exception as e:
            logger.error(f"Failed to upsert vectors to FAISS: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query FAISS index for similar vectors.

        Args:
            name: Index name
            query_vector: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters (applied post-search)

        Returns:
            List of similar vectors with scores
        """
        try:
            logger.info(f"Querying FAISS index {name} for top {top_k} results")

            if name not in self._collections:
                logger.error(f"Index {name} not found")
                return []

            collection = self._collections[name]
            index = collection["index"]

            if index.ntotal == 0:
                logger.warning(f"Index {name} is empty")
                return []

            # Prepare query vector
            query_array = self.np.array([query_vector], dtype='float32')

            # Normalize if using cosine similarity
            if collection["similarity_metric"] == "cosine":
                self.faiss.normalize_L2(query_array)

            # Set search parameters for IVF indexes
            if hasattr(index, 'nprobe'):
                index.nprobe = 10  # Number of clusters to visit

            # Execute search
            # Note: For L2 distance, smaller is better. For IP, larger is better.
            distances, indices = index.search(query_array, top_k)

            # Format results
            formatted_results = []
            for i in range(len(indices[0])):
                internal_id = int(indices[0][i])

                # Skip invalid indices
                if internal_id == -1:
                    continue

                external_id = collection["id_map"].get(internal_id, str(internal_id))
                metadata = collection["metadata_store"].get(external_id, {})

                # Apply metadata filtering if provided
                if filter_metadata:
                    # Simple exact match filtering
                    match = all(
                        metadata.get(key) == value
                        for key, value in filter_metadata.items()
                    )
                    if not match:
                        continue

                # Convert distance to score (higher is better)
                distance = float(distances[0][i])
                if collection["similarity_metric"] == "cosine":
                    score = distance  # Inner product (already similarity)
                else:
                    # L2 distance: convert to similarity
                    score = 1.0 / (1.0 + distance)

                formatted_results.append({
                    "id": external_id,
                    "score": score,
                    "metadata": metadata,
                    "vector": []  # Don't return vectors by default
                })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query FAISS index: {e}")
            return []

    def save_index(self, name: str) -> bool:
        """
        Persist FAISS index to disk.

        Args:
            name: Index name

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._collections:
                logger.error(f"Index {name} not found")
                return False

            collection = self._collections[name]
            index = collection["index"]

            # Save FAISS index
            index_path = os.path.join(self.storage_dir, f"{name}.index")
            self.faiss.write_index(index, index_path)

            # Save metadata as JSON
            metadata_path = os.path.join(self.storage_dir, f"{name}.metadata.json")
            metadata = {
                "dimension": collection["dimension"],
                "similarity_metric": collection["similarity_metric"],
                "index_type": collection["index_type"],
                "metadata_store": collection["metadata_store"],
                "id_map": {str(k): v for k, v in collection["id_map"].items()},  # Convert int keys to str for JSON
                "created_at": collection["created_at"].isoformat(),
                "vector_count": collection["vector_count"]
            }

            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)

            logger.info(f"FAISS index {name} saved to {index_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False

    def load_index(self, name: str) -> bool:
        """
        Load FAISS index from disk.

        Args:
            name: Index name

        Returns:
            True if successful, False otherwise
        """
        try:
            index_path = os.path.join(self.storage_dir, f"{name}.index")
            metadata_path = os.path.join(self.storage_dir, f"{name}.metadata.json")

            if not os.path.exists(index_path) or not os.path.exists(metadata_path):
                logger.error(f"Index files not found for {name}")
                return False

            # Load FAISS index
            index = self.faiss.read_index(index_path)

            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            # Convert id_map keys back to int
            id_map = {int(k): v for k, v in metadata["id_map"].items()}

            # Store in collections
            self._collections[name] = {
                "index": index,
                "dimension": metadata["dimension"],
                "similarity_metric": metadata["similarity_metric"],
                "index_type": metadata["index_type"],
                "metadata_store": metadata["metadata_store"],
                "id_map": id_map,
                "created_at": datetime.fromisoformat(metadata["created_at"]),
                "vector_count": metadata["vector_count"]
            }

            logger.info(f"FAISS index {name} loaded from {index_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            return False

    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate FAISS provider availability.

        Since FAISS is an embedded library, this checks if the library
        is properly initialized and ready to use.

        Returns:
            Connectivity validation result
        """
        start_time = time.time()

        try:
            # Test FAISS by creating a small temporary index
            test_index = self.faiss.IndexFlatL2(128)
            test_vector = self.np.random.rand(1, 128).astype('float32')
            test_index.add(test_vector)

            response_time_ms = (time.time() - start_time) * 1000

            return {
                "accessible": True,
                "endpoint": "embedded (in-process)",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": "healthy",
                "error_message": None,
                "details": {
                    "gpu_available": self.gpu_available,
                    "num_gpus": self.faiss.get_num_gpus() if self.gpu_available else 0,
                    "storage_dir": self.storage_dir,
                    "loaded_collections": len(self._collections),
                    "service": "FAISS (Embedded)"
                }
            }

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            logger.error(f"FAISS validation failed: {e}")

            return {
                "accessible": False,
                "endpoint": "embedded (in-process)",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": "unhealthy",
                "error_message": error_msg,
                "details": {
                    "storage_dir": self.storage_dir,
                    "service": "FAISS (Embedded)"
                }
            }

    def get_capabilities(self) -> VectorStoreCapabilities:
        """
        Return capabilities of FAISS vector store provider.

        Returns:
            VectorStoreCapabilities defining supported features and limits
        """
        return VectorStoreCapabilities(
            max_dimension=4096,  # Practical limit for FAISS in-memory
            max_vectors=10_000_000,  # ~10M vectors practical for single machine
            supports_metadata_filtering=True,  # Post-search filtering
            supports_hybrid_search=False,  # No native hybrid search
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=0.0,  # Embedded, no database cost
            typical_query_latency_ms=1.0,  # <1ms for in-process search
            supports_sparse_vectors=False,  # FAISS is for dense vectors
            supports_multi_vector=False,  # Single vector per entry
            max_batch_size=100000  # Large batches supported for embedded
        )
