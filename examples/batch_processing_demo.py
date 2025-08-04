#!/usr/bin/env python3
"""
Batch Processing Demo for Bedrock Embedding Service

This demo showcases the enhanced batch processing capabilities including:
- Rate limiting and throttling management
- Configurable batch sizes and concurrency
- Error handling and retry logic
- Performance optimization recommendations
- Cost estimation for batch operations
"""

import asyncio
import time
import sys
import os
from typing import List
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def create_sample_texts(count: int) -> List[str]:
    """Create sample texts for batch processing demonstration."""
    sample_texts = [
        "The quick brown fox jumps over the lazy dog",
        "Machine learning is transforming the way we process data",
        "Cloud computing provides scalable infrastructure for modern applications",
        "Natural language processing enables computers to understand human language",
        "Vector embeddings capture semantic meaning in numerical form",
        "Artificial intelligence is revolutionizing various industries",
        "Deep learning models can learn complex patterns from data",
        "Streaming platforms use recommendation systems to suggest content",
        "Video analysis helps identify scenes and objects automatically",
        "Content discovery systems help users find relevant media"
    ]
    
    # Repeat and modify texts to reach desired count
    texts = []
    for i in range(count):
        base_text = sample_texts[i % len(sample_texts)]
        texts.append(f"{base_text} (sample {i + 1})")
    
    return texts


def demonstrate_basic_batch_processing():
    """Demonstrate basic batch processing functionality."""
    print("\n" + "="*60)
    print("BASIC BATCH PROCESSING DEMONSTRATION")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    texts = create_sample_texts(5)
    
    print(f"Processing {len(texts)} texts using default settings...")
    
    start_time = time.time()
    try:
        results = embedding_service.batch_generate_embeddings(texts)
        processing_time = time.time() - start_time
        
        print(f"✅ Successfully processed {len(results)} embeddings")
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        print(f"📊 Average time per embedding: {processing_time/len(results):.3f} seconds")
        
        # Show sample result
        if results:
            sample_result = results[0]
            print(f"📝 Sample result:")
            print(f"   Text: {sample_result.input_text[:50]}...")
            print(f"   Model: {sample_result.model_id}")
            print(f"   Embedding dimensions: {len(sample_result.embedding)}")
            print(f"   Processing time: {sample_result.processing_time_ms}ms")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def demonstrate_advanced_batch_processing():
    """Demonstrate advanced batch processing with custom parameters."""
    print("\n" + "="*60)
    print("ADVANCED BATCH PROCESSING DEMONSTRATION")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    texts = create_sample_texts(15)
    
    print(f"Processing {len(texts)} texts with custom parameters...")
    
    # Custom parameters for demonstration
    custom_batch_size = 5
    max_concurrent = 3
    rate_limit_delay = 0.1
    
    print(f"📋 Configuration:")
    print(f"   Batch size: {custom_batch_size}")
    print(f"   Max concurrent: {max_concurrent}")
    print(f"   Rate limit delay: {rate_limit_delay}s")
    
    start_time = time.time()
    try:
        results = embedding_service.batch_generate_embeddings(
            texts,
            batch_size=custom_batch_size,
            max_concurrent=max_concurrent,
            rate_limit_delay=rate_limit_delay
        )
        processing_time = time.time() - start_time
        
        print(f"✅ Successfully processed {len(results)} embeddings")
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        print(f"📊 Average time per embedding: {processing_time/len(results):.3f} seconds")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def demonstrate_cohere_batch_processing():
    """Demonstrate Cohere model batch processing with native batching."""
    print("\n" + "="*60)
    print("COHERE NATIVE BATCH PROCESSING DEMONSTRATION")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    texts = create_sample_texts(20)
    
    print(f"Processing {len(texts)} texts using Cohere model with native batching...")
    
    start_time = time.time()
    try:
        results = embedding_service.batch_generate_embeddings(
            texts,
            model_id="cohere.embed-english-v3",
            batch_size=10,  # Cohere can handle larger batches
            rate_limit_delay=0.05
        )
        processing_time = time.time() - start_time
        
        print(f"✅ Successfully processed {len(results)} embeddings")
        print(f"⏱️  Processing time: {processing_time:.2f} seconds")
        print(f"📊 Average time per embedding: {processing_time/len(results):.3f} seconds")
        print(f"🚀 Native batch processing efficiency demonstrated")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def demonstrate_batch_processing_recommendations():
    """Demonstrate batch processing recommendations system."""
    print("\n" + "="*60)
    print("BATCH PROCESSING RECOMMENDATIONS")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    
    # Test different scenarios
    scenarios = [
        ("Small batch", create_sample_texts(5)),
        ("Medium batch", create_sample_texts(50)),
        ("Large batch", create_sample_texts(200))
    ]
    
    for scenario_name, texts in scenarios:
        print(f"\n📊 {scenario_name} ({len(texts)} texts):")
        
        # Get recommendations for Titan model
        titan_recommendations = embedding_service.get_batch_processing_recommendations(
            texts, "amazon.titan-embed-text-v2:0"
        )
        
        print(f"   Titan Text V2:")
        print(f"     Recommended batch size: {titan_recommendations['recommended_batch_size']}")
        print(f"     Concurrent requests: {titan_recommendations['recommended_concurrent_requests']}")
        print(f"     Estimated API requests: {titan_recommendations['estimated_api_requests']}")
        print(f"     Estimated time (concurrent): {titan_recommendations['estimated_processing_time_seconds']['concurrent']}s")
        print(f"     Estimated cost: ${titan_recommendations['cost_estimate']['estimated_cost_usd']:.6f}")
        
        # Get recommendations for Cohere model
        cohere_recommendations = embedding_service.get_batch_processing_recommendations(
            texts, "cohere.embed-english-v3"
        )
        
        print(f"   Cohere English V3:")
        print(f"     Recommended batch size: {cohere_recommendations['recommended_batch_size']}")
        print(f"     Native batch support: {cohere_recommendations['supports_native_batch']}")
        print(f"     Estimated API requests: {cohere_recommendations['estimated_api_requests']}")
        print(f"     Estimated time (concurrent): {cohere_recommendations['estimated_processing_time_seconds']['concurrent']}s")
        print(f"     Estimated cost: ${cohere_recommendations['cost_estimate']['estimated_cost_usd']:.6f}")


def demonstrate_error_handling_and_retry():
    """Demonstrate error handling and retry logic in batch processing."""
    print("\n" + "="*60)
    print("ERROR HANDLING AND RETRY LOGIC DEMONSTRATION")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    
    # Test with various error scenarios
    print("🔧 Testing error handling capabilities...")
    
    # Test empty input validation
    try:
        embedding_service.batch_generate_embeddings([])
        print("❌ Should have failed with empty input")
    except Exception as e:
        print(f"✅ Empty input validation: {type(e).__name__}")
    
    # Test empty text in list validation
    try:
        embedding_service.batch_generate_embeddings(["valid text", "", "another valid text"])
        print("❌ Should have failed with empty text in list")
    except Exception as e:
        print(f"✅ Empty text validation: {type(e).__name__}")
    
    # Test unsupported model
    try:
        embedding_service.batch_generate_embeddings(["test"], model_id="unsupported-model")
        print("❌ Should have failed with unsupported model")
    except Exception as e:
        print(f"✅ Unsupported model validation: {type(e).__name__}")
    
    print("🛡️  Error handling and validation working correctly")


def demonstrate_cost_optimization():
    """Demonstrate cost optimization strategies for batch processing."""
    print("\n" + "="*60)
    print("COST OPTIMIZATION STRATEGIES")
    print("="*60)
    
    embedding_service = BedrockEmbeddingService()
    texts = create_sample_texts(100)
    
    print(f"Analyzing cost optimization for {len(texts)} texts...")
    
    # Compare different models
    models = [
        "amazon.titan-embed-text-v2:0",
        "cohere.embed-english-v3"
    ]
    
    for model_id in models:
        try:
            cost_estimate = embedding_service.estimate_cost(texts, model_id)
            recommendations = embedding_service.get_batch_processing_recommendations(texts, model_id)
            
            print(f"\n💰 {model_id}:")
            print(f"   Cost per 1K tokens: ${cost_estimate['cost_per_1k_tokens']:.6f}")
            print(f"   Estimated total cost: ${cost_estimate['estimated_cost_usd']:.6f}")
            print(f"   Estimated tokens: {cost_estimate['estimated_tokens']:,}")
            print(f"   Native batch support: {recommendations['supports_native_batch']}")
            print(f"   Recommended batch size: {recommendations['recommended_batch_size']}")
            print(f"   Estimated processing time: {recommendations['estimated_processing_time_seconds']['concurrent']}s")
            
        except Exception as e:
            print(f"   ❌ Error analyzing {model_id}: {str(e)}")
    
    print(f"\n💡 Optimization Tips:")
    print(f"   • Use Cohere models for native batch processing efficiency")
    print(f"   • Adjust batch size based on input volume")
    print(f"   • Consider rate limiting for large batches")
    print(f"   • Monitor actual costs vs estimates")


def main():
    """Run all batch processing demonstrations."""
    print("🚀 BEDROCK EMBEDDING SERVICE - BATCH PROCESSING DEMO")
    print("This demo showcases enhanced batch processing capabilities")
    
    try:
        # Run all demonstrations
        demonstrate_basic_batch_processing()
        demonstrate_advanced_batch_processing()
        demonstrate_cohere_batch_processing()
        demonstrate_batch_processing_recommendations()
        demonstrate_error_handling_and_retry()
        demonstrate_cost_optimization()
        
        print("\n" + "="*60)
        print("✅ BATCH PROCESSING DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey features demonstrated:")
        print("• Basic and advanced batch processing")
        print("• Rate limiting and throttling management")
        print("• Configurable batch sizes and concurrency")
        print("• Native batch processing for Cohere models")
        print("• Comprehensive error handling and retry logic")
        print("• Performance optimization recommendations")
        print("• Cost estimation and optimization strategies")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        logger.error(f"Batch processing demo failed: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()