#!/usr/bin/env python3
"""
Example usage of the S3 Vector Embedding POC.

This script demonstrates how to initialize and use the core components
of the vector embedding system.
"""

import os
import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from src.core import create_poc_instance
from src.exceptions import VectorEmbeddingError, ConfigurationError


def main():
    """Main example function."""
    print("S3 Vector Embedding POC - Example Usage")
    print("=" * 50)
    
    # Configuration is automatically loaded from .env file
    print(f"Using AWS Profile: {os.getenv('AWS_PROFILE', 'default')}")
    print(f"Using AWS Region: {os.getenv('AWS_REGION', 'us-west-2')}")
    print(f"Using S3 Bucket: {os.getenv('S3_VECTORS_BUCKET', 'not-configured')}")
    print()
    
    try:
        # Create POC instance with auto-initialization disabled
        print("Creating POC instance...")
        poc = create_poc_instance(
            log_level='INFO',
            structured_logging=True,
            auto_initialize=False
        )
        
        # Initialize the system
        print("Initializing system components...")
        poc.initialize()
        
        # Get system information
        print("\nSystem Information:")
        system_info = poc.get_system_info()
        
        print(f"  - Initialized: {system_info['initialized']}")
        print(f"  - AWS Region: {system_info['aws_config']['region']}")
        print(f"  - S3 Vectors Bucket: {system_info['aws_config']['s3_vectors_bucket']}")
        print(f"  - Bedrock Models: {system_info['aws_config']['bedrock_models']}")
        
        # Perform health check
        print("\nPerforming health check...")
        health = poc.health_check()
        print(f"  - Status: {health['status']}")
        print(f"  - Client Status: {health['clients']}")
        
        print("\n✅ POC initialization completed successfully!")
        print("\nNext steps:")
        print("1. Set up your AWS credentials and permissions")
        print("2. Create an S3 Vector bucket")
        print("3. Configure Bedrock model access")
        print("4. Start implementing the service components")
        
    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        print(f"Error Code: {e.error_code}")
        if e.error_details:
            print(f"Details: {e.error_details}")
        
        print("\nPlease check your environment variables:")
        print("- S3_VECTORS_BUCKET: S3 bucket name for vector storage")
        print("- AWS_REGION: AWS region (default: us-west-2)")
        print("- AWS credentials should be configured via AWS CLI or IAM roles")
        
    except VectorEmbeddingError as e:
        print(f"\n❌ System Error: {e}")
        print(f"Error Code: {e.error_code}")
        if e.error_details:
            print(f"Details: {e.error_details}")
            
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        print("Please check your AWS configuration and permissions.")


if __name__ == '__main__':
    main()