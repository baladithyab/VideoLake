#!/usr/bin/env python3
"""
Media Processing Page - Streamlit Multi-page App

This page handles all media processing functionality by leveraging existing components:
- Uses ProcessingComponents for video input and processing
- Uses sample_video_manager for multiselect interface
- Maintains all existing functionality while providing clean page separation
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
    # Get service manager and coordinator from session state if available
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')
    
    render_media_processing_page(service_manager, coordinator)


def render_media_processing_page(service_manager=None, coordinator=None):
    """Render the media processing page using existing components."""
    st.title("🎬 Media Processing")
    st.markdown("**Select videos, configure processing, and manage ingestion settings**")
    
    # Initialize processing components (reuse existing work)
    processing_components = ProcessingComponents(service_manager, coordinator)
    config = get_config()
    
    # Page description
    st.info("""
    **Media Processing Features:**
    - 📹 Sample video selection with clean multiselect interface
    - 📤 File upload with drag-and-drop support
    - 🔗 S3 URI input for existing videos
    - 🧠 Multi-vector configuration (Marengo 2.7)
    - 🏗️ Storage pattern selection
    - ⚙️ Processing duration and quality settings
    """)
    
    # Storage pattern selection (moved from upload section)
    render_storage_pattern_selection()
    
    # Vector configuration (moved from upload section)
    render_vector_configuration(config)
    
    # Use existing video input section from ProcessingComponents
    st.subheader("📹 Video Input & Selection")
    with ErrorBoundary("Video Input & Processing"):
        if processing_components:
            # This uses all the existing work in ProcessingComponents
            processing_components.render_video_input_section()
        else:
            st.info("📹 **Video Input** - Available when backend services are connected")
    
    # Cost estimation and processing controls
    render_processing_controls(processing_components)


def render_storage_pattern_selection():
    """Render storage pattern selection interface (extracted from existing code)."""
    st.subheader("🏗️ Storage Pattern Selection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("**Pattern 1: Direct S3Vector**")
        st.write("• Query S3Vector indexes directly")
        st.write("• Native S3Vector performance")
        st.write("• Cost-effective vector storage")
    
    with col2:
        st.info("**Pattern 2: OpenSearch + S3Vector Hybrid**")
        st.write("• OpenSearch with S3Vector backend")
        st.write("• Hybrid search capabilities")
        st.write("• Text + vector search fusion")
    
    # Storage pattern selection with dropdown - FIXED: Added unique key
    storage_pattern_options = {
        "Direct S3Vector Only": ["direct_s3vector"],
        "OpenSearch Hybrid Only": ["opensearch_s3vector_hybrid"],
        "Both Patterns (Recommended)": ["direct_s3vector", "opensearch_s3vector_hybrid"]
    }
    
    selected_pattern_key = st.selectbox(
        "Choose Storage Pattern Configuration:",
        options=list(storage_pattern_options.keys()),
        index=2,  # Default to "Both Patterns"
        help="Select which storage patterns to use for processing and comparison",
        key="media_processing_storage_pattern_selectbox"  # UNIQUE KEY ADDED
    )
    
    st.session_state.selected_storage_patterns = storage_pattern_options[selected_pattern_key]
    
    # Show selected patterns
    st.success(f"**Selected Patterns:** {', '.join(st.session_state.selected_storage_patterns)}")


def render_vector_configuration(config):
    """Render vector type and processing configuration (extracted from existing code)."""
    st.subheader("🧠 Multi-Vector Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Vector type selection
        selected_types = st.multiselect(
            "Select Vector Types:",
            options=config.ui.default_vector_types,
            default=st.session_state.get('selected_vector_types', config.ui.default_vector_types),
            help="Choose which Marengo 2.7 vector types to generate",
            key="media_processing_vector_types_multiselect"  # UNIQUE KEY ADDED
        )
        st.session_state.selected_vector_types = selected_types
        
        # Segment duration
        segment_duration = st.slider(
            "Segment Duration (seconds):",
            min_value=2.0,
            max_value=10.0,
            value=st.session_state.get('segment_duration', config.ui.default_segment_duration),
            step=0.5,
            help="Duration of each video segment for processing",
            key="media_processing_segment_duration_slider"  # UNIQUE KEY ADDED
        )
        st.session_state.segment_duration = segment_duration
    
    with col2:
        # Processing mode - FIXED: Added unique key
        processing_mode = st.selectbox(
            "Processing Strategy:",
            options=["parallel", "sequential", "adaptive"],
            index=["parallel", "sequential", "adaptive"].index(
                st.session_state.get('processing_mode', config.ui.default_processing_mode)
            ),
            help="How to process multiple videos",
            key="media_processing_strategy_selectbox"  # UNIQUE KEY ADDED
        )
        st.session_state.processing_mode = processing_mode
        
        # Quality preset - FIXED: Added unique key
        quality_preset = st.selectbox(
            "Quality Preset:",
            options=["standard", "high", "maximum"],
            index=0,
            help="Processing quality vs speed tradeoff",
            key="media_processing_quality_preset_selectbox"  # UNIQUE KEY ADDED
        )
        st.session_state.quality_preset = quality_preset


def render_processing_controls(processing_components):
    """Render processing controls using existing components."""
    st.subheader("⚙️ Processing Controls")
    
    # Processing controls - always use real AWS resources
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("🔧 **Real AWS Processing**: All operations use live AWS resources")
        # Remove fake AWS toggle - always use real AWS
        st.session_state.use_real_aws = True
    
    with col2:
        if st.button("📊 Show Progress", use_container_width=True, key="media_processing_show_progress"):
            # Use existing progress display from ProcessingComponents
            if processing_components:
                processing_components.show_processing_progress()
            else:
                st.info("📊 **Processing Progress** - Available when backend services are connected")


if __name__ == "__main__":
    main()