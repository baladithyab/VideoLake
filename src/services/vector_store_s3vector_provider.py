"""
Videolake AWS S3Vector Backend Provider

Implements the Videolake VectorStoreProvider interface for AWS S3 Vectors service,
enabling the platform to leverage AWS's native vector storage capabilities as one
of its supported vector store backends.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreState,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreProviderFactory
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
            name: Name of the bucket (index ARN will be constructed)
            vectors: List of vector objects
            
        Returns:
            Result dictionary with upsert statistics
        """
        try:
            # This would need index_arn - simplified for now
            # In practice, you'd need to specify which index within the bucket
            logger.warning("upsert_vectors requires index ARN - use storage_manager directly")
            return {
                "success": False,
                "message": "Use S3VectorStorageManager.put_vectors with index ARN"
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
            name: Name of the bucket (index ARN will be constructed)
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional filters
            
        Returns:
            List of similar vectors with scores
        """
        try:
            # This would need index_ARN - simplified for now
            logger.warning("query requires index ARN - use storage_manager directly")
            return []
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []
    
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
        import time
        
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

