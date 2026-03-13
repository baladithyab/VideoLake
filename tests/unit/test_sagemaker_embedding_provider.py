"""
Unit tests for SageMaker Embedding Provider.

Tests model configuration, endpoint management, and embedding generation
without requiring actual AWS SageMaker endpoints.
"""

from unittest.mock import Mock, patch

import pytest

from src.exceptions import ValidationError, VectorEmbeddingError
from src.services.embedding_provider import (
    EmbeddingModelInfo,
    EmbeddingProviderType,
    EmbeddingRequest,
    EmbeddingResponse,
    ModalityType,
)
from src.services.sagemaker_embedding_provider import SageMakerEmbeddingProvider


class TestSageMakerEmbeddingProviderInit:
    """Test SageMaker provider initialization and configuration."""

    def test_init_without_endpoint_mapping(self):
        """Test initialization without endpoint mapping."""
        provider = SageMakerEmbeddingProvider()

        assert provider.endpoint_mapping == {}
        assert provider.region_name == "us-east-1"
        assert provider._runtime is None

    def test_init_with_endpoint_mapping(self):
        """Test initialization with endpoint mapping."""
        endpoint_mapping = {
            "voyage-code-2": "voyage-code-2-endpoint",
            "jina-embeddings-v3": "jina-v3-endpoint"
        }

        provider = SageMakerEmbeddingProvider(
            endpoint_mapping=endpoint_mapping,
            region_name="us-west-2"
        )

        assert provider.endpoint_mapping == endpoint_mapping
        assert provider.region_name == "us-west-2"

    def test_provider_type(self):
        """Test that provider identifies as SAGEMAKER."""
        provider = SageMakerEmbeddingProvider()
        assert provider.provider_type == EmbeddingProviderType.SAGEMAKER

    def test_register_endpoint(self):
        """Test dynamic endpoint registration."""
        provider = SageMakerEmbeddingProvider()

        provider.register_endpoint("voyage-code-2", "my-endpoint")

        assert "voyage-code-2" in provider.endpoint_mapping
        assert provider.endpoint_mapping["voyage-code-2"] == "my-endpoint"

    def test_get_endpoint_name_success(self):
        """Test getting endpoint name for registered model."""
        provider = SageMakerEmbeddingProvider(
            endpoint_mapping={"voyage-code-2": "voyage-endpoint"}
        )

        endpoint = provider.get_endpoint_name("voyage-code-2")
        assert endpoint == "voyage-endpoint"

    def test_get_endpoint_name_not_registered(self):
        """Test getting endpoint name for unregistered model raises error."""
        provider = SageMakerEmbeddingProvider()

        with pytest.raises(ValueError) as exc_info:
            provider.get_endpoint_name("unknown-model")

        assert "No endpoint registered" in str(exc_info.value)


class TestSageMakerModelRegistry:
    """Test SageMaker model registry and capabilities."""

    def test_known_models_structure(self):
        """Test that KNOWN_MODELS has correct structure."""
        provider = SageMakerEmbeddingProvider()

        assert len(provider.KNOWN_MODELS) > 0

        for model_id, model_info in provider.KNOWN_MODELS.items():
            assert isinstance(model_info, EmbeddingModelInfo)
            assert model_info.model_id == model_id
            assert model_info.provider == "sagemaker"
            assert len(model_info.supported_modalities) > 0
            assert model_info.dimensions > 0

    def test_e5_mistral_model_present(self):
        """Test that e5-mistral-7b-instruct model is registered."""
        provider = SageMakerEmbeddingProvider()

        assert "e5-mistral-7b-instruct" in provider.KNOWN_MODELS

        model_info = provider.KNOWN_MODELS["e5-mistral-7b-instruct"]
        assert model_info.dimensions == 4096
        assert model_info.max_input_tokens == 32768
        assert ModalityType.TEXT in model_info.supported_modalities

    def test_get_supported_modalities(self):
        """Test getting all supported modalities across models."""
        provider = SageMakerEmbeddingProvider()

        modalities = provider.get_supported_modalities()

        assert ModalityType.TEXT in modalities
        assert isinstance(modalities, list)

    def test_get_available_models_without_endpoints(self):
        """Test getting available models when no endpoints configured."""
        provider = SageMakerEmbeddingProvider()

        models = provider.get_available_models()

        # Should return all known models
        assert len(models) == len(provider.KNOWN_MODELS)

    def test_get_available_models_with_endpoints(self):
        """Test getting available models filters by configured endpoints."""
        provider = SageMakerEmbeddingProvider(
            endpoint_mapping={
                "voyage-code-2": "endpoint-1",
                "jina-embeddings-v3": "endpoint-2"
            }
        )

        models = provider.get_available_models()

        # Should only return models with configured endpoints
        assert len(models) == 2
        model_ids = [m.model_id for m in models]
        assert "voyage-code-2" in model_ids
        assert "jina-embeddings-v3" in model_ids

    def test_get_default_model_with_endpoint(self):
        """Test getting default model when endpoint is configured."""
        provider = SageMakerEmbeddingProvider(
            endpoint_mapping={"jina-embeddings-v3": "jina-endpoint"}
        )

        default_model = provider.get_default_model(ModalityType.TEXT)

        assert default_model == "jina-embeddings-v3"

    def test_get_default_model_without_endpoint(self):
        """Test getting default model when no endpoint configured."""
        provider = SageMakerEmbeddingProvider()

        default_model = provider.get_default_model(ModalityType.TEXT)

        # Should return None since no endpoints configured
        assert default_model is None


class TestSageMakerEmbeddingGeneration:
    """Test embedding generation with mocked SageMaker runtime."""

    @pytest.fixture
    def mock_runtime(self):
        """Create mock SageMaker runtime client."""
        mock = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b'{"embedding": [0.1, 0.2, 0.3]}'
        mock_response = {"Body": mock_body}
        mock.invoke_endpoint.return_value = mock_response
        return mock

    @pytest.fixture
    def provider_with_mock(self, mock_runtime):
        """Create provider with mocked runtime."""
        provider = SageMakerEmbeddingProvider(
            endpoint_mapping={"voyage-code-2": "test-endpoint"}
        )
        provider._runtime = mock_runtime
        return provider

    @pytest.mark.asyncio
    async def test_generate_text_embedding(self, provider_with_mock, mock_runtime):
        """Test generating text embedding."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document",
            model_id="voyage-code-2"
        )

        response = await provider_with_mock.generate_embedding(request)

        assert isinstance(response, EmbeddingResponse)
        assert response.modality == ModalityType.TEXT
        assert response.model_id == "voyage-code-2"
        assert response.provider == "sagemaker"
        assert len(response.embedding) == 3
        assert response.dimensions == 3

        # Verify endpoint was called
        mock_runtime.invoke_endpoint.assert_called_once()
        call_args = mock_runtime.invoke_endpoint.call_args
        assert call_args[1]["EndpointName"] == "test-endpoint"

    @pytest.mark.asyncio
    async def test_generate_embedding_without_model_id(self, provider_with_mock):
        """Test generating embedding using default model."""
        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test document"
        )

        response = await provider_with_mock.generate_embedding(request)

        assert response.model_id == "voyage-code-2"  # Default for configured endpoint

    @pytest.mark.asyncio
    async def test_generate_embedding_no_endpoint(self):
        """Test generating embedding without configured endpoint raises error."""
        provider = SageMakerEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="voyage-code-2"
        )

        with pytest.raises(ValueError) as exc_info:
            await provider.generate_embedding(request)

        assert "No endpoint registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_batch_generate_embeddings(self, provider_with_mock, mock_runtime):
        """Test batch embedding generation."""
        requests = [
            EmbeddingRequest(modality=ModalityType.TEXT, content=f"Doc {i}", model_id="voyage-code-2")
            for i in range(3)
        ]

        responses = await provider_with_mock.batch_generate_embeddings(requests)

        assert len(responses) == 3
        assert all(isinstance(r, EmbeddingResponse) for r in responses)
        assert mock_runtime.invoke_endpoint.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_generate_empty_list(self):
        """Test batch generation with empty list raises error."""
        provider = SageMakerEmbeddingProvider()

        with pytest.raises(ValidationError) as exc_info:
            await provider.batch_generate_embeddings([])

        assert "empty" in str(exc_info.value).lower()


class TestSageMakerPayloadBuilders:
    """Test payload building for different model families."""

    def test_build_voyage_payload(self):
        """Test building payload for Voyage models."""
        provider = SageMakerEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test content"
        )

        payload = provider._build_voyage_payload(request)

        assert "input" in payload
        assert payload["input"] == "Test content"
        assert payload["input_type"] == "document"

    def test_build_jina_text_payload(self):
        """Test building payload for Jina text models."""
        provider = SageMakerEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test content"
        )

        payload = provider._build_jina_payload(request, "jina-embeddings-v3")

        assert "text" in payload
        assert payload["text"] == "Test content"
        assert payload["task"] == "retrieval.passage"

    def test_build_bge_payload(self):
        """Test building payload for BGE models."""
        provider = SageMakerEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test content",
            normalize=True
        )

        payload = provider._build_bge_payload(request)

        assert payload["text"] == "Test content"
        assert payload["normalize"] is True

    def test_build_sentence_transformers_payload(self):
        """Test building payload for Sentence Transformers models."""
        provider = SageMakerEmbeddingProvider()

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test content"
        )

        payload = provider._build_sentence_transformers_payload(request)

        assert payload["text"] == "Test content"


class TestSageMakerEmbeddingExtraction:
    """Test embedding extraction from various response formats."""

    def test_extract_embedding_standard_format(self):
        """Test extracting from standard 'embedding' key."""
        provider = SageMakerEmbeddingProvider()

        result = {"embedding": [0.1, 0.2, 0.3]}
        embedding = provider._extract_embedding(result, "test-model")

        assert embedding == [0.1, 0.2, 0.3]

    def test_extract_embedding_embeddings_array(self):
        """Test extracting from 'embeddings' array."""
        provider = SageMakerEmbeddingProvider()

        result = {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
        embedding = provider._extract_embedding(result, "test-model")

        assert embedding == [0.1, 0.2]  # Should return first embedding

    def test_extract_embedding_vectors_format(self):
        """Test extracting from 'vectors' format."""
        provider = SageMakerEmbeddingProvider()

        result = {"vectors": [[0.5, 0.6]]}
        embedding = provider._extract_embedding(result, "test-model")

        assert embedding == [0.5, 0.6]

    def test_extract_embedding_direct_array(self):
        """Test extracting when result is the embedding itself."""
        provider = SageMakerEmbeddingProvider()

        result = [0.7, 0.8, 0.9]
        embedding = provider._extract_embedding(result, "test-model")

        assert embedding == [0.7, 0.8, 0.9]

    def test_extract_embedding_invalid_format(self):
        """Test extracting from invalid format raises error."""
        provider = SageMakerEmbeddingProvider()

        result = {"unknown_key": "value"}

        with pytest.raises(VectorEmbeddingError) as exc_info:
            provider._extract_embedding(result, "test-model")

        assert "Could not extract embedding" in str(exc_info.value)


class TestSageMakerConnectivityValidation:
    """Test connectivity validation."""

    def test_validate_connectivity_no_endpoints(self):
        """Test connectivity validation with no configured endpoints."""
        provider = SageMakerEmbeddingProvider()

        result = provider.validate_connectivity()

        assert result["accessible"] is False
        assert len(result["accessible_endpoints"]) == 0

    @patch('asyncio.new_event_loop')
    def test_validate_connectivity_with_endpoints(self, mock_loop):
        """Test connectivity validation with configured endpoints."""
        # Mock the event loop
        mock_loop_instance = Mock()
        mock_loop.return_value = mock_loop_instance

        # Mock successful endpoint call
        mock_loop_instance.run_until_complete.return_value = None

        provider = SageMakerEmbeddingProvider(
            endpoint_mapping={"voyage-code-2": "test-endpoint"}
        )

        # Mock the runtime
        provider._runtime = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b'{"embedding": [0.1, 0.2]}'
        mock_response = {"Body": mock_body}
        provider._runtime.invoke_endpoint.return_value = mock_response

        result = provider.validate_connectivity()

        assert "accessible" in result
        assert "accessible_endpoints" in result


class TestSageMakerModelFamilyHandling:
    """Test handling of different model families."""

    @pytest.fixture
    def provider(self):
        """Create provider with multiple model endpoints."""
        return SageMakerEmbeddingProvider(
            endpoint_mapping={
                "voyage-code-2": "voyage-endpoint",
                "jina-embeddings-v3": "jina-endpoint",
                "bge-m3": "bge-endpoint",
                "e5-large-v2": "e5-endpoint",
                "e5-mistral-7b-instruct": "e5-mistral-endpoint",
            }
        )

    @pytest.mark.asyncio
    async def test_invoke_voyage_model(self, provider):
        """Test invoking Voyage model uses correct payload format."""
        provider._runtime = Mock()
        mock_body = Mock()
        mock_body.read.return_value = b'{"embedding": [0.1, 0.2]}'
        mock_response = {"Body": mock_body}
        provider._runtime.invoke_endpoint.return_value = mock_response

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Test",
            model_id="voyage-code-2"
        )

        await provider.generate_embedding(request)

        # Verify correct endpoint called with Voyage payload format
        call_args = provider._runtime.invoke_endpoint.call_args
        import json
        payload = json.loads(call_args[1]["Body"])
        assert "input" in payload

    @pytest.mark.asyncio
    async def test_invoke_e5_mistral_model(self, provider):
        """Test invoking E5 Mistral model."""
        import json
        provider._runtime = Mock()
        mock_body = Mock()
        # Create a proper JSON with 4096-dimensional embedding
        embedding = [0.1] * 4096
        mock_body.read.return_value = json.dumps({"embedding": embedding}).encode()
        mock_response = {"Body": mock_body}
        provider._runtime.invoke_endpoint.return_value = mock_response

        request = EmbeddingRequest(
            modality=ModalityType.TEXT,
            content="Long document for E5 Mistral",
            model_id="e5-mistral-7b-instruct"
        )

        response = await provider.generate_embedding(request)

        assert response.model_id == "e5-mistral-7b-instruct"
        assert response.dimensions == 4096
        assert provider._runtime.invoke_endpoint.called
