---
inclusion: always
---

# Python and Boto3 Implementation Patterns

## Boto3 Client Configuration

### Standard Client Setup
```python
import boto3
from botocore.config import Config

# Configure clients with retry and timeout settings
config = Config(
    retries={'max_attempts': 3, 'mode': 'adaptive'},
    read_timeout=60,
    connect_timeout=10,
    max_pool_connections=50
)

# S3 Vectors client
s3vectors_client = boto3.client('s3vectors', config=config)

# Bedrock Runtime client
bedrock_client = boto3.client('bedrock-runtime', config=config)
```

### Session Management
```python
# Use sessions for consistent configuration
session = boto3.Session(region_name='us-west-2')
s3vectors = session.client('s3vectors', config=config)
```

## Error Handling Patterns

### Comprehensive Exception Handling
```python
from botocore.exceptions import ClientError, BotoCoreError
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Implement exponential backoff for AWS API calls"""
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['Throttling', 'ServiceUnavailable', 'InternalError']:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(delay)
                    continue
            raise
        except BotoCoreError as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
            raise
```

### Custom Exception Classes
```python
class VectorEmbeddingError(Exception):
    """Base exception for vector embedding operations"""
    pass

class ModelAccessError(VectorEmbeddingError):
    """Raised when model access is denied"""
    pass

class VectorStorageError(VectorEmbeddingError):
    """Raised when vector storage operations fail"""
    pass

class AsyncProcessingError(VectorEmbeddingError):
    """Raised when async processing fails"""
    pass
```

## Async Processing Patterns

### TwelveLabs Async Job Management
```python
import asyncio
import json
from typing import Dict, Any, Optional

class AsyncJobManager:
    def __init__(self, bedrock_client, s3_client):
        self.bedrock_client = bedrock_client
        self.s3_client = s3_client
    
    async def start_video_processing(self, video_uri: str, output_bucket: str) -> str:
        """Start async video processing job"""
        request_body = {
            "modelId": "twelvelabs.marengo-embed-2-7-v1:0",
            "modelInput": {
                "inputType": "video",
                "mediaSource": {
                    "s3Location": {
                        "uri": video_uri,
                        "bucketOwner": "your-account-id"
                    }
                }
            },
            "outputDataConfig": {
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://{output_bucket}/embeddings/"
                }
            }
        }
        
        response = self.bedrock_client.start_async_invoke(**request_body)
        return response['invocationArn']
    
    async def poll_job_status(self, job_arn: str, poll_interval: int = 30) -> Dict[str, Any]:
        """Poll job status until completion"""
        while True:
            response = self.bedrock_client.get_async_invoke(invocationArn=job_arn)
            status = response['status']
            
            if status in ['Completed', 'Failed']:
                return response
            
            await asyncio.sleep(poll_interval)
```

## Data Processing Patterns

### Batch Processing Implementation
```python
from typing import List, Iterator, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

def batch_items(items: List[T], batch_size: int) -> Iterator[List[T]]:
    """Split items into batches of specified size"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

@dataclass
class EmbeddingBatch:
    texts: List[str]
    metadata: List[Dict[str, Any]]
    batch_id: str

class BatchEmbeddingProcessor:
    def __init__(self, bedrock_client, batch_size: int = 100):
        self.bedrock_client = bedrock_client
        self.batch_size = batch_size
    
    def process_text_batch(self, texts: List[str]) -> List[List[float]]:
        """Process batch of texts for embeddings"""
        embeddings = []
        
        for batch in batch_items(texts, self.batch_size):
            batch_embeddings = self._generate_batch_embeddings(batch)
            embeddings.extend(batch_embeddings)
        
        return embeddings
```

## Vector Storage Patterns

### S3 Vectors Operations
```python
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

class VectorStorageManager:
    def __init__(self, s3vectors_client):
        self.client = s3vectors_client
    
    def create_vector_bucket(self, bucket_name: str, region: str) -> Dict[str, Any]:
        """Create S3 vector bucket with proper configuration"""
        try:
            response = self.client.create_vector_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyExists':
                # Handle existing bucket gracefully
                return {'BucketName': bucket_name, 'Status': 'AlreadyExists'}
            raise VectorStorageError(f"Failed to create bucket: {e}")
    
    def put_vectors_batch(self, index_arn: str, vectors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store multiple vectors with metadata"""
        try:
            response = self.client.put_vectors(
                IndexArn=index_arn,
                Vectors=vectors_data
            )
            return response
        except ClientError as e:
            raise VectorStorageError(f"Failed to store vectors: {e}")
    
    def query_similar_vectors(self, 
                            index_arn: str, 
                            query_vector: List[float], 
                            top_k: int = 10,
                            metadata_filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Query for similar vectors with optional filtering"""
        query_params = {
            'IndexArn': index_arn,
            'QueryVector': query_vector,
            'TopK': top_k
        }
        
        if metadata_filters:
            query_params['MetadataFilter'] = metadata_filters
        
        try:
            response = self.client.query_vectors(**query_params)
            return response
        except ClientError as e:
            raise VectorStorageError(f"Failed to query vectors: {e}")
```

## Configuration Management

### Environment-Based Configuration
```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AWSConfig:
    region: str
    s3_vectors_bucket: str
    bedrock_models: Dict[str, str]
    opensearch_domain: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> 'AWSConfig':
        return cls(
            region=os.getenv('AWS_REGION', 'us-west-2'),
            s3_vectors_bucket=os.getenv('S3_VECTORS_BUCKET'),
            bedrock_models={
                'text_embedding': os.getenv('BEDROCK_TEXT_MODEL', 'amazon.titan-embed-text-v2:0'),
                'multimodal_embedding': os.getenv('BEDROCK_MM_MODEL', 'amazon.titan-embed-image-v1'),
                'video_embedding': os.getenv('TWELVELABS_MODEL', 'twelvelabs.marengo-embed-2-7-v1:0')
            },
            opensearch_domain=os.getenv('OPENSEARCH_DOMAIN')
        )
```

## Logging and Monitoring

### Structured Logging Setup
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_operation(self, operation: str, **kwargs):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            **kwargs
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_error(self, operation: str, error: Exception, **kwargs):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'error': str(error),
            'error_type': type(error).__name__,
            **kwargs
        }
        self.logger.error(json.dumps(log_entry))
```

## Testing Patterns

### Mocking AWS Services
```python
import pytest
from moto import mock_s3
from unittest.mock import Mock, patch

@pytest.fixture
def mock_bedrock_client():
    with patch('boto3.client') as mock_client:
        bedrock_mock = Mock()
        bedrock_mock.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'embedding': [0.1, 0.2, 0.3] * 341  # 1024 dimensions
            }).encode())
        }
        mock_client.return_value = bedrock_mock
        yield bedrock_mock

@mock_s3
def test_vector_storage_operations():
    # Test implementation with mocked AWS services
    pass
```