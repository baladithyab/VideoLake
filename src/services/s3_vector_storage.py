"""
S3 Vector Storage Manager for managing vector buckets and operations.

This module provides functionality for creating and managing S3 vector buckets,
with proper IAM permissions, validation, and error handling.
"""

import time
import random
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, BotoCoreError
import logging

from src.utils.aws_clients import aws_client_factory
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class S3VectorStorageManager:
    """Manages S3 vector bucket operations with proper error handling and validation."""
    
    def __init__(self):
        self.s3vectors_client = aws_client_factory.get_s3vectors_client()
        self.s3_client = aws_client_factory.get_s3_client()
    
    def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """Implement exponential backoff for AWS API calls."""
        for attempt in range(max_retries):
            try:
                return func()
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['Throttling', 'ServiceUnavailable', 'InternalError', 'TooManyRequestsException']:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(
                            f"Retrying after {delay:.2f}s due to {error_code} (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                raise
            except BotoCoreError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Retrying after {delay:.2f}s due to BotoCoreError (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    continue
                raise
    
    def _validate_bucket_name(self, bucket_name: str) -> None:
        """Validate vector bucket name according to S3 Vectors requirements."""
        if not bucket_name:
            raise ValidationError(
                "Vector bucket name cannot be empty",
                error_code="EMPTY_BUCKET_NAME"
            )
        
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            raise ValidationError(
                f"Vector bucket name must be between 3 and 63 characters, got {len(bucket_name)}",
                error_code="INVALID_BUCKET_NAME_LENGTH",
                error_details={"bucket_name": bucket_name, "length": len(bucket_name)}
            )
        
        # Check for valid characters (lowercase letters, numbers, hyphens)
        if not all(c.islower() or c.isdigit() or c == '-' for c in bucket_name):
            raise ValidationError(
                "Vector bucket name can only contain lowercase letters, numbers, and hyphens",
                error_code="INVALID_BUCKET_NAME_CHARS",
                error_details={"bucket_name": bucket_name}
            )
        
        # Cannot start or end with hyphen
        if bucket_name.startswith('-') or bucket_name.endswith('-'):
            raise ValidationError(
                "Vector bucket name cannot start or end with a hyphen",
                error_code="INVALID_BUCKET_NAME_HYPHEN",
                error_details={"bucket_name": bucket_name}
            )
        
        # Cannot have consecutive hyphens
        if '--' in bucket_name:
            raise ValidationError(
                "Vector bucket name cannot contain consecutive hyphens",
                error_code="INVALID_BUCKET_NAME_CONSECUTIVE_HYPHENS",
                error_details={"bucket_name": bucket_name}
            )
    
    def create_vector_bucket(self, 
                           bucket_name: str, 
                           encryption_type: str = "SSE-S3",
                           kms_key_arn: Optional[str] = None) -> Dict[str, Any]:
        """
        Create an S3 vector bucket with proper configuration.
        
        Args:
            bucket_name: Name of the vector bucket to create
            encryption_type: Encryption type ("SSE-S3" or "SSE-KMS")
            kms_key_arn: KMS key ARN (required if encryption_type is "SSE-KMS")
        
        Returns:
            Dict containing bucket creation response and metadata
        
        Raises:
            ValidationError: If bucket name or parameters are invalid
            VectorStorageError: If bucket creation fails
        """
        logger.info(f"Creating vector bucket: {bucket_name}")
        
        # Validate bucket name
        self._validate_bucket_name(bucket_name)
        
        # Validate encryption configuration
        if encryption_type not in ["SSE-S3", "SSE-KMS"]:
            raise ValidationError(
                f"Invalid encryption type: {encryption_type}. Must be 'SSE-S3' or 'SSE-KMS'",
                error_code="INVALID_ENCRYPTION_TYPE",
                error_details={"encryption_type": encryption_type}
            )
        
        if encryption_type == "SSE-KMS" and not kms_key_arn:
            raise ValidationError(
                "KMS key ARN is required when using SSE-KMS encryption",
                error_code="MISSING_KMS_KEY_ARN"
            )
        
        # Prepare request parameters
        request_params = {
            "vectorBucketName": bucket_name
        }
        
        # Add encryption configuration if specified
        if encryption_type == "SSE-KMS" and kms_key_arn:
            request_params["encryptionConfiguration"] = {
                "sseType": encryption_type,
                "kmsKeyArn": kms_key_arn
            }
        elif encryption_type == "SSE-S3":
            request_params["encryptionConfiguration"] = {
                "sseType": encryption_type
            }
        
        def _create_bucket():
            return self.s3vectors_client.create_vector_bucket(**request_params)
        
        try:
            response = self._retry_with_backoff(_create_bucket)
            
            logger.info(f"Successfully created vector bucket: {bucket_name}")
            
            return {
                "bucket_name": bucket_name,
                "status": "created",
                "encryption_type": encryption_type,
                "kms_key_arn": kms_key_arn,
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ConflictException':
                logger.warning(f"Vector bucket {bucket_name} already exists")
                return {
                    "bucket_name": bucket_name,
                    "status": "already_exists",
                    "encryption_type": encryption_type,
                    "kms_key_arn": kms_key_arn,
                    "message": "Bucket already exists"
                }
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when creating vector bucket: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "required_permission": "s3vectors:CreateVectorBucket"
                    }
                )
            elif error_code == 'ServiceQuotaExceededException':
                raise VectorStorageError(
                    f"Service quota exceeded when creating vector bucket: {error_message}",
                    error_code="QUOTA_EXCEEDED",
                    error_details={"bucket_name": bucket_name}
                )
            else:
                raise VectorStorageError(
                    f"Failed to create vector bucket {bucket_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error creating vector bucket {bucket_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error creating vector bucket {bucket_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"bucket_name": bucket_name, "error": str(e)}
            )
    
    def get_vector_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """
        Get vector bucket attributes and configuration.
        
        Args:
            bucket_name: Name of the vector bucket
        
        Returns:
            Dict containing bucket attributes
        
        Raises:
            ValidationError: If bucket name is invalid
            VectorStorageError: If operation fails
        """
        logger.info(f"Getting vector bucket attributes: {bucket_name}")
        
        self._validate_bucket_name(bucket_name)
        
        def _get_bucket():
            return self.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
        
        try:
            response = self._retry_with_backoff(_get_bucket)
            
            logger.info(f"Successfully retrieved vector bucket attributes: {bucket_name}")
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NoSuchBucket':
                raise VectorStorageError(
                    f"Vector bucket {bucket_name} does not exist",
                    error_code="BUCKET_NOT_FOUND",
                    error_details={"bucket_name": bucket_name}
                )
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when accessing vector bucket: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "required_permission": "s3vectors:GetVectorBucket"
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to get vector bucket {bucket_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error getting vector bucket {bucket_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error getting vector bucket {bucket_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"bucket_name": bucket_name, "error": str(e)}
            )
    
    def list_vector_buckets(self) -> List[Dict[str, Any]]:
        """
        List all vector buckets in the current region.
        
        Returns:
            List of vector bucket information
        
        Raises:
            VectorStorageError: If operation fails
        """
        logger.info("Listing vector buckets")
        
        def _list_buckets():
            return self.s3vectors_client.list_vector_buckets()
        
        try:
            response = self._retry_with_backoff(_list_buckets)
            
            buckets = response.get('vectorBuckets', [])
            logger.info(f"Successfully listed {len(buckets)} vector buckets")
            
            return buckets
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when listing vector buckets: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={"required_permission": "s3vectors:ListVectorBuckets"}
                )
            else:
                raise VectorStorageError(
                    f"Failed to list vector buckets: {error_message}",
                    error_code=error_code,
                    error_details={
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error listing vector buckets: {e}")
            raise VectorStorageError(
                f"Unexpected error listing vector buckets: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"error": str(e)}
            )
    
    def bucket_exists(self, bucket_name: str) -> bool:
        """
        Check if a vector bucket exists.
        
        Args:
            bucket_name: Name of the vector bucket
        
        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.get_vector_bucket(bucket_name)
            return True
        except VectorStorageError as e:
            if e.error_code == "BUCKET_NOT_FOUND":
                return False
            raise
    
    def _validate_index_name(self, index_name: str) -> None:
        """Validate vector index name according to S3 Vectors requirements."""
        if not index_name:
            raise ValidationError(
                "Vector index name cannot be empty",
                error_code="EMPTY_INDEX_NAME"
            )
        
        if len(index_name) < 3 or len(index_name) > 63:
            raise ValidationError(
                f"Vector index name must be between 3 and 63 characters, got {len(index_name)}",
                error_code="INVALID_INDEX_NAME_LENGTH",
                error_details={"index_name": index_name, "length": len(index_name)}
            )
        
        # Check for valid characters (lowercase letters, numbers, hyphens)
        if not all(c.islower() or c.isdigit() or c == '-' for c in index_name):
            raise ValidationError(
                "Vector index name can only contain lowercase letters, numbers, and hyphens",
                error_code="INVALID_INDEX_NAME_CHARS",
                error_details={"index_name": index_name}
            )
        
        # Cannot start or end with hyphen
        if index_name.startswith('-') or index_name.endswith('-'):
            raise ValidationError(
                "Vector index name cannot start or end with a hyphen",
                error_code="INVALID_INDEX_NAME_HYPHEN",
                error_details={"index_name": index_name}
            )
    
    def _validate_vector_dimensions(self, dimensions: int) -> None:
        """Validate vector dimensions according to S3 Vectors requirements."""
        if not isinstance(dimensions, int):
            raise ValidationError(
                f"Vector dimensions must be an integer, got {type(dimensions).__name__}",
                error_code="INVALID_DIMENSIONS_TYPE",
                error_details={"dimensions": dimensions, "type": type(dimensions).__name__}
            )
        
        if dimensions < 1 or dimensions > 4096:
            raise ValidationError(
                f"Vector dimensions must be between 1 and 4096, got {dimensions}",
                error_code="INVALID_DIMENSIONS_RANGE",
                error_details={"dimensions": dimensions}
            )
    
    def create_vector_index(self,
                          bucket_name: str,
                          index_name: str,
                          dimensions: int,
                          distance_metric: str = "cosine",
                          data_type: str = "float32",
                          non_filterable_metadata_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create a vector index within a vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index to create
            dimensions: Dimensions of the vectors (1-4096)
            distance_metric: Distance metric for similarity search ("cosine" or "euclidean")
            data_type: Data type of vectors ("float32")
            non_filterable_metadata_keys: List of metadata keys that won't be filterable
        
        Returns:
            Dict containing index creation response and metadata
        
        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If index creation fails
        """
        logger.info(f"Creating vector index: {index_name} in bucket: {bucket_name}")
        
        # Validate inputs
        self._validate_bucket_name(bucket_name)
        self._validate_index_name(index_name)
        self._validate_vector_dimensions(dimensions)
        
        if distance_metric not in ["cosine", "euclidean"]:
            raise ValidationError(
                f"Invalid distance metric: {distance_metric}. Must be 'cosine' or 'euclidean'",
                error_code="INVALID_DISTANCE_METRIC",
                error_details={"distance_metric": distance_metric}
            )
        
        if data_type != "float32":
            raise ValidationError(
                f"Invalid data type: {data_type}. Must be 'float32'",
                error_code="INVALID_DATA_TYPE",
                error_details={"data_type": data_type}
            )
        
        # Prepare request parameters
        request_params = {
            "vectorBucketName": bucket_name,
            "indexName": index_name,
            "dimension": dimensions,
            "distanceMetric": distance_metric,
            "dataType": data_type
        }
        
        # Add metadata configuration if specified
        if non_filterable_metadata_keys:
            request_params["metadataConfiguration"] = {
                "nonFilterableMetadataKeys": non_filterable_metadata_keys
            }
        
        def _create_index():
            return self.s3vectors_client.create_index(**request_params)
        
        try:
            response = self._retry_with_backoff(_create_index)
            
            logger.info(f"Successfully created vector index: {index_name} in bucket: {bucket_name}")
            
            return {
                "bucket_name": bucket_name,
                "index_name": index_name,
                "dimensions": dimensions,
                "distance_metric": distance_metric,
                "data_type": data_type,
                "non_filterable_metadata_keys": non_filterable_metadata_keys,
                "status": "created",
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'ConflictException':
                logger.warning(f"Vector index {index_name} already exists in bucket {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "dimensions": dimensions,
                    "distance_metric": distance_metric,
                    "data_type": data_type,
                    "status": "already_exists",
                    "message": "Index already exists"
                }
            elif error_code == 'NotFoundException':
                raise VectorStorageError(
                    f"Vector bucket {bucket_name} not found",
                    error_code="BUCKET_NOT_FOUND",
                    error_details={"bucket_name": bucket_name}
                )
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when creating vector index: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "required_permission": "s3vectors:CreateIndex"
                    }
                )
            elif error_code == 'ServiceQuotaExceededException':
                raise VectorStorageError(
                    f"Service quota exceeded when creating vector index: {error_message}",
                    error_code="QUOTA_EXCEEDED",
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to create vector index {index_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error creating vector index {index_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error creating vector index {index_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "error": str(e)
                }
            )
    
    def list_vector_indexes(self,
                          bucket_name: str,
                          prefix: Optional[str] = None,
                          max_results: Optional[int] = None,
                          next_token: Optional[str] = None) -> Dict[str, Any]:
        """
        List vector indexes within a vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            prefix: Prefix to filter index names
            max_results: Maximum number of results to return (1-500)
            next_token: Token for pagination
        
        Returns:
            Dict containing list of indexes and pagination info
        
        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If operation fails
        """
        logger.info(f"Listing vector indexes in bucket: {bucket_name}")
        
        # Validate inputs
        self._validate_bucket_name(bucket_name)
        
        if max_results is not None:
            if not isinstance(max_results, int) or max_results < 1 or max_results > 500:
                raise ValidationError(
                    f"max_results must be an integer between 1 and 500, got {max_results}",
                    error_code="INVALID_MAX_RESULTS",
                    error_details={"max_results": max_results}
                )
        
        if prefix is not None:
            if not isinstance(prefix, str) or len(prefix) < 1 or len(prefix) > 63:
                raise ValidationError(
                    f"prefix must be a string between 1 and 63 characters, got {prefix}",
                    error_code="INVALID_PREFIX",
                    error_details={"prefix": prefix}
                )
        
        if next_token is not None:
            if not isinstance(next_token, str) or len(next_token) < 1 or len(next_token) > 512:
                raise ValidationError(
                    f"next_token must be a string between 1 and 512 characters",
                    error_code="INVALID_NEXT_TOKEN",
                    error_details={"next_token": next_token}
                )
        
        # Prepare request parameters
        request_params = {
            "vectorBucketName": bucket_name
        }
        
        if prefix is not None:
            request_params["prefix"] = prefix
        if max_results is not None:
            request_params["maxResults"] = max_results
        if next_token is not None:
            request_params["nextToken"] = next_token
        
        def _list_indexes():
            return self.s3vectors_client.list_indexes(**request_params)
        
        try:
            response = self._retry_with_backoff(_list_indexes)
            
            indexes = response.get('indexes', [])
            next_token = response.get('nextToken')
            
            logger.info(f"Successfully listed {len(indexes)} vector indexes in bucket: {bucket_name}")
            
            return {
                "bucket_name": bucket_name,
                "indexes": indexes,
                "next_token": next_token,
                "count": len(indexes)
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotFoundException':
                raise VectorStorageError(
                    f"Vector bucket {bucket_name} not found",
                    error_code="BUCKET_NOT_FOUND",
                    error_details={"bucket_name": bucket_name}
                )
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when listing vector indexes: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "required_permission": "s3vectors:ListIndexes"
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to list vector indexes in bucket {bucket_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error listing vector indexes in bucket {bucket_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error listing vector indexes in bucket {bucket_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"bucket_name": bucket_name, "error": str(e)}
            )
    
    def get_vector_index_metadata(self,
                                bucket_name: str,
                                index_name: str) -> Dict[str, Any]:
        """
        Get metadata for a specific vector index.
        
        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index
        
        Returns:
            Dict containing index metadata
        
        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If operation fails
        """
        logger.info(f"Getting metadata for vector index: {index_name} in bucket: {bucket_name}")
        
        # Validate inputs
        self._validate_bucket_name(bucket_name)
        self._validate_index_name(index_name)
        
        # List indexes with the specific name as prefix to find the exact match
        try:
            response = self.list_vector_indexes(bucket_name, prefix=index_name, max_results=500)
            indexes = response.get('indexes', [])
            
            # Find exact match
            matching_index = None
            for index in indexes:
                if index.get('indexName') == index_name:
                    matching_index = index
                    break
            
            if not matching_index:
                raise VectorStorageError(
                    f"Vector index {index_name} not found in bucket {bucket_name}",
                    error_code="INDEX_NOT_FOUND",
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name
                    }
                )
            
            logger.info(f"Successfully retrieved metadata for vector index: {index_name}")
            
            return {
                "bucket_name": bucket_name,
                "index_name": index_name,
                "index_arn": matching_index.get('indexArn'),
                "creation_time": matching_index.get('creationTime'),
                "metadata": matching_index
            }
            
        except VectorStorageError:
            # Re-raise VectorStorageError as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting vector index metadata: {e}")
            raise VectorStorageError(
                f"Unexpected error getting vector index metadata: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "error": str(e)
                }
            )
    
    def delete_vector_index(self,
                          bucket_name: Optional[str] = None,
                          index_name: Optional[str] = None,
                          index_arn: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a vector index.
        
        Args:
            bucket_name: Name of the vector bucket (required if index_arn not provided)
            index_name: Name of the vector index (required if index_arn not provided)
            index_arn: ARN of the vector index (alternative to bucket_name + index_name)
        
        Returns:
            Dict containing deletion response
        
        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If deletion fails
        """
        # Validate input combinations
        if index_arn:
            if bucket_name or index_name:
                raise ValidationError(
                    "Cannot specify both index_arn and bucket_name/index_name",
                    error_code="CONFLICTING_PARAMETERS",
                    error_details={
                        "index_arn": index_arn,
                        "bucket_name": bucket_name,
                        "index_name": index_name
                    }
                )
            logger.info(f"Deleting vector index by ARN: {index_arn}")
        else:
            if not bucket_name or not index_name:
                raise ValidationError(
                    "Must specify either index_arn or both bucket_name and index_name",
                    error_code="MISSING_PARAMETERS",
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "index_arn": index_arn
                    }
                )
            
            # Validate individual parameters
            self._validate_bucket_name(bucket_name)
            self._validate_index_name(index_name)
            
            logger.info(f"Deleting vector index: {index_name} in bucket: {bucket_name}")
        
        # Prepare request parameters
        request_params = {}
        if index_arn:
            request_params["indexArn"] = index_arn
        else:
            request_params["vectorBucketName"] = bucket_name
            request_params["indexName"] = index_name
        
        def _delete_index():
            return self.s3vectors_client.delete_index(**request_params)
        
        try:
            response = self._retry_with_backoff(_delete_index)
            
            if index_arn:
                logger.info(f"Successfully deleted vector index: {index_arn}")
            else:
                logger.info(f"Successfully deleted vector index: {index_name} in bucket: {bucket_name}")
            
            return {
                "bucket_name": bucket_name,
                "index_name": index_name,
                "index_arn": index_arn,
                "status": "deleted",
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotFoundException':
                # Index doesn't exist - this could be considered success
                logger.warning(f"Vector index not found (may already be deleted)")
                return {
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "index_arn": index_arn,
                    "status": "not_found",
                    "message": "Index not found (may already be deleted)"
                }
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when deleting vector index: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "index_arn": index_arn,
                        "required_permission": "s3vectors:DeleteIndex"
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to delete vector index: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "index_arn": index_arn,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error deleting vector index: {e}")
            raise VectorStorageError(
                f"Unexpected error deleting vector index: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "index_arn": index_arn,
                    "error": str(e)
                }
            )
    
    def index_exists(self,
                   bucket_name: str,
                   index_name: str) -> bool:
        """
        Check if a vector index exists.
        
        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index
        
        Returns:
            True if index exists, False otherwise
        """
        try:
            self.get_vector_index_metadata(bucket_name, index_name)
            return True
        except VectorStorageError as e:
            if e.error_code == "INDEX_NOT_FOUND":
                return False
            raise
    
    def _validate_vector_data(self, vectors_data: List[Dict[str, Any]]) -> None:
        """Validate vector data before storage."""
        if not vectors_data:
            raise ValidationError(
                "Vector data cannot be empty",
                error_code="EMPTY_VECTOR_DATA"
            )
        
        if len(vectors_data) > 500:
            raise ValidationError(
                f"Cannot store more than 500 vectors in a single request, got {len(vectors_data)}",
                error_code="TOO_MANY_VECTORS",
                error_details={"vector_count": len(vectors_data)}
            )
        
        for i, vector in enumerate(vectors_data):
            if not isinstance(vector, dict):
                raise ValidationError(
                    f"Vector at index {i} must be a dictionary",
                    error_code="INVALID_VECTOR_TYPE",
                    error_details={"index": i, "type": type(vector).__name__}
                )
            
            # Validate required fields
            if 'key' not in vector:
                raise ValidationError(
                    f"Vector at index {i} missing required 'key' field",
                    error_code="MISSING_VECTOR_KEY",
                    error_details={"index": i}
                )
            
            if 'data' not in vector:
                raise ValidationError(
                    f"Vector at index {i} missing required 'data' field",
                    error_code="MISSING_VECTOR_DATA",
                    error_details={"index": i}
                )
            
            # Validate key
            key = vector['key']
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(
                    f"Vector key at index {i} must be a non-empty string",
                    error_code="INVALID_VECTOR_KEY",
                    error_details={"index": i, "key": key}
                )
            
            # Validate vector data
            vector_data = vector['data']
            if not isinstance(vector_data, list):
                raise ValidationError(
                    f"Vector data at index {i} must be a list of floats",
                    error_code="INVALID_VECTOR_DATA_TYPE",
                    error_details={"index": i, "type": type(vector_data).__name__}
                )
            
            # Validate vector dimensions and values
            for j, value in enumerate(vector_data):
                if not isinstance(value, (int, float)):
                    raise ValidationError(
                        f"Vector data at index {i}, dimension {j} must be a number",
                        error_code="INVALID_VECTOR_VALUE_TYPE",
                        error_details={"vector_index": i, "dimension": j, "value": value}
                    )
            
            # Validate metadata if present
            if 'metadata' in vector:
                metadata = vector['metadata']
                if metadata is not None and not isinstance(metadata, dict):
                    raise ValidationError(
                        f"Vector metadata at index {i} must be a dictionary or None",
                        error_code="INVALID_METADATA_TYPE",
                        error_details={"index": i, "type": type(metadata).__name__}
                    )
    
    def put_vectors(self,
                   index_arn: str,
                   vectors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store vectors in a vector index with batch support and metadata attachment.
        
        Args:
            index_arn: ARN of the vector index
            vectors_data: List of vector dictionaries with keys: 'key', 'data', 'metadata' (optional)
                         Each vector data should be a list of float32 values
        
        Returns:
            Dict containing storage response and metadata
        
        Raises:
            ValidationError: If vector data is invalid
            VectorStorageError: If storage operation fails
        """
        logger.info(f"Storing {len(vectors_data)} vectors in index: {index_arn}")
        
        # Validate inputs
        if not index_arn or not isinstance(index_arn, str):
            raise ValidationError(
                "Index ARN must be a non-empty string",
                error_code="INVALID_INDEX_ARN",
                error_details={"index_arn": index_arn}
            )
        
        self._validate_vector_data(vectors_data)
        
        # Convert vector data to float32 format as required by S3 Vectors
        formatted_vectors = []
        for vector in vectors_data:
            formatted_vector = {
                'key': vector['key'],
                'data': [float(x) for x in vector['data']]  # Ensure float32 conversion
            }
            
            # Add metadata if present
            if 'metadata' in vector and vector['metadata'] is not None:
                formatted_vector['metadata'] = vector['metadata']
            
            formatted_vectors.append(formatted_vector)
        
        def _put_vectors():
            return self.s3vectors_client.put_vectors(
                indexArn=index_arn,
                vectors=formatted_vectors
            )
        
        try:
            response = self._retry_with_backoff(_put_vectors)
            
            logger.info(f"Successfully stored {len(vectors_data)} vectors in index: {index_arn}")
            
            return {
                "index_arn": index_arn,
                "vectors_stored": len(vectors_data),
                "status": "success",
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotFoundException':
                raise VectorStorageError(
                    f"Vector index not found: {error_message}",
                    error_code="INDEX_NOT_FOUND",
                    error_details={"index_arn": index_arn}
                )
            elif error_code == 'AccessDeniedException':
                raise VectorStorageError(
                    f"Access denied when storing vectors: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "index_arn": index_arn,
                        "required_permission": "s3vectors:PutVectors"
                    }
                )
            elif error_code == 'ServiceUnavailableException':
                raise VectorStorageError(
                    f"Service unavailable when storing vectors: {error_message}",
                    error_code="SERVICE_UNAVAILABLE",
                    error_details={
                        "index_arn": index_arn,
                        "vector_count": len(vectors_data)
                    }
                )
            elif error_code == 'ValidationException':
                raise VectorStorageError(
                    f"Vector data validation failed: {error_message}",
                    error_code="VECTOR_VALIDATION_FAILED",
                    error_details={
                        "index_arn": index_arn,
                        "aws_error_message": error_message
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to store vectors: {error_message}",
                    error_code=error_code,
                    error_details={
                        "index_arn": index_arn,
                        "vector_count": len(vectors_data),
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error storing vectors: {e}")
            raise VectorStorageError(
                f"Unexpected error storing vectors: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "index_arn": index_arn,
                    "vector_count": len(vectors_data),
                    "error": str(e)
                }
            )
    
    def query_vectors(self,
                     index_arn: str,
                     query_vector: List[float],
                     top_k: int = 10,
                     metadata_filter: Optional[Dict[str, Any]] = None,
                     return_distance: bool = True,
                     return_metadata: bool = True) -> Dict[str, Any]:
        """
        Perform similarity search with filtering capabilities.
        
        Args:
            index_arn: ARN of the vector index to query
            query_vector: Query vector as list of floats
            top_k: Number of nearest neighbors to return (1-1000)
            metadata_filter: Optional metadata filter for search results
            return_distance: Whether to include similarity distances in results
            return_metadata: Whether to include metadata in results
        
        Returns:
            Dict containing search results with vectors, distances, and metadata
        
        Raises:
            ValidationError: If query parameters are invalid
            VectorStorageError: If query operation fails
        """
        logger.info(f"Querying vectors in index: {index_arn} with top_k={top_k}")
        
        # Validate inputs
        if not index_arn or not isinstance(index_arn, str):
            raise ValidationError(
                "Index ARN must be a non-empty string",
                error_code="INVALID_INDEX_ARN",
                error_details={"index_arn": index_arn}
            )
        
        if not isinstance(query_vector, list) or not query_vector:
            raise ValidationError(
                "Query vector must be a non-empty list of numbers",
                error_code="INVALID_QUERY_VECTOR",
                error_details={"query_vector_type": type(query_vector).__name__}
            )
        
        # Validate query vector values
        for i, value in enumerate(query_vector):
            if not isinstance(value, (int, float)):
                raise ValidationError(
                    f"Query vector value at dimension {i} must be a number",
                    error_code="INVALID_QUERY_VECTOR_VALUE",
                    error_details={"dimension": i, "value": value}
                )
        
        if not isinstance(top_k, int) or top_k < 1 or top_k > 1000:
            raise ValidationError(
                f"top_k must be an integer between 1 and 1000, got {top_k}",
                error_code="INVALID_TOP_K",
                error_details={"top_k": top_k}
            )
        
        if metadata_filter is not None and not isinstance(metadata_filter, dict):
            raise ValidationError(
                "Metadata filter must be a dictionary or None",
                error_code="INVALID_METADATA_FILTER",
                error_details={"filter_type": type(metadata_filter).__name__}
            )
        
        # Prepare request parameters
        request_params = {
            'indexArn': index_arn,
            'queryVector': [float(x) for x in query_vector],  # Ensure float32 conversion
            'topK': top_k,
            'returnDistance': return_distance,
            'returnMetadata': return_metadata
        }
        
        if metadata_filter:
            request_params['filter'] = metadata_filter
        
        def _query_vectors():
            return self.s3vectors_client.query_vectors(**request_params)
        
        try:
            response = self._retry_with_backoff(_query_vectors)
            
            vectors = response.get('vectors', [])
            
            logger.info(f"Successfully queried vectors, found {len(vectors)} results")
            
            return {
                "index_arn": index_arn,
                "query_vector_dimensions": len(query_vector),
                "top_k": top_k,
                "results_count": len(vectors),
                "vectors": vectors,
                "metadata_filter": metadata_filter,
                "return_distance": return_distance,
                "return_metadata": return_metadata,
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotFoundException':
                raise VectorStorageError(
                    f"Vector index not found: {error_message}",
                    error_code="INDEX_NOT_FOUND",
                    error_details={"index_arn": index_arn}
                )
            elif error_code == 'AccessDeniedException':
                required_permissions = ["s3vectors:QueryVectors"]
                if return_metadata or metadata_filter:
                    required_permissions.append("s3vectors:GetVectors")
                
                raise VectorStorageError(
                    f"Access denied when querying vectors: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "index_arn": index_arn,
                        "required_permissions": required_permissions
                    }
                )
            elif error_code == 'ValidationException':
                raise VectorStorageError(
                    f"Query validation failed: {error_message}",
                    error_code="QUERY_VALIDATION_FAILED",
                    error_details={
                        "index_arn": index_arn,
                        "aws_error_message": error_message
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to query vectors: {error_message}",
                    error_code=error_code,
                    error_details={
                        "index_arn": index_arn,
                        "top_k": top_k,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error querying vectors: {e}")
            raise VectorStorageError(
                f"Unexpected error querying vectors: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "index_arn": index_arn,
                    "top_k": top_k,
                    "error": str(e)
                }
            )
    
    def list_vectors(self,
                    index_arn: str,
                    max_results: Optional[int] = None,
                    next_token: Optional[str] = None,
                    return_data: bool = False,
                    return_metadata: bool = True,
                    segment_count: Optional[int] = None,
                    segment_index: Optional[int] = None) -> Dict[str, Any]:
        """
        List vectors with pagination support.
        
        Args:
            index_arn: ARN of the vector index
            max_results: Maximum number of vectors to return (1-1000, default 500)
            next_token: Token for pagination from previous request
            return_data: Whether to include vector data in response
            return_metadata: Whether to include metadata in response
            segment_count: Number of segments for parallel listing (1-16)
            segment_index: Index of segment to list (0-15, must be < segment_count)
        
        Returns:
            Dict containing list of vectors and pagination info
        
        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If operation fails
        """
        logger.info(f"Listing vectors in index: {index_arn}")
        
        # Validate inputs
        if not index_arn or not isinstance(index_arn, str):
            raise ValidationError(
                "Index ARN must be a non-empty string",
                error_code="INVALID_INDEX_ARN",
                error_details={"index_arn": index_arn}
            )
        
        if max_results is not None:
            if not isinstance(max_results, int) or max_results < 1 or max_results > 1000:
                raise ValidationError(
                    f"max_results must be an integer between 1 and 1000, got {max_results}",
                    error_code="INVALID_MAX_RESULTS",
                    error_details={"max_results": max_results}
                )
        
        if next_token is not None:
            if not isinstance(next_token, str) or len(next_token) < 1 or len(next_token) > 2048:
                raise ValidationError(
                    f"next_token must be a string between 1 and 2048 characters",
                    error_code="INVALID_NEXT_TOKEN",
                    error_details={"next_token": next_token}
                )
        
        if segment_count is not None:
            if not isinstance(segment_count, int) or segment_count < 1 or segment_count > 16:
                raise ValidationError(
                    f"segment_count must be an integer between 1 and 16, got {segment_count}",
                    error_code="INVALID_SEGMENT_COUNT",
                    error_details={"segment_count": segment_count}
                )
        
        if segment_index is not None:
            if not isinstance(segment_index, int) or segment_index < 0 or segment_index > 15:
                raise ValidationError(
                    f"segment_index must be an integer between 0 and 15, got {segment_index}",
                    error_code="INVALID_SEGMENT_INDEX",
                    error_details={"segment_index": segment_index}
                )
            
            if segment_count is None:
                raise ValidationError(
                    "segment_count is required when segment_index is specified",
                    error_code="MISSING_SEGMENT_COUNT"
                )
            
            if segment_index >= segment_count:
                raise ValidationError(
                    f"segment_index ({segment_index}) must be less than segment_count ({segment_count})",
                    error_code="INVALID_SEGMENT_RELATIONSHIP",
                    error_details={"segment_index": segment_index, "segment_count": segment_count}
                )
        
        if segment_count is not None and segment_index is None:
            raise ValidationError(
                "segment_index is required when segment_count is specified",
                error_code="MISSING_SEGMENT_INDEX"
            )
        
        # Prepare request parameters
        request_params = {
            'indexArn': index_arn,
            'returnData': return_data,
            'returnMetadata': return_metadata
        }
        
        if max_results is not None:
            request_params['maxResults'] = max_results
        if next_token is not None:
            request_params['nextToken'] = next_token
        if segment_count is not None:
            request_params['segmentCount'] = segment_count
        if segment_index is not None:
            request_params['segmentIndex'] = segment_index
        
        def _list_vectors():
            return self.s3vectors_client.list_vectors(**request_params)
        
        try:
            response = self._retry_with_backoff(_list_vectors)
            
            vectors = response.get('vectors', [])
            next_token = response.get('nextToken')
            
            logger.info(f"Successfully listed {len(vectors)} vectors from index: {index_arn}")
            
            return {
                "index_arn": index_arn,
                "vectors": vectors,
                "next_token": next_token,
                "count": len(vectors),
                "return_data": return_data,
                "return_metadata": return_metadata,
                "segment_count": segment_count,
                "segment_index": segment_index,
                "response": response
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'NotFoundException':
                raise VectorStorageError(
                    f"Vector index not found: {error_message}",
                    error_code="INDEX_NOT_FOUND",
                    error_details={"index_arn": index_arn}
                )
            elif error_code == 'AccessDeniedException':
                required_permissions = ["s3vectors:ListVectors"]
                if return_data or return_metadata:
                    required_permissions.append("s3vectors:GetVectors")
                
                raise VectorStorageError(
                    f"Access denied when listing vectors: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "index_arn": index_arn,
                        "required_permissions": required_permissions
                    }
                )
            elif error_code == 'ValidationException':
                raise VectorStorageError(
                    f"List vectors validation failed: {error_message}",
                    error_code="LIST_VALIDATION_FAILED",
                    error_details={
                        "index_arn": index_arn,
                        "aws_error_message": error_message
                    }
                )
            else:
                raise VectorStorageError(
                    f"Failed to list vectors: {error_message}",
                    error_code=error_code,
                    error_details={
                        "index_arn": index_arn,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        
        except Exception as e:
            logger.error(f"Unexpected error listing vectors: {e}")
            raise VectorStorageError(
                f"Unexpected error listing vectors: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "index_arn": index_arn,
                    "error": str(e)
                }
            )