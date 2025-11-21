import os
import json
import subprocess
import logging
from typing import Dict, Any, List, Optional

class TerraformManager:
    """
    Manages Terraform operations for VideoLake infrastructure.
    Allows programmatic provisioning and destruction of vector backends.
    """

    def __init__(self, terraform_dir: str = "terraform"):
        """
        Initialize the TerraformManager.

        Args:
            terraform_dir: Path to the terraform directory (relative to project root or absolute)
        """
        # Resolve absolute path
        if os.path.isabs(terraform_dir):
            self.terraform_dir = terraform_dir
        else:
            # Assuming running from project root
            self.terraform_dir = os.path.abspath(terraform_dir)

        self.tfvars_path = os.path.join(self.terraform_dir, "terraform.tfvars.json")
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Map backend types to their terraform variable names
        self.backend_vars = {
            "s3vector": "deploy_s3vector",
            "opensearch": "deploy_opensearch",
            "qdrant": "deploy_qdrant",
            "qdrant_ebs": "deploy_qdrant_ebs",
            "lancedb_s3": "deploy_lancedb_s3",
            "lancedb_efs": "deploy_lancedb_efs",
            "lancedb_ebs": "deploy_lancedb_ebs",
            "benchmark_runner": "deploy_benchmark_runner"
        }

    def _load_tfvars(self) -> Dict[str, Any]:
        """Load current variables from terraform.tfvars.json."""
        if not os.path.exists(self.tfvars_path):
            return {}
        try:
            with open(self.tfvars_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            self.logger.warning(f"Could not decode {self.tfvars_path}, returning empty dict")
            return {}

    def _save_tfvars(self, vars: Dict[str, Any]):
        """Save variables to terraform.tfvars.json."""
        with open(self.tfvars_path, 'w') as f:
            json.dump(vars, f, indent=2)

    def _run_terraform(self, command: str, args: Optional[List[str]] = None) -> subprocess.CompletedProcess:
        """Execute a terraform command."""
        cmd = ["terraform", command] + (args or [])
        self.logger.info(f"Running command: {' '.join(cmd)} in {self.terraform_dir}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.terraform_dir,
                check=True,
                capture_output=True,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Terraform command failed: {e.stderr}")
            raise RuntimeError(f"Terraform command failed: {e.stderr}") from e
        except FileNotFoundError:
            self.logger.error("Terraform executable not found.")
            raise RuntimeError("Terraform executable not found. Please ensure terraform is installed and in PATH.")

    def init(self):
        """Run terraform init."""
        self._run_terraform("init")

    def validate(self):
        """Run terraform validate."""
        self._run_terraform("validate")

    def plan(self, backend_type: Optional[str] = None, destroy: bool = False) -> str:
        """
        Run terraform plan.
        
        Args:
            backend_type: If provided, updates tfvars to enable/disable this backend before planning.
            destroy: If True, plans for destruction (sets var to false).
        
        Returns:
            The stdout of the plan command.
        """
        if backend_type:
            self._update_state_config(backend_type, not destroy)
            
        return self._run_terraform("plan").stdout

    def apply(self, backend_type: str) -> str:
        """
        Provision a specific backend.
        
        Args:
            backend_type: The type of backend to deploy (e.g., 'qdrant', 'opensearch')
            
        Returns:
            The stdout of the apply command.
        """
        self._update_state_config(backend_type, True)
        return self._run_terraform("apply", ["-auto-approve"]).stdout

    def destroy(self, backend_type: str) -> str:
        """
        Destroy a specific backend.
        
        Args:
            backend_type: The type of backend to destroy
            
        Returns:
            The stdout of the apply command (which destroys the resource).
        """
        if backend_type == "s3vector":
             self.logger.warning("S3Vector is the core backend. Destroying it may affect other components.")

        self._update_state_config(backend_type, False)
        # We use apply because we are just changing the variable to false
        return self._run_terraform("apply", ["-auto-approve"]).stdout

    def _update_state_config(self, backend_type: str, enable: bool):
        """Update the tfvars file to enable/disable a backend."""
        if backend_type not in self.backend_vars:
            raise ValueError(f"Unknown backend type: {backend_type}. Valid types: {list(self.backend_vars.keys())}")
            
        var_name = self.backend_vars[backend_type]
        
        current_vars = self._load_tfvars()
        current_vars[var_name] = enable
        
        # Ensure s3vector is always true unless explicitly disabled (which we generally avoid)
        if "deploy_s3vector" not in current_vars:
            current_vars["deploy_s3vector"] = True
            
        self._save_tfvars(current_vars)

    def get_status(self) -> Dict[str, bool]:
        """
        Get the deployment status of all backends.
        
        Returns:
            Dictionary mapping backend types to boolean deployed status.
        """
        try:
            result = self._run_terraform("output", ["-json"])
            outputs = json.loads(result.stdout)
            
            status = {}
            
            # Check deployment_summary if available
            if "deployment_summary" in outputs:
                deployed_map = outputs["deployment_summary"]["value"]["vector_stores_deployed"]
                for backend in self.backend_vars:
                    # The keys in deployment_summary match our backend keys
                    if backend in deployed_map:
                        status[backend] = deployed_map[backend]
                    else:
                        status[backend] = False
            else:
                # Fallback
                for backend in self.backend_vars:
                    if backend in outputs:
                        val = outputs[backend]["value"]
                        if isinstance(val, dict):
                            status[backend] = val.get("deployed", False)
                        else:
                            status[backend] = False
                    else:
                        status[backend] = False
                        
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get status: {e}")
            # Return all false if we can't determine status
            return {k: False for k in self.backend_vars}

    def get_outputs(self, backend_type: str) -> Dict[str, Any]:
        """
        Get the terraform outputs for a specific backend.
        
        Args:
            backend_type: The backend to get outputs for.
            
        Returns:
            Dictionary of outputs.
        """
        try:
            result = self._run_terraform("output", ["-json"])
            outputs = json.loads(result.stdout)
            
            if backend_type in outputs:
                return outputs[backend_type]["value"]
            return {}
        except Exception as e:
            self.logger.error(f"Failed to get outputs: {e}")
            return {}

if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    manager = TerraformManager()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            print(json.dumps(manager.get_status(), indent=2))
        elif cmd == "init":
            manager.init()
            print("Initialized")
        elif cmd == "plan" and len(sys.argv) > 2:
            print(manager.plan(sys.argv[2]))
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("Usage: python terraform_manager.py [status|init|plan <backend>]")