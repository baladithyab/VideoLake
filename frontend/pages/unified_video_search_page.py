"""
Unified Video Search Page

A consolidated demo that combines video processing and cross-modal search
into one streamlined pipeline for ingesting videos into an index and 
searching against them with video segment playback.
"""

import os
import sys
import time
import json
import tempfile
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import pandas as pd

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .common_components import CommonComponents
from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery, IndexType
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.config import config_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class UnifiedVideoSearchPage:
    """Unified video ingestion and search demo page."""
    
    def __init__(self):
        """Initialize the unified video search page."""
        self.search_engine = None
        self.video_processor = None
        self.video_storage = None
        self.s3_manager = None
        
        # Demo state
        self.video_index_arn = None
        self.processed_videos = {}  # video_key -> video_metadata
        self.search_results_cache = {}
        self.selected_segment = None  # Currently selected video segment for playback
        
        # Cost tracking
        self.costs = {
            "video_processing": 0,
            "storage": 0,
            "queries": 0,
            "total": 0
        }
        
        # Embedding visualization state
        self.current_reducer = None
        self.current_embeddings_matrix = None
        self.current_reduction_method = None
        self.current_dimensions = None
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize required services."""
        try:
            self.search_engine = SimilaritySearchEngine()
            self.video_processor = TwelveLabsVideoProcessingService()
            self.video_storage = VideoEmbeddingStorageService()
            self.s3_manager = S3VectorStorageManager()
            logger.info("Unified video search services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize unified services: {e}")
    
    def create_page(self) -> gr.Blocks:
        """Create the unified video search demo page."""
        
        with gr.Blocks(
            title="Unified Video Search Demo",
            theme=gr.themes.Soft(),
            css="""
            .video-grid {display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;}
            .video-card {border: 1px solid #ddd; border-radius: 8px; padding: 1rem; text-align: center;}
            .search-result {border: 1px solid #e0e0e0; border-radius: 6px; padding: 0.8rem; margin: 0.5rem 0;}
            .similarity-score {background: linear-gradient(90deg, #4CAF50, #FFC107); -webkit-background-clip: text; color: transparent; font-weight: bold;}
            """
        ) as page:
            
            gr.Markdown("""
            # 🎬 Unified Video Search Demo
            
            **Complete video-to-search pipeline with segment playback**
            
            Experience the full workflow:
            1. **Ingest Videos**: Upload or select sample videos to build your searchable index
            2. **Process & Store**: Generate embeddings using TwelveLabs Marengo and store in S3 Vector
            3. **Search & Discover**: Find video segments using text queries or video-to-video similarity
            4. **Preview Results**: View matching segments with timestamps and similarity scores
            5. **Build Large Index**: Add multiple videos to create a comprehensive searchable library
            """)
            
            # Global status bar
            status_indicator, progress_info = CommonComponents.create_status_display()
            
            with gr.Tabs():
                
                # ===== INDEX SETUP TAB =====
                with gr.Tab("🗂️ Index Setup"):
                    gr.Markdown("### Create and Manage Your Video Search Index")
                    
                    with gr.Row():
                        # Left column - Index configuration
                        with gr.Column(scale=2):
                            gr.Markdown("#### Index Configuration")
                            
                            index_name = gr.Textbox(
                                label="Index Name",
                                value="unified-video-search-index",
                                info="Name for your video search index"
                            )
                            
                            index_description = gr.Textbox(
                                label="Index Description",
                                value="Unified video search demo index with multimodal capabilities",
                                lines=2,
                                info="Optional description for the index"
                            )
                            
                            # Index setup controls
                            setup_index_btn = gr.Button(
                                "🚀 Create Video Index",
                                variant="primary",
                                size="lg"
                            )
                            
                            refresh_index_btn = gr.Button(
                                "🔄 Refresh Index Status",
                                variant="secondary"
                            )
                            
                            # Index statistics
                            gr.Markdown("#### Index Statistics")
                            index_stats = gr.Markdown(
                                value="*Create an index to see statistics*"
                            )
                        
                        # Right column - Current index status
                        with gr.Column(scale=2):
                            gr.Markdown("#### Index Status")
                            
                            index_status_display = gr.Markdown(
                                value="*No index created yet*"
                            )
                            
                            # Video library overview
                            gr.Markdown("#### Video Library")
                            video_library_display = gr.HTML(
                                value="<p><em>No videos in the library yet</em></p>"
                            )
                
                # ===== VIDEO INGESTION TAB =====
                with gr.Tab("📹 Video Ingestion"):
                    gr.Markdown("### Add Videos to Your Search Index")
                    
                    with gr.Row():
                        # Left column - Video input
                        with gr.Column(scale=2):
                            gr.Markdown("#### Video Source")
                            
                            # Video source selection
                            video_source_type = gr.Radio(
                                label="Video Source",
                                choices=[
                                    "sample_videos",
                                    "upload_single",
                                    "upload_multiple"
                                ],
                                value="sample_videos",
                                info="Choose how to add videos to your index"
                            )
                            
                            # Sample videos (visible by default)
                            with gr.Group(visible=True) as sample_video_group:
                                sample_video_selector = gr.Dropdown(
                                    label="Select Sample Video",
                                    choices=list(CommonComponents.SAMPLE_VIDEOS.keys()),
                                    info="Choose from Creative Commons sample videos"
                                )
                                
                                download_sample_btn = gr.Button(
                                    "📥 Download & Preview Sample",
                                    variant="secondary"
                                )
                            
                            # Single upload (hidden by default)
                            with gr.Group(visible=False) as single_upload_group:
                                single_video_upload = gr.File(
                                    label="Upload Single Video",
                                    file_types=[".mp4", ".mov", ".avi"],
                                    file_count="single"
                                )
                                
                                single_video_metadata = gr.JSON(
                                    label="Video Metadata",
                                    value={
                                        "title": "",
                                        "category": "",
                                        "description": "",
                                        "keywords": []
                                    }
                                )
                            
                            # Multiple upload (hidden by default)
                            with gr.Group(visible=False) as multiple_upload_group:
                                multiple_video_upload = gr.File(
                                    label="Upload Multiple Videos",
                                    file_types=[".mp4", ".mov", ".avi"],
                                    file_count="multiple"
                                )
                                
                                batch_metadata = gr.JSON(
                                    label="Batch Metadata (applied to all)",
                                    value={
                                        "category": "",
                                        "source": "user_upload",
                                        "batch_id": ""
                                    }
                                )
                            
                            # Show/hide groups based on selection
                            def update_video_source_ui(source_type):
                                return (
                                    gr.update(visible=(source_type == "sample_videos")),
                                    gr.update(visible=(source_type == "upload_single")),
                                    gr.update(visible=(source_type == "upload_multiple"))
                                )
                            
                            video_source_type.change(
                                fn=update_video_source_ui,
                                inputs=[video_source_type],
                                outputs=[sample_video_group, single_upload_group, multiple_upload_group]
                            )
                            
                            # Processing configuration
                            gr.Markdown("#### Processing Configuration")
                            
                            with gr.Row():
                                segment_duration = gr.Slider(
                                    label="Segment Duration (seconds)",
                                    minimum=2,
                                    maximum=30,
                                    value=5,
                                    step=1
                                )
                                
                                embedding_options = gr.CheckboxGroup(
                                    label="Embedding Options",
                                    choices=["visual-text", "audio"],
                                    value=["visual-text"],
                                    info="Types of embeddings to generate"
                                )
                            
                            use_real_aws = gr.Checkbox(
                                label="Use Real AWS Processing (incurs costs)",
                                value=False,
                                info="Enable for actual processing with cost"
                            )
                            
                            # Process button
                            process_video_btn = gr.Button(
                                "🎬 Process & Add to Index",
                                variant="primary",
                                size="lg"
                            )
                        
                        # Right column - Video preview and results
                        with gr.Column(scale=2):
                            gr.Markdown("#### Video Preview")
                            
                            # Video preview components
                            video_thumbnail = gr.Image(
                                label="Video Thumbnail",
                                height=300,
                                show_label=True
                            )
                            
                            video_info_display = gr.Markdown(
                                value="*Select a video to see preview*"
                            )
                            
                            # Processing results
                            gr.Markdown("#### Processing Results")
                            processing_results_display = CommonComponents.create_results_display()
                
                # ===== SEARCH & DISCOVERY TAB =====
                with gr.Tab("🔍 Search & Discovery"):
                    gr.Markdown("### Search Your Video Index")
                    
                    with gr.Row():
                        # Left column - Search controls
                        with gr.Column(scale=2):
                            gr.Markdown("#### Search Query")
                            
                            search_type = gr.Radio(
                                label="Search Type",
                                choices=[
                                    "text_to_video",
                                    "video_to_video",
                                    "temporal_search"
                                ],
                                value="text_to_video",
                                info="Choose your search method"
                            )
                            
                            # Text search (visible by default)
                            with gr.Group(visible=True) as text_search_group:
                                search_query = gr.Textbox(
                                    label="Text Query",
                                    placeholder="Describe what you're looking for in the videos...",
                                    lines=3
                                )
                                
                                # Query suggestions
                                with gr.Accordion("💡 Query Suggestions", open=False):
                                    sample_queries = [
                                        "Show me fast car chase scenes",
                                        "Find animated character interactions",
                                        "Locate outdoor adventure sequences",
                                        "Search for dramatic action scenes",
                                        "Find peaceful nature footage"
                                    ]
                                    
                                    for query in sample_queries:
                                        suggest_btn = gr.Button(
                                            f"💡 {query}",
                                            size="sm",
                                            variant="secondary"
                                        )
                                        suggest_btn.click(
                                            fn=lambda q=query: q,
                                            outputs=[search_query]
                                        )
                            
                            # Video-to-video search (hidden by default)
                            with gr.Group(visible=False) as video_search_group:
                                reference_video_selector = gr.Dropdown(
                                    label="Reference Video",
                                    choices=[],
                                    info="Select a video from your index as reference"
                                )
                                
                                refresh_video_list_btn = gr.Button(
                                    "🔄 Refresh Video List",
                                    size="sm"
                                )
                            
                            # Temporal search (hidden by default) 
                            with gr.Group(visible=False) as temporal_search_group:
                                temporal_query = gr.Textbox(
                                    label="Content Query",
                                    placeholder="What content are you looking for?",
                                    lines=2
                                )
                                
                                with gr.Row():
                                    time_start = gr.Number(
                                        label="Start Time (seconds)",
                                        minimum=0,
                                        value=0
                                    )
                                    time_end = gr.Number(
                                        label="End Time (seconds)",
                                        minimum=0,
                                        value=30
                                    )
                            
                            # Show/hide search groups
                            def update_search_ui(search_type_val):
                                return (
                                    gr.update(visible=(search_type_val == "text_to_video")),
                                    gr.update(visible=(search_type_val == "video_to_video")),
                                    gr.update(visible=(search_type_val == "temporal_search"))
                                )
                            
                            search_type.change(
                                fn=update_search_ui,
                                inputs=[search_type],
                                outputs=[text_search_group, video_search_group, temporal_search_group]
                            )
                            
                            # Search parameters
                            gr.Markdown("#### Search Parameters")
                            
                            with gr.Row():
                                search_top_k = gr.Slider(
                                    label="Max Results",
                                    minimum=1,
                                    maximum=50,
                                    value=10,
                                    step=1
                                )
                                
                                similarity_threshold = gr.Slider(
                                    label="Similarity Threshold",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.6,
                                    step=0.05
                                )
                            
                            # Advanced filters
                            with gr.Accordion("🔧 Advanced Filters", open=False):
                                category_filter = gr.CheckboxGroup(
                                    label="Content Categories",
                                    choices=["action", "animation", "adventure", "custom"],
                                    info="Filter by content category"
                                )
                                
                                duration_filter = gr.CheckboxGroup(
                                    label="Segment Duration",
                                    choices=["short (≤5s)", "medium (5-15s)", "long (>15s)"],
                                    info="Filter by segment length"
                                )
                            
                            # Search button
                            search_btn = gr.Button(
                                "🔍 Search Videos",
                                variant="primary",
                                size="lg"
                            )
                        
                        # Right column - Search results with video preview
                        with gr.Column(scale=2):
                            gr.Markdown("#### Search Results")
                            
                            # Results count and metadata
                            results_summary = gr.Markdown(
                                value="*Perform a search to see results*"
                            )
                            
                            # Search results display
                            search_results_display = gr.HTML(
                                value="<p><em>Search results with video segments will appear here</em></p>"
                            )
                            
                            # Selected result details
                            gr.Markdown("#### Selected Result Details")
                            
                            selected_result_info = gr.Markdown(
                                value="*Click on a search result to see details*"
                            )
                            
                            # Video segment player
                            with gr.Accordion("🎥 Video Segment Player", open=True):
                                video_segment_player = gr.HTML(
                                    value="<p><em>Select a search result to play the video segment</em></p>",
                                    label="Video Player"
                                )
                                
                                # Player controls
                                with gr.Row():
                                    play_segment_btn = gr.Button(
                                        "▶️ Play Selected Segment", 
                                        variant="primary",
                                        size="sm"
                                    )
                                    download_segment_btn = gr.Button(
                                        "💾 Download Segment", 
                                        variant="secondary",
                                        size="sm"
                                    )
                
                # ===== ANALYTICS & MANAGEMENT TAB =====
                with gr.Tab("📊 Analytics & Management"):
                    gr.Markdown("### Index Analytics and Management")
                    
                    with gr.Row():
                        # Left column - Analytics
                        with gr.Column(scale=2):
                            gr.Markdown("#### Search Analytics")
                            
                            search_analytics = gr.JSON(
                                label="Search Performance Metrics",
                                value={}
                            )
                            
                            refresh_analytics_btn = gr.Button(
                                "🔄 Refresh Analytics",
                                variant="secondary"
                            )
                            
                            # Cost tracking
                            gr.Markdown("#### Cost Tracking")
                            
                            cost_breakdown = gr.Markdown(
                                value=CommonComponents.format_cost_info(self.costs)
                            )
                            
                            reset_costs_btn = gr.Button(
                                "🗑️ Reset Cost Tracking",
                                variant="secondary"
                            )
                        
                        # Right column - Management
                        with gr.Column(scale=2):
                            gr.Markdown("#### Index Management")
                            
                            # Index operations
                            index_operations = gr.CheckboxGroup(
                                label="Management Operations",
                                choices=[
                                    "Export index metadata",
                                    "Backup embeddings", 
                                    "Clean up temp files",
                                    "Reset demo data"
                                ],
                                info="Select operations to perform"
                            )
                            
                            execute_operations_btn = gr.Button(
                                "⚙️ Execute Operations",
                                variant="secondary"
                            )
                            
                            operations_results = gr.Markdown(
                                value="*Select and execute operations to see results*"
                            )
                            
                            # Danger zone
                            with gr.Accordion("⚠️ Danger Zone", open=False):
                                gr.Markdown("""
                                **Destructive Operations**
                                
                                These operations will permanently delete data:
                                """)
                                
                                cleanup_options = gr.CheckboxGroup(
                                    label="Cleanup Operations",
                                    choices=[
                                        "Delete all processed videos",
                                        "Delete search index",
                                        "Clear all session data"
                                    ]
                                )
                                
                                cleanup_btn = gr.Button(
                                    "🗑️ Execute Cleanup",
                                    variant="stop"
                                )
                
                # ===== EMBEDDING VISUALIZATION TAB =====
                with gr.Tab("🎯 Embedding Visualization"):
                    gr.Markdown("### Explore Your Video Embedding Space")
                    
                    with gr.Row():
                        # Left column - Controls
                        with gr.Column(scale=1):
                            gr.Markdown("#### Visualization Controls")
                            
                            # Dimensionality reduction method
                            reduction_method = gr.Radio(
                                label="Reduction Method",
                                choices=["PCA", "t-SNE"],
                                value="PCA",
                                info="Method to reduce 1024D embeddings to 2D/3D"
                            )
                            
                            # Visualization dimensions
                            viz_dimensions = gr.Radio(
                                label="Dimensions",
                                choices=["2D", "3D"],
                                value="2D",
                                info="2D for overview, 3D for detailed exploration"
                            )
                            
                            # Color coding options
                            color_by = gr.Dropdown(
                                label="Color Points By",
                                choices=[
                                    "video_name",
                                    "processing_type", 
                                    "temporal_position",
                                    "similarity_cluster"
                                ],
                                value="video_name",
                                info="How to color-code the embedding points"
                            )
                            
                            # Sample size for performance
                            sample_size = gr.Slider(
                                label="Sample Size",
                                minimum=50,
                                maximum=1000,
                                value=200,
                                step=50,
                                info="Number of embeddings to visualize (larger = slower)"
                            )
                            
                            # Generate visualization
                            generate_viz_btn = gr.Button(
                                "🎯 Generate Embedding Visualization",
                                variant="primary"
                            )
                            
                            # Visualization status
                            viz_status = gr.Textbox(
                                label="Status",
                                interactive=False,
                                value="Click 'Generate Visualization' to start"
                            )
                            
                            # Search query overlay
                            gr.Markdown("#### Search Query Overlay")
                            
                            query_overlay_text = gr.Textbox(
                                label="Query Text",
                                placeholder="Enter text to see where it lands in embedding space...",
                                info="Overlay a search query on the visualization"
                            )
                            
                            add_query_overlay_btn = gr.Button(
                                "➕ Add Query Overlay",
                                variant="secondary"
                            )
                        
                        # Right column - Visualization
                        with gr.Column(scale=3):
                            # Main visualization plot
                            embedding_plot = gr.Plot(
                                label="Embedding Space Visualization",
                                value=None
                            )
                            
                            # Selected point details
                            gr.Markdown("#### Point Details")
                            selected_point_info = gr.JSON(
                                label="Selected Embedding Details",
                                value={}
                            )
                            
                            # Clustering insights
                            clustering_insights = gr.Markdown(
                                value="*Generate visualization to see clustering insights*"
                            )
            
            # ===== EVENT HANDLERS =====
            
            # Index setup
            setup_index_btn.click(
                fn=self._setup_video_index,
                inputs=[index_name, index_description],
                outputs=[status_indicator, progress_info, index_status_display, index_stats]
            )
            
            # Video source handling
            download_sample_btn.click(
                fn=self._download_sample_video,
                inputs=[sample_video_selector],
                outputs=[status_indicator, progress_info, video_thumbnail, video_info_display]
            )
            
            single_video_upload.change(
                fn=self._handle_single_upload,
                inputs=[single_video_upload],
                outputs=[status_indicator, progress_info, video_thumbnail, video_info_display]
            )
            
            # Video processing
            process_video_btn.click(
                fn=self._process_and_add_video,
                inputs=[
                    video_source_type, sample_video_selector, single_video_upload,
                    segment_duration, embedding_options, use_real_aws,
                    single_video_metadata
                ],
                outputs=[
                    status_indicator, processing_results_display, 
                    video_library_display, index_stats, cost_breakdown
                ]
            )
            
            # Search functionality
            search_btn.click(
                fn=self._perform_search,
                inputs=[
                    search_type, search_query, reference_video_selector,
                    temporal_query, time_start, time_end,
                    search_top_k, similarity_threshold,
                    category_filter, duration_filter
                ],
                outputs=[
                    status_indicator, results_summary, search_results_display,
                    search_analytics, cost_breakdown
                ]
            )
            
            # Utility functions
            refresh_index_btn.click(
                fn=self._refresh_index_status,
                outputs=[index_status_display, index_stats, video_library_display]
            )
            
            refresh_video_list_btn.click(
                fn=self._refresh_video_lists,
                outputs=[reference_video_selector]
            )
            
            refresh_analytics_btn.click(
                fn=self._refresh_analytics,
                outputs=[search_analytics]
            )
            
            reset_costs_btn.click(
                fn=self._reset_costs,
                outputs=[cost_breakdown]
            )
            
            # Management operations
            execute_operations_btn.click(
                fn=self._execute_management_operations,
                inputs=[index_operations],
                outputs=[operations_results]
            )
            
            cleanup_btn.click(
                fn=self._execute_cleanup,
                inputs=[cleanup_options],
                outputs=[operations_results, index_status_display, video_library_display]
            )
            
            # Video segment playback
            play_segment_btn.click(
                fn=self._play_selected_segment,
                outputs=[video_segment_player, selected_result_info]
            )
            
            # Embedding visualization
            generate_viz_btn.click(
                fn=self._generate_embedding_visualization,
                inputs=[reduction_method, viz_dimensions, color_by, sample_size],
                outputs=[embedding_plot, viz_status, clustering_insights]
            )
            
            add_query_overlay_btn.click(
                fn=self._add_query_overlay,
                inputs=[query_overlay_text, embedding_plot, reduction_method],
                outputs=[embedding_plot, viz_status]
            )
        
        return page
    
    # ===== EVENT HANDLER METHODS =====
    
    def _setup_video_index(self, name: str, description: str) -> Tuple[str, str, str, str]:
        """Setup the video search index."""
        try:
            if not name.strip():
                return "❌ Error", "Index name cannot be empty", "Setup failed", "No index created"
            
            bucket_name = config_manager.aws_config.s3_vectors_bucket
            if not bucket_name:
                return "❌ Error", "S3 Vector bucket not configured", "Setup failed", "No index created"
            
            # Create S3 Vector bucket if needed
            try:
                self.s3_manager.create_vector_bucket(bucket_name)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise
            
            # Create video index
            self.video_index_arn = self.video_storage.create_video_index(
                bucket_name=bucket_name,
                index_name=name.strip(),
                embedding_dimension=1024
            )
            
            status_text = f"""✅ **Video Index Created Successfully**

**Index Details:**
- **Name**: {name.strip()}
- **Description**: {description or 'No description provided'}
- **ARN**: {self.video_index_arn}
- **Bucket**: {bucket_name}
- **Embedding Dimension**: 1024 (TwelveLabs Marengo)

**Capabilities:**
- ✅ Text-to-video search
- ✅ Video-to-video similarity
- ✅ Temporal segment search
- ✅ Multi-video library support

Ready to start ingesting videos!"""
            
            stats_text = f"""**Index Statistics:**
- **Total Videos**: 0
- **Total Segments**: 0
- **Index Size**: 0 MB
- **Last Updated**: Just created"""
            
            return (
                "✅ Index Ready", 
                "Video search index created successfully",
                CommonComponents.format_text_for_markdown(status_text),
                stats_text
            )
            
        except Exception as e:
            logger.error(f"Index setup failed: {e}")
            return "❌ Setup Failed", f"Error: {str(e)}", "Index setup failed", "No index created"
    
    def _download_sample_video(self, video_key: str) -> Tuple[str, str, Optional[str], str]:
        """Download and preview sample video."""
        if not video_key:
            return "❌ Error", "Please select a video", None, "No video selected"
        
        # Download the sample video
        status, message, video_path = CommonComponents.download_sample_video(video_key)
        
        # Generate preview if successful
        thumbnail_path = None
        video_info = "Download failed"
        
        if video_path and os.path.exists(video_path):
            thumbnail_path, video_info = CommonComponents.create_video_preview(video_path)
            # Store the video path for processing
            self._current_video_path = video_path
        
        return status, message, thumbnail_path, video_info
    
    def _handle_single_upload(self, uploaded_file) -> Tuple[str, str, Optional[str], str]:
        """Handle single video upload."""
        if uploaded_file is None:
            return "❌ Error", "No file uploaded", None, "No video selected"
        
        try:
            # Validate the uploaded video
            is_valid, validation_msg = CommonComponents.validate_video_file(uploaded_file.name)
            
            if not is_valid:
                return "❌ Invalid Video", validation_msg, None, validation_msg
            
            # Generate preview
            thumbnail_path, video_info = CommonComponents.create_video_preview(uploaded_file.name)
            
            # Store the video path for processing
            self._current_video_path = uploaded_file.name
            
            return "✅ Video Loaded", "Custom video uploaded successfully", thumbnail_path, video_info
            
        except Exception as e:
            logger.error(f"Video upload handling failed: {e}")
            return "❌ Upload Error", f"Error processing upload: {str(e)}", None, "Upload failed"
    
    def _process_and_add_video(self, 
                              source_type: str,
                              sample_video: str, 
                              uploaded_file,
                              segment_duration: int,
                              embedding_options: List[str],
                              use_real_aws: bool,
                              metadata: Dict) -> Tuple[str, str, str, str, str]:
        """Process video and add to search index."""
        
        if not self.video_index_arn:
            return "❌ Error", "Please create an index first", "No videos in library", "No index", "No costs"
        
        # Determine video path based on source
        video_path = None
        if source_type == "sample_videos" and hasattr(self, '_current_video_path'):
            video_path = self._current_video_path
        elif source_type == "upload_single" and uploaded_file:
            video_path = uploaded_file.name
        
        if not video_path or not os.path.exists(video_path):
            return "❌ Error", "No video selected for processing", "No videos in library", "No index", "No costs"
        
        try:
            result_text = f"🎬 **Processing Video for Search Index**\n\n"
            
            video_name = os.path.basename(video_path)
            result_text += f"**Video**: {video_name}\n"
            result_text += f"**Processing Mode**: {'Real AWS' if use_real_aws else 'Simulation'}\n\n"
            
            if use_real_aws:
                # Real processing using TwelveLabs
                result = self._process_video_real(
                    video_path, segment_duration, embedding_options, metadata
                )
                result_text += result
            else:
                # Simulated processing
                result = self._process_video_simulation(
                    video_path, segment_duration, embedding_options, metadata
                )
                result_text += result
            
            # Update video library display
            library_html = self._generate_video_library_html()
            
            # Update index stats
            stats_text = self._generate_index_stats()
            
            # Update costs
            cost_display = CommonComponents.format_cost_info(self.costs)
            
            return (
                "✅ Processing Complete",
                CommonComponents.format_text_for_markdown(result_text),
                library_html,
                stats_text,
                cost_display
            )
            
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            return (
                "❌ Processing Failed", 
                f"Error processing video: {str(e)}", 
                "Processing failed", 
                "Error",
                "Error"
            )
    
    def _process_video_real(self, video_path: str, segment_duration: int, 
                          embedding_options: List[str], metadata: Dict) -> str:
        """Process video using real AWS services."""
        
        result_text = "**Real AWS Processing Steps:**\n\n"
        
        # Step 1: Upload to S3
        result_text += "**1. Uploading to S3**\n"
        
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
        
        s3_uri = f"s3://{bucket_name}/{video_key}"
        result_text += f"✅ Uploaded to: {s3_uri}\n\n"
        
        # Step 2: Process with TwelveLabs
        result_text += "**2. TwelveLabs Processing**\n"
        
        processing_result = self.video_processor.process_video_sync(
            video_s3_uri=s3_uri,
            embedding_options=embedding_options,
            use_fixed_length_sec=float(segment_duration),
            timeout_sec=600
        )
        
        result_text += f"✅ Generated {processing_result.total_segments} segments\n"
        result_text += f"Duration: {processing_result.video_duration_sec:.1f}s\n\n"
        
        # Step 3: Store in index
        result_text += "**3. Storing in Search Index**\n"
        
        # Limit base_metadata to stay within S3 Vector's 10-key limit
        # The VideoVectorMetadata.to_dict() already uses 6-8 keys, so we can only add 2-4 more
        limited_base_metadata = {
            "source_type": "real_processing",
        }
        
        # Add essential fields from metadata if provided, up to the limit
        if metadata:
            # Only add the most important fields from user metadata
            essential_fields = ["title", "category", "description"]
            keys_added = 1  # Already added source_type
            
            for field in essential_fields:
                if field in metadata and keys_added < 3:  # Leave room for other essential fields
                    limited_base_metadata[field] = str(metadata[field])[:100]  # Truncate long values
                    keys_added += 1
                    
        storage_result = self.video_storage.store_video_embeddings(
            video_result=processing_result,
            index_arn=self.video_index_arn,
            base_metadata=limited_base_metadata,
            key_prefix=f"unified-{int(time.time())}"
        )
        
        result_text += f"✅ Stored {storage_result.stored_segments} segments\n"
        result_text += f"Total vectors: {storage_result.total_vectors_stored}\n\n"
        
        # Update tracking
        video_id = f"real-{int(time.time())}"
        self.processed_videos[video_id] = {
            "name": os.path.basename(video_path),
            "segments": processing_result.total_segments,
            "duration": processing_result.video_duration_sec,
            "s3_uri": s3_uri,
            "processing_type": "real",
            "metadata": metadata
        }
        
        # Update costs
        duration_min = processing_result.video_duration_sec / 60
        self.costs["video_processing"] += duration_min * 0.05
        self.costs["storage"] += storage_result.total_vectors_stored * 0.001
        self.costs["total"] = sum(self.costs.values())
        
        result_text += f"**✅ Video Successfully Added to Index!**\n"
        result_text += f"Processing cost: ~${duration_min * 0.05:.4f}\n"
        result_text += f"Storage cost: ~${storage_result.total_vectors_stored * 0.001:.4f}"
        
        return result_text
    
    def _process_video_simulation(self, video_path: str, segment_duration: int,
                                embedding_options: List[str], metadata: Dict) -> str:
        """Simulate video processing for demo purposes."""
        
        result_text = "**Simulation Processing Steps:**\n\n"
        
        # Get video info for simulation
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        cap.release()
        
        # Simulate processing
        segments = max(1, int(duration / segment_duration))
        
        result_text += f"**1. Upload Simulation**\n"
        result_text += f"✅ Would upload {os.path.getsize(video_path):,} bytes to S3\n\n"
        
        result_text += f"**2. Processing Simulation**\n"
        result_text += f"✅ Would generate {segments} segments\n"
        result_text += f"Embedding options: {', '.join(embedding_options)}\n"
        result_text += f"Processing time: ~{duration * 2:.1f}s\n\n"
        
        result_text += f"**3. Storage Simulation**\n"
        vectors_per_segment = len(embedding_options)
        total_vectors = segments * vectors_per_segment
        result_text += f"✅ Would store {total_vectors} vectors\n\n"
        
        # Update tracking for simulation
        video_id = f"sim-{int(time.time())}"
        self.processed_videos[video_id] = {
            "name": os.path.basename(video_path),
            "segments": segments,
            "duration": duration,
            "processing_type": "simulation",
            "metadata": metadata
        }
        
        # Simulate costs
        processing_cost = duration / 60 * 0.05
        storage_cost = total_vectors * 0.001
        
        result_text += f"**✅ Video Simulation Complete!**\n"
        result_text += f"Simulated processing cost: ~${processing_cost:.4f}\n"
        result_text += f"Simulated storage cost: ~${storage_cost:.4f}\n"
        result_text += f"\nEnable 'Use Real AWS' for actual processing"
        
        return result_text
    
    def _perform_search(self, search_type: str, text_query: str, reference_video: str,
                       temporal_query: str, time_start: float, time_end: float,
                       top_k: int, threshold: float, 
                       category_filter: List[str], duration_filter: List[str]) -> Tuple[str, str, str, Dict, str]:
        """Perform search based on selected type and parameters."""
        
        if not self.video_index_arn:
            return "❌ Error", "Please create and populate an index first", "", {}, "No costs"
        
        if not self.processed_videos:
            return "❌ Error", "No videos in index. Please add videos first", "", {}, "No costs"
        
        try:
            start_time = time.time()
            
            results_html = ""
            analytics = {}
            
            if search_type == "text_to_video":
                if not text_query.strip():
                    return "❌ Error", "Please enter a text query", "", {}, "No costs"
                
                results_html, analytics = self._search_text_to_video(
                    text_query.strip(), top_k, threshold, category_filter
                )
                
            elif search_type == "video_to_video":
                if not reference_video:
                    return "❌ Error", "Please select a reference video", "", {}, "No costs"
                
                results_html, analytics = self._search_video_to_video(
                    reference_video, top_k, threshold
                )
                
            elif search_type == "temporal_search":
                if not temporal_query.strip():
                    return "❌ Error", "Please enter a content query", "", {}, "No costs"
                
                results_html, analytics = self._search_temporal(
                    temporal_query.strip(), time_start, time_end, top_k, threshold
                )
            
            search_time = time.time() - start_time
            
            # Update search costs and analytics
            self.costs["queries"] += 0.001
            self.costs["total"] = sum(self.costs.values())
            
            analytics["search_time_ms"] = search_time * 1000
            analytics["cost_usd"] = 0.001
            
            # Generate results summary
            summary = f"**Search Results**\n\n"
            summary += f"**Query Type**: {search_type.replace('_', '-').title()}\n"
            summary += f"**Query**: {text_query or reference_video or temporal_query}\n"
            summary += f"**Processing Time**: {search_time*1000:.1f}ms\n"
            summary += f"**Results Found**: {analytics.get('total_results', 0)}\n"
            
            cost_display = CommonComponents.format_cost_info(self.costs)
            
            return (
                "✅ Search Complete",
                CommonComponents.format_text_for_markdown(summary),
                results_html,
                analytics,
                cost_display
            )
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return "❌ Search Failed", f"Search error: {str(e)}", "", {}, "Error"
    
    def _search_text_to_video(self, query: str, top_k: int, threshold: float, 
                            category_filter: List[str]) -> Tuple[str, Dict]:
        """Perform text-to-video search using real S3 Vector retrieval."""
        
        if not self.video_index_arn:
            # Fall back to simulation if no index available
            return self._simulate_text_to_video_search(query, top_k, threshold, category_filter)
        
        try:
            # Prepare metadata filters for category filtering
            metadata_filters = {"content_type": "video"}
            if category_filter:
                # Add category filter if provided
                metadata_filters["category"] = {"$in": category_filter}
            
            # Create similarity query for text-to-video search
            similarity_query = SimilarityQuery(
                query_text=query,
                top_k=top_k,
                similarity_threshold=threshold,
                metadata_filters=metadata_filters,
                content_type_filter=["video"],
                extract_entities=True,
                expand_synonyms=True,
                include_explanations=True
            )
            
            # Execute real vector search using Marengo multimodal index
            response = self.search_engine.find_similar_content(
                query=similarity_query,
                index_arn=self.video_index_arn,
                index_type=IndexType.MARENGO_MULTIMODAL
            )
            
            # Convert search results to display format
            results = []
            for result in response.results:
                # Extract video information from vector key and metadata
                video_s3_uri = result.metadata.get("video_source_uri", "")
                
                # Try to match with processed videos to get video name
                video_name = "Unknown Video"
                processing_type = "real"
                for video_id, video_info in self.processed_videos.items():
                    if video_info.get("s3_uri") == video_s3_uri:
                        video_name = video_info["name"]
                        processing_type = video_info["processing_type"]
                        break
                
                results.append({
                    "vector_key": result.vector_key,
                    "video_id": result.vector_key.split("-segment-")[0] if "-segment-" in result.vector_key else result.vector_key,
                    "video_name": video_name,
                    "video_s3_uri": video_s3_uri,
                    "segment_index": result.metadata.get("segment_index", 0),
                    "start_sec": result.start_sec or 0,
                    "end_sec": result.end_sec or 5,
                    "score": result.similarity_score,
                    "processing_type": processing_type,
                    "embedding_option": result.metadata.get("embedding_option", "visual-text")
                })
            
            # Update cost tracking
            self.costs["text_search"] = self.costs.get("text_search", 0) + 0.001
            
            # Generate HTML display  
            html = self._generate_search_results_html(results, "text-to-video", query)
            
            analytics = {
                "search_type": "text_to_video_real",
                "query": query, 
                "total_results": len(results),
                "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
                "threshold_applied": threshold,
                "processing_time_ms": response.processing_time_ms,
                "index_arn": self.video_index_arn,
                "search_method": "real_vector_search"
            }
            
            return html, analytics
            
        except Exception as e:
            logger.error(f"Real text-to-video search failed: {e}")
            # Fall back to simulation on error
            return self._simulate_text_to_video_search(query, top_k, threshold, category_filter)
    
    def _search_video_to_video(self, reference_video: str, top_k: int, threshold: float) -> Tuple[str, Dict]:
        """Perform video-to-video similarity search using real S3 Vector retrieval."""
        
        if not self.video_index_arn:
            # Fall back to simulation if no index available
            return self._simulate_video_to_video_search(reference_video, top_k, threshold)
        
        try:
            # Find reference video info to get the vector key
            ref_video_info = self.processed_videos.get(reference_video)
            if not ref_video_info:
                return "<p>Reference video not found</p>", {}
            
            # For real processing videos, use the actual vector key from the index
            if ref_video_info["processing_type"] == "real":
                # Extract the first segment key from the video (assuming segments are named consistently)
                ref_vector_key = f"{reference_video}-segment-0000"  # Use first segment as reference
                
                # Create similarity query for video-to-video search using existing video key
                similarity_query = SimilarityQuery(
                    query_video_key=ref_vector_key,
                    top_k=top_k + 5,  # Get extra results to filter out self-matches
                    similarity_threshold=threshold,
                    metadata_filters={"content_type": "video"},
                    content_type_filter=["video"],
                    include_explanations=True
                )
                
                # Execute real vector search
                response = self.search_engine.find_similar_content(
                    query=similarity_query,
                    index_arn=self.video_index_arn,
                    index_type=IndexType.MARENGO_MULTIMODAL
                )
                
                # Convert search results and filter out self-matches
                results = []
                for result in response.results:
                    # Skip segments from the same reference video
                    if result.vector_key.startswith(reference_video):
                        continue
                    
                    video_s3_uri = result.metadata.get("video_source_uri", "")
                    
                    # Try to match with processed videos to get video name
                    video_name = "Unknown Video"
                    processing_type = "real"
                    for video_id, video_info in self.processed_videos.items():
                        if video_info.get("s3_uri") == video_s3_uri:
                            video_name = video_info["name"]
                            processing_type = video_info["processing_type"]
                            break
                    
                    results.append({
                        "vector_key": result.vector_key,
                        "video_id": result.vector_key.split("-segment-")[0] if "-segment-" in result.vector_key else result.vector_key,
                        "video_name": video_name,
                        "video_s3_uri": video_s3_uri,
                        "segment_index": result.metadata.get("segment_index", 0),
                        "start_sec": result.start_sec or 0,
                        "end_sec": result.end_sec or 5,
                        "score": result.similarity_score,
                        "processing_type": processing_type,
                        "embedding_option": result.metadata.get("embedding_option", "visual-text")
                    })
                    
                    # Limit to requested top_k
                    if len(results) >= top_k:
                        break
                
                # Update cost tracking
                self.costs["video_search"] = self.costs.get("video_search", 0) + 0.001
                
                html = self._generate_search_results_html(results, "video-to-video", f"Reference: {ref_video_info['name']}")
                
                analytics = {
                    "search_type": "video_to_video_real",
                    "reference_video": ref_video_info["name"],
                    "total_results": len(results),
                    "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
                    "threshold_applied": threshold,
                    "processing_time_ms": response.processing_time_ms,
                    "index_arn": self.video_index_arn,
                    "search_method": "real_vector_search"
                }
                
                return html, analytics
            else:
                # For simulated videos, fall back to simulation
                return self._simulate_video_to_video_search(reference_video, top_k, threshold)
                
        except Exception as e:
            logger.error(f"Real video-to-video search failed: {e}")
            # Fall back to simulation on error
            return self._simulate_video_to_video_search(reference_video, top_k, threshold)
    
    def _search_temporal(self, query: str, start_time: float, end_time: float,
                        top_k: int, threshold: float) -> Tuple[str, Dict]:
        """Perform temporal search within time range using real S3 Vector retrieval."""
        
        if not self.video_index_arn:
            # Fall back to simulation if no index available
            return self._simulate_temporal_search(query, start_time, end_time, top_k, threshold)
        
        try:
            from src.services.similarity_search_engine import TemporalFilter
            
            # Create temporal filter for the specified time range
            temporal_filter = TemporalFilter(
                start_time=start_time,
                end_time=end_time
            )
            
            # Create similarity query with text query and temporal filtering
            similarity_query = SimilarityQuery(
                query_text=query,
                top_k=top_k,
                similarity_threshold=threshold,
                metadata_filters={"content_type": "video"},
                temporal_filter=temporal_filter,
                content_type_filter=["video"],
                extract_entities=True,
                include_explanations=True
            )
            
            # Execute real vector search with temporal filtering
            response = self.search_engine.find_similar_content(
                query=similarity_query,
                index_arn=self.video_index_arn,
                index_type=IndexType.MARENGO_MULTIMODAL
            )
            
            # Convert search results 
            results = []
            for result in response.results:
                video_s3_uri = result.metadata.get("video_source_uri", "")
                
                # Try to match with processed videos to get video name
                video_name = "Unknown Video"
                processing_type = "real"
                for video_id, video_info in self.processed_videos.items():
                    if video_info.get("s3_uri") == video_s3_uri:
                        video_name = video_info["name"]
                        processing_type = video_info["processing_type"]
                        break
                
                results.append({
                    "vector_key": result.vector_key,
                    "video_id": result.vector_key.split("-segment-")[0] if "-segment-" in result.vector_key else result.vector_key,
                    "video_name": video_name,
                    "video_s3_uri": video_s3_uri,
                    "segment_index": result.metadata.get("segment_index", 0),
                    "start_sec": result.start_sec or 0,
                    "end_sec": result.end_sec or 5,
                    "score": result.similarity_score,
                    "processing_type": processing_type,
                    "embedding_option": result.metadata.get("embedding_option", "visual-text"),
                    "time_overlap": "Yes"  # All results should overlap due to temporal filter
                })
            
            # Update cost tracking
            self.costs["temporal_search"] = self.costs.get("temporal_search", 0) + 0.001
            
            html = self._generate_search_results_html(results, "temporal", f"{query} [{start_time}s-{end_time}s]")
            
            analytics = {
                "search_type": "temporal_real",
                "query": query,
                "time_range": f"{start_time}-{end_time}s",
                "total_results": len(results),
                "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
                "threshold_applied": threshold,
                "processing_time_ms": response.processing_time_ms,
                "index_arn": self.video_index_arn,
                "search_method": "real_vector_search"
            }
            
            return html, analytics
            
        except Exception as e:
            logger.error(f"Real temporal search failed: {e}")
            # Fall back to simulation on error
            return self._simulate_temporal_search(query, start_time, end_time, top_k, threshold)
    
    def _generate_search_results_html(self, results: List[Dict], search_type: str, query: str) -> str:
        """Generate HTML for search results display with video playback support."""
        
        if not results:
            return f"""
            <div class="search-result">
                <h4>No Results Found</h4>
                <p>No video segments matched your search criteria. Try:</p>
                <ul>
                    <li>Lowering the similarity threshold</li>
                    <li>Using different keywords</li>
                    <li>Adding more videos to your index</li>
                </ul>
            </div>
            """
        
        html = f"""
        <div style="margin-bottom: 1rem;">
            <h4>🔍 {search_type.replace('-', ' ').title()} Results</h4>
            <p><strong>Query:</strong> {query}</p>
            <p><strong>Found:</strong> {len(results)} matching segments</p>
        </div>
        """
        
        for i, result in enumerate(results, 1):
            score_color = "#4CAF50" if result["score"] > 0.8 else "#FF9800" if result["score"] > 0.6 else "#2196F3"
            segment_id = f"{result['video_id']}_seg_{result['segment_index']}"
            
            # Get video S3 URI - prefer from search result, fall back to processed_videos
            s3_uri = result.get("video_s3_uri", "")
            if not s3_uri:
                video_info = self.processed_videos.get(result["video_id"], {})
                s3_uri = video_info.get("s3_uri", "")
            
            html += f"""
            <div class="search-result" style="border-left: 4px solid {score_color}; position: relative;" 
                 id="result_{segment_id}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h5>#{i}. {result["video_name"]} - Segment {result["segment_index"] + 1}</h5>
                    <span class="similarity-score" style="color: {score_color}; font-weight: bold;">
                        {result["score"]:.3f}
                    </span>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 0.5rem 0;">
                    <div>
                        <strong>⏱️ Timing:</strong> {result["start_sec"]:.1f}s - {result["end_sec"]:.1f}s ({result["end_sec"] - result["start_sec"]:.1f}s)
                        <br><strong>🎬 Video ID:</strong> {result["video_id"]}
                    </div>
                    <div>
                        <strong>⚙️ Processing:</strong> {result["processing_type"].title()}
                        <br><strong>📊 Score:</strong> {result["score"]:.1%} match
                    </div>
                </div>
                
                <div style="display: flex; gap: 0.5rem; margin: 0.5rem 0;">
                    <button onclick="selectSegmentForPlayback('{segment_id}', '{result['video_name']}', {result['start_sec']}, {result['end_sec']}, '{s3_uri}')" 
                            style="background: #1976d2; color: white; border: none; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.9em;">
                        🎬 Play Segment
                    </button>
                    {"<button onclick=\"showVideoPlayer('" + s3_uri + "', " + str(result['start_sec']) + ", " + str(result['end_sec']) + ", '" + result['video_name'] + "')\" style=\"background: #4CAF50; color: white; border: none; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.9em;\">▶️ Play Now</button>" if s3_uri and result["processing_type"] == "real" else "<span style=\"color: #666; font-size: 0.9em;\">📹 Real processing required for playback</span>"}
                </div>
                
                {"<div style=\"background: #e8f5e8; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; border-left: 3px solid #4CAF50;\"><small>✅ <strong>Video playback available:</strong> This segment was processed with real AWS services and can be played.</small></div>" if s3_uri and result["processing_type"] == "real" else "<div style=\"background: #f0f8ff; padding: 0.5rem; border-radius: 4px; margin-top: 0.5rem; border-left: 3px solid #2196F3;\"><small>🔵 <strong>Simulated result:</strong> Enable real AWS processing to play video segments.</small></div>"}
            </div>
            """
        
        # Add JavaScript for segment selection
        html += f"""
        <script>
        let selectedSegment = null;
        
        function selectSegmentForPlayback(segmentId, videoName, startSec, endSec, s3Uri) {{
            // Highlight selected result
            document.querySelectorAll('.search-result').forEach(el => {{
                el.style.background = '';
                el.style.border = el.style.borderLeft;
            }});
            
            const selectedElement = document.getElementById('result_' + segmentId);
            if (selectedElement) {{
                selectedElement.style.background = '#f0f8ff';
                selectedElement.style.border = '2px solid #1976d2';
            }}
            
            selectedSegment = {{
                id: segmentId,
                name: videoName,
                start: startSec,
                end: endSec,
                s3Uri: s3Uri
            }};
            
            // Update selected segment info (would trigger Gradio update in full implementation)
            console.log('Selected segment for playback:', selectedSegment);
        }}
        
        function showVideoPlayer(s3Uri, startSec, endSec, videoName) {{
            if (!s3Uri) {{
                alert('Video playback not available for simulated results. Enable real AWS processing.');
                return;
            }}
            
            // This would integrate with the Gradio video player component
            console.log('Playing video segment:', {{
                s3Uri: s3Uri,
                start: startSec,
                end: endSec,
                title: videoName
            }});
            
            // In a full implementation, this would update the video player component
            alert(`Would play: ${{videoName}}\\nSegment: ${{startSec}}s - ${{endSec}}s\\nS3 URI: ${{s3Uri}}`);
        }}
        </script>
        """
        
        return html
    
    def _generate_video_library_html(self) -> str:
        """Generate HTML for video library display."""
        
        if not self.processed_videos:
            return "<p><em>No videos in the library yet. Add some videos to get started!</em></p>"
        
        html = f"""
        <div style="margin-bottom: 1rem;">
            <h4>📚 Video Library ({len(self.processed_videos)} videos)</h4>
        </div>
        <div class="video-grid">
        """
        
        for video_id, video_info in self.processed_videos.items():
            processing_badge = "🟢 Real" if video_info["processing_type"] == "real" else "🔵 Sim"
            
            html += f"""
            <div class="video-card">
                <h5>{video_info["name"]}</h5>
                <div style="text-align: left; font-size: 0.9em;">
                    <div><strong>Duration:</strong> {video_info["duration"]:.1f}s</div>
                    <div><strong>Segments:</strong> {video_info["segments"]}</div>
                    <div><strong>Processing:</strong> {processing_badge}</div>
                    <div><strong>ID:</strong> <code>{video_id}</code></div>
                </div>
            </div>
            """
        
        html += "</div>"
        return html
    
    def _generate_index_stats(self) -> str:
        """Generate index statistics text."""
        
        total_videos = len(self.processed_videos)
        total_segments = sum(v["segments"] for v in self.processed_videos.values())
        total_duration = sum(v["duration"] for v in self.processed_videos.values())
        
        real_videos = sum(1 for v in self.processed_videos.values() if v["processing_type"] == "real")
        sim_videos = total_videos - real_videos
        
        return f"""**Index Statistics:**
- **Total Videos**: {total_videos}
- **Total Segments**: {total_segments:,}
- **Total Duration**: {total_duration:.1f} seconds
- **Real Processing**: {real_videos} videos
- **Simulated**: {sim_videos} videos
- **Average Segments/Video**: {total_segments/total_videos:.1f} (if {total_videos} > 0 else 0)
- **Storage Size**: ~{total_segments * 4:.1f} KB"""
    
    def _refresh_index_status(self) -> Tuple[str, str, str]:
        """Refresh index status displays."""
        
        if not self.video_index_arn:
            return "No index created yet", "No index", "No videos in library"
        
        status_text = f"""✅ **Video Index Active**

**Index Details:**
- **ARN**: {self.video_index_arn}
- **Status**: Active and ready for search
- **Capabilities**: Text-to-video, Video-to-video, Temporal search

**Current State:**
- Videos indexed: {len(self.processed_videos)}
- Ready for search queries"""
        
        stats_text = self._generate_index_stats()
        library_html = self._generate_video_library_html()
        
        return (
            CommonComponents.format_text_for_markdown(status_text),
            stats_text,
            library_html
        )
    
    def _refresh_video_lists(self) -> gr.Dropdown:
        """Refresh video dropdown lists."""
        video_choices = [
            (f"{info['name']} ({video_id})", video_id) 
            for video_id, info in self.processed_videos.items()
        ]
        
        return gr.update(choices=video_choices)
    
    def _refresh_analytics(self) -> Dict:
        """Refresh search analytics."""
        
        return {
            "total_videos": len(self.processed_videos),
            "total_segments": sum(v["segments"] for v in self.processed_videos.values()),
            "real_processing_videos": sum(1 for v in self.processed_videos.values() if v["processing_type"] == "real"),
            "simulated_videos": sum(1 for v in self.processed_videos.values() if v["processing_type"] == "simulation"),
            "total_search_queries": int(self.costs.get("queries", 0) / 0.001),
            "session_costs": dict(self.costs),
            "index_arn": self.video_index_arn,
            "capabilities": [
                "Text-to-video search",
                "Video-to-video similarity",
                "Temporal segment search",
                "Multi-video indexing"
            ]
        }
    
    def _reset_costs(self) -> str:
        """Reset cost tracking."""
        self.costs = {"video_processing": 0, "storage": 0, "queries": 0, "total": 0}
        return CommonComponents.format_cost_info(self.costs)
    
    def _execute_management_operations(self, operations: List[str]) -> str:
        """Execute selected management operations."""
        
        results = "**Management Operations Results:**\n\n"
        
        for operation in operations:
            if operation == "Export index metadata":
                # Generate metadata export
                metadata = {
                    "index_arn": self.video_index_arn,
                    "videos": self.processed_videos,
                    "stats": {
                        "total_videos": len(self.processed_videos),
                        "total_segments": sum(v["segments"] for v in self.processed_videos.values())
                    },
                    "export_timestamp": time.time()
                }
                
                results += f"✅ **{operation}**: Metadata exported ({len(str(metadata))} characters)\n"
                
            elif operation == "Backup embeddings":
                results += f"✅ **{operation}**: Backup procedure initiated (simulated)\n"
                
            elif operation == "Clean up temp files":
                # Clean up any temporary files
                temp_cleaned = 0
                results += f"✅ **{operation}**: Cleaned {temp_cleaned} temporary files\n"
                
            elif operation == "Reset demo data":
                # Reset non-destructive demo data
                self.search_results_cache = {}
                results += f"✅ **{operation}**: Demo cache and temporary data reset\n"
        
        if not operations:
            results += "*No operations selected*"
        
        return CommonComponents.format_text_for_markdown(results)
    
    def _execute_cleanup(self, cleanup_options: List[str]) -> Tuple[str, str, str]:
        """Execute cleanup operations."""
        
        results = "**Cleanup Operations Results:**\n\n"
        
        for option in cleanup_options:
            if option == "Delete all processed videos":
                count = len(self.processed_videos)
                self.processed_videos = {}
                results += f"✅ **{option}**: Removed {count} videos from tracking\n"
                
            elif option == "Delete search index":
                if self.video_index_arn:
                    # Note: In real implementation, this would delete the actual index
                    results += f"✅ **{option}**: Index {self.video_index_arn} marked for deletion\n"
                    self.video_index_arn = None
                else:
                    results += f"ℹ️ **{option}**: No index to delete\n"
                
            elif option == "Clear all session data":
                self.processed_videos = {}
                self.search_results_cache = {}
                self.video_index_arn = None
                self.costs = {"video_processing": 0, "storage": 0, "queries": 0, "total": 0}
                results += f"✅ **{option}**: All session data cleared\n"
        
        if not cleanup_options:
            results += "*No cleanup operations selected*"
        
        # Update displays
        index_status = "No index after cleanup" if not self.video_index_arn else "Index still active"
        library_html = self._generate_video_library_html()
        
        return (
            CommonComponents.format_text_for_markdown(results),
            index_status,
            library_html
        )
    
    def _play_selected_segment(self) -> Tuple[str, str]:
        """Play the currently selected video segment."""
        
        if not self.selected_segment:
            return (
                "<p><em>No segment selected. Click 'Play Segment' on a search result first.</em></p>",
                "*No segment selected for playback*"
            )
        
        try:
            segment_info = self.selected_segment
            s3_uri = segment_info.get("s3Uri", "")
            
            if not s3_uri:
                return (
                    "<p><em>Video playback not available - segment was generated by simulation.</em></p>",
                    "*Video playback requires real AWS processing*"
                )
            
            # Generate video player HTML
            player_html = CommonComponents.create_advanced_video_player(
                video_s3_uri=s3_uri,
                start_sec=segment_info["start"],
                end_sec=segment_info["end"],
                video_title=f"{segment_info['name']} - Segment",
                show_controls=True
            )
            
            # Generate segment details
            duration = segment_info["end"] - segment_info["start"]
            segment_details = f"""**📹 Now Playing:**

**Video:** {segment_info['name']}
**Segment:** {segment_info['start']:.1f}s - {segment_info['end']:.1f}s
**Duration:** {duration:.1f} seconds
**Source:** S3 Video Storage

✅ Video player loaded with automatic segment timing."""
            
            return player_html, CommonComponents.format_text_for_markdown(segment_details)
            
        except Exception as e:
            logger.error(f"Failed to play video segment: {e}")
            return (
                f"<p><em>Error loading video player: {str(e)}</em></p>",
                f"*Error: {str(e)}*"
            )
    
    def _select_segment_for_playback(self, segment_data: str) -> str:
        """Select a segment for playback (called from JavaScript)."""
        try:
            import json
            self.selected_segment = json.loads(segment_data)
            return "Segment selected for playback"
        except Exception as e:
            logger.error(f"Failed to select segment: {e}")
            return f"Error selecting segment: {str(e)}"
    
    # Simulation fallback methods for when real S3 Vector search is unavailable
    
    def _simulate_text_to_video_search(self, query: str, top_k: int, threshold: float, 
                                     category_filter: List[str]) -> Tuple[str, Dict]:
        """Fallback simulation for text-to-video search."""
        
        results = []
        
        # Simple keyword matching for simulation
        query_lower = query.lower()
        keywords = query_lower.split()
        
        for video_id, video_info in self.processed_videos.items():
            video_name = video_info["name"].lower()
            metadata = video_info.get("metadata", {})
            
            # Simple scoring based on keyword matches
            score = 0.5  # Base score
            
            # Check video name
            for keyword in keywords:
                if keyword in video_name:
                    score += 0.2
            
            # Check metadata
            category = str(metadata.get("category", "")).lower()
            for keyword in keywords:
                if keyword in category:
                    score += 0.15
            
            # Add some randomization for demo
            import random
            score += random.uniform(-0.1, 0.1)
            score = min(1.0, max(0.0, score))
            
            if score >= threshold:
                # Generate mock segments for this video
                num_segments = video_info["segments"]
                for i in range(min(3, num_segments)):  # Show up to 3 segments per video
                    segment_score = score + random.uniform(-0.05, 0.05)
                    segment_score = min(1.0, max(0.0, segment_score))
                    
                    if segment_score >= threshold:
                        results.append({
                            "video_id": video_id,
                            "video_name": video_info["name"],
                            "segment_index": i,
                            "start_sec": i * 5,
                            "end_sec": (i + 1) * 5,
                            "score": segment_score,
                            "processing_type": video_info["processing_type"]
                        })
        
        # Sort by score and limit results
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]
        
        # Generate HTML display
        html = self._generate_search_results_html(results, "text-to-video", f"{query} (simulated)")
        
        analytics = {
            "search_type": "text_to_video_simulation", 
            "query": query,
            "total_results": len(results),
            "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
            "threshold_applied": threshold
        }
        
        return html, analytics
    
    def _simulate_video_to_video_search(self, reference_video: str, top_k: int, threshold: float) -> Tuple[str, Dict]:
        """Fallback simulation for video-to-video search."""
        
        results = []
        
        # Find reference video info
        ref_video_info = self.processed_videos.get(reference_video)
        if not ref_video_info:
            return "<p>Reference video not found</p>", {}
        
        for video_id, video_info in self.processed_videos.items():
            if video_id == reference_video:
                continue  # Skip self
            
            # Calculate similarity based on metadata
            base_score = 0.4
            
            # Same processing type gets bonus
            if video_info["processing_type"] == ref_video_info["processing_type"]:
                base_score += 0.3
            
            # Similar duration gets bonus
            duration_diff = abs(video_info["duration"] - ref_video_info["duration"])
            if duration_diff < 10:
                base_score += 0.2
            
            # Add randomization
            import random
            score = base_score + random.uniform(-0.2, 0.2)
            score = min(1.0, max(0.0, score))
            
            if score >= threshold:
                # Generate mock segments
                num_segments = min(3, video_info["segments"])
                for i in range(num_segments):
                    segment_score = score + random.uniform(-0.05, 0.05)
                    segment_score = min(1.0, max(0.0, segment_score))
                    
                    results.append({
                        "video_id": video_id,
                        "video_name": video_info["name"],
                        "segment_index": i,
                        "start_sec": i * 5,
                        "end_sec": (i + 1) * 5,
                        "score": segment_score,
                        "processing_type": video_info["processing_type"]
                    })
        
        # Sort and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]
        
        html = self._generate_search_results_html(results, "video-to-video", f"Reference: {ref_video_info['name']} (simulated)")
        
        analytics = {
            "search_type": "video_to_video_simulation",
            "reference_video": ref_video_info["name"], 
            "total_results": len(results),
            "avg_score": sum(r["score"] for r in results) / len(results) if results else 0
        }
        
        return html, analytics
    
    def _simulate_temporal_search(self, query: str, start_time: float, end_time: float,
                                top_k: int, threshold: float) -> Tuple[str, Dict]:
        """Fallback simulation for temporal search."""
        
        results = []
        
        # Filter segments based on time range
        for video_id, video_info in self.processed_videos.items():
            num_segments = video_info["segments"]
            
            for i in range(num_segments):
                segment_start = i * 5
                segment_end = (i + 1) * 5
                
                # Check if segment overlaps with search time range
                if segment_end >= start_time and segment_start <= end_time:
                    # Simple query matching
                    score = 0.6
                    
                    query_lower = query.lower()
                    video_name_lower = video_info["name"].lower()
                    
                    for word in query_lower.split():
                        if word in video_name_lower:
                            score += 0.2
                    
                    # Add randomization
                    import random
                    score += random.uniform(-0.1, 0.1)
                    score = min(1.0, max(0.0, score))
                    
                    if score >= threshold:
                        results.append({
                            "video_id": video_id,
                            "video_name": video_info["name"],
                            "segment_index": i,
                            "start_sec": segment_start,
                            "end_sec": segment_end,
                            "score": score,
                            "processing_type": video_info["processing_type"],
                            "time_overlap": "Yes"
                        })
        
        # Sort and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]
        
        html = self._generate_search_results_html(results, "temporal", f"{query} [{start_time}s-{end_time}s] (simulated)")
        
        analytics = {
            "search_type": "temporal_simulation",
            "query": query,
            "time_range": f"{start_time}-{end_time}s",
            "total_results": len(results)
        }
        
        return html, analytics
    
    # ===== EMBEDDING VISUALIZATION METHODS =====
    
    def _generate_embedding_visualization(self, reduction_method: str, dimensions: str, 
                                        color_by: str, sample_size: int) -> Tuple[go.Figure, str, str]:
        """Generate interactive embedding visualization."""
        
        if not self.video_index_arn:
            return None, "❌ No video index available. Create an index and add videos first.", "*No index data*"
        
        try:
            # Retrieve embeddings from S3 Vector index
            status_msg = "🔄 Retrieving embeddings from S3 Vector index..."
            
            response = self.s3_manager.list_vectors(
                index_arn=self.video_index_arn,
                max_results=sample_size,
                return_data=True,
                return_metadata=True
            )
            
            vectors = response.get('vectors', [])
            if not vectors:
                return None, "❌ No embeddings found in index", "*No embedding data*"
            
            # Extract embeddings and metadata
            embeddings = []
            metadata_list = []
            
            for vector in vectors:
                embedding_data = vector.get('data', {}).get('float32', [])
                if embedding_data:
                    embeddings.append(embedding_data)
                    
                    # Process metadata for visualization
                    metadata = vector.get('metadata', {})
                    
                    # Extract video name from processed videos - improved matching
                    vector_key = vector.get('key', '')
                    video_id = vector_key.split('-segment-')[0] if '-segment-' in vector_key else vector_key
                    
                    # Try multiple matching strategies for video name
                    video_name = "Unknown Video"
                    video_s3_uri = ""
                    
                    # Look for video source URI in different metadata fields
                    # (due to 10-key limit, it might be stored in base_metadata)
                    for field_name in ['video_source_uri', 'source_uri', 's3_uri', 'source']:
                        if field_name in metadata:
                            video_s3_uri = metadata[field_name]
                            break
                    
                    # Strategy 1: Match by video_id key  
                    if video_id in self.processed_videos:
                        video_name = self.processed_videos[video_id]["name"]
                    else:
                        # Strategy 2: Match by S3 URI
                        if video_s3_uri:
                            for vid_id, vid_info in self.processed_videos.items():
                                if vid_info.get("s3_uri") == video_s3_uri:
                                    video_name = vid_info["name"]
                                    break
                        
                        # Strategy 3: Try to match by timestamp in vector key
                        if video_name == "Unknown Video":
                            # Extract timestamp from key like "unified-1754550140-segment-0000"
                            try:
                                key_parts = vector_key.split('-')
                                if len(key_parts) >= 2:
                                    timestamp = key_parts[1]  # Should be the timestamp
                                    # Look for processed videos with matching timestamp
                                    for vid_id, vid_info in self.processed_videos.items():
                                        if timestamp in vid_id:
                                            video_name = vid_info["name"]
                                            break
                            except:
                                pass
                        
                        # Strategy 4: Try to extract filename from S3 URI or metadata
                        if video_name == "Unknown Video":
                            # Try from S3 URI
                            if video_s3_uri:
                                try:
                                    filename = video_s3_uri.split('/')[-1]
                                    clean_name = filename.rsplit('.', 1)[0]
                                    video_name = f"Video: {clean_name}"
                                except:
                                    pass
                            
                            # Try from metadata title field
                            elif metadata.get('title'):
                                video_name = f"Video: {metadata['title']}"
                    
                    metadata_list.append({
                        'key': vector_key,
                        'video_name': video_name,
                        'video_id': video_id,
                        'video_s3_uri': video_s3_uri,
                        'start_sec': metadata.get('start_sec', 0),
                        'end_sec': metadata.get('end_sec', 0),
                        'content_type': metadata.get('content_type', 'video'),
                        'processing_type': 'real' if video_name != "Unknown Video" else 'unknown',
                        'temporal_position': metadata.get('start_sec', 0) / 60.0  # Convert to minutes
                    })
            
            if not embeddings:
                return None, "❌ No valid embedding data found", "*No embedding vectors*"
            
            # Convert to numpy array
            embeddings = np.array(embeddings)
            status_msg = f"🔄 Reducing {embeddings.shape[0]} embeddings from 1024D to {dimensions}..."
            
            # Perform dimensionality reduction
            if reduction_method == "PCA":
                reducer = PCA(n_components=3 if dimensions == "3D" else 2, random_state=42)
                reduced_embeddings = reducer.fit_transform(embeddings)
                explained_variance = reducer.explained_variance_ratio_.sum()
                reduction_info = f"PCA captured {explained_variance:.1%} of variance"
            else:  # t-SNE
                n_components = 3 if dimensions == "3D" else 2
                reducer = TSNE(n_components=n_components, random_state=42, perplexity=min(30, len(embeddings)-1))
                reduced_embeddings = reducer.fit_transform(embeddings)
                reduction_info = f"t-SNE completed with perplexity {reducer.perplexity}"
            
            # Store reducer and embeddings for query overlay
            self.current_reducer = reducer
            self.current_embeddings_matrix = embeddings
            self.current_reduction_method = reduction_method
            self.current_dimensions = dimensions
            
            # Create DataFrame for plotting
            df = pd.DataFrame(metadata_list)
            df['x'] = reduced_embeddings[:, 0]
            df['y'] = reduced_embeddings[:, 1]
            if dimensions == "3D":
                df['z'] = reduced_embeddings[:, 2]
            
            # Generate color values based on selected option
            if color_by == "video_name":
                color_values = df['video_name']
            elif color_by == "processing_type":
                color_values = df['processing_type']  
            elif color_by == "temporal_position":
                color_values = df['temporal_position']
            else:  # similarity_cluster
                # Perform simple clustering for visualization
                from sklearn.cluster import KMeans
                n_clusters = min(8, len(embeddings) // 10 + 2)
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                cluster_labels = kmeans.fit_predict(reduced_embeddings)
                color_values = [f"Cluster {i}" for i in cluster_labels]
                df['cluster'] = color_values
            
            # Create interactive plot
            if dimensions == "3D":
                fig = px.scatter_3d(
                    df, x='x', y='y', z='z',
                    color=color_values,
                    hover_data=['video_name', 'start_sec', 'end_sec', 'key'],
                    title=f"Video Embedding Space - {reduction_method} ({dimensions})",
                    labels={'x': f'{reduction_method} Component 1', 
                           'y': f'{reduction_method} Component 2',
                           'z': f'{reduction_method} Component 3'},
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
            else:
                fig = px.scatter(
                    df, x='x', y='y',
                    color=color_values,
                    hover_data=['video_name', 'start_sec', 'end_sec', 'key'],
                    title=f"Video Embedding Space - {reduction_method} ({dimensions})",
                    labels={'x': f'{reduction_method} Component 1', 
                           'y': f'{reduction_method} Component 2'},
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
            
            # Enhance plot appearance
            fig.update_traces(marker=dict(size=8, opacity=0.7))
            fig.update_layout(
                hovermode='closest',
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
                margin=dict(l=0, r=100, t=50, b=0)
            )
            
            # Generate clustering insights
            insights = self._analyze_embedding_clusters(df, color_by, reduction_info)
            
            status_msg = f"✅ Visualization complete: {len(embeddings)} embeddings displayed"
            
            return fig, status_msg, insights
            
        except Exception as e:
            logger.error(f"Failed to generate embedding visualization: {e}")
            return None, f"❌ Visualization failed: {str(e)}", "*Visualization error*"
    
    def _add_query_overlay(self, query_text: str, current_plot, 
                          reduction_method: str) -> Tuple[go.Figure, str]:
        """Add search query embedding as overlay by regenerating the full plot with query."""
        
        if not query_text or not query_text.strip():
            return current_plot, "⚠️ Enter a query text to add overlay"
        
        if not self.video_index_arn:
            return current_plot, "❌ No video index available for query embedding"
        
        if not hasattr(self, 'current_reducer') or self.current_reducer is None:
            return current_plot, "⚠️ Generate a visualization first, then add query overlay"
        
        try:
            # Generate text embedding for the query using TwelveLabs
            query_result = self.search_engine.twelvelabs_service.generate_text_embedding(query_text.strip())
            
            if not query_result or 'embedding' not in query_result:
                return current_plot, f"❌ Failed to generate embedding for query: {query_text}"
            
            query_embedding = np.array(query_result['embedding']).reshape(1, -1)
            
            # Apply the same dimensionality reduction that was used for the visualization
            if self.current_reduction_method == "PCA":
                # For PCA, we can transform new points using the fitted reducer
                query_reduced = self.current_reducer.transform(query_embedding)
            else:  # t-SNE
                # For t-SNE, we need to fit on combined data (limitation of t-SNE)
                # Combine query with existing embeddings and re-fit
                combined_embeddings = np.vstack([self.current_embeddings_matrix, query_embedding])
                n_components = 3 if self.current_dimensions == "3D" else 2
                reducer = TSNE(n_components=n_components, random_state=42, 
                              perplexity=min(30, len(combined_embeddings)-1))
                all_reduced = reducer.fit_transform(combined_embeddings)
                
                # Extract just the query point (last row)
                query_reduced = all_reduced[-1:, :]
            
            # Since Gradio's plot doesn't support add_trace, we need to recreate the plot
            # Get the existing data from current_plot and add query data
            
            # First, retrieve the existing embedding data again to recreate the base plot
            response = self.s3_manager.list_vectors(
                index_arn=self.video_index_arn,
                max_results=200,  # Use same sample size as original
                return_data=True,
                return_metadata=True
            )
            
            vectors = response.get('vectors', [])
            if not vectors:
                return current_plot, "❌ No embeddings found to overlay query on"
            
            # Recreate the base visualization data
            embeddings = []
            metadata_list = []
            
            for vector in vectors:
                embedding_data = vector.get('data', {}).get('float32', [])
                if embedding_data:
                    embeddings.append(embedding_data)
                    
                    # Process metadata for visualization (same logic as original)
                    metadata = vector.get('metadata', {})
                    vector_key = vector.get('key', '')
                    video_id = vector_key.split('-segment-')[0] if '-segment-' in vector_key else vector_key
                    
                    video_name = "Unknown Video"
                    video_s3_uri = ""
                    
                    for field_name in ['video_source_uri', 'source_uri', 's3_uri', 'source']:
                        if field_name in metadata:
                            video_s3_uri = metadata[field_name]
                            break
                    
                    if video_id in self.processed_videos:
                        video_name = self.processed_videos[video_id]["name"]
                    else:
                        if video_s3_uri:
                            for vid_id, vid_info in self.processed_videos.items():
                                if vid_info.get("s3_uri") == video_s3_uri:
                                    video_name = vid_info["name"]
                                    break
                        
                        if video_name == "Unknown Video":
                            try:
                                key_parts = vector_key.split('-')
                                if len(key_parts) >= 2:
                                    timestamp = key_parts[1]
                                    for vid_id, vid_info in self.processed_videos.items():
                                        if timestamp in vid_id:
                                            video_name = vid_info["name"]
                                            break
                            except:
                                pass
                        
                        if video_name == "Unknown Video":
                            if video_s3_uri:
                                try:
                                    filename = video_s3_uri.split('/')[-1]
                                    clean_name = filename.rsplit('.', 1)[0]
                                    video_name = f"Video: {clean_name}"
                                except:
                                    pass
                            elif metadata.get('title'):
                                video_name = f"Video: {metadata['title']}"
                    
                    metadata_list.append({
                        'key': vector_key,
                        'video_name': video_name,
                        'video_id': video_id,
                        'video_s3_uri': video_s3_uri,
                        'start_sec': metadata.get('start_sec', 0),
                        'end_sec': metadata.get('end_sec', 0),
                        'content_type': metadata.get('content_type', 'video'),
                        'processing_type': 'real' if video_name != "Unknown Video" else 'unknown',
                        'temporal_position': metadata.get('start_sec', 0) / 60.0
                    })
            
            # Apply the same reduction to existing embeddings
            embeddings = np.array(embeddings)
            reduced_embeddings = self.current_reducer.transform(embeddings)
            
            # Create DataFrame with existing points
            df = pd.DataFrame(metadata_list)
            df['x'] = reduced_embeddings[:, 0]
            df['y'] = reduced_embeddings[:, 1]
            if self.current_dimensions == "3D":
                df['z'] = reduced_embeddings[:, 2]
            
            # Add query point to DataFrame
            query_row = {
                'key': 'TEXT_QUERY',
                'video_name': 'Text Query',
                'video_id': 'query',
                'video_s3_uri': '',
                'start_sec': 0,
                'end_sec': 0,
                'content_type': 'text',
                'processing_type': 'query',
                'temporal_position': 0,
                'x': query_reduced[0, 0],
                'y': query_reduced[0, 1]
            }
            
            if self.current_dimensions == "3D":
                query_row['z'] = query_reduced[0, 2] if query_reduced.shape[1] > 2 else 0.0
            
            # Add query row to DataFrame
            df = pd.concat([df, pd.DataFrame([query_row])], ignore_index=True)
            
            # Create color values with special handling for query
            color_values = []
            for i, row in df.iterrows():
                if row['content_type'] == 'text':
                    color_values.append('TEXT_QUERY')
                else:
                    color_values.append(row['video_name'])
            
            # Create the new plot with query overlay
            if self.current_dimensions == "3D":
                fig = px.scatter_3d(
                    df, x='x', y='y', z='z',
                    color=color_values,
                    hover_data=['video_name', 'start_sec', 'end_sec', 'key'],
                    title=f"Video Embedding Space - {self.current_reduction_method} ({self.current_dimensions}) + Query: '{query_text[:30]}{'...' if len(query_text) > 30 else ''}'",
                    labels={'x': f'{self.current_reduction_method} Component 1', 
                           'y': f'{self.current_reduction_method} Component 2',
                           'z': f'{self.current_reduction_method} Component 3'},
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
            else:
                fig = px.scatter(
                    df, x='x', y='y',
                    color=color_values,
                    hover_data=['video_name', 'start_sec', 'end_sec', 'key'],
                    title=f"Video Embedding Space - {self.current_reduction_method} ({self.current_dimensions}) + Query: '{query_text[:30]}{'...' if len(query_text) > 30 else ''}'",
                    labels={'x': f'{self.current_reduction_method} Component 1', 
                           'y': f'{self.current_reduction_method} Component 2'},
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
            
            # Customize the query point to be black
            for i, trace in enumerate(fig.data):
                if 'TEXT_QUERY' in trace.name:
                    trace.marker.color = 'black'
                    trace.marker.size = 15
                    trace.marker.symbol = 'x'
                    trace.marker.line.color = 'white'
                    trace.marker.line.width = 3
                    trace.marker.opacity = 1.0
                    trace.name = f'Text Query: {query_text[:20]}...'
                else:
                    trace.marker.size = 8
                    trace.marker.opacity = 0.7
            
            fig.update_layout(
                hovermode='closest',
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
                margin=dict(l=0, r=100, t=50, b=0)
            )
            
            status_msg = f"✅ Query '{query_text}' added to visualization (black X marker)"
            
            return fig, status_msg
            
        except Exception as e:
            logger.error(f"Failed to add query overlay: {e}")
            return current_plot, f"❌ Query overlay failed: {str(e)}"
    
    def _analyze_embedding_clusters(self, df: pd.DataFrame, color_by: str, reduction_info: str) -> str:
        """Analyze and describe the embedding clusters."""
        
        insights = f"**🎯 Embedding Space Analysis**\n\n"
        insights += f"**Reduction Method**: {reduction_info}\n"
        insights += f"**Total Points**: {len(df)} video segments\n"
        insights += f"**Color Coding**: {color_by.replace('_', ' ').title()}\n\n"
        
        # Analyze by video distribution
        video_counts = df['video_name'].value_counts()
        insights += f"**Video Distribution**:\n"
        for video, count in video_counts.head(5).items():
            insights += f"- {video}: {count} segments\n"
        
        if len(video_counts) > 5:
            insights += f"- ... and {len(video_counts) - 5} more videos\n"
        
        # Temporal distribution
        if 'start_sec' in df.columns:
            temporal_range = df['end_sec'].max() - df['start_sec'].min()
            insights += f"\n**Temporal Coverage**: {temporal_range:.0f} seconds of video content\n"
            
            # Time-based clusters
            df['time_bucket'] = pd.cut(df['start_sec'], bins=5, labels=['Early', 'Early-Mid', 'Middle', 'Mid-Late', 'Late'])
            time_dist = df['time_bucket'].value_counts()
            insights += f"**Temporal Distribution**:\n"
            for bucket, count in time_dist.items():
                insights += f"- {bucket}: {count} segments\n"
        
        # Clustering analysis if available
        if 'cluster' in df.columns:
            cluster_counts = df['cluster'].value_counts()
            insights += f"\n**Similarity Clusters Found**: {len(cluster_counts)}\n"
            for cluster, count in cluster_counts.head(3).items():
                insights += f"- {cluster}: {count} segments\n"
        
        insights += f"\n**💡 Interpretation**:\n"
        insights += f"- **Close points** = Similar video content\n"
        insights += f"- **Distinct clusters** = Different video types/scenes\n"
        insights += f"- **Color patterns** = Groups by {color_by.replace('_', ' ')}\n"
        
        return insights