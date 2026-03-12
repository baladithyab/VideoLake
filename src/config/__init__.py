#!/usr/bin/env python3
"""
Configuration Package

Unified configuration management system for the S3Vector demo.
"""

from .unified_config_manager import (
    UnifiedConfiguration,
    UnifiedConfigManager,
    get_unified_config_manager,
    get_config,
    get_feature_flag,
    set_feature_flag,
    Environment,
    LogLevel,
    AWSConfiguration,
    VideoProcessingConfiguration,
    StorageConfiguration,
    FeatureConfiguration,
    UIConfiguration,
    PerformanceConfiguration,
    SecurityConfiguration
)

# Backward compatibility aliases
AppConfig = UnifiedConfiguration
ConfigManager = UnifiedConfigManager
get_config_manager = get_unified_config_manager
AWSConfig = AWSConfiguration
UIConfig = UIConfiguration
PerformanceConfig = PerformanceConfiguration
SecurityConfig = SecurityConfiguration

__all__ = [
    'UnifiedConfiguration',
    'UnifiedConfigManager',
    'AppConfig',  # Backward compatibility
    'ConfigManager',  # Backward compatibility
    'get_config_manager',
    'get_unified_config_manager',
    'get_config',
    'get_feature_flag',
    'set_feature_flag',
    'Environment',
    'LogLevel',
    'AWSConfiguration',
    'AWSConfig',  # Backward compatibility
    'VideoProcessingConfiguration',
    'StorageConfiguration',
    'FeatureConfiguration',
    'UIConfiguration',
    'UIConfig',  # Backward compatibility
    'PerformanceConfiguration',
    'PerformanceConfig',  # Backward compatibility
    'SecurityConfiguration',
    'SecurityConfig'  # Backward compatibility
]
