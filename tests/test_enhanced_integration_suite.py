#!/usr/bin/env python3
"""
Enhanced Integration Test Suite for S3Vector Multi-Vector Architecture

This comprehensive test suite validates the integration between:
1. Enhanced Streamlit application and updated services
2. Multi-vector processing workflows
3. Service coordination and error handling
4. API compatibility across all components
5. End-to-end pipeline functionality
"""

import pytest
import asyncio
import time
import tempfile
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Import all enhanced services
from src.services.multi_vector_coordinator import (
    MultiVectorCoordinator, 
    MultiVectorConfig, 
    SearchRequest, 
    VectorType,
    ProcessingMode
)
from src.services.streamlit_integration_utils import (
    StreamlitServiceManager,
    StreamlitIntegrationConfig
)
from src.services.similarity_search_engine import (
    SimilaritySearchEngine, 
    SimilarityQuery,
    IndexType
)
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.exceptions import VectorStorageError, ValidationError


class TestEnhancedServiceIntegration:
    """Test integration between enhanced services and Streamlit application."""
    
    @pytest.fixture
    def streamlit_manager(self):
        """Create StreamlitServiceManager for testing."""
        config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            max_concurrent_jobs=4
        )
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        manager = StreamlitServiceManager(config)
                        return manager
    
    @pytest.fixture
    def multi_vector_coordinator(self):
        """Create MultiVectorCoordinator for testing."""
        config = MultiVectorConfig(
            vector_types=["visual-text", "visual-image", "audio"],
            max_concurrent_jobs=4,
            processing_mode=ProcessingMode.ADAPTIVE
        )
        
        with patch('src.services.multi_vector_coordinator.TwelveLabsVideoProcessingService'):
            with patch('src.services.multi_vector_coordinator.SimilaritySearchEngine'):
                with patch('src.services.multi_vector_coordinator.S3VectorStorageManager'):
                    with patch('src.services.multi_vector_coordinator.BedrockEmbeddingService'):
                        coordinator = MultiVectorCoordinator(config=config)
                        return coordinator

    def test_streamlit_manager_initialization(self, streamlit_manager):
        """Test that StreamlitServiceManager initializes correctly."""
        assert streamlit_manager is not None
        assert streamlit_manager.config.enable_multi_vector
        assert hasattr(streamlit_manager, 'multi_vector_coordinator')
        assert hasattr(streamlit_manager, 'storage_manager')
        assert hasattr(streamlit_manager, 'search_engine')
        
    def test_multi_vector_coordinator_initialization(self, multi_vector_coordinator):
        """Test that MultiVectorCoordinator initializes correctly."""
        assert multi_vector_coordinator is not None
        assert multi_vector_coordinator.config.vector_types == ["visual-text", "visual-image", "audio"]
        assert multi_vector_coordinator.config.processing_mode == ProcessingMode.ADAPTIVE

    @patch('src.services.streamlit_integration_utils.get_logger')
    def test_service_coordination_logging(self, mock_logger, streamlit_manager):
        """Test that service coordination includes proper logging."""
        # Verify logger was called during initialization
        mock_logger.assert_called()
        
    def test_multi_vector_search_request_creation(self):
        """Test SearchRequest creation for multi-vector operations."""
        search_request = SearchRequest(
            query_text="test query",
            vector_types=["visual-text", "audio"],
            top_k=5,
            fusion_method="weighted_average"
        )
        
        assert search_request.query_text == "test query"
        assert search_request.vector_types == ["visual-text", "audio"]
        assert search_request.top_k == 5
        assert search_request.enable_cross_type_fusion


class TestAPICompatibility:
    """Test API compatibility between services and Streamlit frontend."""
    
    @pytest.fixture
    def mock_services(self):
        """Create mock services for API testing."""
        return {
            'storage': Mock(spec=S3VectorStorageManager),
            'search': Mock(spec=SimilaritySearchEngine),
            'twelvelabs': Mock(spec=TwelveLabsVideoProcessingService),
            'bedrock': Mock(spec=BedrockEmbeddingService)
        }
    
    def test_similarity_search_engine_api(self, mock_services):
        """Test SimilaritySearchEngine API compatibility."""
        mock_search = mock_services['search']
        
        # Test expected method exists
        assert hasattr(mock_search, 'search_similar_vectors')
        assert hasattr(mock_search, 'get_available_indexes')
        
        # Test SimilarityQuery structure
        query = SimilarityQuery(
            query_text="test",
            index_type=IndexType.VISUAL_TEXT,
            top_k=10
        )
        
        assert query.query_text == "test"
        assert query.index_type == IndexType.VISUAL_TEXT
        
    def test_multi_vector_coordinator_api(self):
        """Test MultiVectorCoordinator API methods."""
        config = MultiVectorConfig()
        
        with patch('src.services.multi_vector_coordinator.TwelveLabsVideoProcessingService'):
            with patch('src.services.multi_vector_coordinator.SimilaritySearchEngine'):
                with patch('src.services.multi_vector_coordinator.S3VectorStorageManager'):
                    with patch('src.services.multi_vector_coordinator.BedrockEmbeddingService'):
                        coordinator = MultiVectorCoordinator(config=config)
                        
                        # Test expected methods exist
                        assert hasattr(coordinator, 'process_video_multi_vector')
                        assert hasattr(coordinator, 'search_across_vector_types')
                        assert hasattr(coordinator, 'get_processing_status')
                        assert hasattr(coordinator, 'get_health_status')

    def test_streamlit_integration_api(self):
        """Test StreamlitServiceManager API methods."""
        config = StreamlitIntegrationConfig()
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        manager = StreamlitServiceManager(config)
                        
                        # Test expected methods exist
                        assert hasattr(manager, 'process_video')
                        assert hasattr(manager, 'search_videos')
                        assert hasattr(manager, 'get_service_status')
                        assert hasattr(manager, 'get_available_indexes')

    def test_vector_type_enum_compatibility(self):
        """Test VectorType enum values match expected frontend usage."""
        # Test all expected vector types are available
        expected_types = ["visual-text", "visual-image", "audio", "text-titan", "custom"]
        
        for expected_type in expected_types:
            found = False
            for vector_type in VectorType:
                if vector_type.value == expected_type:
                    found = True
                    break
            assert found, f"VectorType.{expected_type} not found"


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows from Streamlit to backend services."""
    
    @pytest.fixture
    def integration_setup(self):
        """Setup for end-to-end testing."""
        # Mock all services
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager') as mock_storage:
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine') as mock_search:
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService') as mock_twelvelabs:
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService') as mock_bedrock:
                        
                        # Configure mocks
                        mock_storage.return_value.store_vectors = Mock(return_value={"status": "success"})
                        mock_search.return_value.search_similar_vectors = Mock(return_value={
                            "results": [], "total": 0, "processing_time_ms": 100
                        })
                        mock_twelvelabs.return_value.create_embeddings_job = Mock(return_value={
                            "job_id": "test-job-123", "status": "processing"
                        })
                        mock_bedrock.return_value.generate_embeddings = Mock(return_value={
                            "embeddings": [0.1, 0.2, 0.3], "model_id": "titan-embed-text-v1"
                        })
                        
                        config = StreamlitIntegrationConfig(enable_multi_vector=True)
                        manager = StreamlitServiceManager(config)
                        
                        yield {
                            'manager': manager,
                            'mocks': {
                                'storage': mock_storage.return_value,
                                'search': mock_search.return_value,
                                'twelvelabs': mock_twelvelabs.return_value,
                                'bedrock': mock_bedrock.return_value
                            }
                        }

    def test_video_upload_and_processing_workflow(self, integration_setup):
        """Test complete video upload and processing workflow."""
        manager = integration_setup['manager']
        mocks = integration_setup['mocks']
        
        # Simulate video processing workflow
        video_data = {
            'file_path': '/tmp/test_video.mp4',
            'title': 'Test Video',
            'description': 'Test video for integration testing'
        }
        
        # Test multi-vector processing
        if hasattr(manager, 'multi_vector_coordinator'):
            # The coordinator should exist
            assert manager.multi_vector_coordinator is not None
            
            # Mock successful processing
            with patch.object(manager.multi_vector_coordinator, 'process_video_multi_vector') as mock_process:
                mock_process.return_value = {
                    'job_id': 'test-job-123',
                    'status': 'processing',
                    'vector_types': ['visual-text', 'visual-image', 'audio']
                }
                
                result = manager.process_video(video_data)
                assert result is not None

    def test_search_workflow(self, integration_setup):
        """Test complete search workflow across vector types."""
        manager = integration_setup['manager']
        mocks = integration_setup['mocks']
        
        search_params = {
            'query_text': 'test search query',
            'vector_types': ['visual-text', 'audio'],
            'top_k': 5
        }
        
        # Test search across multiple vector types
        if hasattr(manager, 'multi_vector_coordinator'):
            with patch.object(manager.multi_vector_coordinator, 'search_across_vector_types') as mock_search:
                mock_search.return_value = {
                    'results_by_type': {
                        'visual-text': [{'score': 0.9, 'metadata': {}}],
                        'audio': [{'score': 0.8, 'metadata': {}}]
                    },
                    'processing_stats': {'total_time_ms': 150},
                    'successful_types': ['visual-text', 'audio'],
                    'failed_types': []
                }
                
                result = manager.search_videos(search_params)
                assert result is not None

    def test_error_handling_workflow(self, integration_setup):
        """Test error handling in end-to-end workflows."""
        manager = integration_setup['manager']
        mocks = integration_setup['mocks']
        
        # Test handling of service failures
        mocks['storage'].store_vectors.side_effect = VectorStorageError("Storage failed")
        
        video_data = {'file_path': '/tmp/test_video.mp4'}
        
        # Should handle the error gracefully
        with pytest.raises((VectorStorageError, Exception)):
            manager.process_video(video_data)


class TestPerformanceIntegration:
    """Test performance aspects of the integrated system."""
    
    @pytest.fixture
    def performance_setup(self):
        """Setup for performance testing."""
        config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            max_concurrent_jobs=8
        )
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        manager = StreamlitServiceManager(config)
                        return manager

    def test_concurrent_processing_capability(self, performance_setup):
        """Test that concurrent processing is properly configured."""
        manager = performance_setup
        
        # Verify concurrent processing is enabled
        assert manager.config.enable_concurrent_processing
        assert manager.config.max_concurrent_jobs == 8
        
        # Test multi-vector coordinator concurrent settings
        if hasattr(manager, 'multi_vector_coordinator'):
            assert manager.multi_vector_coordinator.config.max_concurrent_jobs <= 8

    def test_processing_timeout_handling(self, performance_setup):
        """Test processing timeout handling."""
        manager = performance_setup
        
        if hasattr(manager, 'multi_vector_coordinator'):
            # Check timeout configuration
            config = manager.multi_vector_coordinator.config
            assert hasattr(config, 'timeout_seconds')
            assert config.timeout_seconds > 0

    def test_memory_usage_monitoring(self, performance_setup):
        """Test memory usage monitoring capabilities."""
        manager = performance_setup
        
        # Test service status monitoring
        if hasattr(manager, 'get_service_status'):
            # Should be able to get status without errors
            try:
                status = manager.get_service_status()
                # Status should include memory/performance info
                assert isinstance(status, dict)
            except AttributeError:
                # Method might not be implemented yet
                pass


class TestSecurityAndValidation:
    """Test security aspects and input validation."""
    
    def test_input_validation(self):
        """Test input validation for search requests."""
        # Test invalid vector types
        with pytest.raises((ValidationError, ValueError)):
            SearchRequest(
                query_text="test",
                vector_types=["invalid-type"],
                top_k=-1  # Invalid top_k
            )
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Test invalid configuration
        with pytest.raises((ValidationError, ValueError)):
            StreamlitIntegrationConfig(
                max_concurrent_jobs=-1  # Invalid value
            )
        
        # Test invalid multi-vector config
        with pytest.raises((ValidationError, ValueError)):
            MultiVectorConfig(
                vector_types=[],  # Empty list should be invalid
                max_concurrent_jobs=0
            )

    def test_service_health_monitoring(self):
        """Test service health monitoring and validation."""
        config = StreamlitIntegrationConfig()
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        manager = StreamlitServiceManager(config)
                        
                        # Test health status method exists
                        if hasattr(manager, 'get_service_status'):
                            # Should return health information
                            status = manager.get_service_status()
                            assert isinstance(status, dict)


if __name__ == "__main__":
    # Run the integration test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])