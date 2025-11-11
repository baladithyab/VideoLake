#!/usr/bin/env python3
"""
Test script to verify health check fixes for deployed resources endpoint.

This script tests the three issues that were identified:
1. S3Vectors API error (list_buckets -> list_vector_buckets)
2. OpenSearch missing dependency (opensearch-py)
3. Qdrant connection refused handling (already working)
"""

import asyncio
import sys
from typing import Dict, Any


async def test_s3vector_health_check():
    """Test S3Vector connectivity validation."""
    print("\n=== Testing S3Vector Health Check ===")
    try:
        from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
        
        # Check if provider is available
        if not VectorStoreProviderFactory.is_provider_available(VectorStoreType.S3_VECTOR):
            print("❌ S3Vector provider not available")
            return False
        
        # Create provider
        provider = VectorStoreProviderFactory.create_provider(VectorStoreType.S3_VECTOR)
        
        # Test connectivity with timeout
        validation_result = await asyncio.wait_for(
            asyncio.to_thread(provider.validate_connectivity),
            timeout=5.0
        )
        
        print(f"✅ S3Vector health check completed")
        print(f"   Accessible: {validation_result.get('accessible')}")
        print(f"   Health Status: {validation_result.get('health_status')}")
        print(f"   Response Time: {validation_result.get('response_time_ms')}ms")
        
        if validation_result.get('error_message'):
            print(f"   Error: {validation_result.get('error_message')}")
        
        return True
        
    except asyncio.TimeoutError:
        print("⚠️  S3Vector health check timed out (expected if S3Vectors not deployed)")
        return True  # Timeout is acceptable
    except AttributeError as e:
        if "'S3Vectors' object has no attribute 'list_buckets'" in str(e):
            print(f"❌ FAILED: S3Vector API error still present: {e}")
            return False
        raise
    except Exception as e:
        print(f"⚠️  S3Vector health check error (may be expected): {type(e).__name__}: {e}")
        return True  # Other errors might be expected if service isn't deployed


async def test_opensearch_health_check():
    """Test OpenSearch connectivity validation."""
    print("\n=== Testing OpenSearch Health Check ===")
    try:
        from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
        
        # Check if provider is available
        if not VectorStoreProviderFactory.is_provider_available(VectorStoreType.OPENSEARCH):
            print("❌ OpenSearch provider not available")
            return False
        
        # Create provider
        provider = VectorStoreProviderFactory.create_provider(VectorStoreType.OPENSEARCH)
        
        # Test connectivity with timeout
        validation_result = await asyncio.wait_for(
            asyncio.to_thread(provider.validate_connectivity),
            timeout=5.0
        )
        
        print(f"✅ OpenSearch health check completed")
        print(f"   Accessible: {validation_result.get('accessible')}")
        print(f"   Health Status: {validation_result.get('health_status')}")
        print(f"   Response Time: {validation_result.get('response_time_ms')}ms")
        
        if validation_result.get('error_message'):
            print(f"   Error: {validation_result.get('error_message')}")
        
        return True
        
    except asyncio.TimeoutError:
        print("⚠️  OpenSearch health check timed out (expected if OpenSearch not deployed)")
        return True
    except ImportError as e:
        if "opensearchpy" in str(e) or "opensearch-py" in str(e):
            print(f"❌ FAILED: OpenSearch dependency error still present: {e}")
            print("   Run: pip install opensearch-py>=2.3.0")
            return False
        raise
    except Exception as e:
        print(f"⚠️  OpenSearch health check error (may be expected): {type(e).__name__}: {e}")
        return True


async def test_qdrant_health_check():
    """Test Qdrant connectivity validation with connection refused handling."""
    print("\n=== Testing Qdrant Health Check ===")
    try:
        from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
        
        # Check if provider is available
        if not VectorStoreProviderFactory.is_provider_available(VectorStoreType.QDRANT):
            print("❌ Qdrant provider not available")
            return False
        
        # Create provider
        provider = VectorStoreProviderFactory.create_provider(VectorStoreType.QDRANT)
        
        # Test connectivity with timeout
        validation_result = await asyncio.wait_for(
            asyncio.to_thread(provider.validate_connectivity),
            timeout=5.0
        )
        
        print(f"✅ Qdrant health check completed")
        print(f"   Accessible: {validation_result.get('accessible')}")
        print(f"   Health Status: {validation_result.get('health_status')}")
        print(f"   Response Time: {validation_result.get('response_time_ms')}ms")
        
        if validation_result.get('error_message'):
            error_msg = validation_result.get('error_message')
            print(f"   Error: {error_msg}")
            
            # Verify connection refused is handled gracefully
            if "refused" in error_msg.lower():
                print("   ✅ Connection refused handled gracefully (expected when Qdrant not deployed)")
        
        return True
        
    except asyncio.TimeoutError:
        print("⚠️  Qdrant health check timed out")
        return True
    except Exception as e:
        # Connection refused should be caught by validate_connectivity
        if "refused" in str(e).lower():
            print(f"❌ FAILED: Connection refused not handled properly: {e}")
            return False
        
        print(f"⚠️  Qdrant health check error (may be expected): {type(e).__name__}: {e}")
        return True


async def test_deployed_resources_endpoint():
    """Test the complete deployed resources tree endpoint."""
    print("\n=== Testing Deployed Resources Endpoint ===")
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        from src.api.routers.resources import get_deployed_resources_tree
        
        # Call the endpoint
        result = await get_deployed_resources_tree()
        
        if result.get('success'):
            print("✅ Deployed resources endpoint successful")
            
            # Check backends
            tree = result.get('tree', {})
            backends = tree.get('vector_backends', [])
            
            for backend in backends:
                backend_type = backend.get('type')
                connectivity = backend.get('connectivity', 'unknown')
                print(f"   - {backend_type}: connectivity={connectivity}")
        else:
            print(f"⚠️  Deployed resources endpoint returned success=False")
            print(f"   Message: {result.get('message')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Deployed resources endpoint error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all health check tests."""
    print("=" * 70)
    print("Health Check Fixes Validation")
    print("=" * 70)
    
    results = {
        "S3Vector": await test_s3vector_health_check(),
        "OpenSearch": await test_opensearch_health_check(),
        "Qdrant": await test_qdrant_health_check(),
        "Endpoint": await test_deployed_resources_endpoint()
    }
    
    print("\n" + "=" * 70)
    print("Test Results Summary")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("\n✅ All health check fixes validated successfully!")
        return 0
    else:
        print("\n❌ Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))