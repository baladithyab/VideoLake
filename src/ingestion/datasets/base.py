"""
Abstract Base Class for Dataset Downloaders.

Defines common interface and utilities for downloading and processing
benchmark datasets.
"""

import asyncio
import hashlib
import shutil
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Dict, Any, Optional, List
from urllib.parse import urlparse

import aiohttp
import requests
from tqdm import tqdm

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for dataset download."""
    max_items: Optional[int] = None
    output_dir: Optional[Path] = None
    chunk_size: int = 8192
    max_concurrent_downloads: int = 10
    verify_checksums: bool = True
    cleanup_on_error: bool = True
    resume_from_checkpoint: bool = True


@dataclass
class DatasetMetadata:
    """Metadata about downloaded dataset."""
    dataset_name: str
    modality: str
    total_items: int
    downloaded_items: int
    failed_items: int
    total_size_bytes: int
    download_time_seconds: float
    output_directory: Path
    checksum: Optional[str] = None


class DatasetDownloader(ABC):
    """Abstract base class for dataset downloaders."""

    # Subclasses must define these
    DATASET_NAME: str = ""
    MODALITY: str = ""  # text, image, audio, video
    DESCRIPTION: str = ""
    LICENSE: str = ""
    RECOMMENDED_SIZE: int = 100000  # Recommended items for benchmarking

    def __init__(self, config: DownloadConfig):
        """Initialize downloader with configuration."""
        self.config = config

        # Setup output directory
        if config.output_dir is None:
            self.output_dir = Path(tempfile.mkdtemp(prefix=f"{self.DATASET_NAME}_"))
        else:
            self.output_dir = config.output_dir
            self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized {self.DATASET_NAME} downloader: output_dir={self.output_dir}")

    @abstractmethod
    async def download(self) -> DatasetMetadata:
        """
        Download the dataset.

        Returns:
            DatasetMetadata with download statistics
        """
        pass

    @abstractmethod
    async def stream_items(self) -> AsyncIterator[Any]:
        """
        Stream dataset items for processing.

        Yields dataset items one at a time for efficient processing.
        """
        pass

    @abstractmethod
    def validate_item(self, item: Any) -> bool:
        """
        Validate a dataset item.

        Args:
            item: Dataset item to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    async def download_file(
        self,
        url: str,
        output_path: Path,
        show_progress: bool = True
    ) -> bool:
        """
        Download a file from URL to local path.

        Args:
            url: Source URL
            output_path: Local output path
            show_progress: Whether to show progress bar

        Returns:
            True if successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()

                    total_size = int(response.headers.get('content-length', 0))

                    if show_progress and total_size > 0:
                        pbar = tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            desc=output_path.name
                        )
                    else:
                        pbar = None

                    with open(output_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(self.config.chunk_size):
                            f.write(chunk)
                            if pbar:
                                pbar.update(len(chunk))

                    if pbar:
                        pbar.close()

            logger.info(f"Downloaded: {url} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            return False

    def download_file_sync(
        self,
        url: str,
        output_path: Path,
        show_progress: bool = True
    ) -> bool:
        """
        Synchronous file download (for compatibility).

        Args:
            url: Source URL
            output_path: Local output path
            show_progress: Whether to show progress bar

        Returns:
            True if successful, False otherwise
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))

            if show_progress and total_size > 0:
                pbar = tqdm(
                    total=total_size,
                    unit='B',
                    unit_scale=True,
                    desc=output_path.name
                )
            else:
                pbar = None

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.config.chunk_size):
                    if chunk:
                        f.write(chunk)
                        if pbar:
                            pbar.update(len(chunk))

            if pbar:
                pbar.close()

            logger.info(f"Downloaded: {url} -> {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            return False

    def extract_archive(self, archive_path: Path, extract_to: Optional[Path] = None) -> Path:
        """
        Extract compressed archive.

        Args:
            archive_path: Path to archive file
            extract_to: Optional extraction directory

        Returns:
            Path to extracted content
        """
        if extract_to is None:
            extract_to = archive_path.parent / archive_path.stem

        extract_to.mkdir(parents=True, exist_ok=True)

        logger.info(f"Extracting {archive_path} to {extract_to}")

        try:
            if archive_path.suffix in ['.tar', '.gz', '.tgz', '.bz2']:
                shutil.unpack_archive(archive_path, extract_to)
            elif archive_path.suffix == '.zip':
                shutil.unpack_archive(archive_path, extract_to, 'zip')
            else:
                raise ValueError(f"Unsupported archive format: {archive_path.suffix}")

            logger.info(f"Extraction complete: {extract_to}")
            return extract_to

        except Exception as e:
            logger.error(f"Failed to extract {archive_path}: {e}")
            raise

    def compute_checksum(self, file_path: Path, algorithm: str = 'md5') -> str:
        """
        Compute file checksum.

        Args:
            file_path: Path to file
            algorithm: Hash algorithm (md5, sha256)

        Returns:
            Hex digest string
        """
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.config.chunk_size), b''):
                hasher.update(chunk)

        return hasher.hexdigest()

    def verify_checksum(
        self,
        file_path: Path,
        expected_checksum: str,
        algorithm: str = 'md5'
    ) -> bool:
        """
        Verify file checksum matches expected value.

        Args:
            file_path: Path to file
            expected_checksum: Expected checksum value
            algorithm: Hash algorithm

        Returns:
            True if checksums match, False otherwise
        """
        actual_checksum = self.compute_checksum(file_path, algorithm)
        matches = actual_checksum.lower() == expected_checksum.lower()

        if not matches:
            logger.warning(
                f"Checksum mismatch for {file_path}: "
                f"expected={expected_checksum}, actual={actual_checksum}"
            )

        return matches

    def get_dataset_info(self) -> Dict[str, Any]:
        """Get information about this dataset."""
        return {
            'name': self.DATASET_NAME,
            'modality': self.MODALITY,
            'description': self.DESCRIPTION,
            'license': self.LICENSE,
            'recommended_size': self.RECOMMENDED_SIZE,
            'output_directory': str(self.output_dir)
        }

    def cleanup(self):
        """Clean up temporary files."""
        if self.config.cleanup_on_error and self.output_dir.exists():
            try:
                shutil.rmtree(self.output_dir)
                logger.info(f"Cleaned up: {self.output_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup {self.output_dir}: {e}")
