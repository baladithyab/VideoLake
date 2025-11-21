# VideoLake API Reference

> **Complete REST API documentation for VideoLake platform**

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URLs](#base-urls)
4. [Common Patterns](#common-patterns)
5. [Search Endpoints](#search-endpoints)
6. [Ingestion Endpoints](#ingestion-endpoints)
7. [Infrastructure Endpoints](#infrastructure-endpoints)
8. [Embedding Endpoints](#embedding-endpoints)
9. [Benchmark Endpoints](#benchmark-endpoints)
10. [Error Handling](#error-handling)
11. [Rate Limits](#rate-limits)
12. [Code Examples](#code-examples)

---

## Overview

The VideoLake API is a RESTful API that provides programmatic access to all VideoLake features including video search, ingestion, infrastructure management, and benchmarking.

### API Version

Current version: **v1.0**

### Content Type

All requests and responses use `application/json` unless otherwise specified.

### Interactive Documentation

Access interactive API docs at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Authentication

### Current Implementation

VideoLake currently uses **AWS IAM authentication** for backend services. No additional authentication is required for local development.

### Future: API Keys

API key authentication will be added in a future release:

```http
GET /api/search/query
Authorization: Bearer YOUR_API_KEY
```

---

## Base URLs

### Development
```
http://localhost:8000
```

### Production
```
https://api.videolake.your-domain.com
```

All endpoint paths in this document are relative to the base URL.

---

## Common Patterns

### Standard Response Format

**Success Response:**
```json
{
  "success": true,
  "data": { ... },
  "metadata": {
    "timestamp": "2025-01-13T12:00:00Z",
    "request_id": "abc-123"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid query parameter",
    "details": { ... }
  }
}
```

### Pagination

For endpoints returning lists:

```http
GET /api/search/history?page=1&limit=20
```

**Response:**
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 150,
    "pages": 8
  }
}
```

### Timestamps

All timestamps use **ISO 8601 format** in UTC:
```
2025-01-13T12:00:00Z
```

---

## Search Endpoints

### POST /api/search/query

Execute a vector search query against specified backend.

**Request:**
```http
POST /api/search/query
Content-Type: application/json

{
  "query_text": "person walking in park",
  "vector_types": ["visual-text", "visual-image", "audio"],
  "top_k": 10,
  "backend": "s3_vector",
  "index_arn": "optional-index-arn"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query_text` | string | Yes | Search query text (1-10000 chars) |
| `vector_types` | array[string] | No | Vector types to search. Default: all |
| `top_k` | integer | No | Number of results (1-1000). Default: 10 |
| `backend` | string | No | Backend: `s3_vector`, `lancedb`, `qdrant`, `opensearch` |
| `index_arn` | string | No | Specific index ARN (backend-dependent) |

**Response:**
```json
{
  "success": true,
  "backend": "s3_vector",
  "results": [
    {
      "id": "video1-segment-12",
      "score": 0.94,
      "metadata": {
        "video_id": "video1",
        "filename": "sample.mp4",
        "s3_uri": "s3://bucket/videos/sample.mp4",
        "start_time": 45.2,
        "end_time": 50.5,
        "segment_id": 12,
        "embedding_type": "visual-text",
        "text": "Person walking through park..."
      },
      "content_type": "video/segment"
    }
  ],
  "query_time_ms": 15.3,
  "total_results": 10,
  "timing_report": {
    "total_ms": 15.3,
    "embedding_generation_ms": 10.2,
    "search_ms": 5.1
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid parameters
- `500 Internal Server Error` - Search failed

---

### POST /api/search/compare-backends

Compare query performance across multiple backends.

**Request:**
```http
POST /api/search/compare-backends
Content-Type: application/json

{
  "query_text": "sunset over ocean",
  "backends": ["s3_vector", "lancedb", "qdrant"],
  "top_k": 10
}
```

**Response:**
```json
{
  "success": true,
  "query": "sunset over ocean",
  "backends": ["s3_vector", "lancedb", "qdrant"],
  "results": {
    "s3_vector": {
      "success": true,
      "results": [ ... ],
      "query_time_ms": 15.3,
      "result_count": 10
    },
    "lancedb": {
      "success": true,
      "results": [ ... ],
      "query_time_ms": 95.2,
      "result_count": 10
    },
    "qdrant": {
      "success": true,
      "results": [ ... ],
      "query_time_ms": 85.7,
      "result_count": 10
    }
  },
  "comparison": {
    "fastest_backend": "s3_vector",
    "fastest_latency_ms": 15.3,
    "slowest_backend": "lancedb",
    "slowest_latency_ms": 95.2,
    "average_latency_ms": 65.4,
    "all_latencies": {
      "s3_vector": 15.3,
      "lancedb": 95.2,
      "qdrant": 85.7
    }
  }
}
```

---

### GET /api/search/backends

List all available vector store backends.

**Request:**
```http
GET /api/search/backends
```

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
  "total": 3
}
```

---

### GET /api/search/supported-vector-types

Get list of supported vector embedding types.

**Request:**
```http
GET /api/search/supported-vector-types
```

**Response:**
```json
{
  "success": true,
  "vector_types": [
    {
      "name": "visual-text",
      "description": "Scene descriptions and text content",
      "dimension": 1024
    },
    {
      "name": "visual-image",
      "description": "Visual content and objects",
      "dimension": 1024
    },
    {
      "name": "audio",
      "description": "Audio and speech content",
      "dimension": 1024
    }
  ]
}
```

---

## Ingestion Endpoints

### GET /api/ingestion/datasets

List available standard datasets for ingestion.

**Request:**
```http
GET /api/ingestion/datasets
```

**Response:**
```json
{
  "success": true,
  "datasets": [
    {
      "id": "cc-open-validation",
      "name": "CC-Open Validation Set",
      "description": "Standard validation set with 100 videos",
      "video_count": 100,
      "total_duration_minutes": 45
    },
    {
      "id": "kinetics-400-sample",
      "name": "Kinetics 400 Sample",
      "description": "Sample of 50 videos from Kinetics dataset",
      "video_count": 50,
      "total_duration_minutes": 8
    }
  ]
}
```

---

### POST /api/ingestion/upload-url

Upload and ingest a video from a public URL.

**Request:**
```http
POST /api/ingestion/upload-url
Content-Type: application/json

{
  "url": "https://example.com/video.mp4",
  "model_type": "marengo-2.7",
  "backend_types": ["s3_vector", "lancedb"]
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Public URL of video file |
| `model_type` | string | No | Model: `marengo-2.7`, `nova`, `titan`. Default: `marengo-2.7` |
| `backend_types` | array[string] | No | Backends to index. Default: all deployed |

**Response:**
```json
{
  "job_id": "job-url-123",
  "status": "accepted",
  "message": "Download and ingestion started for video.mp4"
}
```

---

### POST /api/ingestion/start

Start a video ingestion job (S3 URI).

**Request:**
```http
POST /api/ingestion/start
Content-Type: application/json

{
  "video_path": "s3://bucket/videos/sample.mp4",
  "model_type": "marengo-2.7",
  "backend_types": ["s3_vector", "lancedb"]
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `video_path` | string | Yes | S3 URI of video file |
| `model_type` | string | No | Model: `marengo-2.7`, `nova`, `titan`. Default: `marengo-2.7` |
| `backend_types` | array[string] | No | Backends to index. Default: all deployed |

**Response:**
```json
{
  "job_id": "job-abc-123",
  "status": "accepted",
  "message": "Ingestion started for s3://bucket/videos/sample.mp4"
}
```

**Status Codes:**
- `202 Accepted` - Job started
- `400 Bad Request` - Invalid S3 URI or parameters
- `500 Internal Server Error` - Failed to start job

---

### GET /api/processing/status/{job_id}

Get status of a video processing job.

**Request:**
```http
GET /api/processing/status/job-abc-123
```

**Response:**
```json
{
  "job_id": "job-abc-123",
  "status": "processing",
  "progress": 45,
  "message": "Generating embeddings...",
  "created_at": "2025-01-13T12:00:00Z",
  "updated_at": "2025-01-13T12:02:30Z",
  "details": {
    "video_path": "s3://bucket/videos/sample.mp4",
    "model_type": "marengo-2.7",
    "segments_processed": 12,
    "segments_total": 27
  }
}
```

**Status Values:**
- `accepted` - Job queued
- `processing` - Currently processing
- `indexing` - Storing embeddings
- `completed` - Successfully finished
- `failed` - Processing failed

---

## Infrastructure Endpoints

### GET /api/infrastructure/status

Get deployment status of all vector store backends.

**Request:**
```http
GET /api/infrastructure/status
```

**Response:**
```json
{
  "deployed_stores": [
    {
      "name": "s3vector",
      "deployed": true,
      "endpoint": "s3vectors:us-east-1",
      "status": "deployed",
      "estimated_cost_monthly": 0.50
    },
    {
      "name": "lancedb",
      "deployed": true,
      "endpoint": "http://10.0.1.23:8000",
      "status": "deployed",
      "estimated_cost_monthly": 28.00
    },
    {
      "name": "qdrant",
      "deployed": false,
      "endpoint": null,
      "status": "not_deployed",
      "estimated_cost_monthly": 30.00
    }
  ],
  "total_deployed": 2,
  "total_cost_monthly": 28.50
}
```

---

### POST /api/infrastructure/{backend_type}/apply

Deploy infrastructure for a specific backend.

⚠️ **Requires Terraform access**

**Request:**
```http
POST /api/infrastructure/qdrant/apply
```

**Response:**
```json
{
  "status": "success",
  "backend_type": "qdrant",
  "operation_id": "op-xyz-789",
  "output": {
    "message": "Terraform apply started",
    "estimated_time_minutes": 10
  }
}
```

---

### POST /api/infrastructure/{backend_type}/destroy

Destroy infrastructure for a specific backend.

⚠️ **Warning**: This permanently removes the backend and all data.

**Request:**
```http
POST /api/infrastructure/qdrant/destroy
```

**Response:**
```json
{
  "status": "success",
  "backend_type": "qdrant",
  "operation_id": "op-xyz-790",
  "output": {
    "message": "Terraform destroy started",
    "estimated_time_minutes": 5
  }
}
```

---

### GET /api/infrastructure/{backend_type}/output

Get Terraform outputs for a specific backend.

**Request:**
```http
GET /api/infrastructure/qdrant/output
```

**Response:**
```json
{
  "endpoint": "http://10.0.1.45:6333",
  "port": 6333,
  "security_group_id": "sg-abc123",
  "subnet_ids": ["subnet-1", "subnet-2"],
  "task_definition_arn": "arn:aws:ecs:..."
}
```

---

## Embedding Endpoints

### POST /api/embeddings/generate

Generate embedding vector for text query.

**Request:**
```http
POST /api/embeddings/generate
Content-Type: application/json

{
  "text": "person walking in park",
  "model_id": "amazon.titan-embed-text-v2:0"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | Yes | Text to embed (1-10000 chars) |
| `model_id` | string | No | Bedrock model ID. Default: titan-embed-text-v2 |

**Response:**
```json
{
  "success": true,
  "embedding": [0.123, -0.456, 0.789, ...],
  "model_id": "amazon.titan-embed-text-v2:0",
  "dimension": 1024,
  "timing_report": {
    "total_ms": 10.2,
    "bedrock_api_ms": 9.8
  }
}
```

---

### GET /api/embeddings/models

List available embedding models.

**Request:**
```http
GET /api/embeddings/models
```

**Response:**
```json
{
  "success": true,
  "models": [
    {
      "id": "amazon.titan-embed-text-v2:0",
      "name": "Amazon Titan Text v2",
      "type": "text",
      "dimension": 1024,
      "provider": "AWS Bedrock"
    },
    {
      "id": "amazon.titan-embed-image-v1",
      "name": "Amazon Titan Image v1",
      "type": "multimodal",
      "dimension": 1024,
      "provider": "AWS Bedrock"
    },
    {
      "id": "twelvelabs.marengo-embed-2-7-v1:0",
      "name": "TwelveLabs Marengo 2.7",
      "type": "video",
      "dimension": 1024,
      "provider": "TwelveLabs"
    }
  ]
}
```

---

## Benchmark Endpoints

### POST /api/benchmark/start

Start a performance benchmark.

**Request:**
```http
POST /api/benchmark/start
Content-Type: application/json

{
  "backends": ["s3_vector", "lancedb", "qdrant"],
  "query_count": 100,
  "dataset": "cc-open",
  "vector_types": ["visual-text"]
}
```

**Response:**
```json
{
  "benchmark_id": "bench-abc-123",
  "status": "running",
  "estimated_duration_minutes": 5,
  "backends": ["s3_vector", "lancedb", "qdrant"],
  "query_count": 100
}
```

---

### POST /api/benchmark/start-ecs

Start a benchmark job on ECS infrastructure (for long-running tasks).

**Request:**
```http
POST /api/benchmark/start-ecs
Content-Type: application/json

{
  "backends": ["s3_vector", "lancedb", "qdrant"],
  "query_count": 1000,
  "dataset": "cc-open",
  "vector_types": ["visual-text"]
}
```

**Response:**
```json
{
  "benchmark_id": "bench-ecs-789",
  "task_arn": "arn:aws:ecs:us-east-1:123456789012:task/benchmark-cluster/abc-123",
  "status": "provisioning",
  "estimated_duration_minutes": 15,
  "message": "ECS task started successfully"
}
```

---

### GET /api/benchmark/status/{benchmark_id}

Get status of a running benchmark.

**Request:**
```http
GET /api/benchmark/status/bench-abc-123
```

**Response:**
```json
{
  "benchmark_id": "bench-abc-123",
  "status": "running",
  "progress": 67,
  "queries_completed": 67,
  "queries_total": 100,
  "started_at": "2025-01-13T12:00:00Z"
}
```

---

### GET /api/benchmark/results/{benchmark_id}

Get results of a completed benchmark.

**Request:**
```http
GET /api/benchmark/results/bench-abc-123
```

**Response:**
```json
{
  "benchmark_id": "bench-abc-123",
  "status": "completed",
  "results": {
    "s3_vector": {
      "p50_latency_ms": 0.015,
      "p95_latency_ms": 0.016,
      "p99_latency_ms": 0.018,
      "throughput_qps": 60946,
      "success_rate": 1.0,
      "queries_total": 100,
      "queries_successful": 100
    },
    "lancedb": {
      "p50_latency_ms": 95,
      "p95_latency_ms": 120,
      "p99_latency_ms": 145,
      "throughput_qps": 11,
      "success_rate": 1.0,
      "queries_total": 100,
      "queries_successful": 100
    }
  },
  "completed_at": "2025-01-13T12:05:23Z"
}
```

---

### GET /api/benchmark/history

List historical benchmark results.

**Request:**
```http
GET /api/benchmark/history?page=1&limit=20
```

**Response:**
```json
{
  "success": true,
  "benchmarks": [
    {
      "benchmark_id": "bench-abc-123",
      "status": "completed",
      "backends": ["s3_vector", "lancedb"],
      "query_count": 100,
      "completed_at": "2025-01-13T12:05:23Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

---

## Error Handling

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "query_text",
      "issue": "Too long"
    }
  },
  "request_id": "req-abc-123"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `NOT_FOUND` | 404 | Resource not found |
| `BACKEND_UNAVAILABLE` | 503 | Vector store backend unavailable |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |

### Error Examples

**Validation Error:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "query_text must be between 1 and 10000 characters",
    "details": {
      "field": "query_text",
      "provided_length": 15000,
      "max_length": 10000
    }
  }
}
```

**Backend Unavailable:**
```json
{
  "success": false,
  "error": {
    "code": "BACKEND_UNAVAILABLE",
    "message": "Qdrant backend is not responding",
    "details": {
      "backend": "qdrant",
      "last_health_check": "2025-01-13T12:00:00Z",
      "status": "unhealthy"
    }
  }
}
```

---

## Rate Limits

### Current Limits

**Development:**
- No rate limits

**Production (Future):**
- 100 requests per minute per IP
- 1000 requests per hour per API key

### Rate Limit Headers

**Response Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1673625600
```

### Rate Limit Error

**Response (429 Too Many Requests):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "details": {
      "limit": 100,
      "window_seconds": 60,
      "reset_at": "2025-01-13T12:01:00Z"
    }
  }
}
```

---

## Code Examples

### Python

**Search Videos:**
```python
import requests

# Execute search
response = requests.post(
    'http://localhost:8000/api/search/query',
    json={
        'query_text': 'person walking in park',
        'backend': 's3_vector',
        'top_k': 10
    }
)

results = response.json()
print(f"Found {len(results['results'])} results")

for result in results['results']:
    print(f"Video: {result['metadata']['filename']}")
    print(f"Time: {result['metadata']['start_time']}s")
    print(f"Score: {result['score']:.2%}")
```

**Start Ingestion:**
```python
# Start video ingestion
response = requests.post(
    'http://localhost:8000/api/ingestion/start',
    json={
        'video_path': 's3://bucket/videos/sample.mp4',
        'model_type': 'marengo-2.7',
        'backend_types': ['s3_vector', 'lancedb']
    }
)

job = response.json()
job_id = job['job_id']

# Poll for completion
import time
while True:
    status = requests.get(
        f'http://localhost:8000/api/processing/status/{job_id}'
    ).json()
    
    print(f"Status: {status['status']} ({status['progress']}%)")
    
    if status['status'] == 'completed':
        break
    
    time.sleep(10)
```

### JavaScript

**Search Videos:**
```javascript
// Execute search
const response = await fetch('http://localhost:8000/api/search/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query_text: 'person walking in park',
    backend: 's3_vector',
    top_k: 10
  })
});

const results = await response.json();
console.log(`Found ${results.results.length} results`);

results.results.forEach(result => {
  console.log(`Video: ${result.metadata.filename}`);
  console.log(`Time: ${result.metadata.start_time}s`);
  console.log(`Score: ${(result.score * 100).toFixed(2)}%`);
});
```

**Compare Backends:**
```javascript
const response = await fetch('http://localhost:8000/api/search/compare-backends', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query_text: 'sunset over ocean',
    backends: ['s3_vector', 'lancedb', 'qdrant'],
    top_k: 10
  })
});

const comparison = await response.json();
console.log('Performance Comparison:');
Object.entries(comparison.comparison.all_latencies).forEach(([backend, latency]) => {
  console.log(`${backend}: ${latency}ms`);
});
```

### cURL

**Search Videos:**
```bash
curl -X POST http://localhost:8000/api/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "person walking in park",
    "backend": "s3_vector",
    "top_k": 10
  }'
```

**Get Infrastructure Status:**
```bash
curl http://localhost:8000/api/infrastructure/status
```

**Generate Embedding:**
```bash
curl -X POST http://localhost:8000/api/embeddings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "sample query text",
    "model_id": "amazon.titan-embed-text-v2:0"
  }'
```

---

## SDK Support

### Official SDKs

**Coming Soon:**
- Python SDK
- JavaScript/TypeScript SDK
- Go SDK

### Community SDKs

Check [GitHub](https://github.com/your-org/videolake) for community-contributed SDKs.

---

## Versioning

### API Versioning Strategy

VideoLake uses **URL versioning**:
```
/api/v1/search/query
/api/v2/search/query
```

Current version: **v1** (implicit, no version prefix)

### Deprecation Policy

- Backwards-incompatible changes → new version
- Deprecation notice: 6 months minimum
- Old versions supported: 12 months minimum

---

## Support

### Getting Help

- **Interactive Docs**: http://localhost:8000/docs
- **GitHub Issues**: [Report bugs](https://github.com/your-org/videolake/issues)
- **Documentation**: [Full docs](../VIDEOLAKE_README.md)

### Reporting API Issues

When reporting API issues, include:
1. Request method and endpoint
2. Request body (sanitized)
3. Response status and body
4. Expected vs. actual behavior
5. Timestamp and environment

---

## Related Documentation

- [VideoLake README](../VIDEOLAKE_README.md) - Platform overview
- [Architecture Guide](VIDEOLAKE_ARCHITECTURE.md) - System architecture
- [Deployment Guide](VIDEOLAKE_DEPLOYMENT.md) - Setup instructions
- [User Guide](VIDEOLAKE_USER_GUIDE.md) - End-user documentation

---

*Document Version: 1.0*  
*Last Updated: 2025-11-21*  
*Status: Complete*