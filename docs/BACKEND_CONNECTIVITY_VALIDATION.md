# Backend Connectivity Validation

> **Status**: This document is current and reflects the latest connectivity validation architecture.

Comprehensive guide to the backend connectivity validation feature for vector store providers in the S3Vector platform.

## Overview

The backend connectivity validation feature provides real-time health checks for all vector store backends before processing workflows. This ensures that only accessible backends are used and provides detailed diagnostics when backends are unavailable.

**Important:** Backends have different access patterns:
- **S3Vector**: AWS SDK (boto3) only - NO HTTP REST API
- **Qdrant**: HTTP REST API with health check at root `/` (not `/health`)
- **LanceDB**: HTTP REST API at `http://18.234.151.118:8000` with `/health` endpoint

## Features

- **Real-time connectivity checks** - Tests actual backend accessibility, not just deployment status
- **Response time measurement** - Measures and reports response times in milliseconds
- **Health status reporting** - Provides detailed health status (healthy, degraded, unhealthy)
- **Batch validation** - Test multiple backends in parallel
- **Timeout protection** - All validations timeout after 5 seconds to prevent hanging
- **Detailed error reporting** - Clear error messages when backends are inaccessible

## Architecture

### Base Provider Interface

The `validate_connectivity()` method is now part of the `VectorStoreProvider` abstract base class, ensuring all providers implement connectivity validation:

```python
@abstractmethod
def validate_connectivity(self) -> Dict[str, Any]:
    """
    Validate connectivity to the vector store backend.
    
    Returns:
        Dictionary with:
            - accessible (bool): Whether backend is accessible
            - endpoint (str): Backend endpoint/URL
            - response_time_ms (float): Response time in milliseconds
            - health_status (str): Health status (healthy, degraded, unhealthy)
            - error_message (Optional[str]): Error message if not accessible
            - details (Dict): Additional backend-specific details
    """
    pass
```

### Backend Access Patterns

| Backend | Access Method | Endpoint/SDK | Health Check Path |
|---------|---------------|--------------|-------------------|
| S3Vector | AWS SDK (boto3) | `s3vectors.us-east-1.amazonaws.com` | SDK call to `list_vector_buckets()` |
| Qdrant | REST API | `http://98.93.105.87:6333` | `GET /` (root) |
| LanceDB | REST API | `http://18.234.151.118:8000` | `GET /health` |
| OpenSearch | AWS SDK + REST | AWS OpenSearch service | SDK + HTTP endpoint |

### Provider Implementations

#### 1. S3Vector Provider (SDK-based)
- **Access Method**: AWS SDK via boto3 client
- **No HTTP REST API**: S3Vector does NOT expose an HTTP endpoint
- Tests S3 bucket listing functionality via `list_vector_buckets()`
- Validates S3Vectors client accessibility
- Reports bucket count and region information
- **Connectivity Check**: Uses `S3VectorProvider.validate_connectivity()`

**Example Code:**
```python
from src.services.vector_store_s3vector_provider import S3VectorProvider

provider = S3VectorProvider()
result = provider.validate_connectivity()
# Returns: {'accessible': True/False, 'endpoint': 's3vectors.region.amazonaws.com', ...}
```

#### 2. Qdrant Provider (REST API)
- **Access Method**: HTTP REST API
- **Endpoint**: `http://98.93.105.87:6333`
- **Health Check**: `GET /` (root path, NOT `/health`)
- Tests Qdrant endpoint accessibility
- Lists available collections
- Validates service health
- Supports both local and cloud deployments

**Example Code:**
```python
import requests
response = requests.get("http://98.93.105.87:6333/", timeout=5)
# Health check at root, not /health
```

#### 3. LanceDB Provider (REST API)
- **Access Method**: HTTP REST API
- **Endpoint**: `http://18.234.151.118:8000` (updated from 54.175.214.184)
- **Health Check**: `GET /health`
- Tests storage backend accessibility (local or S3)
- Validates database connection
- Lists available tables
- Checks storage type

**Example Code:**
```python
import requests
response = requests.get("http://18.234.151.118:8000/health", timeout=5)
```

#### 4. OpenSearch Provider (Hybrid)
- **Access Method**: AWS SDK for service management + HTTP for queries
- Tests OpenSearch service accessibility
- Lists available domains
- Checks cluster health when domains exist
- Validates endpoint connectivity

## Backend Adapters Module

A new unified `backend_adapters.py` module provides a consistent interface for benchmarking different vector store backends:

```python
from scripts.backend_adapters import get_backend_adapter, validate_backend_connectivity

# Get adapter for any backend
adapter = get_backend_adapter('s3vector')  # Returns S3VectorAdapter (SDK-based)
adapter = get_backend_adapter('qdrant')     # Returns RestAPIAdapter
adapter = get_backend_adapter('lancedb')    # Returns RestAPIAdapter

# Validate connectivity
validation = validate_backend_connectivity('s3vector')
print(f"Accessible: {validation['accessible']}")
print(f"Response time: {validation['response_time_ms']}ms")
```

### Backend Types

The module automatically detects backend types:

```python
BACKEND_TYPES = {
    's3vector': 'sdk',      # AWS SDK-based
    's3_vector': 'sdk',
    'qdrant': 'rest',       # REST API
    'qdrant-efs': 'rest',
    'lancedb': 'rest',      # REST API
    'lancedb-s3': 'rest',
    'lancedb-efs': 'rest'
}
```

### Default Endpoints

```python
DEFAULT_ENDPOINTS = {
    'qdrant': 'http://98.93.105.87:6333',
    'qdrant-efs': 'http://98.93.105.87:6333',
    'lancedb': 'http://18.234.151.118:8000',
    'lancedb-efs': 'http://18.234.151.118:8000',
    'lancedb-s3': 'http://18.234.151.118:8000'
}
```

## API Endpoints

### Single Backend Validation

**Endpoint:** `GET /api/resources/validate-backend/{backend_type}`

**Parameters:**
- `backend_type`: Type of backend (s3_vector, opensearch, qdrant, lancedb)

**Response:**
```json
{
  "success": true,
  "backend_type": "s3_vector",
  "validation": {
    "accessible": true,
    "endpoint": "s3vectors.us-east-1.amazonaws.com",
    "response_time_ms": 245.67,
    "health_status": "healthy",
    "error_message": null,
    "details": {
      "bucket_count": 3,
      "region": "us-east-1",
      "service": "S3 Vectors",
      "access_method": "AWS SDK (boto3)"
    }
  }
}
```

**Example Usage:**
```bash
curl http://localhost:8000/api/resources/validate-backend/s3_vector
```

### Batch Backend Validation

**Endpoint:** `POST /api/resources/validate-backends`

**Request Body:**
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
  "accessible_backends": 2,
  "inaccessible_backends": 2,
  "results": {
    "s3_vector": {
      "accessible": true,
      "endpoint": "s3vectors.us-east-1.amazonaws.com",
      "response_time_ms": 245.67,
      "health_status": "healthy",
      "error_message": null,
      "details": {
        "bucket_count": 3,
        "region": "us-east-1",
        "service": "S3 Vectors"
      }
    },
    "opensearch": {
      "accessible": true,
      "endpoint": "es.us-east-1.amazonaws.com",
      "response_time_ms": 312.45,
      "health_status": "healthy",
      "error_message": null,
      "details": {
        "domain_count": 2,
        "region": "us-east-1",
        "service": "OpenSearch"
      }
    },
    "qdrant": {
      "accessible": true,
      "endpoint": "http://98.93.105.87:6333",
      "response_time_ms": 156.34,
      "health_status": "healthy",
      "error_message": null,
      "details": {
        "url": "http://98.93.105.87:6333",
        "health_check_path": "/",
        "service": "Qdrant"
      }
    },
    "lancedb": {
      "accessible": true,
      "endpoint": "http://18.234.151.118:8000",
      "response_time_ms": 234.56,
      "health_status": "healthy",
      "error_message": null,
      "details": {
        "url": "http://18.234.151.118:8000",
        "health_check_path": "/health",
        "service": "LanceDB"
      }
    }
  }
}
```

**Example Usage:**
```bash
curl -X POST http://localhost:8000/api/resources/validate-backends \
  -H "Content-Type: application/json" \
  -d '{"backend_types": ["s3_vector", "opensearch"]}'
```

## Usage Examples

### Python Script Example

```python
import requests

# Validate single backend
response = requests.get("http://localhost:8000/api/resources/validate-backend/s3_vector")
result = response.json()

if result["success"]:
    print(f"S3 Vector is accessible!")
    print(f"Response time: {result['validation']['response_time_ms']}ms")
else:
    print(f"S3 Vector is NOT accessible: {result['validation']['error_message']}")

# Validate multiple backends
response = requests.post(
    "http://localhost:8000/api/resources/validate-backends",
    json={"backend_types": ["s3_vector", "opensearch", "qdrant", "lancedb"]}
)
result = response.json()

accessible = [
    backend for backend, validation in result["results"].items()
    if validation["accessible"]
]
print(f"Accessible backends: {', '.join(accessible)}")
```

### Using the Test Script

A comprehensive test script is provided at `scripts/test_backend_validation.py`:

```bash
# Run the test script
python scripts/test_backend_validation.py

# Expected output shows validation status for all backends
```

## Use Cases

### 1. Pre-flight Checks

Before starting a data processing pipeline, validate that required backends are accessible:

```python
from src.services.vector_store_provider import VectorStoreProviderFactory, VectorStoreType

# Check S3 Vector availability before pipeline
provider = VectorStoreProviderFactory.create_provider(VectorStoreType.S3_VECTOR)
validation = provider.validate_connectivity()

if not validation["accessible"]:
    raise RuntimeError(f"S3 Vector not accessible: {validation['error_message']}")
```

### 2. Multi-Backend Selection

Select the best available backend based on health status:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/resources/validate-backends",
    json={"backend_types": ["s3_vector", "opensearch"]}
)
results = response.json()["results"]

# Choose the fastest healthy backend
healthy_backends = [
    (name, val) for name, val in results.items()
    if val["accessible"] and val["health_status"] == "healthy"
]

if healthy_backends:
    best_backend = min(healthy_backends, key=lambda x: x[1]["response_time_ms"])
    print(f"Using backend: {best_backend[0]}")
```

### 3. Health Monitoring

Monitor backend health in production:

```python
import time
import requests

while True:
    response = requests.post(
        "http://localhost:8000/api/resources/validate-backends",
        json={"backend_types": ["s3_vector", "opensearch"]}
    )
    
    results = response.json()
    accessible_count = results["accessible_backends"]
    
    if accessible_count < 2:
        print(f"WARNING: Only {accessible_count} backends accessible!")
        # Trigger alert
    
    time.sleep(60)  # Check every minute
```

## Response Format Details

### Health Status Values

- **healthy**: Backend is fully operational with normal response times
- **degraded**: Backend is accessible but experiencing issues (slow response, partial failures)
- **unhealthy**: Backend is not accessible or experiencing critical failures

### Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| `Connection refused` | Service not running | Start the backend service |
| `Validation timed out after 5 seconds` | Network issues or slow backend | Check network connectivity |
| `Invalid response from service` | API incompatibility | Check backend version |
| `Access denied` | Authentication/authorization issues | Verify credentials and permissions |
| `Resource not found` | Missing configuration | Check backend configuration |

## Performance Considerations

- **Timeout**: All validations timeout after 5 seconds to prevent hanging
- **Parallel Validation**: Batch endpoint validates backends in parallel for efficiency
- **Response Time**: Response times include network latency and backend processing
- **Retry Logic**: No automatic retries - implement at application level if needed

## Security Considerations

- Validation endpoints don't expose sensitive credentials
- Error messages are sanitized to prevent information leakage
- All backend connections use existing authentication mechanisms
- No new security boundaries are created

## Limitations and Caveats

1. **Validation is point-in-time**: Backend status may change after validation
2. **No guaranteed availability**: Validation success doesn't guarantee subsequent operations will succeed
3. **Network dependency**: REST API validation requires network access to backends
4. **AWS credentials required**: S3Vector validation requires valid AWS credentials configured
5. **Timeout constraints**: 5-second timeout may be too short for some deployments
6. **Optional dependencies**: Some providers require additional packages (qdrant-client, lancedb, opensearch-py)
7. **S3Vector HTTP confusion**: S3Vector does NOT expose HTTP REST API - use AWS SDK only
8. **Qdrant health check path**: Must use `/` (root), not `/health`
9. **LanceDB endpoint changed**: Old IP (54.175.214.184) is invalid, use 18.234.151.118

## Troubleshooting

### Backend Shows as Unhealthy but Should be Available

1. **For S3Vector (SDK-based)**:
   - Verify AWS credentials: `aws sts get-caller-identity`
   - Check AWS region configuration
   - Test S3Vectors service: `aws s3vectors list-vector-buckets`
   - Do NOT attempt HTTP requests to S3Vector

2. **For Qdrant (REST API)**:
   - Check network connectivity: `curl http://98.93.105.87:6333/`
   - Verify health check at root `/`, not `/health`
   - Check firewall rules for port 6333
   - Verify Qdrant service is running

3. **For LanceDB (REST API)**:
   - Check network connectivity: `curl http://18.234.151.118:8000/health`
   - Use correct endpoint IP: 18.234.151.118 (not old IP)
   - Check firewall rules for port 8000
   - Verify LanceDB API service is running

4. **General checks**:
   - Verify credentials are configured correctly
   - Check firewall rules and security groups
   - Verify backend service is running: `systemctl status <service>`
   - Check logs for detailed error messages

### Validation Timing Out

1. **For S3Vector**:
   - Check AWS API response times
   - Verify AWS credentials aren't rate-limited
   - Check IAM permissions for S3Vectors service

2. **For REST APIs (Qdrant/LanceDB)**:
   - Check network latency: `traceroute <backend-endpoint>`
   - Verify backend isn't overloaded with `curl` tests
   - Check for DNS resolution issues
   - Increase timeout if needed (modify source code)

### Getting 404 Errors

1. **S3Vector returning 404**: This is expected! S3Vector does NOT have HTTP REST API
   - Use AWS SDK methods instead
   - Check that code uses `S3VectorProvider`, not HTTP requests

2. **Qdrant returning 404**: Wrong health check path
   - Use `/` (root) for health check, not `/health`
   - Update endpoint configuration

3. **LanceDB returning 404**: Wrong endpoint or path
   - Verify using `http://18.234.151.118:8000`
   - Health check should be at `/health`

### Inconsistent Results

1. Backend may be intermittently available
2. Check backend health logs
3. Consider implementing retry logic
4. Monitor backend resource utilization

## Future Enhancements

Potential improvements for future releases:

1. **Configurable timeouts** - Allow per-backend timeout configuration
2. **Retry logic** - Automatic retries with exponential backoff
3. **Historical tracking** - Store validation history for trend analysis
4. **Alerting integration** - Direct integration with monitoring systems
5. **Custom health checks** - Allow custom validation logic per provider
6. **Parallel validation limits** - Configurable concurrency for batch validation

## Related Documentation

- [Vector Store Provider Architecture](./ARCHITECTURE.md)
- [Backend Configuration Guide](./DEPLOYMENT_GUIDE.md)
- [Troubleshooting Guide](./troubleshooting-guide.md)
- [Backend Adapters Module](../scripts/backend_adapters.py)
- [Benchmark Scripts](../scripts/benchmark_backend.py)

## Support

For issues or questions about backend connectivity validation:

1. Check this documentation
2. Review error messages in logs
3. Run the test script: `python scripts/test_backend_validation.py`
4. Check backend-specific documentation
5. Open an issue on GitHub with validation results