"""
Amazon Nova Embedding Service

This service provides multi-modal embeddings using Amazon Nova models through Bedrock.
Nova embeddings use a SINGLE unified embedding space across all modalities (text, image,
video, audio), unlike Marengo which uses separate embedding spaces per modality.

Key Differences from Marengo:
- Nova: Single embedding space (e.g., 3072D) for all modalities
- Marengo: Separate embedding spaces (visual-text, visual-image, audio)
- Nova: Unified semantic search across all content types
- Marengo: Task-specific search with result fusion and user-selectable vector types

AWS Documentation:
https://docs.aws.amazon.com/nova/latest/userguide/nova-embeddings.html
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional, Union, Literal
from dataclasses import dataclass
from botocore.exceptions import ClientError

from src.config.unified_config_manager import get_unified_config_manager
from src.utils.aws_clients import aws_client_factory
from src.utils.aws_retry import AWSRetryHandler
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Type hints for Nova parameters
EmbeddingPurpose = Literal["GENERIC_INDEX", "RETRIEVAL", "CLASSIFICATION", "CLUSTERING"]
EmbeddingDimension = Literal[3072, 1024, 384, 256]
VideoEmbeddingMode = Literal["AUDIO_VIDEO_COMBINED", "AUDIO_ONLY", "VIDEO_ONLY"]
TruncationMode = Literal["END", "START"]


@dataclass
class NovaEmbeddingResult:
    """Result from Nova embedding generation - single unified embedding."""
    embedding: List[float]
    input_type: str  # 'text', 'image', 'video', 'audio'
    input_source: str  # URI or text content
    model_id: str
    embedding_dimension: int
    embedding_purpose: str
    processing_time_ms: Optional[int] = None
    unified_space: bool = True  # Always True for Nova


@dataclass
class NovaModelInfo:
    """Information about Nova embedding models."""
    model_id: str
    supported_dimensions: List[int]
    max_context: str
    supports_video: bool
    supports_image: bool
    supports_audio: bool
    supports_text: bool
    supports_async: bool
    cost_per_1k_input_tokens: float
    description: str


class NovaEmbeddingService:
    """
    Service for generating multi-modal embeddings using Amazon Nova models.

    Nova provides a unified embedding space across all modalities, enabling
    seamless cross-modal search (e.g., search videos with text queries).

    This contrasts with Marengo's approach where users select which specific
    embedding types (visual-text, visual-image, audio) they want to generate.

    Example:
        service = NovaEmbeddingService(embedding_dimension=1024)

        # Generate video embedding (unified space, all modalities combined)
        video_result = service.generate_video_embedding(
            video_uri="s3://bucket/video.mp4",
            embedding_mode="AUDIO_VIDEO_COMBINED"  # Single unified embedding
        )

        # Generate text embedding (same unified space)
        text_result = service.generate_text_embedding("sunset over mountains")

        # These embeddings can be directly compared via cosine similarity
        # because they exist in the same semantic space
    """

    # Official Nova embedding model (as per AWS documentation)
    SUPPORTED_MODELS = {
        'amazon.nova-2-multimodal-embeddings-v1:0': NovaModelInfo(
            model_id='amazon.nova-2-multimodal-embeddings-v1:0',
            supported_dimensions=[3072, 1024, 384, 256],
            max_context='8K tokens or 30s video/audio',
            supports_video=True,
            supports_image=True,
            supports_audio=True,
            supports_text=True,
            supports_async=True,
            cost_per_1k_input_tokens=0.0002,  # Estimated, check AWS pricing
            description='Amazon Nova Multimodal Embeddings - Unified space across text, image, video, audio'
        )
    }

    # Default model ID
    DEFAULT_MODEL_ID = 'amazon.nova-2-multimodal-embeddings-v1:0'

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        embedding_dimension: EmbeddingDimension = 1024,
        embedding_purpose: EmbeddingPurpose = "GENERIC_INDEX",
        region_name: str = "us-east-1"
    ):
        """
        Initialize Nova embedding service.

        Args:
            model_id: Nova model ID (default: amazon.nova-2-multimodal-embeddings-v1:0)
            embedding_dimension: Output dimension (3072, 1024, 384, or 256)
            embedding_purpose: Purpose for embeddings (GENERIC_INDEX, RETRIEVAL, etc.)
            region_name: AWS region (Nova currently only in us-east-1)
        """
        # Validate model
        if model_id not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported Nova model: {model_id}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        self.model_id = model_id
        self.model_info = self.SUPPORTED_MODELS[model_id]

        # Validate dimension
        if embedding_dimension not in self.model_info.supported_dimensions:
            raise ValueError(
                f"Unsupported embedding dimension: {embedding_dimension}. "
                f"Supported: {self.model_info.supported_dimensions}"
            )

        self.embedding_dimension = embedding_dimension
        self.embedding_purpose = embedding_purpose
        self.region_name = region_name

        # Initialize Bedrock client
        self.bedrock_client = aws_client_factory.get_bedrock_runtime_client()

        logger.info(
            f"Initialized Nova embedding service: model={model_id}, "
            f"dimension={embedding_dimension}, purpose={embedding_purpose}, "
            f"unified_space=True"
        )

    def generate_video_embedding(
        self,
        video_uri: str,
        embedding_mode: VideoEmbeddingMode = "AUDIO_VIDEO_COMBINED",
        segment_duration_sec: Optional[int] = None,
        start_time_sec: Optional[float] = None,
        end_time_sec: Optional[float] = None,
        use_async: bool = True  # Default to async for videos (no 100MB limit)
    ) -> Union[NovaEmbeddingResult, str]:
        """
        Generate unified embedding for video content.

        Unlike Marengo (which generates separate embeddings per modality that
        users can select), Nova generates a SINGLE embedding that captures
        the selected modality combination in a unified semantic space.

        Args:
            video_uri: S3 URI of video (e.g., s3://bucket/video.mp4)
            embedding_mode: How to combine modalities:
                - "AUDIO_VIDEO_COMBINED": Single unified embedding (default)
                - "AUDIO_ONLY": Audio-only unified embedding
                - "VIDEO_ONLY": Video-only unified embedding
            segment_duration_sec: If set, use segmented embeddings (async only)
            start_time_sec: Optional start time for clip
            end_time_sec: Optional end time for clip
            use_async: Use async API for large videos (returns invocation ARN)

        Returns:
            NovaEmbeddingResult with single unified embedding (sync)
            OR invocation ARN string (async)
        """
        if not self.model_info.supports_video:
            raise ValidationError(
                f"Model {self.model_id} does not support video embeddings."
            )

        start_time = time.time()

        # Determine task type
        task_type = "SEGMENTED_EMBEDDING" if segment_duration_sec else "SINGLE_EMBEDDING"

        if task_type == "SINGLE_EMBEDDING":
            # Build single embedding request
            # Extract video format from URI (default to mp4)
            video_format = "mp4"
            if video_uri.endswith('.webm'):
                video_format = "webm"
            elif video_uri.endswith('.mkv'):
                video_format = "mkv"
            elif video_uri.endswith('.avi'):
                video_format = "avi"
            elif video_uri.endswith('.mov'):
                video_format = "mov"

            request_body = {
                "taskType": "SINGLE_EMBEDDING",
                "singleEmbeddingParams": {
                    "embeddingPurpose": self.embedding_purpose,
                    "embeddingDimension": self.embedding_dimension,
                    "video": {
                        "format": video_format,  # Required by Nova API
                        "embeddingMode": embedding_mode,
                        "source": {
                            "s3Location": {"uri": video_uri}
                        }
                    }
                }
            }

            # Add optional time range
            if start_time_sec is not None or end_time_sec is not None:
                request_body["singleEmbeddingParams"]["video"]["timeRange"] = {}
                if start_time_sec is not None:
                    request_body["singleEmbeddingParams"]["video"]["timeRange"]["startSeconds"] = start_time_sec
                if end_time_sec is not None:
                    request_body["singleEmbeddingParams"]["video"]["timeRange"]["endSeconds"] = end_time_sec

            try:
                # Call Bedrock with retry logic
                def _invoke_nova():
                    return self.bedrock_client.invoke_model(
                        modelId=self.model_id,
                        contentType='application/json',
                        accept='application/json',
                        body=json.dumps(request_body)
                    )

                response = AWSRetryHandler.retry_with_backoff(
                    _invoke_nova,
                    max_retries=3,
                    operation_name=f"nova_video_embedding_{self.model_id}"
                )

                response_body = json.loads(response['body'].read())

                # Nova response format: {"embeddings": [{"embeddingType": "VIDEO", "embedding": [...]}]}
                embedding = response_body['embeddings'][0]['embedding']

                processing_time_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    f"Generated Nova unified video embedding: {len(embedding)}D "
                    f"from {video_uri} with mode={embedding_mode}"
                )

                return NovaEmbeddingResult(
                    embedding=embedding,
                    input_type='video',
                    input_source=video_uri,
                    model_id=self.model_id,
                    embedding_dimension=len(embedding),
                    embedding_purpose=self.embedding_purpose,
                    processing_time_ms=processing_time_ms,
                    unified_space=True
                )

            except ClientError as e:
                self._handle_bedrock_error(e, "video embedding")

        else:
            # Use async API for segmented embeddings
            if not use_async:
                raise ValidationError(
                    "Segmented embeddings require use_async=True"
                )

            return self._generate_video_embedding_async(
                video_uri=video_uri,
                embedding_mode=embedding_mode,
                segment_duration_sec=segment_duration_sec
            )

    def generate_text_embedding(
        self,
        text: str,
        truncation_mode: TruncationMode = "END"
    ) -> NovaEmbeddingResult:
        """
        Generate unified embedding for text.

        The text embedding exists in the SAME semantic space as video, image,
        and audio embeddings, enabling cross-modal search.

        Args:
            text: Input text
            truncation_mode: How to truncate if too long ("END" or "START")

        Returns:
            NovaEmbeddingResult with text embedding in unified space
        """
        if not text or not text.strip():
            raise ValidationError("Text input cannot be empty")

        start_time = time.time()

        # Build Nova text embedding request (following AWS API format)
        request_body = {
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": self.embedding_purpose,
                "embeddingDimension": self.embedding_dimension,
                "text": {
                    "truncationMode": truncation_mode,
                    "value": text
                }
            }
        }

        try:
            def _invoke_nova():
                return self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(request_body)
                )

            response = AWSRetryHandler.retry_with_backoff(
                _invoke_nova,
                max_retries=3,
                operation_name=f"nova_text_embedding_{self.model_id}"
            )

            response_body = json.loads(response['body'].read())

            # Parse Nova response format
            embedding = response_body['embeddings'][0]['embedding']

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Generated Nova unified text embedding: {len(embedding)}D "
                f"(first 50 chars: {text[:50]}...)"
            )

            return NovaEmbeddingResult(
                embedding=embedding,
                input_type='text',
                input_source=text,
                model_id=self.model_id,
                embedding_dimension=len(embedding),
                embedding_purpose=self.embedding_purpose,
                processing_time_ms=processing_time_ms,
                unified_space=True
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "text embedding")

    def generate_image_embedding(
        self,
        image_uri: str
    ) -> NovaEmbeddingResult:
        """
        Generate unified embedding for image.

        Args:
            image_uri: S3 URI of image

        Returns:
            NovaEmbeddingResult with image embedding in unified space
        """
        if not self.model_info.supports_image:
            raise ValidationError(
                f"Model {self.model_id} does not support image embeddings."
            )

        start_time = time.time()

        request_body = {
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": self.embedding_purpose,
                "embeddingDimension": self.embedding_dimension,
                "image": {
                    "source": {
                        "s3Location": {"uri": image_uri}
                    }
                }
            }
        }

        try:
            def _invoke_nova():
                return self.bedrock_client.invoke_model(
                    modelId=self.model_id,
                    contentType='application/json',
                    accept='application/json',
                    body=json.dumps(request_body)
                )

            response = AWSRetryHandler.retry_with_backoff(
                _invoke_nova,
                max_retries=3,
                operation_name=f"nova_image_embedding_{self.model_id}"
            )

            response_body = json.loads(response['body'].read())
            embedding = response_body['embeddings'][0]['embedding']

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Generated Nova unified image embedding: {len(embedding)}D from {image_uri}"
            )

            return NovaEmbeddingResult(
                embedding=embedding,
                input_type='image',
                input_source=image_uri,
                model_id=self.model_id,
                embedding_dimension=len(embedding),
                embedding_purpose=self.embedding_purpose,
                processing_time_ms=processing_time_ms,
                unified_space=True
            )

        except ClientError as e:
            self._handle_bedrock_error(e, "image embedding")

    def _generate_video_embedding_async(
        self,
        video_uri: str,
        embedding_mode: VideoEmbeddingMode,
        segment_duration_sec: Optional[int] = None,
        timeout_sec: int = 1800
    ) -> NovaEmbeddingResult:
        """
        Generate video embeddings asynchronously with polling and retrieval.

        Uses Bedrock async invocation pattern:
        1. Submit async job
        2. Poll for completion
        3. Retrieve embeddings from S3 output
        4. Parse and return NovaEmbeddingResult

        Args:
            video_uri: S3 URI of video
            embedding_mode: AUDIO_VIDEO_COMBINED, AUDIO_ONLY, or VIDEO_ONLY
            segment_duration_sec: Optional segment duration (for SEGMENTED_EMBEDDING)
            timeout_sec: Max wait time for completion (default: 30 min)

        Returns:
            NovaEmbeddingResult with embeddings from S3 output
        """
        start_time = time.time()

        # Extract video format from URI
        video_format = "mp4"
        if video_uri.endswith('.webm'):
            video_format = "webm"
        elif video_uri.endswith('.mkv'):
            video_format = "mkv"
        elif video_uri.endswith('.avi'):
            video_format = "avi"
        elif video_uri.endswith('.mov'):
            video_format = "mov"

        # Build request based on whether segmentation is requested
        if segment_duration_sec:
            task_type = "SEGMENTED_EMBEDDING"
            request_body = {
                "taskType": task_type,
                "segmentedEmbeddingParams": {
                    "embeddingPurpose": self.embedding_purpose,
                    "embeddingDimension": self.embedding_dimension,
                    "video": {
                        "format": video_format,
                        "embeddingMode": embedding_mode,
                        "source": {"s3Location": {"uri": video_uri}},
                        "segmentationConfig": {"durationSeconds": segment_duration_sec}
                    }
                }
            }
        else:
            task_type = "SINGLE_EMBEDDING"
            request_body = {
                "taskType": task_type,
                "singleEmbeddingParams": {
                    "embeddingPurpose": self.embedding_purpose,
                    "embeddingDimension": self.embedding_dimension,
                    "video": {
                        "format": video_format,
                        "embeddingMode": embedding_mode,
                        "source": {"s3Location": {"uri": video_uri}}
                    }
                }
            }

        try:
            # Extract S3 output path from video URI
            bucket = video_uri.split('/')[2]
            output_s3_uri = f"s3://{bucket}/nova-embeddings/"

            # Submit async job
            response = self.bedrock_client.start_async_invoke(
                modelId=self.model_id,
                modelInput=request_body,
                outputDataConfig={
                    "s3OutputDataConfig": {
                        "s3Uri": output_s3_uri
                    }
                }
            )

            invocation_arn = response['invocationArn']

            logger.info(
                f"Started async Nova embedding: ARN={invocation_arn}, mode={embedding_mode}"
            )

            # Poll for completion
            poll_start = time.time()
            poll_interval = 30  # Poll every 30 seconds

            while time.time() - poll_start < timeout_sec:
                try:
                    status_response = self.bedrock_client.get_async_invoke(
                        invocationArn=invocation_arn
                    )

                    status = status_response.get('status', 'Unknown')

                    if status == 'Completed':
                        logger.info(f"Async job completed in {time.time() - poll_start:.1f}s")

                        # Retrieve embeddings from S3 output
                        output_location = status_response.get('outputDataConfig', {}).get('s3OutputDataConfig', {}).get('s3Uri', output_s3_uri)

                        embeddings = self._retrieve_embeddings_from_s3(output_location, invocation_arn)

                        processing_time_ms = int((time.time() - start_time) * 1000)

                        return NovaEmbeddingResult(
                            embedding=embeddings,
                            input_type='video',
                            input_source=video_uri,
                            model_id=self.model_id,
                            embedding_dimension=len(embeddings),
                            embedding_purpose=self.embedding_purpose,
                            processing_time_ms=processing_time_ms,
                            unified_space=True
                        )

                    elif status == 'Failed':
                        error_msg = status_response.get('failureMessage', 'Unknown error')
                        raise VectorEmbeddingError(f"Async job failed: {error_msg}")

                    # Still in progress, wait and retry
                    time.sleep(poll_interval)

                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        raise
                    # Job not found yet, wait and retry
                    time.sleep(poll_interval)

            raise VectorEmbeddingError(f"Async job timeout after {timeout_sec}s")

        except ClientError as e:
            self._handle_bedrock_error(e, "async video embedding")

    def _retrieve_embeddings_from_s3(self, s3_output_uri: str, invocation_arn: str) -> List[float]:
        """
        Retrieve Nova embeddings from S3 output location.

        Args:
            s3_output_uri: S3 URI where Bedrock wrote output
            invocation_arn: Invocation ARN to find specific output file

        Returns:
            List of embedding floats
        """
        import boto3

        try:
            s3_client = boto3.client('s3')

            # Parse S3 URI
            s3_parts = s3_output_uri.replace('s3://', '').split('/', 1)
            bucket = s3_parts[0]
            prefix = s3_parts[1] if len(s3_parts) > 1 else ''

            # Extract invocation ID from ARN
            invocation_id = invocation_arn.split('/')[-1]

            # List objects to find output file
            response = s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=f"{prefix}{invocation_id}"
            )

            if 'Contents' not in response or not response['Contents']:
                raise VectorEmbeddingError(f"No output found in {s3_output_uri} for {invocation_id}")

            # Get first output file (should be only one for single embedding)
            output_key = response['Contents'][0]['Key']

            # Download and parse
            obj_response = s3_client.get_object(Bucket=bucket, Key=output_key)
            output_data = json.loads(obj_response['Body'].read())

            # Parse Nova output format
            if 'embeddings' in output_data and len(output_data['embeddings']) > 0:
                embedding = output_data['embeddings'][0]['embedding']
            else:
                raise VectorEmbeddingError("Unexpected Nova output format")

            logger.info(f"Retrieved Nova embeddings from S3: {len(embedding)}D")

            return embedding

        except Exception as e:
            raise VectorEmbeddingError(f"Failed to retrieve embeddings from S3: {str(e)}")

    def _handle_bedrock_error(self, e: ClientError, operation: str) -> None:
        """Handle Bedrock API errors."""
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']

        if error_code == 'ValidationException':
            raise ValidationError(f"Nova {operation} validation error: {error_msg}")
        elif error_code in ['ThrottlingException', 'TooManyRequestsException']:
            raise ModelAccessError(f"Nova {operation} rate limit: {error_msg}")
        elif error_code == 'ResourceNotFoundException':
            raise ModelAccessError(f"Nova model not found in region {self.region_name}: {error_msg}")
        else:
            raise VectorEmbeddingError(f"Nova {operation} failed: {error_msg}")

    def get_model_info(self) -> NovaModelInfo:
        """Get information about the current Nova model."""
        return self.model_info

    @classmethod
    def list_supported_models(cls) -> Dict[str, NovaModelInfo]:
        """List all supported Nova models."""
        return cls.SUPPORTED_MODELS

    @classmethod
    def compare_with_marengo(cls) -> Dict[str, Any]:
        """
        Get comparison information between Nova and Marengo approaches.

        Returns:
            Dict with comparison metrics and use case recommendations
        """
        return {
            'nova': {
                'embedding_spaces': 1,
                'embedding_dimensions': [3072, 1024, 384, 256],
                'approach': 'Unified multi-modal space',
                'user_control': 'Choose embedding dimension and purpose',
                'modality_combination': 'Single combined embedding per input',
                'advantages': [
                    'Single query searches all content types',
                    'Simpler implementation',
                    'Lower storage requirements per item',
                    'Direct cross-modal comparison',
                    'Flexible dimension for cost/accuracy tradeoff'
                ],
                'use_cases': [
                    'General-purpose multi-modal search',
                    'Cross-modal retrieval (text->video, image->text)',
                    'Unified semantic understanding',
                    'Simplified architecture'
                ]
            },
            'marengo': {
                'embedding_spaces': 3,
                'embedding_dimensions': {
                    'visual-text': 1024,
                    'visual-image': 1024,
                    'audio': 1024
                },
                'approach': 'Task-specific embedding spaces',
                'user_control': 'Choose which embedding types to generate (visual-text, visual-image, audio)',
                'modality_combination': 'Separate embeddings per task type',
                'advantages': [
                    'Optimized for specific modalities',
                    'User selects which vectors to generate',
                    'Higher precision for domain-specific tasks',
                    'Fine-grained control over search',
                    'Task-specific tuning'
                ],
                'use_cases': [
                    'Specialized video analysis',
                    'Task-specific optimization',
                    'Domain-specific applications',
                    'Separate modality tracking'
                ]
            },
            'recommendation': {
                'nova_best_for': 'General multi-modal search, simplicity, unified semantics, cost optimization',
                'marengo_best_for': 'Specialized video tasks, fine-grained control, domain expertise, modality selection'
            }
        }
