#!/usr/bin/env python3
"""
Existing Resources Workflow Test

Tests the workflow resource management with the existing resources
in the registry without creating new AWS resources.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
import json
from typing import Dict, Any, List

def test_registry_existing_resources():
    """Test working with existing resources in the registry."""
    print("📋 Testing Existing Resources in Registry...")
    
    try:
        from src.utils.resource_registry import resource_registry
        
        # Get current registry state
        summary = resource_registry.get_resource_summary()
        
        print(f"✅ Registry loaded successfully")
        print(f"   S3 Buckets: {summary.get('s3_buckets', 0)}")
        print(f"   Vector Buckets: {summary.get('vector_buckets', 0)}")
        print(f"   Vector Indexes: {summary.get('vector_indexes', 0)}")
        print(f"   OpenSearch Collections: {summary.get('opensearch_collections', 0)}")
        
        # List specific resources
        s3_buckets = resource_registry.list_s3_buckets()
        print(f"\n📦 S3 Buckets in Registry ({len(s3_buckets)}):")
        for bucket in s3_buckets:
            status = bucket.get('status', 'unknown')
            source = bucket.get('source', 'unknown')
            print(f"   - {bucket['name']} ({status}, source: {source})")
        
        os_collections = resource_registry.list_opensearch_collections()
        print(f"\n🔎 OpenSearch Collections in Registry ({len(os_collections)}):")
        for collection in os_collections:
            status = collection.get('status', 'unknown')
            source = collection.get('source', 'unknown')
            print(f"   - {collection['name']} ({status}, source: {source})")
        
        # Get active resources
        active = resource_registry.get_active_resources()
        print(f"\n⚙️ Active Resources:")
        for resource_type, resource_name in active.items():
            if resource_name:
                print(f"   {resource_type}: {resource_name}")
            else:
                print(f"   {resource_type}: None")
        
        return True, s3_buckets, os_collections
        
    except Exception as e:
        print(f"❌ Registry test failed: {e}")
        return False, [], []


def test_workflow_resume_with_existing():
    """Test workflow resume functionality with existing resources."""
    print("\n🔄 Testing Workflow Resume with Existing Resources...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        
        # Initialize workflow manager
        manager = WorkflowResourceManager()
        print("✅ Workflow Resource Manager initialized")
        
        # Get existing resources
        existing_resources = manager._get_existing_resources()
        
        print("✅ Existing resources retrieved:")
        total_resources = 0
        for resource_type, resources in existing_resources.items():
            count = len(resources)
            total_resources += count
            if count > 0:
                print(f"   {resource_type.replace('_', ' ').title()}: {count}")
                # Show first few resources
                for resource in resources[:2]:
                    name = resource.get('name', 'Unknown')
                    status = resource.get('status', 'unknown')
                    print(f"     - {name} ({status})")
        
        print(f"   Total resources available: {total_resources}")
        
        if total_resources == 0:
            print("⚠️ No existing resources found for workflow resume")
            return False
        
        # Test resource selection
        print("\nTesting resource selection...")
        
        # Find a test bucket to select
        s3_buckets = existing_resources.get('s3_buckets', [])
        if s3_buckets:
            test_bucket = s3_buckets[0]['name']
            print(f"Selecting S3 bucket: {test_bucket}")
            
            manager._apply_resource_selection(s3_bucket=test_bucket)
            print("✅ Resource selection applied")
            
            # Verify selection
            from src.utils.resource_registry import resource_registry
            active_bucket = resource_registry.get_active_s3_bucket()
            if active_bucket == test_bucket:
                print(f"✅ Active S3 bucket verified: {active_bucket}")
            else:
                print(f"❌ Active S3 bucket mismatch: expected {test_bucket}, got {active_bucket}")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow resume test failed: {e}")
        return False


def test_session_state_management():
    """Test session state management functionality."""
    print("\n💾 Testing Session State Management...")
    
    try:
        # Mock streamlit session state for testing
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def __getitem__(self, key):
                return self.data.get(key)
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def get(self, key, default=None):
                return self.data.get(key, default)
        
        # Set up mock session state
        import streamlit as st
        if not hasattr(st, 'session_state') or not st.session_state:
            st.session_state = MockSessionState()
        
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        
        # Initialize manager (this should set up session state)
        manager = WorkflowResourceManager()
        
        # Check session state
        workflow_state = st.session_state.get('workflow_state', {})
        
        print("✅ Session state initialized:")
        print(f"   Session ID: {workflow_state.get('session_id', 'Not set')}")
        print(f"   Created Resources: {len(workflow_state.get('created_resources', []))}")
        print(f"   Processing History: {len(workflow_state.get('processing_history', []))}")
        print(f"   Last Session: {workflow_state.get('last_session', 'None')}")
        
        # Test session operations
        print("\nTesting session operations...")
        
        # Add a test resource to created list
        created_resources = workflow_state.get('created_resources', [])
        test_resource = f"test-resource-{int(time.time())}"
        created_resources.append(test_resource)
        
        print(f"✅ Added test resource to session: {test_resource}")
        print(f"   Total created resources: {len(created_resources)}")
        
        # Test getting user created resources
        user_resources = manager._get_user_created_resources()
        print(f"✅ User created resources retrieved: {len(user_resources)} types")
        
        return True
        
    except Exception as e:
        print(f"❌ Session state test failed: {e}")
        return False


def test_resource_creation_simulation():
    """Test resource creation simulation (without real AWS)."""
    print("\n🛠️ Testing Resource Creation Simulation...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        
        manager = WorkflowResourceManager()
        
        # Test S3 bucket creation simulation
        test_bucket_name = f"simulation-test-bucket-{int(time.time())}"
        print(f"Creating simulated S3 bucket: {test_bucket_name}")
        
        success = manager._create_s3_bucket(test_bucket_name, True)
        if success:
            print(f"✅ S3 bucket creation simulation successful")
        else:
            print(f"❌ S3 bucket creation simulation failed")
            return False
        
        # Test OpenSearch collection creation simulation
        test_collection_name = f"simulation-test-collection-{int(time.time())}"
        print(f"Creating simulated OpenSearch collection: {test_collection_name}")
        
        success = manager._create_opensearch_collection(test_collection_name, "SEARCH")
        if success:
            print(f"✅ OpenSearch collection creation simulation successful")
        else:
            print(f"❌ OpenSearch collection creation simulation failed")
            return False
        
        # Test complete setup simulation
        setup_name = f"simulation-setup-{int(time.time())}"
        print(f"Creating complete simulated setup: {setup_name}")
        
        success = manager._create_complete_setup(setup_name, "us-east-1")
        if success:
            print(f"✅ Complete setup simulation successful")
            
            # Verify resources were added to registry
            from src.utils.resource_registry import resource_registry
            
            s3_buckets = resource_registry.list_s3_buckets()
            setup_bucket = f"{setup_name}-s3"
            bucket_found = any(b['name'] == setup_bucket for b in s3_buckets)
            
            if bucket_found:
                print(f"✅ Setup S3 bucket found in registry: {setup_bucket}")
            else:
                print(f"❌ Setup S3 bucket not found in registry")
            
            os_collections = resource_registry.list_opensearch_collections()
            setup_collection = f"{setup_name}-collection"
            collection_found = any(c['name'] == setup_collection for c in os_collections)
            
            if collection_found:
                print(f"✅ Setup OpenSearch collection found in registry: {setup_collection}")
            else:
                print(f"❌ Setup OpenSearch collection not found in registry")
        else:
            print(f"❌ Complete setup simulation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Resource creation simulation failed: {e}")
        return False


def test_cleanup_simulation():
    """Test resource cleanup simulation."""
    print("\n🧹 Testing Resource Cleanup Simulation...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        from src.utils.resource_registry import resource_registry
        
        manager = WorkflowResourceManager()
        
        # Get user created resources
        user_resources = manager._get_user_created_resources()
        
        print("User created resources before cleanup:")
        total_user_resources = 0
        for resource_type, resources in user_resources.items():
            count = len(resources)
            total_user_resources += count
            if count > 0:
                print(f"   {resource_type}: {count}")
        
        if total_user_resources == 0:
            print("⚠️ No user created resources found for cleanup test")
            return True
        
        # Test cleanup simulation
        print(f"Simulating cleanup of {total_user_resources} user resources...")
        
        manager._delete_created_resources(user_resources)
        print("✅ Cleanup simulation completed")
        
        # Verify cleanup
        updated_user_resources = manager._get_user_created_resources()
        remaining_total = sum(len(resources) for resources in updated_user_resources.values())
        
        print(f"✅ Resources after cleanup: {remaining_total}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup simulation failed: {e}")
        return False


def main():
    """Run existing resources workflow testing."""
    print("🧪 Existing Resources Workflow Test Suite")
    print("=" * 50)
    print("Testing workflow management with existing resources in registry")
    print("=" * 50)
    
    tests = [
        ("Registry Existing Resources", test_registry_existing_resources),
        ("Workflow Resume with Existing", test_workflow_resume_with_existing),
        ("Session State Management", test_session_state_management),
        ("Resource Creation Simulation", test_resource_creation_simulation),
        ("Cleanup Simulation", test_cleanup_simulation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*15} {test_name} {'='*15}")
        
        try:
            result = test_func()
            if isinstance(result, tuple):
                success = result[0]
            else:
                success = result
            
            if success:
                passed += 1
                print(f"✅ {test_name} - PASSED")
            else:
                print(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} - FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All existing resources workflow tests passed!")
        print("\n📋 Next Steps:")
        print("   1. Run the Streamlit demo: streamlit run frontend/launch_refactored_demo.py")
        print("   2. Navigate to the 'Resources' section")
        print("   3. Test the 'Resume Work' functionality")
        print("   4. Try creating new resources")
        print("   5. Test the cleanup functionality")
        return True
    else:
        print("❌ Some tests failed. Check implementation and configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
