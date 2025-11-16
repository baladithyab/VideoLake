#!/usr/bin/env python3
"""Ingest a small MSR-VTT sample into s3vector-test-datasets.

Uses the AlexZigma/msr-vtt HuggingFace dataset (metadata + URLs) to download
30-50 unique videos and upload them into an S3 prefix that our Marengo
embedding generator already scans.

This keeps ingestion lightweight while following the documented dataset plan
in docs/COMPREHENSIVE_DATASET_RESEARCH.md.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse
import urllib.request

import boto3
from datasets import load_dataset


def pick_unique_videos(dataset, max_videos: int) -> Dict[str, Dict]:
    """Select up to max_videos unique video_ids from the dataset.

    The AlexZigma/msr-vtt dataset is caption-centric (multiple rows per
    video_id). We pick the first example per video_id to get a URL and one
    representative caption.
    """
    by_video: Dict[str, Dict] = {}
    for example in dataset:
        vid = str(example.get("video_id"))
        if not vid or vid in by_video:
            continue
        by_video[vid] = example
        if 0 < max_videos <= len(by_video):
            break
    return by_video


def download_to_temp(url: str, video_id: str) -> str:
    """Download URL to a temp file and return its path."""
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1] or ".mp4"
    local_path = f"/tmp/msrvtt_{video_id}{ext}"

    print(f"  Downloading {url} -> {local_path}")
    with urllib.request.urlopen(url) as resp, open(local_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return local_path


def upload_to_s3(local_path: str, bucket: str, key: str, region: str = "us-east-1") -> None:
    """Upload a local file to S3 and delete it afterwards."""
    s3 = boto3.client("s3", region_name=region)
    print(f"  Uploading {local_path} -> s3://{bucket}/{key}")
    s3.upload_file(local_path, bucket, key)
    try:
        os.remove(local_path)
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a small MSR-VTT sample into S3")
    parser.add_argument("--bucket", default="s3vector-test-datasets", help="Target S3 bucket")
    parser.add_argument(
        "--prefix",
        default="datasets/MSR-VTT/",
        help="S3 prefix under which to store videos",
    )
    parser.add_argument(
        "--dataset-id",
        default="AlexZigma/msr-vtt",
        help="HuggingFace dataset ID to use for MSR-VTT",
    )
    parser.add_argument(
        "--split",
        default="train",
        help="Dataset split to sample from (e.g. train or val)",
    )
    parser.add_argument(
        "--num-videos",
        type=int,
        default=40,
        help="Number of unique video_ids to ingest",
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region for the target S3 bucket",
    )
    args = parser.parse_args()

    print(f"Loading dataset {args.dataset_id} (split={args.split}) via datasets.load_dataset()...")
    ds = load_dataset(args.dataset_id, split=args.split)
    print(f"Loaded split with {len(ds)} rows")

    by_video = pick_unique_videos(ds, args.num_videos)
    print(f"Selected {len(by_video)} unique video_ids to ingest")

    bucket = args.bucket
    prefix = args.prefix.rstrip("/")

    successes = 0
    failures = 0

    for idx, (video_id, example) in enumerate(by_video.items(), start=1):
        url = example.get("url")
        caption = example.get("caption")
        print(f"\n[{idx}/{len(by_video)}] video_id={video_id}")
        print(f"  URL: {url}")
        if caption:
            print(f"  Caption: {caption[:120]}" + ("..." if len(caption) > 120 else ""))

        if not url:
            print("  Skipping: missing URL")
            failures += 1
            continue

        try:
            local_path = download_to_temp(url, video_id)
            ext = os.path.splitext(local_path)[1] or ".mp4"
            key = f"{prefix}/{video_id}{ext}"
            upload_to_s3(local_path, bucket, key, region=args.region)
            successes += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ Failed to ingest {video_id}: {e}")
            failures += 1

    print("\nIngestion complete.")
    print(f"  Successful videos: {successes}")
    print(f"  Failed videos: {failures}")
    print(f"  Target prefix: s3://{bucket}/{prefix}/")

    return 0 if successes > 0 else 1


if __name__ == "__main__":  # pragma: no cover - CLI entry
    sys.exit(main())

