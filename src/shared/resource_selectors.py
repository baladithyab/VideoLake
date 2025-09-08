"""
Common S3 Bucket and Resource Selection Logic

This module provides standardized resource selection and naming strategies
to eliminate duplication across services and ensure consistent resource management.
"""

import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Tuple
import logging

from src.exceptions import ValidationError
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)


class ResourceNamingStrategy(Enum):
    """Strategies for resource naming."""
    ENVIRONMENT_PREFIX = "environment_prefix"  # env-resource-type-suffix
    HASH_SUFFIX = "hash_suffix"  # resource-type-hash
    TIMESTAMP_SUFFIX = "timestamp_suffix"  # resource-type-timestamp
    CUSTOM = "custom"  # User-defined naming


class ResourceType(Enum):
    """Types of AWS resources."""
    S3_BUCKET = "s3-bucket"
    S3_VECTOR_BUCKET = "s3vector-bucket"
    S3_VECTOR_INDEX = "s3vector-index"
    OPENSEARCH_DOMAIN = "opensearch-domain"
    OPENSEARCH_INDEX = "opensearch-index"


@dataclass
class ResourceSelectionCriteria:
    """Criteria for resource selection."""
    resource_type: ResourceType
    environment: str = "prod"
    region: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    name_pattern: Optional[str] = None
    created_after: Optional[str] = None
    created_before: Optional[str] = None
    
    # Resource-specific criteria
    min_capacity: Optional[int] = None
    max_capacity: Optional[int] = None
    encryption_required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert criteria to dictionary."""
        return {
            "resource_type": self.resource_type.value,
            "environment": self.environment,
            "region": self.region,
            "tags": self.tags,
            "name_pattern": self.name_pattern,
            "created_after": self.created_after,
            "created_before": self.created_before,
            "min_capacity": self.min_capacity,
            "max_capacity": self.max_capacity,
            "encryption_required": self.encryption_required
        }


class ResourceSelector(ABC):
    """Abstract base class for resource selectors."""
    
    def __init__(self, naming_strategy: ResourceNamingStrategy = ResourceNamingStrategy.ENVIRONMENT_PREFIX):
        self.naming_strategy = naming_strategy
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def generate_name(self, base_name: str, **kwargs) -> str:
        """Generate a resource name based on the naming strategy."""
        pass
    
    @abstractmethod
    def validate_name(self, name: str) -> bool:
        """Validate a resource name according to AWS requirements."""
        pass
    
    @abstractmethod
    def select_resource(self, criteria: ResourceSelectionCriteria) -> Optional[Dict[str, Any]]:
        """Select an existing resource based on criteria."""
        pass
    
    def sanitize_name(self, name: str, allowed_chars: str = "a-z0-9-") -> str:
        """Sanitize a name to contain only allowed characters."""
        # Convert to lowercase
        sanitized = name.lower()
        
        # Replace invalid characters with hyphens
        pattern = f"[^{allowed_chars}]"
        sanitized = re.sub(pattern, "-", sanitized)
        
        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")
        
        return sanitized


class S3BucketSelector(ResourceSelector):
    """Selector for S3 buckets with AWS naming compliance."""
    
    def __init__(self, naming_strategy: ResourceNamingStrategy = ResourceNamingStrategy.ENVIRONMENT_PREFIX):
        super().__init__(naming_strategy)
        self.min_length = 3
        self.max_length = 63
    
    def generate_name(self, base_name: str, **kwargs) -> str:
        """Generate S3 bucket name based on naming strategy."""
        environment = kwargs.get("environment", "prod")
        suffix = kwargs.get("suffix", "")
        
        if self.naming_strategy == ResourceNamingStrategy.ENVIRONMENT_PREFIX:
            name = f"{environment}-{base_name}"
            if suffix:
                name = f"{name}-{suffix}"
        
        elif self.naming_strategy == ResourceNamingStrategy.HASH_SUFFIX:
            # Create hash from base_name + environment for uniqueness
            hash_input = f"{base_name}-{environment}"
            hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
            name = f"{base_name}-{hash_suffix}"
        
        elif self.naming_strategy == ResourceNamingStrategy.TIMESTAMP_SUFFIX:
            import time
            timestamp = str(int(time.time()))[-8:]  # Last 8 digits
            name = f"{base_name}-{timestamp}"
        
        elif self.naming_strategy == ResourceNamingStrategy.CUSTOM:
            name = kwargs.get("custom_name", base_name)
        
        else:
            name = base_name
        
        # Sanitize and validate
        sanitized_name = self.sanitize_name(name)
        
        # Ensure length constraints
        if len(sanitized_name) < self.min_length:
            sanitized_name = f"s3vector-{sanitized_name}"
        
        if len(sanitized_name) > self.max_length:
            # Truncate but keep meaningful parts
            if "-" in sanitized_name:
                parts = sanitized_name.split("-")
                # Keep first and last parts, truncate middle
                if len(parts) > 2:
                    first_part = parts[0]
                    last_part = parts[-1]
                    available_length = self.max_length - len(first_part) - len(last_part) - 2
                    if available_length > 0:
                        middle_parts = "-".join(parts[1:-1])
                        if len(middle_parts) > available_length:
                            middle_parts = middle_parts[:available_length]
                        sanitized_name = f"{first_part}-{middle_parts}-{last_part}"
                    else:
                        sanitized_name = f"{first_part}-{last_part}"
            else:
                sanitized_name = sanitized_name[:self.max_length]
        
        # Final validation
        if not self.validate_name(sanitized_name):
            # Fallback to a simple valid name
            fallback_name = f"s3vector-bucket-{hashlib.md5(base_name.encode()).hexdigest()[:8]}"
            self.logger.warning(f"Generated name '{sanitized_name}' invalid, using fallback: {fallback_name}")
            sanitized_name = fallback_name
        
        return sanitized_name
    
    def validate_name(self, name: str) -> bool:
        """Validate S3 bucket name according to AWS requirements."""
        if not name or len(name) < self.min_length or len(name) > self.max_length:
            return False
        
        # Must start and end with letter or number
        if not re.match(r"^[a-z0-9].*[a-z0-9]$", name):
            return False
        
        # Only lowercase letters, numbers, hyphens, and periods
        if not re.match(r"^[a-z0-9.-]+$", name):
            return False
        
        # Cannot have consecutive periods or hyphens
        if ".." in name or "--" in name:
            return False
        
        # Cannot have period-hyphen or hyphen-period combinations
        if ".-" in name or "-." in name:
            return False
        
        # Cannot be formatted as IP address
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", name):
            return False
        
        return True
    
    def select_resource(self, criteria: ResourceSelectionCriteria) -> Optional[Dict[str, Any]]:
        """Select an existing S3 bucket based on criteria."""
        try:
            # Query resource registry for matching buckets
            registry_resources = resource_registry.list_resources()
            
            matching_buckets = []
            for resource in registry_resources:
                if resource.get("type") == "s3_bucket":
                    bucket_name = resource.get("name", "")
                    
                    # Apply name pattern filter
                    if criteria.name_pattern and not re.search(criteria.name_pattern, bucket_name):
                        continue
                    
                    # Apply environment filter
                    if criteria.environment and criteria.environment not in bucket_name:
                        continue
                    
                    # Apply tag filters
                    resource_tags = resource.get("tags", {})
                    if criteria.tags:
                        if not all(resource_tags.get(k) == v for k, v in criteria.tags.items()):
                            continue
                    
                    matching_buckets.append(resource)
            
            # Return the most recently created matching bucket
            if matching_buckets:
                return max(matching_buckets, key=lambda x: x.get("created_at", ""))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error selecting S3 bucket: {e}")
            return None
    
    def get_or_create_bucket_name(self, base_name: str, environment: str = "prod", 
                                 suffix: str = "") -> str:
        """Get existing bucket name or generate a new one."""
        # First try to find existing bucket
        criteria = ResourceSelectionCriteria(
            resource_type=ResourceType.S3_BUCKET,
            environment=environment,
            name_pattern=f".*{base_name}.*"
        )
        
        existing_bucket = self.select_resource(criteria)
        if existing_bucket:
            bucket_name = existing_bucket.get("name", "")
            self.logger.info(f"Found existing bucket: {bucket_name}")
            return bucket_name
        
        # Generate new bucket name
        new_name = self.generate_name(
            base_name, 
            environment=environment, 
            suffix=suffix
        )
        self.logger.info(f"Generated new bucket name: {new_name}")
        return new_name


class IndexSelector(ResourceSelector):
    """Selector for vector indexes (S3Vector and OpenSearch)."""
    
    def __init__(self, naming_strategy: ResourceNamingStrategy = ResourceNamingStrategy.ENVIRONMENT_PREFIX):
        super().__init__(naming_strategy)
        self.min_length = 3
        self.max_length = 63
    
    def generate_name(self, base_name: str, **kwargs) -> str:
        """Generate index name based on naming strategy."""
        environment = kwargs.get("environment", "prod")
        vector_type = kwargs.get("vector_type", "")
        version = kwargs.get("version", "v1")
        
        if self.naming_strategy == ResourceNamingStrategy.ENVIRONMENT_PREFIX:
            name = f"{environment}-{base_name}"
            if vector_type:
                name = f"{name}-{vector_type}"
            name = f"{name}-{version}"
        
        elif self.naming_strategy == ResourceNamingStrategy.HASH_SUFFIX:
            hash_input = f"{base_name}-{environment}-{vector_type}"
            hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
            name = f"{base_name}-{hash_suffix}"
        
        elif self.naming_strategy == ResourceNamingStrategy.CUSTOM:
            name = kwargs.get("custom_name", base_name)
        
        else:
            name = base_name
        
        # Sanitize and validate
        sanitized_name = self.sanitize_name(name)
        
        # Ensure length constraints
        if len(sanitized_name) > self.max_length:
            sanitized_name = sanitized_name[:self.max_length].rstrip("-")
        
        if len(sanitized_name) < self.min_length:
            sanitized_name = f"index-{sanitized_name}"
        
        return sanitized_name
    
    def validate_name(self, name: str) -> bool:
        """Validate index name according to AWS requirements."""
        if not name or len(name) < self.min_length or len(name) > self.max_length:
            return False
        
        # Must start and end with letter or number
        if not re.match(r"^[a-z0-9].*[a-z0-9]$", name):
            return False
        
        # Only lowercase letters, numbers, and hyphens
        if not re.match(r"^[a-z0-9-]+$", name):
            return False
        
        # Cannot have consecutive hyphens
        if "--" in name:
            return False
        
        return True
    
    def select_resource(self, criteria: ResourceSelectionCriteria) -> Optional[Dict[str, Any]]:
        """Select an existing index based on criteria."""
        try:
            registry_resources = resource_registry.list_resources()
            
            matching_indexes = []
            resource_type_map = {
                ResourceType.S3_VECTOR_INDEX: "s3vector_index",
                ResourceType.OPENSEARCH_INDEX: "opensearch_index"
            }
            
            target_type = resource_type_map.get(criteria.resource_type)
            if not target_type:
                return None
            
            for resource in registry_resources:
                if resource.get("type") == target_type:
                    index_name = resource.get("name", "")
                    
                    # Apply filters
                    if criteria.name_pattern and not re.search(criteria.name_pattern, index_name):
                        continue
                    
                    if criteria.environment and criteria.environment not in index_name:
                        continue
                    
                    matching_indexes.append(resource)
            
            if matching_indexes:
                return max(matching_indexes, key=lambda x: x.get("created_at", ""))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error selecting index: {e}")
            return None
    
    def generate_index_arn(self, bucket_name: str, index_name: str, 
                          region: str, account_id: str) -> str:
        """Generate S3Vector index ARN."""
        return f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{index_name}"
    
    def parse_index_arn(self, arn: str) -> Tuple[str, str]:
        """Parse S3Vector index ARN to extract bucket and index names."""
        # Expected format: arn:aws:s3vectors:region:account:bucket/bucket_name/index/index_name
        try:
            parts = arn.split(":")
            if len(parts) >= 6 and parts[2] == "s3vectors":
                resource_part = parts[5]  # bucket/name/index/name
                resource_parts = resource_part.split("/")
                if len(resource_parts) >= 4 and resource_parts[0] == "bucket" and resource_parts[2] == "index":
                    bucket_name = resource_parts[1]
                    index_name = resource_parts[3]
                    return bucket_name, index_name
            
            raise ValueError("Invalid ARN format")
            
        except Exception as e:
            raise ValidationError(
                f"Failed to parse index ARN: {arn}",
                error_code="INVALID_INDEX_ARN",
                error_details={"arn": arn, "error": str(e)}
            )


def validate_resource_name(resource_type: ResourceType, name: str) -> bool:
    """Validate a resource name according to its type requirements."""
    if resource_type in [ResourceType.S3_BUCKET, ResourceType.S3_VECTOR_BUCKET]:
        selector = S3BucketSelector()
        return selector.validate_name(name)
    
    elif resource_type in [ResourceType.S3_VECTOR_INDEX, ResourceType.OPENSEARCH_INDEX]:
        selector = IndexSelector()
        return selector.validate_name(name)
    
    else:
        # Generic validation for other resource types
        return bool(name and 3 <= len(name) <= 63 and re.match(r"^[a-z0-9-]+$", name))


def create_resource_selector(resource_type: ResourceType, 
                           naming_strategy: ResourceNamingStrategy = ResourceNamingStrategy.ENVIRONMENT_PREFIX) -> ResourceSelector:
    """Factory function to create appropriate resource selector."""
    if resource_type in [ResourceType.S3_BUCKET, ResourceType.S3_VECTOR_BUCKET]:
        return S3BucketSelector(naming_strategy)
    
    elif resource_type in [ResourceType.S3_VECTOR_INDEX, ResourceType.OPENSEARCH_INDEX]:
        return IndexSelector(naming_strategy)
    
    else:
        raise ValidationError(
            f"No selector available for resource type: {resource_type.value}",
            error_code="UNSUPPORTED_RESOURCE_TYPE",
            error_details={"resource_type": resource_type.value}
        )


# Convenience functions for common operations
def generate_s3_bucket_name(base_name: str, environment: str = "prod", 
                           suffix: str = "") -> str:
    """Generate a valid S3 bucket name."""
    selector = S3BucketSelector()
    return selector.generate_name(base_name, environment=environment, suffix=suffix)


def generate_index_name(base_name: str, vector_type: str, 
                       environment: str = "prod", version: str = "v1") -> str:
    """Generate a valid index name."""
    selector = IndexSelector()
    return selector.generate_name(
        base_name, 
        environment=environment, 
        vector_type=vector_type, 
        version=version
    )


def find_existing_bucket(base_name: str, environment: str = "prod") -> Optional[str]:
    """Find existing S3 bucket matching criteria."""
    selector = S3BucketSelector()
    criteria = ResourceSelectionCriteria(
        resource_type=ResourceType.S3_BUCKET,
        environment=environment,
        name_pattern=f".*{base_name}.*"
    )
    
    result = selector.select_resource(criteria)
    return result.get("name") if result else None