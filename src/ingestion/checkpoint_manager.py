"""
Checkpoint Manager for Long-Running Ingestion Jobs.

Provides checkpoint and resume functionality for large-scale dataset ingestion,
enabling recovery from failures and supporting incremental progress tracking.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import boto3

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CheckpointStatus(str, Enum):
    """Status of a checkpoint."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class CheckpointMetadata:
    """Metadata for an ingestion checkpoint."""
    job_id: str
    job_name: str
    created_at: datetime
    updated_at: datetime
    status: CheckpointStatus
    total_items: int
    processed_items: int
    failed_items: int
    current_batch: int
    total_batches: int
    progress_percentage: float
    modality: str
    dataset_name: str | None = None
    model_id: str | None = None
    backend_types: list[str] = None
    error_message: str | None = None
    cost_estimate: float | None = None
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CheckpointMetadata':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['status'] = CheckpointStatus(data['status'])
        return cls(**data)


@dataclass
class BatchCheckpoint:
    """Checkpoint for a single batch."""
    batch_index: int
    item_indices: list[int]
    status: CheckpointStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'batch_index': self.batch_index,
            'item_indices': self.item_indices,
            'status': self.status.value,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BatchCheckpoint':
        """Create from dictionary."""
        return cls(
            batch_index=data['batch_index'],
            item_indices=data['item_indices'],
            status=CheckpointStatus(data['status']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            error_message=data.get('error_message'),
            retry_count=data.get('retry_count', 0),
        )


class CheckpointStorage:
    """
    Storage backend for checkpoints.

    Supports both local filesystem and S3 storage for checkpoint persistence.
    """

    def __init__(
        self,
        storage_type: str = "local",
        local_dir: Path | None = None,
        s3_bucket: str | None = None,
        s3_prefix: str = "checkpoints/"
    ):
        """
        Initialize checkpoint storage.

        Args:
            storage_type: Storage type ('local' or 's3')
            local_dir: Local directory for checkpoints
            s3_bucket: S3 bucket name for checkpoints
            s3_prefix: S3 key prefix for checkpoints
        """
        self.storage_type = storage_type

        if storage_type == "local":
            self.local_dir = local_dir or Path.home() / ".s3vector" / "checkpoints"
            self.local_dir.mkdir(parents=True, exist_ok=True)
        elif storage_type == "s3":
            if not s3_bucket:
                raise ValueError("s3_bucket required for S3 storage")
            self.s3_client = boto3.client('s3')
            self.s3_bucket = s3_bucket
            self.s3_prefix = s3_prefix
        else:
            raise ValueError(f"Invalid storage type: {storage_type}")

        logger.info(f"Initialized checkpoint storage: {storage_type}")

    def save(self, job_id: str, data: dict[str, Any]) -> None:
        """
        Save checkpoint data.

        Args:
            job_id: Job identifier
            data: Checkpoint data to save
        """
        if self.storage_type == "local":
            file_path = self.local_dir / f"{job_id}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved checkpoint to {file_path}")

        elif self.storage_type == "s3":
            key = f"{self.s3_prefix}{job_id}.json"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json'
            )
            logger.debug(f"Saved checkpoint to s3://{self.s3_bucket}/{key}")

    def load(self, job_id: str) -> dict[str, Any] | None:
        """
        Load checkpoint data.

        Args:
            job_id: Job identifier

        Returns:
            Checkpoint data or None if not found
        """
        try:
            if self.storage_type == "local":
                file_path = self.local_dir / f"{job_id}.json"
                if not file_path.exists():
                    return None
                with open(file_path) as f:
                    return json.load(f)

            elif self.storage_type == "s3":
                key = f"{self.s3_prefix}{job_id}.json"
                response = self.s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=key
                )
                return json.loads(response['Body'].read())

        except Exception as e:
            logger.warning(f"Failed to load checkpoint {job_id}: {e}")
            return None

    def delete(self, job_id: str) -> None:
        """
        Delete checkpoint.

        Args:
            job_id: Job identifier
        """
        try:
            if self.storage_type == "local":
                file_path = self.local_dir / f"{job_id}.json"
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"Deleted checkpoint {job_id}")

            elif self.storage_type == "s3":
                key = f"{self.s3_prefix}{job_id}.json"
                self.s3_client.delete_object(
                    Bucket=self.s3_bucket,
                    Key=key
                )
                logger.debug(f"Deleted checkpoint {job_id}")

        except Exception as e:
            logger.warning(f"Failed to delete checkpoint {job_id}: {e}")

    def list_checkpoints(self) -> list[str]:
        """
        List all checkpoint job IDs.

        Returns:
            List of job IDs
        """
        try:
            if self.storage_type == "local":
                return [
                    f.stem for f in self.local_dir.glob("*.json")
                ]

            elif self.storage_type == "s3":
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=self.s3_prefix
                )
                if 'Contents' not in response:
                    return []

                return [
                    obj['Key'].replace(self.s3_prefix, '').replace('.json', '')
                    for obj in response['Contents']
                    if obj['Key'].endswith('.json')
                ]

        except Exception as e:
            logger.warning(f"Failed to list checkpoints: {e}")
            return []


class CheckpointManager:
    """
    Manages checkpoints for long-running ingestion jobs.

    Provides checkpoint creation, updates, and resume functionality
    for large-scale dataset ingestion with batch processing.
    """

    def __init__(
        self,
        storage: CheckpointStorage | None = None,
        auto_save_interval: int = 10  # Save every N batches
    ):
        """
        Initialize the checkpoint manager.

        Args:
            storage: Checkpoint storage backend
            auto_save_interval: Save checkpoint every N batches
        """
        self.storage = storage or CheckpointStorage()
        self.auto_save_interval = auto_save_interval
        self._active_checkpoints: dict[str, CheckpointMetadata] = {}

    def create_checkpoint(
        self,
        job_id: str,
        job_name: str,
        total_items: int,
        total_batches: int,
        modality: str,
        dataset_name: str | None = None,
        model_id: str | None = None,
        backend_types: list[str] | None = None
    ) -> CheckpointMetadata:
        """
        Create a new checkpoint for an ingestion job.

        Args:
            job_id: Unique job identifier
            job_name: Human-readable job name
            total_items: Total number of items to process
            total_batches: Total number of batches
            modality: Content modality
            dataset_name: Name of the dataset being ingested
            model_id: Embedding model ID
            backend_types: Vector store backends

        Returns:
            CheckpointMetadata instance
        """
        now = datetime.utcnow()

        checkpoint = CheckpointMetadata(
            job_id=job_id,
            job_name=job_name,
            created_at=now,
            updated_at=now,
            status=CheckpointStatus.PENDING,
            total_items=total_items,
            processed_items=0,
            failed_items=0,
            current_batch=0,
            total_batches=total_batches,
            progress_percentage=0.0,
            modality=modality,
            dataset_name=dataset_name,
            model_id=model_id,
            backend_types=backend_types or [],
        )

        self._active_checkpoints[job_id] = checkpoint
        self._save_checkpoint(job_id, checkpoint, [])

        logger.info(f"Created checkpoint for job {job_id}: {job_name}")
        return checkpoint

    def update_progress(
        self,
        job_id: str,
        batch_index: int,
        items_processed: int,
        items_failed: int = 0,
        batch_checkpoints: list[BatchCheckpoint] | None = None,
        status: CheckpointStatus | None = None,
        error_message: str | None = None,
        cost_estimate: float | None = None
    ) -> None:
        """
        Update checkpoint progress.

        Args:
            job_id: Job identifier
            batch_index: Current batch index
            items_processed: Number of items processed in this update
            items_failed: Number of items that failed
            batch_checkpoints: List of batch checkpoints
            status: New status
            error_message: Error message if failed
            cost_estimate: Estimated cost so far
        """
        if job_id not in self._active_checkpoints:
            logger.warning(f"Checkpoint {job_id} not found in active checkpoints")
            return

        checkpoint = self._active_checkpoints[job_id]

        # Update metrics
        checkpoint.processed_items += items_processed
        checkpoint.failed_items += items_failed
        checkpoint.current_batch = batch_index
        checkpoint.progress_percentage = (
            checkpoint.processed_items / checkpoint.total_items * 100
            if checkpoint.total_items > 0 else 0.0
        )
        checkpoint.updated_at = datetime.utcnow()
        checkpoint.elapsed_seconds = (
            checkpoint.updated_at - checkpoint.created_at
        ).total_seconds()

        if status:
            checkpoint.status = status
        elif checkpoint.status == CheckpointStatus.PENDING:
            checkpoint.status = CheckpointStatus.IN_PROGRESS

        if error_message:
            checkpoint.error_message = error_message

        if cost_estimate is not None:
            checkpoint.cost_estimate = cost_estimate

        # Auto-save if interval reached
        if batch_index % self.auto_save_interval == 0 or status in [
            CheckpointStatus.COMPLETED,
            CheckpointStatus.FAILED,
            CheckpointStatus.CANCELLED
        ]:
            self._save_checkpoint(job_id, checkpoint, batch_checkpoints or [])

    def mark_completed(
        self,
        job_id: str,
        batch_checkpoints: list[BatchCheckpoint] | None = None
    ) -> None:
        """
        Mark job as completed.

        Args:
            job_id: Job identifier
            batch_checkpoints: Final batch checkpoints
        """
        self.update_progress(
            job_id,
            batch_index=self._active_checkpoints[job_id].total_batches,
            items_processed=0,
            status=CheckpointStatus.COMPLETED,
            batch_checkpoints=batch_checkpoints
        )
        logger.info(f"Marked job {job_id} as completed")

    def mark_failed(
        self,
        job_id: str,
        error_message: str,
        batch_checkpoints: list[BatchCheckpoint] | None = None
    ) -> None:
        """
        Mark job as failed.

        Args:
            job_id: Job identifier
            error_message: Error description
            batch_checkpoints: Batch checkpoints at failure
        """
        self.update_progress(
            job_id,
            batch_index=self._active_checkpoints[job_id].current_batch,
            items_processed=0,
            status=CheckpointStatus.FAILED,
            error_message=error_message,
            batch_checkpoints=batch_checkpoints
        )
        logger.error(f"Marked job {job_id} as failed: {error_message}")

    def can_resume(self, job_id: str) -> bool:
        """
        Check if a job can be resumed.

        Args:
            job_id: Job identifier

        Returns:
            True if job can be resumed
        """
        data = self.storage.load(job_id)
        if not data:
            return False

        metadata = CheckpointMetadata.from_dict(data['metadata'])
        return metadata.status in [
            CheckpointStatus.IN_PROGRESS,
            CheckpointStatus.FAILED
        ]

    def load_checkpoint(self, job_id: str) -> tuple[CheckpointMetadata, list[BatchCheckpoint]] | None:
        """
        Load checkpoint for resume.

        Args:
            job_id: Job identifier

        Returns:
            Tuple of (metadata, batch_checkpoints) or None if not found
        """
        data = self.storage.load(job_id)
        if not data:
            return None

        metadata = CheckpointMetadata.from_dict(data['metadata'])
        batch_checkpoints = [
            BatchCheckpoint.from_dict(b) for b in data['batch_checkpoints']
        ]

        self._active_checkpoints[job_id] = metadata

        logger.info(
            f"Loaded checkpoint {job_id}: "
            f"{metadata.processed_items}/{metadata.total_items} items processed"
        )

        return metadata, batch_checkpoints

    def get_completed_batches(self, job_id: str) -> set[int]:
        """
        Get set of completed batch indices.

        Args:
            job_id: Job identifier

        Returns:
            Set of completed batch indices
        """
        data = self.storage.load(job_id)
        if not data:
            return set()

        completed = set()
        for batch_data in data['batch_checkpoints']:
            batch = BatchCheckpoint.from_dict(batch_data)
            if batch.status == CheckpointStatus.COMPLETED:
                completed.add(batch.batch_index)

        return completed

    def get_pending_batches(self, job_id: str) -> list[int]:
        """
        Get list of pending batch indices (for resume).

        Args:
            job_id: Job identifier

        Returns:
            List of pending batch indices
        """
        data = self.storage.load(job_id)
        if not data:
            return []

        metadata = CheckpointMetadata.from_dict(data['metadata'])
        completed = self.get_completed_batches(job_id)

        # Return all batches that haven't completed
        return [
            i for i in range(metadata.total_batches)
            if i not in completed
        ]

    def list_jobs(self) -> list[dict[str, Any]]:
        """
        List all checkpointed jobs.

        Returns:
            List of job metadata dictionaries
        """
        jobs = []

        for job_id in self.storage.list_checkpoints():
            data = self.storage.load(job_id)
            if data:
                metadata = CheckpointMetadata.from_dict(data['metadata'])
                jobs.append(metadata.to_dict())

        return jobs

    def delete_checkpoint(self, job_id: str) -> None:
        """
        Delete a checkpoint.

        Args:
            job_id: Job identifier
        """
        if job_id in self._active_checkpoints:
            del self._active_checkpoints[job_id]

        self.storage.delete(job_id)
        logger.info(f"Deleted checkpoint {job_id}")

    def _save_checkpoint(
        self,
        job_id: str,
        metadata: CheckpointMetadata,
        batch_checkpoints: list[BatchCheckpoint]
    ) -> None:
        """Save checkpoint to storage."""
        data = {
            'metadata': metadata.to_dict(),
            'batch_checkpoints': [b.to_dict() for b in batch_checkpoints]
        }

        self.storage.save(job_id, data)
        logger.debug(f"Saved checkpoint {job_id}")

    def get_statistics(self, job_id: str) -> dict[str, Any]:
        """
        Get job statistics.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with job statistics
        """
        if job_id not in self._active_checkpoints:
            data = self.storage.load(job_id)
            if not data:
                return {}
            metadata = CheckpointMetadata.from_dict(data['metadata'])
        else:
            metadata = self._active_checkpoints[job_id]

        items_per_second = 0.0
        if metadata.elapsed_seconds > 0:
            items_per_second = metadata.processed_items / metadata.elapsed_seconds

        eta_seconds = 0.0
        if items_per_second > 0:
            remaining_items = metadata.total_items - metadata.processed_items
            eta_seconds = remaining_items / items_per_second

        return {
            "job_id": metadata.job_id,
            "job_name": metadata.job_name,
            "status": metadata.status.value,
            "progress_percentage": round(metadata.progress_percentage, 2),
            "processed_items": metadata.processed_items,
            "failed_items": metadata.failed_items,
            "total_items": metadata.total_items,
            "current_batch": metadata.current_batch,
            "total_batches": metadata.total_batches,
            "elapsed_seconds": round(metadata.elapsed_seconds, 2),
            "items_per_second": round(items_per_second, 2),
            "eta_seconds": round(eta_seconds, 2),
            "cost_estimate": metadata.cost_estimate,
            "error_message": metadata.error_message,
        }
