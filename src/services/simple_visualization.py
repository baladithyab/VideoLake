#!/usr/bin/env python3
"""
Simple Visualization Service

Provides basic embedding visualization with dimensionality reduction.
Calculations done on service side, visualization shown on frontend.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmbeddingPoint:
    """Simple embedding point for visualization."""
    id: str
    embedding: np.ndarray
    point_type: str  # 'query', 'result'
    similarity_score: Optional[float] = None
    vector_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SimpleVisualization:
    """Simple embedding visualization service."""
    
    def __init__(self):
        """Initialize the visualization service."""
        self.reduction_methods = {
            'PCA': self._apply_pca,
            't-SNE': self._apply_tsne
        }
        logger.info("Simple visualization service initialized")
    
    def create_embedding_plot(
        self,
        query_embeddings: List[EmbeddingPoint],
        result_embeddings: List[EmbeddingPoint],
        method: str = "PCA",
        title: str = "Embedding Space Visualization"
    ) -> go.Figure:
        """Create embedding visualization plot.
        
        Args:
            query_embeddings: Query embedding points
            result_embeddings: Result embedding points
            method: Dimensionality reduction method ('PCA' or 't-SNE')
            title: Plot title
            
        Returns:
            Plotly figure
        """
        # Combine all embeddings
        all_points = query_embeddings + result_embeddings
        
        if len(all_points) < 2:
            # Return empty plot
            fig = go.Figure()
            fig.add_annotation(
                text="Need at least 2 points for visualization",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            return fig
        
        # Extract embeddings and metadata
        embeddings = np.array([point.embedding for point in all_points])
        
        # Apply dimensionality reduction
        if method in self.reduction_methods:
            reduced_embeddings = self.reduction_methods[method](embeddings)
        else:
            reduced_embeddings = self._apply_pca(embeddings)
        
        # Create visualization data
        viz_data = self._prepare_plot_data(all_points, reduced_embeddings)
        
        # Create plot
        fig = self._create_scatter_plot(viz_data, title, method)
        
        return fig
    
    def prepare_visualization_data(
        self,
        query_embeddings: List[EmbeddingPoint],
        result_embeddings: List[EmbeddingPoint],
        method: str = "PCA"
    ) -> Dict[str, Any]:
        """Prepare visualization data for frontend rendering.

        Returns:
            Dictionary with plot figure and statistics for frontend display
        """
        if not query_embeddings and not result_embeddings:
            return {"error": "No embeddings to visualize"}

        try:
            # Create plot
            fig = self.create_embedding_plot(
                query_embeddings=query_embeddings,
                result_embeddings=result_embeddings,
                method=method,
                title=f"Embedding Space ({method})"
            )

            # Calculate statistics
            stats = self._calculate_embedding_stats(query_embeddings, result_embeddings)

            return {
                "figure": fig,
                "statistics": stats,
                "method": method,
                "query_count": len(query_embeddings),
                "result_count": len(result_embeddings)
            }

        except Exception as e:
            logger.error(f"Visualization preparation failed: {e}")
            return {"error": str(e)}
    
    def create_multi_vector_comparison(
        self,
        embeddings_by_type: Dict[str, List[EmbeddingPoint]],
        method: str = "PCA"
    ) -> go.Figure:
        """Create comparison across multiple vector types."""
        from plotly.subplots import make_subplots
        
        vector_types = list(embeddings_by_type.keys())
        n_types = len(vector_types)
        
        if n_types == 0:
            return go.Figure()
        
        # Create subplots
        cols = min(n_types, 2)
        rows = (n_types + cols - 1) // cols
        
        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=vector_types,
            specs=[[{"type": "scatter"}] * cols for _ in range(rows)]
        )
        
        for i, (vector_type, embeddings) in enumerate(embeddings_by_type.items()):
            if not embeddings:
                continue
                
            row = i // cols + 1
            col = i % cols + 1
            
            # Apply dimensionality reduction
            embedding_matrix = np.array([point.embedding for point in embeddings])
            reduced = self._apply_pca(embedding_matrix)
            
            # Add scatter trace
            fig.add_trace(
                go.Scatter(
                    x=reduced[:, 0],
                    y=reduced[:, 1],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=[point.similarity_score or 0.5 for point in embeddings],
                        colorscale='viridis',
                        showscale=(i == 0)
                    ),
                    text=[f"ID: {point.id}<br>Score: {point.similarity_score:.3f}" 
                          for point in embeddings],
                    name=vector_type
                ),
                row=row, col=col
            )
        
        fig.update_layout(
            title="Multi-Vector Type Comparison",
            height=300 * rows
        )
        
        return fig
    
    def _apply_pca(self, embeddings: np.ndarray) -> np.ndarray:
        """Apply PCA dimensionality reduction."""
        pca = PCA(n_components=2, random_state=42)
        return pca.fit_transform(embeddings)
    
    def _apply_tsne(self, embeddings: np.ndarray) -> np.ndarray:
        """Apply t-SNE dimensionality reduction."""
        # Check minimum requirements for t-SNE
        n_samples = embeddings.shape[0]
        if n_samples < 4:
            # Fall back to PCA for very small datasets
            return self._apply_pca(embeddings)

        # Use PCA first if too many dimensions
        if embeddings.shape[1] > 50:
            n_components = min(50, n_samples - 1)
            pca = PCA(n_components=n_components, random_state=42)
            embeddings = pca.fit_transform(embeddings)

        # Adjust perplexity for small datasets
        perplexity = min(30, max(1, (n_samples - 1) // 3))

        try:
            tsne = TSNE(n_components=2, random_state=42, perplexity=perplexity)
            return tsne.fit_transform(embeddings)
        except Exception:
            # Fall back to PCA if t-SNE fails
            return self._apply_pca(embeddings)
    
    def _prepare_plot_data(
        self, 
        points: List[EmbeddingPoint], 
        reduced_embeddings: np.ndarray
    ) -> pd.DataFrame:
        """Prepare data for plotting."""
        data = []
        
        for i, point in enumerate(points):
            data.append({
                'id': point.id,
                'x': reduced_embeddings[i, 0],
                'y': reduced_embeddings[i, 1],
                'type': point.point_type,
                'similarity_score': point.similarity_score or 0.0,
                'vector_type': point.vector_type or 'unknown'
            })
        
        return pd.DataFrame(data)
    
    def _create_scatter_plot(
        self, 
        viz_data: pd.DataFrame, 
        title: str, 
        method: str
    ) -> go.Figure:
        """Create scatter plot from visualization data."""
        fig = go.Figure()
        
        # Color scheme
        colors = {
            'query': '#FF6B6B',    # Red
            'result': '#4ECDC4'    # Teal
        }
        
        # Add traces for each point type
        for point_type in viz_data['type'].unique():
            type_data = viz_data[viz_data['type'] == point_type]
            
            fig.add_trace(go.Scatter(
                x=type_data['x'],
                y=type_data['y'],
                mode='markers',
                marker=dict(
                    size=12 if point_type == 'query' else 8,
                    color=colors.get(point_type, '#888888'),
                    opacity=0.8,
                    line=dict(width=1, color='white')
                ),
                text=[
                    f"ID: {row['id']}<br>"
                    f"Type: {row['type']}<br>"
                    f"Vector: {row['vector_type']}<br>"
                    f"Score: {row['similarity_score']:.3f}"
                    for _, row in type_data.iterrows()
                ],
                hovertemplate='%{text}<extra></extra>',
                name=point_type.title(),
                showlegend=True
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title=f"{method} Component 1",
            yaxis_title=f"{method} Component 2",
            width=700,
            height=500,
            hovermode='closest'
        )
        
        return fig
    
    def _calculate_embedding_stats(
        self,
        query_embeddings: List[EmbeddingPoint],
        result_embeddings: List[EmbeddingPoint]
    ) -> Dict[str, Any]:
        """Calculate embedding statistics for frontend display."""
        stats = {
            "query_count": len(query_embeddings),
            "result_count": len(result_embeddings),
            "avg_similarity": 0.0,
            "vector_type_distribution": {}
        }

        if result_embeddings:
            # Calculate average similarity
            similarities = [p.similarity_score or 0 for p in result_embeddings]
            stats["avg_similarity"] = np.mean(similarities) if similarities else 0.0

            # Calculate vector type distribution
            vector_types = [p.vector_type for p in result_embeddings if p.vector_type]
            if vector_types:
                type_counts = pd.Series(vector_types).value_counts()
                stats["vector_type_distribution"] = type_counts.to_dict()

        return stats


