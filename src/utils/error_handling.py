"""
Enhanced Error Handling and Recovery System for S3Vector

This module provides production-ready error handling, retry logic, and monitoring
capabilities for the S3Vector embedding pipeline.
"""

import time
import random
import logging
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from contextlib import contextmanager

from botocore.exceptions import ClientError, BotoCoreError
from src.exceptions import VectorEmbeddingError, ValidationError
from src.utils.logging_config import get_structured_logger

logger = get_structured_logger("error_handling")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: List[Type[Exception]] = field(default_factory=lambda: [
        ClientError, BotoCoreError, ConnectionError, TimeoutError
    ])
    retryable_error_codes: List[str] = field(default_factory=lambda: [
        'Throttling', 'ServiceUnavailable', 'InternalError', 'RequestTimeout',
        'TooManyRequestsException', 'ProvisionedThroughputExceededException'
    ])


@dataclass
class ErrorMetrics:
    """Metrics for error tracking and analysis."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_service: Dict[str, int] = field(default_factory=dict)
    retry_attempts: int = 0
    successful_retries: int = 0
    failed_retries: int = 0
    last_error_time: Optional[datetime] = None
    error_rate_per_minute: float = 0.0


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascade failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise VectorEmbeddingError(
                    "Circuit breaker is OPEN - service temporarily unavailable",
                    error_code="CIRCUIT_BREAKER_OPEN"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).seconds >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class EnhancedErrorHandler:
    """Enhanced error handling with retry logic, circuit breaker, and monitoring."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.metrics = ErrorMetrics()
        self.circuit_breaker = CircuitBreaker()
        self.logger = get_structured_logger(f"error_handler.{service_name}")
    
    def with_retry(self, config: Optional[RetryConfig] = None):
        """Decorator for adding retry logic to functions."""
        if config is None:
            config = RetryConfig()
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self._execute_with_retry(func, config, *args, **kwargs)
            return wrapper
        return decorator
    
    def _execute_with_retry(self, func: Callable, config: RetryConfig, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None
        
        for attempt in range(config.max_attempts):
            try:
                # Use circuit breaker for protection
                result = self.circuit_breaker.call(func, *args, **kwargs)
                
                if attempt > 0:
                    self.metrics.successful_retries += 1
                    self.logger.info(
                        f"Function succeeded after {attempt + 1} attempts",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "service": self.service_name
                        }
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                self._record_error(e, func.__name__)
                
                if not self._is_retryable(e, config):
                    self.logger.error(
                        f"Non-retryable error in {func.__name__}",
                        extra={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "service": self.service_name
                        }
                    )
                    raise
                
                if attempt < config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, config)
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(e),
                            "service": self.service_name
                        }
                    )
                    time.sleep(delay)
                    self.metrics.retry_attempts += 1
        
        # All attempts failed
        self.metrics.failed_retries += 1
        self.logger.error(
            f"All {config.max_attempts} attempts failed for {func.__name__}",
            extra={
                "function": func.__name__,
                "final_error": str(last_exception),
                "service": self.service_name
            }
        )
        raise last_exception
    
    def _is_retryable(self, exception: Exception, config: RetryConfig) -> bool:
        """Determine if an exception is retryable."""
        # Check exception type
        if any(isinstance(exception, exc_type) for exc_type in config.retryable_exceptions):
            # For ClientError, check the specific error code
            if isinstance(exception, ClientError):
                error_code = exception.response.get('Error', {}).get('Code', '')
                return error_code in config.retryable_error_codes
            return True
        
        return False
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for exponential backoff with jitter."""
        delay = min(
            config.base_delay * (config.exponential_base ** attempt),
            config.max_delay
        )
        
        if config.jitter:
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay
    
    def _record_error(self, exception: Exception, function_name: str):
        """Record error metrics."""
        self.metrics.total_errors += 1
        self.metrics.last_error_time = datetime.now(timezone.utc)
        
        error_type = type(exception).__name__
        self.metrics.errors_by_type[error_type] = self.metrics.errors_by_type.get(error_type, 0) + 1
        self.metrics.errors_by_service[self.service_name] = self.metrics.errors_by_service.get(self.service_name, 0) + 1
    
    @contextmanager
    def error_context(self, operation: str, **context_data):
        """Context manager for enhanced error reporting."""
        start_time = time.time()
        
        try:
            self.logger.info(
                f"Starting operation: {operation}",
                extra={
                    "operation": operation,
                    "service": self.service_name,
                    **context_data
                }
            )
            yield
            
            duration = time.time() - start_time
            self.logger.info(
                f"Operation completed: {operation}",
                extra={
                    "operation": operation,
                    "duration_ms": int(duration * 1000),
                    "service": self.service_name,
                    **context_data
                }
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_error(e, operation)
            
            self.logger.error(
                f"Operation failed: {operation}",
                extra={
                    "operation": operation,
                    "duration_ms": int(duration * 1000),
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "service": self.service_name,
                    **context_data
                }
            )
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status and metrics."""
        return {
            "service": self.service_name,
            "circuit_breaker_state": self.circuit_breaker.state,
            "total_errors": self.metrics.total_errors,
            "retry_success_rate": (
                self.metrics.successful_retries / max(1, self.metrics.retry_attempts) * 100
                if self.metrics.retry_attempts > 0 else 100
            ),
            "errors_by_type": dict(self.metrics.errors_by_type),
            "last_error_time": self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None,
            "status": "healthy" if self.circuit_breaker.state == "CLOSED" else "degraded"
        }


# Global error handlers for each service
_error_handlers: Dict[str, EnhancedErrorHandler] = {}


def get_error_handler(service_name: str) -> EnhancedErrorHandler:
    """Get or create error handler for a service."""
    if service_name not in _error_handlers:
        _error_handlers[service_name] = EnhancedErrorHandler(service_name)
    return _error_handlers[service_name]


def with_error_handling(service_name: str, retry_config: Optional[RetryConfig] = None):
    """Decorator for adding comprehensive error handling to service methods."""
    def decorator(func: Callable):
        handler = get_error_handler(service_name)
        return handler.with_retry(retry_config)(func)
    return decorator


def get_system_health() -> Dict[str, Any]:
    """Get overall system health status."""
    service_statuses = {}
    overall_status = "healthy"
    
    for service_name, handler in _error_handlers.items():
        status = handler.get_health_status()
        service_statuses[service_name] = status
        
        if status["status"] != "healthy":
            overall_status = "degraded"
    
    return {
        "overall_status": overall_status,
        "services": service_statuses,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }