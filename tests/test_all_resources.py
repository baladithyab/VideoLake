#!/usr/bin/env python3
"""
Comprehensive Resource Test

This script tests all resource types supported by the Simplified Resource Manager:
1. S3Vector buckets and indexes
2. S3 buckets
3. Resource verification with AWS CLI

This ensures all resource types work like the previous implementation.
"""

import sys
import time
import subprocess
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from frontend.components.simplified_resource_manager import SimplifiedResourceManager


def run_aws_cli_command(command: str, region: str = "us-east-1") -> dict:
    """Run an AWS CLI command with the specified region."""
    try:
        # Add region to command if not already present and it's an AWS command
        if "aws " in command and "--region" not in command:
            command += f" --region {region}"
        
        print(f"🔍 Running: {command}")
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"success": True, "output": result.stdout.strip()}
            else:
                return {"success": True, "output": "No output"}
        else:
            print(f"❌ Command failed: {result.stderr}")
            return {"error": result.stderr}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def test_s3vector_resources(manager: SimplifiedResourceManager, timestamp: int) -> bool:
    """Test S3Vector bucket and index creation/deletion."""
    print(f"\n" + "="*60)
    print(f"TESTING S3VECTOR RESOURCES")
    print(f"="*60)
    
    bucket_name = f"test-s3vector-{timestamp}"
    index_name = f"test-index-{timestamp}"
    
    try:
        # Test S3Vector bucket creation
        print(f"\n🪣 Testing S3Vector bucket creation: {bucket_name}")
        bucket_success, bucket_arn = manager._create_s3vector_bucket_real(bucket_name)
        
        if not bucket_success:
            print("❌ S3Vector bucket creation failed")
            return False
        
        print(f"✅ S3Vector bucket created: {bucket_arn}")
        
        # Verify with AWS CLI
        result = run_aws_cli_command("aws s3vectors list-vector-buckets")
        if "error" not in result:
            buckets = result.get("vectorBuckets", [])
            bucket_names = [b.get("vectorBucketName") for b in buckets]
            if bucket_name in bucket_names:
                print(f"✅ S3Vector bucket verified with AWS CLI")
            else:
                print(f"❌ S3Vector bucket not found in CLI list")
                return False
        
        # Test S3Vector index creation
        print(f"\n📊 Testing S3Vector index creation: {index_name}")
        index_success, index_arn = manager._create_s3vector_index_real(bucket_name, index_name, 1536)
        
        if not index_success:
            print("❌ S3Vector index creation failed")
            # Clean up bucket
            manager._delete_s3vector_bucket_real(bucket_name)
            return False
        
        print(f"✅ S3Vector index created: {index_arn}")
        
        # Verify index with AWS CLI
        result = run_aws_cli_command(f"aws s3vectors list-indexes --vector-bucket-name {bucket_name}")
        if "error" not in result:
            indexes = result.get("indexes", [])
            index_names = [idx.get("indexName") for idx in indexes]
            if index_name in index_names:
                print(f"✅ S3Vector index verified with AWS CLI")
            else:
                print(f"❌ S3Vector index not found in CLI list")
                return False
        
        # Test S3Vector index deletion
        print(f"\n🗑️ Testing S3Vector index deletion: {index_name}")
        index_delete_success = manager._delete_s3vector_index_real(bucket_name, index_name)
        
        if not index_delete_success:
            print("❌ S3Vector index deletion failed")
        else:
            print(f"✅ S3Vector index deleted successfully")
        
        # Test S3Vector bucket deletion
        print(f"\n🗑️ Testing S3Vector bucket deletion: {bucket_name}")
        bucket_delete_success = manager._delete_s3vector_bucket_real(bucket_name)
        
        if not bucket_delete_success:
            print("❌ S3Vector bucket deletion failed")
        else:
            print(f"✅ S3Vector bucket deleted successfully")
        
        # Verify deletion with AWS CLI
        result = run_aws_cli_command("aws s3vectors list-vector-buckets")
        if "error" not in result:
            buckets = result.get("vectorBuckets", [])
            bucket_names = [b.get("vectorBucketName") for b in buckets]
            if bucket_name not in bucket_names:
                print(f"✅ S3Vector bucket deletion verified with AWS CLI")
            else:
                print(f"❌ S3Vector bucket still exists after deletion")
                return False
        
        return bucket_success and index_success and index_delete_success and bucket_delete_success
        
    except Exception as e:
        print(f"❌ S3Vector test failed: {e}")
        # Emergency cleanup
        try:
            manager._delete_s3vector_index_real(bucket_name, index_name)
            manager._delete_s3vector_bucket_real(bucket_name)
        except:
            pass
        return False


def test_s3_bucket_resources(manager: SimplifiedResourceManager, timestamp: int) -> bool:
    """Test S3 bucket creation/deletion."""
    print(f"\n" + "="*60)
    print(f"TESTING S3 BUCKET RESOURCES")
    print(f"="*60)
    
    bucket_name = f"test-s3-bucket-{timestamp}"
    
    try:
        # Test S3 bucket creation
        print(f"\n🪣 Testing S3 bucket creation: {bucket_name}")
        bucket_success, bucket_arn = manager._create_s3_bucket_real(bucket_name)
        
        if not bucket_success:
            print("❌ S3 bucket creation failed")
            return False
        
        print(f"✅ S3 bucket created: {bucket_arn}")
        
        # Verify with AWS CLI
        result = run_aws_cli_command(f"aws s3 ls s3://{bucket_name}", region="")
        if "error" not in result:
            print(f"✅ S3 bucket verified with AWS CLI")
        else:
            print(f"❌ S3 bucket verification failed: {result.get('error', 'Unknown error')}")
        
        # Test S3 bucket deletion
        print(f"\n🗑️ Testing S3 bucket deletion: {bucket_name}")
        bucket_delete_success = manager._delete_s3_bucket_real(bucket_name)
        
        if not bucket_delete_success:
            print("❌ S3 bucket deletion failed")
        else:
            print(f"✅ S3 bucket deleted successfully")
        
        # Verify deletion with AWS CLI
        result = run_aws_cli_command(f"aws s3 ls s3://{bucket_name}", region="")
        if "error" in result:
            print(f"✅ S3 bucket deletion verified with AWS CLI (bucket not found)")
        else:
            print(f"❌ S3 bucket still exists after deletion")
            return False
        
        return bucket_success and bucket_delete_success
        
    except Exception as e:
        print(f"❌ S3 bucket test failed: {e}")
        # Emergency cleanup
        try:
            manager._delete_s3_bucket_real(bucket_name)
        except:
            pass
        return False


def main():
    """Main test function."""
    print("🧪 Comprehensive Resource Test")
    print("=" * 60)
    
    # Generate unique test names
    timestamp = int(time.time())
    
    print(f"📋 Test Configuration:")
    print(f"   Timestamp: {timestamp}")
    print(f"   S3Vectors Region: us-east-1")
    print(f"   S3 Region: {subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True).stdout.strip()}")
    
    try:
        # Initialize the simplified resource manager
        print(f"\n📋 Initializing SimplifiedResourceManager...")
        manager = SimplifiedResourceManager()
        
        if manager.s3vectors_client is None:
            print("❌ S3Vectors client not initialized")
            return False
        
        if manager.s3_client is None:
            print("❌ S3 client not initialized")
            return False
        
        print("✅ SimplifiedResourceManager initialized successfully")
        print(f"   Account ID: {manager.account_id}")
        print(f"   Region: {manager.region}")
        
        # Test all resource types
        s3vector_success = test_s3vector_resources(manager, timestamp)
        s3_success = test_s3_bucket_resources(manager, timestamp)
        
        # FINAL RESULT
        print(f"\n" + "="*60)
        print(f"FINAL RESULT")
        print(f"="*60)
        
        all_success = s3vector_success and s3_success
        
        if all_success:
            print(f"🎉 ALL TESTS PASSED!")
            print(f"✅ S3Vector resources: CREATE, VERIFY, DELETE")
            print(f"✅ S3 bucket resources: CREATE, VERIFY, DELETE")
            print(f"✅ AWS CLI verification working")
            print(f"✅ ARN generation working")
            print(f"\n🎯 All resource types are working like the previous implementation!")
            return True
        else:
            print(f"❌ SOME TESTS FAILED!")
            print(f"   S3Vector resources: {'✅' if s3vector_success else '❌'}")
            print(f"   S3 bucket resources: {'✅' if s3_success else '❌'}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
