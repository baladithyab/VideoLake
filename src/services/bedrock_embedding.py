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
    
    def batch_generate_embeddings(self, 
                                texts: List[str], 
                                model_id: Optional[str] = None,
                                batch_size: Optional[int] = None,
                                max_concurrent: int = 5,
                                rate_limit_delay: float = 0.1) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple text inputs with advanced batch processing.
        
        Features:
        - Configurable batch sizes for optimal performance
        - Rate limiting and throttling management
        - Concurrent processing with limits
        - Comprehensive error handling and retry logic
        - Progress tracking for large batches
        
        Args:
            texts: List of input texts to embed
            model_id: Bedrock model ID (uses default if not specified)
            batch_size: Override default batch size for processing
            max_concurrent: Maximum concurrent requests (default: 5)
            rate_limit_delay: Delay between batches in seconds (default: 0.1)
            
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
        
        # Determine optimal batch size
        if batch_size is None:
            batch_size = self._get_optimal_batch_size(model_id, len(texts))
        
        start_time = time.time()
        results = []
        failed_items = []
        
        try:
            if model_info.supports_batch and model_id.startswith('cohere'):
                # Use Cohere native batch processing with rate limiting
                results = self._generate_cohere_batch_embeddings_with_rate_limiting(
                    texts, model_id, batch_size, rate_limit_delay
                )
            else:
                # Process individually for Titan models with concurrency control
                results, failed_items = self._generate_titan_batch_embeddings_with_concurrency(
                    texts, model_id, batch_size, max_concurrent, rate_limit_delay
                )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update processing times
            for result in results:
                if result.processing_time_ms is None:
                    result.processing_time_ms = processing_time_ms // len(results)
            
            # Handle partial failures
            if failed_items:
                logger.warning(f"Failed to process {len(failed_items)} out of {len(texts)} texts")
                # Optionally retry failed items or raise partial failure error
                if len(failed_items) == len(texts):
                    raise VectorEmbeddingError(
                        "All batch items failed to process",
                        error_code="BATCH_COMPLETE_FAILURE",
                        error_details={"failed_count": len(failed_items), "total_count": len(texts)}
                    )
            
            logger.info(f"Generated {len(results)} embeddings using {model_id} (batch size: {batch_size})")
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
    
    def _generate_cohere_batch_embeddings_with_rate_limiting(self, 
                                                           texts: List[str], 
                                                           model_id: str,
                                                           batch_size: int,
                                                           rate_limit_delay: float) -> List[EmbeddingResult]:
        """Generate embeddings using Cohere batch processing with rate limiting."""
        # Cohere supports up to 96 texts per call, but respect user's batch_size
        effective_batch_size = min(96, batch_size)
        results = []
        total_batches = (len(texts) + effective_batch_size - 1) // effective_batch_size
        
        for batch_num, i in enumerate(range(0, len(texts), effective_batch_size)):
            batch_texts = texts[i:i + effective_batch_size]
            
            def _process_cohere_batch():
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
                return response_body['embeddings']['float']
            
            try:
                # Use retry logic for each batch
                embeddings = self._retry_with_backoff(_process_cohere_batch, max_retries=3)
                
                for j, embedding in enumerate(embeddings):
                    results.append(EmbeddingResult(
                        embedding=embedding,
                        input_text=batch_texts[j],
                        model_id=model_id
                    ))
                
                logger.debug(f"Processed batch {batch_num + 1}/{total_batches} ({len(batch_texts)} texts)")
                
                # Rate limiting delay between batches (except for the last batch)
                if batch_num < total_batches - 1 and rate_limit_delay > 0:
                    time.sleep(rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"Failed to process Cohere batch {batch_num + 1}: {str(e)}")
                raise VectorEmbeddingError(
                    f"Batch processing failed at batch {batch_num + 1}",
                    error_code="BATCH_PROCESSING_ERROR",
                    error_details={
                        "batch_number": batch_num + 1,
                        "total_batches": total_batches,
                        "batch_size": len(batch_texts),
                        "original_error": str(e)
                    }
                )
        
        return results
    
    def _generate_titan_batch_embeddings_with_concurrency(self, 
                                                        texts: List[str], 
                                                        model_id: str,
                                                        batch_size: int,
                                                        max_concurrent: int,
                                                        rate_limit_delay: float) -> tuple[List[EmbeddingResult], List[str]]:
        """Generate embeddings for Titan models with concurrency control and rate limiting."""
        import concurrent.futures
        import threading
        
        results = []
        failed_items = []
        results_lock = threading.Lock()
        
        # Create batches for processing
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
        def _process_batch(batch_texts: List[str], batch_index: int) -> None:
            """Process a single batch of texts."""
            batch_results = []
            batch_failures = []
            
            for text in batch_texts:
                try:
                    embedding = self._generate_single_embedding(text, model_id)
                    batch_results.append(EmbeddingResult(
                        embedding=embedding,
                        input_text=text,
                        model_id=model_id
                    ))
                except Exception as e:
                    logger.warning(f"Failed to generate embedding for text in batch {batch_index}: {str(e)}")
                    batch_failures.append(text)
            
            # Thread-safe update of results
            with results_lock:
                results.extend(batch_results)
                failed_items.extend(batch_failures)
            
            logger.debug(f"Completed batch {batch_index + 1}/{len(batches)} ({len(batch_results)} successful, {len(batch_failures)} failed)")
            
            # Rate limiting delay
            if rate_limit_delay > 0:
                time.sleep(rate_limit_delay)
        
        # Process batches with controlled concurrency
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Submit all batch processing tasks
            future_to_batch = {
                executor.submit(_process_batch, batch, i): i 
                for i, batch in enumerate(batches)
            }
            
            # Wait for completion and handle any exceptions
            for future in concurrent.futures.as_completed(future_to_batch):
                batch_index = future_to_batch[future]
                try:
                    future.result()  # This will raise any exception that occurred
                except Exception as e:
                    logger.error(f"Batch {batch_index + 1} processing failed: {str(e)}")
                    # Continue processing other batches
        
        return results, failed_items
    
    def _get_optimal_batch_size(self, model_id: str, total_texts: int) -> int:
        """Determine optimal batch size based on model and input size."""
        model_info = self.SUPPORTED_MODELS[model_id]
        
        if model_id.startswith('cohere') and model_info.supports_batch:
            # Cohere can handle up to 96 texts per call
            if total_texts <= 10:
                return min(total_texts, 5)  # Small batches for small inputs
            elif total_texts <= 100:
                return min(total_texts, 20)  # Medium batches
            else:
                return min(total_texts, 50)  # Larger batches for efficiency
        else:
            # Titan models process individually, so batch size affects concurrency
            if total_texts <= 10:
                return min(total_texts, 3)  # Small batches
            elif total_texts <= 100:
                return min(total_texts, 10)  # Medium batches
            else:
                return min(total_texts, 25)  # Larger batches for efficiency
    
    def get_batch_processing_recommendations(self, texts: List[str], model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get recommendations for optimal batch processing parameters.
        
        Args:
            texts: List of input texts
            model_id: Bedrock model ID (uses default if not specified)
            
        Returns:
            Dictionary with recommended batch processing parameters
        """
        if model_id is None:
            model_id = self.config.bedrock_models['text_embedding']
        
        model_info = self.SUPPORTED_MODELS[model_id]
        total_texts = len(texts)
        
        # Calculate optimal parameters
        optimal_batch_size = self._get_optimal_batch_size(model_id, total_texts)
        
        # Estimate processing time and cost
        cost_estimate = self.estimate_cost(texts, model_id)
        
        # Determine recommended concurrency
        if model_info.supports_batch:
            recommended_concurrent = 1  # Native batch processing
            estimated_requests = (total_texts + optimal_batch_size - 1) // optimal_batch_size
        else:
            recommended_concurrent = min(5, max(1, total_texts // 10))  # Scale with input size
            estimated_requests = total_texts
        
        # Estimate processing time (rough calculation)
        avg_request_time = 2.0  # seconds per request
        estimated_time_sequential = estimated_requests * avg_request_time
        estimated_time_concurrent = estimated_time_sequential / recommended_concurrent
        
        return {
            "model_id": model_id,
            "total_texts": total_texts,
            "supports_native_batch": model_info.supports_batch,
            "recommended_batch_size": optimal_batch_size,
            "recommended_concurrent_requests": recommended_concurrent,
            "estimated_api_requests": estimated_requests,
            "estimated_processing_time_seconds": {
                "sequential": round(estimated_time_sequential, 1),
                "concurrent": round(estimated_time_concurrent, 1)
            },
            "cost_estimate": cost_estimate,
            "rate_limiting_recommendations": {
                "delay_between_batches": 0.1 if total_texts > 100 else 0.05,
                "max_concurrent_requests": recommended_concurrent
            }
        }
    
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