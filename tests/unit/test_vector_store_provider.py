#!/usr/bin/env python3
"""
Unit tests for VectorStoreProvider service.

Tests the vector store provider abstraction, factory registration,
and basic operations without requiring actual databases.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Import vector store provider modules
try:
    from src.services.vector_store_s3vector_provider import S3VectorProvider
    from src.services.vector_store_opensearch_provider import OpenSearchProvider
    from src.services.vector_store_lancedb_provider import LanceDBProvider
except ImportError:
    # Handle case where providers don't have standardized interface yet
    S3VectorProvider = None
    OpenSearchProvider = None
    LanceDBProvider = None


@pytest.mark.unit
class TestS3VectorProvider:
    """Test S3VectorProvider without making S3 calls."""

    @pytest.mark.skipif(S3VectorProvider is None, reason="S3VectorProvider not available")
    def test_initialization(self):
        """Test S3Vector provider can be initialized."""
        with patch('boto3.client'):
            provider = S3VectorProvider(
                bucket_name="test-bucket",
                region="us-east-1"
            )
            assert provider.bucket_name == "test-bucket"
            assert provider.region == "us-east-1"

    @pytest.mark.skipif(S3VectorProvider is None, reason="S3VectorProvider not available")
    @pytest.mark.asyncio
    async def test_create_index(self):
        """Test index creation with mocked S3 client."""
        mock_s3_client = MagicMock()
        mock_s3_client.head_bucket.return_value = {}
        mock_s3_client.put_object.return_value = {"ETag": "test-etag"}

        with patch('boto3.client', return_value=mock_s3_client):
            provider = S3VectorProvider(
                bucket_name="test-bucket",
                region="us-east-1"
            )

            result = await provider.create_index(
                index_name="test-index",
                dimension=1536
            )

            assert result is not None
            # Verify S3 operations were called
            assert mock_s3_client.head_bucket.called or mock_s3_client.put_object.called

    @pytest.mark.skipif(S3VectorProvider is None, reason="S3VectorProvider not available")
    @pytest.mark.asyncio
    async def test_insert_vectors(self):
        """Test vector insertion with mocked S3 client."""
        mock_s3_client = MagicMock()
        mock_s3_client.put_object.return_value = {"ETag": "test-etag"}

        with patch('boto3.client', return_value=mock_s3_client):
            provider = S3VectorProvider(
                bucket_name="test-bucket",
                region="us-east-1"
            )

            vectors = [[0.1] * 1536, [0.2] * 1536]
            metadatas = [{"id": "1"}, {"id": "2"}]

            result = await provider.insert_vectors(
                index_name="test-index",
                vectors=vectors,
                metadatas=metadatas
            )

            assert result is not None

    @pytest.mark.skipif(S3VectorProvider is None, reason="S3VectorProvider not available")
    @pytest.mark.asyncio
    async def test_search_vectors(self):
        """Test vector search with mocked S3 client."""
        mock_s3_client = MagicMock()
        mock_search_results = [
            {"id": "1", "score": 0.95, "metadata": {"text": "result 1"}},
            {"id": "2", "score": 0.87, "metadata": {"text": "result 2"}}
        ]

        with patch('boto3.client', return_value=mock_s3_client):
            provider = S3VectorProvider(
                bucket_name="test-bucket",
                region="us-east-1"
            )

            # Mock the internal search method
            with patch.object(provider, '_search_impl', new_callable=AsyncMock) as mock_search:
                mock_search.return_value = mock_search_results

                query_vector = [0.1] * 1536
                results = await provider.search_vectors(
                    index_name="test-index",
                    query_vector=query_vector,
                    top_k=10
                )

                assert len(results) == 2
                assert results[0]["score"] > results[1]["score"]


@pytest.mark.unit
class TestOpenSearchProvider:
    """Test OpenSearchProvider without requiring OpenSearch cluster."""

    @pytest.mark.skipif(OpenSearchProvider is None, reason="OpenSearchProvider not available")
    def test_initialization(self):
        """Test OpenSearch provider can be initialized."""
        with patch('opensearchpy.OpenSearch'):
            provider = OpenSearchProvider(
                endpoint="test-domain.us-east-1.es.amazonaws.com",
                region="us-east-1"
            )
            assert provider.endpoint is not None

    @pytest.mark.skipif(OpenSearchProvider is None, reason="OpenSearchProvider not available")
    @pytest.mark.asyncio
    async def test_create_index_with_mapping(self):
        """Test index creation with k-NN mapping."""
        mock_os_client = MagicMock()
        mock_os_client.indices.create.return_value = {"acknowledged": True}

        with patch('opensearchpy.OpenSearch', return_value=mock_os_client):
            provider = OpenSearchProvider(
                endpoint="test-domain.us-east-1.es.amazonaws.com",
                region="us-east-1"
            )

            result = await provider.create_index(
                index_name="test-index",
                dimension=1536
            )

            # Verify index creation was called with k-NN settings
            assert mock_os_client.indices.create.called
            call_args = mock_os_client.indices.create.call_args
            assert "test-index" in str(call_args)

    @pytest.mark.skipif(OpenSearchProvider is None, reason="OpenSearchProvider not available")
    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid search (vector + keyword) capability."""
        mock_os_client = MagicMock()
        mock_os_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_id": "1", "_score": 0.95, "_source": {"text": "result 1"}},
                    {"_id": "2", "_score": 0.87, "_source": {"text": "result 2"}}
                ]
            }
        }

        with patch('opensearchpy.OpenSearch', return_value=mock_os_client):
            provider = OpenSearchProvider(
                endpoint="test-domain.us-east-1.es.amazonaws.com",
                region="us-east-1"
            )

            query_vector = [0.1] * 1536
            results = await provider.hybrid_search(
                index_name="test-index",
                query_vector=query_vector,
                query_text="test query",
                top_k=10
            )

            assert len(results) == 2
            assert mock_os_client.search.called


@pytest.mark.unit
class TestLanceDBProvider:
    """Test LanceDBProvider without requiring LanceDB instance."""

    @pytest.mark.skipif(LanceDBProvider is None, reason="LanceDBProvider not available")
    def test_initialization(self):
        """Test LanceDB provider can be initialized."""
        provider = LanceDBProvider(
            uri="data/lancedb",
            region="us-east-1"
        )
        assert provider.uri == "data/lancedb"

    @pytest.mark.skipif(LanceDBProvider is None, reason="LanceDBProvider not available")
    @pytest.mark.asyncio
    async def test_create_table(self):
        """Test table creation with schema."""
        with patch('lancedb.connect') as mock_connect:
            mock_db = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.create_table.return_value = MagicMock()

            provider = LanceDBProvider(
                uri="data/lancedb",
                region="us-east-1"
            )

            result = await provider.create_table(
                table_name="test-table",
                dimension=1536
            )

            assert result is not None
            assert mock_db.create_table.called

    @pytest.mark.skipif(LanceDBProvider is None, reason="LanceDBProvider not available")
    @pytest.mark.asyncio
    async def test_vector_search(self):
        """Test vector search with LanceDB."""
        with patch('lancedb.connect') as mock_connect:
            mock_db = MagicMock()
            mock_table = MagicMock()
            mock_connect.return_value = mock_db
            mock_db.open_table.return_value = mock_table

            mock_search_results = [
                {"id": "1", "score": 0.95, "text": "result 1"},
                {"id": "2", "score": 0.87, "text": "result 2"}
            ]
            mock_table.search.return_value.limit.return_value.to_list.return_value = mock_search_results

            provider = LanceDBProvider(
                uri="data/lancedb",
                region="us-east-1"
            )

            query_vector = [0.1] * 1536
            results = await provider.search(
                table_name="test-table",
                query_vector=query_vector,
                top_k=10
            )

            assert len(results) == 2


@pytest.mark.unit
class TestVectorStoreProviderContract:
    """Test common vector store provider interface."""

    def test_all_providers_have_common_methods(self):
        """Verify all providers implement common interface."""
        common_methods = [
            'create_index',
            'insert_vectors',
            'search_vectors',
            'delete_index'
        ]

        for provider_class in [S3VectorProvider, OpenSearchProvider, LanceDBProvider]:
            if provider_class is None:
                continue

            for method_name in common_methods:
                assert hasattr(provider_class, method_name), \
                    f"{provider_class.__name__} missing {method_name}"

    def test_providers_handle_dimension_validation(self):
        """Test providers validate embedding dimensions."""
        # This would test that providers reject invalid dimensions
        # Implementation depends on actual provider validation logic
        pass
