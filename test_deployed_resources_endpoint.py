"""
Quick test script for the deployed resources tree endpoint.
"""

import requests
import json

def test_deployed_resources_tree():
    """Test the deployed resources tree endpoint."""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/resources/deployed-resources-tree"
    
    try:
        print("Testing deployed resources tree endpoint...")
        print(f"URL: {endpoint}")
        
        response = requests.get(endpoint, timeout=10)
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Endpoint is working!")
            print("\nResponse structure:")
            print(json.dumps(data, indent=2, default=str))
            
            # Verify structure
            assert "success" in data, "Missing 'success' field"
            assert "tree" in data, "Missing 'tree' field"
            
            tree = data["tree"]
            assert "shared_resources" in tree, "Missing 'shared_resources'"
            assert "vector_backends" in tree, "Missing 'vector_backends'"
            
            print("\n✅ All structure validations passed!")
            
            # Print summary
            shared_count = len(tree["shared_resources"].get("children", []))
            backend_count = len(tree["vector_backends"])
            
            print(f"\n📊 Summary:")
            print(f"  - Shared Resources: {shared_count}")
            print(f"  - Vector Backends: {backend_count}")
            
            for backend in tree["vector_backends"]:
                children_count = len(backend.get("children", []))
                status = backend.get("status", "unknown")
                print(f"  - {backend['name']}: {status} ({children_count} resources)")
            
            return True
        else:
            print(f"\n❌ Unexpected status code: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n⚠️  Could not connect to API server.")
        print("Make sure the API is running with: python run_api.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_deployed_resources_tree()
    exit(0 if success else 1)