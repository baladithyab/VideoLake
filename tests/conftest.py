#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for S3Vector test suite.

Provides:
- Custom pytest markers for test categorization
- Shared fixtures for FastAPI TestClient, AWS mocks, config loading
- Test collection hooks for conditional test execution
"""

import json
import os
import tempfile
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest

# ============================================================================
# Pytest Options
# ============================================================================

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--real-aws",
        action="store_true",
        default=False,
        help="Enable real AWS tests (required to run these tests)"
    )
    parser.addoption(
        "--requires-aws",
        action="store_true",
        default=False,
        help="Run tests that require AWS credentials (no cost, but needs auth)"
    )


# ============================================================================
# Pytest Markers
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    # Test level markers
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (may use mocks for external services)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test (full system test)"
    )

    # Resource markers
    config.addinivalue_line(
        "markers", "requires_aws: mark test as requiring AWS credentials (no cost)"
    )
    config.addinivalue_line(
        "markers", "real_aws: mark test as using real AWS resources (will incur costs)"
    )
    config.addinivalue_line(
        "markers", "expensive: mark test as expensive (e.g., OpenSearch domain)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (takes >1 minute)"
    )

    # Component markers
    config.addinivalue_line(
        "markers", "api: mark test as testing FastAPI endpoints"
    )
    config.addinivalue_line(
        "markers", "terraform: mark test as testing Terraform infrastructure"
    )
    config.addinivalue_line(
        "markers", "provider: mark test as testing provider interfaces"
    )
    config.addinivalue_line(
        "markers", "frontend: mark test as testing frontend components"
    )


def pytest_collection_modifyitems(config, items):
    """
    Skip tests based on command-line flags.

    - Tests marked @pytest.mark.real_aws require --real-aws flag
    - Tests marked @pytest.mark.requires_aws require --requires-aws flag
    """
    run_real_aws = config.getoption("--real-aws")
    run_requires_aws = config.getoption("--requires-aws")

    for item in items:
        # Skip real AWS tests unless explicitly enabled
        if "real_aws" in item.keywords and not run_real_aws:
            item.add_marker(pytest.mark.skip(
                reason="Real AWS tests require --real-aws flag (will incur costs!)"
            ))

        # Skip tests requiring AWS credentials unless enabled
        if "requires_aws" in item.keywords and not run_requires_aws and not run_real_aws:
            item.add_marker(pytest.mark.skip(
                reason="Tests requiring AWS credentials need --requires-aws flag"
            ))


# ============================================================================
# FastAPI Test Fixtures
# ============================================================================

@pytest.fixture
def test_client():
    """
    FastAPI TestClient for API endpoint testing.

    Returns a TestClient instance with the FastAPI app loaded.
    Use this for testing API endpoints without starting a server.

    Example:
        def test_health_endpoint(test_client):
            response = test_client.get("/api/health")
            assert response.status_code == 200
    """
    from fastapi.testclient import TestClient

    from src.api.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_client_no_auth():
    """
    FastAPI TestClient with authentication middleware disabled.

    Useful for testing endpoints without API key requirements.
    """
    from fastapi.testclient import TestClient

    from src.api.main import app

    # Temporarily disable auth middleware for testing
    original_middleware = app.user_middleware.copy()
    app.user_middleware = [m for m in app.user_middleware if "APIKeyMiddleware" not in str(m)]

    with TestClient(app) as client:
        yield client

    # Restore middleware
    app.user_middleware = original_middleware


# ============================================================================
# AWS Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for unit tests."""
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {"Buckets": []}
    mock_client.head_bucket.return_value = {}
    mock_client.put_object.return_value = {"ETag": "mock-etag"}
    return mock_client


@pytest.fixture
def mock_bedrock_client():
    """Mock boto3 Bedrock client for unit tests."""
    mock_client = MagicMock()
    mock_client.list_foundation_models.return_value = {
        "modelSummaries": [
            {
                "modelId": "amazon.titan-embed-text-v1",
                "modelName": "Titan Embeddings G1 - Text"
            }
        ]
    }
    return mock_client


@pytest.fixture
def mock_bedrock_runtime_client():
    """Mock boto3 Bedrock Runtime client for unit tests."""
    mock_client = MagicMock()

    # Mock embedding response
    mock_embedding = [0.1] * 1536  # Typical embedding dimension
    mock_client.invoke_model.return_value = {
        "body": MagicMock(read=lambda: json.dumps({"embedding": mock_embedding}).encode())
    }

    return mock_client


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config() -> dict[str, Any]:
    """
    Load test configuration from environment or defaults.

    Returns a dictionary with test configuration values.
    Priority: environment variables > test defaults
    """
    return {
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "s3_bucket_prefix": os.getenv("TEST_S3_BUCKET_PREFIX", "s3vector-test"),
        "opensearch_domain_prefix": os.getenv("TEST_OPENSEARCH_PREFIX", "s3vector-test"),
        "api_base_url": os.getenv("TEST_API_BASE_URL", "http://localhost:8000"),
        "test_timeout": int(os.getenv("TEST_TIMEOUT", "300")),
        "cleanup_resources": os.getenv("TEST_CLEANUP_RESOURCES", "true").lower() == "true",
    }


@pytest.fixture
def temp_test_dir() -> Generator[str, None, None]:
    """
    Create a temporary directory for test file operations.

    Automatically cleaned up after test completion.
    """
    with tempfile.TemporaryDirectory(prefix="s3vector-test-") as tmpdir:
        yield tmpdir


# ============================================================================
# Provider Interface Fixtures (for TDD)
# ============================================================================

@pytest.fixture
def mock_vector_store_provider():
    """
    Mock VectorStoreProvider for testing provider interface contract.

    Use this to test code that depends on VectorStoreProvider without
    requiring actual backend implementations.
    """
    from src.services.vector_store_provider import (
        VectorStoreProvider,
        VectorStoreState,
        VectorStoreStatus,
        VectorStoreType,
    )

    mock_provider = MagicMock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.S3_VECTOR

    # Default mock responses
    mock_status = VectorStoreStatus(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        state=VectorStoreState.ACTIVE,
        vector_count=0,
        dimension=1536
    )
    mock_provider.get_status.return_value = mock_status
    mock_provider.list_stores.return_value = [mock_status]
    mock_provider.validate_connectivity.return_value = {
        "accessible": True,
        "endpoint": "test-endpoint",
        "response_time_ms": 10.0,
        "health_status": "healthy"
    }

    return mock_provider


# ============================================================================
# Terraform Test Fixtures
# ============================================================================

@pytest.fixture
def terraform_test_dir(tmp_path):
    """
    Create a temporary Terraform directory for testing.

    Returns a Path object to a temporary directory with basic Terraform structure.
    """
    tf_dir = tmp_path / "terraform_test"
    tf_dir.mkdir()

    # Create minimal terraform files
    (tf_dir / "main.tf").write_text("""
terraform {
  required_version = ">= 1.0"
}

variable "test_var" {
  type    = string
  default = "test"
}
""")

    return tf_dir
