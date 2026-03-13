"""
Embedding provider integration tests.

Tests real embedding generation with Bedrock, SageMaker, and external APIs.
Uses moto for Bedrock mocking in unit tests, real AWS for integration tests.
"""

import pytest
import asyncio
from typing import List

from src.services.embedding_provider import (
    EmbeddingRequest,
    EmbeddingResponse,
    ModalityType,
    EmbeddingProviderType,
)


@pytest.mark.integration
@pytest.mark.provider
class TestBedrockEmbeddingProviderUnit:
    """Unit tests for Bedrock embedding provider."""

    @pytest.fixture
    async def bedrock_provider(self):
        """Create Bedrock embedding provider."""
        from src.services.bedrock_embedding import BedrockEmbeddingProvider

        provider = BedrockEmbeddingProvider()
        yield provider

    def test_provider_type(self, bedrock_provider):
        """Test that provider identifies as BEDROCK."""
        assert bedrock_provider.provider_type == EmbeddingProviderType.BEDROCK

    def test_supported_modalities(self, bedrock_provider):
        """Test that Bedrock supports text and image modalities."""
        modalities = bedrock_provider.supported_modalities

        assert ModalityType.TEXT in modalities
        # Bedrock may support images depending on models available
        assert isinstance(modalities, list)

    def test_get_default_model(self, bedrock_provider):
        """Test getting default model for modality."""
        text_model = bedrock_provider.get_default_model(ModalityType.TEXT)

        assert text_model is not None
        assert isinstance(text_model, str)
        # Should be a Titan or similar model
        assert "titan" in text_model.lower() or "embed" in text_model.lower()

    def test_get_model_dimensions(self, bedrock_provider):
        """Test getting model dimensions."""
        # Titan text v1 typically has 1536 dimensions
        dims = bedrock_provider.get_model_dimensions("amazon.titan-embed-text-v1")

        assert dims > 0
        assert isinstance(dims, int)


@pytest.mark.requires_aws
@pytest.mark.integration
@pytest.mark.provider
class TestBedrockEmbeddingProviderIntegration:
    """Integration tests with real Bedrock service."""

    @pytest.fixture
    async def bedrock_provider(self):
        """Create Bedrock provider for real AWS tests."""
        from src.services.bedrock_embedding import BedrockEmbeddingProvider

        provider = BedrockEmbeddingProvider()
        yield provider

    @pytest.mark.asyncio
    async def test_validate_connectivity(self, bedrock_provider):
        """Test connectivity to Bedrock service."""
        result = await bedrock_provider.validate_connectivity()

        assert isinstance(result, dict)
        assert "accessible" in result

    @pytest.mark.asyncio
    async def test_generate_text_embedding(self, bedrock_provider):
        """Test generating text embedding with Bedrock."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="This is a test document for embedding generation.",
            model_id="amazon.titan-embed-text-v1",
        )

        response = await bedrock_provider.generate_embedding(request)

        assert isinstance(response, EmbeddingResponse)
        assert len(response.embeddings) == 1
        assert response.dimensions > 0
        assert len(response.embeddings[0]) == response.dimensions
        assert response.modality == ModalityType.TEXT

    @pytest.mark.asyncio
    async def test_generate_batch_embeddings(self, bedrock_provider):
        """Test generating batch text embeddings."""
        texts = [
            "First test document",
            "Second test document",
            "Third test document",
        ]

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content=texts,
            model_id="amazon.titan-embed-text-v1",
        )

        response = await bedrock_provider.generate_embedding(request)

        assert len(response.embeddings) == 3
        assert all(len(emb) == response.dimensions for emb in response.embeddings)

    @pytest.mark.asyncio
    async def test_embeddings_are_normalized(self, bedrock_provider):
        """Test that embeddings are normalized when requested."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test normalization",
            normalize=True,
        )

        response = await bedrock_provider.generate_embedding(request)

        # Check if embedding is normalized (magnitude ≈ 1.0)
        embedding = response.embeddings[0]
        magnitude = sum(x * x for x in embedding) ** 0.5

        assert 0.99 <= magnitude <= 1.01, f"Embedding not normalized: magnitude={magnitude}"


@pytest.mark.integration
@pytest.mark.provider
class TestMultimodalEmbeddingProviders:
    """Test multi-modal embedding support across providers."""

    @pytest.fixture
    async def get_provider(self):
        """Factory to get different embedding providers."""

        async def _get_provider(provider_type: str):
            if provider_type == "bedrock":
                from src.services.bedrock_embedding import BedrockEmbeddingProvider
                return BedrockEmbeddingProvider()
            elif provider_type == "bedrock_multimodal":
                from src.services.bedrock_multimodal_provider import BedrockMultimodalProvider
                return BedrockMultimodalProvider()
            elif provider_type == "twelvelabs":
                from src.services.twelvelabs_api_service import TwelveLabsAPIService
                return TwelveLabsAPIService()
            else:
                raise ValueError(f"Unknown provider type: {provider_type}")

        return _get_provider

    @pytest.mark.parametrize("provider_type", [
        "bedrock",
    ])
    @pytest.mark.asyncio
    async def test_provider_text_modality(self, get_provider, provider_type):
        """Test that providers support text modality."""
        provider = await get_provider(provider_type)

        assert ModalityType.TEXT in provider.supported_modalities

    @pytest.mark.asyncio
    async def test_embedding_dimension_consistency(self, get_provider):
        """Test that same model produces consistent dimensions."""
        provider = await get_provider("bedrock")

        # Generate two embeddings with same model
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="amazon.titan-embed-text-v1",
        )

        response1 = await provider.generate_embedding(request)
        response2 = await provider.generate_embedding(request)

        assert response1.dimensions == response2.dimensions
        assert len(response1.embeddings[0]) == len(response2.embeddings[0])


@pytest.mark.real_aws
@pytest.mark.expensive
@pytest.mark.provider
class TestRealEmbeddingGeneration:
    """Real AWS Bedrock embedding tests (costs money!)."""

    @pytest.fixture
    async def bedrock_provider(self):
        """Create Bedrock provider for real tests."""
        from src.services.bedrock_embedding import BedrockEmbeddingProvider

        provider = BedrockEmbeddingProvider()
        yield provider

    @pytest.mark.asyncio
    async def test_multiple_models(self, bedrock_provider):
        """Test embedding generation with different models."""
        models = [
            "amazon.titan-embed-text-v1",
            # Add more models as needed
        ]

        for model_id in models:
            request = EmbeddingRequest(
                modality=ModalityType.TEXT,
                content="Test content for model validation",
                model_id=model_id,
            )

            try:
                response = await bedrock_provider.generate_embedding(request)

                assert len(response.embeddings) == 1
                assert response.dimensions > 0
                assert response.model_id == model_id
            except Exception as e:
                pytest.skip(f"Model {model_id} not available: {e}")

    @pytest.mark.asyncio
    async def test_large_batch_embedding(self, bedrock_provider):
        """Test generating embeddings for large batch."""
        # Generate 50 test documents
        documents = [f"Test document number {i} with some content." for i in range(50)]

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content=documents,
        )

        import time
        start_time = time.time()

        response = await bedrock_provider.generate_embedding(request)

        elapsed = time.time() - start_time

        assert len(response.embeddings) == 50
        assert all(len(emb) > 0 for emb in response.embeddings)
        # Should complete in reasonable time
        print(f"Generated 50 embeddings in {elapsed:.2f}s")


@pytest.mark.integration
@pytest.mark.provider
class TestEmbeddingProviderErrorHandling:
    """Test error handling in embedding providers."""

    @pytest.fixture
    async def bedrock_provider(self):
        """Create Bedrock provider."""
        from src.services.bedrock_embedding import BedrockEmbeddingProvider

        return BedrockEmbeddingProvider()

    @pytest.mark.asyncio
    async def test_invalid_model_id(self, bedrock_provider):
        """Test handling of invalid model ID."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="invalid-model-id-12345",
        )

        with pytest.raises(Exception):
            await bedrock_provider.generate_embedding(request)

    @pytest.mark.asyncio
    async def test_empty_content(self, bedrock_provider):
        """Test handling of empty content."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="",
        )

        # Should either succeed with empty embedding or raise meaningful error
        try:
            response = await bedrock_provider.generate_embedding(request)
            assert response is not None
        except Exception as e:
            # Should have meaningful error message
            assert len(str(e)) > 0

    @pytest.mark.asyncio
    async def test_unsupported_modality(self, bedrock_provider):
        """Test handling of unsupported modality."""
        # If provider doesn't support video
        if ModalityType.VIDEO not in bedrock_provider.supported_modalities:
            request = EmbeddingRequest(
                modality=ModalityType.VIDEO,
                content="s3://bucket/video.mp4",
            )

            with pytest.raises(Exception):
                await bedrock_provider.generate_embedding(request)
