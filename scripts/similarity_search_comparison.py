#!/usr/bin/env python3
"""
Comprehensive test script for comparing S3Vector and OpenSearch similarity searches.

This script performs similarity searches on both S3Vector and OpenSearch visual-text indexes
using the same query text and the Marengo 2.7 model via AWS Bedrock for embedding generation.
"""

import json
import time
import argparse
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SimilaritySearchComparison:
    """Compares similarity search results between S3Vector and OpenSearch indexes."""
    
    def __init__(self):
        """Initialize the comparison service with required components."""
        self.bedrock_service = BedrockEmbeddingService()
        self.twelvelabs_service = TwelveLabsVideoProcessingService()
        self.s3_storage_manager = S3VectorStorageManager()
        self.opensearch_manager = OpenSearchIntegrationManager()

        # Load resource registry to get active resources
        self.registry = resource_registry
        self.active_resources = self.registry.get_active_resources()

        logger.info("Similarity search comparison service initialized")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for input text using Marengo 2.7 model.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the embedding (1024 dimensions)
        """
        try:
            logger.info(f"Generating embedding for text: '{text[:50]}...'")

            # Use TwelveLabs Marengo 2.7 model for text embedding
            result = self.twelvelabs_service.generate_text_embedding(text)

            embedding = result['embedding']
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def search_s3vector_index(self, 
                             query_vector: List[float], 
                             top_k: int = 10) -> Dict[str, Any]:
        """
        Search the S3Vector visual-text index.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Find the visual-text index from registry
            visual_text_index = None
            for index in self.registry.list_indexes():
                if index.get('name') == 'prod-video-visual-text-v1':
                    visual_text_index = index
                    break
            
            if not visual_text_index:
                raise ValueError("Visual-text S3Vector index not found in registry")
            
            index_arn = visual_text_index['arn']
            logger.info(f"Searching S3Vector index: {index_arn}")
            
            start_time = time.time()
            
            # Perform similarity search
            search_results = self.s3_storage_manager.query_vectors(
                index_arn=index_arn,
                query_vector=query_vector,
                top_k=top_k,
                return_distance=True,
                return_metadata=True
            )
            
            query_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Process results to extract similarity scores
            processed_results = []
            for vector in search_results.get('vectors', []):
                # Convert distance to similarity score (assuming cosine distance)
                distance = vector.get('distance', 1.0)
                similarity_score = 1.0 - distance
                
                processed_results.append({
                    'vector_key': vector.get('key', 'unknown'),
                    'similarity_score': similarity_score,
                    'distance': distance,
                    'metadata': vector.get('metadata', {})
                })
            
            return {
                'index_type': 'S3Vector',
                'index_arn': index_arn,
                'query_latency_ms': query_latency,
                'results_count': len(processed_results),
                'results': processed_results
            }
            
        except Exception as e:
            logger.error(f"S3Vector search failed: {e}")
            return {
                'index_type': 'S3Vector',
                'error': str(e),
                'query_latency_ms': 0,
                'results_count': 0,
                'results': []
            }
    
    def search_opensearch_index(self, 
                               query_vector: List[float], 
                               top_k: int = 10) -> Dict[str, Any]:
        """
        Search the OpenSearch visual-text index with S3Vector engine.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        try:
            # Find the OpenSearch visual-text index from registry
            opensearch_index = None
            for index in self.registry.list_opensearch_indexes():
                if index.get('name') == 'prod-video-visual-text-s3vector-v1':
                    opensearch_index = index
                    break
            
            if not opensearch_index:
                raise ValueError("Visual-text OpenSearch index not found in registry")
            
            endpoint = opensearch_index['endpoint']
            index_name = opensearch_index['name']
            vector_field = opensearch_index.get('vector_field', 'embedding')
            
            logger.info(f"Searching OpenSearch index: {index_name} at {endpoint}")
            
            start_time = time.time()
            
            # Perform hybrid search (vector-only)
            # The perform_hybrid_search method expects endpoint without protocol
            search_results = self.opensearch_manager.perform_hybrid_search(
                opensearch_endpoint=endpoint,
                index_name=index_name,
                query_vector=query_vector,
                vector_field=vector_field,
                k=top_k,
                score_combination="weighted",
                vector_weight=1.0,  # Pure vector search
                text_weight=0.0
            )
            
            query_latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Process results
            processed_results = []
            for result in search_results:
                processed_results.append({
                    'document_id': result.document_id,
                    'similarity_score': result.vector_score,
                    'combined_score': result.combined_score,
                    'content': result.content,
                    'metadata': result.metadata
                })
            
            return {
                'index_type': 'OpenSearch',
                'index_name': index_name,
                'endpoint': endpoint,
                'query_latency_ms': query_latency,
                'results_count': len(processed_results),
                'results': processed_results
            }
            
        except Exception as e:
            logger.error(f"OpenSearch search failed: {e}")
            return {
                'index_type': 'OpenSearch',
                'error': str(e),
                'query_latency_ms': 0,
                'results_count': 0,
                'results': []
            }
    
    def compare_search_results(self, 
                              query_text: str, 
                              top_k: int = 10) -> Dict[str, Any]:
        """
        Perform similarity search on both indexes and compare results.
        
        Args:
            query_text: Input text query
            top_k: Number of results to return from each index
            
        Returns:
            Dictionary containing comparison results
        """
        logger.info(f"Starting similarity search comparison for: '{query_text}'")
        
        try:
            # Generate embedding for the query text
            embedding_start = time.time()
            query_vector = self.generate_embedding(query_text)
            embedding_time = (time.time() - embedding_start) * 1000
            
            # Search both indexes
            s3vector_results = self.search_s3vector_index(query_vector, top_k)
            opensearch_results = self.search_opensearch_index(query_vector, top_k)
            
            # Calculate total latencies
            s3vector_total_latency = embedding_time + s3vector_results.get('query_latency_ms', 0)
            opensearch_total_latency = embedding_time + opensearch_results.get('query_latency_ms', 0)
            
            return {
                'query_text': query_text,
                'query_vector_dimensions': len(query_vector),
                'embedding_generation_ms': embedding_time,
                'top_k': top_k,
                's3vector': {
                    **s3vector_results,
                    'total_latency_ms': s3vector_total_latency
                },
                'opensearch': {
                    **opensearch_results,
                    'total_latency_ms': opensearch_total_latency
                },
                'comparison': {
                    'latency_difference_ms': abs(s3vector_total_latency - opensearch_total_latency),
                    'faster_index': 'S3Vector' if s3vector_total_latency < opensearch_total_latency else 'OpenSearch',
                    'results_count_difference': abs(
                        s3vector_results.get('results_count', 0) - 
                        opensearch_results.get('results_count', 0)
                    )
                }
            }
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {
                'query_text': query_text,
                'error': str(e),
                's3vector': {'error': 'Comparison failed'},
                'opensearch': {'error': 'Comparison failed'}
            }

    def print_comparison_results(self, results: Dict[str, Any]) -> None:
        """
        Print formatted comparison results to console.

        Args:
            results: Comparison results dictionary
        """
        print("\n" + "="*80)
        print("SIMILARITY SEARCH COMPARISON RESULTS")
        print("="*80)

        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return

        print(f"Query Text: '{results['query_text']}'")
        print(f"Query Vector Dimensions: {results['query_vector_dimensions']}")
        print(f"Embedding Generation Time: {results['embedding_generation_ms']:.2f}ms")
        print(f"Top-K Results: {results['top_k']}")

        print("\n" + "-"*40 + " S3VECTOR RESULTS " + "-"*40)
        s3v_results = results['s3vector']
        if 'error' in s3v_results:
            print(f"❌ S3Vector Error: {s3v_results['error']}")
        else:
            print(f"Index ARN: {s3v_results.get('index_arn', 'N/A')}")
            print(f"Query Latency: {s3v_results.get('query_latency_ms', 0):.2f}ms")
            print(f"Total Latency: {s3v_results.get('total_latency_ms', 0):.2f}ms")
            print(f"Results Count: {s3v_results.get('results_count', 0)}")

            if s3v_results.get('results'):
                print("\nTop Results:")
                for i, result in enumerate(s3v_results['results'][:5], 1):
                    print(f"  {i}. Key: {result.get('vector_key', 'N/A')}")
                    print(f"     Similarity: {result.get('similarity_score', 0):.4f}")
                    print(f"     Distance: {result.get('distance', 0):.4f}")
                    if result.get('metadata'):
                        print(f"     Metadata: {json.dumps(result['metadata'], indent=8)}")
                    print()

        print("\n" + "-"*40 + " OPENSEARCH RESULTS " + "-"*40)
        os_results = results['opensearch']
        if 'error' in os_results:
            print(f"❌ OpenSearch Error: {os_results['error']}")
        else:
            print(f"Index Name: {os_results.get('index_name', 'N/A')}")
            print(f"Endpoint: {os_results.get('endpoint', 'N/A')}")
            print(f"Query Latency: {os_results.get('query_latency_ms', 0):.2f}ms")
            print(f"Total Latency: {os_results.get('total_latency_ms', 0):.2f}ms")
            print(f"Results Count: {os_results.get('results_count', 0)}")

            if os_results.get('results'):
                print("\nTop Results:")
                for i, result in enumerate(os_results['results'][:5], 1):
                    print(f"  {i}. Document ID: {result.get('document_id', 'N/A')}")
                    print(f"     Vector Score: {result.get('similarity_score', 0):.4f}")
                    print(f"     Combined Score: {result.get('combined_score', 0):.4f}")
                    if result.get('content'):
                        content_preview = str(result['content'])[:100] + "..." if len(str(result['content'])) > 100 else str(result['content'])
                        print(f"     Content: {content_preview}")
                    if result.get('metadata'):
                        print(f"     Metadata: {json.dumps(result['metadata'], indent=8)}")
                    print()

        print("\n" + "-"*40 + " COMPARISON " + "-"*40)
        comparison = results.get('comparison', {})
        print(f"Latency Difference: {comparison.get('latency_difference_ms', 0):.2f}ms")
        print(f"Faster Index: {comparison.get('faster_index', 'N/A')}")
        print(f"Results Count Difference: {comparison.get('results_count_difference', 0)}")

        # Performance analysis
        s3v_latency = s3v_results.get('total_latency_ms', 0)
        os_latency = os_results.get('total_latency_ms', 0)

        if s3v_latency > 0 and os_latency > 0:
            if s3v_latency < os_latency:
                speedup = (os_latency - s3v_latency) / os_latency * 100
                print(f"S3Vector is {speedup:.1f}% faster than OpenSearch")
            else:
                speedup = (s3v_latency - os_latency) / s3v_latency * 100
                print(f"OpenSearch is {speedup:.1f}% faster than S3Vector")

        print("="*80)


def main():
    """Main function to run the similarity search comparison."""
    parser = argparse.ArgumentParser(
        description="Compare similarity search results between S3Vector and OpenSearch indexes"
    )
    parser.add_argument(
        "query_text",
        help="Text query to search for (e.g., 'machine learning algorithms')"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top results to return (default: 10)"
    )
    parser.add_argument(
        "--output-file",
        help="Optional file to save detailed results in JSON format"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.INFO)

    try:
        # Initialize comparison service
        comparison_service = SimilaritySearchComparison()

        # Perform comparison
        results = comparison_service.compare_search_results(
            query_text=args.query_text,
            top_k=args.top_k
        )

        # Print results to console
        comparison_service.print_comparison_results(results)

        # Save to file if requested
        if args.output_file:
            with open(args.output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📁 Detailed results saved to: {args.output_file}")

    except KeyboardInterrupt:
        print("\n⚠️  Search comparison interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error running comparison: {e}")
        logger.error(f"Comparison failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
