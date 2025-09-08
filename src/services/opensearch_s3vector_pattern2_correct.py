"""
Correct OpenSearch S3 Vector Pattern 2 Implementation

This module provides the CORRECT implementation for integrating OpenSearch managed domains
with S3 Vector backend (Pattern 2). This fixes the architectural issues in the current
opensearch_integration.py which incorrectly mixes serverless and managed service clients.

Key Corrections:
1. Uses 'opensearch' client for managed domains (NOT 'opensearchserverless')
2. Proper S3 Vector engine configuration in domain creation
3. Correct index mapping with S3 Vector engine specification
4. Appropriate service boundaries and client usage
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import requests
from requests_aws4auth import AWS4Auth

from ..exceptions import (
    S3VectorError,
    OpenSearchIntegrationError,
    ConfigurationError
)
from ..utils.logging_config import get_structured_logger, LoggedOperation
from ..utils.timing_tracker import TimingTracker
from ..utils.resource_registry import resource_registry


@dataclass
class S3VectorDomainConfig:
    """Configuration for OpenSearch domain with S3 Vector engine."""
    domain_name: str
    s3_vector_bucket_arn: str
    instance_type: str = "or1.medium.search"  # OR1 instances required for S3 Vectors engine
    instance_count: int = 1  # Start with single instance for cost efficiency
    engine_version: str = "OpenSearch_2.19"
    kms_key_id: Optional[str] = None
    vpc_options: Optional[Dict[str, Any]] = None


@dataclass
class S3VectorIndexConfig:
    """Configuration for S3 Vector-backed OpenSearch index."""
    index_name: str
    vector_field_name: str
    vector_dimension: int
    s3_vector_index_arn: str
    space_type: str = "cosine"
    ef_construction: int = 512
    m: int = 16


class OpenSearchS3VectorPattern2Manager:
    """
    CORRECT implementation for OpenSearch Pattern 2 (S3 Vector Engine).
    
    This class properly implements the S3 Vector engine pattern where:
    - OpenSearch managed domains use S3 Vectors as storage engine
    - Vector data is stored in S3 while OpenSearch provides query interface
    - Hybrid search combines vector similarity with text search
    
    Key architectural corrections:
    1. Uses 'opensearch' client for managed domains (not serverless)
    2. Proper domain creation with S3VectorEngine configuration
    3. Correct index mapping with S3 Vector engine specification
    4. Appropriate IAM permissions and service boundaries
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        **kwargs
    ):
        """
        Initialize Pattern 2 manager with correct service clients.
        
        Args:
            region_name: AWS region for services
            **kwargs: Additional configuration options
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_s3vector_pattern2")
        
        # Resource tracking
        self.resource_registry = resource_registry
        
        # Configure boto3 clients with optimization
        self.boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60,
            connect_timeout=10,
            max_pool_connections=50
        )
        
        # Initialize AWS service clients - CORRECT for Pattern 2
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize AWS service clients with CORRECT configuration for Pattern 2."""
        try:
            session = boto3.Session(region_name=self.region_name)
            
            # CORRECT: Use 'opensearch' client for managed domains
            self.opensearch_client = session.client(
                'opensearch',  # NOT 'opensearchserverless'
                config=self.boto_config
            )
            
            # S3 Vectors client for vector operations
            self.s3vectors_client = session.client(
                's3vectors',
                config=self.boto_config
            )
            
            # IAM client for role management
            self.iam_client = session.client(
                'iam',
                config=self.boto_config
            )
            
            # KMS client for encryption
            self.kms_client = session.client(
                'kms',
                config=self.boto_config
            )
            
            # NOTE: NO opensearchserverless client - that's for Pattern 1 (Export)
            
            self.logger.log_operation(
                "pattern2_clients_initialized",
                level="INFO",
                clients=["opensearch", "s3vectors", "iam", "kms"],
                pattern="engine"
            )
            
        except Exception as e:
            error_msg = f"Failed to initialize Pattern 2 clients: {str(e)}"
            self.logger.log_error("pattern2_client_initialization_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def create_s3_vector_bucket(
        self,
        bucket_name: str,
        kms_key_id: Optional[str] = None
    ) -> str:
        """
        Create S3 Vector bucket (NOT regular S3 bucket).
        
        Args:
            bucket_name: Name for the S3 Vector bucket
            kms_key_id: Optional KMS key for encryption
            
        Returns:
            str: S3 Vector bucket ARN
        """
        operation = self.timing_tracker.start_operation("create_s3_vector_bucket")
        try:
            self.logger.log_operation(
                "creating_s3_vector_bucket",
                level="INFO",
                bucket_name=bucket_name,
                kms_encryption=bool(kms_key_id)
            )
            
            # Prepare bucket configuration
            bucket_config = {
                'vectorBucketName': bucket_name
            }
            
            # Add encryption if specified
            if kms_key_id:
                bucket_config['encryptionConfiguration'] = {
                    'sseType': 'aws:kms',
                    'kmsKeyArn': kms_key_id
                }
            
            # CORRECT: Use s3vectors client to create vector bucket
            response = self.s3vectors_client.create_vector_bucket(**bucket_config)
            
            bucket_arn = response['vectorBucketArn']
            
            # Log bucket creation in resource registry
            self.resource_registry.log_s3_vector_bucket_created(
                bucket_name=bucket_name,
                bucket_arn=bucket_arn,
                region=self.region_name,
                encryption_type='kms' if kms_key_id else 'sse-s3',
                source="pattern2_engine"
            )
            
            self.logger.log_operation(
                "s3_vector_bucket_created",
                level="INFO",
                bucket_name=bucket_name,
                bucket_arn=bucket_arn
            )
            
            return bucket_arn
            
        except ClientError as e:
            error_msg = f"Failed to create S3 Vector bucket: {str(e)}"
            self.logger.log_error("s3_vector_bucket_creation_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def create_s3_vector_index(
        self,
        bucket_name: str,
        index_name: str,
        dimension: int,
        distance_metric: str = "cosine",
        data_type: str = "float32",
        metadata_keys: Optional[List[str]] = None
    ) -> str:
        """
        Create S3 Vector index within the vector bucket.
        
        Args:
            bucket_name: S3 Vector bucket name
            index_name: Name for the vector index
            dimension: Vector dimension (must match embedding model)
            distance_metric: Distance metric (cosine, euclidean)
            data_type: Vector data type (float32)
            metadata_keys: Optional non-filterable metadata keys
            
        Returns:
            str: S3 Vector index ARN
        """
        operation = self.timing_tracker.start_operation("create_s3_vector_index")
        try:
            self.logger.log_operation(
                "creating_s3_vector_index",
                level="INFO",
                bucket_name=bucket_name,
                index_name=index_name,
                dimension=dimension,
                distance_metric=distance_metric
            )
            
            # Prepare index configuration
            index_config = {
                'vectorBucketName': bucket_name,
                'indexName': index_name,
                'dataType': data_type,
                'dimension': dimension,
                'distanceMetric': distance_metric
            }
            
            # Add metadata configuration if specified
            if metadata_keys:
                index_config['metadataConfiguration'] = {
                    'nonFilterableMetadataKeys': metadata_keys
                }
            
            # Create the vector index
            response = self.s3vectors_client.create_index(**index_config)
            
            index_arn = response['indexArn']
            
            # Log index creation in resource registry
            self.resource_registry.log_s3_vector_index_created(
                index_name=index_name,
                index_arn=index_arn,
                bucket_name=bucket_name,
                dimension=dimension,
                distance_metric=distance_metric,
                region=self.region_name,
                source="pattern2_engine"
            )
            
            self.logger.log_operation(
                "s3_vector_index_created",
                level="INFO",
                index_name=index_name,
                index_arn=index_arn,
                dimension=dimension
            )
            
            return index_arn
            
        except ClientError as e:
            error_msg = f"Failed to create S3 Vector index: {str(e)}"
            self.logger.log_error("s3_vector_index_creation_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def create_opensearch_domain_with_s3_vectors(
        self,
        config: S3VectorDomainConfig
    ) -> Dict[str, Any]:
        """
        Create OpenSearch managed domain with S3 Vector engine support.
        
        This is the CORRECT implementation for Pattern 2.
        
        Args:
            config: Domain configuration with S3 Vector settings
            
        Returns:
            Dict[str, Any]: Domain creation result
        """
        operation = self.timing_tracker.start_operation("create_opensearch_domain_with_s3_vectors")
        try:
            self.logger.log_operation(
                "creating_opensearch_domain_with_s3_vectors",
                level="INFO",
                domain_name=config.domain_name,
                s3_vector_bucket_arn=config.s3_vector_bucket_arn,
                instance_type=config.instance_type,
                instance_count=config.instance_count
            )
            
            # Prepare domain configuration
            domain_config = {
                'DomainName': config.domain_name,
                'EngineVersion': config.engine_version,
                
                # Cluster configuration
                'ClusterConfig': {
                    'InstanceType': config.instance_type,
                    'InstanceCount': config.instance_count,
                    'DedicatedMasterEnabled': False,
                    'ZoneAwarenessEnabled': config.instance_count > 1
                },
                
                # Storage configuration
                'EBSOptions': {
                    'EBSEnabled': True,
                    'VolumeType': 'gp3',
                    'VolumeSize': 20,
                    'Iops': 3000
                },
                
                # CRITICAL: S3 Vector engine configuration (correct AWS API format)
                'AIMLOptions': {
                    'S3VectorsEngine': {
                        'Enabled': True
                        # Note: S3VectorBucketArn is not supported in create_domain API
                        # The bucket association is handled separately after domain creation
                    }
                },
                
                # Security configuration
                'EncryptionAtRestOptions': {
                    'Enabled': True
                },
                
                'NodeToNodeEncryptionOptions': {
                    'Enabled': True
                },
                
                'DomainEndpointOptions': {
                    'EnforceHTTPS': True,
                    'TLSSecurityPolicy': 'Policy-Min-TLS-1-2-2019-07'
                },
                
                # Access policy (restrictive by default)
                'AccessPolicies': json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": f"arn:aws:iam::{self._get_account_id()}:root"},
                            "Action": "es:*",
                            "Resource": f"arn:aws:es:{self.region_name}:{self._get_account_id()}:domain/{config.domain_name}/*"
                        }
                    ]
                })
            }
            
            # Add KMS encryption if specified
            if config.kms_key_id:
                domain_config['EncryptionAtRestOptions']['KmsKeyId'] = config.kms_key_id
                domain_config['S3VectorEngine']['KmsKeyId'] = config.kms_key_id
            
            # Add VPC configuration if specified
            if config.vpc_options:
                domain_config['VPCOptions'] = config.vpc_options
            
            # CORRECT: Use opensearch client to create managed domain
            response = self.opensearch_client.create_domain(**domain_config)
            
            domain_status = response['DomainStatus']
            domain_arn = domain_status['ARN']
            domain_endpoint = domain_status.get('Endpoint')
            
            # Log domain creation in resource registry
            self.resource_registry.log_opensearch_domain_created(
                domain_name=config.domain_name,
                domain_arn=domain_arn,
                region=self.region_name,
                engine_version=config.engine_version,
                s3_vectors_enabled=True,
                source="pattern2_engine"
            )
            
            self.logger.log_operation(
                "opensearch_domain_created",
                level="INFO",
                domain_name=config.domain_name,
                domain_arn=domain_arn,
                s3_vector_engine_enabled=True
            )
            
            # Wait for domain to become active
            self._wait_for_domain_active(config.domain_name)
            
            # Get updated domain info with endpoint
            updated_domain = self.opensearch_client.describe_domain(
                DomainName=config.domain_name
            )
            domain_endpoint = updated_domain['DomainStatus']['Endpoint']
            
            return {
                'domain_name': config.domain_name,
                'domain_arn': domain_arn,
                'domain_endpoint': domain_endpoint,
                's3_vector_engine_enabled': True,
                's3_vector_bucket_arn': config.s3_vector_bucket_arn,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'InvalidParameterValue':
                raise OpenSearchIntegrationError(
                    f"Invalid S3 Vector configuration: {error_msg}"
                )
            elif error_code == 'ResourceAlreadyExistsException':
                raise OpenSearchIntegrationError(
                    f"Domain {config.domain_name} already exists"
                )
            else:
                raise OpenSearchIntegrationError(
                    f"Domain creation failed: {error_code} - {error_msg}"
                )
        except Exception as e:
            error_msg = f"Unexpected error creating domain: {str(e)}"
            self.logger.log_error("domain_creation_unexpected_error", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def create_s3_vector_backed_index(
        self,
        domain_endpoint: str,
        config: S3VectorIndexConfig,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create OpenSearch index that uses S3 Vector as storage engine.
        
        Args:
            domain_endpoint: OpenSearch domain endpoint
            config: S3 Vector index configuration
            additional_fields: Additional non-vector fields for hybrid search
            
        Returns:
            Dict[str, Any]: Index creation result
        """
        operation = self.timing_tracker.start_operation("create_s3_vector_backed_index")
        try:
            self.logger.log_operation(
                "creating_s3_vector_backed_index",
                level="INFO",
                domain_endpoint=domain_endpoint,
                index_name=config.index_name,
                vector_field=config.vector_field_name,
                s3_vector_index_arn=config.s3_vector_index_arn
            )
            
            # Build index mapping with S3 Vector engine
            mapping = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 512,
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                        "refresh_interval": "30s"
                    }
                },
                "mappings": {
                    "properties": {
                        config.vector_field_name: {
                            "type": "knn_vector",
                            "dimension": config.vector_dimension,
                            "space_type": config.space_type,
                            "method": {
                                "name": "hnsw",
                                "engine": "s3vector",  # CRITICAL: Use S3 Vector engine
                                "parameters": {
                                    "s3_vector_index_arn": config.s3_vector_index_arn,
                                    "ef_construction": config.ef_construction,
                                    "m": config.m
                                }
                            }
                        }
                    }
                }
            }
            
            # Add additional fields for hybrid search
            if additional_fields:
                mapping["mappings"]["properties"].update(additional_fields)
            else:
                # Default fields for hybrid search
                mapping["mappings"]["properties"].update({
                    "title": {"type": "text", "analyzer": "english"},
                    "content": {"type": "text", "analyzer": "english"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "tags": {"type": "keyword"}
                        }
                    }
                })
            
            # Create index via OpenSearch REST API with AWS authentication
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region_name,
                'es',
                session_token=credentials.token
            )
            
            url = f"https://{domain_endpoint}/{config.index_name}"
            response = requests.put(
                url,
                json=mapping,
                auth=awsauth,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(
                    f"Failed to create S3 vector index: {response.status_code} {response.text}"
                )
            
            # Log index creation in resource registry
            self.resource_registry.log_opensearch_index_created(
                index_name=config.index_name,
                opensearch_endpoint=domain_endpoint,
                vector_field_name=config.vector_field_name,
                vector_dimension=config.vector_dimension,
                space_type=config.space_type,
                engine_type="s3vector",
                source="pattern2_engine"
            )
            
            result = {
                "index_name": config.index_name,
                "vector_field": config.vector_field_name,
                "dimension": config.vector_dimension,
                "space_type": config.space_type,
                "engine": "s3vector",
                "s3_vector_index_arn": config.s3_vector_index_arn,
                "domain_endpoint": domain_endpoint,
                "created_at": datetime.utcnow().isoformat(),
                "hybrid_search_enabled": bool(additional_fields)
            }
            
            self.logger.log_operation(
                "s3_vector_backed_index_created",
                level="INFO",
                index_name=config.index_name,
                vector_field=config.vector_field_name,
                s3_vector_engine=True
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to create S3 vector-backed index: {str(e)}"
            self.logger.log_error("s3_vector_backed_index_creation_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def perform_hybrid_search(
        self,
        domain_endpoint: str,
        index_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        vector_field: str = "embedding",
        text_fields: Optional[List[str]] = None,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        vector_weight: float = 0.7,
        text_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining S3 Vector similarity with OpenSearch text search.
        
        Args:
            domain_endpoint: OpenSearch domain endpoint
            index_name: Index to search
            query_text: Text query for keyword search
            query_vector: Vector for similarity search
            vector_field: Name of vector field in index
            text_fields: Fields to search for text queries
            k: Number of results to return
            filters: Additional filters to apply
            vector_weight: Weight for vector similarity scores
            text_weight: Weight for text match scores
            
        Returns:
            List[Dict[str, Any]]: Hybrid search results
        """
        operation = self.timing_tracker.start_operation("perform_hybrid_search")
        try:
            if not query_text and not query_vector:
                raise ValueError("Either query_text or query_vector must be provided")
            
            text_fields = text_fields or ["title", "content"]
            
            self.logger.log_operation(
                "performing_hybrid_search",
                level="INFO",
                index_name=index_name,
                has_text_query=bool(query_text),
                has_vector_query=bool(query_vector),
                k=k
            )
            
            # Build hybrid query
            query_clauses = []
            
            # Add vector similarity query if provided
            if query_vector:
                vector_query = {
                    "knn": {
                        vector_field: {
                            "vector": query_vector,
                            "k": k,
                            "boost": vector_weight
                        }
                    }
                }
                query_clauses.append(vector_query)
            
            # Add text search query if provided
            if query_text:
                text_query = {
                    "multi_match": {
                        "query": query_text,
                        "fields": text_fields,
                        "type": "best_fields",
                        "boost": text_weight
                    }
                }
                query_clauses.append(text_query)
            
            # Combine queries
            if len(query_clauses) == 1:
                combined_query = query_clauses[0]
            else:
                combined_query = {
                    "bool": {
                        "should": query_clauses,
                        "minimum_should_match": 1
                    }
                }
            
            # Add filters if provided
            if filters:
                if "bool" not in combined_query:
                    combined_query = {"bool": {"must": [combined_query]}}
                combined_query["bool"]["filter"] = filters
            
            # Execute search
            search_body = {
                "size": k,
                "query": combined_query,
                "_source": True,
                "highlight": {
                    "fields": {field: {} for field in text_fields}
                }
            }
            
            # Make authenticated request to OpenSearch
            credentials = boto3.Session().get_credentials()
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                self.region_name,
                'es',
                session_token=credentials.token
            )
            
            url = f"https://{domain_endpoint}/{index_name}/_search"
            response = requests.post(
                url,
                json=search_body,
                auth=awsauth,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                raise OpenSearchIntegrationError(
                    f"Hybrid search failed: {response.status_code} {response.text}"
                )
            
            search_results = response.json()
            
            # Process results
            results = []
            for hit in search_results.get('hits', {}).get('hits', []):
                result = {
                    'document_id': hit['_id'],
                    'score': hit['_score'],
                    'content': hit.get('_source', {}),
                    'highlights': hit.get('highlight', {})
                }
                results.append(result)
            
            self.logger.log_operation(
                "hybrid_search_completed",
                level="INFO",
                index_name=index_name,
                results_count=len(results),
                processing_time_ms=search_results.get('took', 0)
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Hybrid search failed: {str(e)}"
            self.logger.log_error("hybrid_search_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def _wait_for_domain_active(self, domain_name: str, timeout_minutes: int = 30) -> None:
        """Wait for OpenSearch domain to become active."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        self.logger.log_operation(
            "waiting_for_domain_active",
            level="INFO",
            domain_name=domain_name,
            timeout_minutes=timeout_minutes
        )
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.opensearch_client.describe_domain(DomainName=domain_name)
                domain_status = response['DomainStatus']
                
                if not domain_status.get('Processing', True) and domain_status.get('Created', False):
                    self.logger.log_operation(
                        "domain_active",
                        level="INFO",
                        domain_name=domain_name,
                        elapsed_seconds=int(time.time() - start_time)
                    )
                    return
                
                time.sleep(30)  # Check every 30 seconds
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                time.sleep(30)
        
        raise OpenSearchIntegrationError(
            f"Domain {domain_name} did not become active within {timeout_minutes} minutes"
        )

    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts', region_name=self.region_name)
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            raise OpenSearchIntegrationError(f"Failed to get AWS account ID: {e}")

    def get_domain_status(self, domain_name: str) -> Dict[str, Any]:
        """Get OpenSearch domain status and configuration."""
        try:
            response = self.opensearch_client.describe_domain(DomainName=domain_name)
            domain_status = response['DomainStatus']
            
            return {
                'domain_name': domain_status['DomainName'],
                'domain_arn': domain_status['ARN'],
                'domain_endpoint': domain_status.get('Endpoint'),
                'engine_version': domain_status['EngineVersion'],
                'processing': domain_status.get('Processing', False),
                'created': domain_status.get('Created', False),
                's3_vector_engine': domain_status.get('S3VectorEngine', {}).get('Enabled', False),
                'cluster_config': domain_status.get('ClusterConfig', {}),
                'ebs_options': domain_status.get('EBSOptions', {}),
                'encryption_at_rest': domain_status.get('EncryptionAtRestOptions', {}).get('Enabled', False)
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise OpenSearchIntegrationError(f"Domain {domain_name} not found")
            raise OpenSearchIntegrationError(f"Failed to get domain status: {str(e)}")

    def delete_domain(self, domain_name: str) -> Dict[str, Any]:
        """Delete OpenSearch domain."""
        try:
            self.logger.log_operation(
                "deleting_opensearch_domain",
                level="INFO",
                domain_name=domain_name
            )
            
            response = self.opensearch_client.delete_domain(DomainName=domain_name)
            
            # Update resource registry
            self.resource_registry.log_opensearch_domain_deleted(
                domain_name=domain_name,
                source="pattern2_cleanup"
            )
            
            return {
                'domain_name': domain_name,
                'status': 'deleting',
                'deleted_at': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return {'domain_name': domain_name, 'status': 'not_found'}
            raise OpenSearchIntegrationError(f"Failed to delete domain: {str(e)}")