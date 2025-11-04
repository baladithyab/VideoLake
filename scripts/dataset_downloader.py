#!/usr/bin/env python3
"""
Video Dataset Downloader and Processor
Supports HuggingFace datasets and streaming with S3 upload integration
"""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
import logging

import requests
import boto3
from datasets import load_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatasetDownloadConfig:
    """Configuration for dataset downloads"""
    def __init__(self, 
                 dataset_id: str,
                 max_videos: int = 100,
                 s3_bucket: Optional[str] = None,
                 checkpoint_dir: Optional[str] = None,
                 batch_size: int = 10):
        self.dataset_id = dataset_id
        self.max_videos = max_videos
        self.s3_bucket = s3_bucket
        self.checkpoint_dir = checkpoint_dir or ".checkpoints"
        self.batch_size = batch_size


class DatasetProcessor:
    """Process and download videos from HuggingFace datasets"""
    
    def __init__(self, config: DatasetDownloadConfig):
        self.config = config
        self.s3_client = boto3.client('s3') if config.s3_bucket else None
        self.checkpoint_file = Path(config.checkpoint_dir) / f"{config.dataset_id.replace('/', '-')}.json"
        self.checkpoint_file.parent.mkdir(exist_ok=True)
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load processing checkpoint"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'processed_videos': 0, 'failed_videos': 0, 'last_video_id': None}
    
    def save_checkpoint(self, checkpoint: Dict[str, Any]):
        """Save processing checkpoint"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
    
    def download_video(self, url: str, max_size_mb: int = 500) -> Optional[bytes]:
        """Download video with size limit and timeout"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, stream=True, timeout=30, headers=headers)
            response.raise_for_status()
            
            content = b''
            max_bytes = max_size_mb * 1024 * 1024
            
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > max_bytes:
                    logger.warning(f"Video exceeded {max_size_mb}MB limit")
                    return None
            
            return content
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return None
    
    def upload_to_s3(self, data: bytes, key: str) -> bool:
        """Upload video to S3"""
        if not self.s3_client or not self.config.s3_bucket:
            return False
        
        try:
            self.s3_client.put_object(
                Bucket=self.config.s3_bucket,
                Key=key,
                Body=data
            )
            logger.info(f"Uploaded to s3://{self.config.s3_bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {key}: {e}")
            return False
    
    def process_dataset(self):
        """Process dataset with streaming"""
        checkpoint = self.load_checkpoint()
        dataset = load_dataset(self.config.dataset_id, streaming=True, split="train")
        
        logger.info(f"Starting processing of {self.config.dataset_id}")
        logger.info(f"Max videos: {self.config.max_videos}")
        
        for i, example in enumerate(dataset):
            if i >= self.config.max_videos:
                break
            
            # Get video URL
            video_url = None
            for url_field in ['url', 'video_url', 'link']:
                if url_field in example and example[url_field]:
                    video_url = example[url_field]
                    break
            
            if not video_url:
                logger.warning(f"No URL found in video {i}")
                checkpoint['failed_videos'] += 1
                continue
            
            try:
                logger.info(f"[{i}] Processing: {video_url[:80]}")
                
                # Download video
                video_data = self.download_video(video_url)
                if not video_data:
                    checkpoint['failed_videos'] += 1
                    continue
                
                # Upload to S3 if configured
                if self.config.s3_bucket:
                    s3_key = f"datasets/{self.config.dataset_id.replace('/', '-')}/{i:06d}.mp4"
                    success = self.upload_to_s3(video_data, s3_key)
                    if not success:
                        checkpoint['failed_videos'] += 1
                        continue
                
                checkpoint['processed_videos'] = i + 1
                checkpoint['last_video_id'] = example.get('video_id', str(i))
                
                # Save checkpoint every N videos
                if (i + 1) % self.config.batch_size == 0:
                    self.save_checkpoint(checkpoint)
                    logger.info(f"Checkpoint saved: {i + 1} videos processed")
                
            except Exception as e:
                logger.error(f"Error processing video {i}: {e}")
                checkpoint['failed_videos'] += 1
                continue
        
        # Final checkpoint
        self.save_checkpoint(checkpoint)
        logger.info(f"Processing complete: {checkpoint['processed_videos']} succeeded, {checkpoint['failed_videos']} failed")
        return checkpoint


def main():
    parser = argparse.ArgumentParser(description="Download and process video datasets")
    parser.add_argument("--dataset-id", required=True, help="HuggingFace dataset ID")
    parser.add_argument("--max-videos", type=int, default=100, help="Maximum videos to download")
    parser.add_argument("--s3-bucket", help="S3 bucket for uploads")
    parser.add_argument("--checkpoint-dir", default=".checkpoints", help="Checkpoint directory")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for checkpointing")
    
    args = parser.parse_args()
    
    config = DatasetDownloadConfig(
        dataset_id=args.dataset_id,
        max_videos=args.max_videos,
        s3_bucket=args.s3_bucket,
        checkpoint_dir=args.checkpoint_dir,
        batch_size=args.batch_size
    )
    
    processor = DatasetProcessor(config)
    result = processor.process_dataset()
    
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
