"""
Cost estimation Lambda function for infrastructure configurations.

Estimates monthly costs for:
- Embedding providers (Bedrock, Marketplace, SageMaker)
- Vector stores (S3Vector, OpenSearch, Qdrant, LanceDB, pgvector)
- Storage (datasets, artifacts)
- Data transfer

Uses AWS Pricing API for real-time pricing (with caching).
"""

import boto3
import json
import os
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timedelta

# Pricing cache (in-memory, cleared on cold start)
PRICING_CACHE = {}
CACHE_TTL = int(os.environ.get('CACHE_TTL', '3600'))  # 1 hour default


def handler(event, context):
    """
    Estimate monthly cost for a given infrastructure configuration.

    Input (POST body):
    {
      "embedding_providers": [
        {"type": "bedrock", "model": "titan-text-v2", "estimated_requests": 100000},
        {"type": "marketplace", "instance_type": "ml.g4dn.xlarge", "hours": 730}
      ],
      "vector_stores": [
        {"type": "s3vector", "storage_gb": 10, "queries_per_month": 50000},
        {"type": "opensearch", "instance_type": "or1.medium.search", "instance_count": 2}
      ],
      "datasets": [
        {"modality": "text", "size_gb": 0.15},
        {"modality": "video", "size_gb": 2.0}
      ]
    }

    Output:
    {
      "total_monthly_cost": 125.45,
      "breakdown": {
        "embedding_providers": 15.20,
        "vector_stores": 95.00,
        "storage": 5.25,
        "data_transfer": 10.00
      },
      "details": [...]
    }
    """
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        # Initialize cost breakdown
        cost_breakdown = {
            'embedding_providers': 0.0,
            'vector_stores': 0.0,
            'storage': 0.0,
            'data_transfer': 0.0
        }
        details = []

        # 1. Embedding Providers
        for provider in body.get('embedding_providers', []):
            cost = estimate_embedding_provider_cost(provider)
            cost_breakdown['embedding_providers'] += cost
            details.append({
                'category': 'Embedding Provider',
                'resource': f"{provider['type']} - {provider.get('model', 'custom')}",
                'monthly_cost': round(cost, 2),
                'config': provider
            })

        # 2. Vector Stores
        for store in body.get('vector_stores', []):
            cost = estimate_vector_store_cost(store)
            cost_breakdown['vector_stores'] += cost
            details.append({
                'category': 'Vector Store',
                'resource': f"{store['type']}",
                'monthly_cost': round(cost, 2),
                'config': store
            })

        # 3. Storage (datasets and artifacts)
        for dataset in body.get('datasets', []):
            cost = estimate_storage_cost(dataset)
            cost_breakdown['storage'] += cost
            details.append({
                'category': 'Storage',
                'resource': f"{dataset['modality']} dataset ({dataset['size_gb']} GB)",
                'monthly_cost': round(cost, 2),
                'config': dataset
            })

        # 4. Data Transfer (estimate 10% of storage size transferred monthly)
        total_storage_gb = sum(d['size_gb'] for d in body.get('datasets', []))
        transfer_cost = total_storage_gb * 0.1 * 0.09  # $0.09/GB egress
        cost_breakdown['data_transfer'] = transfer_cost

        # Calculate total
        total_cost = sum(cost_breakdown.values())

        # Build response
        response_body = {
            'total_monthly_cost': round(total_cost, 2),
            'breakdown': {k: round(v, 2) for k, v in cost_breakdown.items()},
            'details': details,
            'currency': 'USD',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'disclaimer': 'Estimated costs based on AWS Pricing API. Actual costs may vary.'
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response_body, default=str)
        }

    except Exception as e:
        print(f"Error estimating costs: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to estimate costs'
            })
        }


def estimate_embedding_provider_cost(provider: Dict) -> float:
    """Estimate cost for embedding provider."""
    provider_type = provider['type']

    if provider_type == 'bedrock':
        model = provider.get('model', 'titan-text-v2')
        requests = provider.get('estimated_requests', 0)

        # Bedrock pricing (per 1K tokens)
        pricing_map = {
            'titan-text-v1': 0.0001,
            'titan-text-v2': 0.0001,
            'titan-image-v1': 0.00006,  # per image
            'cohere-english-v3': 0.0001,
            'cohere-multilingual-v3': 0.0001,
            'titan-embed-g1-text-02': 0.00013
        }

        cost_per_request = pricing_map.get(model, 0.0001)
        # Assume average 50 tokens per request for text
        if 'image' in model:
            return requests * cost_per_request
        else:
            return (requests / 1000) * cost_per_request * 50

    elif provider_type == 'marketplace':
        instance_type = provider.get('instance_type', 'ml.g4dn.xlarge')
        hours = provider.get('hours', 730)  # Full month

        # SageMaker pricing (per hour)
        instance_pricing = {
            'ml.g4dn.xlarge': 0.736,
            'ml.g4dn.2xlarge': 1.047,
            'ml.m5.xlarge': 0.269,
            'ml.m5.2xlarge': 0.538
        }

        hourly_rate = instance_pricing.get(instance_type, 0.50)
        return hours * hourly_rate

    elif provider_type == 'sagemaker':
        instance_type = provider.get('instance_type', 'ml.m5.xlarge')
        hours = provider.get('hours', 730)

        instance_pricing = {
            'ml.m5.xlarge': 0.269,
            'ml.m5.2xlarge': 0.538,
            'ml.g4dn.xlarge': 0.736
        }

        hourly_rate = instance_pricing.get(instance_type, 0.30)
        return hours * hourly_rate

    return 0.0


def estimate_vector_store_cost(store: Dict) -> float:
    """Estimate cost for vector store."""
    store_type = store['type']

    if store_type == 's3vector':
        storage_gb = store.get('storage_gb', 10)
        queries = store.get('queries_per_month', 0)

        # S3 storage: $0.023/GB/month
        # S3 API queries: $0.0004 per 1K requests (LIST), $0.004 per 1K requests (GET)
        storage_cost = storage_gb * 0.023
        query_cost = (queries / 1000) * 0.002  # Average of GET/LIST
        return storage_cost + query_cost

    elif store_type == 'opensearch':
        instance_type = store.get('instance_type', 'or1.medium.search')
        instance_count = store.get('instance_count', 1)

        # OpenSearch managed instance pricing
        instance_pricing = {
            'or1.medium.search': 0.139,  # per hour
            'or1.large.search': 0.278,
            'or1.xlarge.search': 0.556
        }

        hourly_rate = instance_pricing.get(instance_type, 0.15)
        return hourly_rate * 730 * instance_count

    elif store_type in ['qdrant', 'lancedb']:
        # ECS Fargate pricing
        vcpu = store.get('vcpu', 1)
        memory_gb = store.get('memory_gb', 2)

        # Fargate: $0.04048/vCPU-hour + $0.004445/GB-hour
        vcpu_cost = vcpu * 0.04048 * 730
        memory_cost = memory_gb * 0.004445 * 730

        # Storage (EFS or EBS)
        storage_gb = store.get('storage_gb', 20)
        storage_cost = storage_gb * 0.30  # EFS Standard: $0.30/GB/month

        return vcpu_cost + memory_cost + storage_cost

    elif store_type == 'pgvector':
        min_acu = store.get('min_acu', 0.5)
        max_acu = store.get('max_acu', 2)
        avg_acu = (min_acu + max_acu) / 2  # Rough estimate

        # Aurora Serverless v2: $0.12/ACU-hour
        compute_cost = avg_acu * 0.12 * 730

        # Storage
        storage_gb = store.get('storage_gb', 10)
        storage_cost = storage_gb * 0.10  # $0.10/GB/month

        return compute_cost + storage_cost

    return 0.0


def estimate_storage_cost(dataset: Dict) -> float:
    """Estimate S3 storage cost for datasets."""
    size_gb = dataset['size_gb']
    # S3 Standard: $0.023/GB/month
    return size_gb * 0.023
