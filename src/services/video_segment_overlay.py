#!/usr/bin/env python3
"""
Video Segment Overlay Service

This service provides interactive video player functionality with timeline overlays
showing retrieved segments with similarity scores and interactive navigation.
"""

import json
import base64
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st
from datetime import timedelta

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class VideoSegment:
    """Represents a video segment with metadata."""
    segment_id: str
    start_time: float
    end_time: float
    similarity_score: float
    vector_type: str
    video_s3_uri: str
    
    # Optional metadata
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    confidence: Optional[float] = None
    
    # Display properties
    color: Optional[str] = None
    opacity: Optional[float] = None
    
    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end_time - self.start_time
    
    @property
    def formatted_time_range(self) -> str:
        """Get formatted time range string."""
        start = str(timedelta(seconds=int(self.start_time)))
        end = str(timedelta(seconds=int(self.end_time)))
        return f"{start} - {end}"


@dataclass
class VideoPlayerConfig:
    """Configuration for video player with segment overlay."""
    
    # Player dimensions
    width: int = 800
    height: int = 450
    
    # Timeline configuration
    timeline_height: int = 100
    segment_height: int = 20
    timeline_margin: int = 10
    
    # Color scheme
    segment_colors: Dict[str, str] = field(default_factory=lambda: {
        'visual-text': '#FF6B6B',
        'visual-image': '#4ECDC4', 
        'audio': '#45B7D1',
        'default': '#95A5A6'
    })
    
    # Similarity score visualization
    min_opacity: float = 0.3
    max_opacity: float = 0.9
    score_threshold: float = 0.5
    
    # Interactive features
    enable_segment_click: bool = True
    enable_hover_info: bool = True
    enable_timeline_scrubbing: bool = True
    show_similarity_scores: bool = True
    
    # Auto-play settings
    auto_play: bool = False
    loop: bool = False
    muted: bool = False


class VideoSegmentOverlay:
    """Service for creating interactive video players with segment overlays."""
    
    def __init__(self, config: Optional[VideoPlayerConfig] = None):
        """Initialize the video segment overlay service."""
        self.config = config or VideoPlayerConfig()
        logger.info("Video segment overlay service initialized")
    
    def create_video_player_with_overlay(
        self,
        video_s3_uri: str,
        segments: List[VideoSegment],
        video_duration: Optional[float] = None,
        current_time: float = 0.0,
        title: str = "Video Player with Segment Overlay"
    ) -> str:
        """Create an interactive video player with segment overlay.
        
        Args:
            video_s3_uri: S3 URI of the video file
            segments: List of video segments to overlay
            video_duration: Total video duration in seconds
            current_time: Current playback time
            title: Player title
            
        Returns:
            HTML string for the video player
        """
        # Generate presigned URL for video (in real implementation)
        video_url = self._get_video_url(video_s3_uri)
        
        # Estimate duration if not provided
        if video_duration is None:
            video_duration = self._estimate_video_duration(segments)
        
        # Generate timeline HTML
        timeline_html = self._generate_timeline_html(segments, video_duration)
        
        # Generate player HTML
        player_html = self._generate_player_html(
            video_url=video_url,
            timeline_html=timeline_html,
            segments=segments,
            video_duration=video_duration,
            current_time=current_time,
            title=title
        )
        
        return player_html
    
    def create_streamlit_video_player(
        self,
        video_s3_uri: str,
        segments: List[VideoSegment],
        video_duration: Optional[float] = None,
        key: Optional[str] = None
    ):
        """Create a Streamlit-compatible video player with segment overlay.
        
        Args:
            video_s3_uri: S3 URI of the video file
            segments: List of video segments to overlay
            video_duration: Total video duration in seconds
            key: Streamlit component key
        """
        # Create columns for layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Video player
            st.subheader("🎬 Video Player")
            
            # For demo purposes, show a placeholder
            # In real implementation, this would use a custom Streamlit component
            video_url = self._get_video_url(video_s3_uri)
            
            if video_url.startswith("http"):
                st.video(video_url)
            else:
                st.info("📹 Video player would be displayed here with interactive timeline")
                st.code(f"Video: {video_s3_uri}")
            
            # Timeline visualization
            self._render_streamlit_timeline(segments, video_duration)
        
        with col2:
            # Segment list
            st.subheader("📋 Retrieved Segments")
            self._render_segment_list(segments)
    
    def _get_video_url(self, video_s3_uri: str) -> str:
        """Get video URL (presigned URL in real implementation)."""
        # In real implementation, this would generate a presigned URL
        # For demo purposes, return a placeholder
        if video_s3_uri.startswith("s3://"):
            return f"https://demo-video-url.com/{video_s3_uri.split('/')[-1]}"
        return video_s3_uri
    
    def _estimate_video_duration(self, segments: List[VideoSegment]) -> float:
        """Estimate video duration from segments."""
        if not segments:
            return 60.0  # Default 1 minute
        
        max_end_time = max(segment.end_time for segment in segments)
        return max_end_time + 5.0  # Add 5 seconds buffer
    
    def _generate_timeline_html(self, segments: List[VideoSegment], video_duration: float) -> str:
        """Generate HTML for the interactive timeline."""
        timeline_width = self.config.width - (2 * self.config.timeline_margin)
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time)
        
        # Generate segment bars
        segment_bars = []
        for i, segment in enumerate(sorted_segments):
            # Calculate position and width
            left_percent = (segment.start_time / video_duration) * 100
            width_percent = (segment.duration / video_duration) * 100
            
            # Determine color and opacity
            color = self.config.segment_colors.get(segment.vector_type, self.config.segment_colors['default'])
            opacity = self._calculate_opacity(segment.similarity_score)
            
            # Create segment bar HTML
            segment_html = f"""
            <div class="segment-bar" 
                 style="left: {left_percent}%; 
                        width: {width_percent}%; 
                        background-color: {color}; 
                        opacity: {opacity};"
                 data-segment-id="{segment.segment_id}"
                 data-start-time="{segment.start_time}"
                 data-end-time="{segment.end_time}"
                 data-similarity="{segment.similarity_score:.3f}"
                 title="Segment {i+1}: {segment.formatted_time_range} (Score: {segment.similarity_score:.3f})">
            </div>
            """
            segment_bars.append(segment_html)
        
        # Combine into timeline HTML
        timeline_html = f"""
        <div class="video-timeline" style="width: {timeline_width}px; height: {self.config.timeline_height}px;">
            <div class="timeline-track">
                {''.join(segment_bars)}
            </div>
            <div class="timeline-scrubber" id="timeline-scrubber"></div>
        </div>
        """
        
        return timeline_html
    
    def _generate_player_html(
        self,
        video_url: str,
        timeline_html: str,
        segments: List[VideoSegment],
        video_duration: float,
        current_time: float,
        title: str
    ) -> str:
        """Generate complete HTML for the video player."""
        
        # Generate CSS
        css = self._generate_css()
        
        # Generate JavaScript
        js = self._generate_javascript(segments, video_duration)
        
        # Combine into complete HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>{css}</style>
        </head>
        <body>
            <div class="video-player-container">
                <h2>{title}</h2>
                
                <div class="video-wrapper">
                    <video id="main-video" 
                           width="{self.config.width}" 
                           height="{self.config.height}"
                           controls
                           {'autoplay' if self.config.auto_play else ''}
                           {'loop' if self.config.loop else ''}
                           {'muted' if self.config.muted else ''}>
                        <source src="{video_url}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
                
                <div class="timeline-container">
                    {timeline_html}
                </div>
                
                <div class="segment-info" id="segment-info">
                    <h3>Segment Information</h3>
                    <p>Click on a segment in the timeline to see details</p>
                </div>
            </div>
            
            <script>{js}</script>
        </body>
        </html>
        """
        
        return html
    
    def _generate_css(self) -> str:
        """Generate CSS for the video player."""
        return """
        .video-player-container {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .video-wrapper {
            position: relative;
            margin-bottom: 20px;
        }
        
        .timeline-container {
            margin: 20px 0;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        
        .video-timeline {
            position: relative;
            background-color: #ddd;
            border-radius: 3px;
            margin: 10px 0;
        }
        
        .timeline-track {
            position: relative;
            height: 20px;
            background-color: #ccc;
            border-radius: 3px;
        }
        
        .segment-bar {
            position: absolute;
            height: 20px;
            border-radius: 2px;
            cursor: pointer;
            transition: opacity 0.2s;
            border: 1px solid rgba(255,255,255,0.3);
        }
        
        .segment-bar:hover {
            opacity: 1 !important;
            border: 2px solid white;
        }
        
        .timeline-scrubber {
            position: absolute;
            top: 0;
            width: 2px;
            height: 20px;
            background-color: red;
            pointer-events: none;
        }
        
        .segment-info {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        
        .segment-details {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }
        
        .detail-item {
            background-color: white;
            padding: 8px;
            border-radius: 3px;
            border: 1px solid #ddd;
        }
        
        .detail-label {
            font-weight: bold;
            color: #555;
        }
        
        .similarity-score {
            font-size: 1.2em;
            font-weight: bold;
        }
        
        .score-high { color: #28a745; }
        .score-medium { color: #ffc107; }
        .score-low { color: #dc3545; }
        """
    
    def _generate_javascript(self, segments: List[VideoSegment], video_duration: float) -> str:
        """Generate JavaScript for interactive functionality."""
        segments_json = json.dumps([{
            'id': s.segment_id,
            'start_time': s.start_time,
            'end_time': s.end_time,
            'similarity_score': s.similarity_score,
            'vector_type': s.vector_type,
            'title': s.title or f"Segment {i+1}",
            'description': s.description or ""
        } for i, s in enumerate(segments)])
        
        return f"""
        const segments = {segments_json};
        const videoDuration = {video_duration};
        const video = document.getElementById('main-video');
        const scrubber = document.getElementById('timeline-scrubber');
        const segmentInfo = document.getElementById('segment-info');
        
        // Update scrubber position
        function updateScrubber() {{
            if (video.duration) {{
                const percent = (video.currentTime / video.duration) * 100;
                scrubber.style.left = percent + '%';
            }}
        }}
        
        // Handle segment click
        function handleSegmentClick(segmentId) {{
            const segment = segments.find(s => s.id === segmentId);
            if (segment) {{
                // Jump to segment start time
                video.currentTime = segment.start_time;
                
                // Update segment info display
                updateSegmentInfo(segment);
            }}
        }}
        
        // Update segment information display
        function updateSegmentInfo(segment) {{
            const scoreClass = segment.similarity_score > 0.8 ? 'score-high' : 
                              segment.similarity_score > 0.6 ? 'score-medium' : 'score-low';
            
            segmentInfo.innerHTML = `
                <h3>Segment Information</h3>
                <div class="segment-details">
                    <div class="detail-item">
                        <div class="detail-label">Title</div>
                        <div>${{segment.title}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Time Range</div>
                        <div>${{formatTime(segment.start_time)}} - ${{formatTime(segment.end_time)}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Vector Type</div>
                        <div>${{segment.vector_type}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Similarity Score</div>
                        <div class="similarity-score ${{scoreClass}}">${{segment.similarity_score.toFixed(3)}}</div>
                    </div>
                </div>
                <p>${{segment.description}}</p>
            `;
        }}
        
        // Format time as MM:SS
        function formatTime(seconds) {{
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${{mins.toString().padStart(2, '0')}}:${{secs.toString().padStart(2, '0')}}`;
        }}
        
        // Event listeners
        video.addEventListener('timeupdate', updateScrubber);
        
        // Add click handlers to segment bars
        document.querySelectorAll('.segment-bar').forEach(bar => {{
            bar.addEventListener('click', function() {{
                handleSegmentClick(this.dataset.segmentId);
            }});
        }});
        
        // Initialize
        updateScrubber();
        """
    
    def _calculate_opacity(self, similarity_score: float) -> float:
        """Calculate opacity based on similarity score."""
        if similarity_score < self.config.score_threshold:
            return self.config.min_opacity
        
        # Linear interpolation between min and max opacity
        score_range = 1.0 - self.config.score_threshold
        opacity_range = self.config.max_opacity - self.config.min_opacity
        
        normalized_score = (similarity_score - self.config.score_threshold) / score_range
        opacity = self.config.min_opacity + (normalized_score * opacity_range)
        
        return min(max(opacity, self.config.min_opacity), self.config.max_opacity)
    
    def _render_streamlit_timeline(self, segments: List[VideoSegment], video_duration: Optional[float]):
        """Render timeline visualization in Streamlit."""
        if not segments:
            st.info("No segments to display")
            return
        
        # Create a simple timeline visualization using Streamlit
        st.subheader("📊 Segment Timeline")
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda s: s.start_time)
        
        # Create timeline data for plotting
        timeline_data = []
        for i, segment in enumerate(sorted_segments):
            timeline_data.append({
                'Segment': f"Segment {i+1}",
                'Start': segment.start_time,
                'End': segment.end_time,
                'Duration': segment.duration,
                'Similarity': segment.similarity_score,
                'Vector Type': segment.vector_type,
                'Time Range': segment.formatted_time_range
            })
        
        # Display as a table
        st.dataframe(timeline_data, use_container_width=True)
        
        # Simple bar chart of similarity scores
        import pandas as pd
        df = pd.DataFrame(timeline_data)
        st.bar_chart(df.set_index('Segment')['Similarity'])
    
    def _render_segment_list(self, segments: List[VideoSegment]):
        """Render list of segments in Streamlit."""
        if not segments:
            st.info("No segments available")
            return
        
        # Sort by similarity score (highest first)
        sorted_segments = sorted(segments, key=lambda s: s.similarity_score, reverse=True)
        
        for i, segment in enumerate(sorted_segments):
            with st.expander(f"🎯 Segment {i+1} - Score: {segment.similarity_score:.3f}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Time:** {segment.formatted_time_range}")
                    st.write(f"**Duration:** {segment.duration:.1f}s")
                
                with col2:
                    st.write(f"**Vector Type:** {segment.vector_type}")
                    st.write(f"**Similarity:** {segment.similarity_score:.3f}")
                
                if segment.description:
                    st.write(f"**Description:** {segment.description}")
                
                # Jump to segment button (placeholder)
                if st.button(f"▶️ Jump to Segment", key=f"jump_{segment.segment_id}"):
                    st.success(f"Would jump to {segment.start_time:.1f}s in video player")
    
    def export_segment_data(self, segments: List[VideoSegment], filename: str):
        """Export segment data to file."""
        segment_data = []
        for segment in segments:
            segment_data.append({
                'segment_id': segment.segment_id,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'duration': segment.duration,
                'similarity_score': segment.similarity_score,
                'vector_type': segment.vector_type,
                'video_s3_uri': segment.video_s3_uri,
                'title': segment.title,
                'description': segment.description,
                'formatted_time_range': segment.formatted_time_range
            })
        
        if filename.endswith('.json'):
            with open(filename, 'w') as f:
                json.dump(segment_data, f, indent=2)
        elif filename.endswith('.csv'):
            import pandas as pd
            df = pd.DataFrame(segment_data)
            df.to_csv(filename, index=False)
        else:
            raise ValueError("Unsupported file format. Use .json or .csv")
        
        logger.info(f"Segment data exported to {filename}")
