"""
Integration tests for health and root API endpoints.

Tests real FastAPI app with TestClient, validating service initialization
and health check responses.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.api
class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_api_info(self, test_client):
        """Test that root endpoint returns API information."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"


@pytest.mark.integration
@pytest.mark.api
class TestHealthCheck:
    """Test health check endpoint with real service dependencies."""

    def test_health_check_endpoint_exists(self, test_client):
        """Test that health check endpoint is accessible."""
        response = test_client.get("/api/health")

        # Should return 200 (healthy) or 503 (unhealthy), not 404
        assert response.status_code in [200, 503]

    def test_health_check_returns_service_status(self, test_client):
        """Test that health check returns service status information."""
        response = test_client.get("/api/health")
        data = response.json()

        # Health check should return structured status
        assert "status" in data or "checks" in data or "overall_healthy" in data

    def test_health_check_with_timeout(self, test_client):
        """Test that health check doesn't hang indefinitely."""
        import time
        start = time.time()

        response = test_client.get("/api/health")
        elapsed = time.time() - start

        # Health check should complete within reasonable time
        assert elapsed < 10.0, "Health check took too long"
        assert response.status_code in [200, 503]

    @pytest.mark.parametrize("endpoint", [
        "/api/health",
        "/",
    ])
    def test_endpoints_return_json(self, test_client, endpoint):
        """Test that health endpoints return valid JSON."""
        response = test_client.get(endpoint)

        # Should not raise JSONDecodeError
        data = response.json()
        assert isinstance(data, dict)
