#!/usr/bin/env python3
"""
Add Bedrock permissions to existing S3 buckets.

This script applies the necessary bucket policy to allow Bedrock service
to read videos and write embedding results to S3 buckets.

Usage:
    python scripts/add_bedrock_permissions_to_existing_buckets.py
    python scripts/add_bedrock_permissions_to_existing_buckets.py --bucket-name s3vector-1761077785-media
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError
from src.utils.resource_registry import ResourceRegistry


def add_bedrock_bucket_policy(s3_client, sts_client, bucket_name: str, region: str) -> bool:
    """Add bucket policy to allow Bedrock service access.
    
    Args:
        s3_client: Boto3 S3 client
        sts_client: Boto3 STS client
        bucket_name: Name of the S3 bucket
        region: AWS region
        
    Returns:
        True if policy was added successfully, False otherwise
    """
    try:
        # Get current AWS account ID
        account_id = sts_client.get_caller_identity()['Account']
        
        # Create bucket policy for Bedrock access
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "BedrockS3Access",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock.amazonaws.com"
                    },
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:ListBucket",
                        "s3:GetBucketLocation"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{bucket_name}",
                        f"arn:aws:s3:::{bucket_name}/*"
                    ],
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": account_id
                        }
                    }
                }
            ]
        }
        
        # Apply the bucket policy
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        
        print(f"✅ Successfully added Bedrock access policy to bucket: {bucket_name}")
        print(f"   Account ID: {account_id}")
        print(f"   Region: {region}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            print(f"❌ Bucket does not exist: {bucket_name}")
        else:
            print(f"❌ Failed to add Bedrock bucket policy to {bucket_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error adding Bedrock bucket policy to {bucket_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Add Bedrock permissions to S3 buckets for video processing"
    )
    parser.add_argument(
        '--bucket-name',
        type=str,
        help='Specific bucket name to update (if not provided, updates all buckets in registry)'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-west-2',
        help='AWS region (default: us-west-2)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔐 Adding Bedrock Permissions to S3 Buckets")
    print("=" * 70)
    print()
    
    # Initialize AWS clients
    s3_client = boto3.client('s3', region_name=args.region)
    sts_client = boto3.client('sts', region_name=args.region)
    
    if args.bucket_name:
        # Update specific bucket
        print(f"Updating bucket: {args.bucket_name}")
        print()
        success = add_bedrock_bucket_policy(s3_client, sts_client, args.bucket_name, args.region)
        
        if success:
            print()
            print("=" * 70)
            print("✅ Successfully updated bucket policy")
            print("=" * 70)
            return 0
        else:
            print()
            print("=" * 70)
            print("❌ Failed to update bucket policy")
            print("=" * 70)
            return 1
    else:
        # Update all buckets from resource registry
        registry = ResourceRegistry()
        
        # Get all S3 buckets
        s3_buckets = registry.list_s3_buckets()
        vector_buckets = registry.list_vector_buckets()
        
        all_buckets = []
        
        # Add regular S3 buckets
        for bucket in s3_buckets:
            if bucket.get('status') == 'created' and bucket.get('name'):
                all_buckets.append({
                    'name': bucket['name'],
                    'region': bucket.get('region', args.region),
                    'type': 'S3'
                })
        
        # Add vector buckets
        for bucket in vector_buckets:
            if bucket.get('status') == 'created' and bucket.get('name'):
                all_buckets.append({
                    'name': bucket['name'],
                    'region': bucket.get('region', args.region),
                    'type': 'S3Vector'
                })
        
        if not all_buckets:
            print("⚠️  No buckets found in resource registry")
            print()
            print("To update a specific bucket, use:")
            print("  python scripts/add_bedrock_permissions_to_existing_buckets.py --bucket-name YOUR_BUCKET_NAME")
            return 0
        
        print(f"Found {len(all_buckets)} bucket(s) in resource registry:")
        for bucket in all_buckets:
            print(f"  - {bucket['name']} ({bucket['type']}, {bucket['region']})")
        print()
        
        # Update each bucket
        success_count = 0
        failed_count = 0
        
        for bucket in all_buckets:
            print(f"Updating {bucket['name']}...")
            if add_bedrock_bucket_policy(s3_client, sts_client, bucket['name'], bucket['region']):
                success_count += 1
            else:
                failed_count += 1
            print()
        
        # Summary
        print("=" * 70)
        print("📊 Summary")
        print("=" * 70)
        print(f"✅ Successfully updated: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📦 Total buckets: {len(all_buckets)}")
        print()
        
        if failed_count == 0:
            print("✅ All buckets updated successfully!")
            return 0
        else:
            print("⚠️  Some buckets failed to update. Check errors above.")
            return 1


if __name__ == "__main__":
    sys.exit(main())

