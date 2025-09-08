"""
Centralized Vector Type Definitions and Configurations

This module provides standardized vector type configurations that eliminate
duplication across services and ensure consistency in vector operations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Union
import logging

from src.exceptions import ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SupportedVectorTypes(Enum):
    """Enumeration of all supported vector types in the system."""
    VISUAL_TEXT = "visual-text"
    VISUAL_IMAGE = "visual-image" 
    AUDIO = "audio"
    TEXT_TITAN = "text-titan"
    TEXT_COHERE = "text-cohere"
    MULTIMODAL = "multimodal"


@dataclass
class VectorTypeConfig:
    """Configuration for a specific vector type."""
    vector_type: SupportedVectorTypes
    dimensions: int
    default_metric: str = "cosine"
    supported_metrics: List[str] = field(default_factory=lambda: ["cosine", "euclidean"])
    embedding_model: Optional[str] = None
    max_batch_size: int = 500
    description: str = ""
    
    # S3Vector specific settings
    s3vector_data_type: str = "float32"
    s3vector_non_filterable_keys: List[str] = field(default_factory=list)
    
    # OpenSearch specific settings
    opensearch_space_type: Optional[str] = None
    opensearch_engine: str = "nmslib"
    
    # Processing settings
    processing_batch_size: int = 10
    concurrent_operations: int = 5
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate vector type configuration."""
        if self.dimensions < 1 or self.dimensions > 4096:
            raise ValidationError(
                f"Vector dimensions must be between 1 and 4096, got {self.dimensions}",
                error_code="INVALID_VECTOR_DIMENSIONS",
                error_details={
                    "vector_type": self.vector_type.value,
                    "dimensions": self.dimensions
                }
            )
        
        if self.default_metric not in self.supported_metrics:
            raise ValidationError(
                f"Default metric '{self.default_metric}' not in supported metrics {self.supported_metrics}",
                error_code="INVALID_DEFAULT_METRIC",
                error_details={
                    "vector_type": self.vector_type.value,
                    "default_metric": self.default_metric,
                    "supported_metrics": self.supported_metrics
                }
            )
        
        if self.max_batch_size < 1 or self.max_batch_size > 1000:
            raise ValidationError(
                f"Max batch size must be between 1 and 1000, got {self.max_batch_size}",
                error_code="INVALID_BATCH_SIZE",
                error_details={
                    "vector_type": self.vector_type.value,
                    "max_batch_size": self.max_batch_size
                }
            )
    
    def get_s3vector_config(self) -> Dict[str, Any]:
        """Get S3Vector-specific configuration."""
        return {
            "dimensions": self.dimensions,
            "distance_metric": self.default_metric,
            "data_type": self.s3vector_data_type,
            "non_filterable_metadata_keys": self.s3vector_non_filterable_keys
        }
    
    def get_opensearch_config(self) -> Dict[str, Any]:
        """Get OpenSearch-specific configuration."""
        return {
            "dimension": self.dimensions,
            "space_type": self.opensearch_space_type or self.default_metric,
            "engine": self.opensearch_engine
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing-specific configuration."""
        return {
            "batch_size": self.processing_batch_size,
            "max_concurrent": self.concurrent_operations,
            "max_vectors_per_batch": self.max_batch_size
        }


class VectorTypeRegistry:
    """Registry for managing vector type configurations."""
    
    def __init__(self):
        """Initialize the vector type registry with default configurations."""
        self._configs: Dict[SupportedVectorTypes, VectorTypeConfig] = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self) -> None:
        """Initialize default vector type configurations."""
        
        # Visual-Text vectors (from TwelveLabs Marengo)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.VISUAL_TEXT,
            dimensions=1024,
            default_metric="cosine",
            embedding_model="marengo-2.7",
            description="Visual-text embeddings from TwelveLabs Marengo model",
            s3vector_non_filterable_keys=["segment_id", "timestamp"],
            processing_batch_size=5,
            concurrent_operations=3
        ))
        
        # Visual-Image vectors (from TwelveLabs Marengo)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.VISUAL_IMAGE,
            dimensions=1024,
            default_metric="cosine",
            embedding_model="marengo-2.7",
            description="Visual-image embeddings from TwelveLabs Marengo model",
            s3vector_non_filterable_keys=["frame_number", "timestamp"],
            processing_batch_size=5,
            concurrent_operations=3
        ))
        
        # Audio vectors (from TwelveLabs Marengo)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.AUDIO,
            dimensions=1024,
            default_metric="cosine",
            embedding_model="marengo-2.7",
            description="Audio embeddings from TwelveLabs Marengo model",
            s3vector_non_filterable_keys=["segment_id", "audio_channels"],
            processing_batch_size=5,
            concurrent_operations=3
        ))
        
        # Text-Titan vectors (from Amazon Bedrock)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.TEXT_TITAN,
            dimensions=1536,
            default_metric="cosine",
            embedding_model="amazon.titan-embed-text-v2:0",
            description="Text embeddings from Amazon Titan",
            max_batch_size=100,
            processing_batch_size=20,
            concurrent_operations=5
        ))
        
        # Text-Cohere vectors (from Amazon Bedrock)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.TEXT_COHERE,
            dimensions=1024,
            default_metric="cosine",
            embedding_model="cohere.embed-multilingual-v3",
            description="Text embeddings from Cohere",
            max_batch_size=96,
            processing_batch_size=50,
            concurrent_operations=3
        ))
        
        # Multimodal vectors (from Amazon Titan)
        self.register_config(VectorTypeConfig(
            vector_type=SupportedVectorTypes.MULTIMODAL,
            dimensions=1024,
            default_metric="cosine",
            embedding_model="amazon.titan-embed-image-v1",
            description="Multimodal embeddings from Amazon Titan",
            processing_batch_size=10,
            concurrent_operations=3
        ))
    
    def register_config(self, config: VectorTypeConfig) -> None:
        """Register a vector type configuration."""
        config.validate()
        self._configs[config.vector_type] = config
        logger.info(f"Registered vector type configuration: {config.vector_type.value}")
    
    def get_config(self, vector_type: Union[SupportedVectorTypes, str]) -> VectorTypeConfig:
        """Get configuration for a vector type."""
        if isinstance(vector_type, str):
            try:
                vector_type = SupportedVectorTypes(vector_type)
            except ValueError:
                raise ValidationError(
                    f"Unsupported vector type: {vector_type}",
                    error_code="UNSUPPORTED_VECTOR_TYPE",
                    error_details={
                        "provided_type": vector_type,
                        "supported_types": [vt.value for vt in SupportedVectorTypes]
                    }
                )
        
        if vector_type not in self._configs:
            raise ValidationError(
                f"No configuration found for vector type: {vector_type.value}",
                error_code="VECTOR_TYPE_NOT_CONFIGURED",
                error_details={"vector_type": vector_type.value}
            )
        
        return self._configs[vector_type]
    
    def list_supported_types(self) -> List[str]:
        """List all supported vector types."""
        return [vt.value for vt in self._configs.keys()]
    
    def get_all_configs(self) -> Dict[SupportedVectorTypes, VectorTypeConfig]:
        """Get all registered configurations."""
        return self._configs.copy()
    
    def update_config(self, vector_type: Union[SupportedVectorTypes, str], 
                     updates: Dict[str, Any]) -> None:
        """Update configuration for a vector type."""
        config = self.get_config(vector_type)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")
        
        # Re-validate after updates
        config.validate()
        logger.info(f"Updated configuration for vector type: {config.vector_type.value}")
    
    def get_dimensions(self, vector_type: Union[SupportedVectorTypes, str]) -> int:
        """Get dimensions for a vector type."""
        return self.get_config(vector_type).dimensions
    
    def get_default_metric(self, vector_type: Union[SupportedVectorTypes, str]) -> str:
        """Get default distance metric for a vector type."""
        return self.get_config(vector_type).default_metric
    
    def get_embedding_model(self, vector_type: Union[SupportedVectorTypes, str]) -> Optional[str]:
        """Get embedding model for a vector type."""
        return self.get_config(vector_type).embedding_model
    
    def validate_vector_data(self, vector_type: Union[SupportedVectorTypes, str], 
                           vector_data: List[float]) -> bool:
        """Validate vector data against type configuration."""
        config = self.get_config(vector_type)
        
        if len(vector_data) != config.dimensions:
            raise ValidationError(
                f"Vector dimensions mismatch: expected {config.dimensions}, got {len(vector_data)}",
                error_code="VECTOR_DIMENSION_MISMATCH",
                error_details={
                    "vector_type": config.vector_type.value,
                    "expected_dimensions": config.dimensions,
                    "actual_dimensions": len(vector_data)
                }
            )
        
        # Validate that all values are finite numbers
        import math
        for i, value in enumerate(vector_data):
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValidationError(
                    f"Invalid vector value at index {i}: {value}",
                    error_code="INVALID_VECTOR_VALUE",
                    error_details={
                        "vector_type": config.vector_type.value,
                        "index": i,
                        "value": value
                    }
                )
        
        return True


# Global registry instance
_vector_type_registry = VectorTypeRegistry()


def get_vector_type_config(vector_type: Union[SupportedVectorTypes, str]) -> VectorTypeConfig:
    """Get vector type configuration from the global registry."""
    return _vector_type_registry.get_config(vector_type)


def validate_vector_dimensions(vector_type: Union[SupportedVectorTypes, str], 
                             vector_data: List[float]) -> bool:
    """Validate vector data dimensions against type configuration."""
    return _vector_type_registry.validate_vector_data(vector_type, vector_data)


def list_supported_vector_types() -> List[str]:
    """List all supported vector types."""
    return _vector_type_registry.list_supported_types()


def register_custom_vector_type(config: VectorTypeConfig) -> None:
    """Register a custom vector type configuration."""
    _vector_type_registry.register_config(config)


def get_vector_type_registry() -> VectorTypeRegistry:
    """Get the global vector type registry instance."""
    return _vector_type_registry