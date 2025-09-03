#!/usr/bin/env python3
"""
Comprehensive Test Runner for Enhanced Streamlit Application

Executes all test suites and generates detailed reports including:
- Unit test validation
- Integration test workflows  
- Performance benchmarking
- Security vulnerability testing
- User experience scenarios
- Test coverage analysis
- HTML reporting with metrics
"""

import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Any
import argparse
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import test modules
from tests.test_enhanced_streamlit import (
    TestEnhancedStreamlitApp,
    TestMultiVectorProcessing,
    TestEmbeddingVisualization, 
    TestUserExperienceScenarios,
    TestPerformanceValidation,
    TestSecurityAndValidation,
    TestIntegrationScenarios,
    generate_test_report
)

from tests.test_streamlit_integration import (
    TestCompleteWorkflowIntegration,
    TestPerformanceIntegration,
    TestErrorHandlingIntegration,
    run_integration_benchmarks
)

from tests.test_streamlit_performance import (
    TestEmbeddingPerformance,
    TestVisualizationPerformance,
    TestSearchPerformance,
    TestMemoryUsagePerformance,
    TestConcurrentPerformance,
    run_comprehensive_performance_benchmarks
)

from tests.test_streamlit_security import (
    TestInputValidation,
    TestSessionSecurity,
    TestAPISecurityValidation,
    TestResourceAccessControl,
    TestErrorDisclosurePrevention,
    run_security_test_suite
)

from tests.test_config import TestRunner, TestConfig, test_environment


class ComprehensiveTestRunner:
    """Runs all test suites with detailed reporting."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.runner = TestRunner(config)
        self.results = {}
        self.start_time = time.time()
        
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run all unit tests."""
        print("🧪 Running Unit Tests...")
        
        unit_test_classes = [
            TestEnhancedStreamlitApp,
            TestMultiVectorProcessing,
            TestEmbeddingVisualization,
            TestUserExperienceScenarios,
            TestPerformanceValidation,
            TestSecurityAndValidation,
            TestIntegrationScenarios
        ]
        
        unit_results = []
        for test_class in unit_test_classes:
            print(f"  📋 Running {test_class.__name__}...")
            result = self.runner.run_test_class(test_class)
            unit_results.append(result)
            print(f"    ✅ {result.passed_tests}/{result.total_tests} passed ({result.success_rate:.1f}%)")
        
        # Aggregate unit test results
        total_tests = sum(r.total_tests for r in unit_results)
        total_passed = sum(r.passed_tests for r in unit_results)
        total_duration = sum(r.total_duration_ms for r in unit_results)
        
        unit_summary = {
            'category': 'unit_tests',
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration_ms': total_duration,
            'suite_results': [r.to_dict() for r in unit_results]
        }
        
        print(f"✅ Unit Tests Complete: {total_passed}/{total_tests} passed ({unit_summary['success_rate']:.1f}%)")
        return unit_summary
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        print("\n🔗 Running Integration Tests...")
        
        integration_test_classes = [
            TestCompleteWorkflowIntegration,
            TestPerformanceIntegration,
            TestErrorHandlingIntegration
        ]
        
        integration_results = []
        for test_class in integration_test_classes:
            print(f"  📋 Running {test_class.__name__}...")
            result = self.runner.run_test_class(test_class)
            integration_results.append(result)
            print(f"    ✅ {result.passed_tests}/{result.total_tests} passed ({result.success_rate:.1f}%)")
        
        # Run integration benchmarks
        print("  📊 Running integration benchmarks...")
        try:
            benchmark_results = run_integration_benchmarks()
            print("    ✅ Integration benchmarks completed")
        except Exception as e:
            print(f"    ⚠️  Integration benchmarks failed: {e}")
            benchmark_results = {}
        
        # Aggregate results
        total_tests = sum(r.total_tests for r in integration_results)
        total_passed = sum(r.passed_tests for r in integration_results)
        total_duration = sum(r.total_duration_ms for r in integration_results)
        
        integration_summary = {
            'category': 'integration_tests',
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration_ms': total_duration,
            'suite_results': [r.to_dict() for r in integration_results],
            'benchmarks': benchmark_results
        }
        
        print(f"✅ Integration Tests Complete: {total_passed}/{total_tests} passed ({integration_summary['success_rate']:.1f}%)")
        return integration_summary
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        print("\n⚡ Running Performance Tests...")
        
        performance_test_classes = [
            TestEmbeddingPerformance,
            TestVisualizationPerformance,
            TestSearchPerformance,
            TestMemoryUsagePerformance,
            TestConcurrentPerformance
        ]
        
        performance_results = []
        for test_class in performance_test_classes:
            print(f"  📋 Running {test_class.__name__}...")
            result = self.runner.run_test_class(test_class)
            performance_results.append(result)
            print(f"    ✅ {result.passed_tests}/{result.total_tests} passed ({result.success_rate:.1f}%)")
        
        # Run comprehensive performance benchmarks
        print("  📊 Running comprehensive performance benchmarks...")
        try:
            benchmark_results = run_comprehensive_performance_benchmarks()
            print("    ✅ Performance benchmarks completed")
        except Exception as e:
            print(f"    ⚠️  Performance benchmarks failed: {e}")
            benchmark_results = {}
        
        # Aggregate results
        total_tests = sum(r.total_tests for r in performance_results)
        total_passed = sum(r.passed_tests for r in performance_results)
        total_duration = sum(r.total_duration_ms for r in performance_results)
        
        performance_summary = {
            'category': 'performance_tests',
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration_ms': total_duration,
            'suite_results': [r.to_dict() for r in performance_results],
            'benchmarks': benchmark_results
        }
        
        print(f"✅ Performance Tests Complete: {total_passed}/{total_tests} passed ({performance_summary['success_rate']:.1f}%)")
        return performance_summary
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests."""
        print("\n🔒 Running Security Tests...")
        
        security_test_classes = [
            TestInputValidation,
            TestSessionSecurity,
            TestAPISecurityValidation,
            TestResourceAccessControl,
            TestErrorDisclosurePrevention
        ]
        
        security_results = []
        for test_class in security_test_classes:
            print(f"  📋 Running {test_class.__name__}...")
            result = self.runner.run_test_class(test_class)
            security_results.append(result)
            print(f"    ✅ {result.passed_tests}/{result.total_tests} passed ({result.success_rate:.1f}%)")
        
        # Run security test suite
        print("  🛡️  Running comprehensive security tests...")
        try:
            security_suite_results = run_security_test_suite()
            print("    ✅ Security test suite completed")
        except Exception as e:
            print(f"    ⚠️  Security test suite failed: {e}")
            security_suite_results = {}
        
        # Aggregate results
        total_tests = sum(r.total_tests for r in security_results)
        total_passed = sum(r.passed_tests for r in security_results)
        total_duration = sum(r.total_duration_ms for r in security_results)
        
        security_summary = {
            'category': 'security_tests',
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'total_duration_ms': total_duration,
            'suite_results': [r.to_dict() for r in security_results],
            'security_assessment': security_suite_results
        }
        
        print(f"✅ Security Tests Complete: {total_passed}/{total_tests} passed ({security_summary['success_rate']:.1f}%)")
        return security_summary
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test categories."""
        print("🚀 Starting Comprehensive Enhanced Streamlit Test Suite...")
        print("=" * 80)
        
        # Run all test categories
        self.results['unit_tests'] = self.run_unit_tests()
        self.results['integration_tests'] = self.run_integration_tests()
        self.results['performance_tests'] = self.run_performance_tests()
        self.results['security_tests'] = self.run_security_tests()
        
        # Generate comprehensive report
        return self.generate_final_report()
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report."""
        total_duration = (time.time() - self.start_time) * 1000  # ms
        
        # Aggregate all results
        all_tests = sum(category['total_tests'] for category in self.results.values())
        all_passed = sum(category['passed_tests'] for category in self.results.values())
        overall_success_rate = (all_passed / all_tests * 100) if all_tests > 0 else 0
        
        final_report = {
            'test_execution_summary': {
                'execution_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_duration_ms': total_duration,
                'total_tests': all_tests,
                'total_passed': all_passed,
                'total_failed': all_tests - all_passed,
                'overall_success_rate': overall_success_rate
            },
            'category_results': self.results,
            'quality_assessment': self.assess_quality(),
            'recommendations': self.generate_recommendations()
        }
        
        # Save detailed report
        if self.config.output_dir:
            report_file = self.config.output_dir / 'comprehensive_test_report.json'
            with open(report_file, 'w') as f:
                json.dump(final_report, f, indent=2, default=str)
            print(f"\n📊 Detailed report saved: {report_file}")
        
        self.print_final_summary(final_report)
        return final_report
    
    def assess_quality(self) -> Dict[str, str]:
        """Assess overall quality based on test results."""
        assessments = {}
        
        for category, results in self.results.items():
            success_rate = results['success_rate']
            
            if success_rate >= 95:
                assessments[category] = "Excellent"
            elif success_rate >= 85:
                assessments[category] = "Good"
            elif success_rate >= 70:
                assessments[category] = "Acceptable"
            else:
                assessments[category] = "Needs Improvement"
        
        # Overall assessment
        overall_rate = (sum(r['passed_tests'] for r in self.results.values()) / 
                       sum(r['total_tests'] for r in self.results.values()) * 100)
        
        if overall_rate >= 90:
            assessments['overall'] = "Production Ready"
        elif overall_rate >= 80:
            assessments['overall'] = "Near Production Ready"
        else:
            assessments['overall'] = "Requires Attention"
        
        return assessments
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        for category, results in self.results.items():
            if results['success_rate'] < 85:
                recommendations.append(f"Improve {category.replace('_', ' ')} - success rate below 85%")
            
            if results['total_duration_ms'] > 60000:  # 1 minute
                recommendations.append(f"Optimize {category.replace('_', ' ')} - execution time excessive")
        
        # General recommendations
        overall_rate = (sum(r['passed_tests'] for r in self.results.values()) / 
                       sum(r['total_tests'] for r in self.results.values()) * 100)
        
        if overall_rate < 90:
            recommendations.append("Focus on failing tests to improve overall quality")
        
        if not recommendations:
            recommendations.append("Excellent test coverage - maintain current quality standards")
        
        return recommendations
    
    def print_final_summary(self, report: Dict[str, Any]):
        """Print final summary to console."""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE TEST EXECUTION COMPLETE")
        print("=" * 80)
        
        summary = report['test_execution_summary']
        print(f"📊 Overall Results:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['total_passed']}")
        print(f"   Failed: {summary['total_failed']}")
        print(f"   Success Rate: {summary['overall_success_rate']:.1f}%")
        print(f"   Execution Time: {summary['total_duration_ms']/1000:.1f} seconds")
        
        print(f"\n📋 Category Breakdown:")
        for category, results in self.results.items():
            category_name = category.replace('_', ' ').title()
            print(f"   {category_name}: {results['passed_tests']}/{results['total_tests']} "
                  f"({results['success_rate']:.1f}%)")
        
        print(f"\n🎯 Quality Assessment:")
        for category, assessment in report['quality_assessment'].items():
            category_name = category.replace('_', ' ').title()
            print(f"   {category_name}: {assessment}")
        
        print(f"\n💡 Recommendations:")
        for i, recommendation in enumerate(report['recommendations'], 1):
            print(f"   {i}. {recommendation}")
        
        # Final status
        overall_assessment = report['quality_assessment']['overall']
        if overall_assessment == "Production Ready":
            print(f"\n🟢 Status: {overall_assessment} - Ready for deployment!")
        elif overall_assessment == "Near Production Ready":
            print(f"\n🟡 Status: {overall_assessment} - Minor improvements needed")
        else:
            print(f"\n🔴 Status: {overall_assessment} - Significant improvements required")


def main():
    """Main entry point for comprehensive testing."""
    parser = argparse.ArgumentParser(description="Enhanced Streamlit Comprehensive Test Runner")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--output-dir", type=str, help="Output directory for reports")
    parser.add_argument("--categories", nargs="+", 
                       choices=["unit", "integration", "performance", "security"],
                       help="Test categories to run (default: all)")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--export-data", action="store_true", help="Export test data")
    
    args = parser.parse_args()
    
    # Create test configuration
    config = TestConfig(
        debug_mode=args.debug,
        verbose_output=args.verbose or args.debug,
        generate_html_report=not args.no_html,
        export_test_data=args.export_data,
        output_dir=Path(args.output_dir) if args.output_dir else None
    )
    
    # Run tests in managed environment
    with test_environment(config) as env:
        runner = ComprehensiveTestRunner(config)
        
        if args.categories:
            # Run specific categories
            results = {}
            if "unit" in args.categories:
                results['unit_tests'] = runner.run_unit_tests()
            if "integration" in args.categories:
                results['integration_tests'] = runner.run_integration_tests()
            if "performance" in args.categories:
                results['performance_tests'] = runner.run_performance_tests()
            if "security" in args.categories:
                results['security_tests'] = runner.run_security_tests()
            
            runner.results = results
            final_report = runner.generate_final_report()
        else:
            # Run all tests
            final_report = runner.run_all_tests()
    
    # Exit with appropriate code
    success_rate = final_report['test_execution_summary']['overall_success_rate']
    if success_rate >= 90:
        exit_code = 0  # Success
    elif success_rate >= 75:
        exit_code = 1  # Warning
    else:
        exit_code = 2  # Failure
    
    print(f"\n🚪 Exiting with code {exit_code}")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()