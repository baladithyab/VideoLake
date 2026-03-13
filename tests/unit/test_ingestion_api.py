"""
Unit Tests for Ingestion API Routes.

Tests for both VideoIngestionPipeline and BatchIngestionPipeline endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from src.api.routers.ingestion import (
    BatchIngestionRequest,
    BatchIngestionResponse,
    DatasetIngestionRequest,
    IngestionRequest,
)


class TestVideoIngestionEndpoints:
    """Tests for existing video ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_list_datasets_success(self):
        """Test listing available video datasets."""
        from src.api.routers.ingestion import list_datasets

        with patch('src.services.video_dataset_manager.VideoDatasetManager.list_available_datasets') as mock_list:
            mock_list.return_value = [
                {
                    "name": "Test Dataset",
                    "size_gb": 1.5,
                    "num_videos": 100
                }
            ]

            result = await list_datasets()

            assert len(result) == 1
            assert result[0]["name"] == "Test Dataset"
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_ingestion_invalid_path(self):
        """Test starting ingestion with invalid S3 path."""
        from src.api.routers.ingestion import start_ingestion

        request = IngestionRequest(
            video_path="invalid://path",
            model_type="marengo"
        )

        with pytest.raises(HTTPException) as exc_info:
            await start_ingestion(request)

        assert exc_info.value.status_code == 400
        assert "S3 URI" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_start_ingestion_success(self):
        """Test successful ingestion start."""
        from src.api.routers.ingestion import start_ingestion

        request = IngestionRequest(
            video_path="s3://bucket/video.mp4",
            model_type="marengo"
        )

        with patch('src.ingestion.pipeline.VideoIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.process_video.return_value = Mock(
                job_id="exec-123",
                status="RUNNING",
                message="Started"
            )
            mock_pipeline_class.return_value = mock_pipeline

            result = await start_ingestion(request)

            assert result.job_id == "exec-123"
            assert result.status == "RUNNING"
            mock_pipeline.process_video.assert_called_once()


class TestBatchIngestionEndpoints:
    """Tests for new batch ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_start_batch_ingestion_invalid_modality(self):
        """Test batch ingestion with invalid modality."""
        from src.api.routers.ingestion import start_batch_ingestion

        request = BatchIngestionRequest(
            items=["item1", "item2"] * 10,  # 20 items
            modality="invalid_modality",
            provider_name="bedrock"
        )

        with pytest.raises(HTTPException) as exc_info:
            await start_batch_ingestion(request)

        assert exc_info.value.status_code == 400
        assert "Invalid modality" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_start_batch_ingestion_too_few_items(self):
        """Test batch ingestion with too few items."""
        from src.api.routers.ingestion import start_batch_ingestion

        request = BatchIngestionRequest(
            items=["item1", "item2"],  # Only 2 items
            modality="text",
            provider_name="bedrock"
        )

        with pytest.raises(HTTPException) as exc_info:
            await start_batch_ingestion(request)

        assert exc_info.value.status_code == 400
        assert "at least 10 items" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_start_batch_ingestion_success(self):
        """Test successful batch ingestion start."""
        from src.api.routers.ingestion import start_batch_ingestion
        from src.ingestion.pipeline import BatchIngestionResult

        items = [f"s3://bucket/item{i}.txt" for i in range(100)]

        request = BatchIngestionRequest(
            items=items,
            modality="text",
            provider_name="bedrock",
            batch_size=10,
            max_concurrent_batches=5
        )

        mock_result = BatchIngestionResult(
            job_id="batch_text_abc123",
            status="completed",
            total_items=100,
            processed_items=100,
            failed_items=0,
            total_batches=10,
            completed_batches=10,
            processing_time_seconds=45.5,
            cost_estimate=0.125,
            message="Successfully processed 100/100 items",
            embeddings_generated=100
        )

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.ingest_items = AsyncMock(return_value=mock_result)
            mock_pipeline_class.return_value = mock_pipeline

            result = await start_batch_ingestion(request)

            assert result.job_id == "batch_text_abc123"
            assert result.status == "completed"
            assert result.total_items == 100
            assert result.processed_items == 100
            assert result.embeddings_generated == 100
            mock_pipeline.ingest_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_dataset_invalid_type(self):
        """Test dataset ingestion with invalid dataset type."""
        from src.api.routers.ingestion import ingest_dataset

        request = DatasetIngestionRequest(
            dataset_type="invalid_dataset",
            provider_name="bedrock"
        )

        with pytest.raises(HTTPException) as exc_info:
            await ingest_dataset(request)

        assert exc_info.value.status_code == 400
        assert "Invalid dataset type" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_ingest_dataset_success(self):
        """Test successful dataset ingestion."""
        from src.api.routers.ingestion import ingest_dataset
        from src.ingestion.pipeline import BatchIngestionResult

        request = DatasetIngestionRequest(
            dataset_type="ms_marco",
            provider_name="bedrock",
            download_if_missing=True,
            stage_to_s3=False
        )

        mock_result = BatchIngestionResult(
            job_id="dataset_ms_marco_xyz789",
            status="completed",
            total_items=1000,
            processed_items=1000,
            failed_items=0,
            total_batches=10,
            completed_batches=10,
            processing_time_seconds=120.0,
            cost_estimate=2.5,
            message="Successfully processed 1000/1000 items",
            embeddings_generated=1000
        )

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.ingest_dataset = AsyncMock(return_value=mock_result)
            mock_pipeline_class.return_value = mock_pipeline

            result = await ingest_dataset(request)

            assert result.job_id == "dataset_ms_marco_xyz789"
            assert result.status == "completed"
            assert result.total_items == 1000
            mock_pipeline.ingest_dataset.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_available_datasets_success(self):
        """Test listing available datasets."""
        from src.api.routers.ingestion import list_available_datasets

        with patch('src.api.routers.ingestion.BatchIngestionPipeline.list_available_datasets') as mock_list:
            mock_list.return_value = [
                {
                    "name": "MS MARCO Passages",
                    "type": "ms_marco",
                    "modality": "text",
                    "size_gb": 3.5,
                    "num_items": 8841823
                },
                {
                    "name": "COCO 2017 Train",
                    "type": "coco",
                    "modality": "image",
                    "size_gb": 18.0,
                    "num_items": 118287
                }
            ]

            result = await list_available_datasets()

            assert len(result) == 2
            assert result[0]["name"] == "MS MARCO Passages"
            assert result[1]["modality"] == "image"
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_checkpoint_status_not_found(self):
        """Test getting checkpoint status for non-existent job."""
        from src.api.routers.ingestion import get_checkpoint_status

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.get_checkpoint_status.return_value = None
            mock_pipeline_class.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await get_checkpoint_status("nonexistent_job")

            assert exc_info.value.status_code == 404
            assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_checkpoint_status_success(self):
        """Test successful checkpoint status retrieval."""
        from src.api.routers.ingestion import get_checkpoint_status

        mock_stats = {
            "job_id": "batch_text_abc123",
            "job_name": "Test Job",
            "status": "in_progress",
            "progress_percentage": 65.5,
            "processed_items": 655,
            "failed_items": 5,
            "total_items": 1000,
            "current_batch": 7,
            "total_batches": 10,
            "elapsed_seconds": 120.5,
            "items_per_second": 5.4,
            "eta_seconds": 64.0,
            "cost_estimate": 1.25,
            "error_message": None
        }

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.get_checkpoint_status.return_value = mock_stats
            mock_pipeline_class.return_value = mock_pipeline

            result = await get_checkpoint_status("batch_text_abc123")

            assert result.job_id == "batch_text_abc123"
            assert result.progress_percentage == 65.5
            assert result.status == "in_progress"
            assert result.processed_items == 655
            assert result.items_per_second == 5.4

    @pytest.mark.asyncio
    async def test_list_checkpoints_success(self):
        """Test listing all checkpoints."""
        from src.api.routers.ingestion import list_checkpoints

        mock_checkpoints = [
            {
                "job_id": "job1",
                "status": "completed",
                "progress_percentage": 100.0
            },
            {
                "job_id": "job2",
                "status": "in_progress",
                "progress_percentage": 45.0
            }
        ]

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.list_checkpoints.return_value = mock_checkpoints
            mock_pipeline_class.return_value = mock_pipeline

            result = await list_checkpoints()

            assert len(result) == 2
            assert result[0]["job_id"] == "job1"
            assert result[1]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_resume_batch_job_not_resumable(self):
        """Test resuming a job that cannot be resumed."""
        from src.api.routers.ingestion import resume_batch_job

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.resume_job.return_value = False
            mock_pipeline_class.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await resume_batch_job("completed_job")

            assert exc_info.value.status_code == 400
            assert "cannot be resumed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_resume_batch_job_success(self):
        """Test successful job resume check."""
        from src.api.routers.ingestion import resume_batch_job

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.resume_job.return_value = True
            mock_pipeline_class.return_value = mock_pipeline

            result = await resume_batch_job("failed_job")

            assert result["job_id"] == "failed_job"
            assert result["status"] == "resumable"
            assert "can be resumed" in result["message"]


class TestEndpointIntegration:
    """Integration tests for ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_batch_ingestion_end_to_end(self):
        """Test batch ingestion flow from request to response."""
        from src.api.routers.ingestion import start_batch_ingestion
        from src.ingestion.pipeline import BatchIngestionResult

        # Create a realistic request
        items = [f"Text content {i}" for i in range(50)]
        request = BatchIngestionRequest(
            items=items,
            modality="text",
            provider_name="bedrock",
            batch_size=10,
            max_concurrent_batches=3,
            enable_checkpointing=True,
            job_name="Test E2E Batch"
        )

        # Mock the pipeline
        mock_result = BatchIngestionResult(
            job_id="test_e2e_123",
            status="completed",
            total_items=50,
            processed_items=48,
            failed_items=2,
            total_batches=5,
            completed_batches=5,
            processing_time_seconds=15.3,
            cost_estimate=0.05,
            message="Successfully processed 48/50 items",
            embeddings_generated=48
        )

        with patch('src.api.routers.ingestion.BatchIngestionPipeline') as mock_pipeline_class:
            mock_pipeline = Mock()
            mock_pipeline.ingest_items = AsyncMock(return_value=mock_result)
            mock_pipeline_class.return_value = mock_pipeline

            result = await start_batch_ingestion(request)

            # Verify response structure
            assert isinstance(result, BatchIngestionResponse)
            assert result.job_id == "test_e2e_123"
            assert result.status == "completed"
            assert result.total_items == 50
            assert result.processed_items == 48
            assert result.failed_items == 2
            assert result.cost_estimate == 0.05

            # Verify pipeline was called with correct arguments
            call_args = mock_pipeline.ingest_items.call_args
            assert call_args.kwargs['items'] == items
            assert call_args.kwargs['provider_name'] == "bedrock"
            assert call_args.kwargs['job_name'] == "Test E2E Batch"
