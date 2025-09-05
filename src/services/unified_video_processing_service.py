#!/usr/bin/env python3
"""
Unified Video Processing Service

This service consolidates the functionality of three previous services:
- VideoEmbeddingIntegrationService (integration logic)
- VideoEmbeddingStorageService (storage operations)  
- EnhancedVideoProcessingPipeline (orchestration)

Provides a single, comprehensive interface for video processing, storage, and search.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable

from src.services.video_processing_base import (
    VideoProcessingService,
    BatchVideoProcessor,
    VideoSearchEngine,
    ProcessingResult,
    ProcessingStatus,
    VideoMetadata,
    VideoSegment,
    ProcessingConfig,
    VectorType,
    StoragePattern
)
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.aws_clients import aws_client_factory
from src.exceptions import VectorEmbeddingError, ValidationError, ProcessingError
from src.utils.logging_config import get_logger, get_structured_logger, LoggedOperation, log_function_calls

logger = get_logger(__name__)
structured_logger = get_structured_logger(__name__)


class UnifiedVideoProcessingService(VideoProcessingService, BatchVideoProcessor, VideoSearchEngine):
    """
    Unified service that consolidates video processing, storage, and search operations.
    
    This service combines the functionality of:
    - Video embedding integration (TwelveLabs processing)
    - Video embedding storage (S3Vector storage)
    - Enhanced video pipeline (orchestration and batch processing)
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize the unified video processing service."""
        structured_logger.log_function_entry("__init__", config_provided=config is not None)
        
        try:
            super().__init__(config)
            
            # Initialize core services with detailed logging
            structured_logger.log_operation("initializing_core_services", level="DEBUG")
            
            structured_logger.log_service_call("TwelveLabsVideoProcessingService", "__init__")
            self.twelvelabs_service = TwelveLabsVideoProcessingService()
            
            structured_logger.log_service_call("S3VectorStorageManager", "__init__")
            self.storage_manager = S3VectorStorageManager()
            
            structured_logger.log_service_call("BedrockEmbeddingService", "__init__")
            self.bedrock_service = BedrockEmbeddingService()
            
            structured_logger.log_aws_api_call("s3", "get_client")
            self.s3_client = aws_client_factory.get_s3_client()
            
            # Thread executor for parallel processing
            max_workers = self.config.max_concurrent_jobs
            structured_logger.log_operation(
                "initializing_thread_executor",
                level="DEBUG",
                max_workers=max_workers
            )
            self.executor = ThreadPoolExecutor(max_workers=max_workers)
            
            # Initialize TwelveLabs API service if available
            self.twelvelabs_api_service = None
            self._initialize_twelvelabs_api()
            
            structured_logger.log_operation(
                "service_initialization_complete",
                level="INFO",
                max_concurrent_jobs=max_workers,
                vector_types=len(self.config.vector_types),
                storage_patterns=len(self.config.storage_patterns)
            )
            logger.info("Unified video processing service initialized")
            
        except Exception as e:
            structured_logger.log_error("service_initialization", e)
            raise
        finally:
            structured_logger.log_function_exit("__init__")
    
    def _initialize_twelvelabs_api(self):
        """Initialize TwelveLabs API service if available."""
        structured_logger.log_function_entry("_initialize_twelvelabs_api")
        
        try:
            structured_logger.log_operation("loading_twelvelabs_dependencies", level="DEBUG")
            from src.services.twelvelabs_api_service import TwelveLabsAPIService
            from src.config.unified_config_manager import get_unified_config_manager
            
            structured_logger.log_service_call("unified_config_manager", "get_unified_config_manager")
            config_manager = get_unified_config_manager()
            marengo_config = config_manager.get_marengo_config()
            
            has_api_access = marengo_config['is_twelvelabs_api_access']
            has_api_key = bool(marengo_config.get('twelvelabs_api_key'))
            
            structured_logger.log_operation(
                "checking_twelvelabs_config",
                level="DEBUG",
                has_api_access=has_api_access,
                has_api_key=has_api_key
            )
            
            if has_api_access and has_api_key:
                structured_logger.log_service_call(
                    "TwelveLabsAPIService",
                    "__init__",
                    {"api_url": marengo_config.get('twelvelabs_api_url')}
                )
                self.twelvelabs_api_service = TwelveLabsAPIService(
                    api_key=marengo_config['twelvelabs_api_key'],
                    api_url=marengo_config['twelvelabs_api_url']
                )
                structured_logger.log_operation(
                    "twelvelabs_api_initialized",
                    level="INFO",
                    api_url=marengo_config.get('twelvelabs_api_url')
                )
                logger.info("TwelveLabs API service initialized")
            else:
                structured_logger.log_operation(
                    "twelvelabs_api_skipped",
                    level="INFO",
                    reason="api_access_not_configured"
                )
                
        except Exception as e:
            structured_logger.log_error("twelvelabs_api_initialization", e)
            logger.warning(f"TwelveLabs API service not available: {e}")
        finally:
            structured_logger.log_function_exit("_initialize_twelvelabs_api")
    
    def process_video(
        self,
        video_s3_uri: str,
        video_metadata: Optional[VideoMetadata] = None,
        config_override: Optional[ProcessingConfig] = None,
        callback: Optional[Callable[[ProcessingResult], None]] = None
    ) -> ProcessingResult:
        """
        Process a video end-to-end: embedding generation + storage.
        
        Args:
            video_s3_uri: S3 URI of video to process
            video_metadata: Optional video metadata
            config_override: Optional configuration override
            callback: Optional progress callback
            
        Returns:
            ProcessingResult with embeddings and storage information
        """
        structured_logger.log_function_entry(
            "process_video",
            video_s3_uri=video_s3_uri,
            has_metadata=video_metadata is not None,
            has_config_override=config_override is not None,
            has_callback=callback is not None
        )
        
        # Use override config if provided
        processing_config = config_override or self.config
        job_id = self.generate_job_id()
        
        structured_logger.log_video_operation(
            "process_video_start",
            video_id=job_id,
            video_s3_uri=video_s3_uri,
            processing_mode=processing_config.processing_mode,
            vector_types=len(processing_config.vector_types),
            storage_patterns=len(processing_config.storage_patterns)
        )
        
        # Initialize video metadata if not provided
        if video_metadata is None:
            structured_logger.log_operation(
                "creating_default_video_metadata",
                level="DEBUG",
                job_id=job_id
            )
            video_metadata = VideoMetadata(
                source_uri=video_s3_uri,
                duration_sec=0.0,  # Will be updated after processing
                content_id=job_id
            )
        
        # Create processing result
        structured_logger.log_operation(
            "creating_processing_result",
            level="DEBUG",
            job_id=job_id,
            status="PENDING"
        )
        result = ProcessingResult(
            job_id=job_id,
            status=ProcessingStatus.PENDING,
            video_metadata=video_metadata,
            started_at=datetime.now(timezone.utc)
        )
        
        # Track the job
        self.active_jobs[job_id] = result
        structured_logger.log_operation(
            "job_registered",
            level="DEBUG",
            job_id=job_id,
            total_active_jobs=len(self.active_jobs)
        )
        
        with LoggedOperation(structured_logger, f"video_processing_{job_id}", job_id=job_id, video_s3_uri=video_s3_uri):
            try:
                # Execute processing steps
                structured_logger.log_video_operation("status_change_processing", job_id, status="PROCESSING")
                result.status = ProcessingStatus.PROCESSING
                if callback:
                    callback(result)
                
                # Step 1: Process video with TwelveLabs for each vector type
                structured_logger.log_video_operation("status_change_marengo_processing", job_id, status="MARENGO_PROCESSING")
                result.status = ProcessingStatus.MARENGO_PROCESSING
                if callback:
                    callback(result)
                
                structured_logger.log_operation(
                    "starting_embedding_generation",
                    level="INFO",
                    job_id=job_id,
                    vector_types=[vt.value for vt in processing_config.vector_types],
                    processing_mode=processing_config.processing_mode
                )
                    
                embeddings_by_type = self._process_video_embeddings(
                    video_s3_uri, processing_config, job_id
                )
                
                # Convert to unified format
                structured_logger.log_operation(
                    "converting_embeddings_to_segments",
                    level="DEBUG",
                    job_id=job_id,
                    embedding_types=list(embeddings_by_type.keys())
                )
                result.segments = self._convert_embeddings_to_segments(
                    embeddings_by_type, video_metadata
                )
                
                # Update video duration from embeddings
                if result.segments:
                    max_duration = max(seg.end_sec for seg in result.segments)
                    video_metadata.duration_sec = max_duration
                    structured_logger.log_operation(
                        "video_duration_updated",
                        level="DEBUG",
                        job_id=job_id,
                        duration_sec=max_duration,
                        total_segments=len(result.segments)
                    )
                
                # Step 2: Store embeddings if storage patterns configured
                if processing_config.storage_patterns:
                    structured_logger.log_video_operation("status_change_storing_embeddings", job_id, status="STORING_EMBEDDINGS")
                    result.status = ProcessingStatus.STORING_EMBEDDINGS
                    if callback:
                        callback(result)
                    
                    structured_logger.log_operation(
                        "starting_embedding_storage",
                        level="INFO",
                        job_id=job_id,
                        storage_patterns=[sp.value for sp in processing_config.storage_patterns],
                        segments_to_store=len(result.segments)
                    )
                    
                    storage_results = self._store_embeddings_by_patterns(
                        result, processing_config, job_id
                    )
                    result.storage_results = storage_results
                    
                    structured_logger.log_operation(
                        "embedding_storage_completed",
                        level="INFO",
                        job_id=job_id,
                        storage_results=storage_results
                    )
                else:
                    structured_logger.log_operation(
                        "skipping_storage",
                        level="DEBUG",
                        job_id=job_id,
                        reason="no_storage_patterns_configured"
                    )
                
                # Calculate processing metrics
                result.completed_at = datetime.now(timezone.utc)
                result.processing_time_ms = int(result.processing_duration_sec * 1000)
                result.status = ProcessingStatus.COMPLETED
                
                structured_logger.log_performance(
                    f"video_processing_{job_id}",
                    result.processing_time_ms,
                    job_id=job_id,
                    segments_processed=len(result.segments),
                    video_duration_sec=video_metadata.duration_sec
                )
                
                # Calculate cost if enabled
                if processing_config.enable_cost_tracking:
                    cost = self._calculate_processing_cost(result, processing_config)
                    result.estimated_cost_usd = cost
                    structured_logger.log_cost(
                        f"video_processing_{job_id}",
                        cost,
                        len(result.segments),
                        job_id=job_id,
                        video_duration_sec=video_metadata.duration_sec
                    )
                
                structured_logger.log_video_operation(
                    "process_video_complete",
                    job_id,
                    status="COMPLETED",
                    segments_processed=len(result.segments),
                    processing_time_ms=result.processing_time_ms,
                    estimated_cost_usd=result.estimated_cost_usd
                )
                logger.info(f"Video processing completed successfully: {job_id}")
                
            except Exception as e:
                result.status = ProcessingStatus.FAILED
                result.error_message = str(e)
                result.completed_at = datetime.now(timezone.utc)
                
                processing_time_ms = 0
                if result.completed_at and result.started_at:
                    processing_time_ms = int((result.completed_at - result.started_at).total_seconds() * 1000)
                
                structured_logger.log_video_operation(
                    "process_video_failed",
                    job_id,
                    status="FAILED",
                    error_message=str(e),
                    processing_time_ms=processing_time_ms
                )
                logger.error(f"Video processing failed for job {job_id}: {e}")
                raise ProcessingError(f"Video processing failed: {e}")
            
            finally:
                if callback:
                    callback(result)
                structured_logger.log_function_exit("process_video", result=result.status)
        
        return result
    
    def _process_video_embeddings(
        self,
        video_s3_uri: str,
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[VectorType, VideoEmbeddingResult]:
        """Process video to generate embeddings for all configured vector types."""
        structured_logger.log_function_entry(
            "_process_video_embeddings",
            job_id=job_id,
            processing_mode=config.processing_mode,
            vector_types=[vt.value for vt in config.vector_types],
            segment_duration_sec=config.segment_duration_sec
        )
        
        embeddings_by_type = {}
        
        try:
            if config.processing_mode == "parallel":
                structured_logger.log_operation(
                    "starting_parallel_processing",
                    level="INFO",
                    job_id=job_id,
                    vector_type_count=len(config.vector_types),
                    max_workers=self.executor._max_workers
                )
                
                # Process all vector types in parallel
                futures = {}
                
                for vector_type in config.vector_types:
                    structured_logger.log_service_call(
                        "ThreadPoolExecutor",
                        "submit",
                        {
                            "function": "_process_single_vector_type",
                            "vector_type": vector_type.value,
                            "segment_duration_sec": config.segment_duration_sec
                        }
                    )
                    future = self.executor.submit(
                        self._process_single_vector_type,
                        video_s3_uri,
                        vector_type,
                        config.segment_duration_sec
                    )
                    futures[vector_type] = future
                
                # Collect results
                for vector_type, future in futures.items():
                    try:
                        structured_logger.log_operation(
                            "waiting_for_vector_processing",
                            level="DEBUG",
                            job_id=job_id,
                            vector_type=vector_type.value,
                            timeout_sec=config.timeout_sec
                        )
                        
                        result = future.result(timeout=config.timeout_sec)
                        embeddings_by_type[vector_type] = result
                        
                        structured_logger.log_video_operation(
                            "vector_processing_completed",
                            job_id,
                            vector_type=vector_type.value,
                            segments_generated=result.total_segments,
                            processing_time_ms=result.processing_time_ms
                        )
                        logger.info(f"Completed {vector_type.value} processing: {result.total_segments} segments")
                        
                    except Exception as e:
                        structured_logger.log_error(
                            f"parallel_vector_processing_{vector_type.value}",
                            e,
                            job_id=job_id,
                            vector_type=vector_type.value
                        )
                        logger.error(f"Failed to process {vector_type.value}: {e}")
                        raise
            
            else:  # sequential processing
                structured_logger.log_operation(
                    "starting_sequential_processing",
                    level="INFO",
                    job_id=job_id,
                    vector_type_count=len(config.vector_types)
                )
                
                for i, vector_type in enumerate(config.vector_types, 1):
                    try:
                        structured_logger.log_operation(
                            "processing_vector_type",
                            level="DEBUG",
                            job_id=job_id,
                            vector_type=vector_type.value,
                            step=f"{i}/{len(config.vector_types)}"
                        )
                        
                        result = self._process_single_vector_type(
                            video_s3_uri,
                            vector_type,
                            config.segment_duration_sec
                        )
                        embeddings_by_type[vector_type] = result
                        
                        structured_logger.log_video_operation(
                            "vector_processing_completed",
                            job_id,
                            vector_type=vector_type.value,
                            segments_generated=result.total_segments,
                            processing_time_ms=result.processing_time_ms,
                            sequential_step=f"{i}/{len(config.vector_types)}"
                        )
                        logger.info(f"Completed {vector_type.value} processing: {result.total_segments} segments")
                        
                    except Exception as e:
                        structured_logger.log_error(
                            f"sequential_vector_processing_{vector_type.value}",
                            e,
                            job_id=job_id,
                            vector_type=vector_type.value,
                            sequential_step=f"{i}/{len(config.vector_types)}"
                        )
                        logger.error(f"Failed to process {vector_type.value}: {e}")
                        raise
            
            structured_logger.log_operation(
                "video_embeddings_processing_complete",
                level="INFO",
                job_id=job_id,
                total_vector_types=len(embeddings_by_type),
                total_segments=sum(result.total_segments for result in embeddings_by_type.values())
            )
            
        except Exception as e:
            structured_logger.log_error("video_embeddings_processing", e, job_id=job_id)
            raise
        finally:
            structured_logger.log_function_exit("_process_video_embeddings", result=len(embeddings_by_type))
        
        return embeddings_by_type
    
    def _process_single_vector_type(
        self,
        video_s3_uri: str,
        vector_type: VectorType,
        segment_duration_sec: float
    ) -> VideoEmbeddingResult:
        """Process video for a single vector type."""
        return self.twelvelabs_service.process_video_sync(
            video_s3_uri=video_s3_uri,
            embedding_options=[vector_type.value],
            use_fixed_length_sec=segment_duration_sec
        )
    
    def _convert_embeddings_to_segments(
        self,
        embeddings_by_type: Dict[VectorType, VideoEmbeddingResult],
        video_metadata: VideoMetadata
    ) -> List[VideoSegment]:
        """Convert TwelveLabs results to unified segment format."""
        segments = []
        
        for vector_type, embedding_result in embeddings_by_type.items():
            for i, embedding_data in enumerate(embedding_result.embeddings):
                segment = VideoSegment(
                    start_sec=embedding_data.get("startSec", 0.0),
                    end_sec=embedding_data.get("endSec", 0.0),
                    segment_index=i,
                    vector_type=vector_type,
                    embedding=embedding_data.get("embedding", []),
                    embedding_dimension=len(embedding_data.get("embedding", [])),
                    model_id=embedding_result.model_id,
                    processing_time_ms=embedding_result.processing_time_ms
                )
                segments.append(segment)
        
        return segments
    
    def _store_embeddings_by_patterns(
        self,
        result: ProcessingResult,
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[str, Any]:
        """Store embeddings according to configured storage patterns."""
        storage_results = {}
        
        for pattern in config.storage_patterns:
            if pattern == StoragePattern.DIRECT_S3VECTOR:
                storage_results["direct_s3vector"] = self._store_direct_s3vector(result, job_id)
            elif pattern == StoragePattern.OPENSEARCH_S3VECTOR_HYBRID:
                storage_results["opensearch_hybrid"] = self._store_opensearch_hybrid(result, job_id)
            else:
                logger.warning(f"Unknown storage pattern: {pattern}")
        
        return storage_results
    
    def _store_direct_s3vector(self, result: ProcessingResult, job_id: str) -> Dict[str, Any]:
        """Store embeddings directly in S3Vector indexes."""
        storage_results = {}
        
        # Group segments by vector type
        segments_by_type = {}
        for segment in result.segments:
            if segment.vector_type not in segments_by_type:
                segments_by_type[segment.vector_type] = []
            segments_by_type[segment.vector_type].append(segment)
        
        # Store each vector type separately
        for vector_type, segments in segments_by_type.items():
            try:
                # Generate index ARN (would be configurable in production)
                index_arn = self._get_index_arn_for_vector_type(vector_type)
                
                # Prepare vectors for S3Vector storage
                vectors_data = []
                for segment in segments:
                    vector_key = f"{job_id}-{vector_type.value}-seg-{segment.segment_index:04d}"
                    vector_data = segment.to_storage_format(result.video_metadata, vector_key)
                    vectors_data.append(vector_data)
                
                # Store in batches
                stored_count = 0
                batch_size = 100
                
                for i in range(0, len(vectors_data), batch_size):
                    batch = vectors_data[i:i + batch_size]
                    batch_result = self.storage_manager.put_vectors(index_arn, batch)
                    stored_count += batch_result.get("stored_count", len(batch))
                
                storage_results[vector_type.value] = {
                    "status": "success",
                    "index_arn": index_arn,
                    "stored_count": stored_count,
                    "total_segments": len(segments)
                }
                
                logger.info(f"Stored {stored_count} vectors for {vector_type.value}")
                
            except Exception as e:
                storage_results[vector_type.value] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"Failed to store {vector_type.value} embeddings: {e}")
        
        return storage_results
    
    def _store_opensearch_hybrid(self, result: ProcessingResult, job_id: str) -> Dict[str, Any]:
        """Store embeddings in OpenSearch hybrid pattern (placeholder implementation)."""
        # This would integrate with OpenSearch service when available
        logger.info("OpenSearch hybrid storage not yet implemented, simulating...")
        
        return {
            "status": "simulated",
            "note": "OpenSearch hybrid storage pending implementation",
            "segments_count": len(result.segments)
        }
    
    def _get_index_arn_for_vector_type(self, vector_type: VectorType) -> str:
        """Get S3Vector index ARN for vector type (placeholder implementation)."""
        # In production, this would be configurable
        region = "us-east-1"
        account_id = "123456789012"  # Would get from AWS STS
        return f"arn:aws:s3vectors:{region}:{account_id}:index/video-{vector_type.value}"
    
    def _calculate_processing_cost(self, result: ProcessingResult, config: ProcessingConfig) -> float:
        """Calculate processing cost based on video duration and vector types."""
        if not result.video_metadata.duration_sec:
            return 0.0
        
        duration_minutes = result.video_metadata.duration_sec / 60.0
        cost_per_type = duration_minutes * config.cost_per_minute_usd
        total_cost = cost_per_type * len(config.vector_types)
        
        return total_cost
    
    def store_embeddings(
        self,
        processing_result: ProcessingResult,
        index_arns: Dict[VectorType, str],
        key_prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store embeddings in specified S3Vector indexes.
        
        Args:
            processing_result: Result from video processing
            index_arns: Mapping of vector types to index ARNs
            key_prefix: Optional key prefix for vectors
            
        Returns:
            Storage results by vector type
        """
        storage_results = {}
        key_prefix = key_prefix or processing_result.job_id
        
        # Group segments by vector type
        segments_by_type = {}
        for segment in processing_result.segments:
            if segment.vector_type not in segments_by_type:
                segments_by_type[segment.vector_type] = []
            segments_by_type[segment.vector_type].append(segment)
        
        # Store each vector type
        for vector_type, segments in segments_by_type.items():
            if vector_type not in index_arns:
                logger.warning(f"No index ARN provided for {vector_type.value}")
                continue
            
            try:
                index_arn = index_arns[vector_type]
                vectors_data = []
                
                for segment in segments:
                    vector_key = f"{key_prefix}-{vector_type.value}-seg-{segment.segment_index:04d}"
                    vector_data = segment.to_storage_format(processing_result.video_metadata, vector_key)
                    vectors_data.append(vector_data)
                
                # Store in batches
                stored_count = 0
                batch_size = 100
                
                for i in range(0, len(vectors_data), batch_size):
                    batch = vectors_data[i:i + batch_size]
                    result = self.storage_manager.put_vectors(index_arn, batch)
                    stored_count += result.get("stored_count", len(batch))
                
                storage_results[vector_type.value] = {
                    "status": "success",
                    "stored_count": stored_count,
                    "index_arn": index_arn
                }
                
            except Exception as e:
                storage_results[vector_type.value] = {
                    "status": "error",
                    "error": str(e)
                }
                logger.error(f"Failed to store {vector_type.value} embeddings: {e}")
        
        return storage_results
    
    def search_similar_segments(
        self,
        query: Union[str, List[float]],
        index_arn: str,
        vector_type: VectorType,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar video segments.
        
        Args:
            query: Text query or embedding vector
            index_arn: S3Vector index ARN to search
            vector_type: Type of vectors to search
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of similar segments with similarity scores
        """
        try:
            # Convert text query to vector if needed
            if isinstance(query, str):
                # Use Bedrock for text queries (cross-modal search)
                query_result = self.bedrock_service.generate_text_embedding(
                    query, "amazon.titan-embed-text-v2:0"
                )
                query_vector = query_result.embedding
            else:
                query_vector = query
            
            # Build metadata filters
            search_filter = {"content_type": "video"}
            if filters:
                # Add valid metadata fields only
                valid_fields = {
                    'start_sec', 'end_sec', 'embedding_type', 'model_id',
                    'video_duration_sec', 'content_id', 'title'
                }
                for key, value in filters.items():
                    if key in valid_fields:
                        search_filter[key] = value
            
            # Perform similarity search
            search_results = self.storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=top_k,
                metadata_filter=search_filter
            )
            
            # Process results
            segments = []
            for result in search_results.get('results', []):
                metadata = result.get('metadata', {})
                segment = {
                    "vector_key": result.get('key', ''),
                    "similarity_score": result.get('similarity_score', 0),
                    "video_source": metadata.get('video_source_uri', ''),
                    "start_sec": metadata.get('start_sec', 0),
                    "end_sec": metadata.get('end_sec', 0),
                    "duration_sec": metadata.get('end_sec', 0) - metadata.get('start_sec', 0),
                    "embedding_type": metadata.get('embedding_type', ''),
                    "segment_index": metadata.get('segment_index', 0),
                    "metadata": metadata
                }
                segments.append(segment)
            
            logger.info(f"Found {len(segments)} similar segments for query")
            return segments
            
        except Exception as e:
            logger.error(f"Video search failed: {e}")
            raise VectorEmbeddingError(f"Failed to search video segments: {e}")
    
    def multi_vector_search(
        self,
        query: str,
        index_arns: Dict[VectorType, str],
        vector_types: List[VectorType],
        top_k: int = 10,
        fusion_method: str = "rrf"
    ) -> Dict[str, Any]:
        """
        Perform multi-vector search across different embedding types.
        
        Args:
            query: Search query
            index_arns: Mapping of vector types to index ARNs
            vector_types: Vector types to search
            top_k: Number of results per vector type
            fusion_method: Method for fusing results
            
        Returns:
            Fused search results
        """
        results_by_type = {}
        
        # Search each vector type
        for vector_type in vector_types:
            if vector_type not in index_arns:
                continue
            
            try:
                results = self.search_similar_segments(
                    query=query,
                    index_arn=index_arns[vector_type],
                    vector_type=vector_type,
                    top_k=top_k
                )
                results_by_type[vector_type.value] = results
                
            except Exception as e:
                logger.error(f"Search failed for {vector_type.value}: {e}")
                results_by_type[vector_type.value] = []
        
        # Apply fusion method (simplified RRF implementation)
        if fusion_method == "rrf":
            fused_results = self._reciprocal_rank_fusion(results_by_type, top_k)
        else:
            # Simple concatenation fallback
            fused_results = []
            for vector_type, results in results_by_type.items():
                for result in results:
                    result["vector_type"] = vector_type
                    fused_results.append(result)
            
            # Sort by similarity score
            fused_results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            fused_results = fused_results[:top_k]
        
        return {
            "fused_results": fused_results,
            "results_by_type": results_by_type,
            "total_results": len(fused_results),
            "fusion_method": fusion_method
        }
    
    def _reciprocal_rank_fusion(
        self,
        results_by_type: Dict[str, List[Dict[str, Any]]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Apply reciprocal rank fusion to combine results."""
        # Collect all unique results with their ranks
        result_scores = {}
        
        for vector_type, results in results_by_type.items():
            for rank, result in enumerate(results, 1):
                key = result.get("vector_key", "")
                if key not in result_scores:
                    result_scores[key] = {
                        "result": result,
                        "rrf_score": 0.0,
                        "vector_types": []
                    }
                
                # RRF formula: 1 / (rank + k) where k=60 is common
                rrf_score = 1.0 / (rank + 60)
                result_scores[key]["rrf_score"] += rrf_score
                result_scores[key]["vector_types"].append(vector_type)
        
        # Sort by RRF score and return top-k
        sorted_results = sorted(
            result_scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True
        )
        
        fused_results = []
        for item in sorted_results[:top_k]:
            result = item["result"].copy()
            result["rrf_score"] = item["rrf_score"]
            result["matched_vector_types"] = item["vector_types"]
            fused_results.append(result)
        
        return fused_results
    
    def get_video_timeline(
        self,
        video_s3_uri: str,
        index_arn: str,
        vector_type: VectorType
    ) -> List[Dict[str, Any]]:
        """
        Get complete timeline of video segments.
        
        Args:
            video_s3_uri: S3 URI of the video
            index_arn: Index ARN to search
            vector_type: Type of vectors to retrieve
            
        Returns:
            Ordered list of video segments
        """
        try:
            # Search for all segments of this video
            metadata_filter = {
                "video_source_uri": video_s3_uri,
                "embedding_type": vector_type.value
            }
            
            # Use a large top_k to get all segments
            search_results = self.storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=[0.0] * 1024,  # Dummy vector for metadata-only search
                top_k=10000,  # Large number
                metadata_filter=metadata_filter
            )
            
            # Sort by start time
            segments = []
            for result in search_results.get('results', []):
                metadata = result.get('metadata', {})
                segments.append({
                    "start_sec": metadata.get('start_sec', 0),
                    "end_sec": metadata.get('end_sec', 0),
                    "duration_sec": metadata.get('end_sec', 0) - metadata.get('start_sec', 0),
                    "segment_index": metadata.get('segment_index', 0),
                    "vector_key": result.get('key', ''),
                    "metadata": metadata
                })
            
            # Sort by start time
            segments.sort(key=lambda x: x['start_sec'])
            
            logger.info(f"Retrieved {len(segments)} segments for video timeline")
            return segments
            
        except Exception as e:
            logger.error(f"Failed to get video timeline: {e}")
            raise VectorEmbeddingError(f"Failed to retrieve video timeline: {e}")
    
    def process_batch(
        self,
        video_list: List[Dict[str, Any]],
        config: ProcessingConfig,
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple videos in batch.
        
        Args:
            video_list: List of video info dictionaries with 's3_uri' and optional 'metadata'
            config: Processing configuration
            max_concurrent: Maximum concurrent jobs
            progress_callback: Optional progress callback
            
        Returns:
            List of processing results
        """
        results = []
        logger.info(f"Starting batch processing of {len(video_list)} videos")
        
        # Process videos (could be enhanced with proper concurrent execution)
        for i, video_info in enumerate(video_list, 1):
            video_s3_uri = video_info.get('s3_uri')
            if not video_s3_uri:
                logger.warning(f"Skipping video {i}: no s3_uri provided")
                continue
            
            try:
                # Create video metadata
                video_metadata = VideoMetadata(
                    source_uri=video_s3_uri,
                    duration_sec=0.0,
                    **video_info.get('metadata', {})
                )
                
                # Process video
                result = self.process_video(
                    video_s3_uri=video_s3_uri,
                    video_metadata=video_metadata,
                    config_override=config
                )
                
                results.append(result)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i, len(video_list))
                
                logger.info(f"Completed video {i}/{len(video_list)}: {len(result.segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to process video {i} ({video_s3_uri}): {e}")
                # Create failed result
                failed_result = ProcessingResult(
                    job_id=self.generate_job_id(),
                    status=ProcessingStatus.FAILED,
                    video_metadata=VideoMetadata(source_uri=video_s3_uri, duration_sec=0.0),
                    error_message=str(e)
                )
                results.append(failed_result)
        
        logger.info(f"Batch processing completed: {len(results)} videos processed")
        return results
    
    def upload_video_to_s3(
        self,
        video_file_path: str,
        bucket_name: Optional[str] = None,
        key_prefix: Optional[str] = None
    ) -> str:
        """
        Upload video file to S3 and return S3 URI.
        
        Args:
            video_file_path: Local path to video file
            bucket_name: S3 bucket name
            key_prefix: S3 key prefix
            
        Returns:
            S3 URI of uploaded video
        """
        if not Path(video_file_path).exists():
            raise ValidationError(f"Video file not found: {video_file_path}")
        
        # Use default bucket/prefix if not provided
        bucket_name = bucket_name or "s3vector-production-bucket"
        key_prefix = key_prefix or "videos"
        
        # Generate unique key
        timestamp = int(time.time())
        filename = Path(video_file_path).name
        s3_key = f"{key_prefix}/{timestamp}_{filename}"
        
        try:
            logger.info(f"Uploading {video_file_path} to s3://{bucket_name}/{s3_key}")
            
            with open(video_file_path, 'rb') as file_data:
                self.s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=file_data,
                    ContentType='video/mp4'
                )
            
            s3_uri = f"s3://{bucket_name}/{s3_key}"
            logger.info(f"Video uploaded successfully: {s3_uri}")
            return s3_uri
            
        except Exception as e:
            logger.error(f"Failed to upload video: {e}")
            raise ProcessingError(f"Video upload failed: {e}")
    
    def shutdown(self):
        """Shutdown the service and cleanup resources."""
        logger.info("Shutting down unified video processing service")
        self.executor.shutdown(wait=True)


# Factory function for backward compatibility
def create_unified_video_service(config: Optional[ProcessingConfig] = None) -> UnifiedVideoProcessingService:
    """Factory function to create unified video processing service."""
    return UnifiedVideoProcessingService(config)


# Example usage
if __name__ == "__main__":
    # Example configuration
    config = ProcessingConfig(
        vector_types=[VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE],
        storage_patterns=[StoragePattern.DIRECT_S3VECTOR],
        segment_duration_sec=5.0,
        processing_mode="parallel"
    )
    
    # Create service
    service = UnifiedVideoProcessingService(config)
    
    # Example processing (commented out for safety)
    # result = service.process_video("s3://bucket/video.mp4")
    # print(f"Processed {result.total_segments} segments")
    
    service.shutdown()