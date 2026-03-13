

"""
Rate Limiter and Retry Logic for AWS Services.

Implements token bucket algorithm with per-model rate limits and exponential
backoff retry logic for AWS Bedrock and SageMaker embedding generation to
prevent throttling and handle transient failures gracefully.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, TypeVar

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ServiceType(Enum):
    """AWS service types with rate limits."""
    BEDROCK = "bedrock"
    SAGEMAKER = "sagemaker"
    S3 = "s3"


@dataclass
class RateLimit:
    """Rate limit configuration for a service."""
    requests_per_second: float
    burst_capacity: int
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        """Initialize token bucket."""
        self.tokens = self.burst_capacity
        self.last_refill = time.time()


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


class RateLimiter:
    """
    Token bucket rate limiter for AWS service calls.

    Prevents throttling by limiting request rate per service and model.
    Supports burst capacity for short spikes in traffic.

    Example:
        limiter = RateLimiter()

        async def process_batch():
            await limiter.acquire(ServiceType.BEDROCK, "amazon.titan-embed-text-v2:0")
            # Make API call
            result = await generate_embedding(...)
            limiter.report_success(ServiceType.BEDROCK)
    """

    # Default rate limits (requests per second)
    DEFAULT_LIMITS = {
        ServiceType.BEDROCK: {
            # Titan models: 2000 RPM = ~33 RPS
            "amazon.titan-embed-text-v2:0": RateLimit(requests_per_second=30.0, burst_capacity=50),
            "amazon.titan-embed-text-v1": RateLimit(requests_per_second=30.0, burst_capacity=50),
            "amazon.titan-embed-image-v1": RateLimit(requests_per_second=20.0, burst_capacity=40),

            # Cohere models: 1000 RPM = ~16 RPS
            "cohere.embed-english-v3": RateLimit(requests_per_second=15.0, burst_capacity=30),
            "cohere.embed-multilingual-v3": RateLimit(requests_per_second=15.0, burst_capacity=30),

            # Nova models: conservative estimate
            "amazon.nova-lite-v1:0": RateLimit(requests_per_second=10.0, burst_capacity=20),
            "amazon.nova-pro-v1:0": RateLimit(requests_per_second=5.0, burst_capacity=10),
        },
        ServiceType.SAGEMAKER: {
            # SageMaker endpoints: depends on instance, use conservative defaults
            "default": RateLimit(requests_per_second=10.0, burst_capacity=20),
        },
        ServiceType.S3: {
            # S3: 5500 PUT/POST/DELETE per second per prefix
            "default": RateLimit(requests_per_second=1000.0, burst_capacity=2000),
        }
    }

    def __init__(self, custom_limits: Optional[Dict] = None):
        """
        Initialize rate limiter.

        Args:
            custom_limits: Optional custom rate limits to override defaults
        """
        self.limits: Dict[ServiceType, Dict[str, RateLimit]] = {}

        # Initialize with default limits
        for service_type, model_limits in self.DEFAULT_LIMITS.items():
            self.limits[service_type] = {}
            for model_id, limit_config in model_limits.items():
                self.limits[service_type][model_id] = RateLimit(
                    requests_per_second=limit_config.requests_per_second,
                    burst_capacity=limit_config.burst_capacity
                )

        # Apply custom limits
        if custom_limits:
            for service_type, model_limits in custom_limits.items():
                if service_type not in self.limits:
                    self.limits[service_type] = {}
                for model_id, limit_config in model_limits.items():
                    self.limits[service_type][model_id] = limit_config

        # Metrics
        self.requests_made: Dict[ServiceType, int] = {st: 0 for st in ServiceType}
        self.requests_delayed: Dict[ServiceType, int] = {st: 0 for st in ServiceType}
        self.total_delay_seconds: Dict[ServiceType, float] = {st: 0.0 for st in ServiceType}

        logger.info("RateLimiter initialized with token bucket algorithm")

    async def acquire(
        self,
        service_type: ServiceType,
        model_id: Optional[str] = None,
        tokens_needed: int = 1
    ) -> float:
        """
        Acquire tokens from the rate limiter.

        Blocks if insufficient tokens available, implementing exponential backoff.

        Args:
            service_type: Type of AWS service
            model_id: Specific model or endpoint ID (None for default)
            tokens_needed: Number of tokens to acquire (default: 1)

        Returns:
            Delay in seconds (0 if no delay)
        """
        # Get rate limit for this service/model
        model_limits = self.limits.get(service_type, {})

        if not model_id or model_id not in model_limits:
            # Use default limit if model not configured
            model_id = "default"
            if model_id not in model_limits:
                # No rate limiting configured for this service
                return 0.0

        limit = model_limits[model_id]

        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - limit.last_refill
        refill_amount = elapsed * limit.requests_per_second
        limit.tokens = min(limit.burst_capacity, limit.tokens + refill_amount)
        limit.last_refill = now

        # Check if enough tokens available
        if limit.tokens >= tokens_needed:
            limit.tokens -= tokens_needed
            self.requests_made[service_type] += 1
            return 0.0

        # Calculate delay needed
        tokens_deficit = tokens_needed - limit.tokens
        delay_seconds = tokens_deficit / limit.requests_per_second

        # Log throttling
        logger.debug(
            f"Rate limit reached for {service_type.value}/{model_id}: "
            f"waiting {delay_seconds:.2f}s"
        )

        # Update metrics
        self.requests_delayed[service_type] += 1
        self.total_delay_seconds[service_type] += delay_seconds

        # Wait for tokens to refill
        await asyncio.sleep(delay_seconds)

        # Acquire tokens after waiting
        limit.tokens = 0  # Used up all accumulated tokens
        self.requests_made[service_type] += 1

        return delay_seconds

    def report_throttle(self, service_type: ServiceType, model_id: Optional[str] = None):
        """
        Report that a throttling error occurred.

        Reduces rate limit to prevent future throttling.

        Args:
            service_type: Type of AWS service
            model_id: Specific model or endpoint ID
        """
        model_limits = self.limits.get(service_type, {})

        if not model_id or model_id not in model_limits:
            model_id = "default"

        if model_id in model_limits:
            limit = model_limits[model_id]

            # Reduce rate by 50% (multiplicative decrease)
            old_rate = limit.requests_per_second
            limit.requests_per_second *= 0.5
            limit.burst_capacity = int(limit.burst_capacity * 0.5)

            logger.warning(
                f"Throttle detected for {service_type.value}/{model_id}: "
                f"reducing rate from {old_rate:.2f} to {limit.requests_per_second:.2f} RPS"
            )

    def report_success(self, service_type: ServiceType, model_id: Optional[str] = None):
        """
        Report successful request.

        Gradually increases rate limit (AIMD algorithm).

        Args:
            service_type: Type of AWS service
            model_id: Specific model or endpoint ID
        """
        model_limits = self.limits.get(service_type, {})

        if not model_id or model_id not in model_limits:
            model_id = "default"

        if model_id in model_limits:
            limit = model_limits[model_id]

            # Get original rate
            original_limit = self.DEFAULT_LIMITS.get(service_type, {}).get(model_id)
            if not original_limit:
                return

            # Gradually increase rate (additive increase)
            # Only if below original rate
            if limit.requests_per_second < original_limit.requests_per_second:
                limit.requests_per_second = min(
                    original_limit.requests_per_second,
                    limit.requests_per_second + 0.1  # +0.1 RPS per successful request
                )

    def get_metrics(self) -> Dict[str, any]:
        """Get rate limiter metrics."""
        return {
            "requests_made": {st.value: count for st, count in self.requests_made.items()},
            "requests_delayed": {st.value: count for st, count in self.requests_delayed.items()},
            "total_delay_seconds": {st.value: delay for st, delay in self.total_delay_seconds.items()},
            "delay_rate": {
                st.value: (
                    self.requests_delayed[st] / self.requests_made[st] * 100
                    if self.requests_made[st] > 0 else 0.0
                )
                for st in ServiceType
            }
        }

    def reset_metrics(self):
        """Reset metrics counters."""
        self.requests_made = {st: 0 for st in ServiceType}
        self.requests_delayed = {st: 0 for st in ServiceType}
        self.total_delay_seconds = {st: 0.0 for st in ServiceType}
        logger.info("Rate limiter metrics reset")


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
