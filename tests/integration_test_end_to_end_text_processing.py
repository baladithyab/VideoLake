"""
End-to-End Integration Test for Text Processing Pipeline.

This test demonstrates the complete workflow from text input to embedding storage
and similarity search, validating the integration between all components.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import json
from datetime import datetime

from src.services.embedding_storage_integration import EmbeddingStorageIntegration
from src.services.bedrock_embedding import BedrockEmbeddingService, EmbeddingResult
from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorEmbeddingError, VectorStorageError


class TestEndToEndTextProcessing:
    """End-to-end integration tests for the complete text processing pipeline."""
    
    @pytest.fixture
    def mock_aws_clients(self):
        """Mock all AWS clients for end-to-end testing."""
        with patch('src.services.bedrock_embedding.aws_client_factory') as mock_bedrock_factory, \
             patch('src.services.s3_vector_storage.aws_client_factory') as mock_s3_factory, \
             patch('src.services.embedding_storage_integration.config_manager') as mock_config:
            
            # Configure mock config
            mock_config.aws_config.region = 'us-west-2'
            mock_config.aws_config.bedrock_models = {
                'text_embedding': 'amazon.titan-embed-text-v2:0'
            }
            
            # Mock Bedrock Runtime client
            mock_bedrock_client = Mock()
            mock_bedrock_factory.get_bedrock_runtime_client.return_value = mock_bedrock_client
            
            # Mock S3 Vectors client
            mock_s3vectors_client = Mock()
            mock_s3_factory.get_s3vectors_client.return_value = mock_s3vectors_client
            mock_s3_factory.get_s3_client.return_value = Mock()
            
            yield {
                'bedrock_client': mock_bedrock_client,
                's3vectors_client': mock_s3vectors_client,
                'config': mock_config
            }
    
    def test_complete_text_processing_workflow(self, mock_aws_clients):
        """Test the complete workflow: setup → embed → store → search."""
        
        # Setup test data
        bucket_name = "media-company-embeddings"
        index_name = "content-descriptions"
        index_arn = f"arn:aws:s3vectors:us-west-2:123456789012:index/{bucket_name}/{index_name}"
        
        # Sample media content descriptions
        content_data = [
            {
                'text': 'Epic space battle with stunning visual effects and heroic characters fighting against an evil empire.',
                'metadata': {
                    'content_id': 'movie-001',
                    'genre': ['sci-fi', 'action'],
                    'category': 'movie',
                    'release_date': '2023-05-15'
                }
            },
            {
                'text': 'Romantic comedy set in New York City featuring two unlikely characters who fall in love.',
                'metadata': {
                    'content_id': 'movie-002',
                    'genre': ['romance', 'comedy'],
                    'category': 'movie',
                    'release_date': '2023-08-20'
                }
            },
            {
                'text': 'Intense thriller about a detective investigating mysterious disappearances in a small town.',
                'metadata': {
                    'content_id': 'series-001-s1e1',
                    'series_id': 'mystery-detective',
                    'season': 1,
                    'episode': 1,
                    'genre': ['thriller', 'mystery'],
                    'category': 'episode'
                }
            }
        ]
        
        # Mock AWS service responses
        self._setup_aws_mocks(mock_aws_clients, content_data, index_arn)
        
        # Initialize services
        integration_service = EmbeddingStorageIntegration()
        storage_manager = S3VectorStorageManager()
        
        # Step 1: Create vector bucket and index
        bucket_result = storage_manager.create_vector_bucket(bucket_name)
        assert bucket_result['status'] in ['created', 'already_exists']
        
        index_result = storage_manager.create_vector_index(
            bucket_name=bucket_name,
            index_name=index_name,
            dimensions=1024,
            distance_metric="cosine"
        )
        assert index_result['status'] in ['created', 'already_exists']
        
        # Step 2: Process and store embeddings
        texts = [item['text'] for item in content_data]
        metadata_list = [item['metadata'] for item in content_data]
        
        stored_embeddings = integration_service.batch_store_text_embeddings(
            texts=texts,
            index_arn=index_arn,
            metadata_list=metadata_list
        )
        
        # Verify embeddings were stored
        assert len(stored_embeddings) == 3
        for i, stored_embedding in enumerate(stored_embeddings):
            assert stored_embedding.metadata.source_text == texts[i]
            assert stored_embedding.metadata.content_id == content_data[i]['metadata']['content_id']
            assert len(stored_embedding.embedding) == 1024
        
        # Step 3: Test similarity search
        search_queries = [
            {
                'query': 'Space adventure with heroes and villains',
                'expected_match': 'movie-001',  # Should match sci-fi movie
                'filters': {'category': 'movie'}
            },
            {
                'query': 'Love story in urban setting',
                'expected_match': 'movie-002',  # Should match romantic comedy
                'filters': {'genre': ['romance']}
            },
            {
                'query': 'Crime investigation mystery',
                'expected_match': 'series-001-s1e1',  # Should match thriller series
                'filters': {'category': 'episode'}
            }
        ]
        
        for search_query in search_queries:
            search_result = integration_service.search_similar_text(
                query_text=search_query['query'],
                index_arn=index_arn,
                top_k=3,
                metadata_filters=search_query['filters']
            )
            
            # Verify search results
            assert search_result['total_results'] > 0
            assert search_result['query_text'] == search_query['query']
            
            # Check that the expected content appears in results
            found_expected = False
            for result in search_result['results']:
                if result['metadata'].get('content_id') == search_query['expected_match']:
                    found_expected = True
                    assert result['similarity_score'] > 0.3  # Should have reasonable similarity
                    break
            
            assert found_expected, f"Expected match {search_query['expected_match']} not found in results"
        
        # Step 4: Test individual embedding retrieval
        first_embedding_key = stored_embeddings[0].vector_key
        retrieved_embedding = integration_service.get_embedding_by_key(
            vector_key=first_embedding_key,
            index_arn=index_arn
        )
        
        assert retrieved_embedding is not None
        assert retrieved_embedding['vector_key'] == first_embedding_key
        assert len(retrieved_embedding['embedding']) == 1024
        assert retrieved_embedding['metadata']['content_id'] == content_data[0]['metadata']['content_id']
        
        # Step 5: Test cost estimation
        cost_estimate = integration_service.estimate_storage_cost(texts)
        
        assert 'embedding_generation' in cost_estimate
        assert 'storage' in cost_estimate
        assert 'total_setup_cost_usd' in cost_estimate
        assert cost_estimate['storage']['total_vectors'] == len(texts)
        
        print("✅ End-to-end text processing workflow completed successfully!")
        print(f"   - Processed {len(texts)} text embeddings")
        print(f"   - Performed {len(search_queries)} similarity searches")
        print(f"   - Retrieved individual embedding by key")
        print(f"   - Estimated total setup cost: ${cost_estimate['total_setup_cost_usd']:.6f}")
    
    def _setup_aws_mocks(self, mock_aws_clients, content_data, index_arn):
        """Setup comprehensive AWS service mocks for end-to-end testing."""
        bedrock_client = mock_aws_clients['bedrock_client']
        s3vectors_client = mock_aws_clients['s3vectors_client']
        
        # Mock Bedrock embedding responses
        def mock_bedrock_invoke(modelId, body, **kwargs):
            request_body = json.loads(body)
            input_text = request_body.get('inputText', '')
            
            # Generate deterministic embeddings based on text content
            embedding = self._generate_mock_embedding(input_text)
            
            if modelId == 'amazon.titan-embed-text-v2:0':
                response_body = {
                    'embeddingsByType': {
                        'float': embedding
                    }
                }
            else:
                response_body = {
                    'embedding': embedding
                }
            
            mock_response = Mock()
            mock_response.read.return_value = json.dumps(response_body).encode()
            
            return {'body': mock_response}
        
        bedrock_client.invoke_model.side_effect = mock_bedrock_invoke
        
        # Mock S3 Vectors bucket operations
        s3vectors_client.create_vector_bucket.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200}
        }
        
        s3vectors_client.create_index.return_value = {
            'ResponseMetadata': {'HTTPStatusCode': 200},
            'indexArn': index_arn
        }
        
        # Mock vector storage
        def mock_put_vectors(**kwargs):
            vectors = kwargs.get('vectors', [])
            # Store vectors for later retrieval by list_vectors
            mock_list_vectors.stored_vectors = []
            for vector in vectors:
                stored_vector = {
                    'key': vector['key'],
                    'embedding': vector['data']['float32'],
                    'metadata': vector.get('metadata', {})
                }
                mock_list_vectors.stored_vectors.append(stored_vector)
            
            return {
                'ResponseMetadata': {'HTTPStatusCode': 200},
                'vectorsStored': len(vectors)
            }
        
        s3vectors_client.put_vectors.side_effect = mock_put_vectors
        
        # Mock similarity search
        def mock_query_vectors(**kwargs):
            IndexArn = kwargs.get('indexArn')
            QueryVector = kwargs.get('queryVector')
            TopK = kwargs.get('topK')
            # Generate mock search results based on query vector
            results = []
            
            for i, content in enumerate(content_data):
                # Calculate mock similarity score based on content matching
                similarity_score = self._calculate_mock_similarity(QueryVector, content['text'])
                
                result = {
                    'key': f"content-{content['metadata']['content_id']}",
                    'score': similarity_score,
                    'metadata': {
                        **content['metadata'],
                        'content_type': 'text',
                        'source_text': content['text'][:100] + '...',
                        'model_id': 'amazon.titan-embed-text-v2:0'
                    },
                    'embedding': self._generate_mock_embedding(content['text'])
                }
                results.append(result)
            
            # Sort by similarity score (descending)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Apply metadata filters if provided
            metadata_filter = kwargs.get('filter', {})
            if metadata_filter:
                filtered_results = []
                for result in results:
                    match = True
                    for filter_key, filter_value in metadata_filter.items():
                        result_value = result['metadata'].get(filter_key)
                        if isinstance(filter_value, list):
                            if not any(v in result_value for v in filter_value if isinstance(result_value, list)):
                                if result_value not in filter_value:
                                    match = False
                                    break
                        else:
                            if result_value != filter_value:
                                match = False
                                break
                    if match:
                        filtered_results.append(result)
                results = filtered_results
            
            return {
                'vectors': results[:TopK]
            }
        
        s3vectors_client.query_vectors.side_effect = mock_query_vectors
        
        # Mock list vectors for key retrieval
        def mock_list_vectors(**kwargs):
            IndexArn = kwargs.get('indexArn')
            vectors = []
            # Use the same keys that would be generated by the integration service
            # Since we can't predict UUIDs, we'll store them during put_vectors
            if hasattr(mock_list_vectors, 'stored_vectors'):
                return {'vectors': mock_list_vectors.stored_vectors}
            else:
                return {'vectors': []}
        
        s3vectors_client.list_vectors.side_effect = mock_list_vectors
    
    def _generate_mock_embedding(self, text):
        """Generate a deterministic mock embedding based on text content."""
        # Create a simple hash-based embedding for consistent testing
        import hashlib
        
        # Generate hash from text
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to embedding values
        embedding = []
        for i in range(1024):
            # Use different parts of the hash to generate float values
            hash_part = text_hash[(i * 2) % len(text_hash):(i * 2 + 2) % len(text_hash)]
            if len(hash_part) < 2:
                hash_part = text_hash[:2]
            
            # Convert hex to float between -1 and 1
            hex_value = int(hash_part, 16)
            float_value = (hex_value / 255.0) * 2 - 1
            embedding.append(float_value)
        
        return embedding
    
    def _calculate_mock_similarity(self, query_vector, content_text):
        """Calculate mock similarity score based on content matching."""
        # Generate embedding for content text
        content_embedding = self._generate_mock_embedding(content_text)
        
        # Calculate cosine similarity (simplified)
        dot_product = sum(a * b for a, b in zip(query_vector[:100], content_embedding[:100]))  # Use first 100 dims
        magnitude_a = sum(a * a for a in query_vector[:100]) ** 0.5
        magnitude_b = sum(b * b for b in content_embedding[:100]) ** 0.5
        
        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0
        
        similarity = dot_product / (magnitude_a * magnitude_b)
        
        # Normalize to 0-1 range and add some randomness for realistic results
        import random
        random.seed(hash(content_text))  # Deterministic randomness
        similarity = (similarity + 1) / 2  # Convert from [-1,1] to [0,1]
        similarity = max(0.3, min(0.95, similarity + random.uniform(-0.1, 0.1)))  # Add noise
        
        return round(similarity, 3)
    
    def test_error_handling_in_workflow(self, mock_aws_clients):
        """Test error handling throughout the end-to-end workflow."""
        
        # Test Bedrock service error
        bedrock_client = mock_aws_clients['bedrock_client']
        bedrock_client.invoke_model.side_effect = Exception("Bedrock service unavailable")
        
        integration_service = EmbeddingStorageIntegration()
        
        with pytest.raises(VectorEmbeddingError):
            integration_service.store_text_embedding(
                text="Test text for error handling",
                index_arn="arn:aws:s3vectors:us-west-2:123456789012:index/test/error"
            )
        
        # Test S3 Vectors service error
        bedrock_client.invoke_model.side_effect = None
        bedrock_client.invoke_model.return_value = {
            'body': Mock(read=lambda: json.dumps({
                'embeddingsByType': {'float': [0.1] * 1024}
            }).encode())
        }
        
        s3vectors_client = mock_aws_clients['s3vectors_client']
        s3vectors_client.put_vectors.side_effect = Exception("S3 Vectors service unavailable")
        
        with pytest.raises(VectorEmbeddingError):
            integration_service.store_text_embedding(
                text="Test text for storage error",
                index_arn="arn:aws:s3vectors:us-west-2:123456789012:index/test/error"
            )
    
    def test_performance_metrics_collection(self, mock_aws_clients):
        """Test that performance metrics are properly collected during processing."""
        
        # Setup mocks for performance testing
        self._setup_aws_mocks(mock_aws_clients, [
            {
                'text': 'Performance test content for metrics collection',
                'metadata': {'content_id': 'perf-test-001', 'category': 'test'}
            }
        ], "arn:aws:s3vectors:us-west-2:123456789012:index/perf-test/metrics")
        
        integration_service = EmbeddingStorageIntegration()
        
        # Test single embedding with timing
        import time
        start_time = time.time()
        
        result = integration_service.store_text_embedding(
            text="Performance test content for metrics collection",
            index_arn="arn:aws:s3vectors:us-west-2:123456789012:index/perf-test/metrics"
        )
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        # Verify timing information is captured
        assert result.metadata.processing_time_ms is not None
        assert processing_time > 0
        
        # Test search performance
        start_time = time.time()
        
        search_result = integration_service.search_similar_text(
            query_text="Find performance test content",
            index_arn="arn:aws:s3vectors:us-west-2:123456789012:index/perf-test/metrics",
            top_k=5
        )
        
        end_time = time.time()
        search_time = (end_time - start_time) * 1000
        
        # Verify search timing is captured
        assert 'search_time_ms' in search_result
        assert search_result['search_time_ms'] > 0
        assert search_time > 0
        
        print(f"✅ Performance metrics collected:")
        print(f"   - Embedding storage: {processing_time:.2f}ms")
        print(f"   - Similarity search: {search_time:.2f}ms")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])