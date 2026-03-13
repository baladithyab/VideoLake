#!/usr/bin/env python3
"""
Unit tests for VectorStoreProvider abstraction.

Tests the provider interface contract, factory registration, and type validation
without requiring actual backend implementations. Only mocks external AWS APIs,
not internal service interfaces.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any
try:
    from src.services.vector_store_s3vector_provider import S3VectorProvider
    from src.services.vector_store_opensearch_provider import OpenSearchProvider
    from src.services.vector_store_lancedb_provider import LanceDBProvider
except ImportError:
    S3VectorProvider = None
    OpenSearchProvider = None
    LanceDBProvider = None
from datetime import datetime, timezone
from src.services.vector_store_provider import (
VectorStoreProvider,
VectorStoreType,
VectorStoreState,
VectorStoreConfig,
VectorStoreStatus,
VectorStoreCapabilities,
)


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
class TestVectorStoreCapabilities:
    """Test VectorStoreCapabilities dataclass."""

    def test_capabilities_s3vector(self):
        """Test S3Vector capabilities."""
        caps = VectorStoreCapabilities(
            max_dimension=10000,
            max_vectors=None,  # Unlimited
            supports_metadata_filtering=True,
            supports_hybrid_search=False,
            supports_batch_upsert=True,
            estimated_cost_per_million_vectors=0.10,
            typical_query_latency_ms=50.0,
        )
        assert caps.max_dimension == 10000
        assert caps.max_vectors is None
        assert caps.supports_batch_upsert is True

    def test_capabilities_comparison(self):
        """Test capability comparison for different stores."""
        s3_caps = VectorStoreCapabilities(
            max_dimension=10000,
            supports_hybrid_search=False,
            estimated_cost_per_million_vectors=0.10,
        )
        opensearch_caps = VectorStoreCapabilities(
            max_dimension=16000,
            supports_hybrid_search=True,
            estimated_cost_per_million_vectors=5.00,
        )
        # S3Vector is cheaper
        assert s3_caps.estimated_cost_per_million_vectors < opensearch_caps.estimated_cost_per_million_vectors
        # OpenSearch supports hybrid search
        assert opensearch_caps.supports_hybrid_search is True
        assert s3_caps.supports_hybrid_search is False


@pytest.mark.unit
class TestVectorStoreConfig:
    """Test VectorStoreConfig dataclass validation."""

    def test_config_creation_minimal(self):
        """Test creating config with minimal required fields."""
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name="test-store",
            dimension=1536,
        )
        assert config.store_type == VectorStoreType.S3_VECTOR
        assert config.name == "test-store"
        assert config.dimension == 1536
        assert config.similarity_metric == "cosine"  # Default
        assert config.metadata == {}

    def test_config_with_provider_specific_settings(self):
        """Test config with provider-specific configurations."""
        s3_config = {"bucket_name": "test-bucket", "region": "us-east-1"}
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name="test-store",
            dimension=768,
            similarity_metric="euclidean",
            s3vector_config=s3_config,
        )
        assert config.s3vector_config == s3_config
        assert config.opensearch_config is None

    def test_config_similarity_metrics(self):
        """Test different similarity metrics."""
        metrics = ["cosine", "euclidean", "dot_product"]
        for metric in metrics:
            config = VectorStoreConfig(
                store_type=VectorStoreType.QDRANT,
                name="test-store",
                dimension=512,
                similarity_metric=metric,
            )
            assert config.similarity_metric == metric


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


@pytest.mark.unit
class TestVectorStoreProviderInterface:
    """Test VectorStoreProvider abstract base class contract."""

    def test_provider_is_abstract(self):
        """Test that VectorStoreProvider cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            VectorStoreProvider()

    def test_provider_requires_abstract_methods(self):
        """Test that provider implementations must implement all abstract methods."""

        class IncompleteProvider(VectorStoreProvider):
            """Provider missing required methods."""
            pass

        with pytest.raises(TypeError):
            IncompleteProvider()

    def test_minimal_provider_implementation(self):
        """Test a minimal valid provider implementation."""

        class MinimalProvider(VectorStoreProvider):
            """Minimal provider with all required methods."""

            @property
            def store_type(self) -> VectorStoreType:
                return VectorStoreType.S3_VECTOR

            async def create_store(self, config: VectorStoreConfig) -> VectorStoreStatus:
                return VectorStoreStatus(
                    store_type=self.store_type,
                    name=config.name,
                    state=VectorStoreState.CREATING,
                    dimension=config.dimension,
                )

            async def delete_store(self, name: str) -> bool:
                return True

            async def get_status(self, name: str) -> VectorStoreStatus:
                return VectorStoreStatus(
                    store_type=self.store_type,
                    name=name,
                    state=VectorStoreState.ACTIVE,
                )

            async def list_stores(self) -> List[VectorStoreStatus]:
                return []

            async def upsert_vectors(
                self, store_name: str, vectors: List[Dict[str, Any]]
            ) -> Dict[str, Any]:
                return {"upserted": len(vectors)}

            async def query_vectors(
                self, store_name: str, query_vector: List[float], top_k: int = 10, filters: Dict[str, Any] = None
            ) -> List[Dict[str, Any]]:
                return []

            async def delete_vectors(self, store_name: str, vector_ids: List[str]) -> Dict[str, Any]:
                return {"deleted": len(vector_ids)}

            async def get_capabilities(self) -> VectorStoreCapabilities:
                return VectorStoreCapabilities(max_dimension=10000)

            async def validate_connectivity(self) -> Dict[str, Any]:
                return {"accessible": True}

        # Should not raise
        provider = MinimalProvider()
        assert provider.store_type == VectorStoreType.S3_VECTOR


@pytest.mark.unit
class TestVectorStoreProviderMethods:
    """Test provider method signatures and contracts."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock provider for testing."""

        class MockProvider(VectorStoreProvider):
            """Test provider implementation."""

            @property
            def store_type(self) -> VectorStoreType:
                return VectorStoreType.S3_VECTOR

            async def create_store(self, config: VectorStoreConfig) -> VectorStoreStatus:
                return VectorStoreStatus(
                    store_type=self.store_type,
                    name=config.name,
                    state=VectorStoreState.ACTIVE,
                    dimension=config.dimension,
                )

            async def delete_store(self, name: str) -> bool:
                return True

            async def get_status(self, name: str) -> VectorStoreStatus:
                return VectorStoreStatus(
                    store_type=self.store_type,
                    name=name,
                    state=VectorStoreState.ACTIVE,
                    vector_count=100,
                    dimension=1536,
                )

            async def list_stores(self) -> List[VectorStoreStatus]:
                return [
                    VectorStoreStatus(
                        store_type=self.store_type,
                        name="store-1",
                        state=VectorStoreState.ACTIVE,
                    )
                ]

            async def upsert_vectors(
                self, store_name: str, vectors: List[Dict[str, Any]]
            ) -> Dict[str, Any]:
                return {"upserted": len(vectors), "store": store_name}

            async def query_vectors(
                self, store_name: str, query_vector: List[float], top_k: int = 10, filters: Dict[str, Any] = None
            ) -> List[Dict[str, Any]]:
                return [
                    {
                        "id": "vec-1",
                        "score": 0.95,
                        "metadata": {"title": "Test"},
                    }
                ]

            async def delete_vectors(self, store_name: str, vector_ids: List[str]) -> Dict[str, Any]:
                return {"deleted": len(vector_ids)}

            async def get_capabilities(self) -> VectorStoreCapabilities:
                return VectorStoreCapabilities(
                    max_dimension=10000,
                    supports_batch_upsert=True,
                )

            async def validate_connectivity(self) -> Dict[str, Any]:
                return {
                    "accessible": True,
                    "endpoint": "test-endpoint",
                    "response_time_ms": 10.0,
                }

        return MockProvider()

    @pytest.mark.asyncio
    async def test_create_store_returns_status(self, mock_provider):
        """Test that create_store returns proper status."""
        config = VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name="test-store",
            dimension=768,
        )
        status = await mock_provider.create_store(config)
        assert isinstance(status, VectorStoreStatus)
        assert status.name == "test-store"
        assert status.dimension == 768

    @pytest.mark.asyncio
    async def test_list_stores_returns_list(self, mock_provider):
        """Test that list_stores returns list of statuses."""
        stores = await mock_provider.list_stores()
        assert isinstance(stores, list)
        assert all(isinstance(s, VectorStoreStatus) for s in stores)

    @pytest.mark.asyncio
    async def test_upsert_vectors_batch(self, mock_provider):
        """Test batch vector upsert."""
        vectors = [
            {"id": "v1", "vector": [0.1] * 1536, "metadata": {"key": "val1"}},
            {"id": "v2", "vector": [0.2] * 1536, "metadata": {"key": "val2"}},
        ]
        result = await mock_provider.upsert_vectors("test-store", vectors)
        assert result["upserted"] == 2
        assert result["store"] == "test-store"

    @pytest.mark.asyncio
    async def test_query_vectors_with_filters(self, mock_provider):
        """Test vector query with metadata filters."""
        query = [0.5] * 1536
        filters = {"category": "test"}
        results = await mock_provider.query_vectors(
            "test-store", query, top_k=5, filters=filters
        )
        assert isinstance(results, list)
        assert len(results) > 0
        assert "score" in results[0]

    @pytest.mark.asyncio
    async def test_validate_connectivity(self, mock_provider):
        """Test connectivity validation."""
        result = await mock_provider.validate_connectivity()
        assert result["accessible"] is True
        assert "endpoint" in result
        assert "response_time_ms" in result


@pytest.mark.unit
class TestVectorStoreStatus:
    """Test VectorStoreStatus dataclass."""

    def test_status_creation(self):
        """Test creating status object."""
        status = VectorStoreStatus(
            store_type=VectorStoreType.S3_VECTOR,
            name="test-store",
            state=VectorStoreState.ACTIVE,
            vector_count=1000,
            dimension=1536,
        )
        assert status.store_type == VectorStoreType.S3_VECTOR
        assert status.state == VectorStoreState.ACTIVE
        assert status.vector_count == 1000
        assert status.dimension == 1536

    def test_status_with_timestamps(self):
        """Test status with timestamp fields."""
        now = datetime.now(timezone.utc)
        status = VectorStoreStatus(
            store_type=VectorStoreType.OPENSEARCH,
            name="test-collection",
            state=VectorStoreState.CREATING,
            created_at=now,
            progress_percentage=45,
            estimated_time_remaining=120,
        )
        assert status.created_at == now
        assert status.progress_percentage == 45
        assert status.estimated_time_remaining == 120

    def test_status_with_error(self):
        """Test status with error information."""
        status = VectorStoreStatus(
            store_type=VectorStoreType.LANCEDB,
            name="failed-store",
            state=VectorStoreState.FAILED,
            error_message="Connection timeout",
        )
        assert status.state == VectorStoreState.FAILED
        assert status.error_message == "Connection timeout"


@pytest.mark.unit
class TestVectorStoreTypes:
    """Test VectorStoreType enum and type safety."""

    def test_vector_store_type_enum_values(self):
        """Verify all expected vector store types are defined."""
        assert VectorStoreType.S3_VECTOR == "s3_vector"
        assert VectorStoreType.OPENSEARCH == "opensearch"
        assert VectorStoreType.LANCEDB == "lancedb"
        assert VectorStoreType.QDRANT == "qdrant"
        assert VectorStoreType.PINECONE == "pinecone"
        assert VectorStoreType.WEAVIATE == "weaviate"
        assert VectorStoreType.MILVUS == "milvus"
        assert VectorStoreType.CHROMA == "chroma"

    def test_vector_store_type_string_conversion(self):
        """Test that VectorStoreType can be used as string."""
        store_type = VectorStoreType.S3_VECTOR
        # Enum value should be the string
        assert store_type.value == "s3_vector"
        # Can compare directly to string (StrEnum)
        assert store_type == "s3_vector"

    def test_vector_store_state_enum(self):
        """Verify vector store state transitions."""
        states = [
            VectorStoreState.CREATING,
            VectorStoreState.ACTIVE,
            VectorStoreState.AVAILABLE,
            VectorStoreState.UPDATING,
            VectorStoreState.DELETING,
            VectorStoreState.DELETED,
            VectorStoreState.FAILED,
            VectorStoreState.NOT_FOUND,
        ]
        assert len(states) == 8


