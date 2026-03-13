"""
Unit tests for the comprehensive benchmarks API.

Tests the /api/benchmarks endpoints for comprehensive benchmark functionality.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# Import the FastAPI app
from src.api.main import app

client = TestClient(app)


class TestComprehensiveBenchmarkAPI:
    """Test suite for comprehensive benchmark API endpoints"""

    @pytest.fixture
    def mock_backend_adapter(self):
        """Mock backend adapter"""
        adapter = Mock()
        adapter.index_vectors = Mock(return_value={"success": True})
        adapter.search_vectors = Mock(return_value=[{"id": 1, "score": 0.9}])
        adapter.get_endpoint_info = Mock(return_value={"type": "test", "endpoint": "test://localhost"})
        return adapter

    @pytest.fixture
    def mock_get_backend_adapter(self, mock_backend_adapter):
        """Mock the get_backend_adapter function"""
        with patch('src.api.routers.benchmarks.get_backend_adapter', return_value=mock_backend_adapter):
            yield

    def test_start_comprehensive_benchmark(self, mock_get_backend_adapter):
        """Test starting a comprehensive benchmark"""
        request_data = {
            "backends": ["s3vector", "qdrant-ecs"],
            "config": {
                "vector_dimension": 1536,
                "query_count": 100,
                "vector_counts": [1000]
            }
        }

        response = client.post("/api/benchmarks/comprehensive/start", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["backends"] == ["s3vector", "qdrant-ecs"]
        assert data["estimated_duration_minutes"] is not None

    def test_start_benchmark_without_backend_adapter(self):
        """Test error when backend adapter is not available"""
        with patch('src.api.routers.benchmarks.get_backend_adapter', None):
            request_data = {
                "backends": ["s3vector"],
                "config": {}
            }

            response = client.post("/api/benchmarks/comprehensive/start", json=request_data)

            assert response.status_code == 500
            assert "Backend adapters not available" in response.json()["detail"]

    def test_get_benchmark_status_not_found(self):
        """Test getting status for non-existent job"""
        response = client.get("/api/benchmarks/comprehensive/status/nonexistent-job")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_benchmark_status(self, mock_get_backend_adapter):
        """Test getting status of a running benchmark"""
        # First start a benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {"vector_dimension": 128, "vector_counts": [100]}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Then get status
        response = client.get(f"/api/benchmarks/comprehensive/status/{job_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == job_id
        assert data["status"] in ["pending", "running", "completed"]
        assert data["backends"] == ["s3vector"]
        assert "completed_backends" in data
        assert "failed_backends" in data
        assert "progress_percentage" in data

    def test_get_benchmark_results(self, mock_get_backend_adapter):
        """Test getting results of a benchmark"""
        # Start a benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {"vector_dimension": 128, "vector_counts": [100]}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Get results (immediately, so it will be pending/running)
        response = client.get(f"/api/benchmarks/comprehensive/results/{job_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["job_id"] == job_id
        assert "status" in data
        assert "backends" in data

    def test_get_benchmark_results_not_found(self):
        """Test getting results for non-existent job"""
        response = client.get("/api/benchmarks/comprehensive/results/nonexistent-job")

        assert response.status_code == 404

    def test_get_benchmark_comparison_not_found(self):
        """Test getting comparison for non-existent job"""
        response = client.get("/api/benchmarks/comprehensive/comparison/nonexistent-job")

        assert response.status_code == 404

    def test_get_benchmark_report_formats(self, mock_get_backend_adapter):
        """Test generating reports in different formats"""
        # Start and complete a mock benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {"vector_dimension": 128, "vector_counts": [100]}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Mock the job as completed
        from src.api.routers.benchmarks import active_jobs
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["results"] = {
                "s3vector": {
                    "status": "completed",
                    "latency": {"p99_ms": 1.5},
                    "throughput": {"qps": 1000}
                }
            }

        # Test markdown format
        response = client.get(f"/api/benchmarks/comprehensive/report/{job_id}?format=markdown")
        assert response.status_code == 200
        assert response.json()["format"] == "markdown"

        # Test json format
        response = client.get(f"/api/benchmarks/comprehensive/report/{job_id}?format=json")
        assert response.status_code == 200
        assert response.json()["format"] == "json"

        # Test csv format
        response = client.get(f"/api/benchmarks/comprehensive/report/{job_id}?format=csv")
        assert response.status_code == 200
        assert response.json()["format"] == "csv"

    def test_get_benchmark_report_invalid_format(self, mock_get_backend_adapter):
        """Test report generation with invalid format"""
        request_data = {
            "backends": ["s3vector"],
            "config": {}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Invalid format
        response = client.get(f"/api/benchmarks/comprehensive/report/{job_id}?format=xml")
        assert response.status_code == 422  # Validation error

    def test_list_benchmark_jobs(self, mock_get_backend_adapter):
        """Test listing all benchmark jobs"""
        # Start a few benchmarks
        for i in range(3):
            request_data = {
                "backends": ["s3vector"],
                "config": {"vector_dimension": 128}
            }
            client.post("/api/benchmarks/comprehensive/start", json=request_data)

        # List all jobs
        response = client.get("/api/benchmarks/comprehensive/list")

        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "jobs" in data
        assert len(data["jobs"]) >= 3
        assert all("job_id" in job for job in data["jobs"])
        assert all("status" in job for job in data["jobs"])

    def test_list_benchmark_jobs_with_status_filter(self, mock_get_backend_adapter):
        """Test listing benchmark jobs with status filter"""
        # Start a benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {}
        }
        client.post("/api/benchmarks/comprehensive/start", json=request_data)

        # List pending jobs
        response = client.get("/api/benchmarks/comprehensive/list?status=pending")

        assert response.status_code == 200
        data = response.json()

        # Should have at least the job we just created
        assert data["total"] >= 1
        assert all(job["status"] == "pending" for job in data["jobs"])

    def test_list_benchmark_jobs_with_limit(self, mock_get_backend_adapter):
        """Test listing benchmark jobs with limit"""
        response = client.get("/api/benchmarks/comprehensive/list?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["jobs"]) <= 5

    def test_cancel_benchmark_job(self, mock_get_backend_adapter):
        """Test cancelling a running benchmark job"""
        # Start a benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Cancel it
        response = client.delete(f"/api/benchmarks/comprehensive/{job_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cancelled"
        assert job_id in data["message"]

    def test_cancel_nonexistent_job(self):
        """Test cancelling a non-existent job"""
        response = client.delete("/api/benchmarks/comprehensive/nonexistent-job")

        assert response.status_code == 404

    def test_cancel_completed_job(self, mock_get_backend_adapter):
        """Test cancelling an already completed job"""
        # Start a benchmark
        request_data = {
            "backends": ["s3vector"],
            "config": {}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Mock as completed
        from src.api.routers.benchmarks import active_jobs
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "completed"

        # Try to cancel
        response = client.delete(f"/api/benchmarks/comprehensive/{job_id}")

        assert response.status_code == 400
        assert "cannot cancel" in response.json()["detail"]

    def test_benchmark_configuration_defaults(self, mock_get_backend_adapter):
        """Test that default configuration is applied when not provided"""
        request_data = {
            "backends": ["s3vector"],
            "config": {}  # Empty config, should use defaults
        }

        response = client.post("/api/benchmarks/comprehensive/start", json=request_data)

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Verify defaults were applied
        from src.api.routers.benchmarks import active_jobs
        if job_id in active_jobs:
            config = active_jobs[job_id]["config"]
            assert config["vector_dimension"] == 1536  # Default
            assert config["query_count"] == 1000  # Default

    def test_benchmark_with_custom_configuration(self, mock_get_backend_adapter):
        """Test benchmark with custom configuration"""
        request_data = {
            "backends": ["s3vector"],
            "config": {
                "vector_dimension": 768,
                "query_count": 500,
                "vector_counts": [500, 5000],
                "enable_recall_testing": False,
                "enable_cold_start_testing": False
            }
        }

        response = client.post("/api/benchmarks/comprehensive/start", json=request_data)

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Verify custom config was applied
        from src.api.routers.benchmarks import active_jobs
        if job_id in active_jobs:
            config = active_jobs[job_id]["config"]
            assert config["vector_dimension"] == 768
            assert config["query_count"] == 500
            assert config["vector_counts"] == [500, 5000]
            assert config["enable_recall_testing"] is False

    def test_multiple_backends_benchmark(self, mock_get_backend_adapter):
        """Test benchmark with multiple backends"""
        request_data = {
            "backends": ["s3vector", "qdrant-ecs", "lancedb-s3"],
            "config": {"vector_dimension": 256}
        }

        response = client.post("/api/benchmarks/comprehensive/start", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert len(data["backends"]) == 3
        assert data["estimated_duration_minutes"] > 0

    def test_benchmark_result_structure(self, mock_get_backend_adapter):
        """Test that benchmark results have the expected structure"""
        request_data = {
            "backends": ["s3vector"],
            "config": {"vector_counts": [100]}
        }

        start_response = client.post("/api/benchmarks/comprehensive/start", json=request_data)
        job_id = start_response.json()["job_id"]

        # Mock a completed result
        from src.api.routers.benchmarks import active_jobs
        if job_id in active_jobs:
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["results"] = {
                "s3vector": {
                    "backend": "s3vector",
                    "variant": "default",
                    "status": "completed",
                    "latency": {
                        "p50_ms": 1.0,
                        "p95_ms": 2.0,
                        "p99_ms": 3.0
                    },
                    "throughput": {
                        "qps": 1000,
                        "sustained_qps": 950,
                        "total_queries": 100
                    },
                    "cost": {
                        "monthly_cost_estimate_usd": 2.50
                    }
                }
            }

        # Get results
        response = client.get(f"/api/benchmarks/comprehensive/results/{job_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert "s3vector" in data["results"]
        result = data["results"]["s3vector"]
        assert "latency" in result
        assert "throughput" in result
        assert "cost" in result


@pytest.mark.asyncio
class TestBenchmarkRunner:
    """Test the comprehensive benchmark runner logic"""

    @pytest.fixture
    def mock_adapter(self):
        """Mock backend adapter for testing"""
        adapter = Mock()
        adapter.index_vectors = Mock(return_value={"success": True})
        adapter.search_vectors = Mock(return_value=[{"id": 1, "score": 0.9}])
        return adapter

    async def test_runner_initialization(self, mock_adapter):
        """Test benchmark runner initialization"""
        from src.services.benchmark_models import BenchmarkConfiguration
        from src.services.comprehensive_benchmark_runner import ComprehensiveBenchmarkRunner

        config = BenchmarkConfiguration(vector_dimension=128, vector_counts=[100])
        runner = ComprehensiveBenchmarkRunner(
            backend="test_backend",
            variant="test_variant",
            adapter=mock_adapter,
            config=config
        )

        assert runner.backend == "test_backend"
        assert runner.variant == "test_variant"
        assert runner.config.vector_dimension == 128

    async def test_vector_generation(self, mock_adapter):
        """Test random vector generation"""
        from src.services.benchmark_models import BenchmarkConfiguration
        from src.services.comprehensive_benchmark_runner import ComprehensiveBenchmarkRunner

        config = BenchmarkConfiguration()
        runner = ComprehensiveBenchmarkRunner(
            backend="test",
            variant="test",
            adapter=mock_adapter,
            config=config
        )

        vectors = runner.generate_vectors(100, 128)

        assert vectors.shape == (100, 128)
        assert vectors.dtype.name == 'float32'

        # Check normalization (vectors should have unit length)
        import numpy as np
        norms = np.linalg.norm(vectors, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-6)
