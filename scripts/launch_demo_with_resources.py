#!/usr/bin/env python3
"""
Launch S3Vector Demo with Resource Management

Quick launcher for the S3Vector demo with resource management capabilities.
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_demo_readiness():
    """Check if the demo is ready to launch."""
    print("🔍 Checking Demo Readiness...")
    
    try:
        # Check if main demo file exists
        demo_file = project_root / "frontend" / "launch_refactored_demo.py"
        if not demo_file.exists():
            print(f"❌ Demo file not found: {demo_file}")
            return False
        
        print(f"✅ Demo file found: {demo_file}")
        
        # Check if workflow resource manager exists
        resource_manager_file = project_root / "frontend" / "components" / "workflow_resource_manager.py"
        if not resource_manager_file.exists():
            print(f"❌ Resource manager not found: {resource_manager_file}")
            return False
        
        print(f"✅ Resource manager found: {resource_manager_file}")
        
        # Check resource registry
        registry_file = project_root / "coordination" / "resource_registry.json"
        if not registry_file.exists():
            print(f"❌ Resource registry not found: {registry_file}")
            return False
        
        print(f"✅ Resource registry found: {registry_file}")
        
        # Check if we can import key components
        try:
            from frontend.components.workflow_resource_manager import WorkflowResourceManager
            print("✅ Workflow resource manager import successful")
        except ImportError as e:
            print(f"❌ Failed to import workflow resource manager: {e}")
            return False
        
        try:
            from src.utils.resource_registry import resource_registry
            summary = resource_registry.get_resource_summary()
            print(f"✅ Resource registry accessible ({summary.get('s3_buckets', 0)} S3 buckets, {summary.get('opensearch_collections', 0)} collections)")
        except Exception as e:
            print(f"❌ Failed to access resource registry: {e}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Demo readiness check failed: {e}")
        return False


def show_resource_summary():
    """Show current resource summary."""
    print("\n📊 Current Resource Summary:")
    
    try:
        from src.utils.resource_registry import resource_registry
        
        # Get resource summary
        summary = resource_registry.get_resource_summary()
        
        print(f"   📦 S3 Buckets: {summary.get('s3_buckets', 0)}")
        print(f"   🗂️ Vector Buckets: {summary.get('vector_buckets', 0)}")
        print(f"   🔍 Vector Indexes: {summary.get('vector_indexes', 0)}")
        print(f"   🔎 OpenSearch Collections: {summary.get('opensearch_collections', 0)}")
        print(f"   🌐 OpenSearch Domains: {summary.get('opensearch_domains', 0)}")
        
        # Show active resources
        active = resource_registry.get_active_resources()
        print(f"\n⚙️ Active Resources:")
        for resource_type, resource_name in active.items():
            if resource_name:
                print(f"   {resource_type.replace('_', ' ').title()}: {resource_name}")
        
        # Show some example resources
        s3_buckets = resource_registry.list_s3_buckets()
        if s3_buckets:
            print(f"\n📦 Available S3 Buckets:")
            for bucket in s3_buckets[:3]:  # Show first 3
                status = bucket.get('status', 'unknown')
                print(f"   - {bucket['name']} ({status})")
            if len(s3_buckets) > 3:
                print(f"   ... and {len(s3_buckets) - 3} more")
        
        os_collections = resource_registry.list_opensearch_collections()
        if os_collections:
            print(f"\n🔎 Available OpenSearch Collections:")
            for collection in os_collections[:3]:  # Show first 3
                status = collection.get('status', 'unknown')
                print(f"   - {collection['name']} ({status})")
            if len(os_collections) > 3:
                print(f"   ... and {len(os_collections) - 3} more")
        
    except Exception as e:
        print(f"❌ Failed to get resource summary: {e}")


def launch_demo():
    """Launch the Streamlit demo."""
    print("\n🚀 Launching S3Vector Demo with Resource Management...")
    
    demo_file = project_root / "frontend" / "launch_refactored_demo.py"
    
    try:
        # Change to project directory
        os.chdir(project_root)
        
        # Launch streamlit
        cmd = ["streamlit", "run", str(demo_file), "--server.port", "8501"]
        
        print(f"Running command: {' '.join(cmd)}")
        print(f"Working directory: {project_root}")
        print("\n" + "="*50)
        print("🌐 Demo will be available at: http://localhost:8501")
        print("📋 Navigate to the 'Resources' section to test resource management")
        print("🔄 Try the 'Resume Work' functionality with your existing resources")
        print("🛠️ Test creating new resources")
        print("🧹 Test the cleanup functionality")
        print("="*50)
        
        # Launch the demo
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to launch demo: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
        return True
    except Exception as e:
        print(f"❌ Unexpected error launching demo: {e}")
        return False


def main():
    """Main launcher function."""
    print("🎬 S3Vector Demo Launcher with Resource Management")
    print("=" * 60)
    
    # Check demo readiness
    if not check_demo_readiness():
        print("\n❌ Demo is not ready to launch. Please check the issues above.")
        return False
    
    # Show resource summary
    show_resource_summary()
    
    # Ask user if they want to proceed
    print("\n" + "="*60)
    proceed = input("🚀 Ready to launch the demo? (y/n): ").lower().strip()
    
    if proceed in ['y', 'yes']:
        return launch_demo()
    else:
        print("👋 Demo launch cancelled by user")
        return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
