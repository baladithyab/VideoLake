#!/usr/bin/env python3
"""
Unified Configuration Management System

Comprehensive configuration system with environment-based settings,
feature flags, and runtime configuration updates.
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Environment(Enum):
    """Environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AWSConfig:
    """AWS service configuration."""
    region: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    
    # S3Vector configuration
    s3vector_endpoint: Optional[str] = None
    s3vector_access_key: Optional[str] = None
    s3vector_secret_key: Optional[str] = None
    
    # S3 configuration
    s3_bucket: str = "s3vector-production-bucket"
    s3_prefix: str = "vectors/"
    
    # Bedrock configuration
    bedrock_model_id: str = "amazon.titan-embed-text-v1"
    bedrock_max_tokens: int = 8192


@dataclass
class MarengoConfig:
    """Marengo 2.7 model configuration with access method selection."""
    # Access method selection
    access_method: str = "bedrock"  # "bedrock" or "twelvelabs_api"

    # Bedrock access configuration
    bedrock_model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    bedrock_region: str = "us-east-1"  # Marengo available in us-east-1, eu-west-1, ap-northeast-2

    # TwelveLabs API access configuration
    twelvelabs_api_key: Optional[str] = None
    twelvelabs_api_url: str = "https://api.twelvelabs.io"
    twelvelabs_model_name: str = "marengo2.7"

    # Common processing configuration
    max_video_duration: int = 3600  # seconds
    segment_duration: float = 5.0  # seconds
    supported_vector_types: List[str] = field(default_factory=lambda: [
        "visual-text", "visual-image", "audio"
    ])

    # Bedrock-specific settings
    bedrock_supported_regions: List[str] = field(default_factory=lambda: [
        "us-east-1", "eu-west-1", "ap-northeast-2"
    ])

    def get_model_identifier(self) -> str:
        """Get the appropriate model identifier based on access method."""
        if self.access_method == "bedrock":
            return self.bedrock_model_id
        else:
            return self.twelvelabs_model_name

    def is_bedrock_access(self) -> bool:
        """Check if using Bedrock access method."""
        return self.access_method == "bedrock"

    def is_twelvelabs_api_access(self) -> bool:
        """Check if using TwelveLabs API access method."""
        return self.access_method == "twelvelabs_api"

    def validate_configuration(self) -> bool:
        """Validate configuration based on access method."""
        if self.access_method == "bedrock":
            return self.bedrock_region in self.bedrock_supported_regions
        elif self.access_method == "twelvelabs_api":
            return self.twelvelabs_api_key is not None
        return False


@dataclass
class TwelveLabsConfig:
    """Legacy TwelveLabs configuration for backward compatibility."""
    api_key: Optional[str] = None
    api_url: str = "https://api.twelvelabs.io"
    model_name: str = "marengo2.7"
    max_video_duration: int = 3600  # seconds
    segment_duration: float = 5.0  # seconds


@dataclass
class OpenSearchConfig:
    """OpenSearch service configuration."""
    endpoint: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    index_prefix: str = "s3vector"
    max_results: int = 100


@dataclass
class FeatureFlags:
    """Feature flags for enabling/disabling functionality."""
    enable_real_aws: bool = False
    enable_opensearch_hybrid: bool = True
    enable_video_upload: bool = True
    enable_cost_estimation: bool = True
    enable_performance_monitoring: bool = True
    enable_error_dashboard: bool = True
    enable_advanced_visualization: bool = True
    enable_multi_vector_processing: bool = True
    enable_query_auto_detection: bool = True
    enable_segment_navigation: bool = True


@dataclass
class UIConfig:
    """UI configuration settings."""
    app_title: str = "S3Vector"
    app_icon: str = "🔍"
    page_layout: str = "wide"
    sidebar_state: str = "expanded"
    theme: str = "light"
    
    # Workflow sections
    workflow_sections: List[str] = field(default_factory=lambda: [
        "Upload & Processing",
        "Query & Search", 
        "Results & Playback",
        "Embedding Visualization",
        "Analytics & Management"
    ])
    
    # Default selections
    default_vector_types: List[str] = field(default_factory=lambda: [
        "visual-text", "visual-image", "audio"
    ])
    default_storage_patterns: List[str] = field(default_factory=lambda: [
        "direct_s3vector", "opensearch_s3vector_hybrid"
    ])
    default_processing_mode: str = "parallel"
    default_segment_duration: float = 5.0


@dataclass
class PerformanceConfig:
    """Performance and optimization settings."""
    max_concurrent_jobs: int = 8
    request_timeout: int = 30
    max_retries: int = 3
    cache_ttl: int = 3600  # seconds
    max_memory_usage: int = 4096  # MB
    enable_caching: bool = True
    enable_compression: bool = True


@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_https: bool = True
    session_timeout: int = 3600  # seconds
    max_upload_size: int = 500  # MB
    allowed_file_types: List[str] = field(default_factory=lambda: [
        ".mp4", ".avi", ".mov", ".mkv", ".webm"
    ])
    enable_cors: bool = False
    enable_xsrf_protection: bool = False


@dataclass
class AppConfig:
    """Main application configuration."""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    host: str = "localhost"
    port: int = 8501

    # Service configurations
    aws: AWSConfig = field(default_factory=AWSConfig)
    marengo: MarengoConfig = field(default_factory=MarengoConfig)
    twelvelabs: TwelveLabsConfig = field(default_factory=TwelveLabsConfig)  # Legacy compatibility
    opensearch: OpenSearchConfig = field(default_factory=OpenSearchConfig)
    
    # Feature flags
    features: FeatureFlags = field(default_factory=FeatureFlags)
    
    # UI configuration
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Performance configuration
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Security configuration
    security: SecurityConfig = field(default_factory=SecurityConfig)


class ConfigManager:
    """Configuration manager with environment-based loading."""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config_file = self.config_dir / "config.yaml"
        self.env_file = Path.cwd() / ".env"
        
        self._config: Optional[AppConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from multiple sources."""
        # Start with default configuration
        self._config = AppConfig()
        
        # Load from environment variables
        self._load_from_env()
        
        # Load from config file if exists
        if self.config_file.exists():
            self._load_from_file()
        
        # Apply environment-specific overrides
        self._apply_environment_overrides()
        
        env_value = self._config.environment.value if hasattr(self._config.environment, 'value') else str(self._config.environment)
        logger.info(f"Configuration loaded for environment: {env_value}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Environment
        env_name = os.getenv("ENVIRONMENT", "development").lower()
        try:
            self._config.environment = Environment(env_name)
        except ValueError:
            logger.warning(f"Invalid environment '{env_name}', using development")
            self._config.environment = Environment.DEVELOPMENT
        
        # Basic settings
        self._config.debug = os.getenv("DEBUG", "false").lower() == "true"
        self._config.host = os.getenv("HOST", "localhost")
        self._config.port = int(os.getenv("PORT", "8501"))
        
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            self._config.log_level = LogLevel(log_level)
        except ValueError:
            self._config.log_level = LogLevel.INFO
        
        # AWS configuration
        self._config.aws.region = os.getenv("AWS_REGION", "us-east-1")
        self._config.aws.access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self._config.aws.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self._config.aws.session_token = os.getenv("AWS_SESSION_TOKEN")
        
        self._config.aws.s3vector_endpoint = os.getenv("S3VECTOR_ENDPOINT")
        self._config.aws.s3vector_access_key = os.getenv("S3VECTOR_ACCESS_KEY")
        self._config.aws.s3vector_secret_key = os.getenv("S3VECTOR_SECRET_KEY")
        
        self._config.aws.s3_bucket = os.getenv("S3_BUCKET", "s3vector-production-bucket")
        self._config.aws.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.titan-embed-text-v1")
        
        # Marengo configuration
        self._config.marengo.access_method = os.getenv("MARENGO_ACCESS_METHOD", "bedrock")
        self._config.marengo.bedrock_model_id = os.getenv("MARENGO_BEDROCK_MODEL_ID", "twelvelabs.marengo-embed-2-7-v1:0")
        self._config.marengo.bedrock_region = os.getenv("MARENGO_BEDROCK_REGION", "us-east-1")
        self._config.marengo.twelvelabs_api_key = os.getenv("TWELVELABS_API_KEY")
        self._config.marengo.twelvelabs_api_url = os.getenv("TWELVELABS_API_URL", "https://api.twelvelabs.io")
        self._config.marengo.twelvelabs_model_name = os.getenv("TWELVELABS_MODEL_NAME", "marengo2.7")
        self._config.marengo.max_video_duration = int(os.getenv("MAX_VIDEO_DURATION", "3600"))
        self._config.marengo.segment_duration = float(os.getenv("SEGMENT_DURATION", "5.0"))

        # TwelveLabs configuration (legacy compatibility)
        self._config.twelvelabs.api_key = os.getenv("TWELVELABS_API_KEY")
        self._config.twelvelabs.api_url = os.getenv("TWELVELABS_API_URL", "https://api.twelvelabs.io")
        
        # OpenSearch configuration
        self._config.opensearch.endpoint = os.getenv("OPENSEARCH_ENDPOINT")
        self._config.opensearch.username = os.getenv("OPENSEARCH_USERNAME")
        self._config.opensearch.password = os.getenv("OPENSEARCH_PASSWORD")
        
        # Feature flags
        self._config.features.enable_real_aws = os.getenv("ENABLE_REAL_AWS", "false").lower() == "true"
        self._config.features.enable_opensearch_hybrid = os.getenv("ENABLE_OPENSEARCH_HYBRID", "true").lower() == "true"
        self._config.features.enable_video_upload = os.getenv("ENABLE_VIDEO_UPLOAD", "true").lower() == "true"
        
        # Performance settings
        self._config.performance.max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "8"))
        self._config.performance.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self._config.performance.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
    
    def _load_from_file(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if config_data:
                self._merge_config(config_data)
                logger.info(f"Configuration loaded from {self.config_file}")
        
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
    
    def _merge_config(self, config_data: Dict[str, Any]):
        """Merge configuration data into current config."""
        # This is a simplified merge - in production, you'd want recursive merging
        for key, value in config_data.items():
            if hasattr(self._config, key):
                if isinstance(value, dict):
                    # Handle nested configuration objects
                    config_obj = getattr(self._config, key)
                    for sub_key, sub_value in value.items():
                        if hasattr(config_obj, sub_key):
                            setattr(config_obj, sub_key, sub_value)
                else:
                    setattr(self._config, key, value)
    
    def _apply_environment_overrides(self):
        """Apply environment-specific configuration overrides."""
        if self._config.environment == Environment.PRODUCTION:
            # Production overrides
            self._config.debug = False
            self._config.log_level = LogLevel.WARNING
            self._config.security.enable_https = True
            self._config.security.enable_cors = False
            self._config.security.enable_xsrf_protection = True
            
        elif self._config.environment == Environment.DEVELOPMENT:
            # Development overrides
            self._config.debug = True
            self._config.log_level = LogLevel.DEBUG
            self._config.security.enable_https = False
            self._config.security.enable_cors = True
            self._config.security.enable_xsrf_protection = False
            
        elif self._config.environment == Environment.TESTING:
            # Testing overrides
            self._config.debug = True
            self._config.log_level = LogLevel.INFO
            self._config.features.enable_real_aws = False
            self._config.performance.cache_ttl = 60  # Short cache for testing
    
    @property
    def config(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation key."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if hasattr(value, k):
                value = getattr(value, k)
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set a configuration value by dot notation key."""
        keys = key.split('.')
        obj = self._config
        
        for k in keys[:-1]:
            if hasattr(obj, k):
                obj = getattr(obj, k)
            else:
                return False
        
        if hasattr(obj, keys[-1]):
            setattr(obj, keys[-1], value)
            return True
        
        return False
    
    def reload(self):
        """Reload configuration from all sources."""
        self._load_config()
    
    def save_to_file(self, file_path: Optional[str] = None):
        """Save current configuration to file."""
        if not file_path:
            file_path = self.config_file
        
        # Convert config to dictionary for serialization
        config_dict = self._config_to_dict()
        
        try:
            with open(file_path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
            logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        # This is a simplified conversion - in production, you'd want proper serialization
        return {
            "environment": self._config.environment.value,
            "debug": self._config.debug,
            "log_level": self._config.log_level.value,
            "host": self._config.host,
            "port": self._config.port
        }
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get a feature flag value."""
        return getattr(self._config.features, flag_name, False)
    
    def set_feature_flag(self, flag_name: str, value: bool):
        """Set a feature flag value."""
        if hasattr(self._config.features, flag_name):
            setattr(self._config.features, flag_name, value)
            logger.info(f"Feature flag '{flag_name}' set to {value}")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            "environment": self._config.environment.value,
            "debug": self._config.debug,
            "log_level": self._config.log_level.value,
            "features_enabled": {
                name: getattr(self._config.features, name)
                for name in dir(self._config.features)
                if not name.startswith('_')
            }
        }


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return get_config_manager().config


def get_feature_flag(flag_name: str) -> bool:
    """Get a feature flag value."""
    return get_config_manager().get_feature_flag(flag_name)


def set_feature_flag(flag_name: str, value: bool):
    """Set a feature flag value."""
    get_config_manager().set_feature_flag(flag_name, value)


# Example usage
if __name__ == "__main__":
    config = get_config()
    print(f"Environment: {config.environment.value}")
    print(f"Debug: {config.debug}")
    print(f"AWS Region: {config.aws.region}")
    print(f"Real AWS Enabled: {get_feature_flag('enable_real_aws')}")
