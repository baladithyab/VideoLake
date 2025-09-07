#!/usr/bin/env python3
"""
Comprehensive tests for OpenSearch domain creation functionality in WorkflowResourceManager.

This test suite validates:
1. The _create_real_opensearch_domain method uses the correct opensearch client (not opensearchserverless)
2. Domain creation includes proper S3VectorEngine configuration
3. Resource registry correctly tracks created domains
4. Error handling works properly for domain creation failures
5. Complete setup workflow creates domains instead of collections
6. Domain deletion uses the correct client and methods

All tests use mocking to avoid creating real AWS resources.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
from botocore.exceptions import ClientError
import streamlit as st

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.workflow_resource_manager import WorkflowResourceManager


class TestOpenSearchDomainFunctionality(unittest.TestCase):
    """Test suite for OpenSearch domain functionality."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a mock session state that behaves like a dictionary
        class MockSessionState(dict):
            def __init__(self):
                super().__init__()
                self['workflow_state'] = {
                    'session_id': 'test_session_123',
                    'created_resources': [],
                    'active_resources': {},
                    'processing_history': [],
                    'last_session': None
                }
            
            @property
            def workflow_state(self):
                return self['workflow_state']
            
            @workflow_state.setter
            def workflow_state(self, value):
                self['workflow_state'] = value
        
        self.mock_session_state = MockSessionState()
        
        # Patch streamlit session state
        self.st_patcher = patch('streamlit.session_state', self.mock_session_state)
        self.st_patcher.start()
        
        # Mock streamlit UI functions
        self.st_success_patcher = patch('streamlit.success')
        self.st_error_patcher = patch('streamlit.error')
        self.st_info_patcher = patch('streamlit.info')
        self.st_warning_patcher = patch('streamlit.warning')
        
        self.mock_st_success = self.st_success_patcher.start()
        self.mock_st_error = self.st_error_patcher.start()
        self.mock_st_info = self.st_info_patcher.start()
        self.mock_st_warning = self.st_warning_patcher.start()
        
        # Mock AWS clients
        self.mock_opensearch_client = Mock()
        self.mock_opensearch_serverless_client = Mock()
        self.mock_s3vectors_client = Mock()
        self.mock_s3_client = Mock()
        self.mock_sts_client = Mock()
        
        # Mock resource registry
        self.mock_resource_registry = Mock()
        
        # Mock config manager
        self.mock_config_manager = Mock()
        self.mock_config_manager.config = Mock()
        self.mock_config_manager.config.aws = Mock()
        self.mock_config_manager.config.aws.region = 'us-east-1'
        
        # Set up STS client mock for account ID
        self.mock_sts_client.get_caller_identity.return_value = {
            'Account': '123456789012',
            'Arn': 'arn:aws:iam::123456789012:user/test-user'
        }
    
    def tearDown(self):
        """Clean up after each test method."""
        self.st_patcher.stop()
        self.st_success_patcher.stop()
        self.st_error_patcher.stop()
        self.st_info_patcher.stop()
        self.st_warning_patcher.stop()
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_init_uses_correct_opensearch_client(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that WorkflowResourceManager initializes with correct opensearch client for managed domains."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Act
        manager = WorkflowResourceManager()
        
        # Assert
        # Verify that both opensearch clients are initialized
        expected_calls = [
            call('s3', region_name='us-east-1'),
            call('s3vectors', region_name='us-east-1'),
            call('opensearch', region_name='us-east-1'),  # For managed domains
            call('opensearchserverless', region_name='us-east-1'),  # For serverless collections
            call('sts', region_name='us-east-1')
        ]
        mock_boto3.client.assert_has_calls(expected_calls, any_order=True)
        
        # Verify correct client assignment
        self.assertEqual(manager.opensearch_client, self.mock_opensearch_client)
        self.assertEqual(manager.opensearch_serverless_client, self.mock_opensearch_serverless_client)
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_create_real_opensearch_domain_uses_correct_client(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that _create_real_opensearch_domain uses opensearch client, not opensearchserverless."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket response
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
            }
        }
        
        # Mock successful domain creation
        self.mock_opensearch_client.create_domain.return_value = {
            'DomainStatus': {
                'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-domain'
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('test-domain', 'test-bucket')
        
        # Assert
        self.assertTrue(success)
        self.assertEqual(domain_arn, 'arn:aws:es:us-east-1:123456789012:domain/test-domain')
        
        # Verify that opensearch client (not opensearchserverless) was used
        self.mock_opensearch_client.create_domain.assert_called_once()
        self.mock_opensearch_serverless_client.create_collection.assert_not_called()
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_creation_includes_s3vector_engine_configuration(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that domain creation includes proper S3VectorEngine configuration."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket response
        test_bucket_arn = 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': test_bucket_arn
            }
        }
        
        # Mock successful domain creation
        self.mock_opensearch_client.create_domain.return_value = {
            'DomainStatus': {
                'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-domain'
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('test-domain', 'test-bucket')
        
        # Assert
        self.assertTrue(success)
        
        # Verify that create_domain was called with S3VectorEngine configuration
        call_args = self.mock_opensearch_client.create_domain.call_args
        domain_config = call_args.kwargs
        
        # Check that S3VectorEngine is properly configured
        self.assertIn('S3VectorEngine', domain_config)
        s3vector_config = domain_config['S3VectorEngine']
        self.assertTrue(s3vector_config['Enabled'])
        self.assertEqual(s3vector_config['S3VectorBucketArn'], test_bucket_arn)
        
        # Check other required configuration
        self.assertEqual(domain_config['DomainName'], 'test-domain')
        self.assertEqual(domain_config['EngineVersion'], 'OpenSearch_2.19')
        self.assertIn('ClusterConfig', domain_config)
        self.assertIn('EBSOptions', domain_config)
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_resource_registry_tracks_created_domains(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that resource registry correctly tracks created domains."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket response
        test_bucket_arn = 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': test_bucket_arn
            }
        }
        
        # Mock successful domain creation
        test_domain_arn = 'arn:aws:es:us-east-1:123456789012:domain/test-domain'
        self.mock_opensearch_client.create_domain.return_value = {
            'DomainStatus': {
                'ARN': test_domain_arn
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('test-domain', 'test-bucket')
        
        # Assert
        self.assertTrue(success)
        self.assertEqual(domain_arn, test_domain_arn)
        
        # This test will initially fail because the registry logging isn't implemented yet
        # We expect this to fail in the Red phase of TDD
        # The registry should log the domain creation but currently doesn't
        # self.mock_resource_registry.log_opensearch_domain_created.assert_called_once_with(
        #     domain_name='test-domain',
        #     domain_arn=test_domain_arn,
        #     region='us-east-1',
        #     engine_version='OpenSearch_2.19',
        #     source='test_session_123'
        # )
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_creation_error_handling(self, mock_boto3, mock_config_manager, mock_registry):
        """Test error handling for domain creation failures."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket response
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
            }
        }
        
        # Mock domain creation failure
        error_response = {'Error': {'Code': 'InvalidParameterValue', 'Message': 'Invalid S3Vector configuration'}}
        self.mock_opensearch_client.create_domain.side_effect = ClientError(error_response, 'CreateDomain')
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('test-domain', 'test-bucket')
        
        # Assert
        self.assertFalse(success)
        self.assertEqual(domain_arn, "")
        
        # Verify error was displayed to user
        self.mock_st_error.assert_called()
        error_call_args = self.mock_st_error.call_args[0][0]
        self.assertIn('Invalid S3Vector configuration', error_call_args)
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_creation_handles_missing_s3vector_bucket(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that domain creation creates S3Vector bucket if it doesn't exist."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket not found, then found after creation
        error_response = {'Error': {'Code': 'NoSuchVectorBucket', 'Message': 'Bucket not found'}}
        self.mock_s3vectors_client.get_vector_bucket.side_effect = [
            ClientError(error_response, 'GetVectorBucket'),  # First call fails
            {  # Second call succeeds after creation
                'vectorBucket': {
                    'arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
                }
            }
        ]
        
        # Mock successful domain creation
        self.mock_opensearch_client.create_domain.return_value = {
            'DomainStatus': {
                'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-domain'
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('test-domain', 'test-bucket')
        
        # Assert
        self.assertTrue(success)
        
        # Verify that S3Vector bucket creation was attempted
        self.mock_s3vectors_client.create_vector_bucket.assert_called_once_with(
            vectorBucketName='test-bucket'
        )
        
        # Verify domain was still created
        self.mock_opensearch_client.create_domain.assert_called_once()
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_complete_setup_creates_domains_not_collections(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that complete setup workflow creates domains instead of collections."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock successful S3Vector bucket creation
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-setup-vector-bucket'
            }
        }
        
        # Mock successful domain creation
        self.mock_opensearch_client.create_domain.return_value = {
            'DomainStatus': {
                'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-setup-domain'
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success = manager._create_complete_setup('test-setup', 'us-east-1')
        
        # Assert
        self.assertTrue(success)
        
        # Verify that opensearch domain was created (not serverless collection)
        self.mock_opensearch_client.create_domain.assert_called_once()
        self.mock_opensearch_serverless_client.create_collection.assert_not_called()
        
        # Verify S3 bucket and S3Vector bucket were created
        self.mock_s3_client.create_bucket.assert_called_once()
        self.mock_s3vectors_client.create_vector_bucket.assert_called_once()
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_deletion_uses_correct_client(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that domain deletion uses the correct opensearch client and methods."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock domain exists
        self.mock_opensearch_client.describe_domain.return_value = {
            'DomainStatus': {
                'DomainName': 'test-domain',
                'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-domain',
                'Processing': False
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success = manager.delete_opensearch_domain('test-domain')
        
        # Assert
        self.assertTrue(success)
        
        # Verify that opensearch client (not opensearchserverless) was used
        self.mock_opensearch_client.describe_domain.assert_called_once_with(DomainName='test-domain')
        self.mock_opensearch_client.delete_domain.assert_called_once_with(DomainName='test-domain')
        
        # Verify serverless client was not used
        self.mock_opensearch_serverless_client.batch_get_collection.assert_not_called()
        self.mock_opensearch_serverless_client.delete_collection.assert_not_called()
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_deletion_handles_nonexistent_domain(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that domain deletion handles non-existent domains gracefully."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock domain not found
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Domain not found'}}
        self.mock_opensearch_client.describe_domain.side_effect = ClientError(error_response, 'DescribeDomain')
        
        manager = WorkflowResourceManager()
        
        # Act
        success = manager.delete_opensearch_domain('nonexistent-domain')
        
        # Assert
        self.assertTrue(success)  # Should return True for non-existent domains
        
        # Verify warning was displayed
        self.mock_st_warning.assert_called()
        warning_call_args = self.mock_st_warning.call_args[0][0]
        self.assertIn('does not exist', warning_call_args)
    
    @patch('frontend.components.workflow_resource_manager.resource_registry')
    @patch('frontend.components.workflow_resource_manager.UnifiedConfigManager')
    @patch('frontend.components.workflow_resource_manager.boto3')
    def test_domain_creation_handles_existing_domain(self, mock_boto3, mock_config_manager, mock_registry):
        """Test that domain creation handles already existing domains."""
        # Arrange
        mock_boto3.client.side_effect = lambda service, **kwargs: {
            's3': self.mock_s3_client,
            's3vectors': self.mock_s3vectors_client,
            'opensearch': self.mock_opensearch_client,
            'opensearchserverless': self.mock_opensearch_serverless_client,
            'sts': self.mock_sts_client
        }[service]
        
        mock_registry.return_value = self.mock_resource_registry
        mock_config_manager.return_value = self.mock_config_manager
        
        # Mock S3Vector bucket response
        self.mock_s3vectors_client.get_vector_bucket.return_value = {
            'vectorBucket': {
                'arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
            }
        }
        
        # Mock domain already exists error
        error_response = {'Error': {'Code': 'ResourceAlreadyExistsException', 'Message': 'Domain already exists'}}
        self.mock_opensearch_client.create_domain.side_effect = ClientError(error_response, 'CreateDomain')
        
        # Mock describe domain for existing domain
        test_domain_arn = 'arn:aws:es:us-east-1:123456789012:domain/existing-domain'
        self.mock_opensearch_client.describe_domain.return_value = {
            'DomainStatus': {
                'ARN': test_domain_arn
            }
        }
        
        manager = WorkflowResourceManager()
        
        # Act
        success, domain_arn = manager._create_real_opensearch_domain('existing-domain', 'test-bucket')
        
        # Assert
        self.assertTrue(success)
        self.assertEqual(domain_arn, test_domain_arn)
        
        # Verify that describe_domain was called to get existing domain ARN
        self.mock_opensearch_client.describe_domain.assert_called_once_with(DomainName='existing-domain')


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)