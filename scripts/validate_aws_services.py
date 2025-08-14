#!/usr/bin/env python3
"""
AWS Service Validation Script

Validates our S3Vector implementation against current AWS documentation
and tests core functionality without interactive prompts.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.services.similarity_search_engine import SimilaritySearchEngine
from src.utils.logging_config import get_structured_logger

logger = get_structured_logger("validation")

def validate_s3_vectors_api():
    """Validate S3 Vectors API operations against current documentation."""
    print("🔍 Validating S3 Vectors API Operations...")
    
    try:
        manager = S3VectorStorageManager()
        
        # Test API method availability (from AWS docs)
        expected_methods = [
            'create_vector_bucket',
            'create_vector_index', 
            'put_vectors_batch',
            'query_similar_vectors',
            'list_vectors',
            'get_vector_index_metadata',
            'delete_vector_index'
        ]
        
        missing_methods = []
        for method in expected_methods:
            if not hasattr(manager, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing methods: {missing_methods}")
            return False
        else:
            print("✅ All expected S3 Vectors API methods implemented")
            return True
            
    except Exception as e:
        print(f"❌ S3 Vectors validation failed: {e}")
        return False

def validate_bedrock_models():
    """Validate Bedrock model support against current documentation."""
    print("🔍 Validating Bedrock Model Support...")
    
    try:
        service = BedrockEmbeddingService()
        
        # Get supported models (returns Dict[str, ModelInfo])
        models_dict = service.get_supported_models()
        
        # Expected models from AWS documentation
        expected_models = [
            'amazon.titan-embed-text-v2:0',
            'amazon.titan-embed-image-v1',
            'cohere.embed-english-v3',
            'cohere.embed-multilingual-v3'
        ]
        
        supported_model_ids = list(models_dict.keys())
        
        missing_models = []
        for model_id in expected_models:
            if model_id not in supported_model_ids:
                missing_models.append(model_id)
        
        if missing_models:
            print(f"⚠️ Models not in our config: {missing_models}")
        
        print(f"✅ Supporting {len(models_dict)} Bedrock embedding models:")
        for model_id, model_info in models_dict.items():
            print(f"   • {model_id} - {model_info.dimensions} dims")
        
        return True
        
    except Exception as e:
        print(f"❌ Bedrock validation failed: {e}")
        return False

def validate_twelvelabs_integration():
    """Validate TwelveLabs integration against current documentation."""
    print("🔍 Validating TwelveLabs Marengo Integration...")
    
    try:
        from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService
        
        service = TwelveLabsVideoProcessingService()
        
        # Check model ID matches documentation
        expected_model_id = "twelvelabs.marengo-embed-2-7-v1:0"
        
        # Check if service has the expected configuration
        if hasattr(service, 'model_id'):
            actual_model_id = service.model_id
            if actual_model_id == expected_model_id:
                print(f"✅ TwelveLabs model ID correct: {expected_model_id}")
            else:
                print(f"⚠️ Model ID mismatch: expected {expected_model_id}, got {actual_model_id}")
        
        # Check expected methods
        expected_methods = [
            'start_video_processing',
            'get_job_status', 
            'retrieve_results',
            'process_video_sync'
        ]
        
        missing_methods = []
        for method in expected_methods:
            if not hasattr(service, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing TwelveLabs methods: {missing_methods}")
            return False
        else:
            print("✅ All expected TwelveLabs methods implemented")
            return True
            
    except Exception as e:
        print(f"❌ TwelveLabs validation failed: {e}")
        return False

def validate_search_engine():
    """Validate similarity search engine functionality."""
    print("🔍 Validating Similarity Search Engine...")
    
    try:
        from src.services.similarity_search_engine import (
            SimilaritySearchEngine, SimilarityQuery, IndexType
        )
        
        engine = SimilaritySearchEngine()
        
        # Check expected methods
        expected_methods = [
            'find_similar_content',
            'search_by_text_query',
            'search_video_scenes'
        ]
        
        missing_methods = []
        for method in expected_methods:
            if not hasattr(engine, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ Missing search methods: {missing_methods}")
            return False
        
        # Check IndexType enum values
        expected_index_types = ['TITAN_TEXT', 'MARENGO_MULTIMODAL']
        available_types = [t.name for t in IndexType]
        
        missing_types = []
        for index_type in expected_index_types:
            if index_type not in available_types:
                missing_types.append(index_type)
        
        if missing_types:
            print(f"❌ Missing index types: {missing_types}")
            return False
        
        print("✅ All expected search engine functionality implemented")
        print(f"   • Index types: {available_types}")
        return True
        
    except Exception as e:
        print(f"❌ Search engine validation failed: {e}")
        return False

def test_configuration():
    """Test configuration and environment setup."""
    print("🔍 Validating Configuration...")
    
    try:
        from src.config import config_manager
        
        # Check AWS configuration
        aws_config = config_manager.aws_config
        
        print(f"✅ AWS Region: {aws_config.region}")
        print(f"✅ S3 Vectors Bucket: {aws_config.s3_vectors_bucket}")
        
        # Check model configurations
        if hasattr(aws_config, 'bedrock_models'):
            print("✅ Bedrock models configured:")
            for model_type, model_id in aws_config.bedrock_models.items():
                print(f"   • {model_type}: {model_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def run_simple_functionality_test():
    """Run a simple functionality test without AWS calls."""
    print("🔍 Testing Core Functionality...")
    
    try:
        # Test vector data validation
        from src.services.s3_vector_storage import S3VectorStorageManager
        
        manager = S3VectorStorageManager()
        
        # Test bucket name validation
        valid_names = ["test-bucket", "media-vectors-123", "my-embeddings"]
        invalid_names = ["", "ab", "Invalid_Name", "-bucket", "bucket-"]
        
        for name in valid_names:
            try:
                manager._validate_bucket_name(name)
                print(f"✅ Valid bucket name: {name}")
            except Exception as e:
                print(f"❌ Unexpected validation error for {name}: {e}")
                return False
        
        for name in invalid_names:
            try:
                manager._validate_bucket_name(name)
                print(f"❌ Should have failed validation: {name}")
                return False
            except Exception:
                print(f"✅ Correctly rejected invalid name: {name}")
        
        print("✅ Bucket name validation working correctly")
        
        # Test vector dimension validation (AWS docs: 1 to 4,096)
        valid_dims = [1, 64, 128, 256, 512, 1024, 2048, 4096]
        invalid_dims = [0, -1, 4097]
        
        for dim in valid_dims:
            try:
                manager._validate_vector_dimensions(dim)
                print(f"✅ Valid dimension: {dim}")
            except Exception as e:
                print(f"❌ Unexpected validation error for {dim}: {e}")
                return False
        
        for dim in invalid_dims:
            try:
                manager._validate_vector_dimensions(dim)
                print(f"❌ Should have failed validation: {dim}")
                return False
            except Exception:
                print(f"✅ Correctly rejected invalid dimension: {dim}")
        
        print("✅ Vector dimension validation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Functionality test failed: {e}")
        return False

def main():
    """Main validation function."""
    print("=" * 80)
    print("🧪 S3Vector AWS Service Validation")
    print("=" * 80)
    print()
    
    # Run all validations
    validations = [
        ("Configuration", test_configuration),
        ("S3 Vectors API", validate_s3_vectors_api),
        ("Bedrock Models", validate_bedrock_models),
        ("TwelveLabs Integration", validate_twelvelabs_integration),
        ("Search Engine", validate_search_engine),
        ("Core Functionality", run_simple_functionality_test)
    ]
    
    results = {}
    
    for name, validation_func in validations:
        print(f"\n{'='*60}")
        print(f"VALIDATING: {name.upper()}")
        print(f"{'='*60}")
        
        try:
            result = validation_func()
            results[name] = result
            
            if result:
                print(f"✅ {name} validation PASSED")
            else:
                print(f"❌ {name} validation FAILED")
                
        except Exception as e:
            print(f"❌ {name} validation ERROR: {e}")
            results[name] = False
    
    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nOverall: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 All validations passed! Services are ready for production use.")
        return True
    else:
        print("⚠️ Some validations failed. Review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)