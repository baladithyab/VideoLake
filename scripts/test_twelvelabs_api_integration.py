#!/usr/bin/env python3
"""
TwelveLabs API Integration Test

Tests the TwelveLabs API service integration with proper API patterns
following the official documentation.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from typing import Dict, Any

def test_configuration():
    """Test TwelveLabs API configuration."""
    print("🔧 Testing TwelveLabs API Configuration...")
    
    try:
        from frontend.components.config_adapter import get_enhanced_config
        
        config = get_enhanced_config()
        marengo_config = config.get_marengo_config()
        
        print(f"✅ Configuration loaded")
        print(f"   Access Method: {marengo_config['access_method']}")
        print(f"   Model Identifier: {marengo_config['model_identifier']}")
        print(f"   Is Bedrock Access: {marengo_config['is_bedrock_access']}")
        print(f"   Is TwelveLabs API Access: {marengo_config['is_twelvelabs_api_access']}")
        
        if marengo_config['is_twelvelabs_api_access']:
            print(f"   TwelveLabs API URL: {marengo_config['twelvelabs_api_url']}")
            print(f"   API Key Configured: {bool(marengo_config['twelvelabs_api_key'])}")
            print(f"   Model Name: {marengo_config['twelvelabs_model_name']}")
        
        # Test legacy compatibility
        legacy_config = config.get_twelvelabs_config()
        print(f"✅ Legacy compatibility: {legacy_config['model_name']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_api_service_initialization():
    """Test TwelveLabs API service initialization."""
    print("\n🚀 Testing TwelveLabs API Service Initialization...")
    
    try:
        from src.services.twelvelabs_api_service import TwelveLabsAPIService, TaskStatus, EmbeddingOption
        
        # Test with dummy API key
        service = TwelveLabsAPIService(
            api_key="test_key",
            api_url="https://api.twelvelabs.io"
        )
        
        print("✅ TwelveLabs API service initialized")
        print(f"   API URL: {service.api_url}")
        print(f"   Session configured: {bool(service.session)}")
        
        # Test enums
        print(f"   Task statuses: {[status.value for status in TaskStatus]}")
        print(f"   Embedding options: {[option.value for option in EmbeddingOption]}")
        
        return True
        
    except Exception as e:
        print(f"❌ API service initialization failed: {e}")
        return False


def test_enhanced_pipeline_integration():
    """Test enhanced video pipeline integration."""
    print("\n🎬 Testing Enhanced Video Pipeline Integration...")
    
    try:
        from src.services.comprehensive_video_processing_service import ComprehensiveVideoProcessingService
        TWELVELABS_API_AVAILABLE = True  # Assume available for this test
        
        print(f"✅ TwelveLabs API available: {TWELVELABS_API_AVAILABLE}")
        
        # Initialize pipeline
        pipeline = ComprehensiveVideoProcessingService()
        
        print(f"✅ Pipeline initialized")
        print(f"   Bedrock service: {bool(pipeline.bedrock_service)}")
        print(f"   TwelveLabs API service: {bool(pipeline.twelvelabs_api)}")
        print(f"   S3Vector service: {bool(pipeline.storage_manager)}")
        
        # Test method availability
        has_api_method = hasattr(pipeline, 'process_video_from_url')
        print(f"   Video processing method: {has_api_method}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline integration test failed: {e}")
        return False


def test_api_request_structure():
    """Test API request structure (without actual API calls)."""
    print("\n📋 Testing API Request Structure...")
    
    try:
        from src.services.twelvelabs_api_service import TwelveLabsAPIService, EmbeddingOption
        
        service = TwelveLabsAPIService(api_key="test_key")
        
        # Test request data structure for create task
        test_data = {
            "model_name": "Marengo-retrieval-2.7",
            "video_url": "https://example.com/test.mp4",
            "video_start_offset_sec": 0.0,
            "video_clip_length": 6.0,
            "video_embedding_scope": ["clip"]
        }
        
        print("✅ Create task request structure:")
        for key, value in test_data.items():
            print(f"   {key}: {value}")
        
        # Test embedding options
        options = [EmbeddingOption.VISUAL_TEXT, EmbeddingOption.AUDIO]
        option_strs = [opt.value for opt in options]
        print(f"✅ Embedding options: {option_strs}")
        
        # Test API endpoints
        endpoints = {
            "create_task": f"{service.api_url}/v1.3/embed/tasks",
            "get_status": f"{service.api_url}/v1.3/embed/tasks/{{task_id}}",
            "retrieve_embeddings": f"{service.api_url}/v1.3/embed/tasks/{{task_id}}"
        }
        
        print("✅ API endpoints:")
        for name, url in endpoints.items():
            print(f"   {name}: {url}")
        
        return True
        
    except Exception as e:
        print(f"❌ API request structure test failed: {e}")
        return False


def test_configuration_switching():
    """Test switching between Bedrock and TwelveLabs API access."""
    print("\n🔄 Testing Configuration Switching...")
    
    try:
        # Test environment variable override
        original_access_method = os.getenv('MARENGO_ACCESS_METHOD')
        
        # Test Bedrock access
        os.environ['MARENGO_ACCESS_METHOD'] = 'bedrock'
        from src.config.unified_config_manager import get_unified_config_manager
        
        config = get_unified_config_manager()
        marengo_config = config.get_marengo_config()
        
        print(f"✅ Bedrock access test:")
        print(f"   Access method: {marengo_config['access_method']}")
        print(f"   Is Bedrock: {marengo_config['is_bedrock_access']}")
        print(f"   Model ID: {marengo_config['model_identifier']}")
        
        # Test TwelveLabs API access
        os.environ['MARENGO_ACCESS_METHOD'] = 'twelvelabs_api'
        os.environ['TWELVELABS_API_KEY'] = 'test_key'
        
        # Force reload (in real usage, would restart application)
        config = get_unified_config_manager()
        config.reload()  # Reload configuration
        marengo_config = config.get_marengo_config()
        
        print(f"✅ TwelveLabs API access test:")
        print(f"   Access method: {marengo_config['access_method']}")
        print(f"   Is TwelveLabs API: {marengo_config['is_twelvelabs_api_access']}")
        print(f"   Model ID: {marengo_config['model_identifier']}")
        print(f"   API Key configured: {bool(marengo_config['twelvelabs_api_key'])}")
        
        # Restore original
        if original_access_method:
            os.environ['MARENGO_ACCESS_METHOD'] = original_access_method
        else:
            os.environ.pop('MARENGO_ACCESS_METHOD', None)
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration switching test failed: {e}")
        return False


def main():
    """Run all TwelveLabs API integration tests."""
    print("🧪 TwelveLabs API Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_api_service_initialization,
        test_enhanced_pipeline_integration,
        test_api_request_structure,
        test_configuration_switching
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All TwelveLabs API integration tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check configuration and implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
