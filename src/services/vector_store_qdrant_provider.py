"""
Videolake Qdrant Backend Provider

Implementation of the Videolake VectorStoreProvider interface for Qdrant.
Qdrant is a cloud-native vector database integrated into the Videolake platform,
offering advanced filtering, HNSW indexing, and support for both local and cloud
deployments as a flexible backend option.
"""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreState
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QdrantProvider(VectorStoreProvider):
    """
    Qdrant backend implementation for Videolake platform.

    Features integrated into Videolake:
    - Cloud-native architecture
    - Local and cloud deployment support
    - Advanced metadata filtering capabilities
    - HNSW indexing for fast similarity search
    - Multiple distance metrics (cosine, euclidean, dot product)
    - Payload-based filtering for complex queries
    """

    def __init__(self):
        """Initialize Qdrant provider."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self.QdrantClient = QdrantClient
            self.Distance = Distance
            self.VectorParams = VectorParams

            # Get configuration
            self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            self.qdrant_api_key = os.getenv("QDRANT_API_KEY")

            # Connect to Qdrant
            if self.qdrant_api_key:
                self.client = self.QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key
                )
            else:
                self.client = self.QdrantClient(url=self.qdrant_url)

            logger.info(f"Qdrant provider initialized with URL: {self.qdrant_url}")

        except ImportError as e:
            logger.error(f"Failed to import qdrant_client: {e}")
            raise ImportError(
                "qdrant-client is required for QdrantProvider. "
                "Install with: pip install qdrant-client"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant provider: {e}")
            raise

    @property
    def store_type(self) -> VectorStoreType:
        """Get the store type."""
        return VectorStoreType.QDRANT

    def _get_distance_metric(self, similarity_metric: str):
        """Convert similarity metric string to Qdrant Distance enum."""
        metric_map = {
            "cosine": self.Distance.COSINE,
            "euclidean": self.Distance.EUCLID,
            "dot_product": self.Distance.DOT
        }
        return metric_map.get(similarity_metric.lower(), self.Distance.COSINE)

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new Qdrant collection for Videolake.

        Args:
            config: Vector store configuration

        Returns:
            VectorStoreStatus with creation result
        """
        try:
            from qdrant_client.models import VectorParams, Distance

            logger.info(f"Creating Qdrant collection: {config.name}")

            # Get distance metric
            distance = self._get_distance_metric(config.similarity_metric)

            # Create collection
            self.client.create_collection(
                collection_name=config.name,
                vectors_config=VectorParams(
                    size=config.dimension,
                    distance=distance
                )
            )

            logger.info(f"Qdrant collection created: {config.name}")

            return VectorStoreStatus(
                store_type=VectorStoreType.QDRANT,
                name=config.name,
                state=VectorStoreState.ACTIVE,
                dimension=config.dimension,
                similarity_metric=config.similarity_metric,
                created_at=datetime.now(timezone.utc),
                metadata={
                    "url": self.qdrant_url,
                    "deployment_type": "cloud" if self.qdrant_api_key else "local"
                }
            )

        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.QDRANT,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete a Qdrant collection.

        Args:
            name: Collection name
            force: Force deletion even if collection has data

        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            logger.info(f"Deleting Qdrant collection: {name}")

            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if name in collection_names:
                self.client.delete_collection(collection_name=name)
                logger.info(f"Qdrant collection deleted: {name}")

                return VectorStoreStatus(
                    store_type=VectorStoreType.QDRANT,
                    name=name,
                    state=VectorStoreState.DELETED
                )
            else:
                return VectorStoreStatus(
                    store_type=VectorStoreType.QDRANT,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Collection {name} not found"
                )

        except Exception as e:
            logger.error(f"Failed to delete Qdrant collection: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.QDRANT,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get status of a Qdrant collection.

        Args:
            name: Collection name

        Returns:
            VectorStoreStatus with current state
        """
        try:
            # Get collection info
            collection_info = self.client.get_collection(collection_name=name)

            return VectorStoreStatus(
                store_type=VectorStoreType.QDRANT,
                name=name,
                state=VectorStoreState.ACTIVE,
                vector_count=collection_info.points_count,
                dimension=collection_info.config.params.vectors.size,
                metadata={
                    "url": self.qdrant_url,
                    "deployment_type": "cloud" if self.qdrant_api_key else "local",
                    "status": collection_info.status
                }
            )

        except Exception as e:
            if "Not found" in str(e) or "doesn't exist" in str(e):
                return VectorStoreStatus(
                    store_type=VectorStoreType.QDRANT,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Collection {name} not found"
                )

            logger.error(f"Failed to get Qdrant collection status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.QDRANT,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all Qdrant collections.

        Returns:
            List of VectorStoreStatus objects
        """
        try:
            collections = self.client.get_collections().collections

            return [
                VectorStoreStatus(
                    store_type=VectorStoreType.QDRANT,
                    name=collection.name,
                    state=VectorStoreState.ACTIVE
                )
                for collection in collections
            ]

        except Exception as e:
            logger.error(f"Failed to list Qdrant collections: {e}")
            return []

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in Qdrant collection.

        Args:
            name: Collection name
            vectors: List of vector objects with 'id', 'values', and 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            from qdrant_client.models import PointStruct

            logger.info(f"Upserting {len(vectors)} vectors to Qdrant collection: {name}")

            # Prepare points for Qdrant
            points = []
            for vector in vectors:
                # Generate UUID for id if not provided or if string
                vector_id = vector.get("id", str(uuid.uuid4()))
                if isinstance(vector_id, str):
                    # Convert string to UUID
                    vector_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, vector_id))

                points.append(
                    PointStruct(
                        id=vector_id,
                        vector=vector.get("values", []),
                        payload=vector.get("metadata", {})
                    )
                )

            # Upsert points
            self.client.upsert(
                collection_name=name,
                points=points
            )

            logger.info(f"Successfully upserted {len(vectors)} vectors to {name}")

            return {
                "success": True,
                "upserted_count": len(vectors),
                "collection_name": name
            }

        except Exception as e:
            logger.error(f"Failed to upsert vectors to Qdrant: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Qdrant collection for similar vectors.

        Args:
            name: Collection name
            query_vector: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of similar vectors with scores
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            logger.info(f"Querying Qdrant collection {name} for top {top_k} results")

            # Prepare filter if provided
            query_filter = None
            if filter_metadata:
                conditions = [
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                    for key, value in filter_metadata.items()
                ]
                query_filter = Filter(must=conditions)

            # Execute search
            search_results = self.client.search(
                collection_name=name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter
            )

            # Format results
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "id": str(result.id),
                    "score": float(result.score),
                    "metadata": result.payload if result.payload else {},
                    "vector": result.vector if hasattr(result, 'vector') else []
                })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query Qdrant collection: {e}")
            return []
    
    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to Qdrant service backend.
        
        Tests the Videolake platform's connection to Qdrant backend:
        - Qdrant endpoint accessibility
        - Collection listing capability
        - Service health check
        - Response time measurement
        
        Returns:
            Connectivity validation result
        """
        import time
        
        start_time = time.time()
        
        try:
            # Test Qdrant connectivity by listing collections
            collections_response = self.client.get_collections()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            collections = collections_response.collections
            collection_count = len(collections)
            
            # Determine health status based on response
            health_status = "healthy"
            
            details = {
                "collection_count": collection_count,
                "url": self.qdrant_url,
                "deployment_type": "cloud" if self.qdrant_api_key else "local",
                "service": "Qdrant"
            }
            
            # Try to get additional health info if available
            try:
                # Some Qdrant deployments expose health endpoint
                health_info = self.client.get_collections()
                details['collections_accessible'] = True
            except Exception as e:
                logger.warning(f"Could not fetch additional health info: {e}")
            
            return {
                "accessible": True,
                "endpoint": self.qdrant_url,
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": None,
                "details": details
            }
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"Qdrant connectivity validation failed: {e}")
            
            # Determine if it's a connection error or other issue
            if "refused" in error_msg.lower() or "timeout" in error_msg.lower():
                health_status = "unhealthy"
            else:
                health_status = "degraded"
            
            return {
                "accessible": False,
                "endpoint": self.qdrant_url,
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": error_msg,
                "details": {
                    "url": self.qdrant_url,
                    "deployment_type": "cloud" if self.qdrant_api_key else "local",
                    "service": "Qdrant"
                }
            }
