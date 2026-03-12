#!/usr/bin/env python3
"""
Streamlined S3Vector Demo Runner

Runs consolidated demo script with real AWS services to validate functionality.

Usage:
    export REAL_AWS_DEMO=1  # Enable real AWS operations
    python scripts/run_all_demos.py [--quick] [--video] [--text-only]
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

def check_prerequisites():
    """Check if environment is ready for demos."""
    print("🔍 Checking prerequisites...")
    
    # Check AWS credentials
    try:
        import boto3
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✅ AWS credentials valid - Account: {identity['Account']}")
    except Exception as e:
        print(f"❌ AWS credentials not configured: {e}")
        return False
    
    # Check environment variables
    bucket = os.getenv('S3_VECTORS_BUCKET')
    if not bucket:
        print("❌ S3_VECTORS_BUCKET not set")
        return False
    
    print(f"✅ S3 Vectors bucket: {bucket}")
    
    # Check safety gate
    if os.getenv('REAL_AWS_DEMO') != '1':
        print("❌ REAL_AWS_DEMO not set to '1'")
        return False
    
    print("✅ Real AWS demo enabled")
    return True

def run_validation_tests():
    """Run validation tests first."""
    print("\\n" + "="*80)
    print("🧪 RUNNING VALIDATION TESTS")
    print("="*80)
    
    try:
        # Run service validation
        result = subprocess.run([
            sys.executable, "scripts/validate_aws_services.py"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Service validation passed")
            return True
        else:
            print("❌ Service validation failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def run_comprehensive_demo(args_list):
    """Run the comprehensive real demo."""
    print("\\n" + "="*80)
    print("🎬 RUNNING COMPREHENSIVE S3VECTOR DEMO")
    print("="*80)
    
    try:
        env = os.environ.copy()
        env['REAL_AWS_DEMO'] = '1'
        
        cmd = [sys.executable, "archive/legacy-examples/comprehensive_real_demo.py"] + args_list
        
        result = subprocess.run(
            cmd,
            env=env,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print("✅ Comprehensive demo completed successfully")
            return True
        else:
            print("❌ Comprehensive demo failed")
            return False
            
    except Exception as e:
        print(f"❌ Comprehensive demo error: {e}")
        return False

def run_cross_modal_demo():
    """Run the cross-modal search demo."""
    print("\\n" + "="*80)
    print("🔄 RUNNING CROSS-MODAL SEARCH DEMO")
    print("="*80)
    
    try:
        env = os.environ.copy()
        env['REAL_AWS_DEMO'] = '1'
        
        result = subprocess.run([
            sys.executable, "archive/legacy-examples/cross_modal_search_demo.py"
        ], env=env, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Cross-modal demo completed successfully")
            return True
        else:
            print("❌ Cross-modal demo failed")
            return False
            
    except Exception as e:
        print(f"❌ Cross-modal demo error: {e}")
        return False

def test_streamlit_import():
    """Test that Streamlit app can be imported and initialized."""
    print("\\n" + "="*80)
    print("🎬 TESTING STREAMLIT APP IMPORT")
    print("="*80)
    
    try:
        # Test import without running Streamlit
        test_code = '''
import sys
sys.path.append(".")
from frontend.unified_streamlit_app import UnifiedStreamlitApp
print("✅ Streamlit app imports successfully")
app = UnifiedStreamlitApp()
print("✅ App initializes successfully")
print("✅ Backend services ready for demo")
'''
        
        result = subprocess.run([
            sys.executable, "-c", test_code
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if result.returncode == 0:
            print("✅ Streamlit app import test passed")
            print("✅ Frontend ready for launch")
            return True
        else:
            print("❌ Streamlit app import failed:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Streamlit test error: {e}")
        return False

def main():
    """Main demo runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run S3Vector demos with real AWS services")
    parser.add_argument('--quick', action='store_true', help='Run only quick tests')
    parser.add_argument('--text-only', action='store_true', help='Skip video processing tests')
    parser.add_argument('--with-video', action='store_true', help='Include video processing')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation tests')
    
    args = parser.parse_args()
    
    print("="*80)
    print("🎬 S3Vector Streamlined Demo Runner")
    print("="*80)
    print()
    print("🚀 Testing S3Vector functionality with real AWS services")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\\n❌ Prerequisites not met. Please fix the issues above.")
        return 1
    
    print("\\n✅ All prerequisites satisfied")
    
    # Cost warning based on args
    estimated_cost = 0.02
    if args.with_video:
        estimated_cost = 0.15
    
    print("\\n⚠️  COST WARNING:")
    print(f"   These demos will use real AWS resources and incur costs: ~${estimated_cost:.2f}")
    
    # Build demo arguments
    demo_args = []
    if args.text_only:
        demo_args.append('--text-only')
    if args.with_video:
        demo_args.append('--with-video')
    if args.quick:
        demo_args.append('--quick')
    
    # Run demo suite
    demos = []
    
    if not args.skip_validation:
        demos.append(("Validation Tests", lambda: run_validation_tests()))
    
    demos.extend([
        ("Comprehensive Demo", lambda: run_comprehensive_demo(demo_args)),
        ("Cross-Modal Search Demo", run_cross_modal_demo),
        ("Streamlit Import Test", test_streamlit_import)
    ])
    
    results = {}
    start_time = time.time()
    
    for demo_name, demo_func in demos:
        try:
            print(f"\\n🎯 Starting: {demo_name}")
            result = demo_func()
            results[demo_name] = result
            
            if result:
                print(f"✅ {demo_name}: PASSED")
            else:
                print(f"❌ {demo_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {demo_name}: ERROR - {e}")
            results[demo_name] = False
    
    # Final summary
    total_time = time.time() - start_time
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print("\\n" + "="*80)
    print("🎯 STREAMLINED DEMO RESULTS")
    print("="*80)
    
    for demo_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {demo_name}")
    
    print(f"\\nOverall: {passed}/{total} demos passed")
    print(f"Total time: {total_time:.1f} seconds")
    
    if passed == total:
        print("\\n🎉 ALL DEMOS PASSED! S3Vector is fully functional with real AWS services.")
        print("\\n💡 Ready for production use:")
        print("   1. Launch Streamlit demo: python frontend/launch_unified_streamlit.py")
        print("   2. Test with sample content using comprehensive demo")
        print("   3. Deploy to production environment")
        return 0
    else:
        print("\\n⚠️ Some demos failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())