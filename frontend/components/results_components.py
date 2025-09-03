#!/usr/bin/env python3
"""
Results Display Components for Unified S3Vector Demo

This module contains all results display functionality including:
- Search results table display
- Pattern-specific result formatting
- Result selection and details
- Video player integration
"""

from typing import Dict, Any, List
import streamlit as st


class ResultsComponents:
    """Results display functionality components for the unified demo."""

    def __init__(self):
        # Initialize UI components (frontend)
        try:
            from frontend.components.visualization_ui import VisualizationUI
            self.viz_ui = VisualizationUI()
        except ImportError:
            self.viz_ui = None

        try:
            from frontend.components.video_player_ui import VideoPlayerUI
            self.video_ui = VideoPlayerUI()
        except ImportError:
            self.video_ui = None
    
    def display_search_results(self, search_results: Dict[str, Any]):
        """Display search results with proper formatting for different patterns."""
        if not search_results:
            st.info("📋 **No search results available** - Please complete a search in the Query & Search section first")
            return

        # Display tabs for different views
        tab1, tab2, tab3 = st.tabs(["📋 Results List", "📊 Visualization", "🎬 Video Player"])

        with tab1:
            self._display_results_list(search_results)

        with tab2:
            self._display_embedding_visualization(search_results)

        with tab3:
            self._display_video_player(search_results)
        
        # Handle different result formats
        if isinstance(search_results, dict):
            # New format with pattern-specific results
            if "s3vector" in search_results and "opensearch" in search_results:
                # Dual pattern results
                st.subheader("📊 Dual Pattern Search Results")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**🎯 Direct S3Vector Results**")
                    s3vector_results = search_results["s3vector"]
                    if s3vector_results:
                        self.display_results_table(s3vector_results, "s3vector")
                
                with col2:
                    st.write("**🔍 OpenSearch Hybrid Results**")
                    opensearch_results = search_results["opensearch"]
                    if opensearch_results:
                        self.display_results_table(opensearch_results, "opensearch")
            
            elif "s3vector" in search_results:
                # S3Vector only results
                st.subheader("🎯 Direct S3Vector Results")
                results = search_results["s3vector"]
                if results:
                    self.display_results_table(results, "s3vector")
                
            elif "opensearch" in search_results:
                # OpenSearch only results
                st.subheader("🔍 OpenSearch Hybrid Results")
                results = search_results["opensearch"]
                if results:
                    self.display_results_table(results, "opensearch")
            
        else:
            # Legacy format - list of results
            st.subheader("📊 Search Results")
            st.write(f"**Found {len(search_results)} matching segments**")
            self.display_results_table(search_results, "legacy")

    def display_results_table(self, results: List[Dict[str, Any]], pattern: str):
        """Display search results in a table format."""
        if not results:
            st.info("No results found")
            return
        
        # Create results table data
        results_data = []
        for i, result in enumerate(results):
            # Handle different result formats
            if pattern == "legacy":
                # Legacy format
                results_data.append({
                    "Rank": i + 1,
                    "Video": result.get("video_name", "Unknown"),
                    "Segment": f"{result.get('start_time', 0):.1f}s - {result.get('end_time', 0):.1f}s",
                    "Similarity": f"{result.get('similarity_score', result.get('similarity', 0)):.3f}",
                    "Vector Type": result.get("vector_type", "Unknown"),
                    "Description": result.get("description", "No description")[:50] + "..."
                })
            else:
                # New format
                row_data = {
                    "Rank": i + 1,
                    "Segment ID": result.get("segment_id", f"segment_{i+1}"),
                    "Timestamp": f"{result.get('start_time', 0):.1f}s - {result.get('end_time', 0):.1f}s",
                    "Similarity": f"{result.get('similarity', 0):.3f}",
                    "Vector Type": result.get("vector_type", "Unknown")
                }
                
                # Add pattern-specific columns
                if pattern == "opensearch":
                    row_data["Hybrid Score"] = f"{result.get('hybrid_score', 0):.3f}"
                    row_data["Text Score"] = f"{result.get('text_score', 0):.3f}"
                
                results_data.append(row_data)
        
        # Display table
        st.dataframe(results_data, use_container_width=True)
        
        # Result selection for playback
        if results:
            selected_idx = st.selectbox(
                f"Select {pattern} result for playback:",
                options=range(len(results)),
                format_func=lambda x: f"Result {x+1}: {results[x].get('segment_id', f'segment_{x+1}')} ({results[x].get('similarity', 0):.3f})",
                help="Choose a search result to view in the video player",
                key=f"select_{pattern}_{id(results)}"  # Unique key to avoid conflicts
            )
            
            if selected_idx is not None:
                result = results[selected_idx]
                st.session_state.selected_segment = result
                
                # Show selected result details
                self.display_result_details(result, pattern)

    def display_result_details(self, result: Dict[str, Any], pattern: str):
        """Display detailed information for a selected result."""
        with st.expander(f"📋 Selected {pattern.title()} Result Details", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Segment ID**: {result.get('segment_id', 'Unknown')}")
                st.write(f"**Timestamp**: {result.get('start_time', 0):.1f}s - {result.get('end_time', 0):.1f}s")
                st.write(f"**Vector Type**: {result.get('vector_type', 'Unknown')}")
                if pattern == "legacy":
                    st.write(f"**Video**: {result.get('video_name', 'Unknown')}")
                    st.write(f"**Duration**: {result.get('end_time', 0) - result.get('start_time', 0):.1f}s")
            with col2:
                st.write(f"**Similarity**: {result.get('similarity', result.get('similarity_score', 0)):.3f}")
                if pattern == "opensearch":
                    st.write(f"**Hybrid Score**: {result.get('hybrid_score', 0):.3f}")
                    st.write(f"**Text Match**: {result.get('text_match', 'N/A')}")
                elif pattern == "legacy":
                    st.write(f"**Confidence**: {result.get('confidence', 0.85):.2f}")
                st.write(f"**Index ARN**: {result.get('index_arn', 'N/A')}")
            
            # Additional metadata
            if result.get('metadata'):
                st.write(f"**Metadata**: {result['metadata']}")
            if result.get('description'):
                st.write(f"**Description**: {result['description']}")

    def render_video_player_placeholder(self):
        """Render video player placeholder interface."""
        st.subheader("🎬 Video Player")
        st.info("📋 **Next**: Interactive video player with segment overlay will be implemented in T2.1")
        
        # Placeholder video player interface
        with st.container():
            st.write("**Video Player Interface (Coming Soon)**")
            
            # Simulate video player controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                st.button("⏮️ Previous Segment")
            
            with col2:
                # Simulate video timeline
                st.slider("Video Timeline", 0, 180, 60, help="Video playback position")
            
            with col3:
                st.button("⏭️ Next Segment")
            
            # Playback controls
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.button("⏪ -10s")
            with col2:
                st.button("⏸️ Pause")
            with col3:
                st.button("▶️ Play")
            with col4:
                st.button("⏩ +10s")
            with col5:
                st.button("🔄 Replay Segment")
            
            # Video information
            if hasattr(st.session_state, 'selected_segment') and st.session_state.selected_segment:
                segment = st.session_state.selected_segment
                st.info(f"**Selected Segment**: {segment.get('segment_id', 'Unknown')} "
                       f"({segment.get('start_time', 0):.1f}s - {segment.get('end_time', 0):.1f}s)")

    def render_segment_overlay_placeholder(self):
        """Render segment overlay placeholder interface."""
        st.subheader("🎯 Segment Overlay")
        st.info("📋 **Next**: Segment overlay functionality will be implemented in T2.2")
        
        # Placeholder for segment overlay
        with st.container():
            st.write("**Segment Overlay Features (Coming Soon)**")
            
            # Overlay configuration
            col1, col2 = st.columns(2)
            
            with col1:
                st.checkbox("Show Similarity Scores", value=True)
                st.checkbox("Highlight Active Segment", value=True)
                st.selectbox("Overlay Style", ["Minimal", "Detailed", "Custom"])
            
            with col2:
                st.slider("Overlay Opacity", 0.0, 1.0, 0.8)
                st.color_picker("Highlight Color", "#FF6B6B")
                st.selectbox("Animation", ["None", "Fade", "Slide"])
            
            # Segment navigation
            st.write("**Segment Navigation**")
            if hasattr(st.session_state, 'search_results') and st.session_state.search_results:
                # Show available segments for navigation
                st.info("Segments will be displayed as interactive timeline markers")

    def display_performance_metrics(self, search_results: Dict[str, Any]):
        """Display performance metrics for search results."""
        if not search_results:
            return
        
        st.subheader("⚡ Performance Metrics")
        
        # Extract performance data if available
        if isinstance(search_results, dict):
            if "s3vector" in search_results and "opensearch" in search_results:
                # Dual pattern comparison
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("S3Vector Latency", "~80ms", delta="-20ms")
                    st.metric("S3Vector Results", len(search_results.get("s3vector", [])))
                
                with col2:
                    st.metric("OpenSearch Latency", "~120ms", delta="+40ms")
                    st.metric("OpenSearch Results", len(search_results.get("opensearch", [])))
                
                # Performance comparison chart placeholder
                st.info("📊 **Performance comparison charts will be added in future updates**")
            
            else:
                # Single pattern metrics
                pattern = "s3vector" if "s3vector" in search_results else "opensearch"
                results = search_results.get(pattern, [])
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Latency", "~100ms")
                with col2:
                    st.metric("Results Found", len(results))
                with col3:
                    avg_similarity = sum(r.get('similarity', 0) for r in results) / len(results) if results else 0
                    st.metric("Avg Similarity", f"{avg_similarity:.3f}")

    def render_results_export(self, search_results: Dict[str, Any]):
        """Render results export functionality."""
        if not search_results:
            return
        
        st.subheader("📤 Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📄 Export as JSON"):
                st.download_button(
                    label="Download JSON",
                    data=str(search_results),  # In real implementation, use json.dumps
                    file_name="search_results.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Export as CSV"):
                st.info("CSV export functionality will be implemented")
        
        with col3:
            if st.button("📋 Copy to Clipboard"):
                st.info("Clipboard functionality will be implemented")

    def _display_results_list(self, search_results: Dict[str, Any]):
        """Display search results as a list."""
        st.subheader("📋 Search Results")

        results = search_results.get('results', [])
        if not results:
            st.info("No results found")
            return

        # Display query info
        query = search_results.get('query', 'Unknown query')
        vector_types = search_results.get('vector_types', [])
        st.info(f"🔍 Query: **{query}** | Modalities: **{', '.join(vector_types)}**")

        # Display results
        for i, result in enumerate(results):
            with st.expander(f"🎯 Result {i+1}: {result['segment_id']} (Score: {result['similarity']:.3f})"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Similarity Score:** {result['similarity']:.3f}")
                    st.write(f"**Vector Type:** {result['vector_type']}")
                    st.write(f"**Video:** {result.get('video_s3_uri', 'demo-video.mp4')}")

                with col2:
                    st.write(f"**Time Range:** {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                    st.write(f"**Duration:** {result['end_time'] - result['start_time']:.1f}s")
                    if result.get('metadata'):
                        st.write(f"**Metadata:** {result['metadata']}")

                # Jump to video button
                if st.button(f"▶️ Play Segment", key=f"play_{result['segment_id']}"):
                    st.session_state.selected_video_segment = result
                    st.success(f"Selected segment: {result['start_time']:.1f}s - {result['end_time']:.1f}s")

    def _display_embedding_visualization(self, search_results: Dict[str, Any]):
        """Display embedding space visualization."""
        if not self.viz_ui:
            st.error("Visualization UI not available")
            return

        results = search_results.get('results', [])
        if not results:
            st.info("No results to visualize")
            return

        try:
            # Generate demo embeddings for visualization
            from frontend.components.visualization_ui import generate_demo_embeddings_for_ui

            query = search_results.get('query', 'demo query')
            vector_types = search_results.get('vector_types', ['visual-text'])

            # Create embeddings for each vector type
            all_query_points = []
            all_result_points = []

            for vector_type in vector_types:
                query_points, result_points = generate_demo_embeddings_for_ui(
                    query=query,
                    vector_type=vector_type,
                    n_results=len(results)
                )
                all_query_points.extend(query_points)
                all_result_points.extend(result_points)

            # Render visualization using UI component
            self.viz_ui.render_embedding_visualization(
                query_embeddings=all_query_points,
                result_embeddings=all_result_points
            )

        except Exception as e:
            st.error(f"Visualization failed: {e}")

    def _display_video_player(self, search_results: Dict[str, Any]):
        """Display video player with segment navigation."""
        if not self.video_ui:
            st.error("Video player UI not available")
            return

        results = search_results.get('results', [])
        if not results:
            st.info("No video segments to display")
            return

        try:
            # Convert results to segment dictionaries
            segments = []
            for result in results:
                segment = {
                    'segment_id': result['segment_id'],
                    'start_time': result['start_time'],
                    'end_time': result['end_time'],
                    'similarity_score': result['similarity'],
                    'vector_type': result['vector_type'],
                    'description': f"Segment matching query with {result['similarity']:.3f} similarity",
                    'duration': result['end_time'] - result['start_time'],
                    'time_range_str': f"{result['start_time']:.1f}s - {result['end_time']:.1f}s"
                }
                segments.append(segment)

            # Get video URI (use first result's video)
            video_s3_uri = results[0].get('video_s3_uri', 's3://demo-bucket/sample-video.mp4')

            # Get selected segment ID from session state
            selected_segment_id = None
            if hasattr(st.session_state, 'selected_video_segment'):
                selected_segment_id = st.session_state.selected_video_segment.get('segment_id')

            # Render video player using UI component
            self.video_ui.render_video_with_segments(
                video_s3_uri=video_s3_uri,
                segments=segments,
                selected_segment_id=selected_segment_id
            )

        except Exception as e:
            st.error(f"Video player failed: {e}")
