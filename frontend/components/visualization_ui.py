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
    from src.services.simple_visualization import SimpleVisualization, EmbeddingPoint
except ImportError:
    SimpleVisualization = None
    EmbeddingPoint = None


class VisualizationUI:
    """Frontend UI components for embedding visualization."""
    
    def __init__(self):
        """Initialize visualization UI."""
        if SimpleVisualization:
            self.viz_service = SimpleVisualization()
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
            st.error("Visualization service not available")
            return
        
        if not query_embeddings and not result_embeddings:
            st.info("No embeddings to visualize")
            return
        
        # Method selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            method = st.selectbox(
                "Reduction Method:",
                options=["PCA", "t-SNE"],
                help="Choose dimensionality reduction method"
            )
        
        with col2:
            st.write(f"**Points:** {len(query_embeddings)} queries, {len(result_embeddings)} results")
        
        # Get visualization data from backend service
        try:
            viz_data = self.viz_service.prepare_visualization_data(
                query_embeddings=query_embeddings,
                result_embeddings=result_embeddings,
                method=method
            )
            
            if "error" in viz_data:
                st.error(f"Visualization error: {viz_data['error']}")
                return
            
            # Display plot
            if "figure" in viz_data:
                st.plotly_chart(viz_data["figure"], use_container_width=True)
            
            # Display statistics
            if "statistics" in viz_data:
                self._render_embedding_stats(viz_data["statistics"])
            
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
            # Create comparison plot using backend service
            fig = self.viz_service.create_multi_vector_comparison(
                embeddings_by_type=embeddings_by_type,
                method=method
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


# Demo data generator for frontend use
def generate_demo_embeddings_for_ui(
    query: str, 
    vector_type: str, 
    n_results: int = 10
) -> tuple:
    """Generate demo embeddings for UI testing."""
    try:
        from src.services.simple_visualization import generate_demo_embeddings
        return generate_demo_embeddings(query, vector_type, n_results)
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
