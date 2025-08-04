import os
from src.services.s3_vector_storage import S3VectorStorageManager

def main():
    region = os.getenv("AWS_REGION", "us-east-1")
    print(f"Region: {region}")
    mgr = S3VectorStorageManager()

    print("\nListing S3 Vectors buckets...")
    try:
        buckets = mgr.list_vector_buckets()
        if not buckets:
            print(" (none)")
        for b in buckets:
            name = b.get("vectorBucketName") or b.get("name") or str(b)
            enc = None
            enc_cfg = b.get("encryptionConfiguration") if isinstance(b, dict) else None
            if isinstance(enc_cfg, dict):
                enc = enc_cfg.get("sseType")
            print(f" - {name}  enc={enc}")
    except Exception as e:
        print("Error listing buckets:", e)

    print("\nEnumerating indexes per bucket...")
    try:
        buckets = mgr.list_vector_buckets()
        for b in buckets:
            bucket_name = b.get("vectorBucketName") or b.get("name") if isinstance(b, dict) else None
            if not bucket_name:
                continue
            print(f"Bucket: {bucket_name}")
            try:
                res = mgr.list_vector_indexes(bucket_name)
                idxs = res.get("indexes", [])
                if not idxs:
                    print("  (no indexes)")
                for idx in idxs:
                    if not isinstance(idx, dict):
                        print("  - (unexpected index shape)", idx)
                        continue
                    name = idx.get("indexName")
                    arn = idx.get("indexArn")
                    rid = idx.get("indexResourceName")
                    print(f"  - {name} | ARN: {arn} | ResourceId: {rid}")
            except Exception as ie:
                print("  Error listing indexes:", ie)
    except Exception as e:
        print("Error enumerating indexes:", e)

if __name__ == "__main__":
    main()