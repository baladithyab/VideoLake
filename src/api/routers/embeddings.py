"""
Embeddings API Router.

Handles embedding visualization, analysis, and multi-modal embedding generation
for the Videolake platform. Provides provider discovery, embedding generation,
and visualization tools across multiple backend types.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import numpy as np

from src.services.semantic_mapping_visualization import SemanticMappingVisualizer
from src.services.embedding_provider import (
    EmbeddingProviderFactory,
    ModalityType,
    EmbeddingRequest,
)
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


# Multi-Modal Embedding Provider Endpoints


class GenerateEmbeddingRequest(BaseModel):
    """Request model for generating embeddings."""
    modality: str = Field(..., description="Modality type: text, image, audio, video, multimodal")
    content: Any = Field(..., description="Content to embed (text, URI, or batch)")
    provider_id: Optional[str] = Field(None, description="Specific provider to use (bedrock, sagemaker, external)")
    model_id: Optional[str] = Field(None, description="Specific model ID to use")
    dimension: Optional[int] = Field(None, description="Embedding dimension (if configurable)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")


@router.get("/providers")
async def list_embedding_providers():
    """
    List all available embedding providers and their supported modalities.

    Returns information about each registered embedding provider including
    supported modalities, available models, and capabilities.
    """
    tracker = TimingTracker("list_embedding_providers")

    try:
        with tracker.time_operation("get_providers"):
            factory = EmbeddingProviderFactory()
            provider_ids = factory.get_available_providers()

        providers = []
        for provider_id in provider_ids:
            try:
                with tracker.time_operation(f"query_provider_{provider_id}"):
                    provider = factory.create_provider(provider_id)
                    capabilities = provider.get_capabilities()
                    models = provider.list_available_models()

                    providers.append({
                        "provider_id": provider.provider_id,
                        "provider_name": provider.provider_name,
                        "supported_modalities": [m.value for m in capabilities.supported_modalities],
                        "max_batch_size": capabilities.max_batch_size,
                        "supports_configurable_dimensions": capabilities.supports_configurable_dimensions,
                        "available_dimensions": capabilities.available_dimensions,
                        "typical_latency_ms": capabilities.typical_latency_ms,
                        "models": models
                    })
            except Exception as e:
                logger.error(f"Failed to query provider {provider_id}: {e}")
                providers.append({
                    "provider_id": provider_id,
                    "error": str(e)
                })

        report = tracker.finish()

        return {
            "success": True,
            "providers": providers,
            "timing_report": report.to_dict()
        }

    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}")
async def get_provider_details(provider_id: str):
    """
    Get detailed information about a specific embedding provider.

    Args:
        provider_id: The provider identifier (bedrock, sagemaker, external)

    Returns:
        Provider capabilities, available models, and health status
    """
    tracker = TimingTracker(f"get_provider_details_{provider_id}")

    try:
        factory = EmbeddingProviderFactory()

        if not factory.is_provider_available(provider_id):
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found"
            )

        with tracker.time_operation("create_provider"):
            provider = factory.create_provider(provider_id)

        with tracker.time_operation("get_capabilities"):
            capabilities = provider.get_capabilities()

        with tracker.time_operation("list_models"):
            models = provider.list_available_models()

        with tracker.time_operation("validate_connectivity"):
            health = await provider.validate_connectivity()

        report = tracker.finish()

        return {
            "success": True,
            "provider": {
                "provider_id": provider.provider_id,
                "provider_name": provider.provider_name,
                "capabilities": {
                    "supported_modalities": [m.value for m in capabilities.supported_modalities],
                    "max_batch_size": capabilities.max_batch_size,
                    "supports_configurable_dimensions": capabilities.supports_configurable_dimensions,
                    "available_dimensions": capabilities.available_dimensions,
                    "max_input_tokens": capabilities.max_input_tokens,
                    "cost_per_1k_tokens": capabilities.cost_per_1k_tokens,
                    "typical_latency_ms": capabilities.typical_latency_ms
                },
                "models": models,
                "health": health
            },
            "timing_report": report.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_embeddings(request: GenerateEmbeddingRequest):
    """
    Generate embeddings for the given content using specified or auto-selected provider.

    Supports text, image, audio, video, and multimodal content. Provider can be
    explicitly specified or auto-selected based on modality.
    """
    tracker = TimingTracker("generate_embeddings")

    try:
        # Parse modality
        with tracker.time_operation("parse_modality"):
            try:
                modality = ModalityType(request.modality.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid modality: {request.modality}. Must be one of: text, image, audio, video, multimodal"
                )

        # Get provider
        with tracker.time_operation("select_provider"):
            factory = EmbeddingProviderFactory()

            if request.provider_id:
                if not factory.is_provider_available(request.provider_id):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Provider '{request.provider_id}' not found"
                    )
                provider = factory.create_provider(request.provider_id)
            else:
                # Auto-select provider based on modality
                provider = factory.get_provider_for_modality(modality)
                if not provider:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No provider available for modality: {modality.value}"
                    )

        # Validate provider supports modality
        if not provider.supports_modality(modality):
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider.provider_id}' does not support modality: {modality.value}"
            )

        # Create embedding request
        with tracker.time_operation("generate_embeddings"):
            embedding_request = EmbeddingRequest(
                modality=modality,
                content=request.content,
                model_id=request.model_id,
                dimension=request.dimension,
                metadata=request.metadata
            )

            response = await provider.generate_embeddings(embedding_request)

        report = tracker.finish()

        return {
            "success": True,
            "embeddings": response.embeddings,
            "model_id": response.model_id,
            "modality": response.modality.value,
            "dimension": response.dimension,
            "provider": provider.provider_id,
            "processing_time_ms": response.processing_time_ms,
            "metadata": response.metadata,
            "timing_report": report.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

