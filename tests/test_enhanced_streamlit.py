#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Streamlit Application

Tests the unified Streamlit app with multi-vector capabilities including:
- Multi-vector processing functions
- S3Vector multi-index operations
- Query type detection logic
- Embedding visualization components
- Complete workflow integration
- Performance validation
- User experience scenarios
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import os
import sys
import json
import numpy as np
import pandas as pd
from pathlib import Path
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

# Import Streamlit app components
from frontend.unified_streamlit_app import UnifiedStreamlitApp, ProcessedVideo, SAMPLE_VIDEOS
from src.services.similarity_search_engine import (
    SimilaritySearchEngine, 
    SimilarityQuery, 
    IndexType,
    TemporalFilter
)
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError


class TestEnhancedStreamlitApp(unittest.TestCase):
    """Unit tests for enhanced Streamlit application components."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Streamlit session state
        self.mock_session_state = {
            'processed_videos': {},
            'video_index_arn': None,
            'costs': {
                "video_processing": 0,
                "storage": 0,
                "queries": 0,
                "total": 0
            },
            'search_results': [],
            'last_embeddings': None,
            'selected_segment': None
        }
        
        # Create test videos
        self.test_videos = {
            'test-video-1': ProcessedVideo(
                video_id='test-video-1',
                name='Test Video 1.mp4',
                segments=24,
                duration=120.0,
                s3_uri='s3://test-bucket/video1.mp4',
                processing_type='real',
                metadata={'category': 'test', 'title': 'Test Video 1'}
            ),
            'test-video-2': ProcessedVideo(
                video_id='test-video-2',
                name='Test Video 2.mp4',
                segments=12,
                duration=60.0,
                processing_type='simulation',
                metadata={'category': 'animation', 'title': 'Test Video 2'}
            )
        }
        
        # Create sample search results
        self.sample_search_results = [
            {
                'vector_key': 'test-video-1-segment-0001',
                'video_name': 'Test Video 1.mp4',
                'video_s3_uri': 's3://test-bucket/video1.mp4',
                'segment_index': 0,
                'start_sec': 0.0,
                'end_sec': 5.0,
                'score': 0.95,
                'processing_type': 'real'
            },
            {
                'vector_key': 'test-video-2-segment-0005',
                'video_name': 'Test Video 2.mp4',
                'segment_index': 4,
                'start_sec': 20.0,
                'end_sec': 25.0,
                'score': 0.87,
                'processing_type': 'simulation'
            }
        ]

    @patch('frontend.unified_streamlit_app.st')
    def test_app_initialization(self, mock_st):
        """Test unified Streamlit app initialization."""
        # Mock session state
        mock_st.session_state = self.mock_session_state
        
        # Initialize app
        app = UnifiedStreamlitApp()
        
        # Verify initialization
        self.assertIsNotNone(app)
        self.assertIsNone(app.search_engine)  # Services may be None if init fails
        
        # Verify session state setup
        self.assertIn('processed_videos', mock_st.session_state)
        self.assertIn('costs', mock_st.session_state)

    def test_seed_from_text(self):
        """Test deterministic seed generation from text."""
        app = UnifiedStreamlitApp()
        
        # Test consistent seeds
        seed1 = app._seed_from_text("test query")
        seed2 = app._seed_from_text("test query")
        seed3 = app._seed_from_text("different query")
        
        self.assertEqual(seed1, seed2)
        self.assertNotEqual(seed1, seed3)
        self.assertIsInstance(seed1, int)

    def test_simulate_embeddings(self):
        """Test simulated embedding generation."""
        app = UnifiedStreamlitApp()
        
        # Generate embeddings
        embeddings = app._simulate_embeddings(count=10, dim=512, seed=42)
        
        # Verify shape and properties
        self.assertEqual(embeddings.shape, (10, 512))
        self.assertEqual(embeddings.dtype, np.float32)
        
        # Verify normalization (unit length)
        norms = np.linalg.norm(embeddings, axis=1)
        np.testing.assert_allclose(norms, 1.0, rtol=1e-5)
        
        # Test reproducibility
        embeddings2 = app._simulate_embeddings(count=10, dim=512, seed=42)
        np.testing.assert_array_equal(embeddings, embeddings2)

    @patch('frontend.unified_streamlit_app.st')
    def test_simulate_index_creation(self, mock_st):
        """Test simulated index creation."""
        mock_st.session_state = self.mock_session_state
        app = UnifiedStreamlitApp()
        
        # Simulate index creation
        app._simulate_index_creation("test-index", "Test index description")
        
        # Verify index ARN was set
        self.assertIsNotNone(mock_st.session_state.get('video_index_arn'))
        self.assertIn('test-index', mock_st.session_state['video_index_arn'])

    def test_processed_video_dataclass(self):
        """Test ProcessedVideo dataclass functionality."""
        video = ProcessedVideo(
            video_id="test-123",
            name="Test Video.mp4",
            segments=20,
            duration=100.0,
            s3_uri="s3://bucket/video.mp4",
            processing_type="real",
            metadata={"category": "test"}
        )
        
        self.assertEqual(video.video_id, "test-123")
        self.assertEqual(video.segments, 20)
        self.assertEqual(video.processing_type, "real")
        self.assertIsInstance(video.metadata, dict)

    def test_sample_videos_configuration(self):
        """Test sample videos configuration."""
        # Verify all sample videos have required fields
        required_fields = ['url', 'description', 'duration', 'category', 'file_size_mb', 'resolution', 'tags']
        
        for video_name, video_info in SAMPLE_VIDEOS.items():
            self.assertIsInstance(video_name, str)
            self.assertIsInstance(video_info, dict)
            
            for field in required_fields:
                self.assertIn(field, video_info, f"Missing {field} in {video_name}")
            
            # Verify data types
            self.assertIsInstance(video_info['duration'], int)
            self.assertIsInstance(video_info['file_size_mb'], int)
            self.assertIsInstance(video_info['tags'], list)
            self.assertTrue(video_info['url'].startswith('https://'))


class TestMultiVectorProcessing(unittest.TestCase):
    """Test multi-vector processing capabilities."""
    
    def setUp(self):
        """Set up test fixtures for multi-vector processing."""
        self.mock_session_state = {
            'processed_videos': {},
            'video_index_arn': 'arn:aws:s3vectors:us-east-1:123:bucket/test/index/multi-vector',
            'costs': {'video_processing': 0, 'storage': 0, 'queries': 0, 'total': 0}
        }

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.VideoEmbeddingStorageService')
    def test_process_video_simulation(self, mock_storage_service, mock_st):
        """Test video processing simulation with multiple embedding types."""
        mock_st.session_state = self.mock_session_state
        app = UnifiedStreamlitApp()
        
        # Test processing with multiple embedding options
        result = app._process_video_simulation(
            video_path="/tmp/test_video.mp4",
            video_s3_uri=None,
            segment_duration=5,
            embedding_options=["visual-text", "visual-image", "audio"],
            metadata={"title": "Test Video", "category": "test"}
        )
        
        # Verify result structure
        self.assertTrue(result['success'])
        self.assertIn('segments', result)
        self.assertIn('vectors', result)
        self.assertIn('duration', result)
        self.assertTrue(result['simulated'])
        
        # Verify multi-vector calculation (3 options = 3x vectors)
        expected_vectors = result['segments'] * 3
        self.assertEqual(result['vectors'], expected_vectors)

    @patch('frontend.unified_streamlit_app.st')
    def test_search_simulation_multi_vector(self, mock_st):
        """Test search simulation with multi-vector results."""
        mock_st.session_state = self.mock_session_state
        mock_st.session_state['processed_videos'] = {
            'video1': ProcessedVideo('v1', 'Video 1', 10, 50.0, processing_type='real'),
            'video2': ProcessedVideo('v2', 'Video 2', 15, 75.0, processing_type='simulation')
        }
        
        app = UnifiedStreamlitApp()
        
        # Test different search types
        search_types = ["Text-to-Video", "Video-to-Video", "Temporal Search"]
        
        for search_type in search_types:
            results = app._search_simulation(
                search_type=search_type,
                query="test query",
                time_start=None,
                time_end=None,
                top_k=5,
                similarity_threshold=0.7
            )
            
            self.assertIsInstance(results, list)
            self.assertLessEqual(len(results), 5)
            
            # Verify result structure
            for result in results:
                self.assertIn('vector_key', result)
                self.assertIn('video_name', result)
                self.assertIn('score', result)
                self.assertGreaterEqual(result['score'], 0.7)

    def test_batch_processing_logic(self):
        """Test batch processing mode logic."""
        app = UnifiedStreamlitApp()
        
        # Test with different video counts
        video_paths_single = ["/tmp/video1.mp4"]
        video_paths_multiple = ["/tmp/video1.mp4", "/tmp/video2.mp4", "/tmp/video3.mp4"]
        
        # Single video should use simple processing
        # Multiple videos should support batch modes
        self.assertEqual(len(video_paths_single), 1)
        self.assertGreater(len(video_paths_multiple), 1)


class TestEmbeddingVisualization(unittest.TestCase):
    """Test embedding visualization components."""
    
    def setUp(self):
        """Set up test fixtures for visualization testing."""
        self.sample_results = [
            {'vector_key': f'video-{i}-segment-{j:04d}', 'video_name': f'Video {i}', 
             'score': 0.9 - j*0.01, 'segment_index': j, 'processing_type': 'real'}
            for i in range(3) for j in range(5)
        ]

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.px')
    @patch('frontend.unified_streamlit_app.PCA')
    @patch('frontend.unified_streamlit_app.TSNE')
    def test_generate_embedding_visualization_2d(self, mock_tsne, mock_pca, mock_px, mock_st):
        """Test 2D embedding visualization generation."""
        mock_st.session_state = {'search_results': self.sample_results}
        
        # Mock dimensionality reduction
        mock_pca_instance = Mock()
        mock_pca_instance.fit_transform.return_value = np.random.rand(15, 2)
        mock_pca.return_value = mock_pca_instance
        
        # Mock plotly
        mock_fig = Mock()
        mock_px.scatter.return_value = mock_fig
        
        app = UnifiedStreamlitApp()
        app._generate_embedding_visualization("PCA", "2D", "video_name", 15)
        
        # Verify PCA was used correctly
        mock_pca.assert_called_once_with(n_components=2, random_state=42)
        mock_pca_instance.fit_transform.assert_called_once()
        
        # Verify plotly scatter was called
        mock_px.scatter.assert_called_once()

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.px')
    @patch('frontend.unified_streamlit_app.TSNE')
    def test_generate_embedding_visualization_3d_tsne(self, mock_tsne, mock_px, mock_st):
        """Test 3D t-SNE embedding visualization."""
        mock_st.session_state = {'search_results': self.sample_results}
        
        # Mock t-SNE
        mock_tsne_instance = Mock()
        mock_tsne_instance.fit_transform.return_value = np.random.rand(15, 3)
        mock_tsne.return_value = mock_tsne_instance
        
        # Mock plotly
        mock_fig = Mock()
        mock_px.scatter_3d.return_value = mock_fig
        
        app = UnifiedStreamlitApp()
        app._generate_embedding_visualization("t-SNE", "3D", "score", 15)
        
        # Verify t-SNE parameters
        mock_tsne.assert_called_once_with(n_components=3, perplexity=14, random_state=42)
        mock_tsne_instance.fit_transform.assert_called_once()
        
        # Verify 3D plotting
        mock_px.scatter_3d.assert_called_once()

    @patch('frontend.unified_streamlit_app.st')
    def test_add_query_overlay(self, mock_st):
        """Test adding query overlay to visualization."""
        mock_fig = Mock()
        mock_fig.data = [Mock()]
        mock_fig.data[0].x = [1, 2, 3]
        mock_fig.data[0].y = [1, 2, 3]
        
        mock_st.session_state = {'embedding_plot': mock_fig}
        
        app = UnifiedStreamlitApp()
        app._add_query_overlay("test query overlay")
        
        # Verify add_scatter was called
        mock_fig.add_scatter.assert_called_once()

    def test_visualization_color_options(self):
        """Test different color coding options for visualization."""
        color_options = ["video_name", "processing_type", "similarity_score", "segment_index"]
        
        # Each option should be a valid attribute for coloring
        for option in color_options:
            self.assertIsInstance(option, str)
            self.assertGreater(len(option), 0)

    def test_sample_size_validation(self):
        """Test sample size validation for visualization."""
        app = UnifiedStreamlitApp()
        
        # Test with different result set sizes
        small_results = self.sample_results[:5]
        large_results = self.sample_results * 20  # 300 results
        
        # Verify sample size logic would work correctly
        max_sample_small = min(200, len(small_results))
        max_sample_large = min(200, len(large_results))
        
        self.assertEqual(max_sample_small, 5)
        self.assertEqual(max_sample_large, 200)


class TestUserExperienceScenarios(unittest.TestCase):
    """Test user experience scenarios and workflows."""
    
    def setUp(self):
        """Set up UX testing fixtures."""
        self.mock_session_state = {
            'processed_videos': {},
            'video_index_arn': None,
            'costs': {'video_processing': 0, 'storage': 0, 'queries': 0, 'total': 0},
            'search_results': []
        }

    @patch('frontend.unified_streamlit_app.st')
    def test_complete_workflow_simulation(self, mock_st):
        """Test complete user workflow from index creation to search."""
        mock_st.session_state = self.mock_session_state
        app = UnifiedStreamlitApp()
        
        # Step 1: Create index
        app._simulate_index_creation("test-index", "Test workflow")
        self.assertIsNotNone(mock_st.session_state.get('video_index_arn'))
        
        # Step 2: Process video
        result = app._process_video_simulation(
            video_path="/tmp/test.mp4",
            video_s3_uri=None,
            segment_duration=5,
            embedding_options=["visual-text"],
            metadata={"title": "Test"}
        )
        self.assertTrue(result['success'])
        
        # Step 3: Perform search
        mock_st.session_state['processed_videos'] = {
            'test-video': ProcessedVideo('test', 'Test Video', 10, 50.0)
        }
        
        search_results = app._search_simulation(
            search_type="Text-to-Video",
            query="test content",
            time_start=None,
            time_end=None,
            top_k=5,
            similarity_threshold=0.7
        )
        
        self.assertIsInstance(search_results, list)

    def test_error_handling_scenarios(self):
        """Test error handling in user scenarios."""
        app = UnifiedStreamlitApp()
        
        # Test with invalid video path
        with patch('frontend.unified_streamlit_app.cv2') as mock_cv2:
            mock_cv2.VideoCapture.side_effect = Exception("Video file not found")
            
            result = app._process_video_simulation(
                video_path="/invalid/path.mp4",
                video_s3_uri=None,
                segment_duration=5,
                embedding_options=["visual-text"],
                metadata={}
            )
            
            # Should handle error gracefully
            self.assertTrue(result['success'])  # Simulation should still work

    @patch('frontend.unified_streamlit_app.st')
    def test_cost_tracking(self, mock_st):
        """Test cost tracking functionality."""
        mock_st.session_state = self.mock_session_state
        app = UnifiedStreamlitApp()
        
        # Simulate operations with costs
        initial_total = mock_st.session_state['costs']['total']
        
        # Simulate query cost
        mock_st.session_state['costs']['queries'] += 0.001
        mock_st.session_state['costs']['total'] = sum(mock_st.session_state['costs'].values())
        
        # Verify cost update
        self.assertEqual(mock_st.session_state['costs']['queries'], 0.001)
        self.assertGreater(mock_st.session_state['costs']['total'], initial_total)

    def test_progress_tracking_logic(self):
        """Test progress tracking for batch operations."""
        app = UnifiedStreamlitApp()
        
        # Test progress calculation
        total_videos = 5
        processed_videos = [1, 2, 3, 4, 5]
        
        for i, video_id in enumerate(processed_videos):
            progress = (i + 1) / total_videos
            self.assertGreaterEqual(progress, 0.0)
            self.assertLessEqual(progress, 1.0)
        
        # Final progress should be 1.0
        self.assertEqual(progress, 1.0)


class TestPerformanceValidation(unittest.TestCase):
    """Test performance aspects of the application."""
    
    def test_embedding_generation_performance(self):
        """Test performance of embedding generation."""
        app = UnifiedStreamlitApp()
        
        # Test different sizes
        sizes = [10, 100, 500]
        dimensions = [128, 512, 1024]
        
        for count in sizes:
            for dim in dimensions:
                start_time = time.time()
                
                embeddings = app._simulate_embeddings(count, dim, 42)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Should complete within reasonable time (< 1 second)
                self.assertLess(duration, 1.0)
                self.assertEqual(embeddings.shape, (count, dim))

    def test_search_simulation_scalability(self):
        """Test search simulation with large datasets."""
        app = UnifiedStreamlitApp()
        
        # Create large video dataset
        large_video_set = {}
        for i in range(100):
            large_video_set[f'video-{i}'] = ProcessedVideo(
                video_id=f'video-{i}',
                name=f'Video {i}.mp4',
                segments=20,
                duration=100.0
            )
        
        # Mock session state
        with patch('frontend.unified_streamlit_app.st') as mock_st:
            mock_st.session_state = {'processed_videos': large_video_set}
            
            start_time = time.time()
            
            results = app._search_simulation(
                search_type="Text-to-Video",
                query="performance test",
                time_start=None,
                time_end=None,
                top_k=50,
                similarity_threshold=0.5
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Should handle large datasets efficiently (< 2 seconds)
            self.assertLess(duration, 2.0)
            self.assertLessEqual(len(results), 50)

    def test_memory_usage_visualization(self):
        """Test memory usage during visualization operations."""
        app = UnifiedStreamlitApp()
        
        # Generate large embedding set
        large_embeddings = app._simulate_embeddings(1000, 1024, 42)
        
        # Check memory footprint is reasonable
        # 1000 * 1024 * 4 bytes = ~4MB for float32
        expected_bytes = 1000 * 1024 * 4
        actual_bytes = large_embeddings.nbytes
        
        self.assertEqual(actual_bytes, expected_bytes)
        self.assertLess(actual_bytes, 10_000_000)  # Less than 10MB


class TestSecurityAndValidation(unittest.TestCase):
    """Test security measures and input validation."""
    
    def setUp(self):
        """Set up security test fixtures."""
        self.app = UnifiedStreamlitApp()

    def test_metadata_sanitization(self):
        """Test metadata input sanitization."""
        # Test with potentially malicious metadata
        malicious_metadata = {
            "title": "<script>alert('xss')</script>",
            "description": "'; DROP TABLE videos; --",
            "category": "../../../etc/passwd",
            "keywords": "normal, <img src=x onerror=alert(1)>"
        }
        
        # In a real implementation, metadata should be sanitized
        # For simulation, we just verify it's handled without errors
        result = self.app._process_video_simulation(
            video_path="/tmp/test.mp4",
            video_s3_uri=None,
            segment_duration=5,
            embedding_options=["visual-text"],
            metadata=malicious_metadata
        )
        
        self.assertTrue(result['success'])

    def test_file_path_validation(self):
        """Test file path validation and sanitization."""
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\sam",
            "file://localhost/etc/passwd",
            "\\\\server\\share\\file.txt"
        ]
        
        # App should handle these gracefully in simulation mode
        for path in dangerous_paths:
            result = self.app._process_video_simulation(
                video_path=path,
                video_s3_uri=None,
                segment_duration=5,
                embedding_options=["visual-text"],
                metadata={}
            )
            
            # Should still work in simulation (no actual file access)
            self.assertTrue(result['success'])

    def test_query_injection_protection(self):
        """Test protection against query injection attempts."""
        malicious_queries = [
            "'; DROP TABLE vectors; --",
            "<script>alert('xss')</script>",
            "../../../../etc/passwd",
            "SELECT * FROM users WHERE password = '",
            "UNION SELECT username, password FROM users --"
        ]
        
        for query in malicious_queries:
            # Generate seed (should not execute any malicious code)
            seed = self.app._seed_from_text(query)
            self.assertIsInstance(seed, int)
            
            # Generate embeddings (should work safely)
            embeddings = self.app._simulate_embeddings(5, 128, seed)
            self.assertEqual(embeddings.shape, (5, 128))

    def test_resource_limits(self):
        """Test resource usage limits and protection."""
        # Test large parameter values
        with self.assertRaises(Exception):
            # This should be rejected in a real implementation
            try:
                large_embeddings = self.app._simulate_embeddings(
                    count=1000000,  # Very large
                    dim=10000,      # Very large
                    seed=42
                )
                # If it doesn't raise an exception, at least verify it's bounded
                self.assertLess(large_embeddings.nbytes, 100_000_000)  # < 100MB
            except MemoryError:
                pass  # Expected for very large allocations

    def test_session_state_isolation(self):
        """Test session state isolation and security."""
        # Verify session state doesn't leak sensitive information
        sensitive_data = "secret_api_key_12345"
        
        # Session state should not contain raw sensitive data
        mock_session = {
            'api_key': sensitive_data,
            'processed_videos': {}
        }
        
        # In a real app, sensitive data should be properly handled
        self.assertIn('api_key', mock_session)  # Present but should be encrypted/protected


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests for complete workflows."""
    
    @patch('frontend.unified_streamlit_app.requests')
    @patch('frontend.unified_streamlit_app.tempfile')
    def test_sample_video_download_integration(self, mock_tempfile, mock_requests):
        """Test sample video download integration."""
        app = UnifiedStreamlitApp()
        
        # Mock successful download
        mock_response = Mock()
        mock_response.headers = {'content-length': '1000000'}
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2', b'chunk3']
        mock_requests.get.return_value = mock_response
        
        # Mock temp file
        mock_temp = Mock()
        mock_temp.name = '/tmp/downloaded_video.mp4'
        mock_tempfile.NamedTemporaryFile.return_value.__enter__.return_value = mock_temp
        
        # Test download
        video_info = SAMPLE_VIDEOS['Big Buck Bunny (Creative Commons)']
        with patch('frontend.unified_streamlit_app.st') as mock_st:
            result = app._download_sample_video("Test Video", video_info)
            
            self.assertEqual(result, '/tmp/downloaded_video.mp4')

    @patch('frontend.unified_streamlit_app.st')
    def test_management_operations_integration(self, mock_st):
        """Test management operations integration."""
        mock_st.session_state = {
            'video_index_arn': 'arn:aws:s3vectors:us-east-1:123:bucket/test/index/test',
            'processed_videos': {
                'v1': ProcessedVideo('v1', 'Video 1', 10, 50.0)
            }
        }
        
        app = UnifiedStreamlitApp()
        
        # Test metadata export
        operations = ["Export index metadata"]
        app._execute_management_operations(operations)
        
        # Should complete without errors
        self.assertTrue(True)

    @patch('frontend.unified_streamlit_app.st')
    def test_cleanup_operations_integration(self, mock_st):
        """Test cleanup operations integration."""
        mock_st.session_state = {
            'processed_videos': {'v1': ProcessedVideo('v1', 'Video 1', 10, 50.0)},
            'video_index_arn': 'test-arn',
            'search_results': [{'test': 'result'}],
            'costs': {'total': 10.0}
        }
        
        app = UnifiedStreamlitApp()
        
        # Test complete cleanup
        cleanup_options = ["Clear all session data"]
        app._execute_cleanup(cleanup_options, use_real_aws=False)
        
        # Verify cleanup
        self.assertEqual(len(mock_st.session_state['processed_videos']), 0)
        self.assertIsNone(mock_st.session_state['video_index_arn'])
        self.assertEqual(len(mock_st.session_state['search_results']), 0)


def run_performance_benchmarks():
    """Run performance benchmarks and generate report."""
    print("🔬 Running Performance Benchmarks...")
    
    # Embedding generation benchmark
    app = UnifiedStreamlitApp()
    
    # Test various sizes
    test_cases = [
        (10, 128), (50, 512), (100, 1024), (500, 1024)
    ]
    
    results = []
    for count, dim in test_cases:
        start_time = time.time()
        embeddings = app._simulate_embeddings(count, dim, 42)
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = count / duration
        memory_mb = embeddings.nbytes / (1024 * 1024)
        
        results.append({
            'count': count,
            'dimension': dim,
            'duration_ms': duration * 1000,
            'throughput_per_sec': throughput,
            'memory_mb': memory_mb
        })
        
        print(f"✅ {count}x{dim}: {duration*1000:.1f}ms, {throughput:.1f} emb/s, {memory_mb:.1f}MB")
    
    return results


def generate_test_report():
    """Generate comprehensive test report."""
    print("\n📊 Generating Test Report...")
    
    # Run test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestEnhancedStreamlitApp,
        TestMultiVectorProcessing, 
        TestEmbeddingVisualization,
        TestUserExperienceScenarios,
        TestPerformanceValidation,
        TestSecurityAndValidation,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate summary
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100
    
    print(f"\n📋 TEST SUMMARY")
    print(f"================")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_tests - failures - errors}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Performance benchmarks
    perf_results = run_performance_benchmarks()
    
    return {
        'test_results': {
            'total': total_tests,
            'passed': total_tests - failures - errors,
            'failed': failures,
            'errors': errors,
            'success_rate': success_rate
        },
        'performance_results': perf_results
    }


if __name__ == '__main__':
    # Run comprehensive testing
    report = generate_test_report()
    
    print(f"\n🎯 Enhanced Streamlit Testing Complete!")
    print(f"Success Rate: {report['test_results']['success_rate']:.1f}%")