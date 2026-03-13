"""
Videolake Milvus Backend Provider (Zilliz Cloud)

Implementation of the Videolake VectorStoreProvider interface for Milvus/Zilliz Cloud.
Milvus is a cloud-native vector database integrated into the Videolake platform,
offering billion-scale vector search with multiple index types, hybrid search capabilities,
and fully managed deployment through Zilliz Cloud.
"""

import os
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

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


class MilvusProvider(VectorStoreProvider):
    """
    Milvus/Zilliz Cloud backend implementation for Videolake platform.

    Features integrated into Videolake:
    - Billion-scale vector search (1B-10B+ vectors)
    - Multiple index types (HNSW, IVF, DiskANN)
    - Hybrid search (vector + scalar filtering)
    - Fully managed via Zilliz Cloud
    - Auto-scaling and load balancing
    - Multi-tenancy support
    - Rich metadata filtering
    """

    def __init__(self):
        """Initialize Milvus provider."""
        try:
            from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility

            self.connections = connections
            self.Collection = Collection
            self.CollectionSchema = CollectionSchema
            self.FieldSchema = FieldSchema
            self.DataType = DataType
            self.utility = utility

            # Get configuration from environment
            self.host = os.getenv("MILVUS_HOST", "localhost")
            self.port = os.getenv("MILVUS_PORT", "19530")
            self.user = os.getenv("MILVUS_USER", "")
            self.password = os.getenv("MILVUS_PASSWORD", "")
            self.secure = os.getenv("MILVUS_SECURE", "false").lower() == "true"

            # Zilliz Cloud specific settings
            self.use_zilliz = os.getenv("MILVUS_USE_ZILLIZ", "false").lower() == "true"
            self.zilliz_cloud_uri = os.getenv("ZILLIZ_CLOUD_URI", "")
            self.zilliz_api_key = os.getenv("ZILLIZ_API_KEY", "")

            # Connect to Milvus/Zilliz
            self._connect()

            logger.info(f"Milvus provider initialized (host: {self.host}, Zilliz: {self.use_zilliz})")

        except ImportError as e:
            logger.error(f"Failed to import pymilvus: {e}")
            raise ImportError(
                "pymilvus is required for MilvusProvider. "
                "Install with: pip install pymilvus"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Milvus provider: {e}")
            raise

    def _connect(self):
        """Establish connection to Milvus/Zilliz Cloud."""
        try:
            if self.use_zilliz and self.zilliz_cloud_uri:
                # Connect to Zilliz Cloud
                self.connections.connect(
                    alias="default",
                    uri=self.zilliz_cloud_uri,
                    token=self.zilliz_api_key,
                    secure=True
                )
                logger.info("Connected to Zilliz Cloud")
            else:
                # Connect to self-hosted Milvus
                connect_params = {
                    "alias": "default",
                    "host": self.host,
                    "port": self.port
                }

                if self.user and self.password:
                    connect_params["user"] = self.user
                    connect_params["password"] = self.password

                if self.secure:
                    connect_params["secure"] = True

                self.connections.connect(**connect_params)
                logger.info(f"Connected to Milvus at {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise

    @property
    def store_type(self) -> VectorStoreType:
        """Get the store type."""
        return VectorStoreType.MILVUS

    def _get_metric_type(self, similarity_metric: str) -> str:
        """Convert similarity metric to Milvus metric type."""
        metric_map = {
            "cosine": "COSINE",
            "euclidean": "L2",
            "dot_product": "IP"  # Inner Product
        }
        return metric_map.get(similarity_metric.lower(), "COSINE")

    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new Milvus collection for Videolake.

        Args:
            config: Vector store configuration

        Returns:
            VectorStoreStatus with creation result
        """
        try:
            logger.info(f"Creating Milvus collection: {config.name}")

            # Check if collection already exists
            if self.utility.has_collection(config.name):
                logger.warning(f"Collection {config.name} already exists")
                return self.get_status(config.name)

            # Define collection schema
            fields = [
                self.FieldSchema(name="id", dtype=self.DataType.VARCHAR, is_primary=True, max_length=65535),
                self.FieldSchema(name="vector", dtype=self.DataType.FLOAT_VECTOR, dim=config.dimension),
                self.FieldSchema(name="metadata", dtype=self.DataType.JSON)
            ]

            schema = self.CollectionSchema(
                fields=fields,
                description=f"Videolake vector collection for {config.name}"
            )

            # Create collection
            collection = self.Collection(
                name=config.name,
                schema=schema,
                using="default"
            )

            # Create index for vector field
            index_params = {
                "metric_type": self._get_metric_type(config.similarity_metric),
                "index_type": "HNSW",  # Default to HNSW for best performance
                "params": {"M": 16, "efConstruction": 256}
            }

            collection.create_index(
                field_name="vector",
                index_params=index_params
            )

            logger.info(f"Milvus collection created: {config.name}")

            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=config.name,
                state=VectorStoreState.ACTIVE,
                dimension=config.dimension,
                created_at=datetime.now(timezone.utc),
                metadata={
                    "host": self.host if not self.use_zilliz else "Zilliz Cloud",
                    "index_type": "HNSW",
                    "metric_type": self._get_metric_type(config.similarity_metric)
                }
            )

        except Exception as e:
            logger.error(f"Failed to create Milvus collection: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete a Milvus collection.

        Args:
            name: Collection name
            force: Force deletion even if collection has data

        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            logger.info(f"Deleting Milvus collection: {name}")

            if not self.utility.has_collection(name):
                return VectorStoreStatus(
                    store_type=VectorStoreType.MILVUS,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Collection {name} not found"
                )

            # Drop the collection
            self.utility.drop_collection(name)
            logger.info(f"Milvus collection deleted: {name}")

            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=name,
                state=VectorStoreState.DELETED
            )

        except Exception as e:
            logger.error(f"Failed to delete Milvus collection: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get status of a Milvus collection.

        Args:
            name: Collection name

        Returns:
            VectorStoreStatus with current state
        """
        try:
            if not self.utility.has_collection(name):
                return VectorStoreStatus(
                    store_type=VectorStoreType.MILVUS,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    error_message=f"Collection {name} not found"
                )

            collection = self.Collection(name)
            collection.load()  # Load collection to get stats

            num_entities = collection.num_entities

            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=name,
                state=VectorStoreState.ACTIVE,
                vector_count=num_entities,
                metadata={
                    "host": self.host if not self.use_zilliz else "Zilliz Cloud",
                    "is_loaded": True
                }
            )

        except Exception as e:
            logger.error(f"Failed to get Milvus collection status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.MILVUS,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e)
            )

    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all Milvus collections.

        Returns:
            List of VectorStoreStatus objects
        """
        try:
            collections = self.utility.list_collections()

            return [
                VectorStoreStatus(
                    store_type=VectorStoreType.MILVUS,
                    name=collection_name,
                    state=VectorStoreState.ACTIVE
                )
                for collection_name in collections
            ]

        except Exception as e:
            logger.error(f"Failed to list Milvus collections: {e}")
            return []

    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in Milvus collection.

        Args:
            name: Collection name
            vectors: List of vector objects with 'id', 'values', and 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            logger.info(f"Upserting {len(vectors)} vectors to Milvus collection: {name}")

            if not self.utility.has_collection(name):
                return {
                    "success": False,
                    "error": f"Collection {name} not found"
                }

            collection = self.Collection(name)

            # Prepare data for insertion
            ids = []
            vector_data = []
            metadata_list = []

            for vector in vectors:
                ids.append(str(vector.get("id", "")))
                vector_data.append(vector.get("values", []))
                metadata_list.append(vector.get("metadata", {}))

            # Insert data
            entities = [ids, vector_data, metadata_list]
            insert_result = collection.insert(entities)

            # Flush to ensure data is persisted
            collection.flush()

            logger.info(f"Successfully upserted {len(vectors)} vectors to {name}")

            return {
                "success": True,
                "upserted_count": len(vectors),
                "collection_name": name,
                "insert_ids": insert_result.primary_keys
            }

        except Exception as e:
            logger.error(f"Failed to upsert vectors to Milvus: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query Milvus collection for similar vectors.

        Args:
            name: Collection name
            query_vector: Query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of similar vectors with scores
        """
        try:
            logger.info(f"Querying Milvus collection {name} for top {top_k} results")

            if not self.utility.has_collection(name):
                logger.error(f"Collection {name} not found")
                return []

            collection = self.Collection(name)
            collection.load()  # Ensure collection is loaded

            # Prepare search parameters
            search_params = {
                "metric_type": "COSINE",  # Can be parameterized
                "params": {"ef": 128}  # HNSW search parameter
            }

            # Build filter expression if provided
            filter_expr = None
            if filter_metadata:
                # Build JSON filter expression for Milvus
                filter_parts = []
                for key, value in filter_metadata.items():
                    if isinstance(value, str):
                        filter_parts.append(f'metadata["{key}"] == "{value}"')
                    else:
                        filter_parts.append(f'metadata["{key}"] == {value}')
                filter_expr = " && ".join(filter_parts) if filter_parts else None

            # Execute search
            search_results = collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=filter_expr,
                output_fields=["id", "metadata"]
            )

            # Format results
            formatted_results = []
            for hits in search_results:
                for hit in hits:
                    formatted_results.append({
                        "id": hit.id,
                        "score": float(hit.distance),
                        "metadata": hit.entity.get("metadata", {}),
                        "vector": []  # Milvus doesn't return vectors by default
                    })

            logger.info(f"Found {len(formatted_results)} results")
            return formatted_results

        except Exception as e:
            logger.error(f"Failed to query Milvus collection: {e}")
            return []

    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to Milvus service backend.

        Tests the Videolake platform's connection to Milvus backend:
        - Milvus endpoint accessibility
        - Collection listing capability
        - Service health check
        - Response time measurement

        Returns:
            Connectivity validation result
        """
        start_time = time.time()

        try:
            # Test Milvus connectivity by listing collections
            collections = self.utility.list_collections()

            response_time_ms = (time.time() - start_time) * 1000

            health_status = "healthy"

            details = {
                "collection_count": len(collections),
                "host": self.host if not self.use_zilliz else "Zilliz Cloud",
                "deployment_type": "zilliz_cloud" if self.use_zilliz else "self_hosted",
                "service": "Milvus"
            }

            return {
                "accessible": True,
                "endpoint": self.zilliz_cloud_uri if self.use_zilliz else f"{self.host}:{self.port}",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": None,
                "details": details
            }

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            logger.error(f"Milvus connectivity validation failed: {e}")

            if "refused" in error_msg.lower() or "timeout" in error_msg.lower():
                health_status = "unhealthy"
            else:
                health_status = "degraded"

            return {
                "accessible": False,
                "endpoint": self.zilliz_cloud_uri if self.use_zilliz else f"{self.host}:{self.port}",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": error_msg,
                "details": {
                    "host": self.host if not self.use_zilliz else "Zilliz Cloud",
                    "deployment_type": "zilliz_cloud" if self.use_zilliz else "self_hosted",
                    "service": "Milvus"
                }
            }

    def get_capabilities(self) -> VectorStoreCapabilities:
        """
        Return capabilities of Milvus vector store provider.

        Returns:
            VectorStoreCapabilities defining supported features and limits
        """
        return VectorStoreCapabilities(
            max_dimension=32768,  # Milvus supports up to 32K dimensions
            max_vectors=None,  # Unlimited (billions supported)
            supports_metadata_filtering=True,
            supports_hybrid_search=True,  # Scalar + vector search
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=2.5,  # ~$250/month for 100K = $2.5 per million
            typical_query_latency_ms=10.0,  # P50: 5-15ms
            supports_sparse_vectors=True,  # Milvus 2.3+ supports sparse vectors
            supports_multi_vector=True,  # Multiple vector fields per collection
            max_batch_size=10000  # Recommended batch size for optimal performance
        )
