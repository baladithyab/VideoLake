"""
Lambda function to validate input for video ingestion pipeline.

This function validates the input parameters before processing:
- Checks if video_path is a valid S3 URI
- Validates model_type is supported
- Validates backend_types_str format
- Generates a unique video_id for tracking
"""

import json
import os
import re
import uuid
from typing import Dict, Any
import boto3
from urllib.parse import urlparse


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Validate input parameters for video ingestion.
    
    Args:
        event: Input event containing:
            - video_path: S3 URI of the video (e.g., s3://bucket/path/to/video.mp4)
            - model_type: Type of embedding model (default: "marengo")
            - backend_types_str: Comma-separated backend types (optional)
            
    Returns:
        Dict containing validation result and processed parameters
    """
    try:
        # Extract input parameters
        video_path = event.get('video_path', '')
        model_type = event.get('model_type', 'marengo')
        backend_types_str = event.get('backend_types_str', '')
        
        # Validate video_path
        if not video_path:
            raise ValueError("video_path is required")
        
        # Validate S3 URI format
        if not video_path.startswith('s3://'):
            raise ValueError(f"video_path must be a valid S3 URI (s3://bucket/key), got: {video_path}")
        
        # Parse S3 URI to validate format
        parsed = urlparse(video_path)
        bucket_name = parsed.netloc
        key = parsed.path.lstrip('/')
        
        if not bucket_name or not key:
            raise ValueError(f"Invalid S3 URI format: {video_path}")
        
        # Validate video file extension
        valid_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv']
        file_ext = os.path.splitext(key)[1].lower()
        if file_ext not in valid_extensions:
            raise ValueError(f"Unsupported video format: {file_ext}. Supported: {valid_extensions}")
        
        # Check if video exists in S3
        s3_client = boto3.client('s3')
        try:
            s3_client.head_object(Bucket=bucket_name, Key=key)
        except s3_client.exceptions.NoSuchKey:
            raise ValueError(f"Video not found in S3: {video_path}")
        except Exception as e:
            raise ValueError(f"Failed to access video in S3: {str(e)}")
        
        # Validate model_type
        supported_models = ['marengo', 'bedrock', 'titan-multimodal']
        if model_type not in supported_models:
            raise ValueError(f"Unsupported model_type: {model_type}. Supported: {supported_models}")
        
        # Validate backend_types_str format (if provided)
        if backend_types_str:
            backends = [b.strip() for b in backend_types_str.split(',')]
            supported_backends = ['s3vector', 'lancedb', 'qdrant', 'opensearch']
            for backend in backends:
                if backend and backend not in supported_backends:
                    raise ValueError(f"Unsupported backend: {backend}. Supported: {supported_backends}")
        
        # Generate unique video_id for tracking
        video_filename = os.path.basename(key)
        video_id = f"{os.path.splitext(video_filename)[0]}_{uuid.uuid4().hex[:8]}"
        
        # Return validation result
        return {
            'statusCode': 200,
            'validated': True,
            'video_path': video_path,
            'model_type': model_type,
            'backend_types_str': backend_types_str,
            'video_id': video_id,
            'bucket': bucket_name,
            'key': key,
            'message': 'Input validation successful'
        }
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'validated': False,
            'error': str(e),
            'message': 'Input validation failed'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'validated': False,
            'error': str(e),
            'message': 'Unexpected error during validation'
        }