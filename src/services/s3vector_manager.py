"""
S3 Vector Manager - Manages S3 Vector buckets and indexes.

S3 Vectors is a specialized AWS service that provides native vector storage
with built-in similarity search. It uses a different API than regular S3.

Key differences from regular S3:
- Uses 's3vectors' CLI command, not 's3'
- Creates 'vector buckets', not regular buckets
- Supports vector indexes for similarity search
- Has different API endpoints (s3vectors.{region}.api.aws)
"""

import boto3
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3VectorManager:
    """
    Manages S3 Vector buckets and indexes using the S3 Vectors API.
    
    Note: S3 Vectors is currently in preview and requires special permissions.
    """
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize S3 Vector manager.
        
        Args:
            region: AWS region for S3 Vectors
        """
        self.region = region
        
        # S3 Vectors uses a different service endpoint
        try:
            self.client = boto3.client(
                's3vectors',
                region_name=region,
                endpoint_url=f'https://s3vectors.{region}.api.aws'
            )
        except Exception as e:
            logger.warning(f"S3 Vectors client not available: {e}")
            logger.warning("S3 Vectors is in preview - using fallback to regular S3")
            self.client = None
    
    def create_vector_bucket(
        self,
        bucket_name: str,
        encryption_type: str = "AES256",
        kms_key_arn: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create an S3 Vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            encryption_type: Encryption type (AES256 or aws:kms)
            kms_key_arn: KMS key ARN if using KMS encryption
            
        Returns:
            Response from CreateVectorBucket API
        """
        if not self.client:
            raise RuntimeError(
                "S3 Vectors client not available. "
                "S3 Vectors is in preview and may not be enabled in your account."
            )
        
        try:
            request_body = {
                "vectorBucketName": bucket_name
            }
            
            # Add encryption configuration if KMS is specified
            if encryption_type == "aws:kms" and kms_key_arn:
                request_body["encryptionConfiguration"] = {
                    "sseType": "aws:kms",
                    "kmsKeyArn": kms_key_arn
                }
            
            response = self.client.create_vector_bucket(**request_body)
            
            logger.info(f"Created S3 Vector bucket: {bucket_name}")
            return response
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ConflictException':
                logger.info(f"Vector bucket {bucket_name} already exists")
                return {"status": "already_exists"}
            elif error_code == 'AccessDeniedException':
                raise RuntimeError(
                    f"Access denied creating vector bucket. "
                    f"Ensure you have s3vectors:CreateVectorBucket permission."
                )
            else:
                raise RuntimeError(f"Failed to create vector bucket: {str(e)}")
    
    def create_index(
        self,
        bucket_name: str,
        index_name: str,
        dimension: int,
        data_type: str = "float32",
        distance_metric: str = "cosine"
    ) -> Dict[str, Any]:
        """
        Create a vector index in an S3 Vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the index
            dimension: Vector dimension (e.g., 384, 768, 1536)
            data_type: Data type (float32, float16, int8)
            distance_metric: Distance metric (cosine, euclidean, dot_product)
            
        Returns:
            Response from CreateIndex API
        """
        if not self.client:
            raise RuntimeError("S3 Vectors client not available")
        
        try:
            response = self.client.create_index(
                vectorBucketName=bucket_name,
                indexName=index_name,
                dataType=data_type,
                dimension=dimension,
                distanceMetric=distance_metric
            )
            
            logger.info(
                f"Created index '{index_name}' in bucket '{bucket_name}' "
                f"(dim={dimension}, metric={distance_metric})"
            )
            return response
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            
            if error_code == 'ConflictException':
                logger.info(f"Index {index_name} already exists in {bucket_name}")
                return {"status": "already_exists"}
            else:
                raise RuntimeError(f"Failed to create index: {str(e)}")
    
    def list_vector_buckets(self) -> List[Dict[str, Any]]:
        """
        List all S3 Vector buckets in the region.
        
        Returns:
            List of vector bucket summaries
        """
        if not self.client:
            return []
        
        try:
            response = self.client.list_vector_buckets()
            return response.get('vectorBuckets', [])
        except Exception as e:
            logger.error(f"Failed to list vector buckets: {e}")
            return []
    
    def list_indexes(self, bucket_name: str) -> List[Dict[str, Any]]:
        """
        List all indexes in a vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            
        Returns:
            List of index summaries
        """
        if not self.client:
            return []
        
        try:
            response = self.client.list_indexes(vectorBucketName=bucket_name)
            return response.get('indexes', [])
        except Exception as e:
            logger.error(f"Failed to list indexes in {bucket_name}: {e}")
            return []
    
    def delete_vector_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """
        Delete an S3 Vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket to delete
            
        Returns:
            Response from DeleteVectorBucket API
        """
        if not self.client:
            raise RuntimeError("S3 Vectors client not available")
        
        try:
            response = self.client.delete_vector_bucket(vectorBucketName=bucket_name)
            logger.info(f"Deleted S3 Vector bucket: {bucket_name}")
            return response
        except ClientError as e:
            raise RuntimeError(f"Failed to delete vector bucket: {str(e)}")
    
    def get_bucket_info(self, bucket_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            
        Returns:
            Bucket information or None if not found
        """
        if not self.client:
            return None
        
        try:
            response = self.client.get_vector_bucket(vectorBucketName=bucket_name)
            return response.get('vectorBucket', {})
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'ResourceNotFoundException':
                return None
            raise RuntimeError(f"Failed to get bucket info: {str(e)}")

