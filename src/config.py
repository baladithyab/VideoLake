"""
Configuration management for S3 Vector Embedding POC.

This module handles AWS credentials, regions, and service configuration
with environment-based settings and validation.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any
from src.exceptions import ConfigurationError

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    
    # Look for .env file in project root
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded environment variables from {env_path}")
    else:
        print("No .env file found, using system environment variables")
        
except ImportError:
    print("python-dotenv not installed, using system environment variables only")


@dataclass
class AWSConfig:
    """AWS service configuration settings."""
    
    region: str
    s3_vectors_bucket: str
    bedrock_models: Dict[str, str]
    opensearch_domain: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 60
    
    @classmethod
    def from_environment(cls) -> 'AWSConfig':
        """Create configuration from environment variables."""
        region = os.getenv('AWS_REGION', 'us-west-2')
        s3_vectors_bucket = os.getenv('S3_VECTORS_BUCKET')
        
        if not s3_vectors_bucket:
            raise ConfigurationError(
                "S3_VECTORS_BUCKET environment variable is required",
                error_code="MISSING_BUCKET_CONFIG"
            )
        
        bedrock_models = {
            'text_embedding': os.getenv(
                'BEDROCK_TEXT_MODEL', 
                'amazon.titan-embed-text-v2:0'
            ),
            'multimodal_embedding': os.getenv(
                'BEDROCK_MM_MODEL', 
                'amazon.titan-embed-image-v1'
            ),
            'video_embedding': os.getenv(
                'TWELVELABS_MODEL', 
                'twelvelabs.marengo-embed-2-7-v1:0'
            )
        }
        
        return cls(
            region=region,
            s3_vectors_bucket=s3_vectors_bucket,
            bedrock_models=bedrock_models,
            opensearch_domain=os.getenv('OPENSEARCH_DOMAIN'),
            max_retries=int(os.getenv('AWS_MAX_RETRIES', '3')),
            timeout_seconds=int(os.getenv('AWS_TIMEOUT_SECONDS', '60'))
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if not self.region:
            raise ConfigurationError(
                "AWS region is required",
                error_code="MISSING_REGION"
            )
        
        if not self.s3_vectors_bucket:
            raise ConfigurationError(
                "S3 Vectors bucket name is required",
                error_code="MISSING_BUCKET"
            )
        
        required_models = ['text_embedding', 'multimodal_embedding', 'video_embedding']
        for model_type in required_models:
            if model_type not in self.bedrock_models or not self.bedrock_models[model_type]:
                raise ConfigurationError(
                    f"Bedrock model ID for {model_type} is required",
                    error_code="MISSING_MODEL_ID",
                    error_details={"model_type": model_type}
                )


@dataclass
class ProcessingConfig:
    """Configuration for processing operations."""
    
    batch_size_text: int = 100
    batch_size_video: int = 10
    batch_size_vectors: int = 1000
    video_segment_duration: int = 5  # seconds
    max_video_duration: int = 7200   # 2 hours in seconds
    poll_interval: int = 30          # seconds for async job polling
    
    @classmethod
    def from_environment(cls) -> 'ProcessingConfig':
        """Create processing configuration from environment variables."""
        return cls(
            batch_size_text=int(os.getenv('BATCH_SIZE_TEXT', '100')),
            batch_size_video=int(os.getenv('BATCH_SIZE_VIDEO', '10')),
            batch_size_vectors=int(os.getenv('BATCH_SIZE_VECTORS', '1000')),
            video_segment_duration=int(os.getenv('VIDEO_SEGMENT_DURATION', '5')),
            max_video_duration=int(os.getenv('MAX_VIDEO_DURATION', '7200')),
            poll_interval=int(os.getenv('POLL_INTERVAL', '30'))
        )


class ConfigManager:
    """Centralized configuration management."""
    
    def __init__(self):
        self._aws_config: Optional[AWSConfig] = None
        self._processing_config: Optional[ProcessingConfig] = None
    
    @property
    def aws_config(self) -> AWSConfig:
        """Get AWS configuration, loading from environment if needed."""
        if self._aws_config is None:
            self._aws_config = AWSConfig.from_environment()
            self._aws_config.validate()
        return self._aws_config
    
    @property
    def processing_config(self) -> ProcessingConfig:
        """Get processing configuration, loading from environment if needed."""
        if self._processing_config is None:
            self._processing_config = ProcessingConfig.from_environment()
        return self._processing_config
    
    def reload(self) -> None:
        """Reload configuration from environment variables."""
        self._aws_config = None
        self._processing_config = None


# Global configuration instance
config_manager = ConfigManager()