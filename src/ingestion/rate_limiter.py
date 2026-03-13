"""
Rate Limiter for AWS Bedrock and SageMaker APIs.

Implements token bucket algorithm with per-model rate limits to prevent
throttling during large-scale ingestion operations.
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


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
