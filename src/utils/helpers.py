"""
Helper utilities for the S3 Vector Embedding POC.

This module provides common utility functions for batch processing,
retry logic, and data validation.
"""

import time
import random
import logging
from typing import List, Iterator, TypeVar, Callable, Any, Dict, Optional
from functools import wraps
from botocore.exceptions import ClientError, BotoCoreError

from src.exceptions import VectorEmbeddingError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def batch_items(items: List[T], batch_size: int) -> Iterator[List[T]]:
    """
    Split items into batches of specified size.
    
    Args:
        items: List of items to batch
        batch_size: Maximum size of each batch
        
    Yields:
        List[T]: Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> Callable:
    """
    Decorator for implementing exponential backoff retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay on each retry
        jitter: Whether to add random jitter to delays
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    
                    # Retry on specific AWS error codes
                    if error_code in ['Throttling', 'ServiceUnavailable', 'InternalError', 'RequestTimeout']:
                        last_exception = e
                        
                        if attempt < max_retries:
                            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                            if jitter:
                                delay += random.uniform(0, delay * 0.1)
                            
                            logger.warning(
                                f"Attempt {attempt + 1} failed with {error_code}, "
                                f"retrying in {delay:.2f} seconds"
                            )
                            time.sleep(delay)
                            continue
                    
                    # Don't retry on other client errors
                    raise
                    
                except BotoCoreError as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                        if jitter:
                            delay += random.uniform(0, delay * 0.1)
                        
                        logger.warning(
                            f"Attempt {attempt + 1} failed with BotoCoreError, "
                            f"retrying in {delay:.2f} seconds"
                        )
                        time.sleep(delay)
                        continue
                    
                    raise
                    
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    raise
            
            # If we get here, all retries failed
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def validate_vector_dimensions(vectors: List[List[float]], expected_dim: int = 1024) -> None:
    """
    Validate that all vectors have the expected dimensions.
    
    Args:
        vectors: List of vector embeddings
        expected_dim: Expected vector dimension
        
    Raises:
        ValidationError: If vectors have incorrect dimensions
    """
    from src.exceptions import ValidationError
    
    if not vectors:
        raise ValidationError("Vector list cannot be empty")
    
    for i, vector in enumerate(vectors):
        if len(vector) != expected_dim:
            raise ValidationError(
                f"Vector at index {i} has {len(vector)} dimensions, expected {expected_dim}",
                error_code="INVALID_VECTOR_DIMENSION",
                error_details={
                    "vector_index": i,
                    "actual_dimensions": len(vector),
                    "expected_dimensions": expected_dim
                }
            )


def validate_metadata(metadata: Dict[str, Any]) -> None:
    """
    Validate metadata structure and content.
    
    Args:
        metadata: Metadata dictionary to validate
        
    Raises:
        ValidationError: If metadata is invalid
    """
    from src.exceptions import ValidationError
    
    if not isinstance(metadata, dict):
        raise ValidationError(
            "Metadata must be a dictionary",
            error_code="INVALID_METADATA_TYPE"
        )
    
    # Check for required fields
    required_fields = ['content_type']
    for field in required_fields:
        if field not in metadata:
            raise ValidationError(
                f"Required metadata field '{field}' is missing",
                error_code="MISSING_METADATA_FIELD",
                error_details={"missing_field": field}
            )
    
    # Validate content_type
    valid_content_types = ['text', 'video', 'audio', 'image']
    if metadata['content_type'] not in valid_content_types:
        raise ValidationError(
            f"Invalid content_type '{metadata['content_type']}', "
            f"must be one of: {valid_content_types}",
            error_code="INVALID_CONTENT_TYPE",
            error_details={
                "provided_type": metadata['content_type'],
                "valid_types": valid_content_types
            }
        )


def format_s3_uri(bucket: str, key: str) -> str:
    """
    Format S3 URI from bucket and key.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Formatted S3 URI
    """
    return f"s3://{bucket}/{key}"


def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """
    Parse S3 URI into bucket and key components.
    
    Args:
        s3_uri: S3 URI to parse
        
    Returns:
        Tuple of (bucket, key)
        
    Raises:
        ValidationError: If URI format is invalid
    """
    from src.exceptions import ValidationError
    
    if not s3_uri.startswith('s3://'):
        raise ValidationError(
            f"Invalid S3 URI format: {s3_uri}",
            error_code="INVALID_S3_URI"
        )
    
    uri_parts = s3_uri[5:].split('/', 1)
    if len(uri_parts) != 2:
        raise ValidationError(
            f"Invalid S3 URI format: {s3_uri}",
            error_code="INVALID_S3_URI"
        )
    
    return uri_parts[0], uri_parts[1]


def calculate_cost_estimate(
    operation_type: str,
    volume: int,
    content_type: str = 'text'
) -> float:
    """
    Calculate estimated cost for operations.
    
    Args:
        operation_type: Type of operation (embedding, storage, query)
        volume: Volume of operations
        content_type: Type of content being processed
        
    Returns:
        Estimated cost in USD
    """
    # Cost estimates based on AWS pricing (approximate)
    cost_per_unit = {
        'text_embedding': 0.0001,      # per 1K tokens
        'video_embedding': 0.05,       # per minute
        'vector_storage': 0.023,       # per GB/month
        'vector_query': 0.00001,       # per query
    }
    
    operation_key = f"{content_type}_{operation_type}"
    if operation_key not in cost_per_unit:
        operation_key = operation_type
    
    unit_cost = cost_per_unit.get(operation_key, 0.0)
    return volume * unit_cost