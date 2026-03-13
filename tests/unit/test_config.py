#!/usr/bin/env python3
"""
Test Configuration and Utilities for Enhanced Streamlit Testing

Provides:
- Test configuration management
- Common test utilities and helpers
- Test environment setup/teardown
- Mock service factories
- Test result aggregation
- Reporting utilities
"""

import os
import sys
import unittest
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Callable
from unittest.mock import Mock, patch, MagicMock
import json
import time
from dataclasses import dataclass, asdict
from contextlib import contextmanager

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))


@dataclass
class TestConfig:
    """Test configuration settings."""
    # Environment settings
    test_env: str = "test"
    debug_mode: bool = False
    verbose_output: bool = True
    
    # Performance settings
    performance_timeout_sec: int = 30
    memory_limit_mb: int = 1000
    concurrent_test_limit: int = 10
    
    # Security settings
    enable_security_tests: bool = True
    test_malicious_inputs: bool = True
    validate_sanitization: bool = True
    
    # Mock settings
    use_real_aws: bool = False
    mock_external_apis: bool = True
    simulate_network_delays: bool = False
    
    # Output settings
    generate_html_report: bool = True
    save_performance_metrics: bool = True
    export_test_data: bool = False
    
    # File paths
    test_data_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    temp_dir: Optional[Path] = None
    
    def __post_init__(self):
        """Initialize derived paths."""
        if self.test_data_dir is None:
            self.test_data_dir = Path(__file__).parent / "fixtures"
        
        if self.output_dir is None:
            self.output_dir = Path(__file__).parent / "output"
        
        if self.temp_dir is None:
            self.temp_dir = Path(tempfile.gettempdir()) / "streamlit_tests"
        
        # Create directories
        self.test_data_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)


@dataclass
class TestResult:
    """Container for individual test results."""
    test_name: str
    test_class: str
    status: str  # "passed", "failed", "error", "skipped"
    duration_ms: float
    error_message: Optional[str] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    memory_usage_mb: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestSuiteResult:
    """Container for test suite results."""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    total_duration_ms: float
    individual_results: List[TestResult]
    
    @property
    def success_rate(self) -> float:
        return (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'success_rate': self.success_rate,
            'individual_results': [r.to_dict() for r in self.individual_results]
        }


class TestEnvironment:
    """Manages test environment setup and cleanup."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.temp_files: List[Path] = []
        self.mock_patches: List[Any] = []
        self.original_env = dict(os.environ)
        
    def setup(self):
        """Set up test environment."""
        # Set environment variables
        os.environ.update({
            'TESTING': 'true',
            'LOG_LEVEL': 'DEBUG' if self.config.debug_mode else 'INFO',
            'AWS_DEFAULT_REGION': 'us-east-1',
            'DISABLE_SSL_VALIDATION': 'true'
        })
        
        # Configure logging
        log_level = logging.DEBUG if self.config.debug_mode else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.config.output_dir / 'test.log')
            ]
        )
        
        # Create temp directories
        self.config.temp_dir.mkdir(exist_ok=True)
        
        # Set up mocks if configured
        if self.config.mock_external_apis:
            self._setup_api_mocks()
    
    def teardown(self):
        """Clean up test environment."""
        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    if temp_file.is_file():
                        temp_file.unlink()
                    else:
                        shutil.rmtree(temp_file)
            except Exception as e:
                logging.warning(f"Failed to clean up {temp_file}: {e}")
        
        # Stop all mock patches
        for mock_patch in self.mock_patches:
            try:
                mock_patch.stop()
            except Exception as e:
                logging.warning(f"Failed to stop mock patch: {e}")
        
        # Restore environment
        os.environ.clear()
        os.environ.update(self.original_env)
        
        # Clean up temp directory
        try:
            if self.config.temp_dir.exists():
                shutil.rmtree(self.config.temp_dir)
        except Exception as e:
            logging.warning(f"Failed to clean up temp dir: {e}")
    
    def _setup_api_mocks(self):
        """Set up API mocks."""
        # Mock AWS services
        aws_mock = patch('boto3.client')
        aws_mock.start()
        self.mock_patches.append(aws_mock)
        
        # Mock requests for external APIs
        requests_mock = patch('requests.get')
        requests_mock.start()
        self.mock_patches.append(requests_mock)
        
    def create_temp_file(self, suffix: str = '.tmp', content: str = '') -> Path:
        """Create a temporary file."""
        temp_file = self.config.temp_dir / f"temp_{int(time.time())}_{len(self.temp_files)}{suffix}"
        temp_file.write_text(content)
        self.temp_files.append(temp_file)
        return temp_file
    
    def create_temp_dir(self, name: str = '') -> Path:
        """Create a temporary directory."""
        if not name:
            name = f"temp_dir_{int(time.time())}_{len(self.temp_files)}"
        temp_dir = self.config.temp_dir / name
        temp_dir.mkdir(exist_ok=True)
        self.temp_files.append(temp_dir)
        return temp_dir


class MockServiceFactory:
    """Factory for creating mock services."""
    
    @staticmethod
    def create_mock_streamlit():
        """Create mock Streamlit module."""
        mock_st = Mock()
        
        # Mock session state
        mock_st.session_state = {}
        
        # Mock UI components
        mock_st.title = Mock()
        mock_st.header = Mock()
        mock_st.subheader = Mock()
        mock_st.text = Mock()
        mock_st.markdown = Mock()
        mock_st.info = Mock()
        mock_st.success = Mock()
        mock_st.warning = Mock()
        mock_st.error = Mock()
        mock_st.exception = Mock()
        
        # Mock input components
        mock_st.text_input = Mock(return_value="")
        mock_st.text_area = Mock(return_value="")
        mock_st.number_input = Mock(return_value=0)
        mock_st.slider = Mock(return_value=0)
        mock_st.selectbox = Mock(return_value=None)
        mock_st.multiselect = Mock(return_value=[])
        mock_st.checkbox = Mock(return_value=False)
        mock_st.radio = Mock(return_value=None)
        mock_st.button = Mock(return_value=False)
        mock_st.file_uploader = Mock(return_value=None)
        
        # Mock layout components
        mock_st.columns = Mock(return_value=[Mock() for _ in range(3)])
        mock_st.tabs = Mock(return_value=[Mock() for _ in range(3)])
        mock_st.sidebar = Mock()
        mock_st.container = Mock()
        mock_st.expander = Mock()
        
        # Mock data display
        mock_st.dataframe = Mock()
        mock_st.table = Mock()
        mock_st.json = Mock()
        mock_st.metric = Mock()
        
        # Mock progress and status
        mock_st.progress = Mock()
        mock_st.spinner = Mock()
        mock_st.empty = Mock()
        mock_st.placeholder = Mock()
        
        # Mock media
        mock_st.image = Mock()
        mock_st.audio = Mock()
        mock_st.video = Mock()
        
        # Mock special functions
        mock_st.rerun = Mock()
        mock_st.stop = Mock()
        mock_st.balloons = Mock()
        mock_st.snow = Mock()
        
        # Mock configuration
        mock_st.set_page_config = Mock()
        
        # Mock plotly chart
        mock_st.plotly_chart = Mock()
        
        return mock_st
    
    @staticmethod
    def create_mock_aws_client(service_name: str):
        """Create mock AWS client."""
        mock_client = Mock()
        
        if service_name == 's3':
            mock_client.list_objects_v2 = Mock(return_value={
                'Contents': [],
                'IsTruncated': False
            })
            mock_client.get_object = Mock()
            mock_client.put_object = Mock()
            mock_client.delete_object = Mock()
            mock_client.create_bucket = Mock()
        
        elif service_name == 'opensearch':
            mock_client.search = Mock(return_value={
                'hits': {'hits': [], 'total': {'value': 0}}
            })
            mock_client.index = Mock()
            mock_client.delete = Mock()
        
        return mock_client
    
    @staticmethod
    def create_mock_video_processing_service():
        """Create mock video processing service."""
        mock_service = Mock()
        
        # Mock processing result
        mock_result = Mock()
        mock_result.video_duration_sec = 120.0
        mock_result.total_segments = 24
        mock_result.segments = []
        mock_result.metadata = {}
        
        mock_service.process_video_sync = Mock(return_value=mock_result)
        mock_service.process_video_async = Mock(return_value="task-123")
        mock_service.get_task_status = Mock(return_value={"status": "completed"})
        
        return mock_service
    
    @staticmethod
    def create_mock_search_engine():
        """Create mock search engine."""
        mock_engine = Mock()
        
        # Mock search response
        mock_response = Mock()
        mock_response.results = []
        mock_response.total_results = 0
        mock_response.query_id = "query-123"
        
        mock_engine.search_by_text_query = Mock(return_value=mock_response)
        mock_engine.search_video_scenes = Mock(return_value=mock_response)
        mock_engine.find_similar_content = Mock(return_value=mock_response)
        
        return mock_engine


class TestRunner:
    """Custom test runner with enhanced reporting."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestSuiteResult] = []
    
    def run_test_suite(self, test_suite: unittest.TestSuite, suite_name: str) -> TestSuiteResult:
        """Run a test suite and collect detailed results."""
        start_time = time.time()
        individual_results = []
        
        # Custom result class to capture individual test results
        class DetailedTestResult(unittest.TestResult):
            def __init__(self):
                super().__init__()
                self.test_results = individual_results
            
            def startTest(self, test):
                super().startTest(test)
                self.test_start_time = time.time()
            
            def stopTest(self, test):
                super().stopTest(test)
                duration = (time.time() - self.test_start_time) * 1000  # ms
                
                # Determine status
                if test in [f[0] for f in self.failures]:
                    status = "failed"
                    error_msg = next(f[1] for f in self.failures if f[0] == test)
                elif test in [e[0] for e in self.errors]:
                    status = "error"
                    error_msg = next(e[1] for e in self.errors if e[0] == test)
                elif test in self.skipped:
                    status = "skipped"
                    error_msg = None
                else:
                    status = "passed"
                    error_msg = None
                
                result = TestResult(
                    test_name=test._testMethodName,
                    test_class=test.__class__.__name__,
                    status=status,
                    duration_ms=duration,
                    error_message=error_msg
                )
                
                self.test_results.append(result)
        
        # Run the test suite
        result = DetailedTestResult()
        test_suite.run(result)
        
        total_duration = (time.time() - start_time) * 1000  # ms
        
        suite_result = TestSuiteResult(
            suite_name=suite_name,
            total_tests=result.testsRun,
            passed_tests=result.testsRun - len(result.failures) - len(result.errors),
            failed_tests=len(result.failures),
            error_tests=len(result.errors),
            skipped_tests=len(result.skipped),
            total_duration_ms=total_duration,
            individual_results=individual_results
        )
        
        self.results.append(suite_result)
        return suite_result
    
    def run_test_class(self, test_class: Type[unittest.TestCase]) -> TestSuiteResult:
        """Run all tests in a test class."""
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        return self.run_test_suite(suite, test_class.__name__)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        if not self.results:
            return {"error": "No test results available"}
        
        # Aggregate statistics
        total_tests = sum(r.total_tests for r in self.results)
        total_passed = sum(r.passed_tests for r in self.results)
        total_failed = sum(r.failed_tests for r in self.results)
        total_errors = sum(r.error_tests for r in self.results)
        total_skipped = sum(r.skipped_tests for r in self.results)
        total_duration = sum(r.total_duration_ms for r in self.results)
        
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        
        report = {
            "summary": {
                "total_test_suites": len(self.results),
                "total_tests": total_tests,
                "passed_tests": total_passed,
                "failed_tests": total_failed,
                "error_tests": total_errors,
                "skipped_tests": total_skipped,
                "success_rate": overall_success_rate,
                "total_duration_ms": total_duration,
                "average_test_duration_ms": total_duration / total_tests if total_tests > 0 else 0
            },
            "test_suites": [r.to_dict() for r in self.results],
            "failed_tests": [],
            "performance_summary": {
                "fastest_test": None,
                "slowest_test": None,
                "average_duration_ms": 0
            }
        }
        
        # Collect failed tests and performance data
        all_individual_results = []
        for suite_result in self.results:
            all_individual_results.extend(suite_result.individual_results)
        
        failed_tests = [r for r in all_individual_results if r.status in ["failed", "error"]]
        report["failed_tests"] = [r.to_dict() for r in failed_tests]
        
        if all_individual_results:
            durations = [r.duration_ms for r in all_individual_results]
            fastest = min(all_individual_results, key=lambda x: x.duration_ms)
            slowest = max(all_individual_results, key=lambda x: x.duration_ms)
            
            report["performance_summary"] = {
                "fastest_test": f"{fastest.test_class}.{fastest.test_name} ({fastest.duration_ms:.1f}ms)",
                "slowest_test": f"{slowest.test_class}.{slowest.test_name} ({slowest.duration_ms:.1f}ms)",
                "average_duration_ms": sum(durations) / len(durations)
            }
        
        # Save report if configured
        if self.config.generate_html_report:
            self._save_html_report(report)
        
        return report
    
    def _save_html_report(self, report: Dict[str, Any]):
        """Save HTML report."""
        html_template = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Enhanced Streamlit Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                .success { color: #28a745; }
                .failure { color: #dc3545; }
                .warning { color: #ffc107; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .progress-bar { width: 100%; height: 20px; background: #f0f0f0; border-radius: 10px; overflow: hidden; }
                .progress-fill { height: 100%; background: #28a745; transition: width 0.3s ease; }
            </style>
        </head>
        <body>
            <h1>Enhanced Streamlit Test Report</h1>
            
            <div class="summary">
                <h2>Test Summary</h2>
                <p><strong>Success Rate:</strong> <span class="{success_class}">{success_rate:.1f}%</span></p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {success_rate:.1f}%;"></div>
                </div>
                <p><strong>Total Tests:</strong> {total_tests}</p>
                <p><strong>Passed:</strong> <span class="success">{passed_tests}</span></p>
                <p><strong>Failed:</strong> <span class="failure">{failed_tests}</span></p>
                <p><strong>Errors:</strong> <span class="failure">{error_tests}</span></p>
                <p><strong>Skipped:</strong> <span class="warning">{skipped_tests}</span></p>
                <p><strong>Total Duration:</strong> {total_duration:.1f}ms</p>
            </div>
            
            <h2>Test Suite Results</h2>
            <table>
                <tr>
                    <th>Test Suite</th>
                    <th>Tests</th>
                    <th>Passed</th>
                    <th>Failed</th>
                    <th>Success Rate</th>
                    <th>Duration</th>
                </tr>
                {suite_rows}
            </table>
            
            <h2>Performance Summary</h2>
            <p><strong>Fastest Test:</strong> {fastest_test}</p>
            <p><strong>Slowest Test:</strong> {slowest_test}</p>
            <p><strong>Average Duration:</strong> {avg_duration:.1f}ms</p>
            
            {failed_section}
        </body>
        </html>
        '''
        
        # Generate suite rows
        suite_rows = ""
        for suite in report["test_suites"]:
            success_class = "success" if suite["success_rate"] >= 90 else "failure" if suite["success_rate"] < 70 else "warning"
            suite_rows += f'''
            <tr>
                <td>{suite["suite_name"]}</td>
                <td>{suite["total_tests"]}</td>
                <td class="success">{suite["passed_tests"]}</td>
                <td class="failure">{suite["failed_tests"] + suite["error_tests"]}</td>
                <td class="{success_class}">{suite["success_rate"]:.1f}%</td>
                <td>{suite["total_duration_ms"]:.1f}ms</td>
            </tr>
            '''
        
        # Generate failed tests section
        failed_section = ""
        if report["failed_tests"]:
            failed_section = '''
            <h2>Failed Tests</h2>
            <table>
                <tr>
                    <th>Test</th>
                    <th>Class</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Error</th>
                </tr>
            '''
            for test in report["failed_tests"]:
                error_msg = test.get("error_message", "")[:100] + "..." if test.get("error_message") and len(test.get("error_message", "")) > 100 else test.get("error_message", "")
                failed_section += f'''
                <tr>
                    <td>{test["test_name"]}</td>
                    <td>{test["test_class"]}</td>
                    <td class="failure">{test["status"]}</td>
                    <td>{test["duration_ms"]:.1f}ms</td>
                    <td>{error_msg}</td>
                </tr>
                '''
            failed_section += "</table>"
        
        # Format HTML
        success_class = "success" if report["summary"]["success_rate"] >= 90 else "failure" if report["summary"]["success_rate"] < 70 else "warning"
        
        html_content = html_template.format(
            success_class=success_class,
            success_rate=report["summary"]["success_rate"],
            total_tests=report["summary"]["total_tests"],
            passed_tests=report["summary"]["passed_tests"],
            failed_tests=report["summary"]["failed_tests"],
            error_tests=report["summary"]["error_tests"],
            skipped_tests=report["summary"]["skipped_tests"],
            total_duration=report["summary"]["total_duration_ms"],
            suite_rows=suite_rows,
            fastest_test=report["performance_summary"]["fastest_test"],
            slowest_test=report["performance_summary"]["slowest_test"],
            avg_duration=report["performance_summary"]["average_duration_ms"],
            failed_section=failed_section
        )
        
        # Save HTML report
        report_path = self.config.output_dir / "test_report.html"
        report_path.write_text(html_content)
        
        print(f"📊 HTML report saved to: {report_path}")


@contextmanager
def test_environment(config: Optional[TestConfig] = None):
    """Context manager for test environment setup/cleanup."""
    if config is None:
        config = TestConfig()
    
    env = TestEnvironment(config)
    try:
        env.setup()
        yield env
    finally:
        env.teardown()


def create_test_config(**kwargs) -> TestConfig:
    """Create test configuration with overrides."""
    return TestConfig(**kwargs)


if __name__ == '__main__':
    # Test the configuration and utilities
    print("🔧 Testing Enhanced Streamlit Test Configuration...")
    
    # Test configuration
    config = create_test_config(
        debug_mode=True,
        verbose_output=True,
        generate_html_report=True
    )
    
    print(f"✅ Configuration created:")
    print(f"  Test environment: {config.test_env}")
    print(f"  Debug mode: {config.debug_mode}")
    print(f"  Output directory: {config.output_dir}")
    print(f"  Temp directory: {config.temp_dir}")
    
    # Test environment setup
    with test_environment(config) as env:
        print(f"✅ Test environment set up successfully")
        
        # Create some temp files
        temp_file = env.create_temp_file('.txt', 'test content')
        temp_dir = env.create_temp_dir('test_dir')
        
        print(f"  Created temp file: {temp_file}")
        print(f"  Created temp directory: {temp_dir}")
        
        # Test mock factory
        mock_st = MockServiceFactory.create_mock_streamlit()
        print(f"  Created mock Streamlit: {type(mock_st)}")
        
        mock_aws = MockServiceFactory.create_mock_aws_client('s3')
        print(f"  Created mock AWS S3: {type(mock_aws)}")
    
    print(f"✅ Test environment cleaned up successfully")
    print(f"\n🎯 Test configuration and utilities ready for use!")