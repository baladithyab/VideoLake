#!/usr/bin/env python3
"""
Verify Resources Script

This script checks if the resources created by the frontend actually exist in AWS.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Suppress Streamlit warnings
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

from src.shared.aws_client_pool import get_pooled_client, AWSService


def check_s3vector_resources(bucket_name: str, index_name: str):
    """Check S3Vector bucket and index."""
    print('🔍 Checking S3Vector Resources...')
    print('=' * 60)
    
    s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
    print(f'S3Vectors client region: {s3vectors_client.meta.region_name}')
    
    # List all buckets
    try:
        response = s3vectors_client.list_vector_buckets()
        buckets = response.get('vectorBuckets', [])
        print(f'\n📦 S3Vector Buckets ({len(buckets)}):')
        for bucket in buckets:
            print(f'  - {bucket.get("vectorBucketName")}')
            print(f'    ARN: {bucket.get("vectorBucketArn")}')
            print(f'    Created: {bucket.get("creationTime")}')
    except Exception as e:
        print(f'❌ Error listing buckets: {e}')
        return False
    
    # Check specific bucket
    print(f'\n🔍 Checking bucket: {bucket_name}')
    try:
        response = s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
        print(f'✅ Bucket exists!')
        print(f'   ARN: {response["vectorBucket"]["vectorBucketArn"]}')
    except Exception as e:
        print(f'❌ Bucket not found: {e}')
        return False
    
    # Check index
    print(f'\n🔍 Checking index: {index_name}')
    try:
        response = s3vectors_client.get_index(
            vectorBucketName=bucket_name,
            indexName=index_name
        )
        print(f'✅ Index exists!')
        print(f'   ARN: {response["index"]["indexArn"]}')
        print(f'   Dimensions: {response["index"]["dimension"]}')
        print(f'   Distance Metric: {response["index"]["distanceMetric"]}')
    except Exception as e:
        print(f'❌ Index not found: {e}')
        return False
    
    return True


def check_s3_buckets():
    """Check S3 buckets."""
    print(f'\n🪣 Checking S3 Buckets...')
    print('=' * 60)
    
    s3_client = get_pooled_client(AWSService.S3)
    try:
        response = s3_client.list_buckets()
        s3_buckets = [b['Name'] for b in response.get('Buckets', []) if 's3vector' in b['Name'].lower()]
        print(f'S3 Buckets with "s3vector" in name ({len(s3_buckets)}):')
        for bucket in s3_buckets:
            print(f'  - {bucket}')
        return len(s3_buckets) > 0
    except Exception as e:
        print(f'❌ Error listing S3 buckets: {e}')
        return False


def check_opensearch_domains():
    """Check OpenSearch domains."""
    print(f'\n🔍 Checking OpenSearch Domains...')
    print('=' * 60)
    
    opensearch_client = get_pooled_client(AWSService.OPENSEARCH)
    try:
        response = opensearch_client.list_domain_names()
        domains = response.get('DomainNames', [])
        s3vector_domains = [d for d in domains if 's3vector' in d.get('DomainName', '').lower()]
        print(f'OpenSearch Domains with "s3vector" in name ({len(s3vector_domains)}):')
        
        for domain in s3vector_domains:
            domain_name = domain.get('DomainName')
            print(f'  - {domain_name}')
            
            # Get domain details
            try:
                detail = opensearch_client.describe_domain(DomainName=domain_name)
                domain_info = detail.get('DomainStatus', {})
                print(f'    ARN: {domain_info.get("ARN")}')
                print(f'    Endpoint: {domain_info.get("Endpoint", "N/A")}')
                print(f'    Processing: {domain_info.get("Processing", False)}')
                print(f'    Created: {domain_info.get("Created", False)}')
            except Exception as e:
                print(f'    ❌ Error getting details: {e}')
        
        return len(s3vector_domains) > 0
    except Exception as e:
        print(f'❌ Error listing OpenSearch domains: {e}')
        return False


def main():
    """Main verification function."""
    print('🧪 Resource Verification Script')
    print('=' * 60)
    
    # Resources to check (from the frontend output)
    bucket_name = 's3vector-1759186253-bucket'
    index_name = 's3vector-1759186253-index'
    
    print(f'\nTarget Resources:')
    print(f'  Bucket: {bucket_name}')
    print(f'  Index: {index_name}')
    print()
    
    # Check all resources
    s3vector_ok = check_s3vector_resources(bucket_name, index_name)
    s3_ok = check_s3_buckets()
    opensearch_ok = check_opensearch_domains()
    
    # Summary
    print(f'\n' + '=' * 60)
    print(f'VERIFICATION SUMMARY')
    print(f'=' * 60)
    print(f'S3Vector Resources: {"✅ FOUND" if s3vector_ok else "❌ NOT FOUND"}')
    print(f'S3 Buckets: {"✅ FOUND" if s3_ok else "❌ NOT FOUND"}')
    print(f'OpenSearch Domains: {"✅ FOUND" if opensearch_ok else "❌ NOT FOUND"}')
    
    if s3vector_ok and s3_ok and opensearch_ok:
        print(f'\n🎉 All resources verified successfully!')
        return True
    else:
        print(f'\n⚠️  Some resources were not found')
        return False


if __name__ == "__main__":
    success = main()
    os._exit(0 if success else 1)

