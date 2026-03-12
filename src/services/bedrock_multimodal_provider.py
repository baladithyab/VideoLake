"""
AWS Bedrock Multi-Modal Embedding Provider

Supports embedding generation for text, image, audio, and video using AWS Bedrock models:
- Text: amazon.titan-embed-text-v2:0, cohere.embed-english-v3, cohere.embed-multilingual-v3
- Image: amazon.titan-embed-image-v1
- Multimodal: amazon.nova-canvas-v1:0 (text+image+video+audio unified space)
- Video: twelvelabs.marengo-embed-2-7-v1:0, amazon.nova-canvas-v1:0

Uses asyncio.to_thread to wrap blocking boto3 calls and prevent event loop blocking.
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
import base64

from src.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingProviderType,
    ModalityType,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingModelInfo,
    register_embedding_provider
)
from src.utils.aws_clients import aws_client_factory
from src.utils.logging_config import get_logger
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError

logger = get_logger(__name__)


@register_embedding_provider("bedrock")
class BedrockMultiModalProvider(EmbeddingProvider):
    """AWS Bedrock embedding provider for multi-modal content."""

    # Model registry with capabilities
    MODELS = {
        # Text models
        "amazon.titan-embed-text-v2:0": EmbeddingModelInfo(
            model_id="amazon.titan-embed-text-v2:0",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description="Amazon Titan Text Embeddings V2 - Multilingual, configurable dimensions"
        ),
        "amazon.titan-embed-text-v1": EmbeddingModelInfo(
            model_id="amazon.titan-embed-text-v1",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1536,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description="Amazon Titan Text Embeddings G1 - Original Titan text model"
        ),
        "cohere.embed-english-v3": EmbeddingModelInfo(
            model_id="cohere.embed-english-v3",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=2048,
            supports_batch=True,
            cost_per_1k_tokens=0.0001,
            description="Cohere Embed English V3 - English optimized with batch support"
        ),
        "cohere.embed-multilingual-v3": EmbeddingModelInfo(
            model_id="cohere.embed-multilingual-v3",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=2048,
            supports_batch=True,
            cost_per_1k_tokens=0.0001,
            description="Cohere Embed Multilingual V3 - 100+ languages with batch support"
        ),
        # Multimodal models
        "amazon.titan-embed-image-v1": EmbeddingModelInfo(
            model_id="amazon.titan-embed-image-v1",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT, ModalityType.IMAGE, ModalityType.MULTIMODAL],
            dimensions=1024,
            max_input_tokens=8192,
            max_input_size_mb=5,
            supports_batch=False,
            cost_per_1k_tokens=0.0008,
            cost_per_unit=0.008,  # Per image
            description="Amazon Titan Multimodal Embeddings G1 - Text and image support"
        ),
        "amazon.nova-canvas-v1:0": EmbeddingModelInfo(
            model_id="amazon.nova-canvas-v1:0",
            provider="bedrock",
            supported_modalities=[ModalityType.TEXT, ModalityType.IMAGE, ModalityType.AUDIO,
                                 ModalityType.VIDEO, ModalityType.MULTIMODAL],
            dimensions=1024,
            max_input_tokens=8000,
            max_input_size_mb=100,  # For video
            supports_batch=False,
            cost_per_1k_tokens=0.0002,
            description="Amazon Nova Canvas - Unified multimodal embeddings (text+image+audio+video)"
        ),
        # Video-specific models
        "twelvelabs.marengo-embed-2-7-v1:0": EmbeddingModelInfo(
            model_id="twelvelabs.marengo-embed-2-7-v1:0",
            provider="bedrock",
            supported_modalities=[ModalityType.VIDEO, ModalityType.AUDIO],
            dimensions=1024,
            max_input_size_mb=500,  # 30 min video
            supports_batch=False,
            cost_per_unit=0.042,  # ~$0.0007 per second
            description="TwelveLabs Marengo 2.7 - Multi-vector video (visual-text, visual-image, audio)"
        ),
    }

    # Default model selection per modality
    DEFAULT_MODELS = {
        ModalityType.TEXT: "amazon.titan-embed-text-v2:0",
        ModalityType.IMAGE: "amazon.titan-embed-image-v1",
        ModalityType.AUDIO: "amazon.nova-canvas-v1:0",
        ModalityType.VIDEO: "amazon.nova-canvas-v1:0",
        ModalityType.MULTIMODAL: "amazon.nova-canvas-v1:0",
    }

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize Bedrock provider.

        Args:
            region_name: AWS region for Bedrock API
        """
        self.region_name = region_name
        self._bedrock_runtime = None

    @property
    def bedrock_runtime(self):
        """Lazy-load Bedrock runtime client."""
        if self._bedrock_runtime is None:
            self._bedrock_runtime = aws_client_factory.get_bedrock_runtime_client(
                region_name=self.region_name
            )
        return self._bedrock_runtime

    @property
    def provider_type(self) -> EmbeddingProviderType:
        """Return provider type."""
        return EmbeddingProviderType.BEDROCK

    def get_supported_modalities(self) -> List[ModalityType]:
        """Return all supported modalities."""
        return [
            ModalityType.TEXT,
            ModalityType.IMAGE,
            ModalityType.AUDIO,
            ModalityType.VIDEO,
            ModalityType.MULTIMODAL
        ]

    def get_available_models(self) -> List[EmbeddingModelInfo]:
        """Return list of available Bedrock models."""
        return list(self.MODELS.values())

    def get_default_model(self, modality: ModalityType) -> Optional[str]:
        """Get default model for a modality."""
        return self.DEFAULT_MODELS.get(modality)

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding for a single input.

        Args:
            request: Embedding request

        Returns:
            EmbeddingResponse with embedding and metadata
        """
        # Validate request
        self.validate_request(request)

        # Select model
        model_id = request.model_id or self.get_default_model(request.modality)
        if not model_id:
            raise ValueError(f"No model available for modality: {request.modality.value}")

        model_info = self.MODELS.get(model_id)
        if not model_info:
            raise ValueError(f"Unknown model: {model_id}")

        # Route to appropriate handler based on model family
        start_time = time.time()

        try:
            if model_id.startswith("amazon.titan-embed-text"):
                embedding = await self._generate_titan_text_embedding(request.content, model_id)
            elif model_id.startswith("cohere.embed"):
                embedding = await self._generate_cohere_embedding(request.content, model_id)
            elif model_id == "amazon.titan-embed-image-v1":
                embedding = await self._generate_titan_multimodal_embedding(request, model_id)
            elif model_id == "amazon.nova-canvas-v1:0":
                embedding = await self._generate_nova_embedding(request, model_id)
            elif model_id.startswith("twelvelabs.marengo"):
                embedding = await self._generate_marengo_embedding(request, model_id)
            else:
                raise VectorEmbeddingError(
                    f"Unsupported model: {model_id}",
                    error_code="UNSUPPORTED_MODEL"
                )

            processing_time_ms = int((time.time() - start_time) * 1000)

            # Build response
            response = EmbeddingResponse(
                embedding=embedding,
                modality=request.modality,
                model_id=model_id,
                provider="bedrock",
                dimensions=len(embedding),
                processing_time_ms=processing_time_ms,
                cost_estimate=self.estimate_cost(request),
                metadata={
                    "region": self.region_name,
                    "normalized": request.normalize
                }
            )

            logger.info(
                f"Generated {request.modality.value} embedding using {model_id} "
                f"({processing_time_ms}ms)"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to generate embedding with {model_id}: {str(e)}")
            raise

    async def batch_generate_embeddings(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple inputs.

        Uses native batch API for Cohere models, concurrent processing for others.
        """
        if not requests:
            raise ValidationError("Requests list cannot be empty", error_code="EMPTY_REQUESTS")

        # Group requests by model
        requests_by_model: Dict[str, List[EmbeddingRequest]] = {}
        for req in requests:
            model_id = req.model_id or self.get_default_model(req.modality)
            if not model_id:
                raise ValueError(f"No model for modality: {req.modality.value}")

            if model_id not in requests_by_model:
                requests_by_model[model_id] = []
            requests_by_model[model_id].append(req)

        # Process each model group
        all_responses = []

        for model_id, model_requests in requests_by_model.items():
            model_info = self.MODELS.get(model_id)

            if model_info and model_info.supports_batch and model_id.startswith("cohere"):
                # Use Cohere native batch API
                responses = await self._batch_generate_cohere_embeddings(model_requests, model_id)
            else:
                # Concurrent individual requests
                responses = await self._concurrent_generate_embeddings(model_requests)

            all_responses.extend(responses)

        logger.info(f"Generated {len(all_responses)} embeddings in batch")
        return all_responses

    def validate_connectivity(self) -> Dict[str, Any]:
        """Validate connectivity to Bedrock."""
        try:
            # Test with a simple embedding call
            test_request = EmbeddingRequest(
                modality=ModalityType.TEXT,
                content="test",
                model_id="amazon.titan-embed-text-v2:0"
            )

            start_time = time.time()

            # Run synchronously for connectivity check
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.generate_embedding(test_request))
            finally:
                loop.close()

            response_time_ms = (time.time() - start_time) * 1000

            return {
                "accessible": True,
                "models_available": list(self.MODELS.keys()),
                "response_time_ms": response_time_ms,
                "region": self.region_name,
                "error_message": None
            }

        except Exception as e:
            logger.error(f"Bedrock connectivity check failed: {str(e)}")
            return {
                "accessible": False,
                "models_available": [],
                "response_time_ms": 0,
                "region": self.region_name,
                "error_message": str(e)
            }

    # Private helper methods for model-specific logic

    async def _generate_titan_text_embedding(
        self,
        text: str,
        model_id: str
    ) -> List[float]:
        """Generate text embedding using Titan models."""
        if not isinstance(text, str):
            raise ValueError("Text content must be a string")

        def _invoke():
            if model_id == "amazon.titan-embed-text-v2:0":
                body = {
                    "inputText": text,
                    "dimensions": 1024,
                    "normalize": True,
                    "embeddingTypes": ["float"]
                }
            else:  # v1
                body = {"inputText": text}

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())

            # Handle different response formats
            if model_id == "amazon.titan-embed-text-v2:0":
                if "embeddingsByType" in result:
                    return result["embeddingsByType"]["float"]
                return result["embedding"]
            else:
                return result["embedding"]

        # Wrap blocking boto3 call in thread
        return await asyncio.to_thread(_invoke)

    async def _generate_cohere_embedding(
        self,
        text: str,
        model_id: str
    ) -> List[float]:
        """Generate text embedding using Cohere models."""
        if not isinstance(text, str):
            raise ValueError("Text content must be a string")

        def _invoke():
            body = {
                "texts": [text],
                "input_type": "search_document",
                "embedding_types": ["float"]
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())
            return result["embeddings"]["float"][0]

        return await asyncio.to_thread(_invoke)

    async def _generate_titan_multimodal_embedding(
        self,
        request: EmbeddingRequest,
        model_id: str
    ) -> List[float]:
        """Generate embedding using Titan Multimodal model."""
        def _invoke():
            body = {}

            if request.modality == ModalityType.TEXT:
                body["inputText"] = request.content
            elif request.modality == ModalityType.IMAGE:
                # Expect base64-encoded image or S3 URI
                if isinstance(request.content, str):
                    if request.content.startswith("s3://"):
                        body["inputImage"] = request.content
                    else:
                        body["inputImage"] = request.content  # Assume base64
                else:
                    # Binary data - encode to base64
                    body["inputImage"] = base64.b64encode(request.content).decode()
            elif request.modality == ModalityType.MULTIMODAL:
                # Support both text and image
                if isinstance(request.content, dict):
                    body["inputText"] = request.content.get("text", "")
                    body["inputImage"] = request.content.get("image", "")

            body["embeddingConfig"] = {"outputEmbeddingLength": 1024}

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())
            return result["embedding"]

        return await asyncio.to_thread(_invoke)

    async def _generate_nova_embedding(
        self,
        request: EmbeddingRequest,
        model_id: str
    ) -> List[float]:
        """Generate embedding using Amazon Nova Canvas."""
        def _invoke():
            body = {}

            if request.modality == ModalityType.TEXT:
                body["inputText"] = request.content
            elif request.modality == ModalityType.IMAGE:
                body["inputImage"] = request.content  # S3 URI or base64
            elif request.modality == ModalityType.AUDIO:
                body["inputAudio"] = request.content  # S3 URI
            elif request.modality == ModalityType.VIDEO:
                body["inputVideo"] = request.content  # S3 URI
                if request.embedding_mode:
                    body["embeddingConfig"] = {
                        "embeddingMode": request.embedding_mode,
                        "outputEmbeddingLength": request.dimensions or 1024
                    }

            if "embeddingConfig" not in body:
                body["embeddingConfig"] = {
                    "outputEmbeddingLength": request.dimensions or 1024
                }

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())
            return result["embedding"]

        return await asyncio.to_thread(_invoke)

    async def _generate_marengo_embedding(
        self,
        request: EmbeddingRequest,
        model_id: str
    ) -> List[float]:
        """Generate embedding using TwelveLabs Marengo (returns first vector)."""
        def _invoke():
            body = {
                "videoUri": request.content,  # S3 URI
                "embeddingOptions": request.metadata.get(
                    "embedding_options",
                    ["visual-text"]
                ),
                "segmentDuration": request.video_segment_duration or 5
            }

            response = self.bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            result = json.loads(response["body"].read())
            # Marengo returns multiple vectors - use first one
            # In production, might want to return all vectors
            vectors = result.get("embeddings", [])
            if not vectors:
                raise VectorEmbeddingError("No embeddings returned from Marengo")
            return vectors[0]["embedding"]

        return await asyncio.to_thread(_invoke)

    async def _batch_generate_cohere_embeddings(
        self,
        requests: List[EmbeddingRequest],
        model_id: str
    ) -> List[EmbeddingResponse]:
        """Generate embeddings using Cohere batch API."""
        # Cohere supports up to 96 texts per call
        batch_size = 96
        responses = []

        for i in range(0, len(requests), batch_size):
            batch = requests[i:i + batch_size]
            texts = [req.content for req in batch]

            def _invoke():
                body = {
                    "texts": texts,
                    "input_type": "search_document",
                    "embedding_types": ["float"]
                }

                response = self.bedrock_runtime.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json"
                )

                result = json.loads(response["body"].read())
                return result["embeddings"]["float"]

            start_time = time.time()
            embeddings = await asyncio.to_thread(_invoke)
            processing_time_ms = int((time.time() - start_time) * 1000)

            for j, embedding in enumerate(embeddings):
                responses.append(
                    EmbeddingResponse(
                        embedding=embedding,
                        modality=batch[j].modality,
                        model_id=model_id,
                        provider="bedrock",
                        dimensions=len(embedding),
                        processing_time_ms=processing_time_ms // len(embeddings),
                        cost_estimate=self.estimate_cost(batch[j])
                    )
                )

        return responses

    async def _concurrent_generate_embeddings(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResponse]:
        """Generate embeddings concurrently for non-batch models."""
        tasks = [self.generate_embedding(req) for req in requests]
        return await asyncio.gather(*tasks)
