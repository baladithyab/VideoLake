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
                "opensearch_collection": None,
                "opensearch_domain": None,
            },
            "vector_buckets": [],
            "s3_buckets": [],
            "indexes": [],
            "opensearch_collections": [],
            "opensearch_domains": [],
            "opensearch_pipelines": [],
            "opensearch_indexes": [],
            "iam_roles": []
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

    def get_active_s3_bucket(self) -> Optional[str]:
        """Get active S3 bucket."""
        with self._lock:
            data = self._read()
            return (data.get("active") or {}).get("s3_bucket")

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

    # OpenSearch resource logging methods
    
    def log_opensearch_collection_created(
        self,
        collection_name: str,
        collection_arn: str,
        region: str,
        collection_type: str = "VECTORSEARCH",
        source: str = "opensearch_integration"
    ) -> None:
        """Log creation of OpenSearch Serverless collection."""
        rec = {
            "name": collection_name,
            "arn": collection_arn,
            "region": region,
            "type": collection_type,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("opensearch_collections", [])
            data["opensearch_collections"].append(rec)
            self._write(data)

    def log_opensearch_domain_created(
        self,
        domain_name: str,
        domain_arn: str,
        region: str,
        engine_version: str,
        s3_vectors_enabled: bool = False,
        source: str = "opensearch_integration"
    ) -> None:
        """Log creation or configuration of OpenSearch domain."""
        rec = {
            "name": domain_name,
            "arn": domain_arn,
            "region": region,
            "engine_version": engine_version,
            "s3_vectors_enabled": s3_vectors_enabled,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("opensearch_domains", [])
            data["opensearch_domains"].append(rec)
            self._write(data)

    def log_opensearch_pipeline_created(
        self,
        pipeline_name: str,
        pipeline_arn: str,
        source_index_arn: str,
        target_collection: str,
        region: str,
        source: str = "opensearch_integration"
    ) -> None:
        """Log creation of OpenSearch Ingestion pipeline."""
        rec = {
            "name": pipeline_name,
            "arn": pipeline_arn,
            "source_index_arn": source_index_arn,
            "target_collection": target_collection,
            "region": region,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("opensearch_pipelines", [])
            data["opensearch_pipelines"].append(rec)
            self._write(data)

    def log_opensearch_index_created(
        self,
        index_name: str,
        opensearch_endpoint: str,
        vector_field_name: str,
        vector_dimension: int,
        space_type: str = "cosine",
        engine_type: str = "s3vector",
        source: str = "opensearch_integration"
    ) -> None:
        """Log creation of OpenSearch index with S3 vector engine."""
        rec = {
            "name": index_name,
            "endpoint": opensearch_endpoint,
            "vector_field": vector_field_name,
            "dimensions": vector_dimension,
            "space_type": space_type,
            "engine_type": engine_type,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("opensearch_indexes", [])
            data["opensearch_indexes"].append(rec)
            self._write(data)

    def log_iam_role_created(
        self,
        role_name: str,
        role_arn: str,
        purpose: str,
        region: str,
        source: str = "opensearch_integration"
    ) -> None:
        """Log creation of IAM role for OpenSearch integration."""
        rec = {
            "name": role_name,
            "arn": role_arn,
            "purpose": purpose,  # e.g., "opensearch_ingestion", "cross_service_access"
            "region": region,
            "source": source,
            "status": "created",
            "created_at": _utc_now_iso(),
        }
        with self._lock:
            data = self._read()
            data.setdefault("iam_roles", [])
            data["iam_roles"].append(rec)
            self._write(data)

    # OpenSearch resource deletion methods
    
    def log_opensearch_collection_deleted(
        self,
        collection_name: str,
        source: str = "opensearch_integration"
    ) -> None:
        """Mark OpenSearch Serverless collection as deleted."""
        with self._lock:
            data = self._read()
            collections = data.setdefault("opensearch_collections", [])
            found = False
            for rec in reversed(collections):
                if rec.get("name") == collection_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                collections.append({
                    "name": collection_name,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("opensearch_collection") == collection_name:
                active["opensearch_collection"] = None
            self._write(data)

    def log_opensearch_domain_deleted(
        self,
        domain_name: str,
        source: str = "opensearch_integration"
    ) -> None:
        """Mark OpenSearch domain as deleted."""
        with self._lock:
            data = self._read()
            domains = data.setdefault("opensearch_domains", [])
            found = False
            for rec in reversed(domains):
                if rec.get("name") == domain_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                domains.append({
                    "name": domain_name,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("opensearch_domain") == domain_name:
                active["opensearch_domain"] = None
            self._write(data)

    def log_opensearch_pipeline_deleted(
        self,
        pipeline_name: str,
        source: str = "opensearch_integration"
    ) -> None:
        """Mark OpenSearch Ingestion pipeline as deleted."""
        with self._lock:
            data = self._read()
            pipelines = data.setdefault("opensearch_pipelines", [])
            found = False
            for rec in reversed(pipelines):
                if rec.get("name") == pipeline_name:
                    rec["status"] = "deleted"
                    rec["deleted_at"] = _utc_now_iso()
                    found = True
                    break
            if not found:
                pipelines.append({
                    "name": pipeline_name,
                    "status": "deleted",
                    "source": source,
                    "deleted_at": _utc_now_iso(),
                })
            self._write(data)

    # OpenSearch resource listing methods
    
    def list_opensearch_collections(self) -> List[Dict[str, Any]]:
        """List all OpenSearch Serverless collections."""
        with self._lock:
            return list(self._read().get("opensearch_collections", []))

    def list_opensearch_domains(self) -> List[Dict[str, Any]]:
        """List all OpenSearch domains."""
        with self._lock:
            return list(self._read().get("opensearch_domains", []))

    def list_opensearch_pipelines(self) -> List[Dict[str, Any]]:
        """List all OpenSearch Ingestion pipelines."""
        with self._lock:
            return list(self._read().get("opensearch_pipelines", []))

    def list_opensearch_indexes(self) -> List[Dict[str, Any]]:
        """List all OpenSearch indexes with S3 vector engine."""
        with self._lock:
            return list(self._read().get("opensearch_indexes", []))

    def list_iam_roles(self) -> List[Dict[str, Any]]:
        """List all IAM roles created for OpenSearch integration."""
        with self._lock:
            return list(self._read().get("iam_roles", []))

    # Active selection methods for OpenSearch resources
    
    def set_active_opensearch_collection(self, collection_name: Optional[str]) -> None:
        """Set active OpenSearch Serverless collection."""
        with self._lock:
            data = self._read()
            data.setdefault("active", {})
            data["active"]["opensearch_collection"] = collection_name
            self._write(data)

    def get_active_opensearch_collection(self) -> Optional[str]:
        """Get active OpenSearch Serverless collection."""
        with self._lock:
            data = self._read()
            return (data.get("active") or {}).get("opensearch_collection")

    def set_active_opensearch_domain(self, domain_name: Optional[str]) -> None:
        """Set active OpenSearch domain."""
        with self._lock:
            data = self._read()
            data.setdefault("active", {})
            data["active"]["opensearch_domain"] = domain_name
            self._write(data)

    def get_active_opensearch_domain(self) -> Optional[str]:
        """Get active OpenSearch domain."""
        with self._lock:
            data = self._read()
            return (data.get("active") or {}).get("opensearch_domain")

    def get_active_resources(self) -> Dict[str, Optional[str]]:
        """Get all active resource selections."""
        with self._lock:
            data = self._read()
            active = data.get("active", {})
            return {
                "s3_bucket": active.get("s3_bucket"),
                "vector_bucket": active.get("vector_bucket"),
                "index_arn": active.get("index_arn"),
                "opensearch_collection": active.get("opensearch_collection"),
                "opensearch_domain": active.get("opensearch_domain")
            }

    def set_active_index(self, index_arn: Optional[str]) -> None:
        """Set active vector index (alias for set_active_index_arn)."""
        self.set_active_index_arn(index_arn)

    # Resource summary methods
    
    def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked resources."""
        with self._lock:
            data = self._read()
            return {
                "s3_buckets": len(data.get("s3_buckets", [])),
                "vector_buckets": len(data.get("vector_buckets", [])),
                "vector_indexes": len(data.get("indexes", [])),
                "opensearch_collections": len(data.get("opensearch_collections", [])),
                "opensearch_domains": len(data.get("opensearch_domains", [])),
                "opensearch_pipelines": len(data.get("opensearch_pipelines", [])),
                "opensearch_indexes": len(data.get("opensearch_indexes", [])),
                "iam_roles": len(data.get("iam_roles", [])),
                "last_updated": data.get("updated_at"),
                "active_resources": data.get("active", {})
            }


# Global singleton for easy import
resource_registry = ResourceRegistry()