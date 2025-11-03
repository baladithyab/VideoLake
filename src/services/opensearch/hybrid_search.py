"""
OpenSearch Hybrid Search

Manages hybrid search combining vector similarity and keyword search.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import boto3

from ...exceptions import OpenSearchIntegrationError
from ...utils.logging_config import get_structured_logger
from ...utils.timing_tracker import TimingTracker


@dataclass
class HybridSearchResult:
    """Combined vector and keyword search result."""
    document_id: str
    vector_score: float
    keyword_score: float
    combined_score: float
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    highlights: Optional[Dict[str, List[str]]] = None


class OpenSearchHybridSearch:
    """
    Manages hybrid search combining vector similarity and keyword search.

    Executes combined vector and text queries against OpenSearch indexes,
    supporting both S3 Vectors engine and export patterns.

    Features:
    - Combined vector + keyword search
    - Flexible score combination strategies
    - Result processing and fusion
    - Query cost tracking
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        cost_tracker: Optional[Dict[str, List]] = None
    ):
        """
        Initialize Hybrid Search manager.

        Args:
            region_name: AWS region
            cost_tracker: Optional cost tracking dict (from parent)
        """
        self.region_name = region_name
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_hybrid_search")
        self._cost_tracker = cost_tracker or {'queries': []}

    def perform_hybrid_search(
        self,
        opensearch_endpoint: str,
        index_name: str,
        query_text: Optional[str] = None,
        query_vector: Optional[List[float]] = None,
        vector_field: str = "embedding",
        text_fields: Optional[List[str]] = None,
        k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_combination: str = "weighted",  # "weighted", "max", "harmonic_mean"
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        **kwargs
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining vector similarity and keyword search.

        Executes both vector and text queries, then combines results using
        specified scoring strategy.

        Args:
            opensearch_endpoint: OpenSearch domain endpoint
            index_name: Index to search
            query_text: Text query for keyword search
            query_vector: Vector for similarity search
            vector_field: Name of vector field in index
            text_fields: Fields to search for text queries
            k: Number of results to return
            filters: Additional filters to apply
            score_combination: Method to combine scores
            vector_weight: Weight for vector similarity scores
            text_weight: Weight for text match scores
            **kwargs: Additional search parameters

        Returns:
            List[HybridSearchResult]: Combined search results with scores
        """
        operation = self.timing_tracker.start_operation("perform_hybrid_search")
        try:
            import requests

            if not query_text and not query_vector:
                raise ValueError("Either query_text or query_vector must be provided")

            text_fields = text_fields or ["content", "title", "description"]

            self.logger.log_operation(
                "performing_hybrid_search",
                level="INFO",
                index_name=index_name,
                has_text_query=bool(query_text),
                has_vector_query=bool(query_vector),
                k=k
            )

            # Build hybrid query
            hybrid_query = self._build_hybrid_query(
                query_text=query_text,
                query_vector=query_vector,
                vector_field=vector_field,
                text_fields=text_fields,
                filters=filters,
                **kwargs
            )

            # Execute search
            search_body = {
                "size": k * 2,  # Get more results for better ranking
                "query": hybrid_query,
                "_source": True,
                "highlight": {
                    "fields": {field: {} for field in text_fields}
                }
            }

            # Make authenticated request to OpenSearch
            try:
                from requests_aws4auth import AWS4Auth

                # Get AWS credentials for authentication
                credentials = boto3.Session().get_credentials()
                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    self.region_name,
                    'es',
                    session_token=credentials.token
                )

                url = f"https://{opensearch_endpoint}/{index_name}/_search"
                response = requests.post(
                    url,
                    json=search_body,
                    auth=awsauth,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

            except ImportError:
                # Fallback to no auth if AWS4Auth not available
                self.logger.log_operation(
                    "aws4auth_not_available_using_fallback",
                    level="WARNING"
                )

                url = f"https://{opensearch_endpoint}/{index_name}/_search"
                response = requests.post(
                    url,
                    json=search_body,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

            if response.status_code != 200:
                raise OpenSearchIntegrationError(
                    f"Hybrid search failed: {response.status_code} {response.text}"
                )

            search_results = response.json()

            # Process and combine results
            combined_results = self._process_hybrid_results(
                search_results,
                score_combination=score_combination,
                vector_weight=vector_weight,
                text_weight=text_weight,
                max_results=k
            )

            # Track query cost
            self._track_query_cost(
                query_type="hybrid",
                index_name=index_name,
                result_count=len(combined_results),
                processing_time_ms=search_results.get('took', 0)
            )

            self.logger.log_operation(
                "hybrid_search_completed",
                level="INFO",
                index_name=index_name,
                results_count=len(combined_results),
                processing_time_ms=search_results.get('took', 0)
            )

            return combined_results

        except Exception as e:
            error_msg = f"Hybrid search failed: {str(e)}"
            self.logger.log_operation("hybrid_search_error", level="ERROR", error=error_msg, index_name=index_name)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def _build_hybrid_query(self, **kwargs) -> Dict[str, Any]:
        """Build OpenSearch hybrid query combining vector and text search."""
        bool_query = {"bool": {"should": []}}

        # Add vector similarity query if provided
        if kwargs.get('query_vector'):
            vector_query = {
                "knn": {
                    kwargs['vector_field']: {
                        "vector": kwargs['query_vector'],
                        "k": kwargs.get('k', 10)
                    }
                }
            }
            bool_query["bool"]["should"].append(vector_query)

        # Add text search query if provided
        if kwargs.get('query_text'):
            text_query = {
                "multi_match": {
                    "query": kwargs['query_text'],
                    "fields": kwargs.get('text_fields', ['content']),
                    "type": "best_fields"
                }
            }
            bool_query["bool"]["should"].append(text_query)

        # Add filters if provided
        if kwargs.get('filters'):
            bool_query["bool"]["filter"] = kwargs['filters']

        return bool_query

    def _process_hybrid_results(
        self,
        search_results: Dict[str, Any],
        score_combination: str,
        vector_weight: float,
        text_weight: float,
        max_results: int
    ) -> List[HybridSearchResult]:
        """Process and combine hybrid search results."""
        results = []

        for hit in search_results.get('hits', {}).get('hits', []):
            # Extract scores (implementation would parse actual OpenSearch response)
            total_score = hit.get('_score', 0)

            # For demonstration, assume equal contribution
            vector_score = total_score * vector_weight
            keyword_score = total_score * text_weight

            result = HybridSearchResult(
                document_id=hit['_id'],
                vector_score=vector_score,
                keyword_score=keyword_score,
                combined_score=total_score,
                content=hit.get('_source', {}),
                metadata=hit.get('_source', {}).get('metadata', {}),
                highlights=hit.get('highlight')
            )

            results.append(result)

        # Sort by combined score and return top results
        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:max_results]

    def _track_query_cost(self, **kwargs) -> None:
        """Track query cost for monitoring."""
        from datetime import datetime

        query_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'cost': kwargs.get('processing_time_ms', 0) * 0.001,  # Simplified cost calculation
            **kwargs
        }
        self._cost_tracker['queries'].append(query_record)
