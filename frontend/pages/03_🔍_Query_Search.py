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
    # Get service manager and coordinator from session state if available
    service_manager = st.session_state.get('service_manager')
    coordinator = st.session_state.get('coordinator')
    
    render_query_search_page(service_manager, coordinator)


def render_query_search_page(service_manager=None, coordinator=None):
    """Render the query and search page."""
    st.title("🔍 Query & Search")
    st.markdown("**Intelligent semantic search with dual storage pattern comparison**")
    
    # Check prerequisites
    if not st.session_state.get('processed_videos'):
        st.warning("⚠️ **No processed videos available** - Please complete the Media Processing step first")
        st.info("💡 Navigate to the Media Processing page to upload and process videos before searching.")
        return

    # Page description
    st.info("""
    **Query & Search Features:**
    - 🧠 Multi-vector search with Marengo 2.7 modalities
    - 🎯 Intelligent query analysis and routing
    - 🔄 Dual pattern search (Direct S3Vector + OpenSearch Hybrid)
    - 📊 Performance comparison and metrics
    - 🎛️ Advanced search options and filters
    """)

    # Use the search interface from search components with error handling
    with ErrorBoundary("Query & Search"):
        if service_manager or coordinator:
            # Initialize search components
            search_components = SearchComponents(service_manager, coordinator)
            
            # Render search interface with unique keys
            search_results = render_enhanced_search_interface(search_components)
            
            # Store results in session state
            if search_results:
                st.session_state.search_results = search_results
                
        else:
            st.info("🔍 **Search Interface** - Available when backend services are connected")
            render_demo_search_interface()


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

    # Vector modality selection with dropdown - FIXED: Added unique key
    modality_options = {
        "Visual Text Only": ["visual-text"],
        "Visual Image Only": ["visual-image"],
        "Audio Only": ["audio"],
        "Visual Text + Image": ["visual-text", "visual-image"],
        "Visual Text + Audio": ["visual-text", "audio"],
        "Visual Image + Audio": ["visual-image", "audio"],
        "All Modalities": ["visual-text", "visual-image", "audio"],
        "Auto-detect Best": ["auto-detect"]
    }
    
    selected_modality_key = st.selectbox(
        "🧠 Select Vector Modalities:",
        options=list(modality_options.keys()),
        index=3,  # Default to "Visual Text + Image"
        help="Choose which Marengo 2.7 vector types to use for search",
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

            # Auto-detect modality if enabled
            if "auto-detect" in selected_modalities and query:
                try:
                    from src.services.advanced_query_analysis import SimpleQueryAnalyzer
                    analyzer = SimpleQueryAnalyzer()
                    analysis = analyzer.analyze_query(query, ["visual-text", "visual-image", "audio"])
                    vector_types = analysis.recommended_vectors
                    st.info(f"🤖 Auto-detected modalities: {', '.join(vector_types)} (Intent: {analysis.intent.value})")
                except Exception as e:
                    st.warning(f"Auto-detection failed: {e}")
                    # Fallback to default selection
                    vector_types = ["visual-text", "visual-image"] if not vector_types else vector_types

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


def render_demo_search_interface():
    """Render demo search interface when backend services are not connected."""
    st.write("**Production Search Features:**")
    st.write("• Dual pattern search (Direct S3Vector + OpenSearch Hybrid)")
    st.write("• Multi-vector query processing")
    st.write("• Intelligent query routing")
    st.write("• Performance metrics and comparison")
    
    # Demo search form
    st.subheader("🔍 Demo Search Interface")
    
    demo_query = st.text_input(
        "Enter search query (demo):",
        placeholder="e.g., 'person walking', 'car driving'",
        key="demo_search_query_input"  # UNIQUE KEY ADDED
    )
    
    demo_modality = st.selectbox(
        "Select modality (demo):",
        options=["Visual Text + Image", "Visual Text Only", "Visual Image Only", "Audio Only"],
        key="demo_search_modality_selectbox"  # UNIQUE KEY ADDED
    )
    
    if st.button("🔍 Demo Search", key="demo_search_button"):
        if demo_query:
            st.success(f"Demo search executed for: '{demo_query}' using {demo_modality}")
            st.info("💡 Connect backend services for real search functionality")
        else:
            st.warning("Please enter a search query")


if __name__ == "__main__":
    main()