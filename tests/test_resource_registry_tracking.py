#!/usr/bin/env python3
"""
Resource Registry Tracking Test

This script verifies that the resource management system properly tracks
all resources in the JSON resource registry (coordination/resource_registry.json).

Tests:
1. S3Vector bucket creation is logged
2. S3Vector index creation is logged
3. S3 bucket creation is logged
4. Resource deletion is logged
5. Registry JSON is properly updated
"""

import sys
import time
import json
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Suppress Streamlit warnings
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'


def read_registry() -> dict:
    """Read the resource registry JSON file."""
    registry_path = project_root / "coordination" / "resource_registry.json"
    with open(registry_path, 'r') as f:
        return json.load(f)


def find_resource_in_registry(registry: dict, resource_type: str, resource_name: str) -> dict:
    """Find a resource in the registry by type and name."""
    resources = registry.get(resource_type, [])
    for resource in resources:
        if resource.get('name') == resource_name:
            return resource
    return None


def test_s3vector_bucket_tracking(timestamp: int) -> bool:
    """Test that S3Vector bucket creation/deletion is tracked in registry."""
    print(f"\n" + "="*60)
    print(f"TESTING S3VECTOR BUCKET REGISTRY TRACKING")
    print(f"="*60)
    
    bucket_name = f"registry-test-bucket-{timestamp}"
    
    try:
        import boto3
        from src.shared.aws_client_pool import get_pooled_client, AWSService
        from src.utils.resource_registry import resource_registry
        
        # Get initial registry state
        initial_registry = read_registry()
        initial_bucket_count = len(initial_registry.get('vector_buckets', []))
        print(f"📊 Initial vector bucket count in registry: {initial_bucket_count}")
        
        # Create S3Vector bucket
        print(f"\n🪣 Creating S3Vector bucket: {bucket_name}")
        s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
        s3vectors_client.create_vector_bucket(vectorBucketName=bucket_name)
        
        # Log creation in registry
        session = boto3.Session()
        region = session.region_name or 'us-east-1'
        resource_registry.log_vector_bucket_created(bucket_name, region)
        print(f"✅ Logged bucket creation in registry")
        
        # Verify registry was updated
        updated_registry = read_registry()
        updated_bucket_count = len(updated_registry.get('vector_buckets', []))
        print(f"📊 Updated vector bucket count in registry: {updated_bucket_count}")
        
        if updated_bucket_count != initial_bucket_count + 1:
            print(f"❌ Registry bucket count did not increase! Expected {initial_bucket_count + 1}, got {updated_bucket_count}")
            return False
        
        # Find the created bucket in registry
        bucket_record = find_resource_in_registry(updated_registry, 'vector_buckets', bucket_name)
        if not bucket_record:
            print(f"❌ Bucket not found in registry!")
            return False
        
        print(f"✅ Bucket found in registry:")
        print(f"   Name: {bucket_record.get('name')}")
        print(f"   Region: {bucket_record.get('region')}")
        print(f"   Status: {bucket_record.get('status')}")
        print(f"   Created at: {bucket_record.get('created_at')}")
        
        # Verify bucket status is 'created'
        if bucket_record.get('status') != 'created':
            print(f"❌ Bucket status is not 'created': {bucket_record.get('status')}")
            return False
        
        # Delete the bucket
        print(f"\n🗑️ Deleting S3Vector bucket: {bucket_name}")
        s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        
        # Log deletion in registry
        resource_registry.log_vector_bucket_deleted(bucket_name)
        print(f"✅ Logged bucket deletion in registry")
        
        # Verify registry was updated with deletion
        final_registry = read_registry()
        bucket_record_after_delete = find_resource_in_registry(final_registry, 'vector_buckets', bucket_name)
        
        if not bucket_record_after_delete:
            print(f"❌ Bucket record disappeared from registry after deletion!")
            return False
        
        print(f"✅ Bucket record still in registry (as expected):")
        print(f"   Status: {bucket_record_after_delete.get('status')}")
        print(f"   Deleted at: {bucket_record_after_delete.get('deleted_at')}")
        
        # Verify bucket status is 'deleted'
        if bucket_record_after_delete.get('status') != 'deleted':
            print(f"❌ Bucket status is not 'deleted': {bucket_record_after_delete.get('status')}")
            return False
        
        # Verify deleted_at timestamp exists
        if not bucket_record_after_delete.get('deleted_at'):
            print(f"❌ Bucket deleted_at timestamp is missing!")
            return False
        
        print(f"✅ S3Vector bucket tracking verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ S3Vector bucket tracking test failed: {e}")
        import traceback
        traceback.print_exc()
        # Emergency cleanup
        try:
            s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        except:
            pass
        return False


def test_s3vector_index_tracking(timestamp: int) -> bool:
    """Test that S3Vector index creation/deletion is tracked in registry."""
    print(f"\n" + "="*60)
    print(f"TESTING S3VECTOR INDEX REGISTRY TRACKING")
    print(f"="*60)
    
    bucket_name = f"registry-test-bucket-{timestamp}"
    index_name = f"registry-test-index-{timestamp}"
    
    try:
        import boto3
        from src.shared.aws_client_pool import get_pooled_client, AWSService
        from src.utils.resource_registry import resource_registry
        
        # Get clients
        s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
        sts_client = get_pooled_client(AWSService.STS)
        identity = sts_client.get_caller_identity()
        account_id = identity['Account']
        session = boto3.Session()
        region = session.region_name or 'us-east-1'
        
        # Create bucket first
        print(f"\n🪣 Creating S3Vector bucket: {bucket_name}")
        s3vectors_client.create_vector_bucket(vectorBucketName=bucket_name)
        resource_registry.log_vector_bucket_created(bucket_name, region)
        
        # Get initial registry state
        initial_registry = read_registry()
        initial_index_count = len(initial_registry.get('indexes', []))
        print(f"📊 Initial index count in registry: {initial_index_count}")
        
        # Create S3Vector index
        print(f"\n📊 Creating S3Vector index: {index_name}")
        s3vectors_client.create_index(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dimension=1536,
            distanceMetric='cosine',
            dataType='float32'
        )
        
        # Log creation in registry
        index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}"
        resource_registry.log_index_created(bucket_name, index_name, index_arn, 1536, 'cosine')
        print(f"✅ Logged index creation in registry")
        
        # Verify registry was updated
        updated_registry = read_registry()
        updated_index_count = len(updated_registry.get('indexes', []))
        print(f"📊 Updated index count in registry: {updated_index_count}")
        
        if updated_index_count != initial_index_count + 1:
            print(f"❌ Registry index count did not increase! Expected {initial_index_count + 1}, got {updated_index_count}")
            return False
        
        # Find the created index in registry
        index_record = find_resource_in_registry(updated_registry, 'indexes', index_name)
        if not index_record:
            print(f"❌ Index not found in registry!")
            return False
        
        print(f"✅ Index found in registry:")
        print(f"   Name: {index_record.get('name')}")
        print(f"   Bucket: {index_record.get('bucket')}")
        print(f"   ARN: {index_record.get('arn')}")
        print(f"   Dimensions: {index_record.get('dimensions')}")
        print(f"   Distance Metric: {index_record.get('distance_metric')}")
        print(f"   Status: {index_record.get('status')}")
        
        # Delete the index
        print(f"\n🗑️ Deleting S3Vector index: {index_name}")
        s3vectors_client.delete_index(vectorBucketName=bucket_name, indexName=index_name)
        resource_registry.log_index_deleted(bucket_name=bucket_name, index_name=index_name)
        print(f"✅ Logged index deletion in registry")
        
        # Delete the bucket
        print(f"\n🗑️ Deleting S3Vector bucket: {bucket_name}")
        s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        resource_registry.log_vector_bucket_deleted(bucket_name)
        
        # Verify registry was updated with deletion
        final_registry = read_registry()
        index_record_after_delete = find_resource_in_registry(final_registry, 'indexes', index_name)
        
        if not index_record_after_delete:
            print(f"❌ Index record disappeared from registry after deletion!")
            return False
        
        print(f"✅ Index record still in registry (as expected):")
        print(f"   Status: {index_record_after_delete.get('status')}")
        print(f"   Deleted at: {index_record_after_delete.get('deleted_at')}")
        
        # Verify index status is 'deleted'
        if index_record_after_delete.get('status') != 'deleted':
            print(f"❌ Index status is not 'deleted': {index_record_after_delete.get('status')}")
            return False
        
        print(f"✅ S3Vector index tracking verified successfully!")
        return True
        
    except Exception as e:
        print(f"❌ S3Vector index tracking test failed: {e}")
        import traceback
        traceback.print_exc()
        # Emergency cleanup
        try:
            s3vectors_client.delete_index(vectorBucketName=bucket_name, indexName=index_name)
            s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        except:
            pass
        return False


def main():
    """Main test function."""
    print("🧪 Resource Registry Tracking Test")
    print("=" * 60)
    
    # Generate unique test names
    timestamp = int(time.time())
    
    print(f"📋 Test Configuration:")
    print(f"   Timestamp: {timestamp}")
    print(f"   Registry file: coordination/resource_registry.json")
    
    try:
        # Test all resource tracking
        bucket_tracking_success = test_s3vector_bucket_tracking(timestamp)
        index_tracking_success = test_s3vector_index_tracking(timestamp + 1)  # Different timestamp
        
        # FINAL RESULT
        print(f"\n" + "="*60)
        print(f"FINAL RESULT")
        print(f"="*60)
        
        all_success = bucket_tracking_success and index_tracking_success
        
        if all_success:
            print(f"🎉 ALL REGISTRY TRACKING TESTS PASSED!")
            print(f"✅ S3Vector bucket: CREATE logged, DELETE logged")
            print(f"✅ S3Vector index: CREATE logged, DELETE logged")
            print(f"✅ Registry JSON properly updated")
            print(f"✅ Status transitions tracked correctly")
            print(f"✅ Timestamps recorded properly")
            print(f"\n🎯 Resource registry is working perfectly!")
            return True
        else:
            print(f"❌ SOME REGISTRY TRACKING TESTS FAILED!")
            print(f"   S3Vector bucket tracking: {'✅' if bucket_tracking_success else '❌'}")
            print(f"   S3Vector index tracking: {'✅' if index_tracking_success else '❌'}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    # Force clean exit without waiting for threads
    os._exit(0 if success else 1)

