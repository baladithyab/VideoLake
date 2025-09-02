# OpenSearch Integration Guide

## Table of Contents
1. [Integration Overview](#integration-overview)
2. [Export Pattern Implementation](#export-pattern-implementation)
3. [Engine Pattern Implementation](#engine-pattern-implementation)
4. [Hybrid Search Capabilities](#hybrid-search-capabilities)
5. [Cost Monitoring and Analysis](#cost-monitoring-and-analysis)
6. [Configuration and Setup](#configuration-and-setup)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Integration Overview

S3Vector provides two distinct integration patterns with Amazon OpenSearch Service, each optimized for different use cases and performance requirements.

### Integration Patterns

#### 1. Export Pattern
- **Use Case**: High-performance, low-latency search requirements
- **Architecture**: Point-in-time data export from S3 Vectors to OpenSearch Serverless
- **Benefits**: Fast query performance, full OpenSearch features
- **Trade-offs**: Higher storage costs (dual storage), periodic sync required

#### 2. Engine Pattern  
- **Use Case**: Cost-optimized analytical workloads
- **Architecture**: S3 Vectors as storage engine for OpenSearch domains
- **Benefits**: Single storage location, significant cost savings
- **Trade-offs**: Higher query latency, limited to supported OpenSearch versions

### Architecture Comparison

```
Export Pattern:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   S3 Vectors    │───▶│ OSI Pipeline    │───▶│ OpenSearch      │
│   (Source)      │    │ (Export Job)    │    │ Serverless      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       │                                              │
       └──────────────────────────────────────────────┘
                    Dual Storage

Engine Pattern:
┌─────────────────┐    ┌─────────────────┐
│   S3 Vectors    │◄──▶│ OpenSearch      │
│   (Engine)      │    │ Domain          │
└─────────────────┘    └─────────────────┘
           Single Storage Location
```

## Export Pattern Implementation

### 1. Basic Export Setup

```python
from src.services.opensearch_integration import OpenSearchIntegrationManager, IntegrationPattern

# Initialize integration manager
integration_manager = OpenSearchIntegrationManager(
    region_name="us-east-1",
    opensearch_endpoint="your-domain.us-east-1.es.amazonaws.com"
)

# Export S3 vectors to OpenSearch Serverless
export_id = integration_manager.export_to_opensearch_serverless(
    vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/my-vectors",
    collection_name="my-vector-collection",
    target_index_name="exported-vectors",
    dead_letter_queue_bucket="my-dlq-bucket"  # Optional error handling
)

print(f"Export started with ID: {export_id}")
```

### 2. Monitoring Export Progress

```python
import time

def monitor_export_progress(integration_manager, export_id):
    """Monitor export operation until completion"""
    max_wait_minutes = 60
    check_interval = 30
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_minutes * 60:
        status = integration_manager.get_export_status(export_id)
        
        print(f"Export Status: {status.status}")
        print(f"Records Processed: {status.records_processed}")
        print(f"Cost Estimate: ${status.cost_estimate:.4f}")
        
        if status.status == "COMPLETED":
            print("✅ Export completed successfully!")
            return status
        elif status.status == "FAILED":
            print(f"❌ Export failed: {status.error_message}")
            return status
        
        print(f"⏳ Waiting {check_interval}s before next check...")
        time.sleep(check_interval)
    
    print("⚠️ Export monitoring timed out")
    return None

# Monitor the export
final_status = monitor_export_progress(integration_manager, export_id)
```

### 3. Advanced Export Configuration

```python
# Export with custom configuration
export_id = integration_manager.export_to_opensearch_serverless(
    vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/my-vectors",
    collection_name="advanced-vector-collection",
    target_index_name="processed-vectors",
    
    # Custom IAM role (optional - auto-created if not provided)
    iam_role_arn="arn:aws:iam::123456789012:role/CustomIngestionRole",
    
    # Dead letter queue for failed records
    dead_letter_queue_bucket="vector-processing-errors",
    
    # Additional pipeline configuration
    batch_size=1000,
    max_workers=8,
    estimated_duration=45,  # minutes
    
    # Data transformation options
    field_mappings={
        "vector_field": "embedding",
        "metadata.title": "title",
        "metadata.category": "category"
    },
    
    # Filtering options
    metadata_filters={
        "content_type": ["text", "video"],
        "status": ["published"]
    }
)
```

### 4. Cleanup Export Resources

```python
# Clean up export resources when no longer needed
cleanup_result = integration_manager.cleanup_export_resources(
    export_id=export_id,
    cleanup_collection=False,  # Keep collection for other exports
    cleanup_iam_role=True      # Remove auto-created IAM role
)

print("Cleanup Results:")
print(f"Pipeline deleted: {cleanup_result['pipeline_deleted']}")
print(f"IAM role deleted: {cleanup_result['iam_role_deleted']}")
if cleanup_result['errors']:
    print(f"Errors: {cleanup_result['errors']}")
```

## Engine Pattern Implementation

### 1. Configure OpenSearch Domain

```python
# Configure existing OpenSearch domain to use S3 Vectors engine
config_result = integration_manager.configure_s3_vectors_engine(
    domain_name="my-opensearch-domain",
    enable_s3_vectors=True,
    kms_key_id="arn:aws:kms:us-east-1:123456789012:key/12345678-1234-1234-1234-123456789012"  # Optional
)

print(f"S3 Vectors enabled: {config_result['s3_vectors_enabled']}")
print(f"Domain processing: {config_result['domain_status']}")
print(f"Capabilities: {config_result['engine_capabilities']}")
```

### 2. Create S3 Vector-Backed Index

```python
# Create OpenSearch index that uses S3 Vectors for vector fields
index_result = integration_manager.create_s3_vector_index(
    opensearch_endpoint="my-domain.us-east-1.es.amazonaws.com",
    index_name="hybrid-content-index",
    vector_field_name="content_embedding",
    vector_dimension=1024,
    space_type="cosine",  # cosine, l2, or inner_product
    
    # Additional fields for hybrid search
    additional_fields={
        "title": {
            "type": "text",
            "analyzer": "english"
        },
        "content": {
            "type": "text", 
            "analyzer": "english"
        },
        "category": {
            "type": "keyword"
        },
        "publish_date": {
            "type": "date"
        },
        "metadata": {
            "type": "object",
            "properties": {
                "tags": {"type": "keyword"},
                "author": {"type": "keyword"},
                "rating": {"type": "float"}
            }
        }
    }
)

print(f"Index created: {index_result['index_name']}")
print(f"Vector field: {index_result['vector_field']}")
print(f"Engine: {index_result['engine']}")
```

### 3. Index Documents with Vector Data

```python
import requests
import json

def index_documents_with_vectors(opensearch_endpoint, index_name, documents):
    """Index documents containing both text and vector data"""
    
    for doc in documents:
        doc_id = doc['id']
        
        # Document structure for S3 vector engine
        document = {
            "title": doc['title'],
            "content": doc['content'],
            "category": doc['category'],
            "publish_date": doc['publish_date'],
            "content_embedding": doc['embedding'],  # 1024-dimensional vector
            "metadata": {
                "tags": doc.get('tags', []),
                "author": doc.get('author'),
                "rating": doc.get('rating', 0.0)
            }
        }
        
        # Index document via REST API
        response = requests.put(
            f"https://{opensearch_endpoint}/{index_name}/_doc/{doc_id}",
            json=document,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code not in [200, 201]:
            print(f"Failed to index document {doc_id}: {response.text}")
        else:
            print(f"✅ Indexed document: {doc_id}")

# Sample documents
sample_documents = [
    {
        'id': 'doc-1',
        'title': 'Machine Learning Fundamentals',
        'content': 'Introduction to supervised and unsupervised learning algorithms...',
        'category': 'education',
        'publish_date': '2024-01-15',
        'embedding': [0.1, -0.2, 0.3] * 341 + [0.1],  # 1024 dimensions
        'tags': ['machine-learning', 'ai', 'education'],
        'author': 'Dr. Smith',
        'rating': 4.5
    },
    {
        'id': 'doc-2', 
        'title': 'Deep Learning with Neural Networks',
        'content': 'Comprehensive guide to building and training neural networks...',
        'category': 'education',
        'publish_date': '2024-02-01',
        'embedding': [0.2, -0.1, 0.4] * 341 + [0.2],  # 1024 dimensions
        'tags': ['deep-learning', 'neural-networks', 'tensorflow'],
        'author': 'Prof. Johnson',
        'rating': 4.8
    }
]

index_documents_with_vectors(
    opensearch_endpoint="my-domain.us-east-1.es.amazonaws.com",
    index_name="hybrid-content-index",
    documents=sample_documents
)
```

## Hybrid Search Capabilities

### 1. Basic Hybrid Search

```python
# Perform hybrid search combining vector similarity and text search
search_results = integration_manager.perform_hybrid_search(
    opensearch_endpoint="my-domain.us-east-1.es.amazonaws.com",
    index_name="hybrid-content-index",
    
    # Text query for keyword search
    query_text="machine learning algorithms",
    
    # Vector query for semantic similarity
    query_vector=[0.15, -0.15, 0.35] * 341 + [0.15],  # Query vector
    
    # Search configuration
    vector_field="content_embedding",
    text_fields=["title", "content"],
    k=10,
    
    # Score combination strategy
    score_combination="weighted",  # weighted, max, harmonic_mean
    vector_weight=0.7,            # 70% weight for vector similarity
    text_weight=0.3               # 30% weight for text relevance
)

print(f"Found {len(search_results)} hybrid search results:")

for i, result in enumerate(search_results[:5], 1):
    print(f"\n{i}. Document ID: {result.document_id}")
    print(f"   Title: {result.content.get('title', 'Unknown')}")
    print(f"   Vector Score: {result.vector_score:.3f}")
    print(f"   Keyword Score: {result.keyword_score:.3f}")
    print(f"   Combined Score: {result.combined_score:.3f}")
    print(f"   Category: {result.content.get('category', 'Unknown')}")
    
    if result.highlights:
        print(f"   Highlights: {result.highlights}")
```

### 2. Advanced Hybrid Search with Filters

```python
# Advanced hybrid search with metadata filters and custom scoring
search_results = integration_manager.perform_hybrid_search(
    opensearch_endpoint="my-domain.us-east-1.es.amazonaws.com",
    index_name="hybrid-content-index",
    
    query_text="neural networks deep learning",
    query_vector=query_embedding,  # Pre-computed query vector
    
    # Search configuration
    vector_field="content_embedding",
    text_fields=["title", "content", "metadata.tags"],
    k=20,
    
    # Metadata filters
    filters={
        "bool": {
            "must": [
                {"range": {"metadata.rating": {"gte": 4.0}}},
                {"terms": {"category": ["education", "research"]}},
                {"range": {"publish_date": {"gte": "2023-01-01"}}}
            ]
        }
    },
    
    # Custom scoring strategy
    score_combination="harmonic_mean",
    vector_weight=0.6,
    text_weight=0.4,
    
    # Additional search parameters
    min_score=0.1,                # Minimum relevance threshold
    explain_scores=True,          # Include score explanations
    include_vector_scores=True    # Include individual vector scores
)

# Process results with detailed analysis
for result in search_results[:3]:
    print(f"\n📄 {result.content['title']}")
    print(f"   📊 Scores - Vector: {result.vector_score:.3f}, Text: {result.keyword_score:.3f}, Combined: {result.combined_score:.3f}")
    print(f"   🏷️  Category: {result.content['category']}")
    print(f"   ⭐ Rating: {result.metadata.get('rating', 'N/A')}")
    print(f"   📅 Published: {result.content.get('publish_date', 'Unknown')}")
    
    # Show highlighted text snippets
    if result.highlights:
        for field, snippets in result.highlights.items():
            print(f"   🔍 {field.title()}: {' ... '.join(snippets[:2])}")
```

### 3. Multi-Modal Search Scenarios

```python
class MultiModalSearchEngine:
    """Enhanced search engine for complex multi-modal queries"""
    
    def __init__(self, integration_manager, opensearch_endpoint):
        self.integration_manager = integration_manager
        self.opensearch_endpoint = opensearch_endpoint
    
    def search_by_content_type(self, query_text, content_types, index_name="hybrid-content-index"):
        """Search within specific content types"""
        return self.integration_manager.perform_hybrid_search(
            opensearch_endpoint=self.opensearch_endpoint,
            index_name=index_name,
            query_text=query_text,
            text_fields=["title", "content"],
            filters={
                "terms": {"category": content_types}
            },
            k=15,
            score_combination="weighted",
            vector_weight=0.5,
            text_weight=0.5
        )
    
    def temporal_search(self, query_text, date_range, index_name="hybrid-content-index"):
        """Search within specific time periods"""
        return self.integration_manager.perform_hybrid_search(
            opensearch_endpoint=self.opensearch_endpoint,
            index_name=index_name,
            query_text=query_text,
            filters={
                "range": {
                    "publish_date": {
                        "gte": date_range["start"],
                        "lte": date_range["end"]
                    }
                }
            },
            k=10
        )
    
    def similarity_threshold_search(self, query_vector, threshold=0.8, index_name="hybrid-content-index"):
        """Find documents above similarity threshold"""
        results = self.integration_manager.perform_hybrid_search(
            opensearch_endpoint=self.opensearch_endpoint,
            index_name=index_name,
            query_vector=query_vector,
            vector_field="content_embedding",
            k=100,  # Get many results to filter
            score_combination="weighted",
            vector_weight=1.0,
            text_weight=0.0  # Pure vector search
        )
        
        # Filter by threshold
        filtered_results = [
            result for result in results 
            if result.vector_score >= threshold
        ]
        
        return filtered_results[:20]  # Return top 20 above threshold

# Usage examples
search_engine = MultiModalSearchEngine(integration_manager, "my-domain.us-east-1.es.amazonaws.com")

# Search within educational content
education_results = search_engine.search_by_content_type(
    query_text="machine learning optimization techniques",
    content_types=["education", "research", "tutorial"]
)

# Search recent content
recent_results = search_engine.temporal_search(
    query_text="artificial intelligence trends",
    date_range={"start": "2024-01-01", "end": "2024-12-31"}
)

# Find highly similar content
similar_results = search_engine.similarity_threshold_search(
    query_vector=reference_embedding,
    threshold=0.85
)
```

## Cost Monitoring and Analysis

### 1. Pattern Cost Analysis

```python
# Analyze costs for export pattern
export_cost_analysis = integration_manager.monitor_integration_costs(
    pattern=IntegrationPattern.EXPORT,
    time_period_days=30,
    vector_storage_gb=100.0,      # 100GB of vector data
    query_count_monthly=50000,    # 50K queries per month
    collection_compute_units=2,   # OpenSearch Serverless OCUs
    pipeline_capacity_units=4     # OSI pipeline capacity
)

print("Export Pattern Cost Analysis:")
print(f"📊 Monthly Storage Cost: ${export_cost_analysis.storage_cost_monthly:.2f}")
print(f"🔍 Query Cost per 1K: ${export_cost_analysis.query_cost_per_1k:.4f}")
print(f"📥 Ingestion Cost per GB: ${export_cost_analysis.ingestion_cost_per_gb:.4f}")
print(f"💰 Estimated Monthly Total: ${export_cost_analysis.estimated_monthly_total:.2f}")

# Analyze costs for engine pattern
engine_cost_analysis = integration_manager.monitor_integration_costs(
    pattern=IntegrationPattern.ENGINE,
    time_period_days=30,
    vector_storage_gb=100.0,
    query_count_monthly=50000,
    domain_instance_hours=24*30,  # m6g.large running 24/7
    domain_instance_type="m6g.large"
)

print("\nEngine Pattern Cost Analysis:")
print(f"📊 Monthly Storage Cost: ${engine_cost_analysis.storage_cost_monthly:.2f}")
print(f"🔍 Query Cost per 1K: ${engine_cost_analysis.query_cost_per_1k:.4f}")
print(f"💰 Estimated Monthly Total: ${engine_cost_analysis.estimated_monthly_total:.2f}")

# Compare patterns
if export_cost_analysis.cost_comparison:
    comparison = export_cost_analysis.cost_comparison
    savings_pct = comparison['percentage_savings_engine']
    
    print(f"\n📈 Cost Comparison:")
    print(f"Export Pattern: ${comparison['export_pattern_monthly']:.2f}/month")
    print(f"Engine Pattern: ${comparison['engine_pattern_monthly']:.2f}/month")
    print(f"💵 Savings with Engine: {savings_pct:.1f}% (${comparison['cost_difference']:.2f})")

# Show optimization recommendations
print(f"\n💡 Optimization Recommendations:")
for i, rec in enumerate(export_cost_analysis.optimization_recommendations, 1):
    print(f"{i}. {rec}")
```

### 2. Cost Reporting and Projections

```python
from datetime import datetime, timedelta

# Generate comprehensive cost report
start_date = datetime.utcnow() - timedelta(days=30)
end_date = datetime.utcnow()

cost_report = integration_manager.get_cost_report(
    start_date=start_date,
    end_date=end_date,
    include_projections=True
)

print("📊 OpenSearch Integration Cost Report")
print("=" * 50)

# Current period costs
breakdown = cost_report['cost_breakdown']
print(f"📤 Export Operations: ${breakdown['export_operations']:.4f}")
print(f"🔍 Query Operations: ${breakdown['query_operations']:.4f}")
print(f"💾 Storage Costs: ${breakdown['storage_costs']:.4f}")
print(f"💰 Total Costs: ${breakdown['total_costs']:.4f}")

# Activity summary
activity = cost_report['activity_summary']
print(f"\n📈 Activity Summary:")
print(f"   Exports: {activity['export_count']}")
print(f"   Queries: {activity['query_count']}")
print(f"   Active Integrations: {activity['active_integrations']}")

# Cost projections
if 'projections' in cost_report:
    projections = cost_report['projections']
    print(f"\n🔮 Cost Projections:")
    print(f"   Daily Average: ${projections['daily_average']:.4f}")
    print(f"   Weekly: ${projections['weekly_projection']:.2f}")
    print(f"   Monthly: ${projections['monthly_projection']:.2f}")
    print(f"   Quarterly: ${projections['quarterly_projection']:.2f}")
    print(f"   Annual: ${projections['annual_projection']:.2f}")
```

### 3. Cost Optimization Strategies

```python
class CostOptimizer:
    """Cost optimization strategies for OpenSearch integration"""
    
    def __init__(self, integration_manager):
        self.integration_manager = integration_manager
    
    def analyze_query_patterns(self, time_period_days=7):
        """Analyze query patterns to identify optimization opportunities"""
        # Get query history from cost tracker
        queries = self.integration_manager._cost_tracker['queries']
        
        if not queries:
            return {"message": "No query data available for analysis"}
        
        # Analyze query frequency and types
        query_analysis = {
            'total_queries': len(queries),
            'avg_queries_per_day': len(queries) / time_period_days,
            'query_types': {},
            'peak_hours': {},
            'cost_per_query_avg': sum(q.get('cost', 0) for q in queries) / len(queries)
        }
        
        # Group by query type
        for query in queries:
            qtype = query.get('query_type', 'unknown')
            query_analysis['query_types'][qtype] = query_analysis['query_types'].get(qtype, 0) + 1
        
        # Recommendations based on patterns
        recommendations = []
        
        if query_analysis['avg_queries_per_day'] < 100:
            recommendations.append("Consider engine pattern for low-query workloads")
        elif query_analysis['avg_queries_per_day'] > 10000:
            recommendations.append("Export pattern recommended for high-query workloads")
        
        if query_analysis['query_types'].get('hybrid', 0) > query_analysis['query_types'].get('vector', 0):
            recommendations.append("High hybrid query usage - ensure text fields are properly indexed")
        
        query_analysis['recommendations'] = recommendations
        return query_analysis
    
    def recommend_pattern(self, storage_gb, monthly_queries, performance_requirements="standard"):
        """Recommend optimal integration pattern based on usage"""
        export_cost = self._estimate_export_costs(storage_gb, monthly_queries)
        engine_cost = self._estimate_engine_costs(storage_gb, monthly_queries)
        
        # Decision factors
        factors = {
            'cost_difference': export_cost - engine_cost,
            'export_monthly': export_cost,
            'engine_monthly': engine_cost,
            'query_frequency': monthly_queries / 30,  # per day
            'storage_size': storage_gb
        }
        
        # Recommendation logic
        if performance_requirements == "high" and monthly_queries > 50000:
            recommendation = "export"
            reason = "High performance and query volume favor export pattern"
        elif factors['cost_difference'] > 50:  # Export costs $50+ more
            recommendation = "engine"
            reason = f"Engine pattern saves ${factors['cost_difference']:.2f}/month"
        elif factors['query_frequency'] > 10000:  # >10K queries/day
            recommendation = "export"
            reason = "High query frequency benefits from export pattern performance"
        else:
            recommendation = "engine"
            reason = "Engine pattern provides optimal cost-performance balance"
        
        return {
            'recommended_pattern': recommendation,
            'reason': reason,
            'cost_factors': factors,
            'estimated_savings': abs(factors['cost_difference']),
            'break_even_queries': self._calculate_break_even_point(storage_gb)
        }
    
    def _estimate_export_costs(self, storage_gb, monthly_queries):
        """Estimate export pattern costs"""
        # Simplified cost calculation
        storage_cost = storage_gb * 0.13  # S3 + OpenSearch Serverless
        query_cost = (monthly_queries / 1000) * 0.01
        return storage_cost + query_cost
    
    def _estimate_engine_costs(self, storage_gb, monthly_queries):
        """Estimate engine pattern costs"""
        storage_cost = storage_gb * 0.023  # S3 only
        query_cost = (monthly_queries / 1000) * 0.008  # Slightly lower
        compute_cost = 50  # Base domain cost
        return storage_cost + query_cost + compute_cost
    
    def _calculate_break_even_point(self, storage_gb):
        """Calculate query volume break-even point between patterns"""
        # Simplified calculation
        base_cost_difference = (storage_gb * 0.107) - 50  # Storage difference minus compute
        query_cost_difference = 0.002  # Per 1K queries
        
        if query_cost_difference > 0:
            break_even = abs(base_cost_difference) / query_cost_difference * 1000
            return int(break_even)
        return 0

# Usage example
cost_optimizer = CostOptimizer(integration_manager)

# Analyze current query patterns
query_analysis = cost_optimizer.analyze_query_patterns(time_period_days=7)
print("Query Pattern Analysis:")
print(f"Total Queries: {query_analysis['total_queries']}")
print(f"Daily Average: {query_analysis['avg_queries_per_day']:.1f}")
print(f"Cost per Query: ${query_analysis['cost_per_query_avg']:.6f}")

# Get pattern recommendation
recommendation = cost_optimizer.recommend_pattern(
    storage_gb=150,
    monthly_queries=75000,
    performance_requirements="high"
)

print(f"\n🎯 Pattern Recommendation: {recommendation['recommended_pattern'].upper()}")
print(f"💡 Reason: {recommendation['reason']}")
print(f"💰 Estimated Savings: ${recommendation['estimated_savings']:.2f}/month")
print(f"📊 Break-even Point: {recommendation['break_even_queries']:,} queries/month")
```

## Configuration and Setup

### 1. Environment Configuration

```bash
# OpenSearch Integration Configuration
OPENSEARCH_ENDPOINT=your-domain.us-east-1.es.amazonaws.com
OPENSEARCH_DOMAIN_NAME=your-opensearch-domain

# Export Pattern Settings
OPENSEARCH_SERVERLESS_COLLECTION=your-collection-name
OPENSEARCH_INGESTION_ROLE=your-ingestion-role
DEAD_LETTER_QUEUE_BUCKET=your-dlq-bucket

# Engine Pattern Settings
ENABLE_S3_VECTORS_ENGINE=true
S3_VECTORS_KMS_KEY=arn:aws:kms:us-east-1:123456789012:key/your-key-id

# Cost Monitoring
ENABLE_COST_TRACKING=true
MAX_MONTHLY_OPENSEARCH_COST=500.00
COST_ALERT_THRESHOLD=400.00

# Performance Settings
HYBRID_SEARCH_TIMEOUT=30
VECTOR_SEARCH_BATCH_SIZE=50
TEXT_SEARCH_BATCH_SIZE=100
```

### 2. IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "es:ESHttpGet",
                "es:ESHttpPost",
                "es:ESHttpPut",
                "es:ESHttpDelete",
                "es:ESHttpHead",
                "es:UpdateDomainConfig",
                "es:DescribeDomain"
            ],
            "Resource": "arn:aws:es:*:*:domain/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "aoss:*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "osis:CreatePipeline",
                "osis:DeletePipeline",
                "osis:GetPipeline",
                "osis:ListPipelines",
                "osis:UpdatePipeline"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateRole",
                "iam:PutRolePolicy",
                "iam:DeleteRole",
                "iam:DeleteRolePolicy",
                "iam:ListRolePolicies"
            ],
            "Resource": "arn:aws:iam::*:role/s3vectors-*"
        }
    ]
}
```

### 3. OpenSearch Domain Requirements

#### For Engine Pattern

```yaml
# Minimum OpenSearch domain configuration for S3 vectors engine
OpenSearchDomain:
  Type: AWS::OpenSearch::Domain
  Properties:
    DomainName: s3vector-engine-domain
    EngineVersion: OpenSearch_2.19  # Minimum version for S3 vectors
    ClusterConfig:
      InstanceType: m6g.large.search  # Optimized instances recommended
      InstanceCount: 2
      DedicatedMasterEnabled: false
    EBSOptions:
      EBSEnabled: true
      VolumeType: gp3
      VolumeSize: 20
    VPCOptions:  # Optional but recommended
      SecurityGroupIds: [sg-12345678]
      SubnetIds: [subnet-12345678, subnet-87654321]
    AccessPolicies:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            AWS: 'arn:aws:iam::123456789012:root'
          Action: 'es:*'
          Resource: 'arn:aws:es:us-east-1:123456789012:domain/s3vector-engine-domain/*'
```

## Best Practices

### 1. Pattern Selection Guidelines

```python
def select_optimal_pattern(requirements):
    """Guidelines for selecting the optimal integration pattern"""
    
    factors = {
        'query_volume_monthly': requirements.get('query_volume', 0),
        'query_latency_requirement': requirements.get('latency_ms', 1000),
        'storage_size_gb': requirements.get('storage_gb', 0),
        'budget_monthly': requirements.get('budget', 1000),
        'data_freshness_requirement': requirements.get('freshness_hours', 24),
        'performance_priority': requirements.get('performance_priority', 'cost')
    }
    
    # Decision matrix
    recommendations = []
    
    # High-performance scenarios
    if (factors['query_latency_requirement'] < 100 and 
        factors['query_volume_monthly'] > 100000):
        recommendations.append({
            'pattern': 'export',
            'score': 9,
            'reason': 'High query volume with low latency requirements'
        })
    
    # Cost-optimized scenarios
    if (factors['storage_size_gb'] > 500 and 
        factors['query_volume_monthly'] < 50000):
        recommendations.append({
            'pattern': 'engine',
            'score': 8,
            'reason': 'Large storage with moderate query volume favors engine pattern'
        })
    
    # Real-time scenarios
    if factors['data_freshness_requirement'] < 1:  # Less than 1 hour
        recommendations.append({
            'pattern': 'export',
            'score': 7,
            'reason': 'Real-time data requirements benefit from export pattern'
        })
    
    # Budget constraints
    if factors['budget_monthly'] < 200:
        recommendations.append({
            'pattern': 'engine',
            'score': 8,
            'reason': 'Budget constraints favor cost-effective engine pattern'
        })
    
    # Select best recommendation
    best_recommendation = max(recommendations, key=lambda x: x['score'])
    
    return {
        'recommended_pattern': best_recommendation['pattern'],
        'confidence_score': best_recommendation['score'],
        'reasoning': best_recommendation['reason'],
        'all_factors': factors,
        'alternative_recommendations': [r for r in recommendations if r != best_recommendation]
    }

# Example usage
requirements = {
    'query_volume': 25000,      # 25K queries/month
    'latency_ms': 200,          # 200ms acceptable latency
    'storage_gb': 300,          # 300GB vector data
    'budget': 400,              # $400/month budget
    'freshness_hours': 6,       # 6-hour data freshness requirement
    'performance_priority': 'balanced'
}

selection = select_optimal_pattern(requirements)
print(f"Recommended Pattern: {selection['recommended_pattern']}")
print(f"Confidence: {selection['confidence_score']}/10")
print(f"Reasoning: {selection['reasoning']}")
```

### 2. Performance Optimization

#### Export Pattern Optimization

```python
# Export pattern performance optimization
export_optimization = {
    'opensearch_serverless': {
        'collection_type': 'VECTORSEARCH',  # Use vector-optimized collection
        'compute_units': 2,                 # Start with 2 OCUs, scale as needed
        'standby_replicas': True            # Enable for high availability
    },
    
    'ingestion_pipeline': {
        'min_units': 1,                     # Minimum pipeline capacity
        'max_units': 16,                    # Allow scaling up to 16 units
        'batch_size': 1000,                 # Optimize batch size for throughput
        'buffer_interval': '30s',           # Buffer for efficient batching
        'dead_letter_queue': True           # Enable error handling
    },
    
    'data_optimization': {
        'field_selection': [                # Only export necessary fields
            'vector_field',
            'title',
            'content',
            'metadata.category'
        ],
        'compression': 'gzip',              # Compress data in transit
        'vector_normalization': True       # Normalize vectors for better search
    }
}
```

#### Engine Pattern Optimization

```python
# Engine pattern performance optimization
engine_optimization = {
    'opensearch_domain': {
        'instance_type': 'm6g.large.search',  # Optimized instances
        'instance_count': 2,                  # Multi-node for availability
        'ebs_volume_type': 'gp3',            # High-performance storage
        'ebs_iops': 3000,                    # Provision IOPS for consistency
        'dedicated_master': False,           # Not needed for small domains
        'zone_awareness': True               # Multi-AZ deployment
    },
    
    's3_vectors_config': {
        'index_optimization': {
            'refresh_interval': '30s',        # Balance freshness vs performance
            'number_of_shards': 2,           # Optimize for data size
            'number_of_replicas': 1          # One replica for availability
        },
        
        'vector_optimization': {
            'space_type': 'cosine',          # Most common for text embeddings
            'ef_search': 512,                # Search accuracy parameter
            'ef_construction': 512,          # Index build parameter
            'm': 16                          # Graph connectivity parameter
        }
    },
    
    'query_optimization': {
        'result_caching': True,              # Cache frequent queries
        'batch_requests': True,              # Batch multiple queries
        'request_compression': True,         # Compress large requests
        'connection_pooling': True           # Reuse connections
    }
}
```

### 3. Monitoring and Alerting

```python
def setup_monitoring(integration_manager):
    """Setup comprehensive monitoring for OpenSearch integration"""
    
    monitoring_config = {
        'cost_monitoring': {
            'daily_cost_check': True,
            'cost_alert_threshold': 0.8,      # Alert at 80% of budget
            'cost_projection_enabled': True,
            'budget_period': 'monthly'
        },
        
        'performance_monitoring': {
            'query_latency_p95_ms': 500,      # Alert if P95 > 500ms
            'error_rate_threshold': 0.05,    # Alert if error rate > 5%
            'throughput_monitoring': True,
            'resource_utilization_check': True
        },
        
        'operational_monitoring': {
            'export_job_monitoring': True,
            'pipeline_health_check': True,
            'domain_health_check': True,
            'index_health_monitoring': True
        }
    }
    
    # Setup cost alerts
    def check_daily_costs():
        cost_report = integration_manager.get_cost_report(
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        daily_cost = cost_report['cost_breakdown']['total_costs']
        monthly_projection = daily_cost * 30
        
        budget = monitoring_config['cost_monitoring']['budget_period']
        threshold = monitoring_config['cost_monitoring']['cost_alert_threshold']
        
        if monthly_projection > (budget * threshold):
            send_cost_alert(daily_cost, monthly_projection, budget)
    
    # Setup performance alerts
    def check_query_performance():
        # Monitor query latency and error rates
        queries = integration_manager._cost_tracker['queries']
        recent_queries = [q for q in queries 
                         if datetime.fromisoformat(q['timestamp']) > 
                            datetime.utcnow() - timedelta(hours=1)]
        
        if recent_queries:
            avg_latency = sum(q.get('processing_time_ms', 0) for q in recent_queries) / len(recent_queries)
            error_count = sum(1 for q in recent_queries if q.get('error'))
            error_rate = error_count / len(recent_queries)
            
            if (avg_latency > monitoring_config['performance_monitoring']['query_latency_p95_ms'] or
                error_rate > monitoring_config['performance_monitoring']['error_rate_threshold']):
                send_performance_alert(avg_latency, error_rate)
    
    return monitoring_config
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Export Pattern Issues

**Issue: Export pipeline fails to start**
```python
def troubleshoot_export_pipeline(integration_manager, export_id):
    """Troubleshoot export pipeline issues"""
    
    try:
        status = integration_manager.get_export_status(export_id)
        
        if status.status == "FAILED":
            print(f"❌ Export failed: {status.error_message}")
            
            # Common failure scenarios
            if "AccessDenied" in status.error_message:
                print("🔑 IAM Permission Issue:")
                print("  - Check IAM role has s3vectors:* permissions")
                print("  - Verify OpenSearch Serverless collection access")
                print("  - Ensure cross-service permissions are configured")
            
            elif "InvalidIndex" in status.error_message:
                print("📍 Index Configuration Issue:")
                print("  - Verify source S3 Vector index exists")
                print("  - Check index ARN format")
                print("  - Ensure index has data to export")
            
            elif "ResourceNotFound" in status.error_message:
                print("🏗️ Resource Missing:")
                print("  - Verify OpenSearch Serverless collection exists")
                print("  - Check collection name spelling")
                print("  - Ensure collection is in ACTIVE state")
        
        return status
        
    except Exception as e:
        print(f"Error checking export status: {e}")
        return None
```

**Issue: High export costs**
```python
def optimize_export_costs(integration_manager, export_id):
    """Optimize export operation costs"""
    
    optimizations = {
        'data_filtering': [
            "Apply metadata filters to export only necessary data",
            "Use date ranges to limit export scope",
            "Select specific vector fields rather than all data"
        ],
        
        'pipeline_tuning': [
            "Adjust pipeline capacity based on data volume",
            "Use compression during data transfer",
            "Schedule exports during off-peak hours"
        ],
        
        'collection_optimization': [
            "Right-size OpenSearch Serverless compute units",
            "Enable standby replicas only if needed",
            "Monitor and adjust based on query patterns"
        ]
    }
    
    return optimizations
```

#### 2. Engine Pattern Issues

**Issue: S3 vectors engine not available**
```python
def troubleshoot_engine_setup(integration_manager, domain_name):
    """Troubleshoot S3 vectors engine setup issues"""
    
    try:
        # Check domain configuration
        domain_response = integration_manager.opensearch_client.describe_domain(
            DomainName=domain_name
        )
        domain_config = domain_response['DomainStatus']
        
        # Validation checks
        issues = []
        
        # Check OpenSearch version
        engine_version = domain_config.get('EngineVersion', '')
        if not engine_version.startswith('OpenSearch_2.') or engine_version < 'OpenSearch_2.19':
            issues.append({
                'issue': 'Incompatible OpenSearch version',
                'current': engine_version,
                'required': 'OpenSearch_2.19 or later',
                'solution': 'Upgrade domain to supported version'
            })
        
        # Check instance type
        instance_type = domain_config.get('ClusterConfig', {}).get('InstanceType', '')
        if 'optimized' not in instance_type.lower():
            issues.append({
                'issue': 'Suboptimal instance type for S3 vectors',
                'current': instance_type,
                'recommended': 'm6g.large.search or similar optimized instance',
                'solution': 'Modify domain to use optimized instances'
            })
        
        # Check domain status
        if domain_config.get('Processing', True):
            issues.append({
                'issue': 'Domain is currently processing changes',
                'solution': 'Wait for domain to finish processing before enabling S3 vectors'
            })
        
        if not issues:
            print("✅ Domain configuration is compatible with S3 vectors")
        else:
            print("⚠️ Issues found with S3 vectors engine setup:")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue['issue']}")
                print(f"   Current: {issue.get('current', 'N/A')}")
                print(f"   Solution: {issue['solution']}")
        
        return issues
        
    except Exception as e:
        print(f"Error checking domain configuration: {e}")
        return [{'issue': f'Failed to check domain: {e}', 'solution': 'Verify domain name and permissions'}]
```

#### 3. Hybrid Search Issues

**Issue: Poor search results quality**
```python
def troubleshoot_search_quality(integration_manager, search_results):
    """Troubleshoot hybrid search quality issues"""
    
    quality_metrics = {
        'total_results': len(search_results),
        'avg_combined_score': sum(r.combined_score for r in search_results) / len(search_results) if search_results else 0,
        'score_distribution': {},
        'recommendations': []
    }
    
    # Analyze score distribution
    for result in search_results:
        score_bucket = int(result.combined_score * 10) / 10  # Round to 0.1
        quality_metrics['score_distribution'][score_bucket] = quality_metrics['score_distribution'].get(score_bucket, 0) + 1
    
    # Generate recommendations
    if quality_metrics['avg_combined_score'] < 0.3:
        quality_metrics['recommendations'].extend([
            "Consider adjusting vector/text weight balance",
            "Check if query vector is properly normalized",
            "Review text field analyzers and tokenization",
            "Verify vector embeddings are from compatible model"
        ])
    
    if quality_metrics['total_results'] < 5:
        quality_metrics['recommendations'].extend([
            "Increase result count (k parameter)",
            "Reduce metadata filters if too restrictive",
            "Check index contains relevant data",
            "Consider lowering similarity thresholds"
        ])
    
    # Score balance analysis
    if search_results:
        vector_scores = [r.vector_score for r in search_results]
        text_scores = [r.keyword_score for r in search_results]
        
        vector_avg = sum(vector_scores) / len(vector_scores)
        text_avg = sum(text_scores) / len(text_scores)
        
        if vector_avg / text_avg > 5:  # Vector scores dominating
            quality_metrics['recommendations'].append("Consider increasing text_weight for better balance")
        elif text_avg / vector_avg > 5:  # Text scores dominating
            quality_metrics['recommendations'].append("Consider increasing vector_weight for better balance")
    
    return quality_metrics
```

This comprehensive guide provides all the necessary information for implementing, configuring, and optimizing OpenSearch integration with S3Vector using both export and engine patterns. The hybrid search capabilities enable sophisticated multi-modal search scenarios while the cost monitoring ensures efficient resource utilization.