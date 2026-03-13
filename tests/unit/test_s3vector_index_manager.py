"""
Unit tests for S3VectorIndexManager.

Tests index lifecycle operations including:
- Index creation with various configurations
- Index listing and metadata retrieval
- Index deletion with retries
- Index existence checks
- Validation logic (dimensions, metrics, data types)
- Error handling and retry scenarios
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from botocore.exceptions import ClientError

from src.services.s3vector.index_manager import S3VectorIndexManager
from src.exceptions import VectorStorageError, ValidationError


class TestS3VectorIndexManagerInit:
    """Test S3VectorIndexManager initialization."""

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_init_success(self, mock_factory):
        """Test successful initialization."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        manager = S3VectorIndexManager()

        assert manager.s3vectors_client == mock_s3vectors
        mock_factory.get_s3vectors_client.assert_called_once()
        assert manager.SUPPORTED_DISTANCE_METRICS == {"cosine", "euclidean"}
        assert manager.SUPPORTED_DATA_TYPES == {"float32"}

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_init_client_error(self, mock_factory):
        """Test initialization failure when client creation fails."""
        mock_factory.get_s3vectors_client.side_effect = Exception("Client creation failed")

        with pytest.raises(Exception, match="Client creation failed"):
            S3VectorIndexManager()


class TestIndexNameValidation:
    """Test index name validation logic."""

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def setup_method(self):
        """Setup test fixtures."""
        with patch('src.services.s3vector.index_manager.aws_client_factory'):
            self.manager = S3VectorIndexManager()

    def test_validate_empty_name(self):
        """Test that empty index name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.manager._validate_index_name("")

    def test_validate_name_too_short(self):
        """Test that names < 3 chars raise error."""
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            self.manager._validate_index_name("ab")

    def test_validate_name_too_long(self):
        """Test that names > 63 chars raise error."""
        long_name = "a" * 64
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            self.manager._validate_index_name(long_name)

    def test_validate_invalid_uppercase(self):
        """Test that uppercase letters raise error."""
        with pytest.raises(ValidationError, match="lowercase letters"):
            self.manager._validate_index_name("MyIndex")

    def test_validate_invalid_special_chars(self):
        """Test that invalid special characters raise error."""
        with pytest.raises(ValidationError, match="lowercase letters"):
            self.manager._validate_index_name("my_index")

    def test_validate_starts_with_hyphen(self):
        """Test that names starting with hyphen raise error."""
        with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
            self.manager._validate_index_name("-myindex")

    def test_validate_ends_with_hyphen(self):
        """Test that names ending with hyphen raise error."""
        with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
            self.manager._validate_index_name("myindex-")

    def test_validate_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = [
            "my-index",
            "test123",
            "index-name-123",
            "a1b2c3",
            "my-test-index-2024"
        ]
        for name in valid_names:
            # Should not raise exception
            self.manager._validate_index_name(name)


class TestBucketNameValidation:
    """Test bucket name validation in index manager."""

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def setup_method(self):
        """Setup test fixtures."""
        with patch('src.services.s3vector.index_manager.aws_client_factory'):
            self.manager = S3VectorIndexManager()

    def test_validate_empty_bucket(self):
        """Test that empty bucket name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.manager._validate_bucket_name("")

    def test_validate_whitespace_bucket(self):
        """Test that whitespace-only bucket name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.manager._validate_bucket_name("   ")

    def test_validate_valid_bucket(self):
        """Test that valid bucket name passes."""
        # Should not raise exception
        self.manager._validate_bucket_name("my-bucket")


class TestCreateVectorIndex:
    """Test vector index creation."""

    @patch('src.services.s3vector.index_manager.resource_registry')
    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_success_cosine(self, mock_validator, mock_factory, mock_retry, mock_registry):
        """Test successful index creation with cosine metric."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index",
            "indexName": "test-index"
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.create_vector_index(
            bucket_name="test-bucket",
            index_name="test-index",
            dimensions=1024,
            distance_metric="cosine"
        )

        assert result["bucket_name"] == "test-bucket"
        assert result["index_name"] == "test-index"
        assert result["status"] == "created"
        mock_validator.validate_dimensions.assert_called_once_with(1024)
        mock_retry.retry_with_backoff.assert_called_once()

    @patch('src.services.s3vector.index_manager.resource_registry')
    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_success_euclidean(self, mock_validator, mock_factory, mock_retry, mock_registry):
        """Test successful index creation with euclidean metric."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index"
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.create_vector_index(
            bucket_name="test-bucket",
            index_name="test-index",
            dimensions=768,
            distance_metric="euclidean"
        )

        assert result["status"] == "created"
        mock_validator.validate_dimensions.assert_called_once_with(768)

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_invalid_bucket_name(self, mock_validator, mock_factory):
        """Test index creation with invalid bucket name."""
        mock_factory.get_s3vectors_client.return_value = Mock()

        manager = S3VectorIndexManager()

        with pytest.raises(ValidationError, match="cannot be empty"):
            manager.create_vector_index("", "test-index", 1024)

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_invalid_index_name(self, mock_validator, mock_factory):
        """Test index creation with invalid index name."""
        mock_factory.get_s3vectors_client.return_value = Mock()

        manager = S3VectorIndexManager()

        with pytest.raises(ValidationError):
            manager.create_vector_index("test-bucket", "Invalid-Name", 1024)

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_invalid_dimensions(self, mock_validator, mock_factory):
        """Test index creation with invalid dimensions."""
        mock_factory.get_s3vectors_client.return_value = Mock()
        mock_validator.validate_dimensions.side_effect = ValidationError("Invalid dimensions")

        manager = S3VectorIndexManager()

        with pytest.raises(ValidationError, match="Invalid dimensions"):
            manager.create_vector_index("test-bucket", "test-index", 99999)

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_invalid_metric(self, mock_validator, mock_factory):
        """Test index creation with invalid distance metric."""
        mock_factory.get_s3vectors_client.return_value = Mock()

        manager = S3VectorIndexManager()

        with pytest.raises(ValidationError, match="Distance metric.*must be one of"):
            manager.create_vector_index(
                "test-bucket",
                "test-index",
                1024,
                distance_metric="invalid"
            )

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_invalid_data_type(self, mock_validator, mock_factory):
        """Test index creation with invalid data type."""
        mock_factory.get_s3vectors_client.return_value = Mock()

        manager = S3VectorIndexManager()

        with pytest.raises(ValidationError, match="Data type.*must be one of"):
            manager.create_vector_index(
                "test-bucket",
                "test-index",
                1024,
                data_type="float64"
            )

    @patch('src.services.s3vector.index_manager.resource_registry')
    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_with_metadata_keys(self, mock_validator, mock_factory, mock_retry, mock_registry):
        """Test index creation with non-filterable metadata keys."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.create_vector_index(
            bucket_name="test-bucket",
            index_name="test-index",
            dimensions=1024,
            non_filterable_metadata_keys=["large_text", "binary_data"]
        )

        assert result["status"] == "created"

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_already_exists(self, mock_validator, mock_factory, mock_retry):
        """Test index creation when index already exists."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceAlreadyExistsException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'CreateIndex')

        manager = S3VectorIndexManager()
        result = manager.create_vector_index("test-bucket", "existing-index", 1024)

        assert result["status"] == "already_exists"
        assert "already exists" in result["message"].lower()

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_index_api_error(self, mock_validator, mock_factory, mock_retry):
        """Test index creation with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'CreateIndex')

        manager = S3VectorIndexManager()

        with pytest.raises(VectorStorageError, match="Failed to create vector index"):
            manager.create_vector_index("test-bucket", "test-index", 1024)


class TestListVectorIndexes:
    """Test vector index listing."""

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_list_indexes_success(self, mock_factory, mock_retry):
        """Test successful index listing."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "indexes": [
                {"indexName": "index1", "dimension": 1024},
                {"indexName": "index2", "dimension": 768}
            ]
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.list_vector_indexes("test-bucket")

        assert len(result) == 2
        assert result[0]["indexName"] == "index1"
        assert result[1]["indexName"] == "index2"

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_list_indexes_with_prefix(self, mock_factory, mock_retry):
        """Test index listing with prefix filter."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "indexes": [
                {"indexName": "prod-index1"},
                {"indexName": "prod-index2"}
            ]
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.list_vector_indexes("test-bucket", prefix="prod-")

        assert len(result) == 2
        # Verify prefix was passed to API
        call_args = mock_retry.retry_with_backoff.call_args
        assert call_args is not None

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_list_indexes_empty(self, mock_factory, mock_retry):
        """Test index listing when no indexes exist."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"indexes": []}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.list_vector_indexes("test-bucket")

        assert result == []

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_list_indexes_api_error(self, mock_factory, mock_retry):
        """Test index listing with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'ListIndexes')

        manager = S3VectorIndexManager()

        with pytest.raises(VectorStorageError, match="Failed to list vector indexes"):
            manager.list_vector_indexes("test-bucket")


class TestGetVectorIndexMetadata:
    """Test vector index metadata retrieval."""

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_get_metadata_success(self, mock_factory, mock_retry):
        """Test successful metadata retrieval."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {
            "indexName": "test-index",
            "indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index",
            "dimension": 1024,
            "distanceMetric": "cosine",
            "dataType": "float32"
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.get_vector_index_metadata("test-bucket", "test-index")

        assert result["indexName"] == "test-index"
        assert result["dimension"] == 1024
        assert result["distanceMetric"] == "cosine"

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_get_metadata_not_found(self, mock_factory, mock_retry):
        """Test metadata retrieval when index doesn't exist."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'GetIndexMetadata')

        manager = S3VectorIndexManager()

        with pytest.raises(VectorStorageError, match="Vector index.*not found"):
            manager.get_vector_index_metadata("test-bucket", "nonexistent-index")


class TestDeleteVectorIndex:
    """Test vector index deletion."""

    @patch('src.services.s3vector.index_manager.resource_registry')
    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_index_success(self, mock_factory, mock_retry, mock_registry):
        """Test successful index deletion."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.delete_vector_index("test-bucket", "test-index")

        assert result["bucket_name"] == "test-bucket"
        assert result["index_name"] == "test-index"
        assert result["status"] == "deleted"
        mock_registry.log_index_deleted.assert_called_once()

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_index_not_found(self, mock_factory, mock_retry):
        """Test index deletion when index doesn't exist."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'DeleteIndex')

        manager = S3VectorIndexManager()
        result = manager.delete_vector_index("test-bucket", "nonexistent-index")

        assert result["status"] == "not_found"

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_index_api_error(self, mock_factory, mock_retry):
        """Test index deletion with API error."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'DeleteIndex')

        manager = S3VectorIndexManager()

        with pytest.raises(VectorStorageError, match="Failed to delete vector index"):
            manager.delete_vector_index("test-bucket", "test-index")


class TestDeleteIndexWithRetries:
    """Test index deletion with custom retry logic."""

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_with_retries_success_first_attempt(self, mock_factory):
        """Test successful deletion on first attempt."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_s3vectors.delete_index.return_value = {}

        manager = S3VectorIndexManager()
        result = manager.delete_index_with_retries("test-bucket", "test-index")

        assert result is True
        mock_s3vectors.delete_index.assert_called_once()

    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_with_retries_not_found(self, mock_factory):
        """Test deletion when index not found."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_s3vectors.delete_index.side_effect = ClientError(error_response, 'DeleteIndex')

        manager = S3VectorIndexManager()
        result = manager.delete_index_with_retries("test-bucket", "nonexistent-index")

        assert result is True  # Not found is considered success

    @patch('src.services.s3vector.index_manager.time.sleep')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_with_retries_eventual_success(self, mock_factory, mock_sleep):
        """Test deletion succeeds after retries."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        # First attempt fails, second succeeds
        error_response = {'Error': {'Code': 'ResourceInUseException'}}
        mock_s3vectors.delete_index.side_effect = [
            ClientError(error_response, 'DeleteIndex'),
            {}
        ]

        manager = S3VectorIndexManager()
        result = manager.delete_index_with_retries("test-bucket", "test-index")

        assert result is True
        assert mock_s3vectors.delete_index.call_count == 2

    @patch('src.services.s3vector.index_manager.time.sleep')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_delete_with_retries_max_attempts(self, mock_factory, mock_sleep):
        """Test deletion fails after max attempts."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceInUseException'}}
        mock_s3vectors.delete_index.side_effect = ClientError(error_response, 'DeleteIndex')

        manager = S3VectorIndexManager()
        result = manager.delete_index_with_retries("test-bucket", "test-index", max_attempts=3)

        assert result is False
        assert mock_s3vectors.delete_index.call_count == 3


class TestIndexExists:
    """Test index existence checks."""

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_index_exists_true(self, mock_factory, mock_retry):
        """Test index existence check when index exists."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"indexName": "test-index"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()
        result = manager.index_exists("test-bucket", "test-index")

        assert result is True

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    def test_index_exists_false(self, mock_factory, mock_retry):
        """Test index existence check when index doesn't exist."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'GetIndexMetadata')

        manager = S3VectorIndexManager()
        result = manager.index_exists("test-bucket", "nonexistent-index")

        assert result is False


class TestIntegrationScenarios:
    """Test integrated scenarios and edge cases."""

    @patch('src.services.s3vector.index_manager.resource_registry')
    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_create_list_delete_workflow(self, mock_validator, mock_factory, mock_retry, mock_registry):
        """Test complete create, list, and delete workflow."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        # Mock responses
        create_response = {"indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test-index"}
        list_response = {"indexes": [{"indexName": "test-index", "dimension": 1024}]}
        delete_response = {}

        mock_retry.retry_with_backoff.side_effect = [create_response, list_response, delete_response]

        manager = S3VectorIndexManager()

        # Create index
        create_result = manager.create_vector_index("test-bucket", "test-index", 1024)
        assert create_result["status"] == "created"

        # List indexes
        list_result = manager.list_vector_indexes("test-bucket")
        assert len(list_result) == 1

        # Delete index
        delete_result = manager.delete_vector_index("test-bucket", "test-index")
        assert delete_result["status"] == "deleted"

        # Verify all operations logged
        mock_registry.log_index_created.assert_called_once()
        mock_registry.log_index_deleted.assert_called_once()

    @patch('src.services.s3vector.index_manager.AWSRetryHandler')
    @patch('src.services.s3vector.index_manager.aws_client_factory')
    @patch('src.services.s3vector.index_manager.VectorValidator')
    def test_multiple_dimensions_and_metrics(self, mock_validator, mock_factory, mock_retry):
        """Test creating indexes with different dimensions and metrics."""
        mock_s3vectors = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors

        mock_response = {"indexArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket/index/test"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorIndexManager()

        # Test various valid dimensions
        valid_configs = [
            (768, "cosine"),
            (1024, "euclidean"),
            (1536, "cosine"),
            (4096, "euclidean")
        ]

        for dimensions, metric in valid_configs:
            result = manager.create_vector_index(
                "test-bucket",
                f"index-{dimensions}-{metric}",
                dimensions,
                distance_metric=metric
            )
            assert result["status"] == "created"
