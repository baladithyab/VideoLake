"""
Large-Scale Batch Processor for Dataset Ingestion.

Provides production-grade batch processing with:
- Configurable chunk sizes (10K-100K items)
- Checkpoint/resume capability for long-running jobs
- Progress tracking and cost estimation
- Rate limiting and retry logic
- Multi-modal support (text, image, audio, video)
"""

import asyncio
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, AsyncIterator
from enum import Enum

from src.services.unified_ingestion_service import (
    UnifiedIngestionService,
    IngestionRequest,
    IngestionResult
)
from src.services.embedding_provider import ModalityType
from src.services.vector_store_provider import VectorStoreType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """Status of batch processing job."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    job_id: str
    modality: ModalityType
    vector_store_type: VectorStoreType
    vector_store_name: str
    batch_size: int = 100
    max_concurrent: int = 5
    rate_limit_requests_per_second: float = 10.0
    checkpoint_interval: int = 100
    checkpoint_dir: str = ".checkpoints"
    enable_cost_tracking: bool = True
    enable_progress_tracking: bool = True
    embedding_provider_id: Optional[str] = None
    embedding_model_id: Optional[str] = None


@dataclass
class BatchCheckpoint:
    """Checkpoint for resuming batch processing."""
    job_id: str
    total_items: int
    processed_items: int
    failed_items: int
    successful_items: int
    last_processed_index: int
    status: ProcessingStatus
    start_time: str
    last_update_time: str
    total_embedding_time_ms: int = 0
    total_storage_time_ms: int = 0
    estimated_cost_usd: float = 0.0
    error_log: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.error_log is None:
            self.error_log = []


@dataclass
class BatchResult:
    """Final result of batch processing."""
    job_id: str
    status: ProcessingStatus
    total_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    total_time_seconds: float
    total_embedding_time_ms: int
    total_storage_time_ms: int
    estimated_cost_usd: float
    throughput_items_per_second: float
    error_summary: Dict[str, int]


class BatchProcessor:
    """
    Production-grade batch processor for large-scale dataset ingestion.

    Handles 10K-100K+ items with checkpointing, rate limiting, and comprehensive tracking.
    """

    # Cost estimates per 1K operations (in USD)
    COST_ESTIMATES = {
        'bedrock_text_embedding': 0.0001,
        'bedrock_image_embedding': 0.0008,
        'sagemaker_inference': 0.0005,
        's3_put_requests': 0.000005,
        's3_storage_gb_month': 0.023,
    }

    def __init__(self, config: BatchConfig):
        """Initialize batch processor with configuration."""
        self.config = config
        self.ingestion_service = UnifiedIngestionService()
        self.checkpoint_path = Path(config.checkpoint_dir) / f"{config.job_id}.json"
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing checkpoint if available
        self.checkpoint = self._load_checkpoint()
        if not self.checkpoint:
            self.checkpoint = BatchCheckpoint(
                job_id=config.job_id,
                total_items=0,
                processed_items=0,
                failed_items=0,
                successful_items=0,
                last_processed_index=-1,
                status=ProcessingStatus.PENDING,
                start_time=datetime.utcnow().isoformat(),
                last_update_time=datetime.utcnow().isoformat()
            )

    def _load_checkpoint(self) -> Optional[BatchCheckpoint]:
        """Load checkpoint from disk if exists."""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, 'r') as f:
                    data = json.load(f)
                    data['status'] = ProcessingStatus(data['status'])
                    checkpoint = BatchCheckpoint(**data)
                    logger.info(f"Loaded checkpoint: {checkpoint.processed_items}/{checkpoint.total_items} items processed")
                    return checkpoint
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
                return None
        return None

    def _save_checkpoint(self):
        """Save checkpoint to disk."""
        try:
            checkpoint_dict = asdict(self.checkpoint)
            checkpoint_dict['status'] = self.checkpoint.status.value
            checkpoint_dict['last_update_time'] = datetime.utcnow().isoformat()

            with open(self.checkpoint_path, 'w') as f:
                json.dump(checkpoint_dict, f, indent=2)

            logger.debug(f"Checkpoint saved: {self.checkpoint.processed_items}/{self.checkpoint.total_items}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _estimate_cost(self, items_count: int, modality: ModalityType) -> float:
        """Estimate cost for processing items."""
        cost = 0.0

        # Embedding cost
        if modality == ModalityType.TEXT:
            cost += (items_count / 1000) * self.COST_ESTIMATES['bedrock_text_embedding']
        elif modality in [ModalityType.IMAGE, ModalityType.VIDEO]:
            cost += items_count * self.COST_ESTIMATES['bedrock_image_embedding']
        elif modality == ModalityType.AUDIO:
            cost += (items_count / 1000) * self.COST_ESTIMATES['sagemaker_inference']

        # S3 storage cost (rough estimate)
        cost += (items_count / 1000) * self.COST_ESTIMATES['s3_put_requests']

        return round(cost, 4)

    async def process_batch(
        self,
        data_source: AsyncIterator[Any],
        total_items: Optional[int] = None,
        metadata_fn: Optional[Callable[[Any, int], Dict[str, Any]]] = None
    ) -> BatchResult:
        """
        Process a batch of items from an async data source.

        Args:
            data_source: Async iterator yielding items to process
            total_items: Total number of items (for progress tracking)
            metadata_fn: Optional function to extract metadata from each item

        Returns:
            BatchResult with processing statistics
        """
        start_time = time.time()

        # Initialize checkpoint if first run
        if self.checkpoint.status == ProcessingStatus.PENDING:
            self.checkpoint.total_items = total_items or 0
            self.checkpoint.status = ProcessingStatus.IN_PROGRESS
            self._save_checkpoint()

        logger.info(f"Starting batch processing: job_id={self.config.job_id}")
        logger.info(f"Configuration: batch_size={self.config.batch_size}, "
                   f"max_concurrent={self.config.max_concurrent}, "
                   f"rate_limit={self.config.rate_limit_requests_per_second}/s")

        # Process items in batches
        batch_items = []
        batch_metadata = []
        current_index = self.checkpoint.last_processed_index + 1

        async for idx, item in self._enumerate_with_resume(data_source, current_index):
            batch_items.append(item)

            # Extract metadata if function provided
            if metadata_fn:
                metadata = metadata_fn(item, idx)
            else:
                metadata = {"index": idx, "job_id": self.config.job_id}
            batch_metadata.append(metadata)

            # Process batch when full
            if len(batch_items) >= self.config.batch_size:
                await self._process_batch_chunk(
                    batch_items,
                    batch_metadata,
                    current_index - len(batch_items) + 1
                )
                batch_items = []
                batch_metadata = []

            current_index = idx

        # Process remaining items
        if batch_items:
            await self._process_batch_chunk(
                batch_items,
                batch_metadata,
                current_index - len(batch_items) + 1
            )

        # Mark as completed
        self.checkpoint.status = ProcessingStatus.COMPLETED
        self._save_checkpoint()

        # Calculate final statistics
        total_time = time.time() - start_time
        throughput = self.checkpoint.successful_items / total_time if total_time > 0 else 0

        # Summarize errors
        error_summary = {}
        for error in self.checkpoint.error_log:
            error_type = error.get('error_type', 'unknown')
            error_summary[error_type] = error_summary.get(error_type, 0) + 1

        result = BatchResult(
            job_id=self.config.job_id,
            status=self.checkpoint.status,
            total_items=self.checkpoint.total_items,
            successful_items=self.checkpoint.successful_items,
            failed_items=self.checkpoint.failed_items,
            skipped_items=current_index + 1 - self.checkpoint.processed_items,
            total_time_seconds=total_time,
            total_embedding_time_ms=self.checkpoint.total_embedding_time_ms,
            total_storage_time_ms=self.checkpoint.total_storage_time_ms,
            estimated_cost_usd=self.checkpoint.estimated_cost_usd,
            throughput_items_per_second=throughput,
            error_summary=error_summary
        )

        logger.info(f"Batch processing completed: {result.successful_items}/{result.total_items} successful, "
                   f"throughput={result.throughput_items_per_second:.2f} items/s, "
                   f"estimated_cost=${result.estimated_cost_usd:.4f}")

        return result

    async def _enumerate_with_resume(self, data_source: AsyncIterator[Any], start_index: int):
        """Enumerate data source, resuming from checkpoint."""
        idx = 0
        async for item in data_source:
            if idx >= start_index:
                yield idx, item
            idx += 1

    async def _process_batch_chunk(
        self,
        items: List[Any],
        metadata_list: List[Dict[str, Any]],
        start_index: int
    ):
        """Process a chunk of items with rate limiting."""
        logger.info(f"Processing chunk: {len(items)} items starting at index {start_index}")

        # Create ingestion requests
        requests = []
        for item, metadata in zip(items, metadata_list):
            request = IngestionRequest(
                modality=self.config.modality,
                content=item,
                vector_store_type=self.config.vector_store_type,
                vector_store_name=self.config.vector_store_name,
                embedding_provider_id=self.config.embedding_provider_id,
                embedding_model_id=self.config.embedding_model_id,
                metadata=metadata
            )
            requests.append(request)

        # Process with rate limiting
        results = await self._process_with_rate_limit(requests)

        # Update checkpoint
        for idx, result in enumerate(results):
            self.checkpoint.processed_items += 1
            self.checkpoint.last_processed_index = start_index + idx

            if result.success:
                self.checkpoint.successful_items += result.vectors_ingested
                self.checkpoint.total_embedding_time_ms += result.embedding_time_ms
                self.checkpoint.total_storage_time_ms += result.storage_time_ms
            else:
                self.checkpoint.failed_items += 1
                # Log error
                error_entry = {
                    "index": start_index + idx,
                    "error_type": result.errors[0] if result.errors else "unknown",
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.checkpoint.error_log.append(error_entry)

        # Update cost estimate
        if self.config.enable_cost_tracking:
            self.checkpoint.estimated_cost_usd += self._estimate_cost(
                len(items),
                self.config.modality
            )

        # Save checkpoint at interval
        if self.checkpoint.processed_items % self.config.checkpoint_interval == 0:
            self._save_checkpoint()
            logger.info(f"Progress: {self.checkpoint.processed_items}/{self.checkpoint.total_items} "
                       f"({self.checkpoint.successful_items} successful, {self.checkpoint.failed_items} failed)")

    async def _process_with_rate_limit(
        self,
        requests: List[IngestionRequest]
    ) -> List[IngestionResult]:
        """Process requests with rate limiting."""
        # Calculate delay between requests to respect rate limit
        delay = 1.0 / self.config.rate_limit_requests_per_second

        # Process in parallel batches with concurrency limit
        results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def process_with_semaphore(request: IngestionRequest) -> IngestionResult:
            async with semaphore:
                result = await self.ingestion_service.ingest(request)
                await asyncio.sleep(delay)  # Rate limiting
                return result

        # Execute all requests
        results = await asyncio.gather(
            *[process_with_semaphore(req) for req in requests],
            return_exceptions=True
        )

        # Convert exceptions to failed results
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Processing failed: {result}")
                processed_results.append(
                    IngestionResult(
                        success=False,
                        vectors_ingested=0,
                        vectors_failed=1,
                        embedding_time_ms=0,
                        storage_time_ms=0,
                        total_time_ms=0,
                        errors=[str(result)]
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def get_progress(self) -> Dict[str, Any]:
        """Get current processing progress."""
        progress_pct = 0.0
        if self.checkpoint.total_items > 0:
            progress_pct = (self.checkpoint.processed_items / self.checkpoint.total_items) * 100

        return {
            "job_id": self.config.job_id,
            "status": self.checkpoint.status.value,
            "total_items": self.checkpoint.total_items,
            "processed_items": self.checkpoint.processed_items,
            "successful_items": self.checkpoint.successful_items,
            "failed_items": self.checkpoint.failed_items,
            "progress_percent": round(progress_pct, 2),
            "estimated_cost_usd": self.checkpoint.estimated_cost_usd,
            "avg_embedding_time_ms": (
                self.checkpoint.total_embedding_time_ms / self.checkpoint.successful_items
                if self.checkpoint.successful_items > 0 else 0
            ),
            "avg_storage_time_ms": (
                self.checkpoint.total_storage_time_ms / self.checkpoint.successful_items
                if self.checkpoint.successful_items > 0 else 0
            )
        }

    def pause(self):
        """Pause processing (save checkpoint and mark as paused)."""
        self.checkpoint.status = ProcessingStatus.PAUSED
        self._save_checkpoint()
        logger.info(f"Job paused: {self.config.job_id}")

    def resume(self):
        """Resume processing from last checkpoint."""
        if self.checkpoint.status == ProcessingStatus.PAUSED:
            self.checkpoint.status = ProcessingStatus.IN_PROGRESS
            logger.info(f"Job resumed: {self.config.job_id} from index {self.checkpoint.last_processed_index}")
        else:
            logger.warning(f"Cannot resume job with status: {self.checkpoint.status}")
