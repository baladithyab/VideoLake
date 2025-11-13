# Videolake REST API Documentation

## Overview

Videolake is a comprehensive AWS vector store comparison platform that supports multiple vector store backends for performance evaluation and optimization. The platform processes videos using TwelveLabs Marengo embeddings and provides similarity search across multiple backend options (AWS S3Vector, OpenSearch, Qdrant, LanceDB).

### Architecture Philosophy

- **Multi-Backend Support**: Compare performance across AWS S3Vector, OpenSearch, Qdrant, and LanceDB
- **Terraform-First**: All infrastructure managed through Terraform for reproducibility
- **Video-Centric**: Optimized for video processing and multimodal search
- **Cost-Effective**: AWS S3Vector backend provides 90%+ cost savings vs traditional vector databases

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication for local development. In production deployments, implement appropriate authentication mechanisms.

---

## API Endpoints by Category

### 1. Health & Status

#### `GET /`
**Root endpoint - API information**

**Response:**
```json
{
  "message": "Videolake API",
  "version": "1.0.0", 
  "status": "running"
}
```

#### `GET /api/health`
**Deep health check with service connectivity validation**

Checks:
- Service initialization
- AWS connectivity (S3, Bedrock)
- TwelveLabs API availability
- Backend service health

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "checks": {
    "services": {
      "storage_manager": true,
      "search_engine": true,
      "twelvelabs_service": true,
      "bedrock_service": true
    },
    "aws_s3": {
      "status": "healthy"
    },
    "twelvelabs_api": {
      "status": "healthy",
      "status_code": 200
    },
    "aws_bedrock": {
      "status": "healthy",
      "models_available": 15
    }
  }
}
```

---

### 2. Resource Management (Read-Only)

> ⚠️ **TERRAFORM-FIRST ARCHITECTURE**: All infrastructure creation/deletion must be done through Terraform. These endpoints provide read-only views of deployed infrastructure.

#### `GET /api/resources/deployed-resources-tree`
**Get hierarchical view of deployed infrastructure from terraform.tfstate**

Returns complete infrastructure tree showing:
- Shared media buckets
- Vector backends (S3Vector, OpenSearch, Qdrant, LanceDB) with health checks

**Response:**
```json
{
  "success": true,
  "tree": {
    "shared_resources": {
      "type": "shared",
      "name": "Shared Resources",
      "status": "active",
      "children": [
        {
          "type": "s3_bucket",
          "name": "videolake-media-bucket",
          "arn": "arn:aws:s3:::videolake-media-bucket",
          "region": "us-east-1",
          "status": "active"
        }
      ]
    },
    "vector_backends": [
      {
        "type": "s3vector",
        "name": "S3 Vectors",
        "status": "deployed",
        "connectivity": "healthy",
        "endpoint": "s3vectors.us-east-1.amazonaws.com",
        "response_time_ms": 45.2,
        "children": [...]
      },
      {
        "type": "opensearch",
        "name": "OpenSearch",
        "status": "deployed",
        "connectivity": "healthy",
        "endpoint": "https://my-domain.us-east-1.es.amazonaws.com",
        "response_time_ms": 120.5,
        "children": [...]
      }
    ]
  },
  "metadata": {
    "tfstate_path": "terraform/terraform.tfstate",
    "tfstate_modified": 1705318200.0,
    "total_resources": 15
  }
}
```

#### `GET /api/resources/scan`
**Scan for existing AWS resources**

Scans AWS account for existing S3 buckets, OpenSearch domains, and vector indexes.

**Response:**
```json
{
  "success": true,
  "resources": {
    "s3_buckets": [...],
    "opensearch_domains": [...],
    "vector_indexes": [...]
  }
}
```

#### `GET /api/resources/registry`
**Get current resource registry**

**Response:**
```json
{
  "success": true,
  "registry": {...},
  "active_resources": [...],
  "summary": {
    "vector_buckets": 2,
    "indexes": 5,
    "opensearch_domains": 1,
    "opensearch_collections": 0
  }
}
```

#### `GET /api/resources/validate-backend/{backend_type}`
**Validate backend connectivity**

Tests connectivity to a specific vector store backend.

**Parameters:**
- `backend_type`: Backend to validate (`s3_vector`, `opensearch`, `qdrant`, `lancedb`)

**Response:**
```json
{
  "success": true,
  "backend_type": "opensearch",
  "validation": {
    "accessible": true,
    "endpoint": "https://my-domain.us-east-1.es.amazonaws.com",
    "response_time_ms": 125.3,
    "health_status": "healthy",
    "details": {
      "cluster_name": "my-cluster",
      "version": "2.11.1"
    }
  }
}
```

#### `POST /api/resources/validate-backends`
**Batch validate multiple backends**

**Request:**
```json
{
  "backend_types": ["s3_vector", "opensearch", "qdrant", "lancedb"]
}
```

**Response:**
```json
{
  "success": true,
  "total_backends": 4,
  "accessible_backends": 3,
  "inaccessible_backends": 1,
  "results": {
    "s3_vector": {
      "accessible": true,
      "endpoint": "s3vectors.us-east-1.amazonaws.com",
      "response_time_ms": 45.2,
      "health_status": "healthy"
    },
    "opensearch": {
      "accessible": true,
      "endpoint": "https://my-domain.us-east-1.es.amazonaws.com",
      "response_time_ms": 120.5,
      "health_status": "healthy"
    },
    "qdrant": {
      "accessible": false,
      "endpoint": "unknown",
      "response_time_ms": 0.0,
      "health_status": "unhealthy",
      "error_message": "Provider not available for qdrant"
    },
    "lancedb": {
      "accessible": true,
      "endpoint": "s3://my-lancedb-bucket/",
      "response_time_ms": 89.1,
      "health_status": "healthy"
    }
  }
}
```

#### `GET /api/resources/vector-indexes/{bucket_name}`
**List vector indexes in bucket**

**Parameters:**
- `bucket_name`: Name of the S3 vector bucket

**Response:**
```json
{
  "success": true,
  "bucket_name": "my-vector-bucket",
  "index_count": 3,
  "indexes": [
    {
      "index_name": "video-embeddings",
      "index_arn": "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-vector-bucket/index/video-embeddings",
      "dimension": 1024,
      "distance_metric": "cosine",
      "data_type": "float32",
      "vector_count": 15420,
      "status": "active",
      "created_at": "2024-01-15T10:30:00.000Z"
    }
  ]
}
```

#### `GET /api/resources/vector-index/status`
**Get detailed index status**

**Query Parameters:**
- `index_arn`: ARN of the vector index

**Response:**
```json
{
  "success": true,
  "index_arn": "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index",
  "bucket_name": "my-bucket",
  "index_name": "my-index",
  "status": "active",
  "vector_count": 15420,
  "dimension": 1024,
  "metric": "cosine",
  "data_type": "float32",
  "storage_size_mb": 63.42,
  "created_at": "2024-01-15T10:30:00.000Z",
  "last_updated": "2024-01-16T14:20:00.000Z"
}
```

---

### 3. Media Processing

#### `POST /api/processing/upload`
**Upload video file**

Upload a video file to S3 for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Body: File upload

**Response:**
```json
{
  "success": true,
  "s3_uri": "s3://my-bucket/uploads/20240115_103000_video.mp4",
  "filename": "video.mp4",
  "timing_report": {
    "total_duration_ms": 1234.5,
    "operations": {
      "create_temp_file": 45.2,
      "s3_upload": 1189.3
    }
  }
}
```

#### `POST /api/processing/process`
**Start video processing job**

Process a video using TwelveLabs Marengo to generate embeddings.

**Request:**
```json
{
  "video_s3_uri": "s3://my-bucket/video.mp4",
  "embedding_options": ["visual-text", "visual-image", "audio"],
  "start_sec": 0,
  "length_sec": 300,
  "use_fixed_length_sec": 5.0
}
```

**Notes:**
- `video_s3_uri` can be S3 URI or HTTP URL (will be downloaded to S3)
- `embedding_options`: Types of embeddings to generate
- `use_fixed_length_sec`: Fixed segment length (2-10 seconds)

**Response:**
```json
{
  "success": true,
  "job_id": "job-abc123",
  "status": "processing",
  "s3_uri": "s3://my-bucket/video.mp4",
  "timing_report": {
    "total_duration_ms": 234.5,
    "operations": {
      "start_twelvelabs_processing": 189.3
    }
  }
}
```

#### `GET /api/processing/job/{job_id}`
**Get processing job status**

**Parameters:**
- `job_id`: Processing job ID

**Response:**
```json
{
  "success": true,
  "job": {
    "job_id": "job-abc123",
    "status": "completed",
    "progress": 100.0,
    "result": {
      "video_id": "video-xyz789",
      "segments": [
        {
          "segment_id": "seg-001",
          "start_offset_sec": 0.0,
          "end_offset_sec": 5.0,
          "embedding_option": "visual-text",
          "embedding": [0.1, 0.2, ...]
        }
      ]
    }
  }
}
```

**Status Values:**
- `processing`: Job is running
- `completed`: Job finished successfully
- `failed`: Job failed (check `error` field)

#### `GET /api/processing/jobs`
**List all processing jobs**

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "job-abc123",
      "status": "completed",
      "progress": 100.0
    }
  ]
}
```

#### `GET /api/processing/sample-videos`
**Get list of sample videos**

Returns Creative Commons sample videos for testing.

**Response:**
```json
{
  "success": true,
  "categories": [
    {
      "name": "Movies",
      "videos": [
        {
          "id": "big-buck-bunny",
          "title": "Big Buck Bunny",
          "description": "...",
          "sources": ["http://commondatastorage.googleapis.com/..."],
          "thumb": "http://..."
        }
      ]
    }
  ]
}
```

#### `POST /api/processing/process-sample`
**Process sample video**

Download and process a sample video.

**Query Parameters:**
- `video_id`: Sample video ID
- `embedding_options`: List of embedding options (default: all)

**Response:**
```json
{
  "success": true,
  "job_id": "job-def456",
  "status": "processing",
  "video_title": "Big Buck Bunny",
  "s3_uri": "s3://my-bucket/sample-videos/big-buck-bunny.mp4"
}
```

#### `POST /api/resources/store-embeddings-to-index`
**Store processed embeddings to index**

Store completed job embeddings to a specific vector index.

**Request:**
```json
{
  "job_id": "job-abc123",
  "index_arn": "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index",
  "backend": "s3_vector"
}
```

**Backend Options:**
- `s3_vector`: AWS S3 Vector (direct)
- `opensearch`: OpenSearch Servicе
- `qdrant`: Qdrant vector database
- `lancedb`: LanceDB columnar database

**Response:**
```json
{
  "success": true,
  "message": "Successfully stored 60 embeddings to index",
  "job_id": "job-abc123",
  "index_arn": "arn:aws:s3vectors:...",
  "backend": "s3_vector",
  "stored_count": 60,
  "result": {...}
}
```

---

### 4. Search & Query

#### `POST /api/search/query`
**Execute similarity search**

Search for similar content across specified backend.

**Request:**
```json
{
  "query_text": "car chase scene in urban environment",
  "vector_types": ["visual-text", "visual-image", "audio"],
  "top_k": 10,
  "index_arn": "arn:aws:s3vectors:...",
  "backend": "s3_vector"
}
```

**Backend Options:**
- `s3_vector`: AWS S3 Vector (direct)
- `opensearch`: OpenSearch with hybrid search
- `lancedb`: LanceDB columnar database
- `qdrant`: Qdrant cloud-native database

**Response:**
```json
{
  "success": true,
  "backend": "s3_vector",
  "results": [
    {
      "id": "seg-001",
      "score": 0.95,
      "metadata": {
        "video_id": "video-xyz",
        "start_sec": 120.0,
        "end_sec": 125.0
      },
      "vector_type": "visual-text"
    }
  ],
  "query_time_ms": 45.2,
  "total_results": 10,
  "timing_report": {...}
}
```

#### `POST /api/search/multi-vector`
**Multi-vector search**

Search across multiple vector types simultaneously.

**Request:**
```json
{
  "query_text": "action scene with cars",
  "vector_types": ["visual-text", "visual-image", "audio"],
  "top_k": 10,
  "enable_reranking": true
}
```

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": "seg-001",
      "score": 0.95,
      "metadata": {...},
      "vector_type": "visual-text",
      "source": "s3_vector"
    }
  ],
  "query_time_ms": 123.5,
  "total_results": 10,
  "vector_type_breakdown": {
    "visual-text": 4,
    "visual-image": 3,
    "audio": 3
  },
  "timing_report": {...}
}
```

#### `POST /api/search/dual-pattern`
**Dual pattern search (S3Vector + OpenSearch)**

Execute search on both S3Vector and OpenSearch simultaneously for comparison.

**Request:**
```json
{
  "query_text": "sunset scene",
  "top_k": 10,
  "index_arn": "arn:aws:s3vectors:..."
}
```

**Response:**
```json
{
  "success": true,
  "s3vector": {
    "results": [...],
    "query_time_ms": 45.2
  },
  "opensearch": {
    "results": [...],
    "query_time_ms": 120.5
  },
  "timing_report": {...}
}
```

#### `POST /api/search/compare-backends`
**Compare performance across multiple backends**

Execute same query across all available backends for performance comparison.

**Request:**
```json
{
  "query_text": "action scene",
  "backends": ["s3_vector", "opensearch", "lancedb", "qdrant"],
  "top_k": 10,
  "index_arn": "arn:aws:s3vectors:..."
}
```

**Response:**
```json
{
  "success": true,
  "query": "action scene",
  "backends": ["s3_vector", "opensearch", "lancedb", "qdrant"],
  "results": {
    "s3_vector": {
      "success": true,
      "results": [...],
      "query_time_ms": 45.2,
      "result_count": 10
    },
    "opensearch": {
      "success": true,
      "results": [...],
      "query_time_ms": 120.5,
      "result_count": 10
    }
  },
  "comparison": {
    "fastest_backend": "s3_vector",
    "fastest_latency_ms": 45.2,
    "slowest_backend": "opensearch",
    "slowest_latency_ms": 120.5,
    "latency_range_ms": 75.3,
    "average_latency_ms": 82.85,
    "all_latencies": {
      "s3_vector": 45.2,
      "opensearch": 120.5
    }
  },
  "timing_report": {...}
}
```

#### `GET /api/search/backends`
**List available backends**

**Response:**
```json
{
  "success": true,
  "backends": [
    {
      "type": "s3_vector",
      "name": "S3 VECTOR",
      "description": "AWS-native vector storage with S3 integration",
      "available": true
    },
    {
      "type": "opensearch",
      "name": "OPENSEARCH",
      "description": "Hybrid search with vector and keyword capabilities",
      "available": true
    },
    {
      "type": "lancedb",
      "name": "LANCEDB",
      "description": "High-performance columnar vector database",
      "available": true
    },
    {
      "type": "qdrant",
      "name": "QDRANT",
      "description": "Cloud-native vector database with advanced filtering",
      "available": false
    }
  ],
  "total": 4
}
```

#### `GET /api/search/supported-vector-types`
**Get supported vector types**

**Response:**
```json
{
  "success": true,
  "vector_types": [
    "visual-text",
    "visual-image",
    "audio"
  ]
}
```

#### `POST /api/search/generate-embedding`
**Generate text embedding**

Generate embedding for text query using Bedrock.

**Query Parameters:**
- `text`: Text to embed
- `model_id`: Optional Bedrock model ID

**Response:**
```json
{
  "success": true,
  "embedding": [0.1, 0.2, 0.3, ...],
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimension": 1024,
  "timing_report": {...}
}
```

---

### 5. Embeddings & Visualization

#### `POST /api/embeddings/visualize`
**Generate embedding visualization**

Create 2D/3D visualization of embedding space.

**Request:**
```json
{
  "index_arn": "arn:aws:s3vectors:...",
  "method": "PCA",
  "n_components": 2,
  "query_embedding": [0.1, 0.2, ...],
  "max_points": 1000
}
```

**Visualization Methods:**
- `PCA`: Principal Component Analysis (linear)
- `t-SNE`: t-Distributed Stochastic Neighbor Embedding (non-linear)
- `UMAP`: Uniform Manifold Approximation (fast non-linear)

**Response:**
```json
{
  "success": true,
  "visualization": {
    "points": [[0.1, 0.2], [0.3, 0.4], ...],
    "labels": ["seg-001", "seg-002", ...],
    "metadata": [...]
  },
  "timing_report": {...}
}
```

#### `POST /api/embeddings/analyze`
**Analyze embedding space**

Compute statistics and similarities for a set of embeddings.

**Request:**
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "labels": ["seg-001", "seg-002"]
}
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "num_embeddings": 100,
    "dimension": 1024,
    "mean_embedding": [0.1, 0.2, ...],
    "std_embedding": [0.05, 0.03, ...],
    "avg_similarity": 0.75,
    "min_similarity": 0.45,
    "max_similarity": 0.99
  },
  "timing_report": {...}
}
```

#### `GET /api/embeddings/methods`
**Get visualization methods**

**Response:**
```json
{
  "success": true,
  "methods": [
    {
      "id": "PCA",
      "name": "Principal Component Analysis",
      "description": "Linear dimensionality reduction"
    },
    {
      "id": "t-SNE",
      "name": "t-Distributed Stochastic Neighbor Embedding",
      "description": "Non-linear dimensionality reduction for visualization"
    },
    {
      "id": "UMAP",
      "name": "Uniform Manifold Approximation and Projection",
      "description": "Fast non-linear dimensionality reduction"
    }
  ]
}
```

---

### 6. Analytics

#### `GET /api/analytics/performance`
**Get performance metrics**

**Response:**
```json
{
  "success": true,
  "metrics": {
    "avg_query_latency_ms": 45.2,
    "avg_processing_time_sec": 91.8,
    "total_queries": 1234,
    "total_videos_processed": 56,
    "cache_hit_rate": 0.78,
    "error_rate": 0.02
  }
}
```

#### `POST /api/analytics/cost-estimate`
**Estimate processing cost**

**Request:**
```json
{
  "video_duration_minutes": 60,
  "embedding_options": ["visual-text", "visual-image", "audio"]
}
```

**Response:**
```json
{
  "success": true,
  "estimate": {
    "total_cost": 3.00,
    "breakdown": {
      "marengo_processing": 3.00,
      "storage": 0.00023,
      "search": 0.00001
    },
    "cost_per_minute": 0.05
  }
}
```

#### `GET /api/analytics/system-status`
**Get system status**

**Response:**
```json
{
  "success": true,
  "status": {
    "overall": "healthy",
    "services": {
      "bedrock": "healthy",
      "s3_vectors": "healthy",
      "twelvelabs": "healthy",
      "opensearch": "healthy"
    },
    "uptime_hours": 168.5,
    "last_check": "2024-01-15T10:30:00.000Z"
  }
}
```

#### `GET /api/analytics/usage-stats`
**Get usage statistics**

**Query Parameters:**
- `days`: Number of days to analyze (default: 7)

**Response:**
```json
{
  "success": true,
  "stats": {
    "period_days": 7,
    "total_queries": 5678,
    "total_videos_processed": 234,
    "total_embeddings_stored": 12345,
    "avg_queries_per_day": 811,
    "peak_usage_hour": 14,
    "storage_used_gb": 45.6
  }
}
```

#### `GET /api/analytics/errors`
**Get error dashboard**

**Response:**
```json
{
  "success": true,
  "errors": {
    "total_errors": 12,
    "errors_by_type": {
      "ValidationError": 5,
      "VectorStorageError": 3,
      "ProcessingError": 4
    },
    "recent_errors": [
      {
        "timestamp": "2024-01-15T10:30:00.000Z",
        "type": "ValidationError",
        "message": "Invalid video format",
        "severity": "warning"
      }
    ]
  }
}
```

---

### 7. Infrastructure Management (Terraform)

> ⚠️ **Terraform Operations**: These endpoints provide programmatic access to Terraform operations. Use with caution in production.

#### `POST /api/infrastructure/init`
**Initialize Terraform**

Run `terraform init` to prepare Terraform workspace.

**Response:**
```json
{
  "success": true,
  "message": "Terraform initialized successfully"
}
```

#### `GET /api/infrastructure/status`
**Get deployment status**

Get deployment status of all vector stores.

**Response:**
```json
{
  "deployed_stores": [
    {
      "name": "opensearch",
      "deployed": true,
      "endpoint": "https://my-domain.us-east-1.es.amazonaws.com",
      "status": "healthy",
      "estimated_cost_monthly": 125.50
    }
  ],
  "total_deployed": 2,
  "total_cost_monthly": 200.00
}
```

#### `POST /api/infrastructure/deploy`
**Deploy vector stores**

Deploy selected vector stores in background.

**Request:**
```json
{
  "vector_stores": ["qdrant", "lancedb_s3"],
  "wait_for_completion": false
}
```

**Available Vector Stores:**
- `opensearch`: OpenSearch Service domain
- `qdrant`: Qdrant on EC2/ECS
- `lancedb_s3`: LanceDB with S3 backend
- `lancedb_efs`: LanceDB with EFS backend
- `lancedb_ebs`: LanceDB with EBS backend

**Response:**
```json
{
  "success": true,
  "message": "Batch deployment started for 2 store(s)",
  "stores": ["qdrant", "lancedb_s3"],
  "operation_id": "op-abc123",
  "status": "running"
}
```

#### `POST /api/infrastructure/deploy/{vector_store}`
**Deploy single vector store**

Deploy a single vector store in background.

**Parameters:**
- `vector_store`: Store to deploy

**Response:**
```json
{
  "success": true,
  "message": "Deployment started for qdrant",
  "vector_store": "qdrant",
  "operation_id": "op-def456",
  "status": "running"
}
```

#### `DELETE /api/infrastructure/destroy`
**Destroy vector stores**

Destroy selected vector stores in background.

**Request:**
```json
{
  "vector_stores": ["qdrant", "lancedb_s3"],
  "confirm": true
}
```

**Note:** `confirm: true` is required for safety.

**Response:**
```json
{
  "success": true,
  "message": "Batch destruction started for 2 store(s)",
  "stores": ["qdrant", "lancedb_s3"],
  "operation_id": "op-ghi789",
  "status": "running"
}
```

#### `DELETE /api/infrastructure/destroy/{vector_store}`
**Destroy single vector store**

**Parameters:**
- `vector_store`: Store to destroy

**Query Parameters:**
- `confirm`: Must be `true` to proceed

**Response:**
```json
{
  "success": true,
  "message": "Destruction started for qdrant",
  "vector_store": "qdrant",
  "operation_id": "op-jkl012",
  "status": "running"
}
```

#### `GET /api/infrastructure/logs/{operation_id}`
**Stream Terraform operation logs (SSE)**

Stream real-time logs for a Terraform operation via Server-Sent Events.

**Parameters:**
- `operation_id`: Operation ID from deploy/destroy response

**Response:** Server-Sent Events stream

**Event Format:**
```
data: {"timestamp": "2024-01-15T10:30:00.000Z", "level": "INFO", "message": "Starting deployment..."}

data: {"timestamp": "2024-01-15T10:30:01.000Z", "level": "INFO", "message": "Applying Terraform changes..."}

data: {"timestamp": "2024-01-15T10:35:00.000Z", "level": "COMPLETE", "message": "Operation completed", "status": "completed"}
```

---

## Deployment Modes

Videolake supports three deployment modes:

### Mode 1: AWS S3Vector Only (Cost-Optimized)
- **Backends:** AWS S3Vector only
- **Cost:** ~$0.023/GB/month
- **Use Case:** Cost-sensitive production workloads
- **Terraform:** AWS S3Vector module enabled

### Mode 2: AWS S3Vector + Comparison Backends
- **Backends:** AWS S3Vector + one or more comparison backends
- **Cost:** $0.023-$2.00/GB/month (depends on backends)
- **Use Case:** Performance benchmarking, A/B testing
- **Terraform:** AWS S3Vector + optional backend modules enabled

### Mode 3: Comparison Backends Only
- **Backends:** OpenSearch, Qdrant, and/or LanceDB (no AWS S3Vector)
- **Cost:** $0.50-$2.00/GB/month
- **Use Case:** Existing infrastructure, specific feature requirements
- **Terraform:** Optional backend modules enabled (AWS S3Vector disabled)

---

## Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (resource doesn't exist)
- `500`: Internal Server Error

### Error Types

- `ValidationError`: Invalid input parameters
- `VectorStorageError`: Vector storage operation failed
- `AsyncProcessingError`: Video processing failed
- `ConfigurationError`: Invalid configuration
- `OpenSearchIntegrationError`: OpenSearch operation failed

---

## Rate Limiting

Currently no rate limiting in development. In production, implement appropriate rate limiting based on your infrastructure capacity.

---

## CORS Configuration

CORS is configured to allow requests from:
- `http://localhost:*` (any port)
- `http://127.0.0.1:*` (any port)

Allowed methods: GET, POST, PUT, PATCH, DELETE, OPTIONS

---

## Usage Examples

### Example 1: Complete Video Processing Workflow

```bash
# 1. Check health
curl http://localhost:8000/api/health

# 2. Upload video
curl -X POST http://localhost:8000/api/processing/upload \
  -F "file=@video.mp4"

# 3. Start processing
curl -X POST http://localhost:8000/api/processing/process \
  -H "Content-Type: application/json" \
  -d '{
    "video_s3_uri": "s3://my-bucket/video.mp4",
    "embedding_options": ["visual-text", "visual-image"],
    "use_fixed_length_sec": 5.0
  }'

# 4. Check job status
curl http://localhost:8000/api/processing/job/job-abc123

# 5. Store embeddings
curl -X POST http://localhost:8000/api/resources/store-embeddings-to-index \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-abc123",
    "index_arn": "arn:aws:s3vectors:...",
    "backend": "s3_vector"
  }'

# 6. Search
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "car chase scene",
    "top_k": 10,
    "backend": "s3_vector"
  }'
```

### Example 2: Backend Comparison

```bash
# Compare performance across all backends
curl -X POST http://localhost:8000/api/search/compare-backends \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "sunset scene",
    "backends": ["s3_vector", "opensearch", "lancedb"],
    "top_k": 10
  }'
```

### Example 3: Deploy Infrastructure

```bash
# 1. Initialize Terraform
curl -X POST http://localhost:8000/api/infrastructure/init

# 2. Deploy backends
curl -X POST http://localhost:8000/api/infrastructure/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "vector_stores": ["opensearch", "qdrant"]
  }'

# 3. Stream deployment logs (Server-Sent Events)
curl http://localhost:8000/api/infrastructure/logs/op-abc123

# 4. Check deployment status
curl http://localhost:8000/api/infrastructure/status

# 5. Validate backend connectivity
curl -X POST http://localhost:8000/api/resources/validate-backends \
  -H "Content-Type: application/json" \
  -d '{
    "backend_types": ["s3_vector", "opensearch", "qdrant"]
  }'
```

---

## Cost Comparison

### Storage Costs (per GB/month)

| Backend | Cost | Use Case |
|---------|------|----------|
| AWS S3Vector | $0.023 | Production (cost-optimized) |
| OpenSearch | $0.50-$1.00 | Hybrid search, rich queries |
| Qdrant | $0.80-$1.50 | Advanced filtering, cloud-native |
| LanceDB | $0.40-$1.20 | Columnar storage, analytics |

### Query Latency (typical)

| Backend | P50 | P95 | P99 |
|---------|-----|-----|-----|
| AWS S3Vector | 45ms | 120ms | 250ms |
| OpenSearch | 80ms | 200ms | 400ms |
| Qdrant | 60ms | 150ms | 300ms |
| LanceDB | 70ms | 180ms | 350ms |

---

## Troubleshooting

### Common Issues

#### 1. Backend Not Accessible

**Symptom:** `/validate-backend/{type}` returns `accessible: false`

**Solutions:**
- Check if backend is deployed via `/infrastructure/status`
- Verify Terraform deployment completed successfully
- Check AWS credentials and permissions
- For OpenSearch: verify security policies allow access

#### 2. Processing Job Stuck

**Symptom:** Job status remains "processing" for extended period

**Solutions:**
- Check TwelveLabs API key is valid
- Verify video file is accessible in S3
- Check TwelveLabs API status
- Review job logs for errors

#### 3. Search Returns No Results

**Symptom:** Search query returns empty results

**Solutions:**
- Verify embeddings were stored to index
- Check index ARN is correct
- Ensure backend is deployed and accessible
- Try increasing `top_k` value

#### 4. Terraform Operation Fails

**Symptom:** Deploy/destroy operation completes with error

**Solutions:**
- Check AWS credentials have sufficient permissions
- Review Terraform operation logs via `/infrastructure/logs/{operation_id}`
- Verify Terraform state is not corrupted
- Check AWS service quotas

---

## Security Best Practices

### Development

- API runs without authentication (localhost only)
- CORS restricted to localhost
- Terraform operations require explicit confirmation

### Production Recommendations

1. **Authentication**: Implement API key or OAuth2 authentication
2. **CORS**: Restrict to specific domains
3. **Rate Limiting**: Implement per-user/IP rate limits
4. **Input Validation**: All inputs are validated (already implemented)
5. **HTTPS**: Use HTTPS/TLS for all API communication
6. **IAM**: Follow principle of least privilege for AWS permissions
7. **Secrets**: Store API keys in AWS Secrets Manager
8. **Monitoring**: Enable CloudWatch logs and metrics
9. **Terraform State**: Store terraform.tfstate in encrypted S3 bucket with versioning

---

## API Client Libraries

### Python Example

```python
import requests

class VideolakeClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self):
        return requests.get(f"{self.base_url}/api/health").json()
    
    def process_video(self, s3_uri, embedding_options=None):
        if embedding_options is None:
            embedding_options = ["visual-text", "visual-image", "audio"]
        
        response = requests.post(
            f"{self.base_url}/api/processing/process",
            json={
                "video_s3_uri": s3_uri,
                "embedding_options": embedding_options,
                "use_fixed_length_sec": 5.0
            }
        )
        return response.json()
    
    def search(self, query_text, backend="s3_vector", top_k=10):
        response = requests.post(
            f"{self.base_url}/api/search/query",
            json={
                "query_text": query_text,
                "backend": backend,
                "top_k": top_k
            }
        )
        return response.json()

# Usage
client = VideolakeClient()
print(client.health_check())
```

### JavaScript/TypeScript Example

```typescript
class VideolakeClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}
  
  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/api/health`);
    return response.json();
  }
  
  async processVideo(s3Uri: string, embeddingOptions?: string[]) {
    const response = await fetch(`${this.baseUrl}/api/processing/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_s3_uri: s3Uri,
        embedding_options: embeddingOptions || ['visual-text', 'visual-image', 'audio'],
        use_fixed_length_sec: 5.0
      })
    });
    return response.json();
  }
  
  async search(queryText: string, backend: string = 's3_vector', topK: number = 10) {
    const response = await fetch(`${this.baseUrl}/api/search/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query_text: queryText,
        backend,
        top_k: topK
      })
    });
    return response.json();
  }
}

// Usage
const client = new VideolakeClient();
const health = await client.healthCheck();
console.log(health);
```

---

## Further Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Testing Guide](testing_guide.md)
- [Terraform Migration Guide](../terraform/MIGRATION_GUIDE.md)

---

## Support

For issues, questions, or contributions, please refer to the project repository.
