#!/usr/bin/env python3
"""
S3 Vector Index Management Demo

This script demonstrates the vector index operations including:
- Creating vector indexes with different configurations
- Listing indexes with filtering and pagination
- Getting index metadata
- Checking index existence
- Deleting indexes

This is a demonstration script that shows the API usage patterns.
For actual usage, ensure proper AWS credentials and permissions are configured.
"""

import sys
import os
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class IndexManagementDemo:
    """Demonstrates S3 Vector index management operations."""
    
    def __init__(self):
        """Initialize the demo with S3 Vector Storage Manager."""
        self.storage_manager = S3VectorStorageManager()
        self.demo_bucket = "demo-vector-bucket"
        self.demo_indexes = [
            {
                "name": "text-embeddings",
                "dimensions": 1024,
                "distance_metric": "cosine",
                "description": "Text embeddings using Bedrock Titan"
            },
            {
                "name": "video-embeddings", 
                "dimensions": 1024,
                "distance_metric": "cosine",
                "description": "Video embeddings using TwelveLabs Marengo"
            },
            {
                "name": "image-embeddings",
                "dimensions": 1024,
                "distance_metric": "euclidean",
                "description": "Image embeddings for visual similarity"
            }
        ]
    
    def run_demo(self):
        """Run the complete index management demonstration."""
        print("🚀 S3 Vector Index Management Demo")
        print("=" * 50)
        
        try:
            # Step 1: Ensure bucket exists
            self._ensure_demo_bucket()
            
            # Step 2: Create vector indexes
            self._create_demo_indexes()
            
            # Step 3: List and explore indexes
            self._list_and_explore_indexes()
            
            # Step 4: Demonstrate index metadata retrieval
            self._demonstrate_metadata_retrieval()
            
            # Step 5: Demonstrate index existence checking
            self._demonstrate_existence_checking()
            
            # Step 6: Demonstrate index filtering
            self._demonstrate_index_filtering()
            
            # Step 7: Clean up (optional)
            self._cleanup_demo_indexes()
            
            print("\n✅ Demo completed successfully!")
            
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            print(f"\n❌ Demo failed: {e}")
            return False
        
        return True
    
    def _ensure_demo_bucket(self):
        """Ensure the demo bucket exists."""
        print(f"\n📦 Ensuring demo bucket exists: {self.demo_bucket}")
        
        try:
            if not self.storage_manager.bucket_exists(self.demo_bucket):
                print(f"   Creating bucket: {self.demo_bucket}")
                result = self.storage_manager.create_vector_bucket(self.demo_bucket)
                print(f"   ✅ Bucket created: {result['status']}")
            else:
                print(f"   ✅ Bucket already exists: {self.demo_bucket}")
                
        except VectorStorageError as e:
            if "already_exists" in str(e).lower():
                print(f"   ✅ Bucket already exists: {self.demo_bucket}")
            else:
                raise
    
    def _create_demo_indexes(self):
        """Create demonstration vector indexes."""
        print(f"\n🔧 Creating vector indexes in bucket: {self.demo_bucket}")
        
        for index_config in self.demo_indexes:
            index_name = index_config["name"]
            dimensions = index_config["dimensions"]
            distance_metric = index_config["distance_metric"]
            description = index_config["description"]
            
            print(f"\n   Creating index: {index_name}")
            print(f"   - Dimensions: {dimensions}")
            print(f"   - Distance metric: {distance_metric}")
            print(f"   - Description: {description}")
            
            try:
                # Create index with metadata configuration
                non_filterable_keys = ["large_description", "raw_content"]
                
                result = self.storage_manager.create_vector_index(
                    bucket_name=self.demo_bucket,
                    index_name=index_name,
                    dimensions=dimensions,
                    distance_metric=distance_metric,
                    non_filterable_metadata_keys=non_filterable_keys
                )
                
                print(f"   ✅ Index created: {result['status']}")
                
            except VectorStorageError as e:
                if "already_exists" in str(e).lower():
                    print(f"   ✅ Index already exists: {index_name}")
                else:
                    print(f"   ❌ Failed to create index {index_name}: {e}")
                    raise
    
    def _list_and_explore_indexes(self):
        """List and explore the created indexes."""
        print(f"\n📋 Listing vector indexes in bucket: {self.demo_bucket}")
        
        try:
            # List all indexes
            result = self.storage_manager.list_vector_indexes(self.demo_bucket)
            indexes = result['indexes']
            
            print(f"   Found {result['count']} indexes:")
            
            for index in indexes:
                print(f"   - {index['indexName']}")
                print(f"     ARN: {index['indexArn']}")
                print(f"     Created: {index.get('creationTime', 'N/A')}")
                print(f"     Bucket: {index['vectorBucketName']}")
                print()
            
            # Demonstrate pagination (if needed)
            if result['next_token']:
                print("   📄 More results available (pagination token present)")
            
        except VectorStorageError as e:
            print(f"   ❌ Failed to list indexes: {e}")
            raise
    
    def _demonstrate_metadata_retrieval(self):
        """Demonstrate retrieving metadata for specific indexes."""
        print(f"\n🔍 Retrieving metadata for specific indexes")
        
        for index_config in self.demo_indexes[:2]:  # Just first two for demo
            index_name = index_config["name"]
            
            try:
                print(f"\n   Getting metadata for: {index_name}")
                
                metadata = self.storage_manager.get_vector_index_metadata(
                    self.demo_bucket, 
                    index_name
                )
                
                print(f"   ✅ Metadata retrieved:")
                print(f"     - Index Name: {metadata['index_name']}")
                print(f"     - Index ARN: {metadata['index_arn']}")
                print(f"     - Creation Time: {metadata['creation_time']}")
                print(f"     - Bucket: {metadata['bucket_name']}")
                
            except VectorStorageError as e:
                print(f"   ❌ Failed to get metadata for {index_name}: {e}")
    
    def _demonstrate_existence_checking(self):
        """Demonstrate checking if indexes exist."""
        print(f"\n✅ Checking index existence")
        
        # Check existing indexes
        for index_config in self.demo_indexes:
            index_name = index_config["name"]
            exists = self.storage_manager.index_exists(self.demo_bucket, index_name)
            status = "✅ EXISTS" if exists else "❌ NOT FOUND"
            print(f"   {index_name}: {status}")
        
        # Check non-existent index
        fake_index = "nonexistent-index"
        exists = self.storage_manager.index_exists(self.demo_bucket, fake_index)
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        print(f"   {fake_index}: {status}")
    
    def _demonstrate_index_filtering(self):
        """Demonstrate index filtering with prefix."""
        print(f"\n🔍 Demonstrating index filtering")
        
        # Filter by prefix
        prefix = "text"
        print(f"\n   Filtering indexes with prefix: '{prefix}'")
        
        try:
            result = self.storage_manager.list_vector_indexes(
                self.demo_bucket,
                prefix=prefix,
                max_results=10
            )
            
            print(f"   Found {result['count']} indexes matching prefix '{prefix}':")
            for index in result['indexes']:
                print(f"   - {index['indexName']}")
            
        except VectorStorageError as e:
            print(f"   ❌ Failed to filter indexes: {e}")
        
        # Filter by another prefix
        prefix = "video"
        print(f"\n   Filtering indexes with prefix: '{prefix}'")
        
        try:
            result = self.storage_manager.list_vector_indexes(
                self.demo_bucket,
                prefix=prefix,
                max_results=5
            )
            
            print(f"   Found {result['count']} indexes matching prefix '{prefix}':")
            for index in result['indexes']:
                print(f"   - {index['indexName']}")
            
        except VectorStorageError as e:
            print(f"   ❌ Failed to filter indexes: {e}")
    
    def _cleanup_demo_indexes(self):
        """Clean up demonstration indexes (optional)."""
        print(f"\n🧹 Cleanup demonstration indexes")
        
        cleanup = input("   Do you want to delete the demo indexes? (y/N): ").lower().strip()
        
        if cleanup == 'y':
            print("   Deleting demo indexes...")
            
            for index_config in self.demo_indexes:
                index_name = index_config["name"]
                
                try:
                    print(f"   Deleting: {index_name}")
                    
                    result = self.storage_manager.delete_vector_index(
                        bucket_name=self.demo_bucket,
                        index_name=index_name
                    )
                    
                    print(f"   ✅ Deleted: {result['status']}")
                    
                except VectorStorageError as e:
                    if "not_found" in str(e).lower():
                        print(f"   ✅ Already deleted: {index_name}")
                    else:
                        print(f"   ❌ Failed to delete {index_name}: {e}")
        else:
            print("   Skipping cleanup - indexes will remain for further testing")


def main():
    """Run the index management demonstration."""
    demo = IndexManagementDemo()
    
    print("This demo will create vector indexes in S3 Vectors.")
    print("Make sure you have proper AWS credentials configured.")
    print("Note: This demo uses mocked clients and won't make real AWS calls.")
    
    proceed = input("\nProceed with demo? (Y/n): ").lower().strip()
    
    if proceed == 'n':
        print("Demo cancelled.")
        return
    
    success = demo.run_demo()
    
    if success:
        print("\n🎉 Index management demo completed successfully!")
        print("\nKey takeaways:")
        print("- Vector indexes can be created with configurable dimensions and distance metrics")
        print("- Indexes can be listed with filtering and pagination support")
        print("- Metadata retrieval provides detailed index information")
        print("- Index existence can be checked efficiently")
        print("- Indexes can be deleted by name or ARN")
        print("- All operations include comprehensive error handling")
    else:
        print("\n💥 Demo encountered errors. Check the logs for details.")


if __name__ == "__main__":
    main()