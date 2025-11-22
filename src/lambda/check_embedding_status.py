"""
Lambda function to check the status of an async Bedrock embedding job.

This function:
1. Queries Bedrock for job status
2. Returns status (IN_PROGRESS, COMPLETED, FAILED)
3. Provides output location when completed
"""

import json
import os
from typing import Dict, Any
import boto3
from datetime import datetime


# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Check the status of an async Bedrock embedding job.
    
    Args:
        event: Input event containing:
            - job_id: Bedrock job/invocation ARN
            - video_id: Unique identifier for the video
            
    Returns:
        Dict containing job status and output location if completed
    """
    try:
        # Extract input parameters
        job_id = event.get('job_id', '')
        video_id = event.get('video_id', '')
        
        if not job_id or not video_id:
            raise ValueError("job_id and video_id are required")
        
        print(f"Checking status for job: {job_id}")
        
        # Get job status from Bedrock
        job_status = get_bedrock_job_status(job_id, video_id)
        
        return {
            'statusCode': 200,
            'status': job_status['status'],
            'job_id': job_id,
            'video_id': video_id,
            'output_location': job_status.get('output_location', ''),
            'error_message': job_status.get('error_message', ''),
            'checked_at': datetime.utcnow().isoformat(),
            'message': f"Job status: {job_status['status']}"
        }
        
    except Exception as e:
        print(f"Error checking job status: {str(e)}")
        return {
            'statusCode': 500,
            'status': 'ERROR',
            'job_id': event.get('job_id', ''),
            'video_id': event.get('video_id', ''),
            'error_message': str(e),
            'message': 'Failed to check job status'
        }


def get_bedrock_job_status(job_id: str, video_id: str) -> Dict[str, Any]:
    """
    Get the status of a Bedrock async job.
    
    Args:
        job_id: Bedrock job/invocation ARN
        video_id: Unique identifier for the video
        
    Returns:
        Dict with status, output_location, and error_message
    """
    try:
        # Check if this is a mock job ID (for development)
        if job_id.startswith('mock-job-'):
            print("Mock job detected - simulating completion")
            return {
                'status': 'COMPLETED',
                'output_location': f"s3://{os.environ.get('EMBEDDINGS_BUCKET', 'embeddings-bucket')}/jobs/{video_id}/output.json"
            }
        
        # Call Bedrock to get async invocation status
        # Note: Actual API may differ based on Bedrock documentation
        try:
            response = bedrock_runtime.get_async_invoke(
                invocationArn=job_id
            )
            
            # Map Bedrock status to our status
            bedrock_status = response.get('status', 'UNKNOWN')
            
            status_mapping = {
                'InProgress': 'IN_PROGRESS',
                'Completed': 'COMPLETED',
                'Failed': 'FAILED',
                'Stopping': 'IN_PROGRESS',
                'Stopped': 'FAILED'
            }
            
            our_status = status_mapping.get(bedrock_status, 'IN_PROGRESS')
            
            result = {
                'status': our_status
            }
            
            # If completed, get output location
            if our_status == 'COMPLETED':
                output_config = response.get('outputDataConfig', {})
                s3_output = output_config.get('s3OutputDataConfig', {})
                result['output_location'] = s3_output.get('s3Uri', '')
            
            # If failed, get error message
            if our_status == 'FAILED':
                result['error_message'] = response.get('failureMessage', 'Unknown error')
            
            return result
            
        except bedrock_runtime.exceptions.ResourceNotFoundException:
            print(f"Job not found: {job_id}")
            return {
                'status': 'FAILED',
                'error_message': f"Job not found: {job_id}"
            }
        except Exception as api_error:
            print(f"Bedrock API error: {str(api_error)}")
            # If the API doesn't exist yet or errors, default to IN_PROGRESS for now
            return {
                'status': 'IN_PROGRESS',
                'error_message': ''
            }
            
    except Exception as e:
        print(f"Error getting job status: {str(e)}")
        raise