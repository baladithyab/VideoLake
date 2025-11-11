#!/usr/bin/env python3
"""
Test script for backend connectivity validation endpoints.

Demonstrates how to use the new validation endpoints to check
which vector store backends are accessible before processing.
"""

import requests
import json
import sys
from typing import Dict, Any


def test_single_backend_validation(base_url: str, backend_type: str) -> Dict[str, Any]:
    """
    Test single backend validation endpoint.
    
    Args:
        base_url: Base URL of the API (e.g., http://localhost:8000)
        backend_type: Type of backend to validate (s3_vector, opensearch, qdrant, lancedb)
    
    Returns:
        Validation result dictionary
    """
    print(f"\n{'='*60}")
    print(f"Testing single backend validation: {backend_type}")
    print(f"{'='*60}")
    
    url = f"{base_url}/api/resources/validate-backend/{backend_type}"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            validation = result.get("validation", {})
            print(f"\n✓ Backend {backend_type} is accessible")
            print(f"  Endpoint: {validation.get('endpoint')}")
            print(f"  Response Time: {validation.get('response_time_ms')}ms")
            print(f"  Health Status: {validation.get('health_status')}")
            if validation.get('details'):
                print(f"  Details: {json.dumps(validation.get('details'), indent=4)}")
        else:
            validation = result.get("validation", {})
            print(f"\n✗ Backend {backend_type} is NOT accessible")
            print(f"  Error: {validation.get('error_message')}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return {"success": False, "error": str(e)}


def test_batch_backend_validation(base_url: str, backend_types: list) -> Dict[str, Any]:
    """
    Test batch backend validation endpoint.
    
    Args:
        base_url: Base URL of the API
        backend_types: List of backend types to validate
    
    Returns:
        Validation results dictionary
    """
    print(f"\n{'='*60}")
    print(f"Testing batch backend validation")
    print(f"Backends: {', '.join(backend_types)}")
    print(f"{'='*60}")
    
    url = f"{base_url}/api/resources/validate-backends"
    payload = {"backend_types": backend_types}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        result = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"\nSummary:")
        print(f"  Total Backends: {result.get('total_backends')}")
        print(f"  Accessible: {result.get('accessible_backends')}")
        print(f"  Inaccessible: {result.get('inaccessible_backends')}")
        
        print(f"\nDetailed Results:")
        for backend_type, validation in result.get("results", {}).items():
            accessible = validation.get("accessible", False)
            status_icon = "✓" if accessible else "✗"
            print(f"\n{status_icon} {backend_type}:")
            print(f"    Accessible: {accessible}")
            print(f"    Endpoint: {validation.get('endpoint')}")
            print(f"    Response Time: {validation.get('response_time_ms')}ms")
            print(f"    Health Status: {validation.get('health_status')}")
            if validation.get("error_message"):
                print(f"    Error: {validation.get('error_message')}")
            if validation.get('details'):
                print(f"    Details: {json.dumps(validation.get('details'), indent=6)}")
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {e}")
        return {"success": False, "error": str(e)}


def main():
    """Main test function."""
    # Configuration
    base_url = "http://localhost:8000"
    
    print("="*60)
    print("Backend Connectivity Validation Test")
    print("="*60)
    print(f"API Base URL: {base_url}")
    
    # Test 1: Single backend validation - S3 Vector
    result1 = test_single_backend_validation(base_url, "s3_vector")
    
    # Test 2: Single backend validation - OpenSearch
    result2 = test_single_backend_validation(base_url, "opensearch")
    
    # Test 3: Single backend validation - Qdrant
    result3 = test_single_backend_validation(base_url, "qdrant")
    
    # Test 4: Single backend validation - LanceDB
    result4 = test_single_backend_validation(base_url, "lancedb")
    
    # Test 5: Batch validation for all backends
    all_backends = ["s3_vector", "opensearch", "qdrant", "lancedb"]
    batch_result = test_batch_backend_validation(base_url, all_backends)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    
    accessible_backends = []
    if batch_result.get("success"):
        for backend, validation in batch_result.get("results", {}).items():
            if validation.get("accessible"):
                accessible_backends.append(backend)
    
    print(f"\nAccessible Backends ({len(accessible_backends)}/{len(all_backends)}):")
    for backend in accessible_backends:
        print(f"  ✓ {backend}")
    
    inaccessible_backends = [b for b in all_backends if b not in accessible_backends]
    if inaccessible_backends:
        print(f"\nInaccessible Backends ({len(inaccessible_backends)}/{len(all_backends)}):")
        for backend in inaccessible_backends:
            print(f"  ✗ {backend}")
    
    print(f"\n{'='*60}")
    print("Recommendations:")
    print(f"{'='*60}")
    
    if "s3_vector" in accessible_backends:
        print("✓ S3 Vector backend is available - recommended for production AWS deployments")
    else:
        print("✗ S3 Vector backend is NOT available - check AWS credentials and permissions")
    
    if "opensearch" in accessible_backends:
        print("✓ OpenSearch backend is available - good for hybrid search workloads")
    else:
        print("✗ OpenSearch backend is NOT available - check if domains are deployed")
    
    if "qdrant" in accessible_backends:
        print("✓ Qdrant backend is available - excellent for advanced filtering")
    else:
        print("✗ Qdrant backend is NOT available - check if Qdrant server is running")
    
    if "lancedb" in accessible_backends:
        print("✓ LanceDB backend is available - good for local development")
    else:
        print("✗ LanceDB backend is NOT available - check storage configuration")
    
    # Exit code based on results
    if len(accessible_backends) == 0:
        print("\n⚠️  WARNING: No backends are accessible!")
        sys.exit(1)
    elif len(accessible_backends) < len(all_backends):
        print(f"\n⚠️  WARNING: Only {len(accessible_backends)} of {len(all_backends)} backends are accessible")
        sys.exit(0)
    else:
        print("\n✓ All backends are accessible!")
        sys.exit(0)


if __name__ == "__main__":
    main()