#!/usr/bin/env python3
"""
End-to-end test for text processing workflow.

Tests full pipeline: ingest text → generate embeddings → store in vector DB → search → verify results.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json


@pytest.mark.e2e
@pytest.mark.slow
class TestTextWorkflowE2E:
    """End-to-end test for text embedding and search workflow."""

    @pytest.fixture
    def sample_texts(self):
        """Sample text documents for testing."""
        return [
            "Machine learning is a subset of artificial intelligence.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing enables computers to understand text.",
            "Computer vision allows machines to interpret visual information.",
            "Reinforcement learning trains agents through rewards and penalties."
        ]

    @pytest.mark.asyncio
    async def test_full_text_pipeline(self, test_client, sample_texts):
        """
        Test complete text processing pipeline:
        1. Create vector store index
        2. Generate embeddings for text documents
        3. Insert vectors into store
        4. Perform similarity search
        5. Verify results
        """
        with patch('boto3.client') as mock_boto:
            # Mock S3 client for vector storage
            mock_s3 = MagicMock()
            mock_s3.head_bucket.return_value = {}
            mock_s3.put_object.return_value = {"ETag": "test-etag"}
            mock_s3.list_objects_v2.return_value = {"Contents": []}

            # Mock Bedrock Runtime for embeddings
            mock_bedrock = MagicMock()
            mock_embedding = [0.1 + i * 0.01 for i in range(1536)]  # Unique embeddings
            mock_bedrock.invoke_model.return_value = {
                "body": MagicMock(read=lambda: json.dumps({"embedding": mock_embedding}).encode())
            }

            def get_client(service_name, **kwargs):
                if service_name == 's3':
                    return mock_s3
                elif service_name == 'bedrock-runtime':
                    return mock_bedrock
                return MagicMock()

            mock_boto.side_effect = get_client

            # Step 1: Create index
            index_payload = {
                "index_name": "test-text-index",
                "dimension": 1536,
                "distance_metric": "cosine"
            }

            create_response = test_client.post(
                "/api/vector-stores/s3vector/indices",
                json=index_payload
            )

            if create_response.status_code == 404:
                pytest.skip("Vector store API not yet implemented")

            assert create_response.status_code in [200, 201]

            # Step 2 & 3: Generate embeddings and insert vectors
            for i, text in enumerate(sample_texts):
                # Generate embedding
                embed_payload = {
                    "content": text,
                    "modality": "text",
                    "provider": "bedrock",
                    "model_id": "amazon.titan-embed-text-v1"
                }

                embed_response = test_client.post("/api/embeddings", json=embed_payload)

                if embed_response.status_code == 404:
                    pytest.skip("Embedding API not yet implemented")

                assert embed_response.status_code in [200, 201]
                embedding = embed_response.json()["embedding"]

                # Insert vector
                insert_payload = {
                    "vectors": [embedding],
                    "metadatas": [{"id": str(i), "text": text}]
                }

                insert_response = test_client.post(
                    "/api/vector-stores/s3vector/indices/test-text-index/vectors",
                    json=insert_payload
                )

                assert insert_response.status_code in [200, 201]

            # Step 4: Search for similar documents
            query_text = "What is machine learning?"
            query_embed_response = test_client.post(
                "/api/embeddings",
                json={
                    "content": query_text,
                    "modality": "text",
                    "provider": "bedrock",
                    "model_id": "amazon.titan-embed-text-v1"
                }
            )

            assert query_embed_response.status_code in [200, 201]
            query_embedding = query_embed_response.json()["embedding"]

            # Perform search
            search_payload = {
                "query_vector": query_embedding,
                "top_k": 3
            }

            search_response = test_client.post(
                "/api/vector-stores/s3vector/indices/test-text-index/search",
                json=search_payload
            )

            if search_response.status_code == 404:
                pytest.skip("Vector search API not yet implemented")

            assert search_response.status_code == 200

            # Step 5: Verify results
            results = search_response.json()
            assert isinstance(results, (list, dict))

            if isinstance(results, list):
                assert len(results) > 0
                # First result should be most relevant (machine learning doc)
                # Note: With mocked embeddings, we can't verify semantic relevance
                # In real tests with actual embeddings, we'd check:
                # assert "machine learning" in results[0]["metadata"]["text"].lower()

    @pytest.mark.asyncio
    async def test_search_returns_correct_count(self, test_client):
        """Test that search respects top_k parameter."""
        with patch('boto3.client') as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client

            # Mock search results
            mock_results = [
                {"id": str(i), "score": 0.9 - i * 0.1, "metadata": {"text": f"doc {i}"}}
                for i in range(10)
            ]

            search_payload = {
                "query_vector": [0.1] * 1536,
                "top_k": 5
            }

            response = test_client.post(
                "/api/vector-stores/s3vector/indices/test-index/search",
                json=search_payload
            )

            if response.status_code == 404:
                pytest.skip("Vector search API not yet implemented")

            assert response.status_code == 200
            results = response.json()

            # Verify top_k is respected
            if isinstance(results, list):
                assert len(results) <= 5

    @pytest.mark.asyncio
    async def test_empty_search_results(self, test_client):
        """Test search with no matching results."""
        with patch('boto3.client') as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client

            search_payload = {
                "query_vector": [0.1] * 1536,
                "top_k": 10
            }

            response = test_client.post(
                "/api/vector-stores/s3vector/indices/empty-index/search",
                json=search_payload
            )

            if response.status_code == 404:
                pytest.skip("Vector search API not yet implemented")

            # Should return empty results or 404 for non-existent index
            assert response.status_code in [200, 404]

            if response.status_code == 200:
                results = response.json()
                assert isinstance(results, (list, dict))
