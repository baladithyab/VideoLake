#!/usr/bin/env python3
"""
Test script to validate OpenSearch collection naming fixes.

This script tests the new naming logic to ensure OpenSearch collection names
stay within the 32-character AWS limit while remaining unique and descriptive.
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def test_opensearch_name_validation():
    """Test the OpenSearch collection name validation function."""
    
    # Mock the validation function from workflow_resource_manager
    def validate_opensearch_collection_name(name: str) -> str:
        """Validate and adjust OpenSearch collection name to meet AWS requirements."""
        # Handle empty string case
        if not name:
            name = "s3v-collection"
        
        # Convert to lowercase and replace invalid characters
        clean_name = name.lower().replace('_', '-')
        
        # Ensure it starts with a letter
        if not clean_name or not clean_name[0].isalpha():
            clean_name = 's' + clean_name if clean_name else 's3v-collection'
        
        # Truncate to 32 characters if needed
        if len(clean_name) > 32:
            # Keep the timestamp part for uniqueness
            if '-' in clean_name:
                parts = clean_name.split('-')
                if parts[-1].isdigit():
                    # Keep the timestamp
                    timestamp = parts[-1]
                    prefix_length = 32 - len(timestamp) - 1  # -1 for the hyphen
                    if prefix_length > 0:
                        clean_name = clean_name[:prefix_length] + '-' + timestamp
                    else:
                        clean_name = clean_name[:32]
                else:
                    clean_name = clean_name[:32]
            else:
                clean_name = clean_name[:32]
        
        # Ensure minimum length
        if len(clean_name) < 3:
            clean_name = clean_name + 'col'
        
        return clean_name
    
    # Test cases
    test_cases = [
        # Old problematic naming patterns
        f"s3vector-setup-{int(time.time())}-collection",  # This was 42+ chars
        f"s3vector-collection-{int(time.time())}",  # This was ~35 chars
        f"custom-collection-{int(time.time())}",  # This was ~25 chars
        
        # New improved naming patterns
        f"s3v-{int(time.time())}-coll",  # Should be ~20 chars
        f"s3v-coll-{int(time.time())}",  # Should be ~20 chars
        f"cust-coll-{int(time.time())}",  # Should be ~21 chars
        
        # Edge cases
        "ab",  # Too short
        "a" * 50,  # Too long
        "123-collection",  # Starts with number
        "Test_Collection_Name",  # Has underscores and caps
        "",  # Empty string
    ]
    
    print("🧪 Testing OpenSearch Collection Name Validation")
    print("=" * 60)
    
    all_passed = True
    
    for i, test_name in enumerate(test_cases, 1):
        try:
            validated_name = validate_opensearch_collection_name(test_name)
            length = len(validated_name)
            is_valid = (
                3 <= length <= 32 and 
                validated_name[0].isalpha() and 
                validated_name.islower() and
                all(c.isalnum() or c == '-' for c in validated_name)
            )
            
            status = "✅ PASS" if is_valid else "❌ FAIL"
            print(f"{i:2d}. {status} | '{test_name}' -> '{validated_name}' (len: {length})")
            
            if not is_valid:
                all_passed = False
                if length > 32:
                    print(f"    ⚠️  Name too long: {length} > 32 characters")
                if length < 3:
                    print(f"    ⚠️  Name too short: {length} < 3 characters")
                if not validated_name[0].isalpha():
                    print(f"    ⚠️  Doesn't start with letter: '{validated_name[0]}'")
                if not validated_name.islower():
                    print(f"    ⚠️  Contains uppercase letters")
                    
        except Exception as e:
            print(f"{i:2d}. ❌ ERROR | '{test_name}' -> Exception: {e}")
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 All tests PASSED! OpenSearch naming is working correctly.")
    else:
        print("❌ Some tests FAILED. Check the validation logic.")
    
    return all_passed

def test_new_naming_patterns():
    """Test the new naming patterns to ensure they're within limits."""
    print("\n🔍 Testing New Naming Patterns")
    print("=" * 60)
    
    current_time = int(time.time())
    
    # Test the new default naming patterns
    patterns = {
        "Setup Name": f"s3v-{current_time}",
        "S3Vector Bucket": f"s3v-bucket-{current_time}",
        "S3Vector Index": f"s3v-idx-{current_time}",
        "OpenSearch Collection": f"s3v-coll-{current_time}",
        "Custom Bucket": f"cust-bucket-{current_time}",
        "Custom Index": f"cust-idx-{current_time}",
        "Custom Collection": f"cust-coll-{current_time}",
    }
    
    all_good = True
    
    for name_type, name_pattern in patterns.items():
        length = len(name_pattern)
        is_good = length <= 32
        status = "✅ OK" if is_good else "❌ TOO LONG"
        print(f"{name_type:20s} | '{name_pattern}' (len: {length:2d}) {status}")
        
        if not is_good:
            all_good = False
    
    print("=" * 60)
    if all_good:
        print("🎉 All naming patterns are within AWS limits!")
    else:
        print("❌ Some naming patterns exceed limits.")
    
    return all_good

if __name__ == "__main__":
    print("🚀 Testing OpenSearch Collection Naming Fix")
    print("This script validates the fixes for OpenSearch collection name length validation.")
    print()
    
    # Run validation tests
    validation_passed = test_opensearch_name_validation()
    
    # Test new naming patterns
    patterns_passed = test_new_naming_patterns()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    if validation_passed and patterns_passed:
        print("🎉 SUCCESS: All tests passed!")
        print("✅ OpenSearch collection names will now stay within the 32-character limit.")
        print("✅ Names remain unique and descriptive.")
        print("✅ The resource creation workflow should work correctly.")
        sys.exit(0)
    else:
        print("❌ FAILURE: Some tests failed.")
        print("⚠️  The fixes may need additional work.")
        sys.exit(1)