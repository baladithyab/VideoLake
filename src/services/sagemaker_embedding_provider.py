"""
AWS SageMaker Embedding Provider

Supports embedding generation using models deployed to SageMaker endpoints
(Marketplace, JumpStart, or custom models). Handles:
- Text embeddings: Voyage Code, Jina Embeddings V3, E5-large, BGE-M3
- Multimodal embeddings: Jina CLIP v2
- Custom endpoint inference with flexible payload formats

Uses asyncio.to_thread to wrap blocking boto3 calls and prevent event loop blocking.
"""

import asyncio
import json
import time
from typing import Any

from src.exceptions import ValidationError, VectorEmbeddingError
from src.services.embedding_provider import (
    EmbeddingModelInfo,
    EmbeddingProvider,
    EmbeddingProviderType,
    EmbeddingRequest,
    EmbeddingResponse,
    ModalityType,
    register_embedding_provider,
)
from src.utils.aws_clients import aws_client_factory
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@register_embedding_provider("sagemaker")
class SageMakerEmbeddingProvider(EmbeddingProvider):
    """SageMaker endpoint embedding provider for Marketplace/JumpStart models."""

    # Known model configurations (can be extended)
    KNOWN_MODELS = {
        "voyage-code-2": EmbeddingModelInfo(
            model_id="voyage-code-2",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1536,
            max_input_tokens=16000,
            supports_batch=False,
            cost_per_1k_tokens=0.0002,
            description="Voyage Code 2 - Code search and technical documentation (ml.g5.xlarge)"
        ),
        "voyage-large-2-instruct": EmbeddingModelInfo(
            model_id="voyage-large-2-instruct",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1536,
            max_input_tokens=16000,
            supports_batch=False,
            cost_per_1k_tokens=0.0002,
            description="Voyage Large 2 Instruct - Instruction-following RAG (ml.g5.xlarge)"
        ),
        "jina-embeddings-v3": EmbeddingModelInfo(
            model_id="jina-embeddings-v3",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=True,
            cost_per_1k_tokens=0.00015,
            description="Jina Embeddings V3 - RAG, search, classification (ml.g5.xlarge)"
        ),
        "jina-clip-v2": EmbeddingModelInfo(
            model_id="jina-clip-v2",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT, ModalityType.IMAGE, ModalityType.MULTIMODAL],
            dimensions=1024,
            max_input_tokens=8000,
            max_input_size_mb=5,
            supports_batch=False,
            cost_per_1k_tokens=0.0002,
            description="Jina CLIP v2 - Multimodal text-image matching (ml.g5.xlarge)"
        ),
        "bge-m3": EmbeddingModelInfo(
            model_id="bge-m3",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description="BGE-M3 - Multilingual hybrid search (ml.g5.2xlarge)"
        ),
        "bge-large-en-v1.5": EmbeddingModelInfo(
            model_id="bge-large-en-v1.5",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=512,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description="BGE Large EN v1.5 - English optimized (ml.g5.2xlarge)"
        ),
        "e5-large-v2": EmbeddingModelInfo(
            model_id="e5-large-v2",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=1024,
            max_input_tokens=512,
            supports_batch=False,
            cost_per_1k_tokens=0.0,  # Free model license
            description="E5-large-v2 - Semantic search (ml.g5.xlarge, JumpStart)"
        ),
        "e5-mistral-7b-instruct": EmbeddingModelInfo(
            model_id="e5-mistral-7b-instruct",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=4096,
            max_input_tokens=32768,
            supports_batch=False,
            cost_per_1k_tokens=0.0,  # Free model license
            description="E5 Mistral 7B Instruct - LLM-based embeddings with 32K context (ml.g5.2xlarge, JumpStart)"
        ),
        "all-mpnet-base-v2": EmbeddingModelInfo(
            model_id="all-mpnet-base-v2",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=768,
            max_input_tokens=384,
            supports_batch=False,
            cost_per_1k_tokens=0.0,  # Free model license
            description="Sentence Transformers - General purpose (ml.g4dn.xlarge, JumpStart)"
        ),
        "all-minilm-l6-v2": EmbeddingModelInfo(
            model_id="all-minilm-l6-v2",
            provider="sagemaker",
            supported_modalities=[ModalityType.TEXT],
            dimensions=384,
            max_input_tokens=256,
            supports_batch=False,
            cost_per_1k_tokens=0.0,  # Free model license
            description="Sentence Transformers - High throughput (ml.g4dn.xlarge, JumpStart)"
        ),
    }

    # Default model per modality
    DEFAULT_MODELS = {
        ModalityType.TEXT: "jina-embeddings-v3",
        ModalityType.IMAGE: "jina-clip-v2",
        ModalityType.MULTIMODAL: "jina-clip-v2",
    }

    def __init__(
        self,
        endpoint_mapping: dict[str, str] | None = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialize SageMaker provider.

        Args:
            endpoint_mapping: Map of model_id -> endpoint_name
                Example: {"voyage-code-2": "voyage-code-2-endpoint"}
            region_name: AWS region for SageMaker
        """
        self.endpoint_mapping = endpoint_mapping or {}
        self.region_name = region_name
        self._runtime = None

    @property
    def runtime(self):
        """Lazy-load SageMaker runtime client."""
        if self._runtime is None:
            self._runtime = aws_client_factory.get_sagemaker_runtime_client(
                region_name=self.region_name
            )
        return self._runtime

    @property
    def provider_type(self) -> EmbeddingProviderType:
        """Return provider type."""
        return EmbeddingProviderType.SAGEMAKER

    def get_supported_modalities(self) -> list[ModalityType]:
        """Return all supported modalities."""
        modalities = set()
        for model in self.KNOWN_MODELS.values():
            modalities.update(model.supported_modalities)
        return list(modalities)

    def get_available_models(self) -> list[EmbeddingModelInfo]:
        """Return list of known SageMaker models."""
        # Only return models that have endpoint mappings configured
        if self.endpoint_mapping:
            return [
                model_info for model_id, model_info in self.KNOWN_MODELS.items()
                if model_id in self.endpoint_mapping
            ]
        return list(self.KNOWN_MODELS.values())

    def get_default_model(self, modality: ModalityType) -> str | None:
        """Get default model for a modality."""
        default = self.DEFAULT_MODELS.get(modality)
        # Only return if endpoint is configured
        if default and default in self.endpoint_mapping:
            return default
        # Fallback to first available model for this modality
        for model_id, model_info in self.KNOWN_MODELS.items():
            if modality in model_info.supported_modalities and model_id in self.endpoint_mapping:
                return model_id
        return None

    def register_endpoint(self, model_id: str, endpoint_name: str):
        """
        Register a SageMaker endpoint for a model.

        Args:
            model_id: Model identifier
            endpoint_name: SageMaker endpoint name
        """
        self.endpoint_mapping[model_id] = endpoint_name
        logger.info(f"Registered SageMaker endpoint: {model_id} -> {endpoint_name}")

    def get_endpoint_name(self, model_id: str) -> str:
        """
        Get endpoint name for a model.

        Args:
            model_id: Model identifier

        Returns:
            Endpoint name

        Raises:
            ValueError: If no endpoint registered for model
        """
        if model_id not in self.endpoint_mapping:
            raise ValueError(
                f"No endpoint registered for model: {model_id}. "
                f"Use register_endpoint() or pass endpoint_mapping on init. "
                f"Available: {list(self.endpoint_mapping.keys())}"
            )
        return self.endpoint_mapping[model_id]

    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding using SageMaker endpoint.

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

        # Get endpoint
        endpoint_name = self.get_endpoint_name(model_id)

        # Build payload based on model type
        start_time = time.time()

        try:
            embedding = await self._invoke_endpoint(
                endpoint_name=endpoint_name,
                model_id=model_id,
                request=request
            )

            processing_time_ms = int((time.time() - start_time) * 1000)

            response = EmbeddingResponse(
                embedding=embedding,
                modality=request.modality,
                model_id=model_id,
                provider="sagemaker",
                dimensions=len(embedding),
                processing_time_ms=processing_time_ms,
                cost_estimate=self.estimate_cost(request),
                metadata={
                    "endpoint_name": endpoint_name,
                    "region": self.region_name
                }
            )

            logger.info(
                f"Generated {request.modality.value} embedding using {model_id} "
                f"at {endpoint_name} ({processing_time_ms}ms)"
            )

            return response

        except Exception as e:
            logger.error(f"Failed to generate embedding with {model_id}: {str(e)}")
            raise

    async def batch_generate_embeddings(
        self,
        requests: list[EmbeddingRequest]
    ) -> list[EmbeddingResponse]:
        """
        Generate embeddings for multiple inputs.

        Uses concurrent processing since most SageMaker models don't support
        native batch APIs.
        """
        if not requests:
            raise ValidationError("Requests list cannot be empty", error_code="EMPTY_REQUESTS")

        # Group by model for efficiency
        requests_by_model: dict[str, list[EmbeddingRequest]] = {}
        for req in requests:
            model_id = req.model_id or self.get_default_model(req.modality)
            if not model_id:
                raise ValueError(f"No model for modality: {req.modality.value}")

            if model_id not in requests_by_model:
                requests_by_model[model_id] = []
            requests_by_model[model_id].append(req)

        # Process concurrently
        all_responses = []
        for model_id, model_requests in requests_by_model.items():
            model_info = self.KNOWN_MODELS.get(model_id)

            if model_info and model_info.supports_batch:
                # Use native batch if supported (e.g., Jina Embeddings V3)
                responses = await self._batch_invoke_endpoint(model_requests, model_id)
            else:
                # Concurrent individual requests
                tasks = [self.generate_embedding(req) for req in model_requests]
                responses = await asyncio.gather(*tasks)

            all_responses.extend(responses)

        logger.info(f"Generated {len(all_responses)} embeddings in batch")
        return all_responses

    def validate_connectivity(self) -> dict[str, Any]:
        """Validate connectivity to SageMaker endpoints."""
        accessible_endpoints = []
        failed_endpoints = []
        total_response_time = 0

        for model_id, endpoint_name in self.endpoint_mapping.items():
            try:
                start_time = time.time()

                # Test with a simple synchronous request directly to SageMaker
                # Avoid creating event loops - use direct boto3 call
                test_payload = {"text": "test"}

                response = self.runtime.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType="application/json",
                    Body=json.dumps(test_payload)
                )

                # Read response to ensure endpoint is working
                _ = json.loads(response["Body"].read().decode())

                response_time = (time.time() - start_time) * 1000
                total_response_time += response_time

                accessible_endpoints.append({
                    "model_id": model_id,
                    "endpoint_name": endpoint_name,
                    "response_time_ms": response_time
                })

            except Exception as e:
                logger.warning(f"Endpoint {endpoint_name} not accessible: {str(e)}")
                failed_endpoints.append({
                    "model_id": model_id,
                    "endpoint_name": endpoint_name,
                    "error": str(e)
                })

        accessible = len(accessible_endpoints) > 0
        avg_response_time = (
            total_response_time / len(accessible_endpoints)
            if accessible_endpoints else 0
        )

        return {
            "accessible": accessible,
            "models_available": [ep["model_id"] for ep in accessible_endpoints],
            "response_time_ms": avg_response_time,
            "region": self.region_name,
            "accessible_endpoints": accessible_endpoints,
            "failed_endpoints": failed_endpoints,
            "error_message": (
                f"{len(failed_endpoints)} endpoints failed"
                if failed_endpoints else None
            )
        }

    # Private helper methods

    async def _invoke_endpoint(
        self,
        endpoint_name: str,
        model_id: str,
        request: EmbeddingRequest
    ) -> list[float]:
        """Invoke SageMaker endpoint with appropriate payload format."""

        def _invoke():
            # Build payload based on model family
            if model_id.startswith("voyage"):
                payload = self._build_voyage_payload(request)
            elif model_id.startswith("jina"):
                payload = self._build_jina_payload(request, model_id)
            elif model_id.startswith("bge"):
                payload = self._build_bge_payload(request)
            elif model_id.startswith("e5") or model_id.startswith("all-"):
                payload = self._build_sentence_transformers_payload(request)
            else:
                # Generic format
                payload = {"text": request.content}

            response = self.runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )

            result = json.loads(response["Body"].read().decode())

            # Extract embedding from response
            return self._extract_embedding(result, model_id)

        return await asyncio.to_thread(_invoke)

    async def _batch_invoke_endpoint(
        self,
        requests: list[EmbeddingRequest],
        model_id: str
    ) -> list[EmbeddingResponse]:
        """Batch invoke for models supporting native batch."""
        endpoint_name = self.get_endpoint_name(model_id)

        def _invoke():
            # Build batch payload (model-specific)
            if model_id == "jina-embeddings-v3":
                payload = {
                    "texts": [req.content for req in requests],
                    "task": "retrieval.passage"
                }
            else:
                # Fallback to generic batch format
                payload = {"texts": [req.content for req in requests]}

            response = self.runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType="application/json",
                Body=json.dumps(payload)
            )

            result = json.loads(response["Body"].read().decode())
            return result.get("embeddings", [])

        start_time = time.time()
        embeddings = await asyncio.to_thread(_invoke)
        processing_time_ms = int((time.time() - start_time) * 1000)

        responses = []
        for i, embedding in enumerate(embeddings):
            responses.append(
                EmbeddingResponse(
                    embedding=embedding,
                    modality=requests[i].modality,
                    model_id=model_id,
                    provider="sagemaker",
                    dimensions=len(embedding),
                    processing_time_ms=processing_time_ms // len(embeddings),
                    cost_estimate=self.estimate_cost(requests[i]),
                    metadata={"endpoint_name": endpoint_name}
                )
            )

        return responses

    def _build_voyage_payload(self, request: EmbeddingRequest) -> dict[str, Any]:
        """Build payload for Voyage models."""
        return {
            "input": request.content,
            "input_type": "document"  # or "query"
        }

    def _build_jina_payload(self, request: EmbeddingRequest, model_id: str) -> dict[str, Any]:
        """Build payload for Jina models."""
        if model_id == "jina-clip-v2" and request.modality != ModalityType.TEXT:
            # Multimodal - include image
            return {
                "text": request.content if request.modality == ModalityType.TEXT else "",
                "image": request.content if request.modality == ModalityType.IMAGE else ""
            }
        else:
            # Text-only
            return {
                "text": request.content,
                "task": "retrieval.passage"
            }

    def _build_bge_payload(self, request: EmbeddingRequest) -> dict[str, Any]:
        """Build payload for BGE models."""
        return {
            "text": request.content,
            "normalize": request.normalize
        }

    def _build_sentence_transformers_payload(self, request: EmbeddingRequest) -> dict[str, Any]:
        """Build payload for Sentence Transformers models."""
        return {"text": request.content}

    def _extract_embedding(self, result: dict[str, Any], model_id: str) -> list[float]:
        """Extract embedding from endpoint response."""
        # Try common response formats
        if "embedding" in result:
            return result["embedding"]
        elif "embeddings" in result:
            embeddings = result["embeddings"]
            return embeddings[0] if isinstance(embeddings, list) else embeddings
        elif "vectors" in result:
            return result["vectors"][0] if isinstance(result["vectors"], list) else result["vectors"]
        else:
            # Assume result is the embedding itself
            if isinstance(result, list):
                return result
            raise VectorEmbeddingError(
                f"Could not extract embedding from response for {model_id}",
                error_code="INVALID_RESPONSE_FORMAT",
                error_details={"response_keys": list(result.keys())}
            )
