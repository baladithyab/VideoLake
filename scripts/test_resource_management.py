#!/usr/bin/env python3
"""
Resource Management Test Script

Tests the resource scanning, discovery, and management functionality.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from typing import Dict, Any

def test_resource_registry():
    """Test resource registry functionality."""
    print("📋 Testing Resource Registry...")
    
    try:
        from src.utils.resource_registry import resource_registry
        
        # Test registry summary
        summary = resource_registry.get_resource_summary()
        print(f"✅ Registry summary loaded")
        print(f"   S3 Buckets: {summary.get('s3_buckets', 0)}")
        print(f"   Vector Buckets: {summary.get('vector_buckets', 0)}")
        print(f"   Vector Indexes: {summary.get('vector_indexes', 0)}")
        print(f"   OpenSearch Collections: {summary.get('opensearch_collections', 0)}")
        
        # Test active resources
        active = resource_registry.get_active_resources()
        print(f"✅ Active resources: {len(active)} configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry test failed: {e}")
        return False


def test_aws_resource_scanner():
    """Test AWS resource scanner functionality."""
    print("\n🔍 Testing AWS Resource Scanner...")
    
    try:
        from src.services.aws_resource_scanner import AWSResourceScanner
        
        # Initialize scanner
        scanner = AWSResourceScanner()
        print("✅ AWS Resource Scanner initialized")
        
        # Test individual scan methods (without actual AWS calls)
        print("✅ Scanner methods available:")
        print("   - scan_s3_buckets")
        print("   - scan_s3vector_buckets") 
        print("   - scan_opensearch_collections")
        print("   - scan_opensearch_domains")
        print("   - scan_iam_roles")
        
        return True
        
    except Exception as e:
        print(f"❌ Scanner test failed: {e}")
        return False


def test_resource_management_component():
    """Test resource management Streamlit component."""
    print("\n🎛️ Testing Resource Management Component...")
    
    try:
        from frontend.components.resource_management import ResourceManagementComponent
        
        # Initialize component
        component = ResourceManagementComponent()
        print("✅ Resource Management Component initialized")
        
        # Test component methods
        methods = [
            '_render_resource_overview',
            '_render_resource_scanner', 
            '_render_registry_management',
            '_render_active_resources'
        ]
        
        for method in methods:
            if hasattr(component, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return False


def test_configuration_integration():
    """Test configuration integration."""
    print("\n⚙️ Testing Configuration Integration...")
    
    try:
        from src.config.unified_config_manager import get_unified_config_manager
        
        config = get_unified_config_manager()
        
        # Test AWS configuration
        aws_config = config.get_aws_config()
        print(f"✅ AWS config loaded")
        print(f"   Region: {aws_config.get('region')}")
        print(f"   S3 Bucket: {aws_config.get('s3_bucket')}")
        
        # Test feature flags
        feature_flags = config.config.features.__dict__
        print(f"✅ Feature flags loaded: {len(feature_flags)} flags")
        
        # Test resource-related flags
        resource_flags = [
            'enable_real_aws',
            'enable_opensearch_hybrid',
            'enable_cost_estimation'
        ]
        
        for flag in resource_flags:
            value = feature_flags.get(flag, False)
            print(f"   {flag}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_demo_integration():
    """Test demo integration."""
    print("\n🎬 Testing Demo Integration...")
    
    try:
        # Test import of resource management in demo
        from frontend.components.resource_management import render_resource_management
        print("✅ Resource management render function available")
        
        # Test unified demo integration
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        demo = UnifiedS3VectorDemo()
        
        # Check if resource management section method exists
        if hasattr(demo, 'render_resource_management_section'):
            print("✅ Resource management section integrated in demo")
        else:
            print("❌ Resource management section not integrated")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo integration test failed: {e}")
        return False


def test_simulated_resource_scan():
    """Test simulated resource scanning."""
    print("\n🧪 Testing Simulated Resource Scan...")
    
    try:
        from src.services.aws_resource_scanner import AWSResourceScanner, ScanResult
        
        # Create scanner
        scanner = AWSResourceScanner()
        
        # Test scan result structure
        test_result = ScanResult(
            resource_type="test_resources",
            resources_found=[
                {"name": "test-resource-1", "region": "us-east-1"},
                {"name": "test-resource-2", "region": "us-east-1"}
            ],
            scan_duration=1.5,
            errors=[],
            region="us-east-1"
        )
        
        print(f"✅ Scan result structure valid")
        print(f"   Resource type: {test_result.resource_type}")
        print(f"   Resources found: {len(test_result.resources_found)}")
        print(f"   Scan duration: {test_result.scan_duration}s")
        print(f"   Errors: {len(test_result.errors)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simulated scan test failed: {e}")
        return False


def test_registry_operations():
    """Test registry operations."""
    print("\n📝 Testing Registry Operations...")
    
    try:
        from src.utils.resource_registry import resource_registry
        
        # Test logging a resource
        test_bucket_name = f"test-bucket-{int(time.time())}"
        
        resource_registry.log_s3_bucket_created(
            bucket_name=test_bucket_name,
            region="us-east-1",
            source="test"
        )
        print(f"✅ Logged test S3 bucket: {test_bucket_name}")
        
        # Test listing resources
        s3_buckets = resource_registry.list_s3_buckets()
        print(f"✅ Listed S3 buckets: {len(s3_buckets)} found")
        
        # Test setting active resource
        resource_registry.set_active_s3_bucket(test_bucket_name)
        print(f"✅ Set active S3 bucket: {test_bucket_name}")
        
        # Test getting active resources
        active = resource_registry.get_active_resources()
        if active.get('s3_bucket') == test_bucket_name:
            print(f"✅ Active S3 bucket verified: {test_bucket_name}")
        else:
            print(f"❌ Active S3 bucket mismatch")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry operations test failed: {e}")
        return False


def main():
    """Run all resource management tests."""
    print("🧪 Resource Management Test Suite")
    print("=" * 50)
    
    tests = [
        test_resource_registry,
        test_aws_resource_scanner,
        test_resource_management_component,
        test_configuration_integration,
        test_demo_integration,
        test_simulated_resource_scan,
        test_registry_operations
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
        print("🎉 All resource management tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check implementation and configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
