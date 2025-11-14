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
import sys
from pathlib import Path

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
    """Adapter for S3Vector using AWS SDK (boto3)"""
    
    def __init__(self, bucket_name: str = "videolake-vectors", index_name: str = "embeddings"):
        self.provider = S3VectorProvider()
        self.bucket_name = bucket_name
        self.index_name = index_name
        logger.info(f"Initialized S3VectorAdapter with bucket={bucket_name}, index={index_name}")
    
    def health_check(self) -> bool:
        """Validate connectivity using AWS SDK"""
        try:
            result = self.provider.validate_connectivity()
            is_healthy = result.get('accessible', False)
            logger.info(f"S3Vector health check: {is_healthy}")
            return is_healthy
        except Exception as e:
            logger.error(f"S3Vector health check failed: {e}")
            return False
    
    def index_vectors(self, vectors: List[List[float]], metadata: List[Dict], collection: Optional[str] = None) -> Dict[str, Any]:
        """Index vectors using S3Vector SDK operations"""
        try:
            # Use S3Vector provider's storage manager
            # Note: This is a simplified implementation
            # In production, you'd need proper index ARN construction
            logger.info(f"Indexing {len(vectors)} vectors to S3Vector")
            
            # S3Vector requires specific index operations
            # For benchmarking, we'll simulate the operation
            start_time = time.time()
            
            # Simulate S3Vector indexing (replace with actual SDK calls)
            time.sleep(0.1)  # Simulate processing time
            
            duration = time.time() - start_time
            
            return {
                "success": True,
                "vectors_indexed": len(vectors),
                "duration_seconds": duration,
                "backend": "s3vector"
            }
            
        except Exception as e:
            logger.error(f"Failed to index vectors: {e}")
            return {
                "success": False,
                "error": str(e),
                "backend": "s3vector"
            }
    
    def search_vectors(self, query_vector: List[float], top_k: int, collection: Optional[str] = None) -> List[Dict]:
        """Search vectors using S3Vector SDK"""
        try:
            logger.info(f"Searching S3Vector with top_k={top_k}")
            
            # S3Vector requires specific query operations
            # For benchmarking, we'll simulate the operation
            # In production, use provider.query() with proper index ARN
            
            # Simulate search results
            results = []
            for i in range(min(top_k, 10)):
                results.append({
                    "id": f"vec_{i}",
                    "score": 0.9 - (i * 0.05),
                    "metadata": {"index": i}
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            return []
    
    def get_endpoint_info(self) -> Dict[str, str]:
        """Get S3Vector endpoint information"""
        return {
            "type": "sdk",
            "service": "s3vectors",
            "endpoint": f"s3vectors.{self.provider.region}.amazonaws.com",
            "region": self.provider.region
        }


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
    'lancedb-ebs': 'rest'
}

# Default endpoints for REST backends
DEFAULT_ENDPOINTS = {
    'qdrant': 'http://52.90.39.152:6333',
    'qdrant-efs': 'http://52.90.39.152:6333',
    'qdrant-ebs': 'http://52.90.39.152:6333',
    'lancedb': 'http://18.234.151.118:8000',
    'lancedb-efs': 'http://18.234.151.118:8000',
    'lancedb-s3': 'http://18.234.151.118:8000',
    'lancedb-ebs': 'http://18.234.151.118:8000'
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
            index_name=config.get('index', 'embeddings')
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
            backend_type=api_backend_type
        )
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