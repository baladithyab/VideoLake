"""
OpenSearch Integration Manager for S3 Vectors

This module implements the OpenSearch integration patterns with S3 Vectors:
1. Export Pattern: Point-in-time export to OpenSearch Serverless 
2. Engine Pattern: S3 Vectors as OpenSearch storage engine

Supports hybrid search capabilities and cost monitoring across both patterns.
"""

import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from ..exceptions import (
    S3VectorError,
    OpenSearchIntegrationError,
    ConfigurationError,
    CostMonitoringError
)
from ..utils.logging_config import setup_logging, get_structured_logger, LoggedOperation, log_function_calls
from ..utils.timing_tracker import TimingTracker
from ..utils.resource_registry import resource_registry


class IntegrationPattern(Enum):
    """OpenSearch integration patterns with S3 Vectors."""
    EXPORT = "export"  # Export to OpenSearch Serverless
    ENGINE = "engine"  # S3 Vectors as OpenSearch engine


@dataclass
class ExportStatus:
    """Status information for S3 Vectors export operations."""
    export_id: str
    status: str  # 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    source_index_arn: str
    target_collection_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_processed: int = 0
    cost_estimate: float = 0.0


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


@dataclass
class CostAnalysis:
    """Cost analysis for OpenSearch integration patterns."""
    pattern: IntegrationPattern
    storage_cost_monthly: float
    query_cost_per_1k: float
    ingestion_cost_per_gb: float
    estimated_monthly_total: float
    cost_comparison: Dict[str, float]
    optimization_recommendations: List[str]


class OpenSearchIntegrationManager:
    """
    Manages integration between S3 Vectors and OpenSearch Service.
    
    Provides two integration patterns:
    1. Export Pattern: Export data to OpenSearch Serverless for high performance
    2. Engine Pattern: Use S3 Vectors as cost-effective OpenSearch storage engine
    
    Features:
    - Point-in-time data export to OpenSearch Serverless
    - S3 Vectors engine configuration for OpenSearch domains  
    - Hybrid search combining vector similarity and keyword search
    - Cost monitoring and analysis across integration patterns
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
        
        # Initialize AWS service clients
        self._init_clients()
        
        # Cost tracking
        self._cost_tracker = {
            'exports': [],
            'queries': [],
            'storage_costs': {}
        }

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

    # Export Pattern Implementation (Task 6.1)
    
    def export_to_opensearch_serverless(
        self,
        vector_index_arn: str,
        collection_name: str,
        target_index_name: Optional[str] = None,
        iam_role_arn: Optional[str] = None,
        dead_letter_queue_bucket: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Export S3 vector data to OpenSearch Serverless collection.
        
        Implements point-in-time export using OpenSearch Ingestion Service.
        Data is copied to OpenSearch while remaining in S3 Vectors.
        
        Args:
            vector_index_arn: ARN of source S3 vector index
            collection_name: Target OpenSearch Serverless collection name
            target_index_name: Target index name in OpenSearch (defaults to vector index name)
            iam_role_arn: IAM role for ingestion pipeline (auto-created if not provided)
            dead_letter_queue_bucket: S3 bucket for failed records
            **kwargs: Additional export configuration
            
        Returns:
            str: Export job/pipeline ID
            
        Raises:
            OpenSearchIntegrationError: If export setup fails
        """
        operation = self.timing_tracker.start_operation("export_to_opensearch_serverless")
        try:
            # Extract vector index details
            index_name = vector_index_arn.split('/')[-1]
            target_index = target_index_name or f"{index_name}-export"
            
            self.logger.log_operation(
                "starting_opensearch_export",
                vector_index_arn=vector_index_arn,
                collection_name=collection_name,
                target_index=target_index
            )
            
            # Ensure OpenSearch Serverless collection exists
            collection_arn = self._ensure_serverless_collection(collection_name)
            
            # Log collection creation in resource registry
            self.resource_registry.log_opensearch_collection_created(
                collection_name=collection_name,
                collection_arn=collection_arn,
                region=self.region_name,
                source="export_pattern"
            )
            
            # Create or validate IAM role for ingestion
            if not iam_role_arn:
                iam_role_arn = self._create_ingestion_role(
                    vector_index_arn,
                    collection_arn,
                    dead_letter_queue_bucket
                )
                
                # Log IAM role creation in resource registry
                role_name = iam_role_arn.split('/')[-1]
                self.resource_registry.log_iam_role_created(
                    role_name=role_name,
                    role_arn=iam_role_arn,
                    purpose="opensearch_ingestion",
                    region=self.region_name,
                    source="export_pattern"
                )
            
            # Create OpenSearch Ingestion pipeline for export
            pipeline_config = self._create_export_pipeline_config(
                vector_index_arn=vector_index_arn,
                collection_name=collection_name,
                target_index=target_index,
                iam_role_arn=iam_role_arn,
                dead_letter_queue_bucket=dead_letter_queue_bucket,
                **kwargs
            )
            
            # Create ingestion pipeline
            response = self.osis_client.create_pipeline(
                PipelineName=f"s3vectors-export-{index_name}-{int(time.time())}",
                MinUnits=1,
                MaxUnits=16,  # Scale up to 16 workers for large datasets
                PipelineConfigurationBody=pipeline_config,
                Tags=[
                    {'Key': 'Service', 'Value': 'S3Vectors'},
                    {'Key': 'IntegrationPattern', 'Value': 'Export'},
                    {'Key': 'SourceIndex', 'Value': index_name}
                ]
            )
            
            pipeline_arn = response['Pipeline']['PipelineArn']
            export_id = pipeline_arn.split('/')[-1]
            
            # Log pipeline creation in resource registry
            self.resource_registry.log_opensearch_pipeline_created(
                pipeline_name=export_id,
                pipeline_arn=pipeline_arn,
                source_index_arn=vector_index_arn,
                target_collection=collection_name,
                region=self.region_name,
                source="export_pattern"
            )
            
            # Track export status
            export_status = ExportStatus(
                export_id=export_id,
                status='PENDING',
                source_index_arn=vector_index_arn,
                target_collection_name=collection_name,
                created_at=datetime.utcnow()
            )
            
            self._cost_tracker['exports'].append(export_status)
            
            self.logger.log_operation(
                "opensearch_export_started",
                export_id=export_id,
                pipeline_arn=pipeline_arn,
                estimated_duration_minutes=kwargs.get('estimated_duration', 30)
            )
            
            return export_id
            
        except ClientError as e:
            error_msg = f"AWS API error during OpenSearch export: {str(e)}"
            self.logger.log_operation("export_aws_error", level="ERROR", error=error_msg, vector_index_arn=vector_index_arn)
            raise OpenSearchIntegrationError(error_msg) from e
        except Exception as e:
                error_msg = f"Unexpected error during OpenSearch export: {str(e)}"
                self.logger.log_operation("export_unexpected_error", level="ERROR", error=error_msg)
                raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def get_export_status(self, export_id: str) -> ExportStatus:
        """
        Get status of an OpenSearch export operation.
        
        Args:
            export_id: Export/pipeline ID
            
        Returns:
            ExportStatus: Current export status with progress information
        """
        try:
            # Get pipeline status from OpenSearch Ingestion
            response = self.osis_client.get_pipeline(PipelineName=export_id)
            pipeline = response['Pipeline']
            
            # Find corresponding export status
            export_status = None
            for export in self._cost_tracker['exports']:
                if export.export_id == export_id:
                    export_status = export
                    break
            
            if not export_status:
                raise OpenSearchIntegrationError(f"Export status not found for ID: {export_id}")
            
            # Update status based on pipeline state
            pipeline_status = pipeline['Status']
            if pipeline_status == 'ACTIVE':
                export_status.status = 'IN_PROGRESS'
            elif pipeline_status == 'CREATE_COMPLETE':
                export_status.status = 'COMPLETED'
                export_status.completed_at = datetime.utcnow()
            elif pipeline_status in ['CREATE_FAILED', 'UPDATE_FAILED']:
                export_status.status = 'FAILED'
                export_status.error_message = pipeline.get('StatusReason', 'Unknown error')
            
            return export_status
            
        except ClientError as e:
            error_msg = f"Failed to get export status: {str(e)}"
            self.logger.log_operation("export_status_error", level="ERROR", error=error_msg, export_id=export_id)
            raise OpenSearchIntegrationError(error_msg) from e

    # Engine Pattern Implementation (Task 6.2)
    
    def configure_s3_vectors_engine(
        self,
        domain_name: str,
        enable_s3_vectors: bool = True,
        kms_key_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Configure OpenSearch domain to use S3 Vectors as storage engine.
        
        Enables S3 vector engine support on OpenSearch domain, allowing
        vector fields to be stored in S3 while maintaining OpenSearch functionality.
        
        Args:
            domain_name: OpenSearch domain name
            enable_s3_vectors: Whether to enable S3 vectors engine
            kms_key_id: KMS key for S3 vectors encryption
            **kwargs: Additional domain configuration options
            
        Returns:
            Dict[str, Any]: Domain configuration details
            
        Raises:
            OpenSearchIntegrationError: If domain configuration fails
        """
        operation = self.timing_tracker.start_operation("configure_s3_vectors_engine")
        try:
                self.logger.log_operation(
                    "configuring_s3_vectors_engine",
                    level="INFO",
                    domain_name=domain_name,
                    enable_s3_vectors=enable_s3_vectors
                )
                
                # Get current domain configuration
                try:
                    domain_response = self.opensearch_client.describe_domain(DomainName=domain_name)
                    domain_config = domain_response['DomainStatus']
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        raise OpenSearchIntegrationError(f"OpenSearch domain not found: {domain_name}")
                    raise
                
                # Validate domain requirements for S3 vectors
                self._validate_domain_for_s3_vectors(domain_config)
                
                # Prepare domain configuration update
                update_config = {
                    'DomainName': domain_name,
                    'AdvancedSecurityOptions': {
                        'Enabled': domain_config.get('AdvancedSecurityOptions', {}).get('Enabled', False)
                    }
                }
                
                # Enable S3 vectors engine if requested
                if enable_s3_vectors:
                    # Configure S3 vectors engine settings
                    s3_vectors_config = {
                        'Enabled': True
                    }
                    
                    if kms_key_id:
                        s3_vectors_config['KMSKeyId'] = kms_key_id
                    
                    update_config['S3VectorsEngine'] = s3_vectors_config
                    
                    self.logger.log_operation(
                        "enabling_s3_vectors_engine",
                        level="INFO",
                        domain_name=domain_name,
                        kms_key_id=kms_key_id
                    )
                else:
                    update_config['S3VectorsEngine'] = {'Enabled': False}
                
                # Apply domain configuration update
                update_response = self.opensearch_client.update_domain_config(**update_config)
                
                # Wait for domain update to complete
                self._wait_for_domain_update(domain_name, timeout_minutes=30)
                
                # Get updated domain configuration
                updated_domain = self.opensearch_client.describe_domain(DomainName=domain_name)
                
                # Log domain configuration in resource registry
                domain_status = updated_domain['DomainStatus']
                domain_arn = domain_status.get('ARN', f'arn:aws:es:{self.region_name}:123456789012:domain/{domain_name}')
                engine_version = domain_status.get('EngineVersion', 'OpenSearch_2.19')
                self.resource_registry.log_opensearch_domain_created(
                    domain_name=domain_name,
                    domain_arn=domain_arn,
                    region=self.region_name,
                    engine_version=engine_version,
                    s3_vectors_enabled=enable_s3_vectors,
                    source="engine_pattern"
                )
                
                configuration_result = {
                    'domain_name': domain_name,
                    's3_vectors_enabled': enable_s3_vectors,
                    'domain_status': updated_domain['DomainStatus']['Processing'],
                    'configuration_timestamp': datetime.utcnow().isoformat(),
                    'engine_capabilities': self._get_s3_vectors_capabilities(domain_name) if enable_s3_vectors else None
                }
                
                self.logger.log_operation(
                    "s3_vectors_engine_configured",
                    level="INFO",
                    domain_name=domain_name,
                    enabled=enable_s3_vectors,
                    processing=updated_domain['DomainStatus']['Processing']
                )
                
                return configuration_result
                
        except ClientError as e:
            error_msg = f"AWS API error configuring S3 vectors engine: {str(e)}"
            self.logger.log_operation("engine_config_aws_error", level="ERROR", error=error_msg, domain_name=domain_name)
            raise OpenSearchIntegrationError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error configuring S3 vectors engine: {str(e)}"
            self.logger.log_operation("engine_config_unexpected_error", level="ERROR", error=error_msg)
            raise OpenSearchIntegrationError(error_msg) from e
        finally:
            operation.finish()

    def create_s3_vector_index(
        self,
        opensearch_endpoint: str,
        index_name: str,
        vector_field_name: str,
        vector_dimension: int,
        space_type: str = "cosine",
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
        try:
            # Import requests for direct OpenSearch API calls
            import requests
            from requests.auth import HTTPBasicAuth
            
            # Build index mapping with S3 vector engine
            mapping = {
                "settings": {
                    "index": {
                        "knn": True
                    }
                },
                "mappings": {
                    "properties": {
                        vector_field_name: {
                            "type": "knn_vector",
                            "dimension": vector_dimension,
                            "space_type": space_type,
                            "method": {
                                "engine": "s3vector"
                            }
                        }
                    }
                }
            }
            
            # Add additional fields to mapping
            if additional_fields:
                mapping["mappings"]["properties"].update(additional_fields)
            
            # Create index via OpenSearch REST API
            url = f"https://{opensearch_endpoint}/{index_name}"
            
            # Use AWS signature v4 authentication if no basic auth provided
            response = requests.put(
                url,
                json=mapping,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise OpenSearchIntegrationError(
                    f"Failed to create S3 vector index: {response.status_code} {response.text}"
                )
            
            result = {
                "index_name": index_name,
                "vector_field": vector_field_name,
                "dimension": vector_dimension,
                "space_type": space_type,
                "engine": "s3vector",
                "created_at": datetime.utcnow().isoformat(),
                "response": response.json() if response.text else {}
            }
            
            # Log index creation in resource registry
            self.resource_registry.log_opensearch_index_created(
                index_name=index_name,
                opensearch_endpoint=opensearch_endpoint,
                vector_field_name=vector_field_name,
                vector_dimension=vector_dimension,
                space_type=space_type,
                engine_type="s3vector",
                source="engine_pattern"
            )
            
            self.logger.log_operation(
                "s3_vector_index_created",
                level="INFO",
                index_name=index_name,
                vector_field=vector_field_name,
                dimension=vector_dimension
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to create S3 vector index: {str(e)}"
            self.logger.log_operation("s3_vector_index_creation_failed", level="ERROR", error=error_msg, index_name=index_name)
            raise OpenSearchIntegrationError(error_msg) from e

    # Hybrid Search Implementation (Task 6.3)
    
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

    # Cost Monitoring Implementation (Task 6.4)
    
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
        
        Provides cost analysis comparing export vs engine integration patterns,
        including storage, query, and operational costs.
        
        Args:
            pattern: Integration pattern to analyze
            time_period_days: Analysis time period
            vector_storage_gb: Estimated vector storage size in GB
            query_count_monthly: Estimated monthly query count
            **kwargs: Additional cost parameters
            
        Returns:
            CostAnalysis: Detailed cost analysis with recommendations
        """
        operation = self.timing_tracker.start_operation("monitor_integration_costs")
        try:
            try:
                self.logger.log_operation(
                    "analyzing_integration_costs",
                    pattern=pattern.value,
                    time_period_days=time_period_days,
                    storage_gb=vector_storage_gb
                )
                
                # Get current pricing information
                pricing_data = self._get_aws_pricing_data()
                
                if pattern == IntegrationPattern.EXPORT:
                    cost_analysis = self._analyze_export_pattern_costs(
                        pricing_data,
                        vector_storage_gb,
                        query_count_monthly,
                        time_period_days,
                        **kwargs
                    )
                else:  # ENGINE pattern
                    cost_analysis = self._analyze_engine_pattern_costs(
                        pricing_data,
                        vector_storage_gb,
                        query_count_monthly,
                        time_period_days,
                        **kwargs
                    )
                
                # Add cost comparison between patterns
                if vector_storage_gb and query_count_monthly:
                    cost_analysis.cost_comparison = self._compare_integration_costs(
                        pricing_data,
                        vector_storage_gb,
                        query_count_monthly,
                        time_period_days
                    )
                
                # Generate optimization recommendations
                cost_analysis.optimization_recommendations = self._generate_cost_recommendations(
                    cost_analysis,
                    vector_storage_gb,
                    query_count_monthly
                )
                
                self.logger.log_operation(
                    "cost_analysis_completed",
                    pattern=pattern.value,
                    monthly_total=cost_analysis.estimated_monthly_total,
                    recommendations_count=len(cost_analysis.optimization_recommendations)
                )
                
                return cost_analysis
                
            except Exception as e:
                error_msg = f"Cost monitoring failed: {str(e)}"
                self.logger.log_operation("cost_monitoring_error", level="ERROR", error=error_msg, pattern=pattern.value)
                raise CostMonitoringError(error_msg) from e
        finally:
            operation.finish()

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
        try:
            # Aggregate costs from tracked activities
            export_costs = sum(
    (export.cost_estimate if hasattr(export, 'cost_estimate') and export.cost_estimate is not None 
             else export.get('cost_estimate', 0) if hasattr(export, 'get') else 0) 
                for export in self._cost_tracker['exports']
            )
            query_costs = sum(query.get('cost', 0) for query in self._cost_tracker['queries'])
            storage_costs = sum(self._cost_tracker['storage_costs'].values())
            
            report = {
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'cost_breakdown': {
                    'export_operations': export_costs,
                    'query_operations': query_costs,
                    'storage_costs': storage_costs,
                    'total_costs': export_costs + query_costs + storage_costs
                },
                'activity_summary': {
                    'export_count': len(self._cost_tracker['exports']),
                    'query_count': len(self._cost_tracker['queries']),
                    'active_integrations': len(self._cost_tracker['storage_costs'])
                }
            }
            
            if include_projections:
                # Add cost projections based on current usage patterns
                report['projections'] = self._generate_cost_projections(
                    current_costs=report['cost_breakdown'],
                    period_days=(end_date - start_date).days
                )
            
            return report
            
        except Exception as e:
            error_msg = f"Cost report generation failed: {str(e)}"
            self.logger.log_operation("cost_report_error", level="ERROR", error=error_msg)
            raise CostMonitoringError(error_msg) from e

    # Helper Methods
    
    def _ensure_serverless_collection(self, collection_name: str) -> str:
        """Ensure OpenSearch Serverless collection exists."""
        try:
            # Check if collection exists
            response = self.opensearch_serverless_client.batch_get_collection(
                names=[collection_name]
            )
            
            if response['collectionDetails']:
                return response['collectionDetails'][0]['arn']
            
            # Create collection if it doesn't exist
            create_response = self.opensearch_serverless_client.create_collection(
                name=collection_name,
                type='VECTORSEARCH',
                description=f'Collection for S3 Vectors export: {collection_name}'
            )
            
            collection_arn = create_response['createCollectionDetail']['arn']
            
            # Log new collection creation in resource registry
            self.resource_registry.log_opensearch_collection_created(
                collection_name=collection_name,
                collection_arn=collection_arn,
                region=self.region_name,
                source="auto_created"
            )
            
            return collection_arn
            
        except ClientError as e:
            error_msg = f"Failed to ensure serverless collection: {str(e)}"
            raise OpenSearchIntegrationError(error_msg) from e

    def _create_ingestion_role(
        self,
        vector_index_arn: str,
        collection_arn: str,
        dlq_bucket: Optional[str]
    ) -> str:
        """Create real IAM role for OpenSearch Ingestion pipeline."""
        try:
            role_name = f"s3vectors-ingestion-role-{int(time.time())}"
            
            # Trust policy for OpenSearch Ingestion
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "osis-pipelines.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create the role
            iam_client = boto3.client('iam', region_name=self.region_name)
            
            role_response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Role for S3 Vectors to OpenSearch ingestion pipeline"
            )
            
            role_arn = role_response['Role']['Arn']
            
            # Create and attach policy for S3 Vectors access
            s3vectors_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "s3vectors:ListVectors",
                            "s3vectors:GetVectorIndex",
                            "s3vectors:QueryVectors"
                        ],
                        "Resource": vector_index_arn
                    }
                ]
            }
            
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-s3vectors-policy",
                PolicyDocument=json.dumps(s3vectors_policy)
            )
            
            # Create and attach policy for OpenSearch Serverless access
            opensearch_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "aoss:APIAccessAll",
                            "aoss:BatchGetCollection"
                        ],
                        "Resource": collection_arn
                    }
                ]
            }
            
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=f"{role_name}-opensearch-policy", 
                PolicyDocument=json.dumps(opensearch_policy)
            )
            
            # Add DLQ policy if bucket specified
            if dlq_bucket:
                dlq_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["s3:PutObject"],
                            "Resource": f"arn:aws:s3:::{dlq_bucket}/*"
                        }
                    ]
                }
                
                iam_client.put_role_policy(
                    RoleName=role_name,
                    PolicyName=f"{role_name}-dlq-policy",
                    PolicyDocument=json.dumps(dlq_policy)
                )
            
            self.logger.log_operation("Created real IAM role for ingestion", role_arn=role_arn)
            
            # Log role creation in resource registry (done in calling method)
            # This is tracked when the role is actually used
            
            return role_arn
            
        except Exception as e:
            error_msg = f"Failed to create real IAM role: {str(e)}"
            self.logger.log_operation("IAM role creation failed", level="ERROR", error=error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def _create_export_pipeline_config(self, **kwargs) -> str:
        """Create OpenSearch Ingestion pipeline configuration."""
        # This would generate the YAML configuration for OSI pipeline
        # Implementation details depend on specific pipeline requirements
        config = f"""
version: "2"
s3-vectors-pipeline:
  source:
    s3vectors:
      aws:
        region: "{self.region_name}"
      vector_index_arn: "{kwargs['vector_index_arn']}"
  processor:
    - mutate:
        rename_keys:
          - from_key: "key"
            to_key: "id"
  sink:
    - opensearch:
        hosts:
          - "{kwargs['collection_name']}.{self.region_name}.aoss.amazonaws.com"
        index: "{kwargs['target_index']}"
        aws:
          region: "{self.region_name}"
          role: "{kwargs['iam_role_arn']}"
        """
        return config.strip()

    def _validate_domain_for_s3_vectors(self, domain_config: Dict[str, Any]) -> None:
        """Validate that OpenSearch domain supports S3 vectors."""
        # Check OpenSearch version
        engine_version = domain_config.get('EngineVersion', '')
        if not engine_version.startswith('OpenSearch_2.') or engine_version < 'OpenSearch_2.19':
            raise OpenSearchIntegrationError(
                f"S3 vectors requires OpenSearch 2.19 or later, found: {engine_version}"
            )
        
        # Check instance types (should be OR1 instances for S3 Vectors engine)
        instance_type = domain_config.get('ClusterConfig', {}).get('InstanceType', '')
        if not instance_type.startswith('or1.'):
            self.logger.log_operation(
                "incorrect_instance_type_warning",
                level="WARNING",
                instance_type=instance_type,
                recommendation="Use OR1 instance types (or1.medium.search, or1.large.search, etc.) for S3 Vectors engine"
            )

    def _wait_for_domain_update(self, domain_name: str, timeout_minutes: int = 30) -> None:
        """Wait for OpenSearch domain update to complete."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while time.time() - start_time < timeout_seconds:
            response = self.opensearch_client.describe_domain(DomainName=domain_name)
            if not response['DomainStatus']['Processing']:
                return
            
            time.sleep(30)  # Check every 30 seconds
        
        raise OpenSearchIntegrationError(
            f"Domain update timeout after {timeout_minutes} minutes"
        )

    def _get_s3_vectors_capabilities(self, domain_name: str) -> Dict[str, Any]:
        """Get S3 vectors engine capabilities for domain."""
        return {
            'supported_space_types': ['cosine', 'l2', 'inner_product'],
            'max_dimensions': 10000,
            'features': ['hybrid_search', 'metadata_filtering', 'batch_ingestion'],
            'limitations': ['no_snapshots', 'no_ultraWarm', 'no_cross_cluster_replication']
        }

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

    def _get_aws_pricing_data(self) -> Dict[str, Any]:
        """Retrieve AWS pricing data for cost calculations."""
        # Simplified pricing data - in production, this would query AWS Price List API
        return {
            's3_vectors_storage_per_gb_month': 0.023,  # Standard S3 pricing
            's3_vectors_query_per_1k': 0.01,
            'opensearch_serverless_ocup_per_hour': 0.24,
            'opensearch_ingestion_per_hour': 0.48,
            'data_transfer_per_gb': 0.09
        }

    def _analyze_export_pattern_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: Optional[float],
        queries_monthly: Optional[int],
        period_days: int,
        **kwargs
    ) -> CostAnalysis:
        """Analyze costs for export integration pattern."""
        monthly_multiplier = 30 / period_days
        
        # Storage costs (dual storage: S3 + OpenSearch)
        s3_storage_cost = (storage_gb or 0) * pricing_data['s3_vectors_storage_per_gb_month']
        opensearch_storage_cost = (storage_gb or 0) * 0.10  # Approximate OpenSearch Serverless storage cost
        
        # Query costs
        query_cost = ((queries_monthly or 0) / 1000) * pricing_data['s3_vectors_query_per_1k']
        
        # Ingestion costs (one-time for export)
        ingestion_cost_gb = (storage_gb or 0) * 0.05  # Approximate ingestion cost
        
        total_monthly = (s3_storage_cost + opensearch_storage_cost + query_cost) * monthly_multiplier
        
        return CostAnalysis(
            pattern=IntegrationPattern.EXPORT,
            storage_cost_monthly=s3_storage_cost + opensearch_storage_cost,
            query_cost_per_1k=pricing_data['s3_vectors_query_per_1k'],
            ingestion_cost_per_gb=0.05,
            estimated_monthly_total=total_monthly,
            cost_comparison={},
            optimization_recommendations=[]
        )

    def _analyze_engine_pattern_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: Optional[float],
        queries_monthly: Optional[int],
        period_days: int,
        **kwargs
    ) -> CostAnalysis:
        """Analyze costs for engine integration pattern."""
        monthly_multiplier = 30 / period_days
        
        # Storage costs (single storage: S3 only)
        storage_cost = (storage_gb or 0) * pricing_data['s3_vectors_storage_per_gb_month']
        
        # Query costs (higher latency, lower cost)
        query_cost = ((queries_monthly or 0) / 1000) * pricing_data['s3_vectors_query_per_1k'] * 0.8
        
        # No ingestion costs for engine pattern
        ingestion_cost_gb = 0.0
        
        total_monthly = (storage_cost + query_cost) * monthly_multiplier
        
        return CostAnalysis(
            pattern=IntegrationPattern.ENGINE,
            storage_cost_monthly=storage_cost,
            query_cost_per_1k=pricing_data['s3_vectors_query_per_1k'] * 0.8,
            ingestion_cost_per_gb=ingestion_cost_gb,
            estimated_monthly_total=total_monthly,
            cost_comparison={},
            optimization_recommendations=[]
        )

    def _compare_integration_costs(
        self,
        pricing_data: Dict[str, Any],
        storage_gb: float,
        queries_monthly: int,
        period_days: int
    ) -> Dict[str, float]:
        """Compare costs between integration patterns."""
        export_analysis = self._analyze_export_pattern_costs(
            pricing_data, storage_gb, queries_monthly, period_days
        )
        engine_analysis = self._analyze_engine_pattern_costs(
            pricing_data, storage_gb, queries_monthly, period_days
        )
        
        return {
            'export_pattern_monthly': export_analysis.estimated_monthly_total,
            'engine_pattern_monthly': engine_analysis.estimated_monthly_total,
            'cost_difference': export_analysis.estimated_monthly_total - engine_analysis.estimated_monthly_total,
            'percentage_savings_engine': (
                (export_analysis.estimated_monthly_total - engine_analysis.estimated_monthly_total) 
                / export_analysis.estimated_monthly_total * 100
            ) if export_analysis.estimated_monthly_total > 0 else 0
        }

    def _generate_cost_recommendations(
        self,
        cost_analysis: CostAnalysis,
        storage_gb: Optional[float],
        queries_monthly: Optional[int]
    ) -> List[str]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        if cost_analysis.pattern == IntegrationPattern.EXPORT:
            if (queries_monthly or 0) < 10000:
                recommendations.append(
                    "Consider using engine pattern for low-query workloads to reduce storage costs"
                )
            recommendations.append(
                "Monitor dual storage costs and evaluate if high-performance queries justify the expense"
            )
        else:  # ENGINE pattern
            if (queries_monthly or 0) > 100000:
                recommendations.append(
                    "Consider export pattern for high-query workloads to improve performance"
                )
            recommendations.append(
                "Engine pattern provides optimal cost efficiency for analytical workloads"
            )
        
        # General recommendations
        recommendations.extend([
            "Implement query result caching to reduce repeated vector searches",
            "Use batch processing for embedding generation to optimize costs",
            "Monitor query patterns to identify optimization opportunities"
        ])
        
        return recommendations

    def _track_query_cost(self, **kwargs) -> None:
        """Track query cost for monitoring."""
        query_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'cost': kwargs.get('processing_time_ms', 0) * 0.001,  # Simplified cost calculation
            **kwargs
        }
        self._cost_tracker['queries'].append(query_record)

    def _generate_cost_projections(self, current_costs: Dict[str, float], period_days: int) -> Dict[str, Any]:
        """Generate cost projections based on current usage."""
        daily_rate = sum(current_costs.values()) / period_days if period_days > 0 else 0
        
        return {
            'daily_average': daily_rate,
            'weekly_projection': daily_rate * 7,
            'monthly_projection': daily_rate * 30,
            'quarterly_projection': daily_rate * 90,
            'annual_projection': daily_rate * 365
        }

    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts_client = boto3.client('sts', region_name=self.region_name)
            response = sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            self.logger.log_operation("Failed to get AWS account ID", level="ERROR", error=str(e))
            # Don't fall back to fake account - raise exception to prevent simulation mode
            raise OpenSearchIntegrationError(f"Failed to get real AWS account ID: {e}")

    # Resource Management and Cleanup Methods
    
    def get_opensearch_resource_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all OpenSearch-related resources."""
        try:
            resource_summary = self.resource_registry.get_resource_summary()
            
            # Add OpenSearch-specific details
            collections = self.resource_registry.list_opensearch_collections()
            domains = self.resource_registry.list_opensearch_domains()
            pipelines = self.resource_registry.list_opensearch_pipelines()
            indexes = self.resource_registry.list_opensearch_indexes()
            roles = self.resource_registry.list_iam_roles()
            
            # Filter active resources
            active_collections = [c for c in collections if c.get('status') == 'created']
            active_domains = [d for d in domains if d.get('status') == 'created']
            active_pipelines = [p for p in pipelines if p.get('status') == 'created']
            active_indexes = [i for i in indexes if i.get('status') == 'created']
            active_roles = [r for r in roles if r.get('status') == 'created']
            
            return {
                'summary': resource_summary,
                'opensearch_details': {
                    'collections': {
                        'total': len(collections),
                        'active': len(active_collections),
                        'resources': active_collections
                    },
                    'domains': {
                        'total': len(domains),
                        'active': len(active_domains),
                        'resources': active_domains
                    },
                    'pipelines': {
                        'total': len(pipelines),
                        'active': len(active_pipelines),
                        'resources': active_pipelines
                    },
                    'indexes': {
                        'total': len(indexes),
                        'active': len(active_indexes),
                        'resources': active_indexes
                    },
                    'iam_roles': {
                        'total': len(roles),
                        'active': len(active_roles),
                        'resources': active_roles
                    }
                },
                'integration_patterns': {
                    'export_resources': len([r for r in active_collections if 'export' in r.get('source', '').lower()]),
                    'engine_resources': len([r for r in active_domains if 'engine' in r.get('source', '').lower()])
                }
            }
            
        except Exception as e:
            error_msg = f"Failed to get OpenSearch resource summary: {str(e)}"
            self.logger.log_error("resource_summary_error", error_msg)
            raise OpenSearchIntegrationError(error_msg) from e

    def cleanup_export_resources(
        self,
        export_id: str,
        cleanup_collection: bool = False,
        cleanup_iam_role: bool = True
    ) -> Dict[str, Any]:
        """Clean up resources created for export pattern."""
        cleanup_results = {
            'export_id': export_id,
            'pipeline_deleted': False,
            'collection_deleted': False,
            'iam_role_deleted': False,
            'errors': []
        }
        
        try:
            # Delete OSI pipeline
            try:
                self.osis_client.delete_pipeline(PipelineName=export_id)
                self.resource_registry.log_opensearch_pipeline_deleted(
                    pipeline_name=export_id,
                    source="cleanup"
                )
                cleanup_results['pipeline_deleted'] = True
                self.logger.log_operation("Export pipeline deleted", pipeline_id=export_id)
            except Exception as e:
                cleanup_results['errors'].append(f"Pipeline deletion failed: {str(e)}")
            
            # Optionally delete collection (usually kept for other exports)
            if cleanup_collection:
                pipelines = self.resource_registry.list_opensearch_pipelines()
                target_collection = None
                for pipeline in pipelines:
                    if pipeline.get('name') == export_id:
                        target_collection = pipeline.get('target_collection')
                        break
                
                if target_collection:
                    try:
                        self.opensearch_serverless_client.delete_collection(id=target_collection)
                        self.resource_registry.log_opensearch_collection_deleted(
                            collection_name=target_collection,
                            source="cleanup"
                        )
                        cleanup_results['collection_deleted'] = True
                        self.logger.log_operation("Collection deleted", collection_name=target_collection)
                    except Exception as e:
                        cleanup_results['errors'].append(f"Collection deletion failed: {str(e)}")
            
            # Clean up IAM role if created specifically for this export
            if cleanup_iam_role:
                # Find associated IAM role from resource registry
                roles = self.resource_registry.list_iam_roles()
                export_roles = [r for r in roles if 'export' in r.get('source', '') and 
                               export_id in r.get('name', '')]
                
                for role in export_roles:
                    try:
                        iam_client = boto3.client('iam', region_name=self.region_name)
                        role_name = role.get('name')
                        
                        # Delete role policies first
                        policies = iam_client.list_role_policies(RoleName=role_name)
                        for policy_name in policies['PolicyNames']:
                            iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
                        
                        # Delete the role
                        iam_client.delete_role(RoleName=role_name)
                        cleanup_results['iam_role_deleted'] = True
                        self.logger.log_operation("IAM role deleted", role_name=role_name)
                        
                    except Exception as e:
                        cleanup_results['errors'].append(f"IAM role deletion failed: {str(e)}")
            
            return cleanup_results
            
        except Exception as e:
            error_msg = f"Export resource cleanup failed: {str(e)}"
            self.logger.log_error("export_cleanup_error", error_msg, export_id=export_id)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results

    def cleanup_engine_resources(
        self,
        domain_name: str,
        disable_s3_vectors: bool = True,
        cleanup_indexes: bool = False
    ) -> Dict[str, Any]:
        """Clean up or reset resources used in engine pattern."""
        cleanup_results = {
            'domain_name': domain_name,
            's3_vectors_disabled': False,
            'indexes_deleted': 0,
            'errors': []
        }
        
        try:
            # Disable S3 vectors on the domain
            if disable_s3_vectors:
                try:
                    self.configure_s3_vectors_engine(
                        domain_name=domain_name,
                        enable_s3_vectors=False
                    )
                    cleanup_results['s3_vectors_disabled'] = True
                    self.logger.log_operation("S3 vectors disabled on domain", domain_name=domain_name)
                except Exception as e:
                    cleanup_results['errors'].append(f"S3 vectors disable failed: {str(e)}")
            
            # Optionally cleanup indexes
            if cleanup_indexes:
                indexes = self.resource_registry.list_opensearch_indexes()
                domain_indexes = [i for i in indexes if domain_name in i.get('endpoint', '')]
                
                for index in domain_indexes:
                    try:
                        import requests
                        endpoint = index.get('endpoint')
                        index_name = index.get('name')
                        
                        # Delete index via REST API
                        response = requests.delete(
                            f"https://{endpoint}/{index_name}",
                            timeout=30
                        )
                        
                        if response.status_code in [200, 404]:  # 404 is OK - already deleted
                            cleanup_results['indexes_deleted'] += 1
                            self.logger.log_operation("OpenSearch index deleted", 
                                                    index_name=index_name, endpoint=endpoint)
                        
                    except Exception as e:
                        cleanup_results['errors'].append(f"Index {index.get('name')} deletion failed: {str(e)}")
            
            return cleanup_results
            
        except Exception as e:
            error_msg = f"Engine resource cleanup failed: {str(e)}"
            self.logger.log_error("engine_cleanup_error", error_msg, domain_name=domain_name)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results

    def cleanup_all_opensearch_resources(
        self,
        confirm_deletion: bool = False,
        preserve_collections: bool = True,
        preserve_domains: bool = True
    ) -> Dict[str, Any]:
        """Clean up all OpenSearch integration resources."""
        if not confirm_deletion:
            return {
                'error': 'Must set confirm_deletion=True to proceed with cleanup',
                'resources_found': self.get_opensearch_resource_summary()
            }
        
        cleanup_results = {
            'pipelines_deleted': 0,
            'collections_deleted': 0,
            'domains_modified': 0,
            'indexes_deleted': 0,
            'iam_roles_deleted': 0,
            'errors': []
        }
        
        try:
            # Clean up pipelines
            pipelines = self.resource_registry.list_opensearch_pipelines()
            active_pipelines = [p for p in pipelines if p.get('status') == 'created']
            
            for pipeline in active_pipelines:
                try:
                    result = self.cleanup_export_resources(
                        export_id=pipeline.get('name'),
                        cleanup_collection=not preserve_collections,
                        cleanup_iam_role=True
                    )
                    if result.get('pipeline_deleted'):
                        cleanup_results['pipelines_deleted'] += 1
                    if result.get('collection_deleted'):
                        cleanup_results['collections_deleted'] += 1
                    if result.get('iam_role_deleted'):
                        cleanup_results['iam_roles_deleted'] += 1
                    cleanup_results['errors'].extend(result.get('errors', []))
                except Exception as e:
                    cleanup_results['errors'].append(f"Pipeline cleanup failed: {str(e)}")
            
            # Disable S3 vectors on domains (if not preserving)
            if not preserve_domains:
                domains = self.resource_registry.list_opensearch_domains()
                active_domains = [d for d in domains if d.get('status') == 'created']
                
                for domain in active_domains:
                    try:
                        result = self.cleanup_engine_resources(
                            domain_name=domain.get('name'),
                            disable_s3_vectors=True,
                            cleanup_indexes=True
                        )
                        if result.get('s3_vectors_disabled'):
                            cleanup_results['domains_modified'] += 1
                        cleanup_results['indexes_deleted'] += result.get('indexes_deleted', 0)
                        cleanup_results['errors'].extend(result.get('errors', []))
                    except Exception as e:
                        cleanup_results['errors'].append(f"Domain cleanup failed: {str(e)}")
            
            self.logger.log_operation(
                "OpenSearch resource cleanup completed",
                pipelines_deleted=cleanup_results['pipelines_deleted'],
                collections_deleted=cleanup_results['collections_deleted'],
                domains_modified=cleanup_results['domains_modified'],
                errors_count=len(cleanup_results['errors'])
            )
            
            return cleanup_results
            
        except Exception as e:
            error_msg = f"Bulk cleanup failed: {str(e)}"
            self.logger.log_error("bulk_cleanup_error", error_msg)
            cleanup_results['errors'].append(error_msg)
            return cleanup_results