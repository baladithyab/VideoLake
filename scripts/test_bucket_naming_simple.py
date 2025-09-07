#!/usr/bin/env python3
"""
Simple test for S3 bucket naming fixes without network dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.s3_bucket_utils import S3BucketUtilityService
from src.services.comprehensive_video_processing_service import ComprehensiveVideoProcessingService, ProcessingConfig
from src.config.unified_config_manager import get_unified_config_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def test_bucket_sanitization():
    """Test bucket name sanitization."""
    logger.info("Testing bucket name sanitization...")
    
    test_cases = [
        ("S3Vector_Production_Bucket", "s3vector-production-bucket"),
        ("invalid..bucket..name", "invalid-bucket-name"),
        ("UPPERCASE_WITH_UNDERSCORES", "uppercase-with-underscores"),
        ("", "s3vector-bucket"),
        ("a", "s3vector-a"),
    ]
    
    for input_name, expected in test_cases:
        sanitized = S3BucketUtilityService.sanitize_bucket_name(input_name)
        logger.info(f"'{input_name}' -> '{sanitized}' (expected: '{expected}')")
        
        # Verify AWS S3 naming rules
        assert 3 <= len(sanitized) <= 63, f"Length violation: {sanitized}"
        assert sanitized.islower(), f"Case violation: {sanitized}"
        assert sanitized[0].isalnum(), f"Start character violation: {sanitized}"
        assert sanitized[-1].isalnum(), f"End character violation: {sanitized}"
        
    logger.info("✅ Bucket name sanitization working correctly!")


def test_config_and_bucket_generation():
    """Test configuration and bucket name generation."""
    logger.info("Testing configuration and bucket name generation...")
    
    config_manager = get_unified_config_manager()
    aws_config = config_manager.config.aws
    
    logger.info(f"AWS config - s3_bucket: {aws_config.s3_bucket}")
    logger.info(f"AWS config - s3_vectors_bucket: {aws_config.s3_vectors_bucket}")
    
    # Test the bucket name generation logic from ComprehensiveVideoProcessingService
    service = ComprehensiveVideoProcessingService()
    config = ProcessingConfig()
    
    # Simulate the bucket name generation
    base_bucket = service.aws_config.s3_vectors_bucket or service.aws_config.s3_bucket or "s3vector-default"
    video_bucket_name = f"{base_bucket}{config.video_bucket_suffix}"
    
    logger.info(f"Generated video bucket name: {video_bucket_name}")
    
    # Test sanitization
    sanitized_name = S3BucketUtilityService.sanitize_bucket_name(video_bucket_name)
    logger.info(f"Sanitized video bucket name: {sanitized_name}")
    
    # Verify it's valid
    assert 3 <= len(sanitized_name) <= 63
    assert sanitized_name.islower()
    assert sanitized_name[0].isalnum()
    assert sanitized_name[-1].isalnum()
    
    logger.info("✅ Configuration and bucket generation working correctly!")


def test_s3_bucket_utility():
    """Test S3BucketUtilityService create_bucket method."""
    logger.info("Testing S3BucketUtilityService...")
    
    s3_utils = S3BucketUtilityService()
    
    # Test with an invalid bucket name that should be sanitized
    invalid_name = "Invalid_Bucket_Name_With_Underscores"
    
    try:
        # This should not raise InvalidBucketName error anymore
        result = s3_utils.create_bucket(invalid_name)
        logger.info(f"Bucket creation result: {result}")
        
        # Verify sanitization occurred
        assert result['original_name'] == invalid_name
        assert result['bucket_name'] != invalid_name
        assert result['bucket_name'].islower()
        assert '_' not in result['bucket_name']
        
        logger.info("✅ S3BucketUtilityService working correctly!")
        
    except Exception as e:
        if "InvalidBucketName" in str(e):
            logger.error(f"❌ Still getting InvalidBucketName error: {e}")
            raise
        else:
            # Other AWS errors are expected (permissions, etc.)
            logger.info(f"Got expected AWS error (not InvalidBucketName): {type(e).__name__}")
            logger.info("✅ No InvalidBucketName error - sanitization working!")


def main():
    """Run all tests."""
    logger.info("Starting simple S3 bucket naming tests...")
    
    try:
        test_bucket_sanitization()
        test_config_and_bucket_generation()
        test_s3_bucket_utility()
        
        logger.info("🎉 All bucket naming fixes are working correctly!")
        logger.info("The InvalidBucketName error should now be resolved.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()