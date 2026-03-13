"""
Videolake OpenSearch Backend Provider

Implements the Videolake VectorStoreProvider interface for Amazon OpenSearch Service,
enabling the platform to leverage OpenSearch's powerful vector search capabilities
as one of its supported vector store backends.
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
    VectorStoreProviderFactory,
    VectorStoreCapabilities
)
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.aws_clients import aws_client_factory
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


class OpenSearchProvider(VectorStoreProvider):
    """
    Amazon OpenSearch backend implementation for Videolake platform.
    
    Provides integration with Amazon OpenSearch Service, allowing Videolake to
    utilize OpenSearch's vector search and analytics capabilities as a flexible
    backend option.
    """
    
    def __init__(self):
        """Initialize the OpenSearch provider."""
        self.opensearch_manager = OpenSearchIntegrationManager()
        self.opensearch_client = aws_client_factory.get_opensearch_client()
        
        config_manager = get_unified_config_manager()
        self.region = config_manager.config.aws.region
    
    def _parse_domain_index(self, name: str) -> tuple:
        """
        Parse name parameter to extract domain and index names.

        Args:
            name: Either domain name or "domain/index" format

        Returns:
            Tuple of (domain_name, index_name)
        """
        if "/" in name:
            parts = name.split("/", 1)
            domain_name = parts[0]
            index_name = parts[1]
        else:
            # Default to domain name with "vectors" index
            domain_name = name
            index_name = "vectors"

        return domain_name, index_name

    @property
    def store_type(self) -> VectorStoreType:
        """Return OPENSEARCH as the store type."""
        return VectorStoreType.OPENSEARCH
    
    def create(self, config: VectorStoreConfig) -> VectorStoreStatus:
        """
        Create a new Amazon OpenSearch domain for Videolake.
        
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
            name: Name of the domain (will use default index) or "domain/index" format
            vectors: List of vector objects with 'id', 'values', and optional 'metadata'

        Returns:
            Result dictionary with upsert statistics
        """
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from opensearchpy.helpers import bulk
            from requests_aws4auth import AWS4Auth
            import boto3

            # Parse domain and index name
            domain_name, index_name = self._parse_domain_index(name)

            # Get domain endpoint
            domain_status = self.get_status(domain_name)
            if domain_status.state != VectorStoreState.AVAILABLE:
                raise Exception(f"Domain {domain_name} is not available: {domain_status.state}")

            endpoint = domain_status.endpoint
            if not endpoint:
                raise Exception(f"Domain {domain_name} has no endpoint")

            # Setup AWS authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'es',
                session_token=credentials.token
            )

            # Create OpenSearch client
            os_client = OpenSearch(
                hosts=[{'host': endpoint, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            # Prepare bulk actions
            actions = []
            for vector in vectors:
                doc = {
                    "_index": index_name,
                    "_id": vector.get("id", vector.get("vectorId")),
                    "_source": {
                        "embedding": vector.get("values", vector.get("vector")),
                        "metadata": vector.get("metadata", {})
                    }
                }
                actions.append(doc)

            # Execute bulk upsert
            success_count, errors = bulk(os_client, actions, raise_on_error=False)

            return {
                "success": len(errors) == 0,
                "upserted_count": success_count,
                "errors": errors if errors else []
            }

        except ImportError as e:
            logger.error(f"Missing required libraries: {e}")
            return {
                "success": False,
                "error": f"Missing opensearchpy or requests_aws4auth library: {str(e)}"
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
            name: Name of the domain or "domain/index" format
            query_vector: Query vector
            top_k: Number of results
            filter_metadata: Optional metadata filters

        Returns:
            List of similar vectors with scores
        """
        try:
            from opensearchpy import OpenSearch, RequestsHttpConnection
            from requests_aws4auth import AWS4Auth
            import boto3

            # Parse domain and index name
            domain_name, index_name = self._parse_domain_index(name)

            # Get domain endpoint
            domain_status = self.get_status(domain_name)
            if domain_status.state != VectorStoreState.AVAILABLE:
                raise Exception(f"Domain {domain_name} is not available: {domain_status.state}")

            endpoint = domain_status.endpoint
            if not endpoint:
                raise Exception(f"Domain {domain_name} has no endpoint")

            # Setup AWS authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region,
                'es',
                session_token=credentials.token
            )

            # Create OpenSearch client
            os_client = OpenSearch(
                hosts=[{'host': endpoint, 'port': 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )

            # Build knn query
            query_body = {
                "size": top_k,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": top_k
                        }
                    }
                }
            }

            # Add metadata filters if provided
            if filter_metadata:
                query_body["query"] = {
                    "bool": {
                        "must": [query_body["query"]],
                        "filter": [
                            {"term": {f"metadata.{key}": value}}
                            for key, value in filter_metadata.items()
                        ]
                    }
                }

            # Execute search
            response = os_client.search(index=index_name, body=query_body)

            # Transform results to standard format
            results = []
            for hit in response.get("hits", {}).get("hits", []):
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "values": hit["_source"].get("embedding"),
                    "metadata": hit["_source"].get("metadata", {})
                })

            return results

        except ImportError as e:
            logger.error(f"Missing required libraries: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to query vectors: {e}")
            return []
    
    def get_capabilities(self) -> VectorStoreCapabilities:
        """
        Return OpenSearch provider capabilities.

        Returns:
            VectorStoreCapabilities with OpenSearch specifications
        """
        return VectorStoreCapabilities(
            max_dimension=16000,  # OpenSearch supports very large dimensions
            max_vectors=None,  # Unlimited (depends on cluster size)
            supports_metadata_filtering=True,
            supports_hybrid_search=True,  # OpenSearch supports hybrid search
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=50.0,  # OpenSearch domain costs
            typical_query_latency_ms=100.0,
            supports_sparse_vectors=True,
            supports_multi_vector=True,
            max_batch_size=5000
        )

    def validate_connectivity(self) -> Dict[str, Any]:
        """
        Validate connectivity to Amazon OpenSearch service.
        
        Tests the Videolake platform's connection to OpenSearch backend:
        - OpenSearch service accessibility
        - Domain listing capability
        - Cluster health check if domains exist
        - Response time measurement
        
        Returns:
            Connectivity validation result
        """
        import time
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import boto3
        
        start_time = time.time()
        
        try:
            # Test OpenSearch AWS service by listing domains
            response = self.opensearch_client.list_domain_names()
            
            response_time_ms = (time.time() - start_time) * 1000
            
            domain_names = response.get('DomainNames', [])
            domain_count = len(domain_names)
            
            health_status = "healthy"
            details = {
                "domain_count": domain_count,
                "region": self.region,
                "service": "OpenSearch"
            }
            
            # If we have domains, try to check cluster health of the first active one
            if domain_count > 0:
                for domain_info in domain_names:
                    domain_name = domain_info.get('DomainName')
                    try:
                        domain_status = self.opensearch_client.describe_domain(DomainName=domain_name)
                        domain = domain_status.get('DomainStatus', {})
                        
                        if domain.get('Endpoint') and not domain.get('Processing', False):
                            # Try to connect to actual cluster
                            endpoint = f"https://{domain['Endpoint']}"
                            
                            # Setup AWS auth
                            credentials = boto3.Session().get_credentials()
                            awsauth = AWS4Auth(
                                credentials.access_key,
                                credentials.secret_key,
                                self.region,
                                'es',
                                session_token=credentials.token
                            )
                            
                            # Create OpenSearch client
                            os_client = OpenSearch(
                                hosts=[{'host': domain['Endpoint'], 'port': 443}],
                                http_auth=awsauth,
                                use_ssl=True,
                                verify_certs=True,
                                connection_class=RequestsHttpConnection,
                                timeout=5
                            )
                            
                            # Check cluster health
                            cluster_health = os_client.cluster.health()
                            cluster_status = cluster_health.get('status', 'unknown')
                            
                            details['sample_domain'] = domain_name
                            details['cluster_status'] = cluster_status
                            
                            if cluster_status == 'red':
                                health_status = "degraded"
                            
                            break
                    except Exception as e:
                        logger.warning(f"Could not check cluster health for {domain_name}: {e}")
                        continue
            
            return {
                "accessible": True,
                "endpoint": f"es.{self.region}.amazonaws.com",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": health_status,
                "error_message": None,
                "details": details
            }
                
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            logger.error(f"OpenSearch connectivity validation failed: {e}")
            
            return {
                "accessible": False,
                "endpoint": f"es.{self.region}.amazonaws.com",
                "response_time_ms": round(response_time_ms, 2),
                "health_status": "unhealthy",
                "error_message": error_msg,
                "details": {
                    "region": self.region,
                    "service": "OpenSearch"
                }
            }

