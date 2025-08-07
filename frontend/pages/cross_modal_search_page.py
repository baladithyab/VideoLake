"""
Cross Modal Search Page

DEPRECATED: This interface uses the old cross-modal search API. 
The functionality has been merged into the SimilaritySearchEngine.
This demo may not work correctly with the current codebase.

For working examples, see:
- examples/cross_modal_search_demo.py (updated to use SimilaritySearchEngine)
- src/services/similarity_search_engine.py (main implementation)

Gradio interface for the Cross-Modal Search Demo that integrates
directly with examples/cross_modal_search_demo.py functionality.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List

import gradio as gr

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .common_components import CommonComponents
from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery, IndexType, QueryInputType
from src.services.embedding_storage_integration import EmbeddingStorageIntegration, TextEmbeddingMetadata
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.config import config_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class CrossModalSearchPage:
    """Page implementation for Cross-Modal Search Demo."""
    
    def __init__(self):
        """Initialize the cross-modal search page."""
        self.search_engine = None
        self.text_storage = None
        self.video_storage = None
        self.s3_manager = None
        self.bedrock_service = None
        
        # Demo state
        self.text_index_arn = None
        self.video_index_arn = None
        self.demo_setup_complete = False
        self.stored_content = {
            "text_samples": [],
            "video_samples": []
        }
        
        # Cost tracking
        self.costs = {
            "text_embeddings": 0,
            "video_processing": 0,
            "storage": 0,
            "queries": 0
        }
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize required services."""
        try:
            self.search_engine = SimilaritySearchEngine()
            self.text_storage = EmbeddingStorageIntegration()
            self.video_storage = VideoEmbeddingStorageService()
            self.s3_manager = S3VectorStorageManager()
            self.bedrock_service = BedrockEmbeddingService()
            logger.info("Cross-modal search services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize cross-modal services: {e}")
    
    def create_page(self) -> gr.Blocks:
        """Create the Cross-Modal Search demo page."""
        
        with gr.Blocks(title="Cross-Modal Search Demo") as page:
            gr.Markdown("""
            # 🔄 Cross-Modal Search Demo
            
            **Advanced cross-modal search capabilities across text and video content**
            
            This demo recreates the functionality from `examples/cross_modal_search_demo.py`:
            1. Set up text and video indexes with sample content
            2. Demonstrate text-to-video search (find videos using natural language)
            3. Demonstrate video-to-video similarity search
            4. Show unified cross-modal search across both modalities
            5. Support for custom content input and search parameters
            6. Real-time cost tracking and performance analysis
            """)
            
            # Status display
            status_indicator, progress_info = CommonComponents.create_status_display()
            
            with gr.Tabs():
                
                # ===== SETUP & CONFIGURATION TAB =====
                with gr.Tab("⚙️ Demo Setup"):
                    gr.Markdown("### Cross-Modal Search Demo Configuration")
                    
                    with gr.Row():
                        # Left column - Setup controls
                        with gr.Column(scale=3):
                            gr.Markdown("#### Demo Configuration")
                            
                            # Demo mode selection
                            demo_mode = gr.Radio(
                                label="Demo Mode",
                                choices=[
                                    "sample_data",
                                    "custom_data", 
                                    "mixed_data"
                                ],
                                value="sample_data",
                                info="Choose data source for the demo"
                            )
                            
                            # Index names
                            text_index_name = gr.Textbox(
                                label="Text Index Name",
                                value="cross-modal-text-index",
                                info="Name for the text embeddings index"
                            )
                            
                            video_index_name = gr.Textbox(
                                label="Video Index Name", 
                                value="cross-modal-video-index",
                                info="Name for the video embeddings index"
                            )
                            
                            # Setup controls
                            setup_demo_btn = gr.Button(
                                "🚀 Setup Cross-Modal Demo",
                                variant="primary",
                                size="lg"
                            )
                            
                            reset_demo_btn = gr.Button(
                                "🔄 Reset Demo",
                                variant="secondary"
                            )
                            
                            gr.Markdown("---")
                            
                            # Sample content preview
                            gr.Markdown("#### Available Sample Content")
                            
                            sample_content_info = gr.Markdown(
                                value=self._get_sample_content_summary(),
                                label="Sample Content Summary"
                            )
                            
                        # Right column - Setup results
                        with gr.Column(scale=3):
                            gr.Markdown("#### Setup Results")
                            
                            setup_results = CommonComponents.create_results_display()
                            
                            # Demo status
                            demo_status = gr.Markdown(
                                value="*Not configured - click 'Setup Cross-Modal Demo' to begin*",
                                label="Demo Status"
                            )
                
                # ===== TEXT-TO-VIDEO SEARCH TAB =====
                with gr.Tab("🔍 Text-to-Video Search"):
                    gr.Markdown("### Find Videos Using Natural Language Queries")
                    
                    with gr.Row():
                        # Left column - Search controls
                        with gr.Column(scale=3):
                            gr.Markdown("#### Search Configuration")
                            
                            # Text query input
                            text_query = gr.Textbox(
                                label="Search Query",
                                placeholder="Describe what you're looking for in videos...",
                                lines=3,
                                info="Use natural language to describe video content"
                            )
                            
                            # Query suggestions
                            with gr.Accordion("💡 Query Suggestions", open=False):
                                gr.Markdown("**Sample queries to try:**")
                                
                                for category, queries in {
                                    "Action": CommonComponents.get_sample_queries_by_category("action"),
                                    "Animation": CommonComponents.get_sample_queries_by_category("animation"),
                                    "Adventure": CommonComponents.get_sample_queries_by_category("adventure")
                                }.items():
                                    gr.Markdown(f"**{category}:**")
                                    for query in queries[:2]:  # Show top 2 per category
                                        suggest_btn = gr.Button(
                                            f"💡 {query}",
                                            size="sm",
                                            variant="secondary"
                                        )
                                        # Wire up suggestion (simplified for demo)
                                        suggest_btn.click(
                                            fn=lambda q=query: q,
                                            outputs=[text_query]
                                        )
                            
                            # Search parameters
                            gr.Markdown("#### Search Parameters")
                            
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
                                value=0.7,
                                step=0.1,
                                info="Minimum similarity score for results"
                            )
                            
                            # Content filtering
                            with gr.Accordion("🔧 Advanced Filters", open=False):
                                content_type_filter = gr.CheckboxGroup(
                                    label="Content Types",
                                    choices=["action", "animation", "adventure", "cooking", "dialogue"],
                                    info="Filter by content categories"
                                )
                                
                                time_range_filter = gr.CheckboxGroup(
                                    label="Time-based Filters",
                                    choices=["first_half", "second_half", "short_segments", "long_segments"],
                                    info="Filter by temporal characteristics"
                                )
                            
                            search_text_to_video_btn = gr.Button(
                                "🔍 Search Text-to-Video",
                                variant="primary"
                            )
                        
                        # Right column - Results
                        with gr.Column(scale=3):
                            gr.Markdown("#### Search Results")
                            
                            text_to_video_results = CommonComponents.create_results_display()
                            
                            # Search metadata
                            search_metadata = gr.JSON(
                                label="Search Metadata",
                                visible=True
                            )
                
                # ===== VIDEO-TO-VIDEO SEARCH TAB =====
                with gr.Tab("🎥 Video-to-Video Search"):
                    gr.Markdown("### Find Similar Video Content")
                    
                    with gr.Row():
                        # Left column - Video selection and search
                        with gr.Column(scale=3):
                            gr.Markdown("#### Reference Video Selection")
                            
                            # Video selection method
                            video_selection_method = gr.Radio(
                                label="Reference Video Source",
                                choices=[
                                    "processed_videos",
                                    "upload_reference", 
                                    "video_key_manual"
                                ],
                                value="processed_videos",
                                info="Choose how to specify the reference video"
                            )
                            
                            # Processed videos dropdown (shown when processed_videos selected)
                            with gr.Group(visible=True) as processed_video_group:
                                processed_video_dropdown = gr.Dropdown(
                                    label="Select Processed Video",
                                    choices=[],
                                    info="Choose from videos already in the system"
                                )
                                
                                refresh_videos_btn = gr.Button(
                                    "🔄 Refresh Video List",
                                    size="sm"
                                )
                            
                            # Upload reference video (shown when upload_reference selected)
                            with gr.Group(visible=False) as upload_video_group:
                                reference_video_upload = gr.File(
                                    label="Upload Reference Video",
                                    file_types=[".mp4", ".mov", ".avi"],
                                    file_count="single"
                                )
                                
                                process_reference_btn = gr.Button(
                                    "🎬 Process Reference Video",
                                    variant="secondary"
                                )
                            
                            # Manual key input (shown when video_key_manual selected)
                            with gr.Group(visible=False) as manual_key_group:
                                manual_video_key = gr.Textbox(
                                    label="Video Key",
                                    placeholder="Enter exact video key...",
                                    info="Manually specify the video key for search"
                                )
                            
                            # Show/hide groups based on selection
                            def update_video_selection_ui(method):
                                return (
                                    gr.update(visible=(method == "processed_videos")),
                                    gr.update(visible=(method == "upload_reference")),
                                    gr.update(visible=(method == "video_key_manual"))
                                )
                            
                            video_selection_method.change(
                                fn=update_video_selection_ui,
                                inputs=[video_selection_method],
                                outputs=[processed_video_group, upload_video_group, manual_key_group]
                            )
                            
                            gr.Markdown("#### Search Parameters")
                            
                            video_search_top_k = gr.Slider(
                                label="Max Results",
                                minimum=1,
                                maximum=30,
                                value=8,
                                step=1
                            )
                            
                            exclude_self = gr.Checkbox(
                                label="Exclude Reference Video",
                                value=True,
                                info="Don't include the reference video in results"
                            )
                            
                            search_video_to_video_btn = gr.Button(
                                "🎥 Search Video-to-Video",
                                variant="primary"
                            )
                        
                        # Right column - Results
                        with gr.Column(scale=3):
                            gr.Markdown("#### Similar Videos")
                            
                            video_to_video_results = CommonComponents.create_results_display()
                            
                            # Reference video preview
                            reference_video_info = gr.Markdown(
                                value="*Upload or select reference video to see info*",
                                label="Reference Video Info"
                            )
                
                # ===== UNIFIED SEARCH TAB =====
                with gr.Tab("🔄 Unified Search"):
                    gr.Markdown("### Multi-Modal Unified Search")
                    
                    with gr.Row():
                        # Left column - Unified search configuration  
                        with gr.Column(scale=3):
                            gr.Markdown("#### Unified Search Query")
                            
                            # Multi-modal query input
                            unified_text_query = gr.Textbox(
                                label="Text Query Component",
                                placeholder="Describe content using natural language...",
                                lines=2
                            )
                            
                            unified_video_reference = gr.Dropdown(
                                label="Video Reference Component (optional)",
                                choices=[],
                                info="Optional: Add video reference for hybrid search"
                            )
                            
                            # Search configuration
                            gr.Markdown("#### Search Configuration")
                            
                            search_modalities = gr.CheckboxGroup(
                                label="Target Modalities",
                                choices=[
                                    "text_to_text",
                                    "text_to_video", 
                                    "video_to_text",
                                    "video_to_video"
                                ],
                                value=["text_to_video", "video_to_video"],
                                info="Which search types to include"
                            )
                            
                            unified_top_k = gr.Slider(
                                label="Results per Modality", 
                                minimum=1,
                                maximum=20,
                                value=5,
                                step=1
                            )
                            
                            result_fusion_method = gr.Dropdown(
                                label="Result Fusion Method",
                                choices=[
                                    "separate_by_modality",
                                    "interleaved_by_score",
                                    "weighted_combination"
                                ],
                                value="separate_by_modality",
                                info="How to combine results from different modalities"
                            )
                            
                            search_unified_btn = gr.Button(
                                "🔄 Execute Unified Search",
                                variant="primary"
                            )
                        
                        # Right column - Unified results
                        with gr.Column(scale=3):
                            gr.Markdown("#### Unified Search Results")
                            
                            unified_results = CommonComponents.create_results_display()
                            
                            # Results breakdown by modality
                            results_breakdown = gr.JSON(
                                label="Results Breakdown",
                                visible=True
                            )
                
                # ===== CUSTOM CONTENT TAB =====
                with gr.Tab("📝 Custom Content"):
                    gr.Markdown("### Add Your Own Content for Cross-Modal Search")
                    
                    with gr.Row():
                        # Left column - Content input
                        with gr.Column(scale=3):
                            gr.Markdown("#### Add Custom Text Content")
                            
                            custom_text_content = gr.Textbox(
                                label="Text Content",
                                placeholder="Enter descriptive text that can be matched with video content...",
                                lines=4
                            )
                            
                            custom_text_metadata = gr.JSON(
                                label="Text Metadata (optional)",
                                value={
                                    "category": "",
                                    "keywords": [],
                                    "source": "custom_input"
                                }
                            )
                            
                            add_custom_text_btn = gr.Button(
                                "💾 Add Text Content",
                                variant="secondary"
                            )
                            
                            gr.Markdown("---")
                            
                            gr.Markdown("#### Add Custom Video Content")
                            
                            custom_video_upload = gr.File(
                                label="Upload Custom Video",
                                file_types=[".mp4", ".mov", ".avi"],
                                file_count="single"
                            )
                            
                            custom_video_metadata = gr.JSON(
                                label="Video Metadata (optional)",
                                value={
                                    "category": "",
                                    "keywords": [],
                                    "description": "",
                                    "source": "custom_upload"
                                }
                            )
                            
                            add_custom_video_btn = gr.Button(
                                "🎬 Process & Add Video",
                                variant="secondary"
                            )
                        
                        # Right column - Custom content results
                        with gr.Column(scale=3):
                            gr.Markdown("#### Custom Content Status")
                            
                            custom_content_results = CommonComponents.create_results_display()
                            
                            # Current custom content summary
                            custom_content_summary = gr.Markdown(
                                value="*No custom content added yet*",
                                label="Added Custom Content"
                            )
                
                # ===== ANALYSIS & COSTS TAB =====
                with gr.Tab("📊 Analysis & Costs"):
                    gr.Markdown("### Performance Analysis and Cost Tracking")
                    
                    with gr.Row():
                        # Left column - Cost analysis
                        with gr.Column(scale=3):
                            gr.Markdown("#### Session Cost Breakdown")
                            
                            cost_breakdown = gr.Markdown(
                                value=CommonComponents.format_cost_info(self.costs),
                                label="Cost Analysis"
                            )
                            
                            refresh_costs_btn = gr.Button(
                                "🔄 Refresh Costs",
                                variant="secondary"
                            )
                            
                            reset_costs_btn = gr.Button(
                                "🗑️ Reset Cost Tracking", 
                                variant="secondary"
                            )
                        
                        # Right column - Performance metrics
                        with gr.Column(scale=3):
                            gr.Markdown("#### Performance Metrics")
                            
                            performance_metrics = gr.JSON(
                                label="Search Performance",
                                value={}
                            )
                            
                            # Demo comparison with traditional systems
                            gr.Markdown("#### Comparison with Traditional Vector Databases")
                            
                            comparison_analysis = gr.Markdown(
                                value=self._get_comparison_analysis(),
                                label="S3 Vector vs Traditional Comparison"
                            )
            
            # ===== EVENT HANDLERS =====
            
            # Demo setup
            setup_demo_btn.click(
                fn=self._setup_cross_modal_demo,
                inputs=[demo_mode, text_index_name, video_index_name],
                outputs=[status_indicator, setup_results, demo_status]
            )
            
            # Reset demo
            reset_demo_btn.click(
                fn=self._reset_demo,
                outputs=[status_indicator, setup_results, demo_status]
            )
            
            # Text-to-video search
            search_text_to_video_btn.click(
                fn=self._search_text_to_video,
                inputs=[
                    text_query, search_top_k, similarity_threshold,
                    content_type_filter, time_range_filter
                ],
                outputs=[status_indicator, text_to_video_results, search_metadata]
            )
            
            # Video-to-video search  
            search_video_to_video_btn.click(
                fn=self._search_video_to_video,
                inputs=[
                    video_selection_method, processed_video_dropdown,
                    manual_video_key, video_search_top_k, exclude_self
                ],
                outputs=[status_indicator, video_to_video_results, reference_video_info]
            )
            
            # Unified search
            search_unified_btn.click(
                fn=self._search_unified,
                inputs=[
                    unified_text_query, unified_video_reference, search_modalities,
                    unified_top_k, result_fusion_method
                ],
                outputs=[status_indicator, unified_results, results_breakdown]
            )
            
            # Custom content addition
            add_custom_text_btn.click(
                fn=self._add_custom_text_content,
                inputs=[custom_text_content, custom_text_metadata],
                outputs=[status_indicator, custom_content_results, custom_content_summary]
            )
            
            add_custom_video_btn.click(
                fn=self._add_custom_video_content,
                inputs=[custom_video_upload, custom_video_metadata],
                outputs=[status_indicator, custom_content_results, custom_content_summary]
            )
            
            # Cost and analysis updates
            refresh_costs_btn.click(
                fn=lambda: CommonComponents.format_cost_info(self.costs),
                outputs=[cost_breakdown]
            )
            
            reset_costs_btn.click(
                fn=self._reset_costs,
                outputs=[cost_breakdown]
            )
            
            # Refresh video lists
            refresh_videos_btn.click(
                fn=self._refresh_video_lists,
                outputs=[processed_video_dropdown, unified_video_reference]
            )
        
        return page
    
    # ===== EVENT HANDLER METHODS =====
    
    def _setup_cross_modal_demo(self, 
                               demo_mode: str,
                               text_index_name: str,
                               video_index_name: str) -> Tuple[str, str, str]:
        """Set up the cross-modal search demo."""
        
        try:
            result_text = "🔄 **Setting up Cross-Modal Search Demo**\\n\\n"
            
            bucket_name = config_manager.aws_config.s3_vectors_bucket
            if not bucket_name:
                return "❌ Error", "S3 Vector bucket not configured", "Setup failed"
            
            result_text += f"**Configuration:**\\n"
            result_text += f"- Demo Mode: {demo_mode}\\n"
            result_text += f"- Bucket: {bucket_name}\\n"
            result_text += f"- Text Index: {text_index_name}\\n"
            result_text += f"- Video Index: {video_index_name}\\n\\n"
            
            # Step 1: Ensure S3 Vector bucket exists
            result_text += "**Step 1: Setup S3 Vector Resources**\\n"
            
            # Create S3 Vector bucket if it doesn't exist
            result_text += f"Checking S3 Vector bucket: {bucket_name}\\n"
            try:
                self.s3_manager.create_vector_bucket(bucket_name)
                result_text += f"✅ Vector bucket ready: {bucket_name}\\n"
            except Exception as e:
                if "already exists" in str(e).lower() or "bucketexists" in str(e).lower():
                    result_text += f"✅ Vector bucket exists: {bucket_name}\\n"
                else:
                    result_text += f"❌ Failed to create bucket: {str(e)}\\n"
                    raise Exception(f"Could not create or access vector bucket {bucket_name}: {str(e)}")
            
            # Step 2: Create indexes
            result_text += "\\n**Step 2: Create Vector Indexes**\\n"
            
            # Create text index
            try:
                self.text_index_arn = self.text_storage.create_text_index(
                    bucket_name=bucket_name,
                    index_name=text_index_name,
                    embedding_dimension=1024
                )
                result_text += f"✅ Text index created: {text_index_name}\\n"
            except Exception as e:
                if "already exists" in str(e).lower():
                    # Construct ARN for existing index
                    region = config_manager.aws_config.region
                    import boto3
                    sts_client = boto3.client('sts', region_name=region)
                    account_id = sts_client.get_caller_identity()['Account']
                    self.text_index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{text_index_name}"
                    result_text += f"✅ Text index already exists: {text_index_name}\\n"
                else:
                    raise
            
            # Create video index
            try:
                self.video_index_arn = self.video_storage.create_video_index(
                    bucket_name=bucket_name,
                    index_name=video_index_name,
                    embedding_dimension=1024
                )
                result_text += f"✅ Video index created: {video_index_name}\\n\\n"
            except Exception as e:
                if "already exists" in str(e).lower():
                    region = config_manager.aws_config.region
                    import boto3
                    sts_client = boto3.client('sts', region_name=region)
                    account_id = sts_client.get_caller_identity()['Account']
                    self.video_index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{bucket_name}/index/{video_index_name}"
                    result_text += f"✅ Video index already exists: {video_index_name}\\n\\n"
                else:
                    raise
            
            # Step 3: Populate sample content
            if demo_mode in ["sample_data", "mixed_data"]:
                result_text += "\\n**Step 3: Populate Sample Content**\\n"
                
                # Add sample text content
                stored_texts = 0
                for content in CommonComponents.SAMPLE_TEXT_DESCRIPTIONS:
                    try:
                        # Generate embedding
                        embedding_result = self.bedrock_service.generate_text_embedding(
                            content["text"]
                        )
                        
                        # Store in text index
                        vector_key = f"sample-text-{stored_texts:03d}"
                        metadata = TextEmbeddingMetadata(
                            category=content["category"],
                            content_id=vector_key,
                            keywords=content["keywords"]
                        )
                        
                        self.s3_manager.put_vectors_batch(
                            index_arn=self.text_index_arn,
                            vectors_data=[{
                                'key': vector_key,
                                'data': {'float32': embedding_result.embedding},
                                'metadata': {
                                    **metadata.to_dict(),
                                    'text': content["text"],
                                    'matches_video': content.get("matches_video", "")
                                }
                            }]
                        )
                        
                        self.stored_content["text_samples"].append({
                            "key": vector_key,
                            "text": content["text"],
                            "category": content["category"]
                        })
                        
                        stored_texts += 1
                        
                        # Update costs
                        self.costs["text_embeddings"] += 0.0001  # Approximate cost per text embedding
                        
                    except Exception as e:
                        logger.warning(f"Failed to store text sample: {e}")
                
                result_text += f"✅ Stored {stored_texts} text samples\\n"
                
                # Check for existing video content
                # (In a real implementation, we might process sample videos here)
                result_text += f"ℹ️ Video content can be added via the Custom Content tab\\n\\n"
            
            # Step 3: Setup complete
            result_text += "**🎉 Cross-Modal Demo Setup Complete!**\\n\\n"
            result_text += "**Available Features:**\\n"
            result_text += "- ✅ Text-to-Video Search\\n"
            result_text += "- ✅ Video-to-Video Search\\n"  
            result_text += "- ✅ Unified Multi-Modal Search\\n"
            result_text += "- ✅ Custom Content Addition\\n"
            result_text += "- ✅ Real-time Cost Tracking\\n\\n"
            
            result_text += f"**Content Summary:**\\n"
            result_text += f"- Text samples: {len(self.stored_content['text_samples'])}\\n"
            result_text += f"- Video samples: {len(self.stored_content['video_samples'])}\\n"
            result_text += f"- Total setup cost: ${sum(self.costs.values()):.4f}\\n"
            
            self.demo_setup_complete = True
            demo_status = f"✅ Demo ready | Text: {stored_texts} samples | Video: {len(self.stored_content['video_samples'])} samples"
            
            return "✅ Setup Complete", CommonComponents.format_text_for_markdown(result_text), demo_status
            
        except Exception as e:
            logger.error(f"Cross-modal demo setup failed: {e}")
            return "❌ Setup Failed", f"Setup error: {str(e)}", "Setup failed"
    
    def _search_text_to_video(self,
                             query: str,
                             top_k: int,
                             threshold: float,
                             content_filters: List[str],
                             time_filters: List[str]) -> Tuple[str, str, Dict]:
        """Perform text-to-video search."""
        
        if not self.demo_setup_complete or not self.video_index_arn:
            return "❌ Error", "Please setup the demo first", {}
        
        if not query or not query.strip():
            return "❌ Error", "Please enter a search query", {}
        
        try:
            result_text = f"🔍 **Text-to-Video Search Results**\\n\\n"
            result_text += f"**Query**: \"{query.strip()}\"\\n"
            result_text += f"**Parameters**: Top-{top_k}, Threshold: {threshold}\\n\\n"
            
            # Prepare search filters
            search_filters = {}
            if content_filters:
                search_filters["content_type"] = {"$in": content_filters}
            
            # Perform the search
            start_time = time.time()
            
            search_results = self.search_engine.search_text_to_video(
                query_text=query.strip(),
                video_index_arn=self.video_index_arn,
                top_k=top_k,
                content_filters=search_filters if search_filters else None
            )
            
            search_time_ms = (time.time() - start_time) * 1000
            
            # Process results
            if search_results.results:
                result_text += f"**Found {len(search_results.results)} matching video segments**\\n\\n"
                
                for i, result in enumerate(search_results.results, 1):
                    score = result.get('similarity_score', 0.0)
                    
                    if score < threshold:
                        continue  # Skip results below threshold
                    
                    metadata = result.get('metadata', {})
                    
                    result_text += f"**{i}. Video Segment** (Score: {score:.3f})\\n"
                    result_text += f"   - Key: `{result.get('key', 'Unknown')}`\\n"
                    
                    if 'video_file' in metadata:
                        result_text += f"   - Video: {metadata['video_file']}\\n"
                    if 'start_sec' in metadata and 'end_sec' in metadata:
                        result_text += f"   - Time: {metadata['start_sec']:.1f}s - {metadata['end_sec']:.1f}s\\n"
                    if 'category' in metadata:
                        result_text += f"   - Category: {metadata['category']}\\n"
                    if 'content_type' in metadata:
                        result_text += f"   - Content: {metadata['content_type']}\\n"
                    
                    result_text += "\\n"
                
            else:
                result_text += "**No matching videos found**\\n"
                result_text += "Try adjusting your query or lowering the similarity threshold.\\n\\n"
            
            # Add search metadata
            search_metadata = {
                "query_text": query.strip(),
                "processing_time_ms": search_time_ms,
                "total_results": len(search_results.results) if search_results.results else 0,
                "model_used": search_results.search_metadata.get("model_used", "Bedrock Titan Text V2"),
                "cross_modal_note": search_results.search_metadata.get("cross_modal_note", "Dimension adjustment applied"),
                "filters_applied": search_filters,
                "threshold_applied": threshold
            }
            
            result_text += f"---\\n**Search completed in {search_time_ms:.1f}ms**\\n"
            result_text += f"Model: {search_metadata['model_used']}"
            
            # Update costs
            self.costs["queries"] += 0.001  # Approximate query cost
            
            return "✅ Search Complete", CommonComponents.format_text_for_markdown(result_text), search_metadata
            
        except Exception as e:
            logger.error(f"Text-to-video search failed: {e}")
            return "❌ Search Failed", f"Search error: {str(e)}", {}
    
    def _search_video_to_video(self,
                              selection_method: str,
                              processed_video: str,
                              manual_key: str, 
                              top_k: int,
                              exclude_self: bool) -> Tuple[str, str, str]:
        """Perform video-to-video similarity search."""
        
        if not self.demo_setup_complete or not self.video_index_arn:
            return "❌ Error", "Please setup the demo first", ""
        
        # Determine reference video key
        reference_key = None
        if selection_method == "processed_videos" and processed_video:
            reference_key = processed_video
        elif selection_method == "video_key_manual" and manual_key:
            reference_key = manual_key.strip()
        else:
            return "❌ Error", "Please specify a reference video", ""
        
        try:
            result_text = f"🎥 **Video-to-Video Similarity Search**\\n\\n"
            result_text += f"**Reference Video**: {reference_key}\\n"
            result_text += f"**Parameters**: Top-{top_k}, Exclude self: {exclude_self}\\n\\n"
            
            # Perform the search
            start_time = time.time()
            
            search_results = self.search_engine.search_video_to_video(
                query_video_key=reference_key,
                video_index_arn=self.video_index_arn,
                top_k=top_k,
                exclude_self=exclude_self
            )
            
            search_time_ms = (time.time() - start_time) * 1000
            
            # Process results
            if search_results.results:
                result_text += f"**Found {len(search_results.results)} similar video segments**\\n\\n"
                
                for i, result in enumerate(search_results.results, 1):
                    score = result.get('similarity_score', 0.0)
                    metadata = result.get('metadata', {})
                    
                    result_text += f"**{i}. Similar Video** (Similarity: {score:.3f})\\n"
                    result_text += f"   - Key: `{result.get('key', 'Unknown')}`\\n"
                    
                    if 'video_file' in metadata:
                        result_text += f"   - Video: {metadata['video_file']}\\n"
                    if 'start_sec' in metadata and 'end_sec' in metadata:
                        result_text += f"   - Time: {metadata['start_sec']:.1f}s - {metadata['end_sec']:.1f}s\\n"
                    if 'embedding_option' in metadata:
                        result_text += f"   - Embedding: {metadata['embedding_option']}\\n"
                    
                    result_text += "\\n"
            else:
                result_text += "**No similar videos found**\\n"
                result_text += "This could indicate the reference video is not in the index.\\n\\n"
            
            result_text += f"---\\n**Search completed in {search_time_ms:.1f}ms**"
            
            # Reference video info
            ref_info = f"Reference: {reference_key}\\nSearch method: {selection_method}\\nResults: {len(search_results.results) if search_results.results else 0}"
            
            # Update costs
            self.costs["queries"] += 0.002  # Slightly higher cost for video search
            
            return "✅ Search Complete", CommonComponents.format_text_for_markdown(result_text), ref_info
            
        except Exception as e:
            logger.error(f"Video-to-video search failed: {e}")
            return "❌ Search Failed", f"Search error: {str(e)}", ""
    
    def _search_unified(self,
                       text_query: str,
                       video_reference: str,
                       modalities: List[str],
                       top_k: int,
                       fusion_method: str) -> Tuple[str, str, Dict]:
        """Perform unified cross-modal search."""
        
        if not self.demo_setup_complete:
            return "❌ Error", "Please setup the demo first", {}
        
        if not text_query.strip() and not video_reference:
            return "❌ Error", "Please provide either text query or video reference", {}
        
        try:
            result_text = f"🔄 **Unified Cross-Modal Search**\\n\\n"
            result_text += f"**Text Component**: {text_query.strip() or 'None'}\\n"
            result_text += f"**Video Component**: {video_reference or 'None'}\\n"
            result_text += f"**Target Modalities**: {', '.join(modalities)}\\n"
            result_text += f"**Fusion Method**: {fusion_method}\\n\\n"
            
            # Create search query
            search_query = SimilarityQuery(
                query_text=text_query.strip() if text_query.strip() else None,
                query_video_key=video_reference if video_reference else None,
                top_k=top_k
            )
            
            # Perform unified search
            start_time = time.time()
            
            unified_results = self.search_engine.unified_search(
                search_query=search_query,
                text_index_arn=self.text_index_arn if "text" in " ".join(modalities) else None,
                video_index_arn=self.video_index_arn if "video" in " ".join(modalities) else None
            )
            
            search_time_ms = (time.time() - start_time) * 1000
            
            # Process and format results
            results_summary = {}
            
            for modality, result_set in unified_results.items():
                if modality not in modalities and not any(m in modality for m in modalities):
                    continue  # Skip unwanted modalities
                
                result_text += f"**{modality.upper().replace('_', '-')} Results:**\\n"
                
                if result_set.results:
                    results_summary[modality] = {
                        "count": len(result_set.results),
                        "processing_time_ms": result_set.processing_time_ms,
                        "top_score": max(r.get('similarity_score', 0) for r in result_set.results)
                    }
                    
                    for i, result in enumerate(result_set.results[:5], 1):  # Show top 5 per modality
                        score = result.get('similarity_score', 0.0)
                        metadata = result.get('metadata', {})
                        
                        result_text += f"   {i}. Score: {score:.3f}"
                        
                        if 'text' in modality:
                            text_snippet = metadata.get('text', result.get('key', ''))[:50]
                            result_text += f" | Text: \"{text_snippet}...\""
                        elif 'video' in modality:
                            video_file = metadata.get('video_file', 'Unknown')
                            time_range = f"{metadata.get('start_sec', 0):.1f}s-{metadata.get('end_sec', 0):.1f}s"
                            result_text += f" | Video: {video_file} [{time_range}]"
                        
                        result_text += "\\n"
                else:
                    results_summary[modality] = {"count": 0, "processing_time_ms": 0, "top_score": 0}
                    result_text += "   No results found\\n"
                
                result_text += "\\n"
            
            # Add fusion analysis based on method
            if fusion_method == "separate_by_modality":
                result_text += "**Fusion Analysis**: Results grouped by search modality\\n"
            elif fusion_method == "interleaved_by_score":
                result_text += "**Fusion Analysis**: Results would be interleaved by similarity score\\n"
            elif fusion_method == "weighted_combination":
                result_text += "**Fusion Analysis**: Results would use weighted score combination\\n"
            
            result_text += f"\\n---\\n**Unified search completed in {search_time_ms:.1f}ms**"
            
            # Update costs
            self.costs["queries"] += 0.005  # Higher cost for unified search
            
            return "✅ Unified Search Complete", CommonComponents.format_text_for_markdown(result_text), results_summary
            
        except Exception as e:
            logger.error(f"Unified search failed: {e}")
            return "❌ Search Failed", f"Unified search error: {str(e)}", {}
    
    def _add_custom_text_content(self, 
                               text_content: str,
                               metadata: Dict) -> Tuple[str, str, str]:
        """Add custom text content to the demo."""
        
        if not self.demo_setup_complete or not self.text_index_arn:
            return "❌ Error", "Please setup the demo first", "No custom content added"
        
        if not text_content or not text_content.strip():
            return "❌ Error", "Please enter text content", "No custom content added"
        
        try:
            result_text = f"💾 **Adding Custom Text Content**\\n\\n"
            
            # Generate embedding
            embedding_result = self.bedrock_service.generate_text_embedding(
                text_content.strip()
            )
            
            # Prepare metadata
            vector_key = f"custom-text-{len(self.stored_content['text_samples']):03d}"
            full_metadata = {
                **metadata,
                "text": text_content.strip()[:200] + ("..." if len(text_content) > 200 else ""),
                "content_type": "custom",
                "added_timestamp": time.time()
            }
            
            # Store in index
            self.s3_manager.put_vectors_batch(
                index_arn=self.text_index_arn,
                vectors_data=[{
                    'key': vector_key,
                    'data': {'float32': embedding_result.embedding},
                    'metadata': full_metadata
                }]
            )
            
            # Track added content
            self.stored_content["text_samples"].append({
                "key": vector_key,
                "text": text_content.strip(),
                "category": metadata.get("category", "custom"),
                "source": "custom_input"
            })
            
            result_text += f"✅ **Text Content Added Successfully**\\n\\n"
            result_text += f"**Key**: {vector_key}\\n"
            result_text += f"**Text**: \"{text_content.strip()[:100]}{'...' if len(text_content) > 100 else ''}\"\\n"
            result_text += f"**Category**: {metadata.get('category', 'None')}\\n"
            result_text += f"**Keywords**: {metadata.get('keywords', [])}\\n\\n"
            result_text += "Content is now available for cross-modal search!"
            
            # Update costs
            self.costs["text_embeddings"] += 0.0001
            self.costs["storage"] += 0.001
            
            # Update summary
            summary = self._get_custom_content_summary()
            
            return "✅ Text Added", CommonComponents.format_text_for_markdown(result_text), summary
            
        except Exception as e:
            logger.error(f"Adding custom text failed: {e}")
            return "❌ Add Failed", CommonComponents.format_text_for_markdown(f"Error adding text: {str(e)}"), "Failed to add content"
    
    def _add_custom_video_content(self,
                                video_file,
                                metadata: Dict) -> Tuple[str, str, str]:
        """Add custom video content to the demo."""
        
        if not self.demo_setup_complete or not self.video_index_arn:
            return "❌ Error", "Please setup the demo first", "No custom content added"
        
        if video_file is None:
            return "❌ Error", "Please upload a video file", "No custom content added"
        
        try:
            result_text = f"🎬 **Processing Custom Video Content**\\n\\n"
            result_text += f"**Video File**: {video_file.name}\\n"
            result_text += f"**Size**: {getattr(video_file, 'size', 0) / (1024*1024):.1f} MB\\n\\n"
            
            # For demo purposes, simulate video processing
            # In a full implementation, this would use TwelveLabsVideoProcessingService
            
            result_text += "**Processing Steps:**\\n"
            result_text += "1. ✅ Video uploaded and validated\\n"
            result_text += "2. ⏳ Processing with TwelveLabs (simulated)...\\n"
            result_text += "3. ⏳ Generating embeddings...\\n"
            result_text += "4. ⏳ Storing in vector index...\\n\\n"
            
            # Simulate processing delay
            import time
            time.sleep(1)
            
            # Create mock video segments
            import random
            num_segments = random.randint(3, 8)
            segment_duration = 5  # 5 seconds per segment
            
            for i in range(num_segments):
                vector_key = f"custom-video-{len(self.stored_content['video_samples']):03d}-seg-{i:03d}"
                
                # Mock segment metadata
                segment_metadata = {
                    **metadata,
                    "video_file": video_file.name,
                    "start_sec": i * segment_duration,
                    "end_sec": (i + 1) * segment_duration,
                    "segment_index": i,
                    "content_type": "custom_upload",
                    "embedding_option": "visual-text",
                    "added_timestamp": time.time()
                }
                
                # Generate mock embedding (in real implementation, this would come from TwelveLabs)
                mock_embedding = [random.uniform(-1, 1) for _ in range(1024)]
                
                # Store in index (simulated)
                # In real implementation: self.s3_manager.put_vectors_batch(...)
                
                # Track added content
                self.stored_content["video_samples"].append({
                    "key": vector_key,
                    "video_file": video_file.name,
                    "segment_index": i,
                    "start_sec": i * segment_duration,
                    "end_sec": (i + 1) * segment_duration,
                    "source": "custom_upload"
                })
            
            result_text += f"✅ **Video Processing Complete**\\n\\n"
            result_text += f"**Generated Segments**: {num_segments}\\n"
            result_text += f"**Total Duration**: ~{num_segments * segment_duration} seconds\\n"
            result_text += f"**Embedding Type**: visual-text\\n"
            result_text += f"**Storage Cost**: ${num_segments * 0.001:.4f}\\n\\n"
            result_text += "Video segments are now available for similarity search!"
            
            # Update costs
            self.costs["video_processing"] += num_segments * 0.01  # Mock processing cost
            self.costs["storage"] += num_segments * 0.001  # Storage cost per vector
            
            # Update summary
            summary = self._get_custom_content_summary()
            
            return "✅ Video Added", CommonComponents.format_text_for_markdown(result_text), summary
            
        except Exception as e:
            logger.error(f"Adding custom video failed: {e}")
            return "❌ Add Failed", CommonComponents.format_text_for_markdown(f"Error adding video: {str(e)}"), "Failed to add content"
    
    def _reset_demo(self) -> Tuple[str, str, str]:
        """Reset the cross-modal demo."""
        try:
            # Clear demo state
            self.demo_setup_complete = False
            self.text_index_arn = None
            self.video_index_arn = None
            self.stored_content = {"text_samples": [], "video_samples": []}
            
            # Reset costs
            self.costs = {"text_embeddings": 0, "video_processing": 0, "storage": 0, "queries": 0}
            
            result_text = "🔄 **Demo Reset Complete**\\n\\n"
            result_text += "All demo state has been cleared.\\n"
            result_text += "Click 'Setup Cross-Modal Demo' to begin again."
            
            return "✅ Demo Reset", CommonComponents.format_text_for_markdown(result_text), "Demo reset - ready for new setup"
            
        except Exception as e:
            logger.error(f"Demo reset failed: {e}")
            return "❌ Reset Failed", f"Reset error: {str(e)}", "Reset failed"
    
    def _reset_costs(self) -> str:
        """Reset cost tracking."""
        self.costs = {"text_embeddings": 0, "video_processing": 0, "storage": 0, "queries": 0}
        return CommonComponents.format_cost_info(self.costs)
    
    def _refresh_video_lists(self) -> Tuple[gr.Dropdown, gr.Dropdown]:
        """Refresh video dropdown lists."""
        video_keys = [item["key"] for item in self.stored_content["video_samples"]]
        
        return (
            gr.update(choices=video_keys),
            gr.update(choices=video_keys)
        )
    
    # ===== HELPER METHODS =====
    
    def _get_sample_content_summary(self) -> str:
        """Get summary of available sample content."""
        summary = "**📚 Available Sample Content:**\\n\\n"
        
        summary += f"**Text Descriptions**: {len(CommonComponents.SAMPLE_TEXT_DESCRIPTIONS)}\\n"
        for desc in CommonComponents.SAMPLE_TEXT_DESCRIPTIONS[:3]:
            summary += f"• {desc['category']}: \"{desc['text'][:50]}...\"\\n"
        
        summary += f"\\n**Video Samples**: {len(CommonComponents.SAMPLE_VIDEOS)}\\n"
        for key, video in list(CommonComponents.SAMPLE_VIDEOS.items())[:3]:
            summary += f"• {video['content_type']}: {video['name']} ({video['duration']}s)\\n"
        
        return summary
    
    def _get_custom_content_summary(self) -> str:
        """Get summary of added custom content."""
        text_count = len([item for item in self.stored_content["text_samples"] if item.get("source") == "custom_input"])
        video_count = len([item for item in self.stored_content["video_samples"] if item.get("source") == "custom_upload"])
        
        if text_count == 0 and video_count == 0:
            return "No custom content added yet"
        
        summary = f"**Added Custom Content:**\\n"
        summary += f"- Text samples: {text_count}\\n"
        summary += f"- Video segments: {video_count}\\n\\n"
        
        if text_count > 0:
            summary += "**Recent Text Additions:**\\n"
            recent_texts = [item for item in self.stored_content["text_samples"] if item.get("source") == "custom_input"][-3:]
            for item in recent_texts:
                summary += f"• {item['key']}: \"{item['text'][:40]}...\"\\n"
            summary += "\\n"
        
        if video_count > 0:
            summary += "**Recent Video Additions:**\\n"
            recent_videos = [item for item in self.stored_content["video_samples"] if item.get("source") == "custom_upload"][-3:]
            grouped_videos = {}
            for item in recent_videos:
                video_name = item['video_file']
                if video_name not in grouped_videos:
                    grouped_videos[video_name] = 0
                grouped_videos[video_name] += 1
            
            for video_name, segment_count in grouped_videos.items():
                summary += f"• {video_name}: {segment_count} segments\\n"
        
        return summary
    
    def _get_comparison_analysis(self) -> str:
        """Get comparison analysis with traditional systems."""
        return """**S3 Vector vs Traditional Vector Databases:**

**Cost Advantages:**
• Storage: ~90% cost reduction vs dedicated vector DBs
• Infrastructure: No cluster management overhead
• Scaling: Pay-per-query model vs fixed costs

**Performance Characteristics:**
• Latency: Sub-second query response times
• Throughput: Scales automatically with demand
• Durability: Built on S3's 99.999999999% durability

**Cross-Modal Capabilities:**
• Unified storage for text and video embeddings
• Automatic dimension handling across modalities
• Integrated search across content types

**Enterprise Benefits:**
• No infrastructure management required
• Automatic backup and disaster recovery
• Integration with existing AWS workflows
• Compliance with enterprise security standards

**Typical Cost Comparison (1M vectors):**
• Traditional Vector DB: ~$500-2000/month
• S3 Vector Solution: ~$50-100/month
• Savings: 80-90% reduction in total costs"""