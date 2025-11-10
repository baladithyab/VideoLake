#!/usr/bin/env python3
"""
Safe Runner for Real AWS Integration Tests

This script provides a safe, interactive way to run real AWS tests with:
- Clear cost warnings
- Prerequisites checking
- Resource tracking
- Cost estimation
- Safe cleanup verification

Usage:
    python scripts/run_real_aws_tests.py [options]

Options:
    --skip-expensive    Skip expensive tests (OpenSearch)
    --keep-resources    Keep resources after tests for debugging
    --test-name NAME    Run specific test only
    --yes              Skip interactive confirmations (use with caution!)
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_banner(text: str):
    """Print formatted banner."""
    print("\n" + "=" * 80)
    print(f" {text}")
    print("=" * 80)


def check_prerequisites() -> Tuple[bool, List[str]]:
    """
    Check if prerequisites are met.
    
    Returns:
        (all_ok, messages) tuple
    """
    issues = []
    
    # Check AWS CLI
    try:
        result = subprocess.run(
            ['aws', 'sts', 'get-caller-identity'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print("✅ AWS credentials configured")
        else:
            issues.append("AWS credentials not configured or invalid")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        issues.append("AWS CLI not found or not responding")
    
    # Check region
    region = os.getenv('AWS_REGION', 'not-set')
    if region in ['us-east-1', 'us-west-2']:
        print(f"✅ AWS region: {region} (supports TwelveLabs)")
    else:
        issues.append(f"AWS_REGION '{region}' may not support TwelveLabs models. Use us-east-1 or us-west-2")
    
    # Check pytest
    try:
        import pytest
        print(f"✅ pytest installed: {pytest.__version__}")
    except ImportError:
        issues.append("pytest not installed")
    
    # Check boto3
    try:
        import boto3
        print(f"✅ boto3 installed: {boto3.__version__}")
    except ImportError:
        issues.append("boto3 not installed")
    
    return len(issues) == 0, issues


def estimate_costs(skip_expensive: bool, test_name: Optional[str] = None) -> Dict[str, float]:
    """Estimate test costs."""
    costs = {
        "s3vector": 0.02,
        "lancedb": 0.01,
        "opensearch": 2.00,
        "comparison": 0.05,
        "error_handling": 0.01
    }
    
    if test_name:
        # Specific test
        for key in costs:
            if key in test_name.lower():
                return {"estimated": costs[key], "max": costs[key] * 1.5}
        return {"estimated": 0.05, "max": 0.10}
    
    # All tests
    total = sum(costs.values())
    if skip_expensive:
        total -= costs["opensearch"]
    
    return {"estimated": total, "max": total * 1.5}


def confirm_execution(cost_info: dict, skip_expensive: bool, auto_yes: bool = False) -> bool:
    """Get user confirmation."""
    if auto_yes:
        return True
    
    print_banner("COST WARNING")
    print(f"\n⚠️  These tests will use REAL AWS resources and incur costs!")
    print(f"\nEstimated cost: ${cost_info['estimated']:.2f}")
    print(f"Maximum cost: ${cost_info['max']:.2f}")
    
    if skip_expensive:
        print("\n✅ Expensive tests (OpenSearch) will be SKIPPED")
    else:
        print("\n⚠️  EXPENSIVE tests (OpenSearch ~$2/hour) will be INCLUDED")
    
    print("\nResources that will be created:")
    print("  • S3 buckets (for videos and vectors)")
    print("  • S3 Vector indexes")
    print("  • Test video processing via TwelveLabs/Bedrock")
    if not skip_expensive:
        print("  • OpenSearch Serverless collection (EXPENSIVE!)")
    
    print("\nAll resources will be automatically cleaned up after tests.")
    
    response = input("\n⚠️  Proceed with real AWS tests? (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def build_pytest_command(
    skip_expensive: bool,
    keep_resources: bool,
    test_name: Optional[str] = None
) -> Tuple[List[str], Dict[str, str]]:
    """Build pytest command."""
    cmd = [
        'pytest',
        'tests/test_real_aws_e2e_workflows.py',
        '-v',
        '--real-aws',
        '--tb=short',
        '--durations=10'
    ]
    
    if test_name:
        cmd[1] = f"tests/test_real_aws_e2e_workflows.py::{test_name}"
    
    if skip_expensive:
        cmd.extend(['-m', 'not expensive'])
    
    # Set environment variables
    env = os.environ.copy()
    
    if keep_resources:
        env['KEEP_TEST_RESOURCES'] = '1'
    
    if skip_expensive:
        env['SKIP_EXPENSIVE_TESTS'] = '1'
    
    return cmd, env


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Safe runner for real AWS integration tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--skip-expensive',
        action='store_true',
        help='Skip expensive tests (OpenSearch)'
    )
    parser.add_argument(
        '--keep-resources',
        action='store_true',
        help='Keep resources after tests for debugging'
    )
    parser.add_argument(
        '--test-name',
        type=str,
        help='Run specific test class only'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip interactive confirmations (dangerous!)'
    )
    
    args = parser.parse_args()
    
    # Banner
    print_banner("Real AWS Integration Tests - Safe Runner")
    
    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    all_ok, issues = check_prerequisites()
    
    if not all_ok:
        print("\n❌ Prerequisites check failed:")
        for issue in issues:
            print(f"  • {issue}")
        print("\nPlease fix the issues above and try again.")
        return 1
    
    print("\n✅ All prerequisites OK")
    
    # Estimate costs
    cost_info = estimate_costs(args.skip_expensive, args.test_name)
    
    # Get confirmation
    if not confirm_execution(cost_info, args.skip_expensive, args.yes):
        print("\n❌ Tests cancelled by user")
        return 0
    
    # Build command
    print("\n🚀 Building test command...")
    cmd, env = build_pytest_command(
        args.skip_expensive,
        args.keep_resources,
        args.test_name
    )
    
    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Environment:")
    print(f"  AWS_REGION: {env.get('AWS_REGION', 'default')}")
    print(f"  SKIP_EXPENSIVE_TESTS: {env.get('SKIP_EXPENSIVE_TESTS', '0')}")
    print(f"  KEEP_TEST_RESOURCES: {env.get('KEEP_TEST_RESOURCES', '0')}")
    
    # Run tests
    print_banner("Running Tests")
    print("\n⏳ Starting test execution...\n")
    
    try:
        result = subprocess.run(cmd, env=env)
        
        if result.returncode == 0:
            print_banner("SUCCESS")
            print("\n✅ All tests passed!")
            
            if args.keep_resources:
                print("\n⚠️  Resources were KEPT for debugging")
                print("   Manual cleanup required:")
                print("   python scripts/cleanup_all_resources.py --prefix test-real-e2e")
            else:
                print("\n✅ All resources cleaned up automatically")
            
            return 0
        else:
            print_banner("FAILED")
            print("\n❌ Some tests failed")
            
            if not args.keep_resources:
                print("\n✅ Resources still cleaned up despite failures")
            
            return 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        print("⚠️  Cleanup may still be in progress...")
        return 130
    
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())