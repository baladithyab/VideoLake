"""
Dataset Downloader for Multi-Modal Benchmarking.

Downloads and prepares recommended datasets for large-scale ingestion:
- Text: MS MARCO, Wikipedia, Common Crawl News, Natural Questions
- Image: COCO, LAION, OpenImages, ImageNet
- Audio: LibriSpeech, Common Voice, VoxCeleb, AudioSet
- Video: MSR-VTT, ActivityNet, Kinetics, YouTube-8M

All datasets are staged to S3 for parallel processing.
"""

import asyncio
import gzip
import json
import os
import tarfile
import zipfile
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
import tempfile

import boto3
from botocore.exceptions import ClientError

from src.utils.logging_config import get_logger
from src.utils.aws_clients import aws_client_factory
from src.exceptions import ProcessingError

logger = get_logger(__name__)


class DatasetType(Enum):
    """Supported dataset types."""
    # Text
    MS_MARCO = "ms_marco"
    WIKIPEDIA = "wikipedia"
    COMMON_CRAWL_NEWS = "common_crawl_news"
    NATURAL_QUESTIONS = "natural_questions"

    # Image
    COCO = "coco"
    LAION = "laion"
    OPEN_IMAGES = "open_images"
    IMAGENET = "imagenet"

    # Audio
    LIBRISPEECH = "librispeech"
    COMMON_VOICE = "common_voice"
    VOXCELEB = "voxceleb"
    AUDIOSET = "audioset"

    # Video
    MSR_VTT = "msr_vtt"
    ACTIVITYNET = "activitynet"
    KINETICS = "kinetics"
    YOUTUBE_8M = "youtube_8m"


@dataclass
class DatasetConfig:
    """Configuration for dataset download."""
    dataset_type: DatasetType
    max_items: int = 10000  # Maximum items to download
    s3_bucket: str = "s3vector-datasets"
    s3_prefix: str = "raw"
    local_cache_dir: Optional[str] = None  # Local cache for downloads


@dataclass
class DatasetItem:
    """A single item from a dataset."""
    item_id: str
    content: Any  # Text, S3 URI, bytes, etc.
    metadata: Dict[str, Any]
    s3_uri: Optional[str] = None


class DatasetDownloader:
    """
    Downloads and stages datasets for large-scale ingestion.

    Handles:
    - HTTP/S3 downloads
    - Decompression (gzip, tar, zip)
    - S3 staging for parallel processing
    - Progress tracking
    - Resume capability

    Example:
        config = DatasetConfig(
            dataset_type=DatasetType.MS_MARCO,
            max_items=100000,
            s3_bucket="my-datasets",
            s3_prefix="benchmarking/ms-marco"
        )

        downloader = DatasetDownloader(config)

        # Download and stage to S3
        items_staged = await downloader.download_and_stage()
        print(f"Staged {items_staged} items to S3")

        # Stream items for processing
        async for item in downloader.stream_items():
            print(f"Processing {item.item_id}")
    """

    def __init__(self, config: DatasetConfig):
        """
        Initialize dataset downloader.

        Args:
            config: Dataset download configuration
        """
        self.config = config
        self.s3_client = aws_client_factory.get_s3_client()

        # Setup local cache
        if config.local_cache_dir:
            self.cache_dir = Path(config.local_cache_dir)
        else:
            self.cache_dir = Path(tempfile.gettempdir()) / "s3vector-datasets"

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DatasetDownloader initialized: {config.dataset_type.value}, "
            f"max_items={config.max_items}, cache={self.cache_dir}"
        )

    async def download_and_stage(self) -> int:
        """
        Download dataset and stage to S3.

        Returns:
            Number of items staged
        """
        dataset_type = self.config.dataset_type

        logger.info(f"Starting download: {dataset_type.value}")

        # Route to specific downloader
        if dataset_type == DatasetType.MS_MARCO:
            return await self._download_ms_marco()
        elif dataset_type == DatasetType.WIKIPEDIA:
            return await self._download_wikipedia()
        elif dataset_type == DatasetType.COCO:
            return await self._download_coco()
        elif dataset_type == DatasetType.LIBRISPEECH:
            return await self._download_librispeech()
        elif dataset_type == DatasetType.MSR_VTT:
            return await self._download_msr_vtt()
        else:
            raise NotImplementedError(
                f"Downloader not implemented for {dataset_type.value}. "
                f"Please add implementation in dataset_downloader.py"
            )

    async def stream_items(self) -> AsyncIterator[DatasetItem]:
        """
        Stream dataset items from S3.

        Yields items one at a time for processing.

        Yields:
            DatasetItem objects
        """
        prefix = f"{self.config.s3_prefix}/{self.config.dataset_type.value}/"

        try:
            # List objects in S3
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=self.config.s3_bucket,
                Prefix=prefix
            )

            item_count = 0

            for page in page_iterator:
                for obj in page.get('Contents', []):
                    if item_count >= self.config.max_items:
                        return

                    s3_key = obj['Key']

                    # Generate item from S3 object
                    yield DatasetItem(
                        item_id=Path(s3_key).stem,
                        content=f"s3://{self.config.s3_bucket}/{s3_key}",
                        metadata={
                            'dataset': self.config.dataset_type.value,
                            's3_key': s3_key,
                            'size_bytes': obj['Size']
                        },
                        s3_uri=f"s3://{self.config.s3_bucket}/{s3_key}"
                    )

                    item_count += 1

        except ClientError as e:
            logger.error(f"Failed to stream items from S3: {e}")
            raise ProcessingError(f"S3 streaming failed: {e}")

    # ==================== Text Dataset Downloaders ====================

    async def _download_ms_marco(self) -> int:
        """
        Download MS MARCO dataset.

        Downloads document ranking dataset from Microsoft.
        Reference: https://microsoft.github.io/msmarco/
        """
        logger.info("Downloading MS MARCO dataset...")

        # MS MARCO documents URL
        docs_url = "https://msmarco.blob.core.windows.net/msmarcoranking/msmarco-docs.tsv.gz"

        # Download documents
        docs_file = self.cache_dir / "msmarco-docs.tsv.gz"
        if not docs_file.exists():
            await self._download_file_http(docs_url, docs_file)

        # Parse and stage documents
        items_staged = 0
        with gzip.open(docs_file, 'rt', encoding='utf-8') as f:
            for line in f:
                if items_staged >= self.config.max_items:
                    break

                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue

                doc_id, url, title, body = parts[0], parts[1], parts[2], parts[3]

                # Combine title and body
                content = f"{title}\n\n{body}"

                # Stage to S3
                s3_key = f"{self.config.s3_prefix}/ms_marco/docs/{doc_id}.txt"
                await self._upload_text_to_s3(
                    content=content,
                    s3_key=s3_key,
                    metadata={'url': url, 'title': title}
                )

                items_staged += 1

                if items_staged % 1000 == 0:
                    logger.info(f"Staged {items_staged} MS MARCO documents")

        logger.info(f"MS MARCO download complete: {items_staged} documents")
        return items_staged

    async def _download_wikipedia(self) -> int:
        """
        Download Wikipedia dataset.

        Uses Hugging Face datasets library for streaming.
        """
        logger.info("Downloading Wikipedia dataset...")

        try:
            from datasets import load_dataset

            # Load Wikipedia dataset (streaming mode)
            dataset = load_dataset(
                "wikipedia",
                "20220301.en",
                split="train",
                streaming=True
            )

            items_staged = 0

            for item in dataset:
                if items_staged >= self.config.max_items:
                    break

                doc_id = item.get('id', f"wiki_{items_staged}")
                title = item.get('title', '')
                text = item.get('text', '')

                # Combine title and text
                content = f"# {title}\n\n{text}"

                # Stage to S3
                s3_key = f"{self.config.s3_prefix}/wikipedia/articles/{doc_id}.txt"
                await self._upload_text_to_s3(
                    content=content,
                    s3_key=s3_key,
                    metadata={'title': title}
                )

                items_staged += 1

                if items_staged % 1000 == 0:
                    logger.info(f"Staged {items_staged} Wikipedia articles")

            logger.info(f"Wikipedia download complete: {items_staged} articles")
            return items_staged

        except ImportError:
            logger.error("datasets library not installed. Run: pip install datasets")
            raise ProcessingError("Missing dependency: datasets")

    # ==================== Image Dataset Downloaders ====================

    async def _download_coco(self) -> int:
        """
        Download COCO dataset.

        Downloads COCO 2017 validation set (5K images).
        Reference: https://cocodataset.org/
        """
        logger.info("Downloading COCO dataset...")

        # COCO 2017 validation images
        images_url = "http://images.cocodataset.org/zips/val2017.zip"

        # Download images
        images_zip = self.cache_dir / "coco_val2017.zip"
        if not images_zip.exists():
            await self._download_file_http(images_url, images_zip)

        # Extract and stage images
        items_staged = 0

        with zipfile.ZipFile(images_zip, 'r') as zip_ref:
            image_files = [f for f in zip_ref.namelist() if f.endswith('.jpg')]

            for image_file in image_files[:self.config.max_items]:
                # Extract image
                image_data = zip_ref.read(image_file)

                # Get image ID
                image_id = Path(image_file).stem

                # Upload to S3
                s3_key = f"{self.config.s3_prefix}/coco/images/{image_id}.jpg"
                await self._upload_bytes_to_s3(
                    data=image_data,
                    s3_key=s3_key,
                    content_type="image/jpeg",
                    metadata={'dataset': 'coco', 'split': 'val2017'}
                )

                items_staged += 1

                if items_staged % 100 == 0:
                    logger.info(f"Staged {items_staged} COCO images")

        logger.info(f"COCO download complete: {items_staged} images")
        return items_staged

    # ==================== Audio Dataset Downloaders ====================

    async def _download_librispeech(self) -> int:
        """
        Download LibriSpeech dataset.

        Downloads LibriSpeech test-clean subset (2.6K utterances).
        Reference: https://www.openslr.org/12
        """
        logger.info("Downloading LibriSpeech dataset...")

        # LibriSpeech test-clean subset
        test_url = "https://www.openslr.org/resources/12/test-clean.tar.gz"

        # Download tar file
        tar_file = self.cache_dir / "librispeech-test-clean.tar.gz"
        if not tar_file.exists():
            await self._download_file_http(test_url, tar_file)

        # Extract and stage audio files
        items_staged = 0

        with tarfile.open(tar_file, 'r:gz') as tar:
            for member in tar.getmembers():
                if items_staged >= self.config.max_items:
                    break

                if member.name.endswith('.flac'):
                    # Extract audio file
                    audio_file = tar.extractfile(member)
                    if not audio_file:
                        continue

                    audio_data = audio_file.read()

                    # Get utterance ID
                    utterance_id = Path(member.name).stem

                    # Upload to S3
                    s3_key = f"{self.config.s3_prefix}/librispeech/audio/{utterance_id}.flac"
                    await self._upload_bytes_to_s3(
                        data=audio_data,
                        s3_key=s3_key,
                        content_type="audio/flac",
                        metadata={'dataset': 'librispeech', 'split': 'test-clean'}
                    )

                    items_staged += 1

                    if items_staged % 100 == 0:
                        logger.info(f"Staged {items_staged} LibriSpeech audio files")

        logger.info(f"LibriSpeech download complete: {items_staged} audio files")
        return items_staged

    # ==================== Video Dataset Downloaders ====================

    async def _download_msr_vtt(self) -> int:
        """
        Download MSR-VTT dataset.

        Note: MSR-VTT requires manual download. This implementation
        assumes videos are already downloaded locally.
        """
        logger.info("MSR-VTT requires manual download.")
        logger.info("Visit: http://ms-multimedia-challenge.com/2017/dataset")

        # Check if videos exist locally
        msr_vtt_dir = self.cache_dir / "msr-vtt"
        if not msr_vtt_dir.exists():
            raise ProcessingError(
                f"MSR-VTT videos not found at {msr_vtt_dir}. "
                f"Please download manually."
            )

        # Stage local videos to S3
        items_staged = 0
        video_files = list(msr_vtt_dir.glob("*.mp4"))

        for video_file in video_files[:self.config.max_items]:
            with open(video_file, 'rb') as f:
                video_data = f.read()

            video_id = video_file.stem

            s3_key = f"{self.config.s3_prefix}/msr_vtt/videos/{video_id}.mp4"
            await self._upload_bytes_to_s3(
                data=video_data,
                s3_key=s3_key,
                content_type="video/mp4",
                metadata={'dataset': 'msr-vtt', 'split': 'test'}
            )

            items_staged += 1

            if items_staged % 10 == 0:
                logger.info(f"Staged {items_staged} MSR-VTT videos")

        logger.info(f"MSR-VTT staging complete: {items_staged} videos")
        return items_staged

    # ==================== Helper Methods ====================

    async def _download_file_http(self, url: str, dest_path: Path):
        """Download file from URL using Python requests (not shell commands)."""
        logger.info(f"Downloading {url} to {dest_path}")

        try:
            import requests
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Download complete: {dest_path}")

        except Exception as e:
            raise ProcessingError(f"Download failed: {e}")

    async def _upload_text_to_s3(
        self,
        content: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ):
        """Upload text content to S3."""
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                Metadata=metadata or {}
            )
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise ProcessingError(f"S3 upload failed: {e}")

    async def _upload_bytes_to_s3(
        self,
        data: bytes,
        s3_key: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ):
        """Upload binary data to S3."""
        try:
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.config.s3_bucket,
                Key=s3_key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {}
            )
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {e}")
            raise ProcessingError(f"S3 upload failed: {e}")


# Dataset registry for easy access
RECOMMENDED_DATASETS = {
    "text": {
        "ms_marco_10k": DatasetConfig(
            dataset_type=DatasetType.MS_MARCO,
            max_items=10000
        ),
        "ms_marco_100k": DatasetConfig(
            dataset_type=DatasetType.MS_MARCO,
            max_items=100000
        ),
        "wikipedia_10k": DatasetConfig(
            dataset_type=DatasetType.WIKIPEDIA,
            max_items=10000
        ),
    },
    "image": {
        "coco_5k": DatasetConfig(
            dataset_type=DatasetType.COCO,
            max_items=5000
        ),
    },
    "audio": {
        "librispeech_2k": DatasetConfig(
            dataset_type=DatasetType.LIBRISPEECH,
            max_items=2600
        ),
    },
    "video": {
        "msr_vtt_1k": DatasetConfig(
            dataset_type=DatasetType.MSR_VTT,
            max_items=1000
        ),
    }
}


def get_dataset_config(dataset_name: str) -> DatasetConfig:
    """
    Get dataset configuration by name.

    Args:
        dataset_name: Name from RECOMMENDED_DATASETS

    Returns:
        DatasetConfig

    Example:
        config = get_dataset_config("ms_marco_100k")
    """
    for modality, datasets in RECOMMENDED_DATASETS.items():
        if dataset_name in datasets:
            return datasets[dataset_name]

    raise ValueError(
        f"Dataset not found: {dataset_name}. "
        f"Available: {list(RECOMMENDED_DATASETS.keys())}"
    )
