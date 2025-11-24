import boto3
import sys

def empty_bucket(bucket_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    
    try:
        print(f"Emptying bucket: {bucket_name}")
        bucket.object_versions.delete()
        print(f"Successfully emptied bucket: {bucket_name}")
    except Exception as e:
        print(f"Error emptying bucket {bucket_name}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python empty_bucket.py <bucket_name>")
        sys.exit(1)
    
    empty_bucket(sys.argv[1])