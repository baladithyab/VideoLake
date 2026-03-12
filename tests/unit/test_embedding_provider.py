#!/usr/bin/env python3
"""
Unit tests for EmbeddingProvider service.

Tests the embedding provider abstraction, factory registration,
and modality type validation without making actual API calls.
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


@pytest.mark.unit
class TestModalityType:
    """Test ModalityType enum and validation."""

    def test_modality_types_exist(self):
        """Verify all expected modality types are defined."""
        assert hasattr(ModalityType, 'TEXT')
        assert hasattr(ModalityType, 'IMAGE')
        assert hasattr(ModalityType, 'AUDIO')
        assert hasattr(ModalityType, 'VIDEO')
        assert hasattr(ModalityType, 'MULTIMODAL')

    def test_modality_type_values(self):
        """Verify modality type enum values."""
        assert ModalityType.TEXT.value == "text"
        assert ModalityType.IMAGE.value == "image"
        assert ModalityType.AUDIO.value == "audio"
        assert ModalityType.VIDEO.value == "video"
        assert ModalityType.MULTIMODAL.value == "multimodal"


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
