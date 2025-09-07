#!/usr/bin/env python3
"""
Media Processing Page - Streamlit Multi-page App

Clean, organized interface for video processing with minimal redundancy.
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.processing_components import ProcessingComponents
from frontend.components.error_handling import ErrorBoundary
from frontend.components.sample_video_data import sample_video_manager
from src.config.app_config import get_config

# Page configuration
st.set_page_config(
    page_title="Media Processing - S3Vector",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the media processing page."""
    # Get service manager and coordinator from session state
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')
    
    # Minimal service status in sidebar
    with st.sidebar:
        st.subheader("🔧 Service Status")
        if service_manager and coordinator:
            st.success("✅ Services Connected")
        else:
            st.error("❌ Services Unavailable")
            if st.button("🔄 Retry Initialization"):
                initialize_services()
    
    render_media_processing_page(service_manager, coordinator)

def initialize_services():
    """Initialize services if not available."""
    try:
        from src.services import get_service_manager, StreamlitIntegrationConfig
        
        integration_config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            default_vector_types=["visual-text", "visual-image", "audio"],
            max_concurrent_jobs=8,
            enable_performance_monitoring=True
        )
        
        service_manager = get_service_manager(integration_config)
        if service_manager:
            st.session_state.service_manager = service_manager
            coordinator = getattr(service_manager, 'multi_vector_coordinator', None)
            if coordinator:
                st.session_state.coordinator = coordinator
                st.rerun()
    except Exception as e:
        st.sidebar.error(f"Initialization failed: {str(e)}")

def render_media_processing_page(service_manager=None, coordinator=None):
    """Render the clean, organized media processing page."""
    st.title("🎬 Media Processing")
    
    # Single service status indicator
    if not service_manager or not coordinator:
        st.warning("⚠️ **Limited Mode**: Configuration available, processing disabled")
    
    # Initialize processing components
    processing_components = ProcessingComponents(service_manager, coordinator)
    config = get_config()
    
    # Main workflow sections
    render_configuration_section(config)
    render_video_selection_section(processing_components)
    render_processing_section(processing_components)

def render_configuration_section(config):
    """Render consolidated configuration section."""
    with st.expander("⚙️ Processing Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏗️ Storage Pattern")
            storage_pattern_options = {
                "Direct S3Vector": ["direct_s3vector"],
                "OpenSearch Hybrid": ["opensearch_s3vector_hybrid"],
                "Both (Recommended)": ["direct_s3vector", "opensearch_s3vector_hybrid"]
            }
            
            selected_pattern_key = st.selectbox(
                "Storage Configuration:",
                options=list(storage_pattern_options.keys()),
                index=2,
                key="storage_pattern_select"
            )
            st.session_state.selected_storage_patterns = storage_pattern_options[selected_pattern_key]
            
            # Vector types
            selected_types = st.multiselect(
                "Vector Types:",
                options=config.ui.default_vector_types,
                default=st.session_state.get('selected_vector_types', config.ui.default_vector_types),
                key="vector_types_select"
            )
            st.session_state.selected_vector_types = selected_types
        
        with col2:
            st.subheader("🎯 Processing Settings")
            
            # Segment duration
            segment_duration = st.slider(
                "Segment Duration (seconds):",
                min_value=2.0,
                max_value=10.0,
                value=st.session_state.get('segment_duration', config.ui.default_segment_duration),
                step=0.5,
                key="segment_duration_slider"
            )
            st.session_state.segment_duration = segment_duration
            
            # Processing mode
            processing_mode = st.selectbox(
                "Processing Strategy:",
                options=["parallel", "sequential", "adaptive"],
                index=0,
                key="processing_mode_select"
            )
            st.session_state.processing_mode = processing_mode
            
            # Quality preset
            quality_preset = st.selectbox(
                "Quality Preset:",
                options=["standard", "high", "maximum"],
                index=0,
                key="quality_preset_select"
            )
            st.session_state.quality_preset = quality_preset

def render_video_selection_section(processing_components):
    """Render streamlined video selection section."""
    st.subheader("📹 Video Selection")
    
    # Simplified tabs
    tab1, tab2 = st.tabs(["🎬 Sample Videos", "📤 Upload & S3"])
    
    with tab1:
        render_sample_video_selection(processing_components)
    
    with tab2:
        render_upload_and_s3_section(processing_components)

def render_sample_video_selection(processing_components):
    """Render clean sample video selection."""
    selected_videos = sample_video_manager.render_multi_select_interface()
    
    if selected_videos:
        # Single consolidated summary
        selection_info = sample_video_manager.get_selected_videos_info(selected_videos)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Videos", selection_info["total_videos"])
        with col2:
            st.metric("Est. Duration", f"{selection_info['estimated_duration_minutes']} min")
        with col3:
            st.metric("Creators", len(selection_info["creators"]))
        
        # Single process button
        if st.button("🚀 Process Selected Videos", type="primary", use_container_width=True):
            processing_components.process_sample_videos(selected_videos)

def render_upload_and_s3_section(processing_components):
    """Render simplified upload and S3 input."""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**📤 File Upload**")
        uploaded_files = st.file_uploader(
            "Choose video files:",
            type=['mp4', 'avi', 'mov', 'mkv', 'webm'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} file(s) uploaded")
            if st.button("🚀 Process Files", type="primary", use_container_width=True):
                processing_components.start_file_upload_processing(uploaded_files)
    
    with col2:
        st.write("**🔗 S3 URI Input**")
        s3_uri = st.text_input(
            "S3 URI:",
            placeholder="s3://bucket/video.mp4"
        )
        
        if s3_uri and s3_uri.startswith('s3://'):
            if st.button("🚀 Process S3 Video", type="primary", use_container_width=True):
                processing_components.start_dual_pattern_processing(s3_uri)

def render_processing_section(processing_components):
    """Render clean processing controls and status."""
    st.subheader("⚙️ Processing & Results")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Show Progress", use_container_width=True):
            if processing_components:
                processing_components.show_processing_progress()
            else:
                st.info("Processing progress available when services are connected")
    
    with col2:
        if st.button("💰 Cost Estimation", use_container_width=True):
            if processing_components:
                processing_components.show_cost_estimation()
            else:
                st.info("Cost estimation available when services are connected")


if __name__ == "__main__":
    main()