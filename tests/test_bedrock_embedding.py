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
        assert titan_v1_model.dimensions == 1024
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


class TestBatchProcessingEnhancements:
    """Test cases for enhanced batch processing capabilities."""
    
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
    
    def test_batch_generate_embeddings_with_custom_batch_size(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test batch processing with custom batch size."""
        texts = ["text 1", "text 2", "text 3", "text 4", "text 5"]
        custom_batch_size = 2
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        # Mock individual embedding calls
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response] + [embedding_response] * len(texts)
        
        results = embedding_service.batch_generate_embeddings(
            texts, 
            "amazon.titan-embed-text-v2:0",
            batch_size=custom_batch_size
        )
        
        assert len(results) == len(texts)
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert result.embedding == sample_embedding
    
    def test_batch_generate_embeddings_with_rate_limiting(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test batch processing with rate limiting."""
        texts = ["text 1", "text 2", "text 3"]
        rate_limit_delay = 0.01  # Small delay for testing
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        # Mock batch embedding calls for Cohere
        batch_response = {
            'body': Mock(read=lambda: json.dumps({
                'embeddings': {'float': [sample_embedding] * len(texts)}
            }).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response, batch_response]
        
        with patch('src.services.bedrock_embedding.time.sleep') as mock_sleep:
            results = embedding_service.batch_generate_embeddings(
                texts, 
                "cohere.embed-english-v3",
                rate_limit_delay=rate_limit_delay
            )
        
        assert len(results) == len(texts)
        # Sleep should not be called for single batch
        assert not mock_sleep.called
    
    def test_batch_generate_embeddings_cohere_with_multiple_batches(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Cohere batch processing with multiple batches and rate limiting."""
        # Create enough texts to require multiple batches
        texts = [f"text {i}" for i in range(10)]
        batch_size = 3
        rate_limit_delay = 0.01
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        
        # Mock multiple batch responses
        def create_batch_response(batch_texts):
            return {
                'body': Mock(read=lambda: json.dumps({
                    'embeddings': {'float': [sample_embedding] * len(batch_texts)}
                }).encode())
            }
        
        # Calculate expected batches
        expected_batches = (len(texts) + batch_size - 1) // batch_size
        batch_responses = [create_batch_response(texts[i:i+batch_size]) for i in range(0, len(texts), batch_size)]
        
        mock_bedrock_client.invoke_model.side_effect = [validation_response] + batch_responses
        
        with patch('src.services.bedrock_embedding.time.sleep') as mock_sleep:
            results = embedding_service.batch_generate_embeddings(
                texts, 
                "cohere.embed-english-v3",
                batch_size=batch_size,
                rate_limit_delay=rate_limit_delay
            )
        
        assert len(results) == len(texts)
        # Sleep should be called between batches (expected_batches - 1 times)
        assert mock_sleep.call_count == expected_batches - 1
        for call in mock_sleep.call_args_list:
            assert call[0][0] == rate_limit_delay
    
    def test_batch_generate_embeddings_titan_with_concurrency(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Titan batch processing with concurrency control."""
        texts = ["text 1", "text 2", "text 3", "text 4"]
        max_concurrent = 2
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        # Mock individual embedding calls
        embedding_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        mock_bedrock_client.invoke_model.side_effect = [validation_response] + [embedding_response] * len(texts)
        
        results = embedding_service.batch_generate_embeddings(
            texts, 
            "amazon.titan-embed-text-v2:0",
            max_concurrent=max_concurrent
        )
        
        assert len(results) == len(texts)
        for result in results:
            assert isinstance(result, EmbeddingResult)
            assert result.embedding == sample_embedding
    
    def test_batch_processing_partial_failure_handling(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test handling of partial failures in batch processing."""
        texts = ["text 1", "text 2", "text 3"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        
        # Mock responses: success, failure, success
        success_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        failure_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'InvokeModel'
        )
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation
            success_response,     # First text succeeds
            failure_error,        # Second text fails
            success_response      # Third text succeeds
        ]
        
        # Should still return successful results
        results = embedding_service.batch_generate_embeddings(texts, "amazon.titan-embed-text-v2:0")
        
        # Should have 2 successful results (first and third texts)
        assert len(results) == 2
        assert all(result.embedding == sample_embedding for result in results)
    
    def test_batch_processing_complete_failure(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test handling when all batch items fail."""
        texts = ["text 1", "text 2"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embedding': sample_embedding}).encode())
        }
        
        # Mock all embedding calls to fail
        failure_error = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}},
            'InvokeModel'
        )
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation succeeds
            failure_error,        # All embedding calls fail
            failure_error
        ]
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.batch_generate_embeddings(texts, "amazon.titan-embed-text-v2:0")
        
        assert exc_info.value.error_code == "BATCH_COMPLETE_FAILURE"
        assert exc_info.value.error_details["failed_count"] == 2
        assert exc_info.value.error_details["total_count"] == 2
    
    def test_get_optimal_batch_size(self, embedding_service):
        """Test optimal batch size calculation."""
        # Test small input
        batch_size = embedding_service._get_optimal_batch_size("amazon.titan-embed-text-v2:0", 5)
        assert batch_size <= 5
        
        # Test medium input
        batch_size = embedding_service._get_optimal_batch_size("amazon.titan-embed-text-v2:0", 50)
        assert batch_size <= 50
        
        # Test large input
        batch_size = embedding_service._get_optimal_batch_size("amazon.titan-embed-text-v2:0", 200)
        assert batch_size <= 200
        
        # Test Cohere model
        batch_size = embedding_service._get_optimal_batch_size("cohere.embed-english-v3", 200)
        assert batch_size <= 200
    
    def test_get_batch_processing_recommendations(self, embedding_service):
        """Test batch processing recommendations."""
        texts = ["text 1", "text 2", "text 3"] * 10  # 30 texts
        
        recommendations = embedding_service.get_batch_processing_recommendations(
            texts, "amazon.titan-embed-text-v2:0"
        )
        
        assert isinstance(recommendations, dict)
        assert recommendations["model_id"] == "amazon.titan-embed-text-v2:0"
        assert recommendations["total_texts"] == 30
        assert recommendations["supports_native_batch"] is False
        assert "recommended_batch_size" in recommendations
        assert "recommended_concurrent_requests" in recommendations
        assert "estimated_api_requests" in recommendations
        assert "estimated_processing_time_seconds" in recommendations
        assert "cost_estimate" in recommendations
        assert "rate_limiting_recommendations" in recommendations
    
    def test_get_batch_processing_recommendations_cohere(self, embedding_service):
        """Test batch processing recommendations for Cohere model."""
        texts = ["text 1", "text 2", "text 3"] * 20  # 60 texts
        
        recommendations = embedding_service.get_batch_processing_recommendations(
            texts, "cohere.embed-english-v3"
        )
        
        assert recommendations["model_id"] == "cohere.embed-english-v3"
        assert recommendations["total_texts"] == 60
        assert recommendations["supports_native_batch"] is True
        assert recommendations["recommended_concurrent_requests"] == 1  # Native batch processing
    
    @patch('src.services.bedrock_embedding.time.sleep')
    def test_cohere_batch_processing_with_retry_logic(self, mock_sleep, embedding_service, mock_bedrock_client, sample_embedding):
        """Test Cohere batch processing with retry logic on failures."""
        texts = ["text 1", "text 2"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        
        # Mock throttling error on first call, success on retry
        throttling_error = ClientError(
            {'Error': {'Code': 'Throttling', 'Message': 'Rate exceeded'}},
            'InvokeModel'
        )
        success_response = {
            'body': Mock(read=lambda: json.dumps({
                'embeddings': {'float': [sample_embedding, sample_embedding]}
            }).encode())
        }
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation
            throttling_error,     # First batch call fails
            success_response      # Retry succeeds
        ]
        
        results = embedding_service.batch_generate_embeddings(texts, "cohere.embed-english-v3")
        
        assert len(results) == len(texts)
        assert all(result.embedding == sample_embedding for result in results)
        assert mock_sleep.called  # Verify retry logic was used
    
    def test_batch_processing_error_details(self, embedding_service, mock_bedrock_client, sample_embedding):
        """Test that batch processing errors include detailed information."""
        texts = ["text 1", "text 2"]
        
        # Mock validation call
        validation_response = {
            'body': Mock(read=lambda: json.dumps({'embeddings': {'float': [sample_embedding]}}).encode())
        }
        
        # Mock persistent error in batch processing
        persistent_error = ClientError(
            {'Error': {'Code': 'ServiceUnavailable', 'Message': 'Service unavailable'}},
            'InvokeModel'
        )
        
        mock_bedrock_client.invoke_model.side_effect = [
            validation_response,  # Validation
            persistent_error,     # Batch processing fails
            persistent_error,     # Retry fails
            persistent_error      # Final retry fails
        ]
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            embedding_service.batch_generate_embeddings(texts, "cohere.embed-english-v3")
        
        assert exc_info.value.error_code == "BATCH_PROCESSING_ERROR"
        assert "batch_number" in exc_info.value.error_details
        assert "total_batches" in exc_info.value.error_details
        assert "batch_size" in exc_info.value.error_details
        assert "original_error" in exc_info.value.error_details