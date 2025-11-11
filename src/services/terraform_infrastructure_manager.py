"""
Terraform Infrastructure Manager

Provides Python API for programmatic Terraform operations.
Enables the application to manage infrastructure without manual CLI commands.

Architecture:
- API server calls Python methods
- Python executes terraform commands
- tfstate automatically parsed
- Resource registry updated
- UI shows resource status

Example:
    manager = TerraformInfrastructureManager()

    # Deploy specific vector store
    manager.deploy_vector_store("qdrant")

    # Deploy all vector stores
    manager.deploy_all()

    # Destroy specific store
    manager.destroy_vector_store("qdrant")

    # Get status
    status = manager.get_deployment_status()
"""

import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum

from src.utils.terraform_state_parser import TerraformStateParser
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.services.terraform_operation_tracker import operation_tracker

logger = get_logger(__name__)


class VectorStore(Enum):
    """Available vector stores."""
    S3VECTOR = "s3vector"
    OPENSEARCH = "opensearch"
    QDRANT = "qdrant"
    LANCEDB_S3 = "lancedb_s3"
    LANCEDB_EFS = "lancedb_efs"
    LANCEDB_EBS = "lancedb_ebs"
    DATA_BUCKET = "data_bucket"  # Required for all


@dataclass
class DeploymentStatus:
    """Status of a vector store deployment."""
    vector_store: str
    deployed: bool
    endpoint: Optional[str]
    status: str  # "not_deployed", "deploying", "deployed", "destroying", "failed"
    estimated_cost_monthly: Optional[float]
    deployment_time_sec: Optional[float]
    error_message: Optional[str] = None


class TerraformInfrastructureManager:
    """
    Manages Terraform infrastructure programmatically from Python.

    Enables API server and UI to control vector store deployment
    without manual terraform commands.

    Features:
    - Selective module deployment (deploy only what you need)
    - Async operations (non-blocking deploy/destroy)
    - Status monitoring
    - Cost estimation
    - Automatic resource registry sync
    """

    def __init__(self, terraform_dir: str = "terraform"):
        """
        Initialize Terraform infrastructure manager.

        Args:
            terraform_dir: Path to terraform directory
        """
        self.terraform_dir = Path(terraform_dir)
        self.tfstate_path = self.terraform_dir / "terraform.tfstate"
        self.logger = get_logger(__name__)

        if not self.terraform_dir.exists():
            raise ValueError(f"Terraform directory not found: {terraform_dir}")

        logger.info(f"Initialized Terraform manager: {self.terraform_dir}")

    def _get_module_target(self, vector_store: str) -> str:
        """
        Get the correct Terraform target for a vector store module.
        
        Modules that use count parameter need [0] index.
        
        Args:
            vector_store: Vector store name
            
        Returns:
            Terraform target string (e.g., "module.s3vector[0]")
        """
        # Modules using count need [0] index
        # Only shared_bucket doesn't use count (it's always created)
        modules_with_count = [
            "s3vector", "opensearch", "qdrant",
            "lancedb_s3", "lancedb_efs", "lancedb_ebs",
            "data_bucket"  # Legacy data bucket also uses count
        ]
        
        if vector_store in modules_with_count:
            return f"module.{vector_store}[0]"
        else:
            return f"module.{vector_store}"

    def deploy_vector_store(
        self,
        vector_store: str,
        wait_for_completion: bool = True,
        timeout_sec: int = 3600,  # Increased to 1 hour for S3 Vectors (preview service may be slow)
        operation_id: Optional[str] = None
    ) -> DeploymentStatus:
        """
        Deploy a specific vector store module.

        Args:
            vector_store: Which store to deploy (s3vector, qdrant, opensearch, etc.)
            wait_for_completion: Wait for deployment to finish
            timeout_sec: Max wait time
            operation_id: Optional operation ID for real-time log streaming

        Returns:
            DeploymentStatus with deployment result
        """
        logger.info(f"Deploying vector store: {vector_store}")

        start_time = time.time()

        try:
            # Map store names to Terraform variable names
            var_map = {
                's3vector': 'deploy_s3vector',
                'opensearch': 'deploy_opensearch',
                'qdrant': 'deploy_qdrant',
                'lancedb_s3': 'deploy_lancedb_s3',
                'lancedb_efs': 'deploy_lancedb_efs',
                'lancedb_ebs': 'deploy_lancedb_ebs',
                'data_bucket': None,  # Legacy data_bucket uses different variable
            }
            
            # Build terraform command with -var flag to enable the module
            target = self._get_module_target(vector_store)
            cmd = ["apply", "-auto-approve"]
            
            # Add -var flag to enable the module (set count = 1)
            var_name = var_map.get(vector_store)
            if var_name:
                cmd.extend(["-var", f"{var_name}=true"])
            
            # Add target module
            cmd.extend(["-target", target])

            result = self._run_terraform_command(
                cmd,
                timeout=timeout_sec if wait_for_completion else None,
                operation_id=operation_id
            )

            deployment_time = time.time() - start_time

            # Parse tfstate and sync to registry
            self._sync_state_to_registry()

            # Get deployment info
            parser = TerraformStateParser(str(self.tfstate_path))
            endpoint = None

            if vector_store == "qdrant":
                endpoint = parser.get_qdrant_endpoint()
            elif vector_store.startswith("lancedb"):
                backend_type = vector_store.split('_')[1] if '_' in vector_store else 's3'
                endpoint = parser.get_lancedb_connection_uri(backend_type)

            return DeploymentStatus(
                vector_store=vector_store,
                deployed=True,
                endpoint=endpoint,
                status="deployed",
                estimated_cost_monthly=self._estimate_cost(vector_store),
                deployment_time_sec=deployment_time
            )

        except Exception as e:
            logger.error(f"Failed to deploy {vector_store}: {str(e)}")
            return DeploymentStatus(
                vector_store=vector_store,
                deployed=False,
                endpoint=None,
                status="failed",
                estimated_cost_monthly=None,
                deployment_time_sec=time.time() - start_time,
                error_message=str(e)
            )

    def deploy_multiple_stores(
        self,
        vector_stores: List[str],
        wait_for_completion: bool = True,
        timeout_sec: int = 3600,
        operation_id: Optional[str] = None
    ) -> DeploymentStatus:
        """
        Deploy multiple vector stores in a single Terraform command.

        Uses multiple -target flags, allowing Terraform to parallelize internally.
        This is more efficient than running separate Terraform processes.

        Args:
            vector_stores: List of stores to deploy
            wait_for_completion: Wait for deployment to finish
            timeout_sec: Timeout in seconds
            operation_id: Optional operation ID for real-time log streaming

        Returns:
            Deployment status
        """
        logger.info(f"Deploying multiple vector stores: {', '.join(vector_stores)}")

        try:
            # Map store names to Terraform variable names
            var_map = {
                's3vector': 'deploy_s3vector',
                'opensearch': 'deploy_opensearch',
                'qdrant': 'deploy_qdrant',
                'lancedb_s3': 'deploy_lancedb_s3',
                'lancedb_efs': 'deploy_lancedb_efs',
                'lancedb_ebs': 'deploy_lancedb_ebs',
                'data_bucket': None,  # Legacy data_bucket uses different variable
            }
            
            # Build command with -var flags for each store and multiple -target flags
            cmd = ["apply", "-auto-approve"]
            
            # Add -var flag for each store to enable the module (set count = 1)
            for store in vector_stores:
                var_name = var_map.get(store)
                if var_name:
                    cmd.extend(["-var", f"{var_name}=true"])
            
            # Add -target flag for each store
            for store in vector_stores:
                target = self._get_module_target(store)
                cmd.extend(["-target", target])

            start_time = time.time()
            
            result = self._run_terraform_command(
                cmd,
                timeout=timeout_sec if wait_for_completion else None,
                operation_id=operation_id
            )

            deployment_time = time.time() - start_time
            
            # Sync state
            if self.tfstate_path.exists():
                self._sync_state_to_registry()

            return DeploymentStatus(
                vector_store=f"batch_{len(vector_stores)}_stores",
                deployed=True,
                endpoint=None,  # Multiple stores don't have a single endpoint
                status="deployed",
                estimated_cost_monthly=sum(self._estimate_cost(s) for s in vector_stores),
                deployment_time_sec=deployment_time
            )

        except Exception as e:
            logger.error(f"Batch deployment failed: {str(e)}")
            return DeploymentStatus(
                vector_store=f"batch_{len(vector_stores)}_stores",
                deployed=False,
                endpoint=None,
                status="failed",
                estimated_cost_monthly=None,
                deployment_time_sec=0,
                error_message=str(e)
            )

    def destroy_vector_store(
        self,
        vector_store: str,
        wait_for_completion: bool = True,
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Destroy a specific vector store.

        Args:
            vector_store: Which store to destroy
            wait_for_completion: Wait for destruction to finish
            operation_id: Optional operation ID for real-time log streaming

        Returns:
            Destruction result
        """
        logger.info(f"Destroying vector store: {vector_store}")

        try:
            target = self._get_module_target(vector_store)

            # S3 Vector destroy can take longer due to index deletion waits
            timeout = 3600 if wait_for_completion else None  # 1 hour for destroy operations

            result = self._run_terraform_command(
                ["destroy", "-target", target, "-auto-approve"],
                timeout=timeout,
                operation_id=operation_id
            )

            # Sync state
            if self.tfstate_path.exists():
                self._sync_state_to_registry()

            return {
                "vector_store": vector_store,
                "status": "destroyed",
                "success": True
            }

        except Exception as e:
            logger.error(f"Failed to destroy {vector_store}: {str(e)}")
            return {
                "vector_store": vector_store,
                "status": "failed",
                "success": False,
                "error": str(e)
            }

    def destroy_multiple_stores(
        self,
        vector_stores: List[str],
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Destroy multiple vector stores in a single Terraform command.

        Uses multiple -target flags, allowing Terraform to parallelize internally.
        This is more efficient than running separate Terraform processes.

        Args:
            vector_stores: List of stores to destroy
            operation_id: Optional operation ID for real-time log streaming

        Returns:
            Destruction result
        """
        logger.info(f"Destroying multiple vector stores: {', '.join(vector_stores)}")

        try:
            # Build command with multiple -target flags
            cmd = ["destroy", "-auto-approve"]
            for store in vector_stores:
                target = self._get_module_target(store)
                cmd.extend(["-target", target])

            result = self._run_terraform_command(
                cmd,
                timeout=3600,  # 1 hour for batch destroy
                operation_id=operation_id
            )

            # Sync state
            if self.tfstate_path.exists():
                self._sync_state_to_registry()

            return {
                "success": True,
                "stores": vector_stores,
                "error": None
            }

        except Exception as e:
            logger.error(f"Batch destruction failed: {str(e)}")
            return {
                "success": False,
                "stores": vector_stores,
                "error": str(e)
            }

    def deploy_all(
        self,
        selected_stores: Optional[List[str]] = None
    ) -> Dict[str, DeploymentStatus]:
        """
        Deploy all vector stores or selected subset.

        Args:
            selected_stores: List of stores to deploy (None = all)

        Returns:
            Dict mapping store name to DeploymentStatus
        """
        stores_to_deploy = selected_stores or [
            "data_bucket",  # Always deploy data bucket first
            "s3vector",
            "opensearch",
            "qdrant",
            "lancedb_s3",
            "lancedb_efs",
            "lancedb_ebs"
        ]

        logger.info(f"Deploying vector stores: {stores_to_deploy}")

        results = {}

        # Deploy data bucket first (required for embeddings)
        if "data_bucket" in stores_to_deploy:
            results["data_bucket"] = self.deploy_vector_store("data_bucket")

        # Deploy other stores
        for store in stores_to_deploy:
            if store != "data_bucket":
                results[store] = self.deploy_vector_store(store)

        return results

    def get_deployment_status(self) -> Dict[str, DeploymentStatus]:
        """
        Get current deployment status of all vector stores.

        Parses tfstate to determine what's deployed.

        Returns:
            Dict mapping store name to DeploymentStatus
        """
        status = {}

        if not self.tfstate_path.exists():
            # No tfstate = nothing deployed
            return self._get_empty_status()

        # Parse state
        parser = TerraformStateParser(str(self.tfstate_path))

        # Check each vector store
        all_stores = ["data_bucket", "s3vector", "opensearch", "qdrant",
                      "lancedb_s3", "lancedb_efs", "lancedb_ebs"]

        for store in all_stores:
            resources = parser.get_resources_by_module(store)

            if resources:
                # Store is deployed
                endpoint = None
                if store == "qdrant":
                    endpoint = parser.get_qdrant_endpoint()
                elif store.startswith("lancedb"):
                    backend = store.split('_')[1] if '_' in store else 's3'
                    endpoint = parser.get_lancedb_connection_uri(backend)

                status[store] = DeploymentStatus(
                    vector_store=store,
                    deployed=True,
                    endpoint=endpoint,
                    status="deployed",
                    estimated_cost_monthly=self._estimate_cost(store),
                    deployment_time_sec=None
                )
            else:
                # Store not deployed
                status[store] = DeploymentStatus(
                    vector_store=store,
                    deployed=False,
                    endpoint=None,
                    status="not_deployed",
                    estimated_cost_monthly=None,
                    deployment_time_sec=None
                )

        return status

    def _run_terraform_command(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        operation_id: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Run terraform command with optional real-time log streaming.

        Args:
            args: Terraform command arguments
            timeout: Command timeout in seconds
            operation_id: Optional operation ID for log streaming

        Returns:
            CompletedProcess with result
        """
        cmd = ["terraform"] + args

        logger.debug(f"Running terraform command: {' '.join(cmd)}")

        if operation_id:
            # Stream output in real-time
            return self._run_terraform_with_streaming(cmd, timeout, operation_id)
        else:
            # Original behavior - capture all output
            result = subprocess.run(
                cmd,
                cwd=self.terraform_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode != 0:
                logger.error(f"Terraform command failed: {result.stderr}")
                raise RuntimeError(f"Terraform error: {result.stderr}")

            return result

    def _run_terraform_with_streaming(
        self,
        cmd: List[str],
        timeout: Optional[int],
        operation_id: str
    ) -> subprocess.CompletedProcess:
        """
        Run terraform command and stream output to operation tracker in real-time.

        Args:
            cmd: Full command to run
            timeout: Command timeout in seconds
            operation_id: Operation ID for log streaming

        Returns:
            CompletedProcess with result
        """
        import select
        import os
        import fcntl

        operation_tracker.add_log(
            operation_id,
            f"$ {' '.join(cmd)}",
            level="INFO"
        )

        # Start process with pipes (unbuffered)
        process = subprocess.Popen(
            cmd,
            cwd=self.terraform_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,  # Unbuffered for real-time output
            env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Force unbuffered output
        )

        # Make stdout and stderr non-blocking
        for pipe in [process.stdout, process.stderr]:
            fd = pipe.fileno()
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        stdout_lines = []
        stderr_lines = []
        start_time = time.time()

        # Read output in real-time with select
        while True:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                process.kill()
                raise subprocess.TimeoutExpired(cmd, timeout)

            # Check if process finished
            poll_result = process.poll()
            if poll_result is not None and not select.select([process.stdout, process.stderr], [], [], 0)[0]:
                # Process finished and no more data to read
                break

            # Use select to wait for data (with 0.05s timeout for responsiveness)
            readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.05)

            for pipe in readable:
                try:
                    # Read all available data from this pipe
                    data = pipe.read()
                    if data:
                        # Split into lines but keep incomplete lines for next iteration
                        lines = data.splitlines(keepends=True)

                        for line in lines:
                            line = line.rstrip()
                            if not line:
                                continue

                            if pipe == process.stdout:
                                stdout_lines.append(line)
                                operation_tracker.add_log(operation_id, line, level="INFO")
                            else:  # stderr
                                stderr_lines.append(line)
                                # Terraform outputs progress to stderr, not always errors
                                level = "ERROR" if "error" in line.lower() and "│" not in line else "INFO"
                                operation_tracker.add_log(operation_id, line, level=level)

                except (IOError, OSError):
                    # No data available right now, continue
                    pass
                except Exception as e:
                    logger.error(f"Error reading process output: {e}")
                    break

        # Read any remaining output
        remaining_stdout, remaining_stderr = process.communicate()

        if remaining_stdout:
            for line in remaining_stdout.splitlines():
                line = line.rstrip()
                if line:
                    stdout_lines.append(line)
                    operation_tracker.add_log(operation_id, line, level="INFO")

        if remaining_stderr:
            for line in remaining_stderr.splitlines():
                line = line.rstrip()
                if line:
                    stderr_lines.append(line)
                    level = "WARNING" if "error" in line.lower() else "INFO"
                    operation_tracker.add_log(operation_id, line, level=level)

        # Create CompletedProcess result
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout='\n'.join(stdout_lines),
            stderr='\n'.join(stderr_lines)
        )

        if result.returncode != 0:
            error_msg = f"Terraform command failed with exit code {result.returncode}"
            logger.error(error_msg)
            operation_tracker.add_log(operation_id, error_msg, level="ERROR")
            raise RuntimeError(f"Terraform error: {result.stderr}")

        return result

    def _sync_state_to_registry(self) -> None:
        """Sync terraform state to resource registry."""
        if self.tfstate_path.exists():
            parser = TerraformStateParser(str(self.tfstate_path))
            parser.sync_to_resource_registry()
            logger.info("Synced tfstate to resource registry")

    def _estimate_cost(self, vector_store: str) -> float:
        """Estimate monthly cost for vector store."""
        cost_map = {
            "data_bucket": 5.0,  # ~$5/month for data storage
            "s3vector": 2.0,  # ~$2/month for vector storage
            "opensearch": 250.0,  # ~$250/month for 2x or1.medium
            "qdrant": 138.0,  # ~$138/month for t3.xlarge + 100GB
            "lancedb_s3": 2.0,  # ~$2/month for 100GB S3
            "lancedb_efs": 30.0,  # ~$30/month for 100GB EFS
            "lancedb_ebs": 8.0,  # ~$8/month for 100GB gp3
        }
        return cost_map.get(vector_store, 0.0)

    def _get_empty_status(self) -> Dict[str, DeploymentStatus]:
        """Get status when nothing is deployed."""
        stores = ["data_bucket", "s3vector", "opensearch", "qdrant",
                  "lancedb_s3", "lancedb_efs", "lancedb_ebs"]

        return {
            store: DeploymentStatus(
                vector_store=store,
                deployed=False,
                endpoint=None,
                status="not_deployed",
                estimated_cost_monthly=self._estimate_cost(store),
                deployment_time_sec=None
            )
            for store in stores
        }

    def initialize_terraform(self) -> Dict[str, Any]:
        """
        Initialize Terraform (run terraform init).

        Returns:
            Init result
        """
        try:
            result = self._run_terraform_command(["init"], timeout=300)

            return {
                "success": True,
                "message": "Terraform initialized successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def plan(self, target: Optional[str] = None) -> Dict[str, Any]:
        """
        Run terraform plan to preview changes.

        Args:
            target: Optional specific module to plan

        Returns:
            Plan summary
        """
        try:
            args = ["plan", "-json"]
            if target:
                args.extend(["-target", f"module.{target}"])

            result = self._run_terraform_command(args, timeout=300)

            return {
                "success": True,
                "plan_output": result.stdout
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
