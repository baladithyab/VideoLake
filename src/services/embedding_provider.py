"""
Multi-Modal Embedding Provider Abstraction

Provides a unified interface for generating embeddings across text, image, audio,
and video modalities. Supports multiple backend providers (AWS Bedrock, SageMaker,
external APIs) with auto-registration and factory pattern for dynamic discovery.

This module provides the foundation for the multi-modal vector platform architecture,
enabling seamless integration of diverse embedding providers with consistent interfaces
and auto-discovery capabilities.

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
    """
    Supported modality types for multi-modal embeddings.

    This enum defines the core content types that can be embedded in the
    vector platform, enabling cross-modal search and unified retrieval.
    """
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
    """
    Request for generating embeddings.

    Attributes:
        modality: The type of content being embedded
        content: The content to embed (text string, S3 URI, base64 bytes, or batch)
        model_id: Optional specific model to use (provider will choose default if None)
        dimensions: Optional dimension override for configurable models (also accepts 'dimension')
        normalize: Normalize embeddings to unit length
        metadata: Additional provider-specific parameters
        image_size: For image resizing (optional)
        audio_sample_rate: For audio processing (optional)
        video_segment_duration: Seconds per segment for video (optional)
        embedding_mode: Provider-specific embedding mode (optional)
    """
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

    # Backward compatibility alias
    @property
    def dimension(self) -> Optional[int]:
        """Alias for dimensions (backward compatibility)."""
        return self.dimensions

    @dimension.setter
    def dimension(self, value: Optional[int]):
        """Alias for dimensions (backward compatibility)."""
        self.dimensions = value


@dataclass
class EmbeddingResponse:
    """
    Response from embedding generation.

    Supports both single and batch embeddings for flexibility.

    Attributes:
        embedding: Single embedding vector (for single requests)
        embeddings: List of embedding vectors (for batch requests) - alias for [embedding]
        model_id: The model used to generate embeddings
        modality: The modality that was processed
        provider: Provider name (e.g., 'bedrock', 'sagemaker')
        dimensions: The dimension of the embedding vectors
        processing_time_ms: Time taken to generate embeddings
        input_tokens: Number of input tokens processed (optional)
        cost_estimate: Estimated cost in USD (optional)
        metadata: Provider-specific metadata
        created_at: Timestamp of creation
    """
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

    # Backward compatibility aliases
    @property
    def embeddings(self) -> List[List[float]]:
        """Return embeddings as list (backward compatibility with batch API)."""
        return [self.embedding]

    @property
    def dimension(self) -> int:
        """Alias for dimensions (backward compatibility)."""
        return self.dimensions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "embedding": self.embedding,
            "embeddings": self.embeddings,  # Include batch format
            "modality": self.modality.value,
            "model_id": self.model_id,
            "provider": self.provider,
            "dimensions": self.dimensions,
            "dimension": self.dimension,  # Alias
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


@dataclass
class ProviderCapabilities:
    """
    Capabilities supported by an embedding provider.

    Defines what modalities, dimensions, and features are available
    from a specific embedding provider. Complementary to EmbeddingModelInfo.
    """
    supported_modalities: List[ModalityType]
    max_batch_size: int
    supports_configurable_dimensions: bool
    available_dimensions: List[int]
    max_input_tokens: Optional[int] = None
    cost_per_1k_tokens: Optional[float] = None
    typical_latency_ms: Optional[float] = None


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    All embedding provider implementations must inherit from this class
    and implement the required methods. This ensures a consistent interface
    across different backends (AWS Bedrock, SageMaker, external APIs) and enables
    dynamic provider selection based on modality and capability requirements.

    Implementations:
    - BedrockMultiModalProvider: AWS Bedrock (Titan Text/Image, Nova Multi-modal)
    - SageMakerEmbeddingProvider: SageMaker endpoints (Voyage, Jina, etc.)
    - ExternalEmbeddingProvider: External APIs (OpenAI, Cohere, etc.)
    """

    @property
    @abstractmethod
    def provider_type(self) -> EmbeddingProviderType:
        """Return the type of this provider."""
        pass

    @property
    def provider_name(self) -> str:
        """Return human-readable provider name (e.g., 'AWS Bedrock')."""
        return self.provider_type.value.title()

    @property
    def provider_id(self) -> str:
        """Return unique provider identifier (e.g., 'bedrock')."""
        return self.provider_type.value

    @abstractmethod
    def get_supported_modalities(self) -> List[ModalityType]:
        """Return list of modalities supported by this provider."""
        pass

    @abstractmethod
    def get_available_models(self) -> List[EmbeddingModelInfo]:
        """Return list of available models from this provider."""
        pass

    def list_available_models(self) -> List[Dict[str, Any]]:
        """
        List all models available from this provider (dict format).

        Returns:
            List of model information dictionaries with:
                - model_id (str): Model identifier
                - modality (ModalityType): Supported modality
                - dimensions (int): Embedding dimensions
                - description (str): Human-readable description
        """
        models = []
        for model_info in self.get_available_models():
            for modality in model_info.supported_modalities:
                models.append({
                    "model_id": model_info.model_id,
                    "modality": modality.value,
                    "dimensions": model_info.dimensions,
                    "max_tokens": model_info.max_input_tokens,
                    "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
                    "description": model_info.description,
                    "supports_batch": model_info.supports_batch
                })
        return models

    @abstractmethod
    def get_default_model(self, modality: ModalityType) -> Optional[str]:
        """Get default model ID for a specific modality."""
        pass

    def get_capabilities(self) -> ProviderCapabilities:
        """
        Return provider capabilities.

        Default implementation derives capabilities from available models.
        Providers can override for more specific capabilities.

        Returns:
            ProviderCapabilities defining supported modalities and features
        """
        models = self.get_available_models()
        modalities = set()
        dimensions = set()
        max_tokens = 0
        supports_batch = False

        for model in models:
            modalities.update(model.supported_modalities)
            dimensions.add(model.dimensions)
            if model.max_input_tokens:
                max_tokens = max(max_tokens, model.max_input_tokens)
            if model.supports_batch:
                supports_batch = True

        return ProviderCapabilities(
            supported_modalities=list(modalities),
            max_batch_size=96 if supports_batch else 1,
            supports_configurable_dimensions=len(dimensions) > 1,
            available_dimensions=sorted(list(dimensions)),
            max_input_tokens=max_tokens if max_tokens > 0 else None,
            cost_per_1k_tokens=None,
            typical_latency_ms=None
        )

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
            ValidationError: If request validation fails
            ModelAccessError: If model access fails
            VectorEmbeddingError: If embedding generation fails
        """
        pass

    async def generate_embeddings(
        self, request: EmbeddingRequest
    ) -> EmbeddingResponse:
        """
        Generate embeddings for the given request (backward compatibility alias).

        This is an alias for generate_embedding() to support both naming conventions.

        Args:
            request: Embedding request with modality and content

        Returns:
            EmbeddingResponse with generated embeddings

        Raises:
            ValidationError: If request validation fails
            ModelAccessError: If model access fails
            VectorEmbeddingError: If embedding generation fails
        """
        return await self.generate_embedding(request)

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
    async def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to the provider backend.

        Returns:
            Dictionary with:
                - accessible (bool): Whether backend is accessible
                - models_available (List[str]): List of accessible model IDs (optional)
                - response_time_ms (float): Response time in milliseconds
                - health_status (str): Health status (optional)
                - error_message (Optional[str]): Error if not accessible
        """
        pass

    def supports_modality(self, modality: ModalityType) -> bool:
        """
        Check if provider supports a given modality.

        Args:
            modality: The modality to check

        Returns:
            True if modality is supported
        """
        return modality in self.get_supported_modalities()

    def supports_batch_processing(self) -> bool:
        """
        Check if provider supports batch embedding generation.

        Returns:
            True if batch processing is supported
        """
        capabilities = self.get_capabilities()
        return capabilities.max_batch_size > 1

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

    This factory maintains a registry of available embedding providers and enables
    dynamic provider selection based on modality requirements. Supports both manual
    registration and decorator-based auto-registration with optional singleton pattern.
    """

    _providers: Dict[str, type] = {}
    _instances: Dict[str, EmbeddingProvider] = {}

    @classmethod
    def register_provider(cls, provider_name: str, provider_class: type):
        """
        Register an embedding provider.

        Args:
            provider_name: Unique identifier for the provider (e.g., 'bedrock', 'sagemaker')
            provider_class: Provider class (must inherit from EmbeddingProvider)

        Raises:
            TypeError: If provider_class doesn't inherit from EmbeddingProvider
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
            **kwargs: Provider-specific initialization arguments (optional)

        Returns:
            EmbeddingProvider instance

        Raises:
            ValueError: If provider_name is not registered
        """
        if provider_name not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider_name}. "
                f"Available providers: {list(cls._providers.keys())}"
            )

        # Use singleton pattern for providers if no kwargs (reuse instances)
        if not kwargs:
            if provider_name not in cls._instances:
                provider_class = cls._providers[provider_name]
                cls._instances[provider_name] = provider_class()
                logger.info(f"Created new instance of provider: {provider_name}")
            return cls._instances[provider_name]
        else:
            # Create new instance with custom kwargs
            provider_class = cls._providers[provider_name]
            return provider_class(**kwargs)

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of available provider IDs.

        Returns:
            List of registered provider identifiers
        """
        return list(cls._providers.keys())

    @classmethod
    def is_provider_available(cls, provider_name: str) -> bool:
        """
        Check if a provider is available.

        Args:
            provider_name: The provider identifier to check

        Returns:
            True if provider is registered
        """
        return provider_name in cls._providers

    @classmethod
    def get_provider_for_modality(
        cls, modality: ModalityType
    ) -> Optional[EmbeddingProvider]:
        """
        Get first available provider supporting the modality.

        Args:
            modality: The required modality

        Returns:
            EmbeddingProvider instance or None if no provider supports the modality
        """
        for provider_class in cls._providers.values():
            try:
                provider = provider_class()
                if provider.supports_modality(modality):
                    return provider
            except Exception as e:
                logger.warning(f"Failed to instantiate provider: {e}")
        return None

    @classmethod
    def get_all_providers_for_modality(
        cls, modality: ModalityType
    ) -> List[EmbeddingProvider]:
        """
        Get all providers supporting the modality.

        Args:
            modality: The required modality

        Returns:
            List of EmbeddingProvider instances supporting the modality
        """
        providers = []
        for provider_class in cls._providers.values():
            try:
                provider = provider_class()
                if provider.supports_modality(modality):
                    providers.append(provider)
            except Exception as e:
                logger.warning(f"Failed to instantiate provider: {e}")
        return providers

    @classmethod
    def get_providers_for_modality(cls, modality: ModalityType) -> List[str]:
        """
        Get list of provider names that support a specific modality.

        Args:
            modality: Modality to check

        Returns:
            List of provider names supporting the modality
        """
        supporting_providers = []

        for provider_name, provider_class in cls._providers.items():
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
        provider_name: Unique identifier for the provider (e.g., 'bedrock', 'sagemaker')

    Returns:
        Decorator function that registers the provider class
    """
    def decorator(cls):
        EmbeddingProviderFactory.register_provider(provider_name, cls)
        return cls
    return decorator
