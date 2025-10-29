"""
S3 Vector Storage Manager - Facade Pattern.

This is the refactored version that delegates to specialized managers.
Maintains backward compatibility with existing code while providing
a clean, maintainable architecture.

The manager now acts as a facade, coordinating:
- S3VectorBucketManager: Bucket operations
- S3VectorIndexManager: Index operations
- S3VectorOperations: Vector CRUD operations

This replaces the original 2,467-line monolithic s3_vector_storage.py.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Dict, Any, Optional, List

from src.services.s3vector import (
    S3VectorBucketManager,
    S3VectorIndexManager,
    S3VectorOperations
)
from src.utils.aws_clients import aws_client_factory
from src.utils.arn_parser import ARNParser
from src.utils.logging_config import get_logger, get_structured_logger

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)

# Legacy helper functions for backward compatibility
def _to_vectors_resource_id(bucket: str, index: str) -> str:
    """Return S3 Vectors resource-id format expected by certain API params."""
    return ARNParser.to_resource_id(bucket, index)


def _to_resource_id(bucket: str, index: str) -> str:
    """
    Generate a normalized resource-id for an index.
    Exposed for external use.
    """
    return ARNParser.to_resource_id(bucket, index)


class S3VectorStorageManager:
    """
    Facade for S3 vector storage operations.

    Delegates to specialized managers while maintaining backward compatibility.
    """

    def __init__(self):
        """Initialize storage manager with specialized sub-managers."""
        structured_logger.log_function_entry("s3vector_storage_manager_init")

        try:
            # Initialize specialized managers
            self.bucket_manager = S3VectorBucketManager()
            self.index_manager = S3VectorIndexManager()
            self.vector_ops = S3VectorOperations()

            # Keep AWS clients for any direct operations needed
            self.s3vectors_client = aws_client_factory.get_s3vectors_client()
            self.s3_client = aws_client_factory.get_s3_client()

            # Multi-index coordination (for advanced features)
            self.index_registry: Dict[str, Dict[str, Any]] = {}
            self._registry_lock = Lock()
            self.executor = ThreadPoolExecutor(max_workers=10)

            # Vector type management (for multi-index support)
            self.vector_type_configs = {
                "visual-text": {"dimensions": 1024, "default_metric": "cosine"},
                "visual-image": {"dimensions": 1024, "default_metric": "cosine"},
                "audio": {"dimensions": 1024, "default_metric": "cosine"},
                "text-titan": {"dimensions": 1536, "default_metric": "cosine"}
            }

            structured_logger.log_operation(
                "s3vector_storage_manager_initialized",
                level="INFO",
                managers=["bucket", "index", "vector_ops"]
            )

        except Exception as e:
            structured_logger.log_error("s3vector_storage_manager_init", e)
            raise
        finally:
            structured_logger.log_function_exit("s3vector_storage_manager_init")

    # ==================== Bucket Operations (Delegated) ====================

    def create_vector_bucket(
        self,
        bucket_name: str,
        encryption_type: str = "SSE-S3",
        kms_key_arn: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create vector bucket. Delegates to BucketManager."""
        return self.bucket_manager.create_vector_bucket(
            bucket_name, encryption_type, kms_key_arn
        )

    def get_vector_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Get vector bucket. Delegates to BucketManager."""
        return self.bucket_manager.get_vector_bucket(bucket_name)

    def list_vector_buckets(self) -> List[Dict[str, Any]]:
        """List vector buckets. Delegates to BucketManager."""
        return self.bucket_manager.list_vector_buckets()

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists. Delegates to BucketManager."""
        return self.bucket_manager.bucket_exists(bucket_name)

    def delete_vector_bucket(
        self,
        bucket_name: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """Delete vector bucket. Delegates to BucketManager."""
        if cascade:
            # If cascade, delete all indexes first
            try:
                indexes = self.list_vector_indexes(bucket_name)
                for index in indexes:
                    index_name = index.get('indexName')
                    if index_name:
                        logger.info(f"Cascade deleting index: {index_name}")
                        self.delete_vector_index(bucket_name, index_name)
            except Exception as e:
                logger.warning(f"Error during cascade delete: {e}")

        return self.bucket_manager.delete_vector_bucket(bucket_name, cascade)

    # ==================== Index Operations (Delegated) ====================

    def create_vector_index(
        self,
        bucket_name: str,
        index_name: str,
        dimensions: int,
        distance_metric: str = "cosine",
        data_type: str = "float32",
        non_filterable_metadata_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create vector index. Delegates to IndexManager."""
        return self.index_manager.create_vector_index(
            bucket_name,
            index_name,
            dimensions,
            distance_metric,
            data_type,
            non_filterable_metadata_keys
        )

    # Alias for backward compatibility
    def create_index(self, *args, **kwargs) -> Dict[str, Any]:
        """Alias for create_vector_index."""
        return self.create_vector_index(*args, **kwargs)

    def list_vector_indexes(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List vector indexes. Delegates to IndexManager."""
        return self.index_manager.list_vector_indexes(
            bucket_name, prefix, max_results
        )

    def get_vector_index_metadata(
        self,
        bucket_name: str,
        index_name: str
    ) -> Dict[str, Any]:
        """Get index metadata. Delegates to IndexManager."""
        return self.index_manager.get_vector_index_metadata(
            bucket_name, index_name
        )

    def delete_vector_index(
        self,
        bucket_name: str,
        index_name: str
    ) -> Dict[str, Any]:
        """Delete vector index. Delegates to IndexManager."""
        return self.index_manager.delete_vector_index(bucket_name, index_name)

    def delete_index_with_retries(
        self,
        bucket: str,
        index: str,
        max_attempts: int = 6,
        backoff_base: float = 1.0
    ) -> bool:
        """Delete index with retries. Delegates to IndexManager."""
        return self.index_manager.delete_index_with_retries(
            bucket, index, max_attempts, backoff_base
        )

    def index_exists(
        self,
        bucket_name: str,
        index_name: str
    ) -> bool:
        """Check if index exists. Delegates to IndexManager."""
        return self.index_manager.index_exists(bucket_name, index_name)

    # ==================== Vector Operations (Delegated) ====================

    def put_vectors(
        self,
        index_arn: str,
        vectors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Store vectors. Delegates to VectorOperations."""
        return self.vector_ops.put_vectors(index_arn, vectors_data)

    def query_vectors(
        self,
        index_arn: str,
        query_vector: List[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query vectors. Delegates to VectorOperations."""
        return self.vector_ops.query_vectors(
            index_arn, query_vector, top_k, metadata_filter
        )

    def list_vectors(
        self,
        index_arn: str,
        max_results: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List vectors. Delegates to VectorOperations."""
        return self.vector_ops.list_vectors(index_arn, max_results, next_token)

    def put_vectors_batch(
        self,
        index_arn: str,
        vectors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Batch store vectors. Delegates to VectorOperations."""
        return self.vector_ops.put_vectors_batch(index_arn, vectors_data)

    def query_similar_vectors(
        self,
        index_arn: str,
        query_vector: List[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query similar vectors. Delegates to VectorOperations."""
        return self.vector_ops.query_similar_vectors(
            index_arn, query_vector, top_k, metadata_filter
        )

    # ==================== Multi-Index Operations ====================
    # These remain in the facade for now as they coordinate across managers

    def register_vector_index(
        self,
        index_arn: str,
        vector_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Register an index for multi-index operations."""
        with self._registry_lock:
            self.index_registry[index_arn] = {
                "vector_type": vector_type,
                "index_arn": index_arn,
                "metadata": metadata or {}
            }
            logger.info(f"Registered index {index_arn} for vector type {vector_type}")

    def get_multi_index_stats(self) -> Dict[str, Any]:
        """Get statistics about registered indexes."""
        with self._registry_lock:
            return {
                "registered_index_count": len(self.index_registry),
                "vector_types": list(set(
                    idx["vector_type"] for idx in self.index_registry.values()
                )),
                "indexes": list(self.index_registry.keys())
            }

    # ==================== Legacy/Deprecated Methods ====================
    # Keep for backward compatibility, but delegate to new managers

    def create_multi_index_architecture(
        self,
        bucket_name: str,
        base_index_name: str,
        vector_types: List[str]
    ) -> Dict[str, Any]:
        """
        Create multiple indexes for different vector types.
        Legacy method maintained for backward compatibility.
        """
        logger.info(f"Creating multi-index architecture: {base_index_name} for types: {vector_types}")

        results = {
            "bucket_name": bucket_name,
            "base_index_name": base_index_name,
            "created_indexes": [],
            "failed_indexes": []
        }

        for vector_type in vector_types:
            if vector_type not in self.vector_type_configs:
                logger.warning(f"Unknown vector type: {vector_type}, skipping")
                continue

            index_name = f"{base_index_name}-{vector_type}"
            config = self.vector_type_configs[vector_type]

            try:
                result = self.create_vector_index(
                    bucket_name=bucket_name,
                    index_name=index_name,
                    dimensions=config["dimensions"],
                    distance_metric=config["default_metric"]
                )

                if result.get("status") in ["created", "already_exists"]:
                    results["created_indexes"].append({
                        "index_name": index_name,
                        "vector_type": vector_type,
                        "status": result["status"]
                    })

                    # Register for multi-index operations
                    # Build ARN (simplified - would need account/region in production)
                    index_arn = f"arn:aws:s3vectors:*:*:bucket/{bucket_name}/index/{index_name}"
                    self.register_vector_index(index_arn, vector_type)

            except Exception as e:
                logger.error(f"Failed to create index {index_name}: {e}")
                results["failed_indexes"].append({
                    "index_name": index_name,
                    "vector_type": vector_type,
                    "error": str(e)
                })

        results["success"] = len(results["created_indexes"]) > 0
        return results
