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
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio

from src.services.terraform_infrastructure_manager import TerraformInfrastructureManager, DeploymentStatus
from src.services.terraform_operation_tracker import operation_tracker
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
    Deploy selected vector stores with real-time log streaming.

    Args:
        request: Deployment request with selected stores

    Returns:
        Operation ID for real-time log streaming (deployment runs in background)
    """
    # Start operation tracking for batch deployment
    stores_str = ", ".join(request.vector_stores)
    operation_id = operation_tracker.start_operation("deploy", f"batch: {stores_str}")

    logger.info(f"Starting batch deployment for {len(request.vector_stores)} stores with operation_id: {operation_id}")

    # Define background task
    def deploy_batch_task():
        try:
            logger.info(f"[{operation_id}] Batch deployment started for: {stores_str}")

            # Import threading for parallel deployment
            import threading
            from queue import Queue

            # Queue to collect results
            results_queue = Queue()

            # Function to deploy a single store in a thread
            def deploy_store_thread(store_name):
                try:
                    operation_tracker.add_log(operation_id, f"\n{'='*60}", level="INFO")
                    operation_tracker.add_log(operation_id, f"[{store_name}] Starting deployment...", level="INFO")
                    operation_tracker.add_log(operation_id, f"{'='*60}\n", level="INFO")

                    status = terraform_manager.deploy_vector_store(
                        vector_store=store_name,
                        wait_for_completion=True,
                        operation_id=operation_id  # Use same operation_id for all stores
                    )

                    if status.deployed:
                        operation_tracker.add_log(operation_id, f"✅ [{store_name}] Deployed successfully", level="INFO")
                        results_queue.put((store_name, True, None))
                    else:
                        operation_tracker.add_log(operation_id, f"❌ [{store_name}] Deployment failed: {status.error_message}", level="ERROR")
                        results_queue.put((store_name, False, status.error_message))

                except Exception as e:
                    operation_tracker.add_log(operation_id, f"❌ [{store_name}] Deployment error: {str(e)}", level="ERROR")
                    results_queue.put((store_name, False, str(e)))

            # Start all deployment threads in parallel
            operation_tracker.add_log(operation_id, f"🚀 Starting parallel deployment of {len(request.vector_stores)} store(s)...\n", level="INFO")

            threads = []
            for store in request.vector_stores:
                thread = threading.Thread(target=deploy_store_thread, args=(store,), daemon=True)
                thread.start()
                threads.append(thread)
                operation_tracker.add_log(operation_id, f"[{store}] Deployment thread started", level="INFO")

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Collect results
            all_success = True
            while not results_queue.empty():
                store_name, success, error = results_queue.get()
                if not success:
                    all_success = False

            # Mark operation as complete
            if all_success:
                operation_tracker.add_log(operation_id, f"\n✅ All {len(request.vector_stores)} store(s) deployed successfully!", level="INFO")
            else:
                operation_tracker.add_log(operation_id, f"\n⚠️ Batch deployment completed with some failures", level="WARNING")

            operation_tracker.complete_operation(operation_id, success=all_success)
            logger.info(f"[{operation_id}] Batch deployment completed")

        except Exception as e:
            logger.error(f"[{operation_id}] Batch deployment failed: {e}")
            operation_tracker.complete_operation(operation_id, success=False, error=str(e))

    # Add task to background
    background_tasks.add_task(deploy_batch_task)

    # Return immediately with operation_id
    return {
        "success": True,
        "message": f"Batch deployment started for {len(request.vector_stores)} store(s)",
        "stores": request.vector_stores,
        "operation_id": operation_id,  # Frontend uses this to stream logs
        "status": "running"
    }


@router.delete("/destroy")
async def destroy_infrastructure(
    request: DestroyRequest,
    background_tasks: BackgroundTasks
):
    """
    Destroy selected vector stores with real-time log streaming.

    Requires confirm=True for safety.

    Args:
        request: Destroy request with selected stores

    Returns:
        Operation ID for real-time log streaming (destruction runs in background)
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=True to destroy resources"
        )

    # Start operation tracking for batch destruction
    stores_str = ", ".join(request.vector_stores)
    operation_id = operation_tracker.start_operation("destroy", f"batch: {stores_str}")

    logger.info(f"Starting batch destruction for {len(request.vector_stores)} stores with operation_id: {operation_id}")

    # Define background task
    def destroy_batch_task():
        try:
            logger.info(f"[{operation_id}] Batch destruction started for: {stores_str}")

            # Import threading for parallel destruction
            import threading
            from queue import Queue

            # Queue to collect results
            results_queue = Queue()

            # Function to destroy a single store in a thread
            def destroy_store_thread(store_name):
                try:
                    operation_tracker.add_log(operation_id, f"\n{'='*60}", level="INFO")
                    operation_tracker.add_log(operation_id, f"[{store_name}] Starting destruction...", level="INFO")
                    operation_tracker.add_log(operation_id, f"{'='*60}\n", level="INFO")

                    result = terraform_manager.destroy_vector_store(
                        store_name,
                        operation_id=operation_id  # Use same operation_id for all stores
                    )

                    if result["success"]:
                        operation_tracker.add_log(operation_id, f"✅ [{store_name}] Destroyed successfully", level="INFO")
                        results_queue.put((store_name, True, None))
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        operation_tracker.add_log(operation_id, f"❌ [{store_name}] Destruction failed: {error_msg}", level="ERROR")
                        results_queue.put((store_name, False, error_msg))

                except Exception as e:
                    operation_tracker.add_log(operation_id, f"❌ [{store_name}] Destruction error: {str(e)}", level="ERROR")
                    results_queue.put((store_name, False, str(e)))

            # Start all destruction threads in parallel
            operation_tracker.add_log(operation_id, f"🚀 Starting parallel destruction of {len(request.vector_stores)} store(s)...\n", level="INFO")

            threads = []
            for store in request.vector_stores:
                thread = threading.Thread(target=destroy_store_thread, args=(store,), daemon=True)
                thread.start()
                threads.append(thread)
                operation_tracker.add_log(operation_id, f"[{store}] Destruction thread started", level="INFO")

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Collect results
            all_success = True
            while not results_queue.empty():
                store_name, success, error = results_queue.get()
                if not success:
                    all_success = False

            # Mark operation as complete
            if all_success:
                operation_tracker.add_log(operation_id, f"\n✅ All {len(request.vector_stores)} store(s) destroyed successfully!", level="INFO")
            else:
                operation_tracker.add_log(operation_id, f"\n⚠️ Batch destruction completed with some failures", level="WARNING")

            operation_tracker.complete_operation(operation_id, success=all_success)
            logger.info(f"[{operation_id}] Batch destruction completed")

        except Exception as e:
            logger.error(f"[{operation_id}] Batch destruction failed: {e}")
            operation_tracker.complete_operation(operation_id, success=False, error=str(e))

    # Add task to background
    background_tasks.add_task(destroy_batch_task)

    # Return immediately with operation_id
    return {
        "success": True,
        "message": f"Batch destruction started for {len(request.vector_stores)} store(s)",
        "stores": request.vector_stores,
        "operation_id": operation_id,  # Frontend uses this to stream logs
        "status": "running"
    }


@router.post("/deploy/{vector_store}")
async def deploy_single_store(
    vector_store: str,
    background_tasks: BackgroundTasks
):
    """
    Deploy a single vector store with real-time log streaming.

    Args:
        vector_store: Store to deploy (qdrant, lancedb_s3, etc.)

    Returns:
        Operation ID for real-time log streaming (deployment runs in background)
    """
    # Start operation tracking
    operation_id = operation_tracker.start_operation("deploy", vector_store)

    logger.info(f"Starting background deployment for {vector_store} with operation_id: {operation_id}")

    # Define background task
    def deploy_task():
        try:
            logger.info(f"[{operation_id}] Background deployment started for {vector_store}")

            status = terraform_manager.deploy_vector_store(
                vector_store=vector_store,
                wait_for_completion=True,
                operation_id=operation_id
            )

            # Mark operation as complete
            operation_tracker.complete_operation(
                operation_id,
                success=status.deployed,
                error=status.error_message
            )

            logger.info(f"[{operation_id}] Background deployment completed for {vector_store}: success={status.deployed}")

        except Exception as e:
            logger.error(f"[{operation_id}] Background deployment failed for {vector_store}: {e}")
            operation_tracker.complete_operation(
                operation_id,
                success=False,
                error=str(e)
            )

    # Add task to background
    background_tasks.add_task(deploy_task)

    # Return immediately with operation_id
    return {
        "success": True,
        "message": f"Deployment started for {vector_store}",
        "vector_store": vector_store,
        "operation_id": operation_id,  # Frontend uses this to stream logs
        "status": "running"
    }


@router.delete("/destroy/{vector_store}")
async def destroy_single_store(
    vector_store: str,
    confirm: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    Destroy a single vector store with real-time log streaming.

    Args:
        vector_store: Store to destroy
        confirm: Must be true to proceed

    Returns:
        Operation ID for real-time log streaming (destruction runs in background)
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true query parameter"
        )

    # Start operation tracking
    operation_id = operation_tracker.start_operation("destroy", vector_store)

    logger.info(f"Starting background destruction for {vector_store} with operation_id: {operation_id}")

    # Define background task
    def destroy_task():
        try:
            logger.info(f"[{operation_id}] Background destruction started for {vector_store}")

            result = terraform_manager.destroy_vector_store(
                vector_store,
                operation_id=operation_id
            )

            # Mark operation as complete
            operation_tracker.complete_operation(
                operation_id,
                success=result["success"],
                error=result.get("error")
            )

            logger.info(f"[{operation_id}] Background destruction completed for {vector_store}: success={result['success']}")

        except Exception as e:
            logger.error(f"[{operation_id}] Background destruction failed for {vector_store}: {e}")
            operation_tracker.complete_operation(
                operation_id,
                success=False,
                error=str(e)
            )

    # Add task to background
    if background_tasks:
        background_tasks.add_task(destroy_task)
    else:
        # Fallback: run in thread if no background_tasks available
        import threading
        threading.Thread(target=destroy_task, daemon=True).start()

    # Return immediately with operation_id
    return {
        "success": True,
        "message": f"Destruction started for {vector_store}",
        "vector_store": vector_store,
        "operation_id": operation_id,  # Frontend uses this to stream logs
        "status": "running"
    }


@router.get("/logs/{operation_id}")
async def stream_operation_logs(operation_id: str):
    """
    Stream real-time logs for a Terraform operation via Server-Sent Events (SSE).

    The UI connects to this endpoint when a deploy/destroy operation starts.
    Logs are streamed in real-time as Terraform executes.

    Args:
        operation_id: Operation ID to stream logs for

    Returns:
        SSE stream of log messages
    """
    logger.info(f"SSE connection established for operation {operation_id}")

    operation = operation_tracker.get_operation(operation_id)

    if not operation:
        logger.error(f"Operation {operation_id} not found")
        raise HTTPException(
            status_code=404,
            detail=f"Operation {operation_id} not found"
        )

    logger.info(f"Streaming logs for {operation.operation_type} operation on {operation.vector_store}")

    async def event_generator():
        """Generate SSE events from operation logs."""
        try:
            current_index = 0

            # Stream logs until operation completes
            while True:
                # Get new logs
                logs = operation_tracker.get_logs(operation_id)

                # Send any new logs
                for i in range(current_index, len(logs)):
                    log_entry = logs[i]

                    # Format as SSE event
                    data = json.dumps(log_entry)
                    yield f"data: {data}\n\n"

                    current_index = i + 1

                # Check if operation completed
                operation = operation_tracker.get_operation(operation_id)
                if not operation or operation.status != "running":
                    # Send completion event
                    completion_data = json.dumps({
                        "timestamp": "",
                        "level": "COMPLETE",
                        "message": f"Operation {operation.status}",
                        "status": operation.status,
                        "error": operation.error
                    })
                    yield f"data: {completion_data}\n\n"
                    break

                # Wait before checking for new logs (50ms for real-time feel)
                await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Error streaming logs for {operation_id}: {e}")
            error_data = json.dumps({
                "timestamp": "",
                "level": "ERROR",
                "message": f"Stream error: {str(e)}"
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
