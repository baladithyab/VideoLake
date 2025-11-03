"""
Unit tests for OpenSearchExportManager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.services.opensearch.export_manager import OpenSearchExportManager, ExportStatus
from src.exceptions import OpenSearchIntegrationError


class TestExportManagerInitialization(unittest.TestCase):
    """Test export manager initialization."""

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_init_success(self, mock_session, mock_registry):
        """Test successful initialization."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        manager = OpenSearchExportManager(region_name="us-east-1")

        assert manager.region_name == "us-east-1"
        assert manager.opensearch_serverless_client == mock_serverless_client
        assert manager.osis_client == mock_osis_client

    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_init_client_failure(self, mock_session):
        """Test initialization failure when clients can't be created."""
        mock_session.side_effect = Exception("AWS connection failed")

        with self.assertRaises(OpenSearchIntegrationError) as context:
            OpenSearchExportManager()

        assert "Failed to initialize export manager clients" in str(context.exception)


class TestExportToOpenSearchServerless(unittest.TestCase):
    """Test export to OpenSearch Serverless."""

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    @patch('src.services.opensearch.export_manager.boto3.client')
    def test_export_success_with_new_role(self, mock_boto_client, mock_session, mock_retry, mock_registry):
        """Test successful export with auto-created IAM role."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()
        mock_iam_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]
        mock_boto_client.return_value = mock_iam_client

        # Mock collection check (doesn't exist)
        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        mock_serverless_client.batch_get_collection.return_value = {
            'collectionDetails': []
        }

        # Mock collection creation
        mock_serverless_client.create_collection.return_value = {
            'createCollectionDetail': {
                'arn': 'arn:aws:aoss:us-east-1:123456789012:collection/test-coll'
            }
        }

        # Mock IAM role creation
        mock_iam_client.create_role.return_value = {
            'Role': {
                'Arn': 'arn:aws:iam::123456789012:role/test-role'
            }
        }

        # Mock pipeline creation
        mock_osis_client.create_pipeline.return_value = {
            'Pipeline': {
                'PipelineArn': 'arn:aws:osis:us-east-1:123456789012:pipeline/test-pipeline'
            }
        }

        manager = OpenSearchExportManager(region_name="us-east-1")

        result = manager.export_to_opensearch_serverless(
            vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket/index/test-index",
            collection_name="test-collection"
        )

        assert result == "test-pipeline"
        assert len(manager._exports) == 1
        assert manager._exports[0].export_id == "test-pipeline"
        assert manager._exports[0].status == "PENDING"

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_export_with_existing_role(self, mock_session, mock_retry, mock_registry):
        """Test export with provided IAM role."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        # Mock existing collection
        mock_serverless_client.batch_get_collection.return_value = {
            'collectionDetails': [{
                'arn': 'arn:aws:aoss:us-east-1:123456789012:collection/test-coll'
            }]
        }

        # Mock pipeline creation
        mock_osis_client.create_pipeline.return_value = {
            'Pipeline': {
                'PipelineArn': 'arn:aws:osis:us-east-1:123456789012:pipeline/test-pipeline'
            }
        }

        manager = OpenSearchExportManager(region_name="us-east-1")

        result = manager.export_to_opensearch_serverless(
            vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket/index/test-index",
            collection_name="test-collection",
            iam_role_arn="arn:aws:iam::123456789012:role/existing-role"
        )

        assert result == "test-pipeline"
        # Should not create IAM role (provided one was used)


class TestGetExportStatus(unittest.TestCase):
    """Test export status retrieval."""

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_get_status_in_progress(self, mock_session, mock_retry, mock_registry):
        """Test getting status for in-progress export."""
        # Setup mocks
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        manager = OpenSearchExportManager(region_name="us-east-1")

        # Add a pending export
        export_status = ExportStatus(
            export_id="test-pipeline",
            status="PENDING",
            source_index_arn="arn:aws:s3vectors:us-east-1:123:bucket/test/index/idx",
            target_collection_name="test-coll",
            created_at=datetime.utcnow()
        )
        manager._exports.append(export_status)

        # Mock pipeline status check
        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        mock_osis_client.get_pipeline.return_value = {
            'Pipeline': {
                'Status': 'ACTIVE'
            }
        }

        result = manager.get_export_status("test-pipeline")

        assert result.status == "IN_PROGRESS"

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_get_status_completed(self, mock_session, mock_retry, mock_registry):
        """Test getting status for completed export."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        manager = OpenSearchExportManager(region_name="us-east-1")

        # Add a pending export
        export_status = ExportStatus(
            export_id="test-pipeline",
            status="PENDING",
            source_index_arn="arn:aws:s3vectors:us-east-1:123:bucket/test/index/idx",
            target_collection_name="test-coll",
            created_at=datetime.utcnow()
        )
        manager._exports.append(export_status)

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        mock_osis_client.get_pipeline.return_value = {
            'Pipeline': {
                'Status': 'CREATE_COMPLETE'
            }
        }

        result = manager.get_export_status("test-pipeline")

        assert result.status == "COMPLETED"
        assert result.completed_at is not None

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_get_status_not_found(self, mock_session, mock_retry, mock_registry):
        """Test getting status for non-existent export."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        mock_osis_client.get_pipeline.return_value = {
            'Pipeline': {
                'Status': 'ACTIVE'
            }
        }

        manager = OpenSearchExportManager(region_name="us-east-1")

        with self.assertRaises(OpenSearchIntegrationError) as context:
            manager.get_export_status("non-existent")

        assert "Export status not found" in str(context.exception)


class TestEnsureServerlessCollection(unittest.TestCase):
    """Test serverless collection management."""

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_collection_exists(self, mock_session, mock_retry, mock_registry):
        """Test with existing collection."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        mock_serverless_client.batch_get_collection.return_value = {
            'collectionDetails': [{
                'arn': 'arn:aws:aoss:us-east-1:123456789012:collection/existing-coll'
            }]
        }

        manager = OpenSearchExportManager(region_name="us-east-1")
        result = manager._ensure_serverless_collection("existing-coll")

        assert result == 'arn:aws:aoss:us-east-1:123456789012:collection/existing-coll'

    @patch('src.services.opensearch.export_manager.resource_registry')
    @patch('src.services.opensearch.export_manager.AWSRetryHandler')
    @patch('src.services.opensearch.export_manager.boto3.Session')
    def test_collection_creation(self, mock_session, mock_retry, mock_registry):
        """Test creating new collection."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance

        mock_serverless_client = Mock()
        mock_osis_client = Mock()

        mock_session_instance.client.side_effect = [
            mock_serverless_client,
            mock_osis_client
        ]

        def retry_side_effect(func, **kwargs):
            return func()

        mock_retry.retry_with_backoff.side_effect = retry_side_effect

        # First call: collection doesn't exist
        mock_serverless_client.batch_get_collection.return_value = {
            'collectionDetails': []
        }

        # Second call: collection created
        mock_serverless_client.create_collection.return_value = {
            'createCollectionDetail': {
                'arn': 'arn:aws:aoss:us-east-1:123456789012:collection/new-coll'
            }
        }

        manager = OpenSearchExportManager(region_name="us-east-1")
        result = manager._ensure_serverless_collection("new-coll")

        assert result == 'arn:aws:aoss:us-east-1:123456789012:collection/new-coll'
        mock_serverless_client.create_collection.assert_called_once()


if __name__ == '__main__':
    unittest.main()
