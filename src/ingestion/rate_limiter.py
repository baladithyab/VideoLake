"""
Rate Limiter and Retry Logic for AWS Services.

Provides configurable rate limiting and exponential backoff retry logic
for AWS Bedrock and SageMaker embedding generation to prevent throttling
and handle transient failures gracefully.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 10.0  # Max requests per second
    burst_size: int = 20  # Max burst size (token bucket capacity)
    max_retries: int = 5  # Max retry attempts
    initial_retry_delay: float = 1.0  # Initial retry delay in seconds
    max_retry_delay: float = 60.0  # Max retry delay in seconds
    exponential_base: float = 2.0  # Base for exponential backoff
    jitter: bool = True  # Add random jitter to retry delays


@dataclass
class RetryStatistics:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_retries: int = 0
    total_delay_seconds: float = 0.0
    last_error: str | None = None
    last_success: datetime | None = None
    last_failure: datetime | None = None


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter for controlling request rates.

    Implements the token bucket algorithm to enforce rate limits while
    allowing controlled bursts. Thread-safe for concurrent use.
    """

    def __init__(self, config: RateLimiterConfig):
        """
        Initialize the rate limiter.

        Args:
            config: Rate limiter configuration
        """
        self.config = config
        self.tokens = float(config.burst_size)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

        logger.info(
            f"Initialized rate limiter: {config.requests_per_second} req/s, "
            f"burst={config.burst_size}"
        )

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens from the bucket (blocks if insufficient tokens).

        Args:
            tokens: Number of tokens to acquire
        """
        async with self.lock:
            while True:
                # Refill tokens based on elapsed time
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.config.burst_size,
                    self.tokens + elapsed * self.config.requests_per_second
                )
                self.last_refill = now

                # Check if we have enough tokens
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate wait time for next refill
                needed_tokens = tokens - self.tokens
                wait_time = needed_tokens / self.config.requests_per_second

                # Release lock while waiting
                await asyncio.sleep(wait_time)

    async def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self.lock:
            # Refill tokens
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.config.burst_size,
                self.tokens + elapsed * self.config.requests_per_second
            )
            self.last_refill = now

            # Check availability
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RetryHandler:
    """
    Retry handler with exponential backoff and jitter.

    Provides configurable retry logic for handling transient failures
    with exponential backoff, jitter, and comprehensive statistics.
    """

    def __init__(self, config: RateLimiterConfig):
        """
        Initialize the retry handler.

        Args:
            config: Rate limiter configuration (includes retry settings)
        """
        self.config = config
        self.stats = RetryStatistics()

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff and optional jitter.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay = self.config.initial_retry_delay * (
            self.config.exponential_base ** attempt
        )

        # Cap at max delay
        delay = min(delay, self.config.max_retry_delay)

        # Add jitter if enabled
        if self.config.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    async def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute (can be async or sync)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            Last exception encountered if all retries exhausted
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            self.stats.total_attempts += 1

            try:
                # Execute function (handle both sync and async)
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success
                self.stats.successful_attempts += 1
                self.stats.last_success = datetime.utcnow()

                if attempt > 0:
                    logger.info(f"Succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_exception = e
                self.stats.last_error = str(e)
                self.stats.last_failure = datetime.utcnow()

                # Check if we should retry
                if attempt < self.config.max_retries:
                    self.stats.total_retries += 1

                    # Check if error is retryable
                    if not self._is_retryable_error(e):
                        logger.error(f"Non-retryable error: {e}")
                        self.stats.failed_attempts += 1
                        raise

                    # Calculate and wait
                    delay = self.calculate_delay(attempt)
                    self.stats.total_delay_seconds += delay

                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    self.stats.failed_attempts += 1
                    logger.error(
                        f"All {self.config.max_retries} retries exhausted. "
                        f"Last error: {e}"
                    )
                    raise

        # Should never reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry logic failed unexpectedly")

    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Determine if an error is retryable.

        Args:
            error: Exception to check

        Returns:
            True if error is retryable
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()

        # Retryable AWS errors
        retryable_patterns = [
            'throttling',
            'throttled',
            'rate exceeded',
            'too many requests',
            'service unavailable',
            'timeout',
            'connection',
            'temporary failure',
            'internal error',
            '500',
            '502',
            '503',
            '504',
        ]

        # Check error message and type
        for pattern in retryable_patterns:
            if pattern in error_str or pattern in error_type:
                return True

        # Non-retryable errors
        non_retryable_patterns = [
            'validation',
            'invalid',
            'not found',
            '400',
            '401',
            '403',
            '404',
        ]

        for pattern in non_retryable_patterns:
            if pattern in error_str or pattern in error_type:
                return False

        # Default to retryable for unknown errors
        return True

    def get_statistics(self) -> dict[str, Any]:
        """
        Get retry statistics.

        Returns:
            Dictionary with statistics
        """
        success_rate = 0.0
        if self.stats.total_attempts > 0:
            success_rate = (
                self.stats.successful_attempts / self.stats.total_attempts * 100
            )

        avg_delay = 0.0
        if self.stats.total_retries > 0:
            avg_delay = self.stats.total_delay_seconds / self.stats.total_retries

        return {
            "total_attempts": self.stats.total_attempts,
            "successful_attempts": self.stats.successful_attempts,
            "failed_attempts": self.stats.failed_attempts,
            "success_rate_pct": round(success_rate, 2),
            "total_retries": self.stats.total_retries,
            "total_delay_seconds": round(self.stats.total_delay_seconds, 2),
            "average_delay_seconds": round(avg_delay, 2),
            "last_error": self.stats.last_error,
            "last_success": self.stats.last_success.isoformat() if self.stats.last_success else None,
            "last_failure": self.stats.last_failure.isoformat() if self.stats.last_failure else None,
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.stats = RetryStatistics()


class RateLimitedExecutor:
    """
    Combined rate limiter and retry handler for executing functions.

    Provides a unified interface for rate-limited execution with automatic
    retry logic, suitable for AWS API calls and other rate-limited operations.
    """

    def __init__(
        self,
        config: RateLimiterConfig | None = None,
        rate_limiter: TokenBucketRateLimiter | None = None,
        retry_handler: RetryHandler | None = None
    ):
        """
        Initialize the rate-limited executor.

        Args:
            config: Configuration (creates rate_limiter and retry_handler if not provided)
            rate_limiter: Custom rate limiter instance
            retry_handler: Custom retry handler instance
        """
        if config is None:
            config = RateLimiterConfig()

        self.config = config
        self.rate_limiter = rate_limiter or TokenBucketRateLimiter(config)
        self.retry_handler = retry_handler or RetryHandler(config)

    async def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        tokens: int = 1,
        **kwargs: Any
    ) -> T:
        """
        Execute a function with rate limiting and retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            tokens: Number of rate limit tokens to acquire
            **kwargs: Keyword arguments for func

        Returns:
            Result from func
        """
        # Acquire rate limit tokens
        await self.rate_limiter.acquire(tokens)

        # Execute with retry
        return await self.retry_handler.execute_with_retry(func, *args, **kwargs)

    def get_statistics(self) -> dict[str, Any]:
        """
        Get execution statistics.

        Returns:
            Dictionary with rate limiter and retry statistics
        """
        return {
            "config": {
                "requests_per_second": self.config.requests_per_second,
                "burst_size": self.config.burst_size,
                "max_retries": self.config.max_retries,
            },
            "retry_stats": self.retry_handler.get_statistics(),
        }

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self.retry_handler.reset_statistics()
