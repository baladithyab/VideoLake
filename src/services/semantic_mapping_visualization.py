#!/usr/bin/env python3
"""
Semantic Mapping Visualization Service

This service provides interactive embedding space visualization with dimensionality reduction
techniques (PCA, t-SNE, UMAP) showing query embeddings alongside retrieved results.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import time
import json

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EmbeddingPoint:
    """Represents a point in the embedding space."""
    id: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    point_type: str  # 'query', 'result', 'reference'
    similarity_score: Optional[float] = None
    video_s3_uri: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    vector_type: Optional[str] = None


@dataclass
class VisualizationConfig:
    """Configuration for semantic mapping visualization."""
    
    # Dimensionality reduction methods
    reduction_method: str = "umap"  # 'pca', 'tsne', 'umap'
    target_dimensions: int = 2
    
    # Method-specific parameters
    pca_params: Dict[str, Any] = field(default_factory=dict)
    tsne_params: Dict[str, Any] = field(default_factory=lambda: {
        'perplexity': 30,
        'n_iter': 1000,
        'random_state': 42
    })
    umap_params: Dict[str, Any] = field(default_factory=lambda: {
        'n_neighbors': 15,
        'min_dist': 0.1,
        'random_state': 42
    })
    
    # Visualization parameters
    plot_width: int = 800
    plot_height: int = 600
    point_size: int = 8
    opacity: float = 0.7
    
    # Color schemes
    color_schemes: Dict[str, str] = field(default_factory=lambda: {
        'query': '#FF6B6B',      # Red for query points
        'result': '#4ECDC4',     # Teal for result points
        'reference': '#45B7D1',  # Blue for reference points
        'cluster': 'viridis'     # Colormap for clusters
    })
    
    # Interactive features
    enable_hover: bool = True
    enable_selection: bool = True
    enable_zoom: bool = True
    show_similarity_lines: bool = True


class SemanticMappingVisualizer:
    """Service for creating interactive semantic mapping visualizations."""
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """Initialize the semantic mapping visualizer."""
        self.config = config or VisualizationConfig()
        
        # Cache for fitted reducers
        self._fitted_reducers: Dict[str, Any] = {}
        
        logger.info(f"Semantic mapping visualizer initialized with {self.config.reduction_method}")
    
    def create_embedding_visualization(
        self,
        query_embeddings: List[EmbeddingPoint],
        result_embeddings: List[EmbeddingPoint],
        reference_embeddings: Optional[List[EmbeddingPoint]] = None,
        title: str = "Semantic Embedding Space"
    ) -> go.Figure:
        """Create an interactive embedding space visualization.
        
        Args:
            query_embeddings: Query embedding points
            result_embeddings: Search result embedding points
            reference_embeddings: Optional reference embedding points
            title: Plot title
            
        Returns:
            Plotly figure with interactive visualization
        """
        # Combine all embeddings
        all_embeddings = query_embeddings + result_embeddings
        if reference_embeddings:
            all_embeddings.extend(reference_embeddings)
        
        if len(all_embeddings) < 2:
            raise ValueError("Need at least 2 embedding points for visualization")
        
        # Extract embedding vectors
        embedding_matrix = np.array([point.embedding for point in all_embeddings])
        
        # Apply dimensionality reduction
        reduced_embeddings = self._reduce_dimensions(embedding_matrix)
        
        # Create visualization data
        viz_data = self._prepare_visualization_data(all_embeddings, reduced_embeddings)
        
        # Create the plot
        fig = self._create_interactive_plot(viz_data, title)
        
        # Add similarity connections if enabled
        if self.config.show_similarity_lines:
            self._add_similarity_connections(fig, viz_data, query_embeddings, result_embeddings)
        
        return fig
    
    def create_multi_vector_comparison(
        self,
        embeddings_by_type: Dict[str, List[EmbeddingPoint]],
        query_point: EmbeddingPoint,
        title: str = "Multi-Vector Embedding Comparison"
    ) -> go.Figure:
        """Create a comparison visualization across multiple vector types.
        
        Args:
            embeddings_by_type: Dictionary mapping vector types to embedding lists
            query_point: Query embedding point
            title: Plot title
            
        Returns:
            Plotly figure with subplots for each vector type
        """
        vector_types = list(embeddings_by_type.keys())
        n_types = len(vector_types)
        
        if n_types == 0:
            raise ValueError("No vector types provided")
        
        # Create subplots
        cols = min(n_types, 3)
        rows = (n_types + cols - 1) // cols
        
        fig = make_subplots(
            rows=rows, cols=cols,
            subplot_titles=[f"{vt.replace('-', ' ').title()}" for vt in vector_types],
            specs=[[{"type": "scatter"}] * cols for _ in range(rows)]
        )
        
        for i, (vector_type, embeddings) in enumerate(embeddings_by_type.items()):
            row = i // cols + 1
            col = i % cols + 1
            
            # Add query point to embeddings for this vector type
            all_embeddings = [query_point] + embeddings
            
            # Reduce dimensions
            embedding_matrix = np.array([point.embedding for point in all_embeddings])
            reduced_embeddings = self._reduce_dimensions(embedding_matrix)
            
            # Prepare data
            viz_data = self._prepare_visualization_data(all_embeddings, reduced_embeddings)
            
            # Add traces to subplot
            self._add_subplot_traces(fig, viz_data, row, col, vector_type)
        
        # Update layout
        fig.update_layout(
            title=title,
            height=300 * rows,
            width=self.config.plot_width,
            showlegend=True
        )
        
        return fig
    
    def create_temporal_embedding_evolution(
        self,
        temporal_embeddings: List[Tuple[float, EmbeddingPoint]],
        title: str = "Temporal Embedding Evolution"
    ) -> go.Figure:
        """Create a visualization showing how embeddings evolve over time.
        
        Args:
            temporal_embeddings: List of (timestamp, embedding_point) tuples
            title: Plot title
            
        Returns:
            Plotly figure with temporal evolution visualization
        """
        if len(temporal_embeddings) < 2:
            raise ValueError("Need at least 2 temporal points for evolution visualization")
        
        # Sort by timestamp
        temporal_embeddings.sort(key=lambda x: x[0])
        
        # Extract embeddings and timestamps
        timestamps = [t for t, _ in temporal_embeddings]
        embeddings = [point for _, point in temporal_embeddings]
        
        # Reduce dimensions
        embedding_matrix = np.array([point.embedding for point in embeddings])
        reduced_embeddings = self._reduce_dimensions(embedding_matrix)
        
        # Create the plot
        fig = go.Figure()
        
        # Add trajectory line
        fig.add_trace(go.Scatter(
            x=reduced_embeddings[:, 0],
            y=reduced_embeddings[:, 1],
            mode='lines+markers',
            line=dict(color='blue', width=2),
            marker=dict(
                size=self.config.point_size,
                color=timestamps,
                colorscale='viridis',
                colorbar=dict(title="Time"),
                showscale=True
            ),
            text=[f"Time: {t:.2f}s<br>ID: {point.id}" for t, point in temporal_embeddings],
            hovertemplate='%{text}<br>X: %{x:.3f}<br>Y: %{y:.3f}<extra></extra>',
            name='Temporal Evolution'
        ))
        
        # Add start and end markers
        fig.add_trace(go.Scatter(
            x=[reduced_embeddings[0, 0]],
            y=[reduced_embeddings[0, 1]],
            mode='markers',
            marker=dict(size=15, color='green', symbol='star'),
            name='Start',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[reduced_embeddings[-1, 0]],
            y=[reduced_embeddings[-1, 1]],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            name='End',
            showlegend=True
        ))
        
        # Update layout
        fig.update_layout(
            title=title,
            width=self.config.plot_width,
            height=self.config.plot_height,
            xaxis_title=f"{self.config.reduction_method.upper()} Component 1",
            yaxis_title=f"{self.config.reduction_method.upper()} Component 2"
        )
        
        return fig
    
    def _reduce_dimensions(self, embedding_matrix: np.ndarray) -> np.ndarray:
        """Apply dimensionality reduction to embedding matrix."""
        method = self.config.reduction_method.lower()
        
        # Check cache for fitted reducer
        cache_key = f"{method}_{embedding_matrix.shape}"
        
        if method == "pca":
            reducer = PCA(
                n_components=self.config.target_dimensions,
                **self.config.pca_params
            )
        elif method == "tsne":
            reducer = TSNE(
                n_components=self.config.target_dimensions,
                **self.config.tsne_params
            )
        elif method == "umap":
            reducer = umap.UMAP(
                n_components=self.config.target_dimensions,
                **self.config.umap_params
            )
        else:
            raise ValueError(f"Unsupported reduction method: {method}")
        
        # Fit and transform
        try:
            reduced = reducer.fit_transform(embedding_matrix)
            
            # Cache the fitted reducer for PCA (can be reused)
            if method == "pca":
                self._fitted_reducers[cache_key] = reducer
                
        except Exception as e:
            logger.error(f"Dimensionality reduction failed: {e}")
            # Fallback to PCA if other methods fail
            if method != "pca":
                logger.warning("Falling back to PCA")
                reducer = PCA(n_components=self.config.target_dimensions)
                reduced = reducer.fit_transform(embedding_matrix)
            else:
                raise
        
        return reduced
    
    def _prepare_visualization_data(
        self, 
        embeddings: List[EmbeddingPoint], 
        reduced_embeddings: np.ndarray
    ) -> pd.DataFrame:
        """Prepare data for visualization."""
        data = []
        
        for i, point in enumerate(embeddings):
            row = {
                'id': point.id,
                'x': reduced_embeddings[i, 0],
                'y': reduced_embeddings[i, 1],
                'type': point.point_type,
                'similarity_score': point.similarity_score or 0.0,
                'vector_type': point.vector_type or 'unknown',
                'video_uri': point.video_s3_uri or '',
                'start_time': point.start_time or 0.0,
                'end_time': point.end_time or 0.0
            }
            
            # Add metadata fields
            for key, value in point.metadata.items():
                row[f'meta_{key}'] = value
            
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _create_interactive_plot(self, viz_data: pd.DataFrame, title: str) -> go.Figure:
        """Create the main interactive plot."""
        fig = go.Figure()
        
        # Add traces for each point type
        for point_type in viz_data['type'].unique():
            type_data = viz_data[viz_data['type'] == point_type]
            
            # Determine color and size
            color = self.config.color_schemes.get(point_type, '#888888')
            size = self.config.point_size
            
            if point_type == 'query':
                size = self.config.point_size * 1.5
            
            # Create hover text
            hover_text = []
            for _, row in type_data.iterrows():
                text = f"ID: {row['id']}<br>"
                text += f"Type: {row['type']}<br>"
                text += f"Vector: {row['vector_type']}<br>"
                
                if row['similarity_score'] > 0:
                    text += f"Similarity: {row['similarity_score']:.3f}<br>"
                
                if row['start_time'] > 0:
                    text += f"Time: {row['start_time']:.1f}s - {row['end_time']:.1f}s<br>"
                
                hover_text.append(text)
            
            # Add trace
            fig.add_trace(go.Scatter(
                x=type_data['x'],
                y=type_data['y'],
                mode='markers',
                marker=dict(
                    size=size,
                    color=color,
                    opacity=self.config.opacity,
                    line=dict(width=1, color='white')
                ),
                text=hover_text,
                hovertemplate='%{text}<br>X: %{x:.3f}<br>Y: %{y:.3f}<extra></extra>',
                name=point_type.title(),
                showlegend=True
            ))
        
        # Update layout
        fig.update_layout(
            title=title,
            width=self.config.plot_width,
            height=self.config.plot_height,
            xaxis_title=f"{self.config.reduction_method.upper()} Component 1",
            yaxis_title=f"{self.config.reduction_method.upper()} Component 2",
            hovermode='closest' if self.config.enable_hover else False,
            dragmode='select' if self.config.enable_selection else 'zoom'
        )
        
        return fig
    
    def _add_similarity_connections(
        self,
        fig: go.Figure,
        viz_data: pd.DataFrame,
        query_embeddings: List[EmbeddingPoint],
        result_embeddings: List[EmbeddingPoint]
    ):
        """Add lines connecting query points to their most similar results."""
        query_data = viz_data[viz_data['type'] == 'query']
        result_data = viz_data[viz_data['type'] == 'result']
        
        if len(query_data) == 0 or len(result_data) == 0:
            return
        
        # For each query, connect to top similar results
        for _, query_row in query_data.iterrows():
            # Find top 3 most similar results
            similar_results = result_data.nlargest(3, 'similarity_score')
            
            for _, result_row in similar_results.iterrows():
                if result_row['similarity_score'] > 0.5:  # Only show high similarity
                    fig.add_trace(go.Scatter(
                        x=[query_row['x'], result_row['x']],
                        y=[query_row['y'], result_row['y']],
                        mode='lines',
                        line=dict(
                            color='gray',
                            width=1,
                            dash='dot'
                        ),
                        opacity=0.3,
                        showlegend=False,
                        hoverinfo='skip'
                    ))
    
    def _add_subplot_traces(
        self,
        fig: go.Figure,
        viz_data: pd.DataFrame,
        row: int,
        col: int,
        vector_type: str
    ):
        """Add traces to a subplot."""
        for point_type in viz_data['type'].unique():
            type_data = viz_data[viz_data['type'] == point_type]
            
            color = self.config.color_schemes.get(point_type, '#888888')
            size = self.config.point_size
            
            if point_type == 'query':
                size = self.config.point_size * 1.5
            
            fig.add_trace(
                go.Scatter(
                    x=type_data['x'],
                    y=type_data['y'],
                    mode='markers',
                    marker=dict(size=size, color=color, opacity=self.config.opacity),
                    name=f"{point_type.title()} ({vector_type})",
                    showlegend=(row == 1 and col == 1),  # Only show legend for first subplot
                    legendgroup=point_type
                ),
                row=row, col=col
            )
    
    def export_visualization_data(
        self,
        embeddings: List[EmbeddingPoint],
        reduced_embeddings: np.ndarray,
        filename: str
    ):
        """Export visualization data to file."""
        viz_data = self._prepare_visualization_data(embeddings, reduced_embeddings)
        
        if filename.endswith('.csv'):
            viz_data.to_csv(filename, index=False)
        elif filename.endswith('.json'):
            viz_data.to_json(filename, orient='records', indent=2)
        else:
            raise ValueError("Unsupported file format. Use .csv or .json")
        
        logger.info(f"Visualization data exported to {filename}")
    
    def get_embedding_clusters(
        self,
        embeddings: List[EmbeddingPoint],
        n_clusters: int = 5
    ) -> Dict[int, List[EmbeddingPoint]]:
        """Identify clusters in the embedding space."""
        from sklearn.cluster import KMeans
        
        embedding_matrix = np.array([point.embedding for point in embeddings])
        
        # Apply clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(embedding_matrix)
        
        # Group embeddings by cluster
        clusters = {}
        for i, label in enumerate(cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(embeddings[i])
        
        logger.info(f"Identified {len(clusters)} clusters from {len(embeddings)} embeddings")
        return clusters
