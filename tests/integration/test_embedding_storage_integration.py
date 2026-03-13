"""
Tests for Embedding Storage Integration Service.

This module tests the integration between Bedrock embedding generation
and S3 Vector storage, including end-to-end text processing workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

from src.services.embedding_storage_integration import (
    EmbeddingStorageIntegration,
    TextEmbeddingMetadata,
    StoredEmbedding
)
from src.services.bedrock_embedding import EmbeddingResult
from src.exceptions import ValidationError, VectorEmbeddingError, VectorStorageError


class TestEmbeddingStorageIntegration:
    """Test cases for EmbeddingStorageIntegration service."""
    
    @pytest.fixture
    def mock_bedrock_service(self):
        """Mock Bedrock embedding service."""
        with patch('src.services.embedding_storage_integration.BedrockEmbeddingService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Mock embedding result
            mock_embedding_result = EmbeddingResult(
                embedding=[0.1, 0.2, 0.3] * 341 + [0.1],  # 1024 dimensions
                input_text="test text",
                model_id="amazon.titan-embed-text-v2:0",
                processing_time_ms=150
            )
            
            mock_instance.generate_text_embedding.return_value = mock_embedding_result
            mock_instance.batch_generate_embeddings.return_value = [mock_embedding_result]
            
            yield mock_instance
    
    @pytest.fixture
    def mock_storage_manager(self):
        """Mock S3 Vector storage manager."""
        with patch('src.services.embedding_storage_integration.S3VectorStorageManager') as mock_manager:
            mock_instance = Mock()
            mock_manager.return_value = mock_instance
            
            # Mock storage response
            mock_storage_response = {
                'ResponseMetadata': {'HTTPStatusCode': 200},
                'vectorsStored': 1
            }
            
            mock_instance.put_vectors_batch.return_value = mock_storage_response
            
            # Mock query response
            mock_query_response = {
                'vectors': [
                    {
                        'key': 'test-vector-1',
                        'distance': 0.05,
                        'metadata': {
                            'content_type': 'text',
                            'source_text': 'similar test text',
                            'model_id': 'amazon.titan-embed-text-v2:0'
                        },
                        'data': {'float32': [0.1, 0.2, 0.3] * 341 + [0.1]}
                    }
                ]
            }
            
            mock_instance.query_similar_vectors.return_value = mock_query_response
            
            # Mock list vectors response
            mock_list_response = {
                'vectors': [
                    {
                        'key': 'test-vector-1',
                        'data': {'float32': [0.1, 0.2, 0.3] * 341 + [0.1]},
                        'metadata': {
                            'content_type': 'text',
                            'source_text': 'test text'
                        }
                    }
                ]
            }
            
            mock_instance.list_vectors.return_value = mock_list_response
            
            yield mock_instance
    
    @pytest.fixture
    def integration_service(self, mock_bedrock_service, mock_storage_manager):
        """Create integration service with mocked dependencies."""
        with patch('src.services.embedding_storage_integration.config_manager') as mock_config:
            mock_config.aws_config.region = 'us-west-2'
            service = EmbeddingStorageIntegration()
            return service
    
    def test_store_text_embedding_success(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test successful text embedding storage."""
        text = "This is a test text for embedding"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        result = integration_service.store_text_embedding(
            text=text,
            index_arn=index_arn
        )
        
        # Verify the result
        assert isinstance(result, StoredEmbedding)
        assert result.vector_key.startswith("text-")
        assert len(result.embedding) == 1024
        assert result.metadata.content_type == "text"
        assert result.metadata.source_text == text
        assert result.metadata.text_length == len(text)
        assert result.metadata.model_id == "amazon.titan-embed-text-v2:0"
        assert result.index_arn == index_arn
        
        # Verify service calls
        mock_bedrock_service.generate_text_embedding.assert_called_once_with(text, None)
        mock_storage_manager.put_vectors_batch.assert_called_once()
        
        # Verify vector data structure (AWS S3 Vectors format)
        call_args = mock_storage_manager.put_vectors_batch.call_args
        vectors_data = call_args[1]['vectors_data']
        assert len(vectors_data) == 1
        assert vectors_data[0]['key'] == result.vector_key
        assert 'data' in vectors_data[0]
        assert 'float32' in vectors_data[0]['data']
        assert len(vectors_data[0]['data']['float32']) == 1024
        assert vectors_data[0]['metadata']['content_type'] == 'text'
    
    def test_store_text_embedding_with_custom_metadata(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test text embedding storage with custom metadata."""
        text = "Netflix original series episode"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/netflix-content/episodes"
        custom_metadata = {
            'content_id': 'netflix-123456',
            'series_id': 'stranger-things',
            'season': 4,
            'episode': 1,
            'genre': ['sci-fi', 'drama'],
            'actors': ['Millie Bobby Brown', 'Finn Wolfhard'],
            'director': 'The Duffer Brothers',
            'release_date': '2022-05-27'
        }
        vector_key = "netflix-episode-s4e1"
        
        result = integration_service.store_text_embedding(
            text=text,
            index_arn=index_arn,
            metadata=custom_metadata,
            vector_key=vector_key
        )
        
        # Verify custom metadata was included
        assert result.vector_key == vector_key
        assert result.metadata.content_id == 'netflix-123456'
        assert result.metadata.series_id == 'stranger-things'
        assert result.metadata.season == 4
        assert result.metadata.episode == 1
        assert result.metadata.genre == ['sci-fi', 'drama']
        assert result.metadata.actors == ['Millie Bobby Brown', 'Finn Wolfhard']
        assert result.metadata.director == 'The Duffer Brothers'
        assert result.metadata.release_date == '2022-05-27'
        
        # Verify the metadata was passed to storage
        call_args = mock_storage_manager.put_vectors_batch.call_args
        vectors_data = call_args[1]['vectors_data']
        stored_metadata = vectors_data[0]['metadata']
        assert stored_metadata['content_id'] == 'netflix-123456'
        assert stored_metadata['series_id'] == 'stranger-things'
        assert stored_metadata['season'] == 4
        
        # Verify AWS S3 Vectors format
        assert 'data' in vectors_data[0]
        assert 'float32' in vectors_data[0]['data']
        assert len(vectors_data[0]['data']['float32']) == 1024
    
    def test_batch_store_text_embeddings_success(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test successful batch text embedding storage."""
        texts = [
            "First test text for batch processing",
            "Second test text with different content",
            "Third text to complete the batch"
        ]
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/batch-index"
        
        # Mock batch embedding results
        mock_embedding_results = []
        for i, text in enumerate(texts):
            mock_result = EmbeddingResult(
                embedding=[0.1 + i * 0.1, 0.2 + i * 0.1, 0.3 + i * 0.1] * 341 + [0.1 + i * 0.1],
                input_text=text,
                model_id="amazon.titan-embed-text-v2:0",
                processing_time_ms=150 + i * 10
            )
            mock_embedding_results.append(mock_result)
        
        mock_bedrock_service.batch_generate_embeddings.return_value = mock_embedding_results
        
        results = integration_service.batch_store_text_embeddings(
            texts=texts,
            index_arn=index_arn
        )
        
        # Verify results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert isinstance(result, StoredEmbedding)
            assert result.vector_key.startswith("text-")
            assert len(result.embedding) == 1024
            assert result.metadata.source_text == texts[i]
            assert result.metadata.text_length == len(texts[i])
            assert result.index_arn == index_arn
        
        # Verify service calls
        mock_bedrock_service.batch_generate_embeddings.assert_called_once_with(
            texts=texts,
            model_id=None,
            batch_size=None
        )
        mock_storage_manager.put_vectors_batch.assert_called_once()
        
        # Verify batch storage data (AWS S3 Vectors format)
        call_args = mock_storage_manager.put_vectors_batch.call_args
        vectors_data = call_args[1]['vectors_data']
        assert len(vectors_data) == 3
        for i, vector_data in enumerate(vectors_data):
            assert vector_data['key'] == results[i].vector_key
            assert 'data' in vector_data
            assert 'float32' in vector_data['data']
            assert len(vector_data['data']['float32']) == 1024
            assert vector_data['metadata']['source_text'] == texts[i]
    
    def test_batch_store_with_metadata_list(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test batch storage with individual metadata for each text."""
        texts = ["Movie trailer", "TV episode"]
        metadata_list = [
            {
                'content_type': 'trailer',
                'genre': ['action', 'adventure'],
                'release_date': '2025-01-01'
            },
            {
                'content_type': 'episode',
                'series_id': 'test-series',
                'season': 1,
                'episode': 1
            }
        ]
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/media-content/mixed"
        
        # Mock batch embedding results
        mock_embedding_results = [
            EmbeddingResult(
                embedding=[0.1, 0.2, 0.3] * 341 + [0.1],
                input_text=texts[0],
                model_id="amazon.titan-embed-text-v2:0",
                processing_time_ms=150
            ),
            EmbeddingResult(
                embedding=[0.2, 0.3, 0.4] * 341 + [0.2],
                input_text=texts[1],
                model_id="amazon.titan-embed-text-v2:0",
                processing_time_ms=160
            )
        ]
        mock_bedrock_service.batch_generate_embeddings.return_value = mock_embedding_results
        
        results = integration_service.batch_store_text_embeddings(
            texts=texts,
            index_arn=index_arn,
            metadata_list=metadata_list
        )
        
        # Verify metadata was applied correctly
        assert len(results) == 2
        
        # Check first result (trailer)
        assert results[0].metadata.genre == ['action', 'adventure']
        assert results[0].metadata.release_date == '2025-01-01'
        
        # Check second result (episode)
        assert results[1].metadata.series_id == 'test-series'
        assert results[1].metadata.season == 1
        assert results[1].metadata.episode == 1
    
    def test_search_similar_text_success(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test successful similar text search."""
        query_text = "Find similar content"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/search-test/content"
        top_k = 5
        
        # Mock query embedding
        mock_query_embedding = EmbeddingResult(
            embedding=[0.5, 0.6, 0.7] * 341 + [0.5],
            input_text=query_text,
            model_id="amazon.titan-embed-text-v2:0",
            processing_time_ms=120
        )
        mock_bedrock_service.generate_text_embedding.return_value = mock_query_embedding
        
        result = integration_service.search_similar_text(
            query_text=query_text,
            index_arn=index_arn,
            top_k=top_k
        )
        
        # Verify search result structure
        assert result['query_text'] == query_text
        assert result['query_model_id'] == "amazon.titan-embed-text-v2:0"
        assert result['total_results'] == 1
        assert result['index_arn'] == index_arn
        assert result['top_k_requested'] == top_k
        assert 'search_time_ms' in result
        
        # Verify search results
        search_results = result['results']
        assert len(search_results) == 1
        assert search_results[0]['vector_key'] == 'test-vector-1'
        assert search_results[0]['similarity_score'] == 0.95
        assert search_results[0]['metadata']['content_type'] == 'text'
        
        # Verify service calls
        mock_bedrock_service.generate_text_embedding.assert_called_once_with(query_text, None)
        mock_storage_manager.query_similar_vectors.assert_called_once_with(
            index_arn=index_arn,
            query_vector=mock_query_embedding.embedding,
            top_k=top_k,
            metadata_filters=None
        )
    
    def test_search_with_metadata_filters(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test search with metadata filters."""
        query_text = "Action movie scenes"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/movies/scenes"
        metadata_filters = {
            'genre': ['action'],
            'content_type': 'scene'
        }
        
        mock_query_embedding = EmbeddingResult(
            embedding=[0.5, 0.6, 0.7] * 341 + [0.5],
            input_text=query_text,
            model_id="amazon.titan-embed-text-v2:0",
            processing_time_ms=120
        )
        mock_bedrock_service.generate_text_embedding.return_value = mock_query_embedding
        
        result = integration_service.search_similar_text(
            query_text=query_text,
            index_arn=index_arn,
            metadata_filters=metadata_filters
        )
        
        # Verify metadata filters were passed
        assert result['metadata_filters'] == metadata_filters
        mock_storage_manager.query_similar_vectors.assert_called_once_with(
            index_arn=index_arn,
            query_vector=mock_query_embedding.embedding,
            top_k=10,  # default value
            metadata_filters=metadata_filters
        )
    
    def test_get_embedding_by_key_success(self, integration_service, mock_storage_manager):
        """Test successful embedding retrieval by key."""
        vector_key = "test-vector-1"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        result = integration_service.get_embedding_by_key(
            vector_key=vector_key,
            index_arn=index_arn
        )
        
        # Verify result
        assert result is not None
        assert result['vector_key'] == vector_key
        assert len(result['embedding']) == 1024
        assert result['metadata']['content_type'] == 'text'
        assert result['index_arn'] == index_arn
        
        # Verify service call
        mock_storage_manager.list_vectors.assert_called_once_with(
            index_arn=index_arn,
            max_results=1000
        )
    
    def test_get_embedding_by_key_not_found(self, integration_service, mock_storage_manager):
        """Test embedding retrieval when key is not found."""
        vector_key = "non-existent-key"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Mock empty response
        mock_storage_manager.list_vectors.return_value = {'vectors': []}
        
        result = integration_service.get_embedding_by_key(
            vector_key=vector_key,
            index_arn=index_arn
        )
        
        # Verify result is None
        assert result is None
    
    def test_estimate_storage_cost(self, integration_service, mock_bedrock_service):
        """Test storage cost estimation."""
        texts = [
            "First text for cost estimation",
            "Second text with different length",
            "Third text to complete the cost analysis"
        ]
        
        # Mock embedding cost estimate
        mock_cost_estimate = {
            'total_cost_usd': 0.0003,
            'cost_per_text': 0.0001,
            'model_id': 'amazon.titan-embed-text-v2:0'
        }
        mock_bedrock_service.estimate_cost.return_value = mock_cost_estimate
        
        result = integration_service.estimate_storage_cost(texts)
        
        # Verify cost estimate structure
        assert 'embedding_generation' in result
        assert 'storage' in result
        assert 'query_costs' in result
        assert 'total_setup_cost_usd' in result
        assert 'ongoing_monthly_cost_usd' in result
        
        # Verify storage cost calculations
        storage_info = result['storage']
        assert storage_info['total_vectors'] == 3
        assert storage_info['vector_size_kb'] == 4
        assert storage_info['total_storage_kb'] == 12
        assert 'monthly_storage_cost_usd' in storage_info
        assert 'annual_storage_cost_usd' in storage_info
        
        # Verify query cost information
        query_info = result['query_costs']
        assert query_info['cost_per_1k_queries_usd'] == 0.01
        assert 'estimated_cost_per_query_usd' in query_info
        
        # Verify service call
        mock_bedrock_service.estimate_cost.assert_called_once_with(texts, None)
    
    def test_validation_errors(self, integration_service):
        """Test various validation error scenarios."""
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        
        # Test empty text
        with pytest.raises(ValidationError) as exc_info:
            integration_service.store_text_embedding("", index_arn)
        assert exc_info.value.error_code == "EMPTY_INPUT_TEXT"
        
        # Test empty index ARN
        with pytest.raises(ValidationError) as exc_info:
            integration_service.store_text_embedding("test text", "")
        assert exc_info.value.error_code == "EMPTY_INDEX_ARN"
        
        # Test empty texts list for batch processing
        with pytest.raises(ValidationError) as exc_info:
            integration_service.batch_store_text_embeddings([], index_arn)
        assert exc_info.value.error_code == "EMPTY_INPUT_LIST"
        
        # Test metadata list length mismatch
        with pytest.raises(ValidationError) as exc_info:
            integration_service.batch_store_text_embeddings(
                ["text1", "text2"],
                index_arn,
                metadata_list=[{"key": "value"}]  # Only one metadata for two texts
            )
        assert exc_info.value.error_code == "METADATA_LENGTH_MISMATCH"
        
        # Test invalid top_k for search
        with pytest.raises(ValidationError) as exc_info:
            integration_service.search_similar_text("query", index_arn, top_k=0)
        assert exc_info.value.error_code == "INVALID_TOP_K"
        
        with pytest.raises(ValidationError) as exc_info:
            integration_service.search_similar_text("query", index_arn, top_k=101)
        assert exc_info.value.error_code == "INVALID_TOP_K"
    
    def test_error_propagation(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test that errors from underlying services are properly propagated."""
        text = "Test text for error propagation"
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/error-test"
        
        # Test Bedrock service error
        mock_bedrock_service.generate_text_embedding.side_effect = VectorEmbeddingError(
            "Bedrock model access denied",
            error_code="MODEL_ACCESS_DENIED"
        )
        
        with pytest.raises(VectorEmbeddingError) as exc_info:
            integration_service.store_text_embedding(text, index_arn)
        assert exc_info.value.error_code == "MODEL_ACCESS_DENIED"
        
        # Reset mock and test storage error
        mock_bedrock_service.generate_text_embedding.side_effect = None
        mock_bedrock_service.generate_text_embedding.return_value = EmbeddingResult(
            embedding=[0.1, 0.2, 0.3] * 341 + [0.1],
            input_text=text,
            model_id="amazon.titan-embed-text-v2:0",
            processing_time_ms=150
        )
        
        mock_storage_manager.put_vectors_batch.side_effect = VectorStorageError(
            "S3 Vectors storage failed",
            error_code="STORAGE_FAILED"
        )
        
        with pytest.raises(VectorStorageError) as exc_info:
            integration_service.store_text_embedding(text, index_arn)
        assert exc_info.value.error_code == "STORAGE_FAILED"
    
    def test_media_company_workflow(self, integration_service, mock_bedrock_service, mock_storage_manager):
        """Test a complete media company workflow scenario."""
        # Simulate Netflix processing episode descriptions
        episode_data = [
            {
                'text': 'Stranger Things S4E1: Eleven struggles with her powers while the gang faces new supernatural threats in Hawkins.',
                'metadata': {
                    'content_id': 'st-s4e1',
                    'series_id': 'stranger-things',
                    'season': 4,
                    'episode': 1,
                    'genre': ['sci-fi', 'horror', 'drama'],
                    'actors': ['Millie Bobby Brown', 'Finn Wolfhard', 'David Harbour'],
                    'release_date': '2022-05-27'
                }
            },
            {
                'text': 'The Crown S5E3: Princess Diana navigates royal protocol while facing media scrutiny and personal challenges.',
                'metadata': {
                    'content_id': 'crown-s5e3',
                    'series_id': 'the-crown',
                    'season': 5,
                    'episode': 3,
                    'genre': ['drama', 'biography', 'history'],
                    'actors': ['Elizabeth Debicki', 'Dominic West', 'Imelda Staunton'],
                    'release_date': '2022-11-09'
                }
            }
        ]
        
        index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/netflix-content/episodes"
        
        # Mock batch embedding results
        mock_embedding_results = []
        for i, episode in enumerate(episode_data):
            mock_result = EmbeddingResult(
                embedding=[0.1 + i * 0.1, 0.2 + i * 0.1, 0.3 + i * 0.1] * 341 + [0.1 + i * 0.1],
                input_text=episode['text'],
                model_id="amazon.titan-embed-text-v2:0",
                processing_time_ms=150 + i * 10
            )
            mock_embedding_results.append(mock_result)
        
        mock_bedrock_service.batch_generate_embeddings.return_value = mock_embedding_results
        
        # Store episode embeddings
        texts = [episode['text'] for episode in episode_data]
        metadata_list = [episode['metadata'] for episode in episode_data]
        
        results = integration_service.batch_store_text_embeddings(
            texts=texts,
            index_arn=index_arn,
            metadata_list=metadata_list
        )
        
        # Verify results
        assert len(results) == 2
        
        # Verify Stranger Things episode
        st_result = results[0]
        assert st_result.metadata.content_id == 'st-s4e1'
        assert st_result.metadata.series_id == 'stranger-things'
        assert st_result.metadata.season == 4
        assert st_result.metadata.episode == 1
        assert 'sci-fi' in st_result.metadata.genre
        assert 'Millie Bobby Brown' in st_result.metadata.actors
        
        # Verify The Crown episode
        crown_result = results[1]
        assert crown_result.metadata.content_id == 'crown-s5e3'
        assert crown_result.metadata.series_id == 'the-crown'
        assert crown_result.metadata.season == 5
        assert crown_result.metadata.episode == 3
        assert 'drama' in crown_result.metadata.genre
        assert 'Elizabeth Debicki' in crown_result.metadata.actors
        
        # Test search for similar content
        query_text = "Royal family drama with historical elements"
        
        # Mock search results favoring The Crown
        mock_search_response = {
            'vectors': [
                {
                    'key': crown_result.vector_key,
                    'distance': 0.08,
                    'metadata': crown_result.metadata.to_dict(),
                    'data': {'float32': crown_result.embedding}
                },
                {
                    'key': st_result.vector_key,
                    'distance': 0.35,
                    'metadata': st_result.metadata.to_dict(),
                    'data': {'float32': st_result.embedding}
                }
            ]
        }
        mock_storage_manager.query_similar_vectors.return_value = mock_search_response
        
        search_result = integration_service.search_similar_text(
            query_text=query_text,
            index_arn=index_arn,
            top_k=5
        )
        
        # Verify search results prioritize The Crown (higher similarity)
        assert len(search_result['results']) == 2
        assert search_result['results'][0]['similarity_score'] == 0.92
        assert search_result['results'][0]['metadata']['series_id'] == 'the-crown'
        assert search_result['results'][1]['similarity_score'] == 0.65
        assert search_result['results'][1]['metadata']['series_id'] == 'stranger-things'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])