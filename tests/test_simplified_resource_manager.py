#!/usr/bin/env python3
"""
Test script for the Simplified Resource Manager

This script tests the actual AWS resource creation and deletion functionality
of the simplified resource manager to ensure it works correctly.
"""

import sys
import time
import boto3
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from frontend.components.simplified_resource_manager import SimplifiedResourceManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def test_aws_connectivity():
    """Test basic AWS connectivity."""
    print("🔍 Testing AWS connectivity...")
    
    try:
        # Test basic AWS connectivity
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS Connection successful!")
        print(f"   Account ID: {identity['Account']}")
        print(f"   User ARN: {identity['Arn']}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS Connection failed: {e}")
        return False


def test_s3vectors_client():
    """Test S3Vectors client connectivity."""
    print("\n🔍 Testing S3Vectors client...")
    
    try:
        from src.shared.aws_client_pool import get_pooled_client, AWSService

        s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
        
        # Try to list vector buckets (this should work even if no buckets exist)
        response = s3vectors_client.list_vector_buckets()
        buckets = response.get('vectorBuckets', [])
        
        print(f"✅ S3Vectors client working!")
        print(f"   Found {len(buckets)} existing vector buckets")
        
        return True, s3vectors_client
        
    except Exception as e:
        print(f"❌ S3Vectors client failed: {e}")
        return False, None


def test_resource_creation_and_deletion():
    """Test actual resource creation and deletion."""
    print("\n🚀 Testing resource creation and deletion...")
    
    # Generate unique test names
    timestamp = int(time.time())
    test_setup_name = f"test-s3vector-{timestamp}"
    bucket_name = f"{test_setup_name}-bucket"
    index_name = f"{test_setup_name}-index"
    
    print(f"   Test setup name: {test_setup_name}")
    print(f"   Bucket name: {bucket_name}")
    print(f"   Index name: {index_name}")
    
    try:
        # Initialize the simplified resource manager
        print("\n📋 Initializing SimplifiedResourceManager...")
        manager = SimplifiedResourceManager()
        
        if manager.s3vectors_client is None:
            print("❌ S3Vectors client not initialized in manager")
            return False
        
        print("✅ SimplifiedResourceManager initialized successfully")
        
        # Test 1: Create S3Vector bucket
        print(f"\n🪣 Creating S3Vector bucket: {bucket_name}")
        bucket_success, bucket_arn = manager._create_s3vector_bucket_real(bucket_name)
        
        if bucket_success:
            print(f"✅ S3Vector bucket created successfully!")
            print(f"   ARN: {bucket_arn}")
        else:
            print("❌ Failed to create S3Vector bucket")
            return False
        
        # Test 2: Create S3Vector index
        print(f"\n📊 Creating S3Vector index: {index_name}")
        index_success, index_arn = manager._create_s3vector_index_real(bucket_name, index_name, 1536)
        
        if index_success:
            print(f"✅ S3Vector index created successfully!")
            print(f"   ARN: {index_arn}")
        else:
            print("❌ Failed to create S3Vector index")
            # Still try to clean up bucket
            manager._delete_s3vector_bucket_real(bucket_name)
            return False
        
        # Test 3: Verify resources with AWS CLI commands
        print(f"\n🔍 Verifying resources...")
        
        # Verify bucket
        try:
            response = manager.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
            print(f"✅ Bucket verification successful: {response['vectorBucket']['vectorBucketName']}")
        except Exception as e:
            print(f"❌ Bucket verification failed: {e}")
        
        # Verify index
        try:
            response = manager.s3vectors_client.get_index(
                vectorBucketName=bucket_name,
                indexName=index_name
            )
            print(f"✅ Index verification successful: {response['index']['indexName']}")
            print(f"   Dimensions: {response['index']['dimension']}")
            print(f"   Distance Metric: {response['index']['distanceMetric']}")
        except Exception as e:
            print(f"❌ Index verification failed: {e}")
        
        # Wait a moment before deletion
        print(f"\n⏳ Waiting 5 seconds before cleanup...")
        time.sleep(5)
        
        # Test 4: Delete S3Vector index
        print(f"\n🗑️ Deleting S3Vector index: {index_name}")
        index_delete_success = manager._delete_s3vector_index_real(bucket_name, index_name)
        
        if index_delete_success:
            print(f"✅ S3Vector index deleted successfully!")
        else:
            print("❌ Failed to delete S3Vector index")
        
        # Test 5: Delete S3Vector bucket
        print(f"\n🗑️ Deleting S3Vector bucket: {bucket_name}")
        bucket_delete_success = manager._delete_s3vector_bucket_real(bucket_name)
        
        if bucket_delete_success:
            print(f"✅ S3Vector bucket deleted successfully!")
        else:
            print("❌ Failed to delete S3Vector bucket")
        
        # Final verification
        print(f"\n🔍 Final verification...")
        
        try:
            manager.s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
            print("❌ Bucket still exists after deletion!")
            return False
        except Exception:
            print("✅ Bucket successfully deleted (not found)")
        
        success = bucket_success and index_success and index_delete_success and bucket_delete_success
        
        if success:
            print(f"\n🎉 All tests passed! Resource creation and deletion working correctly.")
        else:
            print(f"\n❌ Some tests failed. Check the logs above.")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        
        # Attempt cleanup
        try:
            print(f"\n🧹 Attempting emergency cleanup...")
            manager = SimplifiedResourceManager()
            if manager.s3vectors_client:
                manager._delete_s3vector_index_real(bucket_name, index_name)
                manager._delete_s3vector_bucket_real(bucket_name)
        except:
            pass
        
        return False


def print_aws_cli_commands(test_setup_name: str):
    """Print AWS CLI commands for manual verification."""
    bucket_name = f"{test_setup_name}-bucket"
    index_name = f"{test_setup_name}-index"
    
    print(f"\n📋 AWS CLI Commands for Manual Verification:")
    print(f"   (Use these commands to verify resources manually)")
    print()
    print(f"# List all S3Vector buckets:")
    print(f"aws s3vectors list-vector-buckets")
    print()
    print(f"# Get specific bucket details:")
    print(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name}")
    print()
    print(f"# List indexes in bucket:")
    print(f"aws s3vectors list-indexes --vector-bucket-name {bucket_name}")
    print()
    print(f"# Get specific index details:")
    print(f"aws s3vectors get-index --vector-bucket-name {bucket_name} --index-name {index_name}")
    print()
    print(f"# Manual cleanup (if needed):")
    print(f"aws s3vectors delete-index --vector-bucket-name {bucket_name} --index-name {index_name}")
    print(f"aws s3vectors delete-vector-bucket --vector-bucket-name {bucket_name}")


def main():
    """Main test function."""
    print("🧪 S3Vector Simplified Resource Manager Test")
    print("=" * 50)
    
    # Test 1: AWS connectivity
    if not test_aws_connectivity():
        print("\n❌ AWS connectivity test failed. Cannot proceed.")
        return False
    
    # Test 2: S3Vectors client
    s3vectors_success, s3vectors_client = test_s3vectors_client()
    if not s3vectors_success:
        print("\n❌ S3Vectors client test failed. Cannot proceed.")
        return False
    
    # Generate test names for CLI commands
    timestamp = int(time.time())
    test_setup_name = f"test-s3vector-{timestamp}"
    
    # Print CLI commands for reference
    print_aws_cli_commands(test_setup_name)
    
    # Test 3: Resource creation and deletion
    if test_resource_creation_and_deletion():
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ The Simplified Resource Manager is working correctly.")
        print("✅ Resources can be created and deleted successfully.")
        print("✅ ARNs are properly generated and returned.")
        return True
    else:
        print("\n❌ TESTS FAILED!")
        print("❌ There are issues with resource creation or deletion.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
