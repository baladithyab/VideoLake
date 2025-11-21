from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import pytest
from src.api.main import app

client = TestClient(app)

@pytest.fixture
def mock_terraform_manager():
    with patch("src.api.routes.infrastructure.manager") as mock:
        yield mock

def test_get_status(mock_terraform_manager):
    mock_terraform_manager.get_status.return_value = {"s3vector": True, "qdrant": False}
    response = client.get("/api/infrastructure/status")
    assert response.status_code == 200
    assert response.json() == {"s3vector": True, "qdrant": False}

def test_apply_infrastructure(mock_terraform_manager):
    mock_terraform_manager.apply.return_value = "Apply complete!"
    response = client.post("/api/infrastructure/s3vector/apply")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "backend_type": "s3vector",
        "output": "Apply complete!"
    }
    mock_terraform_manager.apply.assert_called_with("s3vector")

def test_destroy_infrastructure(mock_terraform_manager):
    mock_terraform_manager.destroy.return_value = "Destroy complete!"
    response = client.post("/api/infrastructure/s3vector/destroy")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "backend_type": "s3vector",
        "output": "Destroy complete!"
    }
    mock_terraform_manager.destroy.assert_called_with("s3vector")

def test_get_output(mock_terraform_manager):
    mock_terraform_manager.get_outputs.return_value = {"bucket_name": "my-bucket"}
    response = client.get("/api/infrastructure/s3vector/output")
    assert response.status_code == 200
    assert response.json() == {"bucket_name": "my-bucket"}
    mock_terraform_manager.get_outputs.assert_called_with("s3vector")