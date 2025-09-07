#!/usr/bin/env python3
"""
Test script to reproduce and debug the OpenSearch domain creation error.
This script will help isolate the 'arn' error in the _create_real_opensearch_domain method.
"""

import sys
from pathlib import Path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.workflow_resource_manager import WorkflowResourceManager
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_opensearch_domain_creation():
    """Test OpenSearch domain creation with enhanced debugging."""
    print("🔧 Testing OpenSearch Domain Creation with Enhanced Debugging")
    print("=" * 60)
    
    try:
        # Initialize the manager
        print("1. Initializing WorkflowResourceManager...")
        manager = WorkflowResourceManager()
        print("✅ Manager initialized successfully")
        
        # Test domain creation with a test bucket
        test_domain_name = f"test-debug-domain-{int(__import__('time').time())}"
        test_bucket_name = f"test-debug-bucket-{int(__import__('time').time())}"
        
        print(f"\n2. Testing domain creation:")
        print(f"   Domain name: {test_domain_name}")
        print(f"   S3Vector bucket: {test_bucket_name}")
        
        # This should trigger the error and show our enhanced logging
        success, domain_arn = manager._create_real_opensearch_domain(
            domain_name=test_domain_name,
            s3vector_bucket_name=test_bucket_name
        )
        
        if success:
            print(f"✅ Domain created successfully: {domain_arn}")
        else:
            print("❌ Domain creation failed")
            
    except Exception as e:
        print(f"\n❌ Error during testing: {type(e).__name__}: {e}")
        print("\n📋 Full traceback:")
        import traceback
        traceback.print_exc()
        
        # Analyze the error
        print(f"\n🔍 Error Analysis:")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {str(e)}")
        
        if "'arn'" in str(e).lower():
            print("   🎯 This appears to be the 'arn' error we're debugging!")
            print("   📝 Check the logs above for detailed ARN retrieval information")
        
        return False
    
    return True

def test_s3vector_bucket_arn_retrieval():
    """Test S3Vector bucket ARN retrieval in isolation."""
    print("\n🔧 Testing S3Vector Bucket ARN Retrieval")
    print("=" * 50)
    
    try:
        manager = WorkflowResourceManager()
        test_bucket_name = f"test-arn-bucket-{int(__import__('time').time())}"
        
        print(f"Testing ARN retrieval for bucket: {test_bucket_name}")
        
        # Try to get a non-existent bucket to see the error handling
        try:
            response = manager.s3vectors_client.get_vector_bucket(vectorBucketName=test_bucket_name)
            print(f"✅ Bucket response: {response}")
            
            if 'vectorBucket' in response:
                vector_bucket = response['vectorBucket']
                print(f"📋 Vector bucket keys: {list(vector_bucket.keys())}")
                
                if 'arn' in vector_bucket:
                    arn = vector_bucket['arn']
                    print(f"✅ ARN retrieved: {arn}")
                else:
                    print("❌ No 'arn' key in vectorBucket data")
            else:
                print("❌ No 'vectorBucket' key in response")
                
        except Exception as e:
            print(f"❌ Error retrieving bucket: {type(e).__name__}: {e}")
            
            # This is expected for non-existent bucket
            if "NoSuchVectorBucket" in str(e):
                print("ℹ️ This is expected for non-existent bucket")
            
    except Exception as e:
        print(f"❌ Error in ARN retrieval test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🐛 OpenSearch Domain Creation Debug Test")
    print("=" * 60)
    
    # Test 1: S3Vector bucket ARN retrieval
    test_s3vector_bucket_arn_retrieval()
    
    # Test 2: Full domain creation (this should show the error)
    test_opensearch_domain_creation()
    
    print("\n🏁 Debug test completed!")
    print("📝 Check the logs above for detailed error information")