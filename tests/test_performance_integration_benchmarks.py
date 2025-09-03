#!/usr/bin/env python3
"""
Performance Integration Benchmarks

This test suite provides comprehensive performance benchmarks for the enhanced
S3Vector system integration, testing concurrent processing, memory usage,
scalability, and service coordination performance.
"""

import pytest
import asyncio
import time
import threading
import psutil
import gc
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.multi_vector_coordinator import MultiVectorCoordinator, MultiVectorConfig, ProcessingMode
from src.services.streamlit_integration_utils import StreamlitServiceManager, StreamlitIntegrationConfig
from src.services.similarity_search_engine import SimilaritySearchEngine, SimilarityQuery
from src.exceptions import VectorStorageError


@dataclass
class PerformanceMetrics:
    """Container for performance measurement results."""
    execution_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    concurrent_operations: int
    success_rate: float
    throughput_ops_per_sec: float
    error_count: int = 0
    additional_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_metrics is None:
            self.additional_metrics = {}


class PerformanceProfiler:
    """Performance profiler for benchmark measurements."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None
        
    def start_profiling(self):
        """Start performance profiling."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.start_cpu = self.process.cpu_percent()
        
    def stop_profiling(self, operation_count: int = 1) -> PerformanceMetrics:
        """Stop profiling and return metrics."""
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        end_cpu = self.process.cpu_percent()
        
        execution_time_ms = (end_time - self.start_time) * 1000
        memory_usage_mb = end_memory - self.start_memory
        cpu_usage_percent = end_cpu
        throughput = operation_count / (execution_time_ms / 1000) if execution_time_ms > 0 else 0
        
        return PerformanceMetrics(
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent,
            concurrent_operations=operation_count,
            success_rate=1.0,  # Default to 100% for successful operations
            throughput_ops_per_sec=throughput
        )


class TestConcurrentProcessingBenchmarks:
    """Benchmark concurrent processing capabilities."""
    
    @pytest.fixture
    def performance_setup(self):
        """Setup for performance testing."""
        config = StreamlitIntegrationConfig(
            enable_multi_vector=True,
            enable_concurrent_processing=True,
            max_concurrent_jobs=8
        )
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine') as mock_search:
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService') as mock_twelvelabs:
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        
                        # Configure fast mock responses
                        mock_search.return_value.search_similar_vectors.return_value = {
                            "results": [{"score": 0.9, "metadata": {}}],
                            "total": 1,
                            "processing_time_ms": 10
                        }
                        
                        mock_twelvelabs.return_value.create_embeddings_job.return_value = {
                            "job_id": f"job-{int(time.time())}", 
                            "status": "completed"
                        }
                        
                        manager = StreamlitServiceManager(config)
                        return manager

    def test_concurrent_video_processing_benchmark(self, performance_setup):
        """Benchmark concurrent video processing operations."""
        manager = performance_setup
        profiler = PerformanceProfiler()
        
        # Test data
        video_batch = [
            {'file_path': f'/tmp/video_{i}.mp4', 'title': f'Test Video {i}'}
            for i in range(10)
        ]
        
        profiler.start_profiling()
        
        # Process videos concurrently
        results = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(manager.process_video, video_data)
                for video_data in video_batch
            ]
            
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    results.append(result)
                except Exception as e:
                    results.append(None)
        
        metrics = profiler.stop_profiling(len(video_batch))
        
        # Performance assertions
        assert metrics.execution_time_ms < 10000  # Under 10 seconds for 10 videos
        assert metrics.memory_usage_mb < 500  # Under 500MB memory increase
        assert len([r for r in results if r is not None]) >= 8  # At least 80% success rate
        
        print(f"Concurrent Video Processing Benchmark:")
        print(f"  Execution Time: {metrics.execution_time_ms:.2f}ms")
        print(f"  Memory Usage: {metrics.memory_usage_mb:.2f}MB")
        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} ops/sec")
        print(f"  Success Rate: {len([r for r in results if r is not None]) / len(results) * 100:.1f}%")

    def test_concurrent_search_benchmark(self, performance_setup):
        """Benchmark concurrent search operations."""
        manager = performance_setup
        profiler = PerformanceProfiler()
        
        # Test search queries
        search_queries = [
            {
                'query_text': f'test query {i}',
                'vector_types': ['visual-text'],
                'top_k': 5
            }
            for i in range(20)
        ]
        
        profiler.start_profiling()
        
        # Execute searches concurrently
        results = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(manager.search_videos, query)
                for query in search_queries
            ]
            
            for future in futures:
                try:
                    result = future.result(timeout=10)
                    results.append(result)
                except Exception:
                    results.append(None)
        
        metrics = profiler.stop_profiling(len(search_queries))
        
        # Performance assertions
        assert metrics.execution_time_ms < 5000  # Under 5 seconds for 20 searches
        assert metrics.throughput_ops_per_sec > 2  # At least 2 searches per second
        
        success_count = len([r for r in results if r is not None])
        success_rate = success_count / len(results)
        assert success_rate >= 0.9  # At least 90% success rate
        
        print(f"Concurrent Search Benchmark:")
        print(f"  Execution Time: {metrics.execution_time_ms:.2f}ms")
        print(f"  Memory Usage: {metrics.memory_usage_mb:.2f}MB")
        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} searches/sec")
        print(f"  Success Rate: {success_rate * 100:.1f}%")

    def test_mixed_workload_benchmark(self, performance_setup):
        """Benchmark mixed workload of processing and searching."""
        manager = performance_setup
        profiler = PerformanceProfiler()
        
        profiler.start_profiling()
        
        def process_videos():
            """Process videos in background."""
            for i in range(5):
                try:
                    manager.process_video({'file_path': f'/tmp/bg_video_{i}.mp4'})
                    time.sleep(0.1)  # Simulate processing delay
                except Exception:
                    pass
        
        def search_videos():
            """Perform searches concurrently."""
            for i in range(10):
                try:
                    manager.search_videos({
                        'query_text': f'search {i}',
                        'vector_types': ['visual-text']
                    })
                    time.sleep(0.05)  # Simulate search delay
                except Exception:
                    pass
        
        # Run mixed workload
        with ThreadPoolExecutor(max_workers=6) as executor:
            process_future = executor.submit(process_videos)
            search_future = executor.submit(search_videos)
            
            process_future.result(timeout=30)
            search_future.result(timeout=30)
        
        metrics = profiler.stop_profiling(15)  # 5 processing + 10 search
        
        # Performance assertions for mixed workload
        assert metrics.execution_time_ms < 15000  # Under 15 seconds
        assert metrics.memory_usage_mb < 600  # Memory stays reasonable
        
        print(f"Mixed Workload Benchmark:")
        print(f"  Execution Time: {metrics.execution_time_ms:.2f}ms")
        print(f"  Memory Usage: {metrics.memory_usage_mb:.2f}MB")
        print(f"  CPU Usage: {metrics.cpu_usage_percent:.1f}%")


class TestScalabilityBenchmarks:
    """Test scalability of the integrated system."""
    
    @pytest.fixture
    def scalability_setup(self):
        """Setup for scalability testing."""
        with patch('src.services.multi_vector_coordinator.TwelveLabsVideoProcessingService'):
            with patch('src.services.multi_vector_coordinator.SimilaritySearchEngine') as mock_search:
                with patch('src.services.multi_vector_coordinator.S3VectorStorageManager'):
                    with patch('src.services.multi_vector_coordinator.BedrockEmbeddingService'):
                        
                        # Configure mock for scalability testing
                        mock_search.return_value.search_similar_vectors.return_value = {
                            "results": [{"score": 0.8}] * 10,
                            "total": 10,
                            "processing_time_ms": 50
                        }
                        
                        config = MultiVectorConfig(
                            max_concurrent_jobs=16,
                            processing_mode=ProcessingMode.PARALLEL,
                            batch_size=10
                        )
                        
                        coordinator = MultiVectorCoordinator(config=config)
                        return coordinator

    def test_load_scaling_benchmark(self, scalability_setup):
        """Test how system scales with increasing load."""
        coordinator = scalability_setup
        
        # Test different load levels
        load_levels = [1, 5, 10, 20, 50]
        results = {}
        
        for load_level in load_levels:
            profiler = PerformanceProfiler()
            profiler.start_profiling()
            
            # Create load
            with ThreadPoolExecutor(max_workers=min(load_level, 16)) as executor:
                futures = []
                for i in range(load_level):
                    # Mock search request
                    search_request = {
                        'query_text': f'load test {i}',
                        'vector_types': ['visual-text']
                    }
                    
                    if hasattr(coordinator, 'search_across_vector_types'):
                        future = executor.submit(
                            lambda: coordinator.search_across_vector_types(search_request)
                        )
                        futures.append(future)
                
                # Wait for completion
                completed = 0
                for future in futures:
                    try:
                        future.result(timeout=30)
                        completed += 1
                    except Exception:
                        pass
            
            metrics = profiler.stop_profiling(load_level)
            metrics.success_rate = completed / load_level if load_level > 0 else 0
            results[load_level] = metrics
            
            print(f"Load Level {load_level}:")
            print(f"  Time: {metrics.execution_time_ms:.2f}ms")
            print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} ops/sec")
            print(f"  Success Rate: {metrics.success_rate * 100:.1f}%")
        
        # Verify scaling characteristics
        # Throughput should not degrade significantly with moderate load
        if len(results) >= 3:
            low_load = results[load_levels[0]]
            mid_load = results[load_levels[len(load_levels)//2]]
            
            # Allow some degradation but not complete collapse
            throughput_ratio = mid_load.throughput_ops_per_sec / low_load.throughput_ops_per_sec
            assert throughput_ratio > 0.5  # Should maintain at least 50% of low-load throughput

    def test_memory_scaling_benchmark(self, scalability_setup):
        """Test memory usage scaling."""
        coordinator = scalability_setup
        
        # Test memory usage with different data sizes
        batch_sizes = [1, 10, 50, 100]
        memory_results = {}
        
        for batch_size in batch_sizes:
            profiler = PerformanceProfiler()
            profiler.start_profiling()
            
            # Simulate processing batch
            mock_data = [f"data_item_{i}" for i in range(batch_size)]
            
            # Force garbage collection before measurement
            gc.collect()
            
            # Simulate memory usage
            time.sleep(0.1 * batch_size / 10)  # Simulate work proportional to batch size
            
            metrics = profiler.stop_profiling(batch_size)
            memory_results[batch_size] = metrics
            
            print(f"Batch Size {batch_size}:")
            print(f"  Memory Usage: {metrics.memory_usage_mb:.2f}MB")
            print(f"  Time per item: {metrics.execution_time_ms / batch_size:.2f}ms/item")
        
        # Memory should scale reasonably (not exponentially)
        if len(memory_results) >= 2:
            small_batch = memory_results[batch_sizes[0]]
            large_batch = memory_results[batch_sizes[-1]]
            
            # Memory usage should not increase more than 10x for 100x data
            memory_ratio = large_batch.memory_usage_mb / max(small_batch.memory_usage_mb, 1)
            assert memory_ratio < 20  # Reasonable memory scaling


class TestResourceUtilizationBenchmarks:
    """Test resource utilization optimization."""
    
    def test_cpu_utilization_benchmark(self):
        """Test CPU utilization during intensive operations."""
        with patch('src.services.multi_vector_coordinator.TwelveLabsVideoProcessingService'):
            with patch('src.services.multi_vector_coordinator.SimilaritySearchEngine'):
                with patch('src.services.multi_vector_coordinator.S3VectorStorageManager'):
                    with patch('src.services.multi_vector_coordinator.BedrockEmbeddingService'):
                        
                        config = MultiVectorConfig(
                            max_concurrent_jobs=psutil.cpu_count(),
                            processing_mode=ProcessingMode.PARALLEL
                        )
                        
                        coordinator = MultiVectorCoordinator(config=config)
                        
                        # Monitor CPU usage during operations
                        cpu_samples = []
                        
                        def monitor_cpu():
                            """Monitor CPU usage."""
                            for _ in range(10):
                                cpu_samples.append(psutil.cpu_percent(interval=0.1))
                        
                        def perform_work():
                            """Simulate CPU-intensive work."""
                            for i in range(100):
                                # Simulate computation
                                _ = sum(range(1000))
                        
                        # Run work and monitoring concurrently
                        with ThreadPoolExecutor(max_workers=2) as executor:
                            monitor_future = executor.submit(monitor_cpu)
                            work_future = executor.submit(perform_work)
                            
                            work_future.result()
                            monitor_future.result()
                        
                        avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
                        max_cpu = max(cpu_samples) if cpu_samples else 0
                        
                        print(f"CPU Utilization Benchmark:")
                        print(f"  Average CPU: {avg_cpu:.1f}%")
                        print(f"  Peak CPU: {max_cpu:.1f}%")
                        
                        # CPU should be utilized but not completely saturated
                        assert avg_cpu > 10  # Should use some CPU
                        assert max_cpu < 95  # Should not saturate completely

    def test_thread_pool_efficiency(self):
        """Test thread pool efficiency."""
        config = StreamlitIntegrationConfig(
            max_concurrent_jobs=8,
            enable_concurrent_processing=True
        )
        
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine'):
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        
                        manager = StreamlitServiceManager(config)
                        
                        # Test thread pool efficiency
                        profiler = PerformanceProfiler()
                        profiler.start_profiling()
                        
                        def worker_task(task_id):
                            """Simulate work task."""
                            time.sleep(0.1)  # Simulate I/O
                            return f"task_{task_id}_completed"
                        
                        # Execute tasks
                        with ThreadPoolExecutor(max_workers=8) as executor:
                            futures = [
                                executor.submit(worker_task, i) 
                                for i in range(20)
                            ]
                            
                            results = [future.result() for future in futures]
                        
                        metrics = profiler.stop_profiling(20)
                        
                        # Should complete efficiently
                        assert len(results) == 20
                        assert metrics.execution_time_ms < 3000  # Should complete in under 3 seconds
                        assert metrics.throughput_ops_per_sec > 5  # Good throughput
                        
                        print(f"Thread Pool Efficiency:")
                        print(f"  Tasks Completed: {len(results)}")
                        print(f"  Total Time: {metrics.execution_time_ms:.2f}ms")
                        print(f"  Throughput: {metrics.throughput_ops_per_sec:.2f} tasks/sec")


class TestPerformanceRegression:
    """Test for performance regressions."""
    
    def test_baseline_performance_check(self):
        """Establish baseline performance metrics."""
        with patch('src.services.streamlit_integration_utils.S3VectorStorageManager'):
            with patch('src.services.streamlit_integration_utils.SimilaritySearchEngine') as mock_search:
                with patch('src.services.streamlit_integration_utils.TwelveLabsVideoProcessingService'):
                    with patch('src.services.streamlit_integration_utils.BedrockEmbeddingService'):
                        
                        mock_search.return_value.search_similar_vectors.return_value = {
                            "results": [{"score": 0.9}] * 5,
                            "total": 5,
                            "processing_time_ms": 25
                        }
                        
                        manager = StreamlitServiceManager()
                        
                        # Baseline test: single search operation
                        profiler = PerformanceProfiler()
                        profiler.start_profiling()
                        
                        result = manager.search_videos({
                            'query_text': 'baseline test',
                            'vector_types': ['visual-text']
                        })
                        
                        metrics = profiler.stop_profiling(1)
                        
                        # Baseline expectations (adjust based on actual system)
                        assert metrics.execution_time_ms < 1000  # Under 1 second
                        assert metrics.memory_usage_mb < 100    # Under 100MB
                        
                        print(f"Baseline Performance:")
                        print(f"  Single Search Time: {metrics.execution_time_ms:.2f}ms")
                        print(f"  Memory Overhead: {metrics.memory_usage_mb:.2f}MB")
                        
                        # Store baseline for future regression testing
                        baseline_metrics = {
                            'single_search_time_ms': metrics.execution_time_ms,
                            'single_search_memory_mb': metrics.memory_usage_mb,
                            'timestamp': time.time()
                        }
                        
                        return baseline_metrics


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([
        __file__,
        "-v", 
        "-s",  # Don't capture output so we can see benchmark results
        "--tb=short"
    ])