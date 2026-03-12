# LanceDB API Wrapper

Production-ready REST API wrapper for LanceDB vector database operations, designed for deployment on AWS ECS with support for both S3 and local filesystem storage.

## Features

- **RESTful API**: Complete REST API for LanceDB operations
- **Dual Storage**: Supports both S3 and local filesystem backends
- **Vector Search**: Similarity search with configurable distance metrics
- **Health Checks**: Built-in health endpoints for ECS orchestration
- **FastAPI**: Modern, high-performance async API framework
- **Production Ready**: Comprehensive error handling and logging
- **ECS Optimized**: Health checks and graceful shutdown support

## Quick Start

### Building the Docker Image

```bash
cd docker/lancedb-api
docker build -t lancedb/lancedb-api:latest .
```

### Running Locally with Local Storage

```bash
docker run -p 8000:8000 \
  -v $(pwd)/data:/data \
  -e STORAGE_TYPE=local \
  -e DATA_PATH=/data \
  lancedb/lancedb-api:latest
```

### Running with S3 Storage

```bash
docker run -p 8000:8000 \
  -e STORAGE_TYPE=s3 \
  -e S3_BUCKET=my-lancedb-bucket \
  -e AWS_REGION=us-east-1 \
  -e AWS_ACCESS_KEY_ID=your_key \
  -e AWS_SECRET_ACCESS_KEY=your_secret \
  lancedb/lancedb-api:latest
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  lancedb-api:
    image: lancedb/lancedb-api:latest
    ports:
      - "8000:8000"
    environment:
      - STORAGE_TYPE=s3
      - S3_BUCKET=my-lancedb-bucket
      - AWS_REGION=us-east-1
    volumes:
      - ./data:/data  # Only needed for local storage
```

## Environment Variables

### Required Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `STORAGE_TYPE` | Storage backend type | `local` | `s3` or `local` |

### S3 Storage Configuration

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `S3_BUCKET` | S3 bucket name for LanceDB data | Yes (for S3) | `my-lancedb-bucket` |
| `AWS_REGION` | AWS region | No | `us-east-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | No* | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | No* | `wJalrXUtnFEMI/K7MDENG/...` |

*Not required if using IAM roles (recommended for ECS)

### Local Storage Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATA_PATH` | Local data directory path | `/data` | `/app/lancedb-data` |

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service health status, storage type, and table count.

**Response:**
```json
{
  "status": "healthy",
  "storage_type": "s3",
  "storage_uri": "s3://my-bucket/lancedb",
  "tables_count": 5
}
```

### List Tables

```bash
GET /tables
```

Returns list of all LanceDB tables.

**Response:**
```json
["embeddings", "vectors", "documents"]
```

### Get Table Info

```bash
GET /tables/{table_name}
```

Returns schema and metadata for a specific table.

**Response:**
```json
{
  "name": "embeddings",
  "table_schema": {
    "fields": [
      {"name": "id", "type": "int64"},
      {"name": "vector", "type": "fixed_size_list<item: float>[384]"},
      {"name": "text", "type": "string"}
    ]
  }
}
```

### Create/Update Index

```bash
POST /index
Content-Type: application/json

{
  "table_name": "my_vectors",
  "mode": "overwrite",
  "data": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, ...],
      "metadata": "example"
    }
  ]
}
```

**Modes:**
- `create`: Create new table (fails if exists)
- `overwrite`: Replace existing table
- `append`: Add to existing table

**Response:**
```json
{
  "status": "success",
  "operation": "overwritten",
  "table_name": "my_vectors",
  "records_processed": 100
}
```

### Vector Search

```bash
POST /search
Content-Type: application/json

{
  "table_name": "my_vectors",
  "query_vector": [0.1, 0.2, 0.3, ...],
  "limit": 10,
  "metric": "cosine",
  "filter": "metadata = 'example'"
}
```

**Distance Metrics:**
- `cosine`: Cosine similarity (default)
- `l2`: Euclidean distance
- `dot`: Dot product

**Response:**
```json
{
  "results": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, ...],
      "metadata": "example",
      "_distance": 0.05
    }
  ],
  "count": 1
}
```

### Delete Table

```bash
DELETE /tables/{table_name}
```

**Response:**
```json
{
  "status": "success",
  "message": "Table 'my_vectors' deleted",
  "table_name": "my_vectors"
}
```

## Usage Examples

### Python Client

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Create index with vectors
data = {
    "table_name": "documents",
    "mode": "create",
    "data": [
        {
            "id": 1,
            "vector": [0.1] * 384,  # 384-dim vector
            "text": "Example document"
        }
    ]
}
response = requests.post(f"{BASE_URL}/index", json=data)
print(response.json())

# Search for similar vectors
search_query = {
    "table_name": "documents",
    "query_vector": [0.15] * 384,
    "limit": 5
}
response = requests.post(f"{BASE_URL}/search", json=search_query)
print(response.json())
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# List tables
curl http://localhost:8000/tables

# Create index
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "test_vectors",
    "mode": "create",
    "data": [
      {"id": 1, "vector": [0.1, 0.2, 0.3], "label": "A"}
    ]
  }'

# Search
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "test_vectors",
    "query_vector": [0.1, 0.2, 0.3],
    "limit": 5
  }'
```

## Deployment on AWS ECS

### Task Definition Configuration

```json
{
  "family": "lancedb-api",
  "containerDefinitions": [
    {
      "name": "lancedb-api",
      "image": "lancedb/lancedb-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "STORAGE_TYPE",
          "value": "s3"
        },
        {
          "name": "S3_BUCKET",
          "value": "my-lancedb-bucket"
        },
        {
          "name": "AWS_REGION",
          "value": "us-east-1"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 40
      }
    }
  ]
}
```

### IAM Permissions for S3

The ECS task role needs these S3 permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-lancedb-bucket/*",
        "arn:aws:s3:::my-lancedb-bucket"
      ]
    }
  ]
}
```

## Performance Considerations

- **Vector Dimensions**: LanceDB efficiently handles high-dimensional vectors (up to thousands of dimensions)
- **Batch Operations**: Use batch inserts for better performance (100-1000 records per request)
- **S3 Latency**: First query may be slower due to S3 metadata loading; subsequent queries are cached
- **Memory**: Allocate sufficient memory for your vector datasets (recommend 2GB+ for production)

## Monitoring

### Health Check Endpoint

The `/health` endpoint is designed for ECS health checks and monitoring:

```bash
# Check if service is healthy
curl http://localhost:8000/health

# Expected response when healthy
{
  "status": "healthy",
  "storage_type": "s3",
  "storage_uri": "s3://bucket/lancedb",
  "tables_count": 10
}
```

### Logging

All operations are logged with timestamps and severity levels:

```
2024-01-15 10:30:00 - app - INFO - Using S3 storage: s3://my-bucket/lancedb
2024-01-15 10:30:01 - app - INFO - LanceDB connection established
2024-01-15 10:30:05 - app - INFO - Table 'vectors' created with 1000 records
2024-01-15 10:30:10 - app - INFO - Search on 'vectors' returned 10 results
```

## Troubleshooting

### Connection Issues

**Problem**: "Database connection not initialized"
- **Solution**: Check storage configuration and AWS credentials

**Problem**: "S3_BUCKET environment variable must be set"
- **Solution**: Set `S3_BUCKET` when using `STORAGE_TYPE=s3`

### Search Issues

**Problem**: "Table not found"
- **Solution**: Ensure table exists using `GET /tables`

**Problem**: Vector dimension mismatch
- **Solution**: Ensure all vectors have consistent dimensions

### Performance Issues

**Problem**: Slow search queries
- **Solution**: Consider creating indexes or using smaller result limits

## Development

### Building from Source

```bash
git clone https://github.com/yourusername/s3vector
cd s3vector/docker/lancedb-api
docker build -t lancedb/lancedb-api:dev .
```

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt pytest httpx

# Run tests
pytest tests/
```

### Interactive API Documentation

Once the service is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Security Considerations

1. **IAM Roles**: Use ECS task roles instead of hardcoded credentials
2. **Network Security**: Deploy in private subnets with security groups
3. **Data Encryption**: Use S3 encryption at rest
4. **API Authentication**: Add API gateway or authentication layer for production
5. **Input Validation**: All inputs are validated using Pydantic models

## License

This project is part of the S3Vector system. See parent repository for license details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/s3vector/issues
- Documentation: See main project README

## Version History

- **1.0.0** (2024-01): Initial release with S3 and local storage support