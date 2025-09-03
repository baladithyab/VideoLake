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
        """Render the upload and processing section."""
        st.header("🎬 Upload & Processing")
        st.markdown("Select videos and configure multi-vector processing with Marengo 2.7")

        # Service manager integration demo
        if self.service_manager and self.coordinator:
            st.success("✅ **Multi-Vector Coordinator Ready** - Advanced processing capabilities available")

            # Configuration section
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🧠 Vector Configuration")

                # Vector type selection
                available_types = self.config.default_vector_types
                selected_types = st.multiselect(
                    "Select Vector Types:",
                    options=available_types,
                    default=available_types,
                    help="Choose which vector types to generate"
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
                st.session_state.processing_mode = processing_mode

            with col2:
                st.subheader("⚙️ Processing Options")

                # Storage strategy
                storage_strategy = st.selectbox(
                    "Storage Strategy:",
                    options=["direct_s3vector", "hybrid_opensearch"],
                    index=0,
                    help="How to store the generated vectors"
                )

                # Cost estimation toggle
                enable_cost_estimation = st.checkbox(
                    "Enable Cost Estimation",
                    value=True,
                    help="Show estimated processing costs"
                )

                # Update session state
                st.session_state.storage_strategy = storage_strategy
                st.session_state.enable_cost_estimation = enable_cost_estimation

            # Show vector type capabilities
            with st.expander("🧠 Available Vector Types"):
                for vtype in available_types:
                    provider = self._get_service_provider_for_type(vtype)
                    is_selected = vtype in selected_types
                    status = "✅ Selected" if is_selected else "⚪ Available"
                    st.write(f"• **{vtype}**: {provider} service - {status}")

            # Show processing modes
            with st.expander("⚡ Processing Strategies"):
                strategies = {
                    "parallel": "Process all vector types simultaneously (fastest)",
                    "sequential": "Process vector types one by one (most reliable)",
                    "adaptive": "Automatically select optimal strategy based on load"
                }
                for mode, description in strategies.items():
                    is_selected = mode == processing_mode
                    status = "✅ Selected" if is_selected else "⚪ Available"
                    st.write(f"• **{mode.title()}**: {description} - {status}")

        else:
            st.error("❌ **Service Manager Unavailable** - Limited functionality")

        # Placeholder for upload interface - will be implemented in T3.1
        st.info("📋 **Next**: Upload interface will be implemented in T3.1 (Consolidate Upload Features)")

        # Show current processing jobs if any
        if st.session_state.processing_jobs:
            st.subheader("🔄 Active Processing Jobs")
            for job_id, job_info in st.session_state.processing_jobs.items():
                with st.expander(f"Job: {job_id}"):
                    st.json(job_info)

        # Workflow navigation
        self._render_section_navigation("upload")

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
        """Render the query and search section."""
        st.header("🔍 Query & Search")
        st.markdown("Intelligent semantic search with automatic query routing")

        # Check prerequisites
        if not st.session_state.processed_videos:
            st.warning("⚠️ **No processed videos available** - Please complete the Upload & Processing step first")
            return

        # Service manager integration demo
        if self.service_manager and self.coordinator:
            st.success("✅ **Multi-Vector Search Engine Ready** - Cross-vector search capabilities available")

            # Main search interface
            st.subheader("🔍 Semantic Search")

            col1, col2 = st.columns([3, 1])

            with col1:
                search_query = st.text_input(
                    "Enter your search query:",
                    placeholder="e.g., 'person walking in the scene', 'car driving on highway', 'music playing'",
                    help="Describe what you're looking for in the videos",
                    key="main_search_query"
                )

            with col2:
                search_button = st.button("🔍 Search", type="primary", use_container_width=True)

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

                # Search execution (placeholder)
                if search_button:
                    with st.spinner("🔍 Searching across vector indices..."):
                        # Placeholder for actual search - will be implemented in T3.3
                        st.success("Search functionality will be implemented in T3.3")

                        # Update session state to mark search as attempted
                        st.session_state.current_query = search_query
                        st.session_state.query_analysis = query_analysis

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
            demo_results = self._generate_demo_search_results()
            st.session_state.search_results = demo_results
            st.success(f"Generated {len(demo_results)} demo results")

        # Display search results
        if st.session_state.search_results:
            st.write(f"**Found {len(st.session_state.search_results)} matching segments**")

            # Results table
            results_data = []
            for i, result in enumerate(st.session_state.search_results):
                results_data.append({
                    "Rank": i + 1,
                    "Video": result["video_name"],
                    "Segment": f"{result['start_time']:.1f}s - {result['end_time']:.1f}s",
                    "Similarity": f"{result['similarity_score']:.3f}",
                    "Vector Type": result["vector_type"],
                    "Description": result["description"][:50] + "..." if len(result["description"]) > 50 else result["description"]
                })

            # Display results with selection
            selected_result = st.selectbox(
                "Select a result to view:",
                options=range(len(results_data)),
                format_func=lambda x: f"#{x+1}: {results_data[x]['Video']} ({results_data[x]['Segment']}) - {results_data[x]['Similarity']}",
                help="Choose a search result to view in the video player"
            )

            if selected_result is not None:
                result = st.session_state.search_results[selected_result]
                st.session_state.selected_segment = result

                # Show selected result details
                with st.expander("📋 Selected Result Details"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Video**: {result['video_name']}")
                        st.write(f"**Segment**: {result['start_time']:.1f}s - {result['end_time']:.1f}s")
                        st.write(f"**Duration**: {result['end_time'] - result['start_time']:.1f}s")

                    with col2:
                        st.write(f"**Similarity**: {result['similarity_score']:.3f}")
                        st.write(f"**Vector Type**: {result['vector_type']}")
                        st.write(f"**Confidence**: {result.get('confidence', 0.85):.2f}")

                    st.write(f"**Description**: {result['description']}")

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
