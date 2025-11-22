"""
Lambda function to upsert embeddings to vector backends.

This function:
1. Reads embeddings from S3 JSONL file
2. Upserts to configured vector backends (s3vector, lancedb, qdrant, opensearch)
3. Returns upsert results for each backend
"""

import json
import os
from typing import Dict, Any, List
import boto3
from datetime import datetime


# Initialize AWS clients
s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Upsert embeddings to vector backends.
    
    Args:
        event: Input event containing:
            - embeddings_s3_key: S3 key of the JSONL embeddings file
            - embeddings_bucket: S3 bucket containing embeddings
            - backend_types_str: Comma-separated backend types
            - video_id: Unique identifier for the video
            - metadata: Additional metadata
            
    Returns:
        Dict containing upsert results for each backend
    """
    try:
        # Extract input parameters
        embeddings_key = event.get('embeddings_s3_key', '')
        embeddings_bucket = event.get('embeddings_bucket', '')
        backend_types_str = event.get('backend_types_str', '')
        video_id = event.get('video_id', '')
        metadata = event.get('metadata', {})
        
        if not embeddings_key or not embeddings_bucket:
            raise ValueError("embeddings_s3_key and embeddings_bucket are required")
        
        if not backend_types_str:
            print("No backend_types_str provided, skipping upsert")
            return {
                'statusCode': 200,
                'status': 'skipped',
                'upsert_results': [],
                'message': 'No backends specified for upsert'
            }
        
        # Parse backend types
        backends = [b.strip() for b in backend_types_str.split(',') if b.strip()]
        
        if not backends:
            return {
                'statusCode': 200,
                'status': 'skipped',
                'upsert_results': [],
                'message': 'No valid backends specified'
            }
        
        # Download embeddings from S3
        print(f"Downloading embeddings from s3://{embeddings_bucket}/{embeddings_key}")
        embeddings_obj = s3_client.get_object(Bucket=embeddings_bucket, Key=embeddings_key)
        embeddings_content = embeddings_obj['Body'].read().decode('utf-8')
        
        # Parse JSONL
        embeddings = []
        for line in embeddings_content.strip().split('\n'):
            if line:
                embeddings.append(json.loads(line))
        
        print(f"Loaded {len(embeddings)} embeddings")
        
        # Upsert to each backend
        upsert_results = []
        for backend in backends:
            try:
                result = upsert_to_backend(
                    backend_type=backend,
                    embeddings=embeddings,
                    video_id=video_id,
                    metadata=metadata
                )
                upsert_results.append(result)
            except Exception as e:
                print(f"Failed to upsert to {backend}: {str(e)}")
                upsert_results.append({
                    'backend': backend,
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Determine overall status
        failed_count = sum(1 for r in upsert_results if r.get('status') == 'failed')
        overall_status = 'success' if failed_count == 0 else 'partial_success' if failed_count < len(backends) else 'failed'
        
        return {
            'statusCode': 200,
            'status': overall_status,
            'upsert_results': upsert_results,
            'total_backends': len(backends),
            'successful_backends': len(backends) - failed_count,
            'failed_backends': failed_count,
            'message': f'Upserted to {len(backends) - failed_count}/{len(backends)} backends'
        }
        
    except Exception as e:
        print(f"Error in backend upsert: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'failed',
            'error': str(e),
            'message': 'Failed to upsert embeddings to backends'
        }


def upsert_to_backend(
    backend_type: str,
    embeddings: List[Dict[str, Any]],
    video_id: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Upsert embeddings to a specific vector backend.
    
    Args:
        backend_type: Type of backend (s3vector, lancedb, qdrant, opensearch)
        embeddings: List of embedding objects
        video_id: Unique identifier for the video
        metadata: Additional metadata
        
    Returns:
        Dict containing upsert result
    """
    print(f"Upserting {len(embeddings)} embeddings to {backend_type}")
    
    try:
        if backend_type == 's3vector':
            return upsert_to_s3vector(embeddings, video_id, metadata)
        elif backend_type == 'lancedb':
            return upsert_to_lancedb(embeddings, video_id, metadata)
        elif backend_type == 'qdrant':
            return upsert_to_qdrant(embeddings, video_id, metadata)
        elif backend_type == 'opensearch':
            return upsert_to_opensearch(embeddings, video_id, metadata)
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
    except Exception as e:
        raise Exception(f"Failed to upsert to {backend_type}: {str(e)}")


def upsert_to_s3vector(embeddings: List[Dict[str, Any]], video_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert embeddings to S3Vector backend."""
    # TODO: Implement actual S3Vector upsert logic
    # For now, return mock success
    print(f"Mock upsert to S3Vector: {len(embeddings)} embeddings")
    return {
        'backend': 's3vector',
        'status': 'success',
        'embeddings_count': len(embeddings),
        'video_id': video_id,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Upserted to S3Vector (placeholder implementation)'
    }


def upsert_to_lancedb(embeddings: List[Dict[str, Any]], video_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert embeddings to LanceDB backend."""
    # TODO: Implement actual LanceDB upsert logic
    # This would typically involve:
    # 1. Connecting to LanceDB instance
    # 2. Opening/creating a table
    # 3. Inserting embeddings
    print(f"Mock upsert to LanceDB: {len(embeddings)} embeddings")
    return {
        'backend': 'lancedb',
        'status': 'success',
        'embeddings_count': len(embeddings),
        'video_id': video_id,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Upserted to LanceDB (placeholder implementation)'
    }


def upsert_to_qdrant(embeddings: List[Dict[str, Any]], video_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert embeddings to Qdrant backend."""
    # TODO: Implement actual Qdrant upsert logic
    # This would typically involve:
    # 1. Connecting to Qdrant instance
    # 2. Creating/updating collection
    # 3. Upserting points
    print(f"Mock upsert to Qdrant: {len(embeddings)} embeddings")
    return {
        'backend': 'qdrant',
        'status': 'success',
        'embeddings_count': len(embeddings),
        'video_id': video_id,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Upserted to Qdrant (placeholder implementation)'
    }


def upsert_to_opensearch(embeddings: List[Dict[str, Any]], video_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert embeddings to OpenSearch backend."""
    # TODO: Implement actual OpenSearch upsert logic
    # This would typically involve:
    # 1. Connecting to OpenSearch instance
    # 2. Creating/updating index
    # 3. Bulk indexing documents
    print(f"Mock upsert to OpenSearch: {len(embeddings)} embeddings")
    return {
        'backend': 'opensearch',
        'status': 'success',
        'embeddings_count': len(embeddings),
        'video_id': video_id,
        'timestamp': datetime.utcnow().isoformat(),
        'message': 'Upserted to OpenSearch (placeholder implementation)'
    }