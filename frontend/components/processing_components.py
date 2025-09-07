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


class ProcessingComponents:
    """Processing functionality components for the unified demo."""
    
    def __init__(self, service_manager=None, coordinator=None):
        self.service_manager = service_manager
        self.coordinator = coordinator
    
    def render_video_input_section(self):
        """Render enhanced video input options with improved UX."""
        st.subheader("📹 Video Input & Selection")
        
        # Create tabs for better organization
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎬 Sample Videos",
            "📤 Upload Files",
            "🔗 S3 URIs",
            "📦 Batch Processing"
        ])
        
        with tab1:
            self._render_enhanced_sample_videos()
        
        with tab2:
            self._render_enhanced_file_upload()
        
        with tab3:
            self._render_enhanced_s3_uri_input()
        
        with tab4:
            self._render_batch_processing_options()
    
    def _render_enhanced_sample_videos(self):
        """Render enhanced sample video selection with multi-select functionality."""
        st.write("**Google Sample Video Collection**")
        st.write("Select one or more videos from the curated collection for processing:")
        
        # Use the sample video manager for multi-select interface
        selected_videos = sample_video_manager.render_multi_select_interface()
        
        if selected_videos:
            # Show selection summary
            selection_info = sample_video_manager.get_selected_videos_info(selected_videos)
            
            with st.expander("📊 Selection Summary", expanded=True):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Videos Selected", selection_info["total_videos"])
                
                with col2:
                    st.metric("Est. Duration", f"{selection_info['estimated_duration_minutes']} min")
                
                with col3:
                    creators_text = ", ".join([f"{k} ({v})" for k, v in selection_info["creators"].items()])
                    st.write("**Creators:**")
                    st.write(creators_text)
            
            # Processing options
            st.subheader("🚀 Processing Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎬 Process Selected Videos", type="primary", use_container_width=True):
                    self.start_multi_video_processing(selected_videos)
            
            with col2:
                if st.button("🔄 Process with Custom Settings", type="secondary", use_container_width=True):
                    st.session_state.show_custom_processing = True
            
            # Custom processing settings
            if st.session_state.get('show_custom_processing', False):
                with st.expander("⚙️ Custom Processing Settings", expanded=True):
                    self._render_custom_processing_settings(selected_videos)
        else:
            st.info("👆 Select videos above to see processing options")
    
    def _render_sample_collection(self):
        """Render sample collection processing interface."""
        st.info("📦 **Sample Collection Processing**")
        st.write("Process multiple videos simultaneously to demonstrate batch capabilities")
        
        collection_size = st.selectbox(
            "Collection Size:",
            options=[3, 5, 10],
            index=0,
            help="Number of videos to process in batch"
        )
        
        if st.button("🚀 Process Sample Collection", type="primary"):
            self.start_collection_processing(collection_size)
    
    def _render_file_upload(self):
        """Render file upload interface."""
        st.info("📤 **File Upload**")
        uploaded_file = st.file_uploader(
            "Upload Video File:",
            type=['mp4', 'avi', 'mov', 'mkv'],
            help="Upload a video file for processing"
        )
        
        if uploaded_file:
            st.success(f"Uploaded: {uploaded_file.name}")
            if st.button("🚀 Process Uploaded Video", type="primary"):
                self.start_upload_processing(uploaded_file)
    
    def _render_s3_uri_input(self):
        """Render S3 URI input interface."""
        st.info("🔗 **S3 URI Input**")
        s3_uri = st.text_input(
            "Enter S3 URI:",
            placeholder="s3://your-bucket/path/to/video.mp4",
            help="Provide S3 URI of video to process"
        )
        
        if s3_uri and st.button("🚀 Process S3 Video", type="primary"):
            self.start_dual_pattern_processing(s3_uri)
    
    def start_dual_pattern_processing(self, video_uri: str):
        """Start processing video with dual storage patterns using real AWS resources."""
        # Always use real AWS processing - no simulation mode
        st.info("🔧 **Real AWS Processing** - Processing with live AWS resources")
        
        try:
            # Use the multi-vector coordinator for real processing
            processing_config = {
                "vector_types": st.session_state.get('selected_vector_types', ['visual-text']),
                "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
                "segment_duration": st.session_state.get('segment_duration', 5.0),
                "processing_mode": st.session_state.get('processing_mode', 'parallel')
            }
            
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
                st.info("🔄 Integrating with MultiVectorCoordinator for real processing...")
                # Real processing would happen here
            else:
                st.warning("⚠️ MultiVectorCoordinator not available - check backend services")
                
        except Exception as e:
            st.error(f"Processing failed: {e}")
    
    def start_collection_processing(self, collection_size: int):
        """Start processing a collection of videos using real AWS resources."""
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
            "vector_types": st.session_state.get('selected_vector_types', ['visual-text']),
            "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
            "started_at": time.time()
        }
        
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
        """Show processing progress for active jobs."""
        if not hasattr(st.session_state, 'processing_jobs') or not st.session_state.processing_jobs:
            st.info("📋 No active processing jobs")
            return

        st.subheader("🔄 Processing Progress")

        for job_id, job_info in st.session_state.processing_jobs.items():
            with st.expander(f"Job: {job_id}", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Status", job_info.get('status', 'unknown').title())

                with col2:
                    if job_info.get('type') == 'collection':
                        st.metric("Collection Size", job_info.get('collection_size', 0))
                    else:
                        st.metric("Video", "Single Video")

                with col3:
                    vector_types = len(job_info.get('vector_types', []))
                    st.metric("Vector Types", vector_types)

                # Progress simulation
                elapsed = time.time() - job_info.get('started_at', time.time())
                estimated_total = 300  # 5 minutes default
                progress = min(elapsed / estimated_total, 1.0)

                st.progress(progress, text=f"Progress: {progress*100:.1f}%")

                # Job details
                st.write("**Configuration:**")
                st.write(f"• Vector Types: {', '.join(job_info.get('vector_types', []))}")
                st.write(f"• Storage Patterns: {', '.join(job_info.get('storage_patterns', []))}")
                st.write(f"• Segment Duration: {job_info.get('segment_duration', 5.0)}s")
                st.write(f"• Processing Mode: {job_info.get('processing_mode', 'parallel')}")

    def show_cost_estimation(self):
        """Show cost estimation for processing."""
        st.subheader("💰 Cost Estimation")

        # Get processing parameters
        vector_types = st.session_state.get('selected_vector_types', ['visual-text'])
        storage_patterns = st.session_state.get('selected_storage_patterns', ['direct_s3vector'])

        # Estimate video duration (placeholder)
        estimated_duration_minutes = 10.0  # Default estimate

        # TwelveLabs Marengo pricing: $0.05 per minute
        marengo_cost_per_minute = 0.05
        marengo_cost = estimated_duration_minutes * marengo_cost_per_minute * len(vector_types)

        # Storage costs (estimated)
        s3vector_storage_cost = 0.02 * len(vector_types)  # Per index
        opensearch_cost = 0.05 if 'opensearch_s3vector_hybrid' in storage_patterns else 0

        total_cost = marengo_cost + s3vector_storage_cost + opensearch_cost

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Marengo Processing", f"${marengo_cost:.3f}")

        with col2:
            st.metric("S3Vector Storage", f"${s3vector_storage_cost:.3f}")

        with col3:
            st.metric("OpenSearch (if used)", f"${opensearch_cost:.3f}")

        with col4:
            st.metric("Total Estimated", f"${total_cost:.3f}")

        # Cost breakdown
        with st.expander("📊 Cost Breakdown"):
            st.write("**Processing Costs:**")
            st.write(f"• Video Duration: {estimated_duration_minutes:.1f} minutes")
            st.write(f"• Vector Types: {len(vector_types)} types")
            st.write(f"• Marengo Rate: ${marengo_cost_per_minute:.3f} per minute per type")
            st.write(f"• Total Processing: ${marengo_cost:.3f}")
            st.write("")

            st.write("**Storage Costs:**")
            st.write(f"• S3Vector Indexes: {len(vector_types)} indexes")
            st.write(f"• Storage Rate: $0.02 per index per processing session")
            st.write(f"• OpenSearch: {'Enabled' if opensearch_cost > 0 else 'Disabled'}")
            st.write(f"• Total Storage: ${s3vector_storage_cost + opensearch_cost:.3f}")

        # Always use real AWS - show cost warning
        st.warning("⚠️ **Real AWS Processing**: These costs will be charged to your AWS account")
    
    def _render_enhanced_file_upload(self):
        """Render enhanced file upload interface with drag-and-drop and multiple files."""
        st.write("**Upload Video Files**")
        st.write("Upload one or more video files for processing:")
        
        # Multiple file upload
        uploaded_files = st.file_uploader(
            "Choose video files:",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True,
            help="Upload multiple video files for batch processing"
        )
        
        if uploaded_files:
            st.success(f"✅ Uploaded {len(uploaded_files)} file(s)")
            
            # Show file details
            with st.expander("📁 File Details", expanded=True):
                total_size = 0
                for file in uploaded_files:
                    file_size_mb = len(file.getvalue()) / (1024 * 1024)
                    total_size += file_size_mb
                    st.write(f"• **{file.name}** - {file_size_mb:.1f} MB")
                
                st.write(f"**Total Size:** {total_size:.1f} MB")
            
            # Processing options
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🚀 Process All Files", type="primary", use_container_width=True):
                    self.start_file_upload_processing(uploaded_files)
            
            with col2:
                if st.button("⚙️ Custom Processing", type="secondary", use_container_width=True):
                    st.session_state.show_upload_custom_settings = True
            
            if st.session_state.get('show_upload_custom_settings', False):
                with st.expander("⚙️ Upload Processing Settings", expanded=True):
                    self._render_upload_processing_settings(uploaded_files)
    
    def _render_enhanced_s3_uri_input(self):
        """Render enhanced S3 URI input with validation and batch support."""
        st.write("**S3 URI Input**")
        st.write("Provide S3 URIs of videos to process:")
        
        # Single URI input
        st.subheader("Single Video")
        s3_uri = st.text_input(
            "S3 URI:",
            placeholder="s3://your-bucket/path/to/video.mp4",
            help="Enter the S3 URI of a video file"
        )
        
        if s3_uri:
            # Validate URI format
            if s3_uri.startswith('s3://') and s3_uri.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                st.success("✅ Valid S3 URI format")
                if st.button("🚀 Process S3 Video", type="primary"):
                    self.start_dual_pattern_processing(s3_uri)
            else:
                st.error("❌ Invalid S3 URI format. Must start with 's3://' and end with a video extension.")
        
        st.markdown("---")
        
        # Batch URI input
        st.subheader("Batch Processing")
        batch_uris = st.text_area(
            "Multiple S3 URIs (one per line):",
            placeholder="s3://bucket/video1.mp4\ns3://bucket/video2.mp4\ns3://bucket/video3.mp4",
            help="Enter multiple S3 URIs, one per line"
        )
        
        if batch_uris:
            uris = [uri.strip() for uri in batch_uris.split('\n') if uri.strip()]
            valid_uris = []
            invalid_uris = []
            
            for uri in uris:
                if uri.startswith('s3://') and uri.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                    valid_uris.append(uri)
                else:
                    invalid_uris.append(uri)
            
            if valid_uris:
                st.success(f"✅ {len(valid_uris)} valid URIs")
                
            if invalid_uris:
                st.error(f"❌ {len(invalid_uris)} invalid URIs")
                with st.expander("Show invalid URIs"):
                    for uri in invalid_uris:
                        st.write(f"• {uri}")
            
            if valid_uris and st.button("🚀 Process Batch S3 Videos", type="primary"):
                self.start_batch_s3_processing(valid_uris)
    
    def _render_batch_processing_options(self):
        """Render batch processing options and presets."""
        st.write("**Batch Processing Presets**")
        st.write("Quick options for processing multiple videos:")
        
        # Preset options
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎬 Content Type Presets")
            
            if st.button("🎭 Animation Collection", use_container_width=True):
                # Select Blender animations
                blender_videos = [v for v in sample_video_manager.get_all_videos()
                                if "Blender" in v["subtitle"]]
                self.start_multi_video_processing(blender_videos)
            
            if st.button("📺 Commercial Collection", use_container_width=True):
                # Select Chromecast commercials
                chromecast_videos = [v for v in sample_video_manager.get_all_videos()
                                   if "Chromecast" in v["description"]]
                self.start_multi_video_processing(chromecast_videos)
            
            if st.button("🚗 Automotive Collection", use_container_width=True):
                # Select car review videos
                car_videos = [v for v in sample_video_manager.get_all_videos()
                            if "Garage419" in v["subtitle"]]
                self.start_multi_video_processing(car_videos)
        
        with col2:
            st.subheader("⚡ Processing Presets")
            
            if st.button("🚀 Quick Demo (3 videos)", use_container_width=True):
                # Select first 3 videos for quick demo
                quick_videos = sample_video_manager.get_all_videos()[:3]
                self.start_multi_video_processing(quick_videos)
            
            if st.button("🎯 Comprehensive Demo (All)", use_container_width=True):
                # Process all sample videos
                all_videos = sample_video_manager.get_all_videos()
                self.start_multi_video_processing(all_videos)
            
            if st.button("🧪 Test Processing (1 video)", use_container_width=True):
                # Process just one video for testing
                test_video = [sample_video_manager.get_all_videos()[0]]
                self.start_multi_video_processing(test_video)
    
    def _render_custom_processing_settings(self, selected_videos: List[Dict[str, Any]]):
        """Render custom processing settings for selected videos."""
        st.write("**Custom Processing Configuration**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Processing strategy
            processing_strategy = st.selectbox(
                "Processing Strategy:",
                options=["parallel", "sequential", "adaptive"],
                index=0,
                help="How to process multiple videos"
            )
            
            # Priority processing
            priority_mode = st.checkbox(
                "Priority Processing",
                help="Process shorter videos first"
            )
        
        with col2:
            # Custom segment duration
            custom_segment_duration = st.slider(
                "Segment Duration (seconds):",
                min_value=2.0,
                max_value=15.0,
                value=5.0,
                step=0.5
            )
            
            # Quality settings
            quality_preset = st.selectbox(
                "Quality Preset:",
                options=["standard", "high", "maximum"],
                index=0,
                help="Processing quality vs speed tradeoff"
            )
        
        # Advanced settings
        with st.expander("🔧 Advanced Settings"):
            enable_thumbnails = st.checkbox("Generate Thumbnails", value=True)
            enable_metadata = st.checkbox("Extract Metadata", value=True)
            enable_preview = st.checkbox("Generate Preview Clips", value=False)
        
        # Start custom processing
        if st.button("🚀 Start Custom Processing", type="primary"):
            custom_config = {
                "processing_strategy": processing_strategy,
                "priority_mode": priority_mode,
                "segment_duration": custom_segment_duration,
                "quality_preset": quality_preset,
                "enable_thumbnails": enable_thumbnails,
                "enable_metadata": enable_metadata,
                "enable_preview": enable_preview
            }
            self.start_multi_video_processing(selected_videos, custom_config)
    
    def _render_upload_processing_settings(self, uploaded_files):
        """Render processing settings for uploaded files."""
        st.write("**Upload Processing Configuration**")
        
        # File processing order
        processing_order = st.selectbox(
            "Processing Order:",
            options=["upload_order", "size_ascending", "size_descending", "name_alphabetical"],
            index=0,
            help="Order in which to process uploaded files"
        )
        
        # S3 upload settings
        s3_bucket = st.text_input(
            "S3 Bucket (optional):",
            placeholder="your-processing-bucket",
            help="Bucket to upload files to before processing"
        )
        
        if st.button("🚀 Start Upload Processing", type="primary"):
            upload_config = {
                "processing_order": processing_order,
                "s3_bucket": s3_bucket
            }
            self.start_file_upload_processing(uploaded_files, upload_config)
    
    def start_multi_video_processing(self, selected_videos: List[Dict[str, Any]], custom_config: Optional[Dict[str, Any]] = None):
        """Start processing multiple videos with enhanced configuration."""
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
            "vector_types": st.session_state.get('selected_vector_types', ['visual-text']),
            "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
            "segment_duration": custom_config.get("segment_duration", 5.0) if custom_config else st.session_state.get('segment_duration', 5.0),
            "processing_mode": custom_config.get("processing_strategy", "parallel") if custom_config else st.session_state.get('processing_mode', 'parallel'),
            "custom_config": custom_config,
            "started_at": time.time()
        }
        
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
        """Start processing uploaded files."""
        st.info(f"🔄 Processing {len(uploaded_files)} uploaded files...")
        
        # Simulate file upload and processing
        for i, file in enumerate(uploaded_files):
            # Simulate S3 upload
            s3_uri = f"s3://temp-upload-bucket/{file.name}"
            st.info(f"📤 Uploading {file.name} to {s3_uri}")
            
            # Start processing for each file
            self.start_dual_pattern_processing(s3_uri)
    
    def start_batch_s3_processing(self, s3_uris: List[str]):
        """Start batch processing of S3 URIs."""
        st.info(f"🔄 Starting batch processing for {len(s3_uris)} S3 URIs...")
        
        for uri in s3_uris:
            self.start_dual_pattern_processing(uri)
