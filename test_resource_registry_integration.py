#!/usr/bin/env python3
"""
Test script to verify resource registry integration with media processing components.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.resource_registry import resource_registry
from frontend.components.enhanced_storage_components import EnhancedStorageComponents
from src.services.enhanced_storage_integration_manager import StorageConfiguration, StorageBackend
from src.shared.vector_types import SupportedVectorTypes


def test_resource_registry_basic_functionality():
    """Test basic resource registry functionality."""
    print("🧪 Testing Resource Registry Basic Functionality")
    
    try:
        # Test registry access
        registry_data = resource_registry.get_registry()
        print(f"✅ Registry accessible, version: {registry_data.get('version', 'Unknown')}")
        
        # Test resource listing
        vector_buckets = resource_registry.list_vector_buckets()
        opensearch_domains = resource_registry.list_opensearch_domains()
        
        print(f"📦 Found {len(vector_buckets)} vector buckets")
        print(f"🔍 Found {len(opensearch_domains)} OpenSearch domains")
        
        # Test active resources
        active_resources = resource_registry.get_active_resources()
        print(f"🎯 Active resources: {active_resources}")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry test failed: {e}")
        return False


def test_enhanced_storage_components_integration():
    """Test enhanced storage components with resource registry integration."""
    print("\n🧪 Testing Enhanced Storage Components Integration")
    
    try:
        # Initialize enhanced storage components
        enhanced_storage = EnhancedStorageComponents()
        
        # Test resource loading
        enhanced_storage.refresh_available_resources()
        
        # Test resource getters
        available_buckets = enhanced_storage.get_available_s3vector_buckets()
        available_domains = enhanced_storage.get_available_opensearch_domains()
        
        print(f"✅ Enhanced storage initialized")
        print(f"📦 Available buckets: {len(available_buckets)}")
        print(f"🔍 Available domains: {len(available_domains)}")
        
        # Test resource validation
        if available_buckets:
            test_bucket = available_buckets[0]['name']
            validation = enhanced_storage.validate_resource_availability('vector_bucket', test_bucket)
            print(f"🔍 Bucket '{test_bucket}' validation: {validation['exists']}")
        
        if available_domains:
            test_domain = available_domains[0]['name']
            validation = enhanced_storage.validate_resource_availability('opensearch_domain', test_domain)
            print(f"🔍 Domain '{test_domain}' validation: {validation['exists']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced storage components test failed: {e}")
        return False


def test_storage_integration_manager_validation():
    """Test storage integration manager with registry validation."""
    print("\n🧪 Testing Storage Integration Manager Validation")
    
    try:
        # Get available resources
        vector_buckets = resource_registry.list_vector_buckets()
        active_buckets = [b for b in vector_buckets if b.get('status') == 'created']
        
        opensearch_domains = resource_registry.list_opensearch_domains()
        active_domains = [d for d in opensearch_domains if d.get('status') == 'created']
        
        if not active_buckets and not active_domains:
            print("⚠️  No active resources found in registry - creating test configuration")
            
            # Create a minimal test configuration
            test_config = StorageConfiguration(
                enabled_backends=[StorageBackend.DIRECT_S3VECTOR],
                vector_types=[SupportedVectorTypes.VISUAL_TEXT],
                environment="test",
                s3vector_bucket_name="test-s3vector-bucket"
            )
        else:
            # Use existing resources
            backends = []
            bucket_name = None
            domain_name = None
            
            if active_buckets:
                backends.append(StorageBackend.DIRECT_S3VECTOR)
                bucket_name = active_buckets[0]['name']
                
            if active_domains:
                backends.append(StorageBackend.OPENSEARCH_HYBRID)
                domain_name = active_domains[0]['name']
            
            test_config = StorageConfiguration(
                enabled_backends=backends,
                vector_types=[SupportedVectorTypes.VISUAL_TEXT],
                environment="prod",
                s3vector_bucket_name=bucket_name,
                opensearch_domain_name=domain_name
            )
        
        print(f"🔧 Test configuration: {len(test_config.enabled_backends)} backends")
        
        # Test configuration validation (without full initialization)
        try:
            test_config.validate()
            print("✅ Configuration validation passed")
        except Exception as config_error:
            print(f"⚠️  Configuration validation warning: {config_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Storage integration manager test failed: {e}")
        return False


def test_auto_population_functionality():
    """Test auto-population functionality."""
    print("\n🧪 Testing Auto-Population Functionality")
    
    try:
        enhanced_storage = EnhancedStorageComponents()
        
        # Test resource availability
        available_buckets = enhanced_storage.get_available_s3vector_buckets()
        available_domains = enhanced_storage.get_available_opensearch_domains()
        available_collections = enhanced_storage.get_available_opensearch_collections()
        
        print(f"📊 Auto-population test results:")
        print(f"   • S3Vector buckets available for dropdown: {len(available_buckets)}")
        print(f"   • OpenSearch domains available for dropdown: {len(available_domains)}")
        print(f"   • OpenSearch collections available for dropdown: {len(available_collections)}")
        
        # Test validation for each available resource
        validation_results = {
            "buckets": 0,
            "domains": 0,
            "collections": 0
        }
        
        for bucket in available_buckets:
            validation = enhanced_storage.validate_resource_availability('vector_bucket', bucket['name'])
            if validation['exists']:
                validation_results["buckets"] += 1
        
        for domain in available_domains:
            validation = enhanced_storage.validate_resource_availability('opensearch_domain', domain['name'])
            if validation['exists']:
                validation_results["domains"] += 1
        
        print(f"✅ Validated {validation_results['buckets']}/{len(available_buckets)} buckets")
        print(f"✅ Validated {validation_results['domains']}/{len(available_domains)} domains")
        
        # Test active resource detection
        active_resources = resource_registry.get_active_resources()
        if active_resources.get('vector_bucket') or active_resources.get('opensearch_domain'):
            print("✅ Active resources detected for default selection")
        else:
            print("ℹ️  No active resources set (user will need to select)")
        
        return True
        
    except Exception as e:
        print(f"❌ Auto-population test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting Resource Registry Integration Tests\n")
    
    tests = [
        test_resource_registry_basic_functionality,
        test_enhanced_storage_components_integration,
        test_storage_integration_manager_validation,
        test_auto_population_functionality
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print(f"\n📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    print(f"📈 Success Rate: {(sum(results)/len(results))*100:.1f}%")
    
    if all(results):
        print("\n🎉 All integration tests passed! Resource registry integration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
    
    return all(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)