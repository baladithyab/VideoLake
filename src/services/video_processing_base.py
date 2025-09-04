#!/usr/bin/env python3
"""
Abstract Base Classes for Video Processing Operations

This module defines the common interfaces and data structures for video processing
operations, enabling unified implementation across different processing services.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Callable
from enum import Enum

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ProcessingStatus(Enum):
    """Video processing job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    MARENGO_PROCESSING = "marengo_processing"
    STORING_EMBEDDINGS = "storing_embeddings"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VectorType(Enum):
    """Supported vector types."""
    VISUAL_TEXT = "visual-text"
    VISUAL_IMAGE = "visual-image"
    AUDIO = "audio"


class StoragePattern(Enum):
    """Storage patterns for embeddings."""
    DIRECT_S3VECTOR = "direct_s3vector"
    OPENSEARCH_S3VECTOR_HYBRID = "opensearch_s3vector_hybrid"


@dataclass
class VideoMetadata:
    """Comprehensive video metadata structure."""
    # Core video information
    source_uri: str
    duration_sec: float
    content_type: str = "video"
    
    # Content classification
    title: Optional[str] = None
    description: Optional[str] = None
    content_id: Optional[str] = None
    series_id: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    
    # Categorization
    genre: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    
    # Quality metrics
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    
    # Processing metadata
    processed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        result = {
            "source_uri": self.source_uri,
            "duration_sec": self.duration_sec,
            "content_type": self.content_type,
            "processed_at": self.processed_at
        }
        
        # Add optional fields if present
        optional_fields = [
            "title", "description", "content_id", "series_id", 
            "season", "episode", "genre", "tags", "quality_score", "confidence_score"
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        
        return result


@dataclass
class VideoSegment:
    """Represents a video segment with its embedding."""
    # Temporal information
    start_sec: float
    end_sec: float
    segment_index: int
    
    # Embedding data
    vector_type: VectorType
    embedding: List[float]
    embedding_dimension: int
    
    # Processing information
    model_id: str
    processing_time_ms: Optional[int] = None
    
    @property
    def duration_sec(self) -> float:
        """Calculate segment duration."""
        return self.end_sec - self.start_sec
    
    def to_storage_format(self, video_metadata: VideoMetadata, vector_key: str) -> Dict[str, Any]:
        """Convert to S3Vector storage format."""
        metadata = {
            # Temporal information
            "start_sec": self.start_sec,
            "end_sec": self.end_sec,
            "duration_sec": self.duration_sec,
            "segment_index": self.segment_index,
            
            # Embedding information
            "embedding_type": self.vector_type.value,
            "embedding_dimension": self.embedding_dimension,
            "model_id": self.model_id,
            
            # Video information
            "video_source_uri": video_metadata.source_uri,
            "video_duration_sec": video_metadata.duration_sec,
            "content_type": video_metadata.content_type
        }
        
        # Add processing time if available
        if self.processing_time_ms is not None:
            metadata["processing_time_ms"] = self.processing_time_ms
        
        # Add video metadata fields (up to S3Vector's 10-key limit)
        video_meta_dict = video_metadata.to_dict()
        remaining_keys = 10 - len(metadata)
        
        for key, value in list(video_meta_dict.items())[:remaining_keys]:
            if key not in metadata:  # Avoid duplicates
                metadata[key] = value
        
        return {
            "key": vector_key,
            "data": {"float32": self.embedding},
            "metadata": metadata
        }


@dataclass
class ProcessingResult:
    """Result from video processing operations."""
    job_id: str
    status: ProcessingStatus
    video_metadata: VideoMetadata
    segments: List[VideoSegment] = field(default_factory=list)
    
    # Timing information
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    
    # Storage results
    storage_results: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error_message: Optional[str] = None
    
    # Cost information
    estimated_cost_usd: Optional[float] = None
    
    @property
    def total_segments(self) -> int:
        """Get total number of segments."""
        return len(self.segments)
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == ProcessingStatus.COMPLETED and not self.error_message
    
    @property
    def processing_duration_sec(self) -> float:
        """Calculate processing duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


@dataclass  
class ProcessingConfig:
    """Configuration for video processing operations."""
    # Vector types to generate
    vector_types: List[VectorType] = field(default_factory=lambda: [
        VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE, VectorType.AUDIO
    ])
    
    # Storage patterns to use
    storage_patterns: List[StoragePattern] = field(default_factory=lambda: [
        StoragePattern.DIRECT_S3VECTOR
    ])
    
    # Processing parameters
    segment_duration_sec: float = 5.0
    max_video_duration_sec: int = 3600
    processing_mode: str = "parallel"  # "parallel" or "sequential"
    
    # Performance settings
    max_concurrent_jobs: int = 8
    timeout_sec: int = 3600
    
    # Cost tracking
    enable_cost_tracking: bool = True
    cost_per_minute_usd: float = 0.05
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        if not self.vector_types:
            return False
        
        if not self.storage_patterns:
            return False
            
        if self.segment_duration_sec <= 0:
            return False
            
        if self.max_video_duration_sec <= 0:
            return False
            
        return True


class VideoProcessingService(ABC):
    """Abstract base class for video processing services."""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize the video processing service."""
        self.config = config or ProcessingConfig()
        if not self.config.validate():
            raise ValueError("Invalid processing configuration")
        
        self.active_jobs: Dict[str, ProcessingResult] = {}
        logger.info(f"Initialized {self.__class__.__name__}")
    
    @abstractmethod
    def process_video(
        self,
        video_s3_uri: str,
        video_metadata: Optional[VideoMetadata] = None,
        config_override: Optional[ProcessingConfig] = None,
        callback: Optional[Callable[[ProcessingResult], None]] = None
    ) -> ProcessingResult:
        """Process a video and generate embeddings.
        
        Args:
            video_s3_uri: S3 URI of the video to process
            video_metadata: Optional video metadata
            config_override: Optional configuration override
            callback: Optional callback for status updates
            
        Returns:
            ProcessingResult with embeddings and metadata
        """
        pass
    
    @abstractmethod
    def store_embeddings(
        self,
        processing_result: ProcessingResult,
        index_arns: Dict[VectorType, str],
        key_prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store embeddings in vector storage.
        
        Args:
            processing_result: Result from video processing
            index_arns: Mapping of vector types to index ARNs
            key_prefix: Optional key prefix for vectors
            
        Returns:
            Storage results by vector type
        """
        pass
    
    @abstractmethod
    def search_similar_segments(
        self,
        query: Union[str, List[float]],
        index_arn: str,
        vector_type: VectorType,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar video segments.
        
        Args:
            query: Text query or embedding vector
            index_arn: S3Vector index ARN to search
            vector_type: Type of vectors to search
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of similar segments with scores
        """
        pass
    
    def generate_job_id(self) -> str:
        """Generate a unique job ID."""
        return f"video-job-{uuid.uuid4().hex[:12]}"
    
    def get_job_status(self, job_id: str) -> Optional[ProcessingResult]:
        """Get status of a processing job."""
        return self.active_jobs.get(job_id)
    
    def list_active_jobs(self) -> List[ProcessingResult]:
        """List all active processing jobs."""
        return list(self.active_jobs.values())
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                job.status = ProcessingStatus.CANCELLED
                job.completed_at = datetime.now(timezone.utc)
                logger.info(f"Cancelled job {job_id}")
                return True
        return False
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up completed jobs older than specified age."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        jobs_to_remove = []
        for job_id, job in self.active_jobs.items():
            if (job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED] 
                and job.completed_at 
                and job.completed_at.timestamp() < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} completed jobs")
        
        return cleaned_count
    
    def estimate_processing_cost(
        self,
        video_duration_minutes: float,
        vector_types_count: Optional[int] = None
    ) -> Dict[str, float]:
        """Estimate processing cost for a video.
        
        Args:
            video_duration_minutes: Video duration in minutes
            vector_types_count: Number of vector types (defaults to config)
            
        Returns:
            Cost estimation breakdown
        """
        if not self.config.enable_cost_tracking:
            return {"cost_tracking_disabled": True}
        
        vector_count = vector_types_count or len(self.config.vector_types)
        cost_per_vector_type = video_duration_minutes * self.config.cost_per_minute_usd
        total_cost = cost_per_vector_type * vector_count
        
        # Estimate storage cost (rough approximation)
        segments_per_minute = 60 / self.config.segment_duration_sec
        total_segments = video_duration_minutes * segments_per_minute * vector_count
        storage_size_gb = (total_segments * 1024 * 4) / (1024 ** 3)  # 1024 dims * 4 bytes
        monthly_storage_cost = storage_size_gb * 0.023  # S3Vector pricing
        
        return {
            "video_duration_minutes": video_duration_minutes,
            "vector_types_count": vector_count,
            "processing_cost_usd": total_cost,
            "estimated_segments": int(total_segments),
            "storage_size_gb": storage_size_gb,
            "monthly_storage_cost_usd": monthly_storage_cost,
            "total_setup_cost_usd": total_cost,
            "cost_per_minute_usd": self.config.cost_per_minute_usd
        }


class BatchVideoProcessor(ABC):
    """Abstract base class for batch video processing."""
    
    @abstractmethod
    def process_batch(
        self,
        video_list: List[Dict[str, Any]],
        config: ProcessingConfig,
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """Process multiple videos in batch.
        
        Args:
            video_list: List of video info dictionaries
            config: Processing configuration
            max_concurrent: Maximum concurrent jobs
            progress_callback: Optional progress callback
            
        Returns:
            List of processing results
        """
        pass


class VideoSearchEngine(ABC):
    """Abstract base class for video search operations."""
    
    @abstractmethod
    def multi_vector_search(
        self,
        query: str,
        index_arns: Dict[VectorType, str],
        vector_types: List[VectorType],
        top_k: int = 10,
        fusion_method: str = "rrf"  # rank fusion method
    ) -> Dict[str, Any]:
        """Perform multi-vector search across different embedding types.
        
        Args:
            query: Search query
            index_arns: Mapping of vector types to index ARNs
            vector_types: Vector types to search
            top_k: Number of results per vector type
            fusion_method: Method for fusing results
            
        Returns:
            Fused search results
        """
        pass
    
    @abstractmethod
    def get_video_timeline(
        self,
        video_s3_uri: str,
        index_arn: str,
        vector_type: VectorType
    ) -> List[Dict[str, Any]]:
        """Get complete timeline of video segments.
        
        Args:
            video_s3_uri: S3 URI of the video
            index_arn: Index ARN to search
            vector_type: Type of vectors to retrieve
            
        Returns:
            Ordered list of video segments
        """
        pass