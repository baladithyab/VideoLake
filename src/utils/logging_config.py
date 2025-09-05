"""
Enhanced structured logging configuration for S3 Vector Embedding POC.

This module provides comprehensive logging capabilities with structured output,
debugging features, performance tracking, and complete visibility into
application behavior for better monitoring and debugging.
"""

import logging
import json
import sys
import time
import functools
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Enhanced custom formatter for structured JSON logging with debugging context."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON with enhanced context."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': threading.get_ident(),
            'thread_name': threading.current_thread().name
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        extra_fields = [
            'operation', 'cost_estimate', 'performance_metrics', 'request_id',
            'user_action', 'component', 'duration_ms', 'status', 'error_code',
            'service_call', 'aws_api_call', 'resource_id', 'processing_step',
            'query_params', 'response_size', 'execution_context', 'debug_info',
            'frontend_component', 'button_click', 'search_query', 'video_operation',
            'visualization_state', 'resource_operation', 'service_method'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        return json.dumps(log_entry, default=str)


class StructuredLogger:
    """Enhanced wrapper for structured logging operations with debugging capabilities."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.component_name = name.split('.')[-1] if '.' in name else name
    
    def log_operation(
        self,
        operation: str,
        level: str = 'INFO',
        **kwargs
    ) -> None:
        """
        Log an operation with structured data.
        
        Args:
            operation: Name of the operation being performed
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            **kwargs: Additional structured data to include
        """
        extra = {'operation': operation, 'component': self.component_name, **kwargs}
        
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, f"Operation: {operation}", extra=extra)
    
    def log_function_entry(self, function_name: str, **kwargs) -> None:
        """Log function entry for debugging flow visibility."""
        extra = {
            'operation': f"{function_name}_entry",
            'component': self.component_name,
            'processing_step': 'function_entry',
            **kwargs
        }
        self.logger.debug(f"→ Entering {function_name}", extra=extra)
    
    def log_function_exit(self, function_name: str, result: Any = None, **kwargs) -> None:
        """Log function exit for debugging flow visibility."""
        extra = {
            'operation': f"{function_name}_exit",
            'component': self.component_name,
            'processing_step': 'function_exit',
            **kwargs
        }
        if result is not None:
            extra['result_type'] = type(result).__name__
            extra['result_summary'] = str(result)[:200] if result else None
        
        self.logger.debug(f"← Exiting {function_name}", extra=extra)
    
    def log_user_action(self, action: str, component: str, **kwargs) -> None:
        """Log user actions like button clicks, form submissions, etc."""
        extra = {
            'user_action': action,
            'frontend_component': component,
            'operation': f"user_{action}",
            'processing_step': 'user_interaction',
            **kwargs
        }
        self.logger.info(f"User action: {action} on {component}", extra=extra)
    
    def log_service_call(self, service: str, method: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log service method calls with parameters."""
        extra = {
            'service_call': f"{service}.{method}",
            'service_method': method,
            'operation': f"service_call_{method}",
            'processing_step': 'service_invocation',
            **kwargs
        }
        if params:
            extra['query_params'] = params
        
        self.logger.debug(f"Service call: {service}.{method}", extra=extra)
    
    def log_aws_api_call(self, service: str, operation: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        """Log AWS API calls for complete AWS operation visibility."""
        extra = {
            'aws_api_call': f"{service}:{operation}",
            'operation': f"aws_{service}_{operation}",
            'processing_step': 'aws_api_call',
            **kwargs
        }
        if params:
            # Sanitize sensitive parameters
            sanitized_params = self._sanitize_params(params)
            extra['query_params'] = sanitized_params
        
        self.logger.info(f"AWS API call: {service}.{operation}", extra=extra)
    
    def log_resource_operation(self, resource_type: str, operation: str, resource_id: Optional[str] = None, **kwargs) -> None:
        """Log resource creation, deletion, modification operations."""
        extra = {
            'resource_operation': f"{resource_type}_{operation}",
            'operation': f"resource_{operation}",
            'processing_step': 'resource_management',
            **kwargs
        }
        if resource_id:
            extra['resource_id'] = resource_id
        
        self.logger.info(f"Resource {operation}: {resource_type}", extra=extra)
    
    def log_search_operation(self, query: str, search_type: str, results_count: Optional[int] = None, **kwargs) -> None:
        """Log search operations with query and results information."""
        extra = {
            'search_query': query[:500] if query else '',  # Limit query length
            'operation': f"search_{search_type}",
            'processing_step': 'search_execution',
            **kwargs
        }
        if results_count is not None:
            extra['response_size'] = results_count
        
        self.logger.info(f"Search: {search_type} query executed", extra=extra)
    
    def log_video_operation(self, operation: str, video_id: Optional[str] = None, **kwargs) -> None:
        """Log video processing operations."""
        extra = {
            'video_operation': operation,
            'operation': f"video_{operation}",
            'processing_step': 'video_processing',
            **kwargs
        }
        if video_id:
            extra['resource_id'] = video_id
        
        self.logger.info(f"Video operation: {operation}", extra=extra)
    
    def log_visualization_state(self, state: str, component: str, **kwargs) -> None:
        """Log visualization state changes."""
        extra = {
            'visualization_state': state,
            'frontend_component': component,
            'operation': f"visualization_{state}",
            'processing_step': 'visualization_update',
            **kwargs
        }
        self.logger.debug(f"Visualization state: {state} in {component}", extra=extra)
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        **kwargs
    ) -> None:
        """
        Enhanced error logging with structured data and context.
        
        Args:
            operation: Name of the operation that failed
            error: Exception that occurred
            **kwargs: Additional structured data to include
        """
        extra = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'component': self.component_name,
            'processing_step': 'error_handling',
            **kwargs
        }
        
        # Add error code if available
        if hasattr(error, 'error_code'):
            extra['error_code'] = error.error_code
        
        self.logger.error(
            f"Operation failed: {operation} - {str(error)}",
            extra=extra,
            exc_info=True
        )
    
    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        **kwargs
    ) -> None:
        """
        Enhanced performance logging with detailed metrics.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            **kwargs: Additional performance metrics
        """
        performance_metrics = {
            'duration_ms': duration_ms,
            'performance_category': self._categorize_performance(duration_ms),
            **kwargs
        }
        
        extra = {
            'operation': operation,
            'performance_metrics': performance_metrics,
            'component': self.component_name,
            'processing_step': 'performance_tracking'
        }
        
        level = 'WARNING' if duration_ms > 5000 else 'INFO'
        self.logger.log(
            getattr(logging, level),
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            extra=extra
        )
    
    def log_cost(
        self,
        operation: str,
        cost_estimate: float,
        volume: int,
        **kwargs
    ) -> None:
        """
        Enhanced cost logging with budget tracking.
        
        Args:
            operation: Name of the operation
            cost_estimate: Estimated cost in USD
            volume: Volume of operations
            **kwargs: Additional cost-related data
        """
        extra = {
            'operation': operation,
            'cost_estimate': cost_estimate,
            'volume': volume,
            'component': self.component_name,
            'processing_step': 'cost_tracking',
            **kwargs
        }
        
        level = 'WARNING' if cost_estimate > 1.0 else 'INFO'
        self.logger.log(
            getattr(logging, level),
            f"Cost: {operation} estimated at ${cost_estimate:.4f} for {volume} operations",
            extra=extra
        )
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive parameters for logging."""
        sensitive_keys = {'api_key', 'secret', 'token', 'password', 'credential', 'authorization'}
        sanitized = {}
        
        for key, value in params.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _categorize_performance(self, duration_ms: float) -> str:
        """Categorize performance based on duration."""
        if duration_ms < 100:
            return "fast"
        elif duration_ms < 1000:
            return "normal"
        elif duration_ms < 5000:
            return "slow"
        else:
            return "very_slow"


def log_function_calls(logger: StructuredLogger):
    """
    Decorator to automatically log function entry/exit with timing.
    
    Args:
        logger: StructuredLogger instance to use for logging
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            start_time = time.time()
            
            # Log function entry
            logger.log_function_entry(func_name, args_count=len(args), kwargs_keys=list(kwargs.keys()))
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log function exit with performance
                logger.log_function_exit(func_name, result=result)
                logger.log_performance(f"{func_name}_execution", duration_ms)
                
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error with timing
                logger.log_error(f"{func_name}_execution", e, duration_ms=duration_ms)
                raise
        
        return wrapper
    return decorator


def log_aws_calls(logger: StructuredLogger, service_name: str):
    """
    Decorator to automatically log AWS service calls.
    
    Args:
        logger: StructuredLogger instance
        service_name: Name of the AWS service
    
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = func.__name__
            start_time = time.time()
            
            # Extract relevant parameters for logging
            log_params = {}
            if args and hasattr(args[0], '__dict__'):
                # Skip 'self' parameter
                log_params.update({k: v for k, v in kwargs.items() if not k.startswith('_')})
            
            logger.log_aws_api_call(service_name, operation_name, log_params)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.log_performance(f"aws_{service_name}_{operation_name}", duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.log_error(f"aws_{service_name}_{operation_name}", e, duration_ms=duration_ms)
                raise
        
        return wrapper
    return decorator


def setup_logging(
    level: str = 'INFO',
    structured: bool = True,
    log_file: Optional[str] = None,
    enable_debug_mode: bool = False
) -> None:
    """
    Enhanced logging setup with debugging capabilities.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured JSON logging
        log_file: Optional file path for log output
        enable_debug_mode: Enable comprehensive debug logging
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set logging level - force DEBUG if debug mode enabled
    if enable_debug_mode:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, level.upper())
    
    root_logger.setLevel(log_level)
    
    # Create formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        # Enhanced console formatter for debugging
        if enable_debug_mode:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
    
    # Console handler with enhanced configuration
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Create log directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set third-party logger levels
    external_loggers = {
        'boto3': logging.WARNING,
        'botocore': logging.WARNING,
        'urllib3': logging.WARNING,
        'requests': logging.WARNING,
        'matplotlib': logging.WARNING,
        'PIL': logging.WARNING
    }
    
    for logger_name, log_level in external_loggers.items():
        logging.getLogger(logger_name).setLevel(log_level)
    
    # Enable debug logging for our application modules if debug mode
    if enable_debug_mode:
        app_loggers = ['src', 'frontend', 'tests']
        for logger_name in app_loggers:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
    
    # Log the logging setup
    setup_logger = get_structured_logger(__name__)
    setup_logger.log_operation(
        'logging_setup_complete',
        level='INFO',
        log_level=level,
        structured=structured,
        debug_mode=enable_debug_mode,
        log_file=log_file
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


def setup_debug_logging() -> None:
    """Setup comprehensive debug logging for development and troubleshooting."""
    setup_logging(
        level='DEBUG',
        structured=True,
        log_file='logs/s3vector_debug.log',
        enable_debug_mode=True
    )


# Context manager for operation logging
class LoggedOperation:
    """Context manager for logging operations with automatic timing and error handling."""
    
    def __init__(self, logger: StructuredLogger, operation_name: str, **kwargs):
        self.logger = logger
        self.operation_name = operation_name
        self.kwargs = kwargs
        self.start_time: float = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.log_operation(
            f"{self.operation_name}_start",
            level='DEBUG',
            **self.kwargs
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time > 0:
            duration_ms = (time.time() - self.start_time) * 1000
        else:
            duration_ms = 0.0
        
        if exc_type is None:
            # Success
            self.logger.log_operation(
                f"{self.operation_name}_complete",
                level='DEBUG',
                duration_ms=duration_ms,
                **self.kwargs
            )
            self.logger.log_performance(self.operation_name, duration_ms)
        else:
            # Error occurred
            self.logger.log_error(
                self.operation_name,
                exc_val,
                duration_ms=duration_ms,
                **self.kwargs
            )
        return False  # Don't suppress exceptions


# Create module-level structured logger
structured_logger = StructuredLogger(__name__)