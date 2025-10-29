"""
Enhanced Pydantic validators for API request validation.

Provides custom validators for:
- S3 URIs
- Index ARNs
- Video processing parameters
- Search parameters
"""

import re
from typing import Optional, List, Any
from pydantic import validator, Field
import logging

logger = logging.getLogger(__name__)


class S3URIValidator:
    """Validator for S3 URI formats."""

    S3_URI_PATTERN = re.compile(r'^s3://[a-z0-9.-]{3,63}/.*$')
    BUCKET_NAME_PATTERN = re.compile(r'^[a-z0-9.-]{3,63}$')

    @classmethod
    def validate_s3_uri(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate S3 URI format.

        Args:
            v: S3 URI string

        Returns:
            Validated S3 URI

        Raises:
            ValueError: If URI format is invalid
        """
        if v is None:
            return v

        if not cls.S3_URI_PATTERN.match(v):
            raise ValueError(
                f'Invalid S3 URI format: {v}. '
                f'Expected format: s3://bucket-name/key'
            )

        # Extract bucket name and validate
        bucket_name = v.split('/')[2]
        if not cls.BUCKET_NAME_PATTERN.match(bucket_name):
            raise ValueError(
                f'Invalid S3 bucket name: {bucket_name}. '
                f'Must be 3-63 characters, lowercase alphanumeric with dots and hyphens.'
            )

        return v


class IndexARNValidator:
    """Validator for S3 Vector Index ARNs."""

    INDEX_ARN_PATTERN = re.compile(
        r'^arn:aws:s3vector:[a-z0-9-]+:\d{12}:index/[a-zA-Z0-9._-]+$'
    )

    @classmethod
    def validate_index_arn(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate Index ARN format.

        Args:
            v: Index ARN string

        Returns:
            Validated Index ARN

        Raises:
            ValueError: If ARN format is invalid
        """
        if v is None:
            return v

        if not cls.INDEX_ARN_PATTERN.match(v):
            raise ValueError(
                f'Invalid Index ARN format: {v}. '
                f'Expected format: arn:aws:s3vector:region:account:index/index-name'
            )

        return v


class VideoParametersValidator:
    """Validator for video processing parameters."""

    MAX_VIDEO_DURATION_SECONDS = 7200  # 2 hours
    MAX_CLIP_LENGTH_SECONDS = 3600  # 1 hour
    SUPPORTED_EMBEDDING_OPTIONS = {
        "visual-text",
        "visual-image",
        "audio",
        "text-titan"
    }

    @classmethod
    def validate_embedding_options(cls, v: List[str]) -> List[str]:
        """
        Validate embedding options.

        Args:
            v: List of embedding options

        Returns:
            Validated list

        Raises:
            ValueError: If options are invalid
        """
        if not v:
            raise ValueError('At least one embedding option must be specified')

        invalid_options = set(v) - cls.SUPPORTED_EMBEDDING_OPTIONS
        if invalid_options:
            raise ValueError(
                f'Invalid embedding options: {invalid_options}. '
                f'Supported options: {cls.SUPPORTED_EMBEDDING_OPTIONS}'
            )

        return v

    @classmethod
    def validate_time_range(
        cls,
        start_sec: float,
        length_sec: Optional[float] = None,
        use_fixed_length_sec: Optional[float] = None
    ) -> tuple[float, Optional[float], Optional[float]]:
        """
        Validate video time range parameters.

        Args:
            start_sec: Start time in seconds
            length_sec: Optional length in seconds
            use_fixed_length_sec: Optional fixed clip length

        Returns:
            Validated parameters

        Raises:
            ValueError: If parameters are invalid
        """
        if start_sec < 0:
            raise ValueError('start_sec must be non-negative')

        if length_sec is not None:
            if length_sec <= 0:
                raise ValueError('length_sec must be positive')

            if length_sec > cls.MAX_CLIP_LENGTH_SECONDS:
                raise ValueError(
                    f'length_sec exceeds maximum of {cls.MAX_CLIP_LENGTH_SECONDS} seconds'
                )

            total_duration = start_sec + length_sec
            if total_duration > cls.MAX_VIDEO_DURATION_SECONDS:
                raise ValueError(
                    f'Total video duration ({total_duration}s) exceeds maximum of '
                    f'{cls.MAX_VIDEO_DURATION_SECONDS} seconds (2 hours)'
                )

        if use_fixed_length_sec is not None:
            if use_fixed_length_sec <= 0:
                raise ValueError('use_fixed_length_sec must be positive')

            if use_fixed_length_sec > cls.MAX_CLIP_LENGTH_SECONDS:
                raise ValueError(
                    f'use_fixed_length_sec exceeds maximum of {cls.MAX_CLIP_LENGTH_SECONDS} seconds'
                )

        return start_sec, length_sec, use_fixed_length_sec


class SearchParametersValidator:
    """Validator for search parameters."""

    MIN_TOP_K = 1
    MAX_TOP_K = 1000
    DEFAULT_TOP_K = 10

    SUPPORTED_BACKENDS = {
        "s3_vector",
        "opensearch",
        "lancedb",
        "qdrant"
    }

    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """
        Validate top_k parameter.

        Args:
            v: Number of results to return

        Returns:
            Validated top_k

        Raises:
            ValueError: If top_k is out of range
        """
        if v < cls.MIN_TOP_K or v > cls.MAX_TOP_K:
            raise ValueError(
                f'top_k must be between {cls.MIN_TOP_K} and {cls.MAX_TOP_K}, got {v}'
            )

        return v

    @classmethod
    def validate_backend(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate backend parameter.

        Args:
            v: Backend name

        Returns:
            Validated backend

        Raises:
            ValueError: If backend is unsupported
        """
        if v is not None and v not in cls.SUPPORTED_BACKENDS:
            raise ValueError(
                f'Unsupported backend: {v}. '
                f'Supported backends: {cls.SUPPORTED_BACKENDS}'
            )

        return v

    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """
        Validate query text.

        Args:
            v: Query text

        Returns:
            Validated query text

        Raises:
            ValueError: If query is invalid
        """
        if not v or not v.strip():
            raise ValueError('query_text cannot be empty')

        if len(v) > 10000:
            raise ValueError('query_text exceeds maximum length of 10000 characters')

        return v.strip()


class ResourceNameValidator:
    """Validator for AWS resource names."""

    BUCKET_NAME_PATTERN = re.compile(r'^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$')
    INDEX_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{1,255}$')
    DOMAIN_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]{2,27}$')

    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """
        Validate S3 bucket name.

        Args:
            v: Bucket name

        Returns:
            Validated bucket name

        Raises:
            ValueError: If name is invalid
        """
        if not cls.BUCKET_NAME_PATTERN.match(v):
            raise ValueError(
                f'Invalid bucket name: {v}. '
                f'Must be 3-63 characters, lowercase alphanumeric with dots and hyphens, '
                f'cannot start/end with dot or hyphen'
            )

        # Additional checks
        if '..' in v:
            raise ValueError('Bucket name cannot contain consecutive dots')

        if '.-' in v or '-.' in v:
            raise ValueError('Bucket name cannot have dots adjacent to hyphens')

        # Check for IP address format
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', v):
            raise ValueError('Bucket name cannot be formatted as IP address')

        return v

    @classmethod
    def validate_index_name(cls, v: str) -> str:
        """
        Validate index name.

        Args:
            v: Index name

        Returns:
            Validated index name

        Raises:
            ValueError: If name is invalid
        """
        if not cls.INDEX_NAME_PATTERN.match(v):
            raise ValueError(
                f'Invalid index name: {v}. '
                f'Must be 1-255 characters, alphanumeric with dots, underscores, and hyphens'
            )

        return v

    @classmethod
    def validate_domain_name(cls, v: str) -> str:
        """
        Validate OpenSearch domain name.

        Args:
            v: Domain name

        Returns:
            Validated domain name

        Raises:
            ValueError: If name is invalid
        """
        if not cls.DOMAIN_NAME_PATTERN.match(v):
            raise ValueError(
                f'Invalid domain name: {v}. '
                f'Must be 3-28 characters, lowercase, start with letter, '
                f'alphanumeric with hyphens only'
            )

        return v


# Convenience functions for use in Pydantic models
def validate_s3_uri(v: Optional[str]) -> Optional[str]:
    """Convenience wrapper for S3 URI validation."""
    return S3URIValidator.validate_s3_uri(v)


def validate_index_arn(v: Optional[str]) -> Optional[str]:
    """Convenience wrapper for Index ARN validation."""
    return IndexARNValidator.validate_index_arn(v)


def validate_embedding_options(v: List[str]) -> List[str]:
    """Convenience wrapper for embedding options validation."""
    return VideoParametersValidator.validate_embedding_options(v)


def validate_top_k(v: int) -> int:
    """Convenience wrapper for top_k validation."""
    return SearchParametersValidator.validate_top_k(v)


def validate_backend(v: Optional[str]) -> Optional[str]:
    """Convenience wrapper for backend validation."""
    return SearchParametersValidator.validate_backend(v)


def validate_query_text(v: str) -> str:
    """Convenience wrapper for query text validation."""
    return SearchParametersValidator.validate_query_text(v)


def validate_bucket_name(v: str) -> str:
    """Convenience wrapper for bucket name validation."""
    return ResourceNameValidator.validate_bucket_name(v)


def validate_index_name(v: str) -> str:
    """Convenience wrapper for index name validation."""
    return ResourceNameValidator.validate_index_name(v)


def validate_domain_name(v: str) -> str:
    """Convenience wrapper for domain name validation."""
    return ResourceNameValidator.validate_domain_name(v)
