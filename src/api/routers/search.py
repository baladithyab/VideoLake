"""
Search API Router.

Handles multi-modal search queries and similarity search.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery, IndexType
from src.services.multi_vector_coordinator import MultiVectorCoordinator, SearchRequest, VectorType
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


class SearchQueryRequest(BaseModel):
    """Request model for search query."""
    query_text: str
    vector_types: List[str] = ["visual-text", "visual-image", "audio"]
    top_k: int = 10
    index_arn: Optional[str] = None
    use_opensearch: bool = False


class MultiVectorSearchRequest(BaseModel):
    """Request model for multi-vector search."""
    query_text: str
    vector_types: List[str] = ["visual-text", "visual-image", "audio"]
    top_k: int = 10
    enable_reranking: bool = True


@router.post("/query")
async def search_query(request: SearchQueryRequest):
    """Execute search query."""
    try:
        search_engine = SimilaritySearchEngine()
        
        # Create query
        query = SimilarityQuery(
            query_text=request.query_text,
            top_k=request.top_k,
            index_type=IndexType.S3_VECTOR if not request.use_opensearch else IndexType.OPENSEARCH
        )
        
        # Execute search
        results = search_engine.search(
            query=query,
            index_arn=request.index_arn
        )
        
        return {
            "success": True,
            "results": [
                {
                    "id": r.id,
                    "score": r.score,
                    "metadata": r.metadata,
                    "vector_type": r.vector_type
                }
                for r in results.results
            ],
            "query_time_ms": results.query_time_ms,
            "total_results": results.total_results
        }
    except Exception as e:
        logger.error(f"Search query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-vector")
async def multi_vector_search(request: MultiVectorSearchRequest):
    """Execute multi-vector search."""
    try:
        coordinator = MultiVectorCoordinator()
        
        # Create search request
        search_request = SearchRequest(
            query_text=request.query_text,
            vector_types=[VectorType(vt) for vt in request.vector_types],
            top_k=request.top_k,
            enable_reranking=request.enable_reranking
        )
        
        # Execute search
        results = coordinator.search(search_request)
        
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
            "vector_type_breakdown": results.vector_type_breakdown
        }
    except Exception as e:
        logger.error(f"Multi-vector search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-embedding")
async def generate_embedding(text: str, model_id: Optional[str] = None):
    """Generate embedding for text query."""
    try:
        bedrock_service = BedrockEmbeddingService()
        result = bedrock_service.generate_text_embedding(
            text=text,
            model_id=model_id
        )
        
        return {
            "success": True,
            "embedding": result.embedding,
            "model_id": result.model_id,
            "dimension": len(result.embedding)
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
    try:
        search_engine = SimilaritySearchEngine()
        
        # Execute S3Vector search
        s3_query = SimilarityQuery(
            query_text=request.query_text,
            top_k=request.top_k,
            index_type=IndexType.S3_VECTOR
        )
        s3_results = search_engine.search(query=s3_query, index_arn=request.index_arn)
        
        # Execute OpenSearch search
        os_query = SimilarityQuery(
            query_text=request.query_text,
            top_k=request.top_k,
            index_type=IndexType.OPENSEARCH
        )
        os_results = search_engine.search(query=os_query)
        
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
            }
        }
    except Exception as e:
        logger.error(f"Dual pattern search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

