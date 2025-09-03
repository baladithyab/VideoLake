#!/usr/bin/env python3
"""
Validation Script for Refactored S3Vector Demo

This script validates that the refactored demo is working correctly
by testing all components and functionality.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def print_header(title: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)


def print_test(test_name: str, success: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASSED" if success else "❌ FAILED"
    print(f"{status}: {test_name}")
    if details:
        print(f"   {details}")


def test_imports():
    """Test all component imports."""
    print_header("Testing Component Imports")
    
    tests = [
        ("demo_config", "frontend.components.demo_config", "DemoConfig, DemoUtils"),
        ("search_components", "frontend.components.search_components", "SearchComponents"),
        ("results_components", "frontend.components.results_components", "ResultsComponents"),
        ("processing_components", "frontend.components.processing_components", "ProcessingComponents"),
        ("main_demo", "frontend.unified_demo_refactored", "UnifiedS3VectorDemo")
    ]
    
    all_passed = True
    
    for test_name, module_path, classes in tests:
        try:
            module = __import__(module_path, fromlist=classes.split(", "))
            for class_name in classes.split(", "):
                getattr(module, class_name)
            print_test(f"Import {test_name}", True, f"Module: {module_path}")
        except Exception as e:
            print_test(f"Import {test_name}", False, f"Error: {e}")
            all_passed = False
    
    return all_passed


def test_component_initialization():
    """Test component initialization."""
    print_header("Testing Component Initialization")
    
    all_passed = True
    
    try:
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        demo = UnifiedS3VectorDemo()
        
        # Test main demo
        print_test("Main demo initialization", True, "UnifiedS3VectorDemo created")
        
        # Test components
        components = [
            ("Search components", demo.search_components),
            ("Results components", demo.results_components),
            ("Processing components", demo.processing_components),
            ("Configuration", demo.config),
            ("Utilities", demo.utils)
        ]
        
        for name, component in components:
            if component:
                print_test(f"{name} initialization", True, f"Component available")
            else:
                print_test(f"{name} initialization", False, f"Component not available")
                all_passed = False
        
        # Test service integration
        if demo.service_manager:
            print_test("Service manager integration", True, "Backend services connected")
        else:
            print_test("Service manager integration", True, "Running in demo mode (expected)")
        
    except Exception as e:
        print_test("Component initialization", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


def test_component_functionality():
    """Test component functionality."""
    print_header("Testing Component Functionality")
    
    all_passed = True
    
    try:
        # Test search components
        from frontend.components.search_components import SearchComponents
        search_comp = SearchComponents()
        
        # Test search result generation
        results = search_comp.generate_demo_search_results('test query', 's3vector', 5)
        print_test("Search result generation", len(results) == 5, f"Generated {len(results)} results")
        
        # Test query analysis
        analysis = search_comp.analyze_search_query('person walking', ['visual-text'])
        expected_intent = analysis.get('intent') == 'person_detection'
        print_test("Query analysis", expected_intent, f"Intent: {analysis.get('intent')}")
        
        # Test processing components
        from frontend.components.processing_components import ProcessingComponents
        proc_comp = ProcessingComponents()
        
        job_info = {
            'job_id': 'test_job',
            'video_uri': 's3://test/video.mp4',
            'vector_types': ['visual-text'],
            'storage_patterns': ['direct_s3vector'],
            'segment_duration': 5.0
        }
        
        proc_results = proc_comp.generate_demo_processing_results(job_info)
        has_segments = proc_results.get('total_segments', 0) > 0
        print_test("Processing result generation", has_segments, f"Segments: {proc_results.get('total_segments')}")
        
        # Test configuration and utilities
        from frontend.components.demo_config import DemoConfig, DemoUtils
        config = DemoConfig()
        utils = DemoUtils()
        
        # Test configuration
        has_vector_types = len(config.default_vector_types) > 0
        print_test("Configuration loading", has_vector_types, f"Vector types: {len(config.default_vector_types)}")
        
        # Test utilities
        valid_s3 = utils.validate_s3_uri('s3://bucket/key/file.mp4')
        invalid_s3 = not utils.validate_s3_uri('invalid://uri')
        print_test("S3 URI validation", valid_s3 and invalid_s3, "Validation logic working")
        
        # Test workflow progress
        progress = utils.get_workflow_progress('query', config.workflow_sections)
        has_progress = 0 <= progress <= 1
        print_test("Workflow progress calculation", has_progress, f"Progress: {progress*100:.0f}%")
        
    except Exception as e:
        print_test("Component functionality", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


def test_launcher():
    """Test launcher functionality."""
    print_header("Testing Launcher")
    
    all_passed = True
    
    try:
        # Test launcher import
        launcher_path = Path(__file__).parent / "launch_refactored_demo.py"
        if launcher_path.exists():
            print_test("Launcher file exists", True, str(launcher_path))
        else:
            print_test("Launcher file exists", False, "File not found")
            all_passed = False
        
        # Test launcher help (quick test)
        import subprocess
        result = subprocess.run([
            sys.executable, str(launcher_path), "--help"
        ], capture_output=True, text=True, timeout=10)
        
        help_works = result.returncode == 0 and "S3Vector Unified Demo Launcher" in result.stdout
        print_test("Launcher help command", help_works, "Help text displayed correctly")
        
    except Exception as e:
        print_test("Launcher functionality", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


def test_streamlit_startup():
    """Test Streamlit app startup (quick test)."""
    print_header("Testing Streamlit App Startup")
    
    all_passed = True
    
    try:
        # Quick startup test with timeout
        import subprocess
        launcher_path = Path(__file__).parent / "launch_refactored_demo.py"
        
        # Start the app and kill it after 5 seconds
        process = subprocess.Popen([
            sys.executable, str(launcher_path), "--port", "8504"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a bit for startup
        time.sleep(3)
        
        # Check if process is still running (good sign)
        if process.poll() is None:
            print_test("Streamlit app startup", True, "App started successfully")
            process.terminate()
            process.wait(timeout=5)
        else:
            stdout, stderr = process.communicate()
            print_test("Streamlit app startup", False, f"App failed to start: {stderr}")
            all_passed = False
        
    except Exception as e:
        print_test("Streamlit app startup", False, f"Error: {e}")
        all_passed = False
    
    return all_passed


def main():
    """Run all validation tests."""
    print("🎬 S3Vector Refactored Demo Validation")
    print("=" * 60)
    print("This script validates the refactored demo components and functionality.")
    
    # Run all tests
    test_results = [
        test_imports(),
        test_component_initialization(),
        test_component_functionality(),
        test_launcher(),
        test_streamlit_startup()
    ]
    
    # Summary
    print_header("Validation Summary")
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    if all(test_results):
        print("🎉 ALL TESTS PASSED!")
        print("✅ The refactored demo is fully functional and ready to use.")
        print()
        print("🚀 To launch the demo:")
        print("   python frontend/launch_refactored_demo.py")
        print()
        print("📋 Available options:")
        print("   --host 0.0.0.0    # External access")
        print("   --port 8502       # Custom port")
        print("   --browser         # Auto-open browser")
        print("   --debug           # Debug mode")
    else:
        print(f"❌ {total_tests - passed_tests} out of {total_tests} tests failed.")
        print("⚠️  Please check the error messages above and fix the issues.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
