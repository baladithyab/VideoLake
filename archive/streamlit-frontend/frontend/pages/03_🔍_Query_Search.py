#!/usr/bin/env python3
"""
Query & Search Page - Streamlit Multi-page App

This page handles all search functionality including:
- Multi-vector search with modality selection
- Dual storage pattern comparison
- Query analysis and routing
- Search result generation and display
"""

import streamlit as st
from typing import Dict, Any, Optional
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from frontend.components.search_components import SearchComponents
from frontend.components.error_handling import ErrorBoundary

# Page configuration
st.set_page_config(
    page_title="Query & Search - S3Vector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main function for the query and search page."""
    # Initialize backend services if not already done
    _initialize_backend_services()

    # Get service manager and coordinator from session state if available
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')

    render_query_search_page(service_manager, coordinator)

def _initialize_backend_services():
    """Initialize backend services for search functionality."""
    try:
        # Initialize enhanced storage components if not already done
        if 'enhanced_storage_components' not in st.session_state:
            from frontend.components.enhanced_storage_components import EnhancedStorageComponents
            st.session_state.enhanced_storage_components = EnhancedStorageComponents()

        # Get the storage manager
        enhanced_storage_components = st.session_state.enhanced_storage_components
        if hasattr(enhanced_storage_components, 'storage_manager') and enhanced_storage_components.storage_manager:
            st.session_state.enhanced_storage_manager = enhanced_storage_components.storage_manager

        # Initialize service locator
        if 'service_locator' not in st.session_state:
            from frontend.components.service_locator import init_services_in_session
            init_services_in_session()

        # Initialize Marengo 2.7 service (TwelveLabs) - this is the only embedding service we use
        if 'twelvelabs_service' not in st.session_state:
            try:
                from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
                st.session_state.twelvelabs_service = TwelveLabsVideoProcessingService()
                st.success("✅ Marengo 2.7 service initialized successfully")
            except Exception as e:
                st.error(f"❌ Could not initialize Marengo 2.7 service: {e}")
                st.warning("⚠️ Multi-modal search requires Marengo 2.7 service")

    except Exception as e:
        st.error(f"Failed to initialize backend services: {e}")
        # Continue without backend services


def render_query_search_page(service_manager=None, coordinator=None):
    """Render the query and search page."""
    st.title("🔍 Query & Search")
    st.markdown("**Intelligent semantic search with dual storage pattern comparison**")

    # Show backend service status
    _show_backend_status()

    # Check if we have any backend services available
    enhanced_storage_manager = st.session_state.get('enhanced_storage_manager')
    has_backend_services = enhanced_storage_manager is not None or service_manager is not None or coordinator is not None

    # Page description
    st.info("""
    **Marengo 2.7 Multi-Modal Search:**
    - 📝 **Visual-Text**: Text queries → Visual embeddings optimized for text search
    - 🖼️ **Visual-Image**: Text queries → Visual embeddings optimized for image search
    - 🔊 **Audio**: Text queries → Audio embeddings for audio content search
    - 🔄 **Dual Backend**: Direct S3Vector + OpenSearch Hybrid patterns
    - 📊 **Performance Metrics**: Real-time comparison and analytics
    """)

    # Use the search interface from search components with error handling
    with ErrorBoundary("Query & Search"):
        if has_backend_services:
            # Initialize search components
            search_components = SearchComponents(service_manager, coordinator)

            # Render search interface with unique keys
            search_results = render_enhanced_search_interface(search_components)

            # Store results in session state and show status
            if search_results:
                st.session_state.search_results = search_results

                # Show search completion status
                if search_results.get('backend_used'):
                    results_count = len(search_results.get('results', []))
                    processing_time = search_results.get('processing_time_ms', 0)
                    st.success(f"✅ **Search Completed**: {results_count} results found in {processing_time:.1f}ms")

                    if results_count == 0:
                        st.warning("⚠️ **No Results Found** - Try adjusting your query or similarity threshold")
                else:
                    st.error("❌ **Search Failed** - Backend services are not available")
            else:
                st.error("❌ **Search Failed** - No results returned")

        else:
            st.error("❌ **Backend Services Required** - Please ensure S3Vector and OpenSearch services are properly configured")
            st.info("""
            **Required Services:**
            - TwelveLabs Marengo 2.7 service for embeddings
            - S3Vector storage manager for vector search
            - OpenSearch integration manager for hybrid search

            **Setup Instructions:**
            1. Configure AWS credentials
            2. Initialize S3Vector buckets and indexes
            3. Set up OpenSearch domains
            4. Verify TwelveLabs API access
            """)

def _show_backend_status():
    """Show the status of backend services and available resources."""
    with st.expander("🔧 Backend Service Status", expanded=False):
        enhanced_storage_manager = st.session_state.get('enhanced_storage_manager')

        if enhanced_storage_manager:
            st.success("✅ Enhanced Storage Manager: Connected")

            # Show available backends based on manager properties
            available_backends = []
            if hasattr(enhanced_storage_manager, 's3vector_manager') and enhanced_storage_manager.s3vector_manager:
                available_backends.append('s3vector')
            if hasattr(enhanced_storage_manager, 'opensearch_pattern2_manager') and enhanced_storage_manager.opensearch_pattern2_manager:
                available_backends.append('opensearch')

            st.info(f"📊 Available backends: {', '.join(available_backends)}")

            # Show resource details
            col1, col2 = st.columns(2)

            with col1:
                if 's3vector' in available_backends:
                    st.write("**S3Vector Backend:**")
                    try:
                        # Get S3Vector bucket info from resource registry
                        from src.utils.resource_registry import resource_registry
                        vector_buckets = resource_registry.list_vector_buckets()
                        active_buckets = [b for b in vector_buckets if b.get('status') == 'created']
                        if active_buckets:
                            st.write(f"- Bucket: {active_buckets[0].get('name')}")
                            st.write(f"- Status: Active")
                        else:
                            st.write("- No active buckets found")
                    except Exception as e:
                        st.write(f"- Error getting bucket info: {e}")

            with col2:
                if 'opensearch' in available_backends:
                    st.write("**OpenSearch Backend:**")
                    try:
                        # Get OpenSearch domain info from resource registry
                        from src.utils.resource_registry import resource_registry
                        opensearch_domains = resource_registry.list_opensearch_domains()
                        active_domains = [d for d in opensearch_domains if d.get('status') == 'created']
                        if active_domains:
                            st.write(f"- Domain: {active_domains[0].get('name')}")
                            st.write(f"- Status: Active")
                        else:
                            st.write("- No active domains found")
                    except Exception as e:
                        st.write(f"- Error getting domain info: {e}")

        else:
            st.warning("⚠️ Enhanced Storage Manager: Not connected")

        # Show service locator status
        service_locator = st.session_state.get('service_locator')
        if service_locator:
            available_services = service_locator.get_available_services()
            st.info(f"🔧 Service Locator: {len(available_services)} services available")
            if available_services:
                st.write(f"Services: {', '.join(available_services)}")
        else:
            st.warning("⚠️ Service Locator: Not initialized")


def render_enhanced_search_interface(search_components):
    """Render enhanced search interface with unique keys."""
    st.header("🔍 Multi-Vector Search")

    # Query input
    query = st.text_input(
        "Enter your search query:",
        placeholder="e.g., 'person walking in the scene', 'car driving at night'",
        help="Describe what you're looking for in the videos",
        key="query_search_text_input"  # UNIQUE KEY ADDED
    )

    # Modality selection (prominent)
    st.subheader("🎯 Select Search Modality")

    # Marengo 2.7 modality selection - simplified to core modalities
    modality_options = {
        "Visual-Text Search": ["visual-text"],
        "Visual-Image Search": ["visual-image"],
        "Audio Search": ["audio"]
    }
    
    selected_modality_key = st.selectbox(
        "🧠 Select Search Modality:",
        options=list(modality_options.keys()),
        index=0,  # Default to "Visual-Text Search"
        help="Choose which Marengo 2.7 embedding type to use for search",
        key="query_search_modality_selectbox"  # UNIQUE KEY ADDED
    )
    
    selected_modalities = modality_options[selected_modality_key]
    
    # Show selected modalities
    st.info(f"**Selected Modalities:** {', '.join(selected_modalities)}")

    # Advanced options in expander
    with st.expander("🔧 Advanced Search Options"):
        col1, col2 = st.columns(2)

        with col1:
            top_k = st.slider(
                "Number of results:",
                min_value=1, max_value=20, value=5,
                help="How many results to return",
                key="query_search_top_k_slider"  # UNIQUE KEY ADDED
            )

        with col2:
            similarity_threshold = st.slider(
                "Similarity threshold:",
                min_value=0.0, max_value=1.0, value=0.7, step=0.05,
                help="Minimum similarity score for results",
                key="query_search_similarity_threshold_slider"  # UNIQUE KEY ADDED
            )

    # Search execution
    search_results = {}

    if query and selected_modalities and st.button("🔍 Search Videos", type="primary", key="query_search_execute_button"):
        with st.spinner("Searching videos..."):
            # Display selected modalities
            st.info(f"🎯 Searching with modalities: {', '.join(selected_modalities)}")

            # Build vector types list
            vector_types = []
            if "visual-text" in selected_modalities:
                vector_types.append("visual-text")
            if "visual-image" in selected_modalities:
                vector_types.append("visual-image")
            if "audio" in selected_modalities:
                vector_types.append("audio")

            # Display selected modality info
            st.info(f"🎯 **Selected Modality**: {selected_modality_key}")
            if selected_modalities[0] == "visual-text":
                st.info("📝 **Search Type**: Text query → Visual-Text embeddings (optimized for text-to-video search)")
            elif selected_modalities[0] == "visual-image":
                st.info("🖼️ **Search Type**: Text query → Visual-Image embeddings (optimized for image-to-video search)")
            elif selected_modalities[0] == "audio":
                st.info("🔊 **Search Type**: Text query → Audio embeddings (for audio content search)")

            # Analyze query
            analysis = search_components.analyze_search_query(query, vector_types)

            # Execute search for each storage pattern
            search_components.execute_dual_pattern_search(
                query=query,
                analysis=analysis,
                vector_types=vector_types,
                num_results=top_k,
                threshold=similarity_threshold
            )

            # Execute real search using backend services
            search_results = search_components._execute_real_backend_search(
                query=query,
                vector_types=vector_types,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )

            # Store results in session state
            st.session_state.search_results = search_results
            st.session_state.last_query = query
            st.session_state.selected_vector_types = vector_types

    elif query and not selected_modalities:
        st.warning("⚠️ Please select at least one search modality")

    return search_results





if __name__ == "__main__":
    main()