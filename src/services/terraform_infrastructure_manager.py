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

    def deploy_vector_store(
        self,
        vector_store: str,
        wait_for_completion: bool = True,
        timeout_sec: int = 1800
    ) -> DeploymentStatus:
        """
        Deploy a specific vector store module.

        Args:
            vector_store: Which store to deploy (s3vector, qdrant, opensearch, etc.)
            wait_for_completion: Wait for deployment to finish
            timeout_sec: Max wait time

        Returns:
            DeploymentStatus with deployment result
        """
        logger.info(f"Deploying vector store: {vector_store}")

        start_time = time.time()

        try:
            # Use terraform apply with -target to deploy specific module
            target = f"module.{vector_store}"

            result = self._run_terraform_command(
                ["apply", "-target", target, "-auto-approve"],
                timeout=timeout_sec if wait_for_completion else None
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

    def destroy_vector_store(
        self,
        vector_store: str,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Destroy a specific vector store.

        Args:
            vector_store: Which store to destroy
            wait_for_completion: Wait for destruction to finish

        Returns:
            Destruction result
        """
        logger.info(f"Destroying vector store: {vector_store}")

        try:
            target = f"module.{vector_store}"

            result = self._run_terraform_command(
                ["destroy", "-target", target, "-auto-approve"],
                timeout=1800 if wait_for_completion else None
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
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess:
        """
        Run terraform command.

        Args:
            args: Terraform command arguments
            timeout: Command timeout in seconds

        Returns:
            CompletedProcess with result
        """
        cmd = ["terraform"] + args

        logger.debug(f"Running terraform command: {' '.join(cmd)}")

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
