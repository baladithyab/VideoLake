"""
Unified Ingestion Service

Provides a complete pipeline for ingesting multi-modal content (text, image, audio, video)
into vector stores. Handles embedding generation, batch processing, and storage across
all supported vector store backends.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.services.embedding_provider import (
    EmbeddingProviderFactory,
    ModalityType,
    EmbeddingRequest
)
from src.services.vector_store_provider import (
    VectorStoreProviderFactory,
    VectorStoreType
)
from src.utils.logging_config import get_logger
from src.exceptions import ValidationError, VectorEmbeddingError

logger = get_logger(__name__)


@dataclass
class IngestionRequest:
    """
    Request for ingesting content into a vector store.

    Attributes:
        modality: Type of content (text, image, audio, video, multimodal)
        content: Content to ingest (can be batch)
        vector_store_type: Target vector store backend
        vector_store_name: Name of the vector store/collection/index
        embedding_provider_id: Optional specific embedding provider
        embedding_model_id: Optional specific embedding model
        dimension: Optional embedding dimension
        metadata: Additional metadata for each vector
    """
    modality: ModalityType
    content: Any
    vector_store_type: VectorStoreType
    vector_store_name: str
    embedding_provider_id: Optional[str] = None
    embedding_model_id: Optional[str] = None
    dimension: Optional[int] = None
    metadata: Dict[str, Any] = None


@dataclass
class IngestionResult:
    """
    Result from ingestion operation.

    Attributes:
        success: Whether ingestion was successful
        vectors_ingested: Number of vectors successfully stored
        vectors_failed: Number of vectors that failed
        embedding_time_ms: Time spent generating embeddings
        storage_time_ms: Time spent storing vectors
        total_time_ms: Total processing time
        errors: List of errors encountered
    """
    success: bool
    vectors_ingested: int
    vectors_failed: int
    embedding_time_ms: int
    storage_time_ms: int
    total_time_ms: int
    errors: List[str]


class UnifiedIngestionService:
    """
    Unified service for ingesting multi-modal content into vector stores.

    Provides high-level pipeline that:
    1. Auto-selects appropriate embedding provider based on modality
    2. Generates embeddings using the selected provider
    3. Stores vectors in the target vector store
    4. Handles batching, retries, and error recovery
    """

    def __init__(self):
        """Initialize the unified ingestion service."""
        self.embedding_factory = EmbeddingProviderFactory()
        self.vector_store_factory = VectorStoreProviderFactory()

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        """
        Ingest content into a vector store.

        Args:
            request: Ingestion request with content and configuration

        Returns:
            IngestionResult with statistics and errors

        Raises:
            ValidationError: If request validation fails
            VectorEmbeddingError: If embedding generation fails
        """
        import time

        start_time = time.time()
        errors = []

        try:
            # Validate request
            self._validate_request(request)

            # Step 1: Select embedding provider
            if request.embedding_provider_id:
                embedding_provider = self.embedding_factory.create_provider(
                    request.embedding_provider_id
                )
            else:
                embedding_provider = self.embedding_factory.get_provider_for_modality(
                    request.modality
                )

            if not embedding_provider:
                raise ValidationError(
                    f"No embedding provider available for modality: {request.modality.value}",
                    error_code="NO_PROVIDER_AVAILABLE"
                )

            logger.info(
                f"Selected embedding provider: {embedding_provider.provider_name} "
                f"for modality: {request.modality.value}"
            )

            # Step 2: Generate embeddings
            embedding_start = time.time()

            embedding_request = EmbeddingRequest(
                modality=request.modality,
                content=request.content,
                model_id=request.embedding_model_id,
                dimension=request.dimension,
                metadata=request.metadata or {}
            )

            embedding_response = await embedding_provider.generate_embeddings(
                embedding_request
            )

            embedding_time_ms = int((time.time() - embedding_start) * 1000)

            logger.info(
                f"Generated {len(embedding_response.embeddings)} embeddings "
                f"in {embedding_time_ms}ms"
            )

            # Step 3: Prepare vectors for storage
            vectors_data = []

            if isinstance(request.content, list):
                # Batch processing
                for i, (content_item, embedding) in enumerate(
                    zip(request.content, embedding_response.embeddings)
                ):
                    vector_id = f"vec_{i}_{int(time.time() * 1000)}"

                    vectors_data.append({
                        "id": vector_id,
                        "values": embedding,
                        "metadata": {
                            **(request.metadata or {}),
                            "modality": request.modality.value,
                            "model_id": embedding_response.model_id,
                            "dimension": embedding_response.dimension,
                            "content_index": i
                        }
                    })
            else:
                # Single item
                vector_id = f"vec_{int(time.time() * 1000)}"

                vectors_data.append({
                    "id": vector_id,
                    "values": embedding_response.embeddings[0],
                    "metadata": {
                        **(request.metadata or {}),
                        "modality": request.modality.value,
                        "model_id": embedding_response.model_id,
                        "dimension": embedding_response.dimension
                    }
                })

            # Step 4: Store vectors in vector store
            storage_start = time.time()

            vector_store_provider = self.vector_store_factory.create_provider(
                request.vector_store_type
            )

            storage_result = await asyncio.to_thread(
                vector_store_provider.upsert_vectors,
                request.vector_store_name,
                vectors_data
            )

            storage_time_ms = int((time.time() - storage_start) * 1000)

            logger.info(
                f"Stored {len(vectors_data)} vectors to {request.vector_store_name} "
                f"in {storage_time_ms}ms"
            )

            # Calculate final result
            total_time_ms = int((time.time() - start_time) * 1000)

            return IngestionResult(
                success=True,
                vectors_ingested=len(vectors_data),
                vectors_failed=0,
                embedding_time_ms=embedding_time_ms,
                storage_time_ms=storage_time_ms,
                total_time_ms=total_time_ms,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            errors.append(str(e))

            total_time_ms = int((time.time() - start_time) * 1000)

            return IngestionResult(
                success=False,
                vectors_ingested=0,
                vectors_failed=1,
                embedding_time_ms=0,
                storage_time_ms=0,
                total_time_ms=total_time_ms,
                errors=errors
            )

    async def ingest_batch(
        self,
        requests: List[IngestionRequest],
        max_concurrent: int = 5
    ) -> List[IngestionResult]:
        """
        Ingest multiple batches concurrently.

        Args:
            requests: List of ingestion requests
            max_concurrent: Maximum concurrent ingestions

        Returns:
            List of IngestionResult for each request
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def ingest_with_semaphore(request: IngestionRequest) -> IngestionResult:
            async with semaphore:
                return await self.ingest(request)

        results = await asyncio.gather(
            *[ingest_with_semaphore(req) for req in requests],
            return_exceptions=True
        )

        # Convert exceptions to failed results
        final_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch ingestion failed: {result}")
                final_results.append(
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
                final_results.append(result)

        return final_results

    def _validate_request(self, request: IngestionRequest):
        """Validate ingestion request."""
        if not request.content:
            raise ValidationError(
                "Content cannot be empty",
                error_code="EMPTY_CONTENT"
            )

        if not request.vector_store_name:
            raise ValidationError(
                "Vector store name is required",
                error_code="MISSING_VECTOR_STORE_NAME"
            )

        # Validate vector store provider is available
        if not self.vector_store_factory.is_provider_available(request.vector_store_type):
            raise ValidationError(
                f"Vector store provider not available: {request.vector_store_type.value}",
                error_code="PROVIDER_NOT_AVAILABLE"
            )

    async def get_available_pipelines(self) -> Dict[str, Any]:
        """
        Get all available ingestion pipelines.

        Returns pipeline configurations showing which modalities can be ingested
        into which vector stores using which embedding providers.

        Returns:
            Dictionary with available pipelines per modality
        """
        pipelines = {}

        for modality in ModalityType:
            # Get embedding providers for this modality
            providers = self.embedding_factory.get_all_providers_for_modality(modality)

            # Get available vector stores
            vector_stores = self.vector_store_factory.get_available_providers()

            if providers and vector_stores:
                pipelines[modality.value] = {
                    "modality": modality.value,
                    "embedding_providers": [
                        {
                            "provider_id": p.provider_id,
                            "provider_name": p.provider_name
                        }
                        for p in providers
                    ],
                    "vector_stores": [
                        {
                            "store_type": st.value,
                            "store_name": f"{st.value.replace('_', ' ').title()}"
                        }
                        for st in vector_stores
                    ]
                }

        return {
            "available_pipelines": pipelines,
            "total_modalities": len(pipelines)
        }
