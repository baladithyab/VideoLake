"""
Unit tests for S3VectorBucketManager.

Tests bucket lifecycle operations including:
- Bucket creation with various encryption types
- Bucket retrieval and listing
- Bucket deletion with cascade options
- Bucket existence checks
- Validation logic
- Error handling and retries
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from botocore.exceptions import ClientError

from src.services.s3vector.bucket_manager import S3VectorBucketManager, _normalize_encryption_type
from src.exceptions import VectorStorageError, ValidationError


class TestNormalizeEncryptionType:
    """Test the encryption type normalization helper function."""

    def test_normalize_none(self):
        """Test that None is returned as None."""
        assert _normalize_encryption_type(None) is None

    def test_normalize_sse_s3(self):
        """Test SSE-S3 normalization."""
        assert _normalize_encryption_type("SSE-S3") == "AES256"
        assert _normalize_encryption_type("sse-s3") == "AES256"
        assert _normalize_encryption_type("AES256") == "AES256"
        assert _normalize_encryption_type("aes256") == "AES256"

    def test_normalize_sse_kms(self):
        """Test SSE-KMS normalization."""
        assert _normalize_encryption_type("SSE-KMS") == "aws:kms"
        assert _normalize_encryption_type("sse-kms") == "aws:kms"
        assert _normalize_encryption_type("aws:kms") == "aws:kms"

    def test_normalize_passthrough(self):
        """Test that unknown values are passed through."""
        assert _normalize_encryption_type("custom-type") == "custom-type"


class TestS3VectorBucketManagerInit:
    """Test S3VectorBucketManager initialization."""

    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_init_success(self, mock_factory):
        """Test successful initialization."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        manager = S3VectorBucketManager()

        assert manager.s3vectors_client == mock_s3vectors
        assert manager.s3_client == mock_s3
        mock_factory.get_s3vectors_client.assert_called_once()
        mock_factory.get_s3_client.assert_called_once()

    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_init_client_error(self, mock_factory):
        """Test initialization failure when client creation fails."""
        mock_factory.get_s3vectors_client.side_effect = Exception("Client creation failed")

        with pytest.raises(Exception, match="Client creation failed"):
            S3VectorBucketManager()


class TestBucketNameValidation:
    """Test bucket name validation logic."""

    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def setup_method(self):
        """Setup test fixtures."""
        with patch('src.services.s3vector.bucket_manager.aws_client_factory'):
            self.manager = S3VectorBucketManager()

    def test_validate_empty_name(self):
        """Test that empty bucket name raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            self.manager._validate_bucket_name("")

    def test_validate_name_too_short(self):
        """Test that names < 3 chars raise error."""
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            self.manager._validate_bucket_name("ab")

    def test_validate_name_too_long(self):
        """Test that names > 63 chars raise error."""
        long_name = "a" * 64
        with pytest.raises(ValidationError, match="between 3 and 63 characters"):
            self.manager._validate_bucket_name(long_name)

    def test_validate_invalid_uppercase(self):
        """Test that uppercase letters raise error."""
        with pytest.raises(ValidationError, match="lowercase letters"):
            self.manager._validate_bucket_name("MyBucket")

    def test_validate_invalid_special_chars(self):
        """Test that invalid special characters raise error."""
        with pytest.raises(ValidationError, match="lowercase letters"):
            self.manager._validate_bucket_name("my_bucket")

    def test_validate_starts_with_hyphen(self):
        """Test that names starting with hyphen raise error."""
        with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
            self.manager._validate_bucket_name("-mybucket")

    def test_validate_ends_with_hyphen(self):
        """Test that names ending with hyphen raise error."""
        with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
            self.manager._validate_bucket_name("mybucket-")

    def test_validate_consecutive_hyphens(self):
        """Test that consecutive hyphens raise error."""
        with pytest.raises(ValidationError, match="consecutive hyphens"):
            self.manager._validate_bucket_name("my--bucket")

    def test_validate_valid_names(self):
        """Test that valid names pass validation."""
        valid_names = [
            "my-bucket",
            "test123",
            "bucket-name-123",
            "a1b2c3",
            "my-test-bucket-2024"
        ]
        for name in valid_names:
            # Should not raise exception
            self.manager._validate_bucket_name(name)


class TestCreateVectorBucket:
    """Test vector bucket creation."""

    @patch('src.services.s3vector.bucket_manager.resource_registry')
    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_bucket_sse_s3_success(self, mock_factory, mock_retry, mock_registry):
        """Test successful bucket creation with SSE-S3 encryption."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        # Mock successful API response
        mock_response = {"vectorBucketArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.create_vector_bucket("test-bucket", encryption_type="SSE-S3")

        # Verify result
        assert result["bucket_name"] == "test-bucket"
        assert result["status"] == "created"
        assert "response" in result

        # Verify retry handler was called
        mock_retry.retry_with_backoff.assert_called_once()

        # Verify resource registry was updated
        mock_registry.log_vector_bucket_created.assert_called_once()

    @patch('src.services.s3vector.bucket_manager.resource_registry')
    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_bucket_sse_kms_success(self, mock_factory, mock_retry, mock_registry):
        """Test successful bucket creation with SSE-KMS encryption."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        kms_key = "arn:aws:kms:us-east-1:123:key/abc-123"
        mock_response = {"vectorBucketArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.create_vector_bucket("test-bucket", encryption_type="SSE-KMS", kms_key_arn=kms_key)

        assert result["bucket_name"] == "test-bucket"
        assert result["status"] == "created"
        mock_retry.retry_with_backoff.assert_called_once()

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_bucket_invalid_name(self, mock_factory, mock_retry):
        """Test bucket creation with invalid name."""
        mock_factory.get_s3vectors_client.return_value = Mock()
        mock_factory.get_s3_client.return_value = Mock()

        manager = S3VectorBucketManager()

        with pytest.raises(ValidationError):
            manager.create_vector_bucket("Invalid-Name-With-Upper")

    @patch('src.services.s3vector.bucket_manager.resource_registry')
    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_bucket_already_exists(self, mock_factory, mock_retry, mock_registry):
        """Test bucket creation when bucket already exists."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        # Mock ResourceAlreadyExistsException
        error_response = {'Error': {'Code': 'ResourceAlreadyExistsException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'CreateVectorBucket')

        manager = S3VectorBucketManager()
        result = manager.create_vector_bucket("existing-bucket")

        assert result["status"] == "already_exists"
        assert "already exists" in result["message"].lower()

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_bucket_api_error(self, mock_factory, mock_retry):
        """Test bucket creation with API error."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'CreateVectorBucket')

        manager = S3VectorBucketManager()

        with pytest.raises(VectorStorageError, match="Failed to create vector bucket"):
            manager.create_vector_bucket("test-bucket")


class TestGetVectorBucket:
    """Test vector bucket retrieval."""

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_get_bucket_success(self, mock_factory, mock_retry):
        """Test successful bucket retrieval."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        mock_response = {
            "vectorBucketName": "test-bucket",
            "vectorBucketArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket",
            "encryptionConfiguration": {"sseType": "AES256"}
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.get_vector_bucket("test-bucket")

        assert result["vectorBucketName"] == "test-bucket"
        assert "vectorBucketArn" in result
        mock_retry.retry_with_backoff.assert_called_once()

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_get_bucket_not_found(self, mock_factory, mock_retry):
        """Test bucket retrieval when bucket doesn't exist."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'GetVectorBucket')

        manager = S3VectorBucketManager()

        with pytest.raises(VectorStorageError, match="Vector bucket.*not found"):
            manager.get_vector_bucket("nonexistent-bucket")


class TestListVectorBuckets:
    """Test vector bucket listing."""

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_list_buckets_success(self, mock_factory, mock_retry):
        """Test successful bucket listing."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        mock_response = {
            "vectorBuckets": [
                {"vectorBucketName": "bucket1", "vectorBucketArn": "arn1"},
                {"vectorBucketName": "bucket2", "vectorBucketArn": "arn2"}
            ]
        }
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.list_vector_buckets()

        assert len(result) == 2
        assert result[0]["vectorBucketName"] == "bucket1"
        assert result[1]["vectorBucketName"] == "bucket2"

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_list_buckets_empty(self, mock_factory, mock_retry):
        """Test bucket listing when no buckets exist."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        mock_response = {"vectorBuckets": []}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.list_vector_buckets()

        assert result == []

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_list_buckets_api_error(self, mock_factory, mock_retry):
        """Test bucket listing with API error."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'ListVectorBuckets')

        manager = S3VectorBucketManager()

        with pytest.raises(VectorStorageError, match="Failed to list vector buckets"):
            manager.list_vector_buckets()


class TestBucketExists:
    """Test bucket existence checks."""

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_bucket_exists_true(self, mock_factory, mock_retry):
        """Test bucket existence check when bucket exists."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        mock_response = {"vectorBucketName": "test-bucket"}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.bucket_exists("test-bucket")

        assert result is True

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_bucket_exists_false(self, mock_factory, mock_retry):
        """Test bucket existence check when bucket doesn't exist."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'GetVectorBucket')

        manager = S3VectorBucketManager()
        result = manager.bucket_exists("nonexistent-bucket")

        assert result is False


class TestDeleteVectorBucket:
    """Test vector bucket deletion."""

    @patch('src.services.s3vector.bucket_manager.resource_registry')
    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_delete_bucket_success(self, mock_factory, mock_retry, mock_registry):
        """Test successful bucket deletion."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        mock_response = {}
        mock_retry.retry_with_backoff.return_value = mock_response

        manager = S3VectorBucketManager()
        result = manager.delete_vector_bucket("test-bucket")

        assert result["bucket_name"] == "test-bucket"
        assert result["status"] == "deleted"
        mock_registry.log_vector_bucket_deleted.assert_called_once()

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_delete_bucket_not_found(self, mock_factory, mock_retry):
        """Test bucket deletion when bucket doesn't exist."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'ResourceNotFoundException'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'DeleteVectorBucket')

        manager = S3VectorBucketManager()
        result = manager.delete_vector_bucket("nonexistent-bucket")

        assert result["status"] == "not_found"

    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_delete_bucket_api_error(self, mock_factory, mock_retry):
        """Test bucket deletion with API error."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        error_response = {'Error': {'Code': 'InternalError', 'Message': 'Service error'}}
        mock_retry.retry_with_backoff.side_effect = ClientError(error_response, 'DeleteVectorBucket')

        manager = S3VectorBucketManager()

        with pytest.raises(VectorStorageError, match="Failed to delete vector bucket"):
            manager.delete_vector_bucket("test-bucket")


class TestIntegrationScenarios:
    """Test integrated scenarios and edge cases."""

    @patch('src.services.s3vector.bucket_manager.resource_registry')
    @patch('src.services.s3vector.bucket_manager.AWSRetryHandler')
    @patch('src.services.s3vector.bucket_manager.aws_client_factory')
    def test_create_and_delete_workflow(self, mock_factory, mock_retry, mock_registry):
        """Test complete create and delete workflow."""
        mock_s3vectors = Mock()
        mock_s3 = Mock()
        mock_factory.get_s3vectors_client.return_value = mock_s3vectors
        mock_factory.get_s3_client.return_value = mock_s3

        # Mock create response
        create_response = {"vectorBucketArn": "arn:aws:s3vectors:us-east-1:123:bucket/test-bucket"}
        delete_response = {}

        mock_retry.retry_with_backoff.side_effect = [create_response, delete_response]

        manager = S3VectorBucketManager()

        # Create bucket
        create_result = manager.create_vector_bucket("test-bucket")
        assert create_result["status"] == "created"

        # Delete bucket
        delete_result = manager.delete_vector_bucket("test-bucket")
        assert delete_result["status"] == "deleted"

        # Verify both operations logged
        mock_registry.log_vector_bucket_created.assert_called_once()
        mock_registry.log_vector_bucket_deleted.assert_called_once()
