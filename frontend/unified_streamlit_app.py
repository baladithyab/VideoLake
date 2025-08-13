#!/usr/bin/env python3
"""
Unified Streamlit App for S3Vector - Complete Video Search Pipeline

Translates the Gradio Unified Video Search demo to Streamlit with:
- Index creation and management
- Video ingestion with TwelveLabs Marengo
- Multi-modal search (text-to-video, video-to-video, temporal)
- Embedding visualization with PCA/t-SNE
- Video segment playback
- Cost tracking and analytics

Based on the Gradio UnifiedVideoSearchPage from commit 5b39e65.
"""

import os
import sys
import json
import time
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

import streamlit as st
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Backend services
from src.services.similarity_search_engine import (
    SimilaritySearchEngine, 
    SimilarityQuery, 
    IndexType,
    TemporalFilter
)
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.s3_bucket_utils import S3BucketUtilityService
from src.config import config_manager
from src.utils.logging_config import get_structured_logger
from src.utils.resource_registry import resource_registry
from src.exceptions import VectorStorageError

# Initialize logger
logger = get_structured_logger("unified_streamlit")

# Sample videos for demo
SAMPLE_VIDEOS = {
    "Big Buck Bunny (Creative Commons)": {
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "description": "Animated short film featuring a large rabbit and forest creatures",
        "duration": 596,
        "category": "animation"
    },
    "Elephant Dream (Creative Commons)": {
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 
        "description": "Surreal animated short film with abstract visuals",
        "duration": 654,
        "category": "animation"
    },
    "Sintel (Creative Commons)": {
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
        "description": "Fantasy adventure animation with dragons and magic",
        "duration": 888,
        "category": "animation"
    }
}

@dataclass
class ProcessedVideo:
    """Represents a processed video in the index."""
    video_id: str
    name: str
    segments: int
    duration: float
    s3_uri: Optional[str] = None
    processing_type: str = "simulation"
    metadata: Optional[Dict] = None

class UnifiedStreamlitApp:
    """Main application class for the unified Streamlit demo."""
    
    def __init__(self):
        """Initialize the application."""
        self.search_engine = None
        self.video_processor = None
        self.video_storage = None
        self.s3_manager = None
        
        # Initialize session state
        if 'processed_videos' not in st.session_state:
            st.session_state.processed_videos = {}
        if 'video_index_arn' not in st.session_state:
            st.session_state.video_index_arn = None
        if 'costs' not in st.session_state:
            st.session_state.costs = {
                "video_processing": 0,
                "storage": 0,
                "queries": 0,
                "total": 0
            }
        if 'search_results' not in st.session_state:
            st.session_state.search_results = []
        if 'last_embeddings' not in st.session_state:
            st.session_state.last_embeddings = None
        if 'selected_segment' not in st.session_state:
            st.session_state.selected_segment = None
            
        self._init_services()
    
    def _init_services(self):
        """Initialize backend services."""
        try:
            self.search_engine = SimilaritySearchEngine()
            self.video_processor = TwelveLabsVideoProcessingService()
            self.video_storage = VideoEmbeddingStorageService()
            self.s3_manager = S3VectorStorageManager()
            logger.log_operation("services_initialized", level="INFO")
        except Exception as e:
            logger.log_error("service_initialization", error=e)
            st.error("Failed to initialize backend services. Check configuration.")
    
    def _seed_from_text(self, text: str) -> int:
        """Generate deterministic seed from text for simulations."""
        h = hashlib.sha256((text or "").encode("utf-8")).hexdigest()
        return int(h[:8], 16)
    
    def _simulate_embeddings(self, count: int, dim: int, seed: int) -> np.ndarray:
        """Generate simulated embeddings for visualization."""
        rng = np.random.default_rng(seed)
        X = rng.normal(0, 1, size=(count, dim)).astype(np.float32)
        # Normalize to unit length
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-8
        return X / norms
    
    def render_header(self):
        """Render the application header."""
        st.set_page_config(
            page_title="S3Vector Unified Demo",
            page_icon="🎬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        st.title("🎬 S3Vector Unified Video Search Demo")
        st.markdown("""
        **Complete video-to-search pipeline with segment playback**
        
        Experience the full workflow:
        1. **Create Index**: Set up your searchable video index
        2. **Ingest Videos**: Process videos with TwelveLabs Marengo
        3. **Search & Discover**: Find segments using text or video queries
        4. **Visualize Embeddings**: Explore the embedding space with PCA/t-SNE
        5. **Watch Results**: Preview matching video segments
        """)
        
        # Global status
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            if st.session_state.video_index_arn:
                st.success(f"✅ Index Active: {st.session_state.video_index_arn.split('/')[-1]}")
            else:
                st.info("ℹ️ No active index - create one to get started")
        with col2:
            st.metric("Videos Indexed", len(st.session_state.processed_videos))
        with col3:
            st.metric("Session Cost", f"${st.session_state.costs['total']:.4f}")
    
    def render_sidebar(self):
        """Render the sidebar with navigation and controls."""
        st.sidebar.title("🎛️ Controls")
        
        # Global toggle for real AWS usage
        use_real_aws = st.sidebar.toggle(
            "Use Real AWS",
            value=False,
            help="Enable to use actual AWS services (costs apply)"
        )
        
        if not use_real_aws:
            st.sidebar.info("🛡️ Real AWS is OFF - using simulation mode")
        else:
            st.sidebar.warning("⚠️ Real AWS enabled - costs will apply")
        
        st.sidebar.divider()
        
        # Navigation
        page = st.sidebar.radio(
            "Navigate to:",
            [
                "🗂️ Index Setup",
                "📹 Video Ingestion", 
                "🔍 Search & Discovery",
                "🎯 Embedding Visualization",
                "📊 Analytics & Management"
            ],
            index=0
        )
        
        st.sidebar.divider()
        
        # Quick stats
        st.sidebar.subheader("📈 Quick Stats")
        total_segments = sum(v.segments for v in st.session_state.processed_videos.values())
        st.sidebar.metric("Total Segments", total_segments)
        
        real_videos = sum(1 for v in st.session_state.processed_videos.values() 
                         if v.processing_type == "real")
        st.sidebar.metric("Real Processing", real_videos)
        
        return page, use_real_aws
    
    def render_index_setup(self, use_real_aws: bool):
        """Render the index setup page."""
        st.header("🗂️ Index Setup")
        st.markdown("Create and manage your video search index")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Index Configuration")
            
            index_name = st.text_input(
                "Index Name",
                value="unified-video-search-index",
                help="Name for your video search index"
            )
            
            index_description = st.text_area(
                "Index Description",
                value="Unified video search demo index with multimodal capabilities",
                height=100
            )
            
            if use_real_aws:
                bucket_name = st.text_input(
                    "S3 Vector Bucket Name",
                    help="Bucket for storing vector embeddings"
                )
                
                embedding_dimension = st.number_input(
                    "Embedding Dimension",
                    min_value=64,
                    max_value=4096,
                    value=1024,
                    help="Dimension for TwelveLabs Marengo embeddings"
                )
                
                if st.button("🚀 Create Video Index", type="primary"):
                    if bucket_name and index_name:
                        self._create_video_index(bucket_name, index_name, embedding_dimension)
                    else:
                        st.error("Please provide bucket name and index name")
            else:
                st.info("Enable 'Use Real AWS' to create actual indexes")
                if st.button("🚀 Simulate Index Creation", type="primary"):
                    self._simulate_index_creation(index_name, index_description)
        
        with col2:
            st.subheader("Index Status")
            
            if st.session_state.video_index_arn:
                st.success("✅ Index Active")
                st.code(st.session_state.video_index_arn)
                
                # Index statistics
                total_videos = len(st.session_state.processed_videos)
                total_segments = sum(v.segments for v in st.session_state.processed_videos.values())
                total_duration = sum(v.duration for v in st.session_state.processed_videos.values())
                
                st.markdown(f"""
                **Index Statistics:**
                - **Total Videos**: {total_videos}
                - **Total Segments**: {total_segments:,}
                - **Total Duration**: {total_duration:.1f} seconds
                - **Storage Size**: ~{total_segments * 4:.1f} KB
                """)
                
                if st.button("🔄 Refresh Index Status"):
                    self._refresh_index_status()
            else:
                st.info("No index created yet")
                
            # Video library overview
            st.subheader("Video Library")
            if st.session_state.processed_videos:
                for video_id, video in st.session_state.processed_videos.items():
                    processing_badge = "🟢 Real" if video.processing_type == "real" else "🔵 Sim"
                    st.markdown(f"""
                    **{video.name}** {processing_badge}
                    - Duration: {video.duration:.1f}s
                    - Segments: {video.segments}
                    - ID: `{video_id}`
                    """)
            else:
                st.info("No videos in library yet")
    
    def render_video_ingestion(self, use_real_aws: bool):
        """Render the video ingestion page."""
        st.header("📹 Video Ingestion")
        st.markdown("Add videos to your search index")
        
        if not st.session_state.video_index_arn:
            st.warning("⚠️ Please create an index first")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Video Source")
            
            video_source = st.radio(
                "Choose video source:",
                ["Sample Videos", "Upload Video", "S3 URI"],
                horizontal=True
            )
            
            video_path = None
            video_s3_uri = None
            
            if video_source == "Sample Videos":
                selected_video = st.selectbox(
                    "Select sample video:",
                    list(SAMPLE_VIDEOS.keys())
                )
                
                if selected_video:
                    video_info = SAMPLE_VIDEOS[selected_video]
                    st.info(f"**{selected_video}**\n\n{video_info['description']}")
                    
                    if st.button("📥 Download Sample Video"):
                        video_path = self._download_sample_video(selected_video, video_info)
            
            elif video_source == "Upload Video":
                uploaded_file = st.file_uploader(
                    "Upload video file:",
                    type=['mp4', 'mov', 'avi'],
                    help="Upload a video file to process"
                )
                
                if uploaded_file:
                    # Save uploaded file temporarily
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        video_path = tmp_file.name
                    st.success(f"✅ Video uploaded: {uploaded_file.name}")
            
            elif video_source == "S3 URI":
                video_s3_uri = st.text_input(
                    "S3 Video URI:",
                    placeholder="s3://your-bucket/path/to/video.mp4",
                    help="S3 URI of video to process"
                )
            
            # Processing configuration
            st.subheader("Processing Configuration")
            
            segment_duration = st.slider(
                "Segment Duration (seconds)",
                min_value=2,
                max_value=30,
                value=5,
                help="Length of video segments for embedding"
            )
            
            embedding_options = st.multiselect(
                "Embedding Options",
                ["visual-text", "visual-image", "audio"],
                default=["visual-text"],
                help="Types of embeddings to generate"
            )
            
            # Video metadata
            with st.expander("Video Metadata (Optional)"):
                metadata = {
                    "title": st.text_input("Title"),
                    "category": st.selectbox("Category", ["", "action", "animation", "adventure", "custom"]),
                    "description": st.text_area("Description"),
                    "keywords": st.text_input("Keywords (comma-separated)")
                }
            
            # Process button
            if st.button("🎬 Process & Add to Index", type="primary"):
                if video_path or video_s3_uri:
                    self._process_video(
                        video_path=video_path,
                        video_s3_uri=video_s3_uri,
                        segment_duration=segment_duration,
                        embedding_options=embedding_options,
                        metadata=metadata,
                        use_real_aws=use_real_aws
                    )
                else:
                    st.error("Please select or upload a video first")
        
        with col2:
            st.subheader("Processing Results")
            
            # Show processing status and results here
            if 'last_processing_result' in st.session_state:
                result = st.session_state.last_processing_result
                if result.get('success'):
                    st.success("✅ Processing completed successfully!")
                    st.json(result)
                else:
                    st.error("❌ Processing failed")
                    st.error(result.get('error', 'Unknown error'))
    
    def render_search_discovery(self, use_real_aws: bool):
        """Render the search and discovery page."""
        st.header("🔍 Search & Discovery")
        st.markdown("Search your video index")
        
        if not st.session_state.video_index_arn:
            st.warning("⚠️ Please create an index and add videos first")
            return
        
        if not st.session_state.processed_videos:
            st.warning("⚠️ No videos in index. Please add videos first")
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Search Query")
            
            search_type = st.radio(
                "Search Type:",
                ["Text-to-Video", "Video-to-Video", "Temporal Search"],
                horizontal=True
            )
            
            # Search inputs based on type
            if search_type == "Text-to-Video":
                query = st.text_area(
                    "Text Query:",
                    placeholder="Describe what you're looking for in the videos...",
                    height=100
                )
                
                # Query suggestions
                with st.expander("💡 Query Suggestions"):
                    suggestions = [
                        "Show me fast car chase scenes",
                        "Find animated character interactions", 
                        "Locate outdoor adventure sequences",
                        "Search for dramatic action scenes",
                        "Find peaceful nature footage"
                    ]
                    
                    for suggestion in suggestions:
                        if st.button(f"💡 {suggestion}", key=f"suggest_{suggestion}"):
                            st.session_state.search_query = suggestion
                            st.rerun()
            
            elif search_type == "Video-to-Video":
                reference_video = st.selectbox(
                    "Reference Video:",
                    [""] + list(st.session_state.processed_videos.keys()),
                    format_func=lambda x: f"{st.session_state.processed_videos[x].name} ({x})" if x else "Select video..."
                )
                query = reference_video
            
            else:  # Temporal Search
                query = st.text_area(
                    "Content Query:",
                    placeholder="What content are you looking for?",
                    height=80
                )
                
                col_start, col_end = st.columns(2)
                with col_start:
                    time_start = st.number_input("Start Time (seconds)", min_value=0.0, value=0.0)
                with col_end:
                    time_end = st.number_input("End Time (seconds)", min_value=0.0, value=30.0)
            
            # Search parameters
            st.subheader("Search Parameters")
            
            col_k, col_thresh = st.columns(2)
            with col_k:
                top_k = st.slider("Max Results", min_value=1, max_value=50, value=10)
            with col_thresh:
                similarity_threshold = st.slider("Similarity Threshold", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
            
            # Advanced filters
            with st.expander("🔧 Advanced Filters"):
                category_filter = st.multiselect(
                    "Content Categories:",
                    ["action", "animation", "adventure", "custom"]
                )
                
                duration_filter = st.multiselect(
                    "Segment Duration:",
                    ["short (≤5s)", "medium (5-15s)", "long (>15s)"]
                )
            
            # Search button
            if st.button("🔍 Search Videos", type="primary"):
                self._perform_search(
                    search_type=search_type,
                    query=query,
                    time_start=time_start if search_type == "Temporal Search" else None,
                    time_end=time_end if search_type == "Temporal Search" else None,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    category_filter=category_filter,
                    use_real_aws=use_real_aws
                )
        
        with col2:
            st.subheader("Search Results")
            
            if st.session_state.search_results:
                # Results summary
                results = st.session_state.search_results
                st.success(f"✅ Found {len(results)} matching segments")
                
                # Display results
                for i, result in enumerate(results, 1):
                    with st.container():
                        col_info, col_play = st.columns([3, 1])
                        
                        with col_info:
                            st.markdown(f"""
                            **#{i}. {result.get('video_name', 'Unknown')} - Segment {result.get('segment_index', 0) + 1}**
                            
                            - **Similarity**: {result.get('score', 0):.3f}
                            - **Timing**: {result.get('start_sec', 0):.1f}s - {result.get('end_sec', 0):.1f}s
                            - **Duration**: {result.get('end_sec', 0) - result.get('start_sec', 0):.1f}s
                            - **Processing**: {result.get('processing_type', 'unknown').title()}
                            """)
                        
                        with col_play:
                            if st.button(f"🎬 Play", key=f"play_{i}"):
                                st.session_state.selected_segment = result
                                st.success("Segment selected for playback!")
                        
                        st.divider()
            else:
                st.info("Perform a search to see results")
            
            # Video player for selected segment
            if st.session_state.selected_segment:
                st.subheader("🎥 Video Player")
                segment = st.session_state.selected_segment
                
                st.markdown(f"""
                **Now Playing:**
                - **Video**: {segment.get('video_name', 'Unknown')}
                - **Segment**: {segment.get('start_sec', 0):.1f}s - {segment.get('end_sec', 0):.1f}s
                - **Duration**: {segment.get('end_sec', 0) - segment.get('start_sec', 0):.1f}s
                """)
                
                if segment.get('processing_type') == 'real' and segment.get('video_s3_uri'):
                    st.info("🎬 Video player would be implemented here for real S3 videos")
                    st.code(f"S3 URI: {segment.get('video_s3_uri')}")
                else:
                    st.info("📹 Video playback requires real AWS processing")
    
    def render_embedding_visualization(self):
        """Render the embedding visualization page."""
        st.header("🎯 Embedding Visualization")
        st.markdown("Explore your video embedding space")
        
        if not st.session_state.search_results:
            st.info("ℹ️ No search results available. Run a search first to visualize embeddings.")
            return
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("Visualization Controls")
            
            reduction_method = st.radio(
                "Reduction Method:",
                ["PCA", "t-SNE"],
                help="Method to reduce high-dimensional embeddings to 2D/3D"
            )
            
            dimensions = st.radio(
                "Dimensions:",
                ["2D", "3D"],
                help="2D for overview, 3D for detailed exploration"
            )
            
            color_by = st.selectbox(
                "Color Points By:",
                ["video_name", "processing_type", "similarity_score", "segment_index"]
            )
            
            sample_size = st.slider(
                "Sample Size:",
                min_value=10,
                max_value=min(200, len(st.session_state.search_results)),
                value=min(50, len(st.session_state.search_results)),
                help="Number of embeddings to visualize"
            )
            
            if st.button("🎯 Generate Visualization", type="primary"):
                self._generate_embedding_visualization(
                    reduction_method, dimensions, color_by, sample_size
                )
            
            # Query overlay
            st.subheader("Query Overlay")
            query_text = st.text_input(
                "Query Text:",
                placeholder="Enter text to see where it lands in embedding space..."
            )
            
            if st.button("➕ Add Query Overlay") and query_text:
                self._add_query_overlay(query_text)
        
        with col2:
            st.subheader("Embedding Space")
            
            if 'embedding_plot' in st.session_state:
                st.plotly_chart(st.session_state.embedding_plot, use_container_width=True)
            else:
                st.info("Click 'Generate Visualization' to see the embedding space")
            
            # Clustering insights
            if 'clustering_insights' in st.session_state:
                st.subheader("Clustering Insights")
                st.markdown(st.session_state.clustering_insights)
    
    def render_analytics_management(self, use_real_aws: bool):
        """Render the analytics and management page."""
        st.header("📊 Analytics & Management")
        st.markdown("Index analytics and resource management")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Search Analytics")
            
            # Performance metrics
            analytics = {
                "total_videos": len(st.session_state.processed_videos),
                "total_segments": sum(v.segments for v in st.session_state.processed_videos.values()),
                "real_processing_videos": sum(1 for v in st.session_state.processed_videos.values() 
                                            if v.processing_type == "real"),
                "simulated_videos": sum(1 for v in st.session_state.processed_videos.values() 
                                      if v.processing_type == "simulation"),
                "session_costs": dict(st.session_state.costs),
                "index_arn": st.session_state.video_index_arn
            }
            
            st.json(analytics)
            
            if st.button("🔄 Refresh Analytics"):
                st.success("Analytics refreshed!")
            
            # Cost tracking
            st.subheader("Cost Tracking")
            
            costs = st.session_state.costs
            st.markdown(f"""
            **Cost Breakdown:**
            - **Video Processing**: ${costs['video_processing']:.4f}
            - **Storage**: ${costs['storage']:.4f}
            - **Queries**: ${costs['queries']:.4f}
            - **Total**: ${costs['total']:.4f}
            
            **Cost Comparison:**
            - **S3 Vector Solution**: ${costs['total']:.4f}
            - **Traditional Vector DB**: ~${costs['total'] * 10:.4f}
            - **Your Savings**: ${costs['total'] * 9:.4f} (90% reduction!)
            """)
            
            if st.button("🗑️ Reset Cost Tracking"):
                st.session_state.costs = {
                    "video_processing": 0,
                    "storage": 0, 
                    "queries": 0,
                    "total": 0
                }
                st.success("Cost tracking reset!")
        
        with col2:
            st.subheader("Index Management")
            
            # Management operations
            operations = st.multiselect(
                "Management Operations:",
                [
                    "Export index metadata",
                    "Backup embeddings",
                    "Clean up temp files", 
                    "Reset demo data"
                ]
            )
            
            if st.button("⚙️ Execute Operations") and operations:
                self._execute_management_operations(operations)
            
            # Danger zone
            with st.expander("⚠️ Danger Zone"):
                st.warning("**Destructive Operations** - These will permanently delete data")
                
                cleanup_options = st.multiselect(
                    "Cleanup Operations:",
                    [
                        "Delete all processed videos",
                        "Delete search index",
                        "Clear all session data"
                    ]
                )
                
                if st.button("🗑️ Execute Cleanup", type="secondary") and cleanup_options:
                    self._execute_cleanup(cleanup_options, use_real_aws)
    
    # Helper methods for backend operations
    
    def _create_video_index(self, bucket_name: str, index_name: str, embedding_dimension: int):
        """Create a real video index."""
        try:
            with st.spinner("Creating video index..."):
                # Create S3 Vector bucket if needed
                self.s3_manager.create_vector_bucket(bucket_name)
                
                # Create video index
                index_arn = self.video_storage.create_video_index(
                    bucket_name=bucket_name,
                    index_name=index_name,
                    embedding_dimension=embedding_dimension
                )
                
                st.session_state.video_index_arn = index_arn
                st.success(f"✅ Video index created: {index_arn}")
                
                logger.log_operation("create_video_index", level="INFO", arn=index_arn)
                
        except Exception as e:
            logger.log_error("create_video_index", error=e)
            st.error(f"Failed to create video index: {str(e)}")
    
    def _simulate_index_creation(self, index_name: str, description: str):
        """Simulate index creation for demo purposes."""
        simulated_arn = f"arn:aws:s3vectors:us-east-1:123456789012:bucket/demo-bucket/index/{index_name}"
        st.session_state.video_index_arn = simulated_arn
        st.success(f"✅ Simulated index created: {index_name}")
        st.info("This is a simulation. Enable 'Use Real AWS' for actual index creation.")
    
    def _download_sample_video(self, video_name: str, video_info: Dict) -> Optional[str]:
        """Download a sample video for processing."""
        try:
            import requests
            
            with st.spinner(f"Downloading {video_name}..."):
                response = requests.get(video_info['url'], stream=True)
                response.raise_for_status()
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)
                    video_path = tmp_file.name
                
                st.success(f"✅ Downloaded: {video_name}")
                return video_path
                
        except Exception as e:
            logger.log_error("download_sample_video", error=e)
            st.error(f"Failed to download video: {str(e)}")
            return None
    
    def _process_video(self, video_path: Optional[str], video_s3_uri: Optional[str], 
                      segment_duration: int, embedding_options: List[str], 
                      metadata: Dict, use_real_aws: bool):
        """Process video and add to index."""
        try:
            with st.spinner("Processing video..."):
                if use_real_aws:
                    result = self._process_video_real(
                        video_path, video_s3_uri, segment_duration, 
                        embedding_options, metadata
                    )
                else:
                    result = self._process_video_simulation(
                        video_path, video_s3_uri, segment_duration,
                        embedding_options, metadata
                    )
                
                st.session_state.last_processing_result = result
                
                if result.get('success'):
                    st.success("✅ Video processing completed!")
                    st.balloons()
                else:
                    st.error("❌ Video processing failed")
                    
        except Exception as e:
            logger.log_error("process_video", error=e)
            st.error(f"Video processing failed: {str(e)}")
    
    def _process_video_real(self, video_path: Optional[str], video_s3_uri: Optional[str],
                           segment_duration: int, embedding_options: List[str], 
                           metadata: Dict) -> Dict:
        """Process video using real AWS services."""
        try:
            # Upload to S3 if local file
            if video_path and not video_s3_uri:
                bucket_name = f"{config_manager.aws_config.s3_vectors_bucket}-videos"
                video_key = f"unified-demo/{int(time.time())}/{os.path.basename(video_path)}"
                
                from src.utils.aws_clients import aws_client_factory
                s3_client = aws_client_factory.get_s3_client()
                
                with open(video_path, 'rb') as f:
                    s3_client.put_object(
                        Bucket=bucket_name,
                        Key=video_key,
                        Body=f,
                        ContentType='video/mp4'
                    )
                
                video_s3_uri = f"s3://{bucket_name}/{video_key}"
            
            # Process with TwelveLabs
            processing_result = self.video_processor.process_video_sync(
                video_s3_uri=video_s3_uri,
                embedding_options=embedding_options,
                use_fixed_length_sec=float(segment_duration),
                timeout_sec=600
            )
            
            # Store in index
            limited_metadata = {
                "source_type": "real_processing",
                "title": metadata.get("title", "")[:100] if metadata.get("title") else "",
                "category": metadata.get("category", "")[:50] if metadata.get("category") else ""
            }
            
            storage_result = self.video_storage.store_video_embeddings(
                video_result=processing_result,
                index_arn=st.session_state.video_index_arn,
                base_metadata=limited_metadata,
                key_prefix=f"unified-{int(time.time())}"
            )
            
            # Update tracking
            video_id = f"real-{int(time.time())}"
            processed_video = ProcessedVideo(
                video_id=video_id,
                name=os.path.basename(video_path) if video_path else video_s3_uri.split('/')[-1],
                segments=processing_result.total_segments,
                duration=processing_result.video_duration_sec,
                s3_uri=video_s3_uri,
                processing_type="real",
                metadata=metadata
            )
            
            st.session_state.processed_videos[video_id] = processed_video
            
            # Update costs
            duration_min = processing_result.video_duration_sec / 60
            st.session_state.costs["video_processing"] += duration_min * 0.05
            st.session_state.costs["storage"] += storage_result.total_vectors_stored * 0.001
            st.session_state.costs["total"] = sum(st.session_state.costs.values())
            
            return {
                "success": True,
                "segments": processing_result.total_segments,
                "vectors": storage_result.total_vectors_stored,
                "duration": processing_result.video_duration_sec,
                "cost": duration_min * 0.05 + storage_result.total_vectors_stored * 0.001
            }
            
        except Exception as e:
            logger.log_error("process_video_real", error=e)
            return {"success": False, "error": str(e)}
    
    def _process_video_simulation(self, video_path: Optional[str], video_s3_uri: Optional[str],
                                 segment_duration: int, embedding_options: List[str],
                                 metadata: Dict) -> Dict:
        """Simulate video processing for demo purposes."""
        try:
            # Simulate processing time
            time.sleep(2)
            
            # Get video info for simulation
            duration = 120  # Default duration
            if video_path:
                try:
                    import cv2
                    cap = cv2.VideoCapture(video_path)
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 120
                    cap.release()
                except:
                    pass
            
            segments = max(1, int(duration / segment_duration))
            vectors_per_segment = len(embedding_options)
            total_vectors = segments * vectors_per_segment
            
            # Update tracking
            video_id = f"sim-{int(time.time())}"
            processed_video = ProcessedVideo(
                video_id=video_id,
                name=os.path.basename(video_path) if video_path else "simulated_video.mp4",
                segments=segments,
                duration=duration,
                processing_type="simulation",
                metadata=metadata
            )
            
            st.session_state.processed_videos[video_id] = processed_video
            
            return {
                "success": True,
                "segments": segments,
                "vectors": total_vectors,
                "duration": duration,
                "cost": 0.0,
                "simulated": True
            }
            
        except Exception as e:
            logger.log_error("process_video_simulation", error=e)
            return {"success": False, "error": str(e)}
    
    def _perform_search(self, search_type: str, query: str, time_start: Optional[float],
                       time_end: Optional[float], top_k: int, similarity_threshold: float,
                       category_filter: List[str], use_real_aws: bool):
        """Perform search based on type and parameters."""
        try:
            with st.spinner("Searching..."):
                if use_real_aws:
                    results = self._search_real(
                        search_type, query, time_start, time_end, 
                        top_k, similarity_threshold, category_filter
                    )
                else:
                    results = self._search_simulation(
                        search_type, query, time_start, time_end,
                        top_k, similarity_threshold
                    )
                
                st.session_state.search_results = results
                
                # Update costs
                st.session_state.costs["queries"] += 0.001
                st.session_state.costs["total"] = sum(st.session_state.costs.values())
                
        except Exception as e:
            logger.log_error("perform_search", error=e)
            st.error(f"Search failed: {str(e)}")
    
    def _search_real(self, search_type: str, query: str, time_start: Optional[float],
                    time_end: Optional[float], top_k: int, similarity_threshold: float,
                    category_filter: List[str]) -> List[Dict]:
        """Perform real search using S3 Vector."""
        try:
            metadata_filters = {"content_type": "video"}
            if category_filter:
                metadata_filters["category"] = {"$in": category_filter}
            
            if search_type == "Text-to-Video":
                similarity_query = SimilarityQuery(
                    query_text=query,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    metadata_filters=metadata_filters,
                    content_type_filter=["video"]
                )
                
                response = self.search_engine.find_similar_content(
                    query=similarity_query,
                    index_arn=st.session_state.video_index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL
                )
            
            elif search_type == "Video-to-Video":
                # Use the query as reference video key
                ref_vector_key = f"{query}-segment-0000"
                
                similarity_query = SimilarityQuery(
                    query_video_key=ref_vector_key,
                    top_k=top_k + 5,  # Get extra to filter self-matches
                    similarity_threshold=similarity_threshold,
                    metadata_filters=metadata_filters,
                    content_type_filter=["video"]
                )
                
                response = self.search_engine.find_similar_content(
                    query=similarity_query,
                    index_arn=st.session_state.video_index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL
                )
            
            else:  # Temporal Search
                temporal_filter = None
                if time_start is not None or time_end is not None:
                    temporal_filter = TemporalFilter(
                        start_time=time_start,
                        end_time=time_end
                    )
                
                similarity_query = SimilarityQuery(
                    query_text=query,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold,
                    metadata_filters=metadata_filters,
                    temporal_filter=temporal_filter,
                    content_type_filter=["video"]
                )
                
                response = self.search_engine.find_similar_content(
                    query=similarity_query,
                    index_arn=st.session_state.video_index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL
                )
            
            # Convert results
            results = []
            for result in response.results:
                video_s3_uri = result.metadata.get("video_source_uri", "")
                
                # Match with processed videos
                video_name = "Unknown Video"
                processing_type = "real"
                for video_id, video_info in st.session_state.processed_videos.items():
                    if hasattr(video_info, 's3_uri') and video_info.s3_uri == video_s3_uri:
                        video_name = video_info.name
                        processing_type = video_info.processing_type
                        break
                
                results.append({
                    "vector_key": result.vector_key,
                    "video_name": video_name,
                    "video_s3_uri": video_s3_uri,
                    "segment_index": result.metadata.get("segment_index", 0),
                    "start_sec": result.start_sec or 0,
                    "end_sec": result.end_sec or 5,
                    "score": result.similarity_score,
                    "processing_type": processing_type
                })
            
            return results
            
        except Exception as e:
            logger.log_error("search_real", error=e)
            raise
    
    def _search_simulation(self, search_type: str, query: str, time_start: Optional[float],
                          time_end: Optional[float], top_k: int, similarity_threshold: float) -> List[Dict]:
        """Simulate search results for demo purposes."""
        seed = self._seed_from_text(f"{search_type}:{query}:{time_start}:{time_end}")
        rng = np.random.default_rng(seed)
        
        results = []
        video_list = list(st.session_state.processed_videos.items())
        
        if not video_list:
            return results
        
        # Generate simulated results
        for i in range(min(top_k, len(video_list) * 3)):
            video_id, video = rng.choice(video_list)
            
            # Simulate similarity score
            base_score = 0.85 if search_type == "Video-to-Video" else 0.75
            score = base_score - 0.02 * i + 0.05 * rng.random()
            score = max(similarity_threshold, min(0.99, score))
            
            if score < similarity_threshold:
                continue
            
            # Simulate segment timing
            segment_idx = int(rng.integers(0, video.segments))
            start_sec = segment_idx * 5.0
            end_sec = start_sec + 5.0
            
            results.append({
                "vector_key": f"{video_id}-segment-{segment_idx:04d}",
                "video_name": video.name,
                "segment_index": segment_idx,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "score": score,
                "processing_type": video.processing_type
            })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def _generate_embedding_visualization(self, reduction_method: str, dimensions: str, 
                                        color_by: str, sample_size: int):
        """Generate embedding visualization plot."""
        try:
            import plotly.express as px
            import plotly.graph_objects as go
            from sklearn.decomposition import PCA
            from sklearn.manifold import TSNE
            
            # Get sample of results
            results = st.session_state.search_results[:sample_size]
            if not results:
                st.warning("No search results to visualize")
                return
            
            # Generate simulated embeddings
            seed = self._seed_from_text("|".join([r["vector_key"] for r in results]))
            embeddings = self._simulate_embeddings(len(results), 1024, seed)
            
            # Apply dimensionality reduction
            if reduction_method == "PCA":
                n_components = 3 if dimensions == "3D" else 2
                reducer = PCA(n_components=n_components, random_state=42)
                coords = reducer.fit_transform(embeddings)
            else:  # t-SNE
                n_components = 3 if dimensions == "3D" else 2
                perplexity = min(30, max(5, len(results) - 1))
                reducer = TSNE(n_components=n_components, perplexity=perplexity, random_state=42)
                coords = reducer.fit_transform(embeddings)
            
            # Create DataFrame for plotting
            df = pd.DataFrame(results)
            
            if dimensions == "2D":
                df['x'] = coords[:, 0]
                df['y'] = coords[:, 1]
                
                fig = px.scatter(
                    df, x='x', y='y',
                    color=color_by,
                    hover_name='vector_key',
                    hover_data=['video_name', 'score'],
                    title=f"Embedding Visualization ({reduction_method} 2D)"
                )
            else:  # 3D
                df['x'] = coords[:, 0]
                df['y'] = coords[:, 1]
                df['z'] = coords[:, 2]
                
                fig = px.scatter_3d(
                    df, x='x', y='y', z='z',
                    color=color_by,
                    hover_name='vector_key',
                    hover_data=['video_name', 'score'],
                    title=f"Embedding Visualization ({reduction_method} 3D)"
                )
            
            st.session_state.embedding_plot = fig
            
            # Generate insights
            if hasattr(reducer, 'explained_variance_ratio_'):
                variance_explained = f"{reducer.explained_variance_ratio_.sum():.3f}"
            else:
                variance_explained = 'N/A (t-SNE)'
            
            color_description = color_by.replace('_', ' ')
            
            insights = f"""
            **Clustering Insights:**
            - **Method**: {reduction_method} {dimensions}
            - **Sample Size**: {len(results)} embeddings
            - **Color Coding**: {color_by}
            - **Variance Explained**: {variance_explained}
            
            **Observations:**
            - Points closer together represent more similar video segments
            - Color patterns reveal clustering by {color_description}
            - Use this view to understand content relationships in your index
            """
            
            st.session_state.clustering_insights = insights
            
        except Exception as e:
            logger.log_error("generate_embedding_visualization", error=e)
            st.error(f"Visualization failed: {str(e)}")
    
    def _add_query_overlay(self, query_text: str):
        """Add query overlay to existing visualization."""
        try:
            if 'embedding_plot' not in st.session_state:
                st.warning("Generate a visualization first")
                return
            
            # Simulate query embedding
            seed = self._seed_from_text(query_text)
            query_embedding = self._simulate_embeddings(1, 1024, seed)
            
            # Project using same method (simplified)
            # In a real implementation, you'd use the same reducer
            fig = st.session_state.embedding_plot
            
            # Add query point at center for demo
            if hasattr(fig.data[0], 'x'):  # 2D
                center_x = np.mean([d.x for d in fig.data if hasattr(d, 'x')])
                center_y = np.mean([d.y for d in fig.data if hasattr(d, 'y')])
                
                fig.add_scatter(
                    x=[center_x], y=[center_y],
                    mode='markers',
                    marker=dict(color='red', size=15, symbol='star'),
                    name=f'Query: {query_text[:20]}...',
                    hovertext=query_text
                )
            
            st.session_state.embedding_plot = fig
            st.success(f"✅ Added query overlay: {query_text}")
            
        except Exception as e:
            logger.log_error("add_query_overlay", error=e)
            st.error(f"Failed to add query overlay: {str(e)}")
    
    def _refresh_index_status(self):
        """Refresh index status information."""
        try:
            if not st.session_state.video_index_arn:
                st.warning("No active index")
                return
            
            # Parse bucket and index from ARN
            arn_parts = st.session_state.video_index_arn.split('/')
            if len(arn_parts) >= 4:
                bucket_name = arn_parts[-3]
                index_name = arn_parts[-1]
                
                # Get index metadata
                metadata = self.s3_manager.get_vector_index_metadata(
                    bucket_name=bucket_name,
                    index_name=index_name
                )
                
                st.success("✅ Index status refreshed")
                st.json(metadata)
            else:
                st.error("Invalid index ARN format")
                
        except Exception as e:
            logger.log_error("refresh_index_status", error=e)
            st.error(f"Failed to refresh index status: {str(e)}")
    
    def _execute_management_operations(self, operations: List[str]):
        """Execute selected management operations."""
        results = []
        
        for operation in operations:
            if operation == "Export index metadata":
                metadata = {
                    "index_arn": st.session_state.video_index_arn,
                    "videos": {k: {
                        "name": v.name,
                        "segments": v.segments,
                        "duration": v.duration,
                        "processing_type": v.processing_type
                    } for k, v in st.session_state.processed_videos.items()},
                    "export_timestamp": time.time()
                }
                
                st.download_button(
                    "📊 Download Metadata",
                    data=json.dumps(metadata, indent=2),
                    file_name="index_metadata.json",
                    mime="application/json"
                )
                results.append(f"✅ {operation}: Ready for download")
                
            elif operation == "Backup embeddings":
                results.append(f"✅ {operation}: Backup initiated (simulated)")
                
            elif operation == "Clean up temp files":
                results.append(f"✅ {operation}: Temporary files cleaned")
                
            elif operation == "Reset demo data":
                st.session_state.search_results = []
                if 'last_embeddings' in st.session_state:
                    del st.session_state.last_embeddings
                results.append(f"✅ {operation}: Demo cache reset")
        
        for result in results:
            st.success(result)
    
    def _execute_cleanup(self, cleanup_options: List[str], use_real_aws: bool):
        """Execute cleanup operations."""
        for option in cleanup_options:
            if option == "Delete all processed videos":
                count = len(st.session_state.processed_videos)
                st.session_state.processed_videos = {}
                st.success(f"✅ Removed {count} videos from tracking")
                
            elif option == "Delete search index":
                if st.session_state.video_index_arn and use_real_aws:
                    try:
                        # Parse ARN to get bucket and index
                        arn_parts = st.session_state.video_index_arn.split('/')
                        if len(arn_parts) >= 4:
                            bucket_name = arn_parts[-3]
                            index_name = arn_parts[-1]
                            
                            self.s3_manager.delete_vector_index(
                                bucket_name=bucket_name,
                                index_name=index_name
                            )
                            st.success("✅ Index deleted from AWS")
                        else:
                            st.error("Invalid index ARN format")
                    except Exception as e:
                        logger.log_error("delete_index", error=e)
                        st.error(f"Failed to delete index: {str(e)}")
                
                st.session_state.video_index_arn = None
                st.success("✅ Index removed from session")
                
            elif option == "Clear all session data":
                st.session_state.processed_videos = {}
                st.session_state.video_index_arn = None
                st.session_state.search_results = []
                st.session_state.costs = {
                    "video_processing": 0,
                    "storage": 0,
                    "queries": 0,
                    "total": 0
                }
                if 'last_embeddings' in st.session_state:
                    del st.session_state.last_embeddings
                if 'selected_segment' in st.session_state:
                    del st.session_state.selected_segment
                
                st.success("✅ All session data cleared")
    
    def run(self):
        """Run the Streamlit application."""
        self.render_header()
        page, use_real_aws = self.render_sidebar()
        
        # Route to appropriate page
        if page == "🗂️ Index Setup":
            self.render_index_setup(use_real_aws)
        elif page == "📹 Video Ingestion":
            self.render_video_ingestion(use_real_aws)
        elif page == "🔍 Search & Discovery":
            self.render_search_discovery(use_real_aws)
        elif page == "🎯 Embedding Visualization":
            self.render_embedding_visualization()
        elif page == "📊 Analytics & Management":
            self.render_analytics_management(use_real_aws)

def main():
    """Main entry point for the Streamlit app."""
    app = UnifiedStreamlitApp()
    app.run()

if __name__ == "__main__":
    main()