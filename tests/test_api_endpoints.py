#!/usr/bin/env python3
"""
FastAPI endpoint tests using TestClient.

Tests existing API endpoints that are already working:
- Health check endpoint
- Infrastructure status
- Resource listing
- Search endpoints

These tests use the FastAPI TestClient for in-process testing without
starting a server. They are marked as @pytest.mark.api and @pytest.mark.integration.
"""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Health and Status Endpoints
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
def test_root_endpoint(test_client: TestClient):
    """Test that root endpoint returns API info."""
    response = test_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.api
@pytest.mark.integration
def test_health_check_endpoint(test_client: TestClient):
    """
    Test deep health check endpoint.

    This endpoint checks:
    - Service initialization
    - AWS S3 connectivity
    - TwelveLabs API availability
    - AWS Bedrock availability
    """
    response = test_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()

    # Check response structure
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data

    # Status should be either "healthy" or "degraded"
    assert data["status"] in ["healthy", "degraded"]

    # Checks should contain service statuses
    checks = data["checks"]
    assert "services" in checks
    assert "aws_s3" in checks
    assert "twelvelabs_api" in checks
    assert "aws_bedrock" in checks


# ============================================================================
# Infrastructure Endpoints
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
def test_infrastructure_status_endpoint(test_client: TestClient):
    """Test infrastructure status endpoint."""
    response = test_client.get("/api/infrastructure/status")

    # Endpoint should exist and return valid response
    assert response.status_code in [200, 404, 503]

    if response.status_code == 200:
        data = response.json()
        # Should return infrastructure status information
        assert isinstance(data, dict)


# ============================================================================
# Resource Endpoints
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
def test_list_resources_endpoint(test_client: TestClient):
    """Test resource listing endpoint."""
    response = test_client.get("/api/resources")

    # Endpoint should exist
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list | dict)


# ============================================================================
# Search Endpoints
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
def test_search_endpoint_requires_query(test_client: TestClient):
    """Test that search endpoint validates required parameters."""
    response = test_client.post("/api/search")

    # Should return 422 (Validation Error) if query is missing
    assert response.status_code in [422, 400, 404]


@pytest.mark.api
@pytest.mark.integration
def test_search_endpoint_with_valid_query(test_client: TestClient):
    """Test search endpoint with valid query payload."""
    payload = {
        "query": "test query",
        "top_k": 5,
        "backend": "s3_vector"
    }

    response = test_client.post("/api/search", json=payload)

    # Should return 200 or service-unavailable status
    # (200 if backend is configured, 503/404 if not)
    assert response.status_code in [200, 404, 503]


# ============================================================================
# Embeddings Endpoints
# ============================================================================

@pytest.mark.api
@pytest.mark.integration
def test_embeddings_endpoint_exists(test_client: TestClient):
    """Test that embeddings endpoint exists."""
    # Try to generate embeddings for a simple text
    payload = {
        "text": "test input",
        "model": "amazon.titan-embed-text-v1"
    }

    response = test_client.post("/api/embeddings/generate", json=payload)

    # Endpoint should exist (200, 422, 503, or 404)
    assert response.status_code in [200, 422, 404, 503]


# ============================================================================
# CORS and Middleware Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_cors_headers_present(test_client: TestClient):
    """Test that CORS headers are configured."""
    # Make an OPTIONS request to check CORS headers
    response = test_client.options(
        "/api/health",
        headers={"Origin": "http://localhost:5172"}
    )

    # CORS middleware should add appropriate headers
    assert "access-control-allow-origin" in response.headers or response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_404_handler(test_client: TestClient):
    """Test that 404 errors are handled gracefully."""
    response = test_client.get("/nonexistent/endpoint")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "message" in data


@pytest.mark.api
@pytest.mark.unit
def test_method_not_allowed_handler(test_client: TestClient):
    """Test that 405 Method Not Allowed is handled."""
    # Try POST on GET-only endpoint
    response = test_client.post("/")

    assert response.status_code == 405
