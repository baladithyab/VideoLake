"""
S3 Bucket Utility Service

Provides safe, idempotent creation of regular S3 buckets (not S3 Vectors) for use by
the application without performing direct AWS calls in the UI layer.
Also includes video download and upload functionality for processing workflows.
"""

from __future__ import annotations

import os
import time
import tempfile
import requests
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from botocore.exceptions import ClientError
from src.utils.aws_clients import aws_client_factory
from src.config.unified_config_manager import get_unified_config_manager
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry
from src.exceptions import ValidationError, ProcessingError

logger = get_logger(__name__)


class S3BucketUtilityService:
    """
    Utility service to create/manage regular S3 buckets using the shared client factory
    and to persist audit logs in the resource registry.
    """

    @staticmethod
    def sanitize_bucket_name(bucket_name: str, fallback_prefix: str = "s3vector") -> str:
        """
        Sanitize bucket name to comply with AWS S3 naming rules:
        - 3-63 characters long
        - Only lowercase letters, numbers, hyphens, and periods
        - Must start and end with letter or number
        - No consecutive periods or hyphens
        - No uppercase letters or underscores
        
        Args:
            bucket_name: Original bucket name to sanitize
            fallback_prefix: Prefix to use if bucket_name is invalid
            
        Returns:
            Valid S3 bucket name
        """
        if not bucket_name or not isinstance(bucket_name, str):
            bucket_name = fallback_prefix
        
        # Convert to lowercase
        sanitized = bucket_name.lower()
        
        # Replace invalid characters with hyphens
        sanitized = re.sub(r'[^a-z0-9.-]', '-', sanitized)
        
        # Remove consecutive periods and hyphens
        sanitized = re.sub(r'[-]{2,}', '-', sanitized)
        sanitized = re.sub(r'[.]{2,}', '.', sanitized)
        sanitized = re.sub(r'[-.][-.]', '-', sanitized)
        
        # Convert remaining periods to hyphens for better compatibility
        sanitized = sanitized.replace('.', '-')
        
        # Ensure starts and ends with alphanumeric
        sanitized = re.sub(r'^[^a-z0-9]+', '', sanitized)
        sanitized = re.sub(r'[^a-z0-9]+$', '', sanitized)
        
        # Ensure minimum length
        if len(sanitized) < 3:
            sanitized = f"{fallback_prefix}-{sanitized}".lower()
        
        # Ensure maximum length
        if len(sanitized) > 63:
            sanitized = sanitized[:63]
            # Ensure still ends with alphanumeric after truncation
            sanitized = re.sub(r'[^a-z0-9]+$', '', sanitized)
        
        # Final validation - if still invalid, use fallback
        if not re.match(r'^[a-z0-9][a-z0-9.-]*[a-z0-9]$', sanitized) or len(sanitized) < 3:
            sanitized = f"{fallback_prefix}-bucket"
        
        return sanitized

    def generate_presigned_url(self, s3_uri: str, expires_in: int = 600, response_content_type: Optional[str] = None) -> Dict[str, Any]:
        if not s3_uri or not s3_uri.startswith("s3://"):
            raise ValueError("Invalid S3 URI; expected format s3://bucket/key")
        path = s3_uri[5:]
        if "/" not in path:
            raise ValueError("S3 URI missing key path")
        bucket, key = path.split("/", 1)
        params: Dict[str, Any] = {"Bucket": bucket, "Key": key}
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        url = self.s3.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=int(expires_in),
        )
        return {"url": url, "bucket": bucket, "key": key, "expires_in": int(expires_in)}

    def __init__(self):
        self.s3 = aws_client_factory.get_s3_client()
        config_manager = get_unified_config_manager()
        self.region = config_manager.config.aws.region

    def bucket_exists(self, bucket_name: str) -> bool:
        try:
            # HeadBucket returns 200 if the bucket exists and is owned by you
            self.s3.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchBucket", "NotFound"):
                return False
            # For other errors (forbidden, etc.), we surface them
            raise

    def create_bucket(self, bucket_name: str, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a regular S3 bucket (idempotent) and log result to registry.
        Automatically sanitizes bucket name to ensure AWS S3 compliance.

        Returns:
            { "bucket_name": str, "original_name": str, "status": "created"|"already_exists"|"name_conflict", "region": str }
        """
        region = region or self.region
        original_name = bucket_name
        
        # Sanitize bucket name to ensure AWS S3 compliance
        bucket_name = self.sanitize_bucket_name(bucket_name)
        
        if original_name != bucket_name:
            logger.info(f"Sanitized bucket name: '{original_name}' -> '{bucket_name}'")

        # Quick existence check (best-effort)
        try:
            if self.bucket_exists(bucket_name):
                logger.info(f"Regular S3 bucket already exists: {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "original_name": original_name,
                    "status": "already_exists",
                    "region": region
                }
        except ClientError:
            # If head_bucket fails for reasons other than not-found, fall through to create and let it raise
            pass

        # Create bucket; in us-east-1, no CreateBucketConfiguration is required/supported
        params: Dict[str, Any] = {"Bucket": bucket_name}
        if region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}

        try:
            self.s3.create_bucket(**params)
            logger.info(f"Created regular S3 bucket: {bucket_name}")
            # Only log to resource registry when explicitly requested (from resource management UI)
            resource_registry.log_s3_bucket_created(bucket_name=bucket_name, region=region, source="ui")
            return {
                "bucket_name": bucket_name,
                "original_name": original_name,
                "status": "created",
                "region": region
            }
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            # BucketAlreadyOwnedByYou means idempotent success
            if code == "BucketAlreadyOwnedByYou":
                logger.info(f"Regular S3 bucket already owned: {bucket_name}")
                # Do not log to registry for already existing buckets to prevent duplicates
                return {
                    "bucket_name": bucket_name,
                    "original_name": original_name,
                    "status": "already_exists",
                    "region": region
                }
            # BucketAlreadyExists means name conflict in global namespace
            if code == "BucketAlreadyExists":
                logger.warning(f"S3 bucket name conflict (not owned): {bucket_name}")
                return {
                    "bucket_name": bucket_name,
                    "original_name": original_name,
                    "status": "name_conflict",
                    "region": region,
                    "error_code": code
                }
            # InvalidBucketName means our sanitization failed
            if code == "InvalidBucketName":
                logger.error(f"Invalid bucket name after sanitization: {bucket_name}")
                raise ValidationError(f"Unable to create valid bucket name from: {original_name}")
            # Surface other errors
            raise
    def _batch_delete_objects(self, bucket_name: str, identifiers: list[dict[str, str]]) -> int:
        """
        Best-effort batch delete up to 1000 objects or versions at a time.
        Returns number of items reported as Deleted.
        """
        if not identifiers:
            return 0
        deleted_total = 0
        for i in range(0, len(identifiers), 1000):
            chunk = identifiers[i:i + 1000]
            try:
                resp = self.s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={"Objects": chunk, "Quiet": True},
                )
                deleted_total += len(resp.get("Deleted", []))
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                logger.warning(f"DeleteObjects error for bucket={bucket_name} code={code}")
        return deleted_total

    def _empty_bucket_completely(self, bucket_name: str) -> Dict[str, int]:
        """
        Empty a bucket by removing:
          - All object versions and delete markers (for versioned/suspended buckets)
          - All current objects (for unversioned buckets)
        Returns a count summary.
        """
        counts = {"versions": 0, "delete_markers": 0, "objects": 0}

        # Remove versions + delete markers
        try:
            paginator = self.s3.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=bucket_name):
                vers = page.get("Versions", []) or []
                dms = page.get("DeleteMarkers", []) or []
                identifiers: list[dict[str, str]] = []
                for v in vers:
                    counts["versions"] += 1
                    identifiers.append({"Key": v["Key"], "VersionId": v["VersionId"]})
                for m in dms:
                    counts["delete_markers"] += 1
                    identifiers.append({"Key": m["Key"], "VersionId": m["VersionId"]})
                if identifiers:
                    self._batch_delete_objects(bucket_name, identifiers)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            # If bucket is missing, treat as already empty
            if code not in ("NoSuchBucket",):
                logger.warning(f"list_object_versions error for {bucket_name}: {code}")

        # Remove current objects (unversioned or any leftovers)
        try:
            paginator2 = self.s3.get_paginator("list_objects_v2")
            for page in paginator2.paginate(Bucket=bucket_name):
                contents = page.get("Contents", []) or []
                identifiers2 = [{"Key": o["Key"]} for o in contents]
                counts["objects"] += len(identifiers2)
                if identifiers2:
                    self._batch_delete_objects(bucket_name, identifiers2)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("NoSuchBucket",):
                logger.warning(f"list_objects_v2 error for {bucket_name}: {code}")

        return counts

    def delete_bucket(self, bucket_name: str, force_empty: bool = False) -> Dict[str, Any]:
        """
        Delete a regular S3 bucket.

        Args:
            bucket_name: Name of bucket to delete
            force_empty: If True, empties bucket contents (versions, markers, objects) first

        Returns:
            {
              "bucket_name": str,
              "status": "deleted"|"not_found"|"not_empty"|"error",
              "emptied": bool,
              "emptied_counts": {...} (if emptied),
              "error_code": str (optional),
              "message": str (optional)
            }
        """
        emptied_counts: Optional[Dict[str, int]] = None

        if force_empty:
            try:
                emptied_counts = self._empty_bucket_completely(bucket_name)
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                logger.warning(f"Force empty failed for {bucket_name}: {code}")
                return {
                    "bucket_name": bucket_name,
                    "status": "error",
                    "emptied": True,
                    "emptied_counts": emptied_counts or {"versions": 0, "delete_markers": 0, "objects": 0},
                    "error_code": code,
                    "message": "Failed while emptying bucket prior to deletion",
                }

        try:
            self.s3.delete_bucket(Bucket=bucket_name)
            logger.info(f"Deleted S3 bucket: {bucket_name}")
            # Best-effort registry log + clear active if matched
            try:
                resource_registry.log_s3_bucket_deleted(bucket_name=bucket_name)
            except Exception as e:
                logger.warning(f"Failed to update registry after deleting bucket {bucket_name}: {e}")
            out: Dict[str, Any] = {"bucket_name": bucket_name, "status": "deleted", "emptied": bool(force_empty)}
            if emptied_counts is not None:
                out["emptied_counts"] = emptied_counts
            return out

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchBucket", "404", "NotFound"):
                # Consider not_found idempotent; still log deletion to registry
                try:
                    resource_registry.log_s3_bucket_deleted(bucket_name=bucket_name)
                except Exception as e:
                    logger.warning(f"Failed to update registry after bucket not found {bucket_name}: {e}")
                return {"bucket_name": bucket_name, "status": "not_found", "emptied": bool(force_empty)}
            if code == "BucketNotEmpty":
                if not force_empty:
                    return {
                        "bucket_name": bucket_name,
                        "status": "not_empty",
                        "emptied": False,
                        "message": "Bucket contains objects. Enable 'Force empty bucket first'.",
                    }
                # We tried to empty; still not empty -> error
                return {
                    "bucket_name": bucket_name,
                    "status": "error",
                    "emptied": True,
                    "emptied_counts": emptied_counts or {"versions": 0, "delete_markers": 0, "objects": 0},
                    "error_code": code,
                    "message": "Bucket still not empty after force-empty attempt.",
                }
            # Other errors
            return {
                "bucket_name": bucket_name,
                "status": "error",
                "emptied": bool(force_empty),
                "emptied_counts": emptied_counts or {"versions": 0, "delete_markers": 0, "objects": 0},
                "error_code": code,
                "message": "DeleteBucket failed.",
            }

    def download_video_from_url(
        self,
        video_url: str,
        target_bucket: str,
        key_prefix: Optional[str] = None,
        timeout: int = 300,
        chunk_size: int = 8192
    ) -> Dict[str, Any]:
        """
        Download video from URL and upload to S3 bucket.
        
        Args:
            video_url: HTTP/HTTPS URL of video to download
            target_bucket: S3 bucket to upload video to
            key_prefix: Optional S3 key prefix (defaults to 'videos/')
            timeout: Download timeout in seconds
            chunk_size: Download chunk size in bytes
            
        Returns:
            Dictionary with download and upload results
        """
        logger.info(f"Starting video download from URL: {video_url}")
        
        # Validate URL
        parsed_url = urlparse(video_url)
        if not parsed_url.scheme or parsed_url.scheme not in ['http', 'https']:
            raise ValidationError(f"Invalid video URL: {video_url}")
        
        # Generate S3 key
        key_prefix = key_prefix or "videos/"
        if not key_prefix.endswith("/"):
            key_prefix += "/"
        
        # Extract filename from URL or generate one
        filename = Path(parsed_url.path).name
        if not filename or not any(filename.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']):
            filename = f"video_{int(time.time())}.mp4"
        
        s3_key = f"{key_prefix}{filename}"
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
            temp_path = temp_file.name
            
            try:
                # Download video
                logger.info(f"Downloading video to temporary file: {temp_path}")
                start_time = time.time()
                
                response = requests.get(video_url, stream=True, timeout=timeout)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        temp_file.write(chunk)
                        downloaded_size += len(chunk)
                
                download_time = time.time() - start_time
                logger.info(f"Downloaded {downloaded_size} bytes in {download_time:.2f} seconds")
                
                # Upload to S3
                logger.info(f"Uploading video to S3: s3://{target_bucket}/{s3_key}")
                upload_start = time.time()
                
                with open(temp_path, 'rb') as file_data:
                    self.s3.put_object(
                        Bucket=target_bucket,
                        Key=s3_key,
                        Body=file_data,
                        ContentType='video/mp4',
                        Metadata={
                            'source_url': video_url,
                            'download_timestamp': str(int(time.time())),
                            'original_filename': filename
                        }
                    )
                
                upload_time = time.time() - upload_start
                s3_uri = f"s3://{target_bucket}/{s3_key}"
                
                logger.info(f"Successfully uploaded video to {s3_uri} in {upload_time:.2f} seconds")
                
                return {
                    "status": "success",
                    "source_url": video_url,
                    "s3_uri": s3_uri,
                    "bucket": target_bucket,
                    "key": s3_key,
                    "file_size_bytes": downloaded_size,
                    "download_time_sec": round(download_time, 2),
                    "upload_time_sec": round(upload_time, 2),
                    "total_time_sec": round(time.time() - start_time, 2)
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download video from {video_url}: {e}")
                raise ProcessingError(f"Video download failed: {str(e)}")
            
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.error(f"Failed to upload video to S3: {error_code}")
                raise ProcessingError(f"S3 upload failed: {error_code}")
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.warning(f"Failed to delete temporary file: {temp_path}")

    def batch_download_videos(
        self,
        video_urls: List[str],
        target_bucket: str,
        key_prefix: Optional[str] = None,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Download multiple videos from URLs and upload to S3.
        
        Args:
            video_urls: List of video URLs to download
            target_bucket: S3 bucket to upload videos to
            key_prefix: Optional S3 key prefix
            max_concurrent: Maximum concurrent downloads
            
        Returns:
            List of download results
        """
        logger.info(f"Starting batch download of {len(video_urls)} videos")
        
        results = []
        for i, video_url in enumerate(video_urls, 1):
            try:
                logger.info(f"Processing video {i}/{len(video_urls)}: {video_url}")
                result = self.download_video_from_url(
                    video_url=video_url,
                    target_bucket=target_bucket,
                    key_prefix=key_prefix
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to process video {i}: {e}")
                results.append({
                    "status": "failed",
                    "source_url": video_url,
                    "error": str(e)
                })
        
        successful = len([r for r in results if r.get("status") == "success"])
        logger.info(f"Batch download completed: {successful}/{len(video_urls)} successful")
        
        return results

    def get_video_metadata(self, s3_uri: str) -> Dict[str, Any]:
        """
        Get metadata for a video stored in S3.
        
        Args:
            s3_uri: S3 URI of the video
            
        Returns:
            Dictionary with video metadata
        """
        if not s3_uri.startswith("s3://"):
            raise ValidationError("Invalid S3 URI format")
        
        # Parse S3 URI
        path = s3_uri[5:]
        if "/" not in path:
            raise ValidationError("S3 URI missing key path")
        
        bucket, key = path.split("/", 1)
        
        try:
            response = self.s3.head_object(Bucket=bucket, Key=key)
            
            return {
                "s3_uri": s3_uri,
                "bucket": bucket,
                "key": key,
                "size_bytes": response.get('ContentLength', 0),
                "last_modified": response.get('LastModified'),
                "content_type": response.get('ContentType'),
                "metadata": response.get('Metadata', {}),
                "etag": response.get('ETag', '').strip('"')
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                raise ValidationError(f"Video not found: {s3_uri}")
            else:
                raise ProcessingError(f"Failed to get video metadata: {error_code}")