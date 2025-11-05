"""
Embedding Model Selector

Provides unified interface for choosing between different embedding models:
- Marengo: Multi-vector approach with separate embedding spaces
- Nova: Unified single-vector approach with one embedding space

This enables the demo to showcase both architectures side-by-side.
"""

import time
from typing import Dict, Any, List, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum

from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService, VideoEmbeddingResult
from src.services.nova_embedding import NovaEmbeddingService, NovaEmbeddingResult
from src.config.unified_config_manager import get_unified_config_manager
from src.exceptions import ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class EmbeddingModel(Enum):
    """Supported embedding models for video processing."""
    MARENGO = "marengo"  # Multi-vector: separate spaces for visual-text, visual-image, audio
    NOVA = "nova"        # Single-vector: unified space across all modalities


@dataclass
class UnifiedEmbeddingResult:
    """
    Unified result structure for both Marengo and Nova embeddings.

    Normalizes the different approaches into a common interface for comparison.
    """
    model_type: str  # "marengo" or "nova"
    embedding_approach: str  # "multi-vector" or "single-vector"

    # Embedding data
    embeddings: Dict[str, Any]  # {"visual-text": [...], "audio": [...]} OR {"unified": [...]}

    # Metadata
    source_uri: str
    model_id: str
    dimensions: Union[int, Dict[str, int]]  # 1024 (Nova) OR {"visual-text": 1024, ...} (Marengo)
    processing_time_ms: int

    # Model-specific info
    selected_vector_types: Optional[List[str]] = None  # For Marengo
    embedding_mode: Optional[str] = None  # For Nova (AUDIO_VIDEO_COMBINED, etc.)

    @property
    def total_embedding_count(self) -> int:
        """Get total number of embeddings generated."""
        return len(self.embeddings)

    @property
    def total_dimensions(self) -> int:
        """Get total dimensions across all embeddings."""
        if self.embedding_approach == "single-vector":
            return self.dimensions if isinstance(self.dimensions, int) else 1024
        else:
            return sum(self.dimensions.values()) if isinstance(self.dimensions, dict) else 0


class EmbeddingModelSelector:
    """
    Selector for choosing between Marengo and Nova embedding models.

    Provides unified interface for video processing with either approach,
    enabling side-by-side comparison in the demo.

    Example:
        # Use Marengo (multi-vector)
        selector = EmbeddingModelSelector(model=EmbeddingModel.MARENGO)
        result = selector.process_video(
            video_uri="s3://bucket/video.mp4",
            vector_types=["visual-text", "audio"]  # Choose specific embeddings
        )
        # Returns: {"visual-text": [...], "audio": [...]}

        # Use Nova (single-vector)
        selector = EmbeddingModelSelector(model=EmbeddingModel.NOVA)
        result = selector.process_video(
            video_uri="s3://bucket/video.mp4",
            embedding_mode="AUDIO_VIDEO_COMBINED"  # All modalities in one
        )
        # Returns: {"unified": [...]}
    """

    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.MARENGO,
        **model_kwargs
    ):
        """
        Initialize embedding model selector.

        Args:
            model: Which embedding model to use (MARENGO or NOVA)
            **model_kwargs: Model-specific configuration
        """
        self.model = model
        self.config_manager = get_unified_config_manager()

        # Initialize the selected model service
        if model == EmbeddingModel.MARENGO:
            self.service = TwelveLabsVideoProcessingService()
            # Try to get marengo config, use None if not available
            try:
                self.model_config = self.config_manager.config.marengo
            except AttributeError:
                self.model_config = None
            logger.info("Initialized with Marengo (multi-vector approach)")

        elif model == EmbeddingModel.NOVA:
            # Get Nova configuration from config (with fallback to defaults)
            try:
                nova_config = self.config_manager.config.nova
                model_id = model_kwargs.get('model_id', nova_config.model_id)
                embedding_dimension = model_kwargs.get('embedding_dimension', nova_config.default_dimension)
                embedding_purpose = model_kwargs.get('embedding_purpose', nova_config.embedding_purpose)
                region_name = nova_config.region
            except AttributeError:
                # Fallback to defaults if nova not in config
                model_id = model_kwargs.get('model_id', 'amazon.nova-2-multimodal-embeddings-v1:0')
                embedding_dimension = model_kwargs.get('embedding_dimension', 1024)
                embedding_purpose = model_kwargs.get('embedding_purpose', 'GENERIC_INDEX')
                region_name = model_kwargs.get('region_name', 'us-east-1')
                nova_config = None

            self.service = NovaEmbeddingService(
                model_id=model_id,
                embedding_dimension=embedding_dimension,
                embedding_purpose=embedding_purpose,
                region_name=region_name
            )
            self.model_config = nova_config
            logger.info(
                f"Initialized with Nova (single-vector approach, "
                f"{self.service.embedding_dimension}D unified space)"
            )

        else:
            raise ValueError(f"Unsupported model: {model}")

    def process_video(
        self,
        video_uri: str,
        vector_types: Optional[List[str]] = None,  # For Marengo
        embedding_mode: Optional[str] = None,  # For Nova
        **kwargs
    ) -> UnifiedEmbeddingResult:
        """
        Process video with selected embedding model.

        Args:
            video_uri: S3 URI of video
            vector_types: For Marengo - which embeddings to generate
                         (e.g., ["visual-text", "audio"])
            embedding_mode: For Nova - how to combine modalities
                           (e.g., "AUDIO_VIDEO_COMBINED")
            **kwargs: Additional processing parameters

        Returns:
            UnifiedEmbeddingResult with embeddings in normalized format
        """
        start_time = time.time()

        if self.model == EmbeddingModel.MARENGO:
            return self._process_with_marengo(video_uri, vector_types, **kwargs)

        elif self.model == EmbeddingModel.NOVA:
            return self._process_with_nova(video_uri, embedding_mode, **kwargs)

        else:
            raise ValidationError(f"Unknown model: {self.model}")

    def _process_with_marengo(
        self,
        video_uri: str,
        vector_types: Optional[List[str]],
        **kwargs
    ) -> UnifiedEmbeddingResult:
        """Process video with Marengo (multi-vector approach)."""
        start_time = time.time()

        # Use configured default if not specified
        if vector_types is None:
            vector_types = self.model_config.default_vector_types or ["visual-text"]

        logger.info(
            f"Processing video with Marengo: {video_uri}, "
            f"vector_types={vector_types}"
        )

        # Call Marengo service (generates separate embeddings)
        result: VideoEmbeddingResult = self.service.process_video_optimized(
            video_uri=video_uri,
            embedding_options=vector_types,
            **kwargs
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Extract embeddings by type
        embeddings_by_type = {}
        dimensions_by_type = {}

        for vector_type in vector_types:
            if vector_type in result.embeddings:
                embeddings_by_type[vector_type] = result.embeddings[vector_type]
                dimensions_by_type[vector_type] = 1024  # Marengo uses 1024D per type

        return UnifiedEmbeddingResult(
            model_type="marengo",
            embedding_approach="multi-vector",
            embeddings=embeddings_by_type,
            source_uri=video_uri,
            model_id=result.bedrock_model_id,
            dimensions=dimensions_by_type,
            processing_time_ms=processing_time_ms,
            selected_vector_types=vector_types,
            embedding_mode=None
        )

    def _process_with_nova(
        self,
        video_uri: str,
        embedding_mode: Optional[str],
        **kwargs
    ) -> UnifiedEmbeddingResult:
        """Process video with Nova (single unified embedding)."""
        start_time = time.time()

        # Use configured default if not specified
        if embedding_mode is None:
            if self.model_config and hasattr(self.model_config, 'default_embedding_mode'):
                embedding_mode = self.model_config.default_embedding_mode
            else:
                embedding_mode = "AUDIO_VIDEO_COMBINED"

        logger.info(
            f"Processing video with Nova: {video_uri}, "
            f"mode={embedding_mode}, dimension={self.service.embedding_dimension}D"
        )

        # Call Nova service (generates single unified embedding)
        result: NovaEmbeddingResult = self.service.generate_video_embedding(
            video_uri=video_uri,
            embedding_mode=embedding_mode,
            **kwargs
        )

        processing_time_ms = result.processing_time_ms or int((time.time() - start_time) * 1000)

        # Package as unified result
        embeddings = {
            "unified": result.embedding  # Single embedding for all modalities
        }

        return UnifiedEmbeddingResult(
            model_type="nova",
            embedding_approach="single-vector",
            embeddings=embeddings,
            source_uri=video_uri,
            model_id=result.model_id,
            dimensions=result.embedding_dimension,
            processing_time_ms=processing_time_ms,
            selected_vector_types=None,
            embedding_mode=embedding_mode
        )

    def get_model_comparison(self) -> Dict[str, Any]:
        """
        Get comparison information between Marengo and Nova.

        Returns:
            Detailed comparison for demo purposes
        """
        if self.model == EmbeddingModel.MARENGO:
            return {
                'current_model': 'marengo',
                'approach': 'multi-vector',
                'embedding_spaces': 3,
                'user_control': 'Select which vector types to generate',
                'dimensions_per_type': 1024,
                'storage_requirement': 'Higher (multiple embeddings per video)',
                'query_approach': 'Query each type separately, fuse results',
                'best_for': 'Task-specific optimization, fine-grained control'
            }
        else:
            return {
                'current_model': 'nova',
                'approach': 'single-vector',
                'embedding_spaces': 1,
                'user_control': 'Select embedding dimension and mode',
                'dimensions': self.service.embedding_dimension,
                'storage_requirement': 'Lower (single embedding per video)',
                'query_approach': 'Single query searches all modalities',
                'best_for': 'Cross-modal search, simplicity, cost optimization'
            }

    @classmethod
    def create_parallel_comparison(
        cls,
        video_uri: str,
        marengo_vector_types: List[str] = None,
        nova_dimension: int = 1024,
        nova_mode: str = "AUDIO_VIDEO_COMBINED"
    ) -> Dict[str, UnifiedEmbeddingResult]:
        """
        Process same video with both Marengo and Nova for direct comparison.

        This is useful for demo purposes to show the differences between
        multi-vector and single-vector approaches on the same content.

        Args:
            video_uri: S3 URI of video to process
            marengo_vector_types: Which Marengo vectors to generate
            nova_dimension: Nova embedding dimension
            nova_mode: Nova embedding mode

        Returns:
            Dict with 'marengo' and 'nova' results for comparison
        """
        marengo_vector_types = marengo_vector_types or ["visual-text", "visual-image", "audio"]

        results = {}

        # Process with Marengo
        try:
            marengo_selector = cls(model=EmbeddingModel.MARENGO)
            results['marengo'] = marengo_selector.process_video(
                video_uri=video_uri,
                vector_types=marengo_vector_types
            )
            logger.info(
                f"Marengo processing complete: {results['marengo'].total_embedding_count} embeddings, "
                f"{results['marengo'].total_dimensions} total dimensions"
            )
        except Exception as e:
            logger.error(f"Marengo processing failed: {str(e)}")
            results['marengo'] = {'error': str(e)}

        # Process with Nova
        try:
            nova_selector = cls(
                model=EmbeddingModel.NOVA,
                embedding_dimension=nova_dimension
            )
            results['nova'] = nova_selector.process_video(
                video_uri=video_uri,
                embedding_mode=nova_mode
            )
            logger.info(
                f"Nova processing complete: {results['nova'].total_embedding_count} embedding, "
                f"{results['nova'].total_dimensions}D unified space"
            )
        except Exception as e:
            logger.error(f"Nova processing failed: {str(e)}")
            results['nova'] = {'error': str(e)}

        return results
