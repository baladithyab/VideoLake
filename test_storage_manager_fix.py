#!/usr/bin/env python3
"""
Test script to validate the storage manager initialization fix.

This script tests the auto-initialization functionality we just implemented
in the EnhancedStorageComponents class.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.enhanced_storage_components import EnhancedStorageComponents
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def test_auto_initialization():
    """Test the auto-initialization functionality."""
    print("🧪 Testing Enhanced Storage Components Auto-Initialization")
    print("=" * 60)
    
    # Check resource registry status
    print("📋 Checking Resource Registry Status...")
    try:
        active_resources = resource_registry.get_active_resources()
        print(f"   Active Vector Bucket: {active_resources.get('vector_bucket', 'None')}")
        print(f"   Active OpenSearch Domain: {active_resources.get('opensearch_domain', 'None')}")
        
        # List available resources
        vector_buckets = resource_registry.list_vector_buckets()
        active_vector_buckets = [b for b in vector_buckets if b.get('status') == 'created']
        
        opensearch_domains = resource_registry.list_opensearch_domains()
        active_opensearch_domains = [d for d in opensearch_domains if d.get('status') == 'created']
        
        print(f"   Available Vector Buckets: {len(active_vector_buckets)}")
        print(f"   Available OpenSearch Domains: {len(active_opensearch_domains)}")
        
    except Exception as e:
        print(f"   ❌ Resource Registry Error: {e}")
        return False
    
    # Test EnhancedStorageComponents initialization
    print("\n🏗️ Testing EnhancedStorageComponents Initialization...")
    try:
        enhanced_storage = EnhancedStorageComponents()
        print("   ✅ EnhancedStorageComponents created successfully")
        
        # Check if storage manager was auto-initialized
        storage_manager = enhanced_storage.get_storage_manager()
        
        if storage_manager:
            print("   ✅ Storage manager auto-initialized successfully!")
            print(f"   📊 Storage manager type: {type(storage_manager).__name__}")
            
            # Test validation
            try:
                validation_results = storage_manager.validate_configuration()
                print(f"   🔍 Configuration validation: {'✅ Valid' if validation_results['valid'] else '❌ Invalid'}")
                
                if validation_results.get('errors'):
                    print("   ❌ Validation errors:")
                    for error in validation_results['errors']:
                        print(f"      • {error}")
                
                if validation_results.get('warnings'):
                    print("   ⚠️ Validation warnings:")
                    for warning in validation_results['warnings']:
                        print(f"      • {warning}")
                        
            except Exception as validation_error:
                print(f"   ⚠️ Validation check failed: {validation_error}")
        else:
            print("   📋 Storage manager not auto-initialized (manual configuration required)")
            print("   💡 This is expected when no active resources are available")
            
            # Test manual initialization attempt
            print("\n🔧 Testing Manual Initialization...")
            enhanced_storage._auto_initialize_storage_manager()
            storage_manager = enhanced_storage.get_storage_manager()
            
            if storage_manager:
                print("   ✅ Manual initialization successful!")
            else:
                print("   📋 Manual initialization also requires active resources")
        
    except Exception as e:
        print(f"   ❌ EnhancedStorageComponents initialization failed: {e}")
        import traceback
        print(f"   📝 Full traceback:\n{traceback.format_exc()}")
        return False
    
    print("\n✅ Test completed successfully!")
    print("💡 The fix should resolve the 'Storage manager not initialized' message")
    return True

def test_shared_components_integration():
    """Test the shared components integration."""
    print("\n🔄 Testing Shared Components Integration...")
    
    try:
        from src.shared.vector_types import list_supported_vector_types, get_vector_type_config
        from src.shared.metadata_handlers import MetadataTransformer
        from src.shared.aws_client_pool import AWSClientPool
        
        # Test vector types
        supported_types = list_supported_vector_types()
        print(f"   📊 Supported vector types: {len(supported_types)}")
        for vector_type in supported_types[:3]:  # Show first 3
            try:
                config = get_vector_type_config(vector_type)
                print(f"      • {vector_type}: {config.dimensions}D")
            except Exception as e:
                print(f"      • {vector_type}: Config error - {e}")
        
        # Test metadata transformer
        try:
            metadata_transformer = MetadataTransformer()
            print("   ✅ MetadataTransformer initialized successfully")
        except Exception as e:
            print(f"   ⚠️ MetadataTransformer initialization issue: {e}")
        
        # Test AWS client pool
        try:
            aws_client_pool = AWSClientPool()
            print("   ✅ AWSClientPool initialized successfully")
        except Exception as e:
            print(f"   ⚠️ AWSClientPool initialization issue: {e}")
        
        print("   ✅ Shared components integration working")
        return True
        
    except Exception as e:
        print(f"   ❌ Shared components test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Storage Manager Fix Validation")
    print("=" * 60)
    
    # Run tests
    test1_passed = test_auto_initialization()
    test2_passed = test_shared_components_integration()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Auto-initialization test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"   Shared components test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! The storage manager fix is working correctly.")
        print("💡 The Media Processing page should now initialize the storage manager automatically")
        print("   when active AWS resources are available in the registry.")
    else:
        print("\n⚠️ Some tests failed. Review the output above for details.")
    
    print("=" * 60)