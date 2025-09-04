#!/usr/bin/env python3
"""
Unified Configuration Manager

This module consolidates and replaces the following configuration systems:
- src/config.py (core config)
- src/config/app_config.py (application config)
- frontend/components/config_adapter.py (467-line bridge adapter)
- frontend/components/demo_config.py (demo-specific)
- Various YAML configuration files

Provides a single, hierarchical configuration system with environment separation.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logging_config import get_logger
from src.exceptions import ConfigurationError

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
class AWSConfiguration:
    """Unified AWS service configuration."""
    # Core AWS settings
    region: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    
    # S3 and S3Vector settings
    s3_bucket: str = "s3vector-demo-bucket"
    s3_prefix: str = "demo/"
    s3_vectors_bucket: Optional[str] = None
    s3vector_endpoint: Optional[str] = None
    s3vector_access_key: Optional[str] = None
    s3vector_secret_key: Optional[str] = None
    
    # Bedrock settings
    bedrock_models: Dict[str, str] = field(default_factory=lambda: {
        'text_embedding': 'amazon.titan-embed-text-v2:0',
        'multimodal_embedding': 'amazon.titan-embed-image-v1',
        'video_embedding': 'twelvelabs.marengo-embed-2-7-v1:0'
    })
    bedrock_max_tokens: int = 8192
    
    # Service limits
    max_retries: int = 3
    timeout_seconds: int = 60
    
    def validate(self) -> bool:
        """Validate AWS configuration."""
        if not self.region:
            return False
        if not self.s3_bucket:
            return False
        return True


@dataclass
class VideoProcessingConfiguration:
    """Unified video processing configuration consolidating TwelveLabs/Marengo settings."""
    # Access method selection
    access_method: str = "bedrock"  # "bedrock" or "twelvelabs_api"
    
    # Bedrock access configuration
    bedrock_model_id: str = "twelvelabs.marengo-embed-2-7-v1:0"
    bedrock_region: str = "us-east-1"
    bedrock_supported_regions: List[str] = field(default_factory=lambda: [
        "us-east-1", "eu-west-1", "ap-northeast-2"
    ])
    
    # TwelveLabs API access configuration
    twelvelabs_api_key: Optional[str] = None
    twelvelabs_api_url: str = "https://api.twelvelabs.io"
    twelvelabs_model_name: str = "marengo2.7"
    
    # Processing parameters
    max_video_duration_sec: int = 3600
    segment_duration_sec: float = 5.0
    supported_vector_types: List[str] = field(default_factory=lambda: [
        "visual-text", "visual-image", "audio"
    ])
    
    # Processing modes
    default_processing_mode: str = "parallel"
    max_concurrent_jobs: int = 8
    batch_size_video: int = 10
    poll_interval_sec: int = 30
    
    # Cost tracking
    enable_cost_tracking: bool = True
    cost_per_minute_usd: float = 0.05
    
    def get_model_identifier(self) -> str:
        """Get the appropriate model identifier based on access method."""
        return self.bedrock_model_id if self.access_method == "bedrock" else self.twelvelabs_model_name
    
    def is_bedrock_access(self) -> bool:
        """Check if using Bedrock access method."""
        return self.access_method == "bedrock"
    
    def is_twelvelabs_api_access(self) -> bool:
        """Check if using TwelveLabs API access method."""
        return self.access_method == "twelvelabs_api"
    
    def validate(self) -> bool:
        """Validate video processing configuration."""
        if self.access_method == "bedrock":
            return self.bedrock_region in self.bedrock_supported_regions
        elif self.access_method == "twelvelabs_api":
            return self.twelvelabs_api_key is not None
        return False


@dataclass
class StorageConfiguration:
    """Storage and indexing configuration."""
    # OpenSearch configuration
    opensearch_endpoint: Optional[str] = None
    opensearch_username: Optional[str] = None
    opensearch_password: Optional[str] = None
    opensearch_index_prefix: str = "s3vector-demo"
    opensearch_max_results: int = 100
    
    # Storage patterns
    default_storage_patterns: List[str] = field(default_factory=lambda: [
        "direct_s3vector", "opensearch_s3vector_hybrid"
    ])
    
    # Vector storage settings
    default_vector_types: List[str] = field(default_factory=lambda: [
        "visual-text", "visual-image", "audio"
    ])
    vector_dimensions: int = 1024
    distance_metric: str = "cosine"
    
    # Batch processing
    batch_size_vectors: int = 1000
    batch_size_text: int = 100


@dataclass
class FeatureConfiguration:
    """Feature flags and capabilities."""
    # Core features
    enable_real_aws: bool = False
    enable_video_upload: bool = True
    enable_cost_estimation: bool = True
    enable_demo_data: bool = True
    
    # Advanced features
    enable_opensearch_hybrid: bool = True
    enable_performance_monitoring: bool = True
    enable_error_dashboard: bool = True
    enable_advanced_visualization: bool = True
    enable_multi_vector_processing: bool = True
    enable_query_auto_detection: bool = True
    enable_segment_navigation: bool = True
    
    # Performance features
    enable_caching: bool = True
    enable_compression: bool = True


@dataclass
class UIConfiguration:
    """User interface configuration."""
    # Application settings
    app_title: str = "S3Vector Unified Demo"
    app_icon: str = "🎬"
    page_layout: str = "wide"
    sidebar_state: str = "expanded"
    theme: str = "light"
    
    # Workflow sections
    workflow_sections: List[str] = field(default_factory=lambda: [
        "upload", "query", "results", "visualization", "analytics", "resources"
    ])
    
    section_titles: Dict[str, str] = field(default_factory=lambda: {
        "upload": "🎬 Upload & Processing",
        "query": "🔍 Query & Search", 
        "results": "🎯 Results & Playback",
        "visualization": "📊 Embedding Visualization",
        "analytics": "⚙️ Analytics & Management",
        "resources": "🔧 Resource Management"
    })
    
    section_descriptions: Dict[str, str] = field(default_factory=lambda: {
        "upload": "Select videos and configure multi-vector processing",
        "query": "Intelligent semantic search with storage pattern comparison", 
        "results": "Interactive video player with segment overlay and similarity scores",
        "visualization": "Explore embedding space with dimensionality reduction",
        "analytics": "Performance monitoring, cost tracking, and system management",
        "resources": "Manage AWS resources, resume work, and cleanup"
    })
    
    # UI defaults
    default_num_results: int = 10
    default_similarity_threshold: float = 0.7
    max_results: int = 50
    sidebar_width: int = 300


@dataclass
class PerformanceConfiguration:
    """Performance and system settings."""
    # Concurrency limits
    max_concurrent_jobs: int = 8
    request_timeout_sec: int = 30
    max_retries: int = 3
    
    # Memory and caching
    cache_ttl_sec: int = 3600
    max_memory_usage_mb: int = 4096
    enable_caching: bool = True
    enable_compression: bool = True
    
    # Polling and intervals
    poll_interval_sec: int = 30
    cleanup_interval_sec: int = 3600


@dataclass
class SecurityConfiguration:
    """Security and compliance settings."""
    # HTTPS and encryption
    enable_https: bool = False  # Set to true in production
    enable_tls: bool = False
    
    # Session management
    session_timeout_sec: int = 3600
    enable_session_encryption: bool = False
    
    # File upload restrictions
    max_upload_size_mb: int = 500
    allowed_file_types: List[str] = field(default_factory=lambda: [
        ".mp4", ".avi", ".mov", ".mkv", ".webm"
    ])
    
    # API security
    enable_cors: bool = True  # Set to false in production
    enable_xsrf_protection: bool = False  # Set to true in production
    enable_rate_limiting: bool = False


@dataclass
class UnifiedConfiguration:
    """Main unified configuration containing all subsystem configurations."""
    # Environment settings
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    host: str = "localhost"
    port: int = 8501
    
    # Configuration sections
    aws: AWSConfiguration = field(default_factory=AWSConfiguration)
    video_processing: VideoProcessingConfiguration = field(default_factory=VideoProcessingConfiguration)
    storage: StorageConfiguration = field(default_factory=StorageConfiguration)
    features: FeatureConfiguration = field(default_factory=FeatureConfiguration)
    ui: UIConfiguration = field(default_factory=UIConfiguration)
    performance: PerformanceConfiguration = field(default_factory=PerformanceConfiguration)
    security: SecurityConfiguration = field(default_factory=SecurityConfiguration)
    
    def validate(self) -> bool:
        """Validate entire configuration."""
        return (
            self.aws.validate() and 
            self.video_processing.validate()
        )


class UnifiedConfigManager:
    """
    Unified configuration manager that replaces all previous configuration systems.
    
    This manager consolidates:
    - Environment-based configuration loading
    - YAML file parsing and merging  
    - Environment variable overrides
    - Feature flag management
    - Backward compatibility interfaces
    """
    
    def __init__(self, config_dir: Optional[str] = None, config_file: Optional[str] = None):
        """Initialize unified configuration manager."""
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.config_file = Path(config_file) if config_file else self.config_dir / "config.yaml"
        self.env_file = Path.cwd() / ".env"
        
        # Initialize with default configuration first
        self._config: UnifiedConfiguration = UnifiedConfiguration()
        self._load_configuration()
        
        logger.info(f"Unified configuration manager initialized for {self._config.environment.value}")
    
    def _load_configuration(self):
        """Load configuration from all sources in priority order."""
        # Step 1: Start with defaults (already initialized)
        # Reset to defaults
        self._config = UnifiedConfiguration()
        
        # Step 2: Load base YAML configuration
        if self.config_file.exists():
            self._load_from_yaml()
        
        # Step 3: Load environment-specific YAML overrides
        self._load_environment_specific_yaml()
        
        # Step 4: Apply environment variable overrides
        self._apply_environment_variables()
        
        # Step 5: Apply environment-specific defaults
        self._apply_environment_defaults()
        
        # Step 6: Validate final configuration
        if not self._config.validate():
            logger.warning("Configuration validation failed, proceeding with defaults")
    
    def _load_from_yaml(self):
        """Load base YAML configuration file."""
        try:
            with open(self.config_file, 'r') as f:
                yaml_data = yaml.safe_load(f)
            
            if yaml_data:
                self._merge_yaml_data(yaml_data)
                logger.info(f"Loaded base configuration from {self.config_file}")
        
        except Exception as e:
            logger.warning(f"Failed to load YAML config {self.config_file}: {e}")
    
    def _load_environment_specific_yaml(self):
        """Load environment-specific YAML overrides."""
        env_name = self._config.environment.value
        env_config_file = self.config_dir / f"config.{env_name}.yaml"
        
        if env_config_file.exists():
            try:
                with open(env_config_file, 'r') as f:
                    env_yaml_data = yaml.safe_load(f)
                
                if env_yaml_data:
                    self._merge_yaml_data(env_yaml_data)
                    logger.info(f"Loaded {env_name} environment overrides from {env_config_file}")
            
            except Exception as e:
                logger.warning(f"Failed to load environment config {env_config_file}: {e}")
    
    def _merge_yaml_data(self, yaml_data: Dict[str, Any]):
        """Merge YAML data into configuration."""
        # Environment level
        if 'environment' in yaml_data:
            try:
                self._config.environment = Environment(yaml_data['environment'])
            except ValueError:
                logger.warning(f"Invalid environment: {yaml_data['environment']}")
        
        if 'debug' in yaml_data:
            self._config.debug = yaml_data['debug']
        
        if 'log_level' in yaml_data:
            try:
                self._config.log_level = LogLevel(yaml_data['log_level'])
            except ValueError:
                logger.warning(f"Invalid log level: {yaml_data['log_level']}")
        
        # AWS configuration
        if 'aws' in yaml_data:
            self._merge_into_dataclass(self._config.aws, yaml_data['aws'])
        
        # Video processing (consolidates marengo and twelvelabs)
        if 'video_processing' in yaml_data:
            self._merge_into_dataclass(self._config.video_processing, yaml_data['video_processing'])
        elif 'marengo' in yaml_data:
            # Backward compatibility with marengo section
            self._merge_into_dataclass(self._config.video_processing, yaml_data['marengo'])
        elif 'twelvelabs' in yaml_data:
            # Backward compatibility with twelvelabs section
            legacy_data = yaml_data['twelvelabs']
            self._config.video_processing.access_method = "twelvelabs_api"
            if 'api_key' in legacy_data:
                self._config.video_processing.twelvelabs_api_key = legacy_data['api_key']
            if 'api_url' in legacy_data:
                self._config.video_processing.twelvelabs_api_url = legacy_data['api_url']
        
        # Storage (consolidates opensearch settings)
        if 'storage' in yaml_data:
            self._merge_into_dataclass(self._config.storage, yaml_data['storage'])
        elif 'opensearch' in yaml_data:
            # Backward compatibility
            opensearch_data = yaml_data['opensearch']
            if 'endpoint' in opensearch_data:
                self._config.storage.opensearch_endpoint = opensearch_data['endpoint']
            if 'index_prefix' in opensearch_data:
                self._config.storage.opensearch_index_prefix = opensearch_data['index_prefix']
        
        # Feature flags
        if 'features' in yaml_data:
            self._merge_into_dataclass(self._config.features, yaml_data['features'])
        
        # UI configuration
        if 'ui' in yaml_data:
            self._merge_into_dataclass(self._config.ui, yaml_data['ui'])
        
        # Performance settings
        if 'performance' in yaml_data:
            self._merge_into_dataclass(self._config.performance, yaml_data['performance'])
        
        # Security settings  
        if 'security' in yaml_data:
            self._merge_into_dataclass(self._config.security, yaml_data['security'])
    
    def _merge_into_dataclass(self, target_obj: Any, source_data: Dict[str, Any]):
        """Merge dictionary data into a dataclass instance."""
        for key, value in source_data.items():
            if hasattr(target_obj, key):
                setattr(target_obj, key, value)
    
    def _apply_environment_variables(self):
        """Apply environment variable overrides."""
        # Basic settings
        env_name = os.getenv("ENVIRONMENT", self._config.environment.value).lower()
        try:
            self._config.environment = Environment(env_name)
        except ValueError:
            pass
        
        self._config.debug = os.getenv("DEBUG", str(self._config.debug)).lower() == "true"
        self._config.host = os.getenv("HOST", self._config.host)
        self._config.port = int(os.getenv("PORT", str(self._config.port)))
        
        log_level = os.getenv("LOG_LEVEL", self._config.log_level.value)
        try:
            self._config.log_level = LogLevel(log_level)
        except ValueError:
            pass
        
        # AWS settings
        aws = self._config.aws
        aws.region = os.getenv("AWS_REGION", aws.region)
        aws.access_key_id = os.getenv("AWS_ACCESS_KEY_ID", aws.access_key_id)
        aws.secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", aws.secret_access_key)
        aws.session_token = os.getenv("AWS_SESSION_TOKEN", aws.session_token)
        aws.s3_bucket = os.getenv("S3_BUCKET", aws.s3_bucket)
        aws.s3_vectors_bucket = os.getenv("S3_VECTORS_BUCKET", aws.s3_vectors_bucket)
        
        # Video processing settings
        video = self._config.video_processing
        video.access_method = os.getenv("MARENGO_ACCESS_METHOD", video.access_method)
        video.bedrock_model_id = os.getenv("MARENGO_BEDROCK_MODEL_ID", video.bedrock_model_id)
        video.bedrock_region = os.getenv("MARENGO_BEDROCK_REGION", video.bedrock_region)
        video.twelvelabs_api_key = os.getenv("TWELVELABS_API_KEY", video.twelvelabs_api_key)
        video.twelvelabs_api_url = os.getenv("TWELVELABS_API_URL", video.twelvelabs_api_url)
        
        # Feature flags
        features = self._config.features
        features.enable_real_aws = os.getenv("ENABLE_REAL_AWS", str(features.enable_real_aws)).lower() == "true"
        features.enable_opensearch_hybrid = os.getenv("ENABLE_OPENSEARCH_HYBRID", str(features.enable_opensearch_hybrid)).lower() == "true"
        features.enable_cost_estimation = os.getenv("ENABLE_COST_ESTIMATION", str(features.enable_cost_estimation)).lower() == "true"
        
        # Storage settings
        storage = self._config.storage
        storage.opensearch_endpoint = os.getenv("OPENSEARCH_ENDPOINT", storage.opensearch_endpoint)
        storage.opensearch_username = os.getenv("OPENSEARCH_USERNAME", storage.opensearch_username)
        storage.opensearch_password = os.getenv("OPENSEARCH_PASSWORD", storage.opensearch_password)
    
    def _apply_environment_defaults(self):
        """Apply environment-specific default overrides."""
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
            
        elif self._config.environment == Environment.TESTING:
            # Testing overrides
            self._config.debug = True
            self._config.log_level = LogLevel.INFO
            self._config.features.enable_real_aws = False
            self._config.performance.cache_ttl_sec = 60
    
    @property
    def config(self) -> UnifiedConfiguration:
        """Get the unified configuration."""
        return self._config
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation path.
        
        Args:
            key_path: Dot-separated path like 'aws.region' or 'features.enable_real_aws'
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if hasattr(value, key):
                value = getattr(value, key)
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Set configuration value using dot notation path.
        
        Args:
            key_path: Dot-separated path
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        keys = key_path.split('.')
        obj = self._config
        
        # Navigate to parent object
        for key in keys[:-1]:
            if hasattr(obj, key):
                obj = getattr(obj, key)
            else:
                return False
        
        # Set the final value
        final_key = keys[-1]
        if hasattr(obj, final_key):
            setattr(obj, final_key, value)
            return True
        
        return False
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get feature flag value."""
        return getattr(self._config.features, flag_name, False)
    
    def set_feature_flag(self, flag_name: str, value: bool) -> bool:
        """Set feature flag value."""
        if hasattr(self._config.features, flag_name):
            setattr(self._config.features, flag_name, value)
            logger.info(f"Feature flag '{flag_name}' set to {value}")
            return True
        return False
    
    def reload(self):
        """Reload configuration from all sources."""
        logger.info("Reloading unified configuration")
        self._load_configuration()
    
    def save_to_yaml(self, output_path: Optional[str] = None) -> bool:
        """
        Save current configuration to YAML file.
        
        Args:
            output_path: Output file path (defaults to config file)
            
        Returns:
            True if successful
        """
        output_file = Path(output_path) if output_path else self.config_file
        
        try:
            # Convert config to dictionary
            config_dict = self._config_to_dict()
            
            with open(output_file, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for YAML serialization."""
        return {
            'environment': self._config.environment.value,
            'debug': self._config.debug,
            'log_level': self._config.log_level.value,
            'host': self._config.host,
            'port': self._config.port,
            'aws': self._dataclass_to_dict(self._config.aws),
            'video_processing': self._dataclass_to_dict(self._config.video_processing),
            'storage': self._dataclass_to_dict(self._config.storage),
            'features': self._dataclass_to_dict(self._config.features),
            'ui': self._dataclass_to_dict(self._config.ui),
            'performance': self._dataclass_to_dict(self._config.performance),
            'security': self._dataclass_to_dict(self._config.security)
        }
    
    def _dataclass_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        result = {}
        for key, value in obj.__dict__.items():
            if value is not None:  # Only include non-None values
                result[key] = value
        return result
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information summary."""
        return {
            'environment': self._config.environment.value,
            'debug': self._config.debug,
            'log_level': self._config.log_level.value,
            'aws_region': self._config.aws.region,
            'video_access_method': self._config.video_processing.access_method,
            'features_enabled': {
                name: getattr(self._config.features, name)
                for name in dir(self._config.features)
                if not name.startswith('_')
            }
        }
    
    # Backward compatibility methods
    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration (backward compatibility)."""
        aws = self._config.aws
        return {
            'region': aws.region,
            'access_key_id': aws.access_key_id,
            'secret_access_key': aws.secret_access_key,
            's3_bucket': aws.s3_bucket,
            's3_prefix': aws.s3_prefix,
            'bedrock_model_id': aws.bedrock_models.get('text_embedding'),
            's3vector_endpoint': aws.s3vector_endpoint,
            's3vector_access_key': aws.s3vector_access_key,
            's3vector_secret_key': aws.s3vector_secret_key
        }
    
    def get_marengo_config(self) -> Dict[str, Any]:
        """Get video processing configuration (backward compatibility)."""
        video = self._config.video_processing
        return {
            'access_method': video.access_method,
            'bedrock_model_id': video.bedrock_model_id,
            'bedrock_region': video.bedrock_region,
            'twelvelabs_api_key': video.twelvelabs_api_key,
            'twelvelabs_api_url': video.twelvelabs_api_url,
            'twelvelabs_model_name': video.twelvelabs_model_name,
            'max_video_duration': video.max_video_duration_sec,
            'segment_duration': video.segment_duration_sec,
            'supported_vector_types': video.supported_vector_types,
            'model_identifier': video.get_model_identifier(),
            'is_bedrock_access': video.is_bedrock_access(),
            'is_twelvelabs_api_access': video.is_twelvelabs_api_access(),
            'configuration_valid': video.validate()
        }


# Global instance
_unified_config_manager: Optional[UnifiedConfigManager] = None


def get_unified_config_manager() -> UnifiedConfigManager:
    """Get the global unified configuration manager instance."""
    global _unified_config_manager
    
    if _unified_config_manager is None:
        _unified_config_manager = UnifiedConfigManager()
    
    return _unified_config_manager


def get_config() -> UnifiedConfiguration:
    """Get the unified configuration."""
    return get_unified_config_manager().config


def get_feature_flag(flag_name: str) -> bool:
    """Get feature flag value."""
    return get_unified_config_manager().get_feature_flag(flag_name)


def set_feature_flag(flag_name: str, value: bool) -> bool:
    """Set feature flag value."""
    return get_unified_config_manager().set_feature_flag(flag_name, value)


# Example usage
if __name__ == "__main__":
    config_manager = UnifiedConfigManager()
    config = config_manager.config
    
    print(f"Environment: {config.environment.value}")
    print(f"AWS Region: {config.aws.region}")
    print(f"Video Access Method: {config.video_processing.access_method}")
    print(f"Real AWS Enabled: {config.features.enable_real_aws}")
    print(f"App Title: {config.ui.app_title}")