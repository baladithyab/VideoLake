#!/usr/bin/env python3
"""Verify Complete Setup Resources"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'

from src.shared.aws_client_pool import get_pooled_client, AWSService

# Resource names
setup_name = 's3vector-1759187028'
vector_bucket = f'{setup_name}-vector-bucket'
index_name = f'{setup_name}-index'
s3_bucket = f'{setup_name}-media'
domain_name = f'{setup_name}-domain'

print('🔍 Verifying Complete Setup Resources')
print('=' * 70)
print(f'Setup Name: {setup_name}')
print()

# Initialize clients
s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
s3_client = get_pooled_client(AWSService.S3)
opensearch_client = get_pooled_client(AWSService.OPENSEARCH)

results = {}

# 1. S3Vector Bucket
print('1️⃣ S3Vector Bucket')
print('-' * 70)
try:
    response = s3vectors_client.get_vector_bucket(vectorBucketName=vector_bucket)
    bucket_info = response['vectorBucket']
    print(f'✅ FOUND')
    print(f'   Name: {bucket_info.get("vectorBucketName")}')
    print(f'   ARN: {bucket_info.get("vectorBucketArn")}')
    print(f'   Created: {bucket_info.get("creationTime")}')
    results['vector_bucket'] = True
except Exception as e:
    print(f'❌ NOT FOUND: {e}')
    results['vector_bucket'] = False

# 2. S3Vector Index
print()
print('2️⃣ S3Vector Index')
print('-' * 70)
try:
    response = s3vectors_client.get_index(
        vectorBucketName=vector_bucket,
        indexName=index_name
    )
    index_info = response['index']
    print(f'✅ FOUND')
    print(f'   Name: {index_info.get("indexName")}')
    print(f'   ARN: {index_info.get("indexArn")}')
    print(f'   Dimensions: {index_info.get("dimension")}')
    print(f'   Distance Metric: {index_info.get("distanceMetric")}')
    print(f'   Data Type: {index_info.get("dataType")}')
    results['index'] = True
except Exception as e:
    print(f'❌ NOT FOUND: {e}')
    results['index'] = False

# 3. S3 Bucket
print()
print('3️⃣ S3 Bucket (Media Storage)')
print('-' * 70)
try:
    s3_client.head_bucket(Bucket=s3_bucket)
    print(f'✅ FOUND')
    print(f'   Name: {s3_bucket}')
    print(f'   ARN: arn:aws:s3:::{s3_bucket}')
    
    try:
        location = s3_client.get_bucket_location(Bucket=s3_bucket)
        region = location.get('LocationConstraint') or 'us-east-1'
        print(f'   Region: {region}')
    except:
        pass
    results['s3_bucket'] = True
except Exception as e:
    print(f'❌ NOT FOUND: {e}')
    results['s3_bucket'] = False

# 4. OpenSearch Domain
print()
print('4️⃣ OpenSearch Domain')
print('-' * 70)
try:
    response = opensearch_client.describe_domain(DomainName=domain_name)
    domain_info = response['DomainStatus']
    print(f'✅ FOUND')
    print(f'   Name: {domain_info.get("DomainName")}')
    print(f'   ARN: {domain_info.get("ARN")}')
    print(f'   Engine Version: {domain_info.get("EngineVersion")}')
    print(f'   Created: {domain_info.get("Created")}')
    print(f'   Processing: {domain_info.get("Processing")}')
    print(f'   Deleted: {domain_info.get("Deleted", False)}')
    
    endpoint = domain_info.get('Endpoint')
    if endpoint:
        print(f'   Endpoint: {endpoint}')
    else:
        print(f'   Endpoint: Not yet available (domain still creating)')
    
    aiml_options = domain_info.get('AIMLOptions', {})
    s3_vectors = aiml_options.get('S3VectorsEngine', {})
    if s3_vectors.get('Enabled'):
        print(f'   S3 Vectors Engine: ✅ Enabled')
    
    results['opensearch'] = True
except Exception as e:
    print(f'❌ NOT FOUND: {e}')
    results['opensearch'] = False

# Summary
print()
print('=' * 70)
print('VERIFICATION SUMMARY')
print('=' * 70)

all_found = all(results.values())

for resource, found in results.items():
    status = '✅ PASS' if found else '❌ FAIL'
    print(f'{resource.replace("_", " ").title()}: {status}')

print()
if all_found:
    print('🎉 All resources verified successfully!')
    print()
    print('Note: OpenSearch domain may take 10-15 minutes to become fully active.')
    os._exit(0)
else:
    print('⚠️  Some resources were not found')
    os._exit(1)

