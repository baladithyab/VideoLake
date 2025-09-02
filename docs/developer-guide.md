# S3Vector Developer Guide

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Project Architecture](#project-architecture)
3. [Core Components](#core-components)
4. [Development Workflow](#development-workflow)
5. [Testing Strategy](#testing-strategy)
6. [Contributing Guidelines](#contributing-guidelines)
7. [Code Quality Standards](#code-quality-standards)
8. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

## Development Environment Setup

### Prerequisites for Development

- **Python 3.9+**: Latest stable version recommended
- **Git**: Version control and workflow management
- **AWS CLI v2**: For AWS service testing and deployment
- **Docker**: For containerized development and testing
- **VS Code/PyCharm**: Recommended IDEs with Python extensions

### Development Installation

```bash
# Clone and setup development environment
git clone <repository-url>
cd S3Vector

# Create development virtual environment
python -m venv venv-dev
source venv-dev/bin/activate  # Linux/macOS
# venv-dev\Scripts\activate     # Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Development Dependencies

```txt
# requirements-dev.txt
# Code formatting and linting
black>=23.0.0
flake8>=6.0.0
isort>=5.12.0
mypy>=1.5.0
pre-commit>=3.0.0

# Testing and coverage
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
coverage>=7.3.0

# Documentation
sphinx>=7.1.0
sphinx-rtd-theme>=1.3.0
myst-parser>=2.0.0

# Development tools
ipython>=8.15.0
jupyter>=1.0.0
pdbr>=0.8.0
```

### IDE Configuration

#### VS Code Settings (.vscode/settings.json)
```json
{
    "python.defaultInterpreterPath": "./venv-dev/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

#### Pre-commit Hooks (.pre-commit-config.yaml)
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.9

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### Environment Configuration for Development

```bash
# .env.development
# Development-specific settings
USE_REAL_AWS=false
LOG_LEVEL=DEBUG
ENABLE_DEBUG_MODE=true
STRUCTURED_LOGGING=true

# Cost protection
MAX_DAILY_COST_USD=1.00
ENABLE_COST_TRACKING=true

# Fast iteration settings
BATCH_SIZE_TEXT=10
BATCH_SIZE_VIDEO=2
POLL_INTERVAL=5

# Mock services for development
USE_MOCK_BEDROCK=true
USE_MOCK_S3VECTORS=true
USE_MOCK_TWELVELABS=true
```

## Project Architecture

### High-Level Architecture

```
S3Vector Architecture
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                       │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Embedding     │  │   Video         │  │   Search        │ │
│  │   Services      │  │   Processing    │  │   Engine        │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Integration Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   S3 Vector     │  │   Bedrock       │  │   TwelveLabs    │ │
│  │   Storage       │  │   Integration   │  │   Integration   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                    │
│           AWS SDK │ Error Handling │ Configuration        │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
src/
├── __init__.py                 # Package initialization
├── config.py                   # Configuration management
├── core.py                     # Core application logic
├── exceptions.py               # Custom exceptions
│
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── s3_vector_storage.py         # S3 Vector operations
│   ├── bedrock_embedding.py         # Bedrock embedding service
│   ├── twelvelabs_video_processing.py   # Video processing
│   ├── embedding_storage_integration.py # Text embedding workflow
│   ├── video_embedding_storage.py      # Video embedding workflow
│   ├── similarity_search_engine.py     # Multi-modal search
│   └── opensearch_integration.py       # OpenSearch service
│
├── models/                     # Data models and schemas
│   ├── __init__.py
│   ├── embedding_models.py          # Embedding data structures
│   ├── search_models.py             # Search request/response models
│   └── storage_models.py            # Storage operation models
│
└── utils/                      # Utility modules
    ├── __init__.py
    ├── aws_clients.py              # AWS client factory
    ├── error_handling.py           # Error handling utilities
    ├── logging_config.py           # Logging configuration
    ├── helpers.py                  # Common helper functions
    └── resource_registry.py       # Resource management
```

### Design Patterns and Principles

#### 1. Service Layer Pattern
```python
# Each AWS service has a dedicated service class
class BedrockEmbeddingService:
    """Encapsulates all Bedrock embedding operations"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.client = self._create_bedrock_client()
    
    def generate_text_embedding(self, text: str, model_id: str) -> EmbeddingResult:
        """Single responsibility: generate embeddings"""
        pass
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[EmbeddingResult]:
        """Single responsibility: batch processing"""
        pass
```

#### 2. Factory Pattern for AWS Clients
```python
# utils/aws_clients.py
class AWSClientFactory:
    """Factory for creating configured AWS clients"""
    
    @staticmethod
    def create_bedrock_client(region: str = None) -> Any:
        """Create Bedrock client with retry configuration"""
        return boto3.client(
            'bedrock-runtime',
            region_name=region or Config().aws_region,
            config=Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                timeout=60
            )
        )
```

#### 3. Integration Layer Pattern
```python
# Higher-level integration services combine multiple lower-level services
class EmbeddingStorageIntegration:
    """Integrates embedding generation with vector storage"""
    
    def __init__(self):
        self.bedrock_service = BedrockEmbeddingService()
        self.storage_manager = S3VectorStorageManager()
    
    def store_text_embedding(self, text: str, index_arn: str) -> StorageResult:
        """End-to-end workflow: generate → store → return result"""
        embedding = self.bedrock_service.generate_text_embedding(text)
        storage_result = self.storage_manager.put_vectors_batch(index_arn, [embedding])
        return StorageResult(embedding=embedding, storage=storage_result)
```

#### 4. Error Handling Strategy
```python
# Decorator-based error handling with retries
@with_error_handling("bedrock_embedding", retry_config=RetryConfig(max_attempts=3))
def generate_embedding(self, text: str) -> EmbeddingResult:
    """Automatic retry logic for transient failures"""
    pass
```

## Core Components

### 1. Configuration Management (src/config.py)

```python
from pydantic import BaseSettings, Field
from typing import Optional, List

class Config(BaseSettings):
    """Central configuration management with validation"""
    
    # AWS Configuration
    aws_profile: str = Field(default="default", env="AWS_PROFILE")
    aws_region: str = Field(default="us-east-1", env="AWS_REGION")
    s3_vectors_bucket: str = Field(..., env="S3_VECTORS_BUCKET")
    
    # Model Configuration
    bedrock_text_model: str = Field(
        default="amazon.titan-embed-text-v2:0", 
        env="BEDROCK_TEXT_MODEL"
    )
    
    # Processing Configuration
    batch_size_text: int = Field(default=100, env="BATCH_SIZE_TEXT")
    batch_size_video: int = Field(default=10, env="BATCH_SIZE_VIDEO")
    
    # Development Settings
    use_real_aws: bool = Field(default=False, env="USE_REAL_AWS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 2. Data Models (src/models/)

```python
# src/models/embedding_models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class EmbeddingResult(BaseModel):
    """Standard embedding result structure"""
    embedding: List[float]
    model_id: str
    input_text: str
    processing_time_ms: float
    token_count: Optional[int] = None
    cost_estimate_usd: Optional[float] = None

class VectorData(BaseModel):
    """S3 Vector storage format"""
    key: str
    data: Dict[str, List[float]]  # {"float32": [0.1, 0.2, ...]}
    metadata: Dict[str, Any]

class SearchResult(BaseModel):
    """Search result with metadata"""
    vector_key: str
    similarity_score: float
    metadata: Dict[str, Any]
    temporal_info: Optional[Dict[str, float]] = None  # For video segments
```

### 3. Error Handling (src/utils/error_handling.py)

```python
import functools
import time
import random
import logging
from typing import Any, Callable, Optional

class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

def with_error_handling(
    service_name: str, 
    retry_config: Optional[RetryConfig] = None
) -> Callable:
    """Decorator for automatic error handling and retries"""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            config = retry_config or RetryConfig()
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success if it was a retry
                    if attempt > 0:
                        logging.info(
                            f"{service_name}.{func.__name__} succeeded on attempt {attempt + 1}"
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts - 1:
                        delay = min(
                            config.base_delay * (config.exponential_base ** attempt),
                            config.max_delay
                        )
                        
                        if config.jitter:
                            delay *= (0.5 + random.random() * 0.5)
                        
                        logging.warning(
                            f"{service_name}.{func.__name__} failed attempt {attempt + 1}: {e}. "
                            f"Retrying in {delay:.2f} seconds..."
                        )
                        
                        time.sleep(delay)
                    else:
                        logging.error(
                            f"{service_name}.{func.__name__} failed after {config.max_attempts} attempts: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
```

## Development Workflow

### 1. Feature Development Process

```bash
# Create feature branch
git checkout -b feature/new-embedding-model

# Make changes with TDD approach
# 1. Write test first
# 2. Implement feature
# 3. Refactor

# Run tests continuously during development
pytest tests/test_new_feature.py -v --watch

# Check code quality
pre-commit run --all-files

# Commit changes
git add .
git commit -m "feat: add support for new embedding model"
```

### 2. Testing During Development

```bash
# Run specific test categories
pytest tests/test_s3_vector_storage.py -v              # Unit tests
pytest tests/integration/ -v                          # Integration tests
pytest tests/test_end_to_end.py -v                   # End-to-end tests

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test with debugging
pytest tests/test_specific.py::test_function -v -s --pdb

# Performance testing
pytest tests/performance/ -v --benchmark-only
```

### 3. Local Development with Mocks

```python
# tests/conftest.py - Shared test fixtures
import pytest
from unittest.mock import Mock, patch
from src.services.bedrock_embedding import BedrockEmbeddingService

@pytest.fixture
def mock_bedrock_client():
    """Mock Bedrock client for local development"""
    mock_client = Mock()
    mock_client.invoke_model.return_value = {
        'body': Mock(read=lambda: '{"embedding": [0.1, 0.2, 0.3]}')
    }
    return mock_client

@pytest.fixture
def embedding_service_with_mock(mock_bedrock_client):
    """Embedding service with mocked AWS calls"""
    with patch('src.utils.aws_clients.AWSClientFactory.create_bedrock_client', 
               return_value=mock_bedrock_client):
        return BedrockEmbeddingService()

# tests/test_development.py - Development tests
def test_embedding_generation_locally(embedding_service_with_mock):
    """Test embedding generation without AWS calls"""
    result = embedding_service_with_mock.generate_text_embedding(
        text="test content",
        model_id="amazon.titan-embed-text-v2:0"
    )
    
    assert result is not None
    assert len(result.embedding) > 0
```

## Testing Strategy

### 1. Test Pyramid Structure

```
                    ┌─────────────────┐
                    │   E2E Tests     │ <- Few, slow, high-confidence
                    │   (5-10 tests)  │
                ┌───┴─────────────────┴───┐
                │  Integration Tests      │ <- Some, medium speed
                │    (20-30 tests)        │
            ┌───┴─────────────────────────┴───┐
            │        Unit Tests               │ <- Many, fast, focused
            │       (100+ tests)              │
            └─────────────────────────────────┘
```

### 2. Unit Test Examples

```python
# tests/test_s3_vector_storage.py
import pytest
from unittest.mock import Mock, patch
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError

class TestS3VectorStorageManager:
    """Unit tests for S3 Vector storage operations"""
    
    @pytest.fixture
    def storage_manager(self):
        return S3VectorStorageManager()
    
    @patch('src.utils.aws_clients.AWSClientFactory.create_s3vectors_client')
    def test_create_vector_bucket_success(self, mock_client_factory, storage_manager):
        """Test successful bucket creation"""
        # Arrange
        mock_client = Mock()
        mock_client.create_vector_bucket.return_value = {
            'bucket_arn': 'arn:aws:s3vectors:us-east-1:123456789012:bucket/test-bucket'
        }
        mock_client_factory.return_value = mock_client
        
        # Act
        result = storage_manager.create_vector_bucket('test-bucket')
        
        # Assert
        assert result['bucket_arn'] is not None
        mock_client.create_vector_bucket.assert_called_once()
    
    @patch('src.utils.aws_clients.AWSClientFactory.create_s3vectors_client')
    def test_create_vector_bucket_failure(self, mock_client_factory, storage_manager):
        """Test bucket creation error handling"""
        # Arrange
        mock_client = Mock()
        mock_client.create_vector_bucket.side_effect = Exception("AWS Error")
        mock_client_factory.return_value = mock_client
        
        # Act & Assert
        with pytest.raises(VectorStorageError):
            storage_manager.create_vector_bucket('test-bucket')
    
    def test_vector_data_validation(self, storage_manager):
        """Test vector data format validation"""
        # Invalid data should raise validation error
        invalid_data = [
            {
                "key": "test",
                "data": {"int32": [1, 2, 3]},  # Wrong data type
                "metadata": {}
            }
        ]
        
        with pytest.raises(ValueError, match="Vector data must be float32"):
            storage_manager._validate_vector_data(invalid_data)
```

### 3. Integration Test Examples

```python
# tests/test_integration_embedding_workflow.py
import pytest
from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.config import Config

@pytest.mark.integration
class TestEmbeddingWorkflowIntegration:
    """Integration tests for complete embedding workflows"""
    
    @pytest.fixture
    def integration_service(self):
        """Integration service configured for testing"""
        config = Config()
        config.use_real_aws = False  # Use mocks for integration tests
        return EmbeddingStorageIntegration(config)
    
    def test_complete_text_embedding_workflow(self, integration_service):
        """Test end-to-end text embedding and storage"""
        # This test uses mocks but tests service integration
        result = integration_service.store_text_embedding(
            text="Integration test content",
            index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/test",
            metadata={"test": "true"}
        )
        
        assert result.vector_key is not None
        assert result.embedding_result is not None
        assert result.storage_result is not None
    
    @pytest.mark.slow
    def test_batch_processing_performance(self, integration_service):
        """Test batch processing performance characteristics"""
        import time
        
        texts = [f"Test content {i}" for i in range(50)]
        
        start_time = time.time()
        results = integration_service.batch_store_embeddings(texts)
        processing_time = time.time() - start_time
        
        assert len(results) == 50
        assert processing_time < 30.0  # Should complete within 30 seconds
        
        # Check for proper batching behavior
        assert all(r.batch_size <= integration_service.config.batch_size_text 
                  for r in results)
```

### 4. End-to-End Test Examples

```python
# tests/test_e2e_real_aws.py
import pytest
import os
from src.services.video_embedding_storage import VideoEmbeddingStorage
from src.config import Config

@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv('RUN_E2E_TESTS') != 'true',
    reason="E2E tests require RUN_E2E_TESTS=true"
)
class TestE2ERealAWS:
    """End-to-end tests with real AWS services"""
    
    @pytest.fixture(scope="class")
    def real_aws_config(self):
        """Configuration for real AWS testing"""
        config = Config()
        config.use_real_aws = True
        config.s3_vectors_bucket = f"e2e-test-{int(time.time())}"
        return config
    
    @pytest.fixture(scope="class") 
    def video_service(self, real_aws_config):
        """Video service configured for real AWS"""
        return VideoEmbeddingStorage(real_aws_config)
    
    def test_complete_video_pipeline(self, video_service):
        """Test complete video processing pipeline with real AWS"""
        # Download test video
        video_path = self._download_test_video()
        
        try:
            # Create infrastructure
            bucket_response = video_service.storage_manager.create_vector_bucket(
                video_service.config.s3_vectors_bucket
            )
            
            index_arn = video_service.storage_manager.create_vector_index(
                bucket_name=video_service.config.s3_vectors_bucket,
                index_name="e2e-test-index",
                dimensions=1024
            )
            
            # Process video
            result = video_service.process_and_store_video_embeddings(
                video_file_path=video_path,
                index_arn=index_arn,
                metadata={"test": "e2e", "video_type": "test_clip"},
                segment_duration_sec=5.0
            )
            
            # Verify results
            assert result.segments_processed > 0
            assert result.cost_estimate < 1.0  # Reasonable cost limit
            
            # Test search functionality
            search_results = video_service.search_video_content(
                query_text="test video content",
                index_arn=index_arn,
                top_k=3
            )
            
            assert len(search_results.results) > 0
            assert search_results.results[0].similarity_score > 0
            
        finally:
            # Cleanup
            self._cleanup_test_resources(video_service.config.s3_vectors_bucket)
    
    def _download_test_video(self) -> str:
        """Download small test video for E2E testing"""
        # Implementation to download public domain test video
        pass
    
    def _cleanup_test_resources(self, bucket_name: str):
        """Clean up AWS resources after testing"""
        # Implementation to clean up test resources
        pass
```

## Code Quality Standards

### 1. Code Style and Formatting

```python
# pyproject.toml - Black configuration
[tool.black]
line-length = 88
target-version = ['py39']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

# .flake8 - Flake8 configuration
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = .git,__pycache__,docs/source/conf.py,old,build,dist
max-complexity = 10
```

### 2. Documentation Standards

```python
def process_video_embeddings(
    self,
    video_file_path: str,
    index_arn: str,
    metadata: Dict[str, Any],
    segment_duration_sec: float = 5.0,
    embedding_options: Optional[List[str]] = None
) -> VideoProcessingResult:
    """
    Process video file and store embeddings in S3 Vector index.
    
    Args:
        video_file_path: Path to video file to process
        index_arn: ARN of S3 Vector index for storage
        metadata: Additional metadata to store with embeddings
        segment_duration_sec: Duration of each video segment in seconds.
            Must be between 2.0 and 10.0 seconds.
        embedding_options: List of embedding types to generate.
            Options: ['visual-text', 'visual-image', 'audio']
            Defaults to ['visual-text'] if not specified.
    
    Returns:
        VideoProcessingResult containing:
            - segments_processed: Number of video segments processed
            - total_duration_sec: Total video duration
            - cost_estimate: Estimated processing cost in USD
            - processing_time_sec: Total processing time
    
    Raises:
        ValidationError: If video file format is unsupported or parameters invalid
        AsyncProcessingError: If TwelveLabs processing fails
        VectorStorageError: If S3 Vector storage operations fail
    
    Example:
        >>> video_service = VideoEmbeddingStorage()
        >>> result = video_service.process_video_embeddings(
        ...     video_file_path="sample.mp4",
        ...     index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/videos",
        ...     metadata={"title": "Sample Video", "category": "demo"},
        ...     segment_duration_sec=5.0
        ... )
        >>> print(f"Processed {result.segments_processed} segments")
    """
```

### 3. Type Annotations

```python
from typing import List, Dict, Any, Optional, Union, Tuple
from pydantic import BaseModel

class SearchService:
    """Type-annotated service class example"""
    
    def __init__(self, config: Optional[Config] = None) -> None:
        self.config: Config = config or Config()
        self.client: Any = self._create_client()
    
    def search_vectors(
        self, 
        query_vector: List[float], 
        index_arn: str,
        top_k: int = 10,
        metadata_filters: Optional[Dict[str, List[str]]] = None
    ) -> Tuple[List[SearchResult], float]:
        """
        Type-annotated method with clear return type
        
        Returns:
            Tuple of (search_results, processing_time_seconds)
        """
        start_time = time.time()
        
        results: List[SearchResult] = self._perform_search(
            query_vector, index_arn, top_k, metadata_filters or {}
        )
        
        processing_time: float = time.time() - start_time
        
        return results, processing_time
```

## Debugging and Troubleshooting

### 1. Debug Configuration

```python
# Debug mode configuration
import logging
import os
from src.utils.logging_config import setup_logging

if os.getenv('ENABLE_DEBUG_MODE', 'false').lower() == 'true':
    setup_logging(level="DEBUG", structured=True)
    
    # Enable AWS SDK debugging
    boto3.set_stream_logger('boto3', logging.DEBUG)
    boto3.set_stream_logger('botocore', logging.DEBUG)
```

### 2. Common Debugging Scenarios

```python
# Debug embedding generation issues
def debug_embedding_generation():
    """Debug embedding generation with detailed logging"""
    service = BedrockEmbeddingService()
    
    # Test with simple input
    test_text = "Simple test text"
    
    try:
        result = service.generate_text_embedding(test_text, "amazon.titan-embed-text-v2:0")
        
        print(f"✅ Success: Generated {len(result.embedding)} dimensions")
        print(f"   Processing time: {result.processing_time_ms}ms")
        print(f"   Model: {result.model_id}")
        
        # Validate embedding properties
        assert len(result.embedding) == 1024, f"Expected 1024 dimensions, got {len(result.embedding)}"
        assert all(isinstance(x, float) for x in result.embedding), "All values should be floats"
        assert any(abs(x) > 0.001 for x in result.embedding), "Embedding should not be all zeros"
        
    except Exception as e:
        print(f"❌ Embedding generation failed: {e}")
        
        # Debug AWS configuration
        import boto3
        session = boto3.Session()
        print(f"   AWS Region: {session.region_name}")
        print(f"   AWS Profile: {session.profile_name}")
        
        # Test basic AWS access
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"   AWS Identity: {identity}")
        except Exception as aws_e:
            print(f"   ❌ AWS access failed: {aws_e}")

# Debug vector storage issues
def debug_vector_storage():
    """Debug S3 Vector storage operations"""
    storage_manager = S3VectorStorageManager()
    
    # Test bucket creation
    test_bucket = f"debug-test-{int(time.time())}"
    
    try:
        bucket_result = storage_manager.create_vector_bucket(test_bucket)
        print(f"✅ Bucket created: {bucket_result['bucket_arn']}")
        
        # Test index creation
        index_arn = storage_manager.create_vector_index(
            bucket_name=test_bucket,
            index_name="debug-index",
            dimensions=1024
        )
        print(f"✅ Index created: {index_arn}")
        
        # Test vector storage
        test_vector = [0.1] * 1024  # Simple test vector
        vector_data = {
            "key": "debug-test-1",
            "data": {"float32": test_vector},
            "metadata": {"debug": "true", "timestamp": str(time.time())}
        }
        
        storage_result = storage_manager.put_vectors_batch(index_arn, [vector_data])
        print(f"✅ Vector stored: {storage_result}")
        
        # Test vector query
        query_result = storage_manager.query_similar_vectors(
            index_arn=index_arn,
            query_vector=test_vector,
            top_k=1
        )
        print(f"✅ Query successful: {len(query_result['results'])} results")
        
    except Exception as e:
        print(f"❌ Vector storage failed: {e}")
        
        # Check S3 Vectors service availability
        try:
            client = boto3.client('s3vectors')
            response = client.list_vector_buckets()
            print(f"   S3 Vectors accessible: {len(response.get('buckets', []))} existing buckets")
        except Exception as s3v_e:
            print(f"   ❌ S3 Vectors access failed: {s3v_e}")
    
    finally:
        # Cleanup
        try:
            storage_manager._cleanup_test_resources(test_bucket)
        except:
            pass
```

### 3. Performance Debugging

```python
import time
import psutil
from functools import wraps

def performance_monitor(func):
    """Decorator to monitor function performance"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Monitor memory and CPU before
        process = psutil.Process()
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent_before = process.cpu_percent()
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Monitor after
            end_time = time.time()
            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            
            execution_time = end_time - start_time
            memory_used = memory_after - memory_before
            
            print(f"🔍 Performance Stats for {func.__name__}:")
            print(f"   ⏱️  Execution time: {execution_time:.2f}s")
            print(f"   💾 Memory used: {memory_used:.1f}MB")
            print(f"   📊 Memory total: {memory_after:.1f}MB")
            
            # Performance warnings
            if execution_time > 30:
                print(f"   ⚠️  Slow execution: {execution_time:.2f}s")
            if memory_used > 500:
                print(f"   ⚠️  High memory usage: {memory_used:.1f}MB")
            
            return result
            
        except Exception as e:
            print(f"❌ Performance monitoring failed for {func.__name__}: {e}")
            raise
    
    return wrapper

# Usage example
@performance_monitor
def process_large_batch():
    """Example of performance-monitored function"""
    # Your processing logic here
    pass
```

This developer guide provides comprehensive information for contributing to and extending the S3Vector project, with emphasis on maintainable code, thorough testing, and effective debugging practices.