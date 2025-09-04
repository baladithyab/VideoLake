#!/usr/bin/env python3
"""
Automated Test Execution Framework for S3Vector Integration Tests

This framework provides automated execution, reporting, and analysis for the
comprehensive integration test suite with support for different test modes,
environments, and reporting formats.
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.comprehensive_integration_test_plan import TestMode, TestCategory

class TestStatus(Enum):
    """Test execution status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"

@dataclass
class TestExecutionResult:
    """Result of test execution."""
    test_file: str
    test_name: str
    category: str
    status: TestStatus
    duration_ms: int
    error_message: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None

@dataclass
class TestSuiteReport:
    """Complete test suite execution report."""
    execution_id: str
    start_time: str
    end_time: str
    total_duration_ms: int
    test_mode: str
    environment: str
    results: List[TestExecutionResult]
    summary: Dict[str, int]
    coverage_report: Optional[Dict[str, Any]] = None

class AutomatedTestRunner:
    """Automated test execution framework."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.execution_id = f"integration-{int(time.time())}"
        self.results: List[TestExecutionResult] = []
        self.start_time = time.time()
        
    def run_integration_test_suite(self) -> TestSuiteReport:
        """Run the complete integration test suite."""
        print(f"🧪 S3Vector Integration Test Suite")
        print(f"Execution ID: {self.execution_id}")
        print(f"Mode: {self.config.get('mode', 'simulation')}")
        print(f"Environment: {self.config.get('environment', 'local')}")
        print("=" * 80)
        
        # Define test categories and files
        test_categories = {
            "user_journey": {
                "file": "test_complete_user_journey_integration.py",
                "markers": ["user_journey"],
                "timeout": 300
            },
            "service_integration": {
                "file": "test_service_integration_patterns.py", 
                "markers": ["service_integration"],
                "timeout": 180
            },
            "aws_integration": {
                "file": "test_aws_service_integrations.py",
                "markers": ["aws_integration"],
                "timeout": 600
            },
            "performance": {
                "file": "test_performance_error_recovery.py",
                "markers": ["performance"],
                "timeout": 900
            },
            "error_recovery": {
                "file": "test_performance_error_recovery.py",
                "markers": ["error_recovery"],
                "timeout": 300
            }
        }
        
        # Execute test categories
        for category, config in test_categories.items():
            if self._should_run_category(category):
                print(f"\n🔄 Running {category} tests...")
                category_results = self._run_test_category(category, config)
                self.results.extend(category_results)
                self._print_category_summary(category, category_results)
        
        # Generate final report
        return self._generate_final_report()
    
    def _should_run_category(self, category: str) -> bool:
        """Determine if test category should be run based on configuration."""
        config = self.config
        
        # Check mode restrictions
        if category == "aws_integration" and config.get('mode') == 'simulation':
            if not config.get('enable_aws_tests', False):
                print(f"⏭️  Skipping {category} tests - AWS tests disabled in simulation mode")
                return False
        
        if category == "performance" and not config.get('enable_performance_tests', False):
            print(f"⏭️  Skipping {category} tests - Performance tests disabled")
            return False
        
        # Check environment requirements
        if category == "aws_integration" and not os.getenv("AWS_ACCESS_KEY_ID"):
            print(f"⏭️  Skipping {category} tests - AWS credentials not available")
            return False
        
        # Check category filters
        only_categories = config.get('only_categories', [])
        if only_categories and category not in only_categories:
            print(f"⏭️  Skipping {category} tests - Not in requested categories")
            return False
        
        return True
    
    def _run_test_category(self, category: str, category_config: Dict[str, Any]) -> List[TestExecutionResult]:
        """Run tests for a specific category."""
        test_file = category_config["file"]
        markers = category_config["markers"]
        timeout = category_config.get("timeout", 300)
        
        # Build pytest command
        cmd = self._build_pytest_command(test_file, markers, timeout)
        
        # Execute tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=Path(__file__).parent
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Parse pytest results
            return self._parse_pytest_results(
                test_file, category, result, duration_ms
            )
            
        except subprocess.TimeoutExpired:
            duration_ms = timeout * 1000
            return [TestExecutionResult(
                test_file=test_file,
                test_name=f"{category}_timeout",
                category=category,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                error_message=f"Test category {category} timed out after {timeout} seconds"
            )]
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return [TestExecutionResult(
                test_file=test_file,
                test_name=f"{category}_error",
                category=category,
                status=TestStatus.ERROR,
                duration_ms=duration_ms,
                error_message=str(e)
            )]
    
    def _build_pytest_command(self, test_file: str, markers: List[str], timeout: int) -> List[str]:
        """Build pytest command with appropriate options."""
        cmd = [
            sys.executable, "-m", "pytest",
            test_file,
            "-v",
            "--tb=short",
            "--disable-warnings",
            f"--timeout={timeout}"
        ]
        
        # Add marker filters
        if markers:
            marker_expr = " or ".join(markers)
            cmd.extend(["-m", marker_expr])
        
        # Add coverage if requested
        if self.config.get('enable_coverage', False):
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=json:coverage.json"
            ])
        
        # Add output format
        output_format = self.config.get('output_format', 'standard')
        if output_format == 'json':
            cmd.append("--json-report")
            cmd.append(f"--json-report-file=test_report_{self.execution_id}.json")
        
        # Add parallel execution if requested
        max_workers = self.config.get('max_workers', 1)
        if max_workers > 1:
            cmd.extend(["-n", str(max_workers)])
        
        return cmd
    
    def _parse_pytest_results(
        self, 
        test_file: str, 
        category: str, 
        result: subprocess.CompletedProcess, 
        duration_ms: int
    ) -> List[TestExecutionResult]:
        """Parse pytest output into test results."""
        results = []
        
        # Basic result parsing from pytest output
        output_lines = result.stdout.split('\n')
        
        # Count results by parsing pytest summary
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        error_count = 0
        
        for line in output_lines:
            if "passed" in line and "failed" in line:
                # Parse summary line like "5 failed, 3 passed, 2 skipped"
                parts = line.split(',')
                for part in parts:
                    part = part.strip()
                    if 'passed' in part:
                        passed_count = int(part.split()[0])
                    elif 'failed' in part:
                        failed_count = int(part.split()[0])
                    elif 'skipped' in part:
                        skipped_count = int(part.split()[0])
                    elif 'error' in part:
                        error_count = int(part.split()[0])
        
        # Create result objects (simplified for now)
        total_tests = passed_count + failed_count + skipped_count + error_count
        if total_tests == 0:
            total_tests = 1  # At least one test assumed
        
        # Create individual test results
        for i in range(max(1, total_tests)):
            if i < passed_count:
                status = TestStatus.PASSED
            elif i < passed_count + failed_count:
                status = TestStatus.FAILED
            elif i < passed_count + failed_count + skipped_count:
                status = TestStatus.SKIPPED
            else:
                status = TestStatus.ERROR
            
            results.append(TestExecutionResult(
                test_file=test_file,
                test_name=f"{category}_test_{i+1}",
                category=category,
                status=status,
                duration_ms=duration_ms // max(1, total_tests),
                error_message=result.stderr if status in [TestStatus.FAILED, TestStatus.ERROR] else None,
                stdout=result.stdout,
                stderr=result.stderr
            ))
        
        return results
    
    def _print_category_summary(self, category: str, results: List[TestExecutionResult]):
        """Print summary for a test category."""
        if not results:
            return
        
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        total_duration = sum(r.duration_ms for r in results)
        
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⏭️  Skipped: {skipped}")
        print(f"  🚫 Errors: {errors}")
        print(f"  ⏱️  Duration: {total_duration/1000:.2f}s")
        
        # Show failed tests
        failed_results = [r for r in results if r.status == TestStatus.FAILED]
        if failed_results:
            print(f"  📋 Failed Tests:")
            for result in failed_results[:3]:  # Show first 3
                print(f"    • {result.test_name}")
                if result.error_message:
                    error_msg = result.error_message[:100] + "..." if len(result.error_message) > 100 else result.error_message
                    print(f"      {error_msg}")
    
    def _generate_final_report(self) -> TestSuiteReport:
        """Generate final test suite report."""
        end_time = time.time()
        total_duration_ms = int((end_time - self.start_time) * 1000)
        
        # Calculate summary statistics
        summary = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.status == TestStatus.PASSED),
            "failed": sum(1 for r in self.results if r.status == TestStatus.FAILED),
            "skipped": sum(1 for r in self.results if r.status == TestStatus.SKIPPED),
            "errors": sum(1 for r in self.results if r.status == TestStatus.ERROR)
        }
        
        report = TestSuiteReport(
            execution_id=self.execution_id,
            start_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time)),
            end_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time)),
            total_duration_ms=total_duration_ms,
            test_mode=self.config.get('mode', 'simulation'),
            environment=self.config.get('environment', 'local'),
            results=self.results,
            summary=summary
        )
        
        # Print final summary
        self._print_final_summary(report)
        
        # Save report if requested
        if self.config.get('save_report', True):
            self._save_report(report)
        
        return report
    
    def _print_final_summary(self, report: TestSuiteReport):
        """Print final test execution summary."""
        print("\n" + "=" * 80)
        print("🏁 INTEGRATION TEST SUITE COMPLETE")
        print("=" * 80)
        print(f"Execution ID: {report.execution_id}")
        print(f"Duration: {report.total_duration_ms/1000:.2f} seconds")
        print(f"Mode: {report.test_mode}")
        print(f"Environment: {report.environment}")
        print()
        
        summary = report.summary
        total = summary["total"]
        passed = summary["passed"]
        failed = summary["failed"]
        skipped = summary["skipped"]
        errors = summary["errors"]
        
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 TEST RESULTS:")
        print(f"  Total Tests: {total}")
        print(f"  ✅ Passed: {passed} ({passed/total*100:.1f}%)")
        print(f"  ❌ Failed: {failed} ({failed/total*100:.1f}%)")
        print(f"  ⏭️  Skipped: {skipped} ({skipped/total*100:.1f}%)")
        print(f"  🚫 Errors: {errors} ({errors/total*100:.1f}%)")
        print(f"  📈 Success Rate: {success_rate:.1f}%")
        
        # Overall status
        if failed == 0 and errors == 0:
            print(f"\n🎉 ALL TESTS PASSED! (Expected failures due to TDD approach)")
        elif failed > 0:
            print(f"\n⚠️  TESTS FAILED: {failed} failing tests need implementation")
        
        if errors > 0:
            print(f"🚨 TEST ERRORS: {errors} tests had execution errors")
        
        # Category breakdown
        print(f"\n📋 CATEGORY BREAKDOWN:")
        categories = {}
        for result in report.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
            categories[cat][result.status.value.lower()] += 1
        
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            print(f"  {category}: {stats['passed']}/{total_cat} passed")
    
    def _save_report(self, report: TestSuiteReport):
        """Save test report to file."""
        report_dir = Path("test_reports")
        report_dir.mkdir(exist_ok=True)
        
        # Save JSON report
        json_file = report_dir / f"integration_test_report_{report.execution_id}.json"
        with open(json_file, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        print(f"\n💾 Test report saved to: {json_file}")
        
        # Save human-readable report
        txt_file = report_dir / f"integration_test_report_{report.execution_id}.txt"
        with open(txt_file, 'w') as f:
            f.write(f"S3Vector Integration Test Report\n")
            f.write(f"Generated: {report.end_time}\n")
            f.write(f"Execution ID: {report.execution_id}\n")
            f.write(f"Duration: {report.total_duration_ms/1000:.2f}s\n")
            f.write(f"Mode: {report.test_mode}\n")
            f.write(f"Environment: {report.environment}\n\n")
            
            f.write(f"Summary:\n")
            for key, value in report.summary.items():
                f.write(f"  {key}: {value}\n")
            
            f.write(f"\nDetailed Results:\n")
            for result in report.results:
                f.write(f"  {result.test_name}: {result.status.value} ({result.duration_ms}ms)\n")
                if result.error_message:
                    f.write(f"    Error: {result.error_message}\n")

def create_test_configuration(args) -> Dict[str, Any]:
    """Create test configuration from command line arguments."""
    return {
        'mode': args.mode,
        'environment': args.environment,
        'enable_aws_tests': args.aws_tests,
        'enable_performance_tests': args.performance,
        'enable_coverage': args.coverage,
        'max_workers': args.workers,
        'output_format': args.format,
        'save_report': args.save_report,
        'only_categories': args.categories.split(',') if args.categories else [],
        'timeout': args.timeout
    }

def main():
    """Main entry point for automated test runner."""
    parser = argparse.ArgumentParser(description='S3Vector Integration Test Runner')
    
    parser.add_argument(
        '--mode', 
        choices=['simulation', 'hybrid', 'real_aws'],
        default='simulation',
        help='Test execution mode'
    )
    
    parser.add_argument(
        '--environment',
        choices=['local', 'ci', 'staging', 'production'],
        default='local', 
        help='Test environment'
    )
    
    parser.add_argument(
        '--aws-tests',
        action='store_true',
        help='Enable AWS integration tests (requires credentials)'
    )
    
    parser.add_argument(
        '--performance',
        action='store_true',
        help='Enable performance tests'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Enable code coverage reporting'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel test workers'
    )
    
    parser.add_argument(
        '--format',
        choices=['standard', 'json', 'xml'],
        default='standard',
        help='Output format'
    )
    
    parser.add_argument(
        '--save-report',
        action='store_true',
        default=True,
        help='Save test report to file'
    )
    
    parser.add_argument(
        '--categories',
        help='Comma-separated list of test categories to run'
    )
    
    parser.add_argument(
        '--timeout',
        type=int,
        default=600,
        help='Test timeout in seconds'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = create_test_configuration(args)
    
    # Create and run test suite
    runner = AutomatedTestRunner(config)
    report = runner.run_integration_test_suite()
    
    # Exit with appropriate code
    if report.summary['failed'] > 0 or report.summary['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()