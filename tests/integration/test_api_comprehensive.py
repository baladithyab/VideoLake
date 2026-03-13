import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.api.main import app
from src.services.interfaces.search_service_interface import SearchResult, SearchResponse
from src.services.terraform_infrastructure_manager import DeploymentStatus
from src.core.dependencies import get_search_engine

client = TestClient(app)

# --- Mocks ---

@pytest.fixture
def mock_terraform_manager():
    # Patching the one used in src/api/routes/infrastructure.py
    # It uses `manager` instance of `TerraformManager`
    with patch('src.api.routes.infrastructure.manager') as mock:
        yield mock

@pytest.fixture
def mock_ingestion_pipeline():
    with patch('src.api.routes.ingestion.VideoIngestionPipeline') as mock:
        yield mock

@pytest.fixture
def mock_search_engine():
    with patch('src.api.routers.search.SimilaritySearchEngine') as mock:
        yield mock

@pytest.fixture
def mock_benchmark_service():
    with patch('src.api.routers.benchmark.benchmark_service') as mock:
        yield mock

@pytest.fixture
def mock_dependencies():
    # Create a mock engine
    mock_engine = MagicMock()
    return mock_engine

# --- Infrastructure Tests ---

def test_infrastructure_status(mock_terraform_manager):
    # Setup mock
    # src/api/routes/infrastructure.py returns manager.get_status() which returns Dict[str, bool]
    mock_status = {
        "qdrant": True,
        "lancedb": False
    }
    mock_terraform_manager.get_status.return_value = mock_status

    response = client.get("/api/infrastructure/status")
    
    assert response.status_code == 200
    data = response.json()
    assert data["qdrant"] is True
    assert data["lancedb"] is False

def test_infrastructure_deploy(mock_terraform_manager):
    # Setup mock
    # src/api/routes/infrastructure.py uses POST /{backend_type}/apply
    mock_terraform_manager.apply.return_value = "Terraform output..."

    response = client.post("/api/infrastructure/qdrant/apply")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["backend_type"] == "qdrant"
    assert data["output"] == "Terraform output..."

def test_infrastructure_destroy(mock_terraform_manager):
    # Setup mock
    # src/api/routes/infrastructure.py uses POST /{backend_type}/destroy
    mock_terraform_manager.destroy.return_value = "Terraform destroy output..."

    response = client.post("/api/infrastructure/qdrant/destroy")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["backend_type"] == "qdrant"
    assert data["output"] == "Terraform destroy output..."

# --- Ingestion Tests ---

def test_ingestion_start(mock_ingestion_pipeline):
    # Setup mock instance
    mock_pipeline_instance = mock_ingestion_pipeline.return_value
    mock_result = MagicMock(job_id="job-123", status="started", message="Ingestion started")
    mock_pipeline_instance.process_video.return_value = mock_result

    payload = {
        "video_path": "s3://bucket/video.mp4",
        "model_type": "marengo",
        "backend_types": ["qdrant"]
    }
    response = client.post("/api/ingestion/start", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-123"
    assert data["status"] == "started"

def test_ingestion_status(mock_ingestion_pipeline):
    # Setup mock instance
    mock_pipeline_instance = mock_ingestion_pipeline.return_value
    mock_pipeline_instance.get_status.return_value = {
        "status": "SUCCEEDED",
        "startDate": "2023-01-01T00:00:00Z",
        "stopDate": "2023-01-01T00:01:00Z",
        "input": {},
        "output": {}
    }

    response = client.get("/api/ingestion/status/arn:aws:states:execution:123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCEEDED"

# --- Search Tests ---

def test_search_query(mock_dependencies):
    # Setup mock engine (injected via dependency)
    mock_engine = mock_dependencies
    
    from src.services.interfaces.search_service_interface import QueryInputType, IndexType
    
    mock_result = SearchResponse(
        results=[
            SearchResult(
                key="video1",
                similarity_score=0.95,
                metadata={"title": "Test Video"},
                content_type="video"
            )
        ],
        total_results=1,
        query_id="test-query-id",
        input_type=QueryInputType.TEXT,
        index_type=IndexType.MARENGO_MULTIMODAL,
        processing_time_ms=100,
        result_distribution={},
        similarity_range=(0.0, 1.0),
        cost_estimate=0.0,
        search_suggestions=[]
    )
    mock_engine.find_similar_content.return_value = mock_result

    payload = {
        "query_text": "test query",
        "top_k": 5,
        "backend": "qdrant"
    }
    
    # Mocking get_search_engine dependency might not be enough if the router does something else before calling it.
    # The error was 500 Internal Server Error.
    # Logs: AWS error starting text embedding: ValidationException - Invalid S3 credentials
    # This suggests that the router or dependency is trying to use AWS credentials which are missing/invalid in the test environment.
    # We need to mock the AWS clients or the service that uses them.
    # The error comes from src.services.twelvelabs_video_processing.py.
    # It seems the search router might be triggering something that uses this.
    # Wait, the search router calls search_engine.find_similar_content.
    # If we mocked search_engine, why is it calling real AWS services?
    # Maybe the dependency override didn't work as expected or there's another dependency.
    # In main.py: app.include_router(search.router, ...)
    # In search.py: async def search_query(..., search_engine: SimilaritySearchEngine = Depends(get_search_engine)):
    # We patched src.api.routers.search.get_search_engine.
    # But we need to override the dependency in the app.
    
    app.dependency_overrides[get_search_engine] = lambda: mock_engine
    
    response = client.post("/api/search/query", json=payload)
    
    # Clear override
    app.dependency_overrides = {}
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "video1"

def test_compare_backends(mock_search_engine):
    # Setup mock instance (used directly in compare_backends)
    mock_engine_instance = mock_search_engine.return_value
    
    from src.services.interfaces.search_service_interface import QueryInputType, IndexType

    mock_result = SearchResponse(
        results=[
            SearchResult(
                key="video1",
                similarity_score=0.95,
                metadata={"title": "Test Video"},
                content_type="video"
            )
        ],
        total_results=1,
        query_id="test-query-id",
        input_type=QueryInputType.TEXT,
        index_type=IndexType.MARENGO_MULTIMODAL,
        processing_time_ms=100,
        result_distribution={},
        similarity_range=(0.0, 1.0),
        cost_estimate=0.0,
        search_suggestions=[]
    )
    mock_engine_instance.search.return_value = mock_result

    payload = {
        "query_text": "test query",
        "backends": ["qdrant", "lancedb"],
        "top_k": 5
    }
    
    # The error was 422 Unprocessable Entity.
    # This usually means validation error.
    # Let's check the payload against the schema.
    # compare_backends(query_text: str, backends: Optional[List[str]] = None, top_k: int = 10, index_arn: Optional[str] = None)
    # The payload looks correct.
    # However, the error log says: Error response: ValidationError
    # Maybe it's the validator decorators in search.py that are failing?
    # Or maybe the mock isn't working and it's trying to instantiate the real engine which fails?
    # In compare_backends, it does: search_engine = SimilaritySearchEngine()
    # This instantiates the class directly, not via dependency injection.
    # So patching 'src.api.routers.search.SimilaritySearchEngine' should work.
    # But wait, if the validation fails, it happens before the function body is executed.
    # The validators in SearchQueryRequest might be the issue if they are used here.
    # But compare_backends uses query parameters, not a Pydantic model.
    # Wait, looking at the code:
    # @router.post("/compare-backends")
    # async def compare_backends(
    #     query_text: str,
    #     backends: Optional[List[str]] = None,
    #     top_k: int = 10,
    #     index_arn: Optional[str] = None
    # ):
    # It expects query parameters, not a JSON body!
    # But I'm sending json=payload.
    # I should send params=payload or change the endpoint to accept a body.
    # Given it's a POST, it probably should accept a body, but the signature suggests query params.
    # Let's try sending as query params.
    
    # Actually, for POST requests, FastAPI expects body if it's a Pydantic model, or query params if simple types.
    # Here they are simple types, so they are query params.
    # But `backends` is a list, so it should be passed as `backends=qdrant&backends=lancedb`.
    
    response = client.post("/api/search/compare-backends", params=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "qdrant" in data["results"]
    assert "lancedb" in data["results"]
    assert "comparison" in data

# --- Benchmark Tests ---

@pytest.mark.asyncio
async def test_benchmark_start(mock_benchmark_service):
    # Setup mock
    # The service method is async, so the mock should return a coroutine or be awaited?
    # In the router: job_id = await benchmark_service.start_benchmark(...)
    # So the mock return value should be awaitable if it's an AsyncMock, or we configure it to return a future.
    # But MagicMock isn't awaitable by default.
    
    # We need to make the return value awaitable.
    f = asyncio.Future()
    f.set_result("bench-123")
    mock_benchmark_service.start_benchmark.return_value = f

    payload = {
        "backends": ["qdrant"],
        "config": {"vectors": 1000}
    }
    # TestClient handles async endpoints synchronously, but the internal await needs the mock to be awaitable.
    response = client.post("/api/benchmark/start", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "bench-123"
    assert data["status"] == "pending"

def test_benchmark_results(mock_benchmark_service):
    # Setup mock
    mock_benchmark_service.get_results.return_value = {
        "job_id": "bench-123",
        "status": "completed",
        "results": {}
    }

    response = client.get("/api/benchmark/results/bench-123")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"

def test_benchmark_list(mock_benchmark_service):
    # Setup mock
    mock_benchmark_service.list_benchmarks.return_value = [
        {"job_id": "bench-123", "status": "completed"}
    ]

    response = client.get("/api/benchmark/list")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["job_id"] == "bench-123"