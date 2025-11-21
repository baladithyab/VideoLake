import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import os
import sys
from pathlib import Path
import asyncio

# Add project root to path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ingestion.pipeline import VideoIngestionPipeline, IngestionResult
from src.backend.benchmark_service import BenchmarkService
from src.services.video_dataset_manager import VideoDatasetManager, VideoDatasetConfig, VideoMetadata

class TestVideoIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.mock_sfn_client = MagicMock()
        with patch('boto3.client', return_value=self.mock_sfn_client):
            self.pipeline = VideoIngestionPipeline()
        self.pipeline.state_machine_arn = "arn:aws:states:us-east-1:123456789012:stateMachine:TestStateMachine"

    def test_process_video_success(self):
        # Setup mock response
        self.mock_sfn_client.start_execution.return_value = {
            'executionArn': 'arn:aws:states:us-east-1:123456789012:execution:TestStateMachine:execution-id',
            'startDate': '2023-01-01T00:00:00Z'
        }

        # Call method
        result = self.pipeline.process_video(
            video_path="s3://bucket/video.mp4",
            model_type="marengo",
            backend_types=["s3vector", "lancedb"]
        )

        # Verify result
        self.assertIsInstance(result, IngestionResult)
        self.assertEqual(result.status, "RUNNING")
        self.assertEqual(result.job_id, 'arn:aws:states:us-east-1:123456789012:execution:TestStateMachine:execution-id')

        # Verify SFN call
        expected_input = {
            "video_path": "s3://bucket/video.mp4",
            "model_type": "marengo",
            "backend_types_str": "s3vector,lancedb"
        }
        self.mock_sfn_client.start_execution.assert_called_once_with(
            stateMachineArn=self.pipeline.state_machine_arn,
            name=ANY,
            input=ANY
        )
        
        # Verify input payload JSON
        call_args = self.mock_sfn_client.start_execution.call_args
        input_json = json.loads(call_args[1]['input'])
        self.assertEqual(input_json, expected_input)

    def test_process_video_no_arn_mock_mode(self):
        self.pipeline.state_machine_arn = None
        result = self.pipeline.process_video("s3://bucket/video.mp4")
        self.assertEqual(result.status, "mock_success")

class TestBenchmarkService(unittest.TestCase):
    def setUp(self):
        self.mock_ecs_client = MagicMock()
        with patch('boto3.client', return_value=self.mock_ecs_client):
            self.service = BenchmarkService()
        
        # Configure service with mock env vars
        self.service.ecs_cluster = "test-cluster"
        self.service.ecs_task_definition = "test-task-def"
        self.service.ecs_subnets = ["subnet-1"]
        self.service.ecs_security_groups = ["sg-1"]

    def test_start_benchmark_ecs(self):
        # Setup mock response
        self.mock_ecs_client.run_task.return_value = {
            'tasks': [{'taskArn': 'arn:aws:ecs:us-east-1:123456789012:task/test-cluster/task-id'}]
        }

        config = {
            "use_ecs": True,
            "operation": "search",
            "queries": 50
        }
        backends = ["s3vector"]

        # Run async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        job_id = loop.run_until_complete(self.service.start_benchmark(backends, config))
        loop.close()

        # Verify job created
        self.assertIn(job_id, self.service.jobs)
        job = self.service.jobs[job_id]
        self.assertEqual(job["status"], "submitted")
        self.assertEqual(job["task_arn"], 'arn:aws:ecs:us-east-1:123456789012:task/test-cluster/task-id')

        # Verify ECS run_task call
        self.mock_ecs_client.run_task.assert_called_once()
        call_kwargs = self.mock_ecs_client.run_task.call_args[1]
        
        self.assertEqual(call_kwargs['cluster'], "test-cluster")
        self.assertEqual(call_kwargs['launchType'], "FARGATE")
        
        # Check overrides
        overrides = call_kwargs['overrides']['containerOverrides'][0]
        self.assertEqual(overrides['name'], 'benchmark-runner')
        
        # Check command args
        cmd = overrides['command']
        self.assertIn("scripts/benchmark_backend.py", cmd)
        self.assertIn("--backend", cmd)
        self.assertIn("s3vector", cmd)
        self.assertIn("--operation", cmd)
        self.assertIn("search", cmd)
        self.assertIn("--queries", cmd)
        self.assertIn("50", cmd)

    def test_get_status_ecs_running(self):
        job_id = "test-job-id"
        task_arn = "arn:aws:ecs:task-id"
        self.service.jobs[job_id] = {
            "status": "submitted",
            "type": "ecs",
            "task_arn": task_arn
        }

        self.mock_ecs_client.describe_tasks.return_value = {
            'tasks': [{'lastStatus': 'RUNNING'}]
        }

        status = self.service.get_status(job_id)
        self.assertEqual(status["status"], "running")
        self.assertEqual(status["ecs_status"], "RUNNING")

    def test_get_status_ecs_completed(self):
        job_id = "test-job-id"
        task_arn = "arn:aws:ecs:task-id"
        self.service.jobs[job_id] = {
            "status": "running",
            "type": "ecs",
            "task_arn": task_arn
        }

        self.mock_ecs_client.describe_tasks.return_value = {
            'tasks': [{
                'lastStatus': 'STOPPED',
                'containers': [{'exitCode': 0}]
            }]
        }

        status = self.service.get_status(job_id)
        self.assertEqual(status["status"], "completed")

class TestVideoDatasetManager(unittest.TestCase):
    def setUp(self):
        self.config = VideoDatasetConfig(
            name="test-dataset",
            source="direct_url",
            video_urls=["http://example.com/video.mp4"],
            s3_bucket="test-bucket"
        )
        self.manager = VideoDatasetManager(self.config)

    @patch('requests.get')
    @patch('boto3.client')
    def test_download_and_upload_video(self, mock_boto, mock_requests):
        # Mock requests response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'video/mp4'}
        mock_response.raw = MagicMock()
        mock_requests.return_value = mock_response

        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        # Create metadata
        metadata = VideoMetadata(
            video_id="test-video",
            source_url="http://example.com/video.mp4",
            s3_uri=None
        )

        # Call method
        result = self.manager._download_and_upload_video(metadata)

        # Verify result
        self.assertTrue(result.downloaded)
        self.assertTrue(result.uploaded_to_s3)
        self.assertEqual(result.s3_uri, "s3://test-bucket/datasets/test-dataset/test-video.mp4")

        # Verify S3 upload
        mock_s3.upload_fileobj.assert_called_once()
        call_args = mock_s3.upload_fileobj.call_args
        self.assertEqual(call_args[0][1], "test-bucket")
        self.assertEqual(call_args[0][2], "datasets/test-dataset/test-video.mp4")

if __name__ == '__main__':
    unittest.main()