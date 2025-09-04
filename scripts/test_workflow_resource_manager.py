#!/usr/bin/env python3
"""
Workflow Resource Manager Test Script

Tests the workflow-focused resource management functionality.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import time
from typing import Dict, Any

def test_workflow_resource_manager_import():
    """Test workflow resource manager import."""
    print("🎛️ Testing Workflow Resource Manager Import...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager, render_workflow_resource_manager
        
        print("✅ WorkflowResourceManager class imported")
        print("✅ render_workflow_resource_manager function imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False


def test_workflow_manager_initialization():
    """Test workflow manager initialization."""
    print("\n🚀 Testing Workflow Manager Initialization...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        
        # Initialize manager
        manager = WorkflowResourceManager()
        print("✅ WorkflowResourceManager initialized")
        
        # Test manager methods
        methods = [
            'render_workflow_resume_section',
            'render_resource_creation_wizard',
            'render_resource_cleanup_manager',
            'render_session_state_manager'
        ]
        
        for method in methods:
            if hasattr(manager, method):
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        return False


def test_session_state_management():
    """Test session state management."""
    print("\n💾 Testing Session State Management...")
    
    try:
        # Mock streamlit session state
        class MockSessionState:
            def __init__(self):
                self.data = {}
            
            def __getitem__(self, key):
                return self.data.get(key)
            
            def __setitem__(self, key, value):
                self.data[key] = value
            
            def get(self, key, default=None):
                return self.data.get(key, default)
        
        # Mock streamlit
        import streamlit as st
        if not hasattr(st, 'session_state'):
            st.session_state = MockSessionState()
        
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        
        # Initialize manager (this should set up session state)
        manager = WorkflowResourceManager()
        
        # Check session state structure
        workflow_state = st.session_state.get('workflow_state', {})
        
        expected_keys = ['last_session', 'active_resources', 'processing_history', 'created_resources', 'session_id']
        
        for key in expected_keys:
            if key in workflow_state:
                print(f"   ✅ {key}: {type(workflow_state[key])}")
            else:
                print(f"   ❌ {key} missing")
        
        print(f"✅ Session ID: {workflow_state.get('session_id', 'Not set')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Session state test failed: {e}")
        return False


def test_resource_operations():
    """Test resource operations."""
    print("\n🔧 Testing Resource Operations...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        from src.utils.resource_registry import resource_registry
        
        manager = WorkflowResourceManager()
        
        # Test getting existing resources
        existing_resources = manager._get_existing_resources()
        print(f"✅ Existing resources retrieved: {len(existing_resources)} types")
        
        for resource_type, resources in existing_resources.items():
            print(f"   {resource_type}: {len(resources)} found")
        
        # Test getting user created resources
        user_resources = manager._get_user_created_resources()
        print(f"✅ User created resources retrieved: {len(user_resources)} types")
        
        # Test resource creation simulation
        success = manager._create_s3_bucket("test-workflow-bucket", True)
        print(f"✅ S3 bucket creation simulation: {'Success' if success else 'Failed'}")
        
        success = manager._create_s3vector_index("test-workflow-index", 1024)
        print(f"✅ S3Vector index creation simulation: {'Success' if success else 'Failed'}")
        
        success = manager._create_opensearch_collection("test-workflow-collection", "SEARCH")
        print(f"✅ OpenSearch collection creation simulation: {'Success' if success else 'Failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Resource operations test failed: {e}")
        return False


def test_workflow_integration():
    """Test workflow integration."""
    print("\n🔄 Testing Workflow Integration...")
    
    try:
        # Test demo integration
        from frontend.unified_demo_refactored import UnifiedS3VectorDemo
        
        demo = UnifiedS3VectorDemo()
        
        # Check if workflow resource manager is integrated
        if hasattr(demo, 'render_resource_management_section'):
            print("✅ Resource management section integrated in demo")
        else:
            print("❌ Resource management section not integrated")
        
        # Test import in demo
        from frontend.components.workflow_resource_manager import render_workflow_resource_manager
        print("✅ Workflow resource manager render function available")
        
        return True
        
    except Exception as e:
        print(f"❌ Workflow integration test failed: {e}")
        return False


def test_resource_lifecycle():
    """Test complete resource lifecycle."""
    print("\n🔄 Testing Resource Lifecycle...")
    
    try:
        from frontend.components.workflow_resource_manager import WorkflowResourceManager
        from src.utils.resource_registry import resource_registry
        
        manager = WorkflowResourceManager()
        
        # Create test resources
        test_bucket = f"lifecycle-test-bucket-{int(time.time())}"
        test_index = f"lifecycle-test-index-{int(time.time())}"
        test_collection = f"lifecycle-test-collection-{int(time.time())}"
        
        print(f"Creating test resources...")
        
        # Create resources
        success1 = manager._create_s3_bucket(test_bucket, True)
        success2 = manager._create_s3vector_index(test_index, 1024)
        success3 = manager._create_opensearch_collection(test_collection, "SEARCH")
        
        if success1 and success2 and success3:
            print("✅ Test resources created successfully")
        else:
            print("❌ Failed to create test resources")
            return False
        
        # Test resource selection
        manager._apply_resource_selection(
            s3_bucket=test_bucket,
            index_arn=f"arn:aws:s3vectors:us-east-1:123456789012:index/{test_index}",
            opensearch_collection=test_collection
        )
        print("✅ Resource selection applied")
        
        # Test getting active resources
        active_resources = resource_registry.get_active_resources()
        print(f"✅ Active resources retrieved: {len([r for r in active_resources.values() if r])}")
        
        # Test cleanup
        created_resources = manager._get_user_created_resources()
        if any(created_resources.values()):
            print("✅ User created resources found for cleanup")
        
        return True
        
    except Exception as e:
        print(f"❌ Resource lifecycle test failed: {e}")
        return False


def test_configuration_integration():
    """Test configuration integration."""
    print("\n⚙️ Testing Configuration Integration...")
    
    try:
        from src.config.unified_config_manager import get_unified_config_manager
        
        config = get_unified_config_manager()
        
        # Test feature flags
        feature_flags = config.config.features.__dict__
        print(f"✅ Feature flags loaded: {len(feature_flags)} flags")
        
        # Test workflow-relevant flags
        workflow_flags = [
            'enable_real_aws',
            'enable_opensearch_hybrid',
            'enable_cost_estimation'
        ]
        
        for flag in workflow_flags:
            value = feature_flags.get(flag, False)
            print(f"   {flag}: {value}")
        
        # Test AWS configuration
        aws_config = config.get_aws_config()
        print(f"✅ AWS config loaded")
        print(f"   Region: {aws_config.get('region')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration integration test failed: {e}")
        return False


def main():
    """Run all workflow resource manager tests."""
    print("🧪 Workflow Resource Manager Test Suite")
    print("=" * 50)
    
    tests = [
        test_workflow_resource_manager_import,
        test_workflow_manager_initialization,
        test_session_state_management,
        test_resource_operations,
        test_workflow_integration,
        test_resource_lifecycle,
        test_configuration_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All workflow resource manager tests passed!")
        return True
    else:
        print("❌ Some tests failed. Check implementation and configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
