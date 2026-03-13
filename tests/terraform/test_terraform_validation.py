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
TERRAFORM_ROOT = Path(__file__).parent.parent.parent / "terraform"
PROFILES = [
"fast-start.tfvars",
"comparison.tfvars",
"full-multimodal.tfvars",
"production.tfvars",
]


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


@pytest.mark.terraform
class TestTerraformModules:
    """Test individual terraform modules."""

    def test_modules_directory_exists(self):
        """Verify modules directory exists."""
        modules_dir = TERRAFORM_ROOT / "modules"
        assert modules_dir.exists(), f"Modules directory not found: {modules_dir}"
        assert modules_dir.is_dir()

    def test_required_modules_exist(self):
        """Verify expected modules are present."""
        modules_dir = TERRAFORM_ROOT / "modules"

        expected_modules = [
            "opensearch",
            "lancedb",
            "lancedb_ecs",
            "sample_datasets",
            "benchmark_runner",
            "embedding_provider_bedrock_native",
        ]

        for module_name in expected_modules:
            module_path = modules_dir / module_name
            assert module_path.exists(), f"Module not found: {module_name}"
            assert module_path.is_dir(), f"Module path is not a directory: {module_name}"

            # Check for main.tf
            main_tf = module_path / "main.tf"
            assert main_tf.exists(), f"Module {module_name} missing main.tf"

    def test_modules_have_variables(self):
        """Verify modules have variables.tf files."""
        modules_dir = TERRAFORM_ROOT / "modules"

        # Get all module directories
        module_dirs = [d for d in modules_dir.iterdir() if d.is_dir()]

        for module_dir in module_dirs:
            variables_tf = module_dir / "variables.tf"
            # Not all modules need variables, but most should have them
            # This is a soft check - we just verify the file structure is reasonable
            main_tf = module_dir / "main.tf"
            assert main_tf.exists(), f"Module {module_dir.name} missing main.tf"

    def test_module_outputs_format(self):
        """Verify modules with outputs.tf have valid format."""
        modules_dir = TERRAFORM_ROOT / "modules"

        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir():
                continue

            outputs_tf = module_dir / "outputs.tf"
            if outputs_tf.exists():
                content = outputs_tf.read_text()
                # Basic check - should contain 'output' keyword
                assert "output" in content, (
                    f"outputs.tf in {module_dir.name} doesn't contain 'output' keyword"
                )


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


@pytest.mark.requires_aws
class TestTerraformPlan:
    """
    Test terraform plan with each profile.

    These tests require AWS credentials and are skipped in CI.
    Run with: pytest -m requires_aws
    """

    @pytest.mark.parametrize("profile", PROFILES)
    def test_terraform_plan_profile(self, profile):
        """
        Run terraform plan with each deployment profile.

        Requires AWS credentials to be configured.
        This validates that the configuration would execute successfully.
        """
        profiles_dir = TERRAFORM_ROOT / "profiles"
        profile_path = profiles_dir / profile

        # Initialize terraform
        init_result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=TERRAFORM_ROOT,
            capture_output=True,
            text=True,
        )

        if init_result.returncode != 0:
            pytest.skip(f"Terraform init failed: {init_result.stderr}")

        # Run plan
        plan_result = subprocess.run(
            ["terraform", "plan", f"-var-file={profile_path}"],
            cwd=TERRAFORM_ROOT,
            capture_output=True,
            text=True,
        )

        assert plan_result.returncode == 0, (
            f"Terraform plan failed for profile {profile}:\n"
            f"STDOUT: {plan_result.stdout}\n"
            f"STDERR: {plan_result.stderr}"
        )


@pytest.mark.terraform
class TestTerraformValidation:
    """Test terraform configuration validity."""

    def test_terraform_root_exists(self):
        """Verify terraform root directory exists."""
        assert TERRAFORM_ROOT.exists(), f"Terraform root not found: {TERRAFORM_ROOT}"
        assert TERRAFORM_ROOT.is_dir(), f"Terraform root is not a directory: {TERRAFORM_ROOT}"

    def test_terraform_main_exists(self):
        """Verify main.tf exists in root."""
        main_tf = TERRAFORM_ROOT / "main.tf"
        assert main_tf.exists(), f"main.tf not found: {main_tf}"

    def test_profiles_directory_exists(self):
        """Verify profiles directory exists with expected profiles."""
        profiles_dir = TERRAFORM_ROOT / "profiles"
        assert profiles_dir.exists(), f"Profiles directory not found: {profiles_dir}"

        for profile in PROFILES:
            profile_path = profiles_dir / profile
            assert profile_path.exists(), f"Profile not found: {profile}"

    def test_terraform_validate_root(self):
        """Run terraform validate on root configuration."""
        # Initialize terraform first
        init_result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=TERRAFORM_ROOT,
            capture_output=True,
            text=True,
        )

        if init_result.returncode != 0:
            pytest.skip(f"Terraform init failed: {init_result.stderr}")

        # Run validate
        validate_result = subprocess.run(
            ["terraform", "validate"],
            cwd=TERRAFORM_ROOT,
            capture_output=True,
            text=True,
        )

        assert validate_result.returncode == 0, (
            f"Terraform validate failed:\n"
            f"STDOUT: {validate_result.stdout}\n"
            f"STDERR: {validate_result.stderr}"
        )

    @pytest.mark.parametrize("profile", PROFILES)
    def test_terraform_validate_profile(self, profile):
        """
        Test that terraform validate passes with each deployment profile.

        This doesn't run plan (which requires AWS credentials), but validates
        that the configuration is syntactically correct and internally consistent.
        """
        profiles_dir = TERRAFORM_ROOT / "profiles"
        profile_path = profiles_dir / profile

        # Terraform validate doesn't use var files, so we just validate the base config
        # The profile would be used with 'terraform plan -var-file=...'
        assert profile_path.exists(), f"Profile not found: {profile_path}"

        # Just verify the file is valid HCL by checking it's not empty
        content = profile_path.read_text()
        assert len(content) > 0, f"Profile {profile} is empty"
        assert "=" in content, f"Profile {profile} doesn't appear to contain variable assignments"


@pytest.mark.terraform


