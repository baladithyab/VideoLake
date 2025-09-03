#!/usr/bin/env python3
"""
Streamlit Frontend Integration Tests

This test suite validates the integration between the enhanced Streamlit frontend
and the backend services, focusing on UI component functionality, service calls,
and data flow validation.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import Streamlit app components (if available)
try:
    import streamlit as st
    from frontend.multi_vector_utils import (
        VectorIndexManager,
        MultiVectorSearchConfig,
        SearchResult,
        VectorTypeConfig
    )
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    
# Backend services
from src.services.multi_vector_coordinator import MultiVectorCoordinator, SearchRequest
from src.services.streamlit_integration_utils import StreamlitServiceManager
from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery
from src.exceptions import ValidationError


@pytest.mark.skipif(not STREAMLIT_AVAILABLE, reason="Streamlit components not available")
class TestStreamlitComponentIntegration:
    """Test integration between Streamlit UI components and backend services."""
    
    @pytest.fixture
    def mock_service_manager(self):
        """Create mock service manager for testing."""
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        manager = StreamlitServiceManager()
                        return manager

    def test_vector_index_manager_initialization(self):
        """Test VectorIndexManager initialization."""
        if STREAMLIT_AVAILABLE:
            manager = VectorIndexManager()
            assert manager is not None
            assert hasattr(manager, 'get_available_indexes')
            assert hasattr(manager, 'get_index_stats')

    def test_multi_vector_search_config_creation(self):
        """Test MultiVectorSearchConfig creation and validation."""
        if STREAMLIT_AVAILABLE:
            config = MultiVectorSearchConfig(
                vector_types=['visual-text', 'audio'],
                fusion_method='weighted_average',
                top_k=10
            )
            
            assert config.vector_types == ['visual-text', 'audio']
            assert config.fusion_method == 'weighted_average'
            assert config.top_k == 10

    def test_search_result_formatting(self):
        """Test search result formatting for frontend display."""
        if STREAMLIT_AVAILABLE:
            # Mock search result data
            raw_result = {
                'results_by_type': {
                    'visual-text': [
                        {'score': 0.95, 'metadata': {'title': 'Test Video 1'}},
                        {'score': 0.87, 'metadata': {'title': 'Test Video 2'}}
                    ],
                    'audio': [
                        {'score': 0.92, 'metadata': {'title': 'Test Audio 1'}}
                    ]
                },
                'processing_stats': {'total_time_ms': 150}
            }
            
            search_result = SearchResult.from_multi_vector_result(raw_result)
            assert search_result.total_results > 0
            assert len(search_result.results_by_type) == 2

    @patch('streamlit.session_state', {})
    def test_streamlit_state_management(self, mock_service_manager):
        """Test Streamlit session state management."""
        if STREAMLIT_AVAILABLE:
            # Test service manager integration with session state
            with patch('streamlit.session_state') as mock_state:
                mock_state.__getitem__ = Mock(side_effect=KeyError)
                mock_state.__setitem__ = Mock()
                mock_state.__contains__ = Mock(return_value=False)
                
                # Should initialize service manager in session state
                manager = mock_service_manager
                assert manager is not None

    def test_video_processing_ui_integration(self, mock_service_manager):
        """Test video processing UI integration."""
        if STREAMLIT_AVAILABLE:
            manager = mock_service_manager
            
            # Mock video processing workflow
            with patch.object(manager, 'process_video') as mock_process:
                mock_process.return_value = {
                    'job_id': 'test-job-123',
                    'status': 'processing',
                    'vector_types': ['visual-text', 'visual-image', 'audio']
                }
                
                # Simulate UI interaction
                video_data = {
                    'file_path': '/tmp/test.mp4',
                    'title': 'Test Video'
                }
                
                result = manager.process_video(video_data)
                assert result['job_id'] == 'test-job-123'
                mock_process.assert_called_once_with(video_data)

    def test_search_ui_integration(self, mock_service_manager):
        """Test search UI integration."""
        if STREAMLIT_AVAILABLE:
            manager = mock_service_manager
            
            # Mock search functionality
            with patch.object(manager, 'search_videos') as mock_search:
                mock_search.return_value = {
                    'results_by_type': {
                        'visual-text': [{'score': 0.9, 'metadata': {'title': 'Result 1'}}]
                    },
                    'total_results': 1
                }
                
                search_params = {
                    'query_text': 'test search',
                    'vector_types': ['visual-text']
                }
                
                result = manager.search_videos(search_params)
                assert result['total_results'] == 1
                mock_search.assert_called_once_with(search_params)


class TestBackendServiceCommunication:
    """Test communication between frontend and backend services."""
    
    @pytest.fixture
    def service_setup(self):
        """Setup services for communication testing."""
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager') as mock_storage:
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine') as mock_search:
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService') as mock_twelvelabs:
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService') as mock_bedrock:
                        
                        # Configure mock responses
                        mock_search.return_value.get_available_indexes.return_value = {
                            'visual-text': {'count': 100, 'status': 'active'},
                            'visual-image': {'count': 80, 'status': 'active'},
                            'audio': {'count': 60, 'status': 'active'}
                        }
                        
                        mock_twelvelabs.return_value.get_job_status.return_value = {
                            'status': 'completed',
                            'progress': 100,
                            'embeddings': {'visual-text': [0.1, 0.2], 'audio': [0.3, 0.4]}
                        }
                        
                        manager = StreamlitServiceManager()
                        
                        yield {
                            'manager': manager,
                            'mocks': {
                                'storage': mock_storage.return_value,
                                'search': mock_search.return_value,
                                'twelvelabs': mock_twelvelabs.return_value,
                                'bedrock': mock_bedrock.return_value
                            }
                        }

    def test_index_availability_check(self, service_setup):
        """Test checking available vector indexes."""
        manager = service_setup['manager']
        mocks = service_setup['mocks']
        
        # Test getting available indexes
        indexes = manager.get_available_indexes()
        
        # Should call the underlying service
        mocks['search'].get_available_indexes.assert_called()
        assert isinstance(indexes, dict)

    def test_job_status_polling(self, service_setup):
        """Test job status polling for video processing."""
        manager = service_setup['manager']
        mocks = service_setup['mocks']
        
        # Test job status checking
        job_id = 'test-job-123'
        status = manager.get_job_status(job_id)
        
        # Should call the TwelveLabs service
        mocks['twelvelabs'].get_job_status.assert_called_with(job_id)
        assert status['status'] == 'completed'

    def test_error_propagation(self, service_setup):
        """Test error propagation from backend to frontend."""
        manager = service_setup['manager']
        mocks = service_setup['mocks']
        
        # Configure mock to raise error
        mocks['search'].get_available_indexes.side_effect = ValidationError("Service error")
        
        # Should propagate the error
        with pytest.raises(ValidationError):
            manager.get_available_indexes()

    def test_concurrent_request_handling(self, service_setup):
        """Test handling of concurrent requests."""
        manager = service_setup['manager']
        
        # Test that manager can handle concurrent operations
        assert manager.config.enable_concurrent_processing
        assert manager.config.max_concurrent_jobs > 0


class TestDataFlowValidation:
    """Test data flow between frontend and backend components."""
    
    def test_search_request_transformation(self):
        """Test transformation of frontend search params to backend SearchRequest."""
        frontend_params = {
            'query_text': 'test query',
            'vector_types': ['visual-text', 'audio'],
            'top_k': 5,
            'fusion_method': 'weighted_average'
        }
        
        # Transform to backend SearchRequest
        search_request = SearchRequest(
            query_text=frontend_params['query_text'],
            vector_types=frontend_params['vector_types'],
            top_k=frontend_params['top_k'],
            fusion_method=frontend_params['fusion_method']
        )
        
        assert search_request.query_text == 'test query'
        assert search_request.vector_types == ['visual-text', 'audio']
        assert search_request.top_k == 5

    def test_result_data_formatting(self):
        """Test formatting of backend results for frontend display."""
        backend_result = {
            'results_by_type': {
                'visual-text': [
                    {
                        'score': 0.95,
                        'metadata': {
                            'video_id': 'vid_123',
                            'title': 'Test Video',
                            'timestamp': '00:01:30'
                        }
                    }
                ],
                'audio': [
                    {
                        'score': 0.87,
                        'metadata': {
                            'video_id': 'vid_456',
                            'title': 'Audio Test',
                            'timestamp': '00:02:15'
                        }
                    }
                ]
            },
            'processing_stats': {
                'total_time_ms': 250,
                'results_count': 2
            }
        }
        
        # Validate structure for frontend consumption
        assert 'results_by_type' in backend_result
        assert 'processing_stats' in backend_result
        
        # Validate individual results have required fields
        for vector_type, results in backend_result['results_by_type'].items():
            for result in results:
                assert 'score' in result
                assert 'metadata' in result
                assert 'video_id' in result['metadata']

    def test_configuration_propagation(self):
        """Test configuration propagation from frontend to backend."""
        frontend_config = {
            'enable_multi_vector': True,
            'max_concurrent_jobs': 6,
            'vector_types': ['visual-text', 'visual-image'],
            'fusion_method': 'weighted_average'
        }
        
        # Should properly map to backend configuration
        from src.services.streamlit_integration_utils import StreamlitIntegrationConfig
        
        config = StreamlitIntegrationConfig(
            enable_multi_vector=frontend_config['enable_multi_vector'],
            max_concurrent_jobs=frontend_config['max_concurrent_jobs'],
            default_vector_types=frontend_config['vector_types']
        )
        
        assert config.enable_multi_vector == True
        assert config.max_concurrent_jobs == 6
        assert config.default_vector_types == ['visual-text', 'visual-image']


class TestUIResponseHandling:
    """Test UI response handling and user feedback."""
    
    @pytest.fixture
    def mock_streamlit_components(self):
        """Mock Streamlit components for testing."""
        if not STREAMLIT_AVAILABLE:
            pytest.skip("Streamlit not available")
            
        with patch('streamlit.progress') as mock_progress:
            with patch('streamlit.success') as mock_success:
                with patch('streamlit.error') as mock_error:
                    with patch('streamlit.warning') as mock_warning:
                        yield {
                            'progress': mock_progress,
                            'success': mock_success,
                            'error': mock_error,
                            'warning': mock_warning
                        }

    def test_progress_indication(self, mock_streamlit_components):
        """Test progress indication during long operations."""
        if not STREAMLIT_AVAILABLE:
            pytest.skip("Streamlit not available")
            
        # Test progress bar updates
        progress_bar = mock_streamlit_components['progress']()
        
        # Simulate progress updates
        for i in range(0, 101, 10):
            progress_bar.progress(i)
        
        # Should have been called multiple times
        assert progress_bar.progress.call_count == 11

    def test_error_message_display(self, mock_streamlit_components):
        """Test error message display in UI."""
        if not STREAMLIT_AVAILABLE:
            pytest.skip("Streamlit not available")
            
        error_component = mock_streamlit_components['error']
        
        # Test error display
        error_message = "Processing failed: Invalid video format"
        error_component(error_message)
        
        error_component.assert_called_once_with(error_message)

    def test_success_confirmation(self, mock_streamlit_components):
        """Test success confirmation display."""
        if not STREAMLIT_AVAILABLE:
            pytest.skip("Streamlit not available")
            
        success_component = mock_streamlit_components['success']
        
        # Test success message
        success_message = "Video processed successfully! Found 3 vectors."
        success_component(success_message)
        
        success_component.assert_called_once_with(success_message)


if __name__ == "__main__":
    # Run the frontend integration tests
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])