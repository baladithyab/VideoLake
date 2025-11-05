"""
Infrastructure Management API Endpoints

Provides REST API for programmatic Terraform operations.
Enables UI to deploy/destroy vector stores on demand.

Endpoints:
- POST /infrastructure/deploy - Deploy vector stores
- DELETE /infrastructure/destroy - Destroy vector stores
- GET /infrastructure/status - Get deployment status
- POST /infrastructure/init - Initialize Terraform
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.services.terraform_infrastructure_manager import TerraformInfrastructureManager, DeploymentStatus
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])

# Global Terraform manager instance
terraform_manager = TerraformInfrastructureManager()


class DeployRequest(BaseModel):
    """Request to deploy vector stores."""
    vector_stores: List[str]  # ["qdrant", "lancedb_s3", etc.]
    wait_for_completion: bool = False  # If False, deploy async


class DestroyRequest(BaseModel):
    """Request to destroy vector stores."""
    vector_stores: List[str]
    confirm: bool = False  # Safety flag


@router.post("/init")
async def initialize_terraform():
    """
    Initialize Terraform (terraform init).

    Returns:
        Initialization result
    """
    try:
        result = terraform_manager.initialize_terraform()

        if result["success"]:
            return {
                "success": True,
                "message": "Terraform initialized successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "Init failed"))

    except Exception as e:
        logger.error(f"Terraform init failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_infrastructure_status():
    """
    Get deployment status of all vector stores.

    Returns:
        Status for each vector store
    """
    try:
        status = terraform_manager.get_deployment_status()

        return {
            "deployed_stores": [
                {
                    "name": name,
                    "deployed": s.deployed,
                    "endpoint": s.endpoint,
                    "status": s.status,
                    "estimated_cost_monthly": s.estimated_cost_monthly
                }
                for name, s in status.items()
            ],
            "total_deployed": sum(1 for s in status.values() if s.deployed),
            "total_cost_monthly": sum(
                s.estimated_cost_monthly for s in status.values()
                if s.deployed and s.estimated_cost_monthly
            )
        }

    except Exception as e:
        logger.error(f"Failed to get status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy")
async def deploy_infrastructure(
    request: DeployRequest,
    background_tasks: BackgroundTasks
):
    """
    Deploy selected vector stores.

    If wait_for_completion=False, deployment happens in background.

    Args:
        request: Deployment request with selected stores

    Returns:
        Deployment status or background task ID
    """
    try:
        if request.wait_for_completion:
            # Synchronous deployment
            results = terraform_manager.deploy_all(request.vector_stores)

            return {
                "success": True,
                "mode": "synchronous",
                "results": {
                    name: {
                        "deployed": s.deployed,
                        "endpoint": s.endpoint,
                        "deployment_time_sec": s.deployment_time_sec,
                        "error": s.error_message
                    }
                    for name, s in results.items()
                }
            }

        else:
            # Asynchronous deployment
            background_tasks.add_task(
                terraform_manager.deploy_all,
                request.vector_stores
            )

            return {
                "success": True,
                "mode": "asynchronous",
                "message": f"Deploying {len(request.vector_stores)} vector stores in background",
                "stores": request.vector_stores
            }

    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/destroy")
async def destroy_infrastructure(
    request: DestroyRequest,
    background_tasks: BackgroundTasks
):
    """
    Destroy selected vector stores.

    Requires confirm=True for safety.

    Args:
        request: Destroy request with selected stores

    Returns:
        Destruction status
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=True to destroy resources"
        )

    try:
        results = {}

        for store in request.vector_stores:
            result = terraform_manager.destroy_vector_store(store)
            results[store] = result

        return {
            "success": True,
            "destroyed_stores": request.vector_stores,
            "results": results
        }

    except Exception as e:
        logger.error(f"Destruction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy/{vector_store}")
async def deploy_single_store(
    vector_store: str,
    background_tasks: BackgroundTasks
):
    """
    Deploy a single vector store.

    Args:
        vector_store: Store to deploy (qdrant, lancedb_s3, etc.)

    Returns:
        Deployment result
    """
    try:
        status = terraform_manager.deploy_vector_store(
            vector_store=vector_store,
            wait_for_completion=True  # Wait for single deployments
        )

        return {
            "success": status.deployed,
            "vector_store": vector_store,
            "endpoint": status.endpoint,
            "deployment_time_sec": status.deployment_time_sec,
            "estimated_cost_monthly": status.estimated_cost_monthly,
            "error": status.error_message
        }

    except Exception as e:
        logger.error(f"Failed to deploy {vector_store}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/destroy/{vector_store}")
async def destroy_single_store(
    vector_store: str,
    confirm: bool = False
):
    """
    Destroy a single vector store.

    Args:
        vector_store: Store to destroy
        confirm: Must be true to proceed

    Returns:
        Destruction result
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true query parameter"
        )

    try:
        result = terraform_manager.destroy_vector_store(vector_store)

        if result["success"]:
            return result
        else:
            raise HTTPException(status_code=500, detail=result.get("error"))

    except Exception as e:
        logger.error(f"Failed to destroy {vector_store}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
