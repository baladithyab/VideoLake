"""
S3 Vector Storage Module.

Specialized managers for S3 Vector operations, extracted from the monolithic
s3_vector_storage.py file for better separation of concerns and maintainability.

Managers:
- S3VectorBucketManager: Bucket lifecycle operations
- S3VectorIndexManager: Index lifecycle operations
- S3VectorOperations: Core vector CRUD operations
"""

from .bucket_manager import S3VectorBucketManager
from .index_manager import S3VectorIndexManager
from .vector_operations import S3VectorOperations

__all__ = [
    "S3VectorBucketManager",
    "S3VectorIndexManager",
    "S3VectorOperations",
]