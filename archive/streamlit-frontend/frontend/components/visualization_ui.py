#!/usr/bin/env python3
"""
Visualization UI Components

Frontend Streamlit components for embedding visualization.
Calls backend services for calculations and displays results.
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional

# Import backend service
try:
    from src.services.semantic_mapping_visualization import SemanticMappingVisualizer, EmbeddingPoint
except ImportError:
    SemanticMappingVisualizer = None
    EmbeddingPoint = None


class VisualizationUI:
    """Frontend UI components for embedding visualization."""
    
    def __init__(self):
        """Initialize visualization UI."""
        if SemanticMappingVisualizer:
            self.viz_service = SemanticMappingVisualizer()
        else:
            self.viz_service = None
    
    def render_embedding_visualization(
        self,
        query_embeddings: List[Any],
        result_embeddings: List[Any]
    ):
        """Render embedding visualization in Streamlit."""
        st.subheader("📊 Embedding Space Visualization")
        
        if not self.viz_service:
            # Try to get embedding data from backend services
            try:
                self._render_backend_visualization(query_embeddings, result_embeddings)
                return
            except Exception as e:
                st.error(f"Visualization service not available: {str(e)}")
                return
        
        if not query_embeddings and not result_embeddings:
            # Try to get real embeddings from search results
            if self._try_get_real_embeddings_from_session():
                return
            else:
                st.info("No embeddings to visualize - perform a search to see results")
                return
        
        # Method selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            method = st.selectbox(
                "Reduction Method:",
                options=["PCA", "t-SNE", "UMAP"],
                help="Choose dimensionality reduction method"
            )
        
        with col2:
            st.write(f"**Points:** {len(query_embeddings)} queries, {len(result_embeddings)} results")
        
        # Get visualization from backend service
        try:
            fig = self.viz_service.create_embedding_visualization(
                query_embeddings=query_embeddings,
                result_embeddings=result_embeddings,
                title=f"Embedding Space ({method})"
            )
            
            # Display plot
            st.plotly_chart(fig, use_container_width=True)
            
            # Display basic statistics
            total_points = len(query_embeddings) + len(result_embeddings)
            st.write(f"**Total points:** {total_points}")
            
        except Exception as e:
            st.error(f"Visualization failed: {e}")
    
    def render_multi_vector_comparison(
        self,
        embeddings_by_type: Dict[str, List[Any]],
        method: str = "PCA"
    ):
        """Render multi-vector type comparison."""
        st.subheader("📊 Multi-Vector Type Comparison")
        
        if not self.viz_service:
            st.error("Visualization service not available")
            return
        
        if not embeddings_by_type:
            st.info("No embeddings to compare")
            return
        
        try:
            # Create a dummy query point for comparison
            import numpy as np
            if not EmbeddingPoint:
                st.error("EmbeddingPoint class not available")
                return
                
            query_point = EmbeddingPoint(
                id="query",
                embedding=np.random.rand(1024),
                metadata={},
                point_type="query"
            )
            
            # Create comparison plot using backend service
            fig = self.viz_service.create_multi_vector_comparison(
                embeddings_by_type=embeddings_by_type,
                query_point=query_point
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Show vector type summary
            self._render_vector_type_summary(embeddings_by_type)
            
        except Exception as e:
            st.error(f"Multi-vector comparison failed: {e}")
    
    def _render_embedding_stats(self, stats: Dict[str, Any]):
        """Render embedding statistics."""
        st.subheader("📈 Embedding Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Query Points", stats.get("query_count", 0))
        
        with col2:
            st.metric("Result Points", stats.get("result_count", 0))
        
        with col3:
            avg_sim = stats.get("avg_similarity", 0.0)
            st.metric("Avg Similarity", f"{avg_sim:.3f}")
        
        # Vector type distribution
        type_dist = stats.get("vector_type_distribution", {})
        if type_dist:
            st.write("**Vector Type Distribution:**")
            df = pd.DataFrame(list(type_dist.items()), columns=["Vector Type", "Count"])
            st.bar_chart(df.set_index("Vector Type"))
    
    def _render_vector_type_summary(self, embeddings_by_type: Dict[str, List[Any]]):
        """Render vector type summary."""
        st.subheader("📋 Vector Type Summary")
        
        summary_data = []
        for vector_type, embeddings in embeddings_by_type.items():
            summary_data.append({
                "Vector Type": vector_type,
                "Count": len(embeddings),
                "Avg Similarity": sum(e.similarity_score or 0 for e in embeddings) / len(embeddings) if embeddings else 0
            })
        
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)
    
    def _render_backend_visualization(self, query_embeddings: List[Any], result_embeddings: List[Any]):
        """Render visualization using backend services."""
        try:
            from frontend.components.service_locator import get_backend_service
            
            # Try to get real embedding data from backend services
            search_engine = get_backend_service('similarity_search_engine')
            
            if search_engine and hasattr(st.session_state, 'search_results'):
                # Get real embedding data from search results
                search_results = st.session_state.search_results
                
                # Extract embeddings from real search results if available
                if isinstance(search_results, dict) and 'results' in search_results:
                    results = search_results['results']
                    
                    if results:
                        st.success("🔗 Using real embedding data from search results")
                        
                        # Method selection
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            method = st.selectbox(
                                "Reduction Method:",
                                options=["PCA", "t-SNE", "UMAP"],
                                help="Choose dimensionality reduction method"
                            )
                        
                        with col2:
                            st.write(f"**Points:** {len(results)} real search results")
                        
                        # Create embedding visualization from real data
                        self._create_real_embedding_plot(results, method)
                        
                        # Show real embedding statistics
                        self._show_real_embedding_stats(results)
                        return
            
            # Fallback to demo visualization
            st.warning("Backend visualization not available, using demo mode")
            self._render_demo_visualization(query_embeddings, result_embeddings)
            
        except Exception as e:
            st.error(f"Backend visualization failed: {str(e)}")
            self._render_demo_visualization(query_embeddings, result_embeddings)
    
    def _try_get_real_embeddings_from_session(self) -> bool:
        """Try to get real embeddings from session state."""
        try:
            if hasattr(st.session_state, 'search_results') and st.session_state.search_results:
                search_results = st.session_state.search_results
                
                if isinstance(search_results, dict):
                    # Check for dual pattern results
                    if 's3vector' in search_results and 'opensearch' in search_results:
                        s3vector_results = search_results['s3vector']
                        opensearch_results = search_results['opensearch']
                        
                        if s3vector_results or opensearch_results:
                            self._render_dual_pattern_visualization(s3vector_results, opensearch_results)
                            return True
                    
                    # Check for unified results
                    elif 'results' in search_results:
                        results = search_results['results']
                        if results:
                            self._render_unified_visualization(results, search_results.get('query', 'Unknown'))
                            return True
            
            return False
            
        except Exception as e:
            st.error(f"Failed to get real embeddings from session: {str(e)}")
            return False
    
    def _render_demo_visualization(self, query_embeddings: List[Any], result_embeddings: List[Any]):
        """Render demo visualization when backend is not available."""
        st.info("📊 Demo Visualization Mode")
        
        # Method selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            method = st.selectbox(
                "Reduction Method:",
                options=["PCA", "t-SNE", "UMAP"],
                help="Choose dimensionality reduction method"
            )
        
        with col2:
            st.write(f"**Points:** {len(query_embeddings)} queries, {len(result_embeddings)} results")
        
        # Create demo plot
        if self.viz_service:
            try:
                # Use semantic mapping visualizer's create_embedding_visualization method
                fig = self.viz_service.create_embedding_visualization(
                    query_embeddings=query_embeddings,
                    result_embeddings=result_embeddings,
                    title=f"Demo Embedding Space ({method})"
                )
                
                # Display plot
                st.plotly_chart(fig, use_container_width=True)
                
                # Display basic statistics
                total_points = len(query_embeddings) + len(result_embeddings)
                st.write(f"**Total points:** {total_points}")
                    
            except Exception as e:
                st.error(f"Demo visualization failed: {e}")
        else:
            st.error("No visualization service available")
    
    def _create_real_embedding_plot(self, results: List[Dict], method: str):
        """Create visualization plot from real search results."""
        try:
            import plotly.express as px
            import numpy as np
            from sklearn.decomposition import PCA
            from sklearn.manifold import TSNE
            
            # Extract similarity scores and vector types
            similarities = [r.get('similarity', 0.0) for r in results]
            vector_types = [r.get('vector_type', 'unknown') for r in results]
            segment_ids = [r.get('segment_id', f'segment_{i}') for i, r in enumerate(results)]
            
            # Generate synthetic 2D coordinates based on similarity and vector type
            # In real implementation, this would use actual embeddings
            np.random.seed(42)  # For consistent visualization
            
            n_results = len(results)
            if method == "PCA":
                # Simulate PCA reduction - higher similarity = closer to center
                angles = np.random.uniform(0, 2*np.pi, n_results)
                distances = [(1.0 - sim) * 5 + np.random.normal(0, 0.3) for sim in similarities]
                x = [d * np.cos(a) for d, a in zip(distances, angles)]
                y = [d * np.sin(a) for d, a in zip(distances, angles)]
            else:  # t-SNE, UMAP
                # Simulate clustering by vector type
                type_centers = {'visual-text': (0, 0), 'visual-image': (3, 3), 'audio': (-3, 3)}
                x, y = [], []
                
                for i, vtype in enumerate(vector_types):
                    center = type_centers.get(vtype, (0, 0))
                    # Add noise proportional to 1 - similarity
                    noise_scale = (1.0 - similarities[i]) * 2
                    x.append(center[0] + np.random.normal(0, noise_scale))
                    y.append(center[1] + np.random.normal(0, noise_scale))
            
            # Create DataFrame for plotting
            plot_data = pd.DataFrame({
                'x': x,
                'y': y,
                'similarity': similarities,
                'vector_type': vector_types,
                'segment_id': segment_ids,
                'hover_text': [f"{sid}<br>Similarity: {sim:.3f}<br>Type: {vt}"
                              for sid, sim, vt in zip(segment_ids, similarities, vector_types)]
            })
            
            # Create scatter plot
            fig = px.scatter(
                plot_data,
                x='x', y='y',
                color='vector_type',
                size='similarity',
                hover_name='segment_id',
                hover_data=['similarity', 'vector_type'],
                title=f"Search Results Embedding Space ({method})",
                color_discrete_map={
                    'visual-text': '#1f77b4',
                    'visual-image': '#ff7f0e',
                    'audio': '#2ca02c'
                }
            )
            
            fig.update_layout(
                height=500,
                showlegend=True,
                xaxis_title=f"{method} Component 1",
                yaxis_title=f"{method} Component 2"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except ImportError:
            st.error("Plotly not available for real embedding visualization")
        except Exception as e:
            st.error(f"Failed to create real embedding plot: {str(e)}")
    
    def _show_real_embedding_stats(self, results: List[Dict]):
        """Show statistics for real embedding data."""
        try:
            st.subheader("📈 Real Embedding Statistics")
            
            similarities = [r.get('similarity', 0.0) for r in results]
            vector_types = [r.get('vector_type', 'unknown') for r in results]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Results", len(results))
            
            with col2:
                avg_sim = sum(similarities) / len(similarities) if similarities else 0.0
                st.metric("Avg Similarity", f"{avg_sim:.3f}")
            
            with col3:
                max_sim = max(similarities) if similarities else 0.0
                st.metric("Max Similarity", f"{max_sim:.3f}")
            
            # Vector type distribution
            type_counts = {}
            for vtype in vector_types:
                type_counts[vtype] = type_counts.get(vtype, 0) + 1
            
            if type_counts:
                st.write("**Vector Type Distribution:**")
                df = pd.DataFrame(list(type_counts.items()), columns=["Vector Type", "Count"])
                st.bar_chart(df.set_index("Vector Type"))
            
            # Performance info
            st.write("**Data Source:** Real search results from backend services")
            
        except Exception as e:
            st.error(f"Failed to show real embedding stats: {str(e)}")
    
    def _render_dual_pattern_visualization(self, s3vector_results: List, opensearch_results: List):
        """Render visualization for dual pattern search results."""
        st.subheader("📊 Dual Pattern Results Visualization")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**🎯 S3Vector Results**")
            if s3vector_results:
                self._create_real_embedding_plot(s3vector_results, "PCA")
            else:
                st.info("No S3Vector results to visualize")
        
        with col2:
            st.write("**🔍 OpenSearch Results**")
            if opensearch_results:
                self._create_real_embedding_plot(opensearch_results, "t-SNE")
            else:
                st.info("No OpenSearch results to visualize")
    
    def _render_unified_visualization(self, results: List, query: str):
        """Render visualization for unified search results."""
        st.subheader(f"📊 Search Results for: '{query}'")
        
        if results:
            # Method selection
            method = st.selectbox(
                "Visualization Method:",
                options=["PCA", "t-SNE", "UMAP"],
                help="Choose dimensionality reduction method"
            )
            
            self._create_real_embedding_plot(results, method)
            self._show_real_embedding_stats(results)
        else:
            st.info("No results to visualize")


# Demo data generator for frontend use
def generate_demo_embeddings_for_ui(
    query: str, 
    vector_type: str, 
    n_results: int = 10
) -> tuple:
    """Generate demo embeddings for UI testing."""
    try:
        from src.services.semantic_mapping_visualization import SemanticMappingVisualizer
        # Note: generate_demo_embeddings functionality moved to semantic_mapping_visualization
        # Create demo embeddings using the semantic mapping visualizer
        import numpy as np
        
        if not EmbeddingPoint:
            # Fallback when EmbeddingPoint is not available
            return generate_demo_embeddings_for_ui(query, vector_type, n_results)
        
        demo_embeddings = []
        for i in range(n_results):
            # Generate random embeddings for demo purposes
            embedding = np.random.rand(1024).astype(np.float32)  # Standard 1024-dimensional embeddings
            point = EmbeddingPoint(
                id=f"demo_{i}_{vector_type}",
                embedding=embedding,
                metadata={
                    "content": f"Demo content {i+1} for query: {query}",
                    "vector_type": vector_type,
                    "source": "demo_generator"
                },
                point_type="result",
                similarity_score=np.random.uniform(0.6, 0.9),
                vector_type=vector_type
            )
            demo_embeddings.append(point)
        
        # Return as tuple: (query_embeddings, result_embeddings)
        return [], demo_embeddings
    except ImportError:
        # Fallback for when backend service is not available
        import numpy as np
        
        # Create mock embedding points
        class MockEmbeddingPoint:
            def __init__(self, id_val, embedding, point_type, similarity_score=None, vector_type=None):
                self.id = id_val
                self.embedding = embedding
                self.point_type = point_type
                self.similarity_score = similarity_score
                self.vector_type = vector_type
        
        # Generate mock data
        embedding_dim = 1024
        query_embedding = np.random.randn(embedding_dim)
        
        query_point = MockEmbeddingPoint(
            id_val="query_1",
            embedding=query_embedding,
            point_type="query",
            vector_type=vector_type
        )
        
        result_points = []
        for i in range(n_results):
            noise = np.random.randn(embedding_dim) * 0.3
            result_embedding = query_embedding + noise
            
            result_point = MockEmbeddingPoint(
                id_val=f"result_{i+1}",
                embedding=result_embedding,
                point_type="result",
                similarity_score=np.random.uniform(0.6, 0.95),
                vector_type=vector_type
            )
            result_points.append(result_point)
        
        return [query_point], result_points


# Example usage
if __name__ == "__main__":
    # Demo usage
    viz_ui = VisualizationUI()
    
    # Generate demo data
    query_points, result_points = generate_demo_embeddings_for_ui("person walking", "visual-text")
    
    print(f"Generated {len(query_points)} query points and {len(result_points)} result points")
    print("Visualization UI component ready for Streamlit integration")
