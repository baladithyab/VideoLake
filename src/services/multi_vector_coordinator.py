"""
Multi-Vector Coordinator Service

This service orchestrates multi-vector processing workflows across different vector types
and manages coordination between various embedding services, storage systems, and search engines.

Key Features:
- Unified API for multi-vector operations
- Intelligent routing based on vector types
- Cross-vector-type search and fusion
- Performance optimization and monitoring
- Integration with REST API architecture
"""

import time
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, Any, Optional, List, Set, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService,
    ProcessingMode as CompProcessingMode,
    VectorType as CompVectorType,
    ProcessingConfig as CompProcessingConfig
)
from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery, IndexType
from src.services.interfaces.search_service_interface import SearchQuery
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.exceptions import ValidationError, VectorEmbeddingError, VectorStorageError
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


class VectorType(Enum):
    """Supported vector types in the multi-vector architecture."""
    VISUAL_TEXT = "visual-text"
    VISUAL_IMAGE = "visual-image"  
    AUDIO = "audio"
    TEXT_TITAN = "text-titan"
    CUSTOM = "custom"


@dataclass
class MultiVectorConfig:
    """Configuration for multi-vector processing.

    Note: Processing is always parallel since Bedrock operations are async.
    Jobs are submitted in parallel and polled for completion.
    """
    vector_types: List[str] = field(default_factory=lambda: ["visual-text", "visual-image", "audio"])
    max_concurrent_jobs: int = 8
    enable_cross_vector_search: bool = True
    fusion_method: str = "weighted_average"
    default_top_k: int = 10

    # Performance settings
    batch_size: int = 5
    timeout_seconds: int = 300
    retry_attempts: int = 3
    poll_interval_sec: int = 5  # How often to check job status

    # Quality settings
    similarity_threshold: float = 0.7
    enable_result_filtering: bool = True
    enable_deduplication: bool = True


@dataclass  
class MultiVectorResult:
    """Result from multi-vector processing operation."""
    results_by_type: Dict[str, Any]
    processing_stats: Dict[str, Any]
    total_processing_time_ms: int
    successful_types: List[str]
    failed_types: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchRequest:
    """Unified search request across multiple vector types."""
    query_text: Optional[str] = None
    query_media_uri: Optional[str] = None
    query_embedding: Optional[Dict[str, List[float]]] = None  # By vector type
    
    # Search configuration
    vector_types: Optional[List[str]] = None
    target_indexes: Optional[List[str]] = None
    top_k: int = 10
    similarity_threshold: float = 0.0
    
    # Filtering and processing
    metadata_filters: Optional[Dict[str, Any]] = None
    temporal_filters: Optional[Dict[str, Any]] = None
    fusion_method: str = "weighted_average"
    enable_cross_type_fusion: bool = True


class MultiVectorCoordinator:
    """
    Orchestrates multi-vector processing workflows with unified API for application integration.

    This coordinator manages:
    1. Multi-vector embedding generation
    2. Cross-vector-type storage operations
    3. Multi-index search coordination
    4. Result fusion and optimization
    5. Performance monitoring and analytics
    """
    
    def __init__(self,
                 config: Optional[MultiVectorConfig] = None,
                 twelvelabs_service: Optional[TwelveLabsVideoProcessingService] = None,
                 search_engine: Optional[SimilaritySearchEngine] = None,
                 storage_manager: Optional[S3VectorStorageManager] = None,
                 bedrock_service: Optional[BedrockEmbeddingService] = None,
                 comprehensive_service: Optional[ComprehensiveVideoProcessingService] = None):
        """
        Initialize the Multi-Vector Coordinator.
        
        Args:
            config: Multi-vector processing configuration
            twelvelabs_service: TwelveLabs video processing service
            search_engine: Enhanced similarity search engine
            storage_manager: S3 vector storage manager
            bedrock_service: Bedrock embedding service
            comprehensive_service: Comprehensive video processing service
        """
        self.config = config or MultiVectorConfig()
        
        # Initialize services
        self.twelvelabs = twelvelabs_service or TwelveLabsVideoProcessingService()
        self.search_engine = search_engine or SimilaritySearchEngine()
        self.storage = storage_manager or S3VectorStorageManager()
        self.bedrock = bedrock_service or BedrockEmbeddingService()
        
        # Initialize comprehensive video processing service (primary for video URLs)
        self.comprehensive_service = comprehensive_service or ComprehensiveVideoProcessingService(
            CompProcessingConfig(
                processing_mode=CompProcessingMode.BEDROCK_PRIMARY,
                vector_types=[CompVectorType.VISUAL_TEXT, CompVectorType.AUDIO],
                enable_cost_tracking=True
            )
        )
        
        # Multi-vector coordination state
        self._coordination_lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_jobs)
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Vector type routing and capabilities
        self.vector_type_routing = {
            VectorType.VISUAL_TEXT: self.twelvelabs,
            VectorType.VISUAL_IMAGE: self.twelvelabs,
            VectorType.AUDIO: self.twelvelabs,
            VectorType.TEXT_TITAN: self.bedrock
        }
        
        # Performance tracking
        self.performance_stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'average_processing_time_ms': 0.0,
            'operations_by_type': {},
            'cross_vector_searches': 0,
            'multi_index_operations': 0
        }
        
        # Initialize coordination patterns
        self._setup_index_coordination()
        
        logger.info(f"MultiVectorCoordinator initialized with {len(self.config.vector_types)} vector types")

    def process_video_urls(
        self,
        video_urls: List[str],
        target_indexes: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process videos from URLs using the comprehensive video processing service.
        
        This method provides the missing functionality for real AWS operations:
        1. Downloads videos from URLs to S3
        2. Processes with Bedrock Marengo 2.7 (primary) or TwelveLabs API (secondary)
        3. Stores embeddings in S3Vector indexes
        
        Args:
            video_urls: List of HTTP/HTTPS video URLs to process
            target_indexes: Mapping of vector types to S3Vector index ARNs
            progress_callback: Optional progress callback (current, total, result)
            
        Returns:
            List of processing results
        """
        logger.info(f"Processing {len(video_urls)} video URLs with comprehensive service")
        
        # Convert target_indexes to CompVectorType mapping if provided
        comp_target_indexes = None
        if target_indexes:
            comp_target_indexes = {}
            for vector_type_str, index_arn in target_indexes.items():
                try:
                    comp_vector_type = CompVectorType(vector_type_str)
                    comp_target_indexes[comp_vector_type] = index_arn
                except ValueError:
                    logger.warning(f"Unknown vector type: {vector_type_str}")
        
        # Create wrapper callback to match expected signature
        def wrapper_callback(current: int, total: int, result) -> None:
            if progress_callback:
                # Convert VideoProcessingResult to dict for callback
                result_dict = {
                    'job_id': result.job_id,
                    'status': result.status,
                    'source_url': result.source_url,
                    's3_uri': result.s3_uri,
                    'is_successful': result.is_successful,
                    'error_message': result.error_message
                }
                progress_callback(current, total, result_dict)
        
        # Process videos using comprehensive service
        results = self.comprehensive_service.batch_process_videos(
            video_urls=video_urls,
            target_indexes=comp_target_indexes,
            progress_callback=wrapper_callback if progress_callback else None
        )
        
        # Convert results to MultiVectorCoordinator format
        converted_results = []
        for result in results:
            converted_result = {
                'job_id': result.job_id,
                'status': result.status,
                'source_url': result.source_url,
                's3_uri': result.s3_uri,
                'embeddings_by_type': result.embeddings_by_type,
                'storage_results': result.storage_results,
                'processing_time_ms': result.processing_time_ms,
                'estimated_cost_usd': result.estimated_cost_usd,
                'total_segments': result.total_segments,
                'is_successful': result.is_successful,
                'error_message': result.error_message
            }
            converted_results.append(converted_result)
        
        successful = len([r for r in converted_results if r['is_successful']])
        logger.info(f"Video URL processing completed: {successful}/{len(video_urls)} successful")
        
        return converted_results

    def process_sample_videos(
        self,
        sample_videos: List[Dict[str, Any]],
        target_indexes: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Process sample videos from the sample video data.
        
        Args:
            sample_videos: List of sample video dictionaries with 'sources' field
            target_indexes: Mapping of vector types to S3Vector index ARNs
            progress_callback: Optional progress callback
            
        Returns:
            List of processing results
        """
        # Extract video URLs from sample video data
        video_urls = []
        for video in sample_videos:
            sources = video.get('sources', [])
            if sources:
                video_urls.append(sources[0])  # Use first source URL
        
        logger.info(f"Processing {len(video_urls)} sample videos")
        
        return self.process_video_urls(
            video_urls=video_urls,
            target_indexes=target_indexes,
            progress_callback=progress_callback
        )

    def _setup_index_coordination(self) -> None:
        """Setup coordination patterns between different vector indexes."""
        # Register vector type configurations with storage manager
        for vector_type in self.config.vector_types:
            if vector_type in self.storage.vector_type_configs:
                config = self.storage.vector_type_configs[vector_type]
                logger.debug(f"Configured vector type {vector_type}: {config}")

    def process_multi_vector_content(self,
                                   content_inputs: List[Dict[str, Any]],
                                   vector_types: Optional[List[str]] = None) -> MultiVectorResult:
        """
        Process content to generate embeddings across multiple vector types.

        All jobs are submitted in parallel since Bedrock operations are async.
        The method polls for job completion and returns when all jobs finish.

        Args:
            content_inputs: List of content input configurations
            vector_types: Vector types to generate (defaults to config)

        Returns:
            MultiVectorResult with embeddings by vector type
        """
        start_time = time.time()
        workflow_id = f"multi_vector_{int(start_time)}_{id(content_inputs)}"

        vector_types = vector_types or self.config.vector_types

        logger.info(f"Starting parallel multi-vector processing: {workflow_id}, {len(content_inputs)} inputs, {len(vector_types)} types")

        # Track active workflow
        with self._coordination_lock:
            self.active_workflows[workflow_id] = {
                'start_time': start_time,
                'status': 'processing',
                'content_count': len(content_inputs),
                'vector_types': vector_types,
                'processing_mode': 'parallel'  # Always parallel for async Bedrock
            }

        try:
            # Always use parallel processing since Bedrock is async
            results = self._process_parallel(content_inputs, vector_types, workflow_id)

            # Calculate final statistics
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Update workflow status
            with self._coordination_lock:
                if workflow_id in self.active_workflows:
                    self.active_workflows[workflow_id].update({
                        'status': 'completed',
                        'processing_time_ms': processing_time_ms,
                        'end_time': time.time()
                    })

            # Update performance stats
            self._update_performance_stats('process_multi_vector', processing_time_ms, True)
            
            logger.info(f"Multi-vector processing completed: {workflow_id}, {processing_time_ms}ms")
            
            return MultiVectorResult(
                results_by_type=results['results_by_type'],
                processing_stats=results['stats'],
                total_processing_time_ms=processing_time_ms,
                successful_types=results['successful_types'],
                failed_types=results['failed_types'],
                metadata={
                    'workflow_id': workflow_id,
                    'processing_mode': processing_mode.value,
                    'content_count': len(content_inputs)
                }
            )
            
        except Exception as e:
            # Update workflow status
            with self._coordination_lock:
                if workflow_id in self.active_workflows:
                    self.active_workflows[workflow_id].update({
                        'status': 'failed',
                        'error': str(e),
                        'end_time': time.time()
                    })
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            self._update_performance_stats('process_multi_vector', processing_time_ms, False)
            
            logger.error(f"Multi-vector processing failed: {workflow_id}, {e}")
            raise VectorEmbeddingError(f"Multi-vector processing failed: {str(e)}")
        
        finally:
            # Cleanup workflow tracking after delay
            self._schedule_workflow_cleanup(workflow_id)

    def _process_parallel(self, content_inputs: List[Dict[str, Any]], 
                        vector_types: List[str], workflow_id: str) -> Dict[str, Any]:
        """Process content with full parallelization across vector types and inputs."""
        logger.debug(f"Processing {len(content_inputs)} inputs in parallel mode")
        
        # Create all processing tasks
        tasks = []
        for content_input in content_inputs:
            for vector_type in vector_types:
                tasks.append({
                    'content_input': content_input,
                    'vector_type': vector_type,
                    'task_id': f"{workflow_id}_{content_input.get('id', 'unknown')}_{vector_type}"
                })
        
        # Execute all tasks concurrently
        results_by_type = {vt: [] for vt in vector_types}
        failed_types = []
        successful_types = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_jobs) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._process_single_content_vector, task): task
                for task in tasks
            }
            
            # Collect results
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    vector_type = task['vector_type']
                    results_by_type[vector_type].append(result)
                    
                    if vector_type not in successful_types:
                        successful_types.append(vector_type)
                        
                except Exception as e:
                    logger.error(f"Task {task['task_id']} failed: {e}")
                    vector_type = task['vector_type']
                    if vector_type not in failed_types:
                        failed_types.append(vector_type)
        
        return {
            'results_by_type': results_by_type,
            'successful_types': successful_types,
            'failed_types': failed_types,
            'stats': {
                'total_tasks': len(tasks),
                'successful_tasks': sum(len(results) for results in results_by_type.values()),
                'failed_tasks': len(tasks) - sum(len(results) for results in results_by_type.values()),
                'mode': 'parallel'
            }
        }

    def _process_sequential(self, content_inputs: List[Dict[str, Any]], 
                          vector_types: List[str], workflow_id: str) -> Dict[str, Any]:
        """Process content sequentially by vector type."""
        logger.debug(f"Processing {len(content_inputs)} inputs in sequential mode")
        
        results_by_type = {}
        successful_types = []
        failed_types = []
        
        for vector_type in vector_types:
            try:
                logger.debug(f"Processing vector type: {vector_type}")
                
                # Process all content for this vector type
                type_results = []
                for content_input in content_inputs:
                    task = {
                        'content_input': content_input,
                        'vector_type': vector_type,
                        'task_id': f"{workflow_id}_{content_input.get('id', 'unknown')}_{vector_type}"
                    }
                    
                    try:
                        result = self._process_single_content_vector(task)
                        type_results.append(result)
                    except Exception as e:
                        logger.error(f"Failed to process {task['task_id']}: {e}")
                        # Continue with other content
                
                results_by_type[vector_type] = type_results
                successful_types.append(vector_type)
                
            except Exception as e:
                logger.error(f"Failed to process vector type {vector_type}: {e}")
                failed_types.append(vector_type)
                results_by_type[vector_type] = []
        
        return {
            'results_by_type': results_by_type,
            'successful_types': successful_types,
            'failed_types': failed_types,
            'stats': {
                'total_vector_types': len(vector_types),
                'successful_types': len(successful_types),
                'failed_types': len(failed_types),
                'mode': 'sequential'
            }
        }

    def _process_adaptive(self, content_inputs: List[Dict[str, Any]], 
                        vector_types: List[str], workflow_id: str) -> Dict[str, Any]:
        """Adaptively choose processing strategy based on workload."""
        total_tasks = len(content_inputs) * len(vector_types)
        
        if total_tasks <= self.config.batch_size:
            # Small workload - use parallel
            logger.debug("Using parallel processing for small workload")
            return self._process_parallel(content_inputs, vector_types, workflow_id)
        elif len(vector_types) <= 2:
            # Few vector types - process vector types in parallel
            logger.debug("Using vector-type parallelization for few types")
            return self._process_by_vector_type_parallel(content_inputs, vector_types, workflow_id)
        else:
            # Large workload - use hybrid approach
            logger.debug("Using hybrid processing for large workload")
            return self._process_hybrid(content_inputs, vector_types, workflow_id)

    def _process_by_vector_type_parallel(self, content_inputs: List[Dict[str, Any]], 
                                       vector_types: List[str], workflow_id: str) -> Dict[str, Any]:
        """Process vector types in parallel, content sequentially within each type."""
        results_by_type = {}
        successful_types = []
        failed_types = []
        
        with ThreadPoolExecutor(max_workers=len(vector_types)) as executor:
            # Submit one task per vector type
            future_to_type = {
                executor.submit(self._process_vector_type_batch, content_inputs, vector_type, workflow_id): vector_type
                for vector_type in vector_types
            }
            
            # Collect results
            for future in as_completed(future_to_type):
                vector_type = future_to_type[future]
                try:
                    type_results = future.result()
                    results_by_type[vector_type] = type_results
                    successful_types.append(vector_type)
                except Exception as e:
                    logger.error(f"Failed to process vector type {vector_type}: {e}")
                    failed_types.append(vector_type)
                    results_by_type[vector_type] = []
        
        return {
            'results_by_type': results_by_type,
            'successful_types': successful_types,
            'failed_types': failed_types,
            'stats': {
                'total_vector_types': len(vector_types),
                'successful_types': len(successful_types),
                'failed_types': len(failed_types),
                'mode': 'vector_type_parallel'
            }
        }

    def _process_hybrid(self, content_inputs: List[Dict[str, Any]], 
                       vector_types: List[str], workflow_id: str) -> Dict[str, Any]:
        """Hybrid processing with batching and parallelization."""
        # Process in batches to control resource usage
        batch_size = min(self.config.batch_size, len(content_inputs))
        content_batches = [content_inputs[i:i + batch_size] for i in range(0, len(content_inputs), batch_size)]
        
        results_by_type = {vt: [] for vt in vector_types}
        successful_types = []
        failed_types = []
        
        for batch_idx, content_batch in enumerate(content_batches):
            logger.debug(f"Processing batch {batch_idx + 1}/{len(content_batches)}")
            
            # Process this batch across all vector types in parallel
            batch_results = self._process_by_vector_type_parallel(
                content_batch, vector_types, f"{workflow_id}_batch_{batch_idx}"
            )
            
            # Merge results
            for vector_type in vector_types:
                if batch_results['results_by_type'][vector_type]:
                    results_by_type[vector_type].extend(batch_results['results_by_type'][vector_type])
            
            # Track successful types
            for vector_type in batch_results['successful_types']:
                if vector_type not in successful_types:
                    successful_types.append(vector_type)
            
            for vector_type in batch_results['failed_types']:
                if vector_type not in failed_types and vector_type not in successful_types:
                    failed_types.append(vector_type)
        
        return {
            'results_by_type': results_by_type,
            'successful_types': successful_types,
            'failed_types': failed_types,
            'stats': {
                'total_batches': len(content_batches),
                'batch_size': batch_size,
                'total_vector_types': len(vector_types),
                'successful_types': len(successful_types),
                'failed_types': len(failed_types),
                'mode': 'hybrid'
            }
        }

    def _process_vector_type_batch(self, content_inputs: List[Dict[str, Any]], 
                                 vector_type: str, workflow_id: str) -> List[Dict[str, Any]]:
        """Process all content inputs for a single vector type."""
        results = []
        
        for content_input in content_inputs:
            task = {
                'content_input': content_input,
                'vector_type': vector_type,
                'task_id': f"{workflow_id}_{content_input.get('id', 'unknown')}_{vector_type}"
            }
            
            try:
                result = self._process_single_content_vector(task)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {task['task_id']}: {e}")
                # Continue with other content
        
        return results

    def _process_single_content_vector(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single content input for a specific vector type."""
        content_input = task['content_input']
        vector_type = task['vector_type']
        task_id = task['task_id']
        
        logger.debug(f"Processing task: {task_id}")
        
        # Route to appropriate service based on vector type
        if vector_type in ['visual-text', 'visual-image', 'audio']:
            # Use TwelveLabs service
            return self._process_with_twelvelabs(content_input, vector_type)
        elif vector_type == 'text-titan':
            # Use Bedrock service
            return self._process_with_bedrock(content_input, vector_type)
        else:
            raise ValidationError(f"Unsupported vector type: {vector_type}")

    def _process_with_twelvelabs(self, content_input: Dict[str, Any], vector_type: str) -> Dict[str, Any]:
        """Process content using TwelveLabs service."""
        if 'video_s3_uri' in content_input:
            result = self.twelvelabs.process_video_sync(
                video_s3_uri=content_input['video_s3_uri'],
                embedding_options=[vector_type],
                **content_input.get('processing_params', {})
            )
        elif 'video_base64' in content_input:
            result = self.twelvelabs.process_video_sync(
                video_base64=content_input['video_base64'],
                embedding_options=[vector_type],
                **content_input.get('processing_params', {})
            )
        else:
            raise ValidationError("No valid video source in content input")
        
        return {
            'embedding_result': result,
            'vector_type': vector_type,
            'content_id': content_input.get('id'),
            'processing_time_ms': result.processing_time_ms,
            'segments_count': result.total_segments
        }

    def _process_with_bedrock(self, content_input: Dict[str, Any], vector_type: str) -> Dict[str, Any]:
        """Process content using Bedrock service."""
        text = content_input.get('text')
        if not text:
            raise ValidationError("No text provided for Bedrock processing")
        
        result = self.bedrock.generate_text_embedding(text)
        
        return {
            'embedding_result': result,
            'vector_type': vector_type,
            'content_id': content_input.get('id'),
            'processing_time_ms': 0,  # Bedrock doesn't track this
            'dimensions': len(result.embedding)
        }

    def search_multi_vector(self, search_request: SearchRequest) -> Dict[str, Any]:
        """
        Perform unified search across multiple vector types and indexes.
        
        Args:
            search_request: Unified search request configuration
            
        Returns:
            Dictionary with search results and metadata
        """
        start_time = time.time()
        search_id = f"multi_search_{int(start_time)}_{id(search_request)}"
        
        logger.info(f"Starting multi-vector search: {search_id}")
        
        try:
            # Determine search strategy
            if search_request.target_indexes:
                # Direct index search
                results = self._search_specific_indexes(search_request, search_id)
            elif search_request.vector_types:
                # Vector type based search  
                results = self._search_by_vector_types(search_request, search_id)
            else:
                # Auto-discovery search
                results = self._search_auto_discovery(search_request, search_id)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update stats
            self._update_performance_stats('search_multi_vector', processing_time_ms, True)
            
            logger.info(f"Multi-vector search completed: {search_id}, {processing_time_ms}ms")
            
            return {
                'search_id': search_id,
                'results': results,
                'processing_time_ms': processing_time_ms,
                'search_request': search_request,
                'metadata': {
                    'fusion_method': search_request.fusion_method,
                    'cross_type_enabled': search_request.enable_cross_type_fusion
                }
            }
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            self._update_performance_stats('search_multi_vector', processing_time_ms, False)
            
            logger.error(f"Multi-vector search failed: {search_id}, {e}")
            raise VectorEmbeddingError(f"Multi-vector search failed: {str(e)}")

    def _search_specific_indexes(self, search_request: SearchRequest, search_id: str) -> Dict[str, Any]:
        """Search specific indexes directly."""
        logger.debug(f"Searching specific indexes: {search_request.target_indexes}")
        
        # Validate target_indexes is not None
        if not search_request.target_indexes:
            raise ValidationError("No target indexes specified for search")
        
        # Build index configurations
        index_configs = []
        for index_arn in search_request.target_indexes:
            # Determine index type from registry or defaults
            index_type = self._determine_index_type(index_arn)
            index_configs.append({
                'index_arn': index_arn,
                'index_type': index_type.value,
                'weight': 1.0
            })
        
        # Create search query (using interface type)
        search_query = self._build_similarity_query(search_request)
        
        # Execute multi-index search
        response = self.search_engine.search_multi_index(
            search_query, index_configs, search_request.fusion_method
        )
        
        return {
            'results': response.results,
            'total_results': response.total_results,
            'index_count': len(index_configs),
            'fusion_method': search_request.fusion_method
        }

    def _search_by_vector_types(self, search_request: SearchRequest, search_id: str) -> Dict[str, Any]:
        """Search by vector types with auto-discovery of indexes."""
        logger.debug(f"Searching by vector types: {search_request.vector_types}")
        
        # Validate vector_types is not None
        if not search_request.vector_types:
            raise ValidationError("No vector types specified for search")
        
        # Find compatible indexes for each vector type
        index_configs = []
        for vector_type in search_request.vector_types:
            compatible_indexes = self._find_indexes_for_vector_type(vector_type)
            
            for index_arn in compatible_indexes:
                index_type = self._determine_index_type(index_arn)
                index_configs.append({
                    'index_arn': index_arn,
                    'index_type': index_type.value,
                    'weight': 1.0 / len(compatible_indexes),  # Equal weight per type
                    'vector_type': vector_type
                })
        
        if not index_configs:
            raise ValidationError(f"No compatible indexes found for vector types: {search_request.vector_types}")
        
        # Create search query (using interface type)
        search_query = self._build_similarity_query(search_request)
        
        # Execute multi-index search
        response = self.search_engine.search_multi_index(
            search_query, index_configs, search_request.fusion_method
        )
        
        return {
            'results': response.results,
            'total_results': response.total_results,
            'index_count': len(index_configs),
            'vector_types_searched': search_request.vector_types,
            'fusion_method': search_request.fusion_method
        }

    def _search_auto_discovery(self, search_request: SearchRequest, search_id: str) -> Dict[str, Any]:
        """Auto-discover compatible indexes and search all."""
        logger.debug("Auto-discovering compatible indexes")
        
        # Create search query to determine compatibility
        search_query = self._build_similarity_query(search_request)
        
        # Get compatible indexes from search engine
        compatible_indexes = self.search_engine.get_compatible_indexes(search_query)
        
        if not compatible_indexes:
            raise ValidationError("No compatible indexes found for search query")
        
        # Build index configurations
        index_configs = []
        for index_arn in compatible_indexes:
            index_type = self._determine_index_type(index_arn)
            index_configs.append({
                'index_arn': index_arn,
                'index_type': index_type.value,
                'weight': 1.0 / len(compatible_indexes)
            })
        
        # Execute multi-index search
        response = self.search_engine.search_multi_index(
            search_query, index_configs, search_request.fusion_method
        )
        
        return {
            'results': response.results,
            'total_results': response.total_results,
            'index_count': len(index_configs),
            'auto_discovered': True,
            'compatible_indexes': compatible_indexes,
            'fusion_method': search_request.fusion_method
        }

    def _build_similarity_query(self, search_request: SearchRequest) -> SearchQuery:
        """Build SearchQuery from SearchRequest for compatibility with SimilaritySearchEngine."""
        return SearchQuery(
            query_text=search_request.query_text,
            query_video_s3_uri=search_request.query_media_uri if search_request.query_media_uri and search_request.query_media_uri.startswith('s3://') else None,
            query_embedding=search_request.query_embedding.get('default') if search_request.query_embedding else None,
            target_indexes=search_request.target_indexes,
            vector_types=search_request.vector_types,
            top_k=search_request.top_k,
            similarity_threshold=search_request.similarity_threshold,
            metadata_filters=search_request.metadata_filters,
            cross_index_fusion=search_request.enable_cross_type_fusion,
            include_explanations=True,
            deduplicate_results=self.config.enable_deduplication
        )

    def _determine_index_type(self, index_arn: str) -> IndexType:
        """Determine the index type for an index ARN."""
        # Check storage registry if available
        try:
            if hasattr(self.storage, '_registry_lock') and hasattr(self.storage, 'index_registry'):
                with self.storage._registry_lock:
                    if index_arn in self.storage.index_registry:
                        vector_type = self.storage.index_registry[index_arn].get('vector_type')
                        if vector_type in ['visual-text', 'visual-image', 'audio']:
                            return IndexType.MARENGO_MULTIMODAL
                        elif vector_type == 'text-titan':
                            return IndexType.TITAN_TEXT
        except Exception as e:
            logger.warning(f"Could not access storage registry: {e}")
        
        # Default based on index name patterns
        if 'titan' in index_arn.lower() or 'text' in index_arn.lower():
            return IndexType.TITAN_TEXT
        else:
            return IndexType.MARENGO_MULTIMODAL

    def _find_indexes_for_vector_type(self, vector_type: str) -> List[str]:
        """Find indexes compatible with a specific vector type."""
        compatible_indexes = []
        
        try:
            if hasattr(self.storage, '_registry_lock') and hasattr(self.storage, 'index_registry'):
                with self.storage._registry_lock:
                    for index_arn, config in self.storage.index_registry.items():
                        if config.get('vector_type') == vector_type:
                            compatible_indexes.append(index_arn)
        except Exception as e:
            logger.warning(f"Could not access storage registry for vector type {vector_type}: {e}")
            # Return empty list if registry access fails
        
        return compatible_indexes

    def _update_performance_stats(self, operation: str, processing_time_ms: int, success: bool) -> None:
        """Update performance statistics."""
        with self._coordination_lock:
            self.performance_stats['total_operations'] += 1
            
            if success:
                self.performance_stats['successful_operations'] += 1
            else:
                self.performance_stats['failed_operations'] += 1
            
            # Update average processing time
            current_avg = self.performance_stats['average_processing_time_ms']
            total_ops = self.performance_stats['total_operations']
            self.performance_stats['average_processing_time_ms'] = (
                (current_avg * (total_ops - 1) + processing_time_ms) / total_ops
            )
            
            # Update operation type stats
            if operation not in self.performance_stats['operations_by_type']:
                self.performance_stats['operations_by_type'][operation] = 0
            self.performance_stats['operations_by_type'][operation] += 1

    def _schedule_workflow_cleanup(self, workflow_id: str, delay_seconds: int = 300) -> None:
        """Schedule cleanup of workflow tracking after delay."""
        def cleanup():
            time.sleep(delay_seconds)
            with self._coordination_lock:
                if workflow_id in self.active_workflows:
                    del self.active_workflows[workflow_id]
                    logger.debug(f"Cleaned up workflow tracking: {workflow_id}")
        
        # Run cleanup in background
        import threading
        cleanup_thread = threading.Thread(target=cleanup, daemon=True)
        cleanup_thread.start()

    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about multi-vector coordination."""
        with self._coordination_lock:
            active_workflows = dict(self.active_workflows)
            performance_stats = dict(self.performance_stats)
        
        # Add current system state
        stats = {
            'performance': performance_stats,
            'active_workflows': {
                'count': len(active_workflows),
                'workflows': active_workflows
            },
            'configuration': {
                'vector_types': self.config.vector_types,
                'max_concurrent_jobs': self.config.max_concurrent_jobs,
                'processing_mode': self.config.processing_mode.value,
                'fusion_method': self.config.fusion_method
            },
            'service_status': {
                'twelvelabs_initialized': self.twelvelabs is not None,
                'search_engine_initialized': self.search_engine is not None,
                'storage_initialized': self.storage is not None,
                'bedrock_initialized': self.bedrock is not None
            },
            'storage_stats': self.storage.get_multi_index_stats()
        }
        
        return stats

    # ==================== Async Wrapper Methods ====================
    # These methods wrap blocking I/O operations with asyncio.to_thread()
    # to prevent blocking the event loop when called from async contexts.

    async def async_process_video_urls(
        self,
        video_urls: List[str],
        target_indexes: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for process_video_urls.
        Wraps blocking I/O with asyncio.to_thread().

        Args:
            video_urls: List of HTTP/HTTPS video URLs to process
            target_indexes: Mapping of vector types to S3Vector index ARNs
            progress_callback: Optional progress callback (current, total, result)

        Returns:
            List of processing results
        """
        return await asyncio.to_thread(
            self.process_video_urls,
            video_urls,
            target_indexes,
            progress_callback
        )

    async def async_process_sample_videos(
        self,
        sample_videos: List[Dict[str, Any]],
        target_indexes: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Async wrapper for process_sample_videos.
        Wraps blocking I/O with asyncio.to_thread().

        Args:
            sample_videos: List of sample video dictionaries with 'sources' field
            target_indexes: Mapping of vector types to S3Vector index ARNs
            progress_callback: Optional progress callback

        Returns:
            List of processing results
        """
        return await asyncio.to_thread(
            self.process_sample_videos,
            sample_videos,
            target_indexes,
            progress_callback
        )

    async def async_process_multi_vector_content(
        self,
        content_inputs: List[Dict[str, Any]],
        vector_types: Optional[List[str]] = None
    ) -> MultiVectorResult:
        """
        Async wrapper for process_multi_vector_content.
        Wraps blocking I/O with asyncio.to_thread().

        Args:
            content_inputs: List of content input configurations
            vector_types: Vector types to generate (defaults to config)

        Returns:
            MultiVectorResult with embeddings by vector type
        """
        return await asyncio.to_thread(
            self.process_multi_vector_content,
            content_inputs,
            vector_types
        )

    async def async_search_multi_vector(
        self,
        search_request: SearchRequest
    ) -> Dict[str, Any]:
        """
        Async wrapper for search_multi_vector.
        Wraps blocking I/O with asyncio.to_thread().

        Args:
            search_request: Unified search request configuration

        Returns:
            Dictionary with search results and metadata
        """
        return await asyncio.to_thread(
            self.search_multi_vector,
            search_request
        )

    async def async_get_coordination_stats(self) -> Dict[str, Any]:
        """
        Async wrapper for get_coordination_stats.
        Wraps blocking I/O with asyncio.to_thread().

        Returns:
            Dictionary with comprehensive coordination statistics
        """
        return await asyncio.to_thread(self.get_coordination_stats)

    def shutdown(self) -> None:
        """Shutdown the coordinator and cleanup resources."""
        logger.info("Shutting down MultiVectorCoordinator")
        
        # Wait for active workflows to complete or timeout
        timeout = 30  # seconds
        start_time = time.time()
        
        while self.active_workflows and (time.time() - start_time) < timeout:
            time.sleep(1)
            logger.debug(f"Waiting for {len(self.active_workflows)} active workflows to complete")
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        # Clear active workflows
        with self._coordination_lock:
            self.active_workflows.clear()
        
        logger.info("MultiVectorCoordinator shutdown completed")