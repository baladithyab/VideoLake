"""
Bedrock Embedding Service for generating text embeddings using Amazon Bedrock models.

This service provides text embedding generation using multiple Bedrock models
including Amazon Titan and Cohere embedding models with proper validation,
error handling, and batch processing capabilities.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from botocore.exceptions import ClientError, BotoCoreError
import time
import random

from src.config import config_manager
from src.utils.aws_clients import aws_client_factory
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embedding: List[float]
    input_text: str
    model_id: str
    token_count: Optional[int] = None
    processing_time_ms: Optional[int] = None


@dataclass
class ModelInfo:
    """Information about supported embedding models."""
    model_id: str
    dimensions: int
    max_input_tokens: int
    supports_batch: bool
    cost_per_1k_tokens: float
    description: str


class BedrockEmbeddingService:
    """Service for generating text embeddings using Amazon Bedrock models."""
    
    # Supported embedding models with their specifications
    SUPPORTED_MODELS = {
        'amazon.titan-embed-text-v2:0': ModelInfo(
            model_id='amazon.titan-embed-text-v2:0',
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description='Amazon Titan Text Embeddings V2 - Multilingual, configurable dimensions'
        ),
        'amazon.titan-embed-text-v1': ModelInfo(
            model_id='amazon.titan-embed-text-v1',
            dimensions=1536,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0001,
            description='Amazon Titan Text Embeddings G1 - Original Titan text model'
        ),
        'amazon.titan-embed-image-v1': ModelInfo(
            model_id='amazon.titan-embed-image-v1',
            dimensions=1024,
            max_input_tokens=8192,
            supports_batch=False,
            cost_per_1k_tokens=0.0008,
            description='Amazon Titan Multimodal Embeddings G1 - Text and image support'
        ),
        'cohere.embed-english-v3': ModelInfo(
            model_id='cohere.embed-english-v3',
            dimensions=1024,
            max_input_tokens=2048,
            supports_batch=True,
            cost_per_1k_tokens=0.0001,
            description='Cohere Embed English V3 - English optimized'
        ),
        'cohere.embed-multilingual-v3': ModelInfo(
            model_id='cohere.embed-multilingual-v3',
            dimensions=1024,
            max_input_tokens=2048,
            supports_batch=True,
            cost_per_1k_tokens=0.0001,
            description='Cohere Embed Multilingual V3 - Multilingual support'
        )
    }
    
    def __init__(self):
        """Initialize the Bedrock embedding service."""
        self.bedrock_client = aws_client_factory.get_bedrock_runtime_client()
        self.config = config_manager.aws_config
        
    def get_supported_models(self) -> Dict[str, ModelInfo]:
        """Get information about all supported embedding models."""
        return self.SUPPORTED_MODELS.copy()
    
    def validate_model_access(self, model_id: str) -> bool:
        """
        Validate that the specified model is accessible.
        
        Args:
            model_id: The Bedrock model ID to validate
            
        Returns:
            True if model is accessible, False otherwise
            
        Raises:
            ModelAccessError: If model validation fails
        """
        if model_id not in self.SUPPORTED_MODELS:
            raise ModelAccessError(
                f"Unsupported model: {model_id}. Supported models: {list(self.SUPPORTED_MODELS.keys())}",
                error_code="UNSUPPORTED_MODEL",
                error_details={"model_id": model_id, "supported_models": list(self.SUPPORTED_MODELS.keys())}
            )
        
        try:
            # Test model access with a simple embedding request
            test_text = "test"
            self._generate_single_embedding(test_text, model_id)
            logger.info(f"Model access validated successfully for {model_id}")
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code in ['AccessDeniedException', 'ValidationException']:
                raise ModelAccessError(
                    f"Access denied for model {model_id}: {e.response['Error']['Message']}",
                    error_code="MODEL_ACCESS_DENIED",
                    error_details={"model_id": model_id, "aws_error_code": error_code}
                )
            raise ModelAccessError(
                f"Model validation failed for {model_id}: {str(e)}",
                error_code="MODEL_VALIDATION_ERROR",
                error_details={"model_id": model_id, "original_error": str(e)}
            )
    
    def generate_text_embedding(self, text: str, model_id: Optional[str] = None) -> EmbeddingResult:
        """
        Generate embedding for a single text input.
        
        Args:
            text: Input text to embed
            model_id: Bedrock model ID (uses default if not specified)
            
        Returns:
            EmbeddingResult containing the embedding and metadata
            
        Raises:
            ValidationError: If input validation fails
            ModelAccessError: If model access fails
            VectorEmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise ValidationError(
                "Input text cannot be empty",
                error_code="EMPTY_INPUT_TEXT"
            )
        
        if model_id is None:
            model_id = self.config.bedrock_models['text_embedding']
        
        # Validate model access
        self.validate_model_access(model_id)
        
        # Validate input length
        model_info = self.SUPPORTED_MODELS[model_id]
        if len(text) > model_info.max_input_tokens * 4:  # Rough token estimation
            raise ValidationError(
                f"Input text too long for model {model_id}. Max tokens: {model_info.max_input_tokens}",
                error_code="INPUT_TOO_LONG",
                error_details={"model_id": model_id, "max_tokens": model_info.max_input_tokens}
            )
        
        start_time = time.time()
        
        try:
            embedding = self._generate_single_embedding(text, model_id)
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            result = EmbeddingResult(
                embedding=embedding,
                input_text=text,
                model_id=model_id,
                processing_time_ms=processing_time_ms
            )
            
            logger.info(f"Generated embedding for text (length: {len(text)}) using {model_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def batch_generate_embeddings(self, texts: List[str], model_id: Optional[str] = None) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple text inputs with batch processing.
        
        Args:
            texts: List of input texts to embed
            model_id: Bedrock model ID (uses default if not specified)
            
        Returns:
            List of EmbeddingResult objects
            
        Raises:
            ValidationError: If input validation fails
            ModelAccessError: If model access fails
            VectorEmbeddingError: If embedding generation fails
        """
        if not texts:
            raise ValidationError(
                "Input texts list cannot be empty",
                error_code="EMPTY_INPUT_LIST"
            )
        
        if model_id is None:
            model_id = self.config.bedrock_models['text_embedding']
        
        # Validate model access
        self.validate_model_access(model_id)
        model_info = self.SUPPORTED_MODELS[model_id]
        
        # Validate all inputs
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValidationError(
                    f"Text at index {i} cannot be empty",
                    error_code="EMPTY_INPUT_TEXT",
                    error_details={"index": i}
                )
        
        start_time = time.time()
        results = []
        
        try:
            if model_info.supports_batch and model_id.startswith('cohere'):
                # Use Cohere batch processing
                results = self._generate_cohere_batch_embeddings(texts, model_id)
            else:
                # Process individually for Titan models
                for text in texts:
                    embedding = self._generate_single_embedding(text, model_id)
                    results.append(EmbeddingResult(
                        embedding=embedding,
                        input_text=text,
                        model_id=model_id
                    ))
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update processing times
            for result in results:
                if result.processing_time_ms is None:
                    result.processing_time_ms = processing_time_ms // len(results)
            
            logger.info(f"Generated {len(results)} embeddings using {model_id}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise
    
    def _generate_single_embedding(self, text: str, model_id: str) -> List[float]:
        """
        Generate embedding for a single text using the specified model.
        
        Args:
            text: Input text
            model_id: Bedrock model ID
            
        Returns:
            List of float values representing the embedding
        """
        def _invoke_model():
            if model_id.startswith('amazon.titan'):
                return self._generate_titan_embedding(text, model_id)
            elif model_id.startswith('cohere'):
                return self._generate_cohere_embedding(text, model_id)
            else:
                raise VectorEmbeddingError(
                    f"Unsupported model family: {model_id}",
                    error_code="UNSUPPORTED_MODEL_FAMILY"
                )
        
        try:
            # Use retry logic for transient errors
            return self._retry_with_backoff(_invoke_model, max_retries=3)
                
        except ClientError as e:
            self._handle_bedrock_error(e, model_id)
        except BotoCoreError as e:
            raise VectorEmbeddingError(
                f"AWS service error: {str(e)}",
                error_code="AWS_SERVICE_ERROR",
                error_details={"model_id": model_id, "original_error": str(e)}
            )
    
    def _generate_titan_embedding(self, text: str, model_id: str) -> List[float]:
        """Generate embedding using Amazon Titan models."""
        if model_id == 'amazon.titan-embed-text-v2:0':
            # Titan Text V2 with configurable dimensions and embedding types
            request_body = {
                "inputText": text,
                "dimensions": 1024,
                "normalize": True,
                "embeddingTypes": ["float"]  # Specify float type explicitly
            }
        elif model_id == 'amazon.titan-embed-text-v1':
            # Titan Text V1 (G1) - simpler format
            request_body = {
                "inputText": text
            }
        else:
            # Titan Multimodal
            request_body = {
                "inputText": text
            }
        
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        # Handle different response formats for Titan models
        if model_id == 'amazon.titan-embed-text-v2:0':
            # V2 returns embeddingsByType structure
            if 'embeddingsByType' in response_body:
                return response_body['embeddingsByType']['float']
            else:
                # Fallback to embedding field if embeddingsByType not present
                return response_body['embedding']
        else:
            # V1 and multimodal return embedding directly
            return response_body['embedding']
    
    def _generate_cohere_embedding(self, text: str, model_id: str) -> List[float]:
        """Generate embedding using Cohere models."""
        request_body = {
            "texts": [text],
            "input_type": "search_document",
            "embedding_types": ["float"]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embeddings']['float'][0]
    
    def _generate_cohere_batch_embeddings(self, texts: List[str], model_id: str) -> List[EmbeddingResult]:
        """Generate embeddings using Cohere batch processing."""
        # Cohere supports up to 96 texts per call
        batch_size = min(96, len(texts))
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            request_body = {
                "texts": batch_texts,
                "input_type": "search_document",
                "embedding_types": ["float"]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            embeddings = response_body['embeddings']['float']
            
            for j, embedding in enumerate(embeddings):
                results.append(EmbeddingResult(
                    embedding=embedding,
                    input_text=batch_texts[j],
                    model_id=model_id
                ))
        
        return results
    
    def _handle_bedrock_error(self, error: ClientError, model_id: str) -> None:
        """Handle Bedrock-specific errors with appropriate exceptions."""
        error_code = error.response.get('Error', {}).get('Code', 'Unknown')
        error_message = error.response.get('Error', {}).get('Message', str(error))
        
        if error_code == 'AccessDeniedException':
            raise ModelAccessError(
                f"Access denied for model {model_id}: {error_message}",
                error_code="MODEL_ACCESS_DENIED",
                error_details={"model_id": model_id, "aws_error_code": error_code}
            )
        elif error_code == 'ValidationException':
            raise ValidationError(
                f"Invalid request for model {model_id}: {error_message}",
                error_code="INVALID_REQUEST",
                error_details={"model_id": model_id, "aws_error_code": error_code}
            )
        elif error_code in ['Throttling', 'ServiceUnavailable']:
            raise VectorEmbeddingError(
                f"Service temporarily unavailable for model {model_id}: {error_message}",
                error_code="SERVICE_UNAVAILABLE",
                error_details={"model_id": model_id, "aws_error_code": error_code, "retry_suggested": True}
            )
        else:
            raise VectorEmbeddingError(
                f"Bedrock API error for model {model_id}: {error_message}",
                error_code="BEDROCK_API_ERROR",
                error_details={"model_id": model_id, "aws_error_code": error_code}
            )
    
    def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """
        Implement exponential backoff retry logic for AWS API calls.
        
        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            
        Returns:
            Result from successful function call
        """
        for attempt in range(max_retries):
            try:
                return func()
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code in ['Throttling', 'ServiceUnavailable', 'InternalError']:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"Retrying after {delay:.2f}s due to {error_code} (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                # Re-raise non-retryable errors or final attempt
                raise
            except BotoCoreError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Retrying after {delay:.2f}s due to BotoCoreError (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                raise
    
    def estimate_cost(self, texts: List[str], model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Estimate the cost of generating embeddings for the given texts.
        
        Args:
            texts: List of input texts
            model_id: Bedrock model ID (uses default if not specified)
            
        Returns:
            Dictionary containing cost estimation details
        """
        if model_id is None:
            model_id = self.config.bedrock_models['text_embedding']
        
        model_info = self.SUPPORTED_MODELS[model_id]
        
        # Rough token estimation (4 characters per token)
        total_chars = sum(len(text) for text in texts)
        estimated_tokens = total_chars // 4
        
        estimated_cost = (estimated_tokens / 1000) * model_info.cost_per_1k_tokens
        
        return {
            "model_id": model_id,
            "text_count": len(texts),
            "total_characters": total_chars,
            "estimated_tokens": estimated_tokens,
            "cost_per_1k_tokens": model_info.cost_per_1k_tokens,
            "estimated_cost_usd": round(estimated_cost, 6),
            "currency": "USD"
        }