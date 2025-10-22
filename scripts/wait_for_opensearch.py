#!/usr/bin/env python3
"""
Wait for OpenSearch Domain Script

This script waits for an OpenSearch domain to become active and reports progress.

Usage:
    python scripts/wait_for_opensearch.py DOMAIN_NAME [--max-wait MINUTES]

Options:
    --max-wait MINUTES    Maximum time to wait in minutes (default: 20)
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def wait_for_domain(domain_name: str, max_wait_minutes: int = 20):
    """Wait for OpenSearch domain to become active."""
    
    print("=" * 70)
    print("⏳ Waiting for OpenSearch Domain")
    print("=" * 70)
    print(f"\nDomain Name: {domain_name}")
    print(f"Max Wait Time: {max_wait_minutes} minutes")
    print("=" * 70)
    
    try:
        from src.shared.aws_client_pool import get_pooled_client, AWSService
        opensearch_client = get_pooled_client(AWSService.OPENSEARCH)
        print("\n✅ AWS client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize AWS client: {e}")
        return False
    
    max_wait_seconds = max_wait_minutes * 60
    start_time = time.time()
    check_interval = 30  # Check every 30 seconds
    
    print(f"\n⏳ Checking domain status every {check_interval} seconds...")
    
    while time.time() - start_time < max_wait_seconds:
        try:
            response = opensearch_client.describe_domain(DomainName=domain_name)
            domain_status = response.get('DomainStatus', {})
            
            # Get status information
            processing = domain_status.get('Processing', False)
            created = domain_status.get('Created', False)
            deleted = domain_status.get('Deleted', False)
            endpoint = domain_status.get('Endpoint', None)
            
            elapsed_seconds = int(time.time() - start_time)
            elapsed_minutes = elapsed_seconds // 60
            elapsed_secs = elapsed_seconds % 60
            
            if deleted:
                print(f"\n❌ Domain has been deleted!")
                return False
            
            if created and not processing and endpoint:
                print(f"\n✅ Domain is ACTIVE!")
                print(f"   Endpoint: {endpoint}")
                print(f"   Total time: {elapsed_minutes}m {elapsed_secs}s")
                return True
            
            # Show progress
            status_msg = "Creating"
            if processing:
                status_msg = "Processing"
            elif created:
                status_msg = "Created (waiting for endpoint)"
            
            print(f"   [{elapsed_minutes:02d}:{elapsed_secs:02d}] Status: {status_msg}...", end='\r')
            
            time.sleep(check_interval)
            
        except opensearch_client.exceptions.ResourceNotFoundException:
            print(f"\n❌ Domain not found: {domain_name}")
            return False
        except Exception as e:
            elapsed_seconds = int(time.time() - start_time)
            elapsed_minutes = elapsed_seconds // 60
            elapsed_secs = elapsed_seconds % 60
            print(f"\n⚠️  [{elapsed_minutes:02d}:{elapsed_secs:02d}] Error checking status: {e}")
            time.sleep(check_interval)
    
    # Timeout
    print(f"\n⏰ Timeout after {max_wait_minutes} minutes")
    print(f"   Domain may still be creating. Check status with:")
    print(f"   aws opensearch describe-domain --domain-name {domain_name}")
    return False


def check_domain_status(domain_name: str):
    """Check current status of OpenSearch domain."""
    
    print("=" * 70)
    print("🔍 OpenSearch Domain Status")
    print("=" * 70)
    print(f"\nDomain Name: {domain_name}")
    print("=" * 70)
    
    try:
        from src.shared.aws_client_pool import get_pooled_client, AWSService
        opensearch_client = get_pooled_client(AWSService.OPENSEARCH)
    except Exception as e:
        print(f"\n❌ Failed to initialize AWS client: {e}")
        return
    
    try:
        response = opensearch_client.describe_domain(DomainName=domain_name)
        domain_status = response.get('DomainStatus', {})
        
        print(f"\n📊 Domain Information:")
        print(f"   Name: {domain_status.get('DomainName', 'N/A')}")
        print(f"   ARN: {domain_status.get('ARN', 'N/A')}")
        print(f"   Created: {domain_status.get('Created', False)}")
        print(f"   Processing: {domain_status.get('Processing', False)}")
        print(f"   Deleted: {domain_status.get('Deleted', False)}")
        print(f"   Endpoint: {domain_status.get('Endpoint', 'Not available yet')}")
        print(f"   Engine Version: {domain_status.get('EngineVersion', 'N/A')}")
        
        # Cluster config
        cluster_config = domain_status.get('ClusterConfig', {})
        print(f"\n🖥️  Cluster Configuration:")
        print(f"   Instance Type: {cluster_config.get('InstanceType', 'N/A')}")
        print(f"   Instance Count: {cluster_config.get('InstanceCount', 'N/A')}")
        
        # S3Vectors
        s3vectors = domain_status.get('S3VectorsOptions', {})
        if s3vectors:
            print(f"\n📊 S3Vectors Configuration:")
            print(f"   Enabled: {s3vectors.get('Enabled', False)}")
        
        # Status summary
        processing = domain_status.get('Processing', False)
        created = domain_status.get('Created', False)
        deleted = domain_status.get('Deleted', False)
        endpoint = domain_status.get('Endpoint', None)
        
        print(f"\n📋 Status Summary:")
        if deleted:
            print(f"   ❌ Domain is DELETED")
        elif created and not processing and endpoint:
            print(f"   ✅ Domain is ACTIVE and ready to use")
        elif created and processing:
            print(f"   ⏳ Domain is being updated/processed")
        elif created and not endpoint:
            print(f"   ⏳ Domain created, waiting for endpoint")
        else:
            print(f"   ⏳ Domain is being created")
        
    except opensearch_client.exceptions.ResourceNotFoundException:
        print(f"\n❌ Domain not found: {domain_name}")
    except Exception as e:
        print(f"\n❌ Error checking domain status: {e}")


def main():
    parser = argparse.ArgumentParser(description='Wait for OpenSearch domain to become active')
    parser.add_argument('domain_name', type=str, help='OpenSearch domain name')
    parser.add_argument('--max-wait', type=int, default=20, help='Maximum time to wait in minutes')
    parser.add_argument('--status-only', action='store_true', help='Only check status, do not wait')
    
    args = parser.parse_args()
    
    if args.status_only:
        check_domain_status(args.domain_name)
    else:
        success = wait_for_domain(args.domain_name, args.max_wait)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

