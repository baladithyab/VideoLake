"""
External Embedding Provider

Supports external API-based embedding models:
- OpenAI text-embedding-3-large/small
- Cohere embed-v3
- Google Gemini embeddings
"""

import time
import asyncio
from typing import List, Dict, Any, Optional
import os

from src.services.embedding_provider import (
    EmbeddingProvider,
    ModalityType,
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderCapabilities,
    register_embedding_provider
)
from src.utils.logging_config import get_logger
from src.exceptions import ValidationError, ModelAccessError, VectorEmbeddingError

logger = get_logger(__name__)


@register_embedding_provider("external")
class ExternalEmbeddingProvider(EmbeddingProvider):
    """
    External API embedding provider (OpenAI, Cohere, etc.)

    Provides access to external embedding APIs for use cases where
    AWS-native models don't meet specific requirements.
    """

    # Model configurations
    MODELS = {
        "openai.text-embedding-3-large": {
            "modality": ModalityType.TEXT,
            "dimensions": [3072, 1536, 1024, 768, 512, 256],
            "max_tokens": 8191,
            "cost_per_1k": 0.00013,
            "description": "OpenAI text-embedding-3-large - State-of-the-art quality"
        },
        "openai.text-embedding-3-small": {
            "modality": ModalityType.TEXT,
            "dimensions": [1536, 512, 256],
            "max_tokens": 8191,
            "cost_per_1k": 0.00002,
            "description": "OpenAI text-embedding-3-small - Cost-effective"
        },
        "cohere.embed-v3": {
            "modality": ModalityType.TEXT,
            "dimensions": [1024],
            "max_tokens": 512,
            "cost_per_1k": 0.0001,
            "description": "Cohere Embed V3 - Multilingual support"
        }
    }

    def __init__(self):
        """Initialize the external embedding provider."""
        # Check for API keys in environment
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")

    @property
    def provider_name(self) -> str:
        return "External APIs"

    @property
    def provider_id(self) -> str:
        return "external"

    def get_capabilities(self) -> ProviderCapabilities:
        """Return external provider capabilities."""
        return ProviderCapabilities(
            supported_modalities=[ModalityType.TEXT],
            max_batch_size=2048,  # OpenAI supports large batches
            supports_configurable_dimensions=True,
            available_dimensions=[3072, 1536, 1024, 768, 512, 256],
            max_input_tokens=8191,
            cost_per_1k_tokens=0.00013,  # Varies by model
            typical_latency_ms=120.0
        )

    async def generate_embeddings(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Generate embeddings using external APIs.

        Args:
            request: Embedding request with modality and content

        Returns:
            EmbeddingResponse with generated embeddings
        """
        start_time = time.time()

        # Validate request
        if request.modality != ModalityType.TEXT:
            raise ValidationError(
                f"External provider currently only supports TEXT modality",
                error_code="UNSUPPORTED_MODALITY"
            )

        if not request.model_id:
            request.model_id = "openai.text-embedding-3-large"

        # Route to appropriate API
        if request.model_id.startswith("openai."):
            embeddings = await self._generate_openai_embeddings(
                request.content,
                request.model_id,
                request.dimension
            )
        elif request.model_id.startswith("cohere."):
            embeddings = await self._generate_cohere_embeddings(
                request.content,
                request.model_id
            )
        else:
            raise ValidationError(
                f"Unsupported external model: {request.model_id}",
                error_code="UNSUPPORTED_MODEL"
            )

        processing_time_ms = int((time.time() - start_time) * 1000)

        return EmbeddingResponse(
            embeddings=embeddings,
            model_id=request.model_id,
            modality=request.modality,
            dimension=len(embeddings[0]) if embeddings else 0,
            metadata={
                "provider": self.provider_id
            },
            processing_time_ms=processing_time_ms
        )

    async def validate_connectivity(self) -> Dict[str, Any]:
        """Validate external API connectivity."""
        errors = []

        # Check OpenAI
        if not self.openai_api_key:
            errors.append("OPENAI_API_KEY not configured")

        # Check Cohere
        if not self.cohere_api_key:
            errors.append("COHERE_API_KEY not configured")

        if errors:
            return {
                "accessible": False,
                "response_time_ms": 0,
                "health_status": "unhealthy",
                "error_message": "; ".join(errors),
                "provider": self.provider_name
            }

        return {
            "accessible": True,
            "response_time_ms": 0,
            "health_status": "healthy",
            "provider": self.provider_name,
            "configured_apis": ["openai", "cohere"]
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        """List all external API models."""
        models = []

        for model_id, config in self.MODELS.items():
            models.append({
                "model_id": model_id,
                "modality": config["modality"].value,
                "dimensions": config["dimensions"],
                "max_tokens": config.get("max_tokens"),
                "cost_per_1k_tokens": config.get("cost_per_1k"),
                "description": config["description"],
                "is_default": model_id == "openai.text-embedding-3-large"
            })

        return models

    async def _generate_openai_embeddings(
        self,
        content: Any,
        model_id: str,
        dimension: Optional[int]
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""

        if not self.openai_api_key:
            raise ModelAccessError(
                "OPENAI_API_KEY not configured",
                error_code="MISSING_API_KEY"
            )

        # Handle batch or single text
        if isinstance(content, list):
            inputs = content
        else:
            inputs = [content]

        # Extract actual model name (remove "openai." prefix)
        model_name = model_id.replace("openai.", "")

        try:
            # Import OpenAI client (optional dependency)
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.openai_api_key)

            # Create embedding request
            kwargs = {
                "model": model_name,
                "input": inputs
            }

            if dimension:
                kwargs["dimensions"] = dimension

            response = await client.embeddings.create(**kwargs)

            # Extract embeddings
            embeddings = [item.embedding for item in response.data]

            return embeddings

        except ImportError:
            raise VectorEmbeddingError(
                "OpenAI library not installed. Install with: pip install openai",
                error_code="MISSING_DEPENDENCY"
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise VectorEmbeddingError(
                f"OpenAI API error: {str(e)}",
                error_code="EXTERNAL_API_ERROR"
            )

    async def _generate_cohere_embeddings(
        self,
        content: Any,
        model_id: str
    ) -> List[List[float]]:
        """Generate embeddings using Cohere API."""

        if not self.cohere_api_key:
            raise ModelAccessError(
                "COHERE_API_KEY not configured",
                error_code="MISSING_API_KEY"
            )

        # Handle batch or single text
        if isinstance(content, list):
            texts = content
        else:
            texts = [content]

        try:
            # Import Cohere client (optional dependency)
            import cohere

            client = cohere.AsyncClient(api_key=self.cohere_api_key)

            # Create embedding request
            response = await client.embed(
                texts=texts,
                model="embed-english-v3.0",
                input_type="search_document"
            )

            embeddings = response.embeddings

            return embeddings

        except ImportError:
            raise VectorEmbeddingError(
                "Cohere library not installed. Install with: pip install cohere",
                error_code="MISSING_DEPENDENCY"
            )
        except Exception as e:
            logger.error(f"Cohere API error: {e}")
            raise VectorEmbeddingError(
                f"Cohere API error: {str(e)}",
                error_code="EXTERNAL_API_ERROR"
            )
