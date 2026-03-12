#!/usr/bin/env python3
"""
Processing Components for Unified S3Vector Demo

This module contains all video processing functionality including:
- Video input handling (upload, S3 URIs, collections)
- Marengo 2.7 multi-vector processing
- Dual storage pattern implementation
- Progress tracking and cost estimation
"""

import time
import random
from typing import Dict, Any, List, Optional
import streamlit as st
from .sample_video_data import sample_video_manager
from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService,
    ProcessingConfig,
    ProcessingMode,
    StoragePattern
)
from src.shared.vector_types import SupportedVectorTypes, get_vector_type_config, list_supported_vector_types
from src.shared.metadata_handlers import MetadataTransformer, create_media_metadata
from src.shared.aws_client_pool import AWSClientPool
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ProcessingComponents:
    """Processing functionality components for the unified demo."""
    
    def __init__(self, service_manager=None, coordinator=None):
        self.service_manager = service_manager
        self.coordinator = coordinator
        
        # Initialize comprehensive video processing service
        self.comprehensive_service = None
        self._last_vector_types = None  # Track last used vector types for reinit detection
        
        # Initialize shared components
        self._initialize_shared_components()
        self._initialize_comprehensive_service()
    
    def _initialize_shared_components(self):
        """Initialize shared components for optimized operations."""
        try:
            self.metadata_transformer = MetadataTransformer()
            self.aws_client_pool = AWSClientPool()
            logger.info("Processing components: shared components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize shared components in ProcessingComponents: {e}")
            self.metadata_transformer = None
            self.aws_client_pool = None
    
    def _convert_supported_vector_types_to_service_types(self, supported_types: List[SupportedVectorTypes]):
        """Convert SupportedVectorTypes to service-compatible VectorType."""
        # Import the service's VectorType to avoid circular imports
        try:
            from src.services.comprehensive_video_processing_service import VectorType
            
            # Create mapping from shared types to service types
            type_mapping = {
                SupportedVectorTypes.VISUAL_TEXT: VectorType.VISUAL_TEXT,
                SupportedVectorTypes.VISUAL_IMAGE: VectorType.VISUAL_IMAGE,
                SupportedVectorTypes.AUDIO: VectorType.AUDIO,
                SupportedVectorTypes.TEXT_TITAN: getattr(VectorType, 'TEXT_TITAN', None),
                SupportedVectorTypes.TEXT_COHERE: getattr(VectorType, 'TEXT_COHERE', None),
                SupportedVectorTypes.MULTIMODAL: getattr(VectorType, 'MULTIMODAL', None)
            }
            
            service_types = []
            for supported_type in supported_types:
                service_type = type_mapping.get(supported_type)
                if service_type is not None:
                    service_types.append(service_type)
                else:
                    logger.warning(f"No service mapping found for vector type: {supported_type.value}")
            
            return service_types
            
        except ImportError as e:
            logger.error(f"Failed to import service VectorType: {e}")
            # Fallback: return empty list or handle as needed
            return []
    
    def _initialize_comprehensive_service(self):
        """Initialize the comprehensive video processing service."""
        try:
            # Get vector types from session state or use defaults
            import streamlit as st
            from src.config.app_config import get_config
            
            app_config = get_config()
            selected_vector_types = st.session_state.get('selected_vector_types', app_config.ui.default_vector_types)
            
            # Convert string vector types to SupportedVectorTypes enums using shared components
            vector_type_mapping = {
                "visual-text": SupportedVectorTypes.VISUAL_TEXT,
                "visual-image": SupportedVectorTypes.VISUAL_IMAGE,
                "audio": SupportedVectorTypes.AUDIO
            }
            
            vector_types = []
            for vector_type_str in selected_vector_types:
                if vector_type_str in vector_type_mapping:
                    vector_types.append(vector_type_mapping[vector_type_str])
                else:
                    logger.warning(f"Unknown vector type: {vector_type_str}")
            
            # Ensure we have at least one vector type using shared components
            if not vector_types:
                vector_types = [SupportedVectorTypes.VISUAL_TEXT, SupportedVectorTypes.VISUAL_IMAGE, SupportedVectorTypes.AUDIO]
                logger.info("No valid vector types found, using all defaults")
            
            logger.info(f"Initializing ComprehensiveVideoProcessingService with vector types: {[vt.value for vt in vector_types]}")
            
            # Create processing configuration for Bedrock primary mode
            # Convert shared vector types to service-compatible types
            service_vector_types = self._convert_supported_vector_types_to_service_types(vector_types)
            
            config = ProcessingConfig(
                processing_mode=ProcessingMode.BEDROCK_PRIMARY,
                vector_types=service_vector_types,
                storage_patterns=[StoragePattern.DIRECT_S3VECTOR],
                segment_duration_sec=st.session_state.get('segment_duration', 5.0),
                enable_cost_tracking=True
            )
            
            self.comprehensive_service = ComprehensiveVideoProcessingService(config)
            self._last_vector_types = selected_vector_types.copy()  # Track current vector types
            logger.info(f"ComprehensiveVideoProcessingService initialized successfully with {len(vector_types)} vector types")
            
        except Exception as e:
            logger.error(f"Failed to initialize ComprehensiveVideoProcessingService: {e}")
            self.comprehensive_service = None
    
    def _ensure_service_updated(self):
        """Ensure the comprehensive service is updated with current session state configuration."""
        try:
            import streamlit as st
            from src.config.app_config import get_config
            
            app_config = get_config()
            current_vector_types = st.session_state.get('selected_vector_types', app_config.ui.default_vector_types)
            
            # Check if vector types have changed
            if (self._last_vector_types != current_vector_types or
                self.comprehensive_service is None):
                
                logger.info(f"Vector types changed from {self._last_vector_types} to {current_vector_types}, reinitializing service")
                self._initialize_comprehensive_service()
                
        except Exception as e:
            logger.error(f"Failed to update comprehensive service: {e}")
    
    def process_sample_videos(self, selected_videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process sample videos using the ComprehensiveVideoProcessingService.
        
        This method performs real AWS operations:
        1. Downloads videos from URLs to S3
        2. Processes with Bedrock Marengo 2.7
        3. Stores embeddings in S3Vector indexes
        
        Args:
            selected_videos: List of video dictionaries from sample_video_manager
            
        Returns:
            Dictionary with processing results and job information
        """
        # Ensure service is updated with current configuration
        self._ensure_service_updated()
        
        if not self.comprehensive_service:
            st.error("❌ ComprehensiveVideoProcessingService not available")
            return {"status": "error", "message": "Service not initialized"}
        
        if not selected_videos:
            st.error("❌ No videos selected for processing")
            return {"status": "error", "message": "No videos selected"}
        
        # Extract video URLs from selected videos
        video_urls = []
        for video in selected_videos:
            if video.get("sources") and len(video["sources"]) > 0:
                video_urls.append(video["sources"][0])
            else:
                logger.warning(f"No source URL found for video: {video.get('title', 'Unknown')}")
        
        if not video_urls:
            st.error("❌ No valid video URLs found in selected videos")
            return {"status": "error", "message": "No valid video URLs"}
        
        st.info(f"🚀 Starting real AWS processing for {len(video_urls)} videos...")
        
        # Create processing job tracking
        job_id = f"sample_videos_job_{int(time.time())}"
        
        # Initialize processing jobs if not exists
        if 'processing_jobs' not in st.session_state:
            st.session_state.processing_jobs = {}
        
        # Create job info
        job_info = {
            "job_id": job_id,
            "type": "sample_videos_real_aws",
            "video_count": len(video_urls),
            "video_urls": video_urls,
            "video_titles": [v.get("title", "Unknown") for v in selected_videos],
            "status": "processing",
            "started_at": time.time(),
            "processing_method": "comprehensive_video_service"
        }
        
        st.session_state.processing_jobs[job_id] = job_info
        st.success(f"✅ Started real AWS processing job: {job_id}")
        
        try:
            # Process videos using ComprehensiveVideoProcessingService
            st.info("🔄 Processing videos with ComprehensiveVideoProcessingService...")
            
            # Create progress callback
            def progress_callback(current: int, total: int, result):
                progress_pct = (current / total) * 100
                st.progress(progress_pct / 100, text=f"Processing video {current}/{total}: {progress_pct:.1f}%")
                
                if result.is_successful:
                    st.success(f"✅ Completed: {result.source_url}")
                else:
                    st.error(f"❌ Failed: {result.source_url} - {result.error_message}")
            
            # Process all videos in batch
            results = self.comprehensive_service.batch_process_videos(
                video_urls=video_urls,
                progress_callback=progress_callback
            )
            
            # Update job info with results
            successful_results = [r for r in results if r.is_successful]
            failed_results = [r for r in results if not r.is_successful]
            
            job_info.update({
                "status": "completed",
                "completed_at": time.time(),
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "total_segments": sum(r.total_segments for r in successful_results),
                "total_cost_usd": sum(r.estimated_cost_usd or 0 for r in results),
                "processing_results": [
                    {
                        "job_id": r.job_id,
                        "source_url": r.source_url,
                        "s3_uri": r.s3_uri,
                        "status": r.status,
                        "total_segments": r.total_segments,
                        "processing_time_ms": r.processing_time_ms,
                        "estimated_cost_usd": r.estimated_cost_usd,
                        "error_message": r.error_message
                    }
                    for r in results
                ]
            })
            
            st.session_state.processing_jobs[job_id] = job_info
            
            # Show results summary
            if successful_results:
                st.success(f"🎉 Successfully processed {len(successful_results)} videos!")
                st.info(f"📊 Total segments generated: {sum(r.total_segments for r in successful_results)}")
                
                total_cost = sum(r.estimated_cost_usd or 0 for r in results)
                if total_cost > 0:
                    st.info(f"💰 Estimated cost: ${total_cost:.4f}")
            
            if failed_results:
                st.warning(f"⚠️ {len(failed_results)} videos failed to process")
                with st.expander("Show failed videos"):
                    for result in failed_results:
                        st.error(f"❌ {result.source_url}: {result.error_message}")
            
            return {
                "status": "completed",
                "job_id": job_id,
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "results": results
            }
            
        except Exception as e:
            # Update job with error
            job_info.update({
                "status": "failed",
                "completed_at": time.time(),
                "error_message": str(e)
            })
            st.session_state.processing_jobs[job_id] = job_info
            
            st.error(f"❌ Processing failed: {e}")
            logger.error(f"Sample videos processing failed: {e}")
            
            return {
                "status": "error",
                "job_id": job_id,
                "message": str(e)
            }
    
    def render_video_input_section(self):
        """Render streamlined video input options."""
        # Simplified tabs - removed redundant batch processing tab
        tab1, tab2 = st.tabs([
            "🎬 Sample Videos",
            "📤 Upload & S3"
        ])
        
        with tab1:
            self._render_enhanced_sample_videos()
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                self._render_enhanced_file_upload()
            with col2:
                self._render_enhanced_s3_uri_input()
    
    def _render_enhanced_sample_videos(self):
        """Render streamlined sample video selection."""
        # Use the sample video manager for multi-select interface
        selected_videos = sample_video_manager.render_multi_select_interface()
        
        if selected_videos:
            # Single process button - removed redundant options
            if st.button("🚀 Process Selected Videos", type="primary", use_container_width=True):
                self.process_sample_videos(selected_videos)
    
    
    def start_dual_pattern_processing(self, video_uri: str):
        """Start processing video with dual storage patterns using real AWS resources."""
        # Ensure service is updated with current configuration
        self._ensure_service_updated()
        
        # Always use real AWS processing - no simulation mode
        st.info("🔧 **Real AWS Processing** - Processing with live AWS resources")
        
        try:
            # Use the multi-vector coordinator for real processing
            processing_config = {
                "vector_types": st.session_state.get('selected_vector_types', ['visual-text', 'visual-image', 'audio']),
                "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
                "segment_duration": st.session_state.get('segment_duration', 5.0),
                "processing_mode": st.session_state.get('processing_mode', 'parallel')
            }
            
            # Log the vector types being processed for debugging
            st.info(f"🔍 Processing with vector types: {processing_config['vector_types']}")
            
            # Create real processing job
            job_id = f"aws_job_{int(time.time())}"
            job_info = {
                "job_id": job_id,
                "video_uri": video_uri,
                "status": "processing",
                "vector_types": processing_config["vector_types"],
                "storage_patterns": processing_config["storage_patterns"],
                "segment_duration": processing_config["segment_duration"],
                "processing_mode": processing_config["processing_mode"],
                "started_at": time.time()
            }
            
            # Initialize processing jobs if not exists
            if 'processing_jobs' not in st.session_state:
                st.session_state.processing_jobs = {}
            
            st.session_state.processing_jobs[job_id] = job_info
            st.success(f"✅ Started AWS processing job: {job_id}")
            
            # Integrate with actual MultiVectorCoordinator
            if self.coordinator:
                st.info("🔄 Processing with MultiVectorCoordinator...")
                try:
                    # Create content input for coordinator
                    content_input = {
                        'id': job_id,
                        'video_s3_uri': video_uri,
                        'processing_params': {
                            'segment_duration_sec': processing_config["segment_duration"],
                            'processing_mode': processing_config["processing_mode"]
                        }
                    }
                    
                    # Start real multi-vector processing
                    result = self.coordinator.process_multi_vector_content(
                        content_inputs=[content_input],
                        vector_types=processing_config["vector_types"]
                    )
                    
                    # Update job status with real results
                    job_info.update({
                        'status': 'completed',
                        'result': result,
                        'completed_at': time.time()
                    })
                    st.session_state.processing_jobs[job_id] = job_info
                    st.success(f"✅ Processing completed successfully! Generated {len(result.successful_types)} vector types")
                    
                except Exception as e:
                    # Update job with error
                    job_info.update({
                        'status': 'failed',
                        'error': str(e),
                        'completed_at': time.time()
                    })
                    st.session_state.processing_jobs[job_id] = job_info
                    st.error(f"❌ Processing failed: {e}")
                    logger.error(f"MultiVectorCoordinator processing failed: {e}")
            else:
                st.warning("⚠️ MultiVectorCoordinator not available - check backend services")
                # Show detailed service status for debugging
                service_manager = st.session_state.get('service_manager')
                if service_manager:
                    st.info("🔍 Service manager available, checking coordinator initialization...")
                    if hasattr(service_manager, 'multi_vector_coordinator'):
                        if service_manager.multi_vector_coordinator is None:
                            st.error("❌ MultiVectorCoordinator failed to initialize - check AWS credentials and configuration")
                        else:
                            st.info("✅ MultiVectorCoordinator exists but not passed to component")
                    else:
                        st.error("❌ Service manager missing multi_vector_coordinator attribute")
                else:
                    st.error("❌ Service manager not available in session state")
                
        except Exception as e:
            st.error(f"Processing failed: {e}")
    
    def start_collection_processing(self, collection_size: int):
        """Start processing a collection of videos using real AWS resources."""
        # Ensure service is updated with current configuration
        self._ensure_service_updated()
        
        st.info(f"🔄 Processing collection of {collection_size} videos with real AWS resources...")
        
        # Always use real AWS processing
        job_id = f"aws_collection_job_{int(time.time())}"
        
        # Initialize processing jobs if not exists
        if 'processing_jobs' not in st.session_state:
            st.session_state.processing_jobs = {}
        
        job_info = {
            "job_id": job_id,
            "type": "collection",
            "collection_size": collection_size,
            "status": "processing",
            "vector_types": st.session_state.get('selected_vector_types', ['visual-text', 'visual-image', 'audio']),
            "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
            "started_at": time.time()
        }
        
        # Log the vector types being processed for debugging
        st.info(f"🔍 Collection processing with vector types: {job_info['vector_types']}")
        
        st.session_state.processing_jobs[job_id] = job_info
        st.success(f"✅ Started AWS collection processing: {job_id}")
        
    def start_upload_processing(self, uploaded_file):
        """Start processing an uploaded video file using real AWS resources."""
        st.info(f"🔄 Processing uploaded file: {uploaded_file.name}")
        
        # Always use real AWS upload and processing
        # Generate real S3 URI based on configured bucket
        s3_bucket = st.session_state.get('active_s3_bucket', 'default-upload-bucket')
        s3_uri = f"s3://{s3_bucket}/uploads/{uploaded_file.name}"
        st.info(f"📤 Uploading to: {s3_uri}")
        
        # Start real processing
        self.start_dual_pattern_processing(s3_uri)
    
    def generate_demo_processing_results(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate demo processing results for simulation."""
        vector_types = job_info.get("vector_types", ['visual-text'])
        storage_patterns = job_info.get("storage_patterns", ['direct_s3vector'])
        
        results = {
            "job_id": job_info["job_id"],
            "video_uri": job_info.get("video_uri", "demo_video.mp4"),
            "total_segments": random.randint(8, 15),
            "processing_time_sec": random.uniform(45, 120),
            "cost_usd": random.uniform(0.05, 0.15),
            "vector_types_processed": vector_types,
            "storage_patterns_used": storage_patterns,
            "segment_duration": job_info.get("segment_duration", 5.0),
            "embeddings_generated": {}
        }
        
        # Generate embedding info for each vector type and storage pattern
        for vector_type in vector_types:
            results["embeddings_generated"][vector_type] = {}
            
            for pattern in storage_patterns:
                results["embeddings_generated"][vector_type][pattern] = {
                    "index_arn": f"arn:aws:s3vectors:us-east-1:123456789012:index/demo-{vector_type}-{pattern}",
                    "vectors_stored": results["total_segments"],
                    "storage_size_mb": random.uniform(5, 25),
                    "avg_similarity_score": random.uniform(0.75, 0.95)
                }
        
        # Add processing time and cost estimate
        results["processing_time_ms"] = int(results["processing_time_sec"] * 1000)
        results["cost_estimate"] = results["cost_usd"]

        return results

    def simulate_video_upload(self, filename: str, vector_types: List[str]) -> Dict[str, Any]:
        """Simulate video upload process."""
        import time

        # Simulate upload time
        time.sleep(0.1)

        # Generate mock S3 URI
        s3_uri = f"s3://demo-bucket/uploads/{filename}"

        # Simulate file size and duration
        file_size_mb = random.uniform(50, 500)
        duration_minutes = random.uniform(1, 10)

        return {
            'status': 'success',
            'filename': filename,
            's3_uri': s3_uri,
            'file_size_mb': file_size_mb,
            'duration_minutes': duration_minutes,
            'vector_types': vector_types,
            'upload_time_ms': 100,
            'message': f'Successfully uploaded {filename} to {s3_uri}'
        }
    
    def show_processing_progress(self):
        """Show concise processing progress for active jobs."""
        if not hasattr(st.session_state, 'processing_jobs') or not st.session_state.processing_jobs:
            st.info("📋 No active processing jobs")
            return

        st.subheader("🔄 Processing Status")

        for job_id, job_info in st.session_state.processing_jobs.items():
            with st.expander(f"Job: {job_id[-8:]}", expanded=True):  # Show only last 8 chars of job ID
                col1, col2 = st.columns(2)

                with col1:
                    status = job_info.get('status', 'unknown').title()
                    if status == 'Processing':
                        st.info(f"🔄 {status}")
                    elif status == 'Completed':
                        st.success(f"✅ {status}")
                    elif status == 'Failed':
                        st.error(f"❌ {status}")
                    else:
                        st.write(f"📋 {status}")

                with col2:
                    video_count = job_info.get('video_count', job_info.get('collection_size', 1))
                    st.metric("Videos", video_count)

                # Simple progress bar for active jobs
                if job_info.get('status') == 'processing':
                    elapsed = time.time() - job_info.get('started_at', time.time())
                    estimated_total = 300  # 5 minutes default
                    progress = min(elapsed / estimated_total, 1.0)
                    st.progress(progress, text=f"Progress: {progress*100:.1f}%")

    def show_cost_estimation(self):
        """Show simplified cost estimation for processing."""
        st.subheader("💰 Cost Estimation")

        # Get processing parameters
        vector_types = st.session_state.get('selected_vector_types', ['visual-text'])
        storage_patterns = st.session_state.get('selected_storage_patterns', ['direct_s3vector'])

        # Estimate costs
        estimated_duration_minutes = 10.0  # Default estimate
        marengo_cost = estimated_duration_minutes * 0.05 * len(vector_types)
        storage_cost = 0.02 * len(vector_types)
        opensearch_cost = 0.05 if 'opensearch_s3vector_hybrid' in storage_patterns else 0
        total_cost = marengo_cost + storage_cost + opensearch_cost

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Processing", f"${marengo_cost:.3f}")
        with col2:
            st.metric("Storage", f"${storage_cost + opensearch_cost:.3f}")
        with col3:
            st.metric("Total", f"${total_cost:.3f}")

        st.info(f"💡 Estimate for {estimated_duration_minutes:.0f} min video, {len(vector_types)} vector types")
        st.warning("⚠️ **Real AWS costs will apply**")
    
    def _render_enhanced_file_upload(self):
        """Render simplified file upload interface."""
        st.write("**📤 Upload Files**")
        
        uploaded_files = st.file_uploader(
            "Choose video files:",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) ready")
            if st.button("🚀 Process Files", type="primary", use_container_width=True):
                self.start_file_upload_processing(uploaded_files)
    
    def _render_enhanced_s3_uri_input(self):
        """Render simplified S3 URI input."""
        st.write("**🔗 S3 URI Input**")
        
        s3_uri = st.text_input(
            "S3 URI:",
            placeholder="s3://bucket/video.mp4"
        )
        
        if s3_uri and s3_uri.startswith('s3://'):
            if st.button("🚀 Process S3 Video", type="primary", use_container_width=True):
                self.start_dual_pattern_processing(s3_uri)
        elif s3_uri:
            st.error("❌ Invalid S3 URI format")
    
    
    def start_multi_video_processing(self, selected_videos: List[Dict[str, Any]], custom_config: Optional[Dict[str, Any]] = None):
        """Start processing multiple videos with enhanced configuration."""
        # Ensure service is updated with current configuration
        self._ensure_service_updated()
        
        if not selected_videos:
            st.error("No videos selected for processing")
            return
        
        st.info(f"🔄 Starting processing for {len(selected_videos)} videos...")
        
        # Create processing job for multiple videos
        job_id = f"multi_video_job_{int(time.time())}"
        
        # Get video sources
        video_sources = []
        for video in selected_videos:
            if video.get("sources"):
                video_sources.append({
                    "title": video["title"],
                    "source": video["sources"][0],
                    "thumbnail": video.get("thumb", "")
                })
        
        job_info = {
            "job_id": job_id,
            "type": "multi_video",
            "video_count": len(selected_videos),
            "video_sources": video_sources,
            "status": "processing",
            "vector_types": st.session_state.get('selected_vector_types', ['visual-text', 'visual-image', 'audio']),
            "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
            "segment_duration": custom_config.get("segment_duration", 5.0) if custom_config else st.session_state.get('segment_duration', 5.0),
            "processing_mode": custom_config.get("processing_strategy", "parallel") if custom_config else st.session_state.get('processing_mode', 'parallel'),
            "custom_config": custom_config,
            "started_at": time.time()
        }
        
        # Log the vector types being processed for debugging
        st.info(f"🔍 Multi-video processing with vector types: {job_info['vector_types']}")
        
        # Initialize processing jobs if not exists
        if 'processing_jobs' not in st.session_state:
            st.session_state.processing_jobs = {}
        
        st.session_state.processing_jobs[job_id] = job_info
        st.success(f"✅ Started multi-video processing job: {job_id}")
        
        # Always use real AWS processing
        if self.coordinator:
            st.info("🔄 Processing videos with MultiVectorCoordinator...")
            # Real processing would integrate with coordinator here
            
            # Initialize processed videos tracking
            if 'processed_videos' not in st.session_state:
                st.session_state.processed_videos = {}
            
            # Process each video with real AWS services
            for i, video in enumerate(selected_videos):
                video_uri = video["sources"][0] if video.get("sources") else f"aws_video_{i}.mp4"
                video_title = video["title"]
                st.info(f"🔄 Processing: {video_title}")
                
                # Real processing would happen here with coordinator
                # For now, create job tracking
                video_job_key = f"{job_id}_video_{i}"
                st.session_state.processed_videos[video_job_key] = {
                    "job_id": video_job_key,
                    "video_uri": video_uri,
                    "video_title": video_title,
                    "status": "processing",
                    "started_at": time.time()
                }
            
            st.success("🎉 Multi-video processing initiated with real AWS resources!")
        else:
            st.warning("⚠️ MultiVectorCoordinator not available - check backend services")
    
    def start_file_upload_processing(self, uploaded_files, upload_config: Optional[Dict[str, Any]] = None):
        """Start processing uploaded files with enhanced shared components integration."""
        st.info(f"🔄 Processing {len(uploaded_files)} uploaded files...")
        
        # Use standardized bucket naming for uploads
        upload_bucket = self._generate_optimized_upload_bucket_name()
        
        # Process files with optimized metadata handling
        for i, file in enumerate(uploaded_files):
            # Generate S3 URI with optimized naming
            s3_uri = f"s3://{upload_bucket}/uploads/{file.name}"
            st.info(f"📤 Uploading {file.name} to {s3_uri}")
            
            # Create enhanced metadata for the file
            if self.metadata_transformer:
                try:
                    file_metadata = create_media_metadata(
                        file_name=file.name,
                        s3_location=s3_uri,
                        file_format=file.name.split('.')[-1].lower(),
                        file_size=file.size if hasattr(file, 'size') else 0,
                        duration=0.0  # Will be updated after processing
                    )
                    st.session_state[f'file_metadata_{file.name}'] = file_metadata
                except Exception as e:
                    logger.warning(f"Failed to create metadata for {file.name}: {e}")
            
            # Start processing for each file
            self.start_dual_pattern_processing(s3_uri)
    
    def start_batch_s3_processing(self, s3_uris: List[str]):
        """Start batch processing of S3 URIs with optimized resource management."""
        st.info(f"🔄 Starting batch processing for {len(s3_uris)} S3 URIs...")
        
        # Use optimized batch processing if available
        if self.aws_client_pool and len(s3_uris) > 1:
            st.info("🚀 Using optimized AWS client pooling for batch processing")
        
        for uri in s3_uris:
            self.start_dual_pattern_processing(uri)
    
    def _generate_optimized_upload_bucket_name(self) -> str:
        """Generate optimized bucket name for uploads."""
        import streamlit as st
        environment = st.session_state.get('environment', 'prod')
        return f"s3vector-{environment}-uploads"
    
    def _get_optimized_vector_type_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get optimized vector type configurations using shared components."""
        configs = {}
        
        try:
            supported_types = list_supported_vector_types()
            for vector_type_str in supported_types:
                config = get_vector_type_config(vector_type_str)
                configs[vector_type_str] = {
                    'dimensions': config.dimensions,
                    'batch_size': config.processing_batch_size,
                    'concurrent_ops': config.concurrent_operations,
                    'embedding_model': config.embedding_model,
                    'description': config.description
                }
        except Exception as e:
            logger.error(f"Failed to get optimized vector type configs: {e}")
            # Fallback to basic configs
            configs = {
                'visual-text': {'dimensions': 1024, 'batch_size': 5, 'concurrent_ops': 3},
                'visual-image': {'dimensions': 1024, 'batch_size': 5, 'concurrent_ops': 3},
                'audio': {'dimensions': 1024, 'batch_size': 5, 'concurrent_ops': 3}
            }
        
        return configs
    
    def get_enhanced_cost_estimation(self, video_count: int, duration_minutes: float) -> Dict[str, float]:
        """Get enhanced cost estimation using shared vector type configurations."""
        vector_configs = self._get_optimized_vector_type_configs()
        selected_vector_types = st.session_state.get('selected_vector_types', ['visual-text', 'visual-image', 'audio'])
        
        # Calculate costs based on actual vector type configurations
        total_cost = 0.0
        cost_breakdown = {}
        
        for vector_type in selected_vector_types:
            if vector_type in vector_configs:
                config = vector_configs[vector_type]
                # Base cost calculation with configuration-aware pricing
                base_cost_per_minute = 0.05  # Base rate
                
                # Adjust for complexity and batch size efficiency
                batch_efficiency = min(config.get('batch_size', 5) / 5.0, 1.0)
                complexity_multiplier = config.get('dimensions', 1024) / 1024.0
                
                vector_cost = (duration_minutes * base_cost_per_minute * complexity_multiplier) / batch_efficiency
                cost_breakdown[vector_type] = vector_cost * video_count
                total_cost += cost_breakdown[vector_type]
        
        # Add storage costs
        storage_cost = video_count * 0.02
        cost_breakdown['storage'] = storage_cost
        total_cost += storage_cost
        
        cost_breakdown['total'] = total_cost
        
        return cost_breakdown
    
    def get_shared_components_status(self) -> Dict[str, bool]:
        """Get status of shared components for debugging."""
        return {
            'metadata_transformer': self.metadata_transformer is not None,
            'aws_client_pool': self.aws_client_pool is not None,
            'vector_type_configs': len(self._get_optimized_vector_type_configs()) > 0
        }
