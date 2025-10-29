"""
Core application components.

Includes dependency injection, configuration, and shared utilities.
"""

from .dependencies import (
    get_storage_manager,
    get_search_engine,
    get_twelvelabs_service,
    get_bedrock_service,
    get_vector_store_manager,
    get_resource_registry
)

__all__ = [
    'get_storage_manager',
    'get_search_engine',
    'get_twelvelabs_service',
    'get_bedrock_service',
    'get_vector_store_manager',
    'get_resource_registry'
]
