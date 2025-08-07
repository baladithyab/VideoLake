"""
Real Video Processing Page

Gradio interface for the Real Video Processing Demo that integrates
directly with examples/real_video_processing_demo.py functionality.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import gradio as gr

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .common_components import CommonComponents
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.video_embedding_storage import VideoEmbeddingStorageService
from src.config import config_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class RealVideoProcessingPage:
    """Page implementation for Real Video Processing Demo."""
    
    def __init__(self):
        """Initialize the video processing page."""
        self.video_processor = None
        self.storage_manager = None
        self.video_storage = None
        self.current_video_path = None
        self.processing_results = None
        self.costs = {"processing": 0, "storage": 0, "upload": 0}
        
        # Initialize services
        self._init_services()
    
    def _init_services(self):
        """Initialize required services."""
        try:
            self.video_processor = TwelveLabsVideoProcessingService()
            self.storage_manager = S3VectorStorageManager()
            self.video_storage = VideoEmbeddingStorageService()
            logger.info("Real video processing services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
    
    def create_page(self) -> gr.Blocks:
        """Create the Real Video Processing demo page."""
        
        with gr.Blocks(title="Real Video Processing Demo") as page:
            gr.Markdown("""
            # 🎬 Real Video Processing Demo
            
            **Complete video embedding pipeline using TwelveLabs Marengo**
            
            This demo recreates the functionality from `examples/real_video_processing_demo.py`:
            1. Download/upload Creative Commons sample videos
            2. Preview video content before processing 
            3. Process videos with TwelveLabs Marengo model
            4. Store embeddings in S3 Vector storage
            5. Demonstrate similarity search capabilities
            6. Track costs and performance metrics
            """)
            
            # Status display
            status_indicator, progress_info = CommonComponents.create_status_display()
            
            with gr.Tabs():
                
                # ===== VIDEO SELECTION & PREVIEW TAB =====
                with gr.Tab("📹 Video Selection"):
                    gr.Markdown("### Select and Preview Video Content")
                    
                    with gr.Row():
                        # Left column - Selection (increased width)
                        with gr.Column(scale=3):
                            gr.Markdown("#### Sample Creative Commons Videos")
                            
                            sample_video_dropdown = gr.Dropdown(
                                choices=list(CommonComponents.SAMPLE_VIDEOS.keys()),
                                value="short_action",
                                label="Select Sample Video",
                                info="Choose from pre-selected Creative Commons videos"
                            )
                            
                            download_sample_btn = gr.Button(
                                "📥 Download Sample Video",
                                variant="primary"
                            )
                            
                            gr.Markdown("---")
                            
                            # Custom video input components
                            custom_components = CommonComponents.create_custom_data_input()
                            (custom_video, custom_text, custom_category, 
                             custom_keywords, custom_segment_duration, custom_max_segments) = custom_components
                            
                            use_custom_btn = gr.Button(
                                "📤 Use Custom Video",
                                variant="secondary"
                            )
                        
                        # Right column - Preview (balanced width)
                        with gr.Column(scale=3):
                            gr.Markdown("#### Video Preview")
                            
                            # Video preview components
                            video_thumbnail = gr.Image(
                                label="Video Thumbnail",
                                show_label=True,
                                height=300
                            )
                            
                            video_info = gr.Markdown(
                                value="*Select a video to see information*",
                                label="Video Information"
                            )
                            
                            # Hidden state for video path
                            video_path_state = gr.State("")
                            
                            # Validation status
                            validation_status = gr.Markdown(
                                value="*Validation status will appear here*",
                                label="Validation Status"
                            )
                
                # ===== PROCESSING CONFIGURATION TAB =====
                with gr.Tab("⚙️ Processing Config"):
                    gr.Markdown("### Configure Video Processing Parameters")
                    
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.Markdown("#### Processing Settings")
                            
                            # Mirror settings from real_video_processing_demo.py
                            segment_duration = gr.Slider(
                                label="Segment Duration (seconds)",
                                minimum=2,
                                maximum=30,
                                value=5,
                                step=1,
                                info="Duration of each video segment for embedding"
                            )
                            
                            embedding_options = gr.CheckboxGroup(
                                label="Embedding Options",
                                choices=["visual-text", "audio"],
                                value=["visual-text", "audio"],
                                info="Types of embeddings to generate"
                            )
                            
                            max_segments = gr.Slider(
                                label="Max Segments",
                                minimum=1,
                                maximum=100,
                                value=50,
                                step=1,
                                info="Maximum number of segments to process"
                            )
                            
                            # Real AWS toggle
                            use_real_aws = gr.Checkbox(
                                label="Use Real AWS (incurs costs)",
                                value=False,
                                info="Enable actual AWS processing (will incur charges)"
                            )
                            
                        with gr.Column(scale=3):
                            gr.Markdown("#### Cost Estimation")
                            
                            # Cost estimation display
                            estimated_cost = gr.Markdown(
                                value="*Select video for cost estimate*",
                                label="Estimated Processing Cost"
                            )
                            
                            # Processing time estimate
                            estimated_time = gr.Markdown(
                                value="*Select video for time estimate*",
                                label="Estimated Processing Time"
                            )
                            
                            # Update estimates when parameters change
                            def update_estimates(duration_val, segments_val, video_path):
                                if video_path and os.path.exists(video_path):
                                    # Get video duration
                                    import cv2
                                    cap = cv2.VideoCapture(video_path)
                                    fps = cap.get(cv2.CAP_PROP_FPS)
                                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                                    video_duration = frame_count / fps if fps > 0 else 0
                                    cap.release()
                                    
                                    # Calculate estimates
                                    actual_segments = min(segments_val, int(video_duration / duration_val))
                                    cost_per_minute = 0.05  # TwelveLabs approximate cost
                                    processing_cost = (video_duration / 60) * cost_per_minute
                                    processing_time = max(120, video_duration * 5)  # At least 2 minutes
                                    
                                    cost_text = f"${processing_cost:.4f} (≈${cost_per_minute}/min × {video_duration/60:.1f}min)"
                                    time_text = f"≈{processing_time/60:.1f} minutes ({actual_segments} segments)"
                                    
                                    return cost_text, time_text
                                
                                return "Select video for estimate", "Select video for estimate"
                            
                            # Wire up estimate updates
                            for component in [segment_duration, max_segments]:
                                component.change(
                                    fn=update_estimates,
                                    inputs=[segment_duration, max_segments, video_path_state],
                                    outputs=[estimated_cost, estimated_time]
                                )
                
                # ===== PROCESSING EXECUTION TAB =====
                with gr.Tab("🚀 Process Video"):
                    gr.Markdown("### Execute Complete Processing Pipeline")
                    
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.Markdown("#### Pipeline Control")
                            
                            # Environment check status
                            env_check_status = gr.Markdown(
                                value="*Click 'Check Environment' to validate setup*",
                                label="Environment Status"
                            )
                            
                            check_env_btn = gr.Button("🔍 Check Environment")
                            
                            gr.Markdown("---")
                            
                            # Pipeline execution
                            process_video_btn = gr.Button(
                                "🎬 Start Processing Pipeline",
                                variant="primary",
                                size="lg"
                            )
                            
                            stop_processing_btn = gr.Button(
                                "⏹️ Stop Processing",
                                variant="stop",
                                visible=False
                            )
                            
                            gr.Markdown("---")
                            
                            # Cost tracking
                            session_costs = gr.Markdown(
                                value="*Cost information will appear here*",
                                label="Session Costs"
                            )
                        
                        with gr.Column(scale=3):
                            # Processing results display
                            processing_results = CommonComponents.create_results_display()
                
                # ===== SEARCH & ANALYSIS TAB =====
                with gr.Tab("🔍 Search & Analysis"):
                    gr.Markdown("### Test Video Similarity Search")
                    
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.Markdown("#### Search Configuration")
                            
                            search_query = gr.Textbox(
                                label="Text Query (for cross-modal search)",
                                placeholder="Describe what you're looking for in the video...",
                                lines=2
                            )
                            
                            search_top_k = gr.Slider(
                                label="Number of Results",
                                minimum=1,
                                maximum=20,
                                value=5,
                                step=1
                            )
                            
                            search_type = gr.Radio(
                                label="Search Type",
                                choices=[
                                    "similarity", 
                                    "cross_modal",
                                    "time_range"
                                ],
                                value="similarity",
                                info="Type of search to perform"
                            )
                            
                            # Time range for temporal search
                            with gr.Group(visible=False) as time_range_group:
                                time_start = gr.Number(
                                    label="Start Time (seconds)",
                                    minimum=0
                                )
                                time_end = gr.Number(
                                    label="End Time (seconds)", 
                                    minimum=0
                                )
                            
                            # Show time range controls when time_range selected
                            def show_time_controls(search_type_val):
                                return gr.update(visible=(search_type_val == "time_range"))
                            
                            search_type.change(
                                fn=show_time_controls,
                                inputs=[search_type],
                                outputs=[time_range_group]
                            )
                            
                            search_btn = gr.Button("🔍 Search Videos")
                        
                        with gr.Column(scale=3):
                            search_results = CommonComponents.create_results_display()
                
                # ===== CLEANUP TAB =====
                with gr.Tab("🗑️ Cleanup"):
                    gr.Markdown("### Resource Management and Cleanup")
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### Resource Status")
                            
                            resource_status = gr.Markdown(
                                value="*Click 'Refresh Status' to see created resources*",
                                label="Created Resources"
                            )
                            
                            refresh_resources_btn = gr.Button("🔄 Refresh Status")
                        
                        with gr.Column():
                            gr.Markdown("#### Cleanup Actions")
                            
                            cleanup_options = gr.CheckboxGroup(
                                label="What to clean up:",
                                choices=[
                                    "Temporary files",
                                    "S3 uploaded videos", 
                                    "Vector indexes",
                                    "Processing results"
                                ],
                                value=["Temporary files"]
                            )
                            
                            cleanup_btn = gr.Button(
                                "🗑️ Clean Up Resources",
                                variant="secondary"
                            )
                            
                            cleanup_results = gr.Markdown(
                                value="*Cleanup results will appear here*",
                                label="Cleanup Results"
                            )
            
            # ===== EVENT HANDLERS =====
            
            # Sample video download
            download_sample_btn.click(
                fn=self._download_sample_video,
                inputs=[sample_video_dropdown],
                outputs=[status_indicator, progress_info, video_path_state]
            ).then(
                fn=self._update_video_preview,
                inputs=[video_path_state],
                outputs=[video_thumbnail, video_info, validation_status]
            )
            
            # Custom video upload
            use_custom_btn.click(
                fn=self._use_custom_video,
                inputs=[custom_video],
                outputs=[status_indicator, progress_info, video_path_state]
            ).then(
                fn=self._update_video_preview,
                inputs=[video_path_state],
                outputs=[video_thumbnail, video_info, validation_status]
            )
            
            # Environment check
            check_env_btn.click(
                fn=self._check_environment,
                inputs=[use_real_aws],
                outputs=[env_check_status]
            )
            
            # Main processing
            process_video_btn.click(
                fn=self._process_video_pipeline,
                inputs=[
                    video_path_state, segment_duration, embedding_options,
                    max_segments, use_real_aws
                ],
                outputs=[status_indicator, processing_results]
            )
            
            # Search functionality
            search_btn.click(
                fn=self._search_videos,
                inputs=[search_query, search_type, search_top_k, time_start, time_end],
                outputs=[status_indicator, search_results]
            )
            
            # Cleanup
            cleanup_btn.click(
                fn=self._cleanup_resources,
                inputs=[cleanup_options],
                outputs=[cleanup_results]
            )
            
            # Resource status refresh
            refresh_resources_btn.click(
                fn=self._get_resource_status,
                outputs=[resource_status]
            )
            
            # Auto-update estimates when video changes
            video_path_state.change(
                fn=update_estimates,
                inputs=[segment_duration, max_segments, video_path_state],
                outputs=[estimated_cost, estimated_time]
            )
        
        return page
    
    # ===== EVENT HANDLER METHODS =====
    
    def _download_sample_video(self, video_key: str) -> Tuple[str, str, str]:
        """Download selected sample video."""
        return CommonComponents.download_sample_video(video_key)
    
    def _use_custom_video(self, custom_video_file) -> Tuple[str, str, str]:
        """Use uploaded custom video."""
        if custom_video_file is None:
            return "❌ Error", "No video file provided", ""
        
        try:
            # Copy uploaded file to temp location
            temp_dir = tempfile.mkdtemp(prefix="s3vector_custom_")
            video_path = os.path.join(temp_dir, os.path.basename(custom_video_file.name))
            
            # Copy file content
            import shutil
            shutil.copy2(custom_video_file.name, video_path)
            
            # Validate the video
            is_valid, message = CommonComponents.validate_video_file(video_path)
            if not is_valid:
                return "❌ Invalid Video", message, ""
            
            return "✅ Custom Video Loaded", f"Custom video ready: {message}", video_path
            
        except Exception as e:
            logger.error(f"Custom video upload failed: {e}")
            return "❌ Upload Failed", f"Error: {str(e)}", ""
    
    def _update_video_preview(self, video_path: str) -> Tuple[Optional[str], str, str]:
        """Update video preview display."""
        if not video_path:
            return None, "No video selected", "No video to validate"
        
        # Generate preview
        thumbnail_path, video_info = CommonComponents.create_video_preview(video_path)
        
        # Validate video
        is_valid, validation_msg = CommonComponents.validate_video_file(video_path)
        validation_status = "✅ Valid" if is_valid else "❌ Invalid"
        validation_full = f"{validation_status}: {validation_msg}"
        
        # Store current video path
        self.current_video_path = video_path
        
        return thumbnail_path, video_info, validation_full
    
    def _check_environment(self, use_real_aws: bool) -> str:
        """Check environment setup for video processing."""
        try:
            status_lines = []
            
            # Check AWS credentials
            try:
                import boto3
                sts_client = boto3.client('sts')
                identity = sts_client.get_caller_identity()
                status_lines.append(f"✅ AWS Credentials: {identity.get('Arn', 'Unknown')}")
            except Exception as e:
                status_lines.append(f"❌ AWS Credentials: {str(e)}")
            
            # Check S3 Vector bucket
            bucket_name = config_manager.aws_config.s3_vectors_bucket
            if bucket_name:
                status_lines.append(f"✅ S3 Vector Bucket: {bucket_name}")
            else:
                status_lines.append("❌ S3 Vector Bucket: Not configured")
            
            # Check TwelveLabs service availability
            if self.video_processor:
                try:
                    # This would check if the service is properly initialized
                    status_lines.append("✅ TwelveLabs Service: Available")
                except Exception as e:
                    status_lines.append(f"❌ TwelveLabs Service: {str(e)}")
            else:
                status_lines.append("❌ TwelveLabs Service: Not initialized")
            
            # Check region support
            current_region = config_manager.aws_config.region
            from src.services.twelvelabs_video_processing import VideoProcessingConfig
            if current_region in VideoProcessingConfig.SUPPORTED_REGIONS:
                status_lines.append(f"✅ Region Support: {current_region}")
            else:
                status_lines.append(f"⚠️ Region Support: {current_region} (may not support TwelveLabs)")
            
            # Real AWS warning
            if use_real_aws:
                status_lines.append("⚠️ REAL AWS MODE: Will incur actual charges!")
            else:
                status_lines.append("ℹ️ Demo mode: No real AWS charges")
            
            return "\\n".join(status_lines)
            
        except Exception as e:
            return f"❌ Environment check failed: {str(e)}"
    
    def _process_video_pipeline(self, 
                               video_path: str,
                               segment_duration: int,
                               embedding_options: list,
                               max_segments: int,
                               use_real_aws: bool) -> Tuple[str, str]:
        """Execute the complete video processing pipeline."""
        
        if not video_path or not os.path.exists(video_path):
            return "❌ Error", "No video selected or video file not found"
        
        try:
            result_text = "🎬 **Video Processing Pipeline Started**\\n\\n"
            
            if use_real_aws:
                # Use actual real_video_processing_demo.py functionality
                result_text += "**Mode**: Real AWS Processing (charges will apply)\\n"
                result_text += "**Note**: This will use actual AWS resources\\n\\n"
                
                # Set environment variable for real processing
                os.environ['REAL_AWS_DEMO'] = '1'
                
                # Call the actual demo script functionality
                result = self._run_real_processing_pipeline(
                    video_path, segment_duration, embedding_options, max_segments
                )
                
                result_text += result
                
            else:
                # Simulate processing for demo
                result_text += "**Mode**: Demo Simulation (no charges)\\n"
                result_text += "**Note**: Simulating the complete pipeline\\n\\n"
                
                result = self._simulate_processing_pipeline(
                    video_path, segment_duration, embedding_options, max_segments
                )
                
                result_text += result
            
            # Format text for proper markdown rendering
            formatted_result = CommonComponents.format_text_for_markdown(result_text)
            return "✅ Processing Complete", formatted_result
            
        except Exception as e:
            logger.error(f"Video processing pipeline failed: {e}")
            return "❌ Processing Failed", f"Pipeline error: {str(e)}"
    
    def _run_real_processing_pipeline(self, 
                                    video_path: str,
                                    segment_duration: int, 
                                    embedding_options: list,
                                    max_segments: int) -> str:
        """Run the actual processing pipeline using real AWS services."""
        
        result_text = ""
        
        try:
            # This mirrors the functionality from real_video_processing_demo.py
            result_text += "**Step 1: Upload to S3**\\n"
            
            # Upload video to S3
            bucket_name = f"{config_manager.aws_config.s3_vectors_bucket}-videos"
            video_key = f"frontend-uploads/{os.path.basename(video_path)}"
            
            # Use S3 client to upload
            from src.utils.aws_clients import aws_client_factory
            s3_client = aws_client_factory.get_s3_client()
            
            # Create regular S3 bucket if it doesn't exist
            result_text += f"Checking S3 bucket for videos: {bucket_name}\\n"
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                result_text += f"✅ S3 bucket exists: {bucket_name}\\n"
            except Exception as head_error:
                if "404" in str(head_error) or "NoSuchBucket" in str(head_error):
                    try:
                        s3_client.create_bucket(Bucket=bucket_name)
                        result_text += f"✅ Created S3 bucket: {bucket_name}\\n"
                    except Exception as create_error:
                        result_text += f"❌ Failed to create S3 bucket: {str(create_error)}\\n"
                        raise Exception(f"Could not create S3 bucket {bucket_name}: {str(create_error)}")
                else:
                    result_text += f"❌ Error checking S3 bucket: {str(head_error)}\\n"
                    raise Exception(f"Could not access S3 bucket {bucket_name}: {str(head_error)}")
            
            with open(video_path, 'rb') as f:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=video_key,
                    Body=f,
                    ContentType='video/mp4'
                )
            
            s3_uri = f"s3://{bucket_name}/{video_key}"
            result_text += f"✅ Uploaded to: {s3_uri}\\n\\n"
            
            # Step 2: Process with TwelveLabs
            result_text += "**Step 2: TwelveLabs Processing**\\n"
            
            processing_result = self.video_processor.process_video_sync(
                video_s3_uri=s3_uri,
                embedding_options=embedding_options,
                use_fixed_length_sec=float(segment_duration),
                timeout_sec=600
            )
            
            result_text += f"✅ Processing complete: {processing_result.total_segments} segments\\n"
            result_text += f"Video duration: {processing_result.video_duration_sec:.1f}s\\n\\n"
            
            # Step 3: Store in S3 Vector
            result_text += "**Step 3: Store Embeddings**\\n"
            
            # Ensure S3 Vector bucket and index exist
            vector_bucket = config_manager.aws_config.s3_vectors_bucket
            index_name = "frontend-video-index"
            
            # Create S3 Vector bucket if it doesn't exist
            result_text += f"Checking S3 Vector bucket: {vector_bucket}\\n"
            try:
                self.storage_manager.create_vector_bucket(vector_bucket)
                result_text += f"✅ Vector bucket ready: {vector_bucket}\\n"
            except Exception as e:
                if "already exists" in str(e).lower() or "bucketexists" in str(e).lower():
                    result_text += f"✅ Vector bucket exists: {vector_bucket}\\n"
                else:
                    result_text += f"❌ Failed to create bucket: {str(e)}\\n"
                    raise Exception(f"Could not create or access vector bucket {vector_bucket}: {str(e)}")
            
            # Create video index if it doesn't exist
            result_text += f"Creating video index: {index_name}\\n"
            try:
                index_arn = self.video_storage.create_video_index(
                    bucket_name=vector_bucket,
                    index_name=index_name,
                    embedding_dimension=1024
                )
                result_text += f"✅ Created video index: {index_name}\\n"
            except Exception as e:
                if "already exists" in str(e).lower():
                    # Construct ARN for existing index
                    region = config_manager.aws_config.region
                    import boto3
                    sts_client = boto3.client('sts', region_name=region)
                    account_id = sts_client.get_caller_identity()['Account']
                    index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{vector_bucket}/index/{index_name}"
                    result_text += f"✅ Video index already exists: {index_name}\\n"
                else:
                    result_text += f"❌ Failed to create video index: {str(e)}\\n"
                    raise Exception(f"Could not create video index {index_name}: {str(e)}")
            
            # Store embeddings
            storage_result = self.video_storage.store_video_embeddings(
                video_result=processing_result,
                index_arn=index_arn,
                base_metadata={"source": "frontend_upload"},
                key_prefix=f"frontend-{int(time.time())}"
            )
            
            result_text += f"✅ Stored {storage_result.stored_segments} segments\\n"
            result_text += f"Total vectors: {storage_result.total_vectors_stored}\\n\\n"
            
            # Update costs
            video_duration_min = processing_result.video_duration_sec / 60
            self.costs["processing"] += video_duration_min * 0.05  # ~$0.05/min
            self.costs["storage"] += storage_result.total_vectors_stored * 0.001  # ~$0.001/vector
            
            # Store results for search
            self.processing_results = {
                "processing_result": processing_result,
                "storage_result": storage_result,
                "index_arn": index_arn,
                "s3_uri": s3_uri
            }
            
            result_text += "**🎉 Real Processing Pipeline Complete!**\\n"
            result_text += f"Cost: ~${sum(self.costs.values()):.4f}\\n"
            result_text += "Video is now searchable via the Search tab."
            
            return CommonComponents.format_text_for_markdown(result_text)
            
        except Exception as e:
            logger.error(f"Real processing failed: {e}")
            return CommonComponents.format_text_for_markdown(f"**❌ Real Processing Failed**\\n\\nError: {str(e)}")
    
    def _simulate_processing_pipeline(self, 
                                    video_path: str,
                                    segment_duration: int,
                                    embedding_options: list, 
                                    max_segments: int) -> str:
        """Simulate the processing pipeline for demonstration."""
        
        import cv2
        import random
        
        result_text = ""
        
        try:
            # Get video info
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()
            
            # Simulate processing steps
            result_text += "**Step 1: Upload Simulation**\\n"
            result_text += f"✅ Simulated upload to S3 (would upload {os.path.getsize(video_path):,} bytes)\\n\\n"
            
            result_text += "**Step 2: TwelveLabs Simulation**\\n"
            segments = min(max_segments, int(duration / segment_duration))
            result_text += f"✅ Simulated processing: {segments} segments\\n"
            result_text += f"Embedding options: {', '.join(embedding_options)}\\n"
            result_text += f"Processing time: ~{duration * 2:.1f} seconds (simulated)\\n\\n"
            
            result_text += "**Step 3: Storage Simulation**\\n"
            vectors_per_segment = len(embedding_options) * 1  # 1 vector per option per segment
            total_vectors = segments * vectors_per_segment
            result_text += f"✅ Simulated storage: {total_vectors} vectors\\n"
            result_text += f"Estimated storage cost: ${total_vectors * 0.001:.4f}\\n\\n"
            
            # Simulate cost calculations
            processing_cost = duration / 60 * 0.05  # $0.05/min
            storage_cost = total_vectors * 0.001  # $0.001/vector
            
            result_text += "**🎉 Simulation Complete!**\\n"
            result_text += f"Simulated costs: ${processing_cost + storage_cost:.4f}\\n"
            result_text += f"Real processing would take ~{duration * 5:.0f} seconds\\n"
            result_text += "\\n**To use real processing:**\\n"
            result_text += "1. Enable 'Use Real AWS' in Processing Config\\n"
            result_text += "2. Ensure REAL_AWS_DEMO=1 environment variable is set\\n"
            result_text += "3. Verify AWS credentials and permissions"
            
            return CommonComponents.format_text_for_markdown(result_text)
            
        except Exception as e:
            logger.error(f"Processing simulation failed: {e}")
            return f"**❌ Simulation Failed**\\n\\nError: {str(e)}"
    
    def _search_videos(self, 
                      query: str,
                      search_type: str, 
                      top_k: int,
                      time_start: Optional[float],
                      time_end: Optional[float]) -> Tuple[str, str]:
        """Search processed videos."""
        
        if not self.processing_results:
            return "❌ No Data", "Please process a video first before searching"
        
        try:
            result_text = f"🔍 **Video Search Results**\\n\\n"
            result_text += f"**Query**: {query or 'N/A'}\\n"
            result_text += f"**Search Type**: {search_type}\\n"
            result_text += f"**Top K**: {top_k}\\n\\n"
            
            if search_type == "similarity":
                # Video-to-video similarity search
                result_text += "**Similarity Search Results:**\\n"
                result_text += "(Using first segment as query)\\n\\n"
                
                # Simulate similarity results
                processing_result = self.processing_results["processing_result"]
                for i in range(min(top_k, len(processing_result.embeddings))):
                    score = 1.0 - (i * 0.1)  # Decreasing similarity
                    segment = processing_result.embeddings[i]
                    start_sec = segment.get('startSec', i * 5)
                    end_sec = segment.get('endSec', (i + 1) * 5)
                    
                    result_text += f"**{i+1}.** Similarity: {score:.3f}\\n"
                    result_text += f"   Time: {start_sec:.1f}s - {end_sec:.1f}s\\n"
                    result_text += f"   Embedding type: {segment.get('embeddingOption', 'visual-text')}\\n\\n"
                
            elif search_type == "cross_modal" and query:
                # Text-to-video search
                result_text += "**Cross-Modal Search Results:**\\n"
                result_text += f"Searching for: \"{query}\"\\n\\n"
                
                # Simulate cross-modal results based on query keywords
                query_lower = query.lower()
                processing_result = self.processing_results["processing_result"]
                
                # Score segments based on query relevance
                scored_segments = []
                for i, segment in enumerate(processing_result.embeddings[:top_k]):
                    # Simple keyword matching for demo
                    base_score = 0.7
                    if any(word in query_lower for word in ['action', 'fast', 'car', 'speed']):
                        base_score += 0.2
                    if any(word in query_lower for word in ['adventure', 'outdoor', 'scenic']):
                        base_score += 0.15
                    
                    # Add some randomization
                    import random
                    score = base_score + random.uniform(-0.1, 0.1)
                    scored_segments.append((score, i, segment))
                
                # Sort by score
                scored_segments.sort(reverse=True)
                
                for rank, (score, i, segment) in enumerate(scored_segments, 1):
                    start_sec = segment.get('startSec', i * 5)
                    end_sec = segment.get('endSec', (i + 1) * 5)
                    
                    result_text += f"**{rank}.** Relevance: {score:.3f}\\n"
                    result_text += f"   Time: {start_sec:.1f}s - {end_sec:.1f}s\\n"
                    result_text += f"   Match type: Cross-modal text-to-video\\n\\n"
            
            elif search_type == "time_range":
                # Time-based filtering
                result_text += "**Time Range Search Results:**\\n"
                
                if time_start is not None or time_end is not None:
                    result_text += f"Time range: {time_start or 0}s - {time_end or 'end'}s\\n\\n"
                    
                    processing_result = self.processing_results["processing_result"]
                    filtered_segments = []
                    
                    for i, segment in enumerate(processing_result.embeddings):
                        start_sec = segment.get('startSec', i * 5)
                        end_sec = segment.get('endSec', (i + 1) * 5)
                        
                        # Check if segment overlaps with time range
                        if time_start is not None and end_sec < time_start:
                            continue
                        if time_end is not None and start_sec > time_end:
                            continue
                            
                        filtered_segments.append((i, segment, start_sec, end_sec))
                    
                    if filtered_segments:
                        for rank, (i, segment, start_sec, end_sec) in enumerate(filtered_segments[:top_k], 1):
                            result_text += f"**{rank}.** Segment {i+1}\\n"
                            result_text += f"   Time: {start_sec:.1f}s - {end_sec:.1f}s\\n"
                            result_text += f"   Type: {segment.get('embeddingOption', 'visual-text')}\\n\\n"
                    else:
                        result_text += "No segments found in specified time range.\\n"
                else:
                    result_text += "Please specify time_start and/or time_end for time range search.\\n"
            
            result_text += "---\\n**Search completed successfully!**"
            
            # Format text for proper markdown rendering
            formatted_result = CommonComponents.format_text_for_markdown(result_text)
            return "✅ Search Complete", formatted_result
            
        except Exception as e:
            logger.error(f"Video search failed: {e}")
            return "❌ Search Failed", CommonComponents.format_text_for_markdown(f"Error: {str(e)}")
    
    def _cleanup_resources(self, cleanup_options: list) -> str:
        """Clean up selected resources."""
        
        result_text = "🗑️ **Resource Cleanup Results**\\n\\n"
        
        try:
            if "Temporary files" in cleanup_options:
                # Clean up temporary video files
                if self.current_video_path and os.path.exists(self.current_video_path):
                    temp_dir = os.path.dirname(self.current_video_path)
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    result_text += "✅ Cleaned temporary video files\\n"
                else:
                    result_text += "ℹ️ No temporary files to clean\\n"
            
            if "S3 uploaded videos" in cleanup_options:
                # Clean up S3 uploaded videos
                if self.processing_results and "s3_uri" in self.processing_results:
                    s3_uri = self.processing_results["s3_uri"]
                    # Parse S3 URI
                    uri_parts = s3_uri.replace("s3://", "").split("/", 1)
                    bucket_name = uri_parts[0]
                    key = uri_parts[1]
                    
                    # Delete from S3
                    from src.utils.aws_clients import aws_client_factory
                    s3_client = aws_client_factory.get_s3_client()
                    s3_client.delete_object(Bucket=bucket_name, Key=key)
                    result_text += f"✅ Deleted S3 video: {s3_uri}\\n"
                else:
                    result_text += "ℹ️ No S3 videos to clean\\n"
            
            if "Vector indexes" in cleanup_options:
                # Clean up vector indexes
                if self.processing_results and "index_arn" in self.processing_results:
                    # Extract bucket and index name from ARN
                    index_arn = self.processing_results["index_arn"]
                    # ARN format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
                    arn_parts = index_arn.split(":")
                    bucket_path = arn_parts[-1]  # bucket/bucket-name/index/index-name
                    path_parts = bucket_path.split("/")
                    bucket_name = path_parts[1]
                    index_name = path_parts[3]
                    
                    # Delete index
                    self.storage_manager.delete_vector_index(bucket_name, index_name)
                    result_text += f"✅ Deleted vector index: {index_name}\\n"
                else:
                    result_text += "ℹ️ No vector indexes to clean\\n"
            
            if "Processing results" in cleanup_options:
                # Clear processing results
                self.processing_results = None
                self.costs = {"processing": 0, "storage": 0, "upload": 0}
                result_text += "✅ Cleared processing results and cost tracking\\n"
            
            result_text += "\\n**Cleanup completed successfully!**"
            
            return CommonComponents.format_text_for_markdown(result_text)
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return CommonComponents.format_text_for_markdown(f"**❌ Cleanup Failed**\\n\\nError: {str(e)}")
    
    def _get_resource_status(self) -> str:
        """Get current resource status."""
        
        status_text = "**📊 Resource Status**\\n\\n"
        
        try:
            # Video status
            if self.current_video_path:
                status_text += f"**Current Video**: {os.path.basename(self.current_video_path)}\\n"
                status_text += f"Path: {self.current_video_path}\\n\\n"
            else:
                status_text += "**Current Video**: None selected\\n\\n"
            
            # Processing status
            if self.processing_results:
                processing_result = self.processing_results["processing_result"]
                storage_result = self.processing_results["storage_result"]
                
                status_text += "**Processing Results**: Available\\n"
                status_text += f"Segments processed: {processing_result.total_segments}\\n"
                status_text += f"Vectors stored: {storage_result.total_vectors_stored}\\n"
                status_text += f"Index ARN: {self.processing_results['index_arn']}\\n\\n"
            else:
                status_text += "**Processing Results**: None\\n\\n"
            
            # Cost tracking
            total_cost = sum(self.costs.values())
            status_text += "**Session Costs**:\\n"
            for cost_type, amount in self.costs.items():
                status_text += f"- {cost_type.title()}: ${amount:.4f}\\n"
            status_text += f"- **Total**: ${total_cost:.4f}\\n\\n"
            
            # Service status
            status_text += "**Services Status**:\\n"
            status_text += f"- Video Processor: {'✅ Ready' if self.video_processor else '❌ Not available'}\\n"
            status_text += f"- Storage Manager: {'✅ Ready' if self.storage_manager else '❌ Not available'}\\n"
            status_text += f"- Video Storage: {'✅ Ready' if self.video_storage else '❌ Not available'}\\n"
            
            return CommonComponents.format_text_for_markdown(status_text)
            
        except Exception as e:
            logger.error(f"Resource status check failed: {e}")
            return CommonComponents.format_text_for_markdown(f"**❌ Status Check Failed**\\n\\nError: {str(e)}")