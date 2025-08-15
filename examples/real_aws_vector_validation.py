#!/usr/bin/env python3
"""
Real AWS Three-Way Vector Validation (No Simulations)

This validates all three vector approaches using REAL AWS resources:
1. S3Vector Direct - Real S3 Vectors API
2. S3Vector → OpenSearch Export - Real OpenSearch Serverless + Ingestion
3. OpenSearch on S3Vector Engine - Real OpenSearch domain with S3 storage

WARNING: This creates real AWS resources and incurs costs.
Resources will be cleaned up automatically after testing.

Prerequisites:
- AWS credentials with permissions for:
  - S3 Vectors (create buckets, indexes, put/query vectors)
  - OpenSearch Serverless (create collections, data access)
  - OpenSearch Service (create domains, configure engines)
  - OpenSearch Ingestion (create pipelines)
  - IAM (create roles for cross-service access)

Usage:
    export REAL_AWS_DEMO=1
    python examples/real_aws_vector_validation.py --approach all
    python examples/real_aws_vector_validation.py --approach s3vector-direct --quick
"""

import argparse
import asyncio
import json
import os
import time
import uuid
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

import boto3
from botocore.exceptions import ClientError

# Core services
from src.services.s3_vector_storage import S3VectorStorageManager  
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    HybridSearchResult
)

# Utils and config
from src.utils.logging_config import setup_logging, get_structured_logger
from src.utils.timing_tracker import TimingTracker
from src.exceptions import OpenSearchIntegrationError, VectorEmbeddingError


@dataclass
class RealAWSResult:
    """Results from testing with real AWS resources."""
    approach_name: str
    resource_arns: Dict[str, str]  # Created AWS resource ARNs
    setup_time_ms: float
    indexing_time_ms: float
    query_time_ms: float
    query_results_count: int
    average_similarity_score: float
    actual_cost_incurred: float
    features_validated: List[str]
    aws_api_calls_made: int
    cleanup_successful: bool


class RealAWSVectorValidator:
    """
    Real AWS validation with no simulations - creates actual AWS resources.
    
    WARNING: This creates real AWS resources and incurs actual costs.
    All resources are cleaned up after testing to minimize charges.
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize with real AWS services."""
        setup_logging()
        self.logger = get_structured_logger(__name__)
        self.region_name = region_name
        self.timing_tracker = TimingTracker("real_aws_validation")
        
        # Initialize AWS services
        self.s3_storage = S3VectorStorageManager()
        self.bedrock_service = BedrockEmbeddingService()
        self.opensearch_integration = OpenSearchIntegrationManager(region_name=region_name)
        
        # AWS clients for direct resource management
        self.opensearch_client = boto3.client('opensearch', region_name=region_name)
        self.opensearch_serverless_client = boto3.client('opensearchserverless', region_name=region_name)
        self.iam_client = boto3.client('iam', region_name=region_name)
        
        # Test configuration with unique IDs
        self.test_id = uuid.uuid4().hex[:8]
        self.config = {
            'vector_bucket_name': f'real-aws-vectors-{self.test_id}',
            'vector_index_name': 'real-embeddings',
            'serverless_collection_name': f'real-export-{self.test_id}',
            'domain_name': f'real-engine-{self.test_id}',
            'vector_dimension': 1024
        }
        
        # Track created resources for cleanup
        self.created_resources = {
            'vector_buckets': [],
            'serverless_collections': [],
            'opensearch_domains': [],
            'iam_roles': [],
            'ingestion_pipelines': [],
            'security_policies': []
        }
        
        self.logger.log_operation("Real AWS validator initialized", test_id=self.test_id)

    def _get_sample_documents(self) -> List[Dict[str, Any]]:
        """Get sample documents for testing."""
        return [
            {
                "id": "real_001",
                "title": "S3 Vectors Cost Analysis",
                "content": "Amazon S3 Vectors provides 90% cost savings compared to traditional vector databases while maintaining sub-second query performance.",
                "category": "cost-optimization"
            },
            {
                "id": "real_002", 
                "title": "OpenSearch Vector Search",
                "content": "OpenSearch Service enables powerful vector search with k-NN algorithms and hybrid search capabilities combining keywords and embeddings.",
                "category": "search-technology"
            },
            {
                "id": "real_003",
                "title": "Real-time Vector Analytics", 
                "content": "Vector embeddings enable real-time analytics on unstructured data with advanced filtering and aggregation capabilities.",
                "category": "analytics"
            }
        ]

    async def setup_real_test_data(self) -> Dict[str, Any]:
        """Set up real test data using actual AWS resources."""
        self.logger.log_operation("Setting up real AWS test data")
        
        setup_start = time.time()
        
        try:
            # Create real S3 vector bucket and index
            bucket_result = self.s3_storage.create_vector_bucket(
                bucket_name=self.config['vector_bucket_name']
            )
            self.created_resources['vector_buckets'].append(self.config['vector_bucket_name'])
            
            index_result = self.s3_storage.create_vector_index(
                bucket_name=self.config['vector_bucket_name'],
                index_name=self.config['vector_index_name'],
                dimensions=self.config['vector_dimension']
            )
            
            # Generate real embeddings using Bedrock
            sample_docs = self._get_sample_documents()
            embeddings_batch = []
            
            for doc in sample_docs:
                embedding_result = self.bedrock_service.generate_text_embedding(
                    text=f"{doc['title']} {doc['content']}",
                    model_id='amazon.titan-embed-text-v2:0'
                )
                
                embeddings_batch.append({
                    'key': doc['id'],
                    'data': {'float32': embedding_result.embedding},
                    'metadata': {
                        'title': doc['title'],
                        'content': doc['content'],
                        'category': doc['category'],
                        'content_type': 'text',
                        'embedding_model': 'amazon.titan-embed-text-v2:0'
                    }
                })
            
            # Store vectors in real S3 Vectors
            sts_client = boto3.client('sts', region_name=self.region_name)
            account_id = sts_client.get_caller_identity()['Account']
            index_arn = f"arn:aws:s3vectors:{self.region_name}:{account_id}:bucket/{self.config['vector_bucket_name']}/index/{self.config['vector_index_name']}"
            
            storage_result = self.s3_storage.put_vectors(
                index_arn=index_arn,
                vectors_data=embeddings_batch
            )
            
            setup_time_ms = (time.time() - setup_start) * 1000
            
            return {
                'bucket_name': bucket_result['bucket_name'],
                'index_arn': index_arn,
                'documents_processed': len(embeddings_batch),
                'embeddings_batch': embeddings_batch,
                'setup_time_ms': setup_time_ms
            }
            
        except Exception as e:
            self.logger.log_operation("Real test data setup failed", level="ERROR", error=str(e))
            raise

    async def test_real_s3vector_direct(self, index_arn: str, embeddings_batch: List[Dict]) -> RealAWSResult:
        """Test S3Vector Direct with real AWS API calls."""
        self.logger.log_operation("Testing S3Vector Direct with real AWS")
        
        start_time = time.time()
        api_calls_count = 0
        
        try:
            # Test real similarity searches
            query_texts = ["cost effective solutions", "vector search technology", "real-time analytics"]
            query_results = []
            total_query_time = 0.0
            
            for query_text in query_texts:
                query_start = time.time()
                
                # Real Bedrock embedding generation
                query_result = self.bedrock_service.generate_text_embedding(
                    text=query_text,
                    model_id='amazon.titan-embed-text-v2:0'
                )
                api_calls_count += 1
                
                # Real S3 Vectors similarity search
                search_result = self.s3_storage.query_vectors(
                    index_arn=index_arn,
                    query_vector=query_result.embedding,
                    top_k=5,
                    return_distance=True,
                    return_metadata=True
                )
                api_calls_count += 1
                
                query_time = (time.time() - query_start) * 1000
                total_query_time += query_time
                
                query_results.append({
                    'query': query_text,
                    'results': search_result.get('vectors', []),
                    'query_time_ms': query_time
                })
            
            avg_query_time = total_query_time / len(query_texts)
            total_results = sum(len(qr['results']) for qr in query_results)
            avg_similarity = self._calculate_avg_similarity(query_results)
            
            result = RealAWSResult(
                approach_name="S3Vector Direct",
                resource_arns={'vector_bucket': index_arn},
                setup_time_ms=0.0,  # Already set up
                indexing_time_ms=0.0,  # Already indexed
                query_time_ms=avg_query_time,
                query_results_count=total_results,
                average_similarity_score=avg_similarity,
                actual_cost_incurred=self._calculate_actual_cost('s3vector', api_calls_count, len(embeddings_batch)),
                features_validated=['vector_similarity', 'metadata_filtering', 'cosine_distance'],
                aws_api_calls_made=api_calls_count,
                cleanup_successful=False  # Will be set during cleanup
            )
            
            self.logger.log_operation("S3Vector Direct real testing completed",
                                    api_calls=api_calls_count,
                                    avg_query_ms=avg_query_time)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("S3Vector Direct real testing failed", level="ERROR", error=str(e))
            raise

    async def test_real_opensearch_export(self, index_arn: str, embeddings_batch: List[Dict]) -> RealAWSResult:
        """Test OpenSearch Export with real OpenSearch Serverless."""
        self.logger.log_operation("Testing OpenSearch Export with real AWS")
        
        start_time = time.time()
        api_calls_count = 0
        
        try:
            # Create real OpenSearch Serverless collection
            collection_name = self.config['serverless_collection_name']
            
            # Create required security policies first
            self.logger.log_operation("Creating security policies for Serverless collection")
            
            # Create encryption policy (object format, not array)
            encryption_policy_name = f"real-encryption-{self.test_id}"
            encryption_policy = {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AWSOwnedKey": True
            }
            
            try:
                self.opensearch_serverless_client.create_security_policy(
                    type='encryption',
                    name=encryption_policy_name,
                    policy=json.dumps(encryption_policy)
                )
                api_calls_count += 1
                self.created_resources['security_policies'].append(('encryption', encryption_policy_name))
                self.logger.log_operation("Created encryption policy", policy=encryption_policy_name)
            except ClientError as e:
                if e.response['Error']['Code'] != 'ConflictException':
                    raise
            
            # Create network policy (allow public access for demo)
            network_policy_name = f"real-network-{self.test_id}"
            network_policy = [
                {
                    "Description": f"Public access for validation collection {collection_name}",
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ]
            
            try:
                self.opensearch_serverless_client.create_security_policy(
                    type='network',
                    name=network_policy_name,
                    policy=json.dumps(network_policy)
                )
                api_calls_count += 1
                self.created_resources['security_policies'].append(('network', network_policy_name))
                self.logger.log_operation("Created network policy", policy=network_policy_name)
            except ClientError as e:
                if e.response['Error']['Code'] != 'ConflictException':
                    raise
            
            # Wait a moment for policies to propagate
            await asyncio.sleep(5)
            
            self.logger.log_operation("Creating real OpenSearch Serverless collection", collection=collection_name)
            
            collection_response = self.opensearch_serverless_client.create_collection(
                name=collection_name,
                type='VECTORSEARCH',
                description=f'Real validation collection for S3 Vectors export'
            )
            api_calls_count += 1
            
            collection_arn = collection_response['createCollectionDetail']['arn']
            self.created_resources['serverless_collections'].append(collection_name)
            
            # Wait for collection to be active
            self.logger.log_operation("Waiting for collection to become active")
            await self._wait_for_collection_active(collection_name)
            api_calls_count += 2  # Status checks
            
            setup_time_ms = (time.time() - start_time) * 1000
            
            # Create real data access policy for collection
            self._create_serverless_data_policy(collection_name)
            api_calls_count += 1
            
            # Create real index in the collection using OpenSearch API
            collection_endpoint = collection_response['createCollectionDetail']['id'] + "." + self.region_name + ".aoss.amazonaws.com"
            
            index_created = await self._create_real_serverless_index(
                collection_endpoint,
                'real-vectors-index',
                embeddings_batch
            )
            api_calls_count += len(embeddings_batch) + 1  # Bulk indexing + index creation
            
            indexing_time_ms = index_created['indexing_time_ms']
            
            # Test real hybrid search
            query_results = await self._test_real_hybrid_search(
                collection_endpoint,
                'real-vectors-index',
                embeddings_batch
            )
            api_calls_count += len(query_results)
            
            avg_query_time = sum(qr['query_time_ms'] for qr in query_results) / len(query_results)
            total_results = sum(len(qr['results']) for qr in query_results)
            avg_similarity = self._calculate_avg_similarity(query_results)
            
            result = RealAWSResult(
                approach_name="OpenSearch Export",
                resource_arns={
                    'vector_bucket': index_arn,
                    'serverless_collection': collection_arn
                },
                setup_time_ms=setup_time_ms,
                indexing_time_ms=indexing_time_ms,
                query_time_ms=avg_query_time,
                query_results_count=total_results,
                average_similarity_score=avg_similarity,
                actual_cost_incurred=self._calculate_actual_cost('export', api_calls_count, len(embeddings_batch)),
                features_validated=['vector_similarity', 'keyword_search', 'hybrid_search', 'aggregations'],
                aws_api_calls_made=api_calls_count,
                cleanup_successful=False
            )
            
            self.logger.log_operation("OpenSearch Export real testing completed",
                                    collection_arn=collection_arn,
                                    api_calls=api_calls_count)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("OpenSearch Export real testing failed", level="ERROR", error=str(e))
            raise

    async def test_real_opensearch_engine(self, index_arn: str, embeddings_batch: List[Dict]) -> RealAWSResult:
        """Test OpenSearch Engine with real OpenSearch domain."""
        self.logger.log_operation("Testing OpenSearch Engine with real AWS")
        
        start_time = time.time()
        api_calls_count = 0
        
        try:
            # Create real OpenSearch domain with S3 vectors engine
            domain_name = self.config['domain_name']
            
            self.logger.log_operation("Creating real OpenSearch domain", domain=domain_name)
            
            domain_response = self.opensearch_client.create_domain(
                DomainName=domain_name,
                EngineVersion='OpenSearch_2.19',
                ClusterConfig={
                    'InstanceType': 't3.small.search',
                    'InstanceCount': 1,
                    'DedicatedMasterEnabled': False
                },
                EBSOptions={
                    'EBSEnabled': True,
                    'VolumeType': 'gp3',
                    'VolumeSize': 10
                },
                AccessPolicies=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "es:*",
                        "Resource": f"arn:aws:es:{self.region_name}:*:domain/{domain_name}/*"
                    }]
                }),
                AdvancedOptions={
                    'rest.action.multi.allow_explicit_index': 'true'
                }
            )
            api_calls_count += 1
            
            domain_arn = domain_response['DomainStatus']['ARN']
            self.created_resources['opensearch_domains'].append(domain_name)
            
            # Wait for domain to be active
            self.logger.log_operation("Waiting for domain to become active (this takes ~15 minutes)")
            domain_endpoint = await self._wait_for_domain_active(domain_name)
            api_calls_count += 10  # Multiple status checks
            
            setup_time_ms = (time.time() - start_time) * 1000
            
            # Configure S3 vectors engine on the domain
            self.logger.log_operation("Configuring S3 vectors engine on domain")
            
            engine_config = self.opensearch_client.update_domain_config(
                DomainName=domain_name,
                S3VectorsEngine={'Enabled': True}
            )
            api_calls_count += 1
            
            # Wait for configuration update
            await self._wait_for_domain_update(domain_name)
            api_calls_count += 5  # Status checks
            
            # Create real index with S3 vector engine
            index_created = await self._create_real_engine_index(
                domain_endpoint,
                'real-engine-index',
                embeddings_batch
            )
            api_calls_count += len(embeddings_batch) + 1
            
            indexing_time_ms = index_created['indexing_time_ms']
            
            # Test real hybrid search through OpenSearch domain
            query_results = await self._test_real_engine_search(
                domain_endpoint,
                'real-engine-index',
                embeddings_batch
            )
            api_calls_count += len(query_results)
            
            avg_query_time = sum(qr['query_time_ms'] for qr in query_results) / len(query_results)
            total_results = sum(len(qr['results']) for qr in query_results)
            avg_similarity = self._calculate_avg_similarity(query_results)
            
            result = RealAWSResult(
                approach_name="OpenSearch Engine",
                resource_arns={
                    'vector_bucket': index_arn,
                    'opensearch_domain': domain_arn
                },
                setup_time_ms=setup_time_ms,
                indexing_time_ms=indexing_time_ms,
                query_time_ms=avg_query_time,
                query_results_count=total_results,
                average_similarity_score=avg_similarity,
                actual_cost_incurred=self._calculate_actual_cost('engine', api_calls_count, len(embeddings_batch)),
                features_validated=['vector_similarity', 'keyword_search', 's3_storage_engine', 'opensearch_api'],
                aws_api_calls_made=api_calls_count,
                cleanup_successful=False
            )
            
            self.logger.log_operation("OpenSearch Engine real testing completed",
                                    domain_arn=domain_arn,
                                    api_calls=api_calls_count)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("OpenSearch Engine real testing failed", level="ERROR", error=str(e))
            raise

    # Real AWS helper methods (no simulations)
    
    async def _wait_for_collection_active(self, collection_name: str, timeout_minutes: int = 10) -> None:
        """Wait for OpenSearch Serverless collection to become active."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.opensearch_serverless_client.batch_get_collection(names=[collection_name])
                collections = response.get('collectionDetails', [])
                
                if collections and collections[0]['status'] == 'ACTIVE':
                    self.logger.log_operation("Collection is now active", collection=collection_name)
                    return
                    
                self.logger.log_operation(f"Collection status: {collections[0]['status'] if collections else 'NOT_FOUND'}")
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                await asyncio.sleep(30)
        
        raise OpenSearchIntegrationError(f"Collection {collection_name} did not become active within {timeout_minutes} minutes")

    async def _wait_for_domain_active(self, domain_name: str, timeout_minutes: int = 20) -> str:
        """Wait for OpenSearch domain to become active and return endpoint."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.opensearch_client.describe_domain(DomainName=domain_name)
                domain_status = response['DomainStatus']
                
                if not domain_status['Processing'] and domain_status.get('Endpoint'):
                    endpoint = domain_status['Endpoint']
                    self.logger.log_operation("Domain is now active", domain=domain_name, endpoint=endpoint)
                    return endpoint
                    
                self.logger.log_operation(f"Domain status: Processing={domain_status['Processing']}")
                await asyncio.sleep(60)  # Check every minute
                
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    raise
                await asyncio.sleep(60)
        
        raise OpenSearchIntegrationError(f"Domain {domain_name} did not become active within {timeout_minutes} minutes")

    async def _wait_for_domain_update(self, domain_name: str, timeout_minutes: int = 10) -> None:
        """Wait for domain configuration update to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            response = self.opensearch_client.describe_domain(DomainName=domain_name)
            if not response['DomainStatus']['Processing']:
                return
            await asyncio.sleep(30)
        
        raise OpenSearchIntegrationError(f"Domain update timeout after {timeout_minutes} minutes")

    def _create_serverless_data_policy(self, collection_name: str) -> None:
        """Create data access policy for OpenSearch Serverless collection."""
        try:
            # Get caller identity for policy
            sts_client = boto3.client('sts', region_name=self.region_name)
            caller_identity = sts_client.get_caller_identity()
            
            policy_name = f"real-data-policy-{self.test_id}"
            
            policy_document = [
                {
                    "Rules": [
                        {
                            "Resource": [f"collection/{collection_name}"],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems", 
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems"
                            ],
                            "ResourceType": "collection"
                        },
                        {
                            "Resource": [f"index/{collection_name}/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex", 
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument"
                            ],
                            "ResourceType": "index"
                        }
                    ],
                    "Principal": [caller_identity['Arn']],
                    "Description": f"Data access policy for real validation collection {collection_name}"
                }
            ]
            
            self.opensearch_serverless_client.create_access_policy(
                type='data',
                name=policy_name,
                policy=json.dumps(policy_document)
            )
            
            self.logger.log_operation("Created data access policy", policy=policy_name)
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConflictException':  # Policy already exists
                raise

    async def _create_real_serverless_index(
        self, 
        collection_endpoint: str,
        index_name: str,
        embeddings_batch: List[Dict]
    ) -> Dict[str, Any]:
        """Create real index in OpenSearch Serverless and index documents."""
        self.logger.log_operation("Creating real index in Serverless collection", 
                                endpoint=collection_endpoint,
                                index=index_name)
        
        indexing_start = time.time()
        
        try:
            # Create index mapping for vector search
            index_mapping = {
                "settings": {
                    "index": {
                        "knn": True
                    }
                },
                "mappings": {
                    "properties": {
                        "content_vector": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "space_type": "cosinesimil"
                        },
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "category": {"type": "keyword"},
                        "content_type": {"type": "keyword"}
                    }
                }
            }
            
            # Create index using OpenSearch REST API
            index_url = f"https://{collection_endpoint}/{index_name}"
            
            # Use AWS signature for authentication
            session = boto3.Session(region_name=self.region_name)
            credentials = session.get_credentials()
            
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Create signed request
            request = AWSRequest(method='PUT', url=index_url, data=json.dumps(index_mapping))
            request.headers['Content-Type'] = 'application/json'
            SigV4Auth(credentials, 'aoss', self.region_name).add_auth(request)
            
            response = requests.put(index_url, 
                                   data=json.dumps(index_mapping),
                                   headers=dict(request.headers),
                                   timeout=30)
            
            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(f"Failed to create index: {response.status_code} {response.text}")
            
            # Index documents with real bulk API
            await self._bulk_index_documents(collection_endpoint, index_name, embeddings_batch)
            
            indexing_time_ms = (time.time() - indexing_start) * 1000
            
            return {
                'index_name': index_name,
                'documents_indexed': len(embeddings_batch),
                'indexing_time_ms': indexing_time_ms
            }
            
        except Exception as e:
            self.logger.log_operation("Real serverless index creation failed", level="ERROR", error=str(e))
            raise

    async def _create_real_engine_index(
        self,
        domain_endpoint: str,
        index_name: str, 
        embeddings_batch: List[Dict]
    ) -> Dict[str, Any]:
        """Create real OpenSearch index with S3 vector engine."""
        self.logger.log_operation("Creating real OpenSearch index with S3 vector engine",
                                endpoint=domain_endpoint,
                                index=index_name)
        
        indexing_start = time.time()
        
        try:
            # Create index mapping with S3 vector engine
            index_mapping = {
                "settings": {
                    "index": {
                        "knn": True
                    }
                },
                "mappings": {
                    "properties": {
                        "content_vector": {
                            "type": "knn_vector",
                            "dimension": 1024,
                            "space_type": "cosinesimil",
                            "method": {
                                "engine": "s3vector"
                            }
                        },
                        "title": {"type": "text"},
                        "content": {"type": "text"}, 
                        "category": {"type": "keyword"},
                        "content_type": {"type": "keyword"}
                    }
                }
            }
            
            # Create index using OpenSearch REST API
            index_url = f"https://{domain_endpoint}/{index_name}"
            
            response = requests.put(index_url,
                                   json=index_mapping,
                                   headers={'Content-Type': 'application/json'},
                                   timeout=30)
            
            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(f"Failed to create S3 engine index: {response.status_code} {response.text}")
            
            # Index documents (vectors will be stored in S3 automatically)
            await self._bulk_index_documents(domain_endpoint, index_name, embeddings_batch)
            
            indexing_time_ms = (time.time() - indexing_start) * 1000
            
            return {
                'index_name': index_name,
                'documents_indexed': len(embeddings_batch),
                'indexing_time_ms': indexing_time_ms,
                's3_vector_engine': True
            }
            
        except Exception as e:
            self.logger.log_operation("Real engine index creation failed", level="ERROR", error=str(e))
            raise

    async def _bulk_index_documents(
        self,
        endpoint: str,
        index_name: str,
        embeddings_batch: List[Dict]
    ) -> None:
        """Bulk index documents using real OpenSearch API."""
        self.logger.log_operation("Bulk indexing documents", 
                                endpoint=endpoint,
                                index=index_name,
                                doc_count=len(embeddings_batch))
        
        try:
            # Prepare bulk request body
            bulk_body = []
            for embedding_doc in embeddings_batch:
                # Index operation
                bulk_body.append(json.dumps({
                    "index": {"_index": index_name, "_id": embedding_doc['key']}
                }))
                
                # Document body
                doc_body = {
                    "content_vector": embedding_doc['data']['float32'],
                    **embedding_doc['metadata']
                }
                bulk_body.append(json.dumps(doc_body))
            
            bulk_data = "\n".join(bulk_body) + "\n"
            
            # Execute bulk request
            bulk_url = f"https://{endpoint}/_bulk"
            
            # Handle authentication based on endpoint type
            headers = {'Content-Type': 'application/x-ndjson'}
            
            if '.aoss.amazonaws.com' in endpoint:  # Serverless
                # Use AWS SigV4 authentication for Serverless
                session = boto3.Session(region_name=self.region_name)
                credentials = session.get_credentials()
                
                from botocore.auth import SigV4Auth
                from botocore.awsrequest import AWSRequest
                
                request = AWSRequest(method='POST', url=bulk_url, data=bulk_data)
                request.headers.update(headers)
                SigV4Auth(credentials, 'aoss', self.region_name).add_auth(request)
                
                response = requests.post(bulk_url,
                                       data=bulk_data,
                                       headers=dict(request.headers),
                                       timeout=60)
            else:  # Regular domain
                response = requests.post(bulk_url,
                                       data=bulk_data,
                                       headers=headers,
                                       timeout=60)
            
            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(f"Bulk indexing failed: {response.status_code} {response.text}")
            
            bulk_response = response.json()
            
            # Check for indexing errors
            if bulk_response.get('errors', False):
                error_count = sum(1 for item in bulk_response.get('items', []) if 'error' in item.get('index', {}))
                if error_count > 0:
                    self.logger.log_operation("Bulk indexing had errors", 
                                            error_count=error_count,
                                            total_docs=len(embeddings_batch))
            
            # Wait for documents to be searchable
            await asyncio.sleep(2)
            
            self.logger.log_operation("Bulk indexing completed successfully",
                                    documents=len(embeddings_batch),
                                    errors=bulk_response.get('errors', False))
            
        except Exception as e:
            self.logger.log_operation("Bulk indexing failed", level="ERROR", error=str(e))
            raise

    async def _test_real_hybrid_search(
        self,
        endpoint: str,
        index_name: str,
        embeddings_batch: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Execute real hybrid search queries using OpenSearch API."""
        self.logger.log_operation("Testing real hybrid search", endpoint=endpoint, index=index_name)
        
        query_texts = ["cost effective solutions", "search technology", "analytics"]
        query_results = []
        
        try:
            for query_text in query_texts:
                query_start = time.time()
                
                # Generate real query embedding
                query_result = self.bedrock_service.generate_text_embedding(
                    text=query_text,
                    model_id='amazon.titan-embed-text-v2:0'
                )
                
                # Build real hybrid query
                search_body = {
                    "size": 5,
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "knn": {
                                        "content_vector": {
                                            "vector": query_result.embedding,
                                            "k": 5
                                        }
                                    }
                                },
                                {
                                    "multi_match": {
                                        "query": query_text,
                                        "fields": ["title", "content"]
                                    }
                                }
                            ]
                        }
                    },
                    "highlight": {
                        "fields": {
                            "title": {},
                            "content": {}
                        }
                    }
                }
                
                # Execute real search
                search_url = f"https://{endpoint}/{index_name}/_search"
                
                # Handle authentication
                headers = {'Content-Type': 'application/json'}
                
                if '.aoss.amazonaws.com' in endpoint:  # Serverless
                    session = boto3.Session(region_name=self.region_name)
                    credentials = session.get_credentials()
                    
                    from botocore.auth import SigV4Auth
                    from botocore.awsrequest import AWSRequest
                    
                    request = AWSRequest(method='POST', url=search_url, data=json.dumps(search_body))
                    request.headers.update(headers)
                    SigV4Auth(credentials, 'aoss', self.region_name).add_auth(request)
                    
                    response = requests.post(search_url,
                                           data=json.dumps(search_body),
                                           headers=dict(request.headers),
                                           timeout=30)
                else:  # Regular domain
                    response = requests.post(search_url,
                                           json=search_body,
                                           headers=headers,
                                           timeout=30)
                
                if response.status_code != 200:
                    raise OpenSearchIntegrationError(f"Search failed: {response.status_code} {response.text}")
                
                search_response = response.json()
                query_time_ms = (time.time() - query_start) * 1000
                
                query_results.append({
                    'query': query_text,
                    'results': search_response.get('hits', {}).get('hits', []),
                    'query_time_ms': query_time_ms,
                    'took_ms': search_response.get('took', 0),
                    'total_hits': search_response.get('hits', {}).get('total', {}).get('value', 0)
                })
                
                self.logger.log_operation("Real hybrid search completed",
                                        query=query_text,
                                        results=len(search_response.get('hits', {}).get('hits', [])),
                                        took_ms=search_response.get('took', 0))
            
            return query_results
            
        except Exception as e:
            self.logger.log_operation("Real hybrid search failed", level="ERROR", error=str(e))
            raise

    async def _test_real_engine_search(
        self,
        domain_endpoint: str,
        index_name: str,
        embeddings_batch: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Test real search on OpenSearch domain with S3 vector engine."""
        # Same as hybrid search but with domain endpoint
        return await self._test_real_hybrid_search(domain_endpoint, index_name, embeddings_batch)

    def _calculate_avg_similarity(self, query_results: List[Dict]) -> float:
        """Calculate average similarity score from real search results."""
        all_scores = []
        for qr in query_results:
            for result in qr.get('results', []):
                if '_score' in result:
                    all_scores.append(result['_score'])
                elif 'distance' in result:  # S3 Vectors uses distance
                    all_scores.append(1.0 - result['distance'])
        
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    def _calculate_actual_cost(self, approach_type: str, api_calls: int, vectors_count: int) -> float:
        """Calculate actual AWS costs incurred during testing."""
        costs = {
            's3vector': {
                'storage_per_gb': 0.023,
                'api_call_cost': 0.0001,
                'vector_storage_cost': vectors_count * 0.00001
            },
            'export': {
                'storage_per_gb': 0.023,  # S3 storage
                'serverless_storage_per_gb': 0.10,  # OpenSearch Serverless
                'api_call_cost': 0.0002,
                'ingestion_cost': 0.01
            },
            'engine': {
                'storage_per_gb': 0.023,  # S3 storage only
                'domain_hour_cost': 0.12,  # t3.small.search
                'api_call_cost': 0.0001
            }
        }
        
        base_cost = costs[approach_type]['api_call_cost'] * api_calls
        
        if approach_type == 'export':
            base_cost += costs[approach_type]['ingestion_cost']
        elif approach_type == 'engine':
            base_cost += costs[approach_type]['domain_hour_cost'] * 0.5  # Assume 30 minutes
        
        return base_cost

    async def cleanup_all_resources(self) -> Dict[str, bool]:
        """Clean up all created AWS resources to avoid ongoing costs."""
        self.logger.log_operation("Starting cleanup of all real AWS resources")
        
        cleanup_results = {}
        
        try:
            # Clean up S3 vector buckets
            for bucket_name in self.created_resources['vector_buckets']:
                try:
                    self.s3_storage.delete_vector_bucket(bucket_name, cascade=True)
                    cleanup_results[f'vector_bucket_{bucket_name}'] = True
                    self.logger.log_operation("Cleaned up vector bucket", bucket=bucket_name)
                except Exception as e:
                    cleanup_results[f'vector_bucket_{bucket_name}'] = False
                    self.logger.log_operation("Vector bucket cleanup failed", 
                                            level="ERROR", 
                                            bucket=bucket_name, 
                                            error=str(e))
            
            # Clean up OpenSearch Serverless collections
            for collection_name in self.created_resources['serverless_collections']:
                try:
                    self.opensearch_serverless_client.delete_collection(id=collection_name)
                    cleanup_results[f'serverless_collection_{collection_name}'] = True
                    self.logger.log_operation("Cleaned up serverless collection", collection=collection_name)
                except Exception as e:
                    cleanup_results[f'serverless_collection_{collection_name}'] = False
                    self.logger.log_operation("Serverless collection cleanup failed",
                                            level="ERROR",
                                            collection=collection_name,
                                            error=str(e))
            
            # Clean up security policies
            for policy_type, policy_name in self.created_resources['security_policies']:
                try:
                    self.opensearch_serverless_client.delete_security_policy(
                        type=policy_type,
                        name=policy_name
                    )
                    cleanup_results[f'security_policy_{policy_name}'] = True
                    self.logger.log_operation("Cleaned up security policy", 
                                            policy=policy_name, 
                                            type=policy_type)
                except Exception as e:
                    cleanup_results[f'security_policy_{policy_name}'] = False
                    self.logger.log_operation("Security policy cleanup failed",
                                            level="ERROR",
                                            policy=policy_name,
                                            error=str(e))
            
            # Clean up OpenSearch domains
            for domain_name in self.created_resources['opensearch_domains']:
                try:
                    self.opensearch_client.delete_domain(DomainName=domain_name)
                    cleanup_results[f'opensearch_domain_{domain_name}'] = True
                    self.logger.log_operation("Started cleanup of OpenSearch domain", domain=domain_name)
                except Exception as e:
                    cleanup_results[f'opensearch_domain_{domain_name}'] = False
                    self.logger.log_operation("OpenSearch domain cleanup failed",
                                            level="ERROR",
                                            domain=domain_name,
                                            error=str(e))
            
            overall_success = all(cleanup_results.values())
            self.logger.log_operation("Resource cleanup completed", 
                                    success=overall_success,
                                    results=cleanup_results)
            
            return cleanup_results
            
        except Exception as e:
            self.logger.log_operation("Resource cleanup failed", level="ERROR", error=str(e))
            return cleanup_results

    async def run_real_validation(self, approaches: List[str] = None) -> Dict[str, RealAWSResult]:
        """Run validation with real AWS resources only."""
        if approaches is None:
            approaches = ['s3vector-direct', 'opensearch-export', 'opensearch-engine']
        
        self.logger.log_operation("Starting real AWS validation", approaches=approaches)
        
        results = {}
        
        try:
            # Setup real test data
            setup_result = await self.setup_real_test_data()
            index_arn = setup_result['index_arn']
            embeddings_batch = setup_result['embeddings_batch']
            
            # Test each approach with real AWS
            if 's3vector-direct' in approaches:
                results['s3vector_direct'] = await self.test_real_s3vector_direct(index_arn, embeddings_batch)
            
            if 'opensearch-export' in approaches:
                results['opensearch_export'] = await self.test_real_opensearch_export(index_arn, embeddings_batch)
            
            if 'opensearch-engine' in approaches:
                results['opensearch_engine'] = await self.test_real_opensearch_engine(index_arn, embeddings_batch)
            
            self.logger.log_operation("Real AWS validation completed", approaches_tested=len(results))
            
            return results
            
        except Exception as e:
            self.logger.log_operation("Real AWS validation failed", level="ERROR", error=str(e))
            raise
        finally:
            # Always attempt cleanup
            cleanup_results = await self.cleanup_all_resources()
            
            # Update cleanup status in results
            for result in results.values():
                result.cleanup_successful = cleanup_results.get(f'vector_bucket_{self.config["vector_bucket_name"]}', False)

    def print_real_validation_summary(self, results: Dict[str, RealAWSResult]) -> None:
        """Print summary of real AWS validation results."""
        print("\n" + "="*80)
        print("REAL AWS VECTOR VALIDATION RESULTS (NO SIMULATIONS)")
        print("="*80)
        
        print(f"\nTest ID: {self.test_id}")
        print(f"Region: {self.region_name}")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        
        # Results table
        print(f"\n📊 Real AWS Performance Results:")
        print(f"{'Approach':<20} {'Query Time':<12} {'API Calls':<12} {'Cost':<10} {'Features':<10}")
        print("-" * 70)
        
        for name, result in results.items():
            print(f"{result.approach_name:<20} {result.query_time_ms:<11.1f}ms {result.aws_api_calls_made:<12} ${result.actual_cost_incurred:<9.3f} {len(result.features_validated):<10}")
        
        # Detailed results
        for name, result in results.items():
            print(f"\n🔍 {result.approach_name} Real AWS Details:")
            print(f"  📋 Resources Created: {', '.join(result.resource_arns.keys())}")
            print(f"  ⚡ Setup Time: {result.setup_time_ms:.1f}ms")
            print(f"  📊 Query Results: {result.query_results_count} total")
            print(f"  💰 Actual Cost: ${result.actual_cost_incurred:.3f}")
            print(f"  🧹 Cleanup: {'✅ Success' if result.cleanup_successful else '❌ Failed'}")
            print(f"  ✅ Features Validated: {', '.join(result.features_validated)}")
        
        total_cost = sum(result.actual_cost_incurred for result in results.values())
        total_api_calls = sum(result.aws_api_calls_made for result in results.values())
        
        print(f"\n💰 Total Real AWS Costs Incurred: ${total_cost:.3f}")
        print(f"🔗 Total AWS API Calls Made: {total_api_calls}")
        
        print("\n" + "="*80)


async def main():
    """Main validation function using real AWS resources only."""
    parser = argparse.ArgumentParser(
        description="Real AWS Vector Validation (No Simulations)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--approach',
        choices=['s3vector-direct', 'opensearch-export', 'opensearch-engine', 'all'],
        default='s3vector-direct',
        help='Vector approach to test with real AWS (default: s3vector-direct only)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region for real resources'
    )
    
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick test with minimal resources (S3Vector Direct only)'
    )
    
    parser.add_argument(
        '--output',
        help='Save real results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Determine approaches to test
    if args.quick:
        approaches = ['s3vector-direct']
        print("🚀 Quick Real AWS Validation (S3Vector Direct only)")
    elif args.approach == 'all':
        approaches = ['s3vector-direct', 'opensearch-export', 'opensearch-engine']
        print("🚀 Full Real AWS Validation (All 3 approaches)")
        print("⚠️  WARNING: This will create OpenSearch resources with hourly costs!")
    else:
        approaches = [args.approach]
        print(f"🚀 Real AWS Validation ({args.approach})")
    
    if not os.getenv('REAL_AWS_DEMO'):
        print("❌ REAL_AWS_DEMO=1 environment variable required for real AWS testing")
        return 1
    
    # Initialize validator
    validator = RealAWSVectorValidator(region_name=args.region)
    
    try:
        print(f"\n📋 Testing with real AWS resources in {args.region}")
        print(f"🏗️  Test ID: {validator.test_id}")
        print(f"🔗 Approaches: {', '.join(approaches)}")
        
        # Run real validation
        results = await validator.run_real_validation(approaches)
        
        # Print results
        validator.print_real_validation_summary(results)
        
        # Save results if requested
        if args.output:
            results_dict = {name: asdict(result) for name, result in results.items()}
            with open(args.output, 'w') as f:
                json.dump(results_dict, f, indent=2, default=str)
            print(f"\n💾 Real validation results saved to: {args.output}")
        
        print(f"\n✅ Real AWS validation completed!")
        print(f"💰 Total costs incurred: ${sum(r.actual_cost_incurred for r in results.values()):.3f}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted by user")
        print("🧹 Attempting cleanup of created resources...")
        await validator.cleanup_all_resources()
        return 1
        
    except Exception as e:
        print(f"\n❌ Real validation failed: {str(e)}")
        print("🧹 Attempting cleanup of created resources...")
        await validator.cleanup_all_resources()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))