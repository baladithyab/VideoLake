import os
import time
import argparse
from typing import List, Optional
from src.services.s3_vector_storage import S3VectorStorageManager

def delete_all_indexes_in_bucket(mgr: S3VectorStorageManager, bucket_name: str, prefix: Optional[str] = None, dry_run: bool = False) -> None:
    try:
        res = mgr.list_vector_indexes(bucket_name, prefix=prefix if prefix else None)
        idxs = res.get("indexes", [])
        if not idxs:
            print(f"  (no indexes in {bucket_name} matching prefix='{prefix or ''}')")
            return
        for idx in idxs:
            name = idx.get("indexName")
            if prefix and name and not name.startswith(prefix):
                continue
            rid = idx.get("indexResourceName") or (f"bucket/{bucket_name}/index/{name}" if name else None)
            action = "Would delete" if dry_run else "Deleting"
            print(f"  - {action} index: {name} ({rid})")
            if dry_run:
                continue
            try:
                if rid:
                    # Prefer robust retry helper for eventual consistency
                    mgr.delete_index_with_retries(bucket_name, name, max_attempts=6, backoff_base=1.0)
                else:
                    mgr.delete_index_with_retries(bucket_name, name, max_attempts=6, backoff_base=1.0)
            except Exception as e:
                print(f"    Delete index error (ignored): {e}")
            time.sleep(0.2)
    except Exception as e:
        print(f"  List indexes error for {bucket_name}: {e}")

def delete_vector_bucket_if_supported(mgr: S3VectorStorageManager, bucket_name: str, dry_run: bool = False) -> None:
    try:
        client = mgr.s3vectors_client
        if hasattr(client, "delete_vector_bucket"):
            action = "Would delete" if dry_run else "Deleting"
            print(f"  - {action} vector bucket via API: {bucket_name}")
            if dry_run:
                return
            # Retry delete bucket with exponential backoff; ignore not found on final attempt
            attempts, backoff = 6, 1.0
            for attempt in range(1, attempts + 1):
                try:
                    client.delete_vector_bucket(vectorBucketName=bucket_name)
                    return
                except Exception as e:
                    # Best-effort code extraction
                    code = getattr(getattr(e, "response", {}), "get", lambda *_: {})("Error", {}).get("Code", "")
                    if attempt == attempts:
                        print(f"    Final attempt failed deleting bucket {bucket_name}: {code or e}")
                        return
                    print(f"    Retry bucket delete in {backoff:.1f}s due to {code or e}")
                    time.sleep(backoff)
                    backoff *= 2
        else:
            print("  - delete_vector_bucket API not available; bucket may persist after index deletion.")
    except Exception as e:
        print(f"  Delete bucket error (ignored): {e}")

def main() -> None:
    """
    Cleanup script for S3 Vectors:
      - Deletes indexes in specified vector buckets
      - Supports targeted cleanup with --prefix (only indices starting with prefix)
      - Supports --dry-run to list what would be deleted without performing deletion
      - Attempts to delete the vector bucket if the API is available (after index cleanup)

    Examples:
      python scripts/cleanup_s3vectors_buckets.py --prefix 20250804T101530-1a2b3c4d my-test-bucket
      python scripts/cleanup_s3vectors_buckets.py --dry-run my-test-bucket another-bucket
      python scripts/cleanup_s3vectors_buckets.py  # discovers buckets with 's3vector-integration-test-' prefix
    """
    parser = argparse.ArgumentParser(description="Cleanup S3 Vectors buckets and indexes safely.")
    parser.add_argument("buckets", nargs="*", help="Vector bucket names to clean (optional if using --pattern for discovery)")
    parser.add_argument("--pattern", required=True, help="REQUIRED: Bucket name pattern for discovery or validation (e.g., 's3vector-demo-', 's3vector-test-')")
    parser.add_argument("--prefix", help="Only delete indexes whose names start with this prefix", default=None)
    parser.add_argument("--dry-run", action="store_true", help="List what would be deleted without deleting")
    args = parser.parse_args()

    region = os.getenv("AWS_REGION", "us-west-2")
    print(f"Region: {region}")
    print(f"Options: pattern={args.pattern} prefix={args.prefix or ''} dry_run={args.dry_run}")
    mgr = S3VectorStorageManager()

    bucket_args: List[str] = args.buckets or []
    if not bucket_args:
        # Discover buckets, filter by provided pattern for safety
        print(f"\nDiscovering vector buckets with '{args.pattern}' pattern...")
        try:
            buckets = mgr.list_vector_buckets()
            candidates = []
            for b in buckets:
                name = b.get("vectorBucketName") or b.get("name")
                if not name:
                    continue
                if name.startswith(args.pattern):
                    candidates.append(name)
            if not candidates:
                print("  (no candidate buckets found matching pattern)")
                return
            print("Candidates:")
            for c in candidates:
                print(" -", c)
            # Proceed without interactive prompt (non-interactive script)
            bucket_args = candidates
        except Exception as e:
            print("Error discovering buckets:", e)
            return
    else:
        # Validate explicit bucket names against pattern for safety
        print(f"\nValidating explicit bucket names against pattern '{args.pattern}'...")
        for bucket_name in bucket_args:
            if not bucket_name.startswith(args.pattern):
                print(f"ERROR: Bucket '{bucket_name}' does not match required pattern '{args.pattern}'")
                print("This safety check prevents accidental deletion of non-test buckets.")
                return

    for bucket in bucket_args:
        print(f"\nCleaning bucket: {bucket}")
        delete_all_indexes_in_bucket(mgr, bucket, prefix=args.prefix, dry_run=args.dry_run)
        time.sleep(0.5)
        delete_vector_bucket_if_supported(mgr, bucket, dry_run=args.dry_run)

    print("\nCleanup attempt completed.")

if __name__ == "__main__":
    main()