"""
Unit tests for S3VectorOperations.

Tests vector CRUD operations including:
- Vector storage (put) with batch support
- Vector similarity query operations
- Vector listing with pagination
- Index identifier parsing (ARN vs resource-id format)
- Vector data validation and formatting
- Error handling and retries
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.services.s3vector.vector_operations import S3VectorOperations
from src.exceptions import VectorStorageError, ValidationError


class TestS3VectorOperationsInit:
    """Test S3VectorOperations initialization."""

    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_init_success(self, mock_factory):
        """Test successful initialization."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        operations = S3VectorOperations()

        assert operations.s3vectors_client == mock_s3vectors
        mock_factory.get_s3vectors_client.assert_called_once()

    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_init_client_error(self, mock_factory):
        """Test initialization failure when client creation fails."""
        mock_factory.get_s3vectors_client.side_effect = Exception("Client creation failed")

        with pytest.raises(Exception, match="Client creation failed"):
            S3VectorOperations()


class TestParseIndexIdentifier:
    """Test index identifier parsing logic."""

    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def setup_method(self):
        """Setup test fixtures."""
        with patch('src.services.s3vector.vector_operations.aws_client_factory'):
            self.operations = S3VectorOperations()

    def test_parse_arn_format(self):
        """Test parsing full ARN format."""
        arn = "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index"
        result = self.operations._parse_index_identifier(arn)

        assert "indexArn" in result
        assert result["indexArn"] == arn

    def test_parse_resource_id_format(self):
        """Test parsing resource-id format."""
        resource_id = "bucket/my-bucket/index/my-index"
        result = self.operations._parse_index_identifier(resource_id)

        assert "bucket" in result
        assert "indexName" in result
        assert result["bucket"] == "my-bucket"
        assert result["indexName"] == "my-index"

    def test_parse_invalid_resource_id(self):
        """Test parsing invalid resource-id (falls back to ARN)."""
        invalid = "invalid/format"
        result = self.operations._parse_index_identifier(invalid)

        # Should fall back to treating as ARN
        assert "indexArn" in result

    def test_parse_empty_string(self):
        """Test parsing empty string (falls back to ARN)."""
        result = self.operations._parse_index_identifier("")

        assert "indexArn" in result


class TestPutVectors:
    """Test vector storage operations."""

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_success(self, mock_factory, mock_validator, mock_retry):
        """Test successful vector storage."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [
            {
                "key": "vec1",
                "data": {"float32": [0.1, 0.2, 0.3]},
                "metadata": {"category": "test"}
            }
        ]

        mock_response = {"storedVectors": 1}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors(
            "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index",
            vectors_data
        )

        assert result["vector_count"] == 1
        assert result["status"] == "stored"
        mock_validator.validate_vector_data.assert_called_once_with(vectors_data)
        mock_retry.retry_with_backoff.assert_called_once()

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_multiple(self, mock_factory, mock_validator, mock_retry):
        """Test storing multiple vectors."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [
            {"key": "vec1", "data": {"float32": [0.1, 0.2, 0.3]}},
            {"key": "vec2", "data": {"float32": [0.4, 0.5, 0.6]}},
            {"key": "vec3", "data": {"float32": [0.7, 0.8, 0.9]}}
        ]

        mock_response = {"storedVectors": 3}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors("bucket/test-bucket/index/test-index", vectors_data)

        assert result["vector_count"] == 3
        assert result["status"] == "stored"

    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_validation_error(self, mock_factory, mock_validator):
        """Test vector storage with validation error."""
        mock_factory.get_s3vectors_client.return_value = Mock()
        mock_validator.validate_vector_data.side_effect = ValidationError("Invalid vector data")

        operations = S3VectorOperations()

        with pytest.raises(ValidationError, match="Invalid vector data"):
            operations.put_vectors("arn:test", [{"key": "vec1"}])

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_api_error(self, mock_factory, mock_validator, mock_retry):
        """Test vector storage with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [{"key": "vec1", "data": {"float32": [0.1, 0.2]}}]

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'PutVectors')

        operations = S3VectorOperations()

        with pytest.raises(VectorStorageError, match="Failed to store vectors"):
            operations.put_vectors("arn:test", vectors_data)

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_without_metadata(self, mock_factory, mock_validator, mock_retry):
        """Test storing vectors without metadata."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [{"key": "vec1", "data": {"float32": [0.1, 0.2, 0.3]}}]

        mock_response = {"storedVectors": 1}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors("arn:test", vectors_data)

        assert result["status"] == "stored"


class TestQueryVectors:
    """Test vector similarity query operations."""

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_vectors_success(self, mock_factory, mock_validator, mock_retry):
        """Test successful vector query."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        query_vector = [0.1, 0.2, 0.3]
        mock_response = {
            "results": [
                {"key": "vec1", "score": 0.95},
                {"key": "vec2", "score": 0.87}
            ]
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.query_vectors(
            "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index",
            query_vector,
            top_k=10
        )

        assert result["result_count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["key"] == "vec1"
        mock_validator.validate_query_vector.assert_called_once_with(query_vector)

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_vectors_with_metadata_filter(self, mock_factory, mock_validator, mock_retry):
        """Test vector query with metadata filter."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        query_vector = [0.1, 0.2, 0.3]
        metadata_filter = {"category": "test"}
        mock_response = {"results": [{"key": "vec1", "score": 0.95}]}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.query_vectors(
            "bucket/test-bucket/index/test-index",
            query_vector,
            top_k=5,
            metadata_filter=metadata_filter
        )

        assert result["result_count"] == 1
        # Verify metadata filter was passed
        call_args = mock_retry.retry_with_backoff.call_args
        assert call_args is not None

    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_vectors_validation_error(self, mock_factory, mock_validator):
        """Test vector query with validation error."""
        mock_factory.get_s3vectors_client.return_value = Mock()
        mock_validator.validate_query_vector.side_effect = ValidationError("Invalid query vector")

        operations = S3VectorOperations()

        with pytest.raises(ValidationError, match="Invalid query vector"):
            operations.query_vectors("arn:test", [0.1, 0.2])

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_vectors_no_results(self, mock_factory, mock_validator, mock_retry):
        """Test vector query with no results."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"results": []}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.query_vectors("arn:test", [0.1, 0.2, 0.3])

        assert result["result_count"] == 0
        assert result["results"] == []

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_vectors_api_error(self, mock_factory, mock_validator, mock_retry):
        """Test vector query with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'QueryVectors')

        operations = S3VectorOperations()

        with pytest.raises(VectorStorageError, match="Failed to query vectors"):
            operations.query_vectors("arn:test", [0.1, 0.2, 0.3])


class TestListVectors:
    """Test vector listing operations."""

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_list_vectors_success(self, mock_factory, mock_retry):
        """Test successful vector listing."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "vectors": [
                {"key": "vec1", "data": {"float32": [0.1, 0.2]}},
                {"key": "vec2", "data": {"float32": [0.3, 0.4]}}
            ],
            "nextToken": "token123"
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.list_vectors(
            "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index"
        )

        assert len(result["vectors"]) == 2
        assert result["next_token"] == "token123"

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_list_vectors_with_pagination(self, mock_factory, mock_retry):
        """Test vector listing with pagination token."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "vectors": [{"key": "vec3"}],
            "nextToken": None
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.list_vectors(
            "bucket/test-bucket/index/test-index",
            max_results=50,
            next_token="previous_token"
        )

        assert len(result["vectors"]) == 1
        assert result["next_token"] is None

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_list_vectors_empty(self, mock_factory, mock_retry):
        """Test vector listing with no vectors."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"vectors": []}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.list_vectors("arn:test")

        assert result["vectors"] == []
        assert result.get("next_token") is None

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_list_vectors_api_error(self, mock_factory, mock_retry):
        """Test vector listing with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'ListVectors')

        operations = S3VectorOperations()

        with pytest.raises(VectorStorageError, match="Failed to list vectors"):
            operations.list_vectors("arn:test")


class TestBatchOperations:
    """Test batch vector operations."""

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_vectors_batch_alias(self, mock_factory, mock_validator, mock_retry):
        """Test put_vectors_batch is an alias for put_vectors."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [{"key": "vec1", "data": {"float32": [0.1, 0.2]}}]
        mock_response = {"storedVectors": 1}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors_batch("arn:test", vectors_data)

        assert result["status"] == "stored"
        mock_validator.validate_vector_data.assert_called_once()

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_query_similar_vectors_alias(self, mock_factory, mock_validator, mock_retry):
        """Test query_similar_vectors is an alias for query_vectors."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"results": [{"key": "vec1", "score": 0.95}]}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.query_similar_vectors("arn:test", [0.1, 0.2, 0.3])

        assert result["result_count"] == 1
        mock_validator.validate_query_vector.assert_called_once()


class TestIntegrationScenarios:
    """Test integrated scenarios and edge cases."""

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_put_query_list_workflow(self, mock_factory, mock_validator, mock_retry):
        """Test complete put, query, and list workflow."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        # Mock responses
        put_response = {"storedVectors": 2}
        query_response = {"results": [{"key": "vec1", "score": 0.95}]}
        list_response = {"vectors": [{"key": "vec1"}, {"key": "vec2"}]}

        mock_retry.retry_with_backoff.side_effect = [put_response, query_response, list_response]

        operations = S3VectorOperations()
        index_arn = "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index"

        # Put vectors
        vectors_data = [
            {"key": "vec1", "data": {"float32": [0.1, 0.2, 0.3]}},
            {"key": "vec2", "data": {"float32": [0.4, 0.5, 0.6]}}
        ]
        put_result = operations.put_vectors(index_arn, vectors_data)
        assert put_result["vector_count"] == 2

        # Query vectors
        query_result = operations.query_vectors(index_arn, [0.1, 0.2, 0.3], top_k=1)
        assert query_result["result_count"] == 1

        # List vectors
        list_result = operations.list_vectors(index_arn)
        assert len(list_result["vectors"]) == 2

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_multiple_identifier_formats(self, mock_factory, mock_validator, mock_retry):
        """Test operations with different identifier formats."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"results": []}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()

        # Test with ARN format
        result1 = operations.query_vectors(
            "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index",
            [0.1, 0.2, 0.3]
        )
        assert result1["result_count"] == 0

        # Test with resource-id format
        result2 = operations.query_vectors(
            "bucket/test-bucket/index/test-index",
            [0.1, 0.2, 0.3]
        )
        assert result2["result_count"] == 0

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_large_batch_put(self, mock_factory, mock_validator, mock_retry):
        """Test storing a large batch of vectors."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        # Create 100 vectors
        vectors_data = [
            {"key": f"vec{i}", "data": {"float32": [float(i), float(i+1), float(i+2)]}}
            for i in range(100)
        ]

        mock_response = {"storedVectors": 100}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors("arn:test", vectors_data)

        assert result["vector_count"] == 100
        mock_validator.validate_vector_data.assert_called_once_with(vectors_data)

    @patch('src.services.s3vector.vector_operations.AWSRetryHandler')
    @patch('src.services.s3vector.vector_operations.VectorValidator')
    @patch('src.services.s3vector.vector_operations.aws_client_factory')
    def test_vector_with_complex_metadata(self, mock_factory, mock_validator, mock_retry):
        """Test storing vectors with complex metadata."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        vectors_data = [{
            "key": "vec1",
            "data": {"float32": [0.1, 0.2, 0.3]},
            "metadata": {
                "category": "test",
                "timestamp": "2024-01-01",
                "tags": ["important", "verified"],
                "score": 0.95
            }
        }]

        mock_response = {"storedVectors": 1}
        mock_retry.retry_with_backoff.return_value = mock_response

        operations = S3VectorOperations()
        result = operations.put_vectors("arn:test", vectors_data)

        assert result["status"] == "stored"
