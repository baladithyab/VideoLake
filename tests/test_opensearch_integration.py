"""
Tests for OpenSearch Integration Manager.

This module tests the OpenSearch integration functionality including:
- Export to OpenSearch Serverless pattern
- S3 Vectors engine integration pattern  
- Hybrid search capabilities
- Cost monitoring and analysis
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.services.opensearch_integration import (
    OpenSearchIntegrationManager,
    IntegrationPattern,
    ExportStatus,
    HybridSearchResult,
    CostAnalysis
)
from src.exceptions import OpenSearchIntegrationError, CostMonitoringError


@pytest.fixture
def integration_manager():
    """Create OpenSearch integration manager for testing."""
    return OpenSearchIntegrationManager(region_name="us-east-1")


@pytest.fixture
def mock_aws_clients():
    """Mock AWS service clients."""
    clients = {
        's3vectors': Mock(),
        'opensearch': Mock(),
        'opensearchserverless': Mock(),
        'osis': Mock(),
        'pricing': Mock()
    }
    return clients


class TestOpenSearchIntegrationManager:
    """Test cases for OpenSearch Integration Manager."""
    
    def test_initialization(self, integration_manager):
        """Test proper initialization of integration manager."""
        assert integration_manager.region_name == "us-east-1"
        assert hasattr(integration_manager, 'logger')
        assert hasattr(integration_manager, 'timing_tracker')
        assert hasattr(integration_manager, '_cost_tracker')
    
    @patch('boto3.Session')
    def test_client_initialization(self, mock_session):
        """Test AWS client initialization."""
        mock_session_instance = Mock()
        mock_session.return_value = mock_session_instance
        
        # Mock client creation
        mock_s3vectors = Mock()
        mock_opensearch = Mock()
        mock_session_instance.client.side_effect = [
            mock_s3vectors, mock_opensearch, Mock(), Mock(), Mock()
        ]
        
        manager = OpenSearchIntegrationManager()
        
        # Verify clients were created
        assert manager.s3vectors_client == mock_s3vectors
        assert manager.opensearch_client == mock_opensearch

    @pytest.mark.asyncio
    async def test_export_to_opensearch_serverless_success(self, integration_manager):
        """Test successful export to OpenSearch Serverless."""
        # Mock AWS service responses
        with patch.object(integration_manager, '_ensure_serverless_collection') as mock_collection, \
             patch.object(integration_manager, '_create_ingestion_role') as mock_role, \
             patch.object(integration_manager, '_create_export_pipeline_config') as mock_config, \
             patch.object(integration_manager, 'osis_client') as mock_osis:
            
            # Setup mocks
            mock_collection.return_value = "arn:aws:aoss:us-east-1:123456789012:collection/test-collection"
            mock_role.return_value = "arn:aws:iam::123456789012:role/test-role"
            mock_config.return_value = "pipeline-config-yaml"
            mock_osis.create_pipeline.return_value = {
                'Pipeline': {
                    'PipelineArn': 'arn:aws:osis:us-east-1:123456789012:pipeline/test-pipeline'
                }
            }
            
            # Test export
            export_id = integration_manager.export_to_opensearch_serverless(
                vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/test-index",
                collection_name="test-collection"
            )
            
            assert export_id == "test-pipeline"
            mock_osis.create_pipeline.assert_called_once()

    def test_export_status_monitoring(self, integration_manager):
        """Test export status monitoring functionality."""
        # Create a mock export status
        export_status = ExportStatus(
            export_id="test-export-123",
            status="IN_PROGRESS",
            source_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/test-index",
            target_collection_name="test-collection",
            created_at=datetime.utcnow()
        )
        
        # Add to cost tracker
        integration_manager._cost_tracker['exports'].append(export_status)
        
        # Mock OSIS response
        with patch.object(integration_manager, 'osis_client') as mock_osis:
            mock_osis.get_pipeline.return_value = {
                'Pipeline': {
                    'Status': 'ACTIVE',
                    'StatusReason': None
                }
            }
            
            # Test status retrieval
            status = integration_manager.get_export_status("test-export-123")
            
            assert status.export_id == "test-export-123"
            assert status.status == "IN_PROGRESS"

    def test_configure_s3_vectors_engine_success(self, integration_manager):
        """Test successful S3 vectors engine configuration."""
        # Mock domain configuration
        domain_config = {
            'DomainName': 'test-domain',
            'EngineVersion': 'OpenSearch_2.19',
            'ClusterConfig': {'InstanceType': 'm6g.large.search.optimized'},
            'Processing': False,
            'ARN': 'arn:aws:es:us-east-1:123456789012:domain/test-domain'
        }
        
        with patch.object(integration_manager, 'opensearch_client') as mock_opensearch, \
             patch.object(integration_manager, '_wait_for_domain_update'):
            
            # Mock describe and update responses
            mock_opensearch.describe_domain.side_effect = [
                {'DomainStatus': domain_config},
                {'DomainStatus': {**domain_config, 'Processing': False}}
            ]
            mock_opensearch.update_domain_config.return_value = {'DomainConfig': {}}
            
            # Test configuration
            result = integration_manager.configure_s3_vectors_engine(
                domain_name="test-domain",
                enable_s3_vectors=True
            )
            
            assert result['domain_name'] == 'test-domain'
            assert result['s3_vectors_enabled'] is True
            mock_opensearch.update_domain_config.assert_called_once()

    def test_create_s3_vector_index(self, integration_manager):
        """Test S3 vector index creation in OpenSearch."""
        with patch('requests.put') as mock_put:
            # Mock successful index creation
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"acknowledged": True}
            mock_response.text = '{"acknowledged": true}'
            mock_put.return_value = mock_response
            
            # Test index creation
            result = integration_manager.create_s3_vector_index(
                opensearch_endpoint="test-domain.us-east-1.es.amazonaws.com",
                index_name="test-index",
                vector_field_name="embedding",
                vector_dimension=1024
            )
            
            assert result['index_name'] == 'test-index'
            assert result['vector_field'] == 'embedding'
            assert result['dimension'] == 1024
            assert result['engine'] == 's3vector'
            mock_put.assert_called_once()

    def test_perform_hybrid_search_success(self, integration_manager):
        """Test successful hybrid search execution."""
        # Mock OpenSearch search response
        mock_search_response = {
            'took': 15,
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 0.95,
                        '_source': {
                            'content': 'Test document content',
                            'metadata': {'category': 'test'}
                        },
                        'highlight': {'content': ['Test <em>document</em> content']}
                    },
                    {
                        '_id': 'doc2', 
                        '_score': 0.87,
                        '_source': {
                            'content': 'Another test document',
                            'metadata': {'category': 'test'}
                        }
                    }
                ]
            }
        }
        
        with patch('requests.post') as mock_post:
            # Mock successful search
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            mock_post.return_value = mock_response
            
            # Test hybrid search
            results = integration_manager.perform_hybrid_search(
                opensearch_endpoint="test-domain.us-east-1.es.amazonaws.com",
                index_name="test-index",
                query_text="test query",
                query_vector=[0.1, 0.2, 0.3],
                k=2
            )
            
            assert len(results) == 2
            assert all(isinstance(r, HybridSearchResult) for r in results)
            assert results[0].document_id == 'doc1'
            assert results[0].combined_score == 0.95
            mock_post.assert_called_once()

    def test_cost_monitoring_export_pattern(self, integration_manager):
        """Test cost monitoring for export integration pattern."""
        # Test export pattern cost analysis
        with patch.object(integration_manager, '_get_aws_pricing_data') as mock_pricing:
            mock_pricing.return_value = {
                's3_vectors_storage_per_gb_month': 0.023,
                's3_vectors_query_per_1k': 0.01,
                'opensearch_serverless_ocup_per_hour': 0.24,
                'data_transfer_per_gb': 0.09
            }
            
            # Test cost analysis
            cost_analysis = integration_manager.monitor_integration_costs(
                pattern=IntegrationPattern.EXPORT,
                vector_storage_gb=100.0,
                query_count_monthly=50000,
                time_period_days=30
            )
            
            assert isinstance(cost_analysis, CostAnalysis)
            assert cost_analysis.pattern == IntegrationPattern.EXPORT
            assert cost_analysis.storage_cost_monthly > 0
            assert cost_analysis.estimated_monthly_total > 0
            assert len(cost_analysis.optimization_recommendations) > 0

    def test_cost_monitoring_engine_pattern(self, integration_manager):
        """Test cost monitoring for engine integration pattern."""
        with patch.object(integration_manager, '_get_aws_pricing_data') as mock_pricing:
            mock_pricing.return_value = {
                's3_vectors_storage_per_gb_month': 0.023,
                's3_vectors_query_per_1k': 0.01
            }
            
            # Test engine pattern cost analysis
            cost_analysis = integration_manager.monitor_integration_costs(
                pattern=IntegrationPattern.ENGINE,
                vector_storage_gb=100.0,
                query_count_monthly=10000,
                time_period_days=30
            )
            
            assert cost_analysis.pattern == IntegrationPattern.ENGINE
            assert cost_analysis.storage_cost_monthly > 0
            assert cost_analysis.ingestion_cost_per_gb == 0.0  # No ingestion cost for engine pattern
            assert cost_analysis.estimated_monthly_total > 0

    def test_get_cost_report(self, integration_manager):
        """Test comprehensive cost report generation."""
        # Add some mock cost data
        integration_manager._cost_tracker['exports'] = [
            ExportStatus(
                export_id="export-1",
                status="COMPLETED", 
                source_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/test",
                target_collection_name="test-collection",
                created_at=datetime.utcnow(),
                cost_estimate=25.50
            )
        ]
        integration_manager._cost_tracker['queries'] = [
            {'cost': 1.20, 'timestamp': datetime.utcnow().isoformat()},
            {'cost': 0.80, 'timestamp': datetime.utcnow().isoformat()}
        ]
        integration_manager._cost_tracker['storage_costs'] = {'index1': 15.00}
        
        # Generate cost report
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        report = integration_manager.get_cost_report(
            start_date=start_date,
            end_date=end_date,
            include_projections=True
        )
        
        assert 'report_period' in report
        assert 'cost_breakdown' in report
        assert 'activity_summary' in report
        assert 'projections' in report
        assert report['cost_breakdown']['total_costs'] == 42.50  # 25.50 + 2.00 + 15.00

    def test_domain_validation_for_s3_vectors(self, integration_manager):
        """Test OpenSearch domain validation for S3 vectors compatibility."""
        # Test valid domain configuration
        valid_config = {
            'EngineVersion': 'OpenSearch_2.19',
            'ClusterConfig': {'InstanceType': 'm6g.large.optimized'}
        }
        
        # Should not raise exception
        integration_manager._validate_domain_for_s3_vectors(valid_config)
        
        # Test invalid version
        invalid_config = {
            'EngineVersion': 'OpenSearch_2.15',
            'ClusterConfig': {'InstanceType': 'm6g.large.optimized'}
        }
        
        with pytest.raises(OpenSearchIntegrationError, match="S3 vectors requires OpenSearch 2.19"):
            integration_manager._validate_domain_for_s3_vectors(invalid_config)

    def test_hybrid_query_building(self, integration_manager):
        """Test hybrid query construction for OpenSearch."""
        # Test query with both text and vector components
        query = integration_manager._build_hybrid_query(
            query_text="search terms",
            query_vector=[0.1, 0.2, 0.3],
            vector_field="embedding",
            text_fields=["title", "content"],
            k=10
        )
        
        assert 'bool' in query
        assert 'should' in query['bool']
        assert len(query['bool']['should']) == 2  # Text + vector queries
        
        # Verify vector query structure
        vector_query = next((q for q in query['bool']['should'] if 'knn' in q), None)
        assert vector_query is not None
        assert vector_query['knn']['embedding']['vector'] == [0.1, 0.2, 0.3]
        
        # Verify text query structure
        text_query = next((q for q in query['bool']['should'] if 'multi_match' in q), None)
        assert text_query is not None
        assert text_query['multi_match']['query'] == "search terms"

    def test_cost_comparison_between_patterns(self, integration_manager):
        """Test cost comparison functionality between integration patterns."""
        with patch.object(integration_manager, '_get_aws_pricing_data') as mock_pricing:
            mock_pricing.return_value = {
                's3_vectors_storage_per_gb_month': 0.023,
                's3_vectors_query_per_1k': 0.01,
                'opensearch_serverless_ocup_per_hour': 0.24
            }
            
            # Test cost comparison
            comparison = integration_manager._compare_integration_costs(
                mock_pricing.return_value,
                storage_gb=500.0,
                queries_monthly=25000,
                period_days=30
            )
            
            assert 'export_pattern_monthly' in comparison
            assert 'engine_pattern_monthly' in comparison
            assert 'cost_difference' in comparison
            assert 'percentage_savings_engine' in comparison
            assert comparison['engine_pattern_monthly'] < comparison['export_pattern_monthly']

    def test_error_handling_export_failure(self, integration_manager):
        """Test error handling during export operations."""
        with patch.object(integration_manager, '_ensure_serverless_collection') as mock_collection:
            # Mock collection creation failure
            mock_collection.side_effect = Exception("Collection creation failed")
            
            with pytest.raises(OpenSearchIntegrationError, match="Unexpected error during OpenSearch export"):
                integration_manager.export_to_opensearch_serverless(
                    vector_index_arn="arn:aws:s3vectors:us-east-1:123456789012:index/test",
                    collection_name="test-collection"
                )

    def test_error_handling_domain_configuration(self, integration_manager):
        """Test error handling during domain configuration."""
        with patch.object(integration_manager, 'opensearch_client') as mock_opensearch:
            # Mock domain not found
            from botocore.exceptions import ClientError
            mock_opensearch.describe_domain.side_effect = ClientError(
                {'Error': {'Code': 'ResourceNotFoundException'}},
                'DescribeDomain'
            )
            
            with pytest.raises(OpenSearchIntegrationError, match="OpenSearch domain not found"):
                integration_manager.configure_s3_vectors_engine("nonexistent-domain")

    def test_cost_optimization_recommendations(self, integration_manager):
        """Test generation of cost optimization recommendations."""
        # Test recommendations for export pattern with low query volume
        cost_analysis = CostAnalysis(
            pattern=IntegrationPattern.EXPORT,
            storage_cost_monthly=50.0,
            query_cost_per_1k=0.01,
            ingestion_cost_per_gb=0.05,
            estimated_monthly_total=75.0,
            cost_comparison={},
            optimization_recommendations=[]
        )
        
        recommendations = integration_manager._generate_cost_recommendations(
            cost_analysis,
            storage_gb=100.0,
            queries_monthly=5000  # Low query volume
        )
        
        assert len(recommendations) > 0
        assert any("engine pattern" in rec.lower() for rec in recommendations)
        assert any("cach" in rec.lower() for rec in recommendations)

    def test_integration_patterns_enum(self):
        """Test integration pattern enumeration."""
        assert IntegrationPattern.EXPORT.value == "export"
        assert IntegrationPattern.ENGINE.value == "engine"
        assert len(IntegrationPattern) == 2


@pytest.mark.integration
class TestOpenSearchIntegrationReal:
    """Integration tests with real AWS services (requires AWS credentials)."""
    
    @pytest.mark.slow
    def test_real_aws_pricing_data(self):
        """Test retrieving real AWS pricing data."""
        manager = OpenSearchIntegrationManager()
        
        # This would test against real AWS Pricing API
        # Skipped by default to avoid AWS charges
        pytest.skip("Requires real AWS credentials and may incur charges")

    @pytest.mark.real_aws  
    def test_real_opensearch_service_availability(self):
        """Test OpenSearch service availability and client validation."""
        manager = OpenSearchIntegrationManager()
        
        # Test client initialization
        assert hasattr(manager, 'opensearch_client')
        assert hasattr(manager, 'opensearch_serverless_client')
        assert hasattr(manager, 'osis_client')
        
        # Test basic service connectivity (this will work with any AWS account)
        try:
            # Test OpenSearch domains list (may return empty list, which is fine)
            response = manager.opensearch_client.list_domain_names()
            assert 'DomainNames' in response
            
            # Test OpenSearch Serverless collections list (may return empty list)
            collections_response = manager.opensearch_serverless_client.list_collections()
            assert 'collectionSummaries' in collections_response
            
            # Test OpenSearch Ingestion pipelines list (may return empty list)  
            pipelines_response = manager.osis_client.list_pipelines()
            assert 'pipelines' in pipelines_response or 'Pipelines' in pipelines_response
            
        except Exception as e:
            # If we get permission errors, that's still a successful validation
            # that the services exist and our clients are working
            if "AccessDenied" in str(e) or "UnauthorizedOperation" in str(e):
                pytest.skip(f"Insufficient permissions for OpenSearch operations: {e}")
            else:
                # Re-raise other errors
                raise
    
    @pytest.mark.real_aws
    def test_real_aws_cost_analysis_with_pricing_api(self):
        """Test cost analysis with real AWS pricing data."""
        manager = OpenSearchIntegrationManager()
        
        try:
            # Test basic cost monitoring functionality
            cost_analysis = manager.monitor_integration_costs(
                pattern=IntegrationPattern.ENGINE,
                time_period_days=30,
                vector_storage_gb=10.0,
                query_count_monthly=1000
            )
            
            # Validate cost analysis structure
            assert isinstance(cost_analysis, CostAnalysis)
            assert cost_analysis.pattern == IntegrationPattern.ENGINE
            assert cost_analysis.storage_cost_monthly >= 0
            assert cost_analysis.estimated_monthly_total >= 0
            assert len(cost_analysis.optimization_recommendations) > 0
            
            # Test cost comparison
            if cost_analysis.cost_comparison:
                assert 'engine_pattern_monthly' in cost_analysis.cost_comparison
                
        except Exception as e:
            if "AccessDenied" in str(e) or "pricing" in str(e).lower():
                pytest.skip(f"Insufficient permissions for pricing API: {e}")
            else:
                raise
    
    @pytest.mark.real_aws  
    def test_real_opensearch_domain_validation_with_mock_domain(self):
        """Test domain validation logic with mocked domain that follows real patterns."""
        manager = OpenSearchIntegrationManager()
        
        # Test the validation method directly with realistic domain config
        realistic_domain_config = {
            'EngineVersion': 'OpenSearch_2.19',
            'ClusterConfig': {
                'InstanceType': 'm6g.large.search'  # Standard instance, not optimized
            },
            'Processing': False
        }
        
        # This should not raise an error for valid version
        manager._validate_domain_for_s3_vectors(realistic_domain_config)
        
        # Test with old version (should raise error)
        old_version_config = {
            'EngineVersion': 'OpenSearch_2.15',
            'ClusterConfig': {
                'InstanceType': 'm6g.large.search'
            }
        }
        
        with pytest.raises(OpenSearchIntegrationError, match="S3 vectors requires OpenSearch 2.19"):
            manager._validate_domain_for_s3_vectors(old_version_config)
    
    @pytest.mark.real_aws
    def test_hybrid_search_query_building(self):
        """Test hybrid search query building logic."""
        manager = OpenSearchIntegrationManager()
        
        # Test vector-only query
        vector_query = manager._build_hybrid_query(
            query_vector=[0.1] * 1024,
            vector_field="embedding",
            k=5
        )
        
        assert "bool" in vector_query
        assert "should" in vector_query["bool"]
        assert any("knn" in item for item in vector_query["bool"]["should"])
        
        # Test text-only query
        text_query = manager._build_hybrid_query(
            query_text="machine learning vectors",
            text_fields=["content", "title"]
        )
        
        assert "bool" in text_query
        assert "should" in text_query["bool"]
        assert any("multi_match" in item for item in text_query["bool"]["should"])
        
        # Test combined query
        hybrid_query = manager._build_hybrid_query(
            query_text="AI and vector search",
            query_vector=[0.2] * 1024,
            vector_field="embedding",
            text_fields=["content"],
            k=10
        )
        
        assert len(hybrid_query["bool"]["should"]) == 2  # Both vector and text queries
    
    @pytest.mark.real_aws
    def test_cost_report_generation(self):
        """Test cost report generation and structure."""
        manager = OpenSearchIntegrationManager()
        
        # Add some mock data to cost tracker
        manager._cost_tracker['exports'].append({
            'cost_estimate': 15.50,
            'export_id': 'test-export-1',
            'timestamp': datetime.utcnow().isoformat()
        })
        manager._cost_tracker['queries'].append({
            'cost': 0.025,
            'query_type': 'hybrid',
            'timestamp': datetime.utcnow().isoformat()
        })
        manager._cost_tracker['storage_costs']['test-index'] = 12.75
        
        # Generate cost report
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        report = manager.get_cost_report(
            start_date=start_date,
            end_date=end_date,
            include_projections=True
        )
        
        # Validate report structure
        assert 'report_period' in report
        assert 'cost_breakdown' in report
        assert 'activity_summary' in report
        assert 'projections' in report
        
        assert report['cost_breakdown']['total_costs'] > 0
        assert report['activity_summary']['export_count'] == 1
        assert report['activity_summary']['query_count'] == 1
        assert report['projections']['monthly_projection'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])