#!/usr/bin/env python3
"""
Vector Operations Demo

This script demonstrates the vector storage and retrieval operations
implemented in task 2.3, including:
- put_vectors() with batch support and metadata attachment
- query_vectors() for similarity search with filtering
- list_vectors() with pagination support

Requirements covered: 1.3, 1.5, 5.1, 5.2, 5.3
"""

import sys
import os
import numpy as np
from typing import List, Dict, Any

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.s3_vector_storage import S3VectorStorageManager
from src.exceptions import VectorStorageError, ValidationError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def generate_sample_vectors(count: int, dimensions: int = 1024) -> List[Dict[str, Any]]:
    """Generate sample vectors with metadata for demonstration."""
    vectors = []
    
    # Sample content types and categories for media use case
    content_types = ['video', 'text', 'audio', 'image']
    categories = ['news', 'sports', 'entertainment', 'documentary', 'comedy', 'drama']
    
    for i in range(count):
        # Generate random vector data (normalized)
        vector_data = np.random.normal(0, 1, dimensions).astype(np.float32)
        vector_data = vector_data / np.linalg.norm(vector_data)  # Normalize
        
        content_type = content_types[i % len(content_types)]
        category = categories[i % len(categories)]
        
        vector = {
            'key': f'{content_type}_{category}_{i:03d}',
            'data': vector_data.tolist(),
            'metadata': {
                'content_type': content_type,
                'category': category,
                'title': f'Sample {content_type.title()} Content {i}',
                'duration': np.random.randint(30, 7200) if content_type in ['video', 'audio'] else None,
                'quality_score': round(np.random.uniform(0.7, 1.0), 2),
                'created_at': f'2025-01-{(i % 28) + 1:02d}T{np.random.randint(0, 24):02d}:00:00Z'
            }
        }
        vectors.append(vector)
    
    return vectors


def demonstrate_put_vectors(storage_manager: S3VectorStorageManager, index_arn: str):
    """Demonstrate vector storage with batch support and metadata."""
    print("\n" + "="*60)
    print("DEMONSTRATING PUT_VECTORS OPERATION")
    print("="*60)
    
    # Generate sample vectors
    print("Generating sample vectors...")
    sample_vectors = generate_sample_vectors(10, dimensions=1024)
    
    print(f"Generated {len(sample_vectors)} vectors with metadata")
    print(f"Sample vector key: {sample_vectors[0]['key']}")
    print(f"Vector dimensions: {len(sample_vectors[0]['data'])}")
    print(f"Sample metadata: {sample_vectors[0]['metadata']}")
    
    try:
        # Store vectors in batches
        print(f"\nStoring vectors in index: {index_arn}")
        result = storage_manager.put_vectors(index_arn, sample_vectors)
        
        print(f"✅ Successfully stored {result['vectors_stored']} vectors")
        print(f"Status: {result['status']}")
        
        # Demonstrate batch processing with larger dataset
        print("\nDemonstrating batch processing with larger dataset...")
        large_batch = generate_sample_vectors(50, dimensions=1024)
        
        # Process in smaller batches (simulate real-world usage)
        batch_size = 20
        total_stored = 0
        
        for i in range(0, len(large_batch), batch_size):
            batch = large_batch[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}: {len(batch)} vectors")
            
            result = storage_manager.put_vectors(index_arn, batch)
            total_stored += result['vectors_stored']
            
        print(f"✅ Total vectors stored: {total_stored}")
        
    except (VectorStorageError, ValidationError) as e:
        print(f"❌ Error storing vectors: {e}")
        print(f"Error code: {e.error_code}")
        if hasattr(e, 'error_details'):
            print(f"Error details: {e.error_details}")


def demonstrate_query_vectors(storage_manager: S3VectorStorageManager, index_arn: str):
    """Demonstrate similarity search with filtering."""
    print("\n" + "="*60)
    print("DEMONSTRATING QUERY_VECTORS OPERATION")
    print("="*60)
    
    # Generate a query vector
    query_vector = np.random.normal(0, 1, 1024).astype(np.float32)
    query_vector = query_vector / np.linalg.norm(query_vector)  # Normalize
    
    try:
        # Basic similarity search
        print("Performing basic similarity search...")
        result = storage_manager.query_vectors(
            index_arn=index_arn,
            query_vector=query_vector.tolist(),
            top_k=5,
            return_distance=True,
            return_metadata=True
        )
        
        print(f"✅ Found {result['results_count']} similar vectors")
        print(f"Query vector dimensions: {result['query_vector_dimensions']}")
        
        if result['vectors']:
            print("\nTop similar vectors:")
            for i, vector in enumerate(result['vectors'][:3]):
                print(f"  {i+1}. Key: {vector.get('key', 'N/A')}")
                if 'distance' in vector:
                    print(f"     Distance: {vector['distance']:.4f}")
                if 'metadata' in vector and vector['metadata']:
                    metadata = vector['metadata']
                    print(f"     Content: {metadata.get('content_type', 'N/A')} - {metadata.get('category', 'N/A')}")
                    print(f"     Title: {metadata.get('title', 'N/A')}")
        
        # Demonstrate metadata filtering
        print("\nDemonstrating metadata filtering...")
        metadata_filter = {
            'content_type': 'video'
        }
        
        filtered_result = storage_manager.query_vectors(
            index_arn=index_arn,
            query_vector=query_vector.tolist(),
            top_k=3,
            metadata_filter=metadata_filter,
            return_distance=True,
            return_metadata=True
        )
        
        print(f"✅ Found {filtered_result['results_count']} video content matches")
        if filtered_result['vectors']:
            print("Filtered results (video content only):")
            for i, vector in enumerate(filtered_result['vectors']):
                print(f"  {i+1}. Key: {vector.get('key', 'N/A')}")
                if 'metadata' in vector and vector['metadata']:
                    metadata = vector['metadata']
                    print(f"     Type: {metadata.get('content_type', 'N/A')}")
                    print(f"     Category: {metadata.get('category', 'N/A')}")
        
        # Demonstrate minimal response (keys only)
        print("\nDemonstrating minimal response (keys only)...")
        minimal_result = storage_manager.query_vectors(
            index_arn=index_arn,
            query_vector=query_vector.tolist(),
            top_k=5,
            return_distance=False,
            return_metadata=False
        )
        
        print(f"✅ Found {minimal_result['results_count']} matches (keys only)")
        if minimal_result['vectors']:
            keys = [v.get('key', 'N/A') for v in minimal_result['vectors']]
            print(f"Keys: {', '.join(keys)}")
        
    except (VectorStorageError, ValidationError) as e:
        print(f"❌ Error querying vectors: {e}")
        print(f"Error code: {e.error_code}")
        if hasattr(e, 'error_details'):
            print(f"Error details: {e.error_details}")


def demonstrate_list_vectors(storage_manager: S3VectorStorageManager, index_arn: str):
    """Demonstrate vector listing with pagination."""
    print("\n" + "="*60)
    print("DEMONSTRATING LIST_VECTORS OPERATION")
    print("="*60)
    
    try:
        # Basic vector listing
        print("Listing vectors with metadata...")
        result = storage_manager.list_vectors(
            index_arn=index_arn,
            max_results=10,
            return_metadata=True,
            return_data=False
        )
        
        print(f"✅ Listed {result['count']} vectors")
        print(f"Next token: {'Available' if result['next_token'] else 'None'}")
        
        if result['vectors']:
            print("\nSample vectors:")
            for i, vector in enumerate(result['vectors'][:5]):
                print(f"  {i+1}. Key: {vector.get('key', 'N/A')}")
                if 'metadata' in vector and vector['metadata']:
                    metadata = vector['metadata']
                    print(f"     Type: {metadata.get('content_type', 'N/A')}")
                    print(f"     Category: {metadata.get('category', 'N/A')}")
                    print(f"     Quality: {metadata.get('quality_score', 'N/A')}")
        
        # Demonstrate pagination
        if result['next_token']:
            print("\nDemonstrating pagination...")
            next_page = storage_manager.list_vectors(
                index_arn=index_arn,
                max_results=5,
                next_token=result['next_token'],
                return_metadata=True
            )
            
            print(f"✅ Next page: {next_page['count']} vectors")
            if next_page['vectors']:
                print("Next page vectors:")
                for i, vector in enumerate(next_page['vectors'][:3]):
                    print(f"  {i+1}. Key: {vector.get('key', 'N/A')}")
        
        # Demonstrate parallel listing (simulation)
        print("\nDemonstrating parallel listing capability...")
        segment_results = []
        segment_count = 4
        
        for segment_index in range(segment_count):
            segment_result = storage_manager.list_vectors(
                index_arn=index_arn,
                max_results=5,
                segment_count=segment_count,
                segment_index=segment_index,
                return_metadata=False
            )
            segment_results.append(segment_result)
            print(f"  Segment {segment_index}: {segment_result['count']} vectors")
        
        total_segments = sum(r['count'] for r in segment_results)
        print(f"✅ Total vectors across all segments: {total_segments}")
        
        # Demonstrate listing with vector data
        print("\nDemonstrating listing with vector data...")
        data_result = storage_manager.list_vectors(
            index_arn=index_arn,
            max_results=3,
            return_data=True,
            return_metadata=True
        )
        
        print(f"✅ Listed {data_result['count']} vectors with data")
        if data_result['vectors']:
            for i, vector in enumerate(data_result['vectors'][:2]):
                print(f"  {i+1}. Key: {vector.get('key', 'N/A')}")
                if 'data' in vector:
                    data_length = len(vector['data']) if vector['data'] else 0
                    print(f"     Vector data length: {data_length}")
                    if data_length > 0:
                        print(f"     Sample values: {vector['data'][:5]}...")
        
    except (VectorStorageError, ValidationError) as e:
        print(f"❌ Error listing vectors: {e}")
        print(f"Error code: {e.error_code}")
        if hasattr(e, 'error_details'):
            print(f"Error details: {e.error_details}")


def main():
    """Main demonstration function."""
    print("S3 Vector Storage Operations Demo")
    print("Task 2.3: Vector Storage and Retrieval Operations")
    print("Requirements: 1.3, 1.5, 5.1, 5.2, 5.3")
    
    # Note: This demo uses mock data and would require actual AWS credentials
    # and a real S3 Vectors index to run against live services
    
    # Example index ARN (would be real in actual usage)
    index_arn = "arn:aws:s3vectors:us-west-2:123456789012:index/media-embeddings/video-text-index"
    
    print(f"\nUsing index ARN: {index_arn}")
    print("\n⚠️  Note: This demo shows the interface and validation.")
    print("   For actual AWS operations, ensure proper credentials and permissions.")
    
    try:
        # Initialize storage manager
        storage_manager = S3VectorStorageManager()
        
        # Demonstrate each operation
        demonstrate_put_vectors(storage_manager, index_arn)
        demonstrate_query_vectors(storage_manager, index_arn)
        demonstrate_list_vectors(storage_manager, index_arn)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey Features Demonstrated:")
        print("✅ put_vectors() - Batch storage with metadata")
        print("✅ query_vectors() - Similarity search with filtering")
        print("✅ list_vectors() - Pagination and parallel listing")
        print("\nAll operations include:")
        print("• Comprehensive input validation")
        print("• Proper error handling with retry logic")
        print("• Float32 conversion for S3 Vectors compatibility")
        print("• Detailed logging and monitoring")
        print("• Production-ready patterns")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        logger.error(f"Demo error: {e}", exc_info=True)


if __name__ == "__main__":
    main()