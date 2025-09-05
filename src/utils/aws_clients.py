"""
AWS client factory with optimized configuration for S3 Vectors, Bedrock, and OpenSearch.

This module provides centralized client creation with proper retry logic,
timeouts, and connection pooling for optimal performance.
"""

import boto3
from botocore.config import Config
from typing import Dict, Any, Optional
import logging
import os

from src.config.unified_config_manager import get_unified_config_manager
from src.exceptions import ConfigurationError
from src.utils.logging_config import get_structured_logger, LoggedOperation

logger = logging.getLogger(__name__)
structured_logger = get_structured_logger(__name__)


class AWSClientFactory:
    """Factory for creating optimized AWS service clients."""
    
    def __init__(self):
        self._clients: Dict[str, Any] = {}
        self._session: Optional[boto3.Session] = None
        self._demo_mode: Optional[bool] = None
    
    def _is_demo_mode(self) -> bool:
        """Check if running in demo mode (no real AWS credentials)."""
        if self._demo_mode is None:
            config_manager = get_unified_config_manager()
            # Check if real AWS is enabled and credentials are available
            enable_real_aws = config_manager.get_feature_flag('enable_real_aws')
            aws_config = config_manager.config.aws
            
            has_credentials = (
                aws_config.access_key_id or
                aws_config.secret_access_key or
                # Check for default credential providers (env vars, IAM role, etc.)
                bool(os.getenv('AWS_ACCESS_KEY_ID')) or
                bool(os.getenv('AWS_SECRET_ACCESS_KEY')) or
                bool(os.getenv('AWS_PROFILE'))
            )
            
            self._demo_mode = not (enable_real_aws and has_credentials)
            
            if self._demo_mode:
                logger.info("Running in demo mode - AWS clients will use mock functionality")
            else:
                logger.info("Running with real AWS credentials")
                
        return self._demo_mode
    
    def _get_session(self) -> boto3.Session:
        """Get or create boto3 session with consistent configuration."""
        if self._session is None:
            config_manager = get_unified_config_manager()
            aws_config = config_manager.config.aws
            
            # Always create session with region, credentials optional
            session_kwargs = {'region_name': aws_config.region}
            
            # Only add credentials if they're provided
            if aws_config.access_key_id:
                session_kwargs['aws_access_key_id'] = aws_config.access_key_id
            if aws_config.secret_access_key:
                session_kwargs['aws_secret_access_key'] = aws_config.secret_access_key
            if aws_config.session_token:
                session_kwargs['aws_session_token'] = aws_config.session_token
                
            self._session = boto3.Session(**session_kwargs)
        return self._session
    
    def _get_client_config(self) -> Config:
        """Get optimized client configuration."""
        config_manager = get_unified_config_manager()
        aws_config = config_manager.config.aws
        
        return Config(
            retries={
                'max_attempts': aws_config.max_retries,
                'mode': 'adaptive'
            },
            read_timeout=aws_config.timeout_seconds,
            connect_timeout=10,
            max_pool_connections=50,
            region_name=aws_config.region
        )
    
    def get_s3vectors_client(self) -> Any:
        """Get S3 Vectors client with optimized configuration."""
        structured_logger.log_function_entry("get_s3vectors_client")
        
        if 's3vectors' not in self._clients:
            with LoggedOperation(structured_logger, "create_s3vectors_client"):
                try:
                    demo_mode = self._is_demo_mode()
                    structured_logger.log_aws_api_call(
                        "s3vectors",
                        "create_client",
                        {"demo_mode": demo_mode}
                    )
                    
                    if demo_mode:
                        # Return a mock client for demo mode
                        from unittest.mock import MagicMock
                        mock_client = MagicMock()
                        mock_client._demo_mode = True
                        self._clients['s3vectors'] = mock_client
                        
                        structured_logger.log_operation(
                            "s3vectors_client_created_demo",
                            level="INFO",
                            client_type="mock"
                        )
                        logger.info("S3 Vectors client created in demo mode")
                    else:
                        structured_logger.log_service_call("boto3", "Session.client", {"service": "s3vectors"})
                        session = self._get_session()
                        config = self._get_client_config()
                        
                        self._clients['s3vectors'] = session.client(
                            's3vectors',
                            config=config
                        )
                        
                        structured_logger.log_operation(
                            "s3vectors_client_created_real",
                            level="INFO",
                            client_type="boto3",
                            region=config.region_name,
                            max_attempts=config.retries.get('max_attempts')
                        )
                        logger.info("S3 Vectors client created successfully")
                    
                except Exception as e:
                    structured_logger.log_error("s3vectors_client_creation", e, demo_mode=self._is_demo_mode())
                    
                    if self._is_demo_mode():
                        # Fallback to mock if real client fails in demo mode
                        from unittest.mock import MagicMock
                        mock_client = MagicMock()
                        mock_client._demo_mode = True
                        self._clients['s3vectors'] = mock_client
                        
                        structured_logger.log_operation(
                            "s3vectors_client_fallback_demo",
                            level="WARNING",
                            original_error=str(e)
                        )
                        logger.warning(f"Using demo mode for S3 Vectors due to: {e}")
                    else:
                        structured_logger.log_error("s3vectors_client_creation_fatal", e)
                        raise ConfigurationError(
                            f"Failed to create S3 Vectors client: {str(e)}",
                            error_code="S3VECTORS_CLIENT_ERROR",
                            error_details={"original_error": str(e)}
                        )
        
        structured_logger.log_function_exit("get_s3vectors_client", result="client_ready")
        return self._clients['s3vectors']
    
    def get_bedrock_runtime_client(self) -> Any:
        """Get Bedrock Runtime client with optimized configuration."""
        if 'bedrock-runtime' not in self._clients:
            try:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['bedrock-runtime'] = mock_client
                    logger.info("Bedrock Runtime client created in demo mode")
                else:
                    session = self._get_session()
                    config = self._get_client_config()
                    
                    self._clients['bedrock-runtime'] = session.client(
                        'bedrock-runtime',
                        config=config
                    )
                    
                    logger.info("Bedrock Runtime client created successfully")
                
            except Exception as e:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['bedrock-runtime'] = mock_client
                    logger.warning(f"Using demo mode for Bedrock Runtime due to: {e}")
                else:
                    raise ConfigurationError(
                        f"Failed to create Bedrock Runtime client: {str(e)}",
                        error_code="BEDROCK_CLIENT_ERROR",
                        error_details={"original_error": str(e)}
                    )
        
        return self._clients['bedrock-runtime']
    
    def get_opensearch_client(self) -> Any:
        """Get OpenSearch client with optimized configuration."""
        if 'opensearch' not in self._clients:
            try:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['opensearch'] = mock_client
                    logger.info("OpenSearch client created in demo mode")
                else:
                    session = self._get_session()
                    config = self._get_client_config()
                    
                    self._clients['opensearch'] = session.client(
                        'opensearch',
                        config=config
                    )
                    
                    logger.info("OpenSearch client created successfully")
                
            except Exception as e:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['opensearch'] = mock_client
                    logger.warning(f"Using demo mode for OpenSearch due to: {e}")
                else:
                    raise ConfigurationError(
                        f"Failed to create OpenSearch client: {str(e)}",
                        error_code="OPENSEARCH_CLIENT_ERROR",
                        error_details={"original_error": str(e)}
                    )
        
        return self._clients['opensearch']
    
    def get_s3_client(self) -> Any:
        """Get standard S3 client for general S3 operations."""
        if 's3' not in self._clients:
            try:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['s3'] = mock_client
                    logger.info("S3 client created in demo mode")
                else:
                    session = self._get_session()
                    config = self._get_client_config()
                    
                    self._clients['s3'] = session.client(
                        's3',
                        config=config
                    )
                    
                    logger.info("S3 client created successfully")
                
            except Exception as e:
                if self._is_demo_mode():
                    from unittest.mock import MagicMock
                    mock_client = MagicMock()
                    mock_client._demo_mode = True
                    self._clients['s3'] = mock_client
                    logger.warning(f"Using demo mode for S3 due to: {e}")
                else:
                    raise ConfigurationError(
                        f"Failed to create S3 client: {str(e)}",
                        error_code="S3_CLIENT_ERROR",
                        error_details={"original_error": str(e)}
                    )
        
        return self._clients['s3']
    
    def validate_clients(self) -> Dict[str, bool]:
        """Validate that all clients can be created successfully."""
        validation_results = {}
        
        try:
            client = self.get_s3vectors_client()
            validation_results['s3vectors'] = True
            validation_results['s3vectors_demo_mode'] = hasattr(client, '_demo_mode')
        except Exception as e:
            logger.error(f"S3 Vectors client validation failed: {e}")
            validation_results['s3vectors'] = False
        
        try:
            client = self.get_bedrock_runtime_client()
            validation_results['bedrock-runtime'] = True
            validation_results['bedrock_demo_mode'] = hasattr(client, '_demo_mode')
        except Exception as e:
            logger.error(f"Bedrock Runtime client validation failed: {e}")
            validation_results['bedrock-runtime'] = False
        
        try:
            client = self.get_opensearch_client()
            validation_results['opensearch'] = True
            validation_results['opensearch_demo_mode'] = hasattr(client, '_demo_mode')
        except Exception as e:
            logger.error(f"OpenSearch client validation failed: {e}")
            validation_results['opensearch'] = False
        
        try:
            client = self.get_s3_client()
            validation_results['s3'] = True
            validation_results['s3_demo_mode'] = hasattr(client, '_demo_mode')
        except Exception as e:
            logger.error(f"S3 client validation failed: {e}")
            validation_results['s3'] = False
        
        validation_results['demo_mode'] = self._is_demo_mode()
        return validation_results
    
    def is_demo_mode(self) -> bool:
        """Public method to check if clients are running in demo mode."""
        return self._is_demo_mode()
    
    def reset_clients(self) -> None:
        """Reset all cached clients (useful for configuration changes)."""
        self._clients.clear()
        self._session = None
        self._demo_mode = None  # Reset demo mode detection
        logger.info("All AWS clients reset")


# Global client factory instance
aws_client_factory = AWSClientFactory()