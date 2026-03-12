"""
S3Vector provider integration tests.

Tests real S3Vector operations (create bucket, create index, insert, query, delete)
using actual AWS S3Vectors service. Uses moto for unit tests, real AWS for integration.
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from src.services.vector_store_provider import (
    VectorStoreConfig,
    VectorStoreType,
    VectorStoreState,
)


@pytest.mark.integration
@pytest.mark.provider
class TestS3VectorProviderUnit:
    """Unit tests for S3Vector provider using moto mocks."""

    @pytest.fixture
    async def s3vector_provider(self):
        """Create S3Vector provider instance."""
        from src.services.vector_store_s3vector_provider import S3VectorProvider

        provider = S3VectorProvider()
        yield provider
        # Cleanup
        await provider.cleanup() if hasattr(provider, 'cleanup') else None

    @pytest.mark.asyncio
    async def test_provider_type(self, s3vector_provider):
        """Test that provider identifies as S3_VECTOR."""
        assert s3vector_provider.store_type == VectorStoreType.S3_VECTOR

    @pytest.mark.asyncio
    async def test_get_capabilities(self, s3vector_provider):
        """Test S3Vector capabilities."""
        caps = await s3vector_provider.get_capabilities()

        assert caps.max_dimension > 0
        assert caps.supports_batch_upsert is True
        # S3Vector typically doesn't support hybrid search
        assert caps.supports_hybrid_search is False

    @pytest.mark.asyncio
    async def test_validate_connectivity_without_aws(self, s3vector_provider):
        """Test connectivity validation (may fail without AWS creds)."""
        result = await s3vector_provider.validate_connectivity()

        # Should return dict with accessibility status
        assert isinstance(result, dict)
        assert "accessible" in result


@pytest.mark.requires_aws
@pytest.mark.integration
@pytest.mark.provider
@pytest.mark.slow
class TestS3VectorProviderIntegration:
    """Integration tests with real AWS S3Vectors service."""

    @pytest.fixture
    async def s3vector_provider(self):
        """Create S3Vector provider for real AWS tests."""
        from src.services.vector_store_s3vector_provider import S3VectorProvider

        provider = S3VectorProvider()
        yield provider

    @pytest.fixture
    def test_store_config(self):
        """Generate test store configuration."""
        import time
        timestamp = int(time.time())

        return VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name=f"test-s3v-{timestamp}",
            dimension=1536,
            similarity_metric="cosine",
            s3vector_config={
                "region": "us-east-1",
            }
        )

    @pytest.mark.asyncio
    async def test_validate_connectivity(self, s3vector_provider):
        """Test connectivity to S3Vectors service."""
        result = await s3vector_provider.validate_connectivity()

        assert result["accessible"] is True
        assert "region" in result or "endpoint" in result

    @pytest.mark.asyncio
    async def test_list_stores_returns_list(self, s3vector_provider):
        """Test listing S3Vector stores."""
        stores = await s3vector_provider.list_stores()

        assert isinstance(stores, list)
        # Each store should have proper status
        for store in stores:
            assert hasattr(store, 'store_type')
            assert hasattr(store, 'name')
            assert hasattr(store, 'state')

    @pytest.mark.asyncio
    async def test_create_and_delete_store_lifecycle(self, s3vector_provider, test_store_config):
        """Test complete store lifecycle: create → verify → delete."""
        store_name = test_store_config.name

        try:
            # Create store
            status = await s3vector_provider.create_store(test_store_config)

            assert status.name == store_name
            assert status.state in [VectorStoreState.CREATING, VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]
            assert status.dimension == 1536

            # Wait for store to be active
            max_wait = 60
            waited = 0
            while waited < max_wait:
                status = await s3vector_provider.get_status(store_name)
                if status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]:
                    break
                await asyncio.sleep(2)
                waited += 2

            assert status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]

        finally:
            # Cleanup: delete store
            try:
                deleted = await s3vector_provider.delete_store(store_name)
                assert deleted is True
            except Exception as e:
                pytest.fail(f"Failed to cleanup test store: {e}")


@pytest.mark.real_aws
@pytest.mark.expensive
@pytest.mark.e2e
@pytest.mark.slow
class TestS3VectorProviderE2E:
    """End-to-end tests with real S3Vector operations (costs money!)."""

    @pytest.fixture
    async def s3vector_provider(self):
        """Create S3Vector provider for e2e tests."""
        from src.services.vector_store_s3vector_provider import S3VectorProvider

        provider = S3VectorProvider()
        yield provider

    @pytest.fixture
    def test_store_config(self):
        """Generate test store configuration."""
        import time
        timestamp = int(time.time())

        return VectorStoreConfig(
            store_type=VectorStoreType.S3_VECTOR,
            name=f"e2e-test-{timestamp}",
            dimension=1536,
            similarity_metric="cosine",
        )

    @pytest.mark.asyncio
    async def test_full_vector_operations(self, s3vector_provider, test_store_config):
        """Test complete vector operations: insert → query → delete."""
        store_name = test_store_config.name

        try:
            # 1. Create store
            status = await s3vector_provider.create_store(test_store_config)
            assert status.name == store_name

            # Wait for active
            for _ in range(30):
                status = await s3vector_provider.get_status(store_name)
                if status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]:
                    break
                await asyncio.sleep(2)

            assert status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]

            # 2. Insert vectors
            test_vectors = [
                {
                    "id": "vec-1",
                    "vector": [0.1] * 1536,
                    "metadata": {"title": "Test Document 1", "category": "test"}
                },
                {
                    "id": "vec-2",
                    "vector": [0.2] * 1536,
                    "metadata": {"title": "Test Document 2", "category": "test"}
                },
                {
                    "id": "vec-3",
                    "vector": [0.3] * 1536,
                    "metadata": {"title": "Test Document 3", "category": "demo"}
                },
            ]

            result = await s3vector_provider.upsert_vectors(store_name, test_vectors)
            assert result["upserted"] == 3 or "success" in result

            # 3. Query vectors
            query_vector = [0.15] * 1536  # Should match vec-1 closely
            results = await s3vector_provider.query_vectors(
                store_name,
                query_vector,
                top_k=2
            )

            assert len(results) > 0
            # First result should be closest match
            assert results[0]["id"] in ["vec-1", "vec-2"]
            assert "score" in results[0]

            # 4. Query with filters
            filtered_results = await s3vector_provider.query_vectors(
                store_name,
                query_vector,
                top_k=5,
                filters={"category": "test"}
            )

            # Should only return vectors with category="test"
            for result in filtered_results:
                if "metadata" in result:
                    assert result["metadata"].get("category") == "test"

            # 5. Delete specific vectors
            delete_result = await s3vector_provider.delete_vectors(
                store_name,
                ["vec-1", "vec-2"]
            )
            assert delete_result["deleted"] == 2 or "success" in delete_result

            # 6. Verify deletion
            remaining_results = await s3vector_provider.query_vectors(
                store_name,
                query_vector,
                top_k=10
            )

            # Should only have vec-3 left
            remaining_ids = [r["id"] for r in remaining_results]
            assert "vec-1" not in remaining_ids
            assert "vec-2" not in remaining_ids
            assert "vec-3" in remaining_ids

        finally:
            # Cleanup
            try:
                await s3vector_provider.delete_store(store_name)
            except Exception as e:
                pytest.fail(f"Failed to cleanup: {e}")

    @pytest.mark.asyncio
    async def test_batch_upsert_performance(self, s3vector_provider, test_store_config):
        """Test batch upsert performance with larger dataset."""
        store_name = test_store_config.name

        try:
            # Create store
            await s3vector_provider.create_store(test_store_config)

            # Wait for active
            for _ in range(30):
                status = await s3vector_provider.get_status(store_name)
                if status.state in [VectorStoreState.ACTIVE, VectorStoreState.AVAILABLE]:
                    break
                await asyncio.sleep(2)

            # Generate 100 test vectors
            batch_vectors = [
                {
                    "id": f"batch-vec-{i}",
                    "vector": [float(i) / 100.0] * 1536,
                    "metadata": {"index": i, "batch": "test"}
                }
                for i in range(100)
            ]

            # Time the batch upsert
            import time
            start_time = time.time()

            result = await s3vector_provider.upsert_vectors(store_name, batch_vectors)

            elapsed = time.time() - start_time

            assert result["upserted"] == 100 or "success" in result
            # Should complete in reasonable time (< 30 seconds)
            assert elapsed < 30.0, f"Batch upsert took too long: {elapsed}s"

        finally:
            try:
                await s3vector_provider.delete_store(store_name)
            except:
                pass
