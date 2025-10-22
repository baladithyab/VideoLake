#!/usr/bin/env python3
"""
S3Vector Multi-Page Streamlit Application

This is the main entry point for the S3Vector application using Streamlit's
multi-page architecture. It provides proper page routing and eliminates
duplicate element ID conflicts.

Pages:
- 🔧 Resource Management
- 🎬 Media Processing  
- 🔍 Query & Search
- 🎯 Results & Playback
- 📊 Embedding Visualization
- ⚙️ Analytics & Management
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.services import (
    get_service_manager, 
    reset_service_manager,
    StreamlitIntegrationConfig,
    MultiVectorCoordinator
)
from src.utils.logging_config import get_logger
from src.config.app_config import get_config, get_config_manager

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="S3Vector - Multi-Vector Search Platform",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_services():
    """Initialize backend services and store in session state."""
    if 'services_initialized' not in st.session_state:
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
            service_manager = get_service_manager(integration_config)
            
            if service_manager:
                # Get multi-vector coordinator
                coordinator = service_manager.multi_vector_coordinator
                
                # Store in session state for pages to access
                st.session_state.service_manager = service_manager
                st.session_state.coordinator = coordinator
                
                # Validate coordinator initialization
                if coordinator is not None:
                    st.session_state.services_initialized = True
                    logger.info("Successfully initialized service manager and coordinator")
                else:
                    st.session_state.services_initialized = False
                    logger.error("MultiVectorCoordinator initialization failed - coordinator is None")
                    
                    # Show detailed debugging information
                    logger.error(f"Service manager type: {type(service_manager)}")
                    logger.error(f"Service manager has multi_vector_coordinator attr: {hasattr(service_manager, 'multi_vector_coordinator')}")
                    
                    if hasattr(service_manager, 'multi_vector_coordinator'):
                        logger.error(f"Coordinator value: {service_manager.multi_vector_coordinator}")
                    
                    # Check individual services
                    logger.error(f"TwelveLabs service: {getattr(service_manager, 'twelvelabs_service', 'NOT_FOUND')}")
                    logger.error(f"Search engine: {getattr(service_manager, 'search_engine', 'NOT_FOUND')}")
                    logger.error(f"Storage manager: {getattr(service_manager, 'storage_manager', 'NOT_FOUND')}")
                    logger.error(f"Bedrock service: {getattr(service_manager, 'bedrock_service', 'NOT_FOUND')}")
                    
                    # Try to get detailed error information
                    try:
                        # Force re-initialization of coordinator
                        logger.info("Attempting coordinator re-initialization...")
                        service_manager._initialize_multi_vector_coordinator()
                        coordinator = service_manager.multi_vector_coordinator
                        if coordinator is not None:
                            st.session_state.coordinator = coordinator
                            st.session_state.services_initialized = True
                            logger.info("Successfully re-initialized coordinator")
                        else:
                            logger.error("Coordinator re-initialization also failed - still None")
                    except Exception as coord_error:
                        logger.error(f"Coordinator re-initialization error: {coord_error}")
                        import traceback
                        logger.error(f"Full traceback: {traceback.format_exc()}")
            else:
                logger.warning("Service manager initialization returned None")
                st.session_state.services_initialized = False
                
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            st.session_state.services_initialized = False
            st.session_state.service_manager = None
            st.session_state.coordinator = None


def render_sidebar():
    """Render the application sidebar with navigation and status."""
    with st.sidebar:
        st.title("🔍 S3Vector")
        st.markdown("**Multi-Vector Search Platform**")
        
        # Service status
        if st.session_state.get('services_initialized'):
            st.success("✅ **Backend Services Connected**")
        else:
            st.error("❌ **Backend Services Unavailable**")
            if st.button("🔄 Retry Connection", key="sidebar_retry_connection"):
                st.session_state.services_initialized = False
                initialize_services()
                st.rerun()
        
        st.markdown("---")
        
        # Navigation info
        st.markdown("### 📋 Navigation")
        st.markdown("""
        Use the page selector in the sidebar to navigate between:
        
        - **🔧 Resource Management**: Manage AWS resources
        - **🎬 Media Processing**: Upload and process videos
        - **🔍 Query & Search**: Search with multi-vector queries
        - **🎯 Results & Playback**: View results and play videos
        - **📊 Embedding Visualization**: Explore embedding space
        - **⚙️ Analytics & Management**: Monitor system performance
        """)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔧 Test Services", key="sidebar_test_services"):
            test_service_integration()
        
        if st.button("🧹 Clear Cache", key="sidebar_clear_cache"):
            st.cache_data.clear()
            st.success("Cache cleared!")
        
        if st.button("🔄 Reset Session", key="sidebar_reset_session"):
            # Clear session state except for services
            keys_to_keep = ['service_manager', 'coordinator', 'services_initialized']
            keys_to_remove = [k for k in st.session_state.keys() if k not in keys_to_keep]
            for key in keys_to_remove:
                del st.session_state[key]
            st.success("Session reset!")
            st.rerun()


def test_service_integration():
    """Test service integration and display results."""
    try:
        service_manager = st.session_state.get('service_manager')
        coordinator = st.session_state.get('coordinator')
        
        if not service_manager:
            st.error("❌ Service manager not available")
            return
        
        # Test service manager
        st.info("🔄 Testing service manager...")
        
        # Test coordinator
        if coordinator:
            st.success("✅ Multi-vector coordinator available")
        else:
            st.warning("⚠️ Multi-vector coordinator not available")
        
        # Test individual services
        services_status = {
            "Search Engine": hasattr(service_manager, 'search_engine'),
            "Storage Manager": hasattr(service_manager, 'storage_manager'),
            "TwelveLabs Service": hasattr(service_manager, 'twelvelabs_service'),
            "Bedrock Service": hasattr(service_manager, 'bedrock_service')
        }
        
        for service_name, available in services_status.items():
            if available:
                st.success(f"✅ {service_name}")
            else:
                st.error(f"❌ {service_name}")
        
    except Exception as e:
        st.error(f"Service integration test failed: {e}")


def render_main_content():
    """Render the main content area."""
    st.title("🔍 S3Vector Multi-Vector Search Platform")
    st.markdown("**Production S3Vector Application with Dual Storage Pattern Support**")
    
    # Welcome message
    st.info("""
    **Welcome to S3Vector!** 
    
    This is a multi-page Streamlit application for multi-vector search and analysis.
    Use the sidebar navigation to access different features:
    
    1. **🔧 Resource Management** - Set up AWS resources
    2. **🎬 Media Processing** - Upload and process videos
    3. **🔍 Query & Search** - Perform semantic searches
    4. **🎯 Results & Playback** - View and analyze results
    5. **📊 Embedding Visualization** - Explore embedding space
    6. **⚙️ Analytics & Management** - Monitor system performance
    """)
    
    # Quick start guide
    with st.expander("🚀 Quick Start Guide"):
        st.markdown("""
        ### Getting Started:
        
        1. **Resource Management**: First, set up your AWS resources (S3Vector buckets, OpenSearch domains)
        2. **Media Processing**: Upload videos and configure processing settings
        3. **Query & Search**: Perform searches using natural language queries
        4. **Results & Playback**: View search results and play video segments
        5. **Visualization**: Explore the embedding space visually
        6. **Analytics**: Monitor performance and manage the system
        
        ### Features:

        - **Marengo 2.7 Multi-Modal Search**: Unified embedding space for text, image, video, and audio
        - **Simplified Resource Management**: Streamlined AWS resource creation and cleanup
        - **Real-time Processing**: Process videos with Marengo 2.7 model exclusively
        - **Interactive Visualization**: Explore embeddings with PCA, t-SNE, and UMAP
        - **Performance Analytics**: Monitor costs, latency, and system health
        """)
    
    # System status overview
    st.subheader("📊 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        service_status = "Connected" if st.session_state.get('services_initialized') else "Disconnected"
        st.metric("Backend Services", service_status)
    
    with col2:
        processed_videos = len(st.session_state.get('processed_videos', {}))
        st.metric("Processed Videos", processed_videos)
    
    with col3:
        search_results = len(st.session_state.get('search_results', {}))
        st.metric("Search Results", search_results)
    
    with col4:
        active_resources = len(st.session_state.get('active_resources', {}))
        st.metric("Active Resources", active_resources)


def main():
    """Main application entry point."""
    # Initialize services
    initialize_services()
    
    # Render sidebar
    render_sidebar()
    
    # Render main content
    render_main_content()


if __name__ == "__main__":
    main()