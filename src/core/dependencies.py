"""
FastAPI Dependency Injection.

Provides singleton instances of services for dependency injection.
Using @lru_cache ensures services are created once and reused.
"""

from functools import lru_cache
from typing import Optional

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.similarity_search_engine import SimilaritySearchEngine
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.vector_store_manager import VectorStoreManager
from src.utils.resource_registry import ResourceRegistry, resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_storage_manager() -> S3VectorStorageManager:
    """
    Get or create S3VectorStorageManager singleton.

    Returns:
        S3VectorStorageManager instance
    """
    logger.info("Initializing S3VectorStorageManager")
    return S3VectorStorageManager()


@lru_cache()
def get_search_engine() -> SimilaritySearchEngine:
    """
    Get or create SimilaritySearchEngine singleton.

    Returns:
        SimilaritySearchEngine instance
    """
    logger.info("Initializing SimilaritySearchEngine")
    return SimilaritySearchEngine()


@lru_cache()
def get_twelvelabs_service() -> TwelveLabsVideoProcessingService:
    """
    Get or create TwelveLabsVideoProcessingService singleton.

    Returns:
        TwelveLabsVideoProcessingService instance
    """
    logger.info("Initializing TwelveLabsVideoProcessingService")
    return TwelveLabsVideoProcessingService()


@lru_cache()
def get_bedrock_service() -> BedrockEmbeddingService:
    """
    Get or create BedrockEmbeddingService singleton.

    Returns:
        BedrockEmbeddingService instance
    """
    logger.info("Initializing BedrockEmbeddingService")
    return BedrockEmbeddingService()


@lru_cache()
def get_vector_store_manager() -> VectorStoreManager:
    """
    Get or create VectorStoreManager singleton.

    Returns:
        VectorStoreManager instance
    """
    logger.info("Initializing VectorStoreManager")
    return VectorStoreManager()


def get_resource_registry() -> ResourceRegistry:
    """
    Get the global ResourceRegistry instance.

    Returns:
        ResourceRegistry singleton
    """
    return resource_registry


# Lifecycle management functions
def clear_dependency_cache():
    """
    Clear the dependency injection cache.

    Useful for testing or when services need to be recreated.
    """
    logger.info("Clearing dependency injection cache")
    get_storage_manager.cache_clear()
    get_search_engine.cache_clear()
    get_twelvelabs_service.cache_clear()
    get_bedrock_service.cache_clear()
    get_vector_store_manager.cache_clear()


async def initialize_services():
    """
    Initialize all services eagerly on application startup.

    This ensures services are ready before handling requests.
    """
    logger.info("Initializing services eagerly")

    try:
        # Initialize core services
        get_storage_manager()
        get_search_engine()
        get_twelvelabs_service()
        get_bedrock_service()
        get_vector_store_manager()

        logger.info("All services initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


async def cleanup_services():
    """
    Cleanup services on application shutdown.

    Closes connections and releases resources.
    """
    logger.info("Cleaning up services")

    try:
        # Add cleanup logic here if services need explicit cleanup
        # For now, just clear the cache
        clear_dependency_cache()

        logger.info("Services cleanup completed")

    except Exception as e:
        logger.error(f"Error during service cleanup: {e}", exc_info=True)
