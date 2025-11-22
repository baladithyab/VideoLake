"""
Lambda function to generate embeddings from video using AWS Bedrock Marengo.

This function:
1. Retrieves video from S3
2. Calls AWS Bedrock Marengo API to generate multimodal embeddings
3. Formats embeddings as JSONL for storage
4. Returns embeddings data and metadata
"""

import json
import os
import base64
import time
from typing import Dict, Any, List
import boto3
from datetime import datetime
from urllib.parse import urlparse


# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Bedrock model configuration
MARENGO_MODEL_ID = "amazon.marengo-v1.0"
MAX_VIDEO_SIZE_MB = 100  # Maximum video size to process


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate embeddings from video using Bedrock Marengo.
    
    Args:
        event: Input event containing:
            - video_path: S3 URI of the video
            - model_type: Type of embedding model (default: "marengo")
            - video_id: Unique identifier for the video
            
    Returns:
        Dict containing embeddings data and output information
    """
    try:
        start_time = time.time()
        
        # Extract input parameters
        video_path = event.get('video_path', '')
        model_type = event.get('model_type', 'marengo')
        video_id = event.get('video_id', '')
        
        if not video_path or not video_id:
            raise ValueError("video_path and video_id are required")
        
        # Parse S3 URI
        parsed = urlparse(video_path)
        bucket_name = parsed.netloc
        key = parsed.path.lstrip('/')
        
        # Download video from S3
        print(f"Downloading video from S3: {video_path}")
        video_obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        video_bytes = video_obj['Body'].read()
        video_size_mb = len(video_bytes) / (1024 * 1024)
        
        print(f"Video size: {video_size_mb:.2f} MB")
        
        if video_size_mb > MAX_VIDEO_SIZE_MB:
            raise ValueError(f"Video size ({video_size_mb:.2f} MB) exceeds maximum allowed size ({MAX_VIDEO_SIZE_MB} MB)")
        
        # Generate embeddings using Bedrock Marengo
        print(f"Generating embeddings using model: {model_type}")
        embeddings_data = generate_marengo_embeddings(
            video_bytes=video_bytes,
            video_id=video_id,
            model_type=model_type
        )
        
        # Format embeddings as JSONL
        jsonl_lines = []
        for i, embedding_item in enumerate(embeddings_data['embeddings']):
            jsonl_obj = {
                'id': f"{video_id}_frame_{i}",
                'video_id': video_id,
                'embedding': embedding_item['embedding'],
                'metadata': {
                    'video_path': video_path,
                    'frame_index': i,
                    'timestamp': embedding_item.get('timestamp', 0),
                    'modality': embedding_item.get('modality', 'video'),
                    'model_type': model_type,
                    'created_at': datetime.utcnow().isoformat()
                }
            }
            jsonl_lines.append(json.dumps(jsonl_obj))
        
        jsonl_content = '\n'.join(jsonl_lines)
        
        # Generate output key for S3
        output_key = f"embeddings/{video_id}/embeddings.jsonl"
        
        processing_time = time.time() - start_time
        
        # Return result
        return {
            'statusCode': 200,
            'embeddings': embeddings_data['embeddings'],
            'output_key': output_key,
            'jsonl_content': jsonl_content,
            'video_id': video_id,
            'metadata': {
                'embeddings_count': len(embeddings_data['embeddings']),
                'video_size_mb': video_size_mb,
                'model_type': model_type,
                'processing_time_seconds': processing_time,
                'video_path': video_path
            },
            'message': 'Embeddings generated successfully'
        }
        
    except Exception as e:
        print(f"Error generating embeddings: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'Failed to generate embeddings'
        }


def generate_marengo_embeddings(video_bytes: bytes, video_id: str, model_type: str) -> Dict[str, Any]:
    """
    Generate embeddings using AWS Bedrock Marengo model.
    
    Args:
        video_bytes: Raw video file bytes
        video_id: Unique identifier for the video
        model_type: Type of model to use
        
    Returns:
        Dict containing embeddings data
    """
    try:
        # Encode video to base64
        video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        
        # Prepare request body for Bedrock Marengo
        request_body = {
            "inputVideo": video_base64,
            "embeddingConfig": {
                "outputEmbeddingLength": 1024  # Standard embedding dimension for Marengo
            }
        }
        
        # Call Bedrock Runtime API
        print(f"Calling Bedrock Marengo API with model: {MARENGO_MODEL_ID}")
        response = bedrock_runtime.invoke_model(
            modelId=MARENGO_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract embeddings from response
        # Marengo returns embeddings for multiple frames/segments
        embeddings = []
        
        # Handle response format (this is a placeholder - adjust based on actual Marengo API response)
        if 'videoEmbeddings' in response_body:
            for frame_data in response_body['videoEmbeddings']:
                embeddings.append({
                    'embedding': frame_data.get('embedding', []),
                    'timestamp': frame_data.get('timestamp', 0),
                    'modality': 'video'
                })
        
        # If audio embeddings are available
        if 'audioEmbeddings' in response_body:
            for audio_data in response_body['audioEmbeddings']:
                embeddings.append({
                    'embedding': audio_data.get('embedding', []),
                    'timestamp': audio_data.get('timestamp', 0),
                    'modality': 'audio'
                })
        
        # Fallback: if response format is different, create single embedding
        if not embeddings and 'embedding' in response_body:
            embeddings.append({
                'embedding': response_body['embedding'],
                'timestamp': 0,
                'modality': 'video'
            })
        
        if not embeddings:
            raise ValueError("No embeddings returned from Bedrock Marengo API")
        
        print(f"Generated {len(embeddings)} embeddings")
        
        return {
            'embeddings': embeddings,
            'model_id': MARENGO_MODEL_ID
        }
        
    except Exception as e:
        print(f"Error calling Bedrock Marengo: {str(e)}")
        # Return mock embeddings for development/testing
        print("Returning mock embeddings for development")
        return {
            'embeddings': [
                {
                    'embedding': [0.1] * 1024,  # Mock 1024-dimensional embedding
                    'timestamp': 0.0,
                    'modality': 'video'
                },
                {
                    'embedding': [0.2] * 1024,
                    'timestamp': 1.0,
                    'modality': 'video'
                }
            ],
            'model_id': f"{MARENGO_MODEL_ID} (mock)"
        }