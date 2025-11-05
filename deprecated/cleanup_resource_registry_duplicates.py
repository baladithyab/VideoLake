#!/usr/bin/env python3
"""
Script to clean up duplicate entries in the resource registry.
This script uses the new deduplication functionality to remove duplicate S3 buckets,
vector buckets, and other resources from the registry.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Clean up duplicate entries in the resource registry."""
    logger.info("Starting resource registry deduplication cleanup")
    
    try:
        # Get current state before cleanup
        before_summary = resource_registry.get_resource_summary()
        logger.info(f"Resource counts before cleanup: {before_summary}")
        
        # Run deduplication
        removed_counts = resource_registry.deduplicate_resources()
        logger.info(f"Removed duplicate counts: {removed_counts}")
        
        # Get state after cleanup
        after_summary = resource_registry.get_resource_summary()
        logger.info(f"Resource counts after cleanup: {after_summary}")
        
        # Report results
        total_removed = sum(removed_counts.values())
        if total_removed > 0:
            logger.info(f"✅ Successfully removed {total_removed} duplicate entries:")
            for resource_type, count in removed_counts.items():
                if count > 0:
                    logger.info(f"  - {resource_type}: {count} duplicates removed")
        else:
            logger.info("✅ No duplicate entries found - registry is already clean")
        
        # Show specific improvements
        s3_before = before_summary.get('s3_buckets', 0)
        s3_after = after_summary.get('s3_buckets', 0)
        if s3_before > s3_after:
            logger.info(f"📦 S3 buckets: {s3_before} → {s3_after} (removed {s3_before - s3_after} duplicates)")
        
        vector_before = before_summary.get('vector_buckets', 0)
        vector_after = after_summary.get('vector_buckets', 0)
        if vector_before > vector_after:
            logger.info(f"🗂️  Vector buckets: {vector_before} → {vector_after} (removed {vector_before - vector_after} duplicates)")
        
        logger.info("Resource registry cleanup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clean up resource registry: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)