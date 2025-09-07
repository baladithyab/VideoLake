#!/usr/bin/env python3
"""
Unified S3Vector Demo Application (Refactored)

This is the refactored version of the unified demo interface that uses modular components
for better maintainability and code organization.

Key Features:
- Modular component architecture
- Proper backend service integration via StreamlitServiceManager
- 5-section unified workflow (Upload, Processing, Query, Results, Analytics)
- Multi-vector processing with Marengo 2.7
- Dual storage pattern comparison (Direct S3Vector vs OpenSearch Hybrid)
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import backend services
from src.services import (
    get_service_manager, 
    reset_service_manager,
    StreamlitIntegrationConfig,
    MultiVectorCoordinator
)
from src.utils.logging_config import get_logger

# Import production configuration
from src.config.app_config import get_config, get_config_manager
from frontend.components.search_components import SearchComponents
from frontend.components.results_components import ResultsComponents
from frontend.components.processing_components import ProcessingComponents
from frontend.components.workflow_resource_manager import render_workflow_resource_manager
from frontend.components.error_handling import (
    ErrorBoundary,
    FallbackComponents,
    get_error_handler,
    display_error_dashboard,
    ErrorSeverity
)

logger = get_logger(__name__)


class UnifiedS3VectorDemo:
    """Unified S3Vector Production Application with modular architecture."""
    
    def __init__(self):
        """Initialize the unified demo application."""
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
        # Define workflow sections and titles
        self.workflow_sections = ["upload", "query", "results", "visualization", "analytics", "resources"]
        self.section_titles = {
            "upload": "🎬 Upload & Processing",
            "query": "🔍 Query & Search",
            "results": "🎯 Results & Playback",
            "visualization": "📊 Embedding Visualization",
            "analytics": "⚙️ Analytics & Management",
            "resources": "🔧 Resource Management"
        }
        self.section_descriptions = {
            "upload": "Select videos and configure multi-vector processing with Marengo 2.7",
            "query": "Intelligent semantic search with dual storage pattern comparison",
            "results": "Interactive video player with segment overlay and similarity scores",
            "visualization": "Explore embedding space with dimensionality reduction and query overlay",
            "analytics": "Performance monitoring, cost tracking, and system management",
            "resources": "Manage AWS resources, resume work, create new resources, and cleanup"
        }
        
        # Initialize service manager and coordinator
        self.service_manager = None
        self.coordinator = None
        self._initialize_services()
        
        # Initialize component modules with proper error handling
        try:
            self.search_components = SearchComponents(self.service_manager, self.coordinator)
        except Exception as e:
            logger.warning(f"Failed to initialize search components: {e}")
            self.search_components = None
            
        try:
            self.results_components = ResultsComponents()
        except Exception as e:
            logger.warning(f"Failed to initialize results components: {e}")
            self.results_components = None
            
        try:
            self.processing_components = ProcessingComponents(self.service_manager, self.coordinator)
        except Exception as e:
            logger.warning(f"Failed to initialize processing components: {e}")
            self.processing_components = None
        
        # Initialize session state
        self._initialize_session_state()
    
    def get_workflow_progress(self, current_section: str) -> float:
        """Calculate workflow progress percentage."""
        if current_section not in self.workflow_sections:
            return 0.0
        
        current_index = self.workflow_sections.index(current_section)
        return (current_index + 1) / len(self.workflow_sections)
    
    def get_next_section(self, current_section: str) -> str:
        """Get the next section in the workflow."""
        if current_section not in self.workflow_sections:
            return self.workflow_sections[0] if self.workflow_sections else ""
        
        current_index = self.workflow_sections.index(current_section)
        next_index = (current_index + 1) % len(self.workflow_sections)
        return self.workflow_sections[next_index]
    
    def get_previous_section(self, current_section: str) -> str:
        """Get the previous section in the workflow."""
        if current_section not in self.workflow_sections:
            return self.workflow_sections[-1] if self.workflow_sections else ""
        
        current_index = self.workflow_sections.index(current_section)
        prev_index = (current_index - 1) % len(self.workflow_sections)
        return self.workflow_sections[prev_index]
    
    def check_prerequisites(self, section: str, session_state) -> dict:
        """Check prerequisites for a workflow section."""
        prerequisites = {
            "upload": True,  # Always available
            "query": hasattr(session_state, 'processed_videos') and bool(session_state.processed_videos),
            "results": hasattr(session_state, 'search_results') and bool(session_state.search_results),
            "visualization": hasattr(session_state, 'search_results') and bool(session_state.search_results),
            "analytics": hasattr(session_state, 'processing_jobs') and bool(session_state.processing_jobs),
            "resources": True  # Always available
        }

        return {
            "met": prerequisites.get(section, False),
            "required_sections": {
                "query": ["upload"],
                "results": ["upload", "query"],
                "visualization": ["upload", "query"],
                "analytics": ["upload"]
            }.get(section, [])
        }
    
    def _initialize_services(self):
        """Initialize backend services with proper error handling."""
        try:
            # Create integration config for Streamlit
            integration_config = StreamlitIntegrationConfig(
                enable_multi_vector=True,
                enable_concurrent_processing=True,
                default_vector_types=["visual-text", "visual-image", "audio"],
                max_concurrent_jobs=8,
                enable_performance_monitoring=True
            )
            
            # Get service manager
            self.service_manager = get_service_manager(integration_config)
            
            if self.service_manager:
                # Get multi-vector coordinator
                self.coordinator = self.service_manager.multi_vector_coordinator
                logger.info("Successfully initialized service manager and coordinator")
            else:
                logger.warning("Service manager initialization returned None")
                
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            self.service_manager = None
            self.coordinator = None
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables."""
        # Core workflow state
        if 'current_section' not in st.session_state:
            st.session_state.current_section = 'upload'
        
        # Processing state
        if 'processing_jobs' not in st.session_state:
            st.session_state.processing_jobs = {}
        
        if 'processed_videos' not in st.session_state:
            st.session_state.processed_videos = {}
        
        # Search state
        if 'search_results' not in st.session_state:
            st.session_state.search_results = {}
        
        if 'selected_segment' not in st.session_state:
            st.session_state.selected_segment = None
        
        # Configuration state - using production config
        if 'selected_vector_types' not in st.session_state:
            st.session_state.selected_vector_types = self.config.ui.default_vector_types.copy()
        
        if 'selected_storage_patterns' not in st.session_state:
            st.session_state.selected_storage_patterns = self.config.ui.default_storage_patterns.copy()
        
        if 'segment_duration' not in st.session_state:
            st.session_state.segment_duration = self.config.ui.default_segment_duration
        
        if 'processing_mode' not in st.session_state:
            st.session_state.processing_mode = self.config.ui.default_processing_mode
    
    def render_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title=self.config.ui.app_title,
            page_icon=self.config.ui.app_icon,
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def render_header(self):
        """Render the application header."""
        st.title(f"{self.config.ui.app_icon} {self.config.ui.app_title}")
        st.markdown("**Production S3Vector Multi-Vector Application with Dual Storage Pattern Support**")
        
        # Service status indicator
        if self.service_manager and self.coordinator:
            st.success("✅ **Backend Services Connected** - Full functionality available")
        else:
            st.error("❌ **Backend Services Unavailable** - Limited functionality")
    
    def render_sidebar(self):
        """Render the sidebar with configuration options."""
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Service integration test
            if st.button("🔧 Test Service Integration"):
                self.test_service_manager_integration()
            
            # Workflow navigation
            st.header("🔄 Workflow Navigation")
            
            current_section = st.selectbox(
                "Current Section:",
                options=self.workflow_sections,
                index=self.workflow_sections.index(st.session_state.current_section),
                format_func=lambda x: self.section_titles.get(x, x) or x,
                help="Navigate between workflow sections"
            )
            
            st.session_state.current_section = current_section
            
            # Show workflow progress
            progress = self.get_workflow_progress(current_section)
            st.progress(progress, text=f"Workflow Progress: {progress*100:.0f}%")
            
            # Prerequisites check
            prereqs = self.check_prerequisites(current_section, st.session_state)
            if not prereqs["met"]:
                st.warning(f"⚠️ Prerequisites not met. Complete: {', '.join(prereqs['required_sections'])}")
    
    def test_service_manager_integration(self):
        """Test service manager integration and display results."""
        try:
            if not self.service_manager:
                st.error("❌ Service manager not available")
                return
            
            # Test service manager
            st.info("🔄 Testing service manager...")
            
            # Test coordinator
            if self.coordinator:
                st.success("✅ Multi-vector coordinator available")
            else:
                st.warning("⚠️ Multi-vector coordinator not available")
            
            # Test individual services
            services_status = {
                "Search Engine": hasattr(self.service_manager, 'search_engine'),
                "Storage Manager": hasattr(self.service_manager, 'storage_manager'),
                "TwelveLabs Service": hasattr(self.service_manager, 'twelvelabs_service'),
                "Bedrock Service": hasattr(self.service_manager, 'bedrock_service')
            }
            
            for service_name, available in services_status.items():
                if available:
                    st.success(f"✅ {service_name}")
                else:
                    st.error(f"❌ {service_name}")
            
        except Exception as e:
            st.error(f"Service integration test failed: {e}")
    
    def render_main_workflow(self):
        """Render the main workflow based on current section."""
        current_section = st.session_state.current_section
        
        # Render section header
        st.header(self.section_titles.get(current_section, current_section))
        st.markdown(self.section_descriptions.get(current_section, ""))
        
        # Render section content
        if current_section == "upload":
            self.render_upload_processing_section()
        elif current_section == "query":
            self.render_query_search_section()
        elif current_section == "results":
            self.render_results_playback_section()
        elif current_section == "visualization":
            self.render_visualization_section()
        elif current_section == "analytics":
            self.render_analytics_section()
        elif current_section == "resources":
            self.render_resource_management_section()

        # Render section navigation
        self.render_section_navigation(current_section)
    
    def render_upload_processing_section(self):
        """Render the upload and processing section."""
        with ErrorBoundary("Upload & Processing"):
            # Quick resume option
            st.subheader("🔄 Resume or Start Fresh")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Resume with Existing Resources", type="primary"):
                    st.session_state.show_resume_dialog = True

            with col2:
                if st.button("🆕 Create New Resources"):
                    st.session_state.show_creation_dialog = True

            # Show dialogs if requested
            if st.session_state.get('show_resume_dialog', False):
                with st.expander("🔄 Resume with Existing Resources", expanded=True):
                    from frontend.components.workflow_resource_manager import WorkflowResourceManager
                    manager = WorkflowResourceManager()
                    if manager.render_workflow_resume_section():
                        st.session_state.show_resume_dialog = False
                        st.rerun()

            if st.session_state.get('show_creation_dialog', False):
                with st.expander("🛠️ Create New Resources", expanded=True):
                    from frontend.components.workflow_resource_manager import WorkflowResourceManager
                    manager = WorkflowResourceManager()
                    manager.render_resource_creation_wizard()
                    if st.button("✅ Done Creating Resources"):
                        st.session_state.show_creation_dialog = False
                        st.rerun()

            # Storage pattern selection
            st.subheader("🏗️ Storage Pattern Selection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("**Pattern 1: Direct S3Vector**")
            st.write("• Query S3Vector indexes directly")
            st.write("• Native S3Vector performance")
            st.write("• Cost-effective vector storage")
            
            enable_direct = st.checkbox("Enable Direct S3Vector", value=True)
        
        with col2:
            st.info("**Pattern 2: OpenSearch + S3Vector Hybrid**")
            st.write("• OpenSearch with S3Vector backend")
            st.write("• Hybrid search capabilities")
            st.write("• Text + vector search fusion")
            
            enable_hybrid = st.checkbox("Enable OpenSearch Hybrid", value=True)
        
        # Update storage patterns
        patterns = []
        if enable_direct:
            patterns.append("direct_s3vector")
        if enable_hybrid:
            patterns.append("opensearch_s3vector_hybrid")
        
        st.session_state.selected_storage_patterns = patterns
        
        # Vector configuration
        st.subheader("🧠 Multi-Vector Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Vector type selection
            selected_types = st.multiselect(
                "Select Vector Types:",
                options=self.config.ui.default_vector_types,
                default=st.session_state.selected_vector_types,
                help="Choose which Marengo 2.7 vector types to generate"
            )
            st.session_state.selected_vector_types = selected_types
            
            # Segment duration
            segment_duration = st.slider(
                "Segment Duration (seconds):",
                min_value=2.0,
                max_value=10.0,
                value=st.session_state.segment_duration,
                step=0.5
            )
            st.session_state.segment_duration = segment_duration
        
        with col2:
            # Processing mode
            processing_mode = st.selectbox(
                "Processing Strategy:",
                options=["parallel", "sequential", "adaptive"],
                index=["parallel", "sequential", "adaptive"].index(st.session_state.processing_mode)
            )
            st.session_state.processing_mode = processing_mode
            
            # Cost estimation
            if st.checkbox("Show Cost Estimation", value=True):
                if self.processing_components:
                    self.processing_components.show_cost_estimation()
                else:
                    st.info("💰 **Cost Estimation** - Available when backend services are connected")
        
        # Video input section
        if self.processing_components:
            self.processing_components.render_video_input_section()
        else:
            st.info("📹 **Video Upload** - Available when backend services are connected")
    
    def render_query_search_section(self):
        """Render the query and search section."""
        # Check prerequisites
        if not st.session_state.processed_videos:
            st.warning("⚠️ **No processed videos available** - Please complete the Upload & Processing step first")
            return

        # Use the new search interface from search components with error handling
        with ErrorBoundary("Query & Search"):
            if self.search_components:
                search_results = self.search_components.render_search_interface()
            else:
                st.info("🔍 **Search Interface** - Available when backend services are connected")
                st.write("**Production Search Features:**")
                st.write("• Dual pattern search (Direct S3Vector + OpenSearch Hybrid)")
                st.write("• Multi-vector query processing")
                st.write("• Intelligent query routing")
    
    def render_results_playback_section(self):
        """Render the results and playback section."""
        with ErrorBoundary("Results & Playback"):
            if self.results_components:
                # Display search results
                self.results_components.display_search_results(st.session_state.search_results)

                # Video player
                self.results_components.render_video_player_placeholder()

                # Segment overlay
                self.results_components.render_segment_overlay_placeholder()

                # Performance metrics
                self.results_components.display_performance_metrics(st.session_state.search_results)

                # Export functionality
                self.results_components.render_results_export(st.session_state.search_results)
            else:
                st.info("🎯 **Results & Playback** - Available when backend services are connected")
                st.write("**Demo Features:**")
                st.write("• Interactive video player with segment overlay")
                st.write("• Similarity score visualization")
                st.write("• Performance metrics dashboard")
                st.write("• Results export functionality")
    
    def render_visualization_section(self):
        """Render the embedding visualization section."""
        st.info("📊 **Embedding Visualization** - Will be implemented in T3.4")
        
        # Placeholder for visualization
        st.write("**Interactive Embedding Space Exploration (Coming Soon)**")
        st.write("• PCA/t-SNE/UMAP dimensionality reduction")
        st.write("• Query point overlay")
        st.write("• Interactive result exploration")
        st.write("• Multi-vector space comparison")
    
    def render_analytics_section(self):
        """Render the analytics and management section."""
        with ErrorBoundary("Analytics & Management"):
            # Processing progress
            if self.processing_components:
                self.processing_components.show_processing_progress()
            else:
                st.info("📊 **Processing Progress** - Available when backend services are connected")

            # Cost estimation
            if self.processing_components:
                self.processing_components.show_cost_estimation()
            else:
                st.info("💰 **Cost Estimation** - Available when backend services are connected")

            # Error dashboard
            st.subheader("🐛 Error Dashboard")
            display_error_dashboard()

            # System status
            st.subheader("🔧 System Status")
            if st.button("🔄 Refresh Status"):
                self.test_service_manager_integration()

    def render_resource_management_section(self):
        """Render the resource management section."""
        # Use workflow resource manager component directly
        # Note: Removed ErrorBoundary to allow RerunException to bubble up naturally
        try:
            render_workflow_resource_manager()
        except Exception as e:
            # Only catch actual errors, not RerunException
            from frontend.components.error_handling import _is_rerun_exception
            if _is_rerun_exception(e):
                raise  # Let RerunException bubble up
            st.error(f"⚠️ Issue in Resource Management: {e}")
            st.info("🔄 Please refresh the page if the issue persists.")

    def render_section_navigation(self, current_section: str):
        """Render navigation controls for workflow sections."""
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            prev_section = self.get_previous_section(current_section)
            if st.button(f"⬅️ {self.section_titles.get(prev_section, prev_section)}"):
                st.session_state.current_section = prev_section
                st.rerun()
        
        with col2:
            progress = self.get_workflow_progress(current_section)
            st.progress(progress, text=f"Section {self.workflow_sections.index(current_section) + 1} of {len(self.workflow_sections)}")
        
        with col3:
            next_section = self.get_next_section(current_section)
            if st.button(f"{self.section_titles.get(next_section, next_section)} ➡️"):
                st.session_state.current_section = next_section
                st.rerun()
    
    def run(self):
        """Main entry point to run the unified demo application."""
        try:
            # Configure page
            self.render_page_config()
            
            # Render header
            self.render_header()
            
            # Render sidebar
            self.render_sidebar()
            
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
