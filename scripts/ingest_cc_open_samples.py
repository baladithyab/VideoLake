#!/usr/bin/env python3
"""Ingest a curated set of Creative Commons / open sample videos into S3.

This script downloads a small set of well-known public sample videos
(Blender Foundation movies + Google sample clips) and uploads them into
an S3 prefix that the Marengo embedding generator can scan.

By default it targets the s3vector-test-datasets bucket.
"""

import argparse
import os
from typing import List, Dict
from urllib.parse import urlparse
import urllib.request

import boto3


VIDEO_SPECS: List[Dict[str, str]] = [
    # Blender / Google sample videos (commonly used test assets)
    {
        "id": "big-buck-bunny",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "title": "Big Buck Bunny",
    },
    {
        "id": "sintel",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
        "title": "Sintel",
    },
    {
        "id": "elephants-dream",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "title": "Elephants Dream",
    },
    {
        "id": "tears-of-steel",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
        "title": "Tears of Steel",
    },
    {
        "id": "for-bigger-blazes",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "title": "For Bigger Blazes",
    },
    {
        "id": "for-bigger-escapes",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
        "title": "For Bigger Escapes",
    },
    {
        "id": "for-bigger-fun",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
        "title": "For Bigger Fun",
    },
    {
        "id": "for-bigger-joyrides",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
        "title": "For Bigger Joyrides",
    },
    {
        "id": "volkswagen-gti-review",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/VolkswagenGTIReview.mp4",
        "title": "Volkswagen GTI Review",
    },
]


def download_to_temp(url: str, video_id: str) -> str:
    """Download URL to a temp file and return its path."""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1] or ".mp4"
    local_path = f"/tmp/cc_{video_id}{ext}"

    print(f"  Downloading {url} -> {local_path}")
    with urllib.request.urlopen(url) as resp, open(local_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return local_path


def upload_to_s3(local_path: str, bucket: str, key: str, region: str) -> None:
    """Upload local file to S3 under the given key."""
    print(f"  Uploading {local_path} -> s3://{bucket}/{key}")
    session = boto3.session.Session(region_name=region)
    s3 = session.client("s3")
    s3.upload_file(local_path, bucket, key)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest curated Creative Commons / open sample videos into S3",
    )
    parser.add_argument(
        "--bucket",
        default="s3vector-test-datasets",
        help="Target S3 bucket",
    )
    parser.add_argument(
        "--prefix",
        default="datasets/cc-open-samples/",
        help="S3 prefix under which to store videos",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for the target S3 bucket",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Optional limit on number of videos to ingest (for quick tests)",
    )
    args = parser.parse_args()

    bucket = args.bucket
    prefix = args.prefix.rstrip("/")

    specs = VIDEO_SPECS
    if args.max_videos is not None:
        specs = specs[: args.max_videos]

    print(f"Ingesting {len(specs)} curated sample videos into s3://{bucket}/{prefix}/")

    successes = 0
    failures = 0

    for idx, spec in enumerate(specs, start=1):
        vid = spec["id"]
        url = spec["url"]
        title = spec.get("title", vid)

        print(f"\n[{idx}/{len(specs)}] {vid}: {title}")
        print(f"  URL: {url}")

        try:
            local_path = download_to_temp(url, vid)
            _, ext = os.path.splitext(local_path)
            key = f"{prefix}/{vid}{ext or '.mp4'}"
            upload_to_s3(local_path, bucket, key, region=args.region)
            successes += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ Failed to ingest {vid}: {e}")
            failures += 1

    print("\nSummary:")
    print(f"  Successes: {successes}")
    print(f"  Failures: {failures}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

