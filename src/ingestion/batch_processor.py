"""
Batch Processor for Large-Scale Multi-Modal Ingestion.

Orchestrates batch processing of 10K-100K+ items with:
- Configurable batch sizes and chunking
- Checkpoint/resume for long-running jobs
- Rate limiting for AWS services
- Progress tracking and cost estimation
- Error handling and retry logic
- Support for all modalities (text, image, audio, video)
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable, AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.ingestion.checkpoint import CheckpointManager, CheckpointState
from src.ingestion.rate_limiter import RateLimiter, ServiceType
from src.services.embedding_provider import (
    EmbeddingProviderFactory,
    ModalityType,
    EmbeddingRequest
)
from src.services.vector_store_provider import VectorStoreProviderFactory, VectorStoreType
from src.utils.logging_config import get_logger
from src.utils.aws_retry import AWSRetryHandler
from src.exceptions import ProcessingError, VectorEmbeddingError

logger = get_logger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    # Batch sizing
    batch_size: int = 50  # Items per batch
    max_concurrent_batches: int = 5  # Parallel batch processing
    chunk_size: Optional[int] = None  # For text chunking (None = no chunking)

    # Checkpointing
    enable_checkpointing: bool = True
    checkpoint_interval: int = 100  # Items per checkpoint
    checkpoint_s3_bucket: str = "s3vector-checkpoints"

    # Rate limiting
    enable_rate_limiting: bool = True
    bedrock_rps: Optional[float] = None  # Override default rate limit

    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Resource limits
    max_processing_time_hours: Optional[float] = None
    max_cost_usd: Optional[float] = None

    # Progress reporting
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    log_interval: int = 10  # Log progress every N batches


@dataclass
class BatchItem:
    """
    Item to be processed in a batch.

    Represents a single data item (text, image, audio, video) with metadata.
    """
    item_id: str
    content: Any  # Text string, image bytes, S3 URI, etc.
    modality: ModalityType
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result from processing a single batch."""
    batch_id: int
    success: bool
    items_processed: int
    items_failed: int
    embeddings_generated: int
    vectors_stored: int
    processing_time_seconds: float
    cost_usd: float
    errors: List[str] = field(default_factory=list)


@dataclass
class IngestionJobResult:
    """Final result from ingestion job."""
    job_id: str
    success: bool
    total_items: int
    items_processed: int
    items_failed: int
    items_skipped: int

    total_batches: int
    embeddings_generated: int
    vectors_stored: int

    total_time_seconds: float
    total_cost_usd: float

    # Performance metrics
    avg_items_per_second: float
    avg_cost_per_item: float

    # Error summary
    error_count: int

    started_at: str
    completed_at: str

    # Errors (with default, must come last)
    errors: List[str] = field(default_factory=list)


class BatchProcessor:
    """
    Production-grade batch processor for large-scale ingestion.

    Handles 10K-100K+ items with:
    - Automatic batching and parallelization
    - Checkpoint/resume for fault tolerance
    - Rate limiting to prevent throttling
    - Cost tracking and limits
    - Progress reporting

    Example:
        # Configure processor
        config = BatchConfig(
            batch_size=100,
            max_concurrent_batches=10,
            enable_checkpointing=True,
            checkpoint_interval=500,
            max_cost_usd=100.0
        )

        processor = BatchProcessor(
            job_id="ingest-msmarco-100k",
            config=config
        )

        # Process dataset
        async def item_generator():
            for item in dataset:
                yield BatchItem(
                    item_id=item['id'],
                    content=item['text'],
                    modality=ModalityType.TEXT,
                    metadata={'source': 'ms-marco'}
                )

        result = await processor.process_dataset(
            items=item_generator(),
            dataset_name="ms-marco-100k",
            embedding_provider_id="bedrock-titan",
            vector_store_type=VectorStoreType.S3VECTOR,
            vector_store_name="msmarco-index"
        )

        print(f"Processed: {result.items_processed}/{result.total_items}")
        print(f"Cost: ${result.total_cost_usd:.2f}")
        print(f"Throughput: {result.avg_items_per_second:.1f} items/sec")
    """

    def __init__(self, job_id: str, config: BatchConfig):
        """
        Initialize batch processor.

        Args:
            job_id: Unique job identifier
            config: Batch processing configuration
        """
        self.job_id = job_id
        self.config = config

        # Initialize components
        self.embedding_factory = EmbeddingProviderFactory()
        self.vector_store_factory = VectorStoreProviderFactory()

        # Rate limiter
        if config.enable_rate_limiting:
            self.rate_limiter = RateLimiter()
        else:
            self.rate_limiter = None

        # Checkpoint manager
        if config.enable_checkpointing:
            self.checkpoint_manager = CheckpointManager(
                job_id=job_id,
                s3_bucket=config.checkpoint_s3_bucket,
                checkpoint_interval=config.checkpoint_interval
            )
        else:
            self.checkpoint_manager = None

        # State tracking
        self.start_time: Optional[float] = None
        self.batches_processed = 0

        logger.info(
            f"BatchProcessor initialized: job={job_id}, "
            f"batch_size={config.batch_size}, "
            f"checkpointing={'enabled' if config.enable_checkpointing else 'disabled'}"
        )

    async def process_dataset(
        self,
        items: AsyncIterator[BatchItem],
        dataset_name: str,
        embedding_provider_id: str,
        vector_store_type: VectorStoreType,
        vector_store_name: str,
        resume: bool = False
    ) -> IngestionJobResult:
        """
        Process entire dataset with batching and checkpointing.

        Args:
            items: Async iterator of BatchItem objects
            dataset_name: Name of dataset being processed
            embedding_provider_id: ID of embedding provider to use
            vector_store_type: Type of vector store
            vector_store_name: Name of vector store/index
            resume: Resume from checkpoint if available

        Returns:
            IngestionJobResult with complete metrics
        """
        self.start_time = time.time()
        started_at = datetime.utcnow().isoformat()

        logger.info(f"Starting ingestion job: {self.job_id} - {dataset_name}")

        # Try to resume from checkpoint
        checkpoint_state: Optional[CheckpointState] = None
        if resume and self.checkpoint_manager:
            checkpoint_state = self.checkpoint_manager.load_checkpoint()
            if checkpoint_state:
                logger.info(
                    f"Resuming from checkpoint: {len(checkpoint_state.processed_items)} "
                    f"items already processed"
                )

        # Initialize checkpoint if not resuming
        if not checkpoint_state:
            # Count total items (need to consume iterator first)
            items_list = []
            async for item in items:
                items_list.append(item)

            total_items = len(items_list)

            if self.checkpoint_manager:
                checkpoint_state = self.checkpoint_manager.create_checkpoint(
                    dataset_name=dataset_name,
                    modality=items_list[0].modality.value if items_list else "unknown",
                    total_items=total_items
                )

            # Convert back to async iterator
            async def items_from_list():
                for item in items_list:
                    yield item

            items = items_from_list()

        # Get embedding provider
        embedding_provider = self.embedding_factory.create_provider(embedding_provider_id)
        if not embedding_provider:
            raise ProcessingError(f"Embedding provider not found: {embedding_provider_id}")

        # Get vector store provider
        vector_store_provider = self.vector_store_factory.create_provider(vector_store_type)

        # Process batches
        current_batch = []
        batch_results = []

        try:
            async for item in items:
                # Skip if already processed
                if checkpoint_state and checkpoint_state.is_processed(item.item_id):
                    checkpoint_state.mark_skipped(item.item_id)
                    continue

                current_batch.append(item)

                # Process batch when full
                if len(current_batch) >= self.config.batch_size:
                    result = await self._process_batch(
                        batch=current_batch,
                        embedding_provider=embedding_provider,
                        vector_store_provider=vector_store_provider,
                        vector_store_name=vector_store_name,
                        checkpoint_state=checkpoint_state
                    )

                    batch_results.append(result)
                    current_batch = []
                    self.batches_processed += 1

                    # Update checkpoint
                    if checkpoint_state and self.checkpoint_manager:
                        if self.checkpoint_manager.should_checkpoint(result.items_processed):
                            self.checkpoint_manager.save_checkpoint(checkpoint_state)

                    # Progress callback
                    if self.config.progress_callback:
                        self._call_progress_callback(checkpoint_state, batch_results)

                    # Check resource limits
                    self._check_resource_limits(checkpoint_state)

                    # Log progress
                    if self.batches_processed % self.config.log_interval == 0:
                        self._log_progress(checkpoint_state, batch_results)

            # Process remaining items
            if current_batch:
                result = await self._process_batch(
                    batch=current_batch,
                    embedding_provider=embedding_provider,
                    vector_store_provider=vector_store_provider,
                    vector_store_name=vector_store_name,
                    checkpoint_state=checkpoint_state
                )
                batch_results.append(result)

            # Final checkpoint
            if checkpoint_state and self.checkpoint_manager:
                checkpoint_state.status = "completed"
                self.checkpoint_manager.save_checkpoint(checkpoint_state, force=True)

            # Compile final result
            total_time = time.time() - self.start_time
            completed_at = datetime.utcnow().isoformat()

            result = self._compile_final_result(
                checkpoint_state=checkpoint_state,
                batch_results=batch_results,
                total_time=total_time,
                started_at=started_at,
                completed_at=completed_at
            )

            logger.info(
                f"Ingestion complete: {result.items_processed}/{result.total_items} items "
                f"in {total_time/3600:.2f}h, ${result.total_cost_usd:.2f}, "
                f"{result.avg_items_per_second:.1f} items/sec"
            )

            return result

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)

            # Save error checkpoint
            if checkpoint_state and self.checkpoint_manager:
                checkpoint_state.status = "failed"
                checkpoint_state.last_error = str(e)
                self.checkpoint_manager.save_checkpoint(checkpoint_state, force=True)

            raise ProcessingError(f"Batch processing failed: {e}")

    async def _process_batch(
        self,
        batch: List[BatchItem],
        embedding_provider: Any,
        vector_store_provider: Any,
        vector_store_name: str,
        checkpoint_state: Optional[CheckpointState]
    ) -> BatchResult:
        """Process a single batch of items."""
        batch_id = self.batches_processed
        start_time = time.time()

        items_processed = 0
        items_failed = 0
        embeddings_generated = 0
        vectors_stored = 0
        cost_usd = 0.0
        errors = []

        logger.debug(f"Processing batch {batch_id}: {len(batch)} items")

        for item in batch:
            try:
                # Rate limiting
                if self.rate_limiter:
                    await self.rate_limiter.acquire(
                        ServiceType.BEDROCK,
                        model_id=embedding_provider.provider_id
                    )

                # Generate embedding
                embedding_request = EmbeddingRequest(
                    modality=item.modality,
                    content=item.content,
                    metadata=item.metadata
                )

                embedding_response = await embedding_provider.generate_embeddings(
                    embedding_request
                )

                embeddings_generated += len(embedding_response.embeddings)

                # Estimate cost (rough approximation)
                cost_usd += self._estimate_cost(item.modality, embedding_provider.provider_id)

                # Store vectors
                vectors_data = [{
                    "id": item.item_id,
                    "values": embedding_response.embeddings[0],
                    "metadata": {
                        **item.metadata,
                        "modality": item.modality.value,
                        "model_id": embedding_response.model_id
                    }
                }]

                await asyncio.to_thread(
                    vector_store_provider.upsert_vectors,
                    vector_store_name,
                    vectors_data
                )

                vectors_stored += 1
                items_processed += 1

                # Update checkpoint
                if checkpoint_state:
                    checkpoint_state.mark_processed(item.item_id)
                    checkpoint_state.embeddings_generated += len(embedding_response.embeddings)
                    checkpoint_state.vectors_stored += 1
                    checkpoint_state.total_cost_usd += cost_usd

                # Report success to rate limiter
                if self.rate_limiter:
                    self.rate_limiter.report_success(
                        ServiceType.BEDROCK,
                        model_id=embedding_provider.provider_id
                    )

            except VectorEmbeddingError as e:
                logger.error(f"Embedding failed for item {item.item_id}: {e}")
                items_failed += 1
                errors.append(f"{item.item_id}: {str(e)}")

                if checkpoint_state:
                    checkpoint_state.mark_failed(item.item_id, str(e))

                # Report throttle to rate limiter
                if self.rate_limiter and "throttl" in str(e).lower():
                    self.rate_limiter.report_throttle(
                        ServiceType.BEDROCK,
                        model_id=embedding_provider.provider_id
                    )

            except Exception as e:
                logger.error(f"Failed to process item {item.item_id}: {e}")
                items_failed += 1
                errors.append(f"{item.item_id}: {str(e)}")

                if checkpoint_state:
                    checkpoint_state.mark_failed(item.item_id, str(e))

        processing_time = time.time() - start_time

        if checkpoint_state:
            checkpoint_state.processing_time_seconds += processing_time
            checkpoint_state.current_batch_index = batch_id + 1

        return BatchResult(
            batch_id=batch_id,
            success=(items_failed == 0),
            items_processed=items_processed,
            items_failed=items_failed,
            embeddings_generated=embeddings_generated,
            vectors_stored=vectors_stored,
            processing_time_seconds=processing_time,
            cost_usd=cost_usd,
            errors=errors
        )

    def _estimate_cost(self, modality: ModalityType, provider_id: str) -> float:
        """Estimate cost per item (rough approximation)."""
        # Rough cost estimates
        if "titan" in provider_id.lower():
            if modality == ModalityType.TEXT:
                return 0.0001  # $0.0001 per 1K tokens, assume ~1K tokens avg
            elif modality == ModalityType.IMAGE:
                return 0.0008  # Titan multimodal
            elif modality == ModalityType.VIDEO:
                return 0.02  # ~$0.35/min, assume ~3 sec clips
        elif "cohere" in provider_id.lower():
            return 0.0001

        return 0.001  # Default estimate

    def _check_resource_limits(self, checkpoint_state: Optional[CheckpointState]):
        """Check if resource limits exceeded."""
        if not checkpoint_state:
            return

        # Check cost limit
        if self.config.max_cost_usd:
            if checkpoint_state.total_cost_usd >= self.config.max_cost_usd:
                raise ProcessingError(
                    f"Cost limit exceeded: ${checkpoint_state.total_cost_usd:.2f} "
                    f">= ${self.config.max_cost_usd}"
                )

        # Check time limit
        if self.config.max_processing_time_hours and self.start_time:
            elapsed_hours = (time.time() - self.start_time) / 3600
            if elapsed_hours >= self.config.max_processing_time_hours:
                raise ProcessingError(
                    f"Time limit exceeded: {elapsed_hours:.1f}h "
                    f">= {self.config.max_processing_time_hours}h"
                )

    def _log_progress(self, checkpoint_state: Optional[CheckpointState], batch_results: List[BatchResult]):
        """Log progress update."""
        if not checkpoint_state:
            return

        total_processed = len(checkpoint_state.processed_items)
        total_failed = len(checkpoint_state.failed_items)
        progress_pct = checkpoint_state.progress_percentage

        elapsed_time = time.time() - self.start_time if self.start_time else 0
        items_per_sec = total_processed / elapsed_time if elapsed_time > 0 else 0

        logger.info(
            f"Progress: {total_processed}/{checkpoint_state.total_items} "
            f"({progress_pct:.1f}%), {total_failed} failed, "
            f"{items_per_sec:.1f} items/sec, ${checkpoint_state.total_cost_usd:.2f}"
        )

    def _call_progress_callback(self, checkpoint_state: Optional[CheckpointState], batch_results: List[BatchResult]):
        """Call progress callback with current state."""
        if not self.config.progress_callback or not checkpoint_state:
            return

        progress_data = {
            "job_id": self.job_id,
            "total_items": checkpoint_state.total_items,
            "processed_items": len(checkpoint_state.processed_items),
            "failed_items": len(checkpoint_state.failed_items),
            "progress_percentage": checkpoint_state.progress_percentage,
            "total_cost_usd": checkpoint_state.total_cost_usd,
            "elapsed_time_seconds": time.time() - self.start_time if self.start_time else 0
        }

        self.config.progress_callback(progress_data)

    def _compile_final_result(
        self,
        checkpoint_state: Optional[CheckpointState],
        batch_results: List[BatchResult],
        total_time: float,
        started_at: str,
        completed_at: str
    ) -> IngestionJobResult:
        """Compile final ingestion result."""
        if checkpoint_state:
            total_items = checkpoint_state.total_items
            items_processed = len(checkpoint_state.processed_items)
            items_failed = len(checkpoint_state.failed_items)
            items_skipped = len(checkpoint_state.skipped_items)
            embeddings_generated = checkpoint_state.embeddings_generated
            vectors_stored = checkpoint_state.vectors_stored
            total_cost_usd = checkpoint_state.total_cost_usd
            error_count = checkpoint_state.error_count
        else:
            total_items = sum(br.items_processed + br.items_failed for br in batch_results)
            items_processed = sum(br.items_processed for br in batch_results)
            items_failed = sum(br.items_failed for br in batch_results)
            items_skipped = 0
            embeddings_generated = sum(br.embeddings_generated for br in batch_results)
            vectors_stored = sum(br.vectors_stored for br in batch_results)
            total_cost_usd = sum(br.cost_usd for br in batch_results)
            error_count = sum(len(br.errors) for br in batch_results)

        # Calculate performance metrics
        avg_items_per_second = items_processed / total_time if total_time > 0 else 0
        avg_cost_per_item = total_cost_usd / items_processed if items_processed > 0 else 0

        # Collect errors
        all_errors = []
        for br in batch_results:
            all_errors.extend(br.errors)

        return IngestionJobResult(
            job_id=self.job_id,
            success=(items_failed == 0),
            total_items=total_items,
            items_processed=items_processed,
            items_failed=items_failed,
            items_skipped=items_skipped,
            total_batches=len(batch_results),
            embeddings_generated=embeddings_generated,
            vectors_stored=vectors_stored,
            total_time_seconds=total_time,
            total_cost_usd=total_cost_usd,
            avg_items_per_second=avg_items_per_second,
            avg_cost_per_item=avg_cost_per_item,
            error_count=error_count,
            errors=all_errors[:100],  # Limit to first 100 errors
            started_at=started_at,
            completed_at=completed_at
        )
