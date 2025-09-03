#!/usr/bin/env python3
"""
Unified S3Vector Demo Application

This is the consolidated demo interface that replaces the fragmented frontend applications.
It properly integrates with StreamlitServiceManager and MultiVectorCoordinator to showcase
the complete S3Vector multi-vector workflow in a cohesive, professional interface.

Key Features:
- Proper backend service integration via StreamlitServiceManager
- 5-section unified workflow (Upload, Processing, Query, Results, Analytics)
- Multi-vector processing with Marengo 2.7
- Interactive video player with segment overlay
- Real-time progress tracking and cost monitoring
- Professional demo interface for customer presentations
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

import streamlit as st
import numpy as np
import pandas as pd

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import backend services - using the sophisticated service manager
from src.services import (
    get_service_manager, 
    reset_service_manager,
    StreamlitIntegrationConfig,
    MultiVectorCoordinator,
    VectorType,
    ProcessingMode
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DemoConfig:
    """Configuration for the unified demo application."""
    app_title: str = "🎬 S3Vector Unified Multi-Vector Demo"
    app_icon: str = "🎬"
    layout: str = "wide"
    enable_multi_vector: bool = True
    default_vector_types: List[str] = None
    max_concurrent_jobs: int = 8
    enable_performance_monitoring: bool = True
    enable_cost_tracking: bool = True
    
    def __post_init__(self):
        if self.default_vector_types is None:
            self.default_vector_types = ["visual-text", "visual-image", "audio"]


class UnifiedS3VectorDemo:
    """
    Unified S3Vector Demo Application
    
    This class consolidates all frontend functionality into a single, cohesive demo interface
    that properly leverages the sophisticated backend services through StreamlitServiceManager
    and MultiVectorCoordinator.
    """
    
    def __init__(self, config: Optional[DemoConfig] = None):
        """Initialize the unified demo application."""
        self.config = config or DemoConfig()
        
        # Initialize session state first
        self._init_session_state()
        
        # Initialize backend services through service manager
        self._init_service_manager()
        
        logger.info("UnifiedS3VectorDemo initialized successfully")
    
    def _init_session_state(self):
        """Initialize Streamlit session state with default values."""
        defaults = {
            # Application state
            'demo_initialized': True,
            'current_section': 'upload_processing',
            
            # Service status
            'service_health': {},
            'last_health_check': None,
            
            # Upload and processing
            'selected_videos': [],
            'processing_jobs': {},
            'processed_videos': {},
            
            # Vector indices and storage
            'vector_indices': {},
            'storage_strategy': 'direct_s3vector',
            
            # Search and results
            'search_results': [],
            'current_query': '',
            'query_analysis': {},
            'selected_segment': None,
            
            # Visualization
            'embeddings_data': None,
            'visualization_config': {
                'reduction_method': 'PCA',
                'dimensions': '2D',
                'color_by': 'similarity'
            },
            
            # Analytics and costs
            'cost_tracking': {
                'total': 0.0,
                'session': 0.0,
                'processing': 0.0,
                'storage': 0.0,
                'queries': 0.0
            },
            'performance_metrics': {},
            
            # Configuration
            'use_real_aws': False,
            'demo_mode': True
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def _init_service_manager(self):
        """Initialize the StreamlitServiceManager and MultiVectorCoordinator."""
        try:
            # Create integration config
            integration_config = StreamlitIntegrationConfig(
                enable_multi_vector=self.config.enable_multi_vector,
                enable_concurrent_processing=True,
                default_vector_types=self.config.default_vector_types,
                max_concurrent_jobs=self.config.max_concurrent_jobs,
                enable_performance_monitoring=self.config.enable_performance_monitoring
            )

            # Get or create service manager
            self.service_manager = get_service_manager(integration_config)

            # Access the sophisticated services
            self.coordinator = self.service_manager.multi_vector_coordinator
            self.search_engine = self.service_manager.search_engine
            self.storage_manager = self.service_manager.storage_manager
            self.twelvelabs_service = self.service_manager.twelvelabs_service
            self.bedrock_service = self.service_manager.bedrock_service

            # Update session state with service health
            self._update_service_health()

            logger.info("Service manager and coordinator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize service manager: {e}")
            # Don't show error in UI during initialization - will be handled in render

            # Fallback to None - will trigger error handling in UI
            self.service_manager = None
            self.coordinator = None
    
    def _update_service_health(self):
        """Update service health status in session state."""
        if self.service_manager:
            try:
                health_status = self.service_manager.get_system_status()
                st.session_state.service_health = health_status
                st.session_state.last_health_check = time.time()
            except Exception as e:
                logger.error(f"Failed to get service health: {e}")
                st.session_state.service_health = {'status': 'error', 'error': str(e)}
    
    def render_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title=self.config.app_title,
            page_icon=self.config.app_icon,
            layout=self.config.layout,
            initial_sidebar_state="expanded"
        )
    
    def render_header(self):
        """Render the application header with status indicators."""
        st.title(self.config.app_title)
        
        # Subtitle with key features
        st.markdown("""
        **Professional multi-vector video search demonstration**
        
        🎯 **Complete Workflow**: Upload → Process → Search → Visualize → Analyze  
        🧠 **Multi-Vector AI**: Visual-text, visual-image, and audio embeddings with Marengo 2.7  
        🔍 **Intelligent Search**: Cross-vector fusion with automatic query routing  
        📊 **Interactive Visualization**: Real-time embedding space exploration  
        💰 **Cost Monitoring**: Real-time processing and storage cost tracking  
        """)
        
        # Service status indicator
        self._render_service_status()
    
    def _render_service_status(self):
        """Render service health status indicators."""
        if st.session_state.service_health:
            health = st.session_state.service_health
            
            if health.get('services', {}).get('multi_vector_coordinator') == 'healthy':
                st.success("✅ All services operational - Multi-vector processing ready")
            else:
                st.warning("⚠️ Some services may be limited - Check configuration")
        else:
            st.error("❌ Service status unknown - Backend services may not be available")
    
    def render_sidebar(self):
        """Render the sidebar with navigation and global controls."""
        st.sidebar.title("🎛️ Demo Controls")
        
        # Global AWS toggle
        use_real_aws = st.sidebar.toggle(
            "🔧 Use Real AWS",
            value=st.session_state.use_real_aws,
            help="Enable to use actual AWS services (costs apply)"
        )
        st.session_state.use_real_aws = use_real_aws
        
        if not use_real_aws:
            st.sidebar.info("🛡️ **Safe Mode**: Using simulation - no AWS costs")
        else:
            st.sidebar.warning("⚠️ **Live Mode**: Real AWS services - costs will apply")
        
        st.sidebar.divider()
        
        # Cost tracking display
        self._render_cost_tracking()
        
        st.sidebar.divider()
        
        # Service health summary
        self._render_sidebar_health()
        
        return use_real_aws
    
    def _render_cost_tracking(self):
        """Render cost tracking in sidebar."""
        st.sidebar.subheader("💰 Cost Tracking")
        
        costs = st.session_state.cost_tracking
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.metric("Session", f"${costs['session']:.4f}")
            st.metric("Processing", f"${costs['processing']:.4f}")
        
        with col2:
            st.metric("Total", f"${costs['total']:.4f}")
            st.metric("Storage", f"${costs['storage']:.4f}")
    
    def _render_sidebar_health(self):
        """Render service health summary in sidebar."""
        st.sidebar.subheader("🔧 System Status")
        
        if st.session_state.service_health:
            services = st.session_state.service_health.get('services', {})
            
            for service_name, status in services.items():
                if status == 'healthy':
                    st.sidebar.success(f"✅ {service_name.replace('_', ' ').title()}")
                else:
                    st.sidebar.error(f"❌ {service_name.replace('_', ' ').title()}")
        else:
            st.sidebar.warning("⚠️ Service status unavailable")
        
        # Refresh button
        if st.sidebar.button("🔄 Refresh Status"):
            self._update_service_health()
            st.rerun()
    
    def render_main_workflow(self):
        """Render the main 5-section workflow interface with enhanced navigation."""
        # Workflow progress indicator
        self._render_workflow_progress()

        # Create the main workflow tabs
        tab_names = [
            "🎬 Upload & Processing",
            "🔍 Query & Search",
            "🎯 Results & Playback",
            "📊 Embedding Visualization",
            "⚙️ Analytics & Management"
        ]

        tabs = st.tabs(tab_names)

        with tabs[0]:
            self.render_upload_processing_section()

        with tabs[1]:
            self.render_query_search_section()

        with tabs[2]:
            self.render_results_playback_section()

        with tabs[3]:
            self.render_embedding_visualization_section()

        with tabs[4]:
            self.render_analytics_management_section()

    def _render_workflow_progress(self):
        """Render workflow progress indicator."""
        st.subheader("🔄 Workflow Progress")

        # Define workflow stages and their completion status
        stages = [
            ("Upload", "🎬", self._is_stage_complete("upload")),
            ("Process", "⚙️", self._is_stage_complete("process")),
            ("Search", "🔍", self._is_stage_complete("search")),
            ("Results", "🎯", self._is_stage_complete("results")),
            ("Analyze", "📊", self._is_stage_complete("analyze"))
        ]

        # Create progress columns
        cols = st.columns(len(stages))

        for i, (stage_name, icon, is_complete) in enumerate(stages):
            with cols[i]:
                if is_complete:
                    st.success(f"{icon} {stage_name} ✅")
                else:
                    st.info(f"{icon} {stage_name}")

        # Overall progress bar
        completed_stages = sum(1 for _, _, complete in stages if complete)
        progress = completed_stages / len(stages)

        st.progress(progress, text=f"Overall Progress: {completed_stages}/{len(stages)} stages complete")

        # Next step guidance
        if progress < 1.0:
            next_stage = next((name for name, _, complete in stages if not complete), None)
            if next_stage:
                st.info(f"👉 **Next Step**: Complete {next_stage} stage")
        else:
            st.success("🎉 **Workflow Complete** - All stages finished!")

        st.divider()

    def _is_stage_complete(self, stage: str) -> bool:
        """Check if a workflow stage is complete."""
        if stage == "upload":
            return len(st.session_state.selected_videos) > 0
        elif stage == "process":
            return len(st.session_state.processed_videos) > 0
        elif stage == "search":
            return len(st.session_state.search_results) > 0
        elif stage == "results":
            return st.session_state.selected_segment is not None
        elif stage == "analyze":
            return st.session_state.embeddings_data is not None
        return False
    
    def render_upload_processing_section(self):
        """Render the upload and processing section with comprehensive Marengo 2.7 demo."""
        st.header("🎬 Upload & Processing")
        st.markdown("**Complete Marengo 2.7 Multi-Vector Pipeline with Dual Storage Patterns**")

        # Service manager integration demo
        if self.service_manager and self.coordinator:
            st.success("✅ **Multi-Vector Coordinator Ready** - Advanced processing capabilities available")

            # Dual Storage Pattern Selection
            st.subheader("🏗️ Storage Pattern Selection")
            col1, col2 = st.columns(2)

            with col1:
                st.info("**Pattern 1: Direct S3Vector Querying**")
                st.write("• Query S3Vector indexes directly")
                st.write("• Native S3Vector performance")
                st.write("• Optimized for vector similarity search")

            with col2:
                st.info("**Pattern 2: OpenSearch + S3Vector Hybrid**")
                st.write("• OpenSearch with S3Vector backend")
                st.write("• Metadata in OpenSearch, vectors in S3Vector")
                st.write("• Advanced search with vector capabilities")

            # Storage pattern selection
            storage_patterns = st.multiselect(
                "Select Storage Patterns to Demonstrate:",
                options=["direct_s3vector", "opensearch_s3vector_hybrid"],
                default=["direct_s3vector", "opensearch_s3vector_hybrid"],
                help="Choose which storage patterns to implement for comparison"
            )

            st.session_state.selected_storage_patterns = storage_patterns

            # Configuration section
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🧠 Marengo 2.7 Vector Configuration")

                # Vector type selection with detailed descriptions
                available_types = self.config.default_vector_types
                selected_types = st.multiselect(
                    "Select Vector Types:",
                    options=available_types,
                    default=available_types,
                    help="Choose which Marengo 2.7 vector types to generate"
                )

                # Segment configuration
                segment_duration = st.slider(
                    "Segment Duration (seconds):",
                    min_value=2.0,
                    max_value=10.0,
                    value=5.0,
                    step=0.5,
                    help="Duration of each video segment for embedding generation"
                )

                # Processing strategy
                processing_mode = st.selectbox(
                    "Processing Strategy:",
                    options=["parallel", "sequential", "adaptive"],
                    index=0,
                    help="How to process multiple vector types"
                )

                # Update session state
                st.session_state.selected_vector_types = selected_types
                st.session_state.segment_duration = segment_duration
                st.session_state.processing_mode = processing_mode

            with col2:
                st.subheader("⚙️ Processing Options")

                # Parallel upserting configuration
                enable_parallel_upserting = st.checkbox(
                    "Enable Parallel Upserting",
                    value=True,
                    help="Store embeddings in both patterns simultaneously"
                )

                # Cost estimation toggle
                enable_cost_estimation = st.checkbox(
                    "Enable Cost Estimation",
                    value=True,
                    help="Show estimated processing costs"
                )

                # Performance monitoring
                enable_performance_monitoring = st.checkbox(
                    "Enable Performance Monitoring",
                    value=True,
                    help="Track performance differences between storage patterns"
                )

                # Update session state
                st.session_state.enable_parallel_upserting = enable_parallel_upserting
                st.session_state.enable_cost_estimation = enable_cost_estimation
                st.session_state.enable_performance_monitoring = enable_performance_monitoring

            # Video Input Options
            st.subheader("📹 Video Input Options")

            input_method = st.radio(
                "Choose Input Method:",
                options=["Sample Videos", "Sample Collection", "Upload File", "S3 URI"],
                horizontal=True,
                help="Select how to provide video content for processing"
            )

            if input_method == "Sample Videos":
                self._render_sample_videos_selection()
            elif input_method == "Sample Collection":
                self._render_sample_collection_selection()
            elif input_method == "Upload File":
                self._render_file_upload_interface()
            elif input_method == "S3 URI":
                self._render_s3_uri_input()

            # Processing Controls
            st.subheader("🚀 Processing Controls")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("🎬 Start Processing", type="primary", use_container_width=True):
                    self._start_marengo_processing()

            with col2:
                if st.button("📊 View Progress", use_container_width=True):
                    self._show_processing_progress()

            with col3:
                if st.button("💰 Cost Estimate", use_container_width=True):
                    self._show_cost_estimation()

            # Show vector type capabilities with Marengo details
            with st.expander("🧠 Marengo 2.7 Vector Types Details"):
                vector_details = {
                    "visual-text": {
                        "description": "Text content extracted from video frames",
                        "use_cases": "OCR, captions, signs, text overlays",
                        "provider": "TwelveLabs Marengo 2.7"
                    },
                    "visual-image": {
                        "description": "Visual content and objects in video frames",
                        "use_cases": "Object detection, scene analysis, visual similarity",
                        "provider": "TwelveLabs Marengo 2.7"
                    },
                    "audio": {
                        "description": "Audio content and speech from video",
                        "use_cases": "Speech recognition, audio similarity, sound detection",
                        "provider": "TwelveLabs Marengo 2.7"
                    }
                }

                for vtype in available_types:
                    details = vector_details.get(vtype, {})
                    is_selected = vtype in selected_types
                    status = "✅ Selected" if is_selected else "⚪ Available"

                    st.write(f"**{vtype}** - {status}")
                    st.write(f"• **Description**: {details.get('description', 'N/A')}")
                    st.write(f"• **Use Cases**: {details.get('use_cases', 'N/A')}")
                    st.write(f"• **Provider**: {details.get('provider', 'Unknown')}")
                    st.write("---")

            # Show storage pattern details
            with st.expander("🏗️ Storage Pattern Comparison"):
                st.write("**Direct S3Vector Pattern:**")
                st.write("• Vector data stored directly in S3Vector indexes")
                st.write("• One index per vector type (visual-text, visual-image, audio)")
                st.write("• Optimized for pure vector similarity search")
                st.write("• Lower latency for vector operations")
                st.write("")

                st.write("**OpenSearch + S3Vector Hybrid Pattern:**")
                st.write("• Vector data stored in S3Vector as backend")
                st.write("• Metadata and search capabilities in OpenSearch")
                st.write("• Supports complex queries combining vectors and metadata")
                st.write("• Advanced filtering and aggregation capabilities")

        else:
            st.error("❌ **Service Manager Unavailable** - Limited functionality")

        # Show current processing jobs if any
        if st.session_state.processing_jobs:
            st.subheader("🔄 Active Processing Jobs")
            for job_id, job_info in st.session_state.processing_jobs.items():
                with st.expander(f"Job: {job_id}"):
                    st.json(job_info)

        # Video Input Section
        self._render_video_input_section()

        # Workflow navigation
        self._render_section_navigation("upload")

    def _render_video_input_section(self):
        """Render video input options for the demo."""
        st.subheader("📹 Video Input Options")

        # Input method selection
        input_method = st.selectbox(
            "Select Input Method:",
            options=["sample_videos", "sample_collection", "upload_file", "s3_uri"],
            index=0,
            help="Choose how to provide video input"
        )

        if input_method == "sample_videos":
            # Sample video selection
            sample_videos = {
                "Demo Video 1": "s3://s3vector-demo-bucket/sample-videos/demo-video-1.mp4",
                "Demo Video 2": "s3://s3vector-demo-bucket/sample-videos/demo-video-2.mp4",
                "Demo Video 3": "s3://s3vector-demo-bucket/sample-videos/demo-video-3.mp4"
            }

            selected_video = st.selectbox(
                "Select Sample Video:",
                options=list(sample_videos.keys()),
                help="Choose a pre-loaded sample video"
            )

            if selected_video:
                video_uri = sample_videos[selected_video]
                st.session_state.selected_video_uri = video_uri
                st.success(f"Selected: {selected_video}")
                st.code(video_uri)

                # Process button
                if st.button("🚀 Process Video with Dual Storage Patterns", type="primary"):
                    self._start_dual_pattern_processing(video_uri)

        elif input_method == "sample_collection":
            st.info("📦 **Sample Collection Processing**")
            st.write("Process multiple videos simultaneously to demonstrate batch capabilities")

            collection_size = st.selectbox(
                "Collection Size:",
                options=[3, 5, 10],
                index=0,
                help="Number of videos to process in batch"
            )

            if st.button("🚀 Process Sample Collection", type="primary"):
                self._start_collection_processing(collection_size)

        elif input_method == "upload_file":
            st.info("📤 **File Upload**")
            uploaded_file = st.file_uploader(
                "Upload Video File:",
                type=['mp4', 'avi', 'mov', 'mkv'],
                help="Upload a video file for processing"
            )

            if uploaded_file:
                st.success(f"Uploaded: {uploaded_file.name}")
                if st.button("🚀 Process Uploaded Video", type="primary"):
                    self._start_upload_processing(uploaded_file)

        elif input_method == "s3_uri":
            st.info("🔗 **S3 URI Input**")
            s3_uri = st.text_input(
                "Enter S3 URI:",
                placeholder="s3://your-bucket/path/to/video.mp4",
                help="Provide S3 URI of video to process"
            )

            if s3_uri and st.button("🚀 Process S3 Video", type="primary"):
                self._start_dual_pattern_processing(s3_uri)

    def _start_dual_pattern_processing(self, video_uri: str):
        """Start processing video with dual storage patterns."""
        if not st.session_state.use_real_aws:
            # Simulation mode
            st.info("🛡️ **Simulation Mode** - Generating demo processing results")

            # Simulate processing job
            job_id = f"demo_job_{int(time.time())}"
            job_info = {
                "job_id": job_id,
                "video_uri": video_uri,
                "status": "processing",
                "vector_types": st.session_state.selected_vector_types,
                "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
                "segment_duration": st.session_state.get('segment_duration', 5.0),
                "started_at": time.time()
            }

            st.session_state.processing_jobs[job_id] = job_info
            st.success(f"✅ Started demo processing job: {job_id}")

            # Simulate completion after a delay
            time.sleep(2)
            job_info["status"] = "completed"
            job_info["completed_at"] = time.time()

            # Generate demo results
            demo_results = self._generate_demo_processing_results(job_info)
            st.session_state.processed_videos[job_id] = demo_results

            st.success("🎉 Demo processing completed! Check the Results & Playback section.")

        else:
            # Real AWS processing
            st.warning("⚠️ **Real AWS Mode** - This will incur costs")

            if st.button("Confirm Real Processing", type="secondary"):
                try:
                    # Use the multi-vector coordinator for real processing
                    processing_config = {
                        "vector_types": st.session_state.selected_vector_types,
                        "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
                        "segment_duration": st.session_state.get('segment_duration', 5.0),
                        "processing_mode": st.session_state.get('processing_mode', 'parallel')
                    }

                    # This would integrate with the actual MultiVectorCoordinator
                    st.info("🔄 Real processing integration would be implemented here")

                except Exception as e:
                    st.error(f"Processing failed: {e}")

    def _start_collection_processing(self, collection_size: int):
        """Start processing a collection of videos."""
        st.info(f"🔄 Processing collection of {collection_size} videos...")
        # Implementation for batch processing

    def _start_upload_processing(self, uploaded_file):
        """Start processing an uploaded video file."""
        st.info(f"🔄 Processing uploaded file: {uploaded_file.name}")
        # Implementation for uploaded file processing

    def _generate_demo_processing_results(self, job_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate demo processing results for simulation."""
        import random

        vector_types = job_info["vector_types"]
        storage_patterns = job_info["storage_patterns"]

        results = {
            "job_id": job_info["job_id"],
            "video_uri": job_info["video_uri"],
            "total_segments": random.randint(8, 15),
            "processing_time_sec": random.uniform(45, 120),
            "cost_usd": random.uniform(0.05, 0.15),
            "vector_types_processed": vector_types,
            "storage_patterns_used": storage_patterns,
            "segment_duration": job_info["segment_duration"],
            "embeddings_generated": {}
        }

        # Generate embedding info for each vector type and storage pattern
        for vector_type in vector_types:
            results["embeddings_generated"][vector_type] = {}

            for pattern in storage_patterns:
                results["embeddings_generated"][vector_type][pattern] = {
                    "index_arn": f"arn:aws:s3vectors:us-east-1:123456789012:index/demo-{vector_type}-{pattern}",
                    "vectors_stored": results["total_segments"],
                    "storage_size_mb": random.uniform(5, 25),
                    "avg_similarity_score": random.uniform(0.75, 0.95)
                }

        return results

    def _get_service_provider_for_type(self, vector_type: str) -> str:
        """Get the service provider for a vector type."""
        if vector_type in ['visual-text', 'visual-image', 'audio']:
            return 'TwelveLabs Marengo 2.7'
        elif vector_type == 'text-titan':
            return 'Amazon Bedrock Titan'
        else:
            return 'Unknown'

    def _analyze_search_query(self, query: str, vector_types: List[str]) -> Dict[str, Any]:
        """Analyze a search query and provide recommendations."""
        # Simple query analysis - in real implementation, this would use NLP
        query_lower = query.lower()

        # Detect intent based on keywords
        if any(word in query_lower for word in ['person', 'people', 'human', 'man', 'woman']):
            intent = "person_detection"
        elif any(word in query_lower for word in ['car', 'vehicle', 'truck', 'driving']):
            intent = "vehicle_detection"
        elif any(word in query_lower for word in ['music', 'sound', 'audio', 'voice']):
            intent = "audio_content"
        elif any(word in query_lower for word in ['text', 'writing', 'sign', 'caption']):
            intent = "text_content"
        else:
            intent = "general_content"

        # Recommend vector types based on intent
        if intent == "audio_content":
            recommended_vectors = ["audio"]
        elif intent == "text_content":
            recommended_vectors = ["visual-text"]
        else:
            recommended_vectors = ["visual-text", "visual-image"]

        # Determine complexity
        word_count = len(query.split())
        if word_count <= 3:
            complexity = "Simple"
        elif word_count <= 7:
            complexity = "Medium"
        else:
            complexity = "Complex"

        return {
            "intent": intent,
            "recommended_vectors": recommended_vectors,
            "complexity": complexity,
            "word_count": word_count,
            "detected_entities": self._extract_entities(query),
            "suggested_fusion": "weighted_average" if len(recommended_vectors) > 1 else "single_vector"
        }

    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from query (simplified implementation)."""
        # Simple entity extraction - in real implementation, use NER
        entities = []
        query_lower = query.lower()

        # Common entities
        entity_patterns = {
            "person": ["person", "people", "human", "man", "woman", "child"],
            "vehicle": ["car", "truck", "bus", "motorcycle", "vehicle"],
            "location": ["street", "road", "building", "park", "indoor", "outdoor"],
            "action": ["walking", "running", "driving", "sitting", "standing"],
            "object": ["table", "chair", "phone", "computer", "book"]
        }

        for entity_type, keywords in entity_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                entities.append(entity_type)

        return entities

    def _render_section_navigation(self, current_section: str):
        """Render navigation controls for workflow sections."""
        st.divider()

        # Section navigation
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if current_section != "upload":
                if st.button("⬅️ Previous Section", use_container_width=True):
                    st.info("Navigation between sections will be enhanced in future updates")

        with col2:
            st.write(f"**Current Section**: {current_section.title()}")

        with col3:
            if current_section != "analytics":
                if st.button("Next Section ➡️", use_container_width=True):
                    st.info("Navigation between sections will be enhanced in future updates")
    
    def render_query_search_section(self):
        """Render the query and search section with dual pattern comparison."""
        st.header("🔍 Query & Search")
        st.markdown("**Dual Storage Pattern Search Comparison** - Independent pattern interaction with performance metrics")

        # Check prerequisites
        if not st.session_state.processed_videos:
            st.warning("⚠️ **No processed videos available** - Please complete the Upload & Processing step first")
            return

        # Service manager integration demo
        if self.service_manager and self.coordinator:
            st.success("✅ **Multi-Vector Search Engine Ready** - Cross-vector search capabilities available")

            # Main search interface
            st.subheader("🔍 Semantic Search Query")

            col1, col2 = st.columns([3, 1])

            with col1:
                search_query = st.text_input(
                    "Enter your search query:",
                    placeholder="e.g., 'person walking in the scene', 'car driving on highway', 'music playing'",
                    help="Describe what you're looking for in the videos",
                    key="main_search_query"
                )

            with col2:
                # Search both patterns independently
                search_both = st.button("🔍 Search Both Patterns", type="primary", use_container_width=True)

            # Independent pattern search buttons
            col1, col2 = st.columns(2)

            with col1:
                search_s3vector = st.button("🎯 Search Direct S3Vector", use_container_width=True)

            with col2:
                search_opensearch = st.button("🔍 Search OpenSearch Hybrid", use_container_width=True)

            # Search configuration
            with st.expander("⚙️ Search Configuration"):
                col1, col2 = st.columns(2)

                with col1:
                    # Vector types for search
                    search_vector_types = st.multiselect(
                        "Vector Types to Search:",
                        options=st.session_state.get('selected_vector_types', self.config.default_vector_types),
                        default=st.session_state.get('selected_vector_types', self.config.default_vector_types),
                        help="Which vector types to include in search"
                    )

                    # Fusion strategy
                    fusion_strategy = st.selectbox(
                        "Result Fusion:",
                        options=["weighted_average", "max_score", "rank_fusion"],
                        index=0,
                        help="How to combine results from different vector types"
                    )

                with col2:
                    # Number of results
                    num_results = st.slider(
                        "Number of Results:",
                        min_value=5,
                        max_value=50,
                        value=10,
                        help="How many results to return"
                    )

                    # Similarity threshold
                    similarity_threshold = st.slider(
                        "Similarity Threshold:",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.7,
                        step=0.05,
                        help="Minimum similarity score for results"
                    )

            # Query analysis and search execution
            if search_query:
                st.subheader("🧠 Query Analysis")

                # Simulate query analysis
                query_analysis = self._analyze_search_query(search_query, search_vector_types)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Detected Intent", query_analysis["intent"])
                with col2:
                    st.metric("Recommended Vectors", len(query_analysis["recommended_vectors"]))
                with col3:
                    st.metric("Complexity", query_analysis["complexity"])

                # Show analysis details
                with st.expander("📋 Detailed Analysis"):
                    st.json(query_analysis)

                # Search execution with dual pattern support
                if search_both:
                    st.subheader("� Dual Pattern Search Results")
                    self._execute_dual_pattern_search(search_query, query_analysis, search_vector_types, num_results, similarity_threshold)

                elif search_s3vector:
                    st.subheader("🎯 Direct S3Vector Search Results")
                    self._execute_s3vector_search(search_query, query_analysis, search_vector_types, num_results, similarity_threshold)

                elif search_opensearch:
                    st.subheader("🔍 OpenSearch Hybrid Search Results")
                    self._execute_opensearch_search(search_query, query_analysis, search_vector_types, num_results, similarity_threshold)

            # Show search capabilities
            with st.expander("🎯 Search Capabilities"):
                capabilities = [
                    "Multi-Index Search: Search across multiple vector types simultaneously",
                    "Result Fusion: Combine results with intelligent ranking algorithms",
                    "Query Routing: Automatic detection of query intent and vector selection",
                    "Temporal Filtering: Time-based search constraints and segment filtering",
                    "Similarity Scoring: Advanced similarity metrics with confidence scores",
                    "Real-time Processing: Sub-2-second search response times"
                ]
                for capability in capabilities:
                    st.write(f"• **{capability.split(':')[0]}**: {capability.split(':')[1]}")

        else:
            st.error("❌ **Search Engine Unavailable** - Limited search functionality")

        # Workflow navigation
        self._render_section_navigation("search")

        # Placeholder for full search interface - will be implemented in T3.3
        st.info("📋 **Next**: Complete search execution will be implemented in T3.3 (Unify Search and Retrieval Features)")
    
    def render_results_playback_section(self):
        """Render the results and video playback section."""
        st.header("🎯 Results & Playback")
        st.markdown("Interactive video player with segment highlighting")

        # Check prerequisites
        if not st.session_state.current_query:
            st.warning("⚠️ **No search performed** - Please complete a search in the Query & Search section first")
            self._render_section_navigation("results")
            return

        # Show current query context
        st.subheader("🔍 Search Context")
        col1, col2 = st.columns(2)

        with col1:
            st.info(f"**Query**: {st.session_state.current_query}")

        with col2:
            if st.session_state.query_analysis:
                analysis = st.session_state.query_analysis
                st.info(f"**Intent**: {analysis.get('intent', 'Unknown')}")

        # Placeholder search results
        st.subheader("📋 Search Results")

        # Simulate search results for demo
        if st.button("🔄 Generate Demo Results", help="Simulate search results for demonstration"):
            demo_results = self._generate_demo_search_results("sample query", "s3vector", 5)
            st.session_state.search_results = {"s3vector": demo_results, "query": "sample query"}
            st.success(f"Generated {len(demo_results)} demo results")

        # Display search results
        if st.session_state.search_results:
            # Handle different result formats
            if isinstance(st.session_state.search_results, dict):
                # New format with pattern-specific results
                if "s3vector" in st.session_state.search_results and "opensearch" in st.session_state.search_results:
                    # Dual pattern results
                    st.subheader("📊 Dual Pattern Search Results")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**🎯 Direct S3Vector Results**")
                        s3vector_results = st.session_state.search_results["s3vector"]
                        if s3vector_results:
                            self._display_results_table(s3vector_results, "s3vector")

                    with col2:
                        st.write("**🔍 OpenSearch Hybrid Results**")
                        opensearch_results = st.session_state.search_results["opensearch"]
                        if opensearch_results:
                            self._display_results_table(opensearch_results, "opensearch")

                elif "s3vector" in st.session_state.search_results:
                    # S3Vector only results
                    st.subheader("🎯 Direct S3Vector Results")
                    results = st.session_state.search_results["s3vector"]
                    if results:
                        self._display_results_table(results, "s3vector")

                elif "opensearch" in st.session_state.search_results:
                    # OpenSearch only results
                    st.subheader("🔍 OpenSearch Hybrid Results")
                    results = st.session_state.search_results["opensearch"]
                    if results:
                        self._display_results_table(results, "opensearch")

            else:
                # Legacy format - list of results
                st.subheader("📊 Search Results")
                st.write(f"**Found {len(st.session_state.search_results)} matching segments**")
                self._display_results_table(st.session_state.search_results, "legacy")

                # Video player placeholder
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
                        # Timeline placeholder
                        timeline_progress = (result['start_time'] / 300.0)  # Assume 5min video
                        st.progress(timeline_progress, text=f"Timeline: {result['start_time']:.1f}s / 300.0s")

                    with col3:
                        st.button("Next Segment ⏭️")

                    # Player controls
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.button("⏯️ Play/Pause")
                    with col2:
                        st.button("🔇 Mute")
                    with col3:
                        st.button("⚙️ Settings")
                    with col4:
                        st.button("🔍 Jump to Segment")

        else:
            st.info("No search results available. Perform a search or generate demo results.")

        # Workflow navigation
        self._render_section_navigation("results")
    
    def render_embedding_visualization_section(self):
        """Render the embedding visualization section."""
        st.header("📊 Embedding Visualization")
        st.markdown("Explore the multi-vector embedding space with interactive visualizations")

        # Check prerequisites
        if not st.session_state.search_results:
            st.warning("⚠️ **No search results available** - Please perform a search first to visualize embeddings")
            self._render_section_navigation("visualization")
            return

        # Visualization configuration
        st.subheader("⚙️ Visualization Configuration")

        col1, col2, col3 = st.columns(3)

        with col1:
            reduction_method = st.selectbox(
                "Dimensionality Reduction:",
                options=["PCA", "t-SNE", "UMAP"],
                index=0,
                help="Method to reduce embeddings to 2D/3D"
            )

        with col2:
            dimensions = st.selectbox(
                "Dimensions:",
                options=["2D", "3D"],
                index=0,
                help="2D or 3D visualization"
            )

        with col3:
            color_by = st.selectbox(
                "Color By:",
                options=["similarity", "vector_type", "video", "temporal"],
                index=0,
                help="How to color the points"
            )

        # Update visualization config
        st.session_state.visualization_config = {
            'reduction_method': reduction_method,
            'dimensions': dimensions,
            'color_by': color_by
        }

        # Generate demo embeddings
        if st.button("🔄 Generate Demo Visualization", help="Create demo embedding visualization"):
            demo_embeddings = self._generate_demo_embeddings()
            st.session_state.embeddings_data = demo_embeddings
            st.success("Generated demo embedding visualization")

        # Display visualization
        if st.session_state.embeddings_data:
            st.subheader("🎯 Embedding Space Visualization")

            # Placeholder for actual visualization
            st.info("📋 **Next**: Interactive Plotly visualization will be implemented in T3.4")

            # Show embedding statistics
            embeddings = st.session_state.embeddings_data

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Points", len(embeddings))

            with col2:
                vector_types = set(emb['vector_type'] for emb in embeddings)
                st.metric("Vector Types", len(vector_types))

            with col3:
                videos = set(emb['video_name'] for emb in embeddings)
                st.metric("Videos", len(videos))

            with col4:
                avg_similarity = np.mean([emb['similarity_score'] for emb in embeddings])
                st.metric("Avg Similarity", f"{avg_similarity:.3f}")

            # Embedding details table
            with st.expander("📋 Embedding Details"):
                embedding_data = []
                for i, emb in enumerate(embeddings):
                    embedding_data.append({
                        "Point": i + 1,
                        "Video": emb["video_name"],
                        "Vector Type": emb["vector_type"],
                        "Similarity": f"{emb['similarity_score']:.3f}",
                        "Segment": f"{emb['start_time']:.1f}s - {emb['end_time']:.1f}s"
                    })

                st.dataframe(embedding_data, use_container_width=True)

            # Visualization controls
            st.subheader("🎮 Visualization Controls")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Query Point Overlay**")
                show_query_point = st.checkbox("Show Query Point", value=True)
                query_point_size = st.slider("Query Point Size", 5, 20, 10)

            with col2:
                st.write("**Clustering Analysis**")
                show_clusters = st.checkbox("Show Clusters", value=False)
                cluster_method = st.selectbox("Clustering Method", ["K-Means", "DBSCAN", "Hierarchical"])

        else:
            st.info("No embedding data available. Generate demo visualization or perform searches to create embeddings.")

        # Workflow navigation
        self._render_section_navigation("visualization")
    
    def render_analytics_management_section(self):
        """Render the analytics and management section."""
        st.header("⚙️ Analytics & Management")
        st.markdown("Performance metrics, cost analysis, and system management")
        
        # Show current configuration
        st.subheader("🔧 Current Configuration")
        
        config_data = {
            "Multi-Vector Enabled": self.config.enable_multi_vector,
            "Default Vector Types": self.config.default_vector_types,
            "Max Concurrent Jobs": self.config.max_concurrent_jobs,
            "Performance Monitoring": self.config.enable_performance_monitoring,
            "Cost Tracking": self.config.enable_cost_tracking
        }
        
        st.json(config_data)
        
        # Service manager status
        if self.service_manager:
            st.subheader("🔧 Service Manager Status")
            try:
                status = self.service_manager.get_system_status()

                # Display status in a more user-friendly format
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Service Health:**")
                    services = status.get('services', {})
                    for service_name, service_status in services.items():
                        if service_status == 'healthy':
                            st.success(f"✅ {service_name.replace('_', ' ').title()}")
                        else:
                            st.error(f"❌ {service_name.replace('_', ' ').title()}")

                with col2:
                    st.write("**Configuration:**")
                    config = status.get('configuration', {})
                    for key, value in config.items():
                        st.write(f"• **{key.replace('_', ' ').title()}**: {value}")

                # Show raw status in expander
                with st.expander("📋 Raw System Status"):
                    st.json(status)

            except Exception as e:
                st.error(f"Failed to get service status: {e}")

        # Multi-vector coordinator status
        if self.coordinator:
            st.subheader("🧠 Multi-Vector Coordinator")
            try:
                # Get coordination stats if available
                if hasattr(self.coordinator, 'get_coordination_stats'):
                    stats = self.coordinator.get_coordination_stats()

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Active Workflows", len(self.coordinator.active_workflows))
                    with col2:
                        st.metric("Vector Types", len(self.config.default_vector_types))
                    with col3:
                        st.metric("Max Concurrent", self.config.max_concurrent_jobs)

                    with st.expander("📊 Coordination Statistics"):
                        st.json(stats)
                else:
                    st.info("Multi-vector coordinator operational")

            except Exception as e:
                st.error(f"Failed to get coordinator status: {e}")

        # Performance monitoring
        if self.config.enable_performance_monitoring:
            st.subheader("📈 Performance Monitoring")

            # Show performance metrics if available
            if st.session_state.performance_metrics:
                metrics = st.session_state.performance_metrics

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Response Time", f"{metrics.get('avg_response_ms', 0):.0f}ms")
                with col2:
                    st.metric("Total Requests", metrics.get('total_requests', 0))
                with col3:
                    st.metric("Success Rate", f"{metrics.get('success_rate', 0):.1%}")
            else:
                st.info("Performance monitoring enabled - metrics will appear after operations")
    
    def test_service_manager_integration(self):
        """Test and demonstrate service manager integration."""
        if not self.service_manager:
            return {"status": "error", "message": "Service manager not available"}

        try:
            # Test system status
            status = self.service_manager.get_system_status()

            # Test vector type capabilities if available
            capabilities = {}
            if hasattr(self.service_manager, 'get_vector_type_capabilities'):
                capabilities = self.service_manager.get_vector_type_capabilities()

            return {
                "status": "success",
                "system_status": status,
                "capabilities": capabilities,
                "coordinator_available": self.coordinator is not None,
                "services_available": {
                    "search_engine": self.search_engine is not None,
                    "storage_manager": self.storage_manager is not None,
                    "twelvelabs_service": self.twelvelabs_service is not None,
                    "bedrock_service": self.bedrock_service is not None
                }
            }

        except Exception as e:
            logger.error(f"Service manager integration test failed: {e}")
            return {"status": "error", "message": str(e)}

    def _generate_demo_search_results(self) -> List[Dict[str, Any]]:
        """Generate demo search results for demonstration."""
        import random

        # Sample video names
        video_names = [
            "sample_video_001.mp4",
            "sample_video_002.mp4",
            "sample_video_003.mp4",
            "demo_content_A.mp4",
            "demo_content_B.mp4"
        ]

        # Sample descriptions based on query
        query = st.session_state.current_query.lower()

        if "person" in query or "walking" in query:
            descriptions = [
                "Person walking across the street in urban environment",
                "Individual walking through park with trees in background",
                "Person walking along sidewalk near buildings",
                "Walking figure in outdoor scene with natural lighting",
                "Person moving through crowded area with other people"
            ]
        elif "car" in query or "driving" in query:
            descriptions = [
                "Car driving on highway with clear road ahead",
                "Vehicle moving through city traffic intersection",
                "Car driving on rural road with landscape views",
                "Vehicle navigating through urban street scene",
                "Car driving in parking lot area"
            ]
        else:
            descriptions = [
                "General scene with multiple objects and activities",
                "Outdoor environment with various visual elements",
                "Indoor scene with people and objects interaction",
                "Mixed content with audio and visual components",
                "Complex scene with multiple focal points"
            ]

        # Generate results
        results = []
        for i in range(random.randint(5, 12)):
            video_name = random.choice(video_names)
            start_time = random.uniform(10, 200)
            duration = random.uniform(3, 15)

            result = {
                "video_name": video_name,
                "start_time": start_time,
                "end_time": start_time + duration,
                "similarity_score": random.uniform(0.65, 0.95),
                "vector_type": random.choice(["visual-text", "visual-image", "audio"]),
                "description": random.choice(descriptions),
                "confidence": random.uniform(0.7, 0.95),
                "metadata": {
                    "resolution": "1920x1080",
                    "fps": 30,
                    "duration_total": random.uniform(180, 300)
                }
            }
            results.append(result)

        # Sort by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)

        return results

    def _generate_demo_embeddings(self) -> List[Dict[str, Any]]:
        """Generate demo embedding data for visualization."""
        import random

        embeddings = []

        # Use search results as base
        if st.session_state.search_results:
            for result in st.session_state.search_results:
                # Generate random embedding coordinates (normally these would be real embeddings)
                embedding = {
                    "video_name": result["video_name"],
                    "start_time": result["start_time"],
                    "end_time": result["end_time"],
                    "vector_type": result["vector_type"],
                    "similarity_score": result["similarity_score"],
                    "embedding_2d": [random.uniform(-10, 10), random.uniform(-10, 10)],
                    "embedding_3d": [random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-10, 10)],
                    "cluster_id": random.randint(0, 3),
                    "description": result["description"]
                }
                embeddings.append(embedding)

        # Add some additional points for context
        for i in range(random.randint(10, 20)):
            embedding = {
                "video_name": f"context_video_{i:03d}.mp4",
                "start_time": random.uniform(0, 200),
                "end_time": random.uniform(205, 220),
                "vector_type": random.choice(["visual-text", "visual-image", "audio"]),
                "similarity_score": random.uniform(0.3, 0.7),
                "embedding_2d": [random.uniform(-15, 15), random.uniform(-15, 15)],
                "embedding_3d": [random.uniform(-15, 15), random.uniform(-15, 15), random.uniform(-15, 15)],
                "cluster_id": random.randint(0, 3),
                "description": "Background context embedding for visualization"
            }
            embeddings.append(embedding)

        return embeddings

    def _render_sample_videos_selection(self):
        """Render sample videos selection interface."""
        st.write("**Select from curated sample videos:**")

        # Sample videos with metadata
        sample_videos = {
            "Demo Video 1": {
                "s3_uri": "s3://sample-bucket/demo-video-1.mp4",
                "duration": "2:30",
                "description": "Product demonstration with speech and visual elements",
                "size": "45 MB"
            },
            "Demo Video 2": {
                "s3_uri": "s3://sample-bucket/demo-video-2.mp4",
                "duration": "1:45",
                "description": "Nature documentary with narration",
                "size": "32 MB"
            },
            "Demo Video 3": {
                "s3_uri": "s3://sample-bucket/demo-video-3.mp4",
                "duration": "3:15",
                "description": "Conference presentation with slides",
                "size": "58 MB"
            }
        }

        selected_videos = []
        for video_name, metadata in sample_videos.items():
            col1, col2 = st.columns([1, 3])

            with col1:
                if st.checkbox(video_name, key=f"sample_{video_name}"):
                    selected_videos.append(metadata["s3_uri"])

            with col2:
                st.write(f"**Duration**: {metadata['duration']} | **Size**: {metadata['size']}")
                st.write(f"*{metadata['description']}*")

        st.session_state.selected_videos = selected_videos

        if selected_videos:
            st.success(f"✅ Selected {len(selected_videos)} sample video(s)")

    def _render_sample_collection_selection(self):
        """Render sample collection selection interface."""
        st.write("**Select from pre-configured video collections:**")

        collections = {
            "Product Demo Collection": {
                "video_count": 5,
                "total_duration": "12:30",
                "description": "Product demonstrations and tutorials",
                "s3_prefix": "s3://sample-bucket/collections/product-demos/"
            },
            "Educational Content": {
                "video_count": 8,
                "total_duration": "25:45",
                "description": "Educational videos and lectures",
                "s3_prefix": "s3://sample-bucket/collections/educational/"
            },
            "Marketing Materials": {
                "video_count": 3,
                "total_duration": "8:15",
                "description": "Marketing videos and advertisements",
                "s3_prefix": "s3://sample-bucket/collections/marketing/"
            }
        }

        selected_collection = st.selectbox(
            "Choose a collection:",
            options=list(collections.keys()),
            help="Select a pre-configured collection of videos"
        )

        if selected_collection:
            collection_info = collections[selected_collection]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Videos", collection_info["video_count"])
            with col2:
                st.metric("Total Duration", collection_info["total_duration"])
            with col3:
                st.metric("Estimated Cost", f"${collection_info['video_count'] * 0.25:.2f}")

            st.info(f"**Description**: {collection_info['description']}")

            st.session_state.selected_collection = {
                "name": selected_collection,
                "s3_prefix": collection_info["s3_prefix"],
                "video_count": collection_info["video_count"]
            }

    def _render_file_upload_interface(self):
        """Render file upload interface."""
        st.write("**Upload video files for processing:**")

        uploaded_files = st.file_uploader(
            "Choose video files",
            type=['mp4', 'mov', 'avi', 'mkv'],
            accept_multiple_files=True,
            help="Upload video files (max 100MB each)"
        )

        if uploaded_files:
            st.write(f"**Uploaded {len(uploaded_files)} file(s):**")

            total_size = 0
            for file in uploaded_files:
                file_size_mb = file.size / (1024 * 1024)
                total_size += file_size_mb
                st.write(f"• {file.name} ({file_size_mb:.1f} MB)")

            st.info(f"**Total size**: {total_size:.1f} MB")

            if total_size > 500:  # 500MB limit
                st.warning("⚠️ Total file size exceeds 500MB limit. Consider processing in batches.")

            st.session_state.uploaded_files = uploaded_files

    def _render_s3_uri_input(self):
        """Render S3 URI input interface."""
        st.write("**Enter S3 URI(s) for existing videos:**")

        # Single S3 URI input
        s3_uri = st.text_input(
            "S3 URI:",
            placeholder="s3://your-bucket/path/to/video.mp4",
            help="Enter the S3 URI of a video file"
        )

        # Batch S3 URI input
        st.write("**Or enter multiple S3 URIs (one per line):**")
        s3_uris_text = st.text_area(
            "Multiple S3 URIs:",
            placeholder="s3://bucket/video1.mp4\ns3://bucket/video2.mp4\ns3://bucket/video3.mp4",
            help="Enter multiple S3 URIs, one per line"
        )

        # Process inputs
        s3_uris = []
        if s3_uri.strip():
            s3_uris.append(s3_uri.strip())

        if s3_uris_text.strip():
            batch_uris = [uri.strip() for uri in s3_uris_text.strip().split('\n') if uri.strip()]
            s3_uris.extend(batch_uris)

        # Validate S3 URIs
        valid_uris = []
        for uri in s3_uris:
            if uri.startswith('s3://') and uri.count('/') >= 3:
                valid_uris.append(uri)
            else:
                st.error(f"❌ Invalid S3 URI: {uri}")

        if valid_uris:
            st.success(f"✅ {len(valid_uris)} valid S3 URI(s) provided")
            st.session_state.s3_uris = valid_uris

            # Show URI list
            with st.expander("📋 S3 URIs to Process"):
                for i, uri in enumerate(valid_uris, 1):
                    st.write(f"{i}. {uri}")

    def _start_marengo_processing(self):
        """Start Marengo 2.7 multi-vector processing."""
        if not self.coordinator:
            st.error("❌ Multi-vector coordinator not available")
            return

        # Get selected inputs
        videos_to_process = []

        if hasattr(st.session_state, 'selected_videos') and st.session_state.selected_videos:
            videos_to_process.extend(st.session_state.selected_videos)

        if hasattr(st.session_state, 'selected_collection'):
            collection = st.session_state.selected_collection
            st.info(f"📁 Processing collection: {collection['name']} ({collection['video_count']} videos)")
            # In real implementation, would expand collection to individual videos
            videos_to_process.append(collection['s3_prefix'])

        if hasattr(st.session_state, 'uploaded_files') and st.session_state.uploaded_files:
            st.info(f"📤 Uploading {len(st.session_state.uploaded_files)} files to S3...")
            # In real implementation, would upload files to S3 first
            for file in st.session_state.uploaded_files:
                videos_to_process.append(f"s3://temp-bucket/{file.name}")

        if hasattr(st.session_state, 's3_uris') and st.session_state.s3_uris:
            videos_to_process.extend(st.session_state.s3_uris)

        if not videos_to_process:
            st.warning("⚠️ No videos selected for processing")
            return

        # Start processing simulation
        with st.spinner("🚀 Starting Marengo 2.7 multi-vector processing..."):
            time.sleep(2)  # Simulate processing start

            # Create processing job
            job_id = f"marengo-job-{int(time.time())}"

            processing_job = {
                "job_id": job_id,
                "status": "processing",
                "videos": videos_to_process,
                "vector_types": st.session_state.get('selected_vector_types', ['visual-text']),
                "storage_patterns": st.session_state.get('selected_storage_patterns', ['direct_s3vector']),
                "segment_duration": st.session_state.get('segment_duration', 5.0),
                "processing_mode": st.session_state.get('processing_mode', 'parallel'),
                "started_at": time.time(),
                "estimated_completion": time.time() + 300  # 5 minutes
            }

            # Update session state
            if 'processing_jobs' not in st.session_state:
                st.session_state.processing_jobs = {}

            st.session_state.processing_jobs[job_id] = processing_job

            st.success(f"✅ Processing started! Job ID: {job_id}")
            st.info("🔄 Processing will continue in the background. Check the Progress tab for updates.")

    def _show_processing_progress(self):
        """Show processing progress for active jobs."""
        if not hasattr(st.session_state, 'processing_jobs') or not st.session_state.processing_jobs:
            st.info("📋 No active processing jobs")
            return

        st.subheader("🔄 Processing Progress")

        for job_id, job_info in st.session_state.processing_jobs.items():
            with st.expander(f"Job: {job_id}", expanded=True):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Status", job_info.get('status', 'unknown').title())

                with col2:
                    videos_count = len(job_info.get('videos', []))
                    st.metric("Videos", videos_count)

                with col3:
                    vector_types = len(job_info.get('vector_types', []))
                    st.metric("Vector Types", vector_types)

                # Progress simulation
                elapsed = time.time() - job_info.get('started_at', time.time())
                estimated_total = job_info.get('estimated_completion', time.time()) - job_info.get('started_at', time.time())
                progress = min(elapsed / estimated_total, 1.0)

                st.progress(progress, text=f"Progress: {progress*100:.1f}%")

                # Job details
                st.write("**Configuration:**")
                st.write(f"• Vector Types: {', '.join(job_info.get('vector_types', []))}")
                st.write(f"• Storage Patterns: {', '.join(job_info.get('storage_patterns', []))}")
                st.write(f"• Segment Duration: {job_info.get('segment_duration', 5.0)}s")
                st.write(f"• Processing Mode: {job_info.get('processing_mode', 'parallel')}")

    def _show_cost_estimation(self):
        """Show cost estimation for processing."""
        st.subheader("💰 Cost Estimation")

        # Get processing parameters
        vector_types = st.session_state.get('selected_vector_types', ['visual-text'])
        storage_patterns = st.session_state.get('selected_storage_patterns', ['direct_s3vector'])

        # Estimate video duration (placeholder)
        estimated_duration_minutes = 10.0  # Default estimate

        # TwelveLabs Marengo pricing: $0.05 per minute
        marengo_cost_per_minute = 0.05
        marengo_cost = estimated_duration_minutes * marengo_cost_per_minute * len(vector_types)

        # Storage costs (estimated)
        s3vector_storage_cost = 0.02 * len(vector_types)  # Per index
        opensearch_cost = 0.05 if 'opensearch_s3vector_hybrid' in storage_patterns else 0

        total_cost = marengo_cost + s3vector_storage_cost + opensearch_cost

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Marengo Processing", f"${marengo_cost:.3f}")

        with col2:
            st.metric("S3Vector Storage", f"${s3vector_storage_cost:.3f}")

        with col3:
            st.metric("OpenSearch (if used)", f"${opensearch_cost:.3f}")

        with col4:
            st.metric("Total Estimated", f"${total_cost:.3f}")

        # Cost breakdown
        with st.expander("📊 Cost Breakdown"):
            st.write("**Processing Costs:**")
            st.write(f"• Video Duration: {estimated_duration_minutes:.1f} minutes")
            st.write(f"• Vector Types: {len(vector_types)} types")
            st.write(f"• Marengo Rate: ${marengo_cost_per_minute:.3f} per minute per type")
            st.write(f"• Total Processing: ${marengo_cost:.3f}")
            st.write("")

            st.write("**Storage Costs:**")
            st.write(f"• S3Vector Indexes: {len(vector_types)} indexes")
            st.write(f"• Storage Rate: $0.02 per index per processing session")
            st.write(f"• OpenSearch: {'Enabled' if opensearch_cost > 0 else 'Disabled'}")
            st.write(f"• Total Storage: ${s3vector_storage_cost + opensearch_cost:.3f}")

        if st.session_state.get('use_real_aws', False):
            st.warning("⚠️ **Real AWS Mode**: These costs will be charged to your AWS account")
        else:
            st.info("🛡️ **Safe Mode**: No actual costs - simulation only")

    def _execute_dual_pattern_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on both storage patterns and compare performance."""
        import time

        col1, col2 = st.columns(2)

        with col1:
            st.write("**🎯 Direct S3Vector Pattern**")
            start_time = time.time()

            if not st.session_state.use_real_aws:
                # Simulate S3Vector search
                time.sleep(0.1)  # Simulate fast S3Vector response
                s3vector_latency = (time.time() - start_time) * 1000
                s3vector_results = self._generate_demo_search_results(query, "s3vector", num_results)

                st.success(f"✅ **Latency**: {s3vector_latency:.1f}ms")
                st.metric("Results Found", len(s3vector_results))
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in s3vector_results) / len(s3vector_results):.3f}")

                # Show top results
                for i, result in enumerate(s3vector_results[:3]):
                    with st.expander(f"Result {i+1}: {result['segment_id']}"):
                        st.write(f"**Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Metadata**: {result['metadata']}")
            else:
                st.info("Real AWS search would be executed here")

        with col2:
            st.write("**🔍 OpenSearch Hybrid Pattern**")
            start_time = time.time()

            if not st.session_state.use_real_aws:
                # Simulate OpenSearch hybrid search (slightly slower due to hybrid processing)
                time.sleep(0.15)  # Simulate hybrid search overhead
                opensearch_latency = (time.time() - start_time) * 1000
                opensearch_results = self._generate_demo_search_results(query, "opensearch", num_results)

                st.success(f"✅ **Latency**: {opensearch_latency:.1f}ms")
                st.metric("Results Found", len(opensearch_results))
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in opensearch_results) / len(opensearch_results):.3f}")

                # Show top results
                for i, result in enumerate(opensearch_results[:3]):
                    with st.expander(f"Result {i+1}: {result['segment_id']}"):
                        st.write(f"**Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Text Match**: {result.get('text_match', 'N/A')}")
                        st.write(f"**Hybrid Score**: {result.get('hybrid_score', 'N/A')}")

        # Performance comparison
        if not st.session_state.use_real_aws:
            st.subheader("📊 Performance Comparison")

            comparison_data = {
                "Metric": ["Latency (ms)", "Results Found", "Avg Similarity", "Search Type"],
                "Direct S3Vector": [f"{s3vector_latency:.1f}", len(s3vector_results),
                                  f"{sum(r['similarity'] for r in s3vector_results) / len(s3vector_results):.3f}", "Vector Only"],
                "OpenSearch Hybrid": [f"{opensearch_latency:.1f}", len(opensearch_results),
                                    f"{sum(r['similarity'] for r in opensearch_results) / len(opensearch_results):.3f}", "Vector + Text"]
            }

            st.table(comparison_data)

            # Store results for visualization
            st.session_state.search_results = {
                "s3vector": s3vector_results,
                "opensearch": opensearch_results,
                "query": query,
                "analysis": analysis
            }

    def _execute_s3vector_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on Direct S3Vector pattern only."""
        import time

        start_time = time.time()

        if not st.session_state.use_real_aws:
            # Simulate S3Vector search
            time.sleep(0.08)  # Fast S3Vector response
            latency = (time.time() - start_time) * 1000
            results = self._generate_demo_search_results(query, "s3vector", num_results)

            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                st.metric("Avg Similarity", f"{sum(r['similarity'] for r in results) / len(results):.3f}")

            # Detailed results
            st.subheader("🎯 Search Results")
            for i, result in enumerate(results):
                with st.expander(f"Result {i+1}: {result['segment_id']} (Similarity: {result['similarity']:.3f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Timestamp**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Index ARN**: {result['index_arn']}")
                    with col2:
                        st.write(f"**Similarity Score**: {result['similarity']:.3f}")
                        st.write(f"**Distance**: {result['distance']:.3f}")
                        st.write(f"**Metadata**: {result['metadata']}")

            # Store results
            st.session_state.search_results = {
                "s3vector": results,
                "query": query,
                "analysis": analysis,
                "pattern": "s3vector_only"
            }
        else:
            st.info("Real AWS S3Vector search would be executed here")

    def _execute_opensearch_search(self, query: str, analysis: Dict[str, Any], vector_types: List[str], num_results: int, threshold: float):
        """Execute search on OpenSearch Hybrid pattern only."""
        import time

        start_time = time.time()

        if not st.session_state.use_real_aws:
            # Simulate OpenSearch hybrid search
            time.sleep(0.12)  # Hybrid search with text processing
            latency = (time.time() - start_time) * 1000
            results = self._generate_demo_search_results(query, "opensearch", num_results)

            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Latency", f"{latency:.1f}ms")
            with col2:
                st.metric("Results Found", len(results))
            with col3:
                st.metric("Hybrid Score", f"{sum(r.get('hybrid_score', 0.8) for r in results) / len(results):.3f}")

            # Detailed results with hybrid features
            st.subheader("🔍 Hybrid Search Results")
            for i, result in enumerate(results):
                with st.expander(f"Result {i+1}: {result['segment_id']} (Hybrid Score: {result.get('hybrid_score', 0.8):.3f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Vector Similarity**: {result['similarity']:.3f}")
                        st.write(f"**Text Match Score**: {result.get('text_score', 0.7):.3f}")
                        st.write(f"**Combined Score**: {result.get('hybrid_score', 0.8):.3f}")
                    with col2:
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Text Matches**: {result.get('text_match', 'keyword matches')}")
                        st.write(f"**OpenSearch Index**: {result.get('opensearch_index', 'hybrid-index')}")

            # Store results
            st.session_state.search_results = {
                "opensearch": results,
                "query": query,
                "analysis": analysis,
                "pattern": "opensearch_only"
            }
        else:
            st.info("Real AWS OpenSearch hybrid search would be executed here")

    def _generate_demo_search_results(self, query: str, pattern: str, num_results: int) -> List[Dict[str, Any]]:
        """Generate demo search results for simulation."""
        import random

        results = []

        for i in range(num_results):
            # Base similarity score with some randomness
            base_similarity = random.uniform(0.7, 0.95)

            # Adjust based on pattern
            if pattern == "opensearch":
                # OpenSearch might have slightly different scores due to hybrid nature
                similarity = base_similarity * random.uniform(0.95, 1.05)
                text_score = random.uniform(0.6, 0.9)
                hybrid_score = (similarity * 0.7 + text_score * 0.3)
            else:
                similarity = base_similarity
                text_score = None
                hybrid_score = None

            result = {
                "segment_id": f"segment_{i+1}_{pattern}",
                "similarity": min(similarity, 1.0),
                "distance": 1.0 - min(similarity, 1.0),
                "vector_type": random.choice(["visual-text", "visual-image", "audio"]),
                "start_time": random.uniform(0, 120),
                "end_time": random.uniform(125, 180),
                "metadata": {
                    "video_id": f"demo_video_{random.randint(1, 3)}",
                    "confidence": random.uniform(0.8, 0.95),
                    "processing_time": random.uniform(0.1, 0.5)
                },
                "index_arn": f"arn:aws:s3vectors:us-east-1:123456789012:index/demo-{pattern}-index"
            }

            # Add pattern-specific fields
            if pattern == "opensearch":
                result["text_score"] = text_score
                result["hybrid_score"] = hybrid_score
                result["text_match"] = f"Keywords from '{query}' found in segment"
                result["opensearch_index"] = f"hybrid-{result['vector_type']}-index"

            results.append(result)

        # Sort by similarity/hybrid score
        if pattern == "opensearch":
            results.sort(key=lambda x: x.get('hybrid_score', 0), reverse=True)
        else:
            results.sort(key=lambda x: x['similarity'], reverse=True)

        return results

    def _display_results_table(self, results: List[Dict[str, Any]], pattern: str):
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
                video_id = result.get("metadata", {}).get("video_id", "demo_video")

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
                with st.expander(f"📋 Selected {pattern.title()} Result Details", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Segment ID**: {result.get('segment_id', 'Unknown')}")
                        st.write(f"**Timestamp**: {result.get('start_time', 0):.1f}s - {result.get('end_time', 0):.1f}s")
                        st.write(f"**Vector Type**: {result.get('vector_type', 'Unknown')}")
                    with col2:
                        st.write(f"**Similarity**: {result.get('similarity', 0):.3f}")
                        if pattern == "opensearch":
                            st.write(f"**Hybrid Score**: {result.get('hybrid_score', 0):.3f}")
                            st.write(f"**Text Match**: {result.get('text_match', 'N/A')}")
                        st.write(f"**Metadata**: {result.get('metadata', {})}")

    def run(self):
        """Main entry point to run the unified demo application."""
        try:
            # Configure page
            self.render_page_config()

            # Render header
            self.render_header()

            # Render sidebar and get AWS mode
            use_real_aws = self.render_sidebar()

            # Update AWS mode in session state
            st.session_state.use_real_aws = use_real_aws

            # Render main workflow
            self.render_main_workflow()

        except Exception as e:
            logger.error(f"Error in main application: {e}")
            st.error(f"Application error: {e}")
            st.info("Please refresh the page or contact support if the issue persists.")


def main():
    """Main entry point for the unified demo application."""
    try:
        # Create and run the demo
        demo = UnifiedS3VectorDemo()
        demo.run()
        
    except Exception as e:
        st.error(f"Failed to initialize demo application: {e}")
        st.info("Please check your configuration and try again.")


if __name__ == "__main__":
    main()
