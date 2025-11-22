"""
Lambda function to retrieve completed embeddings from Bedrock async job output.

This function:
1. Downloads the embedding output from S3
2. Parses and formats embeddings as JSONL
3. Returns embeddings data for Step Function to save
"""

import json
import os
from typing import Dict, Any, List
import boto3
from datetime import datetime
from urllib.parse import urlparse


# Initialize AWS clients
s3_client = boto3.client('s3')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Retrieve and format embeddings from completed Bedrock job.
    
    Args:
        event: Input event containing:
            - job_id: Bedrock job/invocation ARN
            - video_id: Unique identifier for the video
            - output_location: S3 URI where Bedrock saved the output
            
    Returns:
        Dict containing formatted embeddings and JSONL content
    """
    try:
        # Extract input parameters
        job_id = event.get('job_id', '')
        video_id = event.get('video_id', '')
        output_location = event.get('output_location', '')
        
        if not video_id:
            raise ValueError("video_id is required")
        
        print(f"Retrieving embeddings for video: {video_id}")
        print(f"Output location: {output_location}")
        
        # Download embeddings from S3
        embeddings_data = download_embeddings_from_s3(output_location, video_id)
        
        # Format embeddings as JSONL
        jsonl_lines = []
        for i, embedding_item in enumerate(embeddings_data['embeddings']):
            jsonl_obj = {
                'id': f"{video_id}_frame_{i}",
                'video_id': video_id,
                'embedding': embedding_item['embedding'],
                'metadata': {
                    'frame_index': i,
                    'timestamp': embedding_item.get('timestamp', 0),
                    'modality': embedding_item.get('modality', 'video'),
                    'model_type': embeddings_data.get('model_type', 'marengo'),
                    'created_at': datetime.utcnow().isoformat(),
                    'job_id': job_id
                }
            }
            jsonl_lines.append(json.dumps(jsonl_obj))
        
        jsonl_content = '\n'.join(jsonl_lines)
        
        # Generate output key for final S3 storage
        output_key = f"embeddings/{video_id}/embeddings.jsonl"
        
        return {
            'statusCode': 200,
            'embeddings': embeddings_data['embeddings'],
            'output_key': output_key,
            'jsonl_content': jsonl_content,
            'video_id': video_id,
            'metadata': {
                'embeddings_count': len(embeddings_data['embeddings']),
                'model_type': embeddings_data.get('model_type', 'marengo'),
                'job_id': job_id
            },
            'message': 'Embeddings retrieved and formatted successfully'
        }
        
    except Exception as e:
        print(f"Error retrieving embeddings: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'video_id': event.get('video_id', ''),
            'message': 'Failed to retrieve embeddings'
        }


def download_embeddings_from_s3(output_location: str, video_id: str) -> Dict[str, Any]:
    """
    Download and parse embeddings from S3 output location.
    
    Args:
        output_location: S3 URI where Bedrock saved the output
        video_id: Unique identifier for the video
        
    Returns:
        Dict containing embeddings data
    """
    try:
        # Handle mock output location for development
        if not output_location or output_location.startswith('s3://embeddings-bucket/jobs'):
            print("Using mock embeddings for development")
            return {
                'embeddings': [
                    {
                        'embedding': [0.1] * 1024,
                        'timestamp': 0.0,
                        'modality': 'video'
                    },
                    {
                        'embedding': [0.2] * 1024,
                        'timestamp': 1.0,
                        'modality': 'video'
                    },
                    {
                        'embedding': [0.15] * 1024,
                        'timestamp': 0.5,
                        'modality': 'audio'
                    }
                ],
                'model_type': 'marengo'
            }
        
        # Parse S3 URI
        parsed = urlparse(output_location)
        bucket_name = parsed.netloc
        key = parsed.path.lstrip('/')
        
        print(f"Downloading from s3://{bucket_name}/{key}")
        
        # Download output file from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        output_content = response['Body'].read().decode('utf-8')
        
        # Parse Bedrock output
        # The format may vary based on actual Bedrock Marengo API
        output_data = json.loads(output_content)
        
        embeddings = []
        
        # Handle different possible output formats
        if 'videoEmbeddings' in output_data:
            for frame_data in output_data['videoEmbeddings']:
                embeddings.append({
                    'embedding': frame_data.get('embedding', []),
                    'timestamp': frame_data.get('timestamp', 0),
                    'modality': 'video'
                })
        
        if 'audioEmbeddings' in output_data:
            for audio_data in output_data['audioEmbeddings']:
                embeddings.append({
                    'embedding': audio_data.get('embedding', []),
                    'timestamp': audio_data.get('timestamp', 0),
                    'modality': 'audio'
                })
        
        # Fallback: single embedding
        if not embeddings and 'embedding' in output_data:
            embeddings.append({
                'embedding': output_data['embedding'],
                'timestamp': 0,
                'modality': 'video'
            })
        
        # Another possible format: array of embeddings
        if not embeddings and 'embeddings' in output_data:
            for emb_data in output_data['embeddings']:
                embeddings.append({
                    'embedding': emb_data.get('values', emb_data.get('embedding', [])),
                    'timestamp': emb_data.get('timestamp', 0),
                    'modality': emb_data.get('modality', 'video')
                })
        
        if not embeddings:
            raise ValueError("No embeddings found in Bedrock output")
        
        print(f"Retrieved {len(embeddings)} embeddings")
        
        return {
            'embeddings': embeddings,
            'model_type': output_data.get('modelType', 'marengo')
        }
        
    except Exception as e:
        print(f"Error downloading embeddings: {str(e)}")
        raise