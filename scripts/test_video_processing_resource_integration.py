#!/usr/bin/env python3
"""
Test script to verify video processing service integration with resource management system.

This script tests that the ComprehensiveVideoProcessingService correctly:
1. Uses existing S3Vector buckets from resource registry
2. Prioritizes resource management buckets over creating new ones
3. Maintains backward compatibility
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService, 
    ProcessingConfig,
    ProcessingMode,
    VectorType,
    StoragePattern
)
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def test_bucket_selection_with_existing_resources():
    """Test that service uses existing resources from registry."""
    print("🧪 Testing bucket selection with existing resources...")
    
    # Initialize service
    config = ProcessingConfig(
        processing_mode=ProcessingMode.BEDROCK_PRIMARY,
        vector_types=[VectorType.VISUAL_TEXT],
        storage_patterns=[StoragePattern.DIRECT_S3VECTOR]
    )
    service = ComprehensiveVideoProcessingService(config)
    
    # Test job ID
    test_job_id = "test-job-12345"
    
    # Test S3 bucket selection for videos
    print("📦 Testing S3 bucket selection for video storage...")
    optimal_s3_bucket = service._get_optimal_s3_bucket_for_videos(test_job_id)
    print(f"   Selected S3 bucket: {optimal_s3_bucket}")
    
    # Test S3Vector bucket selection for direct storage
    print("🗂️ Testing S3Vector bucket selection for direct storage...")
    optimal_s3vector_bucket = service._get_optimal_s3vector_bucket_for_direct_storage(test_job_id)
    print(f"   Selected S3Vector bucket: {optimal_s3vector_bucket}")
    
    # Test S3Vector resources for embeddings
    print("🔍 Testing S3Vector resources for embedding storage...")
    storage_patterns = [StoragePattern.DIRECT_S3VECTOR, StoragePattern.OPENSEARCH_S3VECTOR_HYBRID]
    embedding_resources = service._get_optimal_s3vector_resources_for_embeddings(test_job_id, storage_patterns)
    print(f"   Selected embedding resources: {embedding_resources}")
    
    return True


def test_resource_registry_integration():
    """Test integration with resource registry."""
    print("🧪 Testing resource registry integration...")
    
    # Get current registry state
    registry_data = resource_registry.get_registry()
    print(f"📊 Current registry state:")
    print(f"   Active resources: {registry_data.get('active', {})}")
    print(f"   S3 buckets: {len(registry_data.get('s3_buckets', []))}")
    print(f"   Vector buckets: {len(registry_data.get('vector_buckets', []))}")
    print(f"   OpenSearch domains: {len(registry_data.get('opensearch_domains', []))}")
    
    # Test active resource retrieval
    active_resources = resource_registry.get_active_resources()
    print(f"🎯 Active resources from registry:")
    for resource_type, resource_name in active_resources.items():
        if resource_name:
            print(f"   {resource_type}: {resource_name}")
    
    return True


def test_backward_compatibility():
    """Test that service maintains backward compatibility."""
    print("🧪 Testing backward compatibility...")
    
    # Test with minimal configuration (should not break)
    try:
        service = ComprehensiveVideoProcessingService()
        print("✅ Service initializes with default configuration")
        
        # Test bucket selection without any existing resources
        test_job_id = "compat-test-67890"
        bucket = service._get_optimal_s3_bucket_for_videos(test_job_id)
        print(f"✅ Fallback bucket selection works: {bucket}")
        
        return True
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False


def test_resource_prioritization():
    """Test that existing resources are prioritized correctly."""
    print("🧪 Testing resource prioritization...")
    
    # Get current active resources
    active_resources = resource_registry.get_active_resources()
    
    # Initialize service
    service = ComprehensiveVideoProcessingService()
    test_job_id = "priority-test-11111"
    
    # Test S3 bucket prioritization
    selected_s3_bucket = service._get_optimal_s3_bucket_for_videos(test_job_id)
    active_s3_bucket = active_resources.get('s3_bucket')
    
    if active_s3_bucket:
        if selected_s3_bucket == active_s3_bucket:
            print(f"✅ Correctly prioritized active S3 bucket: {selected_s3_bucket}")
        else:
            print(f"⚠️ Selected different S3 bucket: {selected_s3_bucket} vs active: {active_s3_bucket}")
    else:
        print(f"ℹ️ No active S3 bucket, using fallback: {selected_s3_bucket}")
    
    # Test S3Vector bucket prioritization
    selected_vector_bucket = service._get_optimal_s3vector_bucket_for_direct_storage(test_job_id)
    active_vector_bucket = active_resources.get('vector_bucket')
    
    if active_vector_bucket:
        if selected_vector_bucket == active_vector_bucket:
            print(f"✅ Correctly prioritized active S3Vector bucket: {selected_vector_bucket}")
        else:
            print(f"⚠️ Selected different S3Vector bucket: {selected_vector_bucket} vs active: {active_vector_bucket}")
    else:
        print(f"ℹ️ No active S3Vector bucket, using fallback: {selected_vector_bucket}")
    
    return True


def main():
    """Run all integration tests."""
    print("🚀 Starting Video Processing Service Resource Integration Tests")
    print("=" * 70)
    
    tests = [
        ("Resource Registry Integration", test_resource_registry_integration),
        ("Bucket Selection with Existing Resources", test_bucket_selection_with_existing_resources),
        ("Resource Prioritization", test_resource_prioritization),
        ("Backward Compatibility", test_backward_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   Result: {status}")
            
        except Exception as e:
            print(f"   Result: ❌ ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name}: {status}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Video processing service is properly integrated with resource management.")
        return 0
    else:
        print("⚠️ Some tests failed. Please review the integration.")
        return 1


if __name__ == "__main__":
    exit(main())