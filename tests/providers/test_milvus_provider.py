"""
Milvus/Zilliz Cloud provider unit and integration tests.

Tests Milvus provider operations (create collection, insert, query, delete)
using mocked pymilvus for unit tests and optional real Milvus/Zilliz for integration.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
from datetime import datetime, timezone

from src.services.vector_store_provider import (
    VectorStoreConfig,
    VectorStoreType,
    VectorStoreState,
)


@pytest.mark.unit
@pytest.mark.provider
class TestMilvusProviderUnit:
    """Unit tests for Milvus provider with mocked dependencies."""

    @pytest.fixture
    def mock_pymilvus(self):
        """Mock pymilvus module."""
        with patch.dict('sys.modules', {
            'pymilvus': MagicMock(),
            'pymilvus.connections': MagicMock(),
            'pymilvus.Collection': MagicMock(),
            'pymilvus.CollectionSchema': MagicMock(),
            'pymilvus.FieldSchema': MagicMock(),
            'pymilvus.DataType': MagicMock(),
            'pymilvus.utility': MagicMock()
        }):
            yield

    @pytest.fixture
    def milvus_provider(self, mock_pymilvus):
        """Create Milvus provider instance with mocked pymilvus."""
        from src.services.vector_store_milvus_provider import MilvusProvider

        with patch.dict('os.environ', {
            'MILVUS_HOST': 'localhost',
            'MILVUS_PORT': '19530'
        }):
            provider = MilvusProvider()
            # Mock the connection
            provider.utility = MagicMock()
            provider.Collection = MagicMock()
            yield provider

    def test_provider_type(self, milvus_provider):
        """Test that provider identifies as MILVUS."""
        assert milvus_provider.store_type == VectorStoreType.MILVUS

    def test_get_capabilities(self, milvus_provider):
        """Test Milvus capabilities."""
        caps = milvus_provider.get_capabilities()

        assert caps.max_dimension == 32768  # Milvus supports up to 32K dimensions
        assert caps.max_vectors is None  # Unlimited (billions)
        assert caps.supports_metadata_filtering is True
        assert caps.supports_hybrid_search is True
        assert caps.supports_batch_upsert is True
        assert caps.supports_sparse_vectors is True
        assert caps.estimated_cost_per_million_vectors == 2.5

    def test_metric_type_conversion(self, milvus_provider):
        """Test similarity metric to Milvus metric type conversion."""
        assert milvus_provider._get_metric_type("cosine") == "COSINE"
        assert milvus_provider._get_metric_type("euclidean") == "L2"
        assert milvus_provider._get_metric_type("dot_product") == "IP"
        assert milvus_provider._get_metric_type("unknown") == "COSINE"  # default

    def test_create_collection_success(self, milvus_provider):
        """Test successful collection creation."""
        # Mock utility.has_collection to return False (collection doesn't exist)
        milvus_provider.utility.has_collection = MagicMock(return_value=False)

        # Mock Collection creation
        mock_collection = MagicMock()
        mock_collection.create_index = MagicMock()
        milvus_provider.Collection = MagicMock(return_value=mock_collection)

        config = VectorStoreConfig(
            store_type=VectorStoreType.MILVUS,
            name="test-collection",
            dimension=1536,
            similarity_metric="cosine"
        )

        status = milvus_provider.create(config)

        assert status.state == VectorStoreState.ACTIVE
        assert status.name == "test-collection"
        assert status.dimension == 1536
        milvus_provider.Collection.assert_called_once()
        mock_collection.create_index.assert_called_once()

    def test_create_collection_already_exists(self, milvus_provider):
        """Test creation when collection already exists."""
        milvus_provider.utility.has_collection = MagicMock(return_value=True)

        # Mock get_status to return existing collection
        mock_collection = MagicMock()
        mock_collection.num_entities = 100
        mock_collection.config.params.vectors.size = 1536
        milvus_provider.Collection = MagicMock(return_value=mock_collection)

        config = VectorStoreConfig(
            store_type=VectorStoreType.MILVUS,
            name="existing-collection",
            dimension=1536
        )

        status = milvus_provider.create(config)

        # Should return status of existing collection
        assert status.state == VectorStoreState.ACTIVE
        assert status.name == "existing-collection"

    def test_delete_collection_success(self, milvus_provider):
        """Test successful collection deletion."""
        milvus_provider.utility.has_collection = MagicMock(return_value=True)
        milvus_provider.utility.drop_collection = MagicMock()

        status = milvus_provider.delete("test-collection")

        assert status.state == VectorStoreState.DELETED
        assert status.name == "test-collection"
        milvus_provider.utility.drop_collection.assert_called_once_with("test-collection")

    def test_delete_collection_not_found(self, milvus_provider):
        """Test deletion when collection doesn't exist."""
        milvus_provider.utility.has_collection = MagicMock(return_value=False)

        status = milvus_provider.delete("nonexistent-collection")

        assert status.state == VectorStoreState.NOT_FOUND
        assert "not found" in status.error_message.lower()

    def test_get_status_active_collection(self, milvus_provider):
        """Test getting status of an active collection."""
        milvus_provider.utility.has_collection = MagicMock(return_value=True)

        mock_collection = MagicMock()
        mock_collection.num_entities = 1000
        mock_collection.load = MagicMock()
        milvus_provider.Collection = MagicMock(return_value=mock_collection)

        status = milvus_provider.get_status("test-collection")

        assert status.state == VectorStoreState.ACTIVE
        assert status.vector_count == 1000
        mock_collection.load.assert_called_once()

    def test_list_stores(self, milvus_provider):
        """Test listing all collections."""
        milvus_provider.utility.list_collections = MagicMock(
            return_value=["collection1", "collection2", "collection3"]
        )

        stores = milvus_provider.list_stores()

        assert len(stores) == 3
        assert all(store.store_type == VectorStoreType.MILVUS for store in stores)
        assert [store.name for store in stores] == ["collection1", "collection2", "collection3"]

    def test_upsert_vectors_success(self, milvus_provider):
        """Test successful vector upsert."""
        milvus_provider.utility.has_collection = MagicMock(return_value=True)

        mock_collection = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.primary_keys = ["id1", "id2", "id3"]
        mock_collection.insert = MagicMock(return_value=mock_insert_result)
        mock_collection.flush = MagicMock()
        milvus_provider.Collection = MagicMock(return_value=mock_collection)

        vectors = [
            {"id": "vec1", "values": [0.1] * 128, "metadata": {"tag": "test"}},
            {"id": "vec2", "values": [0.2] * 128, "metadata": {"tag": "test"}},
            {"id": "vec3", "values": [0.3] * 128, "metadata": {"tag": "test"}}
        ]

        result = milvus_provider.upsert_vectors("test-collection", vectors)

        assert result["success"] is True
        assert result["upserted_count"] == 3
        mock_collection.insert.assert_called_once()
        mock_collection.flush.assert_called_once()

    def test_query_vectors_success(self, milvus_provider):
        """Test successful vector query."""
        milvus_provider.utility.has_collection = MagicMock(return_value=True)

        # Mock search results
        mock_hit1 = MagicMock()
        mock_hit1.id = "vec1"
        mock_hit1.distance = 0.95
        mock_hit1.entity = MagicMock()
        mock_hit1.entity.get = MagicMock(return_value={"tag": "test1"})

        mock_hit2 = MagicMock()
        mock_hit2.id = "vec2"
        mock_hit2.distance = 0.90
        mock_hit2.entity = MagicMock()
        mock_hit2.entity.get = MagicMock(return_value={"tag": "test2"})

        mock_hits = [mock_hit1, mock_hit2]

        mock_collection = MagicMock()
        mock_collection.load = MagicMock()
        mock_collection.search = MagicMock(return_value=[mock_hits])
        milvus_provider.Collection = MagicMock(return_value=mock_collection)

        query_vector = [0.5] * 128
        results = milvus_provider.query("test-collection", query_vector, top_k=10)

        assert len(results) == 2
        assert results[0]["id"] == "vec1"
        assert results[0]["score"] == 0.95
        assert results[1]["id"] == "vec2"
        mock_collection.search.assert_called_once()

    def test_validate_connectivity_success(self, milvus_provider):
        """Test successful connectivity validation."""
        milvus_provider.utility.list_collections = MagicMock(return_value=["col1", "col2"])

        result = milvus_provider.validate_connectivity()

        assert result["accessible"] is True
        assert result["health_status"] == "healthy"
        assert result["details"]["collection_count"] == 2
        assert result["error_message"] is None

    def test_validate_connectivity_failure(self, milvus_provider):
        """Test connectivity validation failure."""
        milvus_provider.utility.list_collections = MagicMock(
            side_effect=Exception("Connection refused")
        )

        result = milvus_provider.validate_connectivity()

        assert result["accessible"] is False
        assert result["health_status"] == "unhealthy"
        assert "refused" in result["error_message"].lower()


@pytest.mark.integration
@pytest.mark.provider
@pytest.mark.requires_milvus
@pytest.mark.slow
class TestMilvusProviderIntegration:
    """Integration tests with real Milvus/Zilliz Cloud service."""

    @pytest.fixture
    def milvus_provider(self):
        """Create Milvus provider for real Milvus tests."""
        try:
            from src.services.vector_store_milvus_provider import MilvusProvider
            provider = MilvusProvider()
            yield provider
        except ImportError:
            pytest.skip("pymilvus not installed")

    @pytest.fixture
    def test_store_config(self):
        """Generate test store configuration."""
        import time
        timestamp = int(time.time())

        return VectorStoreConfig(
            store_type=VectorStoreType.MILVUS,
            name=f"test_milvus_{timestamp}",
            dimension=128,
            similarity_metric="cosine"
        )

    def test_full_lifecycle(self, milvus_provider, test_store_config):
        """Test full lifecycle: create, upsert, query, delete."""
        # Create collection
        create_status = milvus_provider.create(test_store_config)
        assert create_status.state == VectorStoreState.ACTIVE

        try:
            # Upsert vectors
            vectors = [
                {"id": f"vec{i}", "values": [float(i)] * 128, "metadata": {"index": i}}
                for i in range(10)
            ]
            upsert_result = milvus_provider.upsert_vectors(test_store_config.name, vectors)
            assert upsert_result["success"] is True
            assert upsert_result["upserted_count"] == 10

            # Query vectors
            query_vector = [1.0] * 128
            results = milvus_provider.query(test_store_config.name, query_vector, top_k=5)
            assert len(results) > 0

            # Get status
            status = milvus_provider.get_status(test_store_config.name)
            assert status.state == VectorStoreState.ACTIVE
            assert status.vector_count == 10

        finally:
            # Cleanup: Delete collection
            delete_status = milvus_provider.delete(test_store_config.name, force=True)
            assert delete_status.state == VectorStoreState.DELETED
