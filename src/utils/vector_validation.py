"""
Vector Data Validation Utilities.

Centralized validation for vector data before storage operations.
Extracted from s3_vector_storage.py to promote reuse across backends.
"""

import numpy as np
from typing import List, Dict, Any, Optional

from src.exceptions import ValidationError


class VectorValidator:
    """Validator for vector data structures and values."""

    # Limits
    MAX_VECTORS_PER_REQUEST = 500
    MIN_VECTOR_DIMENSION = 1
    MAX_VECTOR_DIMENSION = 4096

    @classmethod
    def validate_dimensions(cls, dimensions: int) -> None:
        """
        Validate vector dimensions are within acceptable range.

        Args:
            dimensions: Vector dimensionality

        Raises:
            ValidationError: If dimensions are invalid
        """
        if not isinstance(dimensions, int):
            raise ValidationError(
                f"Dimensions must be an integer, got {type(dimensions).__name__}",
                error_code="INVALID_DIMENSION_TYPE"
            )

        if dimensions < cls.MIN_VECTOR_DIMENSION or dimensions > cls.MAX_VECTOR_DIMENSION:
            raise ValidationError(
                f"Vector dimensions must be between {cls.MIN_VECTOR_DIMENSION} and {cls.MAX_VECTOR_DIMENSION}, "
                f"got {dimensions}",
                error_code="INVALID_DIMENSIONS",
                error_details={"dimensions": dimensions}
            )

    @classmethod
    def validate_vector_array(
        cls,
        vector: List[float],
        expected_dim: Optional[int] = None,
        vector_index: Optional[int] = None
    ) -> np.ndarray:
        """
        Validate vector array and convert to numpy array.

        Args:
            vector: List of floats representing the vector
            expected_dim: Expected dimensionality (None to skip check)
            vector_index: Index of vector in batch (for error messages)

        Returns:
            Validated numpy array (float32)

        Raises:
            ValidationError: If vector is invalid
        """
        index_str = f" at index {vector_index}" if vector_index is not None else ""

        if not isinstance(vector, list):
            raise ValidationError(
                f"Vector{index_str} must be a list of floats, got {type(vector).__name__}",
                error_code="INVALID_VECTOR_TYPE",
                error_details={"vector_index": vector_index, "type": type(vector).__name__}
            )

        if not vector:
            raise ValidationError(
                f"Vector{index_str} cannot be empty",
                error_code="EMPTY_VECTOR",
                error_details={"vector_index": vector_index}
            )

        # Convert to numpy array
        try:
            np_vector = np.array(vector, dtype=np.float32)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Vector{index_str} could not be converted to numeric array: {e}",
                error_code="INVALID_VECTOR_CONVERSION",
                error_details={"vector_index": vector_index, "error": str(e)}
            )

        # Validate numeric types
        if not np.issubdtype(np_vector.dtype, np.number):
            raise ValidationError(
                f"Vector{index_str} must contain only numbers",
                error_code="INVALID_VECTOR_VALUE_TYPE",
                error_details={"vector_index": vector_index}
            )

        # Check for NaN or Infinity
        if not np.isfinite(np_vector).all():
            raise ValidationError(
                f"Vector{index_str} contains invalid values (NaN or Infinity)",
                error_code="INVALID_VECTOR_VALUE",
                error_details={"vector_index": vector_index}
            )

        # Check dimensions if specified
        if expected_dim is not None and len(np_vector) != expected_dim:
            raise ValidationError(
                f"Vector{index_str} has {len(np_vector)} dimensions, expected {expected_dim}",
                error_code="DIMENSION_MISMATCH",
                error_details={
                    "vector_index": vector_index,
                    "actual_dim": len(np_vector),
                    "expected_dim": expected_dim
                }
            )

        return np_vector

    @classmethod
    def normalize_vector(cls, vector: np.ndarray) -> np.ndarray:
        """
        Normalize vector to unit length (L2 normalization).

        Args:
            vector: Input vector as numpy array

        Returns:
            Normalized vector

        Raises:
            ValidationError: If vector norm is zero
        """
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValidationError(
                "Cannot normalize zero vector",
                error_code="ZERO_VECTOR_NORM"
            )
        return vector / norm

    @classmethod
    def validate_vector_data(cls, vectors_data: List[Dict[str, Any]]) -> None:
        """
        Validate vector data structure before storage (AWS S3 Vectors format).

        Expected format:
        [
            {
                "key": "unique-vector-id",
                "data": {
                    "float32": [0.1, 0.2, ...]
                },
                "metadata": {...}  # optional
            },
            ...
        ]

        Args:
            vectors_data: List of vector dictionaries

        Raises:
            ValidationError: If validation fails
        """
        if not vectors_data:
            raise ValidationError(
                "Vector data cannot be empty",
                error_code="EMPTY_VECTOR_DATA"
            )

        if len(vectors_data) > cls.MAX_VECTORS_PER_REQUEST:
            raise ValidationError(
                f"Cannot store more than {cls.MAX_VECTORS_PER_REQUEST} vectors in a single request, "
                f"got {len(vectors_data)}",
                error_code="TOO_MANY_VECTORS",
                error_details={"vector_count": len(vectors_data)}
            )

        for i, vector in enumerate(vectors_data):
            # Validate dict type
            if not isinstance(vector, dict):
                raise ValidationError(
                    f"Vector at index {i} must be a dictionary",
                    error_code="INVALID_VECTOR_TYPE",
                    error_details={"index": i, "type": type(vector).__name__}
                )

            # Validate required 'key' field
            if 'key' not in vector:
                raise ValidationError(
                    f"Vector at index {i} missing required 'key' field",
                    error_code="MISSING_VECTOR_KEY",
                    error_details={"index": i}
                )

            key = vector['key']
            if not isinstance(key, str) or not key.strip():
                raise ValidationError(
                    f"Vector key at index {i} must be a non-empty string",
                    error_code="INVALID_VECTOR_KEY",
                    error_details={"index": i, "key": key}
                )

            # Validate required 'data' field
            if 'data' not in vector:
                raise ValidationError(
                    f"Vector at index {i} missing required 'data' field",
                    error_code="MISSING_VECTOR_DATA",
                    error_details={"index": i}
                )

            vector_data = vector['data']
            if not isinstance(vector_data, dict):
                raise ValidationError(
                    f"Vector data at index {i} must be a dictionary with VectorData format",
                    error_code="INVALID_VECTOR_DATA_TYPE",
                    error_details={"index": i, "type": type(vector_data).__name__}
                )

            # Validate 'float32' field (AWS S3 Vectors union type)
            if 'float32' not in vector_data:
                raise ValidationError(
                    f"Vector data at index {i} must contain 'float32' field",
                    error_code="MISSING_FLOAT32_DATA",
                    error_details={"index": i, "available_fields": list(vector_data.keys())}
                )

            float32_data = vector_data['float32']
            if not isinstance(float32_data, list):
                raise ValidationError(
                    f"Vector float32 data at index {i} must be a list of floats",
                    error_code="INVALID_FLOAT32_DATA_TYPE",
                    error_details={"index": i, "type": type(float32_data).__name__}
                )

            # Validate the actual vector array
            cls.validate_vector_array(float32_data, vector_index=i)

            # Validate metadata if present
            if 'metadata' in vector:
                metadata = vector['metadata']
                if metadata is not None and not isinstance(metadata, dict):
                    raise ValidationError(
                        f"Vector metadata at index {i} must be a dictionary or None",
                        error_code="INVALID_METADATA_TYPE",
                        error_details={"index": i, "type": type(metadata).__name__}
                    )

    @classmethod
    def validate_query_vector(
        cls,
        query_vector: List[float],
        expected_dim: Optional[int] = None
    ) -> np.ndarray:
        """
        Validate query vector for similarity search.

        Args:
            query_vector: Query vector as list of floats
            expected_dim: Expected dimensionality

        Returns:
            Validated numpy array (float32)

        Raises:
            ValidationError: If validation fails
        """
        return cls.validate_vector_array(query_vector, expected_dim=expected_dim)

    @classmethod
    def validate_batch_size(cls, batch_size: int, max_size: int = MAX_VECTORS_PER_REQUEST) -> None:
        """
        Validate batch size for batch operations.

        Args:
            batch_size: Number of vectors in batch
            max_size: Maximum allowed batch size

        Raises:
            ValidationError: If batch size is invalid
        """
        if batch_size <= 0:
            raise ValidationError(
                f"Batch size must be positive, got {batch_size}",
                error_code="INVALID_BATCH_SIZE",
                error_details={"batch_size": batch_size}
            )

        if batch_size > max_size:
            raise ValidationError(
                f"Batch size {batch_size} exceeds maximum {max_size}",
                error_code="BATCH_SIZE_EXCEEDED",
                error_details={"batch_size": batch_size, "max_size": max_size}
            )
