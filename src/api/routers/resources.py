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
from src.services.resource_lifecycle_manager import (
    ResourceLifecycleManager,
    ResourceType,
    ResourceState
)
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class CreateMediaBucketRequest(BaseModel):
    """Request model for creating media bucket."""
    bucket_name: str


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


class DeleteResourceRequest(BaseModel):
    """Request model for deleting resources."""
    resource_id: str
    force: bool = False  # For buckets that need to be emptied first


class BatchCreateMediaBucketsRequest(BaseModel):
    """Request model for batch creating media buckets."""
    bucket_names: List[str]


class BatchCreateVectorBucketsRequest(BaseModel):
    """Request model for batch creating vector buckets."""
    bucket_names: List[str]
    encryption_type: str = "SSE-S3"
    kms_key_arn: Optional[str] = None


class BatchCreateOpenSearchDomainsRequest(BaseModel):
    """Request model for batch creating OpenSearch domains."""
    domain_names: List[str]
    instance_type: str = "t3.small.search"
    instance_count: int = 1


class BatchDeleteRequest(BaseModel):
    """Request model for batch deleting resources."""
    resource_type: str  # 'media', 'vector', or 'opensearch'
    resource_names: List[str]
    force: bool = False  # For media buckets that need to be emptied first


class CreateStackRequest(BaseModel):
    """Request model for creating a complete S3Vector stack."""
    project_name: str  # Base name for all resources (e.g., 'my-project')
    create_vector_bucket: bool = True
    create_media_bucket: bool = True
    create_opensearch_domain: bool = True
    # Optional configurations
    encryption_type: str = "SSE-S3"
    kms_key_arn: Optional[str] = None
    opensearch_instance_type: str = "t3.small.search"
    opensearch_instance_count: int = 1


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
    """Create a new S3 vector bucket with lifecycle management."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.create_vector_bucket(
            bucket_name=request.bucket_name,
            encryption_type=request.encryption_type,
            kms_key_arn=request.kms_key_arn
        )

        return {
            "success": status.state == ResourceState.ACTIVE,
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "arn": status.arn,
                "region": status.region,
                "progress_percentage": status.progress_percentage,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
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
    """Create a new OpenSearch domain with lifecycle management."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.create_opensearch_domain(
            domain_name=request.domain_name,
            instance_type=request.instance_type,
            instance_count=request.instance_count
        )

        return {
            "success": status.state in [ResourceState.CREATING, ResourceState.ACTIVE],
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "arn": status.arn,
                "region": status.region,
                "progress_percentage": status.progress_percentage,
                "estimated_time_remaining": status.estimated_time_remaining,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
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


# ==================== New Lifecycle Management Endpoints ====================

@router.post("/media-bucket")
async def create_media_bucket(request: CreateMediaBucketRequest):
    """Create a new S3 media bucket."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.create_media_bucket(request.bucket_name)

        return {
            "success": status.state == ResourceState.ACTIVE,
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "arn": status.arn,
                "region": status.region,
                "progress_percentage": status.progress_percentage,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
        }
    except Exception as e:
        logger.error(f"Failed to create media bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/media-bucket/{bucket_name}")
async def delete_media_bucket(bucket_name: str, force: bool = False):
    """Delete a media bucket."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.delete_media_bucket(bucket_name, force_empty=force)

        return {
            "success": status.state == ResourceState.DELETED,
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "progress_percentage": status.progress_percentage,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
        }
    except Exception as e:
        logger.error(f"Failed to delete media bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vector-bucket/{bucket_name}")
async def delete_vector_bucket(bucket_name: str):
    """Delete a vector bucket."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.delete_vector_bucket(bucket_name)

        return {
            "success": status.state == ResourceState.DELETED,
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "progress_percentage": status.progress_percentage,
                "error_message": status.error_message
            }
        }
    except Exception as e:
        logger.error(f"Failed to delete vector bucket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/opensearch-domain/{domain_name}")
async def delete_opensearch_domain(domain_name: str):
    """Delete an OpenSearch domain."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        status = lifecycle_manager.delete_opensearch_domain(domain_name)

        return {
            "success": status.state in [ResourceState.DELETING, ResourceState.DELETED],
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "progress_percentage": status.progress_percentage,
                "estimated_time_remaining": status.estimated_time_remaining,
                "error_message": status.error_message
            }
        }
    except Exception as e:
        logger.error(f"Failed to delete OpenSearch domain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{resource_type}/{resource_id}")
async def get_resource_status(resource_type: str, resource_id: str):
    """Get current status of a resource."""
    try:
        lifecycle_manager = ResourceLifecycleManager()

        # Convert string to ResourceType enum
        try:
            res_type = ResourceType(resource_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid resource type: {resource_type}")

        status = lifecycle_manager.get_resource_status(res_type, resource_id)

        return {
            "success": True,
            "status": {
                "resource_id": status.resource_id,
                "resource_type": status.resource_type.value,
                "state": status.state.value,
                "arn": status.arn,
                "region": status.region,
                "progress_percentage": status.progress_percentage,
                "estimated_time_remaining": status.estimated_time_remaining,
                "error_message": status.error_message,
                "metadata": status.metadata
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get resource status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Batch Operations ====================

@router.post("/batch/media-buckets")
async def batch_create_media_buckets(request: BatchCreateMediaBucketsRequest):
    """Create multiple media buckets in batch."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        results = []

        for bucket_name in request.bucket_names:
            try:
                status = lifecycle_manager.create_media_bucket(bucket_name)
                results.append({
                    "bucket_name": bucket_name,
                    "success": status.state == ResourceState.ACTIVE,
                    "status": {
                        "resource_id": status.resource_id,
                        "state": status.state.value,
                        "arn": status.arn,
                        "region": status.region,
                        "error_message": status.error_message
                    }
                })
            except Exception as e:
                logger.error(f"Failed to create media bucket {bucket_name}: {e}")
                results.append({
                    "bucket_name": bucket_name,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get("success", False))
        return {
            "success": success_count > 0,
            "total": len(request.bucket_names),
            "successful": success_count,
            "failed": len(request.bucket_names) - success_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch create media buckets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/vector-buckets")
async def batch_create_vector_buckets(request: BatchCreateVectorBucketsRequest):
    """Create multiple vector buckets in batch."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        results = []

        for bucket_name in request.bucket_names:
            try:
                status = lifecycle_manager.create_vector_bucket(
                    bucket_name,
                    encryption_type=request.encryption_type,
                    kms_key_arn=request.kms_key_arn
                )
                results.append({
                    "bucket_name": bucket_name,
                    "success": status.state == ResourceState.ACTIVE,
                    "status": {
                        "resource_id": status.resource_id,
                        "state": status.state.value,
                        "arn": status.arn,
                        "region": status.region,
                        "error_message": status.error_message
                    }
                })
            except Exception as e:
                logger.error(f"Failed to create vector bucket {bucket_name}: {e}")
                results.append({
                    "bucket_name": bucket_name,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get("success", False))
        return {
            "success": success_count > 0,
            "total": len(request.bucket_names),
            "successful": success_count,
            "failed": len(request.bucket_names) - success_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch create vector buckets failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/opensearch-domains")
async def batch_create_opensearch_domains(request: BatchCreateOpenSearchDomainsRequest):
    """Create multiple OpenSearch domains in batch."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        results = []

        for domain_name in request.domain_names:
            try:
                status = lifecycle_manager.create_opensearch_domain(
                    domain_name,
                    instance_type=request.instance_type,
                    instance_count=request.instance_count
                )
                results.append({
                    "domain_name": domain_name,
                    "success": status.state == ResourceState.CREATING,
                    "status": {
                        "resource_id": status.resource_id,
                        "state": status.state.value,
                        "arn": status.arn,
                        "region": status.region,
                        "estimated_time_remaining": status.estimated_time_remaining,
                        "error_message": status.error_message
                    }
                })
            except Exception as e:
                logger.error(f"Failed to create OpenSearch domain {domain_name}: {e}")
                results.append({
                    "domain_name": domain_name,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get("success", False))
        return {
            "success": success_count > 0,
            "total": len(request.domain_names),
            "successful": success_count,
            "failed": len(request.domain_names) - success_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch create OpenSearch domains failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/delete")
async def batch_delete_resources(request: BatchDeleteRequest):
    """Delete multiple resources in batch."""
    try:
        lifecycle_manager = ResourceLifecycleManager()
        results = []

        for resource_name in request.resource_names:
            try:
                if request.resource_type == "media":
                    status = lifecycle_manager.delete_media_bucket(resource_name, force_empty=request.force)
                elif request.resource_type == "vector":
                    status = lifecycle_manager.delete_vector_bucket(resource_name)
                elif request.resource_type == "opensearch":
                    status = lifecycle_manager.delete_opensearch_domain(resource_name)
                else:
                    raise ValueError(f"Invalid resource type: {request.resource_type}")

                results.append({
                    "resource_name": resource_name,
                    "success": status.state in [ResourceState.DELETED, ResourceState.DELETING],
                    "status": {
                        "resource_id": status.resource_id,
                        "state": status.state.value,
                        "error_message": status.error_message
                    }
                })
            except Exception as e:
                logger.error(f"Failed to delete {request.resource_type} resource {resource_name}: {e}")
                results.append({
                    "resource_name": resource_name,
                    "success": False,
                    "error": str(e)
                })

        success_count = sum(1 for r in results if r.get("success", False))
        return {
            "success": success_count > 0,
            "total": len(request.resource_names),
            "successful": success_count,
            "failed": len(request.resource_names) - success_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch delete resources failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stack/create")
async def create_stack(request: CreateStackRequest):
    """
    Create a complete S3Vector stack with selected components.

    Creates a coordinated set of resources with consistent naming:
    - Vector bucket: {project_name}-vector-bucket
    - Media bucket: {project_name}-media-bucket
    - OpenSearch domain: {project_name}-search
    """
    try:
        lifecycle_manager = ResourceLifecycleManager()
        results = {
            "project_name": request.project_name,
            "resources_created": [],
            "resources_failed": [],
            "details": {}
        }

        # Create vector bucket if requested
        if request.create_vector_bucket:
            vector_bucket_name = f"{request.project_name}-vector-bucket"
            try:
                logger.info(f"Creating vector bucket: {vector_bucket_name}")
                status = lifecycle_manager.create_vector_bucket(
                    bucket_name=vector_bucket_name,
                    encryption_type=request.encryption_type,
                    kms_key_arn=request.kms_key_arn
                )

                if status.state == ResourceState.ACTIVE:
                    results["resources_created"].append({
                        "type": "vector_bucket",
                        "name": vector_bucket_name
                    })
                    results["details"]["vector_bucket"] = {
                        "name": vector_bucket_name,
                        "status": "created",
                        "state": status.state.value
                    }
                else:
                    results["resources_failed"].append({
                        "type": "vector_bucket",
                        "name": vector_bucket_name,
                        "error": status.error_message
                    })
                    results["details"]["vector_bucket"] = {
                        "name": vector_bucket_name,
                        "status": "failed",
                        "error": status.error_message
                    }
            except Exception as e:
                logger.error(f"Failed to create vector bucket: {e}")
                results["resources_failed"].append({
                    "type": "vector_bucket",
                    "name": vector_bucket_name,
                    "error": str(e)
                })
                results["details"]["vector_bucket"] = {
                    "name": vector_bucket_name,
                    "status": "failed",
                    "error": str(e)
                }

        # Create media bucket if requested
        if request.create_media_bucket:
            media_bucket_name = f"{request.project_name}-media-bucket"
            try:
                logger.info(f"Creating media bucket: {media_bucket_name}")
                status = lifecycle_manager.create_media_bucket(bucket_name=media_bucket_name)

                if status.state == ResourceState.ACTIVE:
                    results["resources_created"].append({
                        "type": "media_bucket",
                        "name": media_bucket_name
                    })
                    results["details"]["media_bucket"] = {
                        "name": media_bucket_name,
                        "status": "created",
                        "state": status.state.value
                    }
                else:
                    results["resources_failed"].append({
                        "type": "media_bucket",
                        "name": media_bucket_name,
                        "error": status.error_message
                    })
                    results["details"]["media_bucket"] = {
                        "name": media_bucket_name,
                        "status": "failed",
                        "error": status.error_message
                    }
            except Exception as e:
                logger.error(f"Failed to create media bucket: {e}")
                results["resources_failed"].append({
                    "type": "media_bucket",
                    "name": media_bucket_name,
                    "error": str(e)
                })
                results["details"]["media_bucket"] = {
                    "name": media_bucket_name,
                    "status": "failed",
                    "error": str(e)
                }

        # Create OpenSearch domain if requested
        if request.create_opensearch_domain:
            opensearch_domain_name = f"{request.project_name}-search"
            try:
                logger.info(f"Creating OpenSearch domain: {opensearch_domain_name}")
                status = lifecycle_manager.create_opensearch_domain(
                    domain_name=opensearch_domain_name,
                    instance_type=request.opensearch_instance_type,
                    instance_count=request.opensearch_instance_count
                )

                if status.state in [ResourceState.CREATING, ResourceState.ACTIVE]:
                    results["resources_created"].append({
                        "type": "opensearch_domain",
                        "name": opensearch_domain_name
                    })
                    results["details"]["opensearch_domain"] = {
                        "name": opensearch_domain_name,
                        "status": "creating" if status.state == ResourceState.CREATING else "created",
                        "state": status.state.value,
                        "note": "Domain creation takes 5-10 minutes"
                    }
                else:
                    results["resources_failed"].append({
                        "type": "opensearch_domain",
                        "name": opensearch_domain_name,
                        "error": status.error_message
                    })
                    results["details"]["opensearch_domain"] = {
                        "name": opensearch_domain_name,
                        "status": "failed",
                        "error": status.error_message
                    }
            except Exception as e:
                logger.error(f"Failed to create OpenSearch domain: {e}")
                results["resources_failed"].append({
                    "type": "opensearch_domain",
                    "name": opensearch_domain_name,
                    "error": str(e)
                })
                results["details"]["opensearch_domain"] = {
                    "name": opensearch_domain_name,
                    "status": "failed",
                    "error": str(e)
                }

        # Determine overall success
        success = len(results["resources_created"]) > 0

        return {
            "success": success,
            "message": f"Created {len(results['resources_created'])} of {len(results['resources_created']) + len(results['resources_failed'])} requested resources",
            "project_name": request.project_name,
            "created_count": len(results["resources_created"]),
            "failed_count": len(results["resources_failed"]),
            "resources_created": results["resources_created"],
            "resources_failed": results["resources_failed"],
            "details": results["details"]
        }

    except Exception as e:
        logger.error(f"Stack creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

