"""
Core initialization module for S3 Vector Embedding POC.

This module provides the main entry point and initialization logic
for the vector embedding pipeline.
"""

import logging
from typing import Dict, Any, Optional

from src.config import config_manager
from src.utils.aws_clients import aws_client_factory
from src.utils.logging_config import setup_logging, StructuredLogger
from src.exceptions import ConfigurationError, VectorEmbeddingError

logger = StructuredLogger(__name__)


class VectorEmbeddingPOC:
    """
    Main class for the S3 Vector Embedding POC.
    
    This class orchestrates the initialization and provides access
    to all core components of the system.
    """
    
    def __init__(self, log_level: str = 'INFO', structured_logging: bool = True):
        """
        Initialize the POC system.
        
        Args:
            log_level: Logging level for the application
            structured_logging: Whether to use structured JSON logging
        """
        self._initialized = False
        self._log_level = log_level
        self._structured_logging = structured_logging
        
        # Initialize logging first
        setup_logging(
            level=log_level,
            structured=structured_logging
        )
        
        logger.log_operation("poc_initialization_started")
    
    def initialize(self) -> None:
        """
        Initialize all system components.
        
        Raises:
            ConfigurationError: If configuration is invalid
            VectorEmbeddingError: If initialization fails
        """
        try:
            logger.log_operation("validating_configuration")
            
            # Validate configuration
            aws_config = config_manager.aws_config
            processing_config = config_manager.processing_config
            
            logger.log_operation(
                "configuration_loaded",
                aws_region=aws_config.region,
                s3_bucket=aws_config.s3_vectors_bucket,
                batch_sizes={
                    'text': processing_config.batch_size_text,
                    'video': processing_config.batch_size_video,
                    'vectors': processing_config.batch_size_vectors
                }
            )
            
            # Validate AWS clients
            logger.log_operation("validating_aws_clients")
            client_validation = aws_client_factory.validate_clients()
            
            failed_clients = [
                client for client, success in client_validation.items()
                if not success
            ]
            
            if failed_clients:
                raise ConfigurationError(
                    f"Failed to initialize AWS clients: {failed_clients}",
                    error_code="CLIENT_INITIALIZATION_FAILED",
                    error_details={"failed_clients": failed_clients}
                )
            
            logger.log_operation(
                "aws_clients_validated",
                validated_clients=list(client_validation.keys())
            )
            
            self._initialized = True
            logger.log_operation("poc_initialization_completed")
            
        except Exception as e:
            logger.log_error("poc_initialization_failed", e)
            raise
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system information and status.
        
        Returns:
            Dictionary containing system information
        """
        if not self._initialized:
            raise VectorEmbeddingError(
                "System not initialized. Call initialize() first.",
                error_code="SYSTEM_NOT_INITIALIZED"
            )
        
        aws_config = config_manager.aws_config
        processing_config = config_manager.processing_config
        
        return {
            'initialized': self._initialized,
            'aws_config': {
                'region': aws_config.region,
                's3_vectors_bucket': aws_config.s3_vectors_bucket,
                'bedrock_models': aws_config.bedrock_models,
                'opensearch_domain': aws_config.opensearch_domain,
                'max_retries': aws_config.max_retries,
                'timeout_seconds': aws_config.timeout_seconds
            },
            'processing_config': {
                'batch_size_text': processing_config.batch_size_text,
                'batch_size_video': processing_config.batch_size_video,
                'batch_size_vectors': processing_config.batch_size_vectors,
                'video_segment_duration': processing_config.video_segment_duration,
                'max_video_duration': processing_config.max_video_duration,
                'poll_interval': processing_config.poll_interval
            },
            'logging': {
                'level': self._log_level,
                'structured': self._structured_logging
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform system health check.
        
        Returns:
            Dictionary containing health check results
        """
        if not self._initialized:
            return {
                'status': 'unhealthy',
                'reason': 'System not initialized'
            }
        
        try:
            # Validate AWS clients
            client_validation = aws_client_factory.validate_clients()
            
            all_healthy = all(client_validation.values())
            
            return {
                'status': 'healthy' if all_healthy else 'degraded',
                'clients': client_validation,
                'timestamp': logger.logger.handlers[0].formatter.formatTime(
                    logging.LogRecord('', 0, '', 0, '', (), None)
                ) if logger.logger.handlers else None
            }
            
        except Exception as e:
            logger.log_error("health_check_failed", e)
            return {
                'status': 'unhealthy',
                'reason': str(e)
            }
    
    @property
    def is_initialized(self) -> bool:
        """Check if the system is initialized."""
        return self._initialized


def create_poc_instance(
    log_level: str = 'INFO',
    structured_logging: bool = True,
    auto_initialize: bool = True
) -> VectorEmbeddingPOC:
    """
    Create and optionally initialize a POC instance.
    
    Args:
        log_level: Logging level for the application
        structured_logging: Whether to use structured JSON logging
        auto_initialize: Whether to automatically initialize the system
        
    Returns:
        VectorEmbeddingPOC instance
    """
    poc = VectorEmbeddingPOC(
        log_level=log_level,
        structured_logging=structured_logging
    )
    
    if auto_initialize:
        poc.initialize()
    
    return poc