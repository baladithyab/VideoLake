#!/usr/bin/env python3
"""
Complete Resource Lifecycle Test

This script demonstrates the full lifecycle of AWS resources using the
Simplified Resource Manager:
1. Create S3Vector bucket and index
2. Verify with AWS CLI
3. Delete resources
4. Verify deletion with AWS CLI
"""

import sys
import time
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from frontend.components.simplified_resource_manager import SimplifiedResourceManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def run_aws_cli_command(command: str) -> dict:
    """Run an AWS CLI command and return the JSON result."""
    try:
        print(f"🔍 Running: {command}")
        result = subprocess.run(
            command.split(),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                return json.loads(result.stdout)
            else:
                return {"success": True, "output": "No output"}
        else:
            print(f"❌ Command failed: {result.stderr}")
            return {"error": result.stderr}
            
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {command}")
        return {"error": "Command timed out"}
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print(f"Raw output: {result.stdout}")
        return {"error": f"JSON parse error: {e}"}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"error": str(e)}


def verify_bucket_exists(bucket_name: str) -> bool:
    """Verify that a bucket exists using AWS CLI."""
    print(f"\n🔍 Verifying bucket exists: {bucket_name}")
    
    # List all buckets
    result = run_aws_cli_command("aws s3vectors list-vector-buckets")
    if "error" in result:
        print(f"❌ Failed to list buckets: {result['error']}")
        return False
    
    buckets = result.get("vectorBuckets", [])
    bucket_names = [b.get("vectorBucketName") for b in buckets]
    
    if bucket_name in bucket_names:
        print(f"✅ Bucket found in list: {bucket_name}")
        
        # Get specific bucket details
        result = run_aws_cli_command(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name}")
        if "error" in result:
            print(f"❌ Failed to get bucket details: {result['error']}")
            return False
        
        bucket_info = result.get("vectorBucket", {})
        print(f"✅ Bucket details retrieved:")
        print(f"   Name: {bucket_info.get('vectorBucketName')}")
        print(f"   ARN: {bucket_info.get('vectorBucketArn')}")
        print(f"   Region: {bucket_info.get('region')}")
        print(f"   Created: {bucket_info.get('creationDate')}")
        
        return True
    else:
        print(f"❌ Bucket not found in list. Available buckets: {bucket_names}")
        return False


def verify_index_exists(bucket_name: str, index_name: str) -> bool:
    """Verify that an index exists using AWS CLI."""
    print(f"\n🔍 Verifying index exists: {bucket_name}/{index_name}")
    
    # List indexes in bucket
    result = run_aws_cli_command(f"aws s3vectors list-indexes --vector-bucket-name {bucket_name}")
    if "error" in result:
        print(f"❌ Failed to list indexes: {result['error']}")
        return False
    
    indexes = result.get("indexes", [])
    index_names = [idx.get("indexName") for idx in indexes]
    
    if index_name in index_names:
        print(f"✅ Index found in list: {index_name}")
        
        # Get specific index details
        result = run_aws_cli_command(f"aws s3vectors get-index --vector-bucket-name {bucket_name} --index-name {index_name}")
        if "error" in result:
            print(f"❌ Failed to get index details: {result['error']}")
            return False
        
        index_info = result.get("index", {})
        print(f"✅ Index details retrieved:")
        print(f"   Name: {index_info.get('indexName')}")
        print(f"   ARN: {index_info.get('indexArn')}")
        print(f"   Dimensions: {index_info.get('dimension')}")
        print(f"   Distance Metric: {index_info.get('distanceMetric')}")
        print(f"   Data Type: {index_info.get('dataType')}")
        print(f"   Created: {index_info.get('creationDate')}")
        
        return True
    else:
        print(f"❌ Index not found in list. Available indexes: {index_names}")
        return False


def verify_bucket_not_exists(bucket_name: str) -> bool:
    """Verify that a bucket does not exist using AWS CLI."""
    print(f"\n🔍 Verifying bucket does not exist: {bucket_name}")
    
    # Try to get the bucket (should fail)
    result = run_aws_cli_command(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name}")
    if "error" in result:
        print(f"✅ Bucket correctly does not exist: {bucket_name}")
        return True
    else:
        print(f"❌ Bucket still exists: {bucket_name}")
        return False


def main():
    """Main test function."""
    print("🧪 Complete Resource Lifecycle Test")
    print("=" * 50)
    
    # Generate unique test names
    timestamp = int(time.time())
    test_setup_name = f"lifecycle-test-{timestamp}"
    bucket_name = f"{test_setup_name}-bucket"
    index_name = f"{test_setup_name}-index"
    
    print(f"📋 Test Configuration:")
    print(f"   Setup name: {test_setup_name}")
    print(f"   Bucket name: {bucket_name}")
    print(f"   Index name: {index_name}")
    
    try:
        # Initialize the simplified resource manager
        print(f"\n📋 Initializing SimplifiedResourceManager...")
        manager = SimplifiedResourceManager()
        
        if manager.s3vectors_client is None:
            print("❌ S3Vectors client not initialized")
            return False
        
        print("✅ SimplifiedResourceManager initialized successfully")
        
        # PHASE 1: CREATE RESOURCES
        print(f"\n" + "="*50)
        print(f"PHASE 1: CREATING RESOURCES")
        print(f"="*50)
        
        # Create S3Vector bucket
        print(f"\n🪣 Creating S3Vector bucket: {bucket_name}")
        bucket_success, bucket_arn = manager._create_s3vector_bucket_real(bucket_name)
        
        if not bucket_success:
            print("❌ Failed to create S3Vector bucket")
            return False
        
        print(f"✅ S3Vector bucket created successfully!")
        print(f"   ARN: {bucket_arn}")
        
        # Create S3Vector index
        print(f"\n📊 Creating S3Vector index: {index_name}")
        index_success, index_arn = manager._create_s3vector_index_real(bucket_name, index_name, 1536)
        
        if not index_success:
            print("❌ Failed to create S3Vector index")
            # Clean up bucket
            manager._delete_s3vector_bucket_real(bucket_name)
            return False
        
        print(f"✅ S3Vector index created successfully!")
        print(f"   ARN: {index_arn}")
        
        # PHASE 2: VERIFY WITH AWS CLI
        print(f"\n" + "="*50)
        print(f"PHASE 2: VERIFYING WITH AWS CLI")
        print(f"="*50)
        
        # Verify bucket exists
        if not verify_bucket_exists(bucket_name):
            print("❌ Bucket verification failed")
            return False
        
        # Verify index exists
        if not verify_index_exists(bucket_name, index_name):
            print("❌ Index verification failed")
            return False
        
        print(f"\n✅ All resources verified successfully with AWS CLI!")
        
        # Wait before deletion
        print(f"\n⏳ Waiting 3 seconds before cleanup...")
        time.sleep(3)
        
        # PHASE 3: DELETE RESOURCES
        print(f"\n" + "="*50)
        print(f"PHASE 3: DELETING RESOURCES")
        print(f"="*50)
        
        # Delete S3Vector index
        print(f"\n🗑️ Deleting S3Vector index: {index_name}")
        index_delete_success = manager._delete_s3vector_index_real(bucket_name, index_name)
        
        if not index_delete_success:
            print("❌ Failed to delete S3Vector index")
        else:
            print(f"✅ S3Vector index deleted successfully!")
        
        # Delete S3Vector bucket
        print(f"\n🗑️ Deleting S3Vector bucket: {bucket_name}")
        bucket_delete_success = manager._delete_s3vector_bucket_real(bucket_name)
        
        if not bucket_delete_success:
            print("❌ Failed to delete S3Vector bucket")
        else:
            print(f"✅ S3Vector bucket deleted successfully!")
        
        # PHASE 4: VERIFY DELETION WITH AWS CLI
        print(f"\n" + "="*50)
        print(f"PHASE 4: VERIFYING DELETION WITH AWS CLI")
        print(f"="*50)
        
        # Verify bucket is gone
        if not verify_bucket_not_exists(bucket_name):
            print("❌ Bucket deletion verification failed")
            return False
        
        # List all buckets to confirm
        print(f"\n🔍 Final verification - listing all buckets:")
        result = run_aws_cli_command("aws s3vectors list-vector-buckets")
        if "error" not in result:
            buckets = result.get("vectorBuckets", [])
            print(f"✅ Current bucket count: {len(buckets)}")
            if buckets:
                print("   Existing buckets:")
                for bucket in buckets:
                    print(f"   - {bucket.get('vectorBucketName')}")
            else:
                print("   No buckets exist")
        
        # FINAL RESULT
        print(f"\n" + "="*50)
        print(f"FINAL RESULT")
        print(f"="*50)
        
        all_success = (bucket_success and index_success and 
                      index_delete_success and bucket_delete_success)
        
        if all_success:
            print(f"🎉 COMPLETE SUCCESS!")
            print(f"✅ Resources created successfully")
            print(f"✅ Resources verified with AWS CLI")
            print(f"✅ Resources deleted successfully")
            print(f"✅ Deletion verified with AWS CLI")
            print(f"✅ ARNs properly generated and returned")
            return True
        else:
            print(f"❌ PARTIAL FAILURE!")
            print(f"   Bucket creation: {'✅' if bucket_success else '❌'}")
            print(f"   Index creation: {'✅' if index_success else '❌'}")
            print(f"   Index deletion: {'✅' if index_delete_success else '❌'}")
            print(f"   Bucket deletion: {'✅' if bucket_delete_success else '❌'}")
            return False
        
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        
        # Emergency cleanup
        try:
            print(f"\n🧹 Attempting emergency cleanup...")
            manager = SimplifiedResourceManager()
            if manager.s3vectors_client:
                manager._delete_s3vector_index_real(bucket_name, index_name)
                manager._delete_s3vector_bucket_real(bucket_name)
                print("✅ Emergency cleanup completed")
        except:
            print("❌ Emergency cleanup failed")
        
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
