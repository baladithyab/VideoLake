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
    - Thread-safe using an in-process lock
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
        """
        Log vector bucket creation with deduplication.
        Only adds a new record if the bucket isn't already registered.
        """
        with self._lock:
            data = self._read()
            vector_buckets = data.setdefault("vector_buckets", [])
            
            # Check if bucket is already registered
            for existing_bucket in vector_buckets:
                if (existing_bucket.get("name") == bucket_name and
                    existing_bucket.get("status") == "created"):
                    # Bucket already registered, don't add duplicate
                    return
            
            # Add new record only if not already present
            rec = {
                "name": bucket_name,
                "region": region,
                "encryption": encryption,
                "kms_key_arn": kms_key_arn,
                "source": source,
                "status": "created",
                "created_at": _utc_now_iso(),
            }
            vector_buckets.append(rec)
            self._write(data)

    def log_s3_bucket_created(
        self,
        bucket_name: str,
        region: str,
        source: str = "ui"
    ) -> None:
        """
        Log S3 bucket creation with deduplication.
        Only adds a new record if the bucket isn't already registered.
        """
        with self._lock:
            data = self._read()
            s3_buckets = data.setdefault("s3_buckets", [])
            
            # Check if bucket is already registered
            for existing_bucket in s3_buckets:
                if (existing_bucket.get("name") == bucket_name and
                    existing_bucket.get("status") == "created"):
                    # Bucket already registered, don't add duplicate
                    return
            
            # Add new record only if not already present
            rec = {
                "name": bucket_name,
                "region": region,
                "source": source,
                "status": "created",
                "created_at": _utc_now_iso(),
            }
            s3_buckets.append(rec)
            self._write(data)

    def log_vector_bucket_deleted(
        self,
        bucket_name: str
    ) -> None:
        """
        Remove a vector bucket from the registry completely.
        If the deleted bucket matches active.vector_bucket, clear it.
        """
        with self._lock:
            data = self._read()
            vb_list = data.setdefault("vector_buckets", [])

            # Remove all entries with this bucket name
            data["vector_buckets"] = [
                rec for rec in vb_list
                if rec.get("name") != bucket_name
            ]

            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("vector_bucket") == bucket_name:
                active["vector_bucket"] = None
            self._write(data)

    def log_s3_bucket_deleted(
        self,
        bucket_name: str
    ) -> None:
        """
        Remove a regular S3 bucket from the registry completely.
        Clear active.s3_bucket if it matches.
        """
        with self._lock:
            data = self._read()
            s3_list = data.setdefault("s3_buckets", [])

            # Remove all entries with this bucket name
            data["s3_buckets"] = [
                rec for rec in s3_list
                if rec.get("name") != bucket_name
            ]

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
        index_name: Optional[str] = None
    ) -> None:
        """
        Remove an index from the registry completely.
        Can match by ARN or by bucket_name + index_name.
        """
        with self._lock:
            data = self._read()
            idx_list: List[Dict[str, Any]] = data.setdefault("indexes", [])

            # Remove matching entries
            data["indexes"] = [
                rec for rec in idx_list
                if not (
                    (index_arn and rec.get("arn") == index_arn) or
                    (bucket_name and index_name and
                     rec.get("bucket") == bucket_name and
                     rec.get("name") == index_name)
                )
            ]

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
        collection_name: str
    ) -> None:
        """Remove OpenSearch Serverless collection from the registry completely."""
        with self._lock:
            data = self._read()
            collections = data.setdefault("opensearch_collections", [])

            # Remove all entries with this collection name
            data["opensearch_collections"] = [
                rec for rec in collections
                if rec.get("name") != collection_name
            ]

            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("opensearch_collection") == collection_name:
                active["opensearch_collection"] = None
            self._write(data)

    def log_opensearch_domain_deleted(
        self,
        domain_name: str
    ) -> None:
        """Remove OpenSearch domain from the registry completely."""
        with self._lock:
            data = self._read()
            domains = data.setdefault("opensearch_domains", [])

            # Remove all entries with this domain name
            data["opensearch_domains"] = [
                rec for rec in domains
                if rec.get("name") != domain_name
            ]

            # Clear active selection if matches
            active = data.setdefault("active", {})
            if active.get("opensearch_domain") == domain_name:
                active["opensearch_domain"] = None
            self._write(data)

    def log_opensearch_pipeline_deleted(
        self,
        pipeline_name: str
    ) -> None:
        """Remove OpenSearch Ingestion pipeline from the registry completely."""
        with self._lock:
            data = self._read()
            pipelines = data.setdefault("opensearch_pipelines", [])

            # Remove all entries with this pipeline name
            data["opensearch_pipelines"] = [
                rec for rec in pipelines
                if rec.get("name") != pipeline_name
            ]

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

    def deduplicate_resources(self) -> Dict[str, int]:
        """
        Remove duplicate resource entries, keeping the earliest created entry for each resource.
        
        Returns:
            Dictionary with counts of duplicates removed for each resource type
        """
        with self._lock:
            data = self._read()
            removed_counts = {
                "s3_buckets": 0,
                "vector_buckets": 0,
                "indexes": 0,
                "opensearch_collections": 0,
                "opensearch_domains": 0,
                "opensearch_pipelines": 0,
                "opensearch_indexes": 0,
                "iam_roles": 0
            }
            
            # Deduplicate S3 buckets
            s3_buckets = data.get("s3_buckets", [])
            if s3_buckets:
                seen_buckets = {}
                deduplicated_s3 = []
                
                for bucket in s3_buckets:
                    bucket_name = bucket.get("name")
                    bucket_status = bucket.get("status", "created")
                    
                    if bucket_name and bucket_status == "created":
                        if bucket_name not in seen_buckets:
                            seen_buckets[bucket_name] = bucket
                            deduplicated_s3.append(bucket)
                        else:
                            # Keep the earliest created entry
                            existing_created_at = seen_buckets[bucket_name].get("created_at", "")
                            current_created_at = bucket.get("created_at", "")
                            
                            if current_created_at < existing_created_at:
                                # Replace with earlier entry
                                deduplicated_s3 = [b for b in deduplicated_s3 if b != seen_buckets[bucket_name]]
                                deduplicated_s3.append(bucket)
                                seen_buckets[bucket_name] = bucket
                            
                            removed_counts["s3_buckets"] += 1
                    else:
                        # Keep non-created status entries (deleted, etc.)
                        deduplicated_s3.append(bucket)
                
                data["s3_buckets"] = deduplicated_s3
            
            # Deduplicate vector buckets
            vector_buckets = data.get("vector_buckets", [])
            if vector_buckets:
                seen_vector_buckets = {}
                deduplicated_vector = []
                
                for bucket in vector_buckets:
                    bucket_name = bucket.get("name")
                    bucket_status = bucket.get("status", "created")
                    
                    if bucket_name and bucket_status == "created":
                        if bucket_name not in seen_vector_buckets:
                            seen_vector_buckets[bucket_name] = bucket
                            deduplicated_vector.append(bucket)
                        else:
                            # Keep the earliest created entry
                            existing_created_at = seen_vector_buckets[bucket_name].get("created_at", "")
                            current_created_at = bucket.get("created_at", "")
                            
                            if current_created_at < existing_created_at:
                                # Replace with earlier entry
                                deduplicated_vector = [b for b in deduplicated_vector if b != seen_vector_buckets[bucket_name]]
                                deduplicated_vector.append(bucket)
                                seen_vector_buckets[bucket_name] = bucket
                            
                            removed_counts["vector_buckets"] += 1
                    else:
                        # Keep non-created status entries (deleted, etc.)
                        deduplicated_vector.append(bucket)
                
                data["vector_buckets"] = deduplicated_vector
            
            # Deduplicate indexes by ARN
            indexes = data.get("indexes", [])
            if indexes:
                seen_indexes = {}
                deduplicated_indexes = []
                
                for index in indexes:
                    index_arn = index.get("arn")
                    index_status = index.get("status", "created")
                    
                    if index_arn and index_status == "created":
                        if index_arn not in seen_indexes:
                            seen_indexes[index_arn] = index
                            deduplicated_indexes.append(index)
                        else:
                            removed_counts["indexes"] += 1
                    else:
                        # Keep non-created status entries
                        deduplicated_indexes.append(index)
                
                data["indexes"] = deduplicated_indexes
            
            # Deduplicate OpenSearch collections
            collections = data.get("opensearch_collections", [])
            if collections:
                seen_collections = {}
                deduplicated_collections = []
                
                for collection in collections:
                    collection_name = collection.get("name")
                    collection_status = collection.get("status", "created")
                    
                    if collection_name and collection_status == "created":
                        if collection_name not in seen_collections:
                            seen_collections[collection_name] = collection
                            deduplicated_collections.append(collection)
                        else:
                            removed_counts["opensearch_collections"] += 1
                    else:
                        deduplicated_collections.append(collection)
                
                data["opensearch_collections"] = deduplicated_collections
            
            # Deduplicate OpenSearch domains
            domains = data.get("opensearch_domains", [])
            if domains:
                seen_domains = {}
                deduplicated_domains = []
                
                for domain in domains:
                    domain_name = domain.get("name")
                    domain_status = domain.get("status", "created")
                    
                    if domain_name and domain_status == "created":
                        if domain_name not in seen_domains:
                            seen_domains[domain_name] = domain
                            deduplicated_domains.append(domain)
                        else:
                            removed_counts["opensearch_domains"] += 1
                    else:
                        deduplicated_domains.append(domain)
                
                data["opensearch_domains"] = deduplicated_domains
            
            self._write(data)
            return removed_counts


# Global singleton for easy import
resource_registry = ResourceRegistry()