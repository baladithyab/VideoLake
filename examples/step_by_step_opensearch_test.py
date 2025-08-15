#!/usr/bin/env python3
"""
Step-by-Step OpenSearch Real AWS Testing

This script tests OpenSearch integration patterns step-by-step with real AWS resources,
handling the long setup times and providing progress updates.

Focused on validating actual AWS API calls and resource creation.

Usage:
    export REAL_AWS_DEMO=1
    python examples/step_by_step_opensearch_test.py --test security-policies
    python examples/step_by_step_opensearch_test.py --test serverless-collection
    python examples/step_by_step_opensearch_test.py --test domain-creation
    python examples/step_by_step_opensearch_test.py --test all-quick
"""

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

import boto3
import requests
from botocore.exceptions import ClientError

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.logging_config import setup_logging, get_structured_logger


class StepByStepOpenSearchTester:
    """Step-by-step testing of OpenSearch integration with real AWS."""
    
    def __init__(self, region_name: str = "us-east-1"):
        setup_logging()
        self.logger = get_structured_logger(__name__)
        self.region_name = region_name
        self.test_id = uuid.uuid4().hex[:8]
        
        # AWS clients
        self.opensearch_serverless_client = boto3.client('opensearchserverless', region_name=region_name)
        self.opensearch_client = boto3.client('opensearch', region_name=region_name)
        self.s3_storage = S3VectorStorageManager()
        self.bedrock_service = BedrockEmbeddingService()
        
        # Track created resources for cleanup including IDs
        self.created_resources = {
            'collections': [],  # Will store (name, id) tuples
            'domains': [],
            'security_policies': [],  # Will store (type, name) tuples
            'access_policies': []  # Will store policy names
        }
        
        self.config = {
            'collection_name': f'test-vectors-{self.test_id}',
            'domain_name': f'test-domain-{self.test_id}',
            'bucket_name': f'test-vectors-{self.test_id}'
        }
        
        print(f"🧪 OpenSearch Tester initialized (Test ID: {self.test_id})")

    async def test_security_policies_creation(self) -> Dict[str, Any]:
        """Test creation of OpenSearch Serverless security policies."""
        print("\n🔐 Testing Security Policies Creation...")
        
        collection_name = self.config['collection_name']
        results = {}
        
        try:
            # Test encryption policy creation (correct format)
            encryption_policy_name = f"test-encryption-{self.test_id}"
            encryption_policy = {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AWSOwnedKey": True
            }
            
            print(f"   Creating encryption policy: {encryption_policy_name}")
            
            encryption_response = self.opensearch_serverless_client.create_security_policy(
                type='encryption',
                name=encryption_policy_name,
                policy=json.dumps(encryption_policy),
                description=f"Test encryption policy for {collection_name}"
            )
            
            # Track for cleanup
            self.created_resources['security_policies'].append(('encryption', encryption_policy_name))
            
            results['encryption_policy'] = {
                'name': encryption_policy_name,
                'status': 'created',
                'policy_version': encryption_response['securityPolicyDetail']['policyVersion']
            }
            print(f"   ✅ Encryption policy created successfully")
            
            # Test network policy creation (array format)
            network_policy_name = f"test-network-{self.test_id}" 
            network_policy = [
                {
                    "Description": f"Public access for test collection {collection_name}",
                    "Rules": [
                        {
                            "ResourceType": "collection",
                            "Resource": [f"collection/{collection_name}"]
                        }
                    ],
                    "AllowFromPublic": True
                }
            ]
            
            print(f"   Creating network policy: {network_policy_name}")
            
            network_response = self.opensearch_serverless_client.create_security_policy(
                type='network',
                name=network_policy_name,
                policy=json.dumps(network_policy),
                description=f"Test network policy for {collection_name}"
            )
            
            # Track for cleanup
            self.created_resources['security_policies'].append(('network', network_policy_name))
            
            results['network_policy'] = {
                'name': network_policy_name,
                'status': 'created',
                'policy_version': network_response['securityPolicyDetail']['policyVersion']
            }
            print(f"   ✅ Network policy created successfully")
            
            results['overall_status'] = 'success'
            print(f"   🎉 Security policies creation SUCCESSFUL!")
            
            return results
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            print(f"   ❌ Security policy creation failed: {error_code} - {error_msg}")
            results['error'] = {'code': error_code, 'message': error_msg}
            results['overall_status'] = 'failed'
            return results
        except Exception as e:
            print(f"   ❌ Unexpected error: {str(e)}")
            results['error'] = {'message': str(e)}
            results['overall_status'] = 'failed'
            return results

    async def test_serverless_collection_creation(self) -> Dict[str, Any]:
        """Test creation of OpenSearch Serverless collection."""
        print("\n🏗️ Testing Serverless Collection Creation...")
        
        collection_name = self.config['collection_name']
        results = {}
        
        try:
            # First ensure security policies exist
            policies_result = await self.test_security_policies_creation()
            if policies_result['overall_status'] != 'success':
                print(f"   ⚠️ Security policies failed, cannot create collection")
                return policies_result
            
            print(f"   Creating OpenSearch Serverless collection: {collection_name}")
            start_time = time.time()
            
            collection_response = self.opensearch_serverless_client.create_collection(
                name=collection_name,
                type='VECTORSEARCH',
                description=f'Test vector search collection for real AWS validation'
            )
            
            collection_id = collection_response['createCollectionDetail']['id']
            collection_arn = collection_response['createCollectionDetail']['arn']
            
            # Track for cleanup
            self.created_resources['collections'].append((collection_name, collection_id))
            
            print(f"   📋 Collection creation initiated: {collection_id}")
            print(f"   ⏱️ Waiting for collection to become active (may take 5-10 minutes)...")
            
            # Wait for collection to become active with progress updates
            active_collection = await self._wait_for_collection_with_progress(collection_name, timeout_minutes=12)
            
            setup_time_seconds = time.time() - start_time
            
            results.update({
                'collection_name': collection_name,
                'collection_id': collection_id,
                'collection_arn': collection_arn,
                'status': 'active',
                'setup_time_seconds': setup_time_seconds,
                'endpoint': f"{collection_id}.{self.region_name}.aoss.amazonaws.com",
                'overall_status': 'success'
            })
            
            print(f"   ✅ Collection is ACTIVE after {setup_time_seconds:.1f} seconds")
            print(f"   🔗 Endpoint: {results['endpoint']}")
            
            return results
            
        except Exception as e:
            print(f"   ❌ Collection creation failed: {str(e)}")
            results['error'] = str(e)
            results['overall_status'] = 'failed'
            return results

    async def test_real_hybrid_search_api(self, collection_endpoint: str) -> Dict[str, Any]:
        """Test real hybrid search API calls with OpenSearch Serverless."""
        print("\n🔍 Testing Real Hybrid Search API...")
        
        results = {}
        
        try:
            # Create data access policy for the collection
            collection_name = self.config['collection_name']
            await self._create_data_access_policy(collection_name)
            
            # Create a simple test index
            index_name = 'test-hybrid-index'
            print(f"   Creating test index: {index_name}")
            
            # Create index with vector field
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
                        "content": {"type": "text"}
                    }
                }
            }
            
            # Test real index creation API
            index_url = f"https://{collection_endpoint}/{index_name}"
            
            # Use AWS SigV4 authentication
            session = boto3.Session(region_name=self.region_name)
            credentials = session.get_credentials()
            
            from botocore.auth import SigV4Auth
            from botocore.awsrequest import AWSRequest
            
            # Create index
            create_request = AWSRequest(method='PUT', url=index_url, data=json.dumps(index_mapping))
            create_request.headers['Content-Type'] = 'application/json'
            SigV4Auth(credentials, 'aoss', self.region_name).add_auth(create_request)
            
            create_response = requests.put(
                index_url,
                data=json.dumps(index_mapping),
                headers=dict(create_request.headers),
                timeout=30
            )
            
            if create_response.status_code not in [200, 201]:
                raise Exception(f"Index creation failed: {create_response.status_code} {create_response.text}")
            
            print(f"   ✅ Test index created successfully")
            
            # Test document indexing
            print(f"   Testing document indexing...")
            
            # Generate a test embedding
            embedding_result = self.bedrock_service.generate_text_embedding(
                text="This is a test document for hybrid search validation",
                model_id='amazon.titan-embed-text-v2:0'
            )
            
            # Index a test document
            doc_id = "test-doc-1"
            test_doc = {
                "content_vector": embedding_result.embedding,
                "title": "Test Document",
                "content": "This is a test document for hybrid search validation with vector embeddings"
            }
            
            doc_url = f"https://{collection_endpoint}/{index_name}/_doc/{doc_id}"
            
            index_request = AWSRequest(method='POST', url=doc_url, data=json.dumps(test_doc))
            index_request.headers['Content-Type'] = 'application/json'
            SigV4Auth(credentials, 'aoss', self.region_name).add_auth(index_request)
            
            index_response = requests.post(
                doc_url,
                data=json.dumps(test_doc),
                headers=dict(index_request.headers),
                timeout=30
            )
            
            if index_response.status_code not in [200, 201]:
                raise Exception(f"Document indexing failed: {index_response.status_code} {index_response.text}")
            
            print(f"   ✅ Document indexed successfully")
            
            # Wait for document to be searchable
            await asyncio.sleep(3)
            
            # Test real hybrid search
            print(f"   Testing real hybrid search...")
            
            search_query = {
                "size": 5,
                "query": {
                    "bool": {
                        "should": [
                            {
                                "knn": {
                                    "content_vector": {
                                        "vector": embedding_result.embedding,
                                        "k": 5
                                    }
                                }
                            },
                            {
                                "multi_match": {
                                    "query": "test document validation",
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
            
            search_url = f"https://{collection_endpoint}/{index_name}/_search"
            
            search_request = AWSRequest(method='POST', url=search_url, data=json.dumps(search_query))
            search_request.headers['Content-Type'] = 'application/json'
            SigV4Auth(credentials, 'aoss', self.region_name).add_auth(search_request)
            
            search_start = time.time()
            search_response = requests.post(
                search_url,
                data=json.dumps(search_query),
                headers=dict(search_request.headers),
                timeout=30
            )
            search_time_ms = (time.time() - search_start) * 1000
            
            if search_response.status_code != 200:
                raise Exception(f"Search failed: {search_response.status_code} {search_response.text}")
            
            search_result = search_response.json()
            
            print(f"   ✅ Hybrid search executed successfully")
            print(f"   📊 Search took: {search_result.get('took', 0)}ms (OpenSearch) + {search_time_ms:.1f}ms (network)")
            print(f"   📋 Results found: {search_result.get('hits', {}).get('total', {}).get('value', 0)}")
            
            results = {
                'index_created': True,
                'document_indexed': True,
                'hybrid_search_executed': True,
                'search_latency_ms': search_time_ms,
                'opensearch_took_ms': search_result.get('took', 0),
                'results_count': len(search_result.get('hits', {}).get('hits', [])),
                'features_validated': [
                    'Real OpenSearch Serverless collection',
                    'Real index creation with vector fields',
                    'Real document indexing with embeddings',
                    'Real hybrid search (vector + keyword)',
                    'Real AWS SigV4 authentication',
                    'Real search result highlighting'
                ],
                'overall_status': 'success'
            }
            
            return results
            
        except Exception as e:
            print(f"   ❌ Hybrid search API testing failed: {str(e)}")
            return {'error': str(e), 'overall_status': 'failed'}

    async def test_opensearch_domain_engine(self) -> Dict[str, Any]:
        """Test OpenSearch domain creation with S3 vectors engine."""
        print("\n🏛️ Testing OpenSearch Domain with S3 Vectors Engine...")
        
        domain_name = self.config['domain_name']
        results = {}
        
        try:
            print(f"   Creating OpenSearch domain: {domain_name}")
            print(f"   ⚠️ This typically takes 15-20 minutes...")
            
            # Create minimal domain for testing
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
                })
            )
            
            domain_arn = domain_response['DomainStatus']['ARN']
            
            print(f"   📋 Domain creation initiated: {domain_arn}")
            print(f"   ⏱️ Status: {domain_response['DomainStatus']['Processing']}")
            
            # Check initial status
            describe_response = self.opensearch_client.describe_domain(DomainName=domain_name)
            domain_status = describe_response['DomainStatus']
            
            results = {
                'domain_name': domain_name,
                'domain_arn': domain_arn,
                'creation_initiated': True,
                'engine_version': domain_status['EngineVersion'],
                'instance_type': domain_status['ClusterConfig']['InstanceType'],
                'processing': domain_status['Processing'],
                'endpoint': domain_status.get('Endpoint', 'pending'),
                'overall_status': 'creation_initiated'
            }
            
            if domain_status['Processing']:
                print(f"   ⏳ Domain is being created (Processing: True)")
                print(f"   💡 Full validation would require waiting 15-20 minutes")
                results['validation_note'] = 'Domain creation initiated but not waited for completion due to time constraints'
            else:
                print(f"   ✅ Domain creation completed")
                results['overall_status'] = 'success'
            
            # Test S3 vectors engine configuration (even while processing)
            try:
                print(f"   Testing S3 vectors engine configuration...")
                
                # This will fail while domain is processing, but we can test the API
                engine_response = self.opensearch_client.update_domain_config(
                    DomainName=domain_name,
                    S3VectorsEngine={'Enabled': True}
                )
                
                print(f"   ✅ S3 vectors engine configuration initiated")
                results['s3_vectors_engine'] = 'configuration_initiated'
                
            except ClientError as e:
                if 'Processing' in str(e) or 'InProgress' in str(e):
                    print(f"   ⏳ S3 vectors engine config pending (domain still processing)")
                    results['s3_vectors_engine'] = 'pending_domain_completion'
                else:
                    print(f"   ⚠️ S3 vectors engine config error: {e.response['Error']['Code']}")
                    results['s3_vectors_engine'] = f"error_{e.response['Error']['Code']}"
            
            return results
            
        except Exception as e:
            print(f"   ❌ Domain creation failed: {str(e)}")
            return {'error': str(e), 'overall_status': 'failed'}

    async def _wait_for_collection_with_progress(self, collection_name: str, timeout_minutes: int = 12) -> Dict[str, Any]:
        """Wait for collection to become active with progress updates."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        check_interval = 30  # Check every 30 seconds
        
        while time.time() - start_time < timeout_seconds:
            try:
                response = self.opensearch_serverless_client.batch_get_collection(names=[collection_name])
                collections = response.get('collectionDetails', [])
                
                if collections:
                    status = collections[0]['status']
                    elapsed_minutes = (time.time() - start_time) / 60
                    
                    print(f"   ⏱️ {elapsed_minutes:.1f}min: Collection status = {status}")
                    
                    if status == 'ACTIVE':
                        return collections[0]
                    elif status == 'FAILED':
                        raise Exception(f"Collection creation failed: {collections[0].get('statusReason', 'Unknown error')}")
                else:
                    print(f"   ⏱️ Collection not found yet...")
                
                await asyncio.sleep(check_interval)
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print(f"   ⏱️ Collection not ready yet...")
                    await asyncio.sleep(check_interval)
                else:
                    raise
        
        raise Exception(f"Collection {collection_name} did not become active within {timeout_minutes} minutes")

    async def _create_data_access_policy(self, collection_name: str) -> None:
        """Create data access policy for the collection."""
        try:
            sts_client = boto3.client('sts', region_name=self.region_name)
            caller_identity = sts_client.get_caller_identity()
            
            policy_name = f"test-data-policy-{self.test_id}"
            
            # Data access policy should be array format
            data_policy = [
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
                    "Description": f"Data access policy for test collection {collection_name}"
                }
            ]
            
            self.opensearch_serverless_client.create_access_policy(
                type='data',
                name=policy_name,
                policy=json.dumps(data_policy),
                description=f"Test data access policy"
            )
            
            # Track for cleanup
            self.created_resources['access_policies'].append(policy_name)
            
            # Wait for policy to propagate
            await asyncio.sleep(10)
            
            print(f"   ✅ Data access policy created: {policy_name}")
            
        except ClientError as e:
            if e.response['Error']['Code'] != 'ConflictException':
                raise

    async def cleanup_test_resources(self) -> Dict[str, bool]:
        """Clean up all test resources."""
        print("\n🧹 Cleaning up test resources...")
        
        cleanup_results = {}
        
        # Clean up collections using collection IDs
        for collection_name, collection_id in self.created_resources['collections']:
            try:
                self.opensearch_serverless_client.delete_collection(id=collection_id)
                cleanup_results[f'collection_{collection_name}'] = True
                print(f"   ✅ Collection deletion initiated: {collection_name}")
            except Exception as e:
                cleanup_results[f'collection_{collection_name}'] = False
                print(f"   ⚠️ Collection cleanup failed: {str(e)}")
        
        # Clean up domains
        for domain_name in self.created_resources['domains']:
            try:
                self.opensearch_client.delete_domain(DomainName=domain_name)
                cleanup_results[f'domain_{domain_name}'] = True  
                print(f"   ✅ Domain deletion initiated: {domain_name}")
            except Exception as e:
                cleanup_results[f'domain_{domain_name}'] = False
                print(f"   ⚠️ Domain cleanup failed: {str(e)}")
        
        # Clean up access policies  
        for policy_name in self.created_resources['access_policies']:
            try:
                self.opensearch_serverless_client.delete_access_policy(
                    type='data',
                    name=policy_name
                )
                cleanup_results[f'access_policy_{policy_name}'] = True
                print(f"   ✅ Access policy deleted: {policy_name}")
            except Exception as e:
                cleanup_results[f'access_policy_{policy_name}'] = False
                print(f"   ⚠️ Access policy cleanup failed: {str(e)}")
        
        # Clean up security policies
        for policy_type, policy_name in self.created_resources['security_policies']:
            try:
                self.opensearch_serverless_client.delete_security_policy(
                    type=policy_type,
                    name=policy_name
                )
                cleanup_results[f'{policy_type}_policy_{policy_name}'] = True
                print(f"   ✅ {policy_type.title()} policy deleted: {policy_name}")
            except Exception as e:
                cleanup_results[f'{policy_type}_policy_{policy_name}'] = False
                print(f"   ⚠️ {policy_type.title()} policy cleanup failed: {str(e)}")
        
        return cleanup_results

    async def run_focused_opensearch_tests(self, test_type: str) -> Dict[str, Any]:
        """Run focused OpenSearch tests based on type."""
        all_results = {}
        
        try:
            if test_type in ['security-policies', 'all-quick']:
                results = await self.test_security_policies_creation()
                all_results['security_policies'] = results
                
                if results['overall_status'] != 'success':
                    print(f"❌ Security policies test failed, stopping here")
                    return all_results
            
            if test_type in ['serverless-collection', 'all-quick']:
                results = await self.test_serverless_collection_creation()
                all_results['serverless_collection'] = results
                
                if results['overall_status'] == 'success':
                    # Test hybrid search API
                    endpoint = results['endpoint']
                    search_results = await self.test_real_hybrid_search_api(endpoint)
                    all_results['hybrid_search'] = search_results
            
            if test_type in ['domain-creation', 'all-quick']:
                results = await self.test_opensearch_domain_engine()
                all_results['opensearch_domain'] = results
            
            return all_results
            
        except Exception as e:
            print(f"❌ Focused testing failed: {str(e)}")
            all_results['error'] = str(e)
            return all_results
        finally:
            # Always attempt cleanup
            cleanup_results = await self.cleanup_test_resources()
            all_results['cleanup'] = cleanup_results


async def main():
    """Main testing function."""
    if not os.getenv('REAL_AWS_DEMO'):
        print("❌ Set REAL_AWS_DEMO=1 to run real AWS testing")
        return 1
    
    parser = argparse.ArgumentParser(description="Step-by-Step OpenSearch Real AWS Testing")
    parser.add_argument(
        '--test',
        choices=['security-policies', 'serverless-collection', 'domain-creation', 'all-quick'],
        default='all-quick',
        help='Which test to run'
    )
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    tester = StepByStepOpenSearchTester(region_name=args.region)
    
    try:
        print("🚀 STEP-BY-STEP OPENSEARCH REAL AWS TESTING")
        print("="*60)
        print(f"🌍 Region: {args.region}")
        print(f"🧪 Test Type: {args.test}")
        print(f"🏗️ Test ID: {tester.test_id}")
        
        # Run focused tests
        results = await tester.run_focused_opensearch_tests(args.test)
        
        # Print summary
        print(f"\n📊 OPENSEARCH REAL AWS TEST SUMMARY")
        print("="*60)
        
        for test_name, result in results.items():
            if test_name == 'cleanup':
                continue
                
            if isinstance(result, dict) and 'overall_status' in result:
                status_icon = "✅" if result['overall_status'] == 'success' else "❌" if result['overall_status'] == 'failed' else "⏳"
                print(f"{status_icon} {test_name.replace('_', ' ').title()}: {result['overall_status']}")
                
                if 'features_validated' in result:
                    print(f"   📋 Features: {len(result['features_validated'])} validated")
        
        # Show cleanup results
        if 'cleanup' in results:
            cleanup_success = sum(results['cleanup'].values())
            cleanup_total = len(results['cleanup'])
            print(f"\n🧹 Cleanup: {cleanup_success}/{cleanup_total} resources cleaned")
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        # Determine overall success
        main_tests = [k for k in results.keys() if k != 'cleanup']
        successful_tests = sum(1 for k in main_tests if results[k].get('overall_status') == 'success')
        
        print(f"\n🎯 Overall Result: {successful_tests}/{len(main_tests)} tests successful")
        
        if successful_tests == len(main_tests):
            print("✅ All OpenSearch tests passed!")
            return 0
        else:
            print("⚠️ Some tests failed or incomplete")
            return 1
            
    except Exception as e:
        print(f"\n❌ Testing failed: {str(e)}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))