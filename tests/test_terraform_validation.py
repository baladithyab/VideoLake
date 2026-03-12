#!/usr/bin/env python3
"""
Terraform validation tests.

Provides pytest wrappers for running terraform validate and terraform plan
across all deployment profiles. These tests ensure infrastructure-as-code
is syntactically valid before deployment.

Tests are marked as @pytest.mark.terraform and @pytest.mark.integration.
"""

import subprocess
from pathlib import Path

import pytest

# Terraform root directory
TERRAFORM_DIR = Path(__file__).parent.parent / "terraform"

# Deployment profiles (directories with terraform configs)
DEPLOYMENT_PROFILES = [
    "terraform",  # Root terraform config
]


def get_terraform_modules() -> list[Path]:
    """
    Discover all Terraform modules in the terraform/modules/ directory.

    Returns:
        List of Path objects pointing to module directories
    """
    modules_dir = TERRAFORM_DIR / "modules"
    if not modules_dir.exists():
        return []

    return [
        module_dir
        for module_dir in modules_dir.iterdir()
        if module_dir.is_dir() and (module_dir / "main.tf").exists()
    ]


def run_terraform_command(
    command: list[str],
    cwd: Path,
    timeout: int = 60
) -> tuple[int, str, str]:
    """
    Run a terraform command and return exit code, stdout, stderr.

    Args:
        command: Command to run (e.g., ["terraform", "validate"])
        cwd: Working directory
        timeout: Command timeout in seconds

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return 1, "", str(e)


# ============================================================================
# Root Terraform Configuration Tests
# ============================================================================

@pytest.mark.terraform
@pytest.mark.integration
def test_terraform_root_init():
    """Test that terraform init succeeds for root config."""
    if not TERRAFORM_DIR.exists():
        pytest.skip(f"Terraform directory not found: {TERRAFORM_DIR}")

    exit_code, stdout, stderr = run_terraform_command(
        ["terraform", "init", "-backend=false"],
        cwd=TERRAFORM_DIR
    )

    assert exit_code == 0, (
        f"terraform init failed:\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )


@pytest.mark.terraform
@pytest.mark.integration
def test_terraform_root_validate():
    """Test that terraform validate succeeds for root config."""
    if not TERRAFORM_DIR.exists():
        pytest.skip(f"Terraform directory not found: {TERRAFORM_DIR}")

    # Run init first
    init_exit_code, _, _ = run_terraform_command(
        ["terraform", "init", "-backend=false"],
        cwd=TERRAFORM_DIR
    )
    if init_exit_code != 0:
        pytest.skip("terraform init failed, skipping validate")

    # Run validate
    exit_code, stdout, stderr = run_terraform_command(
        ["terraform", "validate"],
        cwd=TERRAFORM_DIR
    )

    assert exit_code == 0, (
        f"terraform validate failed:\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )


@pytest.mark.terraform
@pytest.mark.integration
@pytest.mark.slow
def test_terraform_root_plan():
    """
    Test that terraform plan succeeds for root config.

    This validates that the Terraform configuration is syntactically correct
    and can generate an execution plan (without applying changes).
    """
    if not TERRAFORM_DIR.exists():
        pytest.skip(f"Terraform directory not found: {TERRAFORM_DIR}")

    # Run init first
    init_exit_code, _, _ = run_terraform_command(
        ["terraform", "init", "-backend=false"],
        cwd=TERRAFORM_DIR
    )
    if init_exit_code != 0:
        pytest.skip("terraform init failed, skipping plan")

    # Run plan with -input=false to prevent interactive prompts
    exit_code, stdout, stderr = run_terraform_command(
        ["terraform", "plan", "-input=false"],
        cwd=TERRAFORM_DIR,
        timeout=120
    )

    # Note: Plan may fail if AWS credentials are not available,
    # but it should not fail due to syntax errors
    if exit_code != 0:
        # Check if failure is due to missing credentials (acceptable)
        if "Error: No valid credential sources found" in stderr or \
           "Error: error configuring Terraform AWS Provider" in stderr:
            pytest.skip("AWS credentials not available, skipping plan execution")

    assert exit_code == 0, (
        f"terraform plan failed:\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )


# ============================================================================
# Terraform Module Tests
# ============================================================================

@pytest.mark.terraform
@pytest.mark.integration
@pytest.mark.parametrize("module_dir", get_terraform_modules(), ids=lambda p: p.name)
def test_terraform_module_validate(module_dir: Path):
    """
    Test that terraform validate succeeds for each module.

    This test runs for every Terraform module discovered in terraform/modules/.
    Each module is tested independently to catch module-specific errors.
    """
    # Run init first
    init_exit_code, _, init_stderr = run_terraform_command(
        ["terraform", "init", "-backend=false"],
        cwd=module_dir
    )
    if init_exit_code != 0:
        pytest.fail(
            f"terraform init failed for module {module_dir.name}:\n{init_stderr}"
        )

    # Run validate
    exit_code, stdout, stderr = run_terraform_command(
        ["terraform", "validate"],
        cwd=module_dir
    )

    assert exit_code == 0, (
        f"terraform validate failed for module {module_dir.name}:\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )


@pytest.mark.terraform
@pytest.mark.integration
def test_terraform_fmt_check():
    """
    Test that all Terraform files are properly formatted.

    This runs 'terraform fmt -check' to ensure consistent formatting
    across the codebase.
    """
    if not TERRAFORM_DIR.exists():
        pytest.skip(f"Terraform directory not found: {TERRAFORM_DIR}")

    exit_code, stdout, stderr = run_terraform_command(
        ["terraform", "fmt", "-check", "-recursive"],
        cwd=TERRAFORM_DIR
    )

    assert exit_code == 0, (
        f"terraform fmt found unformatted files:\n"
        f"STDOUT:\n{stdout}\n"
        f"Run 'terraform fmt -recursive' to fix formatting."
    )


# ============================================================================
# Terraform Module Structure Tests
# ============================================================================

@pytest.mark.terraform
@pytest.mark.unit
@pytest.mark.parametrize("module_dir", get_terraform_modules(), ids=lambda p: p.name)
def test_terraform_module_has_required_files(module_dir: Path):
    """
    Test that each Terraform module has required standard files.

    Required files per Terraform best practices:
    - main.tf: Main resource definitions
    - variables.tf: Input variable declarations
    - outputs.tf: Output value declarations (optional for some modules)
    """
    required_files = ["main.tf", "variables.tf"]

    for required_file in required_files:
        file_path = module_dir / required_file
        assert file_path.exists(), (
            f"Module {module_dir.name} is missing required file: {required_file}"
        )


@pytest.mark.terraform
@pytest.mark.unit
def test_terraform_modules_directory_exists():
    """Test that terraform/modules directory exists."""
    modules_dir = TERRAFORM_DIR / "modules"
    assert modules_dir.exists(), "terraform/modules directory not found"
    assert modules_dir.is_dir(), "terraform/modules is not a directory"
