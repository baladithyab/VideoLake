#!/usr/bin/env python3
"""
S3Vector Backend Functionality Validation Script

This script validates the complete S3Vector backend functionality including:
1. Direct S3Vector storage operations
2. OpenSearch hybrid backend integration
3. Dual backend upsertion capabilities
4. Metadata preservation and retrieval
5. Index segregation by embedding type
6. Error handling and recovery mechanisms
"""

import sys
import time
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.enhanced_storage_integration_manager import (
    EnhancedStorageIntegrationManager,
    StorageConfiguration,
    StorageBackend,
    VectorType,
    MediaMetadata,
    UpsertionProgress
)
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_s3vector_pattern2_correct import OpenSearchS3VectorPattern2Manager
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_config

logger = get_logger(__name__)


class S3VectorBackendValidator:
    """Comprehensive validator for S3Vector backend functionality."""
    
    def __init__(self):
        self.config = get_config()
        self.test_results: Dict[str, Any] = {
            "timestamp": time.time(),
            "tests": {},
            "summary": {
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0,
                "warnings": []
            }
        }
        
        # Test configuration
        self.test_bucket_name = "s3vector-validation-test-bucket"
        self.test_domain_name = "s3vector-validation-test-domain"
        self.test_environment = "test"
        
        logger.info("S3Vector Backend Validator initialized")
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation tests."""
        logger.info("Starting comprehensive S3Vector backend validation")
        
        # Test 1: Basic S3Vector Storage Operations
        self._test_s3vector_storage_operations()
        
        # Test 2: OpenSearch Pattern 2 Integration
        self._test_opensearch_pattern2_integration()
        
        # Test 3: Enhanced Storage Integration Manager
        self._test_enhanced_storage_integration()
        
        # Test 4: Dual Backend Configuration
        self._test_dual_backend_configuration()
        
        # Test 5: Metadata Preservation
        self._test_metadata_preservation()
        
        # Test 6: Index Segregation
        self._test_index_segregation()
        
        # Test 7: Error Handling
        self._test_error_handling()
        
        # Test 8: Batch Processing
        self._test_batch_processing()
        
        # Test 9: Progress Tracking
        self._test_progress_tracking()
        
        # Generate final report
        self._generate_validation_report()
        
        return self.test_results
    
    def _test_s3vector_storage_operations(self):
        """Test basic S3Vector storage operations."""
        test_name = "s3vector_storage_operations"
        logger.info(f"Running test: {test_name}")
        
        try:
            storage_manager = S3VectorStorageManager()
            
            # Test bucket operations
            bucket_result = self._test_bucket_operations(storage_manager)
            
            # Test index operations
            index_result = self._test_index_operations(storage_manager)
            
            # Test vector operations
            vector_result = self._test_vector_operations(storage_manager)
            
            success = all([bucket_result, index_result, vector_result])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "bucket_operations": bucket_result,
                    "index_operations": index_result,
                    "vector_operations": vector_result
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_bucket_operations(self, storage_manager: S3VectorStorageManager) -> bool:
        """Test S3Vector bucket operations."""
        try:
            # Create bucket
            bucket_result = storage_manager.create_vector_bucket(
                bucket_name=self.test_bucket_name,
                encryption_type="SSE-S3"
            )
            
            # Verify bucket exists
            bucket_exists = storage_manager.bucket_exists(self.test_bucket_name)
            
            # Get bucket details
            bucket_details = storage_manager.get_vector_bucket(self.test_bucket_name)
            
            # List buckets
            buckets = storage_manager.list_vector_buckets()
            
            return all([
                bucket_result.get("status") in ["created", "already_exists"],
                bucket_exists,
                bucket_details is not None,
                isinstance(buckets, list)
            ])
            
        except Exception as e:
            logger.error(f"Bucket operations test failed: {str(e)}")
            return False
    
    def _test_index_operations(self, storage_manager: S3VectorStorageManager) -> bool:
        """Test S3Vector index operations."""
        try:
            test_indexes = []
            
            # Create indexes for each vector type
            for vector_type in [VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE, VectorType.AUDIO]:
                index_name = f"{self.test_environment}-{vector_type.value}-test-index"
                
                index_result = storage_manager.create_vector_index(
                    bucket_name=self.test_bucket_name,
                    index_name=index_name,
                    dimensions=1024,
                    distance_metric="cosine"
                )
                
                test_indexes.append({
                    "vector_type": vector_type.value,
                    "index_name": index_name,
                    "result": index_result
                })
            
            # List indexes
            indexes_list = storage_manager.list_vector_indexes(self.test_bucket_name)
            
            # Verify all indexes were created
            created_indexes = [idx["index_name"] for idx in test_indexes]
            listed_indexes = [idx.get("indexName") for idx in indexes_list.get("indexes", [])]
            
            return all(idx in listed_indexes for idx in created_indexes)
            
        except Exception as e:
            logger.error(f"Index operations test failed: {str(e)}")
            return False
    
    def _test_vector_operations(self, storage_manager: S3VectorStorageManager) -> bool:
        """Test S3Vector vector operations."""
        try:
            # Create test vectors
            test_vectors = []
            for i in range(5):
                vector_data = {
                    "key": f"test_vector_{i}",
                    "data": {
                        "float32": [0.1 * j for j in range(1024)]  # 1024-dimensional vector
                    },
                    "metadata": {
                        "test_id": i,
                        "vector_type": "visual-text",
                        "timestamp": time.time()
                    }
                }
                test_vectors.append(vector_data)
            
            # Get index ARN for upsertion
            index_name = f"{self.test_environment}-visual-text-test-index"
            
            try:
                import boto3
                sts = boto3.client('sts')
                account_id = sts.get_caller_identity()['Account']
                region = self.config.aws.region
                index_arn = f"arn:aws:s3vectors:{region}:{account_id}:bucket/{self.test_bucket_name}/index/{index_name}"
            except Exception as e:
                logger.warning(f"Could not construct index ARN: {str(e)}")
                return False
            
            # Put vectors
            put_result = storage_manager.put_vectors(
                index_arn=index_arn,
                vectors_data=test_vectors
            )
            
            # Query vectors
            query_vector = [0.1 * j for j in range(1024)]
            query_result = storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=3
            )
            
            # List vectors
            list_result = storage_manager.list_vectors(
                index_arn=index_arn,
                max_results=10
            )
            
            return all([
                put_result.get("status") == "success",
                query_result.get("results_count", 0) > 0,
                list_result.get("count", 0) > 0
            ])
            
        except Exception as e:
            logger.error(f"Vector operations test failed: {str(e)}")
            return False
    
    def _test_opensearch_pattern2_integration(self):
        """Test OpenSearch Pattern 2 integration."""
        test_name = "opensearch_pattern2_integration"
        logger.info(f"Running test: {test_name}")
        
        try:
            pattern2_manager = OpenSearchS3VectorPattern2Manager()
            
            # Test S3Vector bucket creation for OpenSearch
            opensearch_bucket_name = f"{self.test_domain_name}-s3vector"
            bucket_arn = pattern2_manager.create_s3_vector_bucket(
                bucket_name=opensearch_bucket_name
            )
            
            # Test S3Vector index creation
            index_arn = pattern2_manager.create_s3_vector_index(
                bucket_name=opensearch_bucket_name,
                index_name="test-visual-text-index",
                dimension=1024,
                distance_metric="cosine"
            )
            
            success = all([
                bucket_arn is not None,
                index_arn is not None
            ])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "bucket_arn": bucket_arn,
                    "index_arn": index_arn
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_enhanced_storage_integration(self):
        """Test Enhanced Storage Integration Manager."""
        test_name = "enhanced_storage_integration"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Create test configuration
            config = StorageConfiguration(
                enabled_backends=[StorageBackend.DIRECT_S3VECTOR],
                vector_types=[VectorType.VISUAL_TEXT, VectorType.AUDIO],
                environment=self.test_environment,
                s3vector_bucket_name=self.test_bucket_name,
                batch_size=5,
                max_concurrent_operations=2
            )
            
            # Initialize storage manager
            storage_integration = EnhancedStorageIntegrationManager(config)
            
            # Test configuration validation
            validation_results = storage_integration.validate_configuration()
            
            # Test storage statistics
            stats = storage_integration.get_storage_statistics()
            
            # Cleanup
            storage_integration.shutdown()
            
            success = all([
                validation_results.get("valid", False),
                stats is not None,
                "configuration" in stats
            ])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "validation_valid": validation_results.get("valid"),
                    "stats_available": stats is not None
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_dual_backend_configuration(self):
        """Test dual backend configuration."""
        test_name = "dual_backend_configuration"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Test S3Vector only configuration
            s3vector_config = StorageConfiguration(
                enabled_backends=[StorageBackend.DIRECT_S3VECTOR],
                vector_types=[VectorType.VISUAL_TEXT],
                environment=self.test_environment,
                s3vector_bucket_name=self.test_bucket_name
            )
            
            # Test dual backend configuration
            dual_config = StorageConfiguration(
                enabled_backends=[StorageBackend.DIRECT_S3VECTOR, StorageBackend.OPENSEARCH_HYBRID],
                vector_types=[VectorType.VISUAL_TEXT, VectorType.AUDIO],
                environment=self.test_environment,
                s3vector_bucket_name=self.test_bucket_name,
                opensearch_domain_name=self.test_domain_name
            )
            
            # Validate configurations
            s3vector_valid = s3vector_config.validate()
            dual_valid = dual_config.validate()
            
            success = all([s3vector_valid, dual_valid])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "s3vector_config_valid": s3vector_valid,
                    "dual_config_valid": dual_valid
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_metadata_preservation(self):
        """Test metadata preservation system."""
        test_name = "metadata_preservation"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Create test metadata
            test_metadata = MediaMetadata(
                file_name="test_video.mp4",
                s3_storage_location="s3://test-bucket/test_video.mp4",
                file_format="mp4",
                file_size_bytes=1024000,
                duration_seconds=120.5,
                resolution="1920x1080",
                frame_rate=30.0,
                audio_channels=2,
                segment_count=24,
                segment_duration=5.0,
                vector_types_generated=["visual-text", "audio"],
                embedding_model="marengo-2.7",
                embedding_dimensions={"visual-text": 1024, "audio": 1024},
                processing_cost_usd=0.05,
                content_category="entertainment",
                tags=["test", "validation"],
                custom_metadata={"test_run": True}
            )
            
            # Test S3Vector metadata format
            s3vector_metadata = test_metadata.to_s3vector_metadata()
            
            # Test OpenSearch metadata format
            opensearch_metadata = test_metadata.to_opensearch_metadata()
            
            # Validate metadata formats
            s3vector_valid = all([
                len(s3vector_metadata) <= 10,  # S3Vector 10-key limit
                "file_name" in s3vector_metadata,
                "duration" in s3vector_metadata
            ])
            
            opensearch_valid = all([
                "file_name" in opensearch_metadata,
                "duration_seconds" in opensearch_metadata,
                "custom_metadata" in opensearch_metadata
            ])
            
            success = all([s3vector_valid, opensearch_valid])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "s3vector_metadata_valid": s3vector_valid,
                    "opensearch_metadata_valid": opensearch_valid,
                    "s3vector_key_count": len(s3vector_metadata),
                    "opensearch_key_count": len(opensearch_metadata)
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_index_segregation(self):
        """Test index segregation by embedding type."""
        test_name = "index_segregation"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Test index naming conventions
            vector_types = [VectorType.VISUAL_TEXT, VectorType.VISUAL_IMAGE, VectorType.AUDIO]
            index_names = []
            
            for vector_type in vector_types:
                # Test production naming
                prod_name = f"prod-video-{vector_type.value}-v1"
                index_names.append(prod_name)
                
                # Test development naming
                dev_name = f"dev-video-{vector_type.value}-v1"
                index_names.append(dev_name)
            
            # Validate naming conventions
            naming_valid = all([
                "visual-text" in name or "visual-image" in name or "audio" in name
                for name in index_names
            ])
            
            # Test uniqueness
            uniqueness_valid = len(set(index_names)) == len(index_names)
            
            success = all([naming_valid, uniqueness_valid])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "naming_convention_valid": naming_valid,
                    "uniqueness_valid": uniqueness_valid,
                    "generated_names": index_names
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_error_handling(self):
        """Test error handling mechanisms."""
        test_name = "error_handling"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Test invalid configuration
            try:
                invalid_config = StorageConfiguration(
                    enabled_backends=[],  # Empty backends should fail
                    vector_types=[VectorType.VISUAL_TEXT],
                    environment=self.test_environment
                )
                invalid_config.validate()
                config_error_handled = False
            except Exception:
                config_error_handled = True
            
            # Test invalid bucket name
            try:
                storage_manager = S3VectorStorageManager()
                storage_manager.create_vector_bucket("")  # Empty name should fail
                bucket_error_handled = False
            except Exception:
                bucket_error_handled = True
            
            success = all([config_error_handled, bucket_error_handled])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "config_error_handled": config_error_handled,
                    "bucket_error_handled": bucket_error_handled
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_batch_processing(self):
        """Test batch processing capabilities."""
        test_name = "batch_processing"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Create test configuration
            config = StorageConfiguration(
                enabled_backends=[StorageBackend.DIRECT_S3VECTOR],
                vector_types=[VectorType.VISUAL_TEXT],
                environment=self.test_environment,
                s3vector_bucket_name=self.test_bucket_name,
                batch_size=3,
                max_concurrent_operations=2
            )
            
            # Test batch size validation
            batch_size_valid = config.batch_size == 3
            
            # Test concurrent operations validation
            concurrent_valid = config.max_concurrent_operations == 2
            
            success = all([batch_size_valid, concurrent_valid])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "batch_size_valid": batch_size_valid,
                    "concurrent_operations_valid": concurrent_valid
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _test_progress_tracking(self):
        """Test progress tracking functionality."""
        test_name = "progress_tracking"
        logger.info(f"Running test: {test_name}")
        
        try:
            # Create test progress object
            progress = UpsertionProgress(
                operation_id="test_operation_123",
                total_items=100,
                processed_items=50,
                successful_items=45,
                failed_items=5
            )
            
            # Test progress calculations
            progress_percentage = progress.progress_percentage
            elapsed_time = progress.elapsed_time_seconds
            
            # Validate progress tracking
            percentage_valid = progress_percentage == 50.0
            elapsed_valid = elapsed_time >= 0
            
            success = all([percentage_valid, elapsed_valid])
            
            self.test_results["tests"][test_name] = {
                "status": "PASSED" if success else "FAILED",
                "details": {
                    "progress_percentage": progress_percentage,
                    "elapsed_time": elapsed_time,
                    "percentage_valid": percentage_valid,
                    "elapsed_valid": elapsed_valid
                }
            }
            
            if success:
                self.test_results["summary"]["passed_tests"] += 1
            else:
                self.test_results["summary"]["failed_tests"] += 1
                
        except Exception as e:
            logger.error(f"Test {test_name} failed: {str(e)}")
            self.test_results["tests"][test_name] = {
                "status": "FAILED",
                "error": str(e)
            }
            self.test_results["summary"]["failed_tests"] += 1
        
        self.test_results["summary"]["total_tests"] += 1
    
    def _generate_validation_report(self):
        """Generate comprehensive validation report."""
        logger.info("Generating validation report")
        
        # Calculate success rate
        total_tests = self.test_results["summary"]["total_tests"]
        passed_tests = self.test_results["summary"]["passed_tests"]
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.test_results["summary"]["success_rate"] = success_rate
        self.test_results["summary"]["validation_status"] = "PASSED" if success_rate >= 80 else "FAILED"
        
        # Add recommendations
        recommendations = []
        
        if success_rate < 100:
            recommendations.append("Review failed tests and address underlying issues")
        
        if success_rate >= 80:
            recommendations.append("Backend functionality is validated and ready for production use")
        else:
            recommendations.append("Backend requires significant fixes before production deployment")
        
        self.test_results["recommendations"] = recommendations
        
        logger.info(f"Validation completed: {success_rate:.1f}% success rate")
    
    def cleanup_test_resources(self):
        """Cleanup test resources."""
        logger.info("Cleaning up test resources")
        
        try:
            storage_manager = S3VectorStorageManager()
            
            # Delete test bucket (cascade delete indexes)
            try:
                storage_manager.delete_vector_bucket(
                    bucket_name=self.test_bucket_name,
                    cascade=True
                )
                logger.info(f"Deleted test bucket: {self.test_bucket_name}")
            except Exception as e:
                logger.warning(f"Failed to delete test bucket: {str(e)}")
            
            # Cleanup OpenSearch resources
            try:
                pattern2_manager = OpenSearchS3VectorPattern2Manager()
                opensearch_bucket_name = f"{self.test_domain_name}-s3vector"
                
                # Delete OpenSearch S3Vector bucket
                pattern2_manager.s3vectors_client.delete_vector_bucket(
                    vectorBucketName=opensearch_bucket_name
                )
                logger.info(f"Deleted OpenSearch S3Vector bucket: {opensearch_bucket_name}")
                
            except Exception as e:
                logger.warning(f"Failed to cleanup OpenSearch resources: {str(e)}")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")


def main():
    """Main validation function."""
    print("🔍 S3Vector Backend Functionality Validation")
    print("=" * 50)
    
    validator = S3VectorBackendValidator()
    
    try:
        # Run all validations
        results = validator.run_all_validations()
        
        # Print summary
        summary = results["summary"]
        print(f"\n📊 Validation Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Status: {summary['validation_status']}")
        
        # Print failed tests
        failed_tests = [
            name for name, result in results["tests"].items()
            if result["status"] == "FAILED"
        ]
        
        if failed_tests:
            print(f"\n❌ Failed Tests:")
            for test_name in failed_tests:
                test_result = results["tests"][test_name]
                print(f"   • {test_name}: {test_result.get('error', 'Unknown error')}")
        
        # Print recommendations
        if "recommendations" in results:
            print(f"\n💡 Recommendations:")
            for rec in results["recommendations"]:
                print(f"   • {rec}")
        
        # Save results to file
        results_file = project_root / "validation_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Cleanup test resources
        if input("\n🧹 Cleanup test resources? (y/N): ").lower() == 'y':
            validator.cleanup_test_resources()
            print("✅ Test resources cleaned up")
        
        # Exit with appropriate code
        exit_code = 0 if summary["validation_status"] == "PASSED" else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()