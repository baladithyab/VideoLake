"""
TwelveLabs Video Processing Service for generating video embeddings using TwelveLabs Marengo model.

This service provides video embedding generation using TwelveLabs Marengo Embed 2.7 model
through Amazon Bedrock's async inference APIs with proper job monitoring, result processing,
and integration with S3 Vector storage.
"""

import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from botocore.exceptions import ClientError, BotoCoreError
from datetime import datetime, timedelta

from src.config import config_manager
from src.utils.aws_clients import aws_client_factory
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VideoEmbeddingResult:
    """Result from video embedding generation."""
    embeddings: List[Dict[str, Any]]  # List of embedding segments
    input_source: str  # S3 URI or "base64"
    model_id: str
    processing_time_ms: Optional[int] = None
    total_segments: Optional[int] = None
    video_duration_sec: Optional[float] = None


@dataclass
class AsyncJobInfo:
    """Information about async processing job."""
    job_id: str
    invocation_arn: str
    model_id: str
    input_config: Dict[str, Any]
    output_s3_uri: str
    status: str = "InProgress"  # InProgress, Completed, Failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class VideoProcessingConfig:
    """Configuration for video processing."""
    model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    region: str = "us-east-1"  # TwelveLabs models available in us-east-1, eu-west-1, ap-northeast-2
    embedding_options: List[str] = field(default_factory=lambda: ["visual-text"])
    use_fixed_length_sec: Optional[float] = 5.0  # 5-second segments
    min_clip_sec: int = 4
    max_video_duration_sec: int = 7200  # 2 hours max
    poll_interval_sec: int = 30
    max_poll_attempts: int = 120  # 1 hour max wait time

    # Supported regions for TwelveLabs models
    SUPPORTED_REGIONS = ["us-east-1", "eu-west-1", "ap-northeast-2"]


class TwelveLabsVideoProcessingService:
    """Service for processing videos using TwelveLabs Marengo model through Bedrock."""
    
    def __init__(self, region: str = None):
        """Initialize the TwelveLabs video processing service.

        Args:
            region: AWS region (defaults to config_manager region, must be supported by TwelveLabs)
        """
        self.region = region or config_manager.aws_config.region

        # Validate region support
        if self.region not in VideoProcessingConfig.SUPPORTED_REGIONS:
            logger.warning(f"Region {self.region} may not support TwelveLabs models. "
                         f"Supported regions: {VideoProcessingConfig.SUPPORTED_REGIONS}")

        self.config = VideoProcessingConfig(region=self.region)
        
        # Expose model_id for convenience
        self.model_id = self.config.model_id

        # Initialize AWS clients - create clients directly for specific region
        # if different from default config region
        if self.region != config_manager.aws_config.region:
            # Create clients for specific region
            import boto3
            from botocore.config import Config
            
            client_config = Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                read_timeout=60,
                connect_timeout=10,
                region_name=self.region
            )
            
            self.runtime_client = boto3.client('bedrock-runtime', config=client_config)
            self.s3_client = boto3.client('s3', config=client_config)
        else:
            # Use factory clients for default region
            self.runtime_client = aws_client_factory.get_bedrock_runtime_client()
            self.s3_client = aws_client_factory.get_s3_client()
        
        # Active jobs tracking
        self.active_jobs: Dict[str, AsyncJobInfo] = {}
        
        logger.info(f"Initialized TwelveLabs Video Processing Service in region {self.region}")

    def validate_model_access(self, model_id: str = None) -> bool:
        """Validate access to TwelveLabs model.
        
        Args:
            model_id: Model ID to validate (defaults to Marengo)
            
        Returns:
            True if model is accessible, False otherwise
        """
        model_id = model_id or self.config.model_id
        
        try:
            if self.region != config_manager.aws_config.region:
                # Create bedrock client for specific region
                import boto3
                from botocore.config import Config

                client_config = Config(
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    read_timeout=60,
                    connect_timeout=10,
                    region_name=self.region
                )
                bedrock_client = boto3.client('bedrock', config=client_config)
            else:
                # Create bedrock client for default region
                import boto3
                from botocore.config import Config

                client_config = Config(
                    retries={'max_attempts': 3, 'mode': 'adaptive'},
                    read_timeout=60,
                    connect_timeout=10,
                    region_name=config_manager.aws_config.region
                )
                bedrock_client = boto3.client('bedrock', config=client_config)
            response = bedrock_client.list_foundation_models()
            
            available_models = [model['modelId'] for model in response['modelSummaries']]
            is_available = model_id in available_models
            
            if is_available:
                logger.info(f"Model {model_id} is available in region {self.region}")
            else:
                logger.warning(f"Model {model_id} not available. Available models: {available_models}")
                
            return is_available
            
        except Exception as e:
            logger.error(f"Error validating model access: {e}")
            return False

    def start_video_processing(
        self,
        video_s3_uri: str = None,
        video_base64: str = None,
        output_s3_uri: str = None,
        embedding_options: List[str] = None,
        start_sec: float = 0,
        length_sec: float = None,
        use_fixed_length_sec: float = None,
        client_request_token: str = None
    ) -> AsyncJobInfo:
        """Start async video processing using TwelveLabs Marengo model.
        
        Args:
            video_s3_uri: S3 URI of video file
            video_base64: Base64 encoded video data
            output_s3_uri: S3 URI for output results
            embedding_options: Types of embeddings to generate
            start_sec: Start time in video (seconds)
            length_sec: Length to process (seconds)
            use_fixed_length_sec: Fixed segment duration
            client_request_token: Idempotency token
            
        Returns:
            AsyncJobInfo with job details
            
        Raises:
            ValidationError: If input parameters are invalid
            VectorEmbeddingError: If processing fails to start
        """
        if not video_s3_uri and not video_base64:
            raise ValidationError("Either video_s3_uri or video_base64 must be provided")
        
        if video_s3_uri and video_base64:
            raise ValidationError("Only one of video_s3_uri or video_base64 should be provided")
        
        if not output_s3_uri:
            # Generate default output location using regular S3 bucket (not S3 Vector bucket)
            # TwelveLabs output must go to a regular S3 bucket, not S3 Vector bucket
            vector_bucket_name = config_manager.aws_config.s3_vectors_bucket
            regular_bucket_name = f"{vector_bucket_name}-videos"  # Use the same regular bucket as input
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
            output_s3_uri = f"s3://{regular_bucket_name}/video-processing-results/{timestamp}/"
        
        # Prepare model input
        model_input = {
            "inputType": "video",
            "startSec": start_sec,
        }
        
        if length_sec is not None:
            model_input["lengthSec"] = length_sec
            
        if use_fixed_length_sec is not None:
            model_input["useFixedLengthSec"] = use_fixed_length_sec
        else:
            model_input["useFixedLengthSec"] = self.config.use_fixed_length_sec
            
        model_input["minClipSec"] = self.config.min_clip_sec
        
        if embedding_options:
            model_input["embeddingOption"] = embedding_options
        else:
            model_input["embeddingOption"] = self.config.embedding_options
        
        # Configure media source
        if video_s3_uri:
            # Get current AWS account ID for bucket owner
            try:
                import boto3
                sts_client = boto3.client('sts', region_name=self.region)
                account_id = sts_client.get_caller_identity()['Account']
            except Exception as e:
                logger.warning(f"Could not get account ID: {e}")
                account_id = None
            
            s3_location = {"uri": video_s3_uri}
            if account_id:
                s3_location["bucketOwner"] = account_id
                
            model_input["mediaSource"] = {
                "s3Location": s3_location
            }
            input_source = video_s3_uri
        else:
            model_input["mediaSource"] = {
                "base64String": video_base64
            }
            input_source = "base64"
        
        # Prepare output configuration with bucket owner
        output_config = {
            "s3OutputDataConfig": {
                "s3Uri": output_s3_uri
            }
        }

        # Add bucket owner to output config if we have account ID
        if video_s3_uri:  # Only add if we're using S3 input (account ID already retrieved)
            try:
                import boto3
                sts_client = boto3.client('sts', region_name=self.region)
                account_id = sts_client.get_caller_identity()['Account']
                output_config["s3OutputDataConfig"]["bucketOwner"] = account_id
            except Exception as e:
                logger.warning(f"Could not get account ID for output config: {e}")

        # Prepare request
        request_data = {
            "modelId": self.config.model_id,
            "modelInput": model_input,
            "outputDataConfig": output_config
        }
        
        if client_request_token:
            request_data["clientRequestToken"] = client_request_token
        else:
            request_data["clientRequestToken"] = str(uuid.uuid4())
        
        try:
            logger.info(f"Starting async video processing for {input_source}")
            logger.debug(f"Request data: {json.dumps(request_data, indent=2)}")
            
            start_time = time.time()
            response = self.runtime_client.start_async_invoke(**request_data)
            processing_time = int((time.time() - start_time) * 1000)
            
            invocation_arn = response['invocationArn']
            job_id = invocation_arn.split('/')[-1]  # Extract job ID from ARN
            
            # Create job info
            job_info = AsyncJobInfo(
                job_id=job_id,
                invocation_arn=invocation_arn,
                model_id=self.config.model_id,
                input_config={
                    "input_source": input_source,
                    "model_input": model_input,
                    "processing_time_ms": processing_time
                },
                output_s3_uri=output_s3_uri,
                status="InProgress"
            )
            
            # Track the job
            self.active_jobs[job_id] = job_info
            
            logger.info(f"Started async job {job_id} (ARN: {invocation_arn})")
            return job_info
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"AWS error starting video processing: {error_code} - {error_msg}")
            logger.error(f"Full error response: {e.response}")
            logger.error(f"Request data: {json.dumps(request_data, indent=2, default=str)}")
            raise VectorEmbeddingError(f"Failed to start video processing: {error_code} - {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error starting video processing: {e}")
            raise VectorEmbeddingError(f"Failed to start video processing: {str(e)}")

    def get_job_status(self, job_id: str) -> AsyncJobInfo:
        """Get status of async processing job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Updated AsyncJobInfo with current status
            
        Raises:
            ValidationError: If job_id not found
            VectorEmbeddingError: If status check fails
        """
        if job_id not in self.active_jobs:
            raise ValidationError(f"Job {job_id} not found in active jobs")
        
        job_info = self.active_jobs[job_id]
        
        try:
            response = self.runtime_client.get_async_invoke(
                invocationArn=job_info.invocation_arn
            )
            
            status = response.get('status', 'Unknown')
            job_info.status = status
            
            if status == 'Completed':
                job_info.completed_at = datetime.utcnow()
                logger.info(f"Job {job_id} completed successfully")
            elif status == 'Failed':
                job_info.completed_at = datetime.utcnow()
                job_info.error_message = response.get('failureMessage', 'Unknown error')
                logger.error(f"Job {job_id} failed: {job_info.error_message}")
            
            return job_info
            
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Error checking job status: {error_msg}")
            raise VectorEmbeddingError(f"Failed to check job status: {error_msg}")

    def wait_for_completion(self, job_id: str, timeout_sec: int = None) -> AsyncJobInfo:
        """Wait for async job to complete with polling.
        
        Args:
            job_id: Job ID to wait for
            timeout_sec: Maximum wait time in seconds
            
        Returns:
            Completed AsyncJobInfo
            
        Raises:
            VectorEmbeddingError: If job fails or times out
        """
        timeout_sec = timeout_sec or (self.config.max_poll_attempts * self.config.poll_interval_sec)
        start_time = time.time()
        attempts = 0
        
        logger.info(f"Waiting for job {job_id} to complete (timeout: {timeout_sec}s)")
        
        while time.time() - start_time < timeout_sec:
            attempts += 1
            job_info = self.get_job_status(job_id)
            
            if job_info.status == 'Completed':
                logger.info(f"Job {job_id} completed after {attempts} attempts ({time.time() - start_time:.1f}s)")
                return job_info
            elif job_info.status == 'Failed':
                raise VectorEmbeddingError(f"Job {job_id} failed: {job_info.error_message}")
            
            logger.debug(f"Job {job_id} still in progress (attempt {attempts})")
            time.sleep(self.config.poll_interval_sec)
        
        raise VectorEmbeddingError(f"Job {job_id} timed out after {timeout_sec} seconds")

    def retrieve_results(self, job_id: str) -> VideoEmbeddingResult:
        """Retrieve and process results from completed job.
        
        Args:
            job_id: Job ID to retrieve results for
            
        Returns:
            VideoEmbeddingResult with processed embeddings
            
        Raises:
            ValidationError: If job not found or not completed
            VectorEmbeddingError: If result retrieval fails
        """
        if job_id not in self.active_jobs:
            raise ValidationError(f"Job {job_id} not found")
        
        job_info = self.active_jobs[job_id]
        
        if job_info.status != 'Completed':
            raise ValidationError(f"Job {job_id} is not completed (status: {job_info.status})")
        
        try:
            # Parse S3 output URI
            output_uri = job_info.output_s3_uri
            if not output_uri.startswith('s3://'):
                raise VectorEmbeddingError(f"Invalid S3 output URI: {output_uri}")
            
            # Extract bucket and prefix from S3 URI
            uri_parts = output_uri[5:].split('/', 1)
            bucket_name = uri_parts[0]
            prefix = uri_parts[1] if len(uri_parts) > 1 else ""
            
            # List objects in output location
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response or not response['Contents']:
                raise VectorEmbeddingError(f"No results found in {output_uri}")
            
            # Find the result file - prioritize output.json over other JSON files
            result_objects = [obj for obj in response['Contents'] 
                            if obj['Key'].endswith('.json')]
            
            if not result_objects:
                raise VectorEmbeddingError(f"No JSON result files found in {output_uri}")
            
            # Prioritize output.json if it exists, otherwise use the first JSON file
            result_key = None
            for obj in result_objects:
                if obj['Key'].endswith('output.json'):
                    result_key = obj['Key']
                    break
            
            if not result_key:
                result_key = result_objects[0]['Key']
            logger.info(f"Retrieving results from s3://{bucket_name}/{result_key}")
            
            result_obj = self.s3_client.get_object(Bucket=bucket_name, Key=result_key)
            result_data = json.loads(result_obj['Body'].read())
            
            # Process the results
            embeddings = []
            logger.info(f"Processing result data of type: {type(result_data)}")

            if isinstance(result_data, list):
                embeddings = result_data
                logger.info(f"Extracted {len(embeddings)} embeddings from list")
            elif isinstance(result_data, dict):
                logger.info(f"Result data keys: {list(result_data.keys())}")

                # Check for different possible structures
                if 'embeddings' in result_data:
                    embeddings = result_data['embeddings']
                    logger.info(f"Extracted {len(embeddings)} embeddings from 'embeddings' key")
                elif 'results' in result_data:
                    embeddings = result_data['results']
                    logger.info(f"Extracted {len(embeddings)} embeddings from 'results' key")
                elif 'data' in result_data:
                    embeddings = result_data['data']
                    logger.info(f"Extracted {len(embeddings)} embeddings from 'data' key")
                else:
                    # Single embedding result
                    embeddings = [result_data]
                    logger.info(f"Treating single dict as one embedding")
            else:
                raise VectorEmbeddingError(f"Unexpected result format: {type(result_data)}")

            logger.info(f"Total embeddings to process: {len(embeddings)}")
            
            # Calculate processing metrics
            processing_time = job_info.input_config.get('processing_time_ms', 0)
            if job_info.completed_at and job_info.created_at:
                total_time = (job_info.completed_at - job_info.created_at).total_seconds() * 1000
                processing_time += total_time
            
            # Determine video duration from embeddings
            video_duration = 0
            if embeddings:
                # Find embeddings with endSec values
                end_secs = [emb.get('endSec', 0) for emb in embeddings if 'endSec' in emb and emb.get('endSec') is not None]
                if end_secs:
                    video_duration = max(end_secs)
                else:
                    # Fallback: estimate from number of segments if no endSec available
                    video_duration = len(embeddings) * self.config.use_fixed_length_sec if self.config.use_fixed_length_sec else 0
            
            result = VideoEmbeddingResult(
                embeddings=embeddings,
                input_source=job_info.input_config['input_source'],
                model_id=job_info.model_id,
                processing_time_ms=int(processing_time),
                total_segments=len(embeddings),
                video_duration_sec=video_duration
            )
            
            logger.info(f"Retrieved {len(embeddings)} embedding segments for job {job_id}")
            return result
            
        except ClientError as e:
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"S3 error retrieving results: {error_msg}")
            raise VectorEmbeddingError(f"Failed to retrieve results: {error_msg}")
        except Exception as e:
            logger.error(f"Error processing results: {e}")
            raise VectorEmbeddingError(f"Failed to process results: {str(e)}")

    def process_video_sync(
        self,
        video_s3_uri: str = None,
        video_base64: str = None,
        output_s3_uri: str = None,
        embedding_options: List[str] = None,
        start_sec: float = 0,
        length_sec: float = None,
        use_fixed_length_sec: float = None,
        timeout_sec: int = None
    ) -> VideoEmbeddingResult:
        """Process video synchronously with automatic polling.
        
        Args:
            video_s3_uri: S3 URI of video file
            video_base64: Base64 encoded video data
            output_s3_uri: S3 URI for output results
            embedding_options: Types of embeddings to generate
            start_sec: Start time in video (seconds)
            length_sec: Length to process (seconds)
            use_fixed_length_sec: Fixed segment duration
            timeout_sec: Maximum wait time
            
        Returns:
            VideoEmbeddingResult with processed embeddings
        """
        # Start processing
        job_info = self.start_video_processing(
            video_s3_uri=video_s3_uri,
            video_base64=video_base64,
            output_s3_uri=output_s3_uri,
            embedding_options=embedding_options,
            start_sec=start_sec,
            length_sec=length_sec,
            use_fixed_length_sec=use_fixed_length_sec
        )
        
        # Wait for completion
        completed_job = self.wait_for_completion(job_info.job_id, timeout_sec)
        
        # Retrieve results
        return self.retrieve_results(completed_job.job_id)

    def cleanup_job(self, job_id: str) -> None:
        """Remove job from active tracking.
        
        Args:
            job_id: Job ID to clean up
        """
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
            logger.debug(f"Cleaned up job {job_id}")

    def list_active_jobs(self) -> List[AsyncJobInfo]:
        """Get list of currently tracked jobs.
        
        Returns:
            List of active AsyncJobInfo objects
        """
        return list(self.active_jobs.values())

    def generate_text_embedding(self, text: str) -> Dict[str, Any]:
        """
        Generate text embedding using TwelveLabs Marengo model.
        
        Args:
            text: Text to generate embeddings for
            
        Returns:
            Dictionary with embedding data
            
        Raises:
            ValidationError: If text is empty or too long
            VectorEmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValidationError("Text cannot be empty")
        
        # TwelveLabs Marengo has a limit of 77 tokens for text
        if len(text.split()) > 77:
            logger.warning(f"Text has {len(text.split())} tokens, will be truncated to 77 tokens")
        
        try:
            # Generate unique job ID
            job_id = f"text_embed_{uuid.uuid4().hex[:8]}"
            
            # Prepare input for text embedding
            model_input = {
                "inputType": "text",
                "inputText": text.strip(),
                "textTruncate": "end"  # Truncate at end if exceeds 77 tokens
            }
            
            # Start async job with custom model input
            # We need to temporarily modify the start_video_processing call for text embeddings
            
            # Generate default output location
            vector_bucket_name = config_manager.aws_config.s3_vectors_bucket
            regular_bucket_name = f"{vector_bucket_name}-videos"
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
            output_s3_uri = f"s3://{regular_bucket_name}/text-embedding-results/{timestamp}/"
            
            # Prepare request data for text embedding
            request_data = {
                "modelId": self.config.model_id,
                "modelInput": model_input,
                "outputDataConfig": {
                    "s3OutputDataConfig": {
                        "s3Uri": output_s3_uri
                    }
                },
                "clientRequestToken": str(uuid.uuid4())
            }
            
            # Add bucket owner to output config
            try:
                import boto3
                sts_client = boto3.client('sts', region_name=self.region)
                account_id = sts_client.get_caller_identity()['Account']
                request_data["outputDataConfig"]["s3OutputDataConfig"]["bucketOwner"] = account_id
            except Exception as e:
                logger.warning(f"Could not get account ID for output config: {e}")
            
            try:
                logger.debug(f"Starting text embedding with request: {json.dumps(request_data, indent=2)}")
                start_time = time.time()
                response = self.runtime_client.start_async_invoke(**request_data)
                processing_time = int((time.time() - start_time) * 1000)
                
                invocation_arn = response['invocationArn']
                actual_job_id = invocation_arn.split('/')[-1]  # Extract job ID from ARN
                
                # Create job info
                async_job = AsyncJobInfo(
                    job_id=actual_job_id,
                    invocation_arn=invocation_arn,
                    model_id=self.config.model_id,
                    input_config={
                        "input_source": "text",
                        "model_input": model_input,
                        "processing_time_ms": processing_time
                    },
                    output_s3_uri=output_s3_uri,
                    status="InProgress"
                )
                
                # Track the job
                self.active_jobs[actual_job_id] = async_job
                logger.info(f"Started text embedding job {actual_job_id}")
                job_id = actual_job_id  # Update job_id to the actual one
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                error_msg = e.response.get('Error', {}).get('Message', str(e))
                logger.error(f"AWS error starting text embedding: {error_code} - {error_msg}")
                raise VectorEmbeddingError(f"Failed to start text embedding: {error_code} - {error_msg}")
            except Exception as e:
                logger.error(f"Unexpected error starting text embedding: {e}")
                raise VectorEmbeddingError(f"Failed to start text embedding: {str(e)}")
            
            # Wait for completion (text embedding should be fast)
            completed_job = self.wait_for_completion(job_id, timeout_sec=120)
            
            if completed_job.status != "Completed":
                raise VectorEmbeddingError(f"Text embedding failed: {completed_job.error_message}")
            
            # Retrieve results
            embedding_result = self.retrieve_results(job_id)
            
            # Clean up job resources
            try:
                self.cleanup_job(job_id)
            except Exception as e:
                logger.warning(f"Failed to cleanup job {job_id}: {str(e)}")
            
            # Return the embedding data - for text there should be only one embedding
            if embedding_result.embeddings:
                embedding_data = embedding_result.embeddings[0]
                return {
                    'embedding': embedding_data.get('embedding', []),
                    'model_id': embedding_result.model_id,
                    'processing_time_ms': embedding_result.processing_time_ms
                }
            else:
                raise VectorEmbeddingError("No embeddings returned for text")
                
        except Exception as e:
            logger.error(f"Text embedding generation failed: {str(e)}")
            if isinstance(e, (ValidationError, VectorEmbeddingError)):
                raise
            raise VectorEmbeddingError(f"Text embedding generation failed: {str(e)}")

    def generate_media_embedding(self, s3_uri: str, input_type: str) -> Dict[str, Any]:
        """
        Generate media embedding using TwelveLabs Marengo model.
        
        Args:
            s3_uri: S3 URI of the media file
            input_type: Type of media ("video", "audio", "image")
            
        Returns:
            Dictionary with embedding data
            
        Raises:
            ValidationError: If parameters are invalid
            VectorEmbeddingError: If embedding generation fails
        """
        if not s3_uri:
            raise ValidationError("S3 URI cannot be empty")
        
        if input_type not in ["video", "audio", "image"]:
            raise ValidationError(f"Invalid input type: {input_type}. Must be video, audio, or image")
        
        try:
            # For single media embeddings, use the existing process_video_sync method
            # but modify the input configuration
            model_input = {
                "inputType": input_type,
                "mediaSource": {
                    "s3Location": {
                        "uri": s3_uri
                    }
                }
            }
            
            # For non-video media, we still use the video processing pipeline
            # but with different input type
            embedding_result = self.process_video_sync(
                s3_uri=s3_uri,
                model_input=model_input,
                timeout_sec=300
            )
            
            # Return the first embedding (for single media files)
            if embedding_result.embeddings:
                embedding_data = embedding_result.embeddings[0]
                return {
                    'embedding': embedding_data.get('embedding', []),
                    'model_id': embedding_result.model_id,
                    'processing_time_ms': embedding_result.processing_time_ms
                }
            else:
                raise VectorEmbeddingError(f"No embeddings returned for {input_type}")
                
        except Exception as e:
            logger.error(f"Media embedding generation failed: {str(e)}")
            if isinstance(e, (ValidationError, VectorEmbeddingError)):
                raise
            raise VectorEmbeddingError(f"Media embedding generation failed: {str(e)}")

    def estimate_cost(
        self,
        video_duration_minutes: float,
        model_id: str = None
    ) -> Dict[str, float]:
        """Estimate processing cost for video.
        
        Args:
            video_duration_minutes: Video duration in minutes
            model_id: Model ID (defaults to Marengo)
            
        Returns:
            Dictionary with cost estimates
        """
        model_id = model_id or self.config.model_id
        
        # TwelveLabs Marengo pricing: $0.05 per minute
        cost_per_minute = 0.05
        estimated_cost = video_duration_minutes * cost_per_minute
        
        return {
            'video_duration_minutes': video_duration_minutes,
            'cost_per_minute_usd': cost_per_minute,
            'estimated_cost_usd': estimated_cost,
            'model_id': model_id
        }