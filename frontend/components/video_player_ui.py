#!/usr/bin/env python3
"""
Video Player UI Components

Frontend Streamlit components for video player with segment navigation.
Calls backend services for data preparation and displays results.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

# Import backend service
try:
    from src.services.simple_video_player import SimpleVideoPlayer, VideoSegment
except ImportError:
    SimpleVideoPlayer = None
    VideoSegment = None


class VideoPlayerUI:
    """Frontend UI components for video player with segment navigation."""
    
    def __init__(self):
        """Initialize video player UI."""
        if SimpleVideoPlayer:
            self.player_service = SimpleVideoPlayer()
        else:
            self.player_service = None
    
    def render_video_with_segments(
        self,
        video_s3_uri: str,
        segments: List[Any],
        selected_segment_id: Optional[str] = None
    ):
        """Render video player with segment navigation."""
        st.subheader("🎬 Video Player")
        
        if not self.player_service:
            st.error("Video player service not available")
            return
        
        if not segments:
            st.info("No video segments to display")
            return
        
        try:
            # Get video data from backend service
            video_data = self.player_service.prepare_video_data(
                video_s3_uri=video_s3_uri,
                segments=segments,
                selected_segment_id=selected_segment_id
            )
            
            # Display video player
            self._render_video_player(video_data)
            
            # Display segment navigation
            self._render_segment_navigation(video_data["segments"])
            
        except Exception as e:
            st.error(f"Video player failed: {e}")
    
    def render_segment_timeline(self, segments: List[Any]):
        """Render segment timeline visualization."""
        st.subheader("📊 Segment Timeline")
        
        if not self.player_service:
            st.error("Video player service not available")
            return
        
        if not segments:
            st.info("No segments to display")
            return
        
        try:
            # Get timeline data from backend service
            timeline_data = self.player_service._prepare_timeline_data(segments)
            
            # Convert to DataFrame for display
            df = pd.DataFrame(timeline_data)
            
            # Rename columns for display
            display_df = df.rename(columns={
                'segment_number': 'Segment',
                'start_time': 'Start (s)',
                'end_time': 'End (s)',
                'duration': 'Duration (s)',
                'similarity_score': 'Similarity',
                'vector_type': 'Vector Type',
                'time_range_str': 'Time Range'
            })
            
            # Display timeline table
            st.dataframe(display_df[['Segment', 'Start (s)', 'End (s)', 'Duration (s)', 'Similarity', 'Vector Type', 'Time Range']], 
                        use_container_width=True)
            
            # Display similarity chart
            st.bar_chart(display_df.set_index('Segment')['Similarity'])
            
        except Exception as e:
            st.error(f"Timeline rendering failed: {e}")
    
    def create_segment_selector(self, segments: List[Any]) -> Optional[Dict[str, Any]]:
        """Create segment selector widget."""
        if not self.player_service or not segments:
            return None
        
        try:
            # Get selector options from backend service
            options = self.player_service.get_segment_selector_options(segments)
            
            if not options:
                return None
            
            # Create selectbox options
            option_labels = ["Select a segment..."] + [opt["label"] for opt in options]
            
            selected_label = st.selectbox(
                "🎯 Jump to Segment:",
                options=option_labels,
                help="Select a segment to jump to that time in the video"
            )
            
            if selected_label != "Select a segment...":
                # Find the selected option
                for option in options:
                    if option["label"] == selected_label:
                        return option["segment_data"]
            
            return None
            
        except Exception as e:
            st.error(f"Segment selector failed: {e}")
            return None
    
    def _render_video_player(self, video_data: Dict[str, Any]):
        """Render the video player component with real streaming support."""
        video_url = video_data.get("video_url", "")
        video_s3_uri = video_data.get("video_s3_uri", "")
        selected_segment = video_data.get("selected_segment")
        
        # Video player
        if video_url.startswith("http"):
            # Real video URL - S3 presigned URL
            st.success(f"🎬 Streaming video from S3: {video_s3_uri.split('/')[-1]}")
            
            # Add video playback with error handling
            try:
                # Display video with time controls
                video_col, info_col = st.columns([3, 1])
                
                with video_col:
                    st.video(video_url, start_time=selected_segment.get('start_time', 0) if selected_segment else 0)
                
                with info_col:
                    st.write("🎯 **Video Info**")
                    st.write(f"📁 **Source:** {video_s3_uri.split('/')[-1]}")
                    if selected_segment:
                        st.write(f"⏱️ **Current Segment:** {selected_segment['time_range_str']}")
                        st.write(f"📊 **Similarity:** {selected_segment['similarity_score']:.3f}")
                    
            except Exception as e:
                st.error(f"Failed to load video: {e}")
                st.info("💡 If video fails to load, check S3 permissions and video format")
        else:
            # Demo mode - show placeholder
            st.info("📹 Demo mode - Video player would display here")
            st.code(f"Video: {video_s3_uri}")
            
            # Show selected segment info
            if selected_segment:
                st.success(f"▶️ Would jump to: {selected_segment['time_range_str']}")
    
    def _render_segment_navigation(self, segments: List[Dict[str, Any]]):
        """Render segment navigation interface."""
        if not segments:
            return
        
        st.subheader("📋 Video Segments")
        
        # Sort by similarity score (best first)
        sorted_segments = sorted(segments, key=lambda s: s["similarity_score"], reverse=True)
        
        for i, segment in enumerate(sorted_segments):
            with st.expander(
                f"🎯 Segment {i+1} - Score: {segment['similarity_score']:.3f} - {segment['time_range_str']}",
                expanded=(i == 0)  # Expand first (best) segment
            ):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Time Range:** {segment['time_range_str']}")
                    st.write(f"**Duration:** {segment['duration']:.1f} seconds")
                    if segment.get('description'):
                        st.write(f"**Description:** {segment['description']}")
                
                with col2:
                    st.write(f"**Vector Type:** {segment['vector_type']}")
                    st.write(f"**Similarity:** {segment['similarity_score']:.3f}")
                
                with col3:
                    # Jump button
                    if st.button(
                        "▶️ Jump to Segment", 
                        key=f"jump_{segment['segment_id']}",
                        help=f"Jump to {segment['start_time']:.1f}s in video"
                    ):
                        st.success(f"Would jump to {segment['start_time']:.1f}s")
                        # Store selected segment in session state
                        st.session_state.selected_video_segment = segment


# Demo data generator for frontend use
def generate_demo_segments_for_ui(video_s3_uri: str, query: str) -> List[Dict[str, Any]]:
    """Generate demo video segments for UI testing."""
    try:
        from src.services.simple_video_player import generate_demo_segments
        segments = generate_demo_segments(video_s3_uri, query)
        
        # Convert to dictionaries for UI use
        segment_dicts = []
        for segment in segments:
            segment_dicts.append({
                "segment_id": segment.segment_id,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "similarity_score": segment.similarity_score,
                "vector_type": segment.vector_type,
                "description": segment.description,
                "duration": segment.duration,
                "time_range_str": segment.time_range_str
            })
        
        return segment_dicts
        
    except ImportError:
        # Fallback for when backend service is not available
        import random
        
        demo_segments = []
        for i in range(6):  # 6 segments of 15 seconds each
            demo_segments.append({
                "segment_id": f"seg_{i+1}",
                "start_time": i * 15.0,
                "end_time": (i + 1) * 15.0,
                "similarity_score": random.uniform(0.6, 0.95),
                "vector_type": random.choice(["visual-text", "visual-image", "audio"]),
                "description": f"Demo segment {i+1} matching '{query}'",
                "duration": 15.0,
                "time_range_str": f"{i*15}s - {(i+1)*15}s"
            })
        
        return demo_segments


# Example usage
if __name__ == "__main__":
    # Demo usage
    player_ui = VideoPlayerUI()
    
    # Generate demo segments
    demo_video_uri = "s3://demo-bucket/sample-video.mp4"
    demo_query = "person walking"
    segments = generate_demo_segments_for_ui(demo_video_uri, demo_query)
    
    print(f"Generated {len(segments)} demo segments")
    print("Video player UI component ready for Streamlit integration")
