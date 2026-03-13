"""
S3 Staging Manager for Large Dataset Ingestion.

Manages S3-based staging for large datasets:
- Efficient upload strategies (multipart, parallel)
- Dataset organization and versioning
- Bandwidth management and cost optimization
- Cleanup and lifecycle policies
"""

import asyncio
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, BinaryIO
from concurrent.futures import ThreadPoolExecutor

import boto3
from botocore.exceptions import ClientError

from src.utils.aws_retry import AWSRetryHandler
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class StagingConfig:
    """Configuration for S3 staging."""
    bucket_name: str
    prefix: str = "staging"
    enable_versioning: bool = True
    enable_encryption: bool = True
    storage_class: str = "INTELLIGENT_TIERING"
    multipart_threshold_mb: int = 100
    multipart_chunk_size_mb: int = 50
    max_concurrent_uploads: int = 10


@dataclass
class UploadResult:
    """Result of S3 upload operation."""
    s3_key: str
    s3_uri: str
    size_bytes: int
    etag: str
    upload_time_seconds: float
    success: bool
    error: Optional[str] = None


class S3StagingManager:
    """
    Manages S3 staging for large-scale dataset ingestion.

    Provides efficient upload strategies optimized for AWS costs and bandwidth.
    """

    def __init__(self, config: StagingConfig):
        """Initialize S3 staging manager."""
        self.config = config
        self.s3_client = boto3.client('s3')
        self._ensure_bucket_configured()

    def _ensure_bucket_configured(self):
        """Ensure S3 bucket is properly configured."""
        try:
            # Check if bucket exists
            AWSRetryHandler.retry_with_backoff(
                lambda: self.s3_client.head_bucket(Bucket=self.config.bucket_name),
                operation_name="head_bucket"
            )

            # Enable versioning if requested
            if self.config.enable_versioning:
                self.s3_client.put_bucket_versioning(
                    Bucket=self.config.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                logger.info(f"Versioning enabled for bucket: {self.config.bucket_name}")

            # Set lifecycle policy for intelligent tiering
            if self.config.storage_class == "INTELLIGENT_TIERING":
                lifecycle_config = {
                    'Rules': [
                        {
                            'Id': 'staging-intelligent-tiering',
                            'Status': 'Enabled',
                            'Filter': {'Prefix': self.config.prefix},
                            'Transitions': [
                                {
                                    'Days': 0,
                                    'StorageClass': 'INTELLIGENT_TIERING'
                                }
                            ]
                        }
                    ]
                }
                self.s3_client.put_bucket_lifecycle_configuration(
                    Bucket=self.config.bucket_name,
                    LifecycleConfiguration=lifecycle_config
                )
                logger.info(f"Lifecycle policy configured for prefix: {self.config.prefix}")

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                raise ValueError(f"Bucket not found: {self.config.bucket_name}")
            else:
                logger.warning(f"Failed to configure bucket: {e}")

    def generate_staging_key(
        self,
        dataset_name: str,
        modality: str,
        filename: str,
        version: Optional[str] = None
    ) -> str:
        """
        Generate S3 key for staged dataset.

        Args:
            dataset_name: Name of dataset (e.g., 'msmarco', 'coco')
            modality: Data modality ('text', 'image', 'audio', 'video')
            filename: Original filename
            version: Optional version identifier

        Returns:
            S3 key following consistent structure
        """
        if version is None:
            version = datetime.utcnow().strftime('%Y%m%d')

        key = f"{self.config.prefix}/{dataset_name}/{modality}/{version}/{filename}"
        return key

    async def upload_file(
        self,
        local_path: Path,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """
        Upload file to S3 with optimal strategy.

        Uses multipart upload for large files, direct put for small files.

        Args:
            local_path: Path to local file
            s3_key: Target S3 key
            metadata: Optional metadata to attach

        Returns:
            UploadResult with upload details
        """
        import time
        start_time = time.time()

        try:
            file_size = local_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # Determine upload strategy
            if file_size_mb > self.config.multipart_threshold_mb:
                logger.info(f"Using multipart upload for {local_path.name} ({file_size_mb:.2f} MB)")
                result = await self._multipart_upload(local_path, s3_key, metadata)
            else:
                logger.info(f"Using direct upload for {local_path.name} ({file_size_mb:.2f} MB)")
                result = await self._direct_upload(local_path, s3_key, metadata)

            upload_time = time.time() - start_time
            result.upload_time_seconds = upload_time

            logger.info(f"Upload successful: {s3_key} ({file_size_mb:.2f} MB in {upload_time:.2f}s)")
            return result

        except Exception as e:
            logger.error(f"Upload failed for {local_path}: {e}")
            return UploadResult(
                s3_key=s3_key,
                s3_uri=f"s3://{self.config.bucket_name}/{s3_key}",
                size_bytes=0,
                etag="",
                upload_time_seconds=time.time() - start_time,
                success=False,
                error=str(e)
            )

    async def _direct_upload(
        self,
        local_path: Path,
        s3_key: str,
        metadata: Optional[Dict[str, str]]
    ) -> UploadResult:
        """Direct upload for small files."""
        extra_args = {
            'StorageClass': self.config.storage_class
        }

        if metadata:
            extra_args['Metadata'] = metadata

        if self.config.enable_encryption:
            extra_args['ServerSideEncryption'] = 'AES256'

        # Use asyncio.to_thread for blocking I/O
        def _upload():
            with open(local_path, 'rb') as f:
                response = self.s3_client.put_object(
                    Bucket=self.config.bucket_name,
                    Key=s3_key,
                    Body=f,
                    **extra_args
                )
            return response

        response = await asyncio.to_thread(
            AWSRetryHandler.retry_with_backoff,
            _upload,
            operation_name=f"s3_put_{s3_key}"
        )

        return UploadResult(
            s3_key=s3_key,
            s3_uri=f"s3://{self.config.bucket_name}/{s3_key}",
            size_bytes=local_path.stat().st_size,
            etag=response.get('ETag', '').strip('"'),
            upload_time_seconds=0.0,  # Set by caller
            success=True
        )

    async def _multipart_upload(
        self,
        local_path: Path,
        s3_key: str,
        metadata: Optional[Dict[str, str]]
    ) -> UploadResult:
        """Multipart upload for large files."""
        chunk_size = self.config.multipart_chunk_size_mb * 1024 * 1024

        # Initiate multipart upload
        extra_args = {
            'StorageClass': self.config.storage_class
        }

        if metadata:
            extra_args['Metadata'] = metadata

        if self.config.enable_encryption:
            extra_args['ServerSideEncryption'] = 'AES256'

        def _initiate():
            return self.s3_client.create_multipart_upload(
                Bucket=self.config.bucket_name,
                Key=s3_key,
                **extra_args
            )

        response = await asyncio.to_thread(
            AWSRetryHandler.retry_with_backoff,
            _initiate,
            operation_name="create_multipart_upload"
        )

        upload_id = response['UploadId']

        try:
            # Upload parts in parallel
            parts = []
            with open(local_path, 'rb') as f:
                part_number = 1
                while True:
                    data = f.read(chunk_size)
                    if not data:
                        break

                    part = await self._upload_part(
                        data,
                        s3_key,
                        upload_id,
                        part_number
                    )
                    parts.append(part)
                    part_number += 1

            # Complete multipart upload
            def _complete():
                return self.s3_client.complete_multipart_upload(
                    Bucket=self.config.bucket_name,
                    Key=s3_key,
                    UploadId=upload_id,
                    MultipartUpload={'Parts': parts}
                )

            response = await asyncio.to_thread(
                AWSRetryHandler.retry_with_backoff,
                _complete,
                operation_name="complete_multipart_upload"
            )

            return UploadResult(
                s3_key=s3_key,
                s3_uri=f"s3://{self.config.bucket_name}/{s3_key}",
                size_bytes=local_path.stat().st_size,
                etag=response.get('ETag', '').strip('"'),
                upload_time_seconds=0.0,  # Set by caller
                success=True
            )

        except Exception as e:
            # Abort multipart upload on failure
            try:
                await asyncio.to_thread(
                    self.s3_client.abort_multipart_upload,
                    Bucket=self.config.bucket_name,
                    Key=s3_key,
                    UploadId=upload_id
                )
            except Exception as abort_error:
                logger.error(f"Failed to abort multipart upload: {abort_error}")

            raise e

    async def _upload_part(
        self,
        data: bytes,
        s3_key: str,
        upload_id: str,
        part_number: int
    ) -> Dict[str, Any]:
        """Upload a single part of multipart upload."""
        def _upload():
            return self.s3_client.upload_part(
                Bucket=self.config.bucket_name,
                Key=s3_key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data
            )

        response = await asyncio.to_thread(
            AWSRetryHandler.retry_with_backoff,
            _upload,
            operation_name=f"upload_part_{part_number}"
        )

        return {
            'PartNumber': part_number,
            'ETag': response['ETag']
        }

    async def upload_batch(
        self,
        files: List[tuple[Path, str]],
        metadata_fn: Optional[callable] = None
    ) -> List[UploadResult]:
        """
        Upload multiple files in parallel.

        Args:
            files: List of (local_path, s3_key) tuples
            metadata_fn: Optional function to generate metadata per file

        Returns:
            List of UploadResult for each file
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent_uploads)

        async def upload_with_semaphore(local_path: Path, s3_key: str):
            async with semaphore:
                metadata = metadata_fn(local_path) if metadata_fn else None
                return await self.upload_file(local_path, s3_key, metadata)

        results = await asyncio.gather(
            *[upload_with_semaphore(path, key) for path, key in files],
            return_exceptions=True
        )

        # Convert exceptions to failed results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch upload failed: {result}")
                processed_results.append(
                    UploadResult(
                        s3_key="",
                        s3_uri="",
                        size_bytes=0,
                        etag="",
                        upload_time_seconds=0.0,
                        success=False,
                        error=str(result)
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def list_staged_datasets(self) -> List[Dict[str, Any]]:
        """List all staged datasets in the bucket."""
        datasets = []

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=self.config.prefix + '/',
                Delimiter='/'
            )

            for page in pages:
                for prefix in page.get('CommonPrefixes', []):
                    dataset_name = prefix['Prefix'].split('/')[-2]
                    datasets.append({
                        'name': dataset_name,
                        'prefix': prefix['Prefix']
                    })

        except ClientError as e:
            logger.error(f"Failed to list datasets: {e}")

        return datasets

    def get_dataset_size(self, dataset_name: str, modality: str) -> int:
        """Get total size of staged dataset in bytes."""
        prefix = f"{self.config.prefix}/{dataset_name}/{modality}/"
        total_size = 0

        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )

            for page in pages:
                for obj in page.get('Contents', []):
                    total_size += obj['Size']

        except ClientError as e:
            logger.error(f"Failed to get dataset size: {e}")

        return total_size

    async def cleanup_old_versions(
        self,
        dataset_name: str,
        keep_versions: int = 3
    ):
        """Clean up old dataset versions, keeping only N most recent."""
        prefix = f"{self.config.prefix}/{dataset_name}/"

        try:
            # List all versions
            versions = []
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )

            for page in pages:
                for common_prefix in page.get('CommonPrefixes', []):
                    version_path = common_prefix['Prefix']
                    version_id = version_path.split('/')[-2]
                    versions.append(version_id)

            # Sort versions (assumes YYYYMMDD format)
            versions.sort(reverse=True)

            # Delete old versions
            if len(versions) > keep_versions:
                for old_version in versions[keep_versions:]:
                    delete_prefix = f"{prefix}{old_version}/"
                    await self._delete_prefix(delete_prefix)
                    logger.info(f"Deleted old version: {old_version}")

        except ClientError as e:
            logger.error(f"Failed to cleanup versions: {e}")

    async def _delete_prefix(self, prefix: str):
        """Delete all objects under a prefix."""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )

            for page in pages:
                objects = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
                if objects:
                    await asyncio.to_thread(
                        self.s3_client.delete_objects,
                        Bucket=self.config.bucket_name,
                        Delete={'Objects': objects}
                    )

        except ClientError as e:
            logger.error(f"Failed to delete prefix {prefix}: {e}")
