"""
Unit tests for S3 Vector Storage Manager.

Tests bucket creation, validation, error handling, and edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
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
            encryptionConfiguration={'sseType': 'AES256'}
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
                'sseType': 'aws:kms',
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


class TestIndexNameValidation:
    """Test index name validation logic."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory'):
            return S3VectorStorageManager()
    
    def test_valid_index_names(self, storage_manager):
        """Test that valid index names pass validation."""
        valid_names = [
            "text-embeddings",
            "video-index-123",
            "my-vector-index",
            "abc",  # minimum length
            "a" * 63,  # maximum length
            "index123",
            "123index"
        ]
        
        for name in valid_names:
            # Should not raise any exception
            storage_manager._validate_index_name(name)
    
    def test_empty_index_name(self, storage_manager):
        """Test that empty index name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_index_name("")
        
        assert exc_info.value.error_code == "EMPTY_INDEX_NAME"
    
    def test_index_name_too_short(self, storage_manager):
        """Test that index name shorter than 3 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_index_name("ab")
        
        assert exc_info.value.error_code == "INVALID_INDEX_NAME_LENGTH"
        assert exc_info.value.error_details["length"] == 2
    
    def test_index_name_too_long(self, storage_manager):
        """Test that index name longer than 63 characters raises ValidationError."""
        long_name = "a" * 64
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_index_name(long_name)
        
        assert exc_info.value.error_code == "INVALID_INDEX_NAME_LENGTH"
        assert exc_info.value.error_details["length"] == 64
    
    def test_invalid_characters_in_index_name(self, storage_manager):
        """Test that invalid characters in index name raise ValidationError."""
        invalid_names = [
            "Index-Name",  # uppercase
            "index_name",  # underscore
            "index.name",  # dot
            "index name",  # space
            "index@name",  # special character
        ]
        
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_index_name(name)
            assert exc_info.value.error_code == "INVALID_INDEX_NAME_CHARS"
    
    def test_hyphen_at_start_or_end_index(self, storage_manager):
        """Test that hyphens at start or end raise ValidationError."""
        invalid_names = ["-index-name", "index-name-"]
        
        for name in invalid_names:
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_index_name(name)
            assert exc_info.value.error_code == "INVALID_INDEX_NAME_HYPHEN"


class TestVectorDimensionsValidation:
    """Test vector dimensions validation logic."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory'):
            return S3VectorStorageManager()
    
    def test_valid_dimensions(self, storage_manager):
        """Test that valid dimensions pass validation."""
        valid_dimensions = [1, 128, 512, 1024, 1536, 4096]
        
        for dim in valid_dimensions:
            # Should not raise any exception
            storage_manager._validate_vector_dimensions(dim)
    
    def test_dimensions_too_small(self, storage_manager):
        """Test that dimensions less than 1 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_dimensions(0)
        
        assert exc_info.value.error_code == "INVALID_DIMENSIONS_RANGE"
        assert exc_info.value.error_details["dimensions"] == 0
    
    def test_dimensions_too_large(self, storage_manager):
        """Test that dimensions greater than 4096 raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_dimensions(4097)
        
        assert exc_info.value.error_code == "INVALID_DIMENSIONS_RANGE"
        assert exc_info.value.error_details["dimensions"] == 4097
    
    def test_non_integer_dimensions(self, storage_manager):
        """Test that non-integer dimensions raise ValidationError."""
        invalid_dimensions = [1.5, "1024", None, [1024]]
        
        for dim in invalid_dimensions:
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_vector_dimensions(dim)
            assert exc_info.value.error_code == "INVALID_DIMENSIONS_TYPE"


class TestCreateVectorIndex:
    """Test vector index creation functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_index_creation_default_params(self, storage_manager):
        """Test successful index creation with default parameters."""
        bucket_name = "test-bucket"
        index_name = "test-index"
        dimensions = 1024
        
        # Mock successful response
        storage_manager.s3vectors_client.create_index.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.create_vector_index(bucket_name, index_name, dimensions)
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.create_index.assert_called_once_with(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dimension=dimensions,
            distanceMetric="cosine",
            dataType="float32"
        )
        
        # Verify the result
        assert result['bucket_name'] == bucket_name
        assert result['index_name'] == index_name
        assert result['dimensions'] == dimensions
        assert result['distance_metric'] == "cosine"
        assert result['data_type'] == "float32"
        assert result['status'] == 'created'
    
    def test_successful_index_creation_custom_params(self, storage_manager):
        """Test successful index creation with custom parameters."""
        bucket_name = "test-bucket"
        index_name = "test-index"
        dimensions = 512
        distance_metric = "euclidean"
        non_filterable_keys = ["large_text", "binary_data"]
        
        # Mock successful response
        storage_manager.s3vectors_client.create_index.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.create_vector_index(
            bucket_name, 
            index_name, 
            dimensions,
            distance_metric=distance_metric,
            non_filterable_metadata_keys=non_filterable_keys
        )
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.create_index.assert_called_once_with(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dimension=dimensions,
            distanceMetric=distance_metric,
            dataType="float32",
            metadataConfiguration={
                "nonFilterableMetadataKeys": non_filterable_keys
            }
        )
        
        # Verify the result
        assert result['distance_metric'] == distance_metric
        assert result['non_filterable_metadata_keys'] == non_filterable_keys
    
    def test_index_already_exists(self, storage_manager):
        """Test handling when index already exists."""
        bucket_name = "test-bucket"
        index_name = "existing-index"
        dimensions = 1024
        
        # Mock ConflictException
        error_response = {
            'Error': {
                'Code': 'ConflictException',
                'Message': 'Vector index already exists'
            }
        }
        storage_manager.s3vectors_client.create_index.side_effect = ClientError(
            error_response, 'CreateIndex'
        )
        
        result = storage_manager.create_vector_index(bucket_name, index_name, dimensions)
        
        assert result['bucket_name'] == bucket_name
        assert result['index_name'] == index_name
        assert result['status'] == 'already_exists'
        assert result['message'] == 'Index already exists'
    
    def test_bucket_not_found_error(self, storage_manager):
        """Test handling when bucket does not exist."""
        bucket_name = "nonexistent-bucket"
        index_name = "test-index"
        dimensions = 1024
        
        # Mock NotFoundException
        error_response = {
            'Error': {
                'Code': 'NotFoundException',
                'Message': 'Vector bucket not found'
            }
        }
        storage_manager.s3vectors_client.create_index.side_effect = ClientError(
            error_response, 'CreateIndex'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.create_vector_index(bucket_name, index_name, dimensions)
        
        assert exc_info.value.error_code == "BUCKET_NOT_FOUND"
    
    def test_invalid_distance_metric(self, storage_manager):
        """Test validation of distance metric."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.create_vector_index(
                "test-bucket", "test-index", 1024, distance_metric="invalid"
            )
        
        assert exc_info.value.error_code == "INVALID_DISTANCE_METRIC"
    
    def test_invalid_data_type(self, storage_manager):
        """Test validation of data type."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.create_vector_index(
                "test-bucket", "test-index", 1024, data_type="float64"
            )
        
        assert exc_info.value.error_code == "INVALID_DATA_TYPE"


class TestListVectorIndexes:
    """Test listing vector indexes functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_list_indexes(self, storage_manager):
        """Test successful listing of vector indexes."""
        bucket_name = "test-bucket"
        expected_indexes = [
            {
                'indexName': 'text-embeddings',
                'indexArn': 'arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/text-embeddings',
                'creationTime': 1640995200,
                'vectorBucketName': bucket_name
            },
            {
                'indexName': 'video-embeddings',
                'indexArn': 'arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/video-embeddings',
                'creationTime': 1640995300,
                'vectorBucketName': bucket_name
            }
        ]
        
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': expected_indexes,
            'nextToken': None
        }
        
        result = storage_manager.list_vector_indexes(bucket_name)
        
        storage_manager.s3vectors_client.list_indexes.assert_called_once_with(
            vectorBucketName=bucket_name
        )
        
        assert result['bucket_name'] == bucket_name
        assert result['indexes'] == expected_indexes
        assert result['next_token'] is None
        assert result['count'] == 2
    
    def test_list_indexes_with_prefix(self, storage_manager):
        """Test listing indexes with prefix filter."""
        bucket_name = "test-bucket"
        prefix = "text"
        
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [],
            'nextToken': None
        }
        
        storage_manager.list_vector_indexes(bucket_name, prefix=prefix)
        
        storage_manager.s3vectors_client.list_indexes.assert_called_once_with(
            vectorBucketName=bucket_name,
            prefix=prefix
        )
    
    def test_list_indexes_with_pagination(self, storage_manager):
        """Test listing indexes with pagination parameters."""
        bucket_name = "test-bucket"
        max_results = 10
        next_token = "pagination-token"
        
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [],
            'nextToken': "next-pagination-token"
        }
        
        result = storage_manager.list_vector_indexes(
            bucket_name, 
            max_results=max_results,
            next_token=next_token
        )
        
        storage_manager.s3vectors_client.list_indexes.assert_called_once_with(
            vectorBucketName=bucket_name,
            maxResults=max_results,
            nextToken=next_token
        )
        
        assert result['next_token'] == "next-pagination-token"
    
    def test_invalid_max_results(self, storage_manager):
        """Test validation of max_results parameter."""
        bucket_name = "test-bucket"
        
        # Test invalid values
        invalid_values = [0, 501, -1, "10", None]
        
        for invalid_value in invalid_values[:-1]:  # Exclude None as it's valid
            with pytest.raises(ValidationError) as exc_info:
                storage_manager.list_vector_indexes(bucket_name, max_results=invalid_value)
            assert exc_info.value.error_code == "INVALID_MAX_RESULTS"
    
    def test_invalid_prefix(self, storage_manager):
        """Test validation of prefix parameter."""
        bucket_name = "test-bucket"
        
        # Test invalid prefix (too long)
        invalid_prefix = "a" * 64
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vector_indexes(bucket_name, prefix=invalid_prefix)
        assert exc_info.value.error_code == "INVALID_PREFIX"
    
    def test_bucket_not_found_in_list(self, storage_manager):
        """Test handling when bucket does not exist during listing."""
        bucket_name = "nonexistent-bucket"
        
        error_response = {
            'Error': {
                'Code': 'NotFoundException',
                'Message': 'Vector bucket not found'
            }
        }
        storage_manager.s3vectors_client.list_indexes.side_effect = ClientError(
            error_response, 'ListIndexes'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.list_vector_indexes(bucket_name)
        
        assert exc_info.value.error_code == "BUCKET_NOT_FOUND"


class TestGetVectorIndexMetadata:
    """Test getting vector index metadata functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_get_index_metadata(self, storage_manager):
        """Test successful retrieval of index metadata."""
        bucket_name = "test-bucket"
        index_name = "test-index"
        
        expected_index = {
            'indexName': index_name,
            'indexArn': f'arn:aws:s3vectors:us-west-2:123456789012:index/{bucket_name}/{index_name}',
            'creationTime': 1640995200,
            'vectorBucketName': bucket_name
        }
        
        # Mock the list_indexes call that's used internally
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [expected_index],
            'nextToken': None
        }
        
        result = storage_manager.get_vector_index_metadata(bucket_name, index_name)
        
        assert result['bucket_name'] == bucket_name
        assert result['index_name'] == index_name
        assert result['index_arn'] == expected_index['indexArn']
        assert result['creation_time'] == expected_index['creationTime']
        assert result['metadata'] == expected_index
    
    def test_index_not_found(self, storage_manager):
        """Test handling when index does not exist."""
        bucket_name = "test-bucket"
        index_name = "nonexistent-index"
        
        # Mock empty response (index not found)
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [],
            'nextToken': None
        }
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.get_vector_index_metadata(bucket_name, index_name)
        
        assert exc_info.value.error_code == "INDEX_NOT_FOUND"
        assert exc_info.value.error_details['bucket_name'] == bucket_name
        assert exc_info.value.error_details['index_name'] == index_name


class TestDeleteVectorIndex:
    """Test vector index deletion functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_delete_by_name(self, storage_manager):
        """Test successful index deletion using bucket and index names."""
        bucket_name = "test-bucket"
        index_name = "test-index"
        
        # Mock successful response
        storage_manager.s3vectors_client.delete_index.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.delete_vector_index(
            bucket_name=bucket_name,
            index_name=index_name
        )
        
        storage_manager.s3vectors_client.delete_index.assert_called_once_with(
            vectorBucketName=bucket_name,
            indexName=index_name
        )
        
        assert result['bucket_name'] == bucket_name
        assert result['index_name'] == index_name
        assert result['status'] == 'deleted'
    
    def test_successful_delete_by_arn(self, storage_manager):
        """Test successful index deletion using ARN."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Mock successful response
        storage_manager.s3vectors_client.delete_index.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.delete_vector_index(index_arn=index_arn)
        
        storage_manager.s3vectors_client.delete_index.assert_called_once_with(
            indexArn=index_arn
        )
        
        assert result['index_arn'] == index_arn
        assert result['status'] == 'deleted'
    
    def test_index_not_found_during_delete(self, storage_manager):
        """Test handling when index does not exist during deletion."""
        bucket_name = "test-bucket"
        index_name = "nonexistent-index"
        
        error_response = {
            'Error': {
                'Code': 'NotFoundException',
                'Message': 'Vector index not found'
            }
        }
        storage_manager.s3vectors_client.delete_index.side_effect = ClientError(
            error_response, 'DeleteIndex'
        )
        
        result = storage_manager.delete_vector_index(
            bucket_name=bucket_name,
            index_name=index_name
        )
        
        assert result['status'] == 'not_found'
        assert result['message'] == 'Index not found (may already be deleted)'
    
    def test_conflicting_parameters(self, storage_manager):
        """Test validation when both ARN and name parameters are provided."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.delete_vector_index(
                bucket_name="test-bucket",
                index_name="test-index",
                index_arn="arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
            )
        
        assert exc_info.value.error_code == "CONFLICTING_PARAMETERS"
    
    def test_missing_parameters(self, storage_manager):
        """Test validation when required parameters are missing."""
        # Test missing both ARN and name
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.delete_vector_index()
        assert exc_info.value.error_code == "MISSING_PARAMETERS"
        
        # Test missing index name when bucket name is provided
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.delete_vector_index(bucket_name="test-bucket")
        assert exc_info.value.error_code == "MISSING_PARAMETERS"


class TestIndexExists:
    """Test index existence checking."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_index_exists_true(self, storage_manager):
        """Test when index exists."""
        bucket_name = "test-bucket"
        index_name = "existing-index"
        
        expected_index = {
            'indexName': index_name,
            'indexArn': f'arn:aws:s3vectors:us-west-2:123456789012:index/{bucket_name}/{index_name}',
            'creationTime': 1640995200,
            'vectorBucketName': bucket_name
        }
        
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [expected_index],
            'nextToken': None
        }
        
        result = storage_manager.index_exists(bucket_name, index_name)
        
        assert result is True
    
    def test_index_exists_false(self, storage_manager):
        """Test when index does not exist."""
        bucket_name = "test-bucket"
        index_name = "nonexistent-index"
        
        storage_manager.s3vectors_client.list_indexes.return_value = {
            'indexes': [],
            'nextToken': None
        }
        
        result = storage_manager.index_exists(bucket_name, index_name)
        
        assert result is False
    
    def test_index_exists_other_error_propagates(self, storage_manager):
        """Test that non-index-not-found errors are propagated."""
        bucket_name = "test-bucket"
        index_name = "test-index"
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.list_indexes.side_effect = ClientError(
            error_response, 'ListIndexes'
        )
        
        with pytest.raises(VectorStorageError):
            storage_manager.index_exists(bucket_name, index_name)


class TestVectorDataValidation:
    """Test vector data validation logic."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory'):
            return S3VectorStorageManager()
    
    def test_valid_vector_data(self, storage_manager):
        """Test that valid vector data passes validation."""
        valid_vectors = [
            {
                'key': 'vector1',
                'data': {'float32': [0.1, 0.2, 0.3, 0.4]},
                'metadata': {'type': 'text', 'category': 'document'}
            },
            {
                'key': 'vector2',
                'data': {'float32': [0.5, 0.6, 0.7, 0.8]}
            }
        ]
        
        # Should not raise any exception
        storage_manager._validate_vector_data(valid_vectors)
    
    def test_empty_vector_data(self, storage_manager):
        """Test that empty vector data raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data([])
        
        assert exc_info.value.error_code == "EMPTY_VECTOR_DATA"
    
    def test_too_many_vectors(self, storage_manager):
        """Test that more than 500 vectors raises ValidationError."""
        vectors = [{'key': f'vector{i}', 'data': {'float32': [0.1, 0.2]}} for i in range(501)]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(vectors)
        
        assert exc_info.value.error_code == "TOO_MANY_VECTORS"
        assert exc_info.value.error_details["vector_count"] == 501
    
    def test_invalid_vector_type(self, storage_manager):
        """Test that non-dictionary vectors raise ValidationError."""
        invalid_vectors = [
            {'key': 'vector1', 'data': {'float32': [0.1, 0.2]}},
            "invalid_vector"  # Not a dictionary
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "INVALID_VECTOR_TYPE"
        assert exc_info.value.error_details["index"] == 1
    
    def test_missing_vector_key(self, storage_manager):
        """Test that vectors without keys raise ValidationError."""
        invalid_vectors = [
            {'data': {'float32': [0.1, 0.2, 0.3]}}  # Missing 'key'
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "MISSING_VECTOR_KEY"
    
    def test_missing_vector_data(self, storage_manager):
        """Test that vectors without data raise ValidationError."""
        invalid_vectors = [
            {'key': 'vector1'}  # Missing 'data'
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "MISSING_VECTOR_DATA"
    
    def test_invalid_vector_key(self, storage_manager):
        """Test that invalid vector keys raise ValidationError."""
        invalid_vectors = [
            {'key': '', 'data': {'float32': [0.1, 0.2]}},  # Empty key
            {'key': None, 'data': {'float32': [0.1, 0.2]}},  # None key
            {'key': 123, 'data': {'float32': [0.1, 0.2]}}  # Non-string key
        ]
        
        for i, vectors in enumerate([[v] for v in invalid_vectors]):
            with pytest.raises(ValidationError) as exc_info:
                storage_manager._validate_vector_data(vectors)
            assert exc_info.value.error_code == "INVALID_VECTOR_KEY"
    
    def test_invalid_vector_data_type(self, storage_manager):
        """Test that non-list vector data raises ValidationError."""
        invalid_vectors = [
            {'key': 'vector1', 'data': "not_a_list"}
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "INVALID_VECTOR_DATA_TYPE"
    
    def test_invalid_vector_values(self, storage_manager):
        """Test that non-numeric vector values raise ValidationError."""
        invalid_vectors = [
            {'key': 'vector1', 'data': {'float32': [0.1, "invalid", 0.3]}}
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "INVALID_VECTOR_CONVERSION"
        assert "could not be converted" in str(exc_info.value)
    
    def test_invalid_metadata_type(self, storage_manager):
        """Test that invalid metadata types raise ValidationError."""
        invalid_vectors = [
            {'key': 'vector1', 'data': {'float32': [0.1, 0.2]}, 'metadata': "invalid_metadata"}
        ]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager._validate_vector_data(invalid_vectors)
        
        assert exc_info.value.error_code == "INVALID_METADATA_TYPE"


class TestPutVectors:
    """Test vector storage functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_put_vectors(self, storage_manager):
        """Test successful vector storage."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        vectors_data = [
            {
                'key': 'doc1',
                'data': {'float32': [0.1, 0.2, 0.3, 0.4]},
                'metadata': {'type': 'document', 'category': 'news'}
            },
            {
                'key': 'doc2',
                'data': {'float32': [0.5, 0.6, 0.7, 0.8]},
                'metadata': {'type': 'document', 'category': 'sports'}
            }
        ]
        
        # Mock successful response
        storage_manager.s3vectors_client.put_vectors.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.put_vectors(index_arn, vectors_data)
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.put_vectors.assert_called_once()
        call_args = storage_manager.s3vectors_client.put_vectors.call_args[1]
        
        assert 'indexArn' in call_args or ('vectorBucketName' in call_args and 'indexName' in call_args)
        assert len(call_args['vectors']) == 2
        assert call_args['vectors'][0]['key'] == 'doc1'
        assert np.allclose(call_args['vectors'][0]['data']['float32'], [0.1, 0.2, 0.3, 0.4])
        assert call_args['vectors'][0]['metadata'] == {'type': 'document', 'category': 'news'}
        
        # Verify the result
        assert result['index_arn'] == index_arn
        assert result['vectors_stored'] == 2
        assert result['status'] == 'success'
    
    def test_put_vectors_without_metadata(self, storage_manager):
        """Test storing vectors without metadata."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        vectors_data = [
            {
                'key': 'doc1',
                'data': {'float32': [0.1, 0.2, 0.3, 0.4]}
            }
        ]
        
        storage_manager.s3vectors_client.put_vectors.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        result = storage_manager.put_vectors(index_arn, vectors_data)
        
        call_args = storage_manager.s3vectors_client.put_vectors.call_args[1]
        assert 'metadata' not in call_args['vectors'][0]
        assert result['vectors_stored'] == 1
    
    def test_put_vectors_invalid_index_arn(self, storage_manager):
        """Test validation of index ARN."""
        vectors_data = [{'key': 'doc1', 'data': {'float32': [0.1, 0.2]}}]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.put_vectors("", vectors_data)
        
        assert exc_info.value.error_code == "INVALID_INDEX_IDENTIFIER"
    
    def test_put_vectors_index_not_found(self, storage_manager):
        """Test handling when index does not exist."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/nonexistent"
        vectors_data = [{'key': 'doc1', 'data': {'float32': [0.1, 0.2]}}]
        
        error_response = {
            'Error': {
                'Code': 'NotFoundException',
                'Message': 'Vector index not found'
            }
        }
        storage_manager.s3vectors_client.put_vectors.side_effect = ClientError(
            error_response, 'PutVectors'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.put_vectors(index_arn, vectors_data)
        
        assert exc_info.value.error_code == "INDEX_NOT_FOUND"
    
    def test_put_vectors_access_denied(self, storage_manager):
        """Test handling of access denied errors."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        vectors_data = [{'key': 'doc1', 'data': {'float32': [0.1, 0.2]}}]
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.put_vectors.side_effect = ClientError(
            error_response, 'PutVectors'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.put_vectors(index_arn, vectors_data)
        
        assert exc_info.value.error_code == "ACCESS_DENIED"
        assert "s3vectors:PutVectors" in str(exc_info.value.error_details)
    
    def test_put_vectors_service_unavailable(self, storage_manager):
        """Test handling of service unavailable errors."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        vectors_data = [{'key': 'doc1', 'data': {'float32': [0.1, 0.2]}}]
        
        error_response = {
            'Error': {
                'Code': 'ServiceUnavailableException',
                'Message': 'Currently unable to handle the request'
            }
        }
        storage_manager.s3vectors_client.put_vectors.side_effect = ClientError(
            error_response, 'PutVectors'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.put_vectors(index_arn, vectors_data)
        
        assert exc_info.value.error_code == "SERVICE_UNAVAILABLE"


class TestQueryVectors:
    """Test vector similarity search functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_query_vectors(self, storage_manager):
        """Test successful vector similarity search."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        # Mock successful response
        mock_response = {
            'vectors': [
                {
                    'key': 'doc1',
                    'distance': 0.1,
                    'metadata': {'type': 'document', 'category': 'news'}
                },
                {
                    'key': 'doc2',
                    'distance': 0.2,
                    'metadata': {'type': 'document', 'category': 'sports'}
                }
            ]
        }
        storage_manager.s3vectors_client.query_vectors.return_value = mock_response
        
        result = storage_manager.query_vectors(index_arn, query_vector, top_k=5)
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.query_vectors.assert_called_once()
        call_args = storage_manager.s3vectors_client.query_vectors.call_args[1]
        
        assert 'indexArn' in call_args or 'vectorBucketName' in call_args
        assert np.allclose(call_args['queryVector']['float32'], [0.1, 0.2, 0.3, 0.4])
        assert call_args['topK'] == 5
        assert call_args['returnDistance'] is True
        assert call_args['returnMetadata'] is True
        
        # Verify the result
        assert result['index_arn'] == index_arn
        assert result['query_vector_dimensions'] == 4
        assert result['top_k'] == 5
        assert result['results_count'] == 2
        assert len(result['vectors']) == 2
        assert result['vectors'][0]['key'] == 'doc1'
    
    def test_query_vectors_with_metadata_filter(self, storage_manager):
        """Test vector query with metadata filtering."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        metadata_filter = {'category': 'news'}
        
        mock_response = {'vectors': []}
        storage_manager.s3vectors_client.query_vectors.return_value = mock_response
        
        result = storage_manager.query_vectors(
            index_arn, 
            query_vector, 
            top_k=10,
            metadata_filter=metadata_filter
        )
        
        call_args = storage_manager.s3vectors_client.query_vectors.call_args[1]
        assert call_args['filter'] == metadata_filter
        assert result['metadata_filter'] == metadata_filter
    
    def test_query_vectors_minimal_response(self, storage_manager):
        """Test vector query with minimal response options."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        mock_response = {'vectors': []}
        storage_manager.s3vectors_client.query_vectors.return_value = mock_response
        
        result = storage_manager.query_vectors(
            index_arn, 
            query_vector,
            return_distance=False,
            return_metadata=False
        )
        
        call_args = storage_manager.s3vectors_client.query_vectors.call_args[1]
        assert call_args['returnDistance'] is False
        assert call_args['returnMetadata'] is False
        assert result['return_distance'] is False
        assert result['return_metadata'] is False
    
    def test_query_vectors_invalid_index_arn(self, storage_manager):
        """Test validation of index ARN."""
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors("", query_vector)
        
        assert exc_info.value.error_code == "INVALID_INDEX_IDENTIFIER"
    
    def test_query_vectors_invalid_query_vector(self, storage_manager):
        """Test validation of query vector."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Test empty vector
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, [])
        assert exc_info.value.error_code == "INVALID_QUERY_VECTOR"
        
        # Test non-list vector
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, "not_a_list")
        assert exc_info.value.error_code == "INVALID_QUERY_VECTOR"
        
        # Test vector with invalid values
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, [0.1, "invalid", 0.3])
        assert exc_info.value.error_code == "INVALID_QUERY_VECTOR_CONVERSION"
    
    def test_query_vectors_invalid_top_k(self, storage_manager):
        """Test validation of top_k parameter."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        # Test top_k too small
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, query_vector, top_k=0)
        assert exc_info.value.error_code == "INVALID_TOP_K"
        
        # Test top_k too large
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, query_vector, top_k=1001)
        assert exc_info.value.error_code == "INVALID_TOP_K"
    
    def test_query_vectors_invalid_metadata_filter(self, storage_manager):
        """Test validation of metadata filter."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.query_vectors(index_arn, query_vector, metadata_filter="invalid")
        
        assert exc_info.value.error_code == "INVALID_METADATA_FILTER"
    
    def test_query_vectors_access_denied_with_metadata(self, storage_manager):
        """Test access denied error includes required permissions."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        query_vector = [0.1, 0.2, 0.3, 0.4]
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.query_vectors.side_effect = ClientError(
            error_response, 'QueryVectors'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.query_vectors(index_arn, query_vector, return_metadata=True)
        
        assert exc_info.value.error_code == "ACCESS_DENIED"
        required_permissions = exc_info.value.error_details["required_permissions"]
        assert "s3vectors:QueryVectors" in required_permissions
        assert "s3vectors:GetVectors" in required_permissions


class TestListVectors:
    """Test vector listing functionality."""
    
    @pytest.fixture
    def storage_manager(self):
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_client
            mock_factory.get_s3_client.return_value = Mock()
            manager = S3VectorStorageManager()
            manager.s3vectors_client = mock_client
            return manager
    
    def test_successful_list_vectors(self, storage_manager):
        """Test successful vector listing."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Mock successful response
        mock_response = {
            'vectors': [
                {
                    'key': 'doc1',
                    'metadata': {'type': 'document', 'category': 'news'}
                },
                {
                    'key': 'doc2',
                    'metadata': {'type': 'document', 'category': 'sports'}
                }
            ],
            'nextToken': 'next_page_token'
        }
        storage_manager.s3vectors_client.list_vectors.return_value = mock_response
        
        result = storage_manager.list_vectors(index_arn, max_results=100)
        
        # Verify the call was made with correct parameters
        storage_manager.s3vectors_client.list_vectors.assert_called_once()
        call_args = storage_manager.s3vectors_client.list_vectors.call_args[1]
        
        assert 'indexArn' in call_args or 'vectorBucketName' in call_args
        assert call_args['maxResults'] == 100
        assert call_args['returnData'] is False
        assert call_args['returnMetadata'] is True
        
        # Verify the result
        assert result['index_arn'] == index_arn
        assert result['count'] == 2
        assert result['next_token'] == 'next_page_token'
        assert len(result['vectors']) == 2
        assert result['vectors'][0]['key'] == 'doc1'
    
    def test_list_vectors_with_pagination(self, storage_manager):
        """Test vector listing with pagination."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        next_token = "pagination_token"
        
        mock_response = {'vectors': [], 'nextToken': None}
        storage_manager.s3vectors_client.list_vectors.return_value = mock_response
        
        result = storage_manager.list_vectors(index_arn, next_token=next_token)
        
        call_args = storage_manager.s3vectors_client.list_vectors.call_args[1]
        assert call_args['nextToken'] == next_token
        assert result['next_token'] is None
    
    def test_list_vectors_with_data(self, storage_manager):
        """Test vector listing with vector data included."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        mock_response = {'vectors': []}
        storage_manager.s3vectors_client.list_vectors.return_value = mock_response
        
        result = storage_manager.list_vectors(index_arn, return_data=True)
        
        call_args = storage_manager.s3vectors_client.list_vectors.call_args[1]
        assert call_args['returnData'] is True
        assert result['return_data'] is True
    
    def test_list_vectors_parallel_segments(self, storage_manager):
        """Test vector listing with parallel segments."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        mock_response = {'vectors': []}
        storage_manager.s3vectors_client.list_vectors.return_value = mock_response
        
        result = storage_manager.list_vectors(
            index_arn, 
            segment_count=4, 
            segment_index=1
        )
        
        call_args = storage_manager.s3vectors_client.list_vectors.call_args[1]
        assert call_args['segmentCount'] == 4
        assert call_args['segmentIndex'] == 1
        assert result['segment_count'] == 4
        assert result['segment_index'] == 1
    
    def test_list_vectors_invalid_index_arn(self, storage_manager):
        """Test validation of index ARN."""
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors("")
        
        assert exc_info.value.error_code == "INVALID_INDEX_IDENTIFIER"
    
    def test_list_vectors_invalid_max_results(self, storage_manager):
        """Test validation of max_results parameter."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Test max_results too small
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, max_results=0)
        assert exc_info.value.error_code == "INVALID_MAX_RESULTS"
        
        # Test max_results too large
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, max_results=1001)
        assert exc_info.value.error_code == "INVALID_MAX_RESULTS"
    
    def test_list_vectors_invalid_next_token(self, storage_manager):
        """Test validation of next_token parameter."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Test next_token too long
        long_token = "a" * 2049
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, next_token=long_token)
        assert exc_info.value.error_code == "INVALID_NEXT_TOKEN"
    
    def test_list_vectors_invalid_segment_parameters(self, storage_manager):
        """Test validation of segment parameters."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Test segment_count without segment_index
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, segment_count=4)
        assert exc_info.value.error_code == "MISSING_SEGMENT_INDEX"
        
        # Test segment_index without segment_count
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, segment_index=1)
        assert exc_info.value.error_code == "MISSING_SEGMENT_COUNT"
        
        # Test segment_index >= segment_count
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, segment_count=4, segment_index=4)
        assert exc_info.value.error_code == "INVALID_SEGMENT_RELATIONSHIP"
        
        # Test invalid segment_count range
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, segment_count=17, segment_index=0)
        assert exc_info.value.error_code == "INVALID_SEGMENT_COUNT"
        
        # Test invalid segment_index range
        with pytest.raises(ValidationError) as exc_info:
            storage_manager.list_vectors(index_arn, segment_count=4, segment_index=16)
        assert exc_info.value.error_code == "INVALID_SEGMENT_INDEX"
    
    def test_list_vectors_access_denied_with_data(self, storage_manager):
        """Test access denied error includes required permissions."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied'
            }
        }
        storage_manager.s3vectors_client.list_vectors.side_effect = ClientError(
            error_response, 'ListVectors'
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            storage_manager.list_vectors(index_arn, return_data=True)
        
        assert exc_info.value.error_code == "ACCESS_DENIED"
        required_permissions = exc_info.value.error_details["required_permissions"]
        assert "s3vectors:ListVectors" in required_permissions
        assert "s3vectors:GetVectors" in required_permissions