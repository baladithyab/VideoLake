#!/usr/bin/env python3
"""
Real AWS Integration Test Runner

This script sets up the environment and runs real AWS integration tests
to validate that all backend services work correctly with actual AWS resources.

Usage:
    python scripts/run_real_aws_tests.py [--quick] [--full] [--cleanup-only]
    
Options:
    --quick      Run only core functionality tests (faster)
    --full       Run comprehensive test suite including video processing
    --cleanup-only  Only run cleanup operations
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def check_aws_credentials():
    """Check if AWS credentials are properly configured."""
    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials valid - Account: {identity['Account']}")
        print(f"   ARN: {identity['Arn']}")
        return True
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        return False

def check_environment():
    """Check required environment variables."""
    required_vars = {
        'S3_VECTORS_BUCKET': 'S3 Vector bucket name for testing',
        'AWS_REGION': 'AWS region (defaults to us-east-1)'
    }
    
    missing = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            if var == 'AWS_REGION':
                os.environ[var] = 'us-east-1'  # Set default
                print(f"ℹ️  {var}: Using default 'us-east-1'")
            else:
                missing.append(f"  {var}: {description}")
        else:
            print(f"✅ {var}: {value}")
    
    if missing:
        print("❌ Missing required environment variables:")
        for var in missing:
            print(var)
        return False
    
    return True

def run_tests(test_type: str):
    """Run the specified test suite."""
    
    # Set up environment
    env = os.environ.copy()
    env['REAL_AWS_TESTS'] = '1'
    env['PYTHONPATH'] = str(Path(__file__).parent.parent)
    
    if test_type == "quick":
        # Run core functionality tests only
        test_files = [
            "tests/test_s3_vector_storage.py",
            "tests/test_bedrock_embedding.py",
            "tests/integration_test_end_to_end_text_processing.py"
        ]
        
        print("🚀 Running quick real AWS tests...")
        print("   - S3 Vector storage operations")
        print("   - Bedrock embedding generation") 
        print("   - End-to-end text processing")
        
    elif test_type == "full":
        # Run comprehensive test suite
        test_files = [
            "tests/test_real_aws_integration.py",
            "tests/test_s3_vector_storage.py", 
            "tests/test_bedrock_embedding.py",
            "tests/test_similarity_search_engine.py",
            "tests/integration_test_end_to_end_text_processing.py",
            "tests/integration_test_s3_vector_storage.py"
        ]
        
        print("🚀 Running comprehensive real AWS tests...")
        print("   - All integration tests")
        print("   - Performance benchmarking")
        print("   - Error handling scenarios")
        
    elif test_type == "cleanup-only":
        # Run cleanup script
        print("🧹 Running cleanup operations...")
        cleanup_script = Path(__file__).parent / "cleanup_s3vectors_buckets.py"
        if cleanup_script.exists():
            subprocess.run([sys.executable, str(cleanup_script)], env=env)
        return True
    
    # Run pytest with real AWS environment
    cmd = [
        sys.executable, "-m", "pytest",
        *test_files,
        "-v",
        "--tb=short", 
        "--maxfail=3",
        "-x"  # Stop on first failure for faster feedback
    ]
    
    print(f"\n🔧 Running command: {' '.join(cmd)}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, env=env, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("\n✅ All real AWS tests passed!")
            print("🎉 Backend services are working correctly with AWS resources")
            return True
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run real AWS integration tests")
    parser.add_argument(
        '--quick', 
        action='store_true',
        help='Run only core functionality tests (faster)'
    )
    parser.add_argument(
        '--full',
        action='store_true', 
        help='Run comprehensive test suite'
    )
    parser.add_argument(
        '--cleanup-only',
        action='store_true',
        help='Only run cleanup operations'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Skip confirmation prompt and proceed automatically'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🧪 S3Vector Real AWS Integration Test Runner")
    print("=" * 80)
    print()
    
    # Determine test type
    if args.cleanup_only:
        test_type = "cleanup-only"
    elif args.full:
        test_type = "full"
    else:
        test_type = "quick"  # Default
    
    print(f"📋 Test Mode: {test_type}")
    print()
    
    # Check prerequisites
    print("🔍 Checking prerequisites...")
    
    if not check_aws_credentials():
        print("\n💡 Setup tips:")
        print("   1. Configure AWS credentials: aws configure")
        print("   2. Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print("   3. Ensure you have permissions for S3 Vectors and Bedrock")
        sys.exit(1)
    
    if not check_environment():
        print("\n💡 Setup tips:")
        print("   1. Set S3_VECTORS_BUCKET to a unique bucket name")
        print("   2. Optionally set AWS_REGION (defaults to us-east-1)")
        print("   3. Example: export S3_VECTORS_BUCKET=my-test-bucket-12345")
        sys.exit(1)
    
    print("\n✅ Prerequisites satisfied")
    print()
    
    # Warning about costs
    if test_type != "cleanup-only":
        print("⚠️  COST WARNING:")
        print("   These tests will create real AWS resources and may incur costs.")
        print("   - S3 Vector operations: ~$0.001 per operation")
        print("   - Bedrock embeddings: ~$0.0001 per 1K tokens")
        print("   - Storage costs: minimal for test data")
        print()
        
        if not args.yes:
            response = input("Continue with real AWS tests? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                print("❌ Tests cancelled by user")
                sys.exit(0)
        else:
            print("✅ Auto-proceeding with tests (--yes flag provided)")
        print()
    
    # Run tests
    success = run_tests(test_type)
    
    if success:
        print("\n🎉 Real AWS integration tests completed successfully!")
        print("✅ Backend services are ready for Streamlit demo development")
        
        if test_type != "cleanup-only":
            print("\n💡 Next steps:")
            print("   1. Launch the Streamlit demo: python frontend/launch_unified_streamlit.py")
            print("   2. Enable 'Use Real AWS' in the demo for actual processing")
            print("   3. Test with sample videos or upload your own content")
    else:
        print("\n❌ Some tests failed - check the output above")
        print("💡 Fix any issues before proceeding with demo development")
        sys.exit(1)

if __name__ == "__main__":
    main()