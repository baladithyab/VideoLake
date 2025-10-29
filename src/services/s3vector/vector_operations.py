"""
S3 Vector Operations Manager.

Handles core vector storage operations:
- Storing vectors (put) with batch support
- Querying vectors for similarity search
- Listing vectors in an index
- Vector data validation and formatting

Extracted from s3_vector_storage.py as part of service refactoring.
"""

from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError

from src.utils.aws_clients import aws_client_factory
from src.utils.aws_retry import AWSRetryHandler
from src.utils.arn_parser import ARNParser
from src.utils.vector_validation import VectorValidator
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger, get_structured_logger, LoggedOperation

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


class S3VectorOperations:
    """Manages core S3 vector storage operations (CRUD)."""

    def __init__(self):
        """Initialize vector operations manager with AWS clients."""
        structured_logger.log_function_entry("vector_operations_init")

        try:
            structured_logger.log_aws_api_call("s3vectors", "get_client")
            self.s3vectors_client = aws_client_factory.get_s3vectors_client()

            structured_logger.log_operation(
                "s3vector_operations_initialized",
                level="INFO"
            )
        except Exception as e:
            structured_logger.log_error("vector_operations_init", e)
            raise
        finally:
            structured_logger.log_function_exit("vector_operations_init")

    def _parse_index_identifier(self, identifier: str) -> Dict[str, str]:
        """
        Accept either:
          - ARN starting with 'arn:' -> {'indexArn': identifier}
          - resource-id format 'bucket/name/index/name' -> {'bucket': ..., 'indexName': ...}

        Returns:
            Dict with either 'indexArn' or both 'bucket' and 'indexName'
        """
        if identifier.startswith('arn:'):
            return {"indexArn": identifier}
        else:
            # Try parsing as ARN first
            bucket = ARNParser.extract_bucket_name(identifier)
            index = ARNParser.extract_index_name(identifier)

            if bucket and index:
                return {
                    "bucket": bucket,
                    "indexName": index
                }

            # Fall back to resource-id format: bucket/name/index/name
            parts = identifier.split('/')
            if len(parts) == 4 and parts[0] == 'bucket' and parts[2] == 'index':
                return {
                    "bucket": parts[1],
                    "indexName": parts[3]
                }

            # If all else fails, assume it's an ARN
            return {"indexArn": identifier}

    def put_vectors(
        self,
        index_arn: str,
        vectors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Store vectors in a vector index with batch support and metadata attachment.

        Args:
            index_arn: ARN of the vector index or resource-id format
            vectors_data: List of vector dictionaries with keys: 'key', 'data', 'metadata' (optional)
                         Each 'data' should be a VectorData object: {'float32': [list of float values]}

        Returns:
            Dict containing storage response and metadata

        Raises:
            ValidationError: If vector data is invalid
            VectorStorageError: If storage operation fails
        """
        structured_logger.log_function_entry(
            "put_vectors",
            index_arn=index_arn,
            vector_count=len(vectors_data)
        )

        structured_logger.log_resource_operation(
            "vectors",
            "put_start",
            index_arn,
            vector_count=len(vectors_data)
        )
        logger.info(f"Storing {len(vectors_data)} vectors in index: {index_arn}")

        with LoggedOperation(structured_logger, f"put_vectors_{len(vectors_data)}", index_arn=index_arn):
            # Validate inputs
            structured_logger.log_operation("validating_index_identifier", level="DEBUG")
            if not index_arn or not isinstance(index_arn, str):
                structured_logger.log_operation(
                    "validation_failed",
                    level="ERROR",
                    error="invalid_index_identifier",
                    provided=index_arn
                )
                raise ValidationError(
                    "Index ARN or resource-id must be a non-empty string",
                    error_code="INVALID_INDEX_IDENTIFIER",
                    error_details={"index_arn": index_arn}
                )

            structured_logger.log_operation("validating_vector_data", level="DEBUG", vector_count=len(vectors_data))
            VectorValidator.validate_vector_data(vectors_data)

            # Convert vector data to AWS S3 Vectors format
            formatted_vectors = []
            for vector in vectors_data:
                # Extract float32 data from the VectorData union type
                float32_data = vector['data']['float32']

                formatted_vector = {
                    'key': vector['key'],
                    'data': {
                        'float32': float32_data
                    }
                }

                # Add metadata if present
                if 'metadata' in vector and vector['metadata']:
                    formatted_vector['metadata'] = vector['metadata']

                formatted_vectors.append(formatted_vector)

            # Parse index identifier
            structured_logger.log_operation("parsing_index_identifier", level="DEBUG")
            index_params = self._parse_index_identifier(index_arn)

            # Prepare request parameters
            request_params = {
                **index_params,
                'vectors': formatted_vectors
            }

            def _put_vectors():
                structured_logger.log_aws_api_call(
                    "s3vectors",
                    "put_vectors",
                    {
                        "index": index_arn,
                        "vector_count": len(formatted_vectors)
                    }
                )
                return self.s3vectors_client.put_vectors(**request_params)

            try:
                response = AWSRetryHandler.retry_with_backoff(
                    _put_vectors,
                    operation_name=f"put_vectors_{len(vectors_data)}"
                )

                structured_logger.log_resource_operation(
                    "vectors",
                    "put_success",
                    index_arn,
                    vector_count=len(vectors_data)
                )
                logger.info(f"Successfully stored {len(vectors_data)} vectors")

                result = {
                    "index_arn": index_arn,
                    "vector_count": len(vectors_data),
                    "status": "stored",
                    "response": response
                }

                structured_logger.log_function_exit("put_vectors", result="success")
                return result

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']

                if error_code == 'NotFoundException':
                    raise VectorStorageError(
                        f"Vector index not found: {index_arn}",
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
                elif error_code == 'ValidationException':
                    raise ValidationError(
                        f"Vector data validation failed: {error_message}",
                        error_code="VECTOR_VALIDATION_FAILED",
                        error_details={"index_arn": index_arn, "aws_error": error_message}
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

    def query_vectors(
        self,
        index_arn: str,
        query_vector: List[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query vectors for similarity search.

        Args:
            index_arn: ARN of the vector index or resource-id format
            query_vector: Query vector as list of floats
            top_k: Number of similar vectors to return (1-1000)
            metadata_filter: Optional metadata filter for results

        Returns:
            Dict containing query results with similar vectors

        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If query fails
        """
        structured_logger.log_function_entry(
            "query_vectors",
            index_arn=index_arn,
            top_k=top_k
        )
        logger.info(f"Querying index {index_arn} for top {top_k} similar vectors")

        with LoggedOperation(structured_logger, f"query_vectors_k{top_k}", index_arn=index_arn):
            # Validate inputs
            if not index_arn or not isinstance(index_arn, str):
                raise ValidationError(
                    "Index ARN or resource-id must be a non-empty string",
                    error_code="INVALID_INDEX_IDENTIFIER",
                    error_details={"index_arn": index_arn}
                )

            # Validate query vector
            structured_logger.log_operation("validating_query_vector", level="DEBUG")
            VectorValidator.validate_query_vector(query_vector)

            # Validate top_k
            if not isinstance(top_k, int) or top_k < 1 or top_k > 1000:
                raise ValidationError(
                    f"top_k must be an integer between 1 and 1000, got {top_k}",
                    error_code="INVALID_TOP_K",
                    error_details={"top_k": top_k}
                )

            # Parse index identifier
            index_params = self._parse_index_identifier(index_arn)

            # Prepare request parameters
            request_params = {
                **index_params,
                'queryVector': {
                    'float32': query_vector
                },
                'topK': top_k
            }

            # Add metadata filter if provided
            if metadata_filter:
                request_params['metadataFilter'] = metadata_filter

            def _query_vectors():
                structured_logger.log_aws_api_call(
                    "s3vectors",
                    "query_vectors",
                    {
                        "index": index_arn,
                        "top_k": top_k,
                        "has_filter": bool(metadata_filter)
                    }
                )
                return self.s3vectors_client.query_vectors(**request_params)

            try:
                response = AWSRetryHandler.retry_with_backoff(
                    _query_vectors,
                    operation_name=f"query_vectors_{index_arn}"
                )

                results = response.get('results', [])
                structured_logger.log_resource_operation(
                    "vectors",
                    "query_success",
                    index_arn,
                    result_count=len(results),
                    top_k=top_k
                )
                logger.info(f"Query returned {len(results)} results")

                result = {
                    "index_arn": index_arn,
                    "top_k": top_k,
                    "result_count": len(results),
                    "results": results,
                    "response": response
                }

                structured_logger.log_function_exit("query_vectors", result_count=len(results))
                return result

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']

                if error_code == 'NotFoundException':
                    raise VectorStorageError(
                        f"Vector index not found: {index_arn}",
                        error_code="INDEX_NOT_FOUND",
                        error_details={"index_arn": index_arn}
                    )
                elif error_code == 'AccessDeniedException':
                    raise VectorStorageError(
                        f"Access denied when querying vectors: {error_message}",
                        error_code="ACCESS_DENIED",
                        error_details={
                            "index_arn": index_arn,
                            "required_permission": "s3vectors:QueryVectors"
                        }
                    )
                elif error_code == 'ValidationException':
                    raise ValidationError(
                        f"Query validation failed: {error_message}",
                        error_code="QUERY_VALIDATION_FAILED",
                        error_details={"index_arn": index_arn, "aws_error": error_message}
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

    def list_vectors(
        self,
        index_arn: str,
        max_results: int = 100,
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List vectors in an index (paginated).

        Args:
            index_arn: ARN of the vector index or resource-id format
            max_results: Maximum number of vectors to return (1-1000)
            next_token: Pagination token from previous request

        Returns:
            Dict containing list of vectors and pagination token

        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If listing fails
        """
        structured_logger.log_function_entry(
            "list_vectors",
            index_arn=index_arn,
            max_results=max_results,
            has_next_token=bool(next_token)
        )
        logger.info(f"Listing vectors in index {index_arn} (max_results={max_results})")

        with LoggedOperation(structured_logger, "list_vectors", index_arn=index_arn):
            # Validate inputs
            if not index_arn or not isinstance(index_arn, str):
                raise ValidationError(
                    "Index ARN or resource-id must be a non-empty string",
                    error_code="INVALID_INDEX_IDENTIFIER",
                    error_details={"index_arn": index_arn}
                )

            # Validate max_results
            if not isinstance(max_results, int) or max_results < 1 or max_results > 1000:
                raise ValidationError(
                    f"max_results must be an integer between 1 and 1000, got {max_results}",
                    error_code="INVALID_MAX_RESULTS",
                    error_details={"max_results": max_results}
                )

            # Parse index identifier
            index_params = self._parse_index_identifier(index_arn)

            # Prepare request parameters
            request_params = {
                **index_params,
                'maxResults': max_results
            }

            if next_token:
                request_params['nextToken'] = next_token

            def _list_vectors():
                structured_logger.log_aws_api_call(
                    "s3vectors",
                    "list_vectors",
                    {
                        "index": index_arn,
                        "max_results": max_results,
                        "has_next_token": bool(next_token)
                    }
                )
                return self.s3vectors_client.list_vectors(**request_params)

            try:
                response = AWSRetryHandler.retry_with_backoff(
                    _list_vectors,
                    operation_name=f"list_vectors_{index_arn}"
                )

                vectors = response.get('vectors', [])
                next_token_response = response.get('nextToken')

                structured_logger.log_resource_operation(
                    "vectors",
                    "list_success",
                    index_arn,
                    vector_count=len(vectors),
                    has_more=bool(next_token_response)
                )
                logger.info(f"Listed {len(vectors)} vectors (has_more={bool(next_token_response)})")

                result = {
                    "index_arn": index_arn,
                    "vector_count": len(vectors),
                    "vectors": vectors,
                    "next_token": next_token_response,
                    "has_more": bool(next_token_response)
                }

                structured_logger.log_function_exit("list_vectors", vector_count=len(vectors))
                return result

            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']

                if error_code == 'NotFoundException':
                    raise VectorStorageError(
                        f"Vector index not found: {index_arn}",
                        error_code="INDEX_NOT_FOUND",
                        error_details={"index_arn": index_arn}
                    )
                elif error_code == 'AccessDeniedException':
                    raise VectorStorageError(
                        f"Access denied when listing vectors: {error_message}",
                        error_code="ACCESS_DENIED",
                        error_details={
                            "index_arn": index_arn,
                            "required_permission": "s3vectors:ListVectors"
                        }
                    )
                else:
                    raise VectorStorageError(
                        f"Failed to list vectors: {error_message}",
                        error_code=error_code,
                        error_details={
                            "index_arn": index_arn,
                            "max_results": max_results,
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
                        "max_results": max_results,
                        "error": str(e)
                    }
                )

    def put_vectors_batch(
        self,
        index_arn: str,
        vectors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Batch store vectors (alias for put_vectors for backward compatibility).

        Args:
            index_arn: ARN of the vector index
            vectors_data: List of vector dictionaries

        Returns:
            Dict containing storage response

        Raises:
            ValidationError: If vector data is invalid
            VectorStorageError: If storage operation fails
        """
        return self.put_vectors(index_arn, vectors_data)

    def query_similar_vectors(
        self,
        index_arn: str,
        query_vector: List[float],
        top_k: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query similar vectors (alias for query_vectors for backward compatibility).

        Args:
            index_arn: ARN of the vector index
            query_vector: Query vector
            top_k: Number of results
            metadata_filter: Optional metadata filter

        Returns:
            Dict containing query results

        Raises:
            ValidationError: If parameters are invalid
            VectorStorageError: If query fails
        """
        return self.query_vectors(index_arn, query_vector, top_k, metadata_filter)
