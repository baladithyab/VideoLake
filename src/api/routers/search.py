"""
Search API Router.

Handles multi-modal search queries and similarity search across multiple
vector store backends (S3 Vector, OpenSearch, Qdrant, LanceDB) for the
Videolake platform.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Any, Optional

from src.services.similarity_search_engine import SimilaritySearchEngine
from src.services.interfaces.search_service_interface import SearchQuery, IndexType
from src.services.multi_vector_coordinator import MultiVectorCoordinator, SearchRequest, VectorType
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger
from src.utils.timing_tracker import TimingTracker
from src.core.dependencies import get_search_engine, get_bedrock_service
from src.api.validators import (
    validate_query_text,
    validate_top_k,
    validate_backend,
    validate_index_arn,
    validate_embedding_options
)

logger = get_logger(__name__)

router = APIRouter()


class SearchQueryRequest(BaseModel):
    """Request model for search query with enhanced validation."""
    query_text: str = Field(..., description="Search query text", min_length=1, max_length=10000)
    vector_types: List[str] = Field(
        default=["visual-text", "visual-image", "audio"],
        description="Vector types to search"
    )
    top_k: int = Field(default=10, ge=1, le=1000, description="Number of results to return")
    index_arn: Optional[str] = Field(None, description="Index ARN")
    use_opensearch: bool = Field(default=False, description="Use OpenSearch backend")
    backend: Optional[str] = Field(None, description="Backend: s3_vector, opensearch, lancedb, qdrant")

    @validator('query_text')
    def validate_query(cls, v):
        return validate_query_text(v)

    @validator('top_k')
    def validate_k(cls, v):
        return validate_top_k(v)

    @validator('backend')
    def validate_backend_name(cls, v):
        return validate_backend(v)

    @validator('index_arn')
    def validate_arn(cls, v):
        return validate_index_arn(v)

    @validator('vector_types')
    def validate_types(cls, v):
        return validate_embedding_options(v)


class MultiVectorSearchRequest(BaseModel):
    """Request model for multi-vector search with enhanced validation."""
    query_text: str = Field(..., min_length=1, max_length=10000)
    vector_types: List[str] = Field(default=["visual-text", "visual-image", "audio"])
    top_k: int = Field(default=10, ge=1, le=1000)
    enable_reranking: bool = True

    @validator('query_text')
    def validate_query(cls, v):
        return validate_query_text(v)

    @validator('top_k')
    def validate_k(cls, v):
        return validate_top_k(v)

    @validator('vector_types')
    def validate_types(cls, v):
        return validate_embedding_options(v)


@router.post("/query")
async def search_query(
    request: SearchQueryRequest,
    search_engine: SimilaritySearchEngine = Depends(get_search_engine)
):
    """
    Execute search query on specified backend.

    Videolake supports multiple vector store backends:
    - s3_vector: AWS S3 Vector (native AWS service)
    - opensearch: OpenSearch with S3Vector backend integration
    - lancedb: LanceDB columnar database
    - qdrant: Qdrant cloud-native vector database
    """
    tracker = TimingTracker("search_query")

    try:
        # Determine backend
        backend = request.backend or ("opensearch" if request.use_opensearch else "s3_vector")

        with tracker.time_operation(f"prepare_query_{backend}"):
            # Map backend string to IndexType for compatibility
            # For now, using MARENGO_MULTIMODAL as default since it supports all query types
            backend_map = {
                "s3_vector": IndexType.MARENGO_MULTIMODAL,
                "opensearch": IndexType.MARENGO_MULTIMODAL,
                "lancedb": IndexType.MARENGO_MULTIMODAL,
                "qdrant": IndexType.MARENGO_MULTIMODAL
            }
            
            query = SearchQuery(
                query_text=request.query_text,
                top_k=request.top_k,
                backend=backend,
                extract_entities=True,
                expand_synonyms=True
            )

        # Execute search using find_similar_content
        with tracker.time_operation(f"execute_search_{backend}"):
            index_type = backend_map.get(backend, IndexType.MARENGO_MULTIMODAL)
            index_arn = request.index_arn or "default"
            
            results = search_engine.find_similar_content(
                query=query,
                index_arn=index_arn,
                index_type=index_type
            )

        report = tracker.finish()

        return {
            "success": True,
            "backend": backend,
            "results": [
                {
                    "id": r.key,
                    "score": r.similarity_score,
                    "metadata": r.metadata,
                    "content_type": r.content_type
                }
                for r in results.results
            ],
            "query_time_ms": results.processing_time_ms,
            "total_results": results.total_results,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Search query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-vector")
async def multi_vector_search(request: MultiVectorSearchRequest):
    """Execute multi-vector search."""
    tracker = TimingTracker("multi_vector_search")

    try:
        with tracker.time_operation("initialize_coordinator"):
            coordinator = MultiVectorCoordinator()

            # Create search request
            search_request = SearchRequest(
                query_text=request.query_text,
                vector_types=[VectorType(vt) for vt in request.vector_types],
                top_k=request.top_k,
                enable_reranking=request.enable_reranking
            )

        # Execute search
        with tracker.time_operation("execute_multi_vector_search"):
            results = coordinator.search(search_request)

        report = tracker.finish()

        return {
            "success": True,
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "metadata": r.metadata,
                    "vector_type": r.vector_type,
                    "source": r.source
                }
                for r in results.results
            ],
            "query_time_ms": results.query_time_ms,
            "total_results": results.total_results,
            "vector_type_breakdown": results.vector_type_breakdown,
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Multi-vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-embedding")
async def generate_embedding(text: str, model_id: Optional[str] = None):
    """Generate embedding for text query."""
    tracker = TimingTracker("generate_embedding")

    try:
        with tracker.time_operation("bedrock_embedding_generation"):
            bedrock_service = BedrockEmbeddingService()
            result = bedrock_service.generate_text_embedding(
                text=text,
                model_id=model_id
            )

        report = tracker.finish()

        return {
            "success": True,
            "embedding": result.embedding,
            "model_id": result.model_id,
            "dimension": len(result.embedding),
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-vector-types")
async def get_supported_vector_types():
    """Get list of supported vector types."""
    from src.shared.vector_types import list_supported_vector_types
    
    try:
        vector_types = list_supported_vector_types()
        return {
            "success": True,
            "vector_types": vector_types
        }
    except Exception as e:
        logger.error(f"Failed to get vector types: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dual-pattern")
async def dual_pattern_search(request: SearchQueryRequest):
    """Execute dual pattern search (S3Vector + OpenSearch)."""
    tracker = TimingTracker("dual_pattern_search")

    try:
        search_engine = SimilaritySearchEngine()

        # Execute S3Vector search
        with tracker.time_operation("s3vector_search"):
            s3_query = SimilarityQuery(
                query_text=request.query_text,
                top_k=request.top_k,
                index_type=IndexType.S3_VECTOR
            )
            s3_results = search_engine.search(query=s3_query, index_arn=request.index_arn)

        # Execute OpenSearch search
        with tracker.time_operation("opensearch_search"):
            os_query = SimilarityQuery(
                query_text=request.query_text,
                top_k=request.top_k,
                index_type=IndexType.OPENSEARCH
            )
            os_results = search_engine.search(query=os_query)

        report = tracker.finish()

        return {
            "success": True,
            "s3vector": {
                "results": [
                    {
                        "id": r.id,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in s3_results.results
                ],
                "query_time_ms": s3_results.query_time_ms
            },
            "opensearch": {
                "results": [
                    {
                        "id": r.id,
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in os_results.results
                ],
                "query_time_ms": os_results.query_time_ms
            },
            "timing_report": report.to_dict()
        }
    except Exception as e:
        logger.error(f"Dual pattern search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backends")
async def list_backends():
    """
    List all available vector store backends.

    Videolake supports multiple backends for performance comparison:
    - s3_vector: AWS S3 Vector (native AWS service)
    - opensearch: OpenSearch with S3Vector backend integration
    - lancedb: LanceDB columnar database for high-performance queries
    - qdrant: Qdrant cloud-native vector database with advanced filtering
    """
    from src.services.vector_store_manager import VectorStoreManager

    try:
        manager = VectorStoreManager()
        available_types = manager.get_available_store_types()

        backends = []
        descriptions = {
            "s3_vector": "AWS-native vector storage with S3 integration",
            "opensearch": "Hybrid search with vector and keyword capabilities",
            "lancedb": "High-performance columnar vector database",
            "qdrant": "Cloud-native vector database with advanced filtering"
        }

        for backend_type in available_types:
            backends.append({
                "type": backend_type,
                "name": backend_type.upper().replace("_", " "),
                "description": descriptions.get(backend_type, "Vector database backend"),
                "available": True
            })

        return {
            "success": True,
            "backends": backends,
            "total": len(backends)
        }

    except Exception as e:
        logger.error(f"Failed to list backends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-backends")
async def compare_backends(
    query_text: str,
    backends: Optional[List[str]] = None,
    top_k: int = 10,
    index_arn: Optional[str] = None
):
    """
    Compare query performance across multiple backends.

    Videolake's key feature - compare the same query across different
    vector store backends to analyze performance and accuracy trade-offs.

    Args:
        query_text: Search query
        backends: List of backends to compare (defaults to all)
        top_k: Number of results per backend
        index_arn: Optional index ARN for backends that need it

    Returns:
        Results and timing comparison for each backend
    """
    tracker = TimingTracker("compare_backends")

    try:
        # Default to all backends if not specified
        if not backends:
            backends = ["s3_vector", "opensearch", "lancedb", "qdrant"]

        search_engine = SimilaritySearchEngine()
        backend_results = {}

        # Query each backend
        for backend in backends:
            with tracker.time_operation(f"query_{backend}"):
                try:
                    backend_map = {
                        "s3_vector": IndexType.S3_VECTOR,
                        "opensearch": IndexType.OPENSEARCH,
                        "lancedb": IndexType.S3_VECTOR,
                        "qdrant": IndexType.S3_VECTOR
                    }

                    query = SimilarityQuery(
                        query_text=query_text,
                        top_k=top_k,
                        index_type=backend_map.get(backend, IndexType.S3_VECTOR)
                    )

                    results = search_engine.search(query=query, index_arn=index_arn)

                    backend_results[backend] = {
                        "success": True,
                        "results": [
                            {
                                "id": r.id,
                                "score": r.score,
                                "metadata": r.metadata
                            }
                            for r in results.results
                        ],
                        "query_time_ms": results.query_time_ms,
                        "result_count": len(results.results)
                    }

                except Exception as e:
                    logger.error(f"Backend {backend} query failed: {e}")
                    backend_results[backend] = {
                        "success": False,
                        "error": str(e),
                        "query_time_ms": 0,
                        "result_count": 0
                    }

        report = tracker.finish()

        # Calculate comparison statistics
        latencies = {
            k: v["query_time_ms"]
            for k, v in backend_results.items()
            if v.get("success") and v.get("query_time_ms", 0) > 0
        }

        comparison = {}
        if latencies:
            fastest = min(latencies, key=latencies.get)
            slowest = max(latencies, key=latencies.get)

            comparison = {
                "fastest_backend": fastest,
                "fastest_latency_ms": latencies[fastest],
                "slowest_backend": slowest,
                "slowest_latency_ms": latencies[slowest],
                "latency_range_ms": latencies[slowest] - latencies[fastest],
                "average_latency_ms": sum(latencies.values()) / len(latencies),
                "all_latencies": latencies
            }

        return {
            "success": True,
            "query": query_text,
            "backends": backends,
            "results": backend_results,
            "comparison": comparison,
            "timing_report": report.to_dict()
        }

    except Exception as e:
        logger.error(f"Backend comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

