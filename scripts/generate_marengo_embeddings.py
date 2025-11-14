#!/usr/bin/env python3
"""Generate real TwelveLabs Marengo embeddings via Bedrock async inference.

This script discovers media files in S3, runs Bedrock async jobs through
TwelveLabsVideoProcessingService, waits for completion, and writes per-modality
embedding JSON files compatible with scripts/index_embeddings.py.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import boto3
import sys

# Add project root to path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.services.twelvelabs_video_processing import TwelveLabsVideoProcessingService

MEDIA_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".mp3", ".wav")
EMBEDDING_TO_MODALITY = {
    "visual-text": "text",
    "visual-image": "image",
    "audio": "audio",
}


def discover_media_keys(s3_client, bucket: str, prefix: str, max_items: int) -> List[str]:
    """List media object keys in S3 under prefix, up to max_items."""
    keys: List[str] = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if not key.lower().endswith(MEDIA_EXTENSIONS):
                continue
            keys.append(key)
            if 0 < max_items <= len(keys):
                return keys
    return keys


def extract_vector(segment: Dict[str, Any]) -> List[float]:
    """Extract embedding vector from a Marengo segment."""
    for field in ("embedding", "values", "vector"):
        if field in segment and isinstance(segment[field], list):
            return segment[field]
    raise ValueError("No embedding vector field found in segment")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate real Marengo embeddings via Bedrock async inference",
    )
    parser.add_argument("--input-bucket", required=True, help="S3 bucket with media files")
    parser.add_argument("--input-prefix", default="", help="S3 prefix to scan for media")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock & S3")
    parser.add_argument(
        "--embedding-types",
        nargs="+",
        default=["visual-text", "visual-image", "audio"],
        choices=["visual-text", "visual-image", "audio"],
        help="Marengo embedding types to request",
    )
    parser.add_argument("--max-videos", type=int, default=100, help="Max media files to process")
    parser.add_argument("--timeout-sec", type=int, default=900, help="Per-video timeout in seconds")
    parser.add_argument("--output-dir", default="embeddings/marengo", help="Local output directory")
    parser.add_argument("--dataset-name", default="marengo-batch", help="Dataset name in output")
    parser.add_argument(
        "--output-bucket",
        help="Optional S3 bucket for Bedrock outputs (defaults to service logic)",
    )
    parser.add_argument(
        "--output-prefix",
        default="video-processing-results/",
        help="Prefix within output-bucket for Bedrock outputs",
    )
    args = parser.parse_args()

    s3_client = boto3.client("s3", region_name=args.region)
    media_keys = discover_media_keys(s3_client, args.input_bucket, args.input_prefix, args.max_videos)
    if not media_keys:
        print("No media files found in S3; nothing to process.")
        return 1

    print(f"Discovered {len(media_keys)} media files to process from s3://{args.input_bucket}/{args.input_prefix}")

    service = TwelveLabsVideoProcessingService(region=args.region)

    # Accumulate flat embeddings per modality (text/image/audio)
    flat_by_modality: Dict[str, List[Dict[str, Any]]] = {}
    per_video_stats: Dict[str, Dict[str, Any]] = {}
    failed_videos: List[Dict[str, str]] = []
    zero_embedding_videos: List[str] = []

    for emb_type in args.embedding_types:
        modality = EMBEDDING_TO_MODALITY.get(emb_type, emb_type)
        flat_by_modality.setdefault(modality, [])

    for idx, key in enumerate(media_keys, start=1):
        video_id = Path(key).stem
        video_filename = Path(key).name
        s3_uri = f"s3://{args.input_bucket}/{key}"
        print(f"\n[{idx}/{len(media_keys)}] Processing {s3_uri}")

        # Initialize per-video stats entry
        video_stats = per_video_stats.setdefault(
            video_id,
            {"filename": video_filename, "modality_counts": {}},
        )

        if args.output_bucket:
            out_prefix = args.output_prefix.rstrip("/")
            output_s3_uri = f"s3://{args.output_bucket}/{out_prefix}/{video_id}/"
        else:
            output_s3_uri = None

        total_embeddings_for_video = 0

        try:
            embeddings_by_type = service.process_video_with_multiple_embeddings(
                video_s3_uri=s3_uri,
                output_s3_uri=output_s3_uri,
                embedding_options=args.embedding_types,
                timeout_sec=args.timeout_sec,
            )
        except Exception as e:
            err_msg = str(e)
            print(f"✗ Failed to process {s3_uri}: {err_msg}")
            failed_videos.append({"video_id": video_id, "s3_uri": s3_uri, "error": err_msg})
            continue

        for emb_type, segments in embeddings_by_type.items():
            if not segments:
                print(f"  No segments produced for {video_id} ({emb_type})")
                continue
            modality = EMBEDDING_TO_MODALITY.get(emb_type, emb_type)
            target_list = flat_by_modality.setdefault(modality, [])

            for seg_idx, seg in enumerate(segments):
                try:
                    values = extract_vector(seg)
                except Exception as e:
                    print(f"  Skipping segment {seg_idx} for {video_id} ({emb_type}): {e}")
                    continue

                record = {
                    "id": f"{video_id}_{modality}_{seg_idx:04d}",
                    "video_id": video_id,
                    "modality": modality,
                    "values": values,
                    "dimension": len(values),
                    "metadata": {
                        "source_s3_uri": s3_uri,
                        "source_filename": video_filename,
                        "embedding_option": emb_type,
                        "segment_index": seg_idx,
                    },
                }
                # Preserve timing metadata if present
                for field in ("startSec", "endSec"):
                    if field in seg:
                        record["metadata"][field] = seg[field]
                target_list.append(record)

                # Update per-video statistics
                modality_counts = video_stats.setdefault("modality_counts", {})
                modality_counts[modality] = modality_counts.get(modality, 0) + 1
                total_embeddings_for_video += 1


        if total_embeddings_for_video == 0:
            print(f"  No embeddings produced for {s3_uri} (all embedding types empty)")
            zero_embedding_videos.append(video_id)

    # Print per-video summary
    if per_video_stats:
        print("\nEmbedding summary by video:")
        for vid, stats in per_video_stats.items():
            filename = stats.get("filename", vid)
            modality_counts = stats.get("modality_counts", {})
            if modality_counts:
                counts_str = ", ".join(
                    f"{modality}: {count}" for modality, count in sorted(modality_counts.items())
                )
            else:
                counts_str = "no embeddings"
            print(f"  {filename} ({vid}): {counts_str}")

    if failed_videos:
        print("\nVideos that failed processing:")
        for item in failed_videos:
            print(f"  {item['s3_uri']}: {item['error']}")

    if zero_embedding_videos:
        print("\nVideos with zero embeddings (no segments produced):")
        for vid in zero_embedding_videos:
            stats = per_video_stats.get(vid, {})
            filename = stats.get("filename", vid)
            print(f"  {filename} ({vid})")

    # Write per-modality JSON files compatible with index_embeddings.py
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.utcnow().isoformat()

    for modality, records in flat_by_modality.items():
        if not records:
            continue
        dim = len(records[0]["values"])
        data = {
            "dataset": args.dataset_name,
            "modality": modality,
            "embedding_count": len(records),
            "embedding_dimension": dim,
            "generated_at": generated_at,
            "embeddings": records,
        }
        out_path = output_dir / f"{args.dataset_name}-{modality}.json"
        with out_path.open("w") as f:
            json.dump(data, f, indent=2)
        print(f"✓ Saved {len(records)} {modality} embeddings to {out_path}")

    print("\nDone.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())

