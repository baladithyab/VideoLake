"""
Resource Management API Router - READ-ONLY

⚠️  TERRAFORM-FIRST ARCHITECTURE ⚠️

This router provides READ-ONLY access to deployed infrastructure.
ALL infrastructure creation, modification, and deletion is handled
EXCLUSIVELY through Terraform.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE ENDPOINTS (All Read-Only or Workflow Operations):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Resource Viewing:
  - GET  /deployed-resources-tree      View deployed infrastructure from terraform.tfstate
  - GET  /scan                          Scan for existing AWS resources
  - GET  /registry                      View resource registry
  - GET  /active                        View currently active resources

🏥 Health Checks:
  - GET  /validate-backend/{type}       Check backend connectivity
  - POST /validate-backends             Batch validate multiple backends

📦 Vector Index Operations:
  - GET  /vector-indexes/{bucket}       List vector indexes in bucket
  - GET  /vector-index/status           Get detailed index status
  - POST /store-embeddings-to-index     Store embeddings (workflow, not CRUD)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NO POST/PUT/DELETE ENDPOINTS FOR INFRASTRUCTURE MANAGEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

To create, modify, or delete infrastructure resources:
    cd terraform && terraform apply

To destroy infrastructure:
    cd terraform && terraform destroy

For more information, see:
  - terraform/README.md
  - terraform/MIGRATION_GUIDE.md
  - docs/DEPLOYMENT_GUIDE.md
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
import logging

from src.services.aws_resource_scanner import AWSResourceScanner
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.core.dependencies import get_storage_manager
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ==================== Request Models for Workflow Operations ====================

class StoreEmbeddingsToIndexRequest(BaseModel):
    """Request model for storing embeddings to index."""
    job_id: str = Field(..., description="Processing job ID", min_length=1)
    index_arn: str = Field(..., description="S3 Vector index ARN")
    backend: str = Field(default="s3_vector", description="Backend type (s3_vector, opensearch, etc.)")

    @validator('backend')
    def validate_backend(cls, v):
        valid_backends = ["s3_vector", "opensearch", "qdrant", "lancedb"]
        if v not in valid_backends:
            raise ValueError(f"Invalid backend. Must be one of: {', '.join(valid_backends)}")
        return v


class VectorIndexInfo(BaseModel):
    """Vector index information model."""
    index_name: str
    index_arn: str
    dimension: int
    distance_metric: str
    data_type: str
    vector_count: int = 0
    status: str
    created_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


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


# ==================== DEPRECATED/REMOVED INFRASTRUCTURE ENDPOINTS ====================
# The following endpoints have been REMOVED as part of the Terraform-first architecture.
# All infrastructure creation, modification, and deletion must be done via Terraform.
#
# Previously removed POST/PUT/DELETE endpoints:
# - POST   /media-bucket                              (create media bucket)
# - POST   /vector-bucket                             (create vector bucket)
# - POST   /vector-index                              (create vector index)
# - POST   /opensearch-domain                         (create OpenSearch domain)
# - DELETE /media-bucket/{bucket_name}                (delete media bucket)
# - DELETE /vector-bucket/{bucket_name}               (delete vector bucket)
# - DELETE /opensearch-domain/{domain_name}           (delete OpenSearch domain)
# - DELETE /cleanup                                   (cleanup/delete resources)
# - POST   /active/set                                (modify resource registry state)
# - POST   /batch/media-buckets                       (batch create media buckets)
# - POST   /batch/vector-buckets                      (batch create vector buckets)
# - POST   /batch/opensearch-domains                  (batch create OpenSearch domains)
# - POST   /batch/delete                              (batch delete resources)
# - POST   /stack/create                              (create complete stack)
# - GET    /status/{resource_type}/{resource_id}      (get resource status)
#
# For infrastructure management:
#   Create/Modify:  cd terraform && terraform apply
#   Destroy:        cd terraform && terraform destroy


@router.get("/active")
async def get_active_resources():
    """
    Get currently active resources (READ-ONLY).
    
    Returns the list of resources currently marked as active in the resource registry.
    This is a read-only operation - use Terraform to manage actual infrastructure.
    """
    try:
        active_resources = resource_registry.get_active_resources()
        return {
            "success": True,
            "active_resources": active_resources
        }
    except Exception as e:
        logger.error(f"Failed to get active resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Backend Connectivity Validation ====================

@router.get("/validate-backend/{backend_type}")
async def validate_backend_connectivity(backend_type: str):
    """
    Validate that a vector store backend is accessible.
    
    Tests actual connectivity to the backend service and returns
    detailed health information including response time.
    
    Args:
        backend_type: Type of backend (s3_vector, opensearch, qdrant, lancedb)
    
    Returns:
        Connectivity validation result with:
        - accessible: Whether backend is accessible
        - endpoint: Backend endpoint/URL
        - response_time_ms: Response time in milliseconds
        - health_status: Health status (healthy, degraded, unhealthy)
        - error_message: Error message if not accessible
        - details: Additional backend-specific details
    """
    try:
        from src.services.vector_store_provider import (
            VectorStoreType,
            VectorStoreProviderFactory
        )
        
        # Map string to VectorStoreType enum
        backend_type_lower = backend_type.lower()
        type_map = {
            "s3_vector": VectorStoreType.S3_VECTOR,
            "opensearch": VectorStoreType.OPENSEARCH,
            "qdrant": VectorStoreType.QDRANT,
            "lancedb": VectorStoreType.LANCEDB
        }
        
        if backend_type_lower not in type_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid backend type: {backend_type}. "
                       f"Valid types: {', '.join(type_map.keys())}"
            )
        
        store_type = type_map[backend_type_lower]
        
        # Check if provider is available
        if not VectorStoreProviderFactory.is_provider_available(store_type):
            raise HTTPException(
                status_code=400,
                detail=f"Provider not available for backend type: {backend_type}"
            )
        
        # Create provider and validate connectivity
        provider = VectorStoreProviderFactory.create_provider(store_type)
        
        # Add timeout to prevent hanging
        import asyncio
        try:
            validation_result = await asyncio.wait_for(
                asyncio.to_thread(provider.validate_connectivity),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            validation_result = {
                "accessible": False,
                "endpoint": "unknown",
                "response_time_ms": 5000.0,
                "health_status": "unhealthy",
                "error_message": "Validation timed out after 5 seconds",
                "details": {
                    "backend_type": backend_type
                }
            }
        
        return {
            "success": validation_result["accessible"],
            "backend_type": backend_type,
            "validation": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backend validation failed for {backend_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ValidateBackendsRequest(BaseModel):
    """Request model for batch backend validation."""
    backend_types: List[str] = Field(..., description="List of backend types to validate")


@router.post("/validate-backends")
async def validate_multiple_backends(request: ValidateBackendsRequest):
    """
    Validate multiple vector store backends in parallel.
    
    Tests connectivity to multiple backends simultaneously and returns
    results for each. Useful for checking which backends are available
    before processing workflows.
    
    Args:
        request: Request containing list of backend types to validate
    
    Returns:
        Dictionary with validation results for each backend:
        - accessible: Whether backend is accessible
        - endpoint: Backend endpoint/URL
        - response_time_ms: Response time in milliseconds
        - health_status: Health status (healthy, degraded, unhealthy)
        - error_message: Error message if not accessible
    """
    try:
        from src.services.vector_store_provider import (
            VectorStoreType,
            VectorStoreProviderFactory
        )
        import asyncio
        
        # Map string to VectorStoreType enum
        type_map = {
            "s3_vector": VectorStoreType.S3_VECTOR,
            "opensearch": VectorStoreType.OPENSEARCH,
            "qdrant": VectorStoreType.QDRANT,
            "lancedb": VectorStoreType.LANCEDB
        }
        
        results = {}
        validation_tasks = []
        
        async def validate_backend(backend_type: str):
            """Validate a single backend with timeout."""
            backend_type_lower = backend_type.lower()
            
            if backend_type_lower not in type_map:
                return backend_type, {
                    "accessible": False,
                    "endpoint": "unknown",
                    "response_time_ms": 0.0,
                    "health_status": "unhealthy",
                    "error_message": f"Invalid backend type: {backend_type}"
                }
            
            store_type = type_map[backend_type_lower]
            
            # Check if provider is available
            if not VectorStoreProviderFactory.is_provider_available(store_type):
                return backend_type, {
                    "accessible": False,
                    "endpoint": "unknown",
                    "response_time_ms": 0.0,
                    "health_status": "unhealthy",
                    "error_message": f"Provider not available for {backend_type}"
                }
            
            try:
                provider = VectorStoreProviderFactory.create_provider(store_type)
                
                # Validate with timeout
                validation_result = await asyncio.wait_for(
                    asyncio.to_thread(provider.validate_connectivity),
                    timeout=5.0
                )
                return backend_type, validation_result
                
            except asyncio.TimeoutError:
                return backend_type, {
                    "accessible": False,
                    "endpoint": "unknown",
                    "response_time_ms": 5000.0,
                    "health_status": "unhealthy",
                    "error_message": "Validation timed out after 5 seconds"
                }
            except Exception as e:
                logger.error(f"Validation failed for {backend_type}: {e}")
                return backend_type, {
                    "accessible": False,
                    "endpoint": "unknown",
                    "response_time_ms": 0.0,
                    "health_status": "unhealthy",
                    "error_message": str(e)
                }
        
        # Validate all backends in parallel
        validation_tasks = [
            validate_backend(backend_type)
            for backend_type in request.backend_types
        ]
        
        validation_results = await asyncio.gather(*validation_tasks)
        
        # Build results dictionary
        for backend_type, validation_result in validation_results:
            results[backend_type] = validation_result
        
        # Count accessible backends
        accessible_count = sum(
            1 for result in results.values()
            if result.get("accessible", False)
        )
        
        return {
            "success": accessible_count > 0,
            "total_backends": len(request.backend_types),
            "accessible_backends": accessible_count,
            "inaccessible_backends": len(request.backend_types) - accessible_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch backend validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Terraform State Resource Extraction ====================

async def _get_media_buckets_from_tfstate(parser) -> List[Dict[str, Any]]:
    """
    Extract media buckets from Terraform state.
    
    Looks for aws_s3_bucket resources from module.shared_bucket.
    """
    buckets = []
    
    try:
        # Get all S3 bucket resources from shared_bucket module
        for resource in parser.resources:
            if (resource.type == 'aws_s3_bucket' and
                resource.module and 'shared_bucket' in resource.module):
                
                bucket_name = resource.attributes.get('bucket', resource.attributes.get('id'))
                region = resource.attributes.get('region', 'us-east-1')
                arn = resource.attributes.get('arn', f"arn:aws:s3:::{bucket_name}")
                
                buckets.append({
                    "type": "s3_bucket",
                    "name": bucket_name,
                    "arn": arn,
                    "region": region,
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name
                    }
                })
                
    except Exception as e:
        logger.warning(f"Failed to extract media buckets from tfstate: {e}")
    
    return buckets


async def _get_s3vector_backend_from_tfstate(parser) -> Dict[str, Any]:
    """
    Extract S3 Vector backend info from Terraform state.
    
    S3 Vector buckets are created via null_resource with AWS CLI in module.s3vector[0].
    """
    backend = {
        "type": "s3vector",
        "name": "S3 Vectors",
        "status": "not_deployed",
        "children": []
    }
    
    try:
        # Look for null_resource in s3vector module
        s3vector_resources = [
            r for r in parser.resources
            if r.module and 's3vector' in r.module
        ]
        
        if not s3vector_resources:
            return backend
        
        backend["status"] = "deployed"
        
        # Extract bucket information from null_resource triggers or outputs
        for resource in s3vector_resources:
            if resource.type == 'null_resource' and 'bucket' in resource.name:
                triggers = resource.attributes.get('triggers', {})
                bucket_name = triggers.get('bucket_name')
                
                if bucket_name:
                    backend["children"].append({
                        "type": "vector_bucket",
                        "name": bucket_name,
                        "status": "active",
                        "metadata": {
                            "source": "terraform",
                            "tfstate_resource": resource.full_name
                        }
                    })
        
    except Exception as e:
        logger.warning(f"Failed to extract S3 Vector backend from tfstate: {e}")
    
    return backend


async def _get_opensearch_backend_from_tfstate(parser) -> Dict[str, Any]:
    """
    Extract OpenSearch backend info from Terraform state.
    
    Looks for aws_opensearch_domain resources from module.opensearch[0].
    """
    backend = {
        "type": "opensearch",
        "name": "OpenSearch",
        "status": "not_deployed",
        "children": []
    }
    
    try:
        # Look for OpenSearch domains in opensearch module
        for resource in parser.resources:
            if (resource.type == 'aws_opensearch_domain' and
                resource.module and 'opensearch' in resource.module):
                
                backend["status"] = "deployed"
                
                domain_name = resource.attributes.get('domain_name', resource.name)
                endpoint = resource.attributes.get('endpoint')
                arn = resource.attributes.get('arn')
                region = resource.attributes.get('region', 'us-east-1')
                
                backend["children"].append({
                    "type": "opensearch_domain",
                    "name": domain_name,
                    "arn": arn,
                    "endpoint": endpoint,
                    "region": region,
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name
                    }
                })
        
    except Exception as e:
        logger.warning(f"Failed to extract OpenSearch backend from tfstate: {e}")
    
    return backend


async def _get_qdrant_backend_from_tfstate(parser) -> Dict[str, Any]:
    """
    Extract Qdrant backend info from Terraform state.
    
    Looks for aws_instance resources from module.qdrant[0].
    """
    backend = {
        "type": "qdrant",
        "name": "Qdrant",
        "status": "not_deployed",
        "children": []
    }
    
    try:
        # Look for EC2 instances in qdrant module
        for resource in parser.resources:
            if (resource.type == 'aws_instance' and
                resource.module and 'qdrant' in resource.module):
                
                backend["status"] = "deployed"
                
                instance_id = resource.attributes.get('id')
                public_ip = resource.attributes.get('public_ip')
                endpoint = f"http://{public_ip}:6333" if public_ip else None
                
                backend["children"].append({
                    "type": "qdrant_instance",
                    "name": f"qdrant-{instance_id[-8:]}",
                    "instance_id": instance_id,
                    "endpoint": endpoint,
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name,
                        "public_ip": public_ip
                    }
                })
        
    except Exception as e:
        logger.warning(f"Failed to extract Qdrant backend from tfstate: {e}")
    
    return backend


async def _get_lancedb_backend_from_tfstate(parser) -> Dict[str, Any]:
    """
    Extract LanceDB backend info from Terraform state.
    
    Looks for S3/EFS/EBS resources from module.lancedb_*[0].
    """
    backend = {
        "type": "lancedb",
        "name": "LanceDB",
        "status": "not_deployed",
        "children": []
    }
    
    try:
        # Look for LanceDB S3 backends
        for resource in parser.resources:
            if (resource.type == 'aws_s3_bucket' and
                resource.module and 'lancedb' in resource.module):
                
                backend["status"] = "deployed"
                
                bucket_name = resource.attributes.get('bucket', resource.attributes.get('id'))
                arn = resource.attributes.get('arn')
                
                backend["children"].append({
                    "type": "lancedb_s3",
                    "name": bucket_name,
                    "arn": arn,
                    "backend_type": "s3",
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name,
                        "connection_uri": f"s3://{bucket_name}/"
                    }
                })
        
        # Look for LanceDB EFS backends
        for resource in parser.resources:
            if (resource.type == 'aws_efs_file_system' and
                resource.module and 'lancedb' in resource.module):
                
                backend["status"] = "deployed"
                
                efs_id = resource.attributes.get('id')
                
                backend["children"].append({
                    "type": "lancedb_efs",
                    "name": f"efs-{efs_id[-8:]}",
                    "filesystem_id": efs_id,
                    "backend_type": "efs",
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name
                    }
                })
        
        # Look for LanceDB EBS backends
        for resource in parser.resources:
            if (resource.type == 'aws_ebs_volume' and
                resource.module and 'lancedb' in resource.module):
                
                backend["status"] = "deployed"
                
                volume_id = resource.attributes.get('id')
                
                backend["children"].append({
                    "type": "lancedb_ebs",
                    "name": f"ebs-{volume_id[-8:]}",
                    "volume_id": volume_id,
                    "backend_type": "ebs",
                    "status": "active",
                    "metadata": {
                        "source": "terraform",
                        "tfstate_resource": resource.full_name
                    }
                })
        
    except Exception as e:
        logger.warning(f"Failed to extract LanceDB backend from tfstate: {e}")
    
    return backend


async def _add_health_check_to_backend(node: Dict[str, Any], backend_type: str) -> Dict[str, Any]:
    """
    Add health check information to a backend node.
    
    Runs connectivity validation with 3-second timeout and adds:
    - connectivity: "healthy", "degraded", "unhealthy", "timeout", "error", "unavailable"
    - endpoint: Backend endpoint URL
    - response_time_ms: Response time in milliseconds
    - health_details: Additional health information
    """
    from src.services.vector_store_provider import (
        VectorStoreType,
        VectorStoreProviderFactory
    )
    import asyncio
    
    # Map backend type string to VectorStoreType enum
    backend_map = {
        "s3vector": VectorStoreType.S3_VECTOR,
        "opensearch": VectorStoreType.OPENSEARCH,
        "qdrant": VectorStoreType.QDRANT,
        "lancedb": VectorStoreType.LANCEDB
    }
    
    store_type = backend_map.get(backend_type)
    if not store_type:
        node["connectivity"] = "unavailable"
        return node
    
    try:
        # Check if provider is available
        if not VectorStoreProviderFactory.is_provider_available(store_type):
            node["connectivity"] = "unavailable"
            return node
        
        # Create provider and validate connectivity
        provider = VectorStoreProviderFactory.create_provider(store_type)
        
        # Run validation with 3-second timeout
        validation_result = await asyncio.wait_for(
            asyncio.to_thread(provider.validate_connectivity),
            timeout=3.0
        )
        
        # Add health check fields to node
        if validation_result.get("accessible"):
            node["connectivity"] = validation_result.get("health_status", "healthy")
        else:
            node["connectivity"] = "unavailable"
        
        node["endpoint"] = validation_result.get("endpoint")
        node["response_time_ms"] = validation_result.get("response_time_ms")
        node["health_details"] = validation_result.get("details", {})
        
    except asyncio.TimeoutError:
        node["connectivity"] = "timeout"
        logger.warning(f"Health check timeout for {backend_type}")
    except Exception as e:
        node["connectivity"] = "error"
        node["health_details"] = {"error": str(e)}
        logger.warning(f"Health check failed for {backend_type}: {e}")
    
    return node


@router.get("/deployed-resources-tree")
async def get_deployed_resources_tree():
    """
    Get hierarchical view of deployed resources from Terraform state.
    
    Reads terraform/terraform.tfstate and parses deployed infrastructure to
    provide a true view of what's actually deployed via Terraform.
    
    Returns tree structure showing:
    - Shared media buckets (from module.shared_bucket)
    - Vector backends:
      - S3 Vector (from module.s3vector[0])
      - OpenSearch (from module.opensearch[0])
      - Qdrant (from module.qdrant[0])
      - LanceDB (from module.lancedb_*[0])
    
    Each backend includes health check information with connectivity status.
    """
    import os
    from pathlib import Path
    from src.utils.terraform_state_parser import TerraformStateParser
    import asyncio
    
    tfstate_path = Path("terraform/terraform.tfstate")
    
    try:
        # Check if tfstate exists
        if not tfstate_path.exists():
            return {
                "success": False,
                "message": "No terraform state found. Run 'terraform apply' first.",
                "tree": None
            }
        
        # Check if tfstate is empty
        if tfstate_path.stat().st_size == 0:
            return {
                "success": True,
                "message": "Terraform state is empty. No resources have been deployed yet.",
                "tree": {
                    "shared_resources": {
                        "type": "shared",
                        "name": "Shared Resources",
                        "status": "empty",
                        "children": []
                    },
                    "vector_backends": []
                },
                "metadata": {
                    "tfstate_path": str(tfstate_path),
                    "tfstate_modified": None,
                    "total_resources": 0
                }
            }
        
        # Parse Terraform state
        try:
            parser = TerraformStateParser(str(tfstate_path))
        except Exception as e:
            logger.error(f"Failed to parse Terraform state: {e}")
            return {
                "success": False,
                "message": f"Failed to parse Terraform state: {str(e)}",
                "tree": None
            }
        
        # Extract resources from tfstate
        media_buckets = await _get_media_buckets_from_tfstate(parser)
        s3vector_backend = await _get_s3vector_backend_from_tfstate(parser)
        opensearch_backend = await _get_opensearch_backend_from_tfstate(parser)
        qdrant_backend = await _get_qdrant_backend_from_tfstate(parser)
        lancedb_backend = await _get_lancedb_backend_from_tfstate(parser)
        
        # Add health checks to backends (run in parallel)
        health_check_tasks = [
            _add_health_check_to_backend(s3vector_backend, "s3vector"),
            _add_health_check_to_backend(opensearch_backend, "opensearch"),
            _add_health_check_to_backend(qdrant_backend, "qdrant"),
            _add_health_check_to_backend(lancedb_backend, "lancedb")
        ]
        
        await asyncio.gather(*health_check_tasks, return_exceptions=True)
        
        # Build tree structure
        tree = {
            "shared_resources": {
                "type": "shared",
                "name": "Shared Resources",
                "status": "active" if media_buckets else "empty",
                "children": media_buckets
            },
            "vector_backends": [
                s3vector_backend,
                opensearch_backend,
                qdrant_backend,
                lancedb_backend
            ]
        }
        
        # Calculate total resources
        total_resources = len(media_buckets)
        for backend in tree["vector_backends"]:
            total_resources += len(backend.get("children", []))
        
        # Get tfstate modification time
        tfstate_modified = tfstate_path.stat().st_mtime
        
        return {
            "success": True,
            "tree": tree,
            "metadata": {
                "tfstate_path": str(tfstate_path),
                "tfstate_modified": tfstate_modified,
                "total_resources": total_resources
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get deployed resources tree: {e}")
        # Return partial tree if possible
        return {
            "success": False,
            "message": f"Error reading Terraform state: {str(e)}",
            "tree": None
        }



# ==================== Vector Index Management Endpoints ====================

@router.get("/vector-indexes/{bucket_name}")
async def list_vector_indexes(
    bucket_name: str,
    storage_manager: S3VectorStorageManager = Depends(get_storage_manager)
):
    """
    List all vector indexes within a vector bucket.
    
    Args:
        bucket_name: Name of the S3 vector bucket
        
    Returns:
        Dictionary with list of indexes containing:
        - index_name: Name of the index
        - index_arn: ARN of the index
        - dimension: Vector dimension
        - distance_metric: Distance metric used
        - data_type: Data type (float32)
        - vector_count: Number of vectors in the index
        - status: Index status
        - created_at: Creation timestamp
    """
    try:
        logger.info(f"Listing vector indexes for bucket: {bucket_name}")
        
        # List indexes using storage manager
        indexes = storage_manager.list_vector_indexes(bucket_name)
        
        # Format response
        index_list = []
        for index in indexes:
            index_info = {
                "index_name": index.get("indexName"),
                "index_arn": index.get("indexArn"),
                "dimension": index.get("dimension", 0),
                "distance_metric": index.get("distanceMetric", "cosine"),
                "data_type": index.get("dataType", "float32"),
                "vector_count": index.get("vectorCount", 0),
                "status": index.get("status", "active"),
                "created_at": index.get("createdAt")
            }
            index_list.append(index_info)
        
        return {
            "success": True,
            "bucket_name": bucket_name,
            "index_count": len(index_list),
            "indexes": index_list
        }
        
    except Exception as e:
        logger.error(f"Failed to list vector indexes for bucket {bucket_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DEPRECATED ENDPOINTS REMOVED ====================
# The following endpoints have been removed as part of the Terraform-first architecture:
# - POST /create-vector-index (create vector index)
# - DELETE /delete-vector-index/{bucket_name}/{index_name} (delete vector index)
# Vector indexes should be created via the backend provider APIs directly.


@router.get("/vector-index/status")
async def get_vector_index_status(
    index_arn: str,
    storage_manager: S3VectorStorageManager = Depends(get_storage_manager)
):
    """
    Get detailed status and statistics for a vector index.
    
    Args:
        index_arn: ARN of the vector index (format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name)
        
    Returns:
        Dictionary with:
        - index_arn: Index ARN
        - status: Index status (active, creating, etc.)
        - vector_count: Number of vectors in the index
        - dimension: Vector dimension
        - metric: Distance metric
        - storage_size_mb: Estimated storage size in MB
        - last_updated: Last update timestamp
        - metadata: Additional index metadata
    """
    try:
        logger.info(f"Getting status for index: {index_arn}")
        
        # Parse ARN to extract bucket and index name
        from src.utils.arn_parser import ARNParser
        
        try:
            parts = ARNParser.parse_s3vector_arn(index_arn)
            bucket_name = parts["bucket"]
            index_name = parts["index"]
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid index ARN format: {str(e)}"
            )
        
        # Get index metadata
        metadata = storage_manager.get_vector_index_metadata(bucket_name, index_name)
        
        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"Index not found: {index_arn}"
            )
        
        # Calculate estimated storage size (rough estimate: vector_count * dimension * 4 bytes for float32)
        vector_count = metadata.get("vectorCount", 0)
        dimension = metadata.get("dimension", 0)
        storage_size_bytes = vector_count * dimension * 4  # 4 bytes per float32
        storage_size_mb = storage_size_bytes / (1024 * 1024)
        
        return {
            "success": True,
            "index_arn": index_arn,
            "bucket_name": bucket_name,
            "index_name": index_name,
            "status": metadata.get("status", "active"),
            "vector_count": vector_count,
            "dimension": dimension,
            "metric": metadata.get("distanceMetric", "cosine"),
            "data_type": metadata.get("dataType", "float32"),
            "storage_size_mb": round(storage_size_mb, 2),
            "created_at": metadata.get("createdAt"),
            "last_updated": metadata.get("lastUpdated"),
            "metadata": metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get index status for {index_arn}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/store-embeddings-to-index")
async def store_embeddings_to_index(
    request: StoreEmbeddingsToIndexRequest,
    storage_manager: S3VectorStorageManager = Depends(get_storage_manager)
):
    """
    Store completed processing job embeddings to specified index.
    
    This endpoint provides a complete workflow:
    1. Get job results from processing service
    2. Extract embeddings from job
    3. Store to specified index via appropriate backend provider
    4. Return storage status
    
    Args:
        request: StoreEmbeddingsToIndexRequest with:
            - job_id: Processing job ID
            - index_arn: Target index ARN
            - backend: Backend type (s3_vector, opensearch, qdrant, lancedb)
            
    Returns:
        Dictionary with storage result and statistics
    """
    try:
        logger.info(f"Storing embeddings from job {request.job_id} to index {request.index_arn}")
        
        # Import processing jobs from processing router
        from src.api.routers.processing import processing_jobs
        
        # Validate job exists
        if request.job_id not in processing_jobs:
            raise HTTPException(
                status_code=404,
                detail=f"Processing job {request.job_id} not found"
            )
        
        job = processing_jobs[request.job_id]
        
        # Validate job is completed
        if job.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Job {request.job_id} is not completed. Current status: {job.status}"
            )
        
        if not job.result:
            raise HTTPException(
                status_code=400,
                detail=f"Job {request.job_id} has no results available"
            )
        
        # Extract and prepare vectors
        vectors_data = []
        for segment in job.result.get('segments', []):
            embedding = segment.get('embedding')
            if not embedding:
                logger.warning(f"Segment {segment.get('segment_id')} has no embedding, skipping")
                continue
                
            vectors_data.append({
                'id': segment.get('segment_id'),
                'vector': embedding,
                'metadata': {
                    'video_id': job.result.get('video_id'),
                    'start_sec': segment.get('start_offset_sec'),
                    'end_sec': segment.get('end_offset_sec'),
                    'embedding_option': segment.get('embedding_option'),
                    'job_id': request.job_id
                }
            })
        
        if not vectors_data:
            raise HTTPException(
                status_code=400,
                detail="No valid embeddings found in job results"
            )
        
        # Store vectors based on backend type
        if request.backend == "s3_vector":
            # Use S3 Vectors backend
            result = storage_manager.put_vectors(request.index_arn, vectors_data)
            
        elif request.backend == "opensearch":
            # Use OpenSearch backend
            from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
            
            provider = VectorStoreProviderFactory.create_provider(VectorStoreType.OPENSEARCH)
            
            # Parse index name from ARN
            from src.utils.arn_parser import ARNParser
            parts = ARNParser.parse_s3vector_arn(request.index_arn)
            index_name = parts.get("index", "default")
            
            result = provider.upsert_vectors(index_name, vectors_data)
            
        elif request.backend in ["qdrant", "lancedb"]:
            # Use other vector store backends
            from src.services.vector_store_provider import VectorStoreType, VectorStoreProviderFactory
            
            backend_map = {
                "qdrant": VectorStoreType.QDRANT,
                "lancedb": VectorStoreType.LANCEDB
            }
            
            provider = VectorStoreProviderFactory.create_provider(backend_map[request.backend])
            
            # Parse collection/table name from ARN
            from src.utils.arn_parser import ARNParser
            parts = ARNParser.parse_s3vector_arn(request.index_arn)
            store_name = parts.get("index", "default")
            
            result = provider.upsert_vectors(store_name, vectors_data)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported backend: {request.backend}"
            )
        
        return {
            "success": True,
            "message": f"Successfully stored {len(vectors_data)} embeddings to index",
            "job_id": request.job_id,
            "index_arn": request.index_arn,
            "backend": request.backend,
            "stored_count": len(vectors_data),
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store embeddings from job {request.job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
