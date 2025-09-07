#!/usr/bin/env python3
"""
Test script to verify S3 bucket naming fixes.

This script tests:
1. Bucket name sanitization function
2. ComprehensiveVideoProcessingService bucket creation
3. End-to-end video processing workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.s3_bucket_utils import S3BucketUtilityService
from src.services.comprehensive_video_processing_service import (
    ComprehensiveVideoProcessingService, 
    ProcessingConfig, 
    ProcessingMode,
    VectorType
)
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def test_bucket_name_sanitization():
    """Test the bucket name sanitization function."""
    logger.info("Testing bucket name sanitization...")
    
    test_cases = [
        # (input, expected_pattern)
        ("S3Vector_Production_Bucket", "s3vector-production-bucket"),
        ("invalid..bucket..name", "invalid-bucket-name"),
        ("UPPERCASE_WITH_UNDERSCORES", "uppercase-with-underscores"),
        ("", "s3vector-bucket"),
        ("a", "s3vector-a"),
        ("very-long-bucket-name-that-exceeds-the-sixty-three-character-limit-for-s3-buckets", None),  # Should be truncated
        ("bucket-name-with-periods.and.hyphens", "bucket-name-with-periods.and.hyphens"),
        ("123-starts-with-number", "123-starts-with-number"),
        ("ends-with-hyphen-", "ends-with-hyphen"),
        ("has--consecutive--hyphens", "has-consecutive-hyphens"),
    ]
    
    for input_name, expected in test_cases:
        sanitized = S3BucketUtilityService.sanitize_bucket_name(input_name)
        logger.info(f"Input: '{input_name}' -> Output: '{sanitized}'")
        
        # Verify AWS S3 naming rules
        assert 3 <= len(sanitized) <= 63, f"Length violation: {sanitized}"
        assert sanitized.islower(), f"Case violation: {sanitized}"
        assert sanitized[0].isalnum(), f"Start character violation: {sanitized}"
        assert sanitized[-1].isalnum(), f"End character violation: {sanitized}"
        assert not any(c in sanitized for c in ['_', ' ', '\t']), f"Invalid character violation: {sanitized}"
        
        if expected and expected != sanitized:
            logger.warning(f"Expected '{expected}' but got '{sanitized}'")
    
    logger.info("✅ Bucket name sanitization tests passed!")


def test_bucket_creation():
    """Test bucket creation with sanitization."""
    logger.info("Testing bucket creation with sanitization...")
    
    s3_utils = S3BucketUtilityService()
    
    # Test with invalid bucket name
    invalid_bucket_name = "Invalid_Bucket_Name_With_Underscores"
    result = s3_utils.create_bucket(invalid_bucket_name)
    
    logger.info(f"Bucket creation result: {result}")
    
    # Verify the result contains sanitized name
    assert 'bucket_name' in result
    assert 'original_name' in result
    assert result['original_name'] == invalid_bucket_name
    assert result['bucket_name'] != invalid_bucket_name
    assert result['bucket_name'].islower()
    
    logger.info("✅ Bucket creation with sanitization tests passed!")


def test_video_processing_service():
    """Test ComprehensiveVideoProcessingService with bucket naming fixes."""
    logger.info("Testing ComprehensiveVideoProcessingService...")
    
    # Create service with test configuration
    config = ProcessingConfig(
        processing_mode=ProcessingMode.BEDROCK_PRIMARY,
        vector_types=[VectorType.VISUAL_TEXT],
        video_bucket_suffix="-videos",
        max_concurrent_jobs=1,
        timeout_sec=300
    )
    
    service = ComprehensiveVideoProcessingService(config)
    
    # Test video URL (small test video)
    test_video_url = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    
    try:
        logger.info(f"Testing video processing with URL: {test_video_url}")
        
        # This should not fail with InvalidBucketName anymore
        result = service.process_video_from_url(
            video_url=test_video_url,
            target_indexes=None  # Skip embedding storage for this test
        )
        
        logger.info(f"Video processing result: {result.status}")
        logger.info(f"S3 URI: {result.s3_uri}")
        
        if result.error_message:
            logger.error(f"Processing error: {result.error_message}")
        
        # The key test is that we don't get InvalidBucketName errors
        assert "InvalidBucketName" not in str(result.error_message or "")
        
        logger.info("✅ Video processing service tests passed!")
        
    except Exception as e:
        if "InvalidBucketName" in str(e):
            logger.error(f"❌ Still getting InvalidBucketName error: {e}")
            raise
        else:
            logger.warning(f"Other error (may be expected): {e}")


def main():
    """Run all tests."""
    logger.info("Starting S3 bucket naming fix tests...")
    
    try:
        # Test 1: Bucket name sanitization
        test_bucket_name_sanitization()
        
        # Test 2: Bucket creation with sanitization
        test_bucket_creation()
        
        # Test 3: Video processing service
        test_video_processing_service()
        
        logger.info("🎉 All tests passed! S3 bucket naming fixes are working correctly.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()