"""
S3 Vector Bucket Manager.

Handles S3 vector bucket lifecycle operations:
- Creating vector buckets with encryption configuration
- Retrieving bucket attributes and configuration
- Listing vector buckets
- Deleting vector buckets (with optional cascade)
- Checking bucket existence

Extracted from s3_vector_storage.py as part of service refactoring.
"""

from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

from src.utils.aws_clients import aws_client_factory
from src.utils.aws_retry import AWSRetryHandler
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger, get_structured_logger, LoggedOperation
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


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


class S3VectorBucketManager:
    """Manages S3 vector bucket lifecycle operations."""

    def __init__(self):
        """Initialize bucket manager with AWS clients."""
        structured_logger.log_function_entry("bucket_manager_init")

        try:
            structured_logger.log_aws_api_call("s3vectors", "get_client")
            self.s3vectors_client = aws_client_factory.get_s3vectors_client()

            structured_logger.log_aws_api_call("s3", "get_client")
            self.s3_client = aws_client_factory.get_s3_client()

            structured_logger.log_operation(
                "s3vector_bucket_manager_initialized",
                level="INFO"
            )
        except Exception as e:
            structured_logger.log_error("bucket_manager_init", e)
            raise
        finally:
            structured_logger.log_function_exit("bucket_manager_init")

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

    def create_vector_bucket(
        self,
        bucket_name: str,
        encryption_type: str = "SSE-S3",
        kms_key_arn: Optional[str] = None
    ) -> Dict[str, Any]:
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
        structured_logger.log_function_entry(
            "create_vector_bucket",
            bucket_name=bucket_name,
            encryption_type=encryption_type,
            has_kms_key=bool(kms_key_arn)
        )

        structured_logger.log_resource_operation(
            "vector_bucket",
            "create_start",
            bucket_name,
            encryption_type=encryption_type
        )
        logger.info(f"Creating vector bucket: {bucket_name}")

        with LoggedOperation(structured_logger, f"create_vector_bucket_{bucket_name}", bucket_name=bucket_name):
            # Validate bucket name
            structured_logger.log_operation("validating_bucket_name", level="DEBUG", bucket_name=bucket_name)
            self._validate_bucket_name(bucket_name)

            # Validate and normalize encryption configuration
            structured_logger.log_operation("validating_encryption_config", level="DEBUG", encryption_type=encryption_type)
            norm_enc = _normalize_encryption_type(encryption_type)
            if norm_enc not in ["AES256", "aws:kms"]:
                structured_logger.log_operation(
                    "validation_failed",
                    level="ERROR",
                    error="invalid_encryption_type",
                    provided=encryption_type,
                    normalized=norm_enc
                )
                raise ValidationError(
                    f"Invalid encryption type: {encryption_type}. Must be 'SSE-S3'/'AES256' or 'SSE-KMS'/'aws:kms'",
                    error_code="INVALID_ENCRYPTION_TYPE",
                    error_details={"encryption_type": encryption_type}
                )

            if norm_enc == "aws:kms" and not kms_key_arn:
                structured_logger.log_operation(
                    "validation_failed",
                    level="ERROR",
                    error="missing_kms_key_arn",
                    encryption_type=norm_enc
                )
                raise ValidationError(
                    "KMS key ARN is required when using SSE-KMS encryption",
                    error_code="MISSING_KMS_KEY_ARN"
                )

            # Prepare request parameters
            structured_logger.log_operation("preparing_request_params", level="DEBUG")
            request_params = {
                "vectorBucketName": bucket_name
            }

            # Add encryption configuration if specified
            if norm_enc:
                enc_cfg = {"sseType": norm_enc}
                if norm_enc == "aws:kms" and kms_key_arn:
                    enc_cfg["kmsKeyArn"] = kms_key_arn
                request_params["encryptionConfiguration"] = enc_cfg
                structured_logger.log_operation(
                    "encryption_config_added",
                    level="DEBUG",
                    encryption_type=norm_enc,
                    has_kms_key=bool(kms_key_arn)
                )

            def _create_bucket():
                structured_logger.log_aws_api_call(
                    "s3vectors",
                    "create_vector_bucket",
                    {"bucket_name": bucket_name, "encryption_type": norm_enc}
                )
                return self.s3vectors_client.create_vector_bucket(**request_params)

            try:
                response = AWSRetryHandler.retry_with_backoff(
                    _create_bucket,
                    operation_name=f"create_vector_bucket_{bucket_name}"
                )

                structured_logger.log_resource_operation(
                    "vector_bucket",
                    "create_success",
                    bucket_name,
                    response_keys=list(response.keys()) if response else []
                )
                logger.info(f"Successfully created vector bucket: {bucket_name}")

                # Log to local resource registry (best-effort)
                try:
                    from src.config.unified_config_manager import get_unified_config_manager as _cfg
                    resource_registry.log_vector_bucket_created(
                        bucket_name=bucket_name,
                        region=_cfg().config.aws.region,
                        encryption=encryption_type,
                        kms_key_arn=kms_key_arn,
                        source="service",
                    )
                    structured_logger.log_operation(
                        "resource_registry_updated",
                        level="DEBUG",
                        bucket_name=bucket_name
                    )
                except Exception as e:
                    structured_logger.log_error("resource_registry_update", e, bucket_name=bucket_name)

                result = {
                    "bucket_name": bucket_name,
                    "status": "created",
                    "encryption_type": encryption_type,
                    "kms_key_arn": kms_key_arn,
                    "response": response
                }

                structured_logger.log_function_exit("create_vector_bucket", result=result.get("status"))
                return result

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
            Dict containing bucket configuration and metadata

        Raises:
            ValidationError: If bucket name is invalid
            VectorStorageError: If bucket retrieval fails
        """
        structured_logger.log_function_entry("get_vector_bucket", bucket_name=bucket_name)
        logger.info(f"Getting vector bucket: {bucket_name}")

        # Validate bucket name
        self._validate_bucket_name(bucket_name)

        def _get_bucket():
            structured_logger.log_aws_api_call("s3vectors", "get_vector_bucket", {"bucket_name": bucket_name})
            return self.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _get_bucket,
                operation_name=f"get_vector_bucket_{bucket_name}"
            )

            structured_logger.log_operation(
                "get_vector_bucket_success",
                level="INFO",
                bucket_name=bucket_name,
                response_keys=list(response.keys()) if response else []
            )
            logger.info(f"Successfully retrieved vector bucket: {bucket_name}")

            result = {
                "bucket_name": bucket_name,
                "exists": True,
                "details": response
            }

            structured_logger.log_function_exit("get_vector_bucket", result="success")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Vector bucket not found: {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "exists": False,
                    "message": "Bucket not found"
                }
            else:
                logger.error(f"Failed to get vector bucket {bucket_name}: {error_message}")
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
        List all S3 vector buckets in the account.

        Returns:
            List of bucket dictionaries with names and metadata

        Raises:
            VectorStorageError: If listing fails
        """
        structured_logger.log_function_entry("list_vector_buckets")
        logger.info("Listing vector buckets")

        def _list_buckets():
            structured_logger.log_aws_api_call("s3vectors", "list_vector_buckets", {})
            return self.s3vectors_client.list_vector_buckets()

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _list_buckets,
                operation_name="list_vector_buckets"
            )

            buckets = response.get('vectorBuckets', [])
            structured_logger.log_operation(
                "list_vector_buckets_success",
                level="INFO",
                bucket_count=len(buckets)
            )
            logger.info(f"Found {len(buckets)} vector buckets")

            structured_logger.log_function_exit("list_vector_buckets", bucket_count=len(buckets))
            return buckets

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to list vector buckets: {error_message}")
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
            bucket_name: Name of the bucket to check

        Returns:
            True if bucket exists, False otherwise
        """
        try:
            result = self.get_vector_bucket(bucket_name)
            return result.get("exists", False)
        except Exception:
            return False

    def delete_vector_bucket(
        self,
        bucket_name: str,
        cascade: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a vector bucket (optionally with all indexes).

        Args:
            bucket_name: Name of the bucket to delete
            cascade: If True, delete all indexes in the bucket first

        Returns:
            Dict with deletion status

        Raises:
            ValidationError: If bucket name is invalid
            VectorStorageError: If deletion fails
        """
        structured_logger.log_function_entry(
            "delete_vector_bucket",
            bucket_name=bucket_name,
            cascade=cascade
        )
        logger.info(f"Deleting vector bucket: {bucket_name} (cascade={cascade})")

        # Validate bucket name
        self._validate_bucket_name(bucket_name)

        # If cascade, we need to delete all indexes first
        # This requires the index manager, so we'll handle it in the facade

        def _delete_bucket():
            structured_logger.log_aws_api_call(
                "s3vectors",
                "delete_vector_bucket",
                {"bucket_name": bucket_name}
            )
            return self.s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _delete_bucket,
                operation_name=f"delete_vector_bucket_{bucket_name}"
            )

            structured_logger.log_resource_operation(
                "vector_bucket",
                "delete_success",
                bucket_name
            )
            logger.info(f"Successfully deleted vector bucket: {bucket_name}")

            # Update resource registry (best-effort)
            try:
                resource_registry.log_vector_bucket_deleted(bucket_name)
            except Exception as e:
                structured_logger.log_error("resource_registry_update", e, bucket_name=bucket_name)

            result = {
                "bucket_name": bucket_name,
                "status": "deleted",
                "response": response
            }

            structured_logger.log_function_exit("delete_vector_bucket", result="success")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'ResourceNotFoundException':
                logger.warning(f"Vector bucket not found: {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "status": "not_found",
                    "message": "Bucket does not exist"
                }
            elif error_code == 'ConflictException':
                raise VectorStorageError(
                    f"Cannot delete bucket {bucket_name}: bucket contains indexes. Use cascade=True to force deletion.",
                    error_code="BUCKET_NOT_EMPTY",
                    error_details={"bucket_name": bucket_name}
                )
            else:
                logger.error(f"Failed to delete vector bucket {bucket_name}: {error_message}")
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
