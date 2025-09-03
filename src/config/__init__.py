#!/usr/bin/env python3
"""
Configuration Package

Unified configuration management system for the S3Vector demo.
"""

from .app_config import (
    AppConfig,
    ConfigManager,
    get_config_manager,
    get_config,
    get_feature_flag,
    set_feature_flag,
    Environment,
    LogLevel,
    AWSConfig,
    TwelveLabsConfig,
    OpenSearchConfig,
    FeatureFlags,
    UIConfig,
    PerformanceConfig,
    SecurityConfig
)

# Backward compatibility - import old config manager
try:
    from ..config import config_manager as old_config_manager
except ImportError:
    old_config_manager = None

# Export both old and new for compatibility
config_manager = old_config_manager  # Backward compatibility

__all__ = [
    'AppConfig',
    'ConfigManager',
    'get_config_manager',
    'get_config',
    'get_feature_flag',
    'set_feature_flag',
    'Environment',
    'LogLevel',
    'AWSConfig',
    'TwelveLabsConfig',
    'OpenSearchConfig',
    'FeatureFlags',
    'UIConfig',
    'PerformanceConfig',
    'SecurityConfig',
    'config_manager'  # Backward compatibility
]
