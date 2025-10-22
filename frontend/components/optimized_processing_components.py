"""
Optimized Processing Components for S3Vector Frontend

This module provides streamlined video processing components focused on
Marengo 2.7 model with improved user experience and simplified workflows.

Key Features:
- Marengo 2.7 exclusive processing
- Simplified upload interface
- Clear progress tracking
- Optimized batch processing
- Better error handling
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
import tempfile
import os

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class OptimizedProcessingComponents:
    """Optimized processing components for video content."""
    
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
        self.max_file_size_mb = 500
        self.max_duration_seconds = 3600  # 1 hour
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for processing."""
        if 'processing_state' not in st.session_state:
            st.session_state.processing_state = {
                'uploaded_files': [],
                'processing_queue': [],
                'completed_jobs': [],
                'failed_jobs': [],
                'current_job': None
            }
    
    def render_processing_interface(self):
        """Render the main processing interface."""
        st.subheader("🎬 Video Processing with Marengo 2.7")
        st.info("Process videos to generate multi-modal embeddings using Marengo 2.7 model")
        
        # Processing tabs
        tab1, tab2, tab3 = st.tabs([
            "📤 Upload & Process",
            "📊 Processing Status", 
            "📋 Job History"
        ])
        
        with tab1:
            self._render_upload_interface()
        
        with tab2:
            self._render_processing_status()
        
        with tab3:
            self._render_job_history()
    
    def _render_upload_interface(self):
        """Render video upload and processing configuration."""
        st.write("**📤 Upload Videos for Processing**")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Choose video files:",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True,
            help=f"Supported formats: {', '.join(self.supported_formats)}. Max size: {self.max_file_size_mb}MB per file"
        )
        
        if uploaded_files:
            self._display_uploaded_files(uploaded_files)
            
            # Processing configuration
            st.write("**⚙️ Processing Configuration**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                modalities = st.multiselect(
                    "Embedding Modalities:",
                    options=["visual-text", "visual-image", "audio"],
                    default=["visual-text", "audio"],
                    help="Choose which Marengo 2.7 embedding types to generate"
                )
            
            with col2:
                segment_duration = st.slider(
                    "Segment Duration (seconds):",
                    min_value=2.0,
                    max_value=10.0,
                    value=5.0,
                    step=0.5,
                    help="Duration of each video segment for embedding generation"
                )
            
            # Advanced options
            with st.expander("🔧 Advanced Options"):
                batch_size = st.slider(
                    "Batch Size:",
                    min_value=1,
                    max_value=10,
                    value=5,
                    help="Number of segments to process in parallel"
                )
                
                enable_metadata = st.checkbox(
                    "Extract Metadata",
                    value=True,
                    help="Extract video metadata (duration, resolution, etc.)"
                )
                
                storage_pattern = st.radio(
                    "Storage Pattern:",
                    options=["Direct S3Vector", "S3Vector + OpenSearch"],
                    index=0,
                    help="Choose how to store the generated embeddings"
                )
            
            # Process button
            if st.button("🚀 Start Processing", type="primary", disabled=not modalities):
                self._start_processing(uploaded_files, modalities, segment_duration, 
                                     batch_size, enable_metadata, storage_pattern)
    
    def _display_uploaded_files(self, uploaded_files):
        """Display information about uploaded files."""
        st.write(f"**📁 {len(uploaded_files)} file(s) uploaded:**")
        
        for i, file in enumerate(uploaded_files):
            file_size_mb = file.size / (1024 * 1024)
            
            with st.expander(f"📹 {file.name} ({file_size_mb:.1f} MB)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Size:** {file_size_mb:.1f} MB")
                    st.write(f"**Type:** {file.type}")
                
                with col2:
                    if file_size_mb > self.max_file_size_mb:
                        st.error(f"⚠️ File too large (max {self.max_file_size_mb}MB)")
                    else:
                        st.success("✅ File ready for processing")
    
    def _start_processing(self, uploaded_files, modalities, segment_duration, 
                         batch_size, enable_metadata, storage_pattern):
        """Start processing uploaded videos."""
        try:
            valid_files = [f for f in uploaded_files if f.size <= self.max_file_size_mb * 1024 * 1024]
            
            if not valid_files:
                st.error("❌ No valid files to process")
                return
            
            # Create processing jobs
            jobs = []
            for file in valid_files:
                job = {
                    'id': f"job_{int(time.time())}_{file.name}",
                    'filename': file.name,
                    'file_size': file.size,
                    'modalities': modalities,
                    'segment_duration': segment_duration,
                    'batch_size': batch_size,
                    'enable_metadata': enable_metadata,
                    'storage_pattern': storage_pattern,
                    'status': 'queued',
                    'created_at': datetime.now(),
                    'progress': 0
                }
                jobs.append(job)
            
            # Add to processing queue
            st.session_state.processing_state['processing_queue'].extend(jobs)
            
            st.success(f"✅ {len(jobs)} job(s) added to processing queue")
            
            # Start processing (in a real implementation, this would be async)
            self._process_jobs_demo(jobs)
            
        except Exception as e:
            logger.error(f"Failed to start processing: {e}")
            st.error(f"❌ Failed to start processing: {str(e)}")
    
    def _process_jobs_demo(self, jobs):
        """Demo processing simulation."""
        st.info("🔄 Processing started (demo mode)")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, job in enumerate(jobs):
            # Simulate processing
            status_text.text(f"Processing {job['filename']}...")
            
            for progress in range(0, 101, 10):
                time.sleep(0.1)  # Simulate processing time
                progress_bar.progress((i * 100 + progress) / (len(jobs) * 100))
                job['progress'] = progress
            
            # Mark as completed
            job['status'] = 'completed'
            job['completed_at'] = datetime.now()
            job['results'] = {
                'segments_processed': 12,
                'embeddings_generated': len(job['modalities']) * 12,
                'storage_location': f"s3://bucket/videos/{job['filename']}/",
                'processing_time_ms': 2500
            }
            
            # Move to completed
            st.session_state.processing_state['completed_jobs'].append(job)
        
        # Remove from queue
        for job in jobs:
            if job in st.session_state.processing_state['processing_queue']:
                st.session_state.processing_state['processing_queue'].remove(job)
        
        progress_bar.progress(1.0)
        status_text.text("✅ All jobs completed!")
        
        time.sleep(1)
        st.rerun()
    
    def _render_processing_status(self):
        """Render current processing status."""
        st.write("**📊 Processing Status**")
        
        queue = st.session_state.processing_state['processing_queue']
        current_job = st.session_state.processing_state.get('current_job')
        
        if not queue and not current_job:
            st.info("No active processing jobs")
            return
        
        # Current job
        if current_job:
            st.write("**🔄 Currently Processing:**")
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"📹 {current_job['filename']}")
                    st.progress(current_job.get('progress', 0) / 100)
                
                with col2:
                    st.metric("Progress", f"{current_job.get('progress', 0)}%")
        
        # Queue
        if queue:
            st.write(f"**⏳ Queue ({len(queue)} jobs):**")
            
            for job in queue[:5]:  # Show first 5 jobs
                with st.expander(f"📹 {job['filename']} - {job['status']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Modalities:** {', '.join(job['modalities'])}")
                        st.write(f"**Segment Duration:** {job['segment_duration']}s")
                    
                    with col2:
                        st.write(f"**File Size:** {job['file_size'] / (1024*1024):.1f} MB")
                        st.write(f"**Created:** {job['created_at'].strftime('%H:%M:%S')}")
            
            if len(queue) > 5:
                st.info(f"... and {len(queue) - 5} more jobs")
    
    def _render_job_history(self):
        """Render processing job history."""
        st.write("**📋 Job History**")
        
        completed = st.session_state.processing_state['completed_jobs']
        failed = st.session_state.processing_state['failed_jobs']
        
        if not completed and not failed:
            st.info("No completed jobs yet")
            return
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Completed Jobs", len(completed))
        
        with col2:
            st.metric("Failed Jobs", len(failed))
        
        with col3:
            total_embeddings = sum(job.get('results', {}).get('embeddings_generated', 0) for job in completed)
            st.metric("Total Embeddings", total_embeddings)
        
        # Job details
        all_jobs = completed + failed
        all_jobs.sort(key=lambda x: x.get('completed_at', x['created_at']), reverse=True)
        
        for job in all_jobs[:10]:  # Show last 10 jobs
            status_icon = "✅" if job['status'] == 'completed' else "❌"
            
            with st.expander(f"{status_icon} {job['filename']} - {job['status']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Status:** {job['status']}")
                    st.write(f"**Modalities:** {', '.join(job['modalities'])}")
                    st.write(f"**Created:** {job['created_at'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    if job['status'] == 'completed' and 'results' in job:
                        results = job['results']
                        st.write(f"**Segments:** {results.get('segments_processed', 0)}")
                        st.write(f"**Embeddings:** {results.get('embeddings_generated', 0)}")
                        st.write(f"**Processing Time:** {results.get('processing_time_ms', 0)}ms")
                
                # Action buttons
                if job['status'] == 'completed':
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"🔍 View Results", key=f"view_{job['id']}"):
                            st.info("Results viewer would open here")
                    
                    with col2:
                        if st.button(f"📊 Visualize", key=f"viz_{job['id']}"):
                            st.info("Embedding visualization would open here")
                    
                    with col3:
                        if st.button(f"🔄 Reprocess", key=f"reprocess_{job['id']}"):
                            st.info("Reprocessing would start here")


def render_optimized_processing_interface():
    """Render the optimized processing interface."""
    processor = OptimizedProcessingComponents()
    processor.render_processing_interface()


if __name__ == "__main__":
    st.set_page_config(page_title="Optimized Processing", layout="wide")
    render_optimized_processing_interface()
