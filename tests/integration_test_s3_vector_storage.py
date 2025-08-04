"""
Integration test for S3 Vector Storage Manager.

This test demonstrates the functionality with real AWS SDK calls
(mocked for safety) and validates the complete workflow.
"""

import pytest
from unittest.mock import patch, Mock
import json

from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError, ValidationError


class TestS3VectorStorageIntegration:
    """Integration tests for S3VectorStorageManager."""
    
    def test_complete_bucket_lifecycle(self):
        """Test complete bucket lifecycle: create, get, list, check existence."""
        bucket_name = "media-embeddings-test"
        
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            # Mock S3 Vectors client
            mock_s3vectors_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = Mock()
            
            # Mock responses for different operations
            mock_s3vectors_client.create_vector_bucket.return_value = {
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            
            mock_s3vectors_client.get_vector_bucket.return_value = {
                'vectorBucketName': bucket_name,
                'encryptionConfiguration': {'sseType': 'SSE-S3'},
                'creationDate': '2025-01-01T00:00:00Z'
            }
            
            mock_s3vectors_client.list_vector_buckets.return_value = {
                'vectorBuckets': [
                    {
                        'vectorBucketName': bucket_name,
                        'creationDate': '2025-01-01T00:00:00Z'
                    }
                ]
            }
            
            # Create storage manager
            storage_manager = S3VectorStorageManager()
            
            # Test bucket creation
            create_result = storage_manager.create_vector_bucket(bucket_name)
            assert create_result['status'] == 'created'
            assert create_result['bucket_name'] == bucket_name
            assert create_result['encryption_type'] == 'SSE-S3'
            
            # Test getting bucket attributes
            bucket_info = storage_manager.get_vector_bucket(bucket_name)
            assert bucket_info['vectorBucketName'] == bucket_name
            assert bucket_info['encryptionConfiguration']['sseType'] == 'SSE-S3'
            
            # Test listing buckets
            buckets = storage_manager.list_vector_buckets()
            assert len(buckets) == 1
            assert buckets[0]['vectorBucketName'] == bucket_name
            
            # Test bucket existence check
            exists = storage_manager.bucket_exists(bucket_name)
            assert exists is True
            
            # Verify all expected calls were made
            mock_s3vectors_client.create_vector_bucket.assert_called_once()
            mock_s3vectors_client.get_vector_bucket.assert_called()
            mock_s3vectors_client.list_vector_buckets.assert_called_once()
    
    def test_bucket_creation_with_kms_encryption(self):
        """Test bucket creation with KMS encryption."""
        bucket_name = "secure-media-embeddings"
        kms_key_arn = "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
        
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_s3vectors_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = Mock()
            
            mock_s3vectors_client.create_vector_bucket.return_value = {
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            
            storage_manager = S3VectorStorageManager()
            
            result = storage_manager.create_vector_bucket(
                bucket_name,
                encryption_type="SSE-KMS",
                kms_key_arn=kms_key_arn
            )
            
            # Verify the call was made with correct KMS parameters
            expected_call_args = {
                'vectorBucketName': bucket_name,
                'encryptionConfiguration': {
                    'sseType': 'SSE-KMS',
                    'kmsKeyArn': kms_key_arn
                }
            }
            
            mock_s3vectors_client.create_vector_bucket.assert_called_once_with(**expected_call_args)
            
            assert result['status'] == 'created'
            assert result['encryption_type'] == 'SSE-KMS'
            assert result['kms_key_arn'] == kms_key_arn
    
    def test_error_handling_workflow(self):
        """Test error handling in various scenarios."""
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_s3vectors_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = Mock()
            
            storage_manager = S3VectorStorageManager()
            
            # Test validation errors
            with pytest.raises(ValidationError):
                storage_manager.create_vector_bucket("")  # Empty name
            
            with pytest.raises(ValidationError):
                storage_manager.create_vector_bucket("ab")  # Too short
            
            with pytest.raises(ValidationError):
                storage_manager.create_vector_bucket("Invalid-Name")  # Uppercase
            
            with pytest.raises(ValidationError):
                storage_manager.create_vector_bucket("test-bucket", encryption_type="INVALID")
            
            # Test that no AWS calls were made for validation errors
            mock_s3vectors_client.create_vector_bucket.assert_not_called()
    
    def test_media_company_use_case_simulation(self):
        """Simulate a media company setting up vector storage infrastructure."""
        # Simulate Netflix-style bucket names for different content types
        bucket_configs = [
            {"name": "netflix-movie-embeddings", "type": "movies"},
            {"name": "netflix-series-embeddings", "type": "series"},
            {"name": "netflix-trailer-embeddings", "type": "trailers"}
        ]
        
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_s3vectors_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = Mock()
            
            # Mock successful creation for all buckets
            mock_s3vectors_client.create_vector_bucket.return_value = {
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            
            # Mock list response with all created buckets
            mock_s3vectors_client.list_vector_buckets.return_value = {
                'vectorBuckets': [
                    {'vectorBucketName': config['name'], 'creationDate': '2025-01-01T00:00:00Z'}
                    for config in bucket_configs
                ]
            }
            
            storage_manager = S3VectorStorageManager()
            
            # Create buckets for different content types
            created_buckets = []
            for config in bucket_configs:
                result = storage_manager.create_vector_bucket(config['name'])
                created_buckets.append(result)
                assert result['status'] == 'created'
                assert result['bucket_name'] == config['name']
            
            # Verify all buckets were created
            assert len(created_buckets) == 3
            assert mock_s3vectors_client.create_vector_bucket.call_count == 3
            
            # List all buckets to verify infrastructure setup
            all_buckets = storage_manager.list_vector_buckets()
            assert len(all_buckets) == 3
            
            bucket_names = [bucket['vectorBucketName'] for bucket in all_buckets]
            for config in bucket_configs:
                assert config['name'] in bucket_names
    
    def test_cost_optimization_scenario(self):
        """Test scenario focused on cost optimization features."""
        bucket_name = "cost-optimized-embeddings"
        
        with patch('src.services.s3_vector_storage.aws_client_factory') as mock_factory:
            mock_s3vectors_client = Mock()
            mock_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_factory.get_s3_client.return_value = Mock()
            
            # Mock bucket creation with cost-effective SSE-S3 encryption
            mock_s3vectors_client.create_vector_bucket.return_value = {
                'ResponseMetadata': {'HTTPStatusCode': 200}
            }
            
            storage_manager = S3VectorStorageManager()
            
            # Create bucket with default SSE-S3 (most cost-effective)
            result = storage_manager.create_vector_bucket(bucket_name)
            
            # Verify cost-optimized configuration
            call_args = mock_s3vectors_client.create_vector_bucket.call_args[1]
            assert call_args['vectorBucketName'] == bucket_name
            assert call_args['encryptionConfiguration']['sseType'] == 'SSE-S3'
            
            # Verify no KMS key (which would add cost)
            assert 'kmsKeyArn' not in call_args['encryptionConfiguration']
            
            assert result['encryption_type'] == 'SSE-S3'
            assert result['kms_key_arn'] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])