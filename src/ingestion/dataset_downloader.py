"""
Dataset Downloader for Recommended Large-Scale Datasets.

Provides downloaders for MS MARCO, COCO, LibriSpeech, and MSR-VTT datasets
with S3 staging, progress tracking, and metadata extraction.
"""

import asyncio
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import boto3
import requests

from src.services.embedding_provider import ModalityType
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatasetType(str, Enum):
    """Supported dataset types."""
    MS_MARCO = "ms_marco"
    COCO = "coco"
    LIBRISPEECH = "librispeech"
    MSR_VTT = "msr_vtt"


@dataclass
class DatasetInfo:
    """Information about a dataset."""
    name: str
    dataset_type: DatasetType
    modality: ModalityType
    size_gb: float
    num_items: int
    download_url: str
    description: str
    license: str
    homepage: str | None = None
    citation: str | None = None


@dataclass
class DownloadProgress:
    """Progress information for dataset download."""
    dataset_name: str
    total_bytes: int
    downloaded_bytes: int
    progress_percentage: float
    download_speed_mbps: float
    eta_seconds: float
    started_at: datetime
    status: str  # downloading, extracting, staging, completed, failed


class DatasetRegistry:
    """Registry of supported datasets with metadata."""

    DATASETS: dict[DatasetType, DatasetInfo] = {
        DatasetType.MS_MARCO: DatasetInfo(
            name="MS MARCO Passages",
            dataset_type=DatasetType.MS_MARCO,
            modality=ModalityType.TEXT,
            size_gb=3.5,
            num_items=8841823,
            download_url="https://msmarco.blob.core.windows.net/msmarcoranking/collection.tar.gz",
            description="8.8M passages from Bing search results for document ranking",
            license="Microsoft Research License Agreement",
            homepage="https://microsoft.github.io/msmarco/",
            citation="Nguyen et al. MS MARCO: A Human Generated MAchine Reading COmprehension Dataset"
        ),
        DatasetType.COCO: DatasetInfo(
            name="COCO 2017 Train",
            dataset_type=DatasetType.COCO,
            modality=ModalityType.IMAGE,
            size_gb=18.0,
            num_items=118287,
            download_url="http://images.cocodataset.org/zips/train2017.zip",
            description="118K images with object detection and segmentation annotations",
            license="CC BY 4.0",
            homepage="https://cocodataset.org/",
            citation="Lin et al. Microsoft COCO: Common Objects in Context"
        ),
        DatasetType.LIBRISPEECH: DatasetInfo(
            name="LibriSpeech train-clean-360",
            dataset_type=DatasetType.LIBRISPEECH,
            modality=ModalityType.AUDIO,
            size_gb=23.0,
            num_items=104014,
            download_url="https://www.openslr.org/resources/12/train-clean-360.tar.gz",
            description="360 hours of clean English speech from audiobooks",
            license="CC BY 4.0",
            homepage="https://www.openslr.org/12/",
            citation="Panayotov et al. Librispeech: An ASR corpus based on public domain audio books"
        ),
        DatasetType.MSR_VTT: DatasetInfo(
            name="MSR-VTT",
            dataset_type=DatasetType.MSR_VTT,
            modality=ModalityType.VIDEO,
            size_gb=32.0,
            num_items=10000,
            download_url="https://www.robots.ox.ac.uk/~maxbain/frozen-in-time/data/MSRVTT.zip",
            description="10K videos with natural language descriptions",
            license="Microsoft Research License",
            homepage="https://www.microsoft.com/en-us/research/publication/msr-vtt-a-large-video-description-dataset-for-bridging-video-and-language/",
            citation="Xu et al. MSR-VTT: A Large Video Description Dataset for Bridging Video and Language"
        ),
    }

    @classmethod
    def get_dataset_info(cls, dataset_type: DatasetType) -> DatasetInfo:
        """Get dataset information."""
        return cls.DATASETS[dataset_type]

    @classmethod
    def list_datasets(cls) -> list[dict[str, Any]]:
        """List all available datasets."""
        return [
            {
                "name": info.name,
                "type": info.dataset_type.value,
                "modality": info.modality.value,
                "size_gb": info.size_gb,
                "num_items": info.num_items,
                "description": info.description,
                "license": info.license,
            }
            for info in cls.DATASETS.values()
        ]


class DatasetDownloader:
    """
    Dataset downloader with S3 staging and progress tracking.

    Downloads recommended datasets, extracts contents, and stages
    to S3 for large-scale ingestion processing.
    """

    def __init__(
        self,
        local_cache_dir: Path | None = None,
        s3_bucket: str | None = None,
        s3_prefix: str = "datasets/"
    ):
        """
        Initialize the dataset downloader.

        Args:
            local_cache_dir: Local directory for caching downloads
            s3_bucket: S3 bucket for staging datasets
            s3_prefix: S3 key prefix for datasets
        """
        self.local_cache_dir = local_cache_dir or Path.home() / ".s3vector" / "datasets"
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)

        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix

        if s3_bucket:
            self.s3_client = boto3.client('s3')
        else:
            self.s3_client = None

        logger.info(f"Initialized dataset downloader: cache={self.local_cache_dir}")

    async def download_dataset(
        self,
        dataset_type: DatasetType,
        skip_cache: bool = False,
        progress_callback: Callable[[DownloadProgress], None] | None = None
    ) -> Path:
        """
        Download a dataset to local cache.

        Args:
            dataset_type: Type of dataset to download
            skip_cache: Skip cache and re-download
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded and extracted dataset directory
        """
        dataset_info = DatasetRegistry.get_dataset_info(dataset_type)

        # Check cache
        dataset_dir = self.local_cache_dir / dataset_type.value
        if dataset_dir.exists() and not skip_cache:
            logger.info(f"Using cached dataset: {dataset_dir}")
            return dataset_dir

        logger.info(f"Downloading {dataset_info.name} ({dataset_info.size_gb} GB)...")

        # Download file
        download_file = self.local_cache_dir / f"{dataset_type.value}.archive"

        await self._download_file(
            url=dataset_info.download_url,
            output_path=download_file,
            dataset_name=dataset_info.name,
            progress_callback=progress_callback
        )

        # Extract
        logger.info(f"Extracting {dataset_info.name}...")
        dataset_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(DownloadProgress(
                dataset_name=dataset_info.name,
                total_bytes=0,
                downloaded_bytes=0,
                progress_percentage=0.0,
                download_speed_mbps=0.0,
                eta_seconds=0.0,
                started_at=datetime.utcnow(),
                status="extracting"
            ))

        await self._extract_archive(download_file, dataset_dir)

        # Clean up archive
        download_file.unlink()

        logger.info(f"Dataset ready: {dataset_dir}")
        return dataset_dir

    async def stage_to_s3(
        self,
        dataset_dir: Path,
        dataset_type: DatasetType,
        progress_callback: Callable[[DownloadProgress], None] | None = None
    ) -> str:
        """
        Stage dataset to S3 for cloud processing.

        Args:
            dataset_dir: Local dataset directory
            dataset_type: Dataset type
            progress_callback: Optional progress callback

        Returns:
            S3 URI prefix for staged dataset
        """
        if not self.s3_client:
            raise ValueError("S3 client not initialized (s3_bucket required)")

        dataset_info = DatasetRegistry.get_dataset_info(dataset_type)

        logger.info(f"Staging {dataset_info.name} to S3...")

        s3_dataset_prefix = f"{self.s3_prefix}{dataset_type.value}/"

        # Get all files
        files = list(dataset_dir.rglob("*"))
        files = [f for f in files if f.is_file()]

        total_bytes = sum(f.stat().st_size for f in files)
        uploaded_bytes = 0

        if progress_callback:
            progress_callback(DownloadProgress(
                dataset_name=dataset_info.name,
                total_bytes=total_bytes,
                downloaded_bytes=0,
                progress_percentage=0.0,
                download_speed_mbps=0.0,
                eta_seconds=0.0,
                started_at=datetime.utcnow(),
                status="staging"
            ))

        # Upload files
        import time
        start_time = time.time()

        for file_path in files:
            relative_path = file_path.relative_to(dataset_dir)
            s3_key = f"{s3_dataset_prefix}{relative_path}"

            # Upload to S3
            await asyncio.to_thread(
                self.s3_client.upload_file,
                str(file_path),
                self.s3_bucket,
                s3_key
            )

            uploaded_bytes += file_path.stat().st_size

            # Update progress
            if progress_callback:
                elapsed = time.time() - start_time
                speed_mbps = (uploaded_bytes / elapsed / 1024 / 1024) if elapsed > 0 else 0
                remaining_bytes = total_bytes - uploaded_bytes
                eta_seconds = (remaining_bytes / (uploaded_bytes / elapsed)) if uploaded_bytes > 0 else 0

                progress_callback(DownloadProgress(
                    dataset_name=dataset_info.name,
                    total_bytes=total_bytes,
                    downloaded_bytes=uploaded_bytes,
                    progress_percentage=(uploaded_bytes / total_bytes * 100) if total_bytes > 0 else 0,
                    download_speed_mbps=speed_mbps,
                    eta_seconds=eta_seconds,
                    started_at=datetime.utcfromtimestamp(start_time),
                    status="staging"
                ))

        s3_uri = f"s3://{self.s3_bucket}/{s3_dataset_prefix}"
        logger.info(f"Dataset staged to {s3_uri}")

        return s3_uri

    async def _download_file(
        self,
        url: str,
        output_path: Path,
        dataset_name: str,
        progress_callback: Callable[[DownloadProgress], None] | None = None
    ) -> None:
        """Download a file with progress tracking."""
        import time

        # Use requests in a thread to avoid blocking
        def _download():
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_bytes = int(response.headers.get('content-length', 0))
            downloaded_bytes = 0
            start_time = time.time()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        # Update progress
                        if progress_callback:
                            elapsed = time.time() - start_time
                            speed_mbps = (downloaded_bytes / elapsed / 1024 / 1024) if elapsed > 0 else 0
                            remaining_bytes = total_bytes - downloaded_bytes
                            eta_seconds = (remaining_bytes / (downloaded_bytes / elapsed)) if downloaded_bytes > 0 else 0

                            progress_callback(DownloadProgress(
                                dataset_name=dataset_name,
                                total_bytes=total_bytes,
                                downloaded_bytes=downloaded_bytes,
                                progress_percentage=(downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0,
                                download_speed_mbps=speed_mbps,
                                eta_seconds=eta_seconds,
                                started_at=datetime.utcfromtimestamp(start_time),
                                status="downloading"
                            ))

        await asyncio.to_thread(_download)

    async def _extract_archive(self, archive_path: Path, extract_dir: Path) -> None:
        """Extract an archive file."""
        def _extract():
            if archive_path.suffix == '.zip' or str(archive_path).endswith('.zip'):
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif str(archive_path).endswith('.tar.gz') or str(archive_path).endswith('.tgz'):
                import tarfile
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(extract_dir)
            else:
                raise ValueError(f"Unsupported archive format: {archive_path}")

        await asyncio.to_thread(_extract)

    def get_dataset_manifest(self, dataset_dir: Path) -> dict[str, Any]:
        """
        Generate manifest for a dataset directory.

        Args:
            dataset_dir: Dataset directory

        Returns:
            Manifest dictionary with file list and metadata
        """
        files = list(dataset_dir.rglob("*"))
        files = [f for f in files if f.is_file()]

        total_size_bytes = sum(f.stat().st_size for f in files)

        manifest = {
            "dataset_dir": str(dataset_dir),
            "total_files": len(files),
            "total_size_bytes": total_size_bytes,
            "total_size_gb": round(total_size_bytes / 1024 / 1024 / 1024, 2),
            "files": [
                {
                    "path": str(f.relative_to(dataset_dir)),
                    "size_bytes": f.stat().st_size
                }
                for f in files
            ]
        }

        return manifest

    @staticmethod
    def list_available_datasets() -> list[dict[str, Any]]:
        """List all available datasets."""
        return DatasetRegistry.list_datasets()
