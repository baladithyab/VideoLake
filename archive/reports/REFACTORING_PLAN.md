# S3Vector Backend Refactoring Plan

## Overview
Refactor large service files (especially `s3_vector_storage.py` at 2,467 lines) into smaller, focused modules with better separation of concerns.

## Current State Analysis

### Large Files
1. **s3_vector_storage.py** - 2,467 lines, 39 methods
   - Longest methods: `list_vectors` (185L), `create_vector_bucket` (182L), `query_vectors` (171L)
2. **opensearch_integration.py** - 1,650 lines
3. **enhanced_storage_integration_manager.py** - 1,288 lines
4. **similarity_search_engine.py** - 1,204 lines
5. **twelvelabs_video_processing.py** - 1,081 lines

### Identified Issues

#### 1. S3VectorStorageManager - Multiple Responsibilities
Current class handles:
- Bucket management (create, list, get, delete, exists)
- Index management (create, list, get, delete, exists)
- Vector operations (put, query, list)
- Multi-index coordination
- Validation (bucket names, index names, vector data, dimensions)
- Error handling and retries
- Result fusion (weighted average, rank-based, concatenate)

#### 2. Duplicate Code Patterns
- Retry logic with exponential backoff (in `s3_vector_storage.py` and `bedrock_embedding.py`)
- Error handling for AWS ClientError/BotoCoreError (67 occurrences)
- ARN parsing (`_extract_bucket_from_arn`, `_extract_index_from_arn`)
- Resource registry integration patterns

#### 3. Long Methods (>100 lines)
- `list_vectors` - 185 lines
- `create_vector_bucket` - 182 lines
- `query_vectors` - 171 lines
- `create_vector_index` - 162 lines
- `delete_vector_index` - 154 lines
- `put_vectors` - 151 lines
- `delete_vector_bucket` - 127 lines
- `list_vector_indexes` - 118 lines
- `_validate_vector_data` - 105 lines
- `put_vectors_with_lazy_index_creation` - 100 lines

## Refactoring Strategy

### Phase 1: Extract Common Utilities (High Priority)

#### 1.1 Create `src/utils/aws_retry.py`
Extract retry logic with exponential backoff:
```python
class AWSRetryHandler:
    @staticmethod
    def retry_with_backoff(func, max_retries=3, base_delay=1.0):
        """Exponential backoff retry for AWS operations"""

    @staticmethod
    def is_retryable_error(error: ClientError) -> bool:
        """Check if error should be retried"""
```

**Benefits**:
- Eliminates duplicate retry logic (2 implementations)
- Centralized retry configuration
- Consistent error handling across services

#### 1.2 Create `src/utils/arn_parser.py`
Extract ARN parsing utilities:
```python
class ARNParser:
    @staticmethod
    def parse_s3_vector_arn(arn: str) -> Dict[str, str]:
        """Parse S3 Vector ARN into components"""

    @staticmethod
    def extract_bucket_name(arn: str) -> Optional[str]:
        """Extract bucket name from ARN"""

    @staticmethod
    def extract_index_name(arn: str) -> Optional[str]:
        """Extract index name from ARN"""

    @staticmethod
    def build_index_arn(bucket: str, index: str) -> str:
        """Build index ARN from components"""
```

**Benefits**:
- Single source of truth for ARN parsing
- Reduces 3 duplicate methods in s3_vector_storage.py
- Easier to maintain and test

#### 1.3 Create `src/utils/vector_validation.py`
Extract validation logic:
```python
class VectorValidator:
    @staticmethod
    def validate_vector_data(vectors_data: List[Dict]) -> None:
        """Validate vector data structure (105 lines currently)"""

    @staticmethod
    def validate_dimensions(dimensions: int) -> None:
        """Validate vector dimensions"""

    @staticmethod
    def normalize_vector(vector: List[float]) -> np.ndarray:
        """Normalize vector to unit length"""
```

**Benefits**:
- Removes 100+ lines from s3_vector_storage.py
- Reusable across other vector storage backends
- Better unit testing isolation

### Phase 2: Split S3VectorStorageManager (High Priority)

#### 2.1 Create `src/services/s3vector/bucket_manager.py`
Handle bucket operations:
```python
class S3VectorBucketManager:
    """Manages S3 vector bucket lifecycle"""
    def create_vector_bucket(...)
    def get_vector_bucket(...)
    def list_vector_buckets(...)
    def delete_vector_bucket(...)
    def bucket_exists(...)
```
**Reduces**: ~500 lines from main file

#### 2.2 Create `src/services/s3vector/index_manager.py`
Handle index operations:
```python
class S3VectorIndexManager:
    """Manages S3 vector index lifecycle"""
    def create_vector_index(...)
    def get_vector_index_metadata(...)
    def list_vector_indexes(...)
    def delete_vector_index(...)
    def index_exists(...)
    def delete_index_with_retries(...)
```
**Reduces**: ~600 lines from main file

#### 2.3 Create `src/services/s3vector/vector_operations.py`
Handle vector CRUD:
```python
class S3VectorOperations:
    """Core vector storage operations"""
    def put_vectors(...)
    def put_vectors_batch(...)
    def query_vectors(...)
    def list_vectors(...)
```
**Reduces**: ~700 lines from main file

#### 2.4 Create `src/services/s3vector/multi_index_coordinator.py`
Handle multi-index operations:
```python
class MultiIndexCoordinator:
    """Coordinate operations across multiple vector indexes"""
    def put_vectors_multi_index(...)
    def query_vectors_multi_index(...)
    def create_multi_index_architecture(...)
    def register_vector_index(...)
    def get_multi_index_stats(...)
```
**Reduces**: ~300 lines from main file

#### 2.5 Create `src/services/s3vector/result_fusion.py`
Handle result fusion strategies:
```python
class ResultFusionStrategy:
    """Base class for result fusion"""

class WeightedAverageFusion(ResultFusionStrategy):
    def fuse(...)

class RankBasedFusion(ResultFusionStrategy):
    def fuse(...)

class ConcatenateFusion(ResultFusionStrategy):
    def fuse(...)
```
**Reduces**: ~150 lines from main file

#### 2.6 Keep `src/services/s3_vector_storage.py` as Facade
```python
class S3VectorStorageManager:
    """Facade for S3 vector storage operations"""
    def __init__(self):
        self.bucket_manager = S3VectorBucketManager()
        self.index_manager = S3VectorIndexManager()
        self.vector_ops = S3VectorOperations()
        self.multi_index = MultiIndexCoordinator()

    # Delegate methods to specialized managers
```
**Result**: Main file reduced from 2,467 lines to ~300 lines

### Phase 3: Refactor Other Large Files (Medium Priority)

#### 3.1 opensearch_integration.py (1,650 lines)
Split into:
- `opensearch/domain_manager.py` - Domain lifecycle
- `opensearch/index_operations.py` - Index CRUD
- `opensearch/query_builder.py` - Query DSL construction

#### 3.2 similarity_search_engine.py (1,204 lines)
Split into:
- `search/query_processor.py` - Query preprocessing
- `search/backend_router.py` - Route to correct backend
- `search/result_aggregator.py` - Aggregate multi-backend results

#### 3.3 twelvelabs_video_processing.py (1,081 lines)
Split into:
- `video/upload_manager.py` - Video upload handling
- `video/job_tracker.py` - Job monitoring
- `video/embedding_extractor.py` - Embedding extraction

### Phase 4: Consolidate Duplicate Patterns (Low Priority)

#### 4.1 Error Handling Decorator
Create `src/utils/error_handling.py`:
```python
def handle_aws_errors(operation_name: str):
    """Decorator for consistent AWS error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ClientError as e:
                # Structured error handling
```

#### 4.2 Resource Registry Integration Mixin
Create `src/utils/registry_mixin.py`:
```python
class ResourceRegistryMixin:
    """Mixin for consistent resource registry integration"""
    def register_resource(...)
    def unregister_resource(...)
    def get_registered_resources(...)
```

## Implementation Order

### Immediate (Today)
1. ✅ Create utility modules (aws_retry, arn_parser, vector_validation)
2. ✅ Extract and test retry logic
3. ✅ Extract and test ARN parsing

### Next Session
4. Split s3_vector_storage.py into specialized managers
5. Update imports and tests
6. Verify backward compatibility

### Future
7. Refactor opensearch_integration.py
8. Refactor similarity_search_engine.py
9. Create error handling decorator
10. Consolidate remaining duplicates

## Success Metrics

- **LOC Reduction**: s3_vector_storage.py from 2,467 → ~300 lines (88% reduction)
- **Method Size**: No methods >100 lines (currently 10 methods >100 lines)
- **Code Reuse**: Eliminate duplicate retry/parsing logic
- **Maintainability**: Single Responsibility Principle per module
- **Testability**: Smaller, focused modules easier to unit test

## Backward Compatibility

Maintain existing API by keeping `S3VectorStorageManager` as facade:
```python
# OLD CODE (still works)
manager = S3VectorStorageManager()
manager.create_vector_bucket(...)
manager.put_vectors(...)

# NEW CODE (also works, more explicit)
from src.services.s3vector import S3VectorBucketManager
bucket_manager = S3VectorBucketManager()
bucket_manager.create_vector_bucket(...)
```

## Risk Mitigation

1. **Incremental Changes**: Extract utilities first, then split classes
2. **Test Coverage**: Add unit tests for extracted utilities
3. **Backward Compatibility**: Keep facade pattern for existing code
4. **Code Review**: Review each module before moving to next
5. **Git Branches**: Use feature branches for large refactorings
