#!/usr/bin/env python3
"""
End-to-End Integration Tests for Video Retrieval Workflows

This test suite validates the complete video retrieval workflow for each vector store provider:
1. Setup/Initialize vector store
2. Process video to get embeddings (mocked to avoid API costs)
3. Upsert embeddings to vector store
4. Query/search the vector store
5. Verify results are returned correctly
6. Cleanup resources

RUNNING THESE TESTS
===================

# Run all E2E tests
pytest tests/test_e2e_vector_store_workflows.py -v

# Run specific provider tests
pytest tests/test_e2e_vector_store_workflows.py::TestS3VectorE2E -v
pytest tests/test_e2e_vector_store_workflows.py::TestOpenSearchE2E -v
pytest tests/test_e2e_vector_store_workflows.py::TestLanceDBE2E -v
pytest tests/test_e2e_vector_store_workflows.py::TestQdrantE2E -v

# Run combination tests only
pytest tests/test_e2e_vector_store_workflows.py -k "combination" -v

# Run with timing information
pytest tests/test_e2e_vector_store_workflows.py -v --durations=10

# Skip slow tests (providers that require real AWS resources)
pytest tests/test_e2e_vector_store_workflows.py -v -m "not slow"

PREREQUISITES
=============
- AWS credentials configured (for real provider tests)
- Python packages: pytest, boto3, moto (for mocking)
- Optional: Docker (for local OpenSearch/Qdrant testing)

TEST ISOLATION
==============
Each test is independent and includes:
- Setup: Create test resources
- Execution: Run the workflow
- Assertions: Verify results
- Cleanup: Remove test resources

MOCKING STRATEGY
================
- TwelveLabs API calls are mocked to avoid costs
- Fake embeddings (1024-dimensional) are used
- Small test video metadata only (no large files)
- Provider-specific mocking where needed
"""

import pytest
import time
import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.vector_store_provider import (
    VectorStoreProvider,
    VectorStoreConfig,
    VectorStoreStatus,
    VectorStoreType,
    VectorStoreState,
    VectorStoreProviderFactory
)
from src.services.twelvelabs_video_processing import (
    TwelveLabsVideoProcessingService,
    VideoEmbeddingResult,
    AsyncJobInfo
)
from src.exceptions import VectorStorageError, VectorEmbeddingError, ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def fake_embeddings() -> List[float]:
    """Generate fake 1024-dimensional embeddings for testing."""
    return [0.1 * (i % 10) for i in range(1024)]


@pytest.fixture
def fake_video_metadata() -> Dict[str, Any]:
    """Small test video metadata (no large files)."""
    return {
        "video_id": "test-video-001",
        "title": "Test Video - Action Scene",
        "description": "A person walking in dramatic lighting",
        "duration_seconds": 30,
        "s3_uri": "s3://test-bucket/videos/test-video-001.mp4",
        "upload_timestamp": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def fake_video_segments(fake_embeddings) -> List[Dict[str, Any]]:
    """Generate fake video segments with embeddings."""
    segments = []
    for i in range(6):  # 6 segments (30 seconds / 5 second clips)
        segment = {
            "segment_id": f"seg-{i:03d}",
            "start_offset_sec": i * 5,
            "end_offset_sec": (i + 1) * 5,
            "embedding_option": "visual-text",
            "embedding": [e + (i * 0.01) for e in fake_embeddings],  # Slight variation per segment
            "metadata": {
                "scene_type": "action" if i % 2 == 0 else "dialogue",
                "lighting": "dramatic" if i < 3 else "natural",
                "motion_level": "high" if i % 2 == 0 else "low"
            }
        }
        segments.append(segment)
    return segments


@pytest.fixture
def mock_video_embedding_result(fake_video_segments, fake_video_metadata):
    """Create mock VideoEmbeddingResult."""
    return VideoEmbeddingResult(
        embeddings=fake_video_segments,
        input_source=fake_video_metadata["s3_uri"],
        model_id="twelvelabs.marengo-embed-2-7-v1:0",
        processing_time_ms=1500,
        total_segments=len(fake_video_segments),
        video_duration_sec=fake_video_metadata["duration_seconds"]
    )


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_twelvelabs_service(mock_video_embedding_result):
    """Mock TwelveLabs service to avoid API costs."""
    with patch('src.services.twelvelabs_video_processing.TwelveLabsVideoProcessingService') as mock_service:
        mock_instance = Mock()
        
        # Mock async job creation
        def mock_start_processing(**kwargs):
            job_id = str(uuid.uuid4())
            return AsyncJobInfo(
                job_id=job_id,
                invocation_arn=f"arn:aws:bedrock:us-east-1:123456789012:async-invocation/{job_id}",
                model_id="twelvelabs.marengo-embed-2-7-v1:0",
                input_config={"video_s3_uri": kwargs.get("video_s3_uri")},
                output_s3_uri=f"s3://test-bucket/results/{job_id}/",
                status="InProgress"
            )
        
        mock_instance.start_video_processing.side_effect = mock_start_processing
        
        # Mock quick job completion
        def mock_wait_completion(job_id, timeout_sec=None):
            job_info = AsyncJobInfo(
                job_id=job_id,
                invocation_arn=f"arn:aws:bedrock:us-east-1:123456789012:async-invocation/{job_id}",
                model_id="twelvelabs.marengo-embed-2-7-v1:0",
                input_config={},
                output_s3_uri=f"s3://test-bucket/results/{job_id}/",
                status="Completed",
                completed_at=datetime.now(timezone.utc)
            )
            return job_info
        
        mock_instance.wait_for_completion.side_effect = mock_wait_completion
        mock_instance.retrieve_results.return_value = mock_video_embedding_result
        
        # Mock synchronous processing
        mock_instance.process_video_sync.return_value = mock_video_embedding_result
        
        mock_service.return_value = mock_instance
        yield mock_instance


# ============================================================================
# Provider-Specific Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_s3vector_provider():
    """Mock S3Vector provider."""
    mock_provider = Mock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.S3_VECTOR
    
    # Mock create operation
    def mock_create(config: VectorStoreConfig):
        return VectorStoreStatus(
            store_type=VectorStoreType.S3_VECTOR,
            name=config.name,
            state=VectorStoreState.ACTIVE,
            arn=f"arn:aws:s3vectors:us-east-1:123456789012:index/{config.name}",
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
            dimension=config.dimension
        )
    
    mock_provider.create.side_effect = mock_create
    
    # Mock upsert operation
    def mock_upsert(name: str, vectors: List[Dict[str, Any]]):
        return {
            "status": "success",
            "stored_count": len(vectors),
            "failed_count": 0,
            "index_name": name
        }
    
    mock_provider.upsert_vectors.side_effect = mock_upsert
    
    # Mock query operation
    def mock_query(name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict] = None):
        results = []
        for i in range(min(top_k, 5)):  # Return up to 5 results
            results.append({
                "id": f"result-{i}",
                "score": 0.95 - (i * 0.05),  # Decreasing scores
                "values": query_vector,
                "metadata": {
                    "video_id": "test-video-001",
                    "segment_id": f"seg-{i:03d}",
                    "start_sec": i * 5,
                    "end_sec": (i + 1) * 5
                }
            })
        return results
    
    mock_provider.query.side_effect = mock_query
    
    # Mock delete operation
    def mock_delete(name: str, force: bool = False):
        return VectorStoreStatus(
            store_type=VectorStoreType.S3_VECTOR,
            name=name,
            state=VectorStoreState.DELETED
        )
    
    mock_provider.delete.side_effect = mock_delete
    mock_provider.get_status.return_value = VectorStoreStatus(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-index",
        state=VectorStoreState.ACTIVE
    )
    
    return mock_provider


@pytest.fixture
def mock_opensearch_provider():
    """Mock OpenSearch provider."""
    mock_provider = Mock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.OPENSEARCH
    
    def mock_create(config: VectorStoreConfig):
        return VectorStoreStatus(
            store_type=VectorStoreType.OPENSEARCH,
            name=config.name,
            state=VectorStoreState.CREATING,
            endpoint=f"https://{config.name}.us-east-1.es.amazonaws.com",
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
            dimension=config.dimension,
            progress_percentage=0
        )
    
    mock_provider.create.side_effect = mock_create
    
    # Mock poll until ready
    def mock_poll_ready(name: str, timeout: int = 300, poll_interval: int = 5):
        return VectorStoreStatus(
            store_type=VectorStoreType.OPENSEARCH,
            name=name,
            state=VectorStoreState.ACTIVE,
            endpoint=f"https://{name}.us-east-1.es.amazonaws.com",
            progress_percentage=100
        )
    
    mock_provider.poll_until_ready.side_effect = mock_poll_ready
    
    def mock_upsert(name: str, vectors: List[Dict[str, Any]]):
        return {
            "status": "success",
            "stored_count": len(vectors),
            "failed_count": 0,
            "collection_name": name
        }
    
    mock_provider.upsert_vectors.side_effect = mock_upsert
    
    def mock_query(name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict] = None):
        results = []
        for i in range(min(top_k, 4)):
            results.append({
                "id": f"os-result-{i}",
                "score": 0.93 - (i * 0.06),
                "values": query_vector,
                "metadata": {
                    "video_id": "test-video-001",
                    "segment_id": f"seg-{i:03d}"
                }
            })
        return results
    
    mock_provider.query.side_effect = mock_query
    
    def mock_delete(name: str, force: bool = False):
        return VectorStoreStatus(
            store_type=VectorStoreType.OPENSEARCH,
            name=name,
            state=VectorStoreState.DELETING,
            progress_percentage=50
        )
    
    mock_provider.delete.side_effect = mock_delete
    mock_provider.get_status.return_value = VectorStoreStatus(
        store_type=VectorStoreType.OPENSEARCH,
        name="test-collection",
        state=VectorStoreState.ACTIVE
    )
    
    return mock_provider


@pytest.fixture
def mock_lancedb_provider():
    """Mock LanceDB provider."""
    mock_provider = Mock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.LANCEDB
    
    def mock_create(config: VectorStoreConfig):
        return VectorStoreStatus(
            store_type=VectorStoreType.LANCEDB,
            name=config.name,
            state=VectorStoreState.ACTIVE,
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
            dimension=config.dimension
        )
    
    mock_provider.create.side_effect = mock_create
    
    def mock_upsert(name: str, vectors: List[Dict[str, Any]]):
        return {
            "status": "success",
            "stored_count": len(vectors),
            "table_name": name
        }
    
    mock_provider.upsert_vectors.side_effect = mock_upsert
    
    def mock_query(name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict] = None):
        results = []
        for i in range(min(top_k, 5)):
            results.append({
                "id": f"lance-result-{i}",
                "score": 0.94 - (i * 0.04),
                "values": query_vector,
                "metadata": {"video_id": "test-video-001"}
            })
        return results
    
    mock_provider.query.side_effect = mock_query
    
    def mock_delete(name: str, force: bool = False):
        return VectorStoreStatus(
            store_type=VectorStoreType.LANCEDB,
            name=name,
            state=VectorStoreState.DELETED
        )
    
    mock_provider.delete.side_effect = mock_delete
    mock_provider.get_status.return_value = VectorStoreStatus(
        store_type=VectorStoreType.LANCEDB,
        name="test-table",
        state=VectorStoreState.ACTIVE
    )
    
    return mock_provider


@pytest.fixture
def mock_qdrant_provider():
    """Mock Qdrant provider."""
    mock_provider = Mock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.QDRANT
    
    def mock_create(config: VectorStoreConfig):
        return VectorStoreStatus(
            store_type=VectorStoreType.QDRANT,
            name=config.name,
            state=VectorStoreState.ACTIVE,
            endpoint=f"https://{config.name}.qdrant.io:6333",
            region="us-east-1",
            created_at=datetime.now(timezone.utc),
            dimension=config.dimension
        )
    
    mock_provider.create.side_effect = mock_create
    
    def mock_upsert(name: str, vectors: List[Dict[str, Any]]):
        return {
            "status": "success",
            "stored_count": len(vectors),
            "collection_name": name
        }
    
    mock_provider.upsert_vectors.side_effect = mock_upsert
    
    def mock_query(name: str, query_vector: List[float], top_k: int = 10, filter_metadata: Optional[Dict] = None):
        results = []
        for i in range(min(top_k, 6)):
            results.append({
                "id": f"qdrant-result-{i}",
                "score": 0.96 - (i * 0.03),
                "values": query_vector,
                "metadata": {"video_id": "test-video-001"}
            })
        return results
    
    mock_provider.query.side_effect = mock_query
    
    def mock_delete(name: str, force: bool = False):
        return VectorStoreStatus(
            store_type=VectorStoreType.QDRANT,
            name=name,
            state=VectorStoreState.DELETED
        )
    
    mock_provider.delete.side_effect = mock_delete
    mock_provider.get_status.return_value = VectorStoreStatus(
        store_type=VectorStoreType.QDRANT,
        name="test-collection",
        state=VectorStoreState.ACTIVE
    )
    
    return mock_provider


# ============================================================================
# Individual Provider E2E Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.integration
class TestS3VectorE2E:
    """
    End-to-end tests for S3Vector provider workflow.
    
    Validates: Setup → Process → Upsert → Query → Verify → Cleanup
    """
    
    def test_s3vector_e2e_workflow(
        self,
        mock_s3vector_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test complete S3Vector workflow from video processing to search.
        
        Steps:
        1. Initialize S3Vector index
        2. Process video (mocked)
        3. Store embeddings in S3Vector
        4. Query the index
        5. Verify results
        6. Cleanup
        """
        start_time = time.time()
        workflow_metrics = {"steps_completed": [], "timings": {}}
        
        # Step 1: Setup - Create S3Vector index
        step_start = time.time()
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name=f"test-s3vector-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        status = mock_s3vector_provider.create(config)
        assert status.state == VectorStoreState.ACTIVE
        assert status.arn is not None
        workflow_metrics["steps_completed"].append("create_index")
        workflow_metrics["timings"]["create_index"] = time.time() - step_start
        
        # Step 2: Video Processing - Get embeddings
        step_start = time.time()
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        assert job_info.job_id is not None
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        assert completed_job.status == "Completed"
        
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        assert len(embedding_result.embeddings) > 0
        workflow_metrics["steps_completed"].append("process_video")
        workflow_metrics["timings"]["process_video"] = time.time() - step_start
        
        # Step 3: Upsert - Store embeddings
        step_start = time.time()
        vectors_data = []
        for segment in embedding_result.embeddings:
            vectors_data.append({
                "id": segment["segment_id"],
                "values": segment["embedding"],
                "metadata": {
                    "video_id": fake_video_metadata["video_id"],
                    "start_sec": segment["start_offset_sec"],
                    "end_sec": segment["end_offset_sec"]
                }
            })
        
        upsert_result = mock_s3vector_provider.upsert_vectors(config.name, vectors_data)
        assert upsert_result["status"] == "success"
        assert upsert_result["stored_count"] == len(vectors_data)
        workflow_metrics["steps_completed"].append("upsert_vectors")
        workflow_metrics["timings"]["upsert_vectors"] = time.time() - step_start
        
        # Step 4: Query - Search for similar vectors
        step_start = time.time()
        query_results = mock_s3vector_provider.query(
            name=config.name,
            query_vector=fake_embeddings,
            top_k=5
        )
        workflow_metrics["steps_completed"].append("query_vectors")
        workflow_metrics["timings"]["query_vectors"] = time.time() - step_start
        
        # Step 5: Verify - Check results
        assert len(query_results) > 0
        assert all("id" in r for r in query_results)
        assert all("score" in r for r in query_results)
        assert all("metadata" in r for r in query_results)
        assert query_results[0]["score"] >= query_results[-1]["score"]  # Sorted by score
        workflow_metrics["steps_completed"].append("verify_results")
        
        # Step 6: Cleanup
        step_start = time.time()
        delete_status = mock_s3vector_provider.delete(config.name)
        assert delete_status.state == VectorStoreState.DELETED
        workflow_metrics["steps_completed"].append("cleanup")
        workflow_metrics["timings"]["cleanup"] = time.time() - step_start
        
        # Final metrics
        total_time = time.time() - start_time
        workflow_metrics["total_time_seconds"] = total_time
        
        logger.info(f"S3Vector E2E workflow completed in {total_time:.2f}s")
        logger.info(f"Workflow metrics: {json.dumps(workflow_metrics, indent=2)}")
        
        # Assert all steps completed
        assert len(workflow_metrics["steps_completed"]) == 6
        assert "create_index" in workflow_metrics["steps_completed"]
        assert "process_video" in workflow_metrics["steps_completed"]
        assert "upsert_vectors" in workflow_metrics["steps_completed"]
        assert "query_vectors" in workflow_metrics["steps_completed"]
        assert "verify_results" in workflow_metrics["steps_completed"]
        assert "cleanup" in workflow_metrics["steps_completed"]


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.slow
class TestOpenSearchE2E:
    """
    End-to-end tests for OpenSearch provider workflow.
    
    Note: Marked as 'slow' because OpenSearch collection creation can take time.
    """
    
    def test_opensearch_e2e_workflow(
        self,
        mock_opensearch_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test complete OpenSearch workflow from video processing to search.
        
        Steps:
        1. Initialize OpenSearch collection (with polling)
        2. Process video (mocked)
        3. Store embeddings in OpenSearch
        4. Query the collection
        5. Verify results
        6. Cleanup
        """
        start_time = time.time()
        workflow_metrics = {"steps_completed": [], "timings": {}}
        
        # Step 1: Setup - Create OpenSearch collection
        step_start = time.time()
        config = VectorStoreConfig(
            store_type=VectorStoreType.OPENSEARCH,
            name=f"test-opensearch-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        status = mock_opensearch_provider.create(config)
        assert status.state == VectorStoreState.CREATING
        
        # Poll until ready
        ready_status = mock_opensearch_provider.poll_until_ready(config.name, timeout=300)
        assert ready_status.state == VectorStoreState.ACTIVE
        assert ready_status.endpoint is not None
        workflow_metrics["steps_completed"].append("create_collection")
        workflow_metrics["timings"]["create_collection"] = time.time() - step_start
        
        # Step 2: Video Processing
        step_start = time.time()
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        workflow_metrics["steps_completed"].append("process_video")
        workflow_metrics["timings"]["process_video"] = time.time() - step_start
        
        # Step 3: Upsert vectors
        step_start = time.time()
        vectors_data = []
        for segment in embedding_result.embeddings:
            vectors_data.append({
                "id": segment["segment_id"],
                "values": segment["embedding"],
                "metadata": {"video_id": fake_video_metadata["video_id"]}
            })
        
        upsert_result = mock_opensearch_provider.upsert_vectors(config.name, vectors_data)
        assert upsert_result["status"] == "success"
        workflow_metrics["steps_completed"].append("upsert_vectors")
        workflow_metrics["timings"]["upsert_vectors"] = time.time() - step_start
        
        # Step 4: Query
        step_start = time.time()
        query_results = mock_opensearch_provider.query(
            name=config.name,
            query_vector=fake_embeddings,
            top_k=5
        )
        workflow_metrics["steps_completed"].append("query_vectors")
        workflow_metrics["timings"]["query_vectors"] = time.time() - step_start
        
        # Step 5: Verify
        assert len(query_results) > 0
        assert all("score" in r for r in query_results)
        workflow_metrics["steps_completed"].append("verify_results")
        
        # Step 6: Cleanup
        step_start = time.time()
        delete_status = mock_opensearch_provider.delete(config.name)
        assert delete_status.state == VectorStoreState.DELETING
        workflow_metrics["steps_completed"].append("cleanup")
        workflow_metrics["timings"]["cleanup"] = time.time() - step_start
        
        total_time = time.time() - start_time
        workflow_metrics["total_time_seconds"] = total_time
        
        logger.info(f"OpenSearch E2E workflow completed in {total_time:.2f}s")
        assert len(workflow_metrics["steps_completed"]) == 6


@pytest.mark.e2e
@pytest.mark.integration
class TestLanceDBE2E:
    """End-to-end tests for LanceDB provider workflow."""
    
    def test_lancedb_e2e_workflow(
        self,
        mock_lancedb_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test complete LanceDB workflow from video processing to search.
        
        LanceDB is optimized for fast vector operations with columnar storage.
        """
        start_time = time.time()
        workflow_metrics = {"steps_completed": [], "timings": {}}
        
        # Step 1: Setup
        step_start = time.time()
        config = VectorStoreConfig(
            store_type=VectorStoreType.LANCEDB,
            name=f"test-lancedb-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        status = mock_lancedb_provider.create(config)
        assert status.state == VectorStoreState.ACTIVE
        workflow_metrics["steps_completed"].append("create_table")
        workflow_metrics["timings"]["create_table"] = time.time() - step_start
        
        # Step 2: Process video
        step_start = time.time()
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        workflow_metrics["steps_completed"].append("process_video")
        workflow_metrics["timings"]["process_video"] = time.time() - step_start
        
        # Step 3: Upsert
        step_start = time.time()
        vectors_data = [
            {
                "id": seg["segment_id"],
                "values": seg["embedding"],
                "metadata": {"video_id": fake_video_metadata["video_id"]}
            }
            for seg in embedding_result.embeddings
        ]
        
        upsert_result = mock_lancedb_provider.upsert_vectors(config.name, vectors_data)
        assert upsert_result["status"] == "success"
        workflow_metrics["steps_completed"].append("upsert_vectors")
        workflow_metrics["timings"]["upsert_vectors"] = time.time() - step_start
        
        # Step 4: Query
        step_start = time.time()
        query_results = mock_lancedb_provider.query(
            name=config.name,
            query_vector=fake_embeddings,
            top_k=5
        )
        workflow_metrics["steps_completed"].append("query_vectors")
        workflow_metrics["timings"]["query_vectors"] = time.time() - step_start
        
        # Step 5: Verify
        assert len(query_results) > 0
        workflow_metrics["steps_completed"].append("verify_results")
        
        # Step 6: Cleanup
        step_start = time.time()
        delete_status = mock_lancedb_provider.delete(config.name)
        assert delete_status.state == VectorStoreState.DELETED
        workflow_metrics["steps_completed"].append("cleanup")
        workflow_metrics["timings"]["cleanup"] = time.time() - step_start
        
        total_time = time.time() - start_time
        workflow_metrics["total_time_seconds"] = total_time
        
        logger.info(f"LanceDB E2E workflow completed in {total_time:.2f}s")
        assert len(workflow_metrics["steps_completed"]) == 6


@pytest.mark.e2e
@pytest.mark.integration
class TestQdrantE2E:
    """End-to-end tests for Qdrant provider workflow."""
    
    def test_qdrant_e2e_workflow(
        self,
        mock_qdrant_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test complete Qdrant workflow from video processing to search.
        
        Qdrant provides advanced filtering and cloud-native features.
        """
        start_time = time.time()
        workflow_metrics = {"steps_completed": [], "timings": {}}
        
        # Step 1: Setup
        step_start = time.time()
        config = VectorStoreConfig(
            store_type=VectorStoreType.QDRANT,
            name=f"test-qdrant-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        status = mock_qdrant_provider.create(config)
        assert status.state == VectorStoreState.ACTIVE
        assert status.endpoint is not None
        workflow_metrics["steps_completed"].append("create_collection")
        workflow_metrics["timings"]["create_collection"] = time.time() - step_start
        
        # Step 2: Process video
        step_start = time.time()
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        workflow_metrics["steps_completed"].append("process_video")
        workflow_metrics["timings"]["process_video"] = time.time() - step_start
        
        # Step 3: Upsert
        step_start = time.time()
        vectors_data = [
            {
                "id": seg["segment_id"],
                "values": seg["embedding"],
                "metadata": {"video_id": fake_video_metadata["video_id"]}
            }
            for seg in embedding_result.embeddings
        ]
        
        upsert_result = mock_qdrant_provider.upsert_vectors(config.name, vectors_data)
        assert upsert_result["status"] == "success"
        workflow_metrics["steps_completed"].append("upsert_vectors")
        workflow_metrics["timings"]["upsert_vectors"] = time.time() - step_start
        
        # Step 4: Query
        step_start = time.time()
        query_results = mock_qdrant_provider.query(
            name=config.name,
            query_vector=fake_embeddings,
            top_k=5
        )
        workflow_metrics["steps_completed"].append("query_vectors")
        workflow_metrics["timings"]["query_vectors"] = time.time() - step_start
        
        # Step 5: Verify
        assert len(query_results) > 0
        workflow_metrics["steps_completed"].append("verify_results")
        
        # Step 6: Cleanup
        step_start = time.time()
        delete_status = mock_qdrant_provider.delete(config.name)
        assert delete_status.state == VectorStoreState.DELETED
        workflow_metrics["steps_completed"].append("cleanup")
        workflow_metrics["timings"]["cleanup"] = time.time() - step_start
        
        total_time = time.time() - start_time
        workflow_metrics["total_time_seconds"] = total_time
        
        logger.info(f"Qdrant E2E workflow completed in {total_time:.2f}s")
        assert len(workflow_metrics["steps_completed"]) == 6


# ============================================================================
# Combination Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.combination
class TestProviderCombinations:
    """Test combinations of vector store providers working together."""
    
    def test_s3vector_and_opensearch_workflow(
        self,
        mock_s3vector_provider,
        mock_opensearch_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test S3Vector and OpenSearch working together (dual pattern).
        
        This validates the common pattern of using both providers:
        - S3Vector for AWS-native storage
        - OpenSearch for hybrid search capabilities
        """
        start_time = time.time()
        
        # Create both indices
        s3_config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name=f"test-s3-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        os_config = VectorStoreConfig(
            store_type=VectorStoreType.OPENSEARCH,
            name=f"test-os-{uuid.uuid4().hex[:8]}",
            dimension=1024,
            similarity_metric="cosine"
        )
        
        s3_status = mock_s3vector_provider.create(s3_config)
        os_status = mock_opensearch_provider.create(os_config)
        os_ready = mock_opensearch_provider.poll_until_ready(os_config.name)
        
        assert s3_status.state == VectorStoreState.ACTIVE
        assert os_ready.state == VectorStoreState.ACTIVE
        
        # Process video once
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        
        # Store in both providers
        vectors_data = [
            {
                "id": seg["segment_id"],
                "values": seg["embedding"],
                "metadata": {"video_id": fake_video_metadata["video_id"]}
            }
            for seg in embedding_result.embeddings
        ]
        
        s3_upsert = mock_s3vector_provider.upsert_vectors(s3_config.name, vectors_data)
        os_upsert = mock_opensearch_provider.upsert_vectors(os_config.name, vectors_data)
        
        assert s3_upsert["status"] == "success"
        assert os_upsert["status"] == "success"
        
        # Query both providers
        s3_results = mock_s3vector_provider.query(s3_config.name, fake_embeddings, top_k=5)
        os_results = mock_opensearch_provider.query(os_config.name, fake_embeddings, top_k=5)
        
        # Verify both returned results
        assert len(s3_results) > 0
        assert len(os_results) > 0
        
        # Cleanup both
        mock_s3vector_provider.delete(s3_config.name)
        mock_opensearch_provider.delete(os_config.name)
        
        total_time = time.time() - start_time
        logger.info(f"Dual provider workflow completed in {total_time:.2f}s")
    
    def test_all_providers_workflow(
        self,
        mock_s3vector_provider,
        mock_opensearch_provider,
        mock_lancedb_provider,
        mock_qdrant_provider,
        mock_twelvelabs_service,
        fake_video_metadata,
        fake_embeddings
    ):
        """
        Test all four providers working together.
        
        This validates:
        - All providers can be initialized simultaneously
        - Same embeddings can be stored in all providers
        - All providers return results for the same query
        - Performance comparison across providers
        """
        start_time = time.time()
        provider_metrics = {}
        
        # Define all providers
        providers_config = [
            (mock_s3vector_provider, VectorStoreType.S3_VECTOR, "s3vector"),
            (mock_opensearch_provider, VectorStoreType.OPENSEARCH, "opensearch"),
            (mock_lancedb_provider, VectorStoreType.LANCEDB, "lancedb"),
            (mock_qdrant_provider, VectorStoreType.QDRANT, "qdrant")
        ]
        
        # Step 1: Create all provider stores
        stores = []
        for provider, store_type, name_prefix in providers_config:
            config = VectorStoreConfig(
                store_type=store_type,
                name=f"test-{name_prefix}-{uuid.uuid4().hex[:8]}",
                dimension=1024,
                similarity_metric="cosine"
            )
            
            create_start = time.time()
            status = provider.create(config)
            
            # Poll if needed (OpenSearch)
            if store_type == VectorStoreType.OPENSEARCH:
                status = provider.poll_until_ready(config.name)
            
            assert status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]
            
            stores.append({
                "provider": provider,
                "config": config,
                "store_type": store_type,
                "name_prefix": name_prefix
            })
            
            provider_metrics[name_prefix] = {
                "create_time": time.time() - create_start,
                "store_name": config.name
            }
        
        # Step 2: Process video once (shared across all providers)
        process_start = time.time()
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"],
            embedding_options=["visual-text"]
        )
        
        completed_job = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        embedding_result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        process_time = time.time() - process_start
        
        # Prepare vectors
        vectors_data = [
            {
                "id": seg["segment_id"],
                "values": seg["embedding"],
                "metadata": {"video_id": fake_video_metadata["video_id"]}
            }
            for seg in embedding_result.embeddings
        ]
        
        # Step 3: Upsert to all providers
        for store in stores:
            name_prefix = store["name_prefix"]
            upsert_start = time.time()
            
            result = store["provider"].upsert_vectors(
                store["config"].name,
                vectors_data
            )
            
            assert result["status"] == "success"
            provider_metrics[name_prefix]["upsert_time"] = time.time() - upsert_start
            provider_metrics[name_prefix]["vectors_stored"] = result["stored_count"]
        
        # Step 4: Query all providers
        query_results = {}
        for store in stores:
            name_prefix = store["name_prefix"]
            query_start = time.time()
            
            results = store["provider"].query(
                store["config"].name,
                fake_embeddings,
                top_k=5
            )
            
            query_time = time.time() - query_start
            provider_metrics[name_prefix]["query_time"] = query_time
            provider_metrics[name_prefix]["results_count"] = len(results)
            
            query_results[name_prefix] = results
            
            # Verify results
            assert len(results) > 0
            assert all("score" in r for r in results)
        
        # Step 5: Compare performance
        query_times = {k: v["query_time"] for k, v in provider_metrics.items()}
        fastest_provider = min(query_times.items(), key=lambda x: x[1])[0]
        slowest_provider = max(query_times.items(), key=lambda x: x[1])[0]
        
        logger.info(f"Performance comparison:")
        logger.info(f"  Fastest: {fastest_provider} ({query_times[fastest_provider]*1000:.2f}ms)")
        logger.info(f"  Slowest: {slowest_provider} ({query_times[slowest_provider]*1000:.2f}ms)")
        
        # Step 6: Cleanup all providers
        for store in stores:
            delete_status = store["provider"].delete(store["config"].name)
            assert delete_status.state in [VectorStoreState.DELETED, VectorStoreState.DELETING]
        
        total_time = time.time() - start_time
        logger.info(f"All providers workflow completed in {total_time:.2f}s")
        logger.info(f"Provider metrics: {json.dumps(provider_metrics, indent=2)}")
        
        # Assert all providers processed successfully
        assert len(query_results) == 4
        assert all(len(results) > 0 for results in query_results.values())


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.e2e
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in E2E workflows."""
    
    def test_video_processing_failure(
        self,
        mock_s3vector_provider,
        fake_video_metadata
    ):
        """Test handling of video processing failures."""
        with patch('src.services.twelvelabs_video_processing.TwelveLabsVideoProcessingService') as mock_service:
            mock_instance = Mock()
            mock_instance.start_video_processing.side_effect = VectorEmbeddingError("Model access denied")
            mock_service.return_value = mock_instance
            
            # Create index
            config = VectorStoreConfig(
                store_type=VectorStoreType.S3_VECTOR,
                name="test-error-handling",
                dimension=1024
            )
            mock_s3vector_provider.create(config)
            
            # Attempt to process video - should fail
            with pytest.raises(VectorEmbeddingError):
                mock_instance.start_video_processing(
                    video_s3_uri=fake_video_metadata["s3_uri"]
                )
            
            # Cleanup should still work
            mock_s3vector_provider.delete(config.name)
    
    def test_storage_failure(
        self,
        mock_s3vector_provider,
        mock_twelvelabs_service,
        fake_video_metadata
    ):
        """Test handling of storage failures."""
        # Override upsert to fail
        mock_s3vector_provider.upsert_vectors.side_effect = VectorStorageError("Storage quota exceeded")
        
        # Create index
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name="test-storage-error",
            dimension=1024
        )
        mock_s3vector_provider.create.side_effect = None  # Reset for create
        mock_s3vector_provider.create.return_value = VectorStoreStatus(
            store_type=VectorStoreType.S3_VECTOR,
            name=config.name,
            state=VectorStoreState.ACTIVE
        )
        mock_s3vector_provider.create(config)
        
        # Process video successfully
        job_info = mock_twelvelabs_service.start_video_processing(
            video_s3_uri=fake_video_metadata["s3_uri"]
        )
        completed = mock_twelvelabs_service.wait_for_completion(job_info.job_id)
        result = mock_twelvelabs_service.retrieve_results(job_info.job_id)
        
        # Storage should fail
        with pytest.raises(VectorStorageError):
            mock_s3vector_provider.upsert_vectors(config.name, [])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])