"""
MSR-VTT Dataset Downloader.

Downloads MSR-VTT (Microsoft Research Video to Text) dataset for video embedding benchmarking.
"""

import asyncio
import json
from pathlib import Path
from typing import AsyncIterator, Dict, Any, List
import time

from src.ingestion.datasets import register_dataset
from src.ingestion.datasets.base import DatasetDownloader, DownloadConfig, DatasetMetadata
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@register_dataset('msrvtt')
class MSRVTTDownloader(DatasetDownloader):
    """Downloader for MSR-VTT dataset."""

    DATASET_NAME = "msrvtt"
    MODALITY = "video"
    DESCRIPTION = "MSR-VTT - Microsoft Research Video to Text dataset"
    LICENSE = "Research use"
    RECOMMENDED_SIZE = 10000

    # Dataset information
    # Note: MSR-VTT videos are hosted on various platforms and require special handling
    ANNOTATIONS_URL = "https://github.com/ArrowLuo/CLIP4Clip/raw/master/data/MSRVTT/msrvtt_data/MSRVTT_data.json"
    TOTAL_VIDEOS = 10000
    TRAIN_VIDEOS = 6513
    VAL_VIDEOS = 497
    TEST_VIDEOS = 2990

    def __init__(self, config: DownloadConfig):
        """Initialize MSR-VTT downloader."""
        super().__init__(config)
        self.annotations_path = self.output_dir / "MSRVTT_data.json"
        self.videos_dir = self.output_dir / "videos"
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    async def download(self) -> DatasetMetadata:
        """Download MSR-VTT dataset."""
        start_time = time.time()
        logger.info(f"Starting MSR-VTT download to {self.output_dir}")

        # Download annotations first
        success = await self.download_file(self.ANNOTATIONS_URL, self.annotations_path)

        if not success:
            raise RuntimeError("Failed to download MSR-VTT annotations")

        # Load annotations to get video URLs
        with open(self.annotations_path, 'r') as f:
            data = json.load(f)

        # MSR-VTT videos need to be downloaded from YouTube or other sources
        # This is a complex process that requires youtube-dl or similar tools
        logger.warning(
            "MSR-VTT videos must be downloaded separately using youtube-dl or similar tools. "
            "This downloader provides annotations and metadata only."
        )

        # For benchmarking, we'll provide the metadata structure
        # Users need to download videos using: youtube-dl or yt-dlp
        self._generate_download_script(data)

        # Count available metadata
        videos = data.get('videos', [])
        sentences = data.get('sentences', [])

        total_items = len(videos)
        downloaded_items = 0  # Videos not automatically downloaded

        download_time = time.time() - start_time

        metadata = DatasetMetadata(
            dataset_name=self.DATASET_NAME,
            modality=self.MODALITY,
            total_items=total_items,
            downloaded_items=downloaded_items,
            failed_items=0,
            total_size_bytes=self.annotations_path.stat().st_size,
            download_time_seconds=download_time,
            output_directory=self.output_dir
        )

        logger.info(f"MSR-VTT metadata download complete: {total_items} video entries")
        logger.info(f"Use the generated download script to fetch videos: {self.output_dir}/download_videos.sh")

        return metadata

    def _generate_download_script(self, data: Dict[str, Any]):
        """Generate shell script to download MSR-VTT videos."""
        script_path = self.output_dir / "download_videos.sh"

        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# MSR-VTT Video Download Script\n")
            f.write("# Requires yt-dlp: pip install yt-dlp\n\n")
            f.write(f"OUTPUT_DIR=\"{self.videos_dir}\"\n")
            f.write("mkdir -p \"$OUTPUT_DIR\"\n\n")

            videos = data.get('videos', [])
            max_items = self.config.max_items or len(videos)

            for i, video in enumerate(videos[:max_items]):
                video_id = video['video_id']
                youtube_id = video.get('url', '').split('watch?v=')[-1]

                if youtube_id:
                    f.write(f"# Download {video_id}\n")
                    f.write(
                        f"yt-dlp -f 'best[height<=480]' "
                        f"-o \"$OUTPUT_DIR/{video_id}.mp4\" "
                        f"\"https://www.youtube.com/watch?v={youtube_id}\" "
                        f"|| echo \"Failed: {video_id}\"\n\n"
                    )

        script_path.chmod(0o755)
        logger.info(f"Generated download script: {script_path}")

    async def stream_items(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream MSR-VTT video metadata with captions.

        Yields:
            Dict with video_id, video_path, captions, category, split
        """
        if not self.annotations_path.exists():
            raise FileNotFoundError(f"Annotations not found: {self.annotations_path}")

        logger.info(f"Streaming MSR-VTT from {self.output_dir}")

        # Load annotations
        with open(self.annotations_path, 'r') as f:
            data = json.load(f)

        videos = {v['video_id']: v for v in data.get('videos', [])}
        sentences = data.get('sentences', [])

        # Group sentences by video_id
        video_captions = {}
        for sent in sentences:
            video_id = sent['video_id']
            if video_id not in video_captions:
                video_captions[video_id] = []
            video_captions[video_id].append(sent['caption'])

        count = 0
        max_items = self.config.max_items or float('inf')

        for video_id, video_info in videos.items():
            if count >= max_items:
                break

            video_path = self.videos_dir / f"{video_id}.mp4"

            # Check if video exists (may have been downloaded separately)
            video_exists = video_path.exists()

            item = {
                'video_id': video_id,
                'video_path': str(video_path) if video_exists else None,
                'video_exists': video_exists,
                'captions': video_captions.get(video_id, []),
                'category': video_info.get('category', 'unknown'),
                'url': video_info.get('url', ''),
                'start_time': video_info.get('start time', 0),
                'end_time': video_info.get('end time', 0),
                'split': video_info.get('split', 'unknown'),
                'modality': 'video'
            }

            if self.validate_item(item):
                yield item
                count += 1

                if count % 100 == 0:
                    logger.info(f"Streamed {count} video entries")

        logger.info(f"Finished streaming {count} video entries")

    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate MSR-VTT video metadata."""
        # Must have video_id and at least one caption
        if not item.get('video_id'):
            return False

        if not item.get('captions'):
            return False

        # If validating actual video files, check they exist
        # For metadata-only mode, we skip this check
        if self.config.max_items and item.get('video_exists'):
            video_path = Path(item['video_path'])
            if not video_path.exists() or video_path.stat().st_size < 10240:
                return False

        return True

    def get_preprocessing_config(self) -> Dict[str, Any]:
        """Get recommended preprocessing configuration."""
        return {
            'resolution': '480p',
            'fps': 24,
            'format': 'mp4',
            'codec': 'h264',
            'frame_sampling': 'uniform_8_frames',  # Sample 8 frames uniformly
            'description': 'Downsample to 480p, extract 8 uniform frames'
        }

    def get_embedding_strategy(self) -> Dict[str, Any]:
        """Get recommended embedding strategy."""
        return {
            'model': 'amazon.titan-embed-image-v1',
            'model_type': 'bedrock',
            'dimension': 1024,
            'strategy': 'frame_aggregation',
            'frames_per_video': 8,
            'aggregation': 'mean',
            'description': 'Extract 8 frames, embed with Titan, aggregate with mean pooling'
        }

    def get_alternative_sources(self) -> List[Dict[str, Any]]:
        """Get alternative data sources for MSR-VTT."""
        return [
            {
                'name': 'Hugging Face Hub',
                'url': 'https://huggingface.co/datasets/AlexZigma/msr-vtt',
                'description': 'Pre-processed MSR-VTT with videos',
                'method': 'datasets.load_dataset("AlexZigma/msr-vtt")'
            },
            {
                'name': 'Academic Torrents',
                'url': 'http://academictorrents.com/details/2a9c873cdf1a1ed27f57d1fa74ab69ca4c641abb',
                'description': 'Original MSR-VTT video files (torrent)',
                'method': 'Download via torrent client'
            },
            {
                'name': 'Manual Download',
                'url': 'https://www.microsoft.com/en-us/research/publication/msr-vtt-a-large-video-description-dataset-for-bridging-video-and-language/',
                'description': 'Official MSR-VTT page with download links',
                'method': 'Follow instructions on official page'
            }
        ]

    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get MSR-VTT dataset statistics."""
        return {
            'total_videos': self.TOTAL_VIDEOS,
            'train_videos': self.TRAIN_VIDEOS,
            'val_videos': self.VAL_VIDEOS,
            'test_videos': self.TEST_VIDEOS,
            'captions_per_video': 20,
            'total_captions': self.TOTAL_VIDEOS * 20,
            'video_categories': 20,
            'avg_video_duration_seconds': 15,
            'resolution': '240p-480p',
            'total_estimated_size_gb': 30
        }
