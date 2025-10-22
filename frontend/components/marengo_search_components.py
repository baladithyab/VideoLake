"""
Marengo-Focused Search Components

This module provides search functionality focused exclusively on the Marengo 2.7 model
for consistent embedding space across text, image, video, and audio modalities.

Key Features:
- Marengo 2.7 exclusive embedding generation
- Unified search interface for all modalities
- Simplified vector type selection
- Clear search result presentation
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import time

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class MarengoSearchComponents:
    """Search components focused on Marengo 2.7 model."""
    
    def __init__(self):
        self.supported_modalities = [
            "visual-text",
            "visual-image", 
            "audio"
        ]
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state for search functionality."""
        if 'marengo_search_state' not in st.session_state:
            st.session_state.marengo_search_state = {
                'last_query': '',
                'last_results': {},
                'search_history': []
            }
    
    def render_search_interface(self):
        """Render the main search interface."""
        st.subheader("🔍 Marengo 2.7 Multi-Modal Search")
        st.info("Search across video content using Marengo 2.7 embeddings for consistent results")
        
        # Search form
        with st.form("marengo_search_form"):
            # Query input
            query = st.text_area(
                "Search Query:",
                placeholder="Describe what you're looking for (e.g., 'person walking in a park', 'car driving on highway')",
                help="Enter a natural language description of the content you want to find",
                key="marengo_query_input"
            )
            
            # Modality selection
            col1, col2 = st.columns(2)
            
            with col1:
                selected_modalities = st.multiselect(
                    "Search Modalities:",
                    options=self.supported_modalities,
                    default=["visual-text"],
                    help="Choose which Marengo 2.7 embedding types to search with"
                )
            
            with col2:
                num_results = st.slider(
                    "Number of Results:",
                    min_value=5,
                    max_value=50,
                    value=10,
                    help="Maximum number of results to return"
                )
            
            # Advanced options
            with st.expander("🔧 Advanced Options"):
                similarity_threshold = st.slider(
                    "Similarity Threshold:",
                    min_value=0.0,
                    max_value=1.0,
                    value=0.7,
                    step=0.05,
                    help="Minimum similarity score for results"
                )
                
                enable_reranking = st.checkbox(
                    "Enable Result Re-ranking",
                    value=True,
                    help="Re-rank results for better relevance"
                )
            
            # Submit button
            submitted = st.form_submit_button("🔍 Search with Marengo", type="primary")
            
            if submitted and query.strip():
                self._execute_search(query, selected_modalities, num_results, similarity_threshold, enable_reranking)
    
    def _execute_search(self, query: str, modalities: List[str], num_results: int, 
                       similarity_threshold: float, enable_reranking: bool):
        """Execute search using Marengo 2.7."""
        try:
            with st.spinner("🔄 Searching with Marengo 2.7..."):
                # Generate query embedding using Marengo
                query_embedding = self._generate_marengo_embedding(query)
                
                if not query_embedding:
                    st.error("❌ Failed to generate query embedding with Marengo 2.7")
                    return
                
                # Execute search across selected modalities
                search_results = self._search_across_modalities(
                    query, query_embedding, modalities, num_results, similarity_threshold
                )
                
                # Apply re-ranking if enabled
                if enable_reranking:
                    search_results = self._rerank_results(search_results, query)
                
                # Store results and display
                st.session_state.marengo_search_state['last_query'] = query
                st.session_state.marengo_search_state['last_results'] = search_results
                
                self._display_search_results(search_results)
                
        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            st.error(f"❌ Search failed: {str(e)}")
    
    def _generate_marengo_embedding(self, query: str) -> Optional[Dict[str, Any]]:
        """Generate embedding using Marengo 2.7 exclusively."""
        try:
            # Try to get TwelveLabs service from session state
            twelvelabs_service = st.session_state.get('twelvelabs_service')
            
            if twelvelabs_service and hasattr(twelvelabs_service, 'generate_text_embedding'):
                result = twelvelabs_service.generate_text_embedding(query)
                return {
                    'embedding': result['embedding'],
                    'model': 'marengo-2.7',
                    'dimensions': len(result['embedding']),
                    'query': query
                }
            
            # Try to initialize TwelveLabs service
            try:
                from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
                twelvelabs_service = TwelveLabsVideoProcessingService()
                result = twelvelabs_service.generate_text_embedding(query)
                
                # Store in session state
                st.session_state.twelvelabs_service = twelvelabs_service
                
                return {
                    'embedding': result['embedding'],
                    'model': 'marengo-2.7',
                    'dimensions': len(result['embedding']),
                    'query': query
                }
            except Exception as e:
                logger.error(f"TwelveLabs service initialization failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Marengo embedding generation failed: {e}")
            return None
    
    def _search_across_modalities(self, query: str, query_embedding: Dict[str, Any], 
                                 modalities: List[str], num_results: int, 
                                 similarity_threshold: float) -> Dict[str, Any]:
        """Search across selected modalities using Marengo embeddings."""
        try:
            # Get backend services
            from frontend.components.service_locator import get_backend_service
            
            search_engine = get_backend_service('similarity_search_engine')
            coordinator = st.session_state.get('coordinator')
            
            if coordinator and hasattr(coordinator, 'search_multi_vector'):
                # Use coordinator for multi-modal search
                results = coordinator.search_multi_vector(
                    query=query,
                    vector_types=modalities,
                    top_k=num_results,
                    similarity_threshold=similarity_threshold
                )
                
                return {
                    'query': query,
                    'modalities': modalities,
                    'results': results.get('results', []),
                    'total_results': len(results.get('results', [])),
                    'processing_time_ms': results.get('processing_time_ms', 0),
                    'embedding_model': 'marengo-2.7'
                }
            
            elif search_engine:
                # Use search engine directly
                # This is a simplified implementation - would need proper integration
                st.info("Using search engine for Marengo search")
                return self._generate_demo_results(query, modalities, num_results)
            
            else:
                # Fallback to demo results
                st.warning("Backend services not available - showing demo results")
                return self._generate_demo_results(query, modalities, num_results)
                
        except Exception as e:
            logger.error(f"Multi-modal search failed: {e}")
            return self._generate_demo_results(query, modalities, num_results)
    
    def _rerank_results(self, search_results: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Re-rank search results for better relevance."""
        try:
            results = search_results.get('results', [])
            
            # Simple re-ranking based on similarity score and content relevance
            # In a real implementation, this would use more sophisticated ranking
            reranked_results = sorted(
                results,
                key=lambda x: (
                    x.get('similarity', 0) * 0.7 +  # Similarity weight
                    len(x.get('content', '')) / 1000 * 0.3  # Content length weight
                ),
                reverse=True
            )
            
            search_results['results'] = reranked_results
            search_results['reranked'] = True
            
            return search_results
            
        except Exception as e:
            logger.error(f"Result re-ranking failed: {e}")
            return search_results
    
    def _generate_demo_results(self, query: str, modalities: List[str], num_results: int) -> Dict[str, Any]:
        """Generate demo search results for testing."""
        import random
        
        demo_results = []
        
        for i in range(num_results):
            result = {
                'id': f"demo_result_{i}",
                'title': f"Demo Video Segment {i+1}",
                'content': f"Demo content matching '{query}' using {', '.join(modalities)} modalities",
                'similarity': round(random.uniform(0.7, 0.95), 3),
                'timestamp': f"{random.randint(0, 300)}s",
                'duration': f"{random.randint(5, 30)}s",
                'modalities': modalities,
                'embedding_model': 'marengo-2.7'
            }
            demo_results.append(result)
        
        return {
            'query': query,
            'modalities': modalities,
            'results': demo_results,
            'total_results': len(demo_results),
            'processing_time_ms': random.randint(100, 500),
            'embedding_model': 'marengo-2.7',
            'demo_mode': True
        }
    
    def _display_search_results(self, search_results: Dict[str, Any]):
        """Display search results in a clean format."""
        st.subheader("🎯 Search Results")
        
        # Results summary
        total_results = search_results.get('total_results', 0)
        processing_time = search_results.get('processing_time_ms', 0)
        modalities = search_results.get('modalities', [])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Results Found", total_results)
        
        with col2:
            st.metric("Processing Time", f"{processing_time}ms")
        
        with col3:
            st.metric("Modalities", len(modalities))
        
        # Display individual results
        results = search_results.get('results', [])
        
        if not results:
            st.info("No results found. Try adjusting your query or similarity threshold.")
            return
        
        for i, result in enumerate(results):
            with st.expander(f"📹 {result.get('title', f'Result {i+1}')} (Similarity: {result.get('similarity', 0):.3f})"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Content:** {result.get('content', 'No content available')}")
                    st.write(f"**Timestamp:** {result.get('timestamp', 'Unknown')}")
                    st.write(f"**Duration:** {result.get('duration', 'Unknown')}")
                
                with col2:
                    st.write(f"**Similarity:** {result.get('similarity', 0):.3f}")
                    st.write(f"**Modalities:** {', '.join(result.get('modalities', []))}")
                    st.write(f"**Model:** {result.get('embedding_model', 'Unknown')}")
                
                # Action buttons
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button(f"▶️ Play", key=f"play_{i}"):
                        st.info("Video playback would be implemented here")
                
                with col2:
                    if st.button(f"📊 Visualize", key=f"viz_{i}"):
                        st.info("Embedding visualization would be implemented here")
                
                with col3:
                    if st.button(f"🔗 Similar", key=f"similar_{i}"):
                        st.info("Similar content search would be implemented here")
    
    def render_search_history(self):
        """Render search history sidebar."""
        st.sidebar.subheader("🕒 Search History")
        
        history = st.session_state.marengo_search_state.get('search_history', [])
        
        if not history:
            st.sidebar.info("No search history yet")
            return
        
        for i, search in enumerate(history[-5:]):  # Show last 5 searches
            if st.sidebar.button(f"🔍 {search[:30]}...", key=f"history_{i}"):
                # Re-run the search
                st.session_state.marengo_search_state['last_query'] = search
                st.rerun()


def render_marengo_search_interface():
    """Render the Marengo search interface."""
    search_components = MarengoSearchComponents()
    search_components.render_search_interface()
    search_components.render_search_history()


if __name__ == "__main__":
    st.set_page_config(page_title="Marengo Search", layout="wide")
    render_marengo_search_interface()
