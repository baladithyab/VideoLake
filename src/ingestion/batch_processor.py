"""
Batch Processor for Large-Scale Dataset Ingestion.

Provides configurable batch processing with chunking, parallel execution,
and progress tracking for 10K-100K item datasets across all modalities.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from src.ingestion.checkpoint_manager import CheckpointManager
from src.ingestion.rate_limiter import RateLimitedExecutor, RateLimiterConfig
from src.services.embedding_provider import (
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResponse,
    ModalityType,
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 100  # Items per batch
    max_concurrent_batches: int = 5  # Parallel batch processing
    rate_limit_rps: float = 10.0  # Requests per second
    max_retries: int = 3  # Retry attempts per batch
    enable_checkpointing: bool = True  # Enable checkpoint/resume
    checkpoint_interval: int = 10  # Save checkpoint every N batches


@dataclass
class BatchResult:
    """Result of processing a single batch."""
    batch_index: int
    success_count: int
    failure_count: int
    embeddings: list[EmbeddingResponse]
    errors: list[dict[str, Any]]
    processing_time_ms: int
    cost_estimate: float


class BatchProcessor:
    """
    Batch processor for large-scale dataset ingestion.

    Handles chunking, parallel processing, rate limiting, and
    checkpoint/resume for processing 10K-100K item datasets.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        config: BatchConfig | None = None,
        rate_limiter: RateLimitedExecutor | None = None,
        checkpoint_manager: CheckpointManager | None = None
    ):
        """
        Initialize the batch processor.

        Args:
            embedding_provider: Provider for generating embeddings
            config: Batch processing configuration
            rate_limiter: Rate limiter for API calls
            checkpoint_manager: Checkpoint manager for resume capability
        """
        self.embedding_provider = embedding_provider
        self.config = config or BatchConfig()

        # Initialize rate limiter
        if rate_limiter:
            self.rate_limiter = rate_limiter
        else:
            rate_config = RateLimiterConfig(
                requests_per_second=self.config.rate_limit_rps,
                max_retries=self.config.max_retries
            )
            self.rate_limiter = RateLimitedExecutor(rate_config)

        # Initialize checkpoint manager
        self.checkpoint_manager = checkpoint_manager
        if self.config.enable_checkpointing and not checkpoint_manager:
            self.checkpoint_manager = CheckpointManager(
                auto_save_interval=self.config.checkpoint_interval
            )

        logger.info(
            f"Initialized batch processor: "
            f"batch_size={self.config.batch_size}, "
            f"max_concurrent={self.config.max_concurrent_batches}"
        )

    def create_batches(
        self,
        items: list[Any],
        batch_size: int | None = None
    ) -> list[list[Any]]:
        """
        Split items into batches.

        Args:
            items: List of items to batch
            batch_size: Override default batch size

        Returns:
            List of batches
        """
        batch_size = batch_size or self.config.batch_size
        batches = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)

        logger.info(
            f"Created {len(batches)} batches from {len(items)} items "
            f"(batch_size={batch_size})"
        )

        return batches

    async def process_batch(
        self,
        batch: list[Any],
        batch_index: int,
        modality: ModalityType,
        model_id: str | None = None,
        transform_fn: Callable[[Any], str] | None = None
    ) -> BatchResult:
        """
        Process a single batch of items.

        Args:
            batch: Batch of items to process
            batch_index: Index of this batch
            modality: Content modality
            model_id: Embedding model ID
            transform_fn: Optional function to transform items to content strings

        Returns:
            BatchResult with embeddings and statistics
        """
        import time
        start_time = time.time()

        embeddings = []
        errors = []
        success_count = 0
        failure_count = 0
        total_cost = 0.0

        logger.info(f"Processing batch {batch_index} ({len(batch)} items)")

        # Process items in batch
        for item_index, item in enumerate(batch):
            try:
                # Transform item to content if needed
                if transform_fn:
                    content = transform_fn(item)
                else:
                    content = str(item)

                # Create embedding request
                request = EmbeddingRequest(
                    modality=modality,
                    content=content,
                    model_id=model_id
                )

                # Generate embedding with rate limiting and retry
                response = await self.rate_limiter.execute(
                    self.embedding_provider.generate_embedding,
                    request
                )

                embeddings.append(response)
                success_count += 1

                if response.cost_estimate:
                    total_cost += response.cost_estimate

            except Exception as e:
                logger.error(
                    f"Failed to process item {item_index} in batch {batch_index}: {e}"
                )
                errors.append({
                    'item_index': item_index,
                    'error': str(e),
                    'item': str(item)[:100]  # Truncate for logging
                })
                failure_count += 1

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Batch {batch_index} complete: "
            f"{success_count} success, {failure_count} failed, "
            f"{processing_time_ms}ms"
        )

        return BatchResult(
            batch_index=batch_index,
            success_count=success_count,
            failure_count=failure_count,
            embeddings=embeddings,
            errors=errors,
            processing_time_ms=processing_time_ms,
            cost_estimate=total_cost
        )

    async def process_batches(
        self,
        batches: list[list[Any]],
        modality: ModalityType,
        model_id: str | None = None,
        transform_fn: Callable[[Any], str] | None = None,
        job_id: str | None = None,
        job_name: str | None = None,
        progress_callback: Callable[[int, int, float], None] | None = None
    ) -> list[BatchResult]:
        """
        Process multiple batches with concurrency control.

        Args:
            batches: List of batches to process
            modality: Content modality
            model_id: Embedding model ID
            transform_fn: Optional function to transform items
            job_id: Job ID for checkpointing
            job_name: Job name for checkpointing
            progress_callback: Optional callback for progress updates

        Returns:
            List of BatchResult objects
        """
        results = []
        total_batches = len(batches)
        total_items = sum(len(batch) for batch in batches)

        # Create checkpoint if enabled
        if self.checkpoint_manager and job_id:
            checkpoint_meta = self.checkpoint_manager.create_checkpoint(
                job_id=job_id,
                job_name=job_name or f"batch_ingestion_{modality.value}",
                total_items=total_items,
                total_batches=total_batches,
                modality=modality.value,
                model_id=model_id
            )

        # Check for resume
        pending_indices = list(range(total_batches))
        if self.checkpoint_manager and job_id:
            if self.checkpoint_manager.can_resume(job_id):
                pending_indices = self.checkpoint_manager.get_pending_batches(job_id)
                logger.info(
                    f"Resuming job {job_id}: "
                    f"{len(pending_indices)}/{total_batches} batches remaining"
                )

        # Process batches with concurrency control
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        processed_count = total_batches - len(pending_indices)

        async def process_with_semaphore(batch_idx: int) -> BatchResult:
            async with semaphore:
                batch = batches[batch_idx]
                result = await self.process_batch(
                    batch=batch,
                    batch_index=batch_idx,
                    modality=modality,
                    model_id=model_id,
                    transform_fn=transform_fn
                )

                # Update checkpoint
                if self.checkpoint_manager and job_id:
                    self.checkpoint_manager.update_progress(
                        job_id=job_id,
                        batch_index=batch_idx,
                        items_processed=result.success_count,
                        items_failed=result.failure_count,
                        cost_estimate=result.cost_estimate
                    )

                # Call progress callback
                nonlocal processed_count
                processed_count += 1
                progress_pct = (processed_count / total_batches) * 100

                if progress_callback:
                    progress_callback(processed_count, total_batches, progress_pct)

                return result

        # Execute all pending batches
        tasks = [process_with_semaphore(idx) for idx in pending_indices]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results and errors
        final_results = []
        total_success = 0
        total_failed = 0
        total_cost = 0.0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch {pending_indices[i]} failed with exception: {result}")
                # Create error result
                error_result = BatchResult(
                    batch_index=pending_indices[i],
                    success_count=0,
                    failure_count=len(batches[pending_indices[i]]),
                    embeddings=[],
                    errors=[{'error': str(result)}],
                    processing_time_ms=0,
                    cost_estimate=0.0
                )
                final_results.append(error_result)
                total_failed += len(batches[pending_indices[i]])
            else:
                final_results.append(result)
                total_success += result.success_count
                total_failed += result.failure_count
                total_cost += result.cost_estimate

        # Mark checkpoint as completed
        if self.checkpoint_manager and job_id:
            if total_failed == 0:
                self.checkpoint_manager.mark_completed(job_id)
            else:
                self.checkpoint_manager.mark_failed(
                    job_id,
                    f"{total_failed} items failed processing"
                )

        logger.info(
            f"Batch processing complete: "
            f"{total_success} success, {total_failed} failed, "
            f"${total_cost:.4f} estimated cost"
        )

        return final_results

    async def process_items(
        self,
        items: list[Any],
        modality: ModalityType,
        model_id: str | None = None,
        batch_size: int | None = None,
        transform_fn: Callable[[Any], str] | None = None,
        job_id: str | None = None,
        job_name: str | None = None,
        progress_callback: Callable[[int, int, float], None] | None = None
    ) -> list[BatchResult]:
        """
        Process a list of items end-to-end (chunking + processing).

        Args:
            items: List of items to process
            modality: Content modality
            model_id: Embedding model ID
            batch_size: Override default batch size
            transform_fn: Optional function to transform items
            job_id: Job ID for checkpointing
            job_name: Job name
            progress_callback: Progress callback

        Returns:
            List of BatchResult objects
        """
        # Create batches
        batches = self.create_batches(items, batch_size)

        # Process batches
        return await self.process_batches(
            batches=batches,
            modality=modality,
            model_id=model_id,
            transform_fn=transform_fn,
            job_id=job_id,
            job_name=job_name,
            progress_callback=progress_callback
        )

    def get_statistics(self) -> dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with statistics
        """
        stats = {
            "config": {
                "batch_size": self.config.batch_size,
                "max_concurrent_batches": self.config.max_concurrent_batches,
                "rate_limit_rps": self.config.rate_limit_rps,
            },
            "rate_limiter": self.rate_limiter.get_statistics(),
        }

        return stats
