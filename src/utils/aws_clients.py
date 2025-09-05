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
                    structured_logger.log_aws_api_call(
                        "s3vectors",
                        "create_client",
                        {"service": "s3vectors"}
                    )
                    
                    structured_logger.log_service_call("boto3", "Session.client", {"service": "s3vectors"})
                    session = self._get_session()
                    config = self._get_client_config()
                    
                    self._clients['s3vectors'] = session.client(
                        's3vectors',
                        config=config
                    )
                    
                    config_manager = get_unified_config_manager()
                    aws_config = config_manager.config.aws
                    structured_logger.log_operation(
                        "s3vectors_client_created",
                        level="INFO",
                        client_type="boto3",
                        region=aws_config.region,
                        max_attempts=aws_config.max_retries
                    )
                    logger.info("S3 Vectors client created successfully")
                    
                except Exception as e:
                    structured_logger.log_error("s3vectors_client_creation_fatal", e)
                    raise ConfigurationError(
                        f"Failed to create S3 Vectors client: {str(e)}. Please ensure AWS credentials are properly configured.",
                        error_code="S3VECTORS_CLIENT_ERROR",
                        error_details={"original_error": str(e)}
                    )
        
        structured_logger.log_function_exit("get_s3vectors_client", result="client_ready")
        return self._clients['s3vectors']
    
    def get_bedrock_runtime_client(self) -> Any:
        """Get Bedrock Runtime client with optimized configuration."""
        if 'bedrock-runtime' not in self._clients:
            try:
                session = self._get_session()
                config = self._get_client_config()
                
                self._clients['bedrock-runtime'] = session.client(
                    'bedrock-runtime',
                    config=config
                )
                
                logger.info("Bedrock Runtime client created successfully")
                
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create Bedrock Runtime client: {str(e)}. Please ensure AWS credentials and region are properly configured.",
                    error_code="BEDROCK_CLIENT_ERROR",
                    error_details={"original_error": str(e)}
                )
        
        return self._clients['bedrock-runtime']
    
    def get_opensearch_client(self) -> Any:
        """Get OpenSearch client with optimized configuration."""
        if 'opensearch' not in self._clients:
            try:
                session = self._get_session()
                config = self._get_client_config()
                
                self._clients['opensearch'] = session.client(
                    'opensearch',
                    config=config
                )
                
                logger.info("OpenSearch client created successfully")
                
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create OpenSearch client: {str(e)}. Please ensure AWS credentials and region are properly configured.",
                    error_code="OPENSEARCH_CLIENT_ERROR",
                    error_details={"original_error": str(e)}
                )
        
        return self._clients['opensearch']
    
    def get_s3_client(self) -> Any:
        """Get standard S3 client for general S3 operations."""
        if 's3' not in self._clients:
            try:
                session = self._get_session()
                config = self._get_client_config()
                
                self._clients['s3'] = session.client(
                    's3',
                    config=config
                )
                
                logger.info("S3 client created successfully")
                
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create S3 client: {str(e)}. Please ensure AWS credentials and region are properly configured.",
                    error_code="S3_CLIENT_ERROR",
                    error_details={"original_error": str(e)}
                )
        
        return self._clients['s3']
    
    def validate_clients(self) -> Dict[str, bool]:
        """Validate that all clients can be created successfully."""
        validation_results = {}
        
        try:
            self.get_s3vectors_client()
            validation_results['s3vectors'] = True
        except Exception as e:
            logger.error(f"S3 Vectors client validation failed: {e}")
            validation_results['s3vectors'] = False
        
        try:
            self.get_bedrock_runtime_client()
            validation_results['bedrock-runtime'] = True
        except Exception as e:
            logger.error(f"Bedrock Runtime client validation failed: {e}")
            validation_results['bedrock-runtime'] = False
        
        try:
            self.get_opensearch_client()
            validation_results['opensearch'] = True
        except Exception as e:
            logger.error(f"OpenSearch client validation failed: {e}")
            validation_results['opensearch'] = False
        
        try:
            self.get_s3_client()
            validation_results['s3'] = True
        except Exception as e:
            logger.error(f"S3 client validation failed: {e}")
            validation_results['s3'] = False
        
        return validation_results
    
    def reset_clients(self) -> None:
        """Reset all cached clients (useful for configuration changes)."""
        self._clients.clear()
        self._session = None
        logger.info("All AWS clients reset")


# Global client factory instance
aws_client_factory = AWSClientFactory()