#!/usr/bin/env python3
"""
Test script for improved resource deletion functionality.

This script tests the enhanced deletion logic that:
1. Handles already-deleted resources gracefully (idempotent)
2. Updates registry before AWS API calls
3. Provides better error messaging
4. Auto-deletes dependent resources when possible
"""

import sys
from pathlib import Path
import time
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logging_config import get_logger
from src.utils.resource_registry import resource_registry

# Mock Streamlit for testing
class MockStreamlit:
    @staticmethod
    def info(msg): print(f"[INFO] {msg}")
    @staticmethod
    def success(msg): print(f"[SUCCESS] {msg}")
    @staticmethod
    def warning(msg): print(f"[WARNING] {msg}")
    @staticmethod
    def error(msg): print(f"[ERROR] {msg}")

# Replace streamlit import in workflow manager
sys.modules['streamlit'] = MockStreamlit()

from frontend.components.workflow_resource_manager import WorkflowResourceManager

logger = get_logger(__name__)


class TestImprovedResourceDeletion:
    """Test improved resource deletion functionality."""
    
    def __init__(self):
        """Initialize test environment."""
        self.test_prefix = f"test-deletion-{int(time.time())}"
        self.test_results = {
            "deletion_tests": [],
            "registry_tests": [],
            "idempotency_tests": []
        }
        
        # Initialize workflow resource manager
        try:
            self.workflow_manager = WorkflowResourceManager()
            print("✅ Workflow resource manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize workflow resource manager: {e}")
            raise
    
    def test_s3vector_bucket_deletion_idempotency(self):
        """Test that S3Vector bucket deletion is idempotent."""
        test_bucket_name = f"{self.test_prefix}-bucket-idempotent"
        
        print(f"\n=== Testing S3Vector Bucket Deletion Idempotency ===")
        print(f"Test bucket: {test_bucket_name}")
        
        try:
            # Test 1: Delete non-existent bucket (should succeed)
            print(f"Test 1: Deleting non-existent bucket...")
            result1 = self.workflow_manager.delete_s3vector_bucket(test_bucket_name)
            assert result1 == True, "Non-existent bucket deletion should return True (idempotent)"
            print("✅ Non-existent bucket deletion handled gracefully")
            
            # Test 2: Delete the same bucket again (should still succeed)
            print(f"Test 2: Deleting the same non-existent bucket again...")
            result2 = self.workflow_manager.delete_s3vector_bucket(test_bucket_name)
            assert result2 == True, "Second deletion should also return True (idempotent)"
            print("✅ Repeated deletion handled gracefully")
            
            self.test_results["idempotency_tests"].append({
                "test": "s3vector_bucket_deletion",
                "passed": True,
                "details": "Both deletion attempts returned True for non-existent bucket"
            })
            
            return True
            
        except Exception as e:
            print(f"❌ S3Vector bucket deletion idempotency test failed: {e}")
            self.test_results["idempotency_tests"].append({
                "test": "s3vector_bucket_deletion",
                "passed": False,
                "error": str(e)
            })
            return False
    
    def test_s3vector_index_deletion_idempotency(self):
        """Test that S3Vector index deletion is idempotent."""
        test_bucket_name = f"{self.test_prefix}-bucket-for-index"
        test_index_name = f"{self.test_prefix}-index-idempotent"
        
        print(f"\n=== Testing S3Vector Index Deletion Idempotency ===")
        print(f"Test bucket: {test_bucket_name}")
        print(f"Test index: {test_index_name}")
        
        try:
            # Test 1: Delete non-existent index (should succeed)
            print(f"Test 1: Deleting non-existent index...")
            result1 = self.workflow_manager.delete_s3vector_index(test_bucket_name, test_index_name)
            assert result1 == True, "Non-existent index deletion should return True (idempotent)"
            print("✅ Non-existent index deletion handled gracefully")
            
            # Test 2: Delete the same index again (should still succeed)
            print(f"Test 2: Deleting the same non-existent index again...")
            result2 = self.workflow_manager.delete_s3vector_index(test_bucket_name, test_index_name)
            assert result2 == True, "Second deletion should also return True (idempotent)"
            print("✅ Repeated index deletion handled gracefully")
            
            self.test_results["idempotency_tests"].append({
                "test": "s3vector_index_deletion",
                "passed": True,
                "details": "Both deletion attempts returned True for non-existent index"
            })
            
            return True
            
        except Exception as e:
            print(f"❌ S3Vector index deletion idempotency test failed: {e}")
            self.test_results["idempotency_tests"].append({
                "test": "s3vector_index_deletion",
                "passed": False,
                "error": str(e)
            })
            return False
    
    def test_opensearch_collection_deletion_idempotency(self):
        """Test that OpenSearch collection deletion is idempotent."""
        test_collection_name = f"{self.test_prefix}-collection-idempotent"
        
        print(f"\n=== Testing OpenSearch Collection Deletion Idempotency ===")
        print(f"Test collection: {test_collection_name}")
        
        try:
            # Test 1: Delete non-existent collection (should succeed)
            print(f"Test 1: Deleting non-existent collection...")
            result1 = self.workflow_manager.delete_opensearch_collection(test_collection_name)
            assert result1 == True, "Non-existent collection deletion should return True (idempotent)"
            print("✅ Non-existent collection deletion handled gracefully")
            
            # Test 2: Delete the same collection again (should still succeed)
            print(f"Test 2: Deleting the same non-existent collection again...")
            result2 = self.workflow_manager.delete_opensearch_collection(test_collection_name)
            assert result2 == True, "Second deletion should also return True (idempotent)"
            print("✅ Repeated collection deletion handled gracefully")
            
            self.test_results["idempotency_tests"].append({
                "test": "opensearch_collection_deletion",
                "passed": True,
                "details": "Both deletion attempts returned True for non-existent collection"
            })
            
            return True
            
        except Exception as e:
            print(f"❌ OpenSearch collection deletion idempotency test failed: {e}")
            self.test_results["idempotency_tests"].append({
                "test": "opensearch_collection_deletion",
                "passed": False,
                "error": str(e)
            })
            return False
    
    def test_registry_update_during_deletion(self):
        """Test that registry is updated during deletion attempts."""
        test_bucket_name = f"{self.test_prefix}-registry-test"
        
        print(f"\n=== Testing Registry Update During Deletion ===")
        print(f"Test bucket: {test_bucket_name}")
        
        try:
            # First add a fake entry to the registry
            resource_registry.log_vector_bucket_created(
                bucket_name=test_bucket_name,
                region="us-east-1",
                source="test_deletion"
            )
            
            # Verify it's in the registry
            buckets_before = resource_registry.list_vector_buckets()
            test_bucket_in_registry = any(b.get('name') == test_bucket_name for b in buckets_before)
            assert test_bucket_in_registry, "Test bucket should be in registry before deletion"
            print("✅ Test bucket added to registry")
            
            # Now delete the bucket (it doesn't exist in AWS, but should update registry)
            print("Attempting deletion (should update registry even if AWS bucket doesn't exist)...")
            result = self.workflow_manager.delete_s3vector_bucket(test_bucket_name)
            assert result == True, "Deletion should succeed and update registry"
            
            # Verify registry was updated
            buckets_after = resource_registry.list_vector_buckets()
            deleted_buckets = [b for b in buckets_after if b.get('name') == test_bucket_name and b.get('status') == 'deleted']
            assert len(deleted_buckets) > 0, "Bucket should be marked as deleted in registry"
            print("✅ Registry updated during deletion process")
            
            self.test_results["registry_tests"].append({
                "test": "registry_update_during_deletion",
                "passed": True,
                "details": "Registry correctly updated when deleting non-existent AWS resource"
            })
            
            return True
            
        except Exception as e:
            print(f"❌ Registry update test failed: {e}")
            self.test_results["registry_tests"].append({
                "test": "registry_update_during_deletion",
                "passed": False,
                "error": str(e)
            })
            return False
    
    def test_all_improvements(self):
        """Run all deletion improvement tests."""
        print("🚀 Starting Resource Deletion Improvement Tests")
        print("=" * 60)
        
        tests = [
            ("S3Vector Bucket Deletion Idempotency", self.test_s3vector_bucket_deletion_idempotency),
            ("S3Vector Index Deletion Idempotency", self.test_s3vector_index_deletion_idempotency),
            ("OpenSearch Collection Deletion Idempotency", self.test_opensearch_collection_deletion_idempotency),
            ("Registry Update During Deletion", self.test_registry_update_during_deletion)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                    print(f"✅ {test_name}: PASSED")
                else:
                    print(f"❌ {test_name}: FAILED")
            except Exception as e:
                print(f"💥 {test_name}: CRASHED - {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Resource deletion improvements are working correctly.")
        else:
            print(f"⚠️ {total_tests - passed_tests} tests failed. Review the issues above.")
        
        return passed_tests == total_tests


def main():
    """Main test execution."""
    try:
        tester = TestImprovedResourceDeletion()
        success = tester.test_all_improvements()
        
        if success:
            print("\n✅ All resource deletion improvements validated successfully!")
            return 0
        else:
            print("\n❌ Some deletion improvement tests failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())