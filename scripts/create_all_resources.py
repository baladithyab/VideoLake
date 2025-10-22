#!/usr/bin/env python3
"""
Create All Resources Script

This script creates all required AWS resources for the S3Vector application:
1. S3 Bucket (for media uploads)
2. S3Vector Bucket (for vector indices)
3. S3Vector Index (1536 dimensions for Marengo 2.7)
4. OpenSearch Domain (with S3Vector backend) - runs in background

Usage:
    python scripts/create_all_resources.py [--prefix PREFIX] [--skip-opensearch]

Options:
    --prefix PREFIX        Resource name prefix (default: s3vector-{timestamp})
    --skip-opensearch      Skip OpenSearch domain creation
    --wait-for-opensearch  Wait for OpenSearch domain to become active
"""

import sys
import os
import argparse
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Suppress Streamlit warnings
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'


def create_resources(prefix: str | None = None, skip_opensearch: bool = False, wait_for_opensearch: bool = False):
    """Create all required AWS resources."""
    
    # Generate prefix if not provided
    if not prefix:
        timestamp = int(time.time())
        prefix = f"s3vector-{timestamp}"
    
    print("=" * 70)
    print("🚀 S3Vector Resource Creation")
    print("=" * 70)
    print(f"\nResource Prefix: {prefix}")
    print(f"Skip OpenSearch: {skip_opensearch}")
    print(f"Wait for OpenSearch: {wait_for_opensearch}")
    print("=" * 70)
    
    # Initialize resource manager
    print("\n🔧 Initializing Resource Manager...")
    try:
        from frontend.components.simplified_resource_manager import SimplifiedResourceManager
        manager = SimplifiedResourceManager()
        print(f"✅ Resource Manager initialized")
        print(f"   Account ID: {manager.account_id}")
        print(f"   Region: {manager.region}")
    except Exception as e:
        print(f"❌ Failed to initialize Resource Manager: {e}")
        return False
    
    # Create S3 Bucket
    print("\n" + "=" * 70)
    print("🪣 STEP 1: Creating S3 Bucket (Media Storage)")
    print("=" * 70)
    s3_bucket_name = f"{prefix}-media"
    print(f"\nCreating S3 bucket: {s3_bucket_name}")
    print("Purpose: Store uploaded media files (videos, images, audio)")

    try:
        success, arn = manager._create_s3_bucket_real(s3_bucket_name)
        if success:
            print(f"✅ S3 bucket created successfully!")
            print(f"   ARN: {arn}")
            print(f"   Encryption: AES256 (SSE-S3)")
        else:
            print(f"❌ Failed to create S3 bucket: {arn}")
            return False
    except Exception as e:
        print(f"❌ Failed to create S3 bucket: {e}")
        return False
    
    # Create S3Vector Bucket
    print("\n" + "=" * 70)
    print("🪣 STEP 2: Creating S3Vector Bucket")
    print("=" * 70)
    vector_bucket_name = f"{prefix}-vector-bucket"
    print(f"\nCreating S3Vector bucket: {vector_bucket_name}")
    print("Purpose: Store vector indices for embeddings")

    try:
        success, arn = manager._create_s3vector_bucket_real(vector_bucket_name)
        if success:
            print(f"✅ S3Vector bucket created successfully!")
            print(f"   ARN: {arn}")
        else:
            print(f"❌ Failed to create S3Vector bucket: {arn}")
            return False
    except Exception as e:
        print(f"❌ Failed to create S3Vector bucket: {e}")
        return False
    
    # Create S3Vector Index
    print("\n" + "=" * 70)
    print("📊 STEP 3: Creating S3Vector Index")
    print("=" * 70)
    index_name = f"{prefix}-index"
    print(f"\nCreating S3Vector index: {index_name}")
    print("Purpose: Store Marengo 2.7 embeddings (1536 dimensions)")
    print("Note: Index will be populated after video processing with Bedrock")

    try:
        success, arn = manager._create_s3vector_index_real(
            bucket_name=vector_bucket_name,
            index_name=index_name,
            vector_dimension=1536
        )
        if success:
            print(f"✅ S3Vector index created successfully!")
            print(f"   ARN: {arn}")
            print(f"   Dimensions: 1536 (Marengo 2.7)")
            print(f"   Distance Metric: cosine")
        else:
            print(f"❌ Failed to create S3Vector index: {arn}")
            return False
    except Exception as e:
        print(f"❌ Failed to create S3Vector index: {e}")
        return False
    
    # Create OpenSearch Domain
    domain_name = None
    if not skip_opensearch:
        print("\n" + "=" * 70)
        print("🔍 STEP 4: Creating OpenSearch Domain (Background)")
        print("=" * 70)
        domain_name = f"{prefix}-domain"
        print(f"\nCreating OpenSearch domain: {domain_name}")
        print("Purpose: Hybrid search with S3Vector backend")
        print("Configuration:")
        print("  - Engine: OpenSearch 2.19")
        print("  - Instance: or1.medium.search")
        print("  - S3Vector Engine: Enabled")
        print(f"  - S3Vector Bucket: {arn}")  # Use the S3Vector bucket ARN
        print("\n⏳ This will take 10-15 minutes to become active...")
        print("   The domain will be created in the background.")

        try:
            # Get the S3Vector bucket ARN from the previous step
            from src.utils.resource_registry import resource_registry
            vector_buckets = resource_registry.list_vector_buckets()
            s3_vector_bucket_arn = None
            for vb in vector_buckets:
                if vb.get('name') == vector_bucket_name:
                    # Construct ARN from bucket name
                    s3_vector_bucket_arn = f"arn:aws:s3vectors:{manager.region}:{manager.account_id}:bucket/{vector_bucket_name}"
                    break

            if not s3_vector_bucket_arn:
                print(f"❌ Could not find S3Vector bucket ARN")
                print(f"⚠️  Other resources were created successfully")
            else:
                success, arn_or_error = manager._create_opensearch_domain_real(
                    domain_name=domain_name,
                    s3_vector_bucket_arn=s3_vector_bucket_arn,
                    wait_for_active=wait_for_opensearch
                )
                if success:
                    print(f"✅ OpenSearch domain creation initiated!")
                    print(f"   ARN: {arn_or_error}")
                    print(f"   Status: Creating (will take 10-15 minutes)")

                    if wait_for_opensearch:
                        print(f"✅ OpenSearch domain is now active!")
                    else:
                        print(f"\nℹ️  Domain is being created in the background.")
                        print(f"   You can check status with:")
                        print(f"   aws opensearch describe-domain --domain-name {domain_name}")
                else:
                    print(f"❌ Failed to create OpenSearch domain: {arn_or_error}")
                    print(f"⚠️  Other resources were created successfully")
        except Exception as e:
            print(f"❌ Failed to create OpenSearch domain: {e}")
            print(f"⚠️  Other resources were created successfully")
    else:
        print("\n" + "=" * 70)
        print("⏭️  STEP 4: Skipping OpenSearch Domain (--skip-opensearch)")
        print("=" * 70)
        print("\nOpenSearch domain creation skipped")
    
    # Summary
    print("\n" + "=" * 70)
    print("🎉 RESOURCE CREATION COMPLETE!")
    print("=" * 70)
    print("\n✅ Created Resources:")
    print(f"   - S3 Bucket: {s3_bucket_name}")
    print(f"   - S3Vector Bucket: {vector_bucket_name}")
    print(f"   - S3Vector Index: {index_name}")
    if not skip_opensearch:
        print(f"   - OpenSearch Domain: {domain_name} (creating in background)")
    
    print("\n📋 Next Steps:")
    print("   1. Upload media files to S3 bucket")
    print("   2. Process media with Marengo 2.7 on AWS Bedrock")
    print("   3. Store embeddings in S3Vector index")
    print("   4. Test semantic search")
    
    if not skip_opensearch and not wait_for_opensearch:
        print(f"\n⏳ OpenSearch Domain Status:")
        print(f"   The domain is being created in the background.")
        print(f"   Check status with:")
        print(f"   aws opensearch describe-domain --domain-name {domain_name}")
        print(f"\n   Or wait for it to complete:")
        print(f"   python scripts/wait_for_opensearch.py {domain_name}")
    
    print("\n" + "=" * 70)
    return True


def main():
    parser = argparse.ArgumentParser(description='Create all S3Vector resources')
    parser.add_argument('--prefix', type=str, help='Resource name prefix')
    parser.add_argument('--skip-opensearch', action='store_true', help='Skip OpenSearch domain creation')
    parser.add_argument('--wait-for-opensearch', action='store_true', help='Wait for OpenSearch domain to become active')
    
    args = parser.parse_args()
    
    success = create_resources(
        prefix=args.prefix,
        skip_opensearch=args.skip_opensearch,
        wait_for_opensearch=args.wait_for_opensearch
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

