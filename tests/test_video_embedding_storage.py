"""
Tests for Video Embedding Storage Service

These tests verify the integration between TwelveLabs video processing results
and S3 Vector storage, including metadata handling and end-to-end workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime, timezone

from src.services.video_embedding_storage import (
    VideoEmbeddingStorageService,
    VideoVectorMetadata,
    VideoStorageResult
)
from src.services.twelvelabs_video_processing import VideoEmbeddingResult
from src.exceptions import VectorEmbeddingError, ValidationError


class TestVideoVectorMetadata:
    """Test the VideoVectorMetadata class."""
    
    def test_basic_metadata_creation(self):
        """Test creating basic video vector metadata."""
        metadata = VideoVectorMetadata(
            video_source_uri="s3://bucket/video.mp4",
            video_duration_sec=120.0,
            start_sec=10.0,
            end_sec=15.0,
            segment_duration_sec=5.0
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["content_type"] == "video"
        assert metadata_dict["video_source_uri"] == "s3://bucket/video.mp4"
        assert metadata_dict["video_duration_sec"] == 120.0
        assert metadata_dict["start_sec"] == 10.0
        assert metadata_dict["end_sec"] == 15.0
        assert metadata_dict["segment_duration_sec"] == 5.0
        assert metadata_dict["embedding_option"] == "visual-text"
        assert metadata_dict["model_id"] == "twelvelabs.marengo-embed-2-7-v1:0"
        assert metadata_dict["embedding_dimension"] == 1024
        assert "processed_at" in metadata_dict
    
    def test_metadata_with_optional_fields(self):
        """Test metadata with optional media company fields."""
        metadata = VideoVectorMetadata(
            video_source_uri="s3://bucket/episode.mp4",
            video_duration_sec=1800.0,
            title="Season 1 Episode 1",
            content_id="ep-001",
            series_id="series-123",
            season=1,
            episode=1,
            genre=["drama", "thriller"],
            tags=["action", "suspense"],
            quality_score=0.95,
            confidence_score=0.87
        )
        
        metadata_dict = metadata.to_dict()
        
        assert metadata_dict["title"] == "Season 1 Episode 1"
        assert metadata_dict["content_id"] == "ep-001"
        assert metadata_dict["series_id"] == "series-123"
        assert metadata_dict["season"] == 1
        assert metadata_dict["episode"] == 1
        assert metadata_dict["genre"] == ["drama", "thriller"]
        assert metadata_dict["tags"] == ["action", "suspense"]
        assert metadata_dict["quality_score"] == 0.95
        assert metadata_dict["confidence_score"] == 0.87


class TestVideoEmbeddingStorageService:
    """Test the VideoEmbeddingStorageService class."""
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Mock S3VectorStorageManager."""
        with patch('src.services.video_embedding_storage.S3VectorStorageManager') as mock:
            yield mock.return_value
    
    @pytest.fixture
    def mock_s3_client(self):
        """Mock S3 client."""
        with patch('src.services.video_embedding_storage.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_s3_client.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def service(self, mock_storage_manager, mock_s3_client):
        """Create VideoEmbeddingStorageService instance with mocked dependencies."""
        return VideoEmbeddingStorageService()
    
    @pytest.fixture
    def sample_video_result(self):
        """Create sample VideoEmbeddingResult for testing."""
        embeddings = [
            {
                'embedding': [0.1] * 1024,
                'startSec': 0.0,
                'endSec': 5.0,
                'embeddingOption': 'visual-text'
            },
            {
                'embedding': [0.2] * 1024,
                'startSec': 5.0,
                'endSec': 10.0,
                'embeddingOption': 'audio'
            }
        ]
        
        return VideoEmbeddingResult(
            embeddings=embeddings,
            input_source="s3://bucket/test-video.mp4",
            model_id="twelvelabs.marengo-embed-2-7-v1:0",
            processing_time_ms=5000,
            total_segments=2,
            video_duration_sec=10.0
        )
    
    def test_store_video_embeddings_success(self, service, mock_storage_manager, sample_video_result):
        """Test successful storage of video embeddings."""
        # Mock successful put_vectors response
        mock_storage_manager.put_vectors.return_value = {"stored_count": 2}
        
        index_arn = "arn:aws:s3vectors:us-east-1:123456789012:bucket/test/index/video"
        
        result = service.store_video_embeddings(
            video_result=sample_video_result,
            index_arn=index_arn,
            base_metadata={"content_id": "test-001"},
            key_prefix="test-video"
        )
        
        assert isinstance(result, VideoStorageResult)
        assert result.stored_segments == 2
        assert result.index_arn == index_arn
        assert result.total_vectors_stored == 2
        assert len(result.vector_keys) == 2
        assert result.vector_keys[0] == "test-video-segment-0000"
        assert result.vector_keys[1] == "test-video-segment-0001"
        
        # Verify put_vectors was called with correct data
        mock_storage_manager.put_vectors.assert_called_once()
        call_args = mock_storage_manager.put_vectors.call_args
        assert call_args[1]["index_arn"] == index_arn
        
        vectors_data = call_args[1]["vectors_data"]
        assert len(vectors_data) == 2
        
        # Check first vector
        vector1 = vectors_data[0]
        assert vector1["key"] == "test-video-segment-0000"
        assert vector1["data"]["float32"] == [0.1] * 1024
        assert vector1["metadata"]["content_type"] == "video"
        assert vector1["metadata"]["start_sec"] == 0.0
        assert vector1["metadata"]["end_sec"] == 5.0
        assert vector1["metadata"]["embedding_option"] == "visual-text"
        assert vector1["metadata"]["content_id"] == "test-001"
    
    def test_store_video_embeddings_empty_embeddings(self, service):
        """Test error handling for empty embeddings."""
        empty_result = VideoEmbeddingResult(
            embeddings=[],
            input_source="s3://bucket/empty.mp4",
            model_id="test-model",
            total_segments=0
        )
        
        with pytest.raises(ValidationError, match="contains no embeddings"):
            service.store_video_embeddings(
                video_result=empty_result,
                index_arn="test-arn"
            )
    
    def test_store_video_embeddings_missing_index_arn(self, service, sample_video_result):
        """Test error handling for missing index ARN."""
        with pytest.raises(ValidationError, match="Index ARN is required"):
            service.store_video_embeddings(
                video_result=sample_video_result,
                index_arn=""
            )
    
    def test_process_and_store_from_s3_output_success(self, service, mock_s3_client, mock_storage_manager):
        """Test processing TwelveLabs results from S3 output location."""
        # Mock S3 list_objects_v2 response
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'results/output.json'},
                {'Key': 'results/manifest.json'}
            ]
        }
        
        # Mock S3 get_object response with sample TwelveLabs output
        sample_output = [
            {
                'embedding': [0.3] * 1024,
                'startSec': 0.0,
                'endSec': 5.0,
                'embeddingOption': 'visual-text'
            }
        ]
        
        mock_response = Mock()
        mock_response.read.return_value = json.dumps(sample_output).encode()
        mock_s3_client.get_object.return_value = {'Body': mock_response}
        
        # Mock storage manager
        mock_storage_manager.put_vectors.return_value = {"stored_count": 1}
        
        result = service.process_and_store_from_s3_output(
            output_s3_uri="s3://output-bucket/results/",
            index_arn="test-index-arn",
            video_source_uri="s3://input-bucket/video.mp4"
        )
        
        assert isinstance(result, VideoStorageResult)
        assert result.stored_segments == 1
        assert result.total_vectors_stored == 1
        
        # Verify S3 operations
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="output-bucket",
            Prefix="results/"
        )
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="output-bucket",
            Key="results/output.json"
        )
    
    def test_process_and_store_from_s3_output_no_results(self, service, mock_s3_client):
        """Test error handling when no results found in S3 output location."""
        # Mock empty S3 response
        mock_s3_client.list_objects_v2.return_value = {'Contents': []}
        
        with pytest.raises(VectorEmbeddingError, match="No results found"):
            service.process_and_store_from_s3_output(
                output_s3_uri="s3://empty-bucket/results/",
                index_arn="test-index-arn",
                video_source_uri="s3://input-bucket/video.mp4"
            )
    
    def test_process_and_store_from_s3_output_invalid_uri(self, service):
        """Test error handling for invalid S3 URI."""
        with pytest.raises(VectorEmbeddingError, match="Invalid S3 output URI"):
            service.process_and_store_from_s3_output(
                output_s3_uri="invalid-uri",
                index_arn="test-index-arn",
                video_source_uri="s3://input-bucket/video.mp4"
            )
    
    @patch('src.services.video_embedding_storage.TwelveLabsVideoProcessingService')
    def test_process_video_end_to_end_success(self, mock_video_service_class, service, mock_storage_manager):
        """Test end-to-end video processing workflow."""
        # Mock TwelveLabs service
        mock_video_service = Mock()
        mock_video_service_class.return_value = mock_video_service
        
        # Mock TwelveLabs processing result
        mock_video_result = VideoEmbeddingResult(
            embeddings=[{'embedding': [0.1] * 1024, 'startSec': 0.0, 'endSec': 5.0, 'embeddingOption': 'visual-text'}],
            input_source="s3://bucket/video.mp4",
            model_id="twelvelabs.marengo-embed-2-7-v1:0",
            processing_time_ms=10000,
            total_segments=1,
            video_duration_sec=5.0
        )
        mock_video_service.process_video_sync.return_value = mock_video_result
        
        # Mock storage manager
        mock_storage_manager.put_vectors.return_value = {"stored_count": 1}
        
        result = service.process_video_end_to_end(
            video_s3_uri="s3://bucket/video.mp4",
            index_arn="test-index-arn",
            embedding_options=["visual-text"],
            base_metadata={"content_id": "test-video"}
        )
        
        assert result["summary"]["success"] is True
        assert result["summary"]["segments_processed"] == 1
        assert result["summary"]["vectors_stored"] == 1
        assert result["video_processing"]["model_id"] == "twelvelabs.marengo-embed-2-7-v1:0"
        assert result["vector_storage"]["stored_segments"] == 1
        
        # Verify TwelveLabs service was called correctly
        mock_video_service.process_video_sync.assert_called_once()
        call_args = mock_video_service.process_video_sync.call_args
        assert call_args[1]["video_s3_uri"] == "s3://bucket/video.mp4"
        assert call_args[1]["embedding_options"] == ["visual-text"]
    
    @patch('src.services.video_embedding_storage.TwelveLabsVideoProcessingService')
    def test_process_video_end_to_end_failure(self, mock_video_service_class, service):
        """Test end-to-end video processing with failure."""
        # Mock TwelveLabs service to raise exception
        mock_video_service = Mock()
        mock_video_service_class.return_value = mock_video_service
        mock_video_service.process_video_sync.side_effect = Exception("Processing failed")
        
        result = service.process_video_end_to_end(
            video_s3_uri="s3://bucket/video.mp4",
            index_arn="test-index-arn"
        )
        
        assert result["summary"]["success"] is False
        assert "Processing failed" in result["summary"]["error"]
        assert result["summary"]["segments_processed"] == 0
        assert result["summary"]["vectors_stored"] == 0
        assert result["video_processing"] is None
        assert result["vector_storage"] is None
    
    def test_create_video_index(self, service, mock_storage_manager):
        """Test creating a video index."""
        mock_storage_manager.create_vector_index.return_value = {
            "index_arn": "arn:aws:s3vectors:us-east-1:123456789012:bucket/test/index/video"
        }
        
        index_arn = service.create_video_index(
            bucket_name="test-bucket",
            index_name="video-index",
            embedding_dimension=1024,
            distance_metric="cosine"
        )
        
        assert index_arn == "arn:aws:s3vectors:us-east-1:123456789012:bucket/test/index/video"
        
        mock_storage_manager.create_vector_index.assert_called_once_with(
            bucket_name="test-bucket",
            index_name="video-index",
            dimensions=1024,
            distance_metric="cosine",
            data_type="float32"
        )
    
    def test_search_video_segments(self, service, mock_storage_manager):
        """Test searching video segments."""
        # Mock query_vectors response
        mock_storage_manager.query_vectors.return_value = {
            "vectors": [
                {
                    "key": "video-test-segment-0000",
                    "distance": 0.2,
                    "metadata": {
                        "content_type": "video",
                        "video_source_uri": "s3://bucket/video.mp4",
                        "start_sec": 0.0,
                        "end_sec": 5.0,
                        "segment_duration_sec": 5.0,
                        "embedding_option": "visual-text",
                        "title": "Test Video",
                        "content_id": "test-001"
                    }
                }
            ],
            "query_time_ms": 50
        }
        
        query_vector = [0.1] * 1024
        result = service.search_video_segments(
            index_arn="test-index-arn",
            query_vector=query_vector,
            top_k=5,
            time_range_filter={"start_sec": 0, "end_sec": 10},
            content_filters={"content_id": "test-001"}
        )
        
        assert result["total_results"] == 1
        assert result["query_time_ms"] == 50
        
        segment = result["segments"][0]
        assert segment["key"] == "video-test-segment-0000"
        assert segment["similarity_score"] == 0.8  # 1.0 - 0.2
        assert segment["video_source"] == "s3://bucket/video.mp4"
        assert segment["start_sec"] == 0.0
        assert segment["end_sec"] == 5.0
        assert segment["title"] == "Test Video"
        assert segment["content_id"] == "test-001"
        
        # Verify query was called with correct filters
        mock_storage_manager.query_vectors.assert_called_once()
        call_args = mock_storage_manager.query_vectors.call_args
        assert call_args[1]["index_arn"] == "test-index-arn"
        assert call_args[1]["query_vector"] == query_vector
        assert call_args[1]["top_k"] == 5
        
        metadata_filter = call_args[1]["metadata_filter"]
        assert metadata_filter["content_type"] == "video"
        assert metadata_filter["content_id"] == "test-001"
    
    def test_estimate_storage_cost(self, service):
        """Test storage cost estimation."""
        cost_estimate = service.estimate_storage_cost(
            num_segments=100,
            embedding_dimension=1024,
            metadata_size_bytes=600
        )
        
        assert "storage_cost_usd_monthly" in cost_estimate
        assert "estimated_query_cost_usd_monthly" in cost_estimate
        assert "total_estimated_cost_usd_monthly" in cost_estimate
        assert "storage_size_gb" in cost_estimate
        assert cost_estimate["segments"] == 100
        
        # Verify reasonable cost estimates
        assert cost_estimate["storage_cost_usd_monthly"] > 0
        assert cost_estimate["total_estimated_cost_usd_monthly"] > 0
        assert cost_estimate["storage_size_gb"] > 0


class TestVideoEmbeddingIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @pytest.fixture
    def service(self):
        """Create service with mocked dependencies for integration tests."""
        with patch('src.services.video_embedding_storage.S3VectorStorageManager') as mock_storage, \
             patch('src.services.video_embedding_storage.aws_client_factory') as mock_factory:
            
            mock_factory.get_s3_client.return_value = Mock()
            service = VideoEmbeddingStorageService()
            service.storage_manager = mock_storage.return_value
            return service
    
    def test_media_company_workflow(self, service):
        """Test complete workflow for media company use case."""
        # Mock TwelveLabs result for a TV episode
        episode_result = VideoEmbeddingResult(
            embeddings=[
                {
                    'embedding': [0.1] * 1024,
                    'startSec': 0.0,
                    'endSec': 5.0,
                    'embeddingOption': 'visual-text'
                },
                {
                    'embedding': [0.2] * 1024,
                    'startSec': 5.0,
                    'endSec': 10.0,
                    'embeddingOption': 'audio'
                }
            ],
            input_source="s3://media-bucket/series/season1/episode1.mp4",
            model_id="twelvelabs.marengo-embed-2-7-v1:0",
            processing_time_ms=15000,
            total_segments=2,
            video_duration_sec=10.0
        )
        
        # Mock storage success
        service.storage_manager.put_vectors.return_value = {"stored_count": 2}
        
        # Media company metadata
        media_metadata = {
            "title": "The Great Adventure",
            "series_id": "series-001",
            "season": 1,
            "episode": 1,
            "genre": ["drama", "adventure"],
            "content_id": "ep-s01e01",
            "actors": ["John Doe", "Jane Smith"],
            "director": "Famous Director",
            "release_date": "2024-01-15"
        }
        
        result = service.store_video_embeddings(
            video_result=episode_result,
            index_arn="arn:aws:s3vectors:us-east-1:123456789012:bucket/media/index/episodes",
            base_metadata=media_metadata,
            key_prefix="series-001-s01e01"
        )
        
        assert result.stored_segments == 2
        assert result.total_vectors_stored == 2
        
        # Verify metadata was properly incorporated
        call_args = service.storage_manager.put_vectors.call_args
        vectors_data = call_args[1]["vectors_data"]
        
        first_vector = vectors_data[0]
        metadata = first_vector["metadata"]
        assert metadata["title"] == "The Great Adventure"
        assert metadata["series_id"] == "series-001"
        assert metadata["season"] == 1
        assert metadata["episode"] == 1
        assert metadata["content_id"] == "ep-s01e01"
        assert metadata["genre"] == ["drama", "adventure"]
        assert metadata["embedding_option"] == "visual-text"
        assert metadata["start_sec"] == 0.0
        assert metadata["end_sec"] == 5.0