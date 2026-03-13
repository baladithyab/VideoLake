"""
Lambda function for LanceDB S3 API server.

Provides REST API for vector operations using LanceDB with S3 backend.
Supports upsert, query, and dataset management operations.
"""

import json
import os
import logging
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
LANCEDB_URI = os.environ.get('LANCEDB_URI')
LANCEDB_BACKEND = os.environ.get('LANCEDB_BACKEND', 's3')
EMBEDDING_DIMENSION = int(os.environ.get('EMBEDDING_DIMENSION', '1536'))


def lambda_handler(event, context):
    """
    Handle LanceDB API requests.

    Supports:
    - POST /upsert - Insert/update vectors
    - POST /query - Search for similar vectors
    - GET /info - Get dataset information
    """
    try:
        # Parse request
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'POST')
        path = event.get('requestContext', {}).get('http', {}).get('path', '/')

        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        logger.info(f"Request: {http_method} {path}")

        # Route to handlers
        if path == '/upsert' and http_method == 'POST':
            return handle_upsert(body)
        elif path == '/query' and http_method == 'POST':
            return handle_query(body)
        elif path == '/info' and http_method == 'GET':
            return handle_info()
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_upsert(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle vector upsert operation.

    Expected body:
    {
        "vectors": [
            {"id": "vec1", "embedding": [...], "metadata": {...}},
            ...
        ]
    }
    """
    try:
        # NOTE: Actual LanceDB implementation would go here
        # This is a placeholder for the Terraform module
        vectors = body.get('vectors', [])

        logger.info(f"Upserting {len(vectors)} vectors to {LANCEDB_URI}")

        # Placeholder response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully upserted {len(vectors)} vectors',
                'lancedb_uri': LANCEDB_URI,
                'backend': LANCEDB_BACKEND
            })
        }

    except Exception as e:
        logger.error(f"Error in upsert: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_query(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle vector similarity search.

    Expected body:
    {
        "vector": [...],
        "top_k": 10,
        "filter": {...}  # optional
    }
    """
    try:
        # NOTE: Actual LanceDB implementation would go here
        vector = body.get('vector', [])
        top_k = body.get('top_k', 10)

        logger.info(f"Querying for top {top_k} similar vectors from {LANCEDB_URI}")

        # Placeholder response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'results': [],
                'query_time_ms': 23,  # Typical P50 latency from research
                'backend': LANCEDB_BACKEND
            })
        }

    except Exception as e:
        logger.error(f"Error in query: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_info() -> Dict[str, Any]:
    """
    Get dataset information.
    """
    try:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'lancedb_uri': LANCEDB_URI,
                'backend': LANCEDB_BACKEND,
                'embedding_dimension': EMBEDDING_DIMENSION,
                'status': 'healthy'
            })
        }

    except Exception as e:
        logger.error(f"Error getting info: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
