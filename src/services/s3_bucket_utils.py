"""
S3 Bucket Utility Service

Provides safe, idempotent creation of regular S3 buckets (not S3 Vectors) for use by
the Streamlit UI without performing direct AWS calls in the UI layer.
"""

from __future__ import annotations

from typing import Optional, Dict, Any

from botocore.exceptions import ClientError
from src.utils.aws_clients import aws_client_factory
from src.config import config_manager
from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)


class S3BucketUtilityService:
    """
    Utility service to create/manage regular S3 buckets using the shared client factory
    and to persist audit logs in the resource registry.
    """

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
        self.region = config_manager.aws_config.region

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

        Returns:
            { "bucket_name": str, "status": "created"|"already_exists"|"name_conflict", "region": str }
        """
        region = region or self.region

        # Quick existence check (best-effort)
        try:
            if self.bucket_exists(bucket_name):
                resource_registry.log_s3_bucket_created(bucket_name=bucket_name, region=region, source="ui")
                logger.info(f"Regular S3 bucket already exists: {bucket_name}")
                return {"bucket_name": bucket_name, "status": "already_exists", "region": region}
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
            resource_registry.log_s3_bucket_created(bucket_name=bucket_name, region=region, source="ui")
            return {"bucket_name": bucket_name, "status": "created", "region": region}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            # BucketAlreadyOwnedByYou means idempotent success
            if code == "BucketAlreadyOwnedByYou":
                logger.info(f"Regular S3 bucket already owned: {bucket_name}")
                resource_registry.log_s3_bucket_created(bucket_name=bucket_name, region=region, source="ui")
                return {"bucket_name": bucket_name, "status": "already_exists", "region": region}
            # BucketAlreadyExists means name conflict in global namespace
            if code == "BucketAlreadyExists":
                logger.warning(f"S3 bucket name conflict (not owned): {bucket_name}")
                return {"bucket_name": bucket_name, "status": "name_conflict", "region": region, "error_code": code}
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
                resource_registry.log_s3_bucket_deleted(bucket_name=bucket_name, source="service")
            except Exception:
                pass
            out: Dict[str, Any] = {"bucket_name": bucket_name, "status": "deleted", "emptied": bool(force_empty)}
            if emptied_counts is not None:
                out["emptied_counts"] = emptied_counts
            return out

        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchBucket", "404", "NotFound"):
                # Consider not_found idempotent; still log deletion to registry
                try:
                    resource_registry.log_s3_bucket_deleted(bucket_name=bucket_name, source="service")
                except Exception:
                    pass
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