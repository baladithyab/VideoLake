"""
Structured logging configuration for S3 Vector Embedding POC.

This module provides centralized logging setup with structured output
for better monitoring and debugging.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        
        if hasattr(record, 'cost_estimate'):
            log_entry['cost_estimate'] = record.cost_estimate
        
        if hasattr(record, 'performance_metrics'):
            log_entry['performance_metrics'] = record.performance_metrics
        
        return json.dumps(log_entry)


class StructuredLogger:
    """Wrapper for structured logging operations."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
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
        extra = {'operation': operation, **kwargs}
        
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, f"Operation: {operation}", extra=extra)
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        **kwargs
    ) -> None:
        """
        Log an error with structured data.
        
        Args:
            operation: Name of the operation that failed
            error: Exception that occurred
            **kwargs: Additional structured data to include
        """
        extra = {
            'operation': operation,
            'error_type': type(error).__name__,
            'error_message': str(error),
            **kwargs
        }
        
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
        Log performance metrics for an operation.
        
        Args:
            operation: Name of the operation
            duration_ms: Duration in milliseconds
            **kwargs: Additional performance metrics
        """
        performance_metrics = {
            'duration_ms': duration_ms,
            **kwargs
        }
        
        extra = {
            'operation': operation,
            'performance_metrics': performance_metrics
        }
        
        self.logger.info(
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
        Log cost information for an operation.
        
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
            **kwargs
        }
        
        self.logger.info(
            f"Cost: {operation} estimated at ${cost_estimate:.4f} for {volume} operations",
            extra=extra
        )


def setup_logging(
    level: str = 'INFO',
    structured: bool = True,
    log_file: Optional[str] = None
) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured JSON logging
        log_file: Optional file path for log output
    """
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set logging level
    log_level = getattr(logging, level.upper())
    root_logger.setLevel(log_level)
    
    # Create formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


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


# Create module-level structured logger
structured_logger = StructuredLogger(__name__)