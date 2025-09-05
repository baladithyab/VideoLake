"""
Embedding Storage Integration Service.

This service integrates the Bedrock embedding generation with S3 Vector storage,
providing end-to-end functionality for text embedding processing and storage.
"""

import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from uuid import uuid4

from src.services.bedrock_embedding import BedrockEmbeddingService, EmbeddingResult
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorEmbeddingError, ValidationError, VectorStorageError
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


@dataclass
class TextEmbeddingMetadata:
    """Metadata for text embeddings stored in S3 Vectors."""
    content_type: str = "text"
    source_text: str = ""
    text_length: int = 0
    language: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    processing_timestamp: Optional[str] = None
    model_id: str = ""
    embedding_dimensions: int = 0
    processing_time_ms: Optional[int] = None
    confidence_score: Optional[float] = None
    
    # Business metadata for media companies
    content_id: Optional[str] = None
    series_id: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    genre: Optional[List[str]] = None
    actors: Optional[List[str]] = None
    director: Optional[str] = None
    release_date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for S3 Vector metadata, respecting 10-key limit."""
        # Essential fields (always included)
        result = {
            "content_type": self.content_type,
            "model_id": self.model_id,
            "text_length": self.text_length,
            "embedding_dimensions": self.embedding_dimensions
        }
        
        # Add important optional fields up to 10-key limit
        # Current count: 4 keys, can add 6 more
        optional_fields = [
            ("category", self.category),
            ("language", self.language), 
            ("content_id", self.content_id),
            ("series_id", self.series_id),
            ("season", self.season),
            ("episode", self.episode),
            ("source_text", self.source_text),
            ("confidence_score", self.confidence_score),
            ("processing_time_ms", self.processing_time_ms),
            ("processing_timestamp", self.processing_timestamp)
        ]
        
        added_keys = 4  # Already have 4 essential keys
        for field_name, field_value in optional_fields:
            if field_value is not None and added_keys < 10:
                if isinstance(field_value, list):
                    if len(field_value) > 0:  # Skip empty lists
                        result[field_name] = field_value
                        added_keys += 1
                else:
                    result[field_name] = field_value
                    added_keys += 1
        
        return result


@dataclass
class StoredEmbedding:
    """Result from storing an embedding in S3 Vectors."""
    vector_key: str
    embedding: List[float]
    metadata: TextEmbeddingMetadata
    storage_response: Dict[str, Any]
    index_arn: str
    created_at: str


class EmbeddingStorageIntegration:
    """
    Service that integrates Bedrock embedding generation with S3 Vector storage.
    
    This service provides end-to-end functionality for:
    - Generating text embeddings using Bedrock models
    - Creating appropriate metadata for text content
    - Storing embeddings in S3 Vector indexes with proper error handling
    - Batch processing capabilities for multiple texts
    """
    
    def __init__(self):
        """Initialize the integration service."""
        self.bedrock_service = BedrockEmbeddingService()
        self.storage_manager = S3VectorStorageManager()
        config_manager = get_unified_config_manager()
        self.config = config_manager.config.aws
        
        logger.info("Initialized EmbeddingStorageIntegration service")
    
    def store_text_embedding(self,
                           text: str,
                           index_arn: str,
                           model_id: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None,
                           vector_key: Optional[str] = None) -> StoredEmbedding:
        """
        Generate and store a text embedding in S3 Vectors.
        
        Args:
            text: Input text to embed and store
            index_arn: ARN of the S3 Vector index to store in
            model_id: Bedrock model ID (uses default if not specified)
            metadata: Additional metadata to attach to the vector
            vector_key: Custom key for the vector (generates UUID if not provided)
            
        Returns:
            StoredEmbedding containing the stored embedding and metadata
            
        Raises:
            ValidationError: If input validation fails
            VectorEmbeddingError: If embedding generation fails
            VectorStorageError: If storage operation fails
        """
        logger.info(f"Storing text embedding for text (length: {len(text)})")
        
        # Validate inputs
        if not text or not text.strip():
            raise ValidationError(
                "Input text cannot be empty",
                error_code="EMPTY_INPUT_TEXT"
            )
        
        if not index_arn:
            raise ValidationError(
                "Index ARN cannot be empty",
                error_code="EMPTY_INDEX_ARN"
            )
        
        # Generate vector key if not provided
        if vector_key is None:
            vector_key = f"text-{uuid4()}"
        
        try:
            # Generate embedding using Bedrock
            start_time = time.time()
            embedding_result = self.bedrock_service.generate_text_embedding(text, model_id)
            
            # Create metadata for the embedding
            embedding_metadata = self._create_text_metadata(
                text=text,
                embedding_result=embedding_result,
                additional_metadata=metadata
            )
            
            # Prepare vector data for storage (S3 Vectors format)
            vector_data = {
                "key": vector_key,
                "data": {
                    "float32": embedding_result.embedding
                },
                "metadata": embedding_metadata.to_dict()
            }
            
            # Store in S3 Vectors
            storage_response = self.storage_manager.put_vectors_batch(
                index_arn=index_arn,
                vectors_data=[vector_data]
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            stored_embedding = StoredEmbedding(
                vector_key=vector_key,
                embedding=embedding_result.embedding,
                metadata=embedding_metadata,
                storage_response=storage_response,
                index_arn=index_arn,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            
            logger.info(
                f"Successfully stored text embedding",
                extra={
                    "vector_key": vector_key,
                    "text_length": len(text),
                    "model_id": embedding_result.model_id,
                    "processing_time_ms": processing_time,
                    "embedding_dimensions": len(embedding_result.embedding)
                }
            )
            
            return stored_embedding
            
        except (VectorEmbeddingError, VectorStorageError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error storing text embedding: {str(e)}")
            raise VectorEmbeddingError(
                f"Failed to store text embedding: {str(e)}",
                error_code="STORAGE_INTEGRATION_ERROR",
                error_details={
                    "text_length": len(text),
                    "index_arn": index_arn,
                    "vector_key": vector_key,
                    "original_error": str(e)
                }
            )
    
    def batch_store_text_embeddings(self,
                                  texts: List[str],
                                  index_arn: str,
                                  model_id: Optional[str] = None,
                                  metadata_list: Optional[List[Dict[str, Any]]] = None,
                                  vector_keys: Optional[List[str]] = None,
                                  batch_size: Optional[int] = None) -> List[StoredEmbedding]:
        """
        Generate and store embeddings for multiple texts with batch processing.
        
        Args:
            texts: List of input texts to embed and store
            index_arn: ARN of the S3 Vector index to store in
            model_id: Bedrock model ID (uses default if not specified)
            metadata_list: List of additional metadata for each text (optional)
            vector_keys: List of custom keys for vectors (generates UUIDs if not provided)
            batch_size: Override default batch size for processing
            
        Returns:
            List of StoredEmbedding objects
            
        Raises:
            ValidationError: If input validation fails
            VectorEmbeddingError: If embedding generation fails
            VectorStorageError: If storage operation fails
        """
        logger.info(f"Batch storing embeddings for {len(texts)} texts")
        
        # Validate inputs
        if not texts:
            raise ValidationError(
                "Input texts list cannot be empty",
                error_code="EMPTY_INPUT_LIST"
            )
        
        if not index_arn:
            raise ValidationError(
                "Index ARN cannot be empty",
                error_code="EMPTY_INDEX_ARN"
            )
        
        # Validate metadata list length if provided
        if metadata_list is not None and len(metadata_list) != len(texts):
            raise ValidationError(
                f"Metadata list length ({len(metadata_list)}) must match texts length ({len(texts)})",
                error_code="METADATA_LENGTH_MISMATCH",
                error_details={
                    "texts_count": len(texts),
                    "metadata_count": len(metadata_list)
                }
            )
        
        # Generate vector keys if not provided
        if vector_keys is None:
            vector_keys = [f"text-{uuid4()}" for _ in texts]
        elif len(vector_keys) != len(texts):
            raise ValidationError(
                f"Vector keys length ({len(vector_keys)}) must match texts length ({len(texts)})",
                error_code="VECTOR_KEYS_LENGTH_MISMATCH",
                error_details={
                    "texts_count": len(texts),
                    "vector_keys_count": len(vector_keys)
                }
            )
        
        try:
            start_time = time.time()
            
            # Generate embeddings using batch processing
            embedding_results = self.bedrock_service.batch_generate_embeddings(
                texts=texts,
                model_id=model_id,
                batch_size=batch_size
            )
            
            # Prepare vector data for batch storage
            vectors_data = []
            stored_embeddings = []
            
            for i, (text, embedding_result, vector_key) in enumerate(zip(texts, embedding_results, vector_keys)):
                # Get additional metadata for this text
                additional_metadata = metadata_list[i] if metadata_list else None
                
                # Create metadata for the embedding
                embedding_metadata = self._create_text_metadata(
                    text=text,
                    embedding_result=embedding_result,
                    additional_metadata=additional_metadata
                )
                
                # Prepare vector data (S3 Vectors format)
                vector_data = {
                    "key": vector_key,
                    "data": {
                        "float32": embedding_result.embedding
                    },
                    "metadata": embedding_metadata.to_dict()
                }
                vectors_data.append(vector_data)
                
                # Prepare stored embedding result
                stored_embeddings.append(StoredEmbedding(
                    vector_key=vector_key,
                    embedding=embedding_result.embedding,
                    metadata=embedding_metadata,
                    storage_response={},  # Will be updated after storage
                    index_arn=index_arn,
                    created_at=datetime.now(timezone.utc).isoformat()
                ))
            
            # Store all vectors in batch
            storage_response = self.storage_manager.put_vectors_batch(
                index_arn=index_arn,
                vectors_data=vectors_data
            )
            
            # Update storage response in all stored embeddings
            for stored_embedding in stored_embeddings:
                stored_embedding.storage_response = storage_response
            
            processing_time = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"Successfully batch stored {len(stored_embeddings)} text embeddings",
                extra={
                    "texts_count": len(texts),
                    "model_id": embedding_results[0].model_id if embedding_results else "unknown",
                    "processing_time_ms": processing_time,
                    "average_text_length": sum(len(text) for text in texts) / len(texts),
                    "total_vectors_stored": len(vectors_data)
                }
            )
            
            return stored_embeddings
            
        except (VectorEmbeddingError, VectorStorageError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in batch storage: {str(e)}")
            raise VectorEmbeddingError(
                f"Failed to batch store text embeddings: {str(e)}",
                error_code="BATCH_STORAGE_INTEGRATION_ERROR",
                error_details={
                    "texts_count": len(texts),
                    "index_arn": index_arn,
                    "original_error": str(e)
                }
            )
    
    def search_similar_text(self,
                          query_text: str,
                          index_arn: str,
                          top_k: int = 10,
                          model_id: Optional[str] = None,
                          metadata_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Search for similar text embeddings using a text query.
        
        Args:
            query_text: Text to search for similar content
            index_arn: ARN of the S3 Vector index to search in
            top_k: Number of similar results to return
            model_id: Bedrock model ID for query embedding (uses default if not specified)
            metadata_filters: Optional metadata filters for the search
            
        Returns:
            Dictionary containing search results and metadata
            
        Raises:
            ValidationError: If input validation fails
            VectorEmbeddingError: If query embedding generation fails
            VectorStorageError: If search operation fails
        """
        logger.info(f"Searching for similar text (query length: {len(query_text)}, top_k: {top_k})")
        
        # Validate inputs
        if not query_text or not query_text.strip():
            raise ValidationError(
                "Query text cannot be empty",
                error_code="EMPTY_QUERY_TEXT"
            )
        
        if not index_arn:
            raise ValidationError(
                "Index ARN cannot be empty",
                error_code="EMPTY_INDEX_ARN"
            )
        
        if top_k < 1 or top_k > 100:
            raise ValidationError(
                f"top_k must be between 1 and 100, got {top_k}",
                error_code="INVALID_TOP_K",
                error_details={"top_k": top_k}
            )
        
        try:
            start_time = time.time()
            
            # Generate query embedding
            query_embedding_result = self.bedrock_service.generate_text_embedding(query_text, model_id)
            
            # Search for similar vectors
            search_response = self.storage_manager.query_similar_vectors(
                index_arn=index_arn,
                query_vector=query_embedding_result.embedding,
                top_k=top_k,
                metadata_filters=metadata_filters
            )
            
            search_time_ms = int((time.time() - start_time) * 1000)
            
            # Process and enrich search results
            results = search_response.get('vectors', [])
            processed_results = []
            
            for result in results:
                processed_result = {
                    'vector_key': result.get('key'),
                    'similarity_score': round(1 - result.get('distance', 1.0), 4),
                    'metadata': result.get('metadata', {}),
                    'embedding': result.get('data', {}).get('float32', [])
                }
                processed_results.append(processed_result)
            
            search_result = {
                'query_text': query_text,
                'query_model_id': query_embedding_result.model_id,
                'results': processed_results,
                'total_results': len(processed_results),
                'search_time_ms': search_time_ms,
                'index_arn': index_arn,
                'metadata_filters': metadata_filters,
                'top_k_requested': top_k
            }
            
            logger.info(
                f"Successfully searched for similar text",
                extra={
                    "query_length": len(query_text),
                    "results_found": len(processed_results),
                    "search_time_ms": search_time_ms,
                    "model_id": query_embedding_result.model_id
                }
            )
            
            return search_result
            
        except (VectorEmbeddingError, VectorStorageError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error searching similar text: {str(e)}")
            raise VectorEmbeddingError(
                f"Failed to search similar text: {str(e)}",
                error_code="SEARCH_INTEGRATION_ERROR",
                error_details={
                    "query_text_length": len(query_text),
                    "index_arn": index_arn,
                    "top_k": top_k,
                    "original_error": str(e)
                }
            )
    
    def _create_text_metadata(self,
                            text: str,
                            embedding_result: EmbeddingResult,
                            additional_metadata: Optional[Dict[str, Any]] = None) -> TextEmbeddingMetadata:
        """
        Create metadata for a text embedding.
        
        Args:
            text: Original text content
            embedding_result: Result from embedding generation
            additional_metadata: Additional metadata to include
            
        Returns:
            TextEmbeddingMetadata object
        """
        # Create base metadata
        metadata = TextEmbeddingMetadata(
            content_type="text",
            source_text=text[:500] if len(text) > 500 else text,  # Truncate for storage efficiency
            text_length=len(text),
            processing_timestamp=datetime.now(timezone.utc).isoformat(),
            model_id=embedding_result.model_id,
            embedding_dimensions=len(embedding_result.embedding),
            processing_time_ms=embedding_result.processing_time_ms
        )
        
        # Add additional metadata if provided
        if additional_metadata:
            for key, value in additional_metadata.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
                else:
                    # For unknown fields, we could add them to a custom_metadata dict
                    # but for now, we'll log and skip
                    logger.debug(f"Skipping unknown metadata field: {key}")
        
        return metadata
    
    def get_embedding_by_key(self,
                           vector_key: str,
                           index_arn: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific embedding by its vector key.
        
        Args:
            vector_key: Key of the vector to retrieve
            index_arn: ARN of the S3 Vector index
            
        Returns:
            Dictionary containing the embedding and metadata, or None if not found
            
        Raises:
            ValidationError: If input validation fails
            VectorStorageError: If retrieval operation fails
        """
        logger.info(f"Retrieving embedding by key: {vector_key}")
        
        # Validate inputs
        if not vector_key:
            raise ValidationError(
                "Vector key cannot be empty",
                error_code="EMPTY_VECTOR_KEY"
            )
        
        if not index_arn:
            raise ValidationError(
                "Index ARN cannot be empty",
                error_code="EMPTY_INDEX_ARN"
            )
        
        try:
            # Use list_vectors to find the specific key
            # Note: This is a simplified implementation. In a real scenario,
            # you might want to implement a more efficient key-based lookup
            vectors_response = self.storage_manager.list_vectors(
                index_arn=index_arn,
                max_results=1000  # Adjust based on your needs
            )
            
            vectors = vectors_response.get('vectors', [])
            
            # Find the vector with matching key
            for vector in vectors:
                if vector.get('key') == vector_key:
                    logger.info(f"Successfully retrieved embedding by key: {vector_key}")
                    return {
                        'vector_key': vector.get('key'),
                        'embedding': vector.get('data', {}).get('float32', []),
                        'metadata': vector.get('metadata', {}),
                        'index_arn': index_arn
                    }
            
            logger.info(f"Embedding not found for key: {vector_key}")
            return None
            
        except VectorStorageError:
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving embedding by key: {str(e)}")
            raise VectorStorageError(
                f"Failed to retrieve embedding by key {vector_key}: {str(e)}",
                error_code="RETRIEVAL_INTEGRATION_ERROR",
                error_details={
                    "vector_key": vector_key,
                    "index_arn": index_arn,
                    "original_error": str(e)
                }
            )
    
    def estimate_storage_cost(self,
                            texts: List[str],
                            model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Estimate the cost of storing embeddings for the given texts.
        
        Args:
            texts: List of texts to estimate cost for
            model_id: Bedrock model ID (uses default if not specified)
            
        Returns:
            Dictionary containing cost estimates
        """
        logger.info(f"Estimating storage cost for {len(texts)} texts")
        
        # Get embedding cost estimate from Bedrock service
        embedding_cost = self.bedrock_service.estimate_cost(texts, model_id)
        
        # Estimate S3 Vectors storage cost
        # Assuming 1024 dimensions * 4 bytes per float = 4KB per vector
        vector_size_kb = 4  # Approximate size per vector in KB
        total_storage_kb = len(texts) * vector_size_kb
        
        # S3 Vectors pricing (approximate)
        storage_cost_per_gb_month = 0.023  # USD
        storage_cost_per_kb_month = storage_cost_per_gb_month / (1024 * 1024)
        monthly_storage_cost = total_storage_kb * storage_cost_per_kb_month
        
        # Query cost estimation (approximate)
        query_cost_per_1k = 0.01  # USD per 1000 queries
        
        cost_estimate = {
            'embedding_generation': embedding_cost,
            'storage': {
                'total_vectors': len(texts),
                'vector_size_kb': vector_size_kb,
                'total_storage_kb': total_storage_kb,
                'monthly_storage_cost_usd': round(monthly_storage_cost, 6),
                'annual_storage_cost_usd': round(monthly_storage_cost * 12, 4)
            },
            'query_costs': {
                'cost_per_1k_queries_usd': query_cost_per_1k,
                'estimated_cost_per_query_usd': query_cost_per_1k / 1000
            },
            'total_setup_cost_usd': embedding_cost.get('total_cost_usd', 0),
            'ongoing_monthly_cost_usd': round(monthly_storage_cost, 6)
        }
        
        logger.info(
            f"Cost estimate completed",
            extra={
                "texts_count": len(texts),
                "setup_cost": cost_estimate['total_setup_cost_usd'],
                "monthly_cost": cost_estimate['ongoing_monthly_cost_usd']
            }
        )
        
        return cost_estimate