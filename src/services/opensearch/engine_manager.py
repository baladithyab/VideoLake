"""
OpenSearch Engine Manager

Manages configuration of OpenSearch domains to use S3 Vectors as storage engine.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from ...exceptions import OpenSearchIntegrationError
from ...utils.logging_config import get_structured_logger
from ...utils.timing_tracker import TimingTracker
from ...utils.aws_retry import AWSRetryHandler


class OpenSearchEngineManager:
    """
    Manages S3 Vectors as OpenSearch storage engine integration.

    Implements the Engine Pattern where OpenSearch domains use S3 Vectors
    as the backend storage for vector fields, providing cost-effective
    storage with OpenSearch's query capabilities.

    Features:
    - OpenSearch domain S3 Vectors engine configuration
    - Domain validation and compatibility checks
    - Index creation with S3 vector engine
    - Engine capabilities querying
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        boto_config: Optional[Config] = None
    ):
        """
        Initialize Engine Manager.

        Args:
            region_name: AWS region
            boto_config: Optional boto3 Config object
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_engine")
        # resource_registry deprecated - using Terraform tfstate

        # Use provided config or create default
        self.boto_config = boto_config or Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60,
            connect_timeout=10,
            max_pool_connections=50
        )

        # Initialize clients
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize AWS service clients."""
        try:
            session = boto3.Session(region_name=self.region_name)

            self.opensearch_client = session.client(
                'opensearch',
                config=self.boto_config
            )

            self.logger.log_operation("Engine manager clients initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize engine manager clients: {str(e)}"
            self.logger.log_error("client_initialization_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def configure_s3_vectors_engine(
        self,
        domain_name: str,
        enable_s3_vectors: bool = True,
        kms_key_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Configure OpenSearch domain to use S3 Vectors as storage engine.

        Enables S3 vector engine support on OpenSearch domain, allowing
        vector fields to be stored in S3 while maintaining OpenSearch functionality.

        Args:
            domain_name: OpenSearch domain name
            enable_s3_vectors: Whether to enable S3 vectors engine
            kms_key_id: KMS key for S3 vectors encryption
            **kwargs: Additional domain configuration options

        Returns:
            Dict[str, Any]: Domain configuration details

        Raises:
            OpenSearchIntegrationError: If domain configuration fails
        """
        operation = self.timing_tracker.start_operation("configure_s3_vectors_engine")
        try:
            self.logger.log_operation(
                "configuring_s3_vectors_engine",
                level="INFO",
                domain_name=domain_name,
                enable_s3_vectors=enable_s3_vectors
            )

            # Get current domain configuration with retry
            def _describe_domain():
                return self.opensearch_client.describe_domain(DomainName=domain_name)

            try:
                domain_response = AWSRetryHandler.retry_with_backoff(
                    _describe_domain,
                    max_retries=3,
                    operation_name="describe_opensearch_domain"
                )
                domain_config = domain_response['DomainStatus']
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    raise OpenSearchIntegrationError(f"OpenSearch domain not found: {domain_name}")
                raise

            # Validate domain requirements for S3 vectors
            self._validate_domain_for_s3_vectors(domain_config)

            # Prepare domain configuration update
            update_config = {
                'DomainName': domain_name,
                'AdvancedSecurityOptions': {
                    'Enabled': domain_config.get('AdvancedSecurityOptions', {}).get('Enabled', False)
                }
            }

            # Enable S3 vectors engine if requested
            if enable_s3_vectors:
                # Configure S3 vectors engine settings
                s3_vectors_config = {
                    'Enabled': True
                }

                if kms_key_id:
                    s3_vectors_config['KMSKeyId'] = kms_key_id

                update_config['S3VectorsEngine'] = s3_vectors_config

                self.logger.log_operation(
                    "enabling_s3_vectors_engine",
                    level="INFO",
                    domain_name=domain_name,
                    kms_key_id=kms_key_id
                )
            else:
                update_config['S3VectorsEngine'] = {'Enabled': False}

            # Apply domain configuration update with retry
            def _update_domain():
                return self.opensearch_client.update_domain_config(**update_config)

            AWSRetryHandler.retry_with_backoff(
                _update_domain,
                max_retries=3,
                operation_name="update_opensearch_domain_config"
            )

            # Wait for domain update to complete
            self._wait_for_domain_update(domain_name, timeout_minutes=30)

            # Get updated domain configuration
            updated_domain = AWSRetryHandler.retry_with_backoff(
                _describe_domain,
                max_retries=3,
                operation_name="describe_updated_domain"
            )

            # Domain configuration complete
            domain_status = updated_domain['DomainStatus']
            domain_arn = domain_status.get('ARN', f'arn:aws:es:{self.region_name}:123456789012:domain/{domain_name}')
            engine_version = domain_status.get('EngineVersion', 'OpenSearch_2.19')

            configuration_result = {
                'domain_name': domain_name,
                's3_vectors_enabled': enable_s3_vectors,
                'domain_status': updated_domain['DomainStatus']['Processing'],
                'configuration_timestamp': datetime.utcnow().isoformat(),
                'engine_capabilities': self._get_s3_vectors_capabilities(domain_name) if enable_s3_vectors else None
            }

            self.logger.log_operation(
                "s3_vectors_engine_configured",
                level="INFO",
                domain_name=domain_name,
                enabled=enable_s3_vectors,
                processing=updated_domain['DomainStatus']['Processing']
            )

            return configuration_result

        except ClientError as e:
            error_msg = f"AWS API error configuring S3 vectors engine: {str(e)}"
            self.logger.log_operation("engine_config_aws_error", level="ERROR", error=error_msg, domain_name=domain_name)
            raise OpenSearchIntegrationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error configuring S3 vectors engine: {str(e)}"
            self.logger.log_operation("engine_config_unexpected_error", level="ERROR", error=error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    async def create_s3_vector_index(
        self,
        opensearch_endpoint: str,
        index_name: str,
        vector_field_name: str,
        vector_dimension: int,
        space_type: str = "cosinesimil",
        additional_fields: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create OpenSearch index with S3 vector engine for vector fields.

        Args:
            opensearch_endpoint: OpenSearch domain endpoint
            index_name: Name of the index to create
            vector_field_name: Name of the vector field
            vector_dimension: Dimensionality of vectors
            space_type: Distance function ("cosine", "l2", "inner_product")
            additional_fields: Additional non-vector fields for the index
            **kwargs: Additional index configuration

        Returns:
            Dict[str, Any]: Index creation result
        """
        try:
            # Import requests for direct OpenSearch API calls
            import requests
            from requests_aws4auth import AWS4Auth
            import boto3
            import asyncio

            # Build index mapping with PROPER S3 vector engine configuration
            mapping = {
                "settings": {
                    "index.knn": True,
                },
                "mappings": {
                    "properties": {
                        vector_field_name: {
                            "type": "knn_vector",
                            "dimension": vector_dimension,
                            "space_type": space_type,
                            "method": {
                                "engine": "s3vector"  # CRITICAL: S3Vector engine (no name/parameters allowed)
                            }
                        }
                    }
                }
            }

            # Add additional fields to mapping
            if additional_fields:
                mapping["mappings"]["properties"].update(additional_fields)

            # Create index via OpenSearch REST API with proper AWS authentication
            url = f"https://{opensearch_endpoint}/{index_name}"

            # Use AWS Signature V4 authentication
            try:
                # Wrap blocking boto3 call with asyncio.to_thread()
                credentials = await asyncio.to_thread(boto3.Session().get_credentials)
                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    self.region_name,
                    'es',
                    session_token=credentials.token
                )

                response = await asyncio.to_thread(
                    requests.put,
                    url,
                    json=mapping,
                    auth=awsauth,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

            except ImportError:
                # Fallback to no auth if AWS4Auth not available
                self.logger.log_operation(
                    "aws4auth_not_available_using_fallback",
                    level="WARNING"
                )

                response = await asyncio.to_thread(
                    requests.put,
                    url,
                    json=mapping,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(
                    f"Failed to create S3 vector index: {response.status_code} {response.text}"
                )

            result = {
                "index_name": index_name,
                "vector_field": vector_field_name,
                "dimension": vector_dimension,
                "space_type": space_type,
                "engine": "s3vector",
                "created_at": datetime.utcnow().isoformat(),
                "response": response.json() if response.text else {}
            }

            self.logger.log_operation(
                "s3_vector_index_created",
                level="INFO",
                index_name=index_name,
                vector_field=vector_field_name,
                dimension=vector_dimension
            )

            return result

        except Exception as e:
            error_msg = f"Failed to create S3 vector index: {str(e)}"
            self.logger.log_operation("s3_vector_index_creation_failed", level="ERROR", error=error_msg, index_name=index_name)
            raise OpenSearchIntegrationError(error_msg) from e

    def _validate_domain_for_s3_vectors(self, domain_config: Dict[str, Any]) -> None:
        """Validate that OpenSearch domain supports S3 vectors."""
        # Check OpenSearch version
        engine_version = domain_config.get('EngineVersion', '')
        if not engine_version.startswith('OpenSearch_2.') or engine_version < 'OpenSearch_2.19':
            raise OpenSearchIntegrationError(
                f"S3 vectors requires OpenSearch 2.19 or later, found: {engine_version}"
            )

        # Check instance types (should be OR1 instances for S3 Vectors engine)
        instance_type = domain_config.get('ClusterConfig', {}).get('InstanceType', '')
        if not instance_type.startswith('or1.'):
            self.logger.log_operation(
                "incorrect_instance_type_warning",
                level="WARNING",
                instance_type=instance_type,
                recommendation="Use OR1 instance types (or1.medium.search, or1.large.search, etc.) for S3 Vectors engine"
            )

    def _wait_for_domain_update(self, domain_name: str, timeout_minutes: int = 30) -> None:
        """Wait for OpenSearch domain update to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while time.time() - start_time < timeout_seconds:
            def _check_domain():
                return self.opensearch_client.describe_domain(DomainName=domain_name)

            response = AWSRetryHandler.retry_with_backoff(
                _check_domain,
                max_retries=3,
                operation_name="check_domain_update_status"
            )

            if not response['DomainStatus']['Processing']:
                return

            time.sleep(30)  # Check every 30 seconds

        raise OpenSearchIntegrationError(
            f"Domain update timeout after {timeout_minutes} minutes"
        )

    def _get_s3_vectors_capabilities(self, domain_name: str) -> Dict[str, Any]:
        """Get S3 vectors engine capabilities for domain."""
        return {
            'supported_space_types': ['cosine', 'l2', 'inner_product'],
            'max_dimensions': 10000,
            'features': ['hybrid_search', 'metadata_filtering', 'batch_ingestion'],
            'limitations': ['no_snapshots', 'no_ultraWarm', 'no_cross_cluster_replication']
        }
