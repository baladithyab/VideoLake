#!/usr/bin/env python3
"""
Test Complete Setup Validation

This script validates that the complete setup creates all expected resources:
1. S3Vector bucket
2. S3Vector index
3. S3 bucket for media storage
4. OpenSearch domain (optional)
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


def test_complete_setup_resources(setup_name: str):
    """Test that all resources from complete setup exist."""
    print('🧪 Testing Complete Setup Resources')
    print('=' * 60)
    print(f'Setup Name: {setup_name}')
    print()
    
    # Expected resource names
    vector_bucket_name = f"{setup_name}-vector-bucket"
    index_name = f"{setup_name}-index"
    s3_bucket_name = f"{setup_name}-media"
    domain_name = f"{setup_name}-domain"
    
    print('Expected Resources:')
    print(f'  S3Vector Bucket: {vector_bucket_name}')
    print(f'  S3Vector Index: {index_name}')
    print(f'  S3 Bucket: {s3_bucket_name}')
    print(f'  OpenSearch Domain: {domain_name}')
    print()
    
    # Initialize clients
    s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
    s3_client = get_pooled_client(AWSService.S3)
    opensearch_client = get_pooled_client(AWSService.OPENSEARCH)
    
    results = {}
    
    # Test 1: S3Vector Bucket
    print('🔍 Test 1: S3Vector Bucket')
    try:
        response = s3vectors_client.get_vector_bucket(vectorBucketName=vector_bucket_name)
        bucket_arn = response['vectorBucket']['vectorBucketArn']
        print(f'✅ S3Vector bucket exists')
        print(f'   ARN: {bucket_arn}')
        results['vector_bucket'] = True
    except Exception as e:
        print(f'❌ S3Vector bucket not found: {e}')
        results['vector_bucket'] = False
    
    # Test 2: S3Vector Index
    print(f'\n🔍 Test 2: S3Vector Index')
    try:
        response = s3vectors_client.get_index(
            vectorBucketName=vector_bucket_name,
            indexName=index_name
        )
        index_arn = response['index']['indexArn']
        dimensions = response['index']['dimension']
        metric = response['index']['distanceMetric']
        print(f'✅ S3Vector index exists')
        print(f'   ARN: {index_arn}')
        print(f'   Dimensions: {dimensions}')
        print(f'   Distance Metric: {metric}')
        results['index'] = True
    except Exception as e:
        print(f'❌ S3Vector index not found: {e}')
        results['index'] = False
    
    # Test 3: S3 Bucket
    print(f'\n🔍 Test 3: S3 Bucket (Media Storage)')
    try:
        s3_client.head_bucket(Bucket=s3_bucket_name)
        print(f'✅ S3 bucket exists')
        print(f'   Name: {s3_bucket_name}')
        results['s3_bucket'] = True
    except Exception as e:
        print(f'❌ S3 bucket not found: {e}')
        results['s3_bucket'] = False
    
    # Test 4: OpenSearch Domain (optional)
    print(f'\n🔍 Test 4: OpenSearch Domain (Optional)')
    try:
        response = opensearch_client.describe_domain(DomainName=domain_name)
        domain_status = response['DomainStatus']
        domain_arn = domain_status['ARN']
        processing = domain_status.get('Processing', False)
        created = domain_status.get('Created', False)
        endpoint = domain_status.get('Endpoint', 'N/A')
        
        print(f'✅ OpenSearch domain exists')
        print(f'   ARN: {domain_arn}')
        print(f'   Created: {created}')
        print(f'   Processing: {processing}')
        print(f'   Endpoint: {endpoint}')
        results['opensearch_domain'] = True
    except Exception as e:
        print(f'ℹ️  OpenSearch domain not found (optional): {e}')
        results['opensearch_domain'] = False
    
    # Summary
    print(f'\n' + '=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)
    
    required_resources = ['vector_bucket', 'index', 's3_bucket']
    required_passed = all(results.get(r, False) for r in required_resources)
    
    print(f'Required Resources:')
    print(f'  S3Vector Bucket: {"✅ PASS" if results.get("vector_bucket") else "❌ FAIL"}')
    print(f'  S3Vector Index: {"✅ PASS" if results.get("index") else "❌ FAIL"}')
    print(f'  S3 Bucket: {"✅ PASS" if results.get("s3_bucket") else "❌ FAIL"}')
    
    print(f'\nOptional Resources:')
    print(f'  OpenSearch Domain: {"✅ FOUND" if results.get("opensearch_domain") else "ℹ️  NOT CREATED"}')
    
    if required_passed:
        print(f'\n🎉 All required resources validated successfully!')
        return True
    else:
        print(f'\n⚠️  Some required resources were not found')
        return False


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate complete setup resources')
    parser.add_argument('setup_name', help='Setup name to validate (e.g., s3vector-1759186253)')
    
    args = parser.parse_args()
    
    success = test_complete_setup_resources(args.setup_name)
    os._exit(0 if success else 1)


if __name__ == "__main__":
    main()

