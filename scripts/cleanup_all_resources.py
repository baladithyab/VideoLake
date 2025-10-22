#!/usr/bin/env python3
"""
Cleanup All Resources Script

This script deletes all resources tracked in the resource registry and optionally
cleans up the registry entries.

Features:
1. Lists all resources in the registry
2. Identifies resources that still exist in AWS
3. Deletes all active AWS resources
4. Updates registry to mark resources as deleted
5. Optionally purges old deleted entries from registry

Usage:
    python scripts/cleanup_all_resources.py [--purge-deleted] [--dry-run]

Options:
    --purge-deleted    Remove deleted entries from registry (keeps only active)
    --dry-run          Show what would be deleted without actually deleting
    --force            Skip confirmation prompts
"""

import sys
import json
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Suppress Streamlit warnings
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'


def read_registry() -> dict:
    """Read the resource registry JSON file."""
    registry_path = project_root / "coordination" / "resource_registry.json"
    with open(registry_path, 'r') as f:
        return json.load(f)


def write_registry(data: dict):
    """Write the resource registry JSON file."""
    registry_path = project_root / "coordination" / "resource_registry.json"
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    with open(registry_path, 'w') as f:
        json.dump(data, f, indent=2)


def check_s3vector_bucket_exists(s3vectors_client, bucket_name: str) -> bool:
    """Check if an S3Vector bucket exists in AWS."""
    try:
        s3vectors_client.get_vector_bucket(vectorBucketName=bucket_name)
        return True
    except Exception:
        return False


def check_s3vector_index_exists(s3vectors_client, bucket_name: str, index_name: str) -> bool:
    """Check if an S3Vector index exists in AWS."""
    try:
        s3vectors_client.get_index(vectorBucketName=bucket_name, indexName=index_name)
        return True
    except Exception:
        return False


def check_s3_bucket_exists(s3_client, bucket_name: str) -> bool:
    """Check if an S3 bucket exists in AWS."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except Exception:
        return False


def delete_s3vector_index(s3vectors_client, bucket_name: str, index_name: str) -> bool:
    """Delete an S3Vector index."""
    try:
        s3vectors_client.delete_index(vectorBucketName=bucket_name, indexName=index_name)
        print(f"  ✅ Deleted index: {index_name}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to delete index {index_name}: {e}")
        return False


def delete_s3vector_bucket(s3vectors_client, bucket_name: str) -> bool:
    """Delete an S3Vector bucket."""
    try:
        s3vectors_client.delete_vector_bucket(vectorBucketName=bucket_name)
        print(f"  ✅ Deleted bucket: {bucket_name}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to delete bucket {bucket_name}: {e}")
        return False


def delete_s3_bucket(s3_client, bucket_name: str) -> bool:
    """Delete an S3 bucket (with emptying)."""
    try:
        # Empty the bucket first
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket_name)

            for page in pages:
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    if objects:
                        s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})

            # Delete versions
            paginator = s3_client.get_paginator('list_object_versions')
            pages = paginator.paginate(Bucket=bucket_name)

            for page in pages:
                versions = []
                if 'Versions' in page:
                    versions.extend([{'Key': v['Key'], 'VersionId': v['VersionId']} for v in page['Versions']])
                if 'DeleteMarkers' in page:
                    versions.extend([{'Key': d['Key'], 'VersionId': d['VersionId']} for d in page['DeleteMarkers']])

                if versions:
                    s3_client.delete_objects(Bucket=bucket_name, Delete={'Objects': versions})
        except:
            pass  # Bucket might be empty

        # Delete the bucket
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"  ✅ Deleted S3 bucket: {bucket_name}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to delete S3 bucket {bucket_name}: {e}")
        return False


def check_opensearch_domain_exists(opensearch_client, domain_name: str) -> bool:
    """Check if an OpenSearch domain exists in AWS."""
    try:
        opensearch_client.describe_domain(DomainName=domain_name)
        return True
    except opensearch_client.exceptions.ResourceNotFoundException:
        return False
    except Exception:
        return False


def delete_opensearch_domain(opensearch_client, domain_name: str, wait_for_deletion: bool = True) -> bool:
    """Delete an OpenSearch domain and optionally wait for deletion to complete."""
    import time

    try:
        print(f"  🗑️  Deleting OpenSearch domain: {domain_name}")
        opensearch_client.delete_domain(DomainName=domain_name)

        if wait_for_deletion:
            print(f"  ⏳ Waiting for domain deletion to complete (this may take several minutes)...")
            max_wait_time = 600  # 10 minutes
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                try:
                    response = opensearch_client.describe_domain(DomainName=domain_name)
                    domain_status = response.get('DomainStatus', {})

                    # Check if domain is being deleted
                    if domain_status.get('Deleted', False):
                        print(f"  ✅ Domain {domain_name} deleted successfully")
                        return True

                    # Check processing status
                    processing = domain_status.get('Processing', False)
                    if processing:
                        elapsed = int(time.time() - start_time)
                        print(f"  ⏳ Still deleting... ({elapsed}s elapsed)")

                    time.sleep(30)  # Check every 30 seconds

                except opensearch_client.exceptions.ResourceNotFoundException:
                    # Domain no longer exists - deletion complete
                    print(f"  ✅ Domain {domain_name} deleted successfully")
                    return True
                except Exception as e:
                    print(f"  ⚠️  Error checking domain status: {e}")
                    time.sleep(30)

            print(f"  ⚠️  Timeout waiting for domain deletion (waited {max_wait_time}s)")
            print(f"  ℹ️  Domain deletion initiated but may still be in progress")
            return True
        else:
            print(f"  ✅ Domain deletion initiated: {domain_name}")
            return True

    except Exception as e:
        print(f"  ❌ Failed to delete OpenSearch domain {domain_name}: {e}")
        return False


def cleanup_resources(dry_run: bool = False, force: bool = False):
    """Delete all resources tracked in the registry."""
    print("🧹 Resource Cleanup Script")
    print("=" * 60)

    # Read registry
    registry = read_registry()

    # Get resource counts
    vector_buckets = registry.get('vector_buckets', [])
    indexes = registry.get('indexes', [])
    s3_buckets = registry.get('s3_buckets', [])
    opensearch_domains = registry.get('opensearch_domains', [])
    opensearch_indexes = registry.get('opensearch_indexes', [])

    created_vector_buckets = [b for b in vector_buckets if b.get('status') == 'created']
    created_indexes = [i for i in indexes if i.get('status') == 'created']
    created_s3_buckets = [s for s in s3_buckets if s.get('status') == 'created']
    created_opensearch_domains = [d for d in opensearch_domains if d.get('status') == 'created']
    created_opensearch_indexes = [i for i in opensearch_indexes if i.get('status') == 'created']

    print(f"\n📊 Registry Summary:")
    print(f"  S3Vector Buckets: {len(vector_buckets)} total, {len(created_vector_buckets)} active")
    print(f"  S3Vector Indexes: {len(indexes)} total, {len(created_indexes)} active")
    print(f"  S3 Buckets: {len(s3_buckets)} total, {len(created_s3_buckets)} active")
    print(f"  OpenSearch Domains: {len(opensearch_domains)} total, {len(created_opensearch_domains)} active")
    print(f"  OpenSearch Indexes: {len(opensearch_indexes)} total, {len(created_opensearch_indexes)} active")

    if not (created_vector_buckets or created_indexes or created_s3_buckets or created_opensearch_domains or created_opensearch_indexes):
        print("\n✅ No active resources found in registry!")
        return

    # Initialize AWS clients
    try:
        from src.shared.aws_client_pool import get_pooled_client, AWSService
        from src.utils.resource_registry import resource_registry

        s3vectors_client = get_pooled_client(AWSService.S3_VECTORS)
        s3_client = get_pooled_client(AWSService.S3)
        opensearch_client = get_pooled_client(AWSService.OPENSEARCH)

        print("\n✅ AWS clients initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize AWS clients: {e}")
        return
    
    # Check which resources actually exist in AWS
    print(f"\n🔍 Checking which resources exist in AWS...")

    existing_indexes = []
    for index in created_indexes:
        bucket_name = index.get('bucket')
        index_name = index.get('name')
        if check_s3vector_index_exists(s3vectors_client, bucket_name, index_name):
            existing_indexes.append(index)
            print(f"  ⚠️  Index exists: {bucket_name}/{index_name}")

    existing_vector_buckets = []
    for bucket in created_vector_buckets:
        bucket_name = bucket.get('name')
        if check_s3vector_bucket_exists(s3vectors_client, bucket_name):
            existing_vector_buckets.append(bucket)
            print(f"  ⚠️  S3Vector bucket exists: {bucket_name}")

    existing_s3_buckets = []
    for bucket in created_s3_buckets:
        bucket_name = bucket.get('name')
        if check_s3_bucket_exists(s3_client, bucket_name):
            existing_s3_buckets.append(bucket)
            print(f"  ⚠️  S3 bucket exists: {bucket_name}")

    existing_opensearch_domains = []
    for domain in created_opensearch_domains:
        domain_name = domain.get('name')
        if check_opensearch_domain_exists(opensearch_client, domain_name):
            existing_opensearch_domains.append(domain)
            print(f"  ⚠️  OpenSearch domain exists: {domain_name}")

    # Note: OpenSearch indexes are logical entities within domains, not separate AWS resources
    # They will be deleted when the domain is deleted, so we just track them for reporting
    existing_opensearch_indexes = created_opensearch_indexes
    if existing_opensearch_indexes:
        print(f"  ℹ️  {len(existing_opensearch_indexes)} OpenSearch indexes tracked (will be deleted with domain)")

    total_existing = len(existing_indexes) + len(existing_vector_buckets) + len(existing_s3_buckets) + len(existing_opensearch_domains)

    if total_existing == 0 and len(existing_opensearch_indexes) == 0:
        print("\n✅ No resources actually exist in AWS (registry may be out of sync)")
        print("   Updating registry to remove all entries...")

        # Update registry to remove all entries
        for bucket in created_vector_buckets:
            resource_registry.log_vector_bucket_deleted(bucket.get('name'))
        for index in created_indexes:
            resource_registry.log_index_deleted(bucket_name=index.get('bucket'), index_name=index.get('name'))
        for bucket in created_s3_buckets:
            resource_registry.log_s3_bucket_deleted(bucket.get('name'))
        for domain in created_opensearch_domains:
            resource_registry.log_opensearch_domain_deleted(domain.get('name'))
        # OpenSearch indexes will be removed when we clean up the registry

        print("✅ Registry updated")
        return

    print(f"\n⚠️  Found {total_existing} resources that exist in AWS:")
    print(f"  - {len(existing_indexes)} S3Vector indexes")
    print(f"  - {len(existing_vector_buckets)} S3Vector buckets")
    print(f"  - {len(existing_s3_buckets)} S3 buckets")
    print(f"  - {len(existing_opensearch_domains)} OpenSearch domains")
    if existing_opensearch_indexes:
        print(f"  - {len(existing_opensearch_indexes)} OpenSearch indexes (in registry)")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No resources will be deleted")
        print("\nWould delete:")
        for index in existing_indexes:
            print(f"  - Index: {index.get('bucket')}/{index.get('name')}")
        for bucket in existing_vector_buckets:
            print(f"  - S3Vector Bucket: {bucket.get('name')}")
        for bucket in existing_s3_buckets:
            print(f"  - S3 Bucket: {bucket.get('name')}")
        for domain in existing_opensearch_domains:
            print(f"  - OpenSearch Domain: {domain.get('name')}")
        if existing_opensearch_indexes:
            print(f"  - {len(existing_opensearch_indexes)} OpenSearch indexes (removed from registry)")
        return

    # Confirm deletion
    if not force:
        total_to_delete = total_existing
        if existing_opensearch_indexes:
            total_to_delete += len(existing_opensearch_indexes)
        print(f"\n⚠️  WARNING: This will DELETE {total_to_delete} resources from AWS and registry!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cleanup cancelled")
            return

    # Delete resources
    print(f"\n🗑️  Deleting resources...")

    # Delete OpenSearch domains first (they contain indexes)
    if existing_opensearch_domains:
        print(f"\n🔍 Deleting {len(existing_opensearch_domains)} OpenSearch domains...")
        for domain in existing_opensearch_domains:
            domain_name = domain.get('name')
            # Wait for deletion to complete
            if delete_opensearch_domain(opensearch_client, domain_name, wait_for_deletion=True):
                resource_registry.log_opensearch_domain_deleted(domain_name)

    # Remove OpenSearch indexes from registry (they're deleted with the domain)
    if existing_opensearch_indexes:
        print(f"\n📊 Removing {len(existing_opensearch_indexes)} OpenSearch indexes from registry...")
        # Since we don't have a specific delete method for OpenSearch indexes,
        # we'll manually remove them from the registry
        registry = read_registry()
        registry['opensearch_indexes'] = []
        write_registry(registry)
        print(f"  ✅ Removed {len(existing_opensearch_indexes)} OpenSearch indexes from registry")

    # Delete S3Vector indexes
    if existing_indexes:
        print(f"\n📊 Deleting {len(existing_indexes)} S3Vector indexes...")
        for index in existing_indexes:
            bucket_name = index.get('bucket')
            index_name = index.get('name')
            if delete_s3vector_index(s3vectors_client, bucket_name, index_name):
                resource_registry.log_index_deleted(bucket_name=bucket_name, index_name=index_name)

    # Delete S3Vector buckets
    if existing_vector_buckets:
        print(f"\n🪣 Deleting {len(existing_vector_buckets)} S3Vector buckets...")
        for bucket in existing_vector_buckets:
            bucket_name = bucket.get('name')
            if delete_s3vector_bucket(s3vectors_client, bucket_name):
                resource_registry.log_vector_bucket_deleted(bucket_name)

    # Delete S3 buckets
    if existing_s3_buckets:
        print(f"\n🪣 Deleting {len(existing_s3_buckets)} S3 buckets...")
        for bucket in existing_s3_buckets:
            bucket_name = bucket.get('name')
            if delete_s3_bucket(s3_client, bucket_name):
                resource_registry.log_s3_bucket_deleted(bucket_name)

    print(f"\n✅ Cleanup completed!")


def purge_deleted_entries():
    """Remove all deleted entries from the registry."""
    print("\n🧹 Purging deleted entries from registry...")
    
    registry = read_registry()
    
    # Count before
    before_buckets = len(registry.get('vector_buckets', []))
    before_indexes = len(registry.get('indexes', []))
    before_s3 = len(registry.get('s3_buckets', []))
    
    # Keep only created resources
    registry['vector_buckets'] = [b for b in registry.get('vector_buckets', []) if b.get('status') == 'created']
    registry['indexes'] = [i for i in registry.get('indexes', []) if i.get('status') == 'created']
    registry['s3_buckets'] = [s for s in registry.get('s3_buckets', []) if s.get('status') == 'created']
    
    # Count after
    after_buckets = len(registry['vector_buckets'])
    after_indexes = len(registry['indexes'])
    after_s3 = len(registry['s3_buckets'])
    
    # Write updated registry
    write_registry(registry)
    
    print(f"  S3Vector Buckets: {before_buckets} → {after_buckets} (removed {before_buckets - after_buckets})")
    print(f"  S3Vector Indexes: {before_indexes} → {after_indexes} (removed {before_indexes - after_indexes})")
    print(f"  S3 Buckets: {before_s3} → {after_s3} (removed {before_s3 - after_s3})")
    print(f"\n✅ Registry purged!")


def main():
    parser = argparse.ArgumentParser(description='Cleanup all resources from AWS and registry')
    parser.add_argument('--purge-deleted', action='store_true', help='Remove deleted entries from registry')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without deleting')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        # Cleanup active resources
        cleanup_resources(dry_run=args.dry_run, force=args.force)
        
        # Purge deleted entries if requested
        if args.purge_deleted and not args.dry_run:
            purge_deleted_entries()
        
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Clean exit
    os._exit(0)


if __name__ == "__main__":
    main()

