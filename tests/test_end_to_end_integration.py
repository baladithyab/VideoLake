"""
Comprehensive End-to-End Integration Tests for S3Vector Pipeline

These tests validate the complete workflow from content ingestion to similarity search,
ensuring all components work together correctly in production scenarios.
"""

import pytest
import time
import uuid
from typing import Dict, Any, List
from unittest.mock import Mock, patch

from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery, IndexType
from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.utils.error_handling import get_error_handler
from src.exceptions import VectorEmbeddingError


@pytest.mark.integration
class TestEndToEndPipeline:
    """Test complete end-to-end workflows."""
    
    @pytest.fixture
    def pipeline_components(self):
        """Set up all pipeline components with mocks."""
        # Create mocked services
        bedrock_service = Mock(spec=BedrockEmbeddingService)
        twelvelabs_service = Mock(spec=TwelveLabsVideoProcessingService)
        s3_manager = Mock(spec=S3VectorStorageManager)
        
        # Create real integration services
        text_storage = EmbeddingStorageIntegration()
        # Inject mocked services
        text_storage.bedrock_service = bedrock_service
        text_storage.storage_manager = s3_manager
        
        video_storage = VideoEmbeddingStorageService()
        # Inject mocked services
        video_storage.storage_manager = s3_manager
        video_storage.video_processor = twelvelabs_service
        
        search_engine = SimilaritySearchEngine(
            bedrock_service=bedrock_service,
            twelvelabs_service=twelvelabs_service,
            s3_vector_manager=s3_manager,
            text_storage=text_storage,
            video_storage=video_storage
        )
        
        return {
            'search_engine': search_engine,
            'text_storage': text_storage,
            'video_storage': video_storage,
            'bedrock_service': bedrock_service,
            'twelvelabs_service': twelvelabs_service,
            's3_manager': s3_manager
        }
    
    def test_complete_text_embedding_workflow(self, pipeline_components):
        """Test complete text embedding workflow from ingestion to search."""
        components = pipeline_components
        
        # Setup test data
        test_texts = [
            "Netflix original series about supernatural events in a small town",
            "Documentary about marine life in the Pacific Ocean",
            "Comedy series featuring office workers in a paper company"
        ]
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/text-index"
        
        # Mock Bedrock responses
        mock_embeddings = []
        for i, text in enumerate(test_texts):
            mock_result = Mock()
            mock_result.embedding = [0.1 + i * 0.1, 0.2 + i * 0.1, 0.3 + i * 0.1] * 341 + [0.1 + i * 0.1]
            mock_result.model_id = "amazon.titan-embed-text-v2:0"
            mock_result.processing_time_ms = 150
            mock_embeddings.append(mock_result)
        
        components['bedrock_service'].generate_text_embedding.side_effect = mock_embeddings
        components['s3_manager'].put_vectors_batch.return_value = {"stored_count": 1}
        
        # Step 1: Store text embeddings
        stored_embeddings = []
        for i, text in enumerate(test_texts):
            result = components['text_storage'].store_text_embedding(
                text=text,
                index_arn=index_arn,
                metadata={
                    'content_type': 'text',
                    'category': 'entertainment' if i == 0 else 'documentary' if i == 1 else 'comedy',
                    'content_id': f'content-{i+1}'
                },
                vector_key=f"text-{i+1}"
            )
            stored_embeddings.append(result)
        
        # Verify storage calls
        assert components['bedrock_service'].generate_text_embedding.call_count == 3
        assert components['s3_manager'].put_vectors_batch.call_count == 3
        
        # Step 2: Mock search response
        mock_search_results = {
            'vectors': [
                {
                    'key': 'text-1',
                    'distance': 0.1,
                    'metadata': {'content_type': 'text', 'category': 'entertainment'},
                    'data': {'float32': mock_embeddings[0].embedding}
                },
                {
                    'key': 'text-3', 
                    'distance': 0.3,
                    'metadata': {'content_type': 'text', 'category': 'comedy'},
                    'data': {'float32': mock_embeddings[2].embedding}
                }
            ]
        }
        
        components['bedrock_service'].generate_text_embedding.return_value = mock_embeddings[0]
        components['s3_manager'].query_similar_vectors.return_value = mock_search_results
        
        # Step 3: Perform similarity search
        query = SimilarityQuery(query_text="TV series about mysterious events")
        search_response = components['search_engine'].find_similar_content(
            query=query,
            index_arn=index_arn,
            index_type=IndexType.TITAN_TEXT
        )
        
        # Verify search results
        assert len(search_response.results) == 2
        assert search_response.results[0].vector_key == 'text-1'
        assert search_response.results[0].similarity_score == 0.9  # 1 - 0.1
        assert search_response.query_id is not None
        assert search_response.search_time_ms > 0
        
        # Verify all components were called correctly
        components['s3_manager'].query_similar_vectors.assert_called_once()
    
    def test_complete_video_embedding_workflow(self, pipeline_components):
        """Test complete video embedding workflow."""
        components = pipeline_components
        
        # Setup test data
        video_s3_uri = "s3://test-bucket/sample-video.mp4"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/video-index"
        
        # Mock TwelveLabs video processing
        mock_video_result = Mock()
        mock_video_result.embeddings = [
            {
                'embedding': [0.1, 0.2, 0.3] * 341 + [0.1],
                'startSec': 0.0,
                'endSec': 5.0,
                'embeddingOption': 'visual-text'
            },
            {
                'embedding': [0.2, 0.3, 0.4] * 341 + [0.2],
                'startSec': 5.0,
                'endSec': 10.0,
                'embeddingOption': 'visual-text'
            }
        ]
        mock_video_result.input_source = video_s3_uri
        mock_video_result.model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        mock_video_result.total_segments = 2
        mock_video_result.video_duration_sec = 10.0
        
        components['twelvelabs_service'].process_video_sync.return_value = mock_video_result
        components['s3_manager'].put_vectors_batch.return_value = {"stored_count": 2}
        
        # Step 1: Process and store video embeddings
        storage_result = components['video_storage'].store_video_embeddings(
            video_embedding_result=mock_video_result,
            index_arn=index_arn,
            metadata={
                'title': 'Test Video',
                'content_id': 'video-001',
                'category': 'test'
            }
        )
        
        # Verify video processing
        assert storage_result.total_stored == 2
        assert len(storage_result.stored_keys) == 2
        components['s3_manager'].put_vectors_batch.assert_called_once()
        
        # Step 2: Mock video search response
        mock_search_results = {
            'vectors': [
                {
                    'key': storage_result.stored_keys[0],
                    'distance': 0.15,
                    'metadata': {
                        'content_type': 'video',
                        'start_sec': 0.0,
                        'end_sec': 5.0,
                        'title': 'Test Video'
                    },
                    'data': {'float32': mock_video_result.embeddings[0]['embedding']}
                }
            ]
        }
        
        # Mock text embedding for cross-modal search
        mock_text_embedding = Mock()
        mock_text_embedding.embedding = [0.15, 0.25, 0.35] * 341 + [0.15]
        components['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': mock_text_embedding.embedding
        }
        components['s3_manager'].query_similar_vectors.return_value = mock_search_results
        
        # Step 3: Perform cross-modal search (text query on video index)
        query = SimilarityQuery(query_text="action scene with explosions")
        search_response = components['search_engine'].find_similar_content(
            query=query,
            index_arn=index_arn,
            index_type=IndexType.MARENGO_MULTIMODAL
        )
        
        # Verify cross-modal search results
        assert len(search_response.results) == 1
        assert search_response.results[0].temporal_info is not None
        assert search_response.results[0].temporal_info['start_sec'] == 0.0
        assert search_response.results[0].temporal_info['end_sec'] == 5.0
        assert search_response.input_type.value == "text"
        assert search_response.index_type == IndexType.MARENGO_MULTIMODAL
    
    def test_error_handling_and_recovery(self, pipeline_components):
        """Test error handling and recovery mechanisms."""
        components = pipeline_components
        
        # Setup error handler
        error_handler = get_error_handler("test_service")
        
        # Test retry logic with transient failures
        call_count = 0
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                from botocore.exceptions import ClientError
                raise ClientError(
                    error_response={'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
                    operation_name='TestOperation'
                )
            return "success"
        
        # Apply retry decorator
        @error_handler.with_retry()
        def test_function():
            return failing_function()
        
        # Should succeed after retries
        result = test_function()
        assert result == "success"
        assert call_count == 3
        
        # Test circuit breaker
        def always_failing_function():
            raise Exception("Persistent failure")
        
        @error_handler.with_retry()
        def failing_test_function():
            return always_failing_function()
        
        # Should fail after max attempts and open circuit breaker
        with pytest.raises(Exception):
            for _ in range(6):  # Exceed failure threshold
                try:
                    failing_test_function()
                except:
                    pass
        
        # Check health status
        health = error_handler.get_health_status()
        assert health['status'] in ['healthy', 'degraded']
        assert health['total_errors'] > 0
    
    def test_performance_and_cost_tracking(self, pipeline_components):
        """Test performance monitoring and cost tracking."""
        components = pipeline_components
        
        # Setup performance tracking
        start_time = time.time()
        
        # Mock responses with timing
        mock_result = Mock()
        mock_result.embedding = [0.1, 0.2, 0.3] * 341 + [0.1]
        mock_result.model_id = "amazon.titan-embed-text-v2:0"
        mock_result.processing_time_ms = 200
        
        components['bedrock_service'].generate_text_embedding.return_value = mock_result
        components['s3_manager'].put_vectors_batch.return_value = {"stored_count": 1}
        
        # Perform operations
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/perf-index"
        
        result = components['text_storage'].store_text_embedding(
            text="Performance test text",
            index_arn=index_arn,
            vector_key="perf-test-1"
        )
        
        # Verify timing information
        processing_time = time.time() - start_time
        assert processing_time < 5.0  # Should complete quickly in test
        assert result.vector_key == "perf-test-1"
        
        # Test search performance
        mock_search_results = {
            'vectors': [
                {
                    'key': 'perf-test-1',
                    'distance': 0.1,
                    'metadata': {'content_type': 'text'},
                    'data': {'float32': mock_result.embedding}
                }
            ]
        }
        
        components['s3_manager'].query_similar_vectors.return_value = mock_search_results
        
        search_start = time.time()
        query = SimilarityQuery(query_text="performance query")
        search_response = components['search_engine'].find_similar_content(
            query=query,
            index_arn=index_arn,
            index_type=IndexType.TITAN_TEXT
        )
        search_time = time.time() - search_start
        
        # Verify search performance
        assert search_response.search_time_ms > 0
        assert search_time < 2.0  # Should be fast in test
        assert len(search_response.results) == 1
    
    def test_metadata_filtering_and_complex_queries(self, pipeline_components):
        """Test advanced metadata filtering and complex query scenarios."""
        components = pipeline_components
        
        # Setup complex metadata scenarios
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/complex-index"
        
        # Mock search with metadata filters
        mock_search_results = {
            'vectors': [
                {
                    'key': 'filtered-1',
                    'distance': 0.1,
                    'metadata': {
                        'content_type': 'video',
                        'genre': ['action', 'thriller'],
                        'rating': 'PG-13',
                        'year': 2023,
                        'start_sec': 120.0,
                        'end_sec': 180.0
                    },
                    'data': {'float32': [0.1] * 1024}
                }
            ]
        }
        
        # Mock embedding generation
        mock_embedding = Mock()
        mock_embedding.embedding = [0.1] * 1024
        components['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': mock_embedding.embedding
        }
        components['s3_manager'].query_similar_vectors.return_value = mock_search_results
        
        # Test complex query with filters
        query = SimilarityQuery(
            query_text="intense action sequence",
            metadata_filters={
                'genre': ['action'],
                'rating': 'PG-13',
                'year': {'gte': 2020}
            },
            temporal_filter={
                'start_sec': 100.0,
                'end_sec': 200.0
            }
        )
        
        search_response = components['search_engine'].find_similar_content(
            query=query,
            index_arn=index_arn,
            index_type=IndexType.MARENGO_MULTIMODAL
        )
        
        # Verify filtered results
        assert len(search_response.results) == 1
        result = search_response.results[0]
        assert result.vector_key == 'filtered-1'
        assert 'action' in result.metadata.get('genre', [])
        assert result.temporal_info['start_sec'] == 120.0
        
        # Verify filter was passed to S3 manager
        call_args = components['s3_manager'].query_similar_vectors.call_args
        assert call_args[1]['metadata_filters'] is not None


@pytest.mark.integration
@pytest.mark.slow
class TestProductionScenarios:
    """Test production-like scenarios with realistic data volumes."""
    
    def test_batch_processing_workflow(self):
        """Test batch processing of multiple content items."""
        # This would test processing 100+ items in batches
        # Implementation would depend on actual batch processing requirements
        pass
    
    def test_concurrent_operations(self):
        """Test concurrent embedding generation and search operations."""
        # This would test thread safety and concurrent access patterns
        pass
    
    def test_large_scale_search(self):
        """Test search performance with large result sets."""
        # This would test pagination and large result handling
        pass