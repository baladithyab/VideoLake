#!/usr/bin/env python3
"""
Comprehensive Integration Tests for S3Vector Unified Demo

Tests all workflow paths in both simulation and real AWS modes.
"""

import pytest
import sys
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestUnifiedDemoIntegration:
    """Integration tests for the unified S3Vector demo."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.test_data = {
            "sample_query": "person walking in the scene",
            "sample_video_uri": "s3://test-bucket/sample-video.mp4",
            "vector_types": ["visual-text", "visual-image", "audio"],
            "expected_segments": 5
        }
    
    def test_demo_initialization(self):
        """Test that the unified demo initializes correctly."""
        try:
            from frontend.unified_demo_refactored import UnifiedS3VectorDemo
            
            demo = UnifiedS3VectorDemo()
            
            # Verify core components are initialized
            assert demo.config is not None, "Demo config not initialized"
            assert demo.utils is not None, "Demo utils not initialized"
            assert demo.search_components is not None, "Search components not initialized"
            assert demo.results_components is not None, "Results components not initialized"
            assert demo.processing_components is not None, "Processing components not initialized"
            
            print("✅ Demo initialization test passed")
            
        except Exception as e:
            pytest.fail(f"Demo initialization failed: {e}")
    
    def test_backend_services_separation(self):
        """Test that backend services don't import Streamlit."""
        backend_services = [
            "src.services.advanced_query_analysis",
            "src.services.simple_visualization", 
            "src.services.simple_video_player",
            "src.services.enhanced_video_pipeline"
        ]
        
        for service_module in backend_services:
            try:
                module = __import__(service_module, fromlist=[''])
                
                # Check that streamlit is not imported
                if hasattr(module, 'st') or 'streamlit' in str(module.__dict__):
                    pytest.fail(f"Backend service {service_module} imports Streamlit")
                
                print(f"✅ Backend service {service_module} properly separated")
                
            except ImportError as e:
                pytest.fail(f"Failed to import backend service {service_module}: {e}")
    
    def test_query_analysis_workflow(self):
        """Test the query analysis workflow."""
        try:
            from src.services.advanced_query_analysis import SimpleQueryAnalyzer
            
            analyzer = SimpleQueryAnalyzer()
            
            # Test different query types
            test_queries = [
                ("person walking", "visual"),
                ("music playing", "audio"), 
                ("text on screen", "text"),
                ("general content", "general")
            ]
            
            for query, expected_intent_type in test_queries:
                result = analyzer.analyze_query(query, self.test_data["vector_types"])
                
                assert result.original_query == query, f"Query not preserved: {query}"
                assert result.confidence > 0, f"No confidence for query: {query}"
                assert len(result.recommended_vectors) > 0, f"No vectors recommended for: {query}"
                
                print(f"✅ Query analysis for '{query}': {result.intent.value}")
            
        except Exception as e:
            pytest.fail(f"Query analysis workflow failed: {e}")
    
    def test_visualization_data_preparation(self):
        """Test visualization data preparation."""
        try:
            from src.services.simple_visualization import SimpleVisualization, generate_demo_embeddings
            
            viz_service = SimpleVisualization()
            
            # Generate test embeddings
            query_points, result_points = generate_demo_embeddings(
                query=self.test_data["sample_query"],
                vector_type="visual-text",
                n_results=10
            )
            
            # Test visualization data preparation
            viz_data = viz_service.prepare_visualization_data(
                query_embeddings=query_points,
                result_embeddings=result_points,
                method="PCA"
            )
            
            assert "figure" in viz_data, "Visualization figure not generated"
            assert "statistics" in viz_data, "Visualization statistics not generated"
            assert viz_data["method"] == "PCA", "Method not preserved"
            
            print("✅ Visualization data preparation test passed")
            
        except Exception as e:
            pytest.fail(f"Visualization data preparation failed: {e}")
    
    def test_video_player_data_preparation(self):
        """Test video player data preparation."""
        try:
            from src.services.simple_video_player import SimpleVideoPlayer, generate_demo_segments
            
            player_service = SimpleVideoPlayer()
            
            # Generate test segments
            segments = generate_demo_segments(
                video_s3_uri=self.test_data["sample_video_uri"],
                query=self.test_data["sample_query"]
            )
            
            # Test video data preparation
            video_data = player_service.prepare_video_data(
                video_s3_uri=self.test_data["sample_video_uri"],
                segments=segments
            )
            
            assert "video_url" in video_data, "Video URL not generated"
            assert "segments" in video_data, "Segments not prepared"
            assert "timeline_data" in video_data, "Timeline data not prepared"
            assert len(video_data["segments"]) == len(segments), "Segment count mismatch"
            
            print("✅ Video player data preparation test passed")
            
        except Exception as e:
            pytest.fail(f"Video player data preparation failed: {e}")
    
    def test_frontend_ui_components(self):
        """Test frontend UI components initialization."""
        try:
            from frontend.components.visualization_ui import VisualizationUI
            from frontend.components.video_player_ui import VideoPlayerUI
            
            # Test visualization UI
            viz_ui = VisualizationUI()
            assert viz_ui.viz_service is not None, "Visualization service not available in UI"
            
            # Test video player UI
            player_ui = VideoPlayerUI()
            assert player_ui.player_service is not None, "Player service not available in UI"
            
            print("✅ Frontend UI components test passed")
            
        except Exception as e:
            pytest.fail(f"Frontend UI components test failed: {e}")
    
    def test_search_components_integration(self):
        """Test search components integration."""
        try:
            from frontend.components.search_components import SearchComponents
            
            search_comp = SearchComponents()
            
            # Test query analysis
            analysis = search_comp.analyze_search_query(
                self.test_data["sample_query"], 
                self.test_data["vector_types"]
            )
            
            assert "intent" in analysis, "Query analysis missing intent"
            assert "complexity" in analysis, "Query analysis missing complexity"
            assert "recommended_vectors" in analysis, "Query analysis missing vector recommendations"
            
            # Test demo search results generation
            results = search_comp.generate_demo_search_results(
                self.test_data["sample_query"],
                "s3vector",
                5
            )
            
            assert len(results) == 5, "Incorrect number of demo results"
            assert all("similarity" in r for r in results), "Results missing similarity scores"
            
            print("✅ Search components integration test passed")
            
        except Exception as e:
            pytest.fail(f"Search components integration failed: {e}")
    
    def test_results_components_integration(self):
        """Test results components integration."""
        try:
            from frontend.components.results_components import ResultsComponents
            
            results_comp = ResultsComponents()
            
            # Verify UI components are available
            assert results_comp.viz_ui is not None, "Visualization UI not available"
            assert results_comp.video_ui is not None, "Video UI not available"
            
            # Test result analysis
            demo_results = [
                {
                    "segment_id": f"seg_{i}",
                    "similarity": 0.8 + (i * 0.02),
                    "vector_type": "visual-text",
                    "start_time": i * 5.0,
                    "end_time": (i + 1) * 5.0
                }
                for i in range(5)
            ]
            
            analysis = results_comp.analyze_search_results(demo_results)
            
            assert "total_results" in analysis, "Results analysis missing total count"
            assert "avg_similarity" in analysis, "Results analysis missing average similarity"
            
            print("✅ Results components integration test passed")
            
        except Exception as e:
            pytest.fail(f"Results components integration failed: {e}")
    
    def test_processing_components_integration(self):
        """Test processing components integration."""
        try:
            from frontend.components.processing_components import ProcessingComponents
            
            proc_comp = ProcessingComponents()
            
            # Test demo processing results generation
            job_info = {
                'job_id': 'test_job',
                'video_uri': self.test_data["sample_video_uri"],
                'vector_types': self.test_data["vector_types"],
                'storage_patterns': ['direct_s3vector'],
                'segment_duration': 5.0
            }
            
            results = proc_comp.generate_demo_processing_results(job_info)
            
            assert "total_segments" in results, "Processing results missing segment count"
            assert "processing_time_ms" in results, "Processing results missing timing"
            assert "cost_estimate" in results, "Processing results missing cost estimate"
            
            print("✅ Processing components integration test passed")
            
        except Exception as e:
            pytest.fail(f"Processing components integration failed: {e}")
    
    def test_demo_config_and_utils(self):
        """Test demo configuration and utilities."""
        try:
            from frontend.components.demo_config import DemoConfig, DemoUtils
            
            config = DemoConfig()
            utils = DemoUtils()
            
            # Test configuration
            assert len(config.default_vector_types) > 0, "No default vector types configured"
            assert len(config.workflow_sections) == 5, "Incorrect number of workflow sections"
            
            # Test utilities
            valid_uri = utils.validate_s3_uri("s3://bucket/key/file.mp4")
            invalid_uri = utils.validate_s3_uri("invalid://uri")
            
            assert valid_uri == True, "Valid S3 URI not recognized"
            assert invalid_uri == False, "Invalid URI not rejected"
            
            # Test workflow progress
            progress = utils.get_workflow_progress("query", config.workflow_sections)
            assert 0 <= progress <= 1, "Invalid workflow progress value"
            
            print("✅ Demo config and utils test passed")
            
        except Exception as e:
            pytest.fail(f"Demo config and utils test failed: {e}")
    
    @pytest.mark.slow
    def test_full_workflow_simulation(self):
        """Test complete workflow in simulation mode."""
        try:
            from frontend.unified_demo_refactored import UnifiedS3VectorDemo
            
            demo = UnifiedS3VectorDemo()
            
            # Simulate workflow steps
            print("🔄 Testing full workflow simulation...")
            
            # Step 1: Upload simulation
            upload_result = demo.processing_components.simulate_video_upload(
                "sample-video.mp4", 
                self.test_data["vector_types"]
            )
            assert upload_result["status"] == "success", "Upload simulation failed"
            
            # Step 2: Query analysis
            analysis = demo.search_components.analyze_search_query(
                self.test_data["sample_query"],
                self.test_data["vector_types"]
            )
            assert analysis["intent"] is not None, "Query analysis failed"
            
            # Step 3: Search simulation
            search_results = demo.search_components.generate_demo_search_results(
                self.test_data["sample_query"],
                "combined",
                10
            )
            assert len(search_results) == 10, "Search simulation failed"
            
            # Step 4: Results analysis
            results_analysis = demo.results_components.analyze_search_results(search_results)
            assert results_analysis["total_results"] == 10, "Results analysis failed"
            
            print("✅ Full workflow simulation test passed")
            
        except Exception as e:
            pytest.fail(f"Full workflow simulation failed: {e}")


class TestRealAWSIntegration:
    """Tests for real AWS integration (requires AWS credentials)."""
    
    @pytest.mark.aws
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"), 
        reason="AWS credentials not available"
    )
    def test_aws_service_connectivity(self):
        """Test connectivity to AWS services."""
        try:
            from src.utils.aws_clients import aws_client_factory
            
            # Test S3 client
            s3_client = aws_client_factory.get_s3_client()
            response = s3_client.list_buckets()
            assert "Buckets" in response, "S3 connectivity failed"
            
            # Test Bedrock client
            bedrock_client = aws_client_factory.get_bedrock_client()
            assert bedrock_client is not None, "Bedrock client not available"
            
            print("✅ AWS service connectivity test passed")
            
        except Exception as e:
            pytest.fail(f"AWS service connectivity failed: {e}")
    
    @pytest.mark.aws
    @pytest.mark.skipif(
        not os.getenv("AWS_ACCESS_KEY_ID"), 
        reason="AWS credentials not available"
    )
    def test_s3vector_service_integration(self):
        """Test S3Vector service integration."""
        try:
            from src.services.s3_vector_storage import S3VectorStorageService
            
            service = S3VectorStorageService()
            
            # Test service initialization
            assert service is not None, "S3Vector service not initialized"
            
            print("✅ S3Vector service integration test passed")
            
        except Exception as e:
            pytest.fail(f"S3Vector service integration failed: {e}")


def run_integration_tests():
    """Run integration tests with proper reporting."""
    print("🧪 Running S3Vector Unified Demo Integration Tests")
    print("=" * 60)
    
    # Run tests
    test_args = [
        "-v",  # Verbose output
        "-s",  # Don't capture output
        "--tb=short",  # Short traceback format
        __file__
    ]
    
    # Add AWS tests if credentials available
    if os.getenv("AWS_ACCESS_KEY_ID"):
        test_args.extend(["-m", "not slow"])  # Run AWS tests but skip slow tests
        print("🔑 AWS credentials detected - including AWS integration tests")
    else:
        test_args.extend(["-m", "not aws and not slow"])  # Skip AWS and slow tests
        print("⚠️ No AWS credentials - skipping AWS integration tests")
    
    exit_code = pytest.main(test_args)
    
    if exit_code == 0:
        print("\n🎉 All integration tests passed!")
    else:
        print(f"\n❌ Some tests failed (exit code: {exit_code})")
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
