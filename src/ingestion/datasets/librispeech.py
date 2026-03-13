"""
LibriSpeech Dataset Downloader.

Downloads LibriSpeech dataset for audio embedding benchmarking.
"""

import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, Any
import time

from src.ingestion.datasets import register_dataset
from src.ingestion.datasets.base import DatasetDownloader, DownloadConfig, DatasetMetadata
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@register_dataset('librispeech')
class LibriSpeechDownloader(DatasetDownloader):
    """Downloader for LibriSpeech dataset."""

    DATASET_NAME = "librispeech"
    MODALITY = "audio"
    DESCRIPTION = "LibriSpeech - Large corpus of read English speech"
    LICENSE = "CC-BY 4.0"
    RECOMMENDED_SIZE = 100000

    # Dataset URLs (subsets by size and quality)
    SUBSETS = {
        'dev-clean': {
            'url': 'https://www.openslr.org/resources/12/dev-clean.tar.gz',
            'size_hours': 5.4,
            'size_gb': 0.3,
            'items': 2703
        },
        'dev-other': {
            'url': 'https://www.openslr.org/resources/12/dev-other.tar.gz',
            'size_hours': 5.3,
            'size_gb': 0.3,
            'items': 2864
        },
        'test-clean': {
            'url': 'https://www.openslr.org/resources/12/test-clean.tar.gz',
            'size_hours': 5.4,
            'size_gb': 0.3,
            'items': 2620
        },
        'test-other': {
            'url': 'https://www.openslr.org/resources/12/test-other.tar.gz',
            'size_hours': 5.1,
            'size_gb': 0.3,
            'items': 2939
        },
        'train-clean-100': {
            'url': 'https://www.openslr.org/resources/12/train-clean-100.tar.gz',
            'size_hours': 100.6,
            'size_gb': 6.3,
            'items': 28539
        },
        'train-clean-360': {
            'url': 'https://www.openslr.org/resources/12/train-clean-360.tar.gz',
            'size_hours': 363.6,
            'size_gb': 23.0,
            'items': 104014
        },
        'train-other-500': {
            'url': 'https://www.openslr.org/resources/12/train-other-500.tar.gz',
            'size_hours': 496.7,
            'size_gb': 30.0,
            'items': 148688
        }
    }

    def __init__(self, config: DownloadConfig):
        """Initialize LibriSpeech downloader."""
        super().__init__(config)
        self.selected_subsets = self._select_subsets()

    def _select_subsets(self) -> list:
        """Select appropriate subsets based on max_items."""
        max_items = self.config.max_items or 100000

        selected = []

        if max_items <= 5000:
            # Download dev-clean only
            selected = ['dev-clean']
        elif max_items <= 10000:
            # Download dev sets
            selected = ['dev-clean', 'dev-other']
        elif max_items <= 30000:
            # Download train-clean-100
            selected = ['train-clean-100']
        elif max_items <= 110000:
            # Download train-clean-360
            selected = ['train-clean-360']
        else:
            # Download train-clean-360 + train-other-500
            selected = ['train-clean-360', 'train-other-500']

        logger.info(f"Selected subsets: {selected} for max_items={max_items}")
        return selected

    async def download(self) -> DatasetMetadata:
        """Download LibriSpeech dataset."""
        start_time = time.time()
        logger.info(f"Starting LibriSpeech download to {self.output_dir}")

        # Download selected subsets
        download_tasks = []
        for subset_name in self.selected_subsets:
            subset = self.SUBSETS[subset_name]
            archive_path = self.output_dir / f"{subset_name}.tar.gz"
            download_tasks.append(
                self.download_file(subset['url'], archive_path)
            )

        success = await asyncio.gather(*download_tasks)

        if not all(success):
            raise RuntimeError("Failed to download one or more LibriSpeech subsets")

        # Extract archives
        logger.info("Extracting archives...")
        for subset_name in self.selected_subsets:
            archive_path = self.output_dir / f"{subset_name}.tar.gz"
            self.extract_archive(archive_path, self.output_dir)

        # Count audio files
        audio_files = list(self.output_dir.rglob('*.flac'))
        total_items = len(audio_files)
        downloaded_items = min(total_items, self.config.max_items or total_items)

        # Calculate total size
        total_size = sum(f.stat().st_size for f in audio_files)

        download_time = time.time() - start_time

        metadata = DatasetMetadata(
            dataset_name=self.DATASET_NAME,
            modality=self.MODALITY,
            total_items=total_items,
            downloaded_items=downloaded_items,
            failed_items=0,
            total_size_bytes=total_size,
            download_time_seconds=download_time,
            output_directory=self.output_dir
        )

        logger.info(f"LibriSpeech download complete: {downloaded_items} audio clips in {download_time:.2f}s")
        return metadata

    async def stream_items(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream LibriSpeech audio files with transcripts.

        Yields:
            Dict with audio_path, transcript, speaker_id, chapter_id
        """
        logger.info(f"Streaming LibriSpeech from {self.output_dir}")

        count = 0
        max_items = self.config.max_items or float('inf')

        # Find all audio files
        audio_files = sorted(self.output_dir.rglob('*.flac'))

        for audio_path in audio_files:
            if count >= max_items:
                break

            # Parse LibriSpeech file structure
            # Path format: LibriSpeech/<subset>/<speaker_id>/<chapter_id>/<speaker_id>-<chapter_id>-<utterance_id>.flac
            parts = audio_path.stem.split('-')
            if len(parts) >= 3:
                speaker_id = parts[0]
                chapter_id = parts[1]
                utterance_id = parts[2]
            else:
                speaker_id = "unknown"
                chapter_id = "unknown"
                utterance_id = "unknown"

            # Load transcript
            transcript = self._load_transcript(audio_path)

            item = {
                'audio_path': str(audio_path),
                'speaker_id': speaker_id,
                'chapter_id': chapter_id,
                'utterance_id': utterance_id,
                'transcript': transcript,
                'duration_seconds': self._estimate_duration(audio_path),
                'modality': 'audio'
            }

            if self.validate_item(item):
                yield item
                count += 1

                if count % 1000 == 0:
                    logger.info(f"Streamed {count} audio clips")

        logger.info(f"Finished streaming {count} audio clips")

    def _load_transcript(self, audio_path: Path) -> str:
        """Load transcript for audio file."""
        # Transcript files are in the same directory with .txt extension
        # Format: <speaker_id>-<chapter_id>.trans.txt
        # Each line: <speaker_id>-<chapter_id>-<utterance_id> <transcript>

        speaker_id = audio_path.stem.split('-')[0]
        chapter_id = audio_path.stem.split('-')[1]
        utterance_id = audio_path.stem.split('-')[2]

        transcript_file = audio_path.parent / f"{speaker_id}-{chapter_id}.trans.txt"

        if not transcript_file.exists():
            logger.warning(f"Transcript file not found: {transcript_file}")
            return ""

        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(' ', 1)
                    if len(parts) >= 2:
                        file_id = parts[0]
                        transcript = parts[1]

                        expected_id = f"{speaker_id}-{chapter_id}-{utterance_id}"
                        if file_id == expected_id:
                            return transcript

        except Exception as e:
            logger.warning(f"Failed to load transcript: {e}")

        return ""

    def _estimate_duration(self, audio_path: Path) -> float:
        """Estimate audio duration from file size (rough approximation)."""
        # FLAC compression ratio is roughly 50-60% of original
        # LibriSpeech is 16kHz, 16-bit mono = 32000 bytes per second
        # Compressed: ~16000 bytes per second
        file_size = audio_path.stat().st_size
        estimated_duration = file_size / 16000.0
        return round(estimated_duration, 2)

    def validate_item(self, item: Dict[str, Any]) -> bool:
        """Validate LibriSpeech audio clip."""
        audio_path = Path(item['audio_path'])

        # Check file exists
        if not audio_path.exists():
            return False

        # Check file size (should be at least 10KB)
        if audio_path.stat().st_size < 10240:
            return False

        # Check has transcript
        if not item.get('transcript'):
            logger.warning(f"No transcript for {audio_path}")
            return False

        return True

    def get_preprocessing_config(self) -> Dict[str, Any]:
        """Get recommended preprocessing configuration."""
        return {
            'sample_rate': 16000,
            'format': 'wav',
            'channels': 1,  # mono
            'normalization': 'peak',
            'peak_db': -3.0,
            'description': 'Resample to 16kHz mono with peak normalization'
        }

    def get_embedding_strategy(self) -> Dict[str, Any]:
        """Get recommended embedding strategy."""
        return {
            'model': 'facebook/wav2vec2-base-960h',
            'model_type': 'sagemaker',
            'dimension': 768,
            'batch_size': 16,
            'description': 'Wav2Vec2 model on SageMaker'
        }

    def get_subset_info(self) -> Dict[str, Any]:
        """Get information about available subsets."""
        return {
            'selected_subsets': self.selected_subsets,
            'available_subsets': self.SUBSETS,
            'total_estimated_items': sum(
                self.SUBSETS[s]['items'] for s in self.selected_subsets
            ),
            'total_estimated_size_gb': sum(
                self.SUBSETS[s]['size_gb'] for s in self.selected_subsets
            )
        }
