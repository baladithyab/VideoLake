"""
Standardized Metadata Management Patterns

This module provides unified metadata handling across different storage backends,
ensuring consistent metadata transformation and validation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Type
import json
import logging

from src.exceptions import ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class MetadataFormat(Enum):
    """Supported metadata formats."""
    S3_VECTOR = "s3vector"  # Limited to 10 keys, specific types
    OPENSEARCH = "opensearch"  # Unlimited fields, flexible schema
    GENERIC = "generic"  # Basic key-value pairs


class MetadataFieldType(Enum):
    """Metadata field types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    LIST = "list"
    OBJECT = "object"


@dataclass
class MetadataField:
    """Definition of a metadata field."""
    name: str
    field_type: MetadataFieldType
    required: bool = False
    max_length: Optional[int] = None
    allowed_values: Optional[List[Any]] = None
    description: str = ""
    
    def validate_value(self, value: Any) -> bool:
        """Validate a value against this field definition."""
        if value is None and self.required:
            return False
        
        if value is None:
            return True
        
        # Type validation
        if self.field_type == MetadataFieldType.STRING:
            if not isinstance(value, str):
                return False
            if self.max_length and len(value) > self.max_length:
                return False
        
        elif self.field_type == MetadataFieldType.INTEGER:
            if not isinstance(value, int):
                return False
        
        elif self.field_type == MetadataFieldType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
        
        elif self.field_type == MetadataFieldType.BOOLEAN:
            if not isinstance(value, bool):
                return False
        
        elif self.field_type == MetadataFieldType.DATETIME:
            if not isinstance(value, (str, datetime)):
                return False
        
        elif self.field_type == MetadataFieldType.LIST:
            if not isinstance(value, list):
                return False
        
        elif self.field_type == MetadataFieldType.OBJECT:
            if not isinstance(value, dict):
                return False
        
        # Value constraints
        if self.allowed_values and value not in self.allowed_values:
            return False
        
        return True


@dataclass
class MediaMetadata:
    """Comprehensive metadata for media files."""
    # Core file information
    file_name: str
    s3_storage_location: str
    file_format: str
    file_size_bytes: int
    
    # Media properties
    duration_seconds: float
    resolution: Optional[str] = None
    frame_rate: Optional[float] = None
    audio_channels: Optional[int] = None
    bitrate: Optional[int] = None
    
    # Processing information
    processing_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    segment_count: int = 0
    segment_duration: float = 5.0
    vector_types_generated: List[str] = field(default_factory=list)
    
    # Embedding metadata
    embedding_model: str = "marengo-2.7"
    embedding_dimensions: Dict[str, int] = field(default_factory=dict)
    processing_cost_usd: Optional[float] = None
    
    # Business metadata
    content_category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # System metadata
    created_by: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "1.0"
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def add_vector_type(self, vector_type: str, dimensions: int) -> None:
        """Add a vector type to the metadata."""
        if vector_type not in self.vector_types_generated:
            self.vector_types_generated.append(vector_type)
        self.embedding_dimensions[vector_type] = dimensions
        self.update_timestamp()
    
    def add_custom_field(self, key: str, value: Any) -> None:
        """Add a custom metadata field."""
        self.custom_metadata[key] = value
        self.update_timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetadataHandler(ABC):
    """Abstract base class for metadata handlers."""
    
    def __init__(self, format_type: MetadataFormat):
        self.format_type = format_type
        self.logger = get_logger(self.__class__.__name__)
        self.field_definitions: Dict[str, MetadataField] = {}
        self._initialize_field_definitions()
    
    @abstractmethod
    def _initialize_field_definitions(self) -> None:
        """Initialize field definitions for this handler."""
        pass
    
    @abstractmethod
    def transform_metadata(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """Transform metadata to the target format."""
        pass
    
    @abstractmethod
    def validate_metadata(self, metadata_dict: Dict[str, Any]) -> bool:
        """Validate metadata against format requirements."""
        pass
    
    def add_field_definition(self, field: MetadataField) -> None:
        """Add a field definition."""
        self.field_definitions[field.name] = field
    
    def get_field_definition(self, field_name: str) -> Optional[MetadataField]:
        """Get field definition by name."""
        return self.field_definitions.get(field_name)
    
    def validate_field_value(self, field_name: str, value: Any) -> bool:
        """Validate a field value."""
        field_def = self.get_field_definition(field_name)
        if not field_def:
            return True  # Unknown fields are allowed by default
        
        return field_def.validate_value(value)


class S3VectorMetadataHandler(MetadataHandler):
    """Metadata handler for S3Vector format (10-key limit)."""
    
    def __init__(self):
        super().__init__(MetadataFormat.S3_VECTOR)
        self.max_fields = 10
    
    def _initialize_field_definitions(self) -> None:
        """Initialize S3Vector field definitions."""
        # S3Vector has strict limitations: 10 keys max, specific types
        self.add_field_definition(MetadataField(
            name="file_name",
            field_type=MetadataFieldType.STRING,
            required=True,
            max_length=255,
            description="Original file name"
        ))
        
        self.add_field_definition(MetadataField(
            name="s3_location",
            field_type=MetadataFieldType.STRING,
            required=True,
            max_length=512,
            description="S3 storage location"
        ))
        
        self.add_field_definition(MetadataField(
            name="duration",
            field_type=MetadataFieldType.FLOAT,
            required=True,
            description="Duration in seconds"
        ))
        
        self.add_field_definition(MetadataField(
            name="format",
            field_type=MetadataFieldType.STRING,
            max_length=50,
            description="File format"
        ))
        
        self.add_field_definition(MetadataField(
            name="timestamp",
            field_type=MetadataFieldType.STRING,
            required=True,
            description="Processing timestamp"
        ))
        
        self.add_field_definition(MetadataField(
            name="model",
            field_type=MetadataFieldType.STRING,
            max_length=100,
            description="Embedding model used"
        ))
        
        self.add_field_definition(MetadataField(
            name="segments",
            field_type=MetadataFieldType.INTEGER,
            description="Number of segments"
        ))
        
        self.add_field_definition(MetadataField(
            name="category",
            field_type=MetadataFieldType.STRING,
            max_length=50,
            description="Content category"
        ))
        
        self.add_field_definition(MetadataField(
            name="resolution",
            field_type=MetadataFieldType.STRING,
            max_length=20,
            description="Video resolution"
        ))
        
        self.add_field_definition(MetadataField(
            name="cost",
            field_type=MetadataFieldType.FLOAT,
            description="Processing cost in USD"
        ))
    
    def transform_metadata(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """Transform metadata to S3Vector format (10-key limit)."""
        transformed = {
            "file_name": metadata.file_name,
            "s3_location": metadata.s3_storage_location,
            "duration": metadata.duration_seconds,
            "format": metadata.file_format,
            "timestamp": metadata.processing_timestamp,
            "model": metadata.embedding_model,
            "segments": metadata.segment_count,
            "category": metadata.content_category or "video",
            "resolution": metadata.resolution or "unknown",
            "cost": metadata.processing_cost_usd or 0.0
        }
        
        # Validate field count
        if len(transformed) > self.max_fields:
            self.logger.warning(f"S3Vector metadata exceeds {self.max_fields} field limit")
            # Keep only the most important fields
            priority_fields = [
                "file_name", "s3_location", "duration", "timestamp", 
                "model", "segments", "category", "format", "resolution", "cost"
            ]
            transformed = {k: v for k, v in transformed.items() 
                         if k in priority_fields[:self.max_fields]}
        
        return transformed
    
    def validate_metadata(self, metadata_dict: Dict[str, Any]) -> bool:
        """Validate S3Vector metadata."""
        if len(metadata_dict) > self.max_fields:
            raise ValidationError(
                f"S3Vector metadata cannot exceed {self.max_fields} fields, got {len(metadata_dict)}",
                error_code="S3VECTOR_METADATA_TOO_MANY_FIELDS",
                error_details={"field_count": len(metadata_dict), "max_fields": self.max_fields}
            )
        
        # Validate each field
        for field_name, value in metadata_dict.items():
            if not self.validate_field_value(field_name, value):
                raise ValidationError(
                    f"Invalid value for S3Vector metadata field '{field_name}': {value}",
                    error_code="S3VECTOR_METADATA_INVALID_FIELD",
                    error_details={"field_name": field_name, "value": value}
                )
        
        return True


class OpenSearchMetadataHandler(MetadataHandler):
    """Metadata handler for OpenSearch format (unlimited fields)."""
    
    def __init__(self):
        super().__init__(MetadataFormat.OPENSEARCH)
    
    def _initialize_field_definitions(self) -> None:
        """Initialize OpenSearch field definitions."""
        # OpenSearch is more flexible - define common fields but allow others
        common_fields = [
            ("file_name", MetadataFieldType.STRING, True),
            ("s3_storage_location", MetadataFieldType.STRING, True),
            ("file_format", MetadataFieldType.STRING, False),
            ("file_size_bytes", MetadataFieldType.INTEGER, False),
            ("duration_seconds", MetadataFieldType.FLOAT, True),
            ("resolution", MetadataFieldType.STRING, False),
            ("frame_rate", MetadataFieldType.FLOAT, False),
            ("audio_channels", MetadataFieldType.INTEGER, False),
            ("processing_timestamp", MetadataFieldType.STRING, True),
            ("segment_count", MetadataFieldType.INTEGER, False),
            ("segment_duration", MetadataFieldType.FLOAT, False),
            ("vector_types_generated", MetadataFieldType.LIST, False),
            ("embedding_model", MetadataFieldType.STRING, False),
            ("embedding_dimensions", MetadataFieldType.OBJECT, False),
            ("processing_cost_usd", MetadataFieldType.FLOAT, False),
            ("content_category", MetadataFieldType.STRING, False),
            ("tags", MetadataFieldType.LIST, False),
            ("custom_metadata", MetadataFieldType.OBJECT, False),
            ("created_by", MetadataFieldType.STRING, False),
            ("created_at", MetadataFieldType.STRING, False),
            ("updated_at", MetadataFieldType.STRING, False),
            ("version", MetadataFieldType.STRING, False)
        ]
        
        for name, field_type, required in common_fields:
            self.add_field_definition(MetadataField(
                name=name,
                field_type=field_type,
                required=required,
                description=f"OpenSearch field: {name}"
            ))
    
    def transform_metadata(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """Transform metadata to OpenSearch format (unlimited fields)."""
        # OpenSearch can handle the full metadata structure
        transformed = asdict(metadata)
        
        # Add additional OpenSearch-specific fields
        transformed.update({
            "title": metadata.file_name,
            "content": f"Media file: {metadata.file_name}",
            "document_type": "media_file",
            "searchable_text": f"{metadata.file_name} {metadata.content_category or ''} {' '.join(metadata.tags)}",
            "metadata_version": "1.0"
        })
        
        return transformed
    
    def validate_metadata(self, metadata_dict: Dict[str, Any]) -> bool:
        """Validate OpenSearch metadata."""
        # Check required fields
        required_fields = [name for name, field in self.field_definitions.items() if field.required]
        
        for field_name in required_fields:
            if field_name not in metadata_dict:
                raise ValidationError(
                    f"Required OpenSearch metadata field missing: {field_name}",
                    error_code="OPENSEARCH_METADATA_MISSING_FIELD",
                    error_details={"field_name": field_name}
                )
        
        # Validate field values
        for field_name, value in metadata_dict.items():
            if not self.validate_field_value(field_name, value):
                field_def = self.get_field_definition(field_name)
                raise ValidationError(
                    f"Invalid value for OpenSearch metadata field '{field_name}': {value}",
                    error_code="OPENSEARCH_METADATA_INVALID_FIELD",
                    error_details={
                        "field_name": field_name, 
                        "value": value,
                        "expected_type": field_def.field_type.value if field_def else "unknown"
                    }
                )
        
        return True


class GenericMetadataHandler(MetadataHandler):
    """Generic metadata handler for basic key-value pairs."""
    
    def __init__(self):
        super().__init__(MetadataFormat.GENERIC)
    
    def _initialize_field_definitions(self) -> None:
        """Generic handler doesn't enforce specific field definitions."""
        pass
    
    def transform_metadata(self, metadata: MediaMetadata) -> Dict[str, Any]:
        """Transform metadata to generic format."""
        # Flatten complex objects to strings for generic compatibility
        transformed = {}
        metadata_dict = asdict(metadata)
        
        for key, value in metadata_dict.items():
            if isinstance(value, (dict, list)):
                transformed[key] = json.dumps(value)
            elif isinstance(value, (datetime,)):
                transformed[key] = value.isoformat()
            else:
                transformed[key] = str(value) if value is not None else ""
        
        return transformed
    
    def validate_metadata(self, metadata_dict: Dict[str, Any]) -> bool:
        """Generic validation - just check that values are serializable."""
        try:
            json.dumps(metadata_dict, default=str)
            return True
        except (TypeError, ValueError) as e:
            raise ValidationError(
                f"Generic metadata contains non-serializable values: {str(e)}",
                error_code="GENERIC_METADATA_NOT_SERIALIZABLE",
                error_details={"error": str(e)}
            )


class MetadataTransformer:
    """Utility class for transforming metadata between formats."""
    
    def __init__(self):
        self.handlers = {
            MetadataFormat.S3_VECTOR: S3VectorMetadataHandler(),
            MetadataFormat.OPENSEARCH: OpenSearchMetadataHandler(),
            MetadataFormat.GENERIC: GenericMetadataHandler()
        }
    
    def transform(self, metadata: MediaMetadata, target_format: MetadataFormat) -> Dict[str, Any]:
        """Transform metadata to target format."""
        handler = self.handlers.get(target_format)
        if not handler:
            raise ValidationError(
                f"No handler available for metadata format: {target_format.value}",
                error_code="UNSUPPORTED_METADATA_FORMAT",
                error_details={"format": target_format.value}
            )
        
        return handler.transform_metadata(metadata)
    
    def validate(self, metadata_dict: Dict[str, Any], format_type: MetadataFormat) -> bool:
        """Validate metadata against format requirements."""
        handler = self.handlers.get(format_type)
        if not handler:
            raise ValidationError(
                f"No handler available for metadata format: {format_type.value}",
                error_code="UNSUPPORTED_METADATA_FORMAT",
                error_details={"format": format_type.value}
            )
        
        return handler.validate_metadata(metadata_dict)
    
    def get_handler(self, format_type: MetadataFormat) -> MetadataHandler:
        """Get metadata handler for a specific format."""
        handler = self.handlers.get(format_type)
        if not handler:
            raise ValidationError(
                f"No handler available for metadata format: {format_type.value}",
                error_code="UNSUPPORTED_METADATA_FORMAT",
                error_details={"format": format_type.value}
            )
        return handler


# Global transformer instance
_metadata_transformer = MetadataTransformer()


def transform_metadata_for_s3vector(metadata: MediaMetadata) -> Dict[str, Any]:
    """Transform metadata for S3Vector storage."""
    return _metadata_transformer.transform(metadata, MetadataFormat.S3_VECTOR)


def transform_metadata_for_opensearch(metadata: MediaMetadata) -> Dict[str, Any]:
    """Transform metadata for OpenSearch storage."""
    return _metadata_transformer.transform(metadata, MetadataFormat.OPENSEARCH)


def validate_s3vector_metadata(metadata_dict: Dict[str, Any]) -> bool:
    """Validate metadata for S3Vector format."""
    return _metadata_transformer.validate(metadata_dict, MetadataFormat.S3_VECTOR)


def validate_opensearch_metadata(metadata_dict: Dict[str, Any]) -> bool:
    """Validate metadata for OpenSearch format."""
    return _metadata_transformer.validate(metadata_dict, MetadataFormat.OPENSEARCH)


def create_media_metadata(file_name: str, s3_location: str, file_format: str, 
                         file_size: int, duration: float, **kwargs) -> MediaMetadata:
    """Create MediaMetadata instance with common fields."""
    return MediaMetadata(
        file_name=file_name,
        s3_storage_location=s3_location,
        file_format=file_format,
        file_size_bytes=file_size,
        duration_seconds=duration,
        **kwargs
    )