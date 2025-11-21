from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from src.infrastructure.terraform_manager import TerraformManager

router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])
manager = TerraformManager()

@router.get("/status")
async def get_status() -> Dict[str, bool]:
    """
    Get the deployment status of all vector store backends.
    """
    return manager.get_status()

@router.post("/{backend_type}/apply")
async def apply_infrastructure(backend_type: str) -> Dict[str, Any]:
    """
    Apply Terraform configuration for a specific backend type.
    """
    try:
        output = manager.apply(backend_type)
        return {
            "status": "success",
            "backend_type": backend_type,
            "output": output
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{backend_type}/destroy")
async def destroy_infrastructure(backend_type: str) -> Dict[str, Any]:
    """
    Destroy resources for a specific backend type.
    """
    try:
        output = manager.destroy(backend_type)
        return {
            "status": "success",
            "backend_type": backend_type,
            "output": output
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{backend_type}/output")
async def get_infrastructure_output(backend_type: str) -> Dict[str, Any]:
    """
    Get Terraform outputs for a specific backend type.
    """
    return manager.get_outputs(backend_type)