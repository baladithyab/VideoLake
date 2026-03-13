"""
Videolake AWS S3Vector Backend Provider

Implements the Videolake VectorStoreProvider interface for AWS S3 Vectors service,
enabling the platform to leverage AWS's native vector storage capabilities as one
of its supported vector store backends.
"""

import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreState,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreProviderFactory,
    VectorStoreCapabilities
)
from src.services.s3_vector_storage import S3VectorStorageManager
from src.utils.aws_clients import aws_client_factory
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


class S3VectorProvider(VectorStoreProvider):
    """
    AWS S3Vector backend implementation for Videolake platform.
    
    Provides integration with AWS S3 Vectors service, allowing Videolake to
    utilize AWS's native vector storage as a high-performance backend option.
    """
    
    def __init__(self):
        """Initialize the S3Vector provider."""
        self.storage_manager = S3VectorStorageManager()
        self.s3vectors_client = aws_client_factory.get_s3vectors_client()

        config_manager = get_unified_config_manager()
        self.region = config_manager.config.aws.region

    def _parse_name_to_arn(self, name: str) -> str:
        """
        Parse name parameter to construct or validate index ARN.

        Args:
            name: Either "bucket/index" format or full ARN

        Returns:
            Full index ARN
        """
        # If already an ARN, return as-is
        if name.startswith("arn:aws:s3vectors:"):
            return name

        # Parse "bucket/index" format
        if "/" in name:
            parts = name.split("/", 1)
            bucket_name = parts[0]
            index_name = parts[1]
        else:
            # If just bucket name, raise error - need index specification
            raise ValueError(
                f"Name must be in 'bucket/index' format or full ARN. Got: {name}"
            )

        # Construct ARN (simplified - would need account/region in production)
        # Format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
        return f"arn:aws:s3vectors:{self.region}:*:bucket/{bucket_name}/index/{index_name}"

    @property
    def store_type(self) -> VectorStoreType:
        """Return S3_VECTOR as the store type."""
        return VectorStoreType.S3_VECTOR
    
    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new AWS S3 Vector bucket for Videolake.
        
        Args:
            config: Configuration for the S3 Vector bucket
            
        Returns:
            VectorStoreStatus with creation result
        """
        self.validate_config(config)
        
        try:
            # Extract S3Vector-specific config
            s3v_config = config.s3vector_config or {}
            encryption_type = s3v_config.get("encryption_type", "SSE-S3")
            kms_key_arn = s3v_config.get("kms_key_arn")
            
            # Create the vector bucket
            result = self.storage_manager.create_vector_bucket(
                bucket_name=config.name,
                encryption_type=encryption_type,
                kms_key_arn=kms_key_arn
            )
            
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=config.name,
                state=VectorStoreState.ACTIVE,
                arn=result.get("bucket_arn"),
                region=self.region,
                created_at=datetime.now(timezone.utc),
                dimension=config.dimension,
                metadata={
                    "encryption_type": encryption_type,
                    "creation_result": result
                },
                progress_percentage=100
            )
            
        except Exception as e:
            logger.error(f"Failed to create S3 Vector bucket: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete an S3 Vector bucket.
        
        Args:
            name: Name of the bucket
            force: Whether to force deletion
            
        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            # Delete the bucket
            self.s3vectors_client.delete_bucket(Bucket=name)
            
            # Update registry
            resource_registry.log_vector_bucket_deleted(bucket_name=name, source="s3vector_provider")
            
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=name,
                state=VectorStoreState.DELETED,
                progress_percentage=100
            )
            
        except Exception as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code in ('NoSuchBucket', '404'):
                return VectorStoreStatus(
                    store_type=VectorStoreType.S3_VECTOR,
                    name=name,
                    state=VectorStoreState.DELETED,
                    progress_percentage=100
                )
            
            logger.error(f"Failed to delete S3 Vector bucket: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get current status of an S3 Vector bucket.
        
        Args:
            name: Name of the bucket
            
        Returns:
            VectorStoreStatus with current state
        """
        try:
            response = self.s3vectors_client.list_vector_buckets()
            buckets = response.get('vectorBuckets', [])
            
            for bucket in buckets:
                if bucket.get('vectorBucketName') == name:
                    return VectorStoreStatus(
                        store_type=VectorStoreType.S3_VECTOR,
                        name=name,
                        state=VectorStoreState.ACTIVE,
                        arn=bucket.get('vectorBucketArn'),
                        region=self.region,
                        metadata=bucket,
                        progress_percentage=100
                    )
            
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=name,
                state=VectorStoreState.NOT_FOUND,
                progress_percentage=0
            )
            
        except Exception as e:
            logger.error(f"Failed to get S3 Vector bucket status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.S3_VECTOR,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all S3 Vector buckets.
        
        Returns:
            List of VectorStoreStatus objects
        """
        try:
            response = self.s3vectors_client.list_vector_buckets()
            buckets = response.get('vectorBuckets', [])
            
            stores = []
            for bucket in buckets:
                stores.append(VectorStoreStatus(
                    store_type=VectorStoreType.S3_VECTOR,
                    name=bucket.get('vectorBucketName'),
                    state=VectorStoreState.ACTIVE,
                    arn=bucket.get('vectorBucketArn'),
                    region=self.region,
                    metadata=bucket,
                    progress_percentage=100
                ))
            
            return stores
            
        except Exception as e:
            logger.error(f"Failed to list S3 Vector buckets: {e}")
            return []
    
    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in an S3 Vector index.

        Args:
            name: Name in format "bucket/index" or full index ARN
            vectors: List of vector objects with 'id', 'values', and optional 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            # Parse name to get index ARN
            index_arn = self._parse_name_to_arn(name)

            # Transform vectors from generic format to S3Vector format
            # Generic format: {"id": "...", "values": [...], "metadata": {...}}
            # S3Vector format: {"key": "...", "data": {"float32": [...]}, "metadata": {...}}
            vectors_data = []
            for vector in vectors:
                vector_obj = {
                    "key": vector.get("id", vector.get("key")),
                    "data": {
                        "float32": vector.get("values", vector.get("data", {}).get("float32", []))
                    }
                }
                if "metadata" in vector:
                    vector_obj["metadata"] = vector["metadata"]
                vectors_data.append(vector_obj)

            # Delegate to storage manager
            result = self.storage_manager.put_vectors(
                index_arn=index_arn,
                vectors_data=vectors_data
            )

            return {
                "success": True,
                "upserted_count": len(vectors_data),
                "result": result
            }

        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query an S3 Vector index for similar vectors.

        Args:
            name: Name in format "bucket/index" or full index ARN
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of similar vectors with scores
        """
        try:
            # Parse name to get index ARN
            index_arn = self._parse_name_to_arn(name)

            # Delegate to storage manager
            result = self.storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=top_k,
                metadata_filter=filter_metadata
            )

            # Extract vectors from result
            vectors = result.get("vectors", [])

            # Transform from S3Vector format to generic format
            # S3Vector format: {"key": "...", "dist": ..., "data": {"float32": [...]}, "metadata": {...}}
            # Generic format: {"id": "...", "score": ..., "values": [...], "metadata": {...}}
            results = []
            for vector_result in vectors:
                results.append({
                    "id": vector_result.get("key"),
                    "score": vector_result.get("dist", 0.0),
                    "values": vector_result.get("data", {}).get("float32", []),
                    "metadata": vector_result.get("metadata", {})
                })

            return results

        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []

    def get_capabilities(self) -> VectorStoreCapabilities:
        """
        Return S3 Vector provider capabilities.

        Returns:
            VectorStoreCapabilities with S3 Vectors specifications
        """
        return VectorStoreCapabilities(
            max_dimension=2048,  # S3 Vectors supports up to 2048 dimensions
            max_vectors=None,  # Unlimited
            supports_metadata_filtering=True,
            supports_hybrid_search=False,
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=10.0,  # Approximate AWS S3 Vectors pricing
            typical_query_latency_ms=50.0,
            supports_sparse_vectors=False,
            supports_multi_vector=False,
            max_batch_size=10000
        )

    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to AWS S3 Vectors service.

        Tests the Videolake platform's connection to AWS S3 Vectors backend:
        - S3 bucket listing functionality
        - S3Vectors client accessibility
        - Response time measurement

        Returns:
            Connectivity validation result
        """
        start_time = time.time()
        
        try:
            # Test S3Vectors client connectivity by listing vector buckets
            response = self.s3vectors_client.list_vector_buckets()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Check if we got a valid response
            if 'vectorBuckets' in response:
                bucket_count = len(response.get('vectorBuckets', []))
                
                return {
                    "accessible": True,
                    "endpoint": f"s3vectors.{self.region}.amazonaws.com",
                    "response_time_ms": round(response_time_ms, 2),
                    "health_status": "healthy",
                    "error_message": None,
                    "details": {
                        "bucket_count": bucket_count,
                        "region": self.region,
                        "service": "S3 Vectors"
                    }
                }
            else:
                return {
                    "accessible": False,
                    "endpoint": f"s3vectors.{self.region}.amazonaws.com",
                    "response_time_ms": round(response_time_ms, 2),
                    "health_status": "unhealthy",
                    "error_message": "Invalid response from S3 Vectors service"
                }
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"S3 Vectors connectivity validation failed: {e}")
            
            return {
                "accessible": False,
                "endpoint": f"s3vectors.{self.region}.amazonaws.com",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": "unhealthy",
                "error_message": error_msg,
                "details": {
                    "region": self.region,
                    "service": "S3 Vectors"
                }
            }

