"""
Amazon Nova Embedding Service

This service provides multi-modal embeddings using Amazon Nova models through Bedrock.
Nova embeddings use a SINGLE unified embedding space across all modalities (text, image,
video, audio), unlike Marengo which uses separate embedding spaces per modality.

Key Differences from Marengo:
- Nova: Single 1024D embedding space for all modalities
- Marengo: Separate embedding spaces (visual-text, visual-image, audio)
- Nova: Unified semantic search across all content types
- Marengo: Task-specific search with result fusion
"""

import json
import time
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from botocore.exceptions import ClientError

from src.config.unified_config_manager import get_unified_config_manager
from src.utils.aws_clients import aws_client_factory
from src.utils.aws_retry import AWSRetryHandler
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class NovaEmbeddingResult:
    """Result from Nova embedding generation - single unified embedding."""
    embedding: List[float]
    input_type: str  # 'text', 'image', 'video', 'audio'
    input_source: str  # URI or text content
    model_id: str
    embedding_dimension: int = 1024
    processing_time_ms: Optional[int] = None
    unified_space: bool = True  # Always True for Nova


@dataclass
class NovaModelInfo:
    """Information about Nova embedding models."""
    model_id: str
    dimensions: int
    max_input_tokens: int
    supports_video: bool
    supports_image: bool
    supports_audio: bool
    supports_text: bool
    cost_per_1k_tokens: float
    description: str


class NovaEmbeddingService:
    """
    Service for generating multi-modal embeddings using Amazon Nova models.

    Nova provides a unified embedding space across all modalities, enabling
    seamless cross-modal search (e.g., search videos with text queries).

    Example:
        service = NovaEmbeddingService()

        # Generate video embedding (unified space)
        video_result = service.generate_video_embedding(
            video_uri="s3://bucket/video.mp4",
            modalities=['visual', 'audio', 'text']
        )

        # Generate text embedding (same unified space)
        text_result = service.generate_text_embedding("sunset over mountains")

        # These embeddings can be directly compared via cosine similarity
        # because they exist in the same semantic space
    """

    # Nova embedding models
    SUPPORTED_MODELS = {
        'amazon.nova-embed-v1': NovaModelInfo(
            model_id='amazon.nova-embed-v1',
            dimensions=1024,
            max_input_tokens=8192,
            supports_video=True,
            supports_image=True,
            supports_audio=True,
            supports_text=True,
            cost_per_1k_tokens=0.0002,
            description='Amazon Nova Embeddings V1 - Unified multi-modal embedding space'
        ),
        'amazon.nova-embed-text-v1': NovaModelInfo(
            model_id='amazon.nova-embed-text-v1',
            dimensions=1024,
            max_input_tokens=8192,
            supports_video=False,
            supports_image=False,
            supports_audio=False,
            supports_text=True,
            cost_per_1k_tokens=0.0001,
            description='Amazon Nova Text Embeddings V1 - Text-only variant'
        )
    }

    def __init__(self, model_id: str = 'amazon.nova-embed-v1'):
        """
        Initialize Nova embedding service.

        Args:
            model_id: Nova model ID (default: amazon.nova-embed-v1)
        """
        self.bedrock_client = aws_client_factory.get_bedrock_runtime_client()
        self.model_id = model_id

        # Validate model
        if model_id not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported Nova model: {model_id}. "
                f"Supported models: {list(self.SUPPORTED_MODELS.keys())}"
            )

        self.model_info = self.SUPPORTED_MODELS[model_id]

        config_manager = get_unified_config_manager()
        self.config = {
            'region': config_manager.config.aws.region,
            'model_id': model_id
        }

        logger.info(
            f"Initialized Nova embedding service with model {model_id} "
            f"(unified {self.model_info.dimensions}D space)"
        )

    def generate_video_embedding(
        self,
        video_uri: str,
        modalities: Optional[List[str]] = None,
        start_time_sec: Optional[float] = None,
        end_time_sec: Optional[float] = None
    ) -> NovaEmbeddingResult:
        """
        Generate unified embedding for video content.

        Unlike Marengo (which generates separate embeddings per modality),
        Nova generates a SINGLE embedding that captures all modalities in
        a unified semantic space.

        Args:
            video_uri: S3 URI or URL of video
            modalities: Modalities to include (default: all)
            start_time_sec: Optional start time for clip
            end_time_sec: Optional end time for clip

        Returns:
            NovaEmbeddingResult with single unified embedding
        """
        if not self.model_info.supports_video:
            raise ValidationError(
                f"Model {self.model_id} does not support video embeddings. "
                f"Use amazon.nova-embed-v1 instead."
            )

        modalities = modalities or ['visual', 'audio', 'text']
        start_time = time.time()

        # Build Nova video embedding request
        request_body = {
            'inputVideo': {
                'source': video_uri
            },
            'modalities': modalities,
            'embeddingConfig': {
                'outputDimensions': self.model_info.dimensions
            }
        }

        if start_time_sec is not None:
            request_body['inputVideo']['startTime'] = start_time_sec
        if end_time_sec is not None:
            request_body['inputVideo']['endTime'] = end_time_sec

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

            # Nova returns single unified embedding
            embedding = response_body.get('embedding', [])

            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Generated Nova unified video embedding: {len(embedding)}D "
                f"from {video_uri} with modalities {modalities}"
            )

            return NovaEmbeddingResult(
                embedding=embedding,
                input_type='video',
                input_source=video_uri,
                model_id=self.model_id,
                embedding_dimension=len(embedding),
                processing_time_ms=processing_time_ms,
                unified_space=True
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']

            if error_code == 'ValidationException':
                raise ValidationError(f"Nova validation error: {error_msg}")
            elif error_code in ['ThrottlingException', 'TooManyRequestsException']:
                raise ModelAccessError(f"Nova rate limit: {error_msg}")
            else:
                raise VectorEmbeddingError(f"Nova embedding failed: {error_msg}")

    def generate_text_embedding(
        self,
        text: str,
        normalize: bool = True
    ) -> NovaEmbeddingResult:
        """
        Generate unified embedding for text.

        The text embedding exists in the SAME semantic space as video, image,
        and audio embeddings, enabling cross-modal search.

        Args:
            text: Input text
            normalize: Whether to normalize embedding (default: True)

        Returns:
            NovaEmbeddingResult with text embedding in unified space
        """
        if not text or not text.strip():
            raise ValidationError("Text input cannot be empty")

        start_time = time.time()

        # Build Nova text embedding request
        request_body = {
            'inputText': text,
            'embeddingConfig': {
                'outputDimensions': self.model_info.dimensions
            }
        }

        if normalize:
            request_body['embeddingConfig']['normalize'] = True

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
            embedding = response_body.get('embedding', [])

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
                processing_time_ms=processing_time_ms,
                unified_space=True
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']

            if error_code == 'ValidationException':
                raise ValidationError(f"Nova validation error: {error_msg}")
            elif error_code in ['ThrottlingException', 'TooManyRequestsException']:
                raise ModelAccessError(f"Nova rate limit: {error_msg}")
            else:
                raise VectorEmbeddingError(f"Nova embedding failed: {error_msg}")

    def generate_image_embedding(
        self,
        image_uri: str
    ) -> NovaEmbeddingResult:
        """
        Generate unified embedding for image.

        Args:
            image_uri: S3 URI or URL of image

        Returns:
            NovaEmbeddingResult with image embedding in unified space
        """
        if not self.model_info.supports_image:
            raise ValidationError(
                f"Model {self.model_id} does not support image embeddings. "
                f"Use amazon.nova-embed-v1 instead."
            )

        start_time = time.time()

        request_body = {
            'inputImage': {
                'source': image_uri
            },
            'embeddingConfig': {
                'outputDimensions': self.model_info.dimensions
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
            embedding = response_body.get('embedding', [])

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
                processing_time_ms=processing_time_ms,
                unified_space=True
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']

            if error_code == 'ValidationException':
                raise ValidationError(f"Nova validation error: {error_msg}")
            elif error_code in ['ThrottlingException', 'TooManyRequestsException']:
                raise ModelAccessError(f"Nova rate limit: {error_msg}")
            else:
                raise VectorEmbeddingError(f"Nova embedding failed: {error_msg}")

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
                'embedding_dimension': 1024,
                'approach': 'Unified multi-modal space',
                'advantages': [
                    'Single query searches all content types',
                    'Simpler implementation',
                    'Lower storage requirements',
                    'Direct cross-modal comparison'
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
                'advantages': [
                    'Optimized for specific modalities',
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
                'nova_best_for': 'General multi-modal search, simplicity, unified semantics',
                'marengo_best_for': 'Specialized video tasks, fine-grained control, domain expertise'
            }
        }
