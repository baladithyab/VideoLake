#!/usr/bin/env python3
"""
Configuration Adapter

Bridges the old demo configuration system with the new unified configuration management.
Provides backward compatibility while enabling new configuration features.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import unified configuration system
try:
    from src.config.app_config import get_config, get_feature_flag, AppConfig, ConfigManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Import original demo config for fallback
from frontend.components.demo_config import DemoConfig as OriginalDemoConfig, DemoUtils as OriginalDemoUtils


class EnhancedDemoConfig:
    """Enhanced demo configuration using unified config system."""
    
    def __init__(self):
        """Initialize enhanced configuration."""
        if CONFIG_AVAILABLE:
            self.config_manager = ConfigManager()
            self.app_config = self.config_manager.config
            self._use_unified_config = True
        else:
            self.original_config = OriginalDemoConfig()
            self._use_unified_config = False
    
    @property
    def app_title(self) -> str:
        """Get application title."""
        if self._use_unified_config:
            return self.app_config.ui.app_title
        return self.original_config.app_title
    
    @property
    def app_icon(self) -> str:
        """Get application icon."""
        if self._use_unified_config:
            return self.app_config.ui.app_icon
        return self.original_config.app_icon
    
    @property
    def layout(self) -> str:
        """Get page layout."""
        if self._use_unified_config:
            return self.app_config.ui.page_layout
        return self.original_config.layout
    
    @property
    def default_vector_types(self) -> List[str]:
        """Get default vector types."""
        if self._use_unified_config:
            return self.app_config.ui.default_vector_types
        return self.original_config.default_vector_types
    
    @property
    def default_storage_patterns(self) -> List[str]:
        """Get default storage patterns."""
        if self._use_unified_config:
            return self.app_config.ui.default_storage_patterns
        return self.original_config.default_storage_patterns
    
    @property
    def default_segment_duration(self) -> float:
        """Get default segment duration."""
        if self._use_unified_config:
            return self.app_config.ui.default_segment_duration
        return self.original_config.default_segment_duration
    
    @property
    def default_processing_mode(self) -> str:
        """Get default processing mode."""
        if self._use_unified_config:
            return self.app_config.ui.default_processing_mode
        return self.original_config.default_processing_mode
    
    @property
    def enable_real_aws(self) -> bool:
        """Get real AWS enablement status."""
        if self._use_unified_config:
            return self.app_config.features.enable_real_aws
        return self.original_config.enable_real_aws
    
    @property
    def enable_cost_estimation(self) -> bool:
        """Get cost estimation enablement status."""
        if self._use_unified_config:
            return self.app_config.features.enable_cost_estimation
        return self.original_config.enable_cost_estimation
    
    @property
    def workflow_sections(self) -> List[str]:
        """Get workflow sections."""
        if self._use_unified_config:
            return self.app_config.ui.workflow_sections
        return self.original_config.workflow_sections

    @property
    def section_titles(self) -> Dict[str, str]:
        """Get section titles."""
        if self._use_unified_config:
            # Map workflow sections to titles
            return {
                "upload": "🔄 Upload & Processing",
                "query": "🔍 Query & Search",
                "results": "📊 Results & Playback",
                "visualization": "📈 Embedding Visualization",
                "analytics": "📋 Analytics & Management"
            }
        return getattr(self.original_config, 'section_titles', {})

    @property
    def section_descriptions(self) -> Dict[str, str]:
        """Get section descriptions."""
        if self._use_unified_config:
            return {
                "upload": "Configure and process videos with multi-vector embeddings",
                "query": "Search videos using intelligent query routing and modality selection",
                "results": "Explore search results with interactive video playback",
                "visualization": "Visualize embedding spaces and similarity relationships",
                "analytics": "Monitor performance, costs, and system analytics"
            }
        return getattr(self.original_config, 'section_descriptions', {})
    
    @property
    def max_concurrent_jobs(self) -> int:
        """Get maximum concurrent jobs."""
        if self._use_unified_config:
            return self.app_config.performance.max_concurrent_jobs
        return getattr(self.original_config, 'max_concurrent_jobs', 8)
    
    @property
    def request_timeout(self) -> int:
        """Get request timeout."""
        if self._use_unified_config:
            return self.app_config.performance.request_timeout
        return getattr(self.original_config, 'service_timeout', 30)
    
    def get_feature_flag(self, flag_name: str) -> bool:
        """Get feature flag value."""
        if self._use_unified_config:
            return getattr(self.app_config.features, flag_name, False)
        
        # Fallback to environment variables or defaults
        env_var = f"ENABLE_{flag_name.upper()}"
        return os.getenv(env_var, "false").lower() == "true"
    
    def set_feature_flag(self, flag_name: str, value: bool):
        """Set feature flag value."""
        if self._use_unified_config:
            if hasattr(self.app_config.features, flag_name):
                setattr(self.app_config.features, flag_name, value)
    
    def get_aws_config(self) -> Dict[str, Any]:
        """Get AWS configuration."""
        if self._use_unified_config:
            return {
                'region': self.app_config.aws.region,
                'access_key_id': self.app_config.aws.access_key_id,
                'secret_access_key': self.app_config.aws.secret_access_key,
                's3_bucket': self.app_config.aws.s3_bucket,
                's3_prefix': self.app_config.aws.s3_prefix,
                'bedrock_model_id': self.app_config.aws.bedrock_model_id,
                's3vector_endpoint': self.app_config.aws.s3vector_endpoint,
                's3vector_access_key': self.app_config.aws.s3vector_access_key,
                's3vector_secret_key': self.app_config.aws.s3vector_secret_key
            }
        
        # Fallback to environment variables
        return {
            'region': os.getenv('AWS_REGION', 'us-east-1'),
            'access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
            's3_bucket': os.getenv('S3_BUCKET', 's3vector-demo-bucket'),
            's3_prefix': os.getenv('S3_PREFIX', 'demo/'),
            'bedrock_model_id': os.getenv('BEDROCK_MODEL_ID', 'amazon.titan-embed-text-v1'),
            's3vector_endpoint': os.getenv('S3VECTOR_ENDPOINT'),
            's3vector_access_key': os.getenv('S3VECTOR_ACCESS_KEY'),
            's3vector_secret_key': os.getenv('S3VECTOR_SECRET_KEY')
        }
    
    def get_marengo_config(self) -> Dict[str, Any]:
        """Get Marengo 2.7 configuration with access method distinction."""
        if self._use_unified_config:
            marengo = self.app_config.marengo
            return {
                'access_method': marengo.access_method,
                'bedrock_model_id': marengo.bedrock_model_id,
                'bedrock_region': marengo.bedrock_region,
                'twelvelabs_api_key': marengo.twelvelabs_api_key,
                'twelvelabs_api_url': marengo.twelvelabs_api_url,
                'twelvelabs_model_name': marengo.twelvelabs_model_name,
                'max_video_duration': marengo.max_video_duration,
                'segment_duration': marengo.segment_duration,
                'supported_vector_types': marengo.supported_vector_types,
                'model_identifier': marengo.get_model_identifier(),
                'is_bedrock_access': marengo.is_bedrock_access(),
                'is_twelvelabs_api_access': marengo.is_twelvelabs_api_access(),
                'configuration_valid': marengo.validate_configuration()
            }

        # Fallback to environment variables
        access_method = os.getenv('MARENGO_ACCESS_METHOD', 'bedrock')
        return {
            'access_method': access_method,
            'bedrock_model_id': os.getenv('MARENGO_BEDROCK_MODEL_ID', 'twelvelabs.marengo-embed-2-7-v1:0'),
            'bedrock_region': os.getenv('MARENGO_BEDROCK_REGION', 'us-east-1'),
            'twelvelabs_api_key': os.getenv('TWELVELABS_API_KEY'),
            'twelvelabs_api_url': os.getenv('TWELVELABS_API_URL', 'https://api.twelvelabs.io'),
            'twelvelabs_model_name': os.getenv('TWELVELABS_MODEL_NAME', 'marengo2.7'),
            'max_video_duration': int(os.getenv('MAX_VIDEO_DURATION', '3600')),
            'segment_duration': float(os.getenv('SEGMENT_DURATION', '5.0')),
            'supported_vector_types': ['visual-text', 'visual-image', 'audio'],
            'model_identifier': os.getenv('MARENGO_BEDROCK_MODEL_ID', 'twelvelabs.marengo-embed-2-7-v1:0') if access_method == 'bedrock' else os.getenv('TWELVELABS_MODEL_NAME', 'marengo2.7'),
            'is_bedrock_access': access_method == 'bedrock',
            'is_twelvelabs_api_access': access_method == 'twelvelabs_api',
            'configuration_valid': True  # Basic validation
        }

    def get_twelvelabs_config(self) -> Dict[str, Any]:
        """Get TwelveLabs configuration (legacy compatibility)."""
        if self._use_unified_config:
            return {
                'api_key': self.app_config.twelvelabs.api_key,
                'api_url': self.app_config.twelvelabs.api_url,
                'model_name': self.app_config.twelvelabs.model_name,
                'max_video_duration': self.app_config.twelvelabs.max_video_duration,
                'segment_duration': self.app_config.twelvelabs.segment_duration
            }

        # Fallback to environment variables
        return {
            'api_key': os.getenv('TWELVELABS_API_KEY'),
            'api_url': os.getenv('TWELVELABS_API_URL', 'https://api.twelvelabs.io'),
            'model_name': os.getenv('TWELVELABS_MODEL_NAME', 'marengo2.7'),
            'max_video_duration': int(os.getenv('MAX_VIDEO_DURATION', '3600')),
            'segment_duration': float(os.getenv('SEGMENT_DURATION', '5.0'))
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        if self._use_unified_config:
            return self.config_manager.get_environment_info()
        
        return {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'debug': os.getenv('DEBUG', 'false').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'unified_config_available': CONFIG_AVAILABLE
        }
    
    def reload_config(self):
        """Reload configuration from all sources."""
        if self._use_unified_config:
            self.config_manager.reload()
        else:
            # Reinitialize original config
            self.original_config = OriginalDemoConfig()


class EnhancedDemoUtils:
    """Enhanced demo utilities with configuration integration."""
    
    def __init__(self, config: Optional[EnhancedDemoConfig] = None):
        """Initialize enhanced utilities."""
        self.config = config or EnhancedDemoConfig()
        self.original_utils = OriginalDemoUtils()
    
    def validate_s3_uri(self, uri: str) -> bool:
        """Validate S3 URI format."""
        return self.original_utils.validate_s3_uri(uri)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        return self.original_utils.format_duration(seconds)
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        return self.original_utils.format_file_size(size_bytes)
    
    def get_workflow_progress(self, current_section: str, sections: List[str]) -> float:
        """Get workflow progress percentage."""
        return self.original_utils.get_workflow_progress(current_section, sections)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return self.config.get_feature_flag(feature_name)
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """Get performance-related settings."""
        return {
            'max_concurrent_jobs': self.config.max_concurrent_jobs,
            'request_timeout': self.config.request_timeout,
            'enable_caching': self.config.get_feature_flag('enable_caching'),
            'enable_compression': self.config.get_feature_flag('enable_compression')
        }
    
    def get_security_settings(self) -> Dict[str, Any]:
        """Get security-related settings."""
        if self.config._use_unified_config:
            security = self.config.app_config.security
            return {
                'enable_https': security.enable_https,
                'max_upload_size': security.max_upload_size,
                'allowed_file_types': security.allowed_file_types,
                'enable_cors': security.enable_cors,
                'session_timeout': security.session_timeout
            }

        return {
            'enable_https': os.getenv('ENABLE_HTTPS', 'false').lower() == 'true',
            'max_upload_size': int(os.getenv('MAX_UPLOAD_SIZE', '500')),
            'allowed_file_types': ['.mp4', '.avi', '.mov', '.mkv', '.webm'],
            'enable_cors': os.getenv('ENABLE_CORS', 'true').lower() == 'true',
            'session_timeout': int(os.getenv('SESSION_TIMEOUT', '3600'))
        }

    def check_prerequisites(self, section: str, session_state) -> Dict[str, Any]:
        """Check prerequisites for a workflow section."""
        # Use original utils if available, otherwise provide basic implementation
        if hasattr(self.original_utils, 'check_prerequisites'):
            return self.original_utils.check_prerequisites(section, session_state)

        # Basic prerequisite checking
        prerequisites = {
            "upload": [],
            "query": ["processed_videos"],
            "results": ["search_results"],
            "visualization": ["search_results"],
            "analytics": []
        }

        required = prerequisites.get(section, [])
        met = all(hasattr(session_state, req) and getattr(session_state, req) for req in required)

        return {
            "met": met,
            "required_sections": required,
            "missing": [req for req in required if not (hasattr(session_state, req) and getattr(session_state, req))]
        }

    def get_previous_section(self, current_section: str, sections: List[str]) -> str:
        """Get the previous section in the workflow."""
        if hasattr(self.original_utils, 'get_previous_section'):
            return self.original_utils.get_previous_section(current_section, sections)

        try:
            current_index = sections.index(current_section)
            if current_index > 0:
                return sections[current_index - 1]
        except (ValueError, IndexError):
            pass

        return sections[0] if sections else current_section

    def get_next_section(self, current_section: str, sections: List[str]) -> str:
        """Get the next section in the workflow."""
        if hasattr(self.original_utils, 'get_next_section'):
            return self.original_utils.get_next_section(current_section, sections)

        try:
            current_index = sections.index(current_section)
            if current_index < len(sections) - 1:
                return sections[current_index + 1]
        except (ValueError, IndexError):
            pass

        return sections[-1] if sections else current_section


# Global instances for backward compatibility
_enhanced_config: Optional[EnhancedDemoConfig] = None
_enhanced_utils: Optional[EnhancedDemoUtils] = None


def get_enhanced_config() -> EnhancedDemoConfig:
    """Get the global enhanced configuration instance."""
    global _enhanced_config
    
    if _enhanced_config is None:
        _enhanced_config = EnhancedDemoConfig()
    
    return _enhanced_config


def get_enhanced_utils() -> EnhancedDemoUtils:
    """Get the global enhanced utilities instance."""
    global _enhanced_utils
    
    if _enhanced_utils is None:
        _enhanced_utils = EnhancedDemoUtils(get_enhanced_config())
    
    return _enhanced_utils


# Backward compatibility aliases
DemoConfig = EnhancedDemoConfig
DemoUtils = EnhancedDemoUtils


# Example usage
if __name__ == "__main__":
    config = get_enhanced_config()
    utils = get_enhanced_utils()
    
    print(f"App Title: {config.app_title}")
    print(f"Environment: {config.get_environment_info()}")
    print(f"Real AWS Enabled: {config.enable_real_aws}")
    print(f"Feature Flags Available: {CONFIG_AVAILABLE}")
    print(f"Performance Settings: {utils.get_performance_settings()}")
