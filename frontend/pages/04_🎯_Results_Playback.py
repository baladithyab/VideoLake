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
    search_results = st.session_state.get('search_results')
    if not search_results:
        st.warning("⚠️ **No search results available** - Please complete a search first")
        st.info("💡 Navigate to the Query & Search page to perform a search before viewing results.")
        return

    # Show search summary
    _show_search_summary(search_results)

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
            results_components.display_search_results(search_results)

            # Video player section
            render_video_player_section(results_components, search_results)

            # Segment overlay section
            render_segment_overlay_section(results_components, search_results)

            # Performance metrics
            render_performance_metrics_section(results_components, search_results)

            # Export functionality
            render_results_export_section(results_components, search_results)

        except Exception as e:
            st.error(f"⚠️ Error initializing results components: {e}")
            render_fallback_results_interface(search_results)

def _show_search_summary(search_results: Dict[str, Any]):
    """Show a summary of the search results."""
    with st.expander("🔍 Search Summary", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            query = search_results.get('query', 'Unknown query')
            st.metric("Query", query)

        with col2:
            # Count total results across all patterns
            total_results = 0
            if 'results' in search_results:
                total_results = len(search_results['results'])
            elif 's3vector' in search_results:
                total_results += len(search_results.get('s3vector', []))
            if 'opensearch' in search_results:
                total_results += len(search_results.get('opensearch', []))

            st.metric("Total Results", total_results)

        with col3:
            vector_types = search_results.get('vector_types', [])
            st.metric("Vector Types", ', '.join(vector_types) if vector_types else 'Unknown')

        # Show backend information
        if search_results.get('backend_used'):
            backends_used = search_results.get('backends_used', ['Unknown'])
            st.success(f"✅ Real backend search completed using: {', '.join(backends_used)}")
        else:
            st.info("ℹ️ Demo data displayed (backend services not available)")


def render_video_player_section(results_components, search_results: Dict[str, Any]):
    """Render the video player section."""
    st.subheader("🎬 Video Player")

    # Get all results for selection
    all_results = []
    if 'results' in search_results:
        all_results = search_results['results']
    else:
        # Handle dual pattern results
        if 's3vector' in search_results:
            for result in search_results['s3vector']:
                result['source'] = 'S3Vector'
                all_results.append(result)
        if 'opensearch' in search_results:
            for result in search_results['opensearch']:
                result['source'] = 'OpenSearch'
                all_results.append(result)

    if not all_results:
        st.warning("No results available for playback")
        return

    # Video player controls
    col1, col2, col3 = st.columns(3)

    with col1:
        # Create result options with similarity scores
        result_options = []
        for i, result in enumerate(all_results):
            segment_id = result.get('segment_id', f'Result {i+1}')
            similarity = result.get('similarity', 0.0)
            source = result.get('source', 'Unknown')
            result_options.append(f"{segment_id} (Sim: {similarity:.3f}, {source})")

        selected_index = st.selectbox(
            "Select result to play:",
            options=range(len(result_options)),
            format_func=lambda x: result_options[x],
            key="results_video_player_selectbox"
        )

        selected_result = all_results[selected_index] if selected_index < len(all_results) else None

    with col2:
        playback_speed = st.selectbox(
            "Playback speed:",
            options=["0.5x", "1.0x", "1.5x", "2.0x"],
            index=1,
            key="results_playback_speed_selectbox"
        )

    with col3:
        show_overlay = st.checkbox(
            "Show segment overlay",
            value=True,
            key="results_show_overlay_checkbox"
        )

    # Video player placeholder
    if selected_result:
        st.info("🎬 **Video Player** - Will display selected video segment with similarity overlay")

        # Show video metadata if available
        metadata = selected_result.get('metadata', {})
        video_id = metadata.get('video_id', 'Unknown')
        if video_id != 'Unknown':
            st.write(f"**Video ID**: {video_id}")
    else:
        st.warning("No result selected")

    # Segment information
    if selected_result:
        with st.expander("📊 Segment Information", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Segment ID**: {selected_result.get('segment_id', 'Unknown')}")
                st.write(f"**Similarity Score**: {selected_result.get('similarity', 0.0):.3f}")
                st.write(f"**Vector Type**: {selected_result.get('vector_type', 'Unknown')}")
                st.write(f"**Source**: {selected_result.get('source', 'Unknown')}")

            with col2:
                start_time = selected_result.get('start_time', 0.0)
                end_time = selected_result.get('end_time', 0.0)
                st.write(f"**Start Time**: {start_time:.1f}s")
                st.write(f"**End Time**: {end_time:.1f}s")
                st.write(f"**Duration**: {end_time - start_time:.1f}s")

                # Show additional scores if available
                if 'hybrid_score' in selected_result:
                    st.write(f"**Hybrid Score**: {selected_result['hybrid_score']:.3f}")
                if 'text_score' in selected_result:
                    st.write(f"**Text Score**: {selected_result['text_score']:.3f}")

            # Show metadata
            if selected_result.get('metadata'):
                st.write("**Metadata**:")
                st.json(selected_result['metadata'])


def render_segment_overlay_section(results_components, search_results: Dict[str, Any]):
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