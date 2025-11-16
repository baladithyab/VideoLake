#!/usr/bin/env python3
"""
Backend adapters for unified benchmarking interface.
Supports both SDK-based (S3Vector) and REST API-based (Qdrant, LanceDB) backends.

This module provides a consistent interface for benchmarking different vector store
backends regardless of their underlying access method (AWS SDK vs REST API).
"""

from abc import ABC, abstractmethod
import time
from typing import List, Dict, Any, Optional
import numpy as np
import requests
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import boto3
from requests_aws4auth import AWS4Auth

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vector_store_s3vector_provider import S3VectorProvider
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BackendAdapter(ABC):
    """Abstract base class for backend adapters"""

    @abstractmethod
    def health_check(self) -> bool:
        """Check if backend is accessible and healthy"""
        pass

    @abstractmethod
    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        """Index vectors into the backend"""
        pass

    @abstractmethod
    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        """Search for similar vectors"""
        pass

    @abstractmethod
    def get_endpoint_info(self) -> Dict[str, str]:
        """Get endpoint information for display"""
        pass


class S3VectorAdapter(BackendAdapter):
    """Adapter for S3Vector using real AWS SDK operations.

    This adapter uses the existing S3VectorStorageManager + S3VectorOperations
    to perform real indexing and search against an S3 Vector index so that
    benchmarks reflect actual service behavior instead of simulated calls.
    """

    def __init__(self, bucket_name: str = "videolake-vectors", index_name: str = "embeddings"):
        self.provider = S3VectorProvider()
        self.bucket_name = bucket_name
        self.index_name = index_name

        # Reuse the provider's storage manager so we benefit from all retry
        # logic, validation and structured logging that already exists in
        # the core Videolake services.
        self.storage_manager = self.provider.storage_manager

        # Use resource-id format (bucket/<bucket>/index/<index>) so the
        # lower-level vector_operations helper can parse it without needing
        # the AWS account ID.
        from src.utils.arn_parser import ARNParser

        self.index_identifier = ARNParser.to_resource_id(bucket_name, index_name)
        self._index_checked = False  # Lazy index existence / creation flag
        logger.info(
            f"Initialized S3VectorAdapter with bucket={bucket_name}, "
            f"index={index_name}, identifier={self.index_identifier}"
        )

    def health_check(self) -> bool:
        """Validate connectivity using AWS SDK.

        This calls the existing validate_connectivity helper which issues a
        lightweight ListVectorBuckets request and reports accessibility.
        """
        try:
            result = self.provider.validate_connectivity()
            is_healthy = result.get("accessible", False)
            logger.info(f"S3Vector health check: {is_healthy}")
            return is_healthy
        except Exception as e:
            logger.error(f"S3Vector health check failed: {e}")
            return False

    def index_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict],
        collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Index vectors using real S3Vector SDK operations.

        The benchmark harness passes plain float vectors + metadata; we map
        that into the S3VectorOperations "vectors_data" shape and then batch
        requests to respect the service limit of 500 vectors per request.
        """
        try:
            if len(vectors) != len(metadata):
                raise ValueError(
                    f"vectors length ({len(vectors)}) does not match metadata length ({len(metadata)})"
                )

            total = len(vectors)
            if total == 0:
                return {
                    "success": True,
                    "vectors_indexed": 0,
                    "duration_seconds": 0.0,
                    "backend": "s3vector",
                    "raw_response": [],
                }

            logger.info(
                f"Indexing {total} vectors to S3Vector index "
                f"{self.index_identifier} (collection={collection})"
            )

            # Lazily ensure the index exists before first write
            if not self._index_checked:
                dim = len(vectors[0])
                logger.info(
                    f"Ensuring S3Vector index exists: bucket={self.bucket_name}, "
                    f"index={self.index_name}, dimension={dim}"
                )
                try:
                    if not self.storage_manager.index_exists(self.bucket_name, self.index_name):
                        create_result = self.storage_manager.create_vector_index(
                            bucket_name=self.bucket_name,
                            index_name=self.index_name,
                            dimensions=dim,
                            distance_metric="cosine",
                            data_type="float32",
                        )
                        logger.info(
                            "S3Vector index creation result: %s",
                            create_result.get("status", "unknown"),
                        )
                except Exception as e:
                    logger.error(f"Failed to ensure S3Vector index exists: {e}", exc_info=True)
                    raise
                finally:
                    self._index_checked = True

            start_time = time.time()

            # Build vectors_data payload expected by S3VectorOperations
            vectors_data: List[Dict[str, Any]] = []
            for i, (vec, meta) in enumerate(zip(vectors, metadata)):
                key = str(meta.get("id", i))
                record = {
                    "key": key,
                    "data": {"float32": vec},
                    "metadata": meta or {},
                }
                vectors_data.append(record)

            # S3Vector currently enforces a hard limit of 500 vectors per
            # put_vectors call. Batch requests to avoid ValidationError.
            max_batch_size = 500
            responses = []
            indexed = 0
            for start in range(0, len(vectors_data), max_batch_size):
                batch = vectors_data[start : start + max_batch_size]
                logger.info(
                    f"Sending batch {start}-{start + len(batch) - 1} "
                    f"of {len(vectors_data)} to S3Vector index {self.index_identifier}"
                )
                response = self.storage_manager.put_vectors(
                    self.index_identifier,
                    batch,
                )
                responses.append(response)
                indexed += len(batch)

            duration = time.time() - start_time

            return {
                "success": True,
                "vectors_indexed": indexed,
                "duration_seconds": duration,
                "backend": "s3vector",
                "raw_response": responses,
            }

        except Exception as e:
            logger.error(f"Failed to index vectors to S3Vector: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "backend": "s3vector",
            }

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int,
        collection: Optional[str] = None,
    ) -> List[Dict]:
        """Search vectors using real S3Vector SDK operations.

        Returns a list of {id, score, metadata} objects to match the common
        adapter interface used by the benchmark harness.
        """
        try:
            logger.info(
                f"Searching S3Vector index {self.index_identifier} "
                f"with top_k={top_k}, collection={collection}"
            )

            result = self.storage_manager.query_vectors(
                self.index_identifier,
                query_vector,
                top_k,
            )

            raw_results = result.get("results", [])
            formatted: List[Dict[str, Any]] = []
            for r in raw_results:
                # S3 Vectors may return different id fields depending on API
                # version; handle the common possibilities.
                vec_id = (
                    r.get("id")
                    or r.get("key")
                    or r.get("vectorId")
                )
                formatted.append(
                    {
                        "id": vec_id,
                        "score": r.get("score"),
                        "metadata": r.get("metadata", {}),
                    }
                )

            return formatted

        except Exception as e:
            logger.error(f"Failed to search vectors in S3Vector: {e}", exc_info=True)
            # For benchmarking failures we return an empty list so the harness
            # can treat it as a failed query without breaking.
            return []

    def get_endpoint_info(self) -> Dict[str, str]:
        """Get S3Vector endpoint information"""
        return {
            "type": "sdk",
            "service": "s3vectors",
            "endpoint": f"s3vectors.{self.provider.region}.amazonaws.com",
            "region": self.provider.region,
        }


class OpenSearchAdapter(BackendAdapter):
    """Adapter for Amazon OpenSearch Service using S3 Vector engine when available.

    This adapter talks to an OpenSearch domain over HTTPS with SigV4 signing and
    uses the standard index and search APIs. When the domain has the S3 Vectors
    engine enabled, it will attempt to create knn_vector fields backed by the
    `s3vector` engine. If that fails (engine disabled), it falls back to regular
    cluster storage so benchmarks can still run.
    """

    def __init__(
        self,
        endpoint: str,
        region: Optional[str] = None,
        vector_field: str = "embedding",
    ) -> None:
        # Normalise endpoint to https://host form
        raw = endpoint.strip()
        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = f"https://{raw}"
        self.endpoint = raw.rstrip("/")
        self.vector_field = vector_field

        parsed = urlparse(self.endpoint)
        host = parsed.netloc
        inferred_region: Optional[str] = None
        if host:
            parts = host.split(".")
            # Example: search-videolake-xxxx.us-east-1.es.amazonaws.com
            # parts = [domain, 'us-east-1', 'es', 'amazonaws', 'com']
            if len(parts) >= 5:
                inferred_region = parts[-4]

        session = boto3.Session()
        self.region = region or inferred_region or session.region_name or "us-east-1"

        credentials = session.get_credentials()
        if credentials is None:
            raise RuntimeError("AWS credentials not found for OpenSearchAdapter")

        self.awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            self.region,
            "es",
            session_token=credentials.token,
        )
        self.session = requests.Session()
        self._index_initialized: Dict[str, bool] = {}

        logger.info(
            "Initialized OpenSearchAdapter at %s (region=%s, vector_field=%s)",
            self.endpoint,
            self.region,
            self.vector_field,
        )


    def _auth(self):
        """Return auth object for OpenSearch requests (SigV4)."""
        return self.awsauth

    def get_endpoint_info(self) -> Dict[str, str]:
        return {
            "type": "rest",
            "backend": "opensearch",
            "endpoint": self.endpoint,
            "region": self.region,
        }

    def health_check(self) -> bool:
        """Check OpenSearch cluster health via _cluster/health."""
        try:
            url = f"{self.endpoint}/_cluster/health"
            response = self.session.get(url, auth=self._auth(), timeout=5)
            ok = response.status_code == 200
            logger.info(
                "OpenSearch health check: %s (status=%s)", ok, response.status_code
            )
            return ok
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"OpenSearch health check failed: {e}")
            return False

    def _ensure_index(self, index_name: str, dimension: int) -> None:
        """Ensure an index with a knn_vector field exists.

        Tries to create the index with the S3 Vectors engine first and falls
        back to the default engine if S3 Vectors is not enabled on the domain.
        """
        try:
            head = self.session.head(
                f"{self.endpoint}/{index_name}", auth=self._auth(), timeout=5
            )
            if head.status_code == 200:
                return
        except Exception as e:
            logger.warning(
                "OpenSearch HEAD index check failed for %s: %s", index_name, e
            )

        mapping = {
            "settings": {
                "index": {
                    "knn": True,
                }
            },
            "mappings": {
                "properties": {
                    self.vector_field: {
                        "type": "knn_vector",
                        "dimension": dimension,
                        "space_type": "cosinesimil",
                        "method": {"engine": "s3vector"},
                    }
                }
            },
        }

        url = f"{self.endpoint}/{index_name}"
        response = self.session.put(
            url,
            json=mapping,
            auth=self._auth(),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if response.status_code in (200, 201):
            logger.info("Created OpenSearch index %s using s3vector engine", index_name)
            return

        # Fallback: try again without the S3 Vectors engine so we can still
        # benchmark the domain even if the preview feature is disabled.
        logger.warning(
            "Failed to create s3vector-backed index %s: %s %s",
            index_name,
            response.status_code,
            response.text,
        )
        mapping["mappings"]["properties"][self.vector_field].pop("method", None)

        fallback = self.session.put(
            url,
            json=mapping,
            auth=self._auth(),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if fallback.status_code in (200, 201):
            logger.info(
                "Created OpenSearch index %s without s3vector engine", index_name
            )
            return

        raise RuntimeError(
            "Failed to create OpenSearch index %s: %s %s; fallback=%s %s"
            % (
                index_name,
                response.status_code,
                response.text,
                fallback.status_code,
                fallback.text,
            )
        )

    def index_vectors(
        self,
        vectors: List[List[float]],
        metadata: List[Dict],
        collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        if len(vectors) != len(metadata):
            return {
                "success": False,
                "error": (
                    f"vectors length ({len(vectors)}) does not match metadata length "
                    f"({len(metadata)})"
                ),
                "backend": "opensearch",
            }

        if not vectors:
            return {
                "success": True,
                "vectors_indexed": 0,
                "duration_seconds": 0.0,
                "backend": "opensearch",
            }

        index_name = collection or "vectors"
        dim = len(vectors[0])

        if not self._index_initialized.get(index_name):
            self._ensure_index(index_name, dim)
            self._index_initialized[index_name] = True

        start_time = time.time()
        actions = []
        for i, (vec, meta) in enumerate(zip(vectors, metadata)):
            doc_id = meta.get("id", i)
            actions.append(
                json.dumps({"index": {"_index": index_name, "_id": str(doc_id)}})
            )
            source = dict(meta)
            source[self.vector_field] = vec
            actions.append(json.dumps(source))

        body = "\n".join(actions) + "\n"
        url = f"{self.endpoint}/_bulk"
        response = self.session.post(
            url,
            data=body,
            auth=self._auth(),
            headers={"Content-Type": "application/x-ndjson"},
            timeout=300,
        )
        duration = time.time() - start_time

        if response.status_code != 200:
            logger.error(
                "OpenSearch bulk index failed: %s %s",
                response.status_code,
                response.text,
            )
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "backend": "opensearch",
            }

        resp_json = response.json()
        items = resp_json.get("items", [])
        failed = sum(
            1 for item in items if item.get("index", {}).get("status", 500) >= 300
        )
        indexed = len(vectors) - failed

        return {
            "success": failed == 0,
            "vectors_indexed": indexed,
            "duration_seconds": duration,
            "backend": "opensearch",
        }

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int,
        collection: Optional[str] = None,
    ) -> List[Dict]:
        index_name = collection or "vectors"
        body = {
            "size": top_k,
            "query": {
                "knn": {
                    self.vector_field: {
                        "vector": query_vector,
                        "k": top_k,
                    }
                }
            },
            "_source": True,
        }

        url = f"{self.endpoint}/{index_name}/_search"
        try:
            response = self.session.post(
                url,
                json=body,
                auth=self._auth(),
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if response.status_code != 200:
                logger.error(
                    "OpenSearch search failed: %s %s",
                    response.status_code,
                    response.text,
                )
                return []

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            results: List[Dict[str, Any]] = []
            for h in hits:
                results.append(
                    {
                        "id": h.get("_id"),
                        "score": h.get("_score"),
                        "metadata": h.get("_source", {}),
                    }
                )
            return results
        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Failed to search OpenSearch: {e}")
            return []



class QdrantAdapter(BackendAdapter):
    """Dedicated adapter for Qdrant with proper API implementation"""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip('/')
        logger.info(f"Initialized QdrantAdapter at {endpoint}")

    def health_check(self) -> bool:
        """Check Qdrant health via REST API"""
        try:
            url = f"{self.endpoint}/"
            response = requests.get(url, timeout=5)
            is_healthy = response.status_code == 200
            logger.info(f"Qdrant health check: {is_healthy}")
            return is_healthy
        except requests.exceptions.RequestException as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        """Index vectors using Qdrant's API"""
        collection_name = collection or 'default'

        try:
            start_time = time.time()

            # Step 1: Create collection if it doesn't exist
            logger.info(f"Creating/updating collection: {collection_name}")
            vector_dim = len(vectors[0]) if vectors else 1024

            create_url = f"{self.endpoint}/collections/{collection_name}"
            create_payload = {
                "vectors": {
                    "size": vector_dim,
                    "distance": "Cosine"
                }
            }

            # Try to create collection (will fail if exists, which is fine)
            try:
                response = requests.put(create_url, json=create_payload, timeout=10)
                if response.status_code in [200, 409]:  # 409 = already exists
                    logger.info(f"Collection ready: {collection_name}")
                else:
                    logger.warning(f"Collection creation returned: {response.status_code}")
            except Exception as e:
                logger.warning(f"Collection creation attempt: {e}")

            # Step 2: Upsert points (vectors with metadata)
            logger.info(f"Upserting {len(vectors)} vectors to collection {collection_name}")

            points = []
            for idx, (vector, meta) in enumerate(zip(vectors, metadata)):
                point = {
                    "id": idx + 1,  # Qdrant requires integer IDs
                    "vector": vector,
                    "payload": meta
                }
                points.append(point)

            upsert_url = f"{self.endpoint}/collections/{collection_name}/points"
            upsert_payload = {
                "points": points
            }

            response = requests.put(upsert_url, json=upsert_payload, timeout=300)
            duration = time.time() - start_time

            if response.status_code == 200:
                result_data = response.json()
                logger.info(f"Qdrant upsert successful: {result_data}")
                return {
                    "success": True,
                    "vectors_indexed": len(vectors),
                    "duration_seconds": duration,
                    "backend": "qdrant"
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Qdrant upsert failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "backend": "qdrant"
                }

        except Exception as e:
            logger.error(f"Failed to index vectors to Qdrant: {e}")
            return {
                "success": False,
                "error": str(e),
                "backend": "qdrant"
            }

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        """Search vectors using Qdrant's API"""
        collection_name = collection or 'default'

        try:
            url = f"{self.endpoint}/collections/{collection_name}/points/search"
            payload = {
                "vector": query_vector,
                "limit": top_k,
                "with_payload": True
            }

            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                results = data.get("result", [])
                # Format results to match common interface
                formatted = []
                for r in results:
                    formatted.append({
                        "id": r.get("id"),
                        "score": r.get("score"),
                        "metadata": r.get("payload", {})
                    })
                return formatted
            else:
                logger.error(f"Qdrant search failed: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Failed to search vectors in Qdrant: {e}")
            return []

    def get_endpoint_info(self) -> Dict[str, str]:
        """Get Qdrant endpoint information"""
        return {
            "type": "rest",
            "backend": "qdrant",
            "endpoint": self.endpoint
        }


class RestAPIAdapter(BackendAdapter):
    """Adapter for REST API backends (LanceDB)"""

    def __init__(self, endpoint: str, backend_type: str):
        self.endpoint = endpoint.rstrip('/')
        self.backend_type = backend_type.lower()

        # Set health check path based on backend type
        if 'qdrant' in self.backend_type:
            self.health_path = '/'  # Qdrant health check is at root
        else:
            self.health_path = '/health'  # LanceDB uses /health

        logger.info(f"Initialized RestAPIAdapter for {backend_type} at {endpoint}")

    def health_check(self) -> bool:
        """Check backend health via REST API"""
        try:
            url = f"{self.endpoint}{self.health_path}"
            logger.info(f"Health check: {url}")

            response = requests.get(url, timeout=5)
            is_healthy = response.status_code == 200

            logger.info(f"{self.backend_type} health check: {is_healthy} (status={response.status_code})")
            return is_healthy

        except requests.exceptions.RequestException as e:
            logger.error(f"{self.backend_type} health check failed: {e}")
            return False

    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        """Index vectors via REST API"""
        try:
            url = f"{self.endpoint}/index"
            logger.info(f"Indexing {len(vectors)} vectors to {url} (collection: {collection})")

            start_time = time.time()

            # Format payload based on backend type
            if 'lancedb' in self.backend_type:
                # LanceDB expects: {table_name, data: [{vector: [...], ...metadata}]}
                data_records = []
                for vector, meta in zip(vectors, metadata):
                    record = {"vector": vector}
                    record.update(meta)
                    data_records.append(record)

                payload = {
                    "table_name": collection or 'default',
                    "data": data_records,
                    "mode": "overwrite"
                }
            elif 'qdrant' in self.backend_type:
                # Qdrant format (to be implemented when Qdrant is accessible)
                payload = {
                    "collection_name": collection or 'default',
                    "vectors": vectors,
                    "metadata": metadata
                }
            else:
                # Generic format
                payload = {
                    "vectors": vectors,
                    "metadata": metadata
                }

            response = requests.post(
                url,
                json=payload,
                timeout=300
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                return {
                    "success": True,
                    "vectors_indexed": len(vectors),
                    "duration_seconds": duration,
                    "backend": self.backend_type
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "backend": self.backend_type
                }

        except Exception as e:
            logger.error(f"Failed to index vectors: {e}")
            return {
                "success": False,
                "error": str(e),
                "backend": self.backend_type
            }

    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        """Search vectors via REST API"""
        try:
            url = f"{self.endpoint}/search"
            logger.info(f"Searching {url} with top_k={top_k}, collection={collection}")

            # Format payload based on backend type
            if 'lancedb' in self.backend_type:
                payload = {
                    "table_name": collection or 'default',
                    "query_vector": query_vector,
                    "limit": top_k
                }
            elif 'qdrant' in self.backend_type:
                payload = {
                    "collection_name": collection or 'default',
                    "vector": query_vector,
                    "top_k": top_k
                }
            else:
                payload = {
                    "vector": query_vector,
                    "top_k": top_k
                }

            response = requests.post(
                url,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                logger.error(f"Search failed: HTTP {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []

    def get_endpoint_info(self) -> Dict[str, str]:
        """Get REST API endpoint information"""
        return {
            "type": "rest",
            "backend": self.backend_type,
            "endpoint": self.endpoint,
            "health_path": self.health_path
        }


# Backend type mapping
BACKEND_TYPES = {
    's3vector': 'sdk',
    's3_vector': 'sdk',
    'qdrant': 'rest',
    'qdrant-efs': 'rest',
    'qdrant-ebs': 'rest',
    'lancedb': 'rest',
    'lancedb-s3': 'rest',
    'lancedb-efs': 'rest',
    'lancedb-ebs': 'rest',
    'opensearch': 'opensearch',
}

# Default endpoints for REST backends (discovered via ECS/EC2 public IPs)
# NOTE: These are convenience defaults for local benchmarks. For production or
# other environments, pass --endpoint/override configs instead of relying on
# hard-coded IPs.
DEFAULT_ENDPOINTS = {
    # Qdrant on ECS Fargate with EFS backend
    'qdrant': 'http://35.173.203.75:6333',
    'qdrant-efs': 'http://35.173.203.75:6333',

    # Qdrant on EC2 with dedicated EBS volume
    'qdrant-ebs': 'http://3.235.99.89:6333',

    # LanceDB on ECS Fargate with EFS backend (canonical "lancedb" deployment)
    'lancedb': 'http://54.92.155.37:8000',
    'lancedb-efs': 'http://54.92.155.37:8000',

    # LanceDB on ECS Fargate with S3-backed storage (cheapest)
    'lancedb-s3': 'http://3.81.132.243:8000',

    # LanceDB on ECS Fargate with provisioned-throughput EFS (EBS-like)
    'lancedb-ebs': 'http://54.164.111.243:8000',

    # OpenSearch domain with S3 Vectors engine
    'opensearch': 'https://search-videolake-jp74yuza4pylhzhut4vimyh43a.us-east-1.es.amazonaws.com',
}


def get_backend_adapter(backend: str, config: Optional[Dict[str, Any]] = None) -> BackendAdapter:
    """
    Factory function to get appropriate backend adapter.

    Args:
        backend: Backend name (e.g., 's3vector', 'qdrant', 'lancedb')
        config: Optional configuration dict with endpoint, bucket, etc.

    Returns:
        Appropriate BackendAdapter instance

    Raises:
        ValueError: If backend is unknown or configuration is invalid
    """
    backend = backend.lower()
    config = config or {}

    backend_type = BACKEND_TYPES.get(backend)
    if not backend_type:
        raise ValueError(f"Unknown backend: {backend}")

    if backend_type == 'sdk':
        # S3Vector SDK-based backend
        return S3VectorAdapter(
            bucket_name=config.get('bucket', 'videolake-vectors'),
            index_name=config.get('index', 'embeddings'),
        )
    elif backend_type == 'rest':
        # REST API-based backend
        endpoint = config.get('endpoint') or DEFAULT_ENDPOINTS.get(backend)
        if not endpoint:
            raise ValueError(f"No endpoint configured for backend: {backend}")

        # Use dedicated adapter for Qdrant
        if 'qdrant' in backend:
            return QdrantAdapter(endpoint=endpoint)

        # Use RestAPIAdapter for other REST backends (LanceDB)
        if 'lancedb' in backend:
            api_backend_type = 'lancedb'
        else:
            api_backend_type = backend

        return RestAPIAdapter(
            endpoint=endpoint,
            backend_type=api_backend_type,
        )
    elif backend_type == 'opensearch':
        endpoint = config.get('endpoint') or DEFAULT_ENDPOINTS.get(backend)
        if not endpoint:
            raise ValueError(f"No endpoint configured for backend: {backend}")
        return OpenSearchAdapter(endpoint=endpoint)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")


def validate_backend_connectivity(backend: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate connectivity to a backend.

    Args:
        backend: Backend name
        config: Optional configuration

    Returns:
        Validation result dictionary
    """
    try:
        adapter = get_backend_adapter(backend, config)
        endpoint_info = adapter.get_endpoint_info()

        start_time = time.time()
        is_healthy = adapter.health_check()
        response_time = (time.time() - start_time) * 1000

        return {
            "backend": backend,
            "accessible": is_healthy,
            "endpoint_info": endpoint_info,
            "response_time_ms": round(response_time, 2),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Backend connectivity validation failed for {backend}: {e}")
        return {
            "backend": backend,
            "accessible": False,
            "error": str(e),
            "timestamp": time.time()
        }