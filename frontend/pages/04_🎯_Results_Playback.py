#!/usr/bin/env python3
"""
Results & Playback Page - Streamlit Multi-page App

This page handles search results display and video playback:
- Interactive video player with segment overlay
- Similarity score visualization
- Performance metrics dashboard
- Results export functionality
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.results_components import ResultsComponents
from frontend.components.error_handling import ErrorBoundary

# Page configuration
st.set_page_config(
    page_title="Results & Playback - S3Vector",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the results and playback page."""
    render_results_playback_page()


def render_results_playback_page():
    """Render the results and playback page."""
    st.title("🎯 Results & Playback")
    st.markdown("**Interactive video player with segment overlay and similarity scores**")
    
    # Check prerequisites
    if not st.session_state.get('search_results'):
        st.warning("⚠️ **No search results available** - Please complete a search first")
        st.info("💡 Navigate to the Query & Search page to perform a search before viewing results.")
        return

    # Page description
    st.info("""
    **Results & Playback Features:**
    - 🎬 Interactive video player with segment overlay
    - 📊 Similarity score visualization and ranking
    - ⚡ Performance metrics and comparison
    - 📤 Results export functionality
    - 🔍 Detailed result analysis and metadata
    """)

    # Use results components with error handling
    with ErrorBoundary("Results & Playback"):
        try:
            results_components = ResultsComponents()
            
            # Display search results
            search_results = st.session_state.get('search_results', {})
            results_components.display_search_results(search_results)

            # Video player section
            render_video_player_section(results_components)

            # Segment overlay section
            render_segment_overlay_section(results_components)

            # Performance metrics
            render_performance_metrics_section(results_components, search_results)

            # Export functionality
            render_results_export_section(results_components, search_results)
            
        except Exception as e:
            st.error(f"⚠️ Error initializing results components: {e}")
            render_fallback_results_interface()


def render_video_player_section(results_components):
    """Render the video player section."""
    st.subheader("🎬 Video Player")
    
    # Video player controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_result = st.selectbox(
            "Select result to play:",
            options=["Result 1", "Result 2", "Result 3"],
            key="results_video_player_selectbox"  # UNIQUE KEY ADDED
        )
    
    with col2:
        playback_speed = st.selectbox(
            "Playback speed:",
            options=["0.5x", "1.0x", "1.5x", "2.0x"],
            index=1,
            key="results_playback_speed_selectbox"  # UNIQUE KEY ADDED
        )
    
    with col3:
        show_overlay = st.checkbox(
            "Show segment overlay",
            value=True,
            key="results_show_overlay_checkbox"  # UNIQUE KEY ADDED
        )
    
    # Video player placeholder
    results_components.render_video_player_placeholder()


def render_segment_overlay_section(results_components):
    """Render the segment overlay section."""
    st.subheader("📍 Segment Overlay")
    
    # Overlay controls
    col1, col2 = st.columns(2)
    
    with col1:
        overlay_type = st.selectbox(
            "Overlay type:",
            options=["Similarity scores", "Vector types", "Timestamps", "Metadata"],
            key="results_overlay_type_selectbox"  # UNIQUE KEY ADDED
        )
    
    with col2:
        overlay_opacity = st.slider(
            "Overlay opacity:",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            key="results_overlay_opacity_slider"  # UNIQUE KEY ADDED
        )
    
    # Segment overlay placeholder
    results_components.render_segment_overlay_placeholder()


def render_performance_metrics_section(results_components, search_results):
    """Render the performance metrics section."""
    st.subheader("📊 Performance Metrics")
    
    # Metrics display options
    col1, col2 = st.columns(2)
    
    with col1:
        metric_type = st.selectbox(
            "Metric type:",
            options=["Latency", "Similarity scores", "Result count", "All metrics"],
            key="results_metric_type_selectbox"  # UNIQUE KEY ADDED
        )
    
    with col2:
        comparison_mode = st.selectbox(
            "Comparison mode:",
            options=["Side by side", "Overlay", "Separate tabs"],
            key="results_comparison_mode_selectbox"  # UNIQUE KEY ADDED
        )
    
    # Display performance metrics
    results_components.display_performance_metrics(search_results)


def render_results_export_section(results_components, search_results):
    """Render the results export section."""
    st.subheader("📤 Export Results")
    
    # Export options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        export_format = st.selectbox(
            "Export format:",
            options=["JSON", "CSV", "XML", "PDF Report"],
            key="results_export_format_selectbox"  # UNIQUE KEY ADDED
        )
    
    with col2:
        include_metadata = st.checkbox(
            "Include metadata",
            value=True,
            key="results_include_metadata_checkbox"  # UNIQUE KEY ADDED
        )
    
    with col3:
        include_thumbnails = st.checkbox(
            "Include thumbnails",
            value=False,
            key="results_include_thumbnails_checkbox"  # UNIQUE KEY ADDED
        )
    
    # Export functionality
    results_components.render_results_export(search_results)


def render_fallback_results_interface():
    """Render fallback interface when results components are not available."""
    st.info("🎯 **Results & Playback** - Available when backend services are connected")
    
    st.write("**Demo Features:**")
    st.write("• Interactive video player with segment overlay")
    st.write("• Similarity score visualization")
    st.write("• Performance metrics dashboard")
    st.write("• Results export functionality")
    
    # Demo results display
    st.subheader("📊 Demo Results")
    
    # Sample results table
    import pandas as pd
    
    demo_results = pd.DataFrame({
        'Rank': [1, 2, 3, 4, 5],
        'Segment ID': ['seg_001', 'seg_002', 'seg_003', 'seg_004', 'seg_005'],
        'Similarity': [0.95, 0.89, 0.84, 0.78, 0.72],
        'Vector Type': ['visual-text', 'visual-image', 'audio', 'visual-text', 'visual-image'],
        'Timestamp': ['00:15-00:25', '01:30-01:40', '02:45-02:55', '03:20-03:30', '04:10-04:20']
    })
    
    st.dataframe(demo_results, use_container_width=True)
    
    # Demo controls
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎬 Play Selected Segment", key="demo_play_segment"):
            st.info("Demo: Video player would start here")
    
    with col2:
        if st.button("📤 Export Results", key="demo_export_results"):
            st.info("Demo: Results export would be available here")


if __name__ == "__main__":
    main()