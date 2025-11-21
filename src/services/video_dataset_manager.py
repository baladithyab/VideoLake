"""
Video Dataset Manager

Manages large-scale video datasets from multiple sources for stress testing:
- HuggingFace datasets with streaming support
- Creative Commons bulk sources (Pexels, Pixabay)
- Official datasets (MSR-VTT, WebVid, ActivityNet)

Supports progressive download and S3 upload with checkpointing for resumability.
"""

import json
import time
import hashlib
from typing import Dict, List, Any, Optional, Iterator, Literal
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime, timezone

from src.utils.logging_config import get_logger
from src.exceptions import ValidationError, ProcessingError

logger = get_logger(__name__)


DatasetSource = Literal["huggingface", "pexels", "pixabay", "direct_url", "local_archive"]


@dataclass
class VideoDatasetConfig:
    """Configuration for video dataset."""
    name: str
    source: DatasetSource

    # HuggingFace configuration
    hf_dataset_id: Optional[str] = None
    hf_split: str = "train"
    hf_streaming: bool = True

    # Direct URL configuration
    video_urls: Optional[List[str]] = None

    # Local archive configuration
    archive_path: Optional[str] = None

    # Processing configuration
    max_videos: Optional[int] = None  # Limit for testing
    video_extensions: Optional[List[str]] = None
    min_duration_sec: float = 2.0
    max_duration_sec: float = 3600.0

    # S3 upload configuration
    s3_bucket: Optional[str] = None
    s3_prefix: str = "datasets/"
    enable_checkpointing: bool = True
    checkpoint_interval: int = 10  # Save progress every N videos

    def __post_init__(self):
        if self.video_extensions is None:
            self.video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']


@dataclass
class VideoMetadata:
    """Metadata for a single video in dataset."""
    video_id: str
    source_url: Optional[str]
    s3_uri: Optional[str]

    # Video properties
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None

    # Content metadata
    caption: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None

    # Processing status
    downloaded: bool = False
    uploaded_to_s3: bool = False
    embeddings_generated: bool = False

    # Timestamps
    added_at: Optional[str] = None
    processed_at: Optional[str] = None


@dataclass
class DatasetProgress:
    """Progress tracking for dataset processing."""
    dataset_name: str
    total_videos: int
    processed_videos: int
    failed_videos: int
    skipped_videos: int

    # S3 upload progress
    uploaded_to_s3: int = 0
    upload_failures: int = 0

    # Processing timestamps
    started_at: Optional[str] = None
    last_checkpoint_at: Optional[str] = None

    # Cost estimation
    total_size_gb: float = 0.0
    estimated_cost_usd: float = 0.0

    @property
    def progress_percentage(self) -> float:
        """Get progress as percentage."""
        return (self.processed_videos / self.total_videos * 100) if self.total_videos > 0 else 0.0

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        total_attempted = self.processed_videos + self.failed_videos
        return (self.processed_videos / total_attempted * 100) if total_attempted > 0 else 0.0


class VideoDatasetManager:
    """
    Manages video datasets for stress testing and large-scale demonstrations.

    Supports:
    - HuggingFace datasets with streaming
    - Bulk Creative Commons sources
    - Progressive download and S3 upload
    - Checkpointing for resumability
    - Metadata extraction and tracking

    Example:
        # Load MSR-VTT dataset from HuggingFace
        config = VideoDatasetConfig(
            name="msr-vtt-100",
            source="huggingface",
            hf_dataset_id="AlexZigma/msr-vtt",
            max_videos=100,
            s3_bucket="my-video-bucket"
        )

        manager = VideoDatasetManager(config)

        # Stream and upload progressively
        for video_metadata in manager.stream_and_upload():
            print(f"Uploaded: {video_metadata.video_id} to {video_metadata.s3_uri}")
    """

    # Pre-configured popular datasets
    DATASET_CATALOG = {
        "msr-vtt": VideoDatasetConfig(
            name="msr-vtt",
            source="huggingface",
            hf_dataset_id="AlexZigma/msr-vtt",
            hf_split="train",
            hf_streaming=True,
            max_videos=None  # 10,000 videos
        ),
        "webvid-10m": VideoDatasetConfig(
            name="webvid-10m",
            source="huggingface",
            hf_dataset_id="TempoFunk/webvid-10M",
            hf_streaming=True,
            max_videos=None  # 10.7M videos
        ),
        "youcook2": VideoDatasetConfig(
            name="youcook2",
            source="huggingface",
            hf_dataset_id="Awiny/YouCook2",
            hf_streaming=True,
            max_videos=None  # 2,000 videos
        ),
        "activitynet": VideoDatasetConfig(
            name="activitynet",
            source="huggingface",
            hf_dataset_id="sayakpaul/activitynet",
            hf_streaming=True,
            max_videos=None  # ~20,000 videos
        ),
        "pexels-100": VideoDatasetConfig(
            name="pexels-100",
            source="pexels",
            max_videos=100,
            video_urls=[]  # Populated via Pexels API
        ),
        "blender-demos": VideoDatasetConfig(
            name="blender-demos",
            source="direct_url",
            video_urls=[
                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4",
                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
                "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4"
            ],
            max_videos=4
        )
    }

    def __init__(self, config: VideoDatasetConfig):
        """
        Initialize video dataset manager.

        Args:
            config: Dataset configuration
        """
        self.config = config
        self.logger = get_logger(__name__)

        # Progress tracking
        self.progress = DatasetProgress(
            dataset_name=config.name,
            total_videos=0,
            processed_videos=0,
            failed_videos=0,
            skipped_videos=0,
            started_at=datetime.now(timezone.utc).isoformat()
        )

        # Checkpoint file
        self.checkpoint_file = Path(f".checkpoints/{config.name}_progress.json")
        self.checkpoint_file.parent.mkdir(exist_ok=True)

        # Load existing checkpoint if available
        self._load_checkpoint()

        logger.info(f"Initialized dataset manager: {config.name} from {config.source}")

    def stream_and_upload(self) -> Iterator[VideoMetadata]:
        """
        Stream videos from source and upload to S3 progressively.

        Yields:
            VideoMetadata for each processed video
        """
        if self.config.source == "huggingface":
            yield from self._stream_huggingface_dataset()

        elif self.config.source == "direct_url":
            yield from self._stream_direct_urls()

        elif self.config.source == "pexels":
            yield from self._stream_pexels_videos()

        else:
            raise ValidationError(f"Unsupported dataset source: {self.config.source}")

    def _stream_huggingface_dataset(self) -> Iterator[VideoMetadata]:
        """
        Stream dataset from HuggingFace with progressive S3 upload.

        Uses HuggingFace datasets library with streaming mode to avoid
        downloading entire dataset at once.
        """
        try:
            from datasets import load_dataset

            logger.info(
                f"Streaming HuggingFace dataset: {self.config.hf_dataset_id}, "
                f"split={self.config.hf_split}, streaming={self.config.hf_streaming}"
            )

            # Load dataset in streaming mode
            if not self.config.hf_dataset_id:
                raise ValidationError("HuggingFace dataset ID required")

            dataset = load_dataset(
                self.config.hf_dataset_id,
                split=self.config.hf_split,
                streaming=self.config.hf_streaming,
                # trust_remote_code=True  # Deprecated  # Some datasets require this
            )

            # Process videos
            count = 0
            for item in dataset:
                # Check if we've reached max_videos limit
                if self.config.max_videos and count >= self.config.max_videos:
                    logger.info(f"Reached max_videos limit: {self.config.max_videos}")
                    break

                # Extract video metadata from dataset item
                if not isinstance(item, dict):
                    logger.warning(f"Skipping invalid item format: {type(item)}")
                    continue
                    
                video_metadata = self._extract_hf_video_metadata(item, count)

                # Download and upload to S3
                if self.config.s3_bucket:
                    video_metadata = self._download_and_upload_video(video_metadata)

                # Update progress
                self.progress.processed_videos += 1
                count += 1

                # Checkpoint periodically
                if count % self.config.checkpoint_interval == 0:
                    self._save_checkpoint()
                    logger.info(f"Progress: {count} videos processed")

                yield video_metadata

            # Final checkpoint
            self._save_checkpoint()
            logger.info(
                f"HuggingFace dataset streaming complete: {count} videos processed"
            )

        except ImportError:
            raise ProcessingError(
                "HuggingFace datasets library not installed. "
                "Run: pip install datasets"
            )
        except Exception as e:
            logger.error(f"HuggingFace streaming failed: {str(e)}")
            raise ProcessingError(f"Dataset streaming failed: {str(e)}")

    def _stream_direct_urls(self) -> Iterator[VideoMetadata]:
        """Stream videos from direct URLs."""
        if not self.config.video_urls:
            raise ValidationError("No video URLs configured")

        for idx, url in enumerate(self.config.video_urls):
            video_id = hashlib.md5(url.encode()).hexdigest()[:12]

            metadata = VideoMetadata(
                video_id=video_id,
                source_url=url,
                s3_uri=None,
                added_at=datetime.now(timezone.utc).isoformat()
            )

            # Download and upload to S3
            if self.config.s3_bucket:
                metadata = self._download_and_upload_video(metadata)

            self.progress.processed_videos += 1

            yield metadata

    def _stream_pexels_videos(self) -> Iterator[VideoMetadata]:
        """
        Stream videos from Pexels API.

        Note: Requires PEXELS_API_KEY environment variable.
        """
        import os
        import requests

        api_key = os.getenv('PEXELS_API_KEY')
        if not api_key:
            raise ValidationError("PEXELS_API_KEY environment variable required")

        headers = {'Authorization': api_key}
        base_url = "https://api.pexels.com/videos/popular"

        page = 1
        count = 0

        while True:
            # Check limit
            if self.config.max_videos and count >= self.config.max_videos:
                break

            # Fetch page
            response = requests.get(
                base_url,
                headers=headers,
                params={'per_page': 80, 'page': page}
            )

            if response.status_code != 200:
                logger.error(f"Pexels API error: {response.status_code}")
                break

            data = response.json()
            videos = data.get('videos', [])

            if not videos:
                break

            # Process videos
            for video in videos:
                if self.config.max_videos and count >= self.config.max_videos:
                    break

                # Get highest quality file
                video_files = video.get('video_files', [])
                if not video_files:
                    continue

                # Find best quality MP4
                mp4_files = [f for f in video_files if f.get('file_type') == 'video/mp4']
                if not mp4_files:
                    continue

                best_file = max(mp4_files, key=lambda x: x.get('width', 0))

                metadata = VideoMetadata(
                    video_id=str(video['id']),
                    source_url=best_file['link'],
                    s3_uri=None,
                    duration_sec=video.get('duration'),
                    width=best_file.get('width'),
                    height=best_file.get('height'),
                    tags=[],
                    added_at=datetime.now(timezone.utc).isoformat()
                )

                # Download and upload
                if self.config.s3_bucket:
                    metadata = self._download_and_upload_video(metadata)

                count += 1
                self.progress.processed_videos += 1

                if count % self.config.checkpoint_interval == 0:
                    self._save_checkpoint()

                yield metadata

            page += 1

    def _extract_hf_video_metadata(self, item: Dict[str, Any], index: int) -> VideoMetadata:
        """Extract video metadata from HuggingFace dataset item."""
        # Different datasets have different structures
        # Try common field names

        video_id = item.get('video_id') or item.get('id') or f"video_{index}"

        # Try to get video URL
        video_url = (
            item.get('video_url') or
            item.get('url') or
            item.get('video') or
            item.get('contentUrl')
        )

        # Get caption/description
        caption = (
            item.get('caption') or
            item.get('sentence') or
            item.get('description') or
            item.get('name')
        )

        # Get category
        category = item.get('category') or item.get('label')

        metadata = VideoMetadata(
            video_id=str(video_id),
            source_url=video_url,
            s3_uri=None,
            caption=caption,
            category=category,
            tags=item.get('tags', []),
            added_at=datetime.now(timezone.utc).isoformat()
        )

        return metadata

    def _download_and_upload_video(self, metadata: VideoMetadata) -> VideoMetadata:
        """
        Download video from source URL and upload to S3.

        Args:
            metadata: Video metadata with source_url

        Returns:
            Updated metadata with s3_uri
        """
        if not metadata.source_url:
            logger.warning(f"No source URL for video {metadata.video_id}")
            self.progress.skipped_videos += 1
            return metadata

        try:
            import requests
            import boto3
            from urllib.parse import urlparse

            # Download video
            logger.debug(f"Downloading video {metadata.video_id} from {metadata.source_url}")

            response = requests.get(metadata.source_url, stream=True, timeout=60)
            if response.status_code != 200:
                logger.error(f"Failed to download {metadata.video_id}: HTTP {response.status_code}")
                self.progress.failed_videos += 1
                return metadata

            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'mp4' in content_type:
                ext = '.mp4'
            elif 'webm' in content_type:
                ext = '.webm'
            else:
                ext = '.mp4'  # Default

            # Upload directly to S3 (streaming, no local storage)
            s3_client = boto3.client('s3')
            s3_key = f"{self.config.s3_prefix}{self.config.name}/{metadata.video_id}{ext}"

            s3_client.upload_fileobj(
                response.raw,
                self.config.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'source': metadata.source_url or 'unknown',
                        'video-id': metadata.video_id,
                        'dataset': self.config.name
                    },
                    'Tagging': 'dataset=video'
                }
            )

            # Update metadata
            metadata.s3_uri = f"s3://{self.config.s3_bucket}/{s3_key}"
            metadata.downloaded = True
            metadata.uploaded_to_s3 = True

            self.progress.uploaded_to_s3 += 1

            logger.info(f"Uploaded {metadata.video_id} to {metadata.s3_uri}")

            return metadata

        except Exception as e:
            logger.error(f"Failed to download/upload {metadata.video_id}: {str(e)}")
            self.progress.failed_videos += 1
            self.progress.upload_failures += 1
            return metadata

    def _save_checkpoint(self) -> None:
        """Save progress checkpoint."""
        if not self.config.enable_checkpointing:
            return

        checkpoint_data = {
            'config': asdict(self.config),
            'progress': asdict(self.progress),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        self.checkpoint_file.write_text(json.dumps(checkpoint_data, indent=2))
        self.progress.last_checkpoint_at = datetime.now(timezone.utc).isoformat()

        logger.debug(f"Checkpoint saved: {self.progress.processed_videos} videos")

    def _load_checkpoint(self) -> None:
        """Load progress checkpoint if exists."""
        if not self.checkpoint_file.exists():
            return

        try:
            checkpoint_data = json.loads(self.checkpoint_file.read_text())

            # Restore progress
            progress_dict = checkpoint_data.get('progress', {})
            for key, value in progress_dict.items():
                if hasattr(self.progress, key):
                    setattr(self.progress, key, value)

            logger.info(
                f"Resumed from checkpoint: {self.progress.processed_videos} videos already processed"
            )

        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {str(e)}")

    def get_progress(self) -> DatasetProgress:
        """Get current progress."""
        return self.progress

    @classmethod
    def list_available_datasets(cls) -> List[Dict[str, Any]]:
        """List all pre-configured datasets."""
        return [
            {
                'name': config.name,
                'source': config.source,
                'hf_dataset_id': config.hf_dataset_id,
                'streaming_supported': config.hf_streaming,
                'estimated_videos': {
                    'msr-vtt': 10000,
                    'webvid-10m': 10700000,
                    'youcook2': 2000,
                    'activitynet': 20000,
                    'pexels-100': 100,
                    'blender-demos': 4
                }.get(config.name, 'unknown')
            }
            for config in cls.DATASET_CATALOG.values()
        ]

    @classmethod
    def get_recommended_dataset(cls, use_case: str = "quick_test") -> VideoDatasetConfig:
        """
        Get recommended dataset based on use case.

        Args:
            use_case: "quick_test", "stress_test", "large_scale"

        Returns:
            VideoDatasetConfig for recommended dataset
        """
        recommendations = {
            "quick_test": cls.DATASET_CATALOG["blender-demos"],  # 4 videos
            "small_test": VideoDatasetConfig(
                name="msr-vtt-100",
                source="huggingface",
                hf_dataset_id="AlexZigma/msr-vtt",
                max_videos=100  # 100 videos for testing
            ),
            "stress_test": VideoDatasetConfig(
                name="msr-vtt-1000",
                source="huggingface",
                hf_dataset_id="AlexZigma/msr-vtt",
                max_videos=1000  # 1000 videos
            ),
            "large_scale": cls.DATASET_CATALOG["webvid-10m"]  # 10.7M videos
        }

        return recommendations.get(use_case, recommendations["quick_test"])
