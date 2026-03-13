"""
Ingestion Pipelines for S3Vector.

This module provides two ingestion pipelines:
1. VideoIngestionPipeline: Triggers AWS Step Functions for video processing
2. BatchIngestionPipeline: Large-scale batch processing for 10K-100K items across all modalities
"""

import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import boto3

from src.config.unified_config_manager import get_config
from src.ingestion.batch_processor import BatchConfig, BatchProcessor
from src.ingestion.checkpoint_manager import CheckpointManager
from src.ingestion.dataset_downloader import DatasetDownloader, DatasetType
from src.ingestion.rate_limiter import RateLimitedExecutor, RateLimiterConfig
from src.services.embedding_provider import EmbeddingProviderFactory, ModalityType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class IngestionResult:
    """Result of the ingestion process trigger."""
    job_id: str
    status: str
    message: str

class VideoIngestionPipeline:
    """Pipeline for ingesting videos via AWS Step Functions."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.sfn_client = boto3.client('stepfunctions')
        self.config = get_config()
        # In a real deployment, this ARN would come from config or environment variables
        # populated by Terraform outputs.
        self.state_machine_arn = os.getenv("INGESTION_STATE_MACHINE_ARN")
        logger.info("Initialized VideoIngestionPipeline")

    def process_video(self,
                     video_path: str,
                     model_type: str = "marengo",
                     backend_types: list[str] | None = None) -> IngestionResult:
        """
        Trigger the Step Function to process a video.

        Args:
            video_path: S3 URI or path to the video.
            model_type: Type of model to use ("marengo" or "bedrock").
            backend_types: List of backends to update (e.g., ["s3vector", "lancedb"]).
                           If None, updates all configured backends.

        Returns:
            IngestionResult containing the execution ARN.
        """
        if not self.state_machine_arn:
            error_msg = "INGESTION_STATE_MACHINE_ARN environment variable is not set. Cannot process video ingestion without Step Functions infrastructure."
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not backend_types:
            backend_types = ["s3vector"]

        input_payload = {
            "video_path": video_path,
            "model_type": model_type,
            "backend_types_str": ",".join(backend_types) # Pass as string for easier env var handling
        }

        try:
            response = self.sfn_client.start_execution(
                stateMachineArn=self.state_machine_arn,
                name=f"ingest-{uuid.uuid4().hex[:8]}",
                input=json.dumps(input_payload)
            )

            execution_arn = response['executionArn']
            logger.info(f"Started Step Function execution: {execution_arn}")

            return IngestionResult(
                job_id=execution_arn,
                status="RUNNING",
                message="Ingestion workflow started successfully."
            )

        except Exception as e:
            logger.error(f"Failed to start Step Function execution: {e}", exc_info=True)
            raise

    def get_status(self, execution_arn: str) -> dict[str, Any]:
        """
        Get the status of a Step Function execution.
        """
        try:
            response = self.sfn_client.describe_execution(
                executionArn=execution_arn
            )
            return {
                "status": response['status'],
                "startDate": response['startDate'].isoformat(),
                "stopDate": response.get('stopDate').isoformat() if response.get('stopDate') else None,
                "input": json.loads(response.get('input', '{}')),
                "output": json.loads(response.get('output', '{}')) if response.get('output') else None
            }
        except Exception as e:
            logger.error(f"Failed to get execution status: {e}")
            raise


@dataclass
class BatchIngestionConfig:
    """Configuration for batch ingestion pipeline."""
    batch_size: int = 100
    max_concurrent_batches: int = 5
    rate_limit_rps: float = 10.0
    max_retries: int = 3
    enable_checkpointing: bool = True
    checkpoint_storage_type: str = "local"  # 'local' or 's3'
    s3_staging_bucket: str | None = None


@dataclass
class BatchIngestionResult:
    """Result of batch ingestion pipeline."""
    job_id: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    total_batches: int
    completed_batches: int
    processing_time_seconds: float
    cost_estimate: float
    message: str
    embeddings_generated: int


class BatchIngestionPipeline:
    """
    Large-scale batch ingestion pipeline for 10K-100K items.

    Supports all modalities (text, image, audio, video) with:
    - Configurable batch processing and chunking
    - Rate limiting and retry logic for AWS services
    - Checkpoint/resume for long-running jobs
    - S3 staging for large datasets
    - Progress tracking and cost estimation
    - Dataset downloaders for recommended datasets
    """

    def __init__(self, config: BatchIngestionConfig | None = None):
        """
        Initialize the batch ingestion pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config or BatchIngestionConfig()

        # Initialize components
        self._initialize_components()

        logger.info(
            f"Initialized BatchIngestionPipeline: "
            f"batch_size={self.config.batch_size}, "
            f"concurrent={self.config.max_concurrent_batches}"
        )

    def _initialize_components(self) -> None:
        """Initialize pipeline components."""
        # Rate limiter
        rate_config = RateLimiterConfig(
            requests_per_second=self.config.rate_limit_rps,
            max_retries=self.config.max_retries
        )
        self.rate_limiter = RateLimitedExecutor(rate_config)

        # Checkpoint manager
        if self.config.enable_checkpointing:
            from src.ingestion.checkpoint_manager import CheckpointStorage

            storage = CheckpointStorage(
                storage_type=self.config.checkpoint_storage_type,
                s3_bucket=self.config.s3_staging_bucket
            )
            self.checkpoint_manager = CheckpointManager(storage=storage)
        else:
            self.checkpoint_manager = None

        # Dataset downloader
        self.dataset_downloader = DatasetDownloader(
            s3_bucket=self.config.s3_staging_bucket
        )

    async def ingest_items(
        self,
        items: list[Any],
        modality: ModalityType,
        provider_name: str = "bedrock",
        model_id: str | None = None,
        backend_types: list[str] | None = None,
        job_name: str | None = None,
        transform_fn: Callable[[Any], str] | None = None,
        progress_callback: Callable[[int, int, float], None] | None = None
    ) -> BatchIngestionResult:
        """
        Ingest a list of items with batch processing.

        Args:
            items: List of items to ingest (texts, file paths, S3 URIs, etc.)
            modality: Content modality
            provider_name: Embedding provider name
            model_id: Optional embedding model ID
            backend_types: Vector store backends to update
            job_name: Optional job name for tracking
            transform_fn: Optional function to transform items to content strings
            progress_callback: Optional progress callback(processed, total, percent)

        Returns:
            BatchIngestionResult with job statistics
        """
        import time
        start_time = time.time()

        # Generate job ID
        job_id = f"batch_{modality.value}_{uuid.uuid4().hex[:8]}"
        job_name = job_name or f"Batch ingestion: {modality.value}"

        logger.info(
            f"Starting batch ingestion job {job_id}: "
            f"{len(items)} items, modality={modality.value}"
        )

        try:
            # Get embedding provider
            provider = EmbeddingProviderFactory.create_provider(provider_name)

            # Create batch processor
            batch_config = BatchConfig(
                batch_size=self.config.batch_size,
                max_concurrent_batches=self.config.max_concurrent_batches,
                rate_limit_rps=self.config.rate_limit_rps,
                max_retries=self.config.max_retries,
                enable_checkpointing=self.config.enable_checkpointing
            )

            batch_processor = BatchProcessor(
                embedding_provider=provider,
                config=batch_config,
                rate_limiter=self.rate_limiter,
                checkpoint_manager=self.checkpoint_manager
            )

            # Process items
            results = await batch_processor.process_items(
                items=items,
                modality=modality,
                model_id=model_id,
                job_id=job_id,
                job_name=job_name,
                transform_fn=transform_fn,
                progress_callback=progress_callback
            )

            # Aggregate results
            total_success = sum(r.success_count for r in results)
            total_failed = sum(r.failure_count for r in results)
            total_cost = sum(r.cost_estimate for r in results)
            embeddings_generated = sum(len(r.embeddings) for r in results)

            processing_time = time.time() - start_time

            # TODO: Upsert embeddings to vector stores (backend_types)
            # This would integrate with vector_store_manager to update
            # the specified backends (s3vector, lancedb, opensearch)

            logger.info(
                f"Batch ingestion complete: {total_success} success, "
                f"{total_failed} failed, {processing_time:.2f}s, ${total_cost:.4f}"
            )

            return BatchIngestionResult(
                job_id=job_id,
                status="completed" if total_failed == 0 else "partial_failure",
                total_items=len(items),
                processed_items=total_success,
                failed_items=total_failed,
                total_batches=len(results),
                completed_batches=len(results),
                processing_time_seconds=processing_time,
                cost_estimate=total_cost,
                message=f"Successfully processed {total_success}/{len(items)} items",
                embeddings_generated=embeddings_generated
            )

        except Exception as e:
            logger.error(f"Batch ingestion failed: {e}", exc_info=True)

            return BatchIngestionResult(
                job_id=job_id,
                status="failed",
                total_items=len(items),
                processed_items=0,
                failed_items=len(items),
                total_batches=0,
                completed_batches=0,
                processing_time_seconds=time.time() - start_time,
                cost_estimate=0.0,
                message=f"Ingestion failed: {str(e)}",
                embeddings_generated=0
            )

    async def ingest_dataset(
        self,
        dataset_type: DatasetType,
        provider_name: str = "bedrock",
        model_id: str | None = None,
        backend_types: list[str] | None = None,
        download_if_missing: bool = True,
        stage_to_s3: bool = False,
        progress_callback: Callable[[int, int, float], None] | None = None
    ) -> BatchIngestionResult:
        """
        Ingest a recommended dataset.

        Args:
            dataset_type: Dataset type to ingest
            provider_name: Embedding provider name
            model_id: Optional embedding model ID
            backend_types: Vector store backends to update
            download_if_missing: Download dataset if not cached
            stage_to_s3: Stage dataset to S3 for cloud processing
            progress_callback: Optional progress callback

        Returns:
            BatchIngestionResult with job statistics
        """
        from src.ingestion.dataset_downloader import DatasetRegistry

        # Get dataset info
        dataset_info = DatasetRegistry.get_dataset_info(dataset_type)

        logger.info(f"Ingesting dataset: {dataset_info.name}")

        try:
            # Download dataset if needed
            if download_if_missing:
                dataset_dir = await self.dataset_downloader.download_dataset(
                    dataset_type=dataset_type
                )
            else:
                dataset_dir = self.dataset_downloader.local_cache_dir / dataset_type.value
                if not dataset_dir.exists():
                    raise FileNotFoundError(f"Dataset not found: {dataset_dir}")

            # Stage to S3 if requested
            if stage_to_s3:
                s3_uri = await self.dataset_downloader.stage_to_s3(
                    dataset_dir=dataset_dir,
                    dataset_type=dataset_type
                )
                logger.info(f"Dataset staged to {s3_uri}")

            # Get dataset manifest
            manifest = self.dataset_downloader.get_dataset_manifest(dataset_dir)

            # Extract items based on modality
            items = self._extract_items_from_manifest(manifest, dataset_info.modality)

            # Ingest items
            return await self.ingest_items(
                items=items,
                modality=dataset_info.modality,
                provider_name=provider_name,
                model_id=model_id,
                backend_types=backend_types,
                job_name=f"Dataset ingestion: {dataset_info.name}",
                progress_callback=progress_callback
            )

        except Exception as e:
            logger.error(f"Dataset ingestion failed: {e}", exc_info=True)
            raise

    def _extract_items_from_manifest(
        self,
        manifest: dict[str, Any],
        modality: ModalityType
    ) -> list[str]:
        """
        Extract items from dataset manifest based on modality.

        Args:
            manifest: Dataset manifest
            modality: Content modality

        Returns:
            List of file paths or content items
        """
        from pathlib import Path

        items = []
        dataset_dir = Path(manifest['dataset_dir'])

        # Filter files by modality
        extensions = {
            ModalityType.TEXT: ['.txt', '.json', '.csv', '.tsv'],
            ModalityType.IMAGE: ['.jpg', '.jpeg', '.png', '.bmp', '.gif'],
            ModalityType.AUDIO: ['.wav', '.mp3', '.flac', '.ogg'],
            ModalityType.VIDEO: ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        }

        valid_extensions = extensions.get(modality, [])

        for file_info in manifest['files']:
            file_path = dataset_dir / file_info['path']

            # Check extension
            if any(str(file_path).lower().endswith(ext) for ext in valid_extensions):
                items.append(str(file_path))

        logger.info(
            f"Extracted {len(items)} {modality.value} items from manifest"
        )

        return items

    def get_checkpoint_status(self, job_id: str) -> dict[str, Any] | None:
        """
        Get checkpoint status for a job.

        Args:
            job_id: Job identifier

        Returns:
            Checkpoint statistics or None if not found
        """
        if not self.checkpoint_manager:
            return None

        return self.checkpoint_manager.get_statistics(job_id)

    def resume_job(self, job_id: str) -> bool:
        """
        Check if a job can be resumed.

        Args:
            job_id: Job identifier

        Returns:
            True if job can be resumed
        """
        if not self.checkpoint_manager:
            return False

        return self.checkpoint_manager.can_resume(job_id)

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """
        List all checkpointed jobs.

        Returns:
            List of job metadata
        """
        if not self.checkpoint_manager:
            return []

        return self.checkpoint_manager.list_jobs()

    @staticmethod
    def list_available_datasets() -> list[dict[str, Any]]:
        """
        List available datasets for ingestion.

        Returns:
            List of dataset information
        """
        return DatasetDownloader.list_available_datasets()
