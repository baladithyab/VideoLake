"""
Embeddings API Router.

Handles embedding visualization and analysis.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np

from src.services.semantic_mapping_visualization import SemanticMappingVisualizer
from src.utils.logging_config import get_logger
from src.utils.timing_tracker import TimingTracker

logger = get_logger(__name__)

router = APIRouter()


class VisualizationRequest(BaseModel):
    """Request model for embedding visualization."""
    index_arn: str
    method: str = "PCA"  # PCA, t-SNE, UMAP
    n_components: int = 2
    query_embedding: Optional[List[float]] = None
    max_points: int = 1000


class EmbeddingAnalysisRequest(BaseModel):
    """Request model for embedding analysis."""
    embeddings: List[List[float]]
    labels: Optional[List[str]] = None


@router.post("/visualize")
async def visualize_embeddings(request: VisualizationRequest):
    """Generate embedding visualization."""
    tracker = TimingTracker("visualize_embeddings")

    try:
        with tracker.time_operation("initialize_visualizer"):
            viz_service = SemanticMappingVisualizer()

        # Prepare visualization data
        with tracker.time_operation("prepare_visualization_data"):
            viz_data = viz_service.prepare_visualization_data(
                index_arn=request.index_arn,
                method=request.method,
                n_components=request.n_components,
                query_embedding=request.query_embedding,
                max_points=request.max_points
            )

        report = tracker.finish()

        return {
            "success": True,
            "visualization": viz_data,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Visualization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_embeddings(request: EmbeddingAnalysisRequest):
    """Analyze embedding space."""
    tracker = TimingTracker("analyze_embeddings")

    try:
        with tracker.time_operation("prepare_embeddings"):
            embeddings = np.array(request.embeddings)

        # Calculate statistics
        with tracker.time_operation("calculate_statistics"):
            mean_embedding = embeddings.mean(axis=0).tolist()
            std_embedding = embeddings.std(axis=0).tolist()

        # Calculate pairwise similarities
        with tracker.time_operation("calculate_similarities"):
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(embeddings)

        report = tracker.finish()

        return {
            "success": True,
            "analysis": {
                "num_embeddings": len(embeddings),
                "dimension": len(embeddings[0]),
                "mean_embedding": mean_embedding,
                "std_embedding": std_embedding,
                "avg_similarity": float(similarities.mean()),
                "min_similarity": float(similarities.min()),
                "max_similarity": float(similarities.max())
            },
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Embedding analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/methods")
async def get_visualization_methods():
    """Get available visualization methods."""
    return {
        "success": True,
        "methods": [
            {
                "id": "PCA",
                "name": "Principal Component Analysis",
                "description": "Linear dimensionality reduction"
            },
            {
                "id": "t-SNE",
                "name": "t-Distributed Stochastic Neighbor Embedding",
                "description": "Non-linear dimensionality reduction for visualization"
            },
            {
                "id": "UMAP",
                "name": "Uniform Manifold Approximation and Projection",
                "description": "Fast non-linear dimensionality reduction"
            }
        ]
    }

