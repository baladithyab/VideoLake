#!/usr/bin/env python3
"""
Provider interface contract tests (TDD stubs).

These tests define the expected behavior for provider interfaces BEFORE
Wave 2 implementation completes. Import errors are expected until the
implementations land.

Tests are written to validate:
- VectorStoreProvider ABC contract
- EmbeddingProvider interface (when implemented)
- Provider factory pattern
- Provider connectivity validation

Mark tests as @pytest.mark.provider and @pytest.mark.unit.
"""

from unittest.mock import MagicMock

import pytest

# ============================================================================
# VectorStoreProvider Interface Tests
# ============================================================================

@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_provider_interface_exists():
    """Test that VectorStoreProvider ABC exists and can be imported."""
    from src.services.vector_store_provider import VectorStoreProvider

    # VectorStoreProvider should be an abstract base class
    assert hasattr(VectorStoreProvider, "__abstractmethods__")
    assert len(VectorStoreProvider.__abstractmethods__) > 0


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_provider_required_methods():
    """Test that VectorStoreProvider defines all required abstract methods."""
    from src.services.vector_store_provider import VectorStoreProvider

    required_methods = {
        "store_type",
        "create",
        "delete",
        "get_status",
        "list_stores",
        "upsert_vectors",
        "query",
        "validate_connectivity"
    }

    abstract_methods = VectorStoreProvider.__abstractmethods__
    for method in required_methods:
        assert method in abstract_methods, (
            f"VectorStoreProvider should define abstract method: {method}"
        )


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_config_dataclass():
    """Test that VectorStoreConfig dataclass has required fields."""
    from src.services.vector_store_provider import VectorStoreConfig, VectorStoreType

    # Create a config instance
    config = VectorStoreConfig(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        dimension=1536
    )

    assert config.store_type == VectorStoreType.S3_VECTOR
    assert config.name == "test-store"
    assert config.dimension == 1536
    assert config.similarity_metric == "cosine"  # default value


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_status_dataclass():
    """Test that VectorStoreStatus dataclass has required fields."""
    from src.services.vector_store_provider import (
        VectorStoreState,
        VectorStoreStatus,
        VectorStoreType,
    )

    status = VectorStoreStatus(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        state=VectorStoreState.ACTIVE
    )

    assert status.store_type == VectorStoreType.S3_VECTOR
    assert status.name == "test-store"
    assert status.state == VectorStoreState.ACTIVE
    assert status.vector_count == 0  # default value


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_type_enum():
    """Test that VectorStoreType enum has expected values."""
    from src.services.vector_store_provider import VectorStoreType

    # Currently implemented backends
    assert hasattr(VectorStoreType, "S3_VECTOR")
    assert hasattr(VectorStoreType, "OPENSEARCH")
    assert hasattr(VectorStoreType, "LANCEDB")
    assert hasattr(VectorStoreType, "QDRANT")


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_state_enum():
    """Test that VectorStoreState enum has expected values."""
    from src.services.vector_store_provider import VectorStoreState

    expected_states = [
        "CREATING",
        "ACTIVE",
        "AVAILABLE",
        "UPDATING",
        "DELETING",
        "DELETED",
        "FAILED",
        "NOT_FOUND"
    ]

    for state in expected_states:
        assert hasattr(VectorStoreState, state), (
            f"VectorStoreState should have {state} state"
        )


# ============================================================================
# VectorStoreProviderFactory Tests
# ============================================================================

@pytest.mark.provider
@pytest.mark.unit
def test_provider_factory_exists():
    """Test that VectorStoreProviderFactory exists."""
    from src.services.vector_store_provider import VectorStoreProviderFactory

    assert hasattr(VectorStoreProviderFactory, "register_provider")
    assert hasattr(VectorStoreProviderFactory, "create_provider")
    assert hasattr(VectorStoreProviderFactory, "get_available_providers")


@pytest.mark.provider
@pytest.mark.unit
def test_provider_factory_registration():
    """Test provider factory registration mechanism."""
    from src.services.vector_store_provider import (
        VectorStoreProvider,
        VectorStoreProviderFactory,
        VectorStoreType,
    )

    # Create a mock provider class
    class MockProvider(VectorStoreProvider):
        @property
        def store_type(self):
            return VectorStoreType.S3_VECTOR

        def create(self, config):
            pass

        def delete(self, name, force=False):
            pass

        def get_status(self, name):
            pass

        def list_stores(self):
            pass

        def upsert_vectors(self, name, vectors):
            pass

        def query(self, name, query_vector, top_k=10, filter_metadata=None):
            pass

        def validate_connectivity(self):
            pass

    # Register the provider
    VectorStoreProviderFactory.register_provider(
        VectorStoreType.S3_VECTOR,
        MockProvider
    )

    # Check that provider is available
    available = VectorStoreProviderFactory.get_available_providers()
    assert VectorStoreType.S3_VECTOR in available


@pytest.mark.provider
@pytest.mark.unit
def test_mock_provider_validate_connectivity():
    """Test that mock provider implements validate_connectivity correctly."""
    from tests.conftest import mock_vector_store_provider

    provider = mock_vector_store_provider()
    result = provider.validate_connectivity()

    # Result should have expected keys
    assert "accessible" in result
    assert "endpoint" in result
    assert "response_time_ms" in result
    assert "health_status" in result

    # Mock should return healthy status
    assert result["accessible"] is True
    assert result["health_status"] == "healthy"


# ============================================================================
# EmbeddingProvider Interface Tests (TDD - will pass when implemented)
# ============================================================================

@pytest.mark.provider
@pytest.mark.unit
@pytest.mark.skip(reason="EmbeddingProvider interface not yet implemented - Wave 2 TODO")
def test_embedding_provider_interface_exists():
    """
    Test that EmbeddingProvider ABC exists.

    This is a TDD stub - the import will fail until Wave 2 implements
    the embedding provider abstraction.
    """
    # TODO: Update import path when Wave 2 implements this
    from src.services.embedding_provider import EmbeddingProvider

    assert hasattr(EmbeddingProvider, "__abstractmethods__")


@pytest.mark.provider
@pytest.mark.unit
@pytest.mark.skip(reason="EmbeddingProvider interface not yet implemented - Wave 2 TODO")
def test_embedding_provider_required_methods():
    """
    Test that EmbeddingProvider defines required abstract methods.

    Expected methods:
    - generate_embedding(text: str) -> List[float]
    - generate_batch_embeddings(texts: List[str]) -> List[List[float]]
    - get_dimension() -> int
    - get_model_id() -> str
    - validate_connectivity() -> bool
    """
    from src.services.embedding_provider import EmbeddingProvider

    required_methods = {
        "generate_embedding",
        "generate_batch_embeddings",
        "get_dimension",
        "get_model_id",
        "validate_connectivity"
    }

    abstract_methods = EmbeddingProvider.__abstractmethods__
    for method in required_methods:
        assert method in abstract_methods


@pytest.mark.provider
@pytest.mark.unit
@pytest.mark.skip(reason="EmbeddingProvider factory not yet implemented - Wave 2 TODO")
def test_embedding_provider_factory_exists():
    """
    Test that EmbeddingProviderFactory exists.

    This factory should support creating providers for:
    - Bedrock (Titan, Cohere)
    - SageMaker endpoints
    - External APIs (OpenAI, etc.)
    """
    from src.services.embedding_provider import EmbeddingProviderFactory

    assert hasattr(EmbeddingProviderFactory, "create_provider")
    assert hasattr(EmbeddingProviderFactory, "get_available_providers")


# ============================================================================
# Provider Config Validation Tests
# ============================================================================

@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_config_validation():
    """Test VectorStoreConfig validation logic."""
    from src.services.vector_store_provider import (
        VectorStoreConfig,
        VectorStoreProvider,
        VectorStoreType,
    )

    # Create mock provider
    mock_provider = MagicMock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.S3_VECTOR

    # Valid config should pass
    valid_config = VectorStoreConfig(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        dimension=1536,
        similarity_metric="cosine"
    )

    # Use the base class validate_config method
    result = VectorStoreProvider.validate_config(mock_provider, valid_config)
    assert result is True


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_config_validation_invalid_dimension():
    """Test that config validation rejects invalid dimensions."""
    from src.services.vector_store_provider import (
        VectorStoreConfig,
        VectorStoreProvider,
        VectorStoreType,
    )

    mock_provider = MagicMock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.S3_VECTOR

    # Invalid dimension (zero or negative)
    invalid_config = VectorStoreConfig(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        dimension=0  # Invalid!
    )

    with pytest.raises(ValueError, match="Dimension must be positive"):
        VectorStoreProvider.validate_config(mock_provider, invalid_config)


@pytest.mark.provider
@pytest.mark.unit
def test_vector_store_config_validation_invalid_metric():
    """Test that config validation rejects invalid similarity metrics."""
    from src.services.vector_store_provider import (
        VectorStoreConfig,
        VectorStoreProvider,
        VectorStoreType,
    )

    mock_provider = MagicMock(spec=VectorStoreProvider)
    mock_provider.store_type = VectorStoreType.S3_VECTOR

    invalid_config = VectorStoreConfig(
        store_type=VectorStoreType.S3_VECTOR,
        name="test-store",
        dimension=1536,
        similarity_metric="invalid_metric"  # Invalid!
    )

    with pytest.raises(ValueError, match="Invalid similarity metric"):
        VectorStoreProvider.validate_config(mock_provider, invalid_config)
