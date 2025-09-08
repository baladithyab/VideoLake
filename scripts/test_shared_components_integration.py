#!/usr/bin/env python3
"""
Test script to validate shared components integration.

This script tests that all shared components can be imported and used correctly.
"""

import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def test_imports():
    """Test that all shared components can be imported."""
    print("Testing shared components imports...")
    
    try:
        # Test basic imports
        from src.shared import (
            # Vector Types
            VectorTypeRegistry,
            SupportedVectorTypes,
            VectorTypeConfig,
            get_vector_type_config,
            validate_vector_dimensions,
            
            # Resource Selectors
            S3BucketSelector,
            IndexSelector,
            ResourceNamingStrategy,
            validate_resource_name,
            
            # Metadata Handlers
            MetadataTransformer,
            MediaMetadata,
            S3VectorMetadataHandler,
            OpenSearchMetadataHandler,
            
            # AWS Client Pool
            AWSClientPool,
            ClientPoolConfig,
            AWSService,
            get_pooled_client,
            reset_client_pool
        )
        print("✅ All imports successful")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_vector_types():
    """Test vector types functionality."""
    print("\nTesting vector types functionality...")
    
    try:
        from src.shared import get_vector_type_config, SupportedVectorTypes, validate_vector_dimensions
        
        # Test getting config for a known vector type
        config = get_vector_type_config(SupportedVectorTypes.VISUAL_TEXT)
        print(f"✅ Visual-text config: {config.dimensions} dimensions")
        
        # Test validation with proper vector data (list of floats)
        test_vector_1024 = [0.1] * 1024  # Correct dimensions for VISUAL_TEXT
        valid = validate_vector_dimensions(SupportedVectorTypes.VISUAL_TEXT, test_vector_1024)
        print(f"✅ Dimension validation: {valid}")
        
        # Test invalid dimensions
        try:
            test_vector_wrong = [0.1] * 999  # Wrong dimensions
            validate_vector_dimensions(SupportedVectorTypes.VISUAL_TEXT, test_vector_wrong)
            print("❌ Should have failed with wrong dimensions")
            return False
        except Exception:
            print("✅ Invalid dimension check: correctly rejected wrong dimensions")
        
        return True
        
    except Exception as e:
        print(f"❌ Vector types test error: {e}")
        return False

def test_resource_selectors():
    """Test resource selectors functionality."""
    print("\nTesting resource selectors functionality...")
    
    try:
        from src.shared import S3BucketSelector, ResourceNamingStrategy, validate_resource_name
        from src.shared.resource_selectors import ResourceType
        
        # Test S3 bucket name generation using selector
        selector = S3BucketSelector(ResourceNamingStrategy.ENVIRONMENT_PREFIX)
        bucket_name = selector.generate_name("test-bucket", environment="dev")
        print(f"✅ Generated bucket name: {bucket_name}")
        
        # Test resource name validation
        is_valid = validate_resource_name(ResourceType.S3_BUCKET, bucket_name)
        print(f"✅ Bucket name validation: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Resource selectors test error: {e}")
        return False

def test_metadata_handlers():
    """Test metadata handlers functionality."""
    print("\nTesting metadata handlers functionality...")
    
    try:
        from src.shared import MetadataTransformer, MediaMetadata
        from src.shared.metadata_handlers import MetadataFormat
        
        # Create test metadata with correct parameters
        test_metadata = MediaMetadata(
            file_name="test.mp4",
            s3_storage_location="s3://test-bucket/videos/test.mp4",
            file_format="mp4",
            file_size_bytes=1024000,
            duration_seconds=120.5,
            resolution="1920x1080",
            content_category="video"
        )
        
        # Test transformation to S3Vector format
        transformer = MetadataTransformer()
        s3vector_data = transformer.transform(test_metadata, MetadataFormat.S3_VECTOR)
        print(f"✅ S3Vector format transformation: {len(s3vector_data)} fields")
        
        # Test validation
        is_valid = transformer.validate(s3vector_data, MetadataFormat.S3_VECTOR)
        print(f"✅ S3Vector validation: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata handlers test error: {e}")
        return False

def test_aws_client_pool():
    """Test AWS client pool functionality."""
    print("\nTesting AWS client pool functionality...")
    
    try:
        from src.shared import AWSService, ClientPoolConfig, AWSClientPool
        from src.shared.aws_client_pool import ClientPoolStrategy
        
        # Test pool configuration
        config = ClientPoolConfig(
            strategy=ClientPoolStrategy.SINGLETON,
            max_pool_size=5,
            enable_health_checks=False,  # Disable to prevent background threads
            enable_metrics=False         # Disable to prevent background threads
        )
        config.validate()
        print("✅ Client pool config validation passed")
        
        # Test pool creation (without actually connecting to AWS)
        pool = AWSClientPool(config)
        stats = pool.get_pool_statistics()
        print(f"✅ Pool statistics: {stats['config']['strategy']}")
        
        # Clean shutdown (should be fast now)
        pool.shutdown()
        print("✅ Pool shutdown completed")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS client pool test error: {e}")
        return False

def main():
    """Run all integration tests."""
    print("=== Shared Components Integration Test ===\n")
    
    tests = [
        test_imports,
        test_vector_types,
        test_resource_selectors, 
        test_metadata_handlers,
        test_aws_client_pool
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All integration tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())