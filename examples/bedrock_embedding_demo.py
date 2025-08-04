#!/usr/bin/env python3
"""
Bedrock Embedding Service Demonstration

This script demonstrates the text embedding generation functionality using
Amazon Bedrock models including Titan and Cohere embedding models.

Usage:
    python examples/bedrock_embedding_demo.py
"""

import sys
import os
import json
from typing import List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.bedrock_embedding import BedrockEmbeddingService, EmbeddingResult
from src.exceptions import ModelAccessError, ValidationError, VectorEmbeddingError
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def demonstrate_single_embedding():
    """Demonstrate single text embedding generation."""
    print("\n" + "="*60)
    print("SINGLE TEXT EMBEDDING DEMONSTRATION")
    print("="*60)
    
    service = BedrockEmbeddingService()
    
    # Test text
    test_text = "Amazon Bedrock is a fully managed service that offers foundation models from leading AI companies."
    
    # Try different models
    models_to_test = [
        'amazon.titan-embed-text-v2:0',
        'amazon.titan-embed-text-v1',
        'cohere.embed-english-v3'
    ]
    
    for model_id in models_to_test:
        try:
            print(f"\n📝 Testing model: {model_id}")
            print(f"Input text: {test_text[:50]}...")
            
            # Generate embedding
            result = service.generate_text_embedding(test_text, model_id)
            
            print(f"✅ Success!")
            print(f"   - Embedding dimensions: {len(result.embedding)}")
            print(f"   - Processing time: {result.processing_time_ms}ms")
            print(f"   - First 5 values: {result.embedding[:5]}")
            
        except ModelAccessError as e:
            print(f"❌ Model access error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")


def demonstrate_batch_embedding():
    """Demonstrate batch text embedding generation."""
    print("\n" + "="*60)
    print("BATCH TEXT EMBEDDING DEMONSTRATION")
    print("="*60)
    
    service = BedrockEmbeddingService()
    
    # Test texts
    test_texts = [
        "Machine learning is transforming how we process data.",
        "Vector databases enable semantic search capabilities.",
        "Amazon S3 Vectors provides cost-effective vector storage.",
        "Natural language processing helps understand text meaning."
    ]
    
    try:
        print(f"\n📝 Processing {len(test_texts)} texts with batch embedding")
        for i, text in enumerate(test_texts):
            print(f"   {i+1}. {text[:40]}...")
        
        # Generate batch embeddings
        results = service.batch_generate_embeddings(test_texts, 'amazon.titan-embed-text-v2:0')
        
        print(f"✅ Batch processing successful!")
        print(f"   - Generated {len(results)} embeddings")
        
        for i, result in enumerate(results):
            print(f"   - Text {i+1}: {len(result.embedding)} dimensions, {result.processing_time_ms}ms")
            
    except Exception as e:
        print(f"❌ Batch processing error: {e}")


def demonstrate_model_validation():
    """Demonstrate model access validation."""
    print("\n" + "="*60)
    print("MODEL VALIDATION DEMONSTRATION")
    print("="*60)
    
    service = BedrockEmbeddingService()
    
    # Get supported models
    supported_models = service.get_supported_models()
    
    print(f"\n📋 Supported Models ({len(supported_models)} total):")
    for model_id, model_info in supported_models.items():
        print(f"   • {model_id}")
        print(f"     - Dimensions: {model_info.dimensions}")
        print(f"     - Max tokens: {model_info.max_input_tokens}")
        print(f"     - Cost per 1K tokens: ${model_info.cost_per_1k_tokens}")
        print(f"     - Batch support: {model_info.supports_batch}")
        print(f"     - Description: {model_info.description}")
        print()
    
    # Test model validation
    print("🔍 Testing model access validation:")
    for model_id in list(supported_models.keys())[:2]:  # Test first 2 models
        try:
            is_accessible = service.validate_model_access(model_id)
            print(f"   ✅ {model_id}: {'Accessible' if is_accessible else 'Not accessible'}")
        except ModelAccessError as e:
            print(f"   ❌ {model_id}: {e}")
        except Exception as e:
            print(f"   ❌ {model_id}: Unexpected error - {e}")


def demonstrate_cost_estimation():
    """Demonstrate cost estimation functionality."""
    print("\n" + "="*60)
    print("COST ESTIMATION DEMONSTRATION")
    print("="*60)
    
    service = BedrockEmbeddingService()
    
    # Sample texts of different lengths
    test_scenarios = [
        {
            "name": "Short texts",
            "texts": ["Hello world", "AI is amazing", "Vector search"]
        },
        {
            "name": "Medium texts", 
            "texts": [
                "Amazon Bedrock provides access to foundation models from leading AI companies through a single API.",
                "Vector embeddings enable semantic search by converting text into numerical representations.",
                "Cost optimization is crucial when processing large volumes of text data for embedding generation."
            ]
        },
        {
            "name": "Long text",
            "texts": [
                "Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models (FMs) from leading AI companies like AI21 Labs, Anthropic, Cohere, Meta, Stability AI, and Amazon via a single API, along with a broad set of capabilities you need to build generative AI applications with security, privacy, and responsible AI. Using Amazon Bedrock, you can easily experiment with and evaluate top FMs for your use case, privately customize them with your data using techniques such as fine-tuning and Retrieval Augmented Generation (RAG), and build agents that execute tasks using your enterprise systems and data sources."
            ]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n💰 Cost estimation for: {scenario['name']}")
        
        try:
            cost_info = service.estimate_cost(scenario['texts'], 'amazon.titan-embed-text-v2:0')
            
            print(f"   - Text count: {cost_info['text_count']}")
            print(f"   - Total characters: {cost_info['total_characters']:,}")
            print(f"   - Estimated tokens: {cost_info['estimated_tokens']:,}")
            print(f"   - Estimated cost: ${cost_info['estimated_cost_usd']:.6f}")
            
        except Exception as e:
            print(f"   ❌ Cost estimation error: {e}")


def demonstrate_error_handling():
    """Demonstrate error handling scenarios."""
    print("\n" + "="*60)
    print("ERROR HANDLING DEMONSTRATION")
    print("="*60)
    
    service = BedrockEmbeddingService()
    
    # Test various error scenarios
    error_scenarios = [
        {
            "name": "Empty text",
            "text": "",
            "model": "amazon.titan-embed-text-v2:0"
        },
        {
            "name": "Unsupported model",
            "text": "Test text",
            "model": "unsupported-model-id"
        },
        {
            "name": "Very long text",
            "text": "a" * 50000,  # Very long text
            "model": "amazon.titan-embed-text-v2:0"
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\n🚨 Testing: {scenario['name']}")
        try:
            result = service.generate_text_embedding(scenario['text'], scenario['model'])
            print(f"   ✅ Unexpected success: {len(result.embedding)} dimensions")
        except ValidationError as e:
            print(f"   ✅ Validation error caught: {e.error_code} - {e}")
        except ModelAccessError as e:
            print(f"   ✅ Model access error caught: {e.error_code} - {e}")
        except VectorEmbeddingError as e:
            print(f"   ✅ Vector embedding error caught: {e.error_code} - {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")


def main():
    """Main demonstration function."""
    print("🚀 BEDROCK EMBEDDING SERVICE DEMONSTRATION")
    print("This demo showcases text embedding generation using Amazon Bedrock models")
    
    try:
        # Run all demonstrations
        demonstrate_model_validation()
        demonstrate_single_embedding()
        demonstrate_batch_embedding()
        demonstrate_cost_estimation()
        demonstrate_error_handling()
        
        print("\n" + "="*60)
        print("✅ DEMONSTRATION COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey Features Demonstrated:")
        print("• Multiple embedding model support (Titan V1, V2, Cohere)")
        print("• Single and batch text processing")
        print("• Model access validation")
        print("• Cost estimation")
        print("• Comprehensive error handling")
        print("• Retry logic for transient failures")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        logger.error(f"Demo failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())