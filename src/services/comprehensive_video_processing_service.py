#!/usr/bin/env python3
"""
Comprehensive Video Processing Service

This service orchestrates the complete video processing workflow:
1. Download videos from URLs using S3BucketUtilityService
2. Process videos with Bedrock Marengo 2.7 (primary) or TwelveLabs API (secondary)
3. Store embeddings in S3Vector indexes using EmbeddingStorageIntegration
4. Support multiple vector types and storage patterns

Prioritizes Bedrock Marengo 2.7 for cost efficiency and AWS integration.
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from src.services.s3_bucket_utils import S3BucketUtilityService
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.twelvelabs_api_service import TwelveLabsAPIService
from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.s3_vector_storage import S3VectorStorageManager
from src.config.unified_config_manager import get_unified_config_manager
from src.exceptions import ValidationError, VectorEmbeddingError, ProcessingError
from src.utils.logging_config import get_logger
from src.utils.aws_clients import aws_client_factory
from src.utils.resource_registry import resource_registry

logger = get_logger(__name__)


class ProcessingMode(Enum):
    """Video processing mode configuration."""
    BEDROCK_PRIMARY = "bedrock_primary"  # Use Bedrock Marengo 2.7 as primary
    TWELVELABS_PRIMARY = "twelvelabs_primary"  # Use TwelveLabs API as primary
    BEDROCK_ONLY = "bedrock_only"  # Only use Bedrock
    TWELVELABS_ONLY = "twelvelabs_only"  # Only use TwelveLabs API


class VectorType(Enum):
    """Supported vector types for Marengo 2.7."""
    VISUAL_TEXT = "visual-text"
    VISUAL_IMAGE = "visual-image"
    AUDIO = "audio"


class StoragePattern(Enum):
    """Storage patterns for embeddings."""
    DIRECT_S3VECTOR = "direct_s3vector"
    OPENSEARCH_S3VECTOR_HYBRID = "opensearch_s3vector_hybrid"


@dataclass
class ProcessingConfig:
    """Configuration for comprehensive video processing."""
    # Processing mode
    processing_mode: ProcessingMode = ProcessingMode.BEDROCK_PRIMARY
    
    # Vector types to generate
    vector_types: List[VectorType] = field(default_factory=lambda: [
        VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE, VectorType.AUDIO
    ])
    
    # Storage patterns
    storage_patterns: List[StoragePattern] = field(default_factory=lambda: [
        StoragePattern.DIRECT_S3VECTOR
    ])
    
    # Marengo 2.7 specific settings
    segment_duration_sec: float = 5.0  # Fixed segment duration (2-10 seconds)
    min_clip_sec: int = 4  # Minimum clip duration
    max_video_duration_sec: int = 7200  # 2 hours max
    
    # Processing settings
    max_concurrent_jobs: int = 5
    timeout_sec: int = 3600
    enable_cost_tracking: bool = True
    
    # S3 settings
    video_bucket_suffix: str = "-videos"  # Suffix for video storage bucket
    embedding_bucket_suffix: str = "-embeddings"  # Suffix for embedding results
    
    # TwelveLabs API fallback settings
    twelvelabs_api_key: Optional[str] = None
    enable_twelvelabs_fallback: bool = True


@dataclass
class VideoProcessingResult:
    """Result from comprehensive video processing."""
    job_id: str
    status: str
    source_url: str
    s3_uri: str
    
    # Processing results
    embeddings_by_type: Dict[str, Any] = field(default_factory=dict)
    storage_results: Dict[str, Any] = field(default_factory=dict)
    
    # Timing information
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    
    # Cost information
    estimated_cost_usd: Optional[float] = None
    
    # Error information
    error_message: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful."""
        return self.status == "completed" and not self.error_message
    
    @property
    def total_segments(self) -> int:
        """Get total number of segments across all vector types."""
        total = 0
        for vector_type, result in self.embeddings_by_type.items():
            if isinstance(result, dict) and 'total_segments' in result:
                total += result['total_segments']
        return total


class ComprehensiveVideoProcessingService:
    """
    Comprehensive service for end-to-end video processing workflow.
    
    This service integrates:
    - Video download from URLs
    - Bedrock Marengo 2.7 processing (primary)
    - TwelveLabs API processing (secondary/fallback)
    - S3Vector storage integration
    - Multi-vector type support
    - Cost optimization
    """
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize the comprehensive video processing service."""
        self.config = config or ProcessingConfig()
        
        # Initialize core services
        self.s3_utils = S3BucketUtilityService()
        self.bedrock_service = TwelveLabsVideoProcessingService()
        self.storage_integration = EmbeddingStorageIntegration()
        self.storage_manager = S3VectorStorageManager()
        
        # Initialize resource registry for S3Vector bucket management
        self.resource_registry = resource_registry
        
        # Initialize TwelveLabs API service if configured
        self.twelvelabs_api = None
        self._initialize_twelvelabs_api()
        
        # Get configuration
        config_manager = get_unified_config_manager()
        self.aws_config = config_manager.config.aws
        
        # Active jobs tracking
        self.active_jobs: Dict[str, VideoProcessingResult] = {}
        
        logger.info(f"Initialized ComprehensiveVideoProcessingService with mode: {self.config.processing_mode.value}")
    
    def _initialize_twelvelabs_api(self):
        """Initialize TwelveLabs API service if available."""
        try:
            config_manager = get_unified_config_manager()
            marengo_config = config_manager.get_marengo_config()
            
            if (marengo_config.get('is_twelvelabs_api_access') and 
                marengo_config.get('twelvelabs_api_key')):
                
                self.twelvelabs_api = TwelveLabsAPIService(
                    api_key=marengo_config['twelvelabs_api_key'],
                    api_url=marengo_config.get('twelvelabs_api_url', 'https://api.twelvelabs.io')
                )
                logger.info("TwelveLabs API service initialized")
            else:
                logger.info("TwelveLabs API not configured, using Bedrock only")
                
        except Exception as e:
            logger.warning(f"Failed to initialize TwelveLabs API: {e}")
    
    def _get_optimal_s3_bucket_for_videos(self, job_id: str) -> str:
        """
        Get the optimal S3 bucket for video storage and Bedrock Marengo results.
        
        Prioritizes existing S3 buckets from resource management over creating new ones.
        
        Args:
            job_id: Current processing job ID for logging
            
        Returns:
            str: S3 bucket name to use for video storage
        """
        logger.info(f"[{job_id}] Determining optimal S3 bucket for video storage")
        
        try:
            # Priority 1: Use active S3 bucket from resource registry
            active_s3_bucket = self.resource_registry.get_active_resources().get('s3_bucket')
            if active_s3_bucket:
                logger.info(f"[{job_id}] Using active S3 bucket from resource registry: {active_s3_bucket}")
                return active_s3_bucket
            
            # Priority 2: Use any available S3 bucket from resource registry
            s3_buckets = self.resource_registry.list_s3_buckets()
            available_s3_buckets = [
                bucket for bucket in s3_buckets
                if bucket and bucket.get('status') == 'created' and bucket.get('name')
            ]
            
            if available_s3_buckets:
                # Use the most recently created S3 bucket
                latest_s3_bucket = max(available_s3_buckets, key=lambda b: b.get('created_at', ''))
                bucket_name = latest_s3_bucket['name']
                logger.info(f"[{job_id}] Using latest S3 bucket from resource registry: {bucket_name}")
                
                # Set as active for future use
                self.resource_registry.set_active_s3_bucket(bucket_name)
                return bucket_name
            
            # Priority 3: Fall back to configuration-based bucket selection
            logger.info(f"[{job_id}] No existing S3 buckets found in resource registry, using configuration fallback")
            base_bucket = self.aws_config.s3_bucket or "s3vector-default"
            fallback_bucket = f"{base_bucket}{self.config.video_bucket_suffix}"
            
            logger.info(f"[{job_id}] Using configuration-based S3 bucket: {fallback_bucket}")
            return fallback_bucket
            
        except Exception as e:
            logger.error(f"[{job_id}] Error determining optimal S3 bucket: {e}")
            # Ultimate fallback
            fallback_bucket = f"s3-fallback-{job_id}"
            logger.warning(f"[{job_id}] Using emergency fallback S3 bucket: {fallback_bucket}")
            return fallback_bucket
    
    def _get_optimal_s3vector_resources_for_embeddings(self, job_id: str, storage_patterns: List[StoragePattern]) -> Dict[str, Any]:
        """
        Get optimal S3Vector resources for embedding storage based on storage patterns.
        
        Args:
            job_id: Current processing job ID for logging
            storage_patterns: List of storage patterns to support
            
        Returns:
            Dict containing optimal resources for each storage pattern
        """
        logger.info(f"[{job_id}] Determining optimal S3Vector resources for embedding storage")
        resources = {}
        
        try:
            for pattern in storage_patterns:
                if pattern == StoragePattern.DIRECT_S3VECTOR:
                    # For direct S3Vector pattern, we need S3Vector bucket and indexes
                    vector_bucket = self._get_optimal_s3vector_bucket_for_direct_storage(job_id)
                    resources['direct_s3vector'] = {
                        'vector_bucket': vector_bucket,
                        'pattern': 'direct_s3vector'
                    }
                    
                elif pattern == StoragePattern.OPENSEARCH_S3VECTOR_HYBRID:
                    # For hybrid pattern, we need OpenSearch domain with S3Vector backend
                    opensearch_resources = self._get_optimal_opensearch_resources(job_id)
                    resources['opensearch_s3vector_hybrid'] = {
                        'opensearch_domain': opensearch_resources.get('domain'),
                        'opensearch_collection': opensearch_resources.get('collection'),
                        's3vector_bucket': opensearch_resources.get('s3vector_bucket'),
                        'pattern': 'opensearch_s3vector_hybrid'
                    }
            
            logger.info(f"[{job_id}] Selected resources for {len(resources)} storage patterns")
            return resources
            
        except Exception as e:
            logger.error(f"[{job_id}] Error determining optimal S3Vector resources: {e}")
            return {}
    
    def _get_optimal_s3vector_bucket_for_direct_storage(self, job_id: str) -> str:
        """Get optimal S3Vector bucket for direct vector storage."""
        try:
            # Priority 1: Use active S3Vector bucket from resource registry
            active_vector_bucket = self.resource_registry.get_active_resources().get('vector_bucket')
            if active_vector_bucket:
                logger.info(f"[{job_id}] Using active S3Vector bucket: {active_vector_bucket}")
                return active_vector_bucket
            
            # Priority 2: Use any available S3Vector bucket from resource registry
            vector_buckets = self.resource_registry.list_vector_buckets()
            available_buckets = [
                bucket for bucket in vector_buckets
                if bucket and bucket.get('status') == 'created' and bucket.get('name')
            ]
            
            if available_buckets:
                latest_bucket = max(available_buckets, key=lambda b: b.get('created_at', ''))
                bucket_name = latest_bucket['name']
                logger.info(f"[{job_id}] Using latest S3Vector bucket: {bucket_name}")
                self.resource_registry.set_active_vector_bucket(bucket_name)
                return bucket_name
            
            # Priority 3: Configuration fallback
            base_bucket = self.aws_config.s3_vectors_bucket or "s3vector-default"
            fallback_bucket = f"{base_bucket}-vectors"
            logger.info(f"[{job_id}] Using configuration-based S3Vector bucket: {fallback_bucket}")
            return fallback_bucket
            
        except Exception as e:
            logger.error(f"[{job_id}] Error getting S3Vector bucket: {e}")
            return f"s3vector-fallback-{job_id}"
    
    def _get_optimal_opensearch_resources(self, job_id: str) -> Dict[str, str]:
        """Get optimal OpenSearch resources for hybrid storage."""
        try:
            resources = {}
            
            # Check for active OpenSearch domain
            active_domain = self.resource_registry.get_active_resources().get('opensearch_domain')
            if active_domain:
                resources['domain'] = active_domain
                logger.info(f"[{job_id}] Using active OpenSearch domain: {active_domain}")
            
            # Check for active OpenSearch collection
            active_collection = self.resource_registry.get_active_resources().get('opensearch_collection')
            if active_collection:
                resources['collection'] = active_collection
                logger.info(f"[{job_id}] Using active OpenSearch collection: {active_collection}")
            
            # Get associated S3Vector bucket for OpenSearch backend
            if not resources.get('domain') and not resources.get('collection'):
                # Look for any available OpenSearch resources
                domains = self.resource_registry.list_opensearch_domains()
                collections = self.resource_registry.list_opensearch_collections()
                
                if domains:
                    latest_domain = max(domains, key=lambda d: d.get('created_at', ''))
                    resources['domain'] = latest_domain['name']
                    logger.info(f"[{job_id}] Using latest OpenSearch domain: {latest_domain['name']}")
                
                if collections:
                    latest_collection = max(collections, key=lambda c: c.get('created_at', ''))
                    resources['collection'] = latest_collection['name']
                    logger.info(f"[{job_id}] Using latest OpenSearch collection: {latest_collection['name']}")
            
            # Get S3Vector bucket for OpenSearch backend
            resources['s3vector_bucket'] = self._get_optimal_s3vector_bucket_for_direct_storage(job_id)
            
            return resources
            
        except Exception as e:
            logger.error(f"[{job_id}] Error getting OpenSearch resources: {e}")
            return {}
    
    def process_video_from_url(
        self,
        video_url: str,
        target_indexes: Optional[Dict[VectorType, str]] = None,
        config_override: Optional[ProcessingConfig] = None,
        progress_callback: Optional[Callable[[VideoProcessingResult], None]] = None
    ) -> VideoProcessingResult:
        """
        Process a video from URL through the complete workflow.
        
        Args:
            video_url: HTTP/HTTPS URL of video to process
            target_indexes: Mapping of vector types to S3Vector index ARNs
            config_override: Optional configuration override
            progress_callback: Optional progress callback
            
        Returns:
            VideoProcessingResult with complete processing information
        """
        config = config_override or self.config
        job_id = f"video-job-{uuid.uuid4().hex[:12]}"
        
        logger.info(f"Starting comprehensive video processing: {job_id} for {video_url}")
        
        # Create processing result
        result = VideoProcessingResult(
            job_id=job_id,
            status="pending",
            source_url=video_url,
            s3_uri="",
            started_at=datetime.now(timezone.utc)
        )
        
        # Track active job
        self.active_jobs[job_id] = result
        
        try:
            # Step 1: Download video to S3
            result.status = "downloading"
            if progress_callback:
                progress_callback(result)
            
            # Use optimal S3Vector bucket from resource management system
            optimal_s3_bucket = self._get_optimal_s3_bucket_for_videos(job_id)
            video_bucket_name = optimal_s3_bucket
            
            download_result = self._download_video_to_s3(video_url, video_bucket_name, job_id)
            result.s3_uri = download_result["s3_uri"]
            
            logger.info(f"[{job_id}] Video downloaded to S3 using optimal bucket: {result.s3_uri}")
            
            # Step 2: Process video with embeddings
            result.status = "processing_embeddings"
            if progress_callback:
                progress_callback(result)
            
            embeddings_results = self._process_video_embeddings(
                result.s3_uri, config, job_id
            )
            result.embeddings_by_type = embeddings_results
            
            # Step 3: Store embeddings in S3Vector indexes
            if target_indexes and config.storage_patterns:
                result.status = "storing_embeddings"
                if progress_callback:
                    progress_callback(result)
                
                storage_results = self._store_embeddings_in_indexes(
                    embeddings_results, target_indexes, config, job_id
                )
                result.storage_results = storage_results
            
            # Calculate final metrics
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at:
                result.processing_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            result.status = "completed"
            
            # Calculate cost if enabled
            if config.enable_cost_tracking:
                result.estimated_cost_usd = self._calculate_processing_cost(result, config)
            
            logger.info(f"Video processing completed: {job_id}, {result.total_segments} segments, {result.processing_time_ms}ms")
            
            return result
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
            
            if result.started_at and result.completed_at:
                result.processing_time_ms = int(
                    (result.completed_at - result.started_at).total_seconds() * 1000
                )
            
            logger.error(f"Video processing failed: {job_id}, {e}")
            raise ProcessingError(f"Video processing failed: {e}")
        
        finally:
            if progress_callback:
                progress_callback(result)
    
    def _download_video_to_s3(self, video_url: str, bucket: str, job_id: str) -> Dict[str, Any]:
        """Download video from URL to existing S3 bucket (bucket must already exist)."""
        logger.info(f"[{job_id}] Downloading video to existing S3 bucket: {bucket}")
        
        # Verify bucket exists - do not create it
        if not self.s3_utils.bucket_exists(bucket):
            raise ProcessingError(
                f"S3 bucket '{bucket}' does not exist. "
                f"Please create the bucket through the Resource Management page first."
            )
        
        logger.info(f"[{job_id}] Confirmed S3 bucket exists: {bucket}")
        
        # Download video directly to the existing bucket
        key_prefix = f"videos/{job_id}/"
        download_result = self.s3_utils.download_video_from_url(
            video_url=video_url,
            target_bucket=bucket,
            key_prefix=key_prefix
        )
        
        logger.info(f"[{job_id}] Video download completed to: {download_result.get('s3_uri', 'unknown')}")
        return download_result
    
    def _process_video_embeddings(
        self,
        video_s3_uri: str,
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[str, Any]:
        """Process video to generate embeddings using configured method."""
        embeddings_results = {}
        
        # Determine processing method based on config
        if config.processing_mode in [ProcessingMode.BEDROCK_PRIMARY, ProcessingMode.BEDROCK_ONLY]:
            # Use Bedrock Marengo 2.7 as primary
            try:
                embeddings_results = self._process_with_bedrock_marengo(
                    video_s3_uri, config, job_id
                )
                logger.info(f"Successfully processed with Bedrock Marengo 2.7: {job_id}")
                
            except Exception as e:
                logger.error(f"Bedrock processing failed: {e}")
                
                # Fallback to TwelveLabs API if enabled and available
                if (config.processing_mode == ProcessingMode.BEDROCK_PRIMARY and 
                    config.enable_twelvelabs_fallback and self.twelvelabs_api):
                    
                    logger.info(f"Falling back to TwelveLabs API: {job_id}")
                    embeddings_results = self._process_with_twelvelabs_api(
                        video_s3_uri, config, job_id
                    )
                else:
                    raise
        
        elif config.processing_mode in [ProcessingMode.TWELVELABS_PRIMARY, ProcessingMode.TWELVELABS_ONLY]:
            # Use TwelveLabs API as primary
            if not self.twelvelabs_api:
                raise ProcessingError("TwelveLabs API not configured")
            
            try:
                embeddings_results = self._process_with_twelvelabs_api(
                    video_s3_uri, config, job_id
                )
                logger.info(f"Successfully processed with TwelveLabs API: {job_id}")
                
            except Exception as e:
                logger.error(f"TwelveLabs API processing failed: {e}")
                
                # Fallback to Bedrock if enabled
                if config.processing_mode == ProcessingMode.TWELVELABS_PRIMARY:
                    logger.info(f"Falling back to Bedrock Marengo 2.7: {job_id}")
                    embeddings_results = self._process_with_bedrock_marengo(
                        video_s3_uri, config, job_id
                    )
                else:
                    raise
        
        return embeddings_results
    
    def _process_with_bedrock_marengo(
        self,
        video_s3_uri: str,
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[str, Any]:
        """Process video using Bedrock Marengo 2.7 with optimized single-job approach."""
        embeddings_results = {}
        
        # Extract vector type values for the single job
        vector_type_values = [vector_type.value for vector_type in config.vector_types]
        
        logger.info(f"Processing video with multiple embeddings in single Bedrock job: {vector_type_values}")
        
        try:
            # Use the optimized single-job method that processes all embedding types at once
            embeddings_by_type = self.bedrock_service.process_video_with_multiple_embeddings(
                video_s3_uri=video_s3_uri,
                embedding_options=vector_type_values,
                use_fixed_length_sec=config.segment_duration_sec
            )
            
            # Process results for each vector type
            for vector_type in config.vector_types:
                vector_type_value = vector_type.value
                
                if vector_type_value in embeddings_by_type:
                    embeddings = embeddings_by_type[vector_type_value]
                    
                    # Create a VideoEmbeddingResult-like structure for compatibility
                    embeddings_results[vector_type_value] = {
                        'embeddings': embeddings,
                        'total_segments': len(embeddings),
                        'processing_time_ms': 0,  # Will be calculated from the overall job
                        'model_id': self.bedrock_service.model_id,
                        'method': 'bedrock_marengo_2_7_optimized'
                    }
                    
                    logger.info(f"Bedrock processing completed for {vector_type_value}: {len(embeddings)} segments")
                else:
                    logger.warning(f"No embeddings returned for {vector_type_value}")
                    embeddings_results[vector_type_value] = {
                        'embeddings': [],
                        'total_segments': 0,
                        'processing_time_ms': 0,
                        'model_id': self.bedrock_service.model_id,
                        'method': 'bedrock_marengo_2_7_optimized'
                    }
            
            logger.info(f"✅ OPTIMIZED: Processed {len(vector_type_values)} embedding types in single Bedrock job")
            
        except Exception as e:
            logger.error(f"Failed to process video with Bedrock (single job): {e}")
            
            # Fallback to individual jobs if the optimized approach fails
            logger.info("Falling back to individual jobs per embedding type")
            
            for vector_type in config.vector_types:
                logger.info(f"Processing {vector_type.value} with Bedrock Marengo 2.7 (fallback)")
                
                try:
                    # Use individual job approach as fallback
                    result = self.bedrock_service.process_video_sync(
                        video_s3_uri=video_s3_uri,
                        embedding_options=[vector_type.value],
                        use_fixed_length_sec=config.segment_duration_sec
                    )
                    
                    embeddings_results[vector_type.value] = {
                        'embedding_result': result,
                        'total_segments': result.total_segments,
                        'processing_time_ms': result.processing_time_ms,
                        'model_id': result.model_id,
                        'method': 'bedrock_marengo_2_7_fallback'
                    }
                    
                    logger.info(f"Bedrock fallback processing completed for {vector_type.value}: {result.total_segments} segments")
                    
                except Exception as fallback_error:
                    logger.error(f"Failed to process {vector_type.value} with Bedrock (fallback): {fallback_error}")
                    embeddings_results[vector_type.value] = {
                        'error': str(fallback_error),
                        'method': 'bedrock_marengo_2_7_fallback'
                    }
        
        return embeddings_results
    
    def _process_with_twelvelabs_api(
        self,
        video_s3_uri: str,
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[str, Any]:
        """Process video using TwelveLabs API."""
        embeddings_results = {}
        
        if not self.twelvelabs_api:
            raise ProcessingError("TwelveLabs API service not initialized")
        
        # Convert S3 URI to public URL for TwelveLabs API
        # Note: This would require presigned URLs or public access
        # For now, we'll use the direct API approach
        
        for vector_type in config.vector_types:
            logger.info(f"Processing {vector_type.value} with TwelveLabs API")
            
            try:
                # Create embedding task
                task = self.twelvelabs_api.create_video_embedding_task(
                    model_name="Marengo-retrieval-2.7",
                    video_url=video_s3_uri,  # This would need to be a public URL
                    video_clip_length=config.segment_duration_sec,
                    video_embedding_scope=["clip"]
                )
                
                # Wait for completion
                completed_task = self.twelvelabs_api.wait_for_task_completion(task.task_id)
                
                # Retrieve embeddings
                result = self.twelvelabs_api.retrieve_video_embeddings(
                    task.task_id,
                    embedding_options=[vector_type.value]
                )
                
                embeddings_results[vector_type.value] = {
                    'embedding_result': result,
                    'total_segments': len(result.segments),
                    'task_id': task.task_id,
                    'model_name': result.model_name,
                    'method': 'twelvelabs_api'
                }
                
                logger.info(f"TwelveLabs API processing completed for {vector_type.value}: {len(result.segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to process {vector_type.value} with TwelveLabs API: {e}")
                embeddings_results[vector_type.value] = {
                    'error': str(e),
                    'method': 'twelvelabs_api'
                }
        
        return embeddings_results
    
    def _store_embeddings_in_indexes(
        self,
        embeddings_results: Dict[str, Any],
        target_indexes: Dict[VectorType, str],
        config: ProcessingConfig,
        job_id: str
    ) -> Dict[str, Any]:
        """Store embeddings in S3Vector indexes."""
        storage_results = {}
        
        for vector_type_str, embedding_data in embeddings_results.items():
            if 'error' in embedding_data:
                continue
            
            vector_type = VectorType(vector_type_str)
            if vector_type not in target_indexes:
                logger.warning(f"No target index specified for {vector_type.value}")
                continue
            
            index_arn = target_indexes[vector_type]
            
            try:
                logger.info(f"Storing {vector_type.value} embeddings in index: {index_arn}")
                
                # Extract embeddings from result - handle both optimized and legacy formats
                if 'embedding_result' in embedding_data:
                    # Legacy format with VideoEmbeddingResult object
                    embedding_result = embedding_data['embedding_result']
                    if hasattr(embedding_result, 'embeddings'):
                        # Bedrock result format
                        embeddings = embedding_result.embeddings
                    else:
                        # TwelveLabs API result format
                        embeddings = [
                            {
                                'embedding': segment.embedding,
                                'startSec': segment.start_offset_sec,
                                'endSec': segment.end_offset_sec
                            }
                            for segment in embedding_result.segments
                        ]
                elif 'embeddings' in embedding_data:
                    # Optimized format with direct embeddings list
                    embeddings = embedding_data['embeddings']
                else:
                    logger.error(f"Unknown embedding data format for {vector_type.value}: {embedding_data.keys()}")
                    continue
                
                # Prepare vectors for storage
                vectors_data = []
                for i, embedding_segment in enumerate(embeddings):
                    vector_key = f"{job_id}-{vector_type.value}-seg-{i:04d}"
                    
                    # Extract embedding vector
                    if isinstance(embedding_segment, dict):
                        embedding_vector = embedding_segment.get('embedding', [])
                        start_sec = embedding_segment.get('startSec', 0)
                        end_sec = embedding_segment.get('endSec', 0)
                    else:
                        embedding_vector = getattr(embedding_segment, 'embedding', [])
                        start_sec = getattr(embedding_segment, 'start_offset_sec', 0)
                        end_sec = getattr(embedding_segment, 'end_offset_sec', 0)
                    
                    # Create metadata
                    metadata = {
                        'content_type': 'video',
                        'vector_type': vector_type.value,
                        'job_id': job_id,
                        'segment_index': i,
                        'start_sec': start_sec,
                        'end_sec': end_sec,
                        'duration_sec': end_sec - start_sec,
                        'processing_method': embedding_data.get('method', 'unknown'),
                        'model_id': embedding_data.get('model_id', 'unknown')
                    }
                    
                    vector_data = {
                        'key': vector_key,
                        'data': {'float32': embedding_vector},
                        'metadata': metadata
                    }
                    vectors_data.append(vector_data)
                
                # Store in batches
                batch_size = 100
                stored_count = 0
                
                for i in range(0, len(vectors_data), batch_size):
                    batch = vectors_data[i:i + batch_size]
                    batch_result = self.storage_manager.put_vectors_batch(
                        index_arn=index_arn,
                        vectors_data=batch
                    )
                    stored_count += len(batch)
                
                storage_results[vector_type.value] = {
                    'status': 'success',
                    'index_arn': index_arn,
                    'stored_count': stored_count,
                    'total_segments': len(vectors_data)
                }
                
                logger.info(f"Successfully stored {stored_count} {vector_type.value} vectors")
                
            except Exception as e:
                logger.error(f"Failed to store {vector_type.value} embeddings: {e}")
                storage_results[vector_type.value] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return storage_results
    
    def _calculate_processing_cost(
        self,
        result: VideoProcessingResult,
        config: ProcessingConfig
    ) -> float:
        """Calculate estimated processing cost."""
        total_cost = 0.0
        
        # Estimate video duration from segments
        max_duration = 0.0
        for vector_type, embedding_data in result.embeddings_by_type.items():
            if 'total_segments' in embedding_data:
                segments = embedding_data['total_segments']
                duration = segments * config.segment_duration_sec
                max_duration = max(max_duration, duration)
        
        if max_duration > 0:
            duration_minutes = max_duration / 60.0
            
            # Bedrock Marengo 2.7 pricing: ~$0.00070 per minute
            bedrock_cost_per_minute = 0.00070
            
            # Calculate cost per vector type
            for vector_type in config.vector_types:
                total_cost += duration_minutes * bedrock_cost_per_minute
        
        return round(total_cost, 6)
    
    def batch_process_videos(
        self,
        video_urls: List[str],
        target_indexes: Optional[Dict[VectorType, str]] = None,
        config_override: Optional[ProcessingConfig] = None,
        progress_callback: Optional[Callable[[int, int, VideoProcessingResult], None]] = None
    ) -> List[VideoProcessingResult]:
        """
        Process multiple videos in batch.
        
        Args:
            video_urls: List of video URLs to process
            target_indexes: Mapping of vector types to S3Vector index ARNs
            config_override: Optional configuration override
            progress_callback: Optional progress callback (current, total, result)
            
        Returns:
            List of VideoProcessingResult objects
        """
        logger.info(f"Starting batch processing of {len(video_urls)} videos")
        
        results = []
        for i, video_url in enumerate(video_urls, 1):
            try:
                logger.info(f"Processing video {i}/{len(video_urls)}: {video_url}")
                
                result = self.process_video_from_url(
                    video_url=video_url,
                    target_indexes=target_indexes,
                    config_override=config_override
                )
                
                results.append(result)
                
                if progress_callback:
                    progress_callback(i, len(video_urls), result)
                
            except Exception as e:
                logger.error(f"Failed to process video {i}: {e}")
                
                # Create failed result
                failed_result = VideoProcessingResult(
                    job_id=f"failed-{uuid.uuid4().hex[:8]}",
                    status="failed",
                    source_url=video_url,
                    s3_uri="",
                    error_message=str(e),
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc)
                )
                results.append(failed_result)
                
                if progress_callback:
                    progress_callback(i, len(video_urls), failed_result)
        
        successful = len([r for r in results if r.is_successful])
        logger.info(f"Batch processing completed: {successful}/{len(video_urls)} successful")
        
        return results
    
    def get_job_status(self, job_id: str) -> Optional[VideoProcessingResult]:
        """Get status of a processing job."""
        return self.active_jobs.get(job_id)
    
    def list_active_jobs(self) -> List[VideoProcessingResult]:
        """List all active processing jobs."""
        return list(self.active_jobs.values())
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up completed jobs older than specified age."""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cleaned_count = 0
        
        jobs_to_remove = []
        for job_id, job in self.active_jobs.items():
            if (job.status in ["completed", "failed"] and 
                job.completed_at and 
                job.completed_at.timestamp() < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} completed jobs")
        
        return cleaned_count


# Factory function for easy instantiation
def create_comprehensive_video_service(
    processing_mode: ProcessingMode = ProcessingMode.BEDROCK_PRIMARY,
    vector_types: Optional[List[VectorType]] = None,
    **kwargs
) -> ComprehensiveVideoProcessingService:
    """
    Factory function to create comprehensive video processing service.
    
    Args:
        processing_mode: Processing mode (Bedrock primary by default)
        vector_types: Vector types to generate
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured ComprehensiveVideoProcessingService
    """
    config = ProcessingConfig(
        processing_mode=processing_mode,
        vector_types=vector_types or [VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE, VectorType.AUDIO],
        **kwargs
    )
    
    return ComprehensiveVideoProcessingService(config)