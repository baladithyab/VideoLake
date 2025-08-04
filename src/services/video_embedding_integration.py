"""
Video Embedding Integration Service

This service integrates TwelveLabs video processing with S3 Vector storage,
enabling video embeddings to be stored, searched, and retrieved efficiently.
"""

import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.services.twelvelabs_video_processing import (
    TwelveLabsVideoProcessingService, 
    VideoEmbeddingResult
)
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorEmbeddingError, ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VideoSegmentVector:
    """Represents a video segment stored as a vector."""
    vector_key: str
    embedding: List[float]
    metadata: Dict[str, Any]
    segment_info: Dict[str, Any]


@dataclass
class VideoProcessingJob:
    """Represents a complete video processing and storage job."""
    job_id: str
    video_source: str
    index_arn: str
    segments_stored: int
    processing_time_ms: int
    storage_time_ms: int
    total_vectors: int
    metadata: Dict[str, Any]


class VideoEmbeddingIntegrationService:
    """Service for integrating video embeddings with S3 Vector storage."""
    
    def __init__(self, region: str = None):
        """Initialize the video embedding integration service.
        
        Args:
            region: AWS region for TwelveLabs models (defaults to us-east-1)
        """
        self.video_service = TwelveLabsVideoProcessingService(region=region)
        self.storage_manager = S3VectorStorageManager()
        
        logger.info("Video Embedding Integration Service initialized")

    def process_and_store_video(
        self,
        video_s3_uri: str,
        index_arn: str,
        video_metadata: Dict[str, Any] = None,
        embedding_options: List[str] = None,
        use_fixed_length_sec: float = None,
        vector_key_prefix: str = None
    ) -> VideoProcessingJob:
        """Process video and store embeddings in S3 Vector storage.
        
        Args:
            video_s3_uri: S3 URI of video file
            index_arn: ARN of S3 Vector index to store embeddings
            video_metadata: Additional metadata for the video
            embedding_options: Types of embeddings to generate
            use_fixed_length_sec: Fixed segment duration
            vector_key_prefix: Prefix for vector keys
            
        Returns:
            VideoProcessingJob with processing results
        """
        job_start_time = time.time()
        
        # Generate job ID
        import uuid
        job_id = f"video-job-{uuid.uuid4().hex[:12]}"
        
        logger.info(f"Starting video processing job {job_id} for {video_s3_uri}")
        
        try:
            # Step 1: Process video with TwelveLabs
            processing_start = time.time()
            video_result = self.video_service.process_video_sync(
                video_s3_uri=video_s3_uri,
                embedding_options=embedding_options or ["visual-text", "audio"],
                use_fixed_length_sec=use_fixed_length_sec or 5.0
            )
            processing_time = int((time.time() - processing_start) * 1000)
            
            logger.info(f"Video processing completed: {video_result.total_segments} segments")
            
            # Step 2: Prepare vectors for storage
            vectors_data = self._prepare_vectors_for_storage(
                video_result=video_result,
                video_s3_uri=video_s3_uri,
                video_metadata=video_metadata or {},
                vector_key_prefix=vector_key_prefix or f"video-{job_id}"
            )
            
            # Step 3: Store vectors in S3 Vectors
            storage_start = time.time()
            storage_result = self.storage_manager.put_vectors(index_arn, vectors_data)
            storage_time = int((time.time() - storage_start) * 1000)
            
            logger.info(f"Stored {len(vectors_data)} vectors in S3 Vector storage")
            
            # Create job result
            job_result = VideoProcessingJob(
                job_id=job_id,
                video_source=video_s3_uri,
                index_arn=index_arn,
                segments_stored=len(vectors_data),
                processing_time_ms=processing_time,
                storage_time_ms=storage_time,
                total_vectors=len(vectors_data),
                metadata={
                    "video_duration_sec": video_result.video_duration_sec,
                    "embedding_types": list(set(emb.get('embeddingOption') for emb in video_result.embeddings)),
                    "model_id": video_result.model_id,
                    "total_time_ms": int((time.time() - job_start_time) * 1000),
                    **video_metadata
                }
            )
            
            logger.info(f"Video processing job {job_id} completed successfully")
            return job_result
            
        except Exception as e:
            logger.error(f"Video processing job {job_id} failed: {e}")
            raise VectorEmbeddingError(f"Failed to process and store video: {e}")

    def _prepare_vectors_for_storage(
        self,
        video_result: VideoEmbeddingResult,
        video_s3_uri: str,
        video_metadata: Dict[str, Any],
        vector_key_prefix: str
    ) -> List[Dict[str, Any]]:
        """Prepare video embeddings for S3 Vector storage format.
        
        Args:
            video_result: Results from video processing
            video_s3_uri: Source video S3 URI
            video_metadata: Additional video metadata
            vector_key_prefix: Prefix for vector keys
            
        Returns:
            List of vectors in S3 Vector storage format
        """
        vectors_data = []
        
        for i, embedding_data in enumerate(video_result.embeddings):
            # Extract embedding info
            embedding = embedding_data.get('embedding', [])
            start_sec = embedding_data.get('startSec', 0)
            end_sec = embedding_data.get('endSec', 0)
            embedding_type = embedding_data.get('embeddingOption', 'unknown')
            
            # Create unique vector key
            vector_key = f"{vector_key_prefix}-segment-{i:03d}-{embedding_type}-{start_sec:.1f}s"
            
            # Prepare metadata
            segment_metadata = {
                # Temporal information
                "start_sec": start_sec,
                "end_sec": end_sec,
                "duration_sec": end_sec - start_sec,
                "segment_index": i,
                
                # Embedding information  
                "embedding_type": embedding_type,
                "embedding_dimensions": len(embedding),
                "model_id": video_result.model_id,
                
                # Video information
                "video_source": video_s3_uri,
                "video_duration_sec": video_result.video_duration_sec,
                "total_segments": video_result.total_segments,
                
                # Processing information
                "processing_time_ms": video_result.processing_time_ms,
                "created_at": str(int(time.time())),
                
                # Custom metadata
                **video_metadata
            }
            
            # Create vector data in S3 Vectors format
            vector_data = {
                "key": vector_key,
                "data": {
                    "float32": embedding
                },
                "metadata": segment_metadata
            }
            
            vectors_data.append(vector_data)
        
        return vectors_data

    def search_similar_video_segments(
        self,
        query_text: str,
        index_arn: str,
        top_k: int = 10,
        embedding_type_filter: str = None,
        duration_range: tuple = None,
        metadata_filter: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar video segments using text queries.
        
        Args:
            query_text: Text query to search for
            index_arn: ARN of S3 Vector index to search
            top_k: Number of results to return
            embedding_type_filter: Filter by embedding type (e.g., 'visual-text', 'audio')
            duration_range: Tuple of (min_duration, max_duration) in seconds
            metadata_filter: Additional metadata filters
            
        Returns:
            List of similar video segments with metadata
        """
        try:
            # Generate query embedding using Bedrock (for text-to-video search)
            from src.services.bedrock_embedding import BedrockEmbeddingService
            
            bedrock_service = BedrockEmbeddingService()
            query_result = bedrock_service.generate_text_embedding(
                query_text, 
                "amazon.titan-embed-text-v2:0"
            )
            query_vector = query_result.embedding
            
            # Build metadata filter
            search_filter = {}
            if embedding_type_filter:
                search_filter["embedding_type"] = embedding_type_filter
            
            if duration_range:
                min_dur, max_dur = duration_range
                search_filter["duration_sec"] = {">=": min_dur, "<=": max_dur}
            
            if metadata_filter:
                search_filter.update(metadata_filter)
            
            # Perform similarity search
            search_results = self.storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=top_k,
                metadata_filter=search_filter if search_filter else None
            )
            
            # Process and enhance results
            enhanced_results = []
            for result in search_results.get('results', []):
                metadata = result.get('metadata', {})
                
                enhanced_result = {
                    "vector_key": result.get('key', ''),
                    "similarity_score": result.get('similarity_score', 0),
                    "video_source": metadata.get('video_source', ''),
                    "start_sec": metadata.get('start_sec', 0),
                    "end_sec": metadata.get('end_sec', 0),
                    "duration_sec": metadata.get('duration_sec', 0),
                    "embedding_type": metadata.get('embedding_type', ''),
                    "segment_index": metadata.get('segment_index', 0),
                    "metadata": metadata
                }
                
                enhanced_results.append(enhanced_result)
            
            logger.info(f"Found {len(enhanced_results)} similar video segments for query: {query_text}")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Video search failed: {e}")
            raise VectorEmbeddingError(f"Failed to search video segments: {e}")

    def get_video_timeline(
        self,
        video_s3_uri: str,
        index_arn: str,
        embedding_type: str = "visual-text"
    ) -> List[Dict[str, Any]]:
        """Get complete timeline of video segments from storage.
        
        Args:
            video_s3_uri: S3 URI of video
            index_arn: ARN of S3 Vector index
            embedding_type: Type of embeddings to retrieve
            
        Returns:
            List of video segments ordered by time
        """
        try:
            # Search for all segments of this video
            metadata_filter = {
                "video_source": video_s3_uri,
                "embedding_type": embedding_type
            }
            
            # Get all segments (use large top_k)
            search_results = self.storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=[0.0] * 1024,  # Dummy vector - we're filtering by metadata
                top_k=1000,  # Large number to get all segments
                metadata_filter=metadata_filter
            )
            
            # Sort by start time
            segments = []
            for result in search_results.get('results', []):
                metadata = result.get('metadata', {})
                segments.append({
                    "start_sec": metadata.get('start_sec', 0),
                    "end_sec": metadata.get('end_sec', 0),
                    "duration_sec": metadata.get('duration_sec', 0),
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

    def batch_process_videos(
        self,
        video_list: List[Dict[str, Any]],
        index_arn: str,
        max_concurrent: int = 3
    ) -> List[VideoProcessingJob]:
        """Process multiple videos in batch.
        
        Args:
            video_list: List of video info dicts with 's3_uri' and optional 'metadata'
            index_arn: ARN of S3 Vector index to store embeddings
            max_concurrent: Maximum concurrent processing jobs
            
        Returns:
            List of VideoProcessingJob results
        """
        results = []
        
        logger.info(f"Starting batch processing of {len(video_list)} videos")
        
        # For now, process sequentially (could be enhanced with threading)
        for i, video_info in enumerate(video_list, 1):
            video_s3_uri = video_info.get('s3_uri')
            video_metadata = video_info.get('metadata', {})
            
            if not video_s3_uri:
                logger.warning(f"Skipping video {i}: no s3_uri provided")
                continue
            
            try:
                logger.info(f"Processing video {i}/{len(video_list)}: {video_s3_uri}")
                
                job_result = self.process_and_store_video(
                    video_s3_uri=video_s3_uri,
                    index_arn=index_arn,
                    video_metadata={
                        **video_metadata,
                        "batch_index": i,
                        "batch_total": len(video_list)
                    },
                    vector_key_prefix=f"batch-video-{i:03d}"
                )
                
                results.append(job_result)
                logger.info(f"Completed video {i}: {job_result.segments_stored} segments stored")
                
            except Exception as e:
                logger.error(f"Failed to process video {i} ({video_s3_uri}): {e}")
                # Continue with other videos
                
        logger.info(f"Batch processing completed: {len(results)}/{len(video_list)} videos processed")
        return results

    def estimate_processing_cost(
        self,
        video_duration_minutes: float,
        embedding_types: int = 2
    ) -> Dict[str, float]:
        """Estimate total cost for video processing and storage.
        
        Args:
            video_duration_minutes: Duration of video in minutes
            embedding_types: Number of embedding types to generate
            
        Returns:
            Dictionary with cost breakdown
        """
        # TwelveLabs processing cost
        processing_cost = self.video_service.estimate_cost(video_duration_minutes)
        
        # Estimate storage cost
        # Assume ~1024 dimensions per embedding, 5-second segments, 2 embedding types
        segments_per_minute = 60 / 5  # 12 segments per minute
        total_segments = video_duration_minutes * segments_per_minute * embedding_types
        
        # Each vector: 1024 dimensions * 4 bytes = 4KB + metadata ~1KB = 5KB per vector
        storage_size_gb = (total_segments * 5 * 1024) / (1024 ** 3)
        monthly_storage_cost = storage_size_gb * 0.023  # $0.023 per GB/month
        
        return {
            "video_duration_minutes": video_duration_minutes,
            "processing_cost_usd": processing_cost["estimated_cost_usd"],
            "estimated_segments": int(total_segments),
            "storage_size_gb": storage_size_gb,
            "monthly_storage_cost_usd": monthly_storage_cost,
            "total_setup_cost_usd": processing_cost["estimated_cost_usd"],
            "savings_vs_traditional_db": monthly_storage_cost * 50  # Rough 50x savings estimate
        }