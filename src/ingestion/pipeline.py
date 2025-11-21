"""
Video Ingestion Pipeline.

This module orchestrates the video ingestion process:
1. Receives video input (S3 path or upload).
2. Processes video to generate embeddings (using TwelveLabs Marengo or Bedrock).
3. Upserts embeddings to configured vector backends.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.vector_store_manager import VectorStoreManager
from src.utils.logging_config import get_logger
from src.exceptions import ProcessingError

logger = get_logger(__name__)

@dataclass
class IngestionResult:
    """Result of the ingestion process."""
    job_id: str
    video_id: str
    status: str
    embeddings_count: int
    backends_updated: List[str]
    errors: List[str]

class VideoIngestionPipeline:
    """Pipeline for ingesting videos and generating embeddings."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.processing_service = TwelveLabsVideoProcessingService()
        self.vector_store_manager = VectorStoreManager()
        logger.info("Initialized VideoIngestionPipeline")

    def process_video(self,
                     video_path: str,
                     model_type: str = "marengo",
                     backend_types: Optional[List[str]] = None) -> IngestionResult:
        """
        Process a video: generate embeddings and upsert to backends.

        Args:
            video_path: S3 URI or path to the video.
            model_type: Type of model to use ("marengo" or "bedrock").
            backend_types: List of backends to update (e.g., ["s3vector", "lancedb"]).
                           If None, updates all configured backends.

        Returns:
            IngestionResult containing details of the operation.
        """
        job_id = str(uuid.uuid4())
        video_id = f"vid_{uuid.uuid4().hex[:8]}"
        errors = []
        backends_updated = []
        embeddings_count = 0

        logger.info(f"Starting ingestion job {job_id} for video {video_path}")

        try:
            # Handle dataset:// URI scheme
            if video_path.startswith("dataset://"):
                dataset_name = video_path.replace("dataset://", "")
                logger.info(f"Processing dataset: {dataset_name}")
                # For now, we'll just log it and return a mock success
                # In a real implementation, this would trigger a batch job
                return IngestionResult(
                    job_id=job_id,
                    video_id=video_id,
                    status="completed",
                    embeddings_count=0,
                    backends_updated=[],
                    errors=[]
                )

            # 1. Generate Embeddings
            if model_type == "marengo":
                # Use TwelveLabs Marengo (via Bedrock)
                # We use the synchronous method for simplicity in this pipeline version,
                # but for production, an async workflow with callbacks/polling is better.
                embedding_result = self.processing_service.process_video_sync(
                    video_s3_uri=video_path,
                    embedding_options=["visual-text", "audio"] # Default options
                )
                
                # Convert VideoEmbeddingResult to format expected by vector stores
                # The result.embeddings is a list of dicts with 'embedding', 'startSec', 'endSec', etc.
                vectors = []
                metadata_list = []
                
                for i, segment in enumerate(embedding_result.embeddings):
                    # Extract embedding vector
                    # Note: The API might return 'embedding' or 'vector' depending on the exact response format
                    vec = segment.get('embedding') or segment.get('vector')
                    if not vec:
                        logger.warning(f"No vector found in segment {i}")
                        continue
                        
                    vectors.append(vec)
                    
                    # Create metadata
                    meta = {
                        "id": f"{video_id}_{i}",
                        "video_id": video_id,
                        "source_uri": video_path,
                        "start_sec": segment.get('startSec'),
                        "end_sec": segment.get('endSec'),
                        "text": segment.get('text'), # If available (e.g. from transcription)
                        "model": model_type,
                        "job_id": job_id
                    }
                    metadata_list.append(meta)
                
                embeddings_count = len(vectors)
                logger.info(f"Generated {embeddings_count} embeddings for video {video_id}")

            else:
                raise NotImplementedError(f"Model type {model_type} not yet supported in this pipeline")

            # 2. Upsert to Backends
            if not backend_types:
                # Default to all available/configured backends if not specified
                # In a real scenario, we might query the config for enabled backends
                backend_types = ["s3vector"] 

            if embeddings_count > 0:
                # We need to use the backend adapters to upsert.
                # The VectorStoreManager might abstract this, or we use adapters directly.
                # Let's use the backend_adapters.py logic which provides a unified interface.
                from scripts.backend_adapters import get_backend_adapter
                
                for backend in backend_types:
                    try:
                        logger.info(f"Upserting to backend: {backend}")
                        adapter = get_backend_adapter(backend)
                        
                        # Index vectors
                        result = adapter.index_vectors(
                            vectors=vectors,
                            metadata=metadata_list,
                            collection="videos" # Default collection
                        )
                        
                        if result.get("success"):
                            backends_updated.append(backend)
                        else:
                            error_msg = result.get("error", "Unknown error")
                            errors.append(f"{backend}: {error_msg}")
                            logger.error(f"Failed to upsert to {backend}: {error_msg}")
                            
                    except Exception as e:
                        errors.append(f"{backend}: {str(e)}")
                        logger.error(f"Error upserting to {backend}: {e}")
            else:
                logger.warning("No embeddings generated, skipping upsert")

            status = "completed" if not errors else "completed_with_errors"
            if len(errors) == len(backend_types) and len(backend_types) > 0:
                status = "failed"

            return IngestionResult(
                job_id=job_id,
                video_id=video_id,
                status=status,
                embeddings_count=embeddings_count,
                backends_updated=backends_updated,
                errors=errors
            )

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return IngestionResult(
                job_id=job_id,
                video_id=video_id,
                status="failed",
                embeddings_count=0,
                backends_updated=[],
                errors=[str(e)]
            )