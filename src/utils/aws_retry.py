"""
AWS Retry Utilities.

Centralized retry logic with exponential backoff for AWS operations.
Eliminates duplicate retry implementations across service files.
"""

import time
import random
from typing import Callable, TypeVar, Optional, Set
from functools import wraps
from botocore.exceptions import ClientError, BotoCoreError

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

# Default set of retryable AWS error codes
DEFAULT_RETRYABLE_ERROR_CODES: Set[str] = {
    'Throttling',
    'ThrottlingException',
    'TooManyRequestsException',
    'ServiceUnavailable',
    'InternalError',
    'InternalFailure',
    'RequestTimeout',
    'RequestTimeoutException',
    'PriorRequestNotComplete',
    'ProvisionedThroughputExceededException',
    'RequestLimitExceeded',
    'BandwidthLimitExceeded',
    'SlowDown',  # S3 specific
}


class AWSRetryHandler:
    """Handler for AWS API retry logic with exponential backoff."""

    @staticmethod
    def is_retryable_error(error: ClientError, retryable_codes: Optional[Set[str]] = None) -> bool:
        """
        Check if AWS ClientError should be retried.

        Args:
            error: The ClientError to check
            retryable_codes: Optional custom set of retryable error codes.
                           If None, uses DEFAULT_RETRYABLE_ERROR_CODES.

        Returns:
            True if error should be retried, False otherwise
        """
        if retryable_codes is None:
            retryable_codes = DEFAULT_RETRYABLE_ERROR_CODES

        error_code = error.response.get('Error', {}).get('Code', '')
        return error_code in retryable_codes

    @staticmethod
    def calculate_backoff_delay(
        attempt: int,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        jitter: bool = True
    ) -> float:
        """
        Calculate exponential backoff delay with optional jitter.

        Args:
            attempt: Current attempt number (0-indexed)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter (0-1 second)

        Returns:
            Delay in seconds
        """
        delay = min(base_delay * (2 ** attempt), max_delay)
        if jitter:
            delay += random.uniform(0, 1)
        return delay

    @classmethod
    def retry_with_backoff(
        cls,
        func: Callable[[], T],
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_codes: Optional[Set[str]] = None,
        operation_name: Optional[str] = None
    ) -> T:
        """
        Execute function with exponential backoff retry on AWS errors.

        Args:
            func: Function to retry (should be a lambda or callable with no args)
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay in seconds
            retryable_codes: Custom set of retryable error codes (None = use defaults)
            operation_name: Optional operation name for logging

        Returns:
            Result from successful function call

        Raises:
            ClientError: If error is not retryable or max retries exceeded
            BotoCoreError: If max retries exceeded for BotoCore errors

        Example:
            result = AWSRetryHandler.retry_with_backoff(
                lambda: s3_client.list_buckets(),
                operation_name="list_buckets"
            )
        """
        op_name = operation_name or "AWS operation"

        for attempt in range(max_retries):
            try:
                return func()

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')

                # Check if error is retryable
                if not cls.is_retryable_error(e, retryable_codes):
                    logger.error(
                        f"{op_name} failed with non-retryable error: {error_code}",
                        extra={'error_code': error_code}
                    )
                    raise

                # Check if we should retry
                if attempt < max_retries - 1:
                    delay = cls.calculate_backoff_delay(attempt, base_delay, max_delay)
                    logger.warning(
                        f"{op_name} retrying after {delay:.2f}s due to {error_code} "
                        f"(attempt {attempt + 1}/{max_retries})",
                        extra={
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'delay_seconds': delay,
                            'error_code': error_code
                        }
                    )
                    time.sleep(delay)
                    continue

                # Max retries exceeded
                logger.error(
                    f"{op_name} failed after {max_retries} attempts with error: {error_code}",
                    extra={'error_code': error_code, 'max_retries': max_retries}
                )
                raise

            except BotoCoreError as e:
                # BotoCoreError indicates lower-level issues (network, etc.)
                if attempt < max_retries - 1:
                    delay = cls.calculate_backoff_delay(attempt, base_delay, max_delay, jitter=False)
                    logger.warning(
                        f"{op_name} retrying after {delay:.2f}s due to BotoCoreError: {str(e)} "
                        f"(attempt {attempt + 1}/{max_retries})",
                        extra={
                            'attempt': attempt + 1,
                            'max_retries': max_retries,
                            'delay_seconds': delay
                        }
                    )
                    time.sleep(delay)
                    continue

                # Max retries exceeded
                logger.error(
                    f"{op_name} failed after {max_retries} attempts with BotoCoreError: {str(e)}",
                    extra={'max_retries': max_retries}
                )
                raise


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_codes: Optional[Set[str]] = None
):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        retryable_codes: Custom set of retryable error codes

    Example:
        @with_retry(max_retries=5, base_delay=2.0)
        def list_buckets(self):
            return self.s3_client.list_buckets()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return AWSRetryHandler.retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                retryable_codes=retryable_codes,
                operation_name=func.__name__
            )
        return wrapper
    return decorator
