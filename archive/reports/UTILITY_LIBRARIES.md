# Utility Libraries

This document provides comprehensive documentation for the shared utility libraries extracted during the S3Vector backend refactoring. These utilities eliminate code duplication and provide reusable components across all services.

## Table of Contents

- [Overview](#overview)
- [AWSRetryHandler](#awsretryhandler)
- [ARNParser](#arnparser)
- [VectorValidator](#vectorvalidator)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)

---

## Overview

### Purpose

The utility libraries provide:
- **Centralized Logic**: Single source of truth for common patterns
- **Code Reuse**: Eliminate duplication across 10+ service files
- **Consistency**: Standard behavior across all AWS operations
- **Maintainability**: Fix once, applies everywhere

### Extracted Utilities

| Utility | File | Lines | Purpose |
|---------|------|-------|---------|
| **AWSRetryHandler** | `src/utils/aws_retry.py` | 209 | Exponential backoff retry logic |
| **ARNParser** | `src/utils/arn_parser.py` | 234 | AWS ARN parsing and validation |
| **VectorValidator** | `src/utils/vector_validation.py` | 287 | Vector data validation |

---

## AWSRetryHandler

**File**: `src/utils/aws_retry.py`
**Lines**: 209
**Purpose**: Centralized retry logic with exponential backoff for AWS API calls

### Overview

The `AWSRetryHandler` eliminates duplicate retry logic that was previously scattered across `s3_vector_storage.py`, `bedrock_embedding.py`, and other services. It provides configurable retry behavior with exponential backoff, jitter, and error-specific handling.

### Class Methods

#### `retry_with_backoff()`

Execute a function with exponential backoff retry on AWS errors.

```python
@classmethod
def retry_with_backoff(
    cls,
    func: Callable[[], T],
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_codes: Optional[Set[str]] = None,
    operation_name: Optional[str] = None
) -> T:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Function to execute (should be a lambda wrapping the API call)
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 60.0)
        retryable_codes: Set of AWS error codes to retry (default: standard retryable errors)
        operation_name: Name of operation for logging (default: "AWS operation")

    Returns:
        Result from the function call

    Raises:
        ClientError: If non-retryable error or max retries exceeded
    """
```

**Default Retryable Errors**:
- `ThrottlingException`
- `ProvisionedThroughputExceededException`
- `RequestLimitExceeded`
- `ServiceUnavailable`
- `InternalError`
- `ResourceInUseException`

#### `calculate_backoff_delay()`

Calculate exponential backoff delay with jitter.

```python
@classmethod
def calculate_backoff_delay(
    cls,
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0
) -> float:
    """
    Calculate delay using exponential backoff with jitter.

    Formula: min(max_delay, base_delay * (2 ** attempt) + random(0, 1))

    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay in seconds with jitter added
    """
```

#### `is_retryable_error()`

Determine if an AWS ClientError is retryable.

```python
@classmethod
def is_retryable_error(
    cls,
    error: ClientError,
    retryable_codes: Optional[Set[str]] = None
) -> bool:
    """
    Check if AWS error should be retried.

    Args:
        error: ClientError from boto3
        retryable_codes: Custom set of retryable error codes

    Returns:
        True if error should be retried, False otherwise
    """
```

### Usage Examples

#### Basic Usage

```python
from src.utils.aws_retry import AWSRetryHandler

# Simple API call with default retry behavior
result = AWSRetryHandler.retry_with_backoff(
    lambda: self.s3vectors_client.create_vector_bucket(
        vectorBucketName="my-bucket"
    )
)
```

#### Custom Retry Configuration

```python
# Custom retry attempts and delays
result = AWSRetryHandler.retry_with_backoff(
    lambda: self.client.operation(),
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    operation_name="my_critical_operation"
)
```

#### Custom Retryable Errors

```python
# Retry only specific error codes
custom_retryable = {"CustomError", "AnotherError"}
result = AWSRetryHandler.retry_with_backoff(
    lambda: self.client.operation(),
    retryable_codes=custom_retryable
)
```

#### Decorator Pattern

```python
from src.utils.aws_retry import with_retry

class MyService:
    @with_retry(max_retries=3)
    def my_operation(self):
        """This method will automatically retry on AWS errors."""
        return self.client.some_operation()
```

### Error Handling

The handler distinguishes between:

**Retryable Errors** (will retry):
- Throttling/rate limiting errors
- Temporary service unavailability
- Resource contention
- Internal AWS errors

**Non-Retryable Errors** (will raise immediately):
- Invalid parameters (`ValidationException`)
- Access denied (`AccessDeniedException`)
- Resource not found (`ResourceNotFoundException`)
- Resource already exists (`ResourceAlreadyExistsException`)

### Logging

The handler logs retry attempts:
```
WARNING: create_vector_bucket retrying after 1.23s (attempt 1/3): ThrottlingException
WARNING: create_vector_bucket retrying after 2.47s (attempt 2/3): ServiceUnavailable
```

---

## ARNParser

**File**: `src/utils/arn_parser.py`
**Lines**: 234
**Purpose**: AWS ARN (Amazon Resource Name) parsing and validation

### Overview

The `ARNParser` provides centralized ARN parsing logic that was previously duplicated across 3+ methods in `s3_vector_storage.py`. It handles multiple ARN formats and provides extraction utilities for S3 Vectors specific resources.

### Class Methods

#### `parse_arn()`

Parse generic AWS ARN into components.

```python
@classmethod
def parse_arn(cls, arn: str) -> Dict[str, str]:
    """
    Parse AWS ARN into components.

    ARN Format: arn:partition:service:region:account:resource

    Args:
        arn: AWS ARN string

    Returns:
        Dict with keys: partition, service, region, account_id, resource

    Raises:
        ValidationError: If ARN format is invalid

    Example:
        >>> ARNParser.parse_arn("arn:aws:s3:::my-bucket")
        {
            'partition': 'aws',
            'service': 's3',
            'region': '',
            'account_id': '',
            'resource': 'my-bucket'
        }
    """
```

#### `parse_s3vector_arn()`

Parse S3 Vector specific ARN format.

```python
@classmethod
def parse_s3vector_arn(cls, arn: str) -> Dict[str, str]:
    """
    Parse S3 Vector ARN into components.

    S3 Vector ARN Format:
        arn:aws:s3vectors:region:account:bucket/BUCKET_NAME/index/INDEX_NAME

    Args:
        arn: S3 Vector ARN string

    Returns:
        Dict with keys: partition, service, region, account_id, bucket, index

    Raises:
        ValidationError: If ARN is not valid S3 Vector format

    Example:
        >>> ARNParser.parse_s3vector_arn(
        ...     "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index"
        ... )
        {
            'partition': 'aws',
            'service': 's3vectors',
            'region': 'us-east-1',
            'account_id': '123456789012',
            'bucket': 'my-bucket',
            'index': 'my-index'
        }
    """
```

#### `extract_bucket_name()`

Extract bucket name from S3 Vector ARN.

```python
@classmethod
def extract_bucket_name(cls, arn: str) -> Optional[str]:
    """
    Extract bucket name from S3 Vector ARN.

    Args:
        arn: S3 Vector ARN string

    Returns:
        Bucket name if valid ARN, None otherwise

    Example:
        >>> ARNParser.extract_bucket_name(
        ...     "arn:aws:s3vectors:us-east-1:123:bucket/my-bucket/index/my-index"
        ... )
        'my-bucket'
    """
```

#### `extract_index_name()`

Extract index name from S3 Vector ARN.

```python
@classmethod
def extract_index_name(cls, arn: str) -> Optional[str]:
    """
    Extract index name from S3 Vector ARN.

    Args:
        arn: S3 Vector ARN string

    Returns:
        Index name if valid ARN, None otherwise

    Example:
        >>> ARNParser.extract_index_name(
        ...     "arn:aws:s3vectors:us-east-1:123:bucket/my-bucket/index/my-index"
        ... )
        'my-index'
    """
```

#### `build_s3vector_arn()`

Construct S3 Vector ARN from components.

```python
@classmethod
def build_s3vector_arn(
    cls,
    bucket_name: str,
    index_name: str,
    region: str,
    account_id: str,
    partition: str = "aws"
) -> str:
    """
    Build S3 Vector ARN from components.

    Args:
        bucket_name: Vector bucket name
        index_name: Vector index name
        region: AWS region (e.g., 'us-east-1')
        account_id: AWS account ID
        partition: AWS partition (default: 'aws')

    Returns:
        Complete S3 Vector ARN string

    Example:
        >>> ARNParser.build_s3vector_arn(
        ...     "my-bucket", "my-index", "us-east-1", "123456789012"
        ... )
        'arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index'
    """
```

#### `to_resource_id()`

Convert to S3 Vectors API resource-id format.

```python
@classmethod
def to_resource_id(cls, bucket_name: str, index_name: str) -> str:
    """
    Convert to S3 Vectors resource-id format.

    Format: bucket/BUCKET_NAME/index/INDEX_NAME

    Args:
        bucket_name: Vector bucket name
        index_name: Vector index name

    Returns:
        Resource ID string

    Example:
        >>> ARNParser.to_resource_id("my-bucket", "my-index")
        'bucket/my-bucket/index/my-index'
    """
```

### Usage Examples

#### Parse Full ARN

```python
from src.utils.arn_parser import ARNParser

arn = "arn:aws:s3vectors:us-east-1:123456789012:bucket/my-bucket/index/my-index"
parsed = ARNParser.parse_s3vector_arn(arn)

print(parsed['bucket'])     # 'my-bucket'
print(parsed['index'])      # 'my-index'
print(parsed['region'])     # 'us-east-1'
print(parsed['account_id']) # '123456789012'
```

#### Extract Components

```python
# Quick extraction without full parsing
bucket = ARNParser.extract_bucket_name(index_arn)
index = ARNParser.extract_index_name(index_arn)

if bucket and index:
    print(f"Working with bucket: {bucket}, index: {index}")
```

#### Build ARN

```python
# Construct ARN from components
arn = ARNParser.build_s3vector_arn(
    bucket_name="my-bucket",
    index_name="my-index",
    region="us-east-1",
    account_id="123456789012"
)

# Use in API call
self.client.get_index(indexArn=arn)
```

#### Convert to Resource ID

```python
# Some APIs accept resource-id instead of ARN
resource_id = ARNParser.to_resource_id("my-bucket", "my-index")
# Returns: "bucket/my-bucket/index/my-index"

self.client.put_vectors(
    bucket="my-bucket",
    indexName="my-index",
    # Or use resource_id format
)
```

### Validation

The parser validates:
- ARN format (correct number of components)
- S3 Vector specific resource format
- Bucket and index name presence

Invalid ARNs raise `ValidationError` with descriptive messages.

---

## VectorValidator

**File**: `src/utils/vector_validation.py`
**Lines**: 287
**Purpose**: Vector data validation for AWS S3 Vectors

### Overview

The `VectorValidator` provides comprehensive validation for vector data before storage. This 105-line method was previously embedded in `s3_vector_storage.py` and is now reusable across all vector storage backends.

### Class Attributes

```python
MAX_VECTORS_PER_REQUEST = 500    # AWS S3 Vectors limit
MIN_VECTOR_DIMENSION = 1          # Minimum dimensions
MAX_VECTOR_DIMENSION = 4096       # Maximum dimensions
```

### Class Methods

#### `validate_vector_data()`

Validate vector data structure before storage (AWS S3 Vectors format).

```python
@classmethod
def validate_vector_data(cls, vectors_data: List[Dict[str, Any]]) -> None:
    """
    Validate vector data for AWS S3 Vectors format.

    Required Format:
        [
            {
                'key': 'unique-id',
                'data': {'float32': [0.1, 0.2, ...]},
                'metadata': {...}  # optional
            },
            ...
        ]

    Args:
        vectors_data: List of vector dictionaries

    Raises:
        ValidationError: If validation fails with specific error code

    Error Codes:
        - EMPTY_VECTOR_DATA: vectors_data is empty
        - TOO_MANY_VECTORS: Exceeds MAX_VECTORS_PER_REQUEST
        - MISSING_KEY: Vector missing 'key' field
        - INVALID_KEY_TYPE: 'key' is not a string
        - MISSING_DATA: Vector missing 'data' field
        - MISSING_FLOAT32: 'data' missing 'float32' field
        - INVALID_VECTOR_TYPE: Vector data not a list
        - NAN_VALUE: Vector contains NaN values
        - INFINITY_VALUE: Vector contains infinite values
        - INCONSISTENT_DIMENSIONS: Vectors have different dimensions
    """
```

#### `validate_vector_array()`

Validate individual vector array (list of floats).

```python
@classmethod
def validate_vector_array(
    cls,
    vector_array: Union[List[float], np.ndarray],
    vector_index: Optional[int] = None
) -> None:
    """
    Validate single vector array.

    Args:
        vector_array: List or NumPy array of float values
        vector_index: Index for error messages (optional)

    Raises:
        ValidationError: If vector is invalid
    """
```

#### `validate_dimensions()`

Validate vector dimensions are within AWS S3 Vectors limits.

```python
@classmethod
def validate_dimensions(cls, dimensions: int) -> None:
    """
    Validate dimensions are within supported range.

    AWS S3 Vectors supports dimensions: 1-4096

    Args:
        dimensions: Number of dimensions

    Raises:
        ValidationError: If dimensions outside valid range (1-4096)
    """
```

#### `validate_query_vector()`

Validate query vector for similarity search.

```python
@classmethod
def validate_query_vector(cls, query_vector: List[float]) -> None:
    """
    Validate query vector for similarity search.

    Args:
        query_vector: List of float values

    Raises:
        ValidationError: If query vector is invalid
    """
```

#### `normalize_vector()`

L2 normalize vector for cosine similarity.

```python
@classmethod
def normalize_vector(cls, vector: List[float]) -> List[float]:
    """
    L2 normalize vector (for cosine similarity).

    Formula: v / ||v||

    Args:
        vector: List of float values

    Returns:
        Normalized vector (unit length)

    Raises:
        ValidationError: If vector has zero magnitude
    """
```

### Usage Examples

#### Validate Before Storage

```python
from src.utils.vector_validation import VectorValidator

# Prepare vectors
vectors_data = [
    {
        "key": "vec1",
        "data": {"float32": [0.1, 0.2, 0.3, 0.4]},
        "metadata": {"category": "test"}
    },
    {
        "key": "vec2",
        "data": {"float32": [0.5, 0.6, 0.7, 0.8]}
    }
]

# Validate
try:
    VectorValidator.validate_vector_data(vectors_data)
    # Safe to store
    result = self.client.put_vectors(vectors=vectors_data)
except ValidationError as e:
    logger.error(f"Invalid vector data: {e}")
    # Handle error
```

#### Validate Dimensions

```python
# Validate index dimensions
dimensions = 1024

try:
    VectorValidator.validate_dimensions(dimensions)
    # Create index with these dimensions
    self.create_vector_index(dimensions=dimensions)
except ValidationError as e:
    logger.error(f"Invalid dimensions: {e}")
```

#### Validate Query Vector

```python
# Validate before querying
query_vector = [0.1, 0.2, 0.3, 0.4]

try:
    VectorValidator.validate_query_vector(query_vector)
    results = self.query_vectors(query_vector=query_vector)
except ValidationError as e:
    logger.error(f"Invalid query vector: {e}")
```

#### Normalize for Cosine Similarity

```python
# Normalize vector before storage (for cosine distance)
raw_vector = [1.0, 2.0, 3.0, 4.0]
normalized = VectorValidator.normalize_vector(raw_vector)

# Store normalized vector
vectors_data = [{
    "key": "vec1",
    "data": {"float32": normalized}
}]
```

### Error Handling

The validator provides detailed error messages with error codes:

```python
try:
    VectorValidator.validate_vector_data(vectors)
except ValidationError as e:
    print(f"Error Code: {e.error_code}")
    print(f"Message: {e.message}")
    print(f"Details: {e.error_details}")
```

Example error:
```
Error Code: INCONSISTENT_DIMENSIONS
Message: All vectors must have the same dimensions
Details: {'expected': 1024, 'found': 768, 'vector_index': 5}
```

---

## Usage Examples

### Complete Workflow Example

```python
from src.utils.aws_retry import AWSRetryHandler
from src.utils.arn_parser import ARNParser
from src.utils.vector_validation import VectorValidator
from src.utils.aws_clients import aws_client_factory

class MyVectorService:
    def __init__(self):
        self.client = aws_client_factory.get_s3vectors_client()

    def store_vectors(self, bucket: str, index: str, vectors_data: List[Dict]):
        """Store vectors with full validation and retry logic."""

        # 1. Validate vector data
        VectorValidator.validate_vector_data(vectors_data)

        # 2. Build ARN
        arn = ARNParser.build_s3vector_arn(
            bucket_name=bucket,
            index_name=index,
            region="us-east-1",
            account_id="123456789012"
        )

        # 3. Store with retry
        result = AWSRetryHandler.retry_with_backoff(
            lambda: self.client.put_vectors(
                indexArn=arn,
                vectors=vectors_data
            ),
            operation_name=f"put_vectors_{bucket}_{index}"
        )

        return result

    def query_similar(self, index_arn: str, query_vector: List[float], top_k: int = 10):
        """Query similar vectors with validation and retry."""

        # 1. Validate query vector
        VectorValidator.validate_query_vector(query_vector)

        # 2. Extract bucket and index from ARN
        bucket = ARNParser.extract_bucket_name(index_arn)
        index = ARNParser.extract_index_name(index_arn)

        if not bucket or not index:
            raise ValueError("Invalid index ARN")

        # 3. Query with retry
        result = AWSRetryHandler.retry_with_backoff(
            lambda: self.client.query_vectors(
                indexArn=index_arn,
                queryVector={"float32": query_vector},
                topK=top_k
            ),
            operation_name=f"query_vectors_{bucket}_{index}"
        )

        return result
```

---

## Best Practices

### 1. Always Use Utilities

❌ **Don't** implement custom retry logic:
```python
# BAD: Custom retry in service code
for i in range(3):
    try:
        return self.client.operation()
    except ClientError:
        time.sleep(2 ** i)
```

✅ **Do** use AWSRetryHandler:
```python
# GOOD: Use centralized utility
return AWSRetryHandler.retry_with_backoff(
    lambda: self.client.operation()
)
```

### 2. Validate Early

❌ **Don't** let AWS validate (wastes API calls):
```python
# BAD: Let AWS reject invalid data
result = self.client.put_vectors(vectors=vectors_data)
```

✅ **Do** validate before calling AWS:
```python
# GOOD: Catch errors early
VectorValidator.validate_vector_data(vectors_data)
result = self.client.put_vectors(vectors=vectors_data)
```

### 3. Use Specific Error Codes

❌ **Don't** catch generic exceptions:
```python
# BAD: Generic error handling
try:
    VectorValidator.validate_vector_data(vectors)
except Exception:
    return "Invalid data"
```

✅ **Do** use error codes for specific handling:
```python
# GOOD: Specific error handling
try:
    VectorValidator.validate_vector_data(vectors)
except ValidationError as e:
    if e.error_code == "TOO_MANY_VECTORS":
        return self.batch_store(vectors)
    elif e.error_code == "INCONSISTENT_DIMENSIONS":
        return {"error": "All vectors must have same dimensions"}
    raise
```

### 4. Log Operation Names

❌ **Don't** use generic operation names:
```python
# BAD: No context in logs
AWSRetryHandler.retry_with_backoff(lambda: self.client.create_index())
```

✅ **Do** provide descriptive names:
```python
# GOOD: Clear operation context
AWSRetryHandler.retry_with_backoff(
    lambda: self.client.create_index(bucket=bucket, index=index),
    operation_name=f"create_index_{bucket}_{index}"
)
# Logs: "create_index_my-bucket_my-index retrying..."
```

### 5. Handle ARN Formats Flexibly

❌ **Don't** assume single format:
```python
# BAD: Assumes ARN format
parts = arn.split('/')
bucket = parts[-3]
```

✅ **Do** use ARNParser for flexibility:
```python
# GOOD: Handles ARN or resource-id
bucket = ARNParser.extract_bucket_name(identifier)
if not bucket:
    raise ValueError("Invalid identifier")
```

---

## Testing

All utilities have comprehensive unit tests:

```bash
# Run utility tests
pytest tests/test_aws_retry.py -v
pytest tests/test_arn_parser.py -v
pytest tests/test_vector_validation.py -v

# Run with coverage
pytest tests/test_*.py --cov=src/utils --cov-report=html
```

---

## Contributing

When adding new utilities:

1. **Extract from Services**: Identify duplicate patterns (3+ occurrences)
2. **Create Focused Utility**: Single responsibility (retry, parsing, validation)
3. **Add Comprehensive Tests**: Cover success, errors, edge cases
4. **Document Thoroughly**: Usage examples, parameters, error codes
5. **Update This Guide**: Add new utility to this document

---

## Conclusion

The shared utility libraries provide:
- ✅ **Zero Duplication**: Eliminated retry/parsing/validation duplication
- ✅ **Consistency**: Same behavior across all services
- ✅ **Maintainability**: Fix once, applies everywhere
- ✅ **Testability**: Utilities independently tested
- ✅ **Reusability**: Available to all services and future code

For questions or issues with utilities, refer to the test files or open an issue on GitHub.
