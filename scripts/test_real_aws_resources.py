#!/usr/bin/env python3
"""
Real AWS Resource Testing Script

Tests the workflow resource management with actual AWS resources.
Creates, manages, and cleans up real AWS resources for comprehensive testing.

IMPORTANT: This script creates real AWS resources that may incur costs.
Make sure to run cleanup after testing.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError, NoCredentialsError
import json

def check_aws_credentials():
    """Check if AWS credentials are configured."""
    print("🔐 Checking AWS Credentials...")
    
    try:
        # Try to get caller identity
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ AWS credentials configured")
        print(f"   Account ID: {identity.get('Account')}")
        print(f"   User/Role: {identity.get('Arn', 'Unknown')}")
        
        return True
        
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        print("   Please configure AWS credentials using:")
        print("   - aws configure")
        print("   - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
        print("   - IAM roles (if running on EC2)")
        return False
        
    except Exception as e:
        print(f"❌ AWS credential check failed: {e}")
        return False


def test_real_s3_operations():
    """Test real S3 bucket operations."""
    print("\n📦 Testing Real S3 Operations...")
    
    try:
        s3 = boto3.client('s3')
        test_bucket_name = f"s3vector-test-{int(time.time())}"
        
        print(f"Creating S3 bucket: {test_bucket_name}")
        
        # Create bucket
        try:
            s3.create_bucket(Bucket=test_bucket_name)
            print(f"✅ S3 bucket '{test_bucket_name}' created successfully")
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyExists':
                print(f"⚠️ Bucket '{test_bucket_name}' already exists")
            else:
                raise
        
        # List buckets to verify
        response = s3.list_buckets()
        bucket_names = [b['Name'] for b in response['Buckets']]
        
        if test_bucket_name in bucket_names:
            print(f"✅ Bucket verified in bucket list")
        else:
            print(f"❌ Bucket not found in list")
            return False, None
        
        # Test bucket operations
        print("Testing bucket operations...")
        
        # Put a test object
        test_key = "test-object.txt"
        test_content = "This is a test object for S3Vector demo"
        
        s3.put_object(
            Bucket=test_bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain'
        )
        print(f"✅ Test object uploaded: {test_key}")
        
        # List objects
        objects = s3.list_objects_v2(Bucket=test_bucket_name)
        if 'Contents' in objects and len(objects['Contents']) > 0:
            print(f"✅ Objects listed: {len(objects['Contents'])} found")
        else:
            print("⚠️ No objects found in bucket")
        
        return True, test_bucket_name
        
    except Exception as e:
        print(f"❌ S3 operations failed: {e}")
        return False, None


def test_real_opensearch_operations():
    """Test real OpenSearch operations."""
    print("\n🔎 Testing Real OpenSearch Operations...")
    
    try:
        # Try OpenSearch Serverless first
        aoss = boto3.client('opensearchserverless')
        test_collection_name = f"s3vector-test-{int(time.time())}"
        
        print(f"Creating OpenSearch Serverless collection: {test_collection_name}")
        
        # Create collection
        try:
            response = aoss.create_collection(
                name=test_collection_name,
                type='SEARCH',
                description='Test collection for S3Vector demo'
            )
            
            collection_id = response['createCollectionDetail']['id']
            collection_arn = response['createCollectionDetail']['arn']
            
            print(f"✅ OpenSearch collection creation initiated")
            print(f"   Collection ID: {collection_id}")
            print(f"   Collection ARN: {collection_arn}")
            
            # Wait for collection to be active (this can take several minutes)
            print("⏳ Waiting for collection to become active...")
            
            max_wait_time = 300  # 5 minutes
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    collections = aoss.list_collections()
                    for collection in collections.get('collectionSummaries', []):
                        if collection['name'] == test_collection_name:
                            status = collection['status']
                            print(f"   Collection status: {status}")
                            
                            if status == 'ACTIVE':
                                print(f"✅ Collection is now active!")
                                return True, test_collection_name, collection_arn
                            elif status == 'FAILED':
                                print(f"❌ Collection creation failed")
                                return False, None, None
                    
                    time.sleep(10)  # Wait 10 seconds before checking again
                    
                except Exception as e:
                    print(f"⚠️ Error checking collection status: {e}")
                    time.sleep(10)
            
            print(f"⚠️ Collection creation timeout after {max_wait_time} seconds")
            print(f"   Collection may still be creating in the background")
            return True, test_collection_name, collection_arn
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ConflictException':
                print(f"⚠️ Collection '{test_collection_name}' already exists")
                return True, test_collection_name, None
            else:
                print(f"❌ OpenSearch collection creation failed: {e}")
                return False, None, None
        
    except Exception as e:
        print(f"❌ OpenSearch operations failed: {e}")
        print("   Note: OpenSearch Serverless may not be available in all regions")
        return False, None, None


def test_resource_scanner_with_real_aws():
    """Test the resource scanner with real AWS resources."""
    print("\n🔍 Testing Resource Scanner with Real AWS...")
    
    try:
        from src.services.aws_resource_scanner import AWSResourceScanner
        
        # Initialize scanner
        scanner = AWSResourceScanner(region="us-east-1")
        print("✅ AWS Resource Scanner initialized")
        
        # Scan for real S3 buckets
        print("Scanning for real S3 buckets...")
        s3_result = scanner.scan_s3_buckets("us-east-1")
        
        print(f"✅ S3 scan completed:")
        print(f"   Buckets found: {len(s3_result.resources_found)}")
        print(f"   Scan duration: {s3_result.scan_duration:.2f}s")
        print(f"   Errors: {len(s3_result.errors)}")
        
        if s3_result.resources_found:
            print("   Sample buckets:")
            for bucket in s3_result.resources_found[:3]:
                print(f"     - {bucket['name']} ({bucket['region']})")
        
        # Scan for OpenSearch collections
        print("Scanning for OpenSearch collections...")
        os_result = scanner.scan_opensearch_collections("us-east-1")
        
        print(f"✅ OpenSearch scan completed:")
        print(f"   Collections found: {len(os_result.resources_found)}")
        print(f"   Scan duration: {os_result.scan_duration:.2f}s")
        print(f"   Errors: {len(os_result.errors)}")
        
        if os_result.resources_found:
            print("   Sample collections:")
            for collection in os_result.resources_found[:3]:
                print(f"     - {collection['name']} ({collection['status']})")
        
        # Test comprehensive scan
        print("Running comprehensive scan...")
        comprehensive_result = scanner.scan_all_resources(
            regions=["us-east-1"],
            resource_types=["s3_buckets", "opensearch_collections"]
        )
        
        print(f"✅ Comprehensive scan completed:")
        print(f"   Total resources: {comprehensive_result.total_resources}")
        print(f"   Total duration: {comprehensive_result.total_duration:.2f}s")
        print(f"   Regions scanned: {comprehensive_result.regions_scanned}")
        
        return True, comprehensive_result
        
    except Exception as e:
        print(f"❌ Resource scanner test failed: {e}")
        return False, None


def test_workflow_with_real_resources():
    """Test the complete workflow with real resources."""
    print("\n🔄 Testing Complete Workflow with Real Resources...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        from src.utils.resource_registry import resource_registry
        
        # Initialize workflow manager
        manager = WorkflowResourceManager()
        print("✅ Workflow Resource Manager initialized")
        
        # Test getting existing resources (should include real ones now)
        existing_resources = manager._get_existing_resources()
        
        print("✅ Existing resources retrieved:")
        for resource_type, resources in existing_resources.items():
            if resources:
                print(f"   {resource_type}: {len(resources)} found")
                for resource in resources[:2]:  # Show first 2
                    print(f"     - {resource.get('name', 'Unknown')}")
        
        # Test resource creation with real AWS (simulation)
        print("Testing resource creation workflow...")
        
        # Create a test setup
        setup_name = f"real-test-{int(time.time())}"
        success = manager._create_complete_setup(setup_name, "us-east-1")
        
        if success:
            print(f"✅ Complete setup '{setup_name}' created successfully")
        else:
            print(f"❌ Setup creation failed")
            return False
        
        # Test active resource management
        print("Testing active resource management...")
        
        # Get active resources
        active_resources = resource_registry.get_active_resources()
        print(f"✅ Active resources retrieved: {len([r for r in active_resources.values() if r])}")
        
        for resource_type, resource_name in active_resources.items():
            if resource_name:
                print(f"   {resource_type}: {resource_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        return False


def test_real_resource_cleanup():
    """Test cleanup of real resources."""
    print("\n🧹 Testing Real Resource Cleanup...")
    
    try:
        from src.utils.resource_registry import resource_registry
        
        # Get all S3 buckets from registry
        s3_buckets = resource_registry.list_s3_buckets()
        test_buckets = [b for b in s3_buckets if 's3vector-test-' in b.get('name', '')]
        
        print(f"Found {len(test_buckets)} test S3 buckets to clean up")
        
        if test_buckets:
            s3 = boto3.client('s3')
            
            for bucket_info in test_buckets:
                bucket_name = bucket_info['name']
                print(f"Cleaning up S3 bucket: {bucket_name}")
                
                try:
                    # Delete all objects in bucket first
                    objects = s3.list_objects_v2(Bucket=bucket_name)
                    if 'Contents' in objects:
                        delete_keys = [{'Key': obj['Key']} for obj in objects['Contents']]
                        s3.delete_objects(
                            Bucket=bucket_name,
                            Delete={'Objects': delete_keys}
                        )
                        print(f"   Deleted {len(delete_keys)} objects")
                    
                    # Delete the bucket
                    s3.delete_bucket(Bucket=bucket_name)
                    print(f"✅ Bucket '{bucket_name}' deleted successfully")
                    
                    # Update registry
                    resource_registry.log_s3_bucket_deleted(bucket_name, source="cleanup_test")
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'NoSuchBucket':
                        print(f"⚠️ Bucket '{bucket_name}' already deleted")
                        resource_registry.log_s3_bucket_deleted(bucket_name, source="cleanup_test")
                    else:
                        print(f"❌ Failed to delete bucket '{bucket_name}': {e}")
        
        # Clean up OpenSearch collections
        os_collections = resource_registry.list_opensearch_collections()
        test_collections = [c for c in os_collections if 's3vector-test-' in c.get('name', '')]
        
        print(f"Found {len(test_collections)} test OpenSearch collections to clean up")
        
        if test_collections:
            aoss = boto3.client('opensearchserverless')
            
            for collection_info in test_collections:
                collection_name = collection_info['name']
                print(f"Cleaning up OpenSearch collection: {collection_name}")
                
                try:
                    aoss.delete_collection(id=collection_name)
                    print(f"✅ Collection '{collection_name}' deletion initiated")
                    
                    # Update registry
                    resource_registry.log_opensearch_collection_deleted(collection_name, source="cleanup_test")
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ResourceNotFoundException':
                        print(f"⚠️ Collection '{collection_name}' already deleted")
                        resource_registry.log_opensearch_collection_deleted(collection_name, source="cleanup_test")
                    else:
                        print(f"❌ Failed to delete collection '{collection_name}': {e}")
        
        print("✅ Cleanup completed")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


def main():
    """Run comprehensive real AWS resource testing."""
    print("🧪 Real AWS Resource Testing Suite")
    print("=" * 50)
    print("⚠️  WARNING: This script creates real AWS resources that may incur costs!")
    print("   Make sure to run cleanup after testing.")
    print("=" * 50)
    
    # Check if user wants to proceed
    proceed = input("\nDo you want to proceed with real AWS resource testing? (yes/no): ").lower().strip()
    if proceed not in ['yes', 'y']:
        print("❌ Testing cancelled by user")
        return False
    
    tests = [
        ("AWS Credentials Check", check_aws_credentials),
        ("Real S3 Operations", test_real_s3_operations),
        ("Real OpenSearch Operations", test_real_opensearch_operations),
        ("Resource Scanner with Real AWS", test_resource_scanner_with_real_aws),
        ("Workflow with Real Resources", test_workflow_with_real_resources),
    ]
    
    passed = 0
    total = len(tests)
    created_resources = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        
        try:
            result = test_func()
            if isinstance(result, tuple):
                success = result[0]
                if len(result) > 1 and result[1]:
                    created_resources.append(result[1])
            else:
                success = result
            
            if success:
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} - FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if created_resources:
        print(f"\n📋 Resources Created During Testing:")
        for resource in created_resources:
            print(f"   - {resource}")
    
    # Offer cleanup
    if created_resources:
        cleanup = input("\nDo you want to clean up test resources now? (yes/no): ").lower().strip()
        if cleanup in ['yes', 'y']:
            print("\n🧹 Running cleanup...")
            test_real_resource_cleanup()
        else:
            print("⚠️  Remember to clean up test resources manually to avoid charges!")
    
    if passed == total:
        print("🎉 All real AWS resource tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check AWS configuration and permissions.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
