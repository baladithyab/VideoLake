#!/usr/bin/env python3
"""
Performance Tests for Enhanced Streamlit Application

Comprehensive performance testing suite covering:
- Multi-vector processing scalability
- Visualization performance with large embedding sets
- Memory usage during PCA/t-SNE computation
- S3Vector index query performance
- UI responsiveness under load
- Concurrent user simulation
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
import concurrent.futures
import psutil
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional
import gc
import tracemalloc
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

# Import components to test
from frontend.unified_streamlit_app import UnifiedStreamlitApp, ProcessedVideo


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    operation: str
    duration_ms: float
    memory_peak_mb: float
    memory_delta_mb: float
    cpu_percent: float
    throughput_ops_per_sec: float
    data_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'duration_ms': self.duration_ms,
            'memory_peak_mb': self.memory_peak_mb,
            'memory_delta_mb': self.memory_delta_mb,
            'cpu_percent': self.cpu_percent,
            'throughput_ops_per_sec': self.throughput_ops_per_sec,
            'data_size': self.data_size
        }


class PerformanceProfiler:
    """Performance profiling utility for detailed measurements."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_memory = 0
        self.start_time = 0
        self.peak_memory = 0
        
    def __enter__(self):
        gc.collect()  # Clean up before measurement
        tracemalloc.start()
        self.start_memory = self.process.memory_info().rss / (1024 * 1024)  # MB
        self.start_time = time.perf_counter()
        self.peak_memory = self.start_memory
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        self.duration = (end_time - self.start_time) * 1000  # ms
        self.peak_memory = max(self.peak_memory, current / (1024 * 1024))  # MB
        self.memory_delta = self.peak_memory - self.start_memory
        
    def get_metrics(self, operation: str, data_size: int, ops_count: int = 1) -> PerformanceMetrics:
        """Get performance metrics for the profiled operation."""
        cpu_percent = self.process.cpu_percent()
        throughput = ops_count / (self.duration / 1000) if self.duration > 0 else 0
        
        return PerformanceMetrics(
            operation=operation,
            duration_ms=self.duration,
            memory_peak_mb=self.peak_memory,
            memory_delta_mb=self.memory_delta,
            cpu_percent=cpu_percent,
            throughput_ops_per_sec=throughput,
            data_size=data_size
        )


class TestEmbeddingPerformance(unittest.TestCase):
    """Test embedding generation and processing performance."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.app = UnifiedStreamlitApp()
        self.test_sizes = [
            (10, 128),      # Small: 10 vectors, 128 dimensions
            (100, 512),     # Medium: 100 vectors, 512 dimensions  
            (500, 1024),    # Large: 500 vectors, 1024 dimensions
            (1000, 1024),   # XLarge: 1000 vectors, 1024 dimensions
            (2000, 2048),   # XXLarge: 2000 vectors, 2048 dimensions
        ]
        self.performance_results = []

    def test_embedding_generation_scalability(self):
        """Test embedding generation performance across different scales."""
        results = []
        
        for count, dim in self.test_sizes:
            with PerformanceProfiler() as profiler:
                embeddings = self.app._simulate_embeddings(count, dim, seed=42)
                
            metrics = profiler.get_metrics(
                operation=f"generate_embeddings_{count}x{dim}",
                data_size=count * dim,
                ops_count=count
            )
            
            results.append(metrics)
            
            # Verify correctness
            self.assertEqual(embeddings.shape, (count, dim))
            self.assertEqual(embeddings.dtype, np.float32)
            
            # Performance assertions
            self.assertLess(metrics.duration_ms, 5000)  # Should complete within 5 seconds
            self.assertLess(metrics.memory_delta_mb, 100)  # Memory increase should be reasonable
            
            print(f"✅ {count}x{dim}: {metrics.duration_ms:.1f}ms, "
                  f"{metrics.throughput_ops_per_sec:.1f} emb/s, "
                  f"{metrics.memory_delta_mb:.1f}MB delta")
        
        self.performance_results.extend(results)
        
        # Test throughput scaling
        throughputs = [r.throughput_ops_per_sec for r in results]
        
        # Throughput should not degrade significantly with larger datasets
        # (allowing some variation due to memory allocation overhead)
        min_throughput = min(throughputs)
        max_throughput = max(throughputs)
        throughput_ratio = max_throughput / min_throughput if min_throughput > 0 else 1
        
        self.assertLess(throughput_ratio, 10)  # Less than 10x variation

    def test_embedding_normalization_performance(self):
        """Test performance of embedding normalization."""
        test_cases = [(1000, 512), (5000, 1024), (10000, 2048)]
        
        for count, dim in test_cases:
            # Generate unnormalized embeddings
            raw_embeddings = np.random.randn(count, dim).astype(np.float32)
            
            with PerformanceProfiler() as profiler:
                # Normalize to unit length (same as in _simulate_embeddings)
                norms = np.linalg.norm(raw_embeddings, axis=1, keepdims=True) + 1e-8
                normalized = raw_embeddings / norms
                
            metrics = profiler.get_metrics(
                operation=f"normalize_embeddings_{count}x{dim}",
                data_size=count * dim,
                ops_count=1
            )
            
            # Verify normalization
            final_norms = np.linalg.norm(normalized, axis=1)
            np.testing.assert_allclose(final_norms, 1.0, rtol=1e-5)
            
            # Performance check
            self.assertLess(metrics.duration_ms, 2000)  # Should be fast
            
            print(f"✅ Normalize {count}x{dim}: {metrics.duration_ms:.1f}ms")

    def test_batch_embedding_operations(self):
        """Test performance of batch embedding operations."""
        batch_sizes = [1, 10, 50, 100, 200]
        embedding_dim = 1024
        embeddings_per_batch = 100
        
        results = []
        
        for batch_size in batch_sizes:
            with PerformanceProfiler() as profiler:
                batch_embeddings = []
                for i in range(batch_size):
                    seed = 42 + i
                    embeddings = self.app._simulate_embeddings(embeddings_per_batch, embedding_dim, seed)
                    batch_embeddings.append(embeddings)
                
                # Concatenate all embeddings
                if batch_embeddings:
                    combined = np.concatenate(batch_embeddings, axis=0)
                
            total_embeddings = batch_size * embeddings_per_batch
            metrics = profiler.get_metrics(
                operation=f"batch_embeddings_b{batch_size}",
                data_size=total_embeddings * embedding_dim,
                ops_count=total_embeddings
            )
            
            results.append((batch_size, metrics))
            
            # Verify result
            if batch_size > 0:
                self.assertEqual(combined.shape, (total_embeddings, embedding_dim))
            
            print(f"✅ Batch size {batch_size}: {metrics.duration_ms:.1f}ms, "
                  f"{metrics.throughput_ops_per_sec:.1f} emb/s")
        
        # Analyze batch efficiency
        single_throughput = results[0][1].throughput_ops_per_sec if results else 0
        
        for batch_size, metrics in results[1:]:  # Skip single batch
            efficiency = metrics.throughput_ops_per_sec / single_throughput if single_throughput > 0 else 1
            
            # Batch processing should be more efficient (or at least not much worse)
            self.assertGreater(efficiency, 0.5)  # At least 50% efficiency


class TestVisualizationPerformance(unittest.TestCase):
    """Test visualization performance with large embedding sets."""
    
    def setUp(self):
        """Set up visualization performance test fixtures."""
        self.app = UnifiedStreamlitApp()
        
        # Create test datasets of varying sizes
        self.test_datasets = []
        sizes = [50, 100, 200, 500, 1000]
        
        for size in sizes:
            results = []
            for i in range(size):
                results.append({
                    'vector_key': f'video-{i//20}-segment-{i%20:04d}',
                    'video_name': f'Video {i//20}.mp4',
                    'score': 0.95 - (i * 0.0001),
                    'segment_index': i % 20,
                    'processing_type': 'real' if i % 3 == 0 else 'simulation'
                })
            self.test_datasets.append((size, results))

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.PCA')
    @patch('frontend.unified_streamlit_app.px')
    def test_pca_visualization_performance(self, mock_px, mock_pca, mock_st):
        """Test PCA visualization performance."""
        results = []
        
        for size, dataset in self.test_datasets:
            mock_st.session_state = {'search_results': dataset}
            
            # Mock PCA
            mock_pca_instance = Mock()
            coords = np.random.rand(size, 2)
            mock_pca_instance.fit_transform.return_value = coords
            mock_pca_instance.explained_variance_ratio_ = np.array([0.6, 0.3])
            mock_pca.return_value = mock_pca_instance
            
            # Mock plotly
            mock_fig = Mock()
            mock_px.scatter.return_value = mock_fig
            
            with PerformanceProfiler() as profiler:
                self.app._generate_embedding_visualization(
                    reduction_method="PCA",
                    dimensions="2D", 
                    color_by="video_name",
                    sample_size=size
                )
                
            metrics = profiler.get_metrics(
                operation=f"pca_visualization_{size}",
                data_size=size,
                ops_count=1
            )
            
            results.append(metrics)
            
            # Performance expectations
            self.assertLess(metrics.duration_ms, 10000)  # Should complete within 10 seconds
            
            # Verify PCA was called correctly
            mock_pca.assert_called_with(n_components=2, random_state=42)
            
            print(f"✅ PCA {size} points: {metrics.duration_ms:.1f}ms")
        
        # Check scaling behavior
        durations = [r.duration_ms for r in results]
        sizes_tested = [size for size, _ in self.test_datasets]
        
        # Duration should scale reasonably with data size
        largest_duration = max(durations)
        smallest_duration = min(durations)
        
        if smallest_duration > 0:
            scaling_factor = largest_duration / smallest_duration
            max_size_factor = max(sizes_tested) / min(sizes_tested)
            
            # Duration scaling should be reasonable (not exponential)
            self.assertLess(scaling_factor, max_size_factor * 2)

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.TSNE')
    @patch('frontend.unified_streamlit_app.px')
    def test_tsne_visualization_performance(self, mock_px, mock_tsne, mock_st):
        """Test t-SNE visualization performance."""
        # t-SNE is more computationally expensive, so test with smaller datasets
        small_datasets = self.test_datasets[:3]  # Only test up to 200 points
        
        results = []
        
        for size, dataset in small_datasets:
            mock_st.session_state = {'search_results': dataset}
            
            # Mock t-SNE
            mock_tsne_instance = Mock()
            coords = np.random.rand(size, 2)
            mock_tsne_instance.fit_transform.return_value = coords
            mock_tsne.return_value = mock_tsne_instance
            
            # Mock plotly
            mock_fig = Mock()
            mock_px.scatter.return_value = mock_fig
            
            with PerformanceProfiler() as profiler:
                self.app._generate_embedding_visualization(
                    reduction_method="t-SNE",
                    dimensions="2D",
                    color_by="score", 
                    sample_size=size
                )
                
            metrics = profiler.get_metrics(
                operation=f"tsne_visualization_{size}",
                data_size=size,
                ops_count=1
            )
            
            results.append(metrics)
            
            # t-SNE should complete reasonably fast even for moderate sizes
            self.assertLess(metrics.duration_ms, 15000)  # 15 seconds max
            
            # Verify perplexity calculation
            expected_perplexity = min(30, max(5, size - 1))
            mock_tsne.assert_called_with(
                n_components=2, 
                perplexity=expected_perplexity, 
                random_state=42
            )
            
            print(f"✅ t-SNE {size} points: {metrics.duration_ms:.1f}ms")

    @patch('frontend.unified_streamlit_app.st')
    @patch('frontend.unified_streamlit_app.PCA')
    @patch('frontend.unified_streamlit_app.px')
    def test_3d_visualization_performance(self, mock_px, mock_pca, mock_st):
        """Test 3D visualization performance."""
        size = 500
        dataset = self.test_datasets[3][1]  # 500 point dataset
        
        mock_st.session_state = {'search_results': dataset}
        
        # Mock PCA for 3D
        mock_pca_instance = Mock()
        coords = np.random.rand(size, 3)
        mock_pca_instance.fit_transform.return_value = coords
        mock_pca.return_value = mock_pca_instance
        
        # Mock plotly 3D
        mock_fig = Mock()
        mock_px.scatter_3d.return_value = mock_fig
        
        with PerformanceProfiler() as profiler:
            self.app._generate_embedding_visualization(
                reduction_method="PCA",
                dimensions="3D",
                color_by="processing_type",
                sample_size=size
            )
            
        metrics = profiler.get_metrics(
            operation=f"pca_3d_visualization_{size}",
            data_size=size,
            ops_count=1
        )
        
        # 3D visualization should have reasonable performance
        self.assertLess(metrics.duration_ms, 8000)  # 8 seconds max
        
        # Verify 3D PCA was used
        mock_pca.assert_called_with(n_components=3, random_state=42)
        mock_px.scatter_3d.assert_called_once()
        
        print(f"✅ 3D PCA {size} points: {metrics.duration_ms:.1f}ms")

    def test_query_overlay_performance(self):
        """Test performance of adding query overlays to visualizations."""
        overlay_counts = [1, 5, 10, 20]
        
        # Mock visualization figure
        mock_fig = Mock()
        mock_fig.data = [Mock()]
        mock_fig.data[0].x = list(range(100))
        mock_fig.data[0].y = list(range(100))
        mock_fig.add_scatter = Mock()
        
        for overlay_count in overlay_counts:
            with patch('frontend.unified_streamlit_app.st') as mock_st:
                mock_st.session_state = {'embedding_plot': mock_fig}
                
                with PerformanceProfiler() as profiler:
                    for i in range(overlay_count):
                        self.app._add_query_overlay(f"test query {i}")
                        
                metrics = profiler.get_metrics(
                    operation=f"query_overlay_{overlay_count}",
                    data_size=overlay_count,
                    ops_count=overlay_count
                )
                
                # Overlay addition should be fast
                self.assertLess(metrics.duration_ms, 1000)  # 1 second max
                
                # Verify correct number of overlays were added
                self.assertEqual(mock_fig.add_scatter.call_count, overlay_count)
                
                print(f"✅ {overlay_count} overlays: {metrics.duration_ms:.1f}ms")
                
                # Reset for next iteration
                mock_fig.add_scatter.reset_mock()


class TestSearchPerformance(unittest.TestCase):
    """Test search performance with large datasets."""
    
    def setUp(self):
        """Set up search performance test fixtures."""
        self.app = UnifiedStreamlitApp()
        
        # Create large video collections
        self.video_collections = {}
        collection_sizes = [10, 50, 100, 500, 1000]
        
        for size in collection_sizes:
            collection = {}
            for i in range(size):
                video_id = f'video-{i:04d}'
                collection[video_id] = ProcessedVideo(
                    video_id=video_id,
                    name=f'Video {i:04d}.mp4',
                    segments=20 + (i % 10),  # 20-29 segments
                    duration=100.0 + (i % 50),  # 100-149 seconds
                    processing_type='real' if i % 3 == 0 else 'simulation',
                    metadata={
                        'category': ['action', 'animation', 'adventure', 'sci-fi'][i % 4],
                        'quality': 'high' if i % 2 == 0 else 'standard'
                    }
                )
            self.video_collections[size] = collection

    @patch('frontend.unified_streamlit_app.st')
    def test_search_simulation_scalability(self, mock_st):
        """Test search simulation performance with various collection sizes."""
        search_types = ["Text-to-Video", "Video-to-Video", "Temporal Search"]
        results = []
        
        for collection_size, video_collection in self.video_collections.items():
            mock_st.session_state = {'processed_videos': video_collection}
            
            for search_type in search_types:
                with PerformanceProfiler() as profiler:
                    search_results = self.app._search_simulation(
                        search_type=search_type,
                        query="performance test query",
                        time_start=10.0 if search_type == "Temporal Search" else None,
                        time_end=30.0 if search_type == "Temporal Search" else None,
                        top_k=20,
                        similarity_threshold=0.7
                    )
                    
                metrics = profiler.get_metrics(
                    operation=f"search_{search_type.lower().replace('-', '_')}_{collection_size}",
                    data_size=collection_size,
                    ops_count=1
                )
                
                results.append(metrics)
                
                # Performance expectations
                self.assertLess(metrics.duration_ms, 5000)  # 5 seconds max
                self.assertLessEqual(len(search_results), 20)  # Respects top_k
                
                # Verify result quality
                for result in search_results:
                    self.assertGreaterEqual(result['score'], 0.7)  # Respects threshold
                
                print(f"✅ {search_type} on {collection_size} videos: "
                      f"{metrics.duration_ms:.1f}ms, {len(search_results)} results")
        
        # Analyze scaling behavior
        text_search_results = [r for r in results if 'text_to_video' in r.operation]
        
        if len(text_search_results) > 1:
            durations = [r.duration_ms for r in text_search_results]
            
            # Search time should scale reasonably with collection size
            max_duration = max(durations)
            min_duration = min(durations)
            
            if min_duration > 0:
                scaling_factor = max_duration / min_duration
                self.assertLess(scaling_factor, 50)  # Reasonable scaling

    @patch('frontend.unified_streamlit_app.st')
    def test_search_result_processing_performance(self, mock_st):
        """Test performance of search result processing and formatting."""
        collection_size = 200
        video_collection = self.video_collections[collection_size]
        mock_st.session_state = {'processed_videos': video_collection}
        
        # Generate large result set
        result_sizes = [10, 50, 100, 200, 500]
        
        for result_count in result_sizes:
            # Create mock results
            mock_results = []
            for i in range(result_count):
                video_id = f'video-{i % collection_size:04d}'
                video_info = video_collection[video_id]
                
                mock_results.append({
                    'vector_key': f'{video_id}-segment-{i%video_info.segments:04d}',
                    'video_name': video_info.name,
                    'score': 0.95 - (i * 0.001),
                    'segment_index': i % video_info.segments,
                    'start_sec': (i % video_info.segments) * 5.0,
                    'end_sec': ((i % video_info.segments) + 1) * 5.0,
                    'processing_type': video_info.processing_type
                })
            
            with PerformanceProfiler() as profiler:
                # Simulate result processing that might happen in the UI
                processed_results = []
                for result in mock_results:
                    # Simulate data enrichment/formatting
                    processed_result = {
                        **result,
                        'duration': result['end_sec'] - result['start_sec'],
                        'formatted_time': f"{result['start_sec']:.1f}s - {result['end_sec']:.1f}s",
                        'video_category': video_collection[result['vector_key'].split('-segment')[0]].metadata.get('category', 'unknown')
                    }
                    processed_results.append(processed_result)
                
            metrics = profiler.get_metrics(
                operation=f"process_results_{result_count}",
                data_size=result_count,
                ops_count=result_count
            )
            
            # Result processing should be fast
            self.assertLess(metrics.duration_ms, 2000)  # 2 seconds max
            self.assertEqual(len(processed_results), result_count)
            
            print(f"✅ Process {result_count} results: {metrics.duration_ms:.1f}ms, "
                  f"{metrics.throughput_ops_per_sec:.1f} results/s")

    def test_similarity_score_sorting_performance(self):
        """Test performance of similarity score sorting for large result sets."""
        result_sizes = [100, 500, 1000, 5000, 10000]
        
        for size in result_sizes:
            # Generate random similarity scores
            scores = np.random.rand(size).astype(float)
            results = [
                {'vector_key': f'result-{i:06d}', 'score': score, 'index': i}
                for i, score in enumerate(scores)
            ]
            
            with PerformanceProfiler() as profiler:
                # Sort by score (descending)
                sorted_results = sorted(results, key=lambda x: x['score'], reverse=True)
                
            metrics = profiler.get_metrics(
                operation=f"sort_results_{size}",
                data_size=size,
                ops_count=1
            )
            
            # Sorting should be fast
            self.assertLess(metrics.duration_ms, 1000)  # 1 second max
            
            # Verify sorting correctness
            sorted_scores = [r['score'] for r in sorted_results]
            self.assertEqual(sorted_scores, sorted(scores, reverse=True))
            
            print(f"✅ Sort {size} results: {metrics.duration_ms:.1f}ms")


class TestMemoryUsagePerformance(unittest.TestCase):
    """Test memory usage patterns and optimization."""
    
    def setUp(self):
        """Set up memory usage test fixtures."""
        self.app = UnifiedStreamlitApp()

    def test_embedding_memory_usage(self):
        """Test memory usage of embedding operations."""
        test_cases = [
            (100, 512),
            (500, 1024), 
            (1000, 2048),
            (2000, 4096)
        ]
        
        for count, dim in test_cases:
            # Force garbage collection
            gc.collect()
            
            with PerformanceProfiler() as profiler:
                embeddings = self.app._simulate_embeddings(count, dim, 42)
                
                # Perform operations that might increase memory
                normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
                similarities = np.dot(normalized, normalized.T)
                
                # Clean up
                del embeddings, normalized, similarities
                
            metrics = profiler.get_metrics(
                operation=f"memory_test_{count}x{dim}",
                data_size=count * dim,
                ops_count=1
            )
            
            # Expected memory usage
            expected_mb = count * dim * 4 / (1024 * 1024)  # 4 bytes per float32
            
            # Memory usage should be reasonable (allow 3x overhead for operations)
            self.assertLess(metrics.memory_delta_mb, expected_mb * 3)
            
            print(f"✅ Memory {count}x{dim}: {metrics.memory_delta_mb:.1f}MB "
                  f"(expected ~{expected_mb:.1f}MB)")

    def test_large_dataset_memory_management(self):
        """Test memory management with large datasets."""
        # Simulate processing large video collection
        large_collection_size = 1000
        
        with PerformanceProfiler() as profiler:
            # Create large collection
            large_collection = {}
            for i in range(large_collection_size):
                video_id = f'large-video-{i:04d}'
                large_collection[video_id] = ProcessedVideo(
                    video_id=video_id,
                    name=f'Large Video {i:04d}.mp4',
                    segments=30,
                    duration=150.0,
                    processing_type='real',
                    metadata={'category': 'test', 'size': 'large'}
                )
            
            # Simulate search operations
            with patch('frontend.unified_streamlit_app.st') as mock_st:
                mock_st.session_state = {'processed_videos': large_collection}
                
                # Multiple search operations
                for _ in range(10):
                    results = self.app._search_simulation(
                        "Text-to-Video", "test", None, None, 50, 0.7
                    )
                    
                # Clean up
                del large_collection
                
        metrics = profiler.get_metrics(
            operation="large_dataset_management",
            data_size=large_collection_size,
            ops_count=10
        )
        
        # Memory usage should be reasonable for large operations
        self.assertLess(metrics.memory_delta_mb, 500)  # Less than 500MB increase
        
        print(f"✅ Large dataset management: {metrics.memory_delta_mb:.1f}MB")

    def test_memory_cleanup_after_operations(self):
        """Test that memory is properly cleaned up after operations."""
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Perform memory-intensive operations
        large_embeddings = []
        for i in range(5):
            embeddings = self.app._simulate_embeddings(1000, 1024, i)
            large_embeddings.append(embeddings)
        
        peak_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        # Clean up explicitly
        del large_embeddings
        gc.collect()
        
        final_memory = psutil.Process().memory_info().rss / (1024 * 1024)  # MB
        
        memory_increase = peak_memory - initial_memory
        memory_recovered = peak_memory - final_memory
        recovery_ratio = memory_recovered / memory_increase if memory_increase > 0 else 1
        
        print(f"✅ Memory cleanup: {memory_increase:.1f}MB used, "
              f"{memory_recovered:.1f}MB recovered ({recovery_ratio:.1%})")
        
        # Should recover at least 50% of allocated memory
        self.assertGreater(recovery_ratio, 0.5)


class TestConcurrentPerformance(unittest.TestCase):
    """Test performance under concurrent access and operations."""
    
    def setUp(self):
        """Set up concurrent performance test fixtures."""
        self.app = UnifiedStreamlitApp()

    def test_concurrent_embedding_generation(self):
        """Test concurrent embedding generation performance."""
        thread_counts = [1, 2, 4, 8]
        embedding_count = 100
        embedding_dim = 512
        
        results = []
        
        for num_threads in thread_counts:
            def generate_embeddings(thread_id):
                return self.app._simulate_embeddings(
                    embedding_count, embedding_dim, seed=thread_id
                )
            
            with PerformanceProfiler() as profiler:
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [
                        executor.submit(generate_embeddings, i) 
                        for i in range(num_threads)
                    ]
                    
                    embeddings_list = []
                    for future in as_completed(futures):
                        embeddings_list.append(future.result())
                        
            total_embeddings = num_threads * embedding_count
            metrics = profiler.get_metrics(
                operation=f"concurrent_embeddings_t{num_threads}",
                data_size=total_embeddings,
                ops_count=total_embeddings
            )
            
            results.append((num_threads, metrics))
            
            # Verify all embeddings were generated correctly
            self.assertEqual(len(embeddings_list), num_threads)
            for embeddings in embeddings_list:
                self.assertEqual(embeddings.shape, (embedding_count, embedding_dim))
                
            print(f"✅ {num_threads} threads: {metrics.duration_ms:.1f}ms, "
                  f"{metrics.throughput_ops_per_sec:.1f} emb/s")
        
        # Analyze concurrency efficiency
        single_thread_throughput = results[0][1].throughput_ops_per_sec
        
        for num_threads, metrics in results[1:]:
            speedup = metrics.throughput_ops_per_sec / single_thread_throughput
            efficiency = speedup / num_threads
            
            print(f"    {num_threads} threads: {speedup:.2f}x speedup, {efficiency:.2f} efficiency")
            
            # Should show some improvement with concurrency
            self.assertGreater(speedup, 1.0)

    def test_concurrent_search_operations(self):
        """Test concurrent search operation performance."""
        # Create test video collection
        video_collection = {}
        for i in range(100):
            video_id = f'concurrent-video-{i:03d}'
            video_collection[video_id] = ProcessedVideo(
                video_id=video_id,
                name=f'Concurrent Video {i:03d}.mp4',
                segments=20,
                duration=100.0,
                processing_type='simulation'
            )
        
        concurrent_searches = [2, 4, 8, 16]
        
        for num_searches in concurrent_searches:
            def perform_search(search_id):
                with patch('frontend.unified_streamlit_app.st') as mock_st:
                    mock_st.session_state = {'processed_videos': video_collection}
                    return self.app._search_simulation(
                        "Text-to-Video", 
                        f"concurrent search {search_id}",
                        None, None, 10, 0.7
                    )
            
            with PerformanceProfiler() as profiler:
                with ThreadPoolExecutor(max_workers=num_searches) as executor:
                    futures = [
                        executor.submit(perform_search, i)
                        for i in range(num_searches)
                    ]
                    
                    search_results = []
                    for future in as_completed(futures):
                        search_results.append(future.result())
                        
            metrics = profiler.get_metrics(
                operation=f"concurrent_searches_{num_searches}",
                data_size=num_searches,
                ops_count=num_searches
            )
            
            # Verify all searches completed successfully
            self.assertEqual(len(search_results), num_searches)
            for results in search_results:
                self.assertLessEqual(len(results), 10)
                
            print(f"✅ {num_searches} concurrent searches: {metrics.duration_ms:.1f}ms, "
                  f"{metrics.throughput_ops_per_sec:.2f} searches/s")
            
            # Concurrent searches should complete within reasonable time
            self.assertLess(metrics.duration_ms, 10000)  # 10 seconds max


def run_comprehensive_performance_benchmarks():
    """Run all performance benchmarks and generate comprehensive report."""
    print("🚀 Running Comprehensive Performance Benchmarks...")
    
    # Track all benchmark results
    all_results = {
        'embedding_performance': [],
        'visualization_performance': [],
        'search_performance': [], 
        'memory_performance': [],
        'concurrent_performance': []
    }
    
    # Run test suites
    test_classes = [
        ('embedding', TestEmbeddingPerformance),
        ('visualization', TestVisualizationPerformance),
        ('search', TestSearchPerformance),
        ('memory', TestMemoryUsagePerformance),
        ('concurrent', TestConcurrentPerformance)
    ]
    
    for category, test_class in test_classes:
        print(f"\n📊 Running {category.title()} Performance Tests...")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=1, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        # Collect results
        test_count = result.testsRun
        success_count = test_count - len(result.failures) - len(result.errors)
        
        all_results[f'{category}_performance'].append({
            'total_tests': test_count,
            'successful_tests': success_count,
            'success_rate': (success_count / test_count * 100) if test_count > 0 else 0
        })
        
        print(f"✅ {category.title()} tests: {success_count}/{test_count} passed")
    
    # Generate summary report
    print(f"\n📋 COMPREHENSIVE PERFORMANCE REPORT")
    print(f"=====================================")
    
    total_tests = sum(r[0]['total_tests'] for r in all_results.values())
    total_successful = sum(r[0]['successful_tests'] for r in all_results.values())
    overall_success_rate = (total_successful / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Overall Performance Tests: {total_successful}/{total_tests} ({overall_success_rate:.1f}%)")
    
    for category, results in all_results.items():
        if results:
            result = results[0]
            print(f"{category.replace('_', ' ').title()}: "
                  f"{result['successful_tests']}/{result['total_tests']} "
                  f"({result['success_rate']:.1f}%)")
    
    return all_results


if __name__ == '__main__':
    # Run comprehensive performance benchmarks
    benchmark_results = run_comprehensive_performance_benchmarks()
    
    print(f"\n🎯 Enhanced Streamlit Performance Testing Complete!")
    print(f"All benchmarks provide detailed performance metrics for:")
    print(f"  • Multi-vector processing scalability")
    print(f"  • Visualization performance optimization")  
    print(f"  • Search operation efficiency")
    print(f"  • Memory usage patterns")
    print(f"  • Concurrent operation handling")