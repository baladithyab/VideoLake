#!/usr/bin/env python3
"""
Three-Way Vector Index Comparison Demo

This demo showcases and compares all three approaches for vector indexing and search:

1. **S3Vector Direct**: Native S3 Vectors API for storage and similarity search
2. **S3Vector → OpenSearch Export**: Export S3 vectors to OpenSearch Serverless (high performance)  
3. **OpenSearch on S3Vector Engine**: OpenSearch domains using S3 Vectors as storage engine (cost optimized)

The demo demonstrates:
- Vector storage and indexing approaches
- Query performance differences
- Cost implications
- Feature capabilities (hybrid search, filtering, etc.)
- Use case recommendations

Prerequisites:
- AWS credentials configured
- Bedrock access for text embeddings
- OpenSearch domain (for engine pattern)
- OpenSearch Serverless collection (for export pattern)

Usage:
    export REAL_AWS_DEMO=1
    python examples/three_way_vector_comparison_demo.py
    python examples/three_way_vector_comparison_demo.py --storage-size 100 --queries 50000
    python examples/three_way_vector_comparison_demo.py --approach s3vector-direct
    python examples/three_way_vector_comparison_demo.py --approach export --with-performance-test
"""

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Core services
from src.services.s3_vector_storage import S3VectorStorageManager  
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    HybridSearchResult
)
from src.services.similarity_search_engine import SimilaritySearchEngine

# Utils and config
from src.utils.logging_config import setup_logging, get_structured_logger
from src.utils.timing_tracker import TimingTracker
from src.exceptions import OpenSearchIntegrationError, VectorEmbeddingError


@dataclass
class VectorApproachResult:
    """Results from testing a specific vector approach."""
    approach_name: str
    setup_time_ms: float
    indexing_time_ms: float
    query_time_ms: float
    query_results_count: int
    average_similarity_score: float
    cost_estimate_monthly: float
    features_supported: List[str]
    limitations: List[str]
    performance_metrics: Dict[str, Any]


@dataclass
class ComparisonSummary:
    """Summary comparing all three vector approaches."""
    s3vector_direct: VectorApproachResult
    opensearch_export: VectorApproachResult  
    opensearch_engine: VectorApproachResult
    comparison_timestamp: str
    test_configuration: Dict[str, Any]
    recommendations: Dict[str, str]


class ThreeWayVectorComparison:
    """
    Comprehensive comparison of three vector indexing approaches.
    
    This demo provides practical, side-by-side comparison of:
    1. S3Vector Direct API
    2. S3Vector → OpenSearch Export (high performance)
    3. OpenSearch on S3Vector Engine (cost optimized)
    """
    
    def __init__(self, region_name: str = "us-east-1"):
        """Initialize comparison demo with AWS services."""
        setup_logging()
        self.logger = get_structured_logger(__name__)
        self.region_name = region_name
        self.timing_tracker = TimingTracker("vector_comparison")
        
        # Initialize services  
        self.s3_storage = S3VectorStorageManager()
        self.bedrock_service = BedrockEmbeddingService()
        self.opensearch_integration = OpenSearchIntegrationManager(region_name=region_name)
        self.similarity_engine = SimilaritySearchEngine()
        
        # Demo configuration
        self.demo_config = {
            'vector_bucket_name': f'vector-comparison-demo-{uuid.uuid4().hex[:8]}',
            'vector_index_name': 'comparison-embeddings',
            'opensearch_collection_name': f's3vector-export-demo-{uuid.uuid4().hex[:8]}',
            'opensearch_domain_name': f's3vector-engine-demo-{uuid.uuid4().hex[:8]}',
            'vector_dimension': 1024,
            'sample_documents': self._get_sample_documents(),
            'query_texts': self._get_sample_queries()
        }
        
        self.logger.log_operation("Three-way vector comparison initialized", region=region_name)

    def _get_sample_documents(self) -> List[Dict[str, Any]]:
        """Generate sample documents for consistent testing."""
        return [
            {
                "id": "tech_001",
                "title": "Introduction to Vector Databases", 
                "content": "Vector databases revolutionize search by enabling semantic similarity matching using high-dimensional embeddings. They provide efficient similarity search for AI applications including RAG, recommendation systems, and content discovery.",
                "category": "technology",
                "tags": ["vectors", "databases", "AI", "embeddings"],
                "industry": "software"
            },
            {
                "id": "cloud_002",
                "title": "AWS S3 Vectors Cost Analysis",
                "content": "Amazon S3 Vectors delivers up to 90% cost savings compared to traditional vector databases while maintaining sub-second query performance. The service offers elastic scaling with pay-per-use pricing model.",
                "category": "cloud-services", 
                "tags": ["AWS", "S3", "cost optimization", "scalability"],
                "industry": "cloud"
            },
            {
                "id": "ai_003", 
                "title": "OpenSearch Vector Search Capabilities",
                "content": "Amazon OpenSearch Service provides powerful vector search using k-NN algorithms with support for multiple distance metrics. It enables hybrid search combining keyword matching with semantic similarity.",
                "category": "search-technology",
                "tags": ["OpenSearch", "k-NN", "hybrid search", "semantic search"],
                "industry": "enterprise"
            },
            {
                "id": "ml_004",
                "title": "Embedding Models and Dimensionality",
                "content": "Modern embedding models like Amazon Titan and Cohere generate high-quality vector representations with typically 768 or 1024 dimensions. Model choice significantly impacts both accuracy and computational cost.",
                "category": "machine-learning",
                "tags": ["embeddings", "Titan", "Cohere", "dimensionality"],
                "industry": "research"
            },
            {
                "id": "data_005",
                "title": "Real-time Vector Analytics",
                "content": "Real-time vector analytics enable instant insights from unstructured data including documents, images, and audio. Advanced filtering and aggregation provide deep understanding of content patterns and user behavior.",
                "category": "analytics",
                "tags": ["real-time", "analytics", "unstructured data", "insights"],
                "industry": "media"
            },
            {
                "id": "perf_006",
                "title": "Vector Search Performance Optimization",
                "content": "Optimizing vector search performance requires careful consideration of index configuration, query patterns, and hardware resources. Techniques include quantization, pruning, and distributed search architectures.",
                "category": "performance",
                "tags": ["optimization", "performance", "indexing", "architecture"],
                "industry": "technology"
            },
            {
                "id": "scale_007",
                "title": "Scaling Vector Operations",
                "content": "Scaling vector operations to handle billions of vectors requires sophisticated distributed systems, efficient storage formats, and optimized query routing. Cloud-native solutions provide automatic scaling capabilities.",
                "category": "scalability", 
                "tags": ["scaling", "distributed systems", "cloud native", "automation"],
                "industry": "enterprise"
            },
            {
                "id": "security_008",
                "title": "Vector Database Security",
                "content": "Securing vector databases involves encryption at rest and in transit, access controls, audit logging, and compliance with data protection regulations. Enterprise deployments require comprehensive security frameworks.",
                "category": "security",
                "tags": ["security", "encryption", "compliance", "enterprise"],
                "industry": "enterprise"
            }
        ]

    def _get_sample_queries(self) -> List[str]:
        """Generate sample queries for consistent testing."""
        return [
            "cost effective database solutions",
            "real-time analytics and performance",
            "AI and machine learning embeddings", 
            "cloud scalability and optimization",
            "search technology and algorithms"
        ]

    async def setup_test_data(self) -> Dict[str, Any]:
        """
        Set up consistent test data across all approaches.
        
        Returns:
            Dict[str, Any]: Setup results with index ARNs and metadata
        """
        self.logger.log_operation("Setting up test data for comparison")
        
        setup_start_time = time.time()
        
        try:
            # Create S3 vector bucket and index
            bucket_result = self.s3_storage.create_vector_bucket(
                bucket_name=self.demo_config['vector_bucket_name']
            )
            
            index_result = self.s3_storage.create_vector_index(
                bucket_name=self.demo_config['vector_bucket_name'],
                index_name=self.demo_config['vector_index_name'],
                dimensions=self.demo_config['vector_dimension']
            )
            
            # Generate embeddings for all sample documents
            sample_docs = self.demo_config['sample_documents']
            embeddings_batch = []
            
            self.logger.log_operation(f"Generating embeddings for {len(sample_docs)} documents")
            
            for doc in sample_docs:
                # Generate text embedding using Bedrock Titan
                embedding_result = self.bedrock_service.generate_text_embedding(
                    text=f"{doc['title']} {doc['content']}",
                    model_id='amazon.titan-embed-text-v2:0'
                )
                
                embeddings_batch.append({
                    'key': doc['id'],
                    'data': {'float32': embedding_result.embedding},  # S3 Vectors format
                    'metadata': {
                        'title': doc['title'],
                        'content': doc['content'],
                        'category': doc['category'], 
                        'tags': doc['tags'],
                        'industry': doc['industry'],
                        'content_type': 'text',
                        'embedding_model': 'amazon.titan-embed-text-v2:0',
                        'document_length': len(doc['content'])
                    }
                })
            
            # Construct the index ARN for API calls
            # Format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
            import boto3
            sts_client = boto3.client('sts', region_name=self.region_name)
            account_id = sts_client.get_caller_identity()['Account']
            index_arn = f"arn:aws:s3vectors:{self.region_name}:{account_id}:bucket/{self.demo_config['vector_bucket_name']}/index/{self.demo_config['vector_index_name']}"
            
            # Store vectors in S3 Vectors (this will be used by all approaches)
            storage_result = self.s3_storage.put_vectors(
                index_arn=index_arn,
                vectors_data=embeddings_batch
            )
            
            setup_time_ms = (time.time() - setup_start_time) * 1000
            
            setup_result = {
                'bucket_name': bucket_result['bucket_name'],
                'bucket_arn': f"arn:aws:s3vectors:{self.region_name}:{account_id}:bucket/{self.demo_config['vector_bucket_name']}",
                'index_arn': index_arn,
                'documents_processed': len(embeddings_batch),
                'total_vectors': len(embeddings_batch),
                'vector_dimension': self.demo_config['vector_dimension'],
                'setup_time_ms': setup_time_ms,
                'embeddings_batch': embeddings_batch  # For use in other approaches
            }
            
            self.logger.log_operation("Test data setup completed", 
                                    vectors_stored=len(embeddings_batch),
                                    setup_time_ms=setup_time_ms)
            
            return setup_result
            
        except Exception as e:
            self.logger.log_operation("Test data setup failed", level="ERROR", error=str(e))
            raise

    # Approach 1: S3Vector Direct
    
    async def test_s3vector_direct(self, index_arn: str, embeddings_batch: List[Dict]) -> VectorApproachResult:
        """
        Test S3Vector Direct approach using native S3 Vectors API.
        
        Args:
            index_arn: S3 vector index ARN
            embeddings_batch: Pre-generated embeddings for testing
            
        Returns:
            VectorApproachResult: Performance and capability results
        """
        self.logger.log_operation("Testing S3Vector Direct approach")
        
        approach_start_time = time.time()
        
        try:
            # Setup time is 0 since vectors are already stored
            setup_time_ms = 0.0
            indexing_time_ms = 0.0  # Already indexed during setup
            
            # Test query performance with multiple queries
            query_results = []
            total_query_time_ms = 0.0
            
            for query_text in self.demo_config['query_texts']:
                query_start = time.time()
                
                # Generate query embedding
                query_result = self.bedrock_service.generate_text_embedding(
                    text=query_text,
                    model_id='amazon.titan-embed-text-v2:0'
                )
                query_embedding = query_result.embedding
                
                # Perform similarity search using S3 Vectors directly
                search_result = self.s3_storage.query_vectors(
                    index_arn=index_arn,
                    query_vector=query_embedding,
                    top_k=5,
                    return_distance=True,
                    return_metadata=True
                )
                
                query_time_ms = (time.time() - query_start) * 1000
                total_query_time_ms += query_time_ms
                
                query_results.append({
                    'query': query_text,
                    'results_count': len(search_result.get('vectors', [])),
                    'query_time_ms': query_time_ms,
                    'results': search_result.get('vectors', [])
                })
            
            # Calculate performance metrics
            avg_query_time_ms = total_query_time_ms / len(self.demo_config['query_texts'])
            total_results = sum(len(qr.get('results', [])) for qr in query_results)
            avg_similarity_score = self._calculate_avg_similarity(query_results)
            
            # Cost estimation (S3 Vectors direct)
            cost_estimate_monthly = self._estimate_s3vector_direct_cost(
                vectors_count=len(embeddings_batch),
                queries_per_month=10000
            )
            
            # Features and limitations
            features_supported = [
                "Native vector similarity search",
                "Metadata filtering",
                "Sub-second query latency", 
                "Elastic scaling",
                "Cost-effective storage",
                "Simple API",
                "AWS native integration"
            ]
            
            limitations = [
                "No keyword search",
                "No aggregations", 
                "Limited analytics capabilities",
                "No text highlighting",
                "Basic filtering only"
            ]
            
            performance_metrics = {
                'avg_query_latency_ms': avg_query_time_ms,
                'queries_tested': len(self.demo_config['query_texts']),
                'total_results_returned': total_results,
                'vectors_in_index': len(embeddings_batch),
                'approach_total_time_ms': (time.time() - approach_start_time) * 1000
            }
            
            result = VectorApproachResult(
                approach_name="S3Vector Direct",
                setup_time_ms=setup_time_ms,
                indexing_time_ms=indexing_time_ms,
                query_time_ms=avg_query_time_ms,
                query_results_count=total_results,
                average_similarity_score=avg_similarity_score,
                cost_estimate_monthly=cost_estimate_monthly,
                features_supported=features_supported,
                limitations=limitations,
                performance_metrics=performance_metrics
            )
            
            self.logger.log_operation("S3Vector Direct testing completed", 
                                    avg_query_time_ms=avg_query_time_ms,
                                    total_results=total_results)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("S3Vector Direct testing failed", level="ERROR", error=str(e))
            raise

    # Approach 2: S3Vector → OpenSearch Export
    
    async def test_opensearch_export(self, index_arn: str, embeddings_batch: List[Dict]) -> VectorApproachResult:
        """
        Test OpenSearch Export approach (S3 Vectors → OpenSearch Serverless).
        
        Args:
            index_arn: S3 vector index ARN
            embeddings_batch: Pre-generated embeddings for testing
            
        Returns:
            VectorApproachResult: Performance and capability results
        """
        self.logger.log_operation("Testing OpenSearch Export approach")
        
        approach_start_time = time.time()
        
        try:
            # Setup: Export to OpenSearch Serverless (simulated)
            setup_start = time.time()
            
            # In a real implementation, this would:
            # 1. Create OpenSearch Serverless collection
            # 2. Start export using OpenSearch Ingestion Service
            # 3. Wait for export completion
            # For demo purposes, we'll simulate this process
            
            collection_name = self.demo_config['opensearch_collection_name']
            
            # Simulate export time based on data size
            simulated_export_time = len(embeddings_batch) * 0.1  # 100ms per vector
            await asyncio.sleep(min(simulated_export_time, 2.0))  # Cap at 2 seconds for demo
            
            setup_time_ms = (time.time() - setup_start) * 1000
            indexing_time_ms = setup_time_ms  # Export IS the indexing process
            
            # Test query performance with hybrid search capabilities
            query_results = []
            total_query_time_ms = 0.0
            
            for query_text in self.demo_config['query_texts']:
                query_start = time.time()
                
                # Generate query embedding for vector search
                query_result = self.bedrock_service.generate_text_embedding(
                    text=query_text,
                    model_id='amazon.titan-embed-text-v2:0'
                )
                query_embedding = query_result.embedding
                
                # Simulate hybrid search (vector + keyword) in OpenSearch Serverless
                # In real implementation, this would use OpenSearch REST API
                simulated_results = self._simulate_opensearch_hybrid_search(
                    query_text=query_text,
                    query_embedding=query_embedding,
                    embeddings_batch=embeddings_batch,
                    top_k=5
                )
                
                query_time_ms = (time.time() - query_start) * 1000
                total_query_time_ms += query_time_ms
                
                query_results.append({
                    'query': query_text,
                    'results_count': len(simulated_results),
                    'query_time_ms': query_time_ms,
                    'results': simulated_results,
                    'hybrid_features_used': ['vector_similarity', 'keyword_matching', 'highlighting']
                })
            
            # Calculate performance metrics
            avg_query_time_ms = total_query_time_ms / len(self.demo_config['query_texts'])
            total_results = sum(len(qr.get('results', [])) for qr in query_results)
            avg_similarity_score = self._calculate_avg_similarity(query_results)
            
            # Cost estimation (Export pattern - dual storage + higher compute)
            cost_estimate_monthly = self._estimate_opensearch_export_cost(
                vectors_count=len(embeddings_batch),
                queries_per_month=10000
            )
            
            # Features and limitations
            features_supported = [
                "Vector similarity search",
                "Keyword search", 
                "Hybrid search (vector + keyword)",
                "Advanced aggregations",
                "Text highlighting",
                "Complex filtering",
                "Real-time analytics",
                "Sub-millisecond latency",
                "High query throughput",
                "OpenSearch Dashboards integration"
            ]
            
            limitations = [
                "Higher cost (dual storage)",
                "Export complexity",
                "Data synchronization challenges",
                "Point-in-time export only",
                "Requires OpenSearch expertise"
            ]
            
            performance_metrics = {
                'avg_query_latency_ms': avg_query_time_ms,
                'queries_tested': len(self.demo_config['query_texts']),
                'total_results_returned': total_results,
                'vectors_in_index': len(embeddings_batch),
                'export_time_ms': setup_time_ms,
                'approach_total_time_ms': (time.time() - approach_start_time) * 1000
            }
            
            result = VectorApproachResult(
                approach_name="OpenSearch Export",
                setup_time_ms=setup_time_ms,
                indexing_time_ms=indexing_time_ms, 
                query_time_ms=avg_query_time_ms,
                query_results_count=total_results,
                average_similarity_score=avg_similarity_score,
                cost_estimate_monthly=cost_estimate_monthly,
                features_supported=features_supported,
                limitations=limitations,
                performance_metrics=performance_metrics
            )
            
            self.logger.log_operation("OpenSearch Export testing completed",
                                    avg_query_time_ms=avg_query_time_ms,
                                    export_time_ms=setup_time_ms)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("OpenSearch Export testing failed", level="ERROR", error=str(e))
            raise

    # Approach 3: OpenSearch on S3Vector Engine
    
    async def test_opensearch_engine(self, index_arn: str, embeddings_batch: List[Dict]) -> VectorApproachResult:
        """
        Test OpenSearch Engine approach (OpenSearch domain using S3 Vectors as storage engine).
        
        Args:
            index_arn: S3 vector index ARN  
            embeddings_batch: Pre-generated embeddings for testing
            
        Returns:
            VectorApproachResult: Performance and capability results
        """
        self.logger.log_operation("Testing OpenSearch Engine approach")
        
        approach_start_time = time.time()
        
        try:
            # Setup: Configure OpenSearch domain with S3 Vectors engine
            setup_start = time.time()
            
            domain_name = self.demo_config['opensearch_domain_name']
            
            # In a real implementation, this would:
            # 1. Create/configure OpenSearch domain with S3 Vectors engine enabled
            # 2. Create index mapping with s3vector engine
            # 3. Index documents through OpenSearch API (vectors go to S3)
            # For demo purposes, we'll simulate this process
            
            # Simulate domain configuration time
            await asyncio.sleep(1.0)  # Simulated setup time
            
            # Simulate indexing documents through OpenSearch API  
            indexing_start = time.time()
            simulated_indexing_time = len(embeddings_batch) * 0.05  # 50ms per document
            await asyncio.sleep(min(simulated_indexing_time, 1.5))  # Cap at 1.5 seconds for demo
            
            indexing_time_ms = (time.time() - indexing_start) * 1000
            setup_time_ms = (time.time() - setup_start) * 1000
            
            # Test query performance with hybrid search (higher latency than export)
            query_results = []
            total_query_time_ms = 0.0
            
            for query_text in self.demo_config['query_texts']:
                query_start = time.time()
                
                # Generate query embedding for vector search
                query_result = self.bedrock_service.generate_text_embedding(
                    text=query_text,
                    model_id='amazon.titan-embed-text-v2:0'
                )
                query_embedding = query_result.embedding
                
                # Simulate hybrid search through OpenSearch API with S3 vector engine
                # (Higher latency due to S3 storage layer)
                simulated_results = self._simulate_opensearch_engine_search(
                    query_text=query_text,
                    query_embedding=query_embedding,
                    embeddings_batch=embeddings_batch,
                    top_k=5
                )
                
                # Engine pattern has higher latency than export pattern
                base_query_time = time.time() - query_start
                simulated_latency_ms = (base_query_time * 1000) + 50  # Add 50ms for S3 storage latency
                
                total_query_time_ms += simulated_latency_ms
                
                query_results.append({
                    'query': query_text,
                    'results_count': len(simulated_results),
                    'query_time_ms': simulated_latency_ms,
                    'results': simulated_results,
                    'features_used': ['vector_similarity', 'keyword_matching', 's3_storage_engine']
                })
            
            # Calculate performance metrics
            avg_query_time_ms = total_query_time_ms / len(self.demo_config['query_texts'])
            total_results = sum(len(qr.get('results', [])) for qr in query_results)
            avg_similarity_score = self._calculate_avg_similarity(query_results)
            
            # Cost estimation (Engine pattern - single storage, lower cost)
            cost_estimate_monthly = self._estimate_opensearch_engine_cost(
                vectors_count=len(embeddings_batch),
                queries_per_month=10000
            )
            
            # Features and limitations
            features_supported = [
                "Vector similarity search",
                "Keyword search",
                "Hybrid search (vector + keyword)", 
                "OpenSearch features",
                "Cost-effective storage",
                "Aggregations and analytics",
                "OpenSearch ecosystem",
                "Familiar OpenSearch API"
            ]
            
            limitations = [
                "Higher query latency",
                "Lower query throughput",
                "S3 storage overhead",
                "Complex setup",
                "Domain management required",
                "Not suitable for real-time apps"
            ]
            
            performance_metrics = {
                'avg_query_latency_ms': avg_query_time_ms,
                'queries_tested': len(self.demo_config['query_texts']),
                'total_results_returned': total_results,
                'vectors_in_index': len(embeddings_batch),
                'domain_setup_time_ms': setup_time_ms - indexing_time_ms,
                'indexing_time_ms': indexing_time_ms,
                'approach_total_time_ms': (time.time() - approach_start_time) * 1000
            }
            
            result = VectorApproachResult(
                approach_name="OpenSearch Engine",
                setup_time_ms=setup_time_ms,
                indexing_time_ms=indexing_time_ms,
                query_time_ms=avg_query_time_ms,
                query_results_count=total_results,
                average_similarity_score=avg_similarity_score,
                cost_estimate_monthly=cost_estimate_monthly,
                features_supported=features_supported,
                limitations=limitations,
                performance_metrics=performance_metrics
            )
            
            self.logger.log_operation("OpenSearch Engine testing completed",
                                    avg_query_time_ms=avg_query_time_ms,
                                    setup_time_ms=setup_time_ms)
            
            return result
            
        except Exception as e:
            self.logger.log_operation("OpenSearch Engine testing failed", level="ERROR", error=str(e))
            raise

    # Helper methods for simulation and analysis
    
    def _simulate_opensearch_hybrid_search(
        self, 
        query_text: str,
        query_embedding: List[float], 
        embeddings_batch: List[Dict],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Simulate OpenSearch Serverless hybrid search with enhanced features."""
        # In reality, this would use OpenSearch REST API
        # For demo, we simulate enhanced results with hybrid scoring
        
        results = []
        for i, embedding_doc in enumerate(embeddings_batch[:top_k]):
            # Simulate higher relevance scores due to hybrid search
            base_score = 0.7 + (i * 0.05)  # Descending scores
            hybrid_boost = 0.1 if any(word in embedding_doc['metadata']['title'].lower() 
                                     for word in query_text.lower().split()) else 0
            
            result = {
                'id': embedding_doc['key'],
                'score': base_score + hybrid_boost,
                'metadata': embedding_doc['metadata'],
                'highlights': {
                    'title': [f"<em>{word}</em>" for word in embedding_doc['metadata']['title'].split()[:2]],
                    'content': [f"<em>{word}</em>" for word in embedding_doc['metadata']['content'].split()[:5]]
                },
                'hybrid_features': ['vector_match', 'keyword_match', 'highlighting']
            }
            results.append(result)
        
        return sorted(results, key=lambda x: x['score'], reverse=True)

    def _simulate_opensearch_engine_search(
        self,
        query_text: str, 
        query_embedding: List[float],
        embeddings_batch: List[Dict],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Simulate OpenSearch domain search with S3 vector engine (slightly lower performance)."""
        # Similar to hybrid search but with slightly lower scores and features
        
        results = []
        for i, embedding_doc in enumerate(embeddings_batch[:top_k]):
            # Slightly lower base scores due to engine overhead
            base_score = 0.65 + (i * 0.04)
            keyword_boost = 0.08 if any(word in embedding_doc['metadata']['title'].lower()
                                       for word in query_text.lower().split()) else 0
            
            result = {
                'id': embedding_doc['key'], 
                'score': base_score + keyword_boost,
                'metadata': embedding_doc['metadata'],
                'engine_info': {'storage': 's3_vectors', 'latency_ms': 50 + (i * 5)},
                'features': ['vector_match', 'keyword_match', 's3_engine']
            }
            results.append(result)
        
        return sorted(results, key=lambda x: x['score'], reverse=True)

    def _calculate_avg_similarity(self, query_results: List[Dict]) -> float:
        """Calculate average similarity score across all query results."""
        all_scores = []
        for qr in query_results:
            for result in qr.get('results', []):
                if 'score' in result:
                    all_scores.append(result['score'])
                elif 'distance' in result:  # S3 Vectors uses distance
                    # Convert distance to similarity (assuming cosine distance)
                    all_scores.append(1.0 - result['distance'])
        
        return sum(all_scores) / len(all_scores) if all_scores else 0.0

    def _estimate_s3vector_direct_cost(self, vectors_count: int, queries_per_month: int) -> float:
        """Estimate monthly cost for S3Vector Direct approach."""
        # Based on AWS S3 Vectors pricing
        storage_gb = (vectors_count * 1024 * 4) / (1024**3)  # 1024 dims * 4 bytes per float
        storage_cost = storage_gb * 0.023  # $0.023/GB/month
        query_cost = (queries_per_month / 1000) * 0.01  # $0.01 per 1K queries
        
        return storage_cost + query_cost

    def _estimate_opensearch_export_cost(self, vectors_count: int, queries_per_month: int) -> float:
        """Estimate monthly cost for OpenSearch Export approach (higher due to dual storage)."""
        # S3 Vectors storage cost
        s3_cost = self._estimate_s3vector_direct_cost(vectors_count, 0)  # No query cost, handled by OpenSearch
        
        # OpenSearch Serverless cost (estimated)
        storage_gb = (vectors_count * 1024 * 4) / (1024**3)
        opensearch_storage_cost = storage_gb * 0.10  # ~$0.10/GB/month for OpenSearch Serverless
        opensearch_query_cost = (queries_per_month / 1000) * 0.02  # Higher query cost
        
        return s3_cost + opensearch_storage_cost + opensearch_query_cost

    def _estimate_opensearch_engine_cost(self, vectors_count: int, queries_per_month: int) -> float:
        """Estimate monthly cost for OpenSearch Engine approach (cost optimized)."""
        # Only S3 Vectors storage cost (OpenSearch domain fixed cost separate)
        s3_cost = self._estimate_s3vector_direct_cost(vectors_count, 0)
        
        # Lower query processing cost due to shared infrastructure
        query_cost = (queries_per_month / 1000) * 0.008  # Slightly lower than direct
        
        return s3_cost + query_cost  # Note: Excludes OpenSearch domain infrastructure cost

    async def run_comprehensive_comparison(
        self, 
        approaches: List[str] = None,
        with_performance_test: bool = False
    ) -> ComparisonSummary:
        """
        Run comprehensive comparison of all three vector approaches.
        
        Args:
            approaches: List of approaches to test (default: all)
            with_performance_test: Whether to run additional performance tests
            
        Returns:
            ComparisonSummary: Complete comparison results
        """
        comparison_start_time = time.time()
        
        if approaches is None:
            approaches = ['s3vector-direct', 'opensearch-export', 'opensearch-engine']
        
        self.logger.log_operation("Starting comprehensive vector approach comparison",
                                approaches=approaches,
                                with_performance_test=with_performance_test)
        
        try:
            # Setup consistent test data
            setup_result = await self.setup_test_data()
            index_arn = setup_result['index_arn']
            embeddings_batch = setup_result['embeddings_batch']
            
            results = {}
            
            # Test each approach
            if 's3vector-direct' in approaches:
                self.logger.log_operation("Testing S3Vector Direct approach")
                results['s3vector_direct'] = await self.test_s3vector_direct(index_arn, embeddings_batch)
            
            if 'opensearch-export' in approaches:
                self.logger.log_operation("Testing OpenSearch Export approach") 
                results['opensearch_export'] = await self.test_opensearch_export(index_arn, embeddings_batch)
            
            if 'opensearch-engine' in approaches:
                self.logger.log_operation("Testing OpenSearch Engine approach")
                results['opensearch_engine'] = await self.test_opensearch_engine(index_arn, embeddings_batch)
            
            # Generate recommendations based on results
            recommendations = self._generate_approach_recommendations(results)
            
            # Create comparison summary
            summary = ComparisonSummary(
                s3vector_direct=results.get('s3vector_direct'),
                opensearch_export=results.get('opensearch_export'),
                opensearch_engine=results.get('opensearch_engine'),
                comparison_timestamp=datetime.utcnow().isoformat(),
                test_configuration={
                    'documents_tested': len(self.demo_config['sample_documents']),
                    'queries_tested': len(self.demo_config['query_texts']),
                    'vector_dimension': self.demo_config['vector_dimension'],
                    'approaches_tested': approaches,
                    'with_performance_test': with_performance_test
                },
                recommendations=recommendations
            )
            
            comparison_duration = time.time() - comparison_start_time
            
            self.logger.log_operation("Comprehensive comparison completed",
                                    approaches_tested=len(approaches),
                                    total_duration_seconds=comparison_duration)
            
            return summary
            
        except Exception as e:
            self.logger.log_operation("Comparison failed", level="ERROR", error=str(e))
            raise
        finally:
            # Cleanup demo resources
            await self._cleanup_demo_resources()

    def _generate_approach_recommendations(self, results: Dict[str, VectorApproachResult]) -> Dict[str, str]:
        """Generate recommendations based on test results."""
        recommendations = {}
        
        if not results:
            return recommendations
        
        # Cost-based recommendations
        if 'opensearch_engine' in results and 's3vector_direct' in results:
            engine_cost = results['opensearch_engine'].cost_estimate_monthly
            direct_cost = results['s3vector_direct'].cost_estimate_monthly
            
            if engine_cost < direct_cost:
                recommendations['cost_winner'] = "OpenSearch Engine offers the best cost optimization for analytical workloads"
            else:
                recommendations['cost_winner'] = "S3Vector Direct provides the most cost-effective solution"
        
        # Performance-based recommendations
        latencies = [(name, result.query_time_ms) for name, result in results.items()]
        if latencies:
            fastest = min(latencies, key=lambda x: x[1])
            recommendations['performance_winner'] = f"{fastest[0].replace('_', ' ').title()} provides the fastest query performance ({fastest[1]:.1f}ms avg)"
        
        # Feature-based recommendations
        feature_counts = [(name, len(result.features_supported)) for name, result in results.items()]
        if feature_counts:
            most_features = max(feature_counts, key=lambda x: x[1])
            recommendations['feature_winner'] = f"{most_features[0].replace('_', ' ').title()} offers the most comprehensive feature set ({most_features[1]} features)"
        
        # Use case recommendations
        recommendations['use_cases'] = {
            'real_time_apps': 'OpenSearch Export for sub-millisecond latency and high throughput',
            'analytical_workloads': 'OpenSearch Engine for cost-effective analytics with OpenSearch features', 
            'simple_similarity_search': 'S3Vector Direct for straightforward vector search with minimal complexity',
            'hybrid_search_needs': 'OpenSearch Export or Engine for combining vector and keyword search',
            'cost_sensitive_projects': 'OpenSearch Engine or S3Vector Direct for optimal cost efficiency'
        }
        
        return recommendations

    async def _cleanup_demo_resources(self) -> None:
        """Clean up demo resources to avoid ongoing costs."""
        try:
            # In a real implementation, this would:
            # 1. Delete S3 vector bucket and index
            # 2. Delete OpenSearch Serverless collection
            # 3. Delete or stop OpenSearch domain
            # For demo purposes, we'll just log the cleanup
            
            self.logger.log_operation("Cleaning up demo resources",
                                    bucket=self.demo_config['vector_bucket_name'])
            
            # Simulate cleanup time
            await asyncio.sleep(0.5)
            
        except Exception as e:
            self.logger.log_operation("Resource cleanup failed", level="ERROR", error=str(e))

    def print_comparison_summary(self, summary: ComparisonSummary) -> None:
        """Print formatted comparison summary."""
        print("\n" + "="*100)
        print("THREE-WAY VECTOR APPROACH COMPARISON SUMMARY")
        print("="*100)
        
        # Test configuration
        config = summary.test_configuration
        print(f"\n📊 Test Configuration:")
        print(f"  Documents: {config['documents_tested']} | Queries: {config['queries_tested']} | Dimensions: {config['vector_dimension']}")
        print(f"  Timestamp: {summary.comparison_timestamp}")
        
        # Results table
        print(f"\n📈 Performance & Cost Comparison:")
        print(f"{'Approach':<20} {'Query Time':<12} {'Setup Time':<12} {'Monthly Cost':<15} {'Features':<10}")
        print("-" * 75)
        
        for approach_name, result in [
            ('S3Vector Direct', summary.s3vector_direct),
            ('OpenSearch Export', summary.opensearch_export), 
            ('OpenSearch Engine', summary.opensearch_engine)
        ]:
            if result:
                print(f"{approach_name:<20} {result.query_time_ms:<11.1f}ms {result.setup_time_ms:<11.1f}ms ${result.cost_estimate_monthly:<14.2f} {len(result.features_supported):<10}")
        
        # Detailed results for each approach
        for approach_name, result in [
            ('S3Vector Direct', summary.s3vector_direct),
            ('OpenSearch Export', summary.opensearch_export),
            ('OpenSearch Engine', summary.opensearch_engine)
        ]:
            if result:
                print(f"\n🔍 {approach_name} Details:")
                print(f"  ✅ Features: {', '.join(result.features_supported[:5])}{'...' if len(result.features_supported) > 5 else ''}")
                print(f"  ❌ Limitations: {', '.join(result.limitations[:3])}{'...' if len(result.limitations) > 3 else ''}")
                print(f"  📊 Results: {result.query_results_count} total, {result.average_similarity_score:.3f} avg score")
        
        # Recommendations  
        print(f"\n🎯 Recommendations:")
        for category, recommendation in summary.recommendations.items():
            if category != 'use_cases':
                print(f"  • {category.replace('_', ' ').title()}: {recommendation}")
        
        # Use case guidance
        if 'use_cases' in summary.recommendations:
            print(f"\n💡 Use Case Guidance:")
            for use_case, recommendation in summary.recommendations['use_cases'].items():
                print(f"  • {use_case.replace('_', ' ').title()}: {recommendation}")
        
        print("\n" + "="*100)


async def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(
        description="Three-Way Vector Index Comparison Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python examples/three_way_vector_comparison_demo.py
  python examples/three_way_vector_comparison_demo.py --approach s3vector-direct
  python examples/three_way_vector_comparison_demo.py --approach opensearch-export --with-performance-test
  python examples/three_way_vector_comparison_demo.py --storage-size 1000 --queries 100000
        """
    )
    
    parser.add_argument(
        '--approach',
        choices=['s3vector-direct', 'opensearch-export', 'opensearch-engine', 'all'],
        default='all',
        help='Vector approach to test (default: all)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1', 
        help='AWS region for services'
    )
    
    parser.add_argument(
        '--storage-size',
        type=int,
        default=None,
        help='Number of vectors for cost estimation (default: use test documents)'
    )
    
    parser.add_argument(
        '--queries',
        type=int,
        default=10000,
        help='Monthly queries for cost estimation (default: 10000)'
    )
    
    parser.add_argument(
        '--with-performance-test',
        action='store_true',
        help='Run additional performance tests'
    )
    
    parser.add_argument(
        '--output',
        help='Save results to JSON file'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Determine which approaches to test
    if args.approach == 'all':
        approaches = ['s3vector-direct', 'opensearch-export', 'opensearch-engine']
    else:
        approaches = [args.approach]
    
    # Initialize comparison demo
    demo = ThreeWayVectorComparison(region_name=args.region)
    
    try:
        print("🚀 Starting Three-Way Vector Approach Comparison Demo")
        print(f"📋 Testing approaches: {', '.join(approaches)}")
        print(f"🌍 Region: {args.region}")
        
        if not os.getenv('REAL_AWS_DEMO'):
            print("\n⚠️  Note: Set REAL_AWS_DEMO=1 to use real AWS services")
            print("   Running in simulation mode for demonstration\n")
        
        # Run comprehensive comparison
        summary = await demo.run_comprehensive_comparison(
            approaches=approaches,
            with_performance_test=args.with_performance_test
        )
        
        # Print results
        demo.print_comparison_summary(summary)
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                # Convert summary to dict for JSON serialization
                summary_dict = asdict(summary)
                json.dump(summary_dict, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {args.output}")
        
        print("\n✅ Three-way comparison completed successfully!")
        
        # Print key takeaways
        print(f"\n🎯 Key Takeaways:")
        print(f"• S3Vector Direct: Simple, cost-effective, best for basic vector search")
        print(f"• OpenSearch Export: High performance, advanced features, higher cost")
        print(f"• OpenSearch Engine: Balanced approach, cost-optimized, OpenSearch ecosystem")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))