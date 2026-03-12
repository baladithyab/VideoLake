"""
Multi-Modal Embedding Provider Abstraction

Provides a unified interface for generating embeddings across text, image, audio,
and video modalities. Supports multiple backend providers (AWS Bedrock, SageMaker,
external APIs) with auto-registration and factory pattern for dynamic discovery.

Architecture:
- ModalityType: Type-safe enum for content modalities
- EmbeddingProvider: Abstract base class for all providers
- EmbeddingProviderFactory: Factory with auto-registration via decorator
- Auto-discovery: Providers self-register using @register_embedding_provider
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Union, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ModalityType(str, Enum):
    """Supported modality types for embedding generation."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"  # Cross-modal (e.g., text+image, video+audio)


class EmbeddingProviderType(str, Enum):
    """Supported embedding provider backends."""
    BEDROCK = "bedrock"
    SAGEMAKER = "sagemaker"
    EXTERNAL = "external"
    TWELVELABS = "twelvelabs"
    OPENAI = "openai"


@dataclass
class EmbeddingRequest:
    """Request for generating embeddings."""
    modality: ModalityType
    content: Union[str, bytes, List[str]]  # Text, URI, binary data, or batch
    model_id: Optional[str] = None  # Provider-specific model ID
    dimensions: Optional[int] = None  # Target dimension (if configurable)
    normalize: bool = True  # Normalize embeddings to unit length
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Modality-specific options
    image_size: Optional[tuple] = None  # For image resizing
    audio_sample_rate: Optional[int] = None  # For audio processing
    video_segment_duration: Optional[int] = None  # Seconds per segment
    embedding_mode: Optional[str] = None  # Provider-specific mode


@dataclass
class EmbeddingResponse:
    """Response from embedding generation."""
    embedding: List[float]
    modality: ModalityType
    model_id: str
    provider: str
    dimensions: int
    processing_time_ms: int
    input_tokens: Optional[int] = None
    cost_estimate: Optional[float] = None  # USD
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "embedding": self.embedding,
            "modality": self.modality.value,
            "model_id": self.model_id,
            "provider": self.provider,
            "dimensions": self.dimensions,
            "processing_time_ms": self.processing_time_ms,
            "input_tokens": self.input_tokens,
            "cost_estimate": self.cost_estimate,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class EmbeddingModelInfo:
    """Information about an embedding model."""
    model_id: str
    provider: str
    supported_modalities: List[ModalityType]
    dimensions: int
    max_input_tokens: Optional[int] = None
    max_input_size_mb: Optional[int] = None  # For images/audio/video
    supports_batch: bool = False
    cost_per_1k_tokens: Optional[float] = None
    cost_per_unit: Optional[float] = None  # For non-token billing (e.g., per image)
    description: str = ""

    def supports_modality(self, modality: ModalityType) -> bool:
        """Check if this model supports a specific modality."""
        return modality in self.supported_modalities


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    All embedding provider implementations must inherit from this class
    and implement the required methods. This ensures a consistent interface
    across different backends (AWS Bedrock, SageMaker, external APIs).
    """

    @property
    @abstractmethod
    def provider_type(self) -> EmbeddingProviderType:
        """Return the type of this provider."""
        pass

    @abstractmethod
    def get_supported_modalities(self) -> List[ModalityType]:
        """Return list of modalities supported by this provider."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[EmbeddingModelInfo]:
        """Return list of available models from this provider."""
        pass

    @abstractmethod
    def get_default_model(self, modality: ModalityType) -> Optional[str]:
        """Get default model ID for a specific modality."""
        pass

    @abstractmethod
    async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embedding for a single input.

        Args:
            request: Embedding request with modality and content

        Returns:
            EmbeddingResponse with embedding and metadata

        Raises:
            ValueError: If modality not supported or invalid input
            ModelAccessError: If model access fails
            VectorEmbeddingError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def batch_generate_embeddings(
        self,
        requests: List[EmbeddingRequest]
    ) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple inputs.

        Args:
            requests: List of embedding requests

        Returns:
            List of EmbeddingResponse objects

        Note:
            Implementations should use native batch APIs when available,
            otherwise fall back to concurrent individual requests.
        """
        pass

    @abstractmethod
    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to the provider backend.

        Returns:
            Dictionary with:
                - accessible (bool): Whether backend is accessible
                - models_available (List[str]): List of accessible model IDs
                - response_time_ms (float): Response time in milliseconds
                - error_message (Optional[str]): Error if not accessible
        """
        pass

    def validate_request(self, request: EmbeddingRequest) -> bool:
        """
        Validate an embedding request.

        Args:
            request: Request to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Check modality support
        if request.modality not in self.get_supported_modalities():
            raise ValueError(
                f"Modality {request.modality.value} not supported by {self.provider_type.value}. "
                f"Supported: {[m.value for m in self.get_supported_modalities()]}"
            )

        # Check content
        if not request.content:
            raise ValueError("Content cannot be empty")

        # Check model availability if specified
        if request.model_id:
            available_models = [m.model_id for m in self.get_available_models()]
            if request.model_id not in available_models:
                raise ValueError(
                    f"Model {request.model_id} not available. "
                    f"Available: {available_models}"
                )

        return True

    def estimate_cost(self, request: EmbeddingRequest) -> Optional[float]:
        """
        Estimate cost for an embedding request.

        Args:
            request: Embedding request

        Returns:
            Estimated cost in USD, or None if not calculable
        """
        if not request.model_id:
            request.model_id = self.get_default_model(request.modality)
            if not request.model_id:
                return None

        # Find model info
        model_info = None
        for model in self.get_available_models():
            if model.model_id == request.model_id:
                model_info = model
                break

        if not model_info:
            return None

        # Estimate based on content type
        if request.modality == ModalityType.TEXT:
            if model_info.cost_per_1k_tokens:
                # Rough token estimation: 4 chars per token
                text_content = request.content if isinstance(request.content, str) else str(request.content)
                estimated_tokens = len(text_content) // 4
                return (estimated_tokens / 1000) * model_info.cost_per_1k_tokens
        elif model_info.cost_per_unit:
            # For images, audio, video - cost per unit
            if isinstance(request.content, list):
                return len(request.content) * model_info.cost_per_unit
            return model_info.cost_per_unit

        return None


class EmbeddingProviderFactory:
    """
    Factory for creating and managing embedding providers.

    Supports auto-registration via decorator pattern, allowing providers
    to register themselves without modifying factory code.
    """

    _providers: Dict[str, type] = {}
    _instances: Dict[str, EmbeddingProvider] = {}

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: type):
        """
        Register a provider class.

        Args:
            provider_name: Unique name for the provider
            provider_class: Class implementing EmbeddingProvider
        """
        if not issubclass(provider_class, EmbeddingProvider):
            raise TypeError(f"{provider_class} must inherit from EmbeddingProvider")

        cls._providers[provider_name] = provider_class
        logger.info(f"Registered embedding provider: {provider_name}")

    @classmethod
    def create_provider(cls, provider_name: str, **kwargs) -> EmbeddingProvider:
        """
        Create or get a provider instance.

        Args:
            provider_name: Name of the provider to create
            **kwargs: Provider-specific initialization arguments

        Returns:
            EmbeddingProvider instance
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"No provider registered with name: {provider_name}. "
                f"Available: {list(cls._providers.keys())}"
            )

        # Use singleton pattern for providers (reuse instances)
        cache_key = f"{provider_name}:{hash(frozenset(kwargs.items()))}"
        if cache_key not in cls._instances:
            provider_class = cls._providers[provider_name]
            cls._instances[cache_key] = provider_class(**kwargs)
            logger.info(f"Created new instance of provider: {provider_name}")

        return cls._instances[cache_key]

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of registered provider names."""
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """Check if a provider is registered."""
        return provider_name in cls._providers

    @classmethod
    def get_providers_for_modality(cls, modality: ModalityType) -> List[str]:
        """
        Get list of providers that support a specific modality.

        Args:
            modality: Modality to check

        Returns:
            List of provider names supporting the modality
        """
        supporting_providers = []

        for provider_name, provider_class in cls._providers.items():
            # Instantiate temporarily to check modalities
            try:
                provider = cls.create_provider(provider_name)
                if modality in provider.get_supported_modalities():
                    supporting_providers.append(provider_name)
            except Exception as e:
                logger.warning(f"Failed to check modality support for {provider_name}: {e}")

        return supporting_providers

    @classmethod
    def get_all_models(cls) -> Dict[str, List[EmbeddingModelInfo]]:
        """
        Get all available models from all providers.

        Returns:
            Dictionary mapping provider names to their model lists
        """
        all_models = {}

        for provider_name in cls._providers.keys():
            try:
                provider = cls.create_provider(provider_name)
                all_models[provider_name] = provider.get_available_models()
            except Exception as e:
                logger.warning(f"Failed to get models from {provider_name}: {e}")
                all_models[provider_name] = []

        return all_models

    @classmethod
    def find_best_provider(
        cls,
        modality: ModalityType,
        prefer_lowest_cost: bool = False,
        require_batch_support: bool = False
    ) -> Optional[str]:
        """
        Find the best provider for a modality based on criteria.

        Args:
            modality: Target modality
            prefer_lowest_cost: Prefer lowest cost providers
            require_batch_support: Only consider providers with batch support

        Returns:
            Provider name, or None if no suitable provider found
        """
        candidates = []

        for provider_name in cls.get_providers_for_modality(modality):
            try:
                provider = cls.create_provider(provider_name)
                default_model_id = provider.get_default_model(modality)

                if not default_model_id:
                    continue

                # Get model info
                model_info = None
                for model in provider.get_available_models():
                    if model.model_id == default_model_id:
                        model_info = model
                        break

                if not model_info:
                    continue

                # Apply filters
                if require_batch_support and not model_info.supports_batch:
                    continue

                candidates.append({
                    "provider_name": provider_name,
                    "model_info": model_info,
                    "cost": model_info.cost_per_1k_tokens or model_info.cost_per_unit or 0
                })
            except Exception as e:
                logger.warning(f"Failed to evaluate provider {provider_name}: {e}")

        if not candidates:
            return None

        # Sort by cost if requested
        if prefer_lowest_cost:
            candidates.sort(key=lambda x: x["cost"])

        return candidates[0]["provider_name"]


def register_embedding_provider(provider_name: str):
    """
    Decorator for auto-registering embedding providers.

    Usage:
        @register_embedding_provider("bedrock")
        class BedrockMultiModalProvider(EmbeddingProvider):
            ...

    Args:
        provider_name: Unique name for the provider
    """
    def decorator(cls):
        EmbeddingProviderFactory.register_provider(provider_name, cls)
        return cls
    return decorator
