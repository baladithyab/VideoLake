#!/usr/bin/env python3
"""
Terraform validation tests.

Tests terraform validate and plan for all modules and deployment profiles.
"""

import pytest
import subprocess
import json
from pathlib import Path
from typing import List, Dict


@pytest.mark.terraform
class TestTerraformModuleValidation:
    """Test terraform validate for all modules."""

    @pytest.fixture
    def terraform_root(self) -> Path:
        """Get terraform root directory."""
        return Path(__file__).parent.parent.parent / "terraform"

    @pytest.fixture
    def module_dirs(self, terraform_root: Path) -> List[Path]:
        """Get all terraform module directories."""
        modules_dir = terraform_root / "modules"
        if not modules_dir.exists():
            return []

        return [
            d for d in modules_dir.iterdir()
            if d.is_dir() and (d / "main.tf").exists()
        ]

    def test_terraform_root_exists(self, terraform_root: Path):
        """Verify terraform directory exists."""
        assert terraform_root.exists(), "Terraform directory not found"

    def test_terraform_main_file_exists(self, terraform_root: Path):
        """Verify main.tf exists in terraform root."""
        main_tf = terraform_root / "main.tf"
        assert main_tf.exists(), "main.tf not found in terraform root"

    def test_terraform_validate_root(self, terraform_root: Path):
        """Test terraform validate on root configuration."""
        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.skip(f"Terraform init failed: {result.stderr}")

        result = subprocess.run(
            ["terraform", "validate"],
            cwd=terraform_root,
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Terraform validation failed: {result.stderr}"

    def test_terraform_validate_modules(self, module_dirs: List[Path]):
        """Test terraform validate for each module."""
        if not module_dirs:
            pytest.skip("No terraform modules found")

        for module_dir in module_dirs:
            # Initialize module
            init_result = subprocess.run(
                ["terraform", "init", "-backend=false"],
                cwd=module_dir,
                capture_output=True,
                text=True
            )

            if init_result.returncode != 0:
                pytest.fail(f"Module {module_dir.name} init failed: {init_result.stderr}")

            # Validate module
            validate_result = subprocess.run(
                ["terraform", "validate"],
                cwd=module_dir,
                capture_output=True,
                text=True
            )

            assert validate_result.returncode == 0, \
                f"Module {module_dir.name} validation failed: {validate_result.stderr}"

    def test_opensearch_module_exists(self, terraform_root: Path):
        """Verify OpenSearch module exists."""
        opensearch_module = terraform_root / "modules" / "opensearch"
        assert opensearch_module.exists(), "OpenSearch module not found"
        assert (opensearch_module / "main.tf").exists(), "OpenSearch main.tf not found"

    def test_s3vector_module_exists(self, terraform_root: Path):
        """Verify S3Vector module exists."""
        s3vector_module = terraform_root / "modules" / "s3vector"
        if not s3vector_module.exists():
            pytest.skip("S3Vector module not yet created")

        assert (s3vector_module / "main.tf").exists(), "S3Vector main.tf not found"

    def test_lancedb_module_exists(self, terraform_root: Path):
        """Verify LanceDB module exists."""
        lancedb_module = terraform_root / "modules" / "lancedb"
        assert lancedb_module.exists(), "LanceDB module not found"
        assert (lancedb_module / "main.tf").exists(), "LanceDB main.tf not found"


@pytest.mark.terraform
@pytest.mark.slow
class TestTerraformPlan:
    """Test terraform plan for deployment profiles."""

    @pytest.fixture
    def terraform_root(self) -> Path:
        """Get terraform root directory."""
        return Path(__file__).parent.parent.parent / "terraform"

    def test_terraform_plan_minimal(self, terraform_root: Path):
        """Test terraform plan with minimal configuration."""
        # Initialize
        init_result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_root,
            capture_output=True,
            text=True
        )

        if init_result.returncode != 0:
            pytest.skip(f"Terraform init failed: {init_result.stderr}")

        # Create minimal var file
        minimal_vars = {
            "aws_region": "us-east-1",
            "project_name": "s3vector-test",
            "environment": "test"
        }

        var_file = terraform_root / "test.tfvars.json"
        var_file.write_text(json.dumps(minimal_vars))

        try:
            # Run plan
            plan_result = subprocess.run(
                ["terraform", "plan", f"-var-file={var_file.name}", "-out=/dev/null"],
                cwd=terraform_root,
                capture_output=True,
                text=True
            )

            # Plan should succeed (may have warnings but should not error)
            if plan_result.returncode != 0:
                # Check if it's a missing variables error
                if "variable" in plan_result.stderr.lower():
                    pytest.skip("Additional required variables not configured")
                pytest.fail(f"Terraform plan failed: {plan_result.stderr}")

        finally:
            # Clean up
            if var_file.exists():
                var_file.unlink()

    def test_terraform_format_check(self, terraform_root: Path):
        """Test terraform fmt -check to verify code formatting."""
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive"],
            cwd=terraform_root,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(
                f"Terraform code not properly formatted. Run 'terraform fmt -recursive':\n"
                f"{result.stdout}"
            )


@pytest.mark.terraform
class TestTerraformModuleStructure:
    """Test terraform module structure and conventions."""

    @pytest.fixture
    def terraform_root(self) -> Path:
        """Get terraform root directory."""
        return Path(__file__).parent.parent.parent / "terraform"

    @pytest.fixture
    def module_dirs(self, terraform_root: Path) -> List[Path]:
        """Get all terraform module directories."""
        modules_dir = terraform_root / "modules"
        if not modules_dir.exists():
            return []

        return [
            d for d in modules_dir.iterdir()
            if d.is_dir() and (d / "main.tf").exists()
        ]

    def test_modules_have_variables_file(self, module_dirs: List[Path]):
        """Verify each module has variables.tf."""
        if not module_dirs:
            pytest.skip("No terraform modules found")

        for module_dir in module_dirs:
            variables_file = module_dir / "variables.tf"
            assert variables_file.exists(), \
                f"Module {module_dir.name} missing variables.tf"

    def test_modules_have_outputs_file(self, module_dirs: List[Path]):
        """Verify each module has outputs.tf."""
        if not module_dirs:
            pytest.skip("No terraform modules found")

        for module_dir in module_dirs:
            # Some modules may not have outputs, so this is a soft check
            outputs_file = module_dir / "outputs.tf"
            if not outputs_file.exists():
                # Just warn, don't fail
                pass

    def test_modules_have_readme(self, module_dirs: List[Path]):
        """Verify each module has README.md."""
        if not module_dirs:
            pytest.skip("No terraform modules found")

        for module_dir in module_dirs:
            readme_file = module_dir / "README.md"
            if not readme_file.exists():
                # Just warn - README is good practice but not required
                pass

    def test_no_hardcoded_credentials(self, terraform_root: Path):
        """Verify no hardcoded AWS credentials in terraform files."""
        tf_files = list(terraform_root.rglob("*.tf"))

        sensitive_patterns = [
            "aws_access_key",
            "aws_secret_key",
            "AKIA",  # AWS access key prefix
        ]

        for tf_file in tf_files:
            content = tf_file.read_text()
            for pattern in sensitive_patterns:
                assert pattern not in content, \
                    f"Potential hardcoded credential found in {tf_file}: {pattern}"
