
"""
Enhanced Storage Integration Manager

This service orchestrates dual backend storage operations, providing:
1. Automatic upsertion to both Direct S3Vector and OpenSearch Hybrid backends
2. Comprehensive metadata preservation for media files
3. Embedding-specific index segregation
4. Error handling and batch processing capabilities
5. Progress tracking for upsertion operations
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, Any, Optional, List, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timezone
import json
import logging

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_integration import OpenSearchIntegrationManager, IntegrationPattern
from src.services.opensearch_s3vector_pattern2_correct import (
    OpenSearchS3VectorPattern2Manager
)
from src.exceptions import VectorStorageError, ValidationError, OpenSearchIntegrationError
from src.utils.logging_config import get_structured_logger, LoggedOperation
from src.utils.timing_tracker import TimingTracker
from src.utils.resource_registry import resource_registry
from src.config.app_config import get_config

# Import shared components
from src.shared import (
    SupportedVectorTypes,
    VectorTypeRegistry,
    get_vector_type_config,
    S3BucketSelector,
    IndexSelector,
    ResourceNamingStrategy,
    MetadataTransformer,
    AWSService,
    get_pooled_client
)
from src.shared.metadata_handlers import (
    MediaMetadata as SharedMediaMetadata,
    transform_metadata_for_opensearch
)

logger = get_structured_logger(__name__)


class StorageBackend(Enum):
    """Available storage backends."""
    DIRECT_S3VECTOR = "direct_s3vector"
    OPENSEARCH_HYBRID = "opensearch_s3vector_hybrid"


# Use shared SupportedVectorTypes instead of local VectorType enum
# Alias for backward compatibility
VectorType = SupportedVectorTypes


# Use shared MediaMetadata class
MediaMetadata = SharedMediaMetadata


@dataclass
class IndexConfiguration:
    """Configuration for vector type indexes using shared components."""
    vector_type: VectorType
    s3vector_index_name: Optional[str] = None
    opensearch_index_name: Optional[str] = None
    
    def __post_init__(self):
        """Initialize configuration from shared vector type registry."""
        # Get shared vector type configuration
        self._shared_config = get_vector_type_config(self.vector_type.value)
    
    @property
    def dimensions(self) -> int:
        """Get dimensions from shared config."""
        return self._shared_config.dimensions
    
    @property
    def distance_metric(self) -> str:
        """Get distance metric from shared config."""
        return self._shared_config.default_metric
    
    @property
    def metadata_keys(self) -> List[str]:
        """Get metadata keys from shared config."""
        return self._shared_config.s3vector_non_filterable_keys
    
    def get_s3vector_index_name(self, environment: str = "prod") -> str:
        """Generate S3Vector index name using shared selector."""
        if self.s3vector_index_name:
            return self.s3vector_index_name
        
        selector = IndexSelector()
        return selector.generate_name(
            "video",
            environment=environment,
            vector_type=self.vector_type.value,
            version="v1"
        )
    
    def get_opensearch_index_name(self, environment: str = "prod") -> str:
        """Generate OpenSearch index name using shared selector."""
        if self.opensearch_index_name:
            return self.opensearch_index_name
            
        selector = IndexSelector()
        return selector.generate_name(
            "video",
            environment=environment,
            vector_type=f"{self.vector_type.value}-hybrid",
            version="v1"
        )


@dataclass
class StorageConfiguration:
    """Configuration for dual backend storage."""
    enabled_backends: List[StorageBackend]
    vector_types: List[VectorType]
    environment: str = "prod"
    
    # S3Vector Configuration
    s3vector_bucket_name: Optional[str] = None
    s3vector_encryption_type: str = "SSE-S3"
    s3vector_kms_key_arn: Optional[str] = None
    
    # OpenSearch Configuration
    opensearch_domain_name: Optional[str] = None
    opensearch_instance_type: str = "or1.medium.search"  # OR1 required for S3 Vectors
    opensearch_instance_count: int = 1
    
    # Processing Configuration
    batch_size: int = 10
    max_concurrent_operations: int = 5
    enable_progress_tracking: bool = True
    enable_error_recovery: bool = True
    
    def validate(self) -> bool:
        """Validate storage configuration."""
        if not self.enabled_backends:
            raise ValidationError("At least one storage backend must be enabled")
        
        if not self.vector_types:
            raise ValidationError("At least one vector type must be specified")
        
        if StorageBackend.DIRECT_S3VECTOR in self.enabled_backends and not self.s3vector_bucket_name:
            raise ValidationError("S3Vector bucket name required for direct storage")
        
        if StorageBackend.OPENSEARCH_HYBRID in self.enabled_backends and not self.opensearch_domain_name:
            raise ValidationError("OpenSearch domain name required for hybrid storage")
        
        return True


@dataclass
class UpsertionProgress:
    """Progress tracking for upsertion operations."""
    operation_id: str
    total_items: int
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    start_time: float = field(default_factory=time.time)
    current_stage: str = "initializing"
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def elapsed_time_seconds(self) -> float:
        """Calculate elapsed time."""
        return time.time() - self.start_time
    
    @property
    def estimated_remaining_seconds(self) -> Optional[float]:
        """Estimate remaining time."""
        if self.processed_items == 0:
            return None
        
        rate = self.processed_items / self.elapsed_time_seconds
        remaining_items = self.total_items - self.processed_items
        return remaining_items / rate if rate > 0 else None


@dataclass
class UpsertionResult:
    """Result from dual backend upsertion operation."""
    operation_id: str
    success: bool
    total_items: int
    successful_items: int
    failed_items: int
    processing_time_seconds: float
    
    # Backend-specific results
    s3vector_results: Optional[Dict[str, Any]] = None
    opensearch_results: Optional[Dict[str, Any]] = None
    
    # Error information
    error_summary: List[str] = field(default_factory=list)
    detailed_errors: Dict[str, List[str]] = field(default_factory=dict)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedStorageIntegrationManager:
    """
    Enhanced storage integration manager for dual backend operations.
    
    This manager orchestrates storage operations across both Direct S3Vector
    and OpenSearch Hybrid backends, providing comprehensive metadata preservation,
    error handling, and progress tracking.
    """
    
    def __init__(self, config: StorageConfiguration):
        """Initialize the enhanced storage integration manager."""
        self.config = config
        self.config.validate()
        
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("enhanced_storage_integration")
        
        # Initialize backend services
        self.s3vector_manager = S3VectorStorageManager()
        self.opensearch_manager = OpenSearchIntegrationManager()
        self.opensearch_pattern2_manager = OpenSearchS3VectorPattern2Manager()
        
        # Progress tracking
        self._progress_lock = Lock()
        self.active_operations: Dict[str, UpsertionProgress] = {}
        
        # Index configurations
        self.index_configurations = self._initialize_index_configurations()
        
        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_operations)
        
        # Initialize backends
        self._initialize_backends()
        
        self.logger.log_operation(
            "enhanced_storage_integration_manager_initialized",
            level="INFO",
            backends=len(config.enabled_backends),
            vector_types=len(config.vector_types)
        )
    
    def _initialize_index_configurations(self) -> Dict[VectorType, IndexConfiguration]:
        """Initialize index configurations for each vector type."""
        configurations = {}
        
        for vector_type in self.config.vector_types:
            # Create configuration using shared vector type registry
            try:
                config = IndexConfiguration(vector_type=vector_type)
                configurations[vector_type] = config
            except Exception as e:
                raise ValidationError(f"Failed to initialize configuration for vector type {vector_type.value}: {str(e)}")
        
        return configurations
    
    def _initialize_backends(self) -> None:
        """Initialize storage backends based on configuration."""
        try:
            if StorageBackend.DIRECT_S3VECTOR in self.config.enabled_backends:
                self._initialize_s3vector_backend()
            
            if StorageBackend.OPENSEARCH_HYBRID in self.config.enabled_backends:
                self._initialize_opensearch_backend()
                
        except Exception as e:
            self.logger.log_error("backend_initialization_failed", e)
            raise
    
    def _initialize_s3vector_backend(self) -> None:
        """Initialize S3Vector backend with lazy index creation strategy."""
        try:
            # Check if bucket exists in registry first
            vector_buckets = resource_registry.list_vector_buckets()

            # Debug logging to understand the mismatch
            self.logger.log_operation(
                "s3vector_bucket_lookup_debug",
                level="INFO",
                configured_bucket_name=self.config.s3vector_bucket_name,
                registry_buckets=[b.get('name') for b in vector_buckets],
                registry_bucket_count=len(vector_buckets)
            )

            existing_bucket = next((b for b in vector_buckets if b.get('name') == self.config.s3vector_bucket_name and b.get('status') == 'created'), None)

            if existing_bucket:
                self.logger.log_operation(
                    "s3vector_bucket_found_in_registry",
                    level="INFO",
                    bucket_name=self.config.s3vector_bucket_name,
                    region=existing_bucket.get('region')
                )
                # Set as active in registry
                resource_registry.set_active_vector_bucket(self.config.s3vector_bucket_name)
            else:
                # Generate or use existing bucket name using shared selector
                if not self.config.s3vector_bucket_name:
                    selector = S3BucketSelector()
                    self.config.s3vector_bucket_name = selector.generate_name(
                        "s3vector-storage",
                        environment=self.config.environment
                    )
                    
                bucket_result = self.s3vector_manager.create_vector_bucket(
                    bucket_name=self.config.s3vector_bucket_name,
                    encryption_type=self.config.s3vector_encryption_type,
                    kms_key_arn=self.config.s3vector_kms_key_arn
                )
                
                # Log creation in resource registry
                try:
                    from src.config.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    region = config_manager.config.aws.region
                    
                    resource_registry.log_vector_bucket_created(
                        bucket_name=self.config.s3vector_bucket_name,
                        region=region,
                        encryption=self.config.s3vector_encryption_type,
                        kms_key_arn=self.config.s3vector_kms_key_arn,
                        source="enhanced_storage_integration_manager"
                    )
                    
                    # Set as active
                    resource_registry.set_active_vector_bucket(self.config.s3vector_bucket_name)
                    
                except Exception as registry_error:
                    self.logger.log_error("failed_to_log_bucket_creation_in_registry", registry_error)
                
                self.logger.log_operation(
                    "s3vector_bucket_initialized",
                    level="INFO",
                    bucket_name=self.config.s3vector_bucket_name,
                    status=bucket_result.get("status")
                )
            
            # UPDATED: Use lazy index creation strategy - create bucket only, not indexes
            # Indexes will be created on-demand during first upsertion for each vector type
            self.logger.log_operation(
                "s3vector_backend_initialized_with_lazy_index_strategy",
                level="INFO",
                bucket_name=self.config.s3vector_bucket_name,
                vector_types_configured=len(self.config.vector_types)
            )
                
        except Exception as e:
            self.logger.log_error("s3vector_backend_initialization_failed", e)
            raise
    
    def _initialize_opensearch_backend(self) -> None:
        """Initialize OpenSearch backend with S3Vector engine."""
        try:
            # OpenSearch domain with S3VectorsEngine manages S3Vector integration internally
            # No separate S3Vector bucket creation needed - the domain handles this automatically
            
            # Check if OpenSearch domain exists in registry
            opensearch_domains = resource_registry.list_opensearch_domains()
            existing_domain = next((d for d in opensearch_domains if d.get('name') == self.config.opensearch_domain_name and d.get('status') == 'created'), None)

            if existing_domain:
                self.logger.log_operation(
                    "opensearch_domain_found_in_registry",
                    level="INFO",
                    domain_name=self.config.opensearch_domain_name,
                    s3_vectors_enabled=existing_domain.get('s3_vectors_enabled', False)
                )
                # Set as active in registry
                resource_registry.set_active_opensearch_domain(self.config.opensearch_domain_name)
            else:
                # Domain should already exist - this is validation/initialization, not creation
                raise ValidationError(f"OpenSearch domain '{self.config.opensearch_domain_name}' not found in registry. Please create the domain first.")
            
            # Validate domain name is configured
            if not self.config.opensearch_domain_name:
                raise ValidationError("OpenSearch domain name is required")

            # Get domain endpoint for existing domain
            domain_status = self.opensearch_pattern2_manager.get_domain_status(self.config.opensearch_domain_name)
            domain_endpoint = domain_status.get("domain_endpoint")

            if not domain_endpoint:
                raise ValidationError(f"Could not retrieve endpoint for OpenSearch domain '{self.config.opensearch_domain_name}'. Domain status: {domain_status}")

            self.logger.log_operation(
                "opensearch_backend_initialized",
                level="INFO",
                domain_name=self.config.opensearch_domain_name,
                domain_endpoint=domain_endpoint,
                s3_vectors_enabled=True,
                note="OpenSearch domain with S3VectorsEngine manages vector indexes internally"
            )
                
        except Exception as e:
            self.logger.log_error("opensearch_backend_initialization_failed", e)
            raise
    
    def upsert_media_embeddings(
        self,
        embeddings_by_type: Dict[str, List[Dict[str, Any]]],
        media_metadata: MediaMetadata,
        progress_callback: Optional[Callable[[UpsertionProgress], None]] = None
    ) -> UpsertionResult:
        """
        Upsert media embeddings to configured storage backends.
        
        Args:
            embeddings_by_type: Dictionary mapping vector types to embedding data
            media_metadata: Comprehensive metadata for the media file
            progress_callback: Optional callback for progress updates
            
        Returns:
            UpsertionResult with operation details and results
        """
        operation_id = f"upsert_{int(time.time())}_{id(embeddings_by_type)}"
        
        # Calculate total items for progress tracking
        total_items = sum(len(embeddings) for embeddings in embeddings_by_type.values())
        
        # Initialize progress tracking
        progress = UpsertionProgress(
            operation_id=operation_id,
            total_items=total_items,
            current_stage="initializing"
        )
        
        with self._progress_lock:
            self.active_operations[operation_id] = progress
        
        try:
            self.logger.log_operation(
                "starting_media_embeddings_upsert",
                level="INFO",
                operation_id=operation_id,
                total_items=total_items,
                vector_types=list(embeddings_by_type.keys()),
                backends=len(self.config.enabled_backends)
            )
            
            # Update progress
            progress.current_stage = "processing"
            if progress_callback:
                progress_callback(progress)
            
            # Execute upsertion to all configured backends
            backend_results = {}
            
            if StorageBackend.DIRECT_S3VECTOR in self.config.enabled_backends:
                progress.current_stage = "upserting_to_s3vector"
                if progress_callback:
                    progress_callback(progress)
                
                s3vector_result = self._upsert_to_s3vector(
                    embeddings_by_type, media_metadata, progress, progress_callback
                )
                backend_results["s3vector"] = s3vector_result
            
            if StorageBackend.OPENSEARCH_HYBRID in self.config.enabled_backends:
                progress.current_stage = "upserting_to_opensearch"
                if progress_callback:
                    progress_callback(progress)
                
                opensearch_result = self._upsert_to_opensearch(
                    embeddings_by_type, media_metadata, progress, progress_callback
                )
                backend_results["opensearch"] = opensearch_result
            
            # Finalize results
            progress.current_stage = "completed"
            processing_time = time.time() - progress.start_time
            
            result = UpsertionResult(
                operation_id=operation_id,
                success=progress.failed_items == 0,
                total_items=total_items,
                successful_items=progress.successful_items,
                failed_items=progress.failed_items,
                processing_time_seconds=processing_time,
                s3vector_results=backend_results.get("s3vector"),
                opensearch_results=backend_results.get("opensearch"),
                error_summary=progress.error_messages,
                metadata={
                    "media_file": media_metadata.file_name,
                    "vector_types": list(embeddings_by_type.keys()),
                    "backends_used": [b.value for b in self.config.enabled_backends]
                }
            )
            
            if progress_callback:
                progress_callback(progress)
            
            self.logger.log_operation(
                "media_embeddings_upsert_completed",
                level="INFO",
                operation_id=operation_id,
                success=result.success,
                processing_time_seconds=processing_time,
                successful_items=result.successful_items,
                failed_items=result.failed_items
            )
            
            return result
            
        except Exception as e:
            progress.current_stage = "failed"
            progress.error_messages.append(str(e))
            
            if progress_callback:
                progress_callback(progress)
            
            self.logger.log_error("media_embeddings_upsert_failed", e, operation_id=operation_id)
            
            return UpsertionResult(
                operation_id=operation_id,
                success=False,
                total_items=total_items,
                successful_items=progress.successful_items,
                failed_items=total_items,
                processing_time_seconds=time.time() - progress.start_time,
                error_summary=[str(e)]
            )
        
        finally:
            # Cleanup progress tracking after delay
            self._schedule_progress_cleanup(operation_id)
    
    def _upsert_to_s3vector(
        self,
        embeddings_by_type: Dict[str, List[Dict[str, Any]]],
        media_metadata: MediaMetadata,
        progress: UpsertionProgress,
        progress_callback: Optional[Callable[[UpsertionProgress], None]] = None
    ) -> Dict[str, Any]:
        """Upsert embeddings to S3Vector backend."""
        results = {}
        
        for vector_type_str, embeddings in embeddings_by_type.items():
            try:
                vector_type = VectorType(vector_type_str)
                index_config = self.index_configurations[vector_type]
                index_name = index_config.get_s3vector_index_name(self.config.environment)
                
                # Prepare vectors for S3Vector format
                vectors_data = []
                for i, embedding_data in enumerate(embeddings):
                    vector_key = f"{media_metadata.file_name}_{vector_type_str}_segment_{i}"
                    
                    vector_data = {
                        "key": vector_key,
                        "data": {
                            "float32": embedding_data["embedding"]
                        },
                        "metadata": {
                            # S3 Vectors has a 10-key limit, so we need to be selective
                            "file_name": media_metadata.file_name,
                            "duration": media_metadata.duration_seconds,
                            "format": media_metadata.file_format,
                            "timestamp": media_metadata.processing_timestamp,
                            "model": media_metadata.embedding_model,
                            "segments": media_metadata.segment_count,
                            "category": getattr(media_metadata, 'content_category', 'video') or "video",
                            "segment_id": i,
                            "vector_type": vector_type_str,
                            "s3_location": media_metadata.s3_storage_location
                        }
                    }
                    vectors_data.append(vector_data)
                
                # Get index ARN for upsertion using pooled STS client
                try:
                    from src.config.unified_config_manager import get_unified_config_manager
                    
                    config_manager = get_unified_config_manager()
                    region = config_manager.config.aws.region
                    sts_client = get_pooled_client(AWSService.STS)
                    account_id = sts_client.get_caller_identity()['Account']
                    index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{self.config.s3vector_bucket_name}/index/{index_name}"
                    
                except Exception as e:
                    self.logger.log_error("failed_to_construct_index_arn", e)
                    raise
                
                # Ensure bucket name is available
                if not self.config.s3vector_bucket_name:
                    raise ValidationError("S3Vector bucket name is required for upsertion")
                
                # UPDATED: Use lazy index creation during upsertion
                # This will create the index automatically if it doesn't exist
                upsert_result = self.s3vector_manager.put_vectors_with_lazy_index_creation(
                    bucket_name=self.config.s3vector_bucket_name,
                    index_name=index_name,
                    vectors_data=vectors_data,
                    dimensions=index_config.dimensions,
                    distance_metric=index_config.distance_metric
                )
                
                # Construct index ARN for results (needed for tracking)
                try:
                    from src.config.unified_config_manager import get_unified_config_manager
                    config_manager = get_unified_config_manager()
                    region = config_manager.config.aws.region
                    sts_client = get_pooled_client(AWSService.STS)
                    account_id = sts_client.get_caller_identity()['Account']
                    index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{self.config.s3vector_bucket_name}/index/{index_name}"
                except Exception as e:
                    # Use a placeholder ARN if construction fails
                    index_arn = f"bucket/{self.config.s3vector_bucket_name}/index/{index_name}"
                
                results[vector_type_str] = {
                    "index_arn": index_arn,
                    "index_name": index_name,
                    "vectors_stored": len(vectors_data),
                    "result": upsert_result,
                    "index_created_on_demand": upsert_result.get("index_created_on_demand", False)
                }
                
                # Update progress
                progress.processed_items += len(embeddings)
                progress.successful_items += len(embeddings)
                
                if progress_callback:
                    progress_callback(progress)
                
            except Exception as e:
                error_msg = f"S3Vector upsert failed for {vector_type_str}: {str(e)}"
                progress.error_messages.append(error_msg)
                progress.failed_items += len(embeddings)
                
                self.logger.log_error("s3vector_upsert_failed", Exception(error_msg))
                
                results[vector_type_str] = {
                    "error": error_msg,
                    "vectors_failed": len(embeddings)
                }
        
        return results
    
    def _upsert_to_opensearch(
        self,
        embeddings_by_type: Dict[str, List[Dict[str, Any]]],
        media_metadata: MediaMetadata,
        progress: UpsertionProgress,
        progress_callback: Optional[Callable[[UpsertionProgress], None]] = None
    ) -> Dict[str, Any]:
        """Upsert embeddings to OpenSearch hybrid backend."""
        results = {}
        opensearch_metadata = transform_metadata_for_opensearch(media_metadata)
        
        # Get domain endpoint
        try:
            if not self.config.opensearch_domain_name:
                raise ValidationError("OpenSearch domain name is required")
                
            domain_status = self.opensearch_pattern2_manager.get_domain_status(
                self.config.opensearch_domain_name
            )
            domain_endpoint = domain_status["domain_endpoint"]
            
        except Exception as e:
            error_msg = f"Failed to get OpenSearch domain endpoint: {str(e)}"
            progress.error_messages.append(error_msg)
            return {"error": error_msg}
        
        for vector_type_str, embeddings in embeddings_by_type.items():
            try:
                vector_type = VectorType(vector_type_str)
                index_config = self.index_configurations[vector_type]
                index_name = index_config.get_opensearch_index_name(self.config.environment)
                
                # Prepare documents for OpenSearch
                documents = []
                for i, embedding_data in enumerate(embeddings):
                    document_id = f"{media_metadata.file_name}_{vector_type_str}_segment_{i}"
                    
                    document = {
                        "embedding": embedding_data["embedding"],
                        "title": media_metadata.file_name,
                        "content": f"Segment {i} from {media_metadata.file_name}",
                        "file_name": media_metadata.file_name,
                        "duration": media_metadata.duration_seconds,
                        "timestamp": media_metadata.processing_timestamp,
                        "metadata": {
                            **opensearch_metadata,
                            "segment_id": i,
                            "vector_type": vector_type_str
                        }
                    }
                    documents.append((document_id, document))
                
                # Index documents to OpenSearch
                indexed_count = 0
                for document_id, document in documents:
                    try:
                        import requests
                        import boto3
                        
                        try:
                            from requests_aws4auth import AWS4Auth
                            # AWS authentication
                            credentials = boto3.Session().get_credentials()
                            awsauth = AWS4Auth(
                                credentials.access_key,
                                credentials.secret_key,
                                self.opensearch_pattern2_manager.region_name,
                                'es',
                                session_token=credentials.token
                            )
                        except ImportError:
                            # Fallback to no auth if AWS4Auth not available
                            awsauth = None
                            self.logger.log_operation(
                                "aws4auth_not_available_using_fallback",
                                level="WARNING"
                            )
                        
                        url = f"https://{domain_endpoint}/{index_name}/_doc/{document_id}"
                        response = requests.put(
                            url,
                            json=document,
                            auth=awsauth,
                            headers={"Content-Type": "application/json"},
                            timeout=30
                        )
                        
                        if response.status_code in [200, 201]:
                            indexed_count += 1
                        else:
                            self.logger.log_error(
                                "opensearch_document_index_failed",
                                Exception(f"Status: {response.status_code}, Response: {response.text}")
                            )
                            
                    except Exception as doc_error:
                        self.logger.log_error("opensearch_document_error", doc_error)
                
                results[vector_type_str] = {
                    "index_name": index_name,
                    "documents_indexed": indexed_count,
                    "documents_failed": len(documents) - indexed_count
                }
                
                # Update progress
                progress.processed_items += len(embeddings)
                progress.successful_items += indexed_count
                progress.failed_items += (len(embeddings) - indexed_count)
                
                if progress_callback:
                    progress_callback(progress)
                
            except Exception as e:
                error_msg = f"OpenSearch upsert failed for {vector_type_str}: {str(e)}"
                progress.error_messages.append(error_msg)
                progress.failed_items += len(embeddings)
                
                self.logger.log_error("opensearch_upsert_failed", Exception(error_msg))
                
                results[vector_type_str] = {
                    "error": error_msg,
                    "documents_failed": len(embeddings)
                }
        
        return results
    
    def batch_upsert_media_embeddings(
        self,
        batch_data: List[Tuple[Dict[str, List[Dict[str, Any]]], MediaMetadata]],
        progress_callback: Optional[Callable[[UpsertionProgress], None]] = None
    ) -> List[UpsertionResult]:
        """
        Batch upsert multiple media files' embeddings.
        
        Args:
            batch_data: List of (embeddings_by_type, media_metadata) tuples
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of UpsertionResult objects
        """
        operation_id = f"batch_upsert_{int(time.time())}_{len(batch_data)}"
        
        # Calculate total items
        total_items = sum(
            sum(len(embeddings) for embeddings in embeddings_by_type.values())
            for embeddings_by_type, _ in batch_data
        )
        
        # Initialize progress tracking
        progress = UpsertionProgress(
            operation_id=operation_id,
            total_items=total_items,
            current_stage="batch_processing"
        )
        
        with self._progress_lock:
            self.active_operations[operation_id] = progress
        
        try:
            self.logger.log_operation(
                "starting_batch_upsert",
                level="INFO",
                operation_id=operation_id,
                batch_size=len(batch_data),
                total_items=total_items
            )
            
            results = []
            
            # Process in batches to manage resources
            batch_size = self.config.batch_size
            for i in range(0, len(batch_data), batch_size):
                batch_chunk = batch_data[i:i + batch_size]
                
                # Process batch chunk concurrently
                chunk_futures = []
                with ThreadPoolExecutor(max_workers=min(len(batch_chunk), self.config.max_concurrent_operations)) as executor:
                    for embeddings_by_type, media_metadata in batch_chunk:
                        future = executor.submit(
                            self.upsert_media_embeddings,
                            embeddings_by_type,
                            media_metadata,
                            progress_callback
                        )
                        chunk_futures.append(future)
                    
                    # Collect results
                    for future in as_completed(chunk_futures):
                        try:
                            result = future.result()
                            results.append(result)
                        except Exception as e:
                            self.logger.log_error("batch_chunk_processing_failed", e)
                            # Create error result
                            error_result = UpsertionResult(
                                operation_id=f"{operation_id}_error_{len(results)}",
                                success=False,
                                total_items=0,
                                successful_items=0,
                                failed_items=0,
                                processing_time_seconds=0,
                                error_summary=[str(e)]
                            )
                            results.append(error_result)
            
            return results
            
        except Exception as e:
            self.logger.log_error("batch_upsert_failed", e)
            return []
        
        finally:
            # Cleanup progress tracking
            self._schedule_progress_cleanup(operation_id)
    
    def _schedule_progress_cleanup(self, operation_id: str, delay_seconds: int = 300) -> None:
        """Schedule cleanup of progress tracking after delay."""
        def cleanup():
            time.sleep(delay_seconds)
            with self._progress_lock:
                if operation_id in self.active_operations:
                    del self.active_operations[operation_id]
                    self.logger.log_operation(
                        "progress_tracking_cleaned_up",
                        level="DEBUG",
                        operation_id=operation_id
                    )
        
        # Run cleanup in background thread
        import threading
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()
    
    def get_operation_progress(self, operation_id: str) -> Optional[UpsertionProgress]:
        """Get progress information for an active operation."""
        with self._progress_lock:
            return self.active_operations.get(operation_id)
    
    def list_active_operations(self) -> List[str]:
        """List all active operation IDs."""
        with self._progress_lock:
            return list(self.active_operations.keys())
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive storage statistics."""
        stats = {
            "configuration": {
                "enabled_backends": [b.value for b in self.config.enabled_backends],
                "vector_types": [vt.value for vt in self.config.vector_types],
                "environment": self.config.environment
            },
            "active_operations": len(self.active_operations),
            "backend_status": {}
        }
        
        # S3Vector backend stats
        if StorageBackend.DIRECT_S3VECTOR in self.config.enabled_backends:
            try:
                s3vector_stats = self.s3vector_manager.get_multi_index_stats()
                stats["backend_status"]["s3vector"] = {
                    "status": "active",
                    "bucket_name": self.config.s3vector_bucket_name,
                    "indexes": s3vector_stats
                }
            except Exception as e:
                stats["backend_status"]["s3vector"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # OpenSearch backend stats
        if StorageBackend.OPENSEARCH_HYBRID in self.config.enabled_backends:
            try:
                if self.config.opensearch_domain_name:
                    domain_status = self.opensearch_pattern2_manager.get_domain_status(
                        self.config.opensearch_domain_name
                    )
                    stats["backend_status"]["opensearch"] = {
                        "status": "active",
                        "domain_name": self.config.opensearch_domain_name,
                        "domain_status": domain_status
                    }
            except Exception as e:
                stats["backend_status"]["opensearch"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return stats
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate current storage configuration using resource registry."""
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "backend_checks": {},
            "registry_validation": {}
        }
        
        try:
            # Validate basic configuration
            self.config.validate()
            
            # Check S3Vector backend with registry validation
            if StorageBackend.DIRECT_S3VECTOR in self.config.enabled_backends:
                try:
                    if self.config.s3vector_bucket_name:
                        # Check if bucket exists in registry
                        vector_buckets = resource_registry.list_vector_buckets()
                        registry_bucket = next((b for b in vector_buckets if b.get('name') == self.config.s3vector_bucket_name), None)
                        
                        if registry_bucket:
                            if registry_bucket.get('status') == 'created':
                                validation_results["backend_checks"]["s3vector"] = {
                                    "bucket_exists": True,
                                    "bucket_name": self.config.s3vector_bucket_name,
                                    "registry_status": "found_active",
                                    "region": registry_bucket.get('region'),
                                    "created_at": registry_bucket.get('created_at')
                                }
                                validation_results["registry_validation"]["s3vector_bucket"] = {
                                    "found": True,
                                    "status": registry_bucket.get('status'),
                                    "resource_info": registry_bucket
                                }
                            else:
                                validation_results["warnings"].append(f"S3Vector bucket '{self.config.s3vector_bucket_name}' found in registry but marked as {registry_bucket.get('status')}")
                                validation_results["backend_checks"]["s3vector"] = {
                                    "bucket_exists": False,
                                    "registry_status": registry_bucket.get('status')
                                }
                        else:
                            # Not in registry, check if it exists in AWS
                            bucket_exists = self.s3vector_manager.bucket_exists(self.config.s3vector_bucket_name)
                            validation_results["backend_checks"]["s3vector"] = {
                                "bucket_exists": bucket_exists,
                                "bucket_name": self.config.s3vector_bucket_name,
                                "registry_status": "not_found"
                            }
                            validation_results["warnings"].append(f"S3Vector bucket '{self.config.s3vector_bucket_name}' not found in registry")
                            
                        # Validate associated indexes
                        indexes = resource_registry.list_indexes()
                        bucket_indexes = [idx for idx in indexes if idx.get('bucket') == self.config.s3vector_bucket_name and idx.get('status') == 'created']
                        validation_results["registry_validation"]["s3vector_indexes"] = {
                            "count": len(bucket_indexes),
                            "indexes": bucket_indexes
                        }
                        
                    else:
                        validation_results["errors"].append("S3Vector bucket name not configured")
                        validation_results["valid"] = False
                        
                except Exception as e:
                    validation_results["backend_checks"]["s3vector"] = {
                        "error": str(e)
                    }
                    validation_results["warnings"].append(f"S3Vector validation failed: {str(e)}")
            
            # Check OpenSearch backend with registry validation
            if StorageBackend.OPENSEARCH_HYBRID in self.config.enabled_backends:
                try:
                    if self.config.opensearch_domain_name:
                        # Check if domain exists in registry
                        opensearch_domains = resource_registry.list_opensearch_domains()
                        registry_domain = next((d for d in opensearch_domains if d.get('name') == self.config.opensearch_domain_name), None)
                        
                        if registry_domain:
                            if registry_domain.get('status') == 'created':
                                validation_results["backend_checks"]["opensearch"] = {
                                    "domain_exists": True,
                                    "domain_name": self.config.opensearch_domain_name,
                                    "registry_status": "found_active",
                                    "region": registry_domain.get('region'),
                                    "engine_version": registry_domain.get('engine_version'),
                                    "arn": registry_domain.get('arn')
                                }
                                validation_results["registry_validation"]["opensearch_domain"] = {
                                    "found": True,
                                    "status": registry_domain.get('status'),
                                    "resource_info": registry_domain
                                }
                                
                                # Try to get actual domain status
                                try:
                                    domain_status = self.opensearch_pattern2_manager.get_domain_status(
                                        self.config.opensearch_domain_name
                                    )
                                    validation_results["backend_checks"]["opensearch"]["aws_status"] = domain_status
                                except Exception as aws_error:
                                    validation_results["warnings"].append(f"Could not verify AWS status for domain: {str(aws_error)}")
                                    
                            else:
                                validation_results["warnings"].append(f"OpenSearch domain '{self.config.opensearch_domain_name}' found in registry but marked as {registry_domain.get('status')}")
                                validation_results["backend_checks"]["opensearch"] = {
                                    "domain_exists": False,
                                    "registry_status": registry_domain.get('status')
                                }
                        else:
                            # Not in registry, check if it exists in AWS
                            try:
                                domain_status = self.opensearch_pattern2_manager.get_domain_status(
                                    self.config.opensearch_domain_name
                                )
                                validation_results["backend_checks"]["opensearch"] = {
                                    "domain_exists": True,
                                    "domain_name": self.config.opensearch_domain_name,
                                    "registry_status": "not_found",
                                    "status": domain_status
                                }
                                validation_results["warnings"].append(f"OpenSearch domain '{self.config.opensearch_domain_name}' exists in AWS but not found in registry")
                            except Exception as e:
                                validation_results["backend_checks"]["opensearch"] = {
                                    "domain_exists": False,
                                    "registry_status": "not_found",
                                    "error": str(e)
                                }
                                validation_results["warnings"].append(f"OpenSearch domain '{self.config.opensearch_domain_name}' not found in registry or AWS")
                        
                        # Validate associated indexes and pipelines
                        opensearch_indexes = resource_registry.list_opensearch_indexes()
                        opensearch_pipelines = resource_registry.list_opensearch_pipelines()
                        
                        validation_results["registry_validation"]["opensearch_indexes"] = {
                            "count": len(opensearch_indexes),
                            "indexes": opensearch_indexes
                        }
                        validation_results["registry_validation"]["opensearch_pipelines"] = {
                            "count": len(opensearch_pipelines),
                            "pipelines": opensearch_pipelines
                        }
                        
                    else:
                        validation_results["errors"].append("OpenSearch domain name not configured")
                        validation_results["valid"] = False
                        
                except Exception as e:
                    validation_results["backend_checks"]["opensearch"] = {
                        "error": str(e)
                    }
                    validation_results["warnings"].append(f"OpenSearch validation failed: {str(e)}")
            
            # Add registry summary
            validation_results["registry_validation"]["summary"] = {
                "total_vector_buckets": len(resource_registry.list_vector_buckets()),
                "active_vector_buckets": len([b for b in resource_registry.list_vector_buckets() if b.get('status') == 'created']),
                "total_opensearch_domains": len(resource_registry.list_opensearch_domains()),
                "active_opensearch_domains": len([d for d in resource_registry.list_opensearch_domains() if d.get('status') == 'created']),
                "active_resources": resource_registry.get_active_resources()
            }
            
        except ValidationError as e:
            validation_results["valid"] = False
            validation_results["errors"].append(str(e))
        except Exception as e:
            validation_results["valid"] = False
            validation_results["errors"].append(f"Unexpected validation error: {str(e)}")
        
        return validation_results
    
    def shutdown(self) -> None:
        """Shutdown the storage integration manager."""
        self.logger.log_operation("shutting_down_storage_integration_manager", level="INFO")
        
        # Wait for active operations to complete
        timeout = 30  # seconds
        start_time = time.time()
        
        while self.active_operations and (time.time() - start_time) < timeout:
            time.sleep(1)
            self.logger.log_operation(
                "waiting_for_operations_to_complete",
                level="DEBUG",
                active_count=len(self.active_operations)
            )
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        # Clear active operations
        with self._progress_lock:
            self.active_operations.clear()
        
        self.logger.log_operation("storage_integration_manager_shutdown_completed", level="INFO")