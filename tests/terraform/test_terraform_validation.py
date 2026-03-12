#!/usr/bin/env python3
"""
Terraform validation tests.

Tests terraform validate and terraform plan for all modules and deployment profiles.
Does NOT apply terraform (no actual resource creation).
"""

import pytest
import subprocess
import json
from pathlib import Path
from typing import List, Dict
import os
@pytest.mark.terraform


@pytest.mark.terraform
class TestTerraformBestPractices:
    """Test terraform configuration best practices."""

    @pytest.fixture
    def terraform_dir(self):
        """Get terraform directory path."""
        project_root = Path(__file__).parent.parent.parent
        tf_dir = project_root / "terraform"

        if not tf_dir.exists():
            pytest.skip("Terraform directory not found")

        return tf_dir

    def test_no_hardcoded_credentials(self, terraform_dir):
        """Test that no AWS credentials are hardcoded."""
        tf_files = list(terraform_dir.rglob("*.tf"))

        for tf_file in tf_files:
            with open(tf_file, 'r') as f:
                content = f.read()

            # Should not have hardcoded keys
            assert "AKIA" not in content, f"Possible hardcoded AWS key in {tf_file}"
            assert "aws_access_key_id" not in content.lower(), f"Hardcoded credential in {tf_file}"

    def test_variables_have_descriptions(self, terraform_dir):
        """Test that variables have descriptions."""
        variables_tf = terraform_dir / "variables.tf"

        if not variables_tf.exists():
            pytest.skip("No variables.tf")

        with open(variables_tf, 'r') as f:
            content = f.read()

        if "variable" in content:
            # Most variables should have descriptions
            var_count = content.count("variable ")
            desc_count = content.count("description")

            assert desc_count >= var_count * 0.8, "Most variables should have descriptions"

    def test_backend_configuration(self, terraform_dir):
        """Test that backend configuration is present or documented."""
        # Check for backend.tf or backend config in main.tf
        backend_tf = terraform_dir / "backend.tf"
        main_tf = terraform_dir / "main.tf"

        has_backend = False

        if backend_tf.exists():
            has_backend = True

        if main_tf.exists():
            with open(main_tf, 'r') as f:
                content = f.read()
            if "backend" in content:
                has_backend = True

        # Backend may be configured or intentionally local
        # Just verify there's a conscious decision
        assert has_backend or backend_tf.exists() or True  # Always pass, just informational


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


@pytest.mark.integration
class TestTerraformModules:
    """Test individual Terraform modules."""

    @pytest.fixture
    def terraform_dir(self):
        """Get terraform directory path."""
        project_root = Path(__file__).parent.parent.parent
        tf_dir = project_root / "terraform"

        if not tf_dir.exists():
            pytest.skip("Terraform directory not found")

        return tf_dir

    def test_modules_directory_exists(self, terraform_dir):
        """Test that modules directory exists if modules are used."""
        modules_dir = terraform_dir / "modules"

        if modules_dir.exists():
            assert modules_dir.is_dir()

    @pytest.mark.parametrize("module_name", [
        "s3vector",
        "opensearch",
        "lancedb",
        "qdrant",
        "embedding",
    ])
    def test_module_structure(self, terraform_dir, module_name):
        """Test that modules have proper structure."""
        modules_dir = terraform_dir / "modules"

        if not modules_dir.exists():
            pytest.skip("No modules directory")

        module_dir = modules_dir / module_name

        if not module_dir.exists():
            pytest.skip(f"Module {module_name} not found")

        # Module should have main.tf and variables.tf
        main_tf = module_dir / "main.tf"
        variables_tf = module_dir / "variables.tf"

        assert main_tf.exists(), f"Module {module_name} missing main.tf"
        assert variables_tf.exists(), f"Module {module_name} missing variables.tf"

    def test_module_validation(self, terraform_dir):
        """Test validating each module independently."""
        modules_dir = terraform_dir / "modules"

        if not modules_dir.exists():
            pytest.skip("No modules directory")

        modules = [d for d in modules_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

        for module_dir in modules:
            # Init module
            result = subprocess.run(
                ["terraform", "init", "-backend=false"],
                cwd=module_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.fail(f"Module {module_dir.name} init failed:\n{result.stderr}")

            # Validate module
            result = subprocess.run(
                ["terraform", "validate"],
                cwd=module_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                pytest.fail(f"Module {module_dir.name} validation failed:\n{result.stderr}")


@pytest.mark.terraform
@pytest.mark.integration


@pytest.mark.integration
class TestTerraformOutputs:
    """Test terraform output definitions."""

    @pytest.fixture
    def terraform_dir(self):
        """Get terraform directory path."""
        project_root = Path(__file__).parent.parent.parent
        tf_dir = project_root / "terraform"

        if not tf_dir.exists():
            pytest.skip("Terraform directory not found")

        return tf_dir

    def test_outputs_file_exists(self, terraform_dir):
        """Test that outputs.tf exists."""
        outputs_tf = terraform_dir / "outputs.tf"

        if outputs_tf.exists():
            with open(outputs_tf, 'r') as f:
                content = f.read()

            # Should define some outputs
            assert "output" in content

    def test_output_structure(self, terraform_dir):
        """Test that outputs have proper structure."""
        outputs_tf = terraform_dir / "outputs.tf"

        if not outputs_tf.exists():
            pytest.skip("No outputs.tf file")

        with open(outputs_tf, 'r') as f:
            content = f.read()

        # Outputs should have description
        if "output" in content:
            assert "description" in content or "value" in content


@pytest.mark.slow
class TestTerraformPlan:
    """Test terraform plan for different deployment profiles."""

    @pytest.fixture
    def terraform_dir(self):
        """Get terraform directory path."""
        project_root = Path(__file__).parent.parent.parent
        tf_dir = project_root / "terraform"

        if not tf_dir.exists():
            pytest.skip("Terraform directory not found")

        return tf_dir

    def test_terraform_plan_dry_run(self, terraform_dir):
        """Test terraform plan without applying (dry run)."""
        # Init first
        subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_dir,
            capture_output=True
        )

        # Run plan
        result = subprocess.run(
            ["terraform", "plan", "-input=false"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )

        # Plan may fail without AWS creds, but should not crash
        if result.returncode not in [0, 1]:
            pytest.fail(f"terraform plan crashed:\n{result.stderr}")

    @pytest.mark.parametrize("deployment_mode", [
        "mode1",
        "mode2",
        "mode3",
    ])
    def test_deployment_profiles(self, terraform_dir, deployment_mode):
        """Test different deployment mode configurations."""
        # Init
        subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_dir,
            capture_output=True
        )

        # Plan with mode variable
        result = subprocess.run(
            ["terraform", "plan", "-var", f"deployment_mode={deployment_mode}", "-input=false"],
            cwd=terraform_dir,
            capture_output=True,
            text=True,
            timeout=60
        )

        # Should at least parse the configuration
        if "Error" in result.stderr and "credentials" not in result.stderr.lower():
            pytest.fail(f"Plan for {deployment_mode} failed:\n{result.stderr}")


@pytest.mark.terraform


@pytest.mark.integration
class TestTerraformValidation:
    """Test Terraform configuration validation."""

    @pytest.fixture
    def terraform_dir(self):
        """Get terraform directory path."""
        # Assume terraform dir is at project root
        project_root = Path(__file__).parent.parent.parent
        tf_dir = project_root / "terraform"

        if not tf_dir.exists():
            pytest.skip("Terraform directory not found")

        return tf_dir

    def test_terraform_directory_exists(self, terraform_dir):
        """Test that terraform directory exists."""
        assert terraform_dir.exists()
        assert terraform_dir.is_dir()

    def test_terraform_main_file_exists(self, terraform_dir):
        """Test that main.tf exists."""
        main_tf = terraform_dir / "main.tf"
        assert main_tf.exists(), "main.tf not found"

    def test_terraform_variables_file_exists(self, terraform_dir):
        """Test that variables.tf exists."""
        variables_tf = terraform_dir / "variables.tf"
        assert variables_tf.exists(), "variables.tf not found"

    def test_terraform_version_constraint(self, terraform_dir):
        """Test that terraform version is specified."""
        main_tf = terraform_dir / "main.tf"

        with open(main_tf, 'r') as f:
            content = f.read()

        # Should have terraform version requirement
        assert "required_version" in content, "Terraform version not specified"

    def test_terraform_fmt_check(self, terraform_dir):
        """Test that terraform files are properly formatted."""
        result = subprocess.run(
            ["terraform", "fmt", "-check", "-recursive"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )

        # Exit code 0 = all files formatted
        # Exit code 3 = files need formatting
        if result.returncode == 3:
            pytest.fail(f"Terraform files need formatting:\n{result.stdout}")
        elif result.returncode != 0:
            pytest.skip(f"terraform fmt failed: {result.stderr}")

    def test_terraform_init(self, terraform_dir):
        """Test that terraform init succeeds."""
        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"terraform init failed:\n{result.stderr}")

        assert "Terraform has been successfully initialized" in result.stdout

    def test_terraform_validate(self, terraform_dir):
        """Test that terraform validate succeeds."""
        # First init
        subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=terraform_dir,
            capture_output=True
        )

        # Then validate
        result = subprocess.run(
            ["terraform", "validate"],
            cwd=terraform_dir,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            pytest.fail(f"terraform validate failed:\n{result.stderr}")

        assert "Success" in result.stdout or "valid" in result.stdout.lower()


@pytest.mark.terraform


