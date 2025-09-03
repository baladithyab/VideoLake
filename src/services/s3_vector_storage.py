"""
S3 Vector Storage Manager for managing vector buckets and operations.

This module provides functionality for creating and managing S3 vector buckets,
with proper IAM permissions, validation, and error handling.
"""

import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, Any, Optional, List, Set
import numpy as np
from botocore.exceptions import ClientError, BotoCoreError
import logging

from src.utils.aws_clients import aws_client_factory
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)

def _normalize_encryption_type(value: Optional[str]) -> Optional[str]:
    """
    Map friendly encryption types to AWS API values:
      - "SSE-S3" -> "AES256"
      - "SSE-KMS" -> "aws:kms"
    Accept already-correct forms ("AES256", "aws:kms") and return as-is.
    """
    if value is None:
        return None
    v = str(value).strip()
    if v.lower() in ("sse-s3", "aes256"):
        return "AES256"
    if v.lower() in ("sse-kms", "aws:kms", "aws:kms"):
        return "aws:kms"
    return v

def _to_vectors_resource_id(bucket: str, index: str) -> str:
    """Return S3 Vectors resource-id format expected by certain API params."""
    return f"bucket/{bucket}/index/{index}"


def _to_resource_id(bucket: str, index: str) -> str:
    """
    Minimal helper for callers to generate a normalized resource-id for an index.
    This is intentionally identical to _to_vectors_resource_id but exposed for external use.
    """
    return f"bucket/{bucket}/index/{index}"


class S3VectorStorageManager:
    """Manages S3 vector bucket operations with multi-index support and proper error handling."""
    
    def __init__(self):
        self.s3vectors_client = aws_client_factory.get_s3vectors_client()
        self.s3_client = aws_client_factory.get_s3_client()
        
        # Multi-index coordination
        self.index_registry: Dict[str, Dict[str, Any]] = {}
        self._registry_lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Vector type management
        self.vector_type_configs = {
            "visual-text": {"dimensions": 1024, "default_metric": "cosine"},
            "visual-image": {"dimensions": 1024, "default_metric": "cosine"},
            "audio": {"dimensions": 1024, "default_metric": "cosine"},
            "text-titan": {"dimensions": 1536, "default_metric": "cosine"}
        }
    
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

    def _parse_index_identifier(self, identifier: str) -> Dict[str, str]:
        """
        Accept either:
          - ARN starting with 'arn:' -> {'indexArn': identifier}
          - Resource-id 'bucket/<bucket>/index/<index>' -> {'vectorBucketName': bucket, 'indexName': index}
        """
        if not identifier or not isinstance(identifier, str):
            raise ValidationError(
                "Index identifier must be a non-empty string",
                error_code="INVALID_INDEX_IDENTIFIER",
                error_details={"identifier": identifier}
            )
        if identifier.startswith("arn:"):
            return {"indexArn": identifier}
        # resource-id pattern
        if identifier.startswith("bucket/"):
            try:
                parts = identifier.split("/")
                # Expect ['bucket', '<bucket>', 'index', '<index>']
                if len(parts) >= 4 and parts[0] == "bucket" and parts[2] == "index":
                    return {"vectorBucketName": parts[1], "indexName": parts[3]}
            except Exception:
                pass
        # Fallback: treat as invalid
        raise ValidationError(
            "Index identifier must be an ARN or 'bucket/<bucket>/index/<index>'",
            error_code="INVALID_INDEX_IDENTIFIER",
            error_details={"identifier": identifier}
        )
    
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
        
        # Validate and normalize encryption configuration
        norm_enc = _normalize_encryption_type(encryption_type)
        if norm_enc not in ["AES256", "aws:kms"]:
            raise ValidationError(
                f"Invalid encryption type: {encryption_type}. Must be 'SSE-S3'/'AES256' or 'SSE-KMS'/'aws:kms'",
                error_code="INVALID_ENCRYPTION_TYPE",
                error_details={"encryption_type": encryption_type}
            )

        if norm_enc == "aws:kms" and not kms_key_arn:
            raise ValidationError(
                "KMS key ARN is required when using SSE-KMS encryption",
                error_code="MISSING_KMS_KEY_ARN"
            )

        # Prepare request parameters
        request_params = {
            "vectorBucketName": bucket_name
        }

        # Add encryption configuration if specified
        if norm_enc:
            enc_cfg = {"sseType": norm_enc}
            if norm_enc == "aws:kms" and kms_key_arn:
                enc_cfg["kmsKeyArn"] = kms_key_arn
            request_params["encryptionConfiguration"] = enc_cfg
        
        def _create_bucket():
            return self.s3vectors_client.create_vector_bucket(**request_params)
        
        try:
            response = self._retry_with_backoff(_create_bucket)
            
            logger.info(f"Successfully created vector bucket: {bucket_name}")
            # Log to local resource registry (best-effort)
            try:
                from src.config import config_manager as _cfg
                resource_registry.log_vector_bucket_created(
                    bucket_name=bucket_name,
                    region=_cfg.aws_config.region,
                    encryption=encryption_type,
                    kms_key_arn=kms_key_arn,
                    source="service",
                )
            except Exception:
                pass

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
            # Normalize: ensure vectorBucketName present at top level for tests
            if isinstance(response, dict) and 'vectorBucketName' not in response:
                response = dict(response)
                response['vectorBucketName'] = bucket_name
            return response
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code in ['NoSuchBucket', 'NotFoundException']:
                raise VectorStorageError(
                    f"Vector bucket {bucket_name} does not exist",
                    error_code="BUCKET_NOT_FOUND",
                    error_details={"bucket_name": bucket_name, "aws_error_code": error_code}
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
            # Log to registry (best-effort)
            try:
                from src.config import config_manager as _cfg
                import boto3 as _b3
                region = _cfg.aws_config.region
                sts = _b3.client('sts', region_name=region)
                account_id = sts.get_caller_identity()['Account']
                index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}"
                resource_registry.log_index_created(
                    bucket_name=bucket_name,
                    index_name=index_name,
                    arn=index_arn,
                    dimensions=dimensions,
                    distance_metric=distance_metric,
                    source="service",
                )
            except Exception:
                pass

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
            logger.info(f"Deleting vector index by identifier: {index_arn}")
        else:
            if not bucket_name or not index_name:
                raise ValidationError(
                    "Must specify either index_arn (ARN or resource-id) or both bucket_name and index_name",
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
            # If an ARN or resource-id is provided, parse it to extract bucket and index names
            try:
                parsed_id = self._parse_index_identifier(index_arn)
                if "vectorBucketName" in parsed_id and "indexName" in parsed_id:
                    request_params["vectorBucketName"] = parsed_id["vectorBucketName"]
                    request_params["indexName"] = parsed_id["indexName"]
                elif "indexArn" in parsed_id:
                    request_params["indexArn"] = parsed_id["indexArn"]
                else:
                    # Fallback for unexpected parsing result
                    raise ValidationError(f"Could not determine parameters from identifier: {index_arn}", error_code="INVALID_IDENTIFIER_PARSE")
            except ValidationError:
                 # Re-raise validation errors from parser
                 raise
            except Exception as e:
                # Catch other potential errors during parsing
                raise VectorStorageError(f"Failed to parse index identifier '{index_arn}': {e}", error_code="IDENTIFIER_PARSE_FAILED") from e
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
            # Log deletion in registry (best-effort)
            try:
                resource_registry.log_index_deleted(index_arn=index_arn, bucket_name=bucket_name, index_name=index_name, source="service")
            except Exception:
                pass

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
                # Log deletion intent in registry (best-effort)
                try:
                    resource_registry.log_index_deleted(index_arn=index_arn, bucket_name=bucket_name, index_name=index_name, source="service")
                except Exception:
                    pass
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
     
    def delete_index_with_retries(self, bucket: str, index: str, max_attempts: int = 6, backoff_base: float = 1.0) -> bool:
        """
        Delete index using resource-id normalization with retries for eventual consistency.
        Retries on NotFoundException and ConflictException as these can flap during propagation.
        Returns True if the index is deleted or confirmed NotFound by the end.
        """
        identifier = _to_resource_id(bucket, index)
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                logger.info(f"[cleanup] Deleting index (attempt {attempt}/{max_attempts}): {identifier}")
                self.delete_vector_index(index_arn=identifier)
                # Verify deletion via describe/list
                time.sleep(0.5)
                try:
                    if not self.index_exists(bucket, index):
                        logger.info(f"[cleanup] Verified deletion of {identifier}")
                        return True
                except VectorStorageError as e:
                    if getattr(e, "error_code", None) == "INDEX_NOT_FOUND":
                        logger.info(f"[cleanup] Verified deletion (INDEX_NOT_FOUND) of {identifier}")
                        return True
                # If still exists, fall through to retry
                raise VectorStorageError("Index still exists after delete", error_code="DELETE_NOT_CONSISTENT")
            except VectorStorageError as e:
                code = getattr(e, "error_code", None) or ""
                if code in ("INDEX_NOT_FOUND", "NotFoundException"):
                    if attempt == max_attempts:
                        logger.info(f"[cleanup] Index not found on final attempt; treating as deleted: {identifier}")
                        return True
                    # Backoff and retry in case of inconsistent listing
                elif code in ("ConflictException",):
                    # Retry on conflict
                    pass
                else:
                    # For other errors, log and continue to retry cautiously
                    logger.warning(f"[cleanup] Delete attempt error ({code}): {e}")
                # Exponential backoff
                delay = backoff_base * (2 ** (attempt - 1))
                logger.info(f"[cleanup] Retry in {delay:.1f}s for {identifier}")
                time.sleep(delay)
            except Exception as e:
                # Unknown errors - still retry with backoff
                delay = backoff_base * (2 ** (attempt - 1))
                logger.warning(f"[cleanup] Unexpected error deleting {identifier}: {e}; retrying in {delay:.1f}s")
                time.sleep(delay)
        # Final verification
        try:
            if not self.index_exists(bucket, index):
                logger.info(f"[cleanup] Post-retry verification shows index absent: {identifier}")
                return True
        except VectorStorageError as e:
            if getattr(e, "error_code", None) == "INDEX_NOT_FOUND":
                logger.info(f"[cleanup] Post-retry verification INDEX_NOT_FOUND for {identifier}")
                return True
        logger.warning(f"[cleanup] Unable to confirm deletion of {identifier} after {max_attempts} attempts")
        return False
     
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
            
            # Validate vector data (AWS S3 Vectors format)
            vector_data = vector['data']
            if not isinstance(vector_data, dict):
                raise ValidationError(
                    f"Vector data at index {i} must be a dictionary with VectorData format",
                    error_code="INVALID_VECTOR_DATA_TYPE",
                    error_details={"index": i, "type": type(vector_data).__name__}
                )
            
            # Check for float32 field (union type)
            if 'float32' not in vector_data:
                raise ValidationError(
                    f"Vector data at index {i} must contain 'float32' field",
                    error_code="MISSING_FLOAT32_DATA",
                    error_details={"index": i, "available_fields": list(vector_data.keys())}
                )
            
            float32_data = vector_data['float32']
            if not isinstance(float32_data, list):
                raise ValidationError(
                    f"Vector float32 data at index {i} must be a list of floats",
                    error_code="INVALID_FLOAT32_DATA_TYPE",
                    error_details={"index": i, "type": type(float32_data).__name__}
                )
            
            # Validate vector dimensions and values with NumPy
            try:
                np_vector = np.array(float32_data, dtype=np.float32)
                
                if not np.issubdtype(np_vector.dtype, np.number):
                    raise ValidationError(
                        f"Vector float32 data at index {i} must contain only numbers",
                        error_code="INVALID_VECTOR_VALUE_TYPE",
                        error_details={"vector_index": i}
                    )
                
                if not np.isfinite(np_vector).all():
                    raise ValidationError(
                        f"Vector float32 data at index {i} contains invalid values (NaN or Infinity)",
                        error_code="INVALID_VECTOR_VALUE",
                        error_details={"vector_index": i}
                    )
            except (ValueError, TypeError) as e:
                raise ValidationError(
                    f"Vector float32 data at index {i} could not be converted to a numeric array: {e}",
                    error_code="INVALID_VECTOR_CONVERSION",
                    error_details={"vector_index": i, "error": str(e)}
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
                         Each 'data' should be a VectorData object: {'float32': [list of float values]}
        
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
                "Index ARN or resource-id must be a non-empty string",
                error_code="INVALID_INDEX_IDENTIFIER",
                error_details={"index_arn": index_arn}
            )
        
        self._validate_vector_data(vectors_data)
        
        # Convert vector data to AWS S3 Vectors format
        formatted_vectors = []
        for vector in vectors_data:
            # Extract float32 data from the VectorData union type
            float32_data = vector['data']['float32']
            
            formatted_vector = {
                'key': vector['key'],
                'data': {
                    'float32': np.array(float32_data, dtype=np.float32).tolist()
                }
            }
            
            # Add metadata if present
            if 'metadata' in vector and vector['metadata'] is not None:
                formatted_vector['metadata'] = vector['metadata']
            
            formatted_vectors.append(formatted_vector)
        
        def _put_vectors():
            # Accept ARN or resource-id; map to supported params
            mapped = self._parse_index_identifier(index_arn)
            return self.s3vectors_client.put_vectors(
                **mapped,
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
                "Index ARN or resource-id must be a non-empty string",
                error_code="INVALID_INDEX_IDENTIFIER",
                error_details={"index_arn": index_arn}
            )
        
        if not isinstance(query_vector, list) or not query_vector:
            raise ValidationError(
                "Query vector must be a non-empty list of numbers",
                error_code="INVALID_QUERY_VECTOR",
                error_details={"query_vector_type": type(query_vector).__name__}
            )
        
        # Validate query vector values
        try:
            np_query_vector = np.array(query_vector, dtype=np.float32)
            if not np.isfinite(np_query_vector).all():
                raise ValidationError(
                    "Query vector contains invalid values (NaN or Infinity)",
                    error_code="INVALID_QUERY_VECTOR_VALUE"
                )
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Query vector could not be converted to a numeric array: {e}",
                error_code="INVALID_QUERY_VECTOR_CONVERSION",
                error_details={"error": str(e)}
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
            'queryVector': np.array(query_vector, dtype=np.float32).tolist(),
            'topK': top_k,
            'returnDistance': return_distance,
            'returnMetadata': return_metadata
        }
        
        if metadata_filter:
            request_params['filter'] = metadata_filter
        
        def _query_vectors():
            # Map identifier to supported params
            mapped = self._parse_index_identifier(index_arn)
            req = dict(request_params)
            # Coerce queryVector to union type dict expected by API if it's a list
            qv = req.get('queryVector')
            if isinstance(qv, list):
                req['queryVector'] = {'float32': [float(x) for x in qv]}
            # Replace placeholder 'indexArn' with mapped keys
            req.pop('indexArn', None)
            req.update(mapped)
            return self.s3vectors_client.query_vectors(**req)
        
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
                "Index ARN or resource-id must be a non-empty string",
                error_code="INVALID_INDEX_IDENTIFIER",
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
            mapped = self._parse_index_identifier(index_arn)
            req = dict(request_params)
            req.pop('indexArn')
            req.update(mapped)
            return self.s3vectors_client.list_vectors(**req)
        
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
  
    def put_vectors_batch(self, index_arn: str, vectors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Alias for put_vectors method to match integration service expectations.
        
        Args:
            index_arn: ARN of the vector index
            vectors_data: List of vector data dictionaries
            
        Returns:
            Dictionary containing the storage response
        """
        return self.put_vectors(index_arn, vectors_data)
    
    def query_similar_vectors(self,
                            index_arn: str,
                            query_vector: List[float],
                            top_k: int = 10,
                            metadata_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Alias for query_vectors method to match integration service expectations.
        
        Args:
            index_arn: ARN of the vector index
            query_vector: Query vector for similarity search
            top_k: Number of similar results to return
            metadata_filters: Optional metadata filters
            
        Returns:
            Dictionary containing the query results
        """
        return self.query_vectors(index_arn, query_vector, top_k, metadata_filters)

    def create_multi_index_architecture(self,
                                       bucket_name: str,
                                       vector_types: List[str],
                                       base_dimensions: int = 1024,
                                       distance_metric: str = "cosine") -> Dict[str, Any]:
        """
        Create multiple vector indexes for different vector types in a coordinated architecture.
        
        Args:
            bucket_name: Base bucket name
            vector_types: List of vector types to create indexes for
            base_dimensions: Default dimensions (can be overridden by vector type config)
            distance_metric: Distance metric for all indexes
            
        Returns:
            Dictionary with creation results for all indexes
        """
        logger.info(f"Creating multi-index architecture: bucket={bucket_name}, types={vector_types}")
        
        # Create the main bucket first
        bucket_result = self.create_vector_bucket(bucket_name)
        
        # Create indexes concurrently
        index_tasks = []
        with ThreadPoolExecutor(max_workers=len(vector_types)) as executor:
            for vector_type in vector_types:
                # Get dimensions from config or use default
                dimensions = self.vector_type_configs.get(vector_type, {}).get("dimensions", base_dimensions)
                index_name = f"{vector_type}-index"
                
                future = executor.submit(
                    self._create_single_index_safe,
                    bucket_name, index_name, dimensions, distance_metric, vector_type
                )
                index_tasks.append((vector_type, future))
        
        # Collect results
        index_results = {}
        failed_indexes = []
        
        for vector_type, future in index_tasks:
            try:
                result = future.result()
                index_results[vector_type] = result
                
                # Register the index
                index_arn = result.get('response', {}).get('indexArn')
                if index_arn:
                    self.register_vector_index(index_arn, vector_type, dimensions, distance_metric)
                    
            except Exception as e:
                logger.error(f"Failed to create index for {vector_type}: {e}")
                failed_indexes.append({'vector_type': vector_type, 'error': str(e)})
        
        logger.info(f"Multi-index architecture creation completed: {len(index_results)} successful, {len(failed_indexes)} failed")
        
        return {
            'bucket_result': bucket_result,
            'index_results': index_results,
            'failed_indexes': failed_indexes,
            'architecture_type': 'multi-vector',
            'total_indexes': len(vector_types),
            'successful_indexes': len(index_results),
            'failed_indexes': len(failed_indexes)
        }

    def _create_single_index_safe(self, bucket_name: str, index_name: str, 
                                dimensions: int, distance_metric: str, vector_type: str) -> Dict[str, Any]:
        """Create a single index with error handling."""
        try:
            return self.create_vector_index(
                bucket_name=bucket_name,
                index_name=index_name,
                dimensions=dimensions,
                distance_metric=distance_metric
            )
        except Exception as e:
            logger.error(f"Error creating index {index_name} for vector type {vector_type}: {e}")
            raise

    def register_vector_index(self, index_arn: str, vector_type: str, 
                            dimensions: int, distance_metric: str, 
                            metadata: Dict[str, Any] = None) -> None:
        """Register a vector index in the coordination registry."""
        with self._registry_lock:
            self.index_registry[index_arn] = {
                'vector_type': vector_type,
                'dimensions': dimensions,
                'distance_metric': distance_metric,
                'metadata': metadata or {},
                'created_at': time.time(),
                'bucket_name': self._extract_bucket_from_arn(index_arn),
                'index_name': self._extract_index_from_arn(index_arn)
            }
        logger.debug(f"Registered vector index: {index_arn} for type {vector_type}")

    def _extract_bucket_from_arn(self, index_arn: str) -> Optional[str]:
        """Extract bucket name from index ARN."""
        try:
            if index_arn.startswith('arn:aws:s3vectors:'):
                parts = index_arn.split(':')
                if len(parts) >= 6:
                    resource_part = parts[5]  # bucket/name/index/name
                    if resource_part.startswith('bucket/'):
                        return resource_part.split('/')[1]
            return None
        except Exception:
            return None

    def _extract_index_from_arn(self, index_arn: str) -> Optional[str]:
        """Extract index name from index ARN."""
        try:
            if index_arn.startswith('arn:aws:s3vectors:'):
                parts = index_arn.split(':')
                if len(parts) >= 6:
                    resource_part = parts[5]  # bucket/name/index/name
                    resource_parts = resource_part.split('/')
                    if len(resource_parts) >= 4 and resource_parts[2] == 'index':
                        return resource_parts[3]
            return None
        except Exception:
            return None

    def put_vectors_multi_index(self,
                              vectors_by_type: Dict[str, List[Dict[str, Any]]],
                              bucket_name: str = None,
                              index_arns: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Store vectors across multiple indexes by vector type concurrently.
        
        Args:
            vectors_by_type: Dictionary mapping vector types to vector data lists
            bucket_name: Bucket name (if using type-based index lookup)
            index_arns: Dictionary mapping vector types to index ARNs
            
        Returns:
            Dictionary with storage results by vector type
        """
        logger.info(f"Storing vectors across {len(vectors_by_type)} vector types")
        
        # Resolve index ARNs
        resolved_arns = self._resolve_index_arns(vectors_by_type.keys(), bucket_name, index_arns)
        
        # Store vectors concurrently
        storage_tasks = []
        with ThreadPoolExecutor(max_workers=len(vectors_by_type)) as executor:
            for vector_type, vectors in vectors_by_type.items():
                if vector_type not in resolved_arns:
                    logger.error(f"No index ARN resolved for vector type: {vector_type}")
                    continue
                
                index_arn = resolved_arns[vector_type]
                future = executor.submit(self._put_vectors_safe, index_arn, vectors, vector_type)
                storage_tasks.append((vector_type, future))
        
        # Collect results
        results = {}
        failed_types = []
        total_vectors = 0
        
        for vector_type, future in storage_tasks:
            try:
                result = future.result()
                results[vector_type] = result
                total_vectors += result.get('vectors_stored', 0)
            except Exception as e:
                logger.error(f"Failed to store vectors for type {vector_type}: {e}")
                failed_types.append({'vector_type': vector_type, 'error': str(e)})
        
        logger.info(f"Multi-index vector storage completed: {total_vectors} total vectors stored")
        
        return {
            'results_by_type': results,
            'failed_types': failed_types,
            'total_vector_types': len(vectors_by_type),
            'successful_types': len(results),
            'failed_types_count': len(failed_types),
            'total_vectors_stored': total_vectors
        }

    def _resolve_index_arns(self, vector_types: Set[str], bucket_name: str = None, 
                          index_arns: Dict[str, str] = None) -> Dict[str, str]:
        """Resolve index ARNs for vector types."""
        resolved = {}
        
        if index_arns:
            # Use provided ARNs
            resolved.update(index_arns)
        
        # Fill in missing ARNs from registry or construct from bucket
        for vector_type in vector_types:
            if vector_type not in resolved:
                # Try to find in registry
                with self._registry_lock:
                    for arn, config in self.index_registry.items():
                        if config.get('vector_type') == vector_type:
                            resolved[vector_type] = arn
                            break
                
                # If still not found and bucket provided, construct ARN
                if vector_type not in resolved and bucket_name:
                    index_name = f"{vector_type}-index"
                    try:
                        # Get account info for ARN construction
                        import boto3
                        sts = boto3.client('sts')
                        account_id = sts.get_caller_identity()['Account']
                        region = self.s3vectors_client._client_config.region_name
                        
                        arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}"
                        resolved[vector_type] = arn
                    except Exception as e:
                        logger.warning(f"Could not construct ARN for {vector_type}: {e}")
        
        return resolved

    def _put_vectors_safe(self, index_arn: str, vectors: List[Dict[str, Any]], 
                        vector_type: str) -> Dict[str, Any]:
        """Store vectors in a single index with error handling."""
        try:
            result = self.put_vectors(index_arn, vectors)
            result['vector_type'] = vector_type
            return result
        except Exception as e:
            logger.error(f"Error storing vectors for type {vector_type}: {e}")
            raise

    def query_vectors_multi_index(self,
                                query_vectors: Dict[str, List[float]],
                                bucket_name: str = None,
                                index_arns: Dict[str, str] = None,
                                top_k: int = 10,
                                fusion_method: str = "weighted_average") -> Dict[str, Any]:
        """
        Query multiple indexes with different vector types and fuse results.
        
        Args:
            query_vectors: Dictionary mapping vector types to query vectors
            bucket_name: Bucket name for ARN resolution
            index_arns: Specific index ARNs by vector type
            top_k: Number of results per index
            fusion_method: Method for combining results
            
        Returns:
            Dictionary with fused query results
        """
        logger.info(f"Querying {len(query_vectors)} vector types across multiple indexes")
        
        # Resolve index ARNs
        resolved_arns = self._resolve_index_arns(query_vectors.keys(), bucket_name, index_arns)
        
        # Query indexes concurrently
        query_tasks = []
        with ThreadPoolExecutor(max_workers=len(query_vectors)) as executor:
            for vector_type, query_vector in query_vectors.items():
                if vector_type not in resolved_arns:
                    continue
                
                index_arn = resolved_arns[vector_type]
                future = executor.submit(
                    self._query_vectors_safe, 
                    index_arn, query_vector, top_k * 2, vector_type  # Get more for fusion
                )
                query_tasks.append((vector_type, future))
        
        # Collect results
        results_by_type = {}
        failed_types = []
        
        for vector_type, future in query_tasks:
            try:
                result = future.result()
                results_by_type[vector_type] = result
            except Exception as e:
                logger.error(f"Failed to query vectors for type {vector_type}: {e}")
                failed_types.append({'vector_type': vector_type, 'error': str(e)})
        
        # Fuse results using the specified method
        fused_results = self._fuse_query_results(results_by_type, top_k, fusion_method)
        
        return {
            'fused_results': fused_results,
            'results_by_type': results_by_type,
            'failed_types': failed_types,
            'fusion_method': fusion_method,
            'total_results': len(fused_results.get('vectors', []))
        }

    def _query_vectors_safe(self, index_arn: str, query_vector: List[float], 
                          top_k: int, vector_type: str) -> Dict[str, Any]:
        """Query vectors from a single index with error handling."""
        try:
            result = self.query_vectors(index_arn, query_vector, top_k)
            result['vector_type'] = vector_type
            return result
        except Exception as e:
            logger.error(f"Error querying vectors for type {vector_type}: {e}")
            raise

    def _fuse_query_results(self, results_by_type: Dict[str, Dict[str, Any]], 
                          top_k: int, fusion_method: str) -> Dict[str, Any]:
        """Fuse query results from multiple indexes."""
        if not results_by_type:
            return {'vectors': [], 'method': fusion_method}
        
        if fusion_method == "weighted_average":
            return self._fuse_weighted_average_storage(results_by_type, top_k)
        elif fusion_method == "rank_fusion":
            return self._fuse_rank_based_storage(results_by_type, top_k)
        else:
            # Default to concatenation with score normalization
            return self._fuse_concatenate(results_by_type, top_k)

    def _fuse_weighted_average_storage(self, results_by_type: Dict[str, Dict[str, Any]], 
                                     top_k: int) -> Dict[str, Any]:
        """Fuse results using weighted average of scores."""
        combined_vectors = {}
        
        for vector_type, result in results_by_type.items():
            weight = 1.0 / len(results_by_type)  # Equal weights
            for vector in result.get('vectors', []):
                key = vector.get('key', '')
                distance = vector.get('distance', 1.0)
                similarity = 1.0 - distance
                
                if key not in combined_vectors:
                    combined_vectors[key] = {
                        'vector': vector,
                        'weighted_score': 0.0,
                        'weight_sum': 0.0
                    }
                
                combined_vectors[key]['weighted_score'] += similarity * weight
                combined_vectors[key]['weight_sum'] += weight
        
        # Calculate final scores and sort
        final_vectors = []
        for key, data in combined_vectors.items():
            if data['weight_sum'] > 0:
                final_score = data['weighted_score'] / data['weight_sum']
                vector = data['vector'].copy()
                vector['distance'] = 1.0 - final_score
                vector['similarity'] = final_score
                final_vectors.append(vector)
        
        # Sort by similarity (higher is better)
        final_vectors.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        return {
            'vectors': final_vectors[:top_k],
            'method': 'weighted_average',
            'total_combined': len(combined_vectors)
        }

    def _fuse_rank_based_storage(self, results_by_type: Dict[str, Dict[str, Any]], 
                               top_k: int) -> Dict[str, Any]:
        """Fuse results using reciprocal rank fusion."""
        rrf_scores = {}
        
        for vector_type, result in results_by_type.items():
            for rank, vector in enumerate(result.get('vectors', [])):
                key = vector.get('key', '')
                rrf_score = 1.0 / (60 + rank + 1)  # Standard RRF with k=60
                
                if key not in rrf_scores:
                    rrf_scores[key] = {'vector': vector, 'score': 0.0}
                
                rrf_scores[key]['score'] += rrf_score
        
        # Create final result list
        final_vectors = []
        for key, data in rrf_scores.items():
            vector = data['vector'].copy()
            vector['rrf_score'] = data['score']
            vector['distance'] = 1.0 - data['score']  # Convert for consistency
            final_vectors.append(vector)
        
        # Sort by RRF score
        final_vectors.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)
        
        return {
            'vectors': final_vectors[:top_k],
            'method': 'rank_fusion',
            'total_combined': len(rrf_scores)
        }

    def _fuse_concatenate(self, results_by_type: Dict[str, Dict[str, Any]], 
                        top_k: int) -> Dict[str, Any]:
        """Simple concatenation with deduplication."""
        seen_keys = set()
        final_vectors = []
        
        # Collect all vectors, avoiding duplicates
        for vector_type, result in results_by_type.items():
            for vector in result.get('vectors', []):
                key = vector.get('key', '')
                if key not in seen_keys:
                    seen_keys.add(key)
                    vector_copy = vector.copy()
                    vector_copy['source_type'] = vector_type
                    final_vectors.append(vector_copy)
        
        # Sort by distance (lower is better)
        final_vectors.sort(key=lambda x: x.get('distance', 1.0))
        
        return {
            'vectors': final_vectors[:top_k],
            'method': 'concatenate',
            'total_combined': len(final_vectors)
        }

    def get_multi_index_stats(self) -> Dict[str, Any]:
        """Get statistics about registered indexes and multi-index operations."""
        with self._registry_lock:
            registry_copy = dict(self.index_registry)
        
        # Aggregate statistics
        stats = {
            'total_indexes': len(registry_copy),
            'vector_types': {},
            'dimensions_distribution': {},
            'metrics_distribution': {},
            'oldest_index': None,
            'newest_index': None
        }
        
        oldest_time = float('inf')
        newest_time = 0
        
        for arn, config in registry_copy.items():
            vector_type = config.get('vector_type', 'unknown')
            dimensions = config.get('dimensions', 0)
            metric = config.get('distance_metric', 'unknown')
            created_at = config.get('created_at', 0)
            
            # Vector types count
            stats['vector_types'][vector_type] = stats['vector_types'].get(vector_type, 0) + 1
            
            # Dimensions distribution
            dim_key = str(dimensions)
            stats['dimensions_distribution'][dim_key] = stats['dimensions_distribution'].get(dim_key, 0) + 1
            
            # Metrics distribution
            stats['metrics_distribution'][metric] = stats['metrics_distribution'].get(metric, 0) + 1
            
            # Track oldest and newest
            if created_at < oldest_time:
                oldest_time = created_at
                stats['oldest_index'] = {'arn': arn, 'created_at': created_at}
            
            if created_at > newest_time:
                newest_time = created_at
                stats['newest_index'] = {'arn': arn, 'created_at': created_at}
        
        return stats

    def delete_vector_bucket(self, bucket_name: str, cascade: bool = False) -> Dict[str, Any]:
        """
        Delete a vector bucket. If cascade is True, attempt to delete all indexes in the bucket first.

        Behavior:
        - Validates bucket name using existing validation.
        - When cascade is True: lists all indexes and deletes them with retry/backoff.
          Handles NotFound/Conflict during cascade as non-fatal and continues.
        - Calls s3vectors_client.delete_vector_bucket(vectorBucketName=...).
        - On success or NotFound, logs deletion to the resource registry (best-effort).
        - Returns a structured dict consistent with other service methods.

        Returns:
            {
              "bucket_name": str,
              "status": "deleted" | "not_found",
              "indexes_deleted": int,
              "response": dict (when deleted) or omitted,
              "message": str (optional)
            }

        Raises:
            VectorStorageError for access denied or other AWS errors except NotFound.
        """
        logger.info(f"Deleting vector bucket: {bucket_name} (cascade={cascade})")
        # Validate bucket name
        self._validate_bucket_name(bucket_name)

        indexes_deleted = 0

        # Optional cascade: remove indexes first
        if cascade:
            try:
                next_token: Optional[str] = None
                while True:
                    resp = self.list_vector_indexes(bucket_name=bucket_name, max_results=500, next_token=next_token)
                    for idx in (resp.get("indexes") or []):
                        idx_name = idx.get("indexName") or idx.get("name")
                        if not idx_name:
                            continue
                        try:
                            ok = self.delete_index_with_retries(bucket=bucket_name, index=idx_name, max_attempts=6, backoff_base=0.5)
                            if ok:
                                indexes_deleted += 1
                        except VectorStorageError as e:
                            code = getattr(e, "error_code", "") or ""
                            # Treat common flapping states as non-fatal during cascade
                            if code in ("INDEX_NOT_FOUND", "NotFoundException", "ConflictException"):
                                logger.warning(f"Cascade delete non-fatal for index '{idx_name}': {code}")
                            else:
                                logger.warning(f"Error deleting index '{idx_name}' during cascade: {e}")
                    next_token = resp.get("next_token")
                    if not next_token:
                        break
            except VectorStorageError as e:
                # If bucket isn't found during listing, proceed to bucket delete which will return not_found
                if getattr(e, "error_code", "") != "BUCKET_NOT_FOUND":
                    logger.warning(f"Error listing indexes for cascade delete in bucket {bucket_name}: {e}")

        def _del_bucket():
            return self.s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)

        try:
            response = self._retry_with_backoff(_del_bucket)
            logger.info(f"Successfully deleted vector bucket: {bucket_name}")
            # Best-effort registry deletion log
            try:
                resource_registry.log_vector_bucket_deleted(bucket_name=bucket_name, source="service")
            except Exception:
                pass

            return {
                "bucket_name": bucket_name,
                "status": "deleted",
                "indexes_deleted": indexes_deleted,
                "response": response
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code in ("NotFoundException", "NoSuchBucket"):
                logger.warning(f"Vector bucket not found (may already be deleted): {bucket_name}")
                # Best-effort registry deletion log
                try:
                    resource_registry.log_vector_bucket_deleted(bucket_name=bucket_name, source="service")
                except Exception:
                    pass
                return {
                    "bucket_name": bucket_name,
                    "status": "not_found",
                    "indexes_deleted": indexes_deleted,
                    "message": "Bucket not found (may already be deleted)"
                }
            elif error_code == "AccessDeniedException":
                raise VectorStorageError(
                    f"Access denied when deleting vector bucket: {error_message}",
                    error_code="ACCESS_DENIED",
                    error_details={
                        "bucket_name": bucket_name,
                        "required_permission": "s3vectors:DeleteVectorBucket"
                    }
                )
            elif error_code == "ConflictException":
                raise VectorStorageError(
                    f"Conflict when deleting vector bucket (ensure all indexes are deleted): {error_message}",
                    error_code="CONFLICT",
                    error_details={"bucket_name": bucket_name}
                )
            else:
                raise VectorStorageError(
                    f"Failed to delete vector bucket {bucket_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )
        except Exception as e:
            logger.error(f"Unexpected error deleting vector bucket {bucket_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error deleting vector bucket {bucket_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"bucket_name": bucket_name, "error": str(e)}
            )