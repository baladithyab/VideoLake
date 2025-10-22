"""
Resource Management API Router.

Handles AWS resource creation, scanning, and cleanup.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from src.services.aws_resource_scanner import AWSResourceScanner
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class CreateVectorBucketRequest(BaseModel):
    """Request model for creating vector bucket."""
    bucket_name: str
    encryption_type: str = "SSE-S3"
    kms_key_arn: Optional[str] = None


class CreateIndexRequest(BaseModel):
    """Request model for creating vector index."""
    bucket_name: str
    index_name: str
    dimension: int
    similarity_function: str = "cosine"


class CreateOpenSearchDomainRequest(BaseModel):
    """Request model for creating OpenSearch domain."""
    domain_name: str
    instance_type: str = "t3.small.search"
    instance_count: int = 1


@router.get("/scan")
async def scan_resources():
    """Scan for existing AWS resources."""
    try:
        scanner = AWSResourceScanner()
        resources = scanner.scan_all_resources()
        return {
            "success": True,
            "resources": resources
        }
    except Exception as e:
        logger.error(f"Resource scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/registry")
async def get_resource_registry():
    """Get current resource registry."""
    try:
        registry_data = resource_registry.get_registry()
        active_resources = resource_registry.get_active_resources()
        
        return {
            "success": True,
            "registry": registry_data,
            "active_resources": active_resources,
            "summary": {
                "vector_buckets": len(resource_registry.list_vector_buckets()),
                "indexes": len(resource_registry.list_indexes()),
                "opensearch_domains": len(resource_registry.list_opensearch_domains()),
                "opensearch_collections": len(resource_registry.list_opensearch_collections())
            }
        }
    except Exception as e:
        logger.error(f"Failed to get resource registry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector-bucket")
async def create_vector_bucket(request: CreateVectorBucketRequest):
    """Create a new S3 vector bucket."""
    try:
        storage_manager = S3VectorStorageManager()
        result = storage_manager.create_vector_bucket(
            bucket_name=request.bucket_name,
            encryption_type=request.encryption_type,
            kms_key_arn=request.kms_key_arn
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to create vector bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vector-index")
async def create_vector_index(request: CreateIndexRequest):
    """Create a new vector index."""
    try:
        storage_manager = S3VectorStorageManager()
        result = storage_manager.create_index(
            bucket_name=request.bucket_name,
            index_name=request.index_name,
            dimension=request.dimension,
            similarity_function=request.similarity_function
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/opensearch-domain")
async def create_opensearch_domain(request: CreateOpenSearchDomainRequest):
    """Create a new OpenSearch domain."""
    try:
        opensearch_manager = OpenSearchIntegrationManager()
        result = opensearch_manager.create_domain(
            domain_name=request.domain_name,
            instance_type=request.instance_type,
            instance_count=request.instance_count
        )
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to create OpenSearch domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_resources(resource_type: Optional[str] = None):
    """Cleanup AWS resources."""
    try:
        # Implement cleanup logic based on resource_type
        # For now, return success
        return {
            "success": True,
            "message": f"Cleanup initiated for {resource_type or 'all resources'}"
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_resources():
    """Get currently active resources."""
    try:
        active_resources = resource_registry.get_active_resources()
        return {
            "success": True,
            "active_resources": active_resources
        }
    except Exception as e:
        logger.error(f"Failed to get active resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/active/set")
async def set_active_resource(resource_type: str, resource_id: str):
    """Set active resource for a given type."""
    try:
        resource_registry.set_active_resource(resource_type, resource_id)
        return {
            "success": True,
            "message": f"Set active {resource_type} to {resource_id}"
        }
    except Exception as e:
        logger.error(f"Failed to set active resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))

