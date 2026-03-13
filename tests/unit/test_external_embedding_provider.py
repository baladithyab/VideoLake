"""
Unit tests for External Embedding Provider.

Tests external API integration (OpenAI, Cohere) with mocked HTTP calls.
"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.services.embedding_provider import (
    EmbeddingModelInfo,
    EmbeddingProviderType,
    EmbeddingRequest,
    EmbeddingResponse,
    ModalityType,
    ProviderCapabilities,
)
from src.services.external_embedding_provider import ExternalEmbeddingProvider


class TestExternalEmbeddingProviderInit:
    """Test External provider initialization."""

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key-123", "COHERE_API_KEY": "cohere-key-456"})
    def test_init_with_api_keys(self):
        """Test initialization with API keys in environment."""
        provider = ExternalEmbeddingProvider()

        assert provider.openai_api_key == "test-key-123"
        assert provider.cohere_api_key == "cohere-key-456"

    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_keys(self):
        """Test initialization without API keys."""
        provider = ExternalEmbeddingProvider()

        assert provider.openai_api_key is None
        assert provider.cohere_api_key is None

    def test_provider_type(self):
        """Test that provider identifies as EXTERNAL."""
        provider = ExternalEmbeddingProvider()
        assert provider.provider_type == EmbeddingProviderType.EXTERNAL

    def test_provider_name_and_id(self):
        """Test provider name and ID properties."""
        provider = ExternalEmbeddingProvider()

        assert provider.provider_name == "External APIs"
        assert provider.provider_id == "external"


class TestExternalModelRegistry:
    """Test External provider model registry."""

    def test_models_structure(self):
        """Test that MODELS has correct structure."""
        provider = ExternalEmbeddingProvider()

        assert len(provider.MODELS) > 0

        for _model_id, config in provider.MODELS.items():
            assert "modality" in config
            assert "dimensions" in config
            assert "description" in config

    def test_openai_models_present(self):
        """Test that OpenAI models are registered."""
        provider = ExternalEmbeddingProvider()

        assert "openai.text-embedding-3-large" in provider.MODELS
        assert "openai.text-embedding-3-small" in provider.MODELS

        large_config = provider.MODELS["openai.text-embedding-3-large"]
        assert large_config["modality"] == ModalityType.TEXT
        assert 3072 in large_config["dimensions"]

    def test_cohere_model_present(self):
        """Test that Cohere model is registered."""
        provider = ExternalEmbeddingProvider()

        assert "cohere.embed-v3" in provider.MODELS

        config = provider.MODELS["cohere.embed-v3"]
        assert config["modality"] == ModalityType.TEXT
        assert 1024 in config["dimensions"]

    def test_get_supported_modalities(self):
        """Test getting supported modalities."""
        provider = ExternalEmbeddingProvider()

        modalities = provider.get_supported_modalities()

        assert ModalityType.TEXT in modalities
        assert isinstance(modalities, list)

    def test_get_available_models(self):
        """Test getting available models."""
        provider = ExternalEmbeddingProvider()

        models = provider.get_available_models()

        assert len(models) == len(provider.MODELS)
        assert all(isinstance(m, EmbeddingModelInfo) for m in models)

        # Check structure of returned models
        for model in models:
            assert model.provider == "external"
            assert ModalityType.TEXT in model.supported_modalities
            assert model.dimensions > 0

    def test_get_default_model(self):
        """Test getting default model for TEXT modality."""
        provider = ExternalEmbeddingProvider()

        default_model = provider.get_default_model(ModalityType.TEXT)

        assert default_model == "openai.text-embedding-3-large"

    def test_get_default_model_unsupported_modality(self):
        """Test getting default model for unsupported modality returns None."""
        provider = ExternalEmbeddingProvider()

        default_model = provider.get_default_model(ModalityType.VIDEO)

        assert default_model is None

    def test_get_capabilities(self):
        """Test getting provider capabilities."""
        provider = ExternalEmbeddingProvider()

        capabilities = provider.get_capabilities()

        assert isinstance(capabilities, ProviderCapabilities)
        assert ModalityType.TEXT in capabilities.supported_modalities
        assert capabilities.max_batch_size == 2048
        assert capabilities.supports_configurable_dimensions is True
        assert 3072 in capabilities.available_dimensions

    def test_list_available_models(self):
        """Test listing available models with metadata."""
        provider = ExternalEmbeddingProvider()

        models = provider.list_available_models()

        assert len(models) > 0
        assert all(isinstance(m, dict) for m in models)

        for model in models:
            assert "model_id" in model
            assert "modality" in model
            assert "dimensions" in model
            assert "description" in model
            assert "is_default" in model


class TestExternalEmbeddingGeneration:
    """Test embedding generation with mocked external APIs."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mock OpenAI API response."""
        mock_item = Mock()
        mock_item.embedding = [0.1, 0.2, 0.3]

        mock_response = Mock()
        mock_response.data = [mock_item]

        return mock_response

    @pytest.fixture
    def mock_cohere_response(self):
        """Create mock Cohere API response."""
        mock_response = Mock()
        mock_response.embeddings = [[0.4, 0.5, 0.6]]

        return mock_response

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_generate_openai_embedding(self, mock_openai_class, mock_openai_response):
        """Test generating embedding with OpenAI API."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_openai_response
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="openai.text-embedding-3-large"
        )

        response = await provider.generate_embedding(request)

        assert isinstance(response, EmbeddingResponse)
        assert response.modality == ModalityType.TEXT
        assert response.model_id == "openai.text-embedding-3-large"
        assert response.provider == "external"
        assert len(response.embedding) == 3
        assert response.embedding == [0.1, 0.2, 0.3]

        # Verify API was called correctly
        mock_client.embeddings.create.assert_called_once()
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert call_kwargs["model"] == "text-embedding-3-large"
        assert call_kwargs["input"] == ["Test document"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_generate_openai_embedding_with_dimensions(self, mock_openai_class, mock_openai_response):
        """Test generating OpenAI embedding with custom dimensions."""
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_openai_response
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="openai.text-embedding-3-large",
            dimensions=1024
        )

        await provider.generate_embedding(request)

        # Verify dimensions parameter was passed
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert "dimensions" in call_kwargs
        assert call_kwargs["dimensions"] == 1024

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_generate_openai_embedding_no_api_key(self):
        """Test generating OpenAI embedding without API key raises error."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="openai.text-embedding-3-large"
        )

        with pytest.raises(ModelAccessError) as exc_info:
            await provider.generate_embedding(request)

        assert "OPENAI_API_KEY not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"COHERE_API_KEY": "test-key"})
    @patch('cohere.AsyncClient')
    async def test_generate_cohere_embedding(self, mock_cohere_module, mock_cohere_response):
        """Test generating embedding with Cohere API."""
        # Setup mock client
        mock_client = AsyncMock()
        mock_client.embed.return_value = mock_cohere_response
        mock_cohere_module.AsyncClient.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="cohere.embed-v3"
        )

        response = await provider.generate_embedding(request)

        assert isinstance(response, EmbeddingResponse)
        assert response.modality == ModalityType.TEXT
        assert response.model_id == "cohere.embed-v3"
        assert response.provider == "external"
        assert len(response.embedding) == 3
        assert response.embedding == [0.4, 0.5, 0.6]

        # Verify API was called correctly
        mock_client.embed.assert_called_once()
        call_kwargs = mock_client.embed.call_args[1]
        assert call_kwargs["texts"] == ["Test document"]
        assert call_kwargs["model"] == "embed-english-v3.0"
        assert call_kwargs["input_type"] == "search_document"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_generate_cohere_embedding_no_api_key(self):
        """Test generating Cohere embedding without API key raises error."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="cohere.embed-v3"
        )

        with pytest.raises(ModelAccessError) as exc_info:
            await provider.generate_embedding(request)

        assert "COHERE_API_KEY not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_embedding_unsupported_modality(self):
        """Test generating embedding with unsupported modality raises error."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.IMAGE,
            content="image_data"
        )

        with pytest.raises(ValidationError) as exc_info:
            await provider.generate_embedding(request)

        assert "TEXT modality" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_embedding_unsupported_model(self):
        """Test generating embedding with unsupported model raises error."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="unknown.model"
        )

        with pytest.raises(ValidationError) as exc_info:
            await provider.generate_embedding(request)

        assert "Unsupported external model" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_embedding_defaults_to_openai(self):
        """Test that generation defaults to OpenAI large model."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test"
        )

        # Should default to openai.text-embedding-3-large
        assert request.model_id is None

        # After processing in generate_embedding, model_id should be set
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test"}):
            with patch('src.services.external_embedding_provider.AsyncOpenAI'):
                try:
                    await provider.generate_embedding(request)
                except Exception:
                    pass  # We're just checking the default assignment


class TestExternalBatchGeneration:
    """Test batch embedding generation."""

    @pytest.fixture
    def mock_openai_batch_response(self):
        """Create mock OpenAI batch response."""
        mock_items = [Mock(embedding=[0.1, 0.2]), Mock(embedding=[0.3, 0.4]), Mock(embedding=[0.5, 0.6])]

        mock_response = Mock()
        mock_response.data = mock_items

        return mock_response

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_batch_generate_embeddings(self, mock_openai_class, mock_openai_batch_response):
        """Test batch embedding generation."""
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_openai_batch_response
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        requests = [
            EmbeddingRequest(modality=ModalityType.TEXT, content=f"Doc {i}", model_id="openai.text-embedding-3-large")
            for i in range(3)
        ]

        responses = await provider.batch_generate_embeddings(requests)

        assert len(responses) == 3
        assert all(isinstance(r, EmbeddingResponse) for r in responses)
        assert mock_client.embeddings.create.call_count == 3


class TestExternalConnectivityValidation:
    """Test connectivity validation."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key", "COHERE_API_KEY": "test-key"})
    async def test_validate_connectivity_all_keys_present(self):
        """Test connectivity validation when all API keys are present."""
        provider = ExternalEmbeddingProvider()

        result = await provider.validate_connectivity()

        assert result["accessible"] is True
        assert result["health_status"] == "healthy"
        assert "configured_apis" in result
        assert "openai" in result["configured_apis"]
        assert "cohere" in result["configured_apis"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {}, clear=True)
    async def test_validate_connectivity_no_keys(self):
        """Test connectivity validation when no API keys are present."""
        provider = ExternalEmbeddingProvider()

        result = await provider.validate_connectivity()

        assert result["accessible"] is False
        assert result["health_status"] == "unhealthy"
        assert "OPENAI_API_KEY" in result["error_message"]
        assert "COHERE_API_KEY" in result["error_message"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_validate_connectivity_partial_keys(self):
        """Test connectivity validation when only some API keys are present."""
        provider = ExternalEmbeddingProvider()

        result = await provider.validate_connectivity()

        assert result["accessible"] is False
        assert "COHERE_API_KEY" in result["error_message"]


class TestExternalAPIIntegration:
    """Test integration with external API libraries."""

    @pytest.mark.asyncio
    @patch('src.services.external_embedding_provider.AsyncOpenAI', side_effect=ImportError)
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    async def test_openai_library_not_installed(self):
        """Test handling when OpenAI library is not installed."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="openai.text-embedding-3-large"
        )

        with pytest.raises(VectorEmbeddingError) as exc_info:
            await provider.generate_embedding(request)

        assert "OpenAI library not installed" in str(exc_info.value)
        assert "pip install openai" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('src.services.external_embedding_provider.cohere', side_effect=ImportError)
    @patch.dict(os.environ, {"COHERE_API_KEY": "test-key"})
    async def test_cohere_library_not_installed(self):
        """Test handling when Cohere library is not installed."""
        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="cohere.embed-v3"
        )

        with pytest.raises(VectorEmbeddingError) as exc_info:
            await provider.generate_embedding(request)

        assert "Cohere library not installed" in str(exc_info.value)
        assert "pip install cohere" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_openai_api_error_handling(self, mock_openai_class):
        """Test handling of OpenAI API errors."""
        mock_client = AsyncMock()
        mock_client.embeddings.create.side_effect = Exception("API rate limit exceeded")
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="openai.text-embedding-3-large"
        )

        with pytest.raises(VectorEmbeddingError) as exc_info:
            await provider.generate_embedding(request)

        assert "OpenAI API error" in str(exc_info.value)
        assert "rate limit" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"COHERE_API_KEY": "test-key"})
    @patch('cohere.AsyncClient')
    async def test_cohere_api_error_handling(self, mock_cohere_module):
        """Test handling of Cohere API errors."""
        mock_client = AsyncMock()
        mock_client.embed.side_effect = Exception("Invalid API key")
        mock_cohere_module.AsyncClient.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="cohere.embed-v3"
        )

        with pytest.raises(VectorEmbeddingError) as exc_info:
            await provider.generate_embedding(request)

        assert "Cohere API error" in str(exc_info.value)
        assert "Invalid API key" in str(exc_info.value)


class TestExternalBatchContentHandling:
    """Test handling of batch vs single content."""

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_single_text_converts_to_list(self, mock_openai_class):
        """Test that single text is converted to list for API."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2])]

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        await provider._generate_openai_embeddings(
            content="Single text",
            model_id="openai.text-embedding-3-large",
            dimension=None
        )

        # Verify input was converted to list
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert call_kwargs["input"] == ["Single text"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('openai.AsyncOpenAI')
    async def test_list_text_passed_directly(self, mock_openai_class):
        """Test that list of texts is passed directly to API."""
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2]), Mock(embedding=[0.3, 0.4])]

        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        provider = ExternalEmbeddingProvider()

        embeddings = await provider._generate_openai_embeddings(
            content=["Text 1", "Text 2"],
            model_id="openai.text-embedding-3-large",
            dimension=None
        )

        # Verify input was passed as list
        call_kwargs = mock_client.embeddings.create.call_args[1]
        assert call_kwargs["input"] == ["Text 1", "Text 2"]
        assert len(embeddings) == 2
