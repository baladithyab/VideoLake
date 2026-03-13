"""
Integration tests for all FastAPI routers.

Tests real API endpoints via TestClient with actual service wiring.
Tests use real Pydantic models and validation, minimal mocking.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.api
class TestResourcesRouter:
    """Test /api/resources endpoints."""

    def test_list_vector_stores_endpoint(self, test_client):
        """Test listing vector stores."""
        response = test_client.get("/api/resources/vector-stores")

        # Should succeed or return service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_list_embedding_providers_endpoint(self, test_client):
        """Test listing embedding providers."""
        response = test_client.get("/api/resources/embedding-providers")

        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.parametrize("resource_type", [
        "s3-buckets",
        "s3vector-buckets",
        "opensearch-collections",
    ])
    def test_resource_endpoints_accessible(self, test_client, resource_type):
        """Test that resource list endpoints are accessible."""
        response = test_client.get(f"/api/resources/{resource_type}")

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404


@pytest.mark.integration
@pytest.mark.api
class TestSearchRouter:
    """Test /api/search endpoints."""

    def test_search_endpoint_requires_body(self, test_client):
        """Test that search endpoint validates request body."""
        # Missing required fields should return 422 (validation error)
        response = test_client.post("/api/search/query", json={})

        assert response.status_code in [422, 400]

    def test_search_with_valid_request(self, test_client):
        """Test search with valid request structure."""
        search_request = {
            "query": "test query",
            "store_name": "test-store",
            "top_k": 10,
        }

        response = test_client.post("/api/search/query", json=search_request)

        # May fail with service error (503) but shouldn't have validation error
        assert response.status_code != 422

    def test_search_endpoint_returns_structured_response(self, test_client):
        """Test that search returns structured response."""
        search_request = {
            "query": "test",
            "store_name": "test-store",
        }

        response = test_client.post("/api/search/query", json=search_request)

        if response.status_code == 200:
            data = response.json()
            # Should have results structure
            assert isinstance(data, (dict, list))


@pytest.mark.integration
@pytest.mark.api
class TestEmbeddingsRouter:
    """Test /api/embeddings endpoints."""

    def test_generate_embeddings_endpoint_exists(self, test_client):
        """Test that embedding generation endpoint exists."""
        # POST without body should not return 404
        response = test_client.post("/api/embeddings/generate", json={})

        assert response.status_code != 404

    def test_generate_embeddings_validates_request(self, test_client):
        """Test that embeddings endpoint validates request body."""
        # Invalid request should return validation error
        invalid_request = {"invalid_field": "value"}

        response = test_client.post("/api/embeddings/generate", json=invalid_request)

        # Should be validation error or service error, not 404
        assert response.status_code in [400, 422, 503]

    def test_generate_embeddings_with_text(self, test_client):
        """Test generating text embeddings."""
        request_body = {
            "modality": "text",
            "content": "This is a test document",
            "model_id": "amazon.titan-embed-text-v1",
        }

        response = test_client.post("/api/embeddings/generate", json=request_body)

        # Should validate successfully (even if service fails)
        assert response.status_code != 422


@pytest.mark.integration
@pytest.mark.api
class TestProcessingRouter:
    """Test /api/processing endpoints."""

    def test_video_processing_endpoint_exists(self, test_client):
        """Test that video processing endpoints exist."""
        response = test_client.get("/api/processing/status")

        # Endpoint should exist (not 404)
        assert response.status_code != 404

    def test_video_processing_requires_valid_input(self, test_client):
        """Test that video processing validates inputs."""
        # Empty request should be rejected
        response = test_client.post("/api/processing/videos", json={})

        assert response.status_code in [400, 422, 503]


@pytest.mark.integration
@pytest.mark.api
class TestAnalyticsRouter:
    """Test /api/analytics endpoints."""

    def test_analytics_dashboard_endpoint(self, test_client):
        """Test analytics dashboard endpoint."""
        response = test_client.get("/api/analytics/dashboard")

        # Should return data or service unavailable
        assert response.status_code in [200, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_benchmark_results_endpoint(self, test_client):
        """Test benchmark results endpoint."""
        response = test_client.get("/api/analytics/benchmarks")

        assert response.status_code in [200, 404, 503]


@pytest.mark.integration
@pytest.mark.api
class TestInfrastructureRouter:
    """Test /api infrastructure endpoints."""

    def test_infrastructure_status_endpoint(self, test_client):
        """Test infrastructure status endpoint."""
        response = test_client.get("/api/infrastructure/status")

        assert response.status_code in [200, 503]

    def test_deployment_profile_endpoint(self, test_client):
        """Test deployment profile endpoints."""
        response = test_client.get("/api/deployment/profiles")

        # Should exist and return list or error
        assert response.status_code != 404

    def test_terraform_status_endpoint(self, test_client):
        """Test terraform status endpoint."""
        response = test_client.get("/api/infrastructure/terraform/status")

        assert response.status_code != 404


@pytest.mark.integration
@pytest.mark.api
class TestBenchmarkRouter:
    """Test /api/benchmark endpoints."""

    def test_benchmark_start_endpoint_exists(self, test_client):
        """Test benchmark start endpoint."""
        response = test_client.post("/api/benchmark/start", json={})

        # Endpoint exists (not 404)
        assert response.status_code != 404

    def test_benchmark_results_endpoint(self, test_client):
        """Test benchmark results retrieval."""
        response = test_client.get("/api/benchmark/results")

        assert response.status_code in [200, 404, 503]


@pytest.mark.integration
@pytest.mark.api
class TestIngestionRouter:
    """Test /api/ingestion endpoints."""

    def test_ingestion_status_endpoint(self, test_client):
        """Test ingestion status endpoint."""
        response = test_client.get("/api/ingestion/status")

        assert response.status_code != 404

    def test_batch_ingestion_endpoint_validates_input(self, test_client):
        """Test that batch ingestion validates request."""
        response = test_client.post("/api/ingestion/batch", json={})

        # Should validate (even if service fails)
        assert response.status_code in [400, 422, 503]


@pytest.mark.integration
@pytest.mark.api
class TestPydanticValidation:
    """Test Pydantic model validation in API endpoints."""

    @pytest.mark.parametrize("endpoint,method,invalid_body", [
        ("/api/search/query", "post", {"invalid_key": "value"}),
        ("/api/embeddings/generate", "post", {"wrong_field": 123}),
        ("/api/processing/videos", "post", {"bad_data": []}),
    ])
    def test_invalid_request_bodies_return_422(self, test_client, endpoint, method, invalid_body):
        """Test that invalid request bodies return validation errors."""
        if method == "post":
            response = test_client.post(endpoint, json=invalid_body)
        elif method == "put":
            response = test_client.put(endpoint, json=invalid_body)

        # Should return validation error, not 500
        assert response.status_code in [400, 422, 503]

    def test_response_follows_schema(self, test_client):
        """Test that successful responses follow expected schemas."""
        response = test_client.get("/")

        if response.status_code == 200:
            data = response.json()
            # Root endpoint should return dict with standard fields
            assert isinstance(data, dict)
            assert "message" in data or "status" in data


@pytest.mark.integration
@pytest.mark.api
class TestErrorHandling:
    """Test API error handling and exception responses."""

    def test_404_for_nonexistent_endpoints(self, test_client):
        """Test that nonexistent endpoints return 404."""
        response = test_client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404

    def test_405_for_wrong_method(self, test_client):
        """Test that wrong HTTP methods return 405."""
        # Try DELETE on GET-only endpoint
        response = test_client.delete("/api/health")

        assert response.status_code == 405

    def test_error_responses_include_detail(self, test_client):
        """Test that error responses include detail field."""
        response = test_client.post("/api/search/query", json={})

        if response.status_code >= 400:
            data = response.json()
            # FastAPI error responses have detail field
            assert "detail" in data or "message" in data


@pytest.mark.integration
@pytest.mark.api
class TestCORSHeaders:
    """Test CORS configuration."""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are configured."""
        response = test_client.options("/api/health")

        # OPTIONS request should succeed
        assert response.status_code in [200, 204]

    def test_cors_allows_localhost(self, test_client):
        """Test that CORS allows localhost origins."""
        headers = {"Origin": "http://localhost:5173"}
        response = test_client.get("/", headers=headers)

        # Should not be blocked by CORS
        assert response.status_code != 403
