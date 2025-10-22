#!/usr/bin/env python3
"""
Final Comprehensive Resource Test

This script demonstrates the complete functionality of the Simplified Resource Manager:
1. Create S3Vector bucket and index
2. Verify with AWS CLI (using correct region)
3. Delete resources
4. Verify deletion with AWS CLI

This test accounts for the region differences between the S3Vectors client (us-east-1)
and the default AWS CLI configuration.
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
        # Add region to command if not already present
        if "--region" not in command:
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
                return json.loads(result.stdout)
            else:
                return {"success": True, "output": "No output"}
        else:
            print(f"❌ Command failed: {result.stderr}")
            return {"error": result.stderr}
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def main():
    """Main test function."""
    print("🧪 Final Comprehensive Resource Test")
    print("=" * 60)
    
    # Generate unique test names
    timestamp = int(time.time())
    test_setup_name = f"final-test-{timestamp}"
    bucket_name = f"{test_setup_name}-bucket"
    index_name = f"{test_setup_name}-index"
    
    print(f"📋 Test Configuration:")
    print(f"   Setup name: {test_setup_name}")
    print(f"   Bucket name: {bucket_name}")
    print(f"   Index name: {index_name}")
    print(f"   Region: us-east-1 (S3Vectors client region)")
    
    try:
        # Initialize the simplified resource manager
        print(f"\n📋 Initializing SimplifiedResourceManager...")
        manager = SimplifiedResourceManager()
        
        if manager.s3vectors_client is None:
            print("❌ S3Vectors client not initialized")
            return False
        
        print("✅ SimplifiedResourceManager initialized successfully")
        print(f"   Account ID: {manager.account_id}")
        print(f"   Region: {manager.region}")
        
        # STEP 1: CREATE RESOURCES
        print(f"\n" + "="*60)
        print(f"STEP 1: CREATING RESOURCES")
        print(f"="*60)
        
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
        
        # STEP 2: VERIFY WITH AWS CLI
        print(f"\n" + "="*60)
        print(f"STEP 2: VERIFYING WITH AWS CLI")
        print(f"="*60)
        
        # List all buckets
        print(f"\n🔍 Listing all S3Vector buckets...")
        result = run_aws_cli_command("aws s3vectors list-vector-buckets")
        if "error" in result:
            print(f"❌ Failed to list buckets: {result['error']}")
            return False
        
        buckets = result.get("vectorBuckets", [])
        bucket_names = [b.get("vectorBucketName") for b in buckets]
        print(f"✅ Found {len(buckets)} bucket(s): {bucket_names}")
        
        # Verify our bucket exists
        if bucket_name not in bucket_names:
            print(f"❌ Our bucket not found in list!")
            return False
        
        print(f"✅ Our bucket found in list: {bucket_name}")
        
        # Get specific bucket details
        print(f"\n🔍 Getting bucket details...")
        result = run_aws_cli_command(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name}")
        if "error" in result:
            print(f"❌ Failed to get bucket details: {result['error']}")
            return False
        
        bucket_info = result.get("vectorBucket", {})
        print(f"✅ Bucket details retrieved:")
        print(f"   Name: {bucket_info.get('vectorBucketName')}")
        print(f"   ARN: {bucket_info.get('vectorBucketArn')}")
        print(f"   Created: {bucket_info.get('creationTime')}")
        
        # List indexes in bucket
        print(f"\n🔍 Listing indexes in bucket...")
        result = run_aws_cli_command(f"aws s3vectors list-indexes --vector-bucket-name {bucket_name}")
        if "error" in result:
            print(f"❌ Failed to list indexes: {result['error']}")
            return False
        
        indexes = result.get("indexes", [])
        index_names = [idx.get("indexName") for idx in indexes]
        print(f"✅ Found {len(indexes)} index(es): {index_names}")
        
        # Verify our index exists
        if index_name not in index_names:
            print(f"❌ Our index not found in list!")
            return False
        
        print(f"✅ Our index found in list: {index_name}")
        
        # Get specific index details
        print(f"\n🔍 Getting index details...")
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
        print(f"   Created: {index_info.get('creationTime')}")
        
        print(f"\n✅ All resources verified successfully with AWS CLI!")
        
        # Wait before deletion
        print(f"\n⏳ Waiting 3 seconds before cleanup...")
        time.sleep(3)
        
        # STEP 3: DELETE RESOURCES
        print(f"\n" + "="*60)
        print(f"STEP 3: DELETING RESOURCES")
        print(f"="*60)
        
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
        
        # STEP 4: VERIFY DELETION WITH AWS CLI
        print(f"\n" + "="*60)
        print(f"STEP 4: VERIFYING DELETION WITH AWS CLI")
        print(f"="*60)
        
        # List all buckets to confirm deletion
        print(f"\n🔍 Listing all buckets after deletion...")
        result = run_aws_cli_command("aws s3vectors list-vector-buckets")
        if "error" not in result:
            buckets = result.get("vectorBuckets", [])
            bucket_names = [b.get("vectorBucketName") for b in buckets]
            print(f"✅ Current bucket count: {len(buckets)}")
            
            if bucket_name in bucket_names:
                print(f"❌ Our bucket still exists after deletion!")
                return False
            else:
                print(f"✅ Our bucket successfully deleted (not in list)")
            
            if buckets:
                print("   Remaining buckets:")
                for bucket in buckets:
                    print(f"   - {bucket.get('vectorBucketName')}")
            else:
                print("   No buckets exist")
        
        # Try to get the deleted bucket (should fail)
        print(f"\n🔍 Attempting to get deleted bucket (should fail)...")
        result = run_aws_cli_command(f"aws s3vectors get-vector-bucket --vector-bucket-name {bucket_name}")
        if "error" in result:
            print(f"✅ Bucket correctly does not exist (get-bucket failed as expected)")
        else:
            print(f"❌ Bucket still exists (get-bucket succeeded unexpectedly)")
            return False
        
        # FINAL RESULT
        print(f"\n" + "="*60)
        print(f"FINAL RESULT")
        print(f"="*60)
        
        all_success = (bucket_success and index_success and 
                      index_delete_success and bucket_delete_success)
        
        if all_success:
            print(f"🎉 COMPLETE SUCCESS!")
            print(f"✅ S3Vector bucket created and verified")
            print(f"✅ S3Vector index created and verified")
            print(f"✅ Resources verified with AWS CLI")
            print(f"✅ S3Vector index deleted and verified")
            print(f"✅ S3Vector bucket deleted and verified")
            print(f"✅ Deletion verified with AWS CLI")
            print(f"✅ ARNs properly generated and returned")
            print(f"\n🎯 The Simplified Resource Manager is working perfectly!")
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
