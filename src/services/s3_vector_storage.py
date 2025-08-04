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