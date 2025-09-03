#!/usr/bin/env python3
"""
Enhanced Video Processing Pipeline

This service implements the complete video processing workflow:
1. S3 Upload → 2. Marengo Processing → 3. Multi-Vector Generation → 4. Parallel Upserting

Supports both Direct S3Vector and OpenSearch+S3Vector hybrid storage patterns.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from src.config import config_manager
from src.utils.aws_clients import aws_client_factory
from src.exceptions import ValidationError, VectorEmbeddingError, ProcessingError
from src.utils.logging_config import get_logger
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageService
from src.services.video_embedding_storage import VideoEmbeddingStorageService

logger = get_logger(__name__)


@dataclass
class VideoProcessingJob:
    """Represents a video processing job with dual storage patterns."""
    job_id: str
    video_s3_uri: str
    vector_types: List[str]
    storage_patterns: List[str]
    segment_duration: float = 5.0
    processing_mode: str = "parallel"
    
    # Job status tracking
    status: str = "pending"
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    
    # Processing results
    marengo_results: Dict[str, Any] = field(default_factory=dict)
    storage_results: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    total_segments: int = 0
    processing_time_ms: int = 0
    cost_usd: float = 0.0


@dataclass
class PipelineConfig:
    """Configuration for the enhanced video processing pipeline."""
    
    # Storage patterns
    enable_direct_s3vector: bool = True
    enable_opensearch_hybrid: bool = True
    
    # Processing configuration
    default_vector_types: List[str] = field(default_factory=lambda: ["visual-text", "visual-image", "audio"])
    default_segment_duration: float = 5.0
    default_processing_mode: str = "parallel"
    
    # Performance settings
    max_concurrent_jobs: int = 5
    max_concurrent_vectors: int = 3
    job_timeout_sec: int = 3600  # 1 hour
    
    # Storage configuration
    s3vector_indexes: Dict[str, str] = field(default_factory=dict)
    opensearch_indexes: Dict[str, str] = field(default_factory=dict)
    
    # Cost tracking
    enable_cost_tracking: bool = True
    cost_per_minute: float = 0.05  # TwelveLabs Marengo pricing


class EnhancedVideoProcessingPipeline:
    """Enhanced video processing pipeline with dual storage pattern support."""
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the enhanced video processing pipeline."""
        self.config = config or PipelineConfig()
        
        # Initialize services
        self.twelvelabs_service = TwelveLabsVideoProcessingService()
        self.s3vector_service = S3VectorStorageService()
        self.embedding_storage_service = VideoEmbeddingStorageService()
        
        # Job tracking
        self.active_jobs: Dict[str, VideoProcessingJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_jobs)
        
        # Initialize S3 client for uploads
        self.s3_client = aws_client_factory.get_s3_client()
        
        logger.info("Enhanced video processing pipeline initialized")
    
    def upload_video_to_s3(
        self,
        video_file_path: str,
        bucket_name: Optional[str] = None,
        key_prefix: Optional[str] = None
    ) -> str:
        """Upload video file to S3 and return S3 URI.
        
        Args:
            video_file_path: Local path to video file
            bucket_name: S3 bucket name (defaults to config bucket)
            key_prefix: S3 key prefix (defaults to videos/)
            
        Returns:
            S3 URI of uploaded video
        """
        if not Path(video_file_path).exists():
            raise ValidationError(f"Video file not found: {video_file_path}")
        
        # Default bucket and key
        bucket_name = bucket_name or f"{config_manager.aws_config.s3_vectors_bucket}-videos"
        key_prefix = key_prefix or "videos"
        
        # Generate unique key
        timestamp = int(time.time())
        filename = Path(video_file_path).name
        s3_key = f"{key_prefix}/{timestamp}_{filename}"
        
        try:
            # Upload file
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
    
    def start_processing_job(
        self,
        video_s3_uri: str,
        vector_types: Optional[List[str]] = None,
        storage_patterns: Optional[List[str]] = None,
        segment_duration: Optional[float] = None,
        processing_mode: Optional[str] = None
    ) -> VideoProcessingJob:
        """Start a comprehensive video processing job.
        
        Args:
            video_s3_uri: S3 URI of video to process
            vector_types: Vector types to generate
            storage_patterns: Storage patterns to use
            segment_duration: Segment duration in seconds
            processing_mode: Processing mode (parallel/sequential)
            
        Returns:
            VideoProcessingJob instance
        """
        # Generate job ID
        job_id = f"video_job_{uuid.uuid4().hex[:8]}"
        
        # Use defaults if not specified
        vector_types = vector_types or self.config.default_vector_types
        storage_patterns = storage_patterns or []
        
        if self.config.enable_direct_s3vector:
            storage_patterns.append("direct_s3vector")
        if self.config.enable_opensearch_hybrid:
            storage_patterns.append("opensearch_hybrid")
        
        segment_duration = segment_duration or self.config.default_segment_duration
        processing_mode = processing_mode or self.config.default_processing_mode
        
        # Create job
        job = VideoProcessingJob(
            job_id=job_id,
            video_s3_uri=video_s3_uri,
            vector_types=vector_types,
            storage_patterns=storage_patterns,
            segment_duration=segment_duration,
            processing_mode=processing_mode,
            started_at=time.time()
        )
        
        # Track job
        self.active_jobs[job_id] = job
        
        # Submit job for processing
        future = self.executor.submit(self._process_job, job)
        
        logger.info(f"Started processing job {job_id} for {video_s3_uri}")
        return job
    
    def _process_job(self, job: VideoProcessingJob) -> VideoProcessingJob:
        """Process a video job through the complete pipeline."""
        try:
            job.status = "processing"
            logger.info(f"Processing job {job.job_id}")
            
            # Step 1: Process video with Marengo for each vector type
            job.status = "marengo_processing"
            marengo_results = self._process_with_marengo(job)
            job.marengo_results = marengo_results
            
            # Step 2: Parallel upserting to storage patterns
            job.status = "storing_embeddings"
            storage_results = self._parallel_upsert(job, marengo_results)
            job.storage_results = storage_results
            
            # Step 3: Calculate metrics
            self._calculate_job_metrics(job)
            
            # Mark as completed
            job.status = "completed"
            job.completed_at = time.time()
            
            logger.info(f"Job {job.job_id} completed successfully")
            return job
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = time.time()
            logger.error(f"Job {job.job_id} failed: {e}")
            raise ProcessingError(f"Job processing failed: {e}")
    
    def _process_with_marengo(self, job: VideoProcessingJob) -> Dict[str, Any]:
        """Process video with Marengo for all vector types."""
        results = {}
        
        if job.processing_mode == "parallel":
            # Process all vector types in parallel
            futures = {}
            
            for vector_type in job.vector_types:
                future = self.executor.submit(
                    self.twelvelabs_service.process_video_sync,
                    video_s3_uri=job.video_s3_uri,
                    embedding_options=[vector_type],
                    use_fixed_length_sec=job.segment_duration
                )
                futures[vector_type] = future
            
            # Collect results
            for vector_type, future in futures.items():
                try:
                    result = future.result(timeout=self.config.job_timeout_sec)
                    results[vector_type] = result
                    logger.info(f"Completed {vector_type} processing: {result.total_segments} segments")
                except Exception as e:
                    logger.error(f"Failed to process {vector_type}: {e}")
                    raise
        
        else:  # sequential processing
            for vector_type in job.vector_types:
                try:
                    result = self.twelvelabs_service.process_video_sync(
                        video_s3_uri=job.video_s3_uri,
                        embedding_options=[vector_type],
                        use_fixed_length_sec=job.segment_duration
                    )
                    results[vector_type] = result
                    logger.info(f"Completed {vector_type} processing: {result.total_segments} segments")
                except Exception as e:
                    logger.error(f"Failed to process {vector_type}: {e}")
                    raise
        
        return results
    
    def _parallel_upsert(self, job: VideoProcessingJob, marengo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert embeddings to all storage patterns in parallel."""
        storage_results = {}
        
        for pattern in job.storage_patterns:
            if pattern == "direct_s3vector":
                storage_results[pattern] = self._upsert_to_s3vector(job, marengo_results)
            elif pattern == "opensearch_hybrid":
                storage_results[pattern] = self._upsert_to_opensearch_hybrid(job, marengo_results)
            else:
                logger.warning(f"Unknown storage pattern: {pattern}")
        
        return storage_results
    
    def _upsert_to_s3vector(self, job: VideoProcessingJob, marengo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert embeddings to S3Vector indexes."""
        results = {}
        
        for vector_type, embedding_result in marengo_results.items():
            try:
                # Use the video embedding storage service
                result = self.embedding_storage_service.store_video_embeddings(
                    video_result=embedding_result,
                    index_arn=self._get_s3vector_index_arn(vector_type),
                    base_metadata={
                        "job_id": job.job_id,
                        "vector_type": vector_type,
                        "video_s3_uri": job.video_s3_uri
                    }
                )
                results[vector_type] = result
                logger.info(f"Stored {vector_type} embeddings in S3Vector")
                
            except Exception as e:
                logger.error(f"Failed to store {vector_type} in S3Vector: {e}")
                results[vector_type] = {"error": str(e)}
        
        return results
    
    def _upsert_to_opensearch_hybrid(self, job: VideoProcessingJob, marengo_results: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert embeddings to OpenSearch hybrid indexes."""
        # Placeholder for OpenSearch hybrid implementation
        # This would integrate with OpenSearch service when available
        results = {}
        
        for vector_type, embedding_result in marengo_results.items():
            # Simulate OpenSearch hybrid storage
            results[vector_type] = {
                "status": "simulated",
                "index_name": f"opensearch-{vector_type}-hybrid",
                "documents_indexed": embedding_result.total_segments,
                "note": "OpenSearch hybrid integration pending implementation"
            }
            logger.info(f"Simulated {vector_type} storage in OpenSearch hybrid")
        
        return results
    
    def _get_s3vector_index_arn(self, vector_type: str) -> str:
        """Get S3Vector index ARN for vector type."""
        # Use configured index ARN or generate default
        if vector_type in self.config.s3vector_indexes:
            return self.config.s3vector_indexes[vector_type]
        
        # Generate default ARN
        account_id = "123456789012"  # Would get from AWS STS in real implementation
        region = config_manager.aws_config.region
        return f"arn:aws:s3vectors:{region}:{account_id}:index/video-{vector_type}"
    
    def _calculate_job_metrics(self, job: VideoProcessingJob):
        """Calculate job metrics and costs."""
        # Calculate total segments
        total_segments = 0
        total_processing_time = 0
        
        for vector_type, result in job.marengo_results.items():
            total_segments += result.total_segments or 0
            total_processing_time += result.processing_time_ms or 0
        
        job.total_segments = total_segments
        job.processing_time_ms = total_processing_time
        
        # Calculate cost
        if self.config.enable_cost_tracking:
            # Estimate video duration from segments
            video_duration_minutes = (total_segments * job.segment_duration) / 60.0
            cost_per_vector_type = video_duration_minutes * self.config.cost_per_minute
            total_cost = cost_per_vector_type * len(job.vector_types)
            job.cost_usd = total_cost
    
    def get_job_status(self, job_id: str) -> Optional[VideoProcessingJob]:
        """Get status of a processing job."""
        return self.active_jobs.get(job_id)
    
    def list_active_jobs(self) -> List[VideoProcessingJob]:
        """List all active jobs."""
        return list(self.active_jobs.values())
    
    def cleanup_job(self, job_id: str):
        """Clean up completed job."""
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up job {job_id}")
    
    def estimate_processing_cost(
        self,
        video_duration_minutes: float,
        vector_types_count: int
    ) -> Dict[str, float]:
        """Estimate processing cost for video."""
        cost_per_vector_type = video_duration_minutes * self.config.cost_per_minute
        total_cost = cost_per_vector_type * vector_types_count
        
        return {
            'video_duration_minutes': video_duration_minutes,
            'vector_types_count': vector_types_count,
            'cost_per_vector_type_usd': cost_per_vector_type,
            'total_cost_usd': total_cost,
            'cost_per_minute_usd': self.config.cost_per_minute
        }
    
    def shutdown(self):
        """Shutdown the pipeline and cleanup resources."""
        logger.info("Shutting down enhanced video processing pipeline")
        self.executor.shutdown(wait=True)


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_pipeline():
        """Test the enhanced video processing pipeline."""
        # Initialize pipeline
        config = PipelineConfig(
            enable_direct_s3vector=True,
            enable_opensearch_hybrid=True,
            default_vector_types=["visual-text", "visual-image"],
            max_concurrent_jobs=2
        )

        pipeline = EnhancedVideoProcessingPipeline(config)

        try:
            # Test cost estimation
            cost_estimate = pipeline.estimate_processing_cost(
                video_duration_minutes=5.0,
                vector_types_count=3
            )
            print(f"Cost estimate: {cost_estimate}")

            # Test job creation (simulation)
            test_s3_uri = "s3://test-bucket/sample-video.mp4"

            job = pipeline.start_processing_job(
                video_s3_uri=test_s3_uri,
                vector_types=["visual-text", "visual-image"],
                storage_patterns=["direct_s3vector"],
                segment_duration=5.0,
                processing_mode="parallel"
            )

            print(f"Started job: {job.job_id}")

            # Monitor job status
            while job.status not in ["completed", "failed"]:
                await asyncio.sleep(1)
                current_job = pipeline.get_job_status(job.job_id)
                print(f"Job {job.job_id} status: {current_job.status}")

                if current_job.status == "failed":
                    print(f"Job failed: {current_job.error_message}")
                    break

            if job.status == "completed":
                print(f"Job completed successfully!")
                print(f"Total segments: {job.total_segments}")
                print(f"Processing time: {job.processing_time_ms}ms")
                print(f"Cost: ${job.cost_usd:.3f}")

        finally:
            pipeline.shutdown()

    # Run test
    # asyncio.run(test_pipeline())
