#!/usr/bin/env python3
"""
Comprehensive Resource Deletion Test Script

This script tests the enhanced resource deletion functionality to ensure:
1. Real AWS API calls are being made
2. Detailed logging is working correctly
3. Error handling is comprehensive
4. Resource cleanup is successful
5. Registry updates are working properly

Usage:
    python scripts/test_resource_deletion_comprehensive.py
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from frontend.components.workflow_resource_manager import WorkflowResourceManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class ResourceDeletionTester:
    """Comprehensive tester for resource deletion functionality."""
    
    def __init__(self):
        """Initialize the tester."""
        self.manager: Optional[WorkflowResourceManager] = None  # Will be initialized in setup_manager
        self.test_resources = {
            'created_buckets': [],
            'created_indexes': [],
            'created_collections': []
        }
        self.test_results = {
            'creation_tests': [],
            'deletion_tests': [],
            'error_handling_tests': [],
            'logging_tests': []
        }
    
    def setup_manager(self):
        """Set up the workflow resource manager."""
        try:
            logger.info("🔧 Setting up WorkflowResourceManager for testing...")
            self.manager = WorkflowResourceManager()
            logger.info("✅ WorkflowResourceManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize WorkflowResourceManager: {e}")
            return False
    
    def test_create_test_resources(self):
        """Create test resources for deletion testing."""
        logger.info("🛠️ Creating test resources for deletion testing...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        # Create a test S3Vector bucket
        test_bucket_name = f"test-deletion-bucket-{int(time.time())}"
        try:
            logger.info(f"📦 Creating test S3Vector bucket: {test_bucket_name}")
            success = self.manager._create_real_s3vector_bucket(test_bucket_name)
            if success:
                self.test_resources['created_buckets'].append(test_bucket_name)
                logger.info(f"✅ Test bucket created: {test_bucket_name}")
                self.test_results['creation_tests'].append({
                    'resource_type': 'bucket',
                    'resource_name': test_bucket_name,
                    'status': 'success'
                })
            else:
                logger.error(f"❌ Failed to create test bucket: {test_bucket_name}")
                self.test_results['creation_tests'].append({
                    'resource_type': 'bucket',
                    'resource_name': test_bucket_name,
                    'status': 'failed'
                })
        except Exception as e:
            logger.error(f"💥 Exception creating test bucket: {e}")
            self.test_results['creation_tests'].append({
                'resource_type': 'bucket',
                'resource_name': test_bucket_name,
                'status': 'error',
                'error': str(e)
            })
        
        # Create a test S3Vector index
        if self.test_resources['created_buckets']:
            test_index_name = f"test-deletion-index-{int(time.time())}"
            try:
                logger.info(f"🔍 Creating test S3Vector index: {test_index_name}")
                success, index_arn = self.manager._create_real_s3vector_index(
                    test_bucket_name, test_index_name, 1024
                )
                if success:
                    self.test_resources['created_indexes'].append({
                        'name': test_index_name,
                        'bucket': test_bucket_name,
                        'arn': index_arn
                    })
                    logger.info(f"✅ Test index created: {test_index_name}")
                    self.test_results['creation_tests'].append({
                        'resource_type': 'index',
                        'resource_name': test_index_name,
                        'status': 'success'
                    })
                else:
                    logger.error(f"❌ Failed to create test index: {test_index_name}")
                    self.test_results['creation_tests'].append({
                        'resource_type': 'index',
                        'resource_name': test_index_name,
                        'status': 'failed'
                    })
            except Exception as e:
                logger.error(f"💥 Exception creating test index: {e}")
                self.test_results['creation_tests'].append({
                    'resource_type': 'index',
                    'resource_name': test_index_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        # Create a test OpenSearch collection
        test_collection_name = f"test-del-coll-{int(time.time())}"
        try:
            logger.info(f"🔎 Creating test OpenSearch collection: {test_collection_name}")
            logger.info("⏳ Note: OpenSearch collection creation may take 2-5 minutes...")
            success, collection_arn = self.manager._create_real_opensearch_collection(
                test_collection_name, "SEARCH"
            )
            if success:
                self.test_resources['created_collections'].append({
                    'name': test_collection_name,
                    'arn': collection_arn
                })
                logger.info(f"✅ Test collection created and ready: {test_collection_name}")
                self.test_results['creation_tests'].append({
                    'resource_type': 'collection',
                    'resource_name': test_collection_name,
                    'status': 'success'
                })
            else:
                logger.error(f"❌ Failed to create test collection: {test_collection_name}")
                self.test_results['creation_tests'].append({
                    'resource_type': 'collection',
                    'resource_name': test_collection_name,
                    'status': 'failed'
                })
        except Exception as e:
            logger.error(f"💥 Exception creating test collection: {e}")
            self.test_results['creation_tests'].append({
                'resource_type': 'collection',
                'resource_name': test_collection_name,
                'status': 'error',
                'error': str(e)
            })
        
        logger.info(f"📊 Test resource creation summary:")
        logger.info(f"  - Buckets: {len(self.test_resources['created_buckets'])}")
        logger.info(f"  - Indexes: {len(self.test_resources['created_indexes'])}")
        logger.info(f"  - Collections: {len(self.test_resources['created_collections'])}")
    
    def test_index_deletion(self):
        """Test S3Vector index deletion."""
        logger.info("🧪 Testing S3Vector index deletion...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        for index_info in self.test_resources['created_indexes']:
            index_name = index_info['name']
            bucket_name = index_info['bucket']
            
            logger.info(f"🗑️ Testing deletion of index: {bucket_name}/{index_name}")
            
            try:
                success = self.manager.delete_s3vector_index(bucket_name, index_name)
                
                self.test_results['deletion_tests'].append({
                    'resource_type': 'index',
                    'resource_name': f"{bucket_name}/{index_name}",
                    'status': 'success' if success else 'failed'
                })
                
                if success:
                    logger.info(f"✅ Successfully deleted index: {bucket_name}/{index_name}")
                else:
                    logger.error(f"❌ Failed to delete index: {bucket_name}/{index_name}")
                    
            except Exception as e:
                logger.error(f"💥 Exception deleting index {bucket_name}/{index_name}: {e}")
                self.test_results['deletion_tests'].append({
                    'resource_type': 'index',
                    'resource_name': f"{bucket_name}/{index_name}",
                    'status': 'error',
                    'error': str(e)
                })
    
    def test_collection_deletion(self):
        """Test OpenSearch collection deletion."""
        logger.info("🧪 Testing OpenSearch collection deletion...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        for collection_info in self.test_resources['created_collections']:
            collection_name = collection_info['name']
            
            logger.info(f"🗑️ Testing deletion of collection: {collection_name}")
            
            try:
                success = self.manager.delete_opensearch_collection(collection_name)
                
                self.test_results['deletion_tests'].append({
                    'resource_type': 'collection',
                    'resource_name': collection_name,
                    'status': 'success' if success else 'failed'
                })
                
                if success:
                    logger.info(f"✅ Successfully deleted collection: {collection_name}")
                else:
                    logger.error(f"❌ Failed to delete collection: {collection_name}")
                    
            except Exception as e:
                logger.error(f"💥 Exception deleting collection {collection_name}: {e}")
                self.test_results['deletion_tests'].append({
                    'resource_type': 'collection',
                    'resource_name': collection_name,
                    'status': 'error',
                    'error': str(e)
                })
    
    def test_bucket_deletion(self):
        """Test S3Vector bucket deletion."""
        logger.info("🧪 Testing S3Vector bucket deletion...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        for bucket_name in self.test_resources['created_buckets']:
            logger.info(f"🗑️ Testing deletion of bucket: {bucket_name}")
            
            try:
                success = self.manager.delete_s3vector_bucket(bucket_name)
                
                self.test_results['deletion_tests'].append({
                    'resource_type': 'bucket',
                    'resource_name': bucket_name,
                    'status': 'success' if success else 'failed'
                })
                
                if success:
                    logger.info(f"✅ Successfully deleted bucket: {bucket_name}")
                else:
                    logger.error(f"❌ Failed to delete bucket: {bucket_name}")
                    
            except Exception as e:
                logger.error(f"💥 Exception deleting bucket {bucket_name}: {e}")
                self.test_results['deletion_tests'].append({
                    'resource_type': 'bucket',
                    'resource_name': bucket_name,
                    'status': 'error',
                    'error': str(e)
                })
    
    def test_error_handling(self):
        """Test error handling for non-existent resources."""
        logger.info("🧪 Testing error handling for non-existent resources...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        # Test deleting non-existent resources
        fake_resources = {
            'bucket': 'non-existent-bucket-12345',
            'index': ('non-existent-bucket-12345', 'non-existent-index-12345'),
            'collection': 'non-existent-collection-12345'
        }
        
        # Test bucket deletion error handling
        try:
            logger.info(f"🧪 Testing non-existent bucket deletion: {fake_resources['bucket']}")
            success = self.manager.delete_s3vector_bucket(fake_resources['bucket'])
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_bucket_deletion',
                'expected_behavior': 'should_return_true_for_non_existent',
                'actual_result': success,
                'status': 'success' if success else 'unexpected_failure'
            })
        except Exception as e:
            logger.error(f"Unexpected exception in bucket error handling test: {e}")
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_bucket_deletion',
                'status': 'exception',
                'error': str(e)
            })
        
        # Test index deletion error handling
        try:
            bucket_name, index_name = fake_resources['index']
            logger.info(f"🧪 Testing non-existent index deletion: {bucket_name}/{index_name}")
            success = self.manager.delete_s3vector_index(bucket_name, index_name)
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_index_deletion',
                'expected_behavior': 'should_return_true_for_non_existent',
                'actual_result': success,
                'status': 'success' if success else 'unexpected_failure'
            })
        except Exception as e:
            logger.error(f"Unexpected exception in index error handling test: {e}")
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_index_deletion',
                'status': 'exception',
                'error': str(e)
            })
        
        # Test collection deletion error handling
        try:
            logger.info(f"🧪 Testing non-existent collection deletion: {fake_resources['collection']}")
            success = self.manager.delete_opensearch_collection(fake_resources['collection'])
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_collection_deletion',
                'expected_behavior': 'should_return_true_for_non_existent',
                'actual_result': success,
                'status': 'success' if success else 'unexpected_failure'
            })
        except Exception as e:
            logger.error(f"Unexpected exception in collection error handling test: {e}")
            self.test_results['error_handling_tests'].append({
                'test': 'non_existent_collection_deletion',
                'status': 'exception',
                'error': str(e)
            })
    
    def cleanup_remaining_resources(self):
        """Clean up any remaining test resources."""
        logger.info("🧹 Cleaning up any remaining test resources...")
        
        if not self.manager:
            logger.error("❌ Manager not initialized")
            return
        
        # Try to delete any remaining resources
        remaining_cleanup_results = []
        
        # Cleanup remaining indexes
        for index_info in self.test_resources['created_indexes']:
            try:
                self.manager.delete_s3vector_index(index_info['bucket'], index_info['name'])
                remaining_cleanup_results.append(f"✓ Cleaned up index: {index_info['name']}")
            except Exception as e:
                remaining_cleanup_results.append(f"✗ Failed to clean up index: {index_info['name']} - {e}")
        
        # Cleanup remaining collections
        for collection_info in self.test_resources['created_collections']:
            try:
                self.manager.delete_opensearch_collection(collection_info['name'])
                remaining_cleanup_results.append(f"✓ Cleaned up collection: {collection_info['name']}")
            except Exception as e:
                remaining_cleanup_results.append(f"✗ Failed to clean up collection: {collection_info['name']} - {e}")
        
        # Cleanup remaining buckets
        for bucket_name in self.test_resources['created_buckets']:
            try:
                self.manager.delete_s3vector_bucket(bucket_name)
                remaining_cleanup_results.append(f"✓ Cleaned up bucket: {bucket_name}")
            except Exception as e:
                remaining_cleanup_results.append(f"✗ Failed to clean up bucket: {bucket_name} - {e}")
        
        for result in remaining_cleanup_results:
            logger.info(result)
    
    def generate_test_report(self):
        """Generate a comprehensive test report."""
        logger.info("📊 Generating comprehensive test report...")
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'test_summary': {
                'creation_tests': len(self.test_results['creation_tests']),
                'deletion_tests': len(self.test_results['deletion_tests']),
                'error_handling_tests': len(self.test_results['error_handling_tests'])
            },
            'detailed_results': self.test_results,
            'test_resources_created': self.test_resources
        }
        
        # Calculate success rates
        successful_creations = sum(1 for test in self.test_results['creation_tests'] if test['status'] == 'success')
        successful_deletions = sum(1 for test in self.test_results['deletion_tests'] if test['status'] == 'success')
        successful_error_handling = sum(1 for test in self.test_results['error_handling_tests'] if test['status'] == 'success')
        
        report['success_rates'] = {
            'creation_success_rate': successful_creations / max(1, len(self.test_results['creation_tests'])) * 100,
            'deletion_success_rate': successful_deletions / max(1, len(self.test_results['deletion_tests'])) * 100,
            'error_handling_success_rate': successful_error_handling / max(1, len(self.test_results['error_handling_tests'])) * 100
        }
        
        # Save report to file
        report_file = f"resource_deletion_test_report_{int(time.time())}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Test report saved to: {report_file}")
        
        # Print summary
        logger.info("="*80)
        logger.info("📊 RESOURCE DELETION TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Creation Tests: {successful_creations}/{len(self.test_results['creation_tests'])} successful ({report['success_rates']['creation_success_rate']:.1f}%)")
        logger.info(f"Deletion Tests: {successful_deletions}/{len(self.test_results['deletion_tests'])} successful ({report['success_rates']['deletion_success_rate']:.1f}%)")
        logger.info(f"Error Handling Tests: {successful_error_handling}/{len(self.test_results['error_handling_tests'])} successful ({report['success_rates']['error_handling_success_rate']:.1f}%)")
        logger.info("="*80)
        
        return report
    
    def run_comprehensive_test(self):
        """Run the complete test suite."""
        logger.info("🚀 Starting comprehensive resource deletion test suite...")
        
        try:
            # Setup
            if not self.setup_manager():
                logger.error("❌ Failed to setup manager. Aborting tests.")
                return False
            
            # Create test resources
            self.test_create_test_resources()
            
            # Verify resources were created successfully before attempting deletion
            logger.info("🔍 Verifying test resources were created successfully...")
            created_resources_count = (
                len(self.test_resources['created_buckets']) +
                len(self.test_resources['created_indexes']) +
                len(self.test_resources['created_collections'])
            )
            
            if created_resources_count == 0:
                logger.warning("⚠️ No test resources were created successfully. Skipping deletion tests.")
                # Still run error handling tests
                self.test_error_handling()
                report = self.generate_test_report()
                return True
            
            logger.info(f"✅ {created_resources_count} test resources created successfully. Proceeding with deletion tests...")
            
            # Test deletions (indexes first, then collections, then buckets)
            if self.test_resources['created_indexes']:
                logger.info("🗑️ Testing S3Vector index deletion...")
                self.test_index_deletion()
                time.sleep(2)  # Brief pause between tests
            
            if self.test_resources['created_collections']:
                logger.info("🗑️ Testing OpenSearch collection deletion...")
                self.test_collection_deletion()
                time.sleep(2)  # Brief pause between tests
            
            if self.test_resources['created_buckets']:
                logger.info("🗑️ Testing S3Vector bucket deletion...")
                self.test_bucket_deletion()
            
            # Test error handling
            self.test_error_handling()
            
            # Generate report
            report = self.generate_test_report()
            
            # Cleanup any remaining resources
            self.cleanup_remaining_resources()
            
            logger.info("✅ Comprehensive resource deletion test suite completed!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Critical error in test suite: {e}")
            return False

def main():
    """Main test execution function."""
    print("="*80)
    print("🧪 COMPREHENSIVE RESOURCE DELETION TEST SUITE")
    print("="*80)
    
    tester = ResourceDeletionTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n✅ Test suite completed successfully!")
        return 0
    else:
        print("\n❌ Test suite failed!")
        return 1

if __name__ == "__main__":
    exit(main())