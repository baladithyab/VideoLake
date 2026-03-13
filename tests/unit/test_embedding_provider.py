#!/usr/bin/env python3
"""
Unit tests for EmbeddingProvider abstraction.

Tests the multi-modal embedding provider interface, modality types, and provider
registration without requiring actual backend implementations. Only mocks external
API calls (Bedrock, OpenAI), not internal service interfaces.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from src.services.embedding_provider import (
EmbeddingProvider,
ModalityType,
EmbeddingProviderFactory,
ProviderCapabilities,
)
from typing import List
from datetime import datetime
EmbeddingProviderType,
EmbeddingRequest,
EmbeddingResponse,


@pytest.mark.unit
class TestEmbeddingProviderAbstraction:
    """Test EmbeddingProvider abstract base class contract."""

    def test_provider_has_required_methods(self):
        """Verify EmbeddingProvider ABC defines required methods."""
        required_methods = [
            'generate_embedding',
            'generate_embeddings_batch',
            'get_supported_modalities',
            'get_embedding_dimension',
            'get_capabilities'
        ]

        for method_name in required_methods:
            assert hasattr(EmbeddingProvider, method_name)

    def test_cannot_instantiate_abstract_provider(self):
        """Verify EmbeddingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EmbeddingProvider()  # Should raise TypeError for abstract class

    def test_concrete_provider_implements_interface(self):
        """Test that a concrete provider can implement the interface."""
        class ConcreteProvider(EmbeddingProvider):
            async def generate_embedding(self, content: str, modality: ModalityType):
                return [0.1] * 1536

            async def generate_embeddings_batch(self, contents: list, modality: ModalityType):
                return [[0.1] * 1536 for _ in contents]

            def get_supported_modalities(self):
                return [ModalityType.TEXT]

            def get_embedding_dimension(self):
                return 1536

            def get_capabilities(self):
                return ProviderCapabilities(
                    supported_modalities=[ModalityType.TEXT],
                    max_batch_size=32,
                    max_content_length=8192,
                    supports_streaming=False
                )

        # Should be able to instantiate concrete provider
        provider = ConcreteProvider()
        assert isinstance(provider, EmbeddingProvider)

    @pytest.mark.asyncio
    async def test_mock_provider_generates_embeddings(self):
        """Test mock provider can generate embeddings."""
        class MockProvider(EmbeddingProvider):
            async def generate_embedding(self, content, modality):
                return [0.1 + i * 0.01 for i in range(1536)]

            async def generate_embeddings_batch(self, contents, modality):
                return [[0.1] * 1536 for _ in contents]

            def get_supported_modalities(self):
                return [ModalityType.TEXT]

            def get_embedding_dimension(self):
                return 1536

            def get_capabilities(self):
                return ProviderCapabilities(
                    supported_modalities=[ModalityType.TEXT],
                    max_batch_size=32,
                    max_content_length=8192,
                    supports_streaming=False
                )

        provider = MockProvider()

        # Test single embedding
        embedding = await provider.generate_embedding("test text", ModalityType.TEXT)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

        # Test batch embeddings
        batch_embeddings = await provider.generate_embeddings_batch(
            ["text1", "text2"], ModalityType.TEXT
        )
        assert len(batch_embeddings) == 2
        assert all(len(emb) == 1536 for emb in batch_embeddings)


@pytest.mark.unit
class TestEmbeddingProviderFactory:
    """Test EmbeddingProviderFactory registration and lookup."""

    def test_factory_has_methods(self):
        """Test factory has required methods."""
        assert hasattr(EmbeddingProviderFactory, 'register_provider')
        assert hasattr(EmbeddingProviderFactory, 'get_provider')
        assert hasattr(EmbeddingProviderFactory, 'list_providers')

    def test_list_providers(self):
        """Test listing providers returns a collection."""
        providers = EmbeddingProviderFactory.list_providers()
        assert isinstance(providers, (list, tuple, set))

    def test_factory_registration(self):
        """Test provider registration in factory."""
        # Create a mock provider class
        class MockProvider(EmbeddingProvider):
            async def generate_embedding(self, content, modality):
                return [0.1] * 1536

            async def generate_embeddings_batch(self, contents, modality):
                return [[0.1] * 1536 for _ in contents]

            def get_supported_modalities(self):
                return [ModalityType.TEXT]

            def get_embedding_dimension(self):
                return 1536

            def get_capabilities(self):
                return ProviderCapabilities(
                    supported_modalities=[ModalityType.TEXT],
                    max_batch_size=32,
                    max_content_length=8192,
                    supports_streaming=False
                )

        # Register the provider
        EmbeddingProviderFactory.register_provider("mock_test_provider", MockProvider)

        # Verify registration
        providers = EmbeddingProviderFactory.list_providers()
        assert "mock_test_provider" in providers


@pytest.mark.unit
class TestEmbeddingProviderInterface:
    """Test EmbeddingProvider abstract base class contract."""

    def test_provider_is_abstract(self):
        """Test that EmbeddingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            EmbeddingProvider()

    def test_minimal_provider_implementation(self):
        """Test a minimal valid embedding provider implementation."""

        class MinimalEmbeddingProvider(EmbeddingProvider):
            """Minimal provider with required methods."""

            @property
            def provider_type(self) -> EmbeddingProviderType:
                return EmbeddingProviderType.BEDROCK

            @property
            def supported_modalities(self) -> List[ModalityType]:
                return [ModalityType.TEXT, ModalityType.IMAGE]

            async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
                # Mock implementation
                return EmbeddingResponse(
                    embeddings=[[0.1] * 1536],
                    dimensions=1536,
                    model_id=request.model_id or "default-model",
                    modality=request.modality,
                )

            async def validate_connectivity(self) -> dict:
                return {"accessible": True}

            def get_default_model(self, modality: ModalityType) -> str:
                return "default-model"

            def get_model_dimensions(self, model_id: str) -> int:
                return 1536

        # Should not raise
        provider = MinimalEmbeddingProvider()
        assert provider.provider_type == EmbeddingProviderType.BEDROCK
        assert ModalityType.TEXT in provider.supported_modalities


@pytest.mark.unit
class TestEmbeddingProviderMethods:
    """Test embedding provider method signatures and contracts."""

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider for testing."""

        class MockEmbeddingProvider(EmbeddingProvider):
            """Test embedding provider implementation."""

            @property
            def provider_type(self) -> EmbeddingProviderType:
                return EmbeddingProviderType.BEDROCK

            @property
            def supported_modalities(self) -> List[ModalityType]:
                return [
                    ModalityType.TEXT,
                    ModalityType.IMAGE,
                    ModalityType.MULTIMODAL,
                ]

            async def generate_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
                # Determine dimension based on model
                dim = request.dimensions or 1536

                # Handle batch vs single
                if isinstance(request.content, list):
                    embeddings = [[0.1] * dim for _ in request.content]
                else:
                    embeddings = [[0.1] * dim]

                return EmbeddingResponse(
                    embeddings=embeddings,
                    dimensions=dim,
                    model_id=request.model_id or self.get_default_model(request.modality),
                    modality=request.modality,
                    metadata={"generated_at": datetime.utcnow().isoformat()},
                )

            async def validate_connectivity(self) -> dict:
                return {
                    "accessible": True,
                    "provider": "bedrock",
                    "region": "us-east-1",
                }

            def get_default_model(self, modality: ModalityType) -> str:
                defaults = {
                    ModalityType.TEXT: "amazon.titan-embed-text-v1",
                    ModalityType.IMAGE: "amazon.titan-embed-image-v1",
                    ModalityType.MULTIMODAL: "amazon.titan-embed-multimodal-v1",
                }
                return defaults.get(modality, "amazon.titan-embed-text-v1")

            def get_model_dimensions(self, model_id: str) -> int:
                if "v2" in model_id:
                    return 1024
                return 1536

        return MockEmbeddingProvider()

    @pytest.mark.asyncio
    async def test_generate_text_embedding(self, mock_embedding_provider):
        """Test generating text embedding."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="amazon.titan-embed-text-v1",
        )
        response = await mock_embedding_provider.generate_embedding(request)

        assert isinstance(response, EmbeddingResponse)
        assert len(response.embeddings) == 1
        assert response.dimensions == 1536
        assert response.modality == ModalityType.TEXT

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, mock_embedding_provider):
        """Test generating batch embeddings."""
        texts = ["Doc 1", "Doc 2", "Doc 3"]
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content=texts,
        )
        response = await mock_embedding_provider.generate_embedding(request)

        assert len(response.embeddings) == 3
        assert all(len(emb) == 1536 for emb in response.embeddings)

    @pytest.mark.asyncio
    async def test_generate_image_embedding(self, mock_embedding_provider):
        """Test generating image embedding."""
        request = EmbeddingRequest(
            modality=ModalityType.IMAGE,
            content="s3://bucket/image.jpg",
            model_id="amazon.titan-embed-image-v1",
        )
        response = await mock_embedding_provider.generate_embedding(request)

        assert response.modality == ModalityType.IMAGE
        assert len(response.embeddings) == 1

    @pytest.mark.asyncio
    async def test_custom_dimensions(self, mock_embedding_provider):
        """Test generating embeddings with custom dimensions."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            dimensions=512,
        )
        response = await mock_embedding_provider.generate_embedding(request)

        assert response.dimensions == 512
        assert len(response.embeddings[0]) == 512

    @pytest.mark.asyncio
    async def test_validate_connectivity(self, mock_embedding_provider):
        """Test provider connectivity validation."""
        result = await mock_embedding_provider.validate_connectivity()

        assert result["accessible"] is True
        assert "provider" in result
        assert "region" in result

    def test_get_default_model(self, mock_embedding_provider):
        """Test getting default model for modality."""
        text_model = mock_embedding_provider.get_default_model(ModalityType.TEXT)
        assert "text" in text_model.lower()

        image_model = mock_embedding_provider.get_default_model(ModalityType.IMAGE)
        assert "image" in image_model.lower()

    def test_get_model_dimensions(self, mock_embedding_provider):
        """Test getting model dimensions."""
        dims_v1 = mock_embedding_provider.get_model_dimensions("amazon.titan-embed-text-v1")
        assert dims_v1 == 1536

        dims_v2 = mock_embedding_provider.get_model_dimensions("amazon.titan-embed-text-v2")
        assert dims_v2 == 1024

    def test_supported_modalities(self, mock_embedding_provider):
        """Test checking supported modalities."""
        assert ModalityType.TEXT in mock_embedding_provider.supported_modalities
        assert ModalityType.IMAGE in mock_embedding_provider.supported_modalities
        assert ModalityType.VIDEO not in mock_embedding_provider.supported_modalities


@pytest.mark.unit
class TestEmbeddingProviderModalities:
    """Test modality support validation."""

    def test_provider_reports_supported_modalities(self):
        """Test provider can report supported modalities."""
        class TextOnlyProvider(EmbeddingProvider):
            async def generate_embedding(self, content, modality):
                return [0.1] * 768

            async def generate_embeddings_batch(self, contents, modality):
                return [[0.1] * 768 for _ in contents]

            def get_supported_modalities(self):
                return [ModalityType.TEXT]

            def get_embedding_dimension(self):
                return 768

            def get_capabilities(self):
                return ProviderCapabilities(
                    supported_modalities=[ModalityType.TEXT],
                    max_batch_size=16,
                    max_content_length=512,
                    supports_streaming=False
                )

        provider = TextOnlyProvider()
        modalities = provider.get_supported_modalities()

        assert ModalityType.TEXT in modalities
        assert ModalityType.IMAGE not in modalities

    def test_multimodal_provider_capabilities(self):
        """Test multimodal provider reports multiple modalities."""
        class MultiModalProvider(EmbeddingProvider):
            async def generate_embedding(self, content, modality):
                return [0.1] * 1024

            async def generate_embeddings_batch(self, contents, modality):
                return [[0.1] * 1024 for _ in contents]

            def get_supported_modalities(self):
                return [ModalityType.TEXT, ModalityType.IMAGE, ModalityType.MULTIMODAL]

            def get_embedding_dimension(self):
                return 1024

            def get_capabilities(self):
                return ProviderCapabilities(
                    supported_modalities=[
                        ModalityType.TEXT,
                        ModalityType.IMAGE,
                        ModalityType.MULTIMODAL
                    ],
                    max_batch_size=8,
                    max_content_length=4096,
                    supports_streaming=True
                )

        provider = MultiModalProvider()
        modalities = provider.get_supported_modalities()

        assert len(modalities) >= 3
        assert ModalityType.TEXT in modalities
        assert ModalityType.IMAGE in modalities
        assert ModalityType.MULTIMODAL in modalities


@pytest.mark.unit
class TestEmbeddingProviderType:
    """Test EmbeddingProviderType enum."""

    def test_provider_type_values(self):
        """Verify all supported embedding providers."""
        assert EmbeddingProviderType.BEDROCK == "bedrock"
        assert EmbeddingProviderType.SAGEMAKER == "sagemaker"
        assert EmbeddingProviderType.EXTERNAL == "external"
        assert EmbeddingProviderType.TWELVELABS == "twelvelabs"
        assert EmbeddingProviderType.OPENAI == "openai"


@pytest.mark.unit
class TestEmbeddingRequest:
    """Test EmbeddingRequest dataclass."""

    def test_text_embedding_request(self):
        """Test creating text embedding request."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="This is a test document",
            model_id="amazon.titan-embed-text-v1",
        )
        assert request.modality == ModalityType.TEXT
        assert request.content == "This is a test document"
        assert request.normalize is True  # Default

    def test_image_embedding_request(self):
        """Test creating image embedding request with options."""
        request = EmbeddingRequest(
            modality=ModalityType.IMAGE,
            content="s3://bucket/image.jpg",
            model_id="amazon.titan-embed-image-v1",
            dimensions=1024,
            image_size=(224, 224),
        )
        assert request.modality == ModalityType.IMAGE
        assert request.dimensions == 1024
        assert request.image_size == (224, 224)

    def test_video_embedding_request(self):
        """Test creating video embedding request with segment duration."""
        request = EmbeddingRequest(
            modality=ModalityType.VIDEO,
            content="s3://bucket/video.mp4",
            model_id="twelvelabs/marengo-2.6",
            video_segment_duration=10,
            metadata={"source": "test"},
        )
        assert request.modality == ModalityType.VIDEO
        assert request.video_segment_duration == 10
        assert request.metadata["source"] == "test"

    def test_batch_embedding_request(self):
        """Test batch embedding request with list of content."""
        texts = ["Document 1", "Document 2", "Document 3"]
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content=texts,
            model_id="amazon.titan-embed-text-v1",
        )
        assert isinstance(request.content, list)
        assert len(request.content) == 3

    def test_dimension_backward_compatibility(self):
        """Test backward compatibility alias for dimension/dimensions."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            dimensions=512,
        )
        # Both accessors should work
        assert request.dimensions == 512
        assert request.dimension == 512

        # Setter should work
        request.dimension = 768
        assert request.dimensions == 768


@pytest.mark.unit
class TestEmbeddingResponse:
    """Test EmbeddingResponse dataclass."""

    def test_single_embedding_response(self):
        """Test response for single embedding."""
        embedding = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        response = EmbeddingResponse(
            embeddings=[embedding],
            dimensions=1536,
            model_id="amazon.titan-embed-text-v1",
            modality=ModalityType.TEXT,
        )
        assert len(response.embeddings) == 1
        assert response.dimensions == 1536
        assert response.modality == ModalityType.TEXT

    def test_batch_embedding_response(self):
        """Test response for batch embeddings."""
        embeddings = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
        response = EmbeddingResponse(
            embeddings=embeddings,
            dimensions=768,
            model_id="text-embedding-ada-002",
            modality=ModalityType.TEXT,
            metadata={"batch_size": 3},
        )
        assert len(response.embeddings) == 3
        assert all(len(emb) == 768 for emb in response.embeddings)

    def test_video_segment_embeddings(self):
        """Test response for video with segment embeddings."""
        # Video embeddings often have timestamps
        segment_embeddings = [
            [0.1] * 1024,  # Segment 0-10s
            [0.2] * 1024,  # Segment 10-20s
            [0.3] * 1024,  # Segment 20-30s
        ]
        response = EmbeddingResponse(
            embeddings=segment_embeddings,
            dimensions=1024,
            model_id="twelvelabs/marengo-2.6",
            modality=ModalityType.VIDEO,
            metadata={
                "segments": [
                    {"start": 0, "end": 10},
                    {"start": 10, "end": 20},
                    {"start": 20, "end": 30},
                ]
            },
        )
        assert len(response.embeddings) == 3
        assert response.modality == ModalityType.VIDEO
        assert len(response.metadata["segments"]) == 3


@pytest.mark.unit
class TestModalityType:
    """Test ModalityType enum for multi-modal support."""

    def test_modality_type_values(self):
        """Verify all supported modality types."""
        assert ModalityType.TEXT == "text"
        assert ModalityType.IMAGE == "image"
        assert ModalityType.AUDIO == "audio"
        assert ModalityType.VIDEO == "video"
        assert ModalityType.MULTIMODAL == "multimodal"

    def test_modality_type_string_conversion(self):
        """Test modality type string conversion."""
        modality = ModalityType.VIDEO
        # Enum value should be the string
        assert modality.value == "video"
        # Can compare directly to string (StrEnum)
        assert modality == "video"


@pytest.mark.unit
class TestProviderCapabilities:
    """Test ProviderCapabilities dataclass."""

    def test_capabilities_initialization(self):
        """Test ProviderCapabilities can be initialized."""
        caps = ProviderCapabilities(
            supported_modalities=[ModalityType.TEXT, ModalityType.IMAGE],
            max_batch_size=32,
            max_content_length=8192,
            supports_streaming=False
        )

        assert ModalityType.TEXT in caps.supported_modalities
        assert ModalityType.IMAGE in caps.supported_modalities
        assert caps.max_batch_size == 32
        assert caps.max_content_length == 8192
        assert caps.supports_streaming is False


