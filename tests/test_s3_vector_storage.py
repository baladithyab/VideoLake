"""
Unit tests for S3 Vector Storage Manager.

Tests bucket creation, validation, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError, ValidationError


class TestS3VectorStorageManager:
    """Test cases for S3VectorStorageManager."""
    
    @pytest.fixture
    def mock_s3vectors_client(self):
        """Mock S3 Vectors client."""
        return Mock()
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        return Mock()
    
    @pytest.fixture
    def storage_manager(self, mock_s3vectors_client, mock_s3_client):
        """Create storage manager with mocked clients."""
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = mock_s3_client
            return S3VectorStorageManager()


class TestBucketNameValidation:
    """Test bucket name validation logic."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory'):
            return S3VectorStorageManager()
    
    def test_valid_bucket_names(self, storage_manager):
        """Test that valid bucket names pass validation."""
        valid_names = [
            "media-embeddings",
            "test-bucket-123",
            "my-vector-bucket",
            "abc",  # minimum length
            "a" * 63,  # maximum length
            "bucket123",
            "123bucket"
        ]
        
        for name in valid_names:
            # Should not raise any exception
            storage_manager._validate_bucket_name(name)
    
    def test_empty_bucket_name(self, storage_manager):
        """Test that empty bucket name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_bucket_name("")
        
        assert exc_info.value.error_code == "EMPTY_BUCKET_NAME"
    
    def test_bucket_name_too_short(self, storage_manager):
        """Test that bucket name shorter than 3 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_bucket_name("ab")
        
        assert exc_info.value.error_code == "INVALID_BUCKET_NAME_LENGTH"
        assert exc_info.value.error_details["length"] == 2
    
    def test_bucket_name_too_long(self, storage_manager):
        """Test that bucket name longer than 63 characters raises ValidationError."""
        long_name = "a" * 64
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_bucket_name(long_name)
        
        assert exc_info.value.error_code == "INVALID_BUCKET_NAME_LENGTH"
        assert exc_info.value.error_details["length"] == 64
    
    def test_invalid_characters(self, storage_manager):
        """Test that invalid characters in bucket name raise ValidationError."""
        invalid_names = [
            "Bucket-Name",  # uppercase
            "bucket_name",  # underscore
            "bucket.name",  # dot
            "bucket name",  # space
            "bucket@name",  # special character
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_bucket_name(name)
            assert exc_info.value.error_code == "INVALID_BUCKET_NAME_CHARS"
    
    def test_hyphen_at_start_or_end(self, storage_manager):
        """Test that hyphens at start or end raise ValidationError."""
        invalid_names = ["-bucket-name", "bucket-name-"]
        
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_bucket_name(name)
            assert exc_info.value.error_code == "INVALID_BUCKET_NAME_HYPHEN"
    
    def test_consecutive_hyphens(self, storage_manager):
        """Test that consecutive hyphens raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_bucket_name("bucket--name")
        
        assert exc_info.value.error_code == "INVALID_BUCKET_NAME_CONSECUTIVE_HYPHENS"


class TestCreateVectorBucket:
    """Test vector bucket creation functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_bucket_creation_sse_s3(self, storage_manager):
        """Test successful bucket creation with SSE-S3 encryption."""
        bucket_name = "test-vector-bucket"
        
        # Mock successful response
        storage_manager.s3vectors_client.create_vector_bucket.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.create_vector_bucket(bucket_name)
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.create_vector_bucket.assert_called_once_with(
            vectorBucketName=bucket_name,
            encryptionConfiguration={'sseType': 'SSE-S3'}
        )
        
        # Verify the result
        assert result['bucket_name'] == bucket_name
        assert result['status'] == 'created'
        assert result['encryption_type'] == 'SSE-S3'
        assert result['kms_key_arn'] is None
    
    def test_successful_bucket_creation_sse_kms(self, storage_manager):
        """Test successful bucket creation with SSE-KMS encryption."""
        bucket_name = "test-vector-bucket"
        kms_key_arn = "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
        
        # Mock successful response
        storage_manager.s3vectors_client.create_vector_bucket.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.create_vector_bucket(
            bucket_name, 
            encryption_type="SSE-KMS",
            kms_key_arn=kms_key_arn
        )
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.create_vector_bucket.assert_called_once_with(
            vectorBucketName=bucket_name,
            encryptionConfiguration={
                'sseType': 'SSE-KMS',
                'kmsKeyArn': kms_key_arn
            }
        )
        
        # Verify the result
        assert result['bucket_name'] == bucket_name
        assert result['status'] == 'created'
        assert result['encryption_type'] == 'SSE-KMS'
        assert result['kms_key_arn'] == kms_key_arn
    
    def test_bucket_already_exists(self, storage_manager):
        """Test handling when bucket already exists."""
        bucket_name = "existing-bucket"
        
        # Mock ConflictException
        error_response = {
            'Error': {
                'Code': 'ConflictException',
                'Message': 'Vector bucket already exists'
            }
        }
        storage_manager.s3vectors_client.create_vector_bucket.side_effect = ClientError(
            error_response, 'CreateVectorBucket'
        )
        
        result = storage_manager.create_vector_bucket(bucket_name)
        
        assert result['bucket_name'] == bucket_name
        assert result['status'] == 'already_exists'
        assert result['message'] == 'Bucket already exists'
    
    def test_access_denied_error(self, storage_manager):
        """Test handling of access denied errors."""
        bucket_name = "test-bucket"
        
        # Mock AccessDeniedException
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.create_vector_bucket.side_effect = ClientError(
            error_response, 'CreateVectorBucket'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.create_vector_bucket(bucket_name)
        
        assert exc_info.value.error_code == "ACCESS_DENIED"
        assert "s3vectors:CreateVectorBucket" in str(exc_info.value.error_details)
    
    def test_service_quota_exceeded(self, storage_manager):
        """Test handling of service quota exceeded errors."""
        bucket_name = "test-bucket"
        
        # Mock ServiceQuotaExceededException
        error_response = {
            'Error': {
                'Code': 'ServiceQuotaExceededException',
                'Message': 'Service quota exceeded'
            }
        }
        storage_manager.s3vectors_client.create_vector_bucket.side_effect = ClientError(
            error_response, 'CreateVectorBucket'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.create_vector_bucket(bucket_name)
        
        assert exc_info.value.error_code == "QUOTA_EXCEEDED"
    
    def test_invalid_encryption_type(self, storage_manager):
        """Test validation of encryption type."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.create_vector_bucket("test-bucket", encryption_type="INVALID")
        
        assert exc_info.value.error_code == "INVALID_ENCRYPTION_TYPE"
    
    def test_missing_kms_key_for_sse_kms(self, storage_manager):
        """Test that KMS key is required for SSE-KMS encryption."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.create_vector_bucket("test-bucket", encryption_type="SSE-KMS")
        
        assert exc_info.value.error_code == "MISSING_KMS_KEY_ARN"
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_logic_with_throttling(self, mock_sleep, storage_manager):
        """Test retry logic when encountering throttling errors."""
        bucket_name = "test-bucket"
        
        # Mock throttling error followed by success
        throttling_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'CreateVectorBucket'
        )
        success_response = {'ResponseMetadata': {'HTTPStatusCode': 200}}
        
        storage_manager.s3vectors_client.create_vector_bucket.side_effect = [
            throttling_error,
            success_response
        ]
        
        result = storage_manager.create_vector_bucket(bucket_name)
        
        # Verify retry happened
        assert storage_manager.s3vectors_client.create_vector_bucket.call_count == 2
        assert result['status'] == 'created'
        mock_sleep.assert_called_once()  # Verify sleep was called for backoff
    
    def test_unexpected_error(self, storage_manager):
        """Test handling of unexpected errors."""
        bucket_name = "test-bucket"
        
        # Mock unexpected exception
        storage_manager.s3vectors_client.create_vector_bucket.side_effect = Exception("Unexpected error")
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.create_vector_bucket(bucket_name)
        
        assert exc_info.value.error_code == "UNEXPECTED_ERROR"
        assert "Unexpected error" in str(exc_info.value)


class TestGetVectorBucket:
    """Test getting vector bucket attributes."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_get_bucket(self, storage_manager):
        """Test successful retrieval of bucket attributes."""
        bucket_name = "test-bucket"
        expected_response = {
            'vectorBucketName': bucket_name,
            'encryptionConfiguration': {'sseType': 'SSE-S3'},
            'creationDate': '2025-01-01T00:00:00Z'
        }
        
        storage_manager.s3vectors_client.get_vector_bucket.return_value = expected_response
        
        result = storage_manager.get_vector_bucket(bucket_name)
        
        storage_manager.s3vectors_client.get_vector_bucket.assert_called_once_with(
            vectorBucketName=bucket_name
        )
        assert result == expected_response
    
    def test_bucket_not_found(self, storage_manager):
        """Test handling when bucket does not exist."""
        bucket_name = "nonexistent-bucket"
        
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist'
            }
        }
        storage_manager.s3vectors_client.get_vector_bucket.side_effect = ClientError(
            error_response, 'GetVectorBucket'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.get_vector_bucket(bucket_name)
        
        assert exc_info.value.error_code == "BUCKET_NOT_FOUND"


class TestListVectorBuckets:
    """Test listing vector buckets."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_list_buckets(self, storage_manager):
        """Test successful listing of vector buckets."""
        expected_buckets = [
            {'vectorBucketName': 'bucket1', 'creationDate': '2025-01-01T00:00:00Z'},
            {'vectorBucketName': 'bucket2', 'creationDate': '2025-01-01T01:00:00Z'}
        ]
        
        storage_manager.s3vectors_client.list_vector_buckets.return_value = {
            'vectorBuckets': expected_buckets
        }
        
        result = storage_manager.list_vector_buckets()
        
        storage_manager.s3vectors_client.list_vector_buckets.assert_called_once()
        assert result == expected_buckets
    
    def test_empty_bucket_list(self, storage_manager):
        """Test handling when no buckets exist."""
        storage_manager.s3vectors_client.list_vector_buckets.return_value = {
            'vectorBuckets': []
        }
        
        result = storage_manager.list_vector_buckets()
        
        assert result == []


class TestBucketExists:
    """Test bucket existence checking."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_bucket_exists_true(self, storage_manager):
        """Test when bucket exists."""
        bucket_name = "existing-bucket"
        
        storage_manager.s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucketName': bucket_name
        }
        
        result = storage_manager.bucket_exists(bucket_name)
        
        assert result is True
    
    def test_bucket_exists_false(self, storage_manager):
        """Test when bucket does not exist."""
        bucket_name = "nonexistent-bucket"
        
        error_response = {
            'Error': {
                'Code': 'NoSuchBucket',
                'Message': 'The specified bucket does not exist'
            }
        }
        storage_manager.s3vectors_client.get_vector_bucket.side_effect = ClientError(
            error_response, 'GetVectorBucket'
        )
        
        result = storage_manager.bucket_exists(bucket_name)
        
        assert result is False
    
    def test_bucket_exists_other_error_propagates(self, storage_manager):
        """Test that non-bucket-not-found errors are propagated."""
        bucket_name = "test-bucket"
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.get_vector_bucket.side_effect = ClientError(
            error_response, 'GetVectorBucket'
        )
        
        with pytest.raises(VectorStorageError):
            storage_manager.bucket_exists(bucket_name)


if __name__ == "__main__":
    pytest.main([__file__])