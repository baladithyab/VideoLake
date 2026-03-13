"""
Unit tests for BenchmarkRunner and Bench markOrchestrator
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.benchmarks.benchmark_config import (
    BenchmarkConfig,
    BenchmarkResult,
    BackendVariant,
    BenchmarkDimension,
    DimensionResult,
    DatasetConfig,
    QUICK_CONFIG,
)
from src.benchmarks.benchmark_runner import (
    BenchmarkRunner,
    BenchmarkOrchestrator,
)
from src.services.benchmark_dimensions import (
    ComprehensiveBenchmarkResults,
    LatencyMetrics,
    ThroughputMetrics,
)


@pytest.fixture
def simple_config():
    """Simple benchmark config for testing"""
    return BenchmarkConfig(
        backends=[BackendVariant.S3VECTOR_SERVERLESS],
        dataset=DatasetConfig(
            name="test",
            vector_count=100,
            dimensions=128,
        ),
        query_count=10,
        throughput_duration_seconds=5,
        enabled_dimensions=[
            BenchmarkDimension.LATENCY,
            BenchmarkDimension.THROUGHPUT,
        ],
        output_dir="./test_results",
    )


@pytest.fixture
def mock_adapter():
    """Mock backend adapter"""
    adapter = Mock()
    adapter.backend_name = "s3vector-serverless"
    adapter.health_check = Mock(return_value=True)
    adapter.search_vectors = Mock(return_value=[{"id": 1, "score": 0.95}])
    adapter.index_vectors = Mock(return_value={"success": True})
    adapter.get_endpoint_info = Mock(return_value={"endpoint": "mock://test"})
    return adapter


@pytest.fixture
def mock_comprehensive_results():
    """Mock ComprehensiveBenchmarkResults"""
    results = ComprehensiveBenchmarkResults(
        backend="s3vector-serverless",
        timestamp=datetime.utcnow(),
    )
    results.latency = LatencyMetrics(
        p50_ms=10.5,
        p95_ms=15.2,
        p99_ms=20.1,
        p999_ms=25.0,
        min_ms=5.0,
        max_ms=30.0,
        mean_ms=11.0,
        std_ms=3.5,
        samples=100,
    )
    results.throughput = ThroughputMetrics(
        qps=150.0,
        duration_seconds=60.0,
        total_queries=9000,
        successful_queries=8950,
        failed_queries=50,
        error_rate=0.0056,
    )
    return results


class TestBenchmarkRunner:
    """Tests for BenchmarkRunner"""

    def test_init(self, simple_config):
        """Test runner initialization"""
        runner = BenchmarkRunner(simple_config)
        assert runner.config == simple_config
        assert runner.results is None

    def test_get_backend_adapter_mock(self, simple_config, mock_adapter):
        """Test adapter retrieval with mock"""
        runner = BenchmarkRunner(simple_config)

        with patch('scripts.backend_adapters.get_backend_adapter', return_value=mock_adapter):
            adapter = runner.get_backend_adapter(BackendVariant.S3VECTOR_SERVERLESS)
            assert adapter == mock_adapter
            assert adapter.backend_name == "s3vector-serverless"

    def test_convert_dimension_results_latency(self, simple_config, mock_comprehensive_results):
        """Test conversion of latency dimension results"""
        runner = BenchmarkRunner(simple_config)

        dimension_results = runner.convert_dimension_results(
            mock_comprehensive_results,
            [BenchmarkDimension.LATENCY]
        )

        assert BenchmarkDimension.LATENCY in dimension_results
        lat_result = dimension_results[BenchmarkDimension.LATENCY]
        assert lat_result.dimension == BenchmarkDimension.LATENCY
        assert lat_result.value == 10.5  # p50_ms
        assert lat_result.unit == "ms"
        assert lat_result.success is True
        assert 'p99_ms' in lat_result.metadata
        assert lat_result.metadata['p99_ms'] == 20.1

    def test_convert_dimension_results_throughput(self, simple_config, mock_comprehensive_results):
        """Test conversion of throughput dimension results"""
        runner = BenchmarkRunner(simple_config)

        dimension_results = runner.convert_dimension_results(
            mock_comprehensive_results,
            [BenchmarkDimension.THROUGHPUT]
        )

        assert BenchmarkDimension.THROUGHPUT in dimension_results
        thr_result = dimension_results[BenchmarkDimension.THROUGHPUT]
        assert thr_result.dimension == BenchmarkDimension.THROUGHPUT
        assert thr_result.value == 150.0  # qps
        assert thr_result.unit == "QPS"
        assert thr_result.metadata['successful_queries'] == 8950

    @pytest.mark.asyncio
    async def test_run_backend_success(self, simple_config, mock_adapter, mock_comprehensive_results):
        """Test successful backend benchmark run"""
        runner = BenchmarkRunner(simple_config)

        # Mock the adapter and dimensions runner
        with patch.object(runner, 'get_backend_adapter', return_value=mock_adapter):
            with patch('src.benchmarks.benchmark_runner.BenchmarkDimensionsRunner') as mock_dims_runner_class:
                # Setup mock dimensions runner
                mock_dims_runner = Mock()
                mock_dims_runner.run_comprehensive_benchmark = AsyncMock(return_value=mock_comprehensive_results)
                mock_dims_runner_class.return_value = mock_dims_runner

                # Run benchmark
                result = await runner.run(BackendVariant.S3VECTOR_SERVERLESS)

                # Assertions
                assert result is not None
                assert result.backend == BackendVariant.S3VECTOR_SERVERLESS
                assert result.success is True
                assert result.latency is not None
                assert result.throughput is not None
                assert result.latency.value == 10.5

    @pytest.mark.asyncio
    async def test_run_backend_unhealthy(self, simple_config, mock_adapter):
        """Test benchmark run with unhealthy backend"""
        runner = BenchmarkRunner(simple_config)

        # Make adapter unhealthy
        mock_adapter.health_check = Mock(return_value=False)

        with patch.object(runner, 'get_backend_adapter', return_value=mock_adapter):
            result = await runner.run(BackendVariant.S3VECTOR_SERVERLESS)

            # Should fail with error
            assert result.success is False
            assert result.error_message is not None
            assert "not accessible" in result.error_message

    @pytest.mark.asyncio
    async def test_run_backend_with_exception(self, simple_config, mock_adapter):
        """Test benchmark run with exception during execution"""
        runner = BenchmarkRunner(simple_config)

        with patch.object(runner, 'get_backend_adapter', return_value=mock_adapter):
            with patch('src.benchmarks.benchmark_runner.BenchmarkDimensionsRunner') as mock_dims_runner_class:
                # Make dimensions runner raise exception
                mock_dims_runner = Mock()
                mock_dims_runner.run_comprehensive_benchmark = AsyncMock(
                    side_effect=RuntimeError("Test error")
                )
                mock_dims_runner_class.return_value = mock_dims_runner

                result = await runner.run(BackendVariant.S3VECTOR_SERVERLESS)

                # Should fail gracefully
                assert result.success is False
                assert "Test error" in result.error_message


class TestBenchmarkOrchestrator:
    """Tests for BenchmarkOrchestrator"""

    def test_init(self, simple_config, tmp_path):
        """Test orchestrator initialization"""
        config = simple_config
        config.output_dir = str(tmp_path)

        orchestrator = BenchmarkOrchestrator(config)
        assert orchestrator.config == config
        assert len(orchestrator.results) == 0
        assert orchestrator.output_dir.exists()

    @pytest.mark.asyncio
    async def test_run_all_single_backend(self, simple_config, mock_adapter, mock_comprehensive_results, tmp_path):
        """Test running benchmarks for a single backend"""
        simple_config.output_dir = str(tmp_path)
        orchestrator = BenchmarkOrchestrator(simple_config)

        # Mock the runner
        with patch('src.benchmarks.benchmark_runner.BenchmarkRunner') as mock_runner_class:
            mock_runner = Mock()

            # Create a proper BenchmarkResult
            mock_result = BenchmarkResult(
                backend=BackendVariant.S3VECTOR_SERVERLESS,
                timestamp=datetime.utcnow(),
                dataset=simple_config.dataset,
                success=True,
            )
            mock_result.latency = DimensionResult(
                dimension=BenchmarkDimension.LATENCY,
                value=10.5,
                unit="ms",
                metadata={'p50_ms': 10.5, 'p99_ms': 20.1},
                success=True,
            )

            mock_runner.run = AsyncMock(return_value=mock_result)
            mock_runner_class.return_value = mock_runner

            # Run all benchmarks
            results = await orchestrator.run_all()

            # Assertions
            assert len(results) == 1
            assert BackendVariant.S3VECTOR_SERVERLESS in results
            assert results[BackendVariant.S3VECTOR_SERVERLESS].success is True

    @pytest.mark.asyncio
    async def test_run_all_multiple_backends(self, tmp_path):
        """Test running benchmarks for multiple backends"""
        config = BenchmarkConfig(
            backends=[
                BackendVariant.S3VECTOR_SERVERLESS,
                BackendVariant.LANCEDB_EBS,
            ],
            dataset=DatasetConfig(name="test", vector_count=100, dimensions=128),
            enabled_dimensions=[BenchmarkDimension.LATENCY],
            output_dir=str(tmp_path),
            save_raw_results=False,
            generate_report=False,
        )

        orchestrator = BenchmarkOrchestrator(config)

        with patch('src.benchmarks.benchmark_runner.BenchmarkRunner') as mock_runner_class:
            # Create mock results for each backend
            def create_mock_runner(*args, **kwargs):
                mock_runner = Mock()

                async def mock_run(backend, progress_callback=None):
                    return BenchmarkResult(
                        backend=backend,
                        timestamp=datetime.utcnow(),
                        dataset=config.dataset,
                        success=True,
                    )

                mock_runner.run = mock_run
                return mock_runner

            mock_runner_class.side_effect = create_mock_runner

            results = await orchestrator.run_all()

            # Should have results for both backends
            assert len(results) == 2
            assert BackendVariant.S3VECTOR_SERVERLESS in results
            assert BackendVariant.LANCEDB_EBS in results

    def test_generate_comparison_report_empty(self, simple_config):
        """Test report generation with no results"""
        orchestrator = BenchmarkOrchestrator(simple_config)

        report = orchestrator.generate_comparison_report()
        assert "No benchmark results available" in report

    def test_generate_comparison_report_with_results(self, simple_config):
        """Test report generation with results"""
        orchestrator = BenchmarkOrchestrator(simple_config)

        # Add mock result
        result = BenchmarkResult(
            backend=BackendVariant.S3VECTOR_SERVERLESS,
            timestamp=datetime.utcnow(),
            dataset=simple_config.dataset,
            success=True,
        )
        result.latency = DimensionResult(
            dimension=BenchmarkDimension.LATENCY,
            value=10.5,
            unit="ms",
            metadata={'p50_ms': 10.5, 'p99_ms': 20.1, 'mean_ms': 11.0, 'std_ms': 3.5, 'samples': 100},
            success=True,
        )
        result.throughput = DimensionResult(
            dimension=BenchmarkDimension.THROUGHPUT,
            value=150.0,
            unit="QPS",
            metadata={},
            success=True,
        )

        orchestrator.results[BackendVariant.S3VECTOR_SERVERLESS] = result

        report = orchestrator.generate_comparison_report()

        # Check report contains expected sections
        assert "# Benchmark Comparison Report" in report
        assert "Performance Comparison" in report
        assert "s3vector-serverless" in report
        assert "10.5" in report  # latency value
        assert "150" in report  # throughput value

    @pytest.mark.asyncio
    async def test_run_all_with_timeout(self, tmp_path):
        """Test that timeouts are handled correctly"""
        config = BenchmarkConfig(
            backends=[BackendVariant.S3VECTOR_SERVERLESS],
            dataset=DatasetConfig(name="test", vector_count=100, dimensions=128),
            enabled_dimensions=[BenchmarkDimension.LATENCY],
            output_dir=str(tmp_path),
            timeout_seconds=1,  # Very short timeout
            save_raw_results=False,
            generate_report=False,
        )

        orchestrator = BenchmarkOrchestrator(config)

        with patch('src.benchmarks.benchmark_runner.BenchmarkRunner') as mock_runner_class:
            mock_runner = Mock()

            # Make run take too long
            async def slow_run(backend, progress_callback=None):
                await asyncio.sleep(10)  # Longer than timeout
                return BenchmarkResult(
                    backend=backend,
                    timestamp=datetime.utcnow(),
                    dataset=config.dataset,
                    success=True,
                )

            mock_runner.run = slow_run
            mock_runner_class.return_value = mock_runner

            results = await orchestrator.run_all()

            # Should have a result indicating timeout
            assert len(results) == 1
            result = results[BackendVariant.S3VECTOR_SERVERLESS]
            assert result.success is False
            assert "Timeout" in result.error_message


class TestBenchmarkConfig:
    """Tests for BenchmarkConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = BenchmarkConfig()

        assert config.dataset.vector_count == 10000
        assert config.dataset.dimensions == 1024
        assert len(config.enabled_dimensions) == 10  # All dimensions
        assert config.run_id is not None

    def test_quick_config(self):
        """Test QUICK_CONFIG preset"""
        assert len(QUICK_CONFIG.backends) == 3
        assert QUICK_CONFIG.dataset.vector_count == 1000
        assert len(QUICK_CONFIG.enabled_dimensions) == 3

    def test_tier_filters(self):
        """Test tier filtering methods"""
        config = BenchmarkConfig(
            backends=[
                BackendVariant.S3VECTOR_SERVERLESS,  # Tier 1
                BackendVariant.QDRANT_CLOUD,  # Tier 2
                BackendVariant.FAISS_LAMBDA,  # Tier 3
            ]
        )

        tier_1 = config.get_tier_1_backends()
        assert len(tier_1) == 1
        assert BackendVariant.S3VECTOR_SERVERLESS in tier_1

        tier_2 = config.get_tier_2_backends()
        assert len(tier_2) == 1
        assert BackendVariant.QDRANT_CLOUD in tier_2

        tier_3 = config.get_tier_3_backends()
        assert len(tier_3) == 1
        assert BackendVariant.FAISS_LAMBDA in tier_3


class TestBenchmarkResult:
    """Tests for BenchmarkResult"""

    def test_get_set_dimension_result(self):
        """Test getting and setting dimension results"""
        result = BenchmarkResult(
            backend=BackendVariant.S3VECTOR_SERVERLESS,
            timestamp=datetime.utcnow(),
            dataset=DatasetConfig(name="test", vector_count=100, dimensions=128),
        )

        # Set latency result
        lat_result = DimensionResult(
            dimension=BenchmarkDimension.LATENCY,
            value=10.5,
            unit="ms",
            metadata={'p50_ms': 10.5},
            success=True,
        )
        result.set_dimension_result(lat_result)

        # Get latency result
        retrieved = result.get_dimension_result(BenchmarkDimension.LATENCY)
        assert retrieved == lat_result
        assert retrieved.value == 10.5

    def test_to_dict(self):
        """Test conversion to dictionary"""
        result = BenchmarkResult(
            backend=BackendVariant.S3VECTOR_SERVERLESS,
            timestamp=datetime.utcnow(),
            dataset=DatasetConfig(name="test", vector_count=100, dimensions=128),
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict['backend'] == 's3vector-serverless'
        assert 'timestamp' in result_dict
        assert result_dict['dataset']['vector_count'] == 100
        assert result_dict['success'] is True

    def test_get_summary(self):
        """Test summary generation"""
        result = BenchmarkResult(
            backend=BackendVariant.S3VECTOR_SERVERLESS,
            timestamp=datetime.utcnow(),
            dataset=DatasetConfig(name="test", vector_count=100, dimensions=128),
        )

        result.latency = DimensionResult(
            dimension=BenchmarkDimension.LATENCY,
            value=10.5,
            unit="ms",
            metadata={'p50_ms': 10.5, 'p99_ms': 20.1},
            success=True,
        )

        summary = result.get_summary()

        assert summary['backend'] == 's3vector-serverless'
        assert summary['latency_p50_ms'] == 10.5
        assert summary['latency_p99_ms'] == 20.1
