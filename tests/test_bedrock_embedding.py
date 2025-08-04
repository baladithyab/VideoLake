"""
Unit tests for Bedrock Embedding Service.

Tests cover embedding generation, model validation, batch processing,
error handling, and cost estimation functionality.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError, BotoCoreError

from src.services.bedrock_embedding import BedrockEmbeddingService, EmbeddingResult, ModelInfo
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError


class TestBedrockEmbeddingService:
    """Test cases for BedrockEmbeddingService."""
    
    @pytest.fixture
    def mock_bedrock_client(self):
        """Mock Bedrock Runtime client."""
        with patch('src.services.bedrock_embedding.aws_client_factory') as mock_factory:
            mock_client = Mock()
            mock_factory.get_bedrock_runtime_client.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def embedding_service(self, mock_bedrock_client):
        """Create BedrockEmbeddingService instance with mocked client."""
        return BedrockEmbeddingService()
    
    @pytest.fixture
    def sample_embedding(self):
        """Sample embedding vector for testing."""
        return [0.1, 0.2, 0.3] * 341 + [0.1]  # 1024 dimensions
    
    def test_get_supported_models(self, embedding_service):
        """Test getting supported models information."""
        models = embedding_service.get_supported_models()
        
        assert isinstance(models, dict)
        assert len(models) >= 5  # Should have at least 5 models now
        assert 'amazon.titan-embed-text-v2:0' in models
        assert 'amazon.titan-embed-text-v1' in models
        assert 'cohere.embed-english-v3' in models
        
        # Check model info structure for V2
        titan_v2_model = models['amazon.titan-embed-text-v2:0']
        assert titan_v2_model.dimensions == 1024
        assert titan_v2_model.max_input_tokens == 8192
        assert titan_v2_model.cost_per_1k_tokens == 0.0001
        
        # Check model info structure for V1
        titan_v1_model = models['amazon.titan-embed-text-v1']
        assert titan_v1_model.dimensions == 1536
        assert titan_v1_model.max_input_tokens == 8192
        assert titan_v1_model.cost_per_1k_tokens == 0.0001
    
    def test_validate_model_access_success(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test successful model access validation."""
        # Mock successful response
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        result = embedding_service.validate_model_access('amazon.titan-embed-text-v2:0')
        assert result is True
        mock_bedrock_client.invoke_model.assert_called_once()
    
    def test_validate_model_access_unsupported_model(self, embedding_service):
        """Test validation with unsupported model."""
        with pytest.raises(ModelAccessError) as exc_info:
            embedding_service.validate_model_access('unsupported-model')
        
        assert exc_info.value.error_code == "UNSUPPORTED_MODEL"
        assert "unsupported-model" in str(exc_info.value)
    
    def test_validate_model_access_denied(self, embedding_service, mock_bedrock_client):
        """Test validation with access denied error."""
        # Mock access denied error
        error_response = {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': 'Access denied to model'
            }
        }
        mock_bedrock_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        with pytest.raises(ModelAccessError) as exc_info:
            embedding_service.validate_model_access('amazon.titan-embed-text-v2:0')
        
        assert exc_info.value.error_code == "MODEL_ACCESS_DENIED"
    
    def test_generate_text_embedding_success(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test successful text embedding generation."""
        # Mock successful response
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        result = embedding_service.generate_text_embedding("test text", "amazon.titan-embed-text-v2:0")
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == sample_embedding
        assert result.input_text == "test text"
        assert result.model_id == "amazon.titan-embed-text-v2:0"
        assert result.processing_time_ms is not None
        assert result.processing_time_ms >= 0  # Can be 0 for mocked calls
    
    def test_generate_text_embedding_empty_text(self, embedding_service):
        """Test embedding generation with empty text."""
        with pytest.raises(ValidationError) as exc_info:
            embedding_service.generate_text_embedding("", "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "EMPTY_INPUT_TEXT"
    
    def test_generate_text_embedding_text_too_long(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test embedding generation with text that's too long."""
        # Mock successful validation call first
        mock_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = mock_response
        
        # Create very long text (exceeding token limit)
        long_text = "a" * 50000  # Much longer than max tokens * 4
        
        with pytest.raises(ValidationError) as exc_info:
            embedding_service.generate_text_embedding(long_text, "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "INPUT_TOO_LONG"
    
    def test_generate_cohere_embedding(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Cohere model embedding generation."""
        # Mock successful validation call first
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        # Mock actual embedding call
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, embedding_response]
        
        result = embedding_service.generate_text_embedding("test text", "cohere.embed-english-v3")
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == sample_embedding
        assert result.model_id == "cohere.embed-english-v3"
    
    def test_generate_titan_v1_embedding(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Titan V1 model embedding generation."""
        # Mock successful validation call first
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        # Mock actual embedding call
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, embedding_response]
        
        result = embedding_service.generate_text_embedding("test text", "amazon.titan-embed-text-v1")
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == sample_embedding
        assert result.model_id == "amazon.titan-embed-text-v1"
    
    def test_generate_titan_v2_embedding_with_embeddings_by_type(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Titan V2 model with embeddingsByType response format."""
        # Mock successful validation call first
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddingsByType': {'float': sample_embedding}}).encode())
        }
        # Mock actual embedding call with embeddingsByType format
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embeddingsByType': {'float': sample_embedding}}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, embedding_response]
        
        result = embedding_service.generate_text_embedding("test text", "amazon.titan-embed-text-v2:0")
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == sample_embedding
        assert result.model_id == "amazon.titan-embed-text-v2:0"
    
    def test_batch_generate_embeddings_success(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test successful batch embedding generation."""
        texts = ["text 1", "text 2", "text 3"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        # Mock individual embedding calls for Titan model
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response] + [embedding_response] * len(texts)
        
        results = embedding_service.batch_generate_embeddings(texts, "amazon.titan-embed-text-v2:0")
        
        assert len(results) == len(texts)
        for i, result in enumerate(results):
            assert isinstance(result, EmbeddingResult)
            assert result.embedding == sample_embedding
            assert result.input_text == texts[i]
            assert result.model_id == "amazon.titan-embed-text-v2:0"
    
    def test_batch_generate_embeddings_cohere(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test batch embedding generation with Cohere model."""
        texts = ["text 1", "text 2"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        # Mock batch embedding call
        batch_response = {
            'body': Mock(read=lambda: json.dumps({
                'embeddings': {'float': [sample_embedding, sample_embedding]}
            }).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, batch_response]
        
        results = embedding_service.batch_generate_embeddings(texts, "cohere.embed-english-v3")
        
        assert len(results) == len(texts)
        for i, result in enumerate(results):
            assert isinstance(result, EmbeddingResult)
            assert result.embedding == sample_embedding
            assert result.input_text == texts[i]
            assert result.model_id == "cohere.embed-english-v3"
    
    def test_batch_generate_embeddings_empty_list(self, embedding_service):
        """Test batch embedding generation with empty list."""
        with pytest.raises(ValidationError) as exc_info:
            embedding_service.batch_generate_embeddings([], "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "EMPTY_INPUT_LIST"
    
    def test_batch_generate_embeddings_empty_text_in_list(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test batch embedding generation with empty text in list."""
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = validation_response
        
        texts = ["text 1", "", "text 3"]
        
        with pytest.raises(ValidationError) as exc_info:
            embedding_service.batch_generate_embeddings(texts, "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "EMPTY_INPUT_TEXT"
        assert exc_info.value.error_details["index"] == 1
    
    def test_handle_bedrock_throttling_error(self, embedding_service, mock_bedrock_client):
        """Test handling of Bedrock throttling errors."""
        # Mock throttling error
        error_response = {
            'Error': {
                'Code': 'Throttling',
                'Message': 'Rate exceeded'
            }
        }
        mock_bedrock_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "SERVICE_UNAVAILABLE"
        assert exc_info.value.error_details["retry_suggested"] is True
    
    def test_handle_bedrock_validation_error(self, embedding_service, mock_bedrock_client):
        """Test handling of Bedrock validation errors."""
        # Mock validation error
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid input'
            }
        }
        mock_bedrock_client.invoke_model.side_effect = ClientError(error_response, 'InvokeModel')
        
        with pytest.raises(ValidationError) as exc_info:
            embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "INVALID_REQUEST"
    
    def test_handle_botocore_error(self, embedding_service, mock_bedrock_client):
        """Test handling of BotoCoreError."""
        mock_bedrock_client.invoke_model.side_effect = BotoCoreError()
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "AWS_SERVICE_ERROR"
    
    def test_estimate_cost(self, embedding_service):
        """Test cost estimation functionality."""
        texts = ["short text", "this is a longer text with more words"]
        
        cost_estimate = embedding_service.estimate_cost(texts, "amazon.titan-embed-text-v2:0")
        
        assert isinstance(cost_estimate, dict)
        assert cost_estimate["model_id"] == "amazon.titan-embed-text-v2:0"
        assert cost_estimate["text_count"] == 2
        assert cost_estimate["total_characters"] > 0
        assert cost_estimate["estimated_tokens"] > 0
        assert cost_estimate["cost_per_1k_tokens"] == 0.0001
        assert cost_estimate["estimated_cost_usd"] > 0
        assert cost_estimate["currency"] == "USD"
    
    def test_estimate_cost_default_model(self, embedding_service):
        """Test cost estimation with default model."""
        texts = ["test text"]
        
        cost_estimate = embedding_service.estimate_cost(texts)
        
        assert isinstance(cost_estimate, dict)
        assert "model_id" in cost_estimate
        assert cost_estimate["text_count"] == 1
    
    @patch('src.services.bedrock_embedding.time.time')
    def test_processing_time_tracking(self, mock_time, embedding_service, mock_bedrock_client, sample_embedding):
        """Test that processing time is tracked correctly."""
        # Mock time progression
        mock_time.side_effect = [1000.0, 1001.5]  # 1.5 second processing time
        
        # Mock successful responses
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, embedding_response]
        
        result = embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert result.processing_time_ms == 1500  # 1.5 seconds = 1500ms
    
    def test_unsupported_model_family(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test handling of unsupported model family."""
        # Mock validation to pass, but use unsupported model family
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.return_value = validation_response
        
        # Temporarily add unsupported model to test error handling
        embedding_service.SUPPORTED_MODELS['unsupported.model:0'] = ModelInfo(
            model_id='unsupported.model:0',
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description='Unsupported model for testing'
        )
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.generate_text_embedding("test", "unsupported.model:0")
        
        assert exc_info.value.error_code == "UNSUPPORTED_MODEL_FAMILY"
        
        # Clean up
        del embedding_service.SUPPORTED_MODELS['unsupported.model:0']
    
    @patch('src.services.bedrock_embedding.time.sleep')
    def test_retry_logic_success_after_throttling(self, mock_sleep, embedding_service, mock_bedrock_client, sample_embedding):
        """Test that retry logic works for throttling errors."""
        # Mock validation call to succeed
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        
        # Mock throttling error on first call, success on second
        throttling_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        success_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation call
            throttling_error,     # First embedding call fails
            success_response      # Second embedding call succeeds
        ]
        
        result = embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == sample_embedding
        assert mock_sleep.called  # Verify sleep was called for retry
    
    def test_retry_logic_max_retries_exceeded(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test that retry logic eventually gives up after max retries."""
        # Mock validation call to succeed
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        
        # Mock persistent throttling error
        throttling_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation call
            throttling_error,     # All embedding calls fail
            throttling_error,
            throttling_error
        ]
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.generate_text_embedding("test", "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "SERVICE_UNAVAILABLE"