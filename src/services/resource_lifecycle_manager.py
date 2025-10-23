"""
Resource Lifecycle Manager

Manages the complete lifecycle of AWS resources with async status tracking,
including creation, deletion, and state polling.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
import boto3
from botocore.exceptions import ClientError

from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry
from src.utils.aws_clients import aws_client_factory
from src.config.unified_config_manager import get_unified_config_manager
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_integration import OpenSearchIntegrationManager

logger = get_logger(__name__)


class ResourceState(str, Enum):
    """Resource lifecycle states."""
    CREATING = "CREATING"
    ACTIVE = "ACTIVE"
    AVAILABLE = "AVAILABLE"  # For OpenSearch domains
    DELETING = "DELETING"
    DELETED = "DELETED"
    FAILED = "FAILED"
    NOT_FOUND = "NOT_FOUND"


class ResourceType(str, Enum):
    """Supported resource types."""
    MEDIA_BUCKET = "media_bucket"
    VECTOR_BUCKET = "vector_bucket"
    VECTOR_INDEX = "vector_index"
    OPENSEARCH_DOMAIN = "opensearch_domain"
    OPENSEARCH_COLLECTION = "opensearch_collection"


@dataclass
class ResourceStatus:
    """Resource status information."""
    resource_id: str
    resource_type: ResourceType
    state: ResourceState
    arn: Optional[str] = None
    region: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    progress_percentage: int = 0
    estimated_time_remaining: Optional[int] = None  # seconds


class ResourceLifecycleManager:
    """
    Manages AWS resource lifecycle with async status tracking.
    
    Features:
    - Async resource creation with status polling
    - Async resource deletion with status polling
    - Real-time state tracking
    - Timeout handling
    - Error recovery
    """
    
    def __init__(self):
        """Initialize the resource lifecycle manager."""
        self.s3_utils = S3BucketUtilityService()
        self.s3vector_manager = S3VectorStorageManager()
        self.opensearch_manager = OpenSearchIntegrationManager()
        
        config_manager = get_unified_config_manager()
        self.region = config_manager.config.aws.region
        
        # AWS clients
        self.s3_client = aws_client_factory.get_s3_client()
        self.s3vectors_client = aws_client_factory.get_s3vectors_client()
        self.opensearch_client = aws_client_factory.get_opensearch_client()
        
        # Timeout configurations (in seconds)
        self.timeouts = {
            ResourceType.MEDIA_BUCKET: 60,  # S3 buckets are usually instant
            ResourceType.VECTOR_BUCKET: 120,  # S3 Vector buckets may take longer
            ResourceType.VECTOR_INDEX: 300,  # Indices can take a few minutes
            ResourceType.OPENSEARCH_DOMAIN: 600,  # OpenSearch domains take 5-10 minutes
            ResourceType.OPENSEARCH_COLLECTION: 300,  # Collections take a few minutes
        }
    
    # ==================== Media Bucket Operations ====================
    
    def create_media_bucket(self, bucket_name: str) -> ResourceStatus:
        """
        Create a standard S3 bucket for media storage.
        
        Args:
            bucket_name: Name of the bucket to create
            
        Returns:
            ResourceStatus with creation result
        """
        logger.info(f"Creating media bucket: {bucket_name}")
        
        try:
            result = self.s3_utils.create_bucket(bucket_name, region=self.region)
            
            state = ResourceState.ACTIVE if result["status"] in ["created", "already_exists"] else ResourceState.FAILED
            
            # Get bucket ARN
            arn = f"arn:aws:s3:::{result['bucket_name']}"
            
            status = ResourceStatus(
                resource_id=result["bucket_name"],
                resource_type=ResourceType.MEDIA_BUCKET,
                state=state,
                arn=arn,
                region=result["region"],
                created_at=datetime.now(timezone.utc),
                metadata={
                    "original_name": result.get("original_name"),
                    "status": result["status"]
                },
                progress_percentage=100 if state == ResourceState.ACTIVE else 0
            )
            
            if state == ResourceState.FAILED:
                status.error_message = result.get("error_code", "Unknown error")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to create media bucket: {e}")
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.MEDIA_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def delete_media_bucket(self, bucket_name: str, force_empty: bool = False) -> ResourceStatus:
        """
        Delete a media bucket.
        
        Args:
            bucket_name: Name of the bucket to delete
            force_empty: Whether to empty the bucket before deletion
            
        Returns:
            ResourceStatus with deletion result
        """
        logger.info(f"Deleting media bucket: {bucket_name}")
        
        try:
            result = self.s3_utils.delete_bucket(bucket_name, force_empty=force_empty)
            
            state = ResourceState.DELETED if result["status"] in ["deleted", "not_found"] else ResourceState.FAILED
            
            status = ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.MEDIA_BUCKET,
                state=state,
                metadata=result,
                progress_percentage=100 if state == ResourceState.DELETED else 0
            )
            
            if state == ResourceState.FAILED:
                status.error_message = result.get("message", "Deletion failed")
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to delete media bucket: {e}")
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.MEDIA_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def get_media_bucket_status(self, bucket_name: str) -> ResourceStatus:
        """Get current status of a media bucket."""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.MEDIA_BUCKET,
                state=ResourceState.ACTIVE,
                arn=f"arn:aws:s3:::{bucket_name}",
                region=self.region,
                progress_percentage=100
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket"):
                return ResourceStatus(
                    resource_id=bucket_name,
                    resource_type=ResourceType.MEDIA_BUCKET,
                    state=ResourceState.NOT_FOUND,
                    progress_percentage=0
                )
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.MEDIA_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    # ==================== Vector Bucket Operations ====================
    
    def create_vector_bucket(self, bucket_name: str, encryption_type: str = "SSE-S3",
                           kms_key_arn: Optional[str] = None) -> ResourceStatus:
        """
        Create an S3 Vector bucket.
        
        Args:
            bucket_name: Name of the vector bucket
            encryption_type: Encryption type
            kms_key_arn: KMS key ARN if using SSE-KMS
            
        Returns:
            ResourceStatus with creation result
        """
        logger.info(f"Creating vector bucket: {bucket_name}")
        
        try:
            result = self.s3vector_manager.create_vector_bucket(
                bucket_name=bucket_name,
                encryption_type=encryption_type,
                kms_key_arn=kms_key_arn
            )
            
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=ResourceState.ACTIVE,
                arn=result.get("bucket_arn"),
                region=self.region,
                created_at=datetime.now(timezone.utc),
                metadata=result,
                progress_percentage=100
            )
            
        except Exception as e:
            logger.error(f"Failed to create vector bucket: {e}")
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    def delete_vector_bucket(self, bucket_name: str, cascade: bool = True) -> ResourceStatus:
        """
        Delete an S3 Vector bucket.

        Args:
            bucket_name: Name of the vector bucket to delete
            cascade: If True, delete all indexes in the bucket first (default: True)

        Returns:
            ResourceStatus with deletion result
        """
        logger.info(f"Deleting vector bucket: {bucket_name}")

        try:
            # Use the S3VectorStorageManager's delete method which handles cascade deletion
            result = self.s3vector_manager.delete_vector_bucket(
                bucket_name=bucket_name,
                cascade=cascade
            )

            # Check if deletion was successful
            if result.get("status") in ["deleted", "not_found"]:
                state = ResourceState.DELETED
                progress = 100
                error_msg = None
            else:
                state = ResourceState.FAILED
                progress = 0
                error_msg = result.get("message", "Deletion failed")

            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=state,
                progress_percentage=progress,
                error_message=error_msg,
                metadata=result
            )

        except Exception as e:
            logger.error(f"Failed to delete vector bucket: {e}")
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    def get_vector_bucket_status(self, bucket_name: str) -> ResourceStatus:
        """Get current status of a vector bucket."""
        try:
            response = self.s3vectors_client.list_buckets()
            buckets = response.get('Buckets', [])

            for bucket in buckets:
                if bucket.get('Name') == bucket_name:
                    return ResourceStatus(
                        resource_id=bucket_name,
                        resource_type=ResourceType.VECTOR_BUCKET,
                        state=ResourceState.ACTIVE,
                        arn=bucket.get('Arn'),
                        region=self.region,
                        progress_percentage=100
                    )

            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=ResourceState.NOT_FOUND,
                progress_percentage=0
            )

        except Exception as e:
            logger.error(f"Failed to get vector bucket status: {e}")
            return ResourceStatus(
                resource_id=bucket_name,
                resource_type=ResourceType.VECTOR_BUCKET,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    # ==================== OpenSearch Domain Operations ====================

    def create_opensearch_domain(self, domain_name: str, instance_type: str = "or1.medium.search",
                                instance_count: int = 1) -> ResourceStatus:
        """
        Create an OpenSearch domain with S3 Vectors engine enabled (async operation).

        This creates an OpenSearch domain configured to use S3 Vectors as the storage engine,
        enabling hybrid search capabilities with cost-effective vector storage.

        Args:
            domain_name: Name of the domain (max 28 characters)
            instance_type: Instance type (default: or1.medium.search - required for S3 Vectors)
            instance_count: Number of instances

        Returns:
            ResourceStatus with initial creation state

        Note:
            - Requires OpenSearch 2.19+ for S3 Vectors engine support
            - Requires OR1 instance types (OpenSearch Optimized)
            - Requires minimum 20GB EBS volume for OR1 instances
            - Encryption at rest is required for OR1 instances
        """
        logger.info(f"Creating OpenSearch domain with S3 Vectors engine: {domain_name}")

        try:
            # Create domain using OpenSearch API with S3 Vectors engine enabled
            response = self.opensearch_client.create_domain(
                DomainName=domain_name,
                EngineVersion='OpenSearch_2.19',  # Minimum version for S3 Vectors
                ClusterConfig={
                    'InstanceType': instance_type,  # OR1 instances required for S3 Vectors
                    'InstanceCount': instance_count,
                    'DedicatedMasterEnabled': False,
                    'ZoneAwarenessEnabled': False
                },
                EBSOptions={
                    'EBSEnabled': True,
                    'VolumeType': 'gp3',
                    'VolumeSize': 20,  # OR1 requires minimum 20GB
                    'Iops': 3000
                },
                EncryptionAtRestOptions={
                    'Enabled': True  # Required for OR1 instances
                },
                AIMLOptions={
                    'S3VectorsEngine': {
                        'Enabled': True  # Enable S3 Vectors as storage engine
                    }
                },
                AccessPolicies='',  # Will be configured later
            )

            domain_status = response.get('DomainStatus', {})
            arn = domain_status.get('ARN')

            # Log to registry with S3 Vectors enabled
            resource_registry.log_opensearch_domain_created(
                domain_name=domain_name,
                domain_arn=arn,
                region=self.region,
                engine_version='OpenSearch_2.19',
                s3_vectors_enabled=True,  # S3 Vectors engine is enabled
                source="lifecycle_manager"
            )

            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=ResourceState.CREATING,
                arn=arn,
                region=self.region,
                created_at=datetime.now(timezone.utc),
                metadata=domain_status,
                progress_percentage=10,
                estimated_time_remaining=600  # 10 minutes estimate
            )

        except Exception as e:
            logger.error(f"Failed to create OpenSearch domain: {e}")
            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    def delete_opensearch_domain(self, domain_name: str) -> ResourceStatus:
        """Delete an OpenSearch domain (async operation)."""
        logger.info(f"Deleting OpenSearch domain: {domain_name}")

        try:
            self.opensearch_client.delete_domain(DomainName=domain_name)

            # Note: OpenSearch deletion is async, so we return DELETING state
            # The registry will be updated when get_opensearch_domain_status confirms deletion
            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=ResourceState.DELETING,
                progress_percentage=10,
                estimated_time_remaining=300  # 5 minutes estimate
            )

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ResourceNotFoundException":
                # Domain already deleted, update registry
                try:
                    resource_registry.log_opensearch_domain_deleted(domain_name=domain_name)
                except Exception as reg_err:
                    logger.warning(f"Failed to update registry after OpenSearch domain not found {domain_name}: {reg_err}")

                return ResourceStatus(
                    resource_id=domain_name,
                    resource_type=ResourceType.OPENSEARCH_DOMAIN,
                    state=ResourceState.DELETED,
                    progress_percentage=100
                )
            logger.error(f"Failed to delete OpenSearch domain: {e}")
            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    def get_opensearch_domain_status(self, domain_name: str) -> ResourceStatus:
        """Get current status of an OpenSearch domain."""
        try:
            response = self.opensearch_client.describe_domain(DomainName=domain_name)
            domain_status = response.get('DomainStatus', {})

            processing = domain_status.get('Processing', False)
            created = domain_status.get('Created', False)
            deleted = domain_status.get('Deleted', False)

            # Determine state
            if deleted:
                state = ResourceState.DELETED
                progress = 100
                # Update registry when we confirm deletion
                try:
                    resource_registry.log_opensearch_domain_deleted(domain_name=domain_name)
                except Exception as e:
                    logger.warning(f"Failed to update registry after confirming OpenSearch domain deletion {domain_name}: {e}")
            elif processing:
                state = ResourceState.CREATING
                progress = 50  # Estimate
            elif created:
                state = ResourceState.AVAILABLE
                progress = 100
            else:
                state = ResourceState.CREATING
                progress = 25

            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=state,
                arn=domain_status.get('ARN'),
                region=self.region,
                metadata=domain_status,
                progress_percentage=progress
            )

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ResourceNotFoundException":
                # Domain not found - update registry to remove it
                try:
                    resource_registry.log_opensearch_domain_deleted(domain_name=domain_name)
                except Exception as reg_err:
                    logger.warning(f"Failed to update registry after OpenSearch domain not found {domain_name}: {reg_err}")

                return ResourceStatus(
                    resource_id=domain_name,
                    resource_type=ResourceType.OPENSEARCH_DOMAIN,
                    state=ResourceState.NOT_FOUND,
                    progress_percentage=0
                )
            logger.error(f"Failed to get OpenSearch domain status: {e}")
            return ResourceStatus(
                resource_id=domain_name,
                resource_type=ResourceType.OPENSEARCH_DOMAIN,
                state=ResourceState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )

    # ==================== Generic Status Polling ====================

    def poll_resource_status(self, resource_type: ResourceType, resource_id: str,
                            timeout: Optional[int] = None) -> ResourceStatus:
        """
        Poll resource status until it reaches a terminal state or timeout.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            timeout: Timeout in seconds (uses default if not provided)

        Returns:
            Final ResourceStatus
        """
        timeout = timeout or self.timeouts.get(resource_type, 300)
        start_time = time.time()
        poll_interval = 5  # seconds

        while time.time() - start_time < timeout:
            status = self.get_resource_status(resource_type, resource_id)

            # Check if terminal state reached
            if status.state in [ResourceState.ACTIVE, ResourceState.AVAILABLE,
                              ResourceState.DELETED, ResourceState.FAILED,
                              ResourceState.NOT_FOUND]:
                return status

            # Update estimated time remaining
            elapsed = time.time() - start_time
            status.estimated_time_remaining = max(0, int(timeout - elapsed))

            time.sleep(poll_interval)

        # Timeout reached
        status = self.get_resource_status(resource_type, resource_id)
        if status.state not in [ResourceState.ACTIVE, ResourceState.AVAILABLE, ResourceState.DELETED]:
            status.error_message = f"Operation timed out after {timeout} seconds"

        return status

    def get_resource_status(self, resource_type: ResourceType, resource_id: str) -> ResourceStatus:
        """Get current status of any resource type."""
        if resource_type == ResourceType.MEDIA_BUCKET:
            return self.get_media_bucket_status(resource_id)
        elif resource_type == ResourceType.VECTOR_BUCKET:
            return self.get_vector_bucket_status(resource_id)
        elif resource_type == ResourceType.OPENSEARCH_DOMAIN:
            return self.get_opensearch_domain_status(resource_id)
        else:
            return ResourceStatus(
                resource_id=resource_id,
                resource_type=resource_type,
                state=ResourceState.FAILED,
                error_message=f"Unsupported resource type: {resource_type}",
                progress_percentage=0
            )

