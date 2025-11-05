"""
OpenSearch Integration Manager for S3 Vectors (Facade)

This module provides a unified interface to OpenSearch integration functionality
using the Facade Pattern to coordinate specialized managers.

This file maintains 100% backward compatibility with the original API.
"""

import boto3
from datetime import datetime
from typing import Dict, List, Optional, Any
from botocore.config import Config

from .opensearch import (
    OpenSearchEngineManager,
    OpenSearchHybridSearch,
    OpenSearchCostAnalyzer,
    OpenSearchResourceManager,
    HybridSearchResult,
    CostAnalysis,
    IntegrationPattern
)
from ..exceptions import OpenSearchIntegrationError
from ..utils.logging_config import get_structured_logger
from ..utils.timing_tracker import TimingTracker
from ..utils.resource_registry import resource_registry


class OpenSearchIntegrationManager:
    """
    Manages integration between S3 Vectors and OpenSearch Service (Facade).

    Provides Engine Pattern: Use S3 Vectors as cost-effective OpenSearch storage engine

    Features:
    - S3 Vectors engine configuration for OpenSearch domains
    - Hybrid search combining vector similarity and keyword search
    - Cost monitoring and analysis

    This is a facade that delegates to specialized managers while maintaining
    backward compatibility with the original API.
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        opensearch_endpoint: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenSearch Integration Manager.

        Args:
            region_name: AWS region for services
            opensearch_endpoint: Optional OpenSearch domain endpoint
            **kwargs: Additional configuration options
        """
        self.region_name = region_name
        self.opensearch_endpoint = opensearch_endpoint
        self.logger = get_structured_logger(__name__)
        self.timing_tracker = TimingTracker("opensearch_integration")

        # Resource tracking
        self.resource_registry = resource_registry

        # Configure boto3 clients with optimization
        self.boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60,
            connect_timeout=10,
            max_pool_connections=50
        )

        # Initialize AWS service clients (for facade-level operations)
        self._init_clients()

        # Cost tracking (shared across managers)
        self._cost_tracker = {
            'exports': [],
            'queries': [],
            'storage_costs': {}
        }

        # Initialize specialized managers
        self._init_managers()

    def _init_clients(self) -> None:
        """Initialize AWS service clients."""
        try:
            session = boto3.Session(region_name=self.region_name)

            self.s3vectors_client = session.client(
                's3vectors',
                config=self.boto_config
            )

            self.opensearch_client = session.client(
                'opensearch',
                config=self.boto_config
            )

            self.opensearch_serverless_client = session.client(
                'opensearchserverless',
                config=self.boto_config
            )

            self.osis_client = session.client(
                'osis',  # OpenSearch Ingestion Service
                config=self.boto_config
            )

            self.pricing_client = session.client(
                'pricing',
                region_name='us-east-1',  # Pricing API only available in us-east-1
                config=self.boto_config
            )

            self.logger.log_operation("OpenSearch integration clients initialized successfully")

        except Exception as e:
            error_msg = f"Failed to initialize OpenSearch integration clients: {str(e)}"
            self.logger.log_error("client_initialization_failed", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def _init_managers(self) -> None:
        """Initialize specialized managers."""
        # Engine manager
        self.engine_manager = OpenSearchEngineManager(
            region_name=self.region_name,
            boto_config=self.boto_config
        )

        # Hybrid search manager (shares cost tracker)
        self.hybrid_search = OpenSearchHybridSearch(
            region_name=self.region_name,
            cost_tracker=self._cost_tracker
        )

        # Cost analyzer (shares cost tracker)
        self.cost_analyzer = OpenSearchCostAnalyzer(
            region_name=self.region_name,
            cost_tracker=self._cost_tracker
        )

        # Resource manager
        self.resource_manager = OpenSearchResourceManager(
            region_name=self.region_name,
            boto_config=self.boto_config
        )

        self.logger.log_operation("Specialized managers initialized successfully")

    # Engine Pattern Methods (delegate to EngineManager)

    def configure_s3_vectors_engine(
        self,
        domain_name: str,
        enable_s3_vectors: bool = True,
        kms_key_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Configure OpenSearch domain to use S3 Vectors as storage engine.

        Args:
            domain_name: OpenSearch domain name
            enable_s3_vectors: Whether to enable S3 vectors engine
            kms_key_id: KMS key for S3 vectors encryption
            **kwargs: Additional domain configuration options

        Returns:
            Dict[str, Any]: Domain configuration details
        """
        return self.engine_manager.configure_s3_vectors_engine(
            domain_name=domain_name,
            enable_s3_vectors=enable_s3_vectors,
            kms_key_id=kms_key_id,
            **kwargs
        )

    def create_s3_vector_index(
        self,
        opensearch_endpoint: str,
        index_name: str,
        vector_field_name: str,
        vector_dimension: int,
        space_type: str = "cosinesimil",
        additional_fields: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create OpenSearch index with S3 vector engine for vector fields.

        Args:
            opensearch_endpoint: OpenSearch domain endpoint
            index_name: Name of the index to create
            vector_field_name: Name of the vector field
            vector_dimension: Dimensionality of vectors
            space_type: Distance function ("cosine", "l2", "inner_product")
            additional_fields: Additional non-vector fields for the index
            **kwargs: Additional index configuration

        Returns:
            Dict[str, Any]: Index creation result
        """
        return self.engine_manager.create_s3_vector_index(
            opensearch_endpoint=opensearch_endpoint,
            index_name=index_name,
            vector_field_name=vector_field_name,
            vector_dimension=vector_dimension,
            space_type=space_type,
            additional_fields=additional_fields,
            **kwargs
        )

    # Hybrid Search Methods (delegate to HybridSearch)

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
        score_combination: str = "weighted",
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
        **kwargs
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining vector similarity and keyword search.

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
        return self.hybrid_search.perform_hybrid_search(
            opensearch_endpoint=opensearch_endpoint,
            index_name=index_name,
            query_text=query_text,
            query_vector=query_vector,
            vector_field=vector_field,
            text_fields=text_fields,
            k=k,
            filters=filters,
            score_combination=score_combination,
            vector_weight=vector_weight,
            text_weight=text_weight,
            **kwargs
        )

    # Cost Monitoring Methods (delegate to CostAnalyzer)

    def monitor_integration_costs(
        self,
        pattern: IntegrationPattern,
        time_period_days: int = 30,
        vector_storage_gb: Optional[float] = None,
        query_count_monthly: Optional[int] = None,
        **kwargs
    ) -> CostAnalysis:
        """
        Monitor and analyze costs for OpenSearch integration patterns.

        Args:
            pattern: Integration pattern to analyze
            time_period_days: Analysis time period
            vector_storage_gb: Estimated vector storage size in GB
            query_count_monthly: Estimated monthly query count
            **kwargs: Additional cost parameters

        Returns:
            CostAnalysis: Detailed cost analysis with recommendations
        """
        return self.cost_analyzer.monitor_integration_costs(
            pattern=pattern,
            time_period_days=time_period_days,
            vector_storage_gb=vector_storage_gb,
            query_count_monthly=query_count_monthly,
            **kwargs
        )

    def get_cost_report(
        self,
        start_date: datetime,
        end_date: datetime,
        include_projections: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive cost report for all integration activities.

        Args:
            start_date: Report start date
            end_date: Report end date
            include_projections: Whether to include cost projections

        Returns:
            Dict[str, Any]: Detailed cost report
        """
        return self.cost_analyzer.get_cost_report(
            start_date=start_date,
            end_date=end_date,
            include_projections=include_projections
        )

    # Resource Management Methods (delegate to ResourceManager)

    def get_opensearch_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all OpenSearch-related resources."""
        return self.resource_manager.get_opensearch_resource_summary()

    def cleanup_engine_resources(
        self,
        domain_name: str,
        disable_s3_vectors: bool = True,
        cleanup_indexes: bool = False
    ) -> Dict[str, Any]:
        """Clean up or reset resources used in engine pattern."""
        return self.resource_manager.cleanup_engine_resources(
            domain_name=domain_name,
            disable_s3_vectors=disable_s3_vectors,
            cleanup_indexes=cleanup_indexes,
            engine_manager=self.engine_manager  # Inject dependency
        )

    def cleanup_all_opensearch_resources(
        self,
        confirm_deletion: bool = False,
        preserve_collections: bool = True,
        preserve_domains: bool = True
    ) -> Dict[str, Any]:
        """Clean up all OpenSearch integration resources."""
        return self.resource_manager.cleanup_all_opensearch_resources(
            confirm_deletion=confirm_deletion,
            preserve_collections=preserve_collections,
            preserve_domains=preserve_domains,
            engine_manager=self.engine_manager  # Inject dependency
        )

    # Helper methods for backward compatibility

    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts', region_name=self.region_name)
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            self.logger.log_operation("Failed to get AWS account ID", level="ERROR", error=str(e))
            raise OpenSearchIntegrationError(f"Failed to get real AWS account ID: {e}")
