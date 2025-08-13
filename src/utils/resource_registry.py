import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResourceRegistry:
    """
    Lightweight JSON-backed registry for created AWS resources (S3 buckets, S3 Vectors buckets, and indexes).
    - Thread-safe (single-process Streamlit) using an in-process lock
    - Append-only by default; supports marking index records as deleted
    - Stores an 'active' selection to simplify UI workflows
    """

    def __init__(self, path: Optional[str] = None):
        # Default path at repo_root/coordination/resource_registry.json
        if path:
            self._path = Path(path)
        else:
            # src/utils/... -> repo root is parents[2]
            self._path = (Path(__file__).resolve().parents[2] / "coordination" / "resource_registry.json")
        self._lock = threading.Lock()
        self._ensure_file()

    def _default_payload(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "updated_at": _utc_now_iso(),
            "active": {
                "index_arn": None,
                "vector_bucket": None,
                "s3_bucket": None,
            },
            "vector_buckets": [],
            "s3_buckets": [],
            "indexes": []
        }

    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._default_payload(), f, indent=2)

    def _read(self) -> Dict[str, Any]:
        with self._path.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Registry root must be an object")
                return data
            except Exception:
                return self._default_payload()

    def _write(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = _utc_now_iso()
        tmp = self._path.with_suffix(".tmp.json")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self._path)

    def get_registry(self) -> Dict[str, Any]:
        with self._lock:
            return self._read()

    # Active selection helpers
    def set_active_index_arn(self, arn: Optional[str]) -> None:
        with self._lock:
            data = self._read()
            data.setdefault("active", {})
            data["active"]["index_arn"] = arn
            self._write(data)

    def get_active_index_arn(self) -> Optional[str]:
        with self._lock:
            data = self._read()
            return (data.get("active") or {}).get("index_arn")

    def set_active_vector_bucket(self, bucket: Optional[str]) -> None:
        with self._lock:
            data = self._read()
            data.setdefault("active", {})
            data["active"]["vector_bucket"] = bucket
            self._write(data)

    def set_active_s3_bucket(self, bucket: Optional[str]) -> None:
        with self._lock:
            data = self._read()
            data.setdefault("active", {})
            data["active"]["s3_bucket"] = bucket
            self._write(data)

    # Creation logs
    def log_vector_bucket_created(
        self,
        bucket_name: str,
        region: str,
        encryption: str = "SSE-S3",
        kms_key_arn: Optional[str] = None,
        source: str = "ui"
    ) -> None:
        rec = {
            "name": bucket_name,
            "region": region,
            "encryption": encryption,
            "kms_key_arn": kms_key_arn,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("vector_buckets", [])
            data["vector_buckets"].append(rec)
            self._write(data)

    def log_s3_bucket_created(
        self,
        bucket_name: str,
        region: str,
        source: str = "ui"
    ) -> None:
        rec = {
            "name": bucket_name,
            "region": region,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("s3_buckets", [])
            data["s3_buckets"].append(rec)
            self._write(data)

    def log_vector_bucket_deleted(
        self,
        bucket_name: str,
        source: str = "ui"
    ) -> None:
        """
        Mark a vector bucket as deleted in the registry. If a creation record exists,
        update its status to 'deleted' and add deleted_at. Otherwise, append a minimal
        deletion record. If the deleted bucket matches active.vector_bucket, clear it.
        """
        with self._lock:
            data = self._read()
            vb_list = data.setdefault("vector_buckets", [])
            found = False
            for rec in reversed(vb_list):
                if rec.get("name") == bucket_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                vb_list.append({
                    "name": bucket_name,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("vector_bucket") == bucket_name:
                active["vector_bucket"] = None
            self._write(data)

    def log_s3_bucket_deleted(
        self,
        bucket_name: str,
        source: str = "ui"
    ) -> None:
        """
        Mark a regular S3 bucket as deleted in the registry. If an existing record is present,
        update it; otherwise append a deletion record. Clear active.s3_bucket if it matches.
        """
        with self._lock:
            data = self._read()
            s3_list = data.setdefault("s3_buckets", [])
            found = False
            for rec in reversed(s3_list):
                if rec.get("name") == bucket_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                s3_list.append({
                    "name": bucket_name,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            active = data.setdefault("active", {})
            if active.get("s3_bucket") == bucket_name:
                active["s3_bucket"] = None
            self._write(data)
    def log_index_created(
        self,
        bucket_name: str,
        index_name: str,
        arn: str,
        dimensions: int,
        distance_metric: str,
        source: str = "ui"
    ) -> None:
        rec = {
            "bucket": bucket_name,
            "name": index_name,
            "arn": arn,
            "dimensions": dimensions,
            "distance_metric": distance_metric,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("indexes", [])
            data["indexes"].append(rec)
            self._write(data)

    def log_index_deleted(
        self,
        *,
        index_arn: Optional[str] = None,
        bucket_name: Optional[str] = None,
        index_name: Optional[str] = None,
        source: str = "ui"
    ) -> None:
        with self._lock:
            data = self._read()
            idx_list: List[Dict[str, Any]] = data.setdefault("indexes", [])
            # Try to find existing
            found = False
            for rec in idx_list:
                if index_arn and rec.get("arn") == index_arn:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
                if bucket_name and index_name and rec.get("bucket") == bucket_name and rec.get("name") == index_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                # Append a deletion record if not present
                idx_list.append({
                    "bucket": bucket_name,
                    "name": index_name,
                    "arn": index_arn,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            self._write(data)

    # Convenience filters
    def list_indexes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._read().get("indexes", []))

    def list_vector_buckets(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._read().get("vector_buckets", []))

    def list_s3_buckets(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._read().get("s3_buckets", []))


# Global singleton for easy import
resource_registry = ResourceRegistry()