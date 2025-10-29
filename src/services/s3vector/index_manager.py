"""
S3 Vector Index Manager.

Handles S3 vector index lifecycle operations:
- Creating vector indexes with dimension and metric configuration
- Retrieving index metadata and configuration
- Listing indexes within a bucket
- Deleting indexes (with retry logic)
- Checking index existence

Extracted from s3_vector_storage.py as part of service refactoring.
"""

import time
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

from src.utils.aws_clients import aws_client_factory
from src.utils.aws_retry import AWSRetryHandler
from src.utils.arn_parser import ARNParser
from src.utils.vector_validation import VectorValidator
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger, get_structured_logger, LoggedOperation
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


class S3VectorIndexManager:
    """Manages S3 vector index lifecycle operations."""

    # Supported configurations
    SUPPORTED_DISTANCE_METRICS = {"cosine", "euclidean"}
    SUPPORTED_DATA_TYPES = {"float32"}

    def __init__(self):
        """Initialize index manager with AWS clients."""
        structured_logger.log_function_entry("index_manager_init")

        try:
            structured_logger.log_aws_api_call("s3vectors", "get_client")
            self.s3vectors_client = aws_client_factory.get_s3vectors_client()

            structured_logger.log_operation(
                "s3vector_index_manager_initialized",
                level="INFO"
            )
        except Exception as e:
            structured_logger.log_error("index_manager_init", e)
            raise
        finally:
            structured_logger.log_function_exit("index_manager_init")

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

    def _validate_bucket_name(self, bucket_name: str) -> None:
        """Validate bucket name (basic validation)."""
        if not bucket_name or not bucket_name.strip():
            raise ValidationError(
                "Bucket name cannot be empty",
                error_code="EMPTY_BUCKET_NAME"
            )

    def create_vector_index(
        self,
        bucket_name: str,
        index_name: str,
        dimensions: int,
        distance_metric: str = "cosine",
        data_type: str = "float32",
        non_filterable_metadata_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
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
        structured_logger.log_function_entry(
            "create_vector_index",
            bucket_name=bucket_name,
            index_name=index_name,
            dimensions=dimensions,
            distance_metric=distance_metric
        )
        logger.info(f"Creating vector index: {index_name} in bucket: {bucket_name}")

        with LoggedOperation(structured_logger, f"create_index_{bucket_name}_{index_name}"):
            # Validate inputs
            self._validate_bucket_name(bucket_name)
            self._validate_index_name(index_name)
            VectorValidator.validate_dimensions(dimensions)

            if distance_metric not in self.SUPPORTED_DISTANCE_METRICS:
                raise ValidationError(
                    f"Invalid distance metric: {distance_metric}. Must be one of: {self.SUPPORTED_DISTANCE_METRICS}",
                    error_code="INVALID_DISTANCE_METRIC",
                    error_details={"distance_metric": distance_metric}
                )

            if data_type not in self.SUPPORTED_DATA_TYPES:
                raise ValidationError(
                    f"Invalid data type: {data_type}. Must be one of: {self.SUPPORTED_DATA_TYPES}",
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
                structured_logger.log_aws_api_call(
                    "s3vectors",
                    "create_index",
                    {"bucket": bucket_name, "index": index_name, "dimensions": dimensions}
                )
                return self.s3vectors_client.create_index(**request_params)

            try:
                response = AWSRetryHandler.retry_with_backoff(
                    _create_index,
                    operation_name=f"create_index_{bucket_name}_{index_name}"
                )

                structured_logger.log_resource_operation(
                    "vector_index",
                    "create_success",
                    f"{bucket_name}/{index_name}",
                    dimensions=dimensions
                )
                logger.info(f"Successfully created vector index: {index_name} in bucket: {bucket_name}")

                # Log to registry (best-effort)
                try:
                    from src.config.unified_config_manager import get_unified_config_manager as _cfg
                    import boto3 as _b3
                    region = _cfg().config.aws.region
                    sts = _b3.client('sts', region_name=region)
                    account_id = sts.get_caller_identity()['Account']
                    index_arn = ARNParser.build_s3vector_arn(
                        bucket_name, index_name, region, account_id
                    )
                    resource_registry.log_index_created(
                        bucket_name=bucket_name,
                        index_name=index_name,
                        arn=index_arn,
                        dimensions=dimensions,
                        distance_metric=distance_metric,
                        source="service",
                    )
                    structured_logger.log_operation(
                        "resource_registry_updated",
                        level="DEBUG",
                        index_name=index_name
                    )
                except Exception as e:
                    structured_logger.log_error("resource_registry_update", e)

                result = {
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "dimensions": dimensions,
                    "distance_metric": distance_metric,
                    "data_type": data_type,
                    "non_filterable_metadata_keys": non_filterable_metadata_keys,
                    "status": "created",
                    "response": response
                }

                structured_logger.log_function_exit("create_vector_index", result="success")
                return result

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

    def list_vector_indexes(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List vector indexes in a bucket.

        Args:
            bucket_name: Name of the vector bucket
            prefix: Optional prefix to filter index names
            max_results: Maximum number of results to return

        Returns:
            List of index dictionaries with metadata

        Raises:
            ValidationError: If bucket name is invalid
            VectorStorageError: If listing fails
        """
        structured_logger.log_function_entry(
            "list_vector_indexes",
            bucket_name=bucket_name,
            prefix=prefix,
            max_results=max_results
        )
        logger.info(f"Listing indexes in bucket: {bucket_name}")

        # Validate bucket name
        self._validate_bucket_name(bucket_name)

        request_params = {
            "vectorBucketName": bucket_name,
            "maxResults": max_results
        }

        if prefix:
            request_params["prefix"] = prefix

        def _list_indexes():
            structured_logger.log_aws_api_call(
                "s3vectors",
                "list_indexes",
                {"bucket": bucket_name, "prefix": prefix}
            )
            return self.s3vectors_client.list_indexes(**request_params)

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _list_indexes,
                operation_name=f"list_indexes_{bucket_name}"
            )

            indexes = response.get('indexes', [])
            structured_logger.log_operation(
                "list_indexes_success",
                level="INFO",
                bucket_name=bucket_name,
                index_count=len(indexes)
            )
            logger.info(f"Found {len(indexes)} indexes in bucket {bucket_name}")

            structured_logger.log_function_exit("list_vector_indexes", index_count=len(indexes))
            return indexes

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'NotFoundException':
                logger.warning(f"Vector bucket not found: {bucket_name}")
                return []
            else:
                logger.error(f"Failed to list indexes in bucket {bucket_name}: {error_message}")
                raise VectorStorageError(
                    f"Failed to list indexes in bucket {bucket_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )

        except Exception as e:
            logger.error(f"Unexpected error listing indexes in bucket {bucket_name}: {e}")
            raise VectorStorageError(
                f"Unexpected error listing indexes in bucket {bucket_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={"bucket_name": bucket_name, "error": str(e)}
            )

    def get_vector_index_metadata(
        self,
        bucket_name: str,
        index_name: str
    ) -> Dict[str, Any]:
        """
        Get vector index metadata and configuration.

        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index

        Returns:
            Dict containing index metadata

        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If retrieval fails
        """
        structured_logger.log_function_entry(
            "get_vector_index_metadata",
            bucket_name=bucket_name,
            index_name=index_name
        )
        logger.info(f"Getting metadata for index: {index_name} in bucket: {bucket_name}")

        # Validate inputs
        self._validate_bucket_name(bucket_name)
        self._validate_index_name(index_name)

        def _get_metadata():
            structured_logger.log_aws_api_call(
                "s3vectors",
                "get_index",
                {"bucket": bucket_name, "index": index_name}
            )
            return self.s3vectors_client.get_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _get_metadata,
                operation_name=f"get_index_{bucket_name}_{index_name}"
            )

            structured_logger.log_operation(
                "get_index_metadata_success",
                level="INFO",
                bucket_name=bucket_name,
                index_name=index_name
            )
            logger.info(f"Successfully retrieved metadata for index: {index_name}")

            result = {
                "bucket_name": bucket_name,
                "index_name": index_name,
                "exists": True,
                "metadata": response
            }

            structured_logger.log_function_exit("get_vector_index_metadata", result="success")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'NotFoundException':
                logger.warning(f"Index not found: {index_name} in bucket {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "exists": False,
                    "message": "Index not found"
                }
            else:
                logger.error(f"Failed to get index metadata: {error_message}")
                raise VectorStorageError(
                    f"Failed to get index metadata for {index_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )

        except Exception as e:
            logger.error(f"Unexpected error getting index metadata: {e}")
            raise VectorStorageError(
                f"Unexpected error getting index metadata for {index_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "error": str(e)
                }
            )

    def delete_vector_index(
        self,
        bucket_name: str,
        index_name: str
    ) -> Dict[str, Any]:
        """
        Delete a vector index.

        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index to delete

        Returns:
            Dict with deletion status

        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If deletion fails
        """
        structured_logger.log_function_entry(
            "delete_vector_index",
            bucket_name=bucket_name,
            index_name=index_name
        )
        logger.info(f"Deleting vector index: {index_name} from bucket: {bucket_name}")

        # Validate inputs
        self._validate_bucket_name(bucket_name)
        self._validate_index_name(index_name)

        def _delete_index():
            structured_logger.log_aws_api_call(
                "s3vectors",
                "delete_index",
                {"bucket": bucket_name, "index": index_name}
            )
            return self.s3vectors_client.delete_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )

        try:
            response = AWSRetryHandler.retry_with_backoff(
                _delete_index,
                operation_name=f"delete_index_{bucket_name}_{index_name}"
            )

            structured_logger.log_resource_operation(
                "vector_index",
                "delete_success",
                f"{bucket_name}/{index_name}"
            )
            logger.info(f"Successfully deleted vector index: {index_name}")

            # Update resource registry (best-effort)
            try:
                resource_registry.log_index_deleted(bucket_name, index_name)
            except Exception as e:
                structured_logger.log_error("resource_registry_update", e)

            result = {
                "bucket_name": bucket_name,
                "index_name": index_name,
                "status": "deleted",
                "response": response
            }

            structured_logger.log_function_exit("delete_vector_index", result="success")
            return result

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'NotFoundException':
                logger.warning(f"Index not found: {index_name} in bucket {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "status": "not_found",
                    "message": "Index does not exist"
                }
            else:
                logger.error(f"Failed to delete index: {error_message}")
                raise VectorStorageError(
                    f"Failed to delete index {index_name}: {error_message}",
                    error_code=error_code,
                    error_details={
                        "bucket_name": bucket_name,
                        "index_name": index_name,
                        "aws_error_code": error_code,
                        "aws_error_message": error_message
                    }
                )

        except Exception as e:
            logger.error(f"Unexpected error deleting index: {e}")
            raise VectorStorageError(
                f"Unexpected error deleting index {index_name}: {str(e)}",
                error_code="UNEXPECTED_ERROR",
                error_details={
                    "bucket_name": bucket_name,
                    "index_name": index_name,
                    "error": str(e)
                }
            )

    def delete_index_with_retries(
        self,
        bucket: str,
        index: str,
        max_attempts: int = 6,
        backoff_base: float = 1.0
    ) -> bool:
        """
        Delete index with custom retry logic (for cases needing more retries).

        Args:
            bucket: Bucket name
            index: Index name
            max_attempts: Maximum retry attempts
            backoff_base: Base delay for backoff

        Returns:
            True if deleted successfully, False otherwise
        """
        logger.info(f"Attempting to delete index {index} from bucket {bucket} with {max_attempts} max attempts")

        for attempt in range(max_attempts):
            try:
                result = self.delete_vector_index(bucket, index)
                if result.get("status") in ["deleted", "not_found"]:
                    logger.info(f"Successfully deleted index {index} on attempt {attempt + 1}")
                    return True
            except VectorStorageError as e:
                if attempt < max_attempts - 1:
                    delay = backoff_base * (2 ** attempt)
                    logger.warning(
                        f"Delete attempt {attempt + 1}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to delete index {index} after {max_attempts} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error during delete retry: {e}")
                return False

        return False

    def index_exists(
        self,
        bucket_name: str,
        index_name: str
    ) -> bool:
        """
        Check if an index exists.

        Args:
            bucket_name: Name of the vector bucket
            index_name: Name of the vector index

        Returns:
            True if index exists, False otherwise
        """
        try:
            result = self.get_vector_index_metadata(bucket_name, index_name)
            return result.get("exists", False)
        except Exception:
            return False
