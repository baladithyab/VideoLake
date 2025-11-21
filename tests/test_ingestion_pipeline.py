"""
Tests for the Ingestion Pipeline.
"""

import unittest
import json
from unittest.mock import MagicMock, patch
from src.ingestion.pipeline import VideoIngestionPipeline, IngestionResult

class TestVideoIngestionPipeline(unittest.TestCase):

    @patch('boto3.client')
    @patch('src.ingestion.pipeline.get_config')
    @patch('os.getenv')
    def test_process_video_success(self, mock_getenv, mock_get_config, mock_boto3):
        # Setup Mocks
        mock_getenv.return_value = "arn:aws:states:us-east-1:123456789012:stateMachine:test-machine"
        mock_sfn = MagicMock()
        mock_boto3.return_value = mock_sfn
        
        mock_sfn.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:test-machine:123',
            'startDate': '2023-01-01T00:00:00Z'
        }

        # Initialize Pipeline
        pipeline = VideoIngestionPipeline()
        
        # Run Pipeline
        result = pipeline.process_video(
            video_path="s3://test-bucket/video.mp4",
            model_type="marengo",
            backend_types=["s3vector"]
        )

        # Assertions
        self.assertEqual(result.status, "RUNNING")
        self.assertEqual(result.job_id, 'arn:aws:states:us-east-1:123456789012:execution:test-machine:123')
        
        # Verify Step Function call
        mock_sfn.start_execution.assert_called_once()
        call_args = mock_sfn.start_execution.call_args
        self.assertEqual(call_args[1]['stateMachineArn'], "arn:aws:states:us-east-1:123456789012:stateMachine:test-machine")
        
        input_payload = json.loads(call_args[1]['input'])
        self.assertEqual(input_payload['video_path'], "s3://test-bucket/video.mp4")
        self.assertEqual(input_payload['model_type'], "marengo")
        self.assertEqual(input_payload['backend_types_str'], "s3vector")

    @patch('boto3.client')
    @patch('src.ingestion.pipeline.get_config')
    @patch('os.getenv')
    def test_process_video_mock_mode(self, mock_getenv, mock_get_config, mock_boto3):
        # Setup Mocks to return None for ARN
        mock_getenv.return_value = None
        
        # Initialize Pipeline
        pipeline = VideoIngestionPipeline()
        
        # Run Pipeline
        result = pipeline.process_video(
            video_path="s3://test-bucket/video.mp4"
        )
        
        # Assertions
        self.assertEqual(result.status, "mock_success")
        self.assertTrue(result.job_id.startswith("mock-"))

if __name__ == '__main__':
    unittest.main()