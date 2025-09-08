"""
Shared Components Library

This module provides centralized, reusable components to eliminate redundancy
across services and provide standardized interfaces for common operations.

Components:
- vector_types: Centralized vector type definitions and configurations
- resource_selectors: Common S3 bucket and resource selection logic
- metadata_handlers: Standardized metadata management patterns
- aws_client_pool: Centralized AWS client management with connection pooling
"""

from .vector_types import (
    VectorTypeRegistry,
    VectorTypeConfig,
    SupportedVectorTypes,
    get_vector_type_config,
    validate_vector_dimensions
)

from .resource_selectors import (
    ResourceSelector,
    S3BucketSelector,
    IndexSelector,
    ResourceNamingStrategy,
    validate_resource_name
)

from .metadata_handlers import (
    MetadataHandler,
    S3VectorMetadataHandler,
    OpenSearchMetadataHandler,
    MediaMetadata,
    MetadataTransformer
)

from .aws_client_pool import (
    AWSClientPool,
    ClientPoolConfig,
    AWSService,
    get_pooled_client,
    reset_client_pool
)

__all__ = [
    # Vector Types
    'VectorTypeRegistry',
    'VectorTypeConfig', 
    'SupportedVectorTypes',
    'get_vector_type_config',
    'validate_vector_dimensions',
    
    # Resource Selectors
    'ResourceSelector',
    'S3BucketSelector',
    'IndexSelector', 
    'ResourceNamingStrategy',
    'validate_resource_name',
    
    # Metadata Handlers
    'MetadataHandler',
    'S3VectorMetadataHandler',
    'OpenSearchMetadataHandler',
    'MediaMetadata',
    'MetadataTransformer',
    
    # AWS Client Pool
    'AWSClientPool',
    'ClientPoolConfig',
    'get_pooled_client',
    'reset_client_pool'
]