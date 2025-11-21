"""
Tests for the Ingestion Pipeline.
"""

import unittest
from unittest.mock import MagicMock, patch
from src.ingestion.pipeline import VideoIngestionPipeline, IngestionResult
from src.services.twelvelabs_video_processing import VideoEmbeddingResult

class TestVideoIngestionPipeline(unittest.TestCase):

    @patch('src.ingestion.pipeline.TwelveLabsVideoProcessingService')
    @patch('scripts.backend_adapters.get_backend_adapter')
    def test_process_video_marengo_success(self, mock_get_adapter, MockProcessingService):
        # Setup Mocks
        mock_service = MockProcessingService.return_value
        
        # Mock embedding result
        mock_embedding_result = VideoEmbeddingResult(
            embeddings=[
                {'embedding': [0.1, 0.2], 'startSec': 0, 'endSec': 5, 'text': 'segment 1'},
                {'embedding': [0.3, 0.4], 'startSec': 5, 'endSec': 10, 'text': 'segment 2'}
            ],
            input_source="s3://test-bucket/video.mp4",
            model_id="marengo",
            processing_time_ms=100,
            total_segments=2,
            video_duration_sec=10
        )
        mock_service.process_video_sync.return_value = mock_embedding_result

        # Mock backend adapter
        mock_adapter = MagicMock()
        mock_adapter.index_vectors.return_value = {"success": True}
        mock_get_adapter.return_value = mock_adapter

        # Initialize Pipeline
        pipeline = VideoIngestionPipeline()
        
        # Run Pipeline
        result = pipeline.process_video(
            video_path="s3://test-bucket/video.mp4",
            model_type="marengo",
            backend_types=["s3vector"]
        )

        # Assertions
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.embeddings_count, 2)
        self.assertIn("s3vector", result.backends_updated)
        
        # Verify service call
        mock_service.process_video_sync.assert_called_once()
        
        # Verify adapter call
        mock_get_adapter.assert_called_with("s3vector")
        mock_adapter.index_vectors.assert_called_once()
        
        # Check arguments passed to index_vectors
        call_args = mock_adapter.index_vectors.call_args
        vectors = call_args[1]['vectors']
        metadata = call_args[1]['metadata']
        
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(metadata), 2)
        self.assertEqual(metadata[0]['source_uri'], "s3://test-bucket/video.mp4")

    @patch('src.ingestion.pipeline.TwelveLabsVideoProcessingService')
    def test_process_video_unsupported_model(self, MockProcessingService):
        pipeline = VideoIngestionPipeline()
        
        result = pipeline.process_video(
            video_path="s3://test-bucket/video.mp4",
            model_type="unsupported_model"
        )
        
        self.assertEqual(result.status, "failed")
        self.assertIn("Model type unsupported_model not yet supported", result.errors[0])

if __name__ == '__main__':
    unittest.main()