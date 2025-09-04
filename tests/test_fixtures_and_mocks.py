#!/usr/bin/env python3
"""
Test Fixtures and Mock Scenarios for S3Vector Integration Tests

This module provides comprehensive test fixtures, mock data, and scenario builders
to support the integration test framework.
"""

import json
import time
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass, asdict
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@dataclass
class MockVideoData:
    """Mock video data for testing."""
    filename: str
    duration_seconds: int
    size_mb: float
    s3_uri: str
    content_type: str
    expected_segments: int
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class MockEmbeddingResult:
    """Mock embedding generation result."""
    embedding: List[float]
    model_id: str
    input_text: str
    processing_time_ms: int
    dimensions: int = 1024

@dataclass
class MockSearchResult:
    """Mock search result for testing."""
    vector_key: str
    similarity_score: float
    metadata: Dict[str, Any]
    temporal_info: Optional[Dict[str, Any]] = None

@dataclass
class MockResourceStatus:
    """Mock AWS resource status."""
    resource_type: str
    resource_id: str
    status: str
    created_at: str
    metadata: Dict[str, Any]

class IntegrationTestFixtures:
    """Centralized test fixtures for integration testing."""
    
    @staticmethod
    def create_sample_videos() -> Dict[str, MockVideoData]:
        """Create sample video data for testing."""
        return {
            "short_video": MockVideoData(
                filename="short_action_scene.mp4",
                duration_seconds=30,
                size_mb=5.0,
                s3_uri="s3://test-bucket/videos/short_action_scene.mp4",
                content_type="action_scene",
                expected_segments=2,
                metadata={"genre": "action", "quality": "720p", "fps": 30}
            ),
            "medium_video": MockVideoData(
                filename="medium_drama_dialogue.mp4",
                duration_seconds=120,
                size_mb=25.0,
                s3_uri="s3://test-bucket/videos/medium_drama_dialogue.mp4",
                content_type="dialogue_scene",
                expected_segments=8,
                metadata={"genre": "drama", "quality": "1080p", "fps": 24}
            ),
            "long_video": MockVideoData(
                filename="long_documentary.mp4",
                duration_seconds=600,
                size_mb=150.0,
                s3_uri="s3://test-bucket/videos/long_documentary.mp4",
                content_type="documentary",
                expected_segments=40,
                metadata={"genre": "documentary", "quality": "4K", "fps": 30}
            )
        }
    
    @staticmethod
    def create_query_patterns() -> Dict[str, List[str]]:
        """Create diverse query patterns for testing."""
        return {
            "simple_visual": [
                "person walking",
                "car driving",
                "building exterior",
                "sunset landscape"
            ],
            "simple_audio": [
                "music playing",
                "dialogue speaking",
                "nature sounds",
                "urban noise"
            ],
            "complex_multimodal": [
                "emotional dialogue scene with orchestral music during sunset lighting",
                "fast-paced action sequence with explosions and dramatic camera angles", 
                "quiet indoor conversation with subtle background music and soft lighting",
                "outdoor chase scene with vehicle sounds and dynamic camera movement"
            ],
            "temporal_specific": [
                "opening scene introduction",
                "climactic action sequence", 
                "closing credits music",
                "transition between scenes"
            ]
        }
    
    @staticmethod
    def create_embedding_results(query_text: str, result_count: int = 10) -> List[MockEmbeddingResult]:
        """Create mock embedding results."""
        results = []
        base_embedding = [0.1] * 1024  # 1024-dimensional base
        
        for i in range(result_count):
            # Vary embeddings slightly for diversity
            embedding = [val + (i * 0.01) for val in base_embedding]
            
            results.append(MockEmbeddingResult(
                embedding=embedding,
                model_id="amazon.titan-embed-text-v2:0",
                input_text=f"Generated embedding {i+1} for: {query_text}",
                processing_time_ms=150 + (i * 10),
                dimensions=1024
            ))
        
        return results
    
    @staticmethod
    def create_search_results(query_text: str, result_count: int = 5) -> List[MockSearchResult]:
        """Create mock search results."""
        results = []
        
        for i in range(result_count):
            similarity = 0.95 - (i * 0.05)  # Decreasing similarity scores
            
            results.append(MockSearchResult(
                vector_key=f"video-segment-{i+1}",
                similarity_score=similarity,
                metadata={
                    "title": f"Test Video {i+1}",
                    "content_type": "video_segment",
                    "genre": ["action", "drama", "comedy"][i % 3],
                    "duration_sec": 15 + (i * 5)
                },
                temporal_info={
                    "start_sec": i * 15.0,
                    "end_sec": (i + 1) * 15.0,
                    "segment_id": f"seg_{i+1}"
                }
            ))
        
        return results
    
    @staticmethod
    def create_aws_resources() -> Dict[str, MockResourceStatus]:
        """Create mock AWS resource statuses."""
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return {
            "s3vector_bucket": MockResourceStatus(
                resource_type="s3vector_bucket",
                resource_id="test-s3vector-bucket-123",
                status="active",
                created_at=timestamp,
                metadata={
                    "encryption": "SSE-S3",
                    "region": "us-west-2",
                    "indexes": 3
                }
            ),
            "visual_text_index": MockResourceStatus(
                resource_type="s3vector_index",
                resource_id="bucket/test-bucket/index/visual-text-index",
                status="active",
                created_at=timestamp,
                metadata={
                    "dimensions": 1024,
                    "distance_metric": "cosine",
                    "vector_count": 1500
                }
            ),
            "opensearch_collection": MockResourceStatus(
                resource_type="opensearch_collection",
                resource_id="test-collection-456",
                status="active",
                created_at=timestamp,
                metadata={
                    "type": "serverless",
                    "region": "us-west-2",
                    "indices": 2
                }
            )
        }

class MockServiceBuilder:
    """Builder for creating mock services with realistic behavior."""
    
    @staticmethod
    def create_s3vector_storage_mock() -> Mock:
        """Create mock S3Vector storage service."""
        mock_storage = Mock()
        
        # Mock bucket operations
        mock_storage.create_vector_bucket.return_value = {
            "status": "created",
            "bucket_name": "test-bucket",
            "encryption_enabled": True
        }
        
        mock_storage.bucket_exists.return_value = True
        
        # Mock index operations
        mock_storage.create_vector_index.return_value = {
            "status": "created",
            "index_name": "test-index",
            "index_arn": "arn:aws:s3vectors:us-west-2:123456789012:index/test-bucket/test-index"
        }
        
        mock_storage.index_exists.return_value = True
        
        # Mock vector operations
        mock_storage.put_vectors_batch.return_value = {"stored_count": 10}
        
        mock_storage.query_similar_vectors.return_value = {
            "vectors": [
                {
                    "key": f"vector-{i}",
                    "distance": 0.1 + (i * 0.05),
                    "metadata": {"type": "test", "index": i}
                }
                for i in range(5)
            ]
        }
        
        return mock_storage
    
    @staticmethod
    def create_bedrock_embedding_mock() -> Mock:
        """Create mock Bedrock embedding service."""
        mock_bedrock = Mock()
        
        # Mock single embedding generation
        mock_result = Mock()
        mock_result.embedding = [0.1] * 1024
        mock_result.model_id = "amazon.titan-embed-text-v2:0"
        mock_result.processing_time_ms = 150
        
        mock_bedrock.generate_text_embedding.return_value = mock_result
        
        # Mock batch embedding generation
        mock_bedrock.batch_generate_embeddings.return_value = [mock_result] * 5
        
        # Mock model validation
        mock_bedrock.validate_model_access.return_value = True
        
        # Mock cost estimation
        mock_bedrock.estimate_cost.return_value = {
            "model_id": "amazon.titan-embed-text-v2:0",
            "text_count": 5,
            "estimated_cost_usd": 0.0001
        }
        
        return mock_bedrock
    
    @staticmethod
    def create_twelvelabs_processing_mock() -> Mock:
        """Create mock TwelveLabs video processing service."""
        mock_twelvelabs = Mock()
        
        # Mock video processing
        mock_processing_result = Mock()
        mock_processing_result.embeddings = [
            {
                "embedding": [0.1 + i * 0.01] * 1024,
                "startSec": i * 5.0,
                "endSec": (i + 1) * 5.0,
                "embeddingOption": "visual-text"
            }
            for i in range(8)
        ]
        mock_processing_result.input_source = "s3://test-bucket/video.mp4"
        mock_processing_result.model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        mock_processing_result.total_segments = 8
        mock_processing_result.video_duration_sec = 40.0
        
        mock_twelvelabs.process_video_sync.return_value = mock_processing_result
        
        # Mock job management
        mock_twelvelabs.create_embeddings_job.return_value = {
            "job_id": "test-job-123",
            "status": "processing"
        }
        
        mock_twelvelabs.get_job_status.return_value = {
            "job_id": "test-job-123",
            "status": "completed"
        }
        
        return mock_twelvelabs
    
    @staticmethod
    def create_opensearch_integration_mock() -> Mock:
        """Create mock OpenSearch integration service."""
        mock_opensearch = Mock()
        
        # Mock collection operations
        mock_opensearch.create_serverless_collection.return_value = {
            "collection_id": "test-collection-123",
            "status": "created",
            "endpoint": "https://test-collection.us-west-2.aoss.amazonaws.com"
        }
        
        # Mock hybrid search
        mock_opensearch.hybrid_search.return_value = {
            "hits": [
                {
                    "_id": f"doc-{i}",
                    "_score": 0.9 - (i * 0.1),
                    "_source": {
                        "content": f"Search result {i+1}",
                        "metadata": {"type": "hybrid_result"}
                    }
                }
                for i in range(3)
            ],
            "total": 3
        }
        
        return mock_opensearch

class ScenarioBuilder:
    """Builder for creating test scenarios with realistic data flows."""
    
    @staticmethod
    def build_complete_user_journey_scenario() -> Dict[str, Any]:
        """Build complete user journey test scenario."""
        fixtures = IntegrationTestFixtures()
        
        return {
            "test_videos": fixtures.create_sample_videos(),
            "query_patterns": fixtures.create_query_patterns(),
            "expected_results": fixtures.create_search_results("test query", 10),
            "aws_resources": fixtures.create_aws_resources(),
            "performance_targets": {
                "total_workflow_ms": 180000,
                "video_processing_ms": 120000,
                "search_execution_ms": 5000,
                "success_rate": 0.98
            }
        }
    
    @staticmethod
    def build_performance_test_scenario(concurrent_users: int = 4) -> Dict[str, Any]:
        """Build performance test scenario."""
        return {
            "concurrent_users": concurrent_users,
            "operations_per_user": 3,
            "video_sizes": [10, 25, 50],  # MB
            "expected_degradation": 2.0,  # Max 2x slower
            "error_tolerance": 0.05,  # 5% errors
            "resource_limits": {
                "max_memory_mb": 2048,
                "max_cpu_percent": 80
            }
        }
    
    @staticmethod
    def build_error_recovery_scenario() -> Dict[str, Any]:
        """Build error recovery test scenario."""
        return {
            "network_failures": [
                "temporary_disconnection",
                "dns_resolution_failure", 
                "ssl_certificate_error"
            ],
            "aws_service_failures": [
                "s3vector_outage",
                "bedrock_rate_limiting",
                "opensearch_quota_exceeded"
            ],
            "resource_constraints": [
                "memory_exhaustion",
                "disk_space_full",
                "api_quota_exceeded"
            ],
            "recovery_timeouts": {
                "network_recovery_ms": 30000,
                "service_recovery_ms": 60000,
                "resource_recovery_ms": 45000
            }
        }
    
    @staticmethod
    def build_aws_integration_scenario() -> Dict[str, Any]:
        """Build AWS integration test scenario."""
        return {
            "regions": ["us-west-2", "us-east-1", "eu-west-1"],
            "services": {
                "s3vectors": {
                    "bucket_configurations": [
                        {"encryption": "SSE-S3"},
                        {"encryption": "SSE-KMS", "kms_key": "alias/test-key"}
                    ],
                    "index_configurations": [
                        {"metric": "cosine", "dimensions": 1024},
                        {"metric": "euclidean", "dimensions": 512}
                    ]
                },
                "bedrock": {
                    "models": [
                        "amazon.titan-embed-text-v2:0",
                        "cohere.embed-english-v3"
                    ]
                },
                "opensearch": {
                    "patterns": ["export", "engine"]
                }
            },
            "cost_thresholds": {
                "max_hourly_cost_usd": 10.0,
                "max_monthly_cost_usd": 500.0
            }
        }

# Export key classes for easy imports
__all__ = [
    'MockVideoData',
    'MockEmbeddingResult', 
    'MockSearchResult',
    'MockResourceStatus',
    'IntegrationTestFixtures',
    'MockServiceBuilder',
    'ScenarioBuilder'
]

if __name__ == "__main__":
    # Example usage and validation
    fixtures = IntegrationTestFixtures()
    mock_builder = MockServiceBuilder()
    scenario_builder = ScenarioBuilder()
    
    print("🧪 Test Fixtures and Mocks Validation")
    print("=" * 50)
    
    # Test fixture creation
    videos = fixtures.create_sample_videos()
    print(f"✅ Created {len(videos)} video fixtures")
    
    queries = fixtures.create_query_patterns()
    print(f"✅ Created {sum(len(patterns) for patterns in queries.values())} query patterns")
    
    # Test mock services
    s3vector_mock = mock_builder.create_s3vector_storage_mock()
    print(f"✅ Created S3Vector storage mock with {len(dir(s3vector_mock))} methods")
    
    bedrock_mock = mock_builder.create_bedrock_embedding_mock()
    print(f"✅ Created Bedrock embedding mock with {len(dir(bedrock_mock))} methods")
    
    # Test scenario building
    user_journey = scenario_builder.build_complete_user_journey_scenario()
    print(f"✅ Built user journey scenario with {len(user_journey)} components")
    
    print("\n🎉 All fixtures and mocks validated successfully!")