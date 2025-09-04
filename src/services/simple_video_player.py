#!/usr/bin/env python3
"""
Simple Video Player Service

Provides basic video player functionality with segment navigation.
Takes retrieved segments with timecodes and allows jumping to specific times.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import timedelta

from src.utils.logging_config import get_logger
from src.services.s3_bucket_utils import S3BucketUtilityService

logger = get_logger(__name__)


@dataclass
class VideoSegment:
    """Simple video segment with timecode information."""
    segment_id: str
    start_time: float  # seconds
    end_time: float    # seconds
    similarity_score: float
    vector_type: str
    description: Optional[str] = None
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def time_range_str(self) -> str:
        start = str(timedelta(seconds=int(self.start_time)))
        end = str(timedelta(seconds=int(self.end_time)))
        return f"{start} - {end}"


class SimpleVideoPlayer:
    """Simple video player with segment navigation."""
    
    def __init__(self):
        """Initialize the video player."""
        self.s3_service = S3BucketUtilityService()
        logger.info("Simple video player initialized")
    
    def prepare_video_data(
        self,
        video_s3_uri: str,
        segments: List[VideoSegment],
        selected_segment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prepare video player data for frontend rendering.

        Args:
            video_s3_uri: S3 URI of the video
            segments: List of video segments
            selected_segment_id: ID of segment to jump to

        Returns:
            Dictionary with video data for frontend display
        """
        # Get video URL (in real implementation, this would be a presigned URL)
        video_url = self._get_video_url(video_s3_uri)

        # Prepare segment data
        segment_data = []
        selected_segment = None

        for segment in segments:
            segment_info = {
                "segment_id": segment.segment_id,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "duration": segment.duration,
                "similarity_score": segment.similarity_score,
                "vector_type": segment.vector_type,
                "time_range_str": segment.time_range_str,
                "description": segment.description
            }
            segment_data.append(segment_info)

            if segment.segment_id == selected_segment_id:
                selected_segment = segment_info

        return {
            "video_url": video_url,
            "video_s3_uri": video_s3_uri,
            "segments": segment_data,
            "selected_segment": selected_segment,
            "timeline_data": self._prepare_timeline_data(segments)
        }
    
    def _prepare_timeline_data(self, segments: List[VideoSegment]) -> List[Dict[str, Any]]:
        """Prepare timeline data for frontend display."""
        timeline_data = []
        for i, segment in enumerate(sorted(segments, key=lambda s: s.start_time)):
            timeline_data.append({
                'segment_number': i + 1,
                'segment_id': segment.segment_id,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'duration': segment.duration,
                'similarity_score': segment.similarity_score,
                'vector_type': segment.vector_type,
                'time_range_str': segment.time_range_str,
                'description': segment.description
            })
        return timeline_data
    
    def get_segment_selector_options(self, segments: List[VideoSegment]) -> List[Dict[str, Any]]:
        """Get segment selector options for frontend.

        Returns:
            List of segment options for frontend selector
        """
        if not segments:
            return []

        # Sort segments by similarity score
        sorted_segments = sorted(segments, key=lambda s: s.similarity_score, reverse=True)

        options = []
        for i, segment in enumerate(sorted_segments):
            options.append({
                "label": f"Segment {i+1}: {segment.time_range_str} (Score: {segment.similarity_score:.3f})",
                "value": segment.segment_id,
                "segment_data": {
                    "segment_id": segment.segment_id,
                    "start_time": segment.start_time,
                    "end_time": segment.end_time,
                    "similarity_score": segment.similarity_score,
                    "vector_type": segment.vector_type,
                    "time_range_str": segment.time_range_str,
                    "description": segment.description
                }
            })

        return options
    
    def _get_video_url(self, video_s3_uri: str) -> str:
        """Get video URL for playback using S3 presigned URLs."""
        if video_s3_uri.startswith("s3://"):
            try:
                # Generate presigned URL for video streaming
                presigned_data = self.s3_service.generate_presigned_url(
                    s3_uri=video_s3_uri,
                    expires_in=3600,  # 1 hour expiration
                    response_content_type="video/mp4"
                )
                logger.info(f"Generated presigned URL for video: {video_s3_uri}")
                return presigned_data["url"]
            except Exception as e:
                logger.error(f"Failed to generate presigned URL for {video_s3_uri}: {e}")
                # Fallback to placeholder for demo purposes
                return f"demo-video-{video_s3_uri.split('/')[-1]}"
        return video_s3_uri
    
    def get_segment_by_id(self, segments: List[VideoSegment], segment_id: str) -> Optional[VideoSegment]:
        """Get segment by ID."""
        return next((s for s in segments if s.segment_id == segment_id), None)
    
    def filter_segments_by_vector_type(
        self, 
        segments: List[VideoSegment], 
        vector_type: str
    ) -> List[VideoSegment]:
        """Filter segments by vector type."""
        return [s for s in segments if s.vector_type == vector_type]
    
    def get_top_segments(
        self, 
        segments: List[VideoSegment], 
        top_k: int = 5
    ) -> List[VideoSegment]:
        """Get top K segments by similarity score."""
        return sorted(segments, key=lambda s: s.similarity_score, reverse=True)[:top_k]


# Demo data generator for testing
def generate_demo_segments(video_s3_uri: str, query: str) -> List[VideoSegment]:
    """Generate demo video segments for testing."""
    import random
    
    # Demo segments with realistic timecodes
    demo_segments = [
        VideoSegment(
            segment_id=f"seg_{i+1}",
            start_time=i * 15.0,
            end_time=(i + 1) * 15.0,
            similarity_score=random.uniform(0.6, 0.95),
            vector_type=random.choice(["visual-text", "visual-image", "audio"]),
            description=f"Demo segment {i+1} matching '{query}'"
        )
        for i in range(6)  # 6 segments of 15 seconds each
    ]
    
    return demo_segments


# Example usage
if __name__ == "__main__":
    # Demo usage
    player = SimpleVideoPlayer()
    
    # Generate demo segments
    demo_video_uri = "s3://demo-bucket/sample-video.mp4"
    demo_query = "person walking"
    segments = generate_demo_segments(demo_video_uri, demo_query)
    
    print(f"Generated {len(segments)} demo segments")
    for segment in segments:
        print(f"  {segment.segment_id}: {segment.time_range_str} (Score: {segment.similarity_score:.3f})")
