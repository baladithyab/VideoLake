"""
OpenSearch Provider Implementation

Implements the VectorStoreProvider interface for Amazon OpenSearch Service.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from botocore.exceptions import ClientError

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreType,
    VectorStoreState,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreProviderFactory
)
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.aws_clients import aws_client_factory
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


class OpenSearchProvider(VectorStoreProvider):
    """OpenSearch implementation of the vector store provider."""
    
    def __init__(self):
        """Initialize the OpenSearch provider."""
        self.opensearch_manager = OpenSearchIntegrationManager()
        self.opensearch_client = aws_client_factory.get_opensearch_client()
        
        config_manager = get_unified_config_manager()
        self.region = config_manager.config.aws.region
    
    @property
    def store_type(self) -> VectorStoreType:
        """Return OPENSEARCH as the store type."""
        return VectorStoreType.OPENSEARCH
    
    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new OpenSearch domain.
        
        Args:
            config: Configuration for the OpenSearch domain
            
        Returns:
            VectorStoreStatus with creation result
        """
        self.validate_config(config)
        
        try:
            # Extract OpenSearch-specific config
            os_config = config.opensearch_config or {}
            instance_type = os_config.get("instance_type", "t3.small.search")
            instance_count = os_config.get("instance_count", 1)
            ebs_volume_size = os_config.get("ebs_volume_size", 10)
            engine_version = os_config.get("engine_version", "OpenSearch_2.11")
            
            # Create domain
            response = self.opensearch_client.create_domain(
                DomainName=config.name,
                ClusterConfig={
                    'InstanceType': instance_type,
                    'InstanceCount': instance_count,
                    'DedicatedMasterEnabled': False,
                    'ZoneAwarenessEnabled': False
                },
                EBSOptions={
                    'EBSEnabled': True,
                    'VolumeType': 'gp3',
                    'VolumeSize': ebs_volume_size
                },
                AccessPolicies='',
                EngineVersion=engine_version
            )
            
            domain_status = response.get('DomainStatus', {})
            arn = domain_status.get('ARN')
            
            # Log to registry
            resource_registry.log_opensearch_domain_created(
                domain_name=config.name,
                domain_arn=arn,
                region=self.region,
                source="opensearch_provider"
            )
            
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=config.name,
                state=VectorStoreState.CREATING,
                arn=arn,
                region=self.region,
                created_at=datetime.now(timezone.utc),
                dimension=config.dimension,
                metadata={
                    "instance_type": instance_type,
                    "instance_count": instance_count,
                    "engine_version": engine_version,
                    "domain_status": domain_status
                },
                progress_percentage=10,
                estimated_time_remaining=600  # 10 minutes estimate
            )
            
        except Exception as e:
            logger.error(f"Failed to create OpenSearch domain: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=config.name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def delete(self, name: str, force: bool = False) -> VectorStoreStatus:
        """
        Delete an OpenSearch domain.
        
        Args:
            name: Name of the domain
            force: Whether to force deletion
            
        Returns:
            VectorStoreStatus with deletion result
        """
        try:
            self.opensearch_client.delete_domain(DomainName=name)
            
            # Update registry
            resource_registry.log_opensearch_domain_deleted(domain_name=name, source="opensearch_provider")
            
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=name,
                state=VectorStoreState.DELETING,
                progress_percentage=10,
                estimated_time_remaining=300  # 5 minutes estimate
            )
            
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ResourceNotFoundException":
                return VectorStoreStatus(
                    store_type=VectorStoreType.OPENSEARCH,
                    name=name,
                    state=VectorStoreState.DELETED,
                    progress_percentage=100
                )
            
            logger.error(f"Failed to delete OpenSearch domain: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def get_status(self, name: str) -> VectorStoreStatus:
        """
        Get current status of an OpenSearch domain.
        
        Args:
            name: Name of the domain
            
        Returns:
            VectorStoreStatus with current state
        """
        try:
            response = self.opensearch_client.describe_domain(DomainName=name)
            domain_status = response.get('DomainStatus', {})
            
            processing = domain_status.get('Processing', False)
            created = domain_status.get('Created', False)
            deleted = domain_status.get('Deleted', False)
            endpoint = domain_status.get('Endpoint')
            
            # Determine state
            if deleted:
                state = VectorStoreState.DELETED
                progress = 100
            elif processing:
                state = VectorStoreState.CREATING
                progress = 50
            elif created:
                state = VectorStoreState.AVAILABLE
                progress = 100
            else:
                state = VectorStoreState.CREATING
                progress = 25
            
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=name,
                state=state,
                arn=domain_status.get('ARN'),
                endpoint=endpoint,
                region=self.region,
                metadata=domain_status,
                progress_percentage=progress
            )
            
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ResourceNotFoundException":
                return VectorStoreStatus(
                    store_type=VectorStoreType.OPENSEARCH,
                    name=name,
                    state=VectorStoreState.NOT_FOUND,
                    progress_percentage=0
                )
            
            logger.error(f"Failed to get OpenSearch domain status: {e}")
            return VectorStoreStatus(
                store_type=VectorStoreType.OPENSEARCH,
                name=name,
                state=VectorStoreState.FAILED,
                error_message=str(e),
                progress_percentage=0
            )
    
    def list_stores(self) -> List[VectorStoreStatus]:
        """
        List all OpenSearch domains.
        
        Returns:
            List of VectorStoreStatus objects
        """
        try:
            response = self.opensearch_client.list_domain_names()
            domain_names = response.get('DomainNames', [])
            
            stores = []
            for domain_info in domain_names:
                domain_name = domain_info.get('DomainName')
                if domain_name:
                    # Get detailed status for each domain
                    status = self.get_status(domain_name)
                    stores.append(status)
            
            return stores
            
        except Exception as e:
            logger.error(f"Failed to list OpenSearch domains: {e}")
            return []
    
    def upsert_vectors(self, name: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Insert or update vectors in an OpenSearch index.
        
        Args:
            name: Name of the domain
            vectors: List of vector objects
            
        Returns:
            Result dictionary with upsert statistics
        """
        try:
            # This would require OpenSearch client connection and index operations
            logger.warning("upsert_vectors requires OpenSearch client - use opensearch_manager directly")
            return {
                "success": False,
                "message": "Use OpenSearchIntegrationManager for vector operations"
            }
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def query(self, name: str, query_vector: List[float], top_k: int = 10,
             filter_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query an OpenSearch index for similar vectors.
        
        Args:
            name: Name of the domain
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional filters
            
        Returns:
            List of similar vectors with scores
        """
        try:
            # This would require OpenSearch client connection and query operations
            logger.warning("query requires OpenSearch client - use opensearch_manager directly")
            return []
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []


# Register the OpenSearch provider
VectorStoreProviderFactory.register_provider(VectorStoreType.OPENSEARCH, OpenSearchProvider)

