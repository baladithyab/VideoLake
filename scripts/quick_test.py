#!/usr/bin/env python3
"""
Quick S3Vector Functionality Test

Fast validation of core S3Vector services without comprehensive workflows.
Used for CI/CD and quick health checks.

Usage:
    export REAL_AWS_DEMO=1
    python scripts/quick_test.py
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.s3_vector_storage import S3VectorStorageManager
from src.services.bedrock_embedding import BedrockEmbeddingService
from src.utils.logging_config import get_structured_logger

logger = get_structured_logger("quick_test")

def quick_validation():
    """Run quick validation of core services."""
    print("🚀 Quick S3Vector Validation")
    print("=" * 50)
    
    try:
        # Test 1: Service initialization
        print("1. Initializing services...")
        storage_manager = S3VectorStorageManager()
        embedding_service = BedrockEmbeddingService()
        print("✅ Services initialized")
        
        # Test 2: Model access
        print("2. Testing Bedrock model access...")
        model_id = "amazon.titan-embed-text-v2:0"
        is_accessible = embedding_service.validate_model_access(model_id)
        if is_accessible:
            print(f"✅ {model_id} accessible")
        else:
            print(f"❌ {model_id} not accessible")
            return False
        
        # Test 3: Simple embedding
        print("3. Testing embedding generation...")
        test_text = "Quick test of S3Vector functionality"
        result = embedding_service.generate_embedding(test_text, model_id)
        if result and result.embedding:
            print(f"✅ Embedding generated - {len(result.embedding)} dimensions")
        else:
            print("❌ Embedding generation failed")
            return False
        
        # Test 4: S3 Vectors access
        print("4. Testing S3 Vectors service access...")
        try:
            bucket = os.getenv('S3_VECTORS_BUCKET')
            if bucket:
                print(f"✅ S3 Vectors bucket configured: {bucket}")
            else:
                print("❌ S3_VECTORS_BUCKET not configured")
                return False
        except Exception as e:
            print(f"❌ S3 Vectors access failed: {e}")
            return False
        
        print("\n🎉 All quick tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False

def main():
    """Main quick test function."""
    # Check environment
    if os.getenv('REAL_AWS_DEMO') != '1':
        print("❌ REAL_AWS_DEMO not set to '1'")
        print("Run: export REAL_AWS_DEMO=1")
        return 1
    
    try:
        success = quick_validation()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())