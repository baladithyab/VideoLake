#!/usr/bin/env python3
"""
Integration Tests for Enhanced Streamlit Workflow

Tests the complete end-to-end workflows including:
- Multi-index S3Vector coordination
- TwelveLabs API integration with Marengo 2.7
- Complete workflow: selection → upload → processing → retrieval
- Real AWS service integration (with mocking)
- Performance with large video collections
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock, call
import tempfile
import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
import time
import asyncio
from typing import Dict, List, Any, Optional
import requests_mock
import boto3
from moto import mock_s3, mock_opensearch

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

# Import components to test
from frontend.unified_streamlit_app import UnifiedStreamlitApp, ProcessedVideo
from src.services.similarity_search_engine import (
    SimilaritySearchEngine, 
    SimilarityQuery, 
    IndexType,
    TemporalFilter,
    SearchResponse
)
from src.services.unified_video_processing_service import UnifiedVideoProcessingService
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.exceptions import VectorStorageError


class TestCompleteWorkflowIntegration(unittest.TestCase):
    """Test complete end-to-end workflow integration."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.test_bucket = "test-s3vector-bucket"
        self.test_index_arn = f"arn:aws:s3vectors:us-east-1:123456789012:bucket/{self.test_bucket}/index/test-index"
        
        # Mock session state
        self.mock_session_state = {
            'processed_videos': {},
            'video_index_arn': self.test_index_arn,
            'costs': {'video_processing': 0, 'storage': 0, 'queries': 0, 'total': 0},
            'search_results': []
        }
        
        # Test video info
        self.test_video_info = {
            'video_id': 'test-video-123',
            'video_duration_sec': 120.0,
            'total_segments': 24,
            'segments': [
                {
                    'start_sec': i * 5.0,
                    'end_sec': (i + 1) * 5.0,
                    'embedding_visual_text': np.random.rand(1024).astype(np.float32),
                    'embedding_visual_image': np.random.rand(1024).astype(np.float32),
                    'embedding_audio': np.random.rand(1024).astype(np.float32),
                    'metadata': {
                        'segment_index': i,
                        'content_type': 'video',
                        'quality_score': 0.95
                    }
                }
                for i in range(24)
            ]
        }

    @mock_s3
    @patch('frontend.unified_streamlit_app.st')
    @patch('src.services.video_embedding_storage.VideoEmbeddingStorageService')
    @patch('src.services.twelvelabs_video_processing.TwelveLabsVideoProcessingService')
    def test_complete_video_processing_workflow(self, mock_video_processor, mock_storage_service, mock_st):
        """Test complete video processing workflow from upload to storage."""
        mock_st.session_state = self.mock_session_state
        
        # Set up S3 bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket=self.test_bucket)
        
        # Mock TwelveLabs processing result
        mock_processing_result = Mock()
        mock_processing_result.video_duration_sec = 120.0
        mock_processing_result.total_segments = 24
        mock_processing_result.segments = self.test_video_info['segments']
        mock_processing_result.metadata = {'processing_complete': True}
        
        mock_video_processor_instance = Mock()
        mock_video_processor_instance.process_video_sync.return_value = mock_processing_result
        mock_video_processor.return_value = mock_video_processor_instance
        
        # Mock storage result
        mock_storage_result = Mock()
        mock_storage_result.total_vectors_stored = 72  # 24 segments * 3 embedding types
        mock_storage_result.stored_segments = 24
        mock_storage_result.failed_segments = []
        
        mock_storage_instance = Mock()
        mock_storage_instance.store_video_embeddings.return_value = mock_storage_result
        mock_storage_service.return_value = mock_storage_instance
        
        # Initialize app and run processing
        app = UnifiedStreamlitApp()
        
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            temp_file.write(b'fake video content')
            video_path = temp_file.name
        
        try:
            result = app._process_video_real(
                video_path=video_path,
                video_s3_uri=None,
                segment_duration=5,
                embedding_options=["visual-text", "visual-image", "audio"],
                metadata={"title": "Test Video", "category": "test"}
            )
            
            # Verify processing was successful
            self.assertTrue(result['success'])
            self.assertEqual(result['segments'], 24)
            self.assertEqual(result['vectors'], 72)
            self.assertIn('cost', result)
            
            # Verify TwelveLabs was called
            mock_video_processor_instance.process_video_sync.assert_called_once()
            
            # Verify storage was called
            mock_storage_instance.store_video_embeddings.assert_called_once()
            
            # Verify video was added to processed videos
            self.assertEqual(len(mock_st.session_state['processed_videos']), 1)
            
        finally:
            os.unlink(video_path)

    @patch('frontend.unified_streamlit_app.st')
    @patch('src.services.similarity_search_engine.SimilaritySearchEngine')
    def test_multi_index_search_coordination(self, mock_search_engine, mock_st):
        """Test multi-index S3Vector coordination for searches."""
        mock_st.session_state = self.mock_session_state
        mock_st.session_state['processed_videos'] = {
            'video1': ProcessedVideo('v1', 'Video 1.mp4', 20, 100.0, 
                                   s3_uri='s3://bucket/video1.mp4', processing_type='real'),
            'video2': ProcessedVideo('v2', 'Video 2.mp4', 15, 75.0,
                                   s3_uri='s3://bucket/video2.mp4', processing_type='real')
        }
        
        # Mock search results
        mock_results = [
            Mock(
                vector_key='video1-segment-0001',
                similarity_score=0.95,
                start_sec=0.0,
                end_sec=5.0,
                metadata={'segment_index': 0, 'video_source_uri': 's3://bucket/video1.mp4'}
            ),
            Mock(
                vector_key='video2-segment-0003',
                similarity_score=0.87,
                start_sec=15.0,
                end_sec=20.0,
                metadata={'segment_index': 2, 'video_source_uri': 's3://bucket/video2.mp4'}
            )
        ]
        
        mock_response = Mock()
        mock_response.results = mock_results
        mock_response.total_results = len(mock_results)
        mock_response.query_id = 'test-query-123'
        
        mock_engine_instance = Mock()
        mock_engine_instance.find_similar_content.return_value = mock_response
        mock_search_engine.return_value = mock_engine_instance
        
        # Initialize app and perform search
        app = UnifiedStreamlitApp()
        
        results = app._search_real(
            search_type="Text-to-Video",
            query="test query",
            time_start=None,
            time_end=None,
            top_k=10,
            similarity_threshold=0.7,
            category_filter=[]
        )
        
        # Verify search was performed
        mock_engine_instance.find_similar_content.assert_called_once()
        
        # Verify results structure
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['video_name'], 'Video 1.mp4')
        self.assertEqual(results[1]['video_name'], 'Video 2.mp4')
        self.assertEqual(results[0]['score'], 0.95)
        self.assertEqual(results[1]['score'], 0.87)

    @patch('frontend.unified_streamlit_app.st')
    def test_batch_processing_workflow(self, mock_st):
        """Test batch processing workflow with multiple videos."""
        mock_st.session_state = self.mock_session_state
        
        # Create multiple test video files
        video_paths = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix=f'_video_{i}.mp4', delete=False) as temp_file:
                temp_file.write(f'fake video content {i}'.encode())
                video_paths.append(temp_file.name)
        
        try:
            app = UnifiedStreamlitApp()
            
            # Mock the processing methods to avoid actual AWS calls
            def mock_process_simulation(video_path, video_s3_uri, segment_duration, 
                                      embedding_options, metadata):
                video_name = os.path.basename(video_path)
                return {
                    'success': True,
                    'segments': 20,
                    'vectors': 60,  # 3 embedding options
                    'duration': 100.0,
                    'cost': 0.0,
                    'simulated': True,
                    'video_name': video_name
                }
            
            app._process_video_simulation = Mock(side_effect=mock_process_simulation)
            
            # Create mock progress components
            mock_progress_bar = Mock()
            mock_status_text = Mock()
            mock_st.progress.return_value = mock_progress_bar
            mock_st.empty.return_value = mock_status_text
            mock_st.container.return_value = Mock()
            mock_st.spinner.return_value.__enter__ = Mock(return_value=None)
            mock_st.spinner.return_value.__exit__ = Mock(return_value=None)
            
            # Test batch processing
            app._process_multiple_videos(
                video_paths=video_paths,
                segment_duration=5,
                embedding_options=["visual-text", "visual-image", "audio"],
                metadata={"category": "test"},
                use_real_aws=False,
                process_mode="Process All Together"
            )
            
            # Verify all videos were processed
            self.assertEqual(app._process_video_simulation.call_count, 3)
            
            # Verify progress tracking
            expected_progress_calls = [call(1/3), call(2/3), call(3/3)]
            mock_progress_bar.progress.assert_has_calls(expected_progress_calls)
            
            # Verify batch result was stored
            self.assertIn('last_processing_result', mock_st.session_state)
            result = mock_st.session_state['last_processing_result']
            self.assertEqual(result['total_videos'], 3)
            self.assertEqual(result['successful_videos'], 3)
            self.assertEqual(result['failed_videos'], 0)
            
        finally:
            # Clean up temp files
            for path in video_paths:
                try:
                    os.unlink(path)
                except:
                    pass

    @requests_mock.Mocker()
    @patch('frontend.unified_streamlit_app.st')
    def test_sample_video_download_integration(self, requests_mocker, mock_st):
        """Test sample video download integration."""
        mock_st.session_state = self.mock_session_state
        
        # Mock video download
        test_video_content = b'fake MP4 content' * 1000  # ~15KB
        requests_mocker.get(
            'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            content=test_video_content,
            headers={'content-length': str(len(test_video_content))}
        )
        
        # Mock Streamlit components
        mock_progress_bar = Mock()
        mock_st.progress.return_value = mock_progress_bar
        mock_placeholder = Mock()
        mock_placeholder.success = Mock()
        mock_placeholder.info = Mock()
        mock_st.empty.return_value = mock_placeholder
        
        app = UnifiedStreamlitApp()
        
        video_info = {
            'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
            'file_size_mb': 1,
            'description': 'Test video'
        }
        
        result_path = app._download_sample_video("Big Buck Bunny", video_info)
        
        # Verify download was successful
        self.assertIsNotNone(result_path)
        self.assertTrue(os.path.exists(result_path))
        
        # Verify file content
        with open(result_path, 'rb') as f:
            downloaded_content = f.read()
        self.assertEqual(downloaded_content, test_video_content)
        
        # Verify progress tracking was called
        mock_progress_bar.progress.assert_called()
        
        # Clean up
        os.unlink(result_path)

    @patch('frontend.unified_streamlit_app.st')
    def test_temporal_search_integration(self, mock_st):
        """Test temporal search integration with time filters."""
        mock_st.session_state = self.mock_session_state
        
        # Mock search engine with temporal filter support
        with patch('src.services.similarity_search_engine.SimilaritySearchEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            # Mock temporal search results
            mock_results = [
                Mock(
                    vector_key='video1-segment-0010',
                    similarity_score=0.92,
                    start_sec=50.0,
                    end_sec=55.0,
                    metadata={'segment_index': 10, 'video_source_uri': 's3://bucket/video1.mp4'}
                )
            ]
            
            mock_response = Mock()
            mock_response.results = mock_results
            mock_response.total_results = len(mock_results)
            mock_response.query_id = 'temporal-query-123'
            
            mock_engine.find_similar_content.return_value = mock_response
            
            app = UnifiedStreamlitApp()
            
            # Perform temporal search
            results = app._search_real(
                search_type="Temporal Search",
                query="action scene",
                time_start=45.0,
                time_end=60.0,
                top_k=5,
                similarity_threshold=0.8,
                category_filter=["action"]
            )
            
            # Verify temporal filter was used
            mock_engine.find_similar_content.assert_called_once()
            call_args = mock_engine.find_similar_content.call_args
            query_arg = call_args[1]['query']  # keyword argument
            
            # Verify temporal filter was set
            self.assertIsNotNone(query_arg.temporal_filter)
            self.assertEqual(query_arg.temporal_filter.start_time, 45.0)
            self.assertEqual(query_arg.temporal_filter.end_time, 60.0)
            
            # Verify results
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['start_sec'], 50.0)
            self.assertEqual(results[0]['end_sec'], 55.0)

    @patch('frontend.unified_streamlit_app.st')
    def test_video_to_video_search_integration(self, mock_st):
        """Test video-to-video search integration."""
        mock_st.session_state = self.mock_session_state
        mock_st.session_state['processed_videos'] = {
            'ref-video': ProcessedVideo('ref', 'Reference Video.mp4', 10, 50.0, processing_type='real')
        }
        
        with patch('src.services.similarity_search_engine.SimilaritySearchEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_engine_class.return_value = mock_engine
            
            # Mock similar video results
            mock_results = [
                Mock(
                    vector_key='similar-video-segment-0005',
                    similarity_score=0.88,
                    start_sec=25.0,
                    end_sec=30.0,
                    metadata={'segment_index': 5, 'video_source_uri': 's3://bucket/similar.mp4'}
                )
            ]
            
            mock_response = Mock()
            mock_response.results = mock_results
            mock_response.total_results = len(mock_results)
            mock_response.query_id = 'video-similarity-query-123'
            
            mock_engine.find_similar_content.return_value = mock_response
            
            app = UnifiedStreamlitApp()
            
            # Perform video-to-video search
            results = app._search_real(
                search_type="Video-to-Video",
                query="ref-video",  # Reference video ID
                time_start=None,
                time_end=None,
                top_k=10,
                similarity_threshold=0.7,
                category_filter=[]
            )
            
            # Verify video query was used
            mock_engine.find_similar_content.assert_called_once()
            call_args = mock_engine.find_similar_content.call_args
            query_arg = call_args[1]['query']
            
            # Verify reference video key was used
            self.assertEqual(query_arg.query_video_key, "ref-video-segment-0000")
            
            # Verify results
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]['score'], 0.88)


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance aspects of integrated workflows."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.large_video_collection = {}
        
        # Create large collection simulation
        for i in range(50):
            self.large_video_collection[f'video-{i:03d}'] = ProcessedVideo(
                video_id=f'video-{i:03d}',
                name=f'Video {i:03d}.mp4',
                segments=30,
                duration=150.0,
                processing_type='simulation' if i % 2 == 0 else 'real'
            )

    @patch('frontend.unified_streamlit_app.st')
    def test_large_collection_search_performance(self, mock_st):
        """Test search performance with large video collections."""
        mock_st.session_state = {
            'processed_videos': self.large_video_collection,
            'video_index_arn': 'test-arn'
        }
        
        app = UnifiedStreamlitApp()
        
        # Measure search simulation performance
        start_time = time.time()
        
        results = app._search_simulation(
            search_type="Text-to-Video",
            query="performance test query",
            time_start=None,
            time_end=None,
            top_k=20,
            similarity_threshold=0.6
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time even with 50 videos
        self.assertLess(duration, 1.0)  # Less than 1 second
        self.assertLessEqual(len(results), 20)
        
        # Verify all results meet threshold
        for result in results:
            self.assertGreaterEqual(result['score'], 0.6)

    @patch('frontend.unified_streamlit_app.st')
    def test_embedding_visualization_performance(self, mock_st):
        """Test embedding visualization performance with large datasets."""
        # Create large result set
        large_results = []
        for i in range(200):
            large_results.append({
                'vector_key': f'video-{i//10}-segment-{i%10:04d}',
                'video_name': f'Video {i//10}.mp4',
                'score': 0.9 - (i * 0.001),
                'segment_index': i % 10,
                'processing_type': 'real'
            })
        
        mock_st.session_state = {'search_results': large_results}
        
        app = UnifiedStreamlitApp()
        
        # Mock sklearn components
        with patch('frontend.unified_streamlit_app.PCA') as mock_pca, \
             patch('frontend.unified_streamlit_app.px') as mock_px:
            
            mock_pca_instance = Mock()
            mock_pca_instance.fit_transform.return_value = np.random.rand(100, 2)
            mock_pca.return_value = mock_pca_instance
            
            mock_px.scatter.return_value = Mock()
            
            start_time = time.time()
            
            app._generate_embedding_visualization(
                reduction_method="PCA",
                dimensions="2D",
                color_by="video_name",
                sample_size=100
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should complete visualization quickly
            self.assertLess(duration, 2.0)  # Less than 2 seconds
            
            # Verify PCA was called with correct parameters
            mock_pca.assert_called_with(n_components=2, random_state=42)

    def test_memory_usage_optimization(self):
        """Test memory usage optimization for large operations."""
        app = UnifiedStreamlitApp()
        
        # Test embedding generation memory efficiency
        large_count = 1000
        embedding_dim = 1024
        
        start_memory = self._get_memory_usage()
        
        embeddings = app._simulate_embeddings(large_count, embedding_dim, 42)
        
        end_memory = self._get_memory_usage()
        memory_increase = end_memory - start_memory
        
        # Expected memory for embeddings: 1000 * 1024 * 4 bytes = ~4MB
        expected_memory = large_count * embedding_dim * 4
        tolerance = expected_memory * 2  # Allow 2x overhead
        
        self.assertLess(memory_increase, tolerance)
        self.assertEqual(embeddings.nbytes, expected_memory)

    def _get_memory_usage(self):
        """Get current memory usage in bytes."""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss


class TestErrorHandlingIntegration(unittest.TestCase):
    """Test error handling in integrated workflows."""
    
    def setUp(self):
        """Set up error handling test fixtures."""
        self.mock_session_state = {
            'processed_videos': {},
            'video_index_arn': 'test-arn',
            'costs': {'video_processing': 0, 'storage': 0, 'queries': 0, 'total': 0}
        }

    @patch('frontend.unified_streamlit_app.st')
    @patch('src.services.video_embedding_storage.VideoEmbeddingStorageService')
    def test_processing_failure_recovery(self, mock_storage_service, mock_st):
        """Test recovery from processing failures."""
        mock_st.session_state = self.mock_session_state
        
        # Mock storage service to raise exception
        mock_storage_instance = Mock()
        mock_storage_instance.process_video_end_to_end.side_effect = VectorStorageError("Storage failed")
        mock_storage_service.return_value = mock_storage_instance
        
        app = UnifiedStreamlitApp()
        
        # Test processing with failure
        result = app._process_video_real(
            video_path="/tmp/test.mp4",
            video_s3_uri=None,
            segment_duration=5,
            embedding_options=["visual-text"],
            metadata={}
        )
        
        # Should handle error gracefully
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch('frontend.unified_streamlit_app.st')
    @patch('src.services.similarity_search_engine.SimilaritySearchEngine')
    def test_search_failure_recovery(self, mock_search_engine, mock_st):
        """Test recovery from search failures."""
        mock_st.session_state = self.mock_session_state
        
        # Mock search engine to raise exception
        mock_engine_instance = Mock()
        mock_engine_instance.find_similar_content.side_effect = Exception("Search failed")
        mock_search_engine.return_value = mock_engine_instance
        
        app = UnifiedStreamlitApp()
        
        # Test search with failure - should raise exception to be caught by UI
        with self.assertRaises(Exception):
            app._search_real(
                search_type="Text-to-Video",
                query="test",
                time_start=None,
                time_end=None,
                top_k=5,
                similarity_threshold=0.7,
                category_filter=[]
            )

    @patch('frontend.unified_streamlit_app.requests')
    @patch('frontend.unified_streamlit_app.st')
    def test_download_failure_recovery(self, mock_st, mock_requests):
        """Test recovery from download failures."""
        mock_st.session_state = self.mock_session_state
        
        # Mock failed download
        mock_requests.get.side_effect = requests.exceptions.RequestException("Download failed")
        
        app = UnifiedStreamlitApp()
        
        video_info = {
            'url': 'https://example.com/nonexistent.mp4',
            'file_size_mb': 100,
            'description': 'Test video'
        }
        
        result = app._download_sample_video("Test Video", video_info)
        
        # Should handle failure gracefully
        self.assertIsNone(result)

    @patch('frontend.unified_streamlit_app.st')
    def test_batch_processing_partial_failure(self, mock_st):
        """Test batch processing with some failures."""
        mock_st.session_state = self.mock_session_state
        
        # Create test video paths
        video_paths = ["/tmp/video1.mp4", "/tmp/video2.mp4", "/tmp/video3.mp4"]
        
        # Mock processing with partial failures
        def mock_process(video_path, video_s3_uri, segment_duration, embedding_options, metadata):
            if "video2" in video_path:
                return {'success': False, 'error': 'Processing failed for video2'}
            return {
                'success': True,
                'segments': 10,
                'vectors': 30,
                'duration': 50.0,
                'cost': 0.5
            }
        
        app = UnifiedStreamlitApp()
        app._process_video_simulation = Mock(side_effect=mock_process)
        
        # Mock Streamlit components
        mock_st.progress.return_value = Mock()
        mock_st.empty.return_value = Mock()
        mock_st.container.return_value = Mock()
        mock_st.spinner.return_value.__enter__ = Mock(return_value=None)
        mock_st.spinner.return_value.__exit__ = Mock(return_value=None)
        
        # Test batch processing with partial failure
        app._process_multiple_videos(
            video_paths=video_paths,
            segment_duration=5,
            embedding_options=["visual-text"],
            metadata={},
            use_real_aws=False,
            process_mode="Process One by One"
        )
        
        # Verify batch result shows partial success
        result = mock_st.session_state.get('last_processing_result')
        self.assertIsNotNone(result)
        self.assertEqual(result['total_videos'], 3)
        self.assertEqual(result['successful_videos'], 2)
        self.assertEqual(result['failed_videos'], 1)


def run_integration_benchmarks():
    """Run integration benchmarks and generate performance report."""
    print("\n🚀 Running Integration Benchmarks...")
    
    benchmarks = {}
    
    # Test 1: Large collection search
    print("📊 Testing large collection search...")
    start_time = time.time()
    
    app = UnifiedStreamlitApp()
    large_collection = {
        f'video-{i}': ProcessedVideo(f'v{i}', f'Video {i}', 20, 100.0)
        for i in range(100)
    }
    
    with patch('frontend.unified_streamlit_app.st') as mock_st:
        mock_st.session_state = {'processed_videos': large_collection}
        results = app._search_simulation("Text-to-Video", "test", None, None, 20, 0.7)
    
    search_duration = time.time() - start_time
    benchmarks['large_collection_search'] = {
        'duration_ms': search_duration * 1000,
        'collection_size': 100,
        'results_count': len(results)
    }
    
    # Test 2: Embedding visualization performance
    print("📊 Testing embedding visualization...")
    start_time = time.time()
    
    large_results = [
        {'vector_key': f'v{i}-s{j}', 'video_name': f'Video {i}', 'score': 0.9}
        for i in range(20) for j in range(10)
    ]
    
    with patch('frontend.unified_streamlit_app.st') as mock_st:
        mock_st.session_state = {'search_results': large_results}
        with patch('frontend.unified_streamlit_app.PCA') as mock_pca, \
             patch('frontend.unified_streamlit_app.px'):
            mock_pca().fit_transform.return_value = np.random.rand(200, 2)
            app._generate_embedding_visualization("PCA", "2D", "video_name", 200)
    
    viz_duration = time.time() - start_time
    benchmarks['embedding_visualization'] = {
        'duration_ms': viz_duration * 1000,
        'sample_size': 200
    }
    
    # Test 3: Batch processing simulation
    print("📊 Testing batch processing simulation...")
    start_time = time.time()
    
    def mock_process(*args):
        time.sleep(0.01)  # Simulate processing time
        return {'success': True, 'segments': 10, 'vectors': 30, 'duration': 50.0, 'cost': 0.1}
    
    video_paths = [f'/tmp/video{i}.mp4' for i in range(5)]
    
    with patch('frontend.unified_streamlit_app.st') as mock_st:
        mock_st.session_state = {'processed_videos': {}}
        mock_st.progress.return_value = Mock()
        mock_st.empty.return_value = Mock()
        mock_st.container.return_value = Mock()
        mock_st.spinner.return_value.__enter__ = Mock(return_value=None)
        mock_st.spinner.return_value.__exit__ = Mock(return_value=None)
        
        app._process_video_simulation = Mock(side_effect=mock_process)
        app._process_multiple_videos(
            video_paths, 5, ["visual-text"], {}, False, "Process All Together"
        )
    
    batch_duration = time.time() - start_time
    benchmarks['batch_processing'] = {
        'duration_ms': batch_duration * 1000,
        'video_count': 5,
        'throughput_videos_per_sec': 5 / batch_duration
    }
    
    print("✅ Integration benchmarks completed!")
    return benchmarks


if __name__ == '__main__':
    # Run integration tests
    print("🧪 Running Enhanced Streamlit Integration Tests...")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestCompleteWorkflowIntegration,
        TestPerformanceIntegration,
        TestErrorHandlingIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run benchmarks
    benchmarks = run_integration_benchmarks()
    
    # Summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100
    
    print(f"\n📋 INTEGRATION TEST SUMMARY")
    print(f"============================")
    print(f"Total Tests: {total_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"\n📊 PERFORMANCE BENCHMARKS:")
    for test_name, metrics in benchmarks.items():
        print(f"  {test_name}: {metrics['duration_ms']:.1f}ms")
    
    print(f"\n🎯 Integration testing complete!")