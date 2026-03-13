"""
Tests for the Similarity Search Engine Service

This test suite validates the unified similarity search capabilities
including multimodal search within the same embedding space.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from src.services.similarity_search_engine import (
    SimilaritySearchEngine,
    SimilarityQuery,
    SimilarityResult,
    SimilaritySearchResponse,
    TemporalFilter,
    QueryInputType,
    IndexType
)
from src.exceptions import ValidationError


# Fixtures at module level
@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    bedrock_service = Mock()
    twelvelabs_service = Mock()
    s3_vector_manager = Mock()
    text_storage = Mock()
    video_storage = Mock()
    
    return {
        'bedrock_service': bedrock_service,
        'twelvelabs_service': twelvelabs_service,
        's3_vector_manager': s3_vector_manager,
        'text_storage': text_storage,
        'video_storage': video_storage
    }

@pytest.fixture
def similarity_engine(mock_services):
    """Create SimilaritySearchEngine with mocked services."""
    return SimilaritySearchEngine(**mock_services)

@pytest.fixture
def sample_s3_search_results():
    """Sample S3 Vector search results."""
    return {
        'vectors': [
            {
                'key': 'video-test-segment-0001',
                'distance': 0.1,
                'metadata': {
                    'content_type': 'video',
                    'start_sec': 0.0,
                    'end_sec': 5.0,
                    'embedding_option': 'visual-text',
                    'model_id': 'twelvelabs.marengo-embed-2-7-v1:0',
                    'title': 'Sample video segment'
                }
            },
            {
                'key': 'text-document-0001',
                'distance': 0.2,
                'metadata': {
                    'content_type': 'text',
                    'title': 'Sample document',
                    'category': 'educational'
                }
            }
        ]
    }

class TestSimilaritySearchEngine:
    """Test the main SimilaritySearchEngine functionality."""

    def test_engine_initialization(self, similarity_engine):
        """Test proper engine initialization."""
        assert similarity_engine is not None
        assert similarity_engine.search_stats['total_searches'] == 0
        assert similarity_engine.search_stats['total_cost'] == 0.0
        assert similarity_engine.search_stats['average_latency_ms'] == 0.0

    def test_get_engine_capabilities(self, similarity_engine):
        """Test engine capabilities reporting."""
        capabilities = similarity_engine.get_engine_capabilities()
        
        assert 'supported_index_types' in capabilities
        assert 'supported_input_types' in capabilities
        assert 'index_compatibility' in capabilities
        assert 'features' in capabilities
        assert 'models_supported' in capabilities
        
        # Check Marengo multimodal support
        marengo_inputs = capabilities['index_compatibility']['marengo_multimodal']
        assert 'text' in marengo_inputs
        assert 'video_file' in marengo_inputs
        assert 'audio_file' in marengo_inputs
        assert 'image_file' in marengo_inputs
        
        # Check Titan text support
        titan_inputs = capabilities['index_compatibility']['titan_text']
        assert 'text' in titan_inputs
        assert 'embedding' in titan_inputs
        assert len(titan_inputs) == 2  # Only text and embedding


class TestSimilarityQuery:
    """Test SimilarityQuery functionality."""

    def test_text_query_input_type(self):
        """Test text query input type detection."""
        query = SimilarityQuery(query_text="find similar videos about cats")
        assert query.get_input_type() == QueryInputType.TEXT

    def test_video_file_query_input_type(self):
        """Test video file query input type detection."""
        query = SimilarityQuery(query_video_s3_uri="s3://bucket/video.mp4")
        assert query.get_input_type() == QueryInputType.VIDEO_FILE

    def test_audio_file_query_input_type(self):
        """Test audio file query input type detection."""
        query = SimilarityQuery(query_audio_s3_uri="s3://bucket/audio.wav")
        assert query.get_input_type() == QueryInputType.AUDIO_FILE

    def test_image_file_query_input_type(self):
        """Test image file query input type detection."""
        query = SimilarityQuery(query_image_s3_uri="s3://bucket/image.jpg")
        assert query.get_input_type() == QueryInputType.IMAGE_FILE

    def test_embedding_query_input_type(self):
        """Test embedding query input type detection."""
        query = SimilarityQuery(query_embedding=[0.1, 0.2, 0.3])
        assert query.get_input_type() == QueryInputType.EMBEDDING

    def test_no_query_input_error(self):
        """Test error when no query input provided."""
        query = SimilarityQuery()
        with pytest.raises(ValidationError, match="No query input provided"):
            query.get_input_type()


class TestTemporalFilter:
    """Test temporal filtering functionality."""

    def test_temporal_filter_to_s3_metadata(self):
        """Test conversion of temporal filter to S3 Vector metadata format."""
        temporal_filter = TemporalFilter(
            start_time=10.0,
            end_time=30.0
        )
        
        metadata_filter = temporal_filter.to_s3_metadata_filter()
        
        assert metadata_filter['start_sec'] == {'$gte': 10.0}
        assert metadata_filter['end_sec'] == {'$lte': 30.0}

    def test_temporal_filter_duration_warning(self, caplog):
        """Test warning for duration filtering."""
        temporal_filter = TemporalFilter(duration_min=5.0)
        temporal_filter.to_s3_metadata_filter()
        
        assert "Duration filtering requires post-processing" in caplog.text


class TestQueryValidation:
    """Test query validation logic."""

    def test_validate_titan_text_compatibility(self, similarity_engine):
        """Test Titan text index only accepts text queries."""
        text_query = SimilarityQuery(query_text="test")
        
        # Should not raise error
        similarity_engine._validate_query_index_compatibility(
            text_query, IndexType.TITAN_TEXT, QueryInputType.TEXT
        )
        
        # Video query should raise error
        video_query = SimilarityQuery(query_video_s3_uri="s3://bucket/video.mp4")
        with pytest.raises(ValidationError, match="Titan text indexes only support text queries"):
            similarity_engine._validate_query_index_compatibility(
                video_query, IndexType.TITAN_TEXT, QueryInputType.VIDEO_FILE
            )

    def test_validate_marengo_multimodal_compatibility(self, similarity_engine):
        """Test Marengo index accepts all input types."""
        # Test various input types
        queries = [
            (SimilarityQuery(query_text="test"), QueryInputType.TEXT),
            (SimilarityQuery(query_video_s3_uri="s3://bucket/video.mp4"), QueryInputType.VIDEO_FILE),
            (SimilarityQuery(query_audio_s3_uri="s3://bucket/audio.wav"), QueryInputType.AUDIO_FILE),
            (SimilarityQuery(query_image_s3_uri="s3://bucket/image.jpg"), QueryInputType.IMAGE_FILE),
            (SimilarityQuery(query_embedding=[0.1, 0.2]), QueryInputType.EMBEDDING)
        ]
        
        for query, input_type in queries:
            # Should not raise error for any input type
            similarity_engine._validate_query_index_compatibility(
                query, IndexType.MARENGO_MULTIMODAL, input_type
            )

    def test_validate_query_parameters(self, similarity_engine):
        """Test query parameter validation."""
        # Invalid top_k
        invalid_query = SimilarityQuery(query_text="test", top_k=0)
        with pytest.raises(ValidationError, match="top_k must be between 1 and 1000"):
            similarity_engine._validate_query_index_compatibility(
                invalid_query, IndexType.MARENGO_MULTIMODAL, QueryInputType.TEXT
            )
        
        # Invalid similarity threshold
        invalid_query = SimilarityQuery(query_text="test", similarity_threshold=-0.1)
        with pytest.raises(ValidationError, match="similarity_threshold must be between 0.0 and 1.0"):
            similarity_engine._validate_query_index_compatibility(
                invalid_query, IndexType.MARENGO_MULTIMODAL, QueryInputType.TEXT
            )


class TestEmbeddingGeneration:
    """Test embedding generation logic."""

    def test_generate_text_embedding_titan(self, similarity_engine, mock_services):
        """Test text embedding generation for Titan index."""
        # Setup mock
        mock_result = Mock()
        mock_result.embedding = [0.1, 0.2, 0.3] * 341  # 1023 dimensions
        mock_services['bedrock_service'].generate_text_embedding.return_value = mock_result
        
        query = SimilarityQuery(query_text="test query")
        
        embedding, cost = similarity_engine._generate_query_embedding(
            query, IndexType.TITAN_TEXT, "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        )
        
        assert len(embedding) == 1023
        assert cost > 0.0
        mock_services['bedrock_service'].generate_text_embedding.assert_called_once()

    def test_generate_text_embedding_marengo(self, similarity_engine, mock_services):
        """Test text embedding generation for Marengo index."""
        # Setup mock
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341  # 1023 dimensions
        }
        
        query = SimilarityQuery(query_text="test query")
        
        embedding, cost = similarity_engine._generate_query_embedding(
            query, IndexType.MARENGO_MULTIMODAL, "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        )
        
        assert len(embedding) == 1023
        assert cost > 0.0
        mock_services['twelvelabs_service'].generate_text_embedding.assert_called_once()

    def test_generate_media_embedding(self, similarity_engine, mock_services):
        """Test media file embedding generation."""
        # Setup mock
        mock_services['twelvelabs_service'].generate_media_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341  # 1023 dimensions
        }
        
        query = SimilarityQuery(query_video_s3_uri="s3://bucket/video.mp4")
        
        embedding, cost = similarity_engine._generate_query_embedding(
            query, IndexType.MARENGO_MULTIMODAL, "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        )
        
        assert len(embedding) == 1023
        assert cost > 0.0
        mock_services['twelvelabs_service'].generate_media_embedding.assert_called_once_with(
            s3_uri="s3://bucket/video.mp4",
            input_type="video"
        )

    def test_direct_embedding_input(self, similarity_engine):
        """Test direct embedding input."""
        embedding_vector = [0.1, 0.2, 0.3] * 341
        query = SimilarityQuery(query_embedding=embedding_vector)
        
        embedding, cost = similarity_engine._generate_query_embedding(
            query, IndexType.MARENGO_MULTIMODAL, "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        )
        
        assert embedding == embedding_vector
        assert cost == 0.0


class TestSearchExecution:
    """Test search execution and result processing."""

    def test_find_similar_content_text_query(self, similarity_engine, mock_services, sample_s3_search_results):
        """Test finding similar content with text query."""
        # Setup mocks
        mock_services['bedrock_service'].generate_text_embedding.return_value = Mock(
            embedding=[0.1, 0.2, 0.3] * 341
        )
        # Setup TwelveLabs mock for Marengo multimodal index
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341 + [0.1]  # 1024 dimensions
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = sample_s3_search_results
        
        query = SimilarityQuery(
            query_text="find similar videos",
            top_k=5,
            include_explanations=True
        )
        
        response = similarity_engine.find_similar_content(
            query, "arn:aws:s3vectors:us-west-2:123456789:bucket/test/index/video", IndexType.MARENGO_MULTIMODAL
        )
        
        # Verify response structure
        assert isinstance(response, SimilaritySearchResponse)
        assert len(response.results) == 2
        assert response.input_type == QueryInputType.TEXT
        assert response.index_type == IndexType.MARENGO_MULTIMODAL
        assert response.total_results == 2
        assert response.processing_time_ms >= 0  # Can be 0 for mocked operations
        
        # Verify results
        video_result = next((r for r in response.results if r.content_type == 'video'), None)
        assert video_result is not None
        assert video_result.similarity_score > 0.7  # 1.0 - 0.1 distance
        assert video_result.start_sec == 0.0
        assert video_result.end_sec == 5.0
        assert video_result.duration_sec == 5.0
        assert video_result.explanation is not None

    def test_search_by_text_query_convenience_method(self, similarity_engine, mock_services, sample_s3_search_results):
        """Test the search_by_text_query convenience method."""
        # Setup mocks
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = sample_s3_search_results
        
        response = similarity_engine.search_by_text_query(
            query_text="cats playing",
            index_arn="arn:aws:s3vectors:us-west-2:123456789:bucket/test/index/video",
            index_type=IndexType.MARENGO_MULTIMODAL,
            top_k=10
        )
        
        assert isinstance(response, SimilaritySearchResponse)
        assert response.input_type == QueryInputType.TEXT
        assert len(response.results) <= 10

    def test_search_video_scenes_with_text(self, similarity_engine, mock_services, sample_s3_search_results):
        """Test video scene search using text description."""
        # Setup mocks
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = sample_s3_search_results
        
        response = similarity_engine.search_video_scenes(
            video_query="person running in the park",
            index_arn="arn:aws:s3vectors:us-west-2:123456789:bucket/test/index/video",
            time_range=(10.0, 60.0),
            top_k=5
        )
        
        assert isinstance(response, SimilaritySearchResponse)
        assert response.input_type == QueryInputType.TEXT
        
        # Verify temporal filter was applied
        query_call = mock_services['s3_vector_manager'].query_vectors.call_args
        metadata_filter = query_call.kwargs['metadata_filter']
        assert 'start_sec' in metadata_filter
        assert 'end_sec' in metadata_filter
        assert 'content_type' in metadata_filter
        assert metadata_filter['content_type']['$in'] == ['video']

    def test_search_video_scenes_with_s3_uri(self, similarity_engine, mock_services, sample_s3_search_results):
        """Test video scene search using S3 URI."""
        # Setup mocks
        mock_services['twelvelabs_service'].generate_media_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = sample_s3_search_results
        
        response = similarity_engine.search_video_scenes(
            video_query="s3://bucket/reference-video.mp4",
            index_arn="arn:aws:s3vectors:us-west-2:123456789:bucket/test/index/video",
            top_k=5
        )
        
        assert response.input_type == QueryInputType.VIDEO_FILE
        mock_services['twelvelabs_service'].generate_media_embedding.assert_called_once()


class TestResultProcessing:
    """Test result post-processing functionality."""

    def test_convert_s3_results_to_similarity_results(self, similarity_engine, sample_s3_search_results):
        """Test conversion of S3 Vector results to SimilarityResult objects."""
        query = SimilarityQuery(query_text="test", include_explanations=True)
        
        results = similarity_engine._convert_to_similarity_results(
            sample_s3_search_results, query, QueryInputType.TEXT, IndexType.MARENGO_MULTIMODAL
        )
        
        assert len(results) == 2
        
        # Check video result
        video_result = next(r for r in results if r.content_type == 'video')
        assert video_result.key == 'video-test-segment-0001'
        assert video_result.similarity_score == 0.9  # 1.0 - 0.1 distance
        assert video_result.start_sec == 0.0
        assert video_result.end_sec == 5.0
        assert video_result.duration_sec == 5.0
        assert video_result.explanation is not None
        
        # Check text result
        text_result = next(r for r in results if r.content_type == 'text')
        assert text_result.key == 'text-document-0001'
        assert text_result.similarity_score == 0.8  # 1.0 - 0.2 distance

    def test_deduplicate_results(self, similarity_engine):
        """Test result deduplication."""
        results = [
            SimilarityResult(key="doc1", similarity_score=0.9, content_type="text", metadata={"title": "Test"}),
            SimilarityResult(key="doc1", similarity_score=0.8, content_type="text", metadata={"title": "Test"}),  # Duplicate key
            SimilarityResult(key="doc2", similarity_score=0.7, content_type="text", metadata={"title": "Different"}),
        ]
        
        deduplicated = similarity_engine._deduplicate_results(results)
        
        assert len(deduplicated) == 2
        assert deduplicated[0].key == "doc1"
        assert deduplicated[1].key == "doc2"

    def test_apply_diversification(self, similarity_engine):
        """Test result diversification."""
        results = [
            SimilarityResult(key="doc1", similarity_score=0.9, content_type="text", metadata={"category": "A"}),
            SimilarityResult(key="doc2", similarity_score=0.8, content_type="text", metadata={"category": "A"}),  # Similar
            SimilarityResult(key="doc3", similarity_score=0.7, content_type="text", metadata={"category": "B"}),  # Different
        ]
        
        diversified = similarity_engine._apply_diversification(results, diversity_factor=0.5)
        
        assert len(diversified) == 3
        # Results should be re-ordered based on diversity-adjusted confidence
        assert all(hasattr(result, 'confidence_score') for result in diversified)

    def test_filter_by_metadata(self, similarity_engine):
        """Test metadata filtering."""
        results = [
            SimilarityResult(
                key="doc1", similarity_score=0.9, content_type="text",
                metadata={"category": "education", "level": "advanced"}
            ),
            SimilarityResult(
                key="doc2", similarity_score=0.8, content_type="text",
                metadata={"category": "entertainment", "level": "beginner"}
            ),
            SimilarityResult(
                key="doc3", similarity_score=0.6, content_type="text",
                metadata={"category": "education", "level": "beginner"}
            )
        ]
        
        # Filter for education category with minimum similarity
        filtered = similarity_engine.filter_by_metadata(
            results,
            metadata_filters={"category": "education"},
            similarity_threshold=0.7
        )
        
        assert len(filtered) == 1
        assert filtered[0].key == "doc1"


class TestNaturalLanguageProcessing:
    """Test natural language processing features."""

    def test_extract_entities(self, similarity_engine):
        """Test entity extraction from text."""
        entities = similarity_engine._extract_entities("person running in the morning")
        
        assert "running" in entities
        assert "morning" in entities

    def test_expand_with_synonyms(self, similarity_engine):
        """Test synonym expansion."""
        expanded = similarity_engine._expand_with_synonyms("happy fast person")
        
        # Should include original words plus synonyms
        assert "happy" in expanded
        assert "joyful" in expanded
        assert "fast" in expanded
        assert "quick" in expanded
        assert "person" in expanded

    def test_enhance_text_query(self, similarity_engine):
        """Test complete text query enhancement."""
        query = SimilarityQuery(
            query_text="happy fast person",
            extract_entities=True,
            expand_synonyms=True
        )
        
        enhanced = similarity_engine._enhance_text_query("happy fast person", query)
        
        # Should include synonyms
        assert "joyful" in enhanced or "quick" in enhanced


class TestPerformanceAndAnalytics:
    """Test performance tracking and analytics."""

    def test_update_search_stats(self, similarity_engine):
        """Test search statistics tracking."""
        initial_stats = dict(similarity_engine.search_stats)
        
        similarity_engine._update_search_stats(QueryInputType.TEXT, 100, 0.001)
        
        updated_stats = similarity_engine.search_stats
        assert updated_stats['total_searches'] == initial_stats['total_searches'] + 1
        assert updated_stats['total_cost'] > initial_stats['total_cost']
        assert updated_stats['searches_by_input_type']['text'] == 1

    def test_generate_search_suggestions(self, similarity_engine, mock_services, sample_s3_search_results):
        """Test search result suggestions generation."""
        # Setup mocks for low similarity results
        low_similarity_results = {
            'vectors': [
                {
                    'key': 'doc1',
                    'distance': 0.8,  # Low similarity
                    'metadata': {'content_type': 'text'}
                }
            ]
        }
        
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = low_similarity_results
        
        query = SimilarityQuery(query_text="test", top_k=10)
        response = similarity_engine.find_similar_content(
            query, "arn:aws:s3vectors:us-west-2:123456789:bucket/test/index/video", IndexType.MARENGO_MULTIMODAL
        )
        
        assert len(response.search_suggestions) > 0
        assert any("different query terms" in suggestion for suggestion in response.search_suggestions)

    def test_metadata_filtering_operators(self, similarity_engine):
        """Test various metadata filtering operators."""
        metadata = {"score": 85, "category": "education", "tags": ["python", "tutorial"]}
        
        # Test various filter operators
        filters_and_expected = [
            ({"score": {"$gte": 80}}, True),
            ({"score": {"$lt": 80}}, False),
            ({"category": {"$eq": "education"}}, True),
            ({"category": {"$ne": "entertainment"}}, True),
            ({"tags": {"$in": ["python"]}}, True),
            ({"tags": {"$nin": ["java"]}}, True),
        ]
        
        for filters, expected in filters_and_expected:
            result = similarity_engine._matches_metadata_filters(metadata, filters)
            assert result == expected, f"Filter {filters} should return {expected}"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_unsupported_index_type(self, similarity_engine):
        """Test error for unsupported index type."""
        query = SimilarityQuery(query_text="test")
        
        with pytest.raises(ValidationError, match="Unsupported index type"):
            similarity_engine._validate_query_index_compatibility(
                query, "invalid_index_type", QueryInputType.TEXT
            )

    def test_video_key_not_implemented(self, similarity_engine):
        """Test error for video key queries (not yet implemented)."""
        with pytest.raises(ValidationError, match="not yet implemented"):
            similarity_engine._get_embedding_from_video_key("video-key-123")

    def test_media_query_with_titan_index(self, similarity_engine, mock_services):
        """Test error when using media query with Titan text index."""
        query = SimilarityQuery(query_video_s3_uri="s3://bucket/video.mp4")
        
        with pytest.raises(ValidationError, match="Media queries only supported with Marengo indexes"):
            similarity_engine._generate_query_embedding(query, IndexType.TITAN_TEXT)


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    def test_multimodal_media_company_workflow(self, similarity_engine, mock_services):
        """Test a realistic media company workflow."""
        # Setup mocks for a complete workflow
        mock_services['twelvelabs_service'].generate_text_embedding.return_value = {
            'embedding': [0.1, 0.2, 0.3] * 341
        }
        mock_services['s3_vector_manager'].query_vectors.return_value = {
            'vectors': [
                {
                    'key': 'movie-trailer-action-scene-001',
                    'distance': 0.15,
                    'metadata': {
                        'content_type': 'video',
                        'start_sec': 45.0,
                        'end_sec': 52.0,
                        'embedding_option': 'visual-text',
                        'genre': 'action',
                        'movie_id': 'mv_12345',
                        'scene_type': 'chase'
                    }
                },
                {
                    'key': 'tv-show-episode-similar-001',
                    'distance': 0.25,
                    'metadata': {
                        'content_type': 'video',
                        'start_sec': 120.0,
                        'end_sec': 135.0,
                        'embedding_option': 'visual-text',
                        'genre': 'action',
                        'series_id': 'tv_67890',
                        'scene_type': 'chase'
                    }
                }
            ]
        }
        
        # Media company searches for "car chase scenes" 
        response = similarity_engine.search_by_text_query(
            query_text="exciting car chase scenes with explosions",
            index_arn="arn:aws:s3vectors:us-west-2:123456789:bucket/media-library/index/content",
            index_type=IndexType.MARENGO_MULTIMODAL,
            top_k=10,
            metadata_filters={"genre": "action"}
        )
        
        # Verify realistic results
        assert len(response.results) == 2
        assert response.result_distribution["video"] == 2
        assert all(r.content_type == "video" for r in response.results)
        assert all("chase" in r.metadata.get("scene_type", "") for r in response.results)
        
        # Check temporal information
        for result in response.results:
            assert result.duration_sec > 0
            assert result.start_sec is not None
            assert result.end_sec is not None

    def test_cost_tracking_across_searches(self, similarity_engine, mock_services):
        """Test cost tracking across multiple searches."""
        # Setup mocks
        mock_services['bedrock_service'].generate_text_embedding.return_value = Mock(
            embedding=[0.1, 0.2, 0.3] * 341
        )
        mock_services['s3_vector_manager'].query_vectors.return_value = {'vectors': []}
        
        initial_cost = similarity_engine.search_stats['total_cost']
        
        # Perform multiple searches
        for i in range(3):
            query = SimilarityQuery(query_text=f"test query {i}")
            similarity_engine.find_similar_content(
                query, "arn:test", IndexType.TITAN_TEXT
            )
        
        # Verify cost tracking
        final_cost = similarity_engine.search_stats['total_cost']
        assert final_cost > initial_cost
        assert similarity_engine.search_stats['total_searches'] == 3
        assert similarity_engine.search_stats['average_latency_ms'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])