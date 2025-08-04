"""
Demonstration of S3 Vector Bucket Management functionality.

This example shows how to create, configure, and manage S3 vector buckets
for a media company use case.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import setup_logging, get_structured_logger

# Set up logging
setup_logging(level='INFO', structured=False)
logger = get_structured_logger(__name__)


def demonstrate_bucket_creation():
    """Demonstrate creating vector buckets for different content types."""
    print("\n=== S3 Vector Bucket Creation Demo ===")
    
    # Initialize storage manager
    try:
        storage_manager = S3VectorStorageManager()
        print("✓ S3VectorStorageManager initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize storage manager: {e}")
        return
    
    # Define bucket configurations for media company use case
    bucket_configs = [
        {
            "name": "netflix-movie-embeddings",
            "description": "Vector embeddings for movie content",
            "encryption": "SSE-S3"
        },
        {
            "name": "netflix-series-embeddings", 
            "description": "Vector embeddings for TV series content",
            "encryption": "SSE-S3"
        },
        {
            "name": "netflix-secure-embeddings",
            "description": "Secure vector embeddings with KMS encryption",
            "encryption": "SSE-KMS",
            "kms_key": "arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012"
        }
    ]
    
    created_buckets = []
    
    for config in bucket_configs:
        print(f"\nCreating bucket: {config['name']}")
        print(f"Description: {config['description']}")
        print(f"Encryption: {config['encryption']}")
        
        try:
            if config['encryption'] == 'SSE-KMS':
                result = storage_manager.create_vector_bucket(
                    bucket_name=config['name'],
                    encryption_type=config['encryption'],
                    kms_key_arn=config['kms_key']
                )
            else:
                result = storage_manager.create_vector_bucket(
                    bucket_name=config['name'],
                    encryption_type=config['encryption']
                )
            
            if result['status'] == 'created':
                print(f"✓ Successfully created bucket: {config['name']}")
                created_buckets.append(result)
            elif result['status'] == 'already_exists':
                print(f"ℹ Bucket already exists: {config['name']}")
                created_buckets.append(result)
            
            # Log operation for cost tracking
            logger.log_operation(
                operation="create_vector_bucket",
                bucket_name=config['name'],
                encryption_type=config['encryption'],
                status=result['status']
            )
            
        except ValidationError as e:
            print(f"✗ Validation error for {config['name']}: {e}")
            print(f"  Error code: {e.error_code}")
            
        except VectorStorageError as e:
            print(f"✗ Storage error for {config['name']}: {e}")
            print(f"  Error code: {e.error_code}")
            if e.error_details:
                print(f"  Details: {e.error_details}")
        
        except Exception as e:
            print(f"✗ Unexpected error for {config['name']}: {e}")
    
    print(f"\n✓ Successfully processed {len(created_buckets)} buckets")
    return created_buckets


def demonstrate_bucket_validation():
    """Demonstrate bucket name validation."""
    print("\n=== Bucket Name Validation Demo ===")
    
    storage_manager = S3VectorStorageManager()
    
    # Test cases for validation
    test_cases = [
        ("valid-bucket-name", True, "Valid bucket name"),
        ("media-embeddings-123", True, "Valid with numbers"),
        ("", False, "Empty name"),
        ("ab", False, "Too short"),
        ("a" * 64, False, "Too long"),
        ("Invalid-Name", False, "Contains uppercase"),
        ("bucket_name", False, "Contains underscore"),
        ("-bucket-name", False, "Starts with hyphen"),
        ("bucket-name-", False, "Ends with hyphen"),
        ("bucket--name", False, "Consecutive hyphens")
    ]
    
    for bucket_name, should_pass, description in test_cases:
        try:
            storage_manager._validate_bucket_name(bucket_name)
            if should_pass:
                print(f"✓ {description}: '{bucket_name}' - PASSED")
            else:
                print(f"✗ {description}: '{bucket_name}' - Should have failed but passed")
        except ValidationError as e:
            if not should_pass:
                print(f"✓ {description}: '{bucket_name}' - FAILED as expected ({e.error_code})")
            else:
                print(f"✗ {description}: '{bucket_name}' - Should have passed but failed: {e}")


def demonstrate_bucket_operations():
    """Demonstrate various bucket operations."""
    print("\n=== Bucket Operations Demo ===")
    
    storage_manager = S3VectorStorageManager()
    test_bucket = "demo-vector-bucket"
    
    print(f"Testing operations with bucket: {test_bucket}")
    
    try:
        # Check if bucket exists
        print("\n1. Checking bucket existence...")
        exists = storage_manager.bucket_exists(test_bucket)
        print(f"   Bucket exists: {exists}")
        
        # Create bucket if it doesn't exist
        if not exists:
            print("\n2. Creating bucket...")
            result = storage_manager.create_vector_bucket(test_bucket)
            print(f"   Creation result: {result['status']}")
        else:
            print("\n2. Bucket already exists, skipping creation")
        
        # Get bucket attributes
        print("\n3. Getting bucket attributes...")
        try:
            bucket_info = storage_manager.get_vector_bucket(test_bucket)
            print(f"   Bucket name: {bucket_info.get('vectorBucketName', 'N/A')}")
            print(f"   Encryption: {bucket_info.get('encryptionConfiguration', {}).get('sseType', 'N/A')}")
            print(f"   Creation date: {bucket_info.get('creationDate', 'N/A')}")
        except VectorStorageError as e:
            if e.error_code == "BUCKET_NOT_FOUND":
                print("   Bucket not found (this is expected in demo mode)")
            else:
                print(f"   Error getting bucket info: {e}")
        
        # List all buckets
        print("\n4. Listing all vector buckets...")
        try:
            buckets = storage_manager.list_vector_buckets()
            print(f"   Found {len(buckets)} vector buckets:")
            for bucket in buckets[:5]:  # Show first 5
                print(f"     - {bucket.get('vectorBucketName', 'Unknown')}")
            if len(buckets) > 5:
                print(f"     ... and {len(buckets) - 5} more")
        except VectorStorageError as e:
            print(f"   Error listing buckets: {e}")
    
    except Exception as e:
        print(f"✗ Error during bucket operations: {e}")


def demonstrate_cost_optimization():
    """Demonstrate cost optimization considerations."""
    print("\n=== Cost Optimization Demo ===")
    
    print("Cost optimization strategies for S3 Vector storage:")
    print("\n1. Encryption Options:")
    print("   • SSE-S3: No additional cost, uses AWS managed keys")
    print("   • SSE-KMS: Additional cost per key usage, better security")
    
    print("\n2. Bucket Naming Strategy:")
    print("   • Use descriptive names for content organization")
    print("   • Consider regional deployment for latency optimization")
    print("   • Group similar content types in same bucket for efficiency")
    
    print("\n3. Expected Cost Savings:")
    print("   • S3 Vectors: ~$0.023/GB/month storage")
    print("   • Traditional vector DB: ~$0.50-$2.00/GB/month")
    print("   • Potential savings: 90%+ for large-scale deployments")
    
    # Simulate cost calculation
    monthly_content_gb = 10000  # 10TB of vector data
    s3_vectors_cost = monthly_content_gb * 0.023
    traditional_db_cost = monthly_content_gb * 1.0  # Average cost
    savings = traditional_db_cost - s3_vectors_cost
    
    print(f"\n4. Example Cost Calculation (10TB monthly):")
    print(f"   • S3 Vectors cost: ${s3_vectors_cost:,.2f}/month")
    print(f"   • Traditional DB cost: ${traditional_db_cost:,.2f}/month")
    print(f"   • Monthly savings: ${savings:,.2f}")
    print(f"   • Annual savings: ${savings * 12:,.2f}")


def main():
    """Run all demonstrations."""
    print("S3 Vector Bucket Management Demonstration")
    print("=" * 50)
    
    try:
        # Note: These demos use mocked AWS clients for safety
        print("Note: This demo uses mocked AWS clients for demonstration purposes.")
        print("In a real environment, ensure proper AWS credentials and permissions.")
        
        demonstrate_bucket_validation()
        demonstrate_cost_optimization()
        
        # The following would require real AWS credentials
        print("\n" + "=" * 50)
        print("The following operations would require real AWS credentials:")
        print("- demonstrate_bucket_creation()")
        print("- demonstrate_bucket_operations()")
        print("\nTo run with real AWS services, ensure:")
        print("1. AWS credentials are configured")
        print("2. Proper IAM permissions for S3 Vectors")
        print("3. S3 Vectors service is available in your region")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        return 1
    
    print("\n✓ Demo completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())