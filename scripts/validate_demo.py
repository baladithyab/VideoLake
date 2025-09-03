#!/usr/bin/env python3
"""
S3Vector Unified Demo Validation Script

Comprehensive validation of the unified demo including:
- Component initialization
- Service integration
- Workflow simulation
- Performance testing
- Error handling
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DemoValidator:
    """Comprehensive demo validation."""
    
    def __init__(self):
        self.results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_results": []
        }
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and record results."""
        self.results["total_tests"] += 1
        
        try:
            start_time = time.time()
            test_func()
            duration = time.time() - start_time
            
            self.results["passed_tests"] += 1
            self.results["test_results"].append({
                "name": test_name,
                "status": "PASSED",
                "duration": duration,
                "error": None
            })
            
            print(f"✅ {test_name} - PASSED ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.results["failed_tests"] += 1
            self.results["test_results"].append({
                "name": test_name,
                "status": "FAILED", 
                "duration": duration,
                "error": str(e)
            })
            
            print(f"❌ {test_name} - FAILED ({duration:.2f}s)")
            print(f"   Error: {e}")
            return False
    
    def test_core_imports(self):
        """Test that all core components can be imported."""
        # Test main demo
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        
        # Test components
        from frontend.components.search_components import SearchComponents
        from frontend.components.results_components import ResultsComponents
        from frontend.components.processing_components import ProcessingComponents
        from frontend.components.demo_config import DemoConfig, DemoUtils
        
        # Test UI components
        from frontend.components.visualization_ui import VisualizationUI
        from frontend.components.video_player_ui import VideoPlayerUI
        
        # Test backend services
        from src.services.advanced_query_analysis import SimpleQueryAnalyzer
        from src.services.simple_visualization import SimpleVisualization
        from src.services.simple_video_player import SimpleVideoPlayer
    
    def test_demo_initialization(self):
        """Test demo initialization."""
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        
        demo = UnifiedS3VectorDemo()
        
        assert demo.config is not None, "Config not initialized"
        assert demo.utils is not None, "Utils not initialized"
        assert demo.search_components is not None, "Search components not initialized"
        assert demo.results_components is not None, "Results components not initialized"
        assert demo.processing_components is not None, "Processing components not initialized"
    
    def test_query_analysis(self):
        """Test query analysis functionality."""
        from src.services.advanced_query_analysis import SimpleQueryAnalyzer
        
        analyzer = SimpleQueryAnalyzer()
        
        test_queries = [
            "person walking in the scene",
            "music playing in background", 
            "text displayed on screen",
            "car driving on highway"
        ]
        
        for query in test_queries:
            result = analyzer.analyze_query(query, ["visual-text", "visual-image", "audio"])
            
            assert result.original_query == query, f"Query not preserved: {query}"
            assert result.confidence > 0, f"No confidence for: {query}"
            assert len(result.recommended_vectors) > 0, f"No vectors for: {query}"
    
    def test_visualization_service(self):
        """Test visualization service."""
        from src.services.simple_visualization import SimpleVisualization, generate_demo_embeddings
        
        viz_service = SimpleVisualization()
        
        # Generate test data
        query_points, result_points = generate_demo_embeddings("test query", "visual-text", 5)
        
        # Test PCA visualization
        viz_data = viz_service.prepare_visualization_data(
            query_embeddings=query_points,
            result_embeddings=result_points,
            method="PCA"
        )
        
        assert "figure" in viz_data, "No figure generated"
        assert "statistics" in viz_data, "No statistics generated"
        
        # Test t-SNE visualization
        viz_data_tsne = viz_service.prepare_visualization_data(
            query_embeddings=query_points,
            result_embeddings=result_points,
            method="t-SNE"
        )
        
        assert "figure" in viz_data_tsne, "No t-SNE figure generated"
    
    def test_video_player_service(self):
        """Test video player service."""
        from src.services.simple_video_player import SimpleVideoPlayer, generate_demo_segments
        
        player_service = SimpleVideoPlayer()
        
        # Generate test segments
        segments = generate_demo_segments("s3://test/video.mp4", "test query")
        
        # Test video data preparation
        video_data = player_service.prepare_video_data(
            video_s3_uri="s3://test/video.mp4",
            segments=segments
        )
        
        assert "video_url" in video_data, "No video URL"
        assert "segments" in video_data, "No segments data"
        assert "timeline_data" in video_data, "No timeline data"
        
        # Test segment selector options
        options = player_service.get_segment_selector_options(segments)
        assert len(options) == len(segments), "Incorrect selector options"
    
    def test_search_components(self):
        """Test search components."""
        from frontend.components.search_components import SearchComponents
        
        search_comp = SearchComponents()
        
        # Test query analysis
        analysis = search_comp.analyze_search_query("person walking", ["visual-text", "visual-image"])
        
        assert "intent" in analysis, "No intent in analysis"
        assert "complexity" in analysis, "No complexity in analysis"
        
        # Test demo search results
        results = search_comp.generate_demo_search_results("test query", "s3vector", 5)
        
        assert len(results) == 5, "Incorrect number of results"
        assert all("similarity" in r for r in results), "Missing similarity scores"
    
    def test_results_components(self):
        """Test results components."""
        from frontend.components.results_components import ResultsComponents
        
        results_comp = ResultsComponents()
        
        # Test with demo results
        demo_results = [
            {
                "segment_id": f"seg_{i}",
                "similarity": 0.8 + (i * 0.02),
                "vector_type": "visual-text",
                "start_time": i * 5.0,
                "end_time": (i + 1) * 5.0
            }
            for i in range(3)
        ]
        
        analysis = results_comp.analyze_search_results(demo_results)
        
        assert "total_results" in analysis, "No total results"
        assert "avg_similarity" in analysis, "No average similarity"
    
    def test_processing_components(self):
        """Test processing components."""
        from frontend.components.processing_components import ProcessingComponents
        
        proc_comp = ProcessingComponents()
        
        # Test demo processing results
        job_info = {
            'job_id': 'test_job',
            'video_uri': 's3://test/video.mp4',
            'vector_types': ['visual-text'],
            'storage_patterns': ['direct_s3vector'],
            'segment_duration': 5.0
        }
        
        results = proc_comp.generate_demo_processing_results(job_info)
        
        assert "total_segments" in results, "No segment count"
        assert "processing_time_ms" in results, "No processing time"
        assert "cost_estimate" in results, "No cost estimate"
    
    def test_ui_components(self):
        """Test UI components."""
        from frontend.components.visualization_ui import VisualizationUI, generate_demo_embeddings_for_ui
        from frontend.components.video_player_ui import VideoPlayerUI, generate_demo_segments_for_ui
        
        # Test visualization UI
        viz_ui = VisualizationUI()
        assert viz_ui.viz_service is not None, "Viz service not available"
        
        # Test video player UI
        player_ui = VideoPlayerUI()
        assert player_ui.player_service is not None, "Player service not available"
        
        # Test demo data generation
        query_points, result_points = generate_demo_embeddings_for_ui("test", "visual-text", 3)
        assert len(query_points) == 1, "Incorrect query points"
        assert len(result_points) == 3, "Incorrect result points"
        
        segments = generate_demo_segments_for_ui("s3://test/video.mp4", "test")
        assert len(segments) > 0, "No demo segments generated"
    
    def test_config_and_utils(self):
        """Test configuration and utilities."""
        from frontend.components.demo_config import DemoConfig, DemoUtils
        
        config = DemoConfig()
        utils = DemoUtils()
        
        # Test config
        assert len(config.default_vector_types) > 0, "No default vector types"
        assert len(config.workflow_sections) == 5, "Incorrect workflow sections"
        
        # Test utils
        assert utils.validate_s3_uri("s3://bucket/key") == True, "Valid S3 URI rejected"
        assert utils.validate_s3_uri("invalid://uri") == False, "Invalid URI accepted"
        
        progress = utils.get_workflow_progress("query", config.workflow_sections)
        assert 0 <= progress <= 1, "Invalid progress value"
    
    def test_workflow_simulation(self):
        """Test complete workflow simulation."""
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        
        demo = UnifiedS3VectorDemo()
        
        # Simulate upload
        upload_result = demo.processing_components.simulate_video_upload(
            "test-video.mp4", 
            ["visual-text", "visual-image"]
        )
        assert upload_result["status"] == "success", "Upload simulation failed"
        
        # Simulate query analysis
        analysis = demo.search_components.analyze_search_query(
            "person walking",
            ["visual-text", "visual-image"]
        )
        assert analysis["intent"] is not None, "Query analysis failed"
        
        # Simulate search
        search_results = demo.search_components.generate_demo_search_results(
            "person walking",
            "s3vector",
            5
        )
        assert len(search_results) == 5, "Search simulation failed"
        
        # Simulate results analysis
        results_analysis = demo.results_components.analyze_search_results(search_results)
        assert results_analysis["total_results"] == 5, "Results analysis failed"
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks."""
        from src.services.simple_visualization import generate_demo_embeddings
        from src.services.simple_video_player import generate_demo_segments
        
        # Test embedding generation performance
        start_time = time.time()
        query_points, result_points = generate_demo_embeddings("test", "visual-text", 100)
        embedding_time = time.time() - start_time
        
        assert embedding_time < 5.0, f"Embedding generation too slow: {embedding_time:.2f}s"
        
        # Test segment generation performance
        start_time = time.time()
        segments = generate_demo_segments("s3://test/video.mp4", "test")
        segment_time = time.time() - start_time
        
        assert segment_time < 1.0, f"Segment generation too slow: {segment_time:.2f}s"
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests."""
        print("🧪 S3Vector Unified Demo Validation")
        print("=" * 50)
        
        # Define test suite
        tests = [
            ("Core Imports", self.test_core_imports),
            ("Demo Initialization", self.test_demo_initialization),
            ("Query Analysis", self.test_query_analysis),
            ("Visualization Service", self.test_visualization_service),
            ("Video Player Service", self.test_video_player_service),
            ("Search Components", self.test_search_components),
            ("Results Components", self.test_results_components),
            ("Processing Components", self.test_processing_components),
            ("UI Components", self.test_ui_components),
            ("Config and Utils", self.test_config_and_utils),
            ("Workflow Simulation", self.test_workflow_simulation),
            ("Performance Benchmarks", self.test_performance_benchmarks)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Validation Summary")
        print("=" * 50)
        
        total = self.results["total_tests"]
        passed = self.results["passed_tests"]
        failed = self.results["failed_tests"]
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for result in self.results["test_results"]:
                if result["status"] == "FAILED":
                    print(f"  - {result['name']}: {result['error']}")
        
        if success_rate >= 90:
            print("\n🎉 Demo validation PASSED! Ready for use.")
        elif success_rate >= 75:
            print("\n⚠️ Demo validation PARTIAL. Some issues need attention.")
        else:
            print("\n❌ Demo validation FAILED. Significant issues found.")
        
        return self.results


def main():
    """Main validation entry point."""
    validator = DemoValidator()
    results = validator.run_all_tests()
    
    # Exit with appropriate code
    success_rate = (results["passed_tests"] / results["total_tests"]) * 100
    exit_code = 0 if success_rate >= 90 else 1
    
    return exit_code


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
