"""
Checkpoint Manager for Long-Running Ingestion Jobs.

Provides checkpoint/resume functionality for large-scale ingestion pipelines.
Persists progress to S3 to enable recovery from failures and pauses.
"""

import json
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from src.utils.logging_config import get_logger
from src.utils.aws_clients import aws_client_factory

logger = get_logger(__name__)


@dataclass
class CheckpointState:
    """
    State snapshot for ingestion checkpoint.

    Tracks processed items, failed items, and progress metrics.
    """
    job_id: str
    dataset_name: str
    modality: str
    started_at: str
    last_checkpoint_at: str

    # Progress tracking
    total_items: int
    processed_items: List[str] = field(default_factory=list)
    failed_items: List[str] = field(default_factory=list)
    skipped_items: List[str] = field(default_factory=list)

    # Batch progress
    current_batch_index: int = 0
    total_batches: int = 0

    # Metrics
    embeddings_generated: int = 0
    vectors_stored: int = 0
    total_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0

    # Error tracking
    error_count: int = 0
    last_error: Optional[str] = None
    retry_count: int = 0

    # Status
    status: str = "in_progress"  # in_progress, paused, completed, failed

    def mark_processed(self, item_id: str):
        """Mark an item as successfully processed."""
        if item_id not in self.processed_items:
            self.processed_items.append(item_id)

    def mark_failed(self, item_id: str, error: Optional[str] = None):
        """Mark an item as failed."""
        if item_id not in self.failed_items:
            self.failed_items.append(item_id)
        if error:
            self.last_error = error
            self.error_count += 1

    def mark_skipped(self, item_id: str):
        """Mark an item as skipped."""
        if item_id not in self.skipped_items:
            self.skipped_items.append(item_id)

    def is_processed(self, item_id: str) -> bool:
        """Check if item was already processed."""
        return item_id in self.processed_items

    def is_failed(self, item_id: str) -> bool:
        """Check if item failed."""
        return item_id in self.failed_items

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (len(self.processed_items) / self.total_items) * 100

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total_attempts = len(self.processed_items) + len(self.failed_items)
        if total_attempts == 0:
            return 0.0
        return (len(self.processed_items) / total_attempts) * 100


class CheckpointManager:
    """
    Manages checkpoints for long-running ingestion jobs.

    Features:
    - S3-based checkpoint persistence
    - Automatic periodic checkpointing
    - Resume from last checkpoint
    - Compressed checkpoint storage
    - Checkpoint history tracking

    Example:
        manager = CheckpointManager(
            job_id="ingest-msmarco-20240315",
            s3_bucket="my-checkpoints",
            checkpoint_interval=100
        )

        # Start new job
        state = manager.create_checkpoint(
            dataset_name="ms-marco",
            modality="text",
            total_items=100000
        )

        # Process items with periodic checkpointing
        for i, item in enumerate(dataset):
            process_item(item)
            state.mark_processed(item.id)

            if i % manager.checkpoint_interval == 0:
                manager.save_checkpoint(state)

        # Resume from checkpoint
        state = manager.load_checkpoint("ingest-msmarco-20240315")
        for item in dataset:
            if not state.is_processed(item.id):
                process_item(item)
    """

    def __init__(
        self,
        job_id: str,
        s3_bucket: str,
        s3_prefix: str = "ingestion-checkpoints",
        checkpoint_interval: int = 100,
        keep_history: int = 10
    ):
        """
        Initialize checkpoint manager.

        Args:
            job_id: Unique job identifier
            s3_bucket: S3 bucket for checkpoint storage
            s3_prefix: S3 prefix for checkpoint files
            checkpoint_interval: Save checkpoint every N items
            keep_history: Number of checkpoint versions to keep
        """
        self.job_id = job_id
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.checkpoint_interval = checkpoint_interval
        self.keep_history = keep_history

        self.s3_client = aws_client_factory.get_s3_client()

        # Local state tracking
        self.last_checkpoint_time = time.time()
        self.items_since_checkpoint = 0

        logger.info(
            f"CheckpointManager initialized: job={job_id}, bucket={s3_bucket}, "
            f"interval={checkpoint_interval}"
        )

    def create_checkpoint(
        self,
        dataset_name: str,
        modality: str,
        total_items: int
    ) -> CheckpointState:
        """
        Create initial checkpoint state for a new job.

        Args:
            dataset_name: Name of the dataset being ingested
            modality: Modality type (text, image, audio, video)
            total_items: Total number of items to process

        Returns:
            Initial CheckpointState
        """
        now = datetime.utcnow().isoformat()
        state = CheckpointState(
            job_id=self.job_id,
            dataset_name=dataset_name,
            modality=modality,
            started_at=now,
            last_checkpoint_at=now,
            total_items=total_items
        )

        logger.info(f"Created new checkpoint for job {self.job_id}: {total_items} items")
        return state

    def save_checkpoint(self, state: CheckpointState, force: bool = False) -> bool:
        """
        Save checkpoint to S3.

        Args:
            state: Current checkpoint state
            force: Force save even if interval not reached

        Returns:
            True if checkpoint saved, False if skipped
        """
        # Check if we should save (interval or force)
        if not force:
            if self.items_since_checkpoint < self.checkpoint_interval:
                return False

        # Update checkpoint timestamp
        state.last_checkpoint_at = datetime.utcnow().isoformat()

        # Generate S3 key with timestamp for versioning
        timestamp = int(time.time())
        checkpoint_key = f"{self.s3_prefix}/{self.job_id}/checkpoint-{timestamp}.json"

        try:
            # Serialize state
            checkpoint_data = asdict(state)
            checkpoint_json = json.dumps(checkpoint_data, indent=2)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=checkpoint_key,
                Body=checkpoint_json,
                ContentType="application/json",
                Metadata={
                    "job_id": self.job_id,
                    "dataset": state.dataset_name,
                    "progress": f"{state.progress_percentage:.2f}%"
                }
            )

            # Update latest pointer
            latest_key = f"{self.s3_prefix}/{self.job_id}/latest.json"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=latest_key,
                Body=checkpoint_json,
                ContentType="application/json"
            )

            logger.info(
                f"Checkpoint saved: {checkpoint_key} "
                f"({state.progress_percentage:.1f}% complete, "
                f"{len(state.processed_items)} processed)"
            )

            # Reset counters
            self.last_checkpoint_time = time.time()
            self.items_since_checkpoint = 0

            # Clean up old checkpoints
            self._cleanup_old_checkpoints()

            return True

        except ClientError as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def load_checkpoint(self, job_id: Optional[str] = None) -> Optional[CheckpointState]:
        """
        Load checkpoint from S3.

        Args:
            job_id: Job ID to load (defaults to current job)

        Returns:
            CheckpointState if found, None otherwise
        """
        if not job_id:
            job_id = self.job_id

        latest_key = f"{self.s3_prefix}/{job_id}/latest.json"

        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=latest_key
            )

            checkpoint_json = response['Body'].read().decode('utf-8')
            checkpoint_data = json.loads(checkpoint_json)

            # Convert lists back to proper types
            state = CheckpointState(**checkpoint_data)

            logger.info(
                f"Loaded checkpoint for job {job_id}: "
                f"{len(state.processed_items)}/{state.total_items} items processed "
                f"({state.progress_percentage:.1f}% complete)"
            )

            return state

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"No checkpoint found for job {job_id}")
                return None
            else:
                logger.error(f"Failed to load checkpoint: {e}")
                return None

    def checkpoint_exists(self, job_id: Optional[str] = None) -> bool:
        """
        Check if a checkpoint exists for a job.

        Args:
            job_id: Job ID to check (defaults to current job)

        Returns:
            True if checkpoint exists
        """
        if not job_id:
            job_id = self.job_id

        latest_key = f"{self.s3_prefix}/{job_id}/latest.json"

        try:
            self.s3_client.head_object(
                Bucket=self.s3_bucket,
                Key=latest_key
            )
            return True
        except ClientError:
            return False

    def list_checkpoints(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all checkpoint versions for a job.

        Args:
            job_id: Job ID to list (defaults to current job)

        Returns:
            List of checkpoint metadata
        """
        if not job_id:
            job_id = self.job_id

        prefix = f"{self.s3_prefix}/{job_id}/checkpoint-"

        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )

            checkpoints = []
            for obj in response.get('Contents', []):
                checkpoints.append({
                    'key': obj['Key'],
                    'timestamp': obj['LastModified'].isoformat(),
                    'size_bytes': obj['Size']
                })

            # Sort by timestamp (newest first)
            checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)

            return checkpoints

        except ClientError as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    def delete_checkpoint(self, job_id: Optional[str] = None):
        """
        Delete all checkpoints for a job.

        Args:
            job_id: Job ID to delete (defaults to current job)
        """
        if not job_id:
            job_id = self.job_id

        prefix = f"{self.s3_prefix}/{job_id}/"

        try:
            # List all objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )

            # Delete all objects
            objects = [{'Key': obj['Key']} for obj in response.get('Contents', [])]
            if objects:
                self.s3_client.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete={'Objects': objects}
                )

            logger.info(f"Deleted {len(objects)} checkpoint files for job {job_id}")

        except ClientError as e:
            logger.error(f"Failed to delete checkpoints: {e}")

    def should_checkpoint(self, items_processed: int) -> bool:
        """
        Check if we should save a checkpoint based on interval.

        Args:
            items_processed: Number of items processed since last checkpoint

        Returns:
            True if checkpoint should be saved
        """
        self.items_since_checkpoint = items_processed
        return self.items_since_checkpoint >= self.checkpoint_interval

    def _cleanup_old_checkpoints(self):
        """Remove old checkpoint versions, keeping only recent history."""
        checkpoints = self.list_checkpoints()

        # Keep only the most recent N checkpoints
        if len(checkpoints) > self.keep_history:
            old_checkpoints = checkpoints[self.keep_history:]

            objects_to_delete = [{'Key': cp['key']} for cp in old_checkpoints]

            try:
                self.s3_client.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete={'Objects': objects_to_delete}
                )

                logger.debug(f"Cleaned up {len(objects_to_delete)} old checkpoints")

            except ClientError as e:
                logger.warning(f"Failed to cleanup old checkpoints: {e}")
